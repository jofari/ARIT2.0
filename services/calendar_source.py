"""C1 - services/calendar_source.py : calendrier economique a DEUX sources (decision Jonas 03/08).

Remplace `FINNHUB_KEY`, dont l'endpoint calendrier est passe premium (dette C1 de
`research/pistes_2026-07-31/CHANTIERS.md` : « FINNHUB_KEY vide => la porte news est inerte
ou bloquante selon l'etat du fichier macro »).

Architecture decidee par Jonas :

  PRIMAIRE   `user_data/calendar/economic_calendar.json` — VERSIONNE dans le repo,
             lu sans aucun reseau, donc il ne peut pas « echouer ». C'est lui qui garantit
             le blocage des evenements qui comptent.
  SECONDAIRE ForexFactory, fetche **1x par semaine** en tache asynchrone (`--fetch-ff`),
             ecrit dans un cache local. **JAMAIS appele depuis le pipeline temps reel** :
             le run horaire de macro_state.py ne fait que LIRE le cache.

Regle de degradation (mot pour mot) : « si le fetch FF echoue, on continue sur la primaire
sans degrader le blocage des trois evenements qui comptent ». Donc `load_events()` ne leve
JAMAIS : un cache absent, perime ou corrompu se traduit par « on n'a que la primaire », pas
par une exception ni par un blocage global.

⚠️ Etat de la source primaire au 2026-08-04 : FOMC verifie a la source (federalreserve.gov),
CPI et NFP **non renseignes** — bls.gov refuse les recuperations automatisees (HTTP 403) et
fabriquer des dates de publication dans un bot de trading est inacceptable. La couverture
CPI/NFP repose donc aujourd'hui sur la SECONDAIRE. `coverage_gaps()` existe pour que ce trou
soit CRIE a chaque run et jamais silencieux.

Import autorise : contracts/params uniquement (meme regle que les autres services).
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_ARIT_LIB_DIR = Path(__file__).resolve().parents[1] / "user_data" / "strategies"
if str(_ARIT_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_ARIT_LIB_DIR))

from arit_lib import contracts  # noqa: E402

logger = logging.getLogger(__name__)

# Infrastructure (endpoints/HTTP) : hors params.py, ce ne sont pas des parametres de trading.
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"  # flux public FF, sans clef
HTTP_TIMEOUT_S = 15
FF_CACHE_MAX_AGE_H = 8 * 24   # 8 jours : un fetch hebdo peut glisser d'un jour sans trou
# ⚠️ ForexFactory identifie le pays par son CODE DEVISE ("USD"), pas par un code pays.
# Verifie sur le flux reel le 2026-08-04 : USD/EUR/JPY/AUD/NZD/CNY/CAD/CHF/GBP/All. Depuis
# la decision du 04/08 on ne filtre plus par devise (cf. fetch_forexfactory) ; l'info est
# conservee dans le champ `devise` de chaque evenement, pour pouvoir trancher plus tard
# avec des mesures plutot qu'a priori.

# Les trois evenements qui comptent (formulation de Jonas). Sert au controle de couverture :
# chaque cle porte les fragments de nom qui l'identifient, en minuscules.
KEY_EVENTS = {
    "FOMC": ("fomc", "rate decision", "federal funds"),
    "CPI": ("cpi", "consumer price"),
    "NFP": ("nfp", "nonfarm", "non-farm", "employment situation"),
}

# ------------------------------------------------------------ liste SUIVIE (Jonas 04/08)
# Indicateurs que Jonas veut voir bloquer « au minimum », INDEPENDAMMENT de la couleur que
# ForexFactory leur donne : beaucoup sont ORANGE (medium) sur FF — PPI, Retail Sales,
# Industrial Production, KOF, SPPI — et le filtre `impact == high` les jetait donc tous.
#
# Un evenement suivi est capture puis PROMU en `impact: "high"`, ce qui le rend bloquant
# dans `risk._macro_ok` (fenetre +/- NEWS_WINDOW_MIN). L'impact d'origine est conserve dans
# `impact_ff` : c'est ce qui permettra de mesurer plus tard, sans re-fetch, ce que la
# promotion a reellement coute en trades manques.
#
# ⚠️ Pour revenir en arriere : vider ce dict. Le code retombe alors sur « les rouges seuls ».
# Fragments en MINUSCULES, compares en sous-chaine sur le titre FF.
WATCHED_EVENTS = {
    # --- activite / cycle
    "business services index": "BSI",
    "manufacturing pmi": "PMI manufacturier",
    "services pmi": "PMI services",
    "cb leading index": "CB Leading Index",
    "industrial production": "Production industrielle",
    "kof": "KOF Economic Barometer",
    # --- croissance
    "gdp": "GDP",                      # couvre advance / prelim / final / price index
    "corporate profit": "Corporate Profits",
    # --- inflation amont
    "ppi": "PPI",                      # couvre Core PPI
    "producer price": "PPI",
    "sppi": "SPPI (Japon)",
    # --- emploi
    "adp": "ADP Employment Change",
    "employment change": "Employment Change",
    "unemployment claims": "Unemployment Claims",
    "jobless claims": "Unemployment Claims",
    "private payroll": "Private Payrolls",
    # --- demande / menages
    "retail sales": "Retail Sales",    # couvre Core Retail Sales
    "consumer spending": "Consumer Spending",
    "durable goods": "Durable Goods Orders",
    "business inventories": "Business Inventories",
    # --- immobilier
    "hpi": "House Price Index",
    "house price": "House Price Index",
    "rightmove": "Rightmove HPI (UK)",
    # --- exterieur / credit
    "current account": "Current Account",
    "private sector credit": "Private Sector Credit",
}


def _matches_watched(name: str) -> str | None:
    """Titre FF -> libelle de la liste suivie, ou None. Insensible a la casse."""
    lowered = (name or "").lower()
    for fragment, libelle in WATCHED_EVENTS.items():
        if fragment in lowered:
            return libelle
    return None


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _parse_iso(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return _as_utc(parsed)


def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _matches_key_event(name: str) -> str | None:
    """Nom d'evenement -> cle de KEY_EVENTS, ou None si ce n'est pas un des trois."""
    lowered = (name or "").lower()
    for key, fragments in KEY_EVENTS.items():
        if any(fragment in lowered for fragment in fragments):
            return key
    return None


# ------------------------------------------------------------ source PRIMAIRE
def load_static(user_data_dir) -> tuple[list, dict]:
    """(events, meta) depuis le JSON versionne. Ne leve jamais.

    Fichier absent/corrompu => ([], {"ok": False, ...}). C'est une anomalie de DEPLOIEMENT
    (le fichier est cense etre dans le repo), pas une panne reseau : elle doit se voir.
    """
    path = Path(user_data_dir) / contracts.CALENDAR_STATIC_FILE
    data = _read_json(path)
    if not isinstance(data, dict):
        logger.error("calendar: source primaire illisible (%s)", path)
        return [], {"ok": False, "path": str(path), "n": 0}
    events = [event for event in (data.get("events") or [])
              if isinstance(event, dict) and _parse_iso(event.get("time_utc"))]
    return events, {"ok": True, "path": str(path), "n": len(events),
                    "sources": data.get("sources", {})}


# ---------------------------------------------------------- source SECONDAIRE
def fetch_forexfactory() -> list:
    """Flux hebdo ForexFactory -> events normalises. APPELE 1x/SEMAINE, jamais par le bot.

    Decision Jonas 2026-08-04 : on garde **TOUS les evenements ROUGES** (impact=high) du flux,
    toutes devises confondues, **PLUS la liste suivie `WATCHED_EVENTS`** quelle que soit la
    couleur FF (beaucoup de ces indicateurs sont oranges). Avant, deux filtres
    supplementaires s'appliquaient et sont RETIRES ici :
      - filtre de NOM (`_is_relevant`) : ne gardait que FOMC/CPI/NFP + NEWS_KEYWORDS. Un
        rouge « Retail Sales » ou « ADP » etait donc ignore alors qu'il bouge le marche.
      - filtre PAYS (`_US_COUNTRIES`) : ne gardait que USD. Une decision BCE ou BoE rouge
        passait a la trappe, alors qu'elle deplace le BTC comme une statistique US.
    ⚠️ Consequence assumee : bien plus d'evenements bloquants (fenetre +/-30 min, params
    NEWS_WINDOW_MIN). C'est le compromis voulu — sur-bloquer plutot que rater un rouge.
    La devise de chaque evenement est CONSERVEE (champ `devise`) : re-filtrer plus tard se
    fera sur la donnee mesuree, pas sur un a priori.

    Leve RuntimeError en cas d'echec : c'est `main()` du mode --fetch-ff qui decide quoi en
    faire (garder l'ancien cache). Le pipeline temps reel, lui, ne passe jamais ici.
    """
    try:
        resp = requests.get(FF_URL, timeout=HTTP_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json() or []
    except Exception as exc:
        raise RuntimeError(f"ForexFactory injoignable ({type(exc).__name__})") from None
    events = []
    for item in payload if isinstance(payload, list) else []:
        name = str(item.get("title", ""))
        when = _parse_iso(item.get("date"))
        if when is None or not name:
            continue
        impact_ff = str(item.get("impact", "")).lower()
        suivi = _matches_watched(name)
        if impact_ff != "high" and suivi is None:
            continue
        # Un evenement SUIVI n'est promu bloquant que s'il est deja au moins ORANGE chez FF.
        # Les `low` sont conservés dans le calendrier (tracabilite, mesure future) mais NE
        # BLOQUENT PAS : sans ce garde-fou, une semaine ordinaire promeut ~32 evenements —
        # dont « Spanish Manufacturing PMI » et « French Final Services PMI », publies en
        # cascade et sans effet mesurable sur le BTC — ce qui bloque ~24 % du temps calendaire
        # (40 evenements x 1 h de fenetre sur 168 h). Mesure faite sur le flux du 2026-08-04.
        bloquant = impact_ff in ("high", "medium")
        events.append({"name": name, "time_utc": when.isoformat(),
                       "impact": "high" if bloquant else "low",  # lu par risk._macro_ok
                       "impact_ff": impact_ff or None,   # couleur d'origine, pour mesurer
                       "suivi": suivi,             # None si c'est un rouge « ordinaire »
                       "devise": str(item.get("country", "")).upper() or None,
                       "source": "ForexFactory"})
    return events


def write_ff_cache(events, user_data_dir, now) -> Path:
    """Ecrit le cache FF de facon ATOMIQUE (meme invariant que macro_state.write_atomic)."""
    path = Path(user_data_dir) / contracts.CALENDAR_FF_CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_utc": _as_utc(now).isoformat(), "events": list(events)}
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return path


def read_ff_cache(user_data_dir, now) -> tuple[list, dict]:
    """(events, meta) depuis le cache FF. Ne leve jamais, ne fait aucun reseau.

    Cache absent, corrompu ou plus vieux que FF_CACHE_MAX_AGE_H => ([], meta expliquant
    pourquoi). C'est exactement le cas « le fetch FF a echoue » : on continue sur la
    primaire, on ne bloque pas.
    """
    path = Path(user_data_dir) / contracts.CALENDAR_FF_CACHE_FILE
    data = _read_json(path)
    if not isinstance(data, dict):
        return [], {"ok": False, "raison": "absent_ou_corrompu"}
    fetched = _parse_iso(data.get("fetched_utc"))
    if fetched is None:
        return [], {"ok": False, "raison": "fetched_utc_invalide"}
    age_h = (_as_utc(now) - fetched).total_seconds() / 3600.0
    if age_h > FF_CACHE_MAX_AGE_H:
        return [], {"ok": False, "raison": "perime", "age_h": round(age_h, 1)}
    events = [event for event in (data.get("events") or [])
              if isinstance(event, dict) and _parse_iso(event.get("time_utc"))]
    return events, {"ok": True, "age_h": round(age_h, 1), "n": len(events)}


# --------------------------------------------------------------------- fusion
def _dedupe(events) -> list:
    """Dedoublonne sur (cle d'evenement OU nom, heure a la minute) et trie par date.

    La primaire gagne : elle est passee en premier et on garde la PREMIERE occurrence.
    Sans ca, un meme FOMC present dans les deux sources compterait deux fois dans
    next_events et evincerait un autre evenement du top 3 (06.1).
    """
    seen = set()
    out = []
    for event in events:
        when = _parse_iso(event.get("time_utc"))
        if when is None:
            continue
        name = str(event.get("name", ""))
        key = (_matches_key_event(name) or name.lower(), when.replace(second=0, microsecond=0))
        if key in seen:
            continue
        seen.add(key)
        out.append(event)
    out.sort(key=lambda event: _parse_iso(event["time_utc"]))
    return out


def coverage_gaps(events, now, horizon_days: int = 45) -> list:
    """Lesquels des trois evenements qui comptent n'apparaissent NULLE PART a l'horizon.

    C'est le garde-fou explicite du trou CPI/NFP de la source primaire : un trou de
    couverture ne doit jamais etre silencieux (meme principe que le fail-safe A4 du bloc
    actions, docs/06 §6.2.1). Le retour est journalise par l'appelant, pas ici.
    """
    now = _as_utc(now)
    limit = now + timedelta(days=horizon_days)
    covered = {_matches_key_event(str(event.get("name", ""))) for event in events
               if (_parse_iso(event.get("time_utc")) or limit + timedelta(days=1)) <= limit}
    return sorted(key for key in KEY_EVENTS if key not in covered)


def load_events(user_data_dir, now) -> tuple[list, dict]:
    """(events, meta) = PRIMAIRE ∪ SECONDAIRE, dedoublonne et trie. ZERO reseau, ne leve jamais.

    C'est LE point d'entree du pipeline temps reel (macro_state.main()). L'ordre de
    concatenation fait foi pour le dedoublonnage : primaire d'abord.
    """
    static_events, static_meta = load_static(user_data_dir)
    ff_events, ff_meta = read_ff_cache(user_data_dir, now)
    events = _dedupe([*static_events, *ff_events])
    meta = {"primaire": static_meta, "secondaire": ff_meta, "total": len(events),
            "trous_couverture": coverage_gaps(events, now)}
    return events, meta


# ----------------------------------------------------------------------- main
def main(argv=None) -> int:
    """`--fetch-ff` : tache HEBDOMADAIRE (Task Scheduler). Sans argument : diagnostic lecture.

    Codes retour alignes sur macro_state : 0 ok, 1 partiel/degrade, 2 erreur.
    """
    parser = argparse.ArgumentParser(description="Calendrier economique ARIT (C1)")
    parser.add_argument("--fetch-ff", action="store_true",
                        help="fetch ForexFactory et met a jour le cache (1x/semaine)")
    parser.add_argument("--user-data-dir",
                        default=str(Path(__file__).resolve().parents[1] / "user_data"))
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)

    if args.fetch_ff:
        try:
            events = fetch_forexfactory()
        except Exception as exc:
            # Degradation VOULUE : on garde l'ancien cache et la primaire continue de
            # bloquer les evenements qu'elle connait. Un echec FF n'est pas une panne.
            logger.warning("calendar: fetch FF echec (%s) - primaire conservee", exc)
            return 1
        write_ff_cache(events, args.user_data_dir, now)
        logger.info("calendar: cache FF mis a jour (%d evenements)", len(events))
        return 0

    events, meta = load_events(args.user_data_dir, now)
    logger.info("calendar: %d evenements (primaire=%s, secondaire=%s)",
                meta["total"], meta["primaire"]["ok"], meta["secondaire"]["ok"])
    if meta["trous_couverture"]:
        logger.error("calendar: TROU de couverture sur %s", meta["trous_couverture"])
        return 1
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
