# Module BACKTEST — « comment on prouve que ça marche ? »

> Agent d'origine : **Quant / Backtester** (la moitié « validation »).
> ⚠️ **Ce n'est pas un fichier de code.** Le moteur de backtest, c'est **freqtrade** lui-même.
> Ce qui nous appartient, c'est le **protocole** : `docs/09_validation_deploy.md`.

## Où sont les choses

| Quoi | Où |
|---|---|
| **Le protocole** (fait autorité) | [`../docs/09_validation_deploy.md`](../docs/09_validation_deploy.md) |
| Données de marché | `user_data/data/binance/*.feather` |
| Config utilisée | `user_data/config.dry.json` (4 paires, 10 000 USDT, `dry_run: true`) |
| Résultats bruts | `user_data/backtest_results/*.zip` + `.meta.json` (non commités) |
| Journal des décisions | `user_data/logs/decisions/*.jsonl` |
| Runs parallèles isolés | [`../backtest_lanes/`](../backtest_lanes/) (`run1..run5`) — jetable, hors git |

## LA règle absolue

```
TOUJOURS  --timeframe-detail 5m
```

Sans ça, freqtrade évalue SL et TP sur la bougie 1h entière et ne sait pas départager l'ordre
dans lequel le prix a touché le SL puis le TP. Les résultats deviennent **optimistes et faux**.
Ce n'est pas une préférence, c'est une condition de validité.

## Les commandes

```powershell
# 1) Télécharger les données
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe download-data --exchange binance `
  -p BTC/USDT ETH/USDT SOL/USDT BNB/USDT -t 5m 1h 4h 1d --timerange 20170801-

# 2) Backtester (produit B = défaut, les 7 G-rules actives)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy AritV1 `
  -c user_data/config.dry.json --timerange 20180101- --timeframe-detail 5m --cache none

# 3) Revoir le dernier résultat sans relancer
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting-show
```

## Le protocole A/B — le vrai test de l'edge

La thèse d'ARIT (`docs/01`) : **l'edge est dans la gestion, pas dans l'entrée.** Ce protocole est
ce qui la falsifie. Entrées **identiques** des deux côtés, on ne change que la gestion :

| | Contrôle A | Produit B |
|---|---|---|
| Env | `ARIT_CONTROL_A=1` | *(rien)* |
| Entrées | identiques | identiques |
| SL initial | identique | identique |
| Sortie | **TP fixe +1,5R, totale** | **G1-G7 complètes** |

**Exigence** : B > A sur **expectancy (R moyen)**, **profit factor** ET **drawdown max** — sur
l'historique complet **ET** sur chaque sous-période (2018-2020 bull · 2021-2022 bear ·
2023-2026 chop). Si B ne bat pas A partout, la thèse est fausse et il faut le dire.

**Ablation** : B moins chaque Gx (7 runs, `ARIT_G_OFF=Gx`) ⇒ contribution de chaque règle
documentée. Une règle qui dégrade systématiquement ⇒ désactivée par flag (décision Jonas,
journalisée).

Les overrides sont des **variables d'environnement** précisément pour lancer ces runs **en
parallèle** dans des lanes séparées sans jamais éditer `params.py`.

## Les seuils (`docs/09.2`) — chaque passage est une décision manuelle de Jonas

| Phase | Volume | Critères |
|---|---|---|
| Backtest | 2017+, ≥ 100 trades | PF ≥ 1,3 · DD ≤ 15 % · **B > A partout** |
| Dry-run | 6 mois, ≥ 50 trades | PF ≥ 1,3 · DD ≤ 10 % · win-rate ±10 pts du backtest · slippage réel ≤ 2× modélisé |
| Canari (10 000 USDT réels) | ≥ 2 mois | idem + véto Discord actif + exécution conforme au dry-run |
| Montée | — | paliers, jamais > ×2 d'un coup, ≥ 1 mois entre paliers |

**Gate matériel bloquant** (`09.4`) : capital réel ⇒ **machine always-on obligatoire**.
`stoploss_on_exchange` protège du pire pendant un downtime, mais **G1-G7 — l'edge — ne tournent
pas quand la machine dort**.

## Hyperopt — périmètre strict (`docs/09.3`)

Autorisé **uniquement** sur 3-5 paramètres d'**entrée** (seuil TREND, bornes ADX, displacement,
fraîcheur BOS). **JAMAIS** sur G1-G7, les poids, ou les garde-fous (interdit n°5).
Validation : optimisation 2018-2023, test hors-échantillon 2024-2026.

## État actuel

- Seul le **smoke test du 08/07** a tourné (BTC 30 j, 0 trade — critère = pas d'exception).
- La campagne macro a rendu son verdict : **« A + macro » dégrade**, seul le **veto HOSTILE**
  est valide. **Décision Jonas en attente** (voir dernier commit `notes:`).
- **Le protocole A/B complet n'a pas encore tourné sur l'historique complet.** C'est le
  prochain jalon réel du projet.
