"""Tests M09 - services/discord_bot.py : tail avec rotation de jour, flag ecrit sur le bon
signal_id, digest sur un JSONL de fixture, filtrage anti-spam."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

import discord_bot  # noqa: E402

SID = "BTCUSDT-20260707T120000Z"


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")


# ----------------------------------------------------------------- tail rotation
def test_tail_journal_handles_day_rotation(tmp_path):
    dec = tmp_path
    _write_jsonl(dec / "2026-07-07.jsonl", [{"event_type": "entry", "n": 1}])
    _write_jsonl(dec / "2026-07-08.jsonl", [{"event_type": "exit", "n": 2}])

    days = ["2026-07-07", "2026-07-08"]

    class _Clock:
        def __init__(self):
            self.i = 0

        def __call__(self):
            day = days[min(self.i, len(days) - 1)]
            self.i += 1
            return datetime.fromisoformat(day + "T00:00:00").replace(tzinfo=timezone.utc)

    async def _collect():
        out = []
        async for event in discord_bot.tail_journal(dec, poll_s=0, now_fn=_Clock(),
                                                    iterations=2):
            out.append(event)
        return out

    events = asyncio.run(_collect())
    assert [e["n"] for e in events] == [1, 2]


def test_tail_journal_offset_no_reread(tmp_path):
    dec = tmp_path
    day = "2026-07-07"
    _write_jsonl(dec / f"{day}.jsonl", [{"event_type": "entry", "n": 1}])

    def clock():
        return datetime.fromisoformat(day + "T00:00:00").replace(tzinfo=timezone.utc)

    async def _run():
        gen = discord_bot.tail_journal(dec, poll_s=0, now_fn=clock, iterations=3)
        seen = []
        # premiere passe lit la ligne, on ajoute une 2e ligne apres coup
        async for event in gen:
            seen.append(event["n"])
            if len(seen) == 1:
                _write_jsonl(dec / f"{day}.jsonl", [{"event_type": "exit", "n": 2}])
        return seen

    seen = asyncio.run(_run())
    assert seen == [1, 2]  # pas de re-lecture de la ligne 1


# ----------------------------------------------------------------- veto flag
def test_write_veto_flag_matches_signal_id(tmp_path):
    discord_bot.set_user_data_dir(tmp_path)
    flag = discord_bot.write_veto_flag(SID, motif="trop tot", user="jonas")
    expected = tmp_path / discord_bot.contracts.VETO_DIR / f"{SID}.flag"
    assert flag == expected
    assert expected.exists()
    payload = json.loads(expected.read_text(encoding="utf-8"))
    assert payload["signal_id"] == SID and payload["motif"] == "trop tot"


def test_on_reaction_writes_flag_for_correct_signal(tmp_path, monkeypatch):
    discord_bot.set_user_data_dir(tmp_path)
    monkeypatch.setenv(discord_bot.VETO_USER_ID_ENV, "1")
    discord_bot._intent_messages.clear()
    discord_bot._intent_messages[999] = SID

    reaction = SimpleNamespace(emoji=discord_bot.VETO_EMOJI,
                               message=SimpleNamespace(id=999))
    user = SimpleNamespace(id=1, name="jonas", bot=False)
    asyncio.run(discord_bot.on_reaction(reaction, user))

    assert (tmp_path / discord_bot.contracts.VETO_DIR / f"{SID}.flag").exists()


def test_on_reaction_fail_closed_without_authorized_user(tmp_path, monkeypatch):
    discord_bot.set_user_data_dir(tmp_path)
    monkeypatch.delenv(discord_bot.VETO_USER_ID_ENV, raising=False)
    discord_bot._intent_messages.clear()
    discord_bot._intent_messages[999] = SID
    reaction = SimpleNamespace(emoji=discord_bot.VETO_EMOJI,
                               message=SimpleNamespace(id=999))
    user = SimpleNamespace(id=1, name="jonas", bot=False)
    asyncio.run(discord_bot.on_reaction(reaction, user))
    assert not (tmp_path / discord_bot.contracts.VETO_DIR).exists()


def test_on_reaction_ignores_wrong_emoji(tmp_path):
    discord_bot.set_user_data_dir(tmp_path)
    discord_bot._intent_messages.clear()
    discord_bot._intent_messages[1] = SID
    reaction = SimpleNamespace(emoji="✅", message=SimpleNamespace(id=1))
    user = SimpleNamespace(id=1, name="jonas", bot=False)
    asyncio.run(discord_bot.on_reaction(reaction, user))
    assert not (tmp_path / discord_bot.contracts.VETO_DIR).exists()


# ----------------------------------------------------------------- anti-spam
def test_should_post_filtering():
    assert discord_bot.should_post({"event_type": "entry"}) is True
    assert discord_bot.should_post({"event_type": "exit"}) is True
    assert discord_bot.should_post({"event_type": "evaluation", "decision": "signal"}) is False
    assert discord_bot.should_post({"event_type": "gestion", "rule": "G2"}) is False
    assert discord_bot.should_post({"event_type": "gestion", "rule": "G5"}) is True
    assert discord_bot.should_post(
        {"event_type": "gate_check", "decision": "skip", "failed_gate": "weekly_budget"}) is True
    assert discord_bot.should_post(
        {"event_type": "gate_check", "decision": "skip", "failed_gate": "spread"}) is False
    assert discord_bot.should_post({"event_type": "system", "kind": "cb", "detail": "x"}) is True


# ----------------------------------------------------------------- digest
def test_build_digest_counts(tmp_path):
    discord_bot.set_user_data_dir(tmp_path)
    day = "2026-07-06"
    records = [
        {"event_type": "evaluation", "decision": "no_signal"},
        {"event_type": "evaluation", "decision": "signal"},
        {"event_type": "entry"},
        {"event_type": "exit", "r_final": 1.5},
        {"event_type": "exit", "r_final": -1.0},
        {"event_type": "gate_check", "decision": "skip", "failed_gate": "residual_risk"},
        {"event_type": "gestion", "rule": "G3"},
    ]
    _write_jsonl(tmp_path / discord_bot.contracts.DECISIONS_DIR / f"{day}.jsonl", records)
    digest = discord_bot.build_digest(
        discord_bot._read_day_records(day), day)
    assert "evaluations : 2" in digest
    assert "signaux : 1" in digest
    assert "entrees : 1" in digest
    assert "R cumule : 0.5" in digest
    assert "residual_risk=1" in digest
    assert "G3=1" in digest
