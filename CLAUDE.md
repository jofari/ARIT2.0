# CLAUDE.md — ARIT V1 (racine, version courte)

> Ce fichier DOIT rester à la racine (Claude Code ne charge que celui-ci au démarrage).
> Version complète + ressources du build : `for claude build/CLAUDE.md`.

- **Spec contractuelle = `docs/` à la racine** (22 fichiers, avec `modules/` et `11_sync`).
  ⚠️ PAS `for claude build/ARIT_PDR_v3/` (copie incomplète, 11 fichiers). Lire docs/ avant tout code.
- **Arbitrages de Jonas : `DECISIONS.md` (racine) — à lire en début de session, avant tout code.**
  Toute décision qu'il donne s'écrit là le jour même, jamais seulement dans la conversation.
  ⚠️ **Ce fichier est PURGÉ en continu** (règle du 17/08) : il ne contient QUE les décisions
  ouvertes. Dès qu'une décision est appliquée/fermée/abandonnée, **supprimer sa section dans la
  même session** — après avoir déplacé ce qu'elle laisse de durable (piège/mesure →
  `for claude build/BUILD_NOTES.md` · paramètre → `docs/` · travail restant → `CHANTIERS.md`).
  La trace des fermées est dans git : `git log -p -- DECISIONS.md`.
- Carte du repo pour s'orienter : `guide.md` · carte des modules (macro/technical/cio/risk/quant/
  backtest, fiches → vrai code, zéro code dedans) : `modules/`. État du chantier : `for claude build/PLAN.md` ·
  pièges connus : `for claude build/BUILD_NOTES.md` · bilan : `for claude build/RAPPORT_BUILD.md`.
- Les 7 interdits absolus de `docs/README.md` s'appliquent à chaque ligne (pas de LLM runtime,
  SL jamais élargi, zéro look-ahead, zéro valeur magique hors `arit_lib/params.py`, G1-G7/poids
  jamais hyperoptés, chaque évaluation journalisée (live/dry — docs/08), `dry_run: true`).
- Conventions : noms/clés = `arit_lib/contracts.py` uniquement · zéro import croisé entre modules
  arit_lib · AritV1.py < 250 lignes, zéro métier, zéro réseau dans les callbacks · tout en UTC ·
  backtest TOUJOURS `--timeframe-detail 5m` · réponses à Jonas en français.
- venv : `C:\Users\jofar\venvs\arit` (ne pas réinstaller `aiodns` — voir BUILD_NOTES).
  Tests : `& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q` (attendu : 318 passed).
- Le bot est **long ET short** depuis le 04/08 (A2) : `trading_mode: futures`, paires
  `BTC/USDT:USDT`. Convention de signe unique = `docs/03 §3.7`, jamais de `if is_short`
  dispersé. Backtest : `--enable-protections` est OBLIGATOIRE depuis C6 (docs/07 §7.2).
- Git : remote `https://github.com/jofari/ARIT2.0.git`, branche `main`, **push après chaque commit**.
