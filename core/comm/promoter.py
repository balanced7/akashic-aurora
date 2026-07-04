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

# Console control-plane kinds -- the live cockpit (scripts/bifrost_ui.py) lets a human interject,
# pause/resume the collaboration, and drop files into the project. Those are high-signal human actions
# with no durable home today (the console renders them over ephemeral SSE only). Project them into the
# SAME firehose as bifrost_msg so "what the human steered, and when" survives the session. Raw agent
# chatter and presence ticks stay ephemeral by design (bus=ephemeral, F1) -- we capture the DECISIONS,
# not the stream.
INTERJECTION_KIND = "interjection"    # a human message typed into a live session (halt/steer/ask/resume)
CONTROL_KIND = "bus_control"          # pause / resume of the auto-responders
DROP_KIND = "file_drop"               # a file shared into the project via the console
CONSOLE_KINDS = (INTERJECTION_KIND, CONTROL_KIND, DROP_KIND)


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


# ---------------------------------------------------------------------- console control plane
# Same contract as promote(): best-effort, never raise, return True iff a durable record was written.
# The capture must never break the console's request path.

def promote_interjection(text: Any, verdict: Optional[dict], to: str, *, paused: bool = False,
                         by: str = "user", msg_id: Optional[str] = None, event_log=None) -> bool:
    """A human interjection typed into the live console -> a durable Ledger record. `verdict` is the
    interject.classify_intent() dict {intent, confidence, why, source}; `msg_id` links to the delivered
    bus message when there is one."""
    try:
        from core.events.event_log import get_event_log
        el = event_log if event_log is not None else get_event_log()
        v = verdict or {}
        intent = str(v.get("intent", "steer"))
        summary = f"{by} [{intent}] -> {to}: {str(text)[:140]}"
        refs = [f"bifrost:{msg_id}"] if msg_id else None
        el.capture(INTERJECTION_KIND, summary, agent_id=str(by), refs=refs,
                   detail={"text": text, "to": to, "intent": intent, "why": str(v.get("why", "")),
                           "confidence": v.get("confidence"), "source": v.get("source"),
                           "paused": bool(paused)})
        return True
    except Exception:
        return False


def promote_control(action: str, *, reason: str = "", by: str = "user", event_log=None) -> bool:
    """A pause/resume of the collaboration -> a durable Ledger record (the human-in-the-loop audit trail)."""
    try:
        from core.events.event_log import get_event_log
        el = event_log if event_log is not None else get_event_log()
        act = str(action).lower()
        summary = f"{by} {act} the collaboration" + (f": {reason}" if reason else "")
        el.capture(CONTROL_KIND, summary, agent_id=str(by),
                   detail={"action": act, "reason": reason, "by": by})
        return True
    except Exception:
        return False


def promote_drop(path: str, size_bytes: Any, *, by: str = "user", event_log=None) -> bool:
    """A file shared into the project via the console -> a durable provenance record."""
    try:
        from core.events.event_log import get_event_log
        el = event_log if event_log is not None else get_event_log()
        try:
            n = int(size_bytes)
        except Exception:
            n = 0
        el.capture(DROP_KIND, f"{by} shared file {path} ({n} bytes)", agent_id=str(by),
                   refs=[f"file:{path}"], detail={"path": path, "bytes": n, "by": by})
        return True
    except Exception:
        return False


def console_events(limit: int = 20, *, kinds=None, event_query=None,
                   since: Optional[str] = None, until: Optional[str] = None) -> List[Dict[str, Any]]:
    """Durable console control-plane events (interjection/bus_control/file_drop), newest first. The read
    side of the console capture -- time-queryable and Redis-restart-survivable (File ledger). Never raises."""
    wanted = tuple(kinds) if kinds else CONSOLE_KINDS
    try:
        from core.events.event_query import get_event_query
        eq = event_query if event_query is not None else get_event_query()
        out: List[Dict[str, Any]] = []
        for k in wanted:
            out.extend(eq.search("", kind=k, since=since, until=until, top_k=limit))
        out.sort(key=lambda e: str(e.get("at", "")), reverse=True)
        return out[:limit]
    except Exception:
        return []
