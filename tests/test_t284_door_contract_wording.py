"""T284: the door's concurrency contract must claim exactly what the implementation gives.

WHAT HAPPENED. The MCP server instructions claimed "writes/sends/consumes serialize
server-side for ordering." The implementation is ONE `threading.RLock` in ai_setup_mcp.py --
process-local by construction. A CLI-shell write from another process never touches that
lock; cross-process, the real guarantees are per-operation Redis atomicity plus advisory
locks, and the read-modify-write hole was MEASURED (filestore_coherence_hole lesson: 66%
loss at 3 concurrent processes before CAS landed). Two external reviewers hit the gap the
same night: Gemini read the overclaim as a universal serializer AND parsed the "O1" slice id
as O(1) complexity notation; Codex could not find the claimed serialization and said so.
A door contract that overclaims teaches callers to skip the locks that actually protect them.

Pins (structural, over the instructions string):
  P1  the instructions no longer claim bare "server-side" serialization -- the scope
      qualifier ("within this server process") is present
  P2  the cross-process story is stated: backend-atomic single-key ops + CAS/advisory locks
  P3  the O1 homonym is disarmed (the text says it is a task id, not complexity notation)
  P4  the process-local lock the narrowed claim rests on still exists

Run: py -m pytest tests/test_t284_door_contract_wording.py -q
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parents[1]
SRC = io.open(ROOT / "ai_setup_mcp.py", encoding="utf-8").read()


def _instructions_block() -> str:
    """The server instructions literal: from the Akashic Aurora opener to the tool defs."""
    i = SRC.find("Akashic Aurora: a shared-memory system")
    assert i > 0, "instructions literal not found"
    return SRC[i:i + 4000]


def test_p1_no_bare_server_side_claim():
    block = _instructions_block()
    assert "WITHIN THIS SERVER PROCESS" in block, (
        "P1: the serialization claim must carry its process-local scope qualifier")
    assert not re.search(r"serialize server-side", block), (
        "P1: the bare 'serialize server-side' overclaim must be gone -- a CLI write from "
        "another process never touches the door's RLock")


def test_p2_cross_process_story_stated():
    block = _instructions_block()
    for needle in ("Across", "backend-atomic", "CAS", "advisory lock"):
        assert needle in block, (
            f"P2: the cross-process contract must state '{needle}' -- callers doing "
            "read-modify-write across processes need to know the door cannot order them")


def test_p3_o1_homonym_disarmed():
    block = _instructions_block()
    assert "not O(1)" in block or "task id" in block, (
        "P3: 'O1' must be marked as a slice/task id -- an external reviewer parsed it as "
        "O(1) complexity notation (the T174 homonym class, in our own door docs)")


def test_p4_the_narrowed_claim_still_rests_on_a_real_lock():
    assert "_WRITE_LOCK = threading.RLock()" in SRC, (
        "P4: the process-local write lock the narrowed claim describes must still exist -- "
        "if the lock goes, the instructions must change again")
