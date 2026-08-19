# Q4 / G3 — ablation de `s_sr` et `s_patterns` : rapport de mesure

**Date** : 2026-08-20 · **Décision** : G3, actée par Jonas le 20/08
**Préenregistrement** : `research/EXPERIMENTS.jsonl` § `Q4-ablation-scores-sr-patterns`
(famille de 6 tests, essais cumulés **50**) · **Code** : `analysis/ablation_scores.py`
**Substrat** : 42 902 évaluations 4h étiquetées, 4 paires, 2019-09-08 → 2024-12-31,
`split='train'`. Hold-out **scellé**, jamais lu.

---

## Verdict, selon la règle écrite avant la mesure

> **Ablation RETENUE sur la métrique primaire.** Les trois conditions préenregistrées sont
> remplies dans les deux sens : ΔIC ≥ +0,010, intervalle bootstrap 90 % excluant 0, et
> survie à Benjamini-Hochberg (FDR 0,10).

**Ce que la mesure ne dit pas** : que la production doit changer. Elle mesure le pouvoir
prédictif de l'agrégat, pas le résultat en trades — et le coût en nombre d'entrées est lourd
(§ 3). Cette réserve était écrite **avant** la mesure, pas ajoutée après.

---

## 1. Métrique primaire — ΔIC de Spearman contre le rendement futur

| Comparaison | IC production | IC variante | **ΔIC** | IC bootstrap 90 % | BH |
|---|---|---|---|---|---|
| **V1** (`s_sr` + `s_patterns` retirés) — long | 0,0642 | **0,0848** | **+0,0205** | [0,0135 ; 0,0275] | ✅ |
| **V1** — short | 0,0357 | **0,0544** | **+0,0187** | [0,0115 ; 0,0260] | ✅ |
| V2 (`s_sr` seul retiré) — long | 0,0642 | 0,0796 | +0,0154 | [0,0085 ; 0,0222] | ✅ |
| V2 — short | 0,0357 | 0,0512 | +0,0154 | [0,0086 ; 0,0223] | ✅ |

p bootstrap < 0,0002 pour les quatre (bornée par les 10 000 réplicats : aucun tirage ne
produit un Δ négatif). Les quatre survivent à BH sur la famille de 6.

**Trois lectures qui comptent** :

1. **L'agrégat ablaté rattrape le meilleur score seul.** IC(V1) long = **0,0848**, contre
   **0,0851** pour `s_structure` seul (B9, 12/08). Autrement dit, l'agrégation à cinq termes
   détruisait exactement ce que ses deux termes à IC négatif y injectaient — ni plus, ni moins.
   Retirer les deux ne fait pas mieux que le meilleur score isolé, ça le **rejoint**.
2. **`s_sr` porte les trois quarts de l'effet** (+0,0154 sur +0,0205). `s_patterns` ajoute
   ~0,005, cohérent avec son IC de −0,0162 contre −0,0497.
3. **Le short en profite autant que le long**, ce qui n'était pas acquis : les IC de B9
   portaient sur les scores long. L'issue attendue déclarait ce signe « incertain ».

**Robustesse aux blocs** — la longueur de bloc était fixée à 24 bougies (96 h = la fenêtre du
label) ; la sensibilité publiée d'avance couvre 12 et 48 :

| Comparaison | bloc 12 | **bloc 24** | bloc 48 |
|---|---|---|---|
| V1 − V0 (long) | [0,0141 ; 0,0269] | [0,0135 ; 0,0275] | [0,0132 ; 0,0278] |
| V1 − V0 (short) | [0,0119 ; 0,0254] | [0,0115 ; 0,0260] | [0,0107 ; 0,0264] |

L'intervalle ne bouge pas. Le résultat ne dépend pas du choix de bloc.

---

## 2. Le piège arithmétique — prédit, puis constaté

`POIDS` somme à 1,00. Retirer 0,30 de poids **sans renormaliser** plafonne la conviction à
0,70 × multiplicateur, alors que le seuil TRANSITION vaut 0,65 et le multiplicateur 0,85
(⇒ 0,595 : plus aucun signal possible en TRANSITION).

| Variante | Σ poids | signaux long | signaux short |
|---|---|---|---|
| V0 production | 1,00 | 50 | 28 |
| V1 ablation **renormalisée** | 1,00 | 28 | 22 |
| V2 `s_sr` seul, renormalisé | 1,00 | 26 | 21 |
| **V3 ablation brute** (contrôle) | **0,70** | **5** | **8** |

**5 signaux long au lieu de 50.** Une ablation brute aurait mesuré un durcissement de seuil,
pas un retrait de scores — et sur 5 signaux, absolument rien n'aurait été concluable. La
renormalisation n'est pas un raffinement, c'est la condition d'existence de la mesure.

Elle ne choisit aucune valeur : les rapports entre les trois poids conservés
(0,40 : 0,20 : 0,10) sont préservés exactement. L'interdit n° 5 n'est pas touché.

⚠️ V3 n'est **pas** testé en IC : V3 = V1 × 0,70 est une transformation monotone croissante,
donc son IC de rang est **identique** à celui de V1 par construction. Le tester aurait ajouté
un test à la famille pour zéro information.

---

## 3. Métrique secondaire — sélectivité marginale (sous-puissante, comme déclaré)

L'ablation **retire** des signaux et n'en ajoute aucun : V1 ⊂ V0 strictement, dans les deux
sens (0 signal gagné). Le non-emboîtement envisagé au préenregistrement ne s'est pas produit.

| Sens | Signaux perdus | E[R] des perdus | E[R] du noyau conservé | MDE | p brute | BH |
|---|---|---|---|---|---|---|
| long | 22 | **+0,0828 R** | **−0,1964 R** | 0,825 | 0,405 | ❌ |
| short | 6 | −0,1667 R | +0,1918 R | 1,580 | 0,515 | ❌ |

**Les deux sens se contredisent et aucun n'approche son MDE.** Côté long l'ablation retire des
signaux *meilleurs* que ceux qu'elle garde ; côté short, *pires*. Avec 22 et 6 observations,
c'est indécidable — et c'était l'issue annoncée d'avance pour cette métrique.

⚠️ **À ne pas balayer pour autant** : l'amélioration d'IC ne se lit **pas** dans les trades
effectivement perdus côté long. Ce n'est pas contradictoire — l'IC porte sur 42 902
évaluations, la sélectivité sur 22 signaux, et les deux ne mesurent pas la même chose — mais
personne ne peut affirmer aujourd'hui que le gain d'IC se traduira en meilleurs trades.

À noter aussi : le noyau conservé côté long est à **−0,1964 R**. L'espérance des entrées reste
négative après ablation. Améliorer un IC ne crée pas un edge.

---

## 4. Ce que ça coûte, et pourquoi la décision revient à Jonas

L'ablation supprime **44 % des signaux longs** (50 → 28) et **21 % des shorts** (28 → 22).

Or le goulot n° 1 du projet est la **rareté des entrées** : 78 signaux en 5 ans, 0,16 % des
évaluations (chantier Q1, priorité validée le 20/08). Appliquer l'ablation en production
améliore un IC mesuré **et aggrave le goulot mesuré**. Les deux sont vrais en même temps.

**La question posée à Jonas** — elle est dans `DECISIONS.md § G3` :

> On applique l'ablation en production tout de suite, ou on attend **Q1** (courbe N(seuil)) pour
> savoir de combien on peut desserrer les portes en compensation ?

L'ordre validé le 20/08 place Q1 en tête des chantiers. Un abaissement de seuil mesuré par Q1
pourrait rendre les 22 signaux perdus, sans réintroduire les deux scores à IC négatif. Rien
n'oblige à payer les deux coûts.

---

## 5. Écarts au préenregistrement

| Point annoncé | Réalisé |
|---|---|
| Famille de 6 tests | 6 — conforme |
| Emboîtement non garanti, marginaux « gagnés » mesurés à part | mesurés : **0 gagné** dans les deux sens |
| Issue attendue : ΔIC positif long, signe incertain short | positif dans les **deux** sens |
| Métrique secondaire sous-puissante | confirmé (MDE 0,825 et 1,580 R) |

Aucun écart de protocole. La reconstruction de V0 reproduit exactement les 50/28 signaux du
dataset (vérification de fidélité, sinon le script s'arrête).

⚠️ La colonne `direction_macro` du dataset date du 12/08, donc d'**avant A2-quater** (20/08).
C'est voulu : Q4 ne fait varier **que** l'agrégation, toutes les autres portes tenues
constantes. Mesurer l'effet d'A2-quater est un autre travail, avec son propre
préenregistrement.
