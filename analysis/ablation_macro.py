"""A5 — ablation de la porte macro, mesuree hors-ligne sur le dataset G0.

La decision A5 (Jonas, 03/08) — « veto macro HOSTILE seul ? NON, la penalite NEUTRE est
CONSERVEE » — a ete actee sans code : le comportement etait deja celui-la (`cio.py:68-70`,
`MACRO_NEUTRE_CONV_BUMP`). Elle n'a jamais ete MESUREE. `docs/08` l'annonce pourtant depuis
le 03/08 : le journal v2 (`macro_regime`, `equity_veto`) rend la porte macro ablatable a
posteriori, « un seul run permet de deriver PORTEUR seul et non-HOSTILE par filtrage ».

Ce script ne touche a AUCUN code de production : il recalcule le signal a partir des
colonnes deja presentes dans le dataset (`conviction`, `seuil`, `rr_dispo`, `regime`,
`trend_dir`) et ne fait varier QUE la porte macro. La fidelite est verifiee par
construction : la variante V0 doit reproduire exactement les colonnes `signal_long` /
`signal_short` du dataset, sinon le script s'arrete.

CE QUI EST MESURE, ET POURQUOI CE N'EST PAS L'ESPERANCE TOTALE
Le substrat a une esperance NEGATIVE (modele nul B1 : -0,0123 R long, -0,0370 R short). Sur
une base pareille, tout filtre qui bloque des trades ameliore le resultat total SANS RIEN
TRIER — c'est le biais du substrat nul, et c'est exactement ce qui a produit le resultat
historique « veto HOSTILE : -19,1 % -> -7,0 % » (BUILD_NOTES 17/07), non mesure et non
interpretable. La seule question valide est celle de la SELECTIVITE :

    le filtre bloque-t-il des trades dont l'esperance est plus mauvaise que la moyenne ?

D'ou la mesure centrale de ce script : l'esperance en R des signaux MARGINAUX (ceux qu'une
porte plus stricte bloque) comparee a celle du noyau qu'elle laisse passer.

Le hold-out (B5) est SCELLE : `mesures.charger` ne lit que `split='train'`, et le script
verifie qu'aucune ligne de hold-out n'a survecu au chargement.

Usage :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe analysis/ablation_macro.py
      [--db analysis/out/arit_analyse.sqlite] [--fdr 0.10] [--json analysis/out/ablation_A5.json]
"""

import argparse
import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import mesures  # noqa: E402  — charger(), benjamini_hochberg(), modele_nul() : zero duplication

from arit_lib import contracts, params  # noqa: E402

EXPERIMENTS = REPO / "research" / "EXPERIMENTS.jsonl"
EXPERIENCE_ID = "A5-ablation-porte-macro"     # B6 — sans cette ligne, le script refuse de tourner

FDR_DEFAUT = 0.10          # B2 — taux de fausses decouvertes tolere, preenregistre
SIGMA_R_REF = 1.23         # geometrie ARIT (41 % TP a +1,5R / 59 % SL a -1R) — pour le MDE
Z_MDE = 2.487              # z(1-alpha) + z(1-beta) : alpha 0,05 unilateral, puissance 80 %
CHEVAUCHEMENT = 1.6        # n_eff = n / 1,6 — fenetres 96 h qui se recouvrent + paires correlees
BLOC_L_DEFAUT = 3          # longueur moyenne de bloc, FIXEE AVANT la mesure (preenregistree)
BLOC_L_SENSIBILITE = (1, 3, 6)
N_BOOT = 10_000
IC_NIVEAU = 0.90
SEED = 20260818            # bootstrap reproductible

_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES
_SFX = contracts.SHORT_SUFFIX
_MACRO = contracts.MACRO_REGIME_COL
_TREND = contracts.TREND_DIR_COL
_SENS = ("long", "short")


def preenregistrement(chemin: pathlib.Path, id_exp: str) -> dict:
    """B6 — le verrou methodologique, materialise : pas de ligne, pas de mesure.

    Ce n'est pas une formalite. Sans hypothese et sans regle de decision ecrites AVANT, un
    resultat post-hoc est indiscernable d'une hypothese confirmee, et le compteur cumulatif
    d'essais — seule base honnete d'une correction de tests multiples — n'existe pas.
    """
    if not chemin.exists():
        raise SystemExit(f"B6 : registre absent ({chemin}). Preenregistrer avant de mesurer.")
    trouve = None
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        try:
            entree = json.loads(ligne)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"B6 : registre illisible ({exc})") from exc
        if entree.get("id") == id_exp:
            trouve = entree          # la DERNIERE ligne portant cet id fait foi
    if trouve is None:
        raise SystemExit(f"B6 : aucune entree '{id_exp}' dans {chemin}. "
                         "Ecrire l'hypothese, la metrique et la regle de decision AVANT.")
    return trouve


def seuil_sans_bump(df: pd.DataFrame) -> pd.Series:
    """Retire la penalite A5 du seuil.

    PIEGE : la colonne `seuil` du dataset est produite par `cio.conviction`, qui a DEJA
    ajoute MACRO_NEUTRE_CONV_BUMP aux lignes NEUTRE. Une variante « sans bump » qui se
    contenterait de lire `seuil` mesurerait donc la production, pas l'alternative.
    """
    return df["seuil"] - np.where(df[_MACRO] == _NEUTRE, params.MACRO_NEUTRE_CONV_BUMP, 0.0)


def _long_ok_defaut(macro: pd.Series) -> pd.Series:
    # Fail-safe de `cio.direction_macro` : macro inconnue => long seul. On n'ouvre pas un
    # short sur une absence d'information.
    return macro.isin((_PORTEUR, _NEUTRE)) | macro.isna()


def _short_ok_defaut(macro: pd.Series) -> pd.Series:
    return macro.isin((_HOSTILE, _NEUTRE))


VARIANTES = (
    {"nom": "V0_prod", "bump": True,
     "doc": "production : PORTEUR->long, HOSTILE->short, NEUTRE->les deux, seuil +0,05",
     "long_ok": _long_ok_defaut, "short_ok": _short_ok_defaut},
    {"nom": "V1_sans_bump", "bump": False,
     "doc": "A5 alternatif : memes directions, SANS la penalite de seuil en NEUTRE",
     "long_ok": _long_ok_defaut, "short_ok": _short_ok_defaut},
    {"nom": "V2_porteur_hostile", "bump": False,
     "doc": "porte la plus stricte : long en PORTEUR seul, short en HOSTILE seul",
     "long_ok": lambda m: m == _PORTEUR, "short_ok": lambda m: m == _HOSTILE},
    {"nom": "V3_macro_off", "bump": False,
     "doc": "controle negatif : aucune contrainte de direction, aucun bump",
     "long_ok": lambda m: pd.Series(True, index=m.index),
     "short_ok": lambda m: pd.Series(True, index=m.index)},
)

# Chaine d'emboitement, verifiee a l'execution : chaque porte est un sous-ensemble de la
# suivante. C'est ce qui donne un sens aux signaux « marginaux » — l'ensemble exact des
# trades qu'une porte bloque et que la porte immediatement plus large accepte.
EMBOITEMENT = (("V2_porteur_hostile", "V0_prod"),
               ("V0_prod", "V1_sans_bump"),
               ("V1_sans_bump", "V3_macro_off"))


def masques(df: pd.DataFrame, variante: dict) -> dict[str, pd.Series]:
    """Reconstruit signal_long / signal_short en ne faisant varier QUE la porte macro.

    `new_4h` n'apparait pas : le dataset porte une ligne par cloture 4h
    (`dataset.extraire`), donc la condition est vraie partout. La fidelite de V0 le prouve.
    Le seuil est NaN en RANGE/RISK_OFF => la comparaison vaut False (double securite avec
    le filtre de regime, comportement identique a `cio.conviction`).
    """
    seuil = df["seuil"] if variante["bump"] else seuil_sans_bump(df)
    base = df["regime"].isin(params.ENTRY_REGIMES)
    macro = df[_MACRO]
    return {
        "long": (base & (df["conviction"] >= seuil) & (df["rr_dispo"] >= params.RR_MIN)
                 & (df[_TREND] >= 0) & variante["long_ok"](macro)),
        "short": (base & (df["conviction" + _SFX] >= seuil)
                  & (df["rr_dispo" + _SFX] >= params.RR_MIN)
                  & (df[_TREND] <= 0) & variante["short_ok"](macro)),
    }


def verifier_fidelite(df: pd.DataFrame, masques_v0: dict[str, pd.Series]) -> None:
    """V0 doit reproduire EXACTEMENT les signaux du dataset, sinon rien n'est comparable."""
    for sens in _SENS:
        attendu = df[f"signal_{sens}"].fillna(0).astype(bool)
        ecarts = int((masques_v0[sens] != attendu).sum())
        if ecarts:
            raise SystemExit(
                f"fidelite rompue sur {sens} : {ecarts} ecarts entre V0 reconstruit "
                f"({int(masques_v0[sens].sum())} signaux) et le dataset "
                f"({int(attendu.sum())}). La reconstruction ne mesure pas la production.")


def verifier_emboitement(tous: dict[str, dict[str, pd.Series]]) -> None:
    """Chaque porte doit etre incluse dans la suivante — condition d'existence des marginaux."""
    for etroit, large in EMBOITEMENT:
        for sens in _SENS:
            hors = int((tous[etroit][sens] & ~tous[large][sens]).sum())
            if hors:
                raise SystemExit(f"emboitement rompu : {etroit} a {hors} signaux {sens} "
                                 f"hors de {large}. Les marginaux n'ont pas de sens.")


def metriques(df: pd.DataFrame, masque: pd.Series, sens: str) -> dict:
    """Profil d'un ensemble de signaux. La metrique primaire est E[R] PAR SIGNAL.

    `r_total` est calcule mais ne doit JAMAIS servir de verdict : sur un substrat a
    esperance negative il ne mesure que le nombre de trades evites (biais du substrat nul).
    """
    sub = df.loc[masque]
    r = sub[f"y_r_{sens}"].dropna()
    issues = sub[f"y_issue_{sens}"].dropna()
    n = len(issues)
    if not n:
        return {"n": 0}
    tp, sl = int((issues == "TP").sum()), int((issues == "SL").sum())
    sigma = float(r.std(ddof=1)) if len(r) > 1 else float("nan")
    return {"n": n, "tp": tp, "sl": sl, "horizon": n - tp - sl, "p_tp": tp / n,
            "esperance_r": float(r.mean()), "sigma_r": sigma,
            "mediane_r": float(r.median()), "r_total": float(r.sum()),
            "mfe_r": float(sub[f"y_mfe_r_{sens}"].dropna().mean())}


def serie_r(df: pd.DataFrame, masque: pd.Series, sens: str) -> np.ndarray:
    """Les R d'un ensemble de signaux, ORDONNES par date : le bootstrap par blocs en depend."""
    sub = df.loc[masque].sort_values("ts_utc")
    return sub[f"y_r_{sens}"].dropna().to_numpy(dtype=float)


def bootstrap_blocs(x: np.ndarray, ell: int, rng: np.random.Generator,
                    n_boot: int = N_BOOT, niveau: float = IC_NIVEAU) -> tuple[float, float]:
    """IC de la moyenne par bootstrap stationnaire (Politis-Romano).

    Reechantillonner les R un par un supposerait des trades independants : ils ne le sont
    pas (fenetres de 96 h qui se recouvrent, 4 paires correlees). On tire donc des BLOCS de
    longueur geometrique, recolles circulairement — ce qui preserve la memoire locale et
    elargit l'IC jusqu'a sa largeur honnete. La longueur moyenne `ell` est fixee AVANT la
    mesure et sa sensibilite est publiee : elle pilote le resultat, donc la choisir apres
    coup reviendrait a choisir sa conclusion.
    """
    n = len(x)
    if n < 2:
        return (float("nan"), float("nan"))
    p = 1.0 / max(ell, 1)
    moyennes = np.empty(n_boot)
    for b in range(n_boot):
        ech = np.empty(n)
        i = 0
        while i < n:
            debut = int(rng.integers(n))
            longueur = min(int(rng.geometric(p)), n - i)
            ech[i:i + longueur] = x[(debut + np.arange(longueur)) % n]
            i += longueur
        moyennes[b] = ech.mean()
    marge = (1.0 - niveau) / 2.0
    lo, hi = np.quantile(moyennes, [marge, 1.0 - marge])
    return float(lo), float(hi)


def mde(n: int, sigma: float = SIGMA_R_REF, effectif: bool = False) -> float:
    """Plus petit effet detectable, en R par trade. A lire AVANT toute p-value."""
    if n <= 0:
        return float("nan")
    return Z_MDE * sigma / math.sqrt(n / CHEVAUCHEMENT if effectif else n)


def _fmt(valeur, gabarit="{:+.4f}", absent="n/a"):
    if valeur is None or (isinstance(valeur, float) and math.isnan(valeur)):
        return absent
    return gabarit.format(valeur)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=pathlib.Path, default=mesures.DB_DEFAUT)
    ap.add_argument("--fdr", type=float, default=FDR_DEFAUT)
    ap.add_argument("--bloc", type=int, default=BLOC_L_DEFAUT)
    ap.add_argument("--json", type=pathlib.Path, default=None)
    args = ap.parse_args()

    exp = preenregistrement(EXPERIMENTS, EXPERIENCE_ID)
    rng = np.random.default_rng(SEED)

    df = mesures.charger(args.db)
    if "split" in df.columns and (df["split"] != "train").any():
        raise SystemExit("B5 : des lignes hors 'train' ont ete chargees — hold-out en danger.")
    print(f"A5 — ablation de la porte macro · preenregistrement '{exp['id']}' du {exp['date']} "
          f"(essai cumule n° {exp.get('n_essais_cumules', '?')})")
    print(f"{len(df)} evaluations · {df['pair'].nunique()} paires · "
          f"{df['ts_utc'].min()[:10]} -> {df['ts_utc'].max()[:10]} · hold-out SCELLE (B5)\n")

    # --- B1 : le substrat. Sans lui, aucune des lignes suivantes ne veut rien dire. -------
    print("== substrat : modele nul de franchissement (entree au hasard, meme geometrie) ==")
    nuls = {}
    for sens in _SENS:
        nul = mesures.modele_nul(df, sens)
        if nul:
            nuls[sens] = nul
            print(f"  {sens:5s} n={nul['n']:6d}  p(TP)={nul['p_tp']:6.2%}  "
                  f"E[R]={nul['esperance_r']:+.4f}")
    print("  -> esperance NEGATIVE dans les deux sens : le R total d'une variante ne mesure")
    print("     que le nombre de trades evites. Seule la SELECTIVITE est interpretable.\n")

    tous = {v["nom"]: masques(df, v) for v in VARIANTES}
    verifier_fidelite(df, tous["V0_prod"])
    verifier_emboitement(tous)
    print("fidelite V0 == dataset : OK · emboitement V2 < V0 < V1 < V3 : OK\n")

    # --- MDE : ce que l'echantillon permet de voir, avant de regarder quoi que ce soit ----
    print("== MDE — ce que cet echantillon permet de detecter (avant toute p-value) ==")
    for sens in _SENS:
        n0 = int(tous["V0_prod"][sens].sum())
        print(f"  {sens:5s} n={n0:3d} -> MDE {mde(n0):+.3f} R/trade "
              f"(n effectif {n0 / CHEVAUCHEMENT:.0f} -> {mde(n0, effectif=True):+.3f} R)")

    # --- profil de chaque variante -------------------------------------------------------
    resultats: dict[str, dict] = {}
    famille = []
    print("\n== les 4 variantes (metrique primaire : E[R] par signal retenu) ==")
    entete = (f"  {'variante':20s}{'sens':6s}{'n':>4s}{'p(TP)':>8s}{'E[R]':>9s}"
              f"{'IC90 bootstrap':>20s}{'R total':>10s}")
    print(entete)
    for variante in VARIANTES:
        nom = variante["nom"]
        resultats[nom] = {"doc": variante["doc"]}
        for sens in _SENS:
            m = metriques(df, tous[nom][sens], sens)
            if not m.get("n"):
                continue
            lo, hi = bootstrap_blocs(serie_r(df, tous[nom][sens], sens), args.bloc, rng)
            m["ic90"] = [lo, hi]
            nul = nuls.get(sens)
            if nul:
                m["p_value_vs_nul"] = float(stats.binomtest(
                    m["tp"], m["n"], nul["p_tp"], alternative="greater").pvalue)
                famille.append({"test": f"{nom}/{sens} vs modele nul",
                                "p_brute": m["p_value_vs_nul"]})
            resultats[nom][sens] = m
            print(f"  {nom:20s}{sens:6s}{m['n']:4d}{m['p_tp']:8.1%}"
                  f"{m['esperance_r']:+9.4f}  [{_fmt(lo)} ; {_fmt(hi)}]{m['r_total']:+10.2f}")
    print("  (R total affiche pour memoire — jamais comme verdict : biais du substrat nul)")

    # --- LE test A5 : selectivite marginale ----------------------------------------------
    print("\n== selectivite : les signaux qu'une porte BLOQUE sont-ils plus mauvais ? ==")
    print("   marginaux = signaux acceptes par la porte large et refuses par la porte etroite")
    marginaux: list[dict] = []
    print(f"  {'porte etroite -> large':40s}{'sens':6s}{'n':>4s}{'E[R] marg':>11s}"
          f"{'E[R] noyau':>12s}{'delta':>9s}{'p':>8s}")
    for etroit, large in EMBOITEMENT:
        for sens in _SENS:
            marge = tous[large][sens] & ~tous[etroit][sens]
            m_marg = metriques(df, marge, sens)
            m_noyau = metriques(df, tous[etroit][sens], sens)
            if not m_marg.get("n") or not m_noyau.get("n"):
                print(f"  {etroit + ' -> ' + large:40s}{sens:6s}"
                      f"{m_marg.get('n', 0):4d}{'  aucun marginal exploitable':>40s}")
                continue
            # Hypothese A5 : les marginaux sont PLUS MAUVAIS que le noyau -> unilateral 'less'
            p = float(stats.binomtest(m_marg["tp"], m_marg["n"], m_noyau["p_tp"],
                                      alternative="less").pvalue)
            lo, hi = bootstrap_blocs(serie_r(df, marge, sens), args.bloc, rng)
            delta = m_marg["esperance_r"] - m_noyau["esperance_r"]
            ligne = {"porte": f"{etroit} -> {large}", "sens": sens, "n": m_marg["n"],
                     "esperance_marginale": m_marg["esperance_r"],
                     "esperance_noyau": m_noyau["esperance_r"], "delta": delta,
                     "ic90_marginal": [lo, hi], "p_brute": p,
                     "mde_marginal": mde(m_marg["n"])}
            marginaux.append(ligne)
            famille.append({"test": f"marginaux {etroit}->{large}/{sens}", "p_brute": p})
            print(f"  {etroit + ' -> ' + large:40s}{sens:6s}{m_marg['n']:4d}"
                  f"{m_marg['esperance_r']:+11.4f}{m_noyau['esperance_r']:+12.4f}"
                  f"{delta:+9.4f}{p:8.3f}")

    a5 = [m for m in marginaux if m["porte"] == "V0_prod -> V1_sans_bump"]
    print("\n  Le test de A5 est la ligne 'V0_prod -> V1_sans_bump' : les signaux que la")
    print("  penalite NEUTRE bloque. MDE sur ces marginaux :")
    for m in a5:
        print(f"    {m['sens']:5s} n={m['n']:2d} -> il faudrait un ecart de "
              f"{m['mde_marginal']:+.3f} R/trade pour esperer le detecter "
              f"(observe : {m['delta']:+.4f})")

    # --- correction de tests multiples sur la famille DECLAREE ----------------------------
    print(f"\n== Benjamini-Hochberg sur la famille declaree ({len(famille)} tests, "
          f"FDR={args.fdr}) ==")
    table = mesures.benjamini_hochberg(pd.DataFrame(famille), args.fdr)
    survivants = table[table["signif_BH"]] if not table.empty else table
    print(f"  {len(survivants)} test(s) survivent a la correction"
          f"{' : ' + ', '.join(survivants['test']) if len(survivants) else ''}")
    if not table.empty:
        for r in table.head(4).itertuples():
            print(f"    {r.test:44s} p={r.p_brute:.4f}  seuil BH={r.seuil_BH:.4f}"
                  f"  {'OUI' if r.signif_BH else '-'}")
    print("  reserve : les variantes partagent l'essentiel de leurs signaux — BH suppose")
    print("  l'independance, la correction est donc conservatrice dans le mauvais sens.")

    # --- sensibilite a la longueur de bloc ------------------------------------------------
    print(f"\n== sensibilite du bootstrap a la longueur de bloc (ell = "
          f"{', '.join(map(str, BLOC_L_SENSIBILITE))}) ==")
    sensibilite = {}
    marge_a5 = {sens: tous["V1_sans_bump"][sens] & ~tous["V0_prod"][sens] for sens in _SENS}
    for sens in _SENS:
        x = serie_r(df, marge_a5[sens], sens)
        sensibilite[sens] = {}
        rendu = []
        for ell in BLOC_L_SENSIBILITE:
            lo, hi = bootstrap_blocs(x, ell, np.random.default_rng(SEED))
            sensibilite[sens][ell] = [lo, hi]
            rendu.append(f"ell={ell} [{_fmt(lo)} ; {_fmt(hi)}]")
        print(f"  marginaux A5 {sens:5s} n={len(x):2d} : " + "  ".join(rendu))

    # --- verdict, selon la regle preenregistree -------------------------------------------
    regle = exp.get("regle_de_decision", {})
    conclusifs = [m for m in a5
                  if m["delta"] < 0 and m["p_brute"] <= args.fdr / max(len(famille), 1)
                  and m["ic90_marginal"][1] < m["esperance_noyau"]]
    verdict = "A5_confirmee" if conclusifs else "indecidable"
    print(f"\n== VERDICT (regle preenregistree) : {verdict.upper()} ==")
    print(f"  {regle.get(verdict, '')}")
    if verdict == "indecidable":
        print("  A5 tient par defaut, faute de preuve du contraire. Ce n'est pas une")
        print("  validation : l'echantillon est trop petit pour departager quoi que ce soit.")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "experience": exp["id"], "verdict": verdict, "fdr": args.fdr,
            "bloc_defaut": args.bloc, "variantes": resultats, "marginaux": marginaux,
            "famille": table.to_dict("records") if not table.empty else [],
            "sensibilite_bloc": sensibilite,
        }, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
        print(f"\nresultats -> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
