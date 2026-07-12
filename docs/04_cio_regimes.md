# 04 — CIO : régimes de marché & pondération contextuelle (idée 8 de Jonas)

> Principe directeur : **la technique dit OÙ et QUAND précisément ; la macro/fonda dit SI on a le droit d'agir et avec QUELLE ampleur.** Le bot ne pèse jamais les données de la même façon selon le contexte — c'est un bot financier, pas un problème de maths théorique. La fonda n'est PAS un poids dans une somme : elle fixe le régime, le multiplicateur et le seuil.

## 4.1 Classification de régime (déterministe, évaluée à chaque clôture 4h)
Ordre d'évaluation (le premier qui matche gagne) :
1. **RISK_OFF** si : fenêtre event ±30 min (06) OU **régime macro HOSTILE** (Macro Analyst
   V1.1, docs/06 §6.2 — validé Jonas 2026-07-12 ; absorbe l'ancien critère « F&G < 25 »)
   OU `macro_state.risk_off == true`.
2. **RANGE** si : ADX(14)_4h < 20.
3. **TRANSITION** si : 20 ≤ ADX(14)_4h < 25.
4. **TREND** si : ADX(14)_4h ≥ 25 ET EMA50_4h > EMA200_4h ET close_4h > EMA50_4h.
5. Sinon (ADX ≥ 25 mais contexte EMA non haussier) → **RANGE** (pas de continuation long dans un downtrend en spot long-only).

## 4.2 Comportement par régime
| Régime | Entrées | Seuil conviction | Multiplicateur | Gestion |
|---|---|---|---|---|
| TREND | Oui | **0,50** (+0,05 si macro NEUTRE) | ×1,0 si macro PORTEUR · ×0,85 si NEUTRE | G-rules standard |
| TRANSITION | Oui | **0,65** (+0,05 si macro NEUTRE) | ×0,85 | G-rules standard |
| RANGE | **Non** (veto — stratégie range = backlog V2) | — | — | Positions ouvertes : gestion continue normale |
| RISK_OFF | **Non** (veto) | — | ×0 | **Durcie** : G3 passe à 1,5×ATR |
Les positions déjà ouvertes ne sont jamais fermées par un simple changement de régime — seules G1-G7 gèrent les sorties.

## 4.3 Profil de poids (V1 : un seul profil actif, en TREND/TRANSITION)
| Module | Poids |
|---|---|
| Structure (BOS/continuation) | **0,40** |
| Momentum (RSI/MACD 4h) | **0,20** |
| Support/Résistance (qualité du RR) | **0,15** |
| Patterns chandeliers | **0,15** |
| Volume (confirmation) | **0,10** |
Poids FIGÉS (pas d'hyperopt). V1.5 : profils distincts par régime testés en ablation. V2 : poids appris (FreqAI) — voir 10.

## 4.4 Formule de conviction (exacte)
```
conviction = min(1.0, (0.40·s_structure + 0.20·s_momentum + 0.15·s_sr + 0.15·s_patterns + 0.10·s_volume) × multiplicateur_regime)
signal_entrée = (conviction ≥ seuil_du_régime) ET (RR_dispo ≥ 1.5) ET (régime ∈ {TREND, TRANSITION})
```
Les scores `s_*` ∈ {0, 0.3, 0.5, 0.7, 1.0} (valeurs discrètes, définies en 05) — discrets pour rester lisibles, journalisables et déterministes.

## 4.5 Journalisation obligatoire
Chaque évaluation 4h écrit dans le journal : régime retenu + valeurs (ADX, EMAs, F&G, macro_state), les 5 scores, conviction, seuil, décision. C'est ce qui permet l'audit ("pourquoi le bot n'a rien fait mardi ?") et le futur entraînement FreqAI.
