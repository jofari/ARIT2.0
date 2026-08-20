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

## Où en est le programme du 18/08 — les deux points sont consommés

1. **Trancher les décisions** — en cours, c'est le sommaire ci-dessous.
2. **« Est-ce le technique, la stratégie, ou l'edge qui merde ? »** — **répondu, et la réponse
   est décevante au bon sens du terme** : les deux hypothèses issues du diagnostic du 18/08 ont
   été mesurées chez BETA le 19/08 et **aucune n'a survécu**.
   - **R1** (« le trailing stop détruit les shorts ») → **INDÉCIDABLE**. Test apparié sur les
     21 shorts du train, même entrée, même stop, seule la sortie change : la barrière fixe rend
     **+0,5272 R de plus par short** (p = 0,0175), mais le **MDE vaut 0,7463 R** et l'écart ne
     survit pas à Benjamini-Hochberg sur la famille de 8. La p-value passe, la puissance non.
   - **R6** (`news_window`) → **hypothèse NON MESURABLE**, et c'est le résultat le plus utile du
     lot : les « 756 signaux bloqués » sont **756 lignes de journal**, soit **63 signaux
     distincts**, dont **53 sont acceptés ailleurs de toute façon**. La porte **retarde** un
     signal, elle ne l'élimine pas. ⇒ **le chiffre « 91,75 % » ne décrit pas des signaux** ;
     il ne doit plus être cité tel quel, y compris pour trancher C1-bis.

Le diagnostic du 18/08 (tableau signal brut vs stratégie complète, MFE des sorties trailing)
n'attend donc plus rien : sa substance est dans `research/pistes_2026-07-31/CHANTIERS.md`
§ MISE À JOUR DU 2026-08-20 (soir) et dans `BETA/CHANTIERS.md` § R.

---

## Sommaire des décisions ouvertes

| # | Objet | État | Depuis |
|---|---|---|---|
| **A2-sexies** | **Règle de décision par concordance** (rouvre A2-quater) | **à trancher — 1 question** | **20/08** |
| A8 | G-rules à retravailler | reporté (priorité aux autres paramètres) | 03/08 |
| A2-ter | **Levier** en futures (aujourd'hui 1.0) | à trancher | 04/08 |
| A2-quinquies | **F&G adaptatif** (niveau + dynamique) | **acté 20/08**, 3 paramètres à trancher | 04/08 |
| C1-bis | Palier orange du calendrier éco | à trancher | 04/08 |
| C1-ter | Dates CPI/NFP **2027** à saisir | acté, échéance fin 2026 | 04/08 |
| G1 | Modèle appris à la place de l'agrégation Σ poids·score | à trancher | 12/08 |
| G2 | Relance du dry-run, et sa survie aux redémarrages | à trancher | 12/08 |
| G3 | Ablation de `s_sr` et `s_patterns` | **mesurée 20/08** (retenue) — appliquer maintenant ou après Q1 ? | 12/08 |
| G8 | VPS (Hermes Agent + ARIT 24/24) | acté, non codé | 12/08 |

---

## A2-sexies — RÈGLE DE DÉCISION PAR CONCORDANCE (rouvre A2-quater, 20/08)

**Jonas, 20/08** : « A2-quater pas du tout ce que je voulais, je voulais un **filtre
décisionnel** pas une **interdiction de long**. » La règle qu'il écrit :

```
if   macro.trend == bullish and signal.technique == bullish:  → long  + journal des raisons
elif macro.trend == bearish and signal.technique == bearish:  → short + journal des raisons
else:                                                           journal des raisons seul
```

### Ce que le code fait déjà — et c'est la même structure

`cio.conviction` :

```
signal_long  = conviction >= seuil & rr_dispo >= 1,5 & regime ∈ {TREND,TRANSITION}
             & new_4h & trend_dir >= 0 & direction_macro ∈ {long, both}
signal_short = miroir strict, trend_dir <= 0, direction_macro ∈ {short, both}
```

C'est **exactement** la conjonction `macro ∧ technique, même sens`. Le `if/elif/else` demandé
est le câblage en place. Il n'en diffère que sur **trois points**, et un seul coûte quelque
chose. Décompte complet sur le train (hold-out non lu) :
`research/regle_direction/RAPPORT.md`, code `compte_variantes.py`.

| # | Écart entre le code et la règle écrite | Coût mesuré |
|---|---|---|
| 1 | **NEUTRE ⇒ `both`** : macro neutre autorise **les deux sens** (au seuil +0,05). Dans la règle de Jonas, neutre n'est ni bullish ni bearish ⇒ `else` ⇒ **rien** | **−15 signaux sur 78** (6 longs, 9 shorts) |
| 2 | **Macro inconnue ⇒ `long`** (fail-safe historique) alors que la règle dirait `else` ⇒ rien | 0 signal sur le train |
| 3 | **Le véto actions crée un 4ᵉ état `none`** — l'« interdiction de long » contestée | **0 signal touché en 5 ans** |

### Fait n° 1 — A2-quater n'a déplacé aucun trade, dans aucun sens

Le véto actions directionnel est actif sur **2 298 lignes** du train, et **aucun signal
technique ne tombe dessous** : 0 long, 0 short. Le décompte avant A2-quater (véto =
coupe-circuit) et après (véto = filtre directionnel) est **identique au trade près** : 50
longs, 28 shorts, mêmes R. Les deux façons de rendre le véto « décisionnel » plutôt
qu'« interdicteur » (le dégrader d'un cran, ou le forcer à HOSTILE) donnent elles aussi
exactement le même décompte.

⇒ Le désaccord porte sur un bloc **inerte dans l'historique mesuré**. C'est une question de
sens, pas de performance, et elle ne mérite pas de bloquer le reste. **Reco : garder A2-quater
tel quel** (le véto retire le long, ne crée jamais de short) et n'y revenir que si une mesure
future lui donne un effet.

### Fait n° 2 — la concordance stricte retire le seul groupe positif du lot

| macro | long | R moyen | short | R moyen |
|---|---|---|---|---|
| PORTEUR | 44 | −0,0609 | 7 *(déjà bloqués)* | −0,2286 |
| **NEUTRE** | 6 | −0,1667 | **9** | **+0,4978** |
| HOSTILE | 0 | — | 19 | −0,0663 |

Les 9 shorts en macro NEUTRE sont **le seul groupe nettement positif de tout le tableau**, et
la règle stricte les supprime. ⚠️ **n = 9** : à ce N le MDE dépasse le R entier, ce n'est donc
**pas un résultat** — c'est un signal contraire assez net pour interdire d'appliquer la règle
stricte sans l'avoir préenregistrée et mesurée.

### LA question à trancher, et c'est la seule

> **Que fait la macro NEUTRE ?**
> **(a)** elle autorise les deux sens au seuil relevé — le câblage actuel, 78 signaux ;
> **(b)** elle n'autorise rien — ta règle à la lettre, **63 signaux (−19 %)**.

Ma recommandation : **(a) pour l'instant**, pour deux raisons qui n'ont rien à voir avec le
goût. D'abord (b) coûte 19 % des entrées alors que **la rareté est le goulot n° 1** (Q1, que
tu as placé en tête des priorités le 20/08) — et G3 attend déjà cette même courbe pour savoir
de combien desserrer. Ensuite (b) supprime les 9 shorts à +0,4978 R : indécidable, mais on ne
retire pas à l'aveugle le seul sous-groupe qui gagne. **Si tu veux (b), elle se préenregistre
d'abord** (B6) — c'est une hypothèse formulée après avoir vu les chiffres.

### Ce que ta règle demande et qui n'existe nulle part : le `else`

`AritV1._journal_evaluation` écrit bien une ligne par évaluation, mais la raison d'un
`no_signal` est **le régime technique** (`row.get("regime")`), **pas le motif du refus**. Le
journal ne distingue donc pas « refusé : macro discordante » de « conviction insuffisante » ou
« RR manquant ». C'est le **seul morceau de ta spec réellement absent du code**, et c'est
exactement le manque qui a rendu R6 non mesurable chez BETA (il a fallu reconstruire les
populations à la main pour découvrir que `news_window` ne séparait rien).

⇒ **Chantier `Q12` — raison de refus structurée dans le journal.** Ne demande aucun arbitrage,
ne change aucun trade, et rend mesurable tout ce qui suit (Q1 le premier). Il est écrit dans
`CHANTIERS.md` et peut se coder sans attendre ta réponse sur NEUTRE.

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
| 1 | **Le F&G existe en backtest, mais seulement écrasé dans une somme.** ⚠️ *Formulation corrigée le 20/08 au soir après lecture du code* : `macro_regime._score_fear_greed` en fait bien le composant **c5** du régime (< 25 ⇒ −1, ≥ 45 ⇒ +1), calculé depuis `fear_greed.json` ⇒ le F&G **pèse déjà** sur PORTEUR/NEUTRE/HOSTILE en backtest. Ce qui n'existe pas, c'est **sa valeur brute quotidienne en colonne** : `attach_macro_regime` ne pose que `macro_regime` + les colonnes de véto, et `_journal_evaluation` écrit `fear_greed: None` en backtest. Le **coupe-circuit** F&G < 25, lui, est bien neutralisé (`FG_NEUTRAL_BACKTEST = 50`) | **Aucun delta n'est calculable** sans la série brute : un score {−1,0,+1} ne dit pas qu'on est passé de 15 à 30. Poser la colonne (décalage +1 j, comme la macro) reste le **prérequis n° 1** — mais c'est un ajout de colonne, pas la création d'une donnée absente |
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

### Comment ça se code, exactement (demandé par Jonas le 20/08)

Cinq fichiers, dans cet ordre. **Rien n'est décisionnel avant l'étape 5** : les quatre
premières ne font que rendre la donnée disponible et mesurable, et sont sans effet sur les
trades. Elles peuvent donc être codées **avant** que P1-P3 soient tranchés.

**1. `macro_regime.daily_regimes` — poser la valeur brute à côté des scores** *(Q11a)*
`daily_regimes` construit déjà `score_df` (5 colonnes {−1,0,+1}) puis `shifted = same_day.shift(1)`.
Il suffit d'ajouter la série brute au même `same_day`, donc **elle hérite du même décalage
+1 j**, ce qui est ce qui garantit l'absence de look-ahead :

```python
same_day[contracts.FG_LEVEL_COL] = history["fear_greed"].reindex(full_index).ffill(limit=_STALE_DAYS)
```

puis, dans `attach_macro_regime`, ajouter `contracts.FG_LEVEL_COL` à la liste `wanted` — la
jointure `merge_asof` existante s'en occupe. Nouvelle constante dans `contracts.py`
(`FG_LEVEL_COL = "fear_greed"`), aucune valeur magique.

**2. `regimes` — le sortir du fail-safe de données** *(Q11b, le vrai travail)*
Aujourd'hui `F&G < 25` vit à **deux** endroits, et les deux le traitent comme une panne :
- `REGLES` : `("RISK_OFF", lambda r, m: m["risk_off"] or m["stale"] or m["fear_greed"] < FG_RISK_OFF_BELOW)` ;
- `donnee_non_fiable()` : même seuil, à côté de `stale` et « aucun score ».

Tant que la peur du marché est rangée avec « la donnée est cassée », **elle ne peut pas
devenir directionnelle** — un fail-safe ne donne jamais de direction, c'est la règle du projet
(la même qui a fait garder `equity_veto_stale` en coupe-circuit dans A2-quater). Il faut donc
retirer le terme `fear_greed` de ces deux prédicats et le porter dans le composant c5, qui est
sa vraie place. ⚠️ **C'est le seul point du chantier qui change des trades en live**, et il
double le poids du F&G nulle part : c5 le compte déjà.

**3. `services/macro_state.py` — l'historique en live** *(Q11c, parité)*
`fetch_fear_greed()` lit `resp.json()["data"][0]` — la valeur du jour, sans passé. L'API
alternative.me accepte `limit=N` (c'est déjà ce que fait `scripts/download_macro.py` avec
`limit=0`). Passer à `limit=FG_HISTORY_DAYS` et écrire la fenêtre dans `macro_state.json`, à
côté de `fear_greed`. **Sans ça, la règle marche en backtest et meurt en live** : c'est
exactement le bloquant n° 1 déjà payé une fois en août (le régime V1.1 produit en backtest et
absent en live, qui rendait le live long-only).

**4. `scripts/download_macro.py fng`** *(Q11d)* — `fear_greed.json` est figé au 03/08/2026
(3 103 points depuis 2018-02). Une commande, zéro code.

**5. La règle des deux temps** *(Q11e, et c'est là que P1-P3 entrent)*
Une fonction pure dans `macro_regime`, testable seule, sans état :

```python
def fg_retournement(niveau: pd.Series) -> pd.Series:
    """+1 retournement haussier · -1 baissier · 0 rien. Fenêtre et amplitude = params (P1)."""
    delta = niveau.diff(params.FG_REVERSAL_WINDOW_D)
    return (delta >= params.FG_REVERSAL_POINTS).astype(int) - (delta <= -params.FG_REVERSAL_POINTS).astype(int)
```

Son branchement dépend de P3 : **« lever seulement »** signifie que le retournement
n'intervient **pas** dans la somme des composants, mais **relâche une porte** — c'est-à-dire,
concrètement, qu'il vit dans `cio.direction_macro` comme le véto actions, avec le signe
opposé : le véto retire un sens, le retournement en rend un. Rien à toucher dans
l'agrégation Σ poids·score, donc **l'interdit n° 5 n'est pas approché**.

⚠️ **Ce que ce chantier ne peut pas faire** : le F&G est **quotidien et global**, pas par
paire. Il ne créera jamais un signal — il ne peut qu'autoriser un signal que la technique
produit déjà. Sur les 78 entrées de cinq ans, il n'y a aucune raison d'attendre qu'il en
ajoute beaucoup ; il changera surtout **lesquelles** passent, ce qui se mesure en R, pas en N.

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

## G3 — ablation `s_sr` + `s_patterns` : MESURÉE le 20/08. Reste : on l'applique quand ?

**Décision de Jonas (20/08)** : d'accord, l'ablation se fait. **Mesurée le jour même**,
préenregistrée (B6) puis close : `research/ablation_Q4/RAPPORT.md`, code
`analysis/ablation_scores.py`, registre § `Q4-ablation-scores-sr-patterns` (essais cumulés 50).

**Résultat — l'ablation est RETENUE sur la métrique primaire**, selon les trois conditions
écrites avant la mesure (ΔIC ≥ +0,010, IC bootstrap 90 % excluant 0, survie à BH) :

| | IC production | IC ablaté | ΔIC | IC 90 % |
|---|---|---|---|---|
| long | 0,0642 | **0,0848** | **+0,0205** | [0,0135 ; 0,0275] |
| short | 0,0357 | **0,0544** | **+0,0187** | [0,0115 ; 0,0260] |

`s_sr` porte les trois quarts de l'effet. Et le chiffre qui résume tout : IC(ablaté) = **0,0848**
contre **0,0851** pour `s_structure` **seul** (B9). L'agrégation à cinq termes détruisait
exactement ce que ses deux termes à IC négatif y injectaient — l'ablation ne fait pas mieux que
le meilleur score isolé, elle le **rejoint**.

### ⚠️ Ce qui reste à trancher, et c'est un vrai arbitrage

L'ablation supprime **44 % des signaux longs** (50 → 28) et **21 % des shorts** (28 → 22).
Or le goulot n° 1 du projet est la **rareté des entrées** (78 signaux en 5 ans, chantier Q1,
que tu viens de placer en tête des priorités). Appliquer l'ablation améliore un IC mesuré **et
aggrave le goulot mesuré**. Les deux sont vrais en même temps.

> **La question** : on applique en production tout de suite, ou on attend **Q1** (courbe
> N(seuil)) pour savoir de combien desserrer les portes en compensation ?

Ma recommandation : **attendre Q1**. Un seuil abaissé sur mesure pourrait rendre les 22 signaux
perdus sans réintroduire les deux scores à IC négatif — rien n'oblige à payer les deux coûts.

Deux réserves à porter à la décision, toutes deux préenregistrées :
- Le gain d'IC **ne se lit pas** dans les trades effectivement perdus côté long (+0,0828 R
  contre un noyau à −0,1964 R), mais sur 22 signaux c'est indécidable (MDE 0,825 R).
- Le noyau conservé reste à **−0,1964 R** : améliorer un IC ne crée pas un edge.

⚠️ À ne pas confondre avec l'anomalie `rr_dispo` (IC −0,0592, signe instable, variable **tronquée
par sa propre porte** `rr_min`) : celle-là demande un traitement de biais de sélection, pas un IC
de rang. Chantier `Q3`, non conclu.

---

## G8 — VPS : acté, non codé

Jonas, 12/08 : un VPS est prévu pour **Hermes Agent + ARIT 24/24**. C'est la réponse envisagée au
problème de survie du dry-run (G2) et à l'observabilité locale (F2). Rien n'est codé, rien n'est
provisionné. ⚠️ Tant que ce n'est pas fait, tout dry-run dépend de la session Windows de Jonas.
