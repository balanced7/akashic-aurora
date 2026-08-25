"""Remote bridge listener pins — the HTTP door in front of the inbound gate.

Design: docs/library/design/remote-bifrost-bridge-design.md §3.3. accept() decides ADMISSION;
this listener decides EXPOSURE. They are separate questions and separate failure modes, so
they get separate pins: a perfect gate behind a door bound to 0.0.0.0 on a machine with no
antivirus and no OS patches is not a safe bridge.

The handler is a PURE FUNCTION (handle_request) with the socket server as a thin shell over
it, so every pin here runs with no port, no thread and no network — the same discipline
discord_bridge and remote_relay already keep. A listener whose tests need a live socket is a
listener whose tests get skipped in CI and rot.

THE ASYMMETRY THIS FILE EXISTS TO ENFORCE — A REFUSAL MUST TEACH THE OPERATOR AND TELL THE
ATTACKER NOTHING. accept() returns richly explanatory reasons on purpose; this house's whole
error style is errors-that-teach. Piping those to the WIRE inverts it: "kind 'halt' is not on
the bridge allowlist (['blocker', 'chat', ...])" hands an unauthenticated caller the entire
policy, and a distinct message per failure turns the endpoint into an oracle you can probe to
learn whether a key is wrong, stale, or simply unconfigured. So the reason goes to the LOG,
and the wire gets one flat refusal. Errors-that-teach is a rule about the READER, and across
a fleet boundary the reader is not necessarily a friend.
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

from core.comm import remote_relay as RR          # noqa: E402
from scripts import remote_bridge_listener as L   # noqa: E402

IN_SECRET = b"test-inbound-secret"


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    RR._reset_cache()
    yield
    RR._reset_cache()


def _envelope(kind="chat", frm="serge", content="hello", secret=IN_SECRET, sent_at=None, mid="e-1"):
    payload = {"v": 1, "id": mid, "frm": frm, "kind": kind, "content": content,
               "sent_at": int(sent_at if sent_at is not None else time.time())}
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return json.dumps({"body": base64.b64encode(body).decode("ascii"),
                       "sig": RR.sign(body, secret)}).encode("utf-8")


# ------------------------------------------------------------------ exposure: the bind surface
def test_default_bind_is_loopback():
    """THE DEFAULT IS THE POLICY. Nobody reads the flag docs before the first run, and this
    machine runs with Defender disabled and Windows Update blocked by choice — so a listener
    that defaults to all-interfaces is one absent-minded launch from an open door on an
    unpatched box. Widening must be a sentence the operator TYPED."""
    assert L.DEFAULT_HOST == "127.0.0.1"


def test_public_bind_requires_explicit_optin():
    """A flag that merely warns is a flag that gets ignored. Non-loopback must be REFUSED
    unless the operator opted in by name, so the dangerous case cannot be reached by a typo
    or a copied command line."""
    ok, why = L.bind_allowed("0.0.0.0", allow_public=False)
    assert not ok and "public" in why.lower()
    assert L.bind_allowed("0.0.0.0", allow_public=True)[0]
    assert L.bind_allowed("127.0.0.1", allow_public=False)[0]


# ------------------------------------------------------------------ surface: methods and paths
def test_only_post_to_xfer_exists():
    """The bridge has exactly ONE verb on ONE path. Every other method and route is a 404/405
    with no hint — an endpoint that answers differently for a real path than a fake one is a
    map an attacker can read by knocking."""
    assert L.handle_request("GET", "/xfer", b"", secret=IN_SECRET)[0] == 405
    assert L.handle_request("POST", "/", b"", secret=IN_SECRET)[0] == 404
    assert L.handle_request("POST", "/admin", b"", secret=IN_SECRET)[0] == 404
    assert L.handle_request("DELETE", "/xfer", b"", secret=IN_SECRET)[0] == 405


def test_admitted_message_returns_202_and_is_parked():
    status, body, _log = L.handle_request("POST", "/xfer", _envelope(), secret=IN_SECRET,
                                          peer="serge-dsh")
    assert status == 202, f"a valid message was not accepted: {body}"
    assert RR.admitted_count("e-1") == 1, "a 202 was returned but nothing was parked"


# ------------------------------------------------------------------ the asymmetry: wire vs log
@pytest.mark.parametrize("bad,label", [
    (_envelope(secret=b"wrong-key"), "forged signature"),
    (_envelope(kind="halt"), "control kind"),
    (_envelope(kind="kind_from_the_future"), "unknown kind"),
    (b"{not json at all", "malformed json"),
    (b"", "empty body"),
])
def test_refusal_is_flat_on_the_wire(bad, label):
    """One refusal shape for every failure. If a forged signature and a bad kind return
    different bodies, the endpoint is an oracle: an attacker probes it to learn whether the
    key is wrong, the key is stale, or the kind list is short — which is most of what they
    need. Same status, same body, every time."""
    status, body, _log = L.handle_request("POST", "/xfer", bad, secret=IN_SECRET,
                                          peer="serge-dsh")
    assert status == 400, f"{label} did not return the flat refusal status"
    assert body == L.FLAT_REFUSAL, f"{label} leaked a distinct body: {body}"


def test_the_operator_still_learns_the_real_reason():
    """The sibling of the pin above, and the reason this is not just silence. The detailed,
    teaching reason accept() produced must reach the LOG — a flat wire plus a flat log is not
    security, it is a bridge nobody can debug at 2am."""
    _s, _b, log = L.handle_request("POST", "/xfer", _envelope(kind="halt"), secret=IN_SECRET,
                                   peer="serge-dsh")
    assert "halt" in log and "allowlist" in log, (
        f"the operator's log lost the reason the wire deliberately withheld: {log!r}")


def test_refusal_body_names_no_policy():
    """Belt and braces on the flat refusal itself: it must not quote the allowlist, the peer
    name, or the skew window. This pin fails if someone later makes the refusal 'more
    helpful' without noticing who is reading it."""
    for leak in ("chat", "handoff", "allowlist", "hmac", "serge", "skew", "secret"):
        assert leak not in json.dumps(L.FLAT_REFUSAL).lower(), (
            f"the flat refusal leaks {leak!r} to an unauthenticated caller")


# ------------------------------------------------------------------ resource safety
def test_oversize_body_is_refused_by_length_not_by_reading_it():
    """An unauthenticated caller must not be able to make us allocate. The cap is checked
    against the DECLARED length before any read, so a claimed 4GB body costs a comparison
    rather than 4GB."""
    assert L.length_allowed(10) is True
    assert L.length_allowed(L.MAX_BODY_BYTES + 1) is False
    status, body, _log = L.handle_request("POST", "/xfer", b"x" * (L.MAX_BODY_BYTES + 1),
                                          secret=IN_SECRET)
    assert status == 413
    assert body == L.FLAT_REFUSAL


def test_handler_never_raises_on_any_input():
    """The boundary law. A listener that raises on a malformed byte is a denial of service
    with a one-line exploit, and this one is reachable by anyone who can route to the port."""
    for junk in (b"", b"\x00\xff\xfe", b"[]", b"null", b'{"body": 5, "sig": []}',
                 b'{"body": "' + b"A" * 500 + b'", "sig": "x"}'):
        status, body, _log = L.handle_request("POST", "/xfer", junk, secret=IN_SECRET)
        assert status in (400, 413), f"unexpected status for {junk[:20]!r}: {status}"


def test_unkeyed_listener_refuses_everything():
    """Inert-until-keyed reaches the door too: a listener started before the key is dropped
    must refuse, not admit. Absent config is refusal, never permission."""
    status, body, _log = L.handle_request("POST", "/xfer", _envelope(), secret=b"")
    assert status == 400 and body == L.FLAT_REFUSAL
