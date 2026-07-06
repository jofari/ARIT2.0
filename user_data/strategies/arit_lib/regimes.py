"""M02 — Classification de regime de marche (PDR 04.1/04.2, docs/modules/M02).

Fonctions pures : DataFrame in -> DataFrame + colonnes contractuelles `regime`,
`seuil`, `multiplicateur` (contracts.REGIME_COLUMNS). Aucun reseau, aucun LLM,
aucun import d'un autre module arit_lib (contracts/params seulement, docs/11).

Idee 8 de Jonas (docs/04) : la fonda ne pese jamais dans une somme, elle FIXE le
regime, le seuil d'entree et le multiplicateur de conviction.
"""

import pandas as pd

from arit_lib import params

# Table ordonnee = miroir exact du PDR 04.1 : le premier predicat vrai gagne, la
# derniere regle (fallback RANGE) matche toujours (ADX fort mais contexte non
# haussier => pas de continuation long en spot). Bornes issues de params
# (docs/README interdit n4). r = df (colonnes Series), m = macro (dict scalaire,
# constant sur le df — docs/04). RISK_OFF est scalaire (macro) => tout ou rien.
REGLES = (
    (
        "RISK_OFF",
        lambda r, m: m["risk_off"] or m["stale"] or m["fear_greed"] < params.FG_RISK_OFF_BELOW,
    ),
    ("RANGE", lambda r, m: r["adx_4h"] < params.ADX_RANGE_BELOW),
    ("TRANSITION", lambda r, m: r["adx_4h"] < params.ADX_TREND_MIN),
    (
        "TREND",
        lambda r, m: (r["ema50_4h"] > r["ema200_4h"]) & (r["close_4h"] > r["ema50_4h"]),
    ),
    ("RANGE", lambda r, m: True),  # fallback
)


def params_for(regime: str, fear_greed: int) -> tuple[float, float]:
    """(seuil, multiplicateur) d'un regime — table PDR 04.2.

    seuil : TREND/TRANSITION depuis params, NaN sinon (RANGE/RISK_OFF = pas d'entree).
    multiplicateur ∈ {MULT_FULL, MULT_REDUCED, MULT_RISK_OFF} : TREND depend de F&G
    (>= FG_MULT_FULL_FROM => plein, sinon reduit), TRANSITION toujours reduit,
    RANGE/RISK_OFF sans engagement (x0 — "—" du tableau 04.2, veto d'entree).
    """
    if regime == "TREND":
        mult = params.MULT_FULL if fear_greed >= params.FG_MULT_FULL_FROM else params.MULT_REDUCED
        return params.SEUIL_TREND, mult
    if regime == "TRANSITION":
        return params.SEUIL_TRANSITION, params.MULT_REDUCED
    return float("nan"), params.MULT_RISK_OFF


def classify(df: pd.DataFrame, macro: dict | None = None) -> pd.DataFrame:
    """Ajoute `regime`, `seuil`, `multiplicateur` (contracts.REGIME_COLUMNS).

    `macro` = dict schema PDR 06.3 (cles utilisees : risk_off, fear_greed, stale).
    `macro=None` => neutre : limitation backtest documentee (PDR M02, macro
    historique indisponible ; les vetos F&G/news sont mesures en dry-run).

    Invariant PDR 04.2 / M02.1 : un changement de regime ne ferme JAMAIS une
    position (seules G1-G7 sortent). Cette fonction ne cree QUE ses 3 colonnes.
    """
    if macro is None:
        # Neutre backtest (PDR M02) : ni risk_off ni stale, F&G neutre
        # (>= FG_MULT_FULL_FROM => multiplicateur plein en TREND).
        macro = {"risk_off": False, "fear_greed": params.FG_NEUTRAL_BACKTEST, "stale": False}

    regime = pd.Series(index=df.index, dtype=object)
    remaining = pd.Series(True, index=df.index)
    for name, predicate in REGLES:
        mask = predicate(df, macro)
        if not isinstance(mask, pd.Series):  # predicat scalaire (RISK_OFF, fallback)
            mask = pd.Series(bool(mask), index=df.index)
        take = remaining & mask.fillna(False)  # NaN warm-up => predicat faux (fail-safe)
        regime.loc[take] = name
        remaining.loc[take] = False

    fear_greed = macro["fear_greed"]
    resolved = {reg: params_for(reg, fear_greed) for reg in regime.dropna().unique()}
    df["regime"] = regime
    df["seuil"] = regime.map({reg: sm[0] for reg, sm in resolved.items()})
    df["multiplicateur"] = regime.map({reg: sm[1] for reg, sm in resolved.items()})
    return df
