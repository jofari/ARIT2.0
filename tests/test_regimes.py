"""Tests M02 — regimes.classify / params_for (docs/modules/M02, PDR 04.1/04.2)."""

import numpy as np
import pandas as pd
import pytest

from arit_lib import contracts, params, regimes


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


# ---------------------------------- Macro Analyst V1.1 : pilotage par MACRO_REGIME_COL
def _df_macro(adx, ema50, ema200, close_4h, macro, n=1):
    df = _df(adx, ema50, ema200, close_4h, n=n)
    df[contracts.MACRO_REGIME_COL] = [macro] * n
    return df


def test_macro_column_hostile_forces_risk_off():
    # Technique = TREND, mais macro HOSTILE => RISK_OFF (04 §4.1 crit.1, absorbe F&G<25).
    out = regimes.classify(_df_macro(30, 110, 100, 115, "HOSTILE"))
    assert out["regime"].iloc[0] == "RISK_OFF"
    assert out["multiplicateur"].iloc[0] == params.MULT_RISK_OFF
    assert np.isnan(out["seuil"].iloc[0])


def test_macro_column_porteur_full_multiplier():
    out = regimes.classify(_df_macro(30, 110, 100, 115, "PORTEUR"))
    assert out["regime"].iloc[0] == "TREND"
    assert out["multiplicateur"].iloc[0] == params.MULT_FULL
    assert out["seuil"].iloc[0] == params.SEUIL_TREND


def test_macro_column_neutre_reduced_multiplier():
    out = regimes.classify(_df_macro(30, 110, 100, 115, "NEUTRE"))
    assert out["regime"].iloc[0] == "TREND"
    assert out["multiplicateur"].iloc[0] == params.MULT_REDUCED
    assert out["seuil"].iloc[0] == params.SEUIL_TREND  # bump +0,05 = job de cio, pas de regimes


def test_macro_column_transition_reduced_even_if_porteur():
    out = regimes.classify(_df_macro(22, 110, 100, 115, "PORTEUR"))
    assert out["regime"].iloc[0] == "TRANSITION"
    assert out["multiplicateur"].iloc[0] == params.MULT_REDUCED  # TRANSITION toujours x0,85


def test_macro_column_absent_behaviour_unchanged():
    # Sans la colonne, classify == comportement historique (neutre backtest) : retrocompat.
    out = regimes.classify(_df(30, 110, 100, 115), None)
    assert out["regime"].iloc[0] == "TREND"
    assert out["multiplicateur"].iloc[0] == params.MULT_FULL


def test_attach_macro_regime_point_in_time_backward():
    # daily deja decale +1 j (index = jour ou le regime devient valide) ; aucun look-ahead.
    daily = pd.DataFrame(
        {contracts.MACRO_REGIME_COL: ["NEUTRE", "HOSTILE"]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"], utc=True),
    )
    candles = pd.DataFrame({
        "date": pd.date_range("2024-01-02", periods=48, freq="1h", tz="UTC"),
        "close": range(48),
    })
    out = regimes.attach_macro_regime(candles.copy(), daily)
    col = out.set_index("date")[contracts.MACRO_REGIME_COL]
    assert col.loc["2024-01-02 05:00"] == "NEUTRE"          # jour J => regime d'index J (<= J-1)
    assert col.loc["2024-01-03 05:00"] == "HOSTILE"         # jamais la valeur d'un jour futur


def test_attach_macro_regime_mixed_datetime_units():
    # Regression 13/07 : les feather freqtrade livrent date en datetime64[ms, UTC], l'index
    # macro en [ns] — merge_asof refusait le melange => exception avalee => ZERO trade.
    daily = pd.DataFrame(
        {contracts.MACRO_REGIME_COL: ["PORTEUR"]},
        index=pd.to_datetime(["2024-01-01"], utc=True).as_unit("ns"),
    )
    candles = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=24, freq="1h", tz="UTC").as_unit("ms"),
        "close": range(24),
    })
    out = regimes.attach_macro_regime(candles.copy(), daily)   # ne doit PAS lever
    assert (out[contracts.MACRO_REGIME_COL] == "PORTEUR").all()


def test_attach_macro_regime_before_first_day_is_nan():
    daily = pd.DataFrame(
        {contracts.MACRO_REGIME_COL: ["PORTEUR"]},
        index=pd.to_datetime(["2024-01-05"], utc=True),
    )
    candles = pd.DataFrame({
        "date": pd.date_range("2024-01-03", periods=24, freq="1h", tz="UTC"),
        "close": range(24),
    })
    out = regimes.attach_macro_regime(candles.copy(), daily)
    assert out[contracts.MACRO_REGIME_COL].isna().all()     # avant la 1re date => pas de regime


def test_attach_macro_regime_empty_daily_is_noop():
    candles = pd.DataFrame({"date": pd.date_range("2024-01-03", periods=3, freq="1h", tz="UTC")})
    out = regimes.attach_macro_regime(candles.copy(), pd.DataFrame())
    assert contracts.MACRO_REGIME_COL not in out.columns    # retrocompat : colonne non posee


# ------------------------- Bloc correlation actions c6/c7 (docs/06 §6.2.1, A4 du 03/08)
def test_equity_veto_force_risk_off_meme_en_macro_porteur():
    """Le veto actions est SEPARE de la somme des 5 composants : il bloque meme un PORTEUR."""
    df = _df_macro(30, 110, 100, 115, "PORTEUR")
    df[contracts.EQUITY_VETO_COL] = [True]
    out = regimes.classify(df)
    assert out["regime"].iloc[0] == "RISK_OFF"
    assert out["multiplicateur"].iloc[0] == params.MULT_RISK_OFF


def test_equity_veto_faux_ne_change_rien():
    df = _df_macro(30, 110, 100, 115, "PORTEUR")
    df[contracts.EQUITY_VETO_COL] = [False]
    out = regimes.classify(df)
    assert out["regime"].iloc[0] == "TREND"
    assert out["multiplicateur"].iloc[0] == params.MULT_FULL


def test_equity_veto_colonne_absente_est_retrocompatible():
    """Backtest sans indice actions : le bloc est inoperant, la decision est inchangee."""
    out = regimes.classify(_df_macro(30, 110, 100, 115, "PORTEUR"))
    assert out["regime"].iloc[0] == "TREND"


def test_attach_pose_aussi_les_colonnes_du_bloc_correlation():
    daily = pd.DataFrame(
        {contracts.MACRO_REGIME_COL: ["NEUTRE"],
         contracts.EQUITY_VETO_COL: [True],
         contracts.EQUITY_VETO_REASON_COL: [contracts.EQUITY_VETO_BINDING]},
        index=pd.to_datetime(["2024-01-01"], utc=True))
    df = pd.DataFrame({"date": pd.date_range("2024-01-02", periods=2, freq="1h", tz="UTC")})
    out = regimes.attach_macro_regime(df, daily)
    assert out[contracts.EQUITY_VETO_COL].all()
    assert (out[contracts.EQUITY_VETO_REASON_COL] == contracts.EQUITY_VETO_BINDING).all()
