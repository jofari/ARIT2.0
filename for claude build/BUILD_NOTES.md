# BUILD_NOTES — leçons et décisions de build

## 2026-07-27 — MacroFlip : le Macro Analyst seul, sans technique ni gestion (research/macro_flip/)
Expérience Jonas : isoler la couche macro après le verdict « edge d'entrée NUL » du 19/07.
Règle nue — PORTEUR→long, HOSTILE→short (perp), NEUTRE→on garde ; ni SL ni TP, 50 % de
l'équité, levier 1x, BTC/USDT:USDT 4h, 2020-01→2026-07 (borne = début des données mark).
**Aucun code de production touché** (AritV1/arit_lib/docs/config.dry.json intacts) ;
`user_data/strategies/MacroFlip.py` + `research/macro_flip/` uniquement. Données futures
téléchargées (5m/4h/mark/funding). **Résultat : +263,5 %, PF 2,80, DD 24,3 %, 12 trades —
contre un buy & hold à +769 % : perdant contre ne-rien-faire.** Trois découvertes :
(1) **le funding mange 86 % du profit** (−22 579 USDT, dont −17 193 sur le seul long perp
de 729 j) — erreur d'EXÉCUTION, pas de signal : mêmes trades avec les jambes longues en
SPOT ⇒ +577 % (vs +385 % pour un buy & hold à capital égal 50 %) ; **ne jamais porter un
long multi-mois sur un perpétuel à 1x** ; (2) **tout tient dans 2 trades** (les deux bulls) :
sans les 2 meilleurs, +5 % sur 6,5 ans ; (3) le short vaut +93 pts vs rester cash, sur
6 shorts dont 3 gagnants. Significativité : Monte-Carlo directionnel **p = 0,095**
(percentile 90,5) — pas significatif, MAIS à comparer au p = 0,99 de l'edge d'entrée :
c'est le premier signal d'ARIT qui n'est pas du bruit manifeste. Bootstrap IC90
[−2 % ; +7 188 %] = inexploitable (n = 12). **Les 4 dernières positions (déc. 2025 →
juil. 2026) sont toutes perdantes** = le DD de 24,3 %. Variante `ARIT_MACRO_FLAT_NEUTRE=1`
(cash en NEUTRE) : 134 trades de 9 j, +69,6 %, PF 1,29 — le churn coûte 194 pts, mais
c'est la seule version avec un n exploitable. Artefact week-end vérifié et ÉCARTÉ (HOSTILE
uniforme sur les 7 jours). Réserves : seuils 06.2 jamais validés hors échantillon ; mcap
stablecoins DefiLlama reconstruite rétroactivement (biais point-in-time résiduel).
**Aucune décision prise** — suites proposées §7 du RAPPORT (walk-forward d'abord), en
attente de Jonas.
**Suite le même jour — « améliorer le management pour une V1 » : MESURÉ, ça ne marche pas.**
`research/macro_flip/gestion_sim.py` : 22 politiques de sortie × 6 règles de taille rejouées
bougie par bougie sur les 12 épisodes. (a) **Correction de mesure importante : le vrai
drawdown est 49,2 % (spot) / 61,8 % (perp), pas 24,3 %** — le chiffre freqtrade est calculé
sur la courbe des trades CLÔTURÉS, donc aveugle entre deux clôtures espacées de 729 j.
Piège à retenir pour tout backtest à positions longues. (b) Aucune politique ne bat HOLD de
façon crédible : les 3 meilleures (SL 12xATR +622 %, time-stop +616 %, SL 5xATR +599 % vs
HOLD +579 %) sont dans le bruit à n=12 **et ne réduisent pas le DD d'un point**. (c) Tout
trailing serré détruit : chandelier 20xATR +95 %, 12xATR +39 %, 8xATR +16 %, 5xATR **−2 %**
(12 coupes sur 12). (d) Le BE ne se déclenche jamais. (e) Taille : le **50 % fixe est déjà
le meilleur** des 6 (perf/DD 11,77) ; le vol-targeting achète du rendement et autant de DD ;
sizer par la force du score macro DÉGRADE (l'intensité du score ne porte pas d'info).
**Raison structurelle : la valeur du signal EST la durée de détention** (99 % du résultat =
2 tendances de 2 ans) — c'est l'inverse du burst rapide diagnostiqué le 17/07, donc **les
G-rules ne sont pas recyclables ici**. Seule piste notable : chandelier 20xATR, +95 % mais
DD 18,2 % et **+37,6 % sans les 2 meilleurs épisodes** (vs +5,4 % pour HOLD) = la seule règle
dont le résultat ne tient pas à 2 coups de chance. **Classement des leviers réels : spot pour
les longs (+312 pts) >> n plus grand > walk-forward >> gestion (≈ 0) = taille (≈ 0).**

## 2026-07-19 — campagne corrigée A/B pur + rapport edge & G-rules (research/edge_2026-07/)
Demande Jonas : analyse marché (institutions/whales) + idées d'edge + refonte G rules + rapport
Discord. Runs post-fix SL, **macro NEUTRALISÉE par renommage de `data/macro` puis RESTAURÉE**
(méthode validée pour « A pur » : `macro_unavailable` journalisé — tranche le « À DÉCIDER » du
18/07). Verdicts : **A pur corrigé +0,12 %, PF 1,00, 128 trades, p=0,99 → edge d'entrée NUL**
(le « +40 % » était bien l'artefact du bug ; seul 2021 est porteur (+65 %) ; la « famine
2023-2026 » disparaît : 56 épisodes, ≈ flat). **B pur corrigé −17,38 %, PF 0,72, 187 trades ≈ B
buggé** (le bug ne touchait presque pas B → les ablations du 11/07 restent valides). R-space
(`research/edge_2026-07/policy_sim.py`, 12 politiques × 123 épisodes) : toute gestion à l'échelle
1h ≤ 0 (même chandelier 8×ATR) ; TP1+giveback50 = +0,26R mais **+0,00R sans son top trade** →
aucune gestion ne crée d'edge sur substrat nul (martingale docs/01 confirmée sur 8,5 ans).
Découverte : le stop initial 03.3 est ~2× trop large pour le profil burst réel (MAE gagnants
médian −0,25R) → à demi-distance, E ×20 brut à risque constant — chantier ENTRÉE prioritaire.
Proposition G-set v2 (supprimer G1/G2/G3/G5/G6, garder G4+G7, ajouter G-giveback) + 11 idées
d'edge taguées (Polymarket = la donnée consensus qui manquait à l'arbre v0 ; domaine DNS-bloqué
FR/ANJ, lecture contournée via DoH — dépendance d'infra à assumer) : voir RAPPORT.md, envoyé sur
Discord (embed + pièce jointe). **AUCUNE modif code/spec** — décisions Jonas en attente (G-set
v2, ordre de chantier §5 du rapport).

## 2026-07-18 — fix contrôle A LIVRÉ + validé sur données réelles (go Jonas)
Les 2 diffs de la note du 17/07 sont appliqués : (1) `custom_stoploss` offre le floor
`initial_sl` à CHAQUE appel (plus seulement `after_fill`) — idempotent, freqtrade ne
resserre que vers le haut ; (2) garde « vie du trade » sur la branche TP_CONTROL_A de
`check_exit` (miroir G6). +3 tests de régression (203 verts). **Validation smoke**
(run5, 2021-S1, détail 5m, ARIT_CONTROL_A=1) croisée avec le run A+macro buggé du 13/07
à conditions identiques : trade sain byte-identique (+6,60 %) · cluster churn 23/04
7 trades → 1 (+8,89 % au lieu de +7,0 % fragmenté) · le perdant 27/04 sort au stop
structurel −2,29 % (buggé : passait SOUS son SL sans stop et « gagnait » +1,91 % le
lendemain — l'illusion du bag-holding en une ligne). SL posé ≈ 2-3,8 % sous l'entrée
(structurel) au lieu du placeholder −99 %. **PIÈGE découvert au passage** : depuis le
12-13/07, `data/macro/` (6 fichiers) s'injecte par junction dans TOUTES les lanes → tout
backtest est silencieusement « +macro ». Le smoke = A+macro (3 entrées vs ~11 attendues
en A pur — c'est la macro, pas le fix). Pour re-runner le protocole en « A pur » il
faudra neutraliser la macro explicitement (retirer/renommer data/macro de la lane, ou
flag dédié — À DÉCIDER avec Jonas avant le re-run). Protocole complet PAS relancé
(instruction Jonas : fix seul).

## 2026-07-17 — BUG MAJEUR contrôle A : il a tourné SANS stop-loss (campagne A/B invalidée)
Découvert en déployant l'outil replay E0 (décision Jonas 17/07). Preuves (zip run2
15-09-24, 55 trades) : `initial_stop_loss_abs` = −99 % sur TOUS les trades, zéro sortie
stop, trades zombies (ETH 1 381 j à travers −80 % de flottant, BNB 554 j), force_exit
final −20,3 %. **Mécanisme** (AritV1.custom_stoploss) : le floor SL initial n'est posé
que si `after_fill` ET custom_data déjà écrit — or `order_filled` écrit le custom_data
APRÈS → floor jamais posé ; en mode contrôle A `compute_sl` renvoie None pour toujours
→ aucun SL pendant 8,5 ans. Deux bugs secondaires : la branche TP_CONTROL_A de
`check_exit` n'a pas la garde « bougie postérieure à l'entrée » (ajoutée à G6 le 10/07)
→ 14 sorties/re-entrées churn à t+0 ; et aucun cooldown post-exit (Protections jamais
implémentées). Conséquences : le « +40 %, PF 2,12 » du RAPPORT_PROTOCOLE_AB n'est PAS
un benchmark valide ; la « famine 2023-2026 » (8 trades) est en partie l'ombre du bug
(2 slots sur 3 zombie-bloqués 2022-2025) ; B est aussi touché (1re bougie sans SL avant
le 1er move G2). **Fix attendu (2 diffs, EN ATTENTE du go Jonas** car il réécrit la
baseline) : (1) custom_stoploss retourne le floor initial_sl à CHAQUE appel dès que
custom_data existe (freqtrade ne resserre que vers le haut — idempotent) ; (2) garde
`row date >= open_date` sur la branche TP_CONTROL_A ; (+ décision cooldown 07.1).
**Replay des 41 épisodes uniques (churn regroupé) avec le SL initial actif** :
18 TP / 23 SL (44 %) ≈ breakeven après frais — MAIS gagnants très rapides (médiane
2,8 h jusqu'à +1,5R, MAE médian −0,28R) et continuation capturable après +1,5R :
médiane +3,8R, p75 +20R, p90 +90R (giveback pic→creux médian 5R sans gestion).
L'histoire « swing 37 j » était un artefact du bug ; l'edge, s'il existe, est un burst
momentum avec grosse queue droite non capturée. Outil : `analysis/replay_entries.py`
(validé : 55/55 SL journal, tp1 à 0,0000 %, timing sorties reproduit 17/17).
A+macro : +5,4 %, PF 1,21, 31 trades, DD 19,3 % — vs A sans macro : +40,0 %, PF 2,12, 55
trades. **La couche macro calibrée 06.2 DÉGRADE la base saine** : elle supprime les gagnants
2018-2022 (funding chaud en bull ⇒ NEUTRE ⇒ taille réduite + seuil durci en pleine tendance)
et ne filtre PAS les perdants 2023-2026 (8 trades, PF 0,31 identique). En revanche sur B
(G-rules on) : −19,1 % → −7,0 %, DD 24,9 % → 10,6 % — le VÉTO HOSTILE est la partie qui
marche. RECOMMANDATION posée à Jonas (décision en attente) : garder le véto HOSTILE seul,
retirer la pénalité NEUTRE et/ou sortir le funding du score (contre-productif pour du
trend-following long-only). Chiffres archivés : backtest_lanes/run1 et run2, derniers zips.

## 2026-07-13 — zéro-trade macro : unités datetime + 2 leçons de debug
1. **Cause** : `merge_asof` refuse de joindre `datetime64[ms, UTC]` (dates des feather
   freqtrade) avec `[ns]/[us]` (index pandas natifs) → exception avalée par le try/except de
   populate → plus de signal_long → ZÉRO trade, silencieusement. Fix : `.as_unit("us")` sur les
   DEUX clés dans `regimes.attach_macro_regime` + test unités mixtes. **Règle : tout merge avec
   les données freqtrade doit normaliser les unités datetime.**
2. **Leçon debug n°1** : les tests unitaires passaient (données synthétiques = ns partout) —
   seul un run sur données réelles révélait le bug. Un smoke court (3 mois) reproduit en 2 min.
3. **Leçon debug n°2** : le journal écrit au jour UTC (fichier 2026-07-12.jsonl à minuit
   local du 13) — chercher les `indicators_error` au bon jour. Et la base du journal résout la
   junction → les backtests en lanes écrivent leur journal dans le user_data RACINE (fichiers
   90 Mo mélangés entre lanes) : à corriger plus tard via `journal.set_user_data_dir` dans
   bot_start (ajouté à la liste des correctifs différés avec F1/F3/F5).

## 2026-07-12 — Macro Analyst V1.1 : review PASS, findings en file d'attente
Review indépendante du chantier macro (module + câblage) : **PASS** — point-in-time correct
(shift +1 j unique puis merge_asof backward), seuils conformes, rétrocompat gatée. À TRAITER
après les 2 backtests macro : **F3 MEDIUM** (au-delà de la fin de l'historique macro, le
merge_asof forward-fill le dernier régime sans plafond → forcer NEUTRE) · **F1 LOW** (NaN
pré-historique = ×0,85 sans bump de seuil — NEUTRE partiel incohérent) · **F5 LOW** (noms de
fichiers macro à centraliser dans contracts). **F2/F4 différés avec l'extension live** :
journalisation macro_regime + 5 scores dans ev_evaluation (schema_version +1, exigé 06.2)
et bump de seuil côté live. POC arbre v0 : verdict « pas de signal sur la date seule » —
décision Jonas 12/07 : v1 envisageable en conditionnant sur le CONTENU (surprise/consensus,
hawkish-dovish) = chantier V2, prérequis dur : données de consensus historiques.

## 2026-07-11 — décision Jonas : renforcer la couche MACRO avec des données crypto-natives
Jonas juge F&G + calendrier éco insuffisants pour la crypto. À SPÉCIFIER (docs/06 + 04
d'abord) puis intégrer aux FUTURS backtests : funding rates perpétuels (historique Binance
2019+), dominance BTC, market cap stablecoins, F&G historique (alternative.me 2018+) pour
backtester le véto RISK_OFF. Chantier V1.1 — à lancer APRÈS le verdict du protocole A/B en
cours. Rappel vocabulaire acté : l'edge du PDR reste du SWING 4h/1h — « technique » = basé
prix, pas scalping ; aucun changement de timeframe.

## 2026-07-11 — PIÈGE MAJEUR : l'état fichier de risk.py contamine les backtests
Les circuit breakers persistent dans `user_data/state/` (cb_day.json, day_equity.json,
manual_restart_required). Conséquences MESURÉES : (1) chaque backtest hérite de l'état du
précédent (un `manual_restart_required` posé par un run bloque les entrées de TOUS les
suivants — B est passé de 263 à 19 trades) ; (2) des runs PARALLÈLES partageant user_data
s'écrasent mutuellement l'état → résultats invalides. TOUS les chiffres absolus des runs des
10-11/07 avant cette note sont invalides (le diagnostic G6 état/événement reste valide).
**Règles désormais** : jamais 2 backtests sur le même user_data ; purger
`state/*.json + manual_restart_required + veto/*` AVANT CHAQUE run ; pour paralléliser →
lanes isolées (state/logs/veto locaux + junctions NTFS vers data/ et strategies/,
`--userdir <lane>`), isolation VÉRIFIÉE par smoke. Depuis le 11/07 (demande Jonas) les lanes
vivent sous `backtest_lanes/run1..runN` — toujours y ranger les futures lanes. Question de fond pour Jonas/V1.1 :
le bot devrait purger lui-même cet état en mode backtest (bot_start) — non implémenté.
Correctif G6 additionnel au passage : garde « vie du trade » (l'événement ne compte que sur
une bougie entièrement postérieure à l'entrée) — sans elle, 145 sorties G6 à ~7 min.

## 2026-07-10 (soir) — décision Jonas : G6 devient un ÉVÉNEMENT
Suite au diagnostic (voir note du 10/07 ci-dessous), Jonas a choisi l'option « événement » :
G6 sort seulement quand une bougie 1h CASSE le dernier HL en clôture pendant la vie du trade.
Spec amendée (docs/03 §3.4 G6) + nouvelle colonne contractuelle `choch_bear_event_1h`
(docs/11 §11.3 + contracts.FEATURE_COLUMNS). L'état `choch_bear_1h` reste (journal/debug).
Au même tour : reprise du mode CONTRÔLE A interrompu par la limite de session (compute_sl et
partial_tp déjà faits par le coder tué — conservés ; manquent check_exit + tests).

## 2026-07-10 — backtest baseline B : G6 défectueux (état vs événement)
Run complet 2018→2026, 4 paires, détail 5m : **−49,7 %, PF 0,14, 463 trades** — et le
diagnostic est net : **402/463 sorties par G6 avec durée 0:00** (sortie à la bougie d'entrée).
Cause mesurée sur BTC 1h réel : `choch_bear_1h = close < last_hl_1h` est un ÉTAT persistant,
vrai sur **32,5 %** de toutes les bougies (l'événement de cassure, lui, = 5,1 %). La spec
(docs/03 §3.4 G6 « close 1h < dernier HL 1h pivot ») décrit un état → tel quel, G6 tue les
positions immédiatement. Le code est CONFORME à la lettre de la spec — c'est la définition
qui est à amender (état → événement, et/ou ignorer l'état pré-existant à l'entrée).
DÉCISION JONAS REQUISE avant tout changement. Run d'ablation « B moins G6 » (09 §9.1.4) :
**+0,69 %, PF 1,02, 134 trades, durée moyenne 8 j** — confirme que G6-état était le tueur
(−49,7 % → +0,7 % en le coupant). Params remis à l'état normal après le run (G6: True,
jamais commité en False). Reste sous le gate PF ≥ 1,3 : le protocole complet (BOS/CHoCH,
ablations, contrôle A) reste à dérouler APRÈS la décision G6.

## 2026-07-10 — download 2017+ : piège freqtrade `--prepend`
`download-data` ne remplit JAMAIS avant des données existantes sans `--prepend` : BTC/USDT
(qui avait déjà les 30 j du smoke) est resté à 2026-06-07 alors qu'ETH/SOL/BNB (vierges) ont
bien tout pris depuis 2017/2020. Fix : re-run ciblé
`download-data -p BTC/USDT -t 5m 1h 4h 1d --prepend --timerange 20170801-20260608`.
Vérification qui fait foi : `freqtrade list-data --exchange binance --show-timerange`.

## 2026-07-09 (2e tour) — extensions de contrat : verdict de Jonas
- n°2 (TradeState 12 champs), n°3 (contracts étendu), n°4 (compute_stake tuple), n°7
  (ev_evaluation live/dry) : **VALIDÉS tels quels**.
- n°1 signal_id : format modifié à sa demande → `BTCUSDT-2026.07.06.T120000Z` (points acceptés
  par Windows). `contracts.make_signal_id` mis à jour.
- n°5 TP2 : **Jonas choisit le TP2 RECALCULÉ à chaque bougie** (résistance 4h courante), contre
  la recommandation de la review (dérive du niveau de sortie signalée HIGH). Choix éclairé fait
  via question explicite. Spec amendée AVANT le code : docs/03 §3.3 amendement + docs/11 §11.3.
  Le `tp2` custom_data devient un enregistrement d'AUDIT. L'optimisation ML du TP reste en V2
  (docs/10 point 3, nécessite les données du dry-run).
- n°6 dust : **1.0 USDT confirmé**.
- Script de lancement demandé et livré : `start_arit.py` (racine) — ouvre les 4 process chacun
  dans sa console (services d'abord, bot ensuite). Zéro logique métier.
- Webhook Discord fourni par Jonas → placé dans `.env` (ignoré par git, vérifié par
  `git check-ignore`). ⚠️ Le webhook a transité en clair dans la conversation : le RÉGÉNÉRER
  (Discord > Intégrations > Webhooks) avant le canari, par hygiène.
- Digest « R courant » (option A : fichier d'état écrit par le bot) : retenu par défaut pour la
  V1.1 avec spread_state — Jonas n'a pas tranché explicitement A/B, à confirmer.

## 2026-07-09 — décisions de Jonas (réponses aux questions du RAPPORT_BUILD)
1. **BOS vs CHoCH (s_structure)** : trancher par l'EXPÉRIENCE — backtester DEUX versions
   (A : priorité BOS = comportement actuel · B : priorité CHoCH) sur l'historique complet,
   garder celle qui a les meilleurs résultats. → nécessite un flag de comparaison dans params
   (`S_STRUCTURE_CHOCH_PRIORITY`, défaut = comportement actuel) + 2 runs au moment du backtest
   complet. PAS ENCORE CODÉ.
3. **Service spread_state : VALIDÉ pour V1.1** (avant canari) — petit service qui écrit le
   spread dans un fichier d'état (modèle macro_state), pour réactiver le gate 03.2.3.
   PAS ENCORE CODÉ.
4. **Bollinger(20,2)_1h : ON CÂBLE** — les émettre et les journaliser = étendre docs/11 §11.3
   (colonnes) + docs/08 §8.1 (événement evaluation) + features.add_indicators + contracts.
   PAS ENCORE CODÉ.
Questions 2 (validation des extensions de contrat), 5 (script de lancement) et 6 (digest R
courant) : incomprises → réexpliquées à Jonas le 09/07, réponses en attente. AUCUN code tant
que ces réponses ne sont pas données.

## 2026-07-08 — GATE G2 run 1 : pièges freqtrade 2026.6 (à repatcher si on retombe dessus)
1. **Schéma config** : `telegram` et `api_server` avec `enabled: false` exigent QUAND MÊME leurs
   champs obligatoires (`token`/`chat_id`, `username`/`password`) — la validation plante avant
   même de charger la stratégie. **Patch appliqué** : blocs RETIRÉS de `config.dry.json`
   (bloc absent = désactivé par défaut). **Pour le dry-run réel** : réintroduire `api_server`
   (FreqUI locale, PDR 07.4) avec `username`/`password` locaux — jamais committés — sinon même
   erreur ; `telegram` reste absent (off).
   Contournement alternatif sans toucher la config (utilisé par le runner pour diagnostiquer) :
   env `FREQTRADE__TELEGRAM__TOKEN`/`__CHAT_ID` + `FREQTRADE__API_SERVER__USERNAME`/`__PASSWORD`
   factices — zéro effet runtime tant que `enabled: false`.
2. **`populate_exit_trend` obligatoire** même quand toutes les sorties passent par les callbacks
   (`custom_exit`/`custom_stoploss`) : freqtrade lève « must be implemented » au chargement.
   Patch : stub dans `AritV1.py` (df inchangé, aucune colonne exit posée).
3. **Latent, jamais atteint au run 1** : whitelist 4 paires (config) vs données BTC/USDT seul
   sur disque. Si le re-run G2 lève une exception pour données manquantes : smoke avec
   `--pairs BTC/USDT` en CLI (ne PAS modifier la whitelist contractuelle de la config).
4. Backtest 100 % local : le piège DNS/aiodns (note du 07/07) ne concerne PAS `backtesting`,
   seulement les commandes réseau (`download-data`, live/dry).

## 2026-07-07 — venv : scipy manquant · aiodns cassé sous Windows
1. `freqtrade download-data` plantait sur `ModuleNotFoundError: scipy` (import module-level de
   `freqtrade/data/metrics.py`, non tiré par l'install initiale) → `pip install scipy` (1.18.0).
2. Puis `aiodns.error.DNSError: Could not contact DNS servers` : le résolveur c-ares d'aiodns ne lit
   pas la config DNS de cette machine (problème connu c-ares/Windows) — testé hors sandbox, même échec,
   alors que curl/résolveur système passent. Fix : `pip uninstall aiodns` → aiohttp/ccxt retombe sur le
   ThreadedResolver (DNS système). Ne PAS réinstaller aiodns dans ce venv.

## 2026-07-06 — venv hors OneDrive
**Décision** : venv à `C:\Users\jofar\venvs\arit`, pas dans le repo.
**Pourquoi** : le repo vit dans OneDrive ; un venv freqtrade ≈ dizaines de milliers de fichiers que OneDrive synchronise et verrouille (échecs pip aléatoires, CPU). `venv/` reste dans .gitignore au cas où.

## 2026-07-06 — docs/ restaurés depuis Downloads
`ARIT2.0\ARIT_PDR_v3\` (dézippé à la main) était incomplet : 11 fichiers, sans `modules/` ni `11_sync_orchestration.md` — la Phase 0 exigeait un STOP. Versions complètes trouvées dans `Downloads` : `ARIT_PDR_v3_1.zip` et `_v3_2.zip` sont hash-identiques → `docs/` extrait de `_v3_2`. Comptage réel : 22 .md (le prompt dit « 23 fichiers ») — écart signalé, non bloquant.

## 2026-07-06 — Phase 1 : trois décisions de contrat (à connaître avant de coder)
1. **`signal_id` normalisé Windows** : M06 dit `f"{pair}-{ts_4h}"`, mais le signal_id sert de nom de fichier (`user_data/veto/<signal_id>.flag`) et `/` + `:` sont interdits dans un nom de fichier → format retenu `BTCUSDT-20260706T120000Z` (`contracts.make_signal_id`).
2. **`TradeState` = 11 champs de 11.3** (pas les 9 de M05) : 11.3 est LE contrat custom_data ; M05 en omettait `trade_no` et `entry_conviction`, nécessaires au journal/sizing. Défini dans `contracts.py` (le prompt de build l'y place), gestion.py l'IMPORTE au lieu de le redéfinir.
3. **`s_structure` « contexte TREND »** (PDR 05.1) : features.py est pur et n'a pas accès au macro_state → « contexte TREND » = conditions prix du régime TREND (ADX≥25, EMA50>EMA200, close>EMA50). Le veto macro/F&G reste dans regimes.py. Écart documenté, à confirmer par Jonas au rapport.

## 2026-07-06 — point de review T4 (G4, à vérifier au GATE G1)
Le coder T4 fait retourner à `partial_tp` `−(0.5 × amount × open_rate)` (« 50 % du stake d'entrée »). Le PDR 03.4 G4 dit « vendre **50 % de la quantité** » : via `adjust_trade_position`, freqtrade convertit le stake négatif au PRIX COURANT → à +1,5R ça vend MOINS de 50 % des coins. Correction attendue si confirmé : dériver `current_rate = entry + profit_r × (entry − initial_sl)` (possible dans la signature M05) et retourner `−(0.5 × amount × current_rate)`. → transmis au reviewer T4.

## 2026-07-06 — point de review T3 (CB séquentiel, à vérifier au GATE G1)
Le coder T3 laisse « la fenêtre 12 bougies / 5 trades à charge de M07 » : `cb_sequential_state(Trade)` (signature M04 sans `now`) ne peut pas dire seul si le cooldown est actif. M07 doit rester SANS logique métier → correction attendue si confirmé : param optionnel `now=None` injecté (cohérent avec le reste du module) et `(cooldown_active, risk_divisor)` entièrement dérivés de la DB dans risk.py. → transmis au reviewer T3.

## 2026-07-06 — point de review T5 (journal, à vérifier au GATE G1)
Actés côté contrats : enveloppe `event_type` + `signal_id` ajouté aux champs requis d'`evaluation` (contracts.py mis à jour — reconstruction de cycle M06 impossible sinon). Reste à corriger côté module si confirmé : `ev_gate_check` dérive `pair` du signal_id → donne « BTCUSDT » alors que tous les autres événements portent « BTC/USDT » (dataset V2 incohérent) ; correction attendue : param `pair` explicite dans `ev_gate_check`. → transmis au reviewer T5.

## 2026-07-06 — note d'intégration T2 → M07 (Phase 3)
`cio.explain(row)` lit `fear_greed`/`macro_stale` depuis la row, mais classify n'écrit que ses 3 colonnes (11.3) : la stratégie devra fusionner ces 2 valeurs du macro_state dans le dict `explain` avant `ev_evaluation` (sinon `regime_inputs` sera null). À inclure dans le prompt du coder M07.

## 2026-07-06 — extensions de contrat ACTÉES (review risk, à valider par Jonas au rapport)
Ajoutées à `contracts.py` (noms canoniques, risk.py doit les importer) : `CB_DAY_FILE = "state/cb_day.json"` · `VETO_INTENT_SUFFIX = ".intent"` · `SKIP_ZERO_STOP_DISTANCE`. Également actée : la signature `compute_stake(...) -> (stake|None, raison|None)` (écart vs M04 `-> float`, nécessaire pour journaliser `skip_min_notional`) — **le prompt du coder M07 devra explicitement déballer le tuple et journaliser le skip**.

## 2026-07-06 — T1 features : deux points remontés par le coder
1. **Bollinger(20,2)_1h non émises** : PDR 05.3 les veut « calculées et journalisées », mais ni M01 (signatures), ni 11.3 (colonnes), ni 08.1 (schéma evaluation) ne les câblent. Non implémenté = écart documenté pour le RAPPORT (décision Jonas : les ajouter = étendre 11.3 + 08.1 d'abord).
2. **`hh_hl_intact_4h`** : colonne intermédiaire de track_structure (étiquettes HH/HL prévues par M01) consommée par s_structure — extension de fait de la liste 11.3, à vérifier en review et à acter si PASS.

## 2026-07-06 — reviews GATE G1 (1er passage) & incident quota
Verdicts reviewers : regimes+cio FAIL (littéral `50` → corrigé par l'orchestrateur : `params.FG_NEUTRAL_BACKTEST`, re-vérifié 33 tests verts + ruff) · gestion FAIL (G4 vendait 50 % du stake d'entrée, pas 50 % de la quantité — renvoyé au coder) · journal FAIL (pair « BTCUSDT » incohérent dans gate_check, json.dumps hors garde — renvoyé au coder) · risk : review interrompue par la limite de session, relancée.
Leçon : la limite de session (reset 21:50) a tué T1 ×2 et la review risk EN VOL — les transcripts d'agents survivent, reprise par SendMessage sans perte. Ne pas relancer un agent from scratch avant d'avoir vérifié son transcript/l'état disque.

## 2026-07-06 — sous-agents via l'outil Agent
Session lancée depuis `C:\Users\jofar` → les `.claude/agents/` du repo ne sont pas chargés (chargement au démarrage seulement). Reproduction fidèle : outil Agent, modèle Opus, spec du `.md` injectée en tête de prompt. Pour une future session : lancer `claude` DANS le repo.
