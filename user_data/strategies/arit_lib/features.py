"""M01 — features.py : les yeux du bot (docs/modules/M01, PDR 05, docs/11 par.11.3).

Fonctions PURES : DataFrame in -> DataFrame out. pandas/numpy/talib uniquement —
aucun I/O, aucun reseau, aucun import freqtrade (BUILD_NOTES T1).
Priorite absolue (M01) : zero look-ahead, zero repaint — tout pivot decisionnel
est confirme n bougies plus tard (params.PIVOT_CONFIRM_SHIFT pour N=PIVOT_N) ;
les fractals BRUTS repeignent PAR CONSTRUCTION, ils restent donc LOCAUX a
find_pivots et ne sont jamais poses sur le DataFrame (A2, 2026-08-03).

Deux etages (BUILD_NOTES design suffix) :
- frame 4h/1d NATIF (informatives, appelees par M07) : add_indicators,
  find_pivots, track_structure, sr_levels, candle_patterns -> noms natifs sans
  suffixe ; freqtrade ajoute `_4h`/`_1d` au merge (clotures seulement, README 3).
- df 1h MERGE (colonnes *_4h/*_1d deja presentes) : compute_all -> atr_1h,
  last_hl_1h, choch_bear_1h, new_4h, rr_dispo, s_* (contracts.FEATURE_COLUMNS).
"""

import numpy as np
import pandas as pd
import talib

from arit_lib import contracts, params

# Suffixes contractuels (docs/11 par.11.3) : poses par le merge freqtrade (4h/1d)
# ou directement sur la base 1h.
SUFFIX_4H = f"_{params.TIMEFRAME_SETUP}"
SUFFIX_1H = f"_{params.TIMEFRAME_BASE}"

# Pattern custom PDR 05.4 (pin bar bullish) — journalise avec les CDL* (idee 9),
# d'ou le prefixe contractuel contracts.CDL_PREFIX.
PINBAR_COL = contracts.CDL_PREFIX + "pinbar_bull"
PINBAR_BEAR_COL = contracts.CDL_PREFIX + "pinbar_bear"   # A2 — miroir baissier (05.4)

# Scores discrets contractuels (PDR 04.4) — seules valeurs autorisees.
_S0, _S03, _S05, _S07, _S1 = params.SCORE_VALUES

_TALIB_CDL_GROUP = "Pattern Recognition"


def _f64(s: pd.Series) -> np.ndarray:
    return s.to_numpy(dtype=np.float64)


def _bool(s: pd.Series) -> pd.Series:
    """Serie booleenne sure : les colonnes bool deviennent object/float au merge
    (NaN d'amorce) — NaN => False, jamais de True fantome."""
    return s.fillna(False).astype(bool)


def _cdl_col(talib_name: str) -> str:
    """"CDLENGULFING" -> "cdl_engulfing" (BUILD_NOTES 5)."""
    return contracts.CDL_PREFIX + talib_name[len("CDL"):].lower()


def _event(state: pd.Series) -> pd.Series:
    """Etat persistant -> EVENEMENT de bascule faux->vrai (03.4 G6, decision Jonas 10/07).

    shift(1) = passe seul => aucun look-ahead ; warm-up => False (fill_value).
    """
    return state & ~state.shift(1, fill_value=False)


def _prev_4h(s: pd.Series, new_4h: pd.Series) -> pd.Series:
    """Valeur de la bougie 4h PRECEDENTE sur le df 1h merge (PDR 11.2) : les
    colonnes 4h se repetent intra-bougie, on lit la valeur a la ligne new_4h
    (ou shift(1) tombe sur la bougie precedente) puis on la propage."""
    return s.shift(1).where(new_4h).ffill()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """M01 / BUILD_NOTES 2 — etage 1h merge, ordre fixe.

    Requiert le df 1h merge par freqtrade (*_4h/*_1d, date_4h presents).
    Ajoute : atr_1h, last_hl_1h, choch_bear_1h (G2), choch_bear_event_1h (G6), new_4h (PDR 11.2),
    rr_dispo (05.2) et s_structure/s_momentum/s_sr/s_patterns/s_volume (05).
    Idempotente (M01 invariant 2) : tout est recalcule depuis les inputs.
    """
    df = df.copy()
    df["atr" + SUFFIX_1H] = talib.ATR(
        _f64(df["high"]), _f64(df["low"]), _f64(df["close"]),
        timeperiod=params.ATR_PERIOD,
    )
    # Structure 1h (G2/G6, PDR 05.1) : memes regles que le 4h, sur frame
    # temporaire pour ne poser QUE les colonnes contractuelles (par.11.3).
    tmp = df[["open", "high", "low", "close"]].copy()
    tmp["atr"] = df["atr" + SUFFIX_1H]
    tmp = track_structure(find_pivots(tmp))
    df["last_hl" + SUFFIX_1H] = tmp["last_hl"]
    df["choch_bear" + SUFFIX_1H] = tmp["choch_bear"]
    df["last_lh" + SUFFIX_1H] = tmp["last_lh"]        # A2 — ancre du trailing G2 short
    df["choch_bull" + SUFFIX_1H] = tmp["choch_bull"]  # A2 — miroir de l'etat CHoCH
    # G6 = EVENEMENT de cassure (decision Jonas 2026-07-10, docs/03 par.3.4) : la bougie ou
    # l'etat choch_bear_1h PASSE de faux a vrai en cloture. L'etat persistant reste journalise
    # (choch_bear_1h). shift(1) = passe seul => aucun look-ahead ; warm-up => False (fill_value).
    choch_state = df["choch_bear" + SUFFIX_1H]
    df["choch_bear_event" + SUFFIX_1H] = _event(choch_state)
    # A2 — G6 cote SHORT : l'evenement adverse d'une position vendeuse est le CHoCH HAUSSIER.
    df["choch_bull_event" + SUFFIX_1H] = _event(df["choch_bull" + SUFFIX_1H])
    # C3 (decision Jonas 2026-08-03) — Bollinger(20,2) sur 1h. CALCULEES ET JOURNALISEES,
    # JAMAIS decisionnelles en V1 : docs/05 par.5.3 l'exige, et les cabler dans un score
    # consommerait un essai de plus sur un budget de tests deja depasse. Elles accumulent
    # la donnee pour etre testables plus tard sur les barres, pas sur 128 trades.
    bb_up, bb_mid, bb_low = talib.BBANDS(
        _f64(df["close"]), timeperiod=params.BBANDS_PERIOD,
        nbdevup=params.BBANDS_STD, nbdevdn=params.BBANDS_STD,
    )
    df["bb_upper" + SUFFIX_1H] = bb_up
    df["bb_mid" + SUFFIX_1H] = bb_mid
    df["bb_lower" + SUFFIX_1H] = bb_low
    # PDR 11.2 — nouvelle bougie 4h. Garde NaT : avant la premiere bougie 4h
    # mergee il n'y a PAS de nouvelle donnee 4h (warm-up du merge).
    date4 = df["date" + SUFFIX_4H]
    df["new_4h"] = (date4 != date4.shift(1)) & date4.notna()
    df = rr_available(df)
    df = module_scores(df)
    return df


def add_indicators(df: pd.DataFrame, suffix: str = "") -> pd.DataFrame:
    """PDR 05.3 — EMA/RSI/MACD/ATR/ADX/vol_sma, noms natifs (+ suffix optionnel)."""
    df = df.copy()
    close, high, low = _f64(df["close"]), _f64(df["high"]), _f64(df["low"])
    volume = _f64(df["volume"])
    df[f"ema50{suffix}"] = talib.EMA(close, timeperiod=params.EMA_FAST)
    df[f"ema200{suffix}"] = talib.EMA(close, timeperiod=params.EMA_SLOW)
    df[f"rsi{suffix}"] = talib.RSI(close, timeperiod=params.RSI_PERIOD)
    _macd, _signal, hist = talib.MACD(
        close, fastperiod=params.MACD_FAST, slowperiod=params.MACD_SLOW,
        signalperiod=params.MACD_SIGNAL,
    )
    df[f"macd_hist{suffix}"] = hist
    df[f"atr{suffix}"] = talib.ATR(high, low, close, timeperiod=params.ATR_PERIOD)
    df[f"adx{suffix}"] = talib.ADX(high, low, close, timeperiod=params.ADX_PERIOD)
    df[f"vol_sma20{suffix}"] = talib.SMA(volume, timeperiod=params.VOL_SMA_PERIOD)
    return df


def find_pivots(df: pd.DataFrame, n: int = params.PIVOT_N, suffix: str = "") -> pd.DataFrame:
    """PDR 05.1 — fractals N=n (strictement superieur/inferieur aux n voisins).

    Seules les colonnes CONFIRMEES sortent : `pivot_high_conf`/`pivot_low_conf`,
    confirmees n bougies apres (= params.PIVOT_CONFIRM_SHIFT pour N=PIVOT_N), donc
    utilisables au temps t. Les fractals BRUTS restent des variables LOCALES (ph/pl) :
    ils repeignent par construction (ils regardent les n voisins FUTURS) et n'ont
    jamais ete decisionnels (M01) ni contractuels (contracts.py ne liste que les
    `_conf_4h`). Les poser sur le df faisait sortir `lookahead-analysis` en
    has_bias=Yes sur un faux positif — decision Jonas 2026-08-03 (A2).
    """
    df = df.copy()
    high, low = df["high"], df["low"]
    ph = pd.Series(True, index=df.index)
    pl = pd.Series(True, index=df.index)
    for k in range(1, n + 1):
        ph = ph & (high > high.shift(k)) & (high > high.shift(-k))
        pl = pl & (low < low.shift(k)) & (low < low.shift(-k))
    df[f"pivot_high_conf{suffix}"] = ph.shift(n, fill_value=False)
    df[f"pivot_low_conf{suffix}"] = pl.shift(n, fill_value=False)
    return df


def track_structure(df: pd.DataFrame) -> pd.DataFrame:
    """PDR 05.1 / M01 — machine a etats sur les pivots CONFIRMES (frame natif).

    Produit : last_ph, last_hl (dernier HL confirme — PDR 03.3, CHoCH),
    hh_hl_intact (etiquettes du dernier swing = HH ET HL — sortie "HH/HL" de
    M01, consommee par s_structure 0,7), bos_bull, bos_fresh, choch_bear.
    Requiert find_pivots(n=PIVOT_N) et une colonne `atr` (add_indicators).
    """
    df = df.copy()
    n = params.PIVOT_N
    conf_h, conf_l = df["pivot_high_conf"], df["pivot_low_conf"]
    # Prix du pivot connu SEULEMENT a la confirmation (+n) — anti-repaint M01.
    ph_price = df["high"].shift(n).where(conf_h)
    pl_price = df["low"].shift(n).where(conf_l)
    last_ph = ph_price.ffill()
    last_pl = pl_price.ffill()  # dernier pivot low TOUTE etiquette (interne)
    df["last_ph"] = last_ph
    df["last_pl"] = last_pl                   # A2 — dernier pivot low confirme (BOS baissier)
    # Etiquettes : HH si nouveau pivot high > precedent, HL si pivot low > precedent
    # (premier pivot : pas d'etiquette => False, structure neutre).
    is_hh = ph_price > last_ph.shift(1)
    is_hl = pl_price > last_pl.shift(1)
    # A2 — miroirs : LL si nouveau pivot low < precedent, LH si pivot high < precedent.
    # Strictement l'inverse des deux lignes ci-dessus, meme anti-repaint (prix connu a +n).
    is_ll = pl_price < last_pl.shift(1)
    is_lh = ph_price < last_ph.shift(1)
    df["last_hl"] = pl_price.where(is_hl).ffill()
    df["last_lh"] = ph_price.where(is_lh).ffill()   # A2 — ancre du SL short (03.3 miroir)
    hh_state = _bool(is_hh.where(conf_h).ffill())
    hl_state = _bool(is_hl.where(conf_l).ffill())
    df["hh_hl_intact"] = hh_state & hl_state  # 05.1 : "sequence HH/HL intacte"
    ll_state = _bool(is_ll.where(conf_l).ffill())
    lh_state = _bool(is_lh.where(conf_h).ffill())
    df["ll_lh_intact"] = ll_state & lh_state  # A2 — "sequence LL/LH intacte" (miroir)
    # BOS haussier : cassure du dernier PH confirme + displacement (corps >= 1xATR).
    body = (df["close"] - df["open"]).abs()
    displacement = body >= params.BOS_DISPLACEMENT_ATR * df["atr"]
    df["bos_bull"] = (df["close"] > last_ph) & displacement
    # A2 — BOS baissier : cassure du dernier PL confirme, MEME exigence de displacement.
    df["bos_bear"] = (df["close"] < last_pl) & displacement
    # Fraicheur : BOS "frais" pendant BOS_FRESH_CANDLES_4H bougies (05.1).
    df["bos_fresh"] = _fresh(df["bos_bull"])
    df["bos_fresh_bear"] = _fresh(df["bos_bear"])   # A2 — miroir
    df["choch_bear"] = df["close"] < df["last_hl"]
    df["choch_bull"] = df["close"] > df["last_lh"]  # A2 — structure qui se retourne A LA HAUSSE
    return df


def _fresh(flag: pd.Series) -> pd.Series:
    """PDR 05.1 — evenement "frais" pendant BOS_FRESH_CANDLES_4H bougies."""
    return (flag.astype(float)
            .rolling(params.BOS_FRESH_CANDLES_4H, min_periods=1)
            .max() > 0)


def _clusters(prices: np.ndarray, tol: float) -> list[tuple[float, int]]:
    """PDR 05.2 — regroupe des prix TRIES croissants tant que l'ecart au centre
    (moyenne courante) du cluster est <= tol. Retourne [(niveau, touches), ...]."""
    out: list[tuple[float, int]] = []
    total, count = 0.0, 0
    for price in prices:
        if count and abs(price - total / count) <= tol:
            total += price
            count += 1
        else:
            if count:
                out.append((total / count, count))
            total, count = price, 1
    if count:
        out.append((total / count, count))
    return out


def sr_levels(
    df: pd.DataFrame,
    window: int = params.SR_WINDOW_4H,
    tol_atr: float = params.SR_CLUSTER_TOL_ATR,
) -> pd.DataFrame:
    """PDR 05.2 / M01 — nearest_res, nearest_sup, res_touches par clustering des
    pivots CONFIRMES des `window` dernieres bougies (highs = resistances, lows =
    supports). Boucle Python assumee (M01 : df 4h court, 1 recalcul/bougie 4h).
    """
    df = df.copy()
    n = params.PIVOT_N
    ph = _f64(df["high"].shift(n).where(_bool(df["pivot_high_conf"])))
    pl = _f64(df["low"].shift(n).where(_bool(df["pivot_low_conf"])))
    close = _f64(df["close"])
    atr = _f64(df["atr"])
    size = len(df)
    res = np.full(size, np.nan)
    sup = np.full(size, np.nan)
    touches = np.full(size, np.nan)
    for i in range(size):
        tol = tol_atr * atr[i]
        if not np.isfinite(tol):
            continue  # warm-up ATR : pas de niveau exploitable
        lo = max(0, i - window + 1)
        highs = ph[lo:i + 1]
        lows = pl[lo:i + 1]
        res_levels = _clusters(np.sort(highs[np.isfinite(highs)]), tol)
        sup_levels = _clusters(np.sort(lows[np.isfinite(lows)]), tol)
        above = [(level, t) for level, t in res_levels if level > close[i]]
        if above:
            res[i], touches[i] = min(above, key=lambda lt: lt[0])
        below = [level for level, _t in sup_levels if level < close[i]]
        if below:
            sup[i] = max(below)
    df["nearest_res"] = res
    df["nearest_sup"] = sup
    df["res_touches"] = touches
    return df


def rr_available(df: pd.DataFrame) -> pd.DataFrame:
    """PDR 05.2 / BUILD_NOTES 3 — rr_dispo sur le df 1h merge, MEME SL que 03.3.

    LONG  : sl_est = last_hl_4h - SL_HL_ATR_BUFFER x atr_4h ; fallback
            close - SL_FALLBACK_ATR_MULT x atr_4h si HL inexploitable (NaN ou HL >= close).
            rr_dispo = (nearest_res_4h - close) / (close - sl_est).
    SHORT (A2) : miroir strict — sl_est = last_lh_4h + buffer x atr_4h ; fallback
            close + SL_FALLBACK_ATR_MULT x atr_4h si LH inexploitable (NaN ou LH <= close).
            rr_dispo_short = (close - nearest_sup_4h) / (sl_est - close).
    Denominateur <= 0 ou niveau cible absent => NaN (=> s_sr = 0, jamais d'infini).
    """
    df = df.copy()
    close = df["close"]
    atr4 = df["atr" + SUFFIX_4H]
    hl = df["last_hl" + SUFFIX_4H]
    sl_est = (hl - params.SL_HL_ATR_BUFFER * atr4).where(
        hl.notna() & (hl < close),
        close - params.SL_FALLBACK_ATR_MULT * atr4,
    )
    risk = close - sl_est
    df["rr_dispo"] = (df["nearest_res" + SUFFIX_4H] - close) / risk.where(risk > 0)

    lh = df["last_lh" + SUFFIX_4H]
    sl_est_s = (lh + params.SL_HL_ATR_BUFFER * atr4).where(
        lh.notna() & (lh > close),
        close + params.SL_FALLBACK_ATR_MULT * atr4,
    )
    risk_s = sl_est_s - close
    df["rr_dispo" + contracts.SHORT_SUFFIX] = (
        (close - df["nearest_sup" + SUFFIX_4H]) / risk_s.where(risk_s > 0))
    return df


def candle_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """PDR 05.4 + idee 9 — TOUTES les fonctions talib CDL* (~60), journalisees
    comme dataset FreqAI V2, + pin bar bullish custom. Noms BUILD_NOTES 5 :
    cdl_<nom talib sans prefixe CDL, minuscules>."""
    df = df.copy()
    op, hi, lo, cl = (_f64(df[c]) for c in ("open", "high", "low", "close"))
    cols: dict[str, np.ndarray] = {}
    for name in talib.get_function_groups()[_TALIB_CDL_GROUP]:
        cols[_cdl_col(name)] = getattr(talib, name)(op, hi, lo, cl)
    # Pin bar bullish (05.4) : meche basse >= 2 x corps ET cloture dans le tiers
    # haut de la bougie. Sortie 100/0 comme les CDL talib.
    body = np.abs(cl - op)
    lower_wick = np.minimum(op, cl) - lo
    top_third = hi - (hi - lo) * params.PIN_BAR_CLOSE_TOP_FRACTION
    is_pin = (lower_wick >= params.PIN_BAR_WICK_BODY_RATIO * body) & (cl >= top_third)
    cols[PINBAR_COL] = np.where(is_pin, params.CDL_BULLISH, 0)
    # A2 — pin bar BEARISH, miroir strict : meche HAUTE >= 2 x corps ET cloture dans le
    # tiers BAS. Sortie -100/0, convention talib des patterns baissiers.
    upper_wick = hi - np.maximum(op, cl)
    bottom_third = lo + (hi - lo) * params.PIN_BAR_CLOSE_BOTTOM_FRACTION
    is_pin_bear = (upper_wick >= params.PIN_BAR_WICK_BODY_RATIO * body) & (cl <= bottom_third)
    cols[PINBAR_BEAR_COL] = np.where(is_pin_bear, params.CDL_BEARISH, 0)
    return pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)


def _score_structure(df, bos, bos_fresh, choch, intact, trend_ctx, warm):
    """PDR 05.1 — bareme s_structure, INDEPENDANT du sens : le sens vit dans les series
    passees en argument (BOS haussier + HH/HL pour le long, BOS baissier + LL/LH pour le
    short). Ordre BOS-frais/CHoCH pilote par l'A/B Jonas 09/07 (BUILD_NOTES)."""
    # "dernier evenement = CHoCH adverse" : CHoCH plus recent que le dernier BOS.
    pos = pd.Series(np.arange(len(df), dtype=float), index=df.index)
    last_bos = pos.where(bos).ffill()
    last_choch = pos.where(choch).ffill()
    choch_last = last_choch.notna() & (last_choch > last_bos.fillna(-1.0))
    bos_cond = (bos_fresh & trend_ctx, _S1)   # 05.1 : 1,0 — BOS frais ET contexte de tendance
    choch_cond = (choch_last, _S0)            # 05.1 : 0 — dernier evenement = CHoCH adverse
    ranked = [choch_cond, bos_cond] if params.S_STRUCTURE_CHOCH_PRIORITY else [bos_cond, choch_cond]
    return np.select(
        [
            warm,                       # M01 invariant 3 : warm-up => 0
            ranked[0][0],
            ranked[1][0],
            intact & ~bos_fresh,        # 05.1 : 0,7 — sequence intacte, continuation
        ],
        [_S0, ranked[0][1], ranked[1][1], _S07],
        default=_S03,                   # 05.1 : 0,3 — structure neutre
    )


def _score_momentum(band, soft_band, aligned, amplifying):
    """PDR 05.3 — bareme s_momentum. `band`/`soft_band` = bandes RSI (haussieres ou leur
    miroir A2) ; `aligned` = histogramme MACD dans le sens du trade ; `amplifying` = il
    s'amplifie vs la bougie 4h precedente.

    ⚠️ Asymetrie VOULUE du PDR, conservee telle quelle : le score PLEIN exige
    l'amplification, le score 0,5 ne l'exige PAS (bande large + sens suffisent).
    """
    return np.select(
        [band & aligned & amplifying, soft_band & aligned],
        [_S1, _S05],
        default=_S0,                    # 05.3 : sur-extension ou pas de momentum
    )


def _score_sr(rr):
    """PDR 05.2 — bareme s_sr. rr NaN => 0 (le gate RR coupe de toute facon)."""
    return np.select([rr >= params.SR_RR_FULL, rr >= params.RR_MIN], [_S1, _S07], default=_S0)


def _score_patterns(df, new4, atr4, bos, pattern_cols, signe):
    """PDR 05.4 — bareme s_patterns. `pattern_cols` = colonnes CDL du sens vise,
    `signe` = params.CDL_BULLISH (long) ou params.CDL_BEARISH (short)."""
    hit = pd.Series(False, index=df.index)
    for col in pattern_cols:
        hit = hit | (df[col] == signe)
    # Le doji reste lu a +100 : c'est une INDECISION, elle disqualifie une cassure dans
    # les DEUX sens (05.4). Il n'a pas de version baissiere.
    doji = df[_cdl_col(params.FILTER_DOJI) + SUFFIX_4H] == params.CDL_BULLISH
    bos_prev = _prev_4h(bos.astype(float), new4).fillna(0.0) > 0
    recent = hit.copy()  # pattern dans les PATTERN_RECENT_CANDLES_4H bougies
    older = hit.astype(float)
    for _ in range(params.PATTERN_RECENT_CANDLES_4H - 1):
        older = _prev_4h(older, new4)
        recent = recent | (older.fillna(0.0) > 0)
    return np.select(
        [
            atr4.isna(),                 # warm-up : BOS indefini => 0 (M01)
            bos & doji,                  # 05.4 : 0 — doji sur la bougie de cassure
            hit & (bos | bos_prev),      # 05.4 : 1,0 — pattern sur cassure/suivante
            recent,                      # 05.4 : 0,5 — pattern < 3 bougies 4h
        ],
        [_S0, _S0, _S1, _S05],
        default=_S03,                    # 05.4 : 0,3 — absence non disqualifiante
    )


def module_scores(df: pd.DataFrame) -> pd.DataFrame:
    """PDR 05 — les 5 scores discrets, table-driven (np.select), valeurs
    STRICTEMENT dans params.SCORE_VALUES (M01, BUILD_NOTES 6).

    A2 (2026-08-03) : produit DEUX jeux — `s_*` (haussier) et `s_*_short` (baissier).
    Meme bareme, memes seuils, seule la polarite des predicats change : le short
    n'introduit AUCUN degre de liberte nouveau (contrainte du budget de tests, docs/01).
    S'execute sur le df 1h merge : requiert *_4h, volume_4h, new_4h, rr_dispo.
    NaN de warm-up => score 0 (M01 invariant 3) — jamais de fillna sur les prix.
    """
    df = df.copy()
    new4 = _bool(df["new_4h"])
    close = df["close"]
    adx = df["adx" + SUFFIX_4H]
    e50 = df["ema50" + SUFFIX_4H]
    e200 = df["ema200" + SUFFIX_4H]
    atr4 = df["atr" + SUFFIX_4H]
    rsi = df["rsi" + SUFFIX_4H]
    hist = df["macd_hist" + SUFFIX_4H]
    sfx = contracts.SHORT_SUFFIX
    warm = adx.isna() | e50.isna() | e200.isna() | atr4.isna()
    trend_min = adx >= params.ADX_TREND_MIN

    # ---- s_structure (05.1 ; BUILD_NOTES 4 : contexte TREND = conditions PRIX,
    # le veto macro/F&G vit dans regimes.py)
    bos = _bool(df["bos_bull" + SUFFIX_4H])
    bos_bear = _bool(df["bos_bear" + SUFFIX_4H])
    df["s_structure"] = _score_structure(
        df, bos, _bool(df["bos_fresh" + SUFFIX_4H]), _bool(df["choch_bear" + SUFFIX_4H]),
        _bool(df["hh_hl_intact" + SUFFIX_4H]),
        trend_min & (e50 > e200) & (close > e50), warm)
    df["s_structure" + sfx] = _score_structure(   # A2 — contexte de tendance INVERSE
        df, bos_bear, _bool(df["bos_fresh_bear" + SUFFIX_4H]),
        _bool(df["choch_bull" + SUFFIX_4H]), _bool(df["ll_lh_intact" + SUFFIX_4H]),
        trend_min & (e50 < e200) & (close < e50), warm)

    # ---- s_momentum (05.3) — histogramme MACD dans le sens du trade ET qui s'amplifie
    prev_hist = _prev_4h(hist, new4)
    df["s_momentum"] = _score_momentum(
        rsi.between(params.RSI_MOM_LOW, params.RSI_MOM_HIGH),
        rsi.between(params.RSI_MOM_SOFT_LOW, params.RSI_MOM_LOW, inclusive="left")
        | rsi.between(params.RSI_MOM_HIGH, params.RSI_MOM_SOFT_HIGH, inclusive="right"),
        hist > 0, hist > prev_hist)
    df["s_momentum" + sfx] = _score_momentum(     # A2 — miroir autour de 50, hist < 0
        rsi.between(params.RSI_MOM_SHORT_LOW, params.RSI_MOM_SHORT_HIGH),
        rsi.between(params.RSI_MOM_SHORT_HIGH, params.RSI_MOM_SHORT_SOFT_HIGH, inclusive="right")
        | rsi.between(params.RSI_MOM_SHORT_SOFT_LOW, params.RSI_MOM_SHORT_LOW, inclusive="left"),
        hist < 0, hist < prev_hist)

    # ---- s_sr (05.2)
    df["s_sr"] = _score_sr(df["rr_dispo"])
    df["s_sr" + sfx] = _score_sr(df["rr_dispo" + sfx])   # A2 — RR vers le SUPPORT

    # ---- s_patterns (05.4)
    df["s_patterns"] = _score_patterns(
        df, new4, atr4, bos,
        [_cdl_col(p) + SUFFIX_4H for p in params.ENTRY_CDL_PATTERNS] + [PINBAR_COL + SUFFIX_4H],
        params.CDL_BULLISH)
    df["s_patterns" + sfx] = _score_patterns(     # A2 — patterns baissiers sur BOS baissier
        df, new4, atr4, bos_bear,
        [_cdl_col(p) + SUFFIX_4H for p in params.ENTRY_CDL_PATTERNS_SHORT]
        + [PINBAR_BEAR_COL + SUFFIX_4H],
        params.CDL_BEARISH)

    # ---- s_volume (05.5) — SANS SENS par construction : un volume fort confirme un
    # mouvement, il ne dit pas dans quelle direction. Le short reutilise donc le meme
    # score, il n'est pas duplique par symetrie de facade.
    vol = df["volume" + SUFFIX_4H]
    vsma = df["vol_sma20" + SUFFIX_4H]
    df["s_volume"] = np.select(
        [vol >= params.VOL_STRONG_MULT * vsma, vol >= params.VOL_OK_MULT * vsma],
        [_S1, _S05],
        default=_S0,
    )
    df["s_volume" + sfx] = df["s_volume"]
    return df
