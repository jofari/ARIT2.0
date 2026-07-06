"""Tests M02 — regimes.classify / params_for (docs/modules/M02, PDR 04.1/04.2)."""

import numpy as np
import pandas as pd
import pytest

from arit_lib import params, regimes


def _df(adx, ema50, ema200, close_4h, n=1):
    return pd.DataFrame({
        "adx_4h": [adx] * n,
        "ema50_4h": [ema50] * n,
        "ema200_4h": [ema200] * n,
        "close_4h": [close_4h] * n,
    })


def _macro(risk_off=False, fear_greed=60, stale=False):
    return {"risk_off": risk_off, "fear_greed": fear_greed, "stale": stale}


@pytest.mark.parametrize("adx,ema50,ema200,close_4h,expected", [
    (15, 110, 100, 115, "RANGE"),        # ADX < 20
    (22, 110, 100, 115, "TRANSITION"),   # 20 <= ADX < 25
    (30, 110, 100, 115, "TREND"),        # ADX >= 25 + EMA haussier + close_4h > EMA50
    (30, 90, 100, 115, "RANGE"),         # ADX fort mais EMA50 < EMA200 -> fallback
    (30, 110, 100, 105, "RANGE"),        # ADX fort, EMA ok, mais close_4h < EMA50 -> fallback
])
def test_regime_branches(adx, ema50, ema200, close_4h, expected):
    out = regimes.classify(_df(adx, ema50, ema200, close_4h), _macro())
    assert out["regime"].iloc[0] == expected


def test_regime_vectorized_multirow():
    df = pd.DataFrame({
        "adx_4h":    [15, 22, 30, 30],
        "ema50_4h":  [110, 110, 110, 90],
        "ema200_4h": [100, 100, 100, 100],
        "close_4h":  [115, 115, 115, 115],
    })
    out = regimes.classify(df, _macro())
    assert list(out["regime"]) == ["RANGE", "TRANSITION", "TREND", "RANGE"]


def test_risk_off_priority_beats_trend_via_flag():
    out = regimes.classify(_df(30, 110, 100, 115), _macro(risk_off=True))
    assert out["regime"].iloc[0] == "RISK_OFF"
    assert out["multiplicateur"].iloc[0] == params.MULT_RISK_OFF
    assert np.isnan(out["seuil"].iloc[0])


def test_risk_off_via_fear_greed():
    out = regimes.classify(_df(30, 110, 100, 115), _macro(fear_greed=20))
    assert out["regime"].iloc[0] == "RISK_OFF"


def test_stale_implies_risk_off():
    out = regimes.classify(_df(30, 110, 100, 115), _macro(stale=True))
    assert out["regime"].iloc[0] == "RISK_OFF"
    assert out["multiplicateur"].iloc[0] == params.MULT_RISK_OFF


def test_trend_multiplicateur_full_and_reduced():
    full = regimes.classify(_df(30, 110, 100, 115), _macro(fear_greed=45))
    assert full["multiplicateur"].iloc[0] == params.MULT_FULL
    assert full["seuil"].iloc[0] == params.SEUIL_TREND
    reduced = regimes.classify(_df(30, 110, 100, 115), _macro(fear_greed=30))
    assert reduced["multiplicateur"].iloc[0] == params.MULT_REDUCED
    assert reduced["seuil"].iloc[0] == params.SEUIL_TREND


def test_transition_multiplicateur_always_reduced():
    out = regimes.classify(_df(22, 110, 100, 115), _macro(fear_greed=90))
    assert out["multiplicateur"].iloc[0] == params.MULT_REDUCED
    assert out["seuil"].iloc[0] == params.SEUIL_TRANSITION


def test_range_seuil_nan_mult_zero():
    out = regimes.classify(_df(15, 110, 100, 115), _macro())
    assert np.isnan(out["seuil"].iloc[0])
    assert out["multiplicateur"].iloc[0] == params.MULT_RISK_OFF


def test_params_for_matches_pdr_table():
    assert regimes.params_for("TREND", 60) == (params.SEUIL_TREND, params.MULT_FULL)
    assert regimes.params_for("TREND", 30) == (params.SEUIL_TREND, params.MULT_REDUCED)
    assert regimes.params_for("TRANSITION", 90) == (params.SEUIL_TRANSITION, params.MULT_REDUCED)
    for regime in ("RANGE", "RISK_OFF"):
        seuil, mult = regimes.params_for(regime, 60)
        assert np.isnan(seuil)
        assert mult == params.MULT_RISK_OFF


def test_macro_none_is_neutral_backtest():
    trend = regimes.classify(_df(30, 110, 100, 115), None)
    assert trend["regime"].iloc[0] == "TREND"
    assert trend["multiplicateur"].iloc[0] == params.MULT_FULL  # F&G neutre => plein
    rng = regimes.classify(_df(15, 110, 100, 115), None)
    assert rng["regime"].iloc[0] == "RANGE"


def test_classify_only_touches_three_columns_across_regime_change():
    df = _df(30, 110, 100, 115)
    df["preexisting"] = 7
    before = set(df.columns)
    df = regimes.classify(df, _macro(fear_greed=60))
    assert set(df.columns) - before == {"regime", "seuil", "multiplicateur"}
    assert df["regime"].iloc[0] == "TREND"

    frozen = set(df.columns)
    df = regimes.classify(df, _macro(risk_off=True))  # changement de regime
    assert set(df.columns) == frozen                  # aucune colonne creee en plus
    assert df["regime"].iloc[0] == "RISK_OFF"
    for forbidden in ("exit_long", "enter_long", "sell", "close_position", "exit"):
        assert forbidden not in df.columns
    assert df["preexisting"].iloc[0] == 7             # donnees hors-regime intactes
