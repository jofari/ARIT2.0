"""M03 — CIO : fusion contexte + scores -> conviction (PDR 04.3/04.4, docs/modules/M03).

Fonctions pures. Ajoute `conviction` et `signal_long` (contracts.CIO_COLUMNS) et
fournit `explain` : le dict reconstruisant chaque decision pour le journal
(idee 5, docs/08 — invariant M03.2). Aucun reseau, aucun LLM ; imports internes
limites a contracts/params (docs/11). V2 (FreqAI) remplacera conviction() derriere
la MEME interface (df in -> conviction out) : aucun couplage a l'implementation.
"""

import math

import numpy as np
import pandas as pd

from arit_lib import contracts, params


_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES


def direction_macro(df: pd.DataFrame) -> pd.Series:
    """Sens AUTORISE par la macro sur chaque bougie — hypothese v4 (docs/01, decision A7).

    PORTEUR => long seul · HOSTILE => short seul · NEUTRE => les deux, au seuil releve
    (decision A5 : la penalite NEUTRE est CONSERVEE).

    Deux fail-safes, tous deux vers le LONG SEUL, c.-a-d. le comportement d'avant A2 :
    - regime macro inconnu (NaN : jour sans donnee macro) — on n'ouvre pas de short sur
      une absence d'information ;
    - colonne macro absente (chemin LIVE actuel, docs/06 §6.3 : `macro_state.json` porte
      fear_greed/risk_off/stale mais PAS le regime V1.1 en 5 composants). ⚠️ Tant que M08
      n'ecrit pas ce regime, le live reste long-only alors que le backtest est long+short :
      c'est une rupture de parite backtest/live (docs/07 §7.3) et un BLOQUANT declare du
      dry-run, pas un detail d'implementation.

    ⚠️ A2-quater (decision Jonas 2026-08-20) : le veto actions c6/c7 est un FILTRE
    DIRECTIONNEL, plus un coupe-circuit. Il s'applique donc ICI (sur la direction) et non
    plus dans regimes._classify_macro (qui forcait RISK_OFF, donc les DEUX sens). Une
    cassure du NASDAQ correlee au BTC est un avis BAISSIER : elle retire le long, elle ne
    retire pas le short. `evaluate_equity_veto` le disait deja dans son propre contrat
    (« bloquer_nouveaux_longs ») ; le cablage, lui, bloquait les deux.

    Le veto ne CREE jamais de short : il retire le long de ce que la macro autorisait
    (PORTEUR -> aucune entree, NEUTRE -> short seul, HOSTILE -> inchange). Shorter parce
    que les actions cassent alors que la macro est PORTEUR serait un avis directionnel
    invente par un fail-safe, pas un filtre.

    EXCEPTION, et elle est structurante : `EQUITY_VETO_STALE` (serie demarree puis perimee)
    n'est pas un avis de marche, c'est un doute sur la DONNEE. Il reste un coupe-circuit et
    continue d'etre traite dans regimes._classify_macro. Meme principe que
    `regimes.donnee_non_fiable` : une donnee absente ne donne jamais de direction.
    """
    if contracts.MACRO_REGIME_COL not in df.columns:
        direction = pd.Series(contracts.DIR_LONG, index=df.index, dtype=object)
    else:
        macro = df[contracts.MACRO_REGIME_COL]
        direction = pd.Series(
            np.select([macro == _PORTEUR, macro == _HOSTILE, macro == _NEUTRE],
                      [contracts.DIR_LONG, contracts.DIR_SHORT, contracts.DIR_BOTH],
                      default=contracts.DIR_LONG),   # NaN/inconnu => fail-safe long seul
            index=df.index, dtype=object)
    veto = _veto_actions_directionnel(df)
    direction = direction.mask(veto & (direction == contracts.DIR_LONG), contracts.DIR_NONE)
    return direction.mask(veto & (direction == contracts.DIR_BOTH), contracts.DIR_SHORT)


def _veto_actions_directionnel(df: pd.DataFrame) -> pd.Series:
    """Veto actions c6/c7 dans son sens DIRECTIONNEL seul (A2-quater), STALE exclu.

    Colonne absente => bloc inoperant (aucun veto), comportement d'origine.
    Raison absente alors que le veto existe => on ne peut pas distinguer le fail-safe de
    l'avis de marche : aucun veto directionnel ici, `regimes` le traite en coupe-circuit.
    """
    if contracts.EQUITY_VETO_COL not in df.columns:
        return pd.Series(False, index=df.index, dtype=bool)
    veto = df[contracts.EQUITY_VETO_COL].fillna(False).astype(bool)
    if contracts.EQUITY_VETO_REASON_COL not in df.columns:
        return pd.Series(False, index=df.index, dtype=bool)
    return veto & (df[contracts.EQUITY_VETO_REASON_COL] != contracts.EQUITY_VETO_STALE)


def conviction(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute conviction/signal_long ET leurs jumeaux short (contracts.CIO_COLUMNS).

    conviction = min(1, Σ poids·score × multiplicateur)      — formule PDR 04.4.
    Le short applique la MEME formule aux scores `s_*_short` et au `multiplicateur_short`
    (POIDS est indexe sans suffixe : les poids FIGES sont partages, A2 n'en cree aucun).

    signal_long = (conviction >= seuil) & (rr_dispo >= RR_MIN)
                  & (regime ∈ ENTRY_REGIMES) & new_4h
                  & (trend_dir >= 0) & la macro autorise le long
    signal_short = miroir strict, avec trend_dir <= 0.

    Le >= au seuil est contractuel (M03). seuil est NaN en RANGE/RISK_OFF => la
    comparaison vaut False (double securite avec le filtre de regime).
    `trend_dir` est ce qui garantit qu'elargir TREND aux tendances baissieres (A2,
    regimes.REGLES) n'ouvre AUCUN long nouveau : un long exige trend_dir >= 0.
    """
    weighted = sum(params.POIDS[col] * df[col] for col in params.POIDS)
    df["conviction"] = np.minimum(1.0, weighted * df["multiplicateur"])
    sfx = contracts.SHORT_SUFFIX
    weighted_short = sum(params.POIDS[col] * df[col + sfx] for col in params.POIDS)
    df["conviction" + sfx] = np.minimum(1.0, weighted_short * df["multiplicateur" + sfx])
    if contracts.MACRO_REGIME_COL in df.columns:  # Macro V1.1 : NEUTRE => seuil +0,05 (04 §4.2)
        neutre = (df[contracts.MACRO_REGIME_COL] == _NEUTRE).astype(float)
        df["seuil"] = df["seuil"] + neutre * params.MACRO_NEUTRE_CONV_BUMP
    direction = direction_macro(df)
    df["direction_macro"] = direction
    tradable = df["regime"].isin(params.ENTRY_REGIMES) & df["new_4h"].astype(bool)
    trend = df[contracts.TREND_DIR_COL]
    df["signal_long"] = (
        (df["conviction"] >= df["seuil"])
        & (df["rr_dispo"] >= params.RR_MIN)
        & tradable
        & (trend >= 0)
        & direction.isin((contracts.DIR_LONG, contracts.DIR_BOTH))
    )
    df["signal" + sfx] = (
        (df["conviction" + sfx] >= df["seuil"])
        & (df["rr_dispo" + sfx] >= params.RR_MIN)
        & tradable
        & (trend <= 0)
        & direction.isin((contracts.DIR_SHORT, contracts.DIR_BOTH))
    )
    return df


def _py(value):
    """Scalaire pandas/numpy -> type Python JSON-serialisable strict (NaN -> None)."""
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if math.isnan(number) else number
    return value


def explain(row: pd.Series) -> dict:
    """Dict JSON-serialisable reconstruisant integralement la decision (M03.2, docs/08.1).

    Cles alignees sur contracts.REGIME_INPUT_KEYS (inputs regime) et
    contracts.SCORE_KEYS (scores), + poids appliques, produit pondere (Σ poids·score),
    multiplicateur, seuil, conviction, regime. `fear_greed`/`macro_stale` sont lus de
    la row (injectes par la strategie, docs/11) : None si absents. `close_vs_ema` =
    close_4h - ema50_4h (signe : > 0 => la condition EMA du regime TREND est remplie).
    """
    scores = {key: _py(row.get("s_" + key)) for key in contracts.SCORE_KEYS}
    poids = {key: params.POIDS["s_" + key] for key in contracts.SCORE_KEYS}
    weighted = sum(
        params.POIDS["s_" + key] * float(row["s_" + key])
        for key in contracts.SCORE_KEYS
        if pd.notna(row.get("s_" + key))
    )

    close_4h = row.get("close_4h")
    ema50 = row.get("ema50_4h")
    close_vs_ema = _py(close_4h - ema50) if pd.notna(close_4h) and pd.notna(ema50) else None

    regime_inputs = {
        "adx4h": _py(row.get("adx_4h")),
        "ema50_4h": _py(row.get("ema50_4h")),
        "ema200_4h": _py(row.get("ema200_4h")),
        "close_vs_ema": close_vs_ema,
        "fear_greed": _py(row.get("fear_greed")),
        "macro_stale": _py(row.get("macro_stale")),
        # schema journal v2 (03/08, A4/A5) : etat macro + veto actions sur chaque evaluation,
        # ce qui rend la porte macro ablatable a posteriori (docs/08 §8.1).
        contracts.MACRO_REGIME_COL: _py(row.get(contracts.MACRO_REGIME_COL)),
        contracts.EQUITY_VETO_COL: _py(row.get(contracts.EQUITY_VETO_COL)),
        contracts.EQUITY_VETO_REASON_COL: _py(row.get(contracts.EQUITY_VETO_REASON_COL)),
        # schema journal v3 (04/08, A2) : sens autorise par la macro. C'est LA colonne
        # qui rend le Test 1 de docs/01 mesurable (« la macro donne-t-elle la direction ? »).
        "direction_macro": _py(row.get("direction_macro")),
    }
    return {
        "regime": _py(row.get("regime")),
        "regime_inputs": regime_inputs,
        "scores": scores,
        "poids": poids,
        "produit_pondere": _py(weighted),
        "multiplicateur": _py(row.get("multiplicateur")),
        "seuil": _py(row.get("seuil")),
        "conviction": _py(row.get("conviction")),
    }
