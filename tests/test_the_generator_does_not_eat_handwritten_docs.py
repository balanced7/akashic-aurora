"""RED pin: the library generator silently overwrites hand-written READMEs.

PRE-REGISTRATION (M3). RED at this commit; the guard follows separately.

HOW IT WAS FOUND, 2026-10-07, and the manner matters. The overnight census established that
`docs/SHELVES.md` and `docs/ARCS.md` were 75 days stale and missing 361 of 1,016 atoms, and that
zero zone READMEs existed on disk though the schema expects them. The generator exists and works.
Running it was the obviously-correct action, so I ran it.

It wrote 9 zone READMEs and **destroyed 86 lines of hand-written doctrine** in `research/README.md`:

    git diff --stat research/README.md
    1 file changed, 15 insertions(+), 86 deletions(-)

Gone in that diff: the whole "Research day" economics ("frontier tokens are for **deciding**, local
tokens are for **gathering**"), the three-line loop that explains how a research day actually runs,
the layout table defining `queue/` / `drafts/` / `reviewed/`, and the FULL-FIDELITY rule for
`reviewed/frontier-<topic>-<date>.md` -- a rule this house cites as doctrine and which has its own
lesson in the corpus. Restored with `git checkout --`.

THE DEFECT, one line, gen_library.py:534:

    readme_path.write_text(zone_out, encoding="utf-8")

Unconditional. No read of what is already there, no check for the generator's own stamp, no
refusal. Every zone in `_build_zone_census` gets its README replaced whether a human wrote it or
not. Six of the nine zones had no README, so nothing was lost there; `research/` had one, and it
was the one that mattered.

WHY A STAMP IS THE RIGHT GUARD. The generator already writes its own provenance into every file it
produces:

    **Generated:** <ts> · **Source:** `scripts/generators/gen_library.py` · **Never hand-edit.**

So "did I write this?" is already answerable from the file's own contents. A file carrying that
line is the generator's to replace. A file without it belongs to whoever wrote it, and overwriting
it is data loss, not regeneration. SKIP_README_IN already exists at gen_library.py:36 and names
four zones -- but it governs INLINE CATALOGUING, not the overwrite, so `research/` is in that set
and was clobbered anyway.

THE WIDER POINT, which is why this is pinned rather than just patched: a generator that cannot tell
its own output from a human's is one `--readmes` away from erasing any document that happens to sit
at a path it claims. The blast radius is every zone it knows about, and the loss is silent --
nothing failed, nothing warned, and the diff is only visible to someone who looks before committing.

Run::

    py -m pytest tests/test_the_generator_does_not_eat_handwritten_docs.py -q
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts" / "generators" / "gen_library.py"

#: The provenance line the generator stamps into everything it writes. Its presence is the only
#: honest answer to "is this file mine to replace?".
STAMP = "Source:** `scripts/generators/gen_library.py`"


def _src() -> str:
    return GEN.read_text(encoding="utf-8", errors="replace")


def test_the_writer_checks_before_it_overwrites():
    """THE PIN. The write must be guarded by a read of what is already there."""
    src = _src()
    i = src.index("# 2) Zone READMEs")
    block = src[i:i + 2000]
    # Must read the README FILE. An earlier version of this pin accepted any "exists()" and so
    # passed on `zone_dir.exists()` -- the DIRECTORY check that was already there and guards
    # nothing about content. A token that matches the code you are accusing is not a test.
    guarded = ("readme_path.read_text" in block or "readme_path.is_file" in block
               or "readme_path.exists" in block or "_may_write_readme" in block)
    assert guarded, (
        "gen_library writes every zone README unconditionally (gen_library.py:534 "
        "readme_path.write_text(...)) with no read of the existing file. Running it on 2026-10-07 "
        "destroyed 86 lines of hand-written doctrine in research/README.md -- the Research day "
        "economics, the loop, the layout table and the full-fidelity preservation rule.")


def test_a_file_without_the_generator_stamp_is_not_the_generators_to_replace():
    """The rule, stated as a rule. The generator stamps its own provenance into every file it
    writes, so 'did I write this?' is answerable from the file itself. No stamp means a human
    wrote it, and replacing it is data loss rather than regeneration."""
    src = _src()
    assert "Never hand-edit" in src, "the generator no longer stamps its own output"
    i = src.index("# 2) Zone READMEs")
    block = src[i:i + 2000]
    assert ("Never hand-edit" in block or "STAMP" in block or "stamp" in block), (
        "the write loop does not consult the stamp it already emits, so it cannot tell its own "
        "output from a document someone wrote by hand")


def test_it_says_out_loud_when_it_refuses():
    """A silent skip trades one invisible failure for another. If the generator declines to write a
    zone, the operator has to be told which zone and why -- otherwise a stale catalog looks exactly
    like a protected one."""
    src = _src()
    i = src.index("# 2) Zone READMEs")
    block = src[i:i + 2000]
    assert ("skip" in block.lower() or "refus" in block.lower() or "kept" in block.lower()), (
        "the write loop has no path that reports a refusal, so a protected zone and a regenerated "
        "zone are indistinguishable in the output")


# ------------------------------------------------------------------ ratchet
def test_the_generator_still_writes_its_own_catalogs():
    """RATCHET. The guard must not stop the generator doing its job: SHELVES and ARCS carry the
    stamp and are the generator's to replace, every time."""
    r = subprocess.run([sys.executable, "-X", "utf8", str(GEN), "--stdout"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=300)
    assert r.returncode == 0, r.stderr[:300]
    assert "SHELVES" in r.stdout, "the generator no longer renders the SHELVES census"


def test_research_readme_still_holds_the_doctrine_that_was_destroyed():
    """REGRESSION GUARD on the specific loss. These phrases were in the 86 deleted lines. If they
    vanish again, something overwrote this file."""
    p = ROOT / "research" / "README.md"
    if not p.is_file():
        pytest.skip("research/README.md absent on this checkout")
    text = p.read_text(encoding="utf-8", errors="replace")
    for phrase in ("frontier tokens are for", "Research day"):
        assert phrase in text, (
            "research/README.md no longer contains %r -- the hand-written doctrine was "
            "overwritten again" % phrase)
