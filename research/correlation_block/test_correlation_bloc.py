"""Tests du bloc correlation (PROPOSITION — hors suite principale).

Lancer :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe -m pytest research/correlation_block -q

Ces tests ne font PAS partie des ~200 tests du produit : le bloc n'est pas fusionne.
A deplacer dans tests/test_macro_regime.py au moment de la fusion (regle 7 arit_lib).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import macro_correlation_bloc as bloc  # noqa: E402

RNG = np.random.default_rng(20260730)


def _sessions(n: int, start: str = "2024-01-01") -> pd.DatetimeIndex:
    """n jours ouvres US (approximes par les jours de semaine)."""
    return pd.bdate_range(start, periods=n, tz="UTC")


# ------------------------------------------------------------------ c6 : cassure
def test_cassure_detectee_sous_le_plancher():
    idx = _sessions(30)
    spx = pd.Series(100.0, index=idx)
    spx.iloc[-1] = 90.0
    out = bloc.equity_structural_break(spx, window=20)
    assert out.iloc[-1]
    assert not out.iloc[-2]


def test_un_jour_n_est_pas_son_propre_plancher():
    """Serie stritement decroissante : sans shift(1), min() inclurait le jour meme
    et la cassure ne se declencherait jamais. C'est le test anti-tautologie."""
    idx = _sessions(30)
    spx = pd.Series(np.linspace(100, 70, 30), index=idx)
    out = bloc.equity_structural_break(spx, window=5)
    assert out.iloc[10:].all()


def test_pas_de_cassure_en_tendance_haussiere():
    idx = _sessions(40)
    spx = pd.Series(np.linspace(100, 130, 40), index=idx)
    assert not bloc.equity_structural_break(spx, window=20).any()


# --------------------------------------------------- c7 : le piege de la deflation
def _marche_simule(n_jours: int = 2000):
    """BTC 7/7 et SPX 5/7 pilotes par un facteur de risque latent quotidien.

    Le SPX etant ferme le week-end, sa seance du lundi price f(sam)+f(dim)+f(lun) :
    c'est ce desalignement de fenetre, autant que les rendements nuls, qui deflate
    un rho calcule sur calendrier."""
    cal = pd.date_range("2020-01-01", periods=n_jours, freq="D", tz="UTC")
    f = RNG.normal(0, 0.01, len(cal))
    btc = pd.Series(100 * np.exp(np.cumsum(0.8 * f + RNG.normal(0, 0.012, len(cal)))),
                    index=cal)

    is_bd = cal.dayofweek < 5
    r_spx = np.zeros(len(cal))
    accumule = 0.0
    for i in range(len(cal)):
        accumule += f[i]
        if is_bd[i]:
            r_spx[i] = 0.9 * accumule + RNG.normal(0, 0.006)
            accumule = 0.0
    spx = pd.Series(100 * np.exp(np.cumsum(r_spx)), index=cal)[is_bd]
    return btc, spx, cal


def test_rho_calendaire_est_deflate_vs_rho_sessions():
    """Justifie `btc_equity_correlation` : le rho calendaire vaut ~2/3 du vrai rho.

    Un couplage reel a 0,75 s'afficherait ~0,50, pile sur MACRO_CORR_ARM_ABOVE :
    le veto clignoterait ou ne s'armerait jamais."""
    btc, spx, cal = _marche_simule()

    rho_sessions = bloc.btc_equity_correlation(btc, spx, window=90).dropna()

    spx_ff = spx.reindex(cal).ffill()
    rho_calendaire = np.log(btc).diff().rolling(90).corr(np.log(spx_ff).diff()).dropna()

    ratio = rho_calendaire.mean() / rho_sessions.mean()
    assert ratio < 0.85, f"deflation attendue ~0,66 ; mesuree {ratio:.3f}"
    assert 0.55 < ratio, f"deflation invraisemblablement forte : {ratio:.3f}"


# ------------------------------------------------------------------ c7 : hysteresis
def test_hysteresis_garde_l_etat_dans_la_bande_morte():
    idx = _sessions(6)
    fast = pd.Series([0.60, 0.40, 0.35, 0.25, 0.35, 0.60], index=idx)
    slow = pd.Series(0.45, index=idx)
    etats = bloc.correlation_state(fast, slow)

    assert etats.iloc[0] == bloc.CORR_COUPLED
    assert etats.iloc[1] == bloc.CORR_COUPLED   # 0,40 : bande morte, on garde
    assert etats.iloc[2] == bloc.CORR_COUPLED   # 0,35 : idem
    assert etats.iloc[3] == bloc.CORR_DECOUPLED  # 0,25 < 0,30 : desarmement
    assert etats.iloc[4] == bloc.CORR_DECOUPLED  # 0,35 : bande morte, on garde
    assert etats.iloc[5] == bloc.CORR_COUPLED   # 0,60 : re-armement


def test_warmup_sans_etat_etabli_est_transition():
    idx = _sessions(3)
    fast = pd.Series([0.40, 0.45, 0.40], index=idx)
    slow = pd.Series(0.45, index=idx)
    assert (bloc.correlation_state(fast, slow) == bloc.CORR_TRANSITION).all()


def test_rho_long_bloque_un_armement_sur_pic_court():
    """rho court a 0,60 mais rho long a 0,10 : pic passager, pas de couplage."""
    idx = _sessions(3)
    fast = pd.Series([0.60, 0.60, 0.60], index=idx)
    slow = pd.Series([0.10, 0.10, 0.10], index=idx)
    assert (bloc.correlation_state(fast, slow) != bloc.CORR_COUPLED).all()


# ------------------------------------------------------------------- alignement 5/7
def test_fraicheur_traverse_un_week_end_mais_pas_un_pont():
    sessions = pd.DatetimeIndex(["2024-01-04", "2024-01-05"], tz="UTC")  # jeu, ven
    serie = pd.Series([1.0, 2.0], index=sessions)
    cal = pd.date_range("2024-01-04", "2024-01-11", freq="D", tz="UTC")
    out = bloc.align_to_calendar(serie, cal, stale_hours=120)

    assert out.loc["2024-01-07", "fresh"]       # dim, 48 h -> frais
    assert out.loc["2024-01-08", "fresh"]       # lun ferie, 72 h -> encore frais
    assert out.loc["2024-01-10", "fresh"]       # 120 h pile -> encore frais (borne <=)
    assert out.loc["2024-01-11", "fresh"] == False  # 144 h -> perime
    assert out.loc["2024-01-08", "value"] == 2.0    # derniere valeur portee

    # Avec la fenetre 48 h du reste du module, le lundi ferie serait deja stale :
    court = bloc.align_to_calendar(serie, cal, stale_hours=48)
    assert court.loc["2024-01-08", "fresh"] == False


# --------------------------------------------------------------------- decision
@pytest.mark.parametrize("args,attendu", [
    # (equity_break, corr_state, macro_regime, data_fresh) -> (bloque, raison)
    ((True, bloc.CORR_COUPLED, "NEUTRE", True), (True, bloc.EQUITY_VETO_BINDING)),
    ((True, bloc.CORR_COUPLED, "HOSTILE", True), (True, bloc.EQUITY_VETO_REDUNDANT)),
    ((True, bloc.CORR_DECOUPLED, "NEUTRE", True), (False, bloc.EQUITY_PASS_DECOUPLED)),
    ((True, bloc.CORR_TRANSITION, "NEUTRE", True), (False, bloc.EQUITY_PASS_DECOUPLED)),
    ((False, bloc.CORR_COUPLED, "NEUTRE", True), (False, bloc.EQUITY_PASS_NO_BREAK)),
    ((True, bloc.CORR_COUPLED, "NEUTRE", False), (False, bloc.EQUITY_PASS_STALE)),
])
def test_evaluate_branches(args, attendu):
    assert bloc.evaluate(*args) == attendu


def test_evaluate_rend_toujours_une_raison_non_vide():
    for eb in (True, False):
        for st in bloc.MACRO_CORR_STATES:
            for reg in ("PORTEUR", "NEUTRE", "HOSTILE"):
                for fresh in (True, False):
                    bloque, raison = bloc.evaluate(eb, st, reg, fresh)
                    assert isinstance(bloque, bool) and raison
