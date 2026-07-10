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
import re
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


ACK_KIND = "msg_ack"            # P6 (T026): "I HANDLED this" -- read != handled != acknowledged
UNHANDLED_HOURS = 6             # broadcast threshold (ambiguous ownership gets more slack)
DIRECTED_UNHANDLED_HOURS = 2    # directed handoffs have a clear addressee; fleet cadence is minutes
FLAGGABLE_KINDS = {"handoff", "blocker"}   # asks get flagged; decision/completion are fire-and-forget


def _promoted_record(msg_id: str, *, event_query=None) -> Optional[Dict[str, Any]]:
    """The bifrost_msg event carrying ref bifrost:<msg_id>, or None. Scans the promoted tier
    (small by design -- salient kinds only); RB-4 replaces this with an exact by-ref index
    lookup. Never raises."""
    try:
        from core.events.event_query import get_event_query
        eq = event_query if event_query is not None else get_event_query()
        ref = f"bifrost:{str(msg_id).strip()}"
        for e in eq.search("", kind=PROMOTED_KIND, top_k=100000):
            if ref in (e.get("refs") or []):
                return e
    except Exception:
        return None
    return None


def ack_verdict(by: str, msg_id: str, *, event_query=None) -> tuple:
    """(allowed, reason) -- the ONE ack-acceptance rule, guarding every caller (RB-2/T029).
    An ack is accepted only from the message's ADDRESSEE: the sender cannot settle its own
    ask (self-ack), a third id cannot settle someone else's (spoofed actor), a broadcast
    (to='*') accepts any non-sender handler, quarantined/unknown ids are refused, and a
    message with no promoted record is refused -- an ack exists to annotate the salient
    tier, so there is nothing for it to settle. Ids are unauthenticated until identity is
    signed (same honest bound as RB-1); the trust check fails OPEN on a broken door (the
    addressee rule still holds; a refused legit auto-ack would re-flag handled work)."""
    b = str(by)
    try:
        from core.trust.registry import resolve
        if resolve(b).role == "quarantined":
            return False, (f"{b!r} resolves to quarantined -- unknown/expired ids cannot "
                           "settle asks (fix the grant in security/acl.json)")
    except Exception:
        pass
    rec = _promoted_record(msg_id, event_query=event_query)
    if rec is None:
        return False, (f"bifrost:{msg_id} has no promoted record -- only salient messages "
                       "(handoff/decision/completion/blocker) carry acks")
    d = rec.get("detail") or {}
    frm, to = str(d.get("frm", "")), str(d.get("to", "*"))
    if b == frm:
        return False, f"{b} sent this message -- the sender cannot ack its own ask"
    if to != "*" and b != to:
        return False, f"directed to {to!r} -- only the addressee can ack it"
    return True, "ok"


def ack(by: str, msg_id: str, note: str = "", *, event_log=None, event_query=None) -> bool:
    """Durably record that `by` HANDLED bus message `msg_id` (P6/T026). The four 2026-07-09
    incidents (two eaten replies, a drain-swallowed spec, a re-wake loop) all shared one
    shape: nothing distinguished a message that was READ from one that was ACTED ON. Acks
    close that loop on the salient tier. Multiple ACTORS per message are legal (forensics;
    broadcasts only since RB-2 -- directed asks accept only their addressee, via
    ack_verdict); the same actor twice is a NO-OP (red-team: the re-wake loop could
    double-answer). Never raises, never blocks a send path."""
    try:
        clean_id = str(msg_id).strip()
        allowed, _why = ack_verdict(by, clean_id, event_query=event_query)
        if not allowed:
            return False
        existing = acks_for([clean_id], event_query=event_query).get(clean_id, [])
        if any(a.get("by") == str(by) for a in existing):
            return True                       # idempotent: already on record for this actor
        from core.events.event_log import get_event_log
        el = event_log if event_log is not None else get_event_log()
        el.capture(ACK_KIND, f"{by} handled bifrost:{clean_id}" + (f" -- {note[:100]}" if note else ""),
                   agent_id=str(by), refs=[f"bifrost:{clean_id}"],
                   detail={"by": by, "msg_id": clean_id, "note": note})
        return True
    except Exception:
        return False


def acks_for(msg_ids, *, event_query=None) -> Dict[str, List[Dict[str, Any]]]:
    """msg_id -> [ {by, at, note}, ... ] for every ack referencing those bus ids. Never raises."""
    wanted = {str(m) for m in msg_ids}
    out: Dict[str, List[Dict[str, Any]]] = {m: [] for m in wanted}
    try:
        from core.events.event_query import get_event_query
        eq = event_query if event_query is not None else get_event_query()
        for e in eq.search("", kind=ACK_KIND, top_k=500):
            d = e.get("detail") or {}
            mid = str(d.get("msg_id", ""))
            if mid in wanted:
                out[mid].append({"by": d.get("by", "?"), "at": e.get("at", ""),
                                 "note": d.get("note", "")})
    except Exception:
        pass
    return out


def promoted(limit: int = 20, *, event_query=None, since: Optional[str] = None,
             until: Optional[str] = None, with_acks: bool = False,
             now: Any = None, unhandled_hours: int = UNHANDLED_HOURS) -> List[Dict[str, Any]]:
    """Durable salient bus messages (the read side). Time-queryable + survives a Redis restart via
    the File ledger. Returns the raw promoted events (each carries its `detail`). Never raises.

    P6: `with_acks=True` annotates each event with `acks` (who handled it) and, when `now`
    (epoch seconds) is given, `unhandled=True` for ASK-shaped kinds (handoff/blocker) past
    their threshold with no ack -- promoted-and-forgotten is the flag's whole point.
    Red-team-shaped rules: directed asks flag at DIRECTED_UNHANDLED_HOURS (clear addressee,
    minutes-cadence fleet), broadcasts at `unhandled_hours`; decision/completion never flag;
    and an ask whose referenced ledger task is since DONE/ABANDONED is implicitly handled
    (the work completed through another channel) -- suppressed, marked `handled_via`."""
    try:
        from core.events.event_query import get_event_query
        eq = event_query if event_query is not None else get_event_query()
        events = eq.search("", kind=PROMOTED_KIND, since=since, until=until, top_k=limit)
        if not with_acks:
            return events
        ids = [str(e.get("refs", ["bifrost:"])[0]).split("bifrost:", 1)[-1] for e in events]
        amap = acks_for(ids, event_query=eq)
        closed_tasks = _closed_task_ids()
        from datetime import datetime
        for e, mid in zip(events, ids):
            e["acks"] = amap.get(mid, [])
            d = e.get("detail") or {}
            if now is None or e["acks"] or d.get("kind") not in FLAGGABLE_KINDS:
                continue
            referenced = set(re.findall(r"\bT\d{3}\b", str(d.get("content", ""))))
            if referenced & closed_tasks:
                e["handled_via"] = f"ledger: {sorted(referenced & closed_tasks)} closed"
                continue
            threshold = (DIRECTED_UNHANDLED_HOURS if str(d.get("to", "*")) != "*"
                         else unhandled_hours)
            try:
                age_h = (float(now) - datetime.fromisoformat(str(e.get("at", ""))).timestamp()) / 3600
                e["unhandled"] = bool(threshold and age_h > threshold)
                e["age_hours"] = age_h
            except (ValueError, TypeError):
                e["unhandled"] = False
        return events
    except Exception:
        return []


def _closed_task_ids() -> set:
    """Ledger tasks in a terminal state -- an unacked ask about a closed task is implicitly
    handled (red-team finding 3b). Fail-open to empty."""
    try:
        from core.coord.task_ledger import read_ledger
        return {t["id"] for t in read_ledger().get("tasks", [])
                if t.get("status") in ("done", "abandoned")}
    except Exception:
        return set()


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
