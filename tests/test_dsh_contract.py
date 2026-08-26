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


def test_plugin_pins_generation_freshness_probe():
    """The stale-generation guard (Vandor's ask, 2026-08-24): the JS module captures
    its own mtime at FIRST import (module scope -- survives the ESM cache) and
    re-stats inside apply() (which RE-EXECUTES on entry restart), so disk-newer-than-
    loaded is LOUD with a named remedy, never silent. The bug becomes its own detector."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "LOADED_MTIME" in src
    assert "statSync(fileURLToPath(import.meta.url))" in src   # module-scope stamp
    assert "restart the server" in src                        # remedy, named for foreign readers
    assert "freshness-drift" in src                           # durable capture, not console-only


# --- T3 injection contract (the one-beat-late delivery seam, 2026-08-24) ---

def test_t3_injection_rides_decision_additional_contexts():
    """The injection seam, pinned against the harness contract: PostToolDecision.
    additionalContexts?: UserMessage[] (dsh-tool-cordis types), ferried onto the result
    by dsh-tools postExecute, consumed by dsh-agent-loop:183 into the active batch --
    the model's NEXT step. attachContext must append to THAT field, never a sibling."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "additionalContexts" in src
    assert "decision.additionalContexts" in src               # the field, not a sibling
    assert "return { ...decision, additionalContexts" in src  # enrich, never replace
    assert "attachContext(decision" in src                   # both post-execute branches use it


def test_t3_injection_message_shape_is_user_contract():
    """The context item must satisfy the dsh-llm message contract (id + role + content
    + source) with a first-class source slot: kind 'plugin', form 'recall' (the source
    vocabulary's own slot for lifted material). A malformed source crashes the ferry."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "role: 'user'" in src
    assert "content: [{ type: 'text', text }]" in src
    assert "kind: 'plugin'" in src and "form: 'recall'" in src
    assert "id:" in src and "akashic-" in src                # id + stable prefix


# --- MCP door tools (the typed-tools finish, 2026-08-24) ---

def test_plugin_hosts_persistent_mcp_door():
    """The typed-tools design: ONE persistent `py ai_setup_mcp.py` child + runtime
    tools/list schemas + ctx.tools.register -- the seat stops shelling per verb, and
    the door's contract is never hardcoded (no drift)."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "ai_setup_mcp.py" in src
    assert "tools/list" in src
    assert "ctx.tools.register" in src
    assert "defineTool" in src
    assert "export const inject = ['tools']" in src          # satisfiable in the web bundle
    assert "doorHandshake" in src


def test_door_verbs_never_spawn_per_call():
    """Door tools must ride the persistent child (doorCall), never a per-call py spawn
    (spawnBridge) -- the spawn-per-verb pathology this slice retires. The event-driven
    bridge subcommands (presence/whisper/recall/credit/session-end) keep spawnBridge."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "doorCall" in src
    door_block = src.split("MCP DOOR CLIENT", 1)[-1].split("export const name", 1)[0]
    assert "spawnBridge" not in door_block, (
        "a door verb must never spawn per call -- that is the pathology being retired")


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


# --- draft keepalive (Stop-hook + DSH turn-seam wiring, RED 2026-08-26) ---

def test_bridge_exposes_draft_keepalive_subcommand():
    """The bridge must ACCEPT `draft-keepalive` -- the DSH analog of the Stop-hook
    keepalive: a turn-boundary call that refreshes a stale
    chronicles/last-session-draft.md so a hard-killed host leaves a fresh draft."""
    a = argparse.Namespace()
    bridge._build_draft_keepalive_parser().parse_args(["draft-keepalive"], namespace=a)
    assert a.cmd == "draft-keepalive"


def test_draft_keepalive_door_answers_the_shape_and_dies_on_the_kill_switch(monkeypatch):
    """The keepalive door must return the documented shape ({wrote, reason}) and the
    kill switch must stop it BEFORE any draft is touched (the fleet-wide safety latch
    that keeps a defect from rewriting drafts on every turn of every seat)."""
    monkeypatch.setenv("AKASHIC_DRAFT_KEEPALIVE", "0")
    out = bridge._keepalive_run()
    assert out.get("wrote") is False
    assert "disabled" in out.get("reason", "")


def test_plugin_wires_draft_keepalive_on_post_execute_fire_and_forget():
    """The DSH turn seam: tools/post-execute fires draft-keepalive fire-and-forget
    (await_ false -- a keepalive must never block or alter a settled tool result,
    same fail-open law as every other bridge call in the listener)."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "'draft-keepalive'" in src
    assert "await_: false" in src


# --- door self-heal (persistent MCP child respawn, RED 2026-08-26) ---

def test_door_child_respawns_after_exit_with_backoff():
    """A long-lived door child of a long-lived host must not make the host's tools
    die with it (Vandor's reboot receipt: a 21h-old child served yesterday's server
    code because nothing noticed). On exit the plugin must attempt a respawn with
    backoff and a hard attempt cap -- a tight respawn loop wedges the host, and no
    respawn at all wedges the seat's hands."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "'door-exit'" in src                  # the exit observation exists
    assert "door-respawn" in src                 # the respawn attempt is captured, never silent
    assert "RESPAWN_MAX" in src                  # a hard cap -- the loop-guard law
    assert "registerDoorTools" in src            # re-registration after a fresh handshake


def test_door_respawn_exhaustion_is_loud_not_silent():
    """When the cap is reached, the seat must be TOLD (a captured, greppable record)
    -- a dead door that pretends it might still answer is the exact silence class this
    whole file exists to retire."""
    src = (REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js").read_text(encoding="utf-8")
    assert "respawn-exhausted" in src


def test_presence_offline_declares_departure_not_a_beat():
    """The presence door's offline phase must call go_offline -- a declared departure
    that renders OFFLINE in the roster -- never heartbeat the key alive (the old
    placeholder defect that kept ended sessions rendering LIVE)."""
    import uuid
    ns = "t383pre" + uuid.uuid4().hex[:6]
    old = os.environ.get("BIFROST_NAMESPACE")
    old_agent = os.environ.get("AKASHIC_AGENT_ID")
    os.environ["BIFROST_NAMESPACE"] = ns
    os.environ["AKASHIC_AGENT_ID"] = "dsh_agent"   # pin the seat id: the door reads
    # ambient env, and a runner's own id must not silently re-target the pin (T069 class)
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
        if old_agent is None:
            os.environ.pop("AKASHIC_AGENT_ID", None)
        else:
            os.environ["AKASHIC_AGENT_ID"] = old_agent
