"""peer_ready -- make the peer EXIST before asking it something (T197c).

Sol's vision write-up, relayed by Daniil 2026-08-06: "Bifrost should optimize for
collaboration first and infrastructure second... treat the new DeepSeek launcher as a
successful vertical slice whose ergonomics should become the front door to Bifrost."
This is that door. The guiding line -- "make one direct collaboration flow so easy that
nobody needs to understand Bifrost to use it" -- is the acceptance test: the caller says
who to ask and what to ask, and never learns the words runner, lock, cursor or lane.

WHY IT EXISTS, measured. On 2026-08-06 the friction reader read 32 closed ask-episodes:
0 ANSWERED, 26 DEAD (81.2%). Every launchable agent sat at `never_launched`. T197b made
that visible in one second instead of thirty minutes -- but visibility is not a peer. The
operator still had to know which tag to launch, from a registry where four tags share one
agent_id. This closes that last hop.

IT NEVER MAKES THE CALLER INTO A SEAT. The T171 law stands: an ask is a call, not a seat.
Spawning a seat FOR THE PEER is the launcher's job, delegated to it here -- ask_peer
still takes no lock, no cursor, no mailbox and no heartbeat of its own.

WHAT IT REFUSES TO GUESS. `deepseek` resolves to FOUR registry tags (deepseek,
deepseek-build, deepseek-think, deepseek-write), all with agent_id `deepseek`. Picking
one silently would be an unowned decision about which model configuration answers your
question. Ambiguity returns `ambiguous` WITH the candidate list, and the caller chooses.

THE READINESS ORACLE IS attendance(), NOT A SLEEP. deepseek's fence (2026-08-06) named
"boots but never consumes" as the failure autolaunch invites, and a fixed sleep would
report success for exactly that case. Polling the same verdict the rest of T197 uses
means launch success is defined as "a probe now says ATTENDED", not "we waited a while".
Its stated limit rides in BLIND below: ATTENDED proves a process is beating, never that
it is reading the lane your message went to (the wrong-lane class is real and separate).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

# Named blindness, structural rather than remembered -- the same law the friction reader
# follows: a report that names no blindness is claiming omniscience.
BLIND = [
    "ATTENDED means a process is beating, NOT that it consumes the lane this ask rides "
    "-- a healthy seat reading the wrong lane still never answers",
    "readiness is polled, so a peer that comes up AFTER the wait still reads as "
    "never_attended here; the durable expectation is what actually catches it",
    "the launcher's own singleton gate is the only single-flight -- two callers racing "
    "the same absent peer rely on runner_lock, not on anything in this module",
]


def resolve_tag(peer: str, registry: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Which registry tag launches this peer? PURE (no I/O), so the ambiguity rule is
    testable without a launcher.

    Exact tag name wins outright -- `--peer deepseek-think` means that one. Otherwise a
    peer matches by agent_id, and matching EXACTLY ONE tag is required: `deepseek` maps
    to four, and choosing among them is a decision about which configuration answers the
    question. That belongs to the caller, so it is returned as a choice, never resolved
    by an ordering nobody declared.
    """
    p = str(peer or "")
    for row in registry or []:
        if str(row.get("tag") or "") == p:
            return {"ok": True, "tag": p, "candidates": [p]}
    hits = [str(r.get("tag")) for r in (registry or [])
            if str(r.get("agent_id") or "") == p]
    if len(hits) == 1:
        return {"ok": True, "tag": hits[0], "candidates": hits}
    if not hits:
        return {"ok": False, "reason": "no_tag", "candidates": [],
                "why": f"'{p}' is not a launchable agent -- no registry tag names it"}
    return {"ok": False, "reason": "ambiguous", "candidates": sorted(hits),
            "why": (f"'{p}' maps to {len(hits)} launchable tags ({', '.join(sorted(hits))}) "
                    f"-- name one; which configuration answers is your call, not mine")}


def _attending(peer: str) -> tuple:
    """(is_attending, state, why) from THE verdict (T155). Fail-open: an unreadable
    probe is UNKNOWN, never a fabricated death."""
    try:
        from core.comm.liveness import attendance
        v = attendance(str(peer))
        return v.state == "ATTENDED", str(v.state), str(v.reason or "")
    except Exception as e:
        return False, "UNKNOWN", f"attendance probe unreadable ({e.__class__.__name__})"


def ensure_peer(peer: str, *, wait_s: float = 60.0, poll_s: float = 2.0,
                launcher=None, sleep=time.sleep) -> Dict[str, Any]:
    """Make `peer` attending if it can be, and say plainly what happened. Never raises.

    `action` is the honest account, and every value is a state a caller can act on:
      already_attending  it was up; nothing was spawned
      launched           spawned, and a probe then said ATTENDED
      never_attended     spawned, but no probe said ATTENDED inside the wait (this is
                         deepseek's "boots but never consumes" -- reported, not hidden)
      launch_refused     the launcher declined (a live runner holds the lock: correct)
      no_tag / ambiguous nothing was spawned; the caller decides (see `candidates`)

    `sleep` is injected so pins never actually wait.
    """
    peer = str(peer)
    attending, state, why = _attending(peer)
    if attending:
        return {"action": "already_attending", "attending": True, "peer": peer,
                "state": state, "why": why, "tag": None, "blind": list(BLIND)}

    if launcher is None:
        try:
            from core.comm.launcher import get_launcher
            launcher = get_launcher()
        except Exception as e:
            return {"action": "launch_refused", "attending": False, "peer": peer,
                    "state": state, "tag": None,
                    "why": f"launcher unavailable ({e.__class__.__name__})",
                    "blind": list(BLIND)}

    try:
        registry = launcher.registry()
    except Exception as e:
        return {"action": "launch_refused", "attending": False, "peer": peer,
                "state": state, "tag": None,
                "why": f"registry unreadable ({e.__class__.__name__})", "blind": list(BLIND)}

    r = resolve_tag(peer, registry)
    if not r["ok"]:
        return {"action": r["reason"], "attending": False, "peer": peer, "state": state,
                "tag": None, "candidates": r["candidates"], "why": r["why"],
                "blind": list(BLIND)}

    tag = r["tag"]
    try:
        out = launcher.launch(tag) or {}
    except Exception as e:
        return {"action": "launch_refused", "attending": False, "peer": peer,
                "state": state, "tag": tag,
                "why": f"launch raised ({e.__class__.__name__})", "blind": list(BLIND)}
    if not out.get("ok"):
        # A refusal is usually CORRECT -- the launcher's singleton gate declining to
        # spawn a duplicate is the behaviour we want, not an error to route around.
        return {"action": "launch_refused", "attending": False, "peer": peer,
                "state": state, "tag": tag, "pid": out.get("pid"),
                "why": out.get("error") or "launcher refused without a reason",
                "blind": list(BLIND)}

    deadline = time.time() + max(0.0, float(wait_s))
    while True:
        attending, state, why = _attending(peer)
        if attending or time.time() >= deadline:
            break
        sleep(max(0.05, float(poll_s)))

    if attending:
        return {"action": "launched", "attending": True, "peer": peer, "state": state,
                "tag": tag, "pid": out.get("pid"), "why": why, "blind": list(BLIND)}
    return {"action": "never_attended", "attending": False, "peer": peer, "state": state,
            "tag": tag, "pid": out.get("pid"),
            "why": (f"launched {tag} (pid {out.get('pid')}) but no probe said ATTENDED "
                    f"within {wait_s:.0f}s -- it may still be booting, or it boots "
                    f"without consuming"),
            "blind": list(BLIND)}
