# REPRISE — prompt à coller pour reprendre le travail (n'importe quel modèle)

> Écrit le 2026-07-11 au soir. Jonas : colle le bloc ci-dessous tel quel comme premier
> message d'une nouvelle session Claude Code lancée DANS le repo. Réponds ensuite aux
> décisions D1-D6 quand tu es frais — rien n'est urgent, rien n'est bloqué.

---

Tu es l'orchestrateur du projet ARIT V1 — reprise de session. Repo :
C:\Users\jofar\OneDrive\Bureau\ARIT2.0 (lance-toi dedans ; venv : C:\Users\jofar\venvs\arit).

LIS DANS L'ORDRE avant toute action :
1. `guide.md` (carte du repo)
2. `for claude build/RAPPORT_PROTOCOLE_AB.md` (état analytique : verdict du protocole A/B,
   sous-périodes, recommandations, décisions D1-D6 en attente de Jonas)
3. `for claude build/BUILD_NOTES.md` (pièges : contamination d'état des backtests, lanes
   isolées backtest_lanes/, macro_state requis par le gate news, aiodns, --prepend…)
4. `for claude build/PLAN.md` (checklist du build — les 4 phases initiales sont closes,
   tag v0.1.0-build)

ÉTAT VÉRIFIABLE : `git log --oneline -5` · pytest attendu : `152 passed` ·
10 runs de backtest valides dans `backtest_lanes/run1..5/backtest_results/` (les DERNIERS
zips de chaque lane ; les zips de la nuit du 10-11/07 avant 13h57 sont des runs invalides).

SYNTHÈSE EN 5 LIGNES : le build V1 est fini et testé (10 modules, 3 gates PASS). Le protocole
A/B (docs/09 §9.1) est terminé : les ENTRÉES ont un edge (+40 % contrôle A, PF 2,12) mais la
GESTION G1-G7 le détruit (produit B −19 %) ; G6 est la pire règle, G5 inerte, BOS > CHoCH.
⚠️ Nuance clé : l'edge d'entrée gagne 2018-2022 mais PERD 2023-2026 (8 trades, PF 0,32).
AUCUNE config ne passe les gates §9.2 → interdiction de dry-run/live en l'état (PDR).

TRAVAIL DISPONIBLE (selon les réponses de Jonas aux D1-D6 du rapport) :
- Enquête 2023-2026 (analyser les 8 trades du contrôle A, run A sur 2023-2026 seul)
- Hyperopt d'entrée (docs/09 §9.3 : seuil TREND, ADX, displacement, fraîcheur BOS ;
  câbler l'espace hyperopt dans AritV1 d'abord — petit travail coder)
- Chantier macro crypto-native (amender docs/06+04 d'abord : DXY, stablecoins, funding,
  F&G historique — voir décisions D3-D5)
- POC « arbre de probabilité v0 » sur FOMC/CPI (D6)
- Correctifs V1.1 actés : gate news conscient du runmode · service spread_state ·
  digest R courant · câblage Bollinger · purge auto de l'état en début de backtest

RÈGLES INCHANGÉES : interdits de docs/README.md · spec d'abord (docs/) puis code · sous-agents
arit-coder/reviewer/runner pour le code des modules · constantes dans params.py uniquement ·
lanes de backtest TOUJOURS sous backtest_lanes/ avec état purgé avant chaque run · commits
atomiques en français · push après chaque commit · notifier Jonas sur Discord aux étapes
(webhook DISCORD_WEBHOOK_URL du .env ; helper : POST JSON {"content": ...} avec un
User-Agent custom, sinon 403) · réponses à Jonas en français.
