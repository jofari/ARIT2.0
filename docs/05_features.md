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
