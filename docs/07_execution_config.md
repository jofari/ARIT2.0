# 07 — Exécution & configuration freqtrade

## 7.1 Config de référence (`config.dry.json` — valeurs contractuelles)
```json
{
  "dry_run": true,
  "dry_run_wallet": 10000,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "tradable_balance_ratio": 0.99,
  "max_open_trades": 3,
  "timeframe": "1h",
  "exchange": {"name": "binance",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]},
  "order_types": {"entry": "limit", "exit": "market",
    "stoploss": "market", "stoploss_on_exchange": true},
  "entry_pricing": {"price_side": "other"},
  "exit_pricing": {"price_side": "other"}
}
```
(Clés indicatives : la syntaxe exacte de chaque section — protections, discord, telegram=off — se vérifie dans la doc freqtrade au moment du code. Les VALEURS ci-dessus sont contractuelles.)
- `stoploss_on_exchange: true` = le SL vit chez Binance (stop-loss-limit spot) → protection même si le process meurt. `custom_stoploss` le met à jour (G1-G3).
- Sizing réel via `custom_stake_amount` (03) — `unlimited` + ratio libèrent le calcul.
- Protections freqtrade : CooldownPeriod (2 bougies post-sortie), StoplossGuard/MaxDrawdown configurées pour approcher CB séquentiel et CB jour (03.5) ; ce que les Protections natives ne couvrent pas exactement (−6 % équité intraday UTC, ÷2 risque 5 trades) est complété en custom dans `confirm_trade_entry`/`custom_stake_amount`.

### 7.1.1 AMENDEMENT du 2026-08-04 — protections natives câblées (dette C6)
Vérifié sur le freqtrade **installé** (2026.6), pas sur la doc : la liste `protections` ne
vit **plus dans `config.json`** mais dans la **stratégie** (`AritV1.protections`). Valeurs
contractuelles, source unique `params.PROTECTIONS` :

| Protection | Paramètres | Ce qu'elle approche |
|---|---|---|
| `CooldownPeriod` | `stop_duration_candles: 2` | 07.1 — pas de re-entrée immédiate sur la paire quittée |
| `StoplossGuard` | `lookback_period_candles: 24`, `trade_limit: 2`, `stop_duration_candles: 12`, `only_per_pair: false`, `only_per_side: false` | CB séquentiel 03.5 |
| `MaxDrawdown` | `lookback_period_candles: 24`, `trade_limit: 2`, `stop_duration_candles: 24`, `max_allowed_drawdown: 0.06` | CB jour 03.5 |

**Le natif et le custom ne sont pas redondants** — ils n'observent pas la même population :
- `StoplossGuard` compte les sorties **au stop** quel que soit leur R ; `risk.cb_sequential_state`
  compte toute clôture **≤ −0,8R** (donc aussi les sorties G6/G7) et exige qu'elles soient
  **consécutives**. Le natif est plus large sur le seuil, plus étroit sur le motif.
- `MaxDrawdown` mesure le drawdown des **trades clos** sur fenêtre glissante ;
  `risk.cb_day_active` mesure l'**équité wallet** contre le snapshot 00:00 UTC (positions
  ouvertes comprises). Seul le custom voit une perte latente.
- Le sizing ÷2 pendant 5 trades reste **hors de portée du natif** : aucune Protection
  freqtrade ne module la taille, elle ne fait que bloquer.

Choix des valeurs d'approximation (les seules non dérivées de 03.5) : `lookback` de
**24 bougies 1h = 1 jour**, faute de notion de « consécutif » côté natif ; et
`trade_limit: 2` pour `MaxDrawdown`, parce que le drawdown d'un trade unique est déjà borné
par son propre stop (03.3) et ne doit pas armer une protection de portefeuille.

⚠️ **En backtest les protections sont ignorées sans `--enable-protections`** — voir 7.2.

## 7.2 Données & backtest (commandes exactes)
```bash
freqtrade download-data --exchange binance \
  -p BTC/USDT ETH/USDT SOL/USDT BNB/USDT \
  -t 5m 1h 4h 1d --timerange 20170801-
freqtrade backtesting --strategy AritV1 -c user_data/config.dry.json \
  --timerange 20180101- --timeframe-detail 5m --enable-protections --cache none
```
`--timeframe-detail 5m` est OBLIGATOIRE pour tout backtest (fidélité des G-rules intrabar).
`--enable-protections` est OBLIGATOIRE depuis le 04/08 (C6) : **sans ce drapeau, freqtrade
ignore silencieusement `AritV1.protections`** et le backtest ne mesure pas le même produit
que le dry-run. Un run d'ablation qui veut mesurer l'apport des protections l'omet
volontairement — et le note dans `research/EXPERIMENTS.jsonl`. Historique max par paire (BTC/ETH ≈ 2017+, SOL ≈ 2020+ — le backtest par paire commence où ses données commencent).

## 7.3 Parité backtest/live (piège documenté)
En live les callbacks tournent ~toutes les 5 s ; en backtest 1×/bougie(-détail). Règle absolue : **toutes les G-rules et signaux se déclenchent sur CLÔTURES de bougies** (1h pour la gestion, 4h pour les setups) — jamais sur le tick. Le live n'agit donc pas plus souvent que le backtest ne le simule.

## 7.4 Environnement local (machine de Jonas, Windows 11)
- Python 3.11+ · installation freqtrade via pip (venv) ou Docker Desktop — au choix au Sprint 0 (pip recommandé pour déboguer avec Claude Code).
- **Veille Windows désactivée** (secteur branché) pendant dry-run — un laptop qui dort = trous dans les données du dry-run.
- Tout est en **UTC** (freqtrade natif) — ne jamais convertir en heure locale dans la logique.
- FreqUI locale (`api_server` sur 127.0.0.1) : consultation + arrêt d'urgence manuel. Jamais exposée sur le réseau.
- Rappel du gate matériel (09) : le passage au capital réel exige une machine always-on. Le laptop suffit pour dev + dry-run, pas pour 10 k€ en positions actives.
