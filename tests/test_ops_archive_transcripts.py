"""Transcript archive: the durable copy of the one plane git does not protect.

WHY THIS EXISTS (2026-08-11): the harness rotates session transcripts off disk silently. A
schema migration in THE EYE wiped its index on the strength of "a projection, rebuildable
from source" and destroyed events whose source had already rotated away. They were recovered
from a Windows shadow copy with hours to spare. Daniil: "we all put so much effort and our
best reasoning forward in those logs that it would be a tremendous loss to lose them."

THE RULE THAT IS THE WHOLE POINT -- the archive is ADDITIVE-ONLY. A sync that MIRRORS the
source deletes the archived copy the moment a transcript rotates off disk, which is the
original disaster reproduced faithfully, on a schedule, unattended. `robocopy /MIR` here
would be worse than having no backup at all. Same law the migration fix landed on: ADD,
never DROP. P1 is that pin and it is not negotiable.

SECOND RULE: transcripts are APPEND-ONLY, so bigger is always better. A source SMALLER than
its archived copy means truncation or corruption upstream -- the archive must refuse the
overwrite, keep the good copy, and say so (P2). A backup that faithfully replicates
corruption is a backup that destroys the last good copy on the day it matters.

THIRD RULE: it must be LOUD. This repo already carries `backup_door_never_ran` -- a backup
door that had never once succeeded while memory called it proven. A silent scheduled backup
is worse than none, because it manufactures confidence. Every run leaves a dated receipt and
a non-zero exit when anything was refused or failed (P7).

Run: py -m pytest tests/test_ops_archive_transcripts.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ops import archive_transcripts as ARC  # noqa: E402


def _mk(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture()
def rig(tmp_path):
    src = tmp_path / "projects" / "proj-a"
    a = _mk(src / "aaaaaaaa-1111.jsonl", '{"type":"user","t":1}\n')
    b = _mk(src / "bbbbbbbb-2222.jsonl", '{"type":"user","t":2}\n{"type":"assistant"}\n')
    d1 = tmp_path / "dest1"
    d2 = tmp_path / "dest2"
    return {"src_dir": src, "a": a, "b": b, "d1": d1, "d2": d2,
            "sources": [a, b], "dests": [d1, d2]}


# ---------------------------------------------------------------- P1: additive-only
def test_p1_a_source_that_rotated_away_is_NEVER_deleted_from_the_archive(rig):
    """THE pin. A transcript that has left the source is exactly what the archive is FOR --
    deleting it to 'match' would reproduce the incident this tool exists to prevent."""
    ARC.archive(rig["sources"], rig["dests"])
    rotated = rig["d1"] / "aaaaaaaa-1111.jsonl"
    assert rotated.exists()

    rig["a"].unlink()                                    # the harness rotates it off disk
    rep = ARC.archive([rig["b"]], rig["dests"])           # next run sees only b

    assert rotated.exists(), "THE ARCHIVE MUST KEEP WHAT THE SOURCE FORGOT"
    assert rotated.read_text(encoding="utf-8") == '{"type":"user","t":1}\n'
    assert rep["destinations"][0]["deleted"] == 0, "this tool has no delete path at all"


# ---------------------------------------------------------------- P2: refuse shrinking
def test_p2_a_shrunken_source_is_refused_and_the_good_copy_survives(rig):
    """Append-only means a smaller source is corruption upstream, never an update."""
    ARC.archive(rig["sources"], rig["dests"])
    good = (rig["d1"] / "bbbbbbbb-2222.jsonl").read_text(encoding="utf-8")

    rig["b"].write_text('{"type":"user"}\n', encoding="utf-8")   # truncated upstream
    rep = ARC.archive(rig["sources"], rig["dests"])

    assert (rig["d1"] / "bbbbbbbb-2222.jsonl").read_text(encoding="utf-8") == good, (
        "the archived copy was NOT overwritten by the shorter one")
    assert "bbbbbbbb-2222.jsonl" in str(rep["destinations"][0]["refused"])
    assert rep["ok"] is False, "a refusal is a loud outcome, not a quiet skip"


# ---------------------------------------------------------------- P3/P4: incremental
def test_p3_second_run_copies_nothing(rig):
    first = ARC.archive(rig["sources"], rig["dests"])
    assert first["destinations"][0]["copied"] == 2
    second = ARC.archive(rig["sources"], rig["dests"])
    assert second["destinations"][0]["copied"] == 0
    assert second["destinations"][0]["skipped"] == 2
    assert second["ok"] is True


def test_p4_an_appended_source_is_carried_over(rig):
    ARC.archive(rig["sources"], rig["dests"])
    with open(rig["a"], "a", encoding="utf-8") as fh:
        fh.write('{"type":"assistant","t":3}\n')
    rep = ARC.archive(rig["sources"], rig["dests"])
    assert rep["destinations"][0]["copied"] == 1
    assert (rig["d1"] / "aaaaaaaa-1111.jsonl").read_text(encoding="utf-8") == \
        rig["a"].read_text(encoding="utf-8")


# ---------------------------------------------------------------- P5: verification
def test_p5_verify_detects_a_corrupted_archive_copy_and_repairs_it(rig):
    """Equal SIZE is the cheap incremental signal; it cannot see rot. --verify hashes."""
    ARC.archive(rig["sources"], rig["dests"])
    victim = rig["d1"] / "bbbbbbbb-2222.jsonl"
    # PIN CORRECTED during the build: v1 hand-wrote a "same length" string that was not the
    # same length (text-mode newline translation on Windows makes the byte count differ from
    # the character count). Derive the size from the file so the pin exercises the case it
    # names -- size-equal rot, which the fast path CANNOT see and only --verify catches.
    victim.write_bytes(b"X" * rig["b"].stat().st_size)

    quiet = ARC.archive(rig["sources"], rig["dests"])
    assert quiet["destinations"][0]["copied"] == 0, "size-equal, so the fast path skips it"

    rep = ARC.archive(rig["sources"], rig["dests"], verify=True)
    assert rep["destinations"][0]["repaired"] == 1
    assert victim.read_text(encoding="utf-8") == rig["b"].read_text(encoding="utf-8")


# ---------------------------------------------------------------- P6: independence
def test_p6_one_unreachable_destination_does_not_cost_the_other(rig, tmp_path):
    """Two drives exist so that one can die. An unplugged drive must not abort the copy to
    the live one -- and must not be reported as if it had succeeded."""
    dead = tmp_path / "nope" / "nested"   # parent missing AND uncreatable is simulated below
    rep = ARC.archive(rig["sources"], [ARC.UNREACHABLE_PROBE, rig["d1"]])

    live = [d for d in rep["destinations"] if str(rig["d1"]) in d["path"]][0]
    dead_d = [d for d in rep["destinations"] if d["path"] == str(ARC.UNREACHABLE_PROBE)][0]
    assert live["copied"] == 2, "the reachable drive got its copy"
    assert dead_d["reachable"] is False
    assert dead_d["copied"] == 0
    assert rep["ok"] is False, "a destination we could not reach is not a success"


# ---------------------------------------------------------------- P7: the receipt
def test_p7_every_run_leaves_a_dated_receipt(rig, tmp_path):
    receipts = tmp_path / "receipts"
    rep = ARC.archive(rig["sources"], rig["dests"], receipt_dir=receipts)
    files = sorted(receipts.glob("archive-*.json"))
    assert len(files) == 1, "a run that leaves no trace is how a dead backup looks alive"
    # ...plus a stable `latest.json` pointer, so `--status` costs one read and never has to
    # sort filenames to find the newest (v1 of this pin counted *.json and did not know
    # about the pointer it was asking for).
    assert (receipts / "latest.json").exists()
    on_disk = json.loads(files[0].read_text(encoding="utf-8"))
    assert on_disk["sources_seen"] == 2
    assert on_disk["ok"] is True and rep["ok"] is True
    assert on_disk["ran_at"] and on_disk["destinations"][0]["present_total"] == 2


def test_p7b_exit_code_is_nonzero_when_anything_was_refused(rig, tmp_path):
    """A scheduler only ever sees the exit code."""
    ARC.archive(rig["sources"], rig["dests"])
    rig["b"].write_text("short\n", encoding="utf-8")
    assert ARC.main(["--source-dir", str(rig["src_dir"]),
                     "--dest", str(rig["d1"]),
                     "--receipt-dir", str(tmp_path / "r")]) != 0


def test_p7c_a_clean_run_exits_zero(rig, tmp_path):
    assert ARC.main(["--source-dir", str(rig["src_dir"]),
                     "--dest", str(rig["d1"]),
                     "--receipt-dir", str(tmp_path / "r")]) == 0


# ---------------------------------------------------------------- P8: source selection
def test_p8_subagent_transcripts_are_excluded_by_default_and_the_count_is_stated(tmp_path):
    """The eye's coverage lesson, applied here: a denominator that is itself a filter must
    declare what it filtered, or '94 files archived' silently means something else."""
    root = tmp_path / "projects"
    _mk(root / "proj-a" / "top-1.jsonl", "{}\n")
    _mk(root / "proj-a" / "sess" / "subagents" / "workflows" / "wf-1" / "sub-1.jsonl", "{}\n")

    picked, excluded = ARC.source_transcripts(root)
    assert [p.name for p in picked] == ["top-1.jsonl"]
    assert excluded == 1, "the excluded count rides the report, never silence"

    picked_all, _ = ARC.source_transcripts(root, include_subagents=True)
    assert len(picked_all) == 2


# ---------------------------------------------------------------- P9: test isolation
def test_p9_a_test_run_never_overwrites_the_production_receipt(rig):
    """Found live, by reading --status and seeing a pytest tmp_path reported as the last
    real run. `--status` is the operator's ONLY window onto whether the backup is healthy;
    a window showing test data as production is worse than no window. archive() with no
    explicit receipt_dir must not touch DEFAULT_RECEIPTS while pytest is running."""
    prod = ARC.DEFAULT_RECEIPTS / "latest.json"
    before = prod.read_text(encoding="utf-8") if prod.exists() else None

    ARC.archive(rig["sources"], rig["dests"])        # no receipt_dir -- the dangerous call

    after = prod.read_text(encoding="utf-8") if prod.exists() else None
    assert after == before, "the production receipt was left exactly as it was found"
