r"""Decompte DESCRIPTIF des variantes de la regle de direction (A2-quater / A2-sexies).

CE N'EST PAS UNE EXPERIENCE au sens de B6 : aucune hypothese, aucune p-value, aucun
verdict, aucune correction de tests multiples. On compte combien de signaux chaque
cablage laisse passer sur le train, et on affiche le R moyen des groupes obtenus a titre
DESCRIPTIF — les N sont de l'ordre de la dizaine, tout ecart y est indecidable (MDE de
l'ordre du R entier, cf. analysis/mesures.py). Toute conclusion tiree de ces R moyens
exige un preenregistrement prealable (analysis/registre.py).

Hold-out B5 jamais lu : la requete filtre split='train'.

Lancement :
    & C:\Users\jofar\venvs\arit\Scripts\python.exe research/regle_direction/compte_variantes.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

# Miroir de params.py (le script tourne hors du venv freqtrade : pas d'import arit_lib).
RR_MIN = 1.5
ENTRY_REGIMES = ("TREND", "TRANSITION")
PORTEUR, NEUTRE, HOSTILE = "PORTEUR", "NEUTRE", "HOSTILE"
VETO_STALE = "equity_veto_stale"
DB = Path(__file__).resolve().parents[2] / "analysis" / "out" / "arit_analyse.sqlite"


def charger(db: Path = DB) -> pd.DataFrame:
    with sqlite3.connect(db) as con:
        return pd.read_sql("select * from evaluations where split='train'", con)


def portes_techniques(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Le signal technique SANS la porte macro : conviction, RR, regime, sens de tendance."""
    tradable = df["regime"].isin(ENTRY_REGIMES)
    long_ = (tradable & (df["conviction"] >= df["seuil"])
             & (df["rr_dispo"] >= RR_MIN) & (df["trend_dir"] >= 0))
    short = (tradable & (df["conviction_short"] >= df["seuil"])
             & (df["rr_dispo_short"] >= RR_MIN) & (df["trend_dir"] <= 0))
    return long_, short


def veto_directionnel(df: pd.DataFrame) -> pd.Series:
    """Veto actions c6/c7 hors donnee perimee — celui qu'A2-quater a rendu directionnel."""
    return df["equity_veto"].fillna(0).astype(bool) & (df["equity_veto_reason"] != VETO_STALE)


def variantes(df: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    """(autorise_long, autorise_short) par cablage. Le nom est celui de DECISIONS.md."""
    macro, veto = df["macro_regime"], veto_directionnel(df)

    direction = pd.Series("long", index=df.index)          # NaN/inconnu => fail-safe long
    direction[macro == HOSTILE] = "short"
    direction[macro == NEUTRE] = "both"
    v0 = direction.mask(veto & (direction == "long"), "none")
    v0 = v0.mask(veto & (v0 == "both"), "short")

    v0bis = direction.mask(veto, "none")                   # avant A2-quater : coupe-circuit

    degrade = macro.mask(veto & (macro == PORTEUR), NEUTRE).mask(veto & (macro == NEUTRE), HOSTILE)
    force = macro.mask(veto, HOSTILE)

    return {
        "V0  production (A2-quater)": (v0.isin(("long", "both")), v0.isin(("short", "both"))),
        "V0b avant A2-quater (coupe-circuit)": (v0bis.isin(("long", "both")),
                                                v0bis.isin(("short", "both"))),
        "V1  concordance stricte (NEUTRE = rien)": (macro == PORTEUR, macro == HOSTILE),
        "V2  concordance + veto degrade d'un cran": (degrade == PORTEUR, degrade == HOSTILE),
        "V3  concordance + veto force HOSTILE": (force == PORTEUR, force == HOSTILE),
        "V4  concordance, NEUTRE garde les deux": (macro.isin((PORTEUR, NEUTRE)),
                                                   macro.isin((HOSTILE, NEUTRE))),
    }


def _ligne(nom: str, df: pd.DataFrame, longs: pd.Series, shorts: pd.Series) -> str:
    r_l = df.loc[longs, "y_r_long"].mean() if longs.any() else float("nan")
    r_s = df.loc[shorts, "y_r_short"].mean() if shorts.any() else float("nan")
    return (f"{nom:<42} long {longs.sum():>3} (R {r_l:+.4f}) · "
            f"short {shorts.sum():>3} (R {r_s:+.4f}) · total {longs.sum() + shorts.sum():>3}")


def main() -> None:
    df = charger()
    tech_l, tech_s = portes_techniques(df)
    print(f"train : {len(df)} evaluations")
    print(f"technique seule (macro ignoree) : long {tech_l.sum()} · short {tech_s.sum()}\n")
    for nom, (dir_l, dir_s) in variantes(df).items():
        print(_ligne(nom, df, tech_l & dir_l, tech_s & dir_s))

    print("\nou passent les signaux techniques, par regime macro :")
    for regime in (PORTEUR, NEUTRE, HOSTILE):
        masque = df["macro_regime"] == regime
        longs, shorts = tech_l & masque, tech_s & masque
        r_l = df.loc[longs, "y_r_long"].mean() if longs.any() else float("nan")
        r_s = df.loc[shorts, "y_r_short"].mean() if shorts.any() else float("nan")
        print(f"  {regime:<8} lignes {masque.sum():>6} · long {longs.sum():>2} (R {r_l:+.4f})"
              f" · short {shorts.sum():>2} (R {r_s:+.4f})")
    veto = veto_directionnel(df)
    print(f"  veto directionnel actif : {veto.sum()} lignes · signaux techniques dessous : "
          f"long {(tech_l & veto).sum()} · short {(tech_s & veto).sum()}")


if __name__ == "__main__":
    main()
