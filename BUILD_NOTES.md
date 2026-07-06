# BUILD_NOTES — leçons et décisions de build

## 2026-07-06 — venv hors OneDrive
**Décision** : venv à `C:\Users\jofar\venvs\arit`, pas dans le repo.
**Pourquoi** : le repo vit dans OneDrive ; un venv freqtrade ≈ dizaines de milliers de fichiers que OneDrive synchronise et verrouille (échecs pip aléatoires, CPU). `venv/` reste dans .gitignore au cas où.

## 2026-07-06 — docs/ restaurés depuis Downloads
`ARIT2.0\ARIT_PDR_v3\` (dézippé à la main) était incomplet : 11 fichiers, sans `modules/` ni `11_sync_orchestration.md` — la Phase 0 exigeait un STOP. Versions complètes trouvées dans `Downloads` : `ARIT_PDR_v3_1.zip` et `_v3_2.zip` sont hash-identiques → `docs/` extrait de `_v3_2`. Comptage réel : 22 .md (le prompt dit « 23 fichiers ») — écart signalé, non bloquant.

## 2026-07-06 — Phase 1 : trois décisions de contrat (à connaître avant de coder)
1. **`signal_id` normalisé Windows** : M06 dit `f"{pair}-{ts_4h}"`, mais le signal_id sert de nom de fichier (`user_data/veto/<signal_id>.flag`) et `/` + `:` sont interdits dans un nom de fichier → format retenu `BTCUSDT-20260706T120000Z` (`contracts.make_signal_id`).
2. **`TradeState` = 11 champs de 11.3** (pas les 9 de M05) : 11.3 est LE contrat custom_data ; M05 en omettait `trade_no` et `entry_conviction`, nécessaires au journal/sizing. Défini dans `contracts.py` (le prompt de build l'y place), gestion.py l'IMPORTE au lieu de le redéfinir.
3. **`s_structure` « contexte TREND »** (PDR 05.1) : features.py est pur et n'a pas accès au macro_state → « contexte TREND » = conditions prix du régime TREND (ADX≥25, EMA50>EMA200, close>EMA50). Le veto macro/F&G reste dans regimes.py. Écart documenté, à confirmer par Jonas au rapport.

## 2026-07-06 — sous-agents via l'outil Agent
Session lancée depuis `C:\Users\jofar` → les `.claude/agents/` du repo ne sont pas chargés (chargement au démarrage seulement). Reproduction fidèle : outil Agent, modèle Opus, spec du `.md` injectée en tête de prompt. Pour une future session : lancer `claude` DANS le repo.
