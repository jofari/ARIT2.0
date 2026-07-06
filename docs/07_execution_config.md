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

## 7.2 Données & backtest (commandes exactes)
```bash
freqtrade download-data --exchange binance \
  -p BTC/USDT ETH/USDT SOL/USDT BNB/USDT \
  -t 5m 1h 4h 1d --timerange 20170801-
freqtrade backtesting --strategy AritV1 -c user_data/config.dry.json \
  --timerange 20180101- --timeframe-detail 5m --cache none
```
`--timeframe-detail 5m` est OBLIGATOIRE pour tout backtest (fidélité des G-rules intrabar). Historique max par paire (BTC/ETH ≈ 2017+, SOL ≈ 2020+ — le backtest par paire commence où ses données commencent).

## 7.3 Parité backtest/live (piège documenté)
En live les callbacks tournent ~toutes les 5 s ; en backtest 1×/bougie(-détail). Règle absolue : **toutes les G-rules et signaux se déclenchent sur CLÔTURES de bougies** (1h pour la gestion, 4h pour les setups) — jamais sur le tick. Le live n'agit donc pas plus souvent que le backtest ne le simule.

## 7.4 Environnement local (machine de Jonas, Windows 11)
- Python 3.11+ · installation freqtrade via pip (venv) ou Docker Desktop — au choix au Sprint 0 (pip recommandé pour déboguer avec Claude Code).
- **Veille Windows désactivée** (secteur branché) pendant dry-run — un laptop qui dort = trous dans les données du dry-run.
- Tout est en **UTC** (freqtrade natif) — ne jamais convertir en heure locale dans la logique.
- FreqUI locale (`api_server` sur 127.0.0.1) : consultation + arrêt d'urgence manuel. Jamais exposée sur le réseau.
- Rappel du gate matériel (09) : le passage au capital réel exige une machine always-on. Le laptop suffit pour dev + dry-run, pas pour 10 k€ en positions actives.
