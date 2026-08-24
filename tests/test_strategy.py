"""Tests M07 - AritV1.py (docs/modules/M07). Duck-typing freqtrade, AUCUN bot demarre :
instances via __new__ (pas de config freqtrade), arit_lib monkeypatche, journal.write capture.
Cas exiges : _closed_1h_row (helper unique teste), anti-look-ahead new_4h, securite exception
(regle 3), gate_check TOUJOURS journalise (interdit n6), tuple compute_stake + skip, fusion
fear_greed/macro_stale dans l'evaluation, round-trip custom_data, niveaux SL/TP 03.3.
"""

import json

import pandas as pd
import pytest

import AritV1 as strat_mod
from arit_lib import contracts, macro_regime, params

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


# ------------------------------ TP2 = resistance 4h COURANTE (Jonas 09/07, docs/03 par.3.3)
def test_custom_exit_uses_current_res_not_frozen_tp2(monkeypatch):
    """Quand nearest_res_4h change apres l'entree, la sortie TP2 utilise la valeur COURANTE ;
    le tp2 fige en custom_data (audit) reste inchange."""
    _capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(strat_mod.gestion, "update_excursions", lambda st, r, e: st)
    monkeypatch.setattr(strat_mod.gestion, "check_exit",
                        lambda trade, row, state, tp2: seen.setdefault("tp2", tp2))
    s = _inst()
    trade = _CDTrade()
    trade.pair, trade.open_rate = "BTC/USDT", 100.0
    s._save_state(trade, contracts.TradeState(initial_sl=95.0, signal_id="x", tp2=130.0))
    # nearest_res_4h a bouge a 999 depuis l'entree : c'est la valeur COURANTE qui sert.
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: pd.Series({"nearest_res_4h": 999.0}))
    s.custom_exit("BTC/USDT", trade)
    assert seen["tp2"] == 999.0
    assert trade.get_custom_data("tp2") == 130.0          # tp2 d'entree conserve (audit)


def test_custom_exit_no_current_res_means_no_target(monkeypatch):
    _capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(strat_mod.gestion, "update_excursions", lambda st, r, e: st)
    monkeypatch.setattr(strat_mod.gestion, "check_exit",
                        lambda trade, row, state, tp2: seen.setdefault("tp2", tp2))
    s = _inst()
    trade = _CDTrade()
    trade.pair, trade.open_rate = "BTC/USDT", 100.0
    s._save_state(trade, contracts.TradeState(initial_sl=95.0, signal_id="x", tp2=130.0))
    # resistance 4h courante absente (NaN) => pas de cible (jamais un exit fantome).
    monkeypatch.setattr(s, "_closed_1h_row",
                        lambda pair: pd.Series({"nearest_res_4h": float("nan")}))
    s.custom_exit("BTC/USDT", trade)
    assert seen["tp2"] is None


# ------------------------------------- custom_stoploss : floor SL initial (fix 2026-07-18)
def test_custom_stoploss_floor_posed_sans_after_fill(monkeypatch):
    """BUILD_NOTES 17/07 : le floor SL initial doit etre offert a CHAQUE appel — le
    conditionner a after_fill ne le posait JAMAIS (order_filled ecrit le custom_data APRES
    l'appel after_fill) => controle A sans stop pendant 8,5 ans."""
    events = _capture(monkeypatch)
    s = _inst()
    s.dp = _DP(pd.DataFrame())                    # aucune bougie cloturee -> branche floor pure
    trade = _CDTrade()
    trade.set_custom_data("initial_sl", 94.0)
    got = s.custom_stoploss("BTC/USDT", trade, 100.0, after_fill=False)
    assert got == pytest.approx(strat_mod.stoploss_from_absolute(94.0, 100.0))
    assert not [e for e in events if e[0] == "system"]        # aucune exception avalee


def test_custom_stoploss_floor_short_nest_jamais_zero(monkeypatch):
    """A1 (24/08) : le floor d'un SHORT doit etre un ratio STRICTEMENT positif.

    `stoploss_from_absolute` sans `is_short` rend 0.0 pour un stop situe au-dessus du prix
    (le cas de TOUT short), et freqtrade jette cette valeur : `if stop_loss_value_custom`
    est faux pour 0.0. Consequence mesuree avant correctif : aucun short n'avait de stop,
    ni structurel ni G-rule, le SL restait au plancher de classe (-0.99).
    Valeurs = le short BNB du backtest 20/06/2026 (entree 580,93 / SL structurel 584,14).
    """
    _capture(monkeypatch)
    s = _inst()
    s.dp = _DP(pd.DataFrame())                    # aucune bougie cloturee -> branche floor pure
    trade = _CDTrade()
    trade.set_custom_data("initial_sl", 584.1424175479987)
    trade.set_custom_data("is_short", True)
    got = s.custom_stoploss("BNB/USDT:USDT", trade, 580.93, after_fill=False)
    assert got > 0.0, "un floor a 0.0 est jete par freqtrade => short sans stop"
    assert got == pytest.approx(
        strat_mod.stoploss_from_absolute(584.1424175479987, 580.93, is_short=True))


def test_custom_stoploss_grule_short_nest_jamais_zero(monkeypatch):
    """Meme exigence sur le retour d'une G-rule : un SL de short reste au-dessus du prix."""
    _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.gestion, "update_excursions", lambda st, r, e: st)
    monkeypatch.setattr(strat_mod.gestion, "compute_sl", lambda t, r, st: 581.1290741282827)
    s = _inst()
    trade = _CDTrade()
    trade.pair, trade.open_rate, trade.stop_loss = "BNB/USDT:USDT", 580.93, 1156.05
    s._save_state(trade, contracts.TradeState(
        initial_sl=584.1424175479987, signal_id="x", is_short=True))
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: pd.Series({"date": 0}))
    got = s.custom_stoploss("BNB/USDT:USDT", trade, 580.93, after_fill=False)
    assert got > 0.0
    assert got == pytest.approx(
        strat_mod.stoploss_from_absolute(581.1290741282827, 580.93, is_short=True))


def test_custom_stoploss_long_inchange(monkeypatch):
    """Controle de non-regression : le chemin LONG n'etait pas touche, il ne bouge pas."""
    _capture(monkeypatch)
    s = _inst()
    s.dp = _DP(pd.DataFrame())
    trade = _CDTrade()
    trade.set_custom_data("initial_sl", 94.0)
    got = s.custom_stoploss("BTC/USDT", trade, 100.0, after_fill=False)
    assert got == pytest.approx(strat_mod.stoploss_from_absolute(94.0, 100.0, is_short=False))


def test_custom_stoploss_none_avant_custom_data(monkeypatch):
    """Avant order_filled (custom_data vide) : None — on garde le stoploss par defaut,
    jamais un floor a ~0."""
    events = _capture(monkeypatch)
    s = _inst()
    s.dp = _DP(pd.DataFrame())
    got = s.custom_stoploss("BTC/USDT", _CDTrade(), 100.0, after_fill=True)
    assert got is None
    assert not [e for e in events if e[0] == "system"]


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
    s._journal_evaluation(df, "BTC/USDT", {"fear_greed": 55, "stale": False}, True)
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
    s._journal_evaluation(df, "BTC/USDT", {"fear_greed": 55, "stale": False}, True)
    assert not events   # pas de nouvelle bougie 4h => aucune ligne


def _df_deux_cloture_4h():
    """df 1h portant DEUX cloture 4h (lignes 1 et 3) — support des tests de scope."""
    n = 4
    return pd.DataFrame({
        "new_4h": [False, True, False, True], "signal_long": [False] * n,
        "signal_short": [False] * n, "regime": ["TREND"] * n,
        "adx_4h": [30.0] * n, "ema50_4h": [100.0] * n, "ema200_4h": [90.0] * n,
        "close_4h": [105.0] * n,
        "s_structure": [1.0] * n, "s_momentum": [0.5] * n, "s_sr": [1.0] * n,
        "s_patterns": [0.3] * n, "s_volume": [0.5] * n,
        "conviction": [0.8] * n, "seuil": [0.5] * n, "rr_dispo": [2.0] * n,
        "date": [T0 + pd.Timedelta(hours=i) for i in range(n)],
    })


def test_journal_evaluation_backtest_ecrit_toutes_les_cloture_4h(monkeypatch):
    """Le scope BACKTEST est la raison d'etre du changement du 12/08 : sans lui, l'evenement
    `evaluation` n'existait dans AUCUN journal du projet (0 sur ~5 600 lignes)."""
    events = _capture(monkeypatch)
    _inst()._journal_evaluation(_df_deux_cloture_4h(), "BTC/USDT", {}, False)
    evals = [p for et, p in events if et == "evaluation"]
    assert len(evals) == 2, "backtest : une evaluation par cloture 4h, pas seulement la derniere"


def test_journal_evaluation_backtest_nutilise_pas_letat_macro_courant(monkeypatch):
    """macro_state.json porte l'etat d'AUJOURD'HUI : l'ecrire sur une bougie de 2021 serait du
    look-ahead. En backtest ces deux champs doivent rester vides, quoi que porte le fichier."""
    events = _capture(monkeypatch)
    _inst()._journal_evaluation(_df_deux_cloture_4h(), "BTC/USDT",
                                {"fear_greed": 55, "stale": False}, False)
    ri = [p for et, p in events if et == "evaluation"][0]["regime_inputs"]
    assert ri["fear_greed"] is None and ri["macro_stale"] is False


def test_journal_evaluation_live_ne_prend_que_la_derniere_ligne(monkeypatch):
    """Live : une evaluation par boucle (docs/08). Deux cloture 4h dans le df ne doivent PAS
    produire deux lignes — sinon chaque boucle re-journaliserait tout l'historique charge."""
    events = _capture(monkeypatch)
    _inst()._journal_evaluation(_df_deux_cloture_4h(), "BTC/USDT", {}, True)
    assert len([p for et, p in events if et == "evaluation"]) == 1


# ----------------------------------- Macro Analyst V1.1 : pose de la colonne en backtest
def _fake_macro(monkeypatch, daily, veto=None):
    """Stub du module macro_regime. `veto` = frame du bloc correlation c6/c7 (06 §6.2.1) ;
    None => bloc non configure, donc jamais bloquant (fail-safe A4 : started, pas fresh)."""
    if veto is None:
        veto = pd.DataFrame({contracts.EQUITY_VETO_COL: False,
                             contracts.EQUITY_VETO_REASON_COL: contracts.EQUITY_PASS_NOT_STARTED,
                             "stale_days": 0}, index=daily.index)
    # A2/04-08 : l'assemblage (charger + joindre le veto + detecter le stale) a quitte la
    # strategie pour macro_regime.daily_with_equity_veto — M07 ne fait plus que journaliser
    # les evenements retournes. Le stub suit ce contrat.
    def _daily_with_veto(_d):
        if daily.empty:
            return daily, [("macro_unavailable", {"dir": str(_d)})]
        joined = daily.join(veto[[contracts.EQUITY_VETO_COL,
                                  contracts.EQUITY_VETO_REASON_COL]])
        return joined, []

    # `attach_regime_now` (parite live A2) delegue a la VRAIE implementation : c'est le
    # chemin live qu'on veut exercer, pas un stub qui le ferait passer par construction.
    fake = type("M", (), {"daily_with_equity_veto": staticmethod(_daily_with_veto),
                          "attach_regime_now": staticmethod(macro_regime.attach_regime_now)})
    monkeypatch.setattr(strat_mod, "macro_regime", fake)


def _capture_classify(monkeypatch, seen):
    def _classify(df, macro=None):
        seen["has_col"] = contracts.MACRO_REGIME_COL in df.columns
        return df.assign(regime="TREND", seuil=0.5, multiplicateur=1.0)
    monkeypatch.setattr(strat_mod.regimes, "classify", _classify)
    monkeypatch.setattr(strat_mod.cio, "conviction", lambda df: df)
    monkeypatch.setattr(strat_mod.features, "compute_all", lambda df: df)
    monkeypatch.setattr(strat_mod.journal, "read_macro_state",
                        lambda: {"fear_greed": 50, "stale": False})


def _candles():
    return pd.DataFrame({"date": pd.date_range("2024-01-02", periods=3, freq="1h", tz="UTC"),
                         "close": [1.0, 2.0, 3.0]})


def test_backtest_poses_macro_column(monkeypatch):
    _capture(monkeypatch)
    seen = {}
    _capture_classify(monkeypatch, seen)
    daily = pd.DataFrame({contracts.MACRO_REGIME_COL: ["PORTEUR", "NEUTRE"]},
                         index=pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True))
    _fake_macro(monkeypatch, daily)
    s = _inst()
    s.dp = _DP(_candles(), runmode="backtest")
    s.config = {"user_data_dir": "user_data"}
    s.populate_indicators(_candles(), {"pair": "BTC/USDT"})
    assert seen["has_col"] is True                           # colonne posee AVANT classify


def test_backtest_no_column_when_macro_files_absent(monkeypatch):
    events = _capture(monkeypatch)
    seen = {}
    _capture_classify(monkeypatch, seen)
    empty = pd.DataFrame(columns=[contracts.MACRO_REGIME_COL])  # load_history vide => daily vide
    _fake_macro(monkeypatch, empty)
    s = _inst()
    s.dp = _DP(_candles(), runmode="backtest")
    s.config = {"user_data_dir": "user_data"}
    s.populate_indicators(_candles(), {"pair": "BTC/USDT"})
    assert seen["has_col"] is False                          # colonne non posee (macro neutre)
    kinds = [p.get("kind") for et, p in events if et == "system"]
    assert "macro_unavailable" in kinds                      # log warning UNE fois


def _live_strategie(monkeypatch, seen, macro_state):
    """Instance en runmode dry_run, avec `macro_state` renvoye par read_macro_state."""
    _capture(monkeypatch)
    _capture_classify(monkeypatch, seen)
    _fake_macro(monkeypatch, pd.DataFrame({contracts.MACRO_REGIME_COL: ["PORTEUR"]},
                                          index=pd.to_datetime(["2024-01-02"], utc=True)))
    monkeypatch.setattr(strat_mod.journal, "read_macro_state", lambda: macro_state)
    s = _inst()
    monkeypatch.setattr(s, "_journal_evaluation", lambda *a, **k: None)
    s.dp = _DP(_candles(), runmode="dry_run")
    s.config = {"user_data_dir": "user_data"}
    return s.populate_indicators(_candles(), {"pair": "BTC/USDT"})


def test_live_pose_la_colonne_macro_parite_a2(monkeypatch):
    """Parite A2 (2026-08-07) : le live pose DESORMAIS le regime macro, comme le backtest.

    Sans cette colonne, cio.direction_macro retombait sur son fail-safe long-only : le live
    et le backtest etaient deux produits differents (BLOQUANT declare du dry-run, 07 §7.3).
    """
    seen = {}
    out = _live_strategie(monkeypatch, seen, {
        "fear_greed": 50, "stale": False,
        contracts.MACRO_SCORES_KEY: {"dxy": 1, "taux": 1, "stablecoins": 0,
                                     "funding": 0, "fear_greed": 0}})
    assert seen["has_col"] is True                       # colonne posee AVANT classify
    assert (out[contracts.MACRO_REGIME_COL] == "PORTEUR").all()      # somme +2 => PORTEUR


def test_live_sans_scores_macro_est_hostile(monkeypatch):
    """Fonda non alimentee (macro_state sans scores) => HOSTILE, jamais un NEUTRE de facade.

    NEUTRE autoriserait long ET short a l'aveugle. La traduction de ce HOSTILE en « aucune
    entree » est faite par le fail-safe de donnee de regimes.classify (teste en M02).
    """
    seen = {}
    out = _live_strategie(monkeypatch, seen, {"fear_greed": 50, "stale": False})
    assert (out[contracts.MACRO_REGIME_COL] == "HOSTILE").all()


def test_live_fear_greed_brut_nest_jamais_lu_comme_un_score(monkeypatch):
    """Garde-fou anti-collision de schema : `fear_greed` vaut 50 (indice BRUT 06.3) au
    premier niveau. S'il etait somme comme un score, le total ferait +50 => PORTEUR a tous
    les coups, donc long autorise en permanence quelle que soit la macro reelle."""
    seen = {}
    out = _live_strategie(monkeypatch, seen, {
        "fear_greed": 50, "stale": False,
        contracts.MACRO_SCORES_KEY: {"dxy": -1, "taux": -1, "stablecoins": 0,
                                     "funding": 0, "fear_greed": 0}})
    assert (out[contracts.MACRO_REGIME_COL] == "HOSTILE").all()      # somme -2 => HOSTILE


# --------------------- C6 : protections freqtrade natives (07.1.1, 03.5) ---------------------
def test_protections_declarees_dans_la_strategie():
    """freqtrade 2026.6 : la liste vit dans la STRATEGIE, plus dans config.json."""
    assert Strat.protections is params.PROTECTIONS
    assert [p["method"] for p in Strat.protections] == [
        "CooldownPeriod", "StoplossGuard", "MaxDrawdown"]


def test_protections_derivent_des_constantes_03_5():
    """Aucune valeur en dur : les protections suivent les CB de 03.5 (interdit n4)."""
    by_method = {p["method"]: p for p in params.PROTECTIONS}
    assert by_method["CooldownPeriod"]["stop_duration_candles"] == \
        params.COOLDOWN_POST_EXIT_CANDLES
    slg = by_method["StoplossGuard"]
    assert slg["trade_limit"] == params.CB_SEQ_CONSECUTIVE
    assert slg["stop_duration_candles"] == params.CB_SEQ_COOLDOWN_CANDLES_1H
    assert slg["only_per_pair"] is False        # CB sequentiel = portefeuille (03.5)
    assert slg["only_per_side"] is False        # A2 : serie perdante long ET short
    mdd = by_method["MaxDrawdown"]
    assert mdd["max_allowed_drawdown"] == params.CB_DAY_EQUITY_DROP_PCT
    assert mdd["stop_duration_candles"] == params.PROTECT_MAXDD_STOP_CANDLES


def test_protections_chargeables_par_freqtrade():
    """Garde-fou d'upgrade : si freqtrade renomme une cle, ce test casse AVANT le dry-run."""
    pm = pytest.importorskip("freqtrade.plugins.protectionmanager")
    manager = pm.ProtectionManager({"timeframe": params.TIMEFRAME_BASE,
                                    "stake_currency": params.STAKE_CURRENCY},
                                   params.PROTECTIONS)
    handlers = manager._protection_handlers
    assert len(handlers) == len(params.PROTECTIONS)
    assert {h.__class__.__name__ for h in handlers} == {
        "CooldownPeriod", "StoplossGuard", "MaxDrawdown"}
    # les valeurs 03.5 ont bien ete lues par freqtrade, pas juste acceptees
    descs = " | ".join(h.short_desc() for h in handlers)
    assert "2 candles" in descs                                  # cooldown post-sortie
    assert f"{params.CB_DAY_EQUITY_DROP_PCT}" in descs           # -6 % du CB jour


# ==================== A2 — le bot est long ET short (docs/01 v4, DECISIONS A2) ====================
def _row_short(**kw):
    """Bougie 1h merge minimale pour les callbacks d'entree, cote SHORT."""
    base = {"date": T0, "date_4h": T0, "close": 100.0,
            "last_hl_4h": 95.0, "last_lh_4h": 105.0, "atr_4h": 2.0,
            "nearest_res_4h": 130.0, "nearest_sup_4h": 70.0,
            "rr_dispo": 9.0, "rr_dispo_short": 9.0,
            "conviction": 0.9, "conviction_short": 0.8, "regime": "TREND"}
    base.update(kw)
    return pd.DataFrame([base])


def test_can_short_est_actif():
    assert Strat.can_short is True


def test_entry_trend_pose_enter_short():
    s = _inst()
    df = pd.DataFrame({
        "signal_long": [True, False, False, False],
        "signal_short": [False, True, True, False],
        "new_4h": [True, True, False, True],
    })
    out = s.populate_entry_trend(df.copy(), {"pair": "BTC/USDT"})
    assert list(out["enter_long"]) == [1, 0, 0, 0]
    # Meme garde new_4h que le long : jamais deux fois le meme setup 4h.
    assert list(out["enter_short"]) == [0, 1, 0, 0]
    # Colonne toujours posee, meme sans signal short dans le df.
    out = s.populate_entry_trend(pd.DataFrame({"close": [1, 2]}), {})
    assert list(out["enter_short"]) == [0, 0]


def test_confirm_trade_entry_lit_le_rr_du_sens(monkeypatch):
    """Un short doit passer la porte RR sur rr_dispo_short, pas sur le RR long."""
    _capture(monkeypatch)
    seen = {}
    monkeypatch.setattr(strat_mod.risk, "gate_check",
                        lambda p, n, w, t, cfg: (seen.update(cfg) or (True, None, {})))
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.risk, "cb_day_active", lambda w, n, u: False)
    monkeypatch.setattr(strat_mod.Trade, "get_trades_proxy", staticmethod(lambda: []))
    s = _inst()
    s.dp = _DP(_row_short(rr_dispo=9.0, rr_dispo_short=1.0))
    s.config = {"user_data_dir": "user_data", "dry_run": True}
    s.wallets = _Wallets()
    s.confirm_trade_entry("BTC/USDT", T0, side=contracts.DIR_SHORT)
    assert seen["rr"] == 1.0                  # rr_dispo_short, malgre un rr long genereux
    s.confirm_trade_entry("BTC/USDT", T0, side=contracts.DIR_LONG)
    assert seen["rr"] == 9.0


def test_custom_stake_amount_short_utilise_lancre_et_la_cible_baissieres(monkeypatch):
    _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.Trade, "get_trades_proxy", staticmethod(lambda: []))
    s = _inst()
    s.dp = _DP(_row_short())
    s.config = {"user_data_dir": "user_data", "dry_run": True}
    s.wallets = _Wallets(10_000.0)
    stake = s.custom_stake_amount("BTC/USDT", T0, 100.0, 10.0, side=contracts.DIR_SHORT)
    pending = s._pending["BTC/USDT"]
    # SL au-DESSUS de l'entree, ancre sur last_lh_4h (105) + 0,1xATR.
    assert pending["initial_sl"] == pytest.approx(105.0 + params.SL_HL_ATR_BUFFER * 2.0)
    assert pending["initial_sl"] > 100.0
    assert pending["tp1"] < 100.0                       # cible SOUS l'entree
    assert pending["tp2"] == 70.0                       # nearest_sup_4h, pas nearest_res_4h
    assert pending["is_short"] is True
    assert pending["entry_conviction"] == 0.8           # conviction_short, pas conviction
    assert stake > 0                                    # le stake reste positif (taille)
    # Le long sur la MEME bougie prend l'autre ancre et l'autre cible.
    s.custom_stake_amount("BTC/USDT", T0, 100.0, 10.0, side=contracts.DIR_LONG)
    long_pending = s._pending["BTC/USDT"]
    assert long_pending["initial_sl"] < 100.0
    assert long_pending["tp2"] == 130.0
    assert long_pending["is_short"] is False
    assert long_pending["entry_conviction"] == 0.9


def test_custom_stake_amount_short_skip_si_stop_du_mauvais_cote(monkeypatch):
    """LH sous l'entree ET ATR NaN => SL non finie => skip journalise, jamais d'ordre."""
    events = _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.risk, "cb_sequential_state", lambda t, n: (False, 1))
    monkeypatch.setattr(strat_mod.Trade, "get_trades_proxy", staticmethod(lambda: []))
    s = _inst()
    s.dp = _DP(_row_short(atr_4h=float("nan")))
    s.config = {"user_data_dir": "user_data", "dry_run": True}
    s.wallets = _Wallets()
    assert s.custom_stake_amount("BTC/USDT", T0, 100.0, 10.0,
                                 side=contracts.DIR_SHORT) == 0.0
    assert any(et == "gate_check" for et, _ in events)


def test_order_filled_fige_le_sens_dans_le_custom_data(monkeypatch):
    _capture(monkeypatch)
    s = _inst()
    s._pending["BTC/USDT"] = {
        "initial_sl": 110.0, "risk_pct": 0.0116, "signal_id": "SID", "tp1": 85.0,
        "tp2": 70.0, "entry_conviction": 0.8, "entry_regime": "TREND",
        "is_short": True, "trade_no": 1, "ts": T0}   # A3 : tout pending reel porte sa date
    trade = _CDTrade()
    trade.is_open = True
    trade.is_short = True
    trade.pair, trade.open_rate, trade.amount = "BTC/USDT", 100.0, 1.0
    trade.stake_amount, trade.open_date_utc = 1000.0, T0
    s.order_filled("BTC/USDT", trade, type("O", (), {"ft_order_side": "sell"})())
    # ft_order_side 'sell' + is_open : c'est l'ENTREE d'un short, pas une sortie G4.
    state = s._trade_state(trade)
    assert state.is_short is True and state.sign == -1


def test_order_filled_pending_perime_est_recalcule(monkeypatch):
    """A3 (audit 24/08) : une intention deposee il y a des heures ne doit pas etre posee
    telle quelle sur un fill sans rapport. Ordres d'entree en `limit` => cas nominal."""
    events = _capture(monkeypatch)
    monkeypatch.setattr(strat_mod.gestion, "entry_levels", lambda row, entry, sign: (108.0, 84.0, 68.0))
    s = _inst()
    s._pending["BTC/USDT"] = {
        "initial_sl": 110.0, "risk_pct": 0.0116, "signal_id": "VIEUX", "tp1": 85.0,
        "tp2": 70.0, "entry_conviction": 0.8, "entry_regime": "TREND",
        "is_short": True, "trade_no": 1, "ts": T0 - pd.Timedelta(hours=5)}
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: pd.Series({"date": T0}))
    trade = _CDTrade()
    trade.is_open, trade.is_short = True, True
    trade.pair, trade.open_rate, trade.amount = "BTC/USDT", 100.0, 1.0
    trade.stake_amount, trade.open_date_utc = 1000.0, T0
    s.order_filled("BTC/USDT", trade, type("O", (), {"ft_order_side": "sell"})())
    assert s._trade_state(trade).initial_sl == 108.0          # recalcule, pas les 110 perimes
    assert any(et == "system" for et, _ in events)            # et l'anomalie est journalisee


def test_order_filled_pending_perime_sans_row_garde_le_sl(monkeypatch):
    """Corollaire : si la row manque, on GARDE l'intention perimee. Un SL perime vaut mieux
    qu'aucun SL — c'est la lecon de l'audit A1 (shorts sans stop)."""
    _capture(monkeypatch)
    s = _inst()
    s._pending["BTC/USDT"] = {
        "initial_sl": 110.0, "risk_pct": 0.0116, "signal_id": "VIEUX", "tp1": 85.0,
        "tp2": 70.0, "entry_conviction": 0.8, "entry_regime": "TREND",
        "is_short": True, "trade_no": 1, "ts": T0 - pd.Timedelta(hours=5)}
    monkeypatch.setattr(s, "_closed_1h_row", lambda pair: None)
    trade = _CDTrade()
    trade.is_open, trade.is_short = True, True
    trade.pair, trade.open_rate, trade.amount = "BTC/USDT", 100.0, 1.0
    trade.stake_amount, trade.open_date_utc = 1000.0, T0
    s.order_filled("BTC/USDT", trade, type("O", (), {"ft_order_side": "sell"})())
    assert s._trade_state(trade).initial_sl == 110.0


def test_journal_pose_un_run_id_sur_chaque_ligne(tmp_path):
    """C1 (audit 24/08) : sans run_id, deux backtests sur la meme periode s'additionnent
    dans les memes fichiers (nom = jour SIMULE, ouverture en 'a') sans etre separables."""
    strat_mod.journal.set_user_data_dir(tmp_path)
    strat_mod.journal.set_run_id("runA")
    strat_mod.journal.write("system", strat_mod.journal.ev_system("k", {"a": 1}))
    strat_mod.journal.set_run_id("runB")
    strat_mod.journal.write("system", strat_mod.journal.ev_system("k", {"a": 1}))
    lignes = [json.loads(x) for f in (tmp_path / "logs" / "decisions").glob("*.jsonl")
              for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert {li[contracts.RUN_ID_KEY] for li in lignes} == {"runA", "runB"}
    assert all(li["schema_version"] == contracts.SCHEMA_VERSION for li in lignes)


def test_signal_id_supporte_les_paires_futures():
    """Bug latent active par A2 : le ':' des paires perpetuelles est illegal en nom de
    fichier Windows (veto/<signal_id>.intent)."""
    sid = contracts.make_signal_id("BTC/USDT:USDT", T0.to_pydatetime())
    assert ":" not in sid and "/" not in sid
    # Meme signal_id qu'en spot => les journaux restent comparables entre les deux modes.
    assert sid == contracts.make_signal_id("BTC/USDT", T0.to_pydatetime())
