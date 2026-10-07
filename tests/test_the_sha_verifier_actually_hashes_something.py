"""RED pins: the library's integrity check compares one recorded number to another recorded number.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

DANIEL, 2026-10-07, going to sleep: "making our best knowledge reach us when we need it or at least
be easy to find ... so that we know what we have and where its supposed to live."

A library's `akashic_sha` exists for exactly one purpose: to tell you whether a body still says what
it said when it was filed. `scripts/generators/gen_library.py --verify` is the check that should
answer that, and it cannot, because of one line:

    # gen_library.py:424
    elif m.group(1) != a.get("body_sha"):

``m.group(1)`` is the sha parsed out of the PROJECTION'S FRONTMATTER -- a value that was written
down. ``a.get("body_sha")`` is the sha recorded ON THE ATOM -- another value that was written down.
**Neither is recomputed from a body.** Its own docstring states the design without flinching:

    "BELIEF = the projection frontmatter's akashic_sha; STATE = the atom's body_sha."

Both of those are belief. If a body is edited outside the atom door -- by a repo-wide text rewrite,
a merge, a hand edit -- both recorded shas stay exactly as they were, the comparison passes, and the
body no longer hashes to either of them. The one failure a content hash exists to catch is the one
failure this check cannot see.

MEASURED 2026-10-07, all [CERTAIN] from my own commands:

  * ``--verify`` exits 1 and prints "DRIFT: 1010 projection(s) cross-read, 10 local-redacted
    skipped, 8 drift row(s), 14 orphan(s)". Of those rows: **0 are sha drift.** 8 are MISSING
    (projection file absent) and 14 are ORPHAN (file with no atom). The summary counts MISSING as
    "drift row(s)", so the one number a reader scans is also mislabelled.
  * The atom record carries the body: ``fam.find()`` returns ``body`` alongside ``body_sha`` for
    all 1,020 atoms. So recomputing is available and free -- nothing was blocking it.
  * Recomputing ``sha256(body)[:12]`` over the store gives **0 mismatches of 1,020**. The store is
    healthy. That is good news and it is ALSO the point: a check that cannot distinguish a healthy
    corpus from an unverified one is not reporting health, it is reporting silence.
  * An independent census found **40 of 1,020 bodies in the git-tracked durable record**
    (``store/docs/*.jsonl``) that no longer hash to their recorded sha -- same byte length,
    differing mid-text, one pair differing only by a git sha (``84f7cc9`` vs ``035e70e``). That is
    the signature of a repo-wide text rewrite reaching inside the durable record. ``--verify`` says
    CLEAN about every one of them. (Reported as the census's count, not re-derived here -- the
    pins below do not depend on it.)

WHY THIS IS THE THIRD ONE TODAY. `find --sort` re-sorted results after asking es.exe for an order,
so every sort key was inert. A pin I wrote compared only the YEAR of each row when every row was
from 2026, and passed over a plainly unsorted list. Now a sha verifier that hashes nothing. All
three report green by comparing a thing to itself, and all three are invisible until someone asks
what the comparison actually touched.

Run::

    py -m pytest tests/test_the_sha_verifier_actually_hashes_something.py -q
"""
from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GEN = ROOT / "scripts" / "generators" / "gen_library.py"


def _src() -> str:
    return GEN.read_text(encoding="utf-8", errors="replace")


def _atoms():
    from core.foundation.store import create_store
    from core.library.atoms import AtomFamily
    return AtomFamily(create_store(), repo_root=str(ROOT)).find()


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


# ------------------------------------------------------------------ the defect
def test_verify_recomputes_a_sha_from_a_body():
    """THE PIN. A content hash that is never recomputed is a label, not a checksum.

    The verifier must hash at least one actual body and compare the result to a recorded value.
    Comparing two recorded values can only detect a transcription error between two places that
    were both written by the same code path.
    """
    src = _src()
    verify = src[src.index("def _verify_projections"):]
    assert ("_sha12(" in verify or "sha256(" in verify or "hashlib" in verify), (
        "_verify_projections() never computes a hash. It compares the projection's recorded "
        "akashic_sha to the atom's recorded body_sha -- belief against belief -- so a body edited "
        "outside the atom door passes, which is the only failure a content hash exists to catch.")


def test_the_store_integrity_check_exists_and_has_a_denominator():
    """Recomputing over the store is free: fam.find() already returns `body` beside `body_sha` for
    every atom. The check must exist AND must report how many bodies it hashed, or a clean result
    is indistinguishable from a check that ran over nothing."""
    src = _src()
    verify = src[src.index("def _verify_projections"):]
    assert "body" in verify and "body_sha" in verify, "the verifier never reads the atom body"
    for token in ("rehash", "recomput", "hashed", "verified_bodies", "body_checked"):
        if token in verify.lower():
            break
    else:
        pytest.fail("the verifier reports no count of bodies actually hashed -- without that "
                    "denominator, CLEAN means 'nothing was checked' just as easily as 'nothing "
                    "is wrong'")


def test_the_summary_does_not_call_MISSING_rows_drift():
    """Measured: the run prints '8 drift row(s)' when 0 rows are sha drift and 8 are MISSING
    projection files. Those have different causes and different fixes -- a missing file is a
    regeneration, a drifted body is a corruption -- and collapsing them into one word sends the
    reader at the wrong one."""
    src = _src()
    verify = src[src.index("def _verify_projections"):]
    assert "drift row(s)" not in verify or "missing" in verify.lower(), (
        "the summary line labels every row 'drift' regardless of kind")


# ------------------------------------------------------------------ ratchets: keep what works
def test_the_store_is_and_stays_internally_consistent():
    """RATCHET, and the number worth watching. Recomputing sha256(body)[:12] across the store gave
    0 mismatches of 1,020 on 2026-10-07. The store is the healthy plane; this pin is what turns
    that from a one-off observation into a standing guarantee."""
    atoms = _atoms()
    if not atoms:
        # tests/conftest.py isolates to Redis db 15 and FLUSHES it, so the real 1,020 atoms are
        # not visible here. Skipping on the measured precondition rather than on a guess -- the
        # same correction `test_defer_refuses_an_unknown_seat` needed this morning, where a proxy
        # precondition never fired and left the pin permanently red in the baseline.
        pytest.skip("no atoms visible: conftest isolates to db 15 and flushes it. Run with "
                    "AKASHIC_TEST_USE_CANONICAL=1 to exercise this against the real store.")
    bad = [a["id"] for a in atoms
           if a.get("body") is not None and _sha12(a["body"]) != a.get("body_sha")]
    assert not bad, (
        "%d of %d atom bodies in the STORE no longer hash to their recorded body_sha: %r"
        % (len(bad), len(atoms), bad[:5]))


def test_verify_still_reports_missing_and_orphan_rows():
    """RATCHET. The existing MISSING/ORPHAN detection is real and must survive the fix -- 8 and 14
    rows respectively when this was written."""
    src = _src()
    verify = src[src.index("def _verify_projections"):]
    assert "MISSING" in verify and "ORPHAN" in verify


def test_verify_still_exits_nonzero_on_findings():
    """RATCHET. It is ship-gateable today (exit 1 with rows present) and must stay so."""
    r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), "--verify"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=300)
    out = r.stdout + r.stderr
    has_rows = ("MISSING" in out) or ("ORPHAN" in out) or ("DRIFT " in out)
    if has_rows:
        assert r.returncode != 0, "verify printed finding rows and still exited 0 -- not gateable"
