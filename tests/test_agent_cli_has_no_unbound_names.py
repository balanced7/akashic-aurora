"""RED pins: six names in agent_cli.py cannot resolve, and three of them fail SILENTLY.

PRE-REGISTRATION (M3). These are committed BEFORE the fix and are RED at this commit.

THE MEASUREMENT, 2026-10-05. An outside contributor (Simon, GitHub s1-f0) ran basedpyright in
standard mode and reported F821 at six sites in `agent_cli.py`. Verified here twice: once by
lexical scope resolution (module bindings from `tree.body` ONLY -- an `ast.walk` collects
function-local imports and falsely clears four of the six, which my first checker did), and
once at runtime by importing the module:

    agent_cli.get_agent_memory   ABSENT     _continuity_drift:1910
    agent_cli.capture_event      ABSENT     _wish_curate_run:2419, _wish_write:2501
    agent_cli.io                 ABSENT     cmd_season_score:6201
    agent_cli.time               ABSENT     cmd_locks:7957
    agent_cli.REPO               ABSENT     cmd_tool_run:10250

WHY THIS IS A SILENT-ORGAN DEFECT AND NOT A TYPO. Three of the six sit inside a fail-soft
handler -- `except Exception: pass`, or a function-wide `try` returning a falsy default. A
handler written to absorb runtime DATA errors also absorbs NameError, which is a STATIC
defect. So the failure that should be loudest is the one most reliably hidden, and it renders
as a measured zero indistinguishable from the honest answer.

Two consequences, both measured before these pins were written:

  THE DRIFT LINE HAS NEVER RENDERED. The only production caller is `agent_cli.py:2214`,
  `_continuity_drift()` with NO arguments, so `notes is None`, so line 1910 runs the unbound
  `get_agent_memory()`, and the function's outer `except Exception: return ""` eats it. Its
  docstring says "Silent when the notes are newer than HEAD -- no drift, no line", so the
  absence reads as *no drift*.

  THE WISH DOOR HAS NEVER EMITTED AN EVENT. 254 wishes in docs/WISHLIST.md against 0 events
  with kind='wish', scanned over 11,242 events across 58 `events:*:raw` streams. The spine is
  healthy (touch 3,037, learning 718, decision 393); it is specifically `wish` that is absent.

WHY THE EXISTING TESTS ARE ALL GREEN, WHICH IS THE REAL LESSON HERE
-------------------------------------------------------------------
`tests/test_continuity_drift.py` has four tests. ALL FOUR pass `notes=` explicitly (lines 51,
63, 70, 80). The only real caller passes nothing. So four green tests pin a code path that
production never takes, and the path production DOES take has never been exercised once.

That is yesterday's `match_text` error in a different file: nine pins on the seam I believed
in, none on the seam that runs. The generalisable rule, and the reason this file exists:

    PIN THE PRODUCTION CALL SHAPE. A test that supplies an optional argument the only real
    caller omits is a test of a path that does not exist.

So the pins below call these functions the way the repo calls them, with no arguments, and
assert on the namespace rather than on prose about the namespace.

Run::

    py -m pytest tests/test_agent_cli_has_no_unbound_names.py -q
"""
from __future__ import annotations

import ast

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import agent_cli as A  # noqa: E402


#: The six, with the function each one is reached from. Kept as data so a fix that resolves
#: only some of them fails with WHICH remain rather than only that the count moved.
UNBOUND = [
    ("get_agent_memory", "_continuity_drift"),
    ("capture_event", "_wish_curate_run"),
    ("capture_event", "_wish_write"),
    ("io", "cmd_season_score"),
    ("time", "cmd_locks"),
    ("REPO", "cmd_tool_run"),
]


# ------------------------------------------------------------- the name resolves IN ITS SCOPE
#
# THE FIRST VERSION OF THIS SECTION PINNED THE WRONG THING, and the record belongs here
# because it would have forced a worse design. It asserted `hasattr(agent_cli, name)` -- a
# MODULE-LEVEL attribute. But this file's established idiom is the function-local import
# (lines 166, 294, 314, 327, 444, 703, 1453 ...), which is correct here: it avoids import
# cycles through core.* and keeps CLI startup cheap. The fix uses that idiom, so the six
# names are now bound inside their own functions and `hasattr` on the module is STILL False.
#
# Had I kept those pins, the only way to make them green would have been to hoist six
# imports to module scope to satisfy a test, which is the tail wagging the dog. The contract
# that actually matters is NOT "the module carries the name" but "the name resolves wherever
# it is read" -- so these pin scope resolution per site, at the granularity of the defect.
@pytest.mark.parametrize("name,where", UNBOUND, ids=[f"{n}:{w}" for n, w in UNBOUND])
def test_the_name_resolves_in_the_function_that_reads_it(name, where):
    sys.path.insert(0, str(ROOT / "scripts" / "checkers"))
    import check_unbound_names as C

    tree = ast.parse((ROOT / "agent_cli.py").read_text(encoding="utf-8-sig"))
    r = C._Resolver(tree, lazy_annotations=False)
    for st in tree.body:
        r.visit(st)

    hits = [(ln, nm, w) for ln, nm, w in r.violations if nm == name and w == where]
    assert not hits, (
        "`%s` resolves in no scope inside %s (line %d). It raises NameError when reached; "
        "where the site sits inside a fail-soft `except Exception` it raises SILENTLY and "
        "the organ reports a false zero."
        % (name, where, hits[0][0]))


# --------------------------------------------------------- the class, closed by scope analysis
def test_no_function_in_agent_cli_reads_a_name_nothing_binds():
    """RATCHET ON THE CLASS, not the six instances.

    `when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`: six named sites in one
    file is an instance list, not a sweep. This closes the class inside agent_cli.py so a
    seventh cannot arrive quietly. The repo-wide version is
    scripts/checkers/check_unbound_names.py, on a counted ratchet.

    IT DELEGATES TO THE CHECKER AND DOES NOT RE-DERIVE THE RULE, and that is load-bearing.
    The first version of this test hand-rolled its own scope resolver. The two instruments
    then DISAGREED -- the checker said 6 and the test said 87 -- and the test was wrong:
    every one of its 81 extra findings was a CLOSURE (`args` read inside the nested `_invoke`
    is bound in the enclosing `cmd_run`), plus module dunders like `__file__`. A test-local
    resolver has no enclosing-scope chain, so it reports every closure read in the file.

    That is this house's own law arriving on schedule: "a private verdict WILL grow weaker
    public twins -- if a probe is good enough for the send path it must be public, or every
    other surface reinvents it badly." One resolver, one meaning (G5's
    one-derivation-function). The disagreement is the only reason the weaker twin was caught,
    which is an argument for two instruments and against two implementations.
    """
    sys.path.insert(0, str(ROOT / "scripts" / "checkers"))
    import check_unbound_names as C

    rel = "agent_cli.py"
    src = (ROOT / rel).read_text(encoding="utf-8-sig")
    tree = ast.parse(src, filename=rel)
    r = C._Resolver(tree, lazy_annotations=any(
        isinstance(n, ast.ImportFrom) and n.module == "__future__"
        and any(a.name == "annotations" for a in n.names) for n in tree.body))
    for st in tree.body:
        r.visit(st)

    offenders = sorted({"%s:%d `%s` in %s" % (rel, ln, nm, where)
                        for ln, nm, where in r.violations})
    assert not offenders, (
        "%d bare name(s) in agent_cli.py resolve in no scope:\n  %s"
        % (len(offenders), "\n  ".join(offenders))
    )


# -------------------------------------------------- the production call shape, stated as a pin
def test_the_drift_line_is_reached_through_the_shape_the_only_caller_uses(monkeypatch):
    """THE LESSON PIN. agent_cli.py:2214 calls `_continuity_drift()` with NO arguments.

    All four tests in tests/test_continuity_drift.py pass `notes=` and are green; none of them
    takes this path, which is why six months of green said nothing about an organ that has
    never once produced output.

    This pin does not assert a drift line appears -- that depends on store contents. It
    asserts the no-argument path does not die on an unbound name, by checking the one thing
    that path needs and does not have.
    """
    import core.learning.agent_memory as AM

    reached = []
    real = AM.get_decisions if hasattr(AM, "get_decisions") else None   # noqa: F841

    class _Mem:
        def get_decisions(self, days=90):
            reached.append(days)
            return []

    monkeypatch.setattr(AM, "get_agent_memory", lambda *a, **k: _Mem())

    out = A._continuity_drift()          # <- NO ARGUMENTS. The production shape, exactly.

    assert isinstance(out, str), out
    assert reached, (
        "_continuity_drift() with no notes never reached the memory layer. Its own "
        "`except Exception: return ''` swallowed a NameError on the unbound "
        "`get_agent_memory`, so the drift line has never rendered and its absence is "
        "indistinguishable from 'no drift'. The four tests in test_continuity_drift.py all "
        "pass notes= and never take this path.")
    assert reached == [90], "the production path asked for a different window: %r" % reached


def test_the_wish_door_reaches_a_real_capture_event():
    """The wish door builds a careful `detail` payload and hands it to `capture_event` inside
    `except Exception: pass`. Measured: 254 wishes filed, 0 events with kind='wish'.

    Pinned at the import this file actually performs, and on the callable being real -- not
    on a module attribute, for the reason given above the parametrised pins. An import that
    resolves to nothing callable would be the same defect wearing a successful import.
    """
    from core.events.event_log import capture_event
    assert callable(capture_event)

    src = (ROOT / "agent_cli.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(src)
    for fn in [n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in ("_wish_write", "_wish_curate_run")]:
        imports_it = any(
            isinstance(n, ast.ImportFrom) and n.module == "core.events.event_log"
            and any(a.name == "capture_event" for a in n.names)
            for n in ast.walk(fn))
        assert imports_it, (
            "%s calls capture_event without importing it, so the call raises NameError into "
            "its own `except Exception: pass` and the wish never reaches the events spine."
            % fn.name)
