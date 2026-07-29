"""
Triage park (S0-alpha) -- the scry-to-bottom bench.

Semantic Relationship: TriagePark bottoms StaleAsks (durable bench; never a drop)

Recovery-arc S0's substrate (docs/library/design/20260701_recovery-arc-reconciled-design-superviso_ce9a9e.md: deepseek BULKHEAD-0 ∪
kimi R4 ∪ claude B1). The Canon's law: triage = scry-to-bottom -- a stale ask is BOTTOMED
to a durable per-agent bench so fresh mail flows, and it is NEVER dropped (the
graveyard-is-a-resource law applies to the bench too). RB-29 rides every park: the SENDER
is notified loudly -- an expectation settles by visible triage, not by vanishing.

Surface: <ns>:triage:<agent> (Redis list of JSON entries; durable, boot-heal covered).
S0-beta (Anvil-fenced, his loop): the consume paths call park() automatically on
D2-partitioned stale asks and advance past them. Until then: the `triage` verb is the
operator's hand -- the manual pattern that graduates, exactly like standby-hard.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from core.foundation.timeutil import now_iso


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _key(agent: str) -> str:
    return f"{_ns()}:triage:{agent}"


def _client():
    from core.comm.bus import get_bus
    return get_bus("triage")._client


def park(agent: str, msg: Dict[str, Any], *, reason: str, by: str) -> Dict[str, Any]:
    """Bottom one ask to the agent's bench. Durable append + LOUD sender-notify + receipt.
    Returns the bench entry (parked_id) so the caller may advance its cursor past the ask."""
    c = _client()
    if c is None:
        raise RuntimeError("triage park needs the bus (durable bench + sender notify)")
    entry = {"parked_id": uuid.uuid4().hex[:12], "agent": agent, "msg": dict(msg),
             "reason": str(reason), "by": str(by),
             "parked_at": now_iso()}   # T119: the one clock (aware UTC)
    c.rpush(_key(agent), json.dumps(entry, ensure_ascii=False))
    frm = str(msg.get("frm") or "")
    if frm and frm != agent:                      # RB-29: never silent -- the sender HEARS it
        try:
            from core.comm.bus import Bus
            Bus(agent).send(frm, "note",
                            f"[triage] your {msg.get('kind', 'ask')} ({msg.get('id', '?')}) to "
                            f"{agent} was PARKED ({reason}) -- bottomed, not dropped. "
                            f"Re-raise if still live, or drill: py agent_cli.py bench {agent}",
                            meta={"via": "triage-park", "display_only": True})
        except Exception:
            pass                                   # notify is best-effort; the bench is truth
    try:                                           # receipt on the firehose (Catalog was present)
        from core.comm.bus import Bus
        Bus(agent).broadcast("note", f"[triage-receipt] parked {msg.get('id', '?')} from "
                                     f"{frm or '?'} ({reason}; by {by})",
                             meta={"via": "triage-park", "display_only": True})
    except Exception:
        pass
    return entry


def list_parked(agent: str) -> List[Dict[str, Any]]:
    c = _client()
    if c is None:
        return []
    return [json.loads(x) for x in (c.lrange(_key(agent), 0, -1) or [])]


def count(agent: str) -> int:
    c = _client()
    if c is None:
        return 0
    try:
        return int(c.llen(_key(agent)) or 0)
    except Exception:
        return 0


def unpark(agent: str, parked_id: str) -> Optional[Dict[str, Any]]:
    """Scry-to-bottom's return path: remove ONE entry from the bench and hand it back
    INTACT. The bench forgets what it returned; the caller re-processes the ask."""
    c = _client()
    if c is None:
        return None
    for raw in (c.lrange(_key(agent), 0, -1) or []):
        e = json.loads(raw)
        if e.get("parked_id") == parked_id:
            c.lrem(_key(agent), 1, raw)
            return e
    return None


def render(agent: str) -> str:
    bench = list_parked(agent)
    if not bench:
        return f"# triage bench: {agent} -- empty (fresh mail flows)"
    rows = [f"# triage bench: {agent} -- {len(bench)} parked (bottomed, never dropped)"]
    for e in bench:
        m = e.get("msg", {})
        rows.append(f"  {e['parked_id']}  [{m.get('kind', '?')}] from {m.get('frm', '?')} "
                    f"({e.get('reason', '?')}, parked {e.get('parked_at', '?')})")
        rows.append(f"      {str(m.get('content', ''))[:110]}")
    rows.append(f"  return one: py agent_cli.py bench {agent} unpark <parked_id>")
    return "\n".join(rows)
