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
CONFIG_DRY = REPO / "user_data" / "config.dry.json"
CONFIG_API = REPO / "user_data" / "config.api.json"  # overlay FreqUI, gitignore (docs/07 §7.4)
BOT_TITLE = "ARIT bot (freqtrade dry-run)"
UI_HOST = "127.0.0.1"  # miroir de config.api.example.json — la UI n'est JAMAIS exposee au reseau
UI_PORT = 8080


def bot_command() -> list[str]:
    """Commande du bot : config contractuelle, + overlay FreqUI si disponible.

    L'overlay n'est PAS versionne (il porte username/password/jwt). Sur un clone
    frais il est absent : on lance quand meme (le bot trade correctement sans UI)
    mais on l'annonce — l'absence ne degrade que l'observabilite, pas le trading.
    """
    cmd = [str(FREQTRADE), "trade", "-c", str(CONFIG_DRY)]
    if CONFIG_API.is_file() and CONFIG_API.stat().st_size > 0:
        cmd += ["-c", str(CONFIG_API)]
        print(f"[OK] overlay FreqUI -> http://{UI_HOST}:{UI_PORT}")
    else:
        print(f"[WARN] {CONFIG_API.name} absent ou vide : bot lance SANS FreqUI.\n"
              f"       Creer l'overlay : copier user_data/config.api.example.json "
              f"en user_data/config.api.json et remplacer les 4 secrets.", file=sys.stderr)
    return cmd


def deja_lance(exe_name: str = "freqtrade.exe") -> bool:
    """Un bot tourne-t-il deja ? (garde-fou de la relance automatique au demarrage).

    Ce script est declenche a l'ouverture de session pour survivre aux redemarrages
    Windows Update. Sans ce test, une simple fermeture/reouverture de session lancerait un
    SECOND freqtrade sur la meme config : deux bots ecrivant le meme journal et la meme
    base, donc des donnees de dry-run inexploitables. `tasklist` plutot que psutil : aucune
    dependance nouvelle. En cas de doute (commande indisponible) on repond False, car ne
    PAS relancer un bot mort coute plus cher qu'un doublon improbable.
    """
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return exe_name.lower() in (out.stdout or "").lower()


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
    parser.add_argument("--si-absent", action="store_true",
                        help="ne rien lancer si un freqtrade tourne deja (relance au demarrage)")
    args = parser.parse_args()

    if not PYTHON.exists():
        sys.exit(f"venv introuvable : {PYTHON} (voir BUILD_NOTES)")
    if args.si_absent and deja_lance():
        print("[OK] un freqtrade tourne deja : rien a relancer.")
        return
    for title, cmd in SERVICES:
        launch(title, cmd)
    if not args.no_bot:
        launch(BOT_TITLE, bot_command())
    print("Arret : fermer chaque fenetre (ou Ctrl+C dedans). Le watchdog alerte si le bot meurt.")


if __name__ == "__main__":
    main()
