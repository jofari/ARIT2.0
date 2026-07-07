"""M04 — risk.py : sizing, budgets, garde-fous d'entree (docs/03, docs/11).

Module PUR : zero import freqtrade, zero reseau, zero appel LLM (interdits README).
`Trade` (liste de trades = la "DB") et `wallets` sont INJECTES (duck-typing) par la
strategie AritV1 (M07). `gate_check` NE JOURNALISE PAS (journal.py est un autre
module) : il RETOURNE (ok, gate_fautif|None, metrics) et M07 ecrit la ligne 08.1.

Protocole duck-type attendu
---------------------------
Objet *trade* (elements de la liste `Trade`), attributs lus :
    is_open (bool), open_rate (float), stop_loss (float), amount (float),
    close_rate (float, si clos), open_date_utc (datetime), close_date_utc (datetime|None).
    custom_data (cles 11.3 : risk_pct, initial_sl, ...) lu via, dans l'ordre :
    methode `get_custom_data(key)`, sinon dict attribut `custom_data`, sinon
    attribut direct du meme nom.
Objet *wallets* : equite courante (compounding) via `get_total_stake_amount()`
    sinon `get_total(STAKE_CURRENCY)`.

Extensions de contrat (BUILD_NOTES, canoniques dans contracts.py) implementees ici :
    user_data/veto/<signal_id> + contracts.VETO_INTENT_SUFFIX  (mtime = intention, 11.6)
    contracts.CB_DAY_FILE  ({"iso_week","count"}, historique CB jour 03.5)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from arit_lib import contracts, params


# ----------------------------------------------------------------- helpers purs
def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_week(dt: datetime) -> tuple[int, int]:
    iso = _as_utc(dt).isocalendar()
    return (iso[0], iso[1])


def _iso_week_str(dt: datetime) -> str:
    year, week = _iso_week(dt)
    return f"{year}-W{week:02d}"


def _day_str(dt: datetime) -> str:
    return _as_utc(dt).strftime("%Y-%m-%d")


def _custom(trade, key, default=None):
    getter = getattr(trade, "get_custom_data", None)
    if callable(getter):
        val = getter(key)
        return default if val is None else val
    data = getattr(trade, "custom_data", None)
    if isinstance(data, dict):
        return data.get(key, default)
    val = getattr(trade, key, default)
    return default if val is None else val


def _equity(wallets) -> float:
    getter = getattr(wallets, "get_total_stake_amount", None)
    if callable(getter):
        return float(getter())
    getter = getattr(wallets, "get_total", None)
    if callable(getter):
        return float(getter(params.STAKE_CURRENCY))
    raise AttributeError("wallets: get_total_stake_amount()/get_total() requis")


def _read_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _parse_iso(value):
    if not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except (TypeError, ValueError):
        return None


def _trade_r(trade) -> float:
    """R realise d'un trade clos = (close - entry) / (entry - initial_sl) (long)."""
    entry = float(getattr(trade, "open_rate", 0.0) or 0.0)
    sl0 = float(_custom(trade, "initial_sl", 0.0) or 0.0)
    risk_dist = entry - sl0
    if risk_dist <= 0:
        return 0.0
    close = getattr(trade, "close_rate", None)
    close = float(close) if close is not None else entry
    return (close - entry) / risk_dist


# ------------------------------------------------------------- sizing (03.1)
def compute_risk_pct(conviction, seuil, trade_no, cb_divisor=1) -> float:
    """Risque % = (1% + n*(cap-1%)) / cb_divisor, n=(c-seuil)/(1-seuil) borne [0,1]."""
    denom = 1.0 - seuil
    n = 1.0 if denom <= 0 else (conviction - seuil) / denom
    n = min(1.0, max(0.0, n))
    cap = (params.RISK_CAP_FIRST_PCT if trade_no <= params.RISK_CAP_SWITCH_TRADE_NO
           else params.RISK_CAP_AFTER_PCT)
    divisor = cb_divisor if cb_divisor and cb_divisor > 0 else 1
    return (params.RISK_BASE_PCT + n * (cap - params.RISK_BASE_PCT)) / divisor


def compute_stake(equity, risk_pct, entry, sl_initial, min_notional=0.0, risk_cap_pct=None):
    """Stake USDT = equity*risk_pct / dist_frac, dist_frac=(entry-sl)/entry.

    Retour : (stake|None, raison|None). Div/0 (entry<=sl) =>
    (None, contracts.SKIP_ZERO_STOP_DISTANCE), jamais d'exception (M04.4). Si stake <
    min_notional et forcer depasse le cap => (None, contracts.SKIP_MIN_NOTIONAL) ;
    sinon force a min_notional (03.1).
    """
    if entry <= 0:
        return None, contracts.SKIP_ZERO_STOP_DISTANCE
    dist_frac = (entry - sl_initial) / entry
    if dist_frac <= 0:
        return None, contracts.SKIP_ZERO_STOP_DISTANCE
    if equity <= 0:
        return None, contracts.SKIP_MIN_NOTIONAL
    stake = equity * risk_pct / dist_frac
    if min_notional and stake < min_notional:
        cap = risk_cap_pct if risk_cap_pct is not None else risk_pct
        forced_risk = min_notional * dist_frac / equity
        if forced_risk > cap:
            return None, contracts.SKIP_MIN_NOTIONAL
        return min_notional, None
    return stake, None


# --------------------------------------------------- budgets / compteurs (DB)
def residual_risk_total(open_trades, equity) -> float:
    """Somme des residuels des positions ouvertes / equite (0 si SL >= entree)."""
    if equity <= 0:
        return 0.0
    total = 0.0
    for t in open_trades:
        entry = float(getattr(t, "open_rate", 0.0) or 0.0)
        sl = float(getattr(t, "stop_loss", 0.0) or 0.0)
        qty = float(getattr(t, "amount", 0.0) or 0.0)
        total += qty * max(0.0, entry - sl)
    return total / equity


def weekly_state(Trade, now_utc):
    """(risque_initial_engage, n_entrees) pour la semaine ISO UTC de now (open+clos)."""
    week = _iso_week(now_utc)
    risk_engaged = 0.0
    n_entries = 0
    for t in Trade:
        odt = getattr(t, "open_date_utc", None)
        if odt is None or _iso_week(odt) != week:
            continue
        n_entries += 1
        risk_engaged += float(_custom(t, "risk_pct", 0.0) or 0.0)
    return risk_engaged, n_entries


def trade_counter(Trade) -> int:
    """Nombre total de trades (ouverts + clotures) — bascule cap 2%->3% (03.1)."""
    return sum(1 for _ in Trade)


def cb_sequential_state(Trade, now=None):
    """(cooldown_active, risk_divisor) — ENTIEREMENT derive de la DB (03.5, M04).

    trigger_ts = close_date_utc de la 2e perte de la sequence consecutive la plus
    recente (CB_SEQ_CONSECUTIVE clotures <= CB_SEQ_LOSS_R, dans l'ordre des clotures).
    cooldown_active = now < trigger_ts + CB_SEQ_COOLDOWN_CANDLES_1H heures.
    risk_divisor = CB_SEQ_RISK_DIVISOR tant que moins de CB_SEQ_PENALTY_TRADES trades
    ont ete ouverts apres trigger_ts, sinon 1. Aucun etat custom_data requis.
    """
    now = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    closed = [t for t in Trade
              if not getattr(t, "is_open", False)
              and getattr(t, "close_date_utc", None) is not None]
    closed.sort(key=lambda t: _as_utc(t.close_date_utc))

    trigger_ts = None
    streak = 0
    for t in closed:
        streak = streak + 1 if _trade_r(t) <= params.CB_SEQ_LOSS_R else 0
        if streak >= params.CB_SEQ_CONSECUTIVE:
            trigger_ts = _as_utc(t.close_date_utc)
    if trigger_ts is None:
        return False, 1

    cooldown_end = trigger_ts + timedelta(hours=params.CB_SEQ_COOLDOWN_CANDLES_1H)
    cooldown_active = now < cooldown_end

    opened_after = sum(
        1 for t in Trade
        if getattr(t, "open_date_utc", None) is not None
        and _as_utc(t.open_date_utc) > trigger_ts
    )
    divisor = params.CB_SEQ_RISK_DIVISOR if opened_after < params.CB_SEQ_PENALTY_TRADES else 1
    return cooldown_active, divisor


# ------------------------------------------------------- CB jour (03.5, etat)
def snapshot_day_equity_if_new_day(wallets, now, user_data_dir) -> None:
    """Ecrit state/day_equity.json {"date","equity"} au 1er passage d'un jour UTC."""
    path = Path(user_data_dir) / contracts.DAY_EQUITY_FILE
    today = _day_str(now)
    data = _read_json(path)
    if data is not None and data.get("date") == today:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"date": today, "equity": _equity(wallets)}, fh)


def cb_day_active(wallets, now, user_data_dir) -> bool:
    """True si equite < ref_jour*(1-6%) OU flag restart manuel present (03.5).

    2 declenchements distincts (jours differents) dans la meme semaine ISO =>
    cree contracts.MANUAL_RESTART_FLAG (seule une suppression manuelle re-arme).
    """
    base = Path(user_data_dir)
    flag = base / contracts.MANUAL_RESTART_FLAG
    if flag.exists():
        return True
    ref = _read_json(base / contracts.DAY_EQUITY_FILE)
    if not ref or "equity" not in ref:
        return False
    # PDR 03.5 "<= -6 %" : a exactement -6 % le CB declenche => seul equity > seuil passe.
    threshold = float(ref["equity"]) * (1.0 - params.CB_DAY_EQUITY_DROP_PCT)
    if _equity(wallets) > threshold:
        return False
    _register_cb_day(now, base, flag)
    return True


def _register_cb_day(now, base: Path, flag: Path) -> None:
    """Increment cb_day.json (1 fois/jour via mtime), cree le flag au cap semaine."""
    path = base / contracts.CB_DAY_FILE
    week = _iso_week_str(now)
    now_ts = _as_utc(now).timestamp()
    data = _read_json(path) or {}
    same_week = data.get("iso_week") == week
    count = int(data.get("count", 0)) if same_week else 0
    already_today = False
    if path.exists() and same_week:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        already_today = _day_str(mtime) == _day_str(now)
    if not already_today:
        count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"iso_week": week, "count": count}, fh)
    os.utime(path, (now_ts, now_ts))
    if count >= params.CB_DAY_MAX_PER_ISO_WEEK:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()


# ------------------------------------------- news/macro & veto (gate helpers)
def _macro_ok(user_data_dir: Path, now: datetime):
    """(ok, status). Absent/corrompu/stale => fail-safe FAIL ; event high +/-30min => FAIL.

    Staleness verifiee cote lecteur EN PLUS du flag (06.1) : updated_utc absent/invalide
    ou plus vieux que CALENDAR_STALE_HOURS => stale.
    """
    data = _read_json(user_data_dir / contracts.MACRO_STATE_FILE)
    if data is None:
        return False, "missing"
    if data.get("stale", True):
        return False, "stale"
    updated = _parse_iso(data.get("updated_utc"))
    if updated is None or now - updated > timedelta(hours=params.CALENDAR_STALE_HOURS):
        return False, "stale"
    for event in data.get("next_events") or []:
        if not isinstance(event, dict) or event.get("impact") != "high":
            continue
        etime = _parse_iso(event.get("time_utc"))
        if etime is None:
            return False, "event"
        if abs((now - etime).total_seconds()) <= params.NEWS_WINDOW_MIN * 60:
            return False, "event"
    return True, "ok"


def _veto_ok(cfg, now: datetime):
    """(ok, status, intent_created) — veto canari non-bloquant (11.6)."""
    window = int(cfg.get("veto_window_min", 0) or 0)
    if window <= 0:
        return True, "dryrun", False
    base = Path(cfg["user_data_dir"]) / contracts.VETO_DIR
    signal_id = cfg["signal_id"]
    now_ts = now.timestamp()
    if (base / f"{signal_id}{contracts.VETO_FLAG_SUFFIX}").exists():
        return False, "human_veto", False
    intent = base / f"{signal_id}{contracts.VETO_INTENT_SUFFIX}"
    if not intent.exists():
        base.mkdir(parents=True, exist_ok=True)
        intent.touch()
        os.utime(intent, (now_ts, now_ts))
        return False, "intent", True
    if now_ts >= intent.stat().st_mtime + window * 60:
        return True, "expired", False
    return False, "window", False


# --------------------------------------------- porte d'entree unique (03.2)
def gate_check(pair, now, wallets, Trade, cfg):
    """Gates 03.2 dans l'ordre GATE_NAMES, arret au 1er echec pour la DECISION.

    Toutes les metriques PURES sont mesurees AVANT l'evaluation (un skip est
    journalisable aussi richement qu'une entree — 08.1). Seul le veto (effet de
    bord .intent) reste conditionnel : "not_evaluated" si les gates 1-7 echouent.
    cfg (dict) : regime, spread_frac (float|None), rr, risk_pct (nouveau trade),
    signal_id, veto_window_min, user_data_dir (Path). Retour (ok, gate|None, metrics).
    """
    now = _as_utc(now)

    # ------------------------- mesures (lectures pures, aucune ecriture) ----
    regime = cfg.get("regime")
    news_ok, news_status = _macro_ok(Path(cfg["user_data_dir"]), now)
    spread = cfg.get("spread_frac")
    open_trades = [t for t in Trade if getattr(t, "is_open", False)]
    equity = _equity(wallets)
    new_risk = float(cfg.get("risk_pct", 0.0) or 0.0)
    residual_total = residual_risk_total(open_trades, equity)
    risk_engaged, n_entries = weekly_state(Trade, now)
    rr = float(cfg.get("rr", 0.0) or 0.0)

    metrics = {
        "regime": regime,
        "news": news_status,
        "spread": spread,
        "slots": len(open_trades),
        "residual_total": residual_total,
        "weekly_risk": risk_engaged + new_risk,
        "weekly_entries": n_entries,
        "rr": rr,
        "veto": "not_evaluated",
        "intent_created": False,
    }

    # ------------------------- decision (ordre 03.2 strict, 1er echec) ------
    if regime not in params.ENTRY_REGIMES:
        return False, contracts.GATE_NAMES[0], metrics
    if not news_ok:
        return False, contracts.GATE_NAMES[1], metrics
    if spread is not None and spread > params.SPREAD_MAX_FRAC:
        return False, contracts.GATE_NAMES[2], metrics
    if len(open_trades) >= params.MAX_OPEN_TRADES:
        return False, contracts.GATE_NAMES[3], metrics
    if residual_total + new_risk > params.RESIDUAL_RISK_MAX_PCT:
        return False, contracts.GATE_NAMES[4], metrics
    if risk_engaged + new_risk > params.WEEKLY_RISK_BUDGET_PCT:
        return False, contracts.GATE_NAMES[5], metrics
    if n_entries >= params.WEEKLY_MAX_ENTRIES:
        return False, contracts.GATE_NAMES[5], metrics
    if rr < params.RR_MIN:
        return False, contracts.GATE_NAMES[6], metrics

    # Veto en dernier : effet de bord (creation .intent) seulement si tout passe.
    veto_ok, veto_status, intent_created = _veto_ok(cfg, now)
    metrics["veto"] = veto_status
    metrics["intent_created"] = intent_created
    if not veto_ok:
        return False, contracts.GATE_NAMES[7], metrics

    return True, None, metrics
