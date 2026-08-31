"""Pure, bounded awareness providers and the composite ``sweep`` snapshot.

This module deliberately does not call the boot/sync surfaces.  Those surfaces
maintain presence, heartbeats, and expectations; an observer must not make the
subject look alive merely by looking at it.
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from core.coord.observations import Observation, Snapshot


DEFAULT_ORDER = ("bus", "bench", "route", "moved")


def _redis_client():
    try:
        from core.foundation.redis_connection import (
            DEFAULT_REDIS_HOST,
            DEFAULT_REDIS_PORT,
            connect_to_redis_with_fail_fast,
        )
        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST,
            port=DEFAULT_REDIS_PORT,
            timeout_seconds=3,
            decode_responses=True,
        )
    except Exception:
        return None


def _loads(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _sid(value: Any) -> tuple[int, int]:
    head, _, tail = str(value or "0").partition("-")
    try:
        return int(head), int(tail or 0)
    except ValueError:
        return 0, 0


def _max_sid(a: Any, b: Any) -> str:
    return str(a) if _sid(a) >= _sid(b) else str(b)


def _effective_cursor(client, namespace: str, subject: str) -> Dict[str, str]:
    shared = client.hgetall(f"{namespace}:cursor:{subject}") or {}
    lane = client.hgetall(f"{namespace}:cursor:lane:{subject}") or {}
    return {
        "inbox": _max_sid(shared.get("inbox", "0"), lane.get("shadow_inbox", "0")),
        "bc": _max_sid(shared.get("bc", "0"), lane.get("shadow_bc", "0")),
    }


def _decode_row(subject: str, stream: str, sid: Any, fields: Mapping[str, Any]):
    """Decode one packet without reassembly, receipts, logging, or any write edge."""
    try:
        from core.comm import packet_spec
        valid, _reason = packet_spec.verify_integrity(dict(fields))
        if not valid:
            return None, "integrity"
        if packet_spec.parse_frag(dict(fields)) is not None:
            return None, "fragment"
    except Exception:
        return None, "decode"
    meta = _loads(fields.get("meta")) or {}
    if not isinstance(meta, dict):
        meta = {}
    frm = str(fields.get("frm") or "")
    if stream == "bc" and frm == subject:
        # FOUND 2026-08-31: this returned a bare None instead of the (None, why) pair
        # every other early-return here uses, so `row, why = _decode_row(...)` blew up
        # with "cannot unpack non-iterable NoneType object" the moment the subject had
        # a broadcast of its own sitting in the peeked window -- sweep/awareness then
        # reported the whole bus UNAVAILABLE. Independently reproduced; matches
        # deepseek's 2026-08-29 bus_redelivery_loop_masquerades_as_reasks report.
        return None, "own_broadcast"
    if fields.get("sha") and "sha" not in meta:
        meta["sha"] = str(fields.get("sha"))
    return {
        "id": str(sid),
        "frm": frm,
        "to": str(fields.get("to") or ""),
        "kind": str(fields.get("kind") or ""),
        "content": _loads(fields.get("content")),
        "ts": str(fields.get("ts") or ""),
        "meta": meta,
        "_stream": stream,
    }, ""


def peek_unread(subject: str, limit: int = 10, *, client=None,
                namespace: Optional[str] = None) -> list[Dict[str, Any]]:
    """Read a freshness window without touching presence, cursors, or receipts.

    Only Redis read operations are used.  Fragment packets are not reassembled here:
    reassembly is consumer work and persists state.  A cap hit therefore remains an
    ``at_least`` claim, never an exact total.
    """
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("subject is required")
    store = client if client is not None else _redis_client()
    if store is None:
        return []
    ns = str(namespace or os.environ.get("BIFROST_NAMESPACE", "bifrost"))
    want = max(1, int(limit or 10))
    cap = max(want * 5, 50)
    cursors = _effective_cursor(store, ns, subject)
    streams = (
        ("inbox", f"{ns}:inbox:{subject}", cursors["inbox"]),
        ("bc", f"{ns}:broadcast", cursors["bc"]),
    )
    seen: Dict[tuple[str, str], Dict[str, Any]] = {}
    packet_seen = set()
    capped = False
    skipped = {"fragment": 0, "integrity": 0, "decode": 0}
    for stream, key, cursor in streams:
        minimum = f"({cursor}" if str(cursor) not in ("0", "0-0") else "-"
        forward = store.xrange(key, min=minimum, max="+", count=cap + 1) or []
        if len(forward) > cap:
            capped = True
            forward = forward[:cap]
        tail = store.xrevrange(key, max="+", min=minimum, count=want) or []
        for sid, fields in list(forward) + list(tail):
            packet_key = (stream, str(sid))
            if packet_key in packet_seen:
                continue
            packet_seen.add(packet_key)
            row, why = _decode_row(subject, stream, sid, fields)
            if row is not None:
                seen[packet_key] = row
            elif why in skipped:
                skipped[why] += 1

    merged = sorted(
        seen.values(),
        key=lambda row: (_sid(row["id"]), row["_stream"]),
    )
    total = len(merged)
    if total > want:
        oldest_n = max(1, want // 4) if want > 1 else 0
        newest_n = want - oldest_n
        head = merged[:oldest_n]
        tail = merged[-newest_n:] if newest_n else []
        hidden = total - len(head) - len(tail)
    else:
        head, tail, hidden = merged, [], 0

    out: list[Dict[str, Any]] = []
    degraded_n = sum(skipped.values())

    def append_row(row):
        clean = {k: v for k, v in row.items() if not k.startswith("_")}
        clean.update({
            "pending_at_least": total,
            "pending_capped": capped or degraded_n > 0,
            "observation_order": "oldest+newest" if hidden or capped else "oldest",
            "unrendered_entries": degraded_n,
        })
        out.append(clean)

    for row in head:
        append_row(row)
    if hidden:
        out.append({
            "gap": True,
            "display_only": True,
            "id": "",
            "frm": "backlog",
            "to": subject,
            "kind": "gap",
            "content": f"(... {hidden} unread hidden between oldest and newest)",
            "ts": "",
            "pending_at_least": total,
            "pending_capped": capped or degraded_n > 0,
            "observation_order": "oldest+newest",
            "unrendered_entries": degraded_n,
        })
    for row in tail:
        append_row(row)
    if degraded_n:
        out.append({
            "gap": True,
            "display_only": True,
            "id": "",
            "frm": "observer",
            "to": subject,
            "kind": "gap",
            "content": (
                f"(... {degraded_n} packet entries not rendered by the pure observer: "
                f"fragments={skipped['fragment']}, integrity={skipped['integrity']}, "
                f"decode={skipped['decode']})"
            ),
            "ts": "",
            "pending_at_least": total,
            "pending_capped": True,
            "observation_order": "oldest+newest" if hidden or capped else "oldest",
            "unrendered_entries": degraded_n,
        })
    return out


def _presence(subject: str) -> Dict[str, Any]:
    store = _redis_client()
    if store is None:
        return {
            "bus_online": False,
            "agents_online": [],
            "agents_registered_unattended": [],
        }
    ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
    attended, unattended = [], []
    try:
        keys = store.keys(f"{ns}:presence:*") or []
    except Exception:
        keys = []
    for key in keys:
        name = str(key).rsplit(":", 1)[-1]
        try:
            from core.comm.liveness import attendance
            state = attendance(name).state
        except Exception:
            state = "UNKNOWN"
        (attended if state == "ATTENDED" else unattended).append(name)
    return {
        "bus_online": True,
        "agents_online": sorted(set(attended)),
        "agents_registered_unattended": sorted(set(unattended)),
    }


def observe_bus(subject: str, limit: int = 10, *, peek_fn=None,
                presence_fn=None) -> Observation:
    rows = (peek_fn or peek_unread)(subject, limit)
    presence = (presence_fn or _presence)(subject)
    real = [row for row in rows if not row.get("gap")]
    total = max((int(row.get("pending_at_least", 0) or 0) for row in rows), default=0)
    capped = any(bool(row.get("pending_capped")) for row in rows)
    unrendered = max((int(row.get("unrendered_entries", 0) or 0) for row in rows), default=0)
    # T332: this is the existing attention bucket, not a fourth definition of
    # "ask".  In particular, blocker needs attention and kind=ask is retired.
    from agent.bifrost_pull import kind_summary
    attention = int(kind_summary(real).get("asks", 0))
    shown = len(real)
    relation = "at_least" if capped else "exact"
    prefix = ">=" if relation == "at_least" else ""
    online = list(presence.get("agents_online") or [])
    status = "OK" if presence.get("bus_online") else "UNAVAILABLE"
    summary = (
        f"{prefix}{total} pending; {shown} shown; {attention} need attention; "
        f"online={','.join(online) if online else 'none'}"
    )
    return Observation(
        name="bus",
        subject=subject,
        status=status,
        summary=summary,
        source=("redis:xrange/xrevrange", "core.comm.liveness.attendance"),
        total=total,
        total_relation=relation,
        shown=shown,
        order=(str(real[0].get("observation_order")) if real else "oldest"),
        truncated=(capped or total > shown or any(row.get("gap") for row in rows)),
        effects=(),
        details={
            "attention_shown": attention,
            "unrendered_entries": unrendered,
            "agents_online": online,
            "agents_registered_unattended": list(
                presence.get("agents_registered_unattended") or []
            ),
            "bus_online": bool(presence.get("bus_online")),
        },
        drill=f"bifrost-sync {subject} --digest",
    )


def observe_bench(subject: str) -> Observation:
    store = _redis_client()
    if store is None:
        return Observation(
            name="bench", subject=subject, status="UNAVAILABLE",
            summary="bus unavailable; parked count unknown",
            source=("redis:llen",), effects=(),
            drill=f"bench {subject}",
        )
    ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
    parked = int(store.llen(f"{ns}:triage:{subject}") or 0)
    return Observation(
        name="bench", subject=subject, status="OK",
        summary=f"{parked} parked", source=("redis:llen",),
        total=parked, total_relation="exact", shown=0,
        order="not_rendered", truncated=parked > 0, effects=(),
        drill=f"bench {subject}",
    )


def observe_route(subject: str) -> Observation:
    from core.comm.liveness import attendance, live_incarnations

    verdict = attendance(subject)
    incarnations = list(live_incarnations(subject) or [])
    suffix = f"; incarnations={','.join(incarnations)}" if incarnations else ""
    return Observation(
        name="route", subject=subject, status=verdict.state,
        summary=f"{verdict.state}: {verdict.reason}{suffix}",
        source=("core.comm.liveness.attendance", "core.comm.liveness.live_incarnations"),
        effects=(), details={
            "state": verdict.state,
            "reason": verdict.reason,
            "beat_age_s": verdict.beat_age_s,
            "incarnations": incarnations,
        },
        drill=f"roster --agent {subject}",
    )


def observe_moved(subject: str) -> Observation:
    from agent.harness.delta import DeltaMark, FIELDS, current_positions

    mark = DeltaMark(subject).read()
    current = current_positions(subject)
    if mark is None:
        return Observation(
            name="moved", subject=subject, status="UNKNOWN",
            summary="mark absent; movement unknown",
            source=("agent.harness.delta.DeltaMark.read", "agent.harness.delta.current_positions"),
            effects=(), details={"mark": None, "current": current},
            drill=f"delta {subject}",
        )
    moved = {
        field: (str(mark.get(field, "?")) != str(current.get(field, "?"))
                and "?" not in (str(mark.get(field, "?")), str(current.get(field, "?"))))
        for field in FIELDS
    }
    labels = (
        ("git", "git_commit"),
        ("ledger", "ledger_seq"),
        ("notes", "notes_head"),
        ("promoted", "promoted_id"),
    )
    summary = "; ".join(f"{label}={1 if moved[field] else 0}" for label, field in labels)
    return Observation(
        name="moved", subject=subject, status="OK", summary=summary,
        source=("agent.harness.delta.DeltaMark.read", "agent.harness.delta.current_positions"),
        effects=(), details={"mark": mark, "current": current, "moved": moved},
        drill=f"delta {subject}",
    )


def _unavailable(name: str, subject: str, exc: Exception) -> Observation:
    return Observation(
        name=name,
        subject=subject,
        status="UNAVAILABLE",
        summary=f"{type(exc).__name__}: {str(exc)[:120]}",
        source=(f"provider:{name}",),
        effects=(),
    )


def build_snapshot(subject: str, *, providers: Optional[Mapping[str, Callable]] = None
                   ) -> Snapshot:
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("awareness subject is required")
    selected: Dict[str, Callable[[str], Observation]] = {
        "bus": observe_bus,
        "bench": observe_bench,
        "route": observe_route,
        "moved": observe_moved,
    }
    selected.update(dict(providers or {}))

    def observe_one(name: str) -> Observation:
        try:
            row = selected[name](subject)
            if row.name != name:
                raise ValueError(f"provider {name!r} returned observation {row.name!r}")
            return row
        except Exception as exc:  # observability fails one provider open, never the block
            return _unavailable(name, subject, exc)

    # Providers are pure and independent.  Run them concurrently, then restore the
    # declared order: one slow store must not make four sequential timeouts feel like
    # one convenient verb.
    with ThreadPoolExecutor(max_workers=len(DEFAULT_ORDER),
                            thread_name_prefix="awareness") as pool:
        rows = list(pool.map(observe_one, DEFAULT_ORDER))
    return Snapshot(kind="awareness", subject=subject, observations=tuple(rows))


def _effects_text(effects: Sequence[str]) -> str:
    return ",".join(effects) if effects else "none"


def render_snapshot(snapshot: Snapshot) -> str:
    lines = [
        f"# sweep subject={snapshot.subject} as_of={snapshot.observed_at} "
        f"effects={_effects_text(snapshot.effects)}"
    ]
    for row in snapshot.observations:
        if row.name == "bus" and row.total is not None:
            prefix = ">=" if row.total_relation == "at_least" else ""
            lines.append(
                f"  bus: {row.status} {prefix}{row.total} pending; {row.shown or 0} shown; "
                f"order={row.order}; truncated={'yes' if row.truncated else 'no'}; "
                f"attention_shown={row.details.get('attention_shown', 0)}; "
                f"unrendered={row.details.get('unrendered_entries', 0)}"
            )
        else:
            lines.append(f"  {row.name}: {row.status} {row.summary}")
    return "\n".join(lines)
