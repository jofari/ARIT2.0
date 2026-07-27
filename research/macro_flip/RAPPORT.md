# MacroFlip — le Macro Analyst tout seul, sans technique ni gestion

> Expérience demandée par Jonas le 2026-07-27, après le verdict « edge d'entrée NUL »
> de la campagne A/B corrigée (BUILD_NOTES 2026-07-19).
> **Aucun code de production touché** : `AritV1.py`, `arit_lib/`, `docs/` et
> `config.dry.json` sont intacts. Tout vit dans `research/macro_flip/` +
> `user_data/strategies/MacroFlip.py` (banc de mesure, pas un bot).

## 1. Le protocole, tel que demandé

| Paramètre | Valeur |
|---|---|
| Règle | macro **PORTEUR → LONG** · **HOSTILE → SHORT** (le « put ») · **NEUTRE → on garde la position** |
| Sortie | uniquement le signal macro inverse — **ni SL, ni TP, ni trailing, ni G-rule** |
| Taille | **50 % de l'équité** à chaque entrée (compounding), levier **1x** |
| Marché | BTC/USDT:USDT perpétuel Binance USDT-M, marge isolée |
| Timeframe | **4h**, détail d'exécution 5m (règle maison) |
| Période | 2020-01-01 → 2026-07-13 (6,5 ans ; borne basse = début des données mark futures) |
| Capital | 10 000 USDT |
| Signal | `arit_lib.macro_regime` (docs/06 §6.2) — 5 composants : DXY, taux Fed, mcap stablecoins, funding, Fear & Greed |

Point-in-time vérifié : le régime du jour J ne reflète que des données ≤ J-1
(décalage +1 j dans `daily_regimes`, puis `merge_asof` backward). Zéro look-ahead.

**Vérifications de mécanique (smoke 2020-H1)** : flip long→short sur la *même* bougie
(pas de trou d'un jour), levier 1x, stake = 50 % de l'équité courante, funding appliqué,
et **aucune sortie par SL/ROI/liquidation** sur toute la campagne (11 `exit_signal` +
1 `force_exit` de fin de backtest).

## 2. Le résultat brut, tel quel

| | |
|---|---|
| **Profit total** | **+263,5 %** (10 000 → 36 348 USDT) |
| CAGR | 21,8 % |
| Profit factor | 2,80 |
| Trades | **12** (6 longs / 6 shorts), 50 % de gagnants |
| Durée moyenne | 199 jours |
| Drawdown max | 24,3 % (196 jours, du 2025-11-20 au 2026-06-04) |
| **Buy & hold BTC sur la même fenêtre** | **+769,3 %** |

**Le premier chiffre à retenir : la stratégie fait 3× moins bien que ne rien faire.**

### Les 12 positions

| # | Entrée | Sortie | Jours | Sens | Prix entrée → sortie | PnL USDT | Funding |
|---|---|---|---|---|---|---|---|
| 1 | 2020-01-01 | 2020-02-04 | 34 | LONG | 7 222 → 9 294 | +1 270 | −143 |
| 2 | 2020-02-04 | 2020-04-16 | 72 | SHORT | 9 294 → 6 646 | +1 816 | +232 |
| 3 | 2020-04-16 | 2022-04-15 | **729** | LONG | 6 646 → 40 180 | **+15 446** | **−17 193** |
| 4 | 2022-04-15 | 2023-07-11 | 452 | SHORT | 40 180 → 30 461 | +3 959 | +560 |
| 5 | 2023-07-11 | 2023-08-09 | 29 | LONG | 30 461 → 29 710 | −501 | −90 |
| 6 | 2023-08-09 | 2023-11-03 | 86 | SHORT | 29 710 → 34 680 | −2 524 | +137 |
| 7 | 2023-11-03 | 2025-11-20 | **748** | LONG | 34 680 → 92 405 | **+18 274** | **−5 944** |
| 8 | 2025-11-20 | 2025-12-04 | 14 | SHORT | 92 405 → 93 500 | −281 | +22 |
| 9 | 2025-12-04 | 2026-04-07 | 124 | LONG | 93 500 → 68 746 | −6 406 | −172 |
| 10 | 2026-04-07 | 2026-04-19 | 12 | SHORT | 68 746 → 75 473 | −2 024 | −19 |
| 11 | 2026-04-19 | 2026-06-04 | 46 | LONG | 75 473 → 64 336 | −2 892 | −34 |
| 12 | 2026-06-04 | 2026-07-13 | 38 | SHORT | 64 336 → 63 750 | +212 | +67 |

## 3. Trois découvertes

### 3.1 Le funding mange 86 % du profit — et c'est réparable

**−22 579 USDT de funding payés au total**, soit 86 % du profit net. Le seul trade n°3
(long perp tenu 729 jours) coûte **−17 193 USDT** : son gain brut de +33 000 est amputé
de moitié. Tenir un long de deux ans sur un **perpétuel** est une erreur d'exécution —
le funding est le prix du levier, or on n'utilise aucun levier (1x).

Rien n'oblige à tenir les jambes longues en perp. En **spot** (funding = 0), même signal,
mêmes dates :

| Exécution | Résultat |
|---|---|
| A. tout en perp (ce qui a été backtesté) | +267 % |
| **B. long en SPOT + short en perp** | **+577 %** |
| C. long en SPOT + cash pendant HOSTILE (pas de short) | +484 % |
| D. long en perp + cash pendant HOSTILE | +217 % |
| — buy & hold spot 50 % (référence à capital égal) | +385 % |
| — buy & hold spot 100 % | +769 % |

(Scénarios B-D recalculés analytiquement depuis les 12 trades, pas re-backtestés.)

### 3.2 Le short apporte quelque chose — modestement

Scénario B (+577 %) contre scénario C (+484 %) : **le « put » vaut +93 points** sur 6,5 ans.
Ce n'est pas rien, mais ça repose sur 6 shorts dont **3 gagnants**, et le PnL short total
en perp n'est que de **+1 156 USDT** — l'essentiel vient de deux shorts (COVID 2020 et
bear 2022) qui sont autant de la chance que du signal.

### 3.3 Tout le résultat tient dans 2 trades

En scénario B, rendement par position trié :

```
+504,5 %  729 j  LONG   <- bull 2020-2021
+166,3 %  748 j  LONG   <- bull 2023-2025
 +32,5 %   72 j  SHORT     puis plus rien de significatif
 +28,6 %   34 j  LONG
 +28,1 %  452 j  SHORT
  +1,2 %   38 j  SHORT
  -1,2 %   14 j  SHORT
  -2,6 %   29 j  LONG
 -10,0 %   12 j  SHORT
 -14,9 %   46 j  LONG
 -16,0 %   86 j  SHORT
 -26,6 %  124 j  LONG
```

| | |
|---|---|
| Les 12 positions | +577 % |
| **Sans la meilleure** | **+92 %** |
| **Sans les 2 meilleures** | **+5 %** |

Les 10 autres positions rapportent **+5 % en 6,5 ans**. La stratégie se résume à
« être long pendant les deux grands bull markets » — ce que n'importe quel filtre de
tendance lent aurait fait aussi.

### 3.4 Sortir en NEUTRE détruit le résultat (variante testée)

La règle « on garde la position en NEUTRE » avait été choisie par Jonas contre la variante
« on repasse cash dès que ce n'est plus franc ». Les deux ont été backtestées, tout-perp,
même période :

| Variante | Trades | Durée moy. | Profit | PF | CAGR |
|---|---|---|---|---|---|
| **On garde en NEUTRE** (règle retenue) | **12** | 199 j | **+263,5 %** | **2,80** | 21,8 % |
| Cash en NEUTRE (`ARIT_MACRO_FLAT_NEUTRE=1`) | 134 | 9 j | +69,6 % | 1,29 | 8,4 % |

134 trades de 9 jours au lieu de 12 de 199 jours : le churn coûte **194 points**. Le bon
réflexe était le bon — mais noter que la variante à 134 trades, elle, a une taille
d'échantillon exploitable, et qu'elle reste positive (PF 1,29). C'est peut-être la version
à étudier pour *mesurer* le signal, même si c'est la mauvaise version pour le trader.

## 4. Est-ce que ça bat le hasard ?

**Monte-Carlo A** — mêmes 12 fenêtres, **sens tiré à pile ou face**, 20 000 tirages
(funding inversé avec le sens, donc tirage honnête) :

| | |
|---|---|
| médiane du hasard | −381 USDT (≈ 0 %) |
| p90 du hasard | 36 302 USDT |
| **MacroFlip** | **36 724 USDT → percentile 90,5, p = 0,095** |

**Monte-Carlo B** — toujours long sur perp, 12 durées identiques placées au hasard,
funding réel recalculé sur chaque fenêtre : MacroFlip est au **percentile 57,6**
(médiane du hasard : 30 890 USDT). Comme outil de *timing long-only*, le signal
n'apporte quasiment rien.

**Bootstrap** (ré-échantillonnage des 12 trades, scénario B) : IC 90 % =
**[−2 % ; +7 188 %]**. Avec n = 12 et une position qui pèse la moitié du résultat,
l'intervalle est inexploitable.

## 5. Verdict honnête

1. **Tel que demandé (tout en perp), c'est perdant contre le buy & hold** : +263 % vs
   +769 %. À capital égal (50 %), +263 % vs +385 %. La stratégie détruit de la valeur.
2. **La cause principale est une erreur d'exécution, pas le signal** : le funding sur des
   longs de 2 ans. Passer les longs en spot fait +267 % → +577 %, ce qui repasse au-dessus
   de la référence à capital égal (+385 %).
3. **Mais le signal n'est pas démontré pour autant.** p = 0,095 au Monte-Carlo directionnel
   (donc *pas* significatif au seuil usuel), percentile 57,6 en timing long-only, et surtout
   **+5 % sans les 2 meilleurs trades**. 12 observations en 6,5 ans : la puissance
   statistique est quasi nulle. On ne peut ni valider ni invalider.
4. **À signaler quand même** : c'est le premier signal d'ARIT qui n'est pas manifestement du
   bruit. L'edge d'entrée technique était à p = 0,99 (campagne du 19/07) ; celui-ci est à
   p = 0,095. Un ordre de grandeur d'écart, sur une couche que le PDR traitait comme un
   simple véto.
5. **Alerte fraîcheur** : les 4 dernières positions (déc. 2025 → juil. 2026) sont **toutes
   perdantes** (−6 406, −2 024, −2 892, +212) — c'est le drawdown de 24,3 % sur 196 jours.
   Le signal ne fonctionne pas sur la période récente.

## 5 bis. « Améliorer le management pour une V1 » — mesuré, et ça ne marche pas

> Demande de Jonas le 27/07 après lecture des résultats. Testé avec
> `research/macro_flip/gestion_sim.py` : **22 politiques de sortie × 6 règles de taille**,
> rejouées bougie par bougie (4h) sur les 12 épisodes, stop touché en intrabar évalué
> avant tout le reste, funding accru sur le notionnel courant, équité marquée au marché.

### D'abord, une correction importante sur le drawdown

**Le vrai drawdown n'est pas 24,3 %, c'est 49,2 %** (61,8 % en tout-perp).

Le chiffre de freqtrade est calculé sur la courbe des **trades clôturés** : entre deux
clôtures espacées de 729 jours, il ne voit rien. Marqué au marché bougie par bougie, le
creux réel est le krach de mai-juillet 2021 traversé en position. **Piège de mesure à
retenir pour tout backtest à positions longues.**

### Le résultat : rien n'améliore HOLD

Exécution spot (la recommandée), extraits classés par performance :

| Politique de sortie | Perf | DD max | Coupes | **Sans top 2** |
|---|---|---|---|---|
| SL 12×ATR | +621,8 % | 49,2 % | 3/12 | +12,1 % |
| time-stop 90 bougies si perdant | +616,4 % | 49,2 % | 6/12 | +11,2 % |
| **HOLD (aucune gestion)** | **+579,0 %** | **49,2 %** | **0/12** | **+5,4 %** |
| BE après +20 % / +50 % | +579,0 % | 49,2 % | 0/12 | +5,4 % |
| SL 8×ATR | +541,2 % | 49,2 % | 5/12 | −0,5 % |
| SL 3×ATR | +452,8 % | 49,2 % | 8/12 | −14,2 % |
| giveback 50 % | +259,3 % | 50,6 % | 4/12 | −1,8 % |
| chandelier 12×ATR après +50 % | +101,1 % | 30,8 % | 4/12 | +11,4 % |
| **chandelier 20×ATR** | **+94,6 %** | **18,2 %** | 8/12 | **+37,6 %** |
| chandelier 12×ATR | +38,9 % | 14,0 % | 11/12 | +1,3 % |
| chandelier 8×ATR | +16,4 % | 13,6 % | 12/12 | −4,3 % |
| chandelier 5×ATR | −2,2 % | 8,6 % | 12/12 | −6,9 % |

Trois lectures :

1. **Les seules politiques au-dessus de HOLD (+7 %, +6 %, +3 %) sont dans le bruit** —
   3 points d'écart sur 12 observations ne veulent rien dire. Et elles ne réduisent
   **pas du tout** le drawdown (49,2 %, identique à HOLD) : elles ne coupent que des
   épisodes déjà perdants, sans jamais protéger pendant les gros.
2. **Toute gestion qui serre détruit le résultat.** Plus le trailing est serré, pire c'est :
   20×ATR → +94,6 %, 12×ATR → +38,9 %, 8×ATR → +16,4 %, 5×ATR → **−2,2 %**. Le chandelier
   à 5×ATR coupe les 12 épisodes sur 12 : il transforme un système de tendance en machine
   à frais.
3. **Le breakeven ne se déclenche jamais** (perf identique à HOLD au centième) : aucun
   épisode ne revient sous son prix d'entrée après avoir gagné 20 %.

### Pourquoi c'est structurel, pas un mauvais réglage

**La valeur du signal EST la durée de détention.** 99 % du résultat vient de deux
tendances de 2 ans ; toute règle qui sort tôt coupe exactement ce qui rapporte. C'est
l'inverse exact du diagnostic du 17/07 sur les entrées techniques (burst momentum rapide,
substrat nul) — donc **on ne peut pas recycler les G-rules ici**, elles sont conçues pour
un profil de trade opposé.

### La taille non plus (6 règles testées, sorties inchangées)

| Règle de taille | Perf | DD max | **Perf/DD** | Fraction moy. |
|---|---|---|---|---|
| **fixe 50 % (actuel)** | +579,0 % | 49,2 % | **11,77** | 0,50 |
| vol-target 35 % (cap 75 %) | +595,1 % | 51,3 % | 11,59 | 0,69 |
| vol-target 35 % (cap 100 %) | +622,1 % | 54,4 % | 11,43 | 0,78 |
| proportionnel au score macro | +427,5 % | 47,0 % | 9,09 | 0,40 |
| score × vol-target 35 % | +186,9 % | 35,7 % | 5,24 | 0,32 |

Le vol-targeting achète du rendement en achetant proportionnellement autant de drawdown :
le ratio ne bouge pas. **Le 50 % fixe est déjà le meilleur des six.** Et sizer par la force
du score macro (+2 vs +5) **dégrade** — l'intensité du score ne porte pas d'information.

### La seule piste qui mérite un second regard

**Chandelier 20×ATR** : +94,6 % seulement, mais **DD 18,2 %** et surtout
**+37,6 % sans les 2 meilleurs épisodes** — sept fois la robustesse de HOLD (+5,4 %).
C'est la seule règle dont le résultat ne repose pas sur deux coups de chance. En échange
elle abandonne les 4/5 de la performance. À garder en tête si l'objectif de la V1 est
« survivable » plutôt que « spectaculaire en backtest » — mais à ce niveau de rendement
(10,7 %/an), le buy & hold reste devant.

### Conclusion sur le management

**Il n'y a pas de gain de management à aller chercher ici.** Le classement des leviers
réellement mesurés, par impact décroissant :

| Levier | Gain mesuré | Statut |
|---|---|---|
| **Passer les jambes longues en SPOT** | **+267 % → +579 %** | identifié, non implémenté |
| Augmenter le nombre d'observations (variante NEUTRE : 134 trades) | — | non exploré |
| Valider les seuils en walk-forward | — | **jamais fait** |
| Gestion des sorties (22 politiques) | **≈ 0**, dans le bruit | testé, négatif |
| Règles de taille (6 variantes) | **≈ 0**, le fixe gagne | testé, négatif |

## 6. Réserves méthodologiques

- **Calibration in-sample** : les seuils de docs/06 §6.2 (±0,5 % DXY / 20 j, ±0,10 pt taux /
  60 j, +2 %/−1 % stablecoins / 30 j, 0,05 % funding, F&G 25/45) n'ont jamais été validés
  hors échantillon. Ils ont été posés en connaissance générale du marché 2018-2026.
- **Point-in-time des données** : funding (Binance) et Fear & Greed (alternative.me) sont
  propres. DXY et taux Fed (FRED) sont décalés de +1 j, ce qui couvre leur délai de
  publication. **La mcap stablecoins (DefiLlama) est reconstruite rétroactivement** : la
  série vue aujourd'hui n'est pas celle qu'on aurait eue en 2020 — biais résiduel non chiffré.
- **Artefact week-end écarté** : vérifié, HOSTILE est réparti uniformément sur les 7 jours
  (11,1 % à 13,5 %). Le `ffill` à 2 jours absorbe correctement les séries en jours ouvrés,
  le fail-safe « ≥ 3 composants stale ⇒ HOSTILE » ne se déclenche pas sur les week-ends.
- **Scénarios B/C/D non re-backtestés** : recalculés depuis les rendements des 12 trades
  (modèle validé à 0,3 pt près contre freqtrade sur le scénario A). Un vrai run spot
  changerait les chiffres à la marge (frais, slippage).
- **Une seule paire, un seul marché** : BTC. Aucune validation croisée.
- **Simulation de gestion (§5 bis)** : `gestion_sim.py` reproduit HOLD à +579 % contre
  +577 % pour le calcul analytique et +263,5 % (tout-perp) contre +268 % — écart < 2 pt,
  modèle validé. Deux hypothèses pessimistes assumées : après une sortie anticipée on
  reste **en cash jusqu'au flip macro suivant** (aucune ré-entrée dans l'épisode), et le
  stop est testé en intrabar avant toute autre règle. Une politique avec ré-entrée
  ferait mieux que ce qui est mesuré ici — mais aucune ne s'approche assez de HOLD pour
  que ça change le classement.

## 7. Ce que je ferais ensuite (rien n'est lancé sans ton accord)

Dans cet ordre — le management est volontairement absent, §5 bis montre qu'il n'y a rien
à y gagner.

1. **Passer les jambes longues en spot.** Seul changement au gain mesuré et important
   (+267 % → +579 %). Ça implique une config multi-marchés (spot pour les longs, futures
   pour les shorts) : c'est du travail d'exécution, pas de stratégie. **Le seul chantier
   V1 que les mesures justifient aujourd'hui.**
2. **Walk-forward des seuils 06.2** : calibrer sur 2020-2022, tester sur 2023-2026. C'est
   le seul moyen de savoir si le p = 0,095 est du signal ou de la sur-calibration. Tant que
   ce n'est pas fait, **aucune V1 ne devrait partir en dry-run**.
3. **Augmenter n** : le même signal sur ETH, SOL, BNB, et la variante `ARIT_MACRO_FLAT_NEUTRE=1`
   (134 trades — la seule version avec un échantillon mesurable). 12 observations, ce n'est
   pas un échantillon, c'est une anecdote.
4. **Ablation des 5 composants** : lequel porte le signal ? Le rapport du 19/07 soupçonnait
   déjà le funding d'être contre-productif en long-only, et le §5 bis montre que l'intensité
   du score ne porte aucune information exploitable pour la taille.
5. **Si ça survit** : le signal macro devient un *modulateur d'exposition* (0 % / 50 % /
   100 % spot) plutôt qu'un déclencheur de trades — c'est là que sa lenteur est un atout.

## Reproduire

```powershell
# gestion : 22 politiques de sortie, puis 6 regles de taille
& C:\Users\jofar\venvs\arit\Scripts\python.exe research/macro_flip/gestion_sim.py --spot
& C:\Users\jofar\venvs\arit\Scripts\python.exe research/macro_flip/gestion_sim.py --spot --taille

# run principal (tout-perp, on garde la position en NEUTRE)
& C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe backtesting --strategy MacroFlip `
  -c research/macro_flip/config.macro_flip.json --timerange 20200101-20260713 `
  --timeframe-detail 5m --cache none --userdir user_data

# variante : sortie aussi sur NEUTRE
$env:ARIT_MACRO_FLAT_NEUTRE = "1"   # ... même commande

# benchmarks + Monte-Carlo + scénarios d'exécution
& C:\Users\jofar\venvs\arit\Scripts\python.exe research/macro_flip/analyse.py
```
