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

### 6.2.1 Bloc corrélation actions — c6/c7, **HORS de la somme** (décision Jonas 2026-08-03, A4)

Deux composants supplémentaires qui ne s'additionnent **jamais** aux 5 ci-dessus : ils sortent un
**véto booléen** journalisé à part et ablatable seul.

| # | Rôle | Série | Règle |
|---|---|---|---|
| c6 | Risk-off actions | FRED `NASDAQ100` | clôture sous le plus-bas de clôture des 20 j ouvrés ⇒ véto longs |
| c7 | Régime de corrélation (**méta**) | ρ(BTC, NASDAQ100) | décide si c6 est **ARMÉ** |

**Pourquoi pas un 6ᵉ terme additif** — trois raisons, dans l'ordre d'importance :
1. Il déplacerait **silencieusement** le sens des seuils (±2 sur 5 → ±2 sur 6) : HOSTILE
   deviendrait mécaniquement plus facile à atteindre, ce qui recalibre les 5 composants
   existants sans les avoir touchés.
2. Un score ∈ {−1, 0, +1} est **symétrique par construction**. Or la mesure dit que le BTC suit
   les actions à la **baisse** et pas à la hausse : un +1 quand l'indice monte est exactement ce
   qu'il ne faut pas coder.
3. Motif déjà mesuré 3 fois sur ce projet (funding en score, sizing par la force du score,
   pénalité continue de régime) : un signal utile en **véto** détruit de la valeur en **terme
   additif**.

**c7 / hystérésis** : ρ court (30 j) et long (90 j) calculés **sur les sessions US**, jamais sur un
calendrier 7/7 (un indice forward-fillé injecte ~2 jours de rendement nul par semaine et déflate ρ
d'environ −33 % : un vrai couplage à 0,75 s'afficherait à 0,50, pile sur le seuil). États :
`COUPLE` (arme le véto) au-dessus de 0,50 confirmé · `DECOUPLE` sous 0,30 · `TRANSITION` entre les
deux (bande morte ⇒ véto **désarmé**, donc le warm-up ne bloque rien).

**Donnée périmée ⇒ fail-safe** (décision Jonas 2026-08-03, A4 — révise le fail-open proposé) :
- Série **démarrée puis périmée** (> 120 h sans observation) ⇒ **véto ACTIF**, raison
  `equity_veto_stale`. Fenêtre dédiée de 120 h et non les 48 h de `MACRO_STALE_HOURS` : l'indice
  est une série 5/7, un férié US collé à un week-end laisse jusqu'à 96 h sans observation.
- Série **jamais démarrée** (fichier absent, ou date antérieure au début de la série) ⇒ le bloc
  n'est **pas opérationnel**, il ne véto PAS. Un fail-safe sur « jamais configuré » bloquerait
  100 % des entrées de tout backtest, ce qui n'est pas de la sécurité mais une panne.
  Même distinction `started` / `fresh` que les 5 composants ci-dessus.
- Un événement `system` est journalisé au **premier** jour de blocage, avec le compteur de jours
  consécutifs : sans ça, un flux mort arrête le bot en silence.

**Raisons journalisées** (chaînes STABLES, jamais d'f-string — elles sont comptées telles quelles
en ablation) : `equity_risk_off` (bloque, et bloque seul) · `equity_risk_off_redundant` (bloque,
macro déjà HOSTILE) · `equity_decoupled` · `equity_no_break` · `equity_veto_stale` ·
`equity_not_started`. La distinction BINDING/REDUNDANT donne directement l'apport **marginal** du
filtre ; sans elle, l'ablation le surestime de tous ses blocages non-liants.

⚠️ **Ne rien conclure de son backtest tant que l'entrée n'a pas d'edge** : sur un substrat à
espérance nulle, tout filtre qui réduit l'exposition paraît positif par construction.

⚠️ **Portée = backtest.** Le service live `macro_state.py` (§6.3) ne calcule ni les 5 scores ni ce
véto ; en live/dry la stratégie retombe sur l'ancien chemin F&G. Écart pré-existant, à traiter
avant le dry-run.

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
