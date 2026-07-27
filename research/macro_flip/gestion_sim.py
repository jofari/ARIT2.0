"""gestion_sim.py — quelle GESTION pour le signal macro ? (analyse pure, zero code produit)

Question de Jonas (2026-07-27) : « les signaux ne sont pas mauvais, maintenant il faut
ameliorer le manage pour une V1 ». Ce script rejoue les episodes du signal macro bougie
par bougie (4h) sous ~20 politiques de gestion et mesure ce que chacune donne.

Le piege a tester : le resultat de MacroFlip tient dans 2 tendances longues (729 j et
748 j). Toute gestion qui coupe tot les DETRUIT. Mais l'inverse est vrai aussi : la
descente de -26,6 % de dec. 2025 est exactement ce qu'une gestion doit eviter. La
question n'est donc pas « gerer ou pas » mais « quelle gestion garde la queue droite
tout en coupant les mauvaises glissades ». On mesure, on ne discute pas.

Modele (honnete, conservateur) :
- decisions de gestion sur CLOTURE 4h ; touche de stop testee sur le low/high intrabar,
  AVANT toute autre regle (conservateur, miroir de policy_sim.py du 19/07) ;
- le stop ne recule jamais ;
- apres une sortie anticipee, on reste EN CASH jusqu'au prochain flip macro (pas de
  re-entree dans l'episode) — c'est la version pessimiste, a garder en tete ;
- funding accru sur le NOTIONNEL COURANT jusqu'a la sortie reelle (une sortie anticipee
  economise donc du funding : c'est un vrai avantage des politiques qui coupent) ;
- frais 0,05 % taker a l'aller et au retour ;
- equite marquee au marche a chaque bougie => le max drawdown est un vrai DD, pas un
  DD sur trades clotures.

Usage :  python research/macro_flip/gestion_sim.py
         python research/macro_flip/gestion_sim.py --spot   # jambes longues en spot
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FUT = REPO / "user_data" / "data" / "binance" / "futures"
MACRO_DIR = REPO / "user_data" / "data" / "macro"
DEBUT, FIN = "2020-01-01", "2026-07-13"

FRACTION = 0.5            # 50 % de l'equite par position (regle Jonas)
FEE = 0.0005              # 0,05 % taker, par cote
ATR_WINDOW = 14           # ATR(14) sur 4h


@dataclass
class Politique:
    nom: str
    sl_atr: float | None = None        # stop initial a k x ATR de l'entree
    trail_atr: float | None = None     # chandelier : extreme favorable -/+ k x ATR
    trail_after: float | None = None   # trailing arme seulement apres +x % de gain
    be_after: float | None = None      # stop a l'entree (BE) des que gain >= x
    giveback: float | None = None      # sortie si on rend > x % du pic de gain
    giveback_arm: float = 0.20         # giveback arme une fois le pic >= +20 %
    timestop_bars: int | None = None   # sortie si gain < 0 apres N bougies 4h


POLITIQUES = [
    Politique("HOLD (actuel, aucune gestion)"),
    # -- stops fixes
    Politique("SL 3xATR", sl_atr=3),
    Politique("SL 5xATR", sl_atr=5),
    Politique("SL 8xATR", sl_atr=8),
    Politique("SL 12xATR", sl_atr=12),
    # -- chandelier pur (le classique du suivi de tendance)
    Politique("chandelier 5xATR", trail_atr=5),
    Politique("chandelier 8xATR", trail_atr=8),
    Politique("chandelier 12xATR", trail_atr=12),
    Politique("chandelier 20xATR", trail_atr=20),
    # -- chandelier arme tard (laisse respirer le debut de tendance)
    Politique("chandelier 8xATR apres +20 %", trail_atr=8, trail_after=0.20),
    Politique("chandelier 12xATR apres +20 %", trail_atr=12, trail_after=0.20),
    Politique("chandelier 12xATR apres +50 %", trail_atr=12, trail_after=0.50),
    Politique("chandelier 20xATR apres +50 %", trail_atr=20, trail_after=0.50),
    # -- giveback (rendre X % du pic)
    Politique("giveback 25 %", giveback=0.25),
    Politique("giveback 33 %", giveback=0.33),
    Politique("giveback 50 %", giveback=0.50),
    # -- breakeven
    Politique("BE apres +20 %", be_after=0.20),
    Politique("BE apres +50 %", be_after=0.50),
    # -- combinaisons plausibles pour une V1
    Politique("SL 8xATR + giveback 33 %", sl_atr=8, giveback=0.33),
    Politique("SL 8xATR + chandelier 12xATR apres +50 %",
              sl_atr=8, trail_atr=12, trail_after=0.50),
    Politique("SL 12xATR + BE +20 % + giveback 50 %",
              sl_atr=12, be_after=0.20, giveback=0.50),
    Politique("time-stop 90 bougies si perdant", timestop_bars=90),
]


# --------------------------------------------------------------------- donnees
def charger():
    ohlc = pd.read_feather(FUT / "BTC_USDT_USDT-4h-futures.feather")
    ohlc["date"] = pd.to_datetime(ohlc["date"], utc=True)
    ohlc = ohlc[(ohlc.date >= DEBUT) & (ohlc.date <= FIN)].reset_index(drop=True)

    tr = ohlc[["high", "low", "close"]].copy()
    prev = tr["close"].shift(1)
    vraie_plage = pd.concat([tr.high - tr.low, (tr.high - prev).abs(),
                             (tr.low - prev).abs()], axis=1).max(axis=1)
    ohlc["atr"] = vraie_plage.rolling(ATR_WINDOW, min_periods=1).mean()

    fr = pd.read_feather(FUT / "BTC_USDT_USDT-1h-funding_rate.feather")
    fr["date"] = pd.to_datetime(fr["date"], utc=True)
    fr = fr.set_index("date")["open"].sort_index()
    # funding accru par bougie 4h : somme des taux tombes dans la bougie x prix courant
    taux_4h = fr.reindex(pd.DatetimeIndex(ohlc.date), method=None).fillna(0.0)
    taux_par_bougie = fr.resample("4h").sum().reindex(pd.DatetimeIndex(ohlc.date)).fillna(0.0)
    ohlc["taux_funding"] = taux_par_bougie.to_numpy()
    del taux_4h
    return ohlc


def episodes(ohlc: pd.DataFrame) -> list[tuple[int, int, int]]:
    """(i_entree, i_sortie, sens) des episodes macro — recalcules, independants du zip."""
    import sys
    sys.path.insert(0, str(REPO / "user_data" / "strategies"))
    from arit_lib import macro_regime, regimes  # noqa: PLC0415

    daily = macro_regime.daily_regimes(macro_regime.load_history(MACRO_DIR))
    df = regimes.attach_macro_regime(ohlc[["date"]].copy(), daily)
    reg = df["macro_regime"].fillna("NEUTRE").to_numpy()

    sens = np.zeros(len(reg), dtype=int)
    courant = 0
    for i, r in enumerate(reg):
        if r == "PORTEUR":
            courant = 1
        elif r == "HOSTILE":
            courant = -1
        sens[i] = courant                      # NEUTRE => on garde le sens en cours

    eps, debut = [], None
    for i in range(len(sens)):
        if sens[i] == 0:
            continue
        if debut is None:
            debut = i
        elif sens[i] != sens[debut]:
            eps.append((debut, i, sens[debut]))
            debut = i
    if debut is not None and debut < len(sens) - 1:
        eps.append((debut, len(sens) - 1, sens[debut]))
    return eps


# --------------------------------------------------------------------- moteur
def rejouer(pol: Politique, ohlc: pd.DataFrame, i0: int, i1: int, sens: int,
            spot: bool) -> tuple[np.ndarray, int]:
    """-> (rendements marques au marche par bougie, index de sortie effectif).

    Le rendement est exprime en fraction du STAKE d'entree. Apres une sortie
    anticipee, le rendement reste fige (on est en cash jusqu'a i1).
    """
    haut = ohlc["high"].to_numpy()
    bas = ohlc["low"].to_numpy()
    clot = ohlc["close"].to_numpy()
    atr = ohlc["atr"].to_numpy()
    taux = ohlc["taux_funding"].to_numpy()

    entree = ohlc["open"].to_numpy()[i0]
    paie_funding = not (spot and sens > 0)     # en spot un long ne paie pas de funding

    courbe = np.zeros(i1 - i0 + 1)
    stop = None
    if pol.sl_atr is not None:
        stop = entree - sens * pol.sl_atr * atr[i0]
    pic_gain = 0.0
    extreme = entree                            # plus haut (long) / plus bas (short) atteint
    funding_cum = 0.0
    sortie = i1

    for k, i in enumerate(range(i0, i1 + 1)):
        # funding accru sur le notionnel courant, ramene en fraction du stake d'entree
        if paie_funding:
            funding_cum += sens * taux[i] * clot[i] / entree

        # 1) touche du stop, testee AVANT tout le reste (conservateur)
        if stop is not None:
            touche = bas[i] <= stop if sens > 0 else haut[i] >= stop
            if touche:
                r = sens * (stop - entree) / entree - funding_cum - 2 * FEE
                courbe[k:] = r
                return courbe, i

        # 2) etat a la cloture
        gain = sens * (clot[i] - entree) / entree - funding_cum
        pic_gain = max(pic_gain, gain)
        extreme = max(extreme, haut[i]) if sens > 0 else min(extreme, bas[i])
        courbe[k] = gain - 2 * FEE

        # 3) sorties sur cloture
        if (pol.giveback is not None and pic_gain >= pol.giveback_arm
                and (pic_gain - gain) >= pol.giveback * pic_gain):
            courbe[k:] = gain - 2 * FEE
            return courbe, i
        if (pol.timestop_bars is not None and k + 1 >= pol.timestop_bars and gain < 0):
            courbe[k:] = gain - 2 * FEE
            return courbe, i

        # 4) remontee du stop (jamais vers le bas)
        nouveau = stop
        if pol.be_after is not None and gain >= pol.be_after:
            nouveau = entree if nouveau is None else (
                max(nouveau, entree) if sens > 0 else min(nouveau, entree))
        if pol.trail_atr is not None and (pol.trail_after is None or pic_gain >= pol.trail_after):
            chand = extreme - sens * pol.trail_atr * atr[i]
            nouveau = chand if nouveau is None else (
                max(nouveau, chand) if sens > 0 else min(nouveau, chand))
        stop = nouveau

    return courbe, sortie


def evaluer(pol: Politique, ohlc: pd.DataFrame, eps, spot: bool) -> dict:
    equite = 10000.0
    courbe_globale = []
    par_episode = []
    n_coupes = 0
    for i0, i1, sens in eps:
        courbe, sortie = rejouer(pol, ohlc, i0, i1, sens, spot)
        courbe_globale.append(equite * (1 + FRACTION * courbe))
        par_episode.append(courbe[-1])
        if sortie < i1:
            n_coupes += 1
        equite *= 1 + FRACTION * courbe[-1]

    eq = np.concatenate(courbe_globale)
    dd = float((1 - eq / np.maximum.accumulate(eq)).max() * 100)
    r = np.array(par_episode)
    sans2 = 10000.0
    for x in np.delete(r, np.argsort(r)[-2:]):
        sans2 *= 1 + FRACTION * x
    return {"politique": pol.nom, "final": equite, "perf_%": equite / 100 - 100,
            "DD_%": dd, "coupes": n_coupes, "gagnantes": int((r > 0).sum()),
            "sans_top2_%": sans2 / 100 - 100}


# ------------------------------------------------------- gestion par la TAILLE, pas la sortie
def _vol_annualisee(ohlc: pd.DataFrame, i: int, jours: int = 30) -> float:
    """Vol realisee annualisee des rendements 4h sur `jours` avant la bougie i."""
    n = jours * 6                                   # 6 bougies 4h par jour
    debut = max(0, i - n)
    r = np.diff(np.log(ohlc["close"].to_numpy()[debut:i + 1]))
    return float(np.std(r) * np.sqrt(6 * 365)) if len(r) > 10 else 0.60


def _scores_macro(ohlc: pd.DataFrame) -> np.ndarray:
    """Somme des 5 scores macro (-5..+5) alignee sur les bougies 4h."""
    import sys
    sys.path.insert(0, str(REPO / "user_data" / "strategies"))
    from arit_lib import contracts, macro_regime  # noqa: PLC0415

    daily = macro_regime.daily_regimes(macro_regime.load_history(MACRO_DIR))
    somme = daily[list(contracts.MACRO_SCORE_KEYS)].sum(axis=1)
    ref = pd.DataFrame({"date": pd.to_datetime(ohlc["date"], utc=True).dt.as_unit("us")})
    droite = pd.DataFrame({
        "date": pd.to_datetime(somme.index, utc=True).floor("D").as_unit("us"),
        "score": somme.to_numpy()}).sort_values("date").reset_index(drop=True)
    return pd.merge_asof(ref, droite, on="date",
                         direction="backward")["score"].fillna(0.0).to_numpy()


TAILLES = {
    "fixe 50 % (actuel)": None,
    "vol-target 35 % (cap 100 %)": ("vol", 0.35, 1.00),
    "vol-target 35 % (cap 75 %)": ("vol", 0.35, 0.75),
    "vol-target 25 % (cap 100 %)": ("vol", 0.25, 1.00),
    "proportionnel au score macro": ("score", 0.0, 1.00),
    "score x vol-target 35 %": ("mixte", 0.35, 1.00),
}


def evaluer_taille(nom, spec, ohlc, eps, scores, spot: bool) -> dict:
    pol = POLITIQUES[0]                             # HOLD : on ne teste QUE la taille
    equite = 10000.0
    courbe_globale, fractions, par_episode = [], [], []
    for i0, i1, sens in eps:
        if spec is None:
            frac = FRACTION
        else:
            mode, cible, plafond = spec
            f_vol = cible / max(_vol_annualisee(ohlc, i0), 0.05)
            f_score = min(abs(scores[i0]) / 5.0, 1.0)
            frac = {"vol": f_vol, "score": f_score, "mixte": f_vol * f_score}[mode]
            frac = float(np.clip(frac, 0.0, plafond))
        fractions.append(frac)
        courbe, _ = rejouer(pol, ohlc, i0, i1, sens, spot)
        courbe_globale.append(equite * (1 + frac * courbe))
        par_episode.append(frac * courbe[-1])
        equite *= 1 + frac * courbe[-1]
    eq = np.concatenate(courbe_globale)
    dd = float((1 - eq / np.maximum.accumulate(eq)).max() * 100)
    r = np.array(par_episode)
    sans2 = 10000.0
    for x in np.delete(r, np.argsort(r)[-2:]):
        sans2 *= 1 + x
    return {"taille": nom, "final": equite, "perf_%": equite / 100 - 100, "DD_%": dd,
            "perf/DD": (equite / 100 - 100) / max(dd, 1e-9),
            "frac_moy": float(np.mean(fractions)), "sans_top2_%": sans2 / 100 - 100}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spot", action="store_true",
                    help="jambes longues en spot (pas de funding) — l'exec recommandee")
    ap.add_argument("--taille", action="store_true",
                    help="comparer les regles de TAILLE (a sorties identiques) au lieu des sorties")
    args = ap.parse_args()

    ohlc = charger()
    eps = episodes(ohlc)
    print(f"{len(eps)} episodes macro, {ohlc.date.iloc[0]:%Y-%m-%d} -> "
          f"{ohlc.date.iloc[-1]:%Y-%m-%d} | execution : "
          f"{'long SPOT + short perp' if args.spot else 'tout perp'}\n")

    pd.set_option("display.width", 200)
    if args.taille:
        scores = _scores_macro(ohlc)
        lignes = [evaluer_taille(n, s, ohlc, eps, scores, args.spot)
                  for n, s in TAILLES.items()]
        out = pd.DataFrame(lignes).sort_values("perf/DD", ascending=False)
        out["final"] = out["final"].round(0)
        for c in ("perf_%", "DD_%", "sans_top2_%"):
            out[c] = out[c].round(1)
        out["perf/DD"] = out["perf/DD"].round(2)
        out["frac_moy"] = out["frac_moy"].round(2)
        print("Regles de TAILLE, sorties inchangees (HOLD jusqu'au flip macro) :\n")
        print(out.to_string(index=False))
        print("\n`perf/DD` = performance / drawdown max — le vrai critere quand on peut "
              "ajuster l'exposition.")
        print("`frac_moy` = fraction moyenne de l'equite engagee (0,50 = la regle actuelle).")
        return

    lignes = [evaluer(p, ohlc, eps, args.spot) for p in POLITIQUES]
    out = pd.DataFrame(lignes).sort_values("perf_%", ascending=False)
    out["final"] = out["final"].round(0)
    for c in ("perf_%", "DD_%", "sans_top2_%"):
        out[c] = out[c].round(1)
    print(out.to_string(index=False))
    print("\n`coupes` = episodes ou la gestion est sortie AVANT le flip macro "
          f"(sur {len(eps)}).")
    print("`sans_top2_%` = performance en retirant les 2 meilleurs episodes "
          "(test de robustesse).")


if __name__ == "__main__":
    main()
