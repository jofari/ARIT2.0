# Index des runs MacroFlip — quel zip correspond à quoi

> freqtrade nomme ses résultats avec un simple horodatage : rien dans le nom ne dit ce
> qu'il y a dedans. Ce fichier fait la correspondance. **Les zips sont dans
> `user_data/backtest_results/`, qui est gitignoré** — ils vivent uniquement sur la
> machine (synchronisée OneDrive), pas dans le dépôt. Les CSV listés ci-dessous, eux,
> sont commités : c'est la copie durable des trades.

| Zip (`user_data/backtest_results/`) | Ce que c'est | Trades | G / P | PnL | Copie commitée |
|---|---|---|---|---|---|
| `backtest-result-2026-07-27_19-33-56.zip` | Smoke de validation, 2020-01 → 2020-06. Sert à prouver la mécanique : flip même bougie, 1x, 50 %, zéro SL/TP | 3 | 3 / 0 | +5 706 | — |
| **`backtest-result-2026-07-27_19-38-05.zip`** | **Run principal** — règle de Jonas : on garde la position en NEUTRE. C'est celui de tous les chiffres du RAPPORT | **12** | **6 / 6** | **+26 348** | `trades_hold_neutre.csv` |
| `backtest-result-2026-07-27_19-52-48.zip` | Variante `ARIT_MACRO_FLAT_NEUTRE=1` : on repasse cash en NEUTRE | 134 | 62 / 72 | +6 962 | `trades_flat_neutre.csv` |

Tous les trois : stratégie `MacroFlip`, BTC/USDT:USDT perp, 4h, détail 5m, capital
10 000 USDT, `research/macro_flip/config.macro_flip.json`.

## Deux choses à savoir

1. **Aucun journal de décisions n'a été écrit.** `MacroFlip` n'appelle pas `arit_lib.journal`
   (choix assumé : c'est un banc de mesure, et docs/08 réserve `ev_evaluation` au live/dry).
   Le zip est donc le **seul** enregistrement des trades — d'où les CSV commités ici.
   Rien n'a été ajouté dans `user_data/logs/decisions/` le 27/07.
2. **`--export-filename` a été ignoré par freqtrade 2026.6.** Le run principal avait été
   lancé avec `--export-filename user_data/backtest_results/macroflip_hold_neutre.json` :
   le fichier n'existe pas, freqtrade a gardé son nom horodaté par défaut. Ne pas compter
   sur ce flag pour nommer un run — utiliser cet index à la place.

## Relire un run sans le relancer

```powershell
# le DERNIER run (actuellement la variante flat-NEUTRE)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting-show --userdir user_data

# un run précis
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting-show --userdir user_data `
  --export-filename user_data/backtest_results/backtest-result-2026-07-27_19-38-05.zip
```
