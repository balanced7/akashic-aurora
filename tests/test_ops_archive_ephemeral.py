"""The ephemeral planes: exported, archived, queryable.

Audit 2026-08-11, after the transcript archive landed. What was still ephemeral:

  - the BUS. Streams are bounded transport by design (bus.DEFAULT_MAXLEN=10_000) and hold
    ~3 days. SALIENT kinds are already promoted to the durable event log at send time
    (bus.py:593) -- but `chat`, `fyi` and `trace` are not, and that is where a sibling's
    full diagnosis, a peer's report and every narration actually live. The house has been
    covering this with manual discipline (lesson research_full_fidelity_preservation:
    "persist frontier agents' FULL reports ... chat is disposable"). A rule that depends on
    someone remembering is not a mechanism.
  - `session_logs/` (111 MB: learnings.jsonl + store state), `state/spill/` (111 files that
    37 DURABLE records point at by path), `state/wire/`. All local-only, none on the E:/F:
    archive, all gitignored.
  - `backups/` -- snapshot_knowledge output living on the SAME PHYSICAL DISK as the thing it
    protects, which is a copy rather than a backup.

The copy laws are NOT reimplemented here: this imports the engine from
archive_transcripts (additive-only, refuse-shrinking, verify, receipt) because a second
implementation of a safety law is a second thing that can be wrong. What is new is the
EXPORT step -- a Redis stream is not a file until someone writes it down.

Run: py -m pytest tests/test_ops_archive_ephemeral.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ops import archive_ephemeral as EPH  # noqa: E402


class FakeRedis:
    """A stream store with the only two behaviours that matter here: entries are ordered
    by id, and old entries VANISH (that is the whole problem being solved)."""

    def __init__(self, streams):
        self._s = {k: list(v) for k, v in streams.items()}

    def scan_iter(self, match=None, count=None):
        return iter(list(self._s.keys()))

    def type(self, k):
        return "stream" if k in self._s else "none"

    def xlen(self, k):
        return len(self._s.get(k, []))

    def xrange(self, k, min="-", max="+", count=None):
        rows = self._s.get(k, [])
        if min != "-":
            floor = min[1:] if min.startswith("(") else min
            rows = [r for r in rows if r[0] > floor] if min.startswith("(") else \
                   [r for r in rows if r[0] >= floor]
        return rows[:count] if count else rows

    def trim_to(self, k, keep_last):
        self._s[k] = self._s[k][-keep_last:]

    def append(self, k, mid, payload):
        self._s.setdefault(k, []).append((mid, payload))


@pytest.fixture()
def rig(tmp_path):
    r = FakeRedis({
        "bifrost:broadcast": [("1000-0", {"frm": "kimi", "kind": "chat", "content": "alpha"}),
                              ("1001-0", {"frm": "deepseek", "kind": "fyi", "content": "beta"})],
        "bifrost:trace": [("1000-0", {"frm": "claude", "kind": "trace", "content": "t1"})],
    })
    return {"r": r, "out": tmp_path / "bus", "cursor": tmp_path / "cursors.json"}


# ---------------------------------------------------------------- P1: export
def test_p1_streams_become_durable_jsonl_one_file_per_stream(rig):
    rep = EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])
    f = rig["out"] / "bifrost_broadcast.jsonl"
    assert f.exists()
    rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == ["1000-0", "1001-0"]
    assert rows[0]["stream"] == "bifrost:broadcast"
    assert rows[0]["fields"]["content"] == "alpha", "the payload is kept whole, not summarised"
    assert rep["streams"] == 2 and rep["entries_written"] == 3


# ---------------------------------------------------------------- P2: incremental
def test_p2_export_resumes_from_its_cursor_and_never_duplicates(rig):
    EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])
    rig["r"].append("bifrost:broadcast", "1002-0", {"frm": "kimi", "content": "gamma"})
    rep = EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])

    rows = [json.loads(l) for l in
            (rig["out"] / "bifrost_broadcast.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == ["1000-0", "1001-0", "1002-0"], "appended, not rewritten"
    assert rep["entries_written"] == 1, "only the new entry"


# ---------------------------------------------------------------- P3: THE POINT
def test_p3_trimmed_entries_survive_in_the_export(rig):
    """The bus is bounded transport. Once exported, a trimmed message is still readable --
    this is the entire reason the tool exists."""
    EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])
    rig["r"].trim_to("bifrost:broadcast", 1)            # the bus forgets 'alpha'
    assert rig["r"].xlen("bifrost:broadcast") == 1

    EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])
    body = (rig["out"] / "bifrost_broadcast.jsonl").read_text(encoding="utf-8")
    assert "alpha" in body, "THE EXPORT KEEPS WHAT THE BUS DROPPED"
    assert body.count('"1000-0"') == 1, "and does not resurrect it as a duplicate"


# ---------------------------------------------------------------- P4: queryable
def test_p4_the_export_is_queryable_by_who_kind_and_phrase(rig):
    EPH.export_bus(rig["r"], rig["out"], cursor_file=rig["cursor"])
    hits = EPH.search(rig["out"], q="alpha")
    # FIXTURE CORRECTED after the first live run: these records use `frm`, which is the
    # field the real bifrost envelope carries. v1 invented `from`, so the who= facet passed
    # its pin and returned silent-empty against every real message on disk.
    assert len(hits) == 1 and hits[0]["fields"]["frm"] == "kimi"

    assert len(EPH.search(rig["out"], who="deepseek")) == 1
    assert len(EPH.search(rig["out"], kind="chat")) == 1
    assert EPH.search(rig["out"], who="kimi", kind="fyi") == [], "facets AND together"
    assert EPH.search(rig["out"], q="nothing-here") == [], "a real miss is empty"


# ---------------------------------------------------------------- P5: reuses the laws
def test_p5_state_archiving_reuses_the_proven_engine_not_a_second_copy_of_it(tmp_path):
    """A second implementation of a safety law is a second thing that can be wrong."""
    from scripts.ops import archive_transcripts as ARC
    assert EPH.archive is ARC.archive, "same engine: additive-only, refuse-shrink, verify"

    src = tmp_path / "spill"
    src.mkdir()
    (src / "note-1.txt").write_text("body", encoding="utf-8")
    d = tmp_path / "dest"
    rep = EPH.archive([src / "note-1.txt"], [d], receipt_dir=tmp_path / "r")
    assert rep["ok"] and (d / "note-1.txt").exists()

    (src / "note-1.txt").unlink()                       # the source is cleaned up
    EPH.archive([], [d], receipt_dir=tmp_path / "r")
    assert (d / "note-1.txt").exists(), "additive-only carries over unchanged"


# ---------------------------------------------------------------- P6: the source set
def test_p6_collect_names_every_plane_and_states_what_it_skipped(tmp_path):
    root = tmp_path / "repo"
    (root / "state" / "spill").mkdir(parents=True)
    (root / "state" / "spill" / "a.txt").write_text("x", encoding="utf-8")
    (root / "session_logs").mkdir(parents=True)
    (root / "session_logs" / "learnings.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "session_logs" / "scratch.tmp").write_text("junk", encoding="utf-8")

    files, planes = EPH.collect_state(root)
    names = {f.name for f in files}
    assert "a.txt" in names and "learnings.jsonl" in names
    assert "scratch.tmp" not in names, "temp files are not the record"
    assert planes["state/spill"] == 1 and planes["session_logs"] == 1, (
        "per-plane counts ride the report -- an archive that cannot say WHAT it covered "
        "is how a plane goes quietly uncovered")
