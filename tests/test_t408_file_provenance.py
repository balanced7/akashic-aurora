"""Move 2 pins -- file-write provenance: a seat's guarded write records `file_edit` on the
raw firehose, attributed to the seat, queryable by `file:<rel>` so "who produced this
still-uncommitted file" is answerable instead of unanswerable (the dirty-tree problem).

The write goes through ToolBox.write_file/edit_file -> _record_file_provenance -> a
best-effort event_log.capture. The read is event_query.events_for_ref(ref). Both halves
reuse existing machinery (the OPEN `file_edit` kind; the `file:<path>` ref shape already
used by core.comm.promoter.promote_drop).

Hermetic: the ToolBox is built with root=tmp_path (its own repo root), so path-scope accepts
everything under it and nothing touches the real tree; get_event_log is monkeypatched to an
in-memory fake, so no canonical firehose and no Redis.

  P1  a successful write_file emits ONE file_edit event attributed to the seat, with a
      file:<rel> ref pointing at the written path
  P2  edit_file emits file_edit too (same seat, same ref, action=edit)
  P3  a failed write emits NOTHING -- provenance must not claim authorship for a write that
      never happened (a 2-match edit refuses after prewrite, so nothing should be recorded)
  P4  provenance is best-effort: a capture that raises must not break the write
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _FakeLog:
    """Minimal stand-in for EventLog with an in-memory list; no Redis, no file."""
    def __init__(self):
        self.events = []

    def capture(self, kind, summary, *, detail=None, agent_id=None, session_id="",
                refs=None, track=None, at=None):
        self.events.append({"kind": kind, "summary": summary, "detail": detail or {},
                            "agent_id": agent_id, "refs": refs or []})
        return None


@pytest.fixture()
def tb(monkeypatch, tmp_path):
    from core.comm import toolbox as tbmod
    fake = _FakeLog()
    monkeypatch.setattr("core.events.event_log.get_event_log", lambda ledger=None: fake)
    # Root = the temp dir, so `_prewrite`'s in-root path-scope passes and the write stays
    # fully hermetic (never touches the real tree). Import of event_log is lazy inside
    # _record_file_provenance, so the patch is picked up at capture time.
    box = tbmod.ToolBox(tmp_path, allow_write=True, allow_exec=False, trust=True,
                        allow_secrets=False, confirm=lambda p: False, agent_id="deepseek")
    box._provenance_fake = fake  # test-only reach-in; not part of the contract
    return box


def _captured(tb):
    return tb._provenance_fake.events


def test_p1_write_file_emits_seat_file_edit(tb):
    out = tb.write_file("notes/write_me.md", "hello")
    assert "wrote" in out and "ERROR" not in out, out
    evs = _captured(tb)
    assert len(evs) == 1, evs
    e = evs[0]
    assert e["kind"] == "file_edit"
    assert e["agent_id"] == "deepseek"
    assert e["refs"] == ["file:notes/write_me.md"], e["refs"]


def test_p2_edit_file_emits_seat_file_edit(tb):
    tb.write_file("notes/edit_me.md", "before")
    _captured(tb).clear()
    out = tb.edit_file("notes/edit_me.md", "before", "after")
    assert "edited" in out and "ERROR" not in out, out
    evs = _captured(tb)
    assert len(evs) == 1, evs
    assert evs[0]["kind"] == "file_edit"
    assert evs[0]["agent_id"] == "deepseek"
    assert evs[0]["detail"].get("action") == "edit"
    assert evs[0]["refs"] == ["file:notes/edit_me.md"], evs[0]["refs"]


def test_p3_failed_write_emits_nothing(tb):
    tb.write_file("notes/fail_me.md", "xx xx")
    _captured(tb).clear()
    out = tb.edit_file("notes/fail_me.md", "xx", "yy")   # matches 2 places -> refuses AFTER prewrite
    assert "ERROR" in out, out
    assert _captured(tb) == []


def test_p4_capture_failure_does_not_break_write(tb):
    tb._provenance_fake.capture = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    out = tb.write_file("notes/still_writes.md", "content")
    assert "wrote" in out and "ERROR" not in out, out


# ---- slice-tagging: a seat with a declared intent covering the path gets its writes tagged ----

def test_p5_write_under_declared_intent_is_tagged(tb, monkeypatch):
    """A seat that declared an intent covering the path has its file_edit event carry that
    intent tag in the detail -- the "toolcalls tagged as part of a project" half."""
    monkeypatch.setattr(
        "core.coord.intent.active",
        lambda agent=None, client=None: [{"agent": "deepseek", "intent": "t385 recall trigger",
                                          "scope": ["notes/"], "ts": "", "ttl": 900}])
    out = tb.write_file("notes/tagged.md", "x")
    assert "wrote" in out, out
    evs = _captured(tb)
    assert len(evs) == 1, evs
    assert evs[0]["detail"].get("intent") == "t385 recall trigger"


def test_p6_write_outside_any_intent_is_not_tagged(tb, monkeypatch):
    """A write whose path no active intent covers carries NO intent tag -- attribution stays
    truthful (no invented project), not universal."""
    monkeypatch.setattr(
        "core.coord.intent.active",
        lambda agent=None, client=None: [{"agent": "deepseek", "intent": "t385 recall trigger",
                                          "scope": ["other/"], "ts": "", "ttl": 900}])
    out = tb.write_file("notes/untagged.md", "x")
    assert "wrote" in out, out
    evs = _captured(tb)
    assert len(evs) == 1, evs
    assert "intent" not in evs[0]["detail"]


def test_p7_intent_lookup_failure_does_not_break_write(tb, monkeypatch):
    """A broken intent lookup must not wedge a write -- the tag is best-effort, provenance is too."""
    monkeypatch.setattr("core.coord.intent.active", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out = tb.write_file("notes/safe.md", "x")
    assert "wrote" in out and "ERROR" not in out, out

