# PROPOSITION DE SPEC — Macro Analyst V1.1 (à valider par Jonas AVANT tout code)

> Statut : PROPOSITION du 2026-07-12. Une fois validée (ou corrigée), elle sera intégrée dans
> `docs/06_vetos_data.md` + `docs/04_cio_regimes.md` et deviendra contractuelle.
> Chaque seuil marqué 🔧 est ajustable par toi — les valeurs proposées sont des défauts
> raisonnés, PAS optimisés (on ne les hyperoptera jamais, comme les G-rules).

## 1. Principe
Le Macro Analyst produit un **régime macro** à 3 états — PORTEUR / NEUTRE / HOSTILE — recalculé
1×/jour (00:00 UTC), à partir de 5 séries publiques gratuites. Il se SUPERPOSE aux régimes
techniques (TREND/RANGE…) : il ne les remplace pas, il module l'autorisation d'entrer, la
taille et l'exigence de conviction. Il remplace et absorbe l'actuel véto « F&G < 25 ».

## 2. Les 5 composants (chacun → score ∈ {+1, 0, −1})

| # | Série | Source (gratuite) | Règle de score | Seuils 🔧 |
|---|---|---|---|---|
| 1 | **Dollar (DXY broad)** | FRED `DTWEXBGS` (daily) | variation sur 20 jours ouvrés : dollar qui BAISSE = porteur crypto | ≤ −0,5 % ⇒ +1 · ≥ +0,5 % ⇒ −1 · sinon 0 |
| 2 | **Taux Fed effectif** | FRED `DFF` (daily) | variation sur 60 j : détente = porteur | ≤ −0,10 pt ⇒ +1 · ≥ +0,10 pt ⇒ −1 · sinon 0 |
| 3 | **Market cap stablecoins** | DefiLlama `/stablecoins` (daily) | variation sur 30 j : émission = argent qui entre | ≥ +2 % ⇒ +1 · ≤ −1 % ⇒ −1 · sinon 0 |
| 4 | **Funding rate** (moy. BTC+ETH) | Binance fapi `fundingRate` (8 h) | moyenne 7 j : funding très positif = sur-levier long = fragile ; négatif = carburant | > +0,05 %/8h ⇒ −1 · < 0 ⇒ +1 · sinon 0 |
| 5 | **Fear & Greed** | alternative.me (daily, historique 2018+) | reprend ta logique actuelle | < 25 ⇒ −1 · ≥ 45 ⇒ +1 · sinon 0 |

## 3. Agrégation et régime

```
score_macro = Σ des 5 scores   ∈ [−5, +5]
PORTEUR  si score_macro ≥ +2      🔧
HOSTILE  si score_macro ≤ −2      🔧
NEUTRE   sinon
```
Données manquantes/stale (> 48 h 🔧) : le composant vaut 0 ; si ≥ 3 composants sont stale ⇒
HOSTILE (fail-safe, cohérent avec ta philosophie actuelle du calendrier irrécupérable).

## 4. Effets (remplacent le bloc F&G de docs/04 §4.2)

| Régime macro | Entrées | Taille | Seuil de conviction |
|---|---|---|---|
| PORTEUR | autorisées | ×1,0 | inchangé (0,50 TREND / 0,65 TRANSITION) |
| NEUTRE | autorisées | ×0,85 🔧 | +0,05 🔧 (0,55 / 0,70) |
| HOSTILE | **VÉTO** (comme RISK_OFF actuel) | — | — |

Le véto HOSTILE ne ferme JAMAIS une position ouverte (même règle que le changement de régime
technique). Chaque évaluation journalise `macro_regime` + les 5 scores (extension du schéma
`evaluation` de docs/08 — `schema_version` +1).

## 5. Backtest (remplace le « macro neutre »)
- Les 5 séries historiques sont téléchargées par `scripts/download_macro.py` →
  `user_data/data/macro/` (gitignoré, re-téléchargeable).
- **Point-in-time strict** : la valeur du jour J n'est utilisable qu'à partir de J+1 00:00 UTC
  (résolution journalière, zéro look-ahead intraday). Le régime macro du jour est mergé sur
  les bougies 1h comme une informative.
- Avant la première date disponible d'une série (ex. F&G commence 2018-02) : composant = 0.
- En live/dry : le service `macro_state.py` étendu calcule la même chose en continu — MÊME code
  de scoring (module pur `arit_lib/macro_regime.py`), deux sources d'alimentation.

## 6. Ce que ça ne fait PAS (V1.1)
Pas de news NLP, pas d'arbre probabiliste (POC séparé en cours), pas de dominance BTC (écartée
du périmètre par ta décision D4 — réintégrable plus tard), pas de pondération apprise (V2 =
FreqAI). Les seuils 🔧 sont FIGÉS après validation — jamais hyperoptés (interdit n°5).

## 7. Validation attendue de Jonas
Réponds simplement : « OK tout » — ou liste les numéros/seuils à changer
(ex. « composant 4 : véto dès +0,03 % » ou « HOSTILE dès −1 »).
