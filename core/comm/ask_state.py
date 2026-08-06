"""ask_state -- one durable ask's honest state (T196d).

The readout half of the T196 transaction (spec: docs/library/design/
20260805_t196-ask-transaction-spec_b59657.md). Sol's five success-shaped states,
rebuilt as the seven the house laws require -- every state derivable from observables,
every state answering "what should the caller do NOW", UNKNOWN a first-class verdict
instead of a coerced guess (T155's law, one layer up).

FOLD PRECEDENCE (the hybrid the fence settled on): the armed expectation record is the
authority for OPEN states; durable terminal events (T196b kinds) are the authority for
CLOSED states -- they outlive both the record (deleted at settle) and the streams
(maxlen-trimmed); nothing left is UNKNOWN, said plainly. This module is an OBSERVER
(T025: observation split from action): it never sweeps, never settles, never consumes.
The T196c verb is this readout polled in a loop, with sweep() -- the actor -- called
separately beside it.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.foundation.timeutil import to_epoch
# Same-package reuse: snapshot is the public read-only record view; ANSWER_KINDS is the
# settle vocabulary; _client/_ns are the coordination-plane accessors (private by
# underscore, shared by design inside core/comm -- expectations owns the plane, its
# siblings read it).
from core.comm.expectations import ANSWER_KINDS, _client, _ns, snapshot

TERMINAL_TO_STATE = {
    "expectation_settled_answered": "CLOSED.ANSWERED",
    "expectation_settled_done_task": "CLOSED.ECHO",
    "expectation_dead": "CLOSED.DEAD",
}

# state -> (terminal, what the caller should do RIGHT NOW). The lie each state prevents
# lives in the spec's table; the caller_should is that lie's antidote rendered as advice.
STATES: Dict[str, tuple] = {
    "OPEN.DISPATCHED": (False, "wait or do other work -- nothing observable says the "
                               "peer saw it yet"),
    "OPEN.NOTED": (False, "read the note -- it neither answers nor kills the ask; the "
                          "expectation stays armed (RB-29)"),
    "OPEN.REDRIVING": (False, "the peer is probably not consuming -- consider a nudge "
                              "or an alternate peer"),
    "CLOSED.ANSWERED": (True, "read the answer at the pointer"),
    "CLOSED.ECHO": (True, "read the ledger, not the mailbox -- the referenced work is "
                          "already done (T076c)"),
    "CLOSED.DEAD": (True, "chase it or let it go -- redrives exhausted unanswered"),
    "UNKNOWN": (True, "re-ask -- treat the old transaction as unresolvable (evidence "
                      "lost or trimmed: RB-30 flush, or maxlen outlived the ask)"),
}


def _candidates(ask_id: Any) -> List[str]:
    """The id the caller holds plus its alias chain (bounded, <=2 hops -- the same walk
    _resolve_link does, for the same reason): a dual-write sibling or a redrive id must
    resolve to the armed ask instead of lying UNKNOWN."""
    cur = str(ask_id or "")
    out = [cur]
    try:
        c = _client()
        if c is None:
            return out
        for _ in range(2):
            sib = c.get(f"{_ns()}:idalias:{cur}")
            if not sib:
                break
            cur = str(sib)
            if cur in out:
                break                               # never loop
            out.append(cur)
    except Exception:
        pass
    return out


def _peer_traffic_since(sender: str, rec: Dict[str, Any]) -> Dict[str, bool]:
    """Non-consuming peek at the sender's inbox after the ask's anchor: did the peer
    send a NON-answer (-> NOTED), and is an ANSWER visible that no sweep folded yet?
    Read from the stream position, never the cursor (consumption-immune, the
    expectations idiom); the bc lane stays pinned at its tail (room chatter never
    counts). Never raises."""
    try:
        from core.comm.bus import Bus
        b = Bus(str(sender))
        bc_now = b.tail().get("bc", "0")
        msgs = b.wait(timeout_ms=1, limit=200,
                      since={"inbox": rec.get("anchor", "0"), "bc": bc_now})
        frm_peer = [m for m in msgs if getattr(m, "frm", None) == rec.get("to")]
        return {
            "noted": any(getattr(m, "kind", "") not in ANSWER_KINDS for m in frm_peer),
            "answer_visible": any(getattr(m, "kind", "") in ANSWER_KINDS
                                  for m in frm_peer),
        }
    except Exception:
        return {"noted": False, "answer_visible": False}


def _span(later: Any, earlier: Any) -> Optional[float]:
    if later is None or earlier is None:
        return None
    try:
        return max(0.0, float(later) - float(earlier))
    except (TypeError, ValueError):
        return None


def state_of(sender: str, ask_id: Any, *, log=None,
             now: Optional[float] = None) -> Dict[str, Any]:
    """One durable ask's honest state. Read-only; `log` injectable (needs .scan(agent=))
    so tests construct evidence instead of writing it; `now` injectable so pins never
    sleep. Always returns a dict whose state is one of STATES -- including UNKNOWN,
    which is an answer, not a failure."""
    now = time.time() if now is None else float(now)
    sender = str(sender)
    cands = _candidates(ask_id)

    def _result(state: str, resolved: str, **extra) -> Dict[str, Any]:
        terminal, should = STATES[state]
        base = {"ask_id": str(ask_id), "resolved_id": resolved, "state": state,
                "terminal": terminal, "caller_should": should,
                "peer": None, "redrives": None, "age_s": None, "duration_s": None,
                "deadline_in_s": None, "answer_id": None, "evidence": {}}
        base.update(extra)
        return base

    # 1) OPEN states: the armed record is the authority.
    recs = snapshot(sender)
    for cand in cands:
        rec = recs.get(cand)
        if rec is None:
            continue
        try:
            attempt = int(rec.get("attempt", 0) or 0)
        except (TypeError, ValueError):
            attempt = 0
        traffic = _peer_traffic_since(sender, rec)
        if attempt > 0:
            state = "OPEN.REDRIVING"
        elif traffic["noted"]:
            state = "OPEN.NOTED"
        else:
            state = "OPEN.DISPATCHED"
        deadline = rec.get("deadline_ts")
        return _result(
            state, cand, peer=rec.get("to"), redrives=attempt,
            age_s=_span(now, rec.get("created")),
            deadline_in_s=_span(deadline, now) if deadline is not None else None,
            evidence={"record": True,
                      # An ANSWER sitting unswept is worth surfacing: the state is
                      # honest to the RECORDS, and this flag keeps it honest to the
                      # STREAMS too -- "dispatched, but a sweep will settle it".
                      "answer_visible_unswept": traffic["answer_visible"]})

    # 2) CLOSED states: durable terminal events outlive record and streams.
    if log is None:
        from core.events.event_log import EventLog
        log = EventLog()
    try:
        events = log.scan(agent=sender)
    except Exception:
        events = []
    for ev in reversed(events or []):              # newest evidence wins
        state = TERMINAL_TO_STATE.get(str(ev.get("kind") or ""))
        if not state:
            continue
        refs = [str(x) for x in (ev.get("refs") or [])]
        hit = next((c for c in cands if refs and refs[0] == c), None)
        if hit is None:
            continue
        detail = ev.get("detail") or {}
        try:
            closed_at = to_epoch(ev.get("at"))
        except Exception:
            closed_at = None
        redrives = None
        for k in ("attempt", "attempts"):
            if detail.get(k) is not None:
                try:
                    redrives = int(detail[k])
                except (TypeError, ValueError):
                    redrives = None
                break
        return _result(
            state, hit, peer=detail.get("to"), redrives=redrives,
            duration_s=_span(closed_at, detail.get("created")),
            answer_id=detail.get("answer_id"),
            evidence={"event": ev.get("_ref") or ev.get("id") or True,
                      "settle": detail.get("settle")})

    # 3) Nothing anywhere: say so plainly.
    return _result("UNKNOWN", cands[-1],
                   evidence={"record": False, "terminal_event": False,
                             "hops_walked": len(cands) - 1})
