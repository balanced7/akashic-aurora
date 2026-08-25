"""Remote bridge v1 pins — the durable outbox + the INBOUND gate (Akashic↔Akashic).

Design: docs/library/design/remote-bifrost-bridge-design.md. v0.1 shipped the outbound
transport (tests/test_remote_relay_pins.py, 9 green). This file pins the two halves v0.1
promised but did not ship, and both are the SIBLING of a virtue that shipped alone:

  A. DURABILITY — remote_relay's module docstring guarantees "a durable outbox cursor
     records the last-acked id ... replayed on the next tick" and push() points at
     "def tick below". Neither existed. The virtue that shipped was NEVER RAISE INTO A BUS
     CALLER; the sibling that did not was NEVER LOSE THE MESSAGE. Design §5 risk #3 named
     this exactly and said the mitigation "must ship with, not after, the transport."

  B. ADMISSION — the inbound door. v0.1 shipped verify() (HMAC + replay window) and stopped,
     correctly, because inbound is a prompt-injection door into a fleet holding a shell, a
     repo and an API budget. verify() proves THE SENDER HOLDS THE KEY. It proves nothing
     about who the message CLAIMS to be from, and nothing about what the message asks for.

The two traps this file exists to hold shut, both found by reading v0.1 rather than by a
failure — write them down before they are re-derived expensively:

  TRAP 1 — `frm` IS COSTUME. discord_bridge.should_forward() returns True for ANY sender in
  its operator list regardless of kind. Outbound that is right (we are choosing which of OUR
  messages to send). Inbound it is an impersonation bypass: the payload's `frm` is written by
  the peer, so a peer holding the key could claim `frm: daniil` and post any kind at all.
  HMAC authenticates the CHANNEL, never the CLAIM. Inbound provenance is assigned by us from
  the verified route, never read from the payload. (discord_inbound R1: "display names are
  costume — the allowlist is ONE numeric id".)

  TRAP 2 — THE TWO LISTS ANSWER DIFFERENT QUESTIONS. FORWARD_KINDS contains `halt` and
  `nudge`, because it answers "is this worth buzzing the operator's phone?" The bridge must
  answer "is this safe to accept from another fleet?" — and design §3.2 says a remote peer
  CANNOT halt or steer us. Inheriting the Discord list to avoid drift silently imported two
  control verbs. The fix is not a second drifting copy: it is an EXPLICIT bridge allowlist
  plus a pin that fails if any control kind ever appears in it, so drift is caught by a red
  test rather than by a remote peer halting the fleet.

Every pin runs offline. No listener, no network, no Redis.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402

OUT_SECRET = b"test-outbound-secret"
IN_SECRET = b"test-inbound-secret"


class FakePost:
    """Injected transport. `fail` flips mid-test so a pin can prove a message SURVIVES a
    failure and is delivered by a later tick — the whole point of an at-least-once outbox."""

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def __call__(self, url, envelope):
        if self.fail:
            raise OSError("simulated network failure")
        self.calls.append((url, envelope))
        return {"ok": True}


@pytest.fixture()
def outbox(tmp_path, monkeypatch):
    """A private outbox file per test — durability is pinned by re-reading from disk."""
    p = tmp_path / "outbox.jsonl"
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(p))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", "https://peer.invalid/xfer")
    return p


def _msg(kind="chat", **kw):
    m = {"frm": "claude", "kind": kind, "content": "hello", "id": "m-1"}
    m.update(kw)
    return m


# ===========================================================================================
# A. THE DURABLE OUTBOX — "a message that is sent is delivered eventually" (design §3.4)
# ===========================================================================================

def test_failed_push_retains_the_message_for_replay(outbox):
    """THE PIN THE MODULE DOCSTRING ALREADY PROMISED. v0.1's existing pin only asserts a
    failed push does not PRETEND success; nothing asserted the message survived. Reporting a
    loss honestly and preventing it are different virtues, and only the first shipped."""
    RR.enqueue(_msg(), secret=OUT_SECRET)
    dead = FakePost(fail=True)
    RR.tick(post=dead, secret=OUT_SECRET)

    assert RR.pending(), "a failed push dropped the message — the outbox is fire-and-forget"

    live = FakePost()
    RR.tick(post=live, secret=OUT_SECRET)
    assert len(live.calls) == 1, "the retained message was never replayed after recovery"
    assert not RR.pending(), "a delivered message stayed pending — it will be sent forever"


def test_outbox_survives_process_restart(outbox):
    """Durable means ON DISK, not in a module global. A crash between enqueue and delivery is
    the exact case the outbox exists for — an in-memory queue is a comment, not a guarantee."""
    RR.enqueue(_msg(), secret=OUT_SECRET)
    RR.tick(post=FakePost(fail=True), secret=OUT_SECRET)

    assert outbox.exists(), "nothing was written to disk — the outbox cannot survive a crash"

    RR._reset_cache()  # simulate a fresh process reading the same file
    assert RR.pending(), "the outbox did not survive a restart"


def test_enqueue_dedupes_by_stable_id(outbox):
    """RB-26 house law at the bridge boundary: a redelivered copy is never acted on twice.
    The outbox is where a redelivery becomes one message rather than two."""
    RR.enqueue(_msg(), secret=OUT_SECRET)
    RR.enqueue(_msg(), secret=OUT_SECRET)

    live = FakePost()
    RR.tick(post=live, secret=OUT_SECRET)
    assert len(live.calls) == 1, "the same id enqueued twice was sent twice"


def test_disallowed_kind_never_enters_the_outbox(outbox):
    """Refuse at the DOOR, not at the tick. A message that can never be sent must not sit in
    the outbox being retried forever — that is a queue that grows without bound and a log
    that cries wolf until nobody reads it."""
    out = RR.enqueue(_msg(kind="trace"), secret=OUT_SECRET)
    assert not out.ok, "the firehose was accepted into the outbox"
    assert not RR.pending(), "a permanently-undeliverable message is parked in the outbox"


def test_tick_is_ordered_and_a_stuck_head_does_not_block_the_tail(outbox):
    """Two messages, the first permanently refused by the peer. The second must still get
    out. A head-of-line block turns one bad message into a total outage — the failure mode
    that makes people delete the queue and go back to fire-and-forget."""
    RR.enqueue(_msg(id="m-1"), secret=OUT_SECRET)
    RR.enqueue(_msg(id="m-2"), secret=OUT_SECRET)

    class HeadFails:
        def __init__(self):
            self.calls = []

        def __call__(self, url, envelope):
            body = json.loads(base64.b64decode(envelope["body"]))
            if body["id"] == "m-1":
                raise OSError("this one always fails")
            self.calls.append(body["id"])
            return {"ok": True}

    post = HeadFails()
    RR.tick(post=post, secret=OUT_SECRET)
    assert "m-2" in post.calls, "a stuck head blocked the tail of the outbox"


# ===========================================================================================
# B. THE INBOUND GATE — "not everyone has access" (design §3.3), the dangerous half
# ===========================================================================================

def _envelope(msg, secret=IN_SECRET, sent_at=None):
    """Build a wire envelope as a PEER would — including a hostile one, which is the point:
    the gate must be exercised with payloads we did not write."""
    payload = {
        "v": 1,
        "id": str(msg.get("id") or "x-1"),
        "frm": str(msg.get("frm") or "?"),
        "kind": str(msg.get("kind") or "?"),
        "content": str(msg.get("content") or ""),
        "sent_at": int(sent_at if sent_at is not None else time.time()),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"body": base64.b64encode(body).decode("ascii"), "sig": RR.sign(body, secret)}


def test_inbound_is_inert_until_keyed(monkeypatch):
    """Absent key must not resolve to 'allow' (the obvious sin) and must not resolve to a
    guess (discord_inbound's build_config refusal). Inert-until-keyed IS the access gate."""
    out = RR.accept(_envelope(_msg()), secret=b"")
    assert not out.ok
    assert "secret" in (out.why or "").lower()


def test_forged_signature_is_refused():
    out = RR.accept(_envelope(_msg(), secret=b"wrong-key"), secret=IN_SECRET)
    assert not out.ok, "a payload signed with the wrong key was admitted"


def test_stale_payload_is_refused():
    """Replay protection. A captured envelope stays valid forever without a time window."""
    old = _envelope(_msg(), sent_at=int(time.time()) - 10_000)
    out = RR.accept(old, secret=IN_SECRET)
    assert not out.ok, "a replayed envelope from hours ago was admitted"


def test_claimed_frm_cannot_impersonate_the_operator():
    """TRAP 1. The HMAC proves the peer holds the key. It proves NOTHING about the `frm` the
    peer typed into its own payload. Provenance is ASSIGNED from the verified route."""
    out = RR.accept(_envelope(_msg(frm="daniil")), secret=IN_SECRET, peer="serge-dsh")
    assert out.ok, "a legitimate chat message was refused"

    delivered = RR.last_admitted()
    assert delivered["frm"] != "daniil", "a remote peer successfully impersonated the operator"
    assert "serge-dsh" in delivered["frm"], (
        "admitted mail must carry the VERIFIED route as its provenance, so a reader can "
        "never mistake a remote claim for a local one")


def test_operator_claim_does_not_bypass_the_kind_allowlist():
    """TRAP 1, sharper. should_forward() short-circuits to True for an operator sender. If
    the inbound gate reuses it, claiming `frm: daniil` smuggles ANY kind past the allowlist."""
    out = RR.accept(_envelope(_msg(frm="daniil", kind="halt")), secret=IN_SECRET,
                    peer="serge-dsh")
    assert not out.ok, "an operator-costumed sender walked a control kind through the gate"


def test_no_control_kind_can_cross_the_bridge():
    """TRAP 2. Design §3.2: a remote peer CANNOT halt or steer our fleet. `halt` and `nudge`
    are both in FORWARD_KINDS because that list answers a different question."""
    for kind in ("halt", "nudge", "pause", "interrupt", "steer", "launcher/spawn"):
        out = RR.accept(_envelope(_msg(kind=kind)), secret=IN_SECRET, peer="serge-dsh")
        assert not out.ok, f"control kind {kind!r} crossed the bridge"


def test_bridge_allowlist_contains_no_control_kind():
    """The DRIFT GUARD, and the reason this is a pin rather than a shared constant. The two
    allowlists answer different questions, so they must be allowed to differ — but if anyone
    ever adds a control verb to the bridge list, this goes red here instead of going red as
    a remote peer halting the fleet."""
    control = {"halt", "nudge", "pause", "interrupt", "steer", "resume", "drain", "kill"}
    leaked = control & set(RR.BRIDGE_KINDS)
    assert not leaked, f"control kinds leaked onto the bridge allowlist: {sorted(leaked)}"


def test_unknown_kind_is_refused_not_denylisted():
    """Allowlist never denylist: a kind invented after this line was written must NOT cross."""
    out = RR.accept(_envelope(_msg(kind="kind_invented_next_tuesday")), secret=IN_SECRET,
                    peer="serge-dsh")
    assert not out.ok


def test_inbound_content_is_redacted():
    """A remote peer can hand us a credential — ours, theirs, or bait. It never lands raw on
    our bus, and redaction is VISIBLE so a reader can tell it from an empty field."""
    leak = "here is the key sk-ant-api03-AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLL"
    out = RR.accept(_envelope(_msg(content=leak)), secret=IN_SECRET, peer="serge-dsh")
    assert out.ok
    assert "sk-ant-api03-AAAA" not in RR.last_admitted()["content"], (
        "an inbound credential landed unredacted on our bus")


def test_duplicate_inbound_id_is_admitted_once(monkeypatch):
    """RB-26 / T116 at the inbound boundary: at-least-once delivery means the SENDER may
    legitimately resend. Idempotency is the receiver's job, and a duplicate must point at the
    cached outcome rather than silently vanishing (T116 lesson)."""
    env = _envelope(_msg(id="dupe-1"))
    first = RR.accept(env, secret=IN_SECRET, peer="serge-dsh")
    second = RR.accept(env, secret=IN_SECRET, peer="serge-dsh")

    assert first.ok
    assert second.ok, "a legitimate redelivery was reported as a failure"
    assert RR.admitted_count("dupe-1") == 1, "a redelivered message was delivered twice"


def test_gate_never_raises_on_a_malformed_envelope():
    """The boundary law this house already paid for: a listener that raises is a listener an
    attacker can turn into a denial-of-service with one malformed byte."""
    for junk in ({}, {"body": "!!!not-base64!!!", "sig": "x"}, {"body": "", "sig": ""},
                 {"body": base64.b64encode(b"not json").decode(), "sig": "x"}):
        out = RR.accept(junk, secret=IN_SECRET, peer="serge-dsh")
        assert not out.ok, f"malformed envelope {junk} was admitted"
