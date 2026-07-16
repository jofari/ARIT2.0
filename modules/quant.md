# Module QUANT — « est-ce que l'edge existe vraiment ? »

> Agent d'origine : **Quant / Backtester** (la moitié « recherche »).
> ⚠️ **Ce n'est pas un module du bot** : rien ici ne tourne en production. C'est le labo —
> du code jetable qui répond à une question, produit un verdict, et s'arrête là.

## Où est le code

| Quoi | Où |
|---|---|
| Travaux de recherche | [`../research/`](../research/) |
| POC event study FOMC/CPI | [`../research/arbre_v0/`](../research/arbre_v0/) |
| Le protocole qui valide le bot | [backtest.md](backtest.md) + `docs/09` |

## La règle du labo

Le code de `research/` **n'importe jamais** `arit_lib` et n'est **jamais** importé par le bot.
Il lit les mêmes données (`user_data/data/binance/*.feather`) et c'est tout. Un POC qui échoue
reste dans le repo **avec son verdict** — c'est le journal de ce qu'on a déjà essayé, pour ne pas
le refaire dans 6 mois.

## Travail en cours : `arbre_v0`

**Question** : les événements macro calendaires (FOMC, CPI US) prédisent-ils la direction du BTC
à J+1 / J+7 ?

**Méthode** — event study bayésien, seed = 42 :
- rendements close→close J→J+1 et J→J+7 vs baseline « tous les jours », IC bootstrap 90 %
  (N = 10 000)
- P(hausse | événement) avec lissage bayésien **Beta(2,2)**, IC de crédibilité 90 %
- calibration par **Brier walk-forward** (train 2018-2022, test 2023-2026)

**Qualité des dates** (le vrai travail — aucune approximation) :
- **FOMC** : federalreserve.gov, 67 réunions programmées 2018-01 → 2026-06 (67 et non 68 : la
  réunion de mars 2020 a été annulée)
- **CPI** : calendrier officiel BLS via **11 snapshots Wayback** (bls.gov bloque les clients
  non-navigateur) — 102 publications, aucun mois manquant
- HTML brut conservé dans `data/raw_html/` ⇒ **rejouable hors-ligne**

**Verdict** : ❌ **pas de signal sur la seule occurrence calendaire.** Voir
[`../research/arbre_v0/RESULTATS.md`](../research/arbre_v0/RESULTATS.md).

Relancer :
```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe research\arbre_v0\fetch_dates.py   # regénère les CSV (cache HTML)
& C:\Users\jofar\venvs\arit\Scripts\python.exe research\arbre_v0\event_study.py   # tables sur stdout
```

## Pourquoi pas de FreqAI / ML ici ?

La V1 est **100 % déterministe** (interdit n°1 : aucun LLM, aucun modèle dans le runtime).
Le ML est prévu en **V2**, et le chemin est déjà préparé : `cio.conviction()` sera remplacée par
FreqAI derrière la **même interface**, et `journal.py` construit **dès maintenant** le dataset
d'entraînement (chaque évaluation, avec les ~60 colonnes `cdl_*` et tous les scores).
Voir [cio.md](cio.md).
