"""M05 — arit_lib/gestion.py : regles de gestion G1-G7 (le coeur d'ARIT, docs/01).

Pur : aucun I/O, aucun reseau, aucun appel LLM (docs/README interdits n1). Chaque
regle prend l'etat du trade + la bougie 1h CLOTUREE + les flags d'ablation et
retourne une action (nouveau SL, stake a vendre, cause de sortie) ou None. Le
caller (strategie AritV1 / M07) applique l'ordre d'evaluation, persiste le
custom_data, journalise l'event "gestion" (before/after/profit_r) et passe les
ordres freqtrade. G5 (extension) est un one-liner du caller : ce module le PERMET
en neutralisant TP2 quand state.extension_on est vrai.

Invariant absolu (docs/README n2, docs/03 §3.4) : le SL ne s'elargit JAMAIS —
compute_sl re-verifie la monotonie meme si freqtrade la garantit deja.

Protocole `trade` (duck-typed, pas d'import freqtrade — docs/11 §11.5) :
    open_rate: float         prix d'entree (unite de reference R, immuable)
    stop_loss: float         SL courant absolu
    amount: float            quantite base detenue
    open_date_utc: datetime  horodatage d'entree, tz-aware UTC

Protocole `row_1h` : pandas Series de la bougie 1h CLOTUREE, colonnes 11.3 —
    close, high, low, date, atr_1h, last_hl_1h, last_lh_1h (A2),
    choch_bear_event_1h / choch_bull_event_1h (bool, G6),
    bos_fresh_4h / bos_fresh_bear_4h (bool, G5), regime (str).

SENS DU TRADE (A2, 2026-08-04) — le bot est long ET short. Le sens vit dans
`state.is_short` et se lit via `state.sign` (+1/-1, contracts.direction_sign). Toute
comparaison de prix passe par `sign x (a - b)` : aucune G-rule ne contient de `if
is_short`, ce qui garantit qu'aucune ne peut etre symetrisee A MOITIE. Les trois
asymetries reelles, elles, sont explicites : l'ancre de G2, l'evenement de G6, la
CASSURE de G5, et l'extreme de bougie (high/low) utilise pour l'excursion et pour
atteindre une cible.
Le niveau TP2 de sortie est fourni explicitement par l'appelant (parametre `tp2`) :
depuis la decision Jonas 09/07 c'est la resistance 4h COURANTE (nearest_res_4h de la
row), recalculee a chaque cloture 1h — plus le TP2 fige a l'entree (docs/03 par.3.3
amendement). Ce module ne change pas : il recoit deja le niveau en parametre.

Ordre d'evaluation par cloture 1h (applique par le caller, docs/M05 §2) :
    garde last_candle_ts -> update_excursions (toujours) -> check_exit (G6>G7>TP2)
    -> partial_tp (G4) -> G5 (extension_on) -> compute_sl (max G1/G2/G3 actifs).
"""

import pandas as pd

from . import params
from .contracts import TradeState


def flags() -> dict:
    """Copie fraiche des flags d'ablation (params.G_FLAGS_DEFAULT).

    Defaut = les 7 a True (produit B) ; ARIT_G_OFF=Gx en passe UNE a False (ablation 09 §9.1.4).
    Le controle A ne passe PAS par ces flags : il court-circuite via params.CONTROL_A_MODE.
    """
    return dict(params.G_FLAGS_DEFAULT)


def _resolve(overrides: dict | None) -> dict:
    return overrides if overrides is not None else flags()


def r_multiple(price: float, entry: float, initial_sl: float, sign: int = 1) -> float:
    """R du prix : sign x (price - entry) / risque, risque = sign x (entry - initial_sl).

    +1R = +1x le risque initial, DANS LE SENS DU TRADE (A2). initial_sl est immuable
    (unite R). Risque nul/negatif (cas degenere : SL du mauvais cote) -> 0.0.
    `sign` = contracts.direction_sign(is_short) ; defaut +1 = long, retrocompatible.
    """
    risk = sign * (entry - initial_sl)
    if risk <= 0:
        return 0.0
    return sign * (price - entry) / risk


def initial_levels(entry, anchor_4h, atr_4h, target_4h, sign: int = 1):
    """SL/TP1/TP2 initiaux a l'entree (PDR 03.3) — fonction PURE, appelee par M07.

    LONG  (sign=+1) : anchor = last_hl_4h, target = nearest_res_4h.
    SHORT (sign=-1) : anchor = last_lh_4h, target = nearest_sup_4h (A2, docs/03 §3.7).

    SL = anchor - sign x SL_HL_ATR_BUFFER x atr_4h si l'ancre est exploitable (non-NaN et
    du BON COTE de l'entree : sous l'entree en long, au-dessus en short), sinon fallback
    entry - sign x SL_FALLBACK_ATR_MULT x atr_4h. Reference = prix d'ENTREE (PDR 03.3) ;
    features.rr_available utilise `close` pour l'ESTIMATION pre-entree (pas encore d'entree)
    — divergence assumee et documentee. TP1 = entry + sign x TP1_R x risque. TP2 = target
    s'il est strictement AU-DELA de TP1 dans le sens du trade, sinon None (pas de cible).
    atr_4h NaN => SL NaN (le caller skip, M04.4).
    """
    anchor_ok = (anchor_4h is not None and anchor_4h == anchor_4h
                 and sign * (entry - anchor_4h) > 0)
    if anchor_ok:
        sl = anchor_4h - sign * params.SL_HL_ATR_BUFFER * atr_4h
    else:
        sl = entry - sign * params.SL_FALLBACK_ATR_MULT * atr_4h
    tp1 = entry + sign * params.TP1_R * (sign * (entry - sl))
    target_ok = (target_4h is not None and target_4h == target_4h
                 and sign * (target_4h - tp1) > 0)
    return sl, tp1, (target_4h if target_ok else None)


def _num(value) -> float:
    return float(value) if value is not None and pd.notna(value) else float("nan")


def entry_levels(row, entry: float, sign: int = 1):
    """Colonnes 4h du sens vise -> initial_levels (A2, PDR 03.3). Retour (sl, tp1, tp2).

    LONG  : ancre `last_hl_4h`, cible `nearest_res_4h`.
    SHORT : ancre `last_lh_4h`, cible `nearest_sup_4h`.
    Le choix des colonnes est centralise ICI et pas dans la strategie : le disperser est
    exactement la faute qui produit un short symetrise a moitie.
    """
    anchor, target = (("last_hl_4h", "nearest_res_4h") if sign > 0
                      else ("last_lh_4h", "nearest_sup_4h"))
    return initial_levels(entry, row.get(anchor), _num(row.get("atr_4h")), row.get(target), sign)


def _candle_ts(row) -> int:
    """Epoch UTC (s) de la bougie — cle de la garde une-action-par-bougie (11.3 last_candle_ts)."""
    return int(pd.Timestamp(row["date"]).value // 1_000_000_000)


def update_excursions(state: TradeState, row, entry: float) -> TradeState:
    """MAE/MFE en R a chaque cloture 1h (docs/M05 §2, decision #7). Mute et retourne `state`.

    Garde une-action-par-bougie : si la bougie a deja ete traitee (meme ts) -> no-op.
    A2 : l'extreme ADVERSE est le low en long mais le HIGH en short (un prix qui monte
    fait mal a un vendeur) — inverser les deux serait le bug le plus silencieux du short,
    car le signe de mae/mfe resterait plausible tout en pilotant G1/G3/G4/G7 a l'envers.
    """
    ts = _candle_ts(row)
    if ts == state.last_candle_ts:
        return state
    sign = state.sign
    adverse, favorable = (row["low"], row["high"]) if sign > 0 else (row["high"], row["low"])
    state.mae_r = min(state.mae_r, r_multiple(adverse, entry, state.initial_sl, sign))
    state.mfe_r = max(state.mfe_r, r_multiple(favorable, entry, state.initial_sl, sign))
    state.last_candle_ts = ts
    return state


def compute_sl(trade, row_1h, state: TradeState, flags: dict | None = None) -> float | None:
    """SL = max(candidats G1/G2/G3 actifs) en prix absolu (docs/03 §3.4, decision #5).

    G1 : entree x (1 + sign x G1_BE_BUFFER_FRAC) si mfe_r >= G1_TRIGGER_R.
    G2 : ancre_1h - sign x G2_ATR_BUFFER x atr_1h, seulement si ce candidat RESSERRE.
         Ancre = last_hl_1h en long, last_lh_1h en short (A2).
    G3 : close - sign x k x atr_1h (k = G3_ATR_MULT, ou G3_ATR_MULT_RISK_OFF en RISK_OFF)
         seulement si mfe_r >= G3_TRIGGER_R.
    Retour = le candidat le plus SERRE s'il resserre strictement, sinon None. « Resserrer »
    = monter en long, DESCENDRE en short (A2) : d'ou la comparaison sur sign x prix partout.
    Monotonie re-verifiee ici : le SL ne s'elargit jamais (invariant docs/README n2).
    """
    if params.CONTROL_A_MODE:
        # PDR 09 §9.1.1 — controle A : SL fige a l'initial, aucun G1/G2/G3. Contrat compute_sl
        # (« retour seulement si RESSERRE ») : rien ne bouge => None (le SL initial pose a
        # l'entree reste en place ; renvoyer initial_sl a l'identique ferait logger un faux move).
        return None
    active = _resolve(flags)
    sign = state.sign
    entry = trade.open_rate
    current_sl = trade.stop_loss
    atr = row_1h["atr_1h"]
    mfe = state.mfe_r
    candidates = []
    if active["G1"] and mfe >= params.G1_TRIGGER_R:
        candidates.append(entry * (1.0 + sign * params.G1_BE_BUFFER_FRAC))
    if active["G2"]:
        anchor = row_1h["last_hl_1h"] if sign > 0 else row_1h["last_lh_1h"]
        g2 = anchor - sign * params.G2_ATR_BUFFER * atr
        if sign * (g2 - current_sl) > 0:
            candidates.append(g2)
    if active["G3"] and mfe >= params.G3_TRIGGER_R:
        k = params.G3_ATR_MULT_RISK_OFF if row_1h["regime"] == "RISK_OFF" else params.G3_ATR_MULT
        candidates.append(row_1h["close"] - sign * k * atr)
    if not candidates:
        return None
    new_sl = max(candidates, key=lambda c: sign * c)   # le plus serre dans le sens du trade
    if sign * (new_sl - current_sl) <= 0:
        return None
    return new_sl


def partial_tp(trade, current_profit_r: float, state: TradeState,
               flags: dict | None = None) -> float | None:
    """G4 : au premier +1,5R -> vend 50 % du stake, une seule fois (docs/03 §3.4).

    Le caller passe mfe_r via current_profit_r (semantique "premier touch", decision #4).
    Retour = stake NEGATIF a consommer par adjust_trade_position ; sinon None.
    PDR 03.4 G4 : vendre 50 % de la QUANTITE — freqtrade convertit le stake en coins
    au prix COURANT, donc stake = -G4_SELL_FRACTION x amount x current_rate
    (current_rate reconstruit depuis le R courant : entry + R x (entry - initial_sl)).
    A2 : cette formule est DEJA symetrique et n'a pas besoin du signe — le terme
    (entry - initial_sl) est negatif en short (SL au-dessus), ce qui fait descendre le
    prix reconstruit quand R monte. Verifie : entree 100, SL 110, R = 1,5 => 85.
    Le stake reste NEGATIF dans les deux sens : freqtrade reduit la position, il ne la
    retourne pas.
    Mute tp1_done a True au declenchement.
    """
    if params.CONTROL_A_MODE:  # PDR 09 §9.1.1 — controle A : aucune G-rule, G4 jamais declenche.
        return None
    active = _resolve(flags)
    if not active["G4"] or state.tp1_done or current_profit_r < params.G4_TRIGGER_R:
        return None
    state.tp1_done = True
    current_rate = trade.open_rate + current_profit_r * (trade.open_rate - state.initial_sl)
    return -(params.G4_SELL_FRACTION * trade.amount * current_rate)


def _age_candles(trade, row_1h) -> int:
    """Nombre de bougies 1h (heures pleines) ecoulees depuis l'entree."""
    delta = row_1h["date"] - trade.open_date_utc
    # 3600 s = 1 bougie TIMEFRAME_BASE (1h) : conversion secondes -> nb de bougies 1h.
    return int(delta.total_seconds() // 3600)


def set_extension(state: TradeState, row_1h, flags: dict | None = None) -> bool:
    """G5 (docs/03 par.3.4, M05 par.2.5) : apres G4, une NOUVELLE cassure 4h dans le sens du
    trade neutralise TP2 — le reste court sous trailing G2/G3 seul. Rend True si G5 vient de
    s'activer (donc une seule fois par trade), False sinon.

    Vivait en ligne dans AritV1.py jusqu'au 2026-08-31, avec trois consequences :
      - `active["G5"]` n'etait jamais lu : ARIT_G_OFF=G5 etait un no-op SILENCIEUX, et un run
        d'ablation sur G5 rendait un produit B complet lu a tort comme « G5 ne coute rien » ;
      - la colonne testee etait `bos_fresh_4h`, c'est-a-dire la cassure HAUSSIERE seule
        (features.py:202) : sur un short, G5 s'activait donc quand le marche repartait CONTRE
        la position. Meme famille que A1 (audit 24/08) ;
      - c'etait du metier dans la coquille freqtrade, que docs/M05 par.2.5 place ici.

    A2 : la cassure FAVORABLE est haussiere pour un acheteur, BAISSIERE pour un vendeur —
    quatrieme asymetrie explicite du module (cf. docstring).
    """
    if state.extension_on or not state.tp1_done:
        return False
    if not _resolve(flags)["G5"]:
        return False
    colonne = "bos_fresh_4h" if state.sign > 0 else "bos_fresh_bear_4h"
    if not bool(row_1h.get(colonne)):
        return False
    state.extension_on = True
    return True


def check_exit(trade, row_1h, state: TradeState, tp2: float | None,
               flags: dict | None = None) -> str | None:
    """Sorties par priorite (docs/M05 §2.3, decision #6) : G6 > G7 > TP2, sinon None.

    CONTROLE A (PDR 09 §9.1.1) : si params.CONTROL_A_MODE, sortie TOTALE "TP_CONTROL_A" des
    que high >= entry + TP1_R x (entry - initial_sl) (TP fixe +1,5R), sinon None — AVANT toute
    G-rule (G6/G7/TP2 inertes). C'est le controle du test A/B (aucune gestion active). Meme
    garde "vie du trade" que G6 (fix 2026-07-18) : bougie entierement posterieure a l'entree.
    G6 : choch_bear_event_1h vrai en cloture -> "G6" (prioritaire sur tout). EVENEMENT de cassure
    et non l'etat persistant (decision Jonas 2026-07-10, docs/03 par.3.4) : l'etat pre-existant a
    l'entree ne sort plus, seule la bougie qui CASSE le dernier HL 1h en cloture declenche. La
    cassure ne compte que PENDANT LA VIE DU TRADE (docs/03 par.3.4 amendement 2026-07-10) : la
    bougie de l'evenement doit etre entierement posterieure a l'entree (row date d'OUVERTURE
    >= open_date_utc) — sinon la cassure precede le fill de quelques minutes et sort a t+0.
    G7 : age >= G7_MAX_CANDLES_1H ET mfe_r < G7_MIN_R -> "G7" (trade mort).
    TP2 : extension_on False ET tp1_done True ET high >= tp2 -> "TP2".
    `tp2` = niveau fourni par le caller (resistance 4h courante, decision Jonas 09/07),
    None si aucun. extension_on (G5) neutralise TP2.
    """
    sign = state.sign
    # A2 : l'extreme qui atteint une CIBLE est le high en long, le LOW en short.
    reach = row_1h["high"] if sign > 0 else row_1h["low"]
    if params.CONTROL_A_MODE:
        # Meme garde "vie du trade" que G6 (docs/03 par.3.4 amendement 2026-07-10) : la bougie
        # doit etre entierement posterieure a l'entree, sinon un high PRE-fill sort a t+0
        # (14 sorties/re-entrees churn mesurees sur la campagne du 11/07, BUILD_NOTES 17/07).
        if row_1h["date"] < trade.open_date_utc:
            return None
        entry = trade.open_rate
        tp1 = entry + params.TP1_R * (entry - state.initial_sl)
        return "TP_CONTROL_A" if sign * (reach - tp1) >= 0 else None
    active = _resolve(flags)
    # A2 : l'evenement de structure ADVERSE est le CHoCH baissier pour un acheteur,
    # le CHoCH HAUSSIER pour un vendeur.
    choch_adverse = row_1h["choch_bear_event_1h"] if sign > 0 else row_1h["choch_bull_event_1h"]
    if (active["G6"] and bool(choch_adverse)
            and row_1h["date"] >= trade.open_date_utc):
        return "G6"
    if (active["G7"] and _age_candles(trade, row_1h) >= params.G7_MAX_CANDLES_1H
            and state.mfe_r < params.G7_MIN_R):
        return "G7"
    if (not state.extension_on and state.tp1_done
            and tp2 is not None and sign * (reach - tp2) >= 0):
        return "TP2"
    return None
