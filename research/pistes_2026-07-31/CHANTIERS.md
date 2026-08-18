# ARIT — état des chantiers au 2026-07-31

> ⚠️ **CE FICHIER EST APPEND-ONLY. Les tableaux A à E datent du 31/07 ; les statuts réels sont
> dans les sections « MISE À JOUR DU … » plus bas et dans `DECISIONS.md` (racine), qui fait foi.**
> ⚠️ Depuis le 17/08, `DECISIONS.md` est **purgé** : il ne contient plus que les décisions
> **ouvertes**. Une décision fermée n'y est plus, ses motifs sont dans
> `for claude build/BUILD_NOTES.md` (§ 2026-08-17) et dans `git log -p -- DECISIONS.md`.
> Ne jamais compter les lignes de A-E comme « ouvertes » sans lire les mises à jour : les statuts
> périmés ont déjà été recomptés à tort comme des décisions en attente. Depuis le 16/08, chaque
> ligne fermée est **barrée en place** — si elle n'est pas barrée, elle est ouverte.
>
> Raccourci : **C = tout fermé (04/08)** · **B1/B2/B5/B8/B9 fermés (12/08)** · **B6 fermé (18/08)** ·
> **D1 abandonné (12/08)** · **A1-A7 appliqués, A8 reporté** · reste ouvert : B3/B4/B7/B10-B13,
> D2-D4, E2/E3/E4, F1/F2, G1-G4, H1-H9, Q1-Q10.

Inventaire de **tout ce qui est ouvert** : décisions en attente, chantiers de mesure, dettes
techniques, et ce qui bloque le dry-run. Rien de ce qui suit n'est appliqué.

**État du projet en une phrase** : le bot est construit, testé (230 tests) et instrumenté, mais
il **n'a aucun edge démontré**, son hypothèse fondatrice est falsifiée depuis le 19/07, et il
n'a **jamais tourné en dry-run**.

---

## A. Décisions en attente de ta signature — ✅ signées, sauf A8

> ✅ **A1, A3, A4 appliqués le 03/08 · A2 (long ET short) appliqué le 04/08 · A5 acté sans code ·
> A6 appliqué (risque constant 1,16 %) · A7 signé (`docs/01` v4).** Seule **A8 reste reportée par
> Jonas**. Détail : § « MISE À JOUR DU 2026-08-04 » plus bas.

| # | Décision | Statut | Ce que ça débloque | Depuis |
|---|---|---|---|---|
| ~~A1~~ | ~~`startup_candle_count` : 200 → **999**~~ | ✅ appliqué 03/08 | des backtests dont l'EMA200 journalière n'est pas fausse de 9,55 % | 31/07 |
| ~~A2~~ | ~~Retirer `pivot_high`/`pivot_low` bruts du DataFrame~~ | ✅ appliqué 04/08 (avec le short) | un `check_bias.py` qui sort en code 0 | 31/07 |
| ~~A3~~ | ~~Bloc corrélation : `SP500` → **`NASDAQ100`**~~ | ✅ appliqué 03/08 | évite une dégradation **silencieuse** dans ~13 mois | 31/07 |
| ~~A4~~ | ~~Fusionner ou non le bloc corrélation macro~~ | ✅ appliqué 03/08 | la question fail-open / fail-safe reste ouverte | 30/07 |
| ~~A5~~ | ~~Véto macro HOSTILE **seul**~~ | ✅ acté sans code · **mesuré 18/08 : INDÉCIDABLE** (`research/ablation_A5/RAPPORT.md`) | 7 signaux marginaux en 5 ans, MDE +1,53 R : la porte macro n'est pas mesurable à ce N | 17/07 |
| ~~A6~~ | ~~Sizing : risque **constant**~~ | ✅ appliqué (1,16 %) | un sizing justifiable | 31/07 |
| ~~A7~~ | ~~Choisir l'hypothèse d'edge de remplacement~~ | ✅ **signée 04/08** (`docs/01` v4) | tout le reste — c'était le point 1 de la liste E | 19/07 |
| **A8** | G-set v2 (supprimer G1/G2/G3/G5/G6, garder G4+G7) | 🔴 **reporté par Jonas**, à re-mesurer après réparation de l'entrée | — | 19/07 |

---

## B. Chantiers de mesure — le plan en trois vagues

### Vague 1 — ne rien ajouter, tout remesurer (coût quasi nul, aucune donnée nouvelle)

| # | Chantier | Effort | Ce que ça produit |
|---|---|---|---|
| ~~B1~~ | ~~Modèle nul de franchissement de barrière~~ | S | ✅ **FERMÉ 12/08** — long E[R] = −0,0123 · short −0,0370, sur 42 902 bougies |
| ~~B2~~ | ~~MDE + budget de tests + correction Benjamini-Hochberg~~ | S | ✅ **APPLIQUÉ 12/08** (`analysis/mesures.py`, FDR 0,10) — ⚠️ rétroactif sur juillet : reste à faire |
| B3 | Lire `wallet_stats` de tous les zips existants | S | profondeur **et durée** du drawdown, sans re-run |
| B4 | Posterior bayésien de l'espérance, puis Kelly et risque de ruine | S | le sizing chiffré face aux bornes actuelles |
| ~~B5~~ | ~~Sceller le hold-out 2025-01 → 2026-07~~ | S | ✅ **APPLIQUÉ 12/08** — colonne `split`, 13 932 évaluations scellées |
| ~~B6~~ | ~~`research/EXPERIMENTS.jsonl` + préenregistrement des hypothèses~~ | S | ✅ **FERMÉ 18/08** — registre + `EXPERIMENTS.md`, verrou **matériel** (`ablation_macro.preenregistrement()` arrête le script sans entrée préalable), compteur initialisé à 30. Ne bloque plus F1/H7/H1 |
| B7 | Dépendance de queue des 4 paires | M | le nombre réel de paris indépendants (~1,2, pas 3) |

### Vague 2 — élargir l'échantillon et auditer l'existant

| # | Chantier | Critère de passage | Critère d'abandon |
|---|---|---|---|
| ~~B8~~ | ~~`--export signals` + `--rejected-signals`~~ | **N ≥ 400 signaux** | ✅ **SANS OBJET 12/08** (rejeu = 56 890 évaluations) — 🔴 mais **78 signaux en 5 ans** : le critère d'abandon « N < 250 » est **FRANCHI** |
| ~~B9~~ | ~~Audit d'information des 5 scores (IC)~~ | ≥ 1 score IC ≥ 0,04 | ✅ **FERMÉ 12/08 — critère REMPLI.** 9 features \|IC\| ≥ 0,04 survivant à BH. Meilleure : `s_structure` (+0,0851) |
| B10 | Dé-biaiser le score de volume de l'heure et du jour | IC normalisé > IC brut | sinon garder l'existant |
| B11 | Volatilité conditionnelle (EWMA → HAR-RV) | bat ATR(14) en QLIKE hors échantillon | Diebold-Mariano non significatif ⇒ garder l'ATR |
| B12 | Stops fractionnaires en 5m, **frais inclus** | espérance nette > 0 à 15 bps | change de signe entre 6 et 15 bps ⇒ mort |
| B13 | Walk-forward ancré sur ce qui survit | dégradation IS→OOS < 50 %, aucune fenêtre ne porte > 40 % du PnL | sinon retour vague 1 |

### Vague 3 — alors seulement, ajouter de la donnée (une à la fois, préenregistrée)

`B14` klines Binance complètes (taker buy + nombre de trades, ~5 Mo) → `B15` basis spot-perp →
`B16` net liquidity en **remplacement** du taux Fed → `B17` HY OAS.

---

## C. Dettes techniques — ✅ TOUTES FERMÉES le 2026-08-04

> ✅ **Aucune dette C ouverte depuis le 04/08 au soir.** Le tableau ci-dessous décrit l'état
> du **31/07** et n'est conservé que pour l'historique. Statuts à jour : § « MISE À JOUR DU
> 2026-08-04 » plus bas, et `BUILD_NOTES.md` § 2026-08-17 (`DECISIONS.md` a été purgé de ses
> décisions fermées le 17/08 — historique : `git log -p -- DECISIONS.md`).

| # | Dette (constat du 31/07) | Statut réel |
|---|---|---|
| C1 | ~~**`FINNHUB_KEY` vide** → le calendrier économique ne fonctionne pas, la porte « news » est inerte ou bloquante selon l'état du fichier macro~~ | **FERMÉ 04/08** — ⚠️ résidu : calendrier 2027 à compléter fin 2026 |
| C2 | ~~**Porte « spread » inerte** (`spread_frac = None` en permanence) ; `spread_state.py` validé le 09/07, jamais codé~~ | **FERMÉ 04/08** — inerte par décision de Jonas, journalisée sans décider |
| C3 | ~~Bollinger déclaré dans `params.py` avec « à câbler »~~ | **FERMÉ 03/08** |
| C4 | ~~Force des supports/résistances par nombre de touches~~ | **FERMÉ** — constante supprimée (annulé par Jonas) |
| C5 | ~~Fraîcheur du signal 4h : constante définie, non appliquée~~ | **FERMÉ** — constante supprimée (annulé par Jonas) |
| C6 | ~~Protections freqtrade (cooldown, stoploss guard)~~ | **FERMÉ 04/08** — `params.PROTECTIONS`, `docs/07 §7.1.1` |
| C7 | ~~**Webhook Discord à régénérer**~~ | **FERMÉ 04/08** — régénéré, ancien supprimé |
| C8 | ~~`Untitled-1.py` parasite à la racine~~ | **sans objet** — fichier absent |
| C9 | ~~`hyperopt` et les commandes de tracé inutilisables dans le venv~~ | **FERMÉ 04/08** — `optuna` + `plotly` installés |

---

## D. Branche macro (MacroFlip) — quatre chantiers identifiés, D1 abandonné le 12/08

| # | Chantier | Gain mesuré |
|---|---|---|
| D1 | ~~**Passer les jambes longues en spot** au lieu du perpétuel~~ | **FERMÉ — ABANDONNÉ le 12/08 par Jonas.** Le +267 % → +579 % n'est pas un edge : il mesure l'alternance bull/bear de la période. Motif complet : `BUILD_NOTES.md` § 2026-08-17 |
| D2 | Walk-forward des 5 seuils macro (calibrer 2020-2022, tester 2023-2026) | prérequis explicite avant tout dry-run |
| D3 | Ablation des 5 composants macro (lequel porte le signal ?) | — |
| D4 | Augmenter n (ETH/SOL/BNB, ou variante flat-neutre à 134 trades) | p = 0,095 sur 12 trades est indéfendable |

---

## E. Ce qui bloque le dry-run, dans l'ordre

> État du 31/07. Révisions successives : § 04/08, § 07/08, § 08/08 plus bas. Statuts à jour ci-dessous.

1. ~~**Aucune hypothèse d'edge signée** (A7)~~ — ✅ **levé le 04/08** (A7 signé, `docs/01` v4).
2. **Walk-forward jamais fait** (B13, D2) — 🔴 **toujours ouvert**. Mais depuis le 12/08 il passe
   **derrière Q1** : 78 signaux en 5 ans, aucun walk-forward ne conclut sur 78 observations.
3. **Drawdown mal borné** : le gate ne contraint que la profondeur, alors que le produit B passe
   **2 812 jours sous l'eau** (7,7 ans). 🔴 **toujours ouvert** (c'est B3).
4. **Gate matériel** : capital réel ⇒ machine allumée en permanence. Un laptop ne suffit pas.
   🔴 **ouvert et confirmé par les faits** : le dispositif du 07/08 a produit zéro donnée en
   trois semaines. Réponse envisagée = le VPS (G8), non codé.
5. ~~Webhook à régénérer (C7) avant la phase canari~~ — ✅ **fait le 04/08**.

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

`BUILD_NOTES.md` § 2026-08-17 fait foi. Le tableau C ci-dessus est daté du 31/07 ; voici où il en est.

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
> `for claude build/BUILD_NOTES.md` § 2026-08-17. Seuls C1-bis (palier orange) et C1-ter (dates
> 2027) restent ouverts, dans `DECISIONS.md`.

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

`BUILD_NOTES.md` § 2026-08-17 fait foi (section correspondante de `DECISIONS.md` purgée le 17/08).

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
| F1 | **Banc d'essai de stratégies** — un module qui fait tourner d'autres stratégies que AritV1 sur le même protocole, pour comparer les rendements et **diversifier les formes d'investissement** (mean-reversion, portage/funding, macro seule, spot vs perp) | Jonas, 12/08 | **déposé, non tranché** | `DECISIONS.md` § F1 |
| F2 | **Observabilité à distance du dry-run** — aujourd'hui nulle : FreqUI est sur `127.0.0.1`, toutes les traces sont gitignorées, et le seul signal distant est l'absence d'alerte Discord (qui ne distingue pas « bot sain » de « session Windows fermée »). Pistes : bot **Telegram natif** de freqtrade (`/status`, `/profit`, `/daily`, aucun port ouvert) — c'est aussi ce que M09 devait apporter — ou **Tailscale / Cloudflare Tunnel** (FreqUI reste sur `127.0.0.1` et devient joignable sans exposition publique). ❌ **Jamais** `listen_ip_address: 0.0.0.0` + redirection de port : l'API porte `/forceexit`, `/forcebuy`, `/stop` | Jonas, 12/08 | **déposé, non tranché** | cette ligne porte la substance ; voir aussi `DECISIONS.md` § G2 et § G8 |

⚠️ F1 a trois prérequis non négociables, écrits dans `DECISIONS.md` : B2 (correction
Benjamini-Hochberg), B5 (hold-out scellé), B6 (`EXPERIMENTS.jsonl`). Un banc d'essai sans
budget de tests déclaré est une machine à fabriquer du bruit statistiquement gagnant.
Ces trois-là sont précisément le périmètre de la **routine cloud vague 1** armée le 08/08 :
F1 se branche derrière elle. Second frein, matériel celui-là : les OHLCV futures manquent
pour 3 paires sur 4, donc un banc lancé aujourd'hui comparerait les candidates sur BTC seul
— la paire la plus perdante du run du 04/08.

---

# MISE À JOUR DU 2026-08-12 (soir) — B1, B2 et B9 fermés · le dataset existe

`BUILD_NOTES.md` § 2026-08-17 fait foi (mesures et pièges). Résumé de ce qui change dans les
tableaux ci-dessus.

## Le prérequis caché de toute la vague 2 : il n'y avait aucune évaluation

L'évènement `evaluation` — le seul portant le vecteur de features complet — n'est journalisé
qu'en live (`AritV1.py:61`, `if live:`). Le dry-run n'a jamais tenu une boucle. Décompte sur
tout `user_data/logs/decisions/` : **0 évaluation**. B8, B9 et toute piste ML étaient donc
sans données, contrairement à ce qu'annonçait la mise à jour du 08/08.

Résolu par le **rejeu hors-ligne** (`analysis/dataset.py`), qui applique les mêmes fonctions
pures d'`arit_lib` à 5 ans d'OHLCV : **56 890 évaluations en 69 secondes**, étiquetées par
triple barrière, hold-out B5 matérialisé en colonne `split`.

## État révisé des chantiers B

| # | Chantier | Statut au 12/08 |
|---|---|---|
| B1 | Modèle nul de franchissement de barrière | **FERMÉ** — long E[R] = −0,0123 (p(TP) 33,08 %) · short E[R] = −0,0370 (32,87 %), sur 42 902 bougies |
| B2 | MDE + budget de tests + Benjamini-Hochberg | **APPLIQUÉ pour la première fois** — `analysis/mesures.py`, FDR 0,10, 29 tests sur 38 survivent. Rétroactif sur juillet : toujours à faire |
| B5 | Sceller le hold-out 2025-01 → 2026-07 | **APPLIQUÉ** — colonne `split`, 13 932 évaluations scellées, exclues de toute mesure |
| B8 | `--export signals`, N ≥ 400 signaux | **sans objet sous cette forme** — le rejeu donne 56 890 évaluations. ⚠️ mais seulement **78 signaux** en 5 ans (50 longs + 28 shorts) : le critère d'abandon « N < 250 ⇒ l'edge technique est non testable » est **franchi** |
| B9 | Audit d'information des 5 scores (IC) | **FERMÉ — critère de passage REMPLI.** 9 features avec \|IC\| ≥ 0,04, signe stable, survivant à BH. Meilleure : `s_structure` (+0,0851) |

## Ce que B9 révèle et qui n'était pas dans le plan

`produit_pondere` (la somme Σ poids·score) a un IC de **+0,0642**, **inférieur à `s_structure`
seul (+0,0851)** : l'agrégation à poids figés dégrade le meilleur signal en y mélangeant
`s_sr` (IC −0,0497) et `s_patterns` (−0,0162), qui tirent à l'envers avec des poids positifs.

⇒ B10 (« dé-biaiser le score de volume ») n'est plus le chantier de scoring prioritaire :
`s_volume` a l'IC le plus faible de tous (+0,0170) et ne mérite pas d'être réparé en premier.
Ce qui compte est **l'agrégation**, pas un composant.

## Le vrai goulot, révisé

La liste `E` (« ce qui bloque le dry-run ») décrivait des blocages scientifiques. Le blocage
réel est plus simple et n'y figurait pas :

> **0,16 % des évaluations produisent un signal.** 78 entrées en cinq ans sur quatre paires.
> Aucun walk-forward (B13/D2), aucune correction de tests multiples, aucun modèle ne peut
> conclure quoi que ce soit sur 78 observations — quelle que soit la qualité de la méthode.

Augmenter le nombre d'entrées **mesurables** passe donc devant B13/D2 dans l'ordre réel des
priorités. C'est la question G4 posée à Jonas dans `DECISIONS.md`.

## Conséquence sur F1 (banc d'essai)

Les trois prérequis non négociables de F1 étaient B2, B5 et B6. ~~Reste B6~~ — **les trois sont
faits au 18/08** : `analysis/mesures.py` (B2), la colonne `split` (B5), et
`research/EXPERIMENTS.jsonl` + le refus matériel de mesurer sans préenregistrement (B6,
compteur initialisé à 30). **Plus aucun verrou méthodologique devant le banc.**

---

# H. ML, quantitatif et boucle d'amélioration — les neuf chantiers du 12/08

> ⚠️ **Numérotation** : ces chantiers sont notés `H`, **pas** `G`. Les `G1-G8` de `DECISIONS.md`
> sont des *questions et décisions* (G1 autorisation ML sur l'agrégation, G5 journal backtest,
> G6 deux bases…), pas des chantiers. Troisième collision de noms évitée après C6 et D1.

Le 12/08 Jonas ouvre neuf chantiers d'un coup. Aucun n'était réalisable ce jour-là : tous
dépendaient d'un jeu de données qui n'existait pas (`evaluation` n'était journalisé qu'en live,
et le live n'a jamais tenu une boucle — **0 évaluation** sur tout l'historique). Le rejeu
hors-ligne du 12/08 au soir (`analysis/dataset.py`, 56 890 évaluations étiquetées) lève ce
préalable commun. Les neuf redeviennent instruisables ; ils ne sont pas pour autant à ouvrir
en même temps.

| # | Chantier (formulation de Jonas) | Faisable aujourd'hui ? | Verrou |
|---|---|---|---|
| H1 | **Boucle d'auto-amélioration** | ⚠️ partiellement — **à retravailler avec précaution**, voir § H1 | B6 absent, et le précédent du 07/08 |
| H2 | **ML au CIO** (conviction / agrégation des scores) | ✅ données prêtes | **G1 non tranché** — touche l'interdit n° 5 |
| H3 | **ML à la documentation** | ✅ hors chemin de trading | aucun, mais aucun gain sur l'edge |
| H4 | **ML au position manager** (gestion) | ❌ **aveugle** | `exit` n'est écrit nulle part : 95 `entry`, **0 `exit`** — ni `r_final`, ni `mae_r`, ni `mfe_r` |
| H5 | **Quantitatif** (le socle de maths) | ✅ c'est le chantier le plus mûr | rien — détail § H5 |
| H6 | **Interface graphique** | ✅ mais FreqUI + `scripts/suivi.py` existent déjà | l'observabilité est **locale**, c'est ça le vrai manque (F2) |
| H7 | **Banc multi-stratégie** | ⚠️ = **F1**, déjà déposé | B6 ; + OHLCV futures désormais complètes (fermé le 08/08) |
| H8 | **Tracking retail vs institutionnel** | ❌ donnée absente | flux ETF / CVD taker / OI : source externe, aucune n'est câblée |
| H9 | **Agrégateur de news** | ❌ et à cadrer | **interdit n° 1** : aucun LLM dans le chemin de trading. Utilisable en amont, jamais en décision |

**Ordre proposé** (c'est la question G4, non tranchée) : **H5 d'abord**, parce que le goulot
mesuré n'est pas la qualité de l'entrée mais sa **rareté** — 78 signaux en 5 ans sur 4 paires,
soit 0,16 % des évaluations. Aucun modèle, aucun walk-forward, aucune boucle ne conclut quoi
que ce soit sur 78 observations. **H2 ensuite** (point d'insertion ML mesuré). **H1 en dernier**,
et seulement une fois B6 en place — une boucle branchée avant le compteur d'essais est une
machine à fabriquer du bruit gagnant.

---

## H1 — Boucle d'auto-amélioration : ce qui doit être retravaillé, et pourquoi

L'idée est bonne et c'est la plus dangereuse des neuf. Deux précédents, tous deux du projet :

1. **07/08** — un dispositif autonome a été armé pour trois semaines (tâches Windows, veille,
   relance au démarrage). Vérifié le 12/08 **sur la machine, pas dans la doc** : plus aucune
   tâche, plus de fichier de démarrage, plus de process, `macro_state.json` figé depuis 8 jours.
   Les trois semaines de collecte ont produit **zéro donnée**, sans une seule alerte.
   ⇒ *Une boucle qui n'a pas de preuve d'existence vérifiable n'existe pas.*
2. **08/08** — la routine cloud vague 1 (B2/B4/B5/B6) a été armée et n'a rien livré :
   `research/veille/` et `research/veille_locale/` sont **inexistants** au 12/08.
   ⇒ *Une boucle sans livrable versionné ne laisse aucune trace de son échec.*

### Les sept gardes, à écrire avant la première ligne de code

| # | Garde | Raison, tirée d'un fait du projet |
|---|---|---|
| 1 | **Elle mesure, elle ne conclut jamais.** Sortie = mesure + PR en draft ; la décision reste humaine | « un agent qui cherche pendant trois semaines *trouvera* quelque chose » (07/08) |
| 2 | **Préenregistrement obligatoire** : refuser de tourner si l'hypothèse n'est pas déclarée dans `research/EXPERIMENTS.jsonl` **avant** la mesure | B6 — le seul verrou encore ouvert |
| 3 | **Compteur d'essais global et persistant**, initialisé à ≥ 30, jamais remis à zéro entre runs ; FDR Benjamini-Hochberg appliqué sur la famille **cumulée**, pas par exécution | B2 ; une boucle multiplie les tests par construction |
| 4 | **Hold-out inaccessible physiquement** : le chargeur refuse `split == 'holdout'`, la boucle n'a pas de chemin pour l'atteindre | B5 — 13 932 évaluations scellées ne valent que si rien ne peut les lire |
| 5 | **Zéro contact avec la production** : jamais de push sur `main`, jamais `user_data/strategies/**`, `services/**`, ni les configs ; jamais les poids G1-G7 | interdit n° 5 + un dry-run tourne sur la machine de Jonas |
| 6 | **Heartbeat vérifié + livrable versionné** à chaque exécution, sinon la panne est muette | les deux précédents ci-dessus |
| 7 | **Quota et critère d'arrêt déclarés** (N tests/semaine, arrêt si le budget FDR est épuisé) | sans quota, « efficace » veut dire « produit plus de faux positifs » |

### Ce qui reste à trancher sur H1

- Où elle tourne : cloud (routine, ne voit pas `user_data/data/` ni `backtest_results/`, tous
  deux gitignorés) ou local (voit tout, meurt au redémarrage — précédent du 07/08).
- Ce qu'elle a le droit de faire tourner : mesures sur `arit_analyse.sqlite` seulement, ou aussi
  des backtests (donc du temps machine et un risque de p-hacking bien supérieur).
- Sa mémoire entre runs : `research/veille/JOURNAL.md` était prévu, jamais créé.

---

## H2 — ML au CIO : le point d'insertion est mesuré, l'autorisation ne l'est pas

Le premier point d'insertion du ML n'est ni la macro ni la gestion : c'est **l'agrégation des
scores**. `produit_pondere` (Σ poids·score) a un IC de **+0,0642**, soit **moins bon que
`s_structure` seul (+0,0851)**. L'agrégation à poids figés détruit de l'information mesurée, en
mélangeant `s_sr` (IC **−0,0497**) et `s_patterns` (−0,0162) avec des poids **positifs**.

⚠️ **Mesurer un IC n'est pas hyperopter ; remplacer l'agrégation par un modèle appris, si.**
C'est l'interdit n° 5, donc **un arbitrage de Jonas — question G1, ouverte.**

Un cran avant le ML, et sans le toucher : **l'ablation de `s_sr` et `s_patterns`** (question G3)
est une soustraction, pas une optimisation — elle ne franchit aucun interdit et se mesure sur le
dataset existant.

### Gardes ML, non négociables (elles valent pour H2 comme pour H4)

- **Purged K-fold + embargo** : les labels de triple barrière se chevauchent (fenêtre 96 h), les
  observations ne sont pas indépendantes. Une CV naïve surestime toujours.
- **Pondération par unicité** des échantillons chevauchants.
- **Aucune colonne `y_`** en entrée — la convention de nommage du dataset existe pour ça.
- **Stabilité inter-périodes exigée** comme critère de rétention (voir Q2) : `trend_dir` avait un
  IC de +0,0718 en 2019-2021 et **+0,0086 en 2024-2026** — le suivi de tendance naïf a été
  arbitragé, et c'est une des conditions de `signal_long`.
- Entraînement sur les **43 000 évaluations** hors hold-out, jamais sur les 78 signaux.

---

## H5 — Le chantier quantitatif, décomposé

C'est le plus mûr des neuf : les données existent, aucun interdit n'est touché, et il contient le
seul chantier qui débloque tous les autres (Q1).

| # | Sous-chantier | Effort | Pourquoi il compte | Statut |
|---|---|---|---|---|
| **Q1** | **Courbe N(seuil) : combien de signaux, et à quelle espérance, si on desserre chaque porte une à une** (`rr_min`, conviction, ADX, régime) | M | **le goulot n° 1 du projet** : 78 signaux en 5 ans. Rien n'est mesurable avant | à ouvrir |
| Q2 | Câbler la **stabilité inter-périodes** dans `mesures.py` comme critère de rétention de feature | S | `stabilite()` ne teste aujourd'hui que la cohérence **entre cibles**, pas entre **périodes**. G7 l'a montré à la main | à câbler |
| Q3 | **`rr_dispo`** : IC −0,0592 vs `y_r_long`, signe instable, sur une variable **tronquée par sa propre porte** | M | un des filtres les plus contraignants pourrait sélectionner **contre** le rendement. Demande un traitement de biais de sélection, pas un IC de rang | non conclu |
| Q4 | **Ablation `s_sr` + `s_patterns`** (question G3) | S | deux scores sur cinq tirent à l'envers avec un poids positif | question ouverte |
| Q5 | **B4** — posterior bayésien de l'espérance, Kelly, risque de ruine | S | annoncé dans la routine cloud du 08/08, qui **n'a rien livré** | **toujours à faire** |
| Q6 | **B7** — dépendance de queue des 4 paires | M | le nombre réel de paris indépendants (~1,2, pas 4) conditionne tout dimensionnement | ouvert |
| Q7 | **B13 / D2** — walk-forward, ancré, **purgé et avec embargo** | M | prérequis du dry-run depuis juillet, jamais fait. D2 (5 seuils macro) est le plus urgent de la liste D depuis l'abandon de D1 | ouvert |
| Q8 | **B11** (HAR-RV vs ATR, QLIKE + Diebold-Mariano) et **B12** (stops fractionnaires, frais inclus) | M | critères de passage/abandon déjà écrits en vague 2 | ouverts |
| Q9 | **Deflated Sharpe / PSR** + référence **buy-and-hold** imposée à toute candidate | S | décision du 12/08 : « ce qui ne bat pas le hold ne mesure pas un edge, il mesure le marché ». Sans ça, F1 couronnera la plus exposée | à imposer avec F1 |
| Q10 | Étendre le **modèle nul B1 par régime** (macro, volatilité) | S | E[R] nul = −0,0123 long / −0,0370 short **en moyenne** ; par régime, la référence change | extension |

---

## Ce que cette section change dans l'ordre des priorités

1. **Q1 (rareté des entrées)** passe devant B13/D2 et devant tout le ML. C'est la question G4.
2. **H4 (ML gestion) est bloqué par un bug de journal, pas par la méthode** : `_journal_exit`
   n'est déclenché que par `order_filled` quand `not trade.is_open`, condition **jamais remplie**.
   Tant qu'il n'y a pas un seul `exit`, le chantier « gestion » n'a aucune cible à apprendre.
3. **B6 est le dernier verrou méthodologique** et il bloque désormais **deux** chantiers, pas un :
   F1/H7 (banc) **et** H1 (boucle). C'est le prochain à fermer.
