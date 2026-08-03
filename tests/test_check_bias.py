"""Tests de scripts/check_bias.py — parsing des sorties freqtrade et verdicts.

Aucun appel a freqtrade : `run_cli` est monkeypatche par des sorties CLI reelles (rich).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_bias", REPO / "scripts" / "check_bias.py")
check_bias = importlib.util.module_from_spec(_spec)
sys.modules["check_bias"] = check_bias
_spec.loader.exec_module(check_bias)


# Tableaux rich reels, colonnes resserrees pour tenir en 100 colonnes (gate ruff E501).
LOOKAHEAD_TABLE_CLEAN = """
                            Lookahead Analysis
┌───────────┬──────────┬──────────┬───────────────┬───────┬──────┬───────────────────┐
│  filename │ strategy │ has_bias │ total_signals │ entry │ exit │ biased_indicators │
├───────────┼──────────┼──────────┼───────────────┼───────┼──────┼───────────────────┤
│ AritV1.py │   AritV1 │       No │           183 │     0 │    0 │                   │
└───────────┴──────────┴──────────┴───────────────┴───────┴──────┴───────────────────┘
"""

# Colonne « 200 (from strategy) » : freqtrade ajoute d'office le compte de la strategie.
RECURSIVE_TABLE = """
                       Recursive Analysis
┌────────────┬──────────┬──────────────────────┬──────────┬───────┐
│ Indicators │      199 │  200 (from strategy) │      499 │  1999 │
├────────────┼──────────┼──────────────────────┼──────────┼───────┤
│     ema200 │  0.412%  │               0.390% │   0.004% │     - │
│       atr  │    nan%  │                    - │        - │     - │
└────────────┴──────────┴──────────────────────┴──────────┴───────┘
"""


CONFIG = str(REPO / "user_data" / "config.dry.json")


def _args(tmp_path=None, **over):
    args = check_bias.parse_args(["--timerange", "20230101-20240101", "--config", CONFIG])
    for key, value in over.items():
        setattr(args, key, value)
    return args


# ---------------------------------------------------------------- parse_rich_table

def test_parse_rich_table_lookahead():
    headers, rows = check_bias.parse_rich_table(LOOKAHEAD_TABLE_CLEAN, "has_bias")
    assert headers[:3] == ["filename", "strategy", "has_bias"]
    assert rows == [["AritV1.py", "AritV1", "No", "183", "0", "0", ""]]


def test_parse_rich_table_recursive():
    """Les en-tetes viennent de la sortie : la colonne ajoutee par freqtrade est conservee."""
    headers, rows = check_bias.parse_rich_table(RECURSIVE_TABLE, "Indicators")
    assert headers == ["Indicators", "199", "200 (from strategy)", "499", "1999"]
    assert [r[0] for r in rows] == ["ema200", "atr"]
    assert rows[0][1:] == ["0.412%", "0.390%", "0.004%", "-"]


def test_parse_rich_table_absent():
    assert check_bias.parse_rich_table("aucun tableau ici\n", "Indicators") == ([], [])


def test_parse_rich_table_recolle_les_cellules_repliees():
    """Repli rich : 1re cellule vide => suite de la ligne precedente (ex. liste d'indicateurs)."""
    wrapped = (
        "│ filename  │ strategy │ has_bias │ biased_indicators │\n"
        "│ AritV1.py │ AritV1   │ Yes      │ pivot_high,       │\n"
        "│           │          │          │ s_trend           │\n"
    )
    _, rows = check_bias.parse_rich_table(wrapped, "has_bias")
    assert rows == [["AritV1.py", "AritV1", "Yes", "pivot_high, s_trend"]]


# ---------------------------------------------------------------- _worst_pct

@pytest.mark.parametrize("cells,expected", [
    (["0.412%", "0.004%", "-"], pytest.approx(0.00412)),
    (["-", "-"], 0.0),
    (["nan%", "-"], 0.0),                       # nan = derive non chiffrable, pas un ecart
    (["-0.5%", "0.1%"], pytest.approx(0.005)),  # valeur absolue
])
def test_worst_pct(cells, expected):
    assert check_bias._worst_pct(cells) == expected


# ---------------------------------------------------------------- check_lookahead

def test_lookahead_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    csv_path = tmp_path / "lookahead_STAMP.csv"

    def fake_run(cli, log_path):
        csv_path.write_text(
            "filename,strategy,has_bias,total_signals,biased_entry_signals,"
            "biased_exit_signals,biased_indicators\n"
            "AritV1.py,AritV1,False,183,0,0,\n", encoding="utf-8")
        return 0, LOOKAHEAD_TABLE_CLEAN

    monkeypatch.setattr(check_bias, "run_cli", fake_run)
    res = check_bias.check_lookahead(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.PASS
    assert res["total_signals"] == 183
    assert res["biased_indicators"] == []


def test_lookahead_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    csv_path = tmp_path / "lookahead_STAMP.csv"

    def fake_run(cli, log_path):
        csv_path.write_text(
            "filename,strategy,has_bias,total_signals,biased_entry_signals,"
            "biased_exit_signals,biased_indicators\n"
            "AritV1.py,AritV1,True,183,12,3,\"pivot_high,s_trend\"\n", encoding="utf-8")
        return 0, LOOKAHEAD_TABLE_CLEAN

    monkeypatch.setattr(check_bias, "run_cli", fake_run)
    res = check_bias.check_lookahead(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.FAIL
    assert res["biased_indicators"] == ["pivot_high", "s_trend"]
    assert res["biased_entry_signals"] == 12


LOOKAHEAD_TABLE_TOO_FEW = """
                                 Lookahead Analysis
┌───────────┬──────────┬───────────────────────────────────────────┬───────────────┐
│  filename │ strategy │                                  has_bias │ total_signals │
├───────────┼──────────┼───────────────────────────────────────────┼───────────────┤
│ AritV1.py │   AritV1 │ too few trades caught (0/20).Test failed. │               │
└───────────┴──────────┴───────────────────────────────────────────┴───────────────┘
"""


def test_lookahead_indetermine_csv_vide(tmp_path, monkeypatch):
    """Trop peu de signaux : CSV sans ligne -> INDETERMINE, jamais PASS, avec la raison."""
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)

    def fake_run(cli, log_path):
        (tmp_path / "lookahead_STAMP.csv").write_text(
            "filename,strategy,has_bias,total_signals,biased_entry_signals,"
            "biased_exit_signals,biased_indicators\n", encoding="utf-8")
        return 0, LOOKAHEAD_TABLE_TOO_FEW

    monkeypatch.setattr(check_bias, "run_cli", fake_run)
    res = check_bias.check_lookahead(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.UNKNOWN
    assert "too few trades caught (0/20)" in res["details"]


def test_lookahead_indetermine_sans_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, "erreur inattendue"))
    res = check_bias.check_lookahead(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.UNKNOWN


def test_recursive_remonte_une_erreur_a_code_0(tmp_path, monkeypatch):
    """Plafond de warm-up : freqtrade log l'erreur mais sort en 0 — la raison doit remonter."""
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    stdout = ("2026-07-31 15:41:24,501 - freqtrade - ERROR - Configuration error: This strategy "
              "requires 6400 candles to start, which is more than 5x (4999 candles) the amount "
              "of candles Binance provides for 1h.\n")
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, stdout))
    res = check_bias.check_recursive(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.UNKNOWN
    assert "5x (4999 candles)" in res["details"]


def test_lookahead_indetermine_si_freqtrade_echoue(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (2, "OperationalException"))
    res = check_bias.check_lookahead(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.UNKNOWN


def test_lookahead_transmet_les_options(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    seen = {}

    def fake_run(cli, log_path):
        seen["cli"] = cli
        return 2, ""

    monkeypatch.setattr(check_bias, "run_cli", fake_run)
    check_bias.check_lookahead(_args(tmp_path, timeframe_detail="5m", pairs=["BTC/USDT"]), "STAMP")
    cli = seen["cli"]
    assert cli[0] == "lookahead-analysis"
    assert "--timeframe-detail" in cli and "5m" in cli
    assert cli[cli.index("-p") + 1] == "BTC/USDT"
    assert str(check_bias.TARGETED_TRADES) in cli


# ---------------------------------------------------------------- check_recursive

def test_recursive_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    stdout = ("No variance on indicator(s) found due to recursive formula.\n"
              "No lookahead bias on indicators found.\n")
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, stdout))
    res = check_bias.check_recursive(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.PASS
    assert res["indicator_lookahead"] == check_bias.PASS


def test_recursive_fail_au_dessus_du_seuil(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, RECURSIVE_TABLE))
    res = check_bias.check_recursive(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.FAIL          # 0,412 % >= seuil 0,1 %
    assert res["drifting_indicators"] == ["atr", "ema200"]
    assert res["worst_diff_pct"] == pytest.approx(0.412)
    assert "200 (from strategy)" in res["headers"]    # colonne ajoutee par freqtrade conservee

    report = check_bias.build_report([res], _args(tmp_path), "STAMP")
    assert "| Indicators | 199 | 200 (from strategy) | 499 | 1999 |" in report
    assert "| ema200 | 0.412% | 0.390% | 0.004% | - |" in report


def test_recursive_warn_sous_le_seuil(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    table = RECURSIVE_TABLE.replace("0.412%", "0.004%").replace("0.390%", "0.001%")
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, table))
    res = check_bias.check_recursive(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.WARN


def test_recursive_detecte_lookahead_indicateur(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    stdout = ("No variance on indicator(s) found due to recursive formula.\n"
              "=> found lookahead in indicator pivot_high\n"
              "=> found lookahead in indicator pivot_high\n")
    monkeypatch.setattr(check_bias, "run_cli", lambda cli, log: (0, stdout))
    res = check_bias.check_recursive(_args(tmp_path), "STAMP")
    assert res["verdict"] == check_bias.PASS
    assert res["indicator_lookahead"] == check_bias.FAIL
    assert res["indicator_lookahead_indicators"] == ["pivot_high"]


def test_recursive_startup_candles_transmis(tmp_path, monkeypatch):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    seen = {}
    monkeypatch.setattr(check_bias, "run_cli",
                        lambda cli, log: (seen.update(cli=cli), (0, ""))[1])
    check_bias.check_recursive(_args(tmp_path, startup_candles=[199, 499, 999, 1999]), "STAMP")
    cli = seen["cli"]
    idx = cli.index("--startup-candle")
    assert cli[idx + 1: idx + 5] == ["199", "499", "999", "1999"]


# ---------------------------------------------------------------- main / codes de sortie

def _main_with(monkeypatch, tmp_path, lookahead, recursive):
    monkeypatch.setattr(check_bias, "OUT_DIR", tmp_path)
    monkeypatch.setattr(check_bias, "check_lookahead", lambda a, s: lookahead)
    monkeypatch.setattr(check_bias, "check_recursive", lambda a, s: recursive)
    return check_bias.main(["--config", CONFIG])


def _res(check, verdict, **extra):
    return {"check": check, "verdict": verdict, "details": "", "rows": [], "headers": [], **extra}


def test_main_code_0_si_tout_pass(tmp_path, monkeypatch):
    code = _main_with(monkeypatch, tmp_path,
                      _res("lookahead-analysis", check_bias.PASS),
                      _res("recursive-analysis", check_bias.PASS,
                           indicator_lookahead=check_bias.PASS))
    assert code == 0
    assert list(tmp_path.glob("bias_*.md")) and list(tmp_path.glob("bias_*.json"))


def test_main_code_1_si_un_fail(tmp_path, monkeypatch):
    code = _main_with(monkeypatch, tmp_path,
                      _res("lookahead-analysis", check_bias.FAIL),
                      _res("recursive-analysis", check_bias.PASS,
                           indicator_lookahead=check_bias.PASS))
    assert code == 1


def test_main_code_1_si_lookahead_indicateur_seul_fail(tmp_path, monkeypatch):
    code = _main_with(monkeypatch, tmp_path,
                      _res("lookahead-analysis", check_bias.PASS),
                      _res("recursive-analysis", check_bias.PASS,
                           indicator_lookahead=check_bias.FAIL))
    assert code == 1


def test_main_code_2_si_indetermine(tmp_path, monkeypatch):
    code = _main_with(monkeypatch, tmp_path,
                      _res("lookahead-analysis", check_bias.UNKNOWN),
                      _res("recursive-analysis", check_bias.PASS,
                           indicator_lookahead=check_bias.PASS))
    assert code == 2


def test_main_warn_ne_fait_pas_echouer(tmp_path, monkeypatch):
    code = _main_with(monkeypatch, tmp_path,
                      _res("lookahead-analysis", check_bias.PASS),
                      _res("recursive-analysis", check_bias.WARN,
                           indicator_lookahead=check_bias.PASS))
    assert code == 0


# ---------------------------------------------------------------- parse_args

def test_parse_args_refuse_minimum_superieur_a_targeted():
    with pytest.raises(SystemExit):
        check_bias.parse_args(["--minimum-trades", "500", "--targeted-trades", "200"])


def test_parse_args_refuse_config_absente(tmp_path):
    with pytest.raises(SystemExit):
        check_bias.parse_args(["--config", str(tmp_path / "absent.json")])


def test_parse_args_defauts():
    args = check_bias.parse_args([])
    assert args.only == "both"
    assert args.timerange == check_bias.DEFAULT_TIMERANGE
    assert args.startup_candles == list(check_bias.STARTUP_CANDLES)
    assert args.timeframe_detail is None      # non applique par defaut (voir docstring)
