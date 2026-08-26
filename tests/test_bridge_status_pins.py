"""Pins: remote-bridge status and remediation, as a module the UI merely renders.

Daniil, 2026-08-25: "make the bifrost ui be remote aware and to allow for remediation."

TWO HALVES WITH DIFFERENT RULES, which is why they are pinned together and implemented apart:

  STATUS IS A READ and must never lie by omission. Every field says what it measured and
  when. A dashboard that shows a peer as "up" because a config row exists is the
  green-receipt-over-a-broken-path failure with better typography — and this fleet spent
  2h44m on that exact shape, so a status panel is the last place to repeat it.

  REMEDIATION IS AN ACT and must never be a side effect of looking. Every action is explicit,
  reports what it actually did, and refuses rather than guesses. The dangerous one is
  draining parked peer mail onto the live bus: that spends the parked-not-bussed defence, so
  it carries the Discord guest-tier posture (attributed, authority:none, no control kinds)
  and it must not be reachable by rendering a page.

THE RULE THAT SHAPES BOTH: a panel that can act is a door, and a door needs the same
discipline as the gate behind it. Nothing here trusts a name in a payload, and nothing here
does work because a page was loaded.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import bridge_status as BS  # noqa: E402
from core.comm import remote_relay as RR   # noqa: E402


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.delenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", raising=False)
    sec = tmp_path / "secrets"
    sec.mkdir()
    (sec / "a_in.key").write_bytes(b"peer-a-inbound-key-aaaaaaaaaaaa")
    (sec / "a_out.key").write_bytes(b"peer-a-outbound-key-bbbbbbbbbb")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(sec))
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"peers": [
        {"name": "peer-a", "url": "https://a.invalid/xfer",
         "inbound_secret_file": "a_in.key", "outbound_secret_file": "a_out.key"},
        {"name": "peer-unkeyed", "url": "", "inbound_secret_file": "missing.key"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    yield
    RR._reset_cache()


# ------------------------------------------------------------------ STATUS: a read that tells truth
def test_status_lists_every_configured_peer():
    st = BS.status(probe=False)
    names = [p["name"] for p in st["peers"]]
    assert "peer-a" in names and "peer-unkeyed" in names


def test_an_unkeyed_peer_is_reported_inert_not_broken():
    """Absent-is-not-broken, on the dashboard. A peer with no key yet is a CONFIGURATION
    STATE; painting it as a failure trains the reader to ignore red."""
    st = BS.status(probe=False)
    row = next(p for p in st["peers"] if p["name"] == "peer-unkeyed")
    assert row["keyed"] is False
    assert row["state"] == "inert", f"expected inert, got {row['state']!r}"
    row_a = next(p for p in st["peers"] if p["name"] == "peer-a")
    assert row_a["keyed"] is True


def test_reachability_is_absent_rather_than_guessed_when_not_probed():
    """The panel must never imply a measurement it did not take. `probe=False` is the cheap
    render; it may not report a peer as up."""
    st = BS.status(probe=False)
    for p in st["peers"]:
        assert p.get("reachable") is None, "unprobed reachability was reported as a verdict"
    assert st["probed"] is False


def test_status_reports_queue_depths_from_disk():
    RR.enqueue({"frm": "v", "kind": "chat", "content": "x", "id": "q1"}, peer="peer-a")
    st = BS.status(probe=False)
    assert st["outbox_pending"] == 1
    row = next(p for p in st["peers"] if p["name"] == "peer-a")
    assert row["queued_for_peer"] == 1, "per-peer depth is what tells you WHO is stuck"


def test_status_never_raises_on_a_broken_world(monkeypatch):
    """A dashboard that crashes on a malformed config takes the operator's eyes out at exactly
    the moment something is wrong."""
    monkeypatch.setattr(RR, "CONFIG_FILE", Path("does-not-exist.json"))
    RR._reset_cache()
    st = BS.status(probe=False)
    assert isinstance(st, dict) and "peers" in st


def test_status_carries_its_own_timestamp():
    """A rendered number with no age is a claim about now that may be about an hour ago."""
    st = BS.status(probe=False)
    assert abs(int(st["measured_at"]) - int(time.time())) < 5


# ------------------------------------------------------------------ REMEDIATION: acts, never side effects
def test_actions_are_enumerated_and_named():
    acts = BS.actions()
    names = {a["id"] for a in acts}
    assert {"tick_outbox", "drain_parked", "restart_listener"} <= names
    for a in acts:
        assert a.get("danger") in ("low", "medium", "high"), f"{a['id']} has no danger rating"
        assert a.get("what"), f"{a['id']} does not say what it does"


def test_an_unknown_action_is_refused():
    out = BS.act("rm_minus_rf", confirm=True)
    assert not out.ok and "unknown" in (out.why or "").lower()


def test_dangerous_actions_require_explicit_confirmation():
    """Rendering a page must never perform work. Anything that changes the world needs a
    caller who said so — a UI button posts confirm=true, a page load cannot."""
    for aid in ("drain_parked", "restart_listener"):
        out = BS.act(aid, confirm=False)
        assert not out.ok, f"{aid} ran without confirmation"
        assert "confirm" in (out.why or "").lower()


def test_drain_parked_carries_the_guest_tier_posture():
    """Draining spends the parked-not-bussed defence, so what lands must carry no power:
    attributed in the body, authority:none, provenance from the verified route."""
    posted = []
    RR._reset_cache()
    rows = RR._read_jsonl(RR.inbox_path())
    rows.append({"id": "p1", "frm": "remote:peer-a", "claimed_frm": "somebody",
                 "kind": "chat", "content": "hello", "sent_at": 0, "admitted_at": 0})
    RR._write_jsonl(RR.inbox_path(), rows)

    out = BS.act("drain_parked", confirm=True, bus_send=lambda **kw: posted.append(kw) or "id-1")
    assert out.ok, out.why
    assert posted, "nothing was drained"
    meta = posted[0].get("meta") or {}
    assert meta.get("authority") == "none", "drained remote mail carried authority"
    assert meta.get("route") == "remote:peer-a"
    assert "[remote" in str(posted[0].get("content")), "not attributed in the body"


def test_act_never_raises():
    for aid in ("tick_outbox", "drain_parked", "restart_listener", "", None, 123):
        try:
            BS.act(aid, confirm=True, bus_send=lambda **kw: None)
        except Exception as e:                                    # noqa: BLE001
            pytest.fail(f"act({aid!r}) raised {type(e).__name__}: {e}")
