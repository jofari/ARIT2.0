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
    close, high, low, date, atr_1h, last_hl_1h,
    choch_bear_event_1h (bool, G6), bos_fresh_4h (bool), regime (str).
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


def r_multiple(price: float, entry: float, initial_sl: float) -> float:
    """R du prix : (price - entry) / (entry - initial_sl). +1R = +1x le risque initial.

    initial_sl est immuable (unite R). Risque nul/negatif (cas degenere) -> 0.0.
    """
    risk = entry - initial_sl
    if risk <= 0:
        return 0.0
    return (price - entry) / risk


def initial_levels(entry, last_hl_4h, atr_4h, nearest_res_4h):
    """SL/TP1/TP2 initiaux a l'entree (PDR 03.3) — fonction PURE, appelee par M07.

    SL = last_hl_4h - SL_HL_ATR_BUFFER x atr_4h si HL exploitable (non-NaN et sous l'entree),
    sinon fallback entry - SL_FALLBACK_ATR_MULT x atr_4h. Reference = prix d'ENTREE (PDR 03.3) ;
    features.rr_available utilise `close` pour l'ESTIMATION pre-entree (pas encore d'entree) —
    divergence assumee et documentee. TP1 = entry + TP1_R x (entry - SL). TP2 = nearest_res_4h
    si strictement > TP1, sinon None (pas de cible). atr_4h NaN => SL NaN (le caller skip, M04.4).
    """
    hl_ok = last_hl_4h is not None and last_hl_4h == last_hl_4h and last_hl_4h < entry
    if hl_ok:
        sl = last_hl_4h - params.SL_HL_ATR_BUFFER * atr_4h
    else:
        sl = entry - params.SL_FALLBACK_ATR_MULT * atr_4h
    tp1 = entry + params.TP1_R * (entry - sl)
    res_ok = (nearest_res_4h is not None and nearest_res_4h == nearest_res_4h
              and nearest_res_4h > tp1)
    return sl, tp1, (nearest_res_4h if res_ok else None)


def _candle_ts(row) -> int:
    """Epoch UTC (s) de la bougie — cle de la garde une-action-par-bougie (11.3 last_candle_ts)."""
    return int(pd.Timestamp(row["date"]).value // 1_000_000_000)


def update_excursions(state: TradeState, row, entry: float) -> TradeState:
    """MAE/MFE en R a chaque cloture 1h (docs/M05 §2, decision #7). Mute et retourne `state`.

    Garde une-action-par-bougie : si la bougie a deja ete traitee (meme ts) -> no-op.
    Sinon mae_r = min(mae_r, R(low)), mfe_r = max(mfe_r, R(high)), puis stamp du ts.
    """
    ts = _candle_ts(row)
    if ts == state.last_candle_ts:
        return state
    state.mae_r = min(state.mae_r, r_multiple(row["low"], entry, state.initial_sl))
    state.mfe_r = max(state.mfe_r, r_multiple(row["high"], entry, state.initial_sl))
    state.last_candle_ts = ts
    return state


def compute_sl(trade, row_1h, state: TradeState, flags: dict | None = None) -> float | None:
    """SL = max(candidats G1/G2/G3 actifs) en prix absolu (docs/03 §3.4, decision #5).

    G1 : entree x (1 + G1_BE_BUFFER_FRAC) si mfe_r >= G1_TRIGGER_R.
    G2 : last_hl_1h - G2_ATR_BUFFER x atr_1h, seulement si ce candidat > SL courant.
    G3 : close - k x atr_1h (k = G3_ATR_MULT, ou G3_ATR_MULT_RISK_OFF en RISK_OFF)
         seulement si mfe_r >= G3_TRIGGER_R.
    Retour = max des candidats s'il RESSERRE strictement (> trade.stop_loss), sinon None.
    Monotonie re-verifiee ici : jamais un SL <= SL courant (invariant docs/README n2).
    """
    if params.CONTROL_A_MODE:
        # PDR 09 §9.1.1 — controle A : SL fige a l'initial, aucun G1/G2/G3. Contrat compute_sl
        # (« retour seulement si RESSERRE ») : rien ne bouge => None (le SL initial pose a
        # l'entree reste en place ; renvoyer initial_sl a l'identique ferait logger un faux move).
        return None
    active = _resolve(flags)
    entry = trade.open_rate
    current_sl = trade.stop_loss
    atr = row_1h["atr_1h"]
    mfe = state.mfe_r
    candidates = []
    if active["G1"] and mfe >= params.G1_TRIGGER_R:
        candidates.append(entry * (1.0 + params.G1_BE_BUFFER_FRAC))
    if active["G2"]:
        g2 = row_1h["last_hl_1h"] - params.G2_ATR_BUFFER * atr
        if g2 > current_sl:
            candidates.append(g2)
    if active["G3"] and mfe >= params.G3_TRIGGER_R:
        k = params.G3_ATR_MULT_RISK_OFF if row_1h["regime"] == "RISK_OFF" else params.G3_ATR_MULT
        candidates.append(row_1h["close"] - k * atr)
    if not candidates:
        return None
    new_sl = max(candidates)
    if new_sl <= current_sl:
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
    if params.CONTROL_A_MODE:
        # Meme garde "vie du trade" que G6 (docs/03 par.3.4 amendement 2026-07-10) : la bougie
        # doit etre entierement posterieure a l'entree, sinon un high PRE-fill sort a t+0
        # (14 sorties/re-entrees churn mesurees sur la campagne du 11/07, BUILD_NOTES 17/07).
        if row_1h["date"] < trade.open_date_utc:
            return None
        entry = trade.open_rate
        tp1 = entry + params.TP1_R * (entry - state.initial_sl)
        return "TP_CONTROL_A" if row_1h["high"] >= tp1 else None
    active = _resolve(flags)
    if (active["G6"] and bool(row_1h["choch_bear_event_1h"])
            and row_1h["date"] >= trade.open_date_utc):
        return "G6"
    if (active["G7"] and _age_candles(trade, row_1h) >= params.G7_MAX_CANDLES_1H
            and state.mfe_r < params.G7_MIN_R):
        return "G7"
    if (not state.extension_on and state.tp1_done
            and tp2 is not None and row_1h["high"] >= tp2):
        return "TP2"
    return None
