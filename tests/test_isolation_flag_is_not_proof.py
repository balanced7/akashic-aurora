"""Pin: isolation must verify the REDIRECT, never trust the FLAG.

THE INCIDENT, 2026-07-25, twice in one day and the second time I caused it.

`isolate_canonical` guarded its whole body on:

    if not os.environ.get("_AISETUP_TEST_ISOLATED"):
        ...redirect AI_SETUP + REDIS_DB, flush db 15...
        os.environ["_AISETUP_TEST_ISOLATED"] = "1"

So a process that merely INHERITS that flag skips isolation entirely and runs against
canonical -- while conftest, T070's universal isolation, and every reader of the flag believe
it is isolated. Proven directly: set the flag with no redirect, import the module, and
AI_SETUP/REDIS_DB come back UNSET. Isolation silently did nothing.

WHAT IT COST:
  14:25 -- fixture lessons (`messy_exp`, agent `messy_agent`) written into canonical Redis
           db 0 by an unidentified runner. I could not find the vector at the time.
  20:11 -- deepseek ran the full suite at my explicit instruction ("it is safe now, the
           repair ritual is retired") and the live learning index collapsed to FIVE entries:
           437 lessons, 98% of the corpus, invisible to every keyword search. Fixture agents
           (`cursor_pull_6a9194`, `census`) and fixture failures landed in canonical while it
           ran. Same starved-index incident as the night before, reproduced in daylight.

THE GENUS, and it is the day's theme in the isolation primitive itself: a marker was treated
as PROOF of a state it never verified. The same shape as a green suite that only skipped, a
token meter that printed a confident zero, a census OK-line over nothing examined, and a
directory pointer that resolved to the wrong contents.

THE RULE: verify the CONDITION (are the paths actually redirected?), never the CLAIM (does a
flag say so?). A flag may be an optimisation to avoid re-flushing; it may never be the
authority on whether isolation happened.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_PROBE = r"""
import os, sys
os.environ["_AISETUP_TEST_ISOLATED"] = "1"      # the claim, with NO redirect behind it
sys.path.insert(0, r"{tests}")
import isolate_canonical            # noqa: F401
ai = os.environ.get("AI_SETUP", "")
db = os.environ.get("REDIS_DB", "")
print("AI_SETUP=" + ai)
print("REDIS_DB=" + db)
"""


def _run_probe() -> dict:
    """Run in a CHILD so this test's own already-isolated env cannot mask the bug."""
    code = _PROBE.format(tests=str(ROOT / "tests"))
    env = {k: v for k, v in os.environ.items()
           if k not in ("AI_SETUP", "REDIS_DB", "_AISETUP_TEST_ISOLATED", "AKASHIC_SPILL_DIR")}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       cwd=str(ROOT), env=env, timeout=120)
    out = {}
    for line in (r.stdout or "").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def test_the_flag_alone_must_not_disable_isolation():
    """The exact 2026-07-25 vector: inherit the flag, get canonical."""
    got = _run_probe()
    assert got, "probe produced no output"
    ai = got.get("AI_SETUP", "")
    assert ai, (
        "AI_SETUP is UNSET after isolate_canonical ran with the flag pre-set -- isolation was "
        "skipped on the strength of a claim, and this process would write to canonical"
    )
    assert Path(ai).resolve() != ROOT.resolve(), f"AI_SETUP points at the live repo ({ai})"


def test_redis_db_is_redirected_even_when_the_flag_is_preset():
    got = _run_probe()
    db = got.get("REDIS_DB", "")
    assert db not in ("", "0"), (
        f"REDIS_DB={db!r} with the flag pre-set -- the suite would read and write canonical db 0"
    )
