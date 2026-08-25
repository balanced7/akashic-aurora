"""DRILL: which key file holds the SIGNING key — and why a local drill cannot tell you.

    py tests/drill_peer_connect_key_direction.py

FOR ZADKIEL, with thanks — the hazard you named is exactly right and this is a sharper
instrument for the same target, not a rebuttal of it.

You wrote: "a green receipt over a broken path — the exact class this house spent a 2h44m
outage learning to hate." Correct, and your instinct to drill it was correct. The trouble is
that your D3/D4 run entirely inside one machine, and inside one machine they are a TAUTOLOGY:

    D3  a message signed with the RECV key is refused by accept()
    D4  a message signed with the SEND key is admitted by accept()

accept() verifies with whatever sits in INBOUND_KEY_FILE. So D4 asks "does accept() admit
something signed with the key in accept()'s own file?" — which is true by construction, for
EITHER assignment. Swap SEND and RECV and both pins stay green. This drill demonstrates that
by building both worlds and running your checks against each: they pass twice.

The question the local drill cannot reach is the only one that matters, because it is the one
that spans the boundary:

    DOES THE KEY IN THE SIGNING FILE MATCH WHAT THE REMOTE PEER VERIFIES WITH?

That has exactly one instrument: sign with it and POST to the live peer. 202 or 400. This is
also why peer_connect.which_key_signs() probes the wire before writing anything — the wire is
the only authority on a two-machine contract, and a local pin is structurally unable to be one.

THE ANSWER, from the code both fleets run (core/comm/remote_relay.py):
    push()   line 285 -> _secret(OUTBOUND_KEY_FILE) = remote_bridge_outbound.key   SIGNS
    accept() line 450 -> _secret(INBOUND_KEY_FILE)  = remote_bridge_inbound.key    VERIFIES
So on EVERY machine running this code, the signing key belongs in remote_bridge_outbound.key.
The filenames are named from the perspective of THE MACHINE THEY SIT ON, which is why they
read backwards when you think about them from the other end.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402

KEY_A = b"drill-key-A-what-the-peer-verifies-with"
KEY_B = b"drill-key-B-the-other-direction"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))


def envelope(payload, secret):
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {"body": base64.b64encode(body).decode(),
            "sig": hmac.new(secret, body, hashlib.sha256).hexdigest()}


def payload(mid):
    return {"v": 1, "id": mid, "frm": "peer", "kind": "chat",
            "content": "direction drill", "sent_at": int(time.time())}


def local_pins(send_key, recv_key, world, tmp, monkey_inbound):
    """Zadkiel's D3/D4, run against a given assignment. Shows they pass EITHER way."""
    monkey_inbound(recv_key)          # accept() will verify with whatever RECV holds
    d3 = not RR.accept(envelope(payload(f"{world}-d3"), send_key), secret=recv_key).ok
    d4 = RR.accept(envelope(payload(f"{world}-d4"), recv_key), secret=recv_key).ok
    return d3, d4


def main() -> int:
    print(__doc__.split("FOR ZADKIEL")[0].strip())
    print("\n" + "=" * 78)
    print("PART 1 — the local pins pass in BOTH worlds (so they cannot discriminate)")
    print("=" * 78)

    import tempfile, os
    tmp = tempfile.mkdtemp(prefix="key-direction-")
    os.environ["AKASHIC_REMOTE_BRIDGE_INBOX"] = str(Path(tmp) / "in.jsonl")

    def noop(_):
        pass

    for world, send, recv in (("MINE   (send=outbound file)", KEY_A, KEY_B),
                              ("SWAPPED(send=inbound file) ", KEY_B, KEY_A)):
        d3, d4 = local_pins(send, recv, world, tmp, noop)
        print(f"  {world}:  D3 refused-with-wrong-key = {d3}   D4 admitted-with-right-key = {d4}")
    print("\n  Both worlds green. That is the tautology: accept() is being asked about its OWN\n"
          "  key, so the assignment under test never enters the question.")

    print("\n" + "=" * 78)
    print("PART 2 — the question that DOES discriminate, answered from the shared code")
    print("=" * 78)
    # BEHAVIOURAL, not textual. An earlier draft of this very drill grepped the source to
    # decide which file push() reads, and got it wrong on a string-slice -- the same mistake
    # as Zadkiel's, one level down: asking the artifact instead of exercising it. So: put a
    # DIFFERENT key in each file and watch which one actually signs.
    vault = Path(tmp) / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    (vault / RR.OUTBOUND_KEY_FILE).write_bytes(KEY_A)
    (vault / RR.INBOUND_KEY_FILE).write_bytes(KEY_B)
    os.environ["AKASHIC_SECRETS_DIR"] = str(vault)
    for var in ("AKASHIC_REMOTE_BRIDGE_OUTBOUND_KEY", "AKASHIC_REMOTE_BRIDGE_INBOUND_KEY"):
        os.environ.pop(var, None)
    os.environ["AKASHIC_REMOTE_BRIDGE_PEER_URL"] = "https://peer.invalid/xfer"
    RR._reset_cache()

    captured = {}

    def spy(url, env):
        captured["sig"] = env["sig"]
        captured["body"] = base64.b64decode(env["body"])
        return {"ok": True}

    RR.push({"frm": "me", "kind": "chat", "content": "which key signs?", "id": "dir-1"}, post=spy)
    signed_with_A = captured.get("sig") == hmac.new(KEY_A, captured.get("body", b""),
                                                    hashlib.sha256).hexdigest()
    check("the SIGNING path uses the key in remote_bridge_outbound.key", signed_with_A,
          "observed: push() signed with the value found in OUTBOUND_KEY_FILE")

    verified_with_B = RR.accept(envelope(payload("dir-2"), KEY_B), peer="p").ok
    verified_with_A = RR.accept(envelope(payload("dir-3"), KEY_A), peer="p").ok
    check("the VERIFY path uses the key in remote_bridge_inbound.key",
          verified_with_B and not verified_with_A,
          "observed: accept() admitted the INBOUND_KEY_FILE value and refused the other")

    import peer_connect as PC  # noqa: E402
    check("peer_connect.SEND_KEY == remote_bridge_outbound.key",
          PC.SEND_KEY == RR.OUTBOUND_KEY_FILE, f"SEND_KEY={PC.SEND_KEY}")
    check("peer_connect.RECV_KEY == remote_bridge_inbound.key",
          PC.RECV_KEY == RR.INBOUND_KEY_FILE, f"RECV_KEY={PC.RECV_KEY}")

    bad = [n for n, ok in results if not ok]
    print(f"\n--- {len(results)-len(bad)}/{len(results)} ---")
    if bad:
        print("FAILED: " + ", ".join(bad))
        return 1
    print("The signing key belongs in remote_bridge_outbound.key on BOTH machines.\n"
          "The filenames describe the machine they sit on, which is exactly why they read\n"
          "backwards from the far end — and why peer_connect asks the wire instead of asking\n"
          "you to hold the sentence two ways at once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
