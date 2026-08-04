# services/ — programmes SÉPARÉS du bot (chacun se lance seul)

| Fichier | Module | Rôle | Cadence |
|---|---|---|---|
| `macro_state.py` | M08 | Fear&Greed + calendrier éco → écrit `user_data/macro_state.json` | **horaire** |
| `calendar_source.py` | C1 | calendrier éco à 2 sources (JSON versionné + cache ForexFactory) | voir ci-dessous |
| `discord_bot.py` | M09 | digest quotidien + véto humain (pose `user_data/veto/<signal_id>.flag`) | continu |
| `watchdog.py` | M10 | surveille le heartbeat du bot ; alerte + flatten s'il meurt (zéro import du projet) | continu |

Séparés EXPRÈS : le watchdog doit survivre à un crash du bot. Carte : [`../guide.md`](../guide.md)

## `calendar_source.py` — deux modes, deux cadences (C1, décision Jonas 03/08)

```powershell
# HEBDOMADAIRE (Task Scheduler) — seul mode qui touche au réseau pour le calendrier
& C:\Users\jofar\venvs\arit\Scripts\python.exe services\calendar_source.py --fetch-ff

# À la demande — diagnostic de couverture, aucun réseau (code 1 = trou de couverture)
& C:\Users\jofar\venvs\arit\Scripts\python.exe services\calendar_source.py
```

`macro_state.py` (horaire) ne fait **aucun** appel réseau pour le calendrier : il lit le JSON
versionné `user_data/calendar/economic_calendar.json` et le cache écrit par `--fetch-ff`.
Un échec du fetch hebdo dégrade sans bloquer — la primaire continue de couvrir ce qu'elle
connaît (`docs/06 §6.6`).

⚠️ La primaire ne couvre aujourd'hui que le **FOMC**. Les dates CPI/NFP restent à copier
depuis `bls.gov` (qui refuse les fetchs automatisés). Tant que ce n'est pas fait, le mode
diagnostic sort en code 1 avec `TROU de couverture sur ['CPI']` — c'est voulu.
