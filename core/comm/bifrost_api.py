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

import os
from typing import Any, Dict, List, Optional

from core.comm.bus import Bus
from core.comm import control, nudge


def _id_key(sid: str):
    """Sort key for Redis stream ids. "$" (tail) sorts above everything; "0" (virgin cursor)
    and malformed ids sort BELOW every real id -- "0" must lose to "0-0" (seat-2 review
    finding 1: the parse branch made them tie). Plain string compare is WRONG for ids
    ("...-10" < "...-9" lexicographically)."""
    if sid == "$":
        return (float("inf"), float("inf"))
    if sid == "0":
        return (-1, -1)
    try:
        ms, _, seq = str(sid).partition("-")
        return (int(ms), int(seq or 0))
    except (ValueError, TypeError):
        return (-1, -1)


class BifrostAPI:
    """One agent's handle on Bifrost. Wraps the bus + control/nudge/wake so an agent needs one import."""

    def __init__(self, agent: str, namespace: Optional[str] = None):
        self.agent = str(agent)
        self.bus = Bus(self.agent, namespace=namespace) if namespace else Bus(self.agent)
        self._wake_since: Optional[Dict[str, str]] = None   # the wake watcher's LOCAL cursor (P0)
        self._lane_since: Optional[Dict[str, str]] = None   # T045: the lane watcher's LOCAL cursor
        self.last_seat: Optional[Dict[str, Any]] = None     # RB-21: holder info when a consume degraded

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
        """Unread messages. consume=False peeks; consume=True advances the cursor THROUGH
        the RB-21 consumer seat: the claim rides this API instance's stable holder token,
        and a refused claim (live foreign holder) or a fenced commit degrades the read to
        a PEEK -- mail is returned either way, never eaten. After a consume attempt,
        `self.last_seat` is None (we consumed) or the holder's info dict (we degraded) --
        embedders render the teaching from it."""
        if not consume:
            return self.bus.inbox(advance=False)
        from core.comm import runner_lock
        import os
        token = runner_lock.session_holder_token() or f"session:api:{os.getpid()}"
        ok, gen, info = runner_lock.claim_consumer(self.agent, token)
        if not ok:
            self.last_seat = info
            return self.bus.inbox(advance=False)
        status: Dict[str, str] = {}
        msgs = self.bus.inbox(advance=True, generation=gen, commit_status_out=status)
        self.last_seat = (runner_lock.holder(self.agent) or {}) \
            if status.get("status") == "STALE_GENERATION" else None
        return msgs

    def wake_block(self, timeout_ms: int = 120_000) -> List[Any]:
        """Block until a message lands (or timeout), then return it -- WITHOUT consuming. The single
        primitive the wake listener loops on. Returns [] on timeout/offline.

        Detect-only (P0/T017, the T016 Exhibit A fix): the SHARED cursor is never moved, so every
        message the watcher sees remains unread for the real consumer (inbox()/bifrost-sync). Position
        is tracked on a LOCAL in-memory cursor -- skip-kind messages therefore return once (no
        busy-spin) and are never lost. The old advance=True here is what silently ate a directed
        reply on 2026-07-09.

        Local-cursor rules (deepseek red-team F1/F2/F10, research/reviewed/deepseek-p0-design-review):
        - SEED: the shared cursor when the agent has one (pending unconsumed mail must wake the
          watcher armed after it arrived); the CONCRETE stream tail when the shared cursor is
          virgin OR Redis was unreachable at read -- a "0" seed would replay the whole stream as
          "new" (false-wake storm), and the "$" sentinel would skip mail landing BETWEEN two
          blocking reads (a missed-wake hole the T017 pins caught live).
        - FAST-FORWARD: every call lifts the local cursor to at least the shared cursor, so mail a
          concurrent live session already consumed never wakes the watcher; a trimmed-away local
          position degrades to bounded paging from the stream head, not an error loop."""
        if os.environ.get("BIFROST_WAKE_LANE") == "work":
            return self._wake_block_lane(timeout_ms)   # T045 stage 1: watch the WORK LANE only
        if self._wake_since is None:
            seed = dict(self.bus.cursor())
            if seed.get("inbox", "0") == "0" and seed.get("bc", "0") == "0":
                seed = self.bus.tail()             # virgin/offline cursor: only NEW mail wakes
            self._wake_since = seed
        else:
            shared = self.bus.cursor()
            for stream in ("inbox", "bc"):
                candidate = shared.get(stream, self._wake_since.get(stream, "0"))
                if _id_key(candidate) > _id_key(self._wake_since.get(stream, "0")):
                    self._wake_since[stream] = candidate
        nxt: Dict[str, str] = {}
        msgs = self.bus.wait(timeout_ms=timeout_ms, since=self._wake_since, since_out=nxt)
        if nxt:
            self._wake_since.update(nxt)
        return msgs

    def _lane_streams(self) -> Dict[str, str]:
        """The work-lane pair the T045 watcher reads (logical inbox/bc -> lane keys)."""
        from core.comm import packet_spec
        ns = self.bus.ns
        return {"inbox": packet_spec.lane_stream_key(ns, "work", to=self.agent),
                "bc": packet_spec.lane_stream_key(ns, "work")}

    def _lane_tails(self) -> Dict[str, str]:
        """Concrete last-ids of the lane pair -- the A4 tail-at-flip seed (dual-write history
        is a soak, never mail; '$' would skip mail landing between reads, T017)."""
        out: Dict[str, str] = {}
        for logical, key in self._lane_streams().items():
            try:
                last = self.bus._client.xrevrange(key, count=1)
                out[logical] = str(last[0][0]) if last else "0"
            except Exception:
                out[logical] = "0"
        return out

    def _wake_block_lane(self, timeout_ms: int) -> List[Any]:
        """T045 stage 1 (T039b, wake-listener-first): watch the WORK LANE only. Trace/sig
        floods and stranded broadcasts are STRUCTURALLY invisible -- the 2026-07-14 infinite
        wake loop (1280 legacy traces hiding one handoff) cannot be represented here.

        Legacy remains the CONSUME substrate during dual-write, so two rules keep the T017
        missed-wake hole closed:
        (1) ARM-TIME PENDING CHECK -- unconsumed legacy mail wakes immediately (a fresh
            watcher must never sleep past mail that arrived before it armed);
        (2) the lane cursor is caller-owned and seeded at the lane TAILS (A4 tail-at-flip).
        Detect-only, same as the legacy path: nothing here consumes."""
        if self._lane_since is None:
            # 1ms peek, NOT 0 -- in xread semantics block=0 means WAIT FOREVER (caught live:
            # the L2/L5 pins hung the suite on exactly this in the first run).
            pending = self.bus.wait(timeout_ms=1, limit=10)   # shared-cursor peek, no advance
            if pending:
                return pending
            self._lane_since = self._lane_tails()
        nxt: Dict[str, str] = {}
        msgs = self.bus.wait(timeout_ms=timeout_ms, since=self._lane_since, since_out=nxt,
                             streams=self._lane_streams())
        if nxt:
            self._lane_since.update(nxt)
        return msgs

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
