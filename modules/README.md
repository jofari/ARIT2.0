# modules/ — carte des modules ARIT

> **Ce dossier ne contient AUCUN code.** C'est une carte de navigation : une fiche par module
> conceptuel, qui pointe vers le vrai code, ses tests et sa spec.
>
> **Pourquoi le code n'est pas ici ?** freqtrade charge la stratégie depuis
> `user_data/strategies/` et met ce dossier sur le `sys.path` — c'est ce qui fait marcher
> `from arit_lib import ...` dans `AritV1.py` et dans les tests. Déplacer `arit_lib/` ici
> casserait le bot et les 200 tests. Le code reste où freqtrade l'attend ; cette carte dit où.

## Les 5 modules conceptuels

| Fiche | Ce que ça répond | Code réel |
|---|---|---|
| [macro.md](macro.md) | Le contexte est-il porteur ? (F&G, DXY, taux, stables, funding) | `services/macro_state.py` + `arit_lib/macro_regime.py` |
| [technical.md](technical.md) | Que dit le graphique ? (indicateurs, structure, S/R, scores) | `arit_lib/features.py` |
| [cio.md](cio.md) | On prend le trade ? (régime → poids → conviction → signal) | `arit_lib/regimes.py` + `arit_lib/cio.py` |
| [risk.md](risk.md) | Combien, et comment on gère ? (garde-fous, sizing, **G1-G7**) | `arit_lib/risk.py` + `arit_lib/gestion.py` |
| [quant.md](quant.md) | Est-ce que l'edge existe vraiment ? (recherche, event study) | `research/` |
| [backtest.md](backtest.md) | Comment on le prouve ? (protocole A/B, commandes, seuils) | freqtrade + `docs/09` |

## Le pipeline en une image

```
macro ──────┐
            ├──► cio (régime → seuil + poids → conviction) ──► risk (gate + sizing)
technical ──┘                                                       │
                                                                    ▼
                                                     AritV1.py (la colle freqtrade)
                                                                    │
                                                          ┌─────────┴─────────┐
                                                          ▼                   ▼
                                                   risk : G1-G7          journal JSONL
                                                   (gestion du trade)    (boîte noire)
```

## Correspondance avec les modules techniques M01-M10

Les fiches ci-dessus regroupent par **concept**. Le découpage **technique** (1 module = 1 fichier
= 1 spec = 1 fichier de tests) reste celui-ci :

| Mn | Fichier | Fiche concept |
|---|---|---|
| M01 features | `user_data/strategies/arit_lib/features.py` | [technical](technical.md) |
| M02 regimes | `user_data/strategies/arit_lib/regimes.py` | [cio](cio.md) |
| M03 cio | `user_data/strategies/arit_lib/cio.py` | [cio](cio.md) |
| M04 risk | `user_data/strategies/arit_lib/risk.py` | [risk](risk.md) |
| M05 gestion | `user_data/strategies/arit_lib/gestion.py` | [risk](risk.md) — G1-G7 |
| M06 journal | `user_data/strategies/arit_lib/journal.py` | transverse (boîte noire) |
| M07 strategy | `user_data/strategies/AritV1.py` | la colle — zéro métier |
| M08 macro | `services/macro_state.py` | [macro](macro.md) |
| M09 discord | `services/discord_bot.py` | transverse (digest + véto) |
| M10 watchdog | `services/watchdog.py` | transverse (surveillance) |
| — Macro V1.1 | `user_data/strategies/arit_lib/macro_regime.py` | [macro](macro.md) |

Les 2 fichiers « contrats », consommés par tous, sans logique métier :
`arit_lib/params.py` (toutes les constantes, chacune avec sa source PDR) et
`arit_lib/contracts.py` (noms de colonnes, clés `custom_data`, fichiers d'état).

## Voir aussi

- [`../guide.md`](../guide.md) — la carte du repo (dossiers, backtests, « où sont les 10 agents ? »)
- [`../guide_technique.md`](../guide_technique.md) — les outils/libs expliqués, les patterns maison
- [`../docs/`](../docs/) — **la spec officielle** (PDR v3) : elle fait autorité sur ces fiches
