"""Tests M03 — cio.conviction / explain (docs/modules/M03, PDR 04.3/04.4)."""

import json

import pandas as pd

from arit_lib import cio, contracts, params

SCORE_COLS = ("s_structure", "s_momentum", "s_sr", "s_patterns", "s_volume")


def _scores(value):
    return {col: value for col in SCORE_COLS}


def _df(scores, mult, seuil, regime, rr=2.0, new_4h=True, n=1,
        scores_short=None, mult_short=None, rr_short=None, trend_dir=0):
    """df minimal pour cio. A2 : les colonnes short existent TOUJOURS (features.compute_all
    les produit systematiquement) ; par defaut elles sont neutres pour que les cas de test
    haussiers historiques restent litteralement les memes."""
    data = {col: [scores[col]] * n for col in SCORE_COLS}
    short = scores_short if scores_short is not None else {c: 0.0 for c in SCORE_COLS}
    for col in SCORE_COLS:
        data[col + contracts.SHORT_SUFFIX] = [short[col]] * n
    data["multiplicateur"] = [mult] * n
    data["multiplicateur_short"] = [mult if mult_short is None else mult_short] * n
    data["seuil"] = [seuil] * n
    data["regime"] = [regime] * n
    data["rr_dispo"] = [rr] * n
    data["rr_dispo_short"] = [rr if rr_short is None else rr_short] * n
    data["new_4h"] = [new_4h] * n
    data[contracts.TREND_DIR_COL] = [trend_dir] * n
    return pd.DataFrame(data)


def _conv(scores, mult, seuil, regime, rr=2.0, new_4h=True):
    return cio.conviction(_df(scores, mult, seuil, regime, rr=rr, new_4h=new_4h))


def test_weights_sum_to_one():
    assert abs(sum(params.POIDS.values()) - 1.0) < 1e-9


def test_conviction_full_scores_capped_at_one():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] == 1.0


def test_conviction_formula_weighted_by_multiplicateur():
    trend = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert abs(trend["conviction"].iloc[0] - 0.5) < 1e-9  # Σ w·0.5 = 0.5, ×1.0
    reduced = _conv(_scores(0.5), params.MULT_REDUCED, params.SEUIL_TRANSITION, "TRANSITION")
    assert abs(reduced["conviction"].iloc[0] - 0.5 * params.MULT_REDUCED) < 1e-9


def test_conviction_bounded_zero_one():
    rows = [(v, m) for v in params.SCORE_VALUES
            for m in (params.MULT_RISK_OFF, params.MULT_REDUCED, params.MULT_FULL)]
    df = pd.DataFrame({
        **{col: [v for v, _ in rows] for col in SCORE_COLS},
        **{col + contracts.SHORT_SUFFIX: [v for v, _ in rows] for col in SCORE_COLS},
        "multiplicateur": [m for _, m in rows],
        "multiplicateur_short": [m for _, m in rows],
        "seuil": [params.SEUIL_TREND] * len(rows),
        "regime": ["TREND"] * len(rows),
        "rr_dispo": [2.0] * len(rows),
        "rr_dispo_short": [2.0] * len(rows),
        "new_4h": [True] * len(rows),
        contracts.TREND_DIR_COL: [0] * len(rows),
    })
    out = cio.conviction(df)
    for col in ("conviction", "conviction_short"):   # A2 : meme borne pour les deux sens
        assert (out[col] >= 0.0).all()
        assert (out[col] <= 1.0).all()


def test_signal_at_exact_seuil_uses_ge():
    # conviction == seuil => signal (>=, pas >). On fixe seuil EXACTEMENT a la
    # conviction calculee : robuste au bruit flottant, isole la semantique >=.
    conv = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")["conviction"].iloc[0]
    at_seuil = _conv(_scores(0.5), params.MULT_FULL, conv, "TREND")
    assert at_seuil["conviction"].iloc[0] == conv
    assert bool(at_seuil["signal_long"].iloc[0]) is True


def test_no_signal_just_below_seuil():
    out = _conv(_scores(0.3), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] < params.SEUIL_TREND
    assert bool(out["signal_long"].iloc[0]) is False


def test_multiplicateur_zero_never_signals():
    out = _conv(_scores(1.0), params.MULT_RISK_OFF, params.SEUIL_TREND, "TREND")
    assert out["conviction"].iloc[0] == 0.0
    assert bool(out["signal_long"].iloc[0]) is False
    risk_off = _conv(_scores(1.0), params.MULT_RISK_OFF, float("nan"), "RISK_OFF")
    assert bool(risk_off["signal_long"].iloc[0]) is False


def test_no_signal_when_regime_not_entry():
    # conviction >= seuil mais regime RANGE (hors ENTRY_REGIMES) => pas de signal.
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "RANGE")
    assert out["conviction"].iloc[0] >= params.SEUIL_TREND
    assert bool(out["signal_long"].iloc[0]) is False


def test_no_signal_when_rr_below_min():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND", rr=params.RR_MIN - 0.1)
    assert bool(out["signal_long"].iloc[0]) is False


def test_no_signal_when_not_new_4h():
    out = _conv(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND", new_4h=False)
    assert bool(out["signal_long"].iloc[0]) is False


def test_transition_signal_path():
    out = _conv(_scores(1.0), params.MULT_REDUCED, params.SEUIL_TRANSITION, "TRANSITION")
    assert bool(out["signal_long"].iloc[0]) is True


def test_conviction_adds_contract_columns():
    out = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert "conviction" in out.columns
    assert "signal_long" in out.columns
    assert out["signal_long"].dtype == bool


# ------------------------------------------------------------------ explain()

def _full_row(fear_greed=60, macro_stale=False, with_macro=True):
    df = _df(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    df["adx_4h"] = 30.0
    df["ema50_4h"] = 110.0
    df["ema200_4h"] = 100.0
    df["close_4h"] = 115.0
    if with_macro:
        df["fear_greed"] = fear_greed
        df["macro_stale"] = macro_stale
    return cio.conviction(df).iloc[0]


def test_explain_keys_aligned_on_contracts():
    d = cio.explain(_full_row())
    assert set(d["regime_inputs"].keys()) == set(contracts.REGIME_INPUT_KEYS)
    assert set(d["scores"].keys()) == set(contracts.SCORE_KEYS)
    for key in ("regime", "conviction", "seuil", "multiplicateur", "poids", "produit_pondere"):
        assert key in d


def test_explain_is_strict_json_serializable():
    json.dumps(cio.explain(_full_row()), allow_nan=False)


def test_explain_decision_is_reconstructible():
    row = _full_row()
    d = cio.explain(row)
    manual = sum(d["poids"][k] * d["scores"][k] for k in d["scores"])
    assert abs(manual - d["produit_pondere"]) < 1e-9
    recomputed = min(1.0, d["produit_pondere"] * d["multiplicateur"])
    assert abs(recomputed - d["conviction"]) < 1e-9
    assert abs(d["conviction"] - float(row["conviction"])) < 1e-9


def test_explain_surfaces_macro_inputs():
    d = cio.explain(_full_row(fear_greed=30, macro_stale=True))
    assert d["regime_inputs"]["fear_greed"] == 30
    assert d["regime_inputs"]["macro_stale"] is True


def test_explain_macro_absent_is_none():
    d = cio.explain(_full_row(with_macro=False))
    assert d["regime_inputs"]["fear_greed"] is None
    assert d["regime_inputs"]["macro_stale"] is None


def test_explain_close_vs_ema_signed_difference():
    d = cio.explain(_full_row())
    assert abs(d["regime_inputs"]["close_vs_ema"] - (115.0 - 110.0)) < 1e-9


# ------------------------------------- Macro Analyst V1.1 : bump de seuil NEUTRE (04 §4.2)
def _df_macro(scores, mult, seuil, regime, macro, rr=2.0, new_4h=True):
    df = _df(scores, mult, seuil, regime, rr=rr, new_4h=new_4h)
    df[contracts.MACRO_REGIME_COL] = macro
    return df


def test_neutre_column_bumps_seuil():
    out = cio.conviction(
        _df_macro(_scores(0.5), params.MULT_REDUCED, params.SEUIL_TREND, "TREND", "NEUTRE"))
    assert out["seuil"].iloc[0] == params.SEUIL_TREND + params.MACRO_NEUTRE_CONV_BUMP


def test_porteur_column_no_bump():
    out = cio.conviction(
        _df_macro(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND", "PORTEUR"))
    assert out["seuil"].iloc[0] == params.SEUIL_TREND


def test_column_absent_no_bump_backcompat():
    out = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")
    assert out["seuil"].iloc[0] == params.SEUIL_TREND


def test_neutre_bump_can_block_marginal_signal():
    # Conviction pile au seuil de base : PORTEUR passe (>=), NEUTRE (+0,05) bloque.
    conv = _conv(_scores(0.5), params.MULT_FULL, params.SEUIL_TREND, "TREND")["conviction"].iloc[0]
    porteur = cio.conviction(_df_macro(_scores(0.5), params.MULT_FULL, conv, "TREND", "PORTEUR"))
    assert bool(porteur["signal_long"].iloc[0]) is True
    neutre = cio.conviction(_df_macro(_scores(0.5), params.MULT_FULL, conv, "TREND", "NEUTRE"))
    assert neutre["seuil"].iloc[0] == conv + params.MACRO_NEUTRE_CONV_BUMP
    assert bool(neutre["signal_long"].iloc[0]) is False


# ============ A2 — la macro donne la DIRECTION, la technique le timing (docs/01 v4) ============
def _dir_df(macro, trend_dir, scores=None, scores_short=None):
    """df en TREND, conviction pleine des deux cotes : seuls la macro et trend_dir tranchent."""
    df = _df(_scores(1.0) if scores is None else scores,
             params.MULT_FULL, params.SEUIL_TREND, "TREND",
             scores_short=_scores(1.0) if scores_short is None else scores_short,
             trend_dir=trend_dir)
    df[contracts.MACRO_REGIME_COL] = [macro]
    return cio.conviction(df)


def test_porteur_autorise_le_long_seul():
    out = _dir_df("PORTEUR", trend_dir=1)
    assert out["direction_macro"].iloc[0] == contracts.DIR_LONG
    assert bool(out["signal_long"].iloc[0])
    assert not bool(out["signal_short"].iloc[0])


def test_hostile_autorise_le_short_seul_et_bloque_toujours_le_long():
    """Equivalence a demontrer : avant A2, HOSTILE => RISK_OFF => aucun long. Apres A2 le
    regime n'est plus ecrase, mais le long doit rester bloque — par la direction cette fois."""
    out = _dir_df("HOSTILE", trend_dir=-1)
    assert out["direction_macro"].iloc[0] == contracts.DIR_SHORT
    assert not bool(out["signal_long"].iloc[0])     # <- l'equivalence cote long
    assert bool(out["signal_short"].iloc[0])


def test_neutre_autorise_les_deux_sens():
    """A5 : la penalite NEUTRE est conservee — elle releve le seuil, elle ne coupe pas."""
    out = _dir_df("NEUTRE", trend_dir=0)
    assert out["direction_macro"].iloc[0] == contracts.DIR_BOTH
    assert out["seuil"].iloc[0] == params.SEUIL_TREND + params.MACRO_NEUTRE_CONV_BUMP
    assert bool(out["signal_long"].iloc[0])
    assert bool(out["signal_short"].iloc[0])
    # Le bump mord dans les DEUX sens : conviction juste sous le seuil releve => rien.
    marginal = _dir_df("NEUTRE", trend_dir=0,
                       scores=_scores(0.5), scores_short=_scores(0.5))
    assert not bool(marginal["signal_long"].iloc[0])
    assert not bool(marginal["signal_short"].iloc[0])


def test_trend_dir_interdit_de_trader_a_contresens_de_la_technique():
    """LE garde-fou de non-regression : elargir TREND aux tendances baissieres (A2,
    regimes.REGLES) ne doit ouvrir AUCUN long nouveau."""
    # Tendance technique baissiere + macro qui autoriserait le long => long refuse.
    out = _dir_df("PORTEUR", trend_dir=-1)
    assert not bool(out["signal_long"].iloc[0])
    # Tendance technique haussiere + macro qui autoriserait le short => short refuse.
    out = _dir_df("HOSTILE", trend_dir=1)
    assert not bool(out["signal_short"].iloc[0])
    # trend_dir = 0 (indecis) : les deux restent possibles, c'est la macro qui tranche.
    out = _dir_df("NEUTRE", trend_dir=0)
    assert bool(out["signal_long"].iloc[0]) and bool(out["signal_short"].iloc[0])


def test_macro_inconnue_ou_absente_retombe_en_long_seul():
    """Deux fail-safes : on n'ouvre jamais un short sur une absence d'information."""
    nan_macro = _dir_df(float("nan"), trend_dir=0)
    assert nan_macro["direction_macro"].iloc[0] == contracts.DIR_LONG
    assert not bool(nan_macro["signal_short"].iloc[0])
    # Colonne absente = chemin LIVE actuel (docs/06 §6.3) : long-only, comme avant A2.
    df = _df(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND",
             scores_short=_scores(1.0), trend_dir=0)
    out = cio.conviction(df)
    assert (out["direction_macro"] == contracts.DIR_LONG).all()
    assert not bool(out["signal_short"].iloc[0])
    assert bool(out["signal_long"].iloc[0])


def test_short_exige_son_propre_rr():
    """Le short lit rr_dispo_short (distance au SUPPORT), jamais le rr long."""
    df = _df(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND",
             rr=5.0, rr_short=params.RR_MIN - 0.01,
             scores_short=_scores(1.0), trend_dir=-1)
    df[contracts.MACRO_REGIME_COL] = ["HOSTILE"]
    out = cio.conviction(df)
    assert not bool(out["signal_short"].iloc[0])   # rr long genereux : sans effet


def test_conviction_short_utilise_les_scores_et_le_multiplicateur_short():
    out = _dir_df("HOSTILE", trend_dir=-1, scores=_scores(0.0), scores_short=_scores(1.0))
    assert out["conviction"].iloc[0] == 0.0
    assert out["conviction_short"].iloc[0] == 1.0


def test_cio_pose_toutes_les_colonnes_du_contrat():
    out = _dir_df("NEUTRE", trend_dir=0)
    for col in contracts.CIO_COLUMNS:
        assert col in out.columns


# ==== A2-quater (20/08) — le veto actions c6/c7 est un FILTRE DIRECTIONNEL, plus un veto sec ====
def _dir_df_veto(macro, trend_dir, raison=None, veto=True):
    """Meme df que _dir_df, avec le bloc correlation actions pose (colonne + raison)."""
    df = _df(_scores(1.0), params.MULT_FULL, params.SEUIL_TREND, "TREND",
             scores_short=_scores(1.0), trend_dir=trend_dir)
    df[contracts.MACRO_REGIME_COL] = [macro]
    df[contracts.EQUITY_VETO_COL] = [veto]
    if raison is not None:
        df[contracts.EQUITY_VETO_REASON_COL] = [raison]
    return cio.conviction(df)


def test_veto_actions_retire_le_long_et_laisse_le_short_en_neutre():
    """Le coeur de A2-quater : NEUTRE autorisait les deux sens, le veto n'en retire qu'un."""
    out = _dir_df_veto("NEUTRE", trend_dir=-1, raison=contracts.EQUITY_VETO_BINDING)
    assert out["direction_macro"].iloc[0] == contracts.DIR_SHORT
    assert not bool(out["signal_long"].iloc[0])
    assert bool(out["signal_short"].iloc[0])


def test_veto_actions_ne_cree_jamais_un_short_contre_une_macro_porteuse():
    """PORTEUR + cassure actions = desaccord : aucune entree. Le veto SOUSTRAIT le long,
    il n'INVENTE pas un avis de short que la macro ne donne pas."""
    out = _dir_df_veto("PORTEUR", trend_dir=-1, raison=contracts.EQUITY_VETO_BINDING)
    assert out["direction_macro"].iloc[0] == contracts.DIR_NONE
    assert not bool(out["signal_long"].iloc[0])
    assert not bool(out["signal_short"].iloc[0])


def test_veto_actions_equivalence_cote_long_avant_apres_a2_quater():
    """LE garde-fou de non-regression : quelle que soit la macro, un veto actions arme
    n'ouvre AUCUN long — exactement ce que faisait le RISK_OFF qu'il remplace."""
    for macro in ("PORTEUR", "NEUTRE", "HOSTILE", float("nan")):
        out = _dir_df_veto(macro, trend_dir=1, raison=contracts.EQUITY_VETO_BINDING)
        assert not bool(out["signal_long"].iloc[0]), macro


def test_veto_actions_stale_ne_donne_aucune_direction():
    """Serie actions perimee = doute sur la DONNEE, pas avis de marche : cio n'en tire rien
    (le coupe-circuit RISK_OFF reste porte par regimes, cf. test_regimes)."""
    out = _dir_df_veto("NEUTRE", trend_dir=-1, raison=contracts.EQUITY_VETO_STALE)
    assert out["direction_macro"].iloc[0] == contracts.DIR_BOTH


def test_veto_actions_sans_raison_ne_filtre_pas_la_direction():
    """Raison absente : impossible de distinguer fail-safe et avis de marche. cio s'abstient,
    regimes garde le coupe-circuit (retrocompatibilite stricte)."""
    out = _dir_df_veto("NEUTRE", trend_dir=-1, raison=None)
    assert out["direction_macro"].iloc[0] == contracts.DIR_BOTH


def test_veto_actions_faux_ne_change_aucune_direction():
    out = _dir_df_veto("NEUTRE", trend_dir=0, raison=contracts.EQUITY_PASS_NO_BREAK, veto=False)
    assert out["direction_macro"].iloc[0] == contracts.DIR_BOTH
