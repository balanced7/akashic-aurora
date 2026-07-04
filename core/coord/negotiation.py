"""
Negotiation round — brief window after user input where agents declare plans.

The pattern: user sends a message → a "propose" round opens → agents have PROPOSAL_TIMEOUT seconds
to declare what they intend to do, scope, and estimated timeframe → the environment produces a verdict
(green/amber/red) based on scope conflicts → agents proceed or coordinate.

This prevents the "run over each other" failure mode by making intent declaration a REQUIRED step
in the coordination loop, not an optional courtesy. An agent that doesn't propose has no standing
to claim files.

Uses intent.py's Redis-backed proposal store + the Bifrost bus for announcement.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from core.coord import intent
from core.comm.bus import Bus

ROUND_TIMEOUT = intent.PROPOSAL_TIMEOUT   # seconds


def open_round(triggered_by: str, context: str = "", bus: Optional[Bus] = None) -> Dict[str, Any]:
    """Open a negotiation round. Broadcasts a 'propose' request to all agents with the triggering
    context (the user's message). Agents have ROUND_TIMEOUT seconds to call propose()."""
    b = bus or Bus("coordinator")
    rid = intent._round_id()
    b.broadcast("propose", context, meta={
        "round": rid, "timeout": ROUND_TIMEOUT, "triggered_by": triggered_by,
        "intent": "propose",
    })
    return {"round": rid, "timeout": ROUND_TIMEOUT, "opened": True}


def close_round(bus: Optional[Bus] = None) -> Dict[str, Any]:
    """Close the current round. Returns the final state (verdict + all proposals + conflicts).
    Broadcasts the verdict so agents know whether to proceed, coordinate, or defer."""
    state = intent.round_state()
    b = bus or Bus("coordinator")
    kind = "verdict"
    if state.get("verdict") == "red":
        kind = "halt"  # red verdict = halt, coordinate, re-plan
    b.broadcast(kind, state.get("reason", "round closed"), meta={
        "round": state.get("round", ""), "verdict": state.get("verdict"),
        "proposals": state.get("proposals", []), "conflicts": state.get("conflicts", []),
        "intent": "verdict",
    })
    return state


def auto_close(triggered_by: str, context: str = "", bus: Optional[Bus] = None) -> Dict[str, Any]:
    """Full round: open → wait ROUND_TIMEOUT → close → return verdict. Call this after user input.
    This is the one-shot convenience function the UI or agent loop calls."""
    result = open_round(triggered_by=triggered_by, context=context, bus=bus)
    time.sleep(ROUND_TIMEOUT)
    state = close_round(bus=bus)
    state["round_id"] = result["round"]
    return state
