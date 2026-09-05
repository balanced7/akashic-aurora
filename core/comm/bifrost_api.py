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

import logging
import os
from typing import Any, Dict, List, Optional

from core.comm.bus import Bus
from core.comm import control, nudge

_log = logging.getLogger("bifrost")


def classify_straggler(sha, lane_has) -> str:
    """Is this legacy packet a failed lane WRITE, or just cursor SKEW? (W166)

    MEASURED on prod 2026-08-14, and the measurement took three attempts because the first
    two were measuring the wrong thing. The number that stands, taken through THIS module's
    own _dedup_key and _work_lane_shas AND its own R12 population filter:

        50 peeked legacy packets
        45 work-lane ELIGIBLE (R12 excludes trace/sig-routed kinds)
        45 cursor-skew, 0 lane-write-failed

    A drain over that same traffic reported "14 LEGACY STRAGGLER(S) -- lane write failed
    upstream". Zero of them were.

    The two discarded attempts are recorded because each was wrong in an instructive way.
    A hand-rolled version that read raw stream fields and built its own dedup tuples said
    0/60 -- right answer, mirrored detector, so it was not evidence. Redoing it through this
    module's predicate but NOT its population filter said 5 failed writes, all from conductor
    six days earlier with kinds ledger_update and resolved -- and lane_for() routes both to
    'trace', so the real filter would never have looked at them. Borrowing a detector's
    predicate without its population manufactures defects it would never claim.

    The old test was "not in `seen`", where `seen` holds the dedup keys of THIS batch's work
    read. The two lanes are read from independently-positioned cursors (measured skew that
    day: 33 unread on work, 49 on legacy), so every packet the work read had already passed
    or not yet reached looked like a transport defect. It was reporting cursor skew as a
    failed write, and its text told the reader to "investigate the sender side" -- which is
    where another seat's investigation went.

    Returns: "lane-write-failed" | "cursor-skew" | "unknown". UNKNOWN when the membership
    check cannot run or there is no sha to check: guessing "failed" there is exactly how the
    original alarm earned its false positives.
    """
    if not sha:
        return "unknown"
    try:
        return "cursor-skew" if lane_has(sha) else "lane-write-failed"
    except Exception:
        return "unknown"


def render_straggler_summary(counts: Dict[str, int]) -> str:
    """One honest line. Empty string when there is nothing to report.

    Only the genuinely-absent class earns the transport-defect language; skew is named as
    skew. A diagnostic that cries wolf is worse than no diagnostic, because it spends other
    people's attention -- this one spent a day of it.
    """
    failed = int(counts.get("lane-write-failed", 0))
    skew = int(counts.get("cursor-skew", 0))
    unknown = int(counts.get("unknown", 0))
    if not (failed or skew or unknown):
        return ""
    parts = []
    if failed:
        parts.append(f"{failed} LANE WRITE FAILED (absent from the work lane -- a real "
                     f"transport defect; investigate the sender side)")
    if skew:
        parts.append(f"{skew} cursor-skew (present on the work lane, outside this read's "
                     f"window -- delivery is correct and idempotent, nothing to chase)")
    if unknown:
        parts.append(f"{unknown} unknown (membership uncheckable -- not claimed either way)")
    return "; ".join(parts)


def wake_lane() -> str:
    """Which lane the WAKE watcher should watch. T198, fixed 2026-09-04.

    Found by chronos (Serge's fleet) reading our PUBLIC repo from the outside -- the exact
    value of a peer house: they cannot see our working tree, which is why they catch what
    our own probes step over. The defect: this asked only for BIFROST_WAKE_LANE, which is
    set NOWHERE in the house, while every consumer defaults to BIFROST_CONSUME_LANE=work.
    So detection watched one lane and draining moved the other -- two cursors and two
    meanings of "drained". Live cost, measured on this seat 2026-09-04: eight hand re-arms
    in one day, each preceded by draining BOTH lanes, and a standing instruction in the
    watcher's own banner telling the operator to drain the lane it was not armed on.

    The rule: an explicit BIFROST_WAKE_LANE still wins (a seat may deliberately split the
    planes); absent that, the wake lane FOLLOWS the consume lane, so the thing that wakes
    you and the thing you drain are the same thing by default."""
    return (os.environ.get("BIFROST_WAKE_LANE")
            or os.environ.get("BIFROST_CONSUME_LANE")
            or "").strip()


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


# T045: kinds the lane watcher's arm-time pending check ignores -- display/control-plane
# junk that legitimately sits unconsumed in legacy broadcast. MUST equal
# scripts/bifrost_wake.SKIP_KINDS_LANE (guarded by pin L7; drift would either trap the
# pending check on junk or wake idle seats on noise).
PENDING_SKIP_KINDS = {"trace", "steer", "resolved", "ledger_update", "note", "status"}


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
            # PEEK stays legacy during dual-write: every packet is dual-written, so the
            # legacy peek sees everything without touching any cursor (work_drain's
            # sig/shadow auto-advance makes it consume-shaped -- wrong tool for a peek).
            # Revisit at T047 when legacy retires.
            return self.bus.inbox(advance=False)
        from core.comm import runner_lock
        import os
        token = runner_lock.session_holder_token() or f"session:api:{os.getpid()}"
        ok, gen, info = runner_lock.claim_consumer(self.agent, token)
        if not ok:
            self.last_seat = info
            return self.bus.inbox(advance=False)
        status: Dict[str, str] = {}
        if self.consume_lane_enabled():
            # T045 stage 2 session-door cutover (fence Q3: same-slice). The RB-21 seat +
            # generation fence apply to the LANE hash exactly as to the shared cursor.
            self.bus.lane_flip_if_migrating()
            nxt: Dict[str, str] = {}
            msgs = self.work_drain(timeout_ms=1, since_out=nxt, generation=gen)
            fields = {k: v for k, v in nxt.items() if v}
            if fields:
                status["status"] = self.bus.advance_to(
                    inbox=nxt.get("inbox"), bc=nxt.get("bc"),
                    generation=gen, cursor_key=self.bus.lane_cursor_key())
        else:
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
        if wake_lane() == "work":
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
        is a soak, never mail; '$' would skip mail landing between reads, T017).

        FAULT PATH (stage-1 F2 fix, pin R9): a Redis blip during the tails read must yield
        '$' (new-entries-only), NEVER '0' -- a '0' seed replays the whole lane history as
        mail (false-wake storm). '$' degrades to a bounded one-message-class loss (mail
        landing between two reads), which beats the storm; deepseek fence verdict adopted."""
        out: Dict[str, str] = {}
        for logical, key in self._lane_streams().items():
            try:
                last = self.bus._client.xrevrange(key, count=1)
                out[logical] = str(last[0][0]) if last else "0"
            except Exception:
                out[logical] = "$"
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
            # Only WAKE-WORTHY pending mail counts (caught live, first lane soak 2026-07-14):
            # nothing consumes legacy broadcast junk, so skip-kind traces pending there would
            # otherwise trap this check forever -- lane_since never seeds and the watcher
            # busy-peeks legacy for its whole deadline instead of watching the lane.
            # Keep PENDING_SKIP_KINDS == bifrost_wake.SKIP_KINDS_LANE (parity pin L7).
            live = [m for m in pending
                    if str(getattr(m, "kind", "")) not in PENDING_SKIP_KINDS]
            # SEED BEFORE RETURNING. Returning `live` without seeding meant the next call
            # peeked again, found the same mail (detect-only never consumes -- T017), and
            # returned instantly again: the "blocking" read never blocked for as long as any
            # wake-worthy mail sat undrained. Measured 2026-07-25: 20% of one core burned
            # continuously by an idle watcher, 6,202,600 twins deduped in one 3.97h life.
            #
            # The comment above already names this trap for SKIP-kinds ("lane_since never
            # seeds and the watcher busy-peeks for its whole deadline"). The identical trap
            # fires for WAKE-WORTHY kinds the seat cannot drain -- e.g. legacy-lane twins
            # that a work-lane consume does not clear. Seeding here closes both.
            #
            # Nothing is lost: pending mail is still returned to this caller exactly once,
            # and detect-only leaves it on the shared cursor for the real consumer.
            self._lane_since = self._lane_tails()
            if live:
                # VISIBILITY MARKER -- required by kimi's verify, and the fix is a WORKAROUND
                # without it. Before this change the undrainable-mail condition announced
                # itself loudly: 20% of a core and a twin counter in the millions. Seeding
                # silences that. The condition does NOT go away -- the same wake-worthy mail
                # sits on the shared cursor forever, and it can MASK genuinely new mail
                # arriving behind it (deepseek's missed-wake attack: a legacy-only straggler
                # is no longer re-peeked, and the lane read cannot see it).
                #
                # So the alarm moves here rather than disappearing: seeding over NON-EMPTY
                # pending means "this seat has wake-worthy mail its consume path cannot
                # clear". Same fails-open genus kimi caught twice already today (the census
                # OK-line, the FileStore silent copy) -- a component that stops reporting a
                # problem while the problem persists.
                self._pending_at_seed = len(live)
                try:
                    # Do NOT promise the next arm is fixed. _lane_since is PER-PROCESS and every
                    # arm is a NEW process, so this seed dies with the call that set it -- we
                    # return `live` immediately below and exit. The old text ("the watcher will
                    # now block correctly") was true for a future that never arrives, and that is
                    # the recurrence engine: the reader believes it and re-arms instead of
                    # draining. 5 identical arms 2026-07-31, 6 on 2026-07-25.
                    # Name the lane we PEEK -- it is not the lane the operator armed.
                    # W167: SAY WHAT IS WORKING, not only what will not help. The warning
                    # below is true and it was still read as "this seat is broken" by three
                    # seats in one day (and by 5 arms on 2026-07-31, 6 on 2026-07-25 -- the
                    # counts this comment already carried). Each concluded the watcher was
                    # dead and stopped arming. It is not: this seeds ONCE, returns these
                    # messages to the caller, and the loop then blocks correctly for the rest
                    # of the process -- which is why the arm that prints this goes on to fire
                    # on real mail or to end with a planned "deadline self-cycle".
                    #
                    # A line that states only the failure half of a true statement gets read
                    # as total failure. That is the same defect class as the straggler alarm
                    # (W166) and it cost the same currency: other people's attention.
                    _log.warning(
                        "wake: ARMED and watching. Seeded the lane cursor past %d already-seen "
                        "wake-worthy message(s) (kinds: %s) -- this arm is live and will fire on "
                        "new mail. The seed is per-process and does NOT carry to the next arm, so "
                        "if you see this line again the pending set is not clearing and RE-ARMING "
                        "WILL NOT REDUCE IT (the watcher is fine either way). Detection PEEKS the "
                        "legacy lane, not the lane you armed, so drain that one: "
                        "BIFROST_CONSUME_LANE=legacy py agent_cli.py bifrost-sync %s --consume",
                        len(live),
                        ",".join(sorted({str(getattr(m, "kind", "?")) for m in live})),
                        getattr(self, "agent", "<agent>"),
                    )
                except Exception:
                    pass
                return live
        nxt: Dict[str, str] = {}
        msgs = self.bus.wait(timeout_ms=timeout_ms, since=self._lane_since, since_out=nxt,
                             streams=self._lane_streams())
        if nxt:
            self._lane_since.update(nxt)
        return msgs

    # ---- T045 stage 2: the lane-mode CONSUME door ----
    @staticmethod
    def consume_lane_enabled() -> bool:
        """The stage-2 strangler gate: BIFROST_CONSUME_LANE=work flips a consumer's reads
        onto the lanes; unset = legacy path byte-identical (flip is per-process)."""
        return os.environ.get("BIFROST_CONSUME_LANE") == "work"

    def _sig_streams(self) -> Dict[str, str]:
        """The sig-lane pair (fidelity-ladder traffic: nudge/steer/halt/pause)."""
        from core.comm import packet_spec
        ns = self.bus.ns
        return {"inbox": packet_spec.lane_stream_key(ns, "sig", to=self.agent),
                "bc": packet_spec.lane_stream_key(ns, "sig")}

    @staticmethod
    def _dedup_key(m) -> tuple:
        """Logical identity of a packet ACROSS its dual-write twins (lane copy and legacy
        copy carry identical env fields but different stream auto-ids)."""
        return (str(getattr(m, "frm", "")), str(getattr(m, "ts", "")),
                str(getattr(m, "kind", "")))

    #: How far back to look when asking "is this packet on the work lane at all?".
    #: Bounded on purpose: the question only matters for recent traffic, and an unbounded
    #: XRANGE on every drain would make a diagnostic cost more than the delivery it explains.
    #: A packet older than this window classifies UNKNOWN rather than being called a defect.
    LANE_MEMBERSHIP_WINDOW = 500

    def _work_lane_shas(self) -> set:
        """Dedup keys currently on this agent's WORK lane streams (W166).

        Used only to tell a failed lane write apart from cursor skew. Read from the STREAM,
        deliberately not from the cursor -- the cursor's position is the very thing that made
        skew look like a defect.
        """
        out = set()
        try:
            keys = self.bus._lane_keys("work")
            client = self.bus._client
            for stream in (keys.get("inbox"), keys.get("bc")):
                if not stream:
                    continue
                for _sid, fields in client.xrevrange(stream, "+", "-",
                                                     count=self.LANE_MEMBERSHIP_WINDOW):
                    g = fields.get if hasattr(fields, "get") else (lambda k, d="": d)
                    out.add((str(g("frm", "") or ""), str(g("ts", "") or ""),
                             str(g("kind", "") or "")))
        except Exception:
            return set()          # unreadable -> every candidate classifies UNKNOWN
        return out

    def work_drain(self, timeout_ms: int = 1500, *, limit: int = 50,
                   since_out: Optional[Dict[str, str]] = None,
                   generation: int = 0) -> List[Any]:
        """T045 stage 2 (T039b): the lane-mode consume door -- runner and session door both
        cut onto THIS seam. Gated by BIFROST_CONSUME_LANE=work (unset = legacy wait(),
        byte-identical, strangler discipline). In lane mode, per fence-reconciled scope
        (docs/library/design/20260714_t045-stage-2-runner-consume-cutover-scop_b9c06c.md):

        (1) SIG FIRST (P3/R5): the sig lane drains before work every call -- fidelity-ladder
            traffic never queues behind work. Sig positions auto-advance on return (signals
            fold into the CURRENT turn; redelivering a stale nudge has negative value).
        (2) WORK PRIMARY (R1/R3): blocks the caller's budget on the work lane from the
            DURABLE lane cursor. Work positions are NOT auto-advanced -- the consumer
            advances via advance_to(cursor_key=lane_cursor_key()) AFTER processing
            (RB-26 commit-after-processing; crash before advance = redelivery, pin R3).
        (3) LEGACY STRAGGLER NET while dual-write is ON (R2): a packet whose lane write
            failed exists only on legacy. The shadow cursor seeds from the SHARED cursor
            (the pre-flip consumer's own progress -- continued, never written, pin R8) and
            auto-advances. Stragglers are a DEFECT SIGNAL: loud on stderr. Known dual-write-
            window bounds (retire with T047): a shadow-before-lane read-order race can
            double-deliver (at-least-once; RB-26 consumers are idempotent), and a straggler
            returned-then-crashed is at-most-once for that copy.

        `since_out` receives the WORK next-positions (the runner's batch-sweep pattern)."""
        if not self.consume_lane_enabled():
            return self.bus.wait(timeout_ms=timeout_ms, limit=limit, since_out=since_out)
        from core.comm import packet_spec
        cur = self.bus.read_lane_cursor()
        # ONBOARDING SEED (once per api instance; storm-cfdcb65f find): a VIRGIN lane
        # cursor -- newborn or migrant -- seeds at tails before the first read: history
        # (lane soak, legacy broadcasts) is never mail, matching seed_cursor_at_tail's
        # RB-25 F2 newborn discipline. Established consumers (non-virgin) skip in one
        # hgetall. Named residual (M8): pre-onboarding directed mail is skipped WITH the
        # history -- identical to the legacy newborn contract.
        if not getattr(self, "_lane_seeded", False):
            if all(v == "0" for v in cur.values()):
                self.bus.lane_cursor_flip_init()
                cur = self.bus.read_lane_cursor()
            self._lane_seeded = True
        lane_key = self.bus.lane_cursor_key()
        out: List[Any] = []
        seen: set = set()
        # (1) sig first -- 1ms peek (block=0 would wait forever; the L2/L5 lesson)
        snxt: Dict[str, str] = {}
        sig = self.bus.wait(timeout_ms=1, limit=limit,
                            since={"inbox": cur["sig_inbox"], "bc": cur["sig_bc"]},
                            since_out=snxt, streams=self._sig_streams())
        for m in sig:
            seen.add(self._dedup_key(m))
            try:
                m.meta["_lane_src"] = "sig"     # consumers must NOT advance work fields for these
            except Exception:
                pass
        out += sig
        sig_fields = {f: snxt[k] for f, k in (("sig_inbox", "inbox"), ("sig_bc", "bc"))
                      if snxt.get(k) and snxt[k] != cur[f]}
        if sig_fields:
            # generation rides through: once a fenced consumer stamps the hash, a gen-0
            # internal advance would be refused as stale and sig would replay forever
            self.bus.advance_cursor_fields(lane_key, sig_fields, generation=generation)
        # (2) work primary -- caller's blocking budget; NO auto-advance (pin R3)
        wnxt: Dict[str, str] = {}
        work = self.bus.wait(timeout_ms=timeout_ms, limit=limit,
                             since={"inbox": cur["inbox"], "bc": cur["bc"]},
                             since_out=wnxt, streams=self._lane_streams())
        for m in work:
            seen.add(self._dedup_key(m))
            try:
                m.meta["_lane_src"] = "work"    # the ONLY source whose ids advance inbox/bc
            except Exception:
                pass
        out += work
        if since_out is not None:
            since_out.update(wnxt)
        # (3) legacy straggler net -- dual-write window only
        if packet_spec.dual_write_enabled():
            sh_in, sh_bc = cur["shadow_inbox"], cur["shadow_bc"]
            seeded_now = False
            if sh_in == "0" and sh_bc == "0":
                # Belt for a failed/raced seed: continue the shared cursor's story
                # (READ-only: R8 stays intact). The normal path never gets here -- the
                # virgin-cursor seed below handles newborns AND migrants up front.
                shared = self.bus.cursor()
                sh_in = shared.get("inbox", "0")
                sh_bc = shared.get("bc", "0")
                seeded_now = sh_in != "0" or sh_bc != "0"
            shnxt: Dict[str, str] = {}
            legacy = self.bus.wait(timeout_ms=1, limit=limit,
                                   since={"inbox": sh_in, "bc": sh_bc}, since_out=shnxt)
            # R12 (post-ship soak find): only WORK-lane-eligible kinds can be stragglers.
            # A legacy message whose kind routes to trace/sig was never a lane-write
            # failure -- its absence from the work lane is the ROUTER working. Unmapped
            # kinds (lane_for None) stay netted: legacy-only by census gap = deliver.
            stragglers = [m for m in legacy
                          if self._dedup_key(m) not in seen
                          and packet_spec.lane_for(str(getattr(m, "kind", ""))) in ("work", None)]
            if stragglers:
                import sys
                # W166: classify before claiming. The old line said "lane write failed
                # upstream" for every straggler, and measurement put the true rate at 1 in
                # 192 while a single drain reported 10.
                _lane_shas = None

                def _lane_has(key):
                    nonlocal _lane_shas
                    if _lane_shas is None:
                        _lane_shas = self._work_lane_shas()
                    if not _lane_shas:
                        # Empty means the lane could not be read, NOT that the lane is
                        # empty -- claiming "absent" here would recreate the false alarm
                        # this slice exists to remove.
                        raise RuntimeError("work lane membership unreadable")
                    return key in _lane_shas

                counts = {"lane-write-failed": 0, "cursor-skew": 0, "unknown": 0}
                for m in stragglers:
                    counts[classify_straggler(self._dedup_key(m), _lane_has)] += 1
                summary = render_straggler_summary(counts)
                if summary:
                    print(f"[work-drain] {len(stragglers)} legacy-net packet(s) for "
                          f"{self.agent}: {summary}", file=sys.stderr)
                # W97 (T122 scope 3): name the sender + id per straggler -- the
                # investigation starts at the defect, not at a census. getattr-safe.
                for m in stragglers[:20]:
                    print(f"[work-drain]   from {getattr(m, 'frm', '?')} "
                          f"[{getattr(m, 'kind', '?')}] id={getattr(m, 'id', '?')}",
                          file=sys.stderr)
                if len(stragglers) > 20:
                    print(f"[work-drain]   (+{len(stragglers) - 20} more)", file=sys.stderr)
            for m in stragglers:
                try:
                    m.meta["_lane_src"] = "legacy"   # consumed via shadow; never advances work fields
                except Exception:
                    pass
            out += stragglers
            sh_fields = {f: shnxt[k] for f, k in (("shadow_inbox", "inbox"), ("shadow_bc", "bc"))
                         if shnxt.get(k) and shnxt[k] != cur[f]}
            if not sh_fields and seeded_now:
                # persist the one-time shared-cursor seed even on a quiet peek
                sh_fields = {"shadow_inbox": sh_in, "shadow_bc": sh_bc}
            if sh_fields:
                # C6-7 FIX (deepseek 2026-07-22): shadow advance was gated by the caller's
                # generation fence (same guarded Lua as work/sig). Two callers (runner +
                # session client) write to the lane cursor hash with DIFFERENT generations
                # (runner_lock.generation_of vs claim_consumer gen), and the higher-gen write
                # blocks the lower-gen shadow advance as STALE_GENERATION -- silently dropped.
                # The shadow cursor is a best-effort peek cursor, not a consumption contract:
                # plain HSET, no generation fence. Uses the Bus's _client directly (same
                # pattern as lane_flip_init which also writes the lane cursor hash raw).
                try:
                    self.bus._client.hset(lane_key, mapping=sh_fields)
                except Exception:
                    pass
        # T066 S4: receiver-side reply dedup over meta.reply_id. Delivery MARKS the id for
        # every reply; only a LEGACY-path copy of an already-seen id is DROPPED -- work-lane
        # copies always deliver, so RB-26 crash-redelivery (work cursor advances only after
        # processing) stays intact. The dual-write twin / straggler re-race is the one shape
        # this kills (the 2026-07-14 wake-loop class).
        deduped: List[Any] = []
        dropped = 0
        for m in out:
            if str(getattr(m, "kind", "")) == "reply":
                try:
                    mmeta = getattr(m, "meta", {}) or {}
                    rid = str(mmeta.get("reply_id") or "")
                    src = str(mmeta.get("_lane_src") or "")
                except Exception:
                    rid, src = "", ""
                if rid and self.bus.is_duplicate_reply(rid) and src == "legacy":
                    dropped += 1
                    continue
            deduped.append(m)
        if dropped:
            import sys
            print(f"[work-drain] {dropped} duplicate reply(ies) skipped for {self.agent} "
                  f"(reply_id dedup, T066)", file=sys.stderr)
        return deduped

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
