"""T064 PRE-REGISTERED ACCEPTANCE -- over-cap intake spills to a file, never destroys.

Ledger T064 (approved, Daniel's gate 2026-07-15): handoff --note clips at 1000 chars
at WRITE time -- warn the writer AND point overflow to a file. The RB-5 confession
half already exists in agent_cli._intake (the 2026-07-11 knowledge_note incident);
what remains is that the clipped REMAINDER is destroyed ('remainder NOT stored').
Live evidence 2026-07-15: claude's own morning verify-handoff note rendered
'...[truncated]' -- the tail the target agent needed was gone.

Contract pinned here:
  S1  over-cap intake writes the FULL original to a spill file under
      AKASHIC_SPILL_DIR (default <repo>/state/spill), and the printed confession
      names that path (the WRITER is warned and pointed).
  S2  the stored text's in-band marker names the same path (the READER can drill
      from the clipped record itself -- boot briefs stay one hop from the tail).
  S3  under-cap values stay byte-identical: no marker, no confession, no file.
  S4  spill failure degrades to the OLD honest behavior (confession without a
      pointer) -- the door must never die because a disk write failed.

Run: py -m pytest tests/test_t064_intake_spill.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def _run(monkeypatch, tmp_path, body, cap=100):
    monkeypatch.setenv("AKASHIC_SPILL_DIR", str(tmp_path))
    confessions = []
    stored = agent_cli._intake(body, cap, "note", confessions)
    return stored, confessions


def test_s1_overflow_spills_full_original_and_confession_points(monkeypatch, tmp_path):
    body = "word " * 60   # 300 chars > 100 cap
    stored, confessions = _run(monkeypatch, tmp_path, body)
    assert confessions, "over-cap must confess"
    line = confessions[0]
    files = os.listdir(str(tmp_path))
    assert len(files) == 1, f"S1: exactly one spill file expected, got {files}"
    spill = os.path.join(str(tmp_path), files[0])
    assert files[0] in line, f"S1: confession must NAME the spill file: {line!r}"
    with open(spill, encoding="utf-8") as f:
        assert f.read() == body, "S1: spill file must hold the FULL original, byte-identical"


def test_s2_in_band_marker_names_the_spill(monkeypatch, tmp_path):
    body = "x" * 400
    stored, _ = _run(monkeypatch, tmp_path, body)
    files = os.listdir(str(tmp_path))
    assert files and files[0] in stored, \
        "S2: the stored text's in-band marker must point the READER at the spill file"
    assert stored.startswith("x" * 100), "S2: the stored head stays the clipped original"


def test_s3_under_cap_untouched(monkeypatch, tmp_path):
    body = "small note"
    stored, confessions = _run(monkeypatch, tmp_path, body)
    assert stored == body and not confessions
    assert os.listdir(str(tmp_path)) == [], "S3: no spill file for an under-cap value"


def test_s4_spill_failure_degrades_to_confession(monkeypatch, tmp_path):
    deadend = os.path.join(str(tmp_path), "not-a-dir")
    with open(deadend, "w") as f:   # a FILE where a directory must be -> makedirs fails
        f.write("block")
    monkeypatch.setenv("AKASHIC_SPILL_DIR", deadend)
    confessions = []
    stored = agent_cli._intake("y" * 300, 100, "note", confessions)
    assert confessions and "resend" in confessions[0].lower(), \
        "S4: spill failure keeps the honest confession (chunk/resend guidance)"
    assert stored.startswith("y" * 100) and "clipped at" in stored, \
        "S4: in-band marker survives even when the spill write fails"
