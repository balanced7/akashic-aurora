"""RB-5 class regression -- storage-intake bounds must CONFESS, never clip silently.

Incident (2026-07-11 night, docs/rb23-build-spec-2026-07-11.md incident record): deepseek's
knowledge_note tool-args (notes t034-registry-design-deepseek, -part2) were silently
word-clipped at ~4013 chars by the NOTE DOOR -- agent_cli cmd_note stored
`_clip(args.note)` (4000-char cap, " ...[truncated]" marker) while printing plain
[OK], which IS the tool result the agent sees. The deepseek_chat.py Agent dispatch was
exonerated by inspection: tool-call argument deltas accumulate unbounded
(scripts/deepseek_chat.py:820), args are parsed with plain json.loads (:853) and handed
whole to the ToolBox (:860); the [:160]/[:140]/[:120] slices there are console/trace
display only. So the door contract is pinned HERE, at cmd_note:

  a >5k-char note body either STORES WHOLE, or the door's printed RESULT carries an
  explicit clip confession ([CLIPPED] ... line, and `clipped` field in --json mode),
  plus an in-band marker inside the stored text itself.

Run: py tests/test_intake_clip_confession.py   (or via pytest)
"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from types import SimpleNamespace

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
import agent_cli


class _quiet_fanout:
    """Silence cmd_note's best-effort side fanouts (digest regen, narrative beat, raw
    event) so the test exercises exactly the door->store contract against a temp store,
    and never regenerates the real chronicles digest from test data."""

    def __enter__(self):
        import core.events.event_log as ev
        import core.narrative.beat_log as bl
        import core.learning.agent_memory as am
        self._ev, self._bl, self._am = ev, bl, am
        # T069 (repaired 2026-07-15): under _AISETUP_TEST_ISOLATED the doors
        # construct FRESH instances and ignore the cache global this context
        # injects -- in a full-suite run (where another module's import sets the
        # flag for everyone) cmd_note wrote past f.mem and _stored found nothing.
        # This context IS its own sandbox (temp FileStore + silenced fanouts), so
        # the ambient flag is cleared for its scope and restored on exit.
        self._iso = os.environ.pop("_AISETUP_TEST_ISOLATED", None)
        self._saved = (agent_cli.project_notes, ev.capture_event, bl.get_beat_log,
                       am._agent_memory)
        agent_cli.project_notes = lambda *a, **k: None
        ev.capture_event = lambda *a, **k: None
        bl.get_beat_log = lambda: SimpleNamespace(emit=lambda *a, **k: None)
        self.mem = am.AgentMemory(store=FileStore(os.path.join(tempfile.mkdtemp(), "mem.json")))
        am._agent_memory = self.mem
        return self

    def __exit__(self, *exc):
        if self._iso is not None:
            os.environ["_AISETUP_TEST_ISOLATED"] = self._iso
        (agent_cli.project_notes, self._ev.capture_event, self._bl.get_beat_log,
         self._am._agent_memory) = self._saved
        return False


def _note_args(**kw):
    base = dict(agent_id="clipbot", title="clip-probe", note="", context=None,
                supersedes=None, session=None, retire=None, json=False, category=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _run_note(args):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = agent_cli.cmd_note(args)
    return rc, out.getvalue()


def _stored(mem, title):
    d = next((d for d in mem.get_decisions(days=3650) if d.title == title), None)
    assert d is not None, f"note '{title}' not found in the store"
    return d.decision


def test_5k_note_arg_stores_whole():
    """THE named acceptance: a >5k-char note tool-arg stores whole -- no silent clip,
    no lying [OK], no legacy ' ...[truncated]' marker."""
    body = ("the quick brown clip probe sentence %04d. " % 7) * 130   # ~5.6k, word-boundary rich
    assert len(body) > 5000
    with _quiet_fanout() as f:
        rc, out = _run_note(_note_args(title="clip-probe-5k", note=body))
        stored = _stored(f.mem, "clip-probe-5k")
    assert rc == 0 and "[OK] noted" in out
    assert stored == body, f"stored {len(stored)}/{len(body)} chars -- the door clipped"
    assert " ...[truncated]" not in stored, "legacy silent-clip marker resurfaced"
    assert "[CLIPPED]" not in out, "door confessed a clip it did not make"
    print("  5k note body stores WHOLE (no clip, no false confession) OK")


def test_over_cap_note_confesses_in_result_and_in_band(monkeypatch, tmp_path):
    """Above the (raised) cap the bound may bite -- but it must CONFESS in the door's
    printed RESULT and leave an in-band marker in the stored text. T064 upgraded the
    contract: the confession now POINTS (spill file with the full original) when it
    can, and falls back to resend guidance when the spill write fails."""
    monkeypatch.setenv("AKASHIC_SPILL_DIR", str(tmp_path))
    cap = agent_cli._MAX_NOTE
    body = "x" * (cap + 5000)
    with _quiet_fanout() as f:
        rc, out = _run_note(_note_args(title="clip-probe-overcap", note=body))
        stored = _stored(f.mem, "clip-probe-overcap")
    assert rc == 0 and "[OK] noted" in out
    assert "[CLIPPED]" in out and "note body" in out and \
           ("spilled to" in out or "resend" in out.lower()), \
        f"over-cap store did not confess in the result: {out!r}"
    assert stored.startswith("x" * 100) and "...[clipped at" in stored, \
        "stored text lacks the in-band clip marker"
    spills = os.listdir(str(tmp_path))
    assert spills, "T064: the full original must spill to a file"
    with open(os.path.join(str(tmp_path), spills[0]), encoding="utf-8") as fh:
        assert fh.read() == body, "T064: spill holds the FULL original"
    print("  over-cap note CONFESSES + spills the full original OK")


def test_json_mode_carries_confession():
    """knowledge doors are consumed programmatically too -- --json must carry the clip."""
    cap = agent_cli._MAX_NOTE
    with _quiet_fanout():
        rc, out = _run_note(_note_args(title="clip-probe-json", note="y" * (cap + 100), json=True))
    doc = json.loads(out)
    assert rc == 0 and doc["recorded"] is True
    assert doc["clipped"] and any("note body" in c for c in doc["clipped"]), \
        f"--json result lacks the clip confession: {doc}"
    print("  --json result carries the confession OK")


def test_small_note_unchanged():
    """The historical common case must stay byte-identical -- no marker, no confession."""
    body = "small durable note body. " * 40   # ~1k
    with _quiet_fanout() as f:
        rc, out = _run_note(_note_args(title="clip-probe-small", note=body))
        stored = _stored(f.mem, "clip-probe-small")
    assert rc == 0 and stored == body and "[CLIPPED]" not in out
    print("  under-cap note byte-identical, silent OK")


if __name__ == "__main__":
    print("=" * 60)
    print("STORAGE-INTAKE CLIP CONFESSION TESTS (RB-5 class)")
    print("=" * 60)
    test_5k_note_arg_stores_whole()
    test_over_cap_note_confesses_in_result_and_in_band()
    test_json_mode_carries_confession()
    test_small_note_unchanged()
    print("\n" + "=" * 60)
    print("ALL CLIP-CONFESSION TESTS PASSED")
    print("=" * 60)
