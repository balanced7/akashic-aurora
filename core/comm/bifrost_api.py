"""bifrost.api -- the one door an agent uses to join and work the Bifrost bus.

Instead of wiring Bus + control + nudge + the wake listener + presence separately, an agent onboards
with a single object:

    api = BifrostAPI("myagent")
    api.online()                       # announce presence
    api.broadcast("hello, I'm here")   # or api.send("claude", "...")
    for m in api.inbox(): ...          # read what's waiting
    api.nudge("claude", "look now")    # or api.steer(...) -- signal a peer
    # stay wakeable from idle: arm  api.wake_cmd  as a background task

The elegant artifact that gathers the free-floating bus primitives (send / receive / wake / presence /
signals / intent) behind one agent-facing interface. Every method is a thin, honest delegation to the
underlying primitive -- no new behavior, just one place to reach them. Fail-open like the primitives:
a bus outage degrades to no-ops / empty, never an exception into the agent's loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.comm.bus import Bus
from core.comm import control, nudge


class BifrostAPI:
    """One agent's handle on Bifrost. Wraps the bus + control/nudge/wake so an agent needs one import."""

    def __init__(self, agent: str):
        self.agent = str(agent)
        self.bus = Bus(self.agent)

    @property
    def online_now(self) -> bool:
        return bool(self.bus.online)

    # ---- send ----
    def send(self, to: str, text: Any, kind: str = "chat", **meta) -> Optional[str]:
        """Message one agent (to='*' or 'all' broadcasts). Returns the message id, or None if offline."""
        m: Dict[str, Any] = {"hops": 0, "via": f"{self.agent}-api"}
        m.update(meta)
        if to in (None, "*", "all"):
            return self.bus.broadcast(kind, text, meta=m)
        return self.bus.send(str(to), kind, text, meta=m)

    def broadcast(self, text: Any, kind: str = "inform", **meta) -> Optional[str]:
        return self.send("*", text, kind, **meta)

    # ---- receive / wake ----
    def inbox(self, *, consume: bool = False) -> List[Any]:
        """Unread messages. consume=False peeks; consume=True advances the cursor."""
        return self.bus.inbox(advance=consume)

    def wake_block(self, timeout_ms: int = 120_000) -> List[Any]:
        """Block until a message lands (or timeout), then return it. The single primitive the wake
        listener loops on. Returns [] on timeout/offline."""
        return self.bus.wait(timeout_ms=timeout_ms, advance=True)

    @property
    def wake_cmd(self) -> str:
        """The command to arm this agent's wake listener (run it as a background task so its completion
        re-invokes an idle, turn-based agent). Onboarding: 'give an agent its wake_cmd and it's reachable'."""
        return f"py scripts/bifrost_wake.py --agent {self.agent}"

    # ---- presence ----
    def online(self, card: Optional[Dict[str, Any]] = None) -> bool:
        """Announce presence (auto-expires; call again to refresh). Returns False if the bus is offline."""
        return self.bus.register(card=card)

    def who(self) -> List[Dict[str, Any]]:
        """Everyone currently present on the bus."""
        return self.bus.presence()

    # ---- signals ----
    def nudge(self, to: str, text: str) -> Optional[str]:
        """HARD interrupt a peer: set its barge-in flag AND send a nudge it must look at now."""
        nudge.nudge(str(to), by=self.agent, reason=text)
        return self.send(to, text, kind="nudge")

    def steer(self, to: str, text: str) -> bool:
        """SOFT steer a peer: queue a fact it folds into its CURRENT task between rounds (no stop)."""
        return nudge.steer_push(str(to), self.agent, text)

    # ---- coordination: planning round (a brief council before work) ----
    def plan(self, what: str, scope=None, estimate: str = "", intent: str = "") -> Dict[str, Any]:
        """Propose a plan in the current round (what / scope / estimate / intent tag). Returns the round
        state with the green/amber/red conflict verdict. Delegates to core.coord.intent.propose."""
        from core.coord import intent as _intent
        return _intent.propose(self.agent, {"what": what, "scope": scope, "estimate": estimate, "intent": intent})

    def round_state(self) -> Dict[str, Any]:
        """The current planning round: every proposal + the green/amber/red verdict."""
        from core.coord import intent as _intent
        return _intent.round_state()

    def council(self, context: str = "") -> Dict[str, Any]:
        """Run a full planning round (open -> wait -> verdict). Call after user input, before work."""
        from core.coord import negotiation
        return negotiation.auto_close(triggered_by=self.agent, context=context)

    # ---- coordination: active intent (Policy 0) ----
    def declare(self, intent: str, scope=None) -> Dict[str, Any]:
        """Declare an intent before acting: admitted unless a peer holds the same intent (then yield)."""
        from core.coord import intent as _intent
        return _intent.declare(self.agent, intent, scope)

    def intents(self, *, mine_only: bool = False) -> List[Dict[str, Any]]:
        """The intent influence map -- who's working on what (all agents, or just mine)."""
        from core.coord import intent as _intent
        return _intent.active(agent=self.agent if mine_only else None)

    def covers(self, path: str) -> bool:
        """True iff I hold an active intent whose scope covers `path` (the enforcement backstop)."""
        from core.coord import intent as _intent
        return _intent.covers(self.agent, path)

    def release_intent(self, intent: str) -> bool:
        """Withdraw one of my active intents (work done or abandoned)."""
        from core.coord import intent as _intent
        return _intent.release(self.agent, intent)

    # ---- control ----
    def halted(self) -> bool:
        """True iff this agent is frozen (global pause OR a targeted halt)."""
        return control.is_halted(self.agent)
