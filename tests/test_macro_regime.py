"""Tests Macro Analyst V1.1 — macro_regime (docs/06 §6.2, docs/04 §4.1-4.2).

Regles de score, bords des seuils, fail-safe stale, decalage +1 jour et
anti-look-ahead sur donnees SYNTHETIQUES ; un test d'integration sur les VRAIS
fichiers de user_data/data/macro/.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from arit_lib import contracts, macro_regime, params

KEYS = list(contracts.MACRO_SCORE_KEYS)
RCOL = contracts.MACRO_REGIME_COL
PORTEUR, NEUTRE, HOSTILE = params.MACRO_REGIMES


def _hist(n=90, start="2020-01-01", **overrides):
    """DataFrame daily UTC, colonnes MACRO_SCORE_KEYS neutres (score 0) sauf overrides."""
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    base = {
        "dxy": np.full(n, 100.0),
        "taux": np.full(n, 2.0),
        "stablecoins": np.full(n, 1e11),
        "funding": np.full(n, 0.0002),   # 0 < f <= HOT => 0
        "fear_greed": np.full(n, 35.0),  # 25 <= fg < 45 => 0
    }
    base.update(overrides)
    return pd.DataFrame(base, index=idx)


def _step(n, start_idx, value, base):
    arr = np.full(n, base, dtype="float64")
    arr[start_idx:] = value
    return arr


# ------------------------------------------------------------------ baseline neutre
def test_neutral_history_gives_all_zero_and_neutre():
    out = macro_regime.daily_regimes(_hist())
    assert list(out.columns) == KEYS + [RCOL]
    assert (out[KEYS].iloc[70] == 0).all()
    assert out[RCOL].iloc[70] == NEUTRE


# ------------------------------------------------------------------ regle par composant
@pytest.mark.parametrize("value, expected", [(99.0, 1), (101.0, -1)])
def test_score_dxy(value, expected):
    out = macro_regime.daily_regimes(_hist(dxy=_step(90, 40, value, 100.0)))
    assert out["dxy"].iloc[45] == expected


@pytest.mark.parametrize("value, expected", [(1.85, 1), (2.15, -1)])
def test_score_taux(value, expected):
    out = macro_regime.daily_regimes(_hist(taux=_step(90, 60, value, 2.0)))
    assert out["taux"].iloc[70] == expected


@pytest.mark.parametrize("mult, expected", [(1.03, 1), (0.98, -1)])
def test_score_stablecoins(mult, expected):
    out = macro_regime.daily_regimes(_hist(stablecoins=_step(90, 30, 1e11 * mult, 1e11)))
    assert out["stablecoins"].iloc[40] == expected


@pytest.mark.parametrize("value, expected", [(0.001, -1), (-0.0002, 1)])
def test_score_funding(value, expected):
    out = macro_regime.daily_regimes(_hist(funding=_step(90, 10, value, 0.0002)))
    assert out["funding"].iloc[20] == expected


@pytest.mark.parametrize("value, expected", [(20.0, -1), (50.0, 1)])
def test_score_fear_greed(value, expected):
    out = macro_regime.daily_regimes(_hist(fear_greed=_step(90, 20, value, 35.0)))
    assert out["fear_greed"].iloc[25] == expected


# ------------------------------------------------------------------ bords des seuils
@pytest.mark.parametrize("value, expected", [
    (99.4, 1),   # -0,6 % : juste sous -0,5 % => +1
    (99.6, 0),   # -0,4 % : au-dessus du seuil => 0
    (100.6, -1),  # +0,6 % => -1
    (100.4, 0),  # +0,4 % => 0
])
def test_dxy_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(dxy=_step(90, 40, value, 100.0)))
    assert out["dxy"].iloc[45] == expected


@pytest.mark.parametrize("value, expected", [
    (24.0, -1), (25.0, 0),   # < 25 strict
    (44.0, 0), (45.0, 1),    # >= 45
])
def test_fear_greed_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(fear_greed=_step(90, 20, value, 35.0)))
    assert out["fear_greed"].iloc[25] == expected


@pytest.mark.parametrize("value, expected", [
    (params.MACRO_FUNDING_HOT, 0),        # == HOT : pas > => 0
    (params.MACRO_FUNDING_HOT + 1e-4, -1),
    (0.0, 0),                             # == 0 : pas < 0 => 0
    (-1e-4, 1),
])
def test_funding_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(funding=np.full(90, value)))
    assert out["funding"].iloc[70] == expected


# ------------------------------------------------------------------ agregation regime
def test_regime_porteur_and_hostile():
    # fenetres dxy (20 j) et taux (60 j) calees pour co-activer au jour 75.
    # dxy -1 % (+1) ET taux -0,15 (+1) => somme +2 => PORTEUR
    h = _hist(dxy=_step(90, 65, 99.0, 100.0), taux=_step(90, 40, 1.85, 2.0))
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[76] == PORTEUR
    # dxy +1 % (-1) ET taux +0,15 (-1) => somme -2 => HOSTILE
    h2 = _hist(dxy=_step(90, 65, 101.0, 100.0), taux=_step(90, 40, 2.15, 2.0))
    out2 = macro_regime.daily_regimes(h2)
    assert out2[RCOL].iloc[76] == HOSTILE


# ------------------------------------------------------------------ fail-safe stale
def test_failsafe_three_stale_components_hostile():
    h = _hist(n=90)
    for col in ("dxy", "taux", "stablecoins"):
        arr = h[col].to_numpy().copy()
        arr[50:] = np.nan          # 3 series demarrees puis coupees > 48 h
        h[col] = arr
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[80] == HOSTILE


def test_before_any_series_started_is_neutre_not_hostile():
    h = _hist(n=40)
    for col in KEYS:
        arr = h[col].to_numpy().copy()
        arr[:6] = np.nan           # aucune serie n'a encore commence
        h[col] = arr
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[3] == NEUTRE  # 5 composants "sans donnee" mais debut d'historique


# ------------------------------------------------------------------ point-in-time +1 jour
def test_shift_plus_one_day():
    h = _hist(n=60, fear_greed=_step(60, 30, 20.0, 35.0))
    out = macro_regime.daily_regimes(h)
    assert out["fear_greed"].iloc[30] == 0    # J = jour de la bascule : reflete J-1 (35)
    assert out["fear_greed"].iloc[31] == -1   # J+1 : reflete la bascule du jour 30


# ------------------------------------------------------------------ anti-look-ahead
def test_modifying_last_value_never_changes_past_regimes():
    h = _hist(n=60, dxy=_step(60, 30, 98.0, 100.0))
    out1 = macro_regime.daily_regimes(h)

    h2 = h.copy()
    h2.iloc[-1, h2.columns.get_loc("dxy")] = 500.0
    out2 = macro_regime.daily_regimes(h2)
    pd.testing.assert_frame_equal(out1, out2)  # derniere valeur => aucun impact

    h3 = h.copy()
    h3.iloc[-2:, h3.columns.get_loc("fear_greed")] = 5.0
    out3 = macro_regime.daily_regimes(h3)
    pd.testing.assert_frame_equal(out1.iloc[:-2], out3.iloc[:-2])


# ------------------------------------------------------------------ regime_now (live)
def test_regime_now_empty_is_hostile():
    assert macro_regime.regime_now({}) == (HOSTILE, {})
    assert macro_regime.regime_now(None) == (HOSTILE, {})


def test_regime_now_aggregates_scores():
    porteur = {"dxy": 1, "taux": 1, "stablecoins": 1, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(porteur)[0] == PORTEUR
    hostile = {"dxy": -1, "taux": -1, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(hostile)[0] == HOSTILE
    neutre = {"dxy": 1, "taux": 0, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(neutre)[0] == NEUTRE


def test_regime_now_stale_or_missing_is_hostile():
    stale = {"dxy": 1, "taux": 1, "stablecoins": 1, "funding": 1, "fear_greed": 1,
             "stale": True}
    assert macro_regime.regime_now(stale)[0] == HOSTILE
    missing = {"dxy": 1, "taux": 1}  # 3 scores absents => fail-safe
    assert macro_regime.regime_now(missing)[0] == HOSTILE


# ------------------------------------------------------------------ integration reels
def _macro_dir():
    return Path(__file__).resolve().parents[1] / "user_data" / "data" / "macro"


@pytest.mark.skipif(not _macro_dir().exists(), reason="donnees macro absentes")
def test_integration_real_files():
    hist = macro_regime.load_history(_macro_dir())
    assert not hist.empty
    assert isinstance(hist.index, pd.DatetimeIndex)
    assert str(hist.index.tz) == "UTC"
    assert (hist.index == hist.index.normalize()).all()
    assert set(hist.columns) <= set(KEYS)

    regs = macro_regime.daily_regimes(hist)
    assert set(regs[RCOL].unique()) <= set(params.MACRO_REGIMES)
    assert set(np.unique(regs[KEYS].to_numpy())) <= {-1, 0, 1}
    # plage 2018+ couverte
    assert pd.Timestamp("2018-06-01", tz="UTC") in regs.index
    assert pd.Timestamp("2025-06-01", tz="UTC") in regs.index
