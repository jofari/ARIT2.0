"""M02 — Classification de regime de marche (PDR 04.1/04.2, docs/modules/M02).

Fonctions pures : DataFrame in -> DataFrame + colonnes contractuelles `regime`,
`seuil`, `multiplicateur` (contracts.REGIME_COLUMNS). Aucun reseau, aucun LLM,
aucun import d'un autre module arit_lib (contracts/params seulement, docs/11).

Idee 8 de Jonas (docs/04) : la fonda ne pese jamais dans une somme, elle FIXE le
regime, le seuil d'entree et le multiplicateur de conviction.
"""

import pandas as pd

from arit_lib import contracts, params

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

# Macro Analyst V1.1 (06.2) : aliases lisibles des valeurs de params.MACRO_REGIMES.
_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES


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


def _regime_series(df: pd.DataFrame, macro: dict) -> pd.Series:
    """Applique la table REGLES (premier predicat vrai gagne) -> Series regime."""
    regime = pd.Series(index=df.index, dtype=object)
    remaining = pd.Series(True, index=df.index)
    for name, predicate in REGLES:
        mask = predicate(df, macro)
        if not isinstance(mask, pd.Series):  # predicat scalaire (RISK_OFF, fallback)
            mask = pd.Series(bool(mask), index=df.index)
        take = remaining & mask.fillna(False)  # NaN warm-up => predicat faux (fail-safe)
        regime.loc[take] = name
        remaining.loc[take] = False
    return regime


def classify(df: pd.DataFrame, macro: dict | None = None) -> pd.DataFrame:
    """Ajoute `regime`, `seuil`, `multiplicateur` (contracts.REGIME_COLUMNS).

    Si `contracts.MACRO_REGIME_COL` est present (backtest, Macro Analyst V1.1) il PILOTE
    la fonda : HOSTILE => RISK_OFF (04 §4.1 crit.1, absorbe F&G<25), PORTEUR => x1,0,
    NEUTRE => x0,85 (remplace la logique F&G). Sinon, comportement historique : `macro` =
    dict PDR 06.3 (risk_off/fear_greed/stale) ; None => neutre backtest documente (M02).

    Invariant PDR 04.2 / M02.1 : un changement de regime ne ferme JAMAIS une position
    (seules G1-G7 sortent). Cette fonction ne cree QUE ses 3 colonnes.
    """
    if contracts.MACRO_REGIME_COL in df.columns:
        return _classify_macro(df)
    if macro is None:
        # Neutre backtest (PDR M02) : ni risk_off ni stale, F&G neutre (=> mult plein en TREND).
        macro = {"risk_off": False, "fear_greed": params.FG_NEUTRAL_BACKTEST, "stale": False}
    regime = _regime_series(df, macro)
    fear_greed = macro["fear_greed"]
    resolved = {reg: params_for(reg, fear_greed) for reg in regime.dropna().unique()}
    df["regime"] = regime
    df["seuil"] = regime.map({reg: sm[0] for reg, sm in resolved.items()})
    df["multiplicateur"] = regime.map({reg: sm[1] for reg, sm in resolved.items()})
    return df


def _classify_macro(df: pd.DataFrame) -> pd.DataFrame:
    """Regime pilote par la colonne macro (backtest). Le +0,05 de seuil NEUTRE est applique
    par cio (04 §4.2). Retrocompat : sans la colonne, classify() reste inchange."""
    neutral = {"risk_off": False, "fear_greed": params.FG_NEUTRAL_BACKTEST, "stale": False}
    regime = _regime_series(df, neutral)                    # technique seule (RISK_OFF neutralise)
    macro_col = df[contracts.MACRO_REGIME_COL]
    regime = regime.mask(macro_col == _HOSTILE, "RISK_OFF")  # veto macro (absorbe F&G<25)
    is_trend = regime == "TREND"
    porteur = macro_col == _PORTEUR
    mult = pd.Series(params.MULT_RISK_OFF, index=df.index, dtype=float)  # RANGE/RISK_OFF => x0
    mult = mult.mask(regime == "TRANSITION", params.MULT_REDUCED)        # TRANSITION toujours x0,85
    mult = mult.mask(is_trend & porteur, params.MULT_FULL)
    mult = mult.mask(is_trend & ~porteur, params.MULT_REDUCED)           # TREND+NEUTRE/NaN => x0,85
    df["regime"] = regime
    df["seuil"] = regime.map({"TREND": params.SEUIL_TREND,
                              "TRANSITION": params.SEUIL_TRANSITION}).astype(float)
    df["multiplicateur"] = mult
    return df


def attach_macro_regime(df: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Pose contracts.MACRO_REGIME_COL sur les bougies (jointure point-in-time par jour).

    `daily` = sortie macro_regime.daily_regimes (index DatetimeIndex, deja decale +1 j).
    Chaque bougie prend le regime du dernier jour <= sa date (merge_asof backward, day
    floor) : aucun look-ahead (le regime du jour J est calcule sur <= J-1). `daily` vide
    => colonne non posee, classify() retombe sur le neutre (retrocompatibilite totale).
    """
    if daily is None or len(daily) == 0 or contracts.MACRO_REGIME_COL not in daily.columns:
        return df
    right = pd.DataFrame({
        "date": pd.to_datetime(daily.index, utc=True).floor("D"),
        contracts.MACRO_REGIME_COL: daily[contracts.MACRO_REGIME_COL].to_numpy(),
    }).sort_values("date").reset_index(drop=True)
    left = df.copy()
    left["date"] = pd.to_datetime(left["date"], utc=True)
    ordered = left.sort_values("date")
    merged = pd.merge_asof(ordered[["date"]], right, on="date", direction="backward")
    merged.index = ordered.index
    df[contracts.MACRO_REGIME_COL] = merged[contracts.MACRO_REGIME_COL].reindex(df.index).to_numpy()
    return df
