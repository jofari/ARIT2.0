# 03 — Risque & gestion de position (LE cœur d'ARIT)

## 3.1 Sizing (custom_stake_amount)
- Conviction `c ∈ [seuil, 1]` (sortie du CIO, voir 04). Normalisation : `n = (c − seuil) / (1 − seuil)` ∈ [0,1].
- **Risque % = 1 % + n × (cap − 1 %)** avec **cap = 2 %** pour les trades n°1 à 100 (compteur global persistant), **cap = 3 %** ensuite.
- **Stake (USDT) = équité_courante × risque% ÷ distance_stop_fraction**, où `distance_stop_fraction = (prix_entrée − SL_initial) / prix_entrée`. Équité courante = wallet total dry-run/réel (compounding).
- Arrondis : quantité arrondie à la précision de la paire (freqtrade gère) ; si stake < min-notional Binance OU si le respect du min-notional forcerait risque > cap → **skip** (journalisé `skip_min_notional`).

## 3.2 Garde-fous d'entrée (confirm_trade_entry, ordre d'évaluation)
1. Régime ≠ RANGE et ≠ RISK_OFF (04).
2. Fenêtre news : aucun event high-impact à ±30 min (06). Fail-safe : calendrier indisponible > 2 h → bloquer.
3. Liquidité : spread instantané ≤ 0,05 % sinon skip.
4. **Slots** : positions ouvertes < 3. On ne clôture JAMAIS un trade pour en ouvrir un autre.
5. **Risque résiduel total** : Σ résiduels positions ouvertes + risque du nouveau ≤ **6 %**.
   `résiduel(pos) = quantité × max(0, prix_entrée − SL_courant) / équité` (position à BE ou mieux → 0 ; le paramètre 6 % est un config modifiable plus tard).
6. **Budget hebdomadaire** (semaine ISO, reset lundi 00:00 UTC) : Σ des risques initiaux engagés cette semaine + nouveau ≤ **8 %** ET nombre d'entrées cette semaine < **10**.
7. RR ≥ 1,5 (05 — vérifié aussi au signal).
8. Phase canari uniquement : fenêtre de véto Discord (08).
Chaque check échoué → skip + ligne de journal avec le nom exact du gate.

## 3.3 Stop initial et TP initial
- **SL initial** = sous le dernier HL 4h confirmé − 0,1 × ATR(14)_4h ; fallback si pas de HL exploitable : prix_entrée − 1,5 × ATR(14)_4h.
- **TP1 = +1,5R** (fixe). **TP2 initial** = résistance 4h la plus proche (si > TP1, sinon pas de TP2 — tout sort à TP1... non : voir G4/G5, 50 % sortent à TP1, le reste court).
- **Amendement 2026-07-09 (décision Jonas)** : le niveau TP2 de SORTIE est **recalculé à chaque
  clôture 1h** (résistance 4h courante), il n'est PAS figé à l'entrée. Le `tp2` d'entrée reste
  journalisé (`ev_entry`) et stocké en custom_data à titre d'AUDIT. L'optimisation ML du TP
  (modèle MAE/MFE) reste en V2 (docs/10 point 3). ⚠️ Choix fait en connaissance : la review du
  build avait signalé la dérive du niveau de sortie comme risque (le TP peut s'éloigner ou se
  rapprocher avec le marché).
- **Gate RR** : distance à la première résistance 4h ≥ 1,5 × distance de stop, sinon pas de trade.

## 3.4 Les règles de gestion G1-G7 (défauts FIGÉS — jamais hyperoptés — chacune avec flag on/off pour ablation)
Évaluées à chaque clôture 1h sur chaque position ouverte (callbacks freqtrade ; en backtest : bougies 1h + detail 5m).
| # | Règle | Spécification exacte |
|---|---|---|
| G1 | Break-even | Si profit courant ≥ **+1,0R** → SL = prix_entrée × (1 + 0,001) (buffer frais 0,1 %). |
| G2 | Trailing structurel | À chaque nouveau **HL 1h confirmé** (pivot fractal N=2) strictement au-dessus du SL courant → SL = HL − 0,1 × ATR(14)_1h. |
| G3 | Trailing ATR (fallback) | Actif seulement après +1R : SL = max(SL_courant, close_1h − **2,0 × ATR(14)_1h**). En régime RISK_OFF : 1,5 × ATR. |
| G4 | TP partiel | Au premier touch de **+1,5R** → vendre **50 %** de la quantité (adjust_trade_position). Une seule fois par trade. |
| G5 | Extension | Après G4, si **nouveau BOS 4h haussier confirmé** → supprimer TP2 : le reste court sous trailing (G2/G3) uniquement. |
| G6 | Exit structure adverse | **ÉVÉNEMENT de CHoCH 1h en clôture** : la bougie 1h qui CASSE le dernier HL 1h pivot (close passe au-dessus → en-dessous) pendant la vie du trade → sortie market immédiate du reste. *Amendement 2026-07-10 (décision Jonas)* : la définition originale « close 1h < dernier HL » était un ÉTAT, vrai 32,5 % des bougies (mesuré BTC 2017-2026) → tuait 87 % des trades à l'entrée ; l'événement de cassure = 5,1 % des bougies. |
| G7 | Time-stop | Si après **24 bougies 1h** le trade n'a jamais atteint +0,5R → sortie market (trade mort). |
Invariant absolu (natif freqtrade, ne pas contourner) : **le SL ne descend jamais**.

## 3.5 Circuit breakers
- **CB jour** : équité ≤ −6 % vs 00:00 UTC → plus aucune entrée jusqu'à 00:00 UTC suivant (gestion des positions ouvertes continue). 2 CB dans la même semaine ISO → arrêt des entrées jusqu'à redémarrage manuel (commande).
- **CB séquentiel** : 2 trades consécutifs clôturés ≤ −0,8R → cooldown 12 bougies 1h sans entrée + cap de risque ÷2 pendant les 5 trades suivants. (Implémentation : Protections freqtrade StoplossGuard + CooldownPeriod là où elles suffisent, complément custom sinon — vérifier la syntaxe exacte dans la doc au moment du code.)

## 3.6 Frais & slippage (backtest et journal)
Frais Binance spot réels (0,1 % taker par défaut, config). Slippage modélisé : 0,05 % (BTC/ETH) · 0,10 % (SOL/BNB) par côté. Le slippage réel mesuré en live est journalisé et comparé (invalidation si > 2× modèle).
