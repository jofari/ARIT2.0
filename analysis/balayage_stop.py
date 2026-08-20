r"""Q13 — balayage du couple (distance de stop, cible) en esperance NETTE de frais.

Chantier ouvert le 2026-08-20 apres l'arbitrage de Jonas : « le systeme n'est pas rentable
de base ». Le second cerveau le chiffrait deja (`trading/frais et distance de stop.md`) :
E nette = -0,072 R a la distance actuelle, +0,158 R a demi-distance. La grille d'origine
n'avait que TROIS points et rien entre 0,5 et 1,0.

CE QUE CE SCRIPT FAIT
    Il rejoue chaque signal de la strategie sur l'OHLCV, avec la MEME triple barriere que
    `analysis/dataset.py`, en faisant varier deux choses et rien d'autre :
      - `k`      : multiplicateur de la distance de stop structurelle (docs/03 §3.3) ;
      - `cible`  : le TP, exprime en R de la distance RETENUE (production : 1,5 R).
    Puis il retranche le cout reel : `2 * (frais + slippage) / dist_frac`, ou `dist_frac`
    est la distance APRES application de `k`. C'est le point du chantier — les frais en R
    varient comme `1/k`, donc diviser la distance par deux DOUBLE le cout en R.

CE QU'IL NE FAIT PAS
    Il ne CHOISIT pas `k`. Tracer une courbe d'esperance nette est une mesure ; figer le `k`
    qui maximise le backtest est une hyperopt, donc l'interdit n 5. Le passage de la courbe a
    un parametre de production est une decision de Jonas, prise apres avoir vu la forme ET son
    incertitude. Il ne simule ni sizing, ni slots, ni compounding, ni re-entrees (limite deja
    assumee par `replay_entries.py`).

VERROU B6
    Refuse de tourner sans protocole preenregistre (`research/EXPERIMENTS.jsonl`, id
    `Q13-balayage-distance-stop`). Hold-out B5 jamais lu.

Lancement :
    & C:\Users\jofar\venvs\arit\Scripts\python.exe analysis/balayage_stop.py
"""

import argparse
import json
import pathlib
import sys

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import dataset  # noqa: E402  — construire_df() et _issue() : la MEME geometrie qu'en production
import registre  # noqa: E402  — B6 : le verrou de preenregistrement

from arit_lib import contracts, gestion, params  # noqa: E402

ID_EXP = "Q13-balayage-distance-stop"
SORTIE = REPO / "analysis" / "out" / "balayage_Q13.json"

K_GRILLE = tuple(round(0.30 + 0.05 * i, 2) for i in range(15))   # 0,30 -> 1,00
CIBLES_R = (1.0, 1.5, 2.0, 2.5, 3.0)
K_PROD = 1.00                                     # production : distance structurelle (docs/03)
CIBLE_PROD = dataset.TP1_R                        # production : TP1 = +1,5 R
K_CANDIDATE = 0.50                                # la seule comparaison confirmatoire
HOLDOUT_DEBUT = pd.Timestamp(dataset.HOLDOUT_DEBUT, tz="UTC")
BOOTSTRAP = 2000
ALPHA = 0.10                                      # IC bootstrap 90 %


def cout_r(pair: str, dist_frac: float) -> float:
    """Cout aller-retour exprime en R : `2 * (frais + slippage) / dist_frac`.

    Les frais sont un pourcentage du NOTIONNEL ; en R ils valent donc `cout% / distance%`.
    C'est une identite arithmetique, pas une estimation — et c'est elle qui cree un maximum
    interieur : resserrer le stop monte l'esperance brute et monte le cout, en sens contraire.
    """
    slippage = params.SLIPPAGE_FRAC.get(contracts.spot_pair(pair), 0.0)
    return 2.0 * (params.FEE_TAKER_FRAC + slippage) / dist_frac if dist_frac > 0 else np.nan


def r_net(hauts, bas, closes, heures_fin, entree, sl_struct, sign, k, cible, pair):
    """R net d'un signal pour un couple (k, cible). NaN si la geometrie est inexploitable."""
    risque_struct = sign * (entree - sl_struct)
    if not (np.isfinite(risque_struct) and risque_struct > 0 and entree > 0):
        return np.nan
    risque = risque_struct * k
    sl = entree - sign * risque
    tp = entree + sign * risque * cible
    issue, r_brut, i_fin = dataset._issue(hauts, bas, entree, sl, tp, sign)
    if issue == "TP":
        r_brut = cible                       # `_issue` rend TP1_R en dur : on remet NOTRE cible
    elif issue == "horizon":
        r_brut = float(sign * (closes[i_fin] - entree) / risque)
    return r_brut - cout_r(pair, risque / entree)


def signaux_du_train(pairs, horizon_h):
    """Rejoue les df de production et rend un signal par ligne ou signal_long/short est vrai.

    Le hold-out est ecarte ICI, avant toute mesure : une ligne >= HOLDOUT_DEBUT ne descend
    jamais dans le balayage (B5, garde n 4 de H1).
    """
    macro_daily = _macro_daily()
    lignes = []
    for pair in pairs:
        df = dataset.construire_df(pair, macro_daily)
        dates = pd.to_datetime(df["date"], utc=True)
        positions = np.flatnonzero(df["new_4h"].fillna(False).to_numpy())
        for idx in positions:
            if dates.iloc[idx] >= HOLDOUT_DEBUT:
                continue
            row = df.iloc[idx]
            for sens, sign, col in (("long", 1, "signal_long"), ("short", -1, "signal_short")):
                if not bool(row.get(col)):
                    continue
                fin = min(idx + 1 + horizon_h, len(df))
                fenetre = df.iloc[idx + 1:fin]
                if fenetre.empty:
                    continue
                sl_struct, _, _ = gestion.entry_levels(row, float(row["close"]), sign)
                lignes.append({
                    "pair": pair, "sens": sens, "sign": sign, "date": dates.iloc[idx],
                    "entree": float(row["close"]), "sl_struct": float(sl_struct),
                    "hauts": fenetre["high"].to_numpy(), "bas": fenetre["low"].to_numpy(),
                    "closes": fenetre["close"].to_numpy(),
                })
    return lignes


def _macro_daily():
    from arit_lib import macro_regime
    daily, _ = macro_regime.daily_with_equity_veto(REPO / "user_data" / "data" / "macro")
    return daily


def balayer(signaux, k_grille, cibles):
    """-> DataFrame (k, cible, sens, n, e_net, e_brut, cout_moyen)."""
    lignes = []
    for k in k_grille:
        for cible in cibles:
            for sens in ("long", "short"):
                lot = [s for s in signaux if s["sens"] == sens]
                nets = np.array([r_net(s["hauts"], s["bas"], s["closes"], None, s["entree"],
                                       s["sl_struct"], s["sign"], k, cible, s["pair"])
                                 for s in lot], dtype=float)
                nets = nets[np.isfinite(nets)]
                couts = np.array(
                    [cout_r(s["pair"],
                            s["sign"] * (s["entree"] - s["sl_struct"]) * k / s["entree"])
                     for s in lot], dtype=float)
                lignes.append({"k": k, "cible": cible, "sens": sens, "n": len(nets),
                               "e_net": float(nets.mean()) if len(nets) else np.nan,
                               "cout_moyen": float(np.nanmean(couts)) if len(couts) else np.nan})
    return pd.DataFrame(lignes)


def apparie(signaux, sens, cible):
    """Les R nets de la reference et de la candidate, sur les MEMES signaux (test apparie)."""
    lot = [s for s in signaux if s["sens"] == sens]
    ref, cand = [], []
    for s in lot:
        a = r_net(s["hauts"], s["bas"], s["closes"], None, s["entree"], s["sl_struct"],
                  s["sign"], K_PROD, cible, s["pair"])
        b = r_net(s["hauts"], s["bas"], s["closes"], None, s["entree"], s["sl_struct"],
                  s["sign"], K_CANDIDATE, cible, s["pair"])
        if np.isfinite(a) and np.isfinite(b):
            ref.append(a)
            cand.append(b)
    return np.array(ref), np.array(cand)


def bootstrap_delta(ref, cand, tirages=BOOTSTRAP, graine=20260820):
    """IC de l'ecart APPARIE (meme signal, seule la geometrie de sortie change)."""
    if len(ref) == 0:
        return np.nan, (np.nan, np.nan)
    delta = cand - ref
    rng = np.random.default_rng(graine)
    idx = rng.integers(0, len(delta), size=(tirages, len(delta)))
    moyennes = delta[idx].mean(axis=1)
    return float(delta.mean()), (float(np.quantile(moyennes, ALPHA / 2)),
                                 float(np.quantile(moyennes, 1 - ALPHA / 2)))


def mde(ref, cand, puissance_z=2.8):
    """MDE apparie approche : z * ecart-type des differences / sqrt(n) (alpha 5 %, 1-b 80 %)."""
    if len(ref) < 2:
        return np.nan
    delta = cand - ref
    return float(puissance_z * delta.std(ddof=1) / np.sqrt(len(delta)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", nargs="+", default=list(dataset.PAIRS_DEFAUT))
    ap.add_argument("--horizon-h", type=int, default=dataset.HORIZON_H_DEFAUT)
    ap.add_argument("--out", type=pathlib.Path, default=SORTIE)
    args = ap.parse_args()

    proto = registre.preenregistrement(registre.EXPERIMENTS, ID_EXP)
    print(f"B6 : protocole '{ID_EXP}' en vigueur — essais cumules "
          f"{registre.essais_cumules()}\n    {proto['hypothese'][:100]}...")
    if proto.get("split_autorise") != "train":
        raise SystemExit("B6 : le protocole n'autorise pas ce split.")

    signaux = signaux_du_train(args.pairs, args.horizon_h)
    n_long = sum(1 for s in signaux if s["sens"] == "long")
    print(f"signaux du train : {len(signaux)} ({n_long} longs, {len(signaux) - n_long} shorts)")
    if not signaux:
        raise SystemExit("aucun signal : rien a mesurer.")

    grille = balayer(signaux, K_GRILLE, CIBLES_R)

    resultats = {"id": ID_EXP, "n_signaux": len(signaux), "primaire": {}, "grille": []}
    print(f"\n--- PRIMAIRE : k={K_CANDIDATE} contre k={K_PROD}, cible {CIBLE_PROD} R ---")
    for sens in ("long", "short"):
        ref, cand = apparie(signaux, sens, CIBLE_PROD)
        delta, (bas, haut) = bootstrap_delta(ref, cand)
        seuil = mde(ref, cand)
        verdict = ("RETENUE" if (delta >= 0.10 and bas > 0 and delta > seuil)
                   else "INFIRMEE" if delta <= 0
                   else "INDECIDABLE")
        resultats["primaire"][sens] = {
            "n": len(ref), "e_net_k100": float(ref.mean()) if len(ref) else np.nan,
            "e_net_k050": float(cand.mean()) if len(cand) else np.nan,
            "delta": delta, "ic90": [bas, haut], "mde": seuil, "verdict": verdict}
        print(f"  {sens:<6} n={len(ref):>3} · E nette k=1,00 {ref.mean():+.4f} R · "
              f"k=0,50 {cand.mean():+.4f} R · Delta {delta:+.4f} "
              f"[{bas:+.4f} ; {haut:+.4f}] · MDE {seuil:.4f} => {verdict}")

    print("\n--- DESCRIPTIF : E nette par k, cible 1,5 R (aucun verdict) ---")
    vue = grille[grille["cible"] == CIBLE_PROD]
    for sens in ("long", "short"):
        part = vue[vue["sens"] == sens].sort_values("k")
        trace = " ".join(f"{r.k:.2f}:{r.e_net:+.3f}" for r in part.itertuples())
        print(f"  {sens:<6} {trace}")
        meilleur = part.loc[part["e_net"].idxmax()] if part["e_net"].notna().any() else None
        if meilleur is not None:
            print(f"         maximum de la courbe a k={meilleur.k:.2f} "
                  f"(E nette {meilleur.e_net:+.4f} R, cout moyen {meilleur.cout_moyen:.4f} R)")

    resultats["grille"] = grille.replace({np.nan: None}).to_dict(orient="records")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(resultats, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\necrit : {args.out}")
    print("[!] Ce script ne CHOISIT pas k. La courbe est une mesure ; figer son maximum est "
          "une hyperopt (interdit n 5).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
