"""T406 RED pins -- THE EYE cannot see the DSH plane, so Rill has no history.

THE MEASURED DEFECT, 2026-09-24:
    eye stats                          44,525 events / 1,466 sessions
    core.eye.index._corpus_roots()     live=~/.claude/projects, archive=*/transcripts/rolling,
                                       rescued=state/eye/recovered   -- all three are Claude Code
    C:/Users/L5/.dsh/sessions          25 sessions, 45.7 MB, 0 indexed

Every root the indexer reads is a Claude Code transcript plane. Rill (dsh_agent) writes to
`<home>/.dsh/sessions/<session-dir>/session.jsonl.zstd`, and NONE of it is in the corpus. The
live DSH session alone spans 2026-08-26 -> 2026-09-24 and carries 1,431 operator messages --
Daniel's words, absent from the organ built to keep his directives from evaporating.

WHY THIS IS WORSE THAN A MISSING FOLDER. On 2026-09-24 Rill designed the USN "machine diary"
with Daniel, then used THE EYE to check for prior art and reported: `eye find "USN journal"` = 0
hits, `freq` = UNHEARD, concluding "the disk-diary idea is genuinely fresh inside this house."
He ran an absence check from inside the one room the instrument cannot enter. Today that is
harmless because he IS the origin. It is wrong the first time anyone else asks, and it will be
wrong SILENTLY -- which is this house's own `zero_is_not_no` law, and the law is Rill's.

FOUR DEFECTS STACK HERE, and three of them are silent:

  1. The root is not declared.        Fixable by adding a path.
  2. The glob is "*.jsonl".           `session.jsonl.zstd` does not match, so declaring the
                                      root alone still yields nothing.
  3. The name-dedup collapses them.   _take() dedups by `p.name`, and EVERY DSH transcript is
                                      named exactly `session.jsonl.zstd`. 25 files -> 1 kept.
  4. The session id collides.         ingest() uses `f.stem`, which is "session.jsonl" for all
                                      of them. Every event lands under ONE session, event_ids
                                      collide, and INSERT OR IGNORE drops the rest without a
                                      word. This is the one that loses data rather than missing
                                      it, and it is invisible in every count the organ prints.

Pins 3 and 4 are the ones worth keeping after the fix: they fail the day someone adds a second
harness whose files share a basename, which is the general shape, not a DSH quirk.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# One real record of each DSH shape, copied from
# C:/Users/L5/.dsh/sessions/--E-AI-Setup--/session-4cd06dad-.../session.jsonl.zstd
DSH_OPERATOR = {
    "type": "user/message", "seq": 1250509, "time": 1790300029000,
    "data": {"text": "Hey Rill! Check out the new find verb that we just built!"},
}
DSH_AGENT = {
    "type": "assistant/message", "seq": 1250922, "time": 1790300100000,
    "data": {"turn": 171, "step": 1, "message": {"role": "assistant", "content": [
        {"type": "reasoning", "text": "Daniel is excited about a new find verb."},
        {"type": "text", "text": "That's a genuinely good one -- and the dogfood proves it."},
        {"type": "tool-call", "id": "call_00", "name": "pwsh", "arguments": "{}"},
    ]}},
}


def _dsh_root() -> Path:
    return Path.home() / ".dsh" / "sessions"


def _skip_without_dsh():
    if not _dsh_root().is_dir():
        import pytest
        pytest.skip("no DSH plane on this machine")


# ---------------------------------------------------------------- the declaration
def test_config_declares_the_dsh_root_once():
    """Same law T313 established for the archive: ONE home for the constant.

    The indexer must not carry its own literal, or the reader and whatever else needs to find
    DSH sessions can drift apart exactly the way the archiver and indexer did."""
    import config
    roots = getattr(config, "DSH_SESSION_ROOTS", None)
    assert roots, (
        "config.DSH_SESSION_ROOTS does not exist. The Eye's three roots are all Claude Code "
        "planes, so an entire harness -- Rill's -- is outside the corpus with nothing in the "
        "codebase even naming where it lives.")
    assert any(".dsh" in str(r).lower() for r in roots), \
        f"the DSH session root must be among the declared roots, got {roots}"


# ---------------------------------------------------------------- reach
def test_corpus_reaches_every_dsh_session_not_just_one():
    """Defect 3: _take() dedups by basename and every DSH file has the SAME basename.

    This is the pin that outlives DSH. Any harness that names its transcript by a fixed
    filename inside a per-session directory hits it, and the symptom is not an error -- it is
    a corpus that quietly contains one session out of twenty-five."""
    _skip_without_dsh()
    from core.eye.index import default_corpus
    on_disk = list(_dsh_root().rglob("session.jsonl*"))
    if not on_disk:
        import pytest
        pytest.skip("DSH root present but empty")
    seen = {str(p).lower() for p in default_corpus()}
    missing = [p for p in on_disk if str(p).lower() not in seen]
    assert not missing, (
        f"{len(missing)} of {len(on_disk)} DSH transcript(s) are invisible to default_corpus(). "
        f"Two separate causes: the glob is '*.jsonl' (these are '.jsonl.zstd'), and _take() "
        f"dedups by p.name -- every one of these files is named 'session.jsonl.zstd', so even "
        f"with the root declared, 24 of 25 would be dropped as duplicates.")


def test_coverage_publishes_the_dsh_root():
    """A corpus that does not state a plane cannot report that the plane went dark."""
    _skip_without_dsh()
    from core.eye.index import corpus_coverage
    cov = corpus_coverage()
    labels = {str(r.get("label", "")).lower() for r in cov.get("roots", [])}
    paths = " ".join(str(r.get("path", "")).lower() for r in cov.get("roots", []))
    assert "dsh" in labels or ".dsh" in paths, (
        f"corpus_coverage() does not name the DSH plane; roots reported: {cov.get('roots')}. "
        "An unnamed plane cannot shrink visibly.")


# ---------------------------------------------------------------- identity
def test_dsh_sessions_get_distinct_ids():
    """Defect 4, the silent data-loss one.

    ingest() derives `session = f.stem`. For `session.jsonl.zstd` that is the literal string
    "session.jsonl" -- identical for all 25 transcripts. Every event would be written as
    "session.jsonl:<line>", so line 12 of one session and line 12 of another are the SAME
    event_id, and the INSERT OR IGNORE swallows the loser. The organ would report a healthy
    ingest while holding one session's worth of a 25-session plane."""
    _skip_without_dsh()
    try:
        from core.eye.index import session_id_for
    except ImportError as e:
        raise AssertionError(
            f"core.eye.index.session_id_for(path) does not exist ({e}). Session identity is "
            "currently inlined as `f.stem` inside ingest(), which cannot be correct for any "
            "harness that names transcripts by a constant filename. It needs to be one named "
            "function so both the corpus and the ingest agree on what a session IS.")
    files = sorted(_dsh_root().rglob("session.jsonl*"))
    if len(files) < 2:
        import pytest
        pytest.skip("need two DSH sessions to prove ids do not collide")
    ids = [session_id_for(p) for p in files]
    assert len(set(ids)) == len(ids), (
        f"session_id_for() collides across DSH transcripts: {len(ids)} files -> "
        f"{len(set(ids))} distinct ids. Colliding ids do not error, they DROP events.")
    assert all(i and i != "session.jsonl" for i in ids), \
        f"ids must identify the session, not the filename; got e.g. {ids[:3]}"


def test_claude_session_ids_are_unchanged():
    """The fix must not renumber the 44,525 events already indexed.

    A session id change is a silent corpus wipe: every existing event_id becomes unreachable
    while the rows sit there. Claude transcripts must keep resolving to their stem."""
    try:
        from core.eye.index import session_id_for
    except ImportError:
        import pytest
        pytest.skip("session_id_for does not exist yet -- covered by its own pin")
    p = Path.home() / ".claude" / "projects" / "E--" / "deadbeef-1111-2222-3333-444455556666.jsonl"
    assert session_id_for(p) == "deadbeef-1111-2222-3333-444455556666", (
        "a Claude Code transcript must still resolve to its stem, or every event_id already "
        "in the database is orphaned")


# ---------------------------------------------------------------- reading
def test_a_compressed_transcript_is_readable():
    """Defect 2. The reader opens files with plain open(); zstd bytes decode to noise.

    Note the failure shape if this is not handled deliberately: errors='replace' means a
    compressed file does NOT raise. It yields garbage that fails json.loads and increments
    lines_unparsed -- a counter nobody reads -- so the ingest reports success."""
    _skip_without_dsh()
    try:
        from core.eye.index import open_transcript
    except ImportError as e:
        raise AssertionError(
            f"core.eye.index.open_transcript(path) does not exist ({e}). ingest() calls "
            "open(f, encoding='utf-8', errors='replace') directly, which cannot read a "
            "'.jsonl.zstd' and -- because of errors='replace' -- will not fail loudly either.")
    files = sorted(_dsh_root().rglob("session.jsonl.zstd"))
    if not files:
        import pytest
        pytest.skip("no compressed DSH transcript present")
    with open_transcript(files[0]) as fh:
        first = json.loads(next(iter(fh)))
    assert first.get("type") == "session", \
        f"first record of a DSH transcript should be the session header, got {first!r}"


# ---------------------------------------------------------------- mapping
def test_dsh_operator_message_is_operator_voice():
    """Daniel's words on the DSH plane must land on the operator axis.

    `freq` and the standing-directive watcher rank by operator sessions, so a DSH message
    recorded as anything else is a directive that cannot be counted."""
    from core.eye.index import _event_from
    ev = _event_from(DSH_OPERATOR)
    assert ev is not None, \
        "a DSH user/message produced no event -- _event_from only knows Claude Code's shapes"
    assert ev["voice"] == "operator", f"expected operator voice, got {ev['voice']!r}"
    assert "find verb" in ev["text"], f"text not extracted from data.text: {ev['text'][:80]!r}"


def test_dsh_agent_message_keeps_speech_and_drops_reasoning():
    """Rill's REPLY is an utterance; his reasoning is not, and it would drown the corpus.

    Measured in the live session: 58,889 reasoning-chunks against 943 assistant messages.
    Indexing reasoning as speech would make one seat louder than the entire operator axis and
    would put private deliberation into a plane Daniel searches for what was SAID."""
    from core.eye.index import _event_from
    ev = _event_from(DSH_AGENT)
    assert ev is not None, "a DSH assistant/message produced no event"
    assert ev["voice"] == "agent", f"expected agent voice, got {ev['voice']!r}"
    assert "dogfood proves it" in ev["text"], \
        f"the spoken 'text' block was not extracted: {ev['text'][:80]!r}"
    assert "Daniel is excited" not in ev["text"], \
        "the 'reasoning' block leaked into the indexed utterance"
    assert "call_00" not in ev["text"], "the tool-call block leaked into the indexed utterance"


def test_dsh_epoch_milliseconds_parse():
    """DSH stamps `time` as epoch ms; Claude Code stamps `timestamp` as ISO.

    _parse_ts does datetime.fromisoformat(str(raw)) and returns None for an int. A None ts is
    not an error -- it silently becomes part of eye stats' TIME-FOG, the share every as_of
    query is blind to. A whole harness landing in the fog is exactly the kind of quiet
    degradation the coverage contract exists to prevent."""
    from core.eye.index import _event_from
    ev = _event_from(DSH_OPERATOR)
    assert ev is not None and ev["ts"], \
        "DSH epoch-ms timestamps do not parse -- the whole plane would land in TIME-FOG"
    # 1790300029000 ms -> 2026-09-24 local. Assert the year rather than an exact instant.
    from datetime import datetime, timezone
    year = datetime.fromtimestamp(ev["ts"], tz=timezone.utc).year
    assert year == 2026, f"timestamp decoded to year {year} -- ms was probably read as seconds"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"  FAIL  {name}\n        {str(e)[:300]}")
            except Exception as e:
                failures += 1
                print(f"  ERROR {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"\n{failures} failing pin(s) -- RED is expected before T406 is built.")
    sys.exit(1 if failures else 0)
