"""E0 — Outil replay : rejoue chaque entree d'un run de backtest sur l'OHLCV brut.

Objectif (decision Jonas 2026-07-17) : trajectoires en R de chaque entree, SANS aucune
regle de sortie — seulement le SL initial STRUCTUREL (docs/03 par.3.3) et un horizon.
Sert : (1) l'autopsie des runs existants (le zip du controle A a tourne sans stop —
voir BUILD_NOTES 2026-07-17), (2) plus tard la calibration des G-rules V2 depuis les
excursions mesurees. Analyse HORS-LIGNE en R-space par trade : ne simule NI le sizing,
NI les slots, NI le compounding — un re-run freqtrade reste necessaire pour le portefeuille.

Sources de verite :
- trades : zip de resultats freqtrade (backtest_lanes/runN/backtest_results/*.zip)
- SL initial structurel : evenements `entry` du journal (logs/decisions/<jour simule>.jsonl,
  champ sl_initial) — le zip n'a que le stoploss freqtrade (-0.99, jamais le structurel)
- prix : user_data/data/binance/<PAIR>-<tf>.feather (defaut 5m, granularite du
  --timeframe-detail contractuel, PDR 07.2)

Conventions : tout en UTC, timestamps en ms epoch (unite des zips freqtrade ; les dates
feather [ms]/[ns] sont normalisees — piege BUILD_NOTES 2026-07-13). Touche intra-bougie
ambigue (high >= TP et low <= SL sur la MEME bougie) => compte SL d'abord (pessimiste).

Usage :
  python analysis/replay_entries.py --zip backtest_lanes/run2/backtest_results/<...>.zip
      [--horizon-days 90] [--tf 5m] [--out analysis/out]
"""

import argparse
import io
import json
import pathlib
import sys
import zipfile

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "user_data" / "data" / "binance"
JOURNAL_DIR = REPO / "user_data" / "logs" / "decisions"

TP1_R = 1.5              # PDR 03.3 — TP1 fixe +1,5R (unite de validation du replay)
R_LEVELS = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)   # niveaux de premiere touche traques
HORIZON_DAYS_DEFAULT = 90
CHURN_GAP_MIN = 60       # meme paire, entrees espacees < 60 min => meme episode (re-entree churn)
SUBPERIODS = (("2018-2020", "2018-01-01", "2021-01-01"),   # docs/09 par.9.1.3
              ("2021-2022", "2021-01-01", "2023-01-01"),
              ("2023-2026", "2023-01-01", "2027-01-01"))
MS_H = 3_600_000         # 1 h en ms


def load_trades(zip_path: pathlib.Path) -> pd.DataFrame:
    """Trades du json principal du zip freqtrade -> DataFrame trie par open_timestamp."""
    with zipfile.ZipFile(zip_path) as z:
        main = [n for n in z.namelist() if n.endswith(".json")
                and not n.endswith("_config.json") and "market_change" not in n]
        if not main:
            raise SystemExit(f"pas de json de resultats dans {zip_path}")
        data = json.loads(io.TextIOWrapper(z.open(main[0]), encoding="utf-8").read())
    strategies = list(data["strategy"])
    trades = data["strategy"][strategies[0]]["trades"]
    df = pd.DataFrame(trades)[[
        "pair", "open_timestamp", "close_timestamp", "open_rate", "close_rate",
        "profit_ratio", "exit_reason", "trade_duration"]]
    return df.sort_values("open_timestamp").reset_index(drop=True)


def load_journal_sl(days: set[str]) -> dict[tuple[str, int], dict]:
    """Evenements `entry` du journal pour les jours simules donnes.

    Cle (pair, ts_ms a la minute). Les lanes ecrivent toutes dans le user_data racine
    (BUILD_NOTES 2026-07-13) : un meme trade apparait dans plusieurs runs — on verifie
    que sl_initial est coherent entre doublons (deterministe des donnees marche).
    """
    out: dict[tuple[str, int], dict] = {}
    conflicts = 0
    for day in sorted(days):
        path = JOURNAL_DIR / f"{day}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("event_type") != "entry" or not rec.get("ts_utc"):
                continue
            ts_ms = int(pd.Timestamp(rec["ts_utc"]).value // 1_000_000)
            key = (rec["pair"], ts_ms)
            sl = rec.get("sl_initial")
            if sl is None:
                continue
            if key in out and abs(out[key]["sl_initial"] - sl) > 1e-9 * max(abs(sl), 1.0):
                conflicts += 1
            out[key] = {"sl_initial": float(sl), "tp1": rec.get("tp1"),
                        "signal_id": rec.get("signal_id")}
    if conflicts:
        print(f"[WARN] {conflicts} conflits sl_initial entre doublons de runs (journal)")
    return out


def load_candles(pair: str, tf: str) -> pd.DataFrame:
    """Feather freqtrade -> colonnes ts (ms int64), open/high/low/close."""
    path = DATA_DIR / f"{pair.replace('/', '_')}-{tf}.feather"
    df = pd.read_feather(path, columns=["date", "open", "high", "low", "close"])
    # Normalisation d'unite datetime (piege ms/ns, BUILD_NOTES 2026-07-13) -> ms epoch.
    df["ts"] = df["date"].dt.tz_convert("UTC").dt.as_unit("ms").astype("int64")
    return df


def replay_one(candles: pd.DataFrame, open_ms: int, entry: float, sl: float,
               horizon_days: int) -> dict:
    """Trajectoire en R d'une entree, SL initial seul, jusqu'a l'horizon ou fin de donnees.

    R = (prix - entry) / (entry - sl). Touche SL : low <= sl. Touche niveau L : high >= prix(L).
    Bougie ambigue (TP et SL touches sur la meme) => SL d'abord (pessimiste, compte a part).
    """
    risk = entry - sl
    if risk <= 0:
        return {"error": "risk<=0"}
    ts = candles["ts"].to_numpy()
    lo = np.searchsorted(ts, open_ms)                      # 1re bougie >= entree
    hi = np.searchsorted(ts, open_ms + horizon_days * 86_400_000)
    if lo >= len(ts):
        return {"error": "hors donnees"}
    window = candles.iloc[lo:hi]
    r_high = (window["high"].to_numpy() - entry) / risk
    r_low = (window["low"].to_numpy() - entry) / risk
    wts = window["ts"].to_numpy()
    truncated = hi >= len(ts)

    sl_touch = r_low <= -1.0
    sl_idx = int(np.argmax(sl_touch)) if sl_touch.any() else None
    touches = {}
    for level in R_LEVELS:
        mask = r_high >= level
        touches[level] = int(np.argmax(mask)) if mask.any() else None

    tp_idx = touches[TP1_R]
    if tp_idx is not None and (sl_idx is None or tp_idx < sl_idx):
        outcome, end_idx, final_r = "TP", tp_idx, TP1_R
    elif sl_idx is not None:
        outcome, end_idx, final_r = "SL", sl_idx, -1.0
        ambiguous = tp_idx is not None and tp_idx == sl_idx
        if ambiguous:
            outcome = "SL_ambigu"
    else:
        outcome, end_idx = "open", len(window) - 1
        final_r = float((window["close"].to_numpy()[-1] - entry) / risk) if len(window) else 0.0

    pre = slice(0, (tp_idx + 1) if tp_idx is not None else len(window))
    sl_cap = (sl_idx + 1) if sl_idx is not None else len(window)   # fin de vie du trade
    out = {
        "outcome": outcome, "final_r": final_r, "truncated": bool(truncated),
        "end_ts": int(wts[end_idx]) if len(window) else open_ms,
        "hours_to_end": (int(wts[end_idx]) - open_ms) / MS_H if len(window) else 0.0,
        # mfe_r/mae_r : fenetre COMPLETE 90 j (offre brute du marche, ignore le SL) ;
        # mfe_before_sl_r : le max capturable AVANT la touche du SL initial.
        "mfe_r": float(r_high.max()) if len(window) else 0.0,
        "mae_r": float(r_low.min()) if len(window) else 0.0,
        "mfe_before_sl_r": float(r_high[:sl_cap].max()) if len(window) else 0.0,
        "mae_before_tp1_r": float(r_low[pre].min()) if len(window) else 0.0,
    }
    for days_m in (7, 30, 90):                              # marques "hold aveugle" (brut)
        j = int(np.searchsorted(wts, open_ms + days_m * 86_400_000)) - 1
        out[f"r_close_{days_m}d"] = (float((window["close"].to_numpy()[j] - entry) / risk)
                                     if j >= 0 else None)
    for level in R_LEVELS:
        idx = touches[level]
        before_sl = idx is not None and (sl_idx is None or idx <= sl_idx)
        out[f"h_to_{level}R"] = (wts[idx] - open_ms) / MS_H if before_sl else None
    # Continuation apres +1,5R : CAPTURABLE uniquement (outcome TP, cap a la touche SL).
    out.update(max_r_after_tp1=None, h_tp1_to_peak=None, giveback_after_peak_r=None)
    if outcome == "TP":
        seg = r_high[tp_idx:sl_cap]
        peak_rel = int(np.argmax(seg))
        out["max_r_after_tp1"] = float(seg[peak_rel])
        out["h_tp1_to_peak"] = (wts[tp_idx + peak_rel] - wts[tp_idx]) / MS_H
        tail = r_low[tp_idx + peak_rel:sl_cap]
        if len(tail):
            out["giveback_after_peak_r"] = float(seg[peak_rel] - tail.min())
    return out


def resample_trajectory(candles: pd.DataFrame, open_ms: int, entry: float, sl: float,
                        horizon_days: int, trade_id: str) -> pd.DataFrame:
    """Trajectoire re-echantillonnee 1h (r_high/r_low/r_close) pour l'atlas parquet."""
    risk = entry - sl
    ts = candles["ts"].to_numpy()
    lo = np.searchsorted(ts, open_ms)
    hi = np.searchsorted(ts, open_ms + horizon_days * 86_400_000)
    window = candles.iloc[lo:hi].copy()
    if window.empty:
        return pd.DataFrame()
    window["hour"] = (window["ts"] // MS_H) * MS_H
    agg = window.groupby("hour").agg(high=("high", "max"), low=("low", "min"),
                                     close=("close", "last"))
    return pd.DataFrame({
        "trade_id": trade_id, "ts": agg.index,
        "r_high": (agg["high"] - entry) / risk,
        "r_low": (agg["low"] - entry) / risk,
        "r_close": (agg["close"] - entry) / risk,
    })


def quantiles(series: pd.Series) -> str:
    s = series.dropna()
    if s.empty:
        return "n=0"
    q = s.quantile([0.25, 0.5, 0.75, 0.9])
    return (f"n={len(s)} p25={q[0.25]:.2f} med={q[0.5]:.2f} "
            f"p75={q[0.75]:.2f} p90={q[0.9]:.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zip", required=True, type=pathlib.Path)
    ap.add_argument("--horizon-days", type=int, default=HORIZON_DAYS_DEFAULT)
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--out", type=pathlib.Path, default=REPO / "analysis" / "out")
    args = ap.parse_args()

    trades = load_trades(args.zip)
    print(f"{len(trades)} trades charges depuis {args.zip.name}")
    days = {pd.Timestamp(ts, unit="ms", tz="UTC").strftime("%Y-%m-%d")
            for ts in trades["open_timestamp"]}
    sl_map = load_journal_sl(days)

    candle_cache: dict[str, pd.DataFrame] = {}
    rows, trajs = [], []
    for t in trades.itertuples():
        key = (t.pair, int(t.open_timestamp) // 60_000 * 60_000)
        journal = sl_map.get(key)
        row = {"pair": t.pair, "open_ts": int(t.open_timestamp),
               "open_date": pd.Timestamp(t.open_timestamp, unit="ms", tz="UTC"),
               "entry": t.open_rate, "zip_exit_reason": t.exit_reason,
               "zip_profit_pct": t.profit_ratio * 100,
               "zip_close_ts": int(t.close_timestamp),
               "sl_source": "journal" if journal else "MANQUANT"}
        if journal:
            sl = journal["sl_initial"]
            row.update(sl_initial=sl, signal_id=journal["signal_id"],
                       tp1_journal=journal["tp1"],
                       tp1_recalc=t.open_rate + TP1_R * (t.open_rate - sl))
            if t.pair not in candle_cache:
                candle_cache[t.pair] = load_candles(t.pair, args.tf)
            result = replay_one(candle_cache[t.pair], int(t.open_timestamp),
                                t.open_rate, sl, args.horizon_days)
            row.update(result)
            if "error" not in result:
                trajs.append(resample_trajectory(
                    candle_cache[t.pair], int(t.open_timestamp), t.open_rate, sl,
                    args.horizon_days, f"{t.pair}-{int(t.open_timestamp)}"))
        rows.append(row)
    df = pd.DataFrame(rows)

    # Episodes : entrees churn regroupees (meme paire, gap < CHURN_GAP_MIN — cf. docstring).
    df["gap_min"] = df.groupby("pair")["open_ts"].diff().div(60_000)
    df["new_episode"] = (df["gap_min"].isna()) | (df["gap_min"] >= CHURN_GAP_MIN)
    df["episode_id"] = df.groupby("pair")["new_episode"].cumsum().astype(str) + "-" + df["pair"]
    episodes = df[df["new_episode"]].copy()               # 1re entree de chaque episode

    args.out.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["new_episode"]).to_csv(args.out / "summary.csv", index=False)
    if trajs:
        pd.concat(trajs, ignore_index=True).to_parquet(args.out / "trajectories_1h.parquet")
    print(f"-> {args.out / 'summary.csv'} · {args.out / 'trajectories_1h.parquet'}")

    # ---------------- rapport console (brut, aucune interpretation) ----------------
    replayed = df[df["sl_source"] == "journal"]
    print(f"\nSL initial retrouve au journal : {len(replayed)}/{len(df)} trades")
    if "tp1_journal" in replayed and len(replayed):
        delta = (replayed["tp1_recalc"] - replayed["tp1_journal"].astype(float)).abs()
        rel = (delta / replayed["entry"]).max()
        print(f"coherence tp1 journal vs entry+1.5R : ecart max {rel * 100:.4f} % du prix")

    # Validation : gagnants zip (TP_CONTROL_A, duree > 0) vs 1re touche +1,5R du replay.
    winners = df[(df["zip_exit_reason"] == "TP_CONTROL_A") & (df["zip_profit_pct"] > 0)
                 & (df["sl_source"] == "journal")].copy()
    if len(winners):
        touch_ts = winners["open_ts"] + winners["h_to_1.5R"].astype(float) * MS_H
        delta_h = (winners["zip_close_ts"] - touch_ts) / MS_H
        ok = delta_h.dropna().between(-1, 3).mean() * 100
        print(f"validation gagnants zip : {len(winners)} trades, close_zip - touche_replay "
              f"dans [-1h, +3h] pour {ok:.0f} % · {quantiles(delta_h)} (h)")

    print(f"\nepisodes uniques (churn regroupe, gap < {CHURN_GAP_MIN} min) : "
          f"{len(episodes)} · re-entrees churn : {len(df) - len(episodes)}")
    ep = episodes[episodes["sl_source"] == "journal"]
    for label, lo_d, hi_d in SUBPERIODS:
        lo_ts, hi_ts = pd.Timestamp(lo_d, tz="UTC"), pd.Timestamp(hi_d, tz="UTC")
        sub = ep[(ep["open_date"] >= lo_ts) & (ep["open_date"] < hi_ts)]
        if not len(sub):
            print(f"  {label}: 0 episode")
            continue
        counts = sub["outcome"].value_counts().to_dict()
        print(f"  {label}: {len(sub)} episodes -> {counts}")
    print("\n-- stats episodes (SL initial seul, horizon "
          f"{args.horizon_days} j, granularite {args.tf}) --")
    wins = ep[ep["outcome"] == "TP"]
    print(f"heures jusqu'a +1,5R (touche avant SL)  : {quantiles(ep['h_to_1.5R'])}")
    print(f"heures jusqu'a +0,5R                    : {quantiles(ep['h_to_0.5R'])}")
    print(f"MFE brut fenetre 90 j (ignore le SL)    : {quantiles(ep['mfe_r'])}")
    print(f"MFE capturable (avant touche SL)        : {quantiles(ep['mfe_before_sl_r'])}")
    print("-- gagnants (TP avant SL) uniquement --")
    print(f"MAE avant +1,5R (R)                     : {quantiles(wins['mae_before_tp1_r'])}")
    print(f"continuation apres +1,5R, capturable    : {quantiles(wins['max_r_after_tp1'])}")
    print(f"heures du +1,5R au pic                  : {quantiles(wins['h_tp1_to_peak'])}")
    print(f"giveback pic -> creux (R)               : {quantiles(wins['giveback_after_peak_r'])}")
    print(f"repartition outcomes                    : {ep['outcome'].value_counts().to_dict()}")
    amb = int((ep["outcome"] == "SL_ambigu").sum())
    if amb:
        print(f"[NOTE] {amb} episodes ambigus (TP et SL sur la meme bougie {args.tf}, comptes SL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
