# PLAN — Build ARIT V1 (checklist vivante)

> Ce fichier fait foi sur l'état du build. Chaque case cochée pointe une preuve (commande, test, commit).

## Contexte session
- Session orchestrée unique (Fable 5), lancée depuis `C:\Users\jofar` → les agents de `.claude/agents/` ne sont pas chargés nativement ; arit-coder/reviewer/runner sont reproduits via l'outil Agent (Opus), leurs specs `.md` injectées au prompt. `.claude/` copié dans le repo pour les futures sessions.
- venv : `C:\Users\jofar\venvs\arit` (Python 3.12.10, freqtrade 2026.6) — hors OneDrive, voir BUILD_NOTES.
- Repo : `C:\Users\jofar\OneDrive\Bureau\ARIT2.0`

## DAG
```
Phase 0 (env) ──► Phase 1 (contrats) ──► G0 ──► Phase 2 (T1..T5 en parallèle) ──► G1
                                                          │
                                                          ▼
                              Phase 3 (M07 → M08-M10 → config) ──► G2 ──► Phase 4 (rapport)
```

## Règle de session (08/07, demande Jonas)
- Remote GitHub : `https://github.com/jofari/ARIT2.0.git`, branche `main` (renommée depuis master).
- **Push après CHAQUE commit** (`git push`). Premier push fait le 08/07 (8 commits + README).

## Phase 0 — Env & plan (orchestrateur)
- [x] `docs/` complet : 22 .md dont `modules/` ×10 — restauré depuis `Downloads\ARIT_PDR_v3_2.zip` (hash-identique à `_v3_1.zip`)
- [x] `.claude/` copié (arit-coder, arit-reviewer, arit-runner)
- [x] venv 3.12 + freqtrade 2026.6 (preuve : `freqtrade --version` en fin de tâche d'install)
- [x] `git init` (repo imbriqué, indépendant du repo parent de `C:\Users\jofar`)
- [x] `.gitignore` + `.env.example`
- [x] PLAN.md + BUILD_NOTES.md
- [x] commit `phase0: env + plan` (30 fichiers)

## Phase 1 — Contrats (orchestrateur — verrou anti-dérive)
- [x] `user_data/strategies/arit_lib/params.py` — constantes PDR 03→09 + M08-M10, source en commentaire
- [x] `user_data/strategies/arit_lib/contracts.py` — colonnes 11.3, `TradeState` (11 champs), événements journal 08.1, gates 03.2, `make_signal_id`
- [x] `tests/conftest.py` — `make_ohlcv(kind)` seedé : trend / range / gaps / wicks + fixtures
- [x] Arborescence docs/02 §layout (+ pyproject.toml pour ruff/pytest ; ruff 0.15.20, pytest 9.1.1 dans le venv)
- [x] **GATE G0 PASS** (arit-runner, agent a8834234d750a9266) : `ruff check .` → « All checks passed! » · `pytest --collect-only -q` → exit 5 « no tests collected » (normal, zéro erreur d'import)
- [x] commit `phase1: contrats` (a98a082)

## Phase 2 — Modules purs (5 × arit-coder EN PARALLÈLE, Opus)
| T | Spec | Produit | Statut |
|---|---|---|---|
| T1 | `modules/M01` + `05_features.md` | `arit_lib/features.py` + tests (dont anti-look-ahead) | ✅ reviewé PASS (2 notes mineures → CDL_BULLISH déplacé dans params.py), 14 tests |
| T2 | `modules/M02`+`M03` + `04_cio_regimes.md` | `regimes.py` + `cio.py` + tests | ✅ reviewé FAIL→corrigé (FG_NEUTRAL_BACKTEST), 33 tests |
| T3 | `modules/M04` + `03_risque.md` | `risk.py` + tests | ✅ reviewé FAIL→corrigé (CB séq DB, metrics complètes, stale lecteur, borne −6 %, constantes contracts), 22 tests |
| T4 | `modules/M05` + `03_risque.md` | `gestion.py` + tests | ✅ reviewé FAIL→corrigé (G4 = 50 % de la quantité), 15 tests |
| T5 | `modules/M06` + `08_journal_hitl.md` | `journal.py` + tests | ✅ reviewé FAIL→corrigé (pair explicite, dumps gardé), 8 tests |
- [x] pytest global intermédiaire : 92 passed (T2-T5 + contrats), preuve tour du 06/07 22:5x
- [x] runner : pytest global final (07/07) : ruff « All checks passed! » · **92 passed** (cio 18 + features 14 + gestion 15 + journal 8 + regimes 15 + risk 22)
- [x] reviewer sur T1..T5 — T1 PASS (correctif mineur CDL_BULLISH → params.py) ; T2-T5 FAIL motivés → corrigés et re-vérifiés
- [x] **GATE G1 PASS** : pytest 92/92 vert · grep import-croisé arit_lib = zéro match (chaque module n'importe que contracts/params) · anti-look-ahead : `test_anti_lookahead_compute_all` + `test_anti_lookahead_etage_4h` verts
- [x] commit par module (M02-M06 : f1cfc87, 3c9fb03, 3aa0e00, faa798f ; M01 : commit features ci-dessous)

## Phase 3 — Intégration (séquentiel)
- [x] coder : `user_data/strategies/AritV1.py` (M07) — livré 08/07 : 249 lignes + `tests/test_strategy.py` (15 tests), 142 verts ; 2 points contractuels BUILD_NOTES confirmés câblés
  - review M07 : **FAIL** (TP2 non figé HIGH · ev_evaluation backtest MEDIUM · `_initial_levels` métier MEDIUM · garde custom_stoploss LOW · spread inerte = à tracer) → renvoi groupé (AR 2/2) avec le bloqueur G2
  - correctifs appliqués et **vérifiés par moi** (08/07) : `tp2` contractualisé (docs/11 §11.3 + contracts + TradeState) persisté `order_filled`/relu figé `custom_exit` (test dédié) · stub `populate_exit_trend` · `gestion.initial_levels` pure (4 tests, formule PDR 03.3 réf. entry, divergence vs rr_available documentée) · floor None si initial_sl absent · ev_evaluation scopé live/dry (décision Jonas 08/07, docs/08 amendé) — **245 lignes**, ruff propre, **146 passed**
- [x] coder : `services/macro_state.py` + `services/discord_bot.py` + `services/watchdog.py` (M08-M10) + tests — livrés 07/07, ruff propre + 32 tests verts (rapport coder)
  - review services : FAIL (fuite clé Finnhub possible dans les logs · dust 1.0 USDT magique · 3 LOW) → correctifs appliqués (aller-retour 1/2) et **re-vérifiés** : scrub `_scrub_finnhub_error` + 2 tests anti-fuite, dust miroir de `params.WATCHDOG_DUST_THRESHOLD_USDT`, `contracts.VETO_FLAG_SUFFIX` partagé (discord_bot + risk.py), véto fail-closed testé — ruff propre, **127 passed** global (07/07)
  - coder M07 tué 2× par la limite de session en cours de route — repris par SendMessage (transcript intact), livraison complète 08/07
- [x] orchestrateur : `user_data/config.dry.json` vérifié conforme docs/07 §7.1 (07/07) · `CLAUDE.md` racine + `arit_lib/CLAUDE.md` écrits (session du 06/07) — commit avec phase3
  - ⚠️ à vérifier à la review M07 : Protections freqtrade (CooldownPeriod, StoplossGuard/MaxDrawdown — 07 §7.1) vivent dans la stratégie sur freqtrade 2026, pas dans la config
- [ ] download-data smoke (BTC/USDT 30 j, 5m/1h/4h/1d) — 🔄 lancé 07/07 en arrière-plan
- [ ] **GATE G2 — smoke** : download-data fait (07/07, après fix scipy+aiodns) ; backtest `--timerange 20260607- --timeframe-detail 5m --cache none` — critère : aucune exception
  - run 1 (08/07) : FAIL ×3 bloqueurs — (a) schéma freqtrade 2026.6 : `telegram`/`api_server` avec `enabled:false` exigent quand même token/chat_id/username/password → blocs RETIRÉS de config.dry.json (absents = off ; pour le dry-run réel, réintroduire api_server avec credentials locaux, cf. 07.4) ; (b) `populate_exit_trend` manquant → corrigé au renvoi coder
  - run 2 (08/07) : **GATE G2 PASS** — backtest terminé sans exception (~7,3 s, 0 trade = sans importance) ; ETH/SOL/BNB sans données = simples WARNING, config intouchée ; warm-up 200 bougies normal
- [ ] commit `phase3: integration + smoke`

## Phase 4 — Rapport (orchestrateur)
- [ ] `RAPPORT_BUILD.md` : fait/non fait + preuves · écarts vs PDR (aucun silencieux) · questions ouvertes · commandes suivantes (download 2017+, backtest complet, A/B docs/09 §9.1, dry-run)
- [ ] commit final + tag `v0.1.0-build`

## Questions ouvertes à Jonas
- **features/s_structure — priorité BOS vs CHoCH (cas croisé)** : si un CHoCH baissier survient
  pendant la fenêtre `bos_fresh` (3 bougies 4h) d'un BOS haussier en contexte TREND, `np.select`
  donne priorité au BOS → s_structure = 1,0. La spec 05.1 ne tranche pas ce conflit ; le cas
  « BOS postérieur au CHoCH » est testé et correct. À confirmer si le cas croisé doit primer CHoCH.

## Écarts mineurs vs PDR (à reporter dans RAPPORT_BUILD)
- Services (review 07/07, écarts assumés non bloquants) : digest Discord sans « positions ouvertes
  avec R courant » (non dérivable du JSONL seul depuis un process séparé — M09/08.2) · alerte
  « Discord down > 15 min » (`DISCORD_DOWN_ALERT_MIN`) non implémentée dans le watchdog ·
  `WATCHDOG_DUST_THRESHOLD_USDT = 1.0` acté au build (PDR ne fixe pas de valeur) ·
  `state/watchdog_flattened` (flag interne idempotence flatten) hors 11.3 · discord.py optionnel
  à l'import (non installé dans le venv — à installer avant le dry-run).
- `hh_hl_intact_4h`, `pivot_high_4h`, `pivot_low_4h` existent sur le df mergé mais ne sont pas
  listés dans `contracts.FEATURE_COLUMNS` (usage interne à features/module_scores uniquement,
  jamais décisionnels bruts — écart de documentation, aucun impact runtime).
