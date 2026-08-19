"""Q4 / G3 — ablation de `s_sr` et `s_patterns` dans l'agregation, mesuree hors-ligne.

La decision G3 (Jonas, 2026-08-20) : deux scores sur cinq entrent dans la somme ponderee avec
un POIDS POSITIF et un IC NEGATIF (`s_sr` -0,0497, `s_patterns` -0,0162, mesures B9 du 12/08).
Les retirer est une ABLATION, pas une optimisation : aucune valeur n'est choisie, deux termes
sont soustraits. L'interdit n° 5 n'est pas touche.

CE QUI EST MESURE, ET POURQUOI CE N'EST PAS L'ESPERANCE
L'ablation renormalisee fait passer les signaux longs de 50 a 28 (-44 %) : elle n'est PAS
neutre en exposition. Sur un substrat a esperance negative (modele nul B1 : -0,0123 R long /
-0,0370 R short), tout ce qui reduit l'exposition ameliore le total SANS RIEN TRIER. Comparer
les E[R] totaux melangerait tri et reduction d'exposition. La mesure primaire est donc l'IC de
Spearman sur les 42 902 evaluations etiquetees, ou le seuil n'intervient pas.

LE PIEGE ARITHMETIQUE, QUI EST LE COEUR DE CE SCRIPT
`POIDS` somme a 1,00. Retirer 0,30 de poids sans renormaliser plafonne la conviction a
0,70 x multiplicateur, alors que le seuil TRANSITION vaut 0,65 et le multiplicateur 0,85
(=> 0,595 : plus aucun signal possible en TRANSITION). Constate : 5 signaux long au lieu de 50.
Une ablation brute mesurerait un durcissement de seuil, pas un retrait de scores. V3 est
conserve comme CONTROLE de ce piege, jamais comme candidate.

BOOTSTRAP PAR BLOCS, ET POURQUOI LA P-VALUE NAIVE NE VAUT RIEN ICI
Les labels de triple barriere couvrent 96 h, soit 24 bougies 4h consecutives : deux
observations voisines partagent presque tout leur avenir. Les 4 paires sont en outre correlees
(Q6 : ~1,2 paris independants, pas 4). `spearmanr` sur 42 902 lignes supposerait
l'independance et produirait une p-value massivement trop optimiste — c'est avec cette
p-value que les IC historiques de B9 ont ete publies. Les blocs de 24 bougies, tires sur les
DATES (toutes paires ensemble), repondent aux deux problemes a la fois.

Le hold-out (B5) est SCELLE : `mesures.charger` ne lit que `split='train'`, et le script
verifie qu'aucune ligne de hold-out n'a survecu au chargement.

Usage :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe analysis/ablation_scores.py
      [--db analysis/out/arit_analyse.sqlite] [--fdr 0.10]
      [--json analysis/out/ablation_Q4.json]
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy import stats

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import mesures  # noqa: E402  — charger(), benjamini_hochberg() : zero duplication
import registre  # noqa: E402  — B6 : le verrou de preenregistrement

from arit_lib import contracts, params  # noqa: E402

EXPERIENCE_ID = "Q4-ablation-scores-sr-patterns"   # B6 — sans cette ligne, le script s'arrete

FDR_DEFAUT = 0.10          # B2 — preenregistre
SEUIL_AMPLITUDE = 0.010    # preenregistre : sous ce Delta IC, l'effet n'a pas de portee
SIGMA_R_REF = 1.23         # geometrie ARIT — pour le MDE de la mesure secondaire
Z_MDE = 2.487              # z(1-alpha) + z(1-beta) : alpha 0,05 unilateral, puissance 80 %
CHEVAUCHEMENT = 1.6        # n_eff = n / 1,6 sur les SIGNAUX (espaces), cf. A5
BLOC_BOUGIES = 24          # 24 x 4h = 96 h = la fenetre du label. FIXE AVANT la mesure
BLOC_SENSIBILITE = (12, 24, 48)
N_BOOT = 10_000
IC_NIVEAU = 0.90
SEED = 20260820

_SFX = contracts.SHORT_SUFFIX
_SENS = ("long", "short")
RETIRES = ("s_sr", "s_patterns")

VARIANTES = (
    {"nom": "V0_prod", "retires": (), "renorm": False, "candidate": False,
     "doc": "production : 5 scores, POIDS d'origine"},
    {"nom": "V1_ablation_renorm", "retires": RETIRES, "renorm": True, "candidate": True,
     "doc": "s_sr + s_patterns retires, 3 poids restants renormalises a somme 1"},
    {"nom": "V2_sans_sr_renorm", "retires": ("s_sr",), "renorm": True, "candidate": True,
     "doc": "s_sr seul retire, renormalise — attribue l'effet"},
    {"nom": "V3_ablation_brute", "retires": RETIRES, "renorm": False, "candidate": False,
     "doc": "CONTROLE du piege : retires SANS renormaliser (somme des poids = 0,70)"},
)


def poids_variante(variante: dict) -> dict[str, float]:
    """Poids de l'agregat apres retrait, renormalises ou non.

    La renormalisation preserve exactement les RAPPORTS entre poids conserves : elle ne
    choisit aucune valeur, elle retablit la somme a 1. Ce n'est pas une hyperopt.
    """
    poids = {k: v for k, v in params.POIDS.items() if k not in variante["retires"]}
    if not variante["renorm"]:
        return poids
    total = sum(poids.values())
    return {k: v / total for k, v in poids.items()}


def agregat(df: pd.DataFrame, variante: dict, sens: str) -> pd.Series:
    """Somme ponderee des scores du sens demande, pour cette variante."""
    sfx = "" if sens == "long" else _SFX
    return sum(df[nom + sfx] * poids for nom, poids in poids_variante(variante).items())


def multiplicateur_short(df: pd.DataFrame) -> pd.Series:
    """`multiplicateur_short` n'est pas dans le dataset : il se deduit de conviction_short.

    conviction_short = min(1, somme_short x multiplicateur_short), et aucune conviction
    n'atteint le plafond (verifie au preenregistrement), donc le rapport est exact. Somme
    nulle => aucun signal possible de toute facon, le multiplicateur vaut alors 0.
    """
    somme = sum(df[nom + _SFX] * poids for nom, poids in params.POIDS.items())
    deduit = (df["conviction" + _SFX] / somme.replace(0, np.nan)).round(2)
    connus = (params.MULT_RISK_OFF, params.MULT_REDUCED, params.MULT_FULL)
    inattendus = set(deduit.dropna().unique()) - set(connus)
    if inattendus:
        raise SystemExit(f"multiplicateur_short deduit hors des valeurs de params : {inattendus}")
    return deduit.fillna(0.0)


def masques(df: pd.DataFrame, variante: dict, mult: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Reconstruit signal_long / signal_short en ne faisant varier QUE l'agregation.

    Toutes les autres portes sont celles du dataset : regime, rr_dispo, trend_dir et la
    direction macro. La fidelite de V0 le prouve.

    ⚠️ La colonne `direction_macro` du dataset date du 12/08, donc d'AVANT A2-quater (20/08,
    ou le veto actions est devenu directionnel). C'est voulu et sans effet sur cette mesure :
    Q4 ne fait varier QUE l'agregation, toutes les autres portes tenues constantes a ce
    qu'elles etaient. Mesurer A2-quater est un autre travail, avec son propre
    preenregistrement.
    """
    base = df["regime"].isin(params.ENTRY_REGIMES)
    direction = df["direction_macro"]
    sorties = {}
    for sens in _SENS:
        sfx = "" if sens == "long" else _SFX
        autorise = (contracts.DIR_LONG, contracts.DIR_BOTH) if sens == "long" \
            else (contracts.DIR_SHORT, contracts.DIR_BOTH)
        trend = df[contracts.TREND_DIR_COL] >= 0 if sens == "long" \
            else df[contracts.TREND_DIR_COL] <= 0
        conviction = np.minimum(1.0, agregat(df, variante, sens) * mult[sens])
        sorties[sens] = (base & (conviction >= df["seuil"])
                         & (df["rr_dispo" + sfx] >= params.RR_MIN)
                         & trend & direction.isin(autorise))
    return sorties


def verifier_fidelite(df: pd.DataFrame, masques_v0: dict[str, pd.Series]) -> None:
    """V0 doit reproduire EXACTEMENT les signaux du dataset, sinon rien n'est comparable."""
    for sens in _SENS:
        attendu = df[f"signal_{sens}"].fillna(0).astype(bool)
        ecarts = int((masques_v0[sens] != attendu).sum())
        if ecarts:
            raise SystemExit(
                f"fidelite rompue sur {sens} : {ecarts} ecarts entre V0 reconstruit "
                f"({int(masques_v0[sens].sum())} signaux) et le dataset ({int(attendu.sum())}). "
                "La reconstruction ne mesure pas la production.")


def verifier_holdout(df: pd.DataFrame) -> None:
    """B5 — le hold-out est scelle : sa presence ici invaliderait toute la mesure."""
    if "split" in df.columns and (df["split"] != "train").any():
        raise SystemExit("B5 : des lignes hors 'train' ont ete chargees. Mesure interrompue.")


# ------------------------------------------------------------------ IC et bootstrap par blocs
def blocs_de_dates(dates: pd.Series, taille: int) -> np.ndarray:
    """Numero de bloc de chaque ligne : bloc = fenetre de `taille` bougies 4h, toutes paires.

    Le bloc porte sur la DATE et non sur la ligne : les 4 paires d'une meme fenetre tombent
    dans le meme bloc, ce qui neutralise a la fois le chevauchement des labels (96 h) et la
    correlation entre paires (Q6). Tirer les paires separement les traiterait comme
    independantes, ce qu'elles ne sont pas.
    """
    rang = dates.rank(method="dense").to_numpy() - 1.0
    return (rang // taille).astype(np.int64)


def ic_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """IC de Spearman, NaN si l'echantillon est degenere (une seule valeur de rang)."""
    if len(x) < 2 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    return float(stats.spearmanr(x, y).statistic)


def _stats_par_bloc(x0, x1, y, blocs) -> tuple[np.ndarray, np.ndarray]:
    """Statistiques suffisantes de Pearson, agregees par bloc.

    Un IC de Spearman est un Pearson sur les RANGS. Une fois les rangs poses, la correlation
    d'un rechantillonnage ne depend que de sommes (n, Sx, Sy, Sxy, Sxx, Syy) ADDITIVES par
    bloc. Un replicat se calcule donc en additionnant les blocs tires, sans retrier quoi que
    ce soit : le cout passe de 10 000 tris de 43 000 lignes a 10 000 sommes de ~450 nombres.
    Le resultat est exact, pas approche — c'est la meme formule, factorisee.

    ⚠️ Les rangs sont poses UNE FOIS sur l'echantillon complet, et non recalcules dans chaque
    replicat. C'est la convention du bootstrap de correlation de rang ; re-ranger a chaque
    tirage mesurerait en plus la variabilite du rang lui-meme, qui n'est pas la quantite
    d'interet ici.
    """
    lignes = []
    for b in np.unique(blocs):
        m = blocs == b
        a, c, d = x0[m], x1[m], y[m]
        lignes.append([len(d), a.sum(), c.sum(), d.sum(), (a * d).sum(), (c * d).sum(),
                       (a * a).sum(), (c * c).sum(), (d * d).sum()])
    return np.array(lignes, dtype=np.float64), np.unique(blocs)


def _pearson_depuis_sommes(s: np.ndarray, i_x: int, i_xy: int, i_xx: int) -> np.ndarray:
    """r de Pearson depuis les sommes agregees. `s` : (replicats, 9) colonnes de _stats_par_bloc."""
    n, sx, sy, sxy, sxx, syy = s[:, 0], s[:, i_x], s[:, 3], s[:, i_xy], s[:, i_xx], s[:, 8]
    cov = sxy - sx * sy / n
    var_x = sxx - sx * sx / n
    var_y = syy - sy * sy / n
    with np.errstate(invalid="ignore", divide="ignore"):
        return cov / np.sqrt(var_x * var_y)


def bootstrap_delta_ic(rangs_v0, rangs_v1, rangs_y, blocs, taille, rng) -> dict:
    """IC bootstrap par blocs du Delta IC = IC(V1) - IC(V0), APPARIE.

    Les deux agregats sont tires sur les MEMES blocs a chaque replicat : c'est la difference
    qui est bootstrapee, pas deux IC independants. Un intervalle sur des IC tires separement
    serait bien trop large — les deux variantes partagent la quasi-totalite de leur signal.
    """
    par_bloc, uniques = _stats_par_bloc(rangs_v0, rangs_v1, rangs_y, blocs)
    nb = len(uniques)
    deltas = np.empty(N_BOOT)
    lot = 1000                      # borne memoire : 1000 x nb x 9 flottants a la fois
    for debut in range(0, N_BOOT, lot):
        taille_lot = min(lot, N_BOOT - debut)
        tires = rng.integers(0, nb, size=(taille_lot, nb))
        sommes = par_bloc[tires].sum(axis=1)
        deltas[debut:debut + taille_lot] = (_pearson_depuis_sommes(sommes, 2, 5, 7)
                                            - _pearson_depuis_sommes(sommes, 1, 4, 6))
    reste = (1.0 - IC_NIVEAU) / 2.0
    valides = deltas[~np.isnan(deltas)]
    return {"taille_bloc": taille, "n_blocs": int(nb),
            "ic_bas": float(np.quantile(valides, reste)),
            "ic_haut": float(np.quantile(valides, 1.0 - reste)),
            "p_bootstrap": float(min(1.0, 2.0 * min((valides <= 0).mean(),
                                                    (valides >= 0).mean())))}


def mesurer_ic(df: pd.DataFrame, rng) -> list[dict]:
    """Delta IC de chaque variante candidate contre V0, dans les deux sens."""
    v0 = VARIANTES[0]
    lignes = []
    for sens in _SENS:
        cible_nom = f"y_r_{sens}"
        sous = df[df[cible_nom].notna()]
        cible = sous[cible_nom].to_numpy()
        blocs = blocs_de_dates(sous["ts_utc"], BLOC_BOUGIES)
        agg_v0 = agregat(sous, v0, sens).to_numpy()
        ic_v0 = ic_spearman(agg_v0, cible)
        # Rangs poses une fois : le bootstrap travaille dessus (cf. _stats_par_bloc).
        rangs_y = stats.rankdata(cible)
        rangs_v0 = stats.rankdata(agg_v0)
        for variante in VARIANTES:
            if not variante["candidate"]:
                continue
            agg_v = agregat(sous, variante, sens).to_numpy()
            ic_v = ic_spearman(agg_v, cible)
            rangs_v = stats.rankdata(agg_v)
            boot = bootstrap_delta_ic(rangs_v0, rangs_v, rangs_y, blocs, BLOC_BOUGIES, rng)
            sensibilite = [bootstrap_delta_ic(rangs_v0, rangs_v, rangs_y,
                                              blocs_de_dates(sous["ts_utc"], taille),
                                              taille, rng)
                           for taille in BLOC_SENSIBILITE if taille != BLOC_BOUGIES]
            lignes.append({"test": f"dIC {variante['nom']} - V0 ({sens})", "sens": sens,
                           "variante": variante["nom"], "n": int(len(sous)),
                           "ic_v0": ic_v0, "ic_variante": ic_v, "delta_ic": ic_v - ic_v0,
                           "p_brute": boot["p_bootstrap"],
                           "ic_bas": boot["ic_bas"], "ic_haut": boot["ic_haut"],
                           "exclut_zero": bool(boot["ic_bas"] > 0 or boot["ic_haut"] < 0),
                           "n_blocs": boot["n_blocs"], "sensibilite_blocs": sensibilite})
    return lignes


# --------------------------------------------------------------------- selectivite marginale
def mesurer_marginaux(df: pd.DataFrame, tous: dict[str, dict[str, pd.Series]]) -> list[dict]:
    """E[R] des signaux que V1 perd / gagne par rapport a V0, contre le noyau commun.

    ⚠️ L'emboitement n'est PAS garanti : retirer deux scores peut faire PASSER une ligne dont
    `s_sr`/`s_patterns` tiraient la conviction vers le bas. Perdus et gagnes sont donc deux
    ensembles distincts, mesures separement. Test de Mann-Whitney (rangs) : sur des effectifs
    a deux chiffres, il ne suppose ni normalite ni variance egale.
    """
    lignes = []
    for sens in _SENS:
        v0 = tous["V0_prod"][sens]
        v1 = tous["V1_ablation_renorm"][sens]
        cible = df[f"y_r_{sens}"]
        noyau = cible[v0 & v1].dropna()
        for nom, masque in (("perdus (V0 sans V1)", v0 & ~v1), ("gagnes (V1 sans V0)", v1 & ~v0)):
            marge = cible[masque].dropna()
            p = (float(stats.mannwhitneyu(marge, noyau, alternative="two-sided").pvalue)
                 if len(marge) and len(noyau) else float("nan"))
            mde = (Z_MDE * SIGMA_R_REF / np.sqrt(len(marge) / CHEVAUCHEMENT)
                   if len(marge) else float("nan"))
            ligne = {"test": f"marginaux {nom} ({sens})", "sens": sens, "groupe": nom,
                     "n_marginaux": int(len(marge)), "n_noyau": int(len(noyau)),
                     "er_marginaux": float(marge.mean()) if len(marge) else float("nan"),
                     "er_noyau": float(noyau.mean()) if len(noyau) else float("nan"),
                     "mde": float(mde)}
            # Famille preenregistree : seuls les PERDUS sont testes (2 tests). Les gagnes sont
            # publies en descriptif — les tester gonflerait la famille apres coup.
            if nom.startswith("perdus"):
                ligne["p_brute"] = p
            lignes.append(ligne)
    return lignes


def effectifs(tous: dict[str, dict[str, pd.Series]]) -> list[dict]:
    """Nombre de signaux par variante — la seule mesure ou V3 n'est pas redondant."""
    return [{"variante": v["nom"], "doc": v["doc"],
             "poids": {k: round(p, 4) for k, p in poids_variante(v).items()},
             "somme_poids": round(sum(poids_variante(v).values()), 4),
             **{f"n_{sens}": int(tous[v["nom"]][sens].sum()) for sens in _SENS}}
            for v in VARIANTES]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=pathlib.Path, default=mesures.DB_DEFAUT)
    ap.add_argument("--fdr", type=float, default=FDR_DEFAUT)
    ap.add_argument("--json", type=pathlib.Path,
                    default=REPO / "analysis" / "out" / "ablation_Q4.json")
    args = ap.parse_args()

    protocole = registre.preenregistrement(registre.EXPERIMENTS, EXPERIENCE_ID)   # B6
    print(f"B6 : experience preenregistree le {protocole['date']} "
          f"(famille {protocole['famille_taille']}, essais cumules "
          f"{protocole['n_essais_cumules']})")

    df = mesures.charger(args.db)
    verifier_holdout(df)
    mult = {"long": df["multiplicateur"], "short": multiplicateur_short(df)}
    tous = {v["nom"]: masques(df, v, mult) for v in VARIANTES}
    verifier_fidelite(df, tous["V0_prod"])
    print(f"fidelite V0 : OK ({int(tous['V0_prod']['long'].sum())} long, "
          f"{int(tous['V0_prod']['short'].sum())} short)")

    rng = np.random.default_rng(SEED)
    table_ic = mesurer_ic(df, rng)
    table_marge = mesurer_marginaux(df, tous)

    famille = pd.DataFrame([{"test": lg["test"], "p_brute": lg["p_brute"]}
                            for lg in table_ic + table_marge if "p_brute" in lg])
    famille = mesures.benjamini_hochberg(famille, args.fdr)

    print("\n--- effectifs par variante ---")
    print(pd.DataFrame(effectifs(tous))[["variante", "somme_poids", "n_long", "n_short"]]
          .to_string(index=False))
    print("\n--- Delta IC (metrique primaire) ---")
    print(pd.DataFrame(table_ic)[["test", "n", "ic_v0", "ic_variante", "delta_ic",
                                  "ic_bas", "ic_haut", "exclut_zero"]]
          .round(4).to_string(index=False))
    print("\n--- selectivite marginale (secondaire, sous-puissante) ---")
    print(pd.DataFrame(table_marge)[["test", "n_marginaux", "er_marginaux", "n_noyau",
                                     "er_noyau", "mde"]].round(4).to_string(index=False))
    print(f"\n--- Benjamini-Hochberg (FDR {args.fdr}, famille de {len(famille)}) ---")
    print(famille.round(5).to_string(index=False))

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(
        {"experience": EXPERIENCE_ID, "seuil_amplitude": SEUIL_AMPLITUDE, "fdr": args.fdr,
         "bloc_bougies": BLOC_BOUGIES, "n_boot": N_BOOT, "seed": SEED,
         "effectifs": effectifs(tous), "delta_ic": table_ic, "marginaux": table_marge,
         "benjamini_hochberg": famille.to_dict("records")},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nJSON : {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
