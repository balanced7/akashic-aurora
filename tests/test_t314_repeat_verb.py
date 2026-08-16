"""T314 RED pins -- record_repeat needs a door.

THE DEFECT: core/learning/learning_store.py has carried record_repeat() and repeat_report()
since T253, with a docstring that states the point exactly --

    "A REPEAT is evidence ABOUT a lesson: the lesson existed, and the mistake happened anyway."
    "THE COUNT IS A FLOOR, NEVER A RATE. It counts only repeats someone NOTICED."

-- and `py agent_cli.py discover repeat` returns 0 verbs. A capability with no door is not used,
so the store held FOUR repeats across the project's entire life. One session's honest accounting
added three. The count did not read as a floor; it read as "we rarely repeat ourselves."

WHY IT MATTERS MORE THAN A CONVENIENCE: repeat_report() carries `elapsed_s`, the time between
learning a lesson and violating it. Measured today: 1.9h, 1.8h, and 5.4 DAYS. That number is the
only mechanical evidence of whether a lesson is WORKING, and therefore of when prose should be
replaced by a forcing function. It has never been surfaced anywhere.

Pin 3 is the one that keeps the data honest: a repeat against a lesson that does not exist is not
a cautious record, it is noise that inflates a floor nobody can audit.
"""
import os
import subprocess
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)


def _cli(*args):
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=_REPO, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def test_repeat_verb_exists_on_the_door():
    """The whole defect is a capability nothing can reach."""
    rc, out = _cli("repeat", "--help")
    assert rc == 0 and "usage" in out.lower(), \
        f"`agent_cli.py repeat` is not a verb (rc={rc}). record_repeat has no door."


def test_repeat_is_discoverable():
    """discover is how a seat finds a verb it does not already know exists -- which is the
    entire reason this one went unused for a month."""
    rc, out = _cli("discover", "repeat")
    assert "0 verb(s)" not in out, \
        "discover cannot see the repeat verb; an undiscoverable door is the defect restated"


def test_report_surfaces_elapsed_since_the_lesson():
    """elapsed_s is the number Daniel asked for: learned-then-violated, with the gap."""
    import json as _j
    rc, out = _cli("repeat", "--report", "--json")
    assert rc == 0, f"repeat --report failed (rc={rc}): {out[:300]}"
    try:
        rep = _j.loads(out[out.index("{"):out.rindex("}") + 1])
    except Exception as e:
        raise AssertionError(f"--report --json did not emit JSON ({e}): {out[:200]}")
    # Shape, not ambient data: this pin must not depend on the live store having rows, or it
    # passes or fails on whatever else ran first (lesson: a pin that reads ambient state).
    assert "entries" in rep, f"the report drops the per-repeat entries entirely: {list(rep)}"
    for e in rep["entries"]:
        assert "elapsed_s" in e, (
            "an entry carries no elapsed_s -- the gap between learning a lesson and violating "
            "it is the number this verb exists to surface")
    if rep["entries"]:
        rc2, txt = _cli("repeat", "--report")
        assert "elapsed" in txt.lower(), (
            "entries carry elapsed_s but the human-readable report hides it; a number only in "
            f"--json is a number nobody reads. Got: {txt[:300]}")


def test_report_names_no_rate():
    """repeat_report's own docstring pins this: no percentage, no key named a rate, because the
    count is a floor over what someone NOTICED and a rate would imply a denominator we do not
    have. The door must not reintroduce what the store refused."""
    rc, out = _cli("repeat", "--report")
    assert "%" not in out, f"the report printed a percentage over a floor: {out[:300]}"


def test_unknown_lesson_refuses():
    """A repeat is evidence ABOUT a lesson. Recording one against a lesson that does not exist
    inflates a count nobody can audit back to a source."""
    rc, out = _cli("repeat", "learn:experiment:this_lesson_does_not_exist_xyzzy",
                   "--what", "T314 pin: must refuse")
    assert rc != 0, (
        "recording a repeat against a non-existent lesson SUCCEEDED -- a dangling repeat is "
        f"noise in the only honest count we have. Got rc={rc}: {out[:300]}")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}\n        {str(e)[:220]}")
    print(f"\n{failures} failing pin(s) -- RED is expected before T314 is built.")
    sys.exit(1 if failures else 0)
