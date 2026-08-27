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
import shlex
import threading
import time
import uuid
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional

from agent.harness.codex_app_server import CodexAppServer, CodexAppServerError, TurnResult
from core.comm import packet_spec
from core.comm.bus import Bus, Message
from core.comm.toolbox import ToolBox
from core.fleet import residents
from core.toolbelt.registry import Toolbelt


DIRECT_ACTION_KINDS = frozenset({"request", "question", "handoff", "blocker"})
ANSWER_KINDS = frozenset({"response", "reply", "answer", "completion"})
STATE_SCHEMA = 1
AURORA_SAFE_READ_GRAMMAR = {
    # This grammar is intentionally bridge-local and narrower than ToolBox's
    # historical family allowlist.  Values are (minimum positionals, maximum
    # positionals, boolean switches, flags taking one value).  A missing maximum
    # means any number of plain positional words is safe for that read verb.
    "discover": (0, 1, frozenset({"--json"}), frozenset()),
    "doctor": (
        0,
        0,
        frozenset({"--deploy", "--progress", "--json"}),
        frozenset({"--agents"}),
    ),
    "flightdeck": (0, 0, frozenset({"--json"}), frozenset({"--agent"})),
    "flow": (0, 1, frozenset({"--json"}), frozenset({"--window", "--limit"})),
    "harnesses": (0, 0, frozenset({"--json"}), frozenset()),
    "injections": (0, 0, frozenset({"--json"}), frozenset({"--hours"})),
    "knowledge-map": (0, None, frozenset({"--json"}), frozenset({"--per-layer"})),
    "list": (0, 0, frozenset({"--json"}), frozenset()),
    "locks": (0, 1, frozenset({"--json"}), frozenset()),
    "lookback": (
        1,
        None,
        frozenset({"--json"}),
        frozenset({"--per-layer", "--layers"}),
    ),
    "promoted": (
        0,
        0,
        frozenset({"--json"}),
        frozenset({"--limit", "--since", "--until"}),
    ),
    "pulse": (0, 1, frozenset({"--json"}), frozenset()),
    "recall": (
        0,
        1,
        frozenset({"--json"}),
        frozenset({"--full", "--agent"}),
    ),
    "stats": (
        0,
        0,
        frozenset({"--silence", "--json"}),
        frozenset({"--hours", "--days"}),
    ),
    "status": (0, 0, frozenset({"--json"}), frozenset()),
    "triage": (0, 0, frozenset({"--json"}), frozenset({"--min-surfaced"})),
    "unwedge": (1, 1, frozenset({"--json"}), frozenset()),
}
AURORA_SAFE_READ_VERBS = frozenset(AURORA_SAFE_READ_GRAMMAR)
AURORA_SHELL_META = frozenset(";|&><`$()\n\r")
AURORA_READ_COMBO_TOOL_NAME = "aurora_read_combo"
AURORA_COMBO_CATALOG_TOOL_NAME = "aurora_combo_catalog"
AURORA_COMBO_OUTPUT_CHARS = 24_000
AURORA_READ_VERB_TOOL = {
    "type": "function",
    "name": "aurora_read_verb",
    "description": (
        "Run one read-only Akashic Aurora agent_cli verb through the governed unattended "
        "exec door. This is not raw shell: the host independently checks the launch flag, "
        "the live subject-seat ACL, a bridge-specific verb and argument grammar, the shared "
        "ToolBox wall, and shell metacharacters."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "verb": {
                "type": "string",
                "enum": sorted(AURORA_SAFE_READ_VERBS),
                "description": "One verb from Sunshine's conservative read grammar.",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": (
                    "Plain argv items for the selected verb. Unknown flags, shell syntax, "
                    "and positional action subcommands are refused by the host."
                ),
            },
        },
        "required": ["verb"],
        "additionalProperties": False,
    },
}

AURORA_COMBO_CATALOG_TOOL = {
    "type": "function",
    "name": AURORA_COMBO_CATALOG_TOOL_NAME,
    "description": (
        "Explain which active combos in this subject seat's toolbelt are admitted or "
        "omitted by the Codex bridge, including the exact failing step and refusal. "
        "This diagnostic executes no commands and cannot inspect a peer-owned belt."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}


def _aurora_read_combo_tool(names: List[str]) -> Dict[str, Any]:
    """Build the per-turn schema from the subject seat's currently safe combos."""
    return {
        "type": "function",
        "name": AURORA_READ_COMBO_TOOL_NAME,
        "description": (
            "Run one zero-argument, subject-authored Akashic Aurora combo. The host "
            "expands the combo from the subject seat's live toolbelt, preflights every "
            "step against Sunshine's conservative read grammar before executing step one, "
            "and then re-enters the existing ToolBox wall for each primitive."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": list(names),
                    "description": "One currently safe combo from this subject seat's belt.",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    }


def _safe_read_args_refusal(verb: str, args: List[str]) -> Optional[str]:
    """Return why argv is outside Sunshine's bridge-local read grammar, else None."""
    grammar = AURORA_SAFE_READ_GRAMMAR.get(verb)
    if grammar is None:
        return f"{verb!r} is not in the Codex bridge safe read grammar"
    if any(any(ch in token for ch in AURORA_SHELL_META) for token in args):
        return "shell metacharacters are not allowed by the Codex bridge"
    min_positionals, max_positionals, switches, value_flags = grammar
    positionals = 0
    index = 0
    while index < len(args):
        token = args[index]
        if not token or token == "--":
            return "empty arguments and the '--' option escape are not allowed"
        if token.startswith("-"):
            flag, has_inline, inline_value = token.partition("=")
            if flag in switches:
                if has_inline:
                    return f"switch {flag!r} does not take a value"
            elif flag in value_flags:
                if has_inline:
                    if not inline_value or inline_value.startswith("-"):
                        return f"flag {flag!r} needs one plain value"
                else:
                    index += 1
                    if index >= len(args) or not args[index] or args[index].startswith("-"):
                        return f"flag {flag!r} needs one plain value"
            else:
                return f"flag {flag!r} is not allowed for read verb {verb!r}"
        else:
            positionals += 1
        index += 1
    if positionals < min_positionals:
        return f"read verb {verb!r} needs at least {min_positionals} positional argument(s)"
    if max_positionals is not None and positionals > max_positionals:
        return f"read verb {verb!r} accepts at most {max_positionals} positional argument(s)"
    return None


class WakeError(RuntimeError):
    """A loud watcher contract failure."""


@dataclass(frozen=True)
class SubjectIdentity:
    """One authoritative identity snapshot, resolved once for one admitted turn."""

    agent_id: str
    callsign: Optional[str]
    status: str
    authority: str

    @property
    def signature(self) -> tuple[str, str, str, str]:
        return (
            self.agent_id,
            self.callsign or "",
            self.status,
            self.authority,
        )


def resolve_subject_identity(agent: str) -> SubjectIdentity:
    """Resolve callsign truth from the resident registry, never from wake prose.

    Environment values are continuity hints for an unratified or temporarily unavailable
    registry. They can never promote themselves to ``ratified``: only a resident ceremony
    can do that. A registry failure remains UNKNOWN rather than becoming "unregistered".
    """
    subject = str(agent or "").strip()
    hint = str(os.environ.get("AKASHIC_CALLSIGN_HINT") or "").strip() or None
    hinted_status = str(os.environ.get("AKASHIC_CALLSIGN_STATUS") or "").strip().lower()
    try:
        record = residents.get(subject)
    except Exception:
        return SubjectIdentity(
            agent_id=subject,
            callsign=hint,
            status="registry-unavailable",
            authority=(
                "environment-hint;resident-registry-unavailable"
                if hint
                else "resident-registry-unavailable"
            ),
        )

    callsign = str((record or {}).get("callsign") or "").strip() or None
    if callsign:
        return SubjectIdentity(
            agent_id=subject,
            callsign=callsign,
            status="ratified",
            authority="resident-registry",
        )
    if hint:
        status = "registry-mismatch" if hinted_status == "ratified" else (
            hinted_status or "historical-unratified"
        )
        return SubjectIdentity(
            agent_id=subject,
            callsign=hint,
            status=status,
            authority="environment-hint;resident-registry-absent",
        )
    return SubjectIdentity(
        agent_id=subject,
        callsign=None,
        status="unregistered",
        authority="resident-registry",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage_accounting(usage: Mapping[str, Any]) -> Dict[str, Any]:
    """Label whole-turn usage separately from the final model step.

    App Server reports both ``total`` and ``last``. They are identical for a
    one-step turn and diverge when tools or another continuation cause more
    than one model call. A cost receipt that leaves those scopes implicit makes
    an expensive multi-step turn look like only its final call.
    """
    raw_total = usage.get("total") if isinstance(usage, Mapping) else None
    raw_last = usage.get("last") if isinstance(usage, Mapping) else None
    turn_total = dict(raw_total) if isinstance(raw_total, Mapping) else {}
    final_step = dict(raw_last) if isinstance(raw_last, Mapping) else {}
    basis = "turn_total" if turn_total else "final_model_step_fallback"
    if not turn_total:
        turn_total = dict(final_step)
    return {
        "accounting_basis": basis,
        "turn_total": turn_total,
        "final_model_step": final_step,
        "multi_step": bool(raw_total and raw_last and turn_total != final_step),
    }


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
    required_source: Optional[str] = None

    def accepts(self, message: Message) -> bool:
        if message.to != self.agent or message.frm not in self.allowed_senders:
            return False
        if self.required_source:
            actual_source = str((message.meta or {}).get("source") or "").lower()
            if actual_source != str(self.required_source).lower():
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


def build_wake_prompt(
    agent: str,
    message: Message,
    *,
    identity: SubjectIdentity,
) -> str:
    """Render the exact subject, identity snapshot, and peer message."""
    content = json.dumps(message.content, ensure_ascii=False, indent=2, default=str)
    meta = json.dumps(message.meta or {}, ensure_ascii=False, sort_keys=True, default=str)
    callsign = identity.callsign or "(none)"
    return f"""This is a fresh, event-driven Akashic Aurora collaboration turn.

SUBJECT SEAT: {agent}
HARNESS: Codex Desktop via an independently owned App Server child
CALLSIGN: {callsign}
CALLSIGN STATUS: {identity.status}
IDENTITY AUTHORITY: {identity.authority}
SOURCE PEER: {message.frm}
SOURCE MESSAGE ID: {message.id}
SOURCE KIND: {message.kind}
SOURCE META: {meta}

Identity law: evidence about another seat is not evidence about this subject. Preserve uncertainty
and cite the subject of every identity-bearing claim. Resident-registry ratification is authoritative;
an environment hint can preserve history but can never ratify itself.

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


def wake_developer_instructions(agent: str, identity: SubjectIdentity) -> str:
    """Bind a read-only wake turn to the same identity snapshot as its prompt and child."""
    callsign = identity.callsign or "(none)"
    return f"""You are the Codex/{agent} seat in a narrowly scoped, read-only Akashic Aurora
wake turn. The subject seat is {agent}. Its callsign is {callsign}; callsign status is
{identity.status}, according to {identity.authority}. The resident registry is authoritative;
an environment hint cannot ratify itself. Never infer self-identity from another subject's records.
Never touch, inspect, relaunch, stop, steer, or mutate Rill/dsh_agent processes, sessions, watchers,
or cursors. Never advance any Bifrost cursor. Do not edit files or durable state. Return one final
peer-facing reply; the owning host, not you, performs the causally linked Bifrost send."""


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
        allow_exec: bool = False,
        server_factory: Callable[..., CodexAppServer] = CodexAppServer,
        identity_resolver: Callable[[str], SubjectIdentity] = resolve_subject_identity,
        toolbelt_factory: Callable[[str], Toolbelt] = Toolbelt,
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
        self.allow_exec = bool(allow_exec)
        self.server_factory = server_factory
        self.identity_resolver = identity_resolver
        self.toolbelt_factory = toolbelt_factory
        self._server: Optional[CodexAppServer] = None
        self._server_identity_signature: Optional[tuple[str, str, str, str]] = None
        self._stop = threading.Event()
        self._toolbox = ToolBox(
            self.cwd,
            allow_exec=self.allow_exec,
            trust=True,
            allow_secrets=False,
            confirm=lambda _prompt: False,
            agent_id=self.policy.agent,
            allow_write=False,
        )

    @property
    def dynamic_tools(self) -> List[Dict[str, Any]]:
        """Tools advertised to the model; launch posture is visible at admission time."""
        if not self.allow_exec:
            return []
        tools = [AURORA_READ_VERB_TOOL, AURORA_COMBO_CATALOG_TOOL]
        safe_names = sorted(self._safe_combo_catalog())
        if safe_names:
            tools.append(_aurora_read_combo_tool(safe_names))
        return tools

    def _combo_admission_rows(self) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Evaluate subject-owned active combos without executing a primitive."""
        try:
            belt = self.toolbelt_factory(self.policy.agent)
            names = sorted(str(name) for name in belt.active())
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return [], f"{type(exc).__name__}: {exc}"

        rows: List[Dict[str, Any]] = []
        for name in names:
            row: Dict[str, Any] = {
                "name": name,
                "evidence": "UNKNOWN",
                "family": "UNSORTED",
                "steps": [],
                "admitted": False,
                "reason": "entry could not be evaluated",
            }
            try:
                entry = belt.get(name)
                row["evidence"] = str(entry.get("evidence", "UNKNOWN"))
                row["family"] = str(entry.get("family", "UNSORTED"))
                kind = str(entry.get("kind", "alias"))
                try:
                    params = int(entry.get("params", 0) or 0)
                except (TypeError, ValueError):
                    row["reason"] = f"invalid parameter count {entry.get('params')!r}"
                    rows.append(row)
                    continue
                if kind != "alias":
                    row["reason"] = f"kind {kind!r} is not a zero-argument combo"
                    rows.append(row)
                    continue
                if params:
                    row["reason"] = f"requires {params} argument(s); bridge combos are zero-argument"
                    rows.append(row)
                    continue
                steps = [[str(arg) for arg in step] for step in belt.resolve(name)]
                row["steps"] = steps
            except (ValueError, KeyError, TypeError) as exc:
                row["reason"] = f"registry resolution failed: {type(exc).__name__}: {exc}"
                rows.append(row)
                continue

            for index, step in enumerate(row["steps"], start=1):
                if not step:
                    row["reason"] = f"step {index} is empty"
                    break
                refusal = _safe_read_args_refusal(step[0], step[1:])
                if refusal is not None:
                    row["reason"] = f"step {index} ({' '.join(step)}): {refusal}"
                    break
            else:
                row["admitted"] = True
                row["reason"] = f"all {len(row['steps'])} step(s) clear the bridge grammar"
            rows.append(row)
        return rows, None

    def _combo_admission_text(self) -> tuple[str, bool]:
        """Render the admission diagnostic within the same whole-result cap as execution."""
        rows, error = self._combo_admission_rows()
        if error is not None:
            return (
                f"UNAVAILABLE: combo admission catalog for {self.policy.agent}: {error}",
                False,
            )
        admitted = sum(1 for row in rows if row["admitted"])
        lines = [
            f"# combo admission: {self.policy.agent} -- active={len(rows)} "
            f"admitted={admitted} omitted={len(rows) - admitted}",
        ]
        if not rows:
            lines.append("  no active subject-authored combos")
        for row in rows:
            verdict = "ADMITTED" if row["admitted"] else "OMITTED"
            lines.append(
                f"  [{verdict}] {row['name']} [{row['evidence']}; {row['family']}] -- "
                f"{row['reason']}"
            )
        body = "\n".join(lines)
        if len(body) > AURORA_COMBO_OUTPUT_CHARS:
            marker = "\n[combo catalog capped; remainder omitted]"
            body = body[: AURORA_COMBO_OUTPUT_CHARS - len(marker)] + marker
        return body, True

    def _safe_combo_catalog(self) -> Dict[str, List[List[str]]]:
        """Resolve safe zero-argument combos; registry blindness fails this surface closed."""
        rows, error = self._combo_admission_rows()
        if error is not None:
            return {}
        return {
            str(row["name"]): [list(step) for step in row["steps"]]
            for row in rows
            if row["admitted"]
        }

    def handle_dynamic_tool_call(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        """Execute one structured read verb through the bridge and ToolBox walls."""
        def response(success: bool, text: str) -> Dict[str, Any]:
            return {
                "success": bool(success),
                "contentItems": [{"type": "inputText", "text": str(text)}],
            }

        if not self.allow_exec:
            return response(False, "REFUSED: Codex wake exec lacks its explicit launch opt-in.")
        tool_name = str(params.get("tool") or "")
        if tool_name not in {
            AURORA_READ_VERB_TOOL["name"],
            AURORA_READ_COMBO_TOOL_NAME,
            AURORA_COMBO_CATALOG_TOOL_NAME,
        }:
            return response(False, f"REFUSED: unknown dynamic tool {params.get('tool')!r}.")
        arguments = params.get("arguments")
        if not isinstance(arguments, Mapping):
            return response(False, "REFUSED: dynamic tool arguments must be an object.")
        if tool_name == AURORA_COMBO_CATALOG_TOOL_NAME:
            if arguments:
                return response(False, "REFUSED: combo admission catalog accepts no arguments.")
            body, success = self._combo_admission_text()
            return response(success, body)
        if tool_name == AURORA_READ_COMBO_TOOL_NAME:
            if set(arguments) - {"name"}:
                return response(False, "REFUSED: read combos accept only the 'name' field.")
            name = str(arguments.get("name") or "").strip()
            catalog = self._safe_combo_catalog()
            steps = catalog.get(name)
            if steps is None:
                return response(
                    False,
                    f"REFUSED by Codex bridge safe read grammar: combo {name!r} is not a "
                    "currently safe zero-argument combo for this subject seat.",
                )
            rendered: List[str] = []
            total = len(steps)
            for index, argv in enumerate(steps, start=1):
                command = shlex.join(["py", "agent_cli.py", *argv])
                output = self._toolbox.run_command(command, timeout=120)
                rendered.append(f"[{name} {index}/{total}] {' '.join(argv)}\n{output}")
                refused = output.startswith(
                    ("REFUSED", "ERROR:", "DENIED", "run_command is DISABLED")
                )
                failed_exit = "\n[exit " in output
                if refused or failed_exit:
                    return response(False, "\n\n".join(rendered)[:AURORA_COMBO_OUTPUT_CHARS])
            body = "\n\n".join(rendered)
            if len(body) > AURORA_COMBO_OUTPUT_CHARS:
                marker = "\n\n[combo output capped; remainder omitted]"
                body = body[: AURORA_COMBO_OUTPUT_CHARS - len(marker)] + marker
            return response(True, body)
        verb = str(arguments.get("verb") or "").strip()
        raw_args = arguments.get("args", [])
        if not isinstance(raw_args, list) or any(not isinstance(arg, str) for arg in raw_args):
            return response(False, "REFUSED: args must be an array of strings.")
        grammar_refusal = _safe_read_args_refusal(verb, raw_args)
        if grammar_refusal:
            return response(False, f"REFUSED by Codex bridge safe read grammar: {grammar_refusal}.")
        command = shlex.join(["py", "agent_cli.py", verb, *raw_args])
        output = self._toolbox.run_command(command, timeout=120)
        refused = output.startswith(("REFUSED", "ERROR:", "DENIED", "run_command is DISABLED"))
        failed_exit = "\n[exit " in output
        return response(not refused and not failed_exit, output)

    def stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
        self._server_identity_signature = None

    def _log(self, event: str, **fields: Any) -> None:
        _append_jsonl(
            self.log_path,
            {"at": _now(), "event": event, "subject": self.policy.agent, **fields},
        )

    def _app_server(self, identity: SubjectIdentity) -> CodexAppServer:
        signature = identity.signature
        if self._server is not None and self._server_identity_signature != signature:
            self._log(
                "app_server_identity_refresh",
                prior_identity=list(self._server_identity_signature or ()),
                next_identity=list(signature),
            )
            self._server.close()
            self._server = None
            self._server_identity_signature = None
        if self._server is None:
            env = {
                "AKASHIC_AGENT_ID": self.policy.agent,
                "AKASHIC_HARNESS": "codex-desktop",
                "AKASHIC_CALLSIGN_HINT": identity.callsign or "",
                "AKASHIC_CALLSIGN_STATUS": identity.status,
            }
            self._server = self.server_factory(
                cwd=self.cwd,
                env=env,
                request_handlers={"item/tool/call": self.handle_dynamic_tool_call},
                experimental_api=self.allow_exec,
            ).start()
            self._server_identity_signature = signature
            self._log(
                "app_server_initialized",
                command=self._server.command,
                pid=self._server.process.pid,
                model_turns=0,
                callsign=identity.callsign or "",
                callsign_status=identity.status,
                identity_authority=identity.authority,
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
            # Resolve exactly once at admission. Prompt, developer instructions, child env,
            # and the causal reply receipt all describe the same identity observation.
            identity = self.identity_resolver(self.policy.agent)
            server = self._app_server(identity)
            thread = server.start_thread(
                ephemeral=True,
                sandbox="read-only",
                cwd=self.cwd,
                model=self.model,
                developer_instructions=wake_developer_instructions(
                    self.policy.agent, identity
                ),
                approval_policy="never",
                personality="friendly",
                dynamic_tools=self.dynamic_tools or None,
            )
            # Durable admission precedes the paid turn: a crash cannot silently
            # redrive the same message and spend twice.
            self.state.record(
                mid,
                outcome="turn_admitted",
                detail="paid turn admitted; automatic redrive disabled",
                thread_id=thread.thread_id,
                peer=message.frm,
                callsign=identity.callsign or "",
                callsign_status=identity.status,
                identity_authority=identity.authority,
            )
            self._log(
                "turn_admitted",
                mid=mid,
                thread_id=thread.thread_id,
                peer=message.frm,
                callsign=identity.callsign or "",
                callsign_status=identity.status,
                identity_authority=identity.authority,
            )
            result = server.run_turn(
                thread.thread_id,
                build_wake_prompt(self.policy.agent, message, identity=identity),
                effort=self.effort,
                model=self.model,
                sandbox_policy={"type": "readOnly", "networkAccess": False},
                timeout=self.turn_timeout,
            )
        except (CodexAppServerError, OSError, ValueError) as exc:
            self.state.record(mid, outcome="turn_failed", detail=str(exc))
            self._log("turn_failed", mid=mid, error=str(exc))
            return {"mid": mid, "outcome": "turn_failed", "error": str(exc)}

        return self._finish(message, result, identity)

    def _finish(
        self,
        message: Message,
        result: TurnResult,
        identity: SubjectIdentity,
    ) -> Dict[str, Any]:
        usage = result.token_usage or {}
        usage_accounting = _usage_accounting(usage)
        if result.status != "completed" or not result.text.strip():
            detail = f"status={result.status!r}; final_text={bool(result.text.strip())}"
            self.state.record(
                message.id,
                outcome="turn_incomplete",
                detail=detail,
                thread_id=result.thread_id,
                turn_id=result.turn_id,
                token_usage=usage,
                usage_accounting=usage_accounting,
            )
            self._log(
                "turn_incomplete",
                mid=message.id,
                detail=detail,
                token_usage=usage,
                usage_accounting=usage_accounting,
            )
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
                "subject_callsign": identity.callsign or "",
                "callsign_status": identity.status,
                "identity_authority": identity.authority,
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
                usage_accounting=usage_accounting,
            )
            self._log(
                "reply_failed",
                mid=message.id,
                detail=detail,
                token_usage=usage,
                usage_accounting=usage_accounting,
            )
            return {"mid": message.id, "outcome": "reply_failed"}

        self.state.record(
            message.id,
            outcome="replied",
            detail="one read-only Codex turn; causal reply link stamped",
            reply_mid=str(reply_mid),
            thread_id=result.thread_id,
            turn_id=result.turn_id,
            token_usage=usage,
            usage_accounting=usage_accounting,
        )
        self._log(
            "replied",
            mid=message.id,
            reply_mid=str(reply_mid),
            thread_id=result.thread_id,
            turn_id=result.turn_id,
            token_usage=usage,
            usage_accounting=usage_accounting,
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
    "DIRECT_ACTION_KINDS",
    "SubjectIdentity",
    "WakeError",
    "WakePolicy",
    "WakeState",
    "build_wake_prompt",
    "current_inbox_tail",
    "decode_exact_message",
    "decode_stream_message",
    "default_runtime_paths",
    "install_signal_stops",
    "resolve_subject_identity",
    "wake_developer_instructions",
]
