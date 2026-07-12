"""Tests M03 — cio.conviction / explain (docs/modules/M03, PDR 04.3/04.4)."""

import json

import pandas as pd

from arit_lib import cio, contracts, params

SCORE_COLS = ("s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume")


def _scores(value):
    return {col: value for col in SCORE_COLS}


def _df(scores, mult, seuil, regime, rr=2.0, new_4h=True, n=1):
    data = {col: [scores[col]] * n for col in SCORE_COLS}
    data["multiplicateur"] = [mult] * n
    data["seuil"] = [seuil] * n
    data["regime"] = [regime] * n
    data["rr_dispo"] = [rr] * n
    data["new_4h"] = [new_4h] * n
    return pd.DataFrame(data)


def _conv(scores, mult, seuil, regime, rr=2.0, new_4h=True):
    return cio.conviction(_df(scores, mult, seuil, regime, rr=rr, new_4h=new_4h))


def test_weights_sum_to_one():
    assert abs(sum(params.POIDS.values()) - 1.0) < 1e-9


def test_conviction_full_scores_capped_at_one():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] == 1.0


def test_conviction_formula_weighted_by_multiplicateur():
    trend = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert abs(trend["conviction"].iloc[0] - 0.5) < 1e-9  # Σ w·0.5 = 0.5, ×1.0
    reduced = _conv(_scores(0.5), params.MULT_REDUCED, params.SEUIL_TRANSITION, "TRANSITION")
    assert abs(reduced["conviction"].iloc[0] - 0.5 * params.MULT_REDUCED) < 1e-9


def test_conviction_bounded_zero_one():
    rows = [(v, m) for v in params.SCORE_VALUES
            for m in (params.MULT_RISK_OFF, params.MULT_REDUCED, params.MULT_FULL)]
    df = pd.DataFrame({
        **{col: [v for v, _ in rows] for col in SCORE_COLS},
        "multiplicateur": [m for _, m in rows],
        "seuil": [params.SEUIL_TREND] * len(rows),
        "regime": ["TREND"] * len(rows),
        "rr_dispo": [2.0] * len(rows),
        "new_4h": [True] * len(rows),
    })
    out = cio.conviction(df)
    assert (out["conviction"] >= 0.0).all()
    assert (out["conviction"] <= 1.0).all()


def test_signal_at_exact_seuil_uses_ge():
    # conviction == seuil => signal (>=, pas >). On fixe seuil EXACTEMENT a la
    # conviction calculee : robuste au bruit flottant, isole la semantique >=.
    conv = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")["conviction"].iloc[0]
    at_seuil = _conv(_scores(0.5), params.MULT_FULL, conv, "TREND")
    assert at_seuil["conviction"].iloc[0] == conv
    assert bool(at_seuil["signal_long"].iloc[0]) is True


def test_no_signal_just_below_seuil():
    out = _conv(_scores(0.3), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] < params.SEUIL_TREND
    assert bool(out["signal_long"].iloc[0]) is False


def test_multiplicateur_zero_never_signals():
    out = _conv(_scores(1.0), params.MULT_RISK_OFF, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] == 0.0
    assert bool(out["signal_long"].iloc[0]) is False
    risk_off = _conv(_scores(1.0), params.MULT_RISK_OFF, float("nan"), "RISK_OFF")
    assert bool(risk_off["signal_long"].iloc[0]) is False


def test_no_signal_when_regime_not_entry():
    # conviction >= seuil mais regime RANGE (hors ENTRY_REGIMES) => pas de signal.
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "RANGE")
    assert out["conviction"].iloc[0] >= params.SEUIL_TREND
    assert bool(out["signal_long"].iloc[0]) is False


def test_no_signal_when_rr_below_min():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND", rr=params.RR_MIN - 0.1)
    assert bool(out["signal_long"].iloc[0]) is False


def test_no_signal_when_not_new_4h():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND", new_4h=False)
    assert bool(out["signal_long"].iloc[0]) is False


def test_transition_signal_path():
    out = _conv(_scores(1.0), params.MULT_REDUCED, params.SEUIL_TRANSITION, "TRANSITION")
    assert bool(out["signal_long"].iloc[0]) is True


def test_conviction_adds_contract_columns():
    out = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert "conviction" in out.columns
    assert "signal_long" in out.columns
    assert out["signal_long"].dtype == bool


# ------------------------------------------------------------------ explain()

def _full_row(fear_greed=60, macro_stale=False, with_macro=True):
    df = _df(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    df["adx_4h"] = 30.0
    df["ema50_4h"] = 110.0
    df["ema200_4h"] = 100.0
    df["close_4h"] = 115.0
    if with_macro:
        df["fear_greed"] = fear_greed
        df["macro_stale"] = macro_stale
    return cio.conviction(df).iloc[0]


def test_explain_keys_aligned_on_contracts():
    d = cio.explain(_full_row())
    assert set(d["regime_inputs"].keys()) == set(contracts.REGIME_INPUT_KEYS)
    assert set(d["scores"].keys()) == set(contracts.SCORE_KEYS)
    for key in ("regime", "conviction", "seuil", "multiplicateur", "poids", "produit_pondere"):
        assert key in d


def test_explain_is_strict_json_serializable():
    json.dumps(cio.explain(_full_row()), allow_nan=False)


def test_explain_decision_is_reconstructible():
    row = _full_row()
    d = cio.explain(row)
    manual = sum(d["poids"][k] * d["scores"][k] for k in d["scores"])
    assert abs(manual - d["produit_pondere"]) < 1e-9
    recomputed = min(1.0, d["produit_pondere"] * d["multiplicateur"])
    assert abs(recomputed - d["conviction"]) < 1e-9
    assert abs(d["conviction"] - float(row["conviction"])) < 1e-9


def test_explain_surfaces_macro_inputs():
    d = cio.explain(_full_row(fear_greed=30, macro_stale=True))
    assert d["regime_inputs"]["fear_greed"] == 30
    assert d["regime_inputs"]["macro_stale"] is True


def test_explain_macro_absent_is_none():
    d = cio.explain(_full_row(with_macro=False))
    assert d["regime_inputs"]["fear_greed"] is None
    assert d["regime_inputs"]["macro_stale"] is None


def test_explain_close_vs_ema_signed_difference():
    d = cio.explain(_full_row())
    assert abs(d["regime_inputs"]["close_vs_ema"] - (115.0 - 110.0)) < 1e-9


# ------------------------------------- Macro Analyst V1.1 : bump de seuil NEUTRE (04 §4.2)
def _df_macro(scores, mult, seuil, regime, macro, rr=2.0, new_4h=True):
    df = _df(scores, mult, seuil, regime, rr=rr, new_4h=new_4h)
    df[contracts.MACRO_REGIME_COL] = macro
    return df


def test_neutre_column_bumps_seuil():
    out = cio.conviction(
        _df_macro(_scores(0.5), params.MULT_REDUCED, params.SEUIL_TREND, "TREND", "NEUTRE"))
    assert out["seuil"].iloc[0] == params.SEUIL_TREND + params.MACRO_NEUTRE_CONV_BUMP


def test_porteur_column_no_bump():
    out = cio.conviction(
        _df_macro(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND", "PORTEUR"))
    assert out["seuil"].iloc[0] == params.SEUIL_TREND


def test_column_absent_no_bump_backcompat():
    out = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["seuil"].iloc[0] == params.SEUIL_TREND


def test_neutre_bump_can_block_marginal_signal():
    # Conviction pile au seuil de base : PORTEUR passe (>=), NEUTRE (+0,05) bloque.
    conv = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")["conviction"].iloc[0]
    porteur = cio.conviction(_df_macro(_scores(0.5), params.MULT_FULL, conv, "TREND", "PORTEUR"))
    assert bool(porteur["signal_long"].iloc[0]) is True
    neutre = cio.conviction(_df_macro(_scores(0.5), params.MULT_FULL, conv, "TREND", "NEUTRE"))
    assert neutre["seuil"].iloc[0] == conv + params.MACRO_NEUTRE_CONV_BUMP
    assert bool(neutre["signal_long"].iloc[0]) is False
