"""Envoie un rapport de recherche sur le Discord de Jonas (embed + le .md en piece jointe).

Le webhook vient de DISCORD_WEBHOOK_URL (.env, jamais committe, jamais logge).
Usage :  python scripts/send_discord_report.py research/macro_flip/RAPPORT.md
         python scripts/send_discord_report.py <rapport.md> --titre "..." --resume "..."

L'embed est construit depuis un fichier `<rapport>.discord.json` s'il existe a cote du
.md (titre/couleur/champs) ; sinon on envoie juste le fichier avec un entete minimal.
Ce script ne fait qu'envoyer : il ne modifie ni le rapport ni le repo.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 30
DISCORD_EMBED_DESC_MAX = 4096
DISCORD_FIELD_VALUE_MAX = 1024


def charger_webhook() -> str:
    """.env (ou variable d'env deja posee) -> URL du webhook. Jamais affichee."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        env = REPO / ".env"
        if env.exists():
            for ligne in env.read_text(encoding="utf-8").splitlines():
                if ligne.startswith("DISCORD_WEBHOOK_URL="):
                    url = ligne.split("=", 1)[1].strip()
                    break
    if not url:
        sys.exit("DISCORD_WEBHOOK_URL absent de .env — rien envoye.")
    return url


def tronque(txt: str, limite: int) -> str:
    return txt if len(txt) <= limite else txt[: limite - 3].rstrip() + "..."


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("rapport", help="chemin du .md a envoyer")
    ap.add_argument("--titre", default=None)
    ap.add_argument("--resume", default=None)
    args = ap.parse_args()

    md = Path(args.rapport)
    if not md.is_absolute():
        md = REPO / md
    if not md.exists():
        sys.exit(f"rapport introuvable : {md}")

    meta_file = md.with_suffix(".discord.json")
    meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}

    embed = {
        "title": tronque(args.titre or meta.get("title", md.stem), 256),
        "description": tronque(args.resume or meta.get("description", ""),
                               DISCORD_EMBED_DESC_MAX),
        "color": meta.get("color", 0x5865F2),
    }
    if meta.get("fields"):
        embed["fields"] = [
            {"name": tronque(f["name"], 256),
             "value": tronque(f["value"], DISCORD_FIELD_VALUE_MAX),
             "inline": bool(f.get("inline", False))}
            for f in meta["fields"][:25]
        ]
    if meta.get("footer"):
        embed["footer"] = {"text": tronque(meta["footer"], 2048)}

    payload = {"embeds": [embed], "username": meta.get("username", "ARIT recherche")}
    with open(md, "rb") as fh:
        rep = requests.post(
            charger_webhook(),
            data={"payload_json": json.dumps(payload)},
            files={"files[0]": (md.name, fh, "text/markdown")},
            timeout=TIMEOUT,
        )
    # On n'affiche jamais l'URL (elle est un secret) : seulement le code HTTP.
    if rep.status_code >= 300:
        sys.exit(f"echec Discord (HTTP {rep.status_code}) : {tronque(rep.text, 400)}")
    print(f"envoye : {md.name} ({md.stat().st_size:,} octets) — HTTP {rep.status_code}")


if __name__ == "__main__":
    main()
