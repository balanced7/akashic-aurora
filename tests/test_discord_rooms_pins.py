"""Room-router acceptance pins — his breakouts become chatrooms, outbound only
(RED committed alone, M3).

COMMISSIONED, verbatim (2026-08-18, off to work): "bifrost have a discord native
expression that I can chat in, with global chat and each specific breakout or
ask being visible as chatrooms!" — the CHAT-IN half is phase 2 and does NOT
ship here; these pins cover the rooms half and pin the door shut behind it.

Design: research/in-flight/discord-native-rooms-design-2026-08-18.md.
Neighbour law: copy discord_bridge's guards, not just its shape.

Run:  py -m pytest tests/test_discord_rooms_pins.py -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _mod():
    try:
        from core.comm import discord_rooms
    except ImportError:
        pytest.fail("core.comm.discord_rooms missing — the room router is not built (RED)")
    return discord_rooms


class _Spy:
    """Injectable transport: records every call, returns a fake thread id."""
    def __init__(self):
        self.calls = []

    def __call__(self, url, content, *, thread_id=None, thread_name=None, username=None):
        self.calls.append({"url": url, "content": content, "thread_id": thread_id,
                           "thread_name": thread_name, "username": username})
        return "789012345678"          # the thread id Discord would mint


@pytest.fixture()
def env(tmp_path, monkeypatch):
    reg = tmp_path / "discord_rooms.json"
    monkeypatch.setenv("AKASHIC_DISCORD_ROOMS_REGISTRY", str(reg))
    monkeypatch.setenv("AKASHIC_DISCORD_FORUM_WEBHOOK", "https://discord.com/api/webhooks/1/x")
    return reg


def _msg(kind="reply", frm="claude", ask="ask-42", body="fence counter body"):
    return {"id": "1787000000000-0", "kind": kind, "frm": frm,
            "content": body, "meta": {"ask_id": ask, "title": "T362 fence"}}


# ---- P1: first post for an ask CREATES its room ------------------------------
def test_p1_first_post_creates_the_room(env):
    spy = _Spy()
    out = _mod().post_to_room(_msg(), post=spy)
    assert out.ok, out
    assert len(spy.calls) == 1
    c = spy.calls[0]
    assert c["thread_name"], "first post must create the thread (thread_name set)"
    assert c["thread_id"] is None
    reg = json.loads(env.read_text(encoding="utf-8"))
    assert reg["ask-42"]["thread_id"] == "789012345678", (
        "the minted thread id must land in the registry — it is a new address "
        "dialect and unrecorded addresses are how dialects fracture (T362 census)")


# ---- P2: second post REUSES the room -----------------------------------------
def test_p2_second_post_reuses_the_room(env):
    m = _mod()
    spy = _Spy()
    m.post_to_room(_msg(), post=spy)
    m.post_to_room(_msg(body="second beat"), post=spy)
    c2 = spy.calls[1]
    assert c2["thread_id"] == "789012345678" and c2["thread_name"] is None, (
        "a known ask must post into its existing thread, never mint a twin room")


# ---- P3: seats post as Callsign (vendor) — the Species-A kill ----------------
def test_p3_username_teaches_both_names(env):
    spy = _Spy()
    _mod().post_to_room(_msg(frm="deepseek"), post=spy)
    assert spy.calls[0]["username"] == "Heimdall (deepseek)", (
        "the surface Daniil reads must teach BOTH names on every line "
        "(Heimdall's name-collision scan, Species A)")
    spy2 = _Spy()
    _mod().post_to_room(_msg(frm="somebot"), post=spy2)
    assert spy2.calls[0]["username"] == "somebot", "unknown agents keep their bare id"


# ---- P4: the kind allowlist is inherited, not forked -------------------------
def test_p4_unknown_kind_does_not_forward(env):
    spy = _Spy()
    out = _mod().post_to_room(_msg(kind="trace"), post=spy)
    assert not out.ok and not spy.calls, (
        "rooms inherit the bridge's allowlist — the firehose stays out, and a "
        "second hand-kept kind list is the fork this repo keeps paying for")


# ---- P5: the twin no-inbound-door guard --------------------------------------
def test_p5_rooms_expose_no_inbound_door():
    m = _mod()
    for banned in ("receive", "poll", "listen", "on_message", "read_channel"):
        assert not hasattr(m, banned), (
            f"discord_rooms exposes {banned!r} — phase 2 must not arrive by accident; "
            f"it ships behind the R1-R3 gate or not at all")


# ---- P6: absent is not broken ------------------------------------------------
def test_p6_unconfigured_is_a_state_not_a_failure(env, monkeypatch):
    monkeypatch.delenv("AKASHIC_DISCORD_FORUM_WEBHOOK")
    out = _mod().post_to_room(_msg(), post=_Spy())
    assert not out.ok and "not configured" in str(out.why).lower(), (
        "an unconfigured room webhook is opt-in-and-unset, distinguishable from "
        "a delivery failure (T170 vocabulary, carried from the bridge)")


# ---- P7: redaction rides along -----------------------------------------------
def test_p7_secrets_are_redacted_in_rooms(env):
    spy = _Spy()
    _mod().post_to_room(_msg(body="here is sk-abcdefghijklmnop leaking"), post=spy)
    assert "sk-abcdefghijklmnop" not in spy.calls[0]["content"], (
        "rooms publish to a third party exactly like the bridge — redact() is "
        "not optional equipment")
