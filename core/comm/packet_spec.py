"""
Packet Spec v1 -- envelope integrity + MTU library (T040 LAW; built in T043).

Cites docs/packet-spec-v1-2026-07.md (Status: LAW). This module is the SINGLE SOURCE OF
TRUTH for the parts of the packet contract that are pure computation -- the MTU bound, the
len+sha integrity pair over a canonical serialization, and (below) fragmentation/reassembly
of oversize payloads. It has NO Redis / IO dependency, so both doors compute identically:
the SEND door (bus._emit) stamps, the CONSUME door (bus._drain) verifies, and the answer
filter (expectations._answers_since) reuses the SAME verify so a corrupt reply is invisible
to every consume path (RB-29 extension, pin 9). Pure functions => the 10 acceptance pins
test computation, not transport.

Why a separate module (spec R6): "schemas live in core/comm/packet_spec.py (code is the
source of truth; families are contracts, not tunables)". bus.py orchestrates; this computes.

CANONICAL INTEGRITY FIELDS. The seven v1 wire fields (frm, to, kind, content, ts, meta,
parts) -- exactly as they already sit in the Redis stream, i.e. the literal STRING values
(content/meta/parts are json.dumps'd at the send door) -- are hashed in canonical form.
Hashing the literal stream strings (NOT re-parsed objects) guarantees the consume door,
which reads those exact bytes back from Redis, computes a byte-identical digest; a
re-parse->re-serialize round-trip would risk dict-order / float-repr drift. Envelope-control
fields (v, len, sha, frag, lane, family, pri, deadline_ts, seq, ecn, idempotency_key) are
deliberately NOT hashed: they are transport metadata with their own validators, not message
content -- and you cannot hash the hash.

DIALS are read at CALL time (not import time), matching the codebase's per-call config
pattern, so a flip is honored live without reimport:
  BUS_MAX_MESSAGE_BYTES   (default 65536) -- MTU; a packet whose canonical len exceeds it is
                          REFUSED loud at send (never truncated), or fragmented if opted in.
  PACKET_INTEGRITY_ENABLED(default True)  -- kill-switch; False degrades to v1 integrity, LOUD.
  FRAG_REASSEMBLY_TTL     (default 300s)  -- a whole whose fragments do not all arrive within
                          this window is dropped LOUD with the missing seq(s) named.
"""
import hashlib
import json
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

SPEC_VERSION = 2
DEFAULT_MAX_MESSAGE_BYTES = 65536
DEFAULT_FRAG_REASSEMBLY_TTL = 300

# The seven v1 wire fields hashed for content integrity, in the spec's EXPLICIT canonical
# order -- this tuple IS the serialization order (canonical_bytes builds the dict from it and
# does NOT sort_keys), so any independent verifier following the spec agrees byte-for-byte.
CANONICAL_FIELDS = ("frm", "to", "kind", "content", "ts", "meta", "parts")


# --------------------------------------------------------------------------- dials
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def max_message_bytes() -> int:
    return _int_env("BUS_MAX_MESSAGE_BYTES", DEFAULT_MAX_MESSAGE_BYTES)


def integrity_enabled() -> bool:
    return _bool_env("PACKET_INTEGRITY_ENABLED", True)


def frag_reassembly_ttl() -> int:
    return _int_env("FRAG_REASSEMBLY_TTL", DEFAULT_FRAG_REASSEMBLY_TTL)


# ------------------------------------------------------------------ canonical len+sha
def canonical_bytes(fields: Dict[str, Any]) -> bytes:
    """The exact bytes hashed for integrity: the seven v1 wire fields as literal strings,
    in the spec's EXPLICIT canonical order (frm,to,kind,content,ts,meta,parts), compact-
    separated. Missing field => empty string (a v1 envelope always carries all seven, but be
    defensive). content/meta/parts are hashed VERBATIM as the already-serialized strings the
    stream holds.

    ORDER IS EXPLICIT, NOT sort_keys (T043 fence reconciliation, 2026-07-13): the spec names
    'canonical order (frm,to,kind,content,ts,meta,parts)'. A single implementation could use
    sort_keys and stay self-consistent, but ANY independent verifier (a future consumer, a
    port, an OTLP exporter following the spec's stated order) would then disagree. We build the
    dict in roster order and DO NOT sort (Python 3.7+ preserves insertion order; json.dumps
    honors it when sort_keys is False) so the digest matches the spec verbatim."""
    canon = {k: ("" if fields.get(k) is None else str(fields.get(k))) for k in CANONICAL_FIELDS}
    return json.dumps(canon, sort_keys=False, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def compute_len_sha(fields: Dict[str, Any]) -> Tuple[int, str]:
    """(byte length, sha256 hex) over the canonical serialization. The len is ALSO the size
    the MTU bounds -- one honest number for both 'is it too big' and 'did it arrive whole'."""
    b = canonical_bytes(fields)
    return len(b), hashlib.sha256(b).hexdigest()


def stamp(env: Dict[str, Any], *, length: Optional[int] = None,
          sha: Optional[str] = None) -> Dict[str, Any]:
    """SEND door: stamp v + len + sha onto the envelope (mutates and returns it). Redis stream
    fields are strings, so the integrity fields are stringified too. Pass a precomputed
    (length, sha) to avoid re-hashing on the hot path when the caller already ran the MTU check."""
    if length is None or sha is None:
        length, sha = compute_len_sha(env)
    env["v"] = str(SPEC_VERSION)
    env["len"] = str(length)
    env["sha"] = sha
    return env


def verify_integrity(fields: Dict[str, Any]) -> Tuple[bool, str]:
    """CONSUME door + reply filter: recompute len+sha over the canonical fields and compare
    to the stamped values. Returns (ok, reason).

    - kill-switch OFF (PACKET_INTEGRITY_ENABLED False): always (True, 'integrity-disabled')
      -- degraded to v1 integrity; the caller logs LOUD, never silent (pin 4).
    - a legacy v1 message (no sha stamped): (True, 'v1-unstamped') -- never drop mail for
      schema alone (spec: consumers downgrade unknown versions, they do not drop; pin 10).
    - len disagrees: (False, 'len-mismatch ...') BEFORE sha, so len-wrong/sha-right is named
      distinctly from sha-wrong/len-right (probe P3).
    - sha disagrees: (False, 'sha-mismatch ...').
    - both agree: (True, 'ok').
    """
    if not integrity_enabled():
        return True, "integrity-disabled"
    stamped_sha = fields.get("sha")
    if not stamped_sha:
        return True, "v1-unstamped"
    length, sha = compute_len_sha(fields)
    stamped_len = fields.get("len")
    if stamped_len is not None and str(stamped_len) != str(length):
        return False, f"len-mismatch: stamped={stamped_len} actual={length}"
    if sha != stamped_sha:
        return False, f"sha-mismatch: stamped={str(stamped_sha)[:12]}.. actual={sha[:12]}.."
    return True, "ok"


# ------------------------------------------------------------------------- MTU gate
def mtu_refusal_text(size: int, limit: Optional[int] = None) -> str:
    """The EXACT teaching text a refused oversize send emits (pin 1 asserts it verbatim)."""
    limit = max_message_bytes() if limit is None else limit
    return (f"REFUSED: packet {size}B exceeds BUS_MAX_MESSAGE_BYTES {limit}B "
            f"(never truncated). Fragment it (allow_frag=True), send large media as a "
            f"blob-ref Part (media-by-reference), or split the payload.")


def within_mtu(nbytes: int) -> bool:
    """True when a canonical size is deliverable as a single packet (<= the MTU dial).
    Default 65536: 65535 ok, 65536 ok, 65537 refused (pin 1)."""
    return nbytes <= max_message_bytes()


# Storage-intake tools whose arguments ARE the payload that used to be silently clipped at the
# note/file door (the 2026-07-12 receipts). Their serialized args ride the same MTU as a packet.
MTU_GATED_TOOLS = ("write_file", "edit_file", "knowledge_note")


def tool_args_within_mtu(name: str, args: Any) -> Tuple[bool, str]:
    """The runner tool-bridge gate (pin 8): (ok, refusal_text). For a storage-intake tool, refuse
    LOUD when the serialized args exceed the packet MTU -- replacing the old ~4k silent clip at the
    bite site with a visible refusal the model can act on. Non-gated tools always pass."""
    if name not in MTU_GATED_TOOLS:
        return True, ""
    try:
        payload = json.dumps({"tool": name, "args": args}, default=str)
    except Exception:
        payload = str(args)
    size = len(payload.encode("utf-8"))
    if within_mtu(size):
        return True, ""
    return False, (f"REFUSED: {name} args {size}B exceed the {max_message_bytes()}B limit "
                   f"(never silently clipped -- T043). Split the content into multiple smaller "
                   f"{name} calls, or write a blob and reference it.")


# ------------------------------------------------------------------ lanes (T039a)
# Kind -> lane router. R6 rules this file the roster home (families/kinds are contracts,
# not tunables); the lane CONTRACT (QoS/seat/wake/retention) lives in the LAW spec and the
# governing design doc (docs/t039-lanes-latches-design-2026-07.md, Daniel gate 2026-07-13).
# Senders cannot choose lanes; the door derives lane from kind.
LANES = ("work", "sig", "trace")            # + test-* per drill namespace (T039b formalizes)

KIND_LANE = {
    # work -- directed mail + coordination answers (QoS1/AF, RB-21 seat, THE wake lane)
    "handoff": "work", "reply": "work", "request": "work", "question": "work",
    "chat": "work", "inform": "work", "note": "work", "answer": "work", "query": "work",
    "dispatch": "work", "status": "work",
    "completion": "work",   # T061 census fix: a completion is an ANSWER kind (settles
                            # expectations) -- it must ride the wake lane, never legacy-only
    # sig -- fidelity-ladder control (QoS1/EF, seatless, never queues behind trace)
    "halt": "sig", "interrupt": "sig", "pause": "sig", "resume": "sig",
    "nudge": "sig", "steer": "sig",
    # trace -- telemetry + re-derivable hints (QoS0/BE ring; the durable ledger is truth
    # for ledger_update/resolved/hint, so lossy retention is correct for them)
    "trace": "trace", "thinking": "trace", "tool": "trace", "narration": "trace",
    "ledger_update": "trace", "resolved": "trace", "hint": "trace",
}

# P0 retention (dual-write soak): approximate-trim everywhere; the per-lane REFUSE-WRITE
# overflow contract activates at the T039b cutover when a lane becomes load-bearing.
LANE_MAXLEN = {"work": 10000, "sig": 5000, "trace": 5000}

DEFAULT_TRACE_SPOT_INTERVAL = 1000


def lane_for(kind: Any) -> Optional[str]:
    """The pure router: lane for a kind, or None when unmapped. STRANGLER PHASE: None means
    legacy-only + loud (a sender must never break on a census miss); the spec's unknown-kind
    REFUSAL is the end state and activates at the T039b/d cutover."""
    return KIND_LANE.get(str(kind))


def lane_maxlen(lane: str) -> int:
    return LANE_MAXLEN.get(lane, 10000)


def dual_write_enabled() -> bool:
    """T039a P0 kill-switch. Default ON: the dual-write IS the slice (a live soak of the
    lane write path; consumers untouched, lane cursors init tail-at-flip per A4)."""
    return _bool_env("BIFROST_LANES_DUAL_WRITE", True)


def trace_spot_interval() -> int:
    return _int_env("PACKET_TRACE_SPOT_INTERVAL", DEFAULT_TRACE_SPOT_INTERVAL)


def lane_wants_integrity(lane: str, tick: int = 0) -> bool:
    """R5 + amend E: len+sha REQUIRED on work/sig/test-*; on trace DIAL-OPTIONAL
    (PACKET_INTEGRITY_TRACE, default off) with an every-Nth spot-check stamped via the
    global tick so a corrupt trace stream stays detectable at ~1/N cost."""
    if lane != "trace":
        return True
    if _bool_env("PACKET_INTEGRITY_TRACE", False):
        return True
    n = trace_spot_interval()
    return n > 0 and tick > 0 and tick % n == 0


def lane_stream_key(ns: str, lane: str, to: Optional[str] = None) -> str:
    """Per-lane key: the lane dimension inserted before the topology suffix (design B5).
    trace is ONE shared ring (no per-agent inbox, no bell, no cursor)."""
    if lane == "trace":
        return f"{ns}:trace"
    return f"{ns}:{lane}:inbox:{to}" if to else f"{ns}:{lane}:broadcast"


# --------------------------------------------------------------------- fragmentation
def parse_frag(fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The frag header {seq,of,whole_id,whole_len,whole_sha} from an envelope, or None if the
    packet is not a fragment. Tolerates the header arriving as a dict or a json string."""
    raw = fields.get("frag")
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else None
    except (ValueError, TypeError):
        return None


def _chunk_by_bytes(s: str, max_bytes: int) -> List[str]:
    """Greedy split of a str into pieces each <= max_bytes when UTF-8 encoded, NEVER splitting
    a multibyte char. O(len(s)). Concatenating the pieces reproduces s exactly."""
    max_bytes = max(1, max_bytes)
    chunks: List[str] = []
    cur: List[str] = []
    cur_bytes = 0
    for ch in s:
        cb = len(ch.encode("utf-8"))
        if cur and cur_bytes + cb > max_bytes:
            chunks.append("".join(cur))
            cur, cur_bytes = [], 0
        cur.append(ch)
        cur_bytes += cb
    if cur:
        chunks.append("".join(cur))
    return chunks or [""]


def fragment(fields: Dict[str, Any], *, max_bytes: Optional[int] = None) -> List[Dict[str, Any]]:
    """Split an oversize envelope into N fragment envelopes (opt-in: the send door calls this
    only when allow_frag=True and the packet exceeds the MTU). Each fragment replicates the
    small routing fields (frm,to,kind,ts,meta,parts), carries a slice of the content STRING,
    and carries frag={seq,of,whole_id,whole_len,whole_sha} so the consumer can order the
    pieces, know the set is complete ('of'), and VERIFY the reassembled whole. Each fragment
    is itself a valid, under-MTU, len+sha-stamped packet. whole_id is content-addressed
    (whole_sha[:32]) so an identical whole re-sent reassembles idempotently."""
    limit = max_message_bytes() if max_bytes is None else max_bytes
    whole_len, whole_sha = compute_len_sha(fields)
    whole_id = whole_sha[:32]
    content = "" if fields.get("content") is None else str(fields.get("content"))
    template = {k: fields.get(k) for k in CANONICAL_FIELDS}
    template["content"] = ""
    overhead = len(canonical_bytes(template)) + 160     # slack for the frag dict + v/len/sha
    budget = max(1, limit - overhead)
    pieces = _chunk_by_bytes(content, budget)
    of = len(pieces)
    frags: List[Dict[str, Any]] = []
    for seq, piece in enumerate(pieces):
        fenv = {k: fields.get(k) for k in CANONICAL_FIELDS}
        fenv["content"] = piece
        fenv["frag"] = json.dumps({"seq": seq, "of": of, "whole_id": whole_id,
                                   "whole_len": whole_len, "whole_sha": whole_sha})
        stamp(fenv)                                     # each fragment is independently integrity-checked
        frags.append(fenv)
    return frags


_DONE_CAP = 8192


class Reassembler:
    """Consumer-side fragment buffer (one per Bus instance). Reconciliation R-3: the cursor
    advances past received fragments and they are buffered HERE; the whole is emitted the moment
    its last seq lands; a whole that never completes within FRAG_REASSEMBLY_TTL is dropped LOUD by
    sweep_expired with its missing seq(s) named.

    CRASH-DURABLE (T043 verify-gate fix, deepseek GATE RED round 1): an optional `persist`
    callback mirrors each in-flight slot to durable storage (the Bus wires a Redis hash), and
    `rehydrate` reloads it at startup -- so a consumer restart mid-reassembly still fires the LOUD
    timeout (and can still complete) instead of losing the partial SILENTLY. `persist=None` keeps
    it pure in-memory (unit tests, and any consumer without a live bus)."""

    def __init__(self, persist=None) -> None:
        # whole_id -> {"of", "pieces": {seq: content}, "first": float, "whole_len", "whole_sha"}
        self._buf: Dict[str, Dict[str, Any]] = {}
        self._done: "OrderedDict[str, None]" = OrderedDict()   # bounded LRU of finished whole_ids
        self._persist = persist    # callable(whole_id, slot|None); None => in-memory only

    def rehydrate(self, slots: Dict[str, Dict[str, Any]]) -> None:
        """Load persisted partial slots at startup (crash recovery). seq keys are normalized back
        to int (json stringifies dict keys).

        A rehydrated slot that ALREADY holds all `of` pieces is SKIPPED and cleaned up: it can only
        mean an already-completed-and-delivered whole whose durable delete did not land (a swallowed
        Redis error, or a crash between deliver and delete). Resurrecting it would risk a DOUBLE
        DELIVERY, because the `_done` dedup guard is in-memory and gone after a restart. So only
        genuinely-INCOMPLETE slots come back -- upholding the invariant by construction, not by
        assuming the delete always succeeds (deepseek GATE RED round 2)."""
        for wid, slot in (slots or {}).items():
            pieces = slot.get("pieces", {})
            slot["pieces"] = {int(k): v for k, v in pieces.items()}
            of = slot.get("of", 0)
            if of and len(slot["pieces"]) >= of:          # already-complete -> never resurrect
                if self._persist is not None:
                    try:
                        self._persist(str(wid), None)     # clean up the orphaned durable slot
                    except Exception:
                        pass
                continue
            self._buf[str(wid)] = slot

    def _save(self, wid: str) -> None:
        if self._persist is not None:
            try:
                self._persist(wid, self._buf.get(wid))     # slot when present, None once popped (delete)
            except Exception:
                pass

    def _mark_done(self, wid: str) -> None:
        self._done[wid] = None
        self._done.move_to_end(wid)
        while len(self._done) > _DONE_CAP:
            self._done.popitem(last=False)

    def add(self, fields: Dict[str, Any], *, now: float
            ) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[str, str]]]:
        """Feed one fragment. Returns (whole|None, problem|None):
          - whole: the reassembled, whole-verified envelope, when this frag completes the set.
          - problem: (kind, detail) with kind in {orphan, whole-corrupt, stale} for a LOUD log
            (the frag is dropped).
          - (None, None): buffered, set still incomplete (or a late dup of a finished whole)."""
        frag = parse_frag(fields)
        if frag is None:
            return None, None                              # not a fragment
        wid = frag.get("whole_id")
        try:
            of = int(frag.get("of", 0))
            seq = int(frag.get("seq", -1))
        except (TypeError, ValueError):
            return None, ("orphan", "non-int seq/of")
        if not wid or of <= 0 or seq < 0 or seq >= of:
            return None, ("orphan", f"bad frag header seq={seq} of={of} whole={wid}")
        if wid in self._done:
            return None, None                              # late/duplicate frag of a finished whole
        slot = self._buf.get(wid)
        if slot is None:
            slot = self._buf[wid] = {"of": of, "pieces": {}, "first": now,
                                     "whole_len": frag.get("whole_len"),
                                     "whole_sha": frag.get("whole_sha")}
        if now - slot["first"] > frag_reassembly_ttl():    # a late arrival cannot complete a stale set
            missing = [i for i in range(slot["of"]) if i not in slot["pieces"]]
            self._buf.pop(wid, None)
            self._mark_done(wid)
            self._save(wid)                                # drop the durable slot too
            return None, ("stale", f"whole {wid} exceeded TTL; missing seq {missing}")
        slot["pieces"][seq] = "" if fields.get("content") is None else str(fields.get("content"))
        if len(slot["pieces"]) < slot["of"]:
            self._save(wid)                                # persist the growing partial (crash-durable)
            return None, None                              # incomplete
        content = "".join(slot["pieces"][i] for i in range(slot["of"]))
        whole = {k: fields.get(k) for k in CANONICAL_FIELDS}
        whole["content"] = content
        self._buf.pop(wid, None)
        self._mark_done(wid)
        self._save(wid)                                    # complete -> delete the durable slot
        wl, ws = slot.get("whole_len"), slot.get("whole_sha")
        length, sha = compute_len_sha(whole)
        if ws and sha != ws:
            return None, ("whole-corrupt", f"reassembled {wid} sha {sha[:12]}.. != {str(ws)[:12]}..")
        if wl is not None and str(wl) != str(length):
            return None, ("whole-corrupt", f"reassembled {wid} len {length} != {wl}")
        stamp(whole)                                       # deliver a clean v2 packet
        return whole, None

    def sweep_expired(self, now: float) -> List[Tuple[str, List[int]]]:
        """Drop wholes past TTL; return [(whole_id, [missing seqs])] for a LOUD fragment_timeout
        event. Call at drain time (cheap: iterates only in-flight partial sets)."""
        ttl = frag_reassembly_ttl()
        dead: List[Tuple[str, List[int]]] = []
        for wid, slot in list(self._buf.items()):
            if now - slot["first"] > ttl:
                missing = [i for i in range(slot["of"]) if i not in slot["pieces"]]
                dead.append((wid, missing))
                self._buf.pop(wid, None)
                self._mark_done(wid)
                self._save(wid)                            # drop the durable slot
        return dead
