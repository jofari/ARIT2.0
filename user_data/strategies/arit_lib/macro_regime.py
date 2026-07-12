"""Macro Analyst V1.1 — regime macro quotidien (docs/06 §6.2, docs/04 §4.1-4.2).

Module PUR : pandas/numpy + contracts/params UNIQUEMENT. Aucun reseau, aucun LLM.
Seule I/O autorisee = lecture des fichiers du repertoire passe en argument.

5 composants quotidiens scores dans {+1, 0, -1} (docs/06 §6.2) ; regime = somme :
PORTEUR >= +2 · HOSTILE <= -2 · NEUTRE sinon. Composant stale (>48 h) => 0 ;
>= 3 composants stale => HOSTILE (fail-safe). Point-in-time STRICT : la valeur du
jour J n'est utilisable qu'a partir de J+1 00:00 UTC (decalage +1 jour, zero look-ahead).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from arit_lib import contracts, params

# Fichiers attendus dans MACRO_DATA_DIR (scripts/download_macro.py, docs/06 §6.2).
_DXY_FILE = "dxy.csv"
_TAUX_FILE = "taux_fed.csv"
_STABLES_FILE = "stablecoins.json"
_FUNDING_FILES = ("funding_BTCUSDT.json", "funding_ETHUSDT.json")
_FEARGREED_FILE = "fear_greed.json"

# 06.2 : fenetre de fraicheur exprimee en jours (48 h => 2 jours calendaires).
_STALE_DAYS = params.MACRO_STALE_HOURS / 24.0


# --------------------------------------------------------------- parsers (I/O locale)
def _read_fred_csv(path: Path) -> pd.Series:
    """CSV FRED (observation_date, VALEUR) ; '.' = manquant. -> Series daily UTC minuit."""
    df = pd.read_csv(path, na_values=["."])
    date_col, val_col = df.columns[0], df.columns[1]
    idx = pd.to_datetime(df[date_col], utc=True).dt.normalize()
    s = pd.Series(pd.to_numeric(df[val_col], errors="coerce").values, index=idx)
    return s.dropna().sort_index()


def _read_stablecoins(path: Path) -> pd.Series:
    """DefiLlama [{date epoch s, totalCirculatingUSD:{peggedUSD}}] -> mcap daily."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    dates, values = [], []
    for row in raw:
        block = row.get("totalCirculatingUSD") or {}
        val = block.get("peggedUSD")
        if val is None:
            continue
        dates.append(int(row["date"]))
        values.append(float(val))
    idx = pd.to_datetime(dates, unit="s", utc=True).normalize()
    return pd.Series(values, index=idx).dropna().sort_index()


def _read_funding_file(path: Path) -> pd.Series:
    """[{fundingTime ms, fundingRate str}] -> moyenne journaliere du symbole."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    idx = pd.to_datetime([r["fundingTime"] for r in raw], unit="ms", utc=True)
    s = pd.Series([float(r["fundingRate"]) for r in raw], index=idx)
    return s.resample("1D").mean().dropna()


def _read_fear_greed(path: Path) -> pd.Series:
    """alternative.me {data:[{value str, timestamp epoch s}]} -> F&G daily."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rows = raw.get("data", [])
    idx = pd.to_datetime([int(r["timestamp"]) for r in rows], unit="s", utc=True).normalize()
    s = pd.Series([float(r["value"]) for r in rows], index=idx)
    return s[~s.index.duplicated(keep="last")].dropna().sort_index()


def load_history(macro_dir) -> pd.DataFrame:
    """Lit macro_dir -> DataFrame DAILY (index DatetimeIndex UTC normalise minuit).

    Colonnes float = contracts.MACRO_SCORE_KEYS (valeurs BRUTES ; funding = moyenne
    BTC+ETH par jour, en fraction/8h). Une serie absente ou illisible => colonne
    absente (aucune exception remontee).
    """
    base = Path(macro_dir)
    series: dict[str, pd.Series] = {}

    def _try(key: str, loader) -> None:
        try:
            s = loader()
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return
        if s is not None and not s.empty:
            series[key] = s

    _try("dxy", lambda: _read_fred_csv(base / _DXY_FILE))
    _try("taux", lambda: _read_fred_csv(base / _TAUX_FILE))
    _try("stablecoins", lambda: _read_stablecoins(base / _STABLES_FILE))
    _try("fear_greed", lambda: _read_fear_greed(base / _FEARGREED_FILE))

    def _load_funding() -> pd.Series | None:
        parts = []
        for name in _FUNDING_FILES:
            p = base / name
            if p.exists():
                parts.append(_read_funding_file(p))
        if not parts:
            return None
        return pd.concat(parts, axis=1).mean(axis=1, skipna=True).dropna()

    _try("funding", _load_funding)

    if not series:
        return pd.DataFrame()

    frame = pd.concat(series, axis=1, sort=False).sort_index()
    frame.index = frame.index.normalize()
    cols = [k for k in contracts.MACRO_SCORE_KEYS if k in frame.columns]
    return frame[cols]


# --------------------------------------------------------------- scoring (par composant)
def _score_relative(series: pd.Series, window: int, up: float, down: float,
                    up_score: int, down_score: int) -> pd.Series:
    """Variation relative sur `window` observations : >= up => up_score ; <= down => down_score."""
    var = series / series.shift(window) - 1.0
    out = pd.Series(0, index=series.index, dtype="float64")
    out[var >= up] = up_score
    out[var <= down] = down_score
    out[var.isna()] = np.nan
    return out


def _score_dxy(series: pd.Series) -> pd.Series:
    # 06.2 c1 : dollar en baisse = porteur. Var 20 j ouvres <= -0,5 % => +1 ; >= +0,5 % => -1.
    return _score_relative(series, params.MACRO_DXY_WINDOW_D,
                           up=params.MACRO_DXY_THRESH, down=-params.MACRO_DXY_THRESH,
                           up_score=-1, down_score=1)


def _score_taux(series: pd.Series) -> pd.Series:
    # 06.2 c2 : variation ABSOLUE (points) sur 60 j. <= -0,10 => +1 ; >= +0,10 => -1.
    diff = series - series.shift(params.MACRO_RATES_WINDOW_D)
    out = pd.Series(0, index=series.index, dtype="float64")
    out[diff <= -params.MACRO_RATES_THRESH] = 1
    out[diff >= params.MACRO_RATES_THRESH] = -1
    out[diff.isna()] = np.nan
    return out


def _score_stablecoins(series: pd.Series) -> pd.Series:
    # 06.2 c3 : var 30 j >= +2 % => +1 ; <= -1 % => -1.
    return _score_relative(series, params.MACRO_STABLES_WINDOW_D,
                           up=params.MACRO_STABLES_UP, down=params.MACRO_STABLES_DOWN,
                           up_score=1, down_score=-1)


def _score_funding(series: pd.Series) -> pd.Series:
    # 06.2 c4 : moyenne 7 j > +0,05 %/8h => -1 (sur-levier) ; < 0 => +1 (carburant).
    mean = series.rolling(params.MACRO_FUNDING_WINDOW_D).mean()
    out = pd.Series(0, index=series.index, dtype="float64")
    out[mean > params.MACRO_FUNDING_HOT] = -1
    out[mean < 0] = 1
    out[mean.isna()] = np.nan
    return out


def _score_fear_greed(series: pd.Series) -> pd.Series:
    # 06.2 c5 : < 25 => -1 ; >= 45 => +1.
    out = pd.Series(0, index=series.index, dtype="float64")
    out[series < params.FG_RISK_OFF_BELOW] = -1
    out[series >= params.FG_MULT_FULL_FROM] = 1
    return out


_SCORERS = {
    "dxy": _score_dxy,
    "taux": _score_taux,
    "stablecoins": _score_stablecoins,
    "funding": _score_funding,
    "fear_greed": _score_fear_greed,
}


def _component_frame(raw: pd.Series, scorer, full_index: pd.DatetimeIndex):
    """-> (score, started, stale) alignes sur full_index, calcules SAME-DAY (donnees <= D).

    score : {-1,0,1} float (0 si stale ou sans score exploitable) ; started : la serie
    a >= 1 observation <= D ; stale : demarree mais derniere obs > MACRO_STALE_HOURS.
    """
    obs = raw.dropna()
    if obs.empty:
        zeros = pd.Series(0.0, index=full_index)
        falses = pd.Series(False, index=full_index)
        return zeros, falses, falses

    score_native = scorer(obs)
    score_ff = score_native.reindex(full_index).ffill(limit=int(_STALE_DAYS))

    idx_series = pd.Series(full_index, index=full_index)
    obs_marker = idx_series.where(obs.reindex(full_index).notna())
    last_obs = obs_marker.ffill()
    started = last_obs.notna()
    age_h = (idx_series - last_obs) / pd.Timedelta(hours=1)
    fresh = started & (age_h <= params.MACRO_STALE_HOURS)
    stale = started & ~fresh

    score = score_ff.where(fresh, other=0.0).fillna(0.0)
    return score, started, stale


def daily_regimes(history: pd.DataFrame) -> pd.DataFrame:
    """DataFrame daily : 5 scores int {-1,0,1} + contracts.MACRO_REGIME_COL (str).

    POINT-IN-TIME : decale de +1 jour (la ligne du jour J reflete les donnees <= J-1).
    Composant sans donnee => 0 ; >= MACRO_STALE_FAILSAFE composants stale => HOSTILE,
    SAUF avant la 1re date de toutes les series (aucune serie commencee) => NEUTRE.
    """
    keys = list(contracts.MACRO_SCORE_KEYS)
    if history is None or history.empty:
        cols = keys + [contracts.MACRO_REGIME_COL]
        return pd.DataFrame(columns=cols)

    full_index = pd.date_range(history.index.min(), history.index.max(),
                               freq="D", tz="UTC")

    scores, started_flags, stale_flags = {}, {}, {}
    for key in keys:
        raw = history[key] if key in history.columns else pd.Series(dtype="float64")
        raw = raw.reindex(full_index) if not raw.empty else pd.Series(np.nan, index=full_index)
        sc, st, sl = _component_frame(raw, _SCORERS[key], full_index)
        scores[key], started_flags[key], stale_flags[key] = sc, st, sl

    score_df = pd.DataFrame(scores)
    any_started = pd.DataFrame(started_flags).any(axis=1)
    n_stale = pd.DataFrame(stale_flags).sum(axis=1)
    total = score_df.sum(axis=1)

    regime = pd.Series(params.MACRO_REGIMES[1], index=full_index)  # NEUTRE
    regime[total >= params.MACRO_PORTEUR_MIN] = params.MACRO_REGIMES[0]  # PORTEUR
    regime[total <= params.MACRO_HOSTILE_MAX] = params.MACRO_REGIMES[2]  # HOSTILE
    regime[n_stale >= params.MACRO_STALE_FAILSAFE] = params.MACRO_REGIMES[2]  # fail-safe
    regime[~any_started] = params.MACRO_REGIMES[1]  # debut d'historique => NEUTRE

    same_day = score_df.astype("int64")
    same_day[contracts.MACRO_REGIME_COL] = regime

    shifted = same_day.shift(1)  # point-in-time : ligne J = same-day de J-1
    shifted[keys] = shifted[keys].fillna(0).astype("int64")
    shifted[contracts.MACRO_REGIME_COL] = shifted[contracts.MACRO_REGIME_COL].fillna(
        params.MACRO_REGIMES[1])
    return shifted


def regime_now(macro_state: dict) -> tuple[str, dict]:
    """Live : macro_state.json etendu (scores deja calcules) -> (regime, scores).

    dict vide/None => ("HOSTILE", {}) fail-safe. Un flag `stale` vrai ou >= 3 scores
    absents => HOSTILE (docs/06 §6.2-6.3, la securite prime).
    """
    if not macro_state:
        return params.MACRO_REGIMES[2], {}

    scores = {k: int(macro_state[k]) for k in contracts.MACRO_SCORE_KEYS
              if macro_state.get(k) is not None}
    n_missing = len(contracts.MACRO_SCORE_KEYS) - len(scores)

    if macro_state.get("stale") or n_missing >= params.MACRO_STALE_FAILSAFE:
        return params.MACRO_REGIMES[2], scores

    total = sum(scores.values())
    if total >= params.MACRO_PORTEUR_MIN:
        regime = params.MACRO_REGIMES[0]
    elif total <= params.MACRO_HOSTILE_MAX:
        regime = params.MACRO_REGIMES[2]
    else:
        regime = params.MACRO_REGIMES[1]
    return regime, scores
