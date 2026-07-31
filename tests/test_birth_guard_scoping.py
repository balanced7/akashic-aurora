"""rule-13 must judge only the paths the commit names -- the C2-4 invariant, enforced.

THE DEFECT (live, 2026-07-31): mirror.py's named-path mode is scoped everywhere except here.
It stages exactly the named paths, computes `staged` scoped to them, and runs the rule-8
mojibake guard over that scoped list -- with an explicit comment at the staging site:

    "the index is SHARED between seats -- another agent's staged work may be sitting in it.
     Named-path mode must commit the named paths and nothing else, leaving stranger staged
     entries staged for their own author."

But rule-13 is invoked as `[sys.executable, hook13]` with NO ARGUMENTS, so birth_guard runs
its own unscoped `git diff --cached --diff-filter=A` over the WHOLE index. Consequence: one
seat's loose .md sitting in the shared index REFUSES an unrelated seat's commit of an entirely
allowed path, and keeps refusing until someone thinks to run `git reset`. A one-seat mistake
becomes a fleet-wide commit outage that outlives the session that caused it.

Cost on the day it was found: two false refusals on docs/ORG.md -- a crown doc the guard
allows outright -- and ~20 minutes chasing a doc-door migration that was never the problem.
The refusal names files you never touched, which is what misleads: it reads as "your artifact
is malformed", not "someone else's file is stuck in your index".

Test note: birth_guard pins `cwd=ROOT`, so it always inspects THIS repo's index no matter
where it is invoked from (correct for a git hook, untestable via a temp repo). These pins
drive the real `main()` and stub only the git read.

W111 · lesson mirror_refusal_leaves_tree_staged. Shares the blanket-stage genus with W109/W110.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD_PATH = os.path.join(ROOT, "scripts", "githooks", "birth_guard.py")

STRANGER = "research/in-flight/stranger-position.md"   # REFUSE since the P3 flip
MINE = "docs/MINE.md"                                  # crown doc -- allowed outright


@pytest.fixture()
def guard():
    spec = importlib.util.spec_from_file_location("birth_guard_under_test", GUARD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub_index(guard, monkeypatch, contents):
    """Stub the git read; record the argv the guard would have run."""
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        paths = cmd[cmd.index("--") + 1:] if "--" in cmd else None
        out = [p for p in contents if (not paths or p in paths)]

        class R:
            stdout = "\n".join(out) + ("\n" if out else "")
        return R()

    monkeypatch.setattr(guard.subprocess, "run", fake_run)
    return seen


def test_p1_scoped_call_ignores_a_strangers_staged_file(guard, monkeypatch):
    """THE defect. Naming only my own allowed path must not be refused by someone else's."""
    _stub_index(guard, monkeypatch, [STRANGER, MINE])
    rc = guard.main([MINE])
    assert rc == 0, ("rule-13 refused a commit of an allowed crown doc because ANOTHER seat's "
                     ".md was sitting in the shared index")


def test_p2_scoped_call_still_refuses_my_own_bad_path(guard, monkeypatch, capsys):
    """Scoping must not defang the guard: name the refusable file and it still refuses."""
    _stub_index(guard, monkeypatch, [STRANGER, MINE])
    rc = guard.main([STRANGER])
    assert rc != 0, "scoping must not turn rule-13 into a no-op for the paths it IS given"
    assert "stranger-position" in capsys.readouterr().out


def test_p3_unscoped_call_is_unchanged(guard, monkeypatch, capsys):
    """Backwards compatibility: no argv = judge the whole index, exactly as before.

    The pre-commit hook relies on this -- it invokes the guard bare."""
    _stub_index(guard, monkeypatch, [STRANGER, MINE])
    rc = guard.main([])
    assert rc != 0, "unscoped mode must still catch the whole index"
    assert "stranger-position" in capsys.readouterr().out


def test_p4_scoping_keeps_the_added_only_filter(guard, monkeypatch):
    """A MODIFIED tracked .md is not a birth. Scoping must narrow by PATH without dropping
    --diff-filter=A, or every edit to an existing doc would start tripping the guard."""
    seen = _stub_index(guard, monkeypatch, [MINE])
    guard.main([MINE])
    cmd = seen["cmd"]
    assert "--diff-filter=A" in cmd, f"scoped query lost the added-only filter: {cmd}"
    assert "--" in cmd and MINE in cmd[cmd.index("--") + 1:], \
        f"scoped query did not pathspec-limit to the named paths: {cmd}"


def test_p5_mirror_passes_the_scoped_list_to_rule_13():
    """The integration point: mirror must hand rule-13 its scoped list, as it already does
    for rule-8. Without this the fix exists but nothing calls it."""
    src = open(os.path.join(ROOT, "scripts", "mirror.py"), encoding="utf-8").read()
    assert "hook13" in src, "mirror.py no longer references hook13"
    # Anchor on the INVOCATION, not on a byte window -- a comment above the call site must
    # not be able to break this pin (it did, first cut).
    assert "hook13, *" in src, (
        "mirror.py still invokes birth_guard with no file arguments -- rule-13 will keep "
        "judging the whole shared index in named-path mode (C2-4 violation)")
    assert "staged13" in src, (
        "the list handed to rule-13 must derive from this invocation's STAGED set, not be "
        "re-derived from the shared index")
