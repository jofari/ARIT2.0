"""Tests Macro Analyst V1.1 — macro_regime (docs/06 §6.2, docs/04 §4.1-4.2).

Regles de score, bords des seuils, fail-safe stale, decalage +1 jour et
anti-look-ahead sur donnees SYNTHETIQUES ; un test d'integration sur les VRAIS
fichiers de user_data/data/macro/.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from arit_lib import contracts, macro_regime, params

KEYS = list(contracts.MACRO_SCORE_KEYS)
RCOL = contracts.MACRO_REGIME_COL
PORTEUR, NEUTRE, HOSTILE = params.MACRO_REGIMES


def _hist(n=90, start="2020-01-01", **overrides):
    """DataFrame daily UTC, colonnes MACRO_SCORE_KEYS neutres (score 0) sauf overrides."""
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    base = {
        "dxy": np.full(n, 100.0),
        "taux": np.full(n, 2.0),
        "stablecoins": np.full(n, 1e11),
        "funding": np.full(n, 0.0002),   # 0 < f <= HOT => 0
        "fear_greed": np.full(n, 35.0),  # 25 <= fg < 45 => 0
    }
    base.update(overrides)
    return pd.DataFrame(base, index=idx)


def _step(n, start_idx, value, base):
    arr = np.full(n, base, dtype="float64")
    arr[start_idx:] = value
    return arr


# ------------------------------------------------------------------ baseline neutre
def test_neutral_history_gives_all_zero_and_neutre():
    out = macro_regime.daily_regimes(_hist())
    assert list(out.columns) == KEYS + [RCOL]
    assert (out[KEYS].iloc[70] == 0).all()
    assert out[RCOL].iloc[70] == NEUTRE


# ------------------------------------------------------------------ regle par composant
@pytest.mark.parametrize("value, expected", [(99.0, 1), (101.0, -1)])
def test_score_dxy(value, expected):
    out = macro_regime.daily_regimes(_hist(dxy=_step(90, 40, value, 100.0)))
    assert out["dxy"].iloc[45] == expected


@pytest.mark.parametrize("value, expected", [(1.85, 1), (2.15, -1)])
def test_score_taux(value, expected):
    out = macro_regime.daily_regimes(_hist(taux=_step(90, 60, value, 2.0)))
    assert out["taux"].iloc[70] == expected


@pytest.mark.parametrize("mult, expected", [(1.03, 1), (0.98, -1)])
def test_score_stablecoins(mult, expected):
    out = macro_regime.daily_regimes(_hist(stablecoins=_step(90, 30, 1e11 * mult, 1e11)))
    assert out["stablecoins"].iloc[40] == expected


@pytest.mark.parametrize("value, expected", [(0.001, -1), (-0.0002, 1)])
def test_score_funding(value, expected):
    out = macro_regime.daily_regimes(_hist(funding=_step(90, 10, value, 0.0002)))
    assert out["funding"].iloc[20] == expected


@pytest.mark.parametrize("value, expected", [(20.0, -1), (50.0, 1)])
def test_score_fear_greed(value, expected):
    out = macro_regime.daily_regimes(_hist(fear_greed=_step(90, 20, value, 35.0)))
    assert out["fear_greed"].iloc[25] == expected


# ------------------------------------------------------------------ bords des seuils
@pytest.mark.parametrize("value, expected", [
    (99.4, 1),   # -0,6 % : juste sous -0,5 % => +1
    (99.6, 0),   # -0,4 % : au-dessus du seuil => 0
    (100.6, -1),  # +0,6 % => -1
    (100.4, 0),  # +0,4 % => 0
])
def test_dxy_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(dxy=_step(90, 40, value, 100.0)))
    assert out["dxy"].iloc[45] == expected


@pytest.mark.parametrize("value, expected", [
    (24.0, -1), (25.0, 0),   # < 25 strict
    (44.0, 0), (45.0, 1),    # >= 45
])
def test_fear_greed_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(fear_greed=_step(90, 20, value, 35.0)))
    assert out["fear_greed"].iloc[25] == expected


@pytest.mark.parametrize("value, expected", [
    (params.MACRO_FUNDING_HOT, 0),        # == HOT : pas > => 0
    (params.MACRO_FUNDING_HOT + 1e-4, -1),
    (0.0, 0),                             # == 0 : pas < 0 => 0
    (-1e-4, 1),
])
def test_funding_threshold_edges(value, expected):
    out = macro_regime.daily_regimes(_hist(funding=np.full(90, value)))
    assert out["funding"].iloc[70] == expected


# ------------------------------------------------------------------ agregation regime
def test_regime_porteur_and_hostile():
    # fenetres dxy (20 j) et taux (60 j) calees pour co-activer au jour 75.
    # dxy -1 % (+1) ET taux -0,15 (+1) => somme +2 => PORTEUR
    h = _hist(dxy=_step(90, 65, 99.0, 100.0), taux=_step(90, 40, 1.85, 2.0))
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[76] == PORTEUR
    # dxy +1 % (-1) ET taux +0,15 (-1) => somme -2 => HOSTILE
    h2 = _hist(dxy=_step(90, 65, 101.0, 100.0), taux=_step(90, 40, 2.15, 2.0))
    out2 = macro_regime.daily_regimes(h2)
    assert out2[RCOL].iloc[76] == HOSTILE


# ------------------------------------------------------------------ fail-safe stale
def test_failsafe_three_stale_components_hostile():
    h = _hist(n=90)
    for col in ("dxy", "taux", "stablecoins"):
        arr = h[col].to_numpy().copy()
        arr[50:] = np.nan          # 3 series demarrees puis coupees > 48 h
        h[col] = arr
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[80] == HOSTILE


def test_before_any_series_started_is_neutre_not_hostile():
    h = _hist(n=40)
    for col in KEYS:
        arr = h[col].to_numpy().copy()
        arr[:6] = np.nan           # aucune serie n'a encore commence
        h[col] = arr
    out = macro_regime.daily_regimes(h)
    assert out[RCOL].iloc[3] == NEUTRE  # 5 composants "sans donnee" mais debut d'historique


# ------------------------------------------------------------------ point-in-time +1 jour
def test_shift_plus_one_day():
    h = _hist(n=60, fear_greed=_step(60, 30, 20.0, 35.0))
    out = macro_regime.daily_regimes(h)
    assert out["fear_greed"].iloc[30] == 0    # J = jour de la bascule : reflete J-1 (35)
    assert out["fear_greed"].iloc[31] == -1   # J+1 : reflete la bascule du jour 30


# ------------------------------------------------------------------ anti-look-ahead
def test_modifying_last_value_never_changes_past_regimes():
    h = _hist(n=60, dxy=_step(60, 30, 98.0, 100.0))
    out1 = macro_regime.daily_regimes(h)

    h2 = h.copy()
    h2.iloc[-1, h2.columns.get_loc("dxy")] = 500.0
    out2 = macro_regime.daily_regimes(h2)
    pd.testing.assert_frame_equal(out1, out2)  # derniere valeur => aucun impact

    h3 = h.copy()
    h3.iloc[-2:, h3.columns.get_loc("fear_greed")] = 5.0
    out3 = macro_regime.daily_regimes(h3)
    pd.testing.assert_frame_equal(out1.iloc[:-2], out3.iloc[:-2])


# ------------------------------------------------------------------ regime_now (live)
def test_regime_now_empty_is_hostile():
    assert macro_regime.regime_now({}) == (HOSTILE, {})
    assert macro_regime.regime_now(None) == (HOSTILE, {})


def test_regime_now_aggregates_scores():
    porteur = {"dxy": 1, "taux": 1, "stablecoins": 1, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(porteur)[0] == PORTEUR
    hostile = {"dxy": -1, "taux": -1, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(hostile)[0] == HOSTILE
    neutre = {"dxy": 1, "taux": 0, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    assert macro_regime.regime_now(neutre)[0] == NEUTRE


def test_regime_now_stale_or_missing_is_hostile():
    stale = {"dxy": 1, "taux": 1, "stablecoins": 1, "funding": 1, "fear_greed": 1,
             "stale": True}
    assert macro_regime.regime_now(stale)[0] == HOSTILE
    missing = {"dxy": 1, "taux": 1}  # 3 scores absents => fail-safe
    assert macro_regime.regime_now(missing)[0] == HOSTILE


# ------------------------------------------- parite live A2 (2026-08-07)
SCORES_KEY = contracts.MACRO_SCORES_KEY


def _state(scores, **extra):
    return {"fear_greed": 50, "stale": False, SCORES_KEY: scores, **extra}


def test_regime_from_state_ne_melange_pas_les_deux_schemas():
    """Garde-fou anti-collision : `fear_greed` = indice BRUT 0-100 au premier niveau (06.3),
    score {-1,0,1} dans le sous-objet (06.2). A plat, un F&G de 50 serait somme comme +50 et
    rendrait PORTEUR quelle que soit la macro reelle — le pire biais long possible."""
    hostile = {"dxy": -1, "taux": -1, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    regime, scores = macro_regime.regime_from_state(_state(hostile))
    assert regime == HOSTILE            # -2, et surtout PAS +48
    assert scores["fear_greed"] == 0    # le score, jamais l'indice brut


def test_regime_from_state_propage_le_stale():
    porteur = {"dxy": 1, "taux": 1, "stablecoins": 1, "funding": 1, "fear_greed": 1}
    assert macro_regime.regime_from_state(_state(porteur))[0] == PORTEUR
    assert macro_regime.regime_from_state(_state(porteur, stale=True))[0] == HOSTILE


@pytest.mark.parametrize("state", [None, {}, {"fear_greed": 50}, _state({}), _state(None)])
def test_regime_from_state_sans_scores_est_hostile(state):
    """Sous-objet absent, vide ou nul => aucun score => HOSTILE (jamais NEUTRE, qui
    autoriserait long ET short sur une absence de donnee)."""
    assert macro_regime.regime_from_state(state)[0] == HOSTILE


def test_attach_regime_now_pose_une_colonne_scalaire():
    """Pendant live de attach_macro_regime : le live n'a qu'un etat courant, donc le regime
    est CONSTANT sur tout le df (le backtest, lui, joint un regime par jour)."""
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    porteur = {"dxy": 1, "taux": 1, "stablecoins": 0, "funding": 0, "fear_greed": 0}
    out = macro_regime.attach_regime_now(df, _state(porteur))
    assert list(out[RCOL]) == [PORTEUR] * 3


# ------------------------------------------------------------------ integration reels
def _macro_dir():
    return Path(__file__).resolve().parents[1] / "user_data" / "data" / "macro"


@pytest.mark.skipif(not _macro_dir().exists(), reason="donnees macro absentes")
def test_integration_real_files():
    hist = macro_regime.load_history(_macro_dir())
    assert not hist.empty
    assert isinstance(hist.index, pd.DatetimeIndex)
    assert str(hist.index.tz) == "UTC"
    assert (hist.index == hist.index.normalize()).all()
    assert set(hist.columns) <= set(KEYS)

    regs = macro_regime.daily_regimes(hist)
    assert set(regs[RCOL].unique()) <= set(params.MACRO_REGIMES)
    assert set(np.unique(regs[KEYS].to_numpy())) <= {-1, 0, 1}
    # plage 2018+ couverte
    assert pd.Timestamp("2018-06-01", tz="UTC") in regs.index
    assert pd.Timestamp("2025-06-01", tz="UTC") in regs.index


# ==================================================== 06.2.1 bloc correlation actions (c6/c7)
# Portes depuis research/correlation_block/ a la fusion du 2026-08-03 (A4), regle 7 arit_lib.
RNG = np.random.default_rng(20260730)
COUPLE, TRANSITION, DECOUPLE = params.MACRO_CORR_STATES


def _sessions(n, start="2024-01-01"):
    """n jours ouvres US (approximes par les jours de semaine)."""
    return pd.bdate_range(start, periods=n, tz="UTC")


# ------------------------------------------------------------------------ c6 : cassure
def test_cassure_detectee_sous_le_plancher():
    idx = _sessions(30)
    eq = pd.Series(100.0, index=idx)
    eq.iloc[-1] = 90.0
    out = macro_regime.equity_structural_break(eq, window=20)
    assert out.iloc[-1]
    assert not out.iloc[-2]


def test_un_jour_n_est_pas_son_propre_plancher():
    """Serie strictement decroissante : sans shift(1), min() inclurait le jour meme et la
    cassure ne se declencherait jamais. C'est le test anti-tautologie."""
    idx = _sessions(30)
    eq = pd.Series(np.linspace(100, 70, 30), index=idx)
    assert macro_regime.equity_structural_break(eq, window=5).iloc[10:].all()


def test_pas_de_cassure_en_tendance_haussiere():
    idx = _sessions(40)
    eq = pd.Series(np.linspace(100, 130, 40), index=idx)
    assert not macro_regime.equity_structural_break(eq, window=20).any()


# --------------------------------------------------- c7 : le piege de la deflation de rho
def _marche_simule(n_jours=2000):
    """BTC 7/7 et indice 5/7 pilotes par un facteur de risque latent quotidien.

    L'indice etant ferme le week-end, sa seance du lundi price f(sam)+f(dim)+f(lun) : c'est ce
    desalignement de fenetre, autant que les rendements nuls, qui deflate un rho calendaire."""
    cal = pd.date_range("2020-01-01", periods=n_jours, freq="D", tz="UTC")
    f = RNG.normal(0, 0.01, len(cal))
    btc = pd.Series(100 * np.exp(np.cumsum(0.8 * f + RNG.normal(0, 0.012, len(cal)))), index=cal)

    is_bd = cal.dayofweek < 5
    r_eq = np.zeros(len(cal))
    accumule = 0.0
    for i in range(len(cal)):
        accumule += f[i]
        if is_bd[i]:
            r_eq[i] = 0.9 * accumule + RNG.normal(0, 0.006)
            accumule = 0.0
    eq = pd.Series(100 * np.exp(np.cumsum(r_eq)), index=cal)[is_bd]
    return btc, eq, cal


def test_rho_calendaire_est_deflate_vs_rho_sessions():
    """Justifie btc_equity_correlation : le rho calendaire vaut ~2/3 du vrai rho. Un couplage
    reel a 0,75 s'afficherait ~0,50, pile sur MACRO_CORR_ARM_ABOVE — le veto clignoterait."""
    btc, eq, cal = _marche_simule()
    rho_sessions = macro_regime.btc_equity_correlation(btc, eq, window=90).dropna()

    eq_ff = eq.reindex(cal).ffill()
    rho_calendaire = np.log(btc).diff().rolling(90).corr(np.log(eq_ff).diff()).dropna()

    ratio = rho_calendaire.mean() / rho_sessions.mean()
    assert ratio < 0.85, f"deflation attendue ~0,66 ; mesuree {ratio:.3f}"
    assert 0.55 < ratio, f"deflation invraisemblablement forte : {ratio:.3f}"


# ---------------------------------------------------------------------- c7 : hysteresis
def test_hysteresis_garde_l_etat_dans_la_bande_morte():
    idx = _sessions(6)
    fast = pd.Series([0.60, 0.40, 0.35, 0.25, 0.35, 0.60], index=idx)
    slow = pd.Series(0.45, index=idx)
    etats = macro_regime.correlation_state(fast, slow)

    assert etats.iloc[0] == COUPLE
    assert etats.iloc[1] == COUPLE     # 0,40 : bande morte, on garde
    assert etats.iloc[2] == COUPLE     # 0,35 : idem
    assert etats.iloc[3] == DECOUPLE   # 0,25 < 0,30 : desarmement
    assert etats.iloc[4] == DECOUPLE   # 0,35 : bande morte, on garde
    assert etats.iloc[5] == COUPLE     # 0,60 : re-armement


def test_warmup_sans_etat_etabli_est_transition():
    idx = _sessions(3)
    fast = pd.Series([0.40, 0.45, 0.40], index=idx)
    slow = pd.Series(0.45, index=idx)
    assert (macro_regime.correlation_state(fast, slow) == TRANSITION).all()


def test_rho_long_bloque_un_armement_sur_pic_court():
    """rho court a 0,60 mais rho long a 0,10 : pic passager, pas de couplage."""
    idx = _sessions(3)
    fast = pd.Series([0.60, 0.60, 0.60], index=idx)
    slow = pd.Series([0.10, 0.10, 0.10], index=idx)
    assert (macro_regime.correlation_state(fast, slow) != COUPLE).all()


# --------------------------------------------------------------------- alignement 5/7
def test_fraicheur_traverse_un_week_end_mais_pas_un_pont():
    sessions = pd.DatetimeIndex(["2024-01-04", "2024-01-05"], tz="UTC")  # jeu, ven
    serie = pd.Series([1.0, 2.0], index=sessions)
    cal = pd.date_range("2024-01-04", "2024-01-11", freq="D", tz="UTC")
    out = macro_regime._align_to_calendar(serie, cal, stale_hours=120)

    assert out.loc["2024-01-07", "fresh"]           # dim, 48 h -> frais
    assert out.loc["2024-01-08", "fresh"]           # lun ferie, 72 h -> encore frais
    assert out.loc["2024-01-10", "fresh"]           # 120 h pile -> frais (borne <=)
    assert not out.loc["2024-01-11", "fresh"]       # 144 h -> perime
    assert out.loc["2024-01-08", "value"] == 2.0    # derniere valeur portee

    court = macro_regime._align_to_calendar(serie, cal, stale_hours=48)
    assert not court.loc["2024-01-08", "fresh"]     # avec 48 h, le lundi ferie est deja stale


def test_avant_la_premiere_session_rien_n_est_demarre():
    sessions = pd.DatetimeIndex(["2024-01-10"], tz="UTC")
    serie = pd.Series([1.0], index=sessions)
    cal = pd.date_range("2024-01-05", "2024-01-11", freq="D", tz="UTC")
    out = macro_regime._align_to_calendar(serie, cal)
    assert not out.loc["2024-01-05", "started"]
    assert out.loc["2024-01-10", "started"]


# ------------------------------------------------------------------- decision c6+c7
@pytest.mark.parametrize("args,attendu", [
    # (equity_break, corr_state, macro_regime, data_fresh, data_started) -> (bloque, raison)
    ((True, COUPLE, NEUTRE, True, True), (True, contracts.EQUITY_VETO_BINDING)),
    ((True, COUPLE, HOSTILE, True, True), (True, contracts.EQUITY_VETO_REDUNDANT)),
    ((True, DECOUPLE, NEUTRE, True, True), (False, contracts.EQUITY_PASS_DECOUPLED)),
    ((True, TRANSITION, NEUTRE, True, True), (False, contracts.EQUITY_PASS_DECOUPLED)),
    ((False, COUPLE, NEUTRE, True, True), (False, contracts.EQUITY_PASS_NO_BREAK)),
    # A4 (03/08) : DEMARREE puis perimee => FAIL-SAFE, le veto bloque.
    ((False, DECOUPLE, PORTEUR, False, True), (True, contracts.EQUITY_VETO_STALE)),
    # ... mais JAMAIS demarree => bloc inoperant, il ne bloque rien (sinon 0 entree en backtest).
    ((True, COUPLE, NEUTRE, False, False), (False, contracts.EQUITY_PASS_NOT_STARTED)),
])
def test_evaluate_equity_veto_branches(args, attendu):
    assert macro_regime.evaluate_equity_veto(*args) == attendu


def test_evaluate_rend_toujours_une_raison_non_vide():
    for eb in (True, False):
        for st in params.MACRO_CORR_STATES:
            for reg in params.MACRO_REGIMES:
                for fresh in (True, False):
                    for started in (True, False):
                        bloque, raison = macro_regime.evaluate_equity_veto(
                            eb, st, reg, fresh, started)
                        assert isinstance(bloque, bool) and raison


def test_serie_perimee_bloque_mais_serie_absente_ne_bloque_pas():
    """Le coeur d'A4 : distinguer un flux MORT (on bloque) d'un bloc NON CONFIGURE (on passe).

    Confondre les deux ferait sortir 0 entree de tout backtest lance sans nasdaq100.csv."""
    assert macro_regime.evaluate_equity_veto(False, COUPLE, NEUTRE, False, True)[0] is True
    assert macro_regime.evaluate_equity_veto(True, COUPLE, NEUTRE, False, False)[0] is False


# ------------------------------------------------------------------ frame quotidien
def _regimes_daily(n=40, start="2024-01-01", regime=None):
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    return pd.DataFrame({RCOL: regime or NEUTRE}, index=idx)


def test_daily_equity_veto_sans_donnees_ne_bloque_jamais():
    daily = _regimes_daily()
    out = macro_regime.daily_equity_veto(pd.Series(dtype="float64"),
                                         pd.Series(dtype="float64"), daily)
    assert not out[contracts.EQUITY_VETO_COL].any()
    assert (out[contracts.EQUITY_VETO_REASON_COL] == contracts.EQUITY_PASS_NOT_STARTED).all()


def test_daily_equity_veto_est_decale_d_un_jour():
    """Point-in-time : le veto du jour J ne peut refleter que des donnees <= J-1."""
    daily = _regimes_daily(n=40, start="2024-01-01")
    sessions = pd.bdate_range("2023-11-01", periods=60, tz="UTC")
    eq = pd.Series(np.linspace(100, 60, 60), index=sessions)      # chute continue => cassures
    btc = pd.Series(np.linspace(100, 60, 120),
                    index=pd.date_range("2023-11-01", periods=120, freq="D", tz="UTC"))
    out = macro_regime.daily_equity_veto(eq, btc, daily)
    assert len(out) == len(daily)
    assert out.index.equals(daily.index)
    assert out[contracts.EQUITY_VETO_COL].dtype == bool


def test_compteur_de_jours_stale_consecutifs():
    """Un flux mort doit etre visible dans le journal : jours_max donne la duree de l'episode."""
    daily = _regimes_daily(n=30, start="2024-03-01")
    sessions = pd.bdate_range("2024-02-01", periods=10, tz="UTC")  # s'arrete debut fevrier
    eq = pd.Series(np.linspace(100, 95, 10), index=sessions)
    btc = pd.Series(np.linspace(100, 95, 90),
                    index=pd.date_range("2024-01-01", periods=90, freq="D", tz="UTC"))
    out = macro_regime.daily_equity_veto(eq, btc, daily)

    stale = out[out[contracts.EQUITY_VETO_REASON_COL] == contracts.EQUITY_VETO_STALE]
    assert len(stale) > 0                       # serie demarree puis morte => fail-safe
    assert stale[contracts.EQUITY_VETO_COL].all()
    assert (stale["stale_days"] == range(1, len(stale) + 1)).all()  # 1, 2, 3... consecutifs


def test_le_bloc_peut_reellement_bloquer_bout_en_bout():
    """Anti-inertie : avec un indice REELLEMENT correle au BTC et une cassure, le pipeline
    complet doit produire au moins un veto BINDING. Sans ce test, un bloc qui ne s'arme
    jamais (rho toujours sous le seuil) passerait tous les autres tests."""
    cal = pd.date_range("2024-01-01", periods=400, freq="D", tz="UTC")
    rng = np.random.default_rng(7)
    facteur = rng.normal(0, 0.012, len(cal))
    btc = pd.Series(100 * np.exp(np.cumsum(facteur + rng.normal(0, 0.004, len(cal)))), index=cal)

    sessions = cal[cal.dayofweek < 5]
    eq = pd.Series(100 * np.exp(np.cumsum(
        pd.Series(facteur, index=cal).reindex(sessions).to_numpy())), index=sessions)
    eq.iloc[-40:] *= np.linspace(1.0, 0.75, 40)   # decrochage final => cassure du plancher 20 j

    daily = _regimes_daily(n=len(cal), start="2024-01-01")
    out = macro_regime.daily_equity_veto(eq, btc, daily)

    raisons = set(out[contracts.EQUITY_VETO_REASON_COL])
    assert contracts.EQUITY_VETO_BINDING in raisons, f"bloc inerte, raisons vues : {raisons}"
    assert out[contracts.EQUITY_VETO_COL].any()


def test_stale_episodes_resume_le_blocage_ou_rend_none():
    idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
    sain = pd.DataFrame({contracts.EQUITY_VETO_REASON_COL: contracts.EQUITY_PASS_NO_BREAK,
                         "stale_days": 0}, index=idx)
    assert macro_regime.stale_episodes(sain) is None

    casse = pd.DataFrame({contracts.EQUITY_VETO_REASON_COL:
                          [contracts.EQUITY_PASS_NO_BREAK] + [contracts.EQUITY_VETO_STALE] * 4,
                          "stale_days": [0, 1, 2, 3, 4]}, index=idx)
    out = macro_regime.stale_episodes(casse)
    assert out["episodes"] == 1 and out["jours_max"] == 4 and out["jours_total"] == 4
