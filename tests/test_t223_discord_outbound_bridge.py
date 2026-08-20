"""T223 RED: outbound Discord bridge -- the fleet becomes watchable from a phone.

Daniil, leaving for work 2026-08-07: "research and build out what it will take for me to be
able to interact with akashic aurora via discord".

DESIGN: research/in-flight/discord-bridge-design-2026-08-07.md. The finding that shrinks it:
this is `bifrost_console.py` with a different I/O surface, not an integration. Phase 1 is
OUTBOUND ONLY -- ~80% of the value (visibility while away) at ~0% of the risk, because a
Discord webhook URL is write-only and opens no command channel.

EVERY PIN HERE RUNS WITHOUT A NETWORK. The transport is injected, so the selection rules, the
redaction and the failure semantics are all testable offline -- and a bridge whose tests need
a live webhook is a bridge nobody runs the tests for.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import discord_bridge as DB  # noqa: E402


class FakePost:
    """Captures posts instead of making them. Also the phase-1 safety argument in code form:
    nothing in this suite can reach Discord even by accident."""

    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def __call__(self, url, content):
        if self.fail:
            raise OSError("simulated network failure")
        self.sent.append((url, content))
        return True


def _msg(kind="handoff", frm="deepseek", content="a thing happened", to="claude"):
    return {"kind": kind, "frm": frm, "to": to, "content": content}


# ------------------------------------------------------------------ selection
def test_only_allowlisted_kinds_go_out():
    """An ALLOWLIST, never a denylist. A denylist silently leaks every kind added after it
    was written -- and this repo adds kinds regularly (31 at last count, T177)."""
    assert DB.should_forward(_msg(kind="handoff"))
    assert DB.should_forward(_msg(kind="blocker"))
    assert not DB.should_forward(_msg(kind="trace")), \
        "trace is the firehose -- forwarding it makes the channel unreadable within an hour"
    assert not DB.should_forward(_msg(kind="some_kind_invented_next_week")), \
        "an unknown kind must default to NOT forwarded; that is what allowlist means"


def test_a_human_message_always_goes_out():
    """Whatever the kind, a message from a person is the one thing worth a phone buzz."""
    assert DB.should_forward({"kind": "chat", "frm": "daniil", "content": "hi"})


# ------------------------------------------------------------------ redaction
def test_secrets_are_redacted_before_they_leave_the_machine():
    """Posting to Discord PUBLISHES to a third party, retained and indexed regardless of
    later deletion. A bus body can carry a key, a token or a webhook URL; that must not be
    the way it escapes."""
    body = ("failed with DEEPSEEK_API_KEY=sk-abc123def456ghi789 and "
            "https://discord.com/api/webhooks/123/AbCdEfGhIjK")
    out = DB.redact(body)
    assert "sk-abc123def456ghi789" not in out
    assert "AbCdEfGhIjK" not in out
    assert "REDACTED" in out, "redaction must be VISIBLE, not silent deletion"


def test_redaction_keeps_the_message_readable():
    """Over-redaction makes the channel useless, which is how a safety feature gets turned
    off. The surrounding text must survive."""
    out = DB.redact("T219 landed at cbae99e -- the scorer fork is closed")
    assert "cbae99e" in out and "scorer fork" in out


# ------------------------------------------------------------------ transport
def test_a_post_carries_who_and_what():
    post = FakePost()
    DB.forward(_msg(), url="https://example.invalid/hook", post=post)
    assert len(post.sent) == 1
    _, content = post.sent[0]
    assert "deepseek" in content and "handoff" in content


def test_oversize_bodies_post_multiple_parts_never_over_the_cap():
    """Discord caps a message at 2000 chars. T368 (shipped under the t364 test filename,
    before the registry spoke): a long body posts as N whole-line parts instead of one
    truncated clip — a `bifrost-fetch` handle is a shell command the reader (Daniil on a
    phone) cannot run, so multi-part posting replaces it."""
    long_body = "x" * 5000
    post = FakePost()
    DB.forward({**_msg(content=long_body), "id": "1786094136458-0"},
               url="https://example.invalid/hook", post=post)
    assert len(post.sent) > 1, "an oversize body must post multiple parts, not one clip"
    for _, content in post.sent:
        assert len(content) <= 2000, "Discord will reject any part over 2000 outright"
        assert "bifrost-fetch" not in content, \
            "the recovery handle is a shell command a phone cannot run -- N parts replace it"


def test_a_dead_webhook_never_breaks_the_bus():
    """The bridge is a LISTENER on a substrate that must not care about it. A Discord outage
    must not raise into a caller, and must not silently pretend success either."""
    out = DB.forward(_msg(), url="https://example.invalid/hook", post=FakePost(fail=True))
    assert out.ok is False and out.why, "a failed post must say why"


def test_no_url_is_a_configuration_state_not_a_failure():
    """Absent config is not an error -- the bridge is opt-in and most seats will never set it.
    But it must be DISTINGUISHABLE from a delivery failure (T170's one vocabulary)."""
    out = DB.forward(_msg(), url="", post=FakePost())
    assert out.ok is False
    assert "not configured" in out.why.lower()


# ------------------------------------------------------------------ phase-2 boundary
def test_the_outbound_bridge_exposes_no_inbound_door():
    """PHASE 1 IS OUTBOUND ONLY, and that is a security property, not a roadmap note. An
    inbound path is a prompt-injection channel into a fleet that holds a shell, a repo and a
    budget; it does not ship until the R1-R3 identity gate is built and pinned."""
    for banned in ("receive", "poll", "listen", "on_message", "read_channel"):
        assert not hasattr(DB, banned), (
            f"discord_bridge exposes {banned!r} -- phase 2 must not arrive by accident")
