"""Lanceur ARIT V1 (demande Jonas 2026-07-09) — demarre les 4 process en une commande.

Chaque process s'ouvre dans SA console (ils restent independants : si le bot crashe,
le watchdog survit — docs/02). Ce script ne fait QUE lancer ; zero logique metier.

    & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe start_arit.py           # les 4
    & C:\\Users\\jofar\\venvs\\arit\\Scripts\\python.exe start_arit.py --no-bot  # services seuls
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
VENV = Path(r"C:\Users\jofar\venvs\arit\Scripts")  # voir for claude build/BUILD_NOTES.md
PYTHON = VENV / "python.exe"
FREQTRADE = VENV / "freqtrade.exe"

# (titre de fenetre, commande) — le bot freqtrade en dernier : les services d'abord,
# pour que macro_state.json existe avant la premiere evaluation (docs/11).
SERVICES = [
    ("ARIT macro_state", [str(PYTHON), str(REPO / "services" / "macro_state.py")]),
    ("ARIT discord_bot", [str(PYTHON), str(REPO / "services" / "discord_bot.py")]),
    ("ARIT watchdog", [str(PYTHON), str(REPO / "services" / "watchdog.py")]),
]
BOT = ("ARIT bot (freqtrade dry-run)", [
    str(FREQTRADE), "trade", "-c", str(REPO / "user_data" / "config.dry.json"),
])


def launch(title: str, cmd: list[str]) -> None:
    """Ouvre une console Windows dediee, sans bloquer ce script."""
    try:
        subprocess.Popen(
            cmd, cwd=str(REPO),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        print(f"[OK] {title}")
    except OSError as exc:
        print(f"[ERREUR] {title} : {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lance les 4 process ARIT V1.")
    parser.add_argument("--no-bot", action="store_true",
                        help="lance seulement les 3 services (pas le bot freqtrade)")
    args = parser.parse_args()

    if not PYTHON.exists():
        sys.exit(f"venv introuvable : {PYTHON} (voir BUILD_NOTES)")
    for title, cmd in SERVICES:
        launch(title, cmd)
    if not args.no_bot:
        launch(*BOT)
    print("Arret : fermer chaque fenetre (ou Ctrl+C dedans). Le watchdog alerte si le bot meurt.")


if __name__ == "__main__":
    main()
