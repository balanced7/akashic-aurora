"""T220 RED: a render that clips a message body must print that body's ADDRESS.

DANIIL'S ASK, verbatim, 2026-08-07: "can we make the truncation be handled by the substrate
and have it auto-reconstruct for you when you reach for it?" Filed as W137; this is the
first half -- the mint. The resolver half already exists (`bifrost-fetch --get blob:<sha>`,
T113) and `_clip_store` already mints a spill file for STORAGE clips, which is why the
outgoing seat's second letter was recoverable at all.

THE GAP IS THE DISPLAY CLIP. agent/bifrost_pull.py:19 ends a truncated body with the bare
string " ...[truncated]" and nothing else. On 2026-08-07 that cost a fresh seat roughly
eight turns and six doors -- spill dir, mailbox LIST, mailbox OPEN, bifrost-fetch, a raw
redis scan, promoted, git log -- to recover the tail of one peer note.

THE FIX IS NOT TO MINT A NEW BLOB. The body is already durable and already addressed: every
bus message carries an id, and the mailbox indexes it by sha. Minting a second copy would
create a second address for one object, which is the disease this repo is already treating.
What the render owes the reader is the address it ALREADY HAS.

An unaddressed clip is a data-loss path by design rather than by accident, because nothing
in the output says where the rest went.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agent import bifrost_pull as BP  # noqa: E402


def _msg(body: str, mid: str = "1786094136458-0", sha: str = "518bfcb0c5"):
    return {"frm": "claude", "kind": "note", "content": body, "id": mid, "sha": sha}


def test_a_clipped_body_prints_a_way_to_reach_the_rest():
    """THE PIN. Clip a long body and require a retrievable handle in the rendered line."""
    long_body = "POINT ONE. " + ("x" * 4000) + " POINT THREE, the part that got eaten."
    line = BP.format_inbox_line(_msg(long_body), max_len=200)
    assert "[truncated]" in line or "clipped" in line.lower()
    assert ("1786094136458-0" in line or "518bfcb0c5" in line), (
        "the body was clipped and the line names no address -- the reader has nothing to "
        "follow, which is exactly the six-door hunt this pin exists to prevent")


def test_the_pointer_names_the_door_not_just_the_id():
    """An id with no verb is a puzzle. The prior seat's W138 finding was that the cheapest
    reconstruction path in the system had no door in any manifest; a bare sha repeats that
    mistake in miniature."""
    long_body = "y" * 5000
    line = BP.format_inbox_line(_msg(long_body), max_len=200)
    low = line.lower()
    assert "mailbox" in low or "bifrost-fetch" in low or "--open" in low, \
        "name the door that turns this handle back into the body"


def test_an_unclipped_body_gains_no_pointer():
    """Noise on clean output gets filtered out mentally, and that is how the real notice
    gets missed. A short body is complete and needs no address."""
    line = BP.format_inbox_line(_msg("short and complete"), max_len=200)
    assert "[truncated]" not in line
    assert "mailbox" not in line.lower(), "pointer printed on a body that was never clipped"


def test_a_message_with_no_addressable_id_says_so():
    """UNKNOWN stays representable. If a render genuinely has no handle, it must say the
    rest is unreachable rather than implying the reader simply has not looked hard enough --
    that silence is what sent a seat through six doors."""
    m = {"frm": "x", "kind": "note", "content": "z" * 5000}
    line = BP.format_inbox_line(m, max_len=200)
    low = line.lower()
    assert "no address" in low or "unrecoverable" in low or "not addressable" in low, \
        "a clip with no recoverable handle must confess it, not stay quiet"
