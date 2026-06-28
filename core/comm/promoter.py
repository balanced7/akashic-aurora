"""
Bifrost B2 -- the durable projection. Promote SALIENT bus messages into the append-only Ledger.

Semantic Relationship: SalientBusMessage promoted_to LedgerRecord (durable; queryable)

The bus (core/comm/bus.py) is ephemeral Redis Streams -- fast, bounded, lost on flush/restart. That
is correct for chatter, but a handoff/decision/completion/blocker is the kind of thing that must
SURVIVE: "what was said and decided". So those salient kinds are projected into the existing event
firehose (core/events) -- which writes File ALWAYS + Redis best-effort and is time-indexed (V1) -- so
they're durable and queryable, while ephemeral kinds stay ephemeral. (Design delta F1: the bus and
the durable record are separate concerns, with promotion the bridge -- exactly the raw->beats pattern.)

Interop contract with the read side (agent_cli/MCP, owned by Cursor): a promoted message is an event
with kind=`bifrost_msg`, ref `bifrost:<msg_id>`, and detail {frm,to,kind,content,ts}. Query via
`promoted(...)` (or event_query for kind==bifrost_msg).
"""
from typing import Any, Dict, List, Optional

SALIENT_KINDS = frozenset({"handoff", "decision", "completion", "blocker"})
PROMOTED_KIND = "bifrost_msg"


def is_salient(kind: Any) -> bool:
    return str(kind) in SALIENT_KINDS


def promote(frm: str, to: str, kind: str, content: Any, msg_id: str, ts: str,
            *, event_log=None) -> bool:
    """Record a salient bus message durably in the Ledger. No-op (False) for ephemeral kinds or on
    any error -- promotion must never break the send path. Returns True if promoted."""
    if not is_salient(kind):
        return False
    try:
        from core.events.event_log import get_event_log
        el = event_log if event_log is not None else get_event_log()
        summary = f"{frm} -> {to} [{kind}]: {str(content)[:160]}"
        el.capture(PROMOTED_KIND, summary, agent_id=str(frm), refs=[f"bifrost:{msg_id}"],
                   detail={"frm": frm, "to": to, "kind": kind, "content": content, "ts": ts}, at=ts)
        return True
    except Exception:
        return False


def promoted(limit: int = 20, *, event_query=None, since: Optional[str] = None,
             until: Optional[str] = None) -> List[Dict[str, Any]]:
    """Durable salient bus messages (the read side). Time-queryable + survives a Redis restart via
    the File ledger. Returns the raw promoted events (each carries its `detail`). Never raises."""
    try:
        from core.events.event_query import get_event_query
        eq = event_query if event_query is not None else get_event_query()
        return eq.search("", kind=PROMOTED_KIND, since=since, until=until, top_k=limit)
    except Exception:
        return []
