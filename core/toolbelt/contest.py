"""
contest (T099 · play tier) -- second a toast with proof (kimi's R2 build).

Daniel's leaderboard ghost was "surfaced 14x / 0 credit" -- lessons that earned credit had
no human-feeling expression. toast (BETA-2) fixed that: gratitude-with-receipt, VERIFIED or
it refuses. But toast is a SOLO act: one seat credits a peer, and the leaderboard counts
distinct-users love. A second seat who ALSO drank from the same well had no door -- sending
a fresh toast creates a NEW credit-note (a parallel claim), not a second signature on the
existing one. The credit loop's social fabric needed its chorus.

contest is that door: "I drank from this well too." One call:
  (a) PROVES the second seat's claim against the learning store (toast's own verifier,
      agent-attributed -- you can only second what actually saved YOU hops);
  (b) APPENDS the signature to the existing toast note (decide_with_retry CAS -- the note
      grows a contesters list, never piles up parallel copies);
  (c) PINGS the toasted peer on the bus (delight NOW, the chorus sound).

Laws (the kimi register, inherited from toast):
  PROVEN     -- the receipt must verify for the CONTESTER too (same store, same attribution
                rule). Unproven seconding is a hollow echo; contest REFUSES unless forced,
                and a forced contest confesses GUESS in both artifacts.
  APPEND-ONLY -- the note's toast-line is untouched; contesters accrue as a list. The
                lesson-identity contract holds: a thread is the verb's biography, never
                edited in place -- contesters are new verses, not revisions.
  INJECTED   -- bus send / note read / note write are injected (the resolve_and_run seam).
                Fail-soft: bus offline still leaves the durable note; the caller is told.

Name: MTG's "contest" is not a card -- but the verb names what it does. It CONTESTS the
silence around a lesson: the first toast says "this worked"; a contest says "this is a
PATTERN, not an accident." Two seats saved by the same lesson is a signal the curator can
weight (bench_reason's killer: credit × distinct voices). Also the fence-seat's native act:
I verify, I second, I contest -- in both directions.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

# toast's verifier is the shared truth: a contest proves itself the same way a toast does.
try:
    from core.toolbelt.toast import verify_receipt, note_title, NOTE_TITLE_PREFIX
except Exception:  # pragma: no cover - toast is a sibling module; same package in prod
    from toast import verify_receipt, note_title, NOTE_TITLE_PREFIX  # type: ignore

MAX_BODY = 240          # a second voice is shorter than the first; chorus, not solo.


def render_contest_line(frm: str, to: str, receipt: str, hops: str, tier: str) -> str:
    """The bus payload -- one line, the second signature confessed with its tier."""
    body = f"\U0001f9eb @{to}: {hops.strip()}"
    tag = "[CONTESTED VERIFIED]" if tier == "VERIFIED" else "[CONTESTED GUESS :unverified]"
    return f"{tag} {body} (same receipt: {receipt.strip()})"


def render_contest_verse(frm: str, hops: str, tier: str, found_by: str,
                         when: Optional[str] = None) -> str:
    """One appended verse for the durable note -- the chorus line."""
    return (f"\ncontested ({tier}) -- {when or time.strftime('%Y-%m-%d %H:%M')}\n"
            f"  by: {frm}\n"
            f"  credit: {hops.strip()}\n"
            f"  verification: {tier} ({found_by})")


def send(frm: str, to: str, receipt: str, hops: str, *,
         force: bool = False,
         bus_send: Optional[Callable[[str, str, str], Any]] = None,
         note_read: Optional[Callable[[str], Optional[str]]] = None,
         note_write: Optional[Callable[[str, str], Any]] = None,
         store: Optional[Any] = None) -> Dict[str, Any]:
    """One contest: prove, append, ping. Refuses loudly on an unproven receipt unless forced.

    bus_send(to, kind, text) -- the live ping.
    note_read(title) -> prior body or None -- the CAS read (RB-8: re-read before write).
    note_write(title, body) -- the CAS write (decide_with_retry semantics).
    store -- the learning store (tests pass a fake).
    """
    frm, to = str(frm), str(to)
    if frm == to:
        raise ValueError("contest is a chorus, not a solo: you cannot second your own toast")
    if not str(hops or "").strip():
        raise ValueError("contest needs the credit (what did the same lesson save YOU?) -- "
                         "a second voice without its own receipt-detail is an echo")
    hops = str(hops).strip()
    if len(hops) > MAX_BODY:
        raise ValueError(f"contest credit clipped at {MAX_BODY} chars ({len(hops)} given) -- "
                         "chorus is shorter than solo; longer wants a fresh toast")

    # (a) PROVE -- the contester's claim verifies for THEM (agent-attributed, like toast).
    ok, found_by = verify_receipt(to, receipt, store=store)
    tier = "VERIFIED" if ok else "GUESS"
    if not ok and not force:
        raise ValueError(f"contest REFUSED: receipt does not verify ({found_by}). "
                         "Re-check the experiment name, or pass force=True to second it "
                         "honestly labeled GUESS.")

    title = note_title(to, receipt)
    line = render_contest_line(frm, to, receipt, hops, tier)
    verse = render_contest_verse(frm, hops, tier, found_by)
    res: Dict[str, Any] = {"tier": tier, "found_by": found_by, "line": line,
                           "note_title": title, "bus": "skipped", "note": "skipped"}

    # (b) APPEND -- read the existing toast note (CAS re-read), append the verse, write back.
    if note_read is None:
        def note_read(_title: str) -> Optional[str]:
            from core.learning.agent_memory import get_agent_memory
            mem = get_agent_memory()
            try:                                  # latest-by-title; None when absent
                cur = mem.latest(_title)
                return cur.get("decision") if cur else None
            except Exception:
                return None
    if note_write is None:
        def note_write(_title: str, body: str) -> Any:
            from core.learning.agent_memory import get_agent_memory
            return get_agent_memory().decide_with_retry(_title, body, curated=True)
    try:
        prior = note_read(title)
        body = (prior.rstrip() + "\n" + verse) if prior else (
            f"TOAST-THREAD ({tier}) -- opened by a contest (no prior toast found)\n"
            f"receipt: {receipt}\n" + verse.lstrip("\n")
        )
        note_write(title, body)
        res["note"] = "appended" if prior else "opened (no prior toast; contest stands alone)"
    except Exception as e:
        res["note"] = f"failed ({type(e).__name__})"

    # (c) PING -- the live chorus sound; fail-soft, the durable note is the credit.
    if bus_send is None:
        def bus_send(_to: str, kind: str, text: str) -> Any:
            from core.comm.bifrost import get_bus
            return get_bus().send(frm, _to, kind, text)
    try:
        bus_send(to, "note", line)
        res["bus"] = "sent"
    except Exception as e:
        res["bus"] = f"failed ({type(e).__name__}) -- bus offline? the durable note still lands"

    return res


def render_result(res: Dict[str, Any]) -> str:
    return (f"contest [{res['tier']}] ({res['found_by']})\n"
            f"  bus : {res['bus']}\n"
            f"  note: {res['note']} -> {res['note_title']}\n"
            f"  line: {res['line']}")
