"""Write-once project notes — record one atom (AgentMemory.decide), correct by superseding, and the
generated chronicles/memory.md digest is a derived projection (never hand-edited).

Run: py tests/test_notes.py   (or via pytest)
"""
import os
import sys
import tempfile

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.learning.agent_memory import AgentMemory
import agent_cli


def _mem():
    return AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "mem.json")))


def test_note_records_and_supersedes():
    mem = _mem()
    a = mem.decide(title="checkpoint", decision="recall-at-action done")
    assert a and len(mem.get_decisions(days=3650)) == 1
    b = mem.decide(title="checkpoint", decision="write-once done; FC-01 next", supersedes=a)
    active = mem.get_decisions(days=3650)
    assert len(active) == 1 and active[0].id == b, "superseding leaves exactly one active note"
    assert active[0].decision == "write-once done; FC-01 next"
    print("\n--- note supersession ---\n  correcting a note retires the prior; one active note OK")


def test_project_notes_renders_active_only():
    mem = _mem()
    a = mem.decide(title="alpha", decision="first state")
    mem.decide(title="alpha", decision="second state", supersedes=a)   # supersede first
    mem.decide(title="beta", decision="another note")
    path = agent_cli.project_notes(memory=mem, chronicle_dir=tempfile.mkdtemp())
    text = open(path, encoding="utf-8").read()
    assert "auto-generated from notes" in text
    assert "second state" in text and "another note" in text, "active notes are present"
    assert "first state" not in text, "the superseded note is excluded (write-once correction)"
    assert "(source: mem:decision:" in text, "digest lines carry lossless source pointers"
    print("--- project notes ---\n  digest renders ACTIVE notes only, with source pointers OK")


def test_empty_notes_graceful():
    path = agent_cli.project_notes(memory=_mem(), chronicle_dir=tempfile.mkdtemp())
    assert os.path.exists(path), "still writes a valid (empty) digest"
    print("--- empty ---\n  empty notes -> valid empty digest OK")


if __name__ == "__main__":
    print("=" * 60)
    print("WRITE-ONCE NOTES TESTS")
    print("=" * 60)
    test_note_records_and_supersedes()
    test_project_notes_renders_active_only()
    test_empty_notes_graceful()
    print("\n" + "=" * 60)
    print("ALL NOTES TESTS PASSED")
    print("=" * 60)
