"""M08 - services/macro_state.py : pre-calcul fonda hors hot-path (docs/06.3, docs/11).

Process INDEPENDANT lance par le Task Scheduler Windows toutes les heures (run-once).
Ecrit user_data/macro_state.json (schema EXACT PDR 06.3) : la strategie freqtrade LIT
ce fichier, elle n'appelle JAMAIS le reseau (docs/11.5). Ce script ne DECIDE rien - il
decrit ; la logique de veto vit dans regimes/risk (docs/06.3 invariant 1).

Regles (M08 / 06) :
- risk_off = (F&G < 25) OU event high-impact dans +/- 30 min.
- next_events = 3 prochains high-impact <= 48 h, tries.
- Echec d'UNE source : garder la derniere valeur connue (relire l'ancien fichier) ;
  stale seulement si updated_utc global > 2 h (le lecteur traite stale => RISK_OFF).
- Clef Finnhub via env FINNHUB_KEY ; jamais en dur, jamais loggee.
- Timestamps 100 % UTC ISO8601, aucune conversion locale.

Import autorise : contracts/params (docs : les services peuvent les importer). AUCUN import
d'arit_lib.{features,regimes,cio,risk,gestion,journal} ni de freqtrade (process separe).
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# arit_lib vit sous user_data/strategies/ (docs/02) - contracts/params importables.
_ARIT_LIB_DIR = Path(__file__).resolve().parents[1] / "user_data" / "strategies"
if str(_ARIT_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_ARIT_LIB_DIR))

from arit_lib import contracts, params  # noqa: E402

logger = logging.getLogger(__name__)

# --- Constantes d'infrastructure (endpoints/HTTP) : hors params.py car elles ne sont
# pas des parametres de trading. Valeurs metier (fenetres, seuils) viennent de params.
FINNHUB_ENV = "FINNHUB_KEY"                                       # docs/06.1 / M08 invariant 2
FINNHUB_CALENDAR_URL = "https://finnhub.io/api/v1/calendar/economic"  # docs/06.1
FEAR_GREED_URL = "https://api.alternative.me/fng/"               # docs/06.2 alternative.me
HTTP_TIMEOUT_S = 10
FG_RETRY_MAX = 3                                                  # M08 : retry x3 backoff
FG_BACKOFF_BASE_S = 2  # infra, non fixe par le PDR (M08 : "backoff" sans valeur chiffree)
_US_COUNTRIES = ("US", "USA", "UNITED STATES")                    # docs/06.1 : events US

# Codes retour pour le Task Scheduler (M08 : main -> codes retour).
EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_ERROR = 2

# Repertoire user_data/ (override en test via set_user_data_dir).
_DEFAULT_USER_DATA_DIR = Path(__file__).resolve().parents[1] / "user_data"
_USER_DATA_DIR = None


def set_user_data_dir(path) -> None:
    """Fixe le repertoire user_data/ (tests: tmp_path)."""
    global _USER_DATA_DIR
    _USER_DATA_DIR = Path(path)


def _user_data_dir() -> Path:
    return _USER_DATA_DIR or _DEFAULT_USER_DATA_DIR


def _state_path() -> Path:
    return _user_data_dir() / contracts.MACRO_STATE_FILE


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _parse_iso(value):
    """ISO8601 (Z / offset / naif) -> datetime aware UTC, sinon None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_finnhub_time(value):
    """Finnhub 'YYYY-MM-DD HH:MM:SS' (UTC) ou ISO -> datetime aware UTC, sinon None."""
    if not value:
        return None
    text = str(value)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return _parse_iso(text)


# ----------------------------------------------------------------- fetch
def _scrub_finnhub_error(exc) -> str:
    """Message d'erreur Finnhub SANS la clef (M08 §2 / 06.5) : l'URL Finnhub contient
    ?token=<KEY> et fuiterait dans le log de main(). On ne garde que type + status HTTP."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    label = f"HTTP {status}" if status is not None else type(exc).__name__
    return f"calendar Finnhub injoignable ({label})"


def fetch_calendar(finnhub_key) -> list:
    """/calendar/economic -> events US impact=high filtres par mots-cles (NEWS_KEYWORDS).

    Retourne des dicts normalises {"name", "time_utc" (ISO UTC), "impact": "high"}.
    Leve un RuntimeError SCRUBBE en cas d'echec reseau/HTTP (main() gere le fallback).
    SECURITE (M08 §2 / 06.5) : la clef n'apparait JAMAIS dans l'exception - l'URL Finnhub
    porte ?token=<KEY>, donc aucune exception requests brute n'est propagee/loggee.
    """
    if not finnhub_key:
        raise RuntimeError("FINNHUB_KEY absente")
    try:
        resp = requests.get(
            FINNHUB_CALENDAR_URL, params={"token": finnhub_key}, timeout=HTTP_TIMEOUT_S
        )
        resp.raise_for_status()
        payload = resp.json() or {}
    except Exception as exc:
        raise RuntimeError(_scrub_finnhub_error(exc)) from None
    raw = payload.get("economicCalendar") or payload.get("calendar") or []
    events = []
    for item in raw:
        if str(item.get("impact", "")).lower() != "high":
            continue
        country = str(item.get("country", "")).upper()
        if country and country not in _US_COUNTRIES:
            continue
        name = str(item.get("event", ""))
        if not any(kw.lower() in name.lower() for kw in params.NEWS_KEYWORDS):
            continue
        when = _parse_finnhub_time(item.get("time"))
        if when is None:
            continue
        events.append({"name": name, "time_utc": when.isoformat(), "impact": "high"})
    return events


def fetch_fear_greed() -> int:
    """alternative.me Fear&Greed (valeur du jour) -> int. Retry x3 backoff, puis leve."""
    last_exc = None
    for attempt in range(FG_RETRY_MAX):
        try:
            resp = requests.get(FEAR_GREED_URL, timeout=HTTP_TIMEOUT_S)
            resp.raise_for_status()
            return int(resp.json()["data"][0]["value"])
        except Exception as exc:  # reseau, JSON, clef : on retente
            last_exc = exc
            if attempt < FG_RETRY_MAX - 1:
                time.sleep(FG_BACKOFF_BASE_S * (attempt + 1))
    raise RuntimeError(f"fear_greed injoignable: {last_exc}")


# ----------------------------------------------------------------- build
def build_state(events, fg, now) -> dict:
    """Schema EXACT PDR 06.3. `events` = sortie de fetch_calendar ; `fg` int ou None ; `now` UTC.

    risk_off = (fg < FG_RISK_OFF_BELOW) OU un event high dans la fenetre +/- NEWS_WINDOW_MIN.
    next_events = les NEXT_EVENTS_MAX prochains high <= NEXT_EVENTS_HORIZON_H, tries. stale=False
    (etat frais ; le stale global est gere par main() en cas d'echec total, cf. _stale()).
    """
    now = _as_utc(now)
    horizon = now + timedelta(hours=params.NEXT_EVENTS_HORIZON_H)
    window_s = params.NEWS_WINDOW_MIN * 60

    dated = []
    in_window = False
    for event in events or []:
        when = _parse_iso(event.get("time_utc"))
        if when is None:
            continue
        if abs((when - now).total_seconds()) < window_s:
            in_window = True
        if now <= when <= horizon:
            dated.append((when, event))
    dated.sort(key=lambda pair: pair[0])
    next_events = [event for _, event in dated[: params.NEXT_EVENTS_MAX]]

    risk_off = bool(in_window or (fg is not None and fg < params.FG_RISK_OFF_BELOW))
    return {
        "updated_utc": now.isoformat(),
        "risk_off": risk_off,
        "fear_greed": fg,
        "next_events": next_events,
        "stale": False,
    }


def _stale(updated_iso, now) -> bool:
    """True si updated_utc global date de > CALENDAR_STALE_HOURS (fail-safe M08 / 06.1)."""
    updated = _parse_iso(updated_iso)
    if updated is None:
        return True
    return (_as_utc(now) - updated) > timedelta(hours=params.CALENDAR_STALE_HOURS)


def _fail_safe_state(now) -> dict:
    """Aucune donnee du tout : stale + risk_off (la securite prime, 06.1/06.3)."""
    return {
        "updated_utc": _as_utc(now).isoformat(),
        "risk_off": True,
        "fear_greed": None,
        "next_events": [],
        "stale": True,
    }


# ----------------------------------------------------------------- write
def write_atomic(state, path) -> None:
    """Ecrit `state` en JSON de facon ATOMIQUE (tmp + os.replace) : jamais de JSON a moitie
    ecrit (M08 invariant). En cas d'echec, l'ancien fichier reste intact et le tmp est nettoye."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _read_old(path) -> dict:
    """Ancien macro_state.json (fallback source en echec), ou None si absent/corrompu."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# ----------------------------------------------------------------- main
def main() -> int:
    """Orchestration horaire + codes retour Task Scheduler (0 ok, 1 partiel, 2 erreur)."""
    now = _now_utc()
    path = _state_path()
    old = _read_old(path)

    key = os.environ.get(FINNHUB_ENV)
    events = None
    fg = None
    cal_ok = True
    fg_ok = True

    try:
        events = fetch_calendar(key)
    except Exception as exc:
        cal_ok = False
        logger.warning("macro_state: calendar echec (%s)", exc)
    try:
        fg = fetch_fear_greed()
    except Exception as exc:
        fg_ok = False
        logger.warning("macro_state: fear_greed echec (%s)", exc)

    if not cal_ok:
        events = (old or {}).get("next_events", []) if old else []
    if not fg_ok:
        fg = (old or {}).get("fear_greed") if old else None

    if cal_ok or fg_ok:
        state = build_state(events or [], fg, now)
        exit_code = EXIT_OK if (cal_ok and fg_ok) else EXIT_PARTIAL
    elif old is None:
        state = _fail_safe_state(now)
        exit_code = EXIT_ERROR
    else:
        state = dict(old)
        state["stale"] = _stale(old.get("updated_utc"), now)
        if state["stale"]:
            state["risk_off"] = True
        exit_code = EXIT_PARTIAL

    try:
        write_atomic(state, path)
    except Exception as exc:
        logger.error("macro_state: ecriture echec (%s)", exc)
        return EXIT_ERROR
    return exit_code


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
