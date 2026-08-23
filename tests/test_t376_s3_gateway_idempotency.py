"""
T376 S3a -- the gateway relay idempotency stamp (pins, RED-first).

The reconciled design (fences/t376-metabolism/reconciliation.md, layer 3
PRIMARY): every relay stamps meta.idempotency_key = discord:<message.id>, so
double-relay -- two overlapping gateway generations, a RESUME replay, the
make-before-break window -- dies at the bus door via the identity walk
(mailbox._IDENTITY_FIELDS honors idempotency_key ahead of packet sha), with
no coordination between the racers.

  P1  every operator relay path (seat-lane, mention, broadcast) stamps
      meta.idempotency_key = discord:<message_id> when the runner passes the
      Discord message id.
  P2  two bus messages carrying the same idempotency_key resolve to ONE
      mailbox identity -- the door-dedupe foundation the design rides.
  P3  a caller that passes no message_id degrades to no stamp (never a
      crash, never a fabricated key).

Run: py -m pytest tests/test_t376_s3_gateway_idempotency.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import discord_inbound
from core.comm.mailbox import identity_of


class _Bus:
    def __init__(self):
        self.sent = []

    def send(self, to, kind, content, meta=None):
        self.sent.append({"to": to, "kind": kind, "content": content,
                          "meta": dict(meta or {})})
        return f"m{len(self.sent)}-0"

    def broadcast(self, kind, content, meta=None):
        self.sent.append({"to": "*", "kind": kind, "content": content,
                          "meta": dict(meta or {})})
        return f"m{len(self.sent)}-0"


def _cfg():
    return {"operator_id": "111222333444555666",
            "people": {"111222333444555666": {"tier": "operator",
                                              "agent": "daniil"}}}


def _call(bus, message_id=None, content="ping"):
    kwargs = {}
    if message_id is not None:
        kwargs["message_id"] = message_id
    return discord_inbound.handle_message(
        _cfg(), author_id="111222333444555666", author_name="d",
        channel_id="c-unmapped", content=content, bus=bus,
        react=lambda e: None, **kwargs)


# ------------------------------------------------------------------ P1 stamp
def test_p1_operator_relay_carries_the_discord_idempotency_key():
    bus = _Bus()
    out = _call(bus, message_id="555000111")
    assert out.get("acted")
    assert bus.sent, "the relay must reach the bus"
    meta = bus.sent[-1]["meta"]
    assert meta.get("idempotency_key") == "discord:555000111", (
        f"every relay must self-identify by its Discord message id; got {meta}")


# ------------------------------------------------------------------ P2 identity
def test_p2_same_key_resolves_to_one_identity():
    fields_a = {"frm": "daniil", "to": "claude", "kind": "chat",
                "content": "ping", "ts": "1"}
    fields_b = {"frm": "daniil", "to": "claude", "kind": "chat",
                "content": "ping (redelivered wording drift)", "ts": "2"}
    ida, basis_a = identity_of(fields_a, {"idempotency_key": "discord:555"})
    idb, basis_b = identity_of(fields_b, {"idempotency_key": "discord:555"})
    assert ida == idb, "one Discord message must be ONE identity at the door"
    assert basis_a == "idempotency_key" == basis_b


# ------------------------------------------------------------------ P3 degrade
def test_p3_no_message_id_degrades_to_no_stamp():
    bus = _Bus()
    out = _call(bus)                       # legacy caller shape, no message_id
    assert out.get("acted")
    meta = bus.sent[-1]["meta"]
    assert "idempotency_key" not in meta, (
        "no id means NO stamp -- a fabricated key would merge distinct messages")
