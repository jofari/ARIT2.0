"""Tests M08 - services/macro_state.py : build_state (event 29/31 min, fg 24/25/44/45),
atomicite (echec pendant write => ancien fichier intact), stale a 1h59/2h01."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

import macro_state  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 7, 7, 12, 0, tzinfo=UTC)

# Parite A2 : jeu de scores 06.2 EXPLOITABLE (somme 1 => NEUTRE). Sans lui, build_state
# declare l'etat stale a dessein — c'est le fail-safe teste plus bas, pas le cas nominal.
SCORES = {"dxy": 1, "taux": 0, "stablecoins": 0, "funding": 0, "fear_greed": 0}


def _event(minutes_from_now, name="CPI US"):
    when = NOW + timedelta(minutes=minutes_from_now)
    return {"name": name, "time_utc": when.isoformat(), "impact": "high"}


def _scores_ok(monkeypatch, scores=None):
    """main() lit l'historique macro sur disque ; en test on fixe le resultat."""
    monkeypatch.setattr(macro_state, "component_scores",
                        lambda *a, **k: SCORES if scores is None else scores)


# ----------------------------------------------------------------- build_state
def test_build_state_schema_keys():
    state = macro_state.build_state([], 50, NOW, SCORES)
    assert set(state) == {"updated_utc", "risk_off", "fear_greed", "next_events", "stale",
                          macro_state.contracts.MACRO_SCORES_KEY}
    assert state["updated_utc"] == NOW.isoformat()
    assert state["stale"] is False
    assert state["fear_greed"] == 50
    # `fear_greed` reste l'indice BRUT au premier niveau ; son SCORE 06.2 vit dans le
    # sous-objet. Confondre les deux ferait sommer 50 comme un score (=> PORTEUR toujours).
    assert state[macro_state.contracts.MACRO_SCORES_KEY]["fear_greed"] == 0


def test_build_state_event_29_min_is_risk_off():
    state = macro_state.build_state([_event(29)], 50, NOW)
    assert state["risk_off"] is True


def test_build_state_event_31_min_not_risk_off():
    state = macro_state.build_state([_event(31)], 50, NOW, SCORES)
    assert state["risk_off"] is False
    # mais l'event reste dans next_events (<= 48 h)
    assert len(state["next_events"]) == 1


@pytest.mark.parametrize("fg,expected", [(24, True), (25, False), (44, False), (45, False)])
def test_build_state_fear_greed_threshold(fg, expected):
    state = macro_state.build_state([], fg, NOW, SCORES)
    assert state["risk_off"] is expected


# ------------------------------------------------- parite A2 : scores macro (2026-08-07)
@pytest.mark.parametrize("scores", [None, {}])
def test_build_state_sans_scores_est_stale_et_risk_off(scores):
    """Fail-safe central du dry-run non surveille : fonda non alimentee => le bot se met au
    REPOS. Ecrire des zeros donnerait NEUTRE, donc long ET short autorises a l'aveugle."""
    state = macro_state.build_state([], 50, NOW, scores)
    assert state["stale"] is True
    assert state["risk_off"] is True
    assert state[macro_state.contracts.MACRO_SCORES_KEY] == {}


def test_component_scores_none_si_historique_absent(tmp_path):
    assert macro_state.component_scores(tmp_path / "vide", NOW) is None


def test_component_scores_none_si_historique_perime(tmp_path, monkeypatch):
    """Historique lisible mais vieux de > MACRO_STALE_HOURS => None, pas des zeros."""
    import pandas as pd
    vieux = NOW - timedelta(hours=macro_state.params.MACRO_STALE_HOURS + 24)
    daily = pd.DataFrame({k: [0] for k in macro_state.contracts.MACRO_SCORE_KEYS},
                         index=pd.to_datetime([vieux], utc=True))
    monkeypatch.setattr(macro_state.macro_regime, "load_history", lambda d: daily)
    monkeypatch.setattr(macro_state.macro_regime, "daily_regimes", lambda h: daily)
    assert macro_state.component_scores(tmp_path, NOW) is None


def test_component_scores_ne_leve_jamais(tmp_path, monkeypatch):
    """Le service doit TOUJOURS pouvoir ecrire son fichier, meme historique corrompu."""
    monkeypatch.setattr(macro_state.macro_regime, "load_history",
                        lambda d: (_ for _ in ()).throw(ValueError("corrompu")))
    assert macro_state.component_scores(tmp_path, NOW) is None


def test_build_state_next_events_sorted_capped_and_horizon():
    events = [_event(60 * 40, "CPI"), _event(60 * 10, "FOMC"), _event(60 * 20, "NFP"),
              _event(60 * 60, "rate decision")]  # dernier > 48 h => exclu
    state = macro_state.build_state(events, 50, NOW)
    assert len(state["next_events"]) == macro_state.params.NEXT_EVENTS_MAX
    times = [e["time_utc"] for e in state["next_events"]]
    assert times == sorted(times)


# ----------------------------------------------------------------- stale
def test_stale_below_two_hours_is_false():
    updated = (NOW - timedelta(hours=1, minutes=59)).isoformat()
    assert macro_state._stale(updated, NOW) is False


def test_stale_above_two_hours_is_true():
    updated = (NOW - timedelta(hours=2, minutes=1)).isoformat()
    assert macro_state._stale(updated, NOW) is True


def test_stale_missing_updated_is_true():
    assert macro_state._stale(None, NOW) is True


# ----------------------------------------------------------------- atomicite
def test_write_atomic_roundtrip(tmp_path):
    path = tmp_path / "macro_state.json"
    state = macro_state.build_state([_event(120)], 62, NOW)
    macro_state.write_atomic(state, path)
    assert json.loads(path.read_text(encoding="utf-8")) == state


def test_write_atomic_failure_keeps_old_file_intact(tmp_path):
    path = tmp_path / "macro_state.json"
    old = {"updated_utc": NOW.isoformat(), "risk_off": False,
           "fear_greed": 60, "next_events": [], "stale": False}
    macro_state.write_atomic(old, path)

    class _Unserializable:
        pass

    with pytest.raises(TypeError):
        macro_state.write_atomic({"bad": _Unserializable()}, path)
    # ancien fichier intact, aucun tmp residuel
    assert json.loads(path.read_text(encoding="utf-8")) == old
    assert not (tmp_path / "macro_state.json.tmp").exists()


# ------------------------------- C1 : le calendrier ne fait plus de reseau dans ce run
def _cal(events, primaire_ok=True, secondaire_ok=True, trous=()):
    """Stub de calendar_source.load_events (C1). Signature (user_data_dir, now)."""
    meta = {"primaire": {"ok": primaire_ok, "n": len(events)},
            "secondaire": {"ok": secondaire_ok, "raison": None if secondaire_ok else "perime"},
            "total": len(events), "trous_couverture": list(trous)}
    return lambda _d, _n: (list(events), meta)


def test_finnhub_a_ete_retire(monkeypatch):
    """C1 : plus aucune clef, plus aucun appel calendrier au runtime horaire."""
    assert not hasattr(macro_state, "fetch_calendar")
    assert not hasattr(macro_state, "FINNHUB_ENV")


def test_main_ne_bloque_pas_quand_forexfactory_est_indisponible(tmp_path, monkeypatch):
    """Degradation VOULUE (Jonas 03/08) : FF en echec => on continue sur la primaire."""
    macro_state.set_user_data_dir(tmp_path)
    # Evenement calé sur l'heure REELLE : main() utilise _now_utc(), pas la constante NOW.
    soon = (macro_state._now_utc() + timedelta(hours=6)).isoformat()
    primaire = [{"name": "FOMC rate decision", "time_utc": soon, "impact": "high"}]
    monkeypatch.setattr(macro_state.calendar_source, "load_events",
                        _cal(primaire, secondaire_ok=False))
    monkeypatch.setattr(macro_state, "fetch_fear_greed", lambda: 55)
    _scores_ok(monkeypatch)
    code = macro_state.main()
    assert code == macro_state.EXIT_OK          # PAS un echec : la primaire suffit
    written = json.loads((tmp_path / macro_state.contracts.MACRO_STATE_FILE).read_text("utf-8"))
    assert written["stale"] is False
    assert len(written["next_events"]) == 1     # l'evenement de la primaire est bien la


def test_main_journalise_les_trous_de_couverture(tmp_path, monkeypatch, caplog):
    """Un trou sur un des trois evenements qui comptent n'est JAMAIS silencieux."""
    import logging
    macro_state.set_user_data_dir(tmp_path)
    monkeypatch.setattr(macro_state.calendar_source, "load_events",
                        _cal([], trous=("CPI", "NFP")))
    monkeypatch.setattr(macro_state, "fetch_fear_greed", lambda: 55)
    with caplog.at_level(logging.ERROR):
        macro_state.main()
    assert "CPI" in caplog.text and "NFP" in caplog.text


# ----------------------------------------------------------------- main
def test_main_partial_uses_old_value_on_source_failure(tmp_path, monkeypatch):
    macro_state.set_user_data_dir(tmp_path)
    old = macro_state.build_state([], 60, NOW - timedelta(minutes=30), SCORES)
    macro_state.write_atomic(old, tmp_path / macro_state.contracts.MACRO_STATE_FILE)

    monkeypatch.setattr(macro_state.calendar_source, "load_events", _cal([_event(120)]))
    monkeypatch.setattr(macro_state, "fetch_fear_greed",
                        lambda: (_ for _ in ()).throw(RuntimeError("down")))
    _scores_ok(monkeypatch)

    code = macro_state.main()
    assert code == macro_state.EXIT_PARTIAL
    written = json.loads((tmp_path / macro_state.contracts.MACRO_STATE_FILE).read_text("utf-8"))
    assert written["fear_greed"] == 60  # valeur reprise de l'ancien fichier
    assert written["stale"] is False


def test_main_total_failure_no_old_is_fail_safe(tmp_path, monkeypatch):
    """Echec TOTAL = source primaire illisible (anomalie de deploiement) ET F&G mort."""
    macro_state.set_user_data_dir(tmp_path)
    monkeypatch.setattr(macro_state.calendar_source, "load_events",
                        _cal([], primaire_ok=False))
    monkeypatch.setattr(macro_state, "fetch_fear_greed",
                        lambda: (_ for _ in ()).throw(RuntimeError("down")))

    code = macro_state.main()
    assert code == macro_state.EXIT_ERROR
    written = json.loads((tmp_path / macro_state.contracts.MACRO_STATE_FILE).read_text("utf-8"))
    assert written["stale"] is True and written["risk_off"] is True
