# Module TECHNICAL — « que dit le graphique ? »

> Agents d'origine : **Technical Analyst** + **Flow Specialist** (réduit au score volume).
> Un seul fichier, 100 % pur : DataFrame in → DataFrame out.

## Où est le code

| Quoi | Où |
|---|---|
| Code | [`../user_data/strategies/arit_lib/features.py`](../user_data/strategies/arit_lib/features.py) (371 l.) |
| Tests | [`../tests/test_features.py`](../tests/test_features.py) |
| Spec | `docs/modules/M01_features.md` + `docs/05_signaux.md` |
| Colonnes produites | `arit_lib/contracts.py` → `FEATURE_COLUMNS` |

## Les deux étages

C'est le piège n°1 du module — il travaille sur **deux frames différentes** :

```
1. frame 4h/1d NATIVE (informatives, appelées par AritV1)
   add_indicators · find_pivots · track_structure · sr_levels · candle_patterns
   → noms SANS suffixe ; c'est freqtrade qui ajoute `_4h` / `_1d` au merge

2. df 1h MERGÉE (les colonnes *_4h/*_1d sont déjà là)
   compute_all → atr_1h, last_hl_1h, choch_bear_1h, new_4h, rr_dispo, s_*
```

Le merge freqtrade ne fait passer que des **clôtures** — c'est une des garanties anti-look-ahead.

## Ce qu'il produit

**Indicateurs** (talib) : EMA 50/200, ADX, RSI, MACD hist, ATR(14), SMA20 du volume.

**Structure** : pivots fractals (N = `PIVOT_N` = 2), BOS haussier, CHoCH baissier, et
`choch_bear_event_1h` — l'**événement** de cassure, pas l'état (voir [risk.md](risk.md), G6).

**S/R** : clustering des niveaux (`SR_CLUSTER_TOL_ATR` = 0,5 × ATR), `nearest_res_4h`,
`nearest_sup_4h`, `res_touches_4h`, et `rr_dispo` (le RR estimé avant l'entrée).

**Les 5 scores** — c'est la seule sortie que le CIO consomme. Toujours **discrets**,
dans `{0 · 0,3 · 0,5 · 0,7 · 1,0}` (`params.SCORE_VALUES`) :

| Score | Mesure |
|---|---|
| `s_structure` | BOS / CHoCH / tendance des pivots |
| `s_momentum` | RSI (1,0 si ∈ [50,70]) + MACD |
| `s_sr` | place disponible jusqu'à la résistance (1,0 si RR ≥ 2,0) |
| `s_patterns` | patterns de bougies talib |
| `s_volume` | vs SMA20 (1,0 si ≥ 1,5× · 0,5 si ≥ 1,0×) |

## Les 2 invariants à ne jamais casser

1. **Zéro look-ahead / zéro repaint.** Tout pivot décisionnel est confirmé 2 bougies plus tard
   (`PIVOT_CONFIRM_SHIFT`). Les fractals bruts **repeignent par construction** : depuis le
   2026-08-03 (décision A2) ils restent **locaux à `find_pivots`** et ne sont plus posés sur le
   DataFrame — seules les versions confirmées `*_conf_*` en sortent.
2. **NaN de warm-up ⇒ score 0**, jamais une exception, jamais un remplissage arbitraire.

## État actuel / limites connues

- ~~`SR_FORCE_TOUCHES_DIV = 4`~~ (force = min(touches/4, 1), PDR 05.2) : **ANNULÉ le 2026-08-03**
  (C4, décision Jonas). Constante retirée de `params.py` — ne sera pas implémenté en V1.
  `res_touches_4h` est bien calculé mais le nombre de touches ne pondère pas `s_sr`.
- `BBANDS_PERIOD` / `BBANDS_STD` : constantes présentes, **rien de câblé** (décision Jonas 09/07 :
  journalisées, pas utilisées en V1).
- `S_STRUCTURE_CHOCH_PRIORITY` (`ARIT_CHOCH_PRIORITY=1`) : branche A/B non tranchée.
- ~60 colonnes `cdl_*` (talib) sont journalisées mais **hors** `s_patterns` — dataset pour la V2.
