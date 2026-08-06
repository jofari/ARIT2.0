# Session du 2026-08-04 — rapport complet

Poste remis à jour, backtest complet, **toutes les dettes C fermées**, glossaire macro versé
au second cerveau. Ce document rassemble tout ce qui a été fait, mesuré et décidé.

---

## 1. Remise à jour du poste

| Contrôle | Résultat |
|---|---|
| `git pull` | **9 commits** rapatriés (`615d7a1` → `ff8b9b3`), 52 fichiers, +5 520 lignes, fast-forward propre |
| Tests | 317 passed / 1 skipped |
| Ruff | clean |
| Imports | `AritV1` + 9 modules `arit_lib` + `services` → OK |
| venv | `C:\Users\jofar\venvs\arit`, freqtrade 2026.6, Python 3.12.10 |

**Données téléchargées** (elles manquaient entièrement — bloquant n°2 du 04/08) :

| Paire | Bougies 5m | Début réel |
|---|---|---|
| BTC/USDT:USDT | 726 301 | 2019-09-08 |
| ETH/USDT:USDT | 703 384 | 2019-11-27 |
| BNB/USDT:USDT | 681 781 | 2020-02-10 |
| SOL/USDT:USDT | 619 297 | 2020-09-14 |

24 fichiers feather : OHLCV **+ funding_rate + mark prices**, indispensables à un backtest
futures réaliste. Plus 8 séries macro (DXY, taux Fed, NASDAQ100, BTC daily, stablecoins,
funding BTC/ETH, Fear & Greed).

⚠️ Le `guide.md` documentait un download **spot** (`BTC/USDT`), périmé depuis A2 qui a fait
passer le bot en futures. Non corrigé — à trancher.

---

## 2. Backtest 2021-2026 — le premier après A1-A4 / C6

`backtest-result-2026-08-04_17-31-00` · 4 paires perp · 1h détail 5m · `--enable-protections`

| Métrique | Valeur |
|---|---|
| Trades | 79 (0,04/jour) |
| Profit | **−293,34 USDT (−2,93 %)** |
| Profit factor | **0,86** |
| Win rate | 35,4 % (28 G / 51 P) |
| Sharpe (wallet quotidien) | −0,16 |
| Max drawdown | 667,50 USDT (6,62 %) |
| Durée du drawdown | **1 570 jours** — 77 % de la période |
| Funding payé | −46,72 USDT |

**Par paire** : SOL +571,61 (seul positif, 50 % WR) · BNB −39,62 · ETH −234,38 ·
**BTC −590,95**. Retirer SOL rend le système franchement perdant : la performance tient à
une paire sur quatre.

**Par sortie** : `trailing_stop_loss` **71 trades (90 %), −527,29 USDT** · TP2 3 trades
+174,90 · G6 5 trades +59,05. Le trailing encaisse 9 sorties sur 10 et la totalité de la
perte. **15 trades (19 %) durent 0 minute** — ouverts et fermés sur la même bougie, MFE
moyen +0,35 %, PnL −225,52 USDT.

### Deux blocages diagnostiqués, pas devinés

1. **`macro_state.json` absent = 100 % des entrées refusées.** Fichier gitignoré, produit au
   runtime : absent d'un clone frais ⇒ fail-safe ⇒ **1 284 évaluations, 1 284 refus, tous sur
   `news_window`**. Deux backtests à 0 trade avant de comprendre. Non documenté dans `guide.md`.
2. **La porte news est inerte en backtest.** Une fois le fichier généré, il ne contient que
   les événements **à venir** : sur 2021-2026 la gate passe toujours (`news: ok` × 127). Ces
   chiffres décrivent la stratégie **sans filtre news**.

### Correction d'une erreur d'analyse

Annoncé d'abord : « 79/79 trades partent dans le bon sens (MFE > 0), l'entrée ne se trompe
jamais ». **Faux — artefact.** Le MAE est lui aussi à 79/79 : dès que le prix bouge,
`max_rate` passe au-dessus de l'entrée **et** `min_rate` en dessous. La statistique est vraie
par construction.

La bonne mesure est MFE **contre** MAE :

| Mesure | Moyenne | Médiane |
|---|---|---|
| MFE | +1,66 % | +0,62 % |
| MAE | −1,14 % | −0,48 % |
| **MFE > MAE** | **37 / 79 — 47 %** | |

**47 %, c'est pile ou face.** L'entrée n'a pas d'edge directionnel — ce qui **confirme** le
checkpoint de juillet au lieu de le contredire.

---

## 3. check_bias — le verdict

| Check | Résultat |
|---|---|
| `recursive-analysis` | **FAIL affiché — mais A1 est validé** |
| `lookahead-analysis` | **INDÉTERMINÉ** (0 trade capturé sur 20 requis, fenêtre 2023) |

Le FAIL vient des paliers 199 et 499, **plus courts que la config réelle** :

| Indicateur | 199 | 499 | **999 (réel)** | 1999 |
|---|---|---|---|---|
| `ema200_1d` | nan | **−0,313 %** | **0,000 %** | 0,000 % |
| `ema200_4h` | nan | −0,100 % | **0,000 %** | 0,000 % |

À 999, l'écart est **nul sur les 20 indicateurs**. Ta décision A1 (200 → 999) est confirmée
par la mesure ; le verdict FAIL du wrapper agrège des paliers qu'on n'utilise pas.

---

## 4. Dettes C — les 4 restantes fermées

C3, C4, C5, C6, C8 l'étaient déjà. **Il n'y a plus aucune dette C ouverte.**

### C1 — calendrier économique : changement de doctrine

Deux filtres cachés **retirés** de `fetch_forexfactory()` :
- **filtre de NOM** — ne gardait que FOMC/CPI/NFP ; un rouge « ISM Manufacturing PMI » était ignoré ;
- **filtre PAYS** — ne gardait que `USD` ; une décision BCE ou BoE rouge passait à la trappe.

Puis, sur ta liste de ~25 indicateurs : `WATCHED_EVENTS` (24 fragments de noms), capturés
**quelle que soit leur couleur** — la plupart sont oranges ou jaunes chez FF.

**Le palier orange, tranché par la mesure** :

| Règle | Capturés | Bloquants | Temps calendaire bloqué |
|---|---|---|---|
| Tout suivi promu | 40 | **40** | **~24 %** |
| **Palier orange (retenu)** | 40 | **11** | **~7 %** |

Sans palier, la semaine bloquait sur *Spanish Manufacturing PMI*, *Italian Services PMI*,
*French Final Services PMI* — 11 PMI nationaux publiés en cascade, sans effet sur le BTC. Les
11 bloquants retenus couvrent ISM Manufacturing, ADP, ISM Services, Unemployment Claims, NFP,
Employment Change.

**Dates CPI/NFP 2026** : 24 événements ajoutés (primaire 16 → 40). `bls.gov` refuse tout
(403 sur `requests` **et** sur WebFetch) : les dates viennent de sources **secondaires
concordantes**, tracé dans le fichier. Aucune date inventée.
⚠️ **2027 non couvert** — le BLS publie son calendrier annuel fin 2026.

**Résultat** : `calendar_source.py` sort en code 0, plus aucun trou. `macro_state.py` ne
logue plus ni warning ni erreur.

### C2, C7, C9
- **C2 spread** — fermée en *acte de non-codage* : reste inerte, journalisée sans décider,
  on tranchera sur mesure au dry-run. Zéro ligne écrite, et c'est le résultat.
- **C7 webhook** — régénéré, ancien supprimé.
- **C9 outillage** — `optuna` 4.9.0 + `plotly` 6.9.0 installés.

**320 tests verts, ruff propre.**

---

## 5. Bibliothèques utilisées

### Dépendances externes réellement importées par le code ARIT

| Bibliothèque | Version | Où et pourquoi |
|---|---|---|
| **freqtrade** | 2026.6 | moteur de backtest et d'exécution ; `IStrategy`, `Trade`, `@informative`, `stoploss_from_absolute` |
| **pandas** | 3.0.3 | tout le pipeline de features — DataFrames 1h/4h/1d |
| **numpy** | 2.5.1 | calcul vectoriel des scores (`np.minimum` sur la conviction) |
| **TA-Lib** | 0.6.8 | indicateurs : ATR, ADX, EMA, RSI, MACD, BBANDS, patterns `CDL*` |
| **requests** | 2.34.2 | services hors hot-path : Fear & Greed, FRED, DefiLlama, Binance, ForexFactory, webhook Discord |
| **ccxt** | 4.5.64 | connecteur exchange (via freqtrade) |
| **pytest** | 9.1.1 | les 320 tests |
| **ruff** | 0.15.20 | lint, gate G0 |

### Installées ce jour (C9)

| Bibliothèque | Version | Débloque |
|---|---|---|
| **optuna** | 4.9.0 | `freqtrade hyperopt` — ⚠️ interdit n°5 : jamais sur G1-G7 ni les poids |
| **plotly** | 6.9.0 | `plot-dataframe`, `plot-profit` |

### Tirées par freqtrade (non importées directement)

`scipy` 1.18.0 · `SQLAlchemy` 2.0.51 · `pyarrow` 24.0.0 (feather) · `aiohttp` 3.14.1 ·
`websockets` 16.0 · `pydantic` 2.13.4 · `orjson` 3.11.9 · `python-rapidjson` 1.23 ·
`python-telegram-bot` 22.8 · `rich` 15.0.0 · `questionary` 2.1.1 · `joblib` 1.5.3 ·
`alembic` 1.19.0 — **95 paquets** au total dans le venv.

### Standard library — et elle porte plus que les dépendances externes

Comptée en nombre de fichiers qui l'importent, `pathlib` est **le module le plus utilisé de
tout le projet**, devant n'importe quelle dépendance externe. Ce n'est pas un détail : deux
règles structurantes d'ARIT reposent entièrement sur la stdlib.

| Module | Fichiers | Rôle dans ARIT |
|---|---|---|
| **pathlib** | **20** | **règle Windows** : tous les chemins passent par `Path`, jamais de `/` codé en dur. C'est ce qui rend `C:\Users\jofar\...` portable dans le code |
| `json` | 16 | tout le bus de fichiers : `macro_state.json`, calendrier, cache FF, journaux `.jsonl`, résultats de backtest |
| `sys` | 13 | injection de `user_data/strategies` dans `sys.path` (les services importent `arit_lib` sans package installé) + codes retour du Task Scheduler |
| **datetime** | **13** | **règle « tout en UTC »** : `timezone.utc` partout, `timedelta` pour les fenêtres (news ±30 min, staleness 2 h, horizon 48 h). Aucune conversion locale nulle part |
| `os` | 9 | écritures **atomiques** (`os.replace` + `os.fsync`) : jamais de JSON à moitié écrit ; et `os.environ` pour les overrides du protocole A/B |
| `logging` | 9 | interdit n°4 du CLAUDE.md — jamais de `print` en prod |
| `time` | 4 | politesse rate-limit sur les API (`time.sleep(0.3)` entre pages Binance) |
| `argparse` | 4 | CLI des scripts hors runtime (`--fetch-ff`, `--only lookahead`) |
| `math` | 3 | `math.isfinite` sur les niveaux de stop — un NaN d'ATR doit faire *skip*, pas crasher |
| `types`, `csv`, `asyncio` | 2 chacun | duck-typing en test · export trades · services asynchrones |
| `subprocess`, `shutil`, `re`, `random`, `importlib`, `html`, `functools`, `dataclasses` | 1 chacun | `check_bias` lance freqtrade · rapport HTML · `TradeState` en dataclass |

Le point qui mérite d'être retenu : **les deux invariants les plus cités du projet — paths
Windows et UTC intégral — ne dépendent d'aucune bibliothèque tierce.** Ils tiennent à
`pathlib` et `datetime.timezone`, et c'est une bonne nouvelle : rien ne peut les casser lors
d'une montée de version de freqtrade ou de pandas.

### Modules internes ARIT (à ne pas confondre avec des libs)

`arit_lib` (contracts, params, features, regimes, cio, risk, gestion, journal, macro_regime) ·
`services` (macro_state, calendar_source, discord_bot, watchdog) · `AritV1`

**Zéro dépendance LLM au runtime** — conforme à l'interdit n°1 du PDR : aucun appel Claude
ou OpenAI dans le bot.

---

## 6. Ce qui reste ouvert

| Sujet | État |
|---|---|
| **Parité backtest/live rompue** | le régime macro V1.1 n'existe qu'en backtest ⇒ **le live est long-only alors que le backtest est long+short**. Les 28 shorts du run n'existeraient pas en dry-run. **Le vrai bloquant.** |
| Palier orange | à valider par toi : 7 % du temps bloqué, ou 24 % ? |
| Trailing stop | 90 % des sorties, −527 USDT, 15 trades de durée nulle |
| A2-ter / quater / quinquies | levier, véto actions, F&G < 25 — jamais tranchés |
| Chantiers B1-B17 | 0 sur 17 lancés ; la vague 1 est à coût quasi nul |
| D1 (jambes longues en spot) | +267 % → +579 % mesuré — **repoussé par toi**, gros changements à venir |
| CPI/NFP 2027 | à compléter quand le BLS publiera, fin 2026 |
| `lookahead-analysis` | à relancer sur 2021-2026, indéterminé sur 2023 seul |

### Anomalies d'outillage, non corrigées
1. `macro_state.json` absent bloque tout — à documenter dans `guide.md`.
2. `trade_report.py` cherche les prix en **spot** ⇒ HTML généré avec **tous les graphes vides**.
3. `guide.md §4` documente un download spot et « BTC 30 j », périmé depuis A2.

---

## 7. Second cerveau

**12 notes créées**, 1 enrichie, à partir de ton glossaire macro : `indicateur
macroeconomique` (table d'entrée), PMI, PIB/GDP, CPI, PPI/SPPI, CB Leading Index (10
composants), emploi, demande des ménages, HPI, FPI, notations — plus `calendrier economique
dans arit` côté projet.

`MAE et MFE` porte désormais le piège « MFE > 0 ne mesure rien » et sa leçon générale : un
100 % sur une mesure continue est une alarme, pas un résultat ; on le vérifie en calculant la
mesure miroir.

Scan anti-perte : **aucune note vide** dans le vault.
