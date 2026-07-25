"""FileStore cross-process coherence: the lost-update hole, pinned as a strict xfail.

WHY THIS TEST FAILS ON PURPOSE
------------------------------
FileStore._flush (core/foundation/store.py) writes the WHOLE in-memory dict and os.replace's
it onto the shared path. The class is thread-safe via an RLock; it is NOT process-safe, and
there is no CAS and no read-modify-write. Two processes each hold a full copy of state, so the
second flush replaces the first writer's data wholesale. Last writer wins. Nothing raises.

Measured 2026-07-25 with an isolated 3-process probe: 450 writes, 155 survived, 295 LOST --
65.6% silent data loss, with one worker's entire output erased while it believed every single
write had succeeded. This is the store underneath the knowledge substrate.

WHY STRICT XFAIL RATHER THAN A SKIP OR A PLAIN FAILURE
------------------------------------------------------
- A `skip` would not run the body, so "cannot verify" and "verified broken" would collapse into
  one silent outcome. That is the exact type error this suite is being cured of.
- A plain failure adds one more red line to a suite already too red to read.
- `xfail(strict=True)` runs the body, expects today's loss, stays quiet -- and the day someone
  lands RB-8 CAS (T034) and the write survives, the XPASS FAILS THE BUILD and says so. The pin
  turns an open wound into a tracked one, and it cannot rot into a green.

WHY THIS IS DETERMINISTIC AND NOT A RACE
----------------------------------------
A racy pin under strict=True would occasionally XPASS and cry wolf. So this does not race. It
sequences the interleaving by hand:

    parent  : open store, write P1              -> file {P1}
    child   : open store (loads {P1}), write C  -> file {P1, C}
    parent  : write P2 from its STALE dict      -> file {P1, P2}   <- C is gone

The parent never reloads, because nothing tells it to. That is the defect, stated as a
schedule rather than discovered by luck.

Remove the xfail marker -- do not delete the test -- when the store learns to merge or refuse.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.foundation.store import FileStore

REPO_ROOT = Path(__file__).resolve().parents[1]

# Runs in its own interpreter so the write genuinely crosses a process boundary.
_CHILD = """
import sys
sys.path.insert(0, {repo!r})
from core.foundation.store import FileStore
store = FileStore({path!r})
store.set("child_write", "survives?")
"""


def _read_kv(state: Path) -> dict:
    """The kv bucket as it actually sits on disk, read without going through FileStore."""
    if not state.exists():
        return {}
    return json.loads(state.read_text(encoding="utf-8")).get("kv", {})


@pytest.mark.xfail(
    strict=True,
    reason="FileStore has no cross-process coherence: _flush replaces the whole file from a "
           "stale in-memory dict, so the child's write is lost. Pinned 2026-07-25; unpin when "
           "RB-8 CAS / T034 lands. XPASS here means the store was fixed -- delete the marker.",
)
def test_a_concurrent_writers_write_is_not_silently_lost(tmp_path):
    state = tmp_path / "store_state.json"

    parent = FileStore(str(state))
    parent.set("parent_first", "1")
    assert "parent_first" in _read_kv(state), "setup: parent's first write should be on disk"

    child_src = _CHILD.format(repo=str(REPO_ROOT), path=str(state))
    done = subprocess.run(
        [sys.executable, "-c", child_src],
        capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0, f"setup: child writer failed: {done.stderr[:500]}"
    assert "child_write" in _read_kv(state), "setup: the child's write should have landed"

    # The parent has not reloaded and does not know the file moved under it.
    parent.set("parent_second", "1")

    on_disk = _read_kv(state)
    assert "parent_second" in on_disk, "sanity: the parent's own second write should be on disk"

    # THE PIN. Today this fails: the parent's whole-dict flush erased the child's key, and
    # neither writer was told. When it passes, the coherence hole is closed.
    assert "child_write" in on_disk, (
        "A second process's committed write was silently erased by this process's flush. "
        "FileStore._flush writes its entire in-memory dict over the shared file with no CAS "
        "and no re-read, so the last writer wins and the loser is never informed."
    )


def test_b_the_loss_is_silent_which_is_what_makes_it_dangerous(tmp_path):
    """This one PASSES today, and that is the finding.

    Kept separate from the xfail pin on purpose: it asserts the *current* contract rather
    than the desired one, so it must not be swept up when the pin above is unpinned. It
    documents that the store reports success for a write it is about to lose -- the property
    that makes the hole invisible in production rather than merely wrong.
    """
    state = tmp_path / "store_state.json"

    parent = FileStore(str(state))
    parent.set("parent_first", "1")

    child_src = _CHILD.format(repo=str(REPO_ROOT), path=str(state))
    subprocess.run([sys.executable, "-c", child_src], capture_output=True, text=True, timeout=120)

    # set() returns truthy and raises nothing, even though this call is about to destroy
    # a committed write by another process.
    result = parent.set("parent_second", "1")

    assert result is not False, "set() reports success"
    assert "child_write" not in _read_kv(state), (
        "If this assertion fails, the coherence hole may have been fixed -- check the xfail "
        "pin above, which should then be XPASSing and failing the build."
    )
