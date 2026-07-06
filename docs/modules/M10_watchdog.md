# M10 — `services/watchdog.py` (le dernier filet)

**Lien à l'edge** : l'edge suppose une gestion continue — ce module couvre le cas où elle S'ARRÊTE (crash, freeze). Défense en profondeur : ligne 1 = stoploss_on_exchange (déjà posé chez Binance), ligne 2 = ce watchdog.

**Libs** : `ccxt` (clés PROPRES, trade-only, distinctes de celles de freqtrade), `requests` (webhook Discord direct — ce process a le droit au réseau), `pathlib/time`. Boucle simple toutes les 60 s. Process indépendant (Task Scheduler au boot).

## Architecture interne
```python
def heartbeat_age(path) -> float                      # now − mtime(user_data/state/heartbeat)
def open_exposure(ccxt_client) -> list[dict]          # soldes non-USDT au-dessus du dust (spot = pas de "positions")
def alert(level, msg) -> None                         # webhook Discord direct
def flatten(ccxt_client, holdings) -> None            # cancel open orders + market-sell (SI activé)
def main_loop() -> None
```

## Stratégies précises
- `heartbeat_age > 600 s` ET exposition non nulle ⇒ `alert(CRITICAL)` ; si `WATCHDOG_FLATTEN=true` (défaut **false** ; activé seulement en phase canari, décision manuelle) ⇒ `flatten()` puis re-alerte avec le détail. Sinon : alerte seule (les SL exchange restent la protection).
- Anti-faux-positif : 2 lectures à 60 s d'intervalle avant d'agir ; ne flatten JAMAIS deux fois (flag une fois déclenché, reset manuel).
- Dry-run : exposition réelle = 0 par construction ⇒ le watchdog ne peut qu'alerter — parfait pour le tester 6 mois.

## Règles & invariants
1. Indépendance totale : aucun import du projet, aucun accès à la DB freqtrade — fichiers + exchange only.
2. Ses clés ccxt : trade-only, sans retrait, IP allowlist quand disponible.
3. Chaque action (alerte, flatten) est aussi écrite en local (`system` log) — le watchdog est lui-même auditable.
**Tests** : age du heartbeat simulé · double-lecture anti-faux-positif · flatten idempotent (mock ccxt) · dust threshold.
