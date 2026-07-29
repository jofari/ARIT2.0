# `research/_reporting` — rapport de backtest trade par trade

Produit un **fichier HTML autonome et local** à partir d'un CSV de trades freqtrade :
une fiche par position, avec le graphe du prix traversé, l'état jour par jour des cinq
composants macro, et le détail chiffré de la décision d'entrée **et** de sortie
(valeur mesurée, seuil de `docs/06 §6.2`, score, somme → régime).

**Local par construction.** Le HTML embarque ses données, son CSS et son JS : aucun CDN,
aucune requête réseau, aucune publication. Il s'ouvre par double-clic depuis le disque.
Règle posée par Jonas le 2026-07-29 : les rapports de backtest ne sortent pas de la machine.

## Générer

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe research/_reporting/trade_report.py `
  --trades research/macro_flip/trades_hold_neutre.csv `
  --out    research/macro_flip/RAPPORT_TRADES.html `
  --titre  "MacroFlip — les 12 trades, entrée par entrée" `
  --eyebrow "ARIT · Recherche · MacroFlip" `
  --meta "Run backtest-result-2026-07-27_19-38-05" `
  --meta "BTC/USDT:USDT perp · 4h · détail 5m" `
  --capital 10000 `
  --meta "10 000 USDT · 50 % par entrée · 1x"
```

`--capital` (défaut 10 000) est le capital de départ du run : il sert à tracer la **courbe
de capital marquée au marché**, réévaluée chaque jour position ouverte comprise, avec le
drawdown réellement traversé. Le CSV freqtrade ne contient pas le capital initial — s'il est
faux, toute la section « capital » est décalée.

`--meta` est répétable : chaque valeur devient une ligne de contexte dans l'en-tête.
Le CSV attendu est l'export freqtrade (`open_date`, `close_date`, `is_short`, `open_rate`,
`close_rate`, `stake_amount`, `profit_abs`, `profit_ratio`, `funding_fees`, `exit_reason`,
`enter_tag`). Un run freqtrade n'écrit pas ce CSV tout seul : l'extraire du zip
(`backtesting-show`) avant, comme dans `research/macro_flip/RUNS.md`.

## Vérifier avant de livrer

```powershell
node research/_reporting/check_report.js research/macro_flip/RAPPORT_TRADES.html
```

Le script rejoue le JS de la page contre un DOM minimal qui **lève** dès qu'un attribut SVG
vaut `NaN` ou qu'un `innerHTML` contient `undefined` — c'est ce test qui a attrapé le trade
clôturé par `force_exit` le 2026-07-13 alors que les données macro s'arrêtent au 12/07.

## Limites connues

- Le signal décrit fiche par fiche est **le régime macro uniquement** (les cinq composants de
  `arit_lib.macro_regime`). Un backtest piloté par la couche technique (features/CIO/G-rules)
  afficherait le prix et les trades correctement, mais les ledgers montreraient le contexte
  macro, pas la conviction qui a réellement déclenché l'entrée. Adapter `COMPS` dans
  `template.html` et `macro_timeline()` le jour où on veut journaliser une autre décision.
- Le prix vient de `user_data/data/binance/BTC_USDT-1d.feather` — une seule paire, en dur.
- Le régime est recalculé depuis `user_data/data/macro/` : si ces fichiers sont réactualisés
  après le run, le rapport peut différer du backtest d'origine. Pour un rapport durable,
  regénérer au moment du run.
- La courbe de capital est **reconstruite**, pas exportée par freqtrade : mise × sens ×
  variation du prix, funding du trade réparti au prorata des jours, prix de clôture quotidien
  (pas d'intrabar). Sur MacroFlip elle donne un creux max de −58,7 % là où l'étude
  `research/macro_flip/gestion_sim.py`, qui rejoue en 4h, trouve −61,8 % : même événement
  (juillet 2021), écart dû au pas quotidien et à la proration du funding. À ne pas citer
  comme chiffre officiel de drawdown.
- Le HTML pèse ~380 Ko pour 6,5 ans de données quotidiennes (la table quotidienne est
  embarquée en entier). À ne pas commiter systématiquement.
