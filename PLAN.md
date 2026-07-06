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
- [ ] commit `phase0: env + plan`

## Phase 1 — Contrats (orchestrateur — verrou anti-dérive)
- [ ] `user_data/strategies/arit_lib/params.py` — TOUTES les constantes du PDR, source en commentaire (`# PDR 03.4 G3`)
- [ ] `user_data/strategies/arit_lib/contracts.py` — `COLUMNS` (docs/11 §11.3), `TradeState`, schémas événements journal (docs/08), format `signal_id`
- [ ] `tests/conftest.py` — générateur OHLCV synthétique seedé (tendance, range, gaps, mèches)
- [ ] Arborescence complète docs/02 §layout
- [ ] **GATE G0** (runner) : `ruff check` propre + `pytest --collect-only` OK
- [ ] commit `phase1: contrats`

## Phase 2 — Modules purs (5 × arit-coder EN PARALLÈLE, Opus)
| T | Spec | Produit | Statut |
|---|---|---|---|
| T1 | `modules/M01` + `05_features.md` | `arit_lib/features.py` + tests (dont anti-look-ahead) | ☐ |
| T2 | `modules/M02`+`M03` + `04_cio_regimes.md` | `regimes.py` + `cio.py` + tests | ☐ |
| T3 | `modules/M04` + `03_risque.md` | `risk.py` + tests | ☐ |
| T4 | `modules/M05` + `03_risque.md` | `gestion.py` + tests | ☐ |
| T5 | `modules/M06` + `08_journal_hitl.md` | `journal.py` + tests | ☐ |
- [ ] runner : pytest global (échec → renvoi au coder, max 2 allers-retours/module puis question à Jonas)
- [ ] reviewer sur chaque module (checklists du prompt de build)
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
