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
