"""
T202 -- name the cause of death, and say what to do about it. RED before impl.

PRIOR ART, adopted with one correction. data4sci's agentic-harness write-up classifies
errors by CAUSE and gives each class its own recovery: transient -> backoff and retry;
tool misuse -> feed the error back; MISSING INFORMATION -> re-plan, NOT blind retry;
policy violation -> halt. Our redrive is blind: three attempts on a fixed schedule
regardless of why the first failed.

THE MEASUREMENT that made this worth building (2026-08-06, 336h window). 26 dead asks
across 12 peers, and they are not one failure wearing one costume:
    deepseek x9              launchable, ATTENDED right now        27 redrives
    codex_019f9924 x2, codex_019faa7a x1, codex_root_019fab2d x1   12 redrives, all to
                             SESSION-SUFFIXED incarnation ids
    kimi x3, sol x2, deepseek-review x2, codex_root x1,
    opus-engineer x1, cursor_grok x1, t147probe x1                 real seats, down
    claude x2                self-addressed, died while ATTENDED
Four different situations, four different right moves, one undifferentiated "DEAD".

FENCED WITH DEEPSEEK, AND IT KILLED HALF THE DESIGN. Both objections stand:

  (A) I proposed a DEAD_INCARNATION class on the claim that a session id is never
      reissued, so redriving one is PROVABLY futile. Overclaimed. deepseek: mail to an
      orphan address can still be caught if the transport re-homes or prefix-routes it.
      Verified in our own code -- reaper.py's first line is "a dead seat's unread
      directed mail re-homes, loudly. Never stranded." So the class COLLAPSES into
      SEAT_DOWN. It survives here only as STALE_INCARNATION: a routing HINT (re-address
      to the base seat, which is cheaper and more likely to be read), never a verdict of
      futility. Pinned below, because "provably futile" was exactly the kind of confident
      claim this repo's instruments exist to refuse.

  (B) I wanted to keep "preflight never gates the send" AND shorten futile redrives.
      deepseek: "redrive is still a send" -- skipping one because of a classification is
      gating with extra steps, one decision point later. It is also the SAME window: the
      expectation dies when redrives are exhausted, so fewer redrives is a shorter
      late-binding window, which is precisely what the law protects. That law was
      empirically vindicated (an ask sent to a provably-absent peer settled ANSWERED at
      540.9s). So this slice changes NO transport policy at all.

WHAT IS LEFT IS STILL THE POINT: the caller learns in one second which of four situations
it is in and what to do, instead of discovering it thirty minutes later by hand. Same
shape as T197 -- observe, report, never gate.

Run: py -m pytest tests/test_t202_failure_class.py -q
"""
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import failure_class as FC  # noqa: E402


# --------------------------------------------------------------------------------------
# The four classes, each keyed to a real row from the measurement above.
# --------------------------------------------------------------------------------------

def test_attending_but_silent_is_not_a_transport_problem():
    """deepseek x9 / claude x2. The peer was home the whole time. Retrying transport
    cannot fix a consumer that is reading the wrong lane or is wedged."""
    v = FC.classify("deepseek", attending=True, base_attending=False,
                    launchable=True, known_seat=True)
    assert v["klass"] == "SEAT_SILENT"
    assert "retry" not in v["recovery"].lower() or "not" in v["recovery"].lower()
    assert any(w in v["recovery"].lower() for w in ("lane", "consum", "wedge", "nudge"))


def test_known_seat_down_keeps_the_late_binding_answer_alive():
    """kimi / sol / deepseek-review. Down now, can come up -- the 540.9s case. The
    advice must NOT be 'give up'; it must be launch-or-wait."""
    v = FC.classify("kimi", attending=False, base_attending=False,
                    launchable=False, known_seat=True)
    assert v["klass"] == "SEAT_DOWN"
    assert "give up" not in v["recovery"].lower()


def test_launchable_down_seat_is_told_to_launch():
    v = FC.classify("deepseek", attending=False, base_attending=False,
                    launchable=True, known_seat=True)
    assert v["klass"] == "SEAT_DOWN"
    assert "launch" in v["recovery"].lower()


def test_stale_incarnation_is_a_routing_hint_not_a_verdict():
    """THE CORRECTED CLASS (deepseek's A). codex_root_019fab2d -> re-address codex_root.
    It must recommend the cheaper route WITHOUT claiming the old address is hopeless --
    the reaper re-homes orphan mail, so futility is not ours to assert."""
    v = FC.classify("codex_root_019fab2d", attending=False, base_attending=True,
                    launchable=False, known_seat=True)
    assert v["klass"] == "STALE_INCARNATION"
    assert "codex_root" in v["recovery"], "must name the base seat to re-address"
    for forbidden in ("never", "futile", "impossible", "cannot be answered", "hopeless"):
        assert forbidden not in v["recovery"].lower(), (
            f"'{forbidden}' overclaims: reaper.py re-homes orphan mail, so this address "
            f"is unlikely to be read, not provably dead")


def test_unknown_peer_says_so_without_claiming_certainty():
    """t147probe: no seat, no base, no history."""
    v = FC.classify("t147probe", attending=False, base_attending=False,
                    launchable=False, known_seat=False)
    assert v["klass"] == "UNKNOWN_PEER"


def test_every_class_carries_an_actionable_recovery():
    """A classification with no next move is a label, not a diagnosis."""
    for klass in FC.CLASSES:
        assert FC.RECOVERY[klass].strip(), f"{klass} has no recovery advice"


# --------------------------------------------------------------------------------------
# The two laws the fence bought. These are the pins that matter most.
# --------------------------------------------------------------------------------------

def test_classification_changes_no_transport_policy():
    """DEEPSEEK'S (B), PINNED AS LAW: 'redrive is still a send'. This module must be a
    pure READER -- it may not send, arm, sweep, settle, or touch redrive counts. A future
    optimizer will be tempted to 'save' the 12 futile redrives; that is gating one
    decision point later, and it shortens the late-binding window the 540.9s answer
    proved is real.

    READ AS NAMES, NOT TEXT -- and this pin's first cut proved the point on itself, for
    the THIRD time in one session (after T171 K6 and T197c). The module docstring
    contains the word "settled" while EXPLAINING that it settles nothing, so a raw-source
    scan for "settle" went red on the prose describing its own compliance. An AST walk
    reads identifiers and cannot see a docstring at all.
    """
    import ast

    tree = ast.parse(inspect.getsource(FC))
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            referenced.update((node.module or "").split("."))
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)

    for forbidden in ("REDRIVES", "redrives_left", "send", "send_reply", "arm", "sweep",
                      "settle", "xadd", "hset", "Bus", "capture_event"):
        assert forbidden not in referenced, (
            f"{forbidden}: classification DIAGNOSES, it never changes transport policy")


def test_classify_is_pure():
    """No I/O: the caller supplies the observations, so the taxonomy is testable without
    a bus and cannot silently start probing on a hot path."""
    src = inspect.getsource(FC.classify)
    for forbidden in ("import ", "attendance(", "Bus(", "_client("):
        assert forbidden not in src, f"classify must stay pure ({forbidden})"


def test_no_class_asserts_futility_anywhere():
    """The whole-module version of the STALE_INCARNATION pin. reaper.py re-homes orphan
    mail; 'this can never be answered' is a claim we cannot support for ANY class."""
    blob = " ".join(FC.RECOVERY.values()).lower()
    for forbidden in ("never be answered", "provably futile", "impossible", "hopeless"):
        assert forbidden not in blob


def test_unknown_is_reachable_when_observations_are_missing():
    """The house law one layer up: absence of evidence is not evidence of absence."""
    v = FC.classify("whoever", attending=None, base_attending=None,
                    launchable=None, known_seat=None)
    assert v["klass"] == "UNCLASSIFIED"
    assert v["recovery"]
