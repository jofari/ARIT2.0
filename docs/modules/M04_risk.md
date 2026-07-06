# M04 — `arit_lib/risk.py` (sizing, budgets, garde-fous d'entrée)

**Lien à l'edge** : l'edge dit "sécuriser au maximum" — ce module garantit qu'aucune entrée ne peut violer les enveloppes (6 % résiduel, 8 % hebdo, 3 slots, CB). C'est lui qui rend le "plus de risque" de Jonas **survivable**. Il incarne aussi l'auto-financement de la thèse : une position sécurisée (BE) libère du budget pour la suivante.

**Libs** : `pandas` (requêtes), API `Trade`/`Wallets` de freqtrade (lecture DB — fonctionne aussi en backtest), `json`/`pathlib` (day_equity, veto flags). Pas de réseau.

## Architecture interne
```python
def compute_risk_pct(conviction, seuil, trade_no) -> float        # PDR 03.1 : 1% + n×(cap−1%), cap 2%→3% à 100
def compute_stake(equity, risk_pct, entry, sl_initial) -> float   # + skip si min-notional force > cap
def residual_risk_total(open_trades, equity) -> float             # Σ qty×max(0, entry−SL)/equity
def weekly_state(Trade, now_utc) -> (risk_engaged, n_entries)     # dérivé DB : trades ouverts cette semaine ISO
def gate_check(pair, now, wallets, Trade, cfg) -> (ok, gate, metrics)  # ordre EXACT du PDR 03.2 (1→8)
def snapshot_day_equity_if_new_day(wallets, now) -> None          # state/day_equity.json (référence CB −6 %)
def cb_day_active(wallets, now) -> bool
def cb_sequential_state(Trade) -> (cooldown_active, risk_divisor) # 2 clôtures consécutives ≤ −0.8R
def trade_counter(Trade) -> int                                   # nb total de trades (ouverts+clôturés) — cap 2/3 %
```

## Stratégies précises
- **Mapping** : `n = (conviction − seuil)/(1 − seuil)` ; `risk = (0.01 + n×(cap−0.01)) / cb_divisor` (le CB séquentiel divise par 2 pendant 5 trades).
- **Budget hebdo sans état** : tout est recalculé depuis la DB à chaque check (Σ des `risk_pct` stockés en custom_data des trades ouverts cette semaine ISO UTC + comptage). Zéro fichier de compteur = zéro désynchronisation, et le backtest a le même comportement.
- **CB jour** : équité courante < day_equity × 0.94 ⇒ bloqué jusqu'au prochain snapshot. 2 déclenchements même semaine ISO ⇒ flag `manual_restart_required` (fichier state) que seule une commande manuelle efface.
- **Ordre des gates = ordre du PDR 03.2**, et on s'arrête au premier échec (le journal enregistre le gate fautif + toutes les métriques mesurées).

## Règles & invariants
1. `gate_check` est la SEULE porte d'entrée — aucun chemin d'achat ne la contourne (y compris en backtest).
2. Tout `False` est journalisé avec métriques (un skip vaut une entrée en information).
3. Les caps (6 %, 8 %, 10, 3, −6 %) vivent dans `params.py`, modifiables uniquement via mise à jour du PDR.
4. Division par zéro impossible : `entry == sl_initial` ⇒ skip journalisé (jamais d'exception).
**Tests** : mapping aux bornes (conviction = seuil ⇒ 1 % ; = 1.0 ⇒ cap) · trade 100 vs 101 · résiduel avec position à BE = 0 · budget hebdo au franchissement exact · CB jour à −5.99 %/−6.01 % · séquentiel : −0.8R exactement.
