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


# =========================================== 06.2.1 bloc correlation actions (c6/c7)
# Fusionne depuis research/correlation_block/ le 2026-08-03 (decision Jonas A4), en
# FAIL-SAFE (la proposition d'origine etait en fail-open).
#
# POURQUOI PAS UN 6e COMPOSANT DE SCORE (docs/06 §6.2.1) : le regime est une SOMME de 5
# composants dans {-1,0,+1} avec PORTEUR >= +2 / HOSTILE <= -2. Un 6e terme additif
# (1) deplacerait SILENCIEUSEMENT le sens des seuils (+-2 sur 5 -> +-2 sur 6), donc
# recalibrerait les 5 composants existants sans les avoir touches ; (2) serait SYMETRIQUE
# par construction alors que le BTC suit les actions a la BAISSE et pas a la hausse ;
# (3) reproduirait un motif deja mesure 3 fois ici — un signal utile en VETO detruit de la
# valeur en TERME ADDITIF. => veto booleen, journalise a part, ablatable seul.
#
# c6  risk-off actions : l'indice casse sa structure a la baisse -> veto longs.
# c7  regime de correlation (META) : rho(BTC, indice) decide si c6 est ARME.


def _read_btc_daily(path: Path) -> pd.Series:
    """Klines Binance 1d [[openTime ms, o, h, l, c, ...], ...] -> Series close daily UTC."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    idx = pd.to_datetime([int(r[0]) for r in raw], unit="ms", utc=True).normalize()
    s = pd.Series([float(r[4]) for r in raw], index=idx)
    return s[~s.index.duplicated(keep="last")].dropna().sort_index()


def load_equity_inputs(macro_dir) -> tuple[pd.Series, pd.Series]:
    """(indice actions sessions US, cloture 1d BTC) depuis macro_dir. Absent/illisible => vide.

    Volontairement SEPARE de load_history : ces series ne sont PAS des composants de la
    somme (docs/06 §6.2.1), elles ne doivent jamais entrer dans MACRO_SCORE_KEYS.
    """
    base = Path(macro_dir)
    empty = pd.Series(dtype="float64")

    def _try(loader) -> pd.Series:
        try:
            s = loader()
        except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            return empty
        return s if s is not None and not s.empty else empty

    equity = _try(lambda: _read_fred_csv(base / contracts.EQUITY_FILE))
    btc = _try(lambda: _read_btc_daily(base / contracts.BTC_DAILY_FILE))
    return equity, btc


def equity_structural_break(equity: pd.Series, window: int | None = None) -> pd.Series:
    """True quand l'indice cloture sous son plus-bas de cloture des `window` j ouvres.

    `shift(1)` exclut le jour courant de son propre plancher : la cassure est un EVENEMENT,
    pas une tautologie. Index = sessions US uniquement (le passage au 7/7 est le role de
    _align_to_calendar).

    ASYMETRIQUE PAR CONSTRUCTION : aucune sortie haussiere n'existe. Le symetrique (l'indice
    casse un plus-haut => +1) est explicitement ECARTE — la correlation coute dans un sens et
    ne rapporte pas dans l'autre (docs/06 §6.2.1).
    """
    window = params.MACRO_EQUITY_BREAK_WINDOW_D if window is None else window
    floor_ = equity.shift(1).rolling(window).min()
    return (equity < floor_).fillna(False)


def btc_equity_correlation(btc_daily_close: pd.Series, equity: pd.Series,
                           window: int) -> pd.Series:
    """rho de Pearson des rendements log BTC/actions, calcule SUR LES SESSIONS US.

    PIEGE EVITE : calculer rho sur un calendrier 7/7 avec un indice forward-fille injecte
    ~2 jours de rendement NUL par semaine cote actions ET desaligne les fenetres (le lundi,
    le BTC rend 1 jour quand l'indice rend le week-end entier). Effet mesure par simulation :
    rho calendaire ~= 0,66 x rho sessions (-33 %) — un vrai couplage a 0,75 s'afficherait a
    0,50, pile sur le seuil d'armement, donc un veto qui clignote ou ne s'arme jamais.
    (Chiffre de simulation ; a re-deriver sur l'historique reel BTC/NASDAQ100.)

    Le rendement BTC vendredi->lundi couvre le week-end : c'est la bonne fenetre, elle
    correspond a celle de l'indice sur le meme intervalle.
    """
    sessions = equity.index
    btc_on_sessions = btc_daily_close.reindex(sessions).ffill()
    r_btc = np.log(btc_on_sessions).diff()
    r_equity = np.log(equity).diff()
    return r_btc.rolling(window).corr(r_equity)


def correlation_state(rho_fast: pd.Series, rho_slow: pd.Series) -> pd.Series:
    """rho -> {COUPLE, TRANSITION, DECOUPLE} avec hysteresis (params.MACRO_CORR_STATES).

    Sans hysteresis, un rho qui oscille autour d'un seuil unique fait clignoter le veto d'un
    jour a l'autre. Bande morte : on ARME au-dessus de MACRO_CORR_ARM_ABOVE (confirme par le
    rho long), on ne DESARME qu'en repassant sous MACRO_CORR_DISARM_BELOW, et on garde l'etat
    precedent entre les deux. Avant tout etat etabli => TRANSITION, donc veto desarme : le
    warm-up ne bloque aucune entree.
    """
    coupled, transition, decoupled = params.MACRO_CORR_STATES
    arm = (rho_fast >= params.MACRO_CORR_ARM_ABOVE) & (rho_slow >= params.MACRO_CORR_DISARM_BELOW)
    disarm = rho_fast < params.MACRO_CORR_DISARM_BELOW

    state = pd.Series(np.nan, index=rho_fast.index, dtype="object")
    state[arm] = coupled
    state[disarm] = decoupled
    return state.ffill().fillna(transition)


def _align_to_calendar(sessions_series: pd.Series, full_index: pd.DatetimeIndex,
                       stale_hours: int | None = None) -> pd.DataFrame:
    """Sessions US -> calendrier 7/7. -> DataFrame(value, started, fresh).

    `value` est forward-fillee depuis la derniere session ; `started` dit qu'il existe au
    moins une observation <= D ; `fresh` dit que cette derniere observation a moins de
    `stale_hours`. Les TROIS colonnes sont necessaires : evaluate_equity_veto doit separer
    "pas de cassure" (fresh), "on ne sait plus" (started sans fresh => fail-safe) et
    "bloc jamais configure" (pas started => inoperant, cf. docs/06 §6.2.1).

    ⚠️ Fenetre DEDIEE et pas MACRO_STALE_HOURS (48 h) : l'indice est une serie 5/7 ; un ferie
    US colle a un week-end laisse jusqu'a 96 h sans observation, le composant tomberait stale
    ~10 fois par an pour une raison purement calendaire.
    """
    stale_hours = params.MACRO_EQUITY_STALE_HOURS if stale_hours is None else stale_hours
    obs_dates = pd.Series(sessions_series.index, index=sessions_series.index)
    union = full_index.union(sessions_series.index)

    value = sessions_series.reindex(union).ffill().reindex(full_index)
    last_obs = obs_dates.reindex(union).ffill().reindex(full_index)
    age_h = (pd.Series(full_index, index=full_index) - last_obs) / pd.Timedelta(hours=1)
    started = last_obs.notna()
    fresh = started & (age_h <= stale_hours)
    return pd.DataFrame({"value": value, "started": started, "fresh": fresh})


def evaluate_equity_veto(equity_break: bool, corr_state: str, macro_regime: str,
                         data_fresh: bool, data_started: bool = True) -> tuple[bool, str]:
    """Compose c6 + c7 -> (bloquer_nouveaux_longs, raison journalisable). docs/06 §6.2.1.

    Les arbitrages, et leur justification :

    1. SERIE JAMAIS DEMARREE => le bloc est INOPERANT, il ne veto pas. Un fail-safe sur
       "jamais configure" bloquerait 100 % des entrees de tout backtest : ce n'est pas de la
       securite, c'est une panne. Meme distinction started/fresh que les 5 composants.
    2. DONNEE DEMARREE PUIS PERIMEE => FAIL-SAFE, veto actif (decision Jonas 03/08, A4 —
       revise le fail-open propose le 30/07). Contrepartie assumee et documentee : un filtre
       qui bloque sur donnee absente devient plus difficile a isoler en ablation, d'ou la
       raison DISTINCTE EQUITY_VETO_STALE, comptee a part.
    3. ARMEMENT SUR COUPLE SEUL. TRANSITION est la bande morte de l'hysteresis, c'est-a-dire
       "on ne sait pas". Armer sur l'incertitude rendrait le meta-gate inutile (veto actif
       presque tout le temps) et couterait des entrees valides. Le veto doit etre precis.
    4. BINDING vs REDUNDANT. Quand la macro est deja HOSTILE, l'entree est bloquee en amont :
       le veto actions n'ajoute rien ce jour-la. Compter les deux cas separement donne
       directement l'apport MARGINAL du filtre (= nombre de BINDING), seule quantite
       decisionnelle. Sans cette distinction, l'ablation surestime le filtre de tous ses
       blocages non-liants.
    """
    if not data_started:
        return False, contracts.EQUITY_PASS_NOT_STARTED
    if not data_fresh:
        return True, contracts.EQUITY_VETO_STALE
    if corr_state != params.MACRO_CORR_STATES[0]:  # pas COUPLE
        return False, contracts.EQUITY_PASS_DECOUPLED
    if not equity_break:
        return False, contracts.EQUITY_PASS_NO_BREAK
    if macro_regime == params.MACRO_REGIMES[2]:  # HOSTILE
        return True, contracts.EQUITY_VETO_REDUNDANT
    return True, contracts.EQUITY_VETO_BINDING


def daily_equity_veto(equity: pd.Series, btc_daily: pd.Series,
                      regimes_daily: pd.DataFrame) -> pd.DataFrame:
    """-> DataFrame daily : EQUITY_VETO_COL (bool), EQUITY_VETO_REASON_COL (str), stale_days.

    Index = celui de `regimes_daily` (sortie de daily_regimes, deja decalee +1 j).
    POINT-IN-TIME : le veto est calcule same-day puis decale de +1 jour, exactement comme
    les 5 composants — aucune valeur du jour J n'est lisible avant J+1 00:00 UTC.
    `stale_days` = nombre de jours CONSECUTIFS de veto stale, pour que l'appelant journalise
    un `system` au premier jour de blocage (un flux mort ne doit pas arreter le bot en silence).
    """
    cols = [contracts.EQUITY_VETO_COL, contracts.EQUITY_VETO_REASON_COL, "stale_days"]
    if regimes_daily is None or len(regimes_daily) == 0:
        return pd.DataFrame(columns=cols)
    idx = regimes_daily.index

    if equity.empty or btc_daily.empty:  # bloc non configure => inoperant, jamais bloquant
        return pd.DataFrame({contracts.EQUITY_VETO_COL: False,
                             contracts.EQUITY_VETO_REASON_COL: contracts.EQUITY_PASS_NOT_STARTED,
                             "stale_days": 0}, index=idx)

    brk_sessions = equity_structural_break(equity)
    rho_fast = btc_equity_correlation(btc_daily, equity, params.MACRO_CORR_WINDOW_FAST_D)
    rho_slow = btc_equity_correlation(btc_daily, equity, params.MACRO_CORR_WINDOW_SLOW_D)
    state_sessions = correlation_state(rho_fast, rho_slow)

    brk = _align_to_calendar(brk_sessions.astype("float64"), idx)
    state = _align_to_calendar(state_sessions, idx)
    regime_col = regimes_daily[contracts.MACRO_REGIME_COL]

    decided = [
        evaluate_equity_veto(
            bool(brk["value"].iat[i] == 1.0),
            state["value"].iat[i],
            regime_col.iat[i],
            bool(brk["fresh"].iat[i]),
            bool(brk["started"].iat[i]),
        )
        for i in range(len(idx))
    ]
    same_day = pd.DataFrame(
        {contracts.EQUITY_VETO_COL: [d[0] for d in decided],
         contracts.EQUITY_VETO_REASON_COL: [d[1] for d in decided]}, index=idx)

    # Point-in-time (+1 j) : identique a daily_regimes. Le 1er jour n'a pas d'anteriorite.
    out = same_day.shift(1)
    out[contracts.EQUITY_VETO_COL] = out[contracts.EQUITY_VETO_COL].fillna(False).astype(bool)
    out[contracts.EQUITY_VETO_REASON_COL] = out[contracts.EQUITY_VETO_REASON_COL].fillna(
        contracts.EQUITY_PASS_NOT_STARTED)

    is_stale = out[contracts.EQUITY_VETO_REASON_COL] == contracts.EQUITY_VETO_STALE
    # Compteur de jours CONSECUTIFS : cumcount par serie ininterrompue de jours stale.
    groups = (~is_stale).cumsum()
    out["stale_days"] = is_stale.groupby(groups).cumsum().astype("int64")
    return out


def stale_episodes(veto: pd.DataFrame) -> dict | None:
    """Resume des episodes de veto stale, ou None s'il n'y en a aucun. -> detail journalisable.

    Le fail-safe A4 transforme un flux actions mort en arret de TOUTES les entrees. Sans ce
    resume il le ferait en silence : c'est la contrepartie explicite du choix fail-safe
    (docs/06 §6.2.1). Pur — la strategie ne fait que le passer au journal.
    """
    if veto is None or len(veto) == 0 or "stale_days" not in veto.columns:
        return None
    stale = veto[veto[contracts.EQUITY_VETO_REASON_COL] == contracts.EQUITY_VETO_STALE]
    if stale.empty:
        return None
    starts = stale[stale["stale_days"] == 1]
    return {"episodes": int(len(starts)), "jours_max": int(stale["stale_days"].max()),
            "jours_total": int(len(stale)),
            "premier": str(starts.index[0]) if len(starts) else None}


def daily_with_equity_veto(macro_dir) -> tuple[pd.DataFrame, list[tuple[str, dict]]]:
    """Regimes macro quotidiens + bloc correlation actions c6/c7 joint (backtest, M08).

    Assemble ce que la strategie faisait a la main : charger l'historique, calculer les
    regimes, joindre les colonnes de veto actions, detecter les episodes stale. Ce bloc
    est du METIER et n'a donc rien a faire dans AritV1 (CLAUDE.md : « zero metier » dans
    la strategie).

    NE JOURNALISE PAS — meme contrat que risk.gate_check : retourne
    `(daily, evenements)` ou `evenements` est une liste de (kind, detail) que M07 passe a
    journal.ev_system. C'est ce qui garde ce module pur et sans import croisé (docs/11).
    Historique absent => (DataFrame vide, [macro_unavailable]) : le caller retombe alors
    sur le neutre backtest documente (M02), il ne plante pas.
    """
    daily = daily_regimes(load_history(macro_dir))
    if daily.empty:
        return daily, [("macro_unavailable", {"dir": str(macro_dir)})]
    veto = daily_equity_veto(*load_equity_inputs(macro_dir), daily)
    daily = daily.join(veto[[contracts.EQUITY_VETO_COL, contracts.EQUITY_VETO_REASON_COL]])
    stale = stale_episodes(veto)          # fail-safe A4 jamais silencieux
    return daily, ([("equity_veto_stale", stale)] if stale else [])


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
