"""RED pins: the SECOND door onto WISHLIST.md never took the lock the first one got.

WHAT HAPPENED, AND IT IS MY OWN LESSON LANDING ON ME. Earlier today the filing door
(`cmd_wish`) was measured losing 6 of 40 concurrent wishes and was fixed with
`core/foundation/filelock.py`'s `exclusive()` (commit bbdc3584). Straight after, I filed the
lesson `when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`, whose advice is: at the
moment a shared primitive lands, grep the tree for the UNFIXED SHAPE, because sites diagnosed
before the primitive existed never get revisited.

The sweep's first hit was the door I had just fixed -- from the other side. `cmd_wish_curate`
does its own read-modify-write on the SAME file:

    doc = path.read_text(...)                         # READ
    new_doc, msg = _wish_curate_apply(doc, ...)       # MODIFY
    path.write_text(new_doc, ...)                     # WRITE

A lock excludes only the writers that TAKE it. Locking one of two doors onto a file buys
mutual exclusion between filings and nothing at all between a filing and a curation.

TWO DISTINCT FAILURES, MEASURED 2026-10-02 (four filings against four curations per round):

  * LOST WRITES. A process prints "filed W##" or "folded W##", exits 0, and its row is gone --
    overwritten wholesale by the other door's `write_text`. The same shape as this morning.

  * TORN READS. Operations refuse with "WISHLIST.md structure drifted ('## Folded' anchor
    missing) -- file by hand", or "no wish W01 in the ledger", on a state the ledger was never
    in at rest. `write_text` truncates before it writes, so an unlocked reader can observe the
    file mid-write. This failure is the kinder of the two -- it is loud -- but it sends a seat
    to hand-edit a file that was never damaged.

THE POWER OF THESE PINS, MEASURED RATHER THAN ASSUMED. A pin for a probabilistic defect is
only a pin if its miss rate is negligible, and the first draft of this file passed on a clean
run because the race simply did not fire. Over 12 rounds at four-plus-four:

    lost writes   fired in  7/12 rounds (p=0.58)
    torn reads    fired in  3/12 rounds (p=0.25)
    any anomaly   fired in  9/12 rounds (p=0.75)   -> 5 rounds miss 0.1%

Raising concurrency to six-plus-six made detection WORSE (p=0.33 for loss), because the extra
interpreter startups serialize on this box and shrink the overlap window. Four is deliberate.
ROUNDS is five: enough that a regression that removes the lock is caught ~99.9% of the time,
few enough to stay a suite test. All rounds run ONCE and every pin asserts over the same
evidence, so the cost is 40 subprocesses for the file rather than per test.

WHAT THESE PINS DO NOT ASK FOR. Curation must keep REFUSING a genuinely absent id -- its own
message says refusing beats silently doing nothing, and that is right.
`test_curate_still_refuses_a_wish_that_really_is_absent` exists so the torn-read pin cannot be
satisfied by making the door fail-soft, which would trade a loud wrong answer for a quiet one.

NOT A RED PIN: id uniqueness under mixed contention fired in 0 of 12 rounds. The filing lock
already covers it, because curation never allocates an id. It is kept below as a RATCHET and
must not be cited as evidence of this defect.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WORKERS = 4      # measured sweet spot; see the power note above
ROUNDS = 5       # 5 x p(0.75) -> ~0.1% miss
SEEDED = 8

SEED = ("# Wishes\n\n"
        + "\n".join("- [ ] W%02d (01-01, seed) - seeded wish %d." % (i, i)
                    for i in range(1, SEEDED + 1))
        + "\n\n## Folded (exemplars)\n")

TORN = re.compile(r"structure drifted|no wish W\d")


def _run(ledger, argv):
    """The real doors in real processes -- the only honest test of a CROSS-PROCESS lock.
    Threads in one interpreter would pass under a lock that does nothing for the real mode."""
    env = {**os.environ, "AKASHIC_WISHLIST_FILE": str(ledger), "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, "agent_cli.py"] + argv,
                          capture_output=True, text=True, cwd=str(REPO), env=env)


def _curate(ledger, i, wid):
    return _run(ledger, ["wish-curate", "cur%d" % i, "--id", wid,
                         "--as", "fold", "--task", "T999"])


def _open_ids(t):
    return re.findall(r"- \[ \] W(\d+)", t)


def _folded_ids(t):
    return re.findall(r"- \[x\] W(\d+)", t)


@pytest.fixture(scope="module")
def contention(tmp_path_factory):
    """Run the contention ROUNDS times ONCE and let every pin read the same evidence."""
    led = tmp_path_factory.mktemp("wishrace") / "WISHLIST.md"
    rounds = []
    for _ in range(ROUNDS):
        led.write_text(SEED, encoding="utf-8")
        jobs = [("file", i) for i in range(WORKERS)] + [("curate", i) for i in range(WORKERS)]

        def go(j):
            kind, i = j
            if kind == "file":
                return kind, _run(led, ["wish", "seat%d" % i, "new wish %d" % i])
            return kind, _curate(led, i, "W%02d" % (i + 1))

        with ThreadPoolExecutor(max_workers=2 * WORKERS) as pool:
            res = list(pool.map(go, jobs))

        text = led.read_text(encoding="utf-8")
        ok_f = [r for k, r in res if k == "file" and r.returncode == 0]
        ok_c = [r for k, r in res if k == "curate" and r.returncode == 0]
        rounds.append({
            "filed_ok": len(ok_f),
            "filed_present": len([w for w in _open_ids(text) if int(w) > SEEDED]),
            "curated_ok": len(ok_c),
            "folded_present": len(_folded_ids(text)),
            "torn": [(k, (r.stdout + r.stderr).strip()[:140]) for k, r in res
                     if r.returncode != 0 and TORN.search(r.stdout + r.stderr)],
            "ids": _open_ids(text) + _folded_ids(text),
            "text": text,
        })
    return rounds


# ------------------------------------------------------------------ ratchets


def test_a_lone_curation_still_works(tmp_path):
    """RATCHET. The door must keep working at all; the rest of this file is contention."""
    led = tmp_path / "WISHLIST.md"
    led.write_text(SEED, encoding="utf-8")
    r = _curate(led, 0, "W03")
    assert r.returncode == 0, r.stdout + r.stderr
    text = led.read_text(encoding="utf-8")
    assert "03" in _folded_ids(text), _folded_ids(text)
    assert "03" not in _open_ids(text), "the folded wish is still listed open"


def test_curate_still_refuses_a_wish_that_really_is_absent(tmp_path):
    """RATCHET, and the guard against a VACUOUS pass of the torn-read pin. That pin says no
    operation may fail on a torn read; the cheap way to satisfy it is to stop refusing at all.
    That would be worse than the race -- the door's own message says so."""
    led = tmp_path / "WISHLIST.md"
    led.write_text(SEED, encoding="utf-8")
    r = _curate(led, 0, "W77")
    assert r.returncode != 0, "a curation of an absent wish must still refuse: " + r.stdout
    assert "W77" in (r.stdout + r.stderr), r.stdout + r.stderr


def test_ids_stay_unique_under_mixed_contention(contention):
    """RATCHET, NOT evidence. Measured 0/12 rounds -- the filing lock already covers this
    because curation never allocates an id. Here so a future change that moves allocation
    into curation cannot reintroduce the collision this ledger carried for two months."""
    for i, r in enumerate(contention):
        dupes = sorted({x for x in r["ids"] if r["ids"].count(x) > 1})
        assert not dupes, "round %d issued %s more than once (all: %s)" % (i, dupes, r["ids"])


# ------------------------------------------------------------------ the pins


def test_a_curation_never_swallows_a_concurrent_filing(contention):
    """THE PIN. A filing reports success and its row is overwritten by a curation's write."""
    bad = [(i, r["filed_ok"], r["filed_present"]) for i, r in enumerate(contention)
           if r["filed_present"] < r["filed_ok"]]
    assert not bad, (
        "filings reported success and vanished, in %d of %d rounds "
        "(round, reported, survived): %s" % (len(bad), ROUNDS, bad))


def test_a_filing_never_swallows_a_concurrent_curation(contention):
    """The mirror. A filing's write can equally drop a fold that already reported done."""
    bad = [(i, r["curated_ok"], r["folded_present"]) for i, r in enumerate(contention)
           if r["folded_present"] < r["curated_ok"]]
    assert not bad, (
        "curations reported success and vanished, in %d of %d rounds "
        "(round, reported, survived): %s" % (len(bad), ROUNDS, bad))


def test_no_door_ever_observes_a_torn_ledger(contention):
    """The second failure, which a loss count alone would miss. `write_text` truncates before
    it writes, so an unlocked reader sees the file without its anchor or its rows and refuses
    on damage that does not exist at rest."""
    bad = [(i, r["torn"]) for i, r in enumerate(contention) if r["torn"]]
    assert not bad, (
        "operations refused on a state the ledger was never in, in %d of %d rounds: %s"
        % (len(bad), ROUNDS, bad[:2]))


def test_the_ledger_is_structurally_whole_after_contention(contention):
    """Whatever else races, the file must not end up unparseable -- the door refuses outright
    on a missing anchor, so a torn write that persisted would wedge filing for everyone."""
    for i, r in enumerate(contention):
        assert r["text"].startswith("# Wishes"), "round %d lost the heading" % i
        assert "## Folded" in r["text"], "round %d lost the '## Folded' anchor" % i


def test_the_curate_door_imports_the_house_lock():
    """Names the intended fix, so a refactor that drops it fails with WHICH primitive is
    missing rather than only that a race came back -- and so the next sweep of this class
    finds this door already counted. Deterministic, unlike every pin above it."""
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8")
    start = src.index("def cmd_wish_curate(")
    body = src[start:src.index("\ndef ", start + 1)]
    assert "filelock" in body or "exclusive" in body, (
        "cmd_wish_curate rewrites docs/WISHLIST.md without reaching for "
        "core.foundation.filelock.exclusive -- the lock cmd_wish takes on the same file")
