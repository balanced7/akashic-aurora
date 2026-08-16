"""RED: the private-plane leak guard -- ingress, at the one place everything must pass.

DANIIL'S RULING, 2026-08-16: "Lets not commit the competency and surname stuff to the repo.
I want to make sure its internally accesible." His standing directive, 2026-08-15: "instead
of a dance for redaction we have procedures and protocol." And his ingress principle: police
traffic closest to the source, not at the boundary.

THE LIVE INCIDENT. Personal assessment material was written to research/in-flight/ (tracked),
adopted into atoms whose BODIES landed in store/docs/report.jsonl (tracked), and rendered into
docs/library/report/ (tracked). Repo is public. Caught BY HAND at push -- pure egress.

WHY A GUARD AND NOT JUST A DIRECTORY. deepseek's fence counter (ask 4ec09cc3) named the class
this guard exists for: "any generator that walks the merged atom stream and writes to docs/ or
store/ becomes an egress point", and "existence metadata is a leak" -- a generator can publish
private TITLES and IDS while publishing no bodies at all. Verified live within minutes of that
counter: chronicles/memory.md is a TRACKED auto-regenerated distillation of 633 notes, and its
working-tree diff had already absorbed the portrait note and two operator-verbatim notes. The
directory move alone would not have stopped it, because the leak path is REGENERATION, not
authoring.

SO THE GUARD IS DERIVED, NOT DECLARED. It reads whatever actually lives in private/ and builds
its markers from that -- filenames, atom ids, note titles. A hand-maintained denylist would rot
the moment someone adds a file (the same reason the allowlist inversion was adopted for the
plane itself).

SCOPE: this is the BACKSTOP half of the design. The write-path half (visibility stamped at
mint, plane-routed writes, plane-aware projectors) is the larger arc the fence corrected --
deepseek showed two stores turns visibility into a second primary key, with real work needed
on id allocation, CAS, cross-plane supersession, rebuild order and backup. That is not this
slice. This slice makes the live hole un-reopenable while that gets designed properly.

Run: py -m pytest tests/test_private_plane_guard.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trust import private_plane as PP  # noqa: E402


@pytest.fixture()
def plane(tmp_path):
    """A private plane holding one assessment, mirroring the live shape."""
    priv = tmp_path / "private" / "assessments"
    priv.mkdir(parents=True)
    (priv / "REDACTED.md").write_text(
        "# The Daniil competency register\n\nname: synthetic-sample-dossier\n"
        "L1 findings: asked what a palindrome is.\n", encoding="utf-8")
    (priv / "atoms-private.jsonl").write_text(
        '{"id": "art_REDACTED", '
        '"title": "synthetic-sample-dossier"}\n', encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------- P1: markers are DERIVED
def test_p1_markers_come_from_what_is_actually_in_the_plane(plane):
    """A hand-maintained denylist rots the moment someone adds a file. The guard reads the
    plane."""
    m = PP.markers(root=plane)
    assert "ff00aa" in m, "the atom id short-hash is the strongest single marker"
    assert any("competency-register" in x for x in m), "the title/slug must be a marker"


def test_p1b_markers_are_not_generic_words(plane):
    """A marker like 'the' or 'daniil' would refuse every commit in the repo. The guard must
    be specific or it gets bypassed within a day (the wolf-guard law)."""
    m = PP.markers(root=plane)
    for junk in ("the", "and", "md", "report", "daniil"):
        assert junk not in m, f"{junk!r} is far too generic to be a leak marker"


# ---------------------------------------------------------------- P2: it catches the leak
def test_p2_a_tracked_file_carrying_a_marker_is_refused(plane, tmp_path):
    """The live shape: a generated chronicle absorbs a private note title."""
    tracked = plane / "chronicles" / "memory.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("- synthetic-sample-dossier: L1 findings...\n", encoding="utf-8")
    findings = PP.scan([str(tracked)], root=plane)
    assert findings, "a tracked file carrying a private marker must be refused"
    assert findings[0]["marker"]
    assert "memory.md" in findings[0]["path"]


def test_p2b_existence_metadata_counts_as_a_leak(plane):
    """deepseek's sharpest point: publishing IDS and TITLES leaks even with no body."""
    tracked = plane / "docs" / "MAP.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("atom art_REDACTED -> report\n",
                       encoding="utf-8")
    assert PP.scan([str(tracked)], root=plane), \
        "an id-only reference is still a leak -- existence metadata is content"


# ---------------------------------------------------------------- P3: the plane itself is ok
def test_p3_files_inside_the_private_plane_are_never_flagged(plane):
    """The guard protects the boundary, not the room. Flagging the plane's own files would
    make it unusable and train everyone to pass --no-verify."""
    inside = plane / "private" / "assessments" / "REDACTED.md"
    assert PP.scan([str(inside)], root=plane) == []


def test_p3b_an_ordinary_file_passes_clean(plane):
    ordinary = plane / "core" / "comm" / "kinds.py"
    ordinary.parent.mkdir(parents=True, exist_ok=True)
    ordinary.write_text("KIND_REGISTRY = {}\n", encoding="utf-8")
    assert PP.scan([str(ordinary)], root=plane) == []


# ---------------------------------------------------------------- P4: honest when empty
def test_p4_no_private_plane_means_no_markers_not_a_crash(tmp_path):
    """A machine with no private plane must not fail every commit, and must not silently
    report all-clear in a way indistinguishable from 'guard did not run'."""
    rep = PP.report([], root=tmp_path)
    assert rep["markers"] == 0
    assert rep["scanned"] == 0
    assert "no private plane" in rep["why"].lower()


def test_p4b_the_report_states_its_scope(plane):
    rep = PP.report([], root=plane)
    assert rep["markers"] > 0
    assert "scope" in rep, "a coverage claim must name what it globbed"


# ---------------------------------------------------------------- P5: refuses, teaches
def test_p5_a_finding_names_the_marker_the_file_and_the_remedy(plane):
    tracked = plane / "docs" / "MAP.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("see synthetic-sample-dossier\n", encoding="utf-8")
    f = PP.scan([str(tracked)], root=plane)[0]
    assert f["marker"] and f["path"] and f["line"]
    assert f["remedy"], "a refusal that does not say what to do next gets bypassed"
