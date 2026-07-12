# Arbre de probabilité v0 — event study FOMC / CPI sur BTC (résultats)

Généré par `event_study.py` (seed=42, N_BOOT=10000), données BTC/USDT-1d Binance 2017-08-17 → 2026-07-09.

## Méthodo (3 lignes)

Pour chaque événement (67 décisions FOMC, 102 publications CPI, 2018-01 → 2026-06) on mesure les rendements
close→close J→J+1 et J→J+7 vs la baseline « tous les jours » (IC bootstrap 90 %), puis P(hausse | événement)
avec lissage bayésien Beta(2,2) et IC de crédibilité 90 % ; calibration par Brier walk-forward (train 2018-2022, test 2023-2026).

## Qualité des dates (sources réelles, pas d'approximation)

- **FOMC** : federalreserve.gov (fomccalendars.htm + fomchistorical2018-2020.htm), téléchargées en direct le 2026-07-12.
  Jour retenu = dernier jour de la réunion (jour de la décision). Meetings programmés uniquement
  (unscheduled/notation votes/cancelled exclus — d'où 67 et non 68 : réunion de mars 2020 annulée). 4 réunions 2026 (jusqu'à juin).
- **CPI** : calendrier officiel BLS (bls.gov/schedule/news_release/cpi.htm) via 11 snapshots Wayback Machine 2017→2026
  (bls.gov bloque les clients non-navigateur). Pour chaque mois de référence, le snapshot le plus récent gagne
  (couvre les re-planifications). 102 publications, aucun mois manquant sur la fenêtre.
- HTML brut conservé dans `data/raw_html/` ; dates finales dans `data/fomc_dates.csv` et `data/cpi_dates.csv`.

**Caveat timing** : décision FOMC à 14h00 ET et CPI à 08h30 ET tombent *dans* la bougie daily UTC du jour J.
Le rendement close(J)→close(J+h) mesure donc la dérive post-événement, pas la réaction immédiate à l'annonce
(qui est dans la bougie J elle-même).

## Distributions conditionnelles

### Période complète 2018-01 → 2026-06

| Condition | h | rendement moyen [IC boot 90 %] | P(hausse) [IC créd. 90 %] |
|---|---|---|---|
| Baseline (tous les jours) | J+1 | +0.11 % [+0.01, +0.20] | 0.508 [0.493, 0.523] (k=1577/n=3103) |
| Baseline (tous les jours) | J+7 | +0.72 % [+0.46, +0.98] | 0.522 [0.508, 0.537] (k=1621/n=3103) |
| FOMC | J+1 | +0.03 % [-0.70, +0.77] | 0.437 [0.341, 0.534] (k=29/n=67) |
| FOMC | J+7 | -0.63 % [-2.75, +1.63] | 0.507 [0.410, 0.604] (k=34/n=67) |
| CPI | J+1 | -0.11 % [-1.03, +0.68] | 0.500 [0.420, 0.580] (k=51/n=102) |
| CPI | J+7 | +0.22 % [-1.39, +1.78] | 0.519 [0.439, 0.598] (k=53/n=102) |

### Sous-période 2018-2021

| Condition | h | rendement moyen [IC boot 90 %] | P(hausse) [IC créd. 90 %] |
|---|---|---|---|
| Baseline (tous les jours) | J+1 | +0.17 % [-0.00, +0.34] | 0.526 [0.504, 0.547] (k=768/n=1461) |
| Baseline (tous les jours) | J+7 | +1.09 % [+0.63, +1.56] | 0.533 [0.512, 0.555] (k=779/n=1461) |
| FOMC | J+1 | +0.67 % [-0.54, +1.89] | 0.400 [0.269, 0.538] (k=12/n=31) |
| FOMC | J+7 | +0.67 % [-2.99, +4.53] | 0.543 [0.405, 0.678] (k=17/n=31) |
| CPI | J+1 | -0.53 % [-2.34, +1.05] | 0.481 [0.368, 0.594] (k=23/n=48) |
| CPI | J+7 | +0.41 % [-2.29, +3.09] | 0.519 [0.406, 0.632] (k=25/n=48) |

### Sous-période 2022-2026

| Condition | h | rendement moyen [IC boot 90 %] | P(hausse) [IC créd. 90 %] |
|---|---|---|---|
| Baseline (tous les jours) | J+1 | +0.05 % [-0.06, +0.16] | 0.493 [0.472, 0.513] (k=809/n=1642) |
| Baseline (tous les jours) | J+7 | +0.39 % [+0.10, +0.68] | 0.513 [0.492, 0.533] (k=842/n=1642) |
| FOMC | J+1 | -0.52 % [-1.39, +0.31] | 0.475 [0.347, 0.604] (k=17/n=36) |
| FOMC | J+7 | -1.76 % [-4.16, +0.58] | 0.475 [0.347, 0.604] (k=17/n=36) |
| CPI | J+1 | +0.26 % [-0.40, +0.93] | 0.517 [0.410, 0.624] (k=28/n=54) |
| CPI | J+7 | +0.05 % [-1.74, +1.76] | 0.517 [0.410, 0.624] (k=28/n=54) |

(Les k identiques J+1/J+7 en 2022-2026 sont une coïncidence, revérifiée indépendamment.)

Lecture : **tous** les IC conditionnels chevauchent largement la baseline, sur la période complète comme sur
chaque sous-période. Les moyennes changent même de signe entre sous-périodes (FOMC J+1 : +0.67 % → -0.52 %) :
aucune stabilité.

## Arbre v0 (2 niveaux, période complète)

Niveau 1 : direction close(J)→close(J+1). Niveau 2 : direction close(J+1)→close(J+7), conditionnelle à la
branche du niveau 1. Probabilités lissées Beta(2,2), IC 90 %.

```
FOMC (n=67)
 +-- hausse J+1  P=0.437 [0.341, 0.534]  (n=29)
 |    +-- hausse J+7  P=0.576 [0.433, 0.713]
 |    \-- baisse J+7  P=0.424 [0.287, 0.567]
 \-- baisse J+1  P=0.563 [0.466, 0.659]  (n=38)
      +-- hausse J+7  P=0.452 [0.329, 0.579]
      \-- baisse J+7  P=0.548 [0.421, 0.671]
CPI (n=102)
 +-- hausse J+1  P=0.500 [0.420, 0.580]  (n=51)
 |    +-- hausse J+7  P=0.564 [0.453, 0.671]
 |    \-- baisse J+7  P=0.436 [0.329, 0.547]
 \-- baisse J+1  P=0.500 [0.420, 0.580]  (n=51)
      +-- hausse J+7  P=0.582 [0.472, 0.689]
      \-- baisse J+7  P=0.418 [0.311, 0.528]
```

Toutes les arêtes ont un IC qui contient 0.5 (ou frôle sa borne) : l'arbre n'encode aucune asymétrie fiable.

## Brier walk-forward (train 2018-2022 → test 2023-2026)

| Événement | h | n test | p̂ (train) | Brier événement | Brier 50/50 | Brier base rate |
|---|---|---|---|---|---|---|
| FOMC | J+1 | 28 | 0.419 | 0.2508 | 0.2500 | 0.2510 |
| FOMC | J+7 | 28 | 0.512 | 0.2501 | 0.2500 | 0.2502 |
| CPI | J+1 | 42 | 0.453 | 0.2589 | 0.2500 | 0.2484 |
| CPI | J+7 | 42 | 0.469 | 0.2569 | 0.2500 | 0.2477 |

Le prédicteur conditionné aux événements ne bat **jamais** le 50/50 ni le base rate hors-échantillon
(il est même légèrement pire pour le CPI).

## CONCLUSION (honnête)

Sur 2018-2026, la simple *occurrence* d'un FOMC ou d'un CPI n'a **pas de pouvoir prédictif détectable** sur la
direction du BTC à J+1 ou J+7 : tous les intervalles conditionnels chevauchent la baseline, les effets moyens
changent de signe entre sous-périodes, et le Brier walk-forward est au mieux égal au 50/50. Verdict : **pas de
signal exploitable** avec des probabilités inconditionnelles par type d'événement ; si un futur arbre v1 doit
exister, il devra conditionner sur le *contenu* de l'événement (surprise vs consensus, hawkish/dovish), pas sur
sa seule présence au calendrier.
