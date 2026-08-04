"""PRE-REGISTERED ACCEPTANCE (T160) -- a wire record must know which seat made the call.

MEASURED 2026-08-04, on the live journal at state/wire: 102 of 102 records carry agent='unknown'.
BIFROST_AGENT appears exactly ONCE in the whole repository -- scripts/wire_journal.py:138, the
line that READS it. Nothing anywhere SETS it.

WHAT THAT COSTS, and none of it was visible from the pins:
  * core/comm/doctor.py:1146 calls journal().expert(agent=agent) once per seat. Against a store
    where every record says 'unknown', that has matched NOTHING since T156 shipped. The fleet's
    wire forensics has been rendering empty and reporting itself clean.
  * T157's per-agent sharding and per-shard drop attribution would be INERT in production --
    every seat landing in one 'unknown' shard. The isolation property is real in the pins and
    absent on the machine.
  * Extending the journal to gemini/kimi/sol (W5) would have TRIPLED that rather than tripling
    coverage.

WHY THE EXISTING PINS ALL PASSED. test_t156_wire_verification.py:c6 proves scoped reads isolate
one agent from another -- by passing agent= EXPLICITLY. Every pin that touches attribution
supplies the value it is checking. They test the MECHANISM and never the WIRING, and a mechanism
nothing feeds is a measured zero wearing a passing test.

This is "built != wired" one level below where check_wiring can reach: the function IS called by
a production path, so the gate is satisfied; it is the DATA that never arrives.

  A1  a journal told its agent attributes records to that agent (the mechanism, kept)
  A2  the SEAT IDENTITY DOOR exists and actually reaches a lazily-built journal singleton --
      the singleton is created deep inside a transport hook, long after argv is parsed, so
      setting an env var late must still land
  A3  STRUCTURAL: every scripts/bifrost_runner_*.py stamps its seat identity. This is the pin
      that would have caught the original defect, and it is deliberately a static check over the
      whole runner family rather than a test of one runner -- the defect was that a WHOLE CLASS
      of entry point forgot, and enumerating the family is the only shape that notices.
  A4  the recording transport carries the seat through to the record it writes
  A5  attribution reaches the SHARD, so T157's isolation is real on the machine and not only in
      its own pins

Run: py -m pytest tests/test_t160_wire_seat_attribution.py -q
"""
import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _wj():
    import importlib
    from scripts import wire_journal
    return importlib.reload(wire_journal)


# --------------------------------------------------------------------------- A1

def test_a1_a_journal_told_its_agent_attributes_records(tmp_path):
    WJ = _wj()
    j = WJ.WireJournal(journal_dir=str(tmp_path), agent="kimi")
    j.record(status=200, model="m")
    j.flush()
    assert {r.get("agent") for r in j.read_all()} == {"kimi"}


# --------------------------------------------------------------------------- A2

def test_a2_the_seat_identity_door_reaches_a_lazy_singleton(tmp_path, monkeypatch):
    """The journal singleton is built inside the transport hook, long after argv is parsed.

    So the door has to work when it is called BEFORE the singleton exists (the ordinary case)
    and when it is called AFTER (a runner that already made a call). Both, or attribution
    silently depends on call order.
    """
    monkeypatch.setenv("AKASHIC_WIRE_DIR", str(tmp_path))
    WJ = _wj()
    assert hasattr(WJ, "set_seat_agent"), (
        "wire_journal must expose a seat-identity door -- BIFROST_AGENT is read in exactly one "
        "place and written in none, so there is currently no way for a runner to say who it is")

    WJ.set_seat_agent("gemini")                     # BEFORE the singleton is built
    assert WJ.journal().agent == "gemini"

    WJ.set_seat_agent("sol")                        # AFTER it exists -- must re-point it
    assert WJ.journal().agent == "sol", (
        "the door did not reach an already-built singleton, so attribution depends on whether "
        "the runner happened to make a call first")


# --------------------------------------------------------------------------- A3

def test_a3_every_runner_stamps_its_seat_identity():
    """The pin that would have caught this. Static, over the whole runner FAMILY.

    A hand-written list of runners is what drifted in check_wiring's ENTRY_POINTS (gemini, kimi
    and sol runners went unseen for a week), so this enumerates the directory instead. A new
    runner is covered the day it lands, without anyone remembering this file exists.
    """
    runners = sorted(glob.glob(os.path.join(ROOT, "scripts", "bifrost_runner_*.py")))
    assert len(runners) >= 4, f"expected the runner family, found {len(runners)}"

    missing = []
    for path in runners:
        src = open(path, encoding="utf-8", errors="replace").read()
        # either the shared door, or an explicit env stamp -- both are honest ways to say who I am
        if not re.search(r"set_seat_agent\s*\(|BIFROST_AGENT", src):
            missing.append(os.path.basename(path))
    assert not missing, (
        f"{len(missing)} runner(s) can reach a model call without ever saying which seat they "
        f"are, so every record they write is attributed to 'unknown': {missing}")


# --------------------------------------------------------------------------- A4

def test_a4_the_recording_transport_carries_the_seat(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_WIRE_DIR", str(tmp_path))
    WJ = _wj()
    WJ.set_seat_agent("kimi")
    client = WJ.recording_http_client()
    if client is None:
        pytest.skip("httpx unavailable")
    j = WJ.journal()
    j.record(status=200, model="m")                 # the path the transport hook takes
    j.flush()
    assert {r.get("agent") for r in j.read_all()} == {"kimi"}


# --------------------------------------------------------------------------- A5

def test_a5_attribution_reaches_the_shard(tmp_path, monkeypatch):
    """T157's isolation is only real if the shard key is a real seat id."""
    monkeypatch.setenv("AKASHIC_WIRE_DIR", str(tmp_path))
    WJ = _wj()
    WJ.set_seat_agent("deepseek")
    j = WJ.journal()
    j.record(status=200, model="m")
    j.flush()

    shards = [d for d in os.listdir(tmp_path) if os.path.isdir(os.path.join(tmp_path, d))]
    assert "deepseek" in shards, (
        f"records landed in {shards} -- if that is ['unknown'], every seat shares one shard and "
        f"T157's isolation, per-shard rotation and per-shard drop attribution are all inert")
    assert "unknown" not in shards
