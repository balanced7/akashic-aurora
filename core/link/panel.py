"""panel -- the console's fleet-link panel: a dict to paint, and the few actions a person takes.

GET /api/link renders `snapshot()`: members, devices, last contact, delivery receipts, the
quarantine queue and alarms, per link. POST /api/link/act runs `act()`: promote, accept or decline,
each only with `confirm` set explicitly, so rendering a page can never put another fleet's words on
the bus (the rule /api/remote/act already followed). This replaces the old /api/remote model.
"""

from __future__ import annotations

from typing import Any

from core.link import promote, quarantine
from core.link.client import LinkdMissing, LinkRpcError, connect
from core.link.health import health


def snapshot(inbox_limit: int = 25) -> dict[str, Any]:
    """Everything the panel shows. Never raises: an unavailable daemon is a state, not an error."""
    h = health()
    out: dict[str, Any] = {"health": h, "links": []}
    if not h.get("in_use") or not h.get("available"):
        return out
    try:
        with connect() as c:
            for row in c.call("link.list") or []:
                status = c.call("link.status", link=row["link"])
                out["links"].append({"status": status, "inbox": quarantine.inbox(c, row["link"], limit=inbox_limit)})
    except (LinkdMissing, LinkRpcError, OSError, ValueError) as e:
        out["error"] = str(e)
    return out


def act(action: str, data: dict[str, Any], *, confirm: bool) -> dict[str, Any]:
    """One person-initiated action. Returns {ok, why?, ...}."""
    if not confirm:
        return {"ok": False, "why": "confirm must be sent explicitly"}
    link = str(data.get("link") or "")
    try:
        with connect() as c:
            if action == "promote":
                out = promote.promote(
                    c,
                    link,
                    str(data.get("record") or ""),
                    by=f"console:{data.get('by') or 'person'}",
                    to=data.get("seat") or None,
                )
                return {"ok": True, **out}
            if action in ("accept", "decline"):
                out = c.call(f"link.{action}", link=link, join=str(data.get("join") or ""))
                return {"ok": True, **out}
            if action == "verify":
                rows = c.call("link.verify", link=link, member=str(data.get("member") or "") or None, mark=True)
                return {"ok": True, "verified": rows}
    except (LinkdMissing, LinkRpcError, promote.PromotionRefused, OSError, ValueError) as e:
        return {"ok": False, "why": str(e)}
    return {"ok": False, "why": f"unknown action {action!r}"}
