# user_data/ — l'espace de travail freqtrade (NE PAS RENOMMER)

| Ici | C'est quoi |
|---|---|
| `strategies/AritV1.py` | la stratégie (M07) — le « main » du bot |
| `strategies/arit_lib/` | **LE CODE DES MODULES** M01-M06 + params.py + contracts.py |
| `config.dry.json` | la config (paires, capital, dry_run) |
| `data/binance/` | les bougies téléchargées (.feather) |
| `backtest_results/` | les résultats de chaque backtest (.zip + .meta.json) |
| `logs/decisions/` | le journal JSONL : 1 ligne = 1 décision du bot |
| `macro_state.json`, `state/`, `veto/` | fichiers d'état runtime (écrits par les services/le bot) |

Carte complète : [`../guide.md`](../guide.md)
