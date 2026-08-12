"""Tests de `analysis/ingest.py` — l'ingestion JSONL -> base de debugage.

Ce qui est teste ici est exactement ce qui, s'il cassait, ferait DISPARAITRE des lignes sans
message d'erreur : l'idempotence, l'incrementalite, et la cle d'unicite. Le bug reel trouve
le 12/08 est verrouille par `test_deux_evenements_de_meme_cle_metier_sont_conserves` — une
cle metier plausible detruisait 5 073 lignes sur 5 521.
"""

import json
import pathlib
import sqlite3
import sys

import pytest

ANALYSIS_DIR = pathlib.Path(__file__).resolve().parents[1] / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

import ingest  # noqa: E402

TS = "2026-04-01T12:00:00+00:00"


def _ecrire(dossier: pathlib.Path, jour: str, records: list[dict]) -> pathlib.Path:
    chemin = dossier / f"{jour}.jsonl"
    with open(chemin, "a", encoding="utf-8") as fichier:
        for rec in records:
            fichier.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return chemin


def _evaluation(**extra) -> dict:
    base = {"event_type": "evaluation", "ts_utc": TS, "pair": "BTC/USDT:USDT",
            "signal_id": "BTCUSDT-2026.04.01.T120000Z", "schema_version": 3,
            "regime": "TREND", "decision": "no_signal", "raison": "TREND",
            "conviction": 0.42, "seuil": 0.5, "rr_dispo": 2.1,
            "regime_inputs": {"adx4h": 30.0, "macro_regime": "PORTEUR", "direction_macro": "long"},
            "scores": {"structure": 1.0, "momentum": 0.5, "sr": 0.3,
                       "patterns": 0.0, "volume": 0.7},
            "cdl_features": {"cdl_doji": 0}}
    base.update(extra)
    return base


def _ingerer(tmp_path, records, jour="2026-04-01", db=None):
    journal = tmp_path / "decisions"
    journal.mkdir(exist_ok=True)
    _ecrire(journal, jour, records)
    db = db or tmp_path / "debug.sqlite"
    with sqlite3.connect(db) as conn:
        ingest.creer_schema(conn)
        resultat = ingest.ingerer(conn, journal / f"{jour}.jsonl")
        ingest.creer_vue_pourquoi(conn)
    return db, resultat


# --------------------------------------------------------------- idempotence
def test_reingerer_le_meme_fichier_ne_duplique_rien(tmp_path):
    db, (lues, inserees) = _ingerer(tmp_path, [_evaluation()])
    assert (lues, inserees) == (1, 1)
    journal = tmp_path / "decisions" / "2026-04-01.jsonl"
    with sqlite3.connect(db) as conn:          # 2e passage : le curseur a deja tout lu
        assert ingest.ingerer(conn, journal) == (0, 0)
        assert conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 1


def test_ingestion_incrementale_ne_relit_pas_l_existant(tmp_path):
    """Sans curseur, un cron horaire relit tout le journal a chaque passage."""
    db, _ = _ingerer(tmp_path, [_evaluation()])
    journal = tmp_path / "decisions" / "2026-04-01.jsonl"
    _ecrire(tmp_path / "decisions", "2026-04-01", [_evaluation(ts_utc="2026-04-01T16:00:00+00:00")])
    with sqlite3.connect(db) as conn:
        lues, inserees = ingest.ingerer(conn, journal)
    assert (lues, inserees) == (1, 1), "seule la ligne AJOUTEE doit etre relue"


def test_fichier_tronque_declenche_une_relecture_complete(tmp_path):
    db, _ = _ingerer(tmp_path, [_evaluation(), _evaluation(ts_utc="2026-04-01T16:00:00+00:00")])
    journal = tmp_path / "decisions" / "2026-04-01.jsonl"
    journal.write_text(json.dumps(_evaluation()) + "\n", encoding="utf-8")   # remplace, plus court
    with sqlite3.connect(db) as conn:
        lues, _ = ingest.ingerer(conn, journal)
    assert lues == 1, "un fichier plus court que l'offset doit etre relu depuis le debut"


# ----------------------------------------------------------- cle d'unicite
def test_deux_evenements_de_meme_cle_metier_sont_conserves(tmp_path):
    """LE bug du 12/08. `ev_gestion` ne pose aucun ts_utc : en backtest, des milliers
    d'evenements de marche distincts recoivent la meme seconde d'execution, la meme paire et
    le meme signal_id. Une cle (ts, pair, signal_id, rule) en avait detruit 5 073 sur 5 521."""
    commun = {"event_type": "gestion", "ts_utc": TS, "pair": "BTC/USDT:USDT",
              "signal_id": "SID-1", "rule": "SL", "schema_version": 3}
    db, (_, inserees) = _ingerer(tmp_path, [
        {**commun, "before": 100.0, "after": 101.0, "profit_r": 0.5},
        {**commun, "before": 101.0, "after": 102.0, "profit_r": 0.8},
    ])
    assert inserees == 2
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM gestion").fetchone()[0] == 2


def test_ligne_strictement_identique_est_dedoublonnee(tmp_path):
    rec = _evaluation()
    _, (lues, inserees) = _ingerer(tmp_path, [rec, dict(rec)])
    assert (lues, inserees) == (2, 1)


# ------------------------------------------------------------ aplatissement
def test_sous_objets_remontent_en_colonnes(tmp_path):
    """`regime_inputs` et `scores` doivent etre requetables sans json_extract()."""
    db, _ = _ingerer(tmp_path, [_evaluation()])
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        ligne = dict(conn.execute("SELECT * FROM evaluations").fetchone())
    assert ligne["adx4h"] == 30.0 and ligne["macro_regime"] == "PORTEUR"
    assert ligne["direction_macro"] == "long" and ligne["s_structure"] == 1.0
    assert json.loads(ligne["cdl_features"]) == {"cdl_doji": 0}   # motifs gardes en JSON


def test_gates_remonte_la_porte_bloquante(tmp_path):
    db, _ = _ingerer(tmp_path, [{
        "event_type": "gate_check", "ts_utc": TS, "pair": "BTC/USDT:USDT",
        "signal_id": "SID-1", "schema_version": 3, "decision": "skip",
        "failed_gate": "news_window",
        "gates": [{"regime": "TREND", "rr": 2.8, "slots": 0, "intent_created": False}]}])
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        ligne = dict(conn.execute("SELECT * FROM gate_checks").fetchone())
    assert ligne["failed_gate"] == "news_window" and ligne["rr"] == 2.8


def test_event_type_inconnu_est_ignore_sans_crasher(tmp_path):
    """Un journal d'une version future ne doit pas casser l'ingestion des lignes connues."""
    _, (lues, inserees) = _ingerer(tmp_path, [{"event_type": "futur", "ts_utc": TS},
                                              _evaluation()])
    assert (lues, inserees) == (2, 1)


def test_ligne_json_tronquee_est_sautee(tmp_path):
    """Un arret brutal du bot laisse une derniere ligne incomplete — elle ne doit rien casser."""
    journal = tmp_path / "decisions"
    journal.mkdir()
    chemin = journal / "2026-04-01.jsonl"
    chemin.write_text(json.dumps(_evaluation()) + '\n{"event_type": "evalua',
                      encoding="utf-8")
    with sqlite3.connect(tmp_path / "d.sqlite") as conn:
        ingest.creer_schema(conn)
        lues, inserees = ingest.ingerer(conn, chemin)
    assert (lues, inserees) == (2, 1)


# --------------------------------------------------------------- vue pourquoi
def test_vue_pourquoi_montre_les_setups_REFUSES(tmp_path):
    """La raison d'etre de la vue : un setup evalue puis refuse n'a ni gate_check ni entry.
    Un INNER JOIN le ferait disparaitre — or c'est exactement le cas qu'on veut lire."""
    db, _ = _ingerer(tmp_path, [_evaluation()])
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        ligne = dict(conn.execute("SELECT * FROM pourquoi").fetchone())
    assert ligne["signal_emis"] == "no_signal"
    assert ligne["decision_portes"] is None and ligne["prix_entree"] is None
    assert ligne["ecart_seuil"] == pytest.approx(-0.08)   # conviction 0,42 - seuil 0,50
