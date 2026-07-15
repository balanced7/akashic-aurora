"""
Bifrost Bus (Slice B0) -- one ephemeral message transport for local agents, on Redis Streams.

Semantic Relationship: Agent sends Message to Agent (or broadcasts) over the Bus

This consolidates the four old comm layers into one, and fixes their bugs:
  * **Correct port.** Connects via the canonical connector (the single-source-of-truth host/port),
    not the hardcoded 6379 that `fast_agent_comm` used (real Redis is on 16379).
  * **Real fan-out.** Each agent has its OWN inbox stream (`bifrost:inbox:<agent>`); broadcasts go to a
    shared `bifrost:broadcast` stream that every agent reads from its OWN cursor -- so a broadcast reaches
    ALL agents. (The old code used a single shared consumer group, which *load-balances*, so a "broadcast"
    reached exactly one agent -- the bug.)
  * **Ephemeral, not the durable record.** This is the live transport only (Redis Streams). The durable
    "what was said" record is a separate Ledger projection (slice B2) -- the bus and the audit ledger are
    deliberately NOT conflated (design delta F1).

When Redis is down there is NO live bus -- surfaced EXPLICITLY (`online` is False, `send` returns None),
never silently swallowed. Streams are bounded (maxlen) since this is ephemeral transport.

Read model: per-agent cursors (last-read stream id for inbox + broadcast) in a Redis hash, so each agent
catches up on exactly what it missed and never re-reads (offset semantics without consumer-group coupling).
"""
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.comm import packet_spec
from core.comm.blobs import get_blob_store

NS = "bifrost"
DEFAULT_MAXLEN = 10_000
BROADCAST_TO = "*"
PRESENCE_TTL = 90          # seconds an agent is considered "online" after its last activity
BELL_NS = f"{NS}:bell"     # Bifrost Mesh W1: pub/sub doorbell channel prefix


def bell_channel(to: str) -> str:
    """The pub/sub doorbell channel for a recipient ('*' = broadcast). A Dispatcher PSUBSCRIBEs
    `bifrost:bell:*` to wake in ~ms; the notice is payload-free and SAFE TO LOSE (the Stream +
    cursor remain the durable truth)."""
    return f"{BELL_NS}:{to}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loud(msg: str) -> None:
    """A packet-integrity refusal/drop must be VISIBLE, never silent (the whole point of T043).
    Best-effort stderr; never raises (the transport must survive a logging failure)."""
    try:
        print(msg, file=sys.stderr, flush=True)
    except Exception:
        pass


def _loads(s: Any) -> Any:
    if s is None or s == "":
        return None
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return s


def _connect():
    """The canonical Redis client (correct host/port, decode_responses). None if unreachable."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=3, decode_responses=True)
    except Exception:
        return None


@dataclass
class Part:
    """An A2A-style atomic content unit: a typed value that is either INLINE (small/text) or a
    `blob:<sha>` REFERENCE (media/large) the receiver fetches on demand (lossless-pointer rule)."""
    content_type: str               # text/plain | application/json | image/png | ...
    inline: Any = None              # the value, when carried inline
    ref: Optional[str] = None       # a blob ref, when stored out-of-band

    @property
    def is_ref(self) -> bool:
        return self.ref is not None

    def resolve(self, blobs=None) -> Any:
        """The Part's value: the inline value, or the fetched blob bytes (None if the blob is gone)."""
        if self.ref is not None:
            return (blobs or get_blob_store()).get(self.ref)
        return self.inline

    def to_dict(self) -> Dict[str, Any]:
        return {"content_type": self.content_type, "inline": self.inline, "ref": self.ref}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Part":
        return cls(content_type=d.get("content_type", "application/octet-stream"),
                   inline=d.get("inline"), ref=d.get("ref"))


def text_part(s: Any) -> Part:
    return Part("text/plain", inline=str(s))


def json_part(obj: Any) -> Part:
    return Part("application/json", inline=obj)


def media_part(data, content_type: str, *, blobs=None) -> Part:
    """Store bytes/str as a content-addressed blob and carry only the ref (media-by-reference)."""
    return Part(content_type, ref=(blobs or get_blob_store()).put(data))


def file_part(path, *, content_type: Optional[str] = None, blobs=None) -> Part:
    import mimetypes
    ct = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return Part(ct, ref=(blobs or get_blob_store()).put_path(path))


@dataclass
class Message:
    id: str                 # the stream entry id (also the read cursor / offset)
    frm: str
    to: str                 # an agent id, or "*" for a broadcast
    kind: str               # chat | request | response | handoff | note | ...
    content: Any
    ts: str
    meta: Dict[str, Any] = field(default_factory=dict)
    parts: List[Part] = field(default_factory=list)    # A2A parts (inline or blob refs)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "frm": self.frm, "to": self.to, "kind": self.kind,
                "content": self.content, "ts": self.ts, "meta": self.meta,
                "parts": [p.to_dict() for p in self.parts]}


class Bus:
    """An agent's handle on the Bifrost transport. One per agent identity."""

    def __init__(self, agent_id: str, client: Optional[Any] = None, *,
                 namespace: Optional[str] = None, maxlen: int = DEFAULT_MAXLEN, promote: Optional[bool] = None):
        self.agent_id = str(agent_id or "unknown")
        self.ns = namespace or os.environ.get("BIFROST_NAMESPACE", NS)
        self.maxlen = maxlen
        self._client = client if client is not None else _connect()
        # B2: durably project salient kinds by default -- but NOT under pytest, so transport tests
        # never leak into the canonical firehose. Pass promote=True/False to force the behavior.
        self._promote = (os.getenv("PYTEST_CURRENT_TEST") is None) if promote is None else bool(promote)
        self._card: Dict[str, Any] = {}        # the agent's A2A-style card (runtime_class/wake_mode/door/caps)
        self._last_degraded_warn = 0.0         # T043: rate-limit the integrity-disabled LOUD warning
        # T043: consumer-side fragment reassembly, DURABLY backed (survives restart -> the LOUD
        # timeout still fires; see packet_spec.Reassembler). Rehydrate any in-flight partial now.
        self._reasm = packet_spec.Reassembler(persist=self._reasm_persist)
        self._rehydrate_reasm()

    # ------------------------------------------------------------------ identity / health
    @property
    def online(self) -> bool:
        """True iff the live bus (Redis) is reachable. When False, sends are no-ops returning None.
        NOTE: a construction-time fact -- the client object outlives a dead server. For
        'is Redis there NOW' use probe() (RB-30: wiring a loop guard to `online` was the
        invisible-spin bug's shape -- it can never flip mid-run)."""
        return self._client is not None

    def probe(self) -> bool:
        """LIVE reachability: one PING, False on any failure. The RB-30 BusLossGuard's
        ground truth -- cheap enough for once per runner loop beat."""
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def status(self) -> Dict[str, Any]:
        return {"online": self.online, "agent_id": self.agent_id, "pending": self.pending()}

    # ------------------------------------------------------------------ presence (B3)
    def register(self, ttl: int = PRESENCE_TTL, *, card: Optional[Dict[str, Any]] = None) -> bool:
        """Heartbeat: mark this agent online for `ttl` seconds, carrying an optional A2A-style Agent
        Card ({runtime_class, wake_mode, door, caps, ...}). The card is remembered so every later
        heartbeat (incl. the auto-touch on send/inbox) refreshes WITH it. Returns True if recorded."""
        if not self.online:
            return False
        if card is not None:
            self._card = dict(card)
        try:
            value = json.dumps({"ts": _now(), **self._card}, default=str)
            self._client.set(f"{self.ns}:presence:{self.agent_id}", value, ex=ttl)
            return True
        except Exception:
            return False

    def _touch(self) -> None:
        """Refresh presence as a side effect of using the bus (sending/reading = being active)."""
        self.register()

    def presence(self) -> List[Dict[str, Any]]:
        """The agents currently online (presence keys not yet expired), with their Agent Card fields
        (runtime_class/wake_mode/door/caps) if registered. Backward-compatible with bare-timestamp
        presence records. Sorted by id."""
        if not self.online:
            return []
        try:
            out: List[Dict[str, Any]] = []
            for k in (self._client.keys(f"{self.ns}:presence:*") or []):
                agent = str(k).rsplit(":", 1)[-1]
                raw = self._client.get(k)
                card = _loads(raw)
                if isinstance(card, dict):
                    rec = {"agent": agent, "last_seen": card.get("ts", "")}
                    rec.update({kk: vv for kk, vv in card.items() if kk != "ts"})
                else:
                    rec = {"agent": agent, "last_seen": raw or ""}
                out.append(rec)
            return sorted(out, key=lambda x: x["agent"])
        except Exception:
            return []

    # ------------------------------------------------------------------ keys
    def _inbox_key(self, agent: str) -> str:
        return f"{self.ns}:inbox:{agent}"

    @property
    def _bc_key(self) -> str:
        return f"{self.ns}:broadcast"

    def _cursor_key(self) -> str:
        return f"{self.ns}:cursor:{self.agent_id}"

    # ------------------------------------------------------------------ send
    def send(self, to: str, kind: str, content: Any = None, *, parts: Optional[List[Part]] = None,
             meta: Optional[Dict[str, Any]] = None, allow_frag: bool = False) -> Optional[str]:
        """Direct message to one agent's inbox (optionally with `parts` -- inline or media-by-ref).
        Returns the message id, or None if the bus is offline OR the packet exceeds the MTU and
        `allow_frag` is False (a REFUSE-LOUD, never a silent truncation -- T043). Pass
        allow_frag=True to fragment an oversize payload, or carry large media as a blob-ref Part."""
        return self._emit(self._inbox_key(str(to)), to=str(to), kind=kind, content=content,
                          parts=parts, meta=meta, allow_frag=allow_frag)

    def broadcast(self, kind: str, content: Any = None, *, parts: Optional[List[Part]] = None,
                  meta: Optional[Dict[str, Any]] = None, allow_frag: bool = False) -> Optional[str]:
        """Fan-out to every agent (each reads it from its own cursor). Returns the message id or None
        (None also on an oversize refuse-loud when allow_frag is False -- T043)."""
        return self._emit(self._bc_key, to=BROADCAST_TO, kind=kind, content=content,
                          parts=parts, meta=meta, allow_frag=allow_frag)

    def send_reply(self, to: str, content: Any = None, *,
                   meta: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """T066 S1-S3: the reply-path send -- lane-FIRST, legacy fallback. Replies are the
        one kind whose consumers are ALREADY lane-mode (T045 stage 2), so the advisory
        dual-write of `_emit` is not enough: a silently failed lane mirror strands the reply
        on legacy until the straggler net's next cycle (the 2026-07-14 wake-loop class).
        Here the work-lane write happens first and is VERIFIED (one retry on a transient
        blip; a second failure goes LOUD and falls back to legacy-only). The legacy copy is
        always attempted for pre-lane consumers (P6). Every reply is stamped with
        meta.reply_id -- the receiver-side dedup key (work_drain skips cross-path twins).
        Oversize replies delegate to send(allow_frag=True): fragments ride the existing
        legacy-first machinery (documented residual). Lanes off -> plain send()."""
        if not self.online:
            return None
        from uuid import uuid4
        meta = dict(meta or {})
        meta.setdefault("reply_id", uuid4().hex)
        if not packet_spec.dual_write_enabled():
            return self.send(to, "reply", content, meta=meta)
        env = {"frm": self.agent_id, "to": str(to), "kind": "reply",
               "content": json.dumps(content, default=str), "ts": _now(),
               "meta": json.dumps(meta, default=str), "parts": "[]"}
        length, sha = packet_spec.compute_len_sha(env)
        if not packet_spec.within_mtu(length):
            return self.send(to, "reply", content, meta=meta, allow_frag=True)
        packet_spec.stamp(env, length=length, sha=sha)
        lane_key = packet_spec.lane_stream_key(self.ns, "work", to=str(to))
        lane_mid: Optional[str] = None
        for attempt in (1, 2):                          # S2: exactly one retry
            try:
                lane_mid = str(self._client.xadd(lane_key, env,
                                                 maxlen=packet_spec.lane_maxlen("work"),
                                                 approximate=True))
                break
            except Exception as e:
                if attempt == 2:
                    _loud(f"[send-reply] lane write FAILED twice for {lane_key} ({e}) -- "
                          f"falling back to legacy-only; lane consumers will get this reply "
                          f"via the straggler net, delayed")
        legacy_mid: Optional[str] = None
        try:
            legacy_mid = str(self._client.xadd(self._inbox_key(str(to)), env,
                                               maxlen=self.maxlen, approximate=True))
        except Exception:
            pass
        if lane_mid is None and legacy_mid is None:
            return None                                  # both writes failed: the send failed
        self._touch()
        self._ring_bell(str(to), lane_mid or legacy_mid, "reply")
        return lane_mid or legacy_mid

    def is_duplicate_reply(self, reply_id: str, *, ttl_s: Optional[int] = None) -> bool:
        """T066 S4: receiver-side reply dedup. First sight MARKS the id (SET NX + TTL) and
        reports False; a repeat within the TTL reports True. Fail-open: offline or a Redis
        error reports False -- deliver rather than drop (losing a reply is the worse bug).
        TTL default 1200s (~2x the runner reply window); dial: BIFROST_REPLY_DEDUP_TTL_S."""
        if not reply_id or not self.online:
            return False
        ttl = ttl_s if ttl_s is not None else int(os.environ.get("BIFROST_REPLY_DEDUP_TTL_S", "1200") or 1200)
        try:
            fresh = self._client.set(f"{self.ns}:reply_seen:{reply_id}", "1", nx=True, ex=ttl)
            return not bool(fresh)
        except Exception:
            return False

    def _emit(self, stream: str, *, to: str, kind: str, content: Any,
              parts: Optional[List[Part]] = None, meta=None, allow_frag: bool = False) -> Optional[str]:
        if not self.online:
            return None
        part_dicts = [(p.to_dict() if isinstance(p, Part) else p) for p in (parts or [])]
        env = {"frm": self.agent_id, "to": to, "kind": str(kind),
               "content": json.dumps(content, default=str), "ts": _now(),
               "meta": json.dumps(meta or {}, default=str),
               "parts": json.dumps(part_dicts, default=str)}
        # T043 SEND DOOR: enforce the MTU (refuse loud, or fragment on opt-in) then stamp v/len/sha.
        # The size bounded is the canonical len -- the same honest number the consume door verifies.
        length, sha = packet_spec.compute_len_sha(env)
        if not packet_spec.within_mtu(length):
            if not allow_frag:
                _loud(packet_spec.mtu_refusal_text(length))     # NEVER truncate (pin 1)
                return None
            return self._emit_fragments(stream, env, to=to, kind=str(kind))
        packet_spec.stamp(env, length=length, sha=sha)         # adds v, len, sha (pin 2/3/4); reuse the hash
        try:
            mid = str(self._client.xadd(stream, env, maxlen=self.maxlen, approximate=True))
            self._touch()
            self._lane_write(env, to=to, kind=str(kind))   # T039a P0 dual-write (best-effort)
            self._ring_bell(to, mid, str(kind))    # W1 doorbell: low-latency notify (lose-safe)
            try:                                   # B2: durably project salient kinds (best-effort)
                from core.comm.promoter import is_salient, promote
                if self._promote and is_salient(kind):
                    promote(self.agent_id, to, kind, content, mid, env["ts"])
            except Exception:
                pass
            return mid
        except Exception:
            return None

    def _emit_fragments(self, stream: str, env: Dict[str, Any], *, to: str, kind: str) -> Optional[str]:
        """Split an oversize payload into MTU-safe fragment packets and xadd each (T043 pin 5).
        Every fragment is len+sha-stamped and carries frag={seq,of,whole_id,whole_len,whole_sha}
        so the consumer can reassemble and detect a missing piece (pin 6). Rings the bell ONCE
        for the whole; returns the id of the first fragment (or None on any write failure)."""
        first_mid: Optional[str] = None
        for fenv in packet_spec.fragment(env):
            try:
                mid = str(self._client.xadd(stream, fenv, maxlen=self.maxlen, approximate=True))
            except Exception:
                return None
            self._lane_write(fenv, to=to, kind=kind)       # T039a: fragments mirror too
            if first_mid is None:
                first_mid = mid
        if first_mid is not None:
            self._touch()
            self._ring_bell(to, first_mid, str(kind))
        return first_mid

    _unmapped_loud_seen: set = set()   # once-per-kind-per-process throttle (class-level)

    def _lane_write(self, env: Dict[str, Any], *, to: str, kind: str) -> None:
        """T039a P0 dual-write (docs/t039-lanes-latches-design-2026-07.md): mirror the packet
        onto its lane stream. NOT load-bearing until the T039b cutover -- consumers still read
        legacy, and lane cursors initialize tail-at-flip (A4), so this phase is a live soak of
        the lane write path, not a data migration. Best-effort by design: a lane failure must
        never block or fail the legacy delivery. Kill-switch: BIFROST_LANES_DUAL_WRITE=0."""
        try:
            if not packet_spec.dual_write_enabled():
                return
            lane = packet_spec.lane_for(kind)
            if lane is None:
                # Census miss: legacy-only + LOUD once per kind. Full refusal is the spec's
                # end state and activates at cutover, once the soak proves the table complete.
                if kind not in Bus._unmapped_loud_seen:
                    Bus._unmapped_loud_seen.add(kind)
                    _loud(f"[lane-router] kind '{kind}' has NO lane mapping -- riding legacy "
                          f"only. Add it to packet_spec.KIND_LANE before the T039b cutover.")
                return
            target = None if to == BROADCAST_TO else to
            key = packet_spec.lane_stream_key(self.ns, lane, to=target)
            fields = env
            if lane == "trace":
                # R5 + amend E: trace copy is unstamped except every Nth (global spot tick).
                fields = dict(env)
                tick = 0
                try:
                    tick = int(self._client.incr(f"{self.ns}:trace:spotcount"))
                except Exception:
                    pass
                if packet_spec.lane_wants_integrity("trace", tick=tick):
                    fields["spot_tick"] = str(tick)
                else:
                    fields.pop("len", None)
                    fields.pop("sha", None)
            self._client.xadd(key, fields, maxlen=packet_spec.lane_maxlen(lane),
                              approximate=True)
        except Exception:
            pass   # advisory in P0; the legacy write above is the delivery

    def _ring_bell(self, to: str, mid: str, kind: str) -> None:
        """Doorbell (Bifrost Mesh W1): a payload-free pub/sub notice so a Dispatcher wakes in ~ms.
        At-most-once and SAFE TO LOSE -- the Stream + cursor are the durable truth; a dropped bell is
        caught by the next inbox peek / safety re-scan. Best-effort: never blocks or fails a send."""
        try:
            notice = json.dumps({"mid": mid, "frm": self.agent_id, "to": to, "kind": kind})
            self._client.publish(bell_channel(to), notice)
        except Exception:
            pass

    # ------------------------------------------------------------------ receive
    def inbox(self, limit: int = 50, *, advance: bool = True, generation: int = 0,
              commit_status_out: Optional[Dict[str, str]] = None) -> List[Message]:
        """New messages for this agent (direct + broadcast), oldest-first, from the per-agent cursor.

        `advance=True` moves the cursor past what's returned (so the next call won't re-read). An agent's
        own broadcasts are not delivered back to it. Returns [] (never raises) when offline.

        RB-21: every shared-cursor advance is FENCED -- it commits through the guarded Lua
        carrying `generation` (a consumer-seat tenure from runner_lock.claim_consumer;
        0 keeps working only while the agent has never been fenced). Pass
        `commit_status_out={}` to receive {"status": OK|OK_NOOP|STALE_GENERATION|
        BACKWARDS|ERROR}; a door seeing STALE_GENERATION must treat its read as a PEEK
        (a successor owns the cursor now; redelivery is the successor's, at-least-once)."""
        return self._drain(block=None, limit=limit, advance=advance,
                           generation=generation, commit_status_out=commit_status_out)

    def wait(self, timeout_ms: int = 0, *, limit: int = 50, advance: bool = False,
             since: Optional[Dict[str, str]] = None,
             since_out: Optional[Dict[str, str]] = None,
             streams: Optional[Dict[str, str]] = None) -> List[Message]:
        """BLOCK until a new message arrives (or `timeout_ms` elapses; 0 = forever), then return it.

        The event-driven wake primitive: an idle agent (or a backgrounded watcher) blocks here at ~0
        cost and returns the instant a message lands. Defaults to advance=False -- it *detects* without
        consuming, so the agent can then `inbox()` the message normally. Returns [] on timeout/offline.

        `since={"inbox": id, "bc": id}` reads from a CALLER-OWNED position instead of the shared
        cursor, and the shared cursor is NEVER written (advance is ignored) -- the local-cursor mode a
        wake watcher uses so skip-kinds don't busy-spin it while the real consumer still gets every
        message (P0 / T017; the T016 Exhibit A fix). Pass `since_out={}` to receive the caller's next
        safe position under the same T014 rules the shared cursor uses (this is how a filtered own-
        broadcast -- read but never returned -- still moves the local cursor: filtered != truncated)."""
        # T045: `streams` overrides WHICH keys the logical inbox/bc pair reads (e.g. the work
        # lane) -- caller-owned cursors only (no shared cursor exists for lane keys yet), so
        # advance is forced off; every T043 consume-door protection still applies.
        return self._drain(block=int(timeout_ms), limit=limit,
                           advance=(advance and since is None and streams is None),
                           since=since, since_out=since_out, streams=streams)

    def _blocking_client(self, block_ms):
        """A client whose socket timeout EXCEEDS the block: the fail-fast client's short socket_timeout
        (~2-3s) would abort a long blocking xread prematurely. Built via the canonical connector (so we
        honor redis-only-via-connector) by passing a long `timeout_seconds` (which becomes the socket
        timeout). block_ms of 0 (block 'forever') -> a day. Falls back to the shared client on error."""
        try:
            from core.foundation.redis_connection import (
                connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
            socket_timeout = (block_ms / 1000.0 + 5) if block_ms else 86400.0
            return connect_to_redis_with_fail_fast(
                host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                timeout_seconds=socket_timeout, decode_responses=True)
        except Exception:
            return None

    def _drain(self, *, block, limit: int, advance: bool,
               since: Optional[Dict[str, str]] = None,
               since_out: Optional[Dict[str, str]] = None,
               generation: int = 0,
               commit_status_out: Optional[Dict[str, str]] = None,
               streams: Optional[Dict[str, str]] = None) -> List[Message]:
        if not self.online:
            return []
        self._touch()
        cur = ({"inbox": str(since.get("inbox", "0")), "bc": str(since.get("bc", "0"))}
               if since is not None else self._read_cursor())
        # T045: the logical inbox/bc pair reads legacy keys by default; `streams` retargets it
        # (work lane) without touching any downstream logic -- cursor rules, integrity, frag
        # reassembly and own-broadcast filtering are key-agnostic.
        keys = streams or {"inbox": self._inbox_key(self.agent_id), "bc": self._bc_key}
        client, temp = self._client, None
        if block is not None:                      # a blocking wait() needs a long-socket-timeout client
            temp = self._blocking_client(block)
            if temp is not None:
                client = temp
        try:
            res = client.xread(
                {keys["inbox"]: cur["inbox"], keys["bc"]: cur["bc"]},
                count=max(1, limit), block=block)
        except Exception:
            res = None
        finally:
            if temp is not None:
                try:
                    temp.close()
                except Exception:
                    pass
        now = time.time()
        if not res:                                # idle read: still time out any stalled partial
            for wid, missing in self._reasm.sweep_expired(now):   # (pin 6: a quiet stream must
                self._fragment_timeout(wid, missing)              # still fire fragment_timeout)
            return []
        if not packet_spec.integrity_enabled():    # kill-switch off: delivering UNVERIFIED -> LOUD (pin 4)
            self._integrity_degraded_warn()
        new_inbox, new_bc = cur["inbox"], cur["bc"]
        out: List[Message] = []
        # Track which stream each message came from so we can fix the cursor AFTER truncation.
        # (The old code used the last-read id -- even for entries skipped by out[:limit] -- causing
        # a cursor-skip when the stream had more entries than limit. T014 Defect 1.)
        out_streams: List[str] = []                # "inbox" | "bc" (parallel to out)
        for stream, entries in res or []:
            is_bc = (stream == keys["bc"])
            for sid, fields in entries:
                if is_bc:
                    new_bc = sid
                else:
                    new_inbox = sid
                # T043 CONSUME DOOR. A dropped/incomplete packet is FILTERED (not added to out)
                # while its sid still advances the cursor -- 'filtered != truncated' (T014), the
                # same discipline that skips an own-broadcast: a corrupt packet can never wedge
                # the stream by being re-read forever.
                ok, why = packet_spec.verify_integrity(fields)
                if not ok:
                    self._integrity_drop(sid, fields, why)     # DROP + loud event (pin 2/3)
                    continue
                if packet_spec.parse_frag(fields) is not None:
                    whole, prob = self._reasm.add(fields, now=now)   # buffer/reassemble (pin 5)
                    if prob is not None:
                        self._frag_problem(sid, prob)          # loud orphan/stale/whole-corrupt
                        continue
                    if whole is None:
                        continue                               # buffered; set incomplete
                    m = self._to_msg(sid, whole)               # deliver the reassembled whole
                else:
                    m = self._to_msg(sid, fields)
                if is_bc and m.frm == self.agent_id:
                    continue                       # don't deliver an agent its own broadcast
                out.append(m)
                out_streams.append("bc" if is_bc else "inbox")
        for wid, missing in self._reasm.sweep_expired(now):    # pin 6/7: LOUD timeout, seq named
            self._fragment_timeout(wid, missing)
        # Sort messages (and their stream-tags) by id so newest-last
        pairs = sorted(zip(out, out_streams), key=lambda p: p[0].id)
        out = [p[0] for p in pairs]
        out_streams = [p[1] for p in pairs]
        returned = out[:limit]
        # The safe next-position, one rule for BOTH cursor kinds (shared and caller-owned):
        # - No truncation: everything deliverable was returned, so the last READ id is provably
        #   safe -- and it correctly skips FILTERED entries (own broadcasts), which would
        #   otherwise be re-scanned on every drain forever (claude review of T014:
        #   filtered != truncated; the fix must not conflate them).
        # - Truncation: advance only to the LAST message ACTUALLY RETURNED from each stream
        #   (not the last read -- the T014 cursor-skip gap). The global id-sort preserves
        #   per-stream order, so the returned set holds a prefix of each stream; everything
        #   unreturned stays ahead of its cursor.
        if len(out) <= limit:
            next_inbox, next_bc = new_inbox, new_bc
        else:
            next_inbox, next_bc = cur["inbox"], cur["bc"]
            for m, stream_tag in zip(returned, out_streams[:limit]):
                if stream_tag == "inbox":
                    next_inbox = m.id
                else:
                    next_bc = m.id
        if since_out is not None:      # hand the caller its next safe position -- works for
            # the caller-owned mode (P0) AND for advance=False shared-cursor reads (RB-26:
            # the runner advances per-message, then sweeps to THIS position after the batch
            # so filtered own-broadcasts don't busy-rescan; filtered != truncated, T014).
            since_out["inbox"], since_out["bc"] = next_inbox, next_bc
        if since is None and advance and (next_inbox != cur["inbox"] or next_bc != cur["bc"]):
            # RB-21: the raw unguarded write is RETIRED -- every shared-cursor commit goes
            # through the L1b guarded Lua (refuses STALE_GENERATION + BACKWARDS), so a
            # fenced-out twin can neither eat mail silently nor drag the cursor backwards.
            status = self.advance_to(
                inbox=(next_inbox if next_inbox != cur["inbox"] else None),
                bc=(next_bc if next_bc != cur["bc"] else None),
                generation=generation)
            if commit_status_out is not None:
                commit_status_out["status"] = status
        return returned

    def seed_cursor_at_tail(self) -> bool:
        """RB-25 F2: onboard a NEW agent by moving its shared cursor to the live tail, so
        only mail arriving AFTER onboarding wakes it -- never the stale broadcast backlog.
        A virgin cursor ("0"/"0") drains the whole broadcast history on first read; the
        newborn gauntlet caught a fresh agent acting on a months-old directive as current.
        Same discipline the wake watcher already uses (tail(), not the "$" sentinel).
        ONLY seeds a virgin cursor -- a returning agent with real read progress is never
        rewound (idempotent, safe to call at every onboarding). Returns True if it seeded.
        Uses generation 0: a never-read agent has never been fenced, so the guarded commit
        accepts it; a fenced agent already has progress and is skipped by the virgin check."""
        if not self.online:
            return False
        cur = self._read_cursor()
        if cur.get("inbox", "0") != "0" or cur.get("bc", "0") != "0":
            return False                              # not virgin -> real progress, never rewind
        t = self.tail()
        if t.get("inbox", "0") == "0" and t.get("bc", "0") == "0":
            return False                              # nothing to skip -- leave virgin
        self.advance_to(inbox=t.get("inbox"), bc=t.get("bc"), generation=0)
        return True

    def pending(self) -> int:
        """How many unread messages are waiting (direct + broadcast), without advancing the cursor."""
        msgs = self.inbox(limit=1000, advance=False)
        return len(msgs)

    # ------------------------------------------------------------------ cursor
    def tail(self) -> Dict[str, str]:
        """The CONCRETE last-entry id of this agent's inbox + the broadcast stream ("0" when
        empty/unreadable). The safe 'start from NOW' frontier for a local since-cursor: unlike
        the "$" sentinel (which skips anything landing between two blocking reads), a
        materialized id makes every later arrival detectable (P0 review fold-in)."""
        out: Dict[str, str] = {}
        for stream, key in (("inbox", self._inbox_key(self.agent_id)), ("bc", self._bc_key)):
            try:
                last = self._client.xrevrange(key, count=1)
                out[stream] = str(last[0][0]) if last else "0"
            except Exception:
                out[stream] = "0"
        return out

    def cursor(self) -> Dict[str, str]:
        """A read-only snapshot of this agent's shared read-cursor ({"inbox": id, "bc": id}).
        Does not create or touch the key -- the seed for a watcher's local `since` position."""
        return self._read_cursor()

    def _read_cursor(self) -> Dict[str, str]:
        try:
            h = self._client.hgetall(self._cursor_key()) or {}
        except Exception:
            h = {}
        return {"inbox": h.get("inbox", "0"), "bc": h.get("bc", "0")}

    # (RB-21: _write_cursor -- the raw unguarded HSET -- is GONE. The guarded Lua below is
    # the ONLY cursor writer; its absence is pinned in tests/test_rb21_consumer_seat.py P5.)

    # RB-26 + L1b (T030): the GUARDED cursor commit -- one atomic Lua script, validated
    # AT THE RESOURCE (Kleppmann): refuse a stale fencing generation, refuse a backwards
    # id. Per-field so the consumer commits per message ('inbox' or 'bc') and sweeps the
    # batch tail. Ids compare as (ms, seq) stream ids with plain-int fallback.
    _ADVANCE_LUA = """
        local cur = KEYS[1]
        local gen = tonumber(ARGV[1])
        local field = ARGV[2]
        local newid = ARGV[3]
        local stored = tonumber(redis.call('HGET', cur, 'gen') or '0')
        if gen < stored then return 'STALE_GENERATION' end
        local function parse(id)
            local a, b = string.match(id, '^(%d+)%-(%d+)$')
            if a then return tonumber(a), tonumber(b) end
            return tonumber(id) or 0, 0
        end
        local curid = redis.call('HGET', cur, field) or '0'
        local nm, nsq = parse(newid)
        local cm, csq = parse(curid)
        if nm < cm or (nm == cm and nsq < csq) then return 'BACKWARDS' end
        if nm == cm and nsq == csq then
            redis.call('HSET', cur, 'gen', gen)
            return 'OK_NOOP'
        end
        redis.call('HSET', cur, field, newid, 'gen', gen)
        return 'OK'
    """

    def advance_to(self, *, inbox: Optional[str] = None, bc: Optional[str] = None,
                   generation: int = 0, cursor_key: Optional[str] = None) -> str:
        """Commit the shared read-cursor PAST handled work (RB-26: commit-after-processing;
        the at-least-once half of the idempotent-consumer pattern). Guarded by the fencing
        `generation` (L1b): a fenced-out predecessor gets 'STALE_GENERATION' and MUST stand
        down -- the successor owns the cursor now. Returns the strictest status seen:
        'STALE_GENERATION' > 'BACKWARDS' > 'ERROR' > 'OK'/'OK_NOOP'. 'OFFLINE' when no bus.
        A crash before this call leaves the message unconsumed -- redelivery, not loss.

        `cursor_key` (T045 stage 2, fence Q1 refinement) overrides WHICH cursor hash the
        guarded Lua writes -- default None = the shared legacy cursor (zero change for
        existing callers); lane-mode consumers pass lane_cursor_key() so a lane advance can
        never touch the shared cursor (pin R8). Same Lua either way: stale-generation and
        backwards ids are refused at the resource on ANY cursor hash."""
        if not self.online:
            return "OFFLINE"
        worst = "OK_NOOP"
        rank = {"OK_NOOP": 0, "OK": 1, "ERROR": 2, "BACKWARDS": 3, "STALE_GENERATION": 4}
        key = cursor_key or self._cursor_key()
        for field, val in (("inbox", inbox), ("bc", bc)):
            if val is None:
                continue
            try:
                res = str(self._client.eval(self._ADVANCE_LUA, 1, key,
                                            int(generation), field, str(val)))
            except Exception:
                res = "ERROR"
            if rank.get(res, 1) > rank.get(worst, 0):
                worst = res
        return worst

    def advance_cursor_fields(self, cursor_key: str, fields: Dict[str, str],
                              generation: int = 0) -> str:
        """Per-field guarded advance on an arbitrary cursor hash -- the sig/shadow sibling
        of advance_to(cursor_key=): same Lua (stale generation + backwards refused at the
        resource), arbitrary field names (sig_inbox/sig_bc/shadow_inbox/shadow_bc). WORK
        positions go through advance_to so the pin-R surface stays one door."""
        if not self.online:
            return "OFFLINE"
        worst = "OK_NOOP"
        rank = {"OK_NOOP": 0, "OK": 1, "ERROR": 2, "BACKWARDS": 3, "STALE_GENERATION": 4}
        for field, val in (fields or {}).items():
            if val is None:
                continue
            try:
                res = str(self._client.eval(self._ADVANCE_LUA, 1, cursor_key,
                                            int(generation), str(field), str(val)))
            except Exception:
                res = "ERROR"
            if rank.get(res, 1) > rank.get(worst, 0):
                worst = res
        return worst

    # ------------------------------------------------ T045 stage 2: LANE consumer cursor
    def lane_cursor_key(self, agent: Optional[str] = None) -> str:
        """'{ns}:cursor:lane:{agent}' -- the lane consumer's DURABLE cursor hash (fence Q1,
        deepseek proposal adopted 2026-07-14). Fields mirror the shared cursor: inbox/bc =
        WORK-lane positions (the at-least-once surface, advanced via advance_to(cursor_key=)
        after processing); sig_inbox/sig_bc = sig-lane positions (P3 interleave, consumed on
        return); shadow_inbox/shadow_bc = LEGACY positions for the dual-write straggler peek
        (vestigial once T047 retires the legacy stream)."""
        return f"{self.ns}:cursor:lane:{agent or self.agent_id}"

    _LANE_CURSOR_FIELDS = ("inbox", "bc", "sig_inbox", "sig_bc", "shadow_inbox", "shadow_bc")

    def read_lane_cursor(self) -> Dict[str, str]:
        """All lane-cursor fields with '0' defaults (virgin = drain-from-start semantics --
        a truly-new post-strangler agent's lane holds only real mail, pin R7; MIGRATING
        agents run lane_cursor_flip_init() at the flip instead)."""
        try:
            h = self._client.hgetall(self.lane_cursor_key()) or {}
        except Exception:
            h = {}
        return {f: str(h.get(f, "0")) for f in self._LANE_CURSOR_FIELDS}

    def _lane_keys(self, lane: str) -> Dict[str, str]:
        """Logical inbox/bc pair -> this agent's stream keys on `lane`."""
        from core.comm import packet_spec
        return {"inbox": packet_spec.lane_stream_key(self.ns, lane, to=self.agent_id),
                "bc": packet_spec.lane_stream_key(self.ns, lane)}

    def lane_cursor_flip_init(self) -> bool:
        """A4 tail-at-flip as an explicit RITUAL (seed_cursor_at_tail's lane twin) -- run
        ONCE when a MIGRATING agent (dual-write soak in its lane streams) flips its consumer
        to lane mode. Virgin-only + idempotent: an existing lane cursor is real progress and
        is never rewound. WORK and SIG seed at their CONCRETE lane tails (dual-write history
        is soak, never mail); the legacy SHADOW seeds at the agent's SHARED cursor -- the
        pre-flip consumer's own progress -- so the straggler peek CONTINUES that story
        without ever writing it (pin R8). A truly-new post-strangler agent skips the ritual
        entirely: virgin reads from '0' and its lane holds only real mail (pin R7 -- lazy
        tail-seeding here would eat pre-arm mail, which is why the flip is an explicit act).
        Returns True only when it seeded."""
        if not self.online:
            return False
        cur = self.read_lane_cursor()
        if any(v != "0" for v in cur.values()):
            return False                          # not virgin -> real progress, never rewind
        fields: Dict[str, str] = {}
        for lane, (fi, fb) in (("work", ("inbox", "bc")), ("sig", ("sig_inbox", "sig_bc"))):
            keys = self._lane_keys(lane)
            for logical, field in (("inbox", fi), ("bc", fb)):
                try:
                    last = self._client.xrevrange(keys[logical], count=1)
                    fields[field] = str(last[0][0]) if last else "0"
                except Exception:
                    fields[field] = "0"
        shared = self._read_cursor()
        if shared.get("inbox", "0") != "0" or shared.get("bc", "0") != "0":
            # MIGRANT: the shadow CONTINUES the pre-flip consumer's own progress --
            # unconsumed legacy backlog rides the straggler net (no loss at the flip).
            fields["shadow_inbox"] = shared.get("inbox", "0")
            fields["shadow_bc"] = shared.get("bc", "0")
        else:
            # NEWBORN (cfdcb65f storm find): BROADCAST history is room-noise -- bc
            # positions seed at tails (RB-25 F2 discipline; 44 replays caught live).
            # DIRECTED positions stay "0": addressed mail is queued work FOR YOU and
            # delivers even pre-onboarding (RB-26 directed-mail sanctity; sender-side
            # L4 expectations bound the wait). Deliberate improvement over the legacy
            # newborn seed, which skips the directed inbox too.
            fields["inbox"] = "0"
            fields["sig_inbox"] = "0"
            fields["shadow_inbox"] = "0"
            t = self.tail()
            fields["shadow_bc"] = t.get("bc", "0")
        if all(v == "0" for v in fields.values()):
            return False                          # nothing to skip -- stay virgin
        self.advance_cursor_fields(self.lane_cursor_key(), fields)
        return True

    def lane_flip_if_migrating(self) -> bool:
        """The decidable flip heuristic for CALLERS entering lane mode: a MIGRATING agent
        (virgin lane cursor + real progress on the SHARED cursor) runs the A4 ritual once;
        a truly-new agent (both virgin) skips it and reads the lane from '0' (pin R7).
        The flip gap is covered by design: unconsumed legacy backlog behind the shared
        cursor at flip time is delivered by work_drain's straggler net (shadow seeds AT the
        shared cursor), so tail-seeding the work lane loses nothing."""
        if not self.online:
            return False
        if any(v != "0" for v in self.read_lane_cursor().values()):
            return False                          # already flipped -- real progress
        shared = self._read_cursor()
        if shared.get("inbox", "0") == "0" and shared.get("bc", "0") == "0":
            return False                          # truly new -- no ritual (pin R7 semantics)
        return self.lane_cursor_flip_init()

    def _to_msg(self, sid: str, fields: Dict[str, Any]) -> Message:
        parts = [Part.from_dict(d) for d in (_loads(fields.get("parts")) or []) if isinstance(d, dict)]
        return Message(id=str(sid), frm=fields.get("frm", ""), to=fields.get("to", ""),
                       kind=fields.get("kind", ""), content=_loads(fields.get("content")),
                       ts=fields.get("ts", ""), meta=_loads(fields.get("meta")) or {}, parts=parts)

    # ------------------------------------------------ T043 consume-door loud events
    def _integrity_drop(self, sid: str, fields: Dict[str, Any], why: str) -> None:
        """A packet failed the consume-door len/sha check: DROP it (never deliver) and record a
        LOUD durable event + stderr line. The cursor still advances past it. RB-29 EXTENSION
        (pin 9): because a corrupt reply is dropped HERE, and expectations.sweep reads replies
        THROUGH this same consume door (Bus.wait -> _drain), a corrupt reply is invisible to the
        sweep and clears no armed expectation -- integrity failure never counts as an answer."""
        try:
            from core.events.event_log import capture_event
            capture_event("packet_integrity_drop",
                          f"dropped corrupt packet from {fields.get('frm', '?')} "
                          f"kind={fields.get('kind', '?')}: {why}",
                          agent_id=self.agent_id, refs=[str(sid)],
                          detail={"frm": fields.get("frm"), "kind": fields.get("kind"), "why": why})
        except Exception:
            pass
        _loud(f"[packet-integrity] DROP {sid} from {fields.get('frm', '?')} ({why})")

    def _frag_problem(self, sid: str, prob) -> None:
        """A fragment was an orphan / arrived after its whole went stale / failed whole-verify."""
        kind, detail = prob
        try:
            from core.events.event_log import capture_event
            capture_event("packet_frag_problem", f"fragment {kind}: {detail}",
                          agent_id=self.agent_id, refs=[str(sid)],
                          detail={"problem": kind, "detail": detail})
        except Exception:
            pass
        _loud(f"[packet-frag] {kind} {sid}: {detail}")

    def _fragment_timeout(self, whole_id: str, missing) -> None:
        """A whole never completed within FRAG_REASSEMBLY_TTL -- drop it LOUD, NAME the missing
        seq(s) (pin 6): a missing fragment is detectable, never a silent partial message."""
        try:
            from core.events.event_log import capture_event
            capture_event("fragment_timeout",
                          f"whole {whole_id} incomplete: missing seq {missing}",
                          agent_id=self.agent_id, refs=[str(whole_id)],
                          detail={"whole_id": whole_id, "missing": missing})
        except Exception:
            pass
        _loud(f"[packet-frag] fragment_timeout whole={whole_id} missing seq {missing}")

    def _integrity_degraded_warn(self) -> None:
        """The integrity kill-switch is OFF: packets are delivered WITHOUT len/sha verification.
        That degraded mode must be LOUD, never silent (pin 4 / spec kill-switch clause). Rate-
        limited to once/60s per consumer so it stays visible without flooding a busy drain loop."""
        nowt = time.time()
        if nowt - self._last_degraded_warn < 60.0:
            return
        self._last_degraded_warn = nowt
        try:
            from core.events.event_log import capture_event
            capture_event("packet_integrity_degraded",
                          "PACKET_INTEGRITY_ENABLED is False -- delivering packets WITHOUT len/sha "
                          "verification (degraded to v1 integrity)", agent_id=self.agent_id)
        except Exception:
            pass
        _loud("[packet-integrity] DEGRADED: PACKET_INTEGRITY_ENABLED=False -- delivering UNVERIFIED "
              "packets (v1 integrity). Corruption will NOT be caught until you flip it back on.")

    # ------------------------------------------------ T043 durable reassembly (crash recovery)
    def _reasm_key(self) -> str:
        return f"{self.ns}:reasm:{self.agent_id}"

    def _reasm_persist(self, whole_id: str, slot: Optional[Dict[str, Any]]) -> None:
        """Mirror one in-flight reassembly slot to a Redis hash (slot=None deletes it on
        completion/timeout), so a consumer restart still fires the LOUD timeout for a partial
        (deepseek GATE RED fix: no silent loss on restart). Best-effort; never fails a drain."""
        if not self.online:
            return
        try:
            if slot is None:
                self._client.hdel(self._reasm_key(), whole_id)
            else:
                self._client.hset(self._reasm_key(), whole_id, json.dumps(slot, default=str))
        except Exception:
            pass

    def _rehydrate_reasm(self) -> None:
        """Reload any persisted in-flight partials at construction (crash recovery)."""
        if not self.online:
            return
        try:
            raw = self._client.hgetall(self._reasm_key()) or {}
            slots = {}
            for wid, val in raw.items():
                try:
                    slots[wid] = json.loads(val)
                except (ValueError, TypeError):
                    continue
            if slots:
                self._reasm.rehydrate(slots)
        except Exception:
            pass


_INSTANCES: Dict[str, Bus] = {}


def get_bus(agent_id: Optional[str] = None) -> Bus:
    """Module cache, one Bus per agent identity. agent_id defaults to $AGENT_ID or 'unknown'."""
    aid = str(agent_id or os.getenv("AGENT_ID", "unknown"))
    if aid not in _INSTANCES:
        _INSTANCES[aid] = Bus(aid)
    return _INSTANCES[aid]
