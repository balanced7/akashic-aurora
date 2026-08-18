"""T352 acceptance pins — the suite must leave the production ledger untouched
(RED committed alone, M3).

RECEIPT: 32 phantom rows minted into state/coord/tasks.json between 2026-08-12
and 2026-08-18 (frobnicate/gizmo/t297-closable/T268-pin-target) by three test
files that exercise the REAL task door with no store isolation. ~10 phantom
'done' rows inflated every count the house quotes. Found by the T341 reentry
render's first live run; Daniil's ruling 2026-08-18, verbatim: "Clean".

Three pins:
  P1  TaskLedger honors AKASHIC_TASKS_PATH at construction — the isolation
      mechanism itself.
  P2  DONE -> ABANDONED exists as a gated route: refused without an explicit
      operator ruling, legal with one, and the ruling lands in history. (The
      16 phantom 'done' rows need this door; silent JSON surgery would defeat
      the gates the ledger exists to keep.)
  P3  THE CLASS-CLOSER: running each formerly-polluting test file under
      pytest leaves the production tasks.json byte-identical.

Run:  py -m pytest tests/test_t352_ledger_isolation_pins.py -v
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROD = os.path.join(ROOT, "state", "coord", "tasks.json")
DRILL_FILES = [
    "tests/test_t292_scout_role.py",
    "tests/test_t297_done_receipt_hex.py",
    "tests/test_wrap_routing.py",
]


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _tmp_ledger(tmp_path):
    p = tmp_path / "tasks.json"
    p.write_text(json.dumps({"tasks": [], "next_id": 1}), encoding="utf-8")
    return str(p)


# ---- P1: the isolation mechanism ---------------------------------------------
def test_p1_ledger_honors_env_path(tmp_path, monkeypatch):
    iso = _tmp_ledger(tmp_path)
    monkeypatch.setenv("AKASHIC_TASKS_PATH", iso)
    from core.coord.task_ledger import TaskLedger
    led = TaskLedger()
    assert led.path == iso, (
        "TaskLedger() must honor AKASHIC_TASKS_PATH at construction — without "
        "this, every drill through the real door lands in production")


# ---- P2: the operator-ruling route out of DONE -------------------------------
def test_p2_done_to_abandoned_is_gated_on_an_operator_ruling(tmp_path, monkeypatch):
    iso = _tmp_ledger(tmp_path)
    monkeypatch.setenv("AKASHIC_TASKS_PATH", iso)
    from core.coord import task_ledger as TL
    led = TL.TaskLedger()
    t = led.propose("t352 pin drill: a row that reaches done")
    tid = t["id"]
    TL.approve(led, tid, by="pin")
    TL.claim(led, tid, owner="pin", by="pin")
    TL.done(led, tid, commit="deadpin1", verified_by="pin", by="pin")

    # without a ruling: REFUSED (the gate is the point)
    with pytest.raises(Exception):
        TL.abandon(led, tid, reason="cleanup", by="pin")

    # with a ruling: legal, and the ruling is in the history entry
    TL.abandon(led, tid, reason="cleanup", by="pin",
               operator_ruling="Daniil 2026-08-18 verbatim: 'Clean'")
    row = led.get(tid)
    assert row["status"] == "abandoned"
    last = row["history"][-1]
    assert "operator_ruling" in last and "Clean" in last["operator_ruling"], (
        "the ruling that authorized leaving DONE must live in the history "
        "entry — a terminal-state exit with no recorded authority is a hole")


# ---- P3: the class-closer ----------------------------------------------------
@pytest.mark.parametrize("testfile", DRILL_FILES)
def test_p3_drill_file_leaves_production_ledger_byte_identical(testfile):
    before = _sha(PROD)
    r = subprocess.run(
        [sys.executable, "-m", "pytest", testfile, "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True, timeout=420,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    after = _sha(PROD)
    assert before == after, (
        f"{testfile} mutated the PRODUCTION ledger (sha {before[:12]} -> "
        f"{after[:12]}). A drill through the real door tests the DOOR, never "
        f"the production STORE. pytest rc={r.returncode}")
