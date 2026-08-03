# Bloc « corrélation / sentiment du risque » dans la couche macro — PROPOSITION

**Date** : 2026-07-30 · **Demande de Jonas** : ajouter la corrélation comme indicateur pris en
compte dans la macro. **Statut** : proposition, **non fusionnée**.

## 0. Ce qui a été touché

| | |
|---|---|
| Produit (`arit_lib/`, `docs/`, `params.py`, `contracts.py`) | **rien** |
| Ajouté | `research/correlation_block/` (ce rapport, le module, ses tests) |
| Suite principale | **203 passed** après ajout — inchangée |
| Tests du bloc | **15 passed** (`pytest research/correlation_block -q`) |

Gouvernance PDR « on propose, on n'applique pas » : la fusion demande une décision signée.

## 1. Réponse courte

Oui — mais **pas comme 6ᵉ composant du score macro**. Le bloc sort un **véto booléen**,
journalisé à part, ablatable indépendamment. Les 5 composants existants ne sont pas touchés.

## 2. Pourquoi pas un terme additif

Le régime macro est une **somme** de 5 composants dans {−1, 0, +1}, seuils PORTEUR ≥ +2 /
HOSTILE ≤ −2 (`macro_regime.daily_regimes`). Un 6ᵉ terme poserait trois problèmes :

1. **Les seuils changeraient de sens en silence** : ±2 sur 5 devient ±2 sur 6. HOSTILE devient
   mécaniquement plus facile à atteindre — on recalibre les 5 composants existants sans les
   avoir touchés.
2. **Un score {−1, 0, +1} est symétrique par construction.** Il donnerait +1 quand le SPX monte.
   Or la mesure dit l'inverse : le BTC suit les actions **à la baisse, pas à la hausse**
   (Q2 2026 : S&P +15 % pendant que le BTC restait bloqué 61-73 k$). Le symétrique haussier est
   explicitement à ne pas coder.
3. **Motif déjà mesuré trois fois sur ce projet** — funding en composant de score (tuait les
   gagnants de bull market), sizing par la force du score macro (dégradait), pénalité continue
   de régime (détruisait la base saine, seul le véto HOSTILE binaire tenait). Un signal utile
   en **véto** détruit de la valeur en **terme additif**.

## 3. Deux pièges trouvés en lisant le code — les deux vérifiés

### 3.1 Le budget « stale » ne permet qu'une seule série 5/7 de plus

Séries FRED réellement téléchargées (`scripts/download_macro.py`), couverture vérifiée sur les
CSV présents :

| Série | ID FRED | Jours présents |
|---|---|---|
| `dxy` | `DTWEXBGS` | **jours ouvrés seulement** (lun-ven) |
| `taux` | `DFF` | 7/7 |

`MACRO_STALE_HOURS = 48` est calibré pour du 7/7. Un férié US collé à un week-end laisse
jusqu'à **96 h sans observation** → le composant tombe stale ~10 fois par an, pour un motif
purement calendaire. `dxy` subit déjà ça seul (compteur = 1). Ajouter le SPX → compteur = 2.

**`MACRO_STALE_FAILSAFE = 3`** → ajouter SPX **et** NDX ferait basculer le régime en **HOSTILE
à chaque férié US**, par fail-safe, sans que rien ne le signale.

→ Le bloc n'ajoute **que le SPX**, avec sa propre fenêtre de fraîcheur (`120 h`).

### 3.2 Calculer ρ sur un calendrier 7/7 le déflate d'environ un tiers

⚠️ **Correction d'un chiffre annoncé oralement** : j'avais avancé ~−15 % par un raisonnement
analytique (√(5/7) sur les rendements nuls injectés). C'est faux — l'effet réel est **environ
deux fois plus fort**, parce que les rendements nuls ne sont pas le seul mécanisme : il y a
aussi un **désalignement de fenêtre**. Le lundi, le BTC rend 1 jour quand le SPX rend le
week-end entier.

Mesuré par simulation (facteur de risque latent 7/7, SPX fermé le week-end pricant
samedi+dimanche+lundi à sa séance du lundi) :

| Fenêtre | ρ sessions | ρ calendaire | ratio |
|---|---|---|---|
| 30 j | 0,507 | 0,337 | **0,66** |
| 90 j | 0,514 | 0,345 | **0,67** |

Un couplage réel à 0,75 s'afficherait ~0,50 — **pile sur `MACRO_CORR_ARM_ABOVE`**. Le véto
clignoterait, ou ne s'armerait jamais. D'où le calcul **sur les sessions US uniquement**, puis
alignement.

Chiffre de simulation, pas de mesure sur données réelles : **à re-dériver sur l'historique
BTC/SPX avant fusion**.

## 4. Architecture

```
c6  risk-off actions   : le SPX clôture sous son plus-bas de clôture 20 j ouvrés -> véto longs
c7  régime de corrélation (MÉTA) : rho(BTC, SPX) décide si c6 est ARMÉ
       rho élevé  => le BTC se traite comme un actif de risque, le véto a du sens
       rho faible => le BTC suit ses propres drivers, bloquer sur le SPX = bruit
```

Le vrai apport de la corrélation n'est pas directionnel, il est **méta** : ρ ne dit pas où va le
BTC, il dit **si les indicateurs actions sont pertinents aujourd'hui**. C'est la seule
utilisation honnête d'un coefficient de corrélation — un signal sur la validité des autres
signaux, pas un signal de plus.

Hystérésis sur c7 : armement au-dessus de 0,50 (confirmé par ρ 90 j), désarmement seulement
sous 0,30, état conservé dans la bande morte. Sans ça, ρ oscillant autour d'un seuil unique
fait clignoter le véto d'un jour à l'autre.

## 5. Les quatre arbitrages de `evaluate()` — tous révisables

| Arbitrage | Choix | Raison |
|---|---|---|
| Armement | **`COUPLE` seul**, pas `TRANSITION` | TRANSITION est la bande morte = « on ne sait pas ». Armer sur l'incertitude rend le méta-gate inutile (véto actif presque tout le temps) et coûte des entrées valides. |
| Donnée périmée | **fail-open** | `regime_now` porte déjà un fail-safe global (≥ 3 stale → HOSTILE). Un second fail-safe sur une série 5/7 tirerait ~10×/an pour motif calendaire. Surtout : un filtre qui bloque sur donnée absente devient **infalsifiable en ablation** — impossible de séparer la valeur du filtre de celle du trou de données. |
| Raisons | chaînes **stables**, sans f-string | elles sont comptées telles quelles dans l'ablation. |
| Redondance | `BINDING` vs `REDUNDANT` | quand la macro est déjà HOSTILE, le véto n'ajoute rien ce jour-là. Compter les deux séparément donne l'apport **marginal** du filtre (= nombre de BINDING), seule quantité décisionnelle. Sans ça, l'ablation surestime le filtre de tous ses blocages non-liants. |

⚠️ **Le fail-open est la décision la plus discutable des quatre.** L'alternative fail-safe se
défend si la priorité est la sécurité plutôt que la mesurabilité. À trancher explicitement.

## 6. Écarté volontairement

| Candidat | Motif |
|---|---|
| **NDX** | consomme le dernier cran du fail-safe stale (§3.1). |
| **DXY en corrélation** | déjà composant c1, et la relation BTC/DXY a cassé le 10/01/2024 (test de Chow, p = 0,0000). La doublonner compterait deux fois une relation morte. |
| **Or / ratio BTC-or** | profil hebdo→annuel. Même verdict que M2 et MVRV : variable d'état, jamais outil de timing. |
| **USDJPY / carry trade** | tail risk déclenché par les **communications** BoJ/MoF, pas par un niveau. Famille circuit-breaker, pas famille corrélation. |
| **Symétrique haussier de c6** | la corrélation coûte dans un sens et ne rapporte pas dans l'autre. |

## 7. Reste à faire avant fusion

1. Déplacer les 7 constantes dans `params.py`, bloc `06.2 c6/c7` (interdit n°4).
2. `contracts.py` : `EQUITY_VETO_COL` + clé journal — **docs/11 §11.3 d'abord** (règle 3).
3. `scripts/download_macro.py` : `"sp500": lambda: dl_fred("SP500", "sp500")` — même parser
   que `dxy`, zéro code neuf.
   ⚠️ FRED `SP500` a une **fenêtre glissante de 10 ans** : couvre 2018-2026 aujourd'hui, mais
   un re-run dans 2 ans perdra le début du backtest. Historique stable : `^GSPC` via Stooq.
4. `docs/06_vetos_data.md` §6.2 : documenter c6/c7 **hors somme**.
5. Déplacer les tests dans `tests/test_macro_regime.py` (règle 7 `arit_lib`).
6. Re-dériver la déflation de ρ (§3.2) sur les vraies séries.

## 8. Le point qui conditionne tout

**Ce véto ne peut pas être mesuré maintenant.** Sur le substrat actuel à espérance nulle,
**tout filtre qui réduit l'exposition paraît positif par construction** — et c'est
probablement ce qu'est déjà le résultat « véto HOSTILE : −19,1 % → −7,0 %, DD 24,9 % →
10,6 % », présenté ailleurs comme une validation.

Ce bloc appartient au **chantier 1b**, mesuré contre A' une fois la géométrie du stop réparée.
L'implémenter maintenant est utile ; conclure quoi que ce soit de son backtest maintenant ne
l'est pas.

## Artefacts et reproduction

```
research/correlation_block/macro_correlation_bloc.py    le module proposé
research/correlation_block/test_correlation_bloc.py     15 tests
research/correlation_block/RAPPORT.md                   ce fichier

& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest research/correlation_block -q
& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q      # 203 passed, produit intact
```

## Hygiène (rappel, non traité ici)

Le webhook Discord exposé en clair signalé dans `research/edge_2026-07/RAPPORT.md` §6 est
**toujours à régénérer** avant le canari.
