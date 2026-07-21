"""
toast (T099 · tools-hunt BETA-2) -- gratitude with a receipt (kimi's hunt B3).

Daniel's founding leaderboard, #8: "gratitude-with-receipt; seeds the leaderboard's social
fabric; the credit loop finally FEELS like something." The bench_reason ghost was
"surfaced 14x / 0 credit" -- lessons that earned credit had no human-feeling expression.
toast is that expression, and it is HONEST or it does not send.

Laws (the kimi register, sugar-only like every T099 surface):
  RECEIPTED   -- the receipt must name a REAL learning record (experiment name) attributable
                 to the toasted agent. Verification runs against core.learning's own store;
                 if the receipt does not verify, toast REFUSES to send and confesses why.
                 (Override exists (--force) but confesses GUESS-tier in both artifacts.)
  DUAL-SURFACE -- one toast = (a) a live bus message to the peer (delight NOW, the ping),
                 plus (b) a durable knowledge NOTE (the credit outlives the session; rides
                 the precedence doctrine: notes beat promoted beat live bus).
  HONESTY     -- the bus line and the note both carry the verification tier VERIFIED
                 (receipt found in the store) or GUESS (forced, unverified). Never silent.
  INJECTED    -- the bus send and note write are INJECTED (same pattern as
                 Toolbelt.resolve_and_run's runner seam, which made kata testable).
                 agent_cli passes the real senders; tests pass recorders. Fail-soft:
                 bus-offline still leaves the durable note, and the caller is told.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

NOTE_TITLE_PREFIX = "toast:"
MAX_BODY = 400          # gratitude is short; the leaderboard guard is distinct-users love
                        # (Goodhart-killer), never volume. A toast longer than this is a letter.


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:48] or "x"


def render_line(frm: str, to: str, receipt: str, hops: str, tier: str) -> str:
    """The one-line bus payload -- human-feeling first, receipt attached, tier confessed."""
    body = f"\U0001f9eb @{to}: {hops.strip()}"
    return (f"[{tier}] {body} (receipt: {receipt.strip()})"
            if tier == "VERIFIED"
            else f"[{tier} :unverified receipt] {body} (claimed receipt: {receipt.strip()})")


def note_title(to: str, receipt: str) -> str:
    return f"{NOTE_TITLE_PREFIX}{_slug(to)}-{_slug(receipt)}"


def render_note(frm: str, to: str, receipt: str, hops: str, tier: str,
                found_by: str, when: Optional[str] = None) -> str:
    """The durable credit record -- supersession-by-title keeps one note per (to, receipt);
    a re-toast of the same receipt REFRESHES the same note instead of piling up copies."""
    return (
        f"TOAST ({tier}) -- {when or time.strftime('%Y-%m-%d %H:%M')}\n"
        f"from: {frm}   to: {to}\n"
        f"receipt: {receipt}\n"
        f"credit: {hops.strip()}\n"
        f"verification: {tier} ({found_by})"
    )


def verify_receipt(to: str, receipt: str, *,
                   store: Optional[Any] = None) -> Tuple[bool, str]:
    """Is `receipt` a real learning record attributable to agent `to`?
    Returns (ok, found_by). Attribution: exact agent_id match; fuzzy id match (an
    experiment id CONTAINING the slug) still requires the agent_id to match -- a toast
    must never credit the wrong seat."""
    if store is None:
        try:
            from core.learning.learning_store import get_learning_store
            store = get_learning_store()
        except Exception as e:
            return False, f"store unreachable ({type(e).__name__})"
    rec = str(receipt).strip()
    try:
        hit = store._load_experiment(rec)
        if hit:
            aid = str(hit.get("agent_id") or "")
            if aid == str(to):
                return True, "exact experiment id"
            if not aid or aid in ("unknown", "me"):
                return True, f"exact experiment id (unattributed agent_id={aid!r})"
            return False, f"experiment {rec!r} belongs to {aid}, not {to}"
    except Exception as e:
        return False, f"store lookup failed ({type(e).__name__})"
    # fuzzy: substring match over all experiment names, still agent-scoped
    try:
        all_l = store.load_all_learnings_from_store()
    except Exception as e:
        return False, f"store scan failed ({type(e).__name__})"
    needle = rec.lower()
    cands = [l for l in all_l
             if needle in str(l.get("experiment_name") or l.get("id") or "").lower()]
    if not cands:
        return False, f"no experiment matching {rec!r} in the store"
    mine = [l for l in cands if str(l.get("agent_id") or "") == str(to)]
    if mine:
        return True, f"fuzzy id match ({len(mine)} record(s) for {to})"
    owners = sorted({str(l.get('agent_id') or '?') for l in cands})
    return False, f"matches exist but belong to {', '.join(owners)}, not {to}"


def send(frm: str, to: str, receipt: str, hops: str, *,
         force: bool = False,
         bus_send: Optional[Callable[[str, str, str], Any]] = None,
         note_write: Optional[Callable[[str, str], Any]] = None,
         store: Optional[Any] = None) -> Dict[str, Any]:
    """One toast, both surfaces. Refuses loudly on a bad receipt unless forced.
    bus_send(to, kind, text) / note_write(title, body) are INJECTED; defaults are the
    real doors (bifrost bus + knowledge notes)."""
    if not str(hops or "").strip():
        raise ValueError("toast needs the credit (what did their lesson save you?) -- "
                         "gratitude without the receipt-detail is a hollow ping")
    hops = str(hops).strip()
    if len(hops) > MAX_BODY:
        raise ValueError(f"toast credit clipped at {MAX_BODY} chars ({len(hops)} given) -- "
                         "short is the form; longer gratitude wants a note directly")
    ok, found_by = verify_receipt(to, receipt, store=store)
    tier = "VERIFIED" if ok else "GUESS"
    if not ok and not force:
        raise ValueError(f"toast REFUSED: receipt does not verify ({found_by}). "
                         "Re-check the experiment name, or pass force=True to send it "
                         "honestly labeled GUESS.")
    line = render_line(frm, to, receipt, hops, tier)
    title = note_title(to, receipt)
    note = render_note(frm, to, receipt, hops, tier, found_by)
    res: Dict[str, Any] = {"tier": tier, "found_by": found_by, "line": line,
                           "note_title": title, "bus": "skipped", "note": "skipped"}
    if bus_send is None:
        def bus_send(_to: str, kind: str, text: str) -> Any:   # the real door (lazy import)
            from core.comm.bifrost import get_bus
            return get_bus().send(frm, _to, kind, text)
    try:
        bus_send(to, "note", line)          # 'note' kind: delight, no expectation to answer
        res["bus"] = "sent"
    except Exception as e:
        res["bus"] = f"failed ({type(e).__name__}) -- bus offline? the durable note still lands"
    if note_write is None:
        def note_write(_title: str, body: str) -> Any:
            from core.learning.agent_memory import get_agent_memory
            # decide_with_retry: re-toast of the same (to, receipt) SUPERSEDES its own
            # prior note under CAS (the RB-8-safe path cmd_note itself rides).
            return get_agent_memory().decide_with_retry(_title, body, curated=True)
    try:
        note_write(title, note)
        res["note"] = "written"
    except Exception as e:
        res["note"] = f"failed ({type(e).__name__})"
    return res


def render_result(res: Dict[str, Any]) -> str:
    return (f"toast [{res['tier']}] ({res['found_by']})\n"
            f"  bus : {res['bus']}\n"
            f"  note: {res['note']} -> {res['note_title']}\n"
            f"  line: {res['line']}")
