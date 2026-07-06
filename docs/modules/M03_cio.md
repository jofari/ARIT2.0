# M03 — `arit_lib/cio.py` (la fusion : du contexte + des scores → une conviction)

**Lien à l'edge** : transforme 5 lectures partielles en UNE décision graduée. La conviction pilote directement le risque (1→3 %) — c'est le pont entre "voir" et "engager". Déterministe, explicable ligne par ligne (le journal doit pouvoir dire *pourquoi 0.72*).

**Libs** : `pandas`, `numpy`. Pur.

## Architecture interne
```python
POIDS = {"s_structure": .40, "s_momentum": .20, "s_sr": .15, "s_patterns": .15, "s_volume": .10}  # FIGÉS (PDR 04.3)
def conviction(df: DataFrame) -> DataFrame       # conviction = min(1, Σ w·s × multiplicateur) ; signal_long
def explain(row: Series) -> dict                 # dict complet pour le journal (scores, poids, régime, calcul)
```
`signal_long = (conviction >= seuil) & (rr_dispo >= 1.5) & regime.isin(["TREND","TRANSITION"]) & new_4h`

## Règles & invariants
1. POIDS jamais hyperoptés, jamais modifiés sans mise à jour du PDR 04.3 d'abord.
2. `explain()` est obligatoire à chaque évaluation journalisée — si une décision n'est pas reconstructible depuis le journal, c'est un bug.
3. V2 (FreqAI) remplacera `conviction()` derrière la MÊME interface (df in → conviction out) : ne rien coupler à l'implémentation interne.
**Tests** : somme des poids = 1.0 · conviction bornée [0,1] · multiplicateur ×0 ⇒ jamais de signal · cas limites au seuil exact (≥, pas >).
