"""Verificateurs MECANIQUES des interdits PDR n.3 (zero look-ahead) et du warm-up indicateurs.

Enveloppe les deux commandes freqtrade natives, avec les conventions ARIT en dur
(strategie AritV1, user_data/config.dry.json, venv C:\\Users\\jofar\\venvs\\arit) :

  1. `freqtrade lookahead-analysis`  -> rejoue la strategie sur des fenetres tronquees et
     verifie qu'un signal passe ne change pas quand on ajoute du futur. C'est la preuve
     mecanique de l'interdit n.3, aujourd'hui garanti seulement par relecture humaine
     (pivots shift(2), process_only_new_candles, bougies closes, merge freqtrade).
  2. `freqtrade recursive-analysis` -> recalcule les indicateurs avec 199/499/999/1999
     bougies de warm-up et compare la DERNIERE ligne. Si les valeurs bougent, le
     `startup_candle_count` de la strategie (EMA_SLOW = 200) est trop court : l'EMA200 est
     fausse au debut de chaque run et le backtest est faux SANS LE DIRE.

Sorties (analysis/out/bias/, gitignore) : log brut de chaque commande, CSV freqtrade du
look-ahead, rapport `bias_<horodatage>.md` + `.json` (verdicts machine-lisibles).

Codes de sortie :  0 = tout PASS  ·  1 = au moins un FAIL  ·  2 = indetermine / erreur outil.

Usage (PowerShell) :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe scripts\\check_bias.py
  ... scripts\\check_bias.py --only lookahead --timerange 20230101-20240101
  ... scripts\\check_bias.py --only recursive --startup-candles 199 499 999 1999
  ... scripts\\check_bias.py --timeframe-detail 5m      # execution fidele au backtest, tres lent

Note : `--timeframe-detail` n'est PAS applique par defaut (contrairement aux backtests, ou il
est contractuel, PDR 07.2). Ces deux checks portent sur les indicateurs et les signaux, pas sur
l'execution intra-bougie ; la 5m multiplie le temps de calcul sans rien changer au verdict.
"""

import argparse
import csv
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "analysis" / "out" / "bias"
VENV_FREQTRADE = Path(r"C:\Users\jofar\venvs\arit\Scripts\freqtrade.exe")
CONFIG = REPO / "user_data" / "config.dry.json"
STRATEGY = "AritV1"

DEFAULT_TIMERANGE = "20230101-20240101"   # ~1 an : assez de signaux, run qui reste tenable
TARGETED_TRADES = 200                     # nb de signaux vises par lookahead-analysis
MINIMUM_TRADES = 20                       # en dessous : verdict non concluant, pas "PASS"
STARTUP_CANDLES = (199, 499, 999, 1999)   # freqtrade ajoute d'office le compte de la strategie
RECURSIVE_FAIL_PCT = 0.001                # 0,1 % d'ecart sur un indicateur => FAIL (sinon WARN)
CONSOLE_WIDTH = "250"                     # sinon rich tronque ses tableaux a 80 colonnes

VERTICAL_BARS = "\u2502|"                 # separateurs de cellules des tableaux rich
# freqtrade peut sortir en erreur AVEC un code 0 (ex. plafond des bougies de warm-up :
# "requires 6400 candles to start, which is more than 5x (4999 candles)"). Sans ca, le
# verdict serait un vague "tableau introuvable".
ERROR_LINE = re.compile(r"(?:Configuration error|OperationalException|ERROR - )\s*:?\s*(.+)")

PASS, FAIL, WARN, UNKNOWN = "PASS", "FAIL", "WARN", "INDETERMINE"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("bias")


def freqtrade_bin() -> str:
    """Executable freqtrade : $ARIT_FREQTRADE > venv arit > PATH."""
    override = os.environ.get("ARIT_FREQTRADE")
    if override:
        return override
    if VENV_FREQTRADE.exists():
        return str(VENV_FREQTRADE)
    found = shutil.which("freqtrade")
    if not found:
        raise SystemExit(f"freqtrade introuvable ({VENV_FREQTRADE} absent, pas dans le PATH)")
    return found


def run_cli(args: list[str], log_path: Path) -> tuple[int, str]:
    """Lance freqtrade, ecrit le log AU FIL DE L'EAU, renvoie (code de retour, sortie complete).

    Ecriture ligne par ligne (et non a la fin) : un lookahead-analysis peut tourner une heure,
    le log doit etre suivable en direct (`Get-Content -Wait`) pour savoir ou il en est.
    """
    cmd = [freqtrade_bin()] + args
    log.info("$ %s", " ".join(cmd))
    log.info("suivi en direct : Get-Content -Wait %s", log_path)
    env = dict(os.environ, COLUMNS=CONSOLE_WIDTH, PYTHONIOENCODING="utf-8")
    lines: list[str] = []
    try:
        with subprocess.Popen(
            cmd, cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        ) as proc, log_path.open("w", encoding="utf-8") as fh:
            for line in proc.stdout:
                lines.append(line)
                fh.write(line)
                fh.flush()
            code = proc.wait()
    except OSError as exc:
        raise SystemExit(f"echec du lancement de freqtrade : {exc}") from exc
    log.info("code=%d, log complet : %s", code, log_path)
    return code, "".join(lines)


def parse_rich_table(stdout: str, header_cell: str) -> tuple[list[str], list[list[str]]]:
    """(en-tetes, lignes) d'un tableau rich, repere par un intitule de sa ligne d'en-tete.

    Les en-tetes sont lus dans la sortie, jamais reconstruits : freqtrade ajoute d'office le
    `startup_candle_count` de la strategie a la liste demandee (colonne « 200 (from strategy) »).

    Les cellules trop longues sont repliees par rich sur plusieurs lignes : une ligne dont
    la 1re cellule est vide est un repli, recollee a la ligne precedente. Un nom d'indicateur
    replie (1re cellule non vide) resterait indissociable d'une vraie ligne — improbable a
    COLUMNS=250, et sans effet sur les verdicts (calcules sur les cellules numeriques / le CSV).
    """
    headers: list[str] = []
    rows: list[list[str]] = []
    in_table = False
    for raw in stdout.splitlines():
        line = raw.strip()
        if not any(bar in line for bar in VERTICAL_BARS):
            continue
        cells = [c.strip() for c in re.split(f"[{VERTICAL_BARS}]", line)]
        cells = cells[1:-1] if len(cells) > 2 else cells
        if not any(cells):
            continue
        if header_cell in cells:
            in_table, headers, rows = True, cells, []
            continue
        if not in_table:
            continue
        if not cells[0] and rows:
            rows[-1] = [(a + " " + b).strip() for a, b in zip(rows[-1], cells)]
        else:
            rows.append(cells)
    return headers, rows


def freqtrade_error(stdout: str) -> str:
    """1re erreur freqtrade de la sortie ('' si aucune), meme quand le code de retour est 0."""
    match = ERROR_LINE.search(stdout)
    return match.group(1).strip() if match else ""


def _fmt_table(headers: list[str], rows: list[list[str]]) -> str:
    """Tableau markdown (les rapports sont lus dans Obsidian / Discord). Ne tronque jamais."""
    width = max([len(headers)] + [len(r) for r in rows])
    headers = (headers + [""] * width)[:width]
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * width]
    for row in rows:
        cells = (row + [""] * width)[:width]
        out.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(out)


def check_lookahead(args, stamp: str) -> dict:
    """freqtrade lookahead-analysis -> verdict + CSV natif."""
    csv_path = OUT_DIR / f"lookahead_{stamp}.csv"
    cli = [
        "lookahead-analysis", "--strategy", STRATEGY, "-c", str(args.config),
        "--timerange", args.timerange,
        "--targeted-trade-amount", str(args.targeted_trades),
        "--minimum-trade-amount", str(args.minimum_trades),
        "--lookahead-analysis-exportfilename", str(csv_path),
        "--no-color",
    ]
    if args.timeframe_detail:
        cli += ["--timeframe-detail", args.timeframe_detail]
    if args.pairs:
        cli += ["-p"] + args.pairs

    code, stdout = run_cli(cli, OUT_DIR / f"lookahead_{stamp}.log")
    result = {"check": "lookahead-analysis", "verdict": UNKNOWN, "returncode": code,
              "csv": str(csv_path), "headers": [], "rows": [], "details": ""}

    err = freqtrade_error(stdout)
    if code != 0 or err:
        result["details"] = f"freqtrade en erreur : {err or 'voir le log'}"
        return result

    result["headers"], table = parse_rich_table(stdout, "has_bias")
    result["rows"] = table
    # Le CSV n'est ecrit QUE si le check a abouti (assez de signaux, pas d'erreur) : son
    # absence ou sa vacuite = verdict non concluant, jamais un PASS. La raison exacte est
    # dans la 3e colonne du tableau ("too few trades caught (0/20).Test failed.").
    reason = next((r[2] for r in table if len(r) > 2 and r[1] == STRATEGY), "")
    entries = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as fh:
            entries = [r for r in csv.DictReader(fh) if r.get("strategy") == STRATEGY]
    if not entries:
        result["details"] = (
            f"check non concluant : {reason or 'pas de ligne exploitable'} "
            f"(seuil --minimum-trades = {args.minimum_trades} · fenetre {args.timerange})"
        )
        return result

    row = entries[-1]
    biased = str(row.get("has_bias", "")).strip().lower() == "true"
    result["has_bias"] = biased
    result["total_signals"] = int(row.get("total_signals") or 0)
    result["biased_entry_signals"] = int(row.get("biased_entry_signals") or 0)
    result["biased_exit_signals"] = int(row.get("biased_exit_signals") or 0)
    result["biased_indicators"] = [i for i in (row.get("biased_indicators") or "").split(",") if i]
    result["verdict"] = FAIL if biased else PASS
    result["details"] = (
        f"{result['total_signals']} signaux testes · "
        f"{result['biased_entry_signals']} entrees biaisees · "
        f"{result['biased_exit_signals']} sorties biaisees"
        + (f" · indicateurs : {', '.join(result['biased_indicators'])}"
           if result["biased_indicators"] else "")
    )
    return result


def _worst_pct(cells: list[str]) -> float:
    """Plus grand ecart absolu d'une ligne du tableau recursif ('0.123%', '-', 'nan%').

    'nan%' = freqtrade a vu une difference non chiffrable (valeur non numerique ou nulle) :
    ca compte comme derive (la ligne existe) mais pas dans l'ecart max.
    """
    worst = 0.0
    for cell in cells:
        try:
            value = abs(float(cell.rstrip("%")) / 100.0)
        except ValueError:
            continue
        if math.isfinite(value):
            worst = max(worst, value)
    return worst


def check_recursive(args, stamp: str) -> dict:
    """freqtrade recursive-analysis -> verdict sur startup_candle_count + lookahead indicateurs."""
    cli = [
        "recursive-analysis", "--strategy", STRATEGY, "-c", str(args.config),
        "--timerange", args.timerange,
        "--startup-candle", *[str(c) for c in args.startup_candles],
        "--no-color",
    ]
    if args.pairs:
        cli += ["-p"] + args.pairs

    code, stdout = run_cli(cli, OUT_DIR / f"recursive_{stamp}.log")
    result = {"check": "recursive-analysis", "verdict": UNKNOWN, "returncode": code,
              "headers": [], "rows": [], "details": "",
              "indicator_lookahead": UNKNOWN}

    err = freqtrade_error(stdout)
    if code != 0 or err:
        result["details"] = f"freqtrade en erreur : {err or 'voir le log'}"
        return result

    # Second verdict offert par la commande : look-ahead sur les indicateurs seuls.
    found = re.findall(r"found lookahead in indicator (\S+)", stdout)
    if found:
        result["indicator_lookahead"] = FAIL
        result["indicator_lookahead_indicators"] = sorted(set(found))
    elif "No lookahead bias on indicators found." in stdout:
        result["indicator_lookahead"] = PASS

    headers, rows = parse_rich_table(stdout, "Indicators")
    result["headers"], result["rows"] = headers, rows

    if not rows:
        if "No variance on indicator(s) found due to recursive formula." in stdout:
            result["verdict"] = PASS
            result["details"] = "aucune variance d'indicateur selon le warm-up"
        else:
            result["details"] = "tableau recursif introuvable dans la sortie - voir le log."
        return result

    worst = max(_worst_pct(r[1:]) for r in rows)
    result["worst_diff_pct"] = round(worst * 100.0, 6)
    drifting = sorted({r[0] for r in rows if r and r[0]})
    result["drifting_indicators"] = drifting
    result["verdict"] = FAIL if worst >= RECURSIVE_FAIL_PCT else WARN
    result["details"] = (
        f"{len(drifting)} indicateur(s) dependant du warm-up, ecart max "
        f"{result['worst_diff_pct']:.4f} % (seuil FAIL {RECURSIVE_FAIL_PCT:.3%}) : "
        f"{', '.join(drifting)}"
    )
    return result


def build_report(results: list[dict], args, stamp: str) -> str:
    lines = [
        f"# Check de biais ARIT — {stamp}",
        "",
        f"- strategie : `{STRATEGY}` · config : `{args.config}`",
        f"- timerange : `{args.timerange}`"
        + (f" · timeframe-detail : `{args.timeframe_detail}`" if args.timeframe_detail else ""),
        f"- paires : {', '.join(args.pairs) if args.pairs else 'whitelist de la config'}",
        "",
    ]
    for res in results:
        lines += [f"## {res['check']} — **{res['verdict']}**", "", res["details"] or "—", ""]
        if res["check"] == "lookahead-analysis" and res["rows"]:
            lines += [_fmt_table(res["headers"] or ["freqtrade"], res["rows"]), ""]
        if res["check"] == "recursive-analysis":
            lines.append(f"Look-ahead sur indicateurs seuls : **{res['indicator_lookahead']}**"
                         + (f" ({', '.join(res.get('indicator_lookahead_indicators', []))})"
                            if res.get("indicator_lookahead_indicators") else ""))
            lines.append("")
            if res["rows"]:
                lines += [_fmt_table(res["headers"], res["rows"]), ""]
    lines += [
        "## Lecture",
        "",
        "- `lookahead-analysis` FAIL = un signal passe change quand on ajoute du futur → "
        "interdit n.3 viole, corriger avant tout backtest de decision.",
        "- `recursive-analysis` WARN/FAIL = les indicateurs bougent selon le warm-up → "
        "`startup_candle_count` (aujourd'hui EMA_SLOW = 200) trop court : monter au plus petit "
        "warm-up ou l'ecart se stabilise.",
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Checks mecaniques look-ahead + warm-up (ARIT).")
    p.add_argument("--only", choices=("lookahead", "recursive", "both"), default="both")
    p.add_argument("--timerange", default=DEFAULT_TIMERANGE)
    p.add_argument("--config", type=Path, default=CONFIG)
    p.add_argument("--pairs", nargs="+", help="restreint aux paires données (defaut : whitelist)")
    p.add_argument("--targeted-trades", type=int, default=TARGETED_TRADES)
    p.add_argument("--minimum-trades", type=int, default=MINIMUM_TRADES)
    p.add_argument("--startup-candles", nargs="+", type=int, default=list(STARTUP_CANDLES))
    p.add_argument("--timeframe-detail", default=None,
                   help="ex. 5m — non applique par defaut (voir docstring)")
    args = p.parse_args(argv)
    if args.minimum_trades > args.targeted_trades:
        p.error("--minimum-trades ne peut pas depasser --targeted-trades")
    if not args.config.exists():
        p.error(f"config introuvable : {args.config}")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    results = []
    if args.only in ("lookahead", "both"):
        results.append(check_lookahead(args, stamp))
    if args.only in ("recursive", "both"):
        results.append(check_recursive(args, stamp))

    report_md = OUT_DIR / f"bias_{stamp}.md"
    report_md.write_text(build_report(results, args, stamp), encoding="utf-8")
    (OUT_DIR / f"bias_{stamp}.json").write_text(
        json.dumps({"stamp": stamp, "strategy": STRATEGY, "timerange": args.timerange,
                    "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    for res in results:
        log.info("%s : %s - %s", res["check"], res["verdict"], res["details"])
    log.info("rapport : %s", report_md)

    verdicts = [r["verdict"] for r in results]
    verdicts += [r["indicator_lookahead"] for r in results if "indicator_lookahead" in r]
    if FAIL in verdicts:
        return 1
    if UNKNOWN in verdicts:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
