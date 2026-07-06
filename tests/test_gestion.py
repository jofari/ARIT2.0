"""Tests M05 — arit_lib/gestion.py (G1-G7). Voir docs/modules/M05_gestion.md (tests exiges)."""

import random

import pandas as pd
import pytest

from arit_lib import gestion, params
from arit_lib.contracts import TradeState

T0 = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")


class _Trade:
    """Trade duck-type (protocole gestion.py) : open_rate, stop_loss, amount, open_date_utc."""

    def __init__(self, open_rate=100.0, stop_loss=95.0, amount=1.0, open_date_utc=T0):
        self.open_rate = open_rate
        self.stop_loss = stop_loss
        self.amount = amount
        self.open_date_utc = open_date_utc


def _row(date=T0, close=100.0, high=100.0, low=100.0, atr_1h=1.0, last_hl_1h=0.0,
         choch_bear_1h=False, bos_fresh_4h=False, regime="TREND", nearest_res_4h=999.0):
    """Bougie 1h cloturee (Series, colonnes contractuelles 11.3)."""
    return pd.Series({
        "date": date, "close": close, "high": high, "low": low, "atr_1h": atr_1h,
        "last_hl_1h": last_hl_1h, "choch_bear_1h": choch_bear_1h,
        "bos_fresh_4h": bos_fresh_4h, "regime": regime, "nearest_res_4h": nearest_res_4h,
    })


def _hours(n):
    return T0 + pd.Timedelta(hours=n)


# --------------------------------------------------------------------- r_multiple / flags
def test_r_multiple_sign_and_zero_risk():
    assert gestion.r_multiple(105.0, 100.0, 95.0) == pytest.approx(1.0)
    assert gestion.r_multiple(110.0, 100.0, 95.0) == pytest.approx(2.0)
    assert gestion.r_multiple(95.0, 100.0, 95.0) == pytest.approx(-1.0)
    assert gestion.r_multiple(100.0, 100.0, 95.0) == 0.0
    assert gestion.r_multiple(120.0, 100.0, 100.0) == 0.0  # risque nul -> garde


def test_flags_returns_fresh_copy():
    a = gestion.flags()
    a["G1"] = False
    assert gestion.flags()["G1"] is True
    assert gestion.flags() == dict(params.G_FLAGS_DEFAULT)


# ------------------------------------------------------------------------- MAE / MFE / garde
def test_excursions_mae_mfe_on_constructed_path():
    state = TradeState(initial_sl=95.0)  # entree 100, risque 5
    gestion.update_excursions(state, _row(date=_hours(1), high=110.0, low=98.0), 100.0)
    assert state.mfe_r == pytest.approx(2.0)   # (110-100)/5
    assert state.mae_r == pytest.approx(-0.4)  # (98-100)/5
    gestion.update_excursions(state, _row(date=_hours(2), high=105.0, low=90.0), 100.0)
    assert state.mfe_r == pytest.approx(2.0)   # inchange (105 < 110)
    assert state.mae_r == pytest.approx(-2.0)  # (90-100)/5
    gestion.update_excursions(state, _row(date=_hours(3), high=130.0, low=100.0), 100.0)
    assert state.mfe_r == pytest.approx(6.0)
    assert state.mae_r == pytest.approx(-2.0)


def test_guard_one_action_per_candle():
    state = TradeState(initial_sl=95.0)
    gestion.update_excursions(state, _row(date=_hours(1), high=110.0, low=98.0), 100.0)
    assert state.mfe_r == pytest.approx(2.0)
    assert state.mae_r == pytest.approx(-0.4)
    # meme ts, valeurs bien plus extremes -> garde : no-op
    gestion.update_excursions(state, _row(date=_hours(1), high=200.0, low=50.0), 100.0)
    assert state.mfe_r == pytest.approx(2.0)
    assert state.mae_r == pytest.approx(-0.4)


# ------------------------------------------------------------------------------ compute_sl
def test_g1_break_even_at_exactly_1r():
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    only_g1 = gestion.flags()
    only_g1.update(G2=False, G3=False)
    row = _row(atr_1h=1.0, last_hl_1h=0.0, regime="TREND")
    st = TradeState(initial_sl=95.0, mfe_r=1.0)  # +1,0R exact
    assert gestion.compute_sl(trade, row, st, only_g1) == pytest.approx(100.0 * 1.001)
    st_low = TradeState(initial_sl=95.0, mfe_r=0.999)  # juste sous +1R
    assert gestion.compute_sl(trade, row, st_low, only_g1) is None


def test_g3_trailing_after_1r_and_risk_off_multiplier():
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    only_g3 = gestion.flags()
    only_g3.update(G1=False, G2=False)
    st = TradeState(initial_sl=95.0, mfe_r=1.0)
    row_trend = _row(close=100.0, atr_1h=1.0, regime="TREND", last_hl_1h=0.0)
    assert gestion.compute_sl(trade, row_trend, st, only_g3) == pytest.approx(98.0)   # 100-2.0*1
    row_ro = _row(close=100.0, atr_1h=1.0, regime="RISK_OFF", last_hl_1h=0.0)
    assert gestion.compute_sl(trade, row_ro, st, only_g3) == pytest.approx(98.5)       # 100-1.5*1
    st_low = TradeState(initial_sl=95.0, mfe_r=0.9)  # G3 inactif sous +1R
    assert gestion.compute_sl(trade, row_trend, st_low, only_g3) is None


def test_sl_monotone_over_random_sequence():
    rng = random.Random(20240101)
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    state = TradeState(initial_sl=95.0)
    prev = trade.stop_loss
    for i in range(1, 250):
        close = 100.0 + rng.uniform(-4.0, 14.0)
        row = _row(date=_hours(i), close=close,
                   high=close + rng.uniform(0.0, 4.0),
                   low=close - rng.uniform(0.0, 4.0),
                   atr_1h=rng.uniform(0.5, 2.0),
                   last_hl_1h=close - rng.uniform(0.0, 3.0),
                   regime=rng.choice(("TREND", "RISK_OFF")))
        gestion.update_excursions(state, row, 100.0)
        new_sl = gestion.compute_sl(trade, row, state)
        if new_sl is not None:
            assert new_sl > trade.stop_loss  # ne remonte que strictement
            trade.stop_loss = new_sl
        assert trade.stop_loss >= prev       # jamais descendu
        prev = trade.stop_loss


# ------------------------------------------------------------------------------- partial_tp
def test_g4_fires_once():
    trade = _Trade(amount=2.0, open_rate=100.0)
    st = TradeState(initial_sl=95.0)
    stake = gestion.partial_tp(trade, 1.5, st)
    # PDR 03.4 G4 : 50 % de la QUANTITE -> stake au prix courant, pas au prix d'entree.
    current_rate = trade.open_rate + 1.5 * (trade.open_rate - st.initial_sl)  # 107.5
    assert stake == pytest.approx(-(params.G4_SELL_FRACTION * trade.amount * current_rate))
    # Invariant : le stake vendu converti en coins = 50 % de la quantite.
    assert abs(stake) / current_rate == pytest.approx(params.G4_SELL_FRACTION * trade.amount)
    assert st.tp1_done is True
    assert gestion.partial_tp(trade, 2.0, st) is None  # deja fait


def test_g4_below_trigger_no_fire():
    st = TradeState(initial_sl=95.0)
    assert gestion.partial_tp(_Trade(), 1.49, st) is None
    assert st.tp1_done is False


# --------------------------------------------------------------------------------- check_exit
def test_g6_priority_over_g4_same_candle():
    trade = _Trade()
    st = TradeState(initial_sl=95.0, mfe_r=2.0)  # G4 aurait declenche (>=1,5R)
    row = _row(date=_hours(1), choch_bear_1h=True)
    assert gestion.check_exit(trade, row, st, tp2=None) == "G6"
    # ordre M05 : le caller sort sur G6 avant partial_tp -> G4 jamais joue
    assert st.tp1_done is False


def test_g7_exactly_24_candles():
    trade = _Trade(open_date_utc=T0)
    dead = TradeState(initial_sl=95.0, mfe_r=0.4)  # jamais +0,5R
    assert gestion.check_exit(trade, _row(date=_hours(23)), dead, tp2=None) is None
    assert gestion.check_exit(trade, _row(date=_hours(24)), dead, tp2=None) == "G7"
    alive = TradeState(initial_sl=95.0, mfe_r=0.6)  # a atteint +0,5R
    assert gestion.check_exit(trade, _row(date=_hours(24)), alive, tp2=None) is None


def test_check_exit_priority_order():
    trade = _Trade(open_date_utc=T0)
    # G6 > G7
    st = TradeState(initial_sl=95.0, mfe_r=0.0)
    assert gestion.check_exit(trade, _row(date=_hours(24), choch_bear_1h=True), st, None) == "G6"
    # G7 > TP2
    st2 = TradeState(initial_sl=95.0, mfe_r=0.0, tp1_done=True)
    row2 = _row(date=_hours(24), high=999.0, choch_bear_1h=False)
    assert gestion.check_exit(trade, row2, st2, tp2=100.0) == "G7"


def test_tp2_conditions():
    trade = _Trade(open_date_utc=T0)
    row_hit = _row(date=_hours(1), high=125.0)
    st = TradeState(initial_sl=95.0, tp1_done=True, extension_on=False)
    assert gestion.check_exit(trade, row_hit, st, tp2=120.0) == "TP2"
    st_ext = TradeState(initial_sl=95.0, tp1_done=True, extension_on=True)
    assert gestion.check_exit(trade, row_hit, st_ext, tp2=120.0) is None  # G5 neutralise TP2
    st_notp1 = TradeState(initial_sl=95.0, tp1_done=False)
    assert gestion.check_exit(trade, row_hit, st_notp1, tp2=120.0) is None  # tp1 pas pris
    row_low = _row(date=_hours(1), high=119.0)
    assert gestion.check_exit(trade, row_low, st, tp2=120.0) is None  # high < tp2
    assert gestion.check_exit(trade, row_hit, st, tp2=None) is None     # pas de TP2 defini


def test_g5_flag_controls_tp2_suppression():
    trade = _Trade(open_date_utc=T0)
    row = _row(date=_hours(1), high=125.0, bos_fresh_4h=True)

    def run(fl):
        st = TradeState(initial_sl=95.0, tp1_done=True, extension_on=False)
        # G5 one-liner applique par le caller (M07), respecte le flag
        if fl["G5"] and st.tp1_done and bool(row["bos_fresh_4h"]):
            st.extension_on = True
        return gestion.check_exit(trade, row, st, tp2=120.0, flags=fl)

    on = gestion.flags()
    off = gestion.flags()
    off["G5"] = False
    assert run(on) is None      # G5 on -> extension -> TP2 supprime
    assert run(off) == "TP2"    # G5 off -> inerte -> TP2 declenche


# ------------------------------------------------------------------- ablation : flag off inerte
def test_each_g_flag_off_makes_rule_inert():
    trade = _Trade(open_date_utc=T0)
    off = gestion.flags()
    for k in off:
        off[k] = False
    # G1/G2/G3 off -> aucun SL malgre fort MFE et HL haut
    st = TradeState(initial_sl=95.0, mfe_r=5.0)
    row = _row(date=_hours(1), close=100.0, atr_1h=1.0, last_hl_1h=99.0, regime="TREND")
    assert gestion.compute_sl(trade, row, st, off) is None
    # G4 off
    st4 = TradeState(initial_sl=95.0)
    assert gestion.partial_tp(trade, 3.0, st4, off) is None
    assert st4.tp1_done is False
    # G6 off (malgre choch) + G7 off (malgre age & mfe bas)
    st67 = TradeState(initial_sl=95.0, mfe_r=0.0, tp1_done=False)
    row67 = _row(date=_hours(24), choch_bear_1h=True)
    assert gestion.check_exit(trade, row67, st67, tp2=None, flags=off) is None
