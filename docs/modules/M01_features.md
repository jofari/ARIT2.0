# M01 — `arit_lib/features.py` (les yeux du bot)

**Lien à l'edge** : produit le setup (BOS 4h) et les niveaux (HL, S/R) sur lesquels TOUTE la gestion s'appuie. Un pivot qui repaint = un trailing faux = l'edge détruit. La priorité absolue de ce module : **zéro look-ahead, zéro repaint**.

**Libs** : `pandas`, `numpy`, `talib` (ADX, RSI, MACD, ATR, EMA, SMA, fonctions CDL*). Fonctions **pures** : DataFrame in → DataFrame out, aucun I/O, aucun import freqtrade.

## Architecture interne (signatures)
```python
def compute_all(df: DataFrame) -> DataFrame                 # orchestre tout, ordre fixe ci-dessous
def add_indicators(df, suffix="") -> DataFrame              # EMA/RSI/MACD/ATR/ADX/vol_sma
def find_pivots(df, n=2, suffix="") -> DataFrame            # *_conf SEULEMENT (confirmés à +2 ; bruts locaux, A2 03/08)
def track_structure(df) -> DataFrame                        # last_ph, last_hl, HH/HL, bos_bull, bos_fresh, choch_bear
def sr_levels(df, window=180, tol_atr=0.5) -> DataFrame     # nearest_res/sup, res_touches (sur 4h)
def rr_available(df) -> DataFrame                           # rr_dispo (05.2)
def candle_patterns(df) -> DataFrame                        # engulfing/hammer/pinbar/doji + cdl_* (~60)
def module_scores(df) -> DataFrame                          # s_structure, s_momentum, s_sr, s_patterns, s_volume
```

## Stratégies précises (algorithmes)
- **Pivots sans repaint** : `ph_raw[i] = high[i] > high[i±1..2]` (vectorisé par shifts). La valeur UTILISABLE au temps t est `pivot_high_conf = ph_raw.shift(2)` (connue 2 bougies après) puis `last_ph = prix_du_pivot ffill()`. Interdit d'utiliser `ph_raw` non shifté dans quoi que ce soit de décisionnel.
- **Structure** : machine à états sur la séquence des pivots confirmés → étiquette du dernier swing (HH/HL/LH/LL). `bos_bull = (close > last_ph) & (body >= 1.0*atr_4h)` ; `bos_fresh = bos_bull.rolling(3).max()` ; `choch_bear = close < last_hl`. Idem en 1h pour `choch_bear_1h` et `last_hl_1h` (G2/G6).
- **S/R par clustering** : sur les `window=180` dernières bougies 4h, prendre les prix des pivots confirmés ; tri croissant ; regrouper tant que l'écart au centre du cluster ≤ `0.5*atr_4h` courant ; niveau = moyenne du cluster, touches = taille. `nearest_res` = plus petit niveau > close. Boucle Python acceptée (df 4h court, recalcul 1×/bougie 4h en live).
- **Scores discrets** : implémentation table-driven — chaque `s_*` est un `np.select(conditions, [1.0, 0.7, 0.5, 0.3, 0.0])` dont les conditions citent le PDR 05 en commentaire. Aucune valeur continue : les scores sont dans {0, 0.3, 0.5, 0.7, 1.0}, point.

## Règles & invariants
1. Toute colonne 4h consommée en 1h passe par le merge freqtrade (jamais de resample maison).
2. `compute_all` est idempotente : deux appels sur le même df → mêmes colonnes, mêmes valeurs.
3. NaN de warm-up (EMA200 → 200 bougies) : les scores valent 0 tant que les inputs sont NaN — jamais de fillna créatif.
4. Test anti-look-ahead obligatoire : pour tout t, `compute_all(df[:t])` == valeurs à t de `compute_all(df)` (test pytest sur données synthétiques).

**Tests pytest** : pivot confirmé exactement à +2 · BOS refusé si corps < 1×ATR · CHoCH correct · clustering avec écarts limites (0.49 vs 0.51 ATR) · rr_dispo · chaque s_* sur cas construits · idempotence · anti-look-ahead.
