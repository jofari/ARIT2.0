# Module RISK — « combien, et comment on gère ? »

> Agent d'origine : **Risk Manager**. Deux fichiers : `risk.py` décide **si** et **combien**
> (avant l'entrée), `gestion.py` porte les **G1-G7** (pendant le trade).
> C'est le cœur d'ARIT : `docs/01` dit que l'edge est ici, pas dans l'entrée.

## Où est le code

| Quoi | Fichier | Tests | Spec |
|---|---|---|---|
| Garde-fous, sizing, circuit breakers | [`../user_data/strategies/arit_lib/risk.py`](../user_data/strategies/arit_lib/risk.py) | `tests/test_risk.py` | `M04` + `docs/03.1-03.2`, `03.5` |
| **G1-G7** + SL/TP initiaux | [`../user_data/strategies/arit_lib/gestion.py`](../user_data/strategies/arit_lib/gestion.py) | `tests/test_gestion.py` | `M05` + `docs/03.3-03.4` |

---

## Partie 1 — avant l'entrée (`risk.py`)

### Les 8 gates (`gate_check`), dans l'ordre — arrêt au 1er échec

| # | Gate | Blocage si |
|---|---|---|
| 1 | régime | régime ∉ `ENTRY_REGIMES` |
| 2 | news | event high-impact à ±30 min · ou calendrier périmé > 2 h |
| 3 | spread | spread instantané > 0,05 % |
| 4 | slots | ≥ 3 trades ouverts |
| 5 | risque résiduel | résiduels + nouveau > 6 % |
| 6 | budget semaine | risque engagé/semaine ISO > 8 % · ou ≥ 10 entrées |
| 7 | RR | `rr_dispo` < 1,5 |
| 8 | véto humain | véto Discord (canari uniquement — dry-run : fenêtre 0) |

Détail qui compte : **toutes les métriques sont mesurées AVANT** la décision, même celles des
gates qu'on n'atteindra pas. Un skip est donc journalisable aussi richement qu'une entrée
(`docs/08.1`). Seul le véto (effet de bord : création du `.intent`) reste conditionnel.

`gate_check` **ne journalise pas** : il retourne `(ok, gate_fautif, metrics)` et c'est `AritV1`
qui écrit la ligne. Un module = une responsabilité.

### Sizing

Risque plancher **1 %**, cap **2 %** sur les trades n°1-100, **3 %** ensuite
(`RISK_CAP_SWITCH_TRADE_NO`, compteur global persistant).

### Circuit breakers (`docs/03.5`)

- **CB jour** : équité ≤ −6 % vs 00:00 UTC ⇒ plus aucune entrée. 2 CB dans la même semaine ISO
  ⇒ **restart manuel**.
- **CB séquentiel** : 2 clôtures consécutives ≤ −0,8R ⇒ cooldown.

---

## Partie 2 — LES G-RULES (`gestion.py`)

### SL / TP à l'entrée (`initial_levels`)

```
SL  = dernier HL 4h confirmé − 0,1 × ATR(14)_4h      (si HL exploitable et sous l'entrée)
      sinon fallback : entrée − 1,5 × ATR(14)_4h
TP1 = entrée + 1,5 × (entrée − SL)                    ← +1,5R, fixe
TP2 = résistance 4h la plus proche (si > TP1, sinon aucune cible)
```

`initial_sl` est **immuable** : c'est l'unité **R** de tout le reste du trade.

### Le tableau des 7 règles

| Règle | Nom | Déclencheur | Action |
|---|---|---|---|
| **G1** | Break-even | MFE ≥ **+1,0R** | SL = entrée × (1,001) — buffer frais 0,1 % |
| **G2** | Trailing structurel | HL 1h confirmé au-dessus du SL | SL = HL_1h − 0,1 × ATR(14)_1h |
| **G3** | Trailing ATR (fallback) | MFE ≥ **+1,0R** | SL = close_1h − **2,0** × ATR(14)_1h · **1,5×** en RISK_OFF |
| **G4** | TP partiel | 1er touch **+1,5R** | vend **50 %** de la quantité, **une seule fois** |
| **G5** | Extension | après G4, nouveau BOS 4h haussier | **supprime TP2** : le reste court sous G2/G3 |
| **G6** | Exit structure adverse | **ÉVÉNEMENT** de CHoCH 1h en clôture | sortie market immédiate du reste |
| **G7** | Time-stop | 24 bougies 1h **et** MFE < +0,5R | sortie market (trade mort) |

### L'ordre d'évaluation (appliqué par `AritV1` à chaque clôture 1h)

```
garde last_candle_ts  →  update_excursions (toujours)  →  check_exit (G6 > G7 > TP2)
   →  partial_tp (G4)  →  G5 (extension_on)  →  compute_sl (max des G1/G2/G3 actifs)
```

Trois subtilités qui expliquent la moitié du code :

1. **Le SL = `max()` des candidats, jamais une cascade.** G1, G2 et G3 proposent chacun un prix ;
   on garde le plus haut, et **seulement s'il resserre strictement**. La monotonie est
   re-vérifiée dans `compute_sl` même si freqtrade la garantit déjà — **le SL ne s'élargit
   JAMAIS** (interdit n°2 du PDR).
2. **G6 est un ÉVÉNEMENT, pas un état.** *(amendement décision Jonas 2026-07-10)* La définition
   d'origine « close 1h < dernier HL » était un **état**, vrai **32,5 %** des bougies (mesuré BTC
   2017-2026) ⇒ elle **tuait 87 % des trades dès l'entrée**. L'événement de cassure ne concerne
   que **5,1 %** des bougies. En plus, la bougie doit être **entièrement postérieure à l'entrée**
   (`row["date"] >= trade.open_date_utc`), sinon une cassure antérieure de quelques minutes au
   fill sortait le trade à t+0.
3. **G5 n'est pas du code ici** : `gestion.py` se contente de **permettre** l'extension en
   neutralisant TP2 quand `state.extension_on` est vrai. C'est un one-liner de l'appelant.

### Ablation et contrôle A (protocole A/B, `docs/09 §9.1`)

Overrides par **variable d'environnement** — pour lancer plusieurs backtests en parallèle sans
éditer `params.py` :

| Env | Effet |
|---|---|
| *(rien)* | **produit B** : les 7 G-rules actives |
| `ARIT_G_OFF=G3` | désactive **une** règle (ablation `09 §9.1.4`) |
| `ARIT_CONTROL_A=1` | **contrôle A** : TP fixe +1,5R sortie totale, SL initial figé, **aucune G-rule** |

Ce n'est **pas** de l'hyperopt : les valeurs G restent figées, on ne fait qu'activer/désactiver.
**G1-G7 et les poids ne sont JAMAIS hyperoptés** (interdit n°5).

---

## État actuel / limites connues

- **`COOLDOWN_POST_EXIT_CANDLES = 2`** (PDR 07.1, `CooldownPeriod`) : la constante existe, mais
  **les Protections freqtrade ne sont pas implémentées** — ni dans la config, ni dans `AritV1`.
  Les circuit breakers `03.5` (CB jour / CB séquentiel) sont bien là, eux.
- **`SIGNAL_FRESH_1H_CANDLES = 3`** (PDR 11.6, fraîcheur du signal 4h) : **non appliquée**.
- **G2 n'a pas de déclencheur en R** (contrairement à G1/G3) : il trail depuis l'entrée. C'est
  conforme au PDR, mais c'est la règle qui coupe le plus tôt — candidate n°1 à l'ablation.
