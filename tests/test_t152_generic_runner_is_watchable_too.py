"""PRE-REGISTERED ACCEPTANCE (T152) -- the fifth runner was left out of T150.

T150 made every `scripts/bifrost_runner_<provider>.py` line-buffered and UTF-8. Its pin enumerates
runners by the prefix `bifrost_runner_`, which is exactly the set it fixed -- so it passes 5/5 while
`scripts/bifrost_runner.py`, the GENERIC wake adapter for stateless model classes, has no
reconfigure at all. The name without a suffix falls outside its own family's glob.

This is the same shape the mechanics review found one level up: the opus5 Season 1 doc recorded that
`core/coord/cognitive_metrics.py` is imported by FOUR runners, not five, and that
`scripts/bifrost_runner.py` references it zero times -- so a player fleet on the generic runner would
emit no cognitive metrics AND no watchable log. Two blind spots, one file, one cause: an
enumeration-by-prefix that cannot see the member whose name IS the prefix.

Why it matters now and not later: Daniil's Season 1 wants 10-20 concurrent players. `bifrost_runner.py`
is the adapter for API/web agent classes -- the cheapest possible player body. A season supervised
through it would be invisible for the same reason the 2026-08-03 five-seat round was invisible, and
the fix that already landed would look like it covered them.

  W1  scripts/bifrost_runner.py makes stdout line-buffered and UTF-8/replace
  W2  ...and stderr too (the bus writes its loudest notices there)
  W3  ...guarded, so an unreconfigurable stream degrades instead of killing the runner at import
  W4  the ENUMERATION is fixed, not just this one file: every bifrost_runner*.py -- including any
      future sibling -- is covered, so the next runner added cannot inherit the same hole

Run: py -m pytest tests/test_t152_generic_runner_is_watchable_too.py -q
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RUNNER_DIR = os.path.join(ROOT, "scripts")
GENERIC = "bifrost_runner.py"


def _src(f):
    return open(os.path.join(RUNNER_DIR, f), encoding="utf-8", errors="replace").read()


def _all_runners():
    """Every runner, INCLUDING the one whose name is the bare prefix.

    T150's helper used `f.startswith("bifrost_runner_")`, which silently excludes
    `bifrost_runner.py`. This is the corrected enumeration and W4 exists to keep it honest.
    """
    return sorted(f for f in os.listdir(RUNNER_DIR)
                  if re.fullmatch(r"bifrost_runner(_[a-z0-9]+)?\.py", f))


def test_w1_generic_runner_is_line_buffered_and_utf8():
    m = re.search(r"sys\.stdout\.reconfigure\s*\(([^)]*)\)", _src(GENERIC))
    assert m, (f"{GENERIC} never reconfigures stdout -- an orchestrator watching it sees nothing "
               f"until it exits (the T150 defect, in the one runner T150's glob could not see)")
    args = m.group(1)
    assert "line_buffering" in args and "True" in args, f"{GENERIC}: stdout not line-buffered: {args}"
    assert "utf-8" in args and "replace" in args, f"{GENERIC}: stream encoding left to platform: {args}"


def test_w2_generic_runner_reconfigures_stderr():
    assert re.search(r"sys\.stderr\.reconfigure", _src(GENERIC)), \
        f"{GENERIC}: stderr unconfigured -- bus _loud notices go there"


def test_w3_generic_runner_guards_the_reconfigure():
    s = _src(GENERIC)
    m = re.search(r"sys\.stdout\.reconfigure", s)
    assert m, f"{GENERIC}: no stdout reconfigure to check"
    window = s[max(0, m.start() - 400):m.start() + 400]
    assert "try:" in window and "except" in window, \
        f"{GENERIC}: unguarded reconfigure -- an unsupported stream would kill the runner at import"


def test_w4_the_enumeration_covers_every_runner_including_the_bare_prefix():
    """The pin that outlives this fix. T150 shipped green while missing a member of its own family;
    this asserts over the corrected glob so the NEXT runner cannot inherit the hole silently."""
    runners = _all_runners()
    assert GENERIC in runners, f"enumeration still cannot see {GENERIC}: {runners}"
    assert len(runners) >= 5, f"expected the whole runner family, got {runners}"
    missing = [f for f in runners if not re.search(r"line_buffering\s*=\s*True", _src(f))]
    assert not missing, f"runner(s) an orchestrator cannot watch: {missing}"
