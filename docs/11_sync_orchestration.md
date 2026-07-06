# 11 — Synchronisation & orchestration globale

> Qui tourne quand, qui lit quoi, où vit l'état. AUCUN module n'appelle un autre module directement : tout transite par la stratégie `AritV1` (callbacks freqtrade), par des colonnes de DataFrame, ou par des fichiers d'état. C'est l'héritage direct de la règle d'isolation d'ARIT v1.

## 11.1 Les cadences (toutes en UTC)
| Cadence | Quoi | Qui |
|---|---|---|
| ~5 s (itération freqtrade) | heartbeat (touch fichier) · re-check fenêtre de véto canari · sync exchange | AritV1 `bot_loop_start` / freqtrade |
| **Clôture 1h** | G1-G7 sur chaque position ouverte · update MAE/MFE · journal `gestion` | `gestion.py` via callbacks |
| **Clôture 4h** | features → régime → scores → conviction → signaux · journal `evaluation` | `features/regimes/cio` via `populate_*` |
| Horaire :00 | refresh `macro_state.json` | `services/macro_state.py` (Task Scheduler Windows) |
| Continu | tail du JSONL → posts Discord | `services/discord_bot.py` |
| 08:00 | digest quotidien Markdown → Discord | `discord_bot.py` |
| 00:00 | snapshot équité du jour (référence CB −6 %) | `AritV1 bot_loop_start` (détection de changement de date) |
| Lundi 00:00 | reset budget hebdo — **dérivé de la DB**, aucun cron (somme des trades de la semaine ISO courante) | `risk.py` à chaque gate_check |
| ~60 s | contrôle heartbeat + positions | `services/watchdog.py` (process indépendant) |

## 11.2 Détection "nouvelle bougie" (règle d'implémentation)
Base 1h + colonnes 4h mergées (`merge_informative_pair`) : la nouvelle donnée 4h apparaît sur la ligne 1h qui suit la clôture 4h. Colonne obligatoire `new_4h = (date_4h != date_4h.shift(1))`. **Un signal d'entrée n'est évaluable que si `new_4h == True`** (sinon on retraiterait le même setup 4 fois). Même principe pour les G-rules : une action par bougie 1h max (garde `last_candle_ts` en custom_data du trade).

## 11.3 Contrats de données (noms exacts, à ne pas renommer)
- **Colonnes produites par `features.py`** (consommées par regimes/cio/entrée/gestion) : `ema50_4h, ema200_4h, ema50_1d, adx_4h, rsi_4h, macd_hist_4h, atr_4h, atr_1h, vol_sma20_4h, pivot_high_conf_4h, pivot_low_conf_4h, last_ph_4h, last_hl_4h, last_hl_1h, bos_bull_4h, bos_fresh_4h, choch_bear_4h, choch_bear_1h, nearest_res_4h, nearest_sup_4h, res_touches_4h, rr_dispo, s_structure, s_momentum, s_sr, s_patterns, s_volume, cdl_* (~60), new_4h`.
- **Colonnes produites par `regimes.py`** : `regime` (str), `seuil`, `multiplicateur`.
- **Colonnes produites par `cio.py`** : `conviction`, `signal_long` (bool).
- **custom_data par trade** (API custom_data freqtrade — persistant, dispo en backtest) : `initial_sl, risk_pct, trade_no, tp1_done, extension_on, mae_r, mfe_r, last_candle_ts, entry_conviction, entry_regime, signal_id`.
- **Fichiers d'état** : `user_data/macro_state.json` (06) · `user_data/state/day_equity.json` (`{"date":"YYYY-MM-DD","equity":float}`) · `user_data/veto/<signal_id>.flag` · `user_data/state/heartbeat` (mtime) · `user_data/logs/decisions/*.jsonl`.

## 11.4 Séquence d'une entrée (mermaid)
```mermaid
sequenceDiagram
    participant FT as freqtrade (clôture 4h)
    participant F as features/regimes/cio
    participant E as entry logic
    participant G as confirm_trade_entry (risk.gate_check)
    participant D as discord_bot (canari)
    participant X as exchange
    FT->>F: populate_indicators (df 1h + 4h/1d merged)
    F->>E: conviction, seuil, rr_dispo, new_4h
    E->>FT: enter_long=1 (si conviction>=seuil & RR>=1.5 & regime ok)
    FT->>G: confirm_trade_entry(signal_id)
    G->>G: gates 1..7 (03.2) + journal gate_check
    alt phase canari
        G-->>D: intent posté (via journal) — G refuse tant que fenêtre non expirée
        D-->>G: veto flag OU expiration (5 min) — re-check aux itérations ~5s
    end
    G->>FT: True → custom_stake_amount (risk.compute_stake)
    FT->>X: ordre limit + stoploss_on_exchange
    FT->>G: journal entry + custom_data init
```

## 11.5 Règle réseau (invariant)
**Aucun appel réseau dans les callbacks freqtrade** (hors ceux de freqtrade lui-même vers l'exchange). La stratégie LIT des fichiers (`macro_state.json`, flags) ; les services (macro, discord, watchdog) font les appels externes dans leurs propres process. Garantit : latence stable, déterminisme, backtest identique au live.

## 11.6 Le véto canari est NON-BLOQUANT (décision d'implémentation importante)
`confirm_trade_entry` ne dort jamais 5 minutes (ça gèlerait la gestion des autres positions). Mécanique : au 1er passage, il journalise l'intention (`entry_intent`, avec `signal_id`) et retourne **False**. Le signal 4h reste valide (fraîcheur 3-4 bougies 1h) → freqtrade re-propose l'entrée aux itérations suivantes (~5 s) → dès que `now ≥ intent_time + veto_window` ET pas de flag véto → **True**. Entrée décalée de ≤ 5 min, gestion jamais bloquée. En dry-run `veto_window = 0`.
