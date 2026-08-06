# Backtest AritV1 — 2021-2026, premier run après A1-A4 / C6

**Run** `backtest-result-2026-08-04_17-31-00` · BTC/ETH/SOL/BNB `USDT:USDT` perp · 1h,
détail 5m · capital 10 000 USDT · max 3 positions · `--enable-protections` · `--cache none`
Période **2021-01-01 → 2026-08-04** (les données commencent au 1er perp de chaque paire :
BTC 2019-09, ETH 2019-11, BNB 2020-02, SOL 2020-09).

## Verdict

**Edge négatif.** 79 trades en 5 ans et 7 mois, profit factor 0,86, −293 USDT (−2,93 %).

| Métrique | Valeur |
|---|---|
| Trades | 79 (0,04/jour) |
| Profit absolu | **−293,34 USDT (−2,93 %)** |
| Profit factor | **0,86** |
| Win rate | 35,4 % (28 G / 51 P) |
| CAGR | −0,53 % |
| Sharpe (wallet quotidien) | −0,16 |
| Max drawdown | 667,50 USDT (6,62 %) |
| Durée du drawdown | **1 570 jours** (2021-04-27 → 2025-08-14) |
| Funding payé | −46,72 USDT |

Le drawdown dure **77 % de la période testée**. Ce n'est pas un creux, c'est l'allure
générale de la courbe.

## Par paire — une seule paire porte tout

| Paire | Trades | PnL | Win% |
|---|---|---|---|
| SOL | 22 | **+571,61** | 50,0 % |
| BNB | 21 | −39,62 | 33,3 % |
| ETH | 19 | −234,38 | 26,3 % |
| BTC | 17 | **−590,95** | 29,4 % |

SOL est le seul résultat positif et le seul à 50 % de réussite. BTC, la paire de référence
du PDR, est le pire contributeur. Retirer SOL rendrait le système franchement perdant :
la performance tient à une paire sur quatre, donc à rien de robuste.

## Par année — aucune stabilité

| Année | Trades | PnL |
|---|---|---|
| 2021 | 14 | −101,4 |
| 2022 | 9 | −234,5 |
| 2023 | 15 | −188,5 |
| 2024 | 14 | **+199,4** |
| 2025 | 19 | **+69,7** |
| 2026 (partiel) | 8 | −38,0 |

Trois années perdantes, deux gagnantes. Rien qui ressemble à un edge persistant.

## Le trou est à la SORTIE, pas à l'entrée

| Sortie | Nb | Part | PnL |
|---|---|---|---|
| `trailing_stop_loss` | **71** | **90 %** | **−527,29** |
| TP2 | 3 | 4 % | +174,90 |
| G6 | 5 | 6 % | +59,05 |

Le trailing stop encaisse 9 sorties sur 10 et **la totalité de la perte**. C'est le
problème le plus net du run — indépendamment de l'entrée, qui n'a pas d'edge non plus
(section précédente). Les deux sorties
prévues par la spec (TP2, G6) sont toutes deux positives mais ne concernent que 8 trades
sur 79 : la stratégie n'atteint quasiment jamais ses propres cibles.

### L'entrée : toujours pas d'edge directionnel

> ⚠️ **Piège de mesure, à ne pas répéter.** Une première lecture donnait « 79/79 trades
> partent dans le bon sens (MFE > 0) ». C'est un **artefact** : le MAE est lui aussi à
> 79/79. Dès que le prix bouge, `max_rate` est au-dessus de l'entrée **et** `min_rate` en
> dessous — tout trade va dans les deux sens. « MFE > 0 » ne mesure rien.

La comparaison qui a du sens est MFE **contre** MAE :

| Mesure | Moyenne | Médiane |
|---|---|---|
| MFE (excursion favorable) | +1,66 % | **+0,62 %** |
| MAE (excursion défavorable) | −1,14 % | **−0,48 %** |
| Ratio MFE/MAE | 1,46 | — |
| **Trades où le bon sens a dominé (MFE > MAE)** | **37 / 79 — 47 %** | — |

**47 %, c'est pile ou face.** L'entrée n'a pas d'edge directionnel démontrable sur ces
79 trades. Le ratio moyen de 1,46 est tiré par une poignée de gros gagnants (SOL) ; les
médianes, plus robustes, ne laissent qu'un avantage marginal (0,62 % contre 0,48 %).

Cela **confirme le checkpoint « edge d'entrée nul »** de juillet 2026. L'entrée reste à
réparer — mais la sortie détruit de la valeur en plus, et indépendamment.

Pour mémoire, 30 trades (38 %) sont montés à +1 % ou plus et **11 d'entre eux finissent
perdants** (37 %).

### Le symptôme dur : des trades de durée nulle

| Durée | Trades | Part |
|---|---|---|
| **0 minute** | **15** | **19 %** |
| ≤ 15 min | 21 | 27 % |
| médiane | 160 min | — |

**15 trades sont ouverts et fermés sur la même bougie**, tous par trailing stop. Un trailing
qui se déclenche dans la bougie d'entrée ne protège pas un gain : il paye les frais et le
spread pour rien. Ces 15 trades ont un MFE moyen de **+0,35 %** pour un PnL de
**−225,52 USDT** : ils partaient tous dans le bon sens et se font couper immédiatement.
C'est la première chose à instruire — avant toute retouche de l'entrée.

## Ce qui marche

- **Le short est opérationnel** (A2) : 28 trades sur 79 sont des shorts.
- **Les gates s'enchaînent correctement** : sur 127 évaluations, 79 `enter` et 48 `skip`,
  tous les skips sur `residual_risk`. Aucun blocage parasite.
- **Aucune exception** sur 5,5 ans de données et 4 paires.

## ⚠️ Trois réserves — à lire avant d'exploiter ces chiffres

1. **La porte news est INERTE dans ce run.** `_macro_ok()` lit `user_data/macro_state.json`,
   qui est un instantané du **présent** : sur 2021-2026 il ne contient aucun événement
   historique, donc la gate 2 passe systématiquement (`news: ok` sur les 127 évaluations).
   Ces chiffres décrivent la stratégie **sans filtre news**. C'est exactement le piège déjà
   documenté pour Finnhub dans `macro_state.py:17` (« la porte news est restée inerte tout
   ce temps »). **Un backtest news-aware demande un calendrier historique, qui n'existe pas.**
2. **79 trades, c'est trop peu pour conclure.** PF 0,86 sur 79 trades sur 4 paires n'a pas
   de valeur statistique. Le signe est indicatif, pas la magnitude.
3. **Aucun check anti-biais n'a tourné.** `startup_candle_count` est passé à 999 (A1) sans
   validation par `recursive-analysis`, et `lookahead-analysis` n'a pas été rejoué depuis
   A1-A4 / C6. Tant que `scripts/check_bias.py` n'a pas tourné, ce backtest n'est pas
   certifié.

## Deux anomalies d'outillage trouvées en chemin

1. **`macro_state.json` absent bloque 100 % des entrées.** Sur un clone frais, le fichier
   n'existe pas (gitignoré, produit au runtime) ⇒ fail-safe ⇒ `news_window` refuse tout.
   Deux premiers runs à 0 trade avant de le générer. À documenter dans `guide.md` : un
   backtest sur clone frais exige `python services/macro_state.py` d'abord.
2. **`research/_reporting/trade_report.py` ne trouve plus les prix.** Il cherche
   `user_data/data/binance/BTC_USDT-1d.feather` (chemin **spot**) alors que depuis A2 les
   données vivent dans `binance/futures/BTC_USDT_USDT-1d-futures.feather`. Le HTML se
   génère mais **tous les graphes sont vides**.
3. **Trou de couverture calendrier** : `macro_state.py` logue
   `TROU de couverture calendrier sur ['CPI', 'NFP']`. Le JSON versionné ne contient que
   16 événements FOMC (2026-01-28 → fin 2027) ; `BLS_CPI` et `BLS_NFP` ont
   `verified_utc: null`.

## Prochaine étape proposée

1. `scripts/check_bias.py` — savoir si ce backtest est seulement crédible.
2. Instruire le trailing stop, en commençant par les 15 trades de durée nulle.

Rien n'a été modifié dans le repo pour produire ce rapport.
