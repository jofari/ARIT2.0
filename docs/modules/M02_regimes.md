# M02 — `arit_lib/regimes.py` (le contexte avant tout)

**Lien à l'edge** : matérialise l'idée 8 de Jonas — le bot ne pèse jamais les données pareil selon le marché. La technique dit où/quand ; ce module dit **si on a le droit** et fixe seuil + ampleur. C'est aussi le premier étage de protection (RANGE/RISK_OFF = pas d'entrée).

**Libs** : `pandas`, `numpy` uniquement. Fonctions pures.

## Architecture interne
```python
REGLES = [  # ordre = priorité (le premier qui matche gagne) — table-driven, miroir exact du PDR 04.1
    ("RISK_OFF",  lambda r, m: m["risk_off"] or m["stale"] or m["fear_greed"] < 25),
    ("RANGE",     lambda r, m: r["adx_4h"] < 20),
    ("TRANSITION",lambda r, m: r["adx_4h"] < 25),
    ("TREND",     lambda r, m: (r["ema50_4h"] > r["ema200_4h"]) and (r["close_4h"] > r["ema50_4h"])),
    ("RANGE",     lambda r, m: True),  # fallback (ADX fort mais contexte non haussier)
]
def classify(df: DataFrame, macro: dict) -> DataFrame   # ajoute regime, seuil, multiplicateur
def params_for(regime: str, fear_greed: int) -> tuple[seuil, multiplicateur]  # table PDR 04.2
```

## Stratégie précise
- Évalué ligne à ligne mais vectorisable par masques ; le `macro` (dict lu du JSON) est constant sur le df live — en backtest, macro historique indisponible → V1 assume `macro` neutre en backtest et les vetos news/F&G sont testés en ablation sur le dry-run (limitation documentée, honnête : le backtest mesure la mécanique prix, le dry-run mesure les vetos).
- `seuil` : TREND 0.50 · TRANSITION 0.65 · autres NaN (pas d'entrée). `multiplicateur` : ×1.0 (F&G ≥ 45) · ×0.85 (25-44 ou TRANSITION) · ×0 (RISK_OFF).

## Règles & invariants
1. Un changement de régime ne ferme JAMAIS une position (seules G1-G7 sortent).
2. `stale` du macro_state ⇒ traité comme RISK_OFF (fail-safe).
3. Les bornes (20/25 ADX, 25/45 F&G) vivent dans `params.py`, hyperopt autorisé UNIQUEMENT sur les bornes ADX (PDR 09.3).
**Tests** : chaque branche de la table · priorité RISK_OFF > tout · fallback RANGE · stale ⇒ RISK_OFF.
