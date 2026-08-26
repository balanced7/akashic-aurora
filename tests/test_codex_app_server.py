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

from agent.harness.codex_app_server import CodexAppServer, ThreadHandle, TurnResult
from agent.harness.codex_bifrost_wake import (
    CodexBifrostWake,
    WakeError,
    WakePolicy,
    WakeState,
    build_wake_prompt,
    decode_exact_message,
)
from core.comm import packet_spec
from core.comm.bus import Bus


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
    prompt = build_wake_prompt("sol", message)
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

    def start(self):
        return self

    def start_thread(self, **kwargs):
        assert kwargs["ephemeral"] is True
        assert kwargs["sandbox"] == "read-only"
        assert kwargs["approval_policy"] == "never"
        return ThreadHandle("thread-wake", {"thread": {"id": "thread-wake"}})

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
            token_usage={"last": {"totalTokens": 23}},
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
    )
    result = watcher.handle(mid, redis.fields)
    assert result == {"mid": mid, "outcome": "replied", "reply_mid": "70-0"}
    assert len(servers) == 1 and servers[0].turns == 1
    assert sends[0][:3] == ("dsh_agent", "reply", "A bounded reply from Sol.")
    assert sends[0][3]["answers"] == mid
    assert sends[0][3]["subject_seat"] == "sol"
    assert state.seen(mid) is True

    assert watcher.handle(mid, redis.fields)["outcome"] == "duplicate"
    assert servers[0].turns == 1 and len(sends) == 1
