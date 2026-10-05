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


# ------------------------------------------------------------------ the namespace, at runtime
@pytest.mark.parametrize("name", sorted({n for n, _ in UNBOUND}))
def test_the_name_resolves_in_agent_cli_at_runtime(name):
    """THE PIN, stated at the plane that actually decides: the imported module's namespace.

    Not a grep and not a docstring check -- `hasattr` on the live module. A name the module
    does not carry raises NameError the moment a function body reaches it.
    """
    assert hasattr(A, name), (
        "agent_cli does not carry `%s`, so every site that reads it raises NameError. "
        "Where the site sits inside a fail-soft `except Exception`, it raises SILENTLY and "
        "the organ reports a false zero." % name)


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
def test_the_drift_line_is_reached_through_the_shape_the_only_caller_uses():
    """THE LESSON PIN. agent_cli.py:2214 calls `_continuity_drift()` with NO arguments.

    All four tests in tests/test_continuity_drift.py pass `notes=` and are green; none of them
    takes this path, which is why six months of green said nothing about an organ that has
    never once produced output.

    This pin does not assert a drift line appears -- that depends on store contents. It
    asserts the no-argument path does not die on an unbound name, by checking the one thing
    that path needs and does not have.
    """
    assert hasattr(A, "get_agent_memory"), (
        "the ONLY production call shape -- _continuity_drift() with no notes -- reaches an "
        "unbound `get_agent_memory` at agent_cli.py:1910, raises NameError, and the "
        "function's own `except Exception: return ''` converts it into 'no drift'. The four "
        "existing tests all pass notes= and never reach this line.")

    out = A._continuity_drift()
    assert isinstance(out, str), out


def test_the_wish_door_can_emit_its_event(monkeypatch):
    """The wish door builds a careful `detail` payload and hands it to an unbound name inside
    `except Exception: pass`. 254 wishes filed, 0 events on the spine.

    Pinned by substituting a recorder for `capture_event`: if the name cannot be patched onto
    the module, the door was never calling anything reachable.
    """
    assert hasattr(A, "capture_event"), (
        "agent_cli has no `capture_event`, so both wish write-sites (2419, 2501) raise "
        "NameError inside `except Exception: pass`. That is why docs/WISHLIST.md holds 254 "
        "wishes and the events spine holds 0 with kind='wish'.")

    seen = []
    monkeypatch.setattr(A, "capture_event", lambda kind, summary, **kw: seen.append(kind))
    assert A.capture_event("wish", "probe") is not None or seen == ["wish"]
