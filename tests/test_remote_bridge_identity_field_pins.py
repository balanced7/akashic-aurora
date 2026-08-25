"""Pins: `name` says WHO SENT IT; `as` says WHO WE SIGN AS. One field cannot do both.

Found by CHRONOS, 2026-08-25, before writing a single line of config — which is the second
real defect it has caught in code I shipped hours earlier, both by reading rather than by
failing.

THE DEFECT. `peer_row(name)` matched one field, and that field was carrying two jobs:

  INBOUND   `name` is the label we stamp on an arriving message — who sent this.
  OUTBOUND  `name` is the selector for which row's key signs — who we speak as.

On OUR topology those coincide, which is why it survived review: one local identity, N remote
peers, so every row IS a distinct remote peer and one field answers both questions.

CHRONOS'S TOPOLOGY INVERTS IT — one remote peer (daniil), two local identities (serge-dsh and
chronos). Now inbound wants BOTH rows named `daniil`, because a message from daniil is from
daniil whichever key pair carried it; and outbound needs the two rows to DIFFER, because the
whole point is choosing which identity signs. Its own measurement:

    push(peer="chronos") -> REFUSED, "configured peers are ['daniil', 'daniil']"
    push(peer="daniil")  -> always the FIRST row, so chronos could never speak as itself

THE FIX IS TO SPLIT THE QUESTION, NOT TO PICK A WINNER. `name` stays the remote sender's
label. `as` is added for our local signing identity, and the outbound selector matches EITHER
— so our rows, which have no `as`, keep working untouched, and a machine hosting several
identities can finally address them apart.

The general shape, worth carrying past this file: A FIELD THAT ANSWERS TWO QUESTIONS IS FINE
UNTIL A TOPOLOGY MAKES THE ANSWERS DIFFER, and the topology that does it is usually the mirror
image of the one you designed against.
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

SERGE_OUT = b"serge-identity-outbound-key-aaaa"
CHRONOS_OUT = b"chronos-identity-outbound-key-bb"
DANIIL_IN_A = b"daniil-signs-to-serge-cccccccccc"
DANIIL_IN_B = b"daniil-signs-to-chronos-dddddddd"


@pytest.fixture(autouse=True)
def _their_world(tmp_path, monkeypatch):
    """CHRONOS'S machine, not ours: one remote peer, two local identities."""
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.delenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", raising=False)
    sec = tmp_path / "secrets"
    sec.mkdir()
    (sec / "serge_out.key").write_bytes(SERGE_OUT)
    (sec / "chronos_out.key").write_bytes(CHRONOS_OUT)
    (sec / "serge_in.key").write_bytes(DANIIL_IN_A)
    (sec / "chronos_in.key").write_bytes(DANIIL_IN_B)
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(sec))
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"peers": [
        {"name": "daniil", "as": "serge-dsh", "url": "https://d.invalid/xfer",
         "outbound_secret_file": "serge_out.key", "inbound_secret_file": "serge_in.key"},
        {"name": "daniil", "as": "chronos", "url": "https://d.invalid/xfer",
         "outbound_secret_file": "chronos_out.key", "inbound_secret_file": "chronos_in.key"},
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


def _env_from_daniil(secret, mid="d-1"):
    p = {"v": 1, "id": mid, "frm": "vandor", "kind": "chat", "content": "hi",
         "sent_at": int(time.time())}
    b = json.dumps(p, sort_keys=True, separators=(",", ":")).encode()
    return {"body": base64.b64encode(b).decode(), "sig": RR.sign(b, secret)}


# ------------------------------------------------------------------ outbound: `as` selects
def test_outbound_selects_by_local_identity():
    spy = Spy()
    out = RR.push({"frm": "chronos", "kind": "chat", "content": "x", "id": "m1"},
                  peer="chronos", post=spy)
    assert out.ok, f"could not speak as chronos: {out.why}"
    body = base64.b64decode(spy.calls[0][1]["body"])
    assert spy.calls[0][1]["sig"] == RR.sign(body, CHRONOS_OUT), "signed with the wrong identity"


def test_each_local_identity_signs_with_its_own_key():
    spy = Spy()
    RR.push({"frm": "x", "kind": "chat", "content": "a", "id": "m-s"}, peer="serge-dsh", post=spy)
    RR.push({"frm": "x", "kind": "chat", "content": "b", "id": "m-c"}, peer="chronos", post=spy)
    b1 = base64.b64decode(spy.calls[0][1]["body"])
    b2 = base64.b64decode(spy.calls[1][1]["body"])
    assert spy.calls[0][1]["sig"] == RR.sign(b1, SERGE_OUT)
    assert spy.calls[1][1]["sig"] == RR.sign(b2, CHRONOS_OUT)


# ------------------------------------------------------------------ inbound: `name` labels
def test_inbound_labels_the_sender_the_same_on_both_key_pairs():
    """A message from daniil is from daniil whichever key pair carried it. If the two rows
    labelled inbound differently, the operator's inbox would show one correspondent as two."""
    RR.accept(_env_from_daniil(DANIIL_IN_A, "in-a"))
    assert RR.last_admitted()["frm"] == "remote:daniil"
    RR.accept(_env_from_daniil(DANIIL_IN_B, "in-b"))
    assert RR.last_admitted()["frm"] == "remote:daniil"


# ------------------------------------------------------------------ our own shape unbroken
def test_rows_without_as_still_select_by_name(tmp_path, monkeypatch):
    """OUR topology: N remote peers, one local identity, no `as` anywhere. It must keep
    working exactly as before -- a schema addition that breaks the shape it was added for is
    not an addition."""
    sec = tmp_path / "s2"
    sec.mkdir()
    (sec / "z.key").write_bytes(b"zad-out-key-eeeeeeeeeeeeeeeeeeee")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(sec))
    cfg = tmp_path / "ours.json"
    cfg.write_text(json.dumps({"peers": [
        {"name": "zadkiel", "url": "https://z.invalid/xfer", "outbound_secret_file": "z.key"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    spy = Spy()
    out = RR.push({"frm": "v", "kind": "chat", "content": "x", "id": "m"}, peer="zadkiel", post=spy)
    assert out.ok and spy.calls, f"our own shape broke: {out.why}"


def test_an_ambiguous_selector_is_refused_not_guessed():
    """If two rows could answer to the same selector, picking the first is a silent
    misdelivery. Refusing names the ambiguity while it is still cheap to fix."""
    out = RR.push({"frm": "x", "kind": "chat", "content": "x", "id": "amb"},
                  peer="daniil", post=Spy())
    assert not out.ok, "an ambiguous outbound selector silently picked a row"
    assert "ambiguous" in (out.why or "").lower()
