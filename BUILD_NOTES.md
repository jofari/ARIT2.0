# BUILD_NOTES — leçons et décisions de build

## 2026-07-06 — venv hors OneDrive
**Décision** : venv à `C:\Users\jofar\venvs\arit`, pas dans le repo.
**Pourquoi** : le repo vit dans OneDrive ; un venv freqtrade ≈ dizaines de milliers de fichiers que OneDrive synchronise et verrouille (échecs pip aléatoires, CPU). `venv/` reste dans .gitignore au cas où.

## 2026-07-06 — docs/ restaurés depuis Downloads
`ARIT2.0\ARIT_PDR_v3\` (dézippé à la main) était incomplet : 11 fichiers, sans `modules/` ni `11_sync_orchestration.md` — la Phase 0 exigeait un STOP. Versions complètes trouvées dans `Downloads` : `ARIT_PDR_v3_1.zip` et `_v3_2.zip` sont hash-identiques → `docs/` extrait de `_v3_2`. Comptage réel : 22 .md (le prompt dit « 23 fichiers ») — écart signalé, non bloquant.

## 2026-07-06 — sous-agents via l'outil Agent
Session lancée depuis `C:\Users\jofar` → les `.claude/agents/` du repo ne sont pas chargés (chargement au démarrage seulement). Reproduction fidèle : outil Agent, modèle Opus, spec du `.md` injectée en tête de prompt. Pour une future session : lancer `claude` DANS le repo.
