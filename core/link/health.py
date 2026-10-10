"""health -- the fleet-link section of `aurora doctor` and of the console: is anything wrong?

Read-only, and quiet when links are not in use: no binary and no link store means nothing to
report. Each problem is phrased with its remedy, as the rest of doctor does.
"""

from __future__ import annotations

import time
from typing import Any

from core.link.client import MISSING, LinkdMissing, LinkRpcError, connect, find_linkd, running_addr, state_dir


def health() -> dict[str, Any]:
    """{in_use, available, running, identity, links: [...], problems: [...]}. Never raises."""
    out: dict[str, Any] = {"in_use": False, "available": False, "running": False, "links": [], "problems": []}
    stores = list(state_dir().glob("*.db")) if state_dir().is_dir() else []
    out["in_use"] = bool(stores)
    out["available"] = find_linkd() is not None
    if not out["available"]:
        if stores:
            out["problems"].append(MISSING)
        return out
    out["running"] = running_addr() is not None
    if not stores:
        return out
    try:
        with connect() as c:
            ident = c.call("identity.status")
            out["identity"] = {
                k: ident.get(k) for k in ("device", "label", "fingerprint", "cert_expires", "needs_renewal")
            }
            if ident.get("needs_renewal"):
                out["problems"].append(
                    f"this device's certificate expires {time.strftime('%Y-%m-%d', time.localtime(ident['cert_expires']))}: "
                    "`aurora link renew --phrase-stdin`"
                )
            for row in c.call("link.list") or []:
                s = c.call("link.status", link=row["link"])
                unverified = [
                    m["label"] for m in s["members"] if not m["us"] and not m["removed"] and not m["verified"]
                ]
                link = {
                    "name": s["name"],
                    "link": s["link"],
                    "role": s["my_role"],
                    "members": sum(1 for m in s["members"] if not m["removed"]),
                    "alarms": len(s["alarms"]),
                    "unverified": unverified,
                    "quarantine": s["quarantine_unpromoted"],
                    "rotation_due": s["rotation_due"],
                }
                out["links"].append(link)
                for a in s["alarms"]:
                    out["problems"].append(f"{s['name']}: ALARM {a['kind']} from {a['author'][:16]}: {a['detail']}")
                if unverified:
                    out["problems"].append(
                        f"{s['name']}: safety number not compared with {', '.join(unverified)}: `aurora link verify {s['name']}`"
                    )
                if s["rotation_due"]:
                    out["problems"].append(
                        f"{s['name']}: a key rotation is due; an admin's `aurora link serve` appends it"
                    )
                for p in s["pending_joins"]:
                    if p["needs_approval"]:
                        out["problems"].append(
                            f"{s['name']}: {p['label']} waits for `aurora link accept {s['name']} {p['join'][:12]}`"
                        )
        if not out["running"]:
            out["problems"].append("links exist but nothing syncs them: start `aurora link serve`")
    except (LinkdMissing, LinkRpcError, OSError, ValueError) as e:
        out["problems"].append(f"aurora-linkd did not answer: {e}")
    return out


def render(h: dict[str, Any]) -> list[str]:
    """Doctor's text lines for the section (empty when links are not in use)."""
    if not h.get("in_use") and not h.get("problems"):
        return []
    lines = ["## LINKS (fleet links -- RFC #70)"]
    lines.append(
        f"  daemon: {'running' if h.get('running') else 'not running'}"
        + ("" if h.get("available") else " (not installed)")
    )
    lines.extend(
        f"  {link['name']}: {link['members']} members, role {link['role']}, "
        f"{link['quarantine']} in quarantine" + (f", {link['alarms']} ALARM(S)" if link["alarms"] else "")
        for link in h.get("links", [])
    )
    lines += [f"  ! {p}" for p in h.get("problems", [])]
    return lines
