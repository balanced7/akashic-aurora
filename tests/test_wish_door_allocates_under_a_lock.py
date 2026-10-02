"""RED pins: two seats filing a wish at once must not be handed the same number.

THE DEFECT, and the house has already diagnosed it twice in its own source. `cmd_wish` in
agent_cli.py does a read-modify-write on docs/WISHLIST.md with NO LOCK of any kind:

    text = path.read_text(...)                    # READ
    nums = [... regex scan of the whole file ...]
    n    = (max(nums) if nums else 0) + 1         # DECIDE
    text = text.replace(marker, block + marker)   # MODIFY
    path.write_text(text, ...)                    # WRITE

Its own comment names the mechanism exactly: "max+1 never collides against a correct read, so
duplicates arrive via STALE reads -- two seats filing batches against different versions of this
file. Measured 2026-08-01: 128 blocks, highest id W114, 14 ids doubled (W00, W57..W69)."

IT IS STILL HAPPENING, AND THE LEDGER SHOWS IT. W57 through W69 is a block of thirteen
consecutive numbers issued twice, on 07-22/23 and again on 07-24/25/26. W211 was issued to claude
on 09-23 and to deepseek on 09-25 -- note the second issue carries the EARLIER date, which is what
a stale read looks like from the outside. The door now warns loudly on every filing, which is
right, but a warning is not a fix and the collisions have continued for two months.

THE FIX ALREADY EXISTS IN THIS REPO AND THIS DOOR NEVER GOT IT. `core/foundation/filelock.py`
provides `exclusive(target)`, a cross-process OS lock, born 2026-08-26 from a THIRD instance of
this same class: a bridge inbox that admitted a message and silently lost it to exactly this race.
Its docstring is explicit that threads alone do not cover it, because the file is also written by
CLI processes. `core/foundation/ledger.py` adopted it on 2026-09-24 after the DuckDB dive measured
the unlocked version losing 410 of 18,170 recall outcomes. remote_relay, task_ledger and college
use it too.

So the sequence is: the wish door's collision was measured 2026-08-01, the primitive that fixes it
arrived 2026-08-26, four other modules adopted it, and the door that records our friction was never
told. That is the house's own thesis happening to its own capture loop.

WHAT THESE PINS DO NOT ASK FOR. The door must keep FILING on a collision rather than refusing --
that is deliberate, and its comment says why: "a capture mechanism that refuses is worse than one
with an ambiguous id". The loud warning stays. These pins only require that a NEW collision cannot
be created by two concurrent filings.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SEED = """# Wishes

- [ ] W01 (01-01, seed) - the first wish.
- [ ] W02 (01-01, seed) - the second wish.

## Folded (exemplars)
"""


def _ledger(tmp_path):
    p = tmp_path / "WISHLIST.md"
    p.write_text(SEED, encoding="utf-8")
    return p


def _file_wish(ledger, body, agent="t-seat"):
    """Run the real door in its own process, which is the only honest way to test a
    CROSS-PROCESS lock: threads in one interpreter would pass under a threading.Lock that
    does nothing for the actual failure mode."""
    env = {**os.environ, "AKASHIC_WISHLIST_FILE": str(ledger), "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, "agent_cli.py", "wish", agent, body],
                          capture_output=True, text=True, cwd=str(REPO), env=env)


def _ids(ledger):
    return re.findall(r"- \[[ x~]\] W(\d+)", ledger.read_text(encoding="utf-8"))


def test_a_single_filing_still_works(tmp_path):
    """RATCHET. The door must keep working at all; everything else here is about contention."""
    led = _ledger(tmp_path)
    r = _file_wish(led, "a lone wish")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _ids(led) == ["01", "02", "03"], _ids(led)


def test_concurrent_filings_never_share_a_number(tmp_path):
    """THE PIN. Eight seats file at once against one ledger. Unlocked, several read the same
    `max` and are handed the same id -- which is how W57..W69 came to exist twice."""
    led = _ledger(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        runs = list(pool.map(lambda i: _file_wish(led, f"concurrent wish {i}", f"seat{i}"), range(8)))
    assert all(r.returncode == 0 for r in runs), [r.stdout + r.stderr for r in runs if r.returncode]
    ids = _ids(led)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"the same id was issued more than once: {dupes} (all ids: {ids})"


def test_no_filing_is_lost_to_the_race(tmp_path):
    """The other half, and the one a dedup check would miss. A read-modify-write that rewrites the
    WHOLE file can also drop a peer's row entirely: the loser's write simply overwrites it. Eight
    filings against a two-wish ledger must leave ten."""
    led = _ledger(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: _file_wish(led, f"kept wish {i}", f"seat{i}"), range(8)))
    ids = _ids(led)
    assert len(ids) == 10, f"expected 2 seeded + 8 filed = 10 rows, found {len(ids)}: {ids}"


def test_the_door_still_files_when_the_ledger_already_collides(tmp_path):
    """RATCHET, and deliberately NOT a request to refuse. The door's own comment says a capture
    mechanism that refuses is worse than one with an ambiguous id, so a pre-existing collision must
    still warn loudly and still file."""
    led = tmp_path / "WISHLIST.md"
    led.write_text(SEED.replace("- [ ] W02 (01-01, seed) - the second wish.",
                                "- [ ] W02 (01-01, seed) - the second wish.\n"
                                "- [ ] W02 (01-02, seed) - a collided twin."), encoding="utf-8")
    r = _file_wish(led, "filed despite the collision")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "COLLID" in (r.stdout + r.stderr).upper(), "the collision warning went quiet"
    assert "W03" in r.stdout, r.stdout


def test_the_door_imports_the_house_lock(tmp_path):
    """Names the intended fix, so a future refactor that drops the lock is caught by a pin that
    says WHICH primitive is missing rather than only that a race came back."""
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8")
    start = src.index("def cmd_wish(")
    body = src[start:start + 4000]
    assert "filelock" in body or "exclusive" in body, \
        "cmd_wish does not reach for core.foundation.filelock.exclusive, the cross-process lock " \
        "ledger.py, remote_relay.py, task_ledger.py and college.py already use"
