# ARIT 2.0 — ARIT V1 (bot de trading crypto, freqtrade)

Bot swing-trading spot (BTC/ETH/SOL/BNB vs USDT) construit sur **freqtrade 2026.6**,
spec contractuelle : `docs/` (PDR v3). Aucun LLM dans le runtime ; toutes les décisions
sont des règles déterministes journalisées.

## Arborescence
```
user_data/strategies/AritV1.py    # stratégie freqtrade (mince, < 250 lignes)
user_data/strategies/arit_lib/    # modules purs : features, regimes, cio, risk, gestion, journal
                                  # + contracts.py (noms/clés) et params.py (TOUTES les constantes)
services/                         # 3 process séparés : macro_state, discord_bot, watchdog
tests/                            # pytest (générateur OHLCV seedé dans conftest.py)
docs/                             # PDR v3 = source de vérité (lire AVANT de coder)
user_data/logs/decisions/*.jsonl  # journal de décision (une ligne par événement)
```

## Environnement (Windows)
- venv : `C:\Users\jofar\venvs\arit` (Python 3.12, freqtrade 2026.6, talib, scipy).
- ⚠️ Pièges connus et leurs patchs : voir **`BUILD_NOTES.md`** (scipy manquant, `aiodns`
  cassé sous Windows → désinstallé, schéma config `telegram`/`api_server`,
  `populate_exit_trend` obligatoire).

## Commandes
```powershell
# Tests
& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q
# Backtest (toujours --timeframe-detail 5m)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy AritV1 `
  -c user_data/config.dry.json --timeframe-detail 5m --cache none
# Dry-run (quand docs/09 l'autorise)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe trade -c user_data/config.dry.json
```

## État du build
- Checklist qui fait foi : `PLAN.md` · leçons/pièges : `BUILD_NOTES.md` · bilan : `RAPPORT_BUILD.md` (fin de build).
- Interdits absolus (docs/README.md) : pas de LLM runtime, SL jamais élargi, zéro look-ahead,
  zéro valeur magique hors `params.py`, G1-G7/poids jamais hyperoptés, chaque évaluation
  journalisée (live/dry), `dry_run: true`.
