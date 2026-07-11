# RAPPORT — Protocole de backtest A/B (docs/09 §9.1)

Date : 2026-07-11 · 10 runs propres (2018-01-01 → 2026-07-10, 4 paires, `--timeframe-detail 5m`,
lanes isolées `backtest_lanes/run1..5`, état purgé avant chaque run, macro neutre + gate news ouvert).
Code testé : commit `59c4f58`+ (G6 événement + garde « vie du trade », 152 tests verts).

## 1. Tableau complet (cumul 8,5 ans)

| Run | Profit | PF | Trades | Win% | Durée moy. | DD max |
|---|---|---|---|---|---|---|
| **Contrôle A** (TP fixe +1,5R, SL initial, zéro G-rule) | **+40,0 %** | **2,12** | 55 | 71 % | 37 j | 19,3 % |
| sans-G6 | +0,7 % | 1,02 | 134 | — | 8 j | — |
| sans-G1 | −15,3 % | 0,77 | 183 | 31 % | 5 h | 22,2 % |
| sans-G2 | −15,8 % | 0,75 | 170 | 24 % | 6 h | 20,7 % |
| sans-G4 | −17,4 % | 0,74 | 179 | — | ~5 h | 23,6 % |
| sans-G7 | −17,9 % | 0,72 | 186 | — | ~5 h | — |
| sans-G3 | −18,2 % | 0,71 | 181 | — | ~5 h | 24,1 % |
| **Produit B** (G1-G7 complètes) | **−19,1 %** | **0,70** | 186 | 28 % | 4,5 h | 24,9 % |
| sans-G5 | −19,1 % | 0,70 | 186 | 28 % | 4,5 h | 24,9 % |
| CHoCH-priorité | −20,0 % | 0,68 | 187 | — | ~5 h | 25,9 % |

## 2. Sous-périodes (exigence 09 §9.1.3) — A et B

| Période | Contrôle A | Produit B |
|---|---|---|
| 2018-2020 (bull+bear+covid) | 21 trades · PF 25,7 · win 76 % · **+2 196 USDT** | 70 trades · PF 0,50 · −1 166 USDT |
| 2021-2022 (top+bear) | 26 trades · PF 36,4 · win 69 % · **+4 112 USDT** | 36 trades · PF 0,85 · −297 USDT |
| **2023-2026 (reprise)** | **8 trades · PF 0,32 · −2 306 USDT** ⚠️ | 80 trades · PF 0,77 · −449 USDT |

## 3. Verdicts formels

1. **B ÉCHOUE le gate central** (« B > A sur expectancy, PF ET DD, partout ») : A domine B sur
   TOUT en cumul. La gestion G1-G7, telle que spécifiée, **détruit** un edge d'entrée positif
   (mêmes entrées : +40 % tenues tranquilles vs −19 % gérées activement — les SL resserrés
   coupent en 3-4 h des trades qui gagnent en 37 jours).
2. **Hiérarchie des nuisances** (ablations) : G6 de très loin le pire (+20 pts retiré), puis
   G1 (+3,8), G2 (+3,3), G4 (+1,7), G7 (+1,2), G3 (+0,9). G5 strictement inerte (ne déclenche
   jamais). AUCUNE règle n'améliore B en son absence ⇒ aucune ne « paie » individuellement.
3. **BOS > CHoCH** (duel demandé par Jonas) : priorité CHoCH légèrement pire (−20,0 % vs
   −19,1 %). Le flag `S_STRUCTURE_CHOCH_PRIORITY` reste disponible, défaut = BOS.
4. **⚠️ L'edge d'entrée N'EST PAS uniformément bon** : A gagne massivement 2018-2022 mais
   PERD sur 2023-2026 (PF 0,32, 8 trades — échantillon minuscule car les positions de 37 j
   saturent les 3 slots). Le gate « B > A sur chaque sous-période » est donc invalidable des
   deux côtés : ni A ni B ne sont déployables en l'état. L'edge (BOS 4h swing) semble daté
   des grands cycles trending ; la période récente (chop) ne lui réussit pas.
5. Gates 09 §9.2 (PF ≥ 1,3 · DD ≤ 15 % · ≥ 100 trades) : **aucune configuration ne les passe**
   (A : PF ✅ 2,12 mais DD 19,3 % ❌ et 55 trades ❌ ; B : tout ❌).

## 4. Recommandations (dans l'ordre)

1. **Ne PAS déployer** (dry-run inclus) tant que l'edge n'est pas réparé — le PDR l'impose.
2. **Comprendre 2023-2026 avant tout** : analyser les 8 trades de A (qui sont-ils, pourquoi
   perdent-ils), et re-runner A sur 2023-2026 seul. Si l'edge est mort sur le marché récent,
   l'hyperopt d'entrée (§9.3) est le levier prévu ; sinon envisager les entrées « slots » (A
   sature 3 slots avec des trades de 37 j → très peu d'entrées récentes).
3. **Base de reconstruction** : config A (G-rules OFF) comme point de départ, réintroduction
   d'UNE règle à la fois, seulement si elle améliore A mesurablement (candidats : G7 time-stop
   assoupli, trailing G3 très large). Chaque réintroduction = décision Jonas + spec amendée.
4. **Couche macro crypto-native** (chantier 1) : à spécifier puis backtester PAR-DESSUS l'edge
   réparé — un filtre macro sur des entrées perdantes ne crée pas d'edge.

## 5. Décisions en attente de Jonas (répondre quand frais — AUCUNE urgence)

- **D1** (chantier 3) : valider l'ordre ci-dessus ? (enquête 2023-2026 → réparation edge →
  hyperopt §9.3 → réintroduction G-rules)
- **D2** (chantier 3) : feu vert hyperopt d'entrée (seuil TREND, bornes ADX, displacement,
  fraîcheur BOS · opt. 2018-2023, OOS 2024-2026 · valeurs ensuite FIGÉES) ?
- **D3** (chantier 1, macro) : sortie du module — 3 régimes discrets (recommandé) ou score continu ?
- **D4** (chantier 1) : périmètre V1 — DXY + stablecoins + funding + F&G historique (recommandé),
  ou liste différente ?
- **D5** (chantier 1) : pouvoir du module — véto + taille (recommandé) ou aussi seuil de conviction ?
- **D6** (arbre probabiliste) : lancer le POC « arbre v0 » (FOMC/CPI seuls, 2-3 jours) pour
  mesurer si l'événementiel prédit quelque chose sur CE marché ?

## 6. Reproduire / vérifier

```powershell
# runs du protocole : lanes isolées, état purgé avant chaque run
$FT = "C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe"
& $FT backtesting --strategy AritV1 -c user_data/config.dry.json --userdir backtest_lanes/run1 `
  --timerange 20180101- --timeframe-detail 5m --cache none        # produit B
# contrôle A : env ARIT_CONTROL_A=1 · CHoCH : ARIT_CHOCH_PRIORITY=1 · ablation : ARIT_G_OFF=G3
# résultats bruts : backtest_lanes/runN/backtest_results/*.zip (les DERNIERS zips = runs valides)
```
Pièges connus (état partagé, macro_state, --prepend, aiodns…) : BUILD_NOTES.md.
