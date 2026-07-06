"""Fixtures pytest ARIT — generateur OHLCV synthetique SEEDE (Phase 1, prompt de build).

Quatre profils : tendance propre, range, gaps, meches. Deterministe (seed) pour
que chaque test soit reproductible. Utilisable par tous les tests de modules.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# arit_lib vit sous user_data/strategies/ (layout docs/02) — importable en test.
STRATEGIES_DIR = Path(__file__).resolve().parents[1] / "user_data" / "strategies"
if str(STRATEGIES_DIR) not in sys.path:
    sys.path.insert(0, str(STRATEGIES_DIR))

_TIMEFRAME_FREQ = {"5m": "5min", "1h": "1h", "4h": "4h", "1d": "1D"}


def make_ohlcv(
    kind: str = "trend",
    n: int = 400,
    seed: int = 42,
    timeframe: str = "1h",
    start: str = "2024-01-01",
    base_price: float = 100.0,
) -> pd.DataFrame:
    """DataFrame freqtrade-like : colonnes date (UTC), open, high, low, close, volume.

    kind:
      - "trend"  : derive haussiere reguliere + bruit faible (BOS/HH/HL propres)
      - "range"  : oscillation sinusoidale autour de base_price (ADX bas)
      - "gaps"   : marche aleatoire avec sauts d'open periodiques (+/-2 %)
      - "wicks"  : range avec meches hautes/basses amplifiees (pivots, pin bars)
    """
    if kind not in ("trend", "range", "gaps", "wicks"):
        raise ValueError(f"kind inconnu: {kind}")
    rng = np.random.default_rng(seed)
    idx = np.arange(n, dtype=float)

    if kind == "trend":
        drift = 0.0015 * idx                       # +0,15 %/bougie cumule
        noise = rng.normal(0.0, 0.004, n).cumsum()
        close = base_price * np.exp(drift + noise)
    elif kind == "range":
        wave = 0.03 * np.sin(2 * np.pi * idx / 50.0)
        noise = rng.normal(0.0, 0.002, n)
        close = base_price * (1.0 + wave + noise)
    else:  # gaps / wicks : marche aleatoire neutre
        noise = rng.normal(0.0, 0.005, n).cumsum()
        close = base_price * np.exp(noise)

    open_ = np.empty(n)
    open_[0] = close[0] * (1.0 + rng.normal(0.0, 0.001))
    open_[1:] = close[:-1]

    if kind == "gaps":
        gap_every = 40
        gap_pos = np.arange(gap_every, n, gap_every)
        open_[gap_pos] = open_[gap_pos] * (1.0 + rng.choice([-0.02, 0.02], gap_pos.size))

    body_top = np.maximum(open_, close)
    body_bot = np.minimum(open_, close)
    wick_scale = 0.012 if kind == "wicks" else 0.003
    high = body_top * (1.0 + np.abs(rng.normal(0.0, wick_scale, n)))
    low = body_bot * (1.0 - np.abs(rng.normal(0.0, wick_scale, n)))

    volume = rng.lognormal(mean=6.0, sigma=0.3, size=n)
    body_frac = np.divide(
        body_top - body_bot, close, out=np.zeros(n), where=close > 0
    )
    volume *= 1.0 + 20.0 * body_frac  # grosses bougies = gros volume (s_volume testable)

    date = pd.date_range(start=start, periods=n, freq=_TIMEFRAME_FREQ[timeframe], tz="UTC")
    return pd.DataFrame(
        {"date": date, "open": open_, "high": high, "low": low,
         "close": close, "volume": volume}
    )


@pytest.fixture
def ohlcv():
    """Fabrique : ohlcv(kind, n=..., seed=..., timeframe=...)."""
    return make_ohlcv


@pytest.fixture
def ohlcv_trend():
    return make_ohlcv("trend")


@pytest.fixture
def ohlcv_range():
    return make_ohlcv("range")


@pytest.fixture
def ohlcv_gaps():
    return make_ohlcv("gaps")


@pytest.fixture
def ohlcv_wicks():
    return make_ohlcv("wicks")
