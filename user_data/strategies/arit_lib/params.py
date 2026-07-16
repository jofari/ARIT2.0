"""Toutes les constantes du PDR v3 — UNIQUE source de valeurs du code.

Regle (docs/README interdit n4) : aucune valeur magique ailleurs. Chaque constante
cite sa source PDR. Modifier une valeur = modifier docs/ d'abord.
G1-G7 et poids : JAMAIS hyperoptes (docs/README interdit n5, PDR 09.3).
"""

import os as _os  # uniquement pour les overrides du protocole A/B (PDR 09 §9.1)

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
G2_ATR_BUFFER = 0.1            # PDR 03.4 G2 — SL = HL_1h - 0,1 x ATR(14)_1h (pivot N = PIVOT_N)
G3_TRIGGER_R = 1.0             # PDR 03.4 G3 — trailing ATR actif apres +1R
G3_ATR_MULT = 2.0              # PDR 03.4 G3 — SL = close_1h - 2,0 x ATR(14)_1h
G3_ATR_MULT_RISK_OFF = 1.5     # PDR 03.4 G3 / 04.2 — 1,5 x ATR en RISK_OFF
G4_TRIGGER_R = 1.5             # PDR 03.4 G4 — TP partiel au premier touch +1,5R
G4_SELL_FRACTION = 0.5         # PDR 03.4 G4 — vendre 50 %, une seule fois
G7_MAX_CANDLES_1H = 24         # PDR 03.4 G7 — time-stop apres 24 bougies 1h
G7_MIN_R = 0.5                 # PDR 03.4 G7 — si jamais atteint +0,5R

# ---- Outillage du protocole A/B (PDR 09 §9.1) — overrides d'ENVIRONNEMENT ----
# Permet de lancer plusieurs backtests EN PARALLELE sans editer ce fichier (chaque
# process recoit son env). Env non defini => defauts STRICTEMENT inchanges (produit B).
# Jamais utilise en dry-run/live ; ce n'est PAS de l'hyperopt (les valeurs G restent figees,
# on ne fait qu'activer/desactiver pour l'ablation 09 §9.1.4).

# PDR 09 §9.1.1 — controle A du test A/B : TP fixe +1,5R sortie totale, SL initial,
# aucune G-rule. Defaut False = produit B. Override : ARIT_CONTROL_A=1
CONTROL_A_MODE = _os.environ.get("ARIT_CONTROL_A", "") == "1"

# Flags d'ablation (PDR 03.4 / 09.1.4). Override : ARIT_G_OFF=G3 (desactive UNE regle).
_G_OFF = _os.environ.get("ARIT_G_OFF", "")
G_FLAGS_DEFAULT = {
    g: (g != _G_OFF) for g in ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
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
# décision Jonas 09/07 (BUILD_NOTES) — A/B : True = CHoCH prime sur BOS frais ; défaut = actuel.
# Override protocole (voir bloc 09 §9.1 plus haut) : ARIT_CHOCH_PRIORITY=1
S_STRUCTURE_CHOCH_PRIORITY = _os.environ.get("ARIT_CHOCH_PRIORITY", "") == "1"
SR_CLUSTER_TOL_ATR = 0.5          # PDR 05.2 — meme niveau si ecart <= 0,5 x ATR
SR_FORCE_TOUCHES_DIV = 4          # PDR 05.2 — force=min(t/4,1) ⚠️ NON IMPLEMENTE (13/07)
SR_WINDOW_4H = 180                # M01 — clustering sur 180 dernieres bougies 4h
SR_RR_FULL = 2.0                  # PDR 05.2 — s_sr = 1,0 si RR_dispo >= 2,0

ADX_PERIOD = 14                   # PDR 05.3
EMA_FAST = 50                     # PDR 05.3
EMA_SLOW = 200                    # PDR 05.3
RSI_PERIOD = 14                   # PDR 05.3
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9  # PDR 05.3
ATR_PERIOD = 14                   # PDR 05.3
VOL_SMA_PERIOD = 20               # PDR 05.3
BBANDS_PERIOD, BBANDS_STD = 20, 2  # PDR 05.3 — ⚠️ a cabler (decision Jonas 09/07)

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
FG_CACHE_HOURS = 1                # PDR 06.5 — ⚠️ service = constantes locales (a unifier)
CALENDAR_CACHE_MIN = 30           # PDR 06.5 — idem (miroir de spec, non consomme)
NEWS_KEYWORDS = ("NFP", "nonfarm", "FOMC", "rate decision", "CPI")  # PDR 06.1
NEXT_EVENTS_HORIZON_H = 48        # M08 — 3 prochains events high <= 48 h
NEXT_EVENTS_MAX = 3               # M08

# -------------------------- 06.2 Macro Analyst V1.1 (valide Jonas 2026-07-12, docs/06)
MACRO_DXY_WINDOW_D = 20           # 06.2 c1 — variation DXY sur 20 j ouvres
MACRO_DXY_THRESH = 0.005          # 06.2 c1 — +/-0,5 %
MACRO_RATES_WINDOW_D = 60         # 06.2 c2 — variation taux Fed sur 60 j
MACRO_RATES_THRESH = 0.10         # 06.2 c2 — +/-0,10 point
MACRO_STABLES_WINDOW_D = 30       # 06.2 c3 — variation mcap stablecoins sur 30 j
MACRO_STABLES_UP = 0.02           # 06.2 c3 — >= +2 % => +1
MACRO_STABLES_DOWN = -0.01        # 06.2 c3 — <= -1 % => -1
MACRO_FUNDING_WINDOW_D = 7        # 06.2 c4 — moyenne funding 7 j
MACRO_FUNDING_HOT = 0.0005        # 06.2 c4 — > +0,05 %/8h => -1 ; < 0 => +1
MACRO_PORTEUR_MIN = 2             # 06.2 — somme >= +2 => PORTEUR
MACRO_HOSTILE_MAX = -2            # 06.2 — somme <= -2 => HOSTILE (veto)
MACRO_STALE_HOURS = 48            # 06.2 — composant stale => 0
MACRO_STALE_FAILSAFE = 3          # 06.2 — >= 3 composants stale => HOSTILE
MACRO_NEUTRE_CONV_BUMP = 0.05     # 06.2 / 04.2 — NEUTRE : seuil de conviction +0,05
MACRO_REGIMES = ("PORTEUR", "NEUTRE", "HOSTILE")  # 06.2

# ----------------------------------------------- 07 Execution & config freqtrade
# NB : les valeurs marquees "miroir config" ont pour source RUNTIME user_data/config.dry.json ;
# elles vivent ici comme reference contractuelle du PDR (le code ne les lit pas).
DRY_RUN_WALLET_USDT = 10_000      # PDR 07.1 / README — miroir config (dry_run_wallet)
STAKE_CURRENCY = "USDT"           # PDR 07.1
PAIR_WHITELIST = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT")  # PDR 07.1 — miroir config
TIMEFRAME_BASE = "1h"             # PDR 07.1 / README
TIMEFRAME_SETUP = "4h"            # README — setups/entrees en cloture 4h
TIMEFRAME_CONTEXT = "1d"          # README
TIMEFRAME_DETAIL = "5m"           # PDR 07.2 — miroir CLI (--timeframe-detail obligatoire)
TRADABLE_BALANCE_RATIO = 0.99     # PDR 07.1 — miroir config
COOLDOWN_POST_EXIT_CANDLES = 2    # PDR 07.1 — ⚠️ Protections NON IMPLEMENTEES (13/07)

# --------------------------------------------------------- 08 Journal & HITL
VETO_WINDOW_MIN_CANARI = 5        # PDR 08.4 — fenetre veto Discord (canari)
VETO_WINDOW_MIN_DRYRUN = 0        # PDR 08.4 / 11.6 — dry-run : aucun veto
DIGEST_TIME_UTC = "08:00"         # PDR 08.2 — digest quotidien
SIGNAL_FRESH_1H_CANDLES = 3       # PDR 11.6 — fraicheur 4h ⚠️ NON APPLIQUEE (13/07)

# --------------------------------------------------- 09 / M10 Watchdog & services
WATCHDOG_HEARTBEAT_MAX_S = 600    # PDR 09.5 / M10 — heartbeat > 10 min => alerte
WATCHDOG_LOOP_S = 60              # M10 — boucle 60 s
WATCHDOG_CONFIRM_READS = 2        # M10 — 2 lectures avant d'agir (anti-faux-positif)
DISCORD_DOWN_ALERT_MIN = 15       # M09 — watchdog alerte si bot Discord down > 15 min
WATCHDOG_DUST_THRESHOLD_USDT = 1.0  # M10 §tests (seuil dust) — valeur NON fixee par le PDR,
                                    # actee 1.0 USDT au build (a valider par Jonas au rapport)
