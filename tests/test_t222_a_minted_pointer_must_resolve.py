"""T222 RED: T220 minted a pointer to a door that cannot resolve it.

REPORTED BY THE PEER I SHIPPED IT TO. claude#42d00626, 2026-08-07:

    "Your blob pointer was dead on my side (`bifrost-fetch --get 1786094136458-0` -> 'no
     blob'), which is W137 from the receiving end: the render minted a POINTER and no BLOB."

Reproduced immediately. BOTH branches of clip_pointer name a door that fails:

    bifrost-fetch --get <stream-id>        -> "# no blob for <id>"   (wrong address space:
                                              that resolver serves content-addressed SPILL
                                              blobs, not bus stream ids)
    mailbox <you> --open <content-sha>     -> "no mailbox entry for sha"

Meanwhile the body IS retrievable -- I read it with a raw `xrange(key, min=mid, max=mid)`.
So the address is CORRECT (a stream id is the message's real identity) and the RESOLVER for
that address space simply does not exist on any door.

WHY THIS IS WORSE THAN THE BARE " ...[truncated]" IT REPLACED, in one specific way: a dead
pointer looks actionable. The reader spends a door discovering it is decoration. T220's own
commit message called an unaddressed clip "a data-loss path by design"; an unresolvable
address is a data-loss path that also wastes a turn.

HOW I MISSED IT, which is the part worth keeping: I "verified T220 live" by checking the
pointer was PRINTED. I never ran the command it printed. That is testing the mechanism
instead of the wiring -- L7 -- committed inside a fix about exactly this class, on the same
night I wrote a pin against it for someone else's code.

THE FIX IS THE RESOLVER, NOT THE POINTER. Extending bifrost-fetch to accept a bus stream id
serves the address the message actually has. Rewriting the pointer to name some other door
would just move the lie.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent import bifrost_pull as BP  # noqa: E402


def _cli(*args):
    r = subprocess.run([sys.executable, "agent_cli.py", *args], cwd=REPO,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return (r.stdout or "") + (r.stderr or "")


def _send_long(body: str) -> str:
    """Send a body long enough to clip, return its stream id."""
    sys.path.insert(0, str(REPO))
    from core.comm.bus import Bus
    return str(Bus("claude").send("claude", "note", body) or "")


def test_the_pointer_a_clipped_render_prints_actually_resolves():
    """THE PIN. Not 'a pointer was printed' -- run the command it printed and require the
    body back. That distinction is the whole defect."""
    body = "T222 PROBE HEAD. " + ("pad " * 900) + " T222 PROBE TAIL SENTINEL."
    mid = _send_long(body)
    assert mid, "could not send a probe message"

    line = BP.format_inbox_line({"frm": "claude", "kind": "note", "content": body,
                                 "id": mid}, max_len=200)
    assert "[truncated]" in line and mid in line

    # Extract the command the render told the reader to run, and RUN IT.
    assert "bifrost-fetch --get" in line, f"unexpected pointer shape: {line[-120:]}"
    got = _cli("bifrost-fetch", "--get", mid)
    assert "no blob" not in got.lower(), (
        f"the render told the reader to run `bifrost-fetch --get {mid}` and that command "
        f"cannot resolve it -- the pointer is decoration:\n{got[:300]}")
    assert "TAIL SENTINEL" in got, (
        "resolver returned something, but not the clipped body's tail -- a partial "
        "reconstruction is still a data-loss path")


def test_a_bad_ref_still_fails_loudly():
    """The resolver must not become permissive while gaining an address space. A miss stays
    a LOUD miss -- a fetch that silently returns nothing would be the same defect wearing
    the opposite costume."""
    got = _cli("bifrost-fetch", "--get", "9999999999999-0")
    assert "no" in got.lower() or "not" in got.lower(), \
        "an unresolvable ref must say so rather than returning empty"


def test_spill_blobs_still_resolve():
    """REGRESSION. bifrost-fetch's original job is the T113 spill blob, and gaining a second
    address space must not cost the first one -- that is how a fix becomes a fork."""
    sys.path.insert(0, str(REPO))
    from core.comm.blobs import get_blob_store

    ref = get_blob_store().put(b"T222 spill regression payload")
    got = _cli("bifrost-fetch", "--get", ref)
    assert "spill regression payload" in got, f"broke the original resolver: {got[:200]}"
