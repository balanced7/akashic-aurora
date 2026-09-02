"""Codex App Server ownership and Bifrost wake contract pins.

Hermetic by default: the App Server tests launch a tiny newline-JSON fixture,
and the wake tests use a fake Redis client.  No Codex model turn, canonical
mailbox cursor, or peer process is touched.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

from agent.harness.codex_app_server import (
    CodexAppServer,
    CodexAppServerError,
    ThreadHandle,
    TurnResult,
)
from agent.harness.codex_bifrost_wake import (
    AURORA_COMBO_CATALOG_TOOL_NAME,
    AURORA_READ_VERB_TOOL,
    CodexBifrostWake,
    SubjectIdentity,
    WakeError,
    WakePolicy,
    WakeState,
    build_wake_prompt,
    decode_exact_message,
)
from core.comm import packet_spec
from core.comm.bus import Bus
from core.toolbelt.registry import Toolbelt


FAKE_SERVER = r"""
import json
from pathlib import Path
import sys

log_path = Path(sys.argv[1])
pending_reverse = []

def emit(value):
    print(json.dumps(value, separators=(",", ":")), flush=True)

for line in sys.stdin:
    message = json.loads(line)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(message, sort_keys=True) + "\n")
    method = message.get("method")
    if method == "initialize":
        emit({"id": message["id"], "result": {"userAgent": "fixture"}})
    elif method == "thread/start":
        emit({"method": "thread/started", "params": {"thread": {"id": "thread-fixture"}}})
        emit({"id": message["id"], "result": {"thread": {"id": "thread-fixture"}}})
    elif method == "thread/fork":
        source_id = message["params"]["threadId"]
        thread = {"id": "thread-forked", "forkedFromId": source_id}
        emit({"method": "thread/started", "params": {"thread": thread}})
        emit({"id": message["id"], "result": {"thread": thread}})
    elif method == "thread/resume":
        thread_id = message["params"]["threadId"]
        emit({"method": "thread/started", "params": {"thread": {"id": thread_id}}})
        emit({"id": message["id"], "result": {"thread": {"id": thread_id}}})
    elif method == "turn/start":
        emit({"id": message["id"], "result": {"turn": {"id": "turn-fixture"}}})
        emit({"method": "item/completed", "params": {
            "threadId": "thread-fixture", "turnId": "turn-fixture", "completedAtMs": 1,
            "item": {"id": "item-fixture", "type": "agentMessage", "text": "fixture reply"}}})
        emit({"method": "thread/tokenUsage/updated", "params": {
            "threadId": "thread-fixture", "turnId": "turn-fixture",
            "tokenUsage": {"last": {"inputTokens": 11, "cachedInputTokens": 3,
                "outputTokens": 5, "reasoningOutputTokens": 2, "totalTokens": 16,
                "cacheWriteInputTokens": 0},
                "total": {"inputTokens": 11, "cachedInputTokens": 3,
                "outputTokens": 5, "reasoningOutputTokens": 2, "totalTokens": 16,
                "cacheWriteInputTokens": 0}}}})
        emit({"method": "turn/completed", "params": {"threadId": "thread-fixture",
            "turn": {"id": "turn-fixture", "status": "completed"}}})
    elif method == "reverse":
        pending_reverse.append(message)
        if len(pending_reverse) == 2:
            for item in reversed(pending_reverse):
                emit({"id": item["id"], "result": item["params"]})
"""


FAKE_DYNAMIC_TOOL_SERVER = r"""
import json
from pathlib import Path
import sys

log_path = Path(sys.argv[1])
thread_id = "thread-dynamic-fixture"
turn_id = "turn-dynamic-fixture"

def emit(value):
    print(json.dumps(value, separators=(",", ":")), flush=True)

for line in sys.stdin:
    message = json.loads(line)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(message, sort_keys=True) + "\n")
    method = message.get("method")
    if method == "initialize":
        emit({"id": message["id"], "result": {"userAgent": "dynamic-fixture"}})
    elif method == "thread/start":
        emit({"id": message["id"], "result": {"thread": {"id": thread_id}}})
    elif method == "turn/start":
        emit({"id": message["id"], "result": {"turn": {"id": turn_id}}})
        emit({"id": "reverse-tool-1", "method": "item/tool/call", "params": {
            "arguments": {"verb": "discover", "args": []},
            "callId": "call-fixture", "threadId": thread_id,
            "tool": "aurora_read_verb", "turnId": turn_id}})
    elif message.get("id") == "reverse-tool-1" and "result" in message:
        result = message["result"]
        text = result["contentItems"][0]["text"]
        emit({"method": "item/completed", "params": {
            "threadId": thread_id, "turnId": turn_id, "completedAtMs": 1,
            "item": {"id": "item-fixture", "type": "agentMessage", "text": text}}})
        emit({"method": "turn/completed", "params": {"threadId": thread_id,
            "turn": {"id": turn_id, "status": "completed"}}})
"""


def _command(tmp_path: Path) -> tuple[list[str], Path]:
    log = tmp_path / "fixture-requests.jsonl"
    return [sys.executable, "-u", "-c", FAKE_SERVER, str(log)], log


def test_owned_stdio_host_initializes_and_thread_start_spends_no_turn(tmp_path):
    command, log = _command(tmp_path)
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        thread = server.start_thread(ephemeral=True, sandbox="read-only")
        assert thread.thread_id == "thread-fixture"
        assert server.stdout_reader_starts == 1

    methods = [json.loads(line).get("method") for line in log.read_text(encoding="utf-8").splitlines()]
    assert methods[:3] == ["initialize", "initialized", "thread/start"]
    assert "turn/start" not in methods


def test_owned_stdio_host_resumes_recorded_thread_without_starting_or_spending_a_turn(tmp_path):
    command, log = _command(tmp_path)
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        thread = server.resume_thread(
            "thread-persisted",
            sandbox="read-only",
            approval_policy="never",
            personality="friendly",
        )
        assert thread.thread_id == "thread-persisted"

    traffic = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    methods = [item.get("method") for item in traffic]
    assert methods[:3] == ["initialize", "initialized", "thread/resume"]
    assert "thread/start" not in methods
    assert "turn/start" not in methods
    resume = next(item for item in traffic if item.get("method") == "thread/resume")
    assert resume["params"]["threadId"] == "thread-persisted"
    assert resume["params"]["sandbox"] == "read-only"
    assert resume["params"]["approvalPolicy"] == "never"


def test_owned_stdio_host_forks_stored_history_without_resuming_or_spending_a_turn(tmp_path):
    command, log = _command(tmp_path)
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        thread = server.fork_thread("thread-source", ephemeral=False)
        assert thread.thread_id == "thread-forked"
        assert thread.raw["thread"]["forkedFromId"] == "thread-source"

    traffic = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    methods = [item.get("method") for item in traffic]
    assert methods[:3] == ["initialize", "initialized", "thread/fork"]
    assert "thread/resume" not in methods
    assert "turn/start" not in methods
    fork = next(item for item in traffic if item.get("method") == "thread/fork")
    assert fork["params"] == {"threadId": "thread-source", "ephemeral": False}


def test_one_stdout_reader_demultiplexes_out_of_order_responses(tmp_path):
    command, _log = _command(tmp_path)
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        results: dict[str, dict] = {}

        def call(value: str) -> None:
            results[value] = server.request("reverse", {"value": value})

        a = threading.Thread(target=call, args=("a",))
        b = threading.Thread(target=call, args=("b",))
        a.start()
        b.start()
        a.join(timeout=5)
        b.join(timeout=5)
        assert results == {"a": {"value": "a"}, "b": {"value": "b"}}
        assert server.stdout_reader_starts == 1


def test_turn_result_joins_final_text_status_and_usage(tmp_path):
    command, _log = _command(tmp_path)
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        thread = server.start_thread(ephemeral=True, sandbox="read-only")
        result = server.run_turn(thread.thread_id, "hello", effort="low", timeout=5)
    assert result.turn_id == "turn-fixture"
    assert result.status == "completed"
    assert result.text == "fixture reply"
    assert result.token_usage["last"]["totalTokens"] == 16


def test_dynamic_tool_reverse_request_is_answered_without_blocking_stdout_reader(tmp_path):
    """RED: the host must answer server requests, not misfile them as notifications."""
    log = tmp_path / "dynamic-fixture-requests.jsonl"
    command = [sys.executable, "-u", "-c", FAKE_DYNAMIC_TOOL_SERVER, str(log)]
    seen = []

    def handle_tool(params):
        seen.append(params)
        return {
            "success": True,
            "contentItems": [{"type": "inputText", "text": "governed verb output"}],
        }

    spec = {
        "type": "function",
        "name": "aurora_read_verb",
        "description": "fixture",
        "inputSchema": {"type": "object"},
    }
    with CodexAppServer(
        command=command,
        cwd=tmp_path,
        request_handlers={"item/tool/call": handle_tool},
        experimental_api=True,
    ) as server:
        thread = server.start_thread(dynamic_tools=[spec])
        result = server.run_turn(thread.thread_id, "use the tool", timeout=5)

    assert result.status == "completed"
    assert result.text == "governed verb output"
    assert seen and seen[0]["tool"] == "aurora_read_verb"
    traffic = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    initialize = next(item for item in traffic if item.get("method") == "initialize")
    assert initialize["params"]["capabilities"] == {"experimentalApi": True}
    thread_start = next(item for item in traffic if item.get("method") == "thread/start")
    assert thread_start["params"]["dynamicTools"] == [spec]
    reverse_reply = next(item for item in traffic if item.get("id") == "reverse-tool-1")
    assert reverse_reply["result"]["success"] is True


def test_dynamic_tools_require_explicit_experimental_api_negotiation(tmp_path):
    command, log = _command(tmp_path)
    spec = {
        "type": "function",
        "name": "aurora_read_verb",
        "description": "fixture",
        "inputSchema": {"type": "object"},
    }
    with CodexAppServer(command=command, cwd=tmp_path) as server:
        with pytest.raises(CodexAppServerError, match="experimental_api=True"):
            server.start_thread(dynamic_tools=[spec])

    traffic = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert not any(item.get("method") == "thread/start" for item in traffic)


def test_wake_exec_is_double_gated_and_dynamic_tool_input_is_structured(tmp_path, monkeypatch):
    """RED: launch opt-in and the live ACL both matter; raw shell is never exposed."""
    from core.trust.capabilities import Cap
    from core.trust import registry

    class Grant:
        role = "member"

        def __init__(self, exec_allowed):
            self.exec_allowed = exec_allowed

        def has(self, cap):
            return self.exec_allowed and cap == Cap.EXEC

    redis = IdleRedis()
    bus = Bus("sol", client=redis, promote=False)
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy("sol", frozenset({"daniil"})),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=Path(__file__).resolve().parent.parent,
        allow_exec=True,
        server_factory=lambda **_kwargs: None,
        toolbelt_factory=lambda agent: Toolbelt(
            agent,
            root=str(tmp_path / "empty-belts"),
            known_verbs=lambda: set(),
        ),
    )

    assert [tool["name"] for tool in watcher.dynamic_tools] == [
        AURORA_READ_VERB_TOOL["name"],
        AURORA_COMBO_CATALOG_TOOL_NAME,
    ]
    assert watcher._toolbox.agent_id == "sol"
    assert watcher._toolbox.allow_exec is True and watcher._toolbox.trust is True
    assert "command" not in AURORA_READ_VERB_TOOL["inputSchema"]["properties"]
    advertised_verbs = set(
        AURORA_READ_VERB_TOOL["inputSchema"]["properties"]["verb"]["enum"]
    )
    assert {"task", "fence", "notes"}.isdisjoint(advertised_verbs)

    monkeypatch.setattr(registry, "resolve", lambda _agent: Grant(False))
    denied = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_verb",
        "arguments": {"verb": "discover", "args": []},
    })
    assert denied["success"] is False
    assert "does not hold the exec capability" in denied["contentItems"][0]["text"]

    monkeypatch.setattr(registry, "resolve", lambda _agent: Grant(True))
    refused_mutation = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_verb",
        "arguments": {"verb": "learn", "args": ["sol"]},
    })
    assert refused_mutation["success"] is False
    assert "safe read grammar" in refused_mutation["contentItems"][0]["text"].lower()

    # ToolBox's legacy family-level allowlist currently accepts these positional
    # mutation forms.  The Codex bridge must reject them before that shared wall.
    for verb, args in (
        ("task", ["done", "T999"]),
        ("fence", ["open", "fixture", "--question", "unsafe"]),
        ("notes", ["--project"]),
        ("doctor", ["--page"]),
        ("discover", ["--semantic", "who am I"]),
    ):
        refused = watcher.handle_dynamic_tool_call({
            "tool": "aurora_read_verb",
            "arguments": {"verb": verb, "args": args},
        })
        assert refused["success"] is False
        assert "safe read grammar" in refused["contentItems"][0]["text"].lower()

    refused_shell = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_verb",
        "arguments": {"verb": "discover", "args": ["verbs; whoami"]},
    })
    assert refused_shell["success"] is False
    assert "shell metacharacters" in refused_shell["contentItems"][0]["text"].lower()

    commands = []
    monkeypatch.setattr(
        watcher._toolbox,
        "run_command",
        lambda command, timeout: commands.append((command, timeout)) or "governed output",
    )
    allowed = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_verb",
        "arguments": {"verb": "discover", "args": ["verbs"]},
    })
    assert allowed["success"] is True
    assert allowed["contentItems"][0]["text"] == "governed output"
    assert commands == [("py agent_cli.py discover verbs", 120)]


def test_wake_exec_advertises_only_safe_subject_combos_and_preflights_every_step(
    tmp_path, monkeypatch
):
    """RED: native sugar crosses the bridge only after whole-combo read preflight."""
    from core.trust.capabilities import Cap
    from core.trust import registry

    class Grant:
        role = "member"

        def has(self, cap):
            return cap == Cap.EXEC

    belt_root = tmp_path / "belts"
    known_verbs = lambda: {"triage", "doctor", "locks", "lookback", "learn"}
    belt = Toolbelt("sol", root=str(belt_root), known_verbs=known_verbs)
    belt.mint(
        "pressure",
        [["triage"], ["doctor"], ["locks"]],
        why="Where does it hurt right now?",
        family="SENTINELS",
    )
    belt.mint(
        "late-mutation",
        [["doctor"], ["learn", "sol"]],
        why="Proves that a later unsafe step prevents every earlier step.",
        family="WAR-GAMES",
    )
    belt.mint(
        "late-shell",
        [["doctor"], ["lookback", "risk; whoami"]],
        why="Proves shell syntax is rejected during whole-combo preflight.",
        family="WAR-GAMES",
    )

    redis = IdleRedis()
    watcher = CodexBifrostWake(
        bus=Bus("sol", client=redis, promote=False),
        policy=WakePolicy("sol", frozenset({"daniil"})),
        state=WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0"),
        log_path=tmp_path / "events.jsonl",
        cwd=Path(__file__).resolve().parent.parent,
        allow_exec=True,
        server_factory=lambda **_kwargs: None,
        toolbelt_factory=lambda agent: Toolbelt(
            agent,
            root=str(belt_root),
            known_verbs=known_verbs,
        ),
    )
    monkeypatch.setattr(registry, "resolve", lambda _agent: Grant())

    combo_tool = next(tool for tool in watcher.dynamic_tools if tool["name"] == "aurora_read_combo")
    assert combo_tool["inputSchema"]["properties"]["name"]["enum"] == ["pressure"]
    assert "args" not in combo_tool["inputSchema"]["properties"]

    monkeypatch.setattr(
        watcher._toolbox,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("combo admission catalog must not execute"),
    )
    catalog = watcher.handle_dynamic_tool_call({
        "tool": AURORA_COMBO_CATALOG_TOOL_NAME,
        "arguments": {},
    })
    catalog_body = catalog["contentItems"][0]["text"]
    assert catalog["success"] is True
    assert "pressure" in catalog_body and "ADMITTED" in catalog_body
    assert "late-mutation" in catalog_body and "OMITTED" in catalog_body
    assert "learn" in catalog_body and "safe read grammar" in catalog_body
    assert "late-shell" in catalog_body and "shell metacharacters" in catalog_body
    peer_probe = watcher.handle_dynamic_tool_call({
        "tool": AURORA_COMBO_CATALOG_TOOL_NAME,
        "arguments": {"agent": "deepseek"},
    })
    assert peer_probe["success"] is False
    assert "accepts no arguments" in peer_probe["contentItems"][0]["text"]

    commands = []
    monkeypatch.setattr(
        watcher._toolbox,
        "run_command",
        lambda command, timeout: commands.append((command, timeout)) or f"output:{command}",
    )
    result = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_combo",
        "arguments": {"name": "pressure"},
    })
    assert result["success"] is True
    assert commands == [
        ("py agent_cli.py triage", 120),
        ("py agent_cli.py doctor", 120),
        ("py agent_cli.py locks", 120),
    ]
    assert "[pressure 1/3] triage" in result["contentItems"][0]["text"]
    assert "[pressure 3/3] locks" in result["contentItems"][0]["text"]

    monkeypatch.setattr(
        watcher._toolbox,
        "run_command",
        lambda _command, timeout: "x" * 10_000,
    )
    capped = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_combo",
        "arguments": {"name": "pressure"},
    })
    capped_body = capped["contentItems"][0]["text"]
    assert capped["success"] is True
    assert len(capped_body) <= 24_000
    assert "combo output capped" in capped_body

    commands.clear()
    refused = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_combo",
        "arguments": {"name": "late-mutation"},
    })
    assert refused["success"] is False
    assert "safe read grammar" in refused["contentItems"][0]["text"].lower()
    assert commands == []

    refused_shell = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_combo",
        "arguments": {"name": "late-shell"},
    })
    assert refused_shell["success"] is False
    assert commands == []


def test_combo_admission_catalog_reports_registry_blindness_instead_of_clean_empty(tmp_path):
    def broken_belt(_agent):
        raise OSError("registry unreadable")

    watcher = CodexBifrostWake(
        bus=Bus("sol", client=IdleRedis(), promote=False),
        policy=WakePolicy("sol", frozenset({"daniil"})),
        state=WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0"),
        log_path=tmp_path / "events.jsonl",
        cwd=Path(__file__).resolve().parent.parent,
        allow_exec=True,
        server_factory=lambda **_kwargs: None,
        toolbelt_factory=broken_belt,
    )

    assert [tool["name"] for tool in watcher.dynamic_tools] == [
        AURORA_READ_VERB_TOOL["name"],
        AURORA_COMBO_CATALOG_TOOL_NAME,
    ]
    result = watcher.handle_dynamic_tool_call({
        "tool": AURORA_COMBO_CATALOG_TOOL_NAME,
        "arguments": {},
    })
    assert result["success"] is False
    assert "UNAVAILABLE" in result["contentItems"][0]["text"]
    assert "registry unreadable" in result["contentItems"][0]["text"]


def test_wake_without_launch_opt_in_advertises_no_exec_tool(tmp_path):
    redis = IdleRedis()
    bus = Bus("sol", client=redis, promote=False)
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy("sol", frozenset({"daniil"})),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        allow_exec=False,
        server_factory=lambda **_kwargs: None,
    )
    assert watcher.dynamic_tools == []
    denied = watcher.handle_dynamic_tool_call({
        "tool": "aurora_read_verb",
        "arguments": {"verb": "discover", "args": []},
    })
    assert denied["success"] is False
    assert "launch opt-in" in denied["contentItems"][0]["text"]


class ExactRedis:
    def __init__(self, mid: str, fields: dict):
        self.mid = mid
        self.fields = fields
        self.calls = []

    def xrange(self, key, min, max, count=None):
        self.calls.append((key, min, max, count))
        return [(self.mid, self.fields)] if min == self.mid and max == self.mid else []


def _message_fields(*, answers: str = "") -> dict:
    fields = {
        "frm": "dsh_agent",
        "to": "sol",
        "kind": "response",
        "content": json.dumps("Rill's answer"),
        "parts": "[]",
        "meta": json.dumps({"answers": answers}),
        "ts": "2026-08-26T00:00:00+00:00",
    }
    packet_spec.stamp(fields)
    return fields


def test_exact_wake_read_does_not_touch_shared_cursor():
    mid = "1787730405992-0"
    redis = ExactRedis(mid, _message_fields(answers="1787730404992-0"))
    bus = Bus("sol", client=redis, promote=False)
    message = decode_exact_message(bus, mid)
    assert message is not None and message.content == "Rill's answer"
    assert redis.calls == [("bifrost:inbox:sol", mid, mid, 1)]


def test_policy_allows_rill_requests_but_only_expected_responses():
    policy = WakePolicy(
        agent="sol",
        allowed_senders=frozenset({"dsh_agent"}),
        expected_answers=frozenset({"1787730404992-0"}),
    )
    expected = Bus("sol", client=ExactRedis("x", {}), promote=False)._to_msg(
        "1-0", _message_fields(answers="1787730404992-0")
    )
    unrelated = Bus("sol", client=ExactRedis("x", {}), promote=False)._to_msg(
        "2-0", _message_fields(answers="someone-elses-question")
    )
    request_fields = _message_fields()
    request_fields["kind"] = "request"
    packet_spec.stamp(request_fields)
    request = Bus("sol", client=ExactRedis("x", {}), promote=False)._to_msg("3-0", request_fields)

    assert policy.accepts(expected) is True
    assert policy.accepts(request) is True
    assert policy.accepts(unrelated) is False
    request.frm = "not-rill"
    assert policy.accepts(request) is False


def test_wake_prompt_is_subject_labelled_and_forbids_peer_interference():
    message = Bus("sol", client=ExactRedis("x", {}), promote=False)._to_msg(
        "1-0", _message_fields(answers="1787730404992-0")
    )
    prompt = build_wake_prompt(
        "sol",
        message,
        identity=SubjectIdentity(
            agent_id="sol",
            callsign=None,
            status="unregistered",
            authority="test-fixture",
        ),
    )
    assert "SUBJECT SEAT: sol" in prompt
    assert "dsh_agent" in prompt and "Rill's answer" in prompt
    assert "Do not manage, stop, relaunch, inspect, or mutate Rill's process" in prompt
    assert "Do not consume or advance any Bifrost mailbox cursor" in prompt


def test_ratified_wake_identity_comes_from_the_resident_registry(monkeypatch):
    """A ceremony must change the next admitted turn without editing wake prose."""
    from agent.harness.codex_bifrost_wake import (
        resolve_subject_identity,
        wake_developer_instructions,
    )
    from core.fleet import residents

    monkeypatch.setattr(
        residents,
        "get",
        lambda agent: {
            "agent_id": agent,
            "callsign": "Sunshine",
            "state": "ratified",
            "ratified_by": "daniil",
        },
    )
    message = Bus("sol", client=ExactRedis("x", {}), promote=False)._to_msg(
        "1-0", _message_fields(answers="1787730404992-0")
    )

    identity = resolve_subject_identity("sol")
    prompt = build_wake_prompt("sol", message, identity=identity)
    instructions = wake_developer_instructions("sol", identity)

    assert identity.callsign == "Sunshine"
    assert identity.status == "ratified"
    assert identity.authority == "resident-registry"
    assert "CALLSIGN: Sunshine" in prompt
    assert "CALLSIGN STATUS: ratified" in prompt
    assert "IDENTITY AUTHORITY: resident-registry" in prompt
    assert "currently unratified" not in prompt
    assert "historical and unratified" not in instructions
    assert "Sunshine" in instructions and "ratified" in instructions


def test_environment_cannot_self_promote_a_callsign_when_registry_is_absent(monkeypatch):
    """A stale launcher hint is context, never ratification authority."""
    from agent.harness.codex_bifrost_wake import resolve_subject_identity
    from core.fleet import residents

    monkeypatch.setattr(residents, "get", lambda _agent: None)
    monkeypatch.setenv("AKASHIC_CALLSIGN_HINT", "Sunshine")
    monkeypatch.setenv("AKASHIC_CALLSIGN_STATUS", "ratified")

    identity = resolve_subject_identity("sol")
    assert identity.callsign == "Sunshine"
    assert identity.status == "registry-mismatch"
    assert identity.authority == "environment-hint;resident-registry-absent"


def test_cached_app_server_restarts_when_the_registry_identity_changes(tmp_path):
    """A long-lived child must not retain the identity snapshot from before a ceremony."""
    from agent.harness.codex_bifrost_wake import SubjectIdentity

    class IdentityServer:
        def __init__(self, **kwargs):
            self.env = kwargs["env"]
            self.command = ["identity-fixture"]
            self.process = SimpleNamespace(pid=9000 + len(created))
            self.closed = False

        def start(self):
            return self

        def close(self):
            self.closed = True

    created = []

    def make_server(**kwargs):
        server = IdentityServer(**kwargs)
        created.append(server)
        return server

    redis = IdleRedis()
    bus = Bus("sol", client=redis, promote=False)
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy("sol", frozenset({"daniil"})),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        server_factory=make_server,
    )
    before = SubjectIdentity(
        agent_id="sol",
        callsign="Sunshine",
        status="historical-unratified",
        authority="environment-hint",
    )
    after = SubjectIdentity(
        agent_id="sol",
        callsign="Sunshine",
        status="ratified",
        authority="resident-registry",
    )

    first = watcher._app_server(before)
    assert watcher._app_server(before) is first
    second = watcher._app_server(after)

    assert len(created) == 2
    assert first.closed is True
    assert second is created[1]
    assert second.env["AKASHIC_CALLSIGN_HINT"] == "Sunshine"
    assert second.env["AKASHIC_CALLSIGN_STATUS"] == "ratified"
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "app_server_identity_refresh" in events


def test_private_watcher_state_baselines_and_deduplicates(tmp_path):
    path = tmp_path / "wake-state.json"
    state = WakeState.open(path, agent="sol", baseline="50-0")
    assert state.last_seen == "50-0"
    assert state.seen("51-0") is False
    state.record("51-0", outcome="ignored", detail="non-actionable")

    restored = WakeState.open(path, agent="sol", baseline="999-0")
    assert restored.last_seen == "51-0"
    assert restored.seen("51-0") is True
    assert restored.records[-1]["outcome"] == "ignored"


def test_private_watcher_state_persists_one_explicit_thread_binding_and_lineage(tmp_path):
    path = tmp_path / "wake-state.json"
    state = WakeState.open(
        path,
        agent="sol",
        baseline="50-0",
        thread_id="thread-discord",
        source_thread_id="thread-desktop",
        binding_kind="completed-history-fork",
    )
    assert state.thread_id == "thread-discord"
    assert state.source_thread_id == "thread-desktop"
    assert state.binding_kind == "completed-history-fork"

    restored = WakeState.open(path, agent="sol", baseline="999-0")
    assert restored.thread_id == "thread-discord"
    assert restored.source_thread_id == "thread-desktop"
    assert restored.binding_kind == "completed-history-fork"

    with pytest.raises(WakeError, match="refusing to replace"):
        WakeState.open(
            path,
            agent="sol",
            baseline="999-0",
            thread_id="thread-stranger",
        )


def test_corrupt_private_state_refuses_instead_of_skipping_to_a_new_tail(tmp_path):
    path = tmp_path / "wake-state.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(WakeError, match="refusing to reset"):
        WakeState.open(path, agent="sol", baseline="999-0")


class IdleRedis:
    def __init__(self):
        self.xread_calls = []

    def xread(self, streams, count, block):
        self.xread_calls.append((streams, count, block))
        return []

    def close(self):
        return None


def test_idle_level_watch_spends_no_app_server_or_model_turn(tmp_path):
    redis = IdleRedis()
    bus = Bus("sol", client=redis, promote=False)
    bus._blocking_client = lambda _block_ms: redis
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    created = []

    def forbidden_server(**_kwargs):
        created.append(True)
        raise AssertionError("idle watcher must not create an App Server")

    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy("sol", frozenset({"dsh_agent"})),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        block_ms=100,
        server_factory=forbidden_server,
    )
    assert watcher.run(once=True) == 0
    assert created == []
    assert redis.xread_calls == [({"bifrost:inbox:sol": "50-0"}, 10, 100)]
    assert state.last_seen == "50-0"


class TimeoutRedis(IdleRedis):
    def xread(self, streams, count, block):
        from redis.exceptions import TimeoutError as RedisTimeoutError

        self.xread_calls.append((streams, count, block))
        raise RedisTimeoutError("fixture timeout")


def test_blocking_redis_timeout_is_contained_without_a_model_turn(tmp_path):
    redis = TimeoutRedis()
    bus = Bus("sol", client=redis, promote=False)
    bus._blocking_client = lambda _block_ms: redis
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy("sol", frozenset({"dsh_agent"})),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        block_ms=5_000,
        server_factory=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("timeout must not create an App Server")
        ),
    )
    assert watcher.run(once=True) == 0
    assert state.last_seen == "50-0"
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "redis_wait_interrupted" in events
    assert '"model_turns": 0' in events


class FixtureAppServer:
    def __init__(self, **_kwargs):
        self.command = ["fixture-app-server"]
        self.process = SimpleNamespace(pid=4321)
        self.turns = 0
        self.starts = 0
        self.resumes = 0

    def start(self):
        return self

    def start_thread(self, **kwargs):
        self.starts += 1
        assert kwargs["ephemeral"] is False
        assert kwargs["sandbox"] == "read-only"
        assert kwargs["approval_policy"] == "never"
        return ThreadHandle("thread-wake", {"thread": {"id": "thread-wake"}})

    def resume_thread(self, thread_id, **kwargs):
        self.resumes += 1
        assert thread_id == "thread-wake"
        assert kwargs["sandbox"] == "read-only"
        assert kwargs["approval_policy"] == "never"
        return ThreadHandle(thread_id, {"thread": {"id": thread_id}})

    def run_turn(self, thread_id, prompt, **kwargs):
        self.turns += 1
        assert thread_id == "thread-wake"
        assert "SUBJECT SEAT: sol" in prompt
        assert kwargs["sandbox_policy"] == {"type": "readOnly", "networkAccess": False}
        return TurnResult(
            thread_id=thread_id,
            turn_id="turn-wake",
            status="completed",
            text="A bounded reply from Sol.",
            token_usage={
                "last": {
                    "inputTokens": 28,
                    "cachedInputTokens": 21,
                    "outputTokens": 3,
                    "totalTokens": 31,
                },
                "total": {
                    "inputTokens": 51,
                    "cachedInputTokens": 21,
                    "outputTokens": 6,
                    "totalTokens": 57,
                },
            },
            raw={},
        )

    def close(self):
        return None


def test_one_eligible_message_makes_one_turn_and_one_causally_linked_reply(tmp_path):
    mid = "60-0"
    redis = ExactRedis(mid, _message_fields(answers="1787730404992-0"))
    bus = Bus("sol", client=redis, promote=False)
    sends = []
    bus.send = lambda to, kind, content, meta: sends.append((to, kind, content, meta)) or "70-0"
    state = WakeState.open(tmp_path / "state.json", agent="sol", baseline="50-0")
    servers = []
    identity_reads = []

    def make_server(**kwargs):
        server = FixtureAppServer(**kwargs)
        servers.append(server)
        return server

    def resolve_identity(agent):
        identity_reads.append(agent)
        return SubjectIdentity(
            agent_id=agent,
            callsign="Sunshine",
            status="ratified",
            authority="resident-registry-fixture",
        )

    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy(
            "sol",
            frozenset({"dsh_agent"}),
            expected_answers=frozenset({"1787730404992-0"}),
        ),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        server_factory=make_server,
        identity_resolver=resolve_identity,
    )
    result = watcher.handle(mid, redis.fields)
    assert result == {"mid": mid, "outcome": "replied", "reply_mid": "70-0"}
    assert len(servers) == 1 and servers[0].turns == 1
    assert servers[0].starts == 1 and servers[0].resumes == 0
    assert state.thread_id == "thread-wake", "the first durable thread is bound before reuse"
    assert identity_reads == ["sol"], "one admitted turn gets exactly one identity snapshot"
    assert sends[0][:3] == ("dsh_agent", "reply", "A bounded reply from Sol.")
    assert sends[0][3]["answers"] == mid
    assert sends[0][3]["subject_seat"] == "sol"
    assert sends[0][3]["subject_callsign"] == "Sunshine"
    assert sends[0][3]["callsign_status"] == "ratified"
    assert state.seen(mid) is True
    accounting = state.records[-1]["usage_accounting"]
    assert accounting["accounting_basis"] == "turn_total"
    assert accounting["turn_total"]["totalTokens"] == 57
    assert accounting["final_model_step"]["totalTokens"] == 31
    assert accounting["multi_step"] is True

    events = [json.loads(line) for line in
              (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    replied = next(event for event in events if event.get("event") == "replied")
    assert replied["usage_accounting"] == accounting, (
        "the operational JSONL and private watermark must agree about which usage "
        "scope prices the whole admitted turn")

    assert watcher.handle(mid, redis.fields)["outcome"] == "duplicate"
    assert servers[0].turns == 1 and len(sends) == 1


def test_bound_watcher_resumes_the_same_thread_across_a_fresh_host(tmp_path):
    mid = "60-0"
    redis = ExactRedis(mid, _message_fields(answers="1787730404992-0"))
    bus = Bus("sol", client=redis, promote=False)
    sends = []
    bus.send = lambda to, kind, content, meta: sends.append((to, kind, content, meta)) or "70-0"
    state = WakeState.open(
        tmp_path / "state.json",
        agent="sol",
        baseline="50-0",
        thread_id="thread-wake",
        source_thread_id="thread-desktop",
        binding_kind="completed-history-fork",
    )
    servers = []

    def make_server(**kwargs):
        server = FixtureAppServer(**kwargs)
        servers.append(server)
        return server

    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy(
            "sol",
            frozenset({"dsh_agent"}),
            expected_answers=frozenset({"1787730404992-0"}),
        ),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        server_factory=make_server,
        identity_resolver=lambda agent: SubjectIdentity(
            agent_id=agent,
            callsign="Sunshine",
            status="ratified",
            authority="resident-registry-fixture",
        ),
    )

    result = watcher.handle(mid, redis.fields)
    assert result["outcome"] == "replied"
    assert servers[0].starts == 0 and servers[0].resumes == 1
    assert servers[0].turns == 1
    assert sends[0][3]["continuity_thread_id"] == "thread-wake"
    assert sends[0][3]["continuity_source_thread_id"] == "thread-desktop"
    assert sends[0][3]["continuity_binding"] == "completed-history-fork"


class ActiveWriterAppServer(FixtureAppServer):
    def resume_thread(self, thread_id, **kwargs):
        self.resumes += 1
        raise CodexAppServerError(
            f"App Server 'thread/resume' failed: thread {thread_id} already has an active writer"
        )


def test_active_writer_defers_without_advancing_watermark_or_sending_a_reply(tmp_path):
    mid = "60-0"
    redis = ExactRedis(mid, _message_fields(answers="1787730404992-0"))
    bus = Bus("sol", client=redis, promote=False)
    sends = []
    bus.send = lambda *args, **kwargs: sends.append((args, kwargs)) or "70-0"
    state = WakeState.open(
        tmp_path / "state.json",
        agent="sol",
        baseline="50-0",
        thread_id="thread-wake",
    )
    server = ActiveWriterAppServer()
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy(
            "sol",
            frozenset({"dsh_agent"}),
            expected_answers=frozenset({"1787730404992-0"}),
        ),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        server_factory=lambda **_kwargs: server,
        identity_resolver=lambda agent: SubjectIdentity(
            agent_id=agent,
            callsign="Sunshine",
            status="ratified",
            authority="resident-registry-fixture",
        ),
    )

    result = watcher.handle(mid, redis.fields)
    assert result == {"mid": mid, "outcome": "deferred_active_writer"}
    assert state.last_seen == "50-0"
    assert state.seen(mid) is False
    assert server.starts == 0 and server.resumes == 1 and server.turns == 0
    assert sends == []


class MissingThreadAppServer(FixtureAppServer):
    def resume_thread(self, thread_id, **kwargs):
        self.resumes += 1
        raise CodexAppServerError(
            f"App Server 'thread/resume' failed: thread {thread_id} not found"
        )


def test_missing_bound_thread_refuses_instead_of_silently_starting_a_stranger(tmp_path):
    mid = "60-0"
    redis = ExactRedis(mid, _message_fields(answers="1787730404992-0"))
    bus = Bus("sol", client=redis, promote=False)
    state = WakeState.open(
        tmp_path / "state.json",
        agent="sol",
        baseline="50-0",
        thread_id="thread-wake",
    )
    server = MissingThreadAppServer()
    watcher = CodexBifrostWake(
        bus=bus,
        policy=WakePolicy(
            "sol",
            frozenset({"dsh_agent"}),
            expected_answers=frozenset({"1787730404992-0"}),
        ),
        state=state,
        log_path=tmp_path / "events.jsonl",
        cwd=tmp_path,
        server_factory=lambda **_kwargs: server,
        identity_resolver=lambda agent: SubjectIdentity(
            agent_id=agent,
            callsign="Sunshine",
            status="ratified",
            authority="resident-registry-fixture",
        ),
    )

    result = watcher.handle(mid, redis.fields)
    assert result["outcome"] == "continuity_refused"
    assert state.last_seen == "50-0"
    assert state.seen(mid) is False
    assert server.starts == 0 and server.resumes == 1 and server.turns == 0
