"""Shared Codex hook translation primitives.

Codex and Claude expose similarly named lifecycle events, but their tool and outcome
payloads are not interchangeable.  This module is the explicit Codex boundary: event-scoped
seat resolution, canonical ``apply_patch`` path extraction, bounded raw-payload capture, and
cross-config duplicate suppression.  It contains no model calls and consumes no bus cursor.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


_STATE_ROOT = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(
    tempfile.gettempdir(), "akashic_recall"
)
_CAP_DIR = os.path.join(_STATE_ROOT, "codex_payloads")
_DEDUP_DIR = os.path.join(_STATE_ROOT, "codex_hook_dedup")
_DEDUP_WINDOW_S = 4.0
_PATCH_PATH = re.compile(
    r"^\*\*\* (?:Add File|Update File|Delete File|Move to):\s*(.+?)\s*$",
    re.MULTILINE,
)


def resolve_seat(session_id: str) -> str:
    """Resolve the event's session binding before ambient process identity."""
    try:
        from core.comm.seat_identity import resolve

        return str(resolve(str(session_id or "")) or "unknown")
    except Exception:
        return (os.getenv("AKASHIC_AGENT_ID") or "").strip() or "unknown"


def event_seat(data: Dict[str, Any]) -> str:
    return resolve_seat(str(data.get("session_id") or ""))


def ratified_callsign(seat: str) -> str:
    """Registry truth only; absence is not silently replaced with a hint."""
    try:
        from core.fleet import residents

        return str((residents.get(seat) or {}).get("callsign") or "").strip()
    except Exception:
        return ""


def subject_context(seat: str, session_id: str) -> str:
    """Bounded identity activation block with explicit epistemic status.

    ``AKASHIC_CALLSIGN_HINT`` is deliberately rendered as a hint, never as registry truth.
    This lets an unratified but historically load-bearing name survive cold start without
    bypassing the peer-nomination/human-ratification ceremony.
    """
    seat = str(seat or "unknown")
    sid = str(session_id or "")
    lines = [
        "# AKASHIC IDENTITY (subject-bound)",
        f"subject: {seat}",
        f"session: {sid or 'unknown'}",
        "harness: codex-desktop",
    ]
    ratified = ratified_callsign(seat)
    if ratified:
        lines.append(f"ratified callsign: {ratified}")
    else:
        hint = (os.getenv("AKASHIC_CALLSIGN_HINT") or "").strip()
        if hint:
            status = (os.getenv("AKASHIC_CALLSIGN_STATUS") or "unratified-hint").strip()
            lines.append(f"callsign history: {hint} [{status}; not registry authority]")
    pointer = (os.getenv("AKASHIC_IDENTITY_POINTER") or "").strip()
    if pointer:
        pointer_subject = (os.getenv("AKASHIC_IDENTITY_POINTER_SUBJECT") or "").strip()
        if pointer_subject == seat:
            lines.append(f"identity-history pointer [subject={pointer_subject}]: {pointer}")
        else:
            lines.append(
                "identity-history pointer: REFUSED (missing or mismatched subject declaration; "
                f"declared={pointer_subject or 'UNKNOWN'}, active={seat})"
            )
    lines.append(
        "first law: attribution is not verification; before adopting a receipt, ask "
        "whether its subject is you."
    )
    return "\n".join(lines)


def subject_label(data: Dict[str, Any], seat: str | None = None) -> str:
    seat = seat or event_seat(data)
    return f"[akashic subject={seat} session={str(data.get('session_id') or 'unknown')}]"


def dedup_should_skip(data: Dict[str, Any]) -> bool:
    """Atomically suppress the duplicate caused by merged user and repo hook sources."""
    try:
        key_material = [
            data.get("session_id", ""),
            data.get("turn_id", ""),
            data.get("hook_event_name", ""),
            data.get("tool_name", ""),
            data.get("tool_use_id", ""),
            data.get("source", ""),
            data.get("prompt", ""),
            data.get("tool_input", {}),
        ]
        key = hashlib.sha256(
            json.dumps(key_material, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:32]
        os.makedirs(_DEDUP_DIR, exist_ok=True)
        now = time.time()
        try:
            for name in os.listdir(_DEDUP_DIR):
                path = os.path.join(_DEDUP_DIR, name)
                if now - os.path.getmtime(path) > 60:
                    os.remove(path)
        except Exception:
            pass
        marker = os.path.join(_DEDUP_DIR, key)
        try:
            fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return False
        except FileExistsError:
            return now - os.path.getmtime(marker) < _DEDUP_WINDOW_S
    except Exception:
        return False


def capture_payload(data: Dict[str, Any]) -> None:
    """Best-effort bounded capture; diagnostics can never block the lifecycle event."""
    try:
        from agent.harness.capture import capture

        event = str(data.get("hook_event_name") or "event").lower()
        tool = str(data.get("tool_name") or "lifecycle").lower()
        capture(data, _CAP_DIR, label=f"codex-{event}-{tool}")
    except Exception:
        pass


def _absolute_patch_path(raw: str, cwd: str) -> str:
    raw = str(raw or "").strip().strip('"')
    path = Path(raw)
    if not path.is_absolute():
        path = Path(cwd or os.getcwd()) / path
    return os.path.normpath(str(path))


def action_paths(data: Dict[str, Any]) -> List[str]:
    if str(data.get("tool_name") or "") != "apply_patch":
        return []
    ti = data.get("tool_input")
    command = str(ti.get("command") or "") if isinstance(ti, dict) else ""
    cwd = str(data.get("cwd") or os.getcwd())
    out: List[str] = []
    for raw in _PATCH_PATH.findall(command):
        path = _absolute_patch_path(raw, cwd)
        if path not in out:
            out.append(path)
    return out


def action_targets(data: Dict[str, Any]) -> List[str]:
    from core.recall.at_action import normalize_target

    tool = str(data.get("tool_name") or "")
    ti = data.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    if tool == "Bash":
        target = normalize_target(command=str(ti.get("command") or ""))
        return [target] if target else []
    if tool == "apply_patch":
        return [normalize_target(path=path) for path in action_paths(data)]
    return []


def in_scope_paths(data: Dict[str, Any]) -> List[str]:
    try:
        from agent.harness.scope import file_in_scope

        return [path for path in action_paths(data) if file_in_scope(path)]
    except Exception:
        return []


def event_in_scope(data: Dict[str, Any]) -> bool:
    tool = str(data.get("tool_name") or "")
    if tool == "apply_patch":
        return bool(in_scope_paths(data))
    if tool == "Bash":
        try:
            from agent.harness.scope import shell_in_scope

            ti = data.get("tool_input")
            ti = ti if isinstance(ti, dict) else {}
            return shell_in_scope(
                str(data.get("cwd") or os.getcwd()), str(ti.get("command") or "")
            )
        except Exception:
            return False
    return False


def touch_working(seat: str, session_id: str) -> None:
    """Liveness belongs above adapter filters; a silent recall is still a live seat."""
    if not seat or seat == "unknown" or not session_id:
        return
    try:
        from core.comm.bus import NS
        from core.comm import roster

        roster.heartbeat(NS, seat, session_id, phase="working")
    except Exception:
        pass
    try:
        from core.comm import wake_seat

        wake_seat.touch_activity(seat, session_id)
    except Exception:
        pass
