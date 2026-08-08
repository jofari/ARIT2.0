# DECISIONS.md — journal des arbitrages de Jonas

> **But** : un arbitrage de Jonas ne doit JAMAIS vivre uniquement dans une conversation.
> Toute décision est écrite ici le jour où elle est prise, avec ce qu'elle implique et son
> état d'application. Ce fichier est versionné : il survit à un `/clear`, à un changement de
> modèle et à une réinstallation.
>
> **Règle** : une décision n'est « fermée » que quand la colonne *État* dit `appliqué` et
> cite le commit. `acté` = tranché mais pas encore codé. `reporté` = volontairement remis.
>
> Lecture au démarrage de session : ce fichier, puis `research/pistes_2026-07-31/CHANTIERS.md`.

---

## Session du 2026-08-03 — réponses aux décisions A1-A8 et C1-C8

Source : arbitrages donnés par Jonas le 03/08 au soir, en réponse à l'inventaire
`research/pistes_2026-07-31/CHANTIERS.md`.

### A — Décisions de conception

| # | Décision de Jonas | État | Trace |
|---|---|---|---|
| A1 | `startup_candle_count` = **999** bougies, pour la précision | appliqué | `325a906` |
| A2 | Retirer les fractals bruts du DataFrame **+ autoriser le bot à shorter (long ET short)** | pivots : appliqué `39bc8cc` · short : **appliqué le 04/08** | voir A2-bis et session 04/08 |
| A3 | Indice actions = **NASDAQ100** (pas SP500) | appliqué | `7406a83` |
| A4 | Bloc corrélation macro **fusionné**, en fail-safe | appliqué | `0e3b0e4` |
| A5 | Véto macro HOSTILE seul : **non, pas seul** → la pénalité NEUTRE est CONSERVÉE | acté, aucun code à changer | `cio.py:31` inchangé |
| A6 | Sizing : **risque constant à 1,16 %** (Kelly plein) pour la V1 | appliqué | `docs/03 §3.1.0` + `params.RISK_CONSTANT_PCT` |
| A7 | Hypothèse d'edge : **H1 + une partie de H2** — voir la formulation ci-dessous | appliqué (signé) | `docs/01_edge.md` v4 |
| A8 | G-rules : à retravailler, mais **priorité aux autres paramètres** | reporté | — |

#### A2-bis — le short (décision du 03/08)

Jonas : « long et short ». Ce n'est pas un drapeau. Périmètre réel :
`can_short = False` (`AritV1.py:42`) et `user_data/config.dry.json` sans `trading_mode`
(donc **spot** par défaut). Il faut passer en `futures` / `isolated`, rendre la géométrie
SL/TP symétrique, revoir le sens du véto macro, le sizing, les 7 règles G, et une partie
des 231 tests.

⚠️ **Cette décision est une dépendance de A7, pas une option** : si la macro donne la
direction, un signal macro baissier est inexploitable sans short.

#### A6-bis — risque constant à 1,16 %

Jonas a choisi **le Kelly plein (1,16 %)** en connaissance du fait que le PDR impose
½ Kelly. Conséquence obligatoire : **amender `docs/03_risque.md` AVANT de toucher
`risk.py`** — sinon on viole l'interdit n°4 (« aucune valeur magique, tout paramètre
vit dans `docs/` d'abord »). Remplace l'interpolation conviction-dépendante de
`risk.py:107`.

Le risque **adaptatif** (piloté par le module quant) est explicitement renvoyé à plus
tard : chantier V2, à ouvrir après la V1.

#### A7-bis — l'hypothèse d'edge retenue (formulation de Jonas, 03/08)

> **La macro détermine la DIRECTION de la position (long ou short). La technique
> détermine le MOMENT d'entrée et le moment de sortie.**
>
> Exemple donné : BTC atteint un seuil intéressant, la macro est haussière, les
> indicateurs techniques (volume, gamma, MACD, RSI) sont majoritairement haussiers
> → entrée en position.

Composition : **H1** (l'edge est dans la géométrie du couple stop/cible, seule déviation
positive au modèle nul, z = 1,74) **+ une partie de H2** (le régime macro conditionne,
p = 0,095, le seul signal non-bruit).

Ce que ça implique et qui reste à trancher :
- il faut un **critère de falsification chiffré** pour que `docs/01_edge.md` soit signable
  (le doc actuel exige « si B ≤ A : hypothèse invalidée, pas de rationalisation ») ;
- « gamma » n'existe pas nativement en crypto spot (c'est une grandeur d'options) —
  à remplacer ou à définir ;
- la séparation direction/timing change le rôle du score de conviction : il ne sélectionne
  plus la direction, il ne fait plus que temporiser.

### C — Dettes techniques

| # | Décision de Jonas | État |
|---|---|---|
| C1 | Calendrier éco : **JSON statique annuel embarqué (FOMC + BLS) en source primaire**, ForexFactory hebdo en secondaire, fetch async 1×/semaine, cache local, **jamais appelé depuis le pipeline temps réel**. Échec du fetch FF ⇒ on continue sur la primaire sans dégrader le blocage des trois événements qui comptent. Remplace `FINNHUB_KEY`. | à coder |
| C2 | Spread state : **mesurer d'abord les conséquences** avant de décider | analyse à faire |
| C3 | Bollinger : **câbler d'urgence** | appliqué le 03/08 (`bb_*_1h`, journalisées, non décisionnelles) |
| C4 | Force S/R par nombre de touches : **annulé** | à retirer |
| C5 | Fraîcheur du signal 4h : **annulé** | à retirer |
| C6 | Jonas visait le **bloc corrélation c6/c7** (livré par A4). Le C6 de `CHANTIERS.md` — les **protections freqtrade** — était donc resté ouvert. | **appliqué le 04/08** — `params.PROTECTIONS`, `docs/07 §7.1.1` |
| C7 | Webhook Discord : **régénérer** | action de Jonas |
| C8 | `Untitled-1.py` : supprimer si problématique | **sans objet** — vérifié, le fichier n'existe plus |

### B — Chantiers de mesure

Aucune réponse donnée sur B1-B17. Restent ouverts tels quels dans `CHANTIERS.md`.

---

## Écarts constatés entre les réponses et l'état réel du code

Consignés parce qu'ils se reproduiront si on ne les note pas :

1. **A7 n'avait PAS été appliqué** contrairement au souvenir de Jonas : `docs/01_edge.md`
   n'a pas bougé depuis le 06/07 (`d5b0340`) et H1/H2/H3 n'existaient que comme propositions
   dans `research/pistes_2026-07-31/RAPPORT.md:571-591`.
2. **C6 était une collision de noms** : le `c6` du bloc corrélation macro (livré) contre le
   `C6` des protections freqtrade (jamais codé).
3. **A5 était à moitié fait sans que ce soit dit** : la règle de décision n'a pas bougé, mais
   l'instrumentation qui permet de trancher A5 par filtrage d'un seul run a été livrée avec
   A4 (journal schéma v1 → v2, `contracts.py:105`).

---

## Session du 2026-08-04 — application de C6 et du short (A2)

Aucune décision NOUVELLE de Jonas ce jour : cette session applique des arbitrages déjà
signés le 03/08. Ce qui suit est l'état d'application, plus les points que l'application a
révélés et qui n'étaient couverts par aucune réponse.

### C6 — protections freqtrade : FERMÉ
Câblées dans `params.PROTECTIONS`, consommées par `AritV1.protections`. Vérifié **sur le
freqtrade installé (2026.6)**, pas sur la doc : la liste vit dans la STRATÉGIE, plus dans
`config.json`. Valeurs et justification : `docs/07 §7.1.1`.

Point important démontré au passage : **le natif et le custom ne sont pas redondants**.
`StoplossGuard` compte les sorties au stop quel que soit leur R ; `risk.cb_sequential_state`
compte toute clôture ≤ −0,8R (donc aussi G6/G7) et exige qu'elles soient consécutives. Le
sizing ÷2 pendant 5 trades reste hors de portée de toute protection native.

⚠️ **`--enable-protections` devient obligatoire en backtest** (07.2). Sans le drapeau,
freqtrade ignore silencieusement les protections : le backtest ne mesure plus le même
produit que le dry-run.

### A2 — le short : CODÉ, non mesuré
Livré de bout en bout : features baissières miroirs, direction macro, géométrie symétrique
(SL/TP/R/MAE/MFE/G1-G7), sizing, journal v3, `trading_mode: futures`. Specs :
`docs/03 §3.7`, `docs/05 §5.6`, `docs/08 §8.6`, `docs/11 §11.7`. 297 tests verts, ruff
propre, `AritV1.py` ramené à 248 lignes (il était à 262, hors contrat depuis A4).

Deux bugs LATENTS trouvés en codant, qui auraient cassé le short en silence :
1. `order_filled` rejetait les entrées short. Un short entre en **SELL** ; le code lisait
   tout `ft_order_side == "sell"` comme une sortie G4 partielle et sortait avant d'écrire
   le `custom_data`. Aucun short n'aurait eu de `initial_sl` — donc aucune gestion.
2. `make_signal_id` ne normalisait pas le `:` des paires perpétuelles, contrairement à ce
   que promettait sa docstring. `BTC/USDT:USDT` produisait un `signal_id` contenant `:`,
   illégal en nom de fichier Windows ⇒ `OSError` à la création de `veto/<id>.intent`.

### Trois décisions que l'application a rendues nécessaires — À VALIDER

- **A2-ter — LEVIER.** Le short impose les futures. J'ai gardé le défaut freqtrade
  (`leverage() → 1.0`), donc l'exposition reste celle du spot. Un levier > 1 est une
  décision de risque qui t'appartient. Conséquence si on reste à 1 : quand la distance de
  stop est très serrée, le stake calculé dépasse l'équité, freqtrade le plafonne, et le
  risque réel devient **inférieur** à 1,16 % sans le dire. (`docs/03 §3.7.4`)
- **A2-quater — véto actions c6/c7 en HOSTILE.** J'ai gardé le véto actions comme un
  coupe-circuit des DEUX sens (il force toujours RISK_OFF), alors que HOSTILE, lui,
  autorise désormais le short. Raison : le bloc c6/c7 est un fail-safe de corrélation, pas
  un avis directionnel. Si tu penses qu'une cassure du NASDAQ corrélée au BTC est un signal
  de SHORT et pas un signal de « ne rien faire », c'est à changer — et ça se teste seul,
  le véto est ablatable par construction (A4).
- **A2-quinquies — RISK_OFF sur Fear & Greed < 25.** Même question : la peur extrême reste
  aujourd'hui un « on ne trade pas ». En v4 elle pourrait être un signal de short. Non
  touché, faute de réponse.

### Bloquants découverts, à traiter avant tout dry-run
1. **Parité backtest/live rompue** (`docs/11 §11.7`) : le régime macro V1.1 n'existe qu'en
   backtest. En live, `macro_state.json` ne le porte pas ⇒ **le live est long-only alors que
   le backtest est long+short**. C'est M08 qu'il faut compléter, et c'est prioritaire : sans
   ça, le dry-run ne teste pas le produit qu'on a mesuré.
2. **Données OHLCV futures manquantes** : `user_data/data/binance/futures/` ne contient que
   BTC en 4h et 5m. Il faut les 4 paires en 5m/1h/4h/1d avant tout backtest en futures :
   `freqtrade download-data --exchange binance --trading-mode futures -p BTC/USDT:USDT
   ETH/USDT:USDT SOL/USDT:USDT BNB/USDT:USDT -t 5m 1h 4h 1d --timerange 20200101-`
3. **`check_bias.py` n'a pas pu tourner** sur la nouvelle config (mêmes données manquantes).
   Le zéro-look-ahead des colonnes A2 est prouvé au niveau feature par recalcul sur données
   tronquées (`test_colonnes_baissieres_ne_repeignent_pas`), ce qui est fort mais **n'est
   pas** le `lookahead-analysis` de bout en bout. À relancer dès les données présentes.

### C1 — calendrier économique : CODÉ (couverture CPI/NFP à compléter)
`services/calendar_source.py` + `user_data/calendar/economic_calendar.json`. Finnhub retiré
du code (57 lignes). Spec : `docs/06 §6.6`. Le run horaire ne fait **aucun** appel réseau
pour le calendrier ; le fetch ForexFactory est une tâche hebdomadaire séparée.

Vérifié de bout en bout sur le flux réel le 04/08 : 16 FOMC (primaire) + la NFP du
2026-08-07 (secondaire), fusionnés, dédoublonnés, triés. La dégradation FF a été observée en
conditions réelles (rate-limit) : warning, cache précédent conservé, primaire intacte.

⚠️ **Ce qu'il reste à faire, et c'est toi qui peux le faire vite** : `bls.gov` refuse les
récupérations automatisées (HTTP 403). Je n'ai pas inventé les dates. Il faut copier les
dates 2026-2027 de `bls.gov/schedule/news_release/cpi.htm` (CPI) et `.../empsit.htm` (NFP)
dans `economic_calendar.json` — publication à 08:30 US Eastern. Tant que ce n'est pas fait,
la couverture CPI/NFP dépend de ForexFactory, **qui ne voit que la semaine en cours** : un
CPI à J+20 n'est connu de personne. `coverage_gaps()` le signale en `ERROR` à chaque run.

Piège trouvé et corrigé : ForexFactory identifie le pays par **code devise** (`USD`), pas
par code pays. Le filtre initial sur `"US"` laissait passer zéro événement **en silence**.

### C2 — spread : ANALYSÉ, pas codé (c'est ce que tu avais demandé)
Rapport complet : `research/pistes_2026-07-31/C2_spread_analyse.md`. Résumé :

1. La porte est **inerte**, pas cassée : `AritV1` passe `spread_frac = None` en dur.
2. `docs/11 §11.5` interdit le réseau dans les callbacks ⇒ le spread devrait passer par un
   service de fond, donc être **toujours périmé** — sur la grandeur la plus volatile du
   système. Et il faudrait choisir une politique de panne : service mort ⇒ on bloque tout,
   ou on ne bloque rien. Il n'y a pas de troisième option.
3. **Le vrai coût** : les données OHLCV n'ont pas de carnet d'ordres ⇒ une porte spread
   existe en live et **pas en backtest**. On fabriquerait volontairement la divergence
   live/backtest que `docs/09` surveille comme critère d'invalidation.
4. Ordre de grandeur : sur BTC/ETH/SOL/BNB perp, le spread est ~10× sous le seuil de
   0,05 % en régime normal. La porte ne mordrait qu'en stress — déjà couvert en grande
   partie par la fenêtre news et les circuit breakers.

**Recommandation** : ne pas coder. Faire comme pour les Bollinger (C3) — **journaliser sans
décider** au démarrage du dry-run, mesurer la distribution réelle, puis trancher avec des
chiffres. Sur un substrat à espérance nulle, tout filtre qui réduit l'exposition *paraît*
positif : l'activer sans mesure, ce serait s'acheter une illusion.

**À valider par toi** : d'accord pour laisser la porte inerte jusqu'à la mesure ?
→ **Répondu le 04/08 : OUI.** Voir la session ci-dessous.

---

## Session du 2026-08-04 (soir) — fermeture de TOUTES les dettes C

Consigne de Jonas : « on ferme tous les C ». Quatre dettes restaient ouvertes (C1, C2, C7,
C9) ; les cinq autres (C3, C4, C5, C6, C8) l'étaient déjà. **Les quatre sont fermées.**

| # | Décision de Jonas | État |
|---|---|---|
| C1 | Retrouver les dates CPI/NFP en ligne **et surtout ajouter tous les événements marqués en ROUGE sur ForexFactory, au minimum** | **appliqué** |
| C2 | Porte spread : laisser inerte + journaliser | **acté**, aucun code à changer |
| C7 | Webhook régénéré, l'ancien est supprimé | **fermé** |
| C9 | Installer optuna + plotly | **appliqué** |

### C1 — élargissement du calendrier : TOUS les rouges

C'est un **changement de doctrine**, pas un correctif. `fetch_forexfactory()` appliquait deux
filtres en plus de l'impact ; les deux sont **retirés** :

1. **Filtre de NOM** (`_is_relevant`) — ne gardait que FOMC/CPI/NFP + `NEWS_KEYWORDS`. Un
   rouge « Retail Sales » ou « ISM Manufacturing PMI » était ignoré alors qu'il bouge le
   marché. Fonction supprimée (plus aucun appelant).
2. **Filtre PAYS** (`_US_COUNTRIES`) — ne gardait que `USD`. Une décision BCE ou BoE rouge
   passait à la trappe. Constante supprimée ; la devise est désormais **conservée** dans le
   champ `devise` de chaque événement, pour pouvoir re-filtrer plus tard sur des mesures
   plutôt que sur un a priori.

⚠️ **Conséquence assumée** : beaucoup plus d'événements bloquants (fenêtre ±30 min). Le
premier fetch réel a ramené 8 rouges sur la semaine, dont 2 NZD et 2 CAD qui auraient été
jetés avant. Sur-bloquer plutôt que rater un rouge — c'est le compromis choisi.
Verrouillé par `test_fetch_ff_garde_tous_les_rouges_toutes_devises` : remettre un filtre
serait invisible autrement.

**Dates CPI/NFP 2026 renseignées** — 24 événements ajoutés à la primaire (16 → 40).
`bls.gov` refuse toujours tout (403 sur `requests` **et** sur WebFetch), donc les dates
viennent de sources **secondaires concordantes**, et c'est écrit dans le fichier :
`usinflationcalculator.com` (qui recopie le BLS), recoupé pour les dates passées avec les
URL d'archives `bls.gov/news.release/archives/empsit_*`. DST 2026 appliquée (EDT du 08/03
au 01/11), publication 08:30 US Eastern.

⚠️ **2027 non couvert** : le BLS publie son calendrier annuel fin 2026. À compléter à ce
moment-là, sinon la couverture CPI/NFP retombe sur ForexFactory, qui ne voit qu'une semaine.

**Résultat mesuré** : `calendar_source.py` sort en **code 0** (plus aucun trou), 46
événements fusionnés, et `macro_state.py` ne logue plus ni warning ni erreur.

### C2 — porte spread : fermée en « acte de non-codage »

Jonas a suivi la recommandation : la porte reste inerte, on journalisera la distribution
réelle du spread au démarrage du dry-run sans qu'elle décide quoi que ce soit, puis on
tranchera avec des chiffres — même traitement que les Bollinger (C3). Motif retenu : sur un
substrat à espérance nulle, tout filtre qui réduit l'exposition *paraît* positif ; l'activer
sans mesure, c'est s'acheter une illusion. **Aucune ligne de code à écrire, et c'est le
résultat.** La gate 3 reste dans `GATE_NAMES` — elle est traversée sans être évaluée.

### C7 — webhook : fermé
Régénéré par Jonas, l'ancien est supprimé côté Discord. Nouveau webhook en `.env`
(gitignoré). Rapport de backtest envoyé et reçu le 04/08.

### C9 — outillage : fermé
`optuna` et `plotly` installés dans `C:\Users\jofar\venvs\arit`. `freqtrade plot-dataframe`,
`plot-profit` et `hyperopt` redeviennent utilisables. ⚠️ Rappel : l'interdit n°5 interdit
d'hyperopter G1-G7 et les poids — l'outil ne sert qu'au reste.

### C1-bis — la liste des indicateurs SUIVIS (Jonas, 04/08 au soir)

Jonas a fourni un glossaire de ~25 indicateurs macro avec « voilà les données que je veux au
minimum ajouter ». Problème constaté : **la plupart ne sont pas rouges sur ForexFactory**
(PPI, Retail Sales, Industrial Production, KOF, SPPI, ADP, Unemployment Claims sont oranges
ou jaunes), donc le filtre `impact == "high"` les jetait tous, même après l'élargissement.

D'où `WATCHED_EVENTS` (24 fragments de noms → libellés) : ces indicateurs sont capturés
**quelle que soit leur couleur**.

**Palier orange — le garde-fou qui compte.** Un événement suivi ne devient bloquant que si
FF le classe déjà `high` ou `medium`. Mesuré sur le flux réel du 04/08 :

| Règle | Événements capturés | Bloquants | Part du temps calendaire bloquée |
|---|---|---|---|
| Sans palier (tout suivi promu) | 40 | **40** | **~24 %** |
| **Avec palier orange (retenu)** | 40 | **11** | **~7 %** |

Sans le palier, la semaine bloquait sur « Spanish Manufacturing PMI », « Italian Services
PMI » et « French Final Services PMI » — les PMI nationaux européens sont publiés en cascade
et n'ont aucun effet mesurable sur le BTC. Les 11 bloquants retenus couvrent bien tous les
indicateurs qui comptent de la liste : ISM Manufacturing, ADP, ISM Services, Unemployment
Claims, NFP, Employment Change.

Les `low` restent **dans** le calendrier avec `impact: "low"` (donc non bloquants) : la
donnée est là pour mesurer plus tard, sans re-fetch, ce que le palier a coûté ou évité.
`impact_ff` conserve la couleur d'origine de chaque événement.

⚠️ **Deux retours en arrière possibles, tous deux à un endroit unique** : vider
`WATCHED_EVENTS` ramène à « les rouges seuls » ; changer `bloquant` en `impact_ff == "high"`
ramène à l'ancien filtre. Verrouillé par
`test_liste_suivie_capture_les_oranges_mais_pas_les_low`.

**À valider par toi** : d'accord pour le palier orange, ou tu veux que les `low` bloquent
aussi (~24 % du temps) ?

### État après cette session
**Aucune dette C ouverte.** 320 tests verts, ruff propre.

---

## Session du 2026-08-07 — parité live/backtest + dry-run non surveillé

**Contexte** : Jonas part en vacances et doit déconnecter. Objectif donné : fermer les
chantiers et lancer le dry-run pendant son absence.

### Décisions de Jonas (07/08)

| # | Question posée | Réponse | Conséquence |
|---|---|---|---|
| V1 | Périmètre avant départ | **Minimum opérationnel + combler la parité live/backtest** | du code métier neuf embarqué sans surveillance ; recommandation inverse donnée et écartée en connaissance de cause |
| V2 | Remontée Discord pendant l'absence | **Alertes critiques seulement** | le watchdog alerte sur bot mort / exposition anormale ; aucun résumé quotidien |

> ⚠️ Sur V1 j'avais recommandé le périmètre réduit (ne pas toucher à la parité la veille
> d'une déconnexion). Jonas a tranché pour le périmètre large. Compensation appliquée :
> fail-safes durcis et 36 tests ajoutés (320 → 356).

### Ce qui a été fait

**1. Parité live/backtest comblée (le BLOCANT déclaré du dry-run).**
`AritV1.py:58` ne posait la colonne macro qu'en backtest (`df if live`), donc
`cio.direction_macro` retombait sur son fail-safe long-only : le live et le backtest étaient
**deux produits différents** depuis A2. Désormais `macro_regime.attach_regime_now()` pose le
régime en live, calculé par `regime_now()` depuis les 5 scores 06.2 que
`services/macro_state.py` écrit maintenant dans `macro_state.json`.

**2. Collision de schéma évitée — le piège le plus dangereux de la session.**
`fear_greed` existe dans les DEUX schémas avec des sens incompatibles : indice **brut**
0-100 en 06.3, score **{-1,0,1}** en 06.2. Passer le dict à plat à `regime_now()` aurait fait
sommer un F&G de 50 comme +50 ⇒ **PORTEUR en permanence**, donc long autorisé quelle que soit
la macro réelle. Les scores vivent donc dans un sous-objet `contracts.MACRO_SCORES_KEY`
(`macro_scores`), jamais à plat. Verrouillé par
`test_regime_from_state_ne_melange_pas_les_deux_schemas`.

**3. Fail-safe de donnée en live (`regimes.donnee_non_fiable`).**
Depuis A2, HOSTILE ne bloque plus rien — il **autorise le short**. Or `regime_now()` renvoie
justement HOSTILE quand l'état est périmé ou sans scores. Sans garde-fou, une source macro
tombée aurait fait **shorter le bot en aveugle pendant des semaines**. `classify` force
désormais RISK_OFF (les deux sens coupés, comme le véto actions c6/c7) si l'état est `stale`,
`risk_off`, si F&G < 25, **ou si les 5 scores sont absents**. Cette dernière clause est une
défense en profondeur : elle ne suppose pas que le producteur soit à jour — cas constaté en
vrai le 07/08, un `macro_state.json` d'ancienne version portant `stale: false` sans scores.

**4. Bug FRED — panne silencieuse depuis le 2026-07-12.**
`scripts/download_macro.py` envoyait `User-Agent: ARIT-macro/1.0` à toutes les sources.
FRED met cet UA au trou noir : **ReadTimeout à 40 s, reproductible**, alors qu'il répond en
**0,1 s sans en-tête**. Conséquence : `dxy` et `taux` — 2 des 5 composants macro — n'étaient
plus rafraîchis depuis un mois, et `daily_regimes` les scorait à 0 **sans que rien ne le
signale**. `dl_fred` n'envoie plus d'UA. Les 8 fichiers macro sont à jour au 07/08.

**5. Opérationnel — le dry-run pouvait tourner 2 h puis ne plus rien faire.**
`services/macro_state.py` est un one-shot **par design** (docstring : « lancé par le Task
Scheduler toutes les heures ») — mais **la tâche planifiée n'avait jamais été créée**.
`start_arit.py` le lançait une fois ; passé `CALENDAR_STALE_HOURS = 2`, l'état devenait stale
⇒ RISK_OFF ⇒ **plus aucune entrée**, sans alerte. Le watchdog ne rattrape pas ce cas : il
surveille le heartbeat, il ne relance aucun service. Créé :

| Mécanisme | Rôle |
|---|---|
| Tâche `ARIT macro_state` (horaire) | rafraîchit `macro_state.json` — sans elle le bot se fige |
| Tâche `ARIT download_macro` (quotidienne 06:15) | alimente les 5 composants ; historique > 48 h ⇒ scores refusés ⇒ repos |
| `%APPDATA%\...\Startup\ARIT_relance.cmd` | relance les 4 process après un redémarrage Windows Update |
| `start_arit.py --si-absent` | garde-fou anti-doublon (`tasklist`) : ne relance rien si un freqtrade tourne |

> La tâche « à l'ouverture de session » a été refusée par Windows (**Accès refusé** — un
> déclencheur `AtLogOn` exige l'élévation). Contournée par le dossier Démarrage, qui ne
> demande aucun droit. Supprimer `ARIT_relance.cmd` suffit à désactiver la relance.

### Ce qui reste ouvert — à lire au retour

1. **Le dry-run exige que le PC reste allumé ET la session ouverte.** Les 4 process vivent
   dans des consoles utilisateur ; le dossier Démarrage ne se déclenche qu'à l'ouverture de
   session. Un redémarrage sans reconnexion automatique = tout est arrêté jusqu'au retour.
2. **Données OHLCV futures toujours manquantes** pour 3 paires sur 4 (seul BTC en 4h/5m).
   Sans elles, aucun backtest futures et `check_bias.py` ne peut pas re-tourner. N'empêche
   pas le dry-run (freqtrade télécharge le live lui-même), empêche la **validation**.
3. **Chantiers B1→B17 et D1→D4 intacts** — dont le walk-forward (B13/D2), prérequis déclaré
   du dry-run. A8 toujours reporté. Le dry-run lancé produit des **données**, il ne valide
   aucune hypothèse.
4. **`user_data/decisions/` était vide** : c'est précisément le jeu d'évaluations dont
   dépendent B8 (N ≥ 400 signaux), B9 (audit d'IC) et toute piste ML. C'est le gain principal
   de cette absence.

### État après cette session
**356 tests verts** (320 → 356), ruff propre. Parité live/backtest **comblée**.

### Correctif du 07/08 au soir — la remontée Discord était morte

Découvert en vérifiant la décision V2 juste après le lancement.

**`watchdog.alert()` sortait en silence.** Il lisait `DISCORD_WEBHOOK_URL` dans
`os.environ` (`services/watchdog.py`), mais la variable n'existe **dans aucune portée**
Windows — ni `User`, ni `Machine`, ni process. Les secrets ne vivent que dans `.env`, et
**rien ne chargeait `.env`** dans l'environnement des services lancés par `start_arit.py`.
Le watchdog tournait, ne trouvait pas d'URL, et retournait sur `if not url: return`. C'est
la panne la plus coûteuse possible pour un filet de sécurité : muette.

Corrigé par `watchdog._webhook_url()` — environnement d'abord, sinon relecture directe de
`.env`. **Lecture inline, sans import** : l'invariant M10 nº1 interdit tout import du projet
à ce fichier et assume explicitement la duplication. Une alerte non envoyée journalise
désormais `ALERTE NON ENVOYEE` au lieu de disparaître. 4 tests ajoutés.

Le secret n'a **pas** été recopié dans les variables d'environnement Windows : le registre
les expose à tout process enfant et à tout dump, alors que `.env` est la source unique
documentée.

### Constat non corrigé — `services/discord_bot.py` ne démarre pas

Le fichier n'a **aucun point d'entrée** : ni `if __name__ == "__main__"`, ni `client.run()`,
ni instanciation de `Client`. C'est une bibliothèque de fonctions (testée) que
`start_arit.py` lance comme un service — le process se termine donc aussitôt. Vérifié après
lancement : seuls `watchdog.py` et `freqtrade` tournent.

**Volontairement non corrigé le 07/08** : écrire et brancher un service Discord la veille
d'une déconnexion, sans personne pour le surveiller, est exactement le risque qu'on cherche
à éviter. Sans conséquence sur la décision V2 : les alertes critiques viennent du
**watchdog**, pas de ce bot. Ce que M09 apporterait — le digest quotidien — est précisément
ce que Jonas a décliné en choisissant « critiques seulement ».

À traiter au retour, avec le reste de M09.

### Correctif du 07/08 (2) — le watchdog ne pouvait PAS alerter en dry-run

Signalé par Jonas depuis la console du watchdog :
`WARNING:__main__:watchdog: clefs ccxt absentes - mode alerte seule`.

Le message lui-même est **normal** en dry-run (pas de clés ⇒ pas de lecture d'exposition,
pas de *flatten* — ce qui n'a aucun sens sur de l'argent papier). Mais en tirant le fil :

```python
def is_breach(age, holdings) -> bool:
    return age > HEARTBEAT_MAX_S and bool(holdings)   # <-- "and bool(holdings)"
```

Sans clés ccxt, `open_exposure` renvoie **toujours** `[]`, donc `is_breach` est **toujours
faux**, donc le watchdog **n'alerte jamais** — même bot mort. La décision V2 (« alertes
critiques seulement ») était **structurellement vide** : trois semaines de silence garanti,
que le bot tourne ou qu'il soit mort depuis le deuxième jour.

Corrigé en **séparant prévenir et agir**, plutôt qu'en affaiblissant M10 :

| Fonction | Condition | Rôle |
|---|---|---|
| `is_breach` (inchangée) | heartbeat vieux **ET** exposition | déclenche le **flatten** — on ne liquide que ce qui existe |
| `bot_silencieux` (nouvelle) | heartbeat vieux, **sans condition d'exposition** | déclenche l'**alerte** |

`surveiller_liveness()` n'émet qu'**une** alerte par épisode + une à la reprise : sans ça, un
bot mort le 2e jour d'une absence de trois semaines produirait ~30 000 messages Discord.
Même garde anti-faux-positif que le flatten (`CONFIRM_READS` lectures). 6 tests ajoutés.

⚠️ **Non résolu à cette heure** : `freqtrade` tourne mais n'écrit **aucun heartbeat**
(fichier toujours daté du 31/07) et n'a créé ni base dry-run ni journal du jour. Le bot n'a
donc pas atteint sa première boucle. À diagnostiquer avant de considérer le dry-run comme
lancé — un bot qui ne bat pas ne collecte rien.

### Correctif du 07/08 (3) — LE bug qui rendait tout le reste inutile

Diagnostic du heartbeat manquant, en relançant freqtrade au premier plan :

```
freqtrade.worker - INFO - Changing state to: STOPPED
freqtrade.worker - INFO - Bot heartbeat. PID=14768, state='STOPPED'
```

Le bot démarrait **parfaitement** — stratégie résolue, wallets synchronisés, 4 paires,
protections chargées — puis passait en état **STOPPED** et y restait.

**Cause** : `user_data/config.dry.json` ne contenait pas `initial_state`, et le défaut de
freqtrade est `stopped`. L'omission ne produit **aucune erreur** : les logs ont l'air sains,
le process tourne, il n'évalue simplement rien. Et sans FreqUI (`config.api.json` absent) ni
API REST, **rien ne pouvait le démarrer** : il serait resté figé toute l'absence.

C'est ce qui explique tout le reste — pas de heartbeat, pas de base dry-run, pas de journal
du jour.

**Corrigé** : `"initial_state": "running"` + `"logfile": "user_data/logs/freqtrade.log"`.
Le logfile n'est pas cosmétique : sans lui, un run non surveillé est indiagnosticable a
posteriori — il a fallu relancer au premier plan pour voir cette ligne.

**`tests/test_config_dry.py` créé** (5 tests) : aucun test ne validait la config déployée,
c'est précisément pour ça que le bug était invisible. Verrouillés désormais : `dry_run`
vrai, `initial_state` running, logfile présent, futures + paires perpétuelles, aucune clef
API en dur.

### Note — « clefs ccxt absentes » n'est PAS un problème

Le message du watchdog est **attendu** en dry-run : sans clefs, pas de lecture d'exposition
ni de *flatten*, ce qui n'a aucun sens sur de l'argent papier. Aucune clef d'exchange réelle
n'a été ajoutée pour un run en dry — ce serait un risque gratuit. Seule conséquence réelle,
déjà corrigée ci-dessus : l'alerte de liveness ne devait pas dépendre de l'exposition.

---

## Dispositif d'absence — mis en place le 2026-08-07 au soir

Jonas part se reposer (~3 semaines). Demande : « continue de chercher de l'edge sans moi
et des améliorations possibles ».

### Ce que j'ai refusé de programmer, et pourquoi

**Chercher un edge sans surveillance est exactement ce qu'il ne faut pas automatiser.**
`CHANTIERS.md` l'exige noir sur blanc : B6 impose le préenregistrement des hypothèses avec
un compteur d'essais « honnêtement initialisé à ≥ 30 », B2 impose Benjamini-Hochberg. Un
agent qui cherche pendant trois semaines **trouvera** quelque chose — et ce sera du bruit,
avec l'apparence d'un résultat. Le mandat programmé est donc : **préparer et mesurer, jamais
conclure**. Ce qui rend une future recherche d'edge légitime, pas la recherche elle-même.

### Ce qui tourne sur la machine (local — voit les données réelles)

| Mécanisme | Cadence | Rôle |
|---|---|---|
| `ARIT macro_state` | horaire | rafraîchit `macro_state.json` — sans elle le bot se fige en 2 h |
| `ARIT download_macro` | 06:15 | alimente les 5 composants ; > 48 h ⇒ scores refusés ⇒ repos |
| `ARIT veille` | 07:00 | écrit `research/veille_locale/AAAA-MM-JJ.md` : collecte + santé |
| `ARIT_relance.cmd` | ouverture de session | relance les 4 process après un redémarrage |

`veille_quotidienne.py` surveille les **quatre dépendances capables de figer le bot sans
erreur** — heartbeat, `stale`, scores 06.2 absents, historique macro périmé. Ce sont
précisément les pannes muettes du 07/08 : aucune ne se signale seule.

**Lecture seule, et sans Discord.** Le script constate, il ne corrige rien : un dry-run non
surveillé a besoin d'une trace, pas d'un pilote automatique. Et un résumé quotidien poussé
irait contre la décision V2 (« critiques seulement ») — le watchdog reste le seul dispositif
autorisé à interrompre Jonas.

### ⏳ Ce qui reste à armer — UNE action de Jonas

La routine cloud (vague 1 : B2, B4, B5, B6, deux fois par semaine, PR en draft, jamais sur
`main`, jamais de logique de trading) est **écrite mais pas créée** :

> `HTTP 401 — Connect your GitHub account before saving a routine that uses a GitHub repository.`

Il faut connecter le compte GitHub (`/web-setup`, ou l'app GitHub sur le dépôt). Une fois
fait, la routine se crée en une commande. Périmètre volontairement limité à B2/B4/B5/B6 :
ce sont les seuls chantiers réalisables **sans les données locales**, `user_data/data/` et
`user_data/backtest_results/` étant gitignorés donc absents d'un checkout cloud.

### Observabilité ajoutée le même soir

- **FreqUI** installée (`freqtrade install-ui` n'avait jamais été lancé) + overlay
  `config.api.json` généré, gitignoré, sur `127.0.0.1:8080` uniquement.
- **`scripts/suivi.py`** : montre les setups **envisagés puis refusés** avec l'écart au
  seuil — ce que FreqUI ne montre pas, et qui est la matière première de B8/B9.

### Routine cloud ARMÉE — 2026-08-08

GitHub connecté par Jonas, la routine est créée et active.

| | |
|---|---|
| Nom | **ARIT — vague 1 méthodologie (absence Jonas)** |
| ID | `trig_01LarM6hDoUtTrESnVqGRxdM` |
| Cadence | lundi et jeudi, 06:00 UTC (08:00 Paris) |
| Prochaine | 2026-08-10 08:03 Paris |
| Modèle | `claude-opus-5` |
| Suivi | https://claude.ai/code/routines/trig_01LarM6hDoUtTrESnVqGRxdM |

**Connecteurs MCP retirés** (`mcp_connections: []`). L'API avait rattaché
automatiquement Gmail, Google Calendar et Canva ; un agent autonome tournant trois
semaines sans surveillance n'a aucun besoin d'accéder à une boîte mail. Il ne dispose que
du dépôt et de ses outils de fichiers.

**Garde-fous inscrits dans le prompt** : jamais de push sur `main` (branche
`veille/vague1` + PR en draft), aucune modification de `user_data/strategies/**`,
`services/**`, `download_macro.py` ni des configs — un dry-run tourne sur la machine de
Jonas et rien ne doit pouvoir l'atteindre — et interdiction de **conclure** sur l'edge.
Périmètre : B6 d'abord (préenregistrement), puis B2, B4, B5.

**Mémoire entre exécutions** : `research/veille/JOURNAL.md`. Chaque run repart de zéro,
lit ce fichier, continue le travail entamé et y ajoute une entrée datée. Les livrables
vont dans `research/veille/` (versionné), jamais dans `research/veille_locale/`
(gitignoré, réservé à la veille locale).

Une exécution de vérification a été déclenchée le 08/08 à 17:37 (session
`cse_01NVY6e4gu2z8rnoGAS7SMP2`) plutôt que d'attendre trois semaines pour découvrir un
éventuel échec.
