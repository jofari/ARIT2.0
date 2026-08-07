"""Tests M10 - services/watchdog.py : age du heartbeat, double-lecture anti-faux-positif,
flatten idempotent (mock ccxt), dust threshold."""

import sys
import time
from pathlib import Path

SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

import watchdog  # noqa: E402


class _FakeClient:
    """ccxt mock : balance + tickers + compteurs d'ordres."""

    def __init__(self, totals, prices):
        self._totals = totals
        self._prices = prices
        self.cancelled = []
        self.sold = []

    def fetch_balance(self):
        return {"total": self._totals}

    def fetch_ticker(self, symbol):
        asset = symbol.split("/")[0]
        return {"last": self._prices[asset]}

    def cancel_all_orders(self, symbol):
        self.cancelled.append(symbol)

    def create_market_sell_order(self, symbol, amount):
        self.sold.append((symbol, amount))


# ----------------------------------------------------------------- heartbeat
def test_heartbeat_age_recent(tmp_path):
    hb = tmp_path / "heartbeat"
    hb.write_text("")
    assert watchdog.heartbeat_age(hb) < 5


def test_heartbeat_age_old(tmp_path):
    hb = tmp_path / "heartbeat"
    hb.write_text("")
    old = time.time() - 700
    import os
    os.utime(hb, (old, old))
    assert watchdog.heartbeat_age(hb) > watchdog.HEARTBEAT_MAX_S


def test_heartbeat_age_missing_is_inf(tmp_path):
    assert watchdog.heartbeat_age(tmp_path / "nope") == float("inf")


# ----------------------------------------------------------------- dust threshold
def test_open_exposure_ignores_dust_and_usdt():
    # ETH 0.001 * 2000 = 2 USDT (> dust) ; DOGE 1 * 0.1 = 0.1 USDT (dust) ; USDT ignore
    client = _FakeClient(
        totals={"USDT": 500.0, "ETH": 0.001, "DOGE": 1.0},
        prices={"ETH": 2000.0, "DOGE": 0.1},
    )
    holdings = watchdog.open_exposure(client)
    assets = {h["asset"] for h in holdings}
    assert assets == {"ETH"}


def test_open_exposure_empty_when_only_dust():
    client = _FakeClient(totals={"DOGE": 1.0}, prices={"DOGE": 0.1})
    assert watchdog.open_exposure(client) == []


# ------------------------------------------------ double-lecture anti-faux-positif
def test_confirm_reads_requires_two_consecutive():
    consecutive = 0
    consecutive = watchdog.next_consecutive(True, consecutive)
    assert consecutive == 1 and watchdog.ready_to_act(consecutive) is False
    consecutive = watchdog.next_consecutive(True, consecutive)
    assert consecutive == 2 and watchdog.ready_to_act(consecutive) is True


def test_consecutive_resets_when_condition_clears():
    consecutive = watchdog.next_consecutive(True, 1)
    consecutive = watchdog.next_consecutive(False, consecutive)
    assert consecutive == 0


def test_is_breach_requires_age_and_exposure():
    holdings = [{"asset": "ETH", "amount": 1, "value_usdt": 100}]
    assert watchdog.is_breach(watchdog.HEARTBEAT_MAX_S + 1, holdings) is True
    assert watchdog.is_breach(watchdog.HEARTBEAT_MAX_S + 1, []) is False
    assert watchdog.is_breach(10, holdings) is False


# ----------------------------------------------------------------- flatten idempotent
def test_flatten_idempotent(tmp_path):
    watchdog.set_user_data_dir(tmp_path)
    if watchdog._flatten_flag().exists():
        watchdog._flatten_flag().unlink()
    client = _FakeClient(totals={"ETH": 1.0}, prices={"ETH": 2000.0})
    holdings = [{"asset": "ETH", "amount": 1.0, "value_usdt": 2000.0}]

    watchdog.flatten(client, holdings)
    assert client.sold == [("ETH/USDT", 1.0)]
    assert watchdog._flatten_flag().exists()

    watchdog.flatten(client, holdings)  # 2e appel : no-op
    assert client.sold == [("ETH/USDT", 1.0)]
    assert client.cancelled == ["ETH/USDT"]


def test_flatten_enabled_env(monkeypatch):
    monkeypatch.setenv(watchdog.FLATTEN_ENV, "true")
    assert watchdog._flatten_enabled() is True
    monkeypatch.setenv(watchdog.FLATTEN_ENV, "false")
    assert watchdog._flatten_enabled() is False
    monkeypatch.delenv(watchdog.FLATTEN_ENV, raising=False)
    assert watchdog._flatten_enabled() is False


# ------------- webhook : environnement OU .env (correctif 2026-08-07) -------------
def test_webhook_prend_l_environnement_en_priorite(monkeypatch):
    monkeypatch.setenv(watchdog.WEBHOOK_ENV, "https://exemple/hook-env")
    assert watchdog._webhook_url() == "https://exemple/hook-env"


def test_webhook_retombe_sur_le_fichier_env(monkeypatch, tmp_path):
    """LE correctif : les secrets ne vivent que dans .env et rien ne les chargeait dans
    l'environnement des services lances par start_arit.py. alert() sortait en SILENCE."""
    monkeypatch.delenv(watchdog.WEBHOOK_ENV, raising=False)
    env = tmp_path / ".env"
    env.write_text('# commentaire\nAUTRE=x\n'
                   f'{watchdog.WEBHOOK_ENV}="https://exemple/hook-fichier"\n', encoding="utf-8")
    monkeypatch.setattr(watchdog, "__file__", str(tmp_path / "services" / "watchdog.py"))
    assert watchdog._webhook_url() == "https://exemple/hook-fichier"


def test_webhook_absent_partout_est_none(monkeypatch, tmp_path):
    monkeypatch.delenv(watchdog.WEBHOOK_ENV, raising=False)
    monkeypatch.setattr(watchdog, "__file__", str(tmp_path / "services" / "watchdog.py"))
    assert watchdog._webhook_url() is None


def test_alerte_sans_webhook_est_signalee_pas_silencieuse(monkeypatch, caplog):
    """Une alerte non envoyee doit laisser une trace : c'est la panne la plus couteuse
    possible pour un filet de securite, elle ne doit jamais etre muette."""
    monkeypatch.setattr(watchdog, "_webhook_url", lambda: None)
    with caplog.at_level("ERROR"):
        watchdog.alert(watchdog.LEVEL_CRITICAL, "bot mort")
    assert "ALERTE NON ENVOYEE" in caplog.text
