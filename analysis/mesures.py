"""G0 — mesures.py : repond a B1, B9 et B2 sur le dataset produit par `analysis/dataset.py`.

Trois questions, dans cet ordre — chacune ne vaut que si la precedente est repondue :

B1  Modele nul de franchissement de barriere. Quelle est l'esperance d'une entree PRISE AU
    HASARD avec la geometrie du systeme (SL structurel, TP a +1,5R) ? Sans ce chiffre,
    « 36 % de trades gagnants » ne veut rien dire. Mesure sur toutes les evaluations, pas
    sur les trades : c'est ce qui fait passer l'echantillon de 128 a ~43 000.

B9  Contenu informationnel des features. IC de Spearman de chaque feature contre le
    rendement futur ET contre l'issue geometrique. Critere de passage declare dans
    `CHANTIERS.md` : au moins un score avec |IC| >= IC_SEUIL et un signe stable entre les
    deux cibles. En dessous, changer de famille de signal plutot que d'empiler du modele.

B2  Correction de tests multiples (Benjamini-Hochberg). Ce script fait des dizaines de
    tests d'un coup : sans correction, ~5 % des features paraitraient significatives par
    pur hasard. La colonne `signif_BH` est la seule a lire — jamais la p-value brute.

Le hold-out (`split='holdout'`, B5) est EXCLU de tout. Il n'est pas mesure ici, meme pour
regarder : le regarder, c'est le bruler.

Usage :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe analysis/mesures.py
      [--db analysis/out/arit_analyse.sqlite] [--fdr 0.10]
"""

import argparse
import pathlib
import sqlite3
import sys

import numpy as np
import pandas as pd
from scipy import stats

REPO = pathlib.Path(__file__).resolve().parents[1]
DB_DEFAUT = REPO / "analysis" / "out" / "arit_analyse.sqlite"

TP1_R = 1.5              # PDR 03.3 — la cible du systeme, donc l'unite du modele nul
IC_SEUIL = 0.04          # CHANTIERS.md B9 — critere de passage declare AVANT la mesure
FDR_DEFAUT = 0.10        # B2 — taux de fausses decouvertes tolere (Benjamini-Hochberg)
N_MIN = 500              # sous ce N, on n'annonce pas d'IC

CIBLES = ("y_ret_96h", "y_r_long")
FEATURES = ("s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume",
            "s_structure_short", "s_momentum_short", "s_sr_short", "s_patterns_short",
            "s_volume_short", "conviction", "conviction_short", "produit_pondere",
            "adx4h", "rr_dispo", "rr_dispo_short", "trend_dir", "close_vs_ema", "seuil")


def charger(db: pathlib.Path) -> pd.DataFrame:
    if not db.exists():
        raise SystemExit(f"dataset absent : {db} — lancer d'abord analysis/dataset.py")
    try:
        with sqlite3.connect(db) as conn:
            return pd.read_sql("SELECT * FROM evaluations WHERE split='train'", conn)
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        raise SystemExit(f"lecture du dataset impossible : {exc}") from exc


def modele_nul(df: pd.DataFrame, sens: str) -> dict:
    """B1 — issue d'une entree prise au hasard, geometrie du systeme, aucune regle de gestion."""
    issues = df[f"y_issue_{sens}"].dropna()
    n = len(issues)
    if not n:
        return {}
    tp = int((issues == "TP").sum())
    sl = int((issues == "SL").sum())
    return {"n": n, "p_tp": tp / n, "p_sl": sl / n,
            "esperance_r": (tp * TP1_R + sl * -1.0) / n}


def test_filtre(df: pd.DataFrame, sens: str, p_nul: float) -> dict:
    """Le selecteur d'ARIT bat-il le hasard ? Test binomial exact du taux de TP contre p_nul.

    Exact et non normal : n est de l'ordre de la dizaine, l'approximation gaussienne y est
    grossiere — et c'est precisement le regime ou une conclusion hative se fabrique.
    """
    pris = df[df[f"signal_{sens}"] == 1]
    issues = pris[f"y_issue_{sens}"].dropna()
    n = len(issues)
    if not n:
        return {}
    tp = int((issues == "TP").sum())
    sl = int((issues == "SL").sum())
    return {"n": n, "p_tp": tp / n, "esperance_r": (tp * TP1_R + sl * -1.0) / n,
            "p_value": stats.binomtest(tp, n, p_nul, alternative="greater").pvalue}


def ic_table(df: pd.DataFrame) -> pd.DataFrame:
    """B9 — IC de Spearman de chaque (feature, cible). Une ligne = un test, pour B2."""
    lignes = []
    for feature in FEATURES:
        if feature not in df.columns:
            continue
        for cible in CIBLES:
            sub = df[[feature, cible]].dropna()
            if len(sub) < N_MIN or sub[feature].nunique() < 2:
                continue
            ic, p = stats.spearmanr(sub[feature], sub[cible])
            lignes.append({"feature": feature, "cible": cible, "n": len(sub),
                           "ic": ic, "p_brute": p})
    return pd.DataFrame(lignes)


def benjamini_hochberg(table: pd.DataFrame, fdr: float) -> pd.DataFrame:
    """B2 — procedure BH sur la famille de tests de `table`. Ajoute `rang`, `seuil_BH`, `signif_BH`.

    Un test survit si p <= (rang / m) x fdr, m = nombre total de tests de la famille. La
    procedure est appliquee a la famille ENTIERE mesuree dans ce run : appliquer BH a un
    sous-ensemble choisi apres avoir vu les resultats reviendrait a ne pas la faire.
    """
    if table.empty:
        return table
    out = table.sort_values("p_brute").reset_index(drop=True)
    m = len(out)
    out["rang"] = out.index + 1
    out["seuil_BH"] = out["rang"] / m * fdr
    survivants = out.index[out["p_brute"] <= out["seuil_BH"]]
    coupure = survivants.max() if len(survivants) else -1
    out["signif_BH"] = out.index <= coupure
    return out


def stabilite(table: pd.DataFrame) -> pd.DataFrame:
    """Signe de l'IC identique sur les deux cibles ET |IC| >= IC_SEUIL sur au moins une.

    C'est le critere de B9 tel qu'ecrit dans CHANTIERS.md. Le signe stable compte autant que
    l'amplitude : un IC de 0,06 qui change de signe selon la cible ne decrit pas un edge, il
    decrit deux mesures differentes du bruit.
    """
    lignes = []
    for feature, groupe in table.groupby("feature"):
        ics = dict(zip(groupe["cible"], groupe["ic"]))
        signes = {np.sign(v) for v in ics.values() if v == v}
        amplitude_max = max((abs(v) for v in ics.values()), default=0.0)
        tous_signif = bool(groupe["signif_BH"].all())
        lignes.append({
            "feature": feature,
            **{c: ics.get(c) for c in CIBLES},
            "signe_stable": len(signes) == 1,
            "ic_max": amplitude_max,
            "passe_B9": len(signes) == 1 and amplitude_max >= IC_SEUIL and tous_signif,
        })
    return pd.DataFrame(lignes).sort_values("ic_max", ascending=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=pathlib.Path, default=DB_DEFAUT)
    ap.add_argument("--fdr", type=float, default=FDR_DEFAUT)
    args = ap.parse_args()

    df = charger(args.db)
    print(f"train : {len(df)} evaluations · {df['pair'].nunique()} paires · "
          f"holdout EXCLU (B5)\n")

    print("== B1 — modele nul de franchissement (geometrie du systeme, aucune gestion) ==")
    nuls = {}
    for sens in ("long", "short"):
        nul = modele_nul(df, sens)
        if not nul:
            continue
        nuls[sens] = nul
        print(f"  {sens:5s} n={nul['n']:6d}  p(TP)={nul['p_tp']:6.2%}  "
              f"p(SL)={nul['p_sl']:6.2%}  E[R]={nul['esperance_r']:+.4f}")

    print("\n== le selecteur d'ARIT bat-il ce modele nul ? (binomial exact, unilateral) ==")
    for sens, nul in nuls.items():
        res = test_filtre(df, sens, nul["p_tp"])
        if not res:
            print(f"  {sens:5s} aucun signal — non testable")
            continue
        verdict = "significatif" if res["p_value"] < 0.05 else "NON significatif"
        print(f"  {sens:5s} n={res['n']:4d}  p(TP)={res['p_tp']:6.2%} "
              f"(nul {nul['p_tp']:.2%})  E[R]={res['esperance_r']:+.4f}  "
              f"p={res['p_value']:.3f} -> {verdict}")

    print(f"\n== B9 + B2 — IC de Spearman, corrige Benjamini-Hochberg (FDR={args.fdr}) ==")
    table = benjamini_hochberg(ic_table(df), args.fdr)
    if table.empty:
        print("  aucun test exploitable")
        return 0
    print(f"  {len(table)} tests dans la famille · "
          f"{int(table['signif_BH'].sum())} survivent a la correction\n")
    resume = stabilite(table)
    entetes = f"  {'feature':20s}" + "".join(f"{c:>12s}" for c in CIBLES) + \
              f"{'ic_max':>9s}{'signe':>7s}{'B9':>5s}"
    print(entetes)
    for r in resume.itertuples():
        cols = "".join(f"{getattr(r, c):+12.4f}" if getattr(r, c) == getattr(r, c)
                       else f"{'n/a':>12s}" for c in CIBLES)
        print(f"  {r.feature:20s}{cols}{r.ic_max:9.4f}"
              f"{'ok' if r.signe_stable else 'NON':>7s}{'OUI' if r.passe_B9 else '-':>5s}")

    passent = resume[resume["passe_B9"]]["feature"].tolist()
    print(f"\n  critere B9 (|IC| >= {IC_SEUIL}, signe stable, survit a BH) : "
          f"{len(passent)} feature(s) -> {', '.join(passent) if passent else 'AUCUNE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
