"""Tests du lanceur start_arit.py — garde-fou anti-doublon de la relance automatique.

Le lanceur est declenche a l'ouverture de session pour survivre aux redemarrages Windows
Update pendant une absence longue. Ces tests verrouillent la seule logique qu'il porte :
ne PAS lancer un second freqtrade sur la meme config (deux bots ecrivant le meme journal
et la meme base rendraient les donnees du dry-run inexploitables). Aucun process n'est
demarre ici : subprocess est monkeypatche.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import start_arit  # noqa: E402


def _venv_ok(monkeypatch):
    """PYTHON est un Path : ses methodes sont en lecture seule, on remplace l'attribut."""
    monkeypatch.setattr(start_arit, "PYTHON",
                        type("P", (), {"exists": staticmethod(lambda: True)})())


def _tasklist(monkeypatch, stdout):
    def _run(*a, **k):
        return subprocess.CompletedProcess(a, 0, stdout=stdout, stderr="")
    monkeypatch.setattr(start_arit.subprocess, "run", _run)


def test_deja_lance_detecte_un_bot_en_cours(monkeypatch):
    _tasklist(monkeypatch, "freqtrade.exe   12345 Console   1   180 000 Ko")
    assert start_arit.deja_lance() is True


def test_deja_lance_faux_quand_aucun_process(monkeypatch):
    # Message reel de tasklist quand le filtre ne matche rien.
    _tasklist(monkeypatch, "INFORMATION: Aucune tache en cours avec les criteres specifies.")
    assert start_arit.deja_lance() is False


@pytest.mark.parametrize("exc", [OSError("introuvable"), subprocess.TimeoutExpired("t", 1)])
def test_deja_lance_faux_si_tasklist_indisponible(monkeypatch, exc):
    """En cas de doute on repond False : ne PAS relancer un bot mort coute bien plus cher
    qu'un doublon improbable."""
    def _boom(*a, **k):
        raise exc
    monkeypatch.setattr(start_arit.subprocess, "run", _boom)
    assert start_arit.deja_lance() is False


def test_si_absent_ne_lance_rien_quand_le_bot_tourne(monkeypatch, capsys):
    monkeypatch.setattr(start_arit, "deja_lance", lambda *a, **k: True)
    monkeypatch.setattr(start_arit.sys, "argv", ["start_arit.py", "--si-absent"])
    lances = []
    monkeypatch.setattr(start_arit, "launch", lambda t, c: lances.append(t))
    _venv_ok(monkeypatch)
    start_arit.main()
    assert lances == []
    assert "rien a relancer" in capsys.readouterr().out


def test_si_absent_lance_tout_quand_le_bot_est_mort(monkeypatch):
    monkeypatch.setattr(start_arit, "deja_lance", lambda *a, **k: False)
    monkeypatch.setattr(start_arit.sys, "argv", ["start_arit.py", "--si-absent"])
    lances = []
    monkeypatch.setattr(start_arit, "launch", lambda t, c: lances.append(t))
    _venv_ok(monkeypatch)
    monkeypatch.setattr(start_arit, "bot_command", lambda: ["freqtrade"])
    start_arit.main()
    assert len(lances) == len(start_arit.SERVICES) + 1      # 3 services + le bot


def test_sans_le_flag_le_lancement_manuel_est_inchange(monkeypatch):
    """Retrocompat : sans --si-absent, on lance meme si un bot tourne (choix explicite)."""
    monkeypatch.setattr(start_arit, "deja_lance", lambda *a, **k: True)
    monkeypatch.setattr(start_arit.sys, "argv", ["start_arit.py"])
    lances = []
    monkeypatch.setattr(start_arit, "launch", lambda t, c: lances.append(t))
    _venv_ok(monkeypatch)
    monkeypatch.setattr(start_arit, "bot_command", lambda: ["freqtrade"])
    start_arit.main()
    assert len(lances) == len(start_arit.SERVICES) + 1
