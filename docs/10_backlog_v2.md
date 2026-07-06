# 10 — Backlog V2+ (rien de tout ceci ne se code en V1)

## ⛔ Copy-trading des gros portefeuilles (idée 6 de Jonas) — DOCUMENTÉE, **NE PAS IMPLÉMENTER**
Concept : suivre les N portefeuilles les plus performants (ex. top 10) et intégrer leurs positions dans le score de confiance des actifs.
Raisons du gel (à relire avant toute réévaluation) : (1) **biais du survivant** massif dans les classements de rendement — les leaders tournent, souvent chanceux/leveragés ; (2) **latence** : une position visible est déjà vieille ; (3) accès aux données verrouillé (ToS exchanges, APIs payantes, wallets on-chain ≠ intentions).
Critères de réévaluation V2 : source de données fiable et légale disponible + intégration comme simple **feature** dans FreqAI (jamais un signal autonome) + doit améliorer l'OOS sinon rejet définitif.

## FreqAI — méta-modèle de conviction (le "vert" principal)
Dataset : le journal JSONL (08) — évaluations, scores, features CDL*, labels = résultat des trades ET des skips reconstruits. Modèles : LightGBM/XGBoost. Gate de promotion : battre les poids figés V1 en OOS (métrique composite Sortino + pénalité DD > 15 % + variance inter-folds). Promotion MANUELLE par Jonas. Jamais d'online learning (la doc FreqAI elle-même le déconseille).

## Autres éléments verts / extensions (dans l'ordre de valeur probable)
1. **Poids par régime appris** (extension directe de 04 — profils V1.5 figés d'abord, appris ensuite).
2. **HMM de régime** (hmmlearn, GaussianHMM sur rendements+range 4h) en remplacement/complément de la règle ADX.
3. **Modèle MAE/MFE** (FreqAI regressor) pour optimiser G3/G4 — données = ton propre dry-run (aucun modèle public n'existe ni ne peut exister).
4. **¼ Kelly capé 3 %** = calibration du mapping conviction→risque quand ≥ 100 trades réels.
5. **NLP macro** : FinBERT zero-shot (ProsusAI/finbert) + hawkish/dovish pré-entraîné (gtfintechlab/FOMC-RoBERTa) pour enrichir macro_state.
6. **Stratégie RANGE** (le bot ne fait rien en range en V1 — une stratégie mean-reversion S/R est un module séparé, avec son propre A/B).
7. Perps/shorts (funding modélisé) · IBKR/forex (attention volume=proxy) · profondeur de carnet · Nautilus/moteur maison SEULEMENT si freqtrade bride une fonctionnalité précise et documentée.

## Rappel de méthode
Chaque élément V2 suit le même chemin : spec ici → backtest A/B contre la V1 en place → gate OOS → promotion manuelle. Aucune exception, y compris pour les idées séduisantes.
