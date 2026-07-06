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
- [ ] commit `phase1: contrats`

## Phase 2 — Modules purs (5 × arit-coder EN PARALLÈLE, Opus)
| T | Spec | Produit | Statut |
|---|---|---|---|
| T1 | `modules/M01` + `05_features.md` | `arit_lib/features.py` + tests (dont anti-look-ahead) | 🔄 en cours (features.py écrit, tests en écriture) |
| T2 | `modules/M02`+`M03` + `04_cio_regimes.md` | `regimes.py` + `cio.py` + tests | ✅ reviewé FAIL→corrigé (FG_NEUTRAL_BACKTEST), 33 tests |
| T3 | `modules/M04` + `03_risque.md` | `risk.py` + tests | ✅ reviewé FAIL→corrigé (CB séq DB, metrics complètes, stale lecteur, borne −6 %, constantes contracts), 22 tests |
| T4 | `modules/M05` + `03_risque.md` | `gestion.py` + tests | ✅ reviewé FAIL→corrigé (G4 = 50 % de la quantité), 15 tests |
| T5 | `modules/M06` + `08_journal_hitl.md` | `journal.py` + tests | ✅ reviewé FAIL→corrigé (pair explicite, dumps gardé), 8 tests |
- [x] pytest global intermédiaire : 92 passed (T2-T5 + contrats), preuve tour du 06/07 22:5x
- [ ] runner : pytest global final (après T1)
- [x] reviewer sur T2/T3/T4/T5 (verdicts FAIL motivés → correctifs appliqués et re-vérifiés) ; review T1 restante
- [ ] **GATE G1** : pytest 100 % vert · zéro import croisé entre modules arit_lib (grep : un module n'importe que contracts/params) · anti-look-ahead présent et vert
- [ ] commit par module

## Phase 3 — Intégration (séquentiel)
- [ ] coder : `user_data/strategies/AritV1.py` (M07) — < 250 lignes, zéro logique métier
- [ ] coder : `services/macro_state.py` + `services/discord_bot.py` + `services/watchdog.py` (M08-M10) + tests
- [ ] orchestrateur : `user_data/config.dry.json` (07) · `CLAUDE.md` racine · `arit_lib/CLAUDE.md`
- [ ] **GATE G2 — smoke** : `freqtrade download-data` BTC/USDT 30 j (`-t 5m 1h 4h 1d`) puis `freqtrade backtesting --strategy AritV1 -c user_data/config.dry.json --timeframe-detail 5m` — critère : aucune exception
- [ ] commit `phase3: integration + smoke`

## Phase 4 — Rapport (orchestrateur)
- [ ] `RAPPORT_BUILD.md` : fait/non fait + preuves · écarts vs PDR (aucun silencieux) · questions ouvertes · commandes suivantes (download 2017+, backtest complet, A/B docs/09 §9.1, dry-run)
- [ ] commit final + tag `v0.1.0-build`

## Questions ouvertes à Jonas
- (aucune pour l'instant)
