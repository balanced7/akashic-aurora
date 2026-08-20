"""T273 slice 1, RED: the clip contract, pinned before a single migration.

Daniil, 2026-08-10, verbatim: "How can we fix all clipping instances everywhere so we stop
running into that issue?"

WHY AN AUDIT CANNOT ANSWER HIM, which is the load-bearing reason this is a chokepoint slice and
not a sweep: x[:200] is a clip only when x is text someone else needs and will not see the rest
of. Syntactically identical, semantically opposite. Two detector attempts over-counted 179 then
364. My own census tonight, scoped to the declared seam with a variable-name heuristic, read 13
text clips against 15 list slices -- and that heuristic is a guess too, not truth. Token-level
tools cannot detect forked MEANINGS by construction, so the fix must make the NEXT silent clip
impossible to add rather than find today's.

THE POPULATION IS GROWING WHILE THE FIX WAITS. T273's census counted five independent clippers.
Tonight a live grep found eight -- and one of the new ones (core/comm/discord_bridge.chunk) was
minted by FIXING a clipping bug. We are fixing clippers by adding clippers.

THE THRESHOLD IS MEASURED, NOT CHOSEN. Live cut sizes across the seam: 64, 120, 200, 220, 500,
2000, 8000, 65536. Those are three tiers, not a spectrum: previews (64-500), a hard transport cap
(2000, Discord -- physics, not policy), and the already-shipped byte-PRESERVING door
(packet_spec.TOOL_SEND_TEXT_MAX = 8000, deepseek's D3 verdict 2026-07-19). So the spill point is
not mine to invent; it is in the tree, and this contract binds to it so the two cannot drift.

THE CONTRACT, paid for three times separately and never written down together:
  T220 clipped with NO address                -> data loss by design
  T222 minted an address that did not resolve -> WORSE: a dead pointer looks actionable and costs
                                                 a turn to discover it is decoration
  T263 tool door spilled while the CLI door clipped -> one concept, two behaviours, same house
So: above the threshold SPILL and return a ref that resolves FROM A THIRD PARTY; below it, either
CHUNK (the transport has a hard cap) or DECLARE N-of-M with a recovery command that actually RUNS;
never a bare ellipsis.

REFINEMENT THE MEASUREMENT PRODUCED: T273 wrote the below-threshold path as one rule. It is two.
Discord's 2000 cannot be negotiated, so N parts is the only faithful answer there (Heimdall's T368
whole-line chunker is the reference); a 220-char inbox preview must NOT mint a blob, so it declares
its bounds instead. One threshold, two below-strategies, chosen by whether the cap is physics.

SLICE 1 IS PINS ONLY -- zero migrations, which also keeps T273's own sequencing note intact
(it lands after the n=5 drill, and rewriting files the drill is measuring would front-run it).

Run:  py -m pytest tests/test_clip_chokepoint_contract.py -v
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

pytestmark = pytest.mark.xfail(raises=(ImportError, ModuleNotFoundError, AttributeError),
                              reason="T273 slice 1 is RED by design: the canonical clipper does "
                                     "not exist yet. These pins ARE the pre-registration.",
                              strict=True)


def _clip():
    from core.primitives import clip
    return clip


# ------------------------------------------------------------------ the threshold
def test_threshold_binds_to_the_shipped_spill_door_and_cannot_drift():
    """8000 is not a taste. It is packet_spec.TOOL_SEND_TEXT_MAX, already shipped and already
    byte-preserving. If someone retunes one number, this pin fails rather than letting the house
    hold two thresholds for one concept -- which IS the T263 defect restated."""
    from core.comm.packet_spec import TOOL_SEND_TEXT_MAX
    assert _clip().SPILL_THRESHOLD == TOOL_SEND_TEXT_MAX


def test_the_threshold_records_its_own_measurement():
    """Tonight's 5s-vs-16s lesson, applied: a bound whose provenance is not written down gets
    rounded back to a comfortable number by the next tidy-up."""
    doc = _clip().__doc__ or ""
    assert "8000" in doc or "TOOL_SEND_TEXT_MAX" in doc
    assert any(w in doc.lower() for w in ("measured", "distribution", "live")), doc[:200]


# ------------------------------------------------------------- above: spill, and it RESOLVES
def test_above_threshold_preserves_every_byte():
    big = "x" * 20000
    r = _clip().clip(big, surface="tool_send")
    assert r.spilled, "above the threshold the bytes must survive, not be destroyed"
    assert r.ref, "a spill without a ref is T220: data loss by design"


def test_the_ref_resolves_from_a_THIRD_party():
    """T222's whole lesson. Verifying that a pointer was PRINTED is not verifying that it
    RESOLVES, and a dead pointer is worse than none because it looks actionable. So this pin
    resolves the ref through a reader that is neither the sender nor the recipient."""
    big = "y" * 20000
    r = _clip().clip(big, surface="tool_send")
    got = _clip().resolve(r.ref, as_agent="a-third-party-who-never-saw-it")
    assert got == big, "the ref must return the ORIGINAL bytes to a stranger"


# ---------------------------------------------- below: chunk when the cap is physics
def test_below_threshold_with_a_hard_cap_chunks_into_n_parts():
    """Discord's 2000 cannot be negotiated, so N whole-line parts is the only faithful answer.
    Reusing Heimdall's T368 logic rather than minting a ninth clipper."""
    body = "\n".join("line {} ".format(i) + "z" * 80 for i in range(60))
    parts = _clip().clip(body, surface="discord", hard_cap=2000).parts
    assert len(parts) > 1
    assert all(len(p) <= 2000 for p in parts)
    assert "".join(parts).replace("\n", "") == body.replace("\n", ""), "no byte lost to chunking"


# ------------------------------------- below: declare N-of-M, with a command that RUNS
def test_below_threshold_preview_declares_n_of_m_and_never_a_bare_ellipsis():
    body = "w" * 5000
    r = _clip().clip(body, surface="inbox_preview", limit=220)
    assert not r.spilled, "a 220-char preview must not mint a blob"
    assert "of" in r.render and "5000" in r.render.replace(",", ""), r.render
    assert not r.render.rstrip().endswith(("...", "…")), "a bare ellipsis is no address"


def test_the_recovery_COMMAND_IS_RUN_not_merely_printed():
    """T222 again, and the sharpest pin in the file: asserting that a recovery command was
    printed proves nothing. The pin RUNS it and demands the body back. Tonight's !spawn taught
    the same thing one layer up -- a receipt about a syscall is not a receipt about the world."""
    body = "v" * 5000
    r = _clip().clip(body, surface="inbox_preview", limit=220)
    assert r.recovery_cmd, "below the threshold there must be a way back to the bytes"
    out = subprocess.run(r.recovery_cmd, shell=True, cwd=str(REPO), capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=120)
    assert out.returncode == 0, "the recovery command does not run: {}".format(out.stderr[:300])
    assert "v" * 200 in (out.stdout or ""), "it ran, but it did not return the body"


def test_a_phone_can_run_the_recovery_command():
    """His reader is Daniil on a phone (T368's finding). A recovery handle that requires a shell
    he does not have is the T220/T222 defect wearing gloves."""
    r = _clip().clip("u" * 5000, surface="discord", limit=220)
    assert "bifrost-fetch" not in (r.render or ""), \
        "a shell command is not a recovery path for a phone reader"


# ------------------------------------------------------------------- the ratchet
def test_a_new_raw_text_truncation_outside_the_helper_FAILS_the_checker():
    """The chokepoint's teeth. Today's instances freeze as a backlog exactly like check_wiring's
    116, so 'where do we clip' becomes 'who calls the clipper' -- mechanically answerable."""
    checker = REPO / "scripts" / "checkers" / "check_clip_chokepoint.py"
    assert checker.exists(), "the ratchet is the half that stops the ninth clipper"
    victim = REPO / "core" / "_t273_ratchet_probe.py"
    victim.write_text("def leak(body):\n    return str(body)[:500]   # a new silent text clip\n",
                      encoding="utf-8")
    try:
        out = subprocess.run([sys.executable, str(checker)], cwd=str(REPO),
                             capture_output=True, text=True, timeout=180)
        assert out.returncode != 0, "the ratchet let a NEW raw text truncation through"
    finally:
        victim.unlink(missing_ok=True)


def test_the_ratchet_does_not_fire_on_a_list_slice():
    """The false-positive floor, and the reason the two earlier detectors were abandoned:
    hits[:25] is not a clip. A ratchet that cries wolf on list slices gets switched off."""
    checker = REPO / "scripts" / "checkers" / "check_clip_chokepoint.py"
    assert checker.exists(), "no checker yet -- this pin must fail on ABSENCE, not pretend the "                              "ratchet misfired (a missing script exits 2 and would read as a hit)"
    victim = REPO / "core" / "_t273_ratchet_probe.py"
    victim.write_text("def top(hits):\n    return hits[:25]   # a LIST slice, not a clip\n",
                      encoding="utf-8")
    try:
        out = subprocess.run([sys.executable, str(checker)], cwd=str(REPO),
                             capture_output=True, text=True, timeout=180)
        assert out.returncode == 0, "the ratchet fired on a list slice: {}".format(out.stdout[-300:])
    finally:
        victim.unlink(missing_ok=True)
