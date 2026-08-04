"""Tests M04 — risk.py. Fakes duck-type construits a la main (aucun import freqtrade)."""

from datetime import datetime, timedelta, timezone

import json

from arit_lib import contracts, params, risk

NOW = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)  # lundi, semaine ISO 2026-W28
SEUIL = params.SEUIL_TREND  # 0.50


class FakeTrade:
    def __init__(self, *, is_open=False, open_rate=100.0, stop_loss=90.0, amount=1.0,
                 close_rate=None, open_date_utc=None, close_date_utc=None, **custom):
        self.is_open = is_open
        self.open_rate = open_rate
        self.stop_loss = stop_loss
        self.amount = amount
        self.close_rate = close_rate if close_rate is not None else open_rate
        self.open_date_utc = open_date_utc
        self.close_date_utc = close_date_utc
        self.custom_data = dict(custom)

    def get_custom_data(self, key, default=None):
        return self.custom_data.get(key, default)


class FakeWallets:
    def __init__(self, equity):
        self._equity = float(equity)

    def get_total_stake_amount(self):
        return self._equity


def _write_macro(base, *, stale=False, events=None):
    (base).mkdir(parents=True, exist_ok=True)
    payload = {"updated_utc": NOW.isoformat(), "risk_off": False, "fear_greed": 60,
               "next_events": events or [], "stale": stale}
    (base / contracts.MACRO_STATE_FILE).write_text(json.dumps(payload), encoding="utf-8")


def _base_cfg(base, **over):
    cfg = {"regime": "TREND", "spread_frac": None, "rr": 2.0, "risk_pct": 0.01,
           "signal_id": "BTCUSDT-20260706T120000Z", "veto_window_min": 0,
           "user_data_dir": base}
    cfg.update(over)
    return cfg


# ------------------------------------------------------------------- sizing
def test_risk_pct_constant():
    # A6 (docs/03 §3.1.0) : le risque ne depend PLUS de la conviction — meme valeur au
    # seuil et a conviction maximale. C'est le test qui verrouille la suspension de §3.1.1.
    assert risk.compute_risk_pct(SEUIL, SEUIL, 1) == params.RISK_CONSTANT_PCT
    assert risk.compute_risk_pct(1.0, SEUIL, 1) == params.RISK_CONSTANT_PCT
    # CB seq : le diviseur 2 continue de s'appliquer.
    assert risk.compute_risk_pct(1.0, SEUIL, 1, cb_divisor=2) == params.RISK_CONSTANT_PCT / 2


def test_cap_borne_le_risque_constant():
    # Les caps 2 %/3 % restent en vigueur et BORNENT le constant (non mordants : 1,16 % < 2 %).
    assert risk.compute_risk_pct(1.0, SEUIL, 100) == min(
        params.RISK_CONSTANT_PCT, params.RISK_CAP_FIRST_PCT)
    assert risk.compute_risk_pct(1.0, SEUIL, 101) == min(
        params.RISK_CONSTANT_PCT, params.RISK_CAP_AFTER_PCT)


def test_compute_stake_zero_stop_distance():
    assert risk.compute_stake(10_000, 0.02, 100.0, 100.0) == (
        None, contracts.SKIP_ZERO_STOP_DISTANCE)
    assert risk.compute_stake(10_000, 0.02, 100.0, 105.0) == (
        None, contracts.SKIP_ZERO_STOP_DISTANCE)
    stake, reason = risk.compute_stake(10_000, 0.02, 100.0, 98.0)
    assert reason is None and stake == 10_000 * 0.02 / 0.02


def test_compute_stake_min_notional():
    # stake=1000 < min_notional=2000 ; forcer reste sous le cap 2 % => force a 2000.
    assert risk.compute_stake(10_000, 0.001, 100.0, 99.0,
                              min_notional=2000, risk_cap_pct=0.02) == (2000, None)
    # forcer depasserait le cap 0,15 % => skip.
    assert risk.compute_stake(10_000, 0.001, 100.0, 99.0,
                              min_notional=2000, risk_cap_pct=0.0015) == (None,
                                                                          contracts.SKIP_MIN_NOTIONAL)


# --------------------------------------------------------- budgets / DB
def test_residual_be_zero():
    be = FakeTrade(is_open=True, open_rate=100.0, stop_loss=101.0, amount=1.0)  # SL >= entree
    assert risk.residual_risk_total([be], 10_000) == 0.0
    risky = FakeTrade(is_open=True, open_rate=100.0, stop_loss=95.0, amount=2.0)
    assert risk.residual_risk_total([risky], 10_000) == 2.0 * 5.0 / 10_000


def test_trade_counter():
    trades = [FakeTrade(), FakeTrade(is_open=True), FakeTrade()]
    assert risk.trade_counter(trades) == 3


def _seq_losses():
    """2 pertes consecutives a -0.8R exactement, trigger_ts = NOW."""
    loss = dict(open_rate=100.0, initial_sl=90.0, close_rate=92.0, is_open=False)
    return [FakeTrade(**loss, close_date_utc=NOW - timedelta(hours=2),
                      open_date_utc=NOW - timedelta(hours=10)),
            FakeTrade(**loss, close_date_utc=NOW,
                      open_date_utc=NOW - timedelta(hours=8))]


def test_cb_sequential_minus_08r_exact():
    # entry 100, initial_sl 90 => dist 10 ; close 92 => R = -0.8 exact => declenche.
    assert risk.cb_sequential_state(_seq_losses(), now=NOW) == (
        True, params.CB_SEQ_RISK_DIVISOR)
    # -0.79R (close 92.1) sur la derniere => pas de declenchement.
    trades = _seq_losses()
    trades[-1] = FakeTrade(open_rate=100.0, initial_sl=90.0, close_rate=92.1,
                           close_date_utc=NOW, is_open=False,
                           open_date_utc=NOW - timedelta(hours=8))
    assert risk.cb_sequential_state(trades, now=NOW) == (False, 1)


def test_cb_sequential_cooldown_12e_vs_13e_bougie():
    trades = _seq_losses()
    # pendant la 12e bougie 1h apres le trigger => cooldown actif.
    in_12th = NOW + timedelta(hours=params.CB_SEQ_COOLDOWN_CANDLES_1H) - timedelta(minutes=30)
    assert risk.cb_sequential_state(trades, now=in_12th)[0] is True
    # 13e bougie (>= trigger + 12 h) => cooldown termine.
    in_13th = NOW + timedelta(hours=params.CB_SEQ_COOLDOWN_CANDLES_1H)
    assert risk.cb_sequential_state(trades, now=in_13th)[0] is False


def test_cb_sequential_penalty_5e_vs_6e_trade():
    later = NOW + timedelta(days=2)

    def post_trades(n):
        return [FakeTrade(is_open=False, open_rate=100.0, initial_sl=90.0,
                          close_rate=101.0, open_date_utc=NOW + timedelta(hours=13 + i),
                          close_date_utc=NOW + timedelta(hours=14 + i))
                for i in range(n)]
    # 4 trades ouverts apres le trigger => le 5e a venir reste penalise (/2).
    trades = _seq_losses() + post_trades(params.CB_SEQ_PENALTY_TRADES - 1)
    assert risk.cb_sequential_state(trades, now=later)[1] == params.CB_SEQ_RISK_DIVISOR
    # 5 trades ouverts apres le trigger => le 6e n'est plus penalise.
    trades = _seq_losses() + post_trades(params.CB_SEQ_PENALTY_TRADES)
    assert risk.cb_sequential_state(trades, now=later)[1] == 1


# ------------------------------------------------------- CB jour (etat)
def _write_day_equity(base, equity):
    (base / "state").mkdir(parents=True, exist_ok=True)
    (base / contracts.DAY_EQUITY_FILE).write_text(
        json.dumps({"date": "2026-07-06", "equity": equity}), encoding="utf-8")


def test_cb_day_boundary(tmp_path):
    _write_day_equity(tmp_path, 10_000)
    # -5,99 % => 9401 > seuil 9400 => pas de blocage.
    assert risk.cb_day_active(FakeWallets(9401), NOW, tmp_path) is False
    # -6,00 % EXACTEMENT => bloque (PDR 03.5 "<= -6 %").
    assert risk.cb_day_active(FakeWallets(9400), NOW, tmp_path) is True
    # -6,01 % => 9399 => blocage.
    assert risk.cb_day_active(FakeWallets(9399), NOW, tmp_path) is True


def test_snapshot_day_equity(tmp_path):
    risk.snapshot_day_equity_if_new_day(FakeWallets(10_000), NOW, tmp_path)
    data = json.loads((tmp_path / contracts.DAY_EQUITY_FILE).read_text(encoding="utf-8"))
    assert data == {"date": "2026-07-06", "equity": 10_000.0}
    # meme jour => pas d'ecrasement.
    risk.snapshot_day_equity_if_new_day(FakeWallets(12_345), NOW, tmp_path)
    data = json.loads((tmp_path / contracts.DAY_EQUITY_FILE).read_text(encoding="utf-8"))
    assert data["equity"] == 10_000.0


# --------------------------------------------------------------- gates
def test_gate_full_pass(tmp_path):
    _write_macro(tmp_path)
    ok, gate, metrics = risk.gate_check(
        "BTC/USDT", NOW, FakeWallets(10_000), [], _base_cfg(tmp_path))
    assert ok is True and gate is None
    assert metrics["veto"] == "dryrun"


def test_gate_order_stops_at_first_fail(tmp_path):
    # regime OK (gate1) mais macro_state absent => DECISION au gate2 news_window ;
    # les metriques pures des gates suivants sont quand meme mesurees (08.1),
    # seul le veto (effet de bord .intent) reste non evalue.
    ok, gate, metrics = risk.gate_check(
        "BTC/USDT", NOW, FakeWallets(10_000), [],
        _base_cfg(tmp_path, regime="TREND",
                  veto_window_min=params.VETO_WINDOW_MIN_CANARI))
    assert ok is False
    assert gate == contracts.GATE_NAMES[1] == "news_window"
    for key in ("spread", "slots", "residual_total", "weekly_risk",
                "weekly_entries", "rr"):
        assert key in metrics
    assert metrics["veto"] == "not_evaluated"
    assert not (tmp_path / contracts.VETO_DIR).exists()  # aucun .intent cree


def test_gate_regime_first(tmp_path):
    _write_macro(tmp_path)
    ok, gate, _ = risk.gate_check(
        "BTC/USDT", NOW, FakeWallets(10_000), [], _base_cfg(tmp_path, regime="RANGE"))
    assert ok is False and gate == "regime"


def test_gate_weekly_budget_boundary(tmp_path):
    _write_macro(tmp_path)
    engaged = [FakeTrade(is_open=True, open_rate=100.0, stop_loss=99.0, amount=1.0,
                         open_date_utc=NOW, risk_pct=0.06)]
    wallets = FakeWallets(10_000)
    # 0,06 + 0,0199 = 0,0799 <= 8 % => pass.
    ok, _, _ = risk.gate_check("BTC/USDT", NOW, wallets, engaged,
                               _base_cfg(tmp_path, risk_pct=0.0199))
    assert ok is True
    # 0,06 + 0,0201 = 0,0801 > 8 % => fail weekly_budget.
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, wallets, engaged,
                                  _base_cfg(tmp_path, risk_pct=0.0201))
    assert ok is False and gate == "weekly_budget"


def test_gate_weekly_entries_boundary(tmp_path):
    _write_macro(tmp_path)
    wallets = FakeWallets(10_000)
    # trades CLOS (n'occupent pas de slot) ouverts cette semaine, risque negligeable.
    def week_trades(n):
        return [FakeTrade(is_open=False, open_date_utc=NOW, risk_pct=0.0001)
                for _ in range(n)]
    ok, _, _ = risk.gate_check("BTC/USDT", NOW, wallets, week_trades(9),
                               _base_cfg(tmp_path, risk_pct=0.001))
    assert ok is True  # 9 entrees < 10
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, wallets, week_trades(10),
                                  _base_cfg(tmp_path, risk_pct=0.001))
    assert ok is False and gate == "weekly_budget"  # 10 entrees => fail


def test_gate_slots(tmp_path):
    _write_macro(tmp_path)
    opens = [FakeTrade(is_open=True, open_rate=100.0, stop_loss=99.0, open_date_utc=NOW)
             for _ in range(params.MAX_OPEN_TRADES)]
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), opens,
                                  _base_cfg(tmp_path))
    assert ok is False and gate == "slots"


def test_gate_news_event_window(tmp_path):
    event = {"name": "CPI US", "time_utc": (NOW + timedelta(minutes=10)).isoformat(),
             "impact": "high"}
    _write_macro(tmp_path, events=[event])
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [],
                                  _base_cfg(tmp_path))
    assert ok is False and gate == "news_window"


def test_gate_spread_and_rr(tmp_path):
    _write_macro(tmp_path)
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [],
                                  _base_cfg(tmp_path, spread_frac=0.01))
    assert ok is False and gate == "spread"
    ok, gate, _ = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [],
                                  _base_cfg(tmp_path, rr=1.0))
    assert ok is False and gate == "rr_min"


# ---------------------------------------------------- veto canari (11.6)
def test_veto_window_zero_pass(tmp_path):
    _write_macro(tmp_path)
    ok, gate, metrics = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [],
                                        _base_cfg(tmp_path, veto_window_min=0))
    assert ok is True and metrics["veto"] == "dryrun"


def test_veto_intent_then_expiration(tmp_path):
    _write_macro(tmp_path)
    cfg = _base_cfg(tmp_path, veto_window_min=params.VETO_WINDOW_MIN_CANARI)
    ok, gate, metrics = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [], cfg)
    assert ok is False and gate == "veto_canari" and metrics["intent_created"] is True
    later = NOW + timedelta(minutes=params.VETO_WINDOW_MIN_CANARI + 1)
    ok, gate, metrics = risk.gate_check("BTC/USDT", later, FakeWallets(10_000), [], cfg)
    assert ok is True and metrics["veto"] == "expired"


def test_veto_flag_blocks(tmp_path):
    _write_macro(tmp_path)
    veto_dir = tmp_path / contracts.VETO_DIR
    veto_dir.mkdir(parents=True, exist_ok=True)
    (veto_dir / "BTCUSDT-20260706T120000Z.flag").touch()
    cfg = _base_cfg(tmp_path, veto_window_min=params.VETO_WINDOW_MIN_CANARI)
    ok, gate, metrics = risk.gate_check("BTC/USDT", NOW, FakeWallets(10_000), [], cfg)
    assert ok is False and gate == "veto_canari" and metrics["veto"] == "human_veto"
