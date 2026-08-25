"""Pins: OUTBOUND must be per-peer too, or multi-peer is half a bridge.

Found by CHRONOS (Serge's DSH seat) 2026-08-25, reading the code rather than the claim, one
hour after I shipped multi-peer and called it done. Its words:

    "resolve_peer() distinguishes INBOUND senders by trying every peer's inbound_secret_file,
     but OUTBOUND signing still reads a single remote_bridge_outbound.key. So one outbound
     key = one outbound identity, per file."

Correct, and it makes the earlier commit a half-measure with a whole-measure commit message.
Inbound could tell Chronos from Zadkiel; outbound could only ever speak as whoever owned the
one file. Chronos noticed because it was asked to place its keys and the two instructions I
had given it pointed at different actions — overwrite (become the only peer) or add (be a
second peer that outbound cannot reach). It refused to write a byte until that was resolved,
which is exactly right, and is the behaviour I would want from any seat handed an ambiguous
instruction about credentials.

THE RULE: A PEER IS A PAIR OF DIRECTIONS, NOT AN INBOX. If a fleet can be told apart when it
speaks to us but not when we speak to it, we have not modelled a peer — we have modelled a
mailbox with several locks and one return address.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402

ZAD_OUT = b"zadkiel-outbound-key-aaaaaaaaaaaa"
CHR_OUT = b"chronos-outbound-key-bbbbbbbbbbbb"


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.delenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", raising=False)
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "zad_out.key").write_bytes(ZAD_OUT)
    (secrets / "chr_out.key").write_bytes(CHR_OUT)
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(secrets))
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"peers": [
        {"name": "zadkiel", "url": "https://zad.invalid/xfer",
         "outbound_secret_file": "zad_out.key"},
        {"name": "chronos", "url": "https://chr.invalid/xfer",
         "outbound_secret_file": "chr_out.key"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    yield
    RR._reset_cache()


class Spy:
    def __init__(self):
        self.calls = []

    def __call__(self, url, envelope):
        self.calls.append((url, envelope))
        return {"ok": True}


def _msg(mid="m-1"):
    return {"frm": "vandor", "kind": "chat", "content": "hi", "id": mid}


def test_push_uses_the_named_peers_url_and_key():
    spy = Spy()
    RR.push(_msg(), peer="chronos", post=spy)
    url, env = spy.calls[0]
    assert url == "https://chr.invalid/xfer", "went to the wrong peer's endpoint"
    body = __import__("base64").b64decode(env["body"])
    assert env["sig"] == RR.sign(body, CHR_OUT), "signed with the wrong peer's key"
    assert env["sig"] != RR.sign(body, ZAD_OUT)


def test_each_peer_gets_its_own_identity():
    spy = Spy()
    RR.push(_msg("a"), peer="zadkiel", post=spy)
    RR.push(_msg("b"), peer="chronos", post=spy)
    import base64
    (u1, e1), (u2, e2) = spy.calls
    assert u1 != u2
    assert e1["sig"] == RR.sign(base64.b64decode(e1["body"]), ZAD_OUT)
    assert e2["sig"] == RR.sign(base64.b64decode(e2["body"]), CHR_OUT)


def test_unknown_peer_is_refused_not_silently_defaulted():
    """Falling back to 'the first peer' would send one fleet's message to another fleet —
    a misdelivery that looks like a success, which is the worst shape a bug can take."""
    out = RR.push(_msg(), peer="nobody-by-that-name", post=Spy())
    assert not out.ok
    assert "peer" in (out.why or "").lower()


def test_enqueue_remembers_which_peer_and_tick_honours_it():
    """The outbox must carry the ADDRESS, not just the letter. A queue that forgets who a
    message was for delivers it to whoever is configured first when it finally drains."""
    RR.enqueue(_msg("q-zad"), peer="zadkiel")
    RR.enqueue(_msg("q-chr"), peer="chronos")
    spy = Spy()
    RR.tick(post=spy)
    seen = {u: e for u, e in spy.calls}
    assert "https://zad.invalid/xfer" in seen and "https://chr.invalid/xfer" in seen
    import base64
    z = seen["https://zad.invalid/xfer"]
    assert z["sig"] == RR.sign(base64.b64decode(z["body"]), ZAD_OUT)


def test_a_failed_peer_does_not_strand_the_other_peers_mail():
    """One unreachable fleet must not hold another fleet's mail hostage — the head-of-line
    rule, now applied across peers rather than only within one queue."""
    RR.enqueue(_msg("q-zad"), peer="zadkiel")
    RR.enqueue(_msg("q-chr"), peer="chronos")

    class ZadDown:
        def __init__(self):
            self.ok_calls = []

        def __call__(self, url, envelope):
            if "zad.invalid" in url:
                raise OSError("that fleet is down")
            self.ok_calls.append(url)
            return {"ok": True}

    post = ZadDown()
    RR.tick(post=post)
    assert "https://chr.invalid/xfer" in post.ok_calls, "a down peer stranded another's mail"
    assert any(r.get("id") == "q-zad" for r in RR.pending()), "the down peer's mail was lost"
    assert not any(r.get("id") == "q-chr" for r in RR.pending()), "delivered mail stayed queued"
