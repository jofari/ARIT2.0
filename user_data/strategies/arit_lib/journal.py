"""M06 - journal.py : la boite noire ARIT (journal de decision JSONL + macro_state).

Role (docs/08, docs/M06) : rendre l'edge AUDITABLE et preparer le dataset V2 (FreqAI).
Append-only, une ligne = un evenement JSON compact horodate. AUCUN reseau
(Discord est un service separe qui tail le JSONL - docs/README interdit n1/reseau).

Politique fail-safe (M06) : le trading ne s'arrete JAMAIS pour un probleme de journal.
- write() ne leve jamais : erreur d'ecriture => 1 retry puis logging.error, pas d'exception.
- Champ obligatoire manquant => la ligne est ecrite quand meme avec "schema_incomplete": true
  et l'anomalie est loggee (un dataset avec un trou signale vaut mieux qu'une ligne perdue).

Base dir : configurable via set_user_data_dir(path). Les chemins (contracts.DECISIONS_DIR,
contracts.MACRO_STATE_FILE) sont resolus RELATIVEMENT a ce repertoire (defaut : le dossier
user_data/ deduit de l'emplacement du module). Les tests injectent tmp_path.

event_type : write() ecrit ce discriminateur dans chaque ligne (cle "event_type") pour
permettre la reconstruction d'un cycle par signal_id (evaluation..exit). C'est la seule cle
hors JOURNAL_REQUIRED_FIELDS, mais elle est structurellement indispensable au dataset.
"""

import functools
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import contracts, params

logger = logging.getLogger(__name__)

# v4 (audit 24/08) — identifiant du PROCESSUS qui ecrit. Le nom de fichier ne depend que du
# jour SIMULE et l'ouverture se fait en "a" : sans cette cle, deux backtests sur la meme
# periode s'additionnent sans etre separables (52 % de doublons mesures le 24/08). Genere une
# fois a l'import, donc constant pour tout un run freqtrade et distinct d'un run a l'autre.
_RUN_ID = uuid.uuid4().hex[:12]


def run_id() -> str:
    """Identifiant du run courant (constant pour tout le processus)."""
    return _RUN_ID


def set_run_id(value: str) -> None:
    """Force le run_id — tests uniquement, jamais en production."""
    global _RUN_ID, _PROTOCOLE_ECRIT
    _RUN_ID = str(value)
    _PROTOCOLE_ECRIT = False        # le protocole se reecrit sous le nouveau run_id


# D3 (audit 24/08) — trois variables d'env changent le comportement de trading sans
# laisser de trace : un run n'etait pas rejouable depuis son propre journal.
_PROTOCOLE_ECRIT = False


def _emit_protocole() -> None:
    """Ecrit UNE fois par run la ligne 'system' qui decrit l'environnement du run.

    Emis a la PREMIERE ecriture, pas a l'import : le repertoire user_data peut etre
    redefini apres l'import (set_user_data_dir), et la politique fail-safe interdit
    d'ecrire dans un chemin non resolu.
    """
    global _PROTOCOLE_ECRIT
    if _PROTOCOLE_ECRIT:
        return
    _PROTOCOLE_ECRIT = True     # pose AVANT le write : sinon write -> emit -> write -> ...
    write("system", ev_system(contracts.SYSTEM_KIND_PROTOCOLE, dict(params.PROTOCOLE_ACTIF)))


def safe(default, event):
    """Decorateur de callback M07 (regle 3) : toute exception -> ligne 'system' + action sure.

    Vit ici plutot que dans la strategie parce que son unique effet EST de journaliser :
    c'est la seule chose qui doit survivre a une exception dans un callback freqtrade.
    Une feature qui casse ne doit jamais tuer le bot ni passer un ordre par defaut —
    d'ou `default` (False pour une porte, 0.0 pour un sizing, None pour une gestion).
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                write("system", ev_system(event, {"error": str(exc)}))
                return default
        return wrap
    return deco

_WRITE_ATTEMPTS = 2  # M06 : 1 ecriture + 1 retry puis logging.error (jamais d'exception)
_SECONDS_PER_HOUR = 3600.0  # conversion duree s -> h (exit.duration_h)
_MACRO_SCHEMA_KEYS = ("updated_utc", "risk_off", "fear_greed", "next_events", "stale")  # PDR 06.3

# Repertoire user_data/ par defaut (module sous user_data/strategies/arit_lib/journal.py).
_USER_DATA_DIR = Path(__file__).resolve().parents[2]


def set_user_data_dir(path) -> None:
    """Fixe le repertoire user_data/ contre lequel les chemins sont resolus (tests: tmp_path)."""
    global _USER_DATA_DIR
    _USER_DATA_DIR = Path(path)


def _decisions_dir() -> Path:
    return _USER_DATA_DIR / contracts.DECISIONS_DIR


def _macro_state_path() -> Path:
    return _USER_DATA_DIR / contracts.MACRO_STATE_FILE


# --------------------------------------------------------------------- helpers
def _coerce(value):
    """numpy scalar -> python natif ; autres inchanges (fidelite round-trip JSON)."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            return value
    return value


def _json_default(value):
    """Dernier recours json.dumps : jamais d'exception (numpy -> natif, sinon str)."""
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    return str(value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value):
    """ISO8601 (avec 'Z', offset ou naif) -> datetime aware UTC, sinon None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value):
    """datetime/Timestamp -> ISO8601 ; str inchange ; None -> None."""
    if value is None or isinstance(value, str):
        return value
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            return str(value)
    return str(value)


def _utc_day(ts_utc) -> str:
    """Jour UTC (YYYY-MM-DD) du timestamp -> nom du fichier journalier (rotation naturelle)."""
    moment = _parse_iso(ts_utc) or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%d")


def _get(obj, key, default=None):
    """Lecture duck-type : dict / pandas Series (.get) sinon objet (getattr)."""
    if obj is None:
        return default
    getter = getattr(obj, "get", None)
    if callable(getter):
        try:
            value = getter(key, default)
        except TypeError:
            value = getattr(obj, key, default)
    else:
        value = getattr(obj, key, default)
    return default if value is None else value


def _items(obj):
    """(cle, valeur) d'un row : dict, pandas Series (.index) ou objet (__dict__)."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    index = getattr(obj, "index", None)
    if index is not None:
        try:
            return {key: obj[key] for key in index}
        except Exception:
            return {}
    return dict(getattr(obj, "__dict__", {}) or {})


def _extract_cdl(row) -> dict:
    """Colonnes cdl_* du row (prefixe contracts.CDL_PREFIX) - journalisees ICI seulement."""
    return {
        str(key): _coerce(value)
        for key, value in _items(row).items()
        if str(key).startswith(contracts.CDL_PREFIX)
    }


def _duration_h(trade):
    explicit = _get(trade, "duration_h")
    if explicit is not None:
        return _coerce(explicit)
    open_dt = _parse_iso(_iso(_get(trade, "open_date")))
    close_dt = _parse_iso(_iso(_get(trade, "close_date")))
    if open_dt and close_dt:
        return (close_dt - open_dt).total_seconds() / _SECONDS_PER_HOUR
    return None


# ------------------------------------------------------------------- ecriture
def write(event_type: str, payload: dict) -> None:
    """Append 1 ligne JSON compacte dans logs/decisions/<jour UTC de ts_utc>.jsonl, flush direct.

    Ajoute event_type, schema_version et ts_utc (si absent). Valide event_type et la presence
    des champs contracts.JOURNAL_REQUIRED_FIELDS ; champ manquant => "schema_incomplete": true
    + logging.error, mais la ligne est ecrite quand meme. Ne leve JAMAIS (M06).
    """
    _emit_protocole()                       # D3 — une fois par run, avant tout le reste
    record = _prepare_record(event_type, payload)
    path = _decisions_dir() / f"{_utc_day(record.get('ts_utc'))}.jsonl"
    _append_line(path, record, event_type)


def _prepare_record(event_type: str, payload) -> dict:
    record = dict(payload) if isinstance(payload, dict) else {}
    record["event_type"] = event_type
    record.setdefault(contracts.RUN_ID_KEY, _RUN_ID)   # v4 — separe les runs superposes
    record.setdefault("schema_version", contracts.SCHEMA_VERSION)
    record.setdefault("ts_utc", _now_iso())
    required = contracts.JOURNAL_REQUIRED_FIELDS.get(event_type)
    if required is None:
        logger.error("journal.write: event_type inconnu %r", event_type)
        record["schema_incomplete"] = True
        return record
    missing = [key for key in required if key not in record]
    if missing:
        logger.error("journal.write: %s champs manquants %s", event_type, missing)
        record["schema_incomplete"] = True
    return record


def _append_line(path: Path, record: dict, event_type: str) -> None:
    """Serialisation + I/O gardees ENSEMBLE : ni json.dumps (ref circulaire, cle non
    convertible) ni l'ecriture ne remontent au trading — retry x1 puis logging.error."""
    last_exc = None
    for _ in range(_WRITE_ATTEMPTS):
        try:
            line = json.dumps(
                record, separators=(",", ":"), ensure_ascii=False, default=_json_default
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
            return
        except Exception as exc:  # M06 : le journal ne casse jamais le trading
            last_exc = exc
    logger.error("journal.write echec ecriture (%s): %s", event_type, last_exc)


# ------------------------------------------------ selection des lignes (M06 -> M07)
def lignes_evaluation(df, live: bool) -> list:
    """Lignes du DataFrame pour lesquelles M07 doit ecrire une 'evaluation'.

    LIVE : la derniere ligne seulement, et seulement si elle ouvre une bougie 4h — une
    evaluation par boucle, comportement d'origine (docs/08, decision Jonas 2026-07-08).

    BACKTEST : TOUTES les cloture 4h du df. Avant le 2026-08-12, `AritV1` n'appelait la
    journalisation qu'en live ; l'evenement `evaluation` — le SEUL qui porte le vecteur de
    features complet — n'existait donc dans AUCUN journal du projet, et B9 comme toute piste
    ML etaient sans donnees. La garde `new_4h` (docs/11 §11.2) reste la seule regle : jamais
    deux evaluations du meme setup 4h.

    Retourne une liste (pas un generateur) : l'appelant est un callback freqtrade, on ne
    laisse pas une lecture de DataFrame trainer au-dela de l'appel.
    """
    if df is None or len(df) == 0 or "new_4h" not in df.columns:
        return []
    marques = df["new_4h"].fillna(False).astype(bool).tolist()
    if live:
        return [df.iloc[-1]] if marques[-1] else []
    return [df.iloc[i] for i, marque in enumerate(marques) if marque]


# ----------------------------------------------------- builders typees (M06)
def ev_evaluation(row, explain_dict) -> dict:
    """Evenement 'evaluation' (chaque cloture 4h, par paire). Seul evenement portant les cdl_*.

    row (duck-type dict/Series) : regime, adx_4h, ema50_4h, ema200_4h, s_structure, s_momentum,
      s_sr, s_patterns, s_volume, conviction, seuil, rr_dispo, colonnes cdl_* (CDL_PREFIX).
    explain_dict : pair, ts_utc, signal_id, decision ('signal'|'no_signal'), raison, close_vs_ema,
      fear_greed, macro_stale (contexte absent du row).
    signal_id est inclus (hors champs requis) pour la reconstruction du cycle par signal_id (M06).
    """
    ts_utc = _iso(_get(explain_dict, "ts_utc") or _get(row, "date"))
    record = {
        "pair": _get(explain_dict, "pair") or _get(row, "pair"),
        "signal_id": _get(explain_dict, "signal_id"),
        "regime": _get(row, "regime"),
        "regime_inputs": {
            "adx4h": _coerce(_get(row, "adx_4h")),
            "ema50_4h": _coerce(_get(row, "ema50_4h")),
            "ema200_4h": _coerce(_get(row, "ema200_4h")),
            "close_vs_ema": _coerce(_get(explain_dict, "close_vs_ema")),
            "fear_greed": _coerce(_get(explain_dict, "fear_greed")),
            "macro_stale": bool(_get(explain_dict, "macro_stale", False)),
            # schema v2 (03/08, A4/A5) : l'etat macro et le veto actions sur CHAQUE evaluation.
            # C'est ce qui rend la porte macro ablatable a posteriori (PORTEUR-seul vs
            # non-HOSTILE derives par filtrage d'un seul run) — docs/08 §8.1.
            contracts.MACRO_REGIME_COL: _get(row, contracts.MACRO_REGIME_COL),
            contracts.EQUITY_VETO_COL: bool(_get(row, contracts.EQUITY_VETO_COL, False)),
            contracts.EQUITY_VETO_REASON_COL: _get(row, contracts.EQUITY_VETO_REASON_COL),
            # schema v3 (04/08, A2) : sens AUTORISE par la macro sur cette bougie.
            # Declare depuis le 04/08 dans cio.explain et contracts (§8.1) mais JAMAIS
            # ecrit ici — donc absent de tous les journaux, et le Test 1 de docs/01
            # (« la macro donne-t-elle la direction ? ») n'etait pas mesurable, alors que
            # c'est la raison d'etre de A2. Corrige le 2026-08-07.
            "direction_macro": _get(row, "direction_macro"),
        },
        "scores": {
            "structure": _coerce(_get(row, "s_structure")),
            "momentum": _coerce(_get(row, "s_momentum")),
            "sr": _coerce(_get(row, "s_sr")),
            "patterns": _coerce(_get(row, "s_patterns")),
            "volume": _coerce(_get(row, "s_volume")),
        },
        "cdl_features": _extract_cdl(row),
        "conviction": _coerce(_get(row, "conviction")),
        "seuil": _coerce(_get(row, "seuil")),
        "rr_dispo": _coerce(_get(row, "rr_dispo")),
        "decision": _get(explain_dict, "decision"),
        "raison": _get(explain_dict, "raison"),
    }
    if ts_utc:
        record["ts_utc"] = ts_utc
    return record


def ev_gate_check(signal_id, gates, decision, failed, pair) -> dict:
    """Evenement 'gate_check' (si signal) : etat de chaque garde-fou 03.2 + decision finale.

    Extension de signature vs M06 (review build, aller-retour 1) : `pair` explicite, format
    slashe 'BTC/USDT' identique aux autres evenements (dataset V2, groupby par pair).
    gates : list[dict] (ex. {'name': contracts.GATE_NAMES[i], 'pass': bool, 'value': ...}).
    decision : 'enter'|'skip'. failed : nom du gate fautif ou None. ts_utc pose par write().
    """
    return {
        "pair": pair,
        "signal_id": signal_id,
        "gates": list(gates) if gates is not None else [],
        "decision": decision,
        "failed_gate": failed,
    }


def ev_entry(trade, state) -> dict:
    """Evenement 'entry'. trade (duck-type) : pair, open_rate, amount, stake_amount, open_date,
    tp1, tp2 (calcules par la logique d'entree M05). state = contracts.TradeState (initial_sl,
    risk_pct, entry_conviction, entry_regime, signal_id)."""
    ts_utc = _iso(_get(trade, "open_date"))
    record = {
        "pair": _get(trade, "pair"),
        "signal_id": _get(state, "signal_id") or _get(trade, "signal_id"),
        "price": _coerce(_get(trade, "open_rate")),
        "qty": _coerce(_get(trade, "amount")),
        "risk_pct": _coerce(_get(state, "risk_pct")),
        "stake": _coerce(_get(trade, "stake_amount")),
        "sl_initial": _coerce(_get(state, "initial_sl")),
        "tp1": _coerce(_get(trade, "tp1")),
        "tp2": _coerce(_get(trade, "tp2")),
        "conviction": _coerce(_get(state, "entry_conviction")),
        "regime": _get(state, "entry_regime"),
        # schema v3 (A2, 04/08) : sans le sens, un journal post-short est incomparable a
        # tout ce qui precede et le Test 1 de docs/01 n'est pas mesurable.
        "direction": (contracts.DIR_SHORT if _get(state, "is_short")
                      else contracts.DIR_LONG),
    }
    if ts_utc:
        record["ts_utc"] = ts_utc
    return record


def ev_gestion(trade, action, before, after, r) -> dict:
    """Evenement 'gestion' (declenchement G1-G7). action = regle (rule) ; before/after = ancien/
    nouveau SL ou action ; r = profit courant en R. signal_id lu sur le trade ; ts_utc via write."""
    return {
        "pair": _get(trade, "pair"),
        "signal_id": _get(trade, "signal_id"),
        "rule": action,
        "before": _coerce(before),
        "after": _coerce(after),
        "profit_r": _coerce(r),
    }


def ev_exit(trade, cause, r_final, mae, mfe, fees, slippage) -> dict:
    """Evenement 'exit'. cause (G4/G5-trail/G6/G7/SL/TP), r_final, mae/mfe (en R), fees, slippage.
    duration_h calcule depuis trade.open_date/close_date. signal_id lu sur le trade."""
    record = {
        "pair": _get(trade, "pair"),
        "signal_id": _get(trade, "signal_id"),
        "cause": cause,
        "r_final": _coerce(r_final),
        "mae_r": _coerce(mae),
        "mfe_r": _coerce(mfe),
        "duration_h": _duration_h(trade),
        "fees": _coerce(fees),
        "slippage": _coerce(slippage),
    }
    ts_utc = _iso(_get(trade, "close_date"))
    if ts_utc:
        record["ts_utc"] = ts_utc
    return record


def ev_system(kind, detail) -> dict:
    """Evenement 'system' (demarrage, CB, stale calendrier, erreur). ts_utc pose par write()."""
    return {"kind": kind, "detail": detail}


# --------------------------------------------------- macro_state (partage 06.3)
def read_macro_state(now=None) -> dict:
    """Lit macro_state.json (schema PDR 06.3), applique la regle stale/risk_off (fail-safe).

    Force stale=True ET risk_off=True si updated_utc est plus vieux que
    params.CALENDAR_STALE_HOURS heures, ou si le fichier est absent/corrompu/hors-schema
    (la strategie traite stale comme risk_off - PDR 06.3). Ne leve jamais. `now` injectable.
    Cle partagee : regimes/risk lisent ce dict via la strategie.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        data = json.loads(_macro_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _fail_safe_macro()
    if not isinstance(data, dict) or not all(key in data for key in _MACRO_SCHEMA_KEYS):
        return _fail_safe_macro()

    state = {
        "updated_utc": data.get("updated_utc"),
        "risk_off": bool(data.get("risk_off", True)),
        "fear_greed": data.get("fear_greed"),
        "next_events": data.get("next_events") or [],
        "stale": bool(data.get("stale", False)),
    }
    # Parite A2 : les 5 scores macro (06.2) transitent vers macro_regime.regime_now.
    # IMBRIQUES sous contracts.MACRO_SCORES_KEY, JAMAIS a plat : `fear_greed` existe dans
    # les DEUX schemas avec deux sens incompatibles — indice BRUT 0-100 ici (06.3, lu par
    # regimes.REGLES), score {-1,0,1} dans MACRO_SCORE_KEYS (06.2). A plat, regime_now
    # sommerait un F&G de 20 comme +20 et renverrait PORTEUR en permanence.
    # VOLONTAIREMENT hors de _MACRO_SCHEMA_KEYS : un macro_state.json d'avant la parite
    # reste lisible, sans scores — regime_now bascule alors en HOSTILE (>= 3 manquants),
    # que classify met au repos via le fail-safe de donnee.
    scores = data.get(contracts.MACRO_SCORES_KEY)
    state[contracts.MACRO_SCORES_KEY] = scores if isinstance(scores, dict) else {}
    updated = _parse_iso(state["updated_utc"])
    stale = (
        state["stale"]
        or updated is None
        or now - updated > timedelta(hours=params.CALENDAR_STALE_HOURS)
    )
    if stale:
        state["stale"] = True
        state["risk_off"] = True
    return state


def _fail_safe_macro() -> dict:
    """Defaut sur fichier absent/corrompu => stale + risk_off (la securite prime, PDR 06.1/06.3)."""
    return {
        "updated_utc": None,
        "risk_off": True,
        "fear_greed": None,
        "next_events": [],
        "stale": True,
        contracts.MACRO_SCORES_KEY: {},   # aucun score => regime_now HOSTILE (parite A2)
    }
