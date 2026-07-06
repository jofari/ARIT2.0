# M06 — `arit_lib/journal.py` (la boîte noire — idée 5)

**Lien à l'edge** : rend l'edge AUDITABLE (pourquoi chaque action/inaction) et prépare la V2 (dataset FreqAI). Un skip documenté = la moitié de la valeur. C'est aussi l'outil n°1 de debug pendant les 6 mois de dry-run.

**Libs** : `json`, `pathlib`, `datetime` (UTC), `gzip` (rotation). AUCUN réseau (Discord = service séparé qui tail).

## Architecture interne
```python
def write(event_type: str, payload: dict) -> None      # append JSONL, fichier du jour, flush immédiat
def read_macro_state() -> dict                         # lecture + validation schéma + stale (partagé)
# builders typés (un par type d'événement du PDR 08.1) :
def ev_evaluation(row, explain_dict) -> dict
def ev_gate_check(signal_id, gates: list[dict], decision, failed) -> dict
def ev_entry(trade, state) -> dict
def ev_gestion(trade, action, before, after, r) -> dict
def ev_exit(trade, cause, r_final, mae, mfe, fees, slippage) -> dict
def ev_system(kind, detail) -> dict
```

## Stratégies précises
- Append-only, une ligne = un JSON compact horodaté `ts_utc` ISO + `schema_version: 1`. Écriture atomique (open append + newline). Erreur d'écriture ⇒ retry ×1 puis `logging.error` — **le trading ne s'arrête jamais pour un problème de journal**, mais l'incident est tracé.
- `signal_id = f"{pair}-{ts_4h}"` : clé de corrélation entre evaluation → gate_check → intent/veto → entry → gestion → exit. Tout le cycle d'un trade se reconstruit par ce champ.
- Les ~60 colonnes `cdl_*` ne sont écrites QUE dans `evaluation` (pas répétées ensuite).

## Règles & invariants
1. JAMAIS de suppression (dataset V2) ; compression mensuelle .gz acceptée.
2. Aucune donnée sensible (pas de clés, pas de soldes absolus hors équité — l'équité est nécessaire au calcul).
3. Toute nouvelle clé de payload = mise à jour du schéma dans le PDR 08.1 d'abord (`schema_version` incrémenté).
**Tests** : round-trip write/read · rotation au changement de jour UTC · reconstruction d'un cycle complet par signal_id.
