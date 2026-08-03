# 08 — Journal de décision & humain dans la boucle (idée 5)

> Objectif (formulation Jonas) : pendant la phase de test, une **documentation détaillée, étape par étape, de la réflexion du bot** — ce qui le conduit à faire ou ne pas faire chaque chose. Ce journal sert trois usages : audit humain, détection de bugs, et futur dataset d'entraînement FreqAI (V2).

## 8.1 Journal JSONL (`user_data/logs/decisions/YYYY-MM-DD.jsonl`)
Une ligne par événement. Types et champs obligatoires :
- **`evaluation`** (chaque clôture 4h, par paire) : `ts_utc, pair, regime, regime_inputs{adx4h, ema50_4h, ema200_4h, close_vs_ema, fear_greed, macro_stale, macro_regime, equity_veto, equity_veto_reason}, scores{structure, momentum, sr, patterns, volume}, cdl_features{...toutes les CDL*...}, conviction, seuil, rr_dispo, decision("signal"|"no_signal"), raison`.
  **`schema_version = 2`** depuis le 2026-08-03 (décisions A4/A5) : `regime_inputs` gagne trois clés — `macro_regime` (PORTEUR|NEUTRE|HOSTILE, déclaré dans les contrats depuis le 12/07 mais jamais réellement écrit) et le couple `equity_veto`/`equity_veto_reason` du bloc corrélation (docs/06 §6.2.1). Ce sont ces clés qui rendent la porte macro **ablatable a posteriori** : un seul run permet de dériver « PORTEUR seul » et « non-HOSTILE » par filtrage, au lieu de figer le choix dans le code.
  Portée : **live/dry-run uniquement** — en backtest (populate vectorisé), `gate_check` + `entry`/`exit` suffisent, les `no_signal` ne sont pas journalisés (décision Jonas 2026-07-08, review M07).
- **`gate_check`** (si signal) : chaque garde-fou de 03.2 avec `pass|fail` + valeur mesurée (spread, résiduel_total, budget_semaine, entrées_semaine, slots, fenêtre_news). Décision finale `enter|skip` + gate fautif.
- **`entry`** : prix, quantité, risque %, stake, SL_initial, TP1, TP2, conviction, régime.
- **`gestion`** : chaque déclenchement G1-G7 : règle, ancien/nouveau SL ou action, profit courant en R.
- **`exit`** : cause (G4/G5-trail/G6/G7/SL/TP), R final, MAE, MFE, durée, frais, slippage mesuré.
- **`system`** : démarrages, CB déclenchés, stale calendrier, erreurs.
Règle : **un skip est journalisé aussi richement qu'une entrée** — c'est la moitié de la valeur du dataset.

## 8.2 Digest lisible
Chaque jour 08:00 UTC, `journal.py` génère un résumé Markdown (posté sur Discord) : évaluations, signaux, entrées/skips par gate, actions de gestion, PnL, positions ouvertes avec leur R courant. But : Jonas comprend en 1 minute ce que le bot a "pensé" sur 24 h.

## 8.3 Notifications Discord (PAS Telegram — décision Jonas)
- Canal : webhook Discord (intégration native freqtrade pour entry/exit + posts custom de `journal.py` pour le raisonnement).
- Messages riches : à l'entrée → régime, scores, conviction, risque %, SL/TP, RR. À la sortie → cause, R, MAE/MFE. Skips notables (gate budget/résiduel) → notification courte.

## 8.4 Véto humain — PHASE CANARI UNIQUEMENT
- **Dry-run : AUCUN véto** (notifications seulement) — le dry-run doit mesurer le bot seul, pas Jonas+bot.
- **Canari (capital réel)** : avant chaque entrée, `discord_bot.py` poste l'intention complète ; Jonas a **5 minutes** (config `veto_window_min`) pour réagir ❌. Sans réaction → exécution automatique. Mécanique : le bot Discord écrit `user_data/veto/<signal_id>.flag` ; `confirm_trade_entry` attend la fenêtre puis vérifie le flag. Chaque véto est journalisé avec motif (texte libre de Jonas).
- Jamais d'approbation obligatoire (un véto qui expire = go) : préserve le 24/7 et la parité backtest/live. Les vétos de Jonas sont des données (journalisées), pas le mécanisme d'apprentissage.

## 8.5 Rétention
JSONL append-only, jamais supprimé (c'est le dataset V2). Rotation par fichier journalier ; compression mensuelle zip acceptable.
