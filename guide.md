# GUIDE — carte du repo ARIT 2.0

> Tu te perds ? Ce fichier est la carte. Chaque dossier a aussi son mini-README.
> Règle d'or : les noms `user_data/`, `tests/`, `services/`, `docs/` sont IMPOSÉS par les
> outils (freqtrade, pytest, Python) — ne pas les renommer, sinon le bot casse.

## 1. Vue en 30 secondes

ARIT = **4 programmes séparés** qui communiquent par fichiers :

```
┌─ freqtrade + AritV1.py ─┐   lit   ┌─ user_data/macro_state.json ─┐  écrit  ┌─ services/macro_state.py ─┐
│  LE BOT (trade/backtest)│ ──────► │  (état macro : F&G, news)    │ ◄────── │  va chercher F&G + news   │
└──────────┬──────────────┘         └──────────────────────────────┘         └───────────────────────────┘
           │ écrit
           ▼
  user_data/logs/decisions/*.jsonl  ◄─── lu par ───  services/discord_bot.py  (digest + véto humain)
  user_data/state/heartbeat         ◄─── surveillé ─  services/watchdog.py    (alerte si le bot meurt)
```

## 2. Les dossiers racine

| Dossier | C'est quoi | Tu y vas quand… |
|---|---|---|
| `docs/` | **LA SPEC OFFICIELLE** (PDR v3, 22 fichiers : couches 01-11 + `modules/M01-M10`) | tu veux savoir CE QUE le bot doit faire |
| `user_data/` | Tout ce que freqtrade utilise/produit : stratégie, **code des modules**, config, données, **résultats de backtest**, journaux | tu veux le code, un backtest, un journal |
| `services/` | Les 3 programmes annexes (macro, Discord, watchdog) — hors freqtrade | tu touches au macro/Discord/watchdog |
| `tests/` | Les 146 tests pytest (1 fichier par module) | tu veux vérifier que rien n'est cassé |
| `for claude build/` | Ressources du BUILD : prompt, pack, PLAN.md (checklist), BUILD_NOTES.md (pièges), RAPPORT_BUILD.md (bilan) | tu veux l'historique/état du chantier |
| ⚠️ | `for claude build/ARIT_PDR_v3/` = **vieille copie INCOMPLÈTE** (11 fichiers, sans modules/). La vraie spec = `docs/` à la racine. | |

## 3. Où est le code de chaque module

Tout le code métier vit dans **`user_data/strategies/arit_lib/`** (1 module = 1 fichier) :

| Module | Rôle (1 ligne) | Code | Tests | Spec |
|---|---|---|---|---|
| M01 features | calcule indicateurs, pivots, structure, scores s_* | `user_data/strategies/arit_lib/features.py` | `tests/test_features.py` | `docs/modules/M01_features.md` + `docs/05` |
| M02 regimes | classe le marché : TREND / TRANSITION / RANGE / RISK_OFF | `…/arit_lib/regimes.py` | `tests/test_regimes.py` | `M02` + `docs/04` |
| M03 cio | vote pondéré → conviction [0,1] + signal | `…/arit_lib/cio.py` | `tests/test_cio.py` | `M03` + `docs/04` |
| M04 risk | garde-fous d'entrée + sizing + circuit breakers | `…/arit_lib/risk.py` | `tests/test_risk.py` | `M04` + `docs/03` |
| M05 gestion | règles G1-G7 (BE, trailing, TP partiel…) + SL/TP initiaux | `…/arit_lib/gestion.py` | `tests/test_gestion.py` | `M05` + `docs/03` |
| M06 journal | écrit chaque décision en JSONL (append-only) | `…/arit_lib/journal.py` | `tests/test_journal.py` | `M06` + `docs/08` |
| M07 strategy | la colle freqtrade (mince, < 250 lignes, zéro métier) | `user_data/strategies/AritV1.py` | `tests/test_strategy.py` | `M07` + `docs/11` |
| M08 macro | service : Fear&Greed + calendrier → macro_state.json | `services/macro_state.py` | `tests/test_macro_state.py` | `M08` + `docs/06` |
| M09 discord | service : digest quotidien + véto humain | `services/discord_bot.py` | `tests/test_discord_bot.py` | `M09` + `docs/08` |
| M10 watchdog | service : alerte + flatten si le bot meurt | `services/watchdog.py` | `tests/test_watchdog.py` | `M10` + `docs/09 §9.5` |

Les 2 fichiers « contrats » (jamais de logique) : `arit_lib/params.py` = TOUTES les constantes
(chacune avec sa source PDR) · `arit_lib/contracts.py` = noms de colonnes, clés, fichiers d'état.

## 4. Les BACKTESTS — de A à Z

| Quoi | Où |
|---|---|
| **Données** de marché (bougies) | `user_data/data/binance/*.feather` (actuellement : BTC/USDT 30 j en 5m/1h/4h/1d) |
| **Config** utilisée | `user_data/config.dry.json` (paires, capital 10 000 USDT, dry_run) |
| **Résultats** de chaque run | `user_data/backtest_results/backtest-result-<date>.zip` + `.meta.json` (non commités — artefacts) |
| Journal des décisions du run | `user_data/logs/decisions/*.jsonl` (en live/dry ; en backtest : gate_check/entry/exit) |

```powershell
# 1) Télécharger plus de données (ex. historique complet 2017+)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe download-data --exchange binance `
  -p BTC/USDT ETH/USDT SOL/USDT BNB/USDT -t 5m 1h 4h 1d --timerange 20170801-

# 2) Lancer un backtest (RÈGLE : toujours --timeframe-detail 5m)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy AritV1 `
  -c user_data/config.dry.json --timerange 20180101- --timeframe-detail 5m --cache none

# 3) Revoir le DERNIER résultat sans relancer
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting-show
```

Le protocole de validation (A/B, ablation G1-G7, seuils PF/DD) : `docs/09_validation_deploy.md`.
Ce qui a déjà tourné : uniquement le **smoke** du 08/07 (BTC 30 j, 0 trade, critère = pas d'exception).

## 5. « Où sont les 10 agents ? » (Macro Analyst, CIO, Backtester…)

**Ils existent, mais pas sous forme d'agents IA.** L'interdit n°1 du PDR = AUCUN LLM dans le
runtime. La vision multi-agents (façon Aladdin) a été traduite en **modules déterministes** :
chaque « agent » est devenu un fichier de code testable. Claude ne sert qu'à DÉVELOPPER le bot.

| Agent (vision d'origine) | Devenu quoi | Le code est ici |
|---|---|---|
| **Macro Analyst** | collecteur macro (Fear&Greed + calendrier éco → fichier d'état) | `services/macro_state.py` (M08) |
| **Sentiment Watcher** | le Fear&Greed du macro_state + veto RISK_OFF | `services/macro_state.py` + `arit_lib/regimes.py` |
| **Technical Analyst** | toutes les features techniques (indicateurs, structure, S/R, patterns) | `arit_lib/features.py` (M01) |
| **Flow Specialist** | réduit au score volume `s_volume` (PDR 05.5) | `arit_lib/features.py` (M01) |
| **Main Agent CIO** | classification du régime + vote pondéré → conviction | `arit_lib/regimes.py` (M02) + `arit_lib/cio.py` (M03) |
| **Strategist** | profils de poids par régime + seuils (figés, jamais hyperoptés) | `arit_lib/params.py` (POIDS, SEUIL_*) consommés par `cio.py` |
| **Risk Manager** | garde-fous d'entrée, sizing, circuit breakers + gestion G1-G7 | `arit_lib/risk.py` (M04) + `arit_lib/gestion.py` (M05) |
| **Executing Trader** | l'exécution des ordres = freqtrade lui-même, piloté par la stratégie | `user_data/strategies/AritV1.py` (M07) |
| **Performance Controller** | journal de chaque décision + chien de garde | `arit_lib/journal.py` (M06) + `services/watchdog.py` (M10) |
| **Quant / Backtester** | PAS un module : c'est le moteur de backtest freqtrade + le protocole A/B | commande §4 + `docs/09_validation_deploy.md` |

À ne pas confondre avec les **sous-agents de BUILD** (`arit-coder`, `arit-reviewer`,
`arit-runner`) : ce sont des prompts `.md` dans `.claude/agents/` que Claude Code utilise
pour CONSTRUIRE le bot — aucun rapport avec le code qui trade.

## 6. Trouver vite

- **« Pourquoi le bot a fait ça ? »** → `user_data/logs/decisions/YYYY-MM-DD.jsonl` (1 ligne = 1 décision, format `docs/08`).
- **« C'est quoi cette constante ? »** → `user_data/strategies/arit_lib/params.py` (le commentaire cite le PDR).
- **« Ça marche encore ? »** → `& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q` (attendu : 146 passed).
- **« Où en est le chantier ? »** → `for claude build/PLAN.md` (état) · `RAPPORT_BUILD.md` (bilan + questions) · `BUILD_NOTES.md` (pièges Windows/freqtrade et leurs patchs).
- **Secrets** : `.env` (jamais commité) — modèle dans `.env.example`.
