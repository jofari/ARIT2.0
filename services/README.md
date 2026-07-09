# services/ — 3 programmes SÉPARÉS du bot (chacun se lance seul)

| Fichier | Module | Rôle |
|---|---|---|
| `macro_state.py` | M08 | Fear&Greed + calendrier éco → écrit `user_data/macro_state.json` |
| `discord_bot.py` | M09 | digest quotidien + véto humain (pose `user_data/veto/<signal_id>.flag`) |
| `watchdog.py` | M10 | surveille le heartbeat du bot ; alerte + flatten s'il meurt (zéro import du projet) |

Séparés EXPRÈS : le watchdog doit survivre à un crash du bot. Carte : [`../guide.md`](../guide.md)
