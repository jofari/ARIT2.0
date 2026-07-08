# RAPPORT_BUILD — ARIT V1 · build v0.1.0

Date : 2026-07-08 · Orchestrateur : session Claude (Fable 5) + sous-agents arit-coder/reviewer/runner (Opus)
Repo : `C:\Users\jofar\OneDrive\Bureau\ARIT2.0` · GitHub : `https://github.com/jofari/ARIT2.0` (branche `main`)

## 1. Synthèse
Les 10 modules du PDR v3 sont codés, testés, reviewés et committés. Les 3 gates sont PASS.
**146 tests pytest, 100 % verts · ruff propre · backtest smoke sans exception.**
Le bot n'a PAS été lancé en dry-run (hors mission) ; aucune clé API réelle n'est configurée.

## 2. Fait — avec preuves

| Livrable | Preuve |
|---|---|
| Phase 0 : docs/ (22 .md), venv 3.12 + freqtrade 2026.6, git, .gitignore, .env.example, PLAN.md, BUILD_NOTES.md | commit `phase0` ; `freqtrade --version` lors de l'install |
| Phase 1 : `params.py` (constantes PDR sourcées), `contracts.py` (11.3, TradeState, événements 08.1, signal_id), `conftest.py` seedé | commit `a98a082` ; **GATE G0 PASS** (ruff « All checks passed! », collect sans erreur d'import) |
| M01 features (+ anti-look-ahead ×2, idempotence) | 14 tests ; review PASS ; commit `a9619c7` |
| M02+M03 regimes/cio | 33 tests ; review FAIL→corrigé (FG_NEUTRAL_BACKTEST) ; commit `f1cfc87` |
| M04 risk | 22 tests ; review FAIL→corrigé (CB séquentiel via DB, borne −6 %, métriques skips) ; commit `3c9fb03` |
| M05 gestion (G1-G7 + flags ablation) | 15+4 tests ; review FAIL→corrigé (G4 = 50 % de la quantité) ; commits `3aa0e00`, `82882fc` |
| M06 journal (append-only, schema_version) | 8 tests ; review FAIL→corrigé (pair explicite) ; commit `faa798f` |
| **GATE G1 PASS** : pytest 92/92 (alors) · zéro import croisé arit_lib (grep : contracts/params uniquement) · anti-look-ahead vert | tour du 07/07, PLAN.md §Phase 2 |
| M07 AritV1.py : **245 lignes**, zéro réseau dans les callbacks, garde `new_4h`, exceptions module ⇒ action sûre + journal | 15+1 tests ; review FAIL→5 correctifs vérifiés (dont TP2 figé, `gestion.initial_levels`) ; commit `82882fc` |
| M08-M10 services : write atomique, watchdog stdlib-only, token env only | 32 tests ; review FAIL→5 correctifs vérifiés (dont anti-fuite clé Finnhub testé, véto fail-closed) ; commit `9a2b556` |
| config.dry.json (valeurs contractuelles 07.1, `dry_run: true`) | vérifiée ligne à ligne vs docs/07 ; smoke la charge sans erreur |
| **GATE G2 PASS** : backtest smoke BTC/USDT 30 j `--timeframe-detail 5m` terminé sans exception (~7,3 s) | run 2 du 08/07 (runner) ; run 1 FAIL documenté BUILD_NOTES |
| CLAUDE.md racine + arit_lib/CLAUDE.md · README.md | commits `82882fc`, `44f5809` |
| GitHub `main` + push de tout l'historique | `git push -u origin main` 08/07 ; règle « push après chaque commit » |

## 3. Non fait (volontairement — hors mission)
Download 2017+ complet · backtest complet + protocole A/B · dry-run lancé · hyperopt · clés API réelles ·
tout le backlog v2 (copy-trading : NE PAS IMPLÉMENTER) · script de lancement unifié des 4 process (non spécifié — question 5).

## 4. Écarts vs PDR — liste exhaustive (aucun écart silencieux)
**Extensions de contrat actées au build (à valider par Jonas) :**
1. `signal_id` normalisé Windows : `BTCUSDT-20260706T120000Z` (`/` et `:` interdits en nom de fichier).
2. `TradeState` = 12 champs (11.3 + `tp2`) — M05 en listait 9.
3. `contracts` étendu : `CB_DAY_FILE`, `VETO_INTENT_SUFFIX`, `VETO_FLAG_SUFFIX`, `SKIP_ZERO_STOP_DISTANCE`.
4. `compute_stake -> (stake|None, raison|None)` (M04 disait `-> float`) — nécessaire pour journaliser `skip_min_notional`.
5. Clé custom_data `tp2` ajoutée (docs/11 §11.3 amendé) — TP2 figé à l'entrée (review M07, PDR 03.3).
6. `WATCHDOG_DUST_THRESHOLD_USDT = 1.0` — le PDR ne fixait aucune valeur de dust.
7. `ev_evaluation` scopé live/dry (décision Jonas 08/07, docs/08 amendé) — le backtest garde gate_check/entry/exit.

**Écarts fonctionnels assumés (non bloquants en dry-run) :**
8. Gate spread (03.2.3) INERTE : `spread_frac=None` journalisé — pas de source spread sans réseau dans les callbacks. **À résoudre avant canari** (service fichier d'état spread, modèle macro_state).
9. Bollinger(20,2)_1h calculées (params) mais non émises/journalisées — 11.3 et 08.1 ne les câblent pas ; les câbler = étendre 11.3 + 08.1 d'abord.
10. `hh_hl_intact_4h`, `pivot_high_4h`, `pivot_low_4h` présents sur le df mergé mais hors `FEATURE_COLUMNS` (usage interne features, jamais décisionnels bruts) — écart de documentation.
11. `s_structure` « contexte TREND » = conditions prix seules (ADX≥25, EMA50>EMA200, close>EMA50) — features.py est pur, sans macro_state ; le veto macro reste dans regimes.
12. Formule SL : `gestion.initial_levels` référence **entry** (PDR 03.3) ; `features.rr_available` référence close (estimation pré-entrée) — divergence documentée en docstring.
13. Digest Discord sans « positions ouvertes avec R courant » (M09/08.2) — non dérivable du seul JSONL depuis un process séparé.
14. Alerte « Discord down > 15 min » (`DISCORD_DOWN_ALERT_MIN`) non implémentée dans le watchdog.
15. `state/watchdog_flattened` (idempotence flatten, reset manuel) — fichier interne hors 11.3.
16. `FG_BACKOFF_BASE_S = 2` (infra macro_state) non fixé par le PDR.
17. Littéraux tolérés dans AritV1 : `stoploss = -0.99` (squelette freqtrade), `"user_data"` (chemin).

**Environnement / config :**
18. config.dry.json : blocs `telegram`/`api_server` RETIRÉS (schéma 2026.6 exige leurs champs même `enabled:false`). Pour le dry-run réel : réintroduire `api_server` (FreqUI 127.0.0.1, credentials locaux non commités).
19. venv : `scipy` ajouté (requis par freqtrade, non tiré à l'install) ; `aiodns` RETIRÉ (c-ares ne résout pas le DNS sur cette machine — ne pas le réinstaller). Détail : BUILD_NOTES.
20. `discord.py` non installé dans le venv (import optionnel dans le service) — à installer avant le dry-run avec bot Discord.
21. docs/ = 22 fichiers (le prompt de build en annonçait 23).

## 5. Questions ouvertes pour Jonas
1. **Priorité BOS vs CHoCH** (s_structure) : un CHoCH baissier pendant la fenêtre `bos_fresh` d'un BOS haussier en TREND donne s_structure = 1,0 — la spec 05.1 ne tranche pas ce conflit. OK ou CHoCH prioritaire ?
2. **Valider les extensions de contrat** n°1-7 ci-dessus (sinon dire lesquelles reprendre).
3. **Spread avant canari** : OK pour un petit service `spread_state` (fichier d'état, modèle macro_state) en V1.1 ?
4. **Bollinger** : les câbler dans 11.3 + 08.1, ou les retirer de params ?
5. **Script de lancement** des 4 process (bot + 3 services) : souhaité ? (non spécifié dans docs/ — pas improvisé.)
6. **Digest « R courant »** : ajouter un fichier d'état écrit par le bot pour le bot Discord, ou s'en passer ?

## 6. Commandes prêtes pour la suite
```powershell
# 1. Données complètes (BTC/ETH ≈ 2017+, SOL ≈ 2020+) — RÉSEAU : hors sandbox
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe download-data --exchange binance `
  -p BTC/USDT ETH/USDT SOL/USDT BNB/USDT -t 5m 1h 4h 1d --timerange 20170801-

# 2. Backtest complet (produit B = G1-G7 ON, défaut)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy AritV1 `
  -c user_data/config.dry.json --timerange 20180101- --timeframe-detail 5m --cache none

# 3. Protocole A/B (docs/09 §9.1) — contrôle A : entrées/SL identiques, TP fixe +1,5R sortie
#    totale, AUCUNE G-rule. Les flags G1-G7 existent (params.G_FLAGS_DEFAULT + gestion.py) ;
#    le MODE A complet (TP fixe sortie totale) nécessite un petit toggle non encore exposé
#    (env/config) — à câbler avant le run A/B (5 lignes, sans hyperopt). Puis :
#    7 runs d'ablation (B moins chaque Gx) ; sous-périodes 2018-2020 / 2021-2022 / 2023-2026.

# 4. Dry-run (6 mois, ≥ 50 trades — docs/09 §9.2 ; veille Windows désactivée ;
#    réintroduire api_server dans la config d'abord ; pip install discord.py ; .env rempli)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe trade -c user_data/config.dry.json
# + les 3 services dans des fenêtres séparées :
& C:\Users\jofar\venvs\arit\Scripts\python.exe services\macro_state.py
& C:\Users\jofar\venvs\arit\Scripts\python.exe services\discord_bot.py
& C:\Users\jofar\venvs\arit\Scripts\python.exe services\watchdog.py
```

## 7. Incidents & leçons
Voir `BUILD_NOTES.md` (venv OneDrive, docs restaurés, scipy/aiodns, schéma config freqtrade,
`populate_exit_trend`, limites de session tuant les agents en vol → reprise par transcript).
