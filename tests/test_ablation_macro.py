"""Tests de `analysis/ablation_macro.py` — A5, ablation hors-ligne de la porte macro.

Ce que ces tests protegent, dans l'ordre d'importance :
1. le verrou B6 (pas de preenregistrement, pas de mesure) ;
2. le retrait du bump A5, qui est le piege principal du script (`seuil` est DEJA bumpe) ;
3. l'emboitement des quatre variantes, sans lequel les « signaux marginaux » n'existent pas ;
4. la detection d'une reconstruction infidele.
"""

import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "analysis"))

import ablation_macro as ab  # noqa: E402

from arit_lib import params  # noqa: E402

_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES
_SEUIL_BASE = 0.50


def _df(macro, conviction=0.9, conviction_short=0.9, regime="TREND", trend_dir=0):
    """Dataset minimal : une ligne par regime macro passe. Le seuil est deja bumpe en
    NEUTRE, exactement comme le fait `cio.conviction` avant l'ecriture du dataset."""
    macro = list(macro)
    seuil = [_SEUIL_BASE + (params.MACRO_NEUTRE_CONV_BUMP if m == _NEUTRE else 0.0)
             for m in macro]
    n = len(macro)
    return pd.DataFrame({
        "macro_regime": macro,
        "seuil": seuil,
        "conviction": [conviction] * n,
        "conviction_short": [conviction_short] * n,
        "rr_dispo": [2.0] * n,
        "rr_dispo_short": [2.0] * n,
        "regime": [regime] * n,
        "trend_dir": [trend_dir] * n,
        "ts_utc": [f"2024-01-0{i + 1}T00:00:00+00:00" for i in range(n)],
        "signal_long": [False] * n,
        "signal_short": [False] * n,
        "y_r_long": [0.5] * n,
        "y_r_short": [0.5] * n,
        "y_issue_long": ["TP"] * n,
        "y_issue_short": ["TP"] * n,
        "y_mfe_r_long": [1.0] * n,
        "y_mfe_r_short": [1.0] * n,
    })


# --- B6 : le verrou methodologique ---------------------------------------------------

def test_preenregistrement_absent_refuse_de_mesurer(tmp_path):
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(json.dumps({"id": "autre-chose"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="B6"):
        ab.preenregistrement(registre, "A5-ablation-porte-macro")


def test_preenregistrement_fichier_absent_refuse_de_mesurer(tmp_path):
    with pytest.raises(SystemExit, match="B6"):
        ab.preenregistrement(tmp_path / "rien.jsonl", "A5-ablation-porte-macro")


def test_dernier_protocole_fait_foi(tmp_path):
    """Amender un protocole = ajouter une ligne `preenregistre` ; la derniere fait foi."""
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(
        json.dumps({"id": "X", "statut": "preenregistre", "v": 1}) + "\n"
        + json.dumps({"id": "X", "statut": "preenregistre", "v": 2}) + "\n", encoding="utf-8")
    assert ab.preenregistrement(registre, "X")["v"] == 2


def test_ligne_de_resultat_ne_sert_jamais_de_protocole(tmp_path):
    """Le bug du 20/08 : une ligne `mesure`/`clos` ne porte ni variantes ni split_autorise.
    La laisser faire foi VIDAIT le garde-fou au lieu de l'appliquer."""
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(
        json.dumps({"id": "X", "statut": "preenregistre", "split_autorise": "train"}) + "\n"
        + json.dumps({"id": "X", "statut": "mesure"}) + "\n", encoding="utf-8")
    assert ab.preenregistrement(registre, "X")["split_autorise"] == "train"


def test_experience_close_refuse_une_remesure(tmp_path):
    """Rejouer une experience close jusqu'au bon resultat est du p-hacking par repetition :
    une nouvelle mesure exige un nouvel id, donc un essai de plus au compteur cumule."""
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(
        json.dumps({"id": "X", "statut": "preenregistre"}) + "\n"
        + json.dumps({"id": "X", "statut": "clos", "verdict": "indecidable"}) + "\n",
        encoding="utf-8")
    with pytest.raises(SystemExit, match="B6"):
        ab.preenregistrement(registre, "X")


def test_protocole_reste_lisible_apres_cloture(tmp_path):
    """La cloture bloque la MESURE, elle n'efface pas le protocole : il reste auditable."""
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(
        json.dumps({"id": "X", "statut": "preenregistre", "split_autorise": "train"}) + "\n"
        + json.dumps({"id": "X", "statut": "clos"}) + "\n", encoding="utf-8")
    assert ab.protocole(registre, "X")["split_autorise"] == "train"


def test_resultat_sans_protocole_refuse_de_mesurer(tmp_path):
    """Un resultat ecrit sans protocole prealable ne vaut pas preenregistrement."""
    registre = tmp_path / "EXPERIMENTS.jsonl"
    registre.write_text(json.dumps({"id": "X", "statut": "mesure"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="B6"):
        ab.preenregistrement(registre, "X")


def test_experience_reelle_est_preenregistree():
    """Le registre versionne doit contenir le protocole que le script exige — A5 est CLOSE
    depuis le 18/08, donc c'est `protocole` (lecture) et non le verrou de mesure."""
    entree = ab.protocole(ab.EXPERIMENTS, ab.EXPERIENCE_ID)
    assert entree["split_autorise"] == "train"
    assert {v["nom"] for v in entree["variantes"]} == {v["nom"] for v in ab.VARIANTES}


def test_a5_est_close_donc_le_script_refuse_de_la_rejouer():
    """Consequence directe de la cloture d'A5 le 18/08 : `ablation_macro.py` relance tel quel
    s'arrete. C'est le comportement voulu, pas une panne."""
    with pytest.raises(SystemExit, match="CLOSE"):
        ab.preenregistrement(ab.EXPERIMENTS, ab.EXPERIENCE_ID)


# --- le piege du bump deja applique --------------------------------------------------

def test_seuil_sans_bump_ne_touche_que_neutre():
    df = _df([_PORTEUR, _NEUTRE, _HOSTILE])
    nu = ab.seuil_sans_bump(df)
    assert nu.tolist() == pytest.approx([_SEUIL_BASE] * 3)
    assert df["seuil"].tolist() != nu.tolist()   # la colonne d'origine n'est pas modifiee


def test_bump_change_le_nombre_de_signaux_en_neutre():
    """Conviction pile entre le seuil nu et le seuil bumpe : V0 refuse, V1 accepte."""
    df = _df([_NEUTRE], conviction=_SEUIL_BASE + 0.01)
    v0, v1 = (v for v in ab.VARIANTES if v["nom"] in ("V0_prod", "V1_sans_bump"))
    assert not ab.masques(df, v0)["long"].iloc[0]
    assert ab.masques(df, v1)["long"].iloc[0]


# --- la porte macro elle-meme ---------------------------------------------------------

def test_directions_autorisees_par_variante():
    df = _df([_PORTEUR, _NEUTRE, _HOSTILE])
    par_nom = {v["nom"]: ab.masques(df, v) for v in ab.VARIANTES}
    assert par_nom["V1_sans_bump"]["long"].tolist() == [True, True, False]
    assert par_nom["V1_sans_bump"]["short"].tolist() == [False, True, True]
    assert par_nom["V2_porteur_hostile"]["long"].tolist() == [True, False, False]
    assert par_nom["V2_porteur_hostile"]["short"].tolist() == [False, False, True]
    assert par_nom["V3_macro_off"]["long"].tolist() == [True, True, True]


def test_macro_inconnue_retombe_sur_long_seul():
    """Fail-safe de `cio.direction_macro` : pas de short sur une absence d'information."""
    df = _df([None])
    masques = ab.masques(df, ab.VARIANTES[0])
    assert masques["long"].iloc[0]
    assert not masques["short"].iloc[0]


def test_hors_entry_regimes_aucun_signal():
    df = _df([_PORTEUR], regime="RANGE")
    masques = ab.masques(df, ab.VARIANTES[3])       # V3, la variante la plus permissive
    assert not masques["long"].iloc[0] and not masques["short"].iloc[0]


def test_emboitement_des_quatre_variantes():
    df = _df([_PORTEUR, _NEUTRE, _HOSTILE], conviction=_SEUIL_BASE + 0.01,
             conviction_short=_SEUIL_BASE + 0.01)
    tous = {v["nom"]: ab.masques(df, v) for v in ab.VARIANTES}
    ab.verifier_emboitement(tous)                   # ne doit rien lever
    for etroit, large in ab.EMBOITEMENT:
        for sens in ("long", "short"):
            assert not (tous[etroit][sens] & ~tous[large][sens]).any()


def test_emboitement_rompu_est_detecte():
    faux = {nom: {"long": pd.Series([False]), "short": pd.Series([False])}
            for nom in (v["nom"] for v in ab.VARIANTES)}
    faux["V0_prod"]["long"] = pd.Series([True])     # V0 deborde de V1 : impossible
    with pytest.raises(SystemExit, match="emboitement"):
        ab.verifier_emboitement(faux)


# --- fidelite de la reconstruction ----------------------------------------------------

def test_fidelite_detecte_un_ecart():
    df = _df([_PORTEUR])
    with pytest.raises(SystemExit, match="fidelite"):
        ab.verifier_fidelite(df, {"long": pd.Series([True]), "short": pd.Series([False])})


def test_fidelite_acceptee_quand_identique():
    df = _df([_PORTEUR])
    ab.verifier_fidelite(df, {"long": pd.Series([False]), "short": pd.Series([False])})


# --- outillage statistique ------------------------------------------------------------

def test_mde_decroit_avec_n_et_monte_avec_le_chevauchement():
    assert ab.mde(200) < ab.mde(50) < ab.mde(7)
    assert ab.mde(50, effectif=True) > ab.mde(50)


def test_bootstrap_blocs_encadre_la_moyenne():
    rng = np.random.default_rng(ab.SEED)
    x = np.array([1.5, -1.0, 1.5, -1.0, 1.5, -1.0, 1.5, -1.0], dtype=float)
    lo, hi = ab.bootstrap_blocs(x, ell=3, rng=rng, n_boot=500)
    assert lo <= x.mean() <= hi


def test_bootstrap_blocs_echantillon_trop_court():
    rng = np.random.default_rng(ab.SEED)
    lo, hi = ab.bootstrap_blocs(np.array([0.5]), ell=3, rng=rng, n_boot=10)
    assert np.isnan(lo) and np.isnan(hi)


def test_metriques_ensemble_vide():
    df = _df([_PORTEUR])
    assert ab.metriques(df, pd.Series([False]), "long") == {"n": 0}


def test_metriques_esperance_en_r():
    df = _df([_PORTEUR, _NEUTRE])
    m = ab.metriques(df, pd.Series([True, True]), "long")
    assert m["n"] == 2 and m["p_tp"] == 1.0
    assert m["esperance_r"] == pytest.approx(0.5)
    assert m["r_total"] == pytest.approx(1.0)
