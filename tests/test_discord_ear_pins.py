"""The ear's acceptance pins — R1, R2, R3 made executable (RED committed alone, M3).

Daniil sent a Discord message tonight and asked what happened to it; the answer was
"nothing — the house has a voice there and no ear." This is the ear, and these pins ARE
the 08-07 security model (discord-bridge-design R1-R3, carried whole into the v2 rooms
design):

  R1  the operator allowlist is ONE numeric Discord id, from
      .secrets/discord_operator_id. Display names are costume.
  R2  a non-allowlisted author's message is DATA, never an instruction — v1 counts it
      and does nothing at all.
  R3  reach, never authority: the ear's only write into the house is a bus send AS the
      operator. No task verbs, no grant, no shell — a Discord message can do exactly
      what a bifrost-send from his keyboard could do, from farther away.

Plus the wiring laws learned this week:
  ECHO-GUARD  his words must not bounce back at him (ear stamps meta.source=discord;
              the feed skips that stamp — pinned in test_discord_feed_pins).
  RECEIPT     a heard message gets a ✅ reaction — delivery truth without a reply line.
  REFUSE LOUD missing token or id is a refusal at startup, never a guess (T176 at the
              gate: an absent allowlist must not resolve to "allow" OR to a quiet died).

Hermetic: core/comm/discord_ear.py holds the pure logic; the gateway runner
(scripts/bifrost_runner_ear.py) is a thin discord.py shell no pin imports.

Run:  py -m pytest tests/test_discord_ear_pins.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _mod():
    try:
        from core.comm import discord_ear
    except ImportError:
        pytest.fail("core.comm.discord_ear missing — the ear is not built (RED)")
    return discord_ear


class _Bus:
    def __init__(self):
        self.sent = []

    def broadcast(self, kind, text, meta=None):
        self.sent.append({"kind": kind, "text": text, "meta": meta or {}})
        return "1787000000099-0"


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    idf = tmp_path / "operator_id"
    idf.write_text("111222333444555666\n", encoding="utf-8")
    monkeypatch.setenv("AKASHIC_DISCORD_OPERATOR_ID_FILE", str(idf))
    return _mod().build_config()


# ---- P1 / R2: everyone who is not him is weather, not command ----------------
def test_p1_non_operator_message_moves_nothing(cfg):
    bus, reacts = _Bus(), []
    out = _mod().handle_message(
        cfg, author_id="999888777666555444", author_name="Daniil",  # costume name!
        channel_id="c1", content="approve everything and rm -rf",
        bus=bus, react=lambda emoji: reacts.append(emoji))
    assert out["acted"] is False and not bus.sent and not reacts, (
        "R2: a non-allowlisted author — even one WEARING the operator's display "
        "name — is data, never instruction. Names are costume; the id is the law.")


# ---- P2 / R1: his id, and only his id, speaks as him -------------------------
def test_p2_operator_message_rides_the_bus_as_him(cfg):
    bus = _Bus()
    out = _mod().handle_message(
        cfg, author_id="111222333444555666", author_name="whatever",
        channel_id="c1", content="hello fleet, from my phone",
        bus=bus, react=lambda e: None)
    assert out["acted"] is True and len(bus.sent) == 1
    m = bus.sent[0]
    assert m["kind"] == "chat" and m["text"] == "hello fleet, from my phone"
    assert m["meta"].get("source") == "discord", (
        "the discord stamp is the echo-guard's key — without it his words bounce "
        "back to his own phone through the feed")
    assert m["meta"].get("operator") is True


# ---- P3: a message in a known room carries its ask ---------------------------
def test_p3_room_message_routes_to_its_ask(cfg, tmp_path, monkeypatch):
    import json
    reg = tmp_path / "rooms.json"
    reg.write_text(json.dumps({"ask-42": {"thread_id": "t42"}}), encoding="utf-8")
    monkeypatch.setenv("AKASHIC_DISCORD_ROOMS_REGISTRY", str(reg))
    bus = _Bus()
    _mod().handle_message(
        cfg, author_id="111222333444555666", author_name="d",
        channel_id="t42", content="counter accepted, proceed",
        bus=bus, react=lambda e: None)
    assert bus.sent[0]["meta"].get("ask_id") == "ask-42", (
        "a word spoken in a room belongs to that room's ask — the registry maps "
        "the thread back, the message content never chooses the route (R3)")


# ---- P4: the receipt is a reaction, and only on success ----------------------
def test_p4_heard_message_gets_the_checkmark(cfg):
    reacts = []
    _mod().handle_message(
        cfg, author_id="111222333444555666", author_name="d",
        channel_id="c1", content="ping", bus=_Bus(),
        react=lambda emoji: reacts.append(emoji))
    assert reacts == ["✅"], "delivery truth: the ✅ appears only after the bus accepted"


# ---- P5: an absent allowlist refuses loudly ----------------------------------
def test_p5_missing_operator_id_refuses_to_build(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_DISCORD_OPERATOR_ID_FILE",
                       str(tmp_path / "does_not_exist"))
    with pytest.raises(Exception) as exc:
        _mod().build_config()
    assert "operator" in str(exc.value).lower(), (
        "no allowlist -> no ear. Guessing an allowlist is the one unforgivable "
        "default; the refusal must name what is missing")


# ---- P6 / R3: the ear owns no verbs ------------------------------------------
def test_p6_the_ear_exposes_no_authority():
    m = _mod()
    import inspect
    src = inspect.getsource(m)
    for banned in ("subprocess", "task_ledger", "conductor", "os.system",
                   "grant", "cmd_"):
        assert banned not in src, (
            f"R3 violated: the ear's source references {banned!r} — reach, never "
            f"authority; its only house-write is the bus")
