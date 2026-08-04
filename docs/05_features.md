# 05 — Features techniques (formules exactes, zéro interprétation)

Tout est calculé dans `populate_indicators` (pandas). Colonnes 4h/1d mergées via `merge_informative_pair` (clôtures uniquement — jamais de look-ahead). Librairies : TA-Lib (livré avec freqtrade) + pandas.

## 5.1 Pivots & structure (4h — le setup)
- **Pivot high (fractal)** : high[i] > high[i−1], high[i−2], high[i+1], high[i+2] (N=2). Confirmé seulement 2 bougies après (pas de repaint). Pivot low symétrique.
- Suivi des swings : séquence de pivots → étiquettes HH/HL/LH/LL.
- **BOS haussier** : close_4h > dernier pivot high confirmé ET corps de la bougie de cassure ≥ **1,0 × ATR(14)_4h** (displacement). Fraîcheur : un BOS est "frais" pendant 3 bougies 4h.
- **CHoCH baissier 4h** : close_4h < dernier HL confirmé. (Équivalent 1h utilisé par G6.)
- **s_structure** : 1,0 si BOS frais ET contexte TREND · 0,7 si séquence HH/HL intacte sans BOS frais (continuation) · 0,3 si structure neutre · 0 si dernier événement = CHoCH baissier.

## 5.2 Support/Résistance (4h)
- Niveaux = clusters de pivots (highs pour résistances, lows pour supports) : deux pivots appartiennent au même niveau si écart ≤ **0,5 × ATR(14)_4h**. Prix du niveau = moyenne du cluster. Touches = nb de pivots du cluster. Force = min(touches/4, 1).
- Résistance pertinente = plus proche niveau au-dessus du prix ; support = plus proche en dessous.
- **RR_dispo = (résistance − entrée) / (entrée − SL_initial)**.
- **s_sr** : 1,0 si RR_dispo ≥ 2,0 · 0,7 si 1,5 ≤ RR_dispo < 2,0 · 0 si < 1,5 (le gate coupe de toute façon).

## 5.3 Indicateurs
ADX(14)_4h · EMA(50)_4h, EMA(200)_4h, EMA(50)_1d · RSI(14)_4h · MACD(12,26,9)_4h (histogramme) · ATR(14)_4h et ATR(14)_1h · SMA20 du volume_4h. Bollinger(20,2)_1h calculées et journalisées (pas utilisées en entrée V1).
- **s_momentum** : 1,0 si RSI_4h ∈ [50, 70] ET histogramme MACD_4h > 0 et croissant · 0,5 si RSI ∈ [45,50) ou (70,75] avec MACD > 0 · 0 sinon (on n'achète pas la sur-extension > 75).

## 5.4 Patterns chandeliers (4h, TA-Lib)
- Entrée V1 (3 patterns bullish) : `CDLENGULFING == 100` · `CDLHAMMER == 100` · pin bar bullish custom (mèche basse ≥ 2× corps ET clôture dans le tiers haut).
- Filtre : `CDLDOJI == 100` sur la bougie de cassure → s_patterns = 0 (indécision sur le breakout).
- **s_patterns** : 1,0 si pattern bullish sur la bougie de cassure ou la suivante · 0,5 si dans les 3 dernières bougies 4h · 0,3 sinon (absence n'est pas disqualifiante) · 0 si doji sur cassure.
- **Idée 9 (journalisation large)** : TOUTES les fonctions TA-Lib `CDL*` (~60) sont calculées et écrites dans le journal comme features — non utilisées en décision V1, elles constituent le dataset d'apprentissage FreqAI V2 qui déterminera lesquelles comptent.

## 5.5 Volume (4h)
- **s_volume** : 1,0 si volume bougie de cassure ≥ 1,5 × SMA20(volume) · 0,5 si ≥ 1,0× · 0 sinon.
- Note : spot crypto = vrai volume exchange (fiable). Ne s'applique pas tel quel au forex (V2 IBKR).

## 5.6 Tests unitaires exigés (pytest, données synthétiques)
Pivots (confirmation à +2, pas de repaint) · BOS avec/sans displacement · CHoCH · clustering S/R (écarts autour de 0,5×ATR) · RR_dispo · chaque s_* sur cas construits · absence de look-ahead (une feature 4h ne change pas avant la clôture 4h).

## 5.6 AMENDEMENT du 2026-08-04 — jeu de features BAISSIER (décision A2)

Le short (03.7) a besoin de sa propre lecture technique. Règle qui a guidé tout ce bloc :
**le miroir n'introduit aucun degré de liberté nouveau** — mêmes seuils, mêmes barèmes,
seule la polarité des prédicats change. Le budget de tests est déjà dépassé (`CHANTIERS.md`
B2) ; un short avec ses propres paramètres serait un second modèle à valider, pas une
symétrie.

### Structure (05.1 miroir)
| Haussier | Baissier | Construction |
|---|---|---|
| `last_hl` | `last_lh` | dernier pivot high CONFIRMÉ plus bas que le précédent |
| `last_ph` | `last_pl` | dernier pivot low confirmé |
| `hh_hl_intact` | `ll_lh_intact` | séquence LL **et** LH établie |
| `bos_bull` | `bos_bear` | clôture sous le dernier PL + **même** exigence de displacement (≥ 1 × ATR) |
| `bos_fresh` | `bos_fresh_bear` | même fenêtre de fraîcheur (3 bougies 4h) |
| `choch_bear` | `choch_bull` | clôture au-dessus du dernier LH |
| `choch_bear_event_1h` | `choch_bull_event_1h` | front montant de l'état (G6, décision 10/07) |

Même anti-repaint : tout part des pivots confirmés à `shift(PIVOT_N)`. Prouvé
mécaniquement par `test_colonnes_baissieres_ne_repeignent_pas` (recalcul sur données
tronquées ⇒ préfixes identiques), pas seulement par relecture.

### Scores (05.2 à 05.5 miroirs) — `s_*_short`
- **`s_structure_short`** : contexte de tendance inversé (`EMA50 < EMA200` **et**
  `close < EMA50`), BOS baissier, CHoCH haussier comme événement adverse.
- **`s_momentum_short`** : bandes RSI par symétrie autour de 50 — plein sur **[30, 50]**
  (miroir de [50, 70]), 0,5 sur **(50, 55]** ou **[25, 30)**. Histogramme MACD **négatif** et
  qui s'amplifie. L'asymétrie du PDR est conservée : le score plein exige l'amplification,
  le 0,5 non.
- **`s_sr_short`** : `rr_dispo_short = (close − nearest_sup_4h) / (SL_est − close)` avec
  `SL_est = last_lh_4h + 0,1 × ATR_4h` (fallback `close + 1,5 × ATR_4h`). Mêmes paliers.
- **`s_patterns_short`** : patterns talib lus à **−100** — `CDLENGULFING` (engulfing
  baissier) et `CDLSHOOTINGSTAR`. ⚠️ `CDLHAMMER` n'a pas de sortie −100 dans talib (il n'est
  défini que haussier) : son miroir structurel est la shooting star. Pin bar bearish custom
  (`cdl_pinbar_bear`) : mèche **haute** ≥ 2 × corps et clôture dans le tiers **bas**. Le doji
  reste lu à +100 — c'est une indécision, elle disqualifie une cassure dans les deux sens.
- **`s_volume_short` = `s_volume`**, **volontairement non dupliqué** : un volume fort
  confirme un mouvement, il ne dit pas dans quelle direction. Le dupliquer par symétrie de
  façade aurait donné l'illusion d'un cinquième signal baissier indépendant.
