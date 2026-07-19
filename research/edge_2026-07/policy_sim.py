"""policy_sim.py — comparateur de politiques de gestion en R-space (analyse pure, E0).

Rejoue des politiques de sortie candidates sur les trajectoires 1h produites par
analysis/replay_entries.py (r_high/r_low/r_close ancres entree, SL initial = -1R,
TP1 = +1.5R). AUCUN code produit importe ; conventions miroir du replay :
- touche stop evaluee AVANT touche target dans la meme bougie (conservateur) ;
- mises a jour de trailing sur CLOTURE 1h uniquement (miroir PDR 03.4) ;
- le stop ne descend jamais ;
- frais/slippage ignores (R-space par trade) — identiques pour toutes les politiques.

Usage :
  python research/edge_2026-07/policy_sim.py --traj analysis/out/trajectories_1h.parquet \
      --summary analysis/out/summary.csv --out research/edge_2026-07/out/policies.csv
"""

from __future__ import annotations

import argparse
import pathlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

TP1_R = 1.5          # cible TP1 (PDR 03.3)
TP1_FRACTION = 0.5   # part vendue a TP1 (PDR 03.4 G4)
SL_INITIAL_R = -1.0  # par construction du R-space
BE_FLOOR_R = 0.1     # buffer frais approx. du BE G1 en R (PDR 03.4 G1 ~ +0.1 % prix)
ATR_WINDOW = 14


@dataclass
class Policy:
    """Une politique de gestion du reste de position (apres TP1 eventuel)."""

    name: str
    tp1: bool = True                 # vendre TP1_FRACTION a +1.5R
    tp_full: bool = False            # sortie TOTALE a +1.5R (controle A)
    be_after_r: float | None = None  # G1 : floor BE_FLOOR_R des que close >= x R
    be_after_tp1: bool = False       # floor BE_FLOOR_R seulement apres TP1
    trail_atr_mult: float | None = None   # chandelier : max(high) - k*ATR_R
    trail_after_r: float | None = None    # trailing actif seulement apres x R (close)
    giveback_frac: float | None = None    # sortie si retrace depuis peak > max(floor, frac*peak)
    giveback_floor_r: float = 1.5
    giveback_arm_r: float = 3.0           # giveback arme seulement une fois peak >= x R
    timestop_bars: int | None = None      # sortie si jamais >= timestop_min_r avant N bougies
    timestop_min_r: float = 0.5


POLICIES = [
    Policy("A_tp_fixe_1.5R", tp1=False, tp_full=True),
    Policy("HOLD_sl_seul", tp1=False),
    Policy("B_proxy_G1G3G4G7", be_after_r=1.0, trail_atr_mult=2.0, trail_after_r=1.0,
           timestop_bars=24),
    Policy("TP1+trail_chand_3atr", trail_atr_mult=3.0, trail_after_r=TP1_R),
    Policy("TP1+trail_chand_5atr", trail_atr_mult=5.0, trail_after_r=TP1_R),
    Policy("TP1+trail_chand_8atr", trail_atr_mult=8.0, trail_after_r=TP1_R),
    Policy("TP1+giveback_33pct", giveback_frac=0.33),
    Policy("TP1+giveback_50pct", giveback_frac=0.50),
    Policy("TP1+BE+trail5atr", be_after_tp1=True, trail_atr_mult=5.0, trail_after_r=TP1_R),
    Policy("TP1+trail5atr+ts48", trail_atr_mult=5.0, trail_after_r=TP1_R, timestop_bars=48),
    Policy("A_fixe+ts24", tp1=False, tp_full=True, timestop_bars=24),
    Policy("TP1+giveback50+BE", giveback_frac=0.50, be_after_tp1=True),
]


def simulate(policy: Policy, bars: pd.DataFrame) -> dict:
    """Rejoue une politique sur les bougies 1h d'UN trade. bars trie par ts."""
    r_high = bars["r_high"].to_numpy()
    r_low = bars["r_low"].to_numpy()
    r_close = bars["r_close"].to_numpy()
    n = len(bars)
    atr = pd.Series(r_high - r_low).rolling(ATR_WINDOW, min_periods=1).mean().to_numpy()

    remaining = 1.0
    realized = 0.0
    stop = SL_INITIAL_R
    tp1_done = False
    peak_close = 0.0
    peak_high = 0.0
    exit_reason = "end_of_data"
    bars_held = n
    reached_min = False

    for i in range(n):
        # 1) touche stop AVANT tout le reste (conservateur)
        if r_low[i] <= stop:
            realized += remaining * stop
            remaining = 0.0
            exit_reason = "stop"
            bars_held = i + 1
            break
        # 2) touches target intrabar
        if r_high[i] >= TP1_R and not tp1_done:
            if policy.tp_full:
                realized += remaining * TP1_R
                remaining = 0.0
                exit_reason = "tp_full"
                bars_held = i + 1
                break
            if policy.tp1:
                realized += TP1_FRACTION * TP1_R
                remaining -= TP1_FRACTION
            tp1_done = True
        # 3) cloture : etat + regles de gestion (jamais vers le bas)
        peak_close = max(peak_close, r_close[i])
        peak_high = max(peak_high, r_high[i])
        if r_close[i] >= policy.timestop_min_r:
            reached_min = True
        new_stop = stop
        if policy.be_after_r is not None and r_close[i] >= policy.be_after_r:
            new_stop = max(new_stop, BE_FLOOR_R)
        if policy.be_after_tp1 and tp1_done:
            new_stop = max(new_stop, BE_FLOOR_R)
        if policy.trail_atr_mult is not None:
            armed = policy.trail_after_r is None or peak_close >= policy.trail_after_r
            if armed:
                new_stop = max(new_stop, peak_high - policy.trail_atr_mult * atr[i])
        stop = new_stop
        # 4) sorties sur cloture
        if (policy.giveback_frac is not None and peak_close >= policy.giveback_arm_r
                and (peak_close - r_close[i])
                >= max(policy.giveback_floor_r, policy.giveback_frac * peak_close)):
            realized += remaining * r_close[i]
            remaining = 0.0
            exit_reason = "giveback"
            bars_held = i + 1
            break
        if (policy.timestop_bars is not None and i + 1 >= policy.timestop_bars
                and not reached_min):
            realized += remaining * r_close[i]
            remaining = 0.0
            exit_reason = "timestop"
            bars_held = i + 1
            break

    if remaining > 0:
        realized += remaining * r_close[-1]

    return {"final_r": realized, "exit_reason": exit_reason, "bars_held": bars_held,
            "tp1_hit": tp1_done or exit_reason == "tp_full"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", type=pathlib.Path, required=True)
    ap.add_argument("--summary", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()

    traj = pd.read_parquet(args.traj).sort_values(["trade_id", "ts"])
    summary = pd.read_csv(args.summary)
    # dedup churn : 1 trade representant par episode (le premier ouvert)
    if "episode_id" in summary.columns:
        keep = (summary.sort_values("open_ts").groupby("episode_id").head(1))
        rep_ids = set(keep["pair"].astype(str) + "-" + keep["open_ts"].astype(str))
        traj = traj[traj["trade_id"].isin(rep_ids)]
        print(f"episodes: {len(rep_ids)} (sur {len(summary)} trades zip)")

    rows = []
    per_trade: dict[str, dict[str, float]] = {}
    for policy in POLICIES:
        res = [dict(simulate(policy, g), trade_id=tid)
               for tid, g in traj.groupby("trade_id", sort=False)]
        df = pd.DataFrame(res)
        for record in res:
            per_trade.setdefault(record["trade_id"], {})[policy.name] = record["final_r"]
        fr = df["final_r"]
        rows.append({
            "policy": policy.name, "n": len(df),
            "expectancy_r": fr.mean(), "median_r": fr.median(), "total_r": fr.sum(),
            "win_pct": (fr > 0).mean() * 100,
            "p25_r": fr.quantile(0.25), "p75_r": fr.quantile(0.75),
            "p90_r": fr.quantile(0.90), "max_r": fr.max(),
            "avg_bars": df["bars_held"].mean(),
            "stops_pct": (df["exit_reason"] == "stop").mean() * 100,
            "tp1_pct": df["tp1_hit"].mean() * 100,
        })

    out = pd.DataFrame(rows).sort_values("expectancy_r", ascending=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    pd.DataFrame(per_trade).T.to_csv(args.out.with_name("per_trade_r.csv"))
    pd.set_option("display.width", 200)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
