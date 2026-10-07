"""Pins for the report shelf (core/library/reports.py).

R1-R3 pin the parse/derive path -- a report that cannot be labelled must still be
listed, because an invisible report is worse than a thinly-labelled one.
R4-R6 pin the two-shelf law: private never claims to be fleet, and the filters that
keep them apart actually separate them.
R7-R9 pin compare(), including the set-precedence trap that `a - a & b` silently
collapses to the empty set -- the bug this suite was written after.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.library import reports as rs


# --------------------------------------------------------------------------- fixtures

FRONT = """---
akashic_id: art_20260812_alpha_aaa111
status: current
type: report
date: 2026-08-12
title: alpha sweep
gist: "first sweep"
visibility: private
category: [method, tooling]
seats: ["claude", "kimi"]
arc: T300
settled: settled
supersedes: null
superseded: null
---

# alpha sweep

Body text for alpha.
"""

BARE = """# bare report

No frontmatter at all; the shelf must still list this.
"""


class FakeFamily:
    """Minimal stand-in for AtomFamily -- find/get only, which is all the shelf reads."""

    def __init__(self, atoms):
        self._atoms = {a["id"]: a for a in atoms}

    def find(self, *, type_=None, arc=None, category=None, status=None):
        out = [a for a in self._atoms.values()
               if type_ is None or a["header"]["type"] == type_]
        return sorted(out, key=lambda a: a["created_ts"], reverse=True)

    def get(self, atom_id):
        return self._atoms.get(atom_id)


def _atom(aid, title, *, date, cats, seats, arc=None, status="current",
          supersedes=None, superseded=None, body="fleet body"):
    return {
        "id": aid,
        "header": {"status": status, "type": "report", "arc": arc, "seats": seats,
                   "date": date, "title": title, "category": cats,
                   "visibility": "fleet", "gist": f"gist of {title}"},
        "body": body, "supersedes": supersedes, "superseded": superseded,
        "citations_out": [], "created_ts": 1000.0,
    }


@pytest.fixture()
def family():
    return FakeFamily([
        _atom("art_a", "fleet one", date="2026-08-10", cats=["method"],
              seats=["claude"], arc="T300"),
        _atom("art_b", "fleet two", date="2026-08-11", cats=["method", "ui"],
              seats=["claude", "deepseek"], arc="T300", superseded="art_c"),
        _atom("art_old", "stale one", date="2026-07-01", cats=["ui"],
              seats=["kimi"], status="superseded"),
    ])


@pytest.fixture()
def priv(tmp_path: Path) -> Path:
    root = tmp_path / "private"
    root.mkdir()
    (root / "20260812_alpha_aaa111.md").write_text(FRONT, encoding="utf-8")
    (root / "20260801_bare.md").write_text(BARE, encoding="utf-8")
    return root


# --------------------------------------------------------------------------- R1-R3

def test_r1_frontmatter_parses_scalars_lists_and_nulls():
    header, body = rs.parse_frontmatter(FRONT)
    assert header["title"] == "alpha sweep"
    assert header["category"] == ["method", "tooling"]
    assert header["seats"] == ["claude", "kimi"]
    assert header["supersedes"] is None
    assert body.startswith("# alpha sweep")


def test_r2_bare_file_is_still_listed_with_a_derived_title(priv):
    out = rs.list_reports(None, private_dir=priv, status=None)
    titles = {r["title"] for r in out["reports"]}
    assert "bare report" in titles, "a report without frontmatter must not vanish"


def test_r3_date_is_derived_from_filename_when_absent(priv):
    out = rs.list_reports(None, private_dir=priv, status=None)
    bare = next(r for r in out["reports"] if r["title"] == "bare report")
    assert bare["date"] == "2026-08-01"


# --------------------------------------------------------------------------- R4-R6

def test_r4_private_reports_never_claim_fleet_visibility(priv):
    out = rs.list_reports(None, private_dir=priv, status=None)
    assert out["reports"], "fixture should produce cards"
    for card in out["reports"]:
        assert card["shelf"] == rs.PRIVATE_SHELF
        assert card["visibility"] != "fleet"


def test_r5_shelf_filter_separates_the_two_shelves(family, priv):
    both = rs.list_reports(family, private_dir=priv, status=None)
    fleet = rs.list_reports(family, private_dir=priv, status=None, shelf=rs.FLEET_SHELF)
    private = rs.list_reports(family, private_dir=priv, status=None, shelf=rs.PRIVATE_SHELF)
    assert both["total"] == fleet["total"] + private["total"]
    assert all(c["shelf"] == rs.FLEET_SHELF for c in fleet["reports"])
    assert all(c["shelf"] == rs.PRIVATE_SHELF for c in private["reports"])


def test_r6_default_status_hides_superseded_reports(family):
    default = rs.list_reports(family)
    everything = rs.list_reports(family, status=None)
    assert "stale one" not in {c["title"] for c in default["reports"]}
    assert "stale one" in {c["title"] for c in everything["reports"]}


# --------------------------------------------------------------------------- R7-R9

def test_r7_compare_reports_disjoint_seats_on_both_sides(family):
    """The precedence trap: `left - left & right` collapses to empty, so a genuine
    left-only seat silently disappears. Pin both directions."""
    out = rs.compare(family, "art_a", "art_b")
    assert out["seats"]["shared"] == ["claude"]
    assert out["seats"]["right_only"] == ["deepseek"]
    other = rs.compare(family, "art_b", "art_a")
    assert other["seats"]["left_only"] == ["deepseek"], \
        "left_only must be populated -- set-operator precedence bug"


def test_r8_compare_names_the_lineage_relation(family):
    out = rs.compare(family, "art_a", "art_b")
    assert out["lineage"] == "same arc, independent"


def test_r9_compare_missing_report_reports_which_one(family):
    out = rs.compare(family, "art_a", "art_missing")
    assert out.get("error")
    assert out["missing"] == ["art_missing"]


def test_r10_search_matches_all_tokens(family):
    hit = rs.list_reports(family, q="fleet two")
    miss = rs.list_reports(family, q="fleet nonexistentword")
    assert {c["title"] for c in hit["reports"]} == {"fleet two"}
    assert miss["total"] == 0
