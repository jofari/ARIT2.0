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
    "choch_bear_event_1h",  # 11.3 / 03.4 G6 — EVENEMENT de cassure (decision Jonas 10/07)
    # A2 (decision Jonas 2026-08-03) — MIROIRS BAISSIERS : le bot est long ET short.
    # Meme construction que leurs jumeaux haussiers, meme anti-repaint (pivots confirmes).
    "last_pl_4h", "last_lh_4h", "last_lh_1h",
    "bos_bear_4h", "bos_fresh_bear_4h", "choch_bull_4h", "choch_bull_1h",
    "choch_bull_event_1h",   # 03.4 G6 cote short : la structure se retourne A LA HAUSSE
    "ll_lh_intact_4h",       # miroir de hh_hl_intact (s_structure_short 0,7)
    # C3 (decision Jonas 2026-08-03) : Bollinger(20,2) 1h CALCULEES ET JOURNALISEES, jamais
    # decisionnelles en V1 (docs/05 par.5.3). Accumule la donnee pour un test futur sur barres.
    "bb_upper_1h", "bb_mid_1h", "bb_lower_1h",
    "nearest_res_4h", "nearest_sup_4h", "res_touches_4h",
    "rr_dispo", "rr_dispo_short",   # A2 — RR vers le support pour le short (05.2 miroir)
    "s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume",
    # A2 — jeu de scores BAISSIER. Meme bareme discret (SCORE_VALUES), meme poids
    # (POIDS est indexe sans suffixe) : seule la polarite des predicats change.
    "s_structure_short", "s_momentum_short", "s_sr_short",
    "s_patterns_short", "s_volume_short",
    "new_4h",
)
SHORT_SUFFIX = "_short"   # A2 — suffixe contractuel des colonnes miroir baissieres
CDL_PREFIX = "cdl_"  # 11.3 / PDR 05.4 idee 9 — ~60 colonnes talib CDL*, journalisees only

# Macro Analyst V1.1 (docs/06 §6.2, valide Jonas 2026-07-12) :
MACRO_REGIME_COL = "macro_regime"          # colonne df + cle journal/evaluation
MACRO_SCORE_KEYS = ("dxy", "taux", "stablecoins", "funding", "fear_greed")  # 06.2
MACRO_DATA_DIR = "data/macro"              # series historiques (scripts/download_macro.py)

# Bloc correlation actions c6/c7 (docs/06 §6.2.1, decision Jonas 2026-08-03 A4).
# HORS de MACRO_SCORE_KEYS : ce n'est PAS un 6e composant de la somme, c'est un veto
# booleen journalise a part et ablatable seul.
EQUITY_VETO_COL = "equity_veto"                    # colonne df (bool) + cle journal
EQUITY_VETO_REASON_COL = "equity_veto_reason"      # colonne df (str) + cle journal
EQUITY_FILE = "nasdaq100.csv"    # 06.2 c6 — FRED NASDAQ100 (A3 : PAS SP500, fenetre 10 ans)
BTC_DAILY_FILE = "btc_daily.json"  # 06.2 c7 — cloture 1d BTC, pour rho(BTC, actions)

# Raisons du veto actions (06.2 §6.2.1). Chaines STABLES et sans interpolation :
# elles sont COMPTEES telles quelles dans l'ablation (interdit n6).
EQUITY_VETO_BINDING = "equity_risk_off"                # bloque, et bloque SEUL
EQUITY_VETO_REDUNDANT = "equity_risk_off_redundant"    # bloque, macro deja HOSTILE
EQUITY_VETO_STALE = "equity_veto_stale"                # serie DEMARREE puis perimee => fail-safe
EQUITY_PASS_DECOUPLED = "equity_decoupled"             # rho bas -> veto desarme
EQUITY_PASS_NO_BREAK = "equity_no_break"               # arme, mais pas de cassure
EQUITY_PASS_NOT_STARTED = "equity_not_started"         # serie JAMAIS demarree => bloc inoperant

# Produites par regimes.py (11.3) — noms francais contractuels, ne pas angliciser.
# A2 : `trend_dir` (+1 haussier / -1 baissier / 0 indecis) separe l'ETAT du marche
# (regime) de son SENS. Sans cette separation, un marche en tendance BAISSIERE tombait
# dans le fallback RANGE et le short etait structurellement impossible.
REGIME_COLUMNS = ("regime", "seuil", "multiplicateur", "trend_dir", "multiplicateur_short")
TREND_DIR_COL = "trend_dir"

# Produites par cio.py (11.3).
# A2 : `conviction_short` et `signal_short` sont les jumeaux baissiers. `direction_macro`
# trace CE QUE LA MACRO AUTORISE sur chaque bougie (hypothese v4 : la macro donne la
# DIRECTION, la technique donne le timing — docs/01).
CIO_COLUMNS = ("conviction", "signal_long", "conviction_short", "signal_short",
               "direction_macro")

# A2 — directions autorisees par la macro (docs/01 v4, docs/06 §6.2).
# PORTEUR => long seul · HOSTILE => short seul · NEUTRE => les deux, seuil releve (A5).
DIR_LONG = "long"
DIR_SHORT = "short"
DIR_BOTH = "both"
DIR_NONE = "none"
DIRECTIONS = (DIR_LONG, DIR_SHORT, DIR_BOTH, DIR_NONE)

# ------------------------------------------- custom_data par trade (11.3)
CUSTOM_DATA_KEYS = (
    "initial_sl", "risk_pct", "trade_no", "tp1_done", "extension_on",
    "mae_r", "mfe_r", "last_candle_ts", "entry_conviction", "entry_regime",
    "signal_id",
    "tp2",  # 11.3 / PDR 03.3 — TP2 INITIAL (audit) ; la sortie recalcule (decision Jonas 09/07)
    "is_short",  # 11.3 / A2 — sens de la position, FIGE a l'entree. Toute la geometrie
                 # (R, SL, TP, MAE/MFE) en depend : c'est l'etat le plus critique du trade.
)


def direction_sign(is_short) -> int:
    """+1 long / -1 short — LE facteur qui symetrise toute la geometrie (A2, docs/03 §3.7).

    Convention unique du projet, a utiliser partout plutot que des `if is_short` disperses :
        risque  = d x (entree - SL_initial)      > 0 dans les deux sens
        R(prix) = d x (prix - entree) / risque
        prix(R) = entree + d x R x risque
    """
    return -1 if bool(is_short) else 1


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
    tp2: float = 0.0  # PDR 03.3 — TP2 initial (audit) ; sortie = resistance courante (Jonas 09/07)
    is_short: bool = False  # A2 — fige a l'entree. Defaut False = retrocompat totale des
                            # trades ouverts avant le 04/08 (relus en long, comme avant).

    @property
    def sign(self) -> int:
        """+1 long / -1 short (A2) — evite de re-deriver le sens dans chaque G-rule."""
        return direction_sign(self.is_short)

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict) -> "TradeState":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


# ------------------------------------------ Fichiers d'etat (11.3, M04)
# Chemins RELATIFS a user_data/ — resolus par l'appelant (live et backtest).
MACRO_STATE_FILE = "macro_state.json"                    # 11.3 / PDR 06.3
# C1 (decision Jonas 2026-08-03) — calendrier economique en DEUX sources.
CALENDAR_STATIC_FILE = "calendar/economic_calendar.json"  # PRIMAIRE : versionne, zero reseau
CALENDAR_FF_CACHE_FILE = "calendar/forexfactory_week.json"  # SECONDAIRE : cache, fetch hebdo
DAY_EQUITY_FILE = "state/day_equity.json"                # 11.3 — {"date","equity"}
HEARTBEAT_FILE = "state/heartbeat"                       # 11.3 — mtime = heartbeat
VETO_DIR = "veto"                                        # 11.3 — <signal_id>.flag
DECISIONS_DIR = "logs/decisions"                         # 11.3 — YYYY-MM-DD.jsonl
MANUAL_RESTART_FLAG = "state/manual_restart_required"    # M04 — 2 CB jour / semaine ISO
# Extensions actees (BUILD_NOTES 2026-07-06, a valider par Jonas au rapport) :
CB_DAY_FILE = "state/cb_day.json"          # M04 — {"iso_week","count"} declenchements CB jour
VETO_INTENT_SUFFIX = ".intent"             # 11.6 — <signal_id>.intent, mtime = heure d'intention
VETO_FLAG_SUFFIX = ".flag"                 # 11.3 — <signal_id>.flag : discord_bot pose, risk lit

# --------------------------------------------------- Journal JSONL (PDR 08.1)
# M06 — toute nouvelle cle => PDR 08.1 d'abord, version += 1.
# v2 (2026-08-03, decisions A4/A5) : regime_inputs gagne macro_regime + equity_veto
# + equity_veto_reason (docs/08 §8.1). C'est ce qui rend la porte macro ablatable a posteriori.
# v3 (2026-08-04, decision A2) : le bot est long ET short. `entry` porte `direction`,
# regime_inputs porte `direction_macro`. Sans ca, aucun journal anterieur n'est comparable
# a un journal post-short et le Test 1 de docs/01 (la macro donne-t-elle la direction ?)
# n'est pas mesurable : c'est LA colonne dont depend l'hypothese v4.
SCHEMA_VERSION = 3

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
        "direction",   # v3 / A2 — "long" | "short"
    ),
    "gestion": ("ts_utc", "pair", "signal_id", "rule", "before", "after", "profit_r"),
    "exit": (
        "ts_utc", "pair", "signal_id", "cause", "r_final", "mae_r", "mfe_r",
        "duration_h", "fees", "slippage",
    ),
    "system": ("ts_utc", "kind", "detail"),
}

# regime_inputs de `evaluation` (PDR 08.1 / 04.5) :
REGIME_INPUT_KEYS = ("adx4h", "ema50_4h", "ema200_4h", "close_vs_ema", "fear_greed", "macro_stale",
                     MACRO_REGIME_COL, EQUITY_VETO_COL, EQUITY_VETO_REASON_COL,  # v2, 03/08
                     "direction_macro")                                          # v3, 04/08 (A2)
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
SKIP_ZERO_STOP_DISTANCE = "skip_zero_stop_distance"  # M04.4 — entry == sl_initial


# ----------------------------------------------------------- signal_id (M06)
def spot_pair(pair: str) -> str:
    """"BTC/USDT:USDT" -> "BTC/USDT" (A2). Les paires FUTURES freqtrade portent un suffixe
    de reglement ; les tables indexees par paire (slippage 03.6, whitelist) restent en
    notation spot. Une paire spot traverse inchangee."""
    return pair.split(":")[0] if pair else pair


def make_signal_id(pair: str, ts_4h: datetime) -> str:
    """Cle de correlation evaluation -> gate_check -> entry -> gestion -> exit.

    Format PDR M06 : "{pair}-{ts_4h}". Normalise pour servir de nom de fichier
    veto flag sous Windows ("/" et ":" interdits ; les points sont permis).
    Format acte par Jonas 2026-07-09 : BTCUSDT-2026.07.06.T120000Z.

    ⚠️ A2 : le ":" des paires futures etait annonce comme normalise par cette docstring
    mais ne l'etait PAS. Sous "BTC/USDT:USDT" le signal_id contenait un ":", donc la
    creation du fichier `veto/<signal_id>.intent` levait OSError sous Windows — bug latent
    active par le passage en futures. Passer par spot_pair() le corrige ET garde les
    signal_id comparables entre un run spot et un run futures.
    """
    if ts_4h.tzinfo is None:
        ts_4h = ts_4h.replace(tzinfo=timezone.utc)
    stamp = ts_4h.astimezone(timezone.utc).strftime("%Y.%m.%d.T%H%M%SZ")
    return f"{spot_pair(pair).replace('/', '')}-{stamp}"
