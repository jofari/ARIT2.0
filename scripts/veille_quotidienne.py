"""Veille quotidienne du dry-run — ecrit un rapport LOCAL, ne poste rien.

Lance par la tache Windows « ARIT veille » chaque jour. Ecrit
research/veille/AAAA-MM-JJ.md : ce que le bot a evalue la veille + l'etat de sante des
quatre dependances qui peuvent le figer en silence.

    python scripts/veille_quotidienne.py            # la veille (defaut)
    python scripts/veille_quotidienne.py 2026-08-07

POURQUOI LOCAL ET SANS DISCORD
- Local : le journal (user_data/logs/decisions/) et les donnees macro sont gitignores,
  donc invisibles d'un agent cloud. Seule une tache sur cette machine peut les lire.
- Sans Discord : Jonas a choisi « alertes critiques seulement » (decision V2 du 07/08).
  Un resume quotidien pousse irait contre ce choix. Les rapports s'empilent, il les lira
  au retour ; le watchdog reste seul a pouvoir l'interrompre.

Lecture seule sur l'etat du bot : ce script ne redemarre rien et ne corrige rien. Il
CONSTATE. Un dry-run non surveille a besoin d'une trace, pas d'un pilote automatique.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import suivi  # noqa: E402  (meme dossier : on reutilise ses lecteurs de journal)

USER_DATA = REPO / "user_data"
# Dossier SEPARE de research/veille/ : ici ce sont des constats locaux, horodates et
# gitignores (ils dependent de user_data/, absent du depot). research/veille/ est reserve
# aux livrables versionnes de la vague 1. Melanger les deux rendrait les PR illisibles.
SORTIE_DIR = REPO / "research" / "veille_locale"

# Miroirs documentes de params.py (ce script ne doit pas importer arit_lib : il tourne
# meme si le paquet est casse, c'est tout l'interet d'une veille).
MACRO_STALE_HOURS = 48        # params.MACRO_STALE_HOURS
HEARTBEAT_MAX_S = 600         # services/watchdog.HEARTBEAT_MAX_S


def _age_h(chemin: Path, maintenant: datetime):
    """Age d'un fichier en heures, ou None s'il est absent."""
    if not chemin.exists():
        return None
    mtime = datetime.fromtimestamp(chemin.stat().st_mtime, tz=timezone.utc)
    return (maintenant - mtime).total_seconds() / 3600.0


def sante(maintenant: datetime) -> list:
    """Les 4 dependances qui peuvent figer le bot SANS erreur. -> [(ok, libelle)]."""
    lignes = []

    # 1. Le bot bat-il encore ? (le watchdog alerte, mais la trace doit rester ici aussi)
    age = _age_h(USER_DATA / "state" / "heartbeat", maintenant)
    if age is None:
        lignes.append((False, "heartbeat ABSENT — le bot n'a jamais demarre"))
    else:
        ok = age * 3600 <= HEARTBEAT_MAX_S
        lignes.append((ok, f"heartbeat : {age * 60:.0f} min "
                            f"({'vivant' if ok else 'BOT MUET'})"))

    # 2. macro_state frais ? Perime => stale => RISK_OFF => plus aucune entree.
    etat_path = USER_DATA / "macro_state.json"
    try:
        etat = json.loads(etat_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        etat = None
    if etat is None:
        lignes.append((False, "macro_state.json illisible — bot au repos"))
    else:
        stale = bool(etat.get("stale"))
        lignes.append((not stale, f"macro_state : stale={stale}, "
                                  f"risk_off={etat.get('risk_off')}, "
                                  f"F&G={etat.get('fear_greed')}"))
        # 3. Les 5 scores 06.2 : absents => HOSTILE => repos (parite A2).
        scores = etat.get("macro_scores") or {}
        lignes.append((bool(scores), f"scores macro : "
                                     f"{scores if scores else 'ABSENTS — bot au repos'}"))

    # 4. Historique macro alimente ? > 48 h => macro_state refuse d'ecrire des scores.
    dxy = _age_h(USER_DATA / "data" / "macro" / "dxy.csv", maintenant)
    if dxy is None:
        lignes.append((False, "historique macro ABSENT — lancer download_macro.py"))
    else:
        lignes.append((dxy <= MACRO_STALE_HOURS,
                       f"historique macro : {dxy:.0f} h (limite {MACRO_STALE_HOURS} h)"))
    return lignes


def rapport(jour: str, maintenant: datetime) -> str:
    recs = suivi._charger(jour)
    res = suivi.resume_jour(recs)
    derniers = suivi.derniere_par_paire(recs)

    out = [f"# Veille ARIT — {jour}", ""]
    out.append(f"_Genere le {maintenant.strftime('%Y-%m-%d %H:%M')} UTC "
               f"par `scripts/veille_quotidienne.py` (lecture seule)._")
    out += ["", "## Sante", ""]
    for ok, libelle in sante(maintenant):
        out.append(f"- {'OK  ' if ok else 'ALERTE'} — {libelle}")

    out += ["", "## Collecte", ""]
    if not recs:
        out.append("**Aucune evaluation ce jour-la.** Si la sante est verte, c'est que le "
                   "bot n'a pas vu de nouvelle cloture 4h ; sinon, voir les alertes.")
    else:
        out.append(f"- {res['evaluations']} evaluations, **{res['signaux']} signal(aux)**")
        out.append(f"- evenements : `{res['types']}`")

    if derniers:
        out += ["", "### Derniere evaluation par paire", "",
                "| paire | regime | conviction | seuil | ecart | macro | sens | decision |",
                "|---|---|---|---|---|---|---|---|"]
        for paire in sorted(derniers):
            r = derniers[paire]
            ri = r.get("regime_inputs", {})
            conv, seuil = r.get("conviction"), r.get("seuil")
            ecart = "-"
            try:
                if conv is not None and seuil is not None and float(seuil) == float(seuil):
                    manque = float(seuil) - float(conv)
                    ecart = "**ATTEINT**" if manque <= 0 else f"il manque {manque:.3f}"
            except (TypeError, ValueError):
                pass
            out.append(f"| {paire} | {r.get('regime')} | {suivi._f(conv)} | "
                       f"{suivi._f(seuil)} | {ecart} | {ri.get('macro_regime')} | "
                       f"{ri.get('direction_macro')} | {r.get('decision')} |")

    sorties = [r for r in recs if r.get("event_type") == "exit"]
    if sorties:
        out += ["", "### Sorties", ""]
        for r in sorties:
            out.append(f"- {r.get('pair')} — cause `{r.get('cause')}`, "
                       f"R={suivi._f(r.get('r_final'))}, "
                       f"MFE={suivi._f(r.get('mfe_r'))}, MAE={suivi._f(r.get('mae_r'))}")

    out += ["", "---", "",
            "Rappel : `no_signal` est le cas NORMAL. Ce rapport CONSTATE, il ne corrige "
            "rien. Le seul dispositif qui peut interrompre Jonas est le watchdog."]
    return "\n".join(out) + "\n"


def main() -> int:
    maintenant = datetime.now(timezone.utc)
    jour = sys.argv[1] if len(sys.argv) > 1 else (
        (maintenant - timedelta(days=1)).strftime("%Y-%m-%d"))

    SORTIE_DIR.mkdir(parents=True, exist_ok=True)
    cible = SORTIE_DIR / f"{jour}.md"
    cible.write_text(rapport(jour, maintenant), encoding="utf-8")
    print(f"ecrit : {cible}")

    # Code retour lisible par le Task Scheduler : 1 = au moins une alerte de sante.
    return 0 if all(ok for ok, _ in sante(maintenant)) else 1


if __name__ == "__main__":
    sys.exit(main())
