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
> D2-D4, E2/E3/E4, **F2** (F1 → BETA), G1-G3 (**G4 tranché 20/08**), H1-H6/H8/H9 (**H7 → BETA**),
> Q1-Q3/Q5-Q8/Q10 (**Q4 fermée 20/08**) + **Q11a-e** (F&G adaptatif) et **Q12** (raison de refus),
> ouverts le 20/08
> (**Q9 → BETA**). ⚠️ **Frontière ARIT / BETA : § MISE À JOUR DU 2026-08-19, en bas de fichier.**
> Un chantier de comparaison de stratégies n'est plus suivi ici.

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
| ~~A5~~ | ~~Véto macro HOSTILE **seul**~~ | ✅ **FERMÉ 18/08** — acté sans code, puis mesuré : **INDÉCIDABLE** (`research/ablation_A5/RAPPORT.md`) | 7 signaux marginaux en 5 ans, MDE +1,53 R : la porte macro n'est pas mesurable à ce N | 17/07 |
| ~~A6~~ | ~~Sizing : risque **constant**~~ | ✅ appliqué (1,16 %) | un sizing justifiable | 31/07 |
| ~~A7~~ | ~~Choisir l'hypothèse d'edge de remplacement~~ | ✅ **FERMÉ** — signée 04/08 (`docs/01` v4) | tout le reste — c'était le point 1 de la liste E | 19/07 |
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

| # (liste du 04/08) | Bloquant | Statut (07/08, révisé le 18/08) |
|---|---|---|
| 1 | Parité backtest/live rompue par A2 | **FERMÉ** — `macro_state` écrit les 5 scores 06.2, `macro_regime.attach_regime_now()` pose le régime en live, fail-safe `regimes.donnee_non_fiable` |
| 2 | ~~Données OHLCV futures manquantes~~ | ✅ **FERMÉ 18/08** — le statut « seul BTC en 4h/5m » était périmé. Vérifié au bit près en construisant le lake BETA : les **4 paires** ont 5m/1h/4h/1d, **100 % de couverture**, 0 bougie manquante (BTC 2019-09, ETH 2019-11, BNB 2020-02, SOL 2020-09 → 2026-08-04). Ne bloque plus les backtests. ⚠️ `check_bias.py` n'a pas été relancé depuis : les données ne manquent plus, mais le passage du contrôle reste à vérifier |
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
| ~~F1~~ | **Banc d'essai de stratégies** — un module qui fait tourner d'autres stratégies que AritV1 sur le même protocole, pour comparer les rendements et **diversifier les formes d'investissement** (mean-reversion, portage/funding, macro seule, spot vs perp) | Jonas, 12/08 | ~~déposé, non tranché~~ → ✅ **FERMÉ ICI le 19/08** (statut périmé) — **acté le 18/08, devenu le projet BETA** | chantiers suivis dans `C:\Users\jofar\BETA\CHANTIERS.md`, plus ici · arbitrages : `C:\Users\jofar\BETA\DECISIONS.md` |
| F2 | **Observabilité à distance du dry-run** — aujourd'hui nulle : FreqUI est sur `127.0.0.1`, toutes les traces sont gitignorées, et le seul signal distant est l'absence d'alerte Discord (qui ne distingue pas « bot sain » de « session Windows fermée »). Pistes : bot **Telegram natif** de freqtrade (`/status`, `/profit`, `/daily`, aucun port ouvert) — c'est aussi ce que M09 devait apporter — ou **Tailscale / Cloudflare Tunnel** (FreqUI reste sur `127.0.0.1` et devient joignable sans exposition publique). ❌ **Jamais** `listen_ip_address: 0.0.0.0` + redirection de port : l'API porte `/forceexit`, `/forcebuy`, `/stop` | Jonas, 12/08 | **déposé, non tranché** | cette ligne porte la substance ; voir aussi `DECISIONS.md` § G2 et § G8 |

❌ **PARAGRAPHE PÉRIMÉ — corrigé le 2026-08-19.** Les trois prérequis (B2, B5, B6) sont
**fermés au 18/08**, et les OHLCV futures sont **complètes sur les 4 paires** (100 % de
couverture, 0 bougie manquante, vérifié au bit près en construisant le lake BETA). Il ne
reste donc **aucun verrou** devant le banc, ni méthodologique ni matériel. Texte d'origine
conservé pour la trace :

> ⚠️ F1 a trois prérequis non négociables, écrits dans `DECISIONS.md` : B2 (correction
> Benjamini-Hochberg), B5 (hold-out scellé), B6 (`EXPERIMENTS.jsonl`). Un banc d'essai sans
> budget de tests déclaré est une machine à fabriquer du bruit statistiquement gagnant.
> Ces trois-là sont précisément le périmètre de la **routine cloud vague 1** armée le 08/08 :
> F1 se branche derrière elle. Second frein, matériel celui-là : les OHLCV futures manquent
> pour 3 paires sur 4, donc un banc lancé aujourd'hui comparerait les candidates sur BTC seul
> — la paire la plus perdante du run du 04/08.

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

**F1 est ouvert depuis le 18/08 et vit désormais dans son propre dépôt** :
`C:\Users\jofar\BETA` (projet **BETA**). Ses chantiers ne sont plus suivis ici mais dans
`BETA\CHANTIERS.md`, pour ne pas dupliquer un statut à deux endroits — la duplication de
statuts est précisément ce qui a déjà fait recompter des lignes fermées comme ouvertes.

Ce qui est **livré** : lake OHLCV (6 paires, 24 séries, 100 % de couverture), données de
stratégie (79 trades, 3 151 évaluations), protocole expérimental, dashboard.
Ce qui **manque, et qui est le cœur du banc** : le **moteur** (bloc M), la **batterie
multi-test** (bloc S — BH, DSR, bootstrap par blocs, Monte-Carlo, CPCV, Reality Check,
buy-and-hold, corrélation des équity) et la **recherche d'edge** (bloc R, 6 hypothèses déjà
identifiées). Arbitrages : `BETA\DECISIONS.md` (sortis de `DECISIONS.md` le 19/08).

⚠️ **H7 (banc multi-stratégie) est donc BETA**, et ne se code plus dans ce dépôt.

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
| ~~H7~~ | **Banc multi-stratégie** | ✅ **FERMÉ ICI le 19/08** — = F1, projet BETA depuis le 18/08 | ne se code plus dans ce dépôt : `BETA\CHANTIERS.md`, blocs M / S / R |
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
| Q9 | **Deflated Sharpe / PSR** + référence **buy-and-hold** imposée à toute candidate | S | décision du 12/08 : « ce qui ne bat pas le hold ne mesure pas un edge, il mesure le marché ». Sans ça, F1 couronnera la plus exposée | ~~à imposer avec F1~~ → ✅ **FERMÉ ICI le 19/08**, migré chez BETA : S2 (Sharpe dégonflé) + S8 (buy-and-hold) |
| Q10 | Étendre le **modèle nul B1 par régime** (macro, volatilité) | S | E[R] nul = −0,0123 long / −0,0370 short **en moyenne** ; par régime, la référence change | extension |

---

## Ce que cette section change dans l'ordre des priorités

1. **Q1 (rareté des entrées)** passe devant B13/D2 et devant tout le ML. C'est la question G4.
2. **H4 (ML gestion) est bloqué par un bug de journal, pas par la méthode** : `_journal_exit`
   n'est déclenché que par `order_filled` quand `not trade.is_open`, condition **jamais remplie**.
   Tant qu'il n'y a pas un seul `exit`, le chantier « gestion » n'a aucune cible à apprendre.
3. **B6 est le dernier verrou méthodologique** et il bloque désormais **deux** chantiers, pas un :
   F1/H7 (banc) **et** H1 (boucle). C'est le prochain à fermer.


---

# MISE À JOUR DU 2026-08-19 — frontière ARIT / BETA

Ce qui a déclenché cette section : ALPHA comptait **24 décisions en attente** sur ARIT — 11 dans
`DECISIONS.md`, 13 ici. Après déduplication il en reste **21**, dont **8 seulement attendent une
réponse de Jonas**. Les 3 lignes de trop étaient des doublons ou des statuts périmés : **F1**
compté deux fois et resté « déposé, non tranché » alors qu'il est acté depuis le 18/08, et
**G3 = Q4**. Corrigés en place plus haut.

## La règle, en une phrase

> **ARIT2.0 = la stratégie qui tourne. BETA = la recherche d'autres stratégies.**
> Un chantier qui porte sur **AritV1** (ses portes, ses scores, sa gestion, son dry-run, son
> observabilité) reste ici. Un chantier qui porte sur **la comparaison de plusieurs candidates**
> (moteur de criblage, batterie multi-test, hypothèses d'edge) est chez BETA.
> **Aucun statut ne vit aux deux endroits** : le dépôt propriétaire fait foi, l'autre ne porte
> qu'un pointeur. C'est exactement la duplication de statuts qui a déjà fait recompter des
> lignes fermées comme ouvertes.

| Ligne | Avant | Depuis le 19/08 |
|---|---|---|
| **F1 / H7** — banc d'essai | « déposé, non tranché » | **BETA** — blocs M (moteur), S (multi-test), R (recherche d'edge) |
| **Q9** — Deflated Sharpe + buy-and-hold | « à imposer avec F1 » | **BETA** — S2 et S8 |
| **Q7** — walk-forward purgé + embargo | ouvert | **reste ici** (B13/D2, pour AritV1). BETA S6 est le même outil appliqué aux candidates : deux travaux, deux dépôts, à ne pas fusionner |
| **G3 / Q4** — ablation `s_sr` + `s_patterns` | compté deux fois | **reste ici** ; `DECISIONS.md` § G3 fait foi, Q4 n'est que sa ligne de chantier |
| **F2** — observabilité du dry-run | ouvert | **reste ici** (avec G2 et G8) : c'est le bot en production, BETA ne tourne pas en live |
| **C1-bis** — palier orange / `news_window` | à trancher | **reste ici** (paramètre d'AritV1), mais BETA **R6** mesure ce que cette porte bloque. La mesure informe la décision, elle ne la prend pas |

## Ce que BETA a trouvé et qui est un chantier ARIT

| # | Dette | Détail | Statut |
|---|---|---|---|
| **T4-ARIT** | **`ts_utc` ment sur les événements `gestion`** | `ev_gestion()` (`user_data/strategies/arit_lib/journal.py:353`) ne pose pas de `ts_utc` ; `write()` retombe alors sur `_now_iso()` (`journal.py:199`), c'est-à-dire **l'heure d'exécution du backtest**, pas celle de la bougie. `ev_signal()` et `ev_exit()`, eux, posent la bonne date (`open_date` / `close_date`). BETA contourne par `signal_id` (sa dette T4), mais **la correction appartient à ARIT** : tout nouveau consommateur du journal retombera dedans, et l'interdit n° 6 (chaque évaluation journalisée) suppose une date juste | 🔴 ouvert |

---

# MISE À JOUR DU 2026-08-20 — quatre décisions tranchées par Jonas

## G4 — l'ORDRE EST VALIDÉ (Jonas, 20/08) : « tu as mon accord »

L'ordre proposé le 12/08 devient l'ordre de travail. Il sort de `DECISIONS.md` (plus rien à
trancher) et fait foi ici :

> **1. H5 — le quantitatif, en commençant par Q1 · 2. H2 — ML au CIO · 3. H1 — la boucle, en
> dernier.**

Motif, inchangé et re-vérifié : le goulot n'est pas la qualité de l'entrée mais sa **rareté**
(78 signaux en 5 ans, 0,16 % des évaluations). Aucun modèle, aucun walk-forward, aucune boucle
ne conclut sur 78 observations. Et une boucle branchée avant le compteur d'essais est une
machine à fabriquer du bruit gagnant.

⚠️ Cet ordre porte sur **H1-H9**. Il ne préempte pas le diagnostic gestion short (le −0,53 R du
18/08), qui est un **bug de mesure et de journal** avant d'être un chantier de recherche —
il passe devant tout, parce qu'il ne coûte presque rien.

## A2-quater — APPLIQUÉ le 20/08 : le véto actions c6/c7 devient un filtre directionnel

Jonas : « A2 filtre directionnel ». Le véto forçait `RISK_OFF` — il interdisait les **deux**
sens. Il retire désormais le **long** seul, et laisse le short (PORTEUR ⇒ aucune entrée,
NEUTRE ⇒ short seul, HOSTILE ⇒ inchangé). Le véto ne crée jamais un short que la macro ne donne
pas. Spec : `docs/06 §6.2.1`. Code : `cio.direction_macro` + `regimes._classify_macro`.
Tests : +8 (426 passed). Équivalence côté long verrouillée par un test dédié.

⚠️ **La distinction qui est le cœur du travail** : `equity_veto_stale` (série périmée) reste un
**coupe-circuit** `RISK_OFF`. Ce n'est pas un avis de marché mais un doute sur la donnée, et
**une donnée absente ne donne jamais de direction** — même règle que `donnee_non_fiable`.
Le véto de corrélation vit maintenant dans `cio`, le véto de donnée reste dans `regimes`.

## A2-quinquies — ACTÉ : F&G adaptatif (niveau + dynamique). Nouveau chantier `Q11`

| # | Sous-chantier | Effort | Statut |
|---|---|---|---|
| **Q11a** | **Poser `fear_greed` en colonne quotidienne** (via `attach_macro_regime`, décalage +1 j) | S | **prérequis absolu** — aujourd'hui `_classify_macro` injecte `FG_NEUTRAL_BACKTEST = 50` en dur : le F&G **n'existe pas en backtest**, aucune règle F&G n'est mesurable |
| **Q11b** | **Sortir F&G < 25 de `regimes.donnee_non_fiable()`** | S | le code confond « donnée cassée » et « marché apeuré ». Tant que le F&G vit dans le fail-safe, il ne *peut pas* devenir directionnel. C'est le vrai travail |
| **Q11c** | `fetch_fear_greed()` → `limit=N` (aujourd'hui `data[0]` seul) | S | sans historique en live, pas de delta ⇒ règle valide en backtest et morte en live : **rupture de parité**, le bloquant n° 1 déjà payé une fois |
| **Q11d** | Re-télécharger `fear_greed.json` (figé au 03/08/2026, 3 103 points depuis 2018-02) | S | `scripts/download_macro.py fng` |
| **Q11e** | Règle des deux temps + préenregistrement (B6) | M | 3 paramètres attendent Jonas : amplitude/fenêtre du retournement, symétrie baissière, et « lever le blocage » vs « ajouter de la conviction ». Détail : `DECISIONS.md § A2-quinquies` |

## G3 / Q4 — ACTÉ : l'ablation de `s_sr` + `s_patterns` se fait

`Q4` passe de « question ouverte » à **acté le 20/08, mesure à faire**.

⚠️ **Piège arithmétique vérifié le 20/08, à lire avant de mesurer** : `POIDS` somme à 1,00.
Retirer les deux scores sans renormaliser plafonne la conviction à **0,70 × multiplicateur**
alors que le seuil TRANSITION vaut 0,65 et le multiplicateur 0,85 ⇒ **0,595 : plus aucun signal
possible en TRANSITION**. L'ablation brute mesurerait un durcissement de seuil, pas un retrait de
scores. Renormaliser les 3 poids restants à somme 1 (rapports inchangés, donc pas une hyperopt).
L'IC est **invariant** par cette renormalisation ; le backtest y est **très sensible**.

## Dette découverte le 20/08 — le verrou B6 est cassé

| # | Dette | Détail | Statut |
|---|---|---|---|
| **T5-ARIT** | **`test_experience_reelle_est_preenregistree` échoue** (`KeyError: 'split_autorise'`) | L'entrée du registre `research/EXPERIMENTS.jsonl` ne porte pas la clé que le test — et le verrou matériel de B6 — exigent. Échec **antérieur au 20/08** (vérifié par `git stash`), donc présent depuis la fermeture de B6 le 18/08. Le préenregistrement est le garde-fou anti-p-hacking de **trois** chantiers actés : G3/Q4, Q11e et l'hypothèse short/trailing | 🔴 ouvert — **à réparer avant toute mesure préenregistrée** |

## 20/08 (suite) — T5-ARIT réparé, et Q4 mesurée

**T5-ARIT — FERMÉ le 20/08.** Le verrou B6 était ouvert depuis sa propre fermeture le 18/08.
Règle en cause : « la DERNIÈRE ligne de cet id fait foi » — dès qu'une expérience était close,
`preenregistrement()` renvoyait la ligne de **résultat**, qui ne porte ni `split_autorise` ni
`variantes`. Le test échouait (`KeyError`), mais le vrai dégât est ailleurs : **le script
relancé après clôture tournait avec un garde-fou vide**. Le verrou censé empêcher le p-hacking
s'ouvrait précisément après la première mesure.

Corrigé en séparant les deux natures de ligne : le **protocole** (statut `preenregistre`, seul
à porter les garde-fous ; un amendement = une nouvelle ligne `preenregistre`, la dernière fait
foi) et le **résultat** (`clos`, `mesure`), qui n'amende jamais un protocole. Deuxième refus
ajouté : une expérience **close** ne se remesure pas — rejouer jusqu'au bon résultat est du
p-hacking par répétition, une nouvelle mesure exige un nouvel id, donc un essai de plus au
compteur cumulé. Le verrou vit désormais dans `analysis/registre.py`, partagé (il sert à Q4,
Q11e et short/trailing) ; `ablation_macro.py` le ré-exporte. +6 tests, 432 passed.

**`Q4` — FERMÉ le 20/08 : mesurée, ablation RETENUE sur la métrique primaire.**
Préenregistrée puis close (essais cumulés **50**) · `research/ablation_Q4/RAPPORT.md` ·
code `analysis/ablation_scores.py`.

| | IC production | IC ablaté (renormalisé) | ΔIC | IC bootstrap 90 % |
|---|---|---|---|---|
| long | 0,0642 | **0,0848** | **+0,0205** | [0,0135 ; 0,0275] |
| short | 0,0357 | **0,0544** | **+0,0187** | [0,0115 ; 0,0260] |

Les trois conditions préenregistrées sont remplies dans les deux sens. `s_sr` porte les trois
quarts de l'effet. **Le chiffre qui résume tout** : IC(ablaté) = 0,0848 contre **0,0851** pour
`s_structure` **seul** (B9) — l'agrégation à cinq termes détruisait exactement ce que ses deux
termes à IC négatif y injectaient. L'ablation ne fait pas mieux que le meilleur score isolé,
elle le **rejoint**.

⚠️ **Le piège arithmétique est confirmé empiriquement** : l'ablation brute (sans renormaliser)
ne laisse que **5 signaux long sur 50** et 8 short sur 28. Elle aurait mesuré un durcissement
de seuil, pas un retrait de scores.

⚠️ **Ce qui reste ouvert, et qui appartient à Jonas** (`DECISIONS.md § G3`) : l'ablation coûte
**44 % des signaux longs** et 21 % des shorts, alors que le goulot n° 1 est la **rareté des
entrées** (Q1, désormais en tête des priorités). Appliquer maintenant, ou attendre Q1 pour
savoir de combien desserrer les portes en compensation ? Reco : **attendre Q1** — un seuil
abaissé sur mesure peut rendre les 22 signaux perdus sans réintroduire les scores à IC négatif.

Réserves préenregistrées, maintenues : le gain d'IC **ne se lit pas** dans les 22 trades
effectivement perdus côté long (+0,0828 R contre un noyau à −0,1964 R), mais c'est indécidable
à ce N (MDE 0,825 R) ; et le noyau conservé reste à **−0,1964 R** — améliorer un IC ne crée pas
un edge.

---

# MISE À JOUR DU 2026-08-20 (soir) — A2-quater rouvert, mesuré, et deux chiffres corrigés

## Où en est l'ordre G4, validé le matin même

**Rien n'a démarré.** L'ordre est acté (H5 → H2 → H1), mais **Q1 n'est pas ouvert** : aucun
fichier dans `analysis/`, aucune courbe N(seuil). Les livraisons du 20/08 (A2-quater,
T5-ARIT, Q4) sont toutes *antérieures* à l'ordre ou orthogonales à lui. Le premier travail
de la prochaine session reste donc **Q1**, et il est réclamé par deux décisions ouvertes
à la fois : **G3** (de combien desserrer pour compenser l'ablation ?) et **A2-sexies**
(peut-on se permettre de perdre 19 % des entrées ?).

## A2-quater rouvert par Jonas — devenu A2-sexies

Jonas, 20/08 : « pas du tout ce que je voulais, je voulais un **filtre décisionnel** pas une
**interdiction de long** », et il écrit la règle qu'il veut (concordance `macro ∧ technique`,
sinon journal seul). Arbitrage : `DECISIONS.md § A2-sexies`.
Décompte descriptif : `research/regle_direction/RAPPORT.md`, code `compte_variantes.py`
(train seul, hold-out non lu ; **aucune p-value, aucun verdict** — les N sont de l'ordre de
la dizaine).

**Ce que la mesure a montré, et qui n'était pas prévisible :**

| Constat | Chiffre |
|---|---|
| **A2-quater n'a déplacé aucun trade** — le véto actions directionnel couvre 2 298 lignes du train, **aucun signal technique ne tombe dessous** | 0 long, 0 short. Décompte avant/après **identique** : 50 longs, 28 shorts |
| Les 3 façons de rendre le véto « décisionnel » (le laisser, le dégrader d'un cran, le forcer HOSTILE) | **même décompte**, au trade près |
| La concordance stricte (NEUTRE ⇒ rien) | **78 → 63 signaux (−19 %)**, tous perdus en macro NEUTRE |
| Les 9 shorts en macro NEUTRE — ceux que la règle stricte supprimerait | **+0,4978 R** de moyenne, **seul groupe nettement positif du lot** (⚠️ n = 9, indécidable) |
| Les 7 shorts techniques en macro PORTEUR, bloqués par la porte macro | −0,2286 R : la porte macro **fait son travail** sur ce sous-groupe |
| Régime technique des 78 signaux | **100 % TREND, zéro TRANSITION** — le seuil 0,65 n'est jamais atteint en cinq ans. À verser à **Q1** |

⇒ Le désaccord porte sur un bloc **inerte dans les données**. Une seule vraie question reste :
**que fait la macro NEUTRE** (les deux sens, ou rien) ? Elle est dans `DECISIONS.md`.

## Q12 — raison de refus structurée dans le journal (nouveau chantier, aucun arbitrage)

| # | Sous-chantier | Effort | Pourquoi |
|---|---|---|---|
| **Q12** | `AritV1._journal_evaluation` écrit `decision: no_signal` avec pour raison **le régime technique** (`row.get("regime")`), **pas le motif du refus** | S | Le `else: enregistrement des raisons` de la règle de Jonas est le **seul morceau de sa spec absent du code**. Aujourd'hui le journal ne distingue pas « macro discordante » de « conviction insuffisante » ou « RR manquant » |

C'est **exactement** le manque qui a rendu R6 non mesurable chez BETA : il a fallu
reconstruire les populations à la main pour découvrir que `news_window` ne séparait rien.
Q12 ne change aucun trade, ne demande aucune décision, et rend mesurable tout ce qui suit —
**Q1 le premier**, qui a besoin de savoir *quelle porte* a refusé pour tracer N(seuil) porte
par porte.

## Deux chiffres à ne plus citer tels quels

1. **« `news_window` bloque 91,75 % de tout ce qui est rejeté (756 signaux sur 824) »** —
   FAUX comme énoncé. BETA R6 (19/08) : ce sont **756 lignes de journal**, soit **63 signaux
   distincts** (≈ 13 `gate_check` par signal, dette T4), dont **53 sont acceptés ailleurs de
   toute façon**. La porte **retarde** un signal, elle ne l'élimine pas. ⚠️ **C1-bis ne doit
   pas être tranchée sur ce chiffre.**
2. **« Le F&G n'existe pas en backtest »** (écrit le 20/08 au matin dans `DECISIONS.md`) —
   trop absolu. `macro_regime._score_fear_greed` en fait le composant **c5** du régime
   (< 25 ⇒ −1, ≥ 45 ⇒ +1) depuis `fear_greed.json` : le F&G **pèse déjà** sur
   PORTEUR/NEUTRE/HOSTILE en backtest. Ce qui manque est sa **valeur brute en colonne** (donc
   tout delta) et le **coupe-circuit**, lui bien neutralisé par `FG_NEUTRAL_BACKTEST = 50`.
   Q11a reste juste, sa justification était fausse. Plan de code complet des 5 étapes :
   `DECISIONS.md § A2-quinquies`.

---

# MISE À JOUR DU 2026-08-20 (nuit) — sept arbitrages de Jonas, et quatre chantiers qu'ils ouvrent

Session de tri des décisions. Arbitrages détaillés : `DECISIONS.md`. Ce qui suit est ce qu'ils
laissent **à faire**.

## Ce que Jonas a tranché

| # | Décision | Effet ici |
|---|---|---|
| **A2-sexies** | (a) — la macro **NEUTRE garde les deux sens** | statu quo, **rien à coder**. Les 78 signaux restent 78 |
| **A2-quinquies** | **P1, P2 et P3 validés** : +15 pts / 1 j · symétrie · lever le blocage seulement | **Q11a-e passent de « acté sans spec » à codables** |
| **A2-ter** | levier reste à **1** | ⚠️ le raisonnement de Jonas (« SL serré ⇒ conviction faible ») est faux — la vraie raison est Kelly (`DECISIONS.md`). Ouvre **Q14** |
| **C1-bis** | le palier binaire devient un **barème de points** (rouge 3, autres 1) | **3 paramètres à fixer**, et ⚠️ **non mesurable en backtest**. Ouvre **Q15** |
| **G1** | ML **reporté**, reste une hypothèse | rien à coder ; `H2` reste documenté, non ouvert |
| **A8** | reporté, re-confirmé (« des G-rules fixes me semblent dangereuses ») | inchangé |
| **G2** | **le suivi à distance part chez BETA** | ⇒ voir « frontière » ci-dessous |
| **C1-ter** | **supprimée** de `DECISIONS.md` sur sa demande | la connaissance atterrit ici, ligne ci-dessous |

## C1-ter, recueillie ici puisqu'elle quitte DECISIONS.md

**Échéance fin 2026 : saisir les dates CPI/NFP 2027** dans
`user_data/calendar/economic_calendar.json`. Le BLS publie son calendrier annuel fin 2026.
Sans cette saisie, la couverture CPI/NFP retombe sur ForexFactory, **qui ne voit que la semaine
en cours** — un CPI à J+20 n'est connu de personne. `coverage_gaps()` le signalera en `ERROR` à
chaque run. ⚠️ `bls.gov` refuse toute récupération automatisée (403) : **saisie manuelle**,
publication 08:30 US Eastern.

## Frontière ARIT / BETA — G2 la déplace, volontairement

Le 19/08, la règle disait : « **F2 / G2 / G8** restent chez ARIT (le dry-run ne tourne que
là) ». Jonas la révise le 20/08 : « intègre le suivi à distance dans le projet BETA si
possible, sinon dans un autre dashboard, mais **il faut pouvoir suivre ça sans avoir accès au
PC** ».

⇒ **L'observabilité (F2 + la moitié « suivi » de G2) devient un bloc `O` chez BETA**
(`BETA/CHANTIERS.md`). Ce qui **reste ici** : la **relance** du dry-run elle-même et sa survie
aux redémarrages — c'est-à-dire le bot, pas sa fenêtre. La frontière n'est pas cassée, elle est
précisée : **ARIT produit les événements, BETA les affiche.** BETA continue de ne jamais écrire
dans `ARIT2.0`.

⚠️ Le défaut à ne pas reproduire est déjà connu : `services/watchdog.py` alerte si le heartbeat
est muet > 10 min, **mais il meurt avec la session Windows**. Un dashboard hébergé sur la même
machine hérite exactement du même angle mort — **le silence y est indiscernable de la santé**.
Tant que le VPS (G8) n'existe pas, le seul suivi distant honnête est un **push sortant**
(Discord), avec un signal de vie **positif** et périodique, jamais une page à consulter.

## Les quatre chantiers ouverts par ces arbitrages

| # | Chantier | Effort | Pourquoi, et ce qui le déclenche |
|---|---|---|---|
| **Q13** | **Balayage du couple (distance de stop, cible) en espérance NETTE** — `k` de 0,3 à 1,0 par pas de 0,05 | M | **Le plus important des quatre.** Jonas : « le système n'est pas rentable de base ». C'est exact et déjà chiffré : à `k = 1` (réglage actuel) **E nette = −0,072 R**, à `k = 0,5` **+0,158 R** (`frais et distance de stop.md`). Les frais en R varient comme `1/k`. **La grille n'a que 3 points, rien entre 0,5 et 1,0**, et le balayage est gratuit (`analysis/replay_entries.py` existe). ⚠️ Balayer distance **et** cible ensemble : séparément on rate l'optimum |
| **Q14** | **Journaliser le plafonnement du stake** | S | Quand la distance de stop est serrée, `stake = equity × risk_pct / dist_frac` dépasse l'équité, freqtrade plafonne, et le risque réel tombe **sous** 1,16 % **sans le dire**. Prérequis de Q13 : on ne peut pas mesurer un stop plus serré si le sizing décroche en silence quand il se resserre |
| **Q15** | **Calendrier économique historique** | M | Sans lui, ni le palier orange ni le barème de points de C1-bis ne sont mesurables : `macro_state.json` ne contient que les événements **à venir**, donc en backtest **la porte news passe toujours**. Même nature de trou que Q11a pour le F&G |
| **Q12** | *(ouvert plus haut le 20/08)* raison de refus structurée dans le journal | S | inchangé — c'est le `else` de la règle de Jonas |

**Ordre proposé** : **Q14 → Q13** (Q14 est un prérequis de Q13 et coûte une heure), puis **Q1**.
Q13 et Q1 répondent tous deux à « le système n'est pas rentable » — Q1 dit *combien* de signaux
on peut avoir, Q13 dit *combien vaut* chacun — et **Q13 est le seul des deux à avoir déjà un
chiffre positif en face de lui**.

⚠️ **Q13 n'est pas une hyperopt**, et la distinction doit être écrite avant de le lancer :
balayer une grille pour **tracer une courbe d'espérance nette** est une mesure ; choisir le `k`
qui maximise le backtest et le figer en production est une optimisation. Le premier se
préenregistre (B6) avec sa règle de décision ; le second tombe sous l'interdit n° 5.

## 20/08 (nuit, suite) — Q14 livré, Q13 mesurée et INFIRMÉE, dette T6-ARIT

**`Q14` — FERMÉ.** `risk.plafonnement_stake()` rend visible le clamp silencieux de freqtrade :
quand le stop est serré, `stake = equity × risk_pct / dist_frac` dépasse `max_stake`, freqtrade
plafonne, et le risque réel tombe **sous** 1,16 % sans que rien ne le dise. La fonction ne
corrige pas (freqtrade plafonnera de toute façon), elle **journalise** — `contracts.STAKE_CAP_KIND`.
+6 tests, **438 passed**.

**`Q13` — FERMÉ le 20/08 : mesurée, hypothèse INFIRMÉE dans les deux sens.**
Préenregistrée puis close (essais cumulés **51**) · `research/balayage_Q13/RAPPORT.md` ·
code `analysis/balayage_stop.py`.

| Sens | n | E nette k = 1,00 | E nette k = 0,50 | Δ | IC 90 % | MDE |
|---|---|---|---|---|---|---|
| long | 50 | −0,3943 R | −0,4914 R | −0,0972 | [−0,3164 ; +0,1337] | 0,4003 |
| short | 38 | −0,3299 R | −0,9741 R | **−0,6441** | **[−0,9443 ; −0,3674]** | 0,5102 |

**Resserrer le stop DÉGRADE l'espérance nette**, l'inverse de l'hypothèse — et côté short l'IC
exclut zéro du mauvais côté. Les **150 cellules** de la grille (15 `k` × 5 cibles × 2 sens) sont
**négatives** ; la meilleure est à −0,1714 R, lue après coup sur 150, donc citée pour la forme
et pas comme un résultat.

### Le chiffre à retenir de tout le chantier

> **Le coût aller-retour vaut 0,3207 R (long) et 0,4147 R (short) à la distance structurelle.**
> Un tiers à 40 % d'un R part en frais et slippage **avant qu'on ait parlé d'edge**.

La distance de stop médiane des signaux longs est de **1,54 %**, avec une queue descendant à
**0,07 %**. Comme le coût vaut `2 × (frais + slippage) / distance`, la moyenne est gouvernée par
`E[1/distance]` : **une poignée de signaux à stop ultra-serré tire tout le coût**. ⇒ Le problème
n'est pas le *niveau* des distances de stop, c'est leur **dispersion**.

⚠️ **Contrôle de cohérence passé avant lecture** : E brute reconstituée à `k = 1` côté long
= **−0,0736 R**, identique au chiffre mesuré indépendamment le même jour
(`research/regle_direction/RAPPORT.md`). La simulation reproduit la production au chiffre près.

### La note du vault se falsifie elle-même, proprement

`trading/frais et distance de stop.md` annonçait −0,072 R à k=1 et **+0,158 R à k=0,5**, et
**réclamait ce balayage** (« une décision prise sur une grille de 3 points n'est pas une
optimisation, c'est un sondage »). Le sondage complet dit l'inverse. Deux causes, aucune n'étant
une faute de la note : substrat différent (campagne edge 2026-07, 128 trades, macro neutralisée)
et **coût sous-estimé d'un facteur ~3,7** (0,0875 R supposé, **0,32 R** mesuré signal par signal).
La variante qu'elle décrivait vraiment — cible en **prix** inchangée, soit (k=0,5 ; cible 3,0 R) —
rend −0,3614 R contre −0,3943 : **+0,033 R, sous tout MDE**.

### Nouvelle dette

| # | Dette | Détail | Statut |
|---|---|---|---|
| **T6-ARIT** | **`FEE_TAKER_FRAC` est le taux SPOT** | `params.py:73` — `0.001  # Binance spot 0,1 % taker`, alors que le bot est en **futures** depuis A2 (`config.dry.json: "trading_mode": "futures"`), où le taker USDⓈ-M vaut **0,05 %**. Portée : **freqtrade utilise sa propre config**, donc backtests et live ne sont pas faussés ; mais la constante sert de fallback de journalisation (`AritV1._journal_exit`) et de source à **toute mesure hors ligne**, qui surestiment donc les frais d'environ 30 %. ⚠️ Le verdict Q13 ne bouge pas, mais **une cellule passerait tout juste positive** ⇒ la re-mesure exige un **nouvel id** (`Q13-bis`), jamais une relance de Q13 (le verrou B6 le refuse, vérifié) | ~~🔴 ouverte~~ **✅ fermée le 24/08** |

### Ce que Q13 ouvre, et qui n'existait pas ce matin

1. **La piste « resserrer le stop » est fermée** pour l'univers de signaux actuel.
2. **Le levier est le coût lui-même**, avec trois entrées mesurables : corriger le taux (**T6**),
   passer en **maker** (0,02 % contre 0,05 % en futures), et **écarter les signaux dont la
   distance de stop est trop serrée pour être rentable** — un signal à stop de 0,2 % paie ~1,5 R
   de frais et **ne peut structurellement pas gagner**. Ce dernier point est une **porte**, elle
   se mesure comme Q1, et elle réduit le nombre de signaux : à arbitrer avec le goulot de rareté.
   ⇒ **`Q16` — porte de distance de stop minimale**, à préenregistrer.
3. **La cible mérite autant d'attention que le stop** : à `k` fixé, passer la cible de 1,0 R à
   2,5-3,0 R améliore l'espérance nette dans presque toute la grille (un TP plus lointain amortit
   un coût fixe sur un R plus grand). Piste **non préenregistrée**, à ne pas lire comme un
   résultat. ⇒ **`Q17` — balayage de la cible seule**, à préenregistrer.

## 24/08 — T6-ARIT fermée : le taux de frais passe du spot au futures

`params.FEE_TAKER_FRAC` : **0,001 → 0,0005** (Binance USDⓈ-M taker 0,05 %). `docs/03 §3.6` corrigé
dans la foulée. **438 passed**, aucun test ne dépendait de la constante.

**Portée exacte, pour ne pas se raconter d'histoire** : freqtrade utilise sa propre configuration
de frais, donc **aucun backtest ni run live n'était faussé**. La constante ne sert qu'à deux
choses : le **fallback de journalisation** de `AritV1._journal_exit` (quand `trade.fee_close` est
absent) et **toute mesure hors ligne** — `analysis/balayage_stop.py:70` en tête.

### Ce que ça déplace dans les chiffres de Q13, sans rien re-mesurer

Le coût aller-retour vaut `2 × (frais + slippage) / distance`. Seul le terme `frais` bouge, et le
slippage dépend de la paire (0,0005 BTC/ETH · 0,0010 SOL/BNB sur un univers de 4 paires) — le
facteur de correction est donc **borné**, pas unique :

| | mesuré avec le taux spot | facteur | **encadrement corrigé** |
|---|---|---|---|
| coût long | 0,3207 R | ×2/3 … ×4/5 | **0,214 → 0,257 R** |
| coût short | 0,4147 R | ×2/3 … ×4/5 | **0,277 → 0,332 R** |

⚠️ **Le verdict de Q13 ne bouge pas** : les 150 cellules restent négatives, la meilleure était à
−0,1714 R et regagne au mieux ~0,10 R. **Une cellule pourrait passer tout juste positive** — c'est
précisément pourquoi la re-mesure exige un **nouvel id `Q13-bis`** (préenregistrement neuf), jamais
une relance de Q13 : le verrou B6 le refuse, et lire la grille corrigée en cherchant la cellule qui
passe au-dessus de zéro sur 150 essais, c'est du p-hacking avec un habillage arithmétique.

**Et le chiffre à retenir survit intact** : même corrigé, **un cinquième à un tiers d'un R part en
frais et slippage avant qu'on ait parlé d'edge**, et la cause reste la **dispersion** des distances
de stop (médiane 1,54 % côté long, queue à 0,07 %), pas leur niveau. `Q16` (porte de distance de
stop minimale) garde donc tout son sens — c'est le seul des trois leviers de coût qui attaque
`E[1/distance]` plutôt que le numérateur.

⚠️ **Ce que T6 ne corrige pas** : `params.G1_BE_BUFFER_FRAC = 0.001` reste à 0,1 %. C'est
volontaire — la valeur couvre désormais **exactement** l'aller-retour taker futures (2 × 0,05 %),
donc elle est juste par accident après avoir été juste par construction. Y toucher serait modifier
une G-rule (interdit n° 5), pas payer une dette.

## 24/08 — backtest hors-échantillon juin→août 2026 : 1 trade en 84 jours

Rapport complet : `research/backtest_2026-06_2026-08/RAPPORT.html` (local, trade-par-trade).
Run `backtest-result-2026-08-24_16-28-20.zip` · 4 paires · `--timeframe-detail 5m`
`--enable-protections` · données OHLCV et macro rafraîchies le jour même (le `fear_greed.json`
figé au 03/08 est reparti à 3 123 points ⇒ **Q11d couvert de fait**).

⚠️ **La période est entièrement dans le hold-out scellé** (`HOLDOUT_DEBUT = 2025-01-01`, B5).
Tout ce qui suit est **descriptif**. Rien ici ne doit servir à choisir un seuil ou une règle :
les mesures de décision se font sur le train.

**Résultat : 1 trade, −13,31 USDT (−0,13 %), 0 long / 1 short, 0 signal rejeté**, pendant que le
marché faisait +10,5 %. Le résultat n'est pas la perte — 13 USDT sur 10 000 est du bruit — c'est
que le bot n'a pas *refusé* des signaux, il n'en a pas **eu**.

### L'entonnoir : le goulot est la conviction, pas le seuil

Rejeu hors-ligne (`analysis/dataset.py`) sur les 2 016 évaluations de la période :

| Porte | longs | shorts |
|---|---|---|
| direction macro autorisée | 42,9 % | 100 % |
| multiplicateur > 0 | 53,6 % | 53,6 % |
| véto equity ok | 86,9 % | 86,9 % |
| `rr_dispo >= 1,5` | 16,9 % | 17,2 % |
| **`conviction >= seuil`** | **0,60 %** | **1,49 %** |
| toutes ensemble | **0** | **1** |

> **Conviction médiane = 0,038 pour un seuil à 0,55 — un facteur 14.** Le p99 long (0,489) est
> encore *sous* le seuil TREND. Baisser le seuil revient à piocher dans une distribution qui n'a
> presque aucune masse au-dessus de 0,3. **Q1 garde son sens, mais ne suffira pas** : le problème
> est en amont, dans l'agrégation — exactement ce que Q4/G3 a mesuré (IC 0,0642 → 0,0848 en
> retirant deux termes).

**La rareté est structurelle, pas conjoncturelle** : la distribution de conviction du train et
celle de juin-août 2026 ont le **même p50 à la quatrième décimale** (0,0382). Au taux du train
(88/42 958) on attendait 4,1 signaux ; on en a 1, P(X≤1 | Poisson 4,1) ≈ 8,5 %. Bas, pas anormal.
Le seul vrai écart est côté long (0,60 % contre 2,13 %) : la macro n'a **jamais** été PORTEUR sur
la période et a interdit le long **57 % du temps**.

### Le trade unique : G2 divise le stop par 16 avant que le trade ait bougé

| Grandeur | Valeur | Distance à l'entrée |
|---|---|---|
| SL initial **structurel** (docs/03 §3.3) | 584,1424 | **0,553 %** |
| SL posé par **G2** au 1ᵉʳ appel de `custom_stoploss` | 581,1291 | **0,0343 %** |
| Prix de sortie (`trailing_stop_loss`, 55 min) | 581,13 | touché |
| TP1 / TP2 | 576,11 / 571,32 | 0,83 % / 1,65 % |

**G2 est la seule G-rule sans déclencheur.** `G1_TRIGGER_R = 1.0` et `G3_TRIGGER_R = 1.0` attendent
+1 R ; `gestion.py:165` fait `if active["G2"]:`, sans condition de MFE. Et la garde qui devrait
l'arrêter ne mord pas : `compute_sl` compare G2 à `current_sl = trade.stop_loss`, qui vaut
**1156,05** (`entry × 1,99`, le plancher `stoploss = -0.99`) — **face à 1156, tout resserre**. Le
SL structurel n'entre jamais dans la comparaison : dans `custom_stoploss`, le `floor` structurel
n'est renvoyé **que si** `compute_sl` rend `None`.

⇒ **`Q18` — G2 sans déclencheur, à mesurer sur le train** (préenregistrement B6 obligatoire) :
ablation de G2 seul, et variante « G2 comparé à `max(current_sl, initial_sl)` ». C'est le
**mécanisme** que le diagnostic du 18/08 cherchait (« ce n'est pas le signal, c'est la gestion »)
et que R1 chez BETA n'a pas pu trancher statistiquement (« le trailing détruit les shorts »,
+0,5272 R par short pour la barrière fixe, p = 0,0175, mort sous Benjamini-Hochberg).
⚠️ Le lien est une **lecture de code**, vraie indépendamment de l'échantillon ; l'**effet** ne
l'est pas et ne se mesure pas sur 1 trade.

### Décomposition de la perte : 74 % de frais

| Composante | USDT | en R | part |
|---|---|---|---|
| mouvement de marché (580,93 → 581,13) | −3,41 | −0,062 R | 26 % |
| **frais aller-retour (2 × 0,05 %)** | **−9,90** | **−0,181 R** | **74 %** |
| total | −13,31 | −0,243 R | 100 % |

0,181 R de frais **seuls, sans slippage** — le chiffre de Q13 sur un cas réel, et la mécanique
`coût = 2 × frais / distance` en pleine lumière : la distance de sizing valait 0,553 %.

### Q14 a servi dès son premier backtest

`stake_demandé = 20 767,54` (2,1 × l'équité) plafonné à **9 900** ⇒ risque réel **0,553 %** contre
1,16 % visé (ratio 0,477). Sur 1 trade sur 1, le plafonnement a mordu : ce n'est pas un cas limite.

### Contrôles passés

Rejeu hors-ligne et backtest freqtrade donnent **le même signal unique** · `fee_open = fee_close
= 0,0005` ⇒ **T6 ne faussait aucun run**, confirmé sur pièce · levier 1,0 · funding 0 (55 min).

### Deux dettes de journalisation ouvertes

| # | Dette | Détail | Statut |
|---|---|---|---|
| **T7-ARIT** | **`entry` journalisé deux fois par trade** | Deux événements pour le trade unique, avec deux stakes (9 620,20 puis 9 899,05) et deux quantités (16,56 / 17,04) — double appel `confirm_trade_entry` / `order_filled`. Toute analyse qui compte les `entry` comptera **double** et prendra le mauvais stake une fois sur deux | 🔴 ouverte |
| **T8-ARIT** | **`before` de l'événement `gestion` n'est pas rafraîchi** | `trade.stop_loss` vaut 1156,05 aux **12** appels, alors que le stop appliqué a changé (le trade sort à 581,13). Le `before` journalisé ne décrit donc pas le stop en vigueur ⇒ ne pas le lire comme tel. N'affecte pas le verdict ci-dessus (le prix de sortie tranche) | 🔴 ouverte |

## 24/08 — AUDIT COMPLET du code de production : 21 constats, dont 2 tueurs

Rapport : `research/audit_2026-08-24/AUDIT.html`. Périmètre relu intégralement : 5 698 lignes de
Python de production, les 22 fichiers `docs/`, 438 tests, 255 fichiers de journal, et un rejeu du
pipeline sur 57 370 évaluations.

### A1 — CORRIGÉ CE JOUR : aucun short n'avait de stop-loss

`AritV1.custom_stoploss` appelait `stoploss_from_absolute(sl, current_rate)` **sans `is_short`**
(deux endroits). Pour un short, le stop est AU-DESSUS du prix : la formule interne rend
`1 - stop/prix < 0`, ramené à **0.0** par le `max(..., 0)` final. Et freqtrade teste
`if stop_loss_value_custom and ...` — **0.0 est falsy**, la valeur est jetée avec un simple
`logger.debug`. Le SL d'un short restait donc au plancher de classe `stoploss = -0.99`.

**Preuve indépendante** : les 12 événements `gestion` du short BNB du dernier backtest portent
tous `before = 1156.05`, soit exactement `580,93 × 1,99`. Le stop n'a jamais quitté le plancher.

| current_rate | SL structurel (584,14) | SL G2 (581,13) | avec `is_short=True` |
|---|---|---|---|
| 580,93 (entrée) | **0.0** | **0.0** | 0,005530 |
| 580,68 | **0.0** | **0.0** | 0,005963 |
| 581,43 | **0.0** | 0,000518 | 0,004665 |

⚠️ **Les longs n'étaient pas touchés** (leur stop est sous le prix, la formule sans `is_short` y
est correcte). Ce sont les shorts, et eux seuls, **depuis A2 le 04/08**.

⚠️⚠️ **Conséquence sur les mesures** : R1 (BETA), la moitié short de Q13, et les 38 shorts du
train ont tous été produits par un système **sans stop**. À re-mesurer sous de **nouveaux id**,
jamais en relançant les anciens (verrou B6).

**Correctif appliqué** : `short = state.sign < 0` puis `is_short=short` aux deux appels.
**+3 tests** dont deux qui échouaient avant (441 passed). ⚠️ Le test qui existait,
`test_custom_stoploss_floor_posed_sans_after_fill`, **reproduisait l'erreur** : il comparait le
résultat à `stoploss_from_absolute(94.0, 100.0)`, le même appel fautif, sur un LONG. Il passait
quelle que soit l'erreur, et aucun test n'exerçait `custom_stoploss` sur un short.

### A2 — corollaire non corrigé : un short ouvert saturait le budget résiduel

`risk.residual_risk_total` lit `trade.stop_loss`. Tant que celui-ci restait au plancher, un short
déclarait `sign × (580,93 − 1156,05) = +575,12` par unité, soit **≈ 98 % de l'équité** de risque
résiduel. Le gate n° 5 exige `≤ 6 %` ⇒ **dès qu'un short était ouvert, plus aucune entrée n'était
possible**, dans aucun sens. Les 3 slots n'en faisaient qu'un. Corrigé par construction avec A1.

### B1 — le vrai goulot : hors PORTEUR, le seuil est arithmétiquement hors de portée

Deux pénalités s'empilent sur la même situation, jamais calibrées ensemble : le **multiplicateur
×0,85** (`regimes._classify_macro`) et le **bump de seuil +0,05** en NEUTRE (`cio.conviction:106`).
Comme `conviction = produit_pondéré × multiplicateur`, le seuil effectif sur le produit vaut
`seuil / multiplicateur`. Mesuré sur les 19 704 bougies TREND du rejeu :

| macro | n | mult | seuil | seuil effectif | % qui passent |
|---|---|---|---|---|---|
| PORTEUR | 7 179 | 1,00 | 0,50 | **0,500** | **14,31 %** |
| NEUTRE | 9 670 | 0,85 | 0,55 | **0,647** | **1,65 %** |
| HOSTILE | 2 855 | 0,85 | 0,50 | **0,588** | **1,37 %** |

**Facteur 9** entre PORTEUR et le reste, et NEUTRE représente **49 % du temps**. Pour référence :
p99 du produit pondéré = **0,695**, max absolu sur 5 ans = **0,875**. Exiger 0,647 revient à
demander le dernier centile. ⇒ **explication complète du « 0 long en 84 jours »** de juin-août
2026 : la macro n'y a jamais été PORTEUR.

⚠️ Ce n'est pas un chantier de mesure, c'est un **arbitrage pour Jonas** : la prudence macro
s'exprime sur le seuil **ou** sur le multiplicateur, pas sur les deux. Et ça reclasse Q1 (la
courbe N(seuil) mesure la mauvaise variable).

### B2 — `s_patterns` est un offset constant, pas un score

Distribution des 5 scores sur les 42 958 évaluations du train :

| score | poids | % de zéros | moyenne | contribution moyenne |
|---|---|---|---|---|
| s_structure | 0,40 | **64,3 %** | 0,190 | 0,0759 |
| s_momentum | 0,20 | 74,7 % | 0,201 | 0,0403 |
| s_sr | 0,15 | **86,0 %** | 0,124 | 0,0187 |
| **s_patterns** | 0,15 | **0,1 %** | 0,378 | 0,0567 |
| s_volume | 0,10 | 61,9 % | 0,271 | 0,0271 |

Le barème donne **0,3 quand il n'y a aucune figure** ⇒ non nul **99,9 % du temps**, il injecte
~0,045 quasi constants. Un terme constant dans une somme à seuil ne discrimine rien, il **déplace
le seuil**. Explication mécanique de son IC de −0,0162 (Q4), sans débat sur les bougies japonaises.
À l'autre bout : `s_structure` porte 40 % du poids et vaut 0 dans 64 % des cas.

### C1 — 52 % des lignes de journal sont des doublons

`journal._append_line` ouvre en `"a"`, le nom de fichier ne dépend que du **jour simulé**, et
**aucune ligne ne porte de `run_id`**. Deux backtests sur la même période s'additionnent sans
pouvoir être séparés après coup. Mesuré : **5 382 doublons exacts sur 10 377 lignes** ;
`2026-08-04.jsonl` porte 5 099 doublons sur 5 545 lignes ; des dizaines de fichiers sont
exactement doublés (48 lignes dont 24 doublons = deux runs superposés).
⚠️ `analysis/replay_entries.py` y lit le `sl_initial`. `analysis/dataset.py` est épargné : il
**rejoue** le pipeline au lieu de lire le journal — c'est pour ça que ses chiffres tiennent.

### Le reste des constats (détail et preuves dans AUDIT.html)

| # | Constat | Gravité |
|---|---|---|
| A3 | `_pending` jamais invalidé : un ordre `limit` non rempli laisse un `initial_sl`/`tp1`/`tp2`/`signal_id` périmé que le prochain fill de la même paire consommera | élevé |
| A4 | `entry` journalisé **deux fois** par trade, avec deux stakes (T7) | moyen |
| B3 | **La porte de spread n'est jamais évaluée** : `"spread_frac": None` câblé en dur (`AritV1.py:94`). Sans conséquence en backtest ; en capital réel c'est le seul garde-fou de liquidité, et il est débranché | élevé |
| B4 | G4 calcule la quantité à vendre au prix du **pic** (`mfe_r`), pas au prix courant | moyen |
| B5 | G2 est la seule G-rule sans déclencheur (G1/G3 attendent +1R) et sa garde se compare au plancher — face au plancher, tout resserre | moyen |
| C2 | **`macro_state.json` est gitignoré mais requis au backtest** : absent ⇒ `_macro_ok` = "missing" ⇒ porte news fermée ⇒ **0 trade, sans erreur**. Un mode d'échec identique au symptôme qu'on étudie depuis deux mois | élevé |
| C3 | Le **slippage réel n'est jamais mesuré** : `ev_exit` reçoit `params.SLIPPAGE_FRAC`, une constante. Le critère d'invalidation « > 2× modèle » de docs/03 §3.6 ne peut pas se déclencher | moyen |
| C4 | Porte news inerte en backtest (Q15) + F&G brut absent en colonne (Q11a) : **ni C1-bis ni A2-quinquies ne seront mesurables** avant de combler ces deux trous | moyen |
| C5 | Aucune rétention sur les journaux (13 Mo, 255 fichiers, croissance linéaire) | mineur |
| D1 | **L'interdit n° 3 (zéro look-ahead) n'a jamais été vérifié** : `lookahead-analysis` rend « too few trades caught (0/20) ». La rareté des entrées empêche de prouver l'absence du biais le plus grave. Le `recursive-analysis` en FAIL est en revanche un **artefact de grille** (écarts nuls au warm-up réel de 999) — à requalifier une bonne fois. Et ces checks datent du **04/08** | critique |
| D2 | **`docs/README.md` décrit un autre bot** : « Binance spot long-only » (futures long+short depuis A2), « mapping conviction 1 %→2 % » (risque constant depuis A6), pairlist spot. Un document estampillé « SPÉCIFICATION VERROUILLÉE » avec trois semaines de retard **autorise à coder faux de bonne foi** | élevé |
| D3 | Trois variables d'env changent le trading en silence (`ARIT_CONTROL_A`, `ARIT_G_OFF`, `ARIT_CHOCH_PRIORITY`) — aucune n'est journalisée au démarrage. Un run d'ablation oublié devient un run de production sans trace | moyen |
| D4 | Commentaire périmé `cio.py:30-34` annonçant un « BLOQUANT déclaré du dry-run » (live long-only) **résolu depuis la parité A2** | moyen |
| D5 | 4 constantes « miroir config » de `params.py` jamais lues et jamais vérifiées contre `config.dry.json` | mineur |

### Cybersécurité : RAS, et c'est vérifié

Secrets absents de l'arbre **et de tout l'historique** (`git rev-list --all`) · `.env` et
`config.api.json` gitignorés et jamais commités · clés exchange vides, `dry_run: true` ·
FreqUI sur `127.0.0.1`, CORS vide, openapi off · aucun `eval`/`exec`/`shell=True` · tous les
appels réseau avec timeout et HTTPS · le `flatten` du watchdog est correctement verrouillé
(opt-in par env, exige une exposition, 2 lectures de confirmation, flag d'idempotence).

### Ce qui manque, clairement

Tout test de `custom_stoploss` en short (comblé aujourd'hui) · `confirm_trade_exit` · un `run_id`
dans le journal · le calendrier historique (Q15) · la mesure du slippage réel · un hôte extérieur
(G8) · **et les critères de validation eux-mêmes** : `docs/README` exige PF ≥ 1,3, DD ≤ 15 % et
**≥ 100 trades**, quand le meilleur run produit 78 à 88 signaux **sur cinq ans**. Le critère
d'entrée en dry-run n'a jamais été approché, et il ne le sera pas par un réglage de seuil.
