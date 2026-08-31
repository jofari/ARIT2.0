"""Tests M05 — arit_lib/gestion.py (G1-G7). Voir docs/modules/M05_gestion.md (tests exiges)."""

import pathlib
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
         choch_bear_1h=False, choch_bear_event_1h=False, bos_fresh_4h=False,
         bos_fresh_bear_4h=False, regime="TREND", nearest_res_4h=999.0):
    """Bougie 1h cloturee (Series, colonnes contractuelles 11.3).

    G6 lit choch_bear_event_1h (EVENEMENT de cassure, decision Jonas 10/07) ; choch_bear_1h
    reste l'etat persistant journalise mais n'est plus decisionnel pour la sortie.
    """
    return pd.Series({
        "date": date, "close": close, "high": high, "low": low, "atr_1h": atr_1h,
        "last_hl_1h": last_hl_1h, "choch_bear_1h": choch_bear_1h,
        "choch_bear_event_1h": choch_bear_event_1h,
        "bos_fresh_4h": bos_fresh_4h, "bos_fresh_bear_4h": bos_fresh_bear_4h,
        "regime": regime, "nearest_res_4h": nearest_res_4h,
    })


def _hours(n):
    return T0 + pd.Timedelta(hours=n)


# --------------------------------------------------------------- initial_levels (PDR 03.3)
def test_initial_levels_hl_based():
    sl, tp1, tp2 = gestion.initial_levels(100.0, 95.0, 2.0, 130.0)
    assert sl == pytest.approx(95.0 - params.SL_HL_ATR_BUFFER * 2.0)      # HL 4h - 0,1xATR
    assert tp1 == pytest.approx(100.0 + params.TP1_R * (100.0 - sl))      # TP1 +1,5R
    assert tp2 == 130.0                                                   # resistance > TP1


def test_initial_levels_fallback_when_hl_above_entry():
    sl, tp1, tp2 = gestion.initial_levels(100.0, 105.0, 2.0, float("nan"))
    assert sl == pytest.approx(100.0 - params.SL_FALLBACK_ATR_MULT * 2.0)  # fallback entry-1,5xATR
    assert tp2 is None


def test_initial_levels_hl_none_and_res_below_tp1():
    sl, tp1, tp2 = gestion.initial_levels(100.0, None, 2.0, 100.5)
    assert sl == pytest.approx(100.0 - params.SL_FALLBACK_ATR_MULT * 2.0)  # HL absent -> fallback
    assert tp2 is None                                                    # resistance <= TP1


def test_initial_levels_atr_nan_gives_nan_sl():
    sl, _tp1, _tp2 = gestion.initial_levels(100.0, 95.0, float("nan"), 130.0)
    assert sl != sl                                                       # NaN -> le caller skip


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
def test_g6_event_not_state_and_priority_over_g4():
    trade = _Trade()
    st = TradeState(initial_sl=95.0, mfe_r=2.0)  # G4 aurait declenche (>=1,5R)
    # decision Jonas 10/07 : G6 = EVENEMENT de cassure. Etat present mais pas d'evenement
    # (cassure a une bougie anterieure, etat qui persiste) => AUCUNE sortie.
    persist = _row(date=_hours(1), choch_bear_1h=True, choch_bear_event_1h=False)
    assert gestion.check_exit(trade, persist, st, tp2=None) is None
    # Bougie de cassure (event True) => G6, prioritaire sur G4.
    row = _row(date=_hours(1), choch_bear_1h=True, choch_bear_event_1h=True)
    assert gestion.check_exit(trade, row, st, tp2=None) == "G6"
    # ordre M05 : le caller sort sur G6 avant partial_tp -> G4 jamais joue
    assert st.tp1_done is False


def test_g6_only_counts_after_entry_candle():
    # docs/03 §3.4 amendement 2026-07-10 : la cassure ne compte que PENDANT LA VIE du trade.
    # Fill a T0+30min : la bougie 1h qui le CONTIENT ouvre a T0 (date < open_date_utc) => exclue,
    # sinon la cassure (anterieure au fill de quelques minutes) sortirait a t+0.
    st = TradeState(initial_sl=95.0, mfe_r=0.0)
    trade = _Trade(open_date_utc=T0 + pd.Timedelta(minutes=30))
    entry_candle = _row(date=T0, choch_bear_event_1h=True)
    assert gestion.check_exit(trade, entry_candle, st, tp2=None) is None
    later = _row(date=_hours(1), choch_bear_event_1h=True)   # bougie entierement posterieure
    assert gestion.check_exit(trade, later, st, tp2=None) == "G6"


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
    g6row = _row(date=_hours(24), choch_bear_event_1h=True)
    assert gestion.check_exit(trade, g6row, st, None) == "G6"
    # G7 > TP2
    st2 = TradeState(initial_sl=95.0, mfe_r=0.0, tp1_done=True)
    row2 = _row(date=_hours(24), high=999.0, choch_bear_event_1h=False)
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
    # G6 off (malgre event de cassure) + G7 off (malgre age & mfe bas)
    st67 = TradeState(initial_sl=95.0, mfe_r=0.0, tp1_done=False)
    row67 = _row(date=_hours(24), choch_bear_1h=True, choch_bear_event_1h=True)
    assert gestion.check_exit(trade, row67, st67, tp2=None, flags=off) is None


# ---------------------------------------------------- MODE CONTROLE A (PDR 09 §9.1.1)
def test_control_a_total_exit_at_exactly_1_5r(monkeypatch):
    monkeypatch.setattr(params, "CONTROL_A_MODE", True)
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    st = TradeState(initial_sl=95.0)
    tp = 100.0 + params.TP1_R * (100.0 - 95.0)          # +1,5R = 107.5
    assert gestion.check_exit(trade, _row(high=tp), st, tp2=None) == "TP_CONTROL_A"
    assert gestion.check_exit(trade, _row(high=tp - 0.01), st, tp2=None) is None  # juste sous


def test_control_a_sl_frozen_and_grules_inert(monkeypatch):
    monkeypatch.setattr(params, "CONTROL_A_MODE", True)
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    st = TradeState(initial_sl=95.0, mfe_r=5.0)
    # sequence ou G1/G2/G3 auraient resserre (fort MFE, HL haut, close haut) : SL immuable.
    for i in range(1, 6):
        row_i = _row(date=_hours(i), close=110.0, atr_1h=1.0, last_hl_1h=109.0, high=106.0)
        gestion.update_excursions(st, row_i, 100.0)
        assert gestion.compute_sl(trade, row_i, st) is None
    # G4 inerte.
    assert gestion.partial_tp(trade, 3.0, st) is None
    assert st.tp1_done is False
    # G6/G7 inertes (event de cassure + age 24 + mfe bas), high sous TP => aucune sortie.
    dead = TradeState(initial_sl=95.0, mfe_r=0.0)
    row67 = _row(date=_hours(24), high=106.0, choch_bear_event_1h=True)
    assert gestion.check_exit(trade, row67, dead, tp2=None) is None


def test_control_a_ignores_pre_entry_candle(monkeypatch):
    """Garde "vie du trade" (fix 2026-07-18, BUILD_NOTES 17/07) : un high >= TP porte par une
    bougie ANTERIEURE a l'entree ne sort pas a t+0 (14 churns mesures campagne 11/07)."""
    monkeypatch.setattr(params, "CONTROL_A_MODE", True)
    trade = _Trade(open_rate=100.0, stop_loss=95.0, open_date_utc=_hours(2))
    st = TradeState(initial_sl=95.0)
    tp = 100.0 + params.TP1_R * (100.0 - 95.0)
    row_before = _row(date=_hours(1), high=tp + 10.0)     # cloturee avant l'entree
    assert gestion.check_exit(trade, row_before, st, tp2=None) is None
    row_after = _row(date=_hours(2), high=tp)             # 1re bougie de la vie du trade
    assert gestion.check_exit(trade, row_after, st, tp2=None) == "TP_CONTROL_A"


def test_control_a_flag_false_keeps_existing_behavior():
    assert params.CONTROL_A_MODE is False               # defaut = produit B
    trade = _Trade(open_rate=100.0, stop_loss=95.0)
    only_g1 = gestion.flags()
    only_g1.update(G2=False, G3=False)
    st = TradeState(initial_sl=95.0, mfe_r=1.0)
    assert gestion.compute_sl(trade, _row(), st, only_g1) == pytest.approx(100.0 * 1.001)
    st6 = TradeState(initial_sl=95.0, mfe_r=2.0)
    assert gestion.check_exit(trade, _row(choch_bear_event_1h=True), st6, tp2=None) == "G6"


# ================== A2 — geometrie SHORT (miroir strict, docs/03 §3.7) ==================
SHORT = -1


def _row_s(date=T0, close=100.0, high=100.0, low=100.0, atr_1h=1.0, last_lh_1h=999.0,
           choch_bull_event_1h=False, regime="TREND", **kw):
    """Bougie 1h vue par un SHORT : ancre G2 = last_lh_1h, evenement G6 = CHoCH haussier."""
    row = _row(date=date, close=close, high=high, low=low, atr_1h=atr_1h, regime=regime, **kw)
    row["last_lh_1h"] = last_lh_1h
    row["choch_bull_event_1h"] = choch_bull_event_1h
    return row


def _state_s(**kw):
    kw.setdefault("is_short", True)
    return TradeState(**kw)


def test_initial_levels_short_est_le_miroir():
    """Memes chiffres que le long, retournes autour de l'entree."""
    sl, tp1, tp2 = gestion.initial_levels(100.0, 105.0, 2.0, 70.0, sign=SHORT)
    assert sl == pytest.approx(105.0 + params.SL_HL_ATR_BUFFER * 2.0)   # LH 4h + 0,1xATR
    assert sl > 100.0                                                   # SL AU-DESSUS de l'entree
    assert tp1 == pytest.approx(100.0 - params.TP1_R * (sl - 100.0))    # TP1 -1,5R
    assert tp1 < 100.0
    assert tp2 == 70.0                                                  # support SOUS TP1
    # Le R du TP1 vaut bien +1,5 dans le sens du trade.
    assert gestion.r_multiple(tp1, 100.0, sl, SHORT) == pytest.approx(params.TP1_R)


def test_initial_levels_short_fallback_quand_lh_sous_lentree():
    sl, tp1, tp2 = gestion.initial_levels(100.0, 95.0, 2.0, float("nan"), sign=SHORT)
    assert sl == pytest.approx(100.0 + params.SL_FALLBACK_ATR_MULT * 2.0)
    assert tp2 is None
    # Un support AU-DESSUS de TP1 n'est pas une cible valable pour un short.
    _, tp1b, tp2b = gestion.initial_levels(100.0, 105.0, 2.0, 99.0, sign=SHORT)
    assert tp1b < 99.0 and tp2b is None


def test_r_multiple_short_signe_correctement():
    entry, sl = 100.0, 110.0          # risque = 10, SL au-dessus
    assert gestion.r_multiple(90.0, entry, sl, SHORT) == pytest.approx(1.0)    # baisse = gain
    assert gestion.r_multiple(110.0, entry, sl, SHORT) == pytest.approx(-1.0)  # SL touche = -1R
    assert gestion.r_multiple(100.0, entry, sl, SHORT) == 0.0
    # SL du mauvais cote (sous l'entree pour un short) = cas degenere => 0, jamais d'infini.
    assert gestion.r_multiple(90.0, entry, 90.0, SHORT) == 0.0


def test_update_excursions_short_inverse_high_et_low():
    """LE piege du short : l'excursion ADVERSE est le high, pas le low."""
    state = _state_s(initial_sl=110.0)
    row = _row_s(date=_hours(1), high=105.0, low=95.0)
    gestion.update_excursions(state, row, entry=100.0)
    assert state.mae_r == pytest.approx(-0.5)   # high 105 => -0,5R (contre le vendeur)
    assert state.mfe_r == pytest.approx(0.5)    # low 95   => +0,5R (pour le vendeur)
    # Le long sur la MEME bougie donne l'exact oppose.
    long_state = TradeState(initial_sl=90.0)
    gestion.update_excursions(long_state, _row(date=_hours(1), high=105.0, low=95.0), 100.0)
    assert long_state.mae_r == pytest.approx(-0.5) and long_state.mfe_r == pytest.approx(0.5)


def test_compute_sl_short_ne_peut_que_descendre():
    trade = _Trade(open_rate=100.0, stop_loss=110.0)
    # G1 : break-even au-dessus de +1R => SL sous l'entree, buffer du BON cote.
    state = _state_s(initial_sl=110.0, mfe_r=1.0)
    new_sl = gestion.compute_sl(trade, _row_s(), state)
    assert new_sl == pytest.approx(100.0 * (1.0 - params.G1_BE_BUFFER_FRAC))
    assert new_sl < trade.open_rate < trade.stop_loss
    # G3 : trailing ATR au-DESSUS du close pour un short.
    state = _state_s(initial_sl=110.0, mfe_r=1.0)
    new_sl = gestion.compute_sl(trade, _row_s(close=90.0, atr_1h=2.0), state,
                                flags={"G1": False, "G2": False, "G3": True,
                                       "G4": True, "G5": True, "G6": True, "G7": True})
    assert new_sl == pytest.approx(90.0 + params.G3_ATR_MULT * 2.0)
    # G2 : ancre = last_lh_1h, candidat au-dessus du SL courant => refuse (elargirait).
    state = _state_s(initial_sl=110.0)
    assert gestion.compute_sl(trade, _row_s(last_lh_1h=120.0), state) is None
    # Invariant absolu : jamais d'elargissement, quel que soit le sens.
    trade_serre = _Trade(open_rate=100.0, stop_loss=92.0)
    state = _state_s(initial_sl=110.0, mfe_r=5.0)
    assert gestion.compute_sl(trade_serre, _row_s(close=99.0, atr_1h=2.0), state) is None


def test_check_exit_short_utilise_le_choch_haussier_et_le_low():
    trade = _Trade(open_rate=100.0, stop_loss=110.0)
    # G6 : c'est le CHoCH HAUSSIER qui sort un short.
    state = _state_s(initial_sl=110.0)
    assert gestion.check_exit(
        trade, _row_s(date=_hours(1), choch_bull_event_1h=True), state, None) == "G6"
    # Un CHoCH baissier ne sort PAS un short (il va dans son sens).
    assert gestion.check_exit(
        trade, _row_s(date=_hours(1), choch_bear_event_1h=True), state, None) is None
    # TP2 : atteint par le LOW, et seulement apres TP1.
    state = _state_s(initial_sl=110.0, tp1_done=True)
    assert gestion.check_exit(trade, _row_s(date=_hours(1), low=80.0), state, 85.0) == "TP2"
    state = _state_s(initial_sl=110.0, tp1_done=True)
    assert gestion.check_exit(trade, _row_s(date=_hours(1), low=90.0), state, 85.0) is None
    # G5 (extension) neutralise TP2 dans les deux sens.
    state = _state_s(initial_sl=110.0, tp1_done=True, extension_on=True)
    assert gestion.check_exit(trade, _row_s(date=_hours(1), low=80.0), state, 85.0) is None


def test_partial_tp_short_reconstruit_le_bon_prix():
    trade = _Trade(open_rate=100.0, stop_loss=110.0, amount=2.0)
    state = _state_s(initial_sl=110.0)
    stake = gestion.partial_tp(trade, params.G4_TRIGGER_R, state)
    # +1,5R pour un short entre a 100 avec SL 110 => prix 85 (et non 115).
    assert stake == pytest.approx(-(params.G4_SELL_FRACTION * 2.0 * 85.0))
    assert stake < 0                      # on REDUIT la position, on ne la retourne pas
    assert state.tp1_done is True


def test_g7_time_stop_identique_dans_les_deux_sens():
    """G7 ne regarde que l'age et le MFE : rien a symetriser, et c'est verifie."""
    trade = _Trade(open_rate=100.0, stop_loss=110.0)
    row = _row_s(date=_hours(params.G7_MAX_CANDLES_1H))
    assert gestion.check_exit(trade, row, _state_s(initial_sl=110.0, mfe_r=0.0), None) == "G7"
    state = _state_s(initial_sl=110.0, mfe_r=params.G7_MIN_R)
    assert gestion.check_exit(trade, row, state, None) is None


def test_tradestate_sign_et_retrocompat():
    assert TradeState().sign == 1                      # defaut = long, trades d'avant A2
    assert TradeState(is_short=True).sign == -1
    assert "is_short" in TradeState().as_dict()
    assert TradeState.from_dict({"is_short": True}).sign == -1


# --------------------------------------------------------------------------------------
# Garde-fou ARIT_G_OFF (2026-08-31). Avant lui, toute valeur hors des sept laissait les
# sept flags a True sans erreur, sans log et sans test : un run d'ablation rate se lisait
# « cette regle ne coute rien ». params.flags_ablation() est le chemin exact utilise a
# l'import — on l'appelle directement plutot que de recharger le module (un reload recree
# params.PROTECTIONS et casse test_protections_declarees_dans_la_strategie).
# --------------------------------------------------------------------------------------


def test_g_off_absent_laisse_le_produit_b():
    assert set(params.flags_ablation("").values()) == {True}
    assert set(params.G_FLAGS_DEFAULT.values()) == {True}      # defaut reel du depot


def test_g_off_nominal_desactive_une_seule_regle():
    flags = params.flags_ablation("G3")
    assert flags["G3"] is False
    assert all(v for k, v in flags.items() if k != "G3")


def test_g_off_tolere_les_espaces_du_shell():
    assert params.flags_ablation("G3 ")["G3"] is False


def test_g_off_casse_refusee_avec_la_correction():
    with pytest.raises(ValueError, match="ARIT_G_OFF=G3"):
        params.flags_ablation("g3")


@pytest.mark.parametrize("valeur", ["G8", "A8", "gestion", "G3,G4", "3"])
def test_g_off_valeur_inconnue_refusee(valeur):
    with pytest.raises(ValueError, match="invalide"):
        params.flags_ablation(valeur)


def test_g5_est_ablatable_depuis_son_cablage():
    """G5 etait refusee tant que son flag n'etait pas lu (le garde-fou aurait menti).
    Depuis gestion.set_extension, les sept regles sont ablatables."""
    assert params.flags_ablation("G5")["G5"] is False
    assert params.G_ABLATABLES == params.G_RULES


def test_toutes_les_g_rules_ablatables_sont_gardees_par_leur_flag():
    """Verrou de coherence : une regle declaree ablatable DOIT etre lue quelque part dans
    gestion.py. C'est ce test qui aurait attrape le trou de G5."""
    source = pathlib.Path(gestion.__file__).read_text(encoding="utf-8")
    manquantes = [g for g in params.G_ABLATABLES if f'active["{g}"]' not in source]
    assert not manquantes, f"declarees ablatables mais jamais lues dans gestion.py : {manquantes}"


# --------------------------------------------------------------------------------------
# G5 — extension post-BOS (docs/03 par.3.4, M05 par.2.5). Cablee dans gestion.py le
# 2026-08-31 : elle vivait en ligne dans AritV1.py, ignorait son flag d'ablation, et lisait
# la cassure HAUSSIERE meme sur un short (donc s'activait contre la position).
# --------------------------------------------------------------------------------------


def test_g5_long_s_active_sur_cassure_haussiere():
    state = TradeState(tp1_done=True)
    assert gestion.set_extension(state, _row(bos_fresh_4h=True)) is True
    assert state.extension_on is True


def test_g5_long_ignore_la_cassure_baissiere():
    state = TradeState(tp1_done=True)
    assert gestion.set_extension(state, _row(bos_fresh_bear_4h=True)) is False
    assert state.extension_on is False


def test_g5_short_s_active_sur_cassure_baissiere():
    """A2 — la cassure FAVORABLE a un vendeur est baissiere (miroir bos_fresh_bear_4h)."""
    state = _state_s(tp1_done=True)
    assert gestion.set_extension(state, _row_s(bos_fresh_bear_4h=True)) is True
    assert state.extension_on is True


def test_g5_short_ignore_la_cassure_haussiere():
    """LE BUG CORRIGE : avant le 2026-08-31, un short etendait sa position sur une cassure
    haussiere, c'est-a-dire exactement quand le marche partait CONTRE lui."""
    state = _state_s(tp1_done=True)
    assert gestion.set_extension(state, _row_s(bos_fresh_4h=True)) is False
    assert state.extension_on is False


def test_g5_exige_tp1_done():
    """G5 est une extension APRES G4 : sans TP1 pris, il n'y a rien a etendre."""
    state = TradeState(tp1_done=False)
    assert gestion.set_extension(state, _row(bos_fresh_4h=True)) is False


def test_g5_ne_s_active_qu_une_fois():
    state = TradeState(tp1_done=True)
    assert gestion.set_extension(state, _row(bos_fresh_4h=True)) is True
    assert gestion.set_extension(state, _row(bos_fresh_4h=True)) is False


def test_g5_inerte_quand_son_flag_est_coupe():
    """ARIT_G_OFF=G5 : c'etait un no-op SILENCIEUX avant le cablage."""
    state = TradeState(tp1_done=True)
    coupe = params.flags_ablation("G5")
    assert gestion.set_extension(state, _row(bos_fresh_4h=True), flags=coupe) is False
    assert state.extension_on is False


def test_g5_neutralise_tp2():
    """L'effet de G5 (docs/03 par.3.4) : TP2 ne sort plus, le reste court sous G2/G3."""
    trade, state = _Trade(), TradeState(initial_sl=95.0, tp1_done=True)
    row = _row(date=_hours(1), high=120.0, bos_fresh_4h=True)
    assert gestion.check_exit(trade, row, state, tp2=110.0) == "TP2"
    gestion.set_extension(state, row)
    assert gestion.check_exit(trade, row, state, tp2=110.0) is None
