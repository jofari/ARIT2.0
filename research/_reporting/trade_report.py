"""Rapport de backtest trade-par-trade — fichier HTML autonome, 100 % LOCAL.

Rien ne sort de la machine : le HTML produit embarque ses donnees, son CSS et son JS,
et s'ouvre par double-clic. Aucun reseau, aucun CDN, aucune publication.

    & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe research/_reporting/trade_report.py ^
        --trades research/macro_flip/trades_hold_neutre.csv ^
        --out    research/macro_flip/RAPPORT_TRADES.html ^
        --titre  "MacroFlip - les 12 trades, entree par entree" ^
        --meta   "Run backtest-result-2026-07-27_19-38-05" ^
        --meta   "BTC/USDT:USDT perp - 4h - detail 5m"

Le signal decrit fiche par fiche est le regime macro (docs/06 par.6.2), rejoue depuis
`arit_lib.macro_regime` sur `user_data/data/macro/`. Le CSV de trades attendu est celui
exporte par freqtrade (colonnes open_date, close_date, is_short, open_rate, close_rate,
stake_amount, profit_abs, profit_ratio, funding_fees, exit_reason, enter_tag).
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))

from arit_lib import contracts, macro_regime, params  # noqa: E402

LOG = logging.getLogger("trade_report")

TEMPLATE = Path(__file__).with_name("template.html")
PRICE_FEATHER = REPO / "user_data" / "data" / "binance" / "BTC_USDT-1d.feather"
MACRO_DIR = REPO / "user_data" / contracts.MACRO_DATA_DIR

# Marge d'historique affichee avant la 1re position, pour situer le regime d'entree.
LEAD_IN_DAYS = 45


# ----------------------------------------------------------------- donnees macro
def macro_timeline() -> pd.DataFrame:
    """Table quotidienne : 5 scores + regime + valeurs brutes mesurees + close BTC.

    Les valeurs brutes sont recalculees avec les MEMES fenetres et le meme decalage
    point-in-time (+1 jour) que `macro_regime.daily_regimes`, sinon la valeur affichee
    ne correspondrait pas au score affiche a cote.
    """
    hist = macro_regime.load_history(MACRO_DIR)
    if hist.empty:
        raise SystemExit(f"aucune donnee macro lisible dans {MACRO_DIR}")
    daily = macro_regime.daily_regimes(hist)

    full = pd.date_range(hist.index.min(), hist.index.max(), freq="D", tz="UTC")
    h = hist.reindex(full).ffill(limit=int(params.MACRO_STALE_HOURS / 24))

    # suffixe _m : les colonnes de scores portent deja les noms bruts dans `daily`
    met = pd.DataFrame(index=full)
    met["dxy_m"] = h["dxy"] / h["dxy"].shift(params.MACRO_DXY_WINDOW_D) - 1.0
    met["taux_m"] = h["taux"] - h["taux"].shift(params.MACRO_RATES_WINDOW_D)
    met["stablecoins_m"] = (h["stablecoins"] / h["stablecoins"].shift(params.MACRO_STABLES_WINDOW_D)) - 1.0
    met["funding_m"] = h["funding"].rolling(params.MACRO_FUNDING_WINDOW_D).mean()
    met["fear_greed_m"] = h["fear_greed"]
    met = met.shift(1)  # meme decalage point-in-time que daily_regimes

    out = daily.join(met)
    out["total"] = out[list(contracts.MACRO_SCORE_KEYS)].sum(axis=1)

    try:
        px = pd.read_feather(PRICE_FEATHER)
        px["date"] = pd.to_datetime(px["date"], utc=True)
        out["close"] = px.set_index("date")["close"].reindex(full).ffill()
    except (OSError, ValueError, KeyError) as exc:
        LOG.warning("prix indisponible (%s) : les graphes seront vides", exc)
        out["close"] = pd.NA
    return out


def read_trades(path: Path) -> list[dict]:
    """CSV freqtrade -> liste de trades normalises (dates en date seule, UTC)."""
    trades = []
    with open(path, encoding="utf-8") as fh:
        for i, t in enumerate(csv.DictReader(fh), start=1):
            od, cd = t["open_date"][:10], t["close_date"][:10]
            trades.append({
                "no": int(t.get("no") or i),
                "open": od, "close": cd,
                "short": str(t["is_short"]).lower() in ("true", "1"),
                "open_rate": float(t["open_rate"]), "close_rate": float(t["close_rate"]),
                "stake": float(t["stake_amount"]),
                "pnl": float(t["profit_abs"]), "ratio": float(t["profit_ratio"]),
                "funding": float(t.get("funding_fees") or 0.0),
                "exit_reason": t.get("exit_reason", ""), "tag": t.get("enter_tag", ""),
                "days": (datetime.fromisoformat(cd) - datetime.fromisoformat(od)).days,
            })
    if not trades:
        raise SystemExit(f"aucun trade dans {path}")
    return trades


def equity_curve(rows: list[dict], trades: list[dict], capital: float) -> None:
    """Ajoute `e` (capital marque au marche) a chaque ligne, et le capital entree/sortie par trade.

    La courbe des trades CLOTURES ne montre rien entre deux clotures espacees de deux ans :
    c'est ce qui faisait afficher un drawdown de 24 % la ou le creux reel etait de ~60 %.
    Ici le capital est reevalue chaque jour :

        capital = capital a l'entree + mise x sens x (prix/prix_entree - 1) + funding couru

    Le funding total du trade est reparti au prorata des jours (freqtrade ne donne que le
    total par trade) : approximation assumee, elle ne change pas la forme de la courbe.
    """
    idx = {r["d"]: i for i, r in enumerate(rows)}
    base = float(capital)

    for r in rows:
        r["e"] = None
    for i in range(idx.get(trades[0]["open"], 0) + 1):
        rows[i]["e"] = round(base, 2)

    for tr in trades:
        i0 = idx.get(tr["open"])
        i1 = idx.get(tr["close"], len(rows) - 1)
        if i0 is None:
            LOG.warning("trade #%s hors plage de donnees, ignore dans la courbe", tr["no"])
            continue
        sign = -1.0 if tr["short"] else 1.0
        span = max(i1 - i0, 1)
        tr["equity_in"] = round(base, 2)
        for k in range(i0, min(i1, len(rows) - 1) + 1):
            px = rows[k]["c"]
            if px is None:
                continue
            unreal = tr["stake"] * sign * (px / tr["open_rate"] - 1.0)
            rows[k]["e"] = round(base + unreal + tr["funding"] * (k - i0) / span, 2)
        base += tr["pnl"]
        tr["equity_out"] = round(base, 2)
        if i1 < len(rows):
            rows[min(i1, len(rows) - 1)]["e"] = round(base, 2)

    # dernier point connu prolonge jusqu'au bout, pour ne pas casser la courbe
    seen = None
    for r in rows:
        if r["e"] is None:
            r["e"] = seen
        else:
            seen = r["e"]


def build_payload(tl: pd.DataFrame, trades: list[dict], capital: float) -> dict:
    """Serialise la table quotidienne + les trades, fenetre reduite a ce qui est affiche."""
    keys = list(contracts.MACRO_SCORE_KEYS)
    first = min(t["open"] for t in trades)
    start = (pd.Timestamp(first, tz="UTC") - pd.Timedelta(days=LEAD_IN_DAYS)).strftime("%Y-%m-%d")
    tl = tl.loc[start:]

    rows = []
    for d, r in tl.iterrows():
        rows.append({
            "d": d.strftime("%Y-%m-%d"),
            "r": r[contracts.MACRO_REGIME_COL],
            "s": [int(r[k]) for k in keys],
            "t": int(r["total"]),
            "c": None if pd.isna(r["close"]) else round(float(r["close"]), 1),
            "m": [None if pd.isna(r[k + "_m"]) else round(float(r[k + "_m"]), 6) for k in keys],
        })

    equity_curve(rows, trades, capital)

    idx = {r["d"]: i for i, r in enumerate(rows)}
    last = len(rows) - 1
    for tr in trades:
        # date de bascule du regime qui a declenche l'entree = 1er jour de la serie en cours
        i = idx.get(tr["open"], last)
        regime, j = rows[i]["r"], i
        while j > 0 and rows[j - 1]["r"] == regime:
            j -= 1
        tr["regime_since"] = rows[j]["d"]
    return {"keys": keys, "rows": rows, "trades": trades}


def _h1(titre: str) -> str:
    """« Sujet — le titre » -> « Le titre » (le sujet est deja dans l'eyebrow)."""
    t = titre.split("—")[-1].strip() if "—" in titre else titre
    return t[:1].upper() + t[1:]


def render(payload: dict, out: Path, titre: str, eyebrow: str, meta: list[str]) -> None:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    n = len(payload["trades"])
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = (tpl
            .replace("__TITLE__", html.escape(titre))
            .replace("__H1__", html.escape(_h1(titre)))
            .replace("__EYEBROW__", html.escape(eyebrow))
            .replace("__META__", "\n    ".join(f"<span>{html.escape(m)}</span>" for m in meta))
            .replace("__H2_OVERVIEW__", "La periode d'un seul coup d'oeil")
            .replace("__H2_INDEX__", f"Les {n} positions")
            .replace("__PAYLOAD__", blob))
    assert "__PAYLOAD__" not in page and "__META__" not in page
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trades", required=True, type=Path, help="CSV de trades freqtrade")
    ap.add_argument("--out", required=True, type=Path, help="fichier HTML a ecrire")
    ap.add_argument("--titre", default="Backtest — trade par trade")
    ap.add_argument("--eyebrow", default="ARIT · Recherche")
    ap.add_argument("--meta", action="append", default=[],
                    help="ligne de contexte dans l'entete (repetable)")
    ap.add_argument("--capital", type=float, default=10000.0,
                    help="capital de depart du run, en USDT (defaut 10000)")
    args = ap.parse_args()

    trades = read_trades(args.trades)
    payload = build_payload(macro_timeline(), trades, args.capital)
    payload["capital"] = args.capital
    render(payload, args.out, args.titre, args.eyebrow, args.meta or [args.trades.name])
    LOG.info("%d trades -> %s (%.0f Ko, local, aucun reseau)",
             len(trades), args.out.resolve(), args.out.stat().st_size / 1024)


if __name__ == "__main__":
    main()
