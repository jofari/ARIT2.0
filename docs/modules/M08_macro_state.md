# M08 — `services/macro_state.py` (le pré-calcul fonda, hors hot-path)

**Lien à l'edge** : fournit le "SI on a le droit" (régimes) sans jamais mettre de latence réseau dans la boucle de trading. L'héritage direct du Macro Analyst d'ARIT v1 : snapshot pré-calculé, lu comme un fichier d'état.

**Libs** : `requests` (REST Finnhub + alternative.me), `json`, `os` (atomic replace), `logging`. Process indépendant lancé par le **Task Scheduler Windows toutes les heures** (run-once, pas de daemon).

## Architecture interne
```python
def fetch_calendar(finnhub_key) -> list[dict]     # /calendar/economic, filtre impact=high + mots-clés (NFP, FOMC, rate, CPI)
def fetch_fear_greed() -> int                     # alternative.me, retry ×3, backoff
def build_state(events, fg, now) -> dict          # schéma EXACT du PDR 06.3
def write_atomic(state, path) -> None             # write tmp + os.replace (jamais de JSON à moitié écrit)
def main() -> int                                 # orchestration + codes retour pour le Task Scheduler
```

## Stratégies précises
- `risk_off = (fg < 25) or (event high dans < 30 min)`. `next_events` = les 3 prochains high-impact ≤ 48 h, triés.
- Échec d'UNE source : garder la dernière valeur connue de cette source (relire l'ancien fichier), poser `stale` seulement si `updated_utc` global > 2 h — le lecteur (regimes.py) traite `stale ⇒ RISK_OFF`.
- Timestamps 100 % UTC ISO8601 ; aucune conversion locale nulle part.

## Règles & invariants
1. Ce script ne DÉCIDE rien — il décrit. Toute logique de veto vit dans regimes/risk.
2. Clé Finnhub via env `FINNHUB_KEY` ; jamais en dur, jamais loggée.
3. Rate limits respectés par construction (1 run/h) ; cache non nécessaire.
**Tests** : build_state sur cas construits (event à 29/31 min, fg 24/25/44/45) · atomicité (kill pendant write ⇒ ancien fichier intact) · stale à 1h59/2h01.
