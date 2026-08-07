"""M02 — Classification de regime de marche (PDR 04.1/04.2, docs/modules/M02).

Fonctions pures : DataFrame in -> DataFrame + colonnes contractuelles `regime`,
`seuil`, `multiplicateur` (contracts.REGIME_COLUMNS). Aucun reseau, aucun LLM,
aucun import d'un autre module arit_lib (contracts/params seulement, docs/11).

Idee 8 de Jonas (docs/04) : la fonda ne pese jamais dans une somme, elle FIXE le
regime, le seuil d'entree et le multiplicateur de conviction.
"""

import pandas as pd

from arit_lib import contracts, params

# Table ordonnee = miroir exact du PDR 04.1 : le premier predicat vrai gagne, la
# derniere regle (fallback RANGE) matche toujours (ADX fort mais contexte non
# haussier => pas de continuation long en spot). Bornes issues de params
# (docs/README interdit n4). r = df (colonnes Series), m = macro (dict scalaire,
# constant sur le df — docs/04). RISK_OFF est scalaire (macro) => tout ou rien.
REGLES = (
    (
        "RISK_OFF",
        lambda r, m: m["risk_off"] or m["stale"] or m["fear_greed"] < params.FG_RISK_OFF_BELOW,
    ),
    ("RANGE", lambda r, m: r["adx_4h"] < params.ADX_RANGE_BELOW),
    ("TRANSITION", lambda r, m: r["adx_4h"] < params.ADX_TREND_MIN),
    # A2 : TREND = « le marche tend », dans UN SENS OU DANS L'AUTRE. Avant le 04/08 ce
    # predicat n'acceptait que la configuration haussiere, donc une tendance baissiere
    # tombait dans le fallback RANGE et aucun short n'etait structurellement possible.
    # Le SENS est porte a part par `trend_dir` — le long reste filtre par trend_dir >= 0
    # dans cio, donc ce elargissement n'ouvre AUCUN long nouveau (cf. tests M02).
    ("TREND", lambda r, m: trend_dir(r) != 0),
    ("RANGE", lambda r, m: True),  # fallback
)


def trend_dir(r) -> "pd.Series":
    """+1 tendance haussiere · -1 baissiere · 0 indecise (A2, PDR 04.1 elargi).

    Haussier = EMA50 > EMA200 ET close au-dessus de l'EMA50 (definition d'origine du
    predicat TREND) ; baissier = son miroir strict. Toute autre configuration (EMAs et
    prix qui se contredisent) reste 0 et retombe donc dans le fallback RANGE, exactement
    comme avant.
    """
    up = (r["ema50_4h"] > r["ema200_4h"]) & (r["close_4h"] > r["ema50_4h"])
    down = (r["ema50_4h"] < r["ema200_4h"]) & (r["close_4h"] < r["ema50_4h"])
    return up.astype(int) - down.astype(int)

# Macro Analyst V1.1 (06.2) : aliases lisibles des valeurs de params.MACRO_REGIMES.
_PORTEUR, _NEUTRE, _HOSTILE = params.MACRO_REGIMES


def params_for(regime: str, fear_greed: int) -> tuple[float, float]:
    """(seuil, multiplicateur) d'un regime — table PDR 04.2.

    seuil : TREND/TRANSITION depuis params, NaN sinon (RANGE/RISK_OFF = pas d'entree).
    multiplicateur ∈ {MULT_FULL, MULT_REDUCED, MULT_RISK_OFF} : TREND depend de F&G
    (>= FG_MULT_FULL_FROM => plein, sinon reduit), TRANSITION toujours reduit,
    RANGE/RISK_OFF sans engagement (x0 — "—" du tableau 04.2, veto d'entree).
    """
    if regime == "TREND":
        mult = params.MULT_FULL if fear_greed >= params.FG_MULT_FULL_FROM else params.MULT_REDUCED
        return params.SEUIL_TREND, mult
    if regime == "TRANSITION":
        return params.SEUIL_TRANSITION, params.MULT_REDUCED
    return float("nan"), params.MULT_RISK_OFF


def _regime_series(df: pd.DataFrame, macro: dict) -> pd.Series:
    """Applique la table REGLES (premier predicat vrai gagne) -> Series regime."""
    regime = pd.Series(index=df.index, dtype=object)
    remaining = pd.Series(True, index=df.index)
    for name, predicate in REGLES:
        mask = predicate(df, macro)
        if not isinstance(mask, pd.Series):  # predicat scalaire (RISK_OFF, fallback)
            mask = pd.Series(bool(mask), index=df.index)
        take = remaining & mask.fillna(False)  # NaN warm-up => predicat faux (fail-safe)
        regime.loc[take] = name
        remaining.loc[take] = False
    return regime


def classify(df: pd.DataFrame, macro: dict | None = None) -> pd.DataFrame:
    """Ajoute `regime`, `seuil`, `multiplicateur` (contracts.REGIME_COLUMNS).

    Si `contracts.MACRO_REGIME_COL` est present (backtest, Macro Analyst V1.1) il PILOTE
    la fonda : HOSTILE => RISK_OFF (04 §4.1 crit.1, absorbe F&G<25), PORTEUR => x1,0,
    NEUTRE => x0,85 (remplace la logique F&G). Sinon, comportement historique : `macro` =
    dict PDR 06.3 (risk_off/fear_greed/stale) ; None => neutre backtest documente (M02).

    Invariant PDR 04.2 / M02.1 : un changement de regime ne ferme JAMAIS une position
    (seules G1-G7 sortent). Cette fonction ne cree QUE ses 3 colonnes.
    """
    if contracts.MACRO_REGIME_COL in df.columns:
        return _classify_macro(df, macro)
    if macro is None:
        # Neutre backtest (PDR M02) : ni risk_off ni stale, F&G neutre (=> mult plein en TREND).
        macro = {"risk_off": False, "fear_greed": params.FG_NEUTRAL_BACKTEST, "stale": False}
    regime = _regime_series(df, macro)
    fear_greed = macro["fear_greed"]
    resolved = {reg: params_for(reg, fear_greed) for reg in regime.dropna().unique()}
    df["regime"] = regime
    df["seuil"] = regime.map({reg: sm[0] for reg, sm in resolved.items()})
    df["multiplicateur"] = regime.map({reg: sm[1] for reg, sm in resolved.items()})
    df[contracts.TREND_DIR_COL] = trend_dir(df)
    # Sans regime macro V1.1 (chemin live actuel, docs/06 §6.3) il n'y a AUCUNE information
    # directionnelle : le multiplicateur short est celui du long. C'est cio qui refusera le
    # short faute de `direction_macro` — voir la limite documentee en tete de cio.conviction.
    df["multiplicateur_short"] = df["multiplicateur"]
    return df


def donnee_non_fiable(macro: dict | None) -> bool:
    """Le macro_state est-il inexploitable ? (fail-safe live, docs/06 par.6.1/6.3).

    Vrai si `stale`, si `risk_off` (F&G < 25 OU event high-impact dans +/- 30 min), si F&G
    est sous le seuil, OU si les 5 scores 06.2 sont absents. None-safe : `fear_greed` vaut
    None des que la source est tombee (journal._fail_safe_macro), et None n'est pas
    comparable a un int. `macro` None (backtest) => False : rien a juger.

    Le test sur les SCORES est une defense en profondeur, pas un doublon du flag `stale` :
    il ne suppose PAS que le producteur soit a jour. Un macro_state.json ecrit par un
    macro_state.py d'avant la parite porte `stale: false` ET aucun score — regime_now rend
    alors HOSTILE, qui depuis A2 AUTORISE le short. Sans cette clause, ce seul decalage de
    version suffirait a faire shorter le bot en aveugle (constate le 2026-08-07).
    """
    if not macro:
        return False
    if macro.get("stale") or macro.get("risk_off"):
        return True
    if not macro.get(contracts.MACRO_SCORES_KEY):
        return True
    fg = macro.get("fear_greed")
    return fg is not None and fg < params.FG_RISK_OFF_BELOW


def _classify_macro(df: pd.DataFrame, macro: dict | None = None) -> pd.DataFrame:
    """Regime pilote par la colonne macro (backtest ET live depuis la parite A2). Le +0,05
    de seuil NEUTRE est applique par cio (04 §4.2). Retrocompat : sans la colonne,
    classify() reste inchange.

    `macro` = dict 06.3 en live (fail-safe de donnee ci-dessous), None en backtest.

    ⚠️ CHANGEMENT A2 (2026-08-04, hypothese v4 de docs/01) : la macro HOSTILE ne force
    PLUS RISK_OFF. Avant, HOSTILE = « aucune entree » — cohérent avec un bot long-only.
    En v4 la macro donne la DIRECTION : HOSTILE veut dire « short autorise », pas
    « rien a faire ». Le blocage des longs en HOSTILE est desormais porte par
    `direction_macro` dans cio, ce qui est strictement equivalent COTE LONG et debloque
    le short. Le veto actions c6/c7, lui, continue de forcer RISK_OFF : c'est un
    fail-safe de correlation, pas un avis directionnel (cf. question ouverte DECISIONS).
    """
    neutral = {"risk_off": False, "fear_greed": params.FG_NEUTRAL_BACKTEST, "stale": False}
    regime = _regime_series(df, neutral)                    # technique seule (RISK_OFF neutralise)
    macro_col = df[contracts.MACRO_REGIME_COL]
    # Bloc correlation c6/c7 (docs/06 §6.2.1, A4 du 03/08) : veto SEPARE de la somme des 5.
    # Colonne absente (donnees macro sans indice actions) => bloc inoperant, rien ne change.
    if contracts.EQUITY_VETO_COL in df.columns:
        equity_veto = df[contracts.EQUITY_VETO_COL].fillna(False).astype(bool)
        regime = regime.mask(equity_veto, "RISK_OFF")
    # FAIL-SAFE LIVE (parite A2) — meme nature que le veto actions ci-dessus : un doute sur
    # la DONNEE force RISK_OFF, il ne donne jamais d'avis directionnel. Indispensable depuis
    # A2 : `regime_now` renvoie HOSTILE quand macro_state est stale ou sans scores, et
    # HOSTILE ne bloque plus rien — il AUTORISE le short. Sans cette ligne, une source macro
    # tombee ferait shorter le bot en aveugle au lieu de le mettre au repos.
    # `macro` est None en backtest : le comportement backtest est strictement inchange.
    if donnee_non_fiable(macro):
        regime = pd.Series("RISK_OFF", index=df.index)
    is_trend = regime == "TREND"
    porteur = macro_col == _PORTEUR
    hostile = macro_col == _HOSTILE
    base = pd.Series(params.MULT_RISK_OFF, index=df.index, dtype=float)   # RANGE/RISK_OFF => x0
    base = base.mask(regime == "TRANSITION", params.MULT_REDUCED)         # TRANSITION => x0,85
    # Le multiplicateur PLEIN recompense l'accord macro/technique, chacun dans son sens :
    # long plein en PORTEUR, short plein en HOSTILE (miroir exact, A2).
    mult = base.mask(is_trend, params.MULT_REDUCED).mask(is_trend & porteur, params.MULT_FULL)
    mult_short = base.mask(is_trend, params.MULT_REDUCED).mask(is_trend & hostile, params.MULT_FULL)
    df["regime"] = regime
    df["seuil"] = regime.map({"TREND": params.SEUIL_TREND,
                              "TRANSITION": params.SEUIL_TRANSITION}).astype(float)
    df["multiplicateur"] = mult
    df["multiplicateur_short"] = mult_short
    df[contracts.TREND_DIR_COL] = trend_dir(df)
    return df


def attach_macro_regime(df: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Pose les colonnes macro quotidiennes sur les bougies (jointure point-in-time par jour).

    `daily` = sortie macro_regime.daily_regimes (+ daily_equity_veto), index DatetimeIndex,
    deja decale +1 j. Colonnes posees si presentes : contracts.MACRO_REGIME_COL,
    EQUITY_VETO_COL, EQUITY_VETO_REASON_COL (docs/11 §11.3).
    Chaque bougie prend la valeur du dernier jour <= sa date (merge_asof backward, day
    floor) : aucun look-ahead (le regime du jour J est calcule sur <= J-1). `daily` vide
    => colonnes non posees, classify() retombe sur le neutre (retrocompatibilite totale).
    """
    if daily is None or len(daily) == 0 or contracts.MACRO_REGIME_COL not in daily.columns:
        return df
    wanted = [col for col in (contracts.MACRO_REGIME_COL, contracts.EQUITY_VETO_COL,
                              contracts.EQUITY_VETO_REASON_COL) if col in daily.columns]
    # Unites homogenes obligatoires : les feather freqtrade sont en datetime64[ms],
    # les index pandas natifs en [ns] — merge_asof refuse le melange (lecon 13/07).
    right = pd.DataFrame({"date": pd.to_datetime(daily.index, utc=True).floor("D").as_unit("us")})
    for col in wanted:
        right[col] = daily[col].to_numpy()
    right = right.sort_values("date").reset_index(drop=True)
    left = df.copy()
    left["date"] = pd.to_datetime(left["date"], utc=True).dt.as_unit("us")
    ordered = left.sort_values("date")
    merged = pd.merge_asof(ordered[["date"]], right, on="date", direction="backward")
    merged.index = ordered.index
    for col in wanted:
        df[col] = merged[col].reindex(df.index).to_numpy()
    return df
