"""Dispatcher (Bifrost Mesh W2): one resident process that turns doorbell notices into wakes.

`PSUBSCRIBE bifrost:bell:*` -> on a notice, do a NON-CONSUMING digest peek for the target agent,
apply a DUMB (zero-token, no-LLM) escalation gate, and dispatch via a per-runtime turn-starter
(the injected `invoker` = the W3 wake-adapter registry). The Stream + cursor remain the durable
truth, so a dropped bell or a dead dispatcher only DELAYS a wake (caught by the next boot peek or
the periodic safety re-scan) -- it never loses a message.

The triage (`should_escalate` / `handle_notice`) is pure and unit-tested without pub/sub; `run()` is
the live loop. `note`/`chat` never escalate (low-token: they're seen on the next natural boot);
only actionable kinds or high importance spawn a turn.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from core.comm.bus import BELL_NS, Bus

# Kinds/importance that justify spending a turn now (everything else waits for the next boot peek).
ESCALATE_KINDS = {"request", "handoff", "question", "blocker"}
ESCALATE_IMPORTANCE = {"high", "urgent"}


def should_escalate(notice: Dict[str, Any]) -> bool:
    """Zero-token gate: does this notice warrant waking the agent NOW?"""
    kind = str(notice.get("kind") or "").lower()
    imp = str(notice.get("importance") or "").lower()
    return kind in ESCALATE_KINDS or imp in ESCALATE_IMPORTANCE


def _default_peek(agent: str) -> List[str]:
    """Non-consuming digest peek (cursor unchanged) -> compact lines. Never raises."""
    try:
        from agent.bifrost_pull import peek_inbox, format_digest_line
        return [format_digest_line(m) for m in peek_inbox(agent, limit=8)]
    except Exception:
        return []


class Dispatcher:
    """Wakes the agents it manages when actionable mail arrives. `invoker(agent, digest, notice)`
    is the per-runtime turn-starter (W3); the default is a no-op recorder (observe, don't spawn)."""

    def __init__(self, agents: Iterable[str], *, invoker: Optional[Callable] = None,
                 peek: Optional[Callable] = None, client: Optional[Any] = None):
        self.agents = set(agents)
        self._invoker = invoker or (lambda agent, digest, notice: None)
        self._peek = peek or _default_peek
        self._client = client                      # redis client for pub/sub; None -> connect on run()
        self.woke: List[Dict[str, Any]] = []       # audit trail of dispatch decisions

    def _targets(self, notice: Dict[str, Any]) -> List[str]:
        """Which of MY agents this notice is for (broadcast = all but the sender; direct = the recipient)."""
        frm, to = notice.get("frm"), notice.get("to")
        if to in ("*", None):
            return sorted(a for a in self.agents if a != frm)
        return sorted(self.agents & {to})

    def handle_notice(self, notice: Dict[str, Any]) -> Dict[str, Any]:
        """Pure triage + dispatch for one bell notice. Returns a decision record (testable)."""
        results = []
        escalate = should_escalate(notice)
        for agent in self._targets(notice):
            if not escalate:
                results.append({"agent": agent, "escalated": False, "dispatched": False, "digest": []})
                continue
            digest = self._peek(agent)
            dispatched = bool(self._invoker(agent, digest, notice))
            rec = {"agent": agent, "escalated": True, "dispatched": dispatched, "digest": digest}
            results.append(rec)
            self.woke.append({"at": time.time(), **rec, "notice": notice})
        return {"to": notice.get("to"), "escalated": escalate, "results": results}

    # ------------------------------------------------------------------ live loop
    def run(self, *, once: bool = False, idle_timeout: float = 1.0) -> int:
        """PSUBSCRIBE the doorbell and dispatch notices. `once=True` handles a single notice then
        returns (for demos/tests). Returns the number of notices handled. Best-effort; never raises
        into the caller on a malformed notice."""
        client = self._client or Bus("dispatcher")._client
        if client is None:
            return 0
        ps = client.pubsub(ignore_subscribe_messages=True)
        ps.psubscribe(f"{BELL_NS}:*")
        handled = 0
        try:
            while True:
                msg = ps.get_message(timeout=idle_timeout)
                if msg and msg.get("type") in ("pmessage", "message"):
                    try:
                        self.handle_notice(json.loads(msg.get("data") or "{}"))
                        handled += 1
                    except Exception:
                        pass
                    if once:
                        break
                elif once and msg is None:
                    break                          # once + nothing within the timeout
        finally:
            try:
                ps.close()
            except Exception:
                pass
        return handled
