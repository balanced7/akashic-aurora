"""T109 -- migration completion pins: the retrieval plane follows the corpus.

RED against the pre-fix tree. The 12-probe canonical battery (tests/test_lookback.py,
pre-registered, NEVER TUNED) has been RED since f8510b6 removed 621 docs/*.md originals
whose names the probes expect. The content survives as atom projections under
docs/library/<type>/ -- but lookback._docs_items walks docs/ TOP-LEVEL ONLY, and the
original slug (the retrieval handle a cold agent searches by) survives in NO surface
lookback reads: not the projection filename (date+title+hash), not the title, not the
frontmatter.

These two pins assert the fix's properties, NOT the battery's (zero test edits to the
battery -- the lease's hard boundary):
  P1  a doc whose bytes live ONLY under docs/library/ is reachable by lookback at all
      (the corpus moved; the plane must follow);
  P2  a migrated doc's ORIGINAL slug resolves to its atom -- the handle, not just the
      bytes (content reachable as bytes, unreachable as a handle = the T113/f8510b6
      genus; the legacy_path -> art_id map the design promised at
      docs/library/design/20260723_kimi-half...§167, finally wired).

Run: py -m pytest tests/test_t109_lookback_migration_completion.py -q
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.recall import lookback as lb

# A governing design doc that exists ONLY as a library projection (its docs/*.md
# original was deleted in f8510b6). Chosen for distinctive vocabulary with no surviving
# top-level doc of the same name.
LIBRARY_ONLY_DOC_TERMS = "artifact substrate reconciled design atoms projections"


def _hits(question):
    return lb.lookback(question, layers=["docs"])


def test_p1_library_projection_is_in_the_docs_corpus():
    """The corpus moved to docs/library/; a plane that never scans it is blind to it."""
    hits = _hits("why do artifacts live as atoms with markdown as a projection")
    sources = " | ".join(str(h.get("source", "")) for h in hits)
    assert hits, "no docs-layer hits at all for a question the library corpus answers"
    assert "docs/library/" in sources, (
        f"every docs hit came from the top-level docs/ sweep; the projection plane "
        f"(docs/library/) is outside the corpus. Sources seen: {sources[:400]}")


def test_p2_original_slug_resolves_to_its_atom():
    """The retrieval handle, not just the bytes: asking by the DELETED doc's name must
    surface the atom that inherited its content."""
    # 'coordination-plan-synthesis' was docs/coordination-plan-synthesis.md, deleted in
    # f8510b6; its content lives on as
    # docs/library/design/20260710_multi-agent-coordination-layer-synthesis_283c99.md.
    hits = _hits("why is the task ledger the coordination substrate")
    blob = " | ".join(
        f"{h.get('layer')}:{h.get('source')}:{h.get('excerpt')}" for h in hits).lower()
    assert "coordination-plan-synthesis" in blob or "coordination" in blob, (
        "the original slug does not resolve: a cold agent asking by the deleted doc's "
        "name finds nothing that names it. Handle unreachable = migration incomplete. "
        f"Blob head: {blob[:400]}")
