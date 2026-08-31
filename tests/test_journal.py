"""Tests M06 - journal.py : round-trip write/read, rotation au changement de jour UTC,
reconstruction d'un cycle par signal_id, write fail-safe (jamais d'exception),
read_macro_state stale/fail-safe."""

import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from arit_lib import contracts, journal
from arit_lib.contracts import TradeState

UTC = timezone.utc
SID = "BTCUSDT-20260706T120000Z"


@pytest.fixture(autouse=True)
def _base_dir(tmp_path):
    journal.set_user_data_dir(tmp_path)
    return tmp_path


def _decisions_dir(base):
    return base / contracts.DECISIONS_DIR


def _read_records(day_file):
    with open(day_file, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _make_trade(signal_id=SID, **overrides):
    trade = dict(
        pair="BTC/USDT",
        open_rate=25000.0,
        amount=0.5,
        stake_amount=250.0,
        open_date=datetime(2026, 7, 6, 12, 0, tzinfo=UTC),
        close_date=datetime(2026, 7, 6, 18, 0, tzinfo=UTC),
        tp1=25750.0,
        tp2=26500.0,
        signal_id=signal_id,
    )
    trade.update(overrides)
    return SimpleNamespace(**trade)


def _make_state(signal_id=SID):
    return TradeState(
        initial_sl=24500.0,
        risk_pct=0.02,
        entry_conviction=0.72,
        entry_regime="TREND",
        signal_id=signal_id,
    )


def _write_macro(base, updated_iso, **overrides):
    payload = {
        "updated_utc": updated_iso,
        "risk_off": False,
        "fear_greed": 62,
        "next_events": [],
        "stale": False,
    }
    payload.update(overrides)
    (base / contracts.MACRO_STATE_FILE).write_text(json.dumps(payload), encoding="utf-8")


def test_write_read_roundtrip(_base_dir):
    event = journal.ev_entry(_make_trade(), _make_state())
    journal.write("entry", event)

    records = _read_records(_decisions_dir(_base_dir) / "2026-07-06.jsonl")
    assert len(records) == 1
    rec = records[0]
    assert rec["event_type"] == "entry"
    assert rec["schema_version"] == contracts.SCHEMA_VERSION
    assert rec["price"] == 25000.0
    assert rec["qty"] == 0.5
    assert rec["stake"] == 250.0
    assert rec["sl_initial"] == 24500.0
    assert rec["risk_pct"] == 0.02
    assert rec["tp1"] == 25750.0
    assert rec["tp2"] == 26500.0
    assert rec["conviction"] == 0.72
    assert rec["regime"] == "TREND"
    assert rec["signal_id"] == SID
    assert "schema_incomplete" not in rec


def test_rotation_on_utc_day_change(_base_dir):
    journal.write("system", {"kind": "boot", "detail": "d1", "ts_utc": "2026-07-06T23:30:00+00:00"})
    journal.write("system", {"kind": "boot", "detail": "d2", "ts_utc": "2026-07-07T00:30:00+00:00"})

    ddir = _decisions_dir(_base_dir)
    assert (ddir / "2026-07-06.jsonl").exists()
    assert (ddir / "2026-07-07.jsonl").exists()
    assert len(_read_records(ddir / "2026-07-06.jsonl")) == 1
    assert len(_read_records(ddir / "2026-07-07.jsonl")) == 1


def test_reconstruct_cycle_by_signal_id(_base_dir):
    other = "ETHUSDT-20260706T120000Z"
    trade = _make_trade(signal_id=SID)
    state = _make_state(SID)
    row = {
        "regime": "TREND", "adx_4h": 31.0, "ema50_4h": 24800.0, "ema200_4h": 23000.0,
        "s_structure": 1.0, "s_momentum": 0.7, "s_sr": 0.5, "s_patterns": 0.5, "s_volume": 1.0,
        "conviction": 0.72, "seuil": 0.5, "rr_dispo": 2.1,
        "cdl_CDLENGULFING": 100, "cdl_CDLHAMMER": 0,
    }
    explain = {
        "pair": "BTC/USDT", "signal_id": SID, "ts_utc": "2026-07-06T12:00:00+00:00",
        "decision": "signal", "raison": "conviction>=seuil",
        "close_vs_ema": 0.01, "fear_greed": 55, "macro_stale": False,
    }

    journal.write("evaluation", journal.ev_evaluation(row, explain))

    gc = journal.ev_gate_check(
        SID, [{"name": "rr_min", "pass": True, "value": 2.1}], "enter", None, "BTC/USDT"
    )
    gc["ts_utc"] = "2026-07-06T12:05:00+00:00"
    journal.write("gate_check", gc)

    journal.write("entry", journal.ev_entry(trade, state))

    ge = journal.ev_gestion(trade, "G1", 24500.0, 25025.0, 1.0)
    ge["ts_utc"] = "2026-07-06T13:00:00+00:00"
    journal.write("gestion", ge)

    journal.write("exit", journal.ev_exit(trade, "TP1", 1.5, -0.3, 1.8, 0.5, 0.0005))

    # Bruit : autre signal_id + system sans signal_id (memes jours pour rester dans le fichier).
    journal.write("gate_check",
                  journal.ev_gate_check(other, [], "skip", "spread", "ETH/USDT")
                  | {"ts_utc": "2026-07-06T12:00:00+00:00"})
    journal.write("system",
                  journal.ev_system("cb", "noise") | {"ts_utc": "2026-07-06T12:00:00+00:00"})

    records = _read_records(_decisions_dir(_base_dir) / "2026-07-06.jsonl")
    cycle = [r for r in records if r.get("signal_id") == SID]
    assert [r["event_type"] for r in cycle] == [
        "evaluation", "gate_check", "entry", "gestion", "exit",
    ]
    # Un seul libelle de paire sur tout le cycle (format slashe — dataset V2 groupby).
    assert {r["pair"] for r in cycle} == {"BTC/USDT"}
    # cdl_* uniquement dans evaluation.
    assert "cdl_features" in cycle[0]
    assert all("cdl_features" not in r for r in cycle[1:])


def test_write_never_raises_on_io_error(monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise OSError("read-only directory")

    monkeypatch.setattr("builtins.open", boom)
    with caplog.at_level(logging.ERROR):
        journal.write("system", journal.ev_system("boot", "x"))  # ne doit pas lever

    assert any(rec.levelno == logging.ERROR for rec in caplog.records)
    assert "journal.write" in caplog.text


def test_write_missing_field_flags_incomplete(_base_dir, caplog):
    with caplog.at_level(logging.ERROR):
        # 'detail' absent => schema_incomplete + logging.error, ligne ecrite quand meme.
        journal.write("system", {"kind": "boot", "ts_utc": "2026-07-06T12:00:00+00:00"})

    rec = _read_records(_decisions_dir(_base_dir) / "2026-07-06.jsonl")[0]
    assert rec["schema_incomplete"] is True
    assert rec["kind"] == "boot"
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_macro_state_fresh_not_stale(_base_dir):
    t0 = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    _write_macro(_base_dir, t0.isoformat())
    state = journal.read_macro_state(now=t0 + timedelta(hours=1, minutes=59))
    assert state["stale"] is False
    assert state["risk_off"] is False
    assert state["fear_greed"] == 62


def test_macro_state_becomes_stale(_base_dir):
    t0 = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    _write_macro(_base_dir, t0.isoformat())
    state = journal.read_macro_state(now=t0 + timedelta(hours=2, minutes=1))
    assert state["stale"] is True
    assert state["risk_off"] is True


def test_macro_state_absent_is_failsafe(_base_dir):
    state = journal.read_macro_state(now=datetime(2026, 7, 6, 12, 0, tzinfo=UTC))
    assert state["risk_off"] is True
    assert state["stale"] is True
    assert state[contracts.MACRO_SCORES_KEY] == {}     # parite A2 : aucun score => HOSTILE


# -------------------------------------------- parite live A2 : traversee des scores 06.2
def test_macro_state_fait_transiter_les_scores(_base_dir):
    """Les 5 scores doivent atteindre macro_regime.regime_now via la strategie."""
    t0 = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    scores = {"dxy": 1, "taux": 0, "stablecoins": -1, "funding": 0, "fear_greed": 1}
    _write_macro(_base_dir, t0.isoformat(), **{contracts.MACRO_SCORES_KEY: scores})
    state = journal.read_macro_state(now=t0 + timedelta(minutes=5))
    assert state[contracts.MACRO_SCORES_KEY] == scores
    # `fear_greed` de premier niveau reste l'indice BRUT : deux sens, deux emplacements.
    assert state["fear_greed"] == 62


@pytest.mark.parametrize("brut", [None, [], "porteur", 3])
def test_macro_state_scores_hors_schema_sont_ignores(_base_dir, brut):
    """Fichier bricole ou d'une version anterieure : on retombe sur {} (=> HOSTILE => repos),
    jamais sur une valeur que regime_now tenterait d'indexer."""
    t0 = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
    _write_macro(_base_dir, t0.isoformat(), **{contracts.MACRO_SCORES_KEY: brut})
    state = journal.read_macro_state(now=t0 + timedelta(minutes=5))
    assert state[contracts.MACRO_SCORES_KEY] == {}


# ------- schema v3 : direction_macro dans regime_inputs (correctif 2026-08-07) -------
def test_evaluation_porte_direction_macro():
    """Declare depuis le 04/08 dans cio.explain et contracts (par.8.1) mais jamais ECRIT :
    la clef etait absente de TOUS les journaux, donc le Test 1 de docs/01 (« la macro
    donne-t-elle la direction ? ») n'etait pas mesurable — la raison d'etre de A2."""
    row = {"regime": "TREND", "conviction": 0.8, "seuil": 0.5,
           contracts.MACRO_REGIME_COL: "PORTEUR", "direction_macro": contracts.DIR_LONG}
    rec = journal.ev_evaluation(row, {"pair": "BTC/USDT:USDT", "decision": "signal"})
    assert rec["regime_inputs"]["direction_macro"] == contracts.DIR_LONG


def test_evaluation_direction_macro_absente_reste_none():
    """Backtest sans la colonne : la clef EXISTE et vaut None, elle ne disparait pas —
    sinon les journaux ne sont pas comparables entre eux."""
    rec = journal.ev_evaluation({"regime": "RANGE"}, {"pair": "BTC/USDT:USDT"})
    assert "direction_macro" in rec["regime_inputs"]
    assert rec["regime_inputs"]["direction_macro"] is None


# --------------------------------------------------------------------------------------
# D3 (audit 24/08) — trois variables d'env changent le comportement de trading sans laisser
# de trace : un run n'etait pas rejouable depuis son propre journal. Une ligne 'system'
# kind='protocole' est desormais emise UNE fois par run, a la premiere ecriture.
# --------------------------------------------------------------------------------------


def _lignes_du_jour(base):
    fichiers = sorted(_decisions_dir(base).glob("*.jsonl"))
    assert fichiers, "aucun fichier de journal ecrit"
    records = []
    for fichier in fichiers:
        records.extend(_read_records(fichier))
    return records


def test_protocole_ecrit_une_fois_et_en_premier(_base_dir):
    journal.set_run_id("run-protocole")          # rearme l'emission
    journal.write("system", journal.ev_system("premier", {}))
    journal.write("system", journal.ev_system("second", {}))
    records = _lignes_du_jour(_base_dir)
    protocoles = [r for r in records if r["kind"] == contracts.SYSTEM_KIND_PROTOCOLE]
    assert len(protocoles) == 1, "le protocole doit etre emis une seule fois par run"
    assert records[0]["kind"] == contracts.SYSTEM_KIND_PROTOCOLE
    assert records[0]["run_id"] == "run-protocole"


def test_protocole_porte_les_trois_variables(_base_dir):
    journal.set_run_id("run-detail")
    journal.write("system", journal.ev_system("declencheur", {}))
    protocole = _lignes_du_jour(_base_dir)[0]
    assert set(protocole["detail"]) == {
        "ARIT_G_OFF", "ARIT_CONTROL_A", "ARIT_CHOCH_PRIORITY"}


def test_set_run_id_rearme_le_protocole(_base_dir):
    journal.set_run_id("run-a")
    journal.write("system", journal.ev_system("a", {}))
    journal.set_run_id("run-b")
    journal.write("system", journal.ev_system("b", {}))
    protocoles = [r for r in _lignes_du_jour(_base_dir)
                  if r["kind"] == contracts.SYSTEM_KIND_PROTOCOLE]
    assert [p["run_id"] for p in protocoles] == ["run-a", "run-b"]
