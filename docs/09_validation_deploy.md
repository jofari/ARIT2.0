# 09 — Validation & déploiement (gates BLOQUANTS)

## 9.1 Protocole de backtest A/B (le test de l'edge — voir 01)
1. **Contrôle A** : entrées identiques, SL initial identique, **TP fixe +1,5R sortie totale**, aucune G-rule.
2. **Produit B** : entrées identiques + G1-G7 complètes.
3. Exigence : **B > A sur expectancy (R moyen), profit factor ET drawdown max**, sur l'historique complet ET sur chaque sous-période (2018-2020 / 2021-2022 / 2023-2026 : bull, bear, chop).
4. **Ablation** : B moins chaque Gx individuellement (7 runs) → contribution de chaque règle documentée. Une règle qui dégrade systématiquement → désactivée par flag (décision Jonas, journalisée dans ce dossier).
5. Résultats détaillés par régime (TREND/TRANSITION) et par paire.

## 9.2 Seuils chiffrés
| Phase | Durée / volume | Critères de passage |
|---|---|---|
| Backtest | Historique max (2017+), ≥ 100 trades | PF ≥ 1,3 · DD max ≤ 15 % · B > A partout · win-rate et R moyen documentés |
| **Dry-run** (local OK) | **6 mois** ET ≥ 50 trades | PF ≥ 1,3 · DD ≤ 10 % · win-rate à ±10 pts du backtest · slippage réel ≤ 2× modélisé · zéro incident critique (crash non récupéré, ordre fantôme) |
| **Canari** (capital réel : 10 000 USDT) | ≥ 2 mois | Mêmes critères + véto Discord actif + exécution réelle conforme au dry-run |
| Montée | — | Par paliers, jamais > ×2 d'un coup, ≥ 1 mois entre paliers |
Chaque passage = **décision manuelle de Jonas**, jamais automatique. Un critère raté → on reste (ou on redescend). Modifier un seuil = modifier CE fichier d'abord.

## 9.3 Hyperopt — périmètre strict
Autorisé UNIQUEMENT sur 3-5 paramètres d'ENTRÉE (ex. : seuil TREND, bornes ADX, multiplicateur de displacement, fraîcheur BOS). **Jamais** sur G1-G7, les profils de poids, ou les garde-fous. Validation : optimisation sur 2018-2023, test hors-échantillon 2024-2026 — les paramètres retenus doivent tenir sur la période non vue.

## 9.4 GATE MATÉRIEL (bloquant pour le capital réel)
Dev + dry-run : machine locale de Jonas (Windows, veille désactivée) — acceptable, les interruptions coûtent des données, pas de l'argent.
**Capital réel ⇒ machine always-on dédiée OBLIGATOIRE** (VPS ~5 €/mois ou PC fixe sans veille). Justification : `stoploss_on_exchange` protège du pire pendant un downtime, mais G1-G7 — l'edge lui-même — ne tournent pas quand la machine dort. Un laptop en veille avec 10 k€ en positions actives est inacceptable. ("Pas de VPS pour le moment" = décision valable jusqu'à ce gate, pas au-delà.)

## 9.5 Watchdog local (`services/watchdog.py`)
Process indépendant : lit le heartbeat du bot (fichier touché à chaque itération). Si heartbeat > 10 min ET positions ouvertes → alerte Discord CRITIQUE + tentative de flatten via ccxt (clés propres, trade-only). Ne fait RIEN d'autre. Testé en dry-run (flatten simulé/loggé).

## 9.6 Sécurité opérationnelle
Clés Binance **sans droit de retrait** · 2FA sur le compte · `.env` jamais commité (`.gitignore` dès le Sprint 0) · FreqUI liée à 127.0.0.1 · IP allowlist Binance dès qu'il y a une IP fixe (VPS) · sauvegarde hebdo de `user_data/` (SQLite + JSONL).
