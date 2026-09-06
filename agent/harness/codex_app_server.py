"""Owned Codex App Server stdio host.

The Windows Codex build does not support the managed daemon lifecycle, so an
embedding process must own the child and its pipes.  This module keeps the
critical invariant explicit: stdout has exactly one long-lived reader, which
demultiplexes request responses and notifications for every caller.

Starting the host and creating a thread do not start a model turn.  A model is
invoked only by :meth:`CodexAppServer.run_turn`.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Any, Callable, Deque, Dict, Iterable, List, Mapping, Optional, Sequence


class CodexAppServerError(RuntimeError):
    """A loud protocol, lifecycle, or transport failure."""


@dataclass(frozen=True)
class ThreadHandle:
    thread_id: str
    raw: Dict[str, Any]


@dataclass(frozen=True)
class TurnResult:
    thread_id: str
    turn_id: str
    status: str
    text: str
    token_usage: Dict[str, Any]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class _Notification:
    seq: int
    method: str
    params: Dict[str, Any]


def summarize_turn_usage(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Preserve thread usage while deriving the cost of this turn.

    App Server's ``ThreadTokenUsage.total`` is cumulative across a thread;
    ``last`` describes the most recent model step.  A tool-bearing turn emits
    one update per model step, so the turn-local total is the sum of those
    ``last`` breakdowns.  Repeated notifications with the same cumulative
    total are deduplicated defensively.
    """
    normalized = [dict(sample) for sample in samples if isinstance(sample, Mapping)]
    if not normalized:
        return {}

    latest = dict(normalized[-1])
    steps: List[Dict[str, Any]] = []
    seen_cumulative: set[tuple[tuple[str, int | float], ...]] = set()
    for sample in normalized:
        last = sample.get("last")
        if not isinstance(last, Mapping):
            continue
        cumulative = sample.get("total")
        signature: tuple[tuple[str, int | float], ...] = ()
        if isinstance(cumulative, Mapping):
            signature = tuple(sorted(
                (str(key), value)
                for key, value in cumulative.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ))
        if signature and signature in seen_cumulative:
            continue
        if signature:
            seen_cumulative.add(signature)
        steps.append(dict(last))

    if not steps:
        return latest

    fields = sorted({str(key) for step in steps for key, value in step.items()
                     if isinstance(value, (int, float)) and not isinstance(value, bool)})
    latest["turnTotal"] = {
        field: sum(
            value for step in steps
            if isinstance((value := step.get(field)), (int, float))
            and not isinstance(value, bool)
        )
        for field in fields
    }
    latest["modelSteps"] = len(steps)
    return latest


def resolve_codex_binary(explicit: Optional[os.PathLike[str] | str] = None) -> Path:
    """Resolve the app-managed Codex executable without pinning its version hash."""
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise CodexAppServerError(f"Codex executable does not exist: {path}")

    env_path = os.environ.get("AKASHIC_CODEX_BINARY")
    if env_path:
        path = Path(env_path).expanduser().resolve()
        if path.is_file():
            return path

    local = os.environ.get("LOCALAPPDATA")
    if local:
        root = Path(local) / "OpenAI" / "Codex" / "bin"
        candidates = list(root.glob("*/codex.exe")) if root.is_dir() else []
        if candidates:
            return max(candidates, key=lambda item: item.stat().st_mtime).resolve()

    found = shutil.which("codex")
    if found:
        return Path(found).resolve()
    raise CodexAppServerError(
        "Could not resolve Codex. Set AKASHIC_CODEX_BINARY or install/open Codex Desktop."
    )


def default_command(*, trust_vetted_hooks: bool = True) -> List[str]:
    command = [str(resolve_codex_binary())]
    if trust_vetted_hooks:
        command.append("--dangerously-bypass-hook-trust")
    command.extend(["app-server", "--stdio"])
    return command


class CodexAppServer:
    """A newline-JSON App Server client with one owned stdout reader."""

    def __init__(
        self,
        *,
        command: Optional[Sequence[str]] = None,
        cwd: Optional[os.PathLike[str] | str] = None,
        env: Optional[Mapping[str, str]] = None,
        request_timeout: float = 30.0,
        notification_limit: int = 2048,
        request_handlers: Optional[
            Mapping[str, Callable[[Dict[str, Any]], Mapping[str, Any]]]
        ] = None,
        experimental_api: bool = False,
    ) -> None:
        self.command = list(command) if command is not None else default_command()
        self.cwd = str(Path(cwd).resolve()) if cwd is not None else None
        self.env = dict(env or {})
        self.request_timeout = float(request_timeout)
        self._notification_limit = int(notification_limit)
        self.request_handlers = dict(request_handlers or {})
        self.experimental_api = bool(experimental_api)

        self._process: Optional[subprocess.Popen[str]] = None
        self._pending: Dict[int, queue.Queue[Any]] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._next_id = 1
        self._started = False
        self._closed = False
        self._dead = threading.Event()

        self._notification_condition = threading.Condition()
        self._notifications: Deque[_Notification] = deque(maxlen=self._notification_limit)
        self._notification_seq = 0
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self.stdout_reader_starts = 0
        self.stderr_tail: Deque[str] = deque(maxlen=100)
        self.protocol_noise: Deque[str] = deque(maxlen=100)

    # ------------------------------------------------------------------ lifecycle
    @property
    def process(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise CodexAppServerError("App Server has not been started")
        return self._process

    def start(self) -> "CodexAppServer":
        if self._started:
            return self
        if self._closed:
            raise CodexAppServerError("A closed App Server host cannot be restarted")

        child_env = os.environ.copy()
        child_env.update({str(k): str(v) for k, v in self.env.items()})
        try:
            self._process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=child_env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise CodexAppServerError(f"Could not launch Codex App Server: {exc}") from exc

        self.stdout_reader_starts += 1
        self._stdout_thread = threading.Thread(
            target=self._stdout_reader,
            name="codex-app-server-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._stderr_reader,
            name="codex-app-server-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        self._started = True

        try:
            initialize_params: Dict[str, Any] = {
                "clientInfo": {"name": "akashic-bifrost-wake", "version": "1.0"}
            }
            if self.experimental_api:
                initialize_params["capabilities"] = {"experimentalApi": True}
            self.request(
                "initialize",
                initialize_params,
            )
            self.notify("initialized", {})
        except Exception:
            self.close()
            raise
        return self

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        process = self._process
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        self._fail_pending(CodexAppServerError("Codex App Server closed"))

    def __enter__(self) -> "CodexAppServer":
        return self.start()

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()

    # ------------------------------------------------------------------ JSON-RPC
    def _send(self, payload: Mapping[str, Any]) -> None:
        process = self.process
        if process.poll() is not None:
            detail = " | ".join(self.stderr_tail)
            raise CodexAppServerError(
                f"Codex App Server exited rc={process.returncode}"
                + (f": {detail}" if detail else "")
            )
        line = json.dumps(dict(payload), ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._write_lock:
            try:
                assert process.stdin is not None
                process.stdin.write(line)
                process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise CodexAppServerError(f"Codex App Server stdin failed: {exc}") from exc

    def request(
        self,
        method: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self._started:
            self.start()
        with self._pending_lock:
            request_id = self._next_id
            self._next_id += 1
            response_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
            self._pending[request_id] = response_queue
        try:
            self._send({"id": request_id, "method": method, "params": dict(params or {})})
            try:
                response = response_queue.get(
                    timeout=self.request_timeout if timeout is None else float(timeout)
                )
            except queue.Empty as exc:
                raise CodexAppServerError(
                    f"Timed out waiting for App Server response to {method!r}"
                ) from exc
            if isinstance(response, BaseException):
                raise response
            if response.get("error") is not None:
                raise CodexAppServerError(
                    f"App Server {method!r} failed: {json.dumps(response['error'], ensure_ascii=False)}"
                )
            result = response.get("result")
            if not isinstance(result, dict):
                raise CodexAppServerError(
                    f"App Server {method!r} returned a non-object result: {result!r}"
                )
            return result
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: Optional[Mapping[str, Any]] = None) -> None:
        if not self._started:
            self.start()
        self._send({"method": method, "params": dict(params or {})})

    def _stdout_reader(self) -> None:
        """The sole reader of child stdout for the entire process lifetime."""
        process = self.process
        try:
            assert process.stdout is not None
            for raw in process.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    self.protocol_noise.append(line)
                    continue
                if not isinstance(message, dict):
                    self.protocol_noise.append(line)
                    continue
                if "id" in message and "method" not in message:
                    try:
                        response_id = int(message["id"])
                    except (TypeError, ValueError):
                        self.protocol_noise.append(line)
                        continue
                    with self._pending_lock:
                        response_queue = self._pending.get(response_id)
                    if response_queue is not None:
                        response_queue.put(message)
                    else:
                        self.protocol_noise.append(line)
                    continue
                method = message.get("method")
                params = message.get("params")
                if "id" in message and isinstance(method, str):
                    self._dispatch_server_request(
                        message["id"],
                        method,
                        params if isinstance(params, dict) else {},
                    )
                    continue
                if isinstance(method, str):
                    self._record_notification(
                        method,
                        params if isinstance(params, dict) else {},
                    )
                else:
                    self.protocol_noise.append(line)
        except Exception as exc:
            self.protocol_noise.append(f"stdout reader failed: {exc!r}")
        finally:
            self._dead.set()
            self._fail_pending(CodexAppServerError("Codex App Server stdout closed"))
            with self._notification_condition:
                self._notification_condition.notify_all()

    def _dispatch_server_request(
        self,
        request_id: Any,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """Answer a reverse JSON-RPC request without blocking the sole stdout reader."""
        handler = self.request_handlers.get(method)
        if handler is None:
            self._send(
                {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"No client handler registered for {method}",
                    },
                }
            )
            return

        def answer() -> None:
            try:
                result = handler(params)
                if not isinstance(result, Mapping):
                    raise TypeError("server request handler must return an object")
                self._send({"id": request_id, "result": dict(result)})
            except Exception as exc:
                try:
                    self._send(
                        {
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": f"{type(exc).__name__}: {exc}",
                            },
                        }
                    )
                except Exception as send_exc:
                    self.protocol_noise.append(
                        f"server request {method!r} reply failed: {send_exc!r}"
                    )

        threading.Thread(
            target=answer,
            name=f"codex-app-server-request-{method.replace('/', '-')}",
            daemon=True,
        ).start()

    def _stderr_reader(self) -> None:
        try:
            process = self.process
            assert process.stderr is not None
            for raw in process.stderr:
                line = raw.rstrip("\r\n")
                if line:
                    self.stderr_tail.append(line)
        except Exception as exc:
            self.stderr_tail.append(f"stderr reader failed: {exc!r}")

    def _fail_pending(self, exc: BaseException) -> None:
        with self._pending_lock:
            queues = list(self._pending.values())
        for response_queue in queues:
            try:
                response_queue.put_nowait(exc)
            except queue.Full:
                pass

    # ------------------------------------------------------------------ notification joins
    @property
    def notification_cursor(self) -> int:
        with self._notification_condition:
            return self._notification_seq

    def _record_notification(self, method: str, params: Dict[str, Any]) -> None:
        with self._notification_condition:
            self._notification_seq += 1
            self._notifications.append(_Notification(self._notification_seq, method, params))
            self._notification_condition.notify_all()

    def notifications(
        self,
        method: str,
        *,
        after: int = 0,
        predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        with self._notification_condition:
            return [
                item.params
                for item in self._notifications
                if item.seq > after
                and item.method == method
                and (predicate is None or predicate(item.params))
            ]

    def wait_notification(
        self,
        method: str,
        *,
        after: int = 0,
        predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        deadline = time.monotonic() + float(timeout)
        with self._notification_condition:
            while True:
                for item in self._notifications:
                    if (
                        item.seq > after
                        and item.method == method
                        and (predicate is None or predicate(item.params))
                    ):
                        return item.params
                if self._dead.is_set():
                    detail = " | ".join(self.stderr_tail)
                    raise CodexAppServerError(
                        "Codex App Server closed before notification"
                        + (f": {detail}" if detail else "")
                    )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CodexAppServerError(
                        f"Timed out waiting for App Server notification {method!r}"
                    )
                self._notification_condition.wait(timeout=remaining)

    # ------------------------------------------------------------------ v2 convenience API
    def start_thread(
        self,
        *,
        ephemeral: bool = True,
        sandbox: str = "read-only",
        cwd: Optional[os.PathLike[str] | str] = None,
        model: Optional[str] = None,
        developer_instructions: Optional[str] = None,
        approval_policy: str = "never",
        personality: Optional[str] = None,
        dynamic_tools: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> ThreadHandle:
        if dynamic_tools and not self.experimental_api:
            raise CodexAppServerError(
                "dynamic_tools require experimental_api=True during App Server initialization"
            )
        params: Dict[str, Any] = {
            "ephemeral": bool(ephemeral),
            "sandbox": sandbox,
            "approvalPolicy": approval_policy,
        }
        if cwd is not None:
            params["cwd"] = str(Path(cwd).resolve())
        elif self.cwd is not None:
            params["cwd"] = self.cwd
        if model:
            params["model"] = model
        if developer_instructions:
            params["developerInstructions"] = developer_instructions
        if personality:
            params["personality"] = personality
        if dynamic_tools is not None:
            params["dynamicTools"] = [dict(spec) for spec in dynamic_tools]
        result = self.request("thread/start", params)
        thread = result.get("thread")
        thread_id = thread.get("id") if isinstance(thread, dict) else None
        if not thread_id:
            raise CodexAppServerError(
                f"thread/start response has no thread id: {json.dumps(result, ensure_ascii=False)}"
            )
        return ThreadHandle(str(thread_id), result)

    def resume_thread(
        self,
        thread_id: str,
        *,
        sandbox: str = "read-only",
        cwd: Optional[os.PathLike[str] | str] = None,
        model: Optional[str] = None,
        developer_instructions: Optional[str] = None,
        approval_policy: str = "never",
        personality: Optional[str] = None,
        dynamic_tools: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> ThreadHandle:
        """Load one persisted Codex thread without starting a model turn.

        The caller owns the thread id and must treat an active-writer refusal as
        serialization, not as permission to create a replacement conversation.
        """
        requested_id = str(thread_id or "").strip()
        if not requested_id:
            raise CodexAppServerError("thread/resume requires a non-empty thread id")
        if dynamic_tools and not self.experimental_api:
            raise CodexAppServerError(
                "dynamic_tools require experimental_api=True during App Server initialization"
            )
        params: Dict[str, Any] = {
            "threadId": requested_id,
            "sandbox": sandbox,
            "approvalPolicy": approval_policy,
        }
        if cwd is not None:
            params["cwd"] = str(Path(cwd).resolve())
        elif self.cwd is not None:
            params["cwd"] = self.cwd
        if model:
            params["model"] = model
        if developer_instructions:
            params["developerInstructions"] = developer_instructions
        if personality:
            params["personality"] = personality
        if dynamic_tools is not None:
            params["dynamicTools"] = [dict(spec) for spec in dynamic_tools]
        result = self.request("thread/resume", params)
        thread = result.get("thread")
        resumed_id = thread.get("id") if isinstance(thread, dict) else None
        if not resumed_id:
            raise CodexAppServerError(
                f"thread/resume response has no thread id: {json.dumps(result, ensure_ascii=False)}"
            )
        if str(resumed_id) != requested_id:
            raise CodexAppServerError(
                f"thread/resume returned {resumed_id!r} for requested thread {requested_id!r}"
            )
        return ThreadHandle(requested_id, result)

    def fork_thread(
        self,
        thread_id: str,
        *,
        last_turn_id: Optional[str] = None,
        ephemeral: bool = False,
    ) -> ThreadHandle:
        """Copy stored history into a new thread owned by this App Server host.

        Forking does not resume the source and does not start a model turn.  A
        persistent fork can therefore move continuity away from a different
        client's active writer without racing that writer.
        """
        source_id = str(thread_id or "").strip()
        if not source_id:
            raise CodexAppServerError("thread/fork requires a non-empty source thread id")
        params: Dict[str, Any] = {
            "threadId": source_id,
            "ephemeral": bool(ephemeral),
        }
        if last_turn_id is not None:
            bounded_turn = str(last_turn_id).strip()
            if not bounded_turn:
                raise CodexAppServerError(
                    "thread/fork last_turn_id must be non-empty when supplied"
                )
            params["lastTurnId"] = bounded_turn
        result = self.request("thread/fork", params)
        thread = result.get("thread")
        forked_id = thread.get("id") if isinstance(thread, dict) else None
        if not forked_id:
            raise CodexAppServerError(
                f"thread/fork response has no thread id: {json.dumps(result, ensure_ascii=False)}"
            )
        forked_from = thread.get("forkedFromId") if isinstance(thread, dict) else None
        if forked_from is not None and str(forked_from) != source_id:
            raise CodexAppServerError(
                f"thread/fork returned source {forked_from!r} for requested {source_id!r}"
            )
        return ThreadHandle(str(forked_id), result)

    def run_turn(
        self,
        thread_id: str,
        prompt: str,
        *,
        effort: Optional[str] = "low",
        model: Optional[str] = None,
        additional_context: Optional[Mapping[str, str]] = None,
        sandbox_policy: Optional[Mapping[str, Any]] = None,
        timeout: float = 600.0,
    ) -> TurnResult:
        cursor = self.notification_cursor
        params: Dict[str, Any] = {
            "threadId": str(thread_id),
            "input": [{"type": "text", "text": str(prompt)}],
        }
        if effort:
            params["effort"] = effort
        if model:
            params["model"] = model
        if additional_context:
            params["additionalContext"] = {
                str(key): {"kind": "application", "value": str(value)}
                for key, value in additional_context.items()
            }
        if sandbox_policy:
            params["sandboxPolicy"] = dict(sandbox_policy)

        started = self.request("turn/start", params, timeout=min(float(timeout), 60.0))
        turn = started.get("turn")
        turn_id = turn.get("id") if isinstance(turn, dict) else None
        if not turn_id:
            raise CodexAppServerError(
                f"turn/start response has no turn id: {json.dumps(started, ensure_ascii=False)}"
            )
        tid = str(turn_id)

        def same_turn(value: Dict[str, Any]) -> bool:
            event_tid = value.get("turnId")
            nested = value.get("turn")
            if event_tid is None and isinstance(nested, dict):
                event_tid = nested.get("id")
            return str(event_tid or "") == tid

        completed = self.wait_notification(
            "turn/completed", after=cursor, predicate=same_turn, timeout=timeout
        )
        item_events = self.notifications(
            "item/completed", after=cursor, predicate=same_turn
        )
        texts = []
        for event in item_events:
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agentMessage" and item.get("text"):
                texts.append(str(item["text"]))
        usage_events = self.notifications(
            "thread/tokenUsage/updated", after=cursor, predicate=same_turn
        )
        usage = summarize_turn_usage([
            event.get("tokenUsage", {}) for event in usage_events
            if isinstance(event.get("tokenUsage"), Mapping)
        ])
        completed_turn = completed.get("turn")
        status = completed_turn.get("status") if isinstance(completed_turn, dict) else None
        return TurnResult(
            thread_id=str(thread_id),
            turn_id=tid,
            status=str(status or "unknown"),
            text="\n\n".join(texts).strip(),
            token_usage=usage if isinstance(usage, dict) else {},
            raw=completed,
        )


__all__ = [
    "CodexAppServer",
    "CodexAppServerError",
    "ThreadHandle",
    "TurnResult",
    "default_command",
    "resolve_codex_binary",
    "summarize_turn_usage",
]
