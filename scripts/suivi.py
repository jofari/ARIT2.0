"""Ce que le bot a ENVISAGE, pas seulement ce qu'il a pris (journal 08.1).

    python scripts/suivi.py                 # aujourd'hui
    python scripts/suivi.py 2026-08-07      # un jour donne
    python scripts/suivi.py --jours 7       # les 7 derniers jours

FreqUI montre les positions OUVERTES. Elle ne montre pas les setups evalues puis
refuses — or c'est la que vit l'information : le bot evalue chaque cloture 4h et decline
la quasi-totalite. Sans cette vue, un dry-run ressemble a « il ne se passe rien », alors
qu'il se passe une decision par paire et par bougie 4h.

Lecture seule : n'ecrit rien, ne touche ni au bot ni au repo.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
JOURNAL_DIR = REPO / "user_data" / "logs" / "decisions"


def _charger(jour: str) -> list:
    """Enregistrements d'un jour (JSONL). Fichier absent => liste vide, jamais d'exception."""
    fichier = JOURNAL_DIR / f"{jour}.jsonl"
    if not fichier.exists():
        return []
    recs = []
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            recs.append(json.loads(ligne))
        except ValueError:      # ligne tronquee (ecriture en cours) : on l'ignore
            continue
    return recs


def _f(valeur, defaut="-"):
    """Nombre lisible ; None/NaN -> tiret (le seuil vaut NaN hors TREND/TRANSITION)."""
    if valeur is None:
        return defaut
    try:
        f = float(valeur)
    except (TypeError, ValueError):
        return str(valeur)
    return defaut if f != f else f"{f:.3f}"      # f != f => NaN


def resume_jour(recs: list) -> dict:
    """Compte les evenements par type + les decisions d'evaluation."""
    par_type = defaultdict(int)
    for r in recs:
        par_type[r.get("event_type", "?")] += 1
    evals = [r for r in recs if r.get("event_type") == "evaluation"]
    return {
        "types": dict(par_type),
        "evaluations": len(evals),
        "signaux": sum(1 for r in evals if r.get("decision") == "signal"),
    }


def derniere_par_paire(recs: list) -> dict:
    """Derniere evaluation de chaque paire (les enregistrements sont deja chronologiques)."""
    out = {}
    for r in recs:
        if r.get("event_type") == "evaluation" and r.get("pair"):
            out[r["pair"]] = r
    return out


def _ligne_paire(paire: str, r: dict) -> str:
    ri = r.get("regime_inputs", {})
    conv, seuil = r.get("conviction"), r.get("seuil")
    ecart = "-"
    try:
        if conv is not None and seuil is not None and float(seuil) == float(seuil):
            manque = float(seuil) - float(conv)
            ecart = "ATTEINT" if manque <= 0 else f"il manque {manque:.3f}"
    except (TypeError, ValueError):
        pass
    return (f"  {paire:<18} {str(r.get('regime')):<12} "
            f"conv {_f(conv):<7} seuil {_f(seuil):<7} {ecart:<16} "
            f"macro {str(ri.get('macro_regime')):<8} "
            f"sens {str(ri.get('direction_macro')):<6} -> {r.get('decision')}")


def _gates(recs: list) -> dict:
    """Gates ayant refuse une entree (event 'gate_check' : ce qui a bloque un SIGNAL)."""
    refus = defaultdict(int)
    for r in recs:
        if r.get("event_type") == "gate_check" and r.get("decision") != "ok":
            refus[r.get("gate_fautif") or r.get("failed") or "?"] += 1
    return dict(refus)


def afficher(jour: str) -> int:
    recs = _charger(jour)
    print(f"\n=== {jour} " + "=" * 52)
    if not recs:
        print("  aucun enregistrement (le bot n'a rien evalue ce jour-la)")
        return 0

    res = resume_jour(recs)
    print(f"  {res['evaluations']} evaluations | {res['signaux']} signal(aux) | "
          f"evenements : {res['types']}")

    derniers = derniere_par_paire(recs)
    if derniers:
        print("\n  Derniere evaluation par paire :")
        for paire in sorted(derniers):
            print(_ligne_paire(paire, derniers[paire]))

    refus = _gates(recs)
    if refus:
        print(f"\n  Entrees bloquees par un garde-fou : {refus}")

    sorties = [r for r in recs if r.get("event_type") == "exit"]
    if sorties:
        print(f"\n  Sorties : {len(sorties)}")
        for r in sorties[-5:]:
            print(f"    {r.get('pair')} cause={r.get('cause')} R={_f(r.get('r_final'))}")
    return res["evaluations"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jour", nargs="?", help="AAAA-MM-JJ (defaut : aujourd'hui, UTC)")
    ap.add_argument("--jours", type=int, default=1, help="nombre de jours a remonter")
    args = ap.parse_args()

    if not JOURNAL_DIR.exists():
        print(f"journal introuvable : {JOURNAL_DIR}", file=sys.stderr)
        return 2

    fin = (datetime.strptime(args.jour, "%Y-%m-%d").replace(tzinfo=timezone.utc)
           if args.jour else datetime.now(timezone.utc))
    total = 0
    for i in range(args.jours - 1, -1, -1):
        total += afficher((fin - timedelta(days=i)).strftime("%Y-%m-%d"))

    print("\n" + "=" * 60)
    print(f"  {total} evaluations sur la periode.")
    print("  Rappel : une evaluation par paire et par cloture 4h. `decision: no_signal`")
    print("  est le cas NORMAL - le bot decline la quasi-totalite des setups.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
