"""Contrats de donnees ARIT V1 — noms EXACTS, ne jamais renommer (docs/11 §11.3).

Un module qui invente un nom de colonne/cle/fichier hors de ce fichier = echec build.
"""

from dataclasses import dataclass, fields
from datetime import datetime, timezone

# ------------------------------------------------ Colonnes DataFrame (11.3)
# Produites par features.py — consommees par regimes/cio/entree/gestion.
FEATURE_COLUMNS = (
    "ema50_4h", "ema200_4h", "ema50_1d",
    "adx_4h", "rsi_4h", "macd_hist_4h", "atr_4h", "atr_1h", "vol_sma20_4h",
    "pivot_high_conf_4h", "pivot_low_conf_4h",
    "last_ph_4h", "last_hl_4h", "last_hl_1h",
    "bos_bull_4h", "bos_fresh_4h", "choch_bear_4h", "choch_bear_1h",
    "nearest_res_4h", "nearest_sup_4h", "res_touches_4h",
    "rr_dispo",
    "s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume",
    "new_4h",
)
CDL_PREFIX = "cdl_"  # 11.3 / PDR 05.4 idee 9 — ~60 colonnes talib CDL*, journalisees only

# Produites par regimes.py (11.3) — noms francais contractuels, ne pas angliciser.
REGIME_COLUMNS = ("regime", "seuil", "multiplicateur")

# Produites par cio.py (11.3).
CIO_COLUMNS = ("conviction", "signal_long")

# ------------------------------------------- custom_data par trade (11.3)
CUSTOM_DATA_KEYS = (
    "initial_sl", "risk_pct", "trade_no", "tp1_done", "extension_on",
    "mae_r", "mfe_r", "last_candle_ts", "entry_conviction", "entry_regime",
    "signal_id",
)


@dataclass
class TradeState:
    """Miroir type du custom_data d'un trade (11.3, M05).

    `initial_sl` est IMMUABLE apres l'entree (c'est l'unite R — PDR M05.4).
    """

    initial_sl: float = 0.0
    risk_pct: float = 0.0
    trade_no: int = 0
    tp1_done: bool = False
    extension_on: bool = False
    mae_r: float = 0.0
    mfe_r: float = 0.0
    last_candle_ts: int = 0
    entry_conviction: float = 0.0
    entry_regime: str = ""
    signal_id: str = ""

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict) -> "TradeState":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


# ------------------------------------------ Fichiers d'etat (11.3, M04)
# Chemins RELATIFS a user_data/ — resolus par l'appelant (live et backtest).
MACRO_STATE_FILE = "macro_state.json"                    # 11.3 / PDR 06.3
DAY_EQUITY_FILE = "state/day_equity.json"                # 11.3 — {"date","equity"}
HEARTBEAT_FILE = "state/heartbeat"                       # 11.3 — mtime = heartbeat
VETO_DIR = "veto"                                        # 11.3 — <signal_id>.flag
DECISIONS_DIR = "logs/decisions"                         # 11.3 — YYYY-MM-DD.jsonl
MANUAL_RESTART_FLAG = "state/manual_restart_required"    # M04 — 2 CB jour / semaine ISO
# Extensions actees (BUILD_NOTES 2026-07-06, a valider par Jonas au rapport) :
CB_DAY_FILE = "state/cb_day.json"          # M04 — {"iso_week","count"} declenchements CB jour
VETO_INTENT_SUFFIX = ".intent"             # 11.6 — <signal_id>.intent, mtime = heure d'intention

# --------------------------------------------------- Journal JSONL (PDR 08.1)
SCHEMA_VERSION = 1  # M06 — toute nouvelle cle => PDR 08.1 d'abord, version += 1

EVENT_TYPES = ("evaluation", "gate_check", "entry", "gestion", "exit", "system")

# Champs obligatoires par type (PDR 08.1). Cles canoniques du build (le PDR les
# decrit en francais ; les cles JSON sont fixees ICI, une fois pour toutes).
# Enveloppe commune ajoutee par journal.write : event_type + schema_version.
# signal_id est present sur TOUT le cycle (M06) — y compris evaluation (derivable
# pair+ts_4h meme sans signal).
JOURNAL_REQUIRED_FIELDS = {
    "evaluation": (
        "ts_utc", "pair", "signal_id", "regime", "regime_inputs", "scores", "cdl_features",
        "conviction", "seuil", "rr_dispo", "decision", "raison",
    ),
    "gate_check": ("ts_utc", "pair", "signal_id", "gates", "decision", "failed_gate"),
    "entry": (
        "ts_utc", "pair", "signal_id", "price", "qty", "risk_pct", "stake",
        "sl_initial", "tp1", "tp2", "conviction", "regime",
    ),
    "gestion": ("ts_utc", "pair", "signal_id", "rule", "before", "after", "profit_r"),
    "exit": (
        "ts_utc", "pair", "signal_id", "cause", "r_final", "mae_r", "mfe_r",
        "duration_h", "fees", "slippage",
    ),
    "system": ("ts_utc", "kind", "detail"),
}

# regime_inputs de `evaluation` (PDR 08.1 / 04.5) :
REGIME_INPUT_KEYS = ("adx4h", "ema50_4h", "ema200_4h", "close_vs_ema", "fear_greed", "macro_stale")
# scores de `evaluation` (PDR 08.1) :
SCORE_KEYS = ("structure", "momentum", "sr", "patterns", "volume")

# Noms exacts des gates 03.2 (ordre d'evaluation contractuel — M04 gate_check).
GATE_NAMES = (
    "regime",          # 03.2.1 — regime dans ENTRY_REGIMES
    "news_window",     # 03.2.2 — pas d'event high +/-30 min, calendar stale => fail
    "spread",          # 03.2.3 — spread <= 0,05 %
    "slots",           # 03.2.4 — positions ouvertes < 3
    "residual_risk",   # 03.2.5 — somme residuels + nouveau <= 6 %
    "weekly_budget",   # 03.2.6 — <= 8 % / semaine ISO ET < 10 entrees
    "rr_min",          # 03.2.7 — RR >= 1,5
    "veto_canari",     # 03.2.8 — fenetre veto Discord (canari uniquement)
)
SKIP_MIN_NOTIONAL = "skip_min_notional"            # PDR 03.1 — skip journalise hors gates
SKIP_ZERO_STOP_DISTANCE = "skip_zero_stop_distance"  # M04.4 — entry == sl_initial, jamais d'exception


# ----------------------------------------------------------- signal_id (M06)
def make_signal_id(pair: str, ts_4h: datetime) -> str:
    """Cle de correlation evaluation -> gate_check -> entry -> gestion -> exit.

    Format PDR M06 : "{pair}-{ts_4h}". Normalise pour servir de nom de fichier
    veto flag sous Windows ("/" et ":" interdits) : BTCUSDT-20260706T120000Z.
    """
    if ts_4h.tzinfo is None:
        ts_4h = ts_4h.replace(tzinfo=timezone.utc)
    stamp = ts_4h.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{pair.replace('/', '')}-{stamp}"
