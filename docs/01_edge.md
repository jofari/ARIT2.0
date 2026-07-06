# 01 — Hypothèse d'edge (SIGNÉE par Jonas, v3)

> **L'edge d'ARIT n'est pas dans la détection d'entrée. Il est dans la gestion dynamique et permanente des positions, 24 h/24.**
> Direction assumée : **swing, pas scalp**. Un bot a un meilleur edge en management de position qu'en entrée scalpée : cela limite le risque et vise des profits **plus constants** — moins gros que ceux d'une "entrée parfaite" théorique, mais réguliers et défendables. (Formulation de Jonas, intégrée telle quelle.)

## Thèse
Sur l'horizon swing crypto, la majorité des participants retail perdent par mauvaise gestion (stops déplacés dans le mauvais sens, gains coupés tôt, pertes laissées courir, sommeil, émotions), pas par absence de setups. ARIT inverse : **peu de positions (max 3), chacune gérée en continu** — réduction agressive du risque dès que possible, extension des gains tant que la structure le justifie. Un vrai trader, qui ne dort jamais.

## Mode de fonctionnement
- **Entrée** : setup de continuation post-BOS validé en clôture 4h · RR initial ≥ 1,5 obligatoire · risque 1→2 % (puis 1→3 %) proportionnel à la conviction.
- **Pendant** : SL ne peut que se resserrer (G1-G3), TP partiel + extension (G4-G5), sorties anticipées (G6-G7). Objectif : sécuriser au maximum chaque position.
- **Résultat visé** : perte moyenne < 1R, gain moyen > 1,5R, même à win-rate moyen.

## Pourquoi ça persiste
Avantage d'**exécution** contre le participant marginal de cet horizon (retail humain : dort, émotions, indiscipline). Les institutionnels ne jouent pas à cette échelle (taille incompatible) — la petitesse est un avantage. Ce n'est pas une anomalie arbitrable : on n'arbitre pas la psychologie de masse ni le sommeil des autres.

## Limite honnête (garde-fou intellectuel)
Sur des entrées à espérance nulle, toute stratégie de sortie est ≤ 0 après frais (propriété martingale). La gestion **préserve et amplifie** un petit edge d'entrée — elle ne le crée pas. Les entrées structurelles restent le substrat nécessaire ; la gestion est le différenciateur.

## Falsifiabilité — LE test central
- **Version A (contrôle)** : mêmes entrées, même SL initial, TP fixe à 1,5R (sortie totale), AUCUNE G-rule.
- **Version B (produit)** : mêmes entrées + G1-G7 complètes.
- **Exigence : B > A** sur expectancy, profit factor ET drawdown max — en backtest (`--timeframe-detail 5m` obligatoire) PUIS en dry-run. Si B ≤ A : hypothèse invalidée, retour recherche. Pas de rationalisation.

## Invalidation live (chiffrée)
PF glissant < 1,1 sur les 100 derniers trades · expectancy < 0 sur fenêtre 3 mois · divergence live/backtest > 10 pts de win-rate · slippage réel > 2× modélisé → **halt + revue**.

## Dépendance de régime — assumée
La continuation saigne en range → en RANGE et RISK_OFF le bot n'entre pas (voir 04). En spot long-only, **ne pas trader EST une position** : marché baissier = bot majoritairement cash, périodes flat longues normales.
