# 06 — Vetos & données externes

## 6.1 News blocker (calendrier économique)
- Source : **Finnhub** `/calendar/economic` (clé gratuite, env var `FINNHUB_KEY`).
- Périmètre V1 : events **US impact high** — NFP, décisions FOMC/taux, CPI (filtrage par champ impact + liste de mots-clés documentée dans le code).
- Règle : aucune ENTRÉE dans la fenêtre **[−30 min, +30 min]** autour de l'event. Les positions ouvertes ne sont pas fermées (G-rules continuent).
- Fail-safe : si le calendrier est irrécupérable depuis > 2 h → **bloquer les entrées** (flag `calendar_stale`, journalisé). La sécurité prime sur l'activité.

## 6.2 Macro Analyst V1.1 (validé Jonas 2026-07-12 — remplace l'ancien « Sentiment de marché »)
> Version d'origine (F&G seul → RISK_OFF/multiplicateur) ABSORBÉE par ce module.
> Spec détaillée et genèse : `for claude build/SPEC_MACRO_V1.1_PROPOSITION.md`.

**5 composants quotidiens, chacun scoré ∈ {+1, 0, −1}** (calcul 1×/jour à 00:00 UTC) :
| # | Série | Source | Score |
|---|---|---|---|
| 1 | Dollar broad (DXY) | FRED `DTWEXBGS` | var. 20 j ouvrés : ≤ −0,5 % ⇒ +1 · ≥ +0,5 % ⇒ −1 |
| 2 | Taux Fed effectif | FRED `DFF` | var. 60 j : ≤ −0,10 pt ⇒ +1 · ≥ +0,10 pt ⇒ −1 |
| 3 | Market cap stablecoins | DefiLlama | var. 30 j : ≥ +2 % ⇒ +1 · ≤ −1 % ⇒ −1 |
| 4 | Funding rate (moy. BTC+ETH) | Binance fapi | moy. 7 j : > +0,05 %/8h ⇒ −1 · < 0 ⇒ +1 |
| 5 | Fear & Greed | alternative.me | < 25 ⇒ −1 · ≥ 45 ⇒ +1 |

**Régime macro** = Σ scores ∈ [−5,+5] : **PORTEUR** ≥ +2 · **HOSTILE** ≤ −2 · **NEUTRE** sinon.
Composant stale (> 48 h) ⇒ 0 ; ≥ 3 composants stale ⇒ HOSTILE (fail-safe).
**Effets** (docs/04 §4.2) : HOSTILE ⇒ véto d'entrée (ne ferme jamais une position) · NEUTRE ⇒
taille ×0,85 ET seuil de conviction +0,05 · PORTEUR ⇒ plein. Journalisation : `macro_regime`
+ les 5 scores dans l'événement `evaluation` (docs/08, schema_version +1).
**Backtest** : séries historiques (`scripts/download_macro.py` → `user_data/data/macro/`),
point-in-time STRICT (valeur du jour J utilisable à partir de J+1 00:00 UTC) — remplace le
« macro neutre ». Avant la 1re date d'une série : composant = 0. Seuils FIGÉS, jamais hyperoptés.

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
