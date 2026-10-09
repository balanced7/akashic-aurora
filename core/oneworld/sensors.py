"""Real sensors for the floor (spec d622ac s4): each a small adapter that replaces one "not wired" entry.

The floor shipped with all four sensors honestly UNWIRED (W3). This module wires them one at a time. Each sensor is
a pure function of injectable sources, so it is pinned without a live Redis, and each is THREE-state like every
floor sensor: FIRED, CLEAR, or UNAVAILABLE -- a read that fails is named, never reported as clear.

undeliverable_mail -- entry 1, Navi's: "mail to an absent seat is more urgent, never ghost mail." Crosses the roster
(who has a live or stale incarnation) with the shadow mailbox (core.comm.mailbox: what is addressed to each agent and
whether it was handled). Wired 2026-10-09, the morning Sunshine came up dead after a reboot: exactly the case where
mail can wait for a reader who is not coming.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from core.oneworld.floor import CLEAR, FIRED, UNAVAILABLE, Signal

# A STALE seat is beating slowly, probably idle -- present, not gone. Only seats with neither are absent.
PRESENT_STATES = frozenset({"LIVE", "STALE"})
NS = "bifrost"


def _roster_rows() -> List[Dict[str, Any]]:
    from core.comm import roster
    return roster.by_agent(roster.roster(NS))


def _mailbox_query(ns: str, agent: str) -> Dict[str, Any]:
    from core.comm import mailbox
    return mailbox.query(ns, agent)


def _obligation_kinds() -> frozenset:
    """Mail that carries an obligation for its recipient, DERIVED from the house's canonical policy sets, never
    declared here (check_kind_policy blocked a hand-written copy on 2026-10-09): the mailbox's long-retention kinds
    (handoff, request, question, blocker) and the kinds that settle an expectation (reply, handoff, completion --
    RB-29). Chat and notes are not obligations."""
    from core.comm import expectations, mailbox
    return frozenset(mailbox.LONG_KINDS) | frozenset(expectations.ANSWER_KINDS)


def _age_s(ts: str, now_s: float) -> Optional[float]:
    try:
        return max(0.0, now_s - datetime.fromisoformat(str(ts)).timestamp())
    except (TypeError, ValueError):
        return None


def _hours(s: Optional[float]) -> str:
    return "age unknown" if s is None else f"oldest {s / 3600:.1f}h"


def undeliverable_mail(roster_rows: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                       mailbox_query: Optional[Callable[[str, str], Dict[str, Any]]] = None, *,
                       ns: str = NS, now_s: Optional[float] = None) -> Signal:
    """FIRED when a seat with no live or stale incarnation holds unhandled directed obligations; CLEAR when both
    reads worked and none do; UNAVAILABLE when the roster, or the mailbox of an absent seat, could not be read."""
    rows_fn = roster_rows or _roster_rows
    query = mailbox_query or _mailbox_query
    now_s = time.time() if now_s is None else now_s
    try:
        rows = rows_fn()
    except Exception as exc:  # noqa: BLE001 -- blind, named
        return Signal(UNAVAILABLE, f"roster unreadable ({type(exc).__name__}: {exc}): cannot say who is absent")
    absent = sorted({str(r.get("agent")) for r in rows or [] if str(r.get("state")) not in PRESENT_STATES})

    try:
        obligations = _obligation_kinds()
    except Exception as exc:  # noqa: BLE001 -- without the canonical sets the sensor cannot classify: blind
        return Signal(UNAVAILABLE, f"cannot load the canonical kind sets ({type(exc).__name__}: {exc})")
    hits: List[str] = []
    blind: List[str] = []
    for agent in absent:
        try:
            q = query(ns, agent)
        except Exception as exc:  # noqa: BLE001
            blind.append(f"{agent} ({type(exc).__name__}: {exc})")
            continue
        if not q or not q.get("available"):
            blind.append(f"{agent} ({(q or {}).get('reason') or 'mailbox unavailable'})")
            continue
        pending = [e for e in q.get("entries") or []
                   if e.get("tier") == "unhandled" and e.get("kind") in obligations]
        if pending:
            kinds: Dict[str, int] = {}
            for e in pending:
                kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
            ages = [a for a in (_age_s(e.get("ts"), now_s) for e in pending) if a is not None]
            kind_text = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
            hits.append(f"{agent}: {len(pending)} unhandled directed ({kind_text}), "
                        f"{_hours(max(ages) if ages else None)}, no live incarnation")

    could_not = f"; could not read the mailbox of: {', '.join(blind)}" if blind else ""
    if hits:
        return Signal(FIRED, "; ".join(hits) + could_not)
    if blind:
        return Signal(UNAVAILABLE, f"checked {len(absent)} absent seat(s){could_not}")
    who = f" ({', '.join(absent)})" if absent else ""
    return Signal(CLEAR, f"{len(absent)} absent seat(s){who} hold no unhandled directed mail; "
                         f"agents never seen on the roster are not scanned")


def undeliverable_mail_falsifier() -> Signal:
    """Drive the REAL sensor logic with an absent seat holding an unhandled request. It must fire; if it does not,
    the sensor guards nothing."""
    now_s = time.time()
    ts = datetime.fromtimestamp(now_s - 3600).astimezone().isoformat()
    return undeliverable_mail(
        roster_rows=lambda: [{"agent": "falsifier-seat", "state": "DEAD"}],
        mailbox_query=lambda ns, agent: {"available": True,
                                         "entries": [{"kind": "request", "tier": "unhandled", "ts": ts}]},
        now_s=now_s)
