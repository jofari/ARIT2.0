# Guide technique ARIT — comprendre chaque outil de TON projet

> Ce guide explique chaque brique du projet : ce que c'est, pourquoi elle a été choisie ICI,
> et où la voir à l'œuvre dans TON code. Chaque exemple est un extrait réel du repo, avec
> le lien vers le fichier. Lis-le dans l'ordre la première fois, puis utilise-le comme référence.

## Table des matières

1. [Python + venv](#1-python--venv)
2. [pandas + numpy — la vectorisation](#2-pandas--numpy--la-vectorisation)
3. [TA-Lib — les indicateurs en C](#3-ta-lib--les-indicateurs-en-c)
4. [freqtrade — le framework de trading](#4-freqtrade--le-framework-de-trading)
5. [pytest — le filet de sécurité](#5-pytest--le-filet-de-sécurité)
6. [ruff — le linter](#6-ruff--le-linter)
7. [git + GitHub — l'historique](#7-git--github--lhistorique)
8. [Formats de données](#8-formats-de-données--feather-json-jsonl-csv)
9. [requests / API HTTP](#9-requests--api-http)
10. [Les patterns MAISON du projet](#10-les-patterns-maison-du-projet)
11. [Glossaire](#11-glossaire)
12. [Comment ce projet a été construit](#12-comment-ce-projet-a-été-construit)

---

## 1. Python + venv

**À quoi ça sert.** Python est le langage de tout le projet. Un venv (environnement virtuel)
est un dossier qui contient une copie isolée de Python + les bibliothèques du projet, pour que
les versions d'ARIT (freqtrade 2026.6, talib 0.6.8…) ne se mélangent jamais avec celles d'un
autre projet ou du Python global de Windows.

**Pourquoi ici.** freqtrade tire des dizaines de dépendances aux versions précises. Sans venv,
installer JARVIS ou un autre projet pourrait casser ARIT en remplaçant une version. Et surtout :
ton venv vit **hors OneDrive**, à `C:\Users\jofar\venvs\arit`. La leçon est documentée dans
[BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md) (note du 2026-07-06) :

> le repo vit dans OneDrive ; un venv freqtrade ≈ dizaines de milliers de fichiers que OneDrive
> synchronise et verrouille (échecs pip aléatoires, CPU).

OneDrive essaie de synchroniser chaque `.pyc`, verrouille des fichiers pendant que pip écrit
→ installations qui échouent au hasard. Le code (léger, précieux) reste dans OneDrive ;
le venv (lourd, régénérable) reste dehors.

**Où le voir dans ton code.** Chaque commande du projet appelle explicitement le Python du venv :

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy AritV1 ...
```

C'est le `Scripts\python.exe` DU venv, pas le `python` global — voir [guide.md](guide.md) §4 et §7.

---

## 2. pandas + numpy — la vectorisation

**À quoi ça sert.** pandas fournit le `DataFrame` : un tableau où chaque ligne est une bougie
(date, open, high, low, close, volume) et chaque colonne une série de valeurs. numpy est le
moteur de calcul en dessous : des tableaux de nombres traités en bloc, en C.

**Pourquoi ici.** Ton backtest traite ~70 000 bougies 1h par paire depuis 2018. La règle d'or :
**on n'écrit jamais `for bougie in bougies:`**. On écrit une opération sur la colonne ENTIÈRE,
et numpy la calcule d'un coup en C — des centaines de fois plus vite qu'une boucle Python.
C'est la « vectorisation ». Autre avantage : le code vectorisé décrit la RÈGLE, pas la mécanique.

**Où le voir dans ton code.** Le BOS haussier dans [features.py](user_data/strategies/arit_lib/features.py) (lignes 161-164) :

```python
# BOS haussier : cassure du dernier PH confirme + displacement (corps >= 1xATR).
body = (df["close"] - df["open"]).abs()
df["bos_bull"] = (df["close"] > last_ph) & (
    body >= params.BOS_DISPLACEMENT_ATR * df["atr"]
)
```

Décortiquons ligne par ligne :
- `df["close"] - df["open"]` : soustrait les DEUX COLONNES entières — une ligne de code =
  70 000 soustractions. `.abs()` : valeur absolue de tout → la taille du corps de chaque bougie.
- `df["close"] > last_ph` : compare chaque close au dernier pivot high connu à cet instant →
  une colonne de True/False (un « masque booléen »).
- `&` : le ET logique élément par élément (pas le `and` de Python, qui ne marche que sur UNE
  valeur). Résultat : `bos_bull` vaut True sur chaque bougie qui casse le pivot AVEC un corps
  ≥ 1×ATR — la définition du PDR, en 3 lignes, sans aucune boucle.

Deuxième exemple, `np.select` — le « tableau de décision » vectorisé, dans
[features.py](user_data/strategies/arit_lib/features.py) (lignes 307-316, score de structure) :

```python
df["s_structure"] = np.select(
    [
        warm_structure,             # M01 invariant 3 : warm-up => 0
        ranked[0][0],
        ranked[1][0],
        intact & ~bos_fresh,        # 05.1 : 0,7 — HH/HL intacte, continuation
    ],
    [_S0, ranked[0][1], ranked[1][1], _S07],
    default=_S03,                   # 05.1 : 0,3 — structure neutre
)
```

`np.select(conditions, valeurs, default)` = un `if/elif/elif/else` appliqué à toutes les bougies
d'un coup. Pour chaque ligne, il prend la **première** condition vraie (l'ordre compte : le
warm-up passe avant tout) et lui donne la valeur correspondante ; sinon le `default`. Résultat :
la table de scores du PDR 05.1 (0 / 0,3 / 0,7 / 1,0) devient une seule expression lisible.

Dernier idiome à connaître, `shift()` : décaler une colonne dans le temps.
`s.shift(1)` = « la valeur de la bougie précédente ». C'est LA brique de l'anti-look-ahead
(chapitre 10) : `shift` vers le passé = légal, vers le futur = interdit en décision.

Une exception assumée : [sr_levels](user_data/strategies/arit_lib/features.py) (ligne 214) contient
un vrai `for i in range(size)` — le clustering des supports/résistances est trop irrégulier pour
être vectorisé, et le df 4h est court. Le commentaire le dit : « Boucle Python assumée ».
La règle n'est pas religieuse, elle est pragmatique.

---

## 3. TA-Lib — les indicateurs en C

**À quoi ça sert.** TA-Lib est LA bibliothèque de référence des indicateurs techniques :
EMA, RSI, MACD, ATR, ADX et ~60 détecteurs de patterns de chandeliers, tous écrits en C.
Tu lui donnes des tableaux numpy, elle te rend l'indicateur calculé.

**Pourquoi ici.** Recoder un RSI à la main, c'est possible… et c'est le meilleur moyen
d'introduire un bug subtil (lissage de Wilder vs moyenne simple, gestion du warm-up) qui
fausserait TOUS tes backtests sans jamais planter. TA-Lib est testée depuis 20 ans, rapide
(C), et ses valeurs sont celles que tout le marché regarde — ton edge se compare au même RSI
que les autres.

**Où le voir dans ton code.** [features.py](user_data/strategies/arit_lib/features.py) (lignes 100-109, `add_indicators`) :

```python
df[f"ema50{suffix}"] = talib.EMA(close, timeperiod=params.EMA_FAST)
df[f"ema200{suffix}"] = talib.EMA(close, timeperiod=params.EMA_SLOW)
df[f"rsi{suffix}"] = talib.RSI(close, timeperiod=params.RSI_PERIOD)
_macd, _signal, hist = talib.MACD(
    close, fastperiod=params.MACD_FAST, slowperiod=params.MACD_SLOW,
    signalperiod=params.MACD_SIGNAL,
)
df[f"macd_hist{suffix}"] = hist
```

Remarque : les périodes ne sont JAMAIS écrites en dur (`50`, `14`…) — elles viennent de
[params.py](user_data/strategies/arit_lib/params.py) (chapitre 10). Et pour les patterns de
chandeliers, le projet prend TOUTES les fonctions `CDL*` d'un coup
([features.py](user_data/strategies/arit_lib/features.py), lignes 263-264) :

```python
for name in talib.get_function_groups()["Pattern Recognition"]:
    cols[_cdl_col(name)] = getattr(talib, name)(op, hi, lo, cl)
```

~60 détecteurs (engulfing, hammer, doji…) journalisés pour le futur dataset ML — sans en
recoder un seul.

---

## 4. freqtrade — le framework de trading

**À quoi ça sert.** freqtrade est un framework open-source de bot de trading crypto. Il gère
tout ce qui N'EST PAS ta stratégie : connexion à Binance, passage d'ordres, base de données des
trades, backtesting, mode dry-run (simulation en conditions réelles, sans argent). Toi, tu
écris UNE classe Python (la stratégie) et il l'orchestre.

**Pourquoi ici.** Coder soi-même un moteur d'exécution + un backtester fidèle (frais, slippage,
ordre des bougies, stoploss côté exchange), c'est des mois de travail et des bugs qui coûtent de
l'argent réel. freqtrade donne surtout LA garantie clé : **le même code tourne en backtest, en
dry-run et en live**. Ce que tu backtestes est ce qui tradera.

**Où le voir dans ton code.** Toute la stratégie tient dans
[AritV1.py](user_data/strategies/AritV1.py) (248 lignes, volontairement « mince » — chapitre 10).

### Les timeframes multiples (`@informative`)

Le bot décide sur bougies 1h, mais le setup se lit en 4h et le contexte en 1d. freqtrade fusionne
ces horizons via les « informative pairs » ([AritV1.py](user_data/strategies/AritV1.py), lignes 57-62) :

```python
@informative(params.TIMEFRAME_SETUP)          # "4h"
def populate_indicators_4h(self, df, metadata):
    df = features.add_indicators(df)
    df = features.find_pivots(df)
    df = features.track_structure(df)
    return features.candle_patterns(features.sr_levels(df))
```

Le décorateur `@informative("4h")` dit à freqtrade : « calcule ça sur les bougies 4h, puis
fusionne-le dans mon df 1h en suffixant les colonnes `_4h` ». Point crucial : le merge n'expose
que les bougies 4h **clôturées** — à 14h, tu vois la bougie 4h de 08h-12h, jamais celle en cours.
C'est l'anti-look-ahead offert par le framework (interdit n°3 du PDR).

### Les callbacks — qui fait quoi dans AritV1.py

freqtrade appelle TES méthodes à des moments précis du cycle de vie d'un trade :

| Callback | Quand | Ce qu'il fait dans [AritV1.py](user_data/strategies/AritV1.py) |
|---|---|---|
| `populate_indicators` (l. 66) | à chaque nouvelle bougie | appelle `features.compute_all` puis `regimes.classify` puis `cio.conviction` — toute l'analyse |
| `populate_entry_trend` (l. 77) | juste après | pose `enter_long = 1` là où `signal_long & new_4h` — le SIGNAL |
| `confirm_trade_entry` (l. 89) | juste avant d'acheter | dernier filtre : circuit breakers + les 8 gates de `risk.gate_check` — peut dire NON |
| `custom_stake_amount` (l. 109) | pour dimensionner l'ordre | calcule SL initial + taille de position via `risk.compute_stake` (risque en % d'équité) |
| `order_filled` (l. 133) | quand l'ordre est exécuté | fige l'état du trade (SL initial, signal_id, TP2…) en `custom_data` + journalise `entry` |
| `custom_stoploss` (l. 152) | à chaque itération | remonte le SL selon G1/G2/G3 via `gestion.compute_sl` — jamais vers le bas |
| `adjust_trade_position` (l. 172) | à chaque itération | G4 : vend 50 % au premier +1,5R via `gestion.partial_tp` |
| `custom_exit` (l. 187) | à chaque itération | sorties G6 (cassure de structure), G7 (time-stop), TP2 via `gestion.check_exit` |
| `bot_loop_start` (l. 201) | à chaque tour de boucle | touche le heartbeat (pour le watchdog) + snapshot d'équité du jour (CB −6 %) |

Retiens la logique : **populate_* = analyse en masse sur le DataFrame ; les callbacks custom_* =
décisions unitaires pendant la vie d'un trade**.

### `--timeframe-detail 5m` — obligatoire en backtest

En backtest, une bougie 1h est par défaut un bloc opaque : freqtrade ne sait pas si le high
(ton TP) est arrivé avant ou après le low (ton SL) → il choisit une convention, souvent
optimiste. `--timeframe-detail 5m` rejoue chaque bougie 1h en 12 sous-bougies de 5m : l'ordre
réel des touches SL/TP est respecté. Sans ça, tes chiffres de backtest sont des mensonges
polis. D'où la règle du [CLAUDE.md](CLAUDE.md) : backtest TOUJOURS avec `--timeframe-detail 5m`.

### `custom_data` — la mémoire par trade

Un callback ne garde rien en mémoire entre deux appels (et le bot peut redémarrer). freqtrade
offre un stockage clé/valeur PAR TRADE, persistant en base :
([AritV1.py](user_data/strategies/AritV1.py), lignes 216-218)

```python
def _save_state(self, trade, state) -> None:
    for key, value in state.as_dict().items():     # cles 11.3 exclusivement
        trade.set_custom_data(key, value)
```

C'est là que vivent `initial_sl` (l'unité R, immuable), `mae_r`/`mfe_r`, `tp1_done`… — les 12
champs du `TradeState` défini dans [contracts.py](user_data/strategies/arit_lib/contracts.py)
(lignes 45-63). Après un crash, le bot relit ces clés et reprend la gestion exactement où il en était.

---

## 5. pytest — le filet de sécurité

**À quoi ça sert.** pytest exécute des fonctions de test : chacune appelle ton code avec des
entrées connues et vérifie (`assert`) que la sortie est celle attendue. Une commande, un
verdict : `152 passed` ou la liste précise de ce qui est cassé.

**Pourquoi ici.** Un bot de trading a un mode de panne vicieux : il ne plante pas, il trade
FAUX. Un `>` au lieu d'un `>=`, et G1 ne passe jamais à break-even — aucun crash, juste des
pertes. Les **152 tests** du projet encodent le PDR règle par règle : toute modification qui
viole une règle fait rougir un test AVANT de coûter de l'argent. C'est ce qui permet de
modifier le code sans peur.

**Où le voir dans ton code.** D'abord les données : les tests n'utilisent JAMAIS de vraies
bougies Binance (trop lourdes, et surtout non reproductibles). Le générateur
[conftest.py](tests/conftest.py) fabrique des bougies synthétiques **seedées** (lignes 40-46) :

```python
rng = np.random.default_rng(seed)      # seed=42 par defaut
idx = np.arange(n, dtype=float)

if kind == "trend":
    drift = 0.0015 * idx                       # +0,15 %/bougie cumule
    noise = rng.normal(0.0, 0.004, n).cumsum()
    close = base_price * np.exp(drift + noise)
```

`default_rng(seed)` : le « hasard » est initialisé avec une graine fixe → la MÊME série de
bougies à chaque exécution, sur toute machine. Un test qui échoue échoue toujours pareil —
reproductible, donc débogable. Quatre profils (`trend`, `range`, `gaps`, `wicks`) couvrent les
conditions de marché qui stressent chaque module.

Maintenant un test décortiqué, [test_gestion.py](tests/test_gestion.py) (lignes 204-210) :

```python
def test_g7_exactly_24_candles():
    trade = _Trade(open_date_utc=T0)
    dead = TradeState(initial_sl=95.0, mfe_r=0.4)  # jamais +0,5R
    assert gestion.check_exit(trade, _row(date=_hours(23)), dead, tp2=None) is None
    assert gestion.check_exit(trade, _row(date=_hours(24)), dead, tp2=None) == "G7"
    alive = TradeState(initial_sl=95.0, mfe_r=0.6)  # a atteint +0,5R
    assert gestion.check_exit(trade, _row(date=_hours(24)), alive, tp2=None) is None
```

Lecture ligne par ligne :
1. `_Trade(...)` : un FAUX trade (duck-typing : n'importe quel objet avec `open_rate`,
   `open_date_utc`… fait l'affaire) — pas besoin de freqtrade ni d'une base de données.
2. `dead` : un trade mou, qui n'a jamais dépassé +0,4R (`mfe_r=0.4`).
3. À 23 bougies : `check_exit` doit rendre `None` (pas de sortie). Test de la borne basse.
4. À 24 bougies : `"G7"` — le time-stop du PDR 03.4 déclenche EXACTEMENT à 24, pas 25.
5-6. `alive` a atteint +0,6R : G7 l'épargne, même à 24 bougies.

Un seul test verrouille les trois arêtes de la règle : le seuil temporel exact, et la condition
`mfe < 0,5R`. Si quelqu'un change `>=` en `>` dans gestion.py, la ligne 4 casse immédiatement.
Regarde aussi `test_sl_monotone_over_random_sequence` ([test_gestion.py](tests/test_gestion.py),
ligne 135) : 250 bougies aléatoires (mais seedées !) pour prouver l'invariant « le SL ne descend
JAMAIS » — l'interdit n°2 du PDR, testé par la force brute.

Lancer les tests :

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q     # attendu : 152 passed
```

---

## 6. ruff — le linter

**À quoi ça sert.** ruff lit ton code SANS l'exécuter et signale les fautes mécaniques :
variable jamais utilisée, import inutile, variable utilisée avant d'exister, ligne trop longue.
C'est un correcteur orthographique pour Python, quasi instantané (écrit en Rust).

**Pourquoi ici.** La moitié des bugs bêtes sont invisibles à l'œil et fatals au runtime :
`F821` (nom non défini — plantage assuré dans un callback à 3h du matin), `F401` (import mort
qui pollue), `E711` (comparaison à None mal écrite). ruff les attrape en une seconde, AVANT
pytest, AVANT le backtest. C'est le premier gate (G0) de chaque livraison de module.

**Où le voir dans ton code.** La configuration vit dans [pyproject.toml](pyproject.toml) :

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
extend-exclude = ["docs", "ARIT_PDR_v3", "ARIT_claudecode_pack"]

[tool.ruff.lint]
select = ["E", "F", "W"]
```

`E` = erreurs de style (pycodestyle), `F` = fautes logiques (pyflakes : imports/variables
mortes, noms non définis), `W` = warnings. `line-length = 100` : la limite de longueur de ligne
du projet. Lancer : `& C:\Users\jofar\venvs\arit\Scripts\python.exe -m ruff check .`

---

## 7. git + GitHub — l'historique

**À quoi ça sert.** git enregistre des instantanés (« commits ») du projet : tu peux revenir en
arrière, comparer, comprendre POURQUOI chaque ligne existe. GitHub est la copie distante :
sauvegarde hors machine + historique consultable dans le navigateur.

**Pourquoi ici.** Deux raisons propres à ARIT. (1) **Commits atomiques** : un commit = UN
changement cohérent, avec un message qui dit le POURQUOI. L'historique devient le journal de
bord du projet — regarde-le :

```
59c4f58 G6: garde 'vie du trade' — l'evenement ne compte que sur bougie posterieure a l'entree
4d2464f fix G6 evenement (decision Jonas 10/07, spec 03.4 amendee) + mode controle A (09 par.9.1.1)
cf43112 notes: diagnostic G6 (etat 32.5% vs evenement 5.1%) + ablation B-G6 (+0.69%, PF 1.02)
```

Toute la saga G6 (diagnostic → décision → fix → garde) se relit en trois lignes de
`git log --oneline`. (2) **Push après chaque commit** (règle du [CLAUDE.md](CLAUDE.md)) : le
repo vit sur UN laptop ; un disque qui meurt sans push = le travail est perdu. Le push
immédiat, c'est la sauvegarde offsite gratuite.

**Où le voir dans ton code.** Le [.gitignore](.gitignore) dit ce que git NE suit PAS — et
chaque exclusion a une raison :

```
# Secrets
.env

# Runtime / donnees
backtest_lanes/
user_data/macro_state.json
user_data/state/
user_data/data/
user_data/backtest_results/
```

- `.env` : les SECRETS (webhook Discord, clé Finnhub). Un secret commité est un secret public —
  GitHub est scanné en permanence par des bots voleurs de clés. Le modèle sans valeurs, lui,
  est versionné : `.env.example`.
- `user_data/data/` : des Go de bougies **régénérables** (`freqtrade download-data`). git est
  fait pour du texte qui change, pas pour des données binaires lourdes.
- `user_data/state/`, `macro_state.json`, `backtest_lanes/` : des fichiers d'ÉTAT runtime —
  ils changent à chaque exécution et n'appartiennent à aucune « version » du code.

Règle simple : **git versionne le code et les specs ; jamais les secrets, jamais le régénérable,
jamais l'état.**

Commandes utiles pour lire l'histoire :

```powershell
git log --oneline           # la frise chronologique
git log -p user_data/strategies/arit_lib/gestion.py   # tous les changements d'UN fichier
git show 59c4f58            # le detail d'un commit
```

---

## 8. Formats de données — feather, JSON, JSONL, CSV

**À quoi ça sert.** Chaque type de donnée du projet a SON format, choisi pour son usage :
lecture massive, état ponctuel, journal infini, ou série téléchargée.

**Pourquoi ici et où le voir.**

### feather — les bougies (`user_data/data/binance/*.feather`)

```
BTC_USDT-1h.feather   BTC_USDT-4h.feather   BTC_USDT-5m.feather ...
```

feather est un format **binaire en colonnes** (Apache Arrow) : pandas charge un fichier de
centaines de milliers de bougies en quelques dizaines de millisecondes, types préservés
(dates UTC, floats), fichier compact. Un CSV équivalent serait 5-10× plus lent à parser et
plus gros. C'est freqtrade qui choisit ce format — bonne pioche. (parquet, son cousin, ajoute
la compression ; même famille Arrow, même logique colonne.)

### JSON — les états ponctuels (`user_data/macro_state.json`)

Le service macro écrit UN objet lisible qui répond à « quel est l'état macro MAINTENANT ? » :

```json
{"updated_utc": "...", "risk_off": false, "fear_greed": 61, "next_events": [...], "stale": false}
```

Schéma exact construit dans [macro_state.py](services/macro_state.py) (`build_state`, lignes
194-200). Un état = un fichier écrasé à chaque mise à jour, lisible par un humain en cas de
doute. C'est aussi le canal de communication entre processus : le service écrit, le bot lit
(jamais de réseau dans le bot).

### JSONL — le journal append-only (`user_data/logs/decisions/YYYY-MM-DD.jsonl`)

JSONL = « JSON Lines » : **une ligne = un objet JSON = un événement**. Pourquoi pas un gros
JSON ? Parce qu'un journal ne se relit pas, il s'ÉTEND : ajouter une ligne à la fin d'un
fichier est instantané et sans risque, alors que réécrire un tableau JSON entier à chaque
événement finirait par corrompre le fichier au premier crash en pleine écriture. Bonus : un
crash ne coûte au pire que la dernière ligne, et `grep`/pandas lisent le fichier ligne à ligne.
Les 6 types d'événements et leurs champs obligatoires sont contractualisés dans
[contracts.py](user_data/strategies/arit_lib/contracts.py) (lignes 90-113,
`JOURNAL_REQUIRED_FIELDS`) ; l'écriture fail-safe (« le trading ne s'arrête JAMAIS pour un
problème de journal ») vit dans [journal.py](user_data/strategies/arit_lib/journal.py).

### CSV — les séries macro téléchargées (FRED)

[download_macro.py](scripts/download_macro.py) (lignes 38-42) :

```python
def dl_fred(sid: str, name: str) -> None:
    """DXY broad (DTWEXBGS) / taux Fed effectif (DFF) — CSV date,valeur."""
    csv = _get(FRED_CSV.format(sid=sid)).text
    (OUT_DIR / f"{name}.csv").write_text(csv, encoding="utf-8")
```

La Fed (FRED) publie ses séries en CSV `date,valeur` : deux colonnes, quelques milliers de
lignes — le format texte le plus simple du monde suffit largement. On prend le format de la
source telle quelle, sans conversion inutile.

---

## 9. requests / API HTTP

**À quoi ça sert.** `requests` est LA bibliothèque Python pour parler HTTP : `requests.get(url)`
interroge une API, `.json()` décode la réponse. Les APIs web renvoient du JSON ; ton code en
tire des nombres.

**Pourquoi ici.** Règle d'architecture : le BOT ne touche jamais au réseau dans ses callbacks
(interdit docs/11.5 — un appel réseau lent bloquerait la boucle de trading). Ce sont les
**services séparés** qui parlent aux APIs et déposent le résultat dans des fichiers.

**Où le voir dans ton code.** Le fetch du Fear & Greed dans
[macro_state.py](services/macro_state.py) (lignes 153-165) :

```python
def fetch_fear_greed() -> int:
    """alternative.me Fear&Greed (valeur du jour) -> int. Retry x3 backoff, puis leve."""
    for attempt in range(FG_RETRY_MAX):
        try:
            resp = requests.get(FEAR_GREED_URL, timeout=HTTP_TIMEOUT_S)
            resp.raise_for_status()
            return int(resp.json()["data"][0]["value"])
        except Exception as exc:  # reseau, JSON, clef : on retente
            last_exc = exc
            if attempt < FG_RETRY_MAX - 1:
                time.sleep(FG_BACKOFF_BASE_S * (attempt + 1))
```

Les trois réflexes pro à retenir : (1) `timeout=` TOUJOURS — sans lui, un serveur muet gèle ton
process pour toujours ; (2) `raise_for_status()` — une réponse HTTP 500 n'est pas une exception
par défaut, il faut la promouvoir ; (3) retry avec backoff croissant (2 s, 4 s…) — le réseau
échoue par nature, on retente poliment. Et si tout échoue : le `main()` retombe sur l'ANCIEN
fichier d'état plutôt que d'écrire du vide (fail-safe M08).

Un point sécurité au passage ([macro_state.py](services/macro_state.py), lignes 109-114) :
l'URL Finnhub contient `?token=<clé>` — une exception `requests` brute la ferait fuiter dans
les logs. D'où `_scrub_finnhub_error`, qui ne garde que le type d'erreur et le status HTTP.

**Le webhook Discord** — l'inverse : ENVOYER un message, dans
[watchdog.py](services/watchdog.py) (lignes 122-126) :

```python
url = os.environ.get(WEBHOOK_ENV)          # DISCORD_WEBHOOK_URL, via .env
...
requests.post(url, json={"content": line}, timeout=HTTP_TIMEOUT_S)
```

Un webhook est une URL secrète fournie par Discord : POSTer un JSON dessus = un message dans
ton salon. Zéro bot, zéro session — parfait pour des alertes. L'URL vient de l'environnement,
jamais du code (chapitre 7, `.env`).

**La leçon aiodns** ([BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md), note du 2026-07-07) :
`freqtrade download-data` plantait avec `DNSError: Could not contact DNS servers`. Coupable :
`aiodns`, résolveur DNS « rapide » utilisé par aiohttp, qui ne lit pas la config DNS de Windows
sur ta machine. Fix : `pip uninstall aiodns` → aiohttp retombe sur le résolveur système, tout
marche. **Ne jamais réinstaller aiodns dans ce venv.** Morale : quand le réseau échoue en
Python mais marche dans le navigateur, suspecte la couche DNS/résolution de la lib, pas ta box.

---

## 10. Les patterns MAISON du projet

C'est le chapitre le plus important pour LIRE le code : cinq conventions qui structurent tout.

### 10.1 contracts.py + params.py — l'anti « valeur magique »

**L'idée.** Aucun nombre, aucun nom de colonne n'est écrit en dur dans la logique. Les
**valeurs** vivent dans [params.py](user_data/strategies/arit_lib/params.py), chacune avec sa
source PDR en commentaire :

```python
G7_MAX_CANDLES_1H = 24         # PDR 03.4 G7 — time-stop apres 24 bougies 1h
G7_MIN_R = 0.5                 # PDR 03.4 G7 — si jamais atteint +0,5R
```

Les **noms** (colonnes, clés custom_data, fichiers d'état) vivent dans
[contracts.py](user_data/strategies/arit_lib/contracts.py) :

```python
FEATURE_COLUMNS = (
    "ema50_4h", "ema200_4h", ...
    "choch_bear_event_1h",  # 11.3 / 03.4 G6 — EVENEMENT de cassure (decision Jonas 10/07)
    ...
)
```

**Pourquoi.** Un `24` écrit en dur dans gestion.py est intraçable : c'est quoi ? d'où ça vient ?
qui d'autre l'utilise ? `params.G7_MAX_CANDLES_1H` répond aux trois questions d'un coup, et le
changer se fait en UN endroit. Même logique pour les noms : si features.py écrit
`"choch_bear_event_1h"` et que gestion.py lit `"choch_bear_evt_1h"`, rien ne plante — la règle
ne déclenche juste jamais. Le contrat centralisé rend cette faute impossible. Corollaire du
CLAUDE.md : modifier une valeur = modifier `docs/` d'abord (le code SUIT la spec).

### 10.2 Modules PURS, zéro import croisé

**L'idée.** Chaque module d'[arit_lib](user_data/strategies/arit_lib/) est une boîte à
fonctions **pures** : données en entrée → valeurs en sortie, aucun réseau, aucun import
freqtrade, et surtout **aucun import d'un autre module métier** (features n'importe jamais
regimes, etc.) — seuls `contracts` et `params` sont permis. Tout transite par la stratégie :

```python
# AritV1.py, populate_indicators — la strategie est le SEUL endroit qui chaine les modules
df = features.compute_all(df)
df = cio.conviction(regimes.classify(df, macro if live else None))
```

**Pourquoi.** (1) **Testabilité** : une fonction pure se teste avec un DataFrame synthétique et
un faux Trade de 5 lignes — regarde `_Trade` dans [test_gestion.py](tests/test_gestion.py)
(ligne 14) : pas besoin de lancer freqtrade pour tester G1-G7. (2) **Isolation** : casser
features.py ne peut pas casser gestion.py — le graphe de dépendances est plat, chaque module se
comprend seul. C'est la traduction des « 10 agents spécialisés » de la vision ARIT en modules
déterministes (voir [guide.md](guide.md) §5).

### 10.3 La stratégie « mince »

**L'idée.** [AritV1.py](user_data/strategies/AritV1.py) < 250 lignes, ZÉRO logique métier :
chaque callback se contente de récupérer la bougie, d'appeler arit_lib, de sauver l'état et de
journaliser. Exemple type (lignes 187-199, `custom_exit`) : 12 lignes, et la seule ligne
« intelligente » est `gestion.check_exit(trade, row, state, tp2)`.

**Pourquoi.** La frontière avec freqtrade est le SEUL endroit qu'on ne peut pas tester
unitairement (le framework appelle ces méthodes, pas toi). Donc on y met le moins de cerveau
possible : tout ce qui peut se tromper vit dans arit_lib, où les 152 tests montent la garde.
Bonus : le décorateur `_safe` (lignes 29-39) enveloppe chaque callback — une exception devient
une ligne de journal `system` + l'action la plus sûre (refuser l'entrée, ne pas bouger le SL),
jamais un crash du bot.

### 10.4 Point-in-time / anti-look-ahead

**L'idée.** À la bougie t, le code n'a le droit d'utiliser QUE ce qui était connu à t. Un
backtest qui triche (même involontairement) avec le futur donne des résultats mirifiques…
et invérifiables en live. Deux exemples concrets :

**Le shift(2) des pivots** ([features.py](user_data/strategies/arit_lib/features.py),
lignes 126-131) :

```python
for k in range(1, n + 1):
    ph = ph & (high > high.shift(k)) & (high > high.shift(-k))
    ...
df[f"pivot_high{suffix}"] = ph                              # BRUT : repeint, JAMAIS decisionnel
df[f"pivot_high_conf{suffix}"] = ph.shift(n, fill_value=False)  # confirme n=2 bougies apres
```

Un pivot fractal N=2 est « le high plus haut que ses 2 voisins de CHAQUE côté » — donc il faut
attendre 2 bougies APRÈS pour le savoir (`shift(-k)` regarde le futur). Le pivot brut
« repeint » : sa valeur au temps t change quand le futur arrive. La colonne `_conf`, décalée de
2 bougies (`shift(n)`), ne devient vraie qu'au moment où l'information existait réellement.
Règle du projet : le brut ne sert JAMAIS à décider, seul le confirmé compte.

**Le +1 jour macro** : les séries macro (DXY, taux) sont datées du jour J mais publiées
APRÈS la clôture — les utiliser le jour J en backtest = lire le journal de demain. La spec
macro V1.1 impose le décalage d'un jour : la valeur du jour J n'est utilisable qu'à partir de
J+1. Même famille : le merge 4h→1h de freqtrade (chapitre 4) et le garde `shift(1)` de
l'événement G6 ([features.py](user_data/strategies/arit_lib/features.py), ligne 85 :
`choch_state & ~choch_state.shift(1)` — le passé seul, aucun look-ahead).

### 10.5 Les fichiers d'état + la leçon de contamination

**L'idée.** Les circuit breakers persistent sur disque (`user_data/state/cb_day.json`,
`day_equity.json`, `manual_restart_required` — chemins contractuels dans
[contracts.py](user_data/strategies/arit_lib/contracts.py), lignes 76-84) pour survivre à un
redémarrage du bot. Indispensable en live… et piégeux en backtest.

**La leçon** ([BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md), note du 2026-07-11,
PIÈGE MAJEUR) : chaque backtest HÉRITE de l'état laissé par le précédent. Un
`manual_restart_required` posé par un run a bloqué les entrées de tous les suivants — le run B
est passé de 263 à 19 trades, silencieusement. Et deux runs parallèles sur le même `user_data`
s'écrasent mutuellement l'état → résultats invalides. Règles depuis : purger
`state/*.json + manual_restart_required + veto/*` avant CHAQUE run ; jamais deux backtests sur
le même user_data.

**Les lanes `backtest_lanes/`** : la solution pour paralléliser. Chaque run reçoit son
`backtest_lanes/runN/` — un user_data ISOLÉ (state, logs, veto locaux) avec des junctions NTFS
(des raccourcis de dossiers Windows) vers les données et les stratégies partagées, lancé via
`--userdir <lane>`. Jetable, hors git ([.gitignore](.gitignore) : `backtest_lanes/`). Morale
générale, au-delà du trading : **quand un programme garde de l'état sur disque, deux exécutions
ne sont plus indépendantes — isole ou purge.**

---

## 11. Glossaire

| Terme | En une phrase |
|---|---|
| **OHLCV** | Les 5 chiffres d'une bougie : Open, High, Low, Close, Volume. |
| **Timeframe** | La durée d'une bougie (5m, 1h, 4h, 1d) ; ARIT décide en 1h, lit le setup en 4h. |
| **Backtest** | Rejouer la stratégie sur l'historique pour mesurer ce qu'elle AURAIT fait. |
| **Dry-run** | Le bot tourne en conditions réelles (prix live) mais avec de l'argent simulé. |
| **Edge** | L'avantage statistique d'une stratégie — ce qui fait qu'elle gagne PLUS que le hasard, frais déduits. |
| **PF (profit factor)** | Gains bruts ÷ pertes brutes ; > 1 = gagnant, le gate du protocole exige ≥ 1,3. |
| **Drawdown (DD)** | La pire baisse de l'équité depuis son sommet, en % — la mesure de la douleur. |
| **Expectancy** | Gain moyen par trade (en R ou en %) ; positif = chaque trade « vaut » de l'argent en moyenne. |
| **R (multiple de R)** | L'unité de risque : la distance entrée → SL initial ; +2R = gagné 2× le risque initial. |
| **MAE / MFE** | Pire excursion (Adverse) et meilleure (Favorable) d'un trade pendant sa vie, en R. |
| **Slippage** | L'écart entre le prix demandé et le prix réellement exécuté (0,05-0,10 % dans params.py). |
| **Spread** | L'écart instantané entre meilleur prix acheteur et vendeur. |
| **Pivot (fractal)** | Un high/low plus extrême que ses N voisins de chaque côté — confirmé N bougies après. |
| **HH / HL** | Higher High / Higher Low : des sommets et creux ascendants = structure haussière intacte. |
| **BOS** | Break Of Structure : clôture au-dessus du dernier pivot high — la tendance continue. |
| **CHoCH** | Change of Character : clôture sous le dernier HL — premier signe de retournement (sortie G6). |
| **ATR** | Average True Range : l'amplitude moyenne des bougies — l'unité de « volatilité » des SL et buffers. |
| **ADX** | Indicateur de FORCE de tendance (pas de direction) ; < 20 = RANGE, ≥ 25 = TREND. |
| **SL / TP** | Stop-Loss (sortie de protection) / Take-Profit (sortie de gain) ; le SL d'ARIT ne s'élargit jamais. |
| **Break-even (BE)** | Remonter le SL au prix d'entrée : le trade ne peut plus perdre (règle G1). |
| **Trailing stop** | SL qui suit le prix à distance (G3 : close − 2×ATR) — verrouille le gain en tendance. |
| **Régime** | L'état du marché classé par M02 : TREND, TRANSITION, RANGE ou RISK_OFF. |
| **Conviction** | Le score final [0,1] du CIO : somme pondérée des 5 scores × multiplicateur macro. |
| **Circuit breaker** | Coupe-circuit : −6 % d'équité en un jour ou 2 pertes ≤ −0,8R d'affilée → stop/réduction des entrées. |
| **Funding rate** | Le loyer périodique des contrats perpétuels ; très positif = foule acheteuse à contre-signal (macro V1.1). |
| **Look-ahead** | Le péché capital du backtest : utiliser une info du futur — interdit n°3, voir chapitre 10.4. |

---

## 12. Comment ce projet a été construit

**À quoi ça sert.** Ce chapitre raconte la FABRICATION : la méthode suivie, ce qui a été
emprunté à l'open source (et pourquoi), ce qui a été écrit de zéro, et les leçons qui valent
pour tous tes futurs projets. C'est le making-of, pas le mode d'emploi.

### 12.1 La démarche — spec d'abord, code ensuite

Le pipeline de build, dans l'ordre, sans jamais sauter d'étape :

1. **La spec contractuelle** (`docs/`, 22 fichiers) : le PDR v3 décrit CHAQUE règle avant la
   moindre ligne de code — jusqu'aux 7 interdits absolus de [docs/README.md](docs/README.md)
   (pas de LLM runtime, SL jamais élargi, zéro look-ahead…). Le code SUIT la spec ; quand un
   backtest révèle qu'une règle est mauvaise (la saga G6, chapitre 7), on amende `docs/`
   D'ABORD, puis le code.
2. **Les contrats** : [params.py](user_data/strategies/arit_lib/params.py) et
   [contracts.py](user_data/strategies/arit_lib/contracts.py) écrits AVANT les modules —
   chaque constante cite sa source PDR, chaque nom de colonne est fixé une fois pour toutes.
   Deux modules codés par deux personnes (ou deux agents) différents s'emboîtent parce qu'ils
   lisent le même contrat.
3. **Les modules purs, codés en parallèle par agents** : chaque module (M01-M10) a été écrit
   par un sous-agent `arit-coder` de Claude Code, avec la spec `docs/modules/MXX.md` en entrée
   et ses tests pytest en sortie. La pureté (chapitre 10.2) n'est pas que de l'élégance : c'est
   ce qui a PERMIS le parallélisme — zéro import croisé = zéro conflit entre agents.
4. **La review systématique** : chaque module passe devant un `arit-reviewer` (lecture seule)
   qui vérifie les invariants PDR. Ça a payé : le premier passage a retoqué 3 modules sur 5 —
   dont G4 qui vendait « 50 % du stake d'entrée » au lieu de « 50 % de la quantité »
   ([BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md), notes du 2026-07-06). Un bug de
   sens, invisible à l'exécution, attrapé par relecture contre la spec.
5. **Les gates** : G0 = ruff propre, G1 = pytest vert (152 tests), G2 = backtest smoke sans
   exception. Aucun module ne « compte » avant d'avoir passé les trois.
6. **Les backtests en lanes isolées** (`backtest_lanes/run1..N`) : le protocole A/B a tourné
   en parallèle, chaque run dans son user_data isolé — après la leçon de contamination
   (12.4). Les résultats et le verdict : [RAPPORT_PROTOCOLE_AB.md](for%20claude%20build/RAPPORT_PROTOCOLE_AB.md).

### 12.2 Ce qui vient de l'open source — et pourquoi

La règle d'arbitrage : **on n'écrit soi-même que ce qui porte l'edge**. Tout le reste existe
déjà, mieux testé que ce qu'on ferait.

| Brique | Rôle ici | Pourquoi emprunter plutôt qu'écrire |
|---|---|---|
| **freqtrade** | moteur d'exécution + backtester + dry-run | des années de code éprouvé sur les ordres, les frais, la DB des trades ; le même code backtest/live est inreproduisible en solo (chapitre 4) |
| **TA-Lib** | EMA, RSI, ATR, ADX, ~60 patterns CDL | 20 ans de tests ; un RSI recodé à la main avec un bug de lissage fausserait tout en silence (chapitre 3) |
| **pandas / numpy** | le DataFrame de bougies, le calcul vectorisé en C | la performance (70 000 bougies) et l'écosystème entier repose dessus (chapitre 2) |
| **pytest / ruff** | tests + linter | l'outillage standard de tout projet Python sérieux (chapitres 5-6) |
| **requests / ccxt** | HTTP vers les APIs ; ccxt dans [watchdog.py](services/watchdog.py) pour parler à Binance sans freqtrade | protocoles réseau = terrain miné, jamais réinventé |
| **FinBERT / FOMC-RoBERTa** (backlog V2) | modèles NLP pré-entraînés pour lire le ton des news macro | [docs/10_backlog_v2.md](docs/10_backlog_v2.md) point 5 : entraîner un modèle de langage financier soi-même coûterait des mois et des GPU — on prendra `ProsusAI/finbert` et `gtfintechlab/FOMC-RoBERTa` sur Hugging Face, déjà entraînés sur des corpus financiers |

### 12.3 Ce qui a été créé de zéro — module par module

Tout ce qui porte l'edge ou la sécurité d'ARIT est du code maison. Pour chacun : le problème,
l'approche, la taille.

- **[features.py](user_data/strategies/arit_lib/features.py) (M01, ~370 lignes)** — problème :
  transformer des bougies brutes en « lecture » du marché (pivots, structure HH/HL, BOS/CHoCH,
  S/R, 5 scores). Approche : 100 % vectorisé pandas/numpy sauf le clustering S/R (boucle
  assumée), anti-repaint par `shift` de confirmation, scores en `np.select` table-driven.
  Le module le plus dense du projet — c'est lui, les « yeux » du bot.
- **[regimes.py](user_data/strategies/arit_lib/regimes.py) (M02, ~80 lignes)** — problème :
  classer chaque bougie en TREND / TRANSITION / RANGE / RISK_OFF et en déduire seuil +
  multiplicateur. Approche : arbre de conditions ADX/EMA/F&G, court exprès — un classifieur
  qu'on ne comprend pas d'un coup d'œil est un classifieur qu'on ne peut pas auditer.
- **[cio.py](user_data/strategies/arit_lib/cio.py) (M03, ~90 lignes)** — problème : fusionner
  les 5 scores en UNE conviction [0,1] et décider du signal. Approche : somme pondérée figée
  (poids jamais hyperoptés) + `explain()` qui reconstruit chaque décision en dict JSON pour le
  journal — la traçabilité est une feature, pas un bonus.
- **[risk.py](user_data/strategies/arit_lib/risk.py) (M04, ~380 lignes)** — problème : ne
  JAMAIS laisser passer une entrée dangereuse. Approche : les 8 gates dans l'ordre contractuel
  (`GATE_NAMES` de contracts.py), sizing en % d'équité, circuit breakers persistés sur disque.
  Le plus gros module avec journal — normal : la sécurité est verbeuse.
- **[gestion.py](user_data/strategies/arit_lib/gestion.py) (M05, ~200 lignes)** — problème :
  gérer un trade ouvert (G1-G7 : break-even, trailing, TP partiel, sortie structure,
  time-stop). Approche : fonctions pures sur (trade, bougie, état) avec flags d'ablation pour
  tester chaque règle isolément — c'est ce qui a permis le diagnostic « B moins G6 ».
- **[journal.py](user_data/strategies/arit_lib/journal.py) (M06, ~375 lignes)** — problème :
  rendre CHAQUE décision auditable sans jamais gêner le trading. Approche : JSONL append-only,
  écriture fail-safe (retry puis log, jamais d'exception), schéma versionné.
- **[AritV1.py](user_data/strategies/AritV1.py) (M07, 248 lignes)** — problème : brancher tout
  ça sur freqtrade sans y mettre de cerveau. Approche : la stratégie « mince » (chapitre 10.3),
  décorateur `_safe` sur chaque callback.
- **Les services (M08-M10, ~840 lignes)** — [macro_state.py](services/macro_state.py) (fetch
  F&G + calendrier → JSON atomique), [discord_bot.py](services/discord_bot.py) (digest + véto
  humain par réaction ❌), [watchdog.py](services/watchdog.py) (heartbeat + alerte + flatten).
  Trois process indépendants : si l'un meurt, les autres vivent.
- **Les utilitaires** — [start_arit.py](start_arit.py) (60 lignes : lance les 4 process,
  zéro logique), [download_macro.py](scripts/download_macro.py) (105 lignes : les 5 séries
  macro V1.1 depuis FRED/DefiLlama/Binance/alternative.me),
  [macro_regime.py](user_data/strategies/arit_lib/macro_regime.py) (chantier V1.1 en cours :
  scores macro discrets → PORTEUR/NEUTRE/HOSTILE).

Total maison : ~2 500 lignes de code métier… protégées par ~2 200 lignes de tests. Ce ratio
proche de 1:1 n'est pas du zèle — c'est le prix normal d'un code qui manipule de l'argent.

### 12.4 Les leçons de fabrication les plus formatrices

**1. L'état sur disque contamine tout ce qui le partage.** Un flag `manual_restart_required`
laissé par un backtest a silencieusement étranglé tous les suivants (263 → 19 trades), et des
runs parallèles s'écrasaient mutuellement — des JOURS de résultats invalidés d'un coup
([BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md), 2026-07-11). Leçon générale : dès
qu'un programme écrit un fichier d'état, deux exécutions ne sont plus indépendantes. Purge ou
isole (les lanes), et vérifie l'isolation par un smoke test — ne la suppose jamais.

**2. Le look-ahead ne prévient pas.** Un backtest qui triche avec le futur ne plante pas : il
affiche de beaux chiffres, faux. D'où la discipline systématique : pivots confirmés à
`shift(2)`, merge 4h clôturé, macro décalée à J+1, événement G6 dérivé du passé seul
(chapitre 10.4). Leçon : les bugs les plus chers sont ceux qui produisent un résultat
plausible.

**3. La spec d'abord, même quand elle a tort.** G6 codé CONFORME à la spec tuait 402 trades
sur 463 à la bougie d'entrée. La réponse n'a pas été « patcher le code en douce » mais :
mesurer (état vrai 32,5 % des bougies vs événement 5,1 %), faire trancher Jonas, amender
`docs/03`, PUIS coder ([BUILD_NOTES.md](for%20claude%20build/BUILD_NOTES.md), 2026-07-10).
Leçon : quand code et spec divergent, celui qui décide c'est le doc — sinon plus personne ne
sait ce que le système est CENSÉ faire.

**4. Des tests seedés ou pas de tests.** Les 152 tests tournent sur des bougies synthétiques
à graine fixe ([conftest.py](tests/conftest.py), `default_rng(seed)`) : même « hasard » à
chaque run, sur toute machine. Un test aléatoire qui échoue une fois sur dix n'apprend rien ;
un test reproductible qui échoue est une flèche pointée sur le bug. Leçon : la reproductibilité
n'est pas un confort, c'est la condition pour que l'échec d'un test soit une INFORMATION.

---

*Guide généré le 2026-07-12. Les numéros de ligne peuvent glisser au fil des commits ;
les noms de fonctions et de constantes, eux, sont contractuels et stables.*
