# A5 — ablation de la porte macro : INDÉCIDABLE

**Date** : 2026-08-18 · **Préenregistrement** : `research/EXPERIMENTS.jsonl` § `A5-ablation-porte-macro`
(essai cumulé n° 44) · **Code** : `analysis/ablation_macro.py` · **Résultats bruts** :
`analysis/out/ablation_A5.json` (gitignoré) · **Tests** : `tests/test_ablation_macro.py` (18)

> **Verdict, dans les termes fixés avant la mesure : INDÉCIDABLE.**
> A5 tient par défaut, faute de preuve du contraire. Ce n'est **pas** une validation.

---

## 0. Le MDE d'abord — ce que cet échantillon permet de voir

| Échantillon | n | MDE (R/trade) | n effectif (÷1,6) | MDE effectif |
|---|---|---|---|---|
| Signaux long de la production | 50 | **+0,433** | 31 | **+0,547** |
| Signaux short de la production | 28 | +0,578 | 18 | +0,731 |
| **Marginaux du bump NEUTRE — long** | **4** | **+1,530** | — | — |
| **Marginaux du bump NEUTRE — short** | **3** | **+1,766** | — | — |

**C'est le résultat principal.** La décision A5 ne porte que sur **7 signaux en 5 ans**. Pour
qu'un test les départage, il faudrait un écart de **1,5 à 1,8 R par trade** — dix fois
l'ordre de grandeur de tout edge plausible. Aucune mesure, aussi bien conduite soit-elle,
ne pouvait conclure ici. C'était écrit dans le préenregistrement comme issue attendue.

---

## 1. Le substrat (B1) — pourquoi le résultat total est inutilisable

| Sens | n | p(TP) | E[R] |
|---|---|---|---|
| long | 42 902 | 33,08 % | **−0,0123** |
| short | 42 902 | 32,87 % | **−0,0370** |

Espérance **négative** dans les deux sens. Sur une base pareille, tout filtre qui bloque des
trades améliore le résultat total **sans rien trier** — c'est le biais du substrat nul. C'est
exactement le mécanisme qui a produit le résultat historique « véto HOSTILE : −19,1 % →
−7,0 % » (`BUILD_NOTES` 17/07), qui n'est donc **pas** une validation du véto : il est
**non mesuré**. La seule question interprétable est celle de la **sélectivité**.

---

## 2. Les quatre variantes

Fidélité vérifiée : V0 reconstruit hors-ligne reproduit **exactement** les colonnes
`signal_long` / `signal_short` du dataset. Emboîtement V2 ⊂ V0 ⊂ V1 ⊂ V3 vérifié.

| Variante | sens | n | p(TP) | **E[R]** | IC 90 % (bootstrap blocs, ℓ=3) | R total |
|---|---|---|---|---|---|---|
| V0_prod | long | 50 | 36,0 % | **−0,0736** | [−0,350 ; +0,203] | −3,68 |
| V0_prod | short | 28 | 39,3 % | **+0,1150** | [−0,286 ; +0,516] | +3,22 |
| V1_sans_bump | long | 54 | 35,2 % | −0,0959 | [−0,352 ; +0,160] | −5,18 |
| V1_sans_bump | short | 31 | 41,9 % | **+0,1684** | [−0,221 ; +0,550] | +5,22 |
| V2_porteur_hostile | long | 44 | 36,4 % | −0,0609 | [−0,372 ; +0,250] | −2,68 |
| V2_porteur_hostile | short | 19 | 36,8 % | −0,0663 | [−0,474 ; +0,341] | −1,26 |
| V3_macro_off | long | 54 | 35,2 % | −0,0959 | [−0,352 ; +0,182] | −5,18 |
| V3_macro_off | short | 38 | 34,2 % | +0,0953 | [−0,233 ; +0,432] | +3,62 |

**Tous les intervalles de confiance contiennent zéro, et se recouvrent tous entre eux.**
Aucune variante n'est distinguable d'une autre.

Deux observations à ne pas surinterpréter, mais à ne pas taire :

1. **Le sélecteur long fait pire que le hasard.** E[R] = −0,0736 pour les 50 signaux long
   retenus, contre −0,0123 pour une entrée prise au hasard avec la même géométrie. Le
   filtrage long complet d'ARIT est **anti-sélectif** sur cet échantillon. Non significatif
   (n = 50, MDE +0,43), mais c'est le sens de l'écart, et il est cohérent avec l'IC de
   `produit_pondere` (+0,0642, inférieur à `s_structure` seul).
2. **Le short est le seul sens à espérance positive**, dans les quatre variantes sauf la
   plus stricte. Là encore : n ≤ 31, rien n'est prouvé.

---

## 3. Le test de A5 : sélectivité marginale

Question posée, la seule valide sur ce substrat : *les signaux que la porte bloque ont-ils
une espérance plus mauvaise que ceux qu'elle laisse passer ?*

| Porte étroite → large | sens | n marg. | E[R] marginaux | E[R] noyau | Δ | p brute |
|---|---|---|---|---|---|---|
| V2 → V0 (NEUTRE autorisé à trader) | long | 6 | −0,1667 | −0,0609 | −0,106 | 0,619 |
| V2 → V0 | short | 9 | +0,4978 | −0,0663 | +0,564 | 0,796 |
| **V0 → V1 (la pénalité NEUTRE = A5)** | **long** | **4** | **−0,3750** | −0,0736 | **−0,301** | 0,545 |
| **V0 → V1** | **short** | **3** | **+0,6667** | +0,1150 | **+0,552** | 0,939 |
| V1 → V3 (contrainte de direction macro) | long | 0 | — | — | — | — |
| V1 → V3 | short | 7 | −0,2286 | +0,1684 | −0,397 | **0,022** |

**Sur A5 (lignes V0 → V1), les deux sens se contredisent** : le bump bloque 4 longs mauvais
(−0,375) *et* 3 shorts excellents (+0,667). Avec n = 4 et n = 3 contre un MDE de +1,5 R,
ces deux chiffres sont du bruit pur. **Il n'y a rien à conclure, et c'est la conclusion.**

**Le seul p < 0,05 brut du run ne concerne pas A5** : c'est la ligne V1 → V3, sens short.
Les 7 shorts que la **contrainte de direction** macro bloque (shorts en régime PORTEUR)
affichent −0,229 contre +0,168 pour ceux qu'elle laisse passer, p = 0,022. Autrement dit :
si quelque chose porte de l'information dans la couche macro, ce n'est **pas** la pénalité
de seuil A5, c'est **l'interdiction directionnelle**. Ce test ne survit pas à la correction
(seuil BH 0,0077) et n'était pas l'hypothèse préenregistrée — il vaut comme **piste à
préenregistrer séparément**, pas comme résultat.

Ce résultat est cohérent avec la règle de conception déjà établie ailleurs : un signal macro
vaut comme **véto directionnel**, pas comme modulation continue d'un seuil.

---

## 4. Correction de tests multiples

Famille déclarée : **13 tests** (8 variantes×sens contre le modèle nul + 5 comparaisons
marginales exploitables). Le préenregistrement en annonçait 14 : la paire V1 → V3 côté long
n'a **aucun** signal marginal (V1 et V3 sont identiques en long — la direction macro
n'interdit jamais un long, seul le fail-safe le ferait). Écart signalé, sans effet sur le
verdict.

**Benjamini-Hochberg, FDR = 0,10 : 0 test sur 13 survit.** Le plus petit p (0,0223) est
trois fois au-dessus de son seuil BH (0,0077).

Réserve déclarée d'avance : les variantes partagent 44 signaux sur 54, BH suppose
l'indépendance — la correction est donc conservatrice dans le mauvais sens. Elle ne change
rien ici, puisque rien ne passait déjà avant correction.

---

## 5. Sensibilité de la longueur de bloc

Longueur ℓ = 3 fixée **avant** la mesure, sensibilité publiée comme exigé :

| Marginaux A5 | ℓ = 1 | ℓ = 3 | ℓ = 6 |
|---|---|---|---|
| long (n=4) | [−1,000 ; +0,875] | [−1,000 ; +0,250] | [−1,000 ; +0,250] |
| short (n=3) | [−0,167 ; +1,500] | [−0,167 ; +1,500] | [−0,167 ; +1,500] |

À n = 3 et n = 4, le bootstrap ne fait que redistribuer trois ou quatre nombres : les bornes
sont les valeurs extrêmes elles-mêmes. La longueur de bloc n'a plus d'influence parce qu'il
n'y a plus de structure à préserver. Autre façon de dire que l'échantillon n'existe pas.

---

## 6. Ce que ça change

| | |
|---|---|
| **A5** | reste appliquée telle quelle. Aucune ligne de production ne change. Ce n'est pas une validation, c'est une absence de raison de bouger. |
| **`MACRO_NEUTRE_CONV_BUMP`** | reste à 0,05. Le rouvrir demanderait un échantillon 50× plus grand — donc Q1 (rareté des entrées) d'abord. |
| **Ce qui est vraiment mesuré ici** | que la porte macro n'est **pas mesurable** à 78 signaux, et que la piste sérieuse est directionnelle, pas graduée. |
| **B6** | fermé : le registre `research/EXPERIMENTS.jsonl` existe, le script refuse matériellement de tourner sans entrée préenregistrée, et le compteur d'essais part de 30 (dette rétroactive), pas de 0. |
| **Hold-out** | intact. Rien n'a été lu au-delà du 2024-12-31. |

**Le vrai goulot reste celui du 12/08 : 78 signaux en 5 ans.** Tant qu'il n'est pas traité,
toute question posée à la couche macro recevra la même réponse — indécidable.

---

## 7. Reproduire

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe analysis\ablation_macro.py `
    --json analysis\out\ablation_A5.json
```

Prérequis : `analysis/out/arit_analyse.sqlite` (produit par `analysis/dataset.py`) et
l'entrée `A5-ablation-porte-macro` dans `research/EXPERIMENTS.jsonl` — sans elle, le script
s'arrête. Bootstrap déterministe (`SEED = 20260818`).
