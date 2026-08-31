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

## ⭐ CHANTIERS PRIORITAIRES — posés par Jonas le 25/08

> Ces deux lignes passent devant tout le reste de ce fichier. Le mot **PRIORITAIRE** dans la
> colonne État n'est pas décoratif : ALPHA le lit et sort ces chantiers de l'agrégat
> « N décisions en attente » pour leur donner leur propre carte, en tête du dashboard
> (`alpha/config.py` → `DECISION_PRIORITY`). Retirer le mot ici, c'est retirer la priorité là-bas.

| # | Chantier | État | Depuis |
|---|---|---|---|
| A8 | **G-rules** : reprise du travail sur G1-G7 et leurs poids | **PRIORITAIRE** — rouvert le 25/08. Outillage réparé le 31/08 (les 7 sont ablatables) ; **bloqué par B5, B4 et l'arbitrage B1** | 03/08 |
| DE1 | **Données entrantes** : les flux qui alimentent les scores | **PRIORITAIRE** — ouvert le 25/08, périmètre à cadrer avant toute mesure | 25/08 |

---

## ⭐ B1 et Test 1 — les deux choses qui n'attendent QUE toi (posées le 31/08)

Diagnostic complet : `research/diagnostic_2026-08-31/RAPPORT.md`. Deux points en sortent qui
ne se résoudront par aucune mesure — ils attendent un arbitrage, et ils commandent tout le reste.

### B1 — la prudence macro s'exprime sur le seuil OU sur le multiplicateur, jamais les deux

Deux pénalités s'appliquent à la même situation et n'ont **jamais été calibrées ensemble** :
multiplicateur **×0,85** hors accord macro/technique (`regimes._classify_macro`) **et** seuil
**+0,05** en macro NEUTRE (`cio.conviction:106`). Comme `conviction = produit_pondéré ×
multiplicateur`, le seuil effectif vaut `seuil / multiplicateur` :

| macro | n (bougies TREND) | mult | seuil | **seuil effectif** | % qui passent |
|---|---|---|---|---|---|
| PORTEUR | 7 179 | 1,00 | 0,50 | **0,500** | 14,31 % |
| **NEUTRE** | **9 670** | 0,85 | 0,55 | **0,647** | **1,65 %** |
| HOSTILE | 2 855 | 0,85 | 0,50 | 0,588 | 1,37 % |

Le p99 du produit pondéré vaut **0,695**, son maximum absolu sur 5 ans **0,875**. Exiger 0,647
revient à demander le dernier centile — **49 % du temps**. Un facteur **9** entre PORTEUR et
le reste.

⚠️ **Ça ne se corrige pas par hyperopt (interdit n° 5).** Ça se corrige en décidant **où** la
prudence macro s'exprime. Trois options :
- **(a)** garder le multiplicateur ×0,85, **retirer** le bump +0,05 de seuil ;
- **(b)** garder le bump de seuil, **retirer** le multiplicateur ;
- **(c)** garder les deux mais **recalibrer** le couple pour viser un taux de passage cible.

**Ma recommandation : (a)** — le multiplicateur agit déjà sur la conviction, le bump double
la peine sur la même information. Mais c'est ta décision.

**Pourquoi ça commande tout** : B1 est la cause mécanique du manque d'entrées, donc du `n`
minuscule, donc de six mesures sur six rendues INDÉCIDABLES, donc de l'impossibilité de vérifier
le look-ahead (D1, 0/20 trades). Tant qu'il n'est pas tranché, le projet ne peut pas apprendre.

### Test 1 — le confirmes-tu comme prochain chantier après B1 ?

`docs/01` v4, que **tu as signée le 03/08**, dit : « **L'ordre des tests n'est pas négociable :
Test 1 d'abord.** » Or **Test 1 n'a jamais été exécuté** — rien dans `research/EXPERIMENTS.jsonl`,
rien dans `research/`, rien dans `CHANTIERS.md`. Les 4 expériences du registre portent toutes sur
de l'aval (scores, stops, G-rules).

Test 1 = « la macro donne-t-elle vraiment la direction ? », contrôle = direction tirée à pile ou
face, timing technique identique. C'est le seul test capable de dire **s'il y a un edge**.

⇒ **Question** : on cadre Test 1 juste après B1, ou tu veux passer avant par le **funding**
(86 % du profit de MacroFlip venait de là, jamais rouvert depuis le 27/07) ?

---

## Sommaire des décisions ouvertes

| # | Objet | État | Depuis |
|---|---|---|---|
| A2-quinquies | **F&G adaptatif** (niveau + dynamique) | **acté**, P1-P3 tranchés 20/08 — **à coder** | 04/08 |
| A2-ter | **Levier** en futures (aujourd'hui 1.0) | **quasi tranché** — raisonnement à corriger avant de fermer | 04/08 |
| C1-bis | Calendrier éco : **barème de points** (nouvelle direction, 20/08) | **acté**, 3 paramètres à fixer | 04/08 |
| G3 | Ablation de `s_sr` et `s_patterns` | mesurée, retenue — **question de Jonas en attente de sa réponse** | 12/08 |
| G1 | Modèle appris à la place de l'agrégation Σ poids·score | **reporté 20/08** — reste une hypothèse, pas un chantier | 12/08 |
| G8 | VPS (Hermes Agent + ARIT 24/24) | acté, non codé — **prérequis de G2 devenu explicite** | 12/08 |

**Tranchées le 20/08 au soir, donc sorties d'ici** : **A2-sexies** (NEUTRE garde les deux
sens — statu quo, rien à coder) · **G2** (le suivi à distance passe chez BETA, c'est un
chantier maintenant) · **C1-ter** (supprimée sur demande de Jonas ; l'échéance de fin 2026
vit désormais dans `CHANTIERS.md`).

---

## A2-sexies — TRANCHÉE le 20/08 : (a), et ce qu'elle ouvre derrière

**Jonas** : « pour la règle en effet passe dans le cas A qui a l'air plus positif de toute
façon le système n'est pas rentable de base, **il faudra changer les triggers de signal** ».

⇒ **La macro NEUTRE garde les deux sens.** C'est le câblage actuel : **rien à coder**, les 78
signaux restent 78. A2-quater reste en place (le véto retire le long, ne crée jamais de short)
— il n'a de toute façon touché aucun trade en cinq ans.
Mesure : `research/regle_direction/RAPPORT.md`.

### La deuxième moitié de sa phrase est la vraie décision, et elle est neuve

« Le système n'est pas rentable de base, il faudra changer les triggers de signal » : c'est
exact, et **le second cerveau donne le chiffre qui le prouve, plus une piste que le projet a
identifiée puis jamais suivie** (`trading/frais et distance de stop.md`, maj 30/07) :

| k (distance de stop) | E brut | frais (c/k) | **E net** |
|---|---|---|---|
| **1,0 — le réglage actuel** | +0,016 | 0,088 | **−0,072** |
| **0,5** | +0,333 | 0,175 | **+0,158** |
| 0,33 | +0,307 | 0,265 | +0,042 |

Deux choses en découlent, et aucune n'est dans les chantiers ouverts :

1. **Le système est en espérance négative une fois les frais comptés**, au réglage actuel.
   Ce n'est pas « pas assez rentable », c'est **négatif**. Les frais en R varient comme `1/k` :
   diviser la distance de stop par deux **double** le coût du trade exprimé en R — identité
   arithmétique, pas estimation.
2. **Le levier le plus fort mesuré n'est pas le trigger, c'est la distance de stop.** La grille
   n'a que **trois points** et il n'existe **aucune mesure entre 0,5 et 1,0** : le vrai maximum
   peut être à 0,6 comme à 0,7, personne ne le sait. Le balayage `k` de 0,3 à 1,0 par pas de
   0,05 est **gratuit** (`analysis/replay_entries.py` existe, aucune donnée nouvelle) et il
   n'a **jamais été fait**.

⚠️ Piège de lecture déjà consigné dans le vault : « le stop à demi-distance multiplie
l'espérance par 20 » est vrai **en brut** et trompeur — le ×20 vient du R/R qui double à cible
inchangée, et net de frais il retombe à ~×10. Corollaire : **la variable à optimiser n'est pas
la distance de stop, c'est le couple (distance, cible)** ; les balayer séparément peut rater
l'optimum.

⇒ Chantier `Q13` — balayage (distance, cible) en espérance nette.
⚠️ **CORRIGÉ le 31/08 : `Q13` est FERMÉ depuis le 20/08, hypothèse INFIRMÉE dans les deux sens**
(`CHANTIERS.md` § « 20/08 (nuit, suite) », commit `6e23ec0` : « resserrer le stop dégrade »).
Le paragraphe ci-dessus le présentait encore comme un « nouveau chantier » : il proposait donc
une mesure **déjà faite, et qui a dit non**. Ne pas la relancer — le verrou B6 l'interdirait de
toute façon sous l'ancien id.

⇒ Ce qui reste vrai de ce raisonnement : le goulot n° 1 est **Q1** (rareté des entrées), et
l'audit du 24/08 l'a depuis reclassé derrière **B1** (le seuil de conviction hors de portée
hors PORTEUR).

---

## ⭐ A8 — G-rules : ROUVERT ET PRIORITAIRE le 25/08

**Jonas, 25/08** : les G-rules passent en chantier prioritaire. Ça annule le report du 20/08
(« des G-rules fixes me semblent dangereuses pour le moment **mais à voir** ») — le « à voir »
est arrivé.

**Ce qui ne change pas** : ⚠️ **interdit n° 5** — G1-G7 et leurs poids ne sont **jamais**
hyperoptés. La reprise se fait **par mesure**, pas par optimisation. Une hyperopt sur ce
périmètre ferme le chantier au lieu de l'ouvrir.

**Le point de départ chiffré** (campagne edge 2026-07, déjà mesuré, rien à relancer) :
**B pur (G1-G7 actives) = −17,38 %** contre **A pur (entrées + TP +1,5R + SL, zéro G-rule)
= +0,12 %**. Les G-rules coûtent ~17,5 points sur un substrat déjà nul, **par churn**
(187 trades contre 128). C'est le seul fait établi sur elles ; il dit *combien elles coûtent
ensemble*, pas *laquelle coûte*.

⚠️ **CORRIGÉ le 31/08** — la phrase « aucune ablation individuelle G1…G7 n'existe » écrite ici
le 25/08 **est fausse**. `research/edge_2026-07/RAPPORT.md` §2 contient une ablation par règle,
avec un verdict pour chacune, et c'est **la définition d'origine d'A8** dans `CHANTIERS.md`
(« G-set v2 : supprimer G1/G2/G3/G5/G6, garder G4+G7 ») :

| Règle | Verdict 11/07 | Chiffre |
|---|---|---|
| G1 BE +1R | ❌ supprimer | **+3,8 pts sans elle** |
| G2 trailing structurel 1h | ❌ supprimer | classe « trailing 1h » ≤ 0 en R-space |
| G3 trailing ATR 1h | ❌ supprimer | ≤ 0 même à 8×ATR |
| G4 TP partiel 50 % @1,5R | ✅ **garder** | seule brique compatible avec la queue |
| G5 extension post-BOS | ❌ supprimer | jamais déclenchée en 8,5 ans |
| G6 CHoCH 1h | ❌ supprimer | **la pire : +20 pts retirés** |
| G7 time-stop 24h | ⚪ garder (hygiène) | −0,01R |
| G-giveback (nouveau) | ➕ à tester | seule politique > 0 sur 2021-22 **et** 2023-26 |

**Le vrai manque n'est donc pas « mesurer », c'est « re-mesurer »** : ces ablations datent du
11/07, donc **long-only** (le short arrive le 04/08 avec A2) et **avant le correctif A1** (aucun
short n'avait de stop, corrigé le 24/08). Elles ne disent rien de la moitié short du produit.
A8 = rejouer ces ablations sur le substrat actuel, puis transformer le §2 du RAPPORT en
décision signée.

### ✅ Prérequis livrés le 31/08 (commit `91a25f0`)

L'outillage d'ablation était inutilisable sans le savoir. Deux défauts corrigés :

1. **`ARIT_G_OFF` échouait en silence.** Toute valeur hors des sept laissait les sept flags à
   `True`, sans erreur, sans log, sans test — un run d'ablation raté rendait un **produit B
   complet**, lu à tort comme « cette règle ne coûte rien ». Démontré sur `g3`, `G8`, `A8`,
   `G3 `. Le run s'arrête désormais à l'import avec la correction exacte à relancer.
   ⚠️ **Arbitrage de Jonas (31/08)** : il proposait une **demande de confirmation** plutôt qu'un
   arrêt. Écarté pour une raison technique qu'il a acceptée — ces backtests tournent **en
   parallèle**, et un process qui attend une réponse se bloque **en silence**, ce qui est pire
   qu'un arrêt. Son intention est conservée autrement : le message **nomme la correction**
   (`tu voulais dire 'G3' ? Relance avec : ARIT_G_OFF=G3`).
2. **G5 avait quatre défauts**, tous sur deux lignes d'`AritV1.py`. Le plus grave : elle lisait
   `bos_fresh_4h`, la cassure **haussière** seule, quel que soit le sens du trade — **sur un
   short, G5 supprimait la sortie TP2 quand le marché repartait CONTRE la position** (même
   famille que A1 ; le miroir `bos_fresh_bear_4h` existait depuis A2 et n'était pas branché).
   Elle ignorait aussi son flag, ne journalisait rien, et vivait dans la coquille freqtrade
   alors que `M05 §2.5` la place dans `gestion.py` — c'est cette dernière violation qui
   **causait** la première. Corrigée dans `gestion.set_extension()`.

⇒ **Les 7 règles sont désormais ablatables** (elles ne l'étaient qu'à 6), chaque run écrit son
protocole dans son journal (ferme **D3** de l'audit), et un test verrouille la cohérence entre
« règles déclarées coupables » et « flags réellement lus ». 469 tests passent.

### ⚠️ Ce qui bloque encore la mesure

- **B5** (audit 24/08) — G2 s'exécute **sans déclencheur** (`gestion.py:165`), face au plancher
  tout resserre. Ablater G2 mesurerait le bug, pas la règle.
- **B4** (audit 24/08) — G4 calcule la quantité au **prix du pic**, pas au prix courant : la
  fraction réellement vendue n'est pas 50 %. Même problème pour G4.
- **B1** (audit 24/08) — empilement multiplicateur ×0,85 + bump +0,05 : le seuil effectif vaut
  0,647 hors PORTEUR contre un p99 à 0,695. **Attend un arbitrage de Jonas, pas une mesure**
  (la prudence macro s'exprime sur le seuil **ou** sur le multiplicateur, jamais les deux).
  C'est lui qui commande le `n` disponible pour toute ablation.
- **B2** (audit 24/08) — `s_patterns` est un **offset constant** (non nul 99,9 % du temps), pas
  un score : il ne discrimine rien, il déplace le seuil. À lire avant le volet « poids ».

⇒ **Ordre proposé** : B5 et B4 (bugs, ~1 h chacun) → arbitrage B1 par Jonas → préenregistrement
`A8-ablation-g-rules` dans `research/EXPERIMENTS.jsonl` (verrou B6) → les 7 ablations.

---

## ⭐ DE1 — DONNÉES ENTRANTES : chantier prioritaire ouvert le 25/08

**Jonas, 25/08** : les données entrantes passent en chantier prioritaire, en même temps qu'A8.

⚠️ **Périmètre proposé, à confirmer par Jonas** — « données entrantes » n'a pas encore de
définition écrite dans le projet. Ce que ce chantier couvre, sauf correction de sa part :
**tout flux extérieur qui entre dans une évaluation** — et donc sa disponibilité, sa fraîcheur,
son historique et sa journalisation. En l'état, ces flux sont éparpillés dans cinq décisions
ouvertes et deux constats d'audit, sans aucun endroit qui les regarde ensemble :

| flux | où il en est aujourd'hui | référence |
|---|---|---|
| `macro_state.json` | **requis à l'exécution mais gitignoré** — rien ne garantit sa présence ni son âge | C2 (audit 24/08) |
| calendrier éco | barème de points acté, **3 paramètres à fixer** ; l'historique n'existe pas | C1-bis · Q15 |
| fenêtre de news | la porte **retarde** un signal, elle ne l'élimine pas — les « 91,75 % » ne décrivent pas des signaux et ne doivent plus être cités | R6 (mesuré chez BETA le 19/08) |
| Fear & Greed | adaptatif acté, P1-P3 tranchés le 20/08, **à coder** | A2-quinquies |
| funding | 86 % du profit de MacroFlip vient de là (checkpoint 27/07) — jamais réexaminé depuis | — |
| variables d'environnement | **non journalisées** : un run n'est pas reproductible à partir de son journal | D3 (audit 24/08) |

**La question qui commande tout le reste, et qu'aucune mesure ne tranchera** : est-ce que DE1
est un chantier de **fiabilité** (les données arrivent-elles, sont-elles fraîches, sait-on les
rejouer ?) ou un chantier d'**edge** (ces données apportent-elles quelque chose ?). Les deux
sont légitimes, ils n'ont pas le même premier pas :

- **fiabilité** ⇒ première marche = C2 + D3 (présence, âge et journalisation des entrées) ;
- **edge** ⇒ première marche = ablation des composants macro (D2/D3 de `CHANTIERS.md`), et elle
  bute d'abord sur `n` (p = 0,095 sur 12 trades).

Rien n'est codé sur DE1 tant que cette question n'est pas tranchée — écrire du code avant
reviendrait à choisir la réponse en silence.

---

## A2-ter — LEVIER : ta conclusion est la bonne, ton raisonnement ne l'est pas

**Jonas, 20/08** : « je ne suis pas sûr que ce soit un problème : si le SL est serré ça veut
dire que le seuil de conviction est faible donc pas la peine de surexposer, sauf si je commets
une erreur ».

### L'erreur, puisque tu la demandes : ce lien n'existe pas dans le code

**La distance de stop et la conviction sont deux quantités indépendantes.**

- La distance de stop est **géométrique** : `sl0` vient de la structure de prix
  (`gestion.entry_levels`, docs/03 §3.3). Un stop serré veut dire que le **niveau structurel
  est proche du prix d'entrée** — c'est un setup géométriquement propre, souvent **meilleur**
  (le R/R monte à cible inchangée). Ça ne dit rien de la conviction.
- Depuis **A6 (03/08), `compute_risk_pct` ne lit même plus la conviction** :
  `return min(params.RISK_CONSTANT_PCT, cap) / divisor`. Les paramètres `conviction` et
  `seuil` sont restés dans la signature mais **ne sont plus lus** — le sizing proportionnel à
  la conviction est *suspendu*. Le motif du gel est écrit dans le docstring : « la conviction
  n'a jamais démontré de pouvoir prédictif, faire varier la taille dessus ajoute de la
  variance sans espérance ».

Donc « SL serré ⇒ conviction faible » est faux **deux fois** : le lien n'existe pas
géométriquement, et même s'il existait le code ne s'en sert plus.

### Ta conclusion tient quand même, et pour une raison bien plus forte

Un levier > 1 est à écarter, non parce que le stop serré signale un setup faible, mais parce
que **le sizing actuel est déjà au-delà de Kelly** (calcul du 31/07, `trading/critere de
kelly.md` et `sizing (taille de position).md`) :

| Quantité | Valeur | Face à `params.py` |
|---|---|---|
| `f*` = E[R]/E[R²] sur l'espérance **brute** | **1,16 %** | = `RISK_CONSTANT_PCT` (0,0116) |
| `f*` sur l'espérance **bayésienne rétrécie** | **0,46 %** | **sous le plancher de 1 %** |
| point de croissance nulle `2f*` | **2,32 %** | cap `RISK_CAP_AFTER_PCT` = **3 %** |

Le cap à 3 % est à **2,6 × Kelly**, au-delà du point où la croissance logarithmique s'annule :
destructeur **même si l'edge était réel**. Et l'espérance nette de frais du réglage actuel est
**négative** (−0,072 R, § A2-sexies) — quand E < 0, la fraction optimale de Kelly est **nulle**,
pas « petite ».

> **Multiplier une espérance négative par un levier ne fait pas un profit, ça fait une ruine
> plus rapide.** ⇒ **levier = 1, et la question se rouvre le jour où E nette est positive.**

### Ce qui reste vrai du problème d'origine, et qui n'a rien à voir avec le levier

Le point que j'avais soulevé subsiste, et il est indépendant : quand la distance de stop est
**très serrée**, `stake = equity × risk_pct / dist_frac` explose, freqtrade plafonne le stake à
l'équité disponible, et le risque réel devient **inférieur** aux 1,16 % visés — **silencieusement**.
Ce n'est pas un argument pour le levier, c'est un **défaut de journalisation** : le bot croit
risquer 1,16 % et risque moins, sans jamais le dire.

⇒ **Chantier `Q14` — journaliser le plafonnement du stake** (`CHANTIERS.md`). Une ligne de
journal quand `stake` est plafonné, avec le risque réellement engagé. Aucune décision requise,
et c'est un prérequis de Q13 (le balayage de distance de stop) : on ne peut pas mesurer l'effet
d'un stop plus serré si le sizing décroche en silence quand il se resserre.

---

## A2-quinquies — F&G ADAPTATIF : acté, **P1-P3 tranchés le 20/08 au soir**

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

### Les trois paramètres — TRANCHÉS le 20/08 (« déploie le P1 P2 ET P3 »)

| # | Question | **Retenu** |
|---|---|---|
| **P1** | Amplitude et fenêtre du retournement | **+15 points sur 1 jour**, littéralement ce que Jonas a dit. `FG_REVERSAL_POINTS = 15`, `FG_REVERSAL_WINDOW_D = 1` |
| **P2** | Le miroir baissier | **symétrie** : −15 points retire le long comme +15 le rend. Sans ça le filtre est un pari haussier déguisé |
| **P3** | Ce que le retournement a le droit de faire | **lever le blocage seulement.** Ajouter du poids toucherait l'agrégation, donc l'interdit n° 5 |

⚠️ **Ce que P3 implique et qui n'est pas un détail** : le retournement F&G vit dans
`cio.direction_macro`, **hors de la somme des 5 composants**. C'est la règle de conception du
projet, mesurée **quatre fois indépendamment** (`trading/veto ou terme additif (branchement
d'un signal).md`) : un signal utile en véto/débloqueur détruit de la valeur en terme additif —
et ajouter un 6ᵉ terme à une somme à seuil ±2 sur 5 **recalibre silencieusement les 5 autres**.

⚠️ **Préenregistrement obligatoire (B6)** avant toute mesure : hypothèse formulée après avoir
vu le marché, comme le sous-groupe short/trailing.

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

## C1-bis — CALENDRIER : le palier binaire devient un BARÈME DE POINTS (acté 20/08)

**Jonas, 20/08** : « les passer en signaux en dur fixe en tout cas, mais faire en sorte
qu'elles ne vaillent par exemple que **1 point**, et les données marquées comme rouge
**3 points** ».

⇒ La porte news cesse d'être un booléen (`bloquant = impact_ff == "high"`) et devient une
**somme de points sur la fenêtre**, avec un seuil de blocage. Un événement orange isolé ne
bloque plus ; trois oranges simultanés, si. C'est ce que le palier binaire ne savait pas faire.

Le palier orange en place bloquait ~7 % du temps calendaire (11 bloquants sur 40) contre ~24 %
sans palier. Le barème remplace ce choix en tout-ou-rien par un curseur.

### Ce que le second cerveau dit avant qu'on code

`trading/veto ou terme additif (branchement d'un signal).md` — la règle du projet est
« **véto ou débloqueur, jamais terme additif, sauf preuve mesurée du contraire** », adossée à
quatre mesures. **Elle ne s'oppose pas à ce barème**, et il faut être précis sur pourquoi :

- ce qui est interdit, c'est d'ajouter un terme **au score de conviction ou au régime macro** —
  une somme à seuil dont on déplacerait la signification sans toucher aux autres composants ;
- ici la somme est **interne à la porte news** : mêmes objets (des événements), même nature,
  même fréquence. C'est le cas où la note dit explicitement qu'un score sommé garde du sens.

Mais le corollaire de mesure de cette note s'applique en entier : **le barème doit être
journalisé avec sa raison propre et rester ablatable seul**, sinon son apport marginal ne sera
jamais mesurable — c'est exactement ce qui a rendu R6 non mesurable chez BETA.

### ⚠️ Le piège qui décide de la faisabilité, et il est connu depuis le 04/08

`arit/calendrier economique dans arit (evenements suivis).md` :

> « Une fois `macro_state.json` généré, il ne contient que les événements **à venir**. Sur un
> backtest historique, la porte news passe donc **toujours** — elle ne filtre jamais rien.
> **Un backtest news-aware demanderait un calendrier historique, qui n'existe pas.** »

⇒ **Le barème ne sera mesurable par aucun backtest**, exactement comme le F&G adaptatif avant
Q11a. Il se code, il tourne en live, et **on ne saura pas ce qu'il vaut** tant qu'un calendrier
historique n'est pas constitué. À accepter explicitement, ou à traiter d'abord (le chantier
existe : `Q15`, dans `CHANTIERS.md`).

⚠️ Second rappel, parce qu'il a servi d'argument le 18/08 : **le chiffre « news_window bloque
91,75 % des rejets » est faux comme énoncé** (BETA R6 : 756 *lignes de journal* = 63 signaux,
dont 53 acceptés ailleurs). Ne pas s'en servir pour calibrer le barème.

### Les 3 paramètres qui restent à fixer

| # | Question | Défaut proposé |
|---|---|---|
| **N1** | **Le barème complet.** Tu as donné rouge = 3 et « elles » = 1. Que vaut le **medium/orange** — 2 points, ou 1 comme les low ? | **high 3 · medium 2 · low 1** (échelle régulière) |
| **N2** | **Le seuil de blocage.** À partir de combien de points la fenêtre bloque ? | **3** — un rouge seul bloque (comportement actuel préservé), trois oranges aussi, un orange seul non |
| **N3** | **La fenêtre d'addition.** Les points s'additionnent-ils sur ±30 min (`NEWS_WINDOW_MIN` actuel) ou sur une plage plus large, les publications se groupant le matin ? | **±30 min inchangé** — élargir la fenêtre ET ajouter un barème, c'est changer deux choses à la fois |

## G1 — ML sur l'agrégation : REPORTÉ le 20/08, reste une hypothèse

**Jonas, 20/08** : « lance Q4 pour le moment, mais **laisse en hypothèse le ML** ».

⇒ **La réponse à l'agrégation défaillante est l'ablation (Q4), pas un modèle appris.** Et c'est
défendable sur les chiffres, pas seulement par prudence : l'ablation seule fait passer l'IC de
**0,0642 à 0,0848**, contre **0,0851** pour `s_structure` isolé — elle **rejoint** le meilleur
score disponible. Un modèle appris devrait battre 0,0851 pour justifier de franchir
l'interdit n° 5 ; rien ne dit aujourd'hui qu'il le ferait, et il n'y a que **78 signaux**.

⚠️ « Lance Q4 » demande une précision : **Q4 est déjà mesurée et close** (20/08, ablation
retenue). Ce qui reste à décider est **quand l'appliquer en production** — c'est G3 ci-dessous,
et ta question sur les patterns y est traitée.

Rien à coder ici. L'insertion ML reste documentée dans `CHANTIERS.md § H2` (gardes non
négociables : purged K-fold + embargo, pondération par unicité, stabilité inter-périodes).

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

### Réponse à la question de Jonas (20/08) : « les patterns, sont-ils les patterns technique ? »

**Oui — `s_patterns`, ce sont les figures de bougies japonaises**, et rien d'autre. Barème
(`features.candle_patterns`, poids 0,15) :

| Situation | Note |
|---|---|
| **engulfing / hammer / pin bar** sur la bougie de cassure ou la suivante | **1,0** |
| pattern présent mais à moins de 3 bougies 4h | 0,5 |
| **doji sur la bougie de cassure** | **0** |
| aucune figure | 0,3 |

⚠️ **Mais le score qui porte les trois quarts de l'effet d'ablation n'est pas celui-là, c'est
`s_sr` — et il n'est pas ce que son nom dit.** Vérifié dans le code le 20/08 :

```python
df["s_sr"] = _score_sr(df["rr_dispo"])      # features.py:453
```

`s_sr` **n'est pas** une mesure de la force d'un support ou d'une résistance (ça, c'était C4,
la constante « force par nombre de touches », **supprimée** par toi le 04/08). C'est le
**R/R disponible jusqu'à la résistance**, recodé en note : ≥ 2,0 → 1,0 · ≥ RR_MIN → 0,7 ·
sinon 0.

> **C'est la même variable que la porte dure `rr_dispo >= RR_MIN`.** La même information est
> comptée **deux fois** : une fois en filtre éliminatoire, une fois en score pondéré à 0,15.

Trois conséquences, et elles se tiennent toutes :

1. **L'ablation de `s_sr` ne retire aucune information** — elle retire un **doublon**. C'est
   l'explication mécanique du +0,0205 d'IC, et elle est bien plus solide qu'un « ce score est
   mauvais ».
2. **Son IC négatif (−0,0497) n'est pas un mystère** : c'est le cas d'école d'une variable
   **tronquée par sa propre porte** — on ne voit jamais les `rr_dispo < 1,5`, donc la corrélation
   mesurée sur ce qui reste n'a pas le signe de la relation vraie. C'est exactement le chantier
   **Q3**, ouvert et non conclu, sur `rr_dispo` lui-même.
3. **`s_patterns` (−0,0162), lui, est bien un score technique faible**, mais son effet est
   marginal (le quart restant). Le débat « faut-il croire aux figures de bougies » n'est pas ce
   que Q4 a tranché.

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

## G8 — VPS : acté, non codé — et devenu le prérequis explicite de G2

Jonas, 12/08 : un VPS est prévu pour **Hermes Agent + ARIT 24/24**. Rien n'est codé, rien n'est
provisionné. ⚠️ Tant que ce n'est pas fait, tout dry-run dépend de la session Windows de Jonas.

**Depuis le 20/08, ce n'est plus seulement « la réponse envisagée » à G2, c'est sa condition.**
Jonas a tranché G2 ce jour-là : le suivi à distance passe chez BETA (chantier `O1-O3`,
`BETA/CHANTIERS.md`), « bientôt on aura un VPS à disposition ce qui simplifiera la tâche ».
Or **un dashboard distant hébergé sur la machine qui peut s'éteindre ne résout rien** : c'est
le défaut exact du watchdog actuel (`services/watchdog.py` alerte si le heartbeat est muet
> 10 min — mais si la session Windows tombe, le watchdog tombe avec, et **le silence devient
indistinguable de la santé**). Tant qu'il n'y a pas d'hôte extérieur, le suivi à distance ne
peut être qu'un **push sortant** (Discord), jamais une page à consulter.
