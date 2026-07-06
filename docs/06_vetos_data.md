# 06 — Vetos & données externes

## 6.1 News blocker (calendrier économique)
- Source : **Finnhub** `/calendar/economic` (clé gratuite, env var `FINNHUB_KEY`).
- Périmètre V1 : events **US impact high** — NFP, décisions FOMC/taux, CPI (filtrage par champ impact + liste de mots-clés documentée dans le code).
- Règle : aucune ENTRÉE dans la fenêtre **[−30 min, +30 min]** autour de l'event. Les positions ouvertes ne sont pas fermées (G-rules continuent).
- Fail-safe : si le calendrier est irrécupérable depuis > 2 h → **bloquer les entrées** (flag `calendar_stale`, journalisé). La sécurité prime sur l'activité.

## 6.2 Sentiment de marché
- Source : **alternative.me Fear & Greed** (API publique, valeur quotidienne, cache 1 h).
- Usage : uniquement via le régime (04) — F&G < 25 → RISK_OFF · 25-44 → multiplicateur 0,85 · ≥ 45 → 1,0. Jamais un score directionnel, jamais un signal.

## 6.3 macro_state.py (service local, hors hot-path)
- Cron horaire (Task Scheduler Windows en local). Écrit `user_data/macro_state.json` :
```json
{"updated_utc": "ISO8601", "risk_off": false, "fear_greed": 62,
 "next_events": [{"name": "CPI US", "time_utc": "ISO8601", "impact": "high"}],
 "stale": false}
```
- `risk_off = true` si F&G < 25 OU event high dans < 30 min. `stale = true` si la dernière mise à jour date de > 2 h → la stratégie traite stale comme risk_off (fail-safe).
- La stratégie LIT ce fichier (jamais d'appel réseau dans les callbacks freqtrade — latence et déterminisme).

## 6.4 Filtre liquidité
Spread instantané (best ask − best bid)/mid ≤ **0,05 %** au moment de l'entrée, sinon skip journalisé. Suffisant en V1 sur les 4 majors ; profondeur de carnet = V2.

## 6.5 Discipline API
Toutes les clés en variables d'environnement (`.env` non commité). Binance : clés **sans droit de retrait**. Respect des rate limits (cache systématique ; F&G 1 h, calendrier 30 min).
