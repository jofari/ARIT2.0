"""Tests de `analysis/dataset.py` — les erreurs qui ne se verraient PAS autrement.

Ce fichier ne teste pas le pipeline (il tourne sur 5 ans de donnees reelles, c'est son propre
test d'integration). Il teste les trois endroits ou une faute resterait muette tout en faussant
chaque conclusion tiree du dataset :

1. la triple barriere, ou une inversion de signe rendrait tous les shorts faux ;
2. la convention pessimiste sur bougie ambigue, qui est la seule protection contre un taux de
   reussite gonfle ;
3. le prefixe `y_` des cibles, qui est la seule chose qui empeche une fuite de cible dans un
   futur entrainement.
"""

import pathlib
import sqlite3
import sys

import numpy as np
import pandas as pd
import pytest

ANALYSIS_DIR = pathlib.Path(__file__).resolve().parents[1] / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

import dataset  # noqa: E402


def _fenetre(hauts, bas):
    return np.array(hauts, dtype=float), np.array(bas, dtype=float)


# ------------------------------------------------------------------ triple barriere
def test_long_touche_tp_avant_sl():
    hauts, bas = _fenetre([101, 116], [99, 110])
    issue, r, i = dataset._issue(hauts, bas, entree=100.0, sl=90.0, tp=115.0, sign=1)
    assert (issue, r, i) == ("TP", dataset.TP1_R, 1)


def test_long_touche_sl_avant_tp():
    hauts, bas = _fenetre([101, 116], [99, 89])
    issue, r, _ = dataset._issue(hauts, bas, entree=100.0, sl=90.0, tp=115.0, sign=1)
    assert (issue, r) == ("SL", -1.0)


def test_short_geometrie_inversee():
    """Un short gagne quand le prix BAISSE : SL au-dessus, TP en dessous.

    C'est le test qui compte le plus du fichier : une inversion ici ferait passer tous les
    shorts pour des gagnants sans qu'aucun autre controle ne s'en apercoive.
    """
    hauts, bas = _fenetre([101, 102], [99, 84])       # descend jusqu'a 84
    issue, r, _ = dataset._issue(hauts, bas, entree=100.0, sl=110.0, tp=85.0, sign=-1)
    assert (issue, r) == ("TP", dataset.TP1_R)

    hauts, bas = _fenetre([101, 111], [99, 98])       # monte jusqu'a 111 => stoppe
    issue, r, _ = dataset._issue(hauts, bas, entree=100.0, sl=110.0, tp=85.0, sign=-1)
    assert (issue, r) == ("SL", -1.0)


@pytest.mark.parametrize("sign,sl,tp", [(1, 90.0, 115.0), (-1, 110.0, 85.0)])
def test_bougie_ambigue_compte_sl(sign, sl, tp):
    """SL et TP touches dans la MEME bougie => SL. Convention pessimiste de replay_entries.

    Sans elle, un TP et un SL simultanes seraient comptes gagnants et le taux de reussite
    mesure serait structurellement optimiste — exactement le biais que le projet traque.
    """
    hauts, bas = _fenetre([120], [80])                # la bougie couvre les deux barrieres
    issue, _, _ = dataset._issue(hauts, bas, 100.0, sl, tp, sign)
    assert issue == "SL"


def test_aucune_barriere_touchee_donne_horizon():
    hauts, bas = _fenetre([101, 102, 103], [99, 98, 97])
    issue, r, i = dataset._issue(hauts, bas, 100.0, 90.0, 115.0, 1)
    assert issue == "horizon" and np.isnan(r) and i == 2


# ------------------------------------------------------------------ cibles / fuite
def _df_synthetique(n=40):
    """DataFrame minimal portant ce que `etiqueter` lit : date/close/high/low + colonnes 4h."""
    dates = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    close = np.linspace(100.0, 130.0, n)
    return pd.DataFrame({
        "date": dates, "open": close, "close": close,
        "high": close + 1.0, "low": close - 1.0,
        "last_hl_4h": 95.0, "nearest_res_4h": 140.0,
        "last_lh_4h": 135.0, "nearest_sup_4h": 90.0,
        "atr_4h": 2.0,
    })


def test_toutes_les_cibles_sont_prefixees_y():
    """Garantie anti-fuite : hors sl_*/tp1_* (connus a l'entree), tout regard vers le futur
    porte le prefixe `y_`. Un entrainement qui exclut `y_%` est alors sur par construction."""
    cibles = dataset.etiqueter(_df_synthetique(), idx=2, horizon_h=20)
    assert cibles, "aucune cible produite"
    fuites = [k for k in cibles
              if not k.startswith(dataset.CIBLE_PREFIX)
              and not k.startswith(("sl_", "tp1_"))]
    assert fuites == [], f"cibles non prefixees, fuite possible : {fuites}"


def test_rendements_futurs_sont_bien_futurs():
    """`y_ret_24h` doit valoir close[idx+24]/close[idx]-1, jamais l'inverse ni un decalage."""
    df = _df_synthetique(n=60)
    idx = 5
    cibles = dataset.etiqueter(df, idx=idx, horizon_h=20)
    attendu = df["close"].iloc[idx + 24] / df["close"].iloc[idx] - 1.0
    assert cibles["y_ret_24h"] == pytest.approx(attendu)


def test_horizon_hors_donnees_donne_none_pas_zero():
    """Rendement inatteignable => None. Un 0.0 se confondrait avec « pas de mouvement »."""
    cibles = dataset.etiqueter(_df_synthetique(n=30), idx=25, horizon_h=4)
    assert cibles["y_ret_168h"] is None


# ------------------------------------------------------------------ ecriture SQLite
def test_ecriture_sqlite_union_des_colonnes(tmp_path):
    """Lignes heterogenes (une paire sans un motif cdl_*) => union des colonnes, pas de perte."""
    db = tmp_path / "t.sqlite"
    dataset.ecrire_sqlite([
        {"pair": "A", "ts_utc": "2024-01-01T00:00:00+00:00", "split": "train", "cdl_x": 1},
        {"pair": "B", "ts_utc": "2024-01-02T00:00:00+00:00", "split": "holdout", "y_ret_24h": 0.5},
    ], db)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        lignes = [dict(r) for r in conn.execute(f"SELECT * FROM {dataset.TABLE} ORDER BY pair")]
    assert {"cdl_x", "y_ret_24h", "split"} <= set(lignes[0])
    assert lignes[0]["cdl_x"] == 1 and lignes[0]["y_ret_24h"] is None
    assert lignes[1]["y_ret_24h"] == 0.5 and lignes[1]["cdl_x"] is None


def test_ecriture_refuse_un_dataset_vide(tmp_path):
    with pytest.raises(SystemExit):
        dataset.ecrire_sqlite([], tmp_path / "vide.sqlite")


def test_holdout_scelle_a_la_date_declaree():
    """B5 — la borne du hold-out est une constante, pas un parametre : elle ne doit pas
    pouvoir bouger run apres run sans que ce soit une modification de code visible."""
    assert dataset.HOLDOUT_DEBUT == "2025-01-01"
    assert pd.Timestamp(dataset.HOLDOUT_DEBUT, tz="UTC") < pd.Timestamp.now(tz="UTC")
