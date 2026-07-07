"""M01 — features.py : les yeux du bot (docs/modules/M01, PDR 05, docs/11 par.11.3).

Fonctions PURES : DataFrame in -> DataFrame out. pandas/numpy/talib uniquement —
aucun I/O, aucun reseau, aucun import freqtrade (BUILD_NOTES T1).
Priorite absolue (M01) : zero look-ahead, zero repaint — tout pivot decisionnel
est confirme n bougies plus tard (params.PIVOT_CONFIRM_SHIFT pour N=PIVOT_N) ;
les pivots BRUTS (pivot_high/pivot_low) repeignent PAR CONSTRUCTION et ne servent
JAMAIS a decider (M01).

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


def _prev_4h(s: pd.Series, new_4h: pd.Series) -> pd.Series:
    """Valeur de la bougie 4h PRECEDENTE sur le df 1h merge (PDR 11.2) : les
    colonnes 4h se repetent intra-bougie, on lit la valeur a la ligne new_4h
    (ou shift(1) tombe sur la bougie precedente) puis on la propage."""
    return s.shift(1).where(new_4h).ffill()


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """M01 / BUILD_NOTES 2 — etage 1h merge, ordre fixe.

    Requiert le df 1h merge par freqtrade (*_4h/*_1d, date_4h presents).
    Ajoute : atr_1h, last_hl_1h, choch_bear_1h (G2/G6), new_4h (PDR 11.2),
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

    `pivot_high`/`pivot_low` : BRUTS, repeignent (voisins futurs) — JAMAIS
    decisionnels (M01). `pivot_high_conf`/`pivot_low_conf` : confirmes n bougies
    apres (= params.PIVOT_CONFIRM_SHIFT pour N=PIVOT_N), utilisables au temps t.
    """
    df = df.copy()
    high, low = df["high"], df["low"]
    ph = pd.Series(True, index=df.index)
    pl = pd.Series(True, index=df.index)
    for k in range(1, n + 1):
        ph = ph & (high > high.shift(k)) & (high > high.shift(-k))
        pl = pl & (low < low.shift(k)) & (low < low.shift(-k))
    df[f"pivot_high{suffix}"] = ph
    df[f"pivot_low{suffix}"] = pl
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
    # Etiquettes : HH si nouveau pivot high > precedent, HL si pivot low > precedent
    # (premier pivot : pas d'etiquette => False, structure neutre).
    is_hh = ph_price > last_ph.shift(1)
    is_hl = pl_price > last_pl.shift(1)
    df["last_hl"] = pl_price.where(is_hl).ffill()
    hh_state = _bool(is_hh.where(conf_h).ffill())
    hl_state = _bool(is_hl.where(conf_l).ffill())
    df["hh_hl_intact"] = hh_state & hl_state  # 05.1 : "sequence HH/HL intacte"
    # BOS haussier : cassure du dernier PH confirme + displacement (corps >= 1xATR).
    body = (df["close"] - df["open"]).abs()
    df["bos_bull"] = (df["close"] > last_ph) & (
        body >= params.BOS_DISPLACEMENT_ATR * df["atr"]
    )
    # Fraicheur : BOS "frais" pendant BOS_FRESH_CANDLES_4H bougies (05.1).
    df["bos_fresh"] = (
        df["bos_bull"]
        .astype(float)
        .rolling(params.BOS_FRESH_CANDLES_4H, min_periods=1)
        .max()
        > 0
    )
    df["choch_bear"] = df["close"] < df["last_hl"]
    return df


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

    sl_est = last_hl_4h - SL_HL_ATR_BUFFER x atr_4h ; fallback
    close - SL_FALLBACK_ATR_MULT x atr_4h si HL inexploitable (NaN ou HL >= close).
    rr_dispo = (nearest_res_4h - close) / (close - sl_est) ; denominateur <= 0 ou
    resistance absente => NaN (=> s_sr = 0, jamais d'infini).
    """
    df = df.copy()
    close = df["close"]
    hl = df["last_hl" + SUFFIX_4H]
    atr4 = df["atr" + SUFFIX_4H]
    sl_est = (hl - params.SL_HL_ATR_BUFFER * atr4).where(
        hl.notna() & (hl < close),
        close - params.SL_FALLBACK_ATR_MULT * atr4,
    )
    risk = close - sl_est
    df["rr_dispo"] = (df["nearest_res" + SUFFIX_4H] - close) / risk.where(risk > 0)
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
    return pd.concat([df, pd.DataFrame(cols, index=df.index)], axis=1)


def module_scores(df: pd.DataFrame) -> pd.DataFrame:
    """PDR 05 — les 5 scores discrets, table-driven (np.select), valeurs
    STRICTEMENT dans params.SCORE_VALUES (M01, BUILD_NOTES 6).

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

    # ---- s_structure (05.1 ; BUILD_NOTES 4 : contexte TREND = conditions PRIX,
    # le veto macro/F&G vit dans regimes.py)
    bos = _bool(df["bos_bull" + SUFFIX_4H])
    bos_fresh = _bool(df["bos_fresh" + SUFFIX_4H])
    choch = _bool(df["choch_bear" + SUFFIX_4H])
    intact = _bool(df["hh_hl_intact" + SUFFIX_4H])
    trend_ctx = (adx >= params.ADX_TREND_MIN) & (e50 > e200) & (close > e50)
    # "dernier evenement = CHoCH baissier" : CHoCH plus recent que le dernier BOS.
    pos = pd.Series(np.arange(len(df), dtype=float), index=df.index)
    last_bos = pos.where(bos).ffill()
    last_choch = pos.where(choch).ffill()
    choch_last = last_choch.notna() & (last_choch > last_bos.fillna(-1.0))
    warm_structure = adx.isna() | e50.isna() | e200.isna() | atr4.isna()
    df["s_structure"] = np.select(
        [
            warm_structure,             # M01 invariant 3 : warm-up => 0
            bos_fresh & trend_ctx,      # 05.1 : 1,0 — BOS frais ET contexte TREND
            choch_last,                 # 05.1 : 0 — dernier evenement = CHoCH
            intact & ~bos_fresh,        # 05.1 : 0,7 — HH/HL intacte, continuation
        ],
        [_S0, _S1, _S0, _S07],
        default=_S03,                   # 05.1 : 0,3 — structure neutre
    )

    # ---- s_momentum (05.3)
    rsi = df["rsi" + SUFFIX_4H]
    hist = df["macd_hist" + SUFFIX_4H]
    growing = hist > _prev_4h(hist, new4)  # croissant vs bougie 4h precedente
    full = rsi.between(params.RSI_MOM_LOW, params.RSI_MOM_HIGH) & (hist > 0) & growing
    soft_band = rsi.between(
        params.RSI_MOM_SOFT_LOW, params.RSI_MOM_LOW, inclusive="left"
    ) | rsi.between(params.RSI_MOM_HIGH, params.RSI_MOM_SOFT_HIGH, inclusive="right")
    df["s_momentum"] = np.select(
        [full, soft_band & (hist > 0)],
        [_S1, _S05],
        default=_S0,                    # 05.3 : sur-extension > 75 ou pas de momentum
    )

    # ---- s_sr (05.2) — rr NaN => 0 (le gate RR coupe de toute facon)
    rr = df["rr_dispo"]
    df["s_sr"] = np.select(
        [rr >= params.SR_RR_FULL, rr >= params.RR_MIN],
        [_S1, _S07],
        default=_S0,
    )

    # ---- s_patterns (05.4)
    bullish = pd.Series(False, index=df.index)
    entry_cols = [_cdl_col(p) + SUFFIX_4H for p in params.ENTRY_CDL_PATTERNS]
    for col in [*entry_cols, PINBAR_COL + SUFFIX_4H]:
        bullish = bullish | (df[col] == params.CDL_BULLISH)
    doji = df[_cdl_col(params.FILTER_DOJI) + SUFFIX_4H] == params.CDL_BULLISH
    bos_prev = _prev_4h(bos.astype(float), new4).fillna(0.0) > 0
    recent = bullish.copy()  # pattern dans les PATTERN_RECENT_CANDLES_4H bougies
    older = bullish.astype(float)
    for _ in range(params.PATTERN_RECENT_CANDLES_4H - 1):
        older = _prev_4h(older, new4)
        recent = recent | (older.fillna(0.0) > 0)
    df["s_patterns"] = np.select(
        [
            atr4.isna(),                 # warm-up : BOS indefini => 0 (M01)
            bos & doji,                  # 05.4 : 0 — doji sur la bougie de cassure
            bullish & (bos | bos_prev),  # 05.4 : 1,0 — pattern sur cassure/suivante
            recent,                      # 05.4 : 0,5 — pattern < 3 bougies 4h
        ],
        [_S0, _S0, _S1, _S05],
        default=_S03,                    # 05.4 : 0,3 — absence non disqualifiante
    )

    # ---- s_volume (05.5)
    vol = df["volume" + SUFFIX_4H]
    vsma = df["vol_sma20" + SUFFIX_4H]
    df["s_volume"] = np.select(
        [vol >= params.VOL_STRONG_MULT * vsma, vol >= params.VOL_OK_MULT * vsma],
        [_S1, _S05],
        default=_S0,
    )
    return df
