"""pager -- page-grade findings reach a HUMAN (T078-W4, the 6h-invisible killer).

A PAGE is louder than a bus blocker: breaker trips, runner down past the
escalation window, storm gauges. Writers (daemon A3 escalation, doctor, gauges)
call page(); ONE capped Redis list holds them; the UserPromptSubmit hook injects
[PAGE] lines into any live seat. Seat doctrine: a live claude seat that sees a
[PAGE] line relays it via the harness PushNotification tool (desktop + phone) --
the harness tool cannot be called from daemon python, so the seat is the relay.
The unattended path (no live seat anywhere) is wave-2's scheduled-session anchor.

Fail-open everywhere; the pager must never wedge a writer.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

CAP = 50


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _key() -> str:
    return f"{_ns()}:pages"


def _client(c=None, allow_fallback: bool = True):
    if c is not None:
        return c
    if not allow_fallback:
        return None
    try:
        from core.comm.bus import get_bus
        return get_bus("control")._client
    except Exception:
        return None


def page(agent: str, text: str, c=None, allow_fallback: bool = True,
         key: str = "") -> bool:
    """Record a page-grade finding. Newest-first, capped at CAP (oldest drop).

    `key` identifies WHAT is being paged about -- conventionally "<agent>:<state>" -- so the
    writer can retract this page when the condition resolves. Without it the only retraction
    is fleet-wide ack_pages(), which discards other agents' LIVE pages; the 2026-07-27 receipt
    is a resolved lane_stall that rendered into every prompt for nine hours because clearing it
    would have thrown away a real one. Optional: a keyless page behaves exactly as before.
    """
    cli = _client(c, allow_fallback)
    if cli is None:
        return False
    try:
        rec = {"ts": time.time(), "agent": str(agent), "text": str(text)[:400]}
        if key:
            rec["key"] = str(key)
        cli.lpush(_key(), json.dumps(rec))
        cli.ltrim(_key(), 0, CAP - 1)
        return True
    except Exception:
        return False


def clear_key(key: str, c=None, allow_fallback: bool = True) -> int:
    """Retract every page carrying `key`; leave all others standing. Returns the count removed.

    A page channel that cannot retract is a channel that teaches people to ignore it -- the
    same banner-blindness that lets a real page go unread. Retraction is what keeps the
    channel worth reading."""
    cli = _client(c, allow_fallback)
    if cli is None or not key:
        return 0
    try:
        kept, removed = [], 0
        for raw in cli.lrange(_key(), 0, -1):
            try:
                rec = json.loads(raw)
            except Exception:
                kept.append(raw)             # unparseable: keep, never silently drop
                continue
            if rec.get("key") == str(key):
                removed += 1
            else:
                kept.append(raw)
        if not removed:
            return 0
        cli.delete(_key())
        for raw in reversed(kept):           # lpush reverses; restore original order
            cli.lpush(_key(), raw)
        return removed
    except Exception:
        return 0


def unread_pages(c=None, allow_fallback: bool = True) -> List[Dict[str, Any]]:
    """Peek (never consumes) -- newest first."""
    cli = _client(c, allow_fallback)
    if cli is None:
        return []
    try:
        out = []
        for raw in cli.lrange(_key(), 0, -1):
            try:
                out.append(json.loads(raw))
            except Exception:
                continue
        return out
    except Exception:
        return []


def ack_pages(c=None, allow_fallback: bool = True) -> bool:
    """Clear after relay. Idempotent."""
    cli = _client(c, allow_fallback)
    if cli is None:
        return False
    try:
        cli.delete(_key())
        return True
    except Exception:
        return False


def hook_lines(c=None, allow_fallback: bool = True, now: Optional[float] = None) -> List[str]:
    """Render for hook injection: '[PAGE] agent: text (Nm ago)'. Empty = silent."""
    now_f = float(now if now is not None else time.time())
    lines = []
    for p in unread_pages(c, allow_fallback):
        age_m = max(0, int((now_f - float(p.get("ts") or now_f)) / 60))
        lines.append(f"[PAGE] {p.get('agent', '?')}: {p.get('text', '')} ({age_m}m ago) "
                     f"-- relay via PushNotification if Daniel may be away, then ack")
    return lines
