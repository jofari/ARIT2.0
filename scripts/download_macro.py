"""Telecharge les 5 series macro du Macro Analyst V1.1 (SPEC_MACRO_V1.1_PROPOSITION).

Sources publiques gratuites, sans cle API. Sortie : user_data/data/macro/ (gitignore).
Usage :  python scripts/download_macro.py          # tout
         python scripts/download_macro.py dxy fng  # series choisies
Re-executable : ecrase les fichiers (les series sont petites, pas d'incremental).
"""

import json
import logging
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "user_data" / "data" / "macro"
UA = {"User-Agent": "ARIT-macro/1.0"}
TIMEOUT = 30
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
LLAMA_STABLES = "https://stablecoins.llama.fi/stablecoincharts/all"
BINANCE_FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
ALTERNATIVE_FNG = "https://api.alternative.me/fng/?limit=0&format=json"
FUNDING_PAGE = 1000          # max API
FUNDING_START_MS = 1568102400000  # 2019-09-10, debut des perps Binance
KLINES_PAGE = 1000                # max API
BTC_START_MS = 1502928000000      # 2017-08-17, 1re bougie BTCUSDT Binance

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("macro")


def _get(url: str, headers=UA, **kw) -> requests.Response:
    r = requests.get(url, headers=headers, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def dl_fred(sid: str, name: str) -> None:
    """DXY broad (DTWEXBGS) / taux Fed effectif (DFF) — CSV date,valeur.

    En-tetes par DEFAUT de requests, jamais UA (2026-08-07) : fredgraph.csv met notre
    User-Agent `ARIT-macro/1.0` au trou noir — ReadTimeout a 40 s, reproductible — alors
    qu'il repond en 0,1 s sans en-tete personnalise. Panne SILENCIEUSE depuis le
    2026-07-12 : dxy et taux, soit 2 des 5 composants 06.2, n'etaient plus rafraichis et
    `daily_regimes` les scorait donc a 0 sans que rien ne le signale.
    """
    csv = _get(FRED_CSV.format(sid=sid), headers=None).text
    (OUT_DIR / f"{name}.csv").write_text(csv, encoding="utf-8")
    log.info("%s : %d lignes", name, csv.count("\n"))


def dl_stablecoins() -> None:
    """DefiLlama — market cap total des stablecoins, 1 point/jour."""
    data = _get(LLAMA_STABLES).json()
    (OUT_DIR / "stablecoins.json").write_text(json.dumps(data), encoding="utf-8")
    log.info("stablecoins : %d points", len(data))


def dl_funding(symbol: str) -> None:
    """Binance perp — funding rate 8h, pagine depuis 2019."""
    rows, start = [], FUNDING_START_MS
    while True:
        page = _get(BINANCE_FUNDING,
                    params={"symbol": symbol, "startTime": start,
                            "limit": FUNDING_PAGE}).json()
        if not page:
            break
        rows.extend(page)
        start = page[-1]["fundingTime"] + 1
        if len(page) < FUNDING_PAGE:
            break
        time.sleep(0.3)  # politesse rate-limit
    out = OUT_DIR / f"funding_{symbol}.json"
    out.write_text(json.dumps(rows), encoding="utf-8")
    log.info("funding %s : %d points (8h)", symbol, len(rows))


def dl_btc_daily() -> None:
    """Binance spot — cloture 1d BTCUSDT, pour rho(BTC, actions) du bloc c7 (06 §6.2.1).

    Serie SEPAREE des 5 composants (elle n'entre dans aucune somme) et separee aussi des
    donnees OHLCV freqtrade : macro_regime ne lit que son propre repertoire (module pur).
    """
    rows, start = [], BTC_START_MS
    while True:
        page = _get(BINANCE_KLINES,
                    params={"symbol": "BTCUSDT", "interval": "1d",
                            "startTime": start, "limit": KLINES_PAGE}).json()
        if not page:
            break
        rows.extend(page)
        start = page[-1][0] + 1
        if len(page) < KLINES_PAGE:
            break
        time.sleep(0.3)  # politesse rate-limit
    (OUT_DIR / "btc_daily.json").write_text(json.dumps(rows), encoding="utf-8")
    log.info("btc_daily : %d bougies 1d", len(rows))


def dl_fng() -> None:
    """alternative.me — Fear & Greed, historique complet (2018-02+)."""
    data = _get(ALTERNATIVE_FNG).json()
    (OUT_DIR / "fear_greed.json").write_text(json.dumps(data), encoding="utf-8")
    log.info("fear_greed : %d points", len(data.get("data", [])))


JOBS = {
    "dxy": lambda: dl_fred("DTWEXBGS", "dxy"),
    "taux": lambda: dl_fred("DFF", "taux_fed"),
    # 06.2 c6 (bloc correlation) — NASDAQ100 et PAS SP500 (decision Jonas 2026-08-03, A3) :
    # la serie FRED `SP500` est une FENETRE GLISSANTE DE 10 ANS. Un re-run dans ~13 mois
    # ferait disparaitre le debut de la periode de backtest, que macro_regime traiterait comme
    # "serie pas encore demarree" => score 0, SANS exception ni log. `NASDAQ100` remonte a 1986
    # (historique stable) et est le meilleur comparable du BTC.
    "nasdaq100": lambda: dl_fred("NASDAQ100", "nasdaq100"),
    "btc_daily": dl_btc_daily,   # 06.2 c7 — cloture 1d BTC pour rho(BTC, actions)
    "stablecoins": dl_stablecoins,
    "funding": lambda: (dl_funding("BTCUSDT"), dl_funding("ETHUSDT")),
    "fng": dl_fng,
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or list(JOBS)
    failed = []
    for name in wanted:
        try:
            JOBS[name]()
        except Exception as exc:  # une serie qui echoue ne bloque pas les autres
            log.error("%s : ECHEC (%s: %s)", name, type(exc).__name__, exc)
            failed.append(name)
    if failed:
        log.error("series en echec : %s", ", ".join(failed))
        return 1
    log.info("OK — tout dans %s", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
