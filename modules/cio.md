# Module CIO — « on prend le trade ? »

> Agents d'origine : **Main Agent CIO** + **Strategist**. Deux fichiers : l'un classe le marché,
> l'autre vote. C'est le cerveau décisionnel — et il tient en 230 lignes.

## Où est le code

| Quoi | Fichier | Tests | Spec |
|---|---|---|---|
| Classification du régime | [`../user_data/strategies/arit_lib/regimes.py`](../user_data/strategies/arit_lib/regimes.py) | `tests/test_regimes.py` | `M02` + `docs/04.1-04.2` |
| Vote pondéré → conviction | [`../user_data/strategies/arit_lib/cio.py`](../user_data/strategies/arit_lib/cio.py) | `tests/test_cio.py` | `M03` + `docs/04.3-04.4` |
| Poids et seuils (figés) | `arit_lib/params.py` → `POIDS`, `SEUIL_*`, `MULT_*` | — | `docs/04.3` |

## Étape 1 — le régime (`regimes.py`)

Une **table ordonnée** (`REGLES`) = miroir exact du PDR 04.1 : le premier prédicat vrai gagne,
le dernier (fallback `RANGE`) matche toujours.

| Régime | Condition | Seuil d'entrée | Multiplicateur |
|---|---|---|---|
| `RISK_OFF` | Fear & Greed < 25 (macro, scalaire ⇒ tout ou rien) | — | **× 0** (aucune entrée) |
| `TREND` | ADX(14)_4h ≥ 25 + EMAs alignées | 0,50 | × 1,0 (F&G ≥ 45) sinon × 0,85 |
| `TRANSITION` | ni l'un ni l'autre | 0,65 | × 0,85 |
| `RANGE` | ADX < 20, ou fallback | — (NaN) | pas d'entrée |

En `RANGE` / `RISK_OFF` le seuil est **NaN** ⇒ toute comparaison `conviction >= seuil` vaut
`False`. Double sécurité avec le filtre `ENTRY_REGIMES`.

## Étape 2 — la conviction (`cio.py`)

```
conviction = min(1, Σ poids·score × multiplicateur)
```

Poids **FIGÉS**, somme = 1,0, **jamais hyperoptés** (interdit PDR) :

| `s_structure` | `s_momentum` | `s_sr` | `s_patterns` | `s_volume` |
|---|---|---|---|---|
| **0,40** | 0,20 | 0,15 | 0,15 | 0,10 |

Le signal n'est levé que si **les 4 conditions** sont vraies :

```
signal_long = (conviction >= seuil)          ← le >= est contractuel
            & (rr_dispo >= RR_MIN = 1,5)
            & (regime ∈ ENTRY_REGIMES)
            & new_4h                          ← uniquement à une clôture 4h
```

Macro V1.1 : régime macro `NEUTRE` ⇒ seuil **+0,05** (`MACRO_NEUTRE_CONV_BUMP`).

## L'idée n°8 de Jonas — pourquoi la fonda ne vote pas

La macro **n'entre jamais dans la somme pondérée**. Elle agit à un autre étage : elle **fixe** le
régime, donc le **seuil** et le **multiplicateur**. Un F&G catastrophique ne fait pas « baisser un
peu la note » — il met le multiplicateur à 0 et l'entrée devient impossible. C'est un
interrupteur, pas un vote.

## `explain()` — l'invariant M03.2

`cio.explain(row)` reconstruit le dict de **chaque** décision (scores, poids, régime, seuil,
multiplicateur, conviction) pour le journal. Idée n°5 : **toute évaluation est reconstructible
a posteriori**. C'est ce qui rend l'edge auditable et ce qui construira le dataset de la V2.

## Note V2

`conviction()` sera remplacée par FreqAI derrière **la même interface** (df in → conviction out).
Aucun appelant ne connaît l'implémentation — d'où le zéro couplage voulu ici.
