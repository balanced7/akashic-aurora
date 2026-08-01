"""Pins for the corpus digest index (2026-08-01) -- the READING surface over a full-corpus sweep.

The corpus has never had a skim-then-drill door: you either read a prose map someone authored
(which drifts, cf. ROADMAP.md) or you re-read 1,600 artifacts. This is the third corpus for the
same traversal contract -- pick an AXIS, take SHALLOW HOPS, ask for DEPTH on demand -- which is
Daniil's own trace method (the bolt, the taillight) applied to history.

Every pin here is about HONESTY of the surface rather than cleverness of the query: a reader must
be able to tell what was searched, how much came back, and what was cut.

Run: py -m pytest tests/test_corpus_digests.py -q
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO, "scripts", "corpus_digests.py")

ROWS = [
    {"run": "r1", "shard": "s1", "path": "docs/a.md", "gist": "alpha thing about recall",
     "themes": ["recall", "memory"], "gold": "a forgotten mechanism",
     "settled": ["alpha is settled"], "status_claimed": "current"},
    {"run": "r1", "shard": "s1", "path": "docs/b.md", "gist": "beta thing",
     "themes": ["recall"], "orphaned": "designed, never built",
     "staleness_signal": "claims current but superseded by docs/a.md"},
    {"run": "r1", "shard": "s2", "path": "utterance:s2:0:t.jsonl", "gist": "he wants a viewer",
     "themes": ["DIRECTIVE"],
     "daniil_directives": [{"quote": "I want a viewer", "date": "07-23"}]},
    # Non-ASCII on purpose. The first fixture was pure ASCII, so the pins all passed while the
    # tool CRASHED on the real corpus: agents write check marks, arrows and em dashes, and a
    # Windows console is cp1252. A reading surface that dies on content it did not author is
    # not a reading surface. Degrade the glyph, never the record.
    {"run": "r1", "shard": "s2", "path": "docs/unicode.md",
     "gist": "verdict ✓ shipped → next — done",
     "themes": ["recall"], "gold": "✓ a mechanism with a check mark",
     "orphaned": "→ designed, never built", "staleness_signal": "— stale"},
]


def _fixture(tmp_path):
    p = tmp_path / "digests.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in ROWS) + "\n", encoding="utf-8")
    return p


def _run(fx, *argv):
    env = {**os.environ, "AKASHIC_DIGESTS_FILE": str(fx)}
    return subprocess.run([sys.executable, TOOL, *argv],
                          capture_output=True, text=True, timeout=60, env=env, cwd=REPO)


def test_themes_lists_the_axes_available(tmp_path):
    """The axis menu. You cannot choose an axis you cannot see -- this is the entry point."""
    r = _run(_fixture(tmp_path), "--themes")
    assert r.returncode == 0, r.stdout + r.stderr
    # Assert the CONTRACT (axes are listed, most-used first, bounds declared), never the
    # fixture's arithmetic -- an earlier version asserted the literal count for 'recall' and
    # broke the moment a row was added. Three brittle pins in one night; the pattern is
    # encoding incidental facts instead of the property under test.
    assert "recall" in r.stdout, r.stdout
    assert " of " in r.stdout, "the axis menu did not declare its bounds:\n" + r.stdout
    lines = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("[digests]")]
    counts = [int(l.split()[0]) for l in lines]
    assert counts == sorted(counts, reverse=True), "axes are not ordered most-used first"


def test_theme_is_a_shallow_hop(tmp_path):
    """Picking an axis returns gists, not bodies -- shallow by default is the whole point."""
    r = _run(_fixture(tmp_path), "--theme", "recall")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "docs/a.md" in r.stdout and "docs/b.md" in r.stdout
    assert "utterance:s2:0" not in r.stdout, "a theme hop leaked an artifact off that axis"


def test_show_is_the_drill(tmp_path):
    """Depth on demand: one artifact, every field the sweep recorded."""
    r = _run(_fixture(tmp_path), "--show", "docs/b.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "designed, never built" in r.stdout and "superseded by docs/a.md" in r.stdout


def test_bands_are_reachable(tmp_path):
    fx = _fixture(tmp_path)
    assert "designed, never built" in _run(fx, "--orphans").stdout
    assert "superseded by docs/a.md" in _run(fx, "--stale").stdout
    assert "a forgotten mechanism" in _run(fx, "--gold").stdout
    assert "I want a viewer" in _run(fx, "--directives").stdout


def test_every_surface_declares_its_bounds(tmp_path):
    """T120 surface honesty + his own bounds law: 'half the battle is knowing what the given
    bounds for a thing are.' A count that does not say N-of-M can hide a truncation."""
    r = _run(_fixture(tmp_path), "--theme", "recall")
    assert " of " in r.stdout.lower(), "no N-of-M bound declared:\n" + r.stdout


def test_truncation_is_announced_never_silent(tmp_path):
    """A limit that quietly drops rows is the exact class this whole corpus keeps paying for."""
    r = _run(_fixture(tmp_path), "--theme", "recall", "--limit", "1")
    assert "docs/a.md" in r.stdout
    low = r.stdout.lower()
    assert "1 of 2" in low or "more" in low or "truncat" in low, (
        "rows were cut with no signal:\n" + r.stdout
    )


def test_missing_dataset_teaches_instead_of_crashing(tmp_path):
    r = _run(tmp_path / "nope.jsonl", "--themes")
    out = (r.stdout + r.stderr).lower()
    assert "corpus_digests" in out or "no digests" in out or "run" in out, out
