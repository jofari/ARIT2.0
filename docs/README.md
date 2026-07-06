# ARIT — PDR v3 (dossier de spécification pour Claude Code)

> **Statut : SPÉCIFICATION VERROUILLÉE.** Zéro question ouverte. Toute ambiguïté rencontrée pendant le code = demander à Jonas, jamais improviser.
> **Mode d'emploi Claude Code** : lire ce README en entier, puis lire le fichier de la couche concernée AVANT de coder chaque module. Discovery-first : poser les questions avant d'écrire du code.

## Ordre de lecture
1. `01_edge.md` — POURQUOI le bot existe (hypothèse signée, test A/B central)
2. `02_architecture.md` — structure globale, mermaid, mapping freqtrade, layout repo
3. `03_risque.md` — sizing, garde-fous, règles de gestion G1-G7 (LE cœur)
4. `04_cio_regimes.md` — régimes de marché, profils de poids, formule de conviction
5. `05_features.md` — formules exactes de chaque feature technique
6. `06_vetos_data.md` — news blocker, sentiment, liquidité, macro_state
7. `07_execution_config.md` — config freqtrade précise, environnement local Windows
8. `08_journal_hitl.md` — journal de décision, Discord, véto humain (phase canari)
9. `09_validation_deploy.md` — protocole A/B, seuils, phases de déploiement
10. `10_backlog_v2.md` — ce qu'on ne code PAS maintenant (dont 1 NE PAS IMPLÉMENTER)

## Décisions verrouillées (récapitulatif)
| Sujet | Valeur |
|---|---|
| Chassis | **freqtrade** (dry-run d'abord), stratégie `AritV1` |
| Instrument | **Binance spot long-only**, stake **USDT** |
| Pairlist V1 (statique) | BTC/USDT · ETH/USDT · SOL/USDT · BNB/USDT |
| Timeframes | Base stratégie **1h** · setup/entrées sur **4h** (informative, clôtures seulement) · contexte 1d · backtest `--timeframe-detail 5m` |
| Risque/trade | Mapping conviction : **1 % → 2 %** (100 premiers trades), puis **1 % → 3 %** |
| Sizing | Sur **équité courante** (compounding) |
| Positions max | **3** simultanées · **risque résiduel total ≤ 6 %** · jamais clôturer un trade pour en ouvrir un autre |
| Budget hebdo | **≤ 8 % de risque initial engagé / semaine ISO (UTC)** et **≤ 10 entrées / semaine** |
| RR d'entrée | **≥ 1,5 obligatoire** sinon pas de trade |
| Gestion | **G1-G7** (voir 03) — défauts FIGÉS, flags d'ablation, jamais hyperoptées |
| SL | Ne bouge JAMAIS dans le sens défavorable + `stoploss_on_exchange` |
| Circuit breakers | Jour : **−6 %** équité (00:00 UTC) · Séquentiel : 2 SL consécutifs → cooldown + risque ÷2 (5 trades) |
| Décision | Gates (veto) → régime → vote pondéré par profil de régime → conviction → sizing |
| LLM | **AUCUN dans le runtime.** Claude = outil de dev uniquement |
| ML (V2) | FreqAI batch, modèles figés, gate de promotion OOS. Jamais d'online learning |
| Notifications | **Discord** (webhook) — pas Telegram |
| HITL | Journal exhaustif + notifications ; véto Discord actif en phase canari uniquement (jamais d'approbation bloquante) |
| Capital | Dry-run wallet **10 000 USDT** = capital canari prévu (10 k) |
| Hébergement | Dev + dry-run : **local** (Windows, machine de Jonas). Capital réel : machine always-on OBLIGATOIRE (gate, voir 09) |
| Validation | Backtest historique max (2017+) PF ≥ 1,3, DD ≤ 15 %, ≥ 100 trades · Dry-run **6 mois**, ≥ 50 trades, PF ≥ 1,3, DD ≤ 10 % |

## Interdits absolus (à respecter dans TOUT le code)
1. Aucun appel LLM dans le runtime.
2. Le SL ne s'élargit jamais (freqtrade l'impose déjà via `custom_stoploss` ; ne pas contourner).
3. Aucun look-ahead : les colonnes 4h/1d utilisées en 1h passent par `merge_informative_pair` standard (clôtures seulement).
4. Aucune valeur magique non documentée : tout paramètre vient de ce dossier ou est ajouté ici d'abord.
5. Les défauts G1-G7 et les profils de régime ne passent JAMAIS en hyperopt.
6. Chaque évaluation d'entrée (prise OU refusée) écrit une ligne de journal (voir 08).
7. `dry_run: true` tant que la §09 ne dit pas autrement. Clés API sans droit de retrait.


## v3.1 — Couche d'implémentation (détail des modules)
- `11_sync_orchestration.md` — cadences, contrats de données (noms de colonnes/custom_data/fichiers d'état), séquence d'entrée, règle réseau, véto non-bloquant.
- `modules/M01…M10` — architecture interne de chaque module : libs exactes, signatures, algorithmes pas-à-pas, lien à l'edge, invariants, tests pytest exigés.
Ordre de lecture pour CODER un module : `README` → `02_architecture` → `11_sync_orchestration` → `modules/MXX` du module → le fichier de couche correspondant (03-08).

## Glossaire minimal
**R** = risque initial du trade (distance entrée→SL en % équité). **BOS** = break of structure (cassure du dernier swing high, clôture 4h). **CHoCH** = change of character (cassure du dernier higher-low). **HL/HH** = higher low / higher high (pivots fractals). **Risque résiduel** = perte max encore possible sur une position (0 si SL ≥ entrée). **Conviction** = score final ∈ [0,1] sortant du CIO.
