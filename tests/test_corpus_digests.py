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
    # The substring trap (codex, 2026-08-01, reproduced live: menu said '95 recall', the hop
    # returned '137 of 137'). Menu counts EXACT labels; the hop matched SUBSTRINGS -- so the
    # two surfaces described different sets, and the hop claimed completeness while doing it.
    {"run": "r1", "shard": "s1", "path": "docs/at.md", "gist": "the recall-at hook",
     "themes": ["recall-at"]},
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


# --- codex's review corrections (2026-08-01) -------------------------------------------------

def test_menu_and_hop_describe_the_same_set(tmp_path):
    """Menu cardinality MUST equal hop cardinality for the same label. Reproduced live: the
    menu said '95 recall' while --theme recall returned '137 of 137' via substring match --
    two surfaces describing different sets, one of them claiming completeness."""
    import re
    fx = _fixture(tmp_path)
    menu = _run(fx, "--themes").stdout
    m = re.search(r"^\s+(\d+)\s+recall\s*$", menu, re.M)
    assert m, "menu lost the exact 'recall' label:\n" + menu
    hop = _run(fx, "--theme", "recall").stdout
    h = re.search(r"\[digests\] (\d+) of (\d+)", hop)
    assert h and h.group(2) == m.group(1), (
        f"menu says {m.group(1)} but the hop's total is {h.group(2) if h else '?'} -- "
        "two surfaces, two different sets:\n" + hop
    )
    assert "docs/at.md" not in hop, "exact hop leaked the 'recall-at' row via substring"


def test_contains_is_opt_in_and_says_so(tmp_path):
    """Substring browsing stays available, but as a DECLARED different query."""
    r = _run(_fixture(tmp_path), "--theme", "recall", "--contains")
    assert "docs/at.md" in r.stdout, "contains-mode should include recall-at:\n" + r.stdout
    # Assert the CONTRACT word ("substring" -- the match semantics), not incidental phrasing.
    assert "substring" in r.stdout.lower(), "contains-mode did not declare itself:\n" + r.stdout


def test_no_surface_prints_unbounded_by_default(tmp_path):
    """codex measured --directives at 284k tokens and --orphans at 95k: EVERY altitude needs a
    budget, not just the menu. Default cap + announced truncation + a continuation pointer."""
    rows = [{"run": "r", "path": f"docs/x{i}.md", "gist": "g", "themes": ["bulk"]}
            for i in range(55)]
    p = tmp_path / "digests.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
    out = _run(p, "--theme", "bulk").stdout
    assert "40 of 55" in out and "TRUNCATED" in out, "no default budget:\n" + out[:500]
    assert "--offset" in out, "truncation offered no continuation mechanism:\n" + out[:500]
    out_all = _run(p, "--theme", "bulk", "--all").stdout
    assert "55 of 55" in out_all, "--all did not lift the cap"
    out_page2 = _run(p, "--theme", "bulk", "--offset", "40").stdout
    assert "docs/x40.md" in out_page2 and "docs/x39.md" not in out_page2


def test_bands_are_labeled_claims_not_facts(tmp_path):
    """The critic proved the sweep's bands carry false positives (TOON-class). A band header
    that reads as fact launders an agent's claim into a finding."""
    r = _run(_fixture(tmp_path), "--orphans")
    assert "claim" in r.stdout.lower(), "orphan band reads as fact:\n" + r.stdout.splitlines()[0]


# --- the join: narrative <-> specifics ------------------------------------------------------
# The spine already implements skim-then-drill (--themes / --theme / --chapter / --beat / --raw)
# and its beats already carry pointers -- but ONLY `git:SHA`. Not atoms, not lessons, not his
# directives. So the general and the specific have never been connected for anything except
# commits. The join key is TIME CONTAINMENT: a chapter carries span_start/span_end, a digest
# carries a date. That is a fact, not an inference -- no prose is interpreted to produce it.

CHAPTERS = [
    {"id": "chapter_aaa", "track": "ai-setup", "title": "The alpha arc",
     "span_start": "2026-07-01T00:00:00-04:00", "span_end": "2026-07-10T00:00:00-04:00"},
    {"id": "chapter_bbb", "track": "ai-setup", "title": "The beta arc",
     "span_start": "2026-07-20T00:00:00-04:00", "span_end": "2026-07-30T00:00:00-04:00"},
]

DATED = [
    {"run": "r1", "path": "docs/early.md", "gist": "in alpha", "date": "2026-07-05", "themes": []},
    {"run": "r1", "path": "docs/late.md", "gist": "in beta", "date": "2026-07-23", "themes": []},
    {"run": "r1", "path": "docs/undated.md", "gist": "no date at all", "themes": []},
]


def _joined(tmp_path):
    d = tmp_path / "digests.jsonl"
    d.write_text("\n".join(json.dumps(r) for r in DATED) + "\n", encoding="utf-8")
    c = tmp_path / "chapters.json"
    c.write_text(json.dumps(CHAPTERS), encoding="utf-8")
    return d, c


def _runj(fx, ch, *argv):
    env = {**os.environ, "AKASHIC_DIGESTS_FILE": str(fx), "AKASHIC_CHAPTERS_FILE": str(ch)}
    return subprocess.run([sys.executable, TOOL, *argv],
                          capture_output=True, text=True, timeout=60, env=env, cwd=REPO)


def test_artifact_resolves_to_its_chapter(tmp_path):
    """From a specific, arrive at the general."""
    fx, ch = _joined(tmp_path)
    r = _runj(fx, ch, "--chapter-of", "docs/late.md")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "chapter_bbb" in r.stdout and "beta arc" in r.stdout, r.stdout
    assert "chapter_aaa" not in r.stdout, "matched a chapter whose span does not contain it"


def test_chapter_resolves_to_its_artifacts(tmp_path):
    """From the general, arrive at the specifics -- the whole point of the exercise."""
    fx, ch = _joined(tmp_path)
    r = _runj(fx, ch, "--in-chapter", "chapter_aaa")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "docs/early.md" in r.stdout and "docs/late.md" not in r.stdout, r.stdout


def test_undated_digests_are_reported_never_silently_dropped(tmp_path):
    """A record with no date cannot be placed. Saying so is the difference between a gap and a
    lie -- UNSCANNED is not EMPTY, applied to the join itself."""
    fx, ch = _joined(tmp_path)
    r = _runj(fx, ch, "--in-chapter", "chapter_aaa")
    low = r.stdout.lower()
    assert "undated" in low or "unplaceable" in low or "no date" in low, (
        "1 undated digest vanished from the join with no signal:\n" + r.stdout
    )
