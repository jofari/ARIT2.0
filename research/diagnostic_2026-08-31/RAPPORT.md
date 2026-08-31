# Diagnostic ARIT — les plus grosses lacunes (2026-08-31)

> Classées par **conséquence**, pas par gravité déclarée. Les six premières s'enchaînent
> causalement : la n° 1 cause les n° 3, 5 et une partie de la n° 2.
> Établi au commit `91a25f0`, après le backtest complet post-correctifs et l'ablation `A8-ablation-G5`.

---

## 1. Le `n` ne permet de décider de rien — racine de tout le reste

**78 signaux en 5 ans · 105 trades en 6,8 ans.** Le projet a écrit son propre critère d'abandon,
puis l'a franchi (`CHANTIERS.md:66`) : « **78 signaux en 5 ans : le critère d'abandon `N < 250`
est FRANCHI** ».

Ce n'est pas une gêne, c'est un **instrument de mesure qui ne résout pas les effets cherchés** :

| Mesure | Verdict |
|---|---|
| A5 — ablation porte macro | **INDÉCIDABLE** (7 signaux marginaux, MDE +1,53 R) |
| R1 — le trailing détruit les shorts (BETA) | **INDÉCIDABLE** (p = 0,0175, MDE 0,7463 R, meurt sous BH) |
| Q4 — métrique secondaire | **INDÉCIDABLE** (MDE 0,825 et 1,580 R) |
| MacroFlip — direction macro | p = 0,095 **sur 12 trades** |
| D1 — look-ahead | **0/20 trades** capturés |
| A8-ablation-G5 (31/08) | **n = 2** issues changées |

Six mesures, six « on ne peut pas savoir ». Structurel, pas malchanceux. **Tant que ça dure, le
projet produit des chiffres, pas des conclusions.**

Cause mécanique identifiée = **B1** (audit 24/08) : hors PORTEUR le seuil effectif vaut **0,647**
pour un p99 du produit pondéré à **0,695**. Le dernier centile est exigé **49 % du temps**.

> **B1 → peu d'entrées → `n` minuscule → rien n'est décidable → aucun résultat n'est fiable.**

## 2. Le test fondateur n'a jamais été exécuté

`docs/01` v4 (signée par Jonas le 03/08) impose : « **L'ordre des tests n'est pas négociable :
Test 1 d'abord.** »

**Test 1 — « la macro donne-t-elle vraiment la direction ? » — n'existe nulle part** : rien dans
`research/EXPERIMENTS.jsonl`, rien dans `research/`, rien dans `CHANTIERS.md`. Alors que
`AritV1.py:275` et `journal.py` ont été construits **exprès** pour le rendre lisible
(`docs/08 §46`).

Pendant ce temps les 4 expériences du registre portent sur les **scores**, les **stops** et les
**G-rules** — des raffinements en aval d'un edge dont l'existence n'a jamais été testée.
⇒ **plus grosse mauvaise allocation d'effort du projet.**

## 3. Le biais le plus grave est structurellement invérifiable

**Interdit n° 3** = zéro look-ahead. Jamais vérifié, et l'audit conclut qu'il **ne peut pas
l'être** : `lookahead-analysis` rend « too few trades caught (0/20) ». Derniers checks : **04/08**.
⇒ on ne peut pas exclure que **tous** les résultats soient gonflés par du look-ahead, et la
raison en est la lacune n° 1.

## 4. Rien n'a jamais touché la réalité

Vérifié le 31/08 : `tradesv3.dryrun.sqlite` = **0 trade** · journaux = **0 événement `live`**.

- **C3** — slippage réel jamais mesuré (`ev_exit` reçoit une constante) ⇒ le critère
  d'invalidation « > 2× le modèle » de `docs/03 §3.6` ne peut pas se déclencher.
- **B3** — porte de spread **débranchée** (`None` câblé en dur, `AritV1.py:94`).
- **funding** — jamais payé ni mesuré, alors que **86 % du profit de MacroFlip venait de là**.
- **G8** — pas de VPS : le watchdog meurt avec la session Windows ⇒ **le silence est
  indistinguable de la santé**.

⇒ Chaque chiffre du projet décrit un bot **qui n'a jamais existé**.

## 5. Le seul résultat positif tient sur 2 trades

Backtest complet du 31/08 (run `7481c40a4e89`) : **+3,20 %**, PF 1,12, 105 trades.

```
sans le meilleur trade  : +132,0 USDT
sans les 2 meilleurs    :  -55,0 USDT
profit médian par trade :   -6,39 USDT
```

4 des 5 meilleurs sont sur **SOL**. CAGR **0,46 %/an** contre un marché à **+1 978 %**.
⇒ Pas une stratégie qui gagne peu : un billet de loterie qui n'a pas encore perdu.

## 6. La doctrine ment sur le code, régulièrement et silencieusement

Constaté en une seule session (31/08) :

- `docs/README.md` décrit un bot **spot long-only** (futures long+short depuis le 04/08) — **D2** ;
- `DECISIONS.md` affirmait « aucune ablation individuelle G1…G7 n'existe » — **faux**
  (`research/edge_2026-07/RAPPORT.md` §2) ;
- `DECISIONS.md` proposait **Q13** comme « nouveau chantier » — fermé et **infirmé** le 20/08 ;
- « G5 strictement inerte, jamais déclenchée en 8,5 ans » — **infirmé** : 8 déclenchements.

Plus les collisions de vocabulaire (`BUILD_NOTES.md` § 2026-08-31), qui ont coûté **3 dégâts
mesurés**. ⇒ **Aucun document du projet n'est fiable sans vérification dans le code.**

---

## Ce qui est solide (et rend le diagnostic crédible plutôt que suspect)

- **Verrou B6** : préenregistrement **matériel**, qui fait planter les scripts de mesure.
- **Hold-out scellé (B5)**, correction Benjamini-Hochberg, bloc-bootstraps.
- **469 tests**, ruff propre, coquille freqtrade vraiment séparée du métier.
- **Auto-correction** : hypothèses falsifiées archivées et non effacées, section « deux chiffres
  à ne plus citer ».

**Le problème n'est pas la rigueur — elle est appliquée au mauvais endroit** : à raffiner un edge
qui n'a jamais été démontré.

---

## Lecture en une phrase

> **ARIT mesure très bien des choses qui n'ont pas d'importance, parce que la seule chose qui en a
> — l'edge existe-t-il ? — est bloquée par un manque de données que personne n'a traité.**

## Ordre qui en découle

1. **B1** — arbitrage de Jonas. Débloque le `n`, donc D1, donc tout le reste.
2. **Test 1** (`docs/01`) — le seul test qui puisse dire s'il y a un edge.
3. **Le funding** — 86 % du profit de MacroFlip, jamais rouvert depuis le 27/07. Plus gros
   chiffre inexploré du projet.

Le reste (B5, B4, B3, D2) est de l'**hygiène** : nécessaire, pas décisif.
