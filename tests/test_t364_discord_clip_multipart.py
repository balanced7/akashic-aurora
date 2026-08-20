"""T364 RED: Discord clip posts N whole-line parts instead of one truncated shell command.

Vandor's handoff, 2026-08-19 (granting hands): the bridge and rooms render a body over
2000 chars as ONE truncated post whose tail carries `bifrost-fetch --get <id>` — a SHELL
command. The reader is Daniil on a phone. An unaddressable clip was already the T220/T222
defect restated; a shell command he cannot run is the same defect wearing gloves. The fix:
split the body into WHOLE-LINE chunks, each under the cap, and post N parts — no part
exceeds DISCORD_MAX, no chunk splits a word, and no chunk splits a markdown fence.

Run:  py -m pytest tests/test_t364_discord_clip_multipart.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import discord_bridge as DB  # noqa: E402


# ---------------------------------------------------------------- the chunker
def test_chunk_fits_under_cap_never_splits_a_word():
    """The core law: N parts, every part <= max_len, no word torn across a boundary."""
    words = ["alpha", "bravo", "charlie"]
    parts = DB.chunk(" ".join(words), max_len=12)
    # "alpha bravo" = 11 chars fits; "charlie" must move to its own part, not split
    assert parts == ["alpha bravo", "charlie"], parts


def test_chunk_keeps_a_markdown_fence_whole():
    """A ``` ... ``` block is one reader unit; splitting it across parts breaks the
    phone's code rendering and reads as corruption."""
    text = "before\n```python\ndef f():\n    return 1\n```\nafter"
    parts = DB.chunk(text, max_len=1000)
    joined = "\n".join(parts)
    assert "```python\ndef f():" in joined
    # the fence opener and its closer must live in the SAME part
    for p in parts:
        if "```python" in p:
            assert "```" in p[len("```python"):], (
                f"a fence was opened and not closed in the same part: {p!r}")


def test_chunk_never_exceeds_the_cap_even_for_fences():
    """A fence block LONGER than the cap must still come out in parts that fit —
    atomic-until-impossible, then hard-split at a word boundary."""
    long_line = "word " * 500                        # ~2500 chars, no newlines
    parts = DB.chunk("```\n" + long_line + "\n```", max_len=500)
    assert len(parts) > 1, "a body over the cap must yield >1 part"
    assert all(len(p) <= 500 for p in parts), parts
    for p in parts:
        assert not p.rstrip().endswith(" "), f"a part ends mid-boundary: {p!r}"


def test_chunk_of_a_short_body_is_one_part():
    assert DB.chunk("one short line", max_len=2000) == ["one short line"]


# ------------------------------------------------------- the bridge render_parts
def test_bridge_oversize_posts_multiple_parts_no_shell_tail():
    """A body over 2000 must post >1 part, none carrying the `bifrost-fetch` shell
    command — the whole defect was that the recovery handle was un-runnable on a phone."""
    body = "\n".join(f"line {i:04d} {('x' * 60)}" for i in range(80))   # ~5800 chars
    msg = {"kind": "handoff", "frm": "deepseek", "content": body,
           "id": "1786094136458-0"}
    parts = DB.render_parts(msg)
    assert len(parts) > 1, "an oversize body must produce multiple parts, not one clip"
    for p in parts:
        assert len(p) <= DB.DISCORD_MAX, "Discord rejects any part over 2000 outright"
        assert "bifrost-fetch" not in p and "clipped" not in p, (
            f"a part carries the phone-un-runnable shell handle: {p[:80]!r}")


def test_bridge_short_body_is_one_part_with_head():
    msg = {"kind": "reply", "frm": "claude", "content": "short"}
    parts = DB.render_parts(msg)
    assert len(parts) == 1
    assert "claude" in parts[0] and "reply" in parts[0], "the head rides the single part"


# ---------------------------------------------------- the forward N-post loop
def test_forward_posts_every_part():
    """forward() must POST each part — the fix is posts, not a better-looking clip."""
    body = "\n".join(f"beat {i} {('y' * 70)}" for i in range(60))
    sent = []

    def fake_post(url, content):
        sent.append(content)
        return True

    out = DB.forward({"kind": "handoff", "frm": "deepseek", "content": body,
                      "id": "1786094136458-0"},
                     url="https://example.invalid/hook", post=fake_post)
    assert out.ok, out.why
    assert len(sent) > 1, "an oversize body must result in multiple POSTS"
    assert all(len(c) <= DB.DISCORD_MAX for c in sent), "no posted part may exceed the cap"


def test_forward_single_part_for_short_body_still_works():
    sent = []

    def fake_post(url, content):
        sent.append(content)
        return True

    DB.forward({"kind": "chat", "frm": "daniil", "content": "hi"},
               url="https://example.invalid/hook", post=fake_post)
    assert len(sent) == 1
