"""Pins: the Ctrl+N + handoff + start-new-session combo, and its door.

Daniel, 2026-10-06: "Lets build those and verbify the Ctrl + N and handoff + start new session
combo." Design sec.6 step 5 already named it ``desktop_prompt``.

WHY THE COMBO NEEDS ITS OWN PINS AND NOT JUST THE ACTUATOR'S. The actuator's pins
(``test_the_actuator_refuses_before_it_acts.py``) cover ONE action at a time. A combo fails
differently: it fails by CARRYING ON. Last night the same sequence worked by hand with
``time.sleep()`` between steps, which is not a verb but an anecdote -- nothing asserted anything,
so the only reason it worked is that the frames happened to arrive in time. The specific danger
is a chain that proceeds past a failed focus, because the next step then types a handoff brief
into whatever window the operator actually has in front of them.

THE RECEIPT IS A FILE, NOT A PIXEL. Claude Desktop writes one JSONL per session under
``~/.claude/projects/<slug>/`` -- measured: 56 transcripts in ``C:\\Users\\L5\\.claude\\
projects\\E--`` on this host. So "did a new session start and did it receive MY text" is
answerable on the filesystem rather than by screenshot, which is the causal proof design sec.6
step 4 asks for and the one thing the UI cannot fake.

MEASURED STATE OF THE DOOR WHEN THESE WERE WRITTEN, which is also why no live drill runs here:
``py agent_cli.py screen status`` reported ``locked=True foreground_hwnd=0``, the window found
at hwnd 67692 / pid 24836 / dpi 144, and **verbs permitted: NONE** -- because the ``screen.*``
tiers sit in no role template, so even the super_admin claude seat holds none of them. Both of
those are correct refusals, and together they mean the combo cannot be drilled unattended. That
is the design's intent (step 4 is "attended"), not a gap in these pins.

Run::

    py -m pytest tests/test_the_new_session_combo_has_a_door.py -q
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.screenspace import combo as C  # noqa: E402

CLI = str(ROOT / "agent_cli.py")


def _run(*args, timeout=120):
    return subprocess.run([sys.executable, "-X", "utf8", CLI, *args],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=timeout,
                          stdin=subprocess.DEVNULL)


# ------------------------------------------------------------------ the door
def test_the_screen_verb_is_registered():
    """An actuator reachable only from Python is one the fleet will not use -- and
    check_wiring.py flagged exactly this module as "built != wired" until the verb landed."""
    r = _run("--help")
    assert "screen" in (r.stdout + r.stderr), "agent_cli has no `screen` verb"


def test_the_three_actions_are_positional_choices_not_subparsers():
    """House convention, and not a style note: the door-parity checker reads add_subparsers as
    separate VERBS, which is how `recall-audit` first arrived as three phantom ones
    (pack/score/recall_audit). `fence` set the convention at agent_cli.py:9213."""
    r = _run("screen", "--help")
    out = r.stdout + r.stderr
    assert "{status,locate,prompt}" in out.replace(" ", ""), out[:400]


def test_status_is_read_only_and_names_what_it_would_refuse():
    """The preflight as a READ. Every refusal the combo can raise should be answerable before a
    caller commits to a sequence, because "why did it refuse" is the question an operator
    actually asks -- and on a locked workstation it is the only question."""
    r = _run("screen", "status", "--json")
    assert r.returncode == 0, r.stderr[:400]
    doc = json.loads(r.stdout)
    for key in ("seat", "uia", "workstation_locked", "foreground_hwnd", "windows", "caps",
                "session_dir", "session_count"):
        assert key in doc, f"status does not report {key!r}"
    assert set(doc["caps"]) >= {"focus", "type", "keys", "invoke"}, doc["caps"]
    for verb, c in doc["caps"].items():
        assert "allowed" in c and "why" in c, (
            f"caps[{verb}] does not say WHY -- a refusal with no remedy is a dead end")


def test_status_does_not_act():
    """A status call must not move the operator's focus. Pinned at the source level because the
    cost of discovering this empirically is the operator losing their window mid-sentence."""
    src = inspect.getsource(C.status)
    for forbidden in ("SendKeys", '"focus"', "'focus'", "SetForegroundWindow", "Click"):
        assert forbidden not in src, (
            f"status() references {forbidden!r} -- a read-only door that focuses or types is "
            f"not read-only")


# ------------------------------------------------------------------ fail-closed
def test_the_combo_refuses_without_the_caps():
    """Measured: `screen status` reported "verbs permitted: NONE" for the super_admin claude
    seat, because the screen tiers are in no role template. The combo must therefore refuse
    end-to-end, not merely log and continue."""
    r = _run("screen", "prompt", "this text must never reach a window", "--json")
    doc = json.loads(r.stdout or "{}")
    assert doc.get("status") == "refused", (
        "the combo did not refuse although the seat holds no screen.* cap: %r" % (doc,))
    assert r.returncode != 0, "a refused combo exited 0"


def test_a_refusal_stops_the_chain_rather_than_continuing():
    """THE COMBO-SPECIFIC PIN. Every step is followed by a return on failure; a chain that
    proceeds past a failed focus types into whatever the operator is looking at."""
    src = inspect.getsource(C.new_session_prompt)
    # every `step(...)` for an acting verb must be followed by a guarded early return
    assert src.count("return stop(") >= 5, (
        "fewer early returns than acting steps -- at least one step can fail and let the chain "
        "continue")
    assert "if not r.ok:" in src, "no step checks its own result"


def test_submit_defaults_to_not_sending():
    """Design step 3 is "Dry actions ... no submit". Submitting is a separate, explicit decision
    and must never be the default of a verb that drives a real desktop."""
    sig = inspect.signature(C.new_session_prompt)
    assert sig.parameters["submit"].default is False
    r = _run("screen", "--help")
    assert "--submit" in (r.stdout + r.stderr), "there is no explicit opt-in to sending"


def test_the_four_outcomes_are_not_a_bool():
    """`staged` (typed, not sent) and `unverified` (sent, read-back blind) are real results that
    a bool rounds to the wrong neighbour in opposite directions."""
    src = inspect.getsource(C)
    for status in ("ok", "staged", "unverified", "refused"):
        assert '"%s"' % status in src, f"the {status!r} outcome does not exist"


# ------------------------------------------------------------------ the receipt plane
def test_the_session_dir_is_derived_not_guessed():
    """This host has SIX project folders (``E--``, ``E--AI-Setup``, ``C--Users-L5``, ...), so a
    slug computed from cwd picks the wrong one. The dir is found by locating our OWN transcript,
    which is the only self-verifying answer to "where will a sibling session land"."""
    src = inspect.getsource(C.session_dir)
    assert "ambient_session_id" in src, (
        "session_dir() does not locate our own transcript; it is guessing the slug")
    d = C.session_dir()
    if d is None:
        pytest.skip("no ~/.claude/projects on this host")
    assert d.is_dir()
    assert (C.projects_root() in d.parents) or d.parent == C.projects_root()


def test_session_files_is_a_snapshot_that_can_detect_a_new_one():
    d = C.session_dir()
    if d is None:
        pytest.skip("no ~/.claude/projects on this host")
    before = C.session_files(d)
    assert isinstance(before, frozenset)
    assert before, "no transcripts found -- the receipt plane would never fire"
    # the receipt is set difference, so a new name must be detectable
    assert (before | {"zzz-not-real.jsonl"}) - before == {"zzz-not-real.jsonl"}


def test_the_nonce_is_embedded_so_the_receipt_is_causal():
    """Without a nonce in the text, "a new session appeared" proves a session appeared -- not
    that it got OUR brief. The nonce is what makes it causal rather than coincident."""
    n = C.make_nonce("some brief")
    assert n and len(n) >= 8
    assert "{nonce}" in C.RECEIPT_TEMPLATE
    assert n in C.RECEIPT_TEMPLATE.format(nonce=n)
    assert C.make_nonce("a") != C.make_nonce("b")


def test_the_centre_strip_is_small_enough_to_be_a_cheap_postcondition():
    """Measured: hashing the whole 8.4M-pixel window costs 88 ms AND changes on any repaint
    anywhere -- a streaming reply alone would trip it every time. A guard that always fires is
    a guard nobody keeps."""
    l, t, w, h = C._centre_strip((-11, -11, 3851, 2171))
    assert w * h <= 200_000, "the post-condition region is too large to be cheap (%dx%d)" % (w, h)
    assert w > 0 and h > 0


def test_text_is_staged_through_the_clipboard_not_through_sendkeys():
    """SendKeys is a little language: ``{}()!+^%`` are syntax and ``{a 3}`` is a repeat count.
    Prose pushed through it does not merely garble, it EXECUTES -- and a brief that arrives
    corrupted is worse than one that never arrives, which is this house's oldest identity law."""
    from core.screenspace import act as A
    src = inspect.getsource(A.act)
    assert "_clip_set" in src, "the type verb does not use the clipboard"
    assert "_escape_sendkeys" in src, (
        "the degraded SendKeys path is unescaped; unescaped prose executes")
    # and the escaper must actually neutralise the dangerous set
    out = A._escape_sendkeys("{a 3} (b) 50% ^x !y +z")
    for ch in "{}()":
        assert ("{%s}" % ch) in out or ("{{}" in out and "{}}" in out), out
    assert "{%}" in out and "{^}" in out and "{!}" in out and "{+}" in out, out
