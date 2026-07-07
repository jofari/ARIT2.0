"""Toutes les constantes du PDR v3 — UNIQUE source de valeurs du code.

Regle (docs/README interdit n4) : aucune valeur magique ailleurs. Chaque constante
cite sa source PDR. Modifier une valeur = modifier docs/ d'abord.
G1-G7 et poids : JAMAIS hyperoptes (docs/README interdit n5, PDR 09.3).
"""

# ---------------------------------------------------------------- 03.1 Sizing
RISK_BASE_PCT = 0.01           # PDR 03.1 — risque plancher 1 %
RISK_CAP_FIRST_PCT = 0.02      # PDR 03.1 — cap 2 % trades n1..100
RISK_CAP_AFTER_PCT = 0.03      # PDR 03.1 — cap 3 % ensuite
RISK_CAP_SWITCH_TRADE_NO = 100  # PDR 03.1 — compteur global persistant

# ------------------------------------------------- 03.2 Garde-fous d'entree
NEWS_WINDOW_MIN = 30           # PDR 03.2.2 / 06.1 — fenetre event high-impact +/-30 min
CALENDAR_STALE_HOURS = 2       # PDR 03.2.2 / 06.1 — calendrier irrecuperable > 2 h => bloquer
SPREAD_MAX_FRAC = 0.0005       # PDR 03.2.3 / 06.4 — spread instantane <= 0,05 %
MAX_OPEN_TRADES = 3            # PDR 03.2.4 / README — slots
RESIDUAL_RISK_MAX_PCT = 0.06   # PDR 03.2.5 — somme residuels + nouveau <= 6 %
WEEKLY_RISK_BUDGET_PCT = 0.08  # PDR 03.2.6 — risque initial engage / semaine ISO <= 8 %
WEEKLY_MAX_ENTRIES = 10        # PDR 03.2.6 — entrees / semaine ISO < 10
RR_MIN = 1.5                   # PDR 03.2.7 / 03.3 / 04.4 — RR d'entree obligatoire

# ------------------------------------------------------ 03.3 SL / TP initiaux
SL_HL_ATR_BUFFER = 0.1         # PDR 03.3 — SL = dernier HL 4h confirme - 0,1 x ATR(14)_4h
SL_FALLBACK_ATR_MULT = 1.5     # PDR 03.3 — fallback : entree - 1,5 x ATR(14)_4h
TP1_R = 1.5                    # PDR 03.3 — TP1 fixe +1,5R

# ------------------------------------- 03.4 G-rules (defauts FIGES, flags ablation)
G1_TRIGGER_R = 1.0             # PDR 03.4 G1 — break-even si profit >= +1,0R
G1_BE_BUFFER_FRAC = 0.001      # PDR 03.4 G1 — SL = entree x (1 + 0,001), buffer frais
G2_PIVOT_N = 2                 # PDR 03.4 G2 — pivot fractal N=2 (HL 1h confirme)
G2_ATR_BUFFER = 0.1            # PDR 03.4 G2 — SL = HL_1h - 0,1 x ATR(14)_1h
G3_TRIGGER_R = 1.0             # PDR 03.4 G3 — trailing ATR actif apres +1R
G3_ATR_MULT = 2.0              # PDR 03.4 G3 — SL = close_1h - 2,0 x ATR(14)_1h
G3_ATR_MULT_RISK_OFF = 1.5     # PDR 03.4 G3 / 04.2 — 1,5 x ATR en RISK_OFF
G4_TRIGGER_R = 1.5             # PDR 03.4 G4 — TP partiel au premier touch +1,5R
G4_SELL_FRACTION = 0.5         # PDR 03.4 G4 — vendre 50 %, une seule fois
G7_MAX_CANDLES_1H = 24         # PDR 03.4 G7 — time-stop apres 24 bougies 1h
G7_MIN_R = 0.5                 # PDR 03.4 G7 — si jamais atteint +0,5R

# Flags d'ablation (PDR 03.4 / 09.1.4) — version A du test central = tous False.
G_FLAGS_DEFAULT = {
    "G1": True, "G2": True, "G3": True, "G4": True,
    "G5": True, "G6": True, "G7": True,
}

# --------------------------------------------------------- 03.5 Circuit breakers
CB_DAY_EQUITY_DROP_PCT = 0.06     # PDR 03.5 — equite <= -6 % vs 00:00 UTC => stop entrees
CB_DAY_MAX_PER_ISO_WEEK = 2       # PDR 03.5 — 2 CB meme semaine ISO => restart manuel
CB_SEQ_LOSS_R = -0.8              # PDR 03.5 — 2 clotures consecutives <= -0,8R
CB_SEQ_CONSECUTIVE = 2            # PDR 03.5
CB_SEQ_COOLDOWN_CANDLES_1H = 12   # PDR 03.5 — cooldown 12 bougies 1h
CB_SEQ_RISK_DIVISOR = 2           # PDR 03.5 — cap de risque / 2
CB_SEQ_PENALTY_TRADES = 5         # PDR 03.5 — pendant les 5 trades suivants

# ------------------------------------------------------ 03.6 Frais & slippage
FEE_TAKER_FRAC = 0.001            # PDR 03.6 — Binance spot 0,1 % taker
SLIPPAGE_FRAC = {                 # PDR 03.6 — par cote
    "BTC/USDT": 0.0005, "ETH/USDT": 0.0005,
    "SOL/USDT": 0.0010, "BNB/USDT": 0.0010,
}

# --------------------------------------------------- 04.1 Regimes (classification)
FG_RISK_OFF_BELOW = 25            # PDR 04.1 / 06.2 — Fear&Greed < 25 => RISK_OFF
ADX_RANGE_BELOW = 20              # PDR 04.1 — ADX(14)_4h < 20 => RANGE
ADX_TREND_MIN = 25                # PDR 04.1 — ADX >= 25 (+ EMAs) => TREND
REGIMES = ("TREND", "TRANSITION", "RANGE", "RISK_OFF")  # PDR 04

# ------------------------------------------------ 04.2 Comportement par regime
SEUIL_TREND = 0.50                # PDR 04.2 — seuil conviction TREND
SEUIL_TRANSITION = 0.65           # PDR 04.2 — seuil conviction TRANSITION
FG_MULT_FULL_FROM = 45            # PDR 04.2 / 06.2 — F&G >= 45 => x1,0
MULT_FULL = 1.0                   # PDR 04.2
MULT_REDUCED = 0.85               # PDR 04.2 — 25 <= F&G < 45 ou TRANSITION => x0,85
MULT_RISK_OFF = 0.0               # PDR 04.2 — RISK_OFF => x0
ENTRY_REGIMES = ("TREND", "TRANSITION")  # PDR 04.2 / 04.4 — seuls regimes d'entree

# --------------------------------------------------- 04.3 Poids (FIGES, somme 1.0)
POIDS = {                         # PDR 04.3 — jamais hyperoptes
    "s_structure": 0.40, "s_momentum": 0.20, "s_sr": 0.15,
    "s_patterns": 0.15, "s_volume": 0.10,
}

SCORE_VALUES = (0.0, 0.3, 0.5, 0.7, 1.0)  # PDR 04.4 — scores discrets uniquement

# -------------------------------------------------------- 05 Features techniques
PIVOT_N = 2                       # PDR 05.1 — fractal N=2
PIVOT_CONFIRM_SHIFT = 2           # PDR 05.1 / M01 — confirme 2 bougies apres (anti-repaint)
BOS_DISPLACEMENT_ATR = 1.0        # PDR 05.1 — corps de cassure >= 1,0 x ATR(14)_4h
BOS_FRESH_CANDLES_4H = 3          # PDR 05.1 — BOS "frais" 3 bougies 4h
SR_CLUSTER_TOL_ATR = 0.5          # PDR 05.2 — meme niveau si ecart <= 0,5 x ATR
SR_FORCE_TOUCHES_DIV = 4          # PDR 05.2 — force = min(touches/4, 1)
SR_WINDOW_4H = 180                # M01 — clustering sur 180 dernieres bougies 4h
SR_RR_FULL = 2.0                  # PDR 05.2 — s_sr = 1,0 si RR_dispo >= 2,0

ADX_PERIOD = 14                   # PDR 05.3
EMA_FAST = 50                     # PDR 05.3
EMA_SLOW = 200                    # PDR 05.3
RSI_PERIOD = 14                   # PDR 05.3
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9  # PDR 05.3
ATR_PERIOD = 14                   # PDR 05.3
VOL_SMA_PERIOD = 20               # PDR 05.3
BBANDS_PERIOD, BBANDS_STD = 20, 2  # PDR 05.3 — journalisees, pas utilisees en V1

RSI_MOM_LOW, RSI_MOM_HIGH = 50, 70       # PDR 05.3 — s_momentum = 1,0 si RSI in [50,70]
RSI_MOM_SOFT_LOW, RSI_MOM_SOFT_HIGH = 45, 75  # PDR 05.3 — 0,5 si [45,50) ou (70,75]

PIN_BAR_WICK_BODY_RATIO = 2.0     # PDR 05.4 — meche basse >= 2 x corps
PIN_BAR_CLOSE_TOP_FRACTION = 1 / 3  # PDR 05.4 — cloture dans le tiers haut
PATTERN_RECENT_CANDLES_4H = 3     # PDR 05.4 — s_patterns = 0,5 si pattern < 3 bougies
ENTRY_CDL_PATTERNS = ("CDLENGULFING", "CDLHAMMER")  # PDR 05.4 — == 100
FILTER_DOJI = "CDLDOJI"           # PDR 05.4 — doji sur cassure => s_patterns = 0
CDL_BULLISH = 100                 # PDR 05.4 — sortie talib CDL* pour pattern bullish

VOL_STRONG_MULT = 1.5             # PDR 05.5 — s_volume = 1,0 si vol >= 1,5 x SMA20
VOL_OK_MULT = 1.0                 # PDR 05.5 — 0,5 si >= 1,0 x

FG_NEUTRAL_BACKTEST = 50          # PDR M02 — macro neutre backtest (>= FG_MULT_FULL_FROM)

# ----------------------------------------------------- 06 Vetos & donnees externes
FG_CACHE_HOURS = 1                # PDR 06.2 / 06.5 — cache Fear&Greed
CALENDAR_CACHE_MIN = 30           # PDR 06.5 — cache calendrier
NEWS_KEYWORDS = ("NFP", "nonfarm", "FOMC", "rate decision", "CPI")  # PDR 06.1
NEXT_EVENTS_HORIZON_H = 48        # M08 — 3 prochains events high <= 48 h
NEXT_EVENTS_MAX = 3               # M08

# ----------------------------------------------- 07 Execution & config freqtrade
DRY_RUN_WALLET_USDT = 10_000      # PDR 07.1 / README — capital dry-run = canari prevu
STAKE_CURRENCY = "USDT"           # PDR 07.1
PAIR_WHITELIST = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT")  # PDR 07.1 / README
TIMEFRAME_BASE = "1h"             # PDR 07.1 / README
TIMEFRAME_SETUP = "4h"            # README — setups/entrees en cloture 4h
TIMEFRAME_CONTEXT = "1d"          # README
TIMEFRAME_DETAIL = "5m"           # PDR 07.2 — obligatoire en backtest
TRADABLE_BALANCE_RATIO = 0.99     # PDR 07.1
COOLDOWN_POST_EXIT_CANDLES = 2    # PDR 07.1 — Protection CooldownPeriod

# --------------------------------------------------------- 08 Journal & HITL
VETO_WINDOW_MIN_CANARI = 5        # PDR 08.4 — fenetre veto Discord (canari)
VETO_WINDOW_MIN_DRYRUN = 0        # PDR 08.4 / 11.6 — dry-run : aucun veto
DIGEST_TIME_UTC = "08:00"         # PDR 08.2 — digest quotidien
SIGNAL_FRESH_1H_CANDLES = 3       # PDR 11.6 — signal 4h valide 3-4 bougies 1h (borne basse retenue)

# --------------------------------------------------- 09 / M10 Watchdog & services
WATCHDOG_HEARTBEAT_MAX_S = 600    # PDR 09.5 / M10 — heartbeat > 10 min => alerte
WATCHDOG_LOOP_S = 60              # M10 — boucle 60 s
WATCHDOG_CONFIRM_READS = 2        # M10 — 2 lectures avant d'agir (anti-faux-positif)
DISCORD_DOWN_ALERT_MIN = 15       # M09 — watchdog alerte si bot Discord down > 15 min
