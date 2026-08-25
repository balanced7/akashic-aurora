"""Remote relay pins — the outbound half of the Akashic↔Akashic bridge (v0.1).

Design: docs/library/design/remote-bifrost-bridge-design.md. Every pin here runs WITHOUT a
network: the transport is injected, so the allowlist, redaction, signing, and failure
semantics are all testable offline — a bridge whose tests need a live peer is a bridge nobody
runs the tests for (the discord_bridge precedent, carried over).

The three properties enforced:
  R1 — not everyone has access: an unkeyed / unrouted relay REFUSES (inert-until-keyed),
       and the allowlist is inherited from discord_bridge, never a second drifting copy.
  R2 — no credential on GitHub: the committed config names a route, never a secret; the
       secret files are the vault's own .secrets/remote_bridge/.
  R3 — robust (at-least-once): a message carries a STABLE id (dedupe address), a failed
       post does NOT advance anything, and the envelope is HMAC-signed + replay-windowed.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402

SECRET = b"test-outbound-secret"


class FakePost:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def __call__(self, url, envelope):
        if self.fail:
            raise OSError("simulated network failure")
        self.calls.append((url, envelope))
        return {"ok": True}


def _msg(kind="chat", **kw):
    m = {"frm": "claude", "kind": kind, "content": "hello", "id": "m-1"}
    m.update(kw)
    return m


# --------------------------------------------------------------------------- R1: allowlist
def test_unknown_kind_does_not_cross(monkeypatch):
    """A kind not on the forward allowlist REFUSES, even routed + keyed — the allowlist
    is inherited from discord_bridge, so the two bridges cannot drift."""
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", "https://peer/xfer")
    out = RR.push(_msg(kind="trace"), secret=SECRET)
    assert not out.ok
    assert "allowlist" in out.why


def test_unkeyed_relay_refuses(monkeypatch):
    """Inert-until-keyed: a routed relay with NO outbound secret refuses — holding a route
    without the key gets you nowhere, which is the 'not everyone has access' gate."""
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", "https://peer/xfer")
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOUND_KEY", "")
    # no secret arg, and env is empty -> resolves to b"" via the vault path we can't reach
    # offline; force the resolved-empty by passing a falsy secret explicitly.
    out = RR.push(_msg(), post=FakePost(), secret=b"")
    assert not out.ok
    assert "secret" in out.why


def test_unrouted_relay_refuses(monkeypatch, tmp_path):
    """Absent-is-not-broken: no peer url means 'not configured', distinct from 'failed'.

    ISOLATES THE CONFIG FILE, not just the env var. Until 2026-08-25 this cleared the env and
    trusted the on-disk config to be empty — so it was really asserting "peer.url happens to
    be blank in this checkout", and it went red the moment we routed the bridge at a real
    peer. A pin that passes because of ambient state is measuring the ambience.
    """
    monkeypatch.delenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", raising=False)
    empty = tmp_path / "unrouted.json"
    empty.write_text('{"peer": {"name": "nobody", "url": ""}}', encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", empty)
    out = RR.push(_msg(), secret=SECRET)
    assert not out.ok
    assert "not routed" in out.why


# --------------------------------------------------------------------------- R2: signing
def test_envelope_is_hmac_signed_and_verifies():
    """The wire envelope carries the base64 body + HMAC; verify() accepts it with the SAME
    secret and rejects with a wrong one."""
    env = RR.build_envelope(_msg(), SECRET)
    assert "body" in env and "sig" in env
    body = base64.b64decode(env["body"]).decode("utf-8")
    decoded = json.loads(body)
    assert decoded["kind"] == "chat" and decoded["frm"] == "claude"
    assert RR.verify(env["body"], env["sig"], SECRET) is True
    assert RR.verify(env["body"], env["sig"], b"wrong-secret") is False


def test_content_is_redacted_before_signature():
    """Visible redaction rides the PROJECTED surface: a credential-shaped body is redacted
    in the signed payload, inherited from discord_bridge.redact."""
    env = RR.build_envelope(_msg(content="my key is sk-abcdefghijklmnop"), SECRET)
    body = base64.b64decode(env["body"]).decode("utf-8")
    assert "sk-abcdefghijklmnop" not in body
    assert "[REDACTED-KEY]" in body


# --------------------------------------------------------------------------- R3: robustness
def test_message_carries_a_stable_id():
    """Dedupe address: the same message renders the same id; a stable id survives re-render,
    so a redelivered copy is dedupeable (no ever-fresh uuid)."""
    a = json.loads(base64.b64decode(RR.build_envelope(_msg(), SECRET)["body"]))
    b = json.loads(base64.b64decode(RR.build_envelope(_msg(), SECRET)["body"]))
    assert a["id"] == b["id"] == "m-1"


def test_idless_message_gets_content_derived_address():
    """A message with no id still gets a STABLE (content-derived) address — never randomized,
    else redelivery could not be deduped."""
    m = _msg(); del m["id"]
    a = json.loads(base64.b64decode(RR.build_envelope(m, SECRET)["body"]))
    b = json.loads(base64.b64decode(RR.build_envelope(m, SECRET)["body"]))
    assert a["id"].startswith("h:") and a["id"] == b["id"]


def test_failed_push_does_not_pretend_success():
    """T149 law carried over: a network failure returns a failed BoundaryOutcome naming the
    exception — it does NOT silently drop and does NOT claim done."""
    out = RR.push(_msg(kind="chat"), secret=SECRET, url="https://peer/xfer",
                  post=FakePost(fail=True))
    assert not out.ok
    assert "network failure" in out.why


def test_verify_rejects_stale_payload():
    """Replay protection: a payload older than the skew window fails verification even with
    the right HMAC."""
    import time as _t
    now = int(_t.time())
    stale = {"v": 1, "id": "m-1", "frm": "claude", "kind": "chat",
             "content": "x", "sent_at": now - 100000}
    body = json.dumps(stale, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body_b64 = base64.b64encode(body).decode("ascii")
    sig = RR.sign(body, SECRET)
    assert RR.verify(body_b64, sig, SECRET) is False
