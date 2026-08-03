# Pistes d'amélioration ARIT — données, processus, mathématiques

**Date** : 2026-07-31 · **Statut** : proposition, **rien n'a été appliqué** (gouvernance PDR) ·
**Méthode** : 6 agents en parallèle (inventaire repo · vault Obsidian · données macro · features
techniques · processus/outillage · méthodes stochastiques), puis consolidation et **vérification
manuelle des affirmations qui portent une décision**.

> Les agents ne sont pas fiables par défaut. Chaque chiffre de ce rapport marqué **✔ vérifié** a
> été recalculé à la main sur les artefacts du repo. Un chiffre marqué **~ à vérifier** vient d'un
> agent et n'a pas encore été reproduit. Une affirmation d'agent a déjà été corrigée ici (§7.1).

**Marquage des pistes** : 🆕 nouveau · 📌 approfondissement d'un item déjà au backlog · ♻️ déjà
testé et réfuté (rappelé pour éviter qu'on y revienne).

---

## 0. Résumé exécutif — les 8 conclusions qui changent une décision

1. **ARIT n'a jamais eu de modèle nul.** Avec TP à +1,5R et SL à −1R, la probabilité de toucher le
   TP en premier sous marche aléatoire vaut exactement `b/(a+b) = 1/2,5 = 40,0 %`. ARIT mesure
   **40,7 %**. Le verdict « edge nul, PF 1,00, p = 0,99 » de 8,5 ans de backtest était **dérivable
   en une ligne d'algèbre sans lancer un seul run**. Corrigé de la dérive réelle du BTC, le nul
   monte à 42,2 % : l'edge d'entrée n'est pas nul, il est **légèrement négatif**.

2. **Mais le même modèle nul sauve le chantier prioritaire.** Le test « demi-stop » (TP +6 %,
   SL −2 %) a un nul à 26,4 % et mesure **33,3 %**, soit z = 1,74 (p unilatéral = 0,041).
   **C'est la seule déviation positive au hasard dans tout le diagnostic de juillet.** Le ×20
   d'espérance n'est donc pas un artefact de redéfinition du R — il survit au modèle nul, de
   justesse.

3. **La recherche de juillet a dépassé son budget statistique.** ~40 politiques de gestion ont été
   comparées sur les mêmes 123 épisodes. L'espérance du *maximum* de 40 essais sous hypothèse nulle
   vaut SR ≈ 0,161 ; la meilleure politique trouvée affiche SR ≈ 0,07. **Le « gagnant » est deux
   fois en dessous de ce que le pur bruit de sélection produit.** Le dossier « chercher une
   meilleure politique de sortie » est mathématiquement clos, pas seulement empiriquement.

4. **Le sizing est au-delà du point de croissance nulle.** Kelly sur l'espérance brute :
   `f* = E[R]/E[R²] = 1,16 %`. Sur l'espérance bayésienne rétrécie : **0,46 %**. Or `params.py`
   impose un plancher de 1 % et un cap de 3 % — soit **2,6 × Kelly**, au-delà de `2f* = 2,32 %` où
   la croissance logarithmique s'annule. **ARIT n'a aucun régime de risque autorisé qui soit
   sous-Kelly.** C'est le seul défaut qui coûte de l'argent dès le premier jour de dry-run.

5. **Le bot jette gratuitement le tiers de ses données.** ✔ vérifié : les feathers freqtrade ont
   6 colonnes (`date, open, high, low, close, volume`). Les klines Binance en ont **12** — dont le
   **volume acheteur agressif** et le **nombre de trades**, dans le même appel, gratuits, depuis
   2017-08. ARIT trade depuis 8,5 ans sans jamais savoir *qui* casse la résistance.

6. **Le vrai chiffre du drawdown n'est pas sa profondeur, c'est sa durée.** ✔ vérifié : le
   drawdown maximal du produit B dure **2 812 jours — 7,7 ans sous l'eau**. Aucun rapport ne l'a
   jamais mentionné. Le gate `docs/09 §9.2` ne contraint que la profondeur.

7. **Trois slots ne sont pas trois paris.** BTC/ETH/SOL/BNB corrèlent à > 0,8 et leur dépendance
   de queue explose en krach. `MAX_OPEN_TRADES = 3` vaut ≈ **1,2 pari indépendant**. Pire :
   `CB_DAY_EQUITY_DROP_PCT = 6 %` est **exactement égal** à `RESIDUAL_RISK_MAX_PCT = 6 %` — le
   circuit breaker journalier est calibré pour se déclencher précisément quand le budget de risque
   se matérialise, c'est-à-dire lors d'une mauvaise journée ordinaire, pas d'un événement rare.

8. **Deux bombes à retardement silencieuses.** (a) La série FRED `SP500` utilisée par le bloc
   corrélation ne conserve que **10 ans glissants** : dans ~13 mois elle commencera après le début
   du backtest et le module se dégradera **sans qu'aucun test n'échoue**. (b) Avec
   `MACRO_STALE_FAILSAFE = 3`, ajouter deux séries en jours ouvrés (HY OAS, VIX) suffit à faire
   basculer le régime en **HOSTILE à chaque férié américain**, silencieusement.

---

## 1. Ce qui invalide ou recadre les conclusions existantes

Cette section passe avant les pistes : plusieurs chantiers envisagés n'ont plus de sens une fois
ces corrections appliquées.

### 1.1 Le modèle nul de franchissement de barrière 🆕

Pour un log-prix `X_t = μt + σW_t`, barrière haute `+a`, barrière basse `−b` :

```
p_null = (1 − e^(θb)) / (e^(−θa) − e^(θb))   avec θ = 2μ/σ²
p_null → b/(a+b) quand μ → 0
```

| Géométrie | Nul sans dérive | Nul avec dérive BTC | Observé | Écart |
|---|---|---|---|---|
| TP +1,5R / SL −1R (ARIT actuel) | 40,0 % | 42,2 % | 40,7 % | **−1,5 pt** |
| TP +6 % / SL −2 % (demi-stop) | 26,4 % | — | 33,3 % | **+6,9 pt** (z = 1,74) |

Conséquence de méthode : **l'edge doit se définir comme `Δp = p_obs − p_null(σ_t, μ)`, pas comme un
PnL**. Le test de permutation actuel randomise le *signe* du signal, jamais sa *géométrie* — il ne
pouvait donc pas voir que 40,7 % était le résultat attendu du hasard.

Bénéfice décisif : `p_null` s'estime sur **70 915 bougies 4h** (✔ vérifié, 4 paires cumulées), pas
sur 128 trades. Facteur d'échantillon ≈ 550×.

**Effort S** (~40 lignes, `numpy`/`scipy` déjà installés). **Compatible** avec les 7 interdits.

### 1.2 Puissance statistique — ce qui est atteignable et ce qui ne l'est pas 🆕

`MDE = 2,487 × σ_R / √n` (α = 0,05, puissance 80 %). Avec σ_R = 1,23 :

| n | Effet minimal détectable | Lecture |
|---|---|---|
| 12 (MacroFlip) | ±0,88 R | inexploitable |
| **128 (A pur)** | **+0,270 R** | seuil de détection |
| 128 corrigé du chevauchement (n_eff ≈ 80) | **+0,34 R** | le vrai seuil |
| 936 | +0,100 R | un edge modeste devient visible |

**ARIT ne peut prouver qu'un edge de classe mondiale.** Un edge réel mais modeste lui est
structurellement invisible : il faudrait ~2 400 ans au rythme actuel. Deux corollaires opérationnels :
le chantier demi-stop demande n ≈ 198 (**à portée**) ; le raffinement du score de conviction ne l'est
pas ; passer de 4 à 20 paires divise le MDE par 2,2.

### 1.3 Budget de tests et Sharpe dégonflé 🆕

`E[max_N SR] ≈ σ_SR × [(1−γ)·z_{1−1/N} + γ·z_{1−1/(Ne)}]`, γ = 0,5772.

Avec N ≈ 40 essais (12 politiques R-space + 22 politiques de sortie + 6 règles de taille + 3
multiplicateurs de stop) et σ_SR = 1/√123 = 0,090 → **E[max SR] = 0,161**. La meilleure politique
(TP1 + giveback, +0,26R) affiche SR ≈ 0,06-0,09.

Ce n'est pas « fragile parce que ça tient à un trade » : c'est **statistiquement pire que rien**.
Même logique pour les 3 politiques MacroFlip « au-dessus de HOLD » (+7, +6, +3 points sur 12
observations) : ordre de grandeur exact du maximum de bruit.

**Discipline à instaurer** : un compteur `N` cumulatif, journalisé, jamais remis à zéro entre
campagnes, et une p-value corrigée (Benjamini-Hochberg, ~15 lignes) à côté de chaque p brute.

### 1.4 Kelly, ergodicité et le sizing actuel 🆕

| Quantité | Valeur | Comparaison à `params.py` |
|---|---|---|
| `f*` sur espérance brute (E[R] = 0,0175) | **1,16 %** | plancher `RISK_BASE_PCT` = 1 % |
| `f*` sur espérance bayésienne rétrécie | **0,46 %** | **sous le plancher** |
| Point de croissance nulle `2f*` | 2,32 % | cap `RISK_CAP_AFTER_PCT` = **3 %** |

Le cap à 3 % est à 2,6 × Kelly, **au-delà du point où la croissance logarithmique s'annule** :
mathématiquement destructeur *même si l'edge était réel*. Et la formule `1 % + n(cap − 1 %)` fait
croître le risque avec la *conviction*, quantité qui n'est reliée à aucune espérance mesurée —
avec ~25 trades par bande de conviction, le MDE par bande est de **+0,61 R** : la pente n'est pas
estimable, donc pas justifiable. **Proposition : risque constant tant que n < 500.**

### 1.5 Le circuit breaker séquentiel se déclenche pour rien 🆕

`CB_SEQ_CONSECUTIVE = 2` pertes ≤ −0,8R. À win-rate 41 %, `P(2 pertes consécutives) = 0,59² =
34,8 %` : **une pause tous les ~3 trades en pur bruit**. Le CB actuel est un CUSUM dégénéré à seuil
2 sans calibration de son temps moyen avant fausse alarme. Un CUSUM calibré (~20 lignes) donnerait
le même service avec un taux de fausse alarme choisi.

### 1.6 Drawdown : la profondeur ment moins que la durée ✔ vérifié

`wallet_stats` et `*_wallet.feather` sont **déjà dans chaque zip** de backtest et personne ne les
lit. Mesures faites à la main sur les deux runs du diagnostic :

| Run | Trades | DD trades clôturés | DD marqué au marché | **Durée du DD** |
|---|---|---|---|---|
| A pur | 128 | 9,78 % | 10,51 % | 949 jours |
| B produit | 187 | 23,32 % | 23,81 % | **2 812 jours (7,7 ans)** |

⚠️ **Correction d'un agent** : l'écart profondeur-clôturé vs marqué-au-marché est de 0,5-0,7 point
ici, pas d'un facteur 4 comme annoncé. Le gouffre n'apparaît que sur des runs à positions longuement
ouvertes — donc sur la branche macro (MacroFlip : 24,3 % annoncés contre 49,2 % réels sur des
positions de 729 jours), pas sur la campagne A/B. **La conclusion utile est ailleurs** : le gate
`docs/09 §9.2` ne contraint que la profondeur, alors que le chiffre qui décide de la tenue d'un
humain est la durée. Un produit qui passe 7,7 ans sous son plus haut est intenable, quel que soit
son PF.

Disponible gratuitement dans les mêmes zips et jamais lu : `sharpe`, `sortino`, `calmar`,
`drawdown_start/end`, `max_drawdown_abs`.

### 1.7 La diversification des 4 paires est cosmétique 🆕

Copule de Student : `λ_L = 2·t_{ν+1}(−√((ν+1)(1−ρ)/(1+ρ)))`. Avec ρ > 0,8 entre les 4 paires et une
dépendance de queue élevée, **3 slots ≈ 1,2 pari indépendant**. La coïncidence
`CB_DAY_EQUITY_DROP_PCT = RESIDUAL_RISK_MAX_PCT = 6 %` signifie que le circuit breaker journalier se
déclenche exactement quand le budget de risque se matérialise entièrement — un événement rare sous
indépendance, **le mode normal d'une mauvaise journée** sous dépendance de queue.

Coût de la mesure : ~60 lignes, `scipy.stats.multivariate_t`, sur 3 100 rendements journaliers.

### 1.8 Deux dégradations silencieuses à corriger avant toute fusion ~ à vérifier

- **FRED `SP500` = fenêtre glissante de 10 ans.** Le module `research/correlation_block/` l'utilise.
  Le backtest démarre en 2017-08 ; la série sert aujourd'hui depuis 2016-08. Dans ~13 mois, elle
  commencera **après** le début du backtest et le bloc se dégradera sans qu'aucun test n'échoue.
  → basculer sur `NASDAQ100` (FRED, depuis 1986, et meilleur comparable du BTC).
- **`MACRO_STALE_FAILSAFE = 3` sature.** DXY est déjà en jours ouvrés. Ajouter HY OAS puis VIX porte
  le compteur à 3 séries simultanément périmées un férié américain collé à un week-end →
  **HOSTILE automatique par fail-safe**, silencieusement. Toute nouvelle série 5/7 doit embarquer sa
  propre fenêtre de fraîcheur à 120 h.

### 1.9 Deux gates inertes ♻️ (déjà connu, jamais corrigé)

- **Gate `news_window`** : `FINNHUB_KEY` est vide → le calendrier économique ne fonctionne pas. Le
  fail-safe (« absent ⇒ échec ») rend le gate soit bloquant, soit inopérant selon la présence de
  `macro_state.json`. À trancher explicitement.
- **Gate `spread`** : `spread_frac = None` en permanence → gate journalisé mais **inerte** depuis
  l'origine. Le service `spread_state.py` a été validé par Jonas, jamais codé.

---

## 2. Données macro non exploitées

Sources testées en direct le 2026-07-31 par l'agent (~ à re-vérifier avant tout code).

| # | Piste | Effort | Historique | Risque principal | Verdict |
|---|---|---|---|---|---|
| M1 | **Basis spot-perp** (`premiumIndexKlines`) 🆕 | S | 2019-09+ | aucun (donnée immuable) | 🟢 |
| M2 | **Net liquidity** WALCL − RRP − TGA 🆕 | M | 2003+ | calendrier de publication | 🟢 |
| M3 | **HY OAS** (`BAMLH0A0HYM2`) 🆕 | S | 1996+ | 2ᵉ série 5/7 (§1.8) | 🟢 |
| M4 | **Coinbase premium** 📌 | S/M | 2018+ | rate-limit 300 bougies | 🟢 |
| M5 | **MVRV** (Coin Metrics) 🆕 | S | 2010+ | effet porté par 2017+2021 | 🟢 |
| M6 | **DVOL Deribit** (vol implicite) 🆕 | M | 2021-03+ | interdit n°2 (SL) | 🟢/🟡 |
| M7 | **Open interest** (dump `metrics`) 📌 | M | 2020-09+ | ampute 3 ans | 🟡 |
| M8 | Netflow exchange (CM) 🆕 | S | 2015+ | **ré-étiquetage rétroactif** | 🟡 |
| M9 | VIX / VIX3M 🆕 | S | 2007+ | 3ᵉ série 5/7 | 🟡 |
| M10 | Stablecoins par chaîne 📌 | S | 2017-11+ | historique recalculé | 🟡 |
| M11 | Taker / top-trader ratio 🆕 | S* | 2020-09+ | population non homogène | 🟡 |
| M12 | Hashrate / difficulté 🆕 | S | — | **répond à rien** | 🔴 |

\* effort marginal nul si M7 est faite.

**M1 — Basis spot-perp.** Le funding que consomme ARIT est la *facture ex-post* du portage ; le
premium index en est le *devis ex-ante*. Sur une stratégie dont la valeur démontrée est la **durée de
détention**, et dont 86 % du profit théorique a été mangé par le funding, connaître le prix ex-ante
du carry n'est pas un raffinement, c'est la variable de décision centrale.
Source : `data.binance.vision/data/futures/um/monthly/premiumIndexKlines/`, ZIP mensuels, immuables.
Test : sur les 729 jours de détention MacroFlip, sortir si basis annualisé 7 j > X avec
X ∈ {8, 12, 15, 20} **fixés a priori**. Rejet si le PnL net de funding ne récupère pas ≥ 30 % du
carry payé, ou si moins de 5 sorties se déclenchent.

**M2 — Net liquidity.** `DFF` en variation 60 j est une série en escalier qui bouge 8 fois par an :
information déjà dans les prix depuis des mois. NetLiq bouge chaque semaine avec une persistance de
plusieurs mois — le profil exact d'un signal dont la valeur est la durée. **C'est un remplacement de
`DFF`, pas un ajout** (ajouter un 6ᵉ terme recalibre silencieusement les seuils ±2 sur 5 — piège
déjà documenté dans `research/correlation_block/`).
⚠️ **Le décalage global de +1 jour est insuffisant** : WALCL daté du mercredi paraît le jeudi
16h30 ET, le TGA du jour J paraît le lendemain. Décalage dédié **+2 jours ouvrés** obligatoire,
couvert par un test.

**M5 — MVRV.** Aucun des 5 composants macro actuels n'est un signal de **valorisation** : 2 de
politique monétaire, 1 de liquidité crypto, 1 de positionnement, 1 de sentiment. MVRV est
l'archétype du signal « la valeur est la durée » (horizon 6-18 mois). Indisponible pour SOL/BNB en
tier communautaire → régime BTC-driven appliqué aux 4 paires, défendable mais à énoncer.

**Écarté avec preuve** (ne pas y revenir) : liquidations historiques (**Binance ne les diffuse
plus** — le bucket S3 n'a aucun dataset de liquidations, donc « entrée post-cascade » du backlog
n'est **pas backtestable proprement**) · skew et GEX crypto (API Deribit ne sert que les
instruments récemment expirés ; reconstruire 8 ans exige Tardis/Amberdata, payants ; et sur crypto
l'hypothèse de signe du dealer est arbitraire) · futures CME (payant, et redondant avec M1) ·
Farside pour les flux ETF (Cloudflare + **640 observations, un seul cycle** → aucun walk-forward n'y
survit ; M4 est le proxy honnête sur 8 ans) · Stooq (cassé en 2026, remplacer par FRED `NASDAQ100`)
· NFCI (**révisé rétroactivement par construction** → look-ahead structurel) · MOVE (propriétaire).

---

## 3. Données techniques non exploitées

**Le constat qui domine tout le reste** ✔ vérifié : les feathers freqtrade ont 6 colonnes, les
klines Binance en ont 12.

```
open_time, open, high, low, close, volume, close_time, quote_asset_volume,
number_of_trades, taker_buy_base_volume, taker_buy_quote_volume, ignore
                 ^^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^ jetées par freqtrade
```

Volumétrie mesurée : **~5 Mo pour tout l'historique 4h des 4 paires**, 17 Mo en 1h, 200 Mo en 5m.
Un bot qui jette 3 colonnes sur 12 fournies gratuitement par son exchange est un problème
indépendamment de toute recherche d'edge.

| # | Piste | Données | Effort | Effet sur le nb de trades | Verdict |
|---|---|---|---|---|---|
| T1 | **Audit d'information des 5 scores** 🆕 | sur disque | M | ↔ / ↑ | 🟢🟢 |
| T2 | **Déséquilibre taker** (`taker_buy/volume`) 🆕 | 5 Mo | S/M | ↔ | 🟢 |
| T3 | **Compression de volatilité Yang-Zhang** 🆕 | sur disque | S | ↓↓ | 🟢 |
| T4 | **Efficience de trajet 5m** 🆕 | sur disque | S | ↔ | 🟢 |
| T5 | **VWAP ancré au BOS + entrée au retest** 🆕 | sur disque | M | ↓ | 🟢 |
| T6 | **Liquidity sweep pré-cassure** 🆕 | sur disque | M | **↑** | 🟢 |
| T7 | `number_of_trades` / taille moyenne d'ordre 🆕 | idem T2 | S | ↔ | 🟢 |
| T8 | **Normalisation horaire du volume et de l'ATR** 🆕 | sur disque | S | ↔ | 🟢 |
| T9 | Force relative transversale + dispersion 🆕 | sur disque | M | ↓ | 🟡 |
| T10 | Volume profile / VPOC / `vol_ahead` 🆕 | sur disque | L | ↔ / ↑ | 🟡 |
| T11 | Extension EMA200-ATR, position dans le range, 1w 🆕 | sur disque | S | ↔ | 🟡 |
| T12 | CVD + divergence / absorption 🆕 | idem T2 | M | ↓ | 🟡 |
| T13 | Open interest 5 min 📌 | 100 Mo | M | ↓↓ + perd 2017-20 | 🟡 |
| T14 | FVG + déplacement continu 🆕 | sur disque | S | **↑** | 🟡 |
| T15 | Hurst / ratio de variance / demi-vie | sur disque | M | ↓↓↓ | 🔴 |

**T1 — l'audit d'information, à faire avant tout le reste.** `conviction = 0,40·s_structure +
0,20·s_momentum + 0,15·s_sr + 0,15·s_patterns + 0,10·s_volume`, poids figés par décret PDR,
**jamais mesurés**. Trois pathologies plausibles et testables :
- les paliers `{0 ; 0,3 ; 0,5 ; 0,7 ; 1,0}` détruisent de l'information (`s_sr` vaut 1,0 que le RR
  soit 2,0 ou 12 ; `s_volume` saute de 0 à 0,5 entre 0,99× et 1,01× la SMA) ;
- `s_structure` et `s_momentum` partagent l'ADX/EMA → colinéarité, donc moins de degrés de liberté
  que 5 termes ne le suggèrent ;
- 5 scores × 5 paliers = 3 125 combinaisons pour 128 observations : massivement sur-paramétré.

Critère de rejet d'un score : `|IC| < 0,04` sur les 70 915 barres 4h, **ou** signe non constant sur
les 3 sous-périodes, **ou** signe non constant sur ≥ 2 des 4 paires. Prédiction posée d'avance par
l'agent : `s_patterns` (0,15) et `s_volume` (0,10) — **25 % du poids** — sont probablement du bruit.

**T8 — un biais de mesure, pas une idée d'edge.** `s_volume` compare le volume à la SMA20 des
20 dernières bougies 4h, soit un mélange de 3,3 jours incluant week-end et heures asiatiques.
Conséquence mécanique : une cassure le samedi est presque toujours « faible volume », une cassure
le mardi 14h UTC presque toujours « fort volume ». **`s_volume` mesure en partie l'heure de la
journée.** Même défaut sur `BOS_DISPLACEMENT_ATR = 1,0 × ATR`. Distinct du « filtre horaire » déjà
au backlog : ici on ne filtre rien, on dé-biaise.

**T5 — la seule piste qui répare le RR sans toucher au stop.** ARIT achète la clôture 4h de
cassure, c'est-à-dire le plus mauvais prix de la séquence — ce qui *cause* mécaniquement un SL
structurel lointain. Entrer au retest du VWAP ancré rapproche l'entrée du stop au lieu d'éloigner
le stop de l'entrée. Critères de passage simultanés : RR médian +30 % **et** taux de non-remplissage
< 40 %, avec mesure obligatoire du rendement des non-remplis (s'il est très supérieur, le retest
sélectionne les mauvais trades et la piste meurt).

**Écarté avec mesure** : aggTrades tick (**567 Mo zippés pour un seul mois BTC** → > 100 Go pour
l'historique complet ; les klines 1m donnent 90 % de l'information utile pour 930 Mo) · carnet L2
(historique trop court, horizon secondes sans rapport avec des décisions 4h) · TPO lettré (capturé
intégralement par T10 sur un marché 24/7 sans séance) · entropie (redondante avec T3/T15 pour plus
de degrés de liberté).

**T15 écarté pour une raison instructive** : l'estimateur R/S du Hurst a un **biais haussier
documenté produisant H ≈ 0,60 sur du bruit pur** — un seuil naïf « H > 0,55 » laisserait passer
100 % des barres en donnant l'illusion d'un filtre. Et sur 500 barres, H change si lentement que
l'échantillon effectif tombe à ~30 régimes indépendants en 8,5 ans : **non falsifiable ici**.

---

## 4. Processus et outillage non utilisés

| # | Piste | Effort | Coût machine | Corrige | Verdict |
|---|---|---|---|---|---|
| P1 | **`wallet_stats` / `*_wallet.feather`** ✔ | S | nul | DD et durée mal mesurés | 🟢🟢 |
| P2 | **`--export signals` + `--rejected-signals`** 🆕 | S/M | faible | **échantillon (N↑)** | 🟢🟢 |
| P3 | **Hold-out scellé** 2025-01 → 2026-07 🆕 | S | négatif | surapprentissage | 🟢🟢 |
| P4 | **Walk-forward ancré** (boucle `--timerange`) 📌 | M | élevé | jamais fait | 🟢 |
| P5 | **Budget de tests + Benjamini-Hochberg + DSR** 🆕 | S→M | faible | §1.3 | 🟢 |
| P6 | **`EXPERIMENTS.jsonl` + préenregistrement** 🆕 | S | nul | p-hacking | 🟢 |
| P7 | **`--fee` balayé + point mort en bps** 🆕 | S/M | ×3 runs | conclusions fausses | 🟢 |
| P8 | `--strategy-list` (A/B en un run) 🆕 | S | −40 % de temps | lenteur | 🟢 |
| P9 | `--breakdown year month weekday` 🆕 | S | nul | sous-périodes à la main | 🟢 |
| P10 | Lock des versions + `data_manifest.json` 🆕 | S | nul | reproductibilité | 🟢 |
| P11 | Bootstrap par blocs stationnaire 🆕 | M | faible | p-values trop optimistes | 🟡→🟢 |
| P12 | Purged K-fold + embargo, CPCV, PBO 🆕 | M/L | très élevé | surapprentissage | 🟡 |
| P13 | Ulcer Index, Calmar glissant, risque de ruine 🆕 | S/M | faible | risque mal mesuré | 🟡 |
| P14 | Surface de paramètres, bruit, décalage +1 🆕 | M | moyen | robustesse | 🟡 |
| P15 | Protections freqtrade ♻️📌 | M | ralentit | churn | 🟡 |
| P16 | Golden run de non-régression 🆕 | M | faible | **bugs silencieux** | 🟡 |
| P17 | FreqAI ♻️ (déjà `docs/10`) | L | élevé | rien aujourd'hui | 🔴 |

**P2 — le levier n°1 sur l'échantillon, sans toucher à la stratégie.** `--export signals` produit
`_rejected.pkl` ; `backtesting-analysis --rejected-signals --analysis-groups 0 1 2 5` sort la
**population complète des signaux**, pas seulement les 128 que les 3 slots ont laissé passer.
`analysis/README.md` reconnaît explicitement ce biais de saturation. Critère de passage : **N ≥ 400
signaux évaluables**. Critère d'abandon : si N < 250 après jointure avec les `ev_gate_check` du
journal, l'edge d'entrée technique est **définitivement non testable** sur cet historique.

**P3 — le hold-out, seule protection réelle.** Depuis juillet, A/B, A/B corrigé, 12 politiques,
ablations, MacroFlip, 4 scénarios et 3 géométries de stop ont tous tourné sur les **mêmes 8,5 ans**.
Aucune p-value calculée sur cette période n'est encore interprétable. Retirer physiquement les
feathers ≥ 2025-01-01 (méthode déjà pratiquée pour neutraliser la macro). ⚠️ 18 mois ≈ 25 trades :
**le hold-out ne pourra jamais confirmer un edge, seulement le réfuter** — écrire ce critère
d'avance.

**P16 — ce qui aurait attrapé le bug à 8,5 ans.** Le contrôle A a tourné **sans stop** pendant toute
une campagne, invalidant le « +40 % » du 11/07, et n'a été détecté que 8 jours plus tard par
relecture humaine. Les 230 tests couvrent les modules unitairement ; **rien ne teste le comportement
composé**. Un golden run figé (timerange court, ≥ 5 trades, KPI commités) l'aurait vu le jour même.

**Corrections factuelles sur l'outillage** : `freqtrade edge` **n'existe plus** (déprécié 2023.9,
retiré 2025.6) · les protections ne sont **plus en config** depuis 2024.10, elles vivent dans
l'attribut `protections` de la stratégie · `--backtest-filename` est déprécié pour `backtesting` ·
`hyperopt` est **inutilisable dans le venv** (Optuna absent) et `plot-*` aussi (plotly absent).

**FreqAI — clarification doctrinale** : l'interdit n°1 dit « aucun **LLM** au runtime ». Un
gradient boosting n'est pas un LLM, et `docs/README.md` prévoit explicitement FreqAI en V2. Le
conflit réel est ailleurs : FreqAI **ré-entraîne en continu** par défaut, alors que la doctrine
impose « modèles figés ». Et avec 128 trades, un modèle à forte capacité apprendra le bruit avec
une efficacité redoutable. → 🔴 maintenant, 🟡 après un edge établi.

---

## 5. Méthodes mathématiques absentes

Critère de tri appliqué : **une méthode est faisable si sa vraisemblance s'écrit en espace-bougie,
condamnée si elle s'écrit en espace-trade.**

| Espace | Échantillon disponible | Paramètres estimables |
|---|---|---|
| trades A pur | 128 (123 épisodes) | 1, très mal |
| trades MacroFlip | 12 | aucun |
| **bougies 4h × 4 paires** | **70 915** ✔ | 10 à 50 |
| **bougies 1h × 4 paires** | **283 448** ✔ | idem, plus fin |
| jours macro | ~2 400 | 5 à 15 |

| # | Méthode | Paramètres | Faisable ? | Effort | Verdict |
|---|---|---|---|---|---|
| S1 | **Franchissement de barrière / premier passage** 🆕 | 0 | ✓ bougies | S | 🟢🟢 |
| S2 | **Puissance statistique / MDE** 🆕 | 0 | ✓ formule | S | 🟢🟢 |
| S3 | **Bootstrap stationnaire + Reality Check + DSR** 🆕 | 1+1 | ✓ n ≈ 100 | M | 🟢 |
| S4 | **Bayes sur l'espérance + rétrécissement** 🆕 | 1 | ✓ dès n = 10 | S | 🟢 |
| S5 | **Volatilité conditionnelle EWMA → HAR-RV** 🆕 | 1 / 4 | ✓✓ 283 448 obs | S/M | 🟢 |
| S6 | **Kelly + ruine + ergodicité** 🆕 | 0 | ✓ | S | 🟢 |
| S7 | **Walk-forward purgé + embargo** 📌 | 0 estimé | ✓ jours · ✗ trades | M | 🟢 |
| S8 | Ornstein-Uhlenbeck / demi-vie / time-stop 🆕 | 3 | ✓ | S | 🟡 |
| S9 | **Survie (Kaplan-Meier, hasard h(t))** 🆕 | 0 | ✓ n = 128 · ✗ n = 12 | S/M | 🟡 |
| S10 | Triple barrier + méta-étiquetage 🆕 | 3 + ≤5 | ~ 6 000 événements | M | 🟡 |
| S11 | Barres volume / dollar 🆕 | 1 | ✓ | S | 🟡 |
| S12 | HMM / Markov switching ♻️ (`docs/10`) | 12 à 48 | ✓ 1 550 obs/param | M/L | 🟡 |
| S13 | CUSUM + BOCPD 🆕 | 2 / 3-4 | ✓ bougies · ✗ 128 R | S/M | 🟡 |
| S14 | **Copules / dépendance de queue** 🆕 | 2 à 7 | ✓✓ | M | 🟡 |
| S15 | EVT (POT / Pareto généralisée) 🆕 | 2 + seuil | ✓ 745 excès | S | 🟡 |
| S16 | Hawkes (auto-excitation) 🆕 | 3 à 36 | ✗ trades · ✓ événements 5m | M | 🟡/🔴 |

**Aucune des 7 méthodes prioritaires ne demande une nouvelle dépendance** : `numpy`, `pandas`,
`scipy` déjà installés suffisent. **Aucune n'utilise le GPU** — et c'est un test de sanité utile :
toute méthode qui aurait besoin de la RTX 5060 est, par construction, trop paramétrée pour ce jeu
de données.

**S5 — la volatilité conditionnelle rend le R comparable.** Le SL structurel a deux défauts : il est
*rétrospectif* (dernier HL confirmé) et sa distance est *incontrôlée* — elle varie d'un facteur 5
selon le setup. **Donc le R n'est pas une unité homogène entre trades**, ce qui invalide
partiellement toutes les statistiques agrégées du diagnostic (le σ_R = 1,23 utilisé partout suppose
une géométrie homogène). Ordre recommandé : EWMA (1 paramètre, 25 lignes) puis HAR-RV (4
paramètres, MCO) ; n'ajouter `arch`/GARCH que si HAR ne suffit pas — la littérature donne HAR ≥
GARCH sur la prévision de volatilité réalisée.

**S9 — la formalisation exacte de la découverte MacroFlip.** « La valeur du signal macro EST la
durée de détention » est une phrase littéraire ; `S(t)` et le hasard `h(t) = f(t)/S(t)` en sont la
version mathématique. Si `h(t)` est **décroissant**, toute règle de sortie temporelle détruit de la
valeur — ce que les 22 politiques ont montré empiriquement sans le nommer. C'est aussi le bon
traitement de la censure du `force_exit` de fin de backtest, comptée jusqu'ici comme un trade normal.

**Écarté définitivement** (pas « pour plus tard ») : arrêt optimal / programmation dynamique sur
l'espace R (**480 cellules pour 123 épisodes = 0,26 observation par cellule**, et c'est de l'hyperopt
de règles sous un nom mathématique → conflit frontal avec l'interdit n°5) · filtre de Kalman (un
modèle de niveau local **est** une EMA adaptative, ARIT en a déjà deux) · GARCH multivarié
DCC/BEKK (20-30 paramètres, la copule donne 90 % pour 10 %) · volatilité rugueuse et Heston/Bates
(calibration sur surface d'options qu'ARIT n'a pas) · **RL, LSTM, transformers, gradient boosting à
forte capacité** (un RL de politique de sortie demande 10⁵-10⁶ épisodes, ARIT en a 123 — *la
contrainte n'est pas la puissance de calcul, c'est l'information : 8,5 ans de crypto contiennent
peut-être 4 à 6 régimes indépendants, aucun GPU n'en fabriquera un septième*).

---

## 6. La question mathématique centrale

> **Quelle est la probabilité que le prix touche +1,5R avant −1R sous une diffusion nulle calibrée
> sur la volatilité conditionnelle du moment — et de combien mon signal la déplace-t-il ?**
>
> Soit : définir l'edge comme **`Δp = p_obs − p_null(σ_t, μ)`**, et non comme un PnL.

Pourquoi c'est *la* question :

1. **Elle change l'espace de mesure.** `p_null` s'estime sur 70 915 bougies, pas sur 128 trades —
   facteur ~550×. Toute la malédiction de l'échantillon vient de ce qu'ARIT n'a jamais posé une
   question estimable en espace-bougie.
2. **Elle sépare deux choses qu'ARIT confond** : l'edge d'*information* (Δp) et l'edge de
   *géométrie* (le choix de a/b). Aujourd'hui ils sont additionnés dans un seul chiffre de PnL. La
   réponse une fois posée : **l'information vaut ~0 voire un peu négatif, la géométrie vaut peut-être
   quelque chose** — l'inverse exact de l'intuition qui a guidé le build (5 scores pondérés =
   l'information ; le stop = du détail).
3. **Elle donne un critère d'entrée qui a une unité.** `SEUIL_TREND = 0,50` n'en a pas. `Δp > 0` est
   en points de probabilité, convertible en espérance (`ΔE = Δp·(1 + a/b)`) puis en fraction de Kelly.

**Le corollaire, presque aussi important** : ARIT n'a **aucune unité de compte commune** entre ses
deux branches — la technique se mesure en R/trade, la macro en % sur 199 jours. Ces deux nombres ne
sont pas comparables, et c'est pourquoi le projet oscille entre les deux sans pouvoir arbitrer.
L'unité existe, imposée par la nature multiplicative de l'équité :

```
g = E[ln(1 + f·R)] / E[T]        (taux de croissance logarithmique par unité de temps)
```

Sous cette métrique, « la valeur du signal macro est la durée » devient l'énoncé que
`E[ln(1+fR)]` est modeste mais que `E[T]` vaut 199 jours, et **qu'un trade technique de 14 h doit
produire ~340 fois moins de log-croissance pour être équivalent**. C'est le calcul qui dirait, en un
seul nombre, laquelle des deux branches ARIT doit devenir — et **il ne demande aucune donnée
nouvelle**.

---

## 7. Arbitrages et vérifications

### 7.1 Une affirmation d'agent corrigée ✔
L'agent processus présentait le drawdown marqué au marché comme un écart de facteur 4 (46,5 % contre
12,3 %). Recalcul manuel sur les deux runs du diagnostic : **10,51 % contre 9,78 %** (A) et
**23,81 % contre 23,32 %** (B). L'écart massif n'existe que sur des runs à positions longuement
ouvertes. La trouvaille reste valide et utile — mais pour la **branche macro** et surtout pour la
**durée** du drawdown (2 812 jours pour B), pas pour la campagne A/B.

### 7.2 Trois agents convergent sur la même cible par trois chemins
La géométrie du stop est désignée indépendamment par : l'agent maths (S1, seule déviation positive
au nul), l'agent technique (T4, l'efficience de trajet conditionne la viabilité d'un stop serré) et
l'agent macro (M6, DVOL comme dénominateur ex-ante). **Convergence à retenir : le chantier prioritaire
déjà identifié en juillet est confirmé par trois analyses indépendantes.**

### 7.3 Contradiction arbitrée — mesurer avant d'ajouter
L'agent macro et l'agent technique proposent tous deux d'enrichir les entrées (nouvelles séries,
nouvelles features). L'agent maths démontre que **rien de tout cela n'est mesurable à n = 128**.
Arbitrage retenu : **P2 (récupérer les signaux rejetés) et T1 (auditer les scores existants) passent
avant toute nouvelle donnée.** Ajouter une variable à un scoring dont on ignore si un seul de ses
5 termes porte de l'information, c'est augmenter le budget de tests sans augmenter l'information.

### 7.4 Le vault croit parquée une idée qui a déjà été testée ✔
La note `arit/idée macro arit.md` (jamais indexée) propose un « arbre de probabilité » macro
alimenté par NLP + réseau bayésien. **`research/arbre_v0/` est exactement cette idée en v0**, testée
sur FOMC/CPI : tous les intervalles de confiance chevauchent la baseline, Brier walk-forward jamais
meilleur que 50/50. Mais son propre `RESULTATS.md` avoue une limite décisive : les mesures sont en
**bougies daily UTC**, or FOMC tombe à 14h00 ET et CPI à 08h30 ET — l'étude a donc mesuré la
*dérive post-événement*, **jamais la réaction à l'annonce**. Les 169 dates exactes sont déjà
téléchargées et cachées localement. **Refaire l'event study en 1 h autour du timestamp exact coûte
quasi rien et n'a jamais été fait** 🆕.

### 7.5 Ce que le vault n'a pas du tout
Absents du second cerveau, donc entièrement neufs pour le projet : processus de Hawkes · GARCH et
volatilité conditionnelle · HMM et régimes cachés · critère de Kelly · cointégration · order flow
niveau L2/L3 · ML appliqué au trading · NLP de sentiment quantifié · volatilité implicite et pricing
d'options · VaR / Expected Shortfall · théorie de l'information · walk-forward automatisé et
validation croisée purgée.

---

## 8. Plan proposé — trois vagues

Aucune de ces étapes n'est engagée. Chaque étape a un critère de passage **et** un critère
d'abandon, écrits avant de lancer.

### Vague 1 — Ne rien ajouter, tout remesurer (aucune donnée nouvelle, ~1 semaine)

| Ordre | Action | Passage | Abandon |
|---|---|---|---|
| 1 | **S1** : modèle nul par franchissement de barrière sur les 128 trades et sur le demi-stop | Δp publié avec son IC | — |
| 2 | **S2 + S3** : MDE, budget de tests N, Benjamini-Hochberg, DSR appliqués **rétroactivement** aux deux rapports de juillet | chaque conclusion porte sa p corrigée | — |
| 3 | **P1** : lire `wallet_stats` de tous les zips, republier profondeur **et durée** du DD ; réécrire le gate `docs/09 §9.2` | tous les rapports corrigés | — |
| 4 | **S4 + S6** : posterior bayésien de l'espérance, puis Kelly et risque de ruine | `f*` chiffré face aux caps de `params.py` | — |
| 5 | **P3** : sceller le hold-out 2025-01 → 2026-07 | `list-data` s'arrête au 2024-12-31 | — |
| 6 | **P6** : `EXPERIMENTS.jsonl`, N initialisé honnêtement (≥ 30 essais déjà consommés) | fichier commité | — |
| 7 | **§1.7** : dépendance de queue des 4 paires, nombre de paris effectifs | λ_L chiffré | — |

**Coût : quasi nul. Valeur : ferme des chantiers au lieu d'en ouvrir.** C'est la vague la plus
rentable du plan, et la seule qui peut être menée sans aucune décision de gouvernance.

### Vague 2 — Élargir l'échantillon et auditer l'existant (~2-3 semaines)

| Ordre | Action | Passage | Abandon |
|---|---|---|---|
| 1 | **P2** : `--export signals` + `--rejected-signals`, jointure avec `ev_gate_check` | **N ≥ 400 signaux** | N < 250 ⇒ l'edge technique est non testable, basculer sur la macro |
| 2 | **T1** : audit d'information des 5 scores sur 70 915 barres | ≥ 1 score avec IC ≥ 0,04, signe stable | tous les IC < 0,04 ⇒ le scoring est vide, changer de famille de signal |
| 3 | **T8** : dé-biaiser `s_volume` et le seuil de déplacement de l'heure et du jour | IC normalisé > IC brut | sinon garder l'existant |
| 4 | **S5** : volatilité conditionnelle EWMA/HAR, homogénéisation du R | QLIKE hors-échantillon bat ATR(14) | test de Diebold-Mariano non significatif ⇒ garder l'ATR |
| 5 | **T4 + S1** : efficience de trajet et viabilité d'un stop à demi-distance, **frais inclus** (**P7**) | espérance nette > 0 à 15 bps | change de signe entre 6 et 15 bps ⇒ mort |
| 6 | **P4** : walk-forward ancré sur ce qui a survécu | dégradation IS→OOS < 50 %, aucune fenêtre ne porte > 40 % du PnL | sinon retour vague 1 en incrémentant N |

### Vague 3 — Alors seulement, ajouter de la donnée

Dans cet ordre, et **une seule à la fois**, chacune préenregistrée : **T2 + T7** (klines complètes :
taker buy + nombre de trades, 5 Mo, la seule information réellement neuve et gratuite) → **M1**
(basis spot-perp, attaque le poste qui a mangé 86 % du profit) → **M2** (net liquidity en
*remplacement* de `DFF`) → **M3** (HY OAS, exogène au crypto) → le reste selon les verdicts.

**Puis** : `check_bias.py` sur la configuration finale (code de sortie 0 exigé ; le code 2
« indéterminé » n'est jamais un succès), et **enfin** l'ouverture du hold-out — une seule fois.

---

## 9. Hypothèses d'edge candidates pour un `docs/01` v4

`docs/01_edge.md` est **signé** et prévoit noir sur blanc : *« si B ≤ A : hypothèse invalidée,
retour recherche. Pas de rationalisation. »* La condition est remplie depuis le 19/07 (B = −17,4 %,
A = +0,12 %). Le projet fonctionne donc aujourd'hui **sans hypothèse d'edge valide**. Trois
candidates, formulées pour être falsifiables :

**H1 — Géométrie plutôt qu'information.** *L'edge d'ARIT n'est pas dans la sélection des entrées mais
dans la géométrie du couple (stop, cible) : à information nulle, un stop à demi-distance sur des
trajets efficients produit un Δp positif après frais.*
Falsification : Δp ≤ 0 sur ≥ 400 signaux, ou espérance nette qui change de signe entre 6 et 15 bps.
**C'est l'hypothèse la mieux soutenue par les mesures existantes** (seule déviation positive au nul,
z = 1,74).

**H2 — La durée plutôt que le timing.** *L'edge est dans la détention longue conditionnée à un
régime macro, mesurée en croissance logarithmique par unité de temps, et le coût de portage est la
variable de décision.*
Falsification : `g = E[ln(1+fR)]/E[T]` de la branche macro ≤ celui du buy & hold spot après funding,
ou p bloc-bootstrap > 0,20 sur un walk-forward des seuils.
Soutien actuel : p = 0,095 (le seul signal non-bruit), +577 % en spot contre +769 % de buy & hold.

**H3 — Le régime plutôt que le signal.** *ARIT n'a pas de problème de signal mais de contexte :
le même déclencheur a une espérance positive dans un sous-régime identifiable (volatilité comprimée,
dispersion faible, basis modéré) et négative ailleurs.*
Falsification : aucun partitionnement en 3 terciles ne produit un PF ≥ 1,20 avec ≥ 35 trades dans le
meilleur tercile.
⚠️ C'est l'hypothèse la plus dangereuse : sur un substrat à espérance nulle, **tout filtre qui réduit
l'exposition paraît positif** (piège déjà nommé dans le vault : « biais du substrat nul »).

---

## 10. Pièges transverses à acter avant toute campagne

1. **Le budget de tests est déjà dépassé.** ~40 essais consommés sur les mêmes données. Toute
   nouvelle p-value doit être corrigée et le compteur tenu.
2. **Le look-ahead peut vivre dans la donnée, pas dans le code.** `check_bias.py` ne tronque que
   l'OHLCV. Les séries révisées rétroactivement (NFCI, netflow avec ré-étiquetage d'adresses,
   historique DefiLlama recalculé) portent un biais que **rien dans le repo ne peut détecter**.
   Parade : archiver un snapshot daté à chaque téléchargement, et ne jamais re-télécharger
   l'historique d'un backtest déjà validé.
3. **Le biais de sélection des 4 paires.** BTC/ETH/SOL/BNB sont les survivants de 2026, pas ceux de
   2018. Toute mesure transversale sur 2018-2020 est faite sur un panier choisi avec la connaissance
   de 2026.
4. **Ne jamais valider une feature sur les 128 trades quand elle peut l'être sur 70 915 barres.**
   La puissance d'un test conditionnel sur 128 trades est de ~15 % : on ne mesurera que du bruit,
   et on l'interprétera.
5. **Un venv de recherche séparé.** Les dépendances des pistes 🟡 (`hmmlearn` en maintenance
   limitée, `statsmodels`, `ruptures` sans compatibilité pandas 3 confirmée) ne doivent jamais
   toucher `C:\Users\jofar\venvs\arit` — créer `venvs\arit-research`.

---

## Annexe — provenance

Repo lu : `CLAUDE.md`, `guide.md`, `docs/` (01, 03-11), `modules/`, `user_data/strategies/arit_lib/`,
`services/`, `scripts/`, `analysis/`, `research/` (edge_2026-07, macro_flip, arbre_v0,
correlation_block, _reporting), `for claude build/`.
Vault Obsidian : 109 notes, dont `arit/` (11) et `trading/` (52) — lecture seule.
Sources externes vérifiées en direct le 2026-07-31 : Binance Data Vision (klines, metrics,
premiumIndexKlines), FRED et ALFRED, US Treasury Fiscal Data, Coin Metrics community, Deribit DVOL,
DefiLlama, documentation freqtrade 2026.6, et la littérature citée (Bailey & López de Prado 2014 ·
Peters 2019 · Corsi 2009 · Politis-Romano · Adams & MacKay 2007 · López de Prado 2018).

Mesures faites à la main pour ce rapport : colonnes des feathers · bougies cumulées 4h et 1h ·
contenu des zips de backtest · drawdown marqué au marché et sa durée sur les runs A et B ·
présence et contenu de `wallet_stats` · nature réelle de `research/arbre_v0/`.
