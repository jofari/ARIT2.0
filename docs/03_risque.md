# 03 — Risque & gestion de position (LE cœur d'ARIT)

## 3.1 Sizing (custom_stake_amount)

### 3.1.0 AMENDEMENT du 2026-08-03 — risque CONSTANT (décision A6 de Jonas)
**Le sizing proportionnel à la conviction décrit en 3.1.1 est SUSPENDU en V1.**
- **Risque % = 1,16 %, constant**, quelle que soit la conviction. Source : Kelly mesuré sur
  l'échantillon de juillet 2026 (`research/pistes_2026-07-31/RAPPORT.md`).
- Motif : la conviction n'a jamais démontré de pouvoir prédictif ; faire varier la taille
  selon une grandeur non validée ajoute de la variance sans espérance. Un risque constant
  est la seule taille défendable tant qu'aucun edge n'est démontré (hypothèse v4, voir 01).
- ⚠️ **Écart assumé au PDR** : le PDR d'origine impose ½ Kelly (soit 0,58 %). Jonas a
  tranché pour le **Kelly plein**, en connaissance de cet écart, le 2026-08-03. Cet
  amendement existe pour que le choix soit tracé et non « magique » (interdit n°4).
  Conséquence : le sizing V1 n'a plus de marge de sécurité Kelly — l'erreur d'estimation de
  l'espérance se répercute intégralement dans la taille.
- Les caps (2 % / 3 %), le résiduel 6 % et le budget hebdo 8 % restent en vigueur et
  **bornent** ce risque constant ; le diviseur du coupe-circuit séquentiel s'y applique aussi.
- Le risque **adaptatif** (piloté par le module quant) est un chantier V2, explicitement
  reporté par Jonas.

### 3.1.1 Sizing par conviction — SUSPENDU (conservé pour la V2)
- Conviction `c ∈ [seuil, 1]` (sortie du CIO, voir 04). Normalisation : `n = (c − seuil) / (1 − seuil)` ∈ [0,1].
- **Risque % = 1 % + n × (cap − 1 %)** avec **cap = 2 %** pour les trades n°1 à 100 (compteur global persistant), **cap = 3 %** ensuite.

### 3.1.2 Commun (inchangé)
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
Frais Binance **USDⓈ-M futures** réels (**0,05 % taker** par défaut, config ; le maker vaut 0,02 %). ⚠️ Le taux spot 0,1 % ne s'applique plus depuis A2 (04/08, passage en `trading_mode: futures`). Slippage modélisé : 0,05 % (BTC/ETH) · 0,10 % (SOL/BNB) par côté. Le slippage réel mesuré en live est journalisé et comparé (invalidation si > 2× modèle).

## 3.7 AMENDEMENT du 2026-08-04 — géométrie SHORT (décision A2 de Jonas)

**Le bot est long ET short** (`can_short = True`, `trading_mode: futures`, `margin_mode:
isolated`). Ce n'est pas une option : l'hypothèse v4 de `01_edge.md` fait donner la
DIRECTION par la macro, et un régime macro HOSTILE est inexploitable sans vente à
découvert. Périmètre confirmé par Jonas après mise en garde : « long et short, en entier ».

### 3.7.1 Convention de signe — unique, non contournable
`sign = +1` en long, `−1` en short (`contracts.direction_sign`, exposé par
`TradeState.sign`). Toute la géométrie en découle :

| Grandeur | Formule unique |
|---|---|
| risque (unité R) | `sign × (entrée − SL_initial)` — toujours > 0, sinon cas dégénéré ⇒ skip |
| R d'un prix | `sign × (prix − entrée) / risque` |
| prix d'un R | `entrée + sign × R × risque` |
| « le SL resserre » | `sign × (SL_nouveau − SL_courant) > 0` |
| « la cible est atteinte » | `sign × (extrême − cible) ≥ 0` |

Aucune G-rule ne contient de test `if is_short` : le signe passe par ces formules. C'est
délibéré — c'est ce qui rend impossible une symétrisation *à moitié*, le mode de panne le
plus probable et le plus silencieux de ce chantier.

### 3.7.2 Les quatre asymétries réelles (tout le reste est mécanique)
1. **Ancre du SL initial et de G2** : `last_hl` (dernier Higher Low) en long, `last_lh`
   (dernier Lower High) en short. Le SL short est donc AU-DESSUS de l'entrée.
2. **Cible** : `nearest_res_4h` en long, `nearest_sup_4h` en short — pour le TP2 initial
   comme pour le TP2 de sortie recalculé à chaque clôture 1h (amendement 09/07).
3. **Événement de sortie G6** : CHoCH baissier en long, **CHoCH haussier** en short.
4. **Extrême de bougie** : l'excursion ADVERSE (MAE) est le `low` en long et le **`high`**
   en short ; l'excursion favorable (MFE) est l'inverse. Inverser ces deux-là piloterait
   G1/G3/G4/G7 à l'envers tout en gardant des signes plausibles — d'où un test dédié.

### 3.7.3 Ce qui NE change pas
Le sizing (risque constant 1,16 %, §3.1.0), les caps 2 %/3 %, le résiduel 6 %, le budget
hebdomadaire 8 %, RR ≥ 1,5, les circuit breakers (§3.5) et les protections natives
(07.1.1) sont **indifférents au sens**. Le résiduel d'un short se lit `SL − entrée` : sans
ce signe, tout short compterait pour 0 dans le budget 03.2.5.

### 3.7.4 Levier — DÉCISION NON PRISE
`AritV1` garde le défaut freqtrade (`leverage() → 1.0`), donc **l'exposition reste celle du
spot** : passer en futures n'augmente pas le risque par lui-même. Choisir un levier > 1 est
une décision de risque qui appartient à Jonas et n'est pas signée (cf. `DECISIONS.md`,
question A2-ter). Conséquence à connaître : si la distance de stop est très serrée, le
stake calculé par §3.1.2 peut dépasser l'équité disponible ; freqtrade le plafonne alors,
et le risque réel du trade devient **inférieur** à 1,16 % — silencieusement.
