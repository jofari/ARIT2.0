# Module MACRO — « le contexte est-il porteur ? »

> Agent d'origine : **Macro Analyst** + **Sentiment Watcher**. Devenu deux morceaux
> déterministes : un **service** qui va chercher les données dehors, un **module pur** qui les score.

## Où est le code

| Quoi | Fichier | Tests | Spec |
|---|---|---|---|
| Service collecteur (réseau) | [`../services/macro_state.py`](../services/macro_state.py) | `tests/test_macro_state.py` | `docs/modules/M08_macro_state.md` + `docs/06` |
| Régime macro V1.1 (pur) | [`../user_data/strategies/arit_lib/macro_regime.py`](../user_data/strategies/arit_lib/macro_regime.py) | `tests/test_macro_regime.py` | `docs/06 §6.2` |
| Téléchargement des séries | [`../scripts/download_macro.py`](../scripts/download_macro.py) | — | `docs/06 §6.2` |
| Lecture de l'état par le bot | `arit_lib/journal.py` → `read_macro_state()` | `tests/test_journal.py` | `docs/06` |

## Comment ça marche

Le service et le bot ne se parlent **jamais** en direct — ils communiquent par un fichier :

```
services/macro_state.py  ──écrit──►  user_data/macro_state.json  ──lit──►  AritV1.py
   (Fear&Greed, calendrier éco Finnhub)                            (via journal.read_macro_state)
```

C'est voulu : l'interdit n°1 du PDR = **aucun réseau dans le runtime de trading**. Si le service
meurt, le bot lit un état périmé et applique le fail-safe (`journal._fail_safe_macro`), il ne
plante pas et n'appelle pas le réseau lui-même.

### Le régime macro V1.1 (`macro_regime.py`)

5 composants quotidiens, chacun scoré dans **{+1, 0, −1}**, puis **somme** :

| Composant | Source | Scoré par |
|---|---|---|
| DXY (dollar) | FRED | `_score_dxy` |
| Taux | FRED | `_score_taux` |
| Stablecoins (offre) | — | `_score_stablecoins` |
| Funding | — | `_score_funding` |
| Fear & Greed | alternative.me | `_score_fear_greed` |

- **PORTEUR** si somme ≥ +2 · **HOSTILE** si ≤ −2 · **NEUTRE** sinon (`params.MACRO_REGIMES`)
- Composant périmé (> 48 h) ⇒ compte 0 · **≥ 3 composants périmés ⇒ HOSTILE** (fail-safe)
- **Point-in-time STRICT** : la valeur du jour J n'est utilisable qu'à partir de J+1 00:00 UTC
  (décalage +1 jour) — c'est ce qui garantit zéro look-ahead.

### Ce que la macro a le droit de faire

Idée n°8 de Jonas (`docs/04`) : **la fonda ne pèse JAMAIS dans une somme**. Elle ne vote pas.
Elle **fixe** le régime, le seuil d'entrée et le multiplicateur de conviction — voir [cio.md](cio.md).
Concrètement : Fear & Greed < 25 ⇒ `RISK_OFF` ⇒ plus aucune entrée.

## État actuel / limites connues

- Le **veto HOSTILE seul** est la seule variante validée à ce jour ; « A + macro » dégrade les
  résultats (verdict de la campagne macro — voir `for claude build/` et le dernier commit notes).
  **Décision Jonas en attente.**
- `FG_CACHE_HOURS` et `CALENDAR_CACHE_MIN` sont dans `params.py` mais **le service ne les lit pas** :
  il a ses propres constantes locales. Duplication à unifier — deux sources pour une seule valeur.
- `.env` requis : `FINNHUB_KEY` (calendrier). Actuellement **vide** ⇒ pas de calendrier éco.
