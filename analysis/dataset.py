"""G0 — dataset.py : construit HORS-LIGNE le dataset supervise d'ARIT.

Pourquoi ce fichier existe (constat du 2026-08-12) : l'evenement `evaluation` — le SEUL
qui porte le vecteur de features complet (5 scores, ~63 motifs de bougie, regime, macro,
conviction, seuil, RR) — n'est journalise QUE en live (`AritV1.py:61`, `if live:`). Le
dry-run etant a l'arret depuis le 05/08, il en existe **zero** dans tout le projet. Sans
ces vecteurs, B9 (IC des 5 scores) et toute piste ML sont litteralement sans donnees.

Ce script ne touche PAS au code de production : il rejoue le pipeline avec les MEMES
fonctions pures d'`arit_lib` (features -> regimes -> cio), donc sans divergence possible,
et sort ~12 000 evaluations par paire sur 2021-2026 au lieu de ~20 par jour en live.

Zero look-ahead cote FEATURES, garanti par construction :
- le merge 4h/1d passe par `freqtrade.strategy.merge_informative_pair` (le decalage d'une
  bougie informative est celui de la production, pas une reimplementation) ;
- `attach_macro_regime` joint des regimes quotidiens deja decales de +1 j (merge_asof
  backward) ;
- les cibles regardent le futur — c'est leur role — et sont TOUTES prefixees `y_`. Un
  entrainement qui exclut `y_%` ne peut donc pas fuiter, meme par erreur d'inattention.

`split` materialise le hold-out de B5 : rien de ce qui est >= HOLDOUT_DEBUT ne doit servir
a choisir quoi que ce soit. La colonne est ecrite ici pour que l'oubli soit impossible.

Usage :
  & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe analysis/dataset.py
      [--pairs BTC/USDT:USDT ETH/USDT:USDT] [--horizon-h 96] [--db analysis/out/arit.sqlite]
"""

import argparse
import logging
import pathlib
import sqlite3
import sys

import numpy as np
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "user_data" / "strategies"))

from freqtrade.strategy import merge_informative_pair  # noqa: E402

from arit_lib import cio, contracts, features, gestion, macro_regime, params, regimes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("dataset")

DATA_DIR = REPO / "user_data" / "data" / "binance" / "futures"
MACRO_DIR = REPO / "user_data" / "data" / contracts.MACRO_DATA_DIR.split("/")[-1]
DB_DEFAUT = REPO / "analysis" / "out" / "arit.sqlite"

PAIRS_DEFAUT = ("BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "BNB/USDT:USDT")
HORIZON_H_DEFAUT = 96          # 4 j = 24 bougies 4h : au-dela, un setup 4h n'a plus de sens
RET_HORIZONS_H = (24, 96, 168)  # rendements bruts futurs -> IC des scores (B9)
TP1_R = 1.5                     # PDR 03.3 — meme cible que la production (et replay_entries)
HOLDOUT_DEBUT = "2025-01-01"    # B5 — scelle : jamais utilise pour choisir quoi que ce soit
TABLE = "evaluations"
CIBLE_PREFIX = "y_"             # separe les cibles des features, structurellement


def charger_ohlcv(pair: str, tf: str) -> pd.DataFrame:
    """Feather freqtrade futures -> DataFrame date/open/high/low/close/volume, date UTC."""
    nom = f"{pair.replace('/', '_').replace(':', '_')}-{tf}-futures.feather"
    chemin = DATA_DIR / nom
    if not chemin.exists():
        raise FileNotFoundError(f"OHLCV manquant : {chemin}")
    df = pd.read_feather(chemin)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)


def construire_df(pair: str, macro_daily: pd.DataFrame) -> pd.DataFrame:
    """Reproduit AritV1.populate_indicators : 1h merge 4h/1d + scores + regime + conviction.

    Chemin BACKTEST (`live=False`) : le regime macro vient de la colonne quotidienne, pas de
    macro_state.json — lire le fichier ici poserait l'etat d'AUJOURD'HUI sur une bougie de
    2021, c'est-a-dire exactement le look-ahead que le projet s'interdit.
    """
    df = charger_ohlcv(pair, params.TIMEFRAME_BASE)

    inf_4h = charger_ohlcv(pair, params.TIMEFRAME_SETUP)
    inf_4h = features.add_indicators(inf_4h)
    inf_4h = features.find_pivots(inf_4h)
    inf_4h = features.track_structure(inf_4h)
    inf_4h = features.candle_patterns(features.sr_levels(inf_4h))

    inf_1d = features.add_indicators(charger_ohlcv(pair, params.TIMEFRAME_CONTEXT))

    df = merge_informative_pair(df, inf_4h, params.TIMEFRAME_BASE, params.TIMEFRAME_SETUP,
                                ffill=True)
    df = merge_informative_pair(df, inf_1d, params.TIMEFRAME_BASE, params.TIMEFRAME_CONTEXT,
                                ffill=True)

    df = features.compute_all(df)
    df = regimes.attach_macro_regime(df, macro_daily)
    return cio.conviction(regimes.classify(df, None))


def _plat(valeur):
    """Scalaire pandas/numpy -> type Python SQLite-compatible (NaN/NaT -> None)."""
    if valeur is None:
        return None
    if isinstance(valeur, (np.bool_, bool)):
        return int(valeur)
    if isinstance(valeur, (np.integer, int)):
        return int(valeur)
    if isinstance(valeur, (np.floating, float)):
        nombre = float(valeur)
        return None if np.isnan(nombre) else nombre
    if pd.isna(valeur):
        return None
    return str(valeur)


def _issue(hauts, bas, entree, sl, tp, sign) -> tuple[str, float, int]:
    """Triple barriere sur une fenetre : (issue, r_final, index de fin).

    Bougie ambigue (SL et TP touches dans la meme) => SL, choix pessimiste identique a
    `analysis/replay_entries.py`. Aucune regle de gestion (G1-G7) n'est simulee : on mesure
    la GEOMETRIE seule, qui est l'hypothese d'edge signee (H1, docs/01 v4).
    """
    if sign > 0:
        touche_sl, touche_tp = bas <= sl, hauts >= tp
    else:
        touche_sl, touche_tp = hauts >= sl, bas <= tp
    i_sl = int(np.argmax(touche_sl)) if touche_sl.any() else None
    i_tp = int(np.argmax(touche_tp)) if touche_tp.any() else None
    if i_tp is not None and (i_sl is None or i_tp < i_sl):
        return "TP", TP1_R, i_tp
    if i_sl is not None:
        return "SL", -1.0, i_sl
    return "horizon", float("nan"), len(hauts) - 1


def etiqueter(df: pd.DataFrame, idx: int, horizon_h: int) -> dict:
    """Cibles `y_*` d'une evaluation : triple barriere long ET short + rendements bruts.

    Les deux sens sont etiquetes sur CHAQUE evaluation, y compris quand la strategie n'aurait
    pris ni l'un ni l'autre : c'est ce qui rend le dataset utilisable pour de la
    meta-labellisation (« ce signal valait-il d'etre pris ? ») et pas seulement pour rejouer
    les decisions deja prises — lesquelles sont trop peu nombreuses pour apprendre quoi que
    ce soit (79 trades sur 5 ans).
    """
    row = df.iloc[idx]
    entree = float(row["close"])
    fin = min(idx + 1 + horizon_h, len(df))
    fenetre = df.iloc[idx + 1:fin]
    cibles: dict = {}

    closes = df["close"].to_numpy()
    for h in RET_HORIZONS_H:
        j = idx + h
        cibles[f"{CIBLE_PREFIX}ret_{h}h"] = (
            float(closes[j] / entree - 1.0) if j < len(closes) and entree else None)

    if fenetre.empty or not np.isfinite(entree):
        return cibles
    hauts, bas = fenetre["high"].to_numpy(), fenetre["low"].to_numpy()
    # Passage par pandas obligatoire : apres le merge informative la colonne `date` est en
    # dtype object, que numpy refuse de soustraire a un datetime64.
    heures = ((pd.to_datetime(fenetre["date"], utc=True) - pd.Timestamp(row["date"]))
              .dt.total_seconds().to_numpy() / 3600.0)

    for sens, sign in (("long", 1), ("short", -1)):
        sl, tp1, _ = gestion.entry_levels(row, entree, sign)
        if not (np.isfinite(sl) and np.isfinite(tp1)):
            continue
        risque = sign * (entree - sl)          # > 0 dans les deux sens (contracts.direction_sign)
        if risque <= 0:
            continue
        issue, r_final, i_fin = _issue(hauts, bas, entree, sl, tp1, sign)
        if issue == "horizon":
            r_final = float(sign * (fenetre["close"].to_numpy()[i_fin] - entree) / risque)
        extreme = hauts.max() if sign > 0 else bas.min()   # meilleur prix offert, avant tout stop
        cibles.update({
            f"{CIBLE_PREFIX}issue_{sens}": issue,
            f"{CIBLE_PREFIX}label_{sens}": {"TP": 1, "SL": -1, "horizon": 0}[issue],
            f"{CIBLE_PREFIX}r_{sens}": _plat(r_final),
            f"{CIBLE_PREFIX}h_to_issue_{sens}": _plat(heures[i_fin]),
            f"{CIBLE_PREFIX}mfe_r_{sens}": _plat(sign * (extreme - entree) / risque),
            f"sl_{sens}": _plat(sl),
            f"tp1_{sens}": _plat(tp1),
        })
    return cibles


def extraire(pair: str, macro_daily: pd.DataFrame, horizon_h: int) -> list[dict]:
    """Une ligne par cloture 4h (garde `new_4h`, docs/11 §11.2) : features + cibles."""
    df = construire_df(pair, macro_daily)
    positions = np.flatnonzero(df["new_4h"].fillna(False).to_numpy())
    logger.info("%s : %d bougies 1h -> %d evaluations", pair, len(df), len(positions))

    lignes = []
    for idx in positions:
        row = df.iloc[idx]
        exp = cio.explain(row)
        ts_4h = row.get("date_4h")
        if ts_4h is None or pd.isna(ts_4h):      # warm-up du merge : pas encore de bougie 4h
            ts_4h = row["date"]
        ligne = {
            "pair": pair,
            "ts_utc": row["date"].isoformat(),
            "signal_id": contracts.make_signal_id(pair, pd.Timestamp(ts_4h).to_pydatetime()),
            "split": "holdout" if row["date"] >= pd.Timestamp(HOLDOUT_DEBUT, tz="UTC")
                     else "train",
            "close": _plat(row["close"]),
            "regime": exp["regime"],
            "seuil": exp["seuil"],
            "multiplicateur": exp["multiplicateur"],
            "produit_pondere": exp["produit_pondere"],
            "conviction": exp["conviction"],
            "conviction_short": _plat(row.get("conviction_short")),
            "rr_dispo": _plat(row.get("rr_dispo")),
            "rr_dispo_short": _plat(row.get("rr_dispo_short")),
            "trend_dir": _plat(row.get(contracts.TREND_DIR_COL)),
            # Ce que la strategie AURAIT decide : la cible de toute meta-labellisation.
            "signal_long": _plat(row.get("signal_long")),
            "signal_short": _plat(row.get("signal_short")),
        }
        ligne.update({f"s_{k}": v for k, v in exp["scores"].items()})
        ligne.update({f"s_{k}_short": _plat(row.get(f"s_{k}{contracts.SHORT_SUFFIX}"))
                      for k in contracts.SCORE_KEYS})
        ligne.update({k: _plat(v) for k, v in exp["regime_inputs"].items()})
        ligne.update({k: _plat(row.get(k)) for k in ("close_4h", "atr_4h", "atr_1h",
                                                     "nearest_res_4h", "nearest_sup_4h")})
        ligne.update({str(k): _plat(row[k]) for k in df.columns
                      if str(k).startswith(contracts.CDL_PREFIX)})
        ligne.update(etiqueter(df, int(idx), horizon_h))
        lignes.append(ligne)
    return lignes


def _type_sql(valeur) -> str:
    if isinstance(valeur, bool):
        return "INTEGER"
    if isinstance(valeur, int):
        return "INTEGER"
    if isinstance(valeur, float):
        return "REAL"
    return "TEXT"


def ecrire_sqlite(lignes: list[dict], db: pathlib.Path) -> None:
    """Ecrit/remplace la table `evaluations`. Schema deduit des lignes (features evolue).

    Table remplacee et non completee : ce dataset est integralement reconstructible depuis
    l'OHLCV, donc l'ajouter en incremental ne ferait que creer des doublons silencieux si
    une constante de `params.py` bouge entre deux runs.
    """
    if not lignes:
        raise SystemExit("aucune evaluation extraite — rien a ecrire")
    colonnes: dict[str, str] = {}
    for ligne in lignes:                       # union des cles : une paire peut manquer un cdl
        for cle, valeur in ligne.items():
            if valeur is not None and cle not in colonnes:
                colonnes[cle] = _type_sql(valeur)
    for ligne in lignes:
        for cle in ligne:
            colonnes.setdefault(cle, "TEXT")

    db.parent.mkdir(parents=True, exist_ok=True)
    noms = list(colonnes)
    cites = [f'"{n}"' for n in noms]
    ddl = ", ".join(f"{c} {colonnes[n]}" for c, n in zip(cites, noms))
    insert = (f'INSERT INTO {TABLE} ({", ".join(cites)}) '
              f'VALUES ({", ".join("?" * len(noms))})')
    # Index poses seulement si leurs colonnes existent : sinon un CREATE INDEX sur une
    # colonne absente ferait echouer l'ecriture ENTIERE (les 56 000 lignes) pour un index.
    index = {"idx_pair_ts": ("pair", "ts_utc"), "idx_split": ("split",),
             "idx_signal": ("signal_id",)}
    try:
        with sqlite3.connect(db) as conn:
            conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
            conn.execute(f"CREATE TABLE {TABLE} (id INTEGER PRIMARY KEY AUTOINCREMENT, {ddl})")
            conn.executemany(insert, [[ligne.get(n) for n in noms] for ligne in lignes])
            for nom, cols in index.items():
                if all(c in colonnes for c in cols):
                    conn.execute(f"CREATE INDEX {nom} ON {TABLE} ({', '.join(cols)})")
    except sqlite3.Error as exc:
        raise SystemExit(f"ecriture SQLite impossible : {exc}") from exc
    logger.info("%d lignes x %d colonnes -> %s", len(lignes), len(noms), db)


def resume(db: pathlib.Path) -> None:
    """Constats BRUTS, sans interpretation : de quoi voir si la collecte a du sens."""
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        for titre, sql in (
            ("evaluations par paire et split",
             f"SELECT pair, split, COUNT(*) n FROM {TABLE} GROUP BY pair, split"),
            ("signaux effectifs (ce que la strategie aurait pris)",
             f"SELECT split, SUM(signal_long) longs, SUM(signal_short) shorts, COUNT(*) n "
             f"FROM {TABLE} GROUP BY split"),
            ("issue geometrique des LONGS signales (train seulement)",
             f"SELECT y_issue_long issue, COUNT(*) n FROM {TABLE} "
             f"WHERE signal_long=1 AND split='train' GROUP BY y_issue_long"),
            ("issue geometrique de TOUTES les evaluations (train, long)",
             f"SELECT y_issue_long issue, COUNT(*) n FROM {TABLE} "
             f"WHERE split='train' GROUP BY y_issue_long"),
        ):
            print(f"\n-- {titre}")
            for r in conn.execute(sql):
                print("   " + " · ".join(f"{k}={r[k]}" for k in r.keys()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", nargs="+", default=list(PAIRS_DEFAUT))
    ap.add_argument("--horizon-h", type=int, default=HORIZON_H_DEFAUT)
    ap.add_argument("--db", type=pathlib.Path, default=DB_DEFAUT)
    args = ap.parse_args()

    macro_daily, evenements = macro_regime.daily_with_equity_veto(MACRO_DIR)
    for kind, detail in evenements:
        logger.warning("macro %s : %s", kind, detail)
    if macro_daily is None or macro_daily.empty:
        logger.warning("aucun regime macro quotidien — le dataset sera sans colonne macro")

    lignes: list[dict] = []
    for pair in args.pairs:
        try:
            lignes.extend(extraire(pair, macro_daily, args.horizon_h))
        except (FileNotFoundError, KeyError, ValueError) as exc:
            logger.error("%s ignoree : %s", pair, exc)

    ecrire_sqlite(lignes, args.db)
    resume(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
