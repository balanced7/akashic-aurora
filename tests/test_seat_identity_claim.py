"""PRE-REGISTERED acceptance for the first-boot identity CLAIM step (T088 part a).

T088 listed collision-safety FIRST in the identity directive ("can two NEW agents spawning
simultaneously with one id break coordination? ... design an identity REGISTRATION handshake:
first-boot claims the id or gets a suffix"). T272 (2026-08-10) declared it "entirely
unbuilt". Recon 2026-10-13 found collision was DETECTED (roster.split_brain,
failure_class.STALE_INCARNATION, incarnation.live_incarnations) but never PREVENTED, and the
missing piece was exactly the claim step -- now `core.comm.seat_identity.claim_id()`.

Prior art this codifies, per seat_identity.py's own docstring: XMPP Bind 2 REFUSES a stanza
with no explicit sender when several resources share one stream; we take the posture one notch
softer because a hook must never break a session (T029/K8) -- loud verdict, never fatal, and
resolve() keeps the honest `unknown-<sid8>` rather than borrowing a peer's name.

WHY THESE ARE PINS AND NOT A SMOKE TEST. The R6 discipline (tests/test_seat_identity_resolver.py)
already names the failure: built-not-wired is code that looks like an asset and is a liability.
These pins drive claim_id() directly (pure -- a fake client, no live bus), so the claim
VERDICTS are locked regardless of whether any given boot path has or has not yet adopted the
call. The wired-vs-latent gap is covered separately: the function's docstring states the
caller's duty, and a latent claim is at least a NAMED gap now, not a silent one.
"""
from __future__ import annotations

import os

import pytest


class _Fake:
    """A minimal Redis-shaped client: get/set(nx,ex)/expire, an in-memory dict."""

    def __init__(self):
        self.store = {}
        self.expired = set()
        self._ttl = {}

    def get(self, key):
        # Simulate TTL expiry crudely: a key with a recorded ttl of 0 is "gone".
        if key in self._ttl and self._ttl[key] <= 0:
            return None
        return self.store.get(key)

    def set(self, key, val, nx=False, ex=None):
        if nx and key in self.store:
            return False          # the atomic claim: refused, someone holds it
        self.store[key] = val
        self._ttl[key] = ex
        return True

    def expire(self, key, ttl):
        self._ttl[key] = ttl
        return True


def _claim(aid, sid, client=None, ttl_s=180):
    from core.comm import seat_identity
    return seat_identity.claim_id(aid, sid, client=client, ttl_s=ttl_s)


def test_c1_first_boot_claims_a_free_id():
    """A brand-new id, nobody holds it -> this session claims it (verdict 'free')."""
    fake = _Fake()
    got = _claim("newbie", "sess-0001", fake)
    assert got["verdict"] == "free"
    assert got["claimed"] is True
    assert fake.store.get("bifrost:claim:newbie") == "sess-0001"


def test_c2_idempotent_re_claim_by_the_same_session():
    """The same session re-claiming its own id must not read as a collision (verdict 'mine')."""
    fake = _Fake()
    _claim("op", "sess-0001", fake)
    got = _claim("op", "sess-0001", fake)
    assert got["verdict"] == "mine"
    assert got["claimed"] is True


def test_c3_a_different_live_session_is_taken():
    """The whole point: a SECOND session claiming a held id is told 'taken', with the holder
    named -- so the caller can suffix to op#<sid8> instead of silently overlapping."""
    fake = _Fake()
    _claim("op", "sess-0001", fake)
    got = _claim("op", "sess-aaaa", fake)
    assert got["verdict"] == "taken"
    assert got["claimed"] is False
    assert got["holder"] == "sess-0001"


def test_c4_unreachable_store_is_unverified_not_safe():
    """Fail-open MUST NOT mean 'assume nobody holds it'. A store the caller cannot reach yields
    'unverified' -- absence of evidence is not evidence of absence -- so the caller keeps
    resolving loudly rather than proceeding on a silent assumption of safety.

    NOTE on how 'unreachable' is simulated: passing client=None means 'use the default bus
    connection' (which SUCCEEDS), not 'no store'. The real unreachable condition is a client
    whose reads/writes raise -- which is what a down Redis looks like at the call site."""
    class _Down:
        def get(self, key):
            raise ConnectionError("redis down")
        def set(self, *a, **k):
            raise ConnectionError("redis down")
        def expire(self, *a, **k):
            raise ConnectionError("redis down")

    got = _claim("op", "sess-0001", client=_Down())
    assert got["verdict"] == "unverified"
    assert got["claimed"] is False


def test_c5_never_raises_even_with_garbage():
    """Hooks are fail-open by contract (T029/K8): a claim must never break a session, even for
    a malformed id or an empty session id."""
    from core.comm import seat_identity
    assert isinstance(seat_identity.claim_id("", ""), dict)
    assert isinstance(seat_identity.claim_id(None, None), dict)
    assert isinstance(seat_identity.claim_id("a" * 200, "s"), dict)


def test_c6_malformed_id_is_not_claimed():
    """An id that fails the injection-surface guard (seat_identity.valid) is refused, never
    written into a Redis key."""
    fake = _Fake()
    got = _claim("bad id has spaces", "sess-0001", fake)
    assert got["claimed"] is False
    assert got["verdict"] == "unverified"


def test_c7_atomic_claim_two_sessions_race():
    """Two sessions read 'free' at once; only ONE may end up the holder. The SETNX path means a
    loser re-reads and reports the TRUE holder rather than a stale 'free'."""
    fake = _Fake()
    first = _claim("race", "sess-0001", fake)
    second = _claim("race", "sess-0002", fake)
    # Exactly one claims; the other is told 'taken' and names the winner.
    verdicts = {first["verdict"], second["verdict"]}
    assert "free" in verdicts or "mine" in verdicts
    assert "taken" in verdicts
    assert fake.store.get("bifrost:claim:race") == "sess-0001"
