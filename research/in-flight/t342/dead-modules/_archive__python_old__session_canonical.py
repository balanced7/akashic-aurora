"""
Canonical session events — single path for all agents (Cursor, Claude, OpenCode).

Appends versioned JSON envelopes to Redis Stream ``session:events`` on the WSL master
and mirrors to ``session_logs/session_events_canonical.jsonl``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import redis

from config import (
    BASE_DIR,
    CANONICAL_EVENTS_JSONL,
    SESSION_EVENTS_STREAM,
    SESSION_NOTE_SCHEMA_VERSION,
    SESSION_STATE_FILE,
    get_redis_config,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_session_id(session_id: str) -> None:
    SESSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if SESSION_STATE_FILE.exists():
        try:
            with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
    state["session_id"] = session_id
    state["updated_at"] = _utc_now()
    with open(SESSION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_persisted_session_id() -> str:
    """Last session id written by MCP or tooling (fallback for new envelopes)."""
    if not SESSION_STATE_FILE.exists():
        return ""
    try:
        with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
            return str(json.load(f).get("session_id") or "")
    except Exception:
        return ""


def build_envelope(
    *,
    session_id: str,
    agent: str,
    event_type: str,
    intent: str = "",
    systems_worked: str = "",
    changes_made: str = "",
    milestones_update: str = "",
    decisions: str = "",
    blockers: str = "",
    next_steps: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SESSION_NOTE_SCHEMA_VERSION,
        "session_id": session_id,
        "agent": agent.strip().lower(),
        "event_type": event_type.strip().lower(),
        "utc_timestamp": _utc_now(),
        "intent": intent.strip(),
        "systems_worked": systems_worked.strip(),
        "changes_made": changes_made.strip(),
        "milestones_update": milestones_update.strip(),
        "decisions": decisions.strip(),
        "blockers": blockers.strip(),
        "next_steps": next_steps.strip(),
        "extra": extra or {},
    }


def _append_jsonl(envelope: Dict[str, Any]) -> None:
    CANONICAL_EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(CANONICAL_EVENTS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(envelope, ensure_ascii=False) + "\n")


def envelope_to_plaintext(env: Dict[str, Any]) -> str:
    """Flatten envelope for Gemma summarization."""
    parts = [
        f"[{env.get('event_type')} | {env.get('agent')} | {env.get('utc_timestamp')}]",
    ]
    for label, key in [
        ("intent", "intent"),
        ("systems", "systems_worked"),
        ("changes", "changes_made"),
        ("milestones", "milestones_update"),
        ("decisions", "decisions"),
        ("blockers", "blockers"),
        ("next_steps", "next_steps"),
    ]:
        val = env.get(key) or ""
        if val.strip():
            parts.append(f"{label}: {val}")
    ex = env.get("extra") or {}
    if ex:
        parts.append("extra: " + json.dumps(ex, ensure_ascii=False)[:500])
    return "\n".join(parts)


def append_session_event(
    *,
    redis_client: Optional[redis.Redis] = None,
    session_id: str,
    agent: str,
    event_type: str,
    intent: str = "",
    systems_worked: str = "",
    changes_made: str = "",
    milestones_update: str = "",
    decisions: str = "",
    blockers: str = "",
    next_steps: str = "",
    extra: Optional[Dict[str, Any]] = None,
    persist_session_state: bool = True,
    mirror_jsonl: bool = True,
) -> Dict[str, Any]:
    """
    XADD to SESSION_EVENTS_STREAM and mirror to JSONL. Returns envelope + redis stream id.
    """
    env = build_envelope(
        session_id=session_id,
        agent=agent,
        event_type=event_type,
        intent=intent,
        systems_worked=systems_worked,
        changes_made=changes_made,
        milestones_update=milestones_update,
        decisions=decisions,
        blockers=blockers,
        next_steps=next_steps,
        extra=extra,
    )
    payload = json.dumps(env, ensure_ascii=False)
    rid = ""

    cli = redis_client
    owns_redis = False
    if cli is None:
        try:
            cli = redis.Redis(**get_redis_config())
            cli.ping()
            owns_redis = True
        except Exception as e:
            env["_error_redis"] = str(e)
            if mirror_jsonl:
                env["_mirror_only"] = True
                _append_jsonl(env)
            if persist_session_state:
                persist_session_id(session_id)
            return {"ok": False, "envelope": env, "stream_id": "", "error": str(e)}

    try:
        rid = cli.xadd(
            SESSION_EVENTS_STREAM,
            {
                "session_id": env["session_id"],
                "agent": env["agent"],
                "event_type": env["event_type"],
                "payload": payload,
            },
        )
    except Exception as e:
        env["_error_xadd"] = str(e)

    if mirror_jsonl:
        _append_jsonl(env)

    if persist_session_state:
        persist_session_id(session_id)

    if owns_redis and cli is not None:
        cli.close()

    ok = bool(rid)
    return {"ok": ok, "envelope": env, "stream_id": rid}


def xrange_tail(
    redis_client: redis.Redis,
    start: str = "-",
    end: str = "+",
    count: Optional[int] = None,
) -> List[Tuple[str, Dict[str, str]]]:
    kwargs = {}
    if count is not None:
        kwargs["count"] = count
    try:
        return redis_client.xrange(SESSION_EVENTS_STREAM, start, end, **kwargs)
    except Exception:
        return []


def xrevrange_scan_for_session(
    redis_client: redis.Redis,
    session_id: str,
    batches: int = 40,
    batch_size: int = 120,
    max_matching: int = 300,
) -> List[Dict[str, Any]]:
    """
    Scan newest-first from the stream until we gather up to ``max_matching`` entries
    matching ``session_id`` (handles large streams without full XRANGE scans).
    """
    out: List[Dict[str, Any]] = []
    cursor_exclusive: Optional[str] = None
    for _ in range(batches):
        if cursor_exclusive:
            chunk = redis_client.xrevrange(
                SESSION_EVENTS_STREAM,
                max=cursor_exclusive,
                min="-",
                count=batch_size,
            )
        else:
            chunk = redis_client.xrevrange(
                SESSION_EVENTS_STREAM, max="+", min="-", count=batch_size
            )
        if not chunk:
            break
        for mid, fields in chunk:
            cursor_exclusive = "(" + mid
            if fields.get("session_id") != session_id:
                continue
            raw = fields.get("payload") or "{}"
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
            if len(out) >= max_matching:
                out.reverse()
                return out
    out.reverse()
    return out


def aggregated_text_for_session(
    redis_client: redis.Redis,
    session_id: str,
) -> str:
    envs = xrevrange_scan_for_session(redis_client, session_id)
    return "\n\n".join(envelope_to_plaintext(e) for e in envs)
