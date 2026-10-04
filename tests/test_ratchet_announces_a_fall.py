"""RED pins: the ratchet never says when debt FALLS, so the slack is silent.

THE GAP, found by walking into it on 2026-10-03. `ratchet_ok` refuses a RISE and is silent
otherwise -- it returns (True, "") whether debt held or dropped. Its own docstring says the
remedy is manual: "Pay it down and re-baseline." That is the right design; an automatic
tighten would let a transiently broken checker lock in a low count nobody can reach again.

But it makes the moment right after paying debt down the moment the gate is WEAKEST, and
nothing tells you. Measured: check_session_resolvers was adopted at 16, four sites were
migrated in d28ccc6a, and the baseline still read 16 against a live 12 -- four free slots a
peer could have filled without the gate firing. It was closed only because the author happened
to re-read the number. Every guard in GUARDRAILS is exposed to the same thing.

This is the same genus as `_count_violations`'s own warning, which the same day produced a
baseline of 1 against 16: "a baseline built from a wrong count is not a ratchet, it is a
rubber stamp with room to absorb twelve new violations silently." A baseline left ABOVE the
true count is that rubber stamp arriving by a different road.

WHAT IS DELIBERATELY NOT ASKED FOR. No automatic re-baseline. The second step stays a human
decision and a recorded one; the only thing missing is that nobody is TOLD the first step
happened. A ratchet that tightens itself is a different and more dangerous machine.

Run::

    py -m pytest tests/test_ratchet_announces_a_fall.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "githooks"))

import pre_commit as pc  # noqa: E402


def test_a_fall_still_passes():
    """RATCHET. Paying debt down must never block a commit."""
    ok, _ = pc.ratchet_ok(baseline={"check_x": 16}, live={"check_x": 12})
    assert ok is True


def test_a_fall_is_ANNOUNCED_with_both_numbers():
    """THE PIN. Silence after a fall is how the slack persists. The message must carry the
    old and the new count, because 'debt fell' without numbers does not tell you how much
    room the gate is now carrying."""
    ok, msg = pc.ratchet_ok(baseline={"check_x": 16}, live={"check_x": 12})
    assert ok is True
    assert msg, "a fall from 16 to 12 was reported as silence"
    assert "check_x" in msg and "16" in msg and "12" in msg, msg
    assert "baseline" in msg.lower(), (
        "the notice does not name the remedy -- being told debt fell is only useful if it "
        "also says to re-baseline: %r" % msg)


def test_holding_steady_stays_quiet():
    """No nag. A gate that speaks on every commit is one nobody reads, and the existing
    guards hold steady on almost every commit."""
    ok, msg = pc.ratchet_ok(baseline={"check_x": 5}, live={"check_x": 5})
    assert ok is True and msg == "", "a steady guard produced output: %r" % msg


def test_a_rise_still_blocks_and_outranks_a_fall():
    """RATCHET, and the ordering matters: a commit that pays one guard down while breaking
    another must still be refused, with the RISE as the message."""
    ok, msg = pc.ratchet_ok(baseline={"check_a": 10, "check_b": 1},
                            live={"check_a": 2, "check_b": 7})
    assert ok is False, "a rise was forgiven because something else fell"
    assert "check_b" in msg and "INCREASED" in msg.upper(), msg


def test_a_crashed_guard_still_outranks_a_fall():
    """-1 means the guard did not RUN. Absence is not a pass, and must not be masked by
    good news from a neighbour."""
    ok, msg = pc.ratchet_ok(baseline={"check_a": 10, "check_b": 1},
                            live={"check_a": 2, "check_b": -1})
    assert ok is False and "check_b" in msg, msg


def test_the_hook_actually_prints_the_notice():
    """The message is currently DISCARDED on success -- the caller reads _r_msg only inside
    `if not _r_ok`. A notice nothing prints is the unwired-keystone shape, so pin the wiring
    and not just the string."""
    import ast
    src = (ROOT / "scripts" / "githooks" / "pre_commit.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # COMPARE LINE NUMBERS, NOT TEXT. The first version unparsed the `if not _r_ok:` node and
    # looked for that string in the source -- but ast.unparse NORMALISES (quotes, wrapping,
    # spacing), so the needle never appeared in the haystack, the "rest of file" came back
    # empty, and the pin failed against a correct fix. A pin that compares generated text to
    # authored text is measuring the formatter.
    blocks = [n for n in ast.walk(tree)
              if isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
              and isinstance(n.test.op, ast.Not)
              and getattr(n.test.operand, "id", "") == "_r_ok"]
    assert blocks, "could not find the `if not _r_ok:` guard at all"
    end = max(b.end_lineno or b.lineno for b in blocks)

    uses_after = [n.lineno for n in ast.walk(tree)
                  if isinstance(n, ast.Name) and n.id == "_r_msg" and n.lineno > end]
    assert uses_after, (
        "pre_commit reads _r_msg only inside the `if not _r_ok:` block (ends line %d), so a "
        "fall notice would be computed and thrown away" % end)

    # REACHABILITY, not just presence. The check above passed against `if False:` wrapped
    # around the write -- a notice that exists in the source and can never print. Mutation
    # testing surfaced it: the harness refused the mutation as NULL-APPLY on a bad anchor, so
    # I ran it by hand and the pin went green over dead code. "Referenced" is not "reached",
    # and a pin that cannot tell them apart is evidence about the pin.
    dead = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        t = node.test
        is_const_false = (isinstance(t, ast.Constant) and not t.value)
        if not is_const_false:
            continue
        if any(isinstance(n, ast.Name) and n.id == "_r_msg" for n in ast.walk(node)):
            dead.append(node.lineno)
    assert not dead, (
        "the fall notice sits inside a constant-false branch at line(s) %s -- it is in the "
        "source and unreachable, which is worse than absent because it reads as wired" % dead)
