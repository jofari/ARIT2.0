# RAPPORT — Marché crypto, institutions/whales & refonte des G rules

Date : 2026-07-19 · Auteur : Claude (campagne demandée par Jonas) · Statut : **proposition — AUCUNE modification de code/spec appliquée** (gouvernance PDR respectée).

---

## 0. TL;DR

1. **L'edge d'entrée BOS 4h est nul.** Contrôle A corrigé (SL actif, macro neutre), 2018→2026, 4 paires, détail 5m : **+0,12 %, PF 1,00, 128 trades, p-value 0,99**. Le « +40 % » du rapport A/B du 11/07 était un artefact du bug SL. Par année d'entrée : 2021 porte tout (+65 %) ; 2019-2020 négatifs ; 2023-2026 ≈ flat. L'edge n'est pas « mort en 2023 » — il n'a jamais existé de façon robuste hors 2021.
2. **Aucune gestion ne peut réparer ça** (garde-fou martingale de docs/01, confirmé empiriquement) : les 12 politiques simulées en R-space sur les 123 épisodes corrigés vont de −0,11R à +0,26R/épisode, et le seul candidat positif (TP1 + giveback) retombe à **+0,00R sans son meilleur trade**. Le produit B corrigé (G1-G7) : **−17,38 %, PF 0,72** — quasi identique au B buggé, les ablations du 11/07 restent valides.
3. **G rules : proposition = suppression de la couche 1h** (G1, G2, G3, G6), G5 déjà inerte, G4 (TP1) conservée, G7 neutre (hygiène de slots), remplacement par UNE règle giveback à grande échelle — mais **seulement après** réparation de l'edge d'entrée, sinon c'est peindre un moteur cassé.
4. **Levier n° 1 identifié (côté entrée, 03.3)** : le stop structurel 4h est ~2× trop large pour le profil réel des gagnants (burst : médiane 3,75 h jusqu'à +1,5R, MAE médian −0,25R). À demi-distance de stop, à risque constant, l'espérance passe de **+0,016 à +0,333 R-risque/trade (×20, brut)**. À confirmer en granularité 5m + frais, mais c'est le chantier prioritaire.
5. **Marché 2024-2026** : la microstructure a changé (ETF/advisors qui rebalancent, gamma dealers qui épinglent le prix, whales qui chassent les liquidations). Un breakout-continuation avec stops serrés est précisément la stratégie que cette structure punit.
6. **Polymarket** : API publique exploitable en lecture (bloquée DNS en France — contourné proprement, à assumer en infra), et c'est la source de « consensus/surprise » qui manquait à l'arbre v0. Snapshot du jour : Fed sans baisse 2026 = 85 %, hausse 2026 = 54 % → régime taux HOSTILE pricé en continu.

---

## 1. Campagne corrigée du 19/07 (chiffres neufs)

Protocole : lanes isolées (`backtest_lanes/run1` = A pur, `run3` = B pur), état purgé, **macro neutralisée** (`user_data/data/macro` renommé pendant la campagne — tranche le point « À DÉCIDER » du 18/07 : la neutralisation par retrait du dossier fonctionne, événement `macro_unavailable` journalisé), `--timerange 20180101- --timeframe-detail 5m --cache none`, code au commit `aec6308` (fix SL contrôle A, 203 tests verts).

### 1.1 Portefeuille (freqtrade, net de frais)

| Run | Profit | PF | Trades | Balance min/max | Notes |
|---|---|---|---|---|---|
| **A pur corrigé** (TP fixe +1,5R, SL initial, zéro G-rule) | **+0,12 %** | **1,00** | 128 | 9 164 / 10 778 | Expectancy ratio 0,00 · p-value 0,99 · buy&hold : +2 458 % |
| **B pur corrigé** (G1-G7) | **−17,38 %** | **0,72** | 187 | 7 959 / 10 380 | Win 28,3 % · durée moy. 4 h 30 · DD max 23,3 % |

Lecture : **A corrigé ≠ le A du 11/07**. L'ancien « A +40 %, PF 2,12, 55 trades, positions 37 j » était du bag-holding sans stop. Avec le SL actif : 128 trades (les slots se libèrent), positions de 14 h en moyenne pour les gagnants, et **zéro edge**. Côté B : **−17,4 % ≈ le B buggé (−19,1 %)** — le bug SL ne touchait presque pas B (G2 pose un stop dès le premier pivot), donc la hiérarchie des ablations du 11/07 (G6 pire, G5 inerte…) reste valide. Le duel honnête devient : les G rules coûtent **~17,5 points** sur un substrat déjà nul, via le churn (187 vs 128 trades) et la conversion systématique de la respiration en pertes.

Par année d'entrée (A pur, somme des profits % par trade) :

| Année | n | Win % | Σ profit |
|---|---|---|---|
| 2018 | 9 | 44 % | +19,9 % |
| 2019 | 17 | 29 % | −7,2 % |
| 2020 | 21 | 33 % | −7,6 % |
| 2021 | 21 | 57 % | **+65,4 %** |
| 2022 | 2 | 0 % | −5,5 % |
| 2023 | 19 | 42 % | +2,6 % |
| 2024 | 19 | 42 % | +4,7 % |
| 2025 | 15 | 40 % | −3,2 % |
| 2026 | 5 | 20 % | +0,2 % |

### 1.2 R-space : 12 politiques de gestion sur les 123 épisodes corrigés

Outil : `research/edge_2026-07/policy_sim.py` (analyse pure, produit intouché) sur les trajectoires du replay (`analysis/out/a_pur_20260719/`). Conventions conservatrices (stop avant target intrabar, trailing sur clôture 1h, stop jamais abaissé, frais ignorés — identiques pour toutes).

| Politique | E (R/épisode) | Win % | Max R | Stops % |
|---|---|---|---|---|
| HOLD (SL initial seul, horizon 90 j) | **+4,18** | 11 % | 128 | 89 % |
| TP1 50 % + giveback 50 % (armé ≥ +3R) | **+0,26** | 41 % | 31 | 78 % |
| TP1 + giveback 50 % + BE | +0,22 | 41 % | 31 | 85 % |
| TP1 + chandelier 8×ATR(1h) | +0,04 | 41 % | 14 | 100 % |
| **A (TP fixe +1,5R)** | **+0,02** | 41 % | 1,5 | 59 % |
| A + time-stop 24 h | +0,01 | 40 % | 1,5 | 59 % |
| B proxy (G1+G3+G4+G7) | −0,01 | 46 % | 4,5 | 98 % |
| TP1 + BE + chandelier 5×ATR | −0,02 | 41 % | 11 | 100 % |
| TP1 + giveback 33 % | −0,04 | 41 % | 5 | 77 % |
| TP1 + chandelier 3×ATR | −0,08 | 41 % | 5 | 100 % |
| TP1 + chandelier 5×ATR + ts48 | −0,10 | 41 % | 11 | 99 % |
| TP1 + chandelier 5×ATR | −0,11 | 41 % | 11 | 100 % |

**Les trois faits durs :**
- **Tout trailing à l'échelle 1h est ≤ 0**, même très large (8×ATR) : la respiration normale d'un trade crypto post-burst mange n'importe quel stop 1h avant que la queue paie. C'est cohérent avec la microstructure (mèches de chasse aux liquidations, §3).
- **L'espérance vit dans la queue extrême** : continuation médiane après +1,5R = +4,6R, p75 +21R, p90 +67R… mais giveback médian pic→creux = 5,3R. Capturer la queue sans rendre 5R est géométriquement impossible avec un trailing serré.
- **Fragilité** : le +0,26R du giveback = UN trade (ETH 08/02/2024, run-up ETF, +31R). Sans lui : +0,00R. Sans le top 3 : −0,17R. Par cohorte : −0,47R (2018-20), +0,50R (2021-22), +0,75R (2023-26, = le trade ETH). **Aucune politique n'est robuste sur un substrat d'entrées à espérance nulle** — c'est le théorème martingale de docs/01 §Limite honnête, vérifié sur 8,5 ans.

### 1.3 La vraie découverte : la géométrie stop/burst (côté ENTRÉE)

Les gagnants ne reviennent presque jamais en arrière : MAE médian **−0,25R**, p75 −0,15R (n=51). Le stop structurel 03.3 (« sous le dernier HL 4h − 0,1 ATR ») paie donc pour une protection que les gagnants n'utilisent pas. Test à risque constant (sizing = risque fixe ÷ distance de stop) :

| Stop initial | Win % | E par unité de risque |
|---|---|---|
| distance structurelle (actuel) | 40,7 % | **+0,016** |
| × 0,5 | 33,3 % | **+0,333** (×20) |
| × 0,33 | 23,6 % | +0,307 |

Brut (sans frais, granularité 1h, sans re-entrées). Les frais rognent ~0,15-0,20R à demi-distance → net ≈ +0,15/+0,20R, toujours ~10× l'actuel. **Chantier prioritaire proposé** : re-run replay 5m avec stops fractionnaires + modélisation frais, puis si confirmé, amendement 03.3 (décision Jonas). Ce n'est PAS du hyperopt G1-G7 (interdit n° 5) : c'est la géométrie du stop initial, périmètre D2.

---

## 2. Proposition G rules v2 (à valider — rien d'appliqué)

**Principe directeur** : la gestion doit épouser le profil empirique de l'edge (burst rapide + queue grasse + respiration large), pas le contredire. Et elle ne se réintroduit **qu'après** un edge d'entrée > 0 démontré (ordre du §5).

| Règle | Verdict | Proposition | Preuve |
|---|---|---|---|
| G1 BE +1R | ❌ supprimer | Le BE à +1R transforme la respiration normale en sortie à ~0 ; l'ablation du 11/07 la donnait déjà nuisible (+3,8 pts sans elle) | ablations 11/07 + B_proxy R-space |
| G2 trailing structurel 1h | ❌ supprimer | Échelle 1h = mangée par les mèches ; toute la classe « trailing 1h » est ≤ 0 en R-space | §1.2 |
| G3 trailing ATR 1h | ❌ supprimer | Idem, même à 8×ATR | §1.2 |
| G4 TP partiel 50 % @ +1,5R | ✅ garder | Seule brique « income » compatible avec la queue ; win 41 % × +1,5R sécurise pendant que le reste court | §1.2 |
| G5 extension post-BOS | ❌ supprimer | Strictement inerte (jamais déclenchée en 8,5 ans) | ablations 11/07 |
| G6 CHoCH 1h | ❌ supprimer | De très loin la pire (+20 pts retirés en ablation) ; l'événement 1h est du bruit à cette échelle | ablations 11/07 |
| G7 time-stop 24 h | ⚪ garder (hygiène) | Impact ≈ 0 (−0,01R) mais libère les slots — utile en portefeuille ; assouplissable à 48 h | §1.2 |
| **NOUVEAU : G-giveback** | ➕ à tester | Armé quand pic ≥ +3R ; sortie du reste si retrace depuis le pic > max(1,5R, 50 % du pic). Seule politique > 0 sur 2021-22 ET 2023-26 ; fragile aujourd'hui car le substrat est nul — à re-mesurer sur l'edge réparé | §1.2 |

Chaque changement = amendement docs/03 + décision signée, comme pour G6 le 10/07. Les flags d'ablation existants permettent de backtester le set proposé sans toucher aux défauts (`ARIT_G_OFF` étendu à une liste — seule modif de code nécessaire, mineure, à valider).

---

## 3. Volet marché — qui bouge réellement les prix (2024-2026)

### 3.1 Les institutions via ETF : le nouveau courant de fond
- IBIT (BlackRock) + FBTC (Fidelity) + Grayscale ≈ 89 % des encours ETF US ; les ETF spot US détiennent ~1,3 M BTC. Les flux de création/rachat frappent le carnet spot directement (les AP doivent sourcer les coins).
- **57 % des actifs ETF déclarés (13F) sont chez des investment advisors** — pas des hedge funds. Ils font du rebalancing de portefeuille : ils ACHÈTENT les dips pour maintenir l'allocation cible. Conséquence mesurable : compression de l'amplitude (max +240 % YoY ce cycle vs ≥ +1 000 % avant) et amortissement des cassures — le carburant du breakout-continuation.
- Avril 2026 : 19 000 BTC absorbés en 9 jours par les ETF = 9× le minage de la période. Les flux ETF quotidiens (publics, gratuits : Farside/CoinGlass) sont devenus LE signal court-terme dominant.

### 3.2 Les dealers d'options : le pinning au gamma
- Quand les dealers sont longs gamma, leur hedging mécanique (vendre les hausses, acheter les baisses) **épingle le prix** entre les strikes chargés. Mesuré fin 2025 : ~507 M$ de gamma dealer vs ~38 M$ de flux ETF quotidiens — ratio 13:1. Le marché peut rester scotché des semaines (85-90 k$ en déc. 2025) jusqu'à l'expiry.
- Le **gamma flip** (passage en zone gamma négative) inverse le régime : les hedges amplifient au lieu d'amortir → les mouvements s'auto-renforcent. C'est exactement la fenêtre où un edge breakout paie. Un filtre de régime gamma est une idée d'edge à part entière (§4, idée 6).

### 3.3 Les whales et la mécanique des perps
- Le prix se découvre majoritairement sur les perps. Funding positif = les longs paient (levier long chargé) ; négatif = stress/capitulation.
- **Chasse aux liquidations** : les acteurs capitalisés poussent le prix vers les clusters de liquidation/stops connus (heatmaps publiques), déclenchent la cascade, et se servent dans la volatilité. Les mèches 1h qui mangent les trailing stops serrés ne sont pas du bruit : c'est un comportement adverse structurel. → Confirme la suppression de la couche de gestion 1h (§2) : nos stops 1h resserrés étaient de la nourriture à cascade.
- Funding **négatif prolongé** après une chute = signal de bottom contrarian documenté (mars 2020, fin 2022, post-FTX) — pertinent pour du spot long-only.
- On-chain (inflows exchanges, whale ratio) : signaux probabilistes, laggy, données révisées a posteriori — faible alpha isolé, utile en confluence seulement.

### 3.4 Anomalies horaires persistantes
- « Monday Asia open » (dimanche 22h-23h UTC) statistiquement significatif ; liquidité/spreads meilleurs pendant les heures US ; week-ends = retail + mèches. Un simple filtre de fenêtre d'entrée est testable gratuitement sur nos données (idée 2, §4).

### 3.5 Ce que ça implique pour ARIT
Le BOS-continuation 4h long-only affronte : des advisors qui achètent les dips (moins de départs en tendance nets), des dealers qui épinglent (cassures avortées), des whales qui chassent les stops (gestion serrée punie). **Il paie quand : gamma négatif / expiry passé, funding reseté, régime macro non hostile.** L'edge V1 n'a de sens qu'équipé de filtres de régime — pas en aveugle.

---

## 4. Idées d'edge — de l'actionnable à l'idéaliste

Tags : **[V1]** = intégrable tel quel (données déjà en base, déterministe) · **[V1.1]** = infra légère (un fichier d'état de plus) · **[V2]** = données/infra nouvelles · **[IDÉALISTE]** = exploratoire, signalé comme demandé. Le « déjà fait ailleurs » est signalé aussi.

1. **[V1] Géométrie stop/burst** (§1.3) — le levier interne n° 1, zéro donnée externe, ×20 brut à confirmer. *Inexploré chez nous, peu documenté ailleurs sous cet angle (la littérature optimise le trailing, pas le ratio stop-initial/profil-de-burst).*
2. **[V1] Filtre de fenêtre d'entrée** — n'entrer que dans les fenêtres historiquement porteuses (Asia open dimanche/lundi, heures US) ; backtest immédiat sur nos bougies. *Déjà documenté académiquement, jamais testé sur NOS entrées.*
3. **[V1.1] Véto macro HOSTILE seul** — déjà mesuré chez nous (B : −19,1 % → −7,0 %, DD 24,9 → 10,6) : garder le véto, retirer la pénalité NEUTRE et le funding du score composite. C'est la décision déjà sur la table du 17/07 — ce rapport la confirme.
4. **[V1.1] Funding extrême contrarian** — funding négatif prolongé (série Binance 2019+, déjà téléchargée pour la macro V1.1) comme **débloqueur d'entrées** en bas de cycle plutôt que comme composant de score (son usage actuel dans le score est contre-productif, cf. verdict du 17/07). *Documenté ailleurs, pas chez nous.*
5. **[V1.1] Polymarket comme couche événementielle** — l'arbre v0 a échoué faute de données de consensus/surprise ; **les prix Polymarket SONT ce consensus**, timestampés, gratuits, historisables (`/prices-history`). Usage : régime taux (ex. live du 19/07 : Fed no-change juillet 94 %, zéro baisse 2026 85 %, hike 2026 54 % → HOSTILE), fenêtres d'événements binaires (shutdown, ETF altcoins), et à terme surprise = |prix veille − résolution|. Contrainte réelle : domaine DNS-bloqué en France (ANJ) — lecture contournable proprement (résolveur alternatif), mais c'est une dépendance d'infra à assumer et re-tester. *Quasi inexploré en systématique crypto — notre POC arbre v0 + cette source = combinaison originale.*
6. **[V2] Régime gamma dealers (GEX)** — filtre « pinning vs flip » : n'autoriser les entrées breakout qu'en zone gamma favorable / post-expiry. Données : Deribit/fournisseurs (Amberdata, Glassnode taker-flow GEX) — payant ou scraping. *Standard chez les pros equities, encore peu en crypto systématique retail.*
7. **[V2] Flux ETF quotidiens comme input macro crypto-native** — creations/redemptions (Farside, gratuit, J+0) en remplacement partiel du score macro actuel ; s'aligne avec ta décision du 11/07 (données crypto-natives).
8. **[V2] Entrée post-cascade de liquidations** — acheter la sur-extension après cascade (mèche + OI purgé + funding reset) : l'exact inverse de notre breakout, adapté au régime range/pinning. Données liquidations/OI : CoinGlass. *Documenté, non testé chez nous.*
9. **[IDÉALISTE] Suivi de wallets whales en temps réel** (clustering on-chain, copy d'accumulation) — infra lourde, faux positifs custody, alpha en décroissance : documenté comme non prioritaire.
10. **[IDÉALISTE] Trader le biais haussier systématique des marchés de prix Polymarket** — le biais est documenté, mais trader Polymarket depuis la France est bloqué (ANJ) : non actionnable légalement, listé pour mémoire.
11. **[IDÉALISTE] Micro-latence / MEV / cross-exchange** — hors classe de taille et d'infra d'ARIT, listé pour cartographie.

---

## 5. Ordre de chantier proposé (répond à D1, actualisé)

1. **Réparer l'entrée** : replay 5m stops fractionnaires (idée 1) + filtres de régime gratuits (idées 2-4) — objectif : un contrôle A' avec E > 0 net et p-value < 0,05 avant toute autre chose.
2. **Re-protocole A/B propre** sur l'edge réparé (lanes, macro neutralisée, `ARIT_G_OFF` liste).
3. **G-set v2** (§2) mesuré CONTRE A' — réintroduction règle par règle, décision signée à chaque fois.
4. **Couche événementielle Polymarket** (idée 5) : spec docs/06 d'abord, collecte historique, backtest par-dessus l'edge réparé.
5. V2+ : GEX, ETF flows, post-cascade (idées 6-8) selon résultats.

## 6. Annexes

- **Artefacts** : zips → `backtest_lanes/run1` (A pur 19/07) et `run3` (B pur 19/07) ; replay → `analysis/out/a_pur_20260719/` ; politiques → `research/edge_2026-07/out/*.csv` ; snapshot Polymarket → scratchpad session (repris dans ce rapport).
- **Reproduction** : commandes §1 (protocole) + `policy_sim.py --help`.
- **Hygiène** : `user_data/data/macro` restauré après la campagne ✔ · le webhook Discord a transité en clair dans une conversation antérieure → à régénérer avant le canari (note du 08/07, toujours valable).
- **Sources web (principales)** : Amberdata (flux institutionnels 2026) · Intellectia/KuCoin/CoinGlass (ETF flows) · CCN/Glassnode/BeInCrypto (gamma exposure, déc. 2025) · Solidus Labs (méltdown 20 Md$ liquidations) · QuantPedia (seasonalité, trend BTC) · QuantifiedStrategies (weekend effect) · docs Polymarket (Gamma/CLOB API) · Kraken/Bitget/AInvest (funding contrarian).
