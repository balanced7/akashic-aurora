"""Answering the operator, in one argument, with an honest delivery verdict.

Daniil 2026-09-04: "How do we make it easy for you to reply, should it be a verb?" -- asked
after watching a seat lose three answers to argv ordering while every gauge read green. His
own standing rule is the whole brief: if you want the right thing to get done, make it EASY
for it to get done. A capability nobody can afford to invoke does not exist, and a door with
five slots and three fatal orderings is a door nobody can afford.

WHAT THIS DOOR DOES DIFFERENTLY, and both halves are load-bearing:

  ONE SLOT. `reply(text)`. The body is the only positional; the sender is inferred from the
  seat and the recipient defaults to the operator. sender_guard REFUSES a body in the sender
  slot; this makes that shape impossible to type in the first place. The pin
  test_sender_is_inferred_not_positional asserts the signature itself, so a later refactor
  cannot quietly reopen the trap.

  HONEST DELIVERY. The afternoon's whole failure was that success was indistinguishable from
  silence: `pump()` increments `forwarded` even when the POST dies (documented in
  discord_feed_global_path_claims_delivery_it_did_not_make and still unfixed). So this reads
  the one signal that does not lie -- the `discord_feed_post_failed` event -- and grades
  itself in four states, never two:

    FAILED                      a failure event names this body. Say so, loudly.
    SENT_NO_FAILURE_RECORDED    the bus took it and nothing has confessed. This is NOT
                                "delivered": the operator reading it is a separate fact
                                (a_served_blob_is_not_a_fetched_blob). Absence of evidence
                                gets its own name so nobody can round it up to proof.
    UNKNOWN                     the verifier itself could not be read. Never claim either way.
    (refusal)                   ok=False -- offline bus, empty body, or a None message id.

  MODEL STAMP (2026-09-04, Daniil: "Lets incorporate the model stamp into the verb"). The
  self-report plane in core/fleet/seat_model.py existed but nothing ever called `report()` --
  `!model` always said "nobody stamped one" because no live session used the door. The reply
  verb is the one thing every session already invokes to talk to him, so it is the natural
  place to refresh the receipt: pass `model=` (an alias like "sonnet" or a full id) and, on a
  successful send, this stamps CLAUDE_CODE_SESSION_ID's model into the same self-report `!model`
  reads. An unresolvable alias or a stamp failure never blocks the reply itself -- the body
  reaching him outranks the receipt about who sent it.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

#: Who "the operator" is when nobody says otherwise. A default, never a truth claim --
#: whoever holds the root id is not necessarily this name (the same discipline
#: discord_inbound applies to attribution).
DEFAULT_OPERATOR = "daniil"

#: How long to look back for a failure confession about this send.
_FAILURE_WINDOW_S = 120


def operator_id() -> str:
    return (os.environ.get("AKASHIC_OPERATOR_ID") or DEFAULT_OPERATOR).strip()


def _seat() -> str:
    return (os.environ.get("AKASHIC_AGENT_ID") or "claude").strip()


def _session_id() -> str:
    """The running Claude Code session's id, short-formed to match seat_model's key shape
    (roster already truncates to 8 chars, e.g. claude#aa2093d4). Empty when absent (a
    non-Claude-Code caller, or a test) -- report() itself refuses a blank session."""
    return (os.environ.get("CLAUDE_CODE_SESSION_ID") or "").strip()[:8]


def _recent_failures() -> List[Dict[str, Any]]:
    """Recent `discord_feed_post_failed` records. Best-effort by construction: the caller
    treats an exception here as UNKNOWN, never as clean."""
    # The SAME door `agent_cli events --search` uses (agent_cli.py:4966). My first guess
    # here was core.narrative.events.search, which does not exist -- and the verb's own
    # honesty caught it: the ImportError degraded to UNKNOWN and it claimed neither
    # delivery nor loss, exactly as designed, instead of reporting a cheerful success.
    from core.events.event_query import get_event_query
    rows = get_event_query().search("discord_feed_post_failed", top_k=25)
    out: List[Dict[str, Any]] = []
    now = time.time()
    for r in rows or []:
        ts = r.get("ts") or r.get("timestamp") or 0
        try:
            age = now - float(ts)
        except (TypeError, ValueError):
            age = 0.0
        if age <= _FAILURE_WINDOW_S:
            out.append(dict(r))
    return out


def reply(text: Optional[str], *, sender: Optional[str] = None, to: Optional[str] = None,
          bus: Any = None, failures: Optional[Callable[[], List[Dict[str, Any]]]] = None,
          kind: str = "chat", model: Optional[str] = None,
          stamp: Optional[Callable[..., bool]] = None) -> Dict[str, Any]:
    """Answer the operator. `text` is the ONLY positional -- see the module docstring.

    `model`, if given, is stamped to the self-report plane (`!model` reads it) on a
    successful send -- best-effort, and never turns a delivered reply into a failure."""
    body = "" if text is None else str(text).strip()
    if not body:
        return {"ok": False, "why": "refusing an EMPTY reply -- a header with nothing under "
                                    "it is indistinguishable from a failed send",
                "delivery": "REFUSED", "id": None}

    who = (sender or _seat()).strip()
    target = (to or operator_id()).strip()

    if bus is None:
        from core.comm.bus import Bus
        bus = Bus(who)
    if not getattr(bus, "online", True):
        return {"ok": False, "why": "bus OFFLINE (Redis down) -- not sent",
                "delivery": "REFUSED", "id": None}
    try:
        bus.register()
    except Exception:                                                     # noqa: BLE001
        pass                          # registration is hygiene, not the delivery path

    mid = bus.send(target, kind, body, meta={"source": "reply-verb", "from_seat": who})
    if mid is None:
        # T149: bus.send returns None WITHOUT raising when Redis is down or both writes
        # fail. Reporting success here is the exact claimed-delivery lie this door exists
        # to end.
        return {"ok": False, "why": "the bus accepted nothing (send returned None) -- no "
                                    "receipt for an undelivered word",
                "delivery": "FAILED", "id": None}

    stamped = _stamp_model(model, agent=who, stamper=stamp)

    reader = failures or _recent_failures
    try:
        rows = reader() or []
    except Exception as e:                                                # noqa: BLE001
        return {"ok": True, "id": str(mid), "delivery": "UNKNOWN", "model_stamped": stamped,
                "why": f"sent, but the failure log could not be read ({type(e).__name__}) "
                       f"-- claiming neither delivery nor loss"}

    probe = body[:60]
    for r in rows:
        blob = f"{r.get('text') or ''} {r.get('detail') or ''}"
        if probe and probe[:40] in blob:
            err = str((r.get("detail") or {}).get("error") or "post failed")
            return {"ok": True, "id": str(mid), "delivery": "FAILED", "model_stamped": stamped,
                    "why": f"the bus took it but the Discord post FAILED: {err}"}

    return {"ok": True, "id": str(mid), "delivery": "SENT_NO_FAILURE_RECORDED",
            "model_stamped": stamped,
            "why": "on the bus, nothing has confessed a failure -- which is not the same "
                   "fact as the operator having read it"}


def _stamp_model(model: Optional[str], *, agent: str,
                  stamper: Optional[Callable[..., bool]] = None) -> bool:
    """Best-effort self-report so `!model` reflects who is actually answering. An
    unresolvable alias, a missing session id, or a Redis hiccup all degrade to False --
    none of them may turn a delivered reply into a failure (see module docstring)."""
    text = str(model or "").strip()
    if not text:
        return False
    session = _session_id()
    if not session:
        return False
    try:
        from core.fleet import seat_model as _sm
        model_id = _sm.resolve_model_id(text)
        do_report = stamper or _sm.report
        return bool(do_report(agent, session, model_id, harness="claude-code"))
    except Exception:                                                     # noqa: BLE001
        return False


def render(out: Dict[str, Any]) -> str:
    """One line for a CLI door."""
    if not out.get("ok"):
        return f"[reply] {out.get('why')}"
    tag = {"FAILED": "FAILED", "UNKNOWN": "sent (unverified)",
           "SENT_NO_FAILURE_RECORDED": "sent"}.get(str(out.get("delivery")), "sent")
    stamp_note = " · model stamped" if out.get("model_stamped") else ""
    return f"[reply] {tag} -> {out.get('id')} :: {out.get('why')}{stamp_note}"
