"""Tests M01 — features.py (docs/modules/M01 bas de spec, PDR 05.6, BUILD_NOTES T1).

Le merge 4h->1h est simule ICI comme le fait merge_informative_pair freqtrade :
colonnes 4h suffixees, disponibles seulement APRES la cloture 4h (date + 4h),
puis ffill sur l'index 1h (clotures seulement, jamais la bougie 4h en cours).
"""

import numpy as np
import pandas as pd
import pytest
from conftest import make_ohlcv

from arit_lib import contracts, features, params

SCORE_COLS = ["s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume"]
# A2 — les scores baissiers sont soumis au MEME contrat de discretion (05 / M01).
SCORE_COLS += [c + contracts.SHORT_SUFFIX for c in SCORE_COLS]
BB_COLS = ["bb_upper_1h", "bb_mid_1h", "bb_lower_1h"]  # C3 (03/08) — journalisees only
COMPUTE_ALL_COLS = [
    "atr_1h", "last_hl_1h", "choch_bear_1h", "choch_bear_event_1h",
    "new_4h", "rr_dispo", *BB_COLS, *SCORE_COLS,
]
# Bougie de reference : TR = 2 constant => ATR(14) = 2 exactement (Wilder).
BASE = (100.0, 101.0, 99.0, 100.2)
TF_MINUTES = {"1h": 60, "4h": 240, "1d": 1440}


# --------------------------------------------------------------- helpers locaux
def _df_ohlc(rows, timeframe="4h", start="2024-01-01"):
    """DataFrame freqtrade-like depuis [(open, high, low, close), ...]."""
    op, hi, lo, cl = (np.array(x, dtype=float) for x in zip(*rows))
    freq = {"1h": "1h", "4h": "4h"}[timeframe]
    date = pd.date_range(start=start, periods=len(rows), freq=freq, tz="UTC")
    return pd.DataFrame({
        "date": date, "open": op, "high": hi, "low": lo, "close": cl,
        "volume": np.full(len(rows), 100.0),
    })


def merge_informative(df_base, df_inf, suffix, tf_minutes):
    """Simule freqtrade merge_informative_pair (BUILD_NOTES 1) : la bougie
    informative n'apparait qu'apres SA CLOTURE (date + timeframe), puis ffill."""
    inf = df_inf.copy()
    available = inf["date"] + pd.Timedelta(minutes=tf_minutes)
    inf.columns = [f"{c}{suffix}" for c in inf.columns]
    inf["_avail"] = available
    out = df_base.merge(inf, how="left", left_on="date", right_on="_avail")
    out = out.drop(columns=["_avail"])
    inf_cols = [c for c in out.columns if c.endswith(suffix)]
    out[inf_cols] = out[inf_cols].ffill()
    return out


def apply_4h(df):
    """Etage natif 4h/1d, ordre fixe M01 (tenu par M07 au runtime)."""
    df = features.add_indicators(df)
    df = features.find_pivots(df)
    df = features.track_structure(df)
    df = features.sr_levels(df)
    df = features.candle_patterns(df)
    return df


def build_merged(n4=320, kind="trend", seed=42):
    """Flux M07 simule : base 1h + informatives 4h/1d featurees + merges."""
    df_1h = make_ohlcv(kind, n=n4 * 4, seed=seed, timeframe="1h")
    df_4h = apply_4h(make_ohlcv(kind, n=n4, seed=seed + 1, timeframe="4h"))
    df_1d = features.add_indicators(
        make_ohlcv(kind, n=max(60, n4 // 6 + 10), seed=seed + 2, timeframe="1d")
    )
    merged = merge_informative(df_1h, df_4h, "_4h", TF_MINUTES["4h"])
    return merge_informative(merged, df_1d, "_1d", TF_MINUTES["1d"])


def _score_df(n=8, **overrides):
    """df 1h merge minimal pour module_scores. new_4h=True partout : chaque
    ligne joue une bougie 4h (les helpers _prev_4h == shift(1), cas lisibles)."""
    base = {
        "close": 100.0, "new_4h": True,
        "adx_4h": 30.0, "ema50_4h": 90.0, "ema200_4h": 80.0, "atr_4h": 2.0,
        "bos_bull_4h": False, "bos_fresh_4h": False, "choch_bear_4h": False,
        "hh_hl_intact_4h": False,
        "rsi_4h": 60.0, "macd_hist_4h": 1.0,
        "rr_dispo": np.nan,
        "cdl_engulfing_4h": 0, "cdl_hammer_4h": 0, "cdl_doji_4h": 0,
        "cdl_pinbar_bull_4h": 0,
        "volume_4h": 50.0, "vol_sma20_4h": 100.0,
        # A2 — miroirs baissiers (defauts neutres : le short ne se declenche jamais
        # tout seul dans les cas de test haussiers, et reciproquement).
        "bos_bear_4h": False, "bos_fresh_bear_4h": False, "choch_bull_4h": False,
        "ll_lh_intact_4h": False,
        "rr_dispo_short": np.nan,
        "cdl_shootingstar_4h": 0, "cdl_pinbar_bear_4h": 0,
    }
    df = pd.DataFrame({k: [v] * n for k, v in base.items()})
    for k, v in overrides.items():
        df[k] = v
    return df


# ------------------------------------------------------------------- pivots 05.1
def test_pivot_confirme_exactement_a_plus_2():
    rows = [BASE] * 30
    rows[10] = (100.0, 103.0, 99.0, 100.2)   # pivot high
    rows[20] = (100.0, 101.0, 97.0, 100.2)   # pivot low
    df = _df_ohlc(rows)
    out = features.find_pivots(df)
    # A2 (03/08) : les fractals BRUTS ne sortent plus du tout — ils repeignent.
    assert "pivot_high" not in out.columns
    assert "pivot_low" not in out.columns
    assert not out["pivot_high_conf"].iloc[:12].any()   # rien avant +2
    assert bool(out["pivot_high_conf"].iloc[12])        # exactement a +2
    assert not out["pivot_low_conf"].iloc[:22].any()
    assert bool(out["pivot_low_conf"].iloc[22])
    # Pas de repaint : donnees arretees a t => memes confirmations qu'en full.
    for t in (11, 12, 13, 25):
        part = features.find_pivots(df.iloc[:t].copy())
        for col in ("pivot_high_conf", "pivot_low_conf"):
            pd.testing.assert_series_equal(part[col], out[col].iloc[:t])


# ---------------------------------------------------------------- BOS/CHoCH 05.1
def test_bos_refuse_sans_displacement():
    def make(breakout):
        rows = [BASE] * 36
        rows[20] = (100.3, 101.8, 99.8, 100.4)  # pivot high 101.8, TR reste 2
        rows[29] = (100.0, 101.0, 99.0, 101.5)  # rapproche la cloture du breakout
        rows[30] = breakout
        return apply_4h(_df_ohlc(rows))

    small = make((101.5, 102.0, 100.0, 101.9))  # cloture > 101.8, corps 0.4 < 1xATR
    big = make((100.0, 102.2, 100.2, 102.2))    # cloture > 101.8, corps 2.2 >= 2
    assert small["atr"].iloc[30] == pytest.approx(2.0)
    assert small["last_ph"].iloc[30] == pytest.approx(101.8)
    assert not small["bos_bull"].iloc[30]       # displacement insuffisant => refus
    assert bool(big["bos_bull"].iloc[30])
    # Fraicheur : BOS_FRESH_CANDLES_4H bougies (3).
    assert big["bos_fresh"].iloc[30:33].all()
    assert not big["bos_fresh"].iloc[33]
    assert not small["bos_fresh"].iloc[30:34].any()


def test_choch_correct():
    rows = [BASE] * 36
    rows[10] = (100.0, 101.0, 97.0, 100.2)  # 1er pivot low : pas d'etiquette
    rows[20] = (100.0, 101.0, 98.0, 100.2)  # pivot low 98 > 97 => HL, confirme a 22
    rows[25] = (100.0, 101.0, 97.4, 97.5)   # cloture 97.5 < HL 98 => CHoCH
    df = apply_4h(_df_ohlc(rows))
    assert np.isnan(df["last_hl"].iloc[20])            # HL connu a la conf seulement
    assert df["last_hl"].iloc[22] == pytest.approx(98.0)
    assert not df["choch_bear"].iloc[22:25].any()
    assert bool(df["choch_bear"].iloc[25])
    assert not df["choch_bear"].iloc[26]               # cloture revenue au-dessus
    # Le pivot low 97.4 (LL, confirme a 27) ne remplace PAS le dernier HL.
    assert df["last_hl"].iloc[30] == pytest.approx(98.0)


def test_choch_bear_event_only_on_breakout_candle():
    # G6 = EVENEMENT de cassure (decision Jonas 2026-07-10, docs/03 §3.4) : la colonne
    # choch_bear_event_1h n'est vraie QUE sur la bougie ou l'etat passe de faux a vrai,
    # jamais sur les bougies suivantes ou l'etat choch_bear_1h persiste.
    out = features.compute_all(build_merged(n4=280, kind="gaps", seed=7))
    state = out["choch_bear_1h"].astype(bool).to_numpy()
    event = out["choch_bear_event_1h"].astype(bool).to_numpy()
    rising = state & ~np.concatenate(([False], state[:-1]))   # front montant de l'etat
    assert (event == rising).all()
    # Le scenario contient bien de la persistance d'etat (etat vrai >=2 bougies de suite)...
    persist = state & np.concatenate(([False], state[:-1]))
    assert persist.any()
    # ... et l'evenement ne s'y declenche jamais (que sur la bougie de cassure).
    assert not (event & persist).any()
    assert not (event & ~state).any()            # jamais d'evenement sans etat
    assert not bool(event[0])                    # warm-up (1re bougie) => False


# ----------------------------------------------------------------- S/R 05.2
def test_sr_clustering_ecarts_limites():
    atr_ref = 2.0  # TR constant par construction

    def make(delta):
        rows = [(100.0, 101.0, 99.0, 100.0)] * 36
        rows[18] = (100.0, 101.5, 99.5, 100.0)   # pivot high 101.5
        rows[25] = (100.0, 101.0, 99.0, 100.6)   # pre-positionne la cloture (TR=2)
        rows[26] = (100.6, 101.5 + delta, 99.5 + delta, 100.6)  # pivot high 2
        rows[27] = (100.6, 101.0, 99.0, 100.0)
        return apply_4h(_df_ohlc(rows))

    merged = make(0.49 * atr_ref)   # ecart 0.98 <= 0.5xATR(=1.0) => UN niveau
    assert merged["atr"].iloc[34] == pytest.approx(atr_ref)
    assert merged["nearest_res"].iloc[34] == pytest.approx(101.5 + 0.49)
    assert merged["res_touches"].iloc[34] == pytest.approx(2)

    split = make(0.51 * atr_ref)    # ecart 1.02 > 1.0 => DEUX niveaux distincts
    assert split["nearest_res"].iloc[34] == pytest.approx(101.5)
    assert split["res_touches"].iloc[34] == pytest.approx(1)
    assert np.isnan(split["nearest_sup"].iloc[34])   # aucun pivot low construit


# ------------------------------------------------------------------ rr_dispo 05.2
def _rr_df():
    return pd.DataFrame({
        "close":          [100.0, 100.0, 100.0, 100.0, 100.0],
        "last_hl_4h":     [98.0, np.nan, 100.2, 98.0, np.nan],
        "atr_4h":         [2.0, 2.0, 2.0, 2.0, 0.0],
        "nearest_res_4h": [104.4, 104.5, 103.0, np.nan, 104.0],
        # A2 — miroirs exacts : LH au-dessus du close, support en dessous.
        "last_lh_4h":     [102.0, np.nan, 99.8, 102.0, np.nan],
        "nearest_sup_4h": [95.6, 95.5, 97.0, np.nan, 96.0],
    })


def test_rr_dispo():
    rr = features.rr_available(_rr_df())["rr_dispo"]
    assert rr.iloc[0] == pytest.approx(2.0)   # SL = 98 - 0.1x2 = 97.8 ; 4.4/2.2
    assert rr.iloc[1] == pytest.approx(1.5)   # HL NaN => fallback SL = 100 - 3
    assert rr.iloc[2] == pytest.approx(1.0)   # HL >= close => fallback
    assert np.isnan(rr.iloc[3])               # pas de resistance => NaN
    assert np.isnan(rr.iloc[4])               # risque nul => NaN, jamais d'infini


def test_rr_dispo_short_est_le_miroir_exact():
    """A2 — memes chiffres que le long, geometrie retournee (05.2 miroir)."""
    rr = features.rr_available(_rr_df())["rr_dispo_short"]
    assert rr.iloc[0] == pytest.approx(2.0)   # SL = 102 + 0.1x2 = 102.2 ; 4.4/2.2
    assert rr.iloc[1] == pytest.approx(1.5)   # LH NaN => fallback SL = 100 + 3
    assert rr.iloc[2] == pytest.approx(1.0)   # LH <= close => fallback
    assert np.isnan(rr.iloc[3])               # pas de support => NaN
    assert np.isnan(rr.iloc[4])               # risque nul => NaN, jamais d'infini


# -------------------------------------------------------------------- scores 05
def test_s_structure_cas_construits():
    # 1,0 : BOS frais ET contexte TREND (BUILD_NOTES 4).
    out = features.module_scores(_score_df(
        n=6,
        bos_bull_4h=[False, True, False, False, False, False],
        bos_fresh_4h=[False, True, True, True, False, False],
    ))
    assert out["s_structure"].iloc[1] == 1.0
    # 0 : dernier evenement = CHoCH baissier, persiste tant que pas de BOS.
    out = features.module_scores(_score_df(
        n=6, choch_bear_4h=[False, False, True, False, False, False],
    ))
    assert out["s_structure"].iloc[2] == 0.0
    assert out["s_structure"].iloc[4] == 0.0
    # Un BOS posterieur au CHoCH reprend la main.
    out = features.module_scores(_score_df(
        n=6,
        choch_bear_4h=[False, True, False, False, False, False],
        bos_bull_4h=[False, False, False, True, False, False],
        bos_fresh_4h=[False, False, False, True, True, True],
    ))
    assert out["s_structure"].iloc[1] == 0.0
    assert out["s_structure"].iloc[3] == 1.0
    # 0,7 : sequence HH/HL intacte sans BOS frais.
    out = features.module_scores(_score_df(hh_hl_intact_4h=True))
    assert (out["s_structure"] == 0.7).all()
    # 0,3 : structure neutre.
    out = features.module_scores(_score_df())
    assert (out["s_structure"] == 0.3).all()
    # 0 : warm-up (input NaN), meme si le reste est favorable.
    out = features.module_scores(_score_df(adx_4h=np.nan, hh_hl_intact_4h=True))
    assert (out["s_structure"] == 0.0).all()
    # BOS frais HORS contexte TREND : ni 1,0 ni 0,7 => 0,3 (05.1 litteral).
    out = features.module_scores(_score_df(bos_fresh_4h=True, adx_4h=20.0))
    assert (out["s_structure"] == 0.3).all()


def test_s_structure_choch_priority_flag_ab(monkeypatch):
    # Bougie croisee : BOS frais (rolling) ET CHoCH posterieur => les deux
    # conditions vraies sur la MEME ligne (idx 1). Flag Jonas 09/07 (BUILD_NOTES).
    def crossing():
        return _score_df(
            n=3,
            bos_bull_4h=[True, False, False],
            bos_fresh_4h=[True, True, True],
            choch_bear_4h=[False, True, False],
        )

    # Defaut (False) = ordre actuel : BOS frais prime => 1,0.
    assert params.S_STRUCTURE_CHOCH_PRIORITY is False
    out = features.module_scores(crossing())
    assert out["s_structure"].iloc[1] == 1.0
    # Flag True : CHoCH prime sur le BOS frais => 0,0.
    monkeypatch.setattr(params, "S_STRUCTURE_CHOCH_PRIORITY", True)
    out = features.module_scores(crossing())
    assert out["s_structure"].iloc[1] == 0.0


def test_s_momentum_cas_construits():
    out = features.module_scores(_score_df(
        n=6,
        rsi_4h=[60.0, 60.0, 47.0, 72.0, 76.0, 60.0],
        macd_hist_4h=[0.5, 1.0, 1.0, 1.0, 1.0, 0.5],
    ))
    assert list(out["s_momentum"]) == [0.0, 1.0, 0.5, 0.5, 0.0, 0.0]
    # Bornes exactes : 50 et 70 inclus dans [50,70] ; 45 in [45,50) ; 75 in (70,75].
    out = features.module_scores(_score_df(
        n=4, rsi_4h=[50.0, 70.0, 45.0, 75.0], macd_hist_4h=[1.0, 2.0, 3.0, 4.0],
    ))
    assert list(out["s_momentum"]) == [0.0, 1.0, 0.5, 0.5]  # ligne 0 : pas de prec.
    # NaN warm-up => 0.
    out = features.module_scores(_score_df(rsi_4h=np.nan))
    assert (out["s_momentum"] == 0.0).all()


def test_s_sr_cas_construits():
    out = features.module_scores(_score_df(
        n=6, rr_dispo=[2.5, 2.0, 1.9, 1.5, 1.2, np.nan],
    ))
    assert list(out["s_sr"]) == [1.0, 1.0, 0.7, 0.7, 0.0, 0.0]


def test_s_patterns_cas_construits():
    f6 = [False] * 6
    # 1,0 : pattern bullish sur la bougie de cassure.
    out = features.module_scores(_score_df(
        n=6, bos_bull_4h=[*f6[:2], True, *f6[:3]],
        cdl_engulfing_4h=[0, 0, 100, 0, 0, 0],
    ))
    assert out["s_patterns"].iloc[2] == 1.0
    # ... ou sur la bougie SUIVANTE (hammer et pin bar comptent aussi).
    out = features.module_scores(_score_df(
        n=6, bos_bull_4h=[*f6[:2], True, *f6[:3]],
        cdl_hammer_4h=[0, 0, 0, 100, 0, 0],
    ))
    assert out["s_patterns"].iloc[3] == 1.0
    out = features.module_scores(_score_df(
        n=6, bos_bull_4h=[*f6[:2], True, *f6[:3]],
        cdl_pinbar_bull_4h=[0, 0, 100, 0, 0, 0],
    ))
    assert out["s_patterns"].iloc[2] == 1.0
    # 0,5 : pattern dans les 3 dernieres bougies 4h ; 0,3 au-dela / absence.
    out = features.module_scores(_score_df(
        n=6, cdl_engulfing_4h=[0, 100, 0, 0, 0, 0],
    ))
    assert list(out["s_patterns"]) == [0.3, 0.5, 0.5, 0.5, 0.3, 0.3]
    # 0 : doji sur la bougie de cassure, meme avec engulfing simultane.
    out = features.module_scores(_score_df(
        n=4, bos_bull_4h=[False, True, False, False],
        cdl_doji_4h=[0, 100, 0, 0], cdl_engulfing_4h=[0, 100, 0, 0],
    ))
    assert out["s_patterns"].iloc[1] == 0.0
    # 0 : warm-up ATR (BOS indefini), meme avec pattern present.
    out = features.module_scores(_score_df(atr_4h=np.nan, cdl_engulfing_4h=100))
    assert (out["s_patterns"] == 0.0).all()


def test_s_volume_cas_construits():
    out = features.module_scores(_score_df(
        n=5, volume_4h=[160.0, 150.0, 120.0, 100.0, 90.0],
    ))
    assert list(out["s_volume"]) == [1.0, 1.0, 0.5, 0.5, 0.0]
    out = features.module_scores(_score_df(vol_sma20_4h=np.nan, volume_4h=160.0))
    assert (out["s_volume"] == 0.0).all()


# ------------------------------------------------- contrat 11.3 + new_4h (11.2)
def test_contrat_colonnes_new_4h_et_scores_discrets():
    out = features.compute_all(build_merged())
    missing = [c for c in contracts.FEATURE_COLUMNS if c not in out.columns]
    assert not missing
    cdl_cols = [c for c in out.columns if c.startswith(contracts.CDL_PREFIX)]
    assert len(cdl_cols) >= 60                    # idee 9 : ~60 CDL journalisees
    for col in SCORE_COLS:                        # scores STRICTEMENT discrets
        assert set(np.unique(out[col])) <= set(params.SCORE_VALUES)
    # 11.2 : new_4h uniquement sur la ligne 1h qui suit une cloture 4h.
    idx = np.arange(len(out))
    expected = (idx >= 4) & (idx % 4 == 0)        # dates alignees, 1re dispo a 04:00
    assert (out["new_4h"].to_numpy() == expected).all()
    # Warm-up du merge : aucune donnee 4h => tous les scores a 0.
    assert (out.loc[:3, SCORE_COLS] == 0.0).all().all()


# ------------------------------------------------------------ invariants M01
def test_bollinger_1h_cablees_et_non_decisionnelles():
    """C3 (decision Jonas 03/08) — Bollinger(20,2) 1h posees, contractuelles, et INERTES.

    docs/05 par.5.3 : « calculees et journalisees (pas utilisees en entree V1) ». Le test
    verrouille les deux moities : la presence, ET le fait qu'aucun score ne bouge quand on
    detruit les bandes. Sans la seconde assertion, un cablage decisionnel passerait inapercu.
    """
    merged = build_merged(n4=280)
    out = features.compute_all(merged)
    for col in BB_COLS:
        assert col in out.columns
        assert col in contracts.FEATURE_COLUMNS      # 11.3 — nom contractuel
    # Bande centrale = SMA20 des clotures : verifie qu'on a bien BBANDS(20,2) et pas autre chose.
    expected_mid = merged["close"].rolling(params.BBANDS_PERIOD).mean()
    pd.testing.assert_series_equal(
        out["bb_mid_1h"].iloc[params.BBANDS_PERIOD:],
        expected_mid.iloc[params.BBANDS_PERIOD:],
        check_names=False,
    )
    assert (out["bb_upper_1h"] >= out["bb_mid_1h"]).where(out["bb_mid_1h"].notna()).all()
    # Inertie decisionnelle : on saccage les bandes, aucun score ne doit bouger.
    saccage = out.copy()
    for col in BB_COLS:
        saccage[col] = np.nan
    rescored = features.module_scores(saccage)
    pd.testing.assert_frame_equal(rescored[SCORE_COLS], out[SCORE_COLS])


def test_idempotence_compute_all():
    merged = build_merged(n4=280)
    once = features.compute_all(merged)
    twice = features.compute_all(once.copy())
    pd.testing.assert_frame_equal(once, twice)


def test_anti_lookahead_compute_all():
    merged = build_merged(n4=280, kind="gaps", seed=7)
    full = features.compute_all(merged)
    cuts = [*range(40, len(merged), 97), len(merged) - 1, len(merged)]
    for t in cuts:
        part = features.compute_all(merged.iloc[:t].copy())
        pd.testing.assert_frame_equal(
            part[COMPUTE_ALL_COLS], full[COMPUTE_ALL_COLS].iloc[:t]
        )


def test_anti_lookahead_etage_4h():
    """Une feature 4h ne change pas apres coup (05.6) : pipeline natif tronque
    a t == pipeline complet sur [0, t) — pivots confirmes, structure, S/R."""
    df4 = make_ohlcv("wicks", n=220, seed=11, timeframe="4h")
    cols = [
        "pivot_high_conf", "pivot_low_conf", "last_ph", "last_hl", "hh_hl_intact",
        "bos_bull", "bos_fresh", "choch_bear",
        "nearest_res", "nearest_sup", "res_touches",
        "atr", "adx", "rsi", "macd_hist", "vol_sma20",
        "cdl_engulfing", "cdl_doji", features.PINBAR_COL,
    ]
    full = apply_4h(df4)
    for t in (60, 120, 180, 219, 220):
        part = apply_4h(df4.iloc[:t].copy())
        pd.testing.assert_frame_equal(part[cols], full[cols].iloc[:t])


# =============== A2 — miroirs baissiers (le bot est long ET short, docs/01 v4) ===============
def _bear_ctx(**kw):
    """_score_df avec un contexte de tendance BAISSIER (e50 < e200 et close < e50)."""
    kw.setdefault("ema50_4h", 90.0)
    kw.setdefault("ema200_4h", 100.0)
    kw.setdefault("close", 80.0)
    return _score_df(**kw)


def test_track_structure_produit_les_miroirs_baissiers():
    """Les colonnes baissieres se construisent sur les MEMES pivots confirmes (anti-repaint)."""
    rows = [BASE] * 40
    rows[10] = (100.0, 104.0, 99.0, 100.2)    # pivot high haut
    rows[16] = (100.0, 101.0, 96.0, 100.2)    # pivot low bas
    rows[22] = (100.0, 102.0, 99.0, 100.2)    # pivot high PLUS BAS que le precedent => LH
    rows[28] = (100.0, 101.0, 94.0, 100.2)    # pivot low PLUS BAS => LL
    out = features.track_structure(features.find_pivots(features.add_indicators(_df_ohlc(rows))))
    for col in ("last_pl", "last_lh", "ll_lh_intact", "bos_bear", "bos_fresh_bear",
                "choch_bull"):
        assert col in out.columns
    # Le LH retenu est bien le pivot high abaisse (102), connu a sa confirmation (+2).
    assert out["last_lh"].iloc[24] == pytest.approx(102.0)
    # Sequence LL ET LH etablie apres les deux pivots abaisses.
    assert bool(out["ll_lh_intact"].iloc[30])
    # Symetrie stricte : aucune ligne ne peut etre simultanement en CHoCH des deux cotes
    # sans que le prix soit a la fois sous le HL et au-dessus du LH (impossible si LH > HL).
    both = out["choch_bear"] & out["choch_bull"]
    coherent = (out["last_lh"] <= out["last_hl"]) | ~both
    assert bool(coherent.fillna(True).all())


def test_s_structure_short_est_le_miroir():
    # 1,0 : BOS baissier frais ET contexte de tendance baissiere.
    out = features.module_scores(_bear_ctx(
        n=6,
        bos_bear_4h=[False, True, False, False, False, False],
        bos_fresh_bear_4h=[False, True, True, True, False, False],
    ))
    assert out["s_structure_short"].iloc[1] == 1.0
    # 0 : dernier evenement = CHoCH HAUSSIER (adverse pour un short).
    out = features.module_scores(_bear_ctx(
        n=6, choch_bull_4h=[False, False, True, False, False, False]))
    assert out["s_structure_short"].iloc[2] == 0.0
    assert out["s_structure_short"].iloc[4] == 0.0
    # 0,7 : sequence LL/LH intacte sans BOS frais.
    out = features.module_scores(_bear_ctx(ll_lh_intact_4h=True))
    assert (out["s_structure_short"] == 0.7).all()
    # 0,3 : structure neutre ; 0 : warm-up.
    assert (features.module_scores(_bear_ctx())["s_structure_short"] == 0.3).all()
    out = features.module_scores(_bear_ctx(adx_4h=np.nan, ll_lh_intact_4h=True))
    assert (out["s_structure_short"] == 0.0).all()
    # BOS baissier frais mais contexte HAUSSIER (defaut de _score_df) => 0,3, pas 1,0.
    out = features.module_scores(_score_df(bos_fresh_bear_4h=True))
    assert (out["s_structure_short"] == 0.3).all()


def test_s_momentum_short_bandes_miroir():
    """Memes chiffres que le long, RSI renverse autour de 50 et histogramme negatif."""
    out = features.module_scores(_score_df(
        n=6,
        rsi_4h=[40.0, 40.0, 53.0, 28.0, 24.0, 40.0],
        macd_hist_4h=[-0.5, -1.0, -1.0, -1.0, -1.0, -0.5],
    ))
    assert list(out["s_momentum_short"]) == [0.0, 1.0, 0.5, 0.5, 0.0, 0.0]
    # Bornes exactes : 50 et 30 inclus dans [30,50] ; 55 in (50,55] ; 25 in [25,30).
    out = features.module_scores(_score_df(
        n=4, rsi_4h=[50.0, 30.0, 55.0, 25.0],
        macd_hist_4h=[-1.0, -2.0, -3.0, -4.0]))
    assert list(out["s_momentum_short"]) == [0.0, 1.0, 0.5, 0.5]  # ligne 0 : pas de prec.
    # Un histogramme POSITIF ne peut jamais donner de momentum baissier.
    out = features.module_scores(_score_df(n=4, rsi_4h=40.0, macd_hist_4h=[1.0, 2.0, 3.0, 4.0]))
    assert (out["s_momentum_short"] == 0.0).all()


def test_s_patterns_short_lit_les_patterns_a_moins_100():
    f6 = [False] * 6
    # 1,0 : engulfing BAISSIER (-100) sur la bougie de cassure baissiere.
    out = features.module_scores(_score_df(
        n=6, bos_bear_4h=[*f6[:2], True, *f6[:3]],
        cdl_engulfing_4h=[0, 0, -100, 0, 0, 0]))
    assert out["s_patterns_short"].iloc[2] == 1.0
    # Un engulfing HAUSSIER (+100) au meme endroit ne compte pas pour le short.
    out = features.module_scores(_score_df(
        n=6, bos_bear_4h=[*f6[:2], True, *f6[:3]],
        cdl_engulfing_4h=[0, 0, 100, 0, 0, 0]))
    assert out["s_patterns_short"].iloc[2] == 0.3
    # Shooting star et pin bar bear comptent aussi.
    for col in ("cdl_shootingstar_4h", "cdl_pinbar_bear_4h"):
        out = features.module_scores(_score_df(
            n=6, bos_bear_4h=[*f6[:2], True, *f6[:3]], **{col: [0, 0, -100, 0, 0, 0]}))
        assert out["s_patterns_short"].iloc[2] == 1.0
    # Le doji disqualifie la cassure dans les DEUX sens (05.4).
    out = features.module_scores(_score_df(
        n=4, bos_bear_4h=[False, True, False, False],
        cdl_doji_4h=[0, 100, 0, 0], cdl_engulfing_4h=[0, -100, 0, 0]))
    assert out["s_patterns_short"].iloc[1] == 0.0


def test_s_volume_short_reutilise_le_score_long():
    """Le volume n'a pas de sens : dupliquer serait une symetrie de facade (05.5)."""
    out = features.module_scores(_score_df(n=5, volume_4h=[160.0, 150.0, 120.0, 100.0, 90.0]))
    assert list(out["s_volume_short"]) == list(out["s_volume"])


def test_pinbar_bear_est_le_miroir_du_pinbar_bull():
    # Pin bar bearish : longue meche HAUTE, cloture dans le tiers bas.
    rows = [BASE] * 5
    rows[2] = (100.0, 112.0, 99.5, 100.0)     # meche haute 12 >> corps 0
    out = features.candle_patterns(_df_ohlc(rows))
    assert out[features.PINBAR_BEAR_COL].iloc[2] == params.CDL_BEARISH
    # Pin bar bullish : longue meche BASSE, cloture dans le tiers haut.
    rows = [BASE] * 5
    rows[2] = (100.0, 100.5, 88.0, 100.0)
    out = features.candle_patterns(_df_ohlc(rows))
    assert out[features.PINBAR_COL].iloc[2] == params.CDL_BULLISH
    # Une bougie ne peut pas etre les deux a la fois.
    both = ((out[features.PINBAR_COL] != 0) & (out[features.PINBAR_BEAR_COL] != 0))
    assert not bool(both.any())


def test_colonnes_baissieres_ne_repeignent_pas():
    """Interdit n3 (zero look-ahead) etendu aux colonnes A2.

    Preuve mecanique au niveau feature : les valeurs calculees sur des donnees ARRETEES a t
    doivent etre IDENTIQUES a celles du run complet sur le meme prefixe. Une seule colonne
    baissiere qui regarderait le futur casserait ce test — et casserait tout le short.
    """
    rows = [BASE] * 60
    rows[10] = (100.0, 104.0, 99.0, 100.2)
    rows[16] = (100.0, 101.0, 96.0, 100.2)
    rows[22] = (100.0, 102.0, 99.0, 100.2)
    rows[28] = (100.0, 101.0, 94.0, 100.2)
    rows[34] = (100.0, 101.0, 99.0, 92.0)     # cloture sous le dernier PL => BOS baissier
    rows[40] = (100.0, 103.5, 99.0, 103.0)    # cloture au-dessus du dernier LH => CHoCH bull
    full = apply_4h(_df_ohlc(rows))
    mirrors = ["last_pl", "last_lh", "ll_lh_intact", "bos_bear", "bos_fresh_bear", "choch_bull"]
    for t in (30, 36, 42, 50):
        part = apply_4h(_df_ohlc(rows[:t]))
        for col in mirrors:
            pd.testing.assert_series_equal(part[col], full[col].iloc[:t], check_names=False)
    # Le scenario declenche bien les evenements testes (sinon le test passerait a vide).
    assert bool(full["bos_bear"].any())
    assert bool(full["choch_bull"].any())


def test_evenements_choch_1h_sont_des_fronts_montants_dans_les_deux_sens():
    """G6 lit un EVENEMENT, pas un etat (decision Jonas 10/07) — vrai aussi cote short."""
    out = features.compute_all(build_merged(n4=280, kind="gaps", seed=11))
    for state_col, event_col in (("choch_bear_1h", "choch_bear_event_1h"),
                                 ("choch_bull_1h", "choch_bull_event_1h")):
        state = out[state_col].astype(bool).to_numpy()
        event = out[event_col].astype(bool).to_numpy()
        rising = state & ~np.concatenate(([False], state[:-1]))
        assert (event == rising).all(), state_col
        assert event.sum() < state.sum()     # il y a bien de la persistance d'etat
