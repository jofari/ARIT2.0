# C2 — Porte « spread » : analyse des conséquences AVANT de coder

> Demande de Jonas (03/08) : « étudier d'abord **les conséquences** du `spread_state` avant
> de coder quoi que ce soit. » Ce document répond à ça. **Aucune ligne de `spread_state.py`
> n'a été écrite.**
>
> Rédigé le 2026-08-04. À lire avec `docs/03 §3.2.3`, `docs/06 §6.4`, `docs/11 §11.5`.

---

## 1. État constaté dans le code (vérifié, pas supposé)

- `params.SPREAD_MAX_FRAC = 0.0005` (0,05 %) existe et est cité par la spec.
- `risk.gate_check` implémente correctement la porte : `if spread is not None and spread >
  SPREAD_MAX_FRAC: return False, GATE_NAMES[2]`.
- **Mais `AritV1.confirm_trade_entry` passe `"spread_frac": None` en dur.** La condition
  `spread is not None` est donc toujours fausse : **la porte n'a jamais bloqué une seule
  entrée et ne le peut pas.** Elle est inerte, pas cassée.
- `services/spread_state.py` n'existe pas. Le dossier `services/` contient
  `macro_state.py`, `discord_bot.py`, `watchdog.py`.

Conséquence immédiate : le gate `spread` apparaît dans chaque ligne `ev_gate_check` du
journal avec la valeur `None`. Toute analyse passée qui a compté les gates a compté un gate
qui ne s'est jamais déclenché — ce n'est pas un biais, mais c'est une colonne vide.

## 2. La contrainte d'architecture qui décide presque tout

`docs/11 §11.5` interdit **tout réseau dans les callbacks** de la stratégie. Lire un carnet
d'ordres EST un appel réseau. Donc `spread_state` ne peut pas être une fonction appelée
depuis `confirm_trade_entry` : ce serait un service de fond qui écrit un fichier, relu par
la stratégie — exactement le patron de `macro_state.json` (M08).

Trois conséquences en découlent mécaniquement :

1. **Le spread lu sera toujours périmé** de l'âge de la boucle du service. Un spread est la
   grandeur la plus volatile du système : il s'écarte et se referme en secondes. Un spread
   vieux de 30 s ne dit pas grand-chose du spread au moment du fill.
2. **Il faut une politique de panne**, et les deux options sont mauvaises. En *fail-safe*
   (comme `_macro_ok`, qui bloque si le fichier est absent/périmé), un service mort coupe
   TOUTES les entrées — on ajoute un point de défaillance unique. En *fail-open*, on revient
   exactement à l'état actuel : porte inerte. Il n'y a pas de troisième voie.
3. **Un nouveau processus à surveiller** : le watchdog (M10) devrait le couvrir, ce qui est
   du travail en plus sur un chantier dont le bénéfice n'est pas mesuré.

## 3. Le vrai coût : la parité backtest/live

`docs/07 §7.3` pose une règle absolue : le live ne doit pas agir différemment de ce que le
backtest simule. Or **les données OHLCV freqtrade ne contiennent aucun carnet d'ordres**.
Un gate de spread est donc, par construction :

> actif en live et en dry-run, **inexistant en backtest**.

Autrement dit, chaque entrée que le backtest compte, le live peut la refuser — sans que le
backtest puisse le prévoir ni le chiffrer. C'est précisément le mode de divergence
live/backtest que `docs/09` liste comme critère d'invalidation (« divergence live/backtest
> 10 pts de win-rate → halt »). Coder C2 aujourd'hui, c'est **fabriquer volontairement**
une source de divergence qu'on s'est engagé à surveiller comme un signal d'alarme.

## 4. Combien la porte mordrait-elle, en ordre de grandeur ?

Rappel : le seuil est 0,05 % et le périmètre est **4 paires majeures** (BTC, ETH, SOL, BNB),
désormais en **perpétuels** (A2 impose les futures). Sur ces instruments, le spread
au meilleur limite est d'ordre 0,005–0,01 % pour BTC/ETH et 0,01–0,03 % pour SOL/BNB en
conditions normales : **un ordre de grandeur sous le seuil**. La porte ne mordrait donc
quasiment jamais en régime normal.

Elle mordrait pendant les élargissements de carnet — annonces macro, liquidations en
cascade, trous de liquidité. C'est l'argument POUR. Mais deux gardes couvrent déjà
largement ces moments :
- la fenêtre news (03.2.2) bloque ±30 min autour de chaque événement *high impact* ;
- le CB jour (−6 %) et le CB séquentiel coupent après les dégâts.

Le gain marginal de C2 est donc **l'intersection** « carnet élargi » ∩ « pas d'événement
calendrier » ∩ « pas encore de perte ». Cet ensemble n'est pas vide (liquidations
endogènes), mais il est petit — et il n'est **pas mesuré**.

## 5. Recommandation

**Ne pas coder la porte maintenant. Mesurer d'abord, exactement comme pour les Bollinger
(C3) : journaliser sans décider.**

Le patron est déjà validé et en place dans le projet : les Bollinger sont calculées et
écrites dans le journal mais explicitement non décisionnelles, « pour accumuler la donnée
et être testables plus tard sur les barres, pas sur 128 trades ».

Étapes proposées, par coût croissant :

1. **(quasi gratuit)** Quand le dry-run tournera, faire écrire au service un
   `spread_state.json` **purement observationnel** et ajouter `spread_frac` aux métriques de
   `ev_gate_check` — en gardant `cfg["spread_frac"] = None`, donc **sans jamais bloquer**.
   Le journal enregistre alors la distribution réelle sans changer le produit d'un iota.
2. **Après N semaines**, répondre avec des chiffres à : quel percentile du spread dépasse
   0,05 % ? sur quelles paires ? à quelles heures ? combien d'entrées auraient été refusées ?
3. **Alors seulement**, décider — avec la mesure — si la porte vaut sa divergence
   backtest/live, et si 0,05 % est le bon seuil (il vient du PDR, il n'a jamais été calibré).

Tant que l'étape 2 n'a pas de chiffres, activer la porte reviendrait à ajouter un filtre non
mesuré à un système dont `CHANTIERS.md` dit qu'il **n'a aucun edge démontré** — et sur un
substrat à espérance nulle, tout filtre qui réduit l'exposition *paraît* positif
(`docs/01_edge.md`, piège du substrat nul). On se paierait une illusion.

## 6. Ce qu'il faut décider, Jonas

- [ ] **Valides-tu de laisser la porte inerte** et de passer par la mesure (étape 1–2) ?
- [ ] Si oui, l'étape 1 se fait **au démarrage du dry-run**, pas avant : elle n'a de sens
      qu'avec un flux temps réel. C2 reste donc ouvert mais **non bloquant**.
- [ ] Si tu préfères l'activer tout de suite malgré tout, il faut trancher la politique de
      panne (§2) : service mort ⇒ on bloque tout, ou on ne bloque rien ?
