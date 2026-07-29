"""defer_queue — the capability-gated standing queue (W33, seat-zero wave B3).

Commands that WAIT FOR A SEAT WITH A CAPABILITY the filing seat lacks (exec, write).
Born from kimi's GREEN queue riding handoff prose: "four one-liners for the next exec
seat" buried in a 3KB message body, discharged only because that seat read carefully.
This registry makes the queue first-class: file with `defer`, surface at boot, discharge
with a receipt.

Consensus laws (claude opening + kimi counter, night-run 2026-07-21):
  COMMANDS-NOT-CHARTERED-WORK — a mini-registry, not task-ledger entries; the ledger's
    gates are wrong-weight for "run these one-liners" (Q2, both seats agree). It reuses
    the ledger's FILE DISCIPLINE (git-durable state/*.json, atomic replace — the K0
    atomicity lesson) without its transitions.
  RECEIPT-ON-DONE (kimi b, blocking) — discharge REQUIRES a receipt string; a queue
    where items vanish stampless is a graveyard. History is never deleted.
  CAPABILITY-AWARE RENDER (kimi a, blocking) — a seat whose ACL lacks the needed cap
    gets ONE dim line ("not you"), never a shouted work list (the W03/W40 genus).
    Honest residual: session-level harness gates (a write-gated seat of a caps-holding
    agent) are invisible here; the ACL gates the render, the seat self-selects live.
  CAPPED SECTION (kimi d) — boot shows at most BOOT_CAP items + "+M more".
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Set

from core.foundation.timeutil import now_iso

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# state/coord/ is the ledger's own git-TRACKED home (state/*.json at top level is
# gitignored -- kimi's amendment (c) requires git-durable, so the queue lives here).
QUEUE_PATH = os.path.join(_ROOT, "state", "coord", "defer_queue.json")
BOOT_CAP = 3
KNOWN_NEEDS = ("exec", "write", "net")


def _load() -> Dict[str, Any]:
    try:
        with open(QUEUE_PATH, encoding="utf-8") as f:
            doc = json.load(f)
        if isinstance(doc, dict) and isinstance(doc.get("items"), list):
            return doc
    except Exception:
        pass
    return {"v": 1, "items": []}


def _save(doc: Dict[str, Any]) -> None:
    """Atomic replace (K0 lesson): multiple seats file/discharge; a torn write must be
    unrepresentable. tmp rides the same directory so os.replace stays same-volume."""
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    tmp = f"{QUEUE_PATH}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, QUEUE_PATH)


def add(by: str, cmd: str, *, needs: str = "exec", why: str = "") -> Dict[str, Any]:
    """File one awaiting-capability command. `needs` names the capability the filing
    seat lacked (KNOWN_NEEDS teaches; unknown values pass through loudly-visible)."""
    cmd = str(cmd or "").strip()
    if not cmd:
        raise ValueError("defer needs the command itself (what should the capable seat run?)")
    item = {"id": uuid.uuid4().hex[:10], "by": str(by), "cmd": cmd,
            "needs": str(needs or "exec"), "why": str(why or ""),
            "filed_at": now_iso(),   # T119: the one clock (aware UTC)
            "done_by": "", "done_at": "", "receipt": ""}
    doc = _load()
    doc["items"].append(item)
    _save(doc)
    return item


def pending() -> List[Dict[str, Any]]:
    return [i for i in _load()["items"] if not i.get("done_by")]


def mark_done(item_id: str, *, seat: str, receipt: str) -> Dict[str, Any]:
    """Discharge with a receipt (REQUIRED): what happened when the capable seat ran it.
    The item stays in the file forever — the queue is also the discharge ledger."""
    if not str(receipt or "").strip():
        raise ValueError("discharge needs a receipt (what happened?) -- a stampless done "
                         "turns the queue into a graveyard")
    doc = _load()
    for i in doc["items"]:
        if i["id"] == str(item_id) and not i.get("done_by"):
            i["done_by"] = str(seat)
            i["done_at"] = now_iso()   # T119: the one clock (aware UTC)
            i["receipt"] = str(receipt).strip()
            _save(doc)
            return i
    raise KeyError(f"no pending item with id {item_id!r} (see: defer <you> --list)")


def render_boot_section(*, agent_caps: Set[str]) -> str:
    """The boot surface. Caps-holders see the capped list; others one dim line; an
    empty queue renders nothing (never a standing header for a standing-empty queue)."""
    items = pending()
    if not items:
        return ""
    runnable = [i for i in items if i["needs"] in agent_caps]
    if not runnable:
        needs = sorted({i["needs"] for i in items})
        return (f"# deferred: {len(items)} command(s) await a seat with "
                f"{'/'.join(needs)} -- not you; a capable seat discharges via "
                f"`defer <it> --list`")
    lines = [f"# DEFERRED FOR YOU ({len(runnable)} runnable -- discharge with a receipt):"]
    for i in runnable[:BOOT_CAP]:
        why = f"  ({i['why']})" if i.get("why") else ""
        lines.append(f"#   [{i['id']}] {i['cmd']}{why}  <- {i['by']}, {i['filed_at'][:10]}")
    if len(runnable) > BOOT_CAP:
        lines.append(f"#   ...+{len(runnable) - BOOT_CAP} more: py agent_cli.py defer <you> --list")
    return "\n".join(lines)
