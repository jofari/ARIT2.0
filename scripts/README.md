# scripts/ — utilitaires hors runtime

Scripts lancés à la main, jamais par le bot. Aucun n'est importé par `arit_lib`.

| Script | Rôle |
|---|---|
| `check_bias.py` | checks mécaniques look-ahead (interdit n°3) + warm-up des indicateurs |
| `download_macro.py` | télécharge les 5 séries macro (DXY, taux, stablecoins, funding, F&G) |
| `send_discord_report.py` | pousse un rapport sur le webhook Discord (URL dans `.env` uniquement) |

## check_bias.py — la preuve mécanique de deux interdits

Enveloppe deux commandes natives de freqtrade avec les conventions ARIT en dur (stratégie
`AritV1`, `user_data/config.dry.json`, venv `C:\Users\jofar\venvs\arit`), parse leurs sorties
et rend un **verdict machine-lisible**.

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe scripts\check_bias.py                  # les deux checks
& C:\Users\jofar\venvs\arit\Scripts\python.exe scripts\check_bias.py --only lookahead
& C:\Users\jofar\venvs\arit\Scripts\python.exe scripts\check_bias.py --only recursive -p BTC/USDT
```

### 1. `lookahead-analysis` → l'interdit n°3 (zéro look-ahead)

freqtrade rejoue la stratégie sur des fenêtres **tronquées** et vérifie qu'un signal passé ne
change pas quand on ajoute du futur. C'est exactement ce que ARIT combat à la main (pivots
`shift(2)`, `process_only_new_candles`, bougies closes uniquement, merge freqtrade) mais qui
n'était jusqu'ici garanti que par relecture humaine.

Coût : un run. Valeur : la preuve mécanique d'un interdit.

### 2. `recursive-analysis` → `startup_candle_count`

Recalcule les indicateurs avec 199 / 499 / 999 / 1999 bougies de warm-up (freqtrade ajoute
d'office celui de la stratégie, `EMA_SLOW` = 200) et compare la dernière ligne. Si les valeurs
bougent, l'EMA200 est fausse au début de chaque run et **le backtest est faux sans le dire**.
La commande rend en prime un verdict look-ahead sur les indicateurs seuls.

### Sorties — `analysis/out/bias/` (gitignoré)

| Fichier | Contenu |
|---|---|
| `lookahead_<stamp>.log` / `recursive_<stamp>.log` | sortie brute freqtrade (dont ses tableaux) |
| `lookahead_<stamp>.csv` | export natif freqtrade (`has_bias`, signaux biaisés, indicateurs) |
| `bias_<stamp>.md` | rapport lisible (verdicts + tableaux + mode d'emploi) |
| `bias_<stamp>.json` | mêmes verdicts, exploitables par un autre script |

### Verdicts et codes de sortie

| Code | Sens |
|---|---|
| `0` | tout PASS (un WARN récursif — écart < 0,1 % — ne fait pas échouer) |
| `1` | au moins un FAIL : look-ahead détecté, ou écart d'indicateur ≥ 0,1 % selon le warm-up |
| `2` | INDÉTERMINÉ : trop peu de signaux (`--minimum-trades`) ou erreur outil — **jamais un succès** |

### Options utiles

| Option | Défaut | Note |
|---|---|---|
| `--timerange` | `20230101-20240101` | ~1 an, assez de signaux pour un run tenable |
| `--targeted-trades` / `--minimum-trades` | 200 / 20 | sous le minimum, verdict INDÉTERMINÉ |
| `--startup-candles` | `199 499 999 1999` | freqtrade ajoute le compte de la stratégie |
| `--pairs` | whitelist de la config | `recursive-analysis` n'utilise de toute façon que la 1re paire |
| `--timeframe-detail` | *absent* | contractuel pour les **backtests** (PDR 07.2), inutile ici : ces checks portent sur les indicateurs et les signaux, pas sur l'exécution intra-bougie |

Tests : `tests/test_check_bias.py` (parsing des tableaux rich + verdicts, sans lancer freqtrade).

### Relevés

- **2026-07-31 · `recursive-analysis` = FAIL** au `startup_candle_count` actuel (200) : écart
  max **4,26 % à 9,55 %** sur `ema200_1d` selon la fenêtre. Seuls `ema200_1d` et `ema200_4h`
  dérivent réellement — tous les autres indicateurs sont ≤ 0,013 % dès 200.

  Mécanique : `startup_candle_count` se compte en bougies **de chaque timeframe**, pas en
  durée. 200 ⇒ 200 bougies 1 d de warm-up = exactement la période de l'EMA200, donc la valeur
  au départ n'est que la SMA200 d'amorçage de TA-Lib. Une EMA a besoin de ~3-5× sa période.

  Balayage des `startup_candle_count` (écart de `ema200_1d` sur la dernière bougie, 3 fenêtres) :

  | startup | BTC 2019-2024 | BTC 2018-2021 | ETH 2020-2026 | pire cas | appels API/démarrage |
  |---|---|---|---|---|---|
  | 200 (actuel) | −4,39 % | −9,55 % | +6,69 % | **9,55 %** | 1 |
  | 500 | −0,31 % | +0,03 % | −0,08 % | 0,31 % | 1 |
  | 600 | −0,08 % | +0,10 % | +0,07 % | 0,10 % | 1 |
  | 800 | +0,02 % | −0,01 % | −0,01 % | 0,02 % | 1 |
  | **999** | **0,000 %** | **0,000 %** | **0,001 %** | **0,001 %** | **1** |
  | 1500-4800 | 0,000 % | 0,000 % | 0,000 % | 0,000 % | 2 à 5 |
  | ≥ 5000 | — | — | — | — | **refusé par freqtrade** |

  **Recommandation swing : `startup_candle_count = 999`** (proposition, non appliquée —
  `params.py` est sous gouvernance PDR). C'est le plus petit palier où l'écart est nul sur les
  3 fenêtres, et le dernier qui tient en **un seul appel OHLCV** (limite Binance = 1000
  bougies/appel) : au-delà, freqtrade avertit « Using N calls » à chaque démarrage du bot,
  sans aucun gain de précision. Plafond dur : `5 × 999 = 4999` bougies, au-delà freqtrade
  refuse de démarrer (`Configuration error`).

  Limite résiduelle (données, pas config) : 999 bougies 1 d ≈ 2,7 ans d'historique avant le
  début du backtest. Les données Binance commencent le 2017-08-17 → un backtest démarrant en
  2018 n'aura jamais son warm-up complet et son `ema200_1d` ne devient fiable que ~2 ans plus
  tard. Les sous-périodes du protocole (docs/09 §9.1.3) démarrant en 2018 sont concernées.
- **2026-07-31 · `lookahead-analysis`** (4 paires, 20200101-20260101, 67 signaux, 50 min de run) :

  | Métrique | Valeur |
  |---|---|
  | signaux testés | 67 |
  | entrées biaisées | **0** |
  | sorties biaisées | **0** |
  | indicateurs signalés | `pivot_high_4h`, `pivot_low_4h` |

  **Lecture : aucun look-ahead décisionnel.** Zéro entrée et zéro sortie ne changent quand on
  retire le futur — l'interdit n°3 est mécaniquement vérifié sur la chaîne de décision.

  Le `has_bias = Yes` porte uniquement sur les **pivots BRUTS**, qui repeignent *par
  construction* (un fractal N=2 ne peut être connu que 2 bougies plus tard) et que
  `features.py:117-119` documente déjà comme « JAMAIS décisionnels ». Le décisionnel utilise
  `pivot_high_conf` / `pivot_low_conf` (`shift(2)`), **non signalés par l'outil**.

  Proposition pour rendre l'audit vert (non appliquée, `arit_lib` sous gouvernance PDR) :
  supprimer `pivot_high` / `pivot_low` du DataFrame après le calcul des colonnes `_conf` — ce ne
  sont pas des colonnes contractuelles (`contracts.py:14` ne liste que les `_conf_4h`), donc les
  retirer ne change aucune décision et supprime le faux positif.

  Précédent relevé (BTC seul, 2023) : INDÉTERMINÉ, 2 signaux — sous le seuil de conclusion.
