"""Tests C1 — services/calendar_source.py (decision Jonas 2026-08-03).

Contrat teste : la source PRIMAIRE (JSON versionne) est lue sans reseau et ne peut pas
"echouer" ; la SECONDAIRE (cache ForexFactory) est facultative ; un echec FF degrade sans
bloquer ; un trou sur un des trois evenements qui comptent est SIGNALE.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services"))

import calendar_source  # noqa: E402
from arit_lib import contracts  # noqa: E402

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
REPO = Path(__file__).resolve().parents[1]


def _ev(name, when, source="test"):
    return {"name": name, "time_utc": when.isoformat(), "impact": "high", "source": source}


def _write_static(root, events, sources=None):
    path = Path(root) / contracts.CALENDAR_STATIC_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 1, "events": events, "sources": sources or {}}),
                    encoding="utf-8")
    return path


# ------------------------------------------------- le fichier LIVRE dans le repo
def test_le_calendrier_versionne_est_valide_et_couvre_le_fomc():
    """Le JSON reellement livre doit se charger et porter des FOMC futurs."""
    events, meta = calendar_source.load_static(REPO / "user_data")
    assert meta["ok"] is True
    assert events, "la source primaire livree est vide"
    fomc = [e for e in events if calendar_source._matches_key_event(e["name"]) == "FOMC"]
    assert len(fomc) >= 8                       # au moins une annee de reunions
    # Toutes les heures sont parsables, en UTC, et strictement croissantes une fois triees.
    times = sorted(calendar_source._parse_iso(e["time_utc"]) for e in events)
    assert all(t is not None and t.tzinfo is not None for t in times)
    assert len(set(times)) == len(times)        # aucun doublon d'horodatage
    # DST US appliquee : un FOMC de decembre (EST) est a 19:00 UTC, un de juin (EDT) a 18:00.
    hours = {t.month: t.hour for t in times}
    assert hours.get(12) == 19 and hours.get(6) == 18


def test_le_fichier_livre_declare_honnetement_ses_trous():
    """CPI/NFP ne sont pas renseignes : le fichier doit le DIRE, pas le cacher."""
    _events, meta = calendar_source.load_static(REPO / "user_data")
    sources = meta["sources"]
    assert sources["FOMC"]["verified_utc"]                     # verifie a la source
    assert sources["BLS_CPI"]["verified_utc"] is None          # trou assume, pas invente
    assert sources["BLS_NFP"]["verified_utc"] is None


# ----------------------------------------------------------------- primaire
def test_primaire_illisible_est_signalee_et_ne_leve_pas(tmp_path):
    events, meta = calendar_source.load_static(tmp_path)
    assert events == [] and meta["ok"] is False
    (tmp_path / "calendar").mkdir()
    (tmp_path / contracts.CALENDAR_STATIC_FILE).write_text("{pas du json", encoding="utf-8")
    events, meta = calendar_source.load_static(tmp_path)
    assert events == [] and meta["ok"] is False


def test_primaire_ignore_les_evenements_sans_date_valide(tmp_path):
    _write_static(tmp_path, [_ev("FOMC rate decision", NOW),
                             {"name": "X", "time_utc": "n'importe"}])
    events, meta = calendar_source.load_static(tmp_path)
    assert len(events) == 1 and meta["n"] == 1


# ---------------------------------------------------------------- secondaire
def test_cache_ff_absent_perime_ou_corrompu_ne_bloque_jamais(tmp_path):
    events, meta = calendar_source.read_ff_cache(tmp_path, NOW)
    assert events == [] and meta["ok"] is False and meta["raison"] == "absent_ou_corrompu"
    # Perime : au-dela de FF_CACHE_MAX_AGE_H, on ignore, on ne bloque pas.
    old = NOW - timedelta(hours=calendar_source.FF_CACHE_MAX_AGE_H + 1)
    calendar_source.write_ff_cache([_ev("CPI m/m", NOW)], tmp_path, old)
    events, meta = calendar_source.read_ff_cache(tmp_path, NOW)
    assert events == [] and meta["raison"] == "perime"


def test_cache_ff_frais_est_lu(tmp_path):
    calendar_source.write_ff_cache([_ev("CPI m/m", NOW + timedelta(hours=3))],
                                   tmp_path, NOW - timedelta(hours=2))
    events, meta = calendar_source.read_ff_cache(tmp_path, NOW)
    assert len(events) == 1 and meta["ok"] is True and meta["age_h"] == 2.0


def test_ecriture_du_cache_est_atomique(tmp_path):
    path = calendar_source.write_ff_cache([_ev("CPI m/m", NOW)], tmp_path, NOW)
    assert path.exists()
    assert not path.with_name(path.name + ".tmp").exists()   # aucun tmp residuel


# -------------------------------------------------------------------- fusion
def test_load_events_fusionne_et_dedoublonne_la_primaire_gagnant(tmp_path):
    """Le meme FOMC vu par les deux sources ne doit compter qu'UNE fois : sinon il evince
    un autre evenement du top 3 de next_events (06.1)."""
    when = NOW + timedelta(hours=5)
    _write_static(tmp_path, [_ev("FOMC rate decision", when, source="FOMC")])
    calendar_source.write_ff_cache(
        [_ev("FOMC Statement", when, source="ForexFactory"),   # doublon (meme cle, meme minute)
         _ev("CPI m/m", NOW + timedelta(hours=9), source="ForexFactory")],
        tmp_path, NOW)
    events, meta = calendar_source.load_events(tmp_path, NOW)
    assert meta["total"] == 2
    assert [e["source"] for e in events] == ["FOMC", "ForexFactory"]   # primaire gardee
    # Tri chronologique garanti.
    assert calendar_source._parse_iso(events[0]["time_utc"]) < \
        calendar_source._parse_iso(events[1]["time_utc"])


def test_load_events_ne_leve_jamais_meme_sans_aucun_fichier(tmp_path):
    events, meta = calendar_source.load_events(tmp_path, NOW)
    assert events == []
    assert meta["primaire"]["ok"] is False and meta["secondaire"]["ok"] is False
    assert set(meta["trous_couverture"]) == {"FOMC", "CPI", "NFP"}


# ------------------------------------------------------- couverture des 3 events
def test_coverage_gaps_detecte_les_trois_evenements_qui_comptent(tmp_path):
    events = [_ev("FOMC rate decision", NOW + timedelta(days=10)),
              _ev("CPI m/m", NOW + timedelta(days=5))]
    assert calendar_source.coverage_gaps(events, NOW) == ["NFP"]
    events.append(_ev("Nonfarm Payrolls", NOW + timedelta(days=7)))
    assert calendar_source.coverage_gaps(events, NOW) == []
    # Un evenement AU-DELA de l'horizon ne compte pas comme couvert.
    loin = [_ev("FOMC rate decision", NOW + timedelta(days=200))]
    assert "FOMC" in calendar_source.coverage_gaps(loin, NOW)


@pytest.mark.parametrize("name,attendu", [
    ("FOMC rate decision", "FOMC"), ("Federal Funds Rate", "FOMC"),
    ("CPI m/m", "CPI"), ("Consumer Price Index", "CPI"),
    ("Non-Farm Employment Change", "NFP"), ("Employment Situation", "NFP"),
    ("Retail Sales", None),
])
def test_reconnaissance_des_noms_devenements(name, attendu):
    assert calendar_source._matches_key_event(name) == attendu


# ------------------------------------------------------------------- fetch FF
def test_fetch_ff_filtre_impact_pays_et_pertinence(monkeypatch):
    payload = [
        # ForexFactory identifie par CODE DEVISE : "USD" doit etre GARDE (verifie sur le
        # flux reel le 04/08 — filtrer sur "US" ne laissait passer aucun evenement).
        {"title": "Non-Farm Employment Change", "country": "USD", "impact": "High",
         "date": "2026-08-07T08:30:00-04:00"},                       # gardé, offset ET
        {"title": "CPI m/m", "country": "EUR", "impact": "High",
         "date": "2026-08-12T12:30:00+00:00"},                       # pas les US
        {"title": "CPI m/m", "country": "USD", "impact": "Low",
         "date": "2026-08-12T12:30:00+00:00"},                       # impact bas
        {"title": "Retail Sales", "country": "USD", "impact": "High",
         "date": "2026-08-14T12:30:00+00:00"},                       # hors périmètre
        {"title": "FOMC Statement", "country": "USD", "impact": "High",
         "date": "pas une date"},                                    # date illisible
    ]
    monkeypatch.setattr(calendar_source.requests, "get",
                        lambda url, timeout=None: type("R", (), {
                            "raise_for_status": lambda self: None,
                            "json": lambda self: payload})())
    events = calendar_source.fetch_forexfactory()
    assert [e["name"] for e in events] == ["Non-Farm Employment Change"]
    assert events[0]["source"] == "ForexFactory"
    # L'offset US Eastern est bien converti en UTC (08:30 ET = 12:30 UTC en ete).
    assert calendar_source._parse_iso(events[0]["time_utc"]).hour == 12


def test_fetch_ff_en_echec_leve_mais_le_mode_fetch_degrade(monkeypatch, tmp_path):
    """Un echec FF ne doit jamais casser le calendrier : code 1, cache precedent conserve."""
    calendar_source.write_ff_cache([_ev("CPI m/m", NOW)], tmp_path, NOW)
    def _boom(url, timeout=None):
        raise ConnectionError("reseau mort")
    monkeypatch.setattr(calendar_source.requests, "get", _boom)
    with pytest.raises(RuntimeError):
        calendar_source.fetch_forexfactory()
    code = calendar_source.main(["--fetch-ff", "--user-data-dir", str(tmp_path)])
    assert code == 1
    events, meta = calendar_source.read_ff_cache(tmp_path, NOW)   # cache INTACT
    assert meta["ok"] is True and len(events) == 1


def test_fetch_ff_ne_fuite_aucun_secret_dans_le_message(monkeypatch):
    """Le flux FF est public (aucune clef), et le message d'erreur reste generique."""
    assert "token" not in calendar_source.FF_URL and "key" not in calendar_source.FF_URL
    monkeypatch.setattr(calendar_source.requests, "get",
                        lambda url, timeout=None: (_ for _ in ()).throw(
                            ConnectionError("https://secret.example/?token=ABC")))
    with pytest.raises(RuntimeError) as excinfo:
        calendar_source.fetch_forexfactory()
    assert "ABC" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None
