"""quarantine -- admitted link records land on `bifrost:remote:<link>`, never on an inbox.

The daemon admits a record when it is authentic, its author may write, and its feed is in order
(aurora-rs/link/src/engine.rs). Admission says nothing about authority over our agents: that is a
separate, local decision (promote.py). So admitted records go to a per-link quarantine stream that
no seat reads by default -- never to `bifrost:inbox:*` or `bifrost:broadcast` (ADR 0008, sharpened
by RFC #70 §7.6).

The stream is a rebuildable view (ADR 0004): the daemon's SQLite store is the durable copy, and
`rebuild()` replays it. The pump keeps one cursor per link in `state/link/cursors.json`, so a
restart neither loses nor repeats what it already queued.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from core.link.client import Client, state_dir

if TYPE_CHECKING:
    from pathlib import Path

MAXLEN = 10_000


def stream_key(link_id: str, ns: str | None = None) -> str:
    """The quarantine stream of one link, in the bus namespace."""
    return f"{ns or os.environ.get('BIFROST_NAMESPACE', 'bifrost')}:remote:{link_id}"


def redis_client() -> Any | None:
    """The canonical Redis client, or None when the bus is offline (the store still has it all)."""
    try:
        from core.foundation.redis_connection import (
            DEFAULT_REDIS_HOST,
            DEFAULT_REDIS_PORT,
            connect_to_redis_with_fail_fast,
        )

        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=3, decode_responses=True
        )
    except Exception:  # noqa: BLE001  # fail-soft: offline bus = None, the store stays the truth
        return None


def fields(event: dict[str, Any]) -> dict[str, str]:
    """One admitted record as stream fields. Provenance comes from the daemon's ACL, never from
    the record body: `fleet` is the member's label in the log, `seat_claim` is only a claim."""
    body = event.get("body") or {}
    return {
        "record_id": str(event.get("record_id", "")),
        "link": str(event.get("link", "")),
        "link_name": str(event.get("link_name", "")),
        "fleet": str(event.get("fleet", "")),
        "fleet_root": str(event.get("fleet_root", "")),
        "device": str(event.get("device", "")),
        "seat_claim": str(body.get("seat", "")),
        "kind": str(body.get("kind", "")),
        "to": str(body.get("to", "")),
        "content": str(body.get("content", "")),
        "reply_to": str(body.get("reply_to") or ""),
        "blobs": json.dumps(body.get("blobs") or []),
        "sent_at": str(body.get("sent_at", "")),
        "received_at": str(event.get("received_at", "")),
        "cursor": str(event.get("cursor", "")),
        "authority": "none",
    }


def admit(events: list[dict[str, Any]], r: Any | None = None) -> int:
    """XADD each event to its link's quarantine stream. Returns how many were queued."""
    r = r if r is not None else redis_client()
    if r is None or not events:
        return 0
    for e in events:
        r.xadd(stream_key(str(e["link"])), fields(e), maxlen=MAXLEN, approximate=True)
    return len(events)


def cursors_path(home: Path | None = None) -> Path:
    return state_dir(home) / "cursors.json"


def load_cursors(home: Path | None = None) -> dict[str, int]:
    try:
        raw = json.loads(cursors_path(home).read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in raw.items()}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def save_cursors(cursors: dict[str, int], home: Path | None = None) -> None:
    path = cursors_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cursors, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def pump_once(
    client: Client, *, timeout_ms: int = 5000, r: Any | None = None, home: Path | None = None
) -> list[dict[str, Any]]:
    """Wait for admitted records past our cursors, queue them, advance the cursors. A record is
    queued before its cursor moves, so a crash can repeat one (promotion is idempotent by record
    id) but never skip one. With the bus offline nothing advances: the store keeps everything."""
    r = r if r is not None else redis_client()
    if r is None:
        return []
    cursors = load_cursors(home)
    events = (client.call("events.wait", cursors=cursors, timeout_ms=timeout_ms) or {}).get("events") or []
    if not events:
        return []
    admit(events, r)
    for e in events:
        link = str(e["link"])
        cursors[link] = max(cursors.get(link, 0), int(e.get("cursor") or 0))
    save_cursors(cursors, home)
    return events


def inbox(client: Client, link: str, *, limit: int = 20, r: Any | None = None) -> list[dict[str, str]]:
    """The newest quarantined records of one link: from the stream, or from the store when the bus
    is offline."""
    status = client.call("link.status", link=link)
    link_id = status["link"]
    r = r if r is not None else redis_client()
    if r is not None:
        rows = r.xrevrange(stream_key(link_id), count=limit)
        if rows:
            return [{"stream_id": sid, **f} for sid, f in rows]
    events = (client.call("events.wait", cursors={link_id: 0}, limit=1000) or {}).get("events") or []
    return [fields(e) for e in events if e.get("link") == link_id][-limit:][::-1]


def rebuild(client: Client, link: str, r: Any | None = None) -> int:
    """Rebuild one link's quarantine stream from the daemon's store (ADR 0004)."""
    r = r if r is not None else redis_client()
    if r is None:
        raise RuntimeError("the bus is offline; nothing to rebuild into (the store still holds every record)")
    link_id = client.call("link.status", link=link)["link"]
    r.delete(stream_key(link_id))
    cursor, total = 0, 0
    while True:
        batch = (client.call("events.wait", cursors={link_id: cursor}, limit=1000) or {}).get("events") or []
        batch = [e for e in batch if e.get("link") == link_id]
        if not batch:
            break
        total += admit(batch, r)
        cursor = max(int(e.get("cursor") or 0) for e in batch)
    cursors = load_cursors()
    cursors[link_id] = cursor
    save_cursors(cursors)
    return total
