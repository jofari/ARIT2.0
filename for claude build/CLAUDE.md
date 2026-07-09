# CLAUDE.md — ARIT V1 (repo)

## Avant tout
**Lire `docs/` avant d'écrire la moindre ligne.** `docs/` (PDR v3, 22 fichiers) est la spec
contractuelle : README → 02_architecture → 11_sync_orchestration → modules/MXX du module visé
→ couche associée (03-08). Toute ambiguïté = question à Jonas, jamais d'improvisation.

## Interdits absolus (docs/README.md — s'appliquent à chaque ligne)
1. Aucun appel LLM dans le runtime.
2. Le SL ne s'élargit jamais.
3. Aucun look-ahead (colonnes 4h/1d via `merge_informative_pair`, clôtures seulement).
4. Aucune valeur magique : tout paramètre vit dans `user_data/strategies/arit_lib/params.py`
   avec sa source PDR en commentaire — et dans `docs/` d'abord.
5. G1-G7 et profils de poids : JAMAIS en hyperopt.
6. Chaque évaluation d'entrée (prise OU refusée) écrit une ligne de journal.
7. `dry_run: true` tant que docs/09 ne dit pas autrement. Clés API sans droit de retrait.

## Conventions
- Réponses à Jonas en français ; code et identifiants en anglais ; commentaires citant le PDR
  (`# PDR 03.4 G3`). Noms de colonnes/clés/fichiers d'état : EXCLUSIVEMENT ceux de
  `arit_lib/contracts.py` (miroir de docs/11 §11.3).
- `AritV1.py` mince (< 250 lignes, zéro logique métier, zéro réseau dans les callbacks) ;
  toute la logique dans `arit_lib/` (pur, testable) ; services dans `services/` (process séparés).
- Zéro import croisé entre modules `arit_lib` : un module n'importe que `contracts` et `params`.
- Tests : pytest, générateur OHLCV seedé de `tests/conftest.py`. Backtest : TOUJOURS
  `--timeframe-detail 5m`.
- Tout en UTC, partout. Paths Windows via `pathlib`.

## Environnement (machine de Jonas)
- venv : `C:\Users\jofar\venvs\arit` (Python 3.12, freqtrade 2026.6, talib 0.6.8, ruff, pytest).
- Tests : `& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q`
- État du build : `PLAN.md` (checklist qui fait foi) · leçons : `BUILD_NOTES.md`.
