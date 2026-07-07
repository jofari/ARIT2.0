"""M09 - services/discord_bot.py : les yeux de Jonas + le veto canari (docs/08, docs/11).

Process INDEPENDANT. Il ne peut RIEN executer (aucune clef exchange) : il LIT le JSONL de
decision (services propres) et ECRIT des flags de veto - c'est tout (M09 invariant 1).

Fonctions :
- tail_journal(dir)   : suit le JSONL du jour (offset persistant en memoire, gere la rotation).
- format_embed(event) : rend un evenement lisible (Embed si discord dispo, sinon dict).
- post(event)         : filtrage anti-spam (tout n'est pas poste, cf. should_post).
- on_intent(event)    : phase canari - poste l'intention + reaction .
- on_reaction(r, u)   :  de Jonas => ecrit user_data/veto/<signal_id>.flag.
- daily_digest(at)    : lit le JSONL de la veille -> resume Markdown -> post.

Token Discord via env (DISCORD_BOT_TOKEN) ; canal prive ; aucune donnee de clef/solde
detaille dans les posts (M09 invariant 3). discord.py est optionnel a l'import : le coeur
testable (tail, flag, digest) ne depend pas de discord.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# arit_lib vit sous user_data/strategies/ (docs/02) - contracts/params importables.
_ARIT_LIB_DIR = Path(__file__).resolve().parents[1] / "user_data" / "strategies"
if str(_ARIT_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_ARIT_LIB_DIR))

from arit_lib import contracts, params  # noqa: E402

try:  # discord.py optionnel : le coeur testable n'en depend pas.
    import discord
except ImportError:  # pragma: no cover - depend de l'environnement
    discord = None

logger = logging.getLogger(__name__)

TOKEN_ENV = "DISCORD_BOT_TOKEN"          # M09 invariant 3 : token via env
CHANNEL_ID_ENV = "DISCORD_CHANNEL_ID"    # canal prive
VETO_USER_ID_ENV = "DISCORD_VETO_USER_ID"  # seul Jonas peut opposer un veto
VETO_EMOJI = "❌"                    # : reaction de veto (08.4)
_POLL_S = 2.0                            # cadence de tail (continu, docs/11.1)

# Gestion postee (anti-spam) : seules G4-G7 (M09 : G1-G3 restent dans le digest/JSONL).
_POSTED_GESTION_RULES = ("G4", "G5", "G6", "G7")
# Skips postes : gates budget/residuel/veto (M09 filtrage anti-spam).
_POSTED_SKIP_GATES = ("weekly_budget", "residual_risk", "veto_canari")

_USER_DATA_DIR = None
_channel = None                          # canal discord courant (pose au demarrage)
_intent_messages = {}                    # message_id -> signal_id (correlation reaction/veto)


def set_user_data_dir(path) -> None:
    """Fixe le repertoire user_data/ (tests: tmp_path)."""
    global _USER_DATA_DIR
    _USER_DATA_DIR = Path(path)


def _user_data_dir() -> Path:
    return _USER_DATA_DIR or (Path(__file__).resolve().parents[1] / "user_data")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _decisions_dir() -> Path:
    return _user_data_dir() / contracts.DECISIONS_DIR


# ----------------------------------------------------- filtrage anti-spam (M09)
def should_post(event) -> bool:
    """True si l'evenement doit etre poste en continu (docs/08.3 / M09 filtrage).

    Postes : entry, exit, gestion G4-G7, CB & erreurs system, skips budget/residuel/veto.
    NON postes : evaluation (avec ou sans signal), gestion G1-G3, gate_check enter.
    """
    kind = (event or {}).get("event_type")
    if kind in ("entry", "exit"):
        return True
    if kind == "gestion":
        return str(event.get("rule", "")).upper() in _POSTED_GESTION_RULES
    if kind == "system":
        detail = f"{event.get('kind', '')} {event.get('detail', '')}".lower()
        return any(tok in detail for tok in ("error", "erreur", "cb", "circuit", "stale"))
    if kind == "gate_check":
        return (
            event.get("decision") == "skip"
            and event.get("failed_gate") in _POSTED_SKIP_GATES
        )
    return False


# --------------------------------------------------------------- rendu
def _embed_fields(event) -> dict:
    """Champs lisibles d'un evenement (pur, sans discord) - jamais de donnee de solde."""
    kind = (event or {}).get("event_type", "?")
    pair = event.get("pair", "")
    if kind == "entry":
        title = f"ENTREE {pair}"
        desc = (
            f"regime={event.get('regime')} conviction={event.get('conviction')} "
            f"risque={event.get('risk_pct')} SL={event.get('sl_initial')} "
            f"TP1={event.get('tp1')} TP2={event.get('tp2')}"
        )
    elif kind == "exit":
        title = f"SORTIE {pair}"
        desc = (
            f"cause={event.get('cause')} R={event.get('r_final')} "
            f"MAE={event.get('mae_r')} MFE={event.get('mfe_r')}"
        )
    elif kind == "gestion":
        title = f"GESTION {event.get('rule')} {pair}"
        desc = f"{event.get('before')} -> {event.get('after')} (profit_r={event.get('profit_r')})"
    elif kind == "gate_check":
        title = f"SKIP {pair}"
        desc = f"gate={event.get('failed_gate')}"
    elif kind == "system":
        title = f"SYSTEM {event.get('kind')}"
        desc = str(event.get("detail"))
    else:
        title = kind
        desc = ""
    return {"title": title, "description": desc, "signal_id": event.get("signal_id")}


def format_embed(event):
    """Embed discord lisible (ou dict de champs si discord.py indisponible)."""
    fields = _embed_fields(event)
    if discord is None:
        return fields
    return discord.Embed(title=fields["title"], description=fields["description"])


def format_intent_embed(event):
    """Intention d'entree canari : signal_id, regime, scores, conviction, risque, SL/TP, RR."""
    desc = (
        f"signal_id={event.get('signal_id')} regime={event.get('regime')} "
        f"scores={event.get('scores')} conviction={event.get('conviction')} "
        f"risque={event.get('risk_pct')} SL={event.get('sl_initial')} "
        f"TP1={event.get('tp1')} TP2={event.get('tp2')} RR={event.get('rr_dispo')}\n"
        f"Reagis {VETO_EMOJI} dans {params.VETO_WINDOW_MIN_CANARI} min pour opposer un veto."
    )
    if discord is None:
        return {"title": f"INTENTION {event.get('pair', '')}", "description": desc}
    return discord.Embed(title=f"INTENTION {event.get('pair', '')}", description=desc)


# -------------------------------------------------- tail du JSONL (rotation)
async def tail_journal(decisions_dir, poll_s=_POLL_S, now_fn=_now_utc, iterations=None):
    """Suit le JSONL du jour (fichier YYYY-MM-DD.jsonl) et yield chaque nouvelle ligne.

    Offset persistant en memoire par jour => pas de re-lecture. Gere la rotation : au
    changement de jour UTC, bascule sur le nouveau fichier. `iterations=None` = boucle infinie
    (prod) ; un entier borne la boucle (tests). `now_fn` et `poll_s` injectables (tests).
    """
    base = Path(decisions_dir)
    offsets = {}
    count = 0
    while iterations is None or count < iterations:
        day = now_fn().strftime("%Y-%m-%d")
        path = base / f"{day}.jsonl"
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                handle.seek(offsets.get(day, 0))
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("tail_journal: ligne JSON invalide ignoree")
                offsets[day] = handle.tell()
        count += 1
        if iterations is None or count < iterations:
            await asyncio.sleep(poll_s)


# -------------------------------------------------------------- veto (flag)
def write_veto_flag(signal_id, motif=None, user=None) -> Path:
    """Ecrit user_data/veto/<signal_id>.flag (docs/11.3). Existence = veto vu par risk.gate_check.

    Contenu (audit/journal) : signal_id, user, motif, ts_utc. Ne leve jamais.
    """
    veto_dir = _user_data_dir() / contracts.VETO_DIR
    flag = veto_dir / f"{signal_id}{contracts.VETO_FLAG_SUFFIX}"
    payload = {
        "signal_id": signal_id,
        "user": user,
        "motif": motif,
        "ts_utc": _now_utc().replace(microsecond=0).isoformat(),
    }
    try:
        veto_dir.mkdir(parents=True, exist_ok=True)
        flag.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.error("write_veto_flag echec (%s): %s", signal_id, exc)
    return flag


# -------------------------------------------------------- callbacks discord
async def post(event) -> None:
    """Poste un evenement filtre sur le canal courant (no-op si non postable / canal absent)."""
    if _channel is None or not should_post(event):
        return
    try:
        await _channel.send(embed=format_embed(event))
    except Exception as exc:  # pragma: no cover - reseau discord
        logger.error("post echec: %s", exc)


async def on_intent(event) -> None:
    """Phase canari : poste l'intention complete + ajoute la reaction  attendue."""
    if _channel is None:
        return
    try:  # pragma: no cover - reseau discord
        message = await _channel.send(embed=format_intent_embed(event))
        await message.add_reaction(VETO_EMOJI)
        _intent_messages[message.id] = event.get("signal_id")
    except Exception as exc:  # pragma: no cover
        logger.error("on_intent echec: %s", exc)


async def on_reaction(reaction, user) -> None:
    """ de Jonas dans la fenetre => ecrit le flag de veto pour le signal_id correspondant."""
    if user is not None and getattr(user, "bot", False):
        return
    if str(getattr(reaction, "emoji", "")) != VETO_EMOJI:
        return
    allowed = os.environ.get(VETO_USER_ID_ENV)
    if not allowed:  # fail-closed (08.4 : seul Jonas) - sans identite autorisee, aucun veto
        logger.warning("on_reaction: %s non defini, veto refuse (fail-closed)", VETO_USER_ID_ENV)
        return
    if str(getattr(user, "id", "")) != allowed:
        return
    message = getattr(reaction, "message", None)
    signal_id = _intent_messages.get(getattr(message, "id", None))
    if not signal_id:
        return
    write_veto_flag(signal_id, motif="reaction", user=str(getattr(user, "name", user)))


# --------------------------------------------------------------- digest
def _read_day_records(day: str) -> list:
    """Lit toutes les lignes JSONL d'un jour UTC (YYYY-MM-DD), liste vide si absent."""
    path = _decisions_dir() / f"{day}.jsonl"
    records = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return records


def build_digest(records, day: str) -> str:
    """Resume Markdown des dernieres 24 h (docs/08.2) : evaluations, signaux, entrees,
    skips par gate, actions de gestion, PnL du jour (somme R des sorties)."""
    evaluations = signals = entries = exits = 0
    r_total = 0.0
    skips_by_gate = {}
    gestion_by_rule = {}
    for rec in records:
        kind = rec.get("event_type")
        if kind == "evaluation":
            evaluations += 1
            if rec.get("decision") == "signal":
                signals += 1
        elif kind == "entry":
            entries += 1
        elif kind == "exit":
            exits += 1
            value = rec.get("r_final")
            if isinstance(value, (int, float)):
                r_total += value
        elif kind == "gate_check" and rec.get("decision") == "skip":
            gate = rec.get("failed_gate") or "?"
            skips_by_gate[gate] = skips_by_gate.get(gate, 0) + 1
        elif kind == "gestion":
            rule = rec.get("rule") or "?"
            gestion_by_rule[rule] = gestion_by_rule.get(rule, 0) + 1

    lines = [
        f"# ARIT digest {day}",
        f"- evaluations : {evaluations}",
        f"- signaux : {signals}",
        f"- entrees : {entries}",
        f"- sorties : {exits} (R cumule : {round(r_total, 2)})",
    ]
    if skips_by_gate:
        detail = ", ".join(f"{gate}={n}" for gate, n in sorted(skips_by_gate.items()))
        lines.append(f"- skips par gate : {detail}")
    if gestion_by_rule:
        detail = ", ".join(f"{rule}={n}" for rule, n in sorted(gestion_by_rule.items()))
        lines.append(f"- gestion : {detail}")
    return "\n".join(lines)


async def daily_digest(at=params.DIGEST_TIME_UTC) -> None:
    """A l'heure `at` (UTC), genere le digest de la veille et le poste (docs/08.2)."""
    yesterday = (_now_utc() - timedelta(days=1)).strftime("%Y-%m-%d")
    text = build_digest(_read_day_records(yesterday), yesterday)
    if _channel is None:
        logger.info("daily_digest (%s) sans canal:\n%s", at, text)
        return
    try:  # pragma: no cover - reseau discord
        await _channel.send(content=text)
    except Exception as exc:  # pragma: no cover
        logger.error("daily_digest echec: %s", exc)
