"""Pins for arc_thread.py -- door 2 of the library (LIBRARY.md), claude's G6 slice.

The arc-thread reconstructs an arc from the HEADER plane (Arc: fields), never folders --
that is the whole point of the one-facet law. These pins hold that contract:
  A1  a known ratified arc (library-schema) surfaces its reconciliation + LIBRARY.md
  A2  the header walk matches on the Arc: field, tolerant of multi-arc and legacy Class:
  A3  output is chronological (oldest first), undated items sink deterministically
  A4  an unknown arc returns cleanly (no crash, honest empty)
  A5  --no-store never shells the store (offline-safe, fast)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import arc_thread  # noqa: E402


def test_a1_library_schema_arc_finds_its_law():
    items = arc_thread.build_thread("library-schema", use_store=False)
    refs = {it["ref"] for it in items}
    assert any("LIBRARY.md" in r for r in refs), "the ratified law must be in its own arc"
    assert any("reconciliation" in r for r in refs), "the decision record must be in the arc"
    assert all(it["plane"] in ("file", "git") for it in items)


def test_a2_arc_match_is_field_based_and_tolerant():
    assert arc_thread._arc_matches("library-schema", "library-schema")
    assert arc_thread._arc_matches("recall, library-schema", "library-schema")  # multi-arc
    assert arc_thread._arc_matches("library_schema", "library-schema")          # underscore
    assert arc_thread._arc_matches("T094 / recall", "t094")                     # case + slash
    assert not arc_thread._arc_matches("recall", "library-schema")


def test_a3_thread_is_chronological():
    items = arc_thread.build_thread("library-schema", use_store=False)
    dates = [it["date"] or "9999" for it in items]
    assert dates == sorted(dates), "thread must be oldest-first"


def test_a4_unknown_arc_is_clean_empty():
    items = arc_thread.build_thread("no-such-arc-xyzzy-2099", use_store=False)
    assert items == []
    out = arc_thread.render("no-such-arc-xyzzy-2099", items)
    assert "no artifacts found" in out


def test_a5_no_store_flag_skips_store_plane():
    # use_store=False must never produce a store-plane item
    items = arc_thread.build_thread("library-schema", use_store=False)
    assert not any(it["plane"] == "store" for it in items)
