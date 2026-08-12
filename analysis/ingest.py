"""G0 — ingest.py : journal JSONL -> base de DEBUGAGE (`arit_debug.sqlite`).

Repond a une seule question, par decision : **pourquoi ce trade est-il passe, ou non ?**
Une ligne du journal = une ligne de table, rien n'est agrege, rien n'est etiquete. C'est la
base de TRACABILITE ; l'analyse statistique et le ML vivent dans l'autre base
(`arit_analyse.sqlite`, produite par `analysis/dataset.py` — grain, sources et garanties
differents, d'ou la separation demandee par Jonas le 12/08).

Le bot n'ecrit JAMAIS ici. Il ecrit du JSONL append-only (`journal.py`, fail-safe M06) et ce
script ingere a part. Trois raisons, toutes deja vecues sur ce projet :
- une ecriture SQL dans un callback freqtrade est de l'I/O bloquante dans le chemin de
  trading (docs/11 §11.5) : un lock pendant `custom_stoploss` fait rater une sortie ;
- `journal.py` garantit que « le trading ne s'arrete JAMAIS pour un probleme de journal » ;
  une base corrompue ne doit pas pouvoir atteindre le bot ;
- le JSONL est rejouable : changer ce schema n'oblige pas a re-trader.

Deux proprietes rendent l'automatisation par cron sure :
- INCREMENTALE — `ingestion_state` retient l'offset deja lu par fichier ; sans ca on relit
  tout le journal a chaque passage horaire ;
- IDEMPOTENTE — cle UNIQUE sur l'empreinte SHA-1 du contenu + INSERT OR IGNORE (voir
  `empreinte()` pour pourquoi une cle metier ne marche PAS ici). Relancer l'ingestion cent
  fois donne le meme resultat : re-jouer un backtest APPEND dans les memes fichiers
  journaliers, donc les doublons sont la norme et non l'exception.

Usage :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe analysis/ingest.py [--reset]
"""

import argparse
import hashlib
import json
import logging
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
JOURNAL_DIR = REPO / "user_data" / "logs" / "decisions"
DB_DEBUG = REPO / "analysis" / "out" / "arit_debug.sqlite"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("ingest")

# Colonnes communes a toutes les tables d'evenements — l'ordre est celui du cycle de vie
# d'un signal (M06) : evaluation -> gate_check -> entry -> gestion -> exit.
COMMUNES = ("ts_utc", "pair", "signal_id", "schema_version", "jour_fichier")

# Colonnes propres a chaque type. `cdl_features` reste du JSON : les ~63 motifs de bougie
# sont journalises sans etre decisionnels (docs/05 §5.4), ils n'ont rien a faire en colonnes
# dans une base de debugage — leur place est dans la base d'analyse, une colonne par motif.
SCHEMA = {
    "evaluations": ("regime", "decision", "raison", "conviction", "seuil", "rr_dispo",
                    "adx4h", "ema50_4h", "ema200_4h", "close_vs_ema", "fear_greed",
                    "macro_stale", "macro_regime", "equity_veto", "equity_veto_reason",
                    "direction_macro", "s_structure", "s_momentum", "s_sr", "s_patterns",
                    "s_volume", "cdl_features"),
    "gate_checks": ("decision", "failed_gate", "regime", "news", "spread", "slots",
                    "residual_total", "weekly_risk", "weekly_entries", "rr", "veto",
                    "intent_created"),
    "entries": ("price", "qty", "risk_pct", "stake", "sl_initial", "tp1", "tp2",
                "conviction", "regime", "direction"),
    "gestion": ("rule", "avant", "apres", "profit_r"),
    "exits": ("cause", "r_final", "mae_r", "mfe_r", "duration_h", "fees", "slippage"),
    "systeme": ("kind", "detail"),
}
TABLE_PAR_EVENT = {"evaluation": "evaluations", "gate_check": "gate_checks",
                   "entry": "entries", "gestion": "gestion", "exit": "exits",
                   "system": "systeme"}


def _plat(valeur):
    """Valeur JSON -> scalaire SQLite. dict/list -> JSON compact (colonne inspectable)."""
    if isinstance(valeur, bool):
        return int(valeur)
    if isinstance(valeur, (dict, list)):
        return json.dumps(valeur, ensure_ascii=False, separators=(",", ":"))
    return valeur


def creer_schema(conn: sqlite3.Connection) -> None:
    for table, propres in SCHEMA.items():
        cols = ", ".join(f'"{c}"' for c in COMMUNES + propres)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} "
                     f"(id INTEGER PRIMARY KEY AUTOINCREMENT, empreinte TEXT UNIQUE, {cols})")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_sid ON {table} (signal_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_ts ON {table} (ts_utc)")
    conn.execute("CREATE TABLE IF NOT EXISTS ingestion_state ("
                 "fichier TEXT PRIMARY KEY, offset INTEGER NOT NULL, lignes INTEGER NOT NULL)")


def empreinte(rec: dict) -> str:
    """SHA-1 du contenu normalise — la cle d'unicite, et il n'y en a pas d'autre possible.

    Une cle metier du type (ts_utc, pair, signal_id, regle) parait naturelle mais elle
    DETRUIT des donnees : `ev_gestion` et `ev_gate_check` ne posent aucun `ts_utc`, donc en
    backtest `journal.write` leur donne l'heure REELLE d'execution. Des milliers d'evenements
    de marche distincts partagent alors la meme seconde, la meme paire et le meme signal_id —
    une cle metier les confond. Mesure sur le journal du 04/08 : 5 521 lignes lues, 448
    conservees. Le hash du contenu ne confond que ce qui est strictement identique.
    """
    return hashlib.sha1(
        json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def aplatir(rec: dict, jour: str) -> tuple[str, dict] | None:
    """Enregistrement JSONL -> (table, ligne). None si le type est inconnu (journal futur)."""
    table = TABLE_PAR_EVENT.get(rec.get("event_type"))
    if table is None:
        return None
    ligne = {"empreinte": empreinte(rec), "ts_utc": rec.get("ts_utc"),
             "pair": rec.get("pair"), "signal_id": rec.get("signal_id"),
             "schema_version": rec.get("schema_version"), "jour_fichier": jour}
    plat = dict(rec)
    # Les sous-objets du schema v3 remontent a plat : c'est ce qui rend la base requetable
    # sans json_extract() a chaque question.
    for sous in ("regime_inputs", "scores"):
        for cle, valeur in (rec.get(sous) or {}).items():
            plat[f"s_{cle}" if sous == "scores" else cle] = valeur
    # `gates` est une LISTE d'un seul dict cote M07 (AritV1 passe [metrics]) — on prend le
    # premier et on garde la liste brute nulle part : ce qui compte pour le debug, c'est
    # quelle porte a coupe (`failed_gate`) et avec quelles valeurs.
    for cle, valeur in ((rec.get("gates") or [{}])[0] or {}).items():
        plat.setdefault(cle, valeur)
    plat["avant"], plat["apres"] = rec.get("before"), rec.get("after")
    for colonne in SCHEMA[table]:
        ligne[colonne] = _plat(plat.get(colonne))
    return table, ligne


def ingerer(conn: sqlite3.Connection, chemin: pathlib.Path) -> tuple[int, int]:
    """Ingere les octets NON ENCORE LUS de `chemin`. Retourne (lignes lues, lignes inserees)."""
    ligne_state = conn.execute("SELECT offset FROM ingestion_state WHERE fichier = ?",
                               (chemin.name,)).fetchone()
    offset = ligne_state[0] if ligne_state else 0
    taille = chemin.stat().st_size
    if taille < offset:      # fichier tronque ou remplace => on repart de zero
        logger.warning("%s a retreci (%d < %d) : relecture complete", chemin.name, taille, offset)
        offset = 0
    if taille == offset:
        return 0, 0

    lues = inserees = 0
    jour = chemin.stem
    with open(chemin, "r", encoding="utf-8") as fichier:
        fichier.seek(offset)
        for brut in fichier:
            if not brut.strip():
                continue
            lues += 1
            try:
                rec = json.loads(brut)
            except json.JSONDecodeError:      # ligne tronquee par un arret brutal du bot
                continue
            resultat = aplatir(rec, jour)
            if resultat is None:
                continue
            table, valeurs = resultat
            noms = list(valeurs)
            cur = conn.execute(
                f'INSERT OR IGNORE INTO {table} ({", ".join(chr(34) + n + chr(34) for n in noms)}) '
                f'VALUES ({", ".join("?" * len(noms))})', [valeurs[n] for n in noms])
            inserees += cur.rowcount
        fin = fichier.tell()
    conn.execute("INSERT INTO ingestion_state (fichier, offset, lignes) VALUES (?, ?, ?) "
                 "ON CONFLICT(fichier) DO UPDATE SET offset = excluded.offset, "
                 "lignes = ingestion_state.lignes + excluded.lignes",
                 (chemin.name, fin, lues))
    return lues, inserees


def creer_vue_pourquoi(conn: sqlite3.Connection) -> None:
    """Vue `pourquoi` : une ligne par signal_id, la chaine complete de la decision.

    C'est LE rapport de debugage sous forme requetable — ce que la strategie a vu
    (evaluation), ce que les portes de risque en ont fait (gate_check), et si une position en
    est sortie (entry/exit). Un LEFT JOIN depuis les evaluations : un setup evalue puis refuse
    n'a ni gate_check ni entry, et c'est precisement le cas qu'on veut pouvoir lire.
    """
    conn.execute("DROP VIEW IF EXISTS pourquoi")
    conn.execute("""
        CREATE VIEW pourquoi AS
        SELECT e.ts_utc, e.pair, e.signal_id, e.regime, e.macro_regime, e.direction_macro,
               e.conviction, e.seuil,
               ROUND(e.conviction - e.seuil, 4) AS ecart_seuil,
               e.rr_dispo, e.decision AS signal_emis, e.raison,
               g.decision AS decision_portes, g.failed_gate AS porte_bloquante,
               en.price AS prix_entree, en.direction, en.sl_initial, en.risk_pct,
               x.cause AS cause_sortie, x.r_final, x.mae_r, x.mfe_r
        FROM evaluations e
        LEFT JOIN gate_checks g ON g.signal_id = e.signal_id AND g.pair = e.pair
        LEFT JOIN entries   en ON en.signal_id = e.signal_id AND en.pair = e.pair
        LEFT JOIN exits      x ON  x.signal_id = e.signal_id AND  x.pair = e.pair
    """)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=pathlib.Path, default=DB_DEBUG)
    ap.add_argument("--journal", type=pathlib.Path, default=JOURNAL_DIR)
    ap.add_argument("--reset", action="store_true",
                    help="repart de zero (supprime la base) — sinon ingestion incrementale")
    args = ap.parse_args()

    if not args.journal.is_dir():
        raise SystemExit(f"journal introuvable : {args.journal}")
    if args.reset and args.db.exists():
        args.db.unlink()
        logger.info("base supprimee (--reset)")
    args.db.parent.mkdir(parents=True, exist_ok=True)

    total_lues = total_inserees = 0
    try:
        with sqlite3.connect(args.db) as conn:
            creer_schema(conn)
            for chemin in sorted(args.journal.glob("*.jsonl")):
                lues, inserees = ingerer(conn, chemin)
                total_lues += lues
                total_inserees += inserees
                if lues:
                    logger.info("%s : %d lues, %d nouvelles", chemin.name, lues, inserees)
            creer_vue_pourquoi(conn)
            resume = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in SCHEMA}
    except sqlite3.Error as exc:
        raise SystemExit(f"ingestion impossible : {exc}") from exc

    logger.info("%d lignes lues, %d inserees (%d deja connues)",
                total_lues, total_inserees, total_lues - total_inserees)
    logger.info("base : %s", args.db)
    for table, n in resume.items():
        logger.info("  %-12s %6d", table, n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
