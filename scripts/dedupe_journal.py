"""Deduplique le journal de decision — dette C1 de l'audit du 2026-08-24.

Pourquoi ce script existe
-------------------------
Avant le `run_id` (schema v4, 24/08), `journal._append_line` ouvrait en "a" et le nom de
fichier ne dependait que du JOUR SIMULE. Deux backtests sur la meme periode s'ajoutaient donc
dans les memes fichiers, sans qu'on puisse les separer apres coup.

Mesure du 2026-08-24 (chiffres verifies, cf. la note de methode ci-dessous) :
  - lignes **strictement identiques** : 1 346 / 10 377 = **13,0 %**, presque toutes dans
    `2026-08-04.jsonl` ;
  - `evaluation` en double par (paire, signal_id) : **260 / 4 744 = 5,5 %**, sur 11 fichiers,
    multiplicite maximale **x2** (deux runs superposes, jamais plus).

⚠️ Note de methode — une premiere mesure annoncait 52 % : elle dedupliquait sur
`(event_type, signal_id, ts_utc)`, or `ts_utc` est l'heure d'ECRITURE REELLE, identique pour
les 12 evenements `gestion` d'un meme trade en backtest. Ces lignes legitimes etaient comptees
comme doublons. Le defaut structurel est reel, son ampleur etait surestimee d'un facteur ~9.

Deux passes, et pourquoi il en faut deux
----------------------------------------
1. **Lignes strictement identiques** (meme JSON, octet pour octet) : premiere occurrence
   gardee. Deux evenements legitimes ne peuvent pas etre identiques.
2. **`evaluation` en double par (paire, signal_id)** : une `evaluation` est unique par bougie
   4h et par paire PAR CONSTRUCTION — deux lignes de meme cle sont forcement deux runs. On
   garde la **derniere** (le run le plus recent, donc le code le plus a jour).
   Cette passe est indispensable : deux runs du meme code produisent des flottants qui
   different au dernier bit (`76785.3838203401` vs `76785.38382034007`), donc la passe 1 ne
   les voit pas. Les autres types (`gestion`, `gate_check`, `entry`, `system`) ont
   legitimement plusieurs lignes par signal_id : ils ne sont JAMAIS touches par cette passe.

Les lignes portant un `run_id` (v4+) ne peuvent plus etre confondues entre runs : le `run_id`
fait partie du JSON. Ce script ne sert donc qu'a nettoyer l'heritage d'avant le 24/08.

Securites
---------
- Sans `--apply`, le script ne fait RIEN d'autre qu'afficher ce qu'il ferait (defaut).
- Avec `--apply`, il copie d'abord l'integralite du dossier dans
  `logs/decisions_backup_<horodatage>/` AVANT de reecrire quoi que ce soit.
- Reecriture fichier par fichier via un temporaire + remplacement atomique.

Usage :
  python scripts/dedupe_journal.py                 # rapport seul (aucune ecriture)
  python scripts/dedupe_journal.py --apply         # backup puis deduplication
"""

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DECISIONS = REPO / "user_data" / "logs" / "decisions"
EVALUATION = "evaluation"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dedupe")


def analyser(path: Path) -> tuple[list[str], int, int]:
    """(lignes conservees, doublons exacts, evaluations en double). Ordre du fichier preserve.

    Passe 1 : lignes strictement identiques, premiere occurrence gardee.
    Passe 2 : `evaluation` de meme (paire, signal_id) — unique par construction — derniere
    occurrence gardee (le run le plus recent). Les autres event_type ne sont pas touches.
    """
    vues: set[str] = set()
    brutes: list[str] = []
    doublons = 0
    with open(path, "r", encoding="utf-8") as fh:
        for ligne in fh:
            brut = ligne.rstrip("\n")
            if not brut.strip():
                continue
            if brut in vues:
                doublons += 1
                continue
            vues.add(brut)
            brutes.append(brut)

    decodes = []
    for brut in brutes:
        try:
            decodes.append(json.loads(brut))
        except ValueError:
            decodes.append(None)

    dernier: dict = {}
    for idx, rec in enumerate(decodes):
        if rec is not None and rec.get("event_type") == EVALUATION:
            dernier[(rec.get("pair"), rec.get("signal_id"))] = idx

    a_jeter = {
        idx for idx, rec in enumerate(decodes)
        if rec is not None and rec.get("event_type") == EVALUATION
        and dernier.get((rec.get("pair"), rec.get("signal_id"))) != idx
    }
    gardees = [b for i, b in enumerate(brutes) if i not in a_jeter]
    return gardees, doublons, len(a_jeter)


def reecrire(path: Path, lignes: list[str]) -> None:
    """Remplacement atomique : on n'ecrase l'original qu'une fois le temporaire complet."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        for ligne in lignes:
            fh.write(ligne + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="ecrit reellement (backup complet prealable). Sans ce flag : rapport seul.")
    ap.add_argument("--dir", type=Path, default=DECISIONS)
    args = ap.parse_args(argv)

    base: Path = args.dir
    if not base.is_dir():
        log.error("dossier introuvable : %s", base)
        return 1

    fichiers = sorted(base.glob("*.jsonl"))
    if not fichiers:
        log.info("aucun fichier .jsonl dans %s", base)
        return 0

    plan = []
    total_lignes = total_doublons = total_evals = 0
    for path in fichiers:
        try:
            gardees, doublons, evals = analyser(path)
        except OSError as exc:
            log.error("illisible, ignore : %s (%s)", path.name, exc)
            continue
        total_lignes += len(gardees) + doublons + evals
        total_doublons += doublons
        total_evals += evals
        if doublons or evals:
            plan.append((path, gardees, doublons, evals))

    retire = total_doublons + total_evals
    pct = 100.0 * retire / total_lignes if total_lignes else 0.0
    log.info("%d fichiers - %d lignes - a retirer : %d doublons exacts + %d evaluations de "
             "runs superposes = %d (%.1f %%) dans %d fichiers",
             len(fichiers), total_lignes, total_doublons, total_evals, retire, pct, len(plan))
    for path, gardees, doublons, evals in plan[:10]:
        log.info("   %s : -%d exacts / -%d evaluations -> %d lignes conservees",
                 path.name, doublons, evals, len(gardees))
    if len(plan) > 10:
        log.info("   ... et %d autres fichiers", len(plan) - 10)

    if not plan:
        log.info("rien a faire.")
        return 0
    if not args.apply:
        log.info("RAPPORT SEUL - aucune ecriture. Relancer avec --apply pour dedupliquer.")
        return 0

    horodatage = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    backup = base.parent / f"{base.name}_backup_{horodatage}"
    try:
        shutil.copytree(base, backup)
    except OSError as exc:
        log.error("backup impossible, ON N'ECRIT RIEN : %s", exc)
        return 1
    log.info("backup complet -> %s", backup)

    reecrits = 0
    for path, gardees, _, _ in plan:
        try:
            reecrire(path, gardees)
            reecrits += 1
        except OSError as exc:
            log.error("reecriture echouee sur %s (%s) - original intact", path.name, exc)
    log.info("OK : %d fichiers reecrits, %d lignes supprimees. Backup : %s",
             reecrits, retire, backup.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
