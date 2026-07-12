"""event_study.py — POC « arbre de probabilité v0 ».

Mesure le pouvoir prédictif des événements macro calendaires (FOMC, CPI US)
sur les rendements BTC/USDT daily (close->close), 2018-01 -> 2026-06.

Pipeline :
  1. Rendements conditionnels a J+1 / J+7 apres evenement vs baseline (tous les jours),
     bootstrap 90 % sur les moyennes.
  2. P(hausse | evenement, h) avec lissage bayesien Beta(2,2) + IC de credibilite 90 %.
  3. Stabilite par sous-periode (2018-2021 vs 2022-2026).
  4. Mini-arbre 2 niveaux : direction J->J+1 puis direction J+1->J+7 conditionnelle.
  5. Brier walk-forward : P estimees sur 2018-2022, testees sur 2023-2026,
     vs predicteur 50/50 et predicteur base rate.

Entrees : data/fomc_dates.csv, data/cpi_dates.csv (produits par fetch_dates.py)
          user_data/data/binance/BTC_USDT-1d.feather (relatif a la racine du repo).
Sortie  : tableaux markdown sur stdout (repris dans RESULTATS.md).

Usage : python event_study.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ----------------------------------------------------------------------------- constantes
SEED = 42
N_BOOT = 10_000
PRIOR_A = 2.0          # lissage bayesien Beta(alpha=2, beta=2)
PRIOR_B = 2.0
CI_LO, CI_HI = 0.05, 0.95   # intervalle 90 %
HORIZONS = (1, 7)

WINDOW_START = pd.Timestamp("2018-01-01")
WINDOW_END = pd.Timestamp("2026-06-30")
SPLIT_SUBPERIOD = pd.Timestamp("2022-01-01")   # 2018-2021 vs 2022-2026
SPLIT_WALKFWD = pd.Timestamp("2023-01-01")     # train 2018-2022 / test 2023-2026

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
FEATHER = REPO_ROOT / "user_data" / "data" / "binance" / "BTC_USDT-1d.feather"

rng = np.random.default_rng(SEED)


# ----------------------------------------------------------------------------- donnees
def load_prices() -> pd.DataFrame:
    """Closes daily indexes par date (naive UTC), + rendements close->close a 1 et 7 j."""
    df = pd.read_feather(FEATHER)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
    df = df.set_index("date").sort_index()
    full = pd.date_range(df.index[0], df.index[-1], freq="D")
    gaps = full.difference(df.index)
    if len(gaps):
        raise RuntimeError(f"trous dans les daily BTC: {list(gaps)[:5]} ...")
    out = pd.DataFrame(index=df.index)
    out["close"] = df["close"]
    for h in HORIZONS:
        out[f"ret{h}"] = df["close"].shift(-h) / df["close"] - 1.0
    # ret intermediaire J+1 -> J+7 pour le niveau 2 de l'arbre
    out["ret1to7"] = df["close"].shift(-7) / df["close"].shift(-1) - 1.0
    return out


def load_events(px: pd.DataFrame) -> dict[str, pd.DatetimeIndex]:
    """Dates d'evenements restreintes a la fenetre ET aux jours ou J+7 existe."""
    last_ok = px.index[-1] - pd.Timedelta(days=max(HORIZONS))
    events = {}
    for name, csv in (("FOMC", "fomc_dates.csv"), ("CPI", "cpi_dates.csv")):
        d = pd.to_datetime(pd.read_csv(HERE / "data" / csv)["date"])
        keep = d[(d >= WINDOW_START) & (d <= min(WINDOW_END, last_ok))]
        dropped = len(d) - len(keep)
        if dropped:
            print(f"<!-- {name}: {dropped} date(s) hors fenetre/donnees, ignoree(s) -->")
        missing = keep[~keep.isin(px.index)]
        if len(missing):
            raise RuntimeError(f"{name}: dates absentes des daily BTC: {list(missing)}")
        events[name] = pd.DatetimeIndex(keep)
    return events


# ----------------------------------------------------------------------------- stats
def boot_mean_ci(x: np.ndarray) -> tuple[float, float, float]:
    """Moyenne + IC bootstrap 90 % (percentiles)."""
    x = x[~np.isnan(x)]
    boots = rng.choice(x, size=(N_BOOT, len(x)), replace=True).mean(axis=1)
    return float(x.mean()), float(np.quantile(boots, CI_LO)), float(np.quantile(boots, CI_HI))


def beta_up(x: np.ndarray) -> tuple[float, float, float, int, int]:
    """P(hausse) posterieure Beta(2+k, 2+n-k) : moyenne, IC 90 %, k, n."""
    x = x[~np.isnan(x)]
    n, k = len(x), int((x > 0).sum())
    a, b = PRIOR_A + k, PRIOR_B + n - k
    return float(a / (a + b)), float(stats.beta.ppf(CI_LO, a, b)), float(stats.beta.ppf(CI_HI, a, b)), k, n


def fmt_p(row: tuple) -> str:
    p, lo, hi, k, n = row
    return f"{p:.3f} [{lo:.3f}, {hi:.3f}] (k={k}/n={n})"


def fmt_m(row: tuple) -> str:
    m, lo, hi = row
    return f"{m * 100:+.2f} % [{lo * 100:+.2f}, {hi * 100:+.2f}]"


# ----------------------------------------------------------------------------- analyses
def table_conditional(px: pd.DataFrame, events: dict, lo: pd.Timestamp, hi: pd.Timestamp, label: str) -> None:
    mask = (px.index >= lo) & (px.index <= hi) & px["ret7"].notna()
    base = px[mask]
    print(f"\n### {label}\n")
    print("| Condition | h | rendement moyen [IC boot 90 %] | P(hausse) [IC cred. 90 %] |")
    print("|---|---|---|---|")
    for h in HORIZONS:
        col = f"ret{h}"
        print(f"| Baseline (tous les jours) | J+{h} | {fmt_m(boot_mean_ci(base[col].values))} "
              f"| {fmt_p(beta_up(base[col].values))} |")
    for name, days in events.items():
        sub = px.loc[days[(days >= lo) & (days <= hi)]]
        for h in HORIZONS:
            col = f"ret{h}"
            print(f"| {name} | J+{h} | {fmt_m(boot_mean_ci(sub[col].values))} "
                  f"| {fmt_p(beta_up(sub[col].values))} |")


def tree(px: pd.DataFrame, events: dict) -> None:
    print("\n### Arbre v0 (2 niveaux, periode complete)\n")
    print("Niveau 1 : direction close(J)->close(J+1). Niveau 2 : direction close(J+1)->close(J+7),")
    print("conditionnelle a la branche du niveau 1. Probabilites lissees Beta(2,2), IC 90 %.\n")
    print("```")
    for name, days in events.items():
        sub = px.loc[days].dropna(subset=["ret1", "ret1to7"])
        p1 = beta_up(sub["ret1"].values)
        print(f"{name} (n={len(sub)})")
        for branch, cond in (("hausse J+1", sub["ret1"] > 0), ("baisse J+1", sub["ret1"] <= 0)):
            leg = sub[cond]
            p_branch = p1 if branch.startswith("hausse") else (1 - p1[0], 1 - p1[2], 1 - p1[1], p1[4] - p1[3], p1[4])
            p2 = beta_up(leg["ret1to7"].values)
            pre = "+--" if branch.startswith("hausse") else "\\--"
            bar = "|  " if branch.startswith("hausse") else "   "
            print(f" {pre} {branch}  P={p_branch[0]:.3f} [{p_branch[1]:.3f}, {p_branch[2]:.3f}]  (n={len(leg)})")
            print(f" {bar}  +-- hausse J+7  P={p2[0]:.3f} [{p2[1]:.3f}, {p2[2]:.3f}]")
            print(f" {bar}  \\-- baisse J+7  P={1 - p2[0]:.3f} [{1 - p2[2]:.3f}, {1 - p2[1]:.3f}]")
    print("```")


def brier(px: pd.DataFrame, events: dict) -> None:
    print("\n### Brier walk-forward (train 2018-2022 -> test 2023-2026)\n")
    print("| Evenement | h | n test | p_hat (train) | Brier evenement | Brier 50/50 | Brier base rate |")
    print("|---|---|---|---|---|---|---|")
    for name, days in events.items():
        train_days = days[days < SPLIT_WALKFWD]
        test_days = days[days >= SPLIT_WALKFWD]
        base_train = px[(px.index >= WINDOW_START) & (px.index < SPLIT_WALKFWD)]
        for h in HORIZONS:
            col = f"ret{h}"
            p_hat = beta_up(px.loc[train_days, col].values)[0]
            p_base = beta_up(base_train[col].dropna().values)[0]
            y = (px.loc[test_days, col].dropna() > 0).astype(float).values
            b_ev = float(np.mean((p_hat - y) ** 2))
            b_50 = float(np.mean((0.5 - y) ** 2))
            b_br = float(np.mean((p_base - y) ** 2))
            print(f"| {name} | J+{h} | {len(y)} | {p_hat:.3f} | {b_ev:.4f} | {b_50:.4f} | {b_br:.4f} |")


def main() -> None:
    px = load_prices()
    events = load_events(px)
    print(f"<!-- genere par event_study.py, seed={SEED}, N_BOOT={N_BOOT}, "
          f"donnees {px.index[0].date()} -> {px.index[-1].date()} -->")
    print(f"<!-- evenements retenus: " + ", ".join(f"{k}={len(v)}" for k, v in events.items()) + " -->")
    table_conditional(px, events, WINDOW_START, WINDOW_END, "Periode complete 2018-01 -> 2026-06")
    table_conditional(px, events, WINDOW_START, SPLIT_SUBPERIOD - pd.Timedelta(days=1), "Sous-periode 2018-2021")
    table_conditional(px, events, SPLIT_SUBPERIOD, WINDOW_END, "Sous-periode 2022-2026")
    tree(px, events)
    brier(px, events)


if __name__ == "__main__":
    main()
