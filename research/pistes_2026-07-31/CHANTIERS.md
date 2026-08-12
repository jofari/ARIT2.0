# ARIT — état des chantiers au 2026-07-31

Inventaire de **tout ce qui est ouvert** : décisions en attente, chantiers de mesure, dettes
techniques, et ce qui bloque le dry-run. Rien de ce qui suit n'est appliqué.

**État du projet en une phrase** : le bot est construit, testé (230 tests) et instrumenté, mais
il **n'a aucun edge démontré**, son hypothèse fondatrice est falsifiée depuis le 19/07, et il
n'a **jamais tourné en dry-run**.

---

## A. Décisions en attente de ta signature — c'est le vrai goulot

Aucune ne demande plus de dix minutes de réflexion, toutes bloquent quelque chose en aval.

| # | Décision | Mesuré ? | Ce que ça débloque | Depuis |
|---|---|---|---|---|
| A1 | `startup_candle_count` : 200 → **999** | ✅ 3 fenêtres, 2 paires | des backtests dont l'EMA200 journalière n'est pas fausse de 9,55 % | 31/07 |
| A2 | Retirer `pivot_high`/`pivot_low` bruts du DataFrame | ✅ audit look-ahead | un `check_bias.py` qui sort en code 0 | 31/07 |
| A3 | Bloc corrélation : `SP500` → **`NASDAQ100`** | ⚠️ à re-vérifier | évite une dégradation **silencieuse** dans ~13 mois | 31/07 |
| A4 | Fusionner ou non le bloc corrélation macro | ✅ 15 tests, module livré | la question fail-open / fail-safe reste ouverte | 30/07 |
| A5 | Véto macro HOSTILE **seul** (sans la pénalité NEUTRE) | ✅ B : −19,1 % → −7,0 %, DD 24,9 % → 10,6 % | un filtre de régime qui marche | 17/07 |
| A6 | Sizing : risque **constant** au lieu du risque par conviction | ✅ Kelly = 1,16 %, MDE par bande = +0,61R | un sizing justifiable | 31/07 |
| A7 | Choisir l'hypothèse d'edge de remplacement (H1 géométrie / H2 durée / H3 régime) | — | tout le reste : sans hypothèse signée, aucune campagne n'a de critère de succès | 19/07 |
| A8 | G-set v2 (supprimer G1/G2/G3/G5/G6, garder G4+G7) | ✅ mais **à re-mesurer** après réparation de l'entrée | — | 19/07 |

---

## B. Chantiers de mesure — le plan en trois vagues

### Vague 1 — ne rien ajouter, tout remesurer (coût quasi nul, aucune donnée nouvelle)

| # | Chantier | Effort | Ce que ça produit |
|---|---|---|---|
| B1 | Modèle nul de franchissement de barrière | S | l'edge devient `Δp`, mesurable sur 70 915 bougies au lieu de 128 trades |
| B2 | MDE + budget de tests + correction Benjamini-Hochberg, **rétroactifs** | S | quelles conclusions de juillet sont recevables |
| B3 | Lire `wallet_stats` de tous les zips existants | S | profondeur **et durée** du drawdown, sans re-run |
| B4 | Posterior bayésien de l'espérance, puis Kelly et risque de ruine | S | le sizing chiffré face aux bornes actuelles |
| B5 | Sceller le hold-out 2025-01 → 2026-07 | S | la seule p-value future à laquelle croire |
| B6 | `research/EXPERIMENTS.jsonl` + préenregistrement des hypothèses | S | le compteur d'essais, initialisé honnêtement à ≥ 30 |
| B7 | Dépendance de queue des 4 paires | M | le nombre réel de paris indépendants (~1,2, pas 3) |

### Vague 2 — élargir l'échantillon et auditer l'existant

| # | Chantier | Critère de passage | Critère d'abandon |
|---|---|---|---|
| B8 | `--export signals` + `--rejected-signals`, joints aux `ev_gate_check` | **N ≥ 400 signaux** | N < 250 ⇒ l'edge technique est non testable, basculer sur la macro |
| B9 | Audit d'information des 5 scores (IC sur 70 915 barres) | ≥ 1 score avec IC ≥ 0,04, signe stable | tous < 0,04 ⇒ le scoring est vide, changer de famille de signal |
| B10 | Dé-biaiser le score de volume de l'heure et du jour | IC normalisé > IC brut | sinon garder l'existant |
| B11 | Volatilité conditionnelle (EWMA → HAR-RV) | bat ATR(14) en QLIKE hors échantillon | Diebold-Mariano non significatif ⇒ garder l'ATR |
| B12 | Stops fractionnaires en 5m, **frais inclus** | espérance nette > 0 à 15 bps | change de signe entre 6 et 15 bps ⇒ mort |
| B13 | Walk-forward ancré sur ce qui survit | dégradation IS→OOS < 50 %, aucune fenêtre ne porte > 40 % du PnL | sinon retour vague 1 |

### Vague 3 — alors seulement, ajouter de la donnée (une à la fois, préenregistrée)

`B14` klines Binance complètes (taker buy + nombre de trades, ~5 Mo) → `B15` basis spot-perp →
`B16` net liquidity en **remplacement** du taux Fed → `B17` HY OAS.

---

## C. Dettes techniques — des choses qui ne marchent pas aujourd'hui

| # | Dette | Statut |
|---|---|---|
| C1 | **`FINNHUB_KEY` vide** → le calendrier économique ne fonctionne pas, la porte « news » est inerte ou bloquante selon l'état du fichier macro | jamais tranché |
| C2 | **Porte « spread » inerte** (`spread_frac = None` en permanence) ; `spread_state.py` validé le 09/07, jamais codé | jamais codé |
| C3 | Bollinger déclaré dans `params.py` avec « à câbler » | depuis le 09/07 |
| C4 | Force des supports/résistances par nombre de touches : constante définie, jamais implémentée | depuis le 13/07 |
| C5 | Fraîcheur du signal 4h : constante définie, **non appliquée** | depuis le 13/07 |
| C6 | Protections freqtrade (cooldown, stoploss guard) : spécifiées, jamais implémentées — et elles vivent désormais **dans la stratégie**, plus en config | depuis 2024.10 côté freqtrade |
| C7 | **Webhook Discord à régénérer** — il a transité en clair dans une conversation | signalé le 19/07 |
| C8 | `Untitled-1.py` parasite à la racine | signalé le 22/07 |
| C9 | `hyperopt` et les commandes de tracé **inutilisables** dans le venv (optuna et plotly absents) | constaté le 31/07 |

---

## D. Branche macro (MacroFlip) — quatre chantiers identifiés, aucun lancé

| # | Chantier | Gain mesuré |
|---|---|---|
| D1 | **Passer les jambes longues en spot** au lieu du perpétuel | **+267 % → +579 %** — le seul levier déjà mesuré et jamais appliqué |
| D2 | Walk-forward des 5 seuils macro (calibrer 2020-2022, tester 2023-2026) | prérequis explicite avant tout dry-run |
| D3 | Ablation des 5 composants macro (lequel porte le signal ?) | — |
| D4 | Augmenter n (ETH/SOL/BNB, ou variante flat-neutre à 134 trades) | p = 0,095 sur 12 trades est indéfendable |

---

## E. Ce qui bloque le dry-run, dans l'ordre

1. **Aucune hypothèse d'edge signée** (A7) — sans elle, un dry-run n'a pas de critère de succès.
2. **Walk-forward jamais fait** (B13, D2) — identifié comme prérequis dans deux rapports.
3. **Drawdown mal borné** : le gate ne contraint que la profondeur, alors que le produit B passe
   **2 812 jours sous l'eau** (7,7 ans).
4. **Gate matériel** : capital réel ⇒ machine allumée en permanence. Un laptop ne suffit pas.
5. Webhook à régénérer (C7) avant la phase canari.

---

## Ce qui est terminé et n'a plus besoin de rien

- Le bot : 230 tests verts, ruff propre, 4 process, journal JSONL de chaque décision.
- **Zéro look-ahead décisionnel prouvé mécaniquement** (0 entrée et 0 sortie biaisées sur
  67 signaux) — l'interdit n°3 n'est plus une promesse.
- Les deux checks de biais câblés, outillés et testés (`scripts/check_bias.py`, 28 tests).
- Le diagnostic lui-même : edge d'entrée nul, gestion destructrice, macro = seul signal
  non-bruit. Ces trois conclusions sont solides et ne sont pas à refaire.
- Deux schémas d'architecture à jour (`modules/ARCHITECTURE.md`).

---

# MISE À JOUR DU 2026-08-04 — état des dettes C

`DECISIONS.md` (racine) fait foi. Le tableau C ci-dessus est daté du 31/07 ; voici où il en est.

| # | Dette | Statut au 04/08 |
|---|---|---|
| C1 | Calendrier économique | **FERMÉ le 04/08 (soir)** — CPI/NFP 2026 renseignés (40 événements en primaire) + fetch FF élargi à **tous les rouges, toutes devises**. ⚠️ 2027 à compléter fin 2026 |
| C2 | Porte spread inerte | **FERMÉ le 04/08 (soir)** — Jonas acte : reste inerte, journalisée sans décider, on tranchera sur mesure |
| C3 | Bollinger | **FERMÉ** le 03/08 — `bb_*_1h`, journalisées, non décisionnelles |
| C4 | Force S/R par touches | **FERMÉ** — constante supprimée (annulé par Jonas) |
| C5 | Fraîcheur signal 4h | **FERMÉ** — constante supprimée (annulé par Jonas) |
| C6 | Protections freqtrade | **FERMÉ** le 04/08 — `params.PROTECTIONS`, `docs/07 §7.1.1` |
| C7 | Webhook Discord | **FERMÉ le 04/08 (soir)** — régénéré par Jonas, ancien supprimé, nouveau en `.env` |
| C8 | `Untitled-1.py` | sans objet — fichier absent |
| C9 | hyperopt/plot inutilisables | **FERMÉ le 04/08 (soir)** — `optuna` + `plotly` installés dans le venv |

> **Au 2026-08-04 au soir : plus AUCUNE dette C ouverte.** Détail et arbitrages dans
> `DECISIONS.md`, section « fermeture de TOUTES les dettes C ».

## Décisions A

A1, A3, A4 appliqués (03/08). **A2 (long ET short) appliqué le 04/08** — le bot n'est plus
long-only. A5 acté sans code. A6 appliqué (risque constant 1,16 %). A7 signé (`docs/01`
v4). A8 toujours reporté par Jonas.

## Ce qui bloque le dry-run — liste RÉVISÉE au 04/08

La liste `E` ci-dessus reste valable, avec deux entrées **nouvelles et prioritaires** :

1. **Parité backtest/live rompue par A2** : le régime macro V1.1 en 5 composants n'est
   produit qu'en backtest. `services/macro_state.py` écrit `fear_greed`/`risk_off`/`stale`
   mais **pas** ce régime, et `macro_regime.regime_now()` n'a donc aucun producteur. En
   live, `direction_macro` retombe sur son fail-safe ⇒ **le live est long-only alors que le
   backtest est long+short**. Ce sont deux produits différents. À traiter dans M08.
2. **Données OHLCV futures manquantes** : `user_data/data/binance/futures/` n'a que BTC en
   4h et 5m. Il faut les 4 paires en 5m/1h/4h/1d. Sans elles, aucun backtest en futures,
   et `check_bias.py` ne peut pas re-tourner sur la nouvelle config.
3. (rappel) Hypothèse signée : **fait** (A7) — ce point de la liste E est levé.

---

# MISE À JOUR DU 2026-08-07 — parité comblée, dry-run lancé

`DECISIONS.md` (racine), section « Session du 2026-08-07 », fait foi.

## Bloquants du dry-run — état

| # (liste du 04/08) | Bloquant | Statut au 07/08 |
|---|---|---|
| 1 | Parité backtest/live rompue par A2 | **FERMÉ** — `macro_state` écrit les 5 scores 06.2, `macro_regime.attach_regime_now()` pose le régime en live, fail-safe `regimes.donnee_non_fiable` |
| 2 | Données OHLCV futures manquantes | **OUVERT** — seul BTC en 4h/5m. Bloque les backtests et `check_bias.py`, PAS le dry-run |
| 3 | Hypothèse signée (A7) | levé depuis le 04/08 |

De la liste `E` d'origine : A7 fait ; **walk-forward (B13/D2) toujours pas fait** ; drawdown
toujours borné en profondeur seulement ; gate matériel désormais explicite (voir ci-dessous).

## Bloquants OPÉRATIONNELS — ils n'étaient dans aucune liste

Découverts le 07/08 en traçant le chemin live. Ils étaient invisibles parce que la liste `E`
ne couvrait que les blocages *scientifiques*.

| Constat | Effet | Traitement |
|---|---|---|
| `macro_state.py` est un one-shot et **la tâche horaire n'existait pas** | après 2 h : stale ⇒ RISK_OFF ⇒ **plus aucune entrée**, sans alerte | tâche `ARIT macro_state` créée |
| Historique macro périmé (12/07) | 5 composants stale | tâche `ARIT download_macro` créée |
| FRED refusait notre User-Agent | `dxy` + `taux` non rafraîchis **depuis un mois, en silence** | UA retiré de `dl_fred` |
| Rien ne survivait à un redémarrage | 4 consoles perdues à la première mise à jour Windows | `ARIT_relance.cmd` (dossier Démarrage) + `--si-absent` |

⚠️ **Gate matériel, désormais précis** : le dry-run exige le PC allumé **et la session
ouverte**. Un redémarrage sans reconnexion automatique arrête tout jusqu'au retour.

## Ce que cette absence produit

Des **évaluations journalisées** (`user_data/logs/decisions/`), qui étaient à zéro. C'est le
prérequis de B8 (N ≥ 400 signaux), B9 (audit d'IC des 5 scores) et de toute piste ML. Le
dry-run ne valide **aucune** hypothèse : il collecte.

## MISE À JOUR DU 2026-08-08 — bloquant nº2 fermé, et ce que le dry-run peut/ne peut pas produire

**Données OHLCV futures : FERMÉ.** Les 4 paires sont désormais en 5m/1h/4h/1d
(24 fichiers, 69 Mo). 4h : 12 273 bougies par paire du 2021-01-01 au 2026-08-08 ;
BTC 5m : 727 458 bougies. Débloque les backtests futures et `check_bias.py`.

### Le dry-run ne produira PAS de statistiques de trades — c'est arithmétique

79 trades sur 2 040 jours = **0,039 trade/jour**. Sur trois semaines :

> **0,81 trade attendu.** Zéro est le résultat le plus probable, pas une anomalie.

Attendre des sorties, des `r_final` ou des MFE/MAE de ce dry-run était exclu dès le
départ. Le chantier « sortie » continue de reposer sur les 79 trades du backtest, qui
portent déjà `mae_r`/`mfe_r`.

### Ce qu'il produit, en revanche, est exploitable

~420 **évaluations** (≈ 20/jour après une captation mesurée à 83 %). Chacune est un
vecteur de features complet et horodaté : 5 scores, 63 motifs de bougie, `rr_dispo`,
ADX, EMA50/200, régime macro, `direction_macro`, conviction, seuil.

⚠️ **Le prix est reconstituable** : `close_4h = ema50_4h + close_vs_ema`, les deux étant
dans `regime_inputs`. C'est ce qui rend chaque évaluation raccordable à un rendement
futur, donc étiquetable par triple barrière **sans aucun trade**. Sans cette propriété,
trois semaines de collecte seraient inexploitables.

Alimente directement **B1** (modèle nul, mesuré sur bougies), **B9** (IC des 5 scores :
corrélation score ↔ rendement futur) et toute méta-labellisation.

**À faire au retour** : relancer un `freqtrade download-data` pour étendre l'OHLCV
jusqu'à la date du retour — les données s'arrêtent au 2026-08-08, il faut le futur des
évaluations pour les étiqueter.

### Captation à 83 % — constaté, non corrigé

Sur 6 blocs 4h : 20 paires-évaluations sur 24. `_journal_evaluation` n'écrit que si
`new_4h` est vrai sur la dernière ligne ; selon l'ordre de rafraîchissement des paires,
certaines passent à côté. **Non corrigé volontairement** : la garde `new_4h` existe pour
empêcher deux évaluations du même setup (docs/11 §11.2), un correctif naïf créerait des
doublons. À traiter au retour, avec la mesure en main.

---

# F. Idées déposées, non tranchées

| # | Idée | Origine | Statut | Détail |
|---|---|---|---|---|
| F1 | **Banc d'essai de stratégies** — un module qui fait tourner d'autres stratégies que AritV1 sur le même protocole, pour comparer les rendements et **diversifier les formes d'investissement** (mean-reversion, portage/funding, macro seule, spot vs perp) | Jonas, 12/08 | **déposé, non tranché** | `DECISIONS.md` § « Session du 2026-08-12 » |

⚠️ F1 a trois prérequis non négociables, écrits dans `DECISIONS.md` : B2 (correction
Benjamini-Hochberg), B5 (hold-out scellé), B6 (`EXPERIMENTS.jsonl`). Un banc d'essai sans
budget de tests déclaré est une machine à fabriquer du bruit statistiquement gagnant.
Ces trois-là sont précisément le périmètre de la **routine cloud vague 1** armée le 08/08 :
F1 se branche derrière elle. Second frein, matériel celui-là : les OHLCV futures manquent
pour 3 paires sur 4, donc un banc lancé aujourd'hui comparerait les candidates sur BTC seul
— la paire la plus perdante du run du 04/08.
