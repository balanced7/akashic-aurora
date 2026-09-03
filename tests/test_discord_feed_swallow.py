"""Feed swallow-class RED pins — the silent-drop door the feed's own docstring disowns
(2026-08-31, fleet Discord robustness review, Heimdall/deepseek lane: outbound delivery).

These pins are RED at commit time. They name two defect classes in core/comm/discord_feed.py
that the existing honesty pins (P1/P2) do NOT cover, because both live in code paths the
D4 drill never exercised:

  S1  THE UNCONFESSED exception sink. pump()'s outer per-stream `try/except Exception:
      continue` wraps `_decode`, `client.xrange`, and `client.hset` alongside the
      injected `post`/`room_post` callables. The seat-lane and global paths confess
      their own failures loud (stderr + discord_feed_post_failed event + `failed`++
      in the seat-lane case), but the OUTER except catches everything they didn't —
      a `_decode` that trips on a non-dict field, a Redis error on hset or xrange —
      and `continue`s with NO stderr line, NO event, NO counter, AND NO cursor
      advance. That is the exact "silent, then retry-forever" shape the module
      docstring says must never happen ("failure is loud exactly once"). The RB-26
      conflict (crash redelivers) is acceptable for a CRASH; it is NOT acceptable
      for a caught-and-swallowed exception.

  S2  THE FAILED-COUNTER ASYMMETRY. Only the seat-lane branch increments `failed`
      and folds it into the outcome ref. A GLOBAL-path failure calls
      _post_failure_loud (loud, evented — the doctor DOES see it via the event
      log) but does NOT increment `failed`, so the pump's own
      `ref="forwarded=X failed=Y"` under-reports on the global surface. The doctor
      is not blind (it counts discard_feed_post_failed / discord_feed_post_failed
      events, not the counter), but the pump's own receipt lies by omission.

Both are defect classes, not design. Land the fix, then flip these pins GREEN via the
receipt comment convention used elsewhere (honest red -> honest green, never delete).

Run:  py -m pytest tests/test_discord_feed_swallow.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import discord_feed as F  # noqa: E402


class _SilentClient:
    """A client whose stream carries an entry _decode cannot parse — the S1 trigger.

    `content` arrives as a Python LIST (not a str), so _decode's `json.loads` on a
    non-string raises TypeError — the exact shape of a malformed envelope field a
    downstream producer could write, and the shape the outer except swallows."""
    def __init__(self):
        self.streams = {
            "bifrost:broadcast": [("100-0", {"frm": "daniil", "kind": "chat",
                                             "content": "old history"})],
            "bifrost:inbox:claude": [],
        }
        self.hash = {}

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


class _Bus:
    ns = "bifrost"
    def __init__(self, client):
        self._client = client
    def known_agents(self):
        return ["claude"]
    def _inbox_key(self, agent):
        return f"bifrost:inbox:{agent}"


@pytest.fixture()
def silent_wired(monkeypatch):
    monkeypatch.setenv("AKASHIC_DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1/g")
    monkeypatch.setenv("AKASHIC_DISCORD_FORUM_WEBHOOK", "https://discord.com/api/webhooks/2/f")
    monkeypatch.setattr(F.DB, "webhook_url", lambda: "https://discord.com/api/webhooks/1/g")
    monkeypatch.setattr(F.ROOMS, "forum_url", lambda: "https://discord.com/api/webhooks/2/f")
    client = _SilentClient()
    return _Bus(client), client


def test_s1_a_stream_beat_failure_must_confess_not_vanish(silent_wired, monkeypatch, capsys):
    """S1: the outer per-stream `except Exception` swallowed everything the inner
    paths didn't confess -- no stderr, no event, no counter. 'Failure is loud
    exactly once' violated on the silence leg.

    VEHICLE CORRECTED 2026-09-02 (a stale bug report is a pointer, not a ticket):
    the audit proposed list-typed `content` as the trigger, but _decode's
    isinstance guard passes non-strings through BY LAW ('leave anything that
    doesn't parse exactly as it came') -- that input raises nowhere. The CLASS is
    real; the honest trigger is any genuine mid-beat explosion, here an xrange
    that dies after tail-init. The fix must confess it to stderr while still
    containing it (other streams keep beating)."""
    bus, client = silent_wired
    F.pump(bus, post=lambda m, **k: None, room_post=lambda m, **k: None)  # tail-init
    client.streams["bifrost:broadcast"].append(
        ("101-0", {"frm": "claude", "kind": "chat", "content": '"survives"'}))

    orig_xrange = client.xrange

    def _boom(key, min="-", count=100):
        if key == "bifrost:inbox:claude":
            raise RuntimeError("mid-beat corpse")
        return orig_xrange(key, min=min, count=count)

    monkeypatch.setattr(client, "xrange", _boom)
    out = F.pump(bus, post=lambda m, **k: None, room_post=lambda m, **k: None)
    err = capsys.readouterr().err

    # leg 1 -- the confession: the swallowed exception must NAME itself on stderr.
    assert "BEAT FAILED" in err or "POST FAILED" in err, (
        "a mid-beat exception was contained with no stderr line -- the outer "
        "except must journal the failure, not absorb it")
    # leg 2 -- the containment: the healthy stream still forwarded this beat.
    assert "forwarded=1" in str(getattr(out, "ref", "") or out), (
        "containment broke: one bad stream starved the rest of the beat")


def test_s2_global_failure_increments_the_failed_counter(silent_wired, monkeypatch, capsys):
    """RED: a GLOBAL-path post failure is loud on stderr and in the event log, but the
    pump's OWN receipt still counts it as `forwarded=1 failed=0` -- the T220/T149
    'claimed delivery' lie, on the global surface. The seat-lane path was fixed for this
    exact class (2026-08-23); the global path still lies because `forwarded += 1` runs
    unconditionally after the attempt, and _forward_global swallows the exception so
    pump() cannot tell the post died."""
    bus, client = silent_wired
    F.pump(bus, post=lambda m, **k: None, room_post=lambda m, **k: None)  # tail-init

    def _dead(*a, **k):
        raise RuntimeError("webhook corpse")
    # global path posts through ROOMS._default_post via _forward_global; kill it.
    # Deliberately do NOT inject `post`/`room_post` callables -- the production feed
    # calls _forward_global + post_to_room, and THIS pin must exercise the real path.
    monkeypatch.setattr(F.ROOMS, "_default_post", _dead)
    client.streams["bifrost:broadcast"].append(
        ("101-0", {"frm": "claude", "kind": "chat", "content": '"a line"'}))
    out = F.pump(bus)
    ref = str(getattr(out, "ref", "") or out)
    err = capsys.readouterr().err
    # HALF 1 (holds today): the global path confesses loud, same as the seat-lane path.
    assert "POST FAILED" in err, (
        "the global path must be loud -- the seat-lane path is, and a dead global "
        "webhook is the same wound")
    # HALF 2 (RED today): the pump's receipt must agree with the confession, not
    # report a dead post as forwarded.
    assert "failed=1" in ref and "forwarded=0" in ref, (
        f"a global post died but the pump's own ref says {ref!r} -- the receipt "
        f"claims a delivery that stderr says did not happen (T220/T149, global surface)")
