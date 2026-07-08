"""Tests M07 - AritV1.py (docs/modules/M07). Duck-typing freqtrade, AUCUN bot demarre :
instances via __new__ (pas de config freqtrade), arit_lib monkeypatche, journal.write capture.
Cas exiges : _closed_1h_row (helper unique teste), anti-look-ahead new_4h, securite exception
(regle 3), gate_check TOUJOURS journalise (interdit n6), tuple compute_stake + skip, fusion
fear_greed/macro_stale dans l'evaluation, round-trip custom_data, niveaux SL/TP 03.3.
"""

import pandas as pd
import pytest

import AritV1 as strat_mod
from arit_lib import contracts, params

Strat = strat_mod.AritV1
T0 = pd.Timestamp("2024-01-01", tz="UTC")


def _inst():
    s = Strat.__new__(Strat)          # bypass IStrategy.__init__ (aucune config freqtrade)
    s._pending = {}
    return s


class _DP:
    def __init__(self, df, runmode="backtest"):
        self._df = df
        self.runmode = type("R", (), {"value": runmode})()

    def get_analyzed_dataframe(self, pair, tf):
        return self._df, {}


class _Wallets:
    def __init__(self, equity=10_000.0):
        self._e = float(equity)

    def get_total_stake_amount(self):
        return self._e


class _FakeTrade:
    @staticmethod
    def get_trades_proxy():
        return []


class _CDTrade:
    """Trade duck-type minimal pour custom_data (set/get)."""

    def __init__(self):
        self.cd = {}

    def set_custom_data(self, key, value):
        self.cd[key] = value

    def get_custom_data(self, key, default=None):
        return self.cd.get(key, default)


def _capture(monkeypatch):
    events = []

    def _w(et, payload):
        events.append((et, payload))

    monkeypatch.setattr(strat_mod.journal, "write", _w)
    return events


# --------------------------------------------------- _closed_1h_row (regle 2)
def test_closed_1h_row_returns_last_closed(ohlcv):
    df = ohlcv("trend", n=12)
    s = _inst()
    s.dp = _DP(df)
    row = s._closed_1h_row("BTC/USDT")
    assert row["close"] == df["close"].iloc[-1]     # derniere bougie CLOTUREE
    assert row["date"] == df["date"].iloc[-1]


def test_closed_1h_row_empty_is_none():
    s = _inst()
    s.dp = _DP(pd.DataFrame())
    assert s._closed_1h_row("BTC/USDT") is None


# --------------------------------------------------- anti-look-ahead new_4h
def test_entry_trend_requires_new_4h():
    s = _inst()
    df = pd.DataFrame({
        "signal_long": [True, True, True, False],
        "new_4h": [True, False, True, True],
    })
    out = s.populate_entry_trend(df.copy(), {"pair": "BTC/USDT"})
    # enter seulement quand signal_long ET new_4h : jamais deux fois le meme setup 4h.
    assert list(out["enter_long"]) == [1, 0, 1, 0]


def test_entry_trend_missing_columns_is_safe():
    s = _inst()
    out = s.populate_entry_trend(pd.DataFrame({"close": [1, 2]}), {})
    assert list(out["enter_long"]) == [0, 0]


# --------------------------------------------------- securite exception (regle 3)
def test_callback_exception_is_caught_and_journaled(monkeypatch):
    events = _capture(monkeypatch)

    class _Boom:
        runmode = type("R", (), {"value": "backtest"})()

        def get_analyzed_dataframe(self, *a):
            raise RuntimeError("boom")

    s = _inst()
    s.dp = _Boom()
    assert s.custom_exit("BTC/USDT", object()) is None       # action la plus sure
    assert any(et == "system" for et, _ in events)           # journal 'system'


def test_populate_indicators_never_crashes(monkeypatch):
    events = _capture(monkeypatch)

    def _boom(*a, **k):
        raise RuntimeError("feature down")

    monkeypatch.setattr(strat_mod.features, "compute_all", _boom)
    s = _inst()
    s.dp = _DP(pd.DataFrame({"close": [1, 2]}), runmode="dry_run")
    out = s.populate_indicators(pd.DataFrame({"close": [1, 2]}), {"pair": "BTC/USDT"})
    assert "close" in out.columns                            # df retourne malgre l'erreur
    assert "system" in [et for et, _ in events]


# --------------------------------------------------- gate_check TOUJOURS (n6)
def test_confirm_entry_always_journals_gate_check(monkeypatch):
    events = _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.risk, "cb_day_active", lambda w, n, u: False)
    monkeypatch.setattr(strat_mod.risk, "gate_check",
                        lambda *a: (False, contracts.GATE_NAMES[0], {"r": "RANGE"}))
    monkeypatch.setattr(strat_mod, "Trade", _FakeTrade)
    s = _inst()
    row = pd.Series({"regime": "RANGE", "rr_dispo": 1.0, "conviction": 0.4, "seuil": 0.5,
                     "date_4h": T0, "date": T0})
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: row)
    s.wallets = _Wallets()
    s.config = {"dry_run": True}
    assert s.confirm_trade_entry("BTC/USDT", T0) is False
    gates = [p for et, p in events if et == "gate_check"]
    assert gates and gates[0]["decision"] == "skip"


def test_confirm_entry_blocked_by_circuit_breaker(monkeypatch):
    events = _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (True, 2))  # cooldown
    monkeypatch.setattr(strat_mod.risk, "cb_day_active", lambda w, n, u: False)
    monkeypatch.setattr(strat_mod, "Trade", _FakeTrade)
    s = _inst()
    monkeypatch.setattr(s, "_closed_1h_row",
                        lambda pair: pd.Series({"regime": "TREND", "date_4h": T0, "date": T0}))
    s.wallets = _Wallets()
    s.config = {"dry_run": True}
    assert s.confirm_trade_entry("BTC/USDT", T0) is False
    assert any(et == "system" for et, _ in events)          # CB -> event 'system'


# --------------------------------------------------- tuple compute_stake + skip
def test_custom_stake_skip_journals_reason(monkeypatch):
    events = _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.risk, "compute_stake",
                        lambda *a, **k: (None, contracts.SKIP_MIN_NOTIONAL))
    monkeypatch.setattr(strat_mod, "Trade", _FakeTrade)
    s = _inst()
    row = pd.Series({"last_hl_4h": 95.0, "atr_4h": 2.0, "nearest_res_4h": 130.0,
                     "conviction": 0.8, "seuil": 0.5, "regime": "TREND", "date_4h": T0, "date": T0})
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: row)
    s.wallets = _Wallets()
    s.config = {"dry_run": True}
    assert s.custom_stake_amount("BTC/USDT", T0, 100.0, 10.0) == 0.0
    skips = [p for et, p in events if et == "gate_check"]
    assert skips and skips[0]["failed_gate"] == contracts.SKIP_MIN_NOTIONAL
    assert "BTC/USDT" not in s._pending


def test_custom_stake_happy_path_stashes_pending(monkeypatch):
    _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.risk, "compute_stake", lambda *a, **k: (250.0, None))
    monkeypatch.setattr(strat_mod, "Trade", _FakeTrade)
    s = _inst()
    row = pd.Series({"last_hl_4h": 95.0, "atr_4h": 2.0, "nearest_res_4h": 130.0,
                     "conviction": 0.8, "seuil": 0.5, "regime": "TREND", "date_4h": T0, "date": T0})
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: row)
    s.wallets = _Wallets()
    s.config = {"dry_run": True}
    assert s.custom_stake_amount("BTC/USDT", T0, 100.0, 10.0) == 250.0
    pend = s._pending["BTC/USDT"]
    assert pend["initial_sl"] == pytest.approx(95.0 - params.SL_HL_ATR_BUFFER * 2.0)
    assert pend["signal_id"].startswith("BTCUSDT-")


# --------------------------------------------------- TP2 fige (11.3, PDR 03.3)
def test_custom_exit_uses_frozen_tp2_not_current_res(monkeypatch):
    """Le TP2 relu du custom_data ne bouge pas quand nearest_res_4h change apres l'entree."""
    _capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(strat_mod.gestion, "update_excursions", lambda st, r, e: st)
    monkeypatch.setattr(strat_mod.gestion, "check_exit",
                        lambda trade, row, state, tp2: seen.setdefault("tp2", tp2))
    s = _inst()
    trade = _CDTrade()
    trade.pair, trade.open_rate = "BTC/USDT", 100.0
    s._save_state(trade, contracts.TradeState(initial_sl=95.0, signal_id="x", tp2=130.0))
    # nearest_res_4h a bouge a 999 depuis l'entree : ignore, on lit le TP2 fige (130).
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: pd.Series({"nearest_res_4h": 999.0}))
    s.custom_exit("BTC/USDT", trade)
    assert seen["tp2"] == 130.0


def test_custom_exit_tp2_zero_means_no_target(monkeypatch):
    _capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(strat_mod.gestion, "update_excursions", lambda st, r, e: st)
    monkeypatch.setattr(strat_mod.gestion, "check_exit",
                        lambda trade, row, state, tp2: seen.setdefault("tp2", tp2))
    s = _inst()
    trade = _CDTrade()
    trade.pair, trade.open_rate = "BTC/USDT", 100.0
    s._save_state(trade, contracts.TradeState(initial_sl=95.0, signal_id="x", tp2=0.0))
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: pd.Series({"nearest_res_4h": 999.0}))
    s.custom_exit("BTC/USDT", trade)
    assert seen["tp2"] is None            # tp2 == 0 => pas de cible (jamais un exit fantome)


# --------------------------------------------------- custom_data round-trip
def test_trade_state_roundtrip():
    s = _inst()
    st = contracts.TradeState(initial_sl=94.8, risk_pct=0.02, trade_no=3, tp1_done=True,
                              mfe_r=1.2, signal_id="BTCUSDT-x", entry_regime="TREND")
    trade = _CDTrade()
    s._save_state(trade, st)
    assert set(trade.cd) == set(contracts.CUSTOM_DATA_KEYS)                # cles 11.3 exclusivement
    back = s._trade_state(trade)
    assert back.initial_sl == 94.8 and back.trade_no == 3 and back.tp1_done is True
    assert back.signal_id == "BTCUSDT-x" and back.entry_regime == "TREND"


# --------------------------------------------------- fusion macro dans evaluation
def test_journal_evaluation_merges_macro(monkeypatch):
    events = _capture(monkeypatch)
    s = _inst()
    df = pd.DataFrame({
        "new_4h": [False, True], "signal_long": [False, True], "regime": ["TREND", "TREND"],
        "adx_4h": [30.0, 30.0], "ema50_4h": [100.0, 100.0], "ema200_4h": [90.0, 90.0],
        "close_4h": [105.0, 105.0],
        "s_structure": [1.0, 1.0], "s_momentum": [0.5, 0.5], "s_sr": [1.0, 1.0],
        "s_patterns": [0.3, 0.3], "s_volume": [0.5, 0.5],
        "conviction": [0.8, 0.8], "seuil": [0.5, 0.5], "rr_dispo": [2.0, 2.0],
        "date": [T0, T0 + pd.Timedelta(hours=4)],
    })
    s._journal_evaluation(df, "BTC/USDT", {"fear_greed": 55, "stale": False})
    evals = [p for et, p in events if et == "evaluation"]
    assert evals, "une ligne 'evaluation' doit etre ecrite a la cloture 4h"
    ri = evals[0]["regime_inputs"]
    assert ri["fear_greed"] == 55 and ri["macro_stale"] is False           # fusion macro_state
    assert evals[0]["decision"] == "signal"


def test_journal_evaluation_skipped_when_not_new_4h(monkeypatch):
    events = _capture(monkeypatch)
    s = _inst()
    df = pd.DataFrame({"new_4h": [False], "signal_long": [True], "regime": ["TREND"],
                       "date": [T0]})
    s._journal_evaluation(df, "BTC/USDT", {"fear_greed": 55, "stale": False})
    assert not events   # pas de nouvelle bougie 4h => aucune ligne
