"""Tests de la config DEPLOYEE (user_data/config.dry.json).

Aucun test ne validait ce fichier — c'est ainsi qu'un dry-run lance le 2026-08-07 est
reste en etat STOPPED sans que rien ne le signale : freqtrade demarre en `stopped` par
defaut, et `initial_state` etait absent. Le bot chargeait la strategie, synchronisait les
wallets, resolvait les 4 paires... puis ne faisait rien. Sans FreqUI ni API REST, rien ne
pouvait le demarrer : il serait reste fige toute l'absence.

Ces tests verrouillent les invariants de DEPLOIEMENT, pas la logique metier.
"""

import json
from pathlib import Path

import pytest

CONFIG = Path(__file__).resolve().parents[1] / "user_data" / "config.dry.json"


@pytest.fixture(scope="module")
def cfg():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_dry_run_est_vrai(cfg):
    """Interdit n7 de docs/README : jamais de capital reel sans decision explicite."""
    assert cfg["dry_run"] is True


def test_initial_state_running(cfg):
    """LE bug du 07/08 : sans cette clef, freqtrade demarre STOPPED et n'evalue RIEN.
    Le defaut de freqtrade est `stopped` — l'omission ne produit aucune erreur, juste un
    bot inerte qui a l'air sain dans ses logs."""
    assert cfg.get("initial_state") == "running"


def test_logfile_configure(cfg):
    """Un run non surveille sans journal est indiagnosticable a posteriori."""
    assert cfg.get("logfile"), "aucun logfile : impossible de diagnostiquer une panne"


def test_futures_et_paires_attendues(cfg):
    """A2 : le bot est long ET short depuis le 04/08 => futures, paires perpetuelles."""
    assert cfg["trading_mode"] == "futures"
    assert cfg["margin_mode"] == "isolated"
    assert all(p.endswith(":USDT") for p in cfg["exchange"]["pair_whitelist"])


def test_aucune_clef_api_en_dur(cfg):
    """Les clefs viennent de l'environnement, jamais du fichier versionne."""
    assert not cfg["exchange"].get("key")
    assert not cfg["exchange"].get("secret")
