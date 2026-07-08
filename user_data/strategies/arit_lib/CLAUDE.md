# CLAUDE.md — package `arit_lib`

Logique métier PURE d'ARIT V1. Règles du package :

1. **Fonctions pures** : DataFrame/valeurs in → valeurs out. Aucun réseau, aucun appel LLM,
   aucun import freqtrade au niveau module (`Trade`/`wallets` toujours injectés, duck-typés).
2. **Imports internes autorisés** : `contracts` et `params` UNIQUEMENT. Jamais un autre module
   du package (features ↛ regimes ↛ cio…) — tout transite par la stratégie (docs/11).
3. **Noms** : colonnes, clés custom_data, fichiers d'état = `contracts.py`, rien d'autre.
   Une nouvelle clé = mise à jour de docs/11 §11.3 + contracts.py d'abord.
4. **Constantes** : `params.py` seulement, chaque valeur avec sa source (`# PDR 03.4 G3`).
   Modifier une valeur = modifier docs/ d'abord. G1-G7 et POIDS : jamais hyperoptés.
5. **Look-ahead interdit** : tout pivot décisionnel est confirmé (`shift(2)`) ; les colonnes
   4h/1d arrivent par le merge freqtrade (clôtures seulement) ; scores discrets
   ∈ {0, 0.3, 0.5, 0.7, 1.0} ; NaN de warm-up ⇒ score 0.
6. **SL** : ne s'élargit jamais (`initial_sl` immuable = unité R) ; monotonie re-vérifiée
   dans `gestion.py` même si freqtrade la garantit.
7. **Chaque module a son fichier de tests** (`tests/test_<module>.py`) avec les cas exigés
   en bas de sa spec `docs/modules/MXX.md`. Données : `tests/conftest.py` (seedé).
