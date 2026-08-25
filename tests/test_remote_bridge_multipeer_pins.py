"""Pins: a peer is identified by WHICH KEY VERIFIED IT, not by a flag or a claim.

2026-08-25. Chronos is real (Daniil, watching Serge's screen), so Serge's machine hosts more
than one fleet identity. Until now our listener took a single `--peer` flag and stamped every
admitted message with it, so Zadkiel and Chronos and Serge all arrived as `remote:serge-dsh`.
Sixteen messages, six claimed names, one route.

That was fine for one peer and is wrong for two, and the wrongness is not cosmetic: an
operator reading the parked inbox cannot tell which fleet said what, so any judgement about
who is confused, who is down, or who asked for something is being made on a label we chose
rather than a fact we verified.

THE RULE THESE PINS ENFORCE: THE KEY IS THE IDENTITY.

A flag is an assertion by our own launcher. A `frm` field is an assertion by the sender. Only
the HMAC is an assertion by CRYPTOGRAPHY — whoever signed this held that secret, and secrets
are per-peer by construction. So provenance resolves to the peer whose key verified the
envelope, and to nothing else. This is the same principle that already made us refuse the
payload's `frm`, applied one level up: we stopped trusting the sender's claim, and now we stop
trusting our own configuration's guess.

The property that makes it worth pinning rather than merely writing: a message signed by peer
A can NEVER be attributed to peer B, no matter what it claims, what order the config lists
them in, or what flag the listener was started with.
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

KEY_ZAD = b"zadkiel-key-aaaaaaaaaaaaaaaaaaaa"
KEY_CHRONOS = b"chronos-key-bbbbbbbbbbbbbbbbbbbb"
KEY_STRANGER = b"nobody-configured-this-one-cccccc"


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "zadkiel_in.key").write_bytes(KEY_ZAD)
    (secrets / "chronos_in.key").write_bytes(KEY_CHRONOS)
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(secrets))
    cfg = tmp_path / "remote_bridge.json"
    cfg.write_text(json.dumps({
        "peers": [
            {"name": "zadkiel", "inbound_secret_file": "zadkiel_in.key"},
            {"name": "chronos", "inbound_secret_file": "chronos_in.key"},
        ]
    }), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    yield
    RR._reset_cache()


def env(kind="chat", frm="whoever", content="x", mid="m-1", secret=KEY_ZAD, sent_at=None):
    p = {"v": 1, "id": mid, "frm": frm, "kind": kind, "content": content,
         "sent_at": int(sent_at if sent_at is not None else time.time())}
    body = json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    return {"body": base64.b64encode(body).decode(), "sig": RR.sign(body, secret)}


def test_each_peer_is_identified_by_its_own_key():
    out = RR.accept(env(mid="z-1", secret=KEY_ZAD))
    assert out.ok
    assert RR.last_admitted()["frm"] == "remote:zadkiel"

    out = RR.accept(env(mid="c-1", secret=KEY_CHRONOS))
    assert out.ok
    assert RR.last_admitted()["frm"] == "remote:chronos"


def test_a_peers_key_cannot_be_attributed_to_another_peer():
    """THE LOAD-BEARING PIN. Chronos claiming to be Zadkiel, signed with Chronos's own key,
    must land as chronos. Otherwise one peer can wear another's identity on our own bus by
    typing a different name, which is the payload-frm hole one level up."""
    RR.accept(env(mid="c-2", frm="zadkiel", secret=KEY_CHRONOS))
    got = RR.last_admitted()
    assert got["frm"] == "remote:chronos", "a peer wore another peer's identity"
    assert got["claimed_frm"] == "zadkiel", "the claim must survive as inert evidence"


def test_an_unconfigured_key_is_refused_not_admitted_as_unknown():
    """Absent knowledge is refusal. A stranger must not be admitted under a placeholder
    identity — 'unknown-peer' on a live bus is an anonymous speaker with a name badge."""
    out = RR.accept(env(mid="s-1", secret=KEY_STRANGER))
    assert not out.ok


def test_config_order_does_not_decide_identity():
    """If the answer changed with list order, the resolver would be guessing rather than
    verifying — and it would be silently order-dependent, which is the worst kind of stable."""
    RR.accept(env(mid="c-3", secret=KEY_CHRONOS))
    first = RR.last_admitted()["frm"]
    RR.accept(env(mid="z-3", secret=KEY_ZAD))
    RR.accept(env(mid="c-4", secret=KEY_CHRONOS))
    assert RR.last_admitted()["frm"] == first == "remote:chronos"


def test_single_peer_config_still_works(tmp_path, monkeypatch):
    """Backward compatibility is a security property here: a fleet that upgrades and silently
    stops admitting its only peer has been broken by a fix."""
    cfg = tmp_path / "single.json"
    cfg.write_text(json.dumps({
        "peer": {"name": "serge-dsh", "inbound_secret_file": "zadkiel_in.key"}
    }), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    out = RR.accept(env(mid="legacy-1", secret=KEY_ZAD))
    assert out.ok
    assert RR.last_admitted()["frm"] == "remote:serge-dsh"


def test_explicit_peer_argument_still_overrides_for_a_single_key_caller():
    """The listener's --peer flag stays usable for the one-key case (and for drills), but it
    must never be able to RENAME a peer the key already identified."""
    RR.accept(env(mid="z-9", secret=KEY_ZAD), peer="not-zadkiel")
    assert RR.last_admitted()["frm"] == "remote:zadkiel", (
        "a flag overrode an identity the key had already proven")
