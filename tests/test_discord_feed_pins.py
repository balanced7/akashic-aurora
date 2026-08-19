"""Feed pins — the subscription that makes the bridge real, and its one sacred rule.

THE RULE: first contact with a stream tail-initializes and forwards NOTHING. The legacy
plane holds millions of entries; "turn on the feed" must never mean "replay the archive
to Daniil's phone."

Run:  py -m pytest tests/test_discord_feed_pins.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import discord_feed as F  # noqa: E402


class _FakeClient:
    """Just enough Redis: two streams with history, a cursor hash."""
    def __init__(self):
        self.streams = {
            "bifrost:broadcast": [("100-0", {"frm": "daniil", "kind": "chat",
                                             "content": "old history line"})],
            "bifrost:inbox:claude": [("200-0", {"frm": "deepseek", "kind": "reply",
                                                "content": "old reply",
                                                "meta": '{"ask_id": "ask-1"}'})],
        }
        self.hash: dict = {}

    def hgetall(self, key):
        return dict(self.hash)

    def hset(self, key, field, value):
        self.hash[field] = value

    def xrevrange(self, key, count=1):
        s = self.streams.get(key, [])
        return list(reversed(s))[:count]

    def xrange(self, key, min="-", count=100):
        s = self.streams.get(key, [])
        if min.startswith("("):
            floor = min[1:]
            return [e for e in s if e[0] > floor][:count]
        return s[:count]


class _FakeBus:
    ns = "bifrost"

    def __init__(self, client):
        self._client = client

    def known_agents(self):
        return ["claude"]

    def _inbox_key(self, agent):
        return f"bifrost:inbox:{agent}"


@pytest.fixture()
def wired(monkeypatch):
    monkeypatch.setenv("AKASHIC_DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1/g")
    monkeypatch.setenv("AKASHIC_DISCORD_FORUM_WEBHOOK", "https://discord.com/api/webhooks/2/f")
    client = _FakeClient()
    return _FakeBus(client), client


def test_p1_first_contact_forwards_nothing(wired):
    bus, client = wired
    sent = []
    out = F.pump(bus, post=lambda m, **k: sent.append(m),
                 room_post=lambda m, **k: sent.append(m))
    assert out.ok
    assert not sent, (
        "FIRST CONTACT MUST BE SILENT: the archive stays home; cursors "
        "tail-initialize instead of replaying history to a phone")
    assert client.hash["bifrost:broadcast"] == "100-0"
    assert client.hash["bifrost:inbox:claude"] == "200-0"


def test_p2_new_mail_forwards_to_both_and_advances(wired):
    bus, client = wired
    F.pump(bus, post=lambda m, **k: None, room_post=lambda m, **k: None)   # init
    # the REAL envelope (bus.py _emit): content is json.dumps'd with ensure_ascii,
    # so an em-dash rides as a literal — inside a QUOTED json string. The live
    # receipt is on Daniil's phone, 2026-08-18: first-light rendered with wrapping
    # quotes and raw — escapes.
    client.streams["bifrost:inbox:claude"].append(
        ("201-0", {"frm": "deepseek", "kind": "reply",
                   "content": '"fresh verdict \\u2014 with a newline\\nbelow"',
                   "meta": '{"ask_id": "ask-2"}'}))
    glob, rooms = [], []
    out = F.pump(bus, post=lambda m, **k: glob.append(m),
                 room_post=lambda m, **k: rooms.append(m))
    assert out.detail["forwarded"] == 1
    assert len(glob) == 1 and len(rooms) == 1, "every new message offers to BOTH surfaces"
    assert glob[0]["content"] == "fresh verdict — with a newline\nbelow", (
        "content must arrive DECODED — no wrapping quotes, no raw \\u2014, real "
        "newlines; the envelope json-encodes every field and the phone is not a "
        "JSON parser")
    assert glob[0]["meta"]["ask_id"] == "ask-2", "meta must arrive decoded, not as a string"
    assert client.hash["bifrost:inbox:claude"] == "201-0", "cursor advances AFTER the attempt"


def test_p3_unconfigured_is_a_fast_no_op(wired, monkeypatch):
    bus, client = wired
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOK")
    monkeypatch.delenv("AKASHIC_DISCORD_FORUM_WEBHOOK")
    # ... and isolate from the AMBIENT config: the operator's real webhook file
    # landed in .secrets/ on 2026-08-18 and turned this pin red from the outside.
    # A pin must not depend on whether the repo it runs in is wired to Discord.
    monkeypatch.setattr(F.DB, "webhook_url", lambda: "")
    monkeypatch.setattr(F.ROOMS, "forum_url", lambda: "")
    out = F.pump(bus, post=lambda m, **k: (_ for _ in ()).throw(AssertionError),
                 room_post=lambda m, **k: (_ for _ in ()).throw(AssertionError))
    assert not out.ok and "not configured" in str(out.why).lower()


def test_p5_global_feed_posts_as_the_seat_itself(wired, monkeypatch):
    """Rung 2 of person-hood (Daniil, 2026-08-18: 'show up as your own person in
    the chat'): the DEFAULT global path posts with the seat's persona as the
    webhook username — Vandor (claude) speaking, not a narrator quoting him —
    while the manual bridge verbs keep their who-in-body contract untouched."""
    bus, client = wired
    from core.comm import discord_rooms as R
    calls = []
    monkeypatch.setattr(
        R, "_default_post",
        lambda url, content, **kw: calls.append({"url": url, "content": content, **kw}))
    # the registry is empty under conftest isolation (T070) — the persona seam is
    # rooms' contract (its own P8-P10); the FEED's contract is faithful pass-through.
    monkeypatch.setattr(
        R, "persona",
        lambda frm: {"username": "🧵 Vandor (claude)",
                     "avatar_url": "https://example.invalid/vandor.png"})
    F.pump(bus)                                             # init (silent)
    client.streams["bifrost:broadcast"].append(
        ("101-0", {"frm": "claude", "kind": "chat", "content": '"a line of mine"'}))
    F.pump(bus)
    glob = [c for c in calls if "webhooks/1/g" in c["url"]]
    assert glob, "the default global path must post through the persona transport"
    assert glob[0].get("username") == "🧵 Vandor (claude)", (
        "the seat speaks as itself on the global feed — the Species-A law on both "
        "surfaces, wearing whatever icon the seat chose")
    assert glob[0].get("avatar_url", "").endswith("vandor.png"), (
        "the face rides with the name — persona fields pass through whole")
    assert "**claude**" not in glob[0]["content"], (
        "the narrator head leaves the body once the username carries the speaker")


def test_p6_his_own_words_never_bounce_back(wired, monkeypatch):
    """The echo-guard: a message that CAME FROM Discord (the ear stamps
    meta.source=discord) must not be pumped back TO Discord — else every phone
    message returns to its sender wearing the fleet's face, at pump cadence."""
    bus, client = wired
    F.pump(bus, post=lambda m, **k: None, room_post=lambda m, **k: None)   # init
    client.streams["bifrost:broadcast"].append(
        ("102-0", {"frm": "daniil", "kind": "chat",
                   "content": '"hello from my phone"',
                   "meta": '{"source": "discord", "operator": true}'}))
    echoes = []
    F.pump(bus, post=lambda m, **k: echoes.append(m),
           room_post=lambda m, **k: echoes.append(m))
    assert not echoes, (
        "meta.source=discord must short-circuit BEFORE the operator-always-"
        "forwards rule — the override that makes his words loud is exactly the "
        "rule that would make them echo")


def test_p4_feed_exposes_no_inbound_door():
    for banned in ("receive", "poll", "listen", "on_message", "read_channel"):
        assert not hasattr(F, banned), (
            f"discord_feed exposes {banned!r} — the feed reads the BUS and writes "
            f"Discord, never the reverse; phase 2 ships behind R1-R3 or not at all")
