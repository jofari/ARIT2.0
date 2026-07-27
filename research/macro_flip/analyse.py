"""Analyse du run MacroFlip : benchmarks + test de significativite (Monte-Carlo).

Question posee : les 12 positions du Macro Analyst battent-elles (a) le buy & hold,
(b) une exposition longue permanente a la meme fraction d'equite, (c) le hasard ?

Modele d'equite reproduit depuis le backtest (verifie trade par trade, ecart < 0,3 pt) :
    equite_{n+1} = equite_n x (1 + FRACTION x rendement_n)
    rendement_n(sens) = sens x (rendement_prix_n + funding_long_n) - frais_aller_retour
ou `funding_long_n` est le cout de funding SI la position avait ete longue (donc
+funding pour un short). Inverser le sens inverse aussi le signe du funding : c'est ce
qui rend le tirage Monte-Carlo honnete.

Usage : python research/macro_flip/analyse.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from freqtrade.data.btanalysis import load_backtest_data

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "user_data" / "backtest_results"
DATA_4H = REPO / "user_data" / "data" / "binance" / "futures" / "BTC_USDT_USDT-4h-futures.feather"

FRACTION = 0.5          # 50 % de l'equite par position (demande Jonas)
FEES_ROUND_TRIP = 0.001  # 0,05 % taker a l'aller + au retour (Binance USDT-M)
N_MC = 20000
SEED = 42


def charger_trades() -> pd.DataFrame:
    zips = sorted(RESULTS.glob("backtest-result-*.zip"))
    df = load_backtest_data(zips[-1])
    df = df.sort_values("open_date").reset_index(drop=True)
    df["sens"] = np.where(df["is_short"], -1, 1)
    df["rdt_prix"] = df["close_rate"] / df["open_rate"] - 1.0
    # funding ramene a « ce qu'un LONG aurait paye », en fraction du stake
    df["funding_long"] = np.where(
        df["is_short"], -df["funding_fees"] / df["stake_amount"],
        df["funding_fees"] / df["stake_amount"])
    return df


def equite(rendements: np.ndarray, depart: float = 10000.0) -> float:
    return depart * np.prod(1.0 + FRACTION * rendements)


def main() -> None:
    tr = charger_trades()
    n = len(tr)
    prix = tr["rdt_prix"].to_numpy()
    fund = tr["funding_long"].to_numpy()
    sens = tr["sens"].to_numpy()

    def rdt(signes: np.ndarray) -> np.ndarray:
        return signes * (prix + fund) - FEES_ROUND_TRIP

    reel = equite(rdt(sens))
    print(f"=== MacroFlip : {n} positions, {tr.open_date.min():%Y-%m-%d} -> "
          f"{tr.close_date.max():%Y-%m-%d} ===")
    print(f"equite finale modelisee : {reel:,.0f} USDT  ({reel / 100 - 100:+.1f} %)")
    print("(controle backtest freqtrade : 36 348 USDT / +263,5 % — ecart = frais arrondis)\n")

    # --- benchmarks -----------------------------------------------------------------
    ohlc = pd.read_feather(DATA_4H)
    ohlc["date"] = pd.to_datetime(ohlc["date"], utc=True)
    fen = ohlc[(ohlc.date >= tr.open_date.min()) & (ohlc.date <= tr.close_date.max())]
    bh = fen.close.iloc[-1] / fen.open.iloc[0] - 1.0

    tout_long = equite(rdt(np.ones(n)))
    print("--- benchmarks sur la MEME fenetre ---")
    print(f"buy & hold BTC 100 % (spot, sans funding)      : {bh * 100:+8.1f} %")
    print(f"buy & hold BTC  50 % (reste en cash)           : {bh * FRACTION * 100:+8.1f} %")
    print(f"toujours LONG 50 %, memes 12 dates de rollover : "
          f"{tout_long / 100 - 100:+8.1f} %   <-- le signal macro doit battre CA")
    print(f"MacroFlip (signal macro)                       : {reel / 100 - 100:+8.1f} %\n")

    # --- decomposition --------------------------------------------------------------
    print("--- d'ou vient (ou pas) l'argent ---")
    for lib, masque in (("LONG ", sens > 0), ("SHORT", sens < 0)):
        sub = tr[masque]
        print(f"{lib} : {masque.sum():2d} positions | PnL {sub.profit_abs.sum():+9,.0f} USDT | "
              f"gagnantes {(sub.profit_abs > 0).sum()}/{masque.sum()} | "
              f"funding {sub.funding_fees.sum():+9,.0f} USDT")
    print(f"funding total paye sur toute la campagne : {tr.funding_fees.sum():+,.0f} USDT "
          f"({tr.funding_fees.sum() / 26348 * 100:.0f} % du profit net)\n")

    # --- Monte-Carlo : le signal bat-il un tirage a pile ou face ? -------------------
    rng = np.random.default_rng(SEED)
    tirages = rng.choice([-1.0, 1.0], size=(N_MC, n))
    finales = np.array([equite(rdt(t)) for t in tirages])
    p_sens = (finales >= reel).mean()
    print("--- Monte-Carlo A : memes 12 fenetres, SENS tire a pile ou face "
          f"({N_MC:,} tirages) ---")
    print(f"mediane du hasard : {np.median(finales):,.0f} USDT | "
          f"p90 : {np.percentile(finales, 90):,.0f} | max : {finales.max():,.0f}")
    print(f"MacroFlip = {reel:,.0f} USDT -> percentile {100 * (1 - p_sens):.1f} "
          f"(p = {p_sens:.3f})\n")

    # --- Monte-Carlo B : toujours long, mais fenetres placees au hasard --------------
    # Le funding est RECALCULE sur chaque fenetre tiree (sinon le hasard est avantage
    # d'un cout que MacroFlip, lui, paye vraiment — le biais du 1er jet de cette analyse).
    fr = pd.read_feather(REPO / "user_data" / "data" / "binance" / "futures"
                         / "BTC_USDT_USDT-1h-funding_rate.feather")
    fr["date"] = pd.to_datetime(fr["date"], utc=True)
    fr_i = fr.set_index("date")["open"].sort_index()
    ohlc_i = ohlc.set_index("date")
    durees = (tr.close_date - tr.open_date).dt.total_seconds().to_numpy()
    debut, fin = fen.date.iloc[0], fen.date.iloc[-1]
    span = (fin - debut).total_seconds()
    alea = []
    for _ in range(2000):
        rs = []
        for d in durees:
            t0 = debut + pd.Timedelta(seconds=float(rng.uniform(0, max(span - d, 1))))
            t1 = t0 + pd.Timedelta(seconds=float(d))
            seg = ohlc_i.loc[t0:t1, "close"]
            if len(seg) < 2:
                rs.append(0.0)
                continue
            p = seg.iloc[-1] / seg.iloc[0] - 1.0
            rs.append(p - float(fr_i.loc[t0:t1].sum()))   # un LONG paye la somme des funding
        alea.append(equite(np.array(rs) - FEES_ROUND_TRIP))
    alea = np.array(alea)
    print("--- Monte-Carlo B : toujours LONG sur perp, memes 12 durees placees au hasard "
          "(2 000 tirages, funding REEL de chaque fenetre) ---")
    print(f"mediane : {np.median(alea):,.0f} USDT | p90 : {np.percentile(alea, 90):,.0f}")
    print(f"MacroFlip = {reel:,.0f} -> percentile {100 * (alea < reel).mean():.1f}\n")

    # --- variante d'execution : le LONG en SPOT (zero funding), le SHORT en perp -----
    # Le funding n'est du que sur le perpetuel. Rien n'oblige a tenir un long de 2 ans
    # en perp : la meme exposition en spot ne coute rien a porter.
    rdt_spot = np.where(sens > 0, prix, -(prix + fund)) - FEES_ROUND_TRIP
    mixte = equite(rdt_spot)
    print("--- variante d'EXECUTION : long en spot (sans funding) + short en perp ---")
    print(f"MacroFlip execute en spot/perp : {mixte:,.0f} USDT ({mixte / 100 - 100:+.1f} %)")
    print(f"  vs MacroFlip tout-perp        : {reel:,.0f} USDT ({reel / 100 - 100:+.1f} %)")
    print(f"  vs buy & hold spot 50 %       : {10000 * (1 + FRACTION * bh):,.0f} USDT "
          f"({bh * FRACTION * 100:+.1f} %)")
    print(f"  vs buy & hold spot 100 %      : {10000 * (1 + bh):,.0f} USDT "
          f"({bh * 100:+.1f} %)")


if __name__ == "__main__":
    main()
