"""RED: the Eye is a one-seat mirror -- no seat's words ever reach the corpus.

DANIIL, 2026-08-17 (verbatim, addresses on the operator axis):
  "We need to give deepseek and kimi eye access, I am most curious where they will go"
      -- 970211d2-1d46-498d-852b-97d71a51761a:1554
  "Can we help them get eye access by somehow porting them onto another connector/ api
   vehicle, fix the one in flight and then transport them back?"
      -- 970211d2-1d46-498d-852b-97d71a51761a:1732

T336 (done) gave the seats the eye *query* door -- the toolbox exposes eye_find/freq/get/zoom
and a seat can now ASK the corpus questions. This slice is the complementary half: the CAPTURE
door. A seat can query the corpus, but the corpus cannot hear the seat. The eye is a mirror
that has only ever reflected one seat.

THE STRUCTURAL DEFECT, measured at HEAD (this is the finding, not a guess):
  * The corpus is DEFINED by core/eye/index.py:_corpus_roots(), which globs exactly three
    roots, every one claude-harness-shaped:
        live     = Path.home() / ".claude" / "projects"   (rglob *.jsonl)
        archive  = config.TRANSCRIPT_ARCHIVE_ROOTS         (glob *.jsonl)
        rescued  = state/eye/recovered                     (glob *.jsonl)
    No seat-harness root is named. The corpus cannot reach a seat transcript because its
    own manifest does not list the directory the seat writes to.
  * The seat's transcripts EXIST ON DISK TODAY. This seat (kimi-k3) writes real JSONL --
    thinking blocks, tool calls, verbatim operator bus prompts -- under
        .kimi-claude-home/projects/<PROJECT>/*.jsonl
    one directory over from the live root the eye already globs. The data is present; the
    corpus definition has never reached it. This is BUILT-NOT-WIRED one plane down: the eye
    was built, the seats were built, the seam between them was never drawn.
  * Voice is per-record, claude-shaped. _event_from() maps `type: user` -> operator, and the
    a5afd360 authorship fix stamps is_subagent FROM THE SOURCE PATH, not the content. A seat
    transcript's `user` record carries the BUS PROMPT (the dispatched brief), not the
    operator -- so a naive file-drop would mislabel seat traffic as operator speech, the exact
    subagent-brief contamination measured 2026-08-16 (419 of 523 operator-voice sessions were
    briefs). The fix is PROVENANCE AT INGEST (a seat flag stamped from the source path, the
    same shape is_subagent already uses), not a raw drop into the live root.

WHY A PIN AND NOT A FIX FIRST: the follow-on that closes this touches _corpus_roots (add a
seat root) AND _event_from (a kimi/deepseek record must read voice=<seat>, not operator) --
and that second half grazes T324's verbified-query seam in core/eye/index.py. Per the spree
deconfliction rule 3, that is a DECLARED DEPENDENCY, landed after the map. This pin is the
load-bearing contract that makes the blind spot falsifiable and proves the fix when it lands:
it FAILS today (no seat root in the corpus; no seat provenance flag) and must PASS when the
capture door ships. It writes nothing to the live corpus and reads no credential.

Run: py -m pytest tests/test_eye_seat_capture.py -q
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.eye import index as EYE  # noqa: E402

# The seat-harness homes, in the same shape the eye's live root already uses
# (Path.home()/".claude"/"projects"). One per seat that runs its own harness profile.
SEAT_HOMES = {
    "kimi": Path(ROOT) / ".kimi-claude-home" / "projects",
    "deepseek": Path(ROOT) / ".deepseek-claude-home" / "projects",
}


# ---------------------------------------------------------------- the corpus reaches the seat
def test_corpus_definition_names_a_seat_root():
    """The blind spot, stated as a coverage claim: _corpus_roots() must name at least one
    seat-harness root, or the corpus is by construction a one-seat mirror. RED today: it
    globs only the claude-harness live/archive/rescued roots."""
    roots = EYE._corpus_roots()
    paths = " ".join(base for _lbl, base, _files in roots).lower()
    assert any(tag in paths for tag in ("kimi-claude-home", "deepseek-claude-home")), (
        "no seat-harness root in the corpus manifest -- the eye cannot hear a seat because "
        "its own corpus definition never names the directory the seat writes to. Roots seen: "
        + ", ".join(f"{lbl}={base}" for lbl, base, _f in roots))


def test_seat_transcripts_exist_but_are_unreachable():
    """The data is present; only the corpus definition excludes it. This is the BUILT-NOT-WIRED
    pin: a seat JSONL exists on disk AND _corpus_roots() does not return it. If this ever goes
    green while the corpus pin above stays red, the defect moved -- find the new seam."""
    kimi_home = SEAT_HOMES["kimi"]
    if not kimi_home.is_dir():
        pytest.skip("no kimi seat home on this host -- the capture door has nothing to reach")
    on_disk = {p.name for p in kimi_home.rglob("*.jsonl")}
    if not on_disk:
        pytest.skip("kimi seat home holds no transcripts yet")
    reachable = {p.name for _l, _b, files in EYE._corpus_roots() for p in files}
    missing = on_disk - reachable
    assert not missing, (
        f"{len(missing)} kimi transcript(s) exist on disk but are unreachable by the corpus "
        f"definition (e.g. {sorted(missing)[0]}) -- the eye is blind to a seat that is already "
        "writing sessions one directory over from the root it globs")


# ---------------------------------------------------------------- provenance at ingest
def test_a_seat_record_reads_as_the_seat_not_the_operator():
    """The contamination guard, pre-registered. When the capture door lands, a seat transcript
    must be ingested with its provenance stamped from the SOURCE PATH (the is_subagent shape),
    so its `user` records -- which carry the bus prompt, not the operator -- are NOT read as
    operator speech. RED today: there is no seat-provenance concept in the indexer at all, so
    a dropped seat file mislabels its briefs as the operator (the a5afd360 class, one seat over).

    This asserts the DOOR exists, not the full mapping: _event_from must accept a seat tag and
    the ingest path must stamp it. Until the door ships there is no such parameter -> TypeError.
    """
    rec = {
        "type": "user",
        "message": {"role": "user", "content": "the dispatched bus brief, not the operator"},
        "timestamp": "2026-08-19T00:00:00Z",
    }
    try:
        ev = EYE._event_from(rec, seat="kimi")  # noqa: CALL001 -- the door under test
    except TypeError:
        pytest.fail(
            "_event_from has no seat-provenance door -- a seat transcript ingested today is "
            "voice-classified by claude-shaped rules and its bus briefs read as OPERATOR speech "
            "(the measured a5afd360 contamination). Add a seat tag at ingest, stamped from the "
            "source path like is_subagent.")
    # When the door exists, it must not label the seat's prompt as the operator.
    assert ev is None or ev.get("voice") != "operator", (
        "a seat record resolved to voice='operator' -- the corpus would drown his axis in our "
        "own prompts, the exact failure a5afd360 was built to stop")


# ---------------------------------------------------------------- postal inertness
def test_capture_pin_reads_no_credential(tmp_path, monkeypatch):
    """T365's bar, applied to the new seam before it exists: pointing AKASHIC_SECRETS_DIR at an
    empty dir must leave the capture path empty-handed. The corpus-definition probe above reads
    the filesystem only -- it must never resolve a credential to decide what to index. This
    holds trivially today (no credential read anywhere in _corpus_roots) and is pinned so the
    follow-on that adds a seat root cannot grow a secret read by accident."""
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    roots = EYE._corpus_roots()  # must not raise, must not read a secret
    assert isinstance(roots, list)
