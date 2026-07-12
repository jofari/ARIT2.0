"""fetch_dates.py — Récupère et parse les dates FOMC (federalreserve.gov) et CPI US
(bls.gov via Wayback Machine, car bls.gov bloque les clients non-navigateur).

Produit :
  data/fomc_dates.csv  (date de DÉCISION, dernier jour de la réunion, meetings programmés uniquement)
  data/cpi_dates.csv   (date de PUBLICATION du CPI, ~08:30 ET)

Fenêtre : 2018-01-01 -> 2026-06-30.
Le HTML brut est mis en cache dans data/raw_html/ : relancer le script hors-ligne
fonctionne tant que le cache existe.

Usage : python fetch_dates.py
"""

import csv
import logging
import re
import urllib.request
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("fetch_dates")

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "data" / "raw_html"
DATA_DIR = HERE / "data"

WINDOW_START = date(2018, 1, 1)
WINDOW_END = date(2026, 6, 30)

FED_BASE = "https://www.federalreserve.gov/monetarypolicy"
# fomccalendars.htm couvre les ~6 dernières années + à venir (2021-2027 au moment du fetch).
FOMC_PAGES = {
    "fomccalendars.htm": f"{FED_BASE}/fomccalendars.htm",
    "fomchistorical2018.htm": f"{FED_BASE}/fomchistorical2018.htm",
    "fomchistorical2019.htm": f"{FED_BASE}/fomchistorical2019.htm",
    "fomchistorical2020.htm": f"{FED_BASE}/fomchistorical2020.htm",
}

# Snapshots Wayback du calendrier CPI du BLS ; chaque snapshot couvre ~18-24 mois
# glissants. Les snapshots plus récents ÉCRASENT les plus anciens (dates re-planifiées).
CPI_WAYBACK_TIMESTAMPS = [
    "20170712", "20180910", "20190601", "20200607", "20210607",
    "20220605", "20230607", "20240604", "20250605", "20251219", "20260601",
]
CPI_URL = "https://www.bls.gov/schedule/news_release/cpi.htm"

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"])}
MONTH_ABBR = {m[:3]: i for m, i in MONTHS.items()}
MONTH_ABBR.update({"Sept": 9})

EXCLUDE_KEYWORDS = ("unscheduled", "cancelled", "notation vote")


def fetch(url: str, cache_name: str) -> str:
    """Télécharge une page (ou lit le cache) et renvoie le HTML."""
    cache = RAW_DIR / cache_name
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"echec telechargement {url}: {exc}") from exc
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(html, encoding="utf-8")
    log.info("telecharge %s (%d octets)", url, len(html))
    return html


def _month_num(name: str) -> int:
    name = name.strip()
    if name in MONTHS:
        return MONTHS[name]
    if name.rstrip(".") in MONTH_ABBR:
        return MONTH_ABBR[name.rstrip(".")]
    raise ValueError(f"mois inconnu: {name!r}")


def _decision_date(month_field: str, day_field: str, year: int) -> date:
    """'April/May' + '30-1' -> 1er mai ; 'January' + '27-28' -> 28 janvier.
    La décision tombe le DERNIER jour de la réunion."""
    months = [_month_num(m) for m in month_field.split("/")]
    days = [int(d) for d in re.findall(r"\d+", day_field)]
    last_day = days[-1]
    # Réunion à cheval sur deux mois : le dernier jour appartient au 2e mois.
    month = months[-1] if (len(months) == 2 and len(days) == 2 and days[1] < days[0]) else months[0]
    return date(year, month, last_day)


def parse_fomc_calendars(html: str) -> list[tuple[date, str]]:
    """Page fomccalendars.htm : panneaux annuels avec divs month/date."""
    out = []
    # Découpe par panneau annuel.
    year_iter = list(re.finditer(r"(\d{4}) FOMC Meetings", html))
    for i, ym in enumerate(year_iter):
        year = int(ym.group(1))
        seg = html[ym.end(): year_iter[i + 1].start() if i + 1 < len(year_iter) else len(html)]
        months = re.findall(r'fomc-meeting__month[^>]*>(?:<strong>)?([^<]+)', seg)
        days = re.findall(r'fomc-meeting__date[^>]*>([^<]+)', seg)
        if len(months) != len(days):
            log.warning("annee %d: %d mois vs %d dates, appariement positionnel", year, len(months), len(days))
        for month_field, day_field in zip(months, days):
            if any(k in day_field.lower() for k in EXCLUDE_KEYWORDS):
                continue
            d = _decision_date(month_field, day_field.replace("*", "").strip(), year)
            out.append((d, "fomccalendars.htm"))
    return out


def parse_fomc_historical(html: str, src: str) -> list[tuple[date, str]]:
    """Pages fomchistoricalYYYY.htm : <h5>January 30-31 Meeting - 2018</h5>."""
    out = []
    for m in re.finditer(r"<h5[^>]*>([A-Za-z/]+) ([\d-]+)([^<]*)- (\d{4})</h5>", html):
        month_field, day_field, extra, year = m.group(1), m.group(2), m.group(3), int(m.group(4))
        if any(k in extra.lower() for k in EXCLUDE_KEYWORDS):
            continue
        # Pages historiques : abréviations type 'Jul/Aug'.
        out.append((_decision_date(month_field, day_field, year), src))
    return out


def build_fomc() -> list[tuple[date, str]]:
    seen: dict[date, str] = {}
    for name, url in FOMC_PAGES.items():
        html = fetch(url, name)
        rows = parse_fomc_calendars(html) if name == "fomccalendars.htm" else parse_fomc_historical(html, name)
        for d, src in rows:
            seen.setdefault(d, src)
    dates = sorted((d, s) for d, s in seen.items() if WINDOW_START <= d <= WINDOW_END)
    log.info("FOMC: %d decisions dans la fenetre", len(dates))
    return dates


def build_cpi() -> list[tuple[date, str, str]]:
    """Renvoie [(date_publication, mois_de_reference, source_snapshot)]."""
    by_ref: dict[str, tuple[date, str]] = {}
    row_re = re.compile(
        r"<td>([A-Za-z]+ \d{4})</td>\s*<td>([A-Za-z.]+)\s+(\d{1,2}),\s+(\d{4})</td>\s*<td>(\d{2}:\d{2} [AP]M)</td>")
    for ts in CPI_WAYBACK_TIMESTAMPS:  # ordre chronologique : le plus récent gagne
        url = f"http://web.archive.org/web/{ts}id_/{CPI_URL}"
        try:
            html = fetch(url, f"cpi_wayback_{ts}.html")
        except RuntimeError as exc:
            log.warning("snapshot %s ignore: %s", ts, exc)
            continue
        for ref, mon, day, year, _time in row_re.findall(html):
            d = date(int(year), _month_num(mon), int(day))
            by_ref[ref] = (d, f"wayback_{ts}")
    rows = sorted((d, ref, src) for ref, (d, src) in by_ref.items()
                  if WINDOW_START <= d <= WINDOW_END)
    log.info("CPI: %d publications dans la fenetre", len(rows))
    # Contrôle de complétude : on attend ~1 publication/mois.
    months_seen = {(d.year, d.month) for d, _, _ in rows}
    expected = [(y, m) for y in range(2018, 2027) for m in range(1, 13)
                if WINDOW_START <= date(y, m, 15) <= WINDOW_END]
    missing = [f"{y}-{m:02d}" for y, m in expected if (y, m) not in months_seen]
    if missing:
        log.warning("mois calendaires sans publication CPI detectee: %s", missing)
    return rows


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fomc = build_fomc()
    with open(DATA_DIR / "fomc_dates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "source"])
        w.writerows([(d.isoformat(), s) for d, s in fomc])
    cpi = build_cpi()
    with open(DATA_DIR / "cpi_dates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "reference_month", "source"])
        w.writerows([(d.isoformat(), ref, s) for d, ref, s in cpi])
    log.info("ecrit: %s (%d lignes), %s (%d lignes)",
             DATA_DIR / "fomc_dates.csv", len(fomc), DATA_DIR / "cpi_dates.csv", len(cpi))


if __name__ == "__main__":
    main()
