# M09 — `services/discord_bot.py` (les yeux de Jonas + le véto canari)

**Lien à l'edge** : l'humain observe et peut opposer un véto SANS jamais être requis (un véto qui expire = go). Préserve le 24/7 et la parité backtest/live tout en donnant à Jonas la visibilité totale (idée 5 + suggestion Matthis, version non-bloquante).

**Libs** : `discord.py` (bot + reactions), `requests` (fallback webhook), `json/pathlib` (tail JSONL + flags), `asyncio`. Process indépendant.

## Architecture interne
```python
async def tail_journal(path) -> AsyncIterator[dict]   # suit le JSONL du jour (offset persistant, gère la rotation)
def format_embed(event: dict) -> Embed                # entry/exit/gestion/skip/system → embed lisible
async def post(event) -> None                         # filtrage : tout n'est pas posté (anti-spam, cf. règles)
async def on_intent(event) -> None                    # phase canari : poste l'intention + réaction ❌ attendue
async def on_reaction(reaction, user) -> None         # ❌ de Jonas ⇒ écrit user_data/veto/<signal_id>.flag
async def daily_digest(at="08:00") -> None            # lit le JSONL de la veille → résumé Markdown → post
```

## Stratégies précises
- **Filtrage anti-spam** : postés = entry, exit, G4/G5/G6/G7, CB, system-errors, skips pour gates budget/résiduel/veto. NON postés en continu = evaluations sans signal et gestion G1-G3 (visibles dans le digest et le JSONL).
- **Véto** : l'intention contient signal_id, régime, scores, conviction, risque %, SL/TP, RR. Réaction ❌ dans la fenêtre (5 min, `veto_window_min` de params) ⇒ flag écrit ⇒ `risk.gate_check` le voit au prochain re-check (~5 s) ⇒ skip journalisé `veto_humain` + motif si Jonas répond au message.
- Digest : compte les évaluations, signaux, entrées/skips par gate, actions G*, PnL du jour, positions ouvertes avec R courant — l'objectif : Jonas comprend la "pensée" des dernières 24 h en 1 minute.

## Règles & invariants
1. Ce bot ne peut RIEN exécuter (pas de clés exchange) — lecture JSONL + écriture de flags, c'est tout.
2. S'il est down : le trading continue à l'identique (en canari, fenêtre expirée sans véto possible = go — Jonas en accepte le principe ; le watchdog alerte si le bot Discord est down > 15 min).
3. Token Discord via env ; canal privé ; aucune donnée de clé/soldes détaillés dans les posts.
**Tests** : tail avec rotation de jour · flag écrit correspond au bon signal_id · digest sur un JSONL de fixture.
