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
- Calendrier : `calendar_source` (C1, decision Jonas 03/08) = JSON versionne + cache
  ForexFactory. ZERO reseau pour le calendrier dans ce run horaire ; le fetch FF est une
  tache hebdomadaire SEPAREE (`calendar_source.py --fetch-ff`). Finnhub a ete RETIRE le
  2026-08-04 : son endpoint calendrier est passe premium, la clef n'a jamais ete fournie,
  et la porte news est restee inerte tout ce temps.
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
# services/ lui-meme, pour calendar_source (C1) : ce module est importable meme quand
# macro_state est charge autrement qu'en script (tests, start_arit.py).
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import calendar_source  # noqa: E402  (meme dossier services/, C1)
import pandas as pd  # noqa: E402
from arit_lib import contracts, macro_regime, params  # noqa: E402
# `macro_regime` est PUR (contracts/params seulement) et n'est pas dans la liste d'imports
# interdits ci-dessus : le reutiliser evite de dupliquer le scoring 06.2 dans le service,
# ou les deux copies divergeraient en silence. Parite A2 (2026-08-07).

logger = logging.getLogger(__name__)

# --- Constantes d'infrastructure (endpoints/HTTP) : hors params.py car elles ne sont
# pas des parametres de trading. Valeurs metier (fenetres, seuils) viennent de params.
FEAR_GREED_URL = "https://api.alternative.me/fng/"               # docs/06.2 alternative.me
HTTP_TIMEOUT_S = 10
FG_RETRY_MAX = 3                                                  # M08 : retry x3 backoff
FG_BACKOFF_BASE_S = 2  # infra, non fixe par le PDR (M08 : "backoff" sans valeur chiffree)

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


# ----------------------------------------------------------------- fetch
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


# --------------------------------------------------- scores macro 06.2 (parite A2)
def component_scores(macro_dir, now):
    """5 scores {-1,0,1} du jour depuis l'historique macro, ou None si inexploitable.

    C'est la moitie manquante de la parite backtest/live : le backtest calcule ces scores
    lui-meme (macro_regime.daily_with_equity_veto), le live ne les avait nulle part, donc
    `direction_macro` retombait sur son fail-safe long-only alors que le backtest tournait
    long+short (docs/07 par.7.3).

    Renvoie None — jamais des zeros — si l'historique est absent, illisible ou plus vieux
    que params.MACRO_STALE_HOURS. La distinction est critique : cinq zeros donnent une
    somme de 0, donc NEUTRE, donc « long ET short autorises » sur une absence de donnee ;
    None fait tomber regime_now en HOSTILE, que regimes.classify met au repos. Aucune
    exception ne sort d'ici : le service doit toujours pouvoir ecrire son fichier.
    """
    try:
        daily = macro_regime.daily_regimes(macro_regime.load_history(macro_dir))
    except Exception as exc:                     # historique corrompu = donnee absente
        logger.warning("macro_state: scores macro illisibles (%s)", exc)
        return None
    if daily is None or daily.empty:
        logger.warning("macro_state: aucun historique macro dans %s", macro_dir)
        return None

    last = daily.index.max()
    age_h = (_as_utc(now) - last.to_pydatetime()).total_seconds() / 3600.0
    if age_h > params.MACRO_STALE_HOURS:
        logger.warning("macro_state: historique macro perime (%.0f h > %d h) - "
                       "lancer scripts/download_macro.py", age_h, params.MACRO_STALE_HOURS)
        return None

    row = daily.loc[last]
    scores = {key: int(row[key]) for key in contracts.MACRO_SCORE_KEYS
              if key in daily.columns and pd.notna(row[key])}
    return scores or None


# ----------------------------------------------------------------- build
def build_state(events, fg, now, scores=None) -> dict:
    """Schema EXACT PDR 06.3. `events` = sortie de fetch_calendar ; `fg` int ou None ; `now` UTC.

    risk_off = (fg < FG_RISK_OFF_BELOW) OU un event high dans la fenetre +/- NEWS_WINDOW_MIN.
    next_events = les NEXT_EVENTS_MAX prochains high <= NEXT_EVENTS_HORIZON_H, tries.
    `scores` = sortie de component_scores (dict 06.2 ou None) : None => stale ET risk_off,
    le bot cesse d'entrer (parite A2). Le stale d'AGE, lui, reste gere par main()/_stale().
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
    # Parite A2 : sans scores macro exploitables, l'etat est declare stale. Le lecteur
    # (journal.read_macro_state) en deduit risk_off et regimes.classify met le bot au REPOS.
    # C'est volontaire : un dry-run non surveille doit cesser d'entrer quand sa fonda n'est
    # plus alimentee, au lieu de continuer sur un NEUTRE de facade (qui, depuis A2, autorise
    # long ET short). `fear_greed` reste l'indice BRUT ici — le score du meme nom vit dans
    # le sous-objet MACRO_SCORES_KEY, jamais a plat (cf. contracts).
    return {
        "updated_utc": now.isoformat(),
        "risk_off": bool(risk_off or not scores),
        "fear_greed": fg,
        "next_events": next_events,
        "stale": not scores,
        contracts.MACRO_SCORES_KEY: scores or {},
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
        contracts.MACRO_SCORES_KEY: {},   # aucun score => HOSTILE => repos (parite A2)
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

    fg = None
    fg_ok = True

    # C1 (Jonas 03/08) : calendrier = primaire versionnee + cache FF, ZERO reseau ici.
    # `load_events` ne leve jamais, donc `cal_ok` ne depend plus d'un appel distant : il
    # ne vaut False que si la source PRIMAIRE elle-meme est illisible (anomalie de deploiement).
    events, cal_meta = calendar_source.load_events(_user_data_dir(), now)
    cal_ok = bool(cal_meta["primaire"]["ok"])
    if not cal_meta["secondaire"]["ok"]:   # degradation VOULUE : la primaire suffit (C1)
        logger.warning("macro_state: cache ForexFactory indisponible (%s) - primaire conservee",
                       cal_meta["secondaire"].get("raison"))
    if cal_meta["trous_couverture"]:       # jamais silencieux (cf. calendar_source)
        logger.error("macro_state: TROU de couverture calendrier sur %s",
                     cal_meta["trous_couverture"])
    try:
        fg = fetch_fear_greed()
    except Exception as exc:
        fg_ok = False
        logger.warning("macro_state: fear_greed echec (%s)", exc)

    if not cal_ok:   # primaire illisible : on retombe sur le dernier etat connu
        events = (old or {}).get("next_events", []) if old else []
    if not fg_ok:
        fg = (old or {}).get("fear_greed") if old else None

    # Parite A2 : scores 06.2 du jour. Hors reseau (fichiers deposes par download_macro.py,
    # tache QUOTIDIENNE separee) — ce run horaire ne fait que les relire.
    scores = component_scores(_user_data_dir() / contracts.MACRO_DATA_DIR, now)

    if cal_ok or fg_ok:
        state = build_state(events or [], fg, now, scores)
        exit_code = EXIT_OK if (cal_ok and fg_ok and scores) else EXIT_PARTIAL
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
