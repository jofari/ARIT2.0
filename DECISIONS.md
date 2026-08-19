# DECISIONS.md — décisions OUVERTES de Jonas

> **But** : un arbitrage de Jonas ne doit jamais vivre uniquement dans une conversation.
> Ce fichier ne contient QUE ce qui attend encore quelque chose — une réponse de Jonas, ou du
> code à écrire. Il se lit en entier en début de session, avant tout code.

## Règle de tenue — PURGE IMMÉDIATE (posée le 2026-08-17 par Jonas)

1. **Une décision actée disparaît d'ici.** Dès qu'elle est appliquée (code + commit), fermée,
   abandonnée ou sans objet, sa section est **supprimée du fichier dans la même session** — pas
   barrée, pas déplacée en bas, pas archivée ici.
2. **On supprime la décision, pas la connaissance.** Avant de supprimer, ce que la décision a
   produit de durable part à sa destination pérenne : un paramètre → `docs/` · un piège ou une
   mesure → `for claude build/BUILD_NOTES.md` · un rapport → `research/` · un travail restant →
   `research/pistes_2026-07-31/CHANTIERS.md`. **Si rien n'a été déplacé, la suppression est
   prématurée.**
3. **La trace reste dans git.** L'historique complet des décisions fermées du 03/08 au 16/08 vit
   dans les versions antérieures de ce fichier : `git log -p -- DECISIONS.md`, ou
   `git log -S "A7" -- DECISIONS.md` pour retrouver une décision précise. Tout renvoi d'un autre
   fichier vers une section fermée de `DECISIONS.md` se résout là.
4. **Un fichier vide est le but**, pas un signe d'oubli : ce qui n'est pas écrit ici n'attend rien
   de Jonas.
5. Corollaire pour les fichiers append-only (`CHANTIERS.md`, `BUILD_NOTES.md`) : là-bas un statut
   se corrige **à l'endroit où il a été écrit** (barré en place, avec sa date). Ici il n'y a plus
   de statut à corriger, seulement une section à retirer.

**Vocabulaire** : `à trancher` = Jonas n'a pas répondu · `acté` = tranché, code encore à écrire ·
`reporté` = volontairement remis. Ces trois états restent dans ce fichier. `appliqué`, `fermé`,
`abandonné`, `sans objet` en sortent immédiatement.

**Frontière avec BETA** (19/08) : les décisions du banc d'essai (projet **BETA**, ex-F1)
ont leur propre fichier, `C:\Users\jofar\BETA\DECISIONS.md`. Ici ne restent que les décisions
qui portent sur **AritV1 en production**. F1 a donc quitté ce fichier le 19/08 : acté le
18/08, sa substance est partie là-bas, ses chantiers dans `BETA\CHANTIERS.md`.

Lecture au démarrage de session : ce fichier, puis `research/pistes_2026-07-31/CHANTIERS.md`.

---

## Programme annoncé par Jonas le 18/08 pour la session suivante

1. **Trancher les décisions d'ARIT** — le sommaire ci-dessous, dans l'ordre qu'il voudra.
   Les plus mûres, parce que la mesure du 18/08 les a reformulées : **A2-quater** et
   **A2-quinquies** (coupe-circuit ou filtre directionnel ?).
2. **Retravailler l'edge**, avec une question précise et bien posée :

   > **est-ce le côté technique, le côté stratégie, ou le côté edge qui merde ?**

   Les trois se mesurent séparément, et les données pour le faire existent depuis le 18/08
   (`C:\Users\jofar\BETA`, tables `trades` / `evaluations` / `gestion`).

   **La comparaison qui sépare le signal de la gestion** — deux sources, ramenées à la
   **même période** (le zip démarre en 2021, le rejeu G0 en 2019 ; les comparer sans ça
   était une erreur, corrigée ici le 18/08 au soir) :

   | Sens | Signal brut, géométrie pure (G0, aucune gestion) | Stratégie complète (zip, G1-G7 actives) | Écart |
   |---|---|---|---|
   | long | n=36 · **+0,0417 R** | n=31 · **+0,0815 R** | +0,04 |
   | **short** | n=27 · **+0,0637 R** | n=21 · **−0,4683 R** | **−0,53** |

   > **Le signal short n'est pas le problème : il est légèrement positif.** Ce qui le détruit
   > se situe **entre le signal et la sortie**.

   Mécanique visible dans les raisons de sortie : sur `trailing_stop_loss`, le MFE moyen est
   de **+1,215 R** côté long (n=29) contre **+0,438 R** côté short (n=17). Les longs vont
   chercher plus d'un R de profit latent avant d'être coupés ; les shorts, jamais.

   - **technique (signal)** : rien ne l'accable une fois la période alignée. Le −0,0736 R du
     long vient surtout de 2019-2020, hors période du backtest.
   - **gestion** : c'est là que se trouve la perte. Hypothèse n° 1 à préenregistrer — *le
     trailing stop coupe les shorts avant qu'ils ne produisent*.
   - **edge (filtrage)** : `news_window` bloque **91,75 %** de tout ce qui est rejeté
     (756 signaux sur 824) — la porte la plus active du système, lien direct avec **C1-bis**.

   ⚠️ Un seul chiffre du lot dépasse son MDE : short + trailing stop (|−0,468| > 0,406).
   Et c'est un sous-groupe repéré **après** avoir vu les données. Il doit donc être
   **préenregistré** (`research/EXPERIMENTS.jsonl`, B6) avant d'être mesuré pour de bon —
   sinon c'est du p-hacking, quel que soit le résultat.

---

## Sommaire des décisions ouvertes

| # | Objet | État | Depuis |
|---|---|---|---|
| A8 | G-rules à retravailler | reporté (priorité aux autres paramètres) | 03/08 |
| A2-ter | **Levier** en futures (aujourd'hui 1.0) | à trancher | 04/08 |
| A2-quinquies | **F&G adaptatif** (niveau + dynamique) | **acté 20/08**, spec à trancher | 04/08 |
| C1-bis | Palier orange du calendrier éco | à trancher | 04/08 |
| C1-ter | Dates CPI/NFP **2027** à saisir | acté, échéance fin 2026 | 04/08 |
| G1 | Modèle appris à la place de l'agrégation Σ poids·score | à trancher | 12/08 |
| G2 | Relance du dry-run, et sa survie aux redémarrages | à trancher | 12/08 |
| G3 | Ablation de `s_sr` et `s_patterns` | **acté 20/08**, mesure à faire | 12/08 |
| G8 | VPS (Hermes Agent + ARIT 24/24) | acté, non codé | 12/08 |

---

## A8 — G-rules : reporté

Jonas, 03/08 : les 7 règles G sont **à retravailler, mais la priorité va aux autres paramètres**.
Rien à coder tant que ce n'est pas rouvert. ⚠️ Interdit n° 5 : G1-G7 et les poids ne sont **jamais**
hyperoptés — la reprise se fera par mesure, pas par optimisation.

---

## A2-ter — LEVIER : décision de risque non signée

Le short impose les futures. Le défaut freqtrade est conservé (`leverage() → 1.0`,
`AritV1.py:32`), donc l'exposition reste celle du spot. Un levier > 1 appartient à Jonas.

**Conséquence de rester à 1**, qui est le point à trancher : quand la distance de stop est très
serrée, le stake calculé dépasse l'équité, freqtrade le plafonne, et le risque réel devient
**inférieur** aux 1,16 % visés (A6) — **sans le dire**. Spec : `docs/03 §3.7.4`, `docs/03:115`.

---

## A2-quinquies — F&G ADAPTATIF : acté le 20/08, spec à trancher

**Décision de Jonas (20/08)** : le Fear & Greed cesse d'être un coupe-circuit statique. Il
devient **adaptatif, en deux temps** :

1. **Le niveau** — des seuils clés, au-dessus / en dessous. C'est ce qui existe déjà (< 25).
2. **La dynamique** — l'*évolution* de l'indice porte de l'information que le niveau ignore.
   Mot pour mot : « s'il prend 15 points en une journée et qu'il passe de 15 à 30, alors ça
   peut être un signal bullish **si d'autres signaux bullish** ».

**Traduction retenue, et pourquoi elle ne crée aucune source de signal nouvelle** : un
retournement du F&G ne **produit** pas d'entrée, il **lève un blocage**. Aujourd'hui F&G < 25
interdit tout ; demain F&G < 25 interdit le long **sauf** si l'indice se retourne violemment,
auquel cas le long redevient possible et ce sont la conviction, `trend_dir` et `rr_dispo` qui
décident. La clause « si d'autres signaux bullish » de Jonas est donc déjà portée par la chaîne
existante — la dupliquer dans le F&G serait un second filtre sur les mêmes données.

### Ce qui bloque, et qui n'est pas une question de goût

| # | Fait constaté le 20/08 | Conséquence |
|---|---|---|
| 1 | **Le F&G n'existe pas en backtest.** `_classify_macro` injecte `FG_NEUTRAL_BACKTEST = 50` en dur (`regimes.py`), donc aucune règle F&G n'est mesurable aujourd'hui | Sans colonne quotidienne `fear_greed` (via `attach_macro_regime`, décalage +1 j comme la macro), on coderait une règle live qu'aucun backtest ne pourrait valider. **C'est le prérequis n° 1** |
| 2 | **Pas de delta possible en live.** `services/macro_state.py:fetch_fear_greed()` ne lit que `data[0]` — la valeur du jour, sans historique | L'API accepte `limit=N`. Sans ça, la règle marche en backtest et pas en live : rupture de parité, exactement le bloquant n° 1 déjà payé une fois |
| 3 | **F&G < 25 est câblé à DEUX endroits**, dont `regimes.donnee_non_fiable()` — la même fonction que `stale` et « aucun score » | Le code **confond « la donnée est cassée » et « le marché a peur »**. Tant que le F&G vit dans le fail-safe de données, il ne *peut pas* être directionnel. L'en sortir est le vrai travail de ce chantier |
| 4 | `user_data/data/macro/fear_greed.json` : 3 103 points depuis 2018-02, **figé au 03/08/2026** | À re-télécharger (`scripts/download_macro.py fng`). L'historique nécessaire au delta existe, lui |

### Les trois paramètres qui attendent Jonas

| # | Question | Défaut proposé |
|---|---|---|
| **P1** | **Amplitude et fenêtre du retournement.** « +15 points en une journée » : 15 points fermes, ou un seuil relatif ? Fenêtre 1 jour, ou 2-3 jours glissants (le F&G bouge par à-coups) ? | **+15 points sur 1 jour**, littéralement ce que tu as dit |
| **P2** | **Le miroir baissier.** Tu n'as parlé que du bas. Une chute de −15 points, ou l'euphorie (F&G > 75), doit-elle retirer le long de la même façon ? | **Symétrie**, sinon le filtre est un pari haussier déguisé |
| **P3** | **Ce que le retournement a le droit de faire.** Lever le blocage seulement, ou aussi *ajouter* de la conviction ? | **Lever seulement.** Ajouter du poids toucherait l'agrégation, donc l'interdit n° 5 |

⚠️ **Préenregistrement obligatoire (B6)** avant toute mesure de cette règle : c'est une
hypothèse formulée après avoir vu le marché, comme le sous-groupe short/trailing.

---

## C1-bis — palier orange du calendrier économique

Le calendrier capture tous les rouges toutes devises + `WATCHED_EVENTS` (24 fragments de noms)
quelle que soit leur couleur, mais un événement suivi ne devient **bloquant** que si ForexFactory
le classe déjà `high` ou `medium`. Mesuré sur le flux réel du 04/08 :

| Règle | Capturés | Bloquants | Part du temps calendaire bloquée |
|---|---|---|---|
| Sans palier (tout suivi promu) | 40 | 40 | **~24 %** |
| **Avec palier orange (en place)** | 40 | 11 | **~7 %** |

**À trancher** : d'accord pour le palier orange, ou tu veux que les `low` bloquent aussi (~24 % du
temps) ? Le retour en arrière est en un point unique (`bloquant` → `impact_ff == "high"`),
verrouillé par `test_liste_suivie_capture_les_oranges_mais_pas_les_low`.

---

## C1-ter — dates CPI/NFP 2027 : à saisir fin 2026

Acté, avec une échéance : le BLS publie son calendrier annuel **fin 2026**. Tant que 2027 n'est pas
saisi dans `user_data/calendar/economic_calendar.json`, la couverture CPI/NFP retombe sur
ForexFactory, **qui ne voit que la semaine en cours** — un CPI à J+20 n'est connu de personne.
`coverage_gaps()` le signalera en `ERROR` à chaque run. ⚠️ `bls.gov` refuse toute récupération
automatisée (403) : saisie manuelle, publication 08:30 US Eastern.

---

## G1 — un modèle appris peut-il remplacer l'agrégation Σ poids·score ?

**Ce qui est mesuré** : `produit_pondere` (la somme pondérée) a un IC de **+0,0642**, soit **moins
bon que `s_structure` seul (+0,0851)**. L'agrégation à poids figés **dégrade** le meilleur signal
disponible, parce qu'elle y mélange `s_sr` (IC −0,0497) et `s_patterns` (−0,0162) avec des poids
positifs. C'est le point d'insertion ML n° 1 — ni le CIO macro, ni le position manager. `cio.py`
l'annonce depuis le début (« V2 remplacera `conviction()` derrière la MÊME interface »).

**Pourquoi ça bloque** : l'interdit n° 5 dit « G1-G7 et les poids jamais hyperoptés ». Mesurer un
IC n'est pas hyperopter ; **remplacer l'agrégation par un modèle appris, si**. C'est donc un
arbitrage de Jonas, pas une évidence technique.

---

## G2 — relance-t-on le dry-run, et avec quel mécanisme de survie ?

Le dry-run est mort depuis le 05/08 et **rien n'a été relancé** : remettre en route un dry-run
engage la machine de Jonas et lui appartient.

Ce que la relance doit régler pour ne pas répéter août :
- les 4 process vivent dans des consoles utilisateur ⇒ **PC allumé ET session ouverte** ; un
  redémarrage sans reconnexion automatique arrête tout ;
- l'état hors-git (tâches planifiées, `ARIT_relance.cmd`, logs) avait **entièrement disparu** entre
  le 08 et le 12/08 — les trois semaines de collecte ont produit zéro donnée ;
- l'observabilité est **intégralement locale** (FreqUI sur `127.0.0.1`, traces gitignorées) : le
  seul signal distant est l'**absence** d'alerte Discord, qui ne distingue pas « bot sain » de
  « session Windows fermée depuis trois jours » (chantier F2, et lien direct avec G8).

Le rejeu hors-ligne (`analysis/dataset.py`) remplace le dry-run pour la **donnée**, pas pour la
**parité** live/backtest ni pour l'exécution réelle.

---

## G3 — ablation de `s_sr` et `s_patterns` : ACTÉ le 20/08, mesure à faire

**Décision de Jonas (20/08) : d'accord, l'ablation se fait.**

Deux scores sur cinq entrent dans la somme avec un **poids positif et un IC négatif** (`s_sr`
−0,0497 · `s_patterns` −0,0162). Leur retrait est une **ablation, pas une optimisation** : c'est
mesurable sans rien recoder, donc l'interdit n° 5 n'est pas touché. Chantier `Q4`.

**Reste à faire, dans cet ordre** :
1. **Préenregistrer** l'hypothèse dans `research/EXPERIMENTS.jsonl` (B6) — retirer deux scores
   après avoir lu leur IC est un choix informé par les données.
   ⚠️ Le test `test_experience_reelle_est_preenregistree` **échoue depuis avant le 20/08**
   (`KeyError: 'split_autorise'`) : le verrou méthodologique B6 est cassé, à réparer d'abord.
2. Mesurer l'ablation sur le dataset hors hold-out, IC de `produit_pondere` avant/après.
3. Critère de passage à écrire **avant** la mesure : de combien l'IC doit-il monter pour que le
   retrait soit retenu ? Sans ce seuil, toute amélioration paraîtra suffisante.

### ⚠️ Le piège arithmétique, vérifié le 20/08 — l'ablation naïve ne mesure PAS ce qu'on croit

`POIDS` somme exactement à 1,00 (`params.py:94` — 0,40 + 0,20 + 0,15 + 0,15 + 0,10). Retirer
`s_sr` et `s_patterns` **sans renormaliser** plafonne la conviction à **0,70 × multiplicateur**.
Or les seuils, eux, ne bougent pas :

| Régime | Seuil | Conviction max après retrait | Verdict |
|---|---|---|---|
| TREND (mult 1,0) | 0,50 | 0,70 | passe, mais exige un score quasi parfait sur les 3 restants |
| TREND + NEUTRE | 0,55 | 0,70 | idem, encore plus serré |
| TRANSITION (mult 0,85) | 0,65 | **0,595** | ❌ **plus aucun signal possible** |

⇒ Une ablation brute mesurerait **un durcissement du seuil**, pas le retrait de deux scores.
Sur 78 signaux en 5 ans, elle les ferait presque tous disparaître et le résultat serait
ininterprétable.

**Ce qui suit de là, et qui n'est pas un détail de méthode** :
- **Renormaliser les 3 poids restants à somme 1** (0,571 / 0,286 / 0,143). Les rapports entre
  poids sont **inchangés** : ce n'est pas une hyperopt, c'est la seule façon d'isoler la variable.
- **L'IC est insensible à cette renormalisation** (corrélation de rang, invariante par
  multiplication par 1/0,70) : la mesure d'IC donnera le même chiffre dans les deux cas.
  **Le backtest, lui, y est extrêmement sensible.** Ne pas conclure de l'un sur l'autre.

⚠️ À ne pas confondre avec l'anomalie `rr_dispo` (IC −0,0592, signe instable, variable **tronquée
par sa propre porte** `rr_min`) : celle-là demande un traitement de biais de sélection, pas un IC
de rang. Chantier `Q3`, non conclu.

---

## G8 — VPS : acté, non codé

Jonas, 12/08 : un VPS est prévu pour **Hermes Agent + ARIT 24/24**. C'est la réponse envisagée au
problème de survie du dry-run (G2) et à l'observabilité locale (F2). Rien n'est codé, rien n'est
provisionné. ⚠️ Tant que ce n'est pas fait, tout dry-run dépend de la session Windows de Jonas.
