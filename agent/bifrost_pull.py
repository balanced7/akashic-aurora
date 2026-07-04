"""
Bifrost pull-side helpers (System 5 read lane).

boot() surfaces unread bus mail without consuming the cursor; promoted() reads durable
salient messages from the Ledger (B2). Presence is refreshed on boot.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _clip(s: Any, n: int = 220) -> str:
    s = "" if s is None else str(s)
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return (cut or s[:n]) + " ...[truncated]"


def _content_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, default=str)
    except (TypeError, ValueError):
        return str(content)


def register_presence(agent_id: str) -> Dict[str, Any]:
    """Mark agent online + list who else is present. Never raises."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        registered = b.register() if b.online else False
        live = b.presence() if b.online else []
        return {
            "online": b.online,
            "registered": registered,
            "pending": b.pending() if b.online else 0,
            "agents_online": [p.get("agent") for p in live],
        }
    except Exception:
        return {"online": False, "registered": False, "pending": 0, "agents_online": []}


def peek_inbox(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Unread direct+broadcast mail; advance=False so cursor is unchanged."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        if not b.online:
            return []
        msgs = b.inbox(limit=max(1, limit), advance=False)
        out = []
        for m in msgs:
            d = m.to_dict() if hasattr(m, "to_dict") else {}
            out.append({
                "id": d.get("id") or getattr(m, "id", ""),
                "frm": d.get("frm") or getattr(m, "frm", ""),
                "to": d.get("to") or getattr(m, "to", ""),
                "kind": d.get("kind") or getattr(m, "kind", ""),
                "content": d.get("content", getattr(m, "content", "")),
                "ts": d.get("ts") or getattr(m, "ts", ""),
            })
        return out
    except Exception:
        return []


def consume_inbox(agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Read and advance the per-agent cursor (ack)."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(agent_id or "unknown"))
        if not b.online:
            return []
        msgs = b.inbox(limit=max(1, limit), advance=True)
        return [m.to_dict() if hasattr(m, "to_dict") else {} for m in msgs]
    except Exception:
        return []


def peek_locks(agent_id: str) -> List[Dict[str, Any]]:
    """Advisory path-locks currently held (C2 awareness). Never raises."""
    try:
        from core.comm.locks import LockManager
        return LockManager(str(agent_id or "viewer")).list_locks()
    except Exception:
        return []


def collect_boot_bifrost(agent_id: str, limit: int = 8) -> Dict[str, Any]:
    """Presence + unread peek + held locks for boot() / bifrost-sync."""
    pres = register_presence(agent_id)
    msgs = peek_inbox(agent_id, limit=limit)
    return {
        "bus_online": pres["online"],
        "presence_registered": pres["registered"],
        "agents_online": pres["agents_online"],
        "pending": len(msgs),
        "messages": msgs,
        "locks": peek_locks(agent_id),
    }


def format_inbox_line(msg: Dict[str, Any], max_len: int = 220) -> str:
    frm = msg.get("frm", "?")
    kind = msg.get("kind", "?")
    body = _clip(_content_str(msg.get("content")), max_len)
    return f"[{kind}] from {frm}: {body}"


def format_digest_line(msg: Dict[str, Any]) -> str:
    """Ultra-compact one-liner for a cheap scan: kind, sender, a 64-char teaser.
    The full body is one drill away (`bifrost-sync` without --digest, or --json)."""
    frm = msg.get("frm", "?")
    kind = msg.get("kind", "?")
    ts = (msg.get("ts") or "")[11:16]   # HH:MM
    teaser = _clip(_content_str(msg.get("content")), 64)
    return f"  {ts} [{kind}] {frm}> {teaser}"


def print_boot_bifrost_section(block: Dict[str, Any]) -> None:
    print("\n## UNREAD BIFROST (live bus)")
    if not block.get("bus_online"):
        print("  (bus OFFLINE -- Redis unreachable; durable mail still in promoted() / events)")
        return
    online = block.get("agents_online") or []
    if online:
        print(f"  online: {', '.join(online)}")
    pending = block.get("pending") or 0
    if pending == 0:
        print("  (no new messages -- peek only; cursor unchanged)")
        return
    print(f"  {pending} unread (peek -- use bifrost_inbox or `py agent_cli.py bifrost-sync --consume` to ack):")
    for msg in block.get("messages") or []:
        print(f"  {format_inbox_line(msg)}")


def print_boot_locks_section(block: Dict[str, Any], agent_id: str = "") -> None:
    """Awareness: who holds which advisory path-locks (only prints if any are held)."""
    locks = block.get("locks") or []
    if not locks:
        return
    print("\n## ADVISORY PATH-LOCKS (who's editing what -- C2)")
    for lk in locks:
        mine = " (you)" if lk.get("agent") == agent_id else ""
        print(f"  {lk.get('path')}  <- {lk.get('agent')}{mine}  token {lk.get('token')}")


def format_promoted_events(events: List[Dict[str, Any]], *, json_out: bool = False) -> str:
    if json_out:
        return json.dumps(events, indent=2, default=str)
    if not events:
        return "# 0 durable Bifrost message(s) (kind=bifrost_msg)"
    lines = [f"# {len(events)} durable Bifrost message(s) (salient bus -> Ledger)"]
    for ev in events:
        d = ev.get("detail") or {}
        at = (ev.get("at") or d.get("ts") or "")[:19]
        frm, to, kind = d.get("frm", "?"), d.get("to", "?"), d.get("kind", "?")
        body = _clip(_content_str(d.get("content")), 200)
        ref = ev.get("_ref") or ev.get("id") or ""
        lines.append(f"  [{kind}] {frm} -> {to}  {at}")
        lines.append(f"    {body}")
        if ref:
            lines.append(f"    ref: {ref}")
    lines.append("\nDrill: py agent_cli.py events --get <ref>")
    return "\n".join(lines)


def format_console_events(events: List[Dict[str, Any]], *, json_out: bool = False) -> str:
    """Render durable console control-plane events (interjection/bus_control/file_drop) for the CLI."""
    if json_out:
        return json.dumps(events, indent=2, default=str)
    if not events:
        return "# 0 durable console event(s) (interjection / bus_control / file_drop)"
    lines = [f"# {len(events)} durable console event(s) (live cockpit -> Ledger)"]
    for ev in events:
        d = ev.get("detail") or {}
        kind = ev.get("kind", "?")
        at = (ev.get("at") or "")[:19]
        ref = ev.get("_ref") or ev.get("id") or ""
        if kind == "interjection":
            head = f"  [interjection:{d.get('intent','?')}] user -> {d.get('to','?')}  {at}"
            body = _clip(_content_str(d.get("text")), 200)
        elif kind == "bus_control":
            head = f"  [control] {d.get('by','user')} {d.get('action','?')}  {at}"
            body = _clip(_content_str(d.get("reason", "")), 200) or "(no reason)"
        elif kind == "file_drop":
            head = f"  [file_drop] {d.get('by','user')} shared  {at}"
            body = f"{d.get('path','?')} ({d.get('bytes','?')} bytes)"
        else:
            head = f"  [{kind}]  {at}"
            body = _clip(_content_str(ev.get("summary", "")), 200)
        lines.append(head)
        lines.append(f"    {body}")
        if ref:
            lines.append(f"    ref: {ref}")
    lines.append("\nDrill: py agent_cli.py events --get <ref>")
    return "\n".join(lines)
