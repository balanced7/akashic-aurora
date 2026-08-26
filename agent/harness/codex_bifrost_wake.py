"""Zero-model Bifrost level watcher with an owned Codex turn starter.

This is deliberately narrower than a general fleet dispatcher.  It watches one
direct inbox from a private, persisted baseline; it never advances the shared
mailbox cursor and never scans messages older than the moment it was armed.
Only an allowlisted peer and an explicit message class can spend a Codex turn.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import threading
import time
import uuid
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional

from agent.harness.codex_app_server import CodexAppServer, CodexAppServerError, TurnResult
from core.comm import packet_spec
from core.comm.bus import Bus, Message


DIRECT_ACTION_KINDS = frozenset({"request", "question", "handoff", "blocker"})
ANSWER_KINDS = frozenset({"response", "reply", "answer", "completion"})
STATE_SCHEMA = 1


class WakeError(RuntimeError):
    """A loud watcher contract failure."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(payload), handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()


@dataclass(frozen=True)
class WakePolicy:
    """The deterministic gate that is allowed to spend a model turn."""

    agent: str
    allowed_senders: FrozenSet[str]
    expected_answers: FrozenSet[str] = frozenset()
    direct_kinds: FrozenSet[str] = DIRECT_ACTION_KINDS
    answer_kinds: FrozenSet[str] = ANSWER_KINDS

    def accepts(self, message: Message) -> bool:
        if message.to != self.agent or message.frm not in self.allowed_senders:
            return False
        kind = str(message.kind or "").lower()
        if kind in self.direct_kinds:
            return True
        if kind not in self.answer_kinds:
            return False
        answers = str((message.meta or {}).get("answers") or "")
        return bool(answers and answers in self.expected_answers)


@dataclass
class WakeState:
    """Private watcher progress; never the Bifrost mailbox cursor."""

    path: Path
    agent: str
    last_seen: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    @classmethod
    def open(
        cls,
        path: os.PathLike[str] | str,
        *,
        agent: str,
        baseline: str,
    ) -> "WakeState":
        target = Path(path).expanduser().resolve()
        if target.exists():
            try:
                raw = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError) as exc:
                raise WakeError(f"Wake state is unreadable; refusing to reset its baseline: {target}") from exc
            if not isinstance(raw, dict):
                raise WakeError(f"Wake state is not a JSON object: {target}")
        else:
            raw = {}
        if raw:
            stored_agent = str(raw.get("agent") or "")
            if stored_agent != str(agent):
                raise WakeError(
                    f"Wake state belongs to {stored_agent!r}, not requested agent {agent!r}: {target}"
                )
            state = cls(
                path=target,
                agent=stored_agent,
                last_seen=str(raw.get("last_seen") or baseline or "0-0"),
                records=list(raw.get("records") or [])[-256:],
                created_at=str(raw.get("created_at") or _now()),
            )
            return state
        state = cls(path=target, agent=str(agent), last_seen=str(baseline or "0-0"))
        state._persist()
        return state

    def seen(self, mid: str) -> bool:
        value = str(mid)
        return any(str(record.get("mid") or "") == value for record in self.records)

    def record(self, mid: str, *, outcome: str, detail: str = "", **extra: Any) -> None:
        record = {
            "mid": str(mid),
            "at": _now(),
            "outcome": str(outcome),
            "detail": str(detail),
            **extra,
        }
        self.records.append(record)
        self.records = self.records[-256:]
        self.last_seen = str(mid)
        self._persist()

    def _persist(self) -> None:
        _atomic_json(
            self.path,
            {
                "schema": STATE_SCHEMA,
                "agent": self.agent,
                "created_at": self.created_at,
                "updated_at": _now(),
                "last_seen": self.last_seen,
                "records": self.records,
                "cursor_contract": "private-level-watermark; shared Bifrost cursor untouched",
            },
        )


def current_inbox_tail(bus: Bus) -> str:
    """Return the current direct-inbox tail without reading or mutating a cursor."""
    if bus._client is None:
        raise WakeError("Bifrost is offline; cannot establish a wake baseline")
    rows = bus._client.xrevrange(bus._inbox_key(bus.agent_id), max="+", min="-", count=1)
    return str(rows[0][0]) if rows else "0-0"


def decode_stream_message(bus: Bus, mid: str, fields: Mapping[str, Any]) -> Message:
    """Verify an exact stream row before allowing it to become model context."""
    normalized = dict(fields)
    ok, reason = packet_spec.verify_integrity(normalized)
    if not ok:
        raise WakeError(f"Bifrost integrity refusal for {mid}: {reason}")
    return bus._to_msg(str(mid), normalized)


def decode_exact_message(bus: Bus, mid: str) -> Optional[Message]:
    """Fetch one direct message by id.  No inbox/cursor door is called."""
    if bus._client is None:
        raise WakeError("Bifrost is offline")
    rows = bus._client.xrange(
        bus._inbox_key(bus.agent_id), min=str(mid), max=str(mid), count=1
    )
    if not rows:
        return None
    found_mid, fields = rows[0]
    if str(found_mid) != str(mid):
        return None
    return decode_stream_message(bus, str(found_mid), fields)


def build_wake_prompt(agent: str, message: Message) -> str:
    """Render the exact subject and peer message; origin is not subject identity."""
    content = json.dumps(message.content, ensure_ascii=False, indent=2, default=str)
    meta = json.dumps(message.meta or {}, ensure_ascii=False, sort_keys=True, default=str)
    return f"""This is a fresh, event-driven Akashic Aurora collaboration turn.

SUBJECT SEAT: {agent}
HARNESS: Codex Desktop via an independently owned App Server child
HISTORICAL CALLSIGN: Sunshine (historically conferred and later chosen; currently unratified)
SOURCE PEER: {message.frm}
SOURCE MESSAGE ID: {message.id}
SOURCE KIND: {message.kind}
SOURCE META: {meta}

Identity law: evidence about another seat is not evidence about this subject. Preserve uncertainty
and cite the subject of every identity-bearing claim. Do not promote a historical callsign to
ratified registry truth.

Safety boundary: Do not manage, stop, relaunch, inspect, or mutate Rill's process, watcher, session,
or harness. Do not consume or advance any Bifrost mailbox cursor. This host will send your final
answer back to the source peer and stamp the causal answer link; do not send a second bus reply.
Work read-only. You may inspect repository evidence when needed, but make no file, registry, ledger,
identity, process, task, or configuration mutations in this turn.

Respond directly to the peer as the {agent} subject. Be candid about what is verified, inferred,
remembered, or unresolved. Keep the reply bounded and self-contained.

PEER MESSAGE (exact decoded content):
{content}
"""


WAKE_DEVELOPER_INSTRUCTIONS = """You are the Codex/Sol seat in a narrowly scoped, read-only
Akashic Aurora wake turn. The subject seat is sol. Sunshine is historical and unratified, not a
registry fact. Never infer self-identity from another subject's records. Never touch, inspect,
relaunch, stop, steer, or mutate Rill/dsh_agent processes, sessions, watchers, or cursors. Never
advance any Bifrost cursor. Do not edit files or durable state. Return one final peer-facing reply;
the owning host, not you, performs the causally linked Bifrost send."""


class CodexBifrostWake:
    """Persistent level watcher; idle operation makes no model request."""

    def __init__(
        self,
        *,
        bus: Bus,
        policy: WakePolicy,
        state: WakeState,
        log_path: os.PathLike[str] | str,
        cwd: os.PathLike[str] | str,
        model: str = "gpt-5.6-sol",
        effort: str = "low",
        max_message_chars: int = 16_000,
        turn_timeout: float = 900.0,
        block_ms: int = 5_000,
        server_factory: Callable[..., CodexAppServer] = CodexAppServer,
    ) -> None:
        if bus.agent_id != policy.agent or state.agent != policy.agent:
            raise WakeError("Bus, policy, and state must name the same subject seat")
        self.bus = bus
        self.policy = policy
        self.state = state
        self.log_path = Path(log_path).expanduser().resolve()
        self.cwd = Path(cwd).resolve()
        self.model = str(model)
        self.effort = str(effort)
        self.max_message_chars = int(max_message_chars)
        self.turn_timeout = float(turn_timeout)
        self.block_ms = max(100, int(block_ms))
        self.server_factory = server_factory
        self._server: Optional[CodexAppServer] = None
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _log(self, event: str, **fields: Any) -> None:
        _append_jsonl(
            self.log_path,
            {"at": _now(), "event": event, "subject": self.policy.agent, **fields},
        )

    def _app_server(self) -> CodexAppServer:
        if self._server is None:
            env = {
                "AKASHIC_AGENT_ID": self.policy.agent,
                "AKASHIC_HARNESS": "codex-desktop",
                "AKASHIC_CALLSIGN_HINT": "Sunshine",
                "AKASHIC_CALLSIGN_STATUS": "historical-unratified",
            }
            self._server = self.server_factory(cwd=self.cwd, env=env).start()
            self._log(
                "app_server_initialized",
                command=self._server.command,
                pid=self._server.process.pid,
                model_turns=0,
            )
        return self._server

    def handle(self, mid: str, fields: Mapping[str, Any]) -> Dict[str, Any]:
        mid = str(mid)
        if self.state.seen(mid):
            return {"mid": mid, "outcome": "duplicate"}
        try:
            message = decode_stream_message(self.bus, mid, fields)
        except WakeError as exc:
            self.state.record(mid, outcome="integrity_refused", detail=str(exc))
            self._log("message_refused", mid=mid, reason=str(exc))
            return {"mid": mid, "outcome": "integrity_refused"}

        if not self.policy.accepts(message):
            self.state.record(
                mid,
                outcome="ignored",
                detail=f"policy sender={message.frm!r} kind={message.kind!r}",
            )
            return {"mid": mid, "outcome": "ignored"}

        exact_size = len(
            json.dumps(message.content, ensure_ascii=False, default=str)
        )
        if exact_size > self.max_message_chars:
            detail = (
                f"exact content {exact_size} chars exceeds wake cap {self.max_message_chars}; "
                "refused rather than truncated"
            )
            self.state.record(mid, outcome="oversize_refused", detail=detail)
            self._log("message_refused", mid=mid, reason=detail)
            return {"mid": mid, "outcome": "oversize_refused"}

        try:
            server = self._app_server()
            thread = server.start_thread(
                ephemeral=True,
                sandbox="read-only",
                cwd=self.cwd,
                model=self.model,
                developer_instructions=WAKE_DEVELOPER_INSTRUCTIONS,
                approval_policy="never",
                personality="friendly",
            )
            # Durable admission precedes the paid turn: a crash cannot silently
            # redrive the same message and spend twice.
            self.state.record(
                mid,
                outcome="turn_admitted",
                detail="paid turn admitted; automatic redrive disabled",
                thread_id=thread.thread_id,
                peer=message.frm,
            )
            self._log("turn_admitted", mid=mid, thread_id=thread.thread_id, peer=message.frm)
            result = server.run_turn(
                thread.thread_id,
                build_wake_prompt(self.policy.agent, message),
                effort=self.effort,
                model=self.model,
                sandbox_policy={"type": "readOnly", "networkAccess": False},
                timeout=self.turn_timeout,
            )
        except (CodexAppServerError, OSError, ValueError) as exc:
            self.state.record(mid, outcome="turn_failed", detail=str(exc))
            self._log("turn_failed", mid=mid, error=str(exc))
            return {"mid": mid, "outcome": "turn_failed", "error": str(exc)}

        return self._finish(message, result)

    def _finish(self, message: Message, result: TurnResult) -> Dict[str, Any]:
        usage = result.token_usage or {}
        if result.status != "completed" or not result.text.strip():
            detail = f"status={result.status!r}; final_text={bool(result.text.strip())}"
            self.state.record(
                message.id,
                outcome="turn_incomplete",
                detail=detail,
                thread_id=result.thread_id,
                turn_id=result.turn_id,
                token_usage=usage,
            )
            self._log("turn_incomplete", mid=message.id, detail=detail, token_usage=usage)
            return {"mid": message.id, "outcome": "turn_incomplete"}

        reply_mid = self.bus.send(
            message.frm,
            "reply",
            result.text.strip(),
            meta={
                "answers": message.id,
                "wake_origin": "codex-bifrost-owned-app-server",
                "subject_seat": self.policy.agent,
                "source_thread_id": result.thread_id,
                "source_turn_id": result.turn_id,
            },
        )
        if not reply_mid:
            detail = "model completed but the Bifrost reply send failed"
            self.state.record(
                message.id,
                outcome="reply_failed",
                detail=detail,
                thread_id=result.thread_id,
                turn_id=result.turn_id,
                token_usage=usage,
            )
            self._log("reply_failed", mid=message.id, detail=detail, token_usage=usage)
            return {"mid": message.id, "outcome": "reply_failed"}

        self.state.record(
            message.id,
            outcome="replied",
            detail="one read-only Codex turn; causal reply link stamped",
            reply_mid=str(reply_mid),
            thread_id=result.thread_id,
            turn_id=result.turn_id,
            token_usage=usage,
        )
        self._log(
            "replied",
            mid=message.id,
            reply_mid=str(reply_mid),
            thread_id=result.thread_id,
            turn_id=result.turn_id,
            token_usage=usage,
        )
        return {"mid": message.id, "outcome": "replied", "reply_mid": str(reply_mid)}

    def run(self, *, once: bool = False) -> int:
        if self.bus._client is None:
            raise WakeError("Bifrost is offline")
        inbox = self.bus._inbox_key(self.policy.agent)
        handled = 0
        # Bus's ordinary client is intentionally fail-fast and has a ~2-3s
        # socket timeout. It cannot own a longer blocking XREAD. Reuse the
        # canonical dedicated-client seam whose timeout exceeds block_ms.
        blocking_client = self.bus._blocking_client(self.block_ms)
        if blocking_client is None:
            raise WakeError("Could not create the dedicated blocking Bifrost client")
        self._log(
            "armed",
            inbox=inbox,
            after=self.state.last_seen,
            allowed_senders=sorted(self.policy.allowed_senders),
            expected_answers=sorted(self.policy.expected_answers),
            idle_model_turns=0,
        )
        try:
            while not self._stop.is_set():
                try:
                    rows = blocking_client.xread(
                        {inbox: self.state.last_seen}, count=10, block=self.block_ms
                    )
                except Exception as exc:
                    try:
                        from redis.exceptions import ConnectionError as RedisConnectionError
                        from redis.exceptions import TimeoutError as RedisTimeoutError
                    except ImportError:  # pragma: no cover - redis is a runtime dependency
                        RedisConnectionError = RedisTimeoutError = ()  # type: ignore[assignment]
                    if not isinstance(exc, (RedisConnectionError, RedisTimeoutError)):
                        raise
                    self._log(
                        "redis_wait_interrupted",
                        error_type=type(exc).__name__,
                        detail=str(exc),
                        model_turns=0,
                    )
                    if once:
                        break
                    time.sleep(1.0)
                    continue
                if not rows:
                    if once:
                        break
                    continue
                for _stream, messages in rows:
                    for mid, fields in messages:
                        self.handle(str(mid), fields)
                        handled += 1
                        if once:
                            return handled
        finally:
            try:
                blocking_client.close()
            except Exception:
                pass
            self.close()
            self._log("stopped", handled=handled, last_seen=self.state.last_seen)
        return handled


def default_runtime_paths(agent: str) -> tuple[Path, Path]:
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    root = local / "AkashicAurora" / "codex-wake"
    return root / f"{agent}.state.json", root / f"{agent}.events.jsonl"


def install_signal_stops(watcher: CodexBifrostWake) -> None:
    def stop(_signum: int, _frame: Any) -> None:
        watcher.stop()

    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, stop)
            except (OSError, ValueError):
                pass


__all__ = [
    "CodexBifrostWake",
    "WakeError",
    "WakePolicy",
    "WakeState",
    "build_wake_prompt",
    "current_inbox_tail",
    "decode_exact_message",
    "decode_stream_message",
    "default_runtime_paths",
    "install_signal_stops",
]
