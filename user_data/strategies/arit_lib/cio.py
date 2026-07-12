"""M03 — CIO : fusion contexte + scores -> conviction (PDR 04.3/04.4, docs/modules/M03).

Fonctions pures. Ajoute `conviction` et `signal_long` (contracts.CIO_COLUMNS) et
fournit `explain` : le dict reconstruisant chaque decision pour le journal
(idee 5, docs/08 — invariant M03.2). Aucun reseau, aucun LLM ; imports internes
limites a contracts/params (docs/11). V2 (FreqAI) remplacera conviction() derriere
la MEME interface (df in -> conviction out) : aucun couplage a l'implementation.
"""

import math

import numpy as np
import pandas as pd

from arit_lib import contracts, params


def conviction(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute `conviction` (float [0,1]) et `signal_long` (bool).

    conviction = min(1, Σ poids·score × multiplicateur)      — formule PDR 04.4.
    signal_long = (conviction >= seuil) & (rr_dispo >= RR_MIN)
                  & (regime ∈ ENTRY_REGIMES) & new_4h         — M03 ; le >= au seuil
    est contractuel. seuil est NaN en RANGE/RISK_OFF => la comparaison vaut False
    (double securite avec le filtre de regime). Poids FIGES depuis params.POIDS.
    """
    weighted = sum(params.POIDS[col] * df[col] for col in params.POIDS)
    df["conviction"] = np.minimum(1.0, weighted * df["multiplicateur"])
    if contracts.MACRO_REGIME_COL in df.columns:  # Macro V1.1 : NEUTRE => seuil +0,05 (04 §4.2)
        neutre = (df[contracts.MACRO_REGIME_COL] == params.MACRO_REGIMES[1]).astype(float)
        df["seuil"] = df["seuil"] + neutre * params.MACRO_NEUTRE_CONV_BUMP
    df["signal_long"] = (
        (df["conviction"] >= df["seuil"])
        & (df["rr_dispo"] >= params.RR_MIN)
        & df["regime"].isin(params.ENTRY_REGIMES)
        & df["new_4h"].astype(bool)
    )
    return df


def _py(value):
    """Scalaire pandas/numpy -> type Python JSON-serialisable strict (NaN -> None)."""
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if math.isnan(number) else number
    return value


def explain(row: pd.Series) -> dict:
    """Dict JSON-serialisable reconstruisant integralement la decision (M03.2, docs/08.1).

    Cles alignees sur contracts.REGIME_INPUT_KEYS (inputs regime) et
    contracts.SCORE_KEYS (scores), + poids appliques, produit pondere (Σ poids·score),
    multiplicateur, seuil, conviction, regime. `fear_greed`/`macro_stale` sont lus de
    la row (injectes par la strategie, docs/11) : None si absents. `close_vs_ema` =
    close_4h - ema50_4h (signe : > 0 => la condition EMA du regime TREND est remplie).
    """
    scores = {key: _py(row.get("s_" + key)) for key in contracts.SCORE_KEYS}
    poids = {key: params.POIDS["s_" + key] for key in contracts.SCORE_KEYS}
    weighted = sum(
        params.POIDS["s_" + key] * float(row["s_" + key])
        for key in contracts.SCORE_KEYS
        if pd.notna(row.get("s_" + key))
    )

    close_4h = row.get("close_4h")
    ema50 = row.get("ema50_4h")
    close_vs_ema = _py(close_4h - ema50) if pd.notna(close_4h) and pd.notna(ema50) else None

    regime_inputs = {
        "adx4h": _py(row.get("adx_4h")),
        "ema50_4h": _py(row.get("ema50_4h")),
        "ema200_4h": _py(row.get("ema200_4h")),
        "close_vs_ema": close_vs_ema,
        "fear_greed": _py(row.get("fear_greed")),
        "macro_stale": _py(row.get("macro_stale")),
    }
    return {
        "regime": _py(row.get("regime")),
        "regime_inputs": regime_inputs,
        "scores": scores,
        "poids": poids,
        "produit_pondere": _py(weighted),
        "multiplicateur": _py(row.get("multiplicateur")),
        "seuil": _py(row.get("seuil")),
        "conviction": _py(row.get("conviction")),
    }
