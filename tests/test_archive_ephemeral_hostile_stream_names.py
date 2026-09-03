"""Pins for the 2026-09-02 bus-archive incident: a literal stream `bifrost:inbox:*`
(minted by a `to:"*"` send on 08-28) crashed the WHOLE nightly bus export for 5 days
-- `*` is invalid in a Windows filename, the OSError escaped the per-stream guard,
and the cursor save died with it. File archiving kept reporting green throughout.

Two laws pinned:
1. `_safe_name` sanitizes the MEANING (every Windows-invalid character), not a
   membership list of the two characters we had met so far.
2. One stream's failure is a loud line in the report -- never an abort of the
   remaining streams, and never a lost cursor save.
"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ops.archive_ephemeral import _safe_name, export_bus  # noqa: E402


def test_safe_name_neutralizes_every_windows_invalid_character():
    hostile = 'bifrost:inbox:*<>?"|\\/x'
    name = _safe_name(hostile)
    for ch in ':*<>?"|\\/':
        assert ch not in name, f"{ch!r} survived _safe_name -> unwritable filename"
    # the incident literal, exactly:
    assert _safe_name("bifrost:inbox:*") == "bifrost_inbox__"


class _FakeRedis:
    """Two streams: one healthy, one whose name is hostile. Minimal surface."""

    def __init__(self):
        self.streams = {
            "bifrost:inbox:good": [("1-1", {"frm": "daniil", "content": '"hello"'})],
            "bifrost:inbox:*": [("1-1", {"frm": "dsh_agent", "content": '"fyi"'})],
        }

    def scan_iter(self, match="*", count=0):
        return list(self.streams.keys())

    def type(self, key):
        return "stream"

    def xrange(self, key, min="-"):
        if key == "bifrost:inbox:*":
            # simulate the incident class: ANY per-stream explosion, not just
            # the filename one -- the containment must be general.
            raise OSError(22, "Invalid argument", key)
        return self.streams[key]


def test_one_hostile_stream_cannot_zero_the_export(tmp_path):
    rep = export_bus(_FakeRedis(), tmp_path, cursor_file=tmp_path / "cur.json")

    # the healthy stream exported...
    out = tmp_path / "bifrost_inbox_good.jsonl"
    assert out.exists(), "healthy stream must export despite a hostile sibling"
    assert rep["entries_written"] == 1

    # ...the cursor save survived...
    cursors = json.loads((tmp_path / "cur.json").read_text(encoding="utf-8"))
    assert cursors.get("bifrost:inbox:good") == "1-1"

    # ...and the failure is CONFESSED, not silent and not fatal.
    assert rep.get("failed_streams"), "a failed stream must appear in the report"
    assert rep["failed_streams"][0]["stream"] == "bifrost:inbox:*"
