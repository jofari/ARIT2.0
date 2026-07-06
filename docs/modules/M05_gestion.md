# M05 — `arit_lib/gestion.py` (G1-G7 : LE produit)

**Lien à l'edge** : c'est l'edge. Tout le reste du système existe pour amener une position ici et la laisser être gérée mieux qu'un humain, 24 h/24. La version A (contrôle) du test central = ce module désactivé.

**Libs** : `pandas` · API trade freqtrade (custom_data, stoploss_from_absolute côté stratégie). Pur côté calculs : chaque règle prend (état du trade, bougie 1h clôturée, custom_data) → action ou None.

## Architecture interne
```python
@dataclass
class TradeState:      # miroir typé du custom_data (chargé/écrit par la stratégie)
    initial_sl: float; risk_pct: float; tp1_done: bool; extension_on: bool
    mae_r: float; mfe_r: float; last_candle_ts: int; entry_regime: str; signal_id: str

def r_multiple(price, entry, initial_sl) -> float
def update_excursions(state, row, entry) -> TradeState            # MAE/MFE à chaque clôture 1h
def compute_sl(trade, row_1h, state) -> float | None              # max(G1, G2, G3) en prix absolu
def partial_tp(trade, current_profit_r, state) -> float | None    # G4 : −50 % du stake, une seule fois
def check_exit(trade, row_1h, state) -> str | None                # "G6" | "G7" | "TP2" | None (G5 gère TP2)
def flags() -> dict                                                # G1..G7 on/off (ablation, params.py)
```

## Stratégies précises (ordre d'évaluation à chaque clôture 1h)
1. Garde : `row.ts == state.last_candle_ts` ⇒ ne rien refaire (une action/bougie).
2. `update_excursions` (toujours).
3. **Sorties d'abord** (`check_exit`) : G6 si `choch_bear_1h` confirmé ⇒ "G6" · G7 si `age ≥ 24 bougies ET mfe_r < 0.5` ⇒ "G7" · si `extension_on == False` et `high ≥ TP2` ⇒ "TP2".
4. **TP partiel** (`partial_tp`) : si `not tp1_done` et `mfe_r ≥ 1.5` ⇒ vendre 50 %, `tp1_done = True`. (Freqtrade : retour de stake négatif via adjust_trade_position.)
5. **G5** : si `tp1_done` et `bos_bull_4h` frais ⇒ `extension_on = True` (TP2 neutralisé, le reste court sous trailing).
6. **SL** (`compute_sl`) : candidats — G1 : `entry×1.001` si `mfe_r ≥ 1.0` · G2 : `last_hl_1h − 0.1×atr_1h` si ce HL > SL courant · G3 : `close − k×atr_1h` (k = 2.0, 1.5 en RISK_OFF) seulement si `mfe_r ≥ 1.0`. Retour = max(candidats actifs) ; la monotonie (jamais vers le bas) est garantie par freqtrade ET re-vérifiée ici (assert défensif).

## Règles & invariants
1. **Le SL ne descend JAMAIS** — invariant testé, en plus de la garantie freqtrade.
2. Toute action (SL bougé, TP partiel, exit) ⇒ ligne de journal `gestion` avec avant/après et le R courant.
3. Chaque règle honore son flag d'ablation ; les défauts (1R, 0.1×ATR, 2×ATR, 1.5R, 50 %, 24, 0.5R) viennent de `params.py` et ne sont JAMAIS hyperoptés (PDR 09.3).
4. `initial_sl` ne change jamais (c'est l'unité R) — le SL courant vit dans `trade.stop_loss`.
**Tests** : monotonie du SL sur séquence aléatoire · G4 une seule fois · G6 prioritaire sur G4 la même bougie · G7 exactement à 24 bougies · MAE/MFE corrects sur un chemin construit · chaque flag off ⇒ règle inerte.
