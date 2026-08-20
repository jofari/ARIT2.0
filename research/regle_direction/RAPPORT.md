# Règle de direction — décompte descriptif des variantes (2026-08-20)

> **Ce document ne conclut rien.** Aucune hypothèse préenregistrée, aucune p-value, aucune
> correction de tests multiples. On compte des signaux et on affiche des R moyens sur des
> groupes de 6 à 44 observations, où le MDE est de l'ordre du R entier : **tout écart lu
> ici est indécidable**. Toute décision qui s'appuierait sur un de ces R exige un
> préenregistrement préalable (`analysis/registre.py`, B6).
>
> Code : `compte_variantes.py`. Source : `analysis/out/arit_analyse.sqlite`, **`split='train'`
> uniquement** — le hold-out B5 n'est pas lu.

## Pourquoi ce décompte

Jonas, 20/08 : « A2-quater pas du tout ce que je voulais, je voulais un filtre décisionnel
pas une interdiction de long ». La règle qu'il écrit :

```
if macro.trend == bullish and signal.technique == bullish:   → long   + journal
elif macro.trend == bearish and signal.technique == bearish: → short  + journal
else:                                                          journal seul
```

Question : **de combien le câblage actuel s'écarte-t-il de cette règle, et ce que ça coûte.**

## Ce que le câblage fait aujourd'hui

`cio.conviction` (`cio.py`) :

```
signal_long  = conviction >= seuil & rr_dispo >= 1,5 & regime ∈ {TREND, TRANSITION}
             & new_4h & trend_dir >= 0 & direction_macro ∈ {long, both}
signal_short = miroir strict, trend_dir <= 0, direction_macro ∈ {short, both}
```

`direction_macro` : PORTEUR → long · HOSTILE → short · **NEUTRE → both** · inconnu → long
(fail-safe), puis le véto actions c6/c7 (hors donnée périmée) transforme long → **none** et
both → short.

**La structure `if/elif/else` de Jonas est donc déjà celle du code** : `signal_long` est
bien la conjonction « macro autorise le long » ∧ « la technique est haussière ». Trois
écarts seulement, et un seul est coûteux.

## Le décompte

Sur 42 958 évaluations du train, la technique seule (macro ignorée) produit **50 signaux
longs et 35 shorts**.

| Variante | long | short | total |
|---|---|---|---|
| **V0 — production (A2-quater)** | 50 (R −0,0736) | 28 (R +0,1150) | **78** |
| V0b — avant A2-quater (véto = coupe-circuit) | 50 (R −0,0736) | 28 (R +0,1150) | **78** |
| **V1 — concordance stricte (NEUTRE = rien)** | 44 (R −0,0609) | 19 (R −0,0663) | **63** |
| V2 — concordance + véto dégradé d'un cran | 44 | 19 | 63 |
| V3 — concordance + véto force HOSTILE | 44 | 19 | 63 |
| V4 — concordance, NEUTRE garde les deux sens | 50 | 28 | 78 |

### Fait n° 1 — A2-quater n'a rien changé, et n'aurait rien changé dans l'autre sens

**V0 = V0b, trait pour trait.** Le véto actions directionnel est actif sur **2 298 lignes**,
et **aucun signal technique ne tombe dessous** : 0 long, 0 short. Sur cinq ans de données,
que le véto soit un coupe-circuit ou un filtre directionnel ne déplace **pas un seul trade**.

⇒ Le désaccord sur A2-quater porte sur un bloc **inerte dans l'historique mesuré**. Il reste
une question de spec (que doit *signifier* une cassure du NASDAQ corrélée), pas une question
de performance. V2 et V3, les deux façons de rendre le véto « décisionnel » plutôt
qu'« interdicteur », donnent exactement le même décompte que V1.

### Fait n° 2 — la concordance stricte coûte 19 % des signaux

78 → **63** (−15 signaux) : 6 longs et 9 shorts, **tous en macro NEUTRE**. C'est le seul
écart réel entre le code et la règle écrite par Jonas, et il tape sur le goulot n° 1 du
projet (rareté des entrées, chantier Q1).

### Fait n° 3 — les signaux retirés sont le seul groupe positif du lot

| macro | long | R moyen | short | R moyen |
|---|---|---|---|---|
| PORTEUR | 44 | −0,0609 | 7 *(bloqués)* | −0,2286 |
| **NEUTRE** | 6 | −0,1667 | **9** | **+0,4978** |
| HOSTILE | 0 | — | 19 | −0,0663 |

Les 9 shorts en macro NEUTRE portent **+0,4978 R de moyenne** — le seul groupe nettement
positif de tout le tableau. La règle stricte les supprimerait.

⚠️ **n = 9.** À ce N le MDE dépasse le R entier : ce n'est **pas** un résultat, c'est un
signal contraire assez visible pour interdire d'appliquer V1 sans mesure. Si la question doit
être tranchée sur les chiffres, elle se préenregistre d'abord.

### Fait n° 4 — deux constats de passage

- Les 7 shorts techniques en macro PORTEUR (R −0,2286) sont bloqués par la porte macro
  aujourd'hui. La porte macro **fait son travail** sur ce sous-groupe.
- **Les 78 signaux sont tous en régime technique TREND. Zéro en TRANSITION.** Le seuil
  TRANSITION (0,65) n'est jamais atteint sur cinq ans — à verser à Q1 (courbe N(seuil)).

## Ce que la règle de Jonas demande et qui n'existe nulle part

Le `else: enregistrement des raisons dans la base de données`.

Aujourd'hui `AritV1._journal_evaluation` écrit bien une ligne pour chaque évaluation, mais la
raison d'un `no_signal` est **le régime technique** (`row.get("regime")`), pas le motif du
refus. Le journal ne permet donc pas de distinguer « refusé parce que la macro est
discordante » de « refusé parce que la conviction est insuffisante » ou « parce que le RR
manque ». C'est le **seul morceau de la spec de Jonas réellement absent du code** — et c'est
exactement le manque que BETA a rencontré sur R6 (`news_window`), où il a fallu reconstruire
les populations à la main pour découvrir que l'hypothèse n'était pas mesurable.
