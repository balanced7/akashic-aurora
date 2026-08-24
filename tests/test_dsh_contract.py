"""t383 F4 capture-pair contract -- the test the post-seal review says is OWED.

Pinned against the FIRST REAL DSH payload captures (tests/fixtures/dsh_payloads/,
captured 2026-08-24 by the live plugin). The law under test, verbatim from the
post-seal notes: "the impression join is byte-for-byte preserved (session_key on
both sides; single normalize_target derivation)".

The join survives only if the target the SURFACE door writes (actions.recall_block
normalizes path/command internally via core.recall.at_action.normalize_target) is the
SAME string the RESOLVE door looks up (bridge.cmd_outcome_credit). The 2026-08-24 live
drill found the wired plugin violating this: its JS pre-joined `path | command` and
passed it as --target, while normalize_target emits p:<abspath> / c:<lowercased
command> -- so flips could never credit. This file pins the fixed contract.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

from agent.harness.dsh_plugin import bridge
from core.recall.at_action import normalize_target

FIXDIR = Path(__file__).parent / "fixtures" / "dsh_payloads"
REPO = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((FIXDIR / name).read_text(encoding="utf-8"))


def test_fixture_pins_real_dsh_posttooluse_shape():
    """The pinned payload is the shape the plugin ACTUALLY emits (not an assumption)."""
    rec = _load("dsh_posttooluse_pwsh.json")
    assert rec["kind"] == "post-execute"
    assert rec["tool"] == "pwsh"
    assert rec["argKeys"] == ["command", "description"]
    assert rec["isError"] is False


def test_capture_pair_target_join_law():
    """Surface and resolve must derive the byte-identical target from the same
    (path, command) pair that produced a real capture."""
    pair = _load("dsh_capture_pair_pwsh.json")
    assert pair["session_key"] == "dsh_agent"  # session_key on BOTH sides, constant
    for case in pair["cases"]:
        surface = normalize_target(case.get("path"), case.get("command"))
        outcome = bridge.derive_target(case.get("path"), case.get("command"), None)
        assert outcome == surface, (
            f"join evaporates: surface={surface!r} outcome={outcome!r} for {case}")


def test_outcome_door_derives_from_path_command_over_stale_target():
    """--target is only an already-normalized override; path/command win (V27)."""
    a = argparse.Namespace(target="stale | joined", path="E:\\AI-Setup\\docs\\WISHLIST.md",
                           command=None, session_key="dsh_agent", seen_key="s", success=1)
    assert bridge.derive_target(a.path, a.command, a.target) == normalize_target(
        "E:\\AI-Setup\\docs\\WISHLIST.md", None)


def test_outcome_argparse_accepts_path_command():
    """The resolve door must ACCEPT --path/--command (the fixed wiring shape)."""
    a = argparse.Namespace()
    bridge._build_outcome_parser().parse_args(
        ["--session-key", "dsh_agent", "--path", "E:\\AI-Setup\\docs\\WISHLIST.md",
         "--command", "py agent_cli.py status", "--success", "1"], namespace=a)
    assert a.path == "E:\\AI-Setup\\docs\\WISHLIST.md"
    assert a.command == "py agent_cli.py status"
    assert a.target is None


def test_plugin_wiring_pins_path_command_not_joined_target():
    """Static seam pin: the plugin must send --path/--command to outcome-credit,
    never a pre-joined --target (the shape that broke the join on 2026-08-24)."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "['--target', target]" not in src
    assert "'--path', path" in src and "'--command', command" in src


# --- T6 DSH session-end shim (auto-handoff flagship, 2026-08-24) ---

def test_dsh_parse_calls_pairs_real_session_records():
    """parse_dsh_calls pairs the REAL tool/call <-> tool/result shapes (callId rides
    message.source.callId) and reads the REAL failure marker (data.error). Pinned
    against verbatim records from session-1266b57c's log."""
    calls, truncated = bridge.parse_dsh_calls(str(FIXDIR / "dsh_session_sample.jsonl"))
    assert truncated is False
    assert sorted(c["tool"] for c in calls) == ["pwsh", "read"]
    read = next(c for c in calls if c["tool"] == "read")
    pwsh = next(c for c in calls if c["tool"] == "pwsh")
    assert read["target"] == normalize_target("E:\\AI-Setup\\.env", None)
    assert pwsh["target"].startswith("c:")   # command target, surface-shaped
    assert read["ok"] is False               # the data.error record
    assert pwsh["ok"] is True
    assert all("at" in c and "target" in c for c in calls)


def test_dsh_session_log_location_matches_real_layout():
    """The shim must find the session log under the REAL layout:
    $DSH_HOME/sessions/<workspace-slug>/session-<id>/session.jsonl.zstd."""
    with tempfile.TemporaryDirectory() as home:
        sid = "session-1266b57c-82cc-4ac2-ad45-d3d44549bfc7"
        d = Path(home) / "sessions" / "--E-AI-Setup--" / sid
        d.mkdir(parents=True)
        log = d / "session.jsonl.zstd"
        log.write_bytes(b"x")
        assert bridge.locate_dsh_session_log(home, sid) == str(log)


def test_presence_offline_declares_departure_not_a_beat():
    """The presence door's offline phase must call go_offline -- a declared departure
    that renders OFFLINE in the roster -- never heartbeat the key alive (the old
    placeholder defect that kept ended sessions rendering LIVE)."""
    import uuid
    ns = "t383pre" + uuid.uuid4().hex[:6]
    old = os.environ.get("BIFROST_NAMESPACE")
    os.environ["BIFROST_NAMESPACE"] = ns
    try:
        a = argparse.Namespace(phase="offline", session_id="seat-0001")
        assert bridge.cmd_presence(a) == 0
        from core.comm import roster
        rows = roster.roster(ns)
        mine = [r for r in rows if r.get("seat") == "dsh_agent#seat-000"]
        assert mine and mine[0]["state"] == "OFFLINE", (
            f"presence offline must render OFFLINE via go_offline: {mine}")
        assert not [r for r in rows if r.get("state") == "LIVE"], (
            f"an offline declaration must not leave a LIVE row behind: {rows}")
    finally:
        if old is None:
            os.environ.pop("BIFROST_NAMESPACE", None)
        else:
            os.environ["BIFROST_NAMESPACE"] = old
