# Q13 — balayage (distance de stop, cible) en espérance nette · 2026-08-20

> Préenregistrée le 20/08 (`research/EXPERIMENTS.jsonl`, id `Q13-balayage-distance-stop`,
> essais cumulés **51**), mesurée le jour même. Code : `analysis/balayage_stop.py`.
> Substrat : les **88 signaux du train** (50 longs, 38 shorts), 4 paires, 2019-09 → 2024-12.
> **Hold-out B5 jamais lu** — le filtre est appliqué avant le balayage, pas après.

## Verdict : **INFIRMÉE**, dans les deux sens

L'hypothèse était : *l'espérance nette de frais est meilleure à demi-distance de stop
(k = 0,5) qu'à la distance structurelle (k = 1,0), à cible inchangée en R.*

| Sens | n | E nette k = 1,00 | E nette k = 0,50 | Δ | IC 90 % | MDE | Verdict |
|---|---|---|---|---|---|---|---|
| long | 50 | **−0,3943 R** | −0,4914 R | −0,0972 | [−0,3164 ; +0,1337] | 0,4003 | **INFIRMÉE** |
| short | 38 | **−0,3299 R** | −0,9741 R | **−0,6441** | [−0,9443 ; −0,3674] | 0,5102 | **INFIRMÉE** |

Côté short l'IC exclut zéro **du mauvais côté** : resserrer le stop ne dégrade pas « peut-être »,
il dégrade. Côté long le signe est net mais l'écart reste sous le MDE.

### Contrôle de cohérence, fait avant de lire quoi que ce soit

E **brute** reconstituée à k = 1,00 côté long : `−0,3943 + 0,3207 = −0,0736 R` — **exactement**
le R moyen des 50 signaux longs mesuré indépendamment le 20/08
(`research/regle_direction/RAPPORT.md`). La simulation reproduit la production au chiffre près ;
tout l'écart vient donc bien des frais, qui sont l'objet du chantier.

## Le vrai résultat n'est pas le verdict, c'est le coût

| | coût aller-retour à k = 1,00 |
|---|---|
| long | **0,3207 R** |
| short | **0,4147 R** |

> **Entre un tiers et 40 % d'un R part en frais et slippage à chaque trade**, avant qu'on ait
> parlé d'edge. C'est, à soi seul, une explication suffisante de « le système n'est pas rentable
> de base ».

D'où vient ce chiffre : `coût_R = 2 × (frais + slippage) / distance_frac`. La distance de stop
**médiane** des signaux longs est de **1,54 %** (moyenne 2,33 %), et la distribution descend
jusqu'à **0,07 %**. Or la moyenne des coûts est gouvernée par `E[1/distance]`, pas par
`1/E[distance]` : **une poignée de signaux à stop ultra-serré tire tout le coût moyen vers le
haut**. Le problème n'est pas le niveau moyen des distances de stop, c'est leur **dispersion**.

## Les 150 cellules de la grille sont négatives

E nette par (k, cible en R). Aucun couple ne passe au-dessus de zéro.

| | meilleure cellule | E nette | coût moyen |
|---|---|---|---|
| long | k = 0,50 · cible 2,5 R | **−0,1714 R** | 0,6414 R |
| long (2ᵉ) | k = 0,85 · cible 1,5 R | −0,2273 R | 0,3773 R |
| short | k = 0,95 · cible 3,0 R | **−0,2672 R** | 0,4365 R |

⚠️ Ces cellules sont les maxima d'une grille de 150 **lues après coup**. Elles ne sont **pas**
un résultat : sur 150 cellules bruitées, la meilleure est mécaniquement flatteuse. Elles sont
citées pour la **forme** de la surface, rien d'autre.

Forme, justement : à cible fixée, l'espérance nette **décroît quand k baisse**, de façon
monotone côté short et quasi monotone côté long. **Resserrer le stop détruit l'espérance** —
l'inverse de ce que l'hypothèse supposait.

## Ce que le second cerveau annonçait, et pourquoi ça ne se reproduit pas

`trading/frais et distance de stop.md` (maj 30/07) donnait **E nette = −0,072 R à k = 1** et
**+0,158 R à k = 0,5**. Deux écarts expliquent la divergence, et aucun n'est une erreur de la
note :

1. **Substrat différent.** La note dérivait ses chiffres de la campagne edge 2026-07 : 128
   trades, 2018-2026, macro neutralisée. Ici ce sont les **88 signaux de la stratégie actuelle**
   (macro active, long+short depuis A2).
2. **Coût sous-estimé d'un facteur ~3,7.** La note calait `c ≈ 0,0875 R` à k = 1 sur l'indication
   « ~0,15-0,20 R à demi-distance ». Le coût **mesuré** ici est de **0,32 R** côté long. Ce
   n'est pas une hypothèse concurrente : c'est le calcul fait sur chaque signal, un par un, avec
   sa propre distance de stop et le slippage de sa paire.

La bonne nouvelle méthodologique : **la note se falsifie elle-même proprement.** Elle réclamait
le balayage complet en disant « une décision prise sur une grille de 3 points n'est pas une
optimisation, c'est un sondage ». Le sondage est fait, et il dit l'inverse du sondage.

### La variante « cible en prix inchangée », qui est celle que la note décrivait vraiment

Resserrer le stop à k = 0,5 **en laissant le TP au même prix** revient à la cellule
(k = 0,5 · cible 3,0 R), puisque le R/R double. Elle donne **−0,3614 R** côté long contre
−0,3943 en production : **+0,033 R**, très loin des +0,158 annoncés et **sous tout MDE**.
Le « ×20 en brut » existe bien, mais net de frais il ne survit pas.

## ⚠️ Dette découverte en mesurant : les frais sont ceux du SPOT

```python
FEE_TAKER_FRAC = 0.001            # PDR 03.6 — Binance spot 0,1 % taker
```

Le bot est en **futures** depuis A2 (`config.dry.json` : `"trading_mode": "futures"`), où le
taker Binance USDⓈ-M est à **0,05 %**, pas 0,10 %. Le paramètre n'a pas suivi le changement de
produit du 04/08.

Portée exacte, pour ne pas surestimer le dégât :
- **En backtest et en live, freqtrade utilise les frais de sa propre configuration**, pas cette
  constante. Les runs freqtrade ne sont donc pas faussés.
- La constante sert de **fallback de journalisation** (`AritV1._journal_exit`) et de source à
  **toute mesure hors ligne** — dont celle-ci. ⇒ **Ce rapport surestime les frais d'environ
  30 %** (le slippage, lui, est inchangé).

**Le verdict ne bouge pas** : avec le taux futures, toutes les cellules remontent d'environ
0,1 R, la référence de production reste à ~−0,29 R, la monotonie reste, et l'hypothèse reste
infirmée. ⚠️ **Mais une cellule de la grille passerait tout juste positive**, et c'est
précisément le genre de chiffre qu'on ne lit pas après coup : la re-mesure aux frais corrects
exige un **nouvel id préenregistré** (le verrou B6 refuse de remesurer une expérience close, et
il a raison — rejouer jusqu'au bon résultat est du p-hacking par répétition).

⇒ Dette **T6-ARIT** ouverte dans `CHANTIERS.md`, et re-mesure **Q13-bis** à préenregistrer
après correction.

## Ce que ça change pour la suite

1. **La distance de stop n'est pas le levier espéré.** La piste « resserrer pour doubler le
   R/R » est fermée pour l'univers de signaux actuel : le gain brut est intégralement mangé.
2. **Le levier est le coût lui-même**, et il a trois entrées, toutes mesurables :
   **(a)** corriger le taux de frais (T6) · **(b)** passer en **maker** là où c'est possible
   (0,02 % contre 0,05 % en futures) · **(c)** **écarter les signaux dont la distance de stop
   est trop serrée pour être rentable** — un signal à stop de 0,2 % paie ~1,5 R de frais et ne
   peut structurellement pas gagner. Ce dernier point est une **porte**, il se mesure comme Q1,
   et il réduirait le nombre de signaux : à arbitrer avec le goulot de rareté.
3. **La cible mérite autant d'attention que le stop.** À k fixé, passer la cible de 1,0 R à
   2,5-3,0 R améliore l'espérance nette dans presque toute la grille — parce qu'un TP plus
   lointain amortit un coût fixe sur un R plus grand. C'est une piste distincte, non
   préenregistrée, qui n'a **pas** été testée ici et qui ne doit pas être lue comme un résultat.
