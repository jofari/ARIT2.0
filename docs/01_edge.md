# 01 — Hypothèse d'edge (v4, SIGNÉE par Jonas le 2026-08-03)

> **La macro détermine la DIRECTION de la position (long ou short).
> La technique détermine le MOMENT d'entrée et le MOMENT de sortie.**
> (Formulation de Jonas, intégrée telle quelle — décision A7 du 03/08, cf. `DECISIONS.md`.)

Exemple donné par Jonas : BTC atteint un seuil intéressant, la macro est haussière, les
indicateurs techniques (volume, MACD, RSI, positionnement) sont majoritairement haussiers
→ entrée en position longue.

## Statut de l'hypothèse précédente — INVALIDÉE, archivée plus bas
La v3 (« l'edge est dans la gestion dynamique des positions ») est **falsifiée depuis le
2026-07-19** par son propre test central : B = −17,4 % contre A = +0,12 %, donc B ≤ A. Le
doc v3 exigeait « retour recherche, pas de rationalisation » — c'est ce qui est fait ici.
Le texte v3 est conservé intégralement en annexe : on n'efface pas une hypothèse falsifiée,
on la garde comme dette de crédibilité.

## Thèse (v4)
Deux affirmations **séparables**, donc testables séparément — c'est tout l'intérêt du
découpage direction/timing :

1. **Direction (issu de H2)** : le régime macro porte une information directionnelle
   exploitable. C'est le seul signal non-bruit mesuré à ce jour (p = 0,095, branche
   MacroFlip, +577 % en spot).
2. **Timing (issu de H1)** : à direction donnée, l'edge réside dans la géométrie du couple
   (stop, cible) et dans le choix du moment, pas dans la sélection d'un setup. C'est la
   seule déviation positive au modèle nul mesurée (z = 1,74).

La v3 prétendait que l'edge était dans la **gestion** d'une position déjà ouverte. La v4
déplace la charge : la gestion n'est plus la source de l'edge, elle redevient un dispositif
de préservation. Le score de conviction ne choisit plus la direction — il ne fait que
temporiser.

## Mode de fonctionnement (v4)
- **Direction** : donnée par le régime macro. PORTEUR → long autorisé, HOSTILE → short
  autorisé, NEUTRE → seuil de conviction relevé (`MACRO_NEUTRE_CONV_BUMP`, décision A5 du
  03/08 : la pénalité NEUTRE est CONSERVÉE, le véto HOSTILE n'agit pas seul).
- **Le bot est long ET short** (décision A2 du 03/08). Un signal macro baissier est
  inexploitable en spot long-only : le short est une **dépendance** de cette hypothèse, pas
  une option. Conséquence : `trading_mode: futures`, `margin_mode: isolated`.
- **Timing d'entrée** : faisceau technique (volume, MACD, RSI, positionnement funding/OI)
  majoritairement dans le sens de la direction macro, en clôture confirmée.
- **Timing de sortie** : géométrie (stop, cible) fixée à l'entrée, RR initial ≥ 1,5.
- **Sizing** : risque constant à 1,16 % (décision A6 du 03/08, cf. `03_risque.md`).

## Falsifiabilité — DEUX tests, un par affirmation
Le découpage direction/timing impose de falsifier les deux moitiés indépendamment. Une
hypothèse composite qu'on ne teste qu'en bloc est irréfutable — donc inutile.

### Test 1 — la macro donne-t-elle vraiment la direction ?
- **Contrôle** : direction tirée à pile ou face, timing technique identique.
- **Produit** : direction donnée par le régime macro, timing technique identique.
- **Exigence** : taux de bonne direction significativement > 50 % (bloc-bootstrap, p < 0,05
  après correction Benjamini-Hochberg sur le compteur d'essais tenu dans
  `research/EXPERIMENTS.jsonl`), ET `g = E[ln(1+fR)]/E[T]` supérieur au buy & hold spot
  **après funding**.
- **Falsification** : direction macro ≤ pile ou face, ou p > 0,20 sur un walk-forward des
  seuils macro (calibration 2020-2022, test 2023-2026).

### Test 2 — le timing technique apporte-t-il quelque chose ?
- **Contrôle** : même direction macro, entrée à un instant **tiré au hasard** dans la
  fenêtre où la direction est active, même géométrie de stop.
- **Produit** : même direction macro, entrée au signal technique.
- **Exigence** : Δp > 0 sur **≥ 400 signaux**, et espérance nette qui ne change pas de signe
  entre 6 et 15 bps de frais.
- **Falsification** : le timing technique ne bat pas l'entrée aléatoire ⇒ la couche
  technique est décorative, on la retire et le bot devient un pur véhicule macro.

### Garde-fou commun (piège du substrat nul)
Sur un substrat à espérance nulle, **tout filtre qui réduit l'exposition paraît positif**.
Aucun résultat de Test 1 ou 2 n'est recevable sans son contrôle apparié tourné sur la
**même** période, avec le **même** nombre de signaux et les frais inclus.

## Limite honnête (garde-fou intellectuel)
Inchangée depuis la v3, et elle s'applique encore plus fort ici : sur des entrées à
espérance nulle, toute stratégie de sortie est ≤ 0 après frais (propriété martingale). Si le
Test 1 échoue, le Test 2 ne peut pas le rattraper — une bonne géométrie sur une direction
aléatoire reste une espérance nulle moins les frais. **L'ordre des tests n'est pas
négociable : Test 1 d'abord.**

## Invalidation live (chiffrée)
PF glissant < 1,1 sur les 100 derniers trades · expectancy < 0 sur fenêtre 3 mois ·
divergence live/backtest > 10 pts de win-rate · slippage réel > 2× modélisé → **halt + revue**.

## Dépendance de régime
En v4 le bot n'est plus long-only : un marché baissier devient exploitable au lieu d'imposer
le cash. En contrepartie, le coût de portage (funding) devient une variable de décision et
non plus un détail — il entre explicitement dans le critère `g` du Test 1.

---

## Annexe — hypothèse v3, INVALIDÉE le 2026-07-19 (conservée telle quelle)

> **L'edge d'ARIT n'est pas dans la détection d'entrée. Il est dans la gestion dynamique et permanente des positions, 24 h/24.**
> Direction assumée : **swing, pas scalp**. Un bot a un meilleur edge en management de position qu'en entrée scalpée : cela limite le risque et vise des profits **plus constants** — moins gros que ceux d'une "entrée parfaite" théorique, mais réguliers et défendables. (Formulation de Jonas, intégrée telle quelle.)

**Thèse v3** — Sur l'horizon swing crypto, la majorité des participants retail perdent par mauvaise gestion (stops déplacés dans le mauvais sens, gains coupés tôt, pertes laissées courir, sommeil, émotions), pas par absence de setups. ARIT inverse : **peu de positions (max 3), chacune gérée en continu** — réduction agressive du risque dès que possible, extension des gains tant que la structure le justifie. Un vrai trader, qui ne dort jamais.

**Mode de fonctionnement v3** — Entrée : setup de continuation post-BOS validé en clôture 4h · RR initial ≥ 1,5 obligatoire · risque 1→2 % (puis 1→3 %) proportionnel à la conviction. Pendant : SL ne peut que se resserrer (G1-G3), TP partiel + extension (G4-G5), sorties anticipées (G6-G7). Résultat visé : perte moyenne < 1R, gain moyen > 1,5R, même à win-rate moyen.

**Pourquoi ça persiste (v3)** — Avantage d'**exécution** contre le participant marginal de cet horizon (retail humain : dort, émotions, indiscipline). Les institutionnels ne jouent pas à cette échelle (taille incompatible) — la petitesse est un avantage.

**Test central v3** — Version A (contrôle) : mêmes entrées, même SL initial, TP fixe à 1,5R, AUCUNE G-rule. Version B (produit) : mêmes entrées + G1-G7. Exigence : B > A sur expectancy, profit factor ET drawdown max.
**Résultat mesuré le 2026-07-19 : B = −17,4 %, A = +0,12 % ⇒ B ≤ A ⇒ HYPOTHÈSE INVALIDÉE.**
