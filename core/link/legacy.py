"""legacy -- the cutover's import: mail the old HMAC bridge parked becomes `legacy` quarantine records.

RFC #70 Phase 6 retires the HMAC door. What it already admitted is not thrown away: each parked row
of `state/coord/remote_bridge_inbox.jsonl` goes to the `bifrost:remote:legacy` stream, with the same
provenance it had (`remote:<route>` named by the key that verified it, the sender's own `frm` kept
only as `claimed_frm`) and `verified=false`, because a shared HMAC secret never proved a fleet the
way a link's signatures do. Promotion is the same person's decision as for link mail.

Idempotent: imported ids are remembered in `state/link/legacy_imported.json`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.link import quarantine
from core.link.client import state_dir
from core.link.kinds import BRIDGE_KINDS
from core.paths import data_root

LEGACY = "legacy"


def inbox_file() -> Path:
    """Where the old bridge parked admitted mail (its AKASHIC_REMOTE_BRIDGE_INBOX override kept)."""
    return Path(
        os.getenv("AKASHIC_REMOTE_BRIDGE_INBOX") or data_root() / "state" / "coord" / "remote_bridge_inbox.jsonl"
    )


def _done_file() -> Path:
    return state_dir() / "legacy_imported.json"


def _done() -> set[str]:
    try:
        return set(json.loads(_done_file().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return set()


def parked_rows() -> list[dict[str, Any]]:
    try:
        lines = inbox_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("id"):
            rows.append(row)
    return rows


def fields(row: dict[str, Any]) -> dict[str, str]:
    route = str(row.get("frm", "")).removeprefix("remote:")
    return {
        "record_id": f"legacy:{row['id']}",
        "link": LEGACY,
        "link_name": "legacy HMAC bridge",
        "fleet": route,
        "fleet_root": "",
        "device": "",
        "seat_claim": str(row.get("claimed_frm", "")),
        "kind": str(row.get("kind", "")),
        "to": "",
        "content": str(row.get("content", "")),
        "reply_to": "",
        "blobs": "[]",
        "sent_at": str(row.get("sent_at", "")),
        "received_at": str(row.get("admitted_at", "")),
        "cursor": "",
        "authority": "none",
        "verified": "false",
    }


def import_parked(*, dry: bool = False, r: Any | None = None) -> dict[str, Any]:
    """Queue every parked row not yet imported. Returns counts."""
    done = _done()
    rows = [row for row in parked_rows() if str(row["id"]) not in done and row.get("kind") in BRIDGE_KINDS]
    skipped = len(parked_rows()) - len(rows)
    if dry or not rows:
        return {"imported": 0, "would_import": len(rows), "skipped": skipped}
    r = r if r is not None else quarantine.redis_client()
    if r is None:
        raise RuntimeError("the bus is offline; the parked file is untouched, run this again once it is up")
    for row in rows:
        r.xadd(quarantine.stream_key(LEGACY), fields(row), maxlen=quarantine.MAXLEN, approximate=True)
        done.add(str(row["id"]))
    path = _done_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(done)) + "\n", encoding="utf-8")
    return {"imported": len(rows), "skipped": skipped}


def promote_legacy(record_id: str, *, by: str, to: str, r: Any | None = None, bus: Any | None = None) -> dict[str, Any]:
    """Promote one imported legacy row onto the bus (a person's decision, as for link mail)."""
    r = r if r is not None else quarantine.redis_client()
    if r is None:
        raise RuntimeError("the bus is offline")
    rid = record_id if record_id.startswith("legacy:") else f"legacy:{record_id}"
    for _sid, f in r.xrange(quarantine.stream_key(LEGACY)):
        if f.get("record_id") == rid:
            if bus is None:
                from core.comm.bus import Bus

                bus = Bus(f"legacy-bridge:{f['fleet']}")
            meta = {
                "source": "legacy-bridge",
                "fleet": f["fleet"],
                "claimed_frm": f["seat_claim"],
                "verified": False,
                "authority": "none",
                "promoted_by": by,
                "idempotency_key": rid,
            }
            mid = bus.send(to, f["kind"], f"[remote {f['fleet']} (legacy bridge)] {f['content']}", meta=meta)
            return {"promoted": bool(mid), "bus_id": mid, "record_id": rid, "seat": to}
    raise RuntimeError(f"no imported legacy record {rid}")
