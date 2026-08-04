"""The API wire journal -- Wireshark-grade forensics for our own model traffic (T156 WIRE-A).

Daniil, 2026-08-04: *"I want us to use the same kind of forensics that wireshark has as well as
enterprise security appliances with deep packet sniffing"* and *"this will serve as a strong
foundation as well as be a good place for our security eyes when we get them"*.

WHY THIS LAYER AND NOT A WRAPPER. Wrapping `client.chat.completions.create()` cannot see the
wire, and that is measured rather than argued. `research/in-flight/wire-capture-deepseek-2026-08-02/
p5-rate-limit-headers.json` records `"no _response/response attribute on the SDK result"` with the
full `dir()` as evidence: the SDK parses the JSON body and drops the HTTP response. Worse, SDK
RETRIES happen INSIDE one `create()` call (`max_retries` at `scripts/deepseek_chat.py:63`), so a
wrapper sees one slow request where three round trips actually happened. Capture therefore sits at
the httpx TRANSPORT, reached through the SDK's own `http_client=` seam -- in-process, no TLS
interception, no second daemon to supervise. "Proxy vs call-site" was a false dichotomy.

WHAT WE WERE THROWING AWAY. deepseek reverse-engineered its own runner at runtime and counted it:
usage 5 of 9 fields read, chunk 1 of 7, HTTP headers 0 of 8, `finish_reason` 0 of 1, timing 0 of n.
Every one of those is already in our process. The cost of keeping them is zero additional API
calls -- two lines: read the field, write it down.

THE FIELDS THAT EARN THEIR PLACE, and what each diagnoses:

  system_fingerprint  the provider's own build id. It CHANGES when they swap the model behind an
                      endpoint. We discard it today, which means a silent swap looks like "the
                      agents got worse" with no cause -- and it would invalidate every
                      champion-challenger comparison in a tournament without anyone noticing.
  finish_reason       truncation. `length` means the answer was cut off, not finished.
  reasoning_tokens    the thinking budget INSIDE the completion budget. With finish_reason this
                      separates three failures we currently cannot tell apart: thought itself out
                      of an answer, was truncated, or genuinely had nothing to say. The corpus has
                      a real incident (`runner_reasoning_eats_final_answer`): 8000 tokens spent on
                      reasoning, empty content, no way to see why.
  cache hit/miss      cached prompt tokens bill at roughly a tenth of fresh ones, so this is the
                      largest cost lever we have. The prefix HASH is what makes a miss explicable.
  x-ds-trace-id       the provider's request UUID -- the handle their support needs to trace one
                      call. Invisible to the SDK; visible here.

METADATA ONLY, BY CONSTRUCTION. No request or response BODIES are ever written. Prompts are the
most sensitive bytes we produce, and a capture system that stores them needs redaction to exist
FIRST. Prefix hashes give the cache forensics with no content at all, so this ships now rather
than waiting on a DLP engine. When the security eyes arrive, body capture is their slice to
design -- and this journal is the seam they hook, not a thing they have to retrofit.

FAIL-OPEN, BUT NEVER SILENT. A recorder that throws must not take a runner down, so every write
is guarded. But a swallowed failure that vanishes is exactly the "unpopulated counter renders as
a MEASURED zero" defect this project keeps relearning -- so drops are COUNTED, and `summarize()`
reports them. Fail-open is only honest when the failures are visible.
"""
import atexit
import hashlib
import json
import os
import queue
import re
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "state", "wire")

# Rotation bound. The journal is diagnostic, not an archive: a season of 20 players must not be
# able to fill a disk. Oldest file is dropped, newest always survives.
MAX_FILES = int(os.getenv("AKASHIC_WIRE_MAX_FILES", "14"))
MAX_BYTES = int(os.getenv("AKASHIC_WIRE_MAX_BYTES", str(8 * 1024 * 1024)))

# Headers worth keeping. An allowlist, not a blocklist: a blocklist would leak the next header a
# provider invents, and authorization is exactly the header that must never land on disk.
KEEP_HEADERS = ("x-ds-trace-id", "x-request-id", "x-cache", "x-amz-cf-pop",
                "content-type", "server", "retry-after",
                "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens")

UNKNOWN = "UNKNOWN"          # T141 vocabulary: a field the provider never sent is not a zero.


def _sha(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8", "replace")).hexdigest()[:16]


# --------------------------------------------------------------------------- T157: shards
QUEUE_SIZE = int(os.getenv("AKASHIC_WIRE_QUEUE", "4096"))
MAX_SHARDS = int(os.getenv("AKASHIC_WIRE_MAX_SHARDS", "64"))
OVERFLOW_SHARD = "_overflow"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
# Windows refuses these as file OR directory names, with or without an extension, and the
# failure is an OSError at open() -- i.e. a silently dropped record on a machine that is our
# primary dev target. POSIX does not care; we pay the stricter rule everywhere so a journal
# copied between platforms stays readable.
_RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} \
    | {f"lpt{i}" for i in range(1, 10)}


def shard_name(agent: str) -> str:
    """Filesystem-safe DIRECTORY name for an agent id.

    Real ids in this fleet are 'claude#7507b107' and 'deepseek#ds-t155-', so this is not a
    theoretical concern. Sanitisation is LOSSY on purpose -- it is a fast path for selecting
    files, never an identity. The authoritative agent is the one inside each record, and
    read_all() re-checks it, so two ids that collide here still cannot read each other's rows.
    """
    s = _UNSAFE.sub("_", str(agent or "").strip())
    s = s.strip(". ")                       # '..' and trailing dots/spaces: traversal + Windows
    if not s:
        s = "unknown"
    if s.split(".")[0].lower() in _RESERVED:
        s = "_" + s
    return s[:64]


class _Shard:
    """One agent's slice of the journal: its own directory, cursor, queue and writer thread.

    The shard is the ISOLATION boundary. Rotation, quota and blast radius are all per-shard, so a
    runaway player fills its own directory and no one else's -- which is the property that makes
    a semi-trusted player pool safe to run at all, and it matters more than the microseconds.
    """

    def __init__(self, root: str, name: str, queue_size: int):
        self.name = name
        self.dir = os.path.join(root, name)
        self.day, self.n = "", 1              # segment cursor -- amortized O(1), see _segment_path
        self.q = queue.Queue(maxsize=queue_size)
        self.thread = None
        self.lock = threading.Lock()          # guards the SYNC path and the cursor
        # PER-SHARD drop count. The journal-wide total answers "did we lose records"; only this
        # answers "WHOSE records", and with a semi-trusted player pool that is the forensically
        # load-bearing question -- a player who floods its own queue to drop its own traffic is
        # the cheapest way to attack a telemetry store, and it must not be deniable.
        self.dropped = 0


class WireJournal:
    """Append-only JSONL of API round trips. One record per HTTP request, retries included."""

    def __init__(self, journal_dir: str = None, agent: str = "",
                 writer: str = None, queue_size: int = None):
        self._journal_dir = journal_dir or os.getenv("AKASHIC_WIRE_DIR") or DEFAULT_DIR
        self.agent = agent or os.getenv("BIFROST_AGENT") or "unknown"
        self.dropped = 0                      # W5: swallowed failures are counted, never silent

        # THE SEAM (T157). Two writers behind one record() signature:
        #   async  -- enqueue on the caller's thread, write on a per-shard background thread
        #   sync   -- the pre-T157 path, byte for byte
        # Selected per-instance or by AKASHIC_WIRE_WRITER, so the shipped behaviour is one env
        # var away and needs no revert. The operator's standing condition for risky work is that
        # it be reversible; a seam is how that is honoured without freezing the design.
        kind = (writer or os.getenv("AKASHIC_WIRE_WRITER") or "async").strip().lower()
        self.writer_kind = kind if kind in ("async", "sync") else "async"

        self._queue_size = int(queue_size or QUEUE_SIZE)
        self._shards = {}                     # shard name -> _Shard
        self._shards_lock = threading.Lock()
        self._paused = threading.Event()      # test hook: hold the writers to fill the queue
        self._closing = False
        self._seg_day, self._seg_n = "", 1    # legacy cursor, kept for the no-arg _segment_path
        self._lock = threading.Lock()
        atexit.register(self.flush)

    # ---------------------------------------------------------------- write
    def record(self, **kw) -> bool:
        """Hand off one round-trip record. NEVER raises -- returns True if it was ACCEPTED.

        Accepts loose kwargs on purpose: this is called from a transport hook and from the
        response-field extractor, and a capture path that can raise on an unexpected key is a
        capture path that takes a runner down.

        T157 changed what the return value MEANS on the async path, and the honest reading is
        "accepted for writing", not "on disk". The caller is mid-API-call and must not wait for
        a disk write; what it needs to know is whether the record was taken or dropped. A drop
        is counted either way, because a silent drop renders as a measured zero -- the hazard
        this repo has been bitten by twice.
        """
        try:
            rec = self._shape(kw)
            shard = self._shard_for(rec.get("agent"))
            if self.writer_kind == "sync":
                return self._write_now(shard, rec)
            try:
                shard.q.put_nowait(rec)
            except queue.Full:
                # BACKPRESSURE NEVER REACHES THE API THREAD. Blocking here would make telemetry
                # able to stall the very call it is observing, which is a worse failure than
                # losing a record. Drop, count, move on -- and count it AGAINST THE SHARD, so the
                # loss is attributable rather than merely known.
                self.dropped += 1
                shard.dropped += 1
                return False
            self._ensure_writer(shard)
            return True
        except Exception:
            self.dropped += 1                 # W4 + W5: swallow for the caller, but COUNT it
            return False

    # ------------------------------------------------------------ shards (T157)
    def _shard_for(self, agent: str) -> "_Shard":
        """The shard owning `agent`, created on demand and CAPPED.

        The cap is not hypothetical: the shard key comes from a record field, so a buggy or
        hostile caller that varies its agent id per request would otherwise spawn a directory,
        a queue and a THREAD per record. Past the cap everything lands in one overflow shard --
        which does reintroduce a shared resource for those callers, and that is the correct
        trade: the well-behaved fleet keeps its isolation, and the pathological case degrades to
        the behaviour we had before this slice instead of exhausting the process.
        """
        name = shard_name(agent or self.agent)
        with self._shards_lock:
            sh = self._shards.get(name)
            if sh is None:
                if len(self._shards) >= MAX_SHARDS:
                    name = OVERFLOW_SHARD
                    sh = self._shards.get(name)
                if sh is None:
                    sh = _Shard(self._journal_dir, name, self._queue_size)
                    self._shards[name] = sh
            return sh

    def _ensure_writer(self, shard: "_Shard"):
        if shard.thread is not None and shard.thread.is_alive():
            return
        with self._shards_lock:
            if shard.thread is not None and shard.thread.is_alive():
                return
            t = threading.Thread(target=self._drain, args=(shard,),
                                 name=f"wire-{shard.name}", daemon=True)
            shard.thread = t
            t.start()

    def _drain(self, shard: "_Shard"):
        """One shard's writer loop. Runs off the request thread, forever, quietly."""
        while True:
            try:
                rec = shard.q.get(timeout=1.0)
            except queue.Empty:
                if self._closing:
                    return
                continue
            try:
                while self._paused.is_set():
                    time.sleep(0.005)
                self._write_now(shard, rec)
            finally:
                shard.q.task_done()

    def _write_now(self, shard: "_Shard", rec: dict) -> bool:
        """The actual disk write. On the writer thread (async) or the caller's (sync)."""
        try:
            with shard.lock:
                os.makedirs(shard.dir, exist_ok=True)
                with open(self._segment_path(shard), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self._rotate(shard)
            return True
        except Exception:
            self.dropped += 1
            shard.dropped += 1
            return False

    def drops_by_shard(self) -> dict:
        """{agent-shard: dropped} -- WHOSE telemetry was lost, not merely that some was.

        A single journal-wide counter says the store is incomplete; it cannot say for whom, and
        "the instrument lost some records" is not a finding anyone can act on. Per-shard counts
        make a flooding player visible as itself.
        """
        return {name: sh.dropped for name, sh in list(self._shards.items()) if sh.dropped}

    def flush(self, timeout: float = 10.0) -> bool:
        """Block until every accepted record is on disk. For tests and clean shutdown.

        Deliberately NOT called on the hot path. Async buys the caller ~9000x precisely by not
        waiting, and a flush inside record() would hand all of that back.
        """
        deadline = time.time() + timeout
        for sh in list(self._shards.values()):
            self._ensure_writer(sh)
            while not sh.q.empty() and time.time() < deadline:
                time.sleep(0.002)
            with sh.lock:                     # the last record may be mid-write
                pass
        return all(sh.q.empty() for sh in list(self._shards.values()))

    def _flush_for_read(self, timeout: float = 2.0):
        """Drain before a read, but never from a writer thread and never while paused.

        Both exclusions are deadlocks rather than optimisations: a writer draining itself would
        wait forever, and a paused writer is a test deliberately holding records in the queue --
        flushing there would hang the very pin that proves backpressure works.
        """
        if self._paused.is_set() or threading.current_thread().name.startswith("wire-"):
            return
        self.flush(timeout=timeout)

    def pause(self):
        """Hold the writer threads. Test hook for proving backpressure never blocks a caller."""
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def _shape(self, kw: dict) -> dict:
        """Metadata only. Bodies are hashed, never stored (W2)."""
        usage = kw.get("usage") or {}
        details = (usage.get("completion_tokens_details") or {}) if isinstance(usage, dict) else {}
        prompt_details = (usage.get("prompt_tokens_details") or {}) if isinstance(usage, dict) else {}
        rec = {
            "ts": kw.get("ts") or time.time(),
            "agent": kw.get("agent") or self.agent,
            "model": kw.get("model"),
            "status": kw.get("status"),
            "attempt": kw.get("attempt", 0),          # W1: retries are separate round trips
            "stream": kw.get("stream"),
            "error": kw.get("error"),
            # -- the fields we measurably discard today --
            "system_fingerprint": kw.get("system_fingerprint"),
            "finish_reason": kw.get("finish_reason"),
            "service_tier": kw.get("service_tier"),
            "response_id": kw.get("response_id"),
            # -- usage, in full --
            "prompt_tokens": usage.get("prompt_tokens") if isinstance(usage, dict) else None,
            "completion_tokens": usage.get("completion_tokens") if isinstance(usage, dict) else None,
            "total_tokens": usage.get("total_tokens") if isinstance(usage, dict) else None,
            "reasoning_tokens": details.get("reasoning_tokens"),
            "cache_hit_tokens": (usage.get("prompt_cache_hit_tokens")
                                 if isinstance(usage, dict) else None),
            "cache_miss_tokens": (usage.get("prompt_cache_miss_tokens")
                                  if isinstance(usage, dict) else None),
            "cached_tokens": prompt_details.get("cached_tokens"),
            # -- timing --
            "ms_total": kw.get("ms_total"),
            "ms_first_byte": kw.get("ms_first_byte"),
            # -- content NEVER stored; hashes only, so a cache miss stays explicable (W2) --
            "prompt_sha": _sha(kw["prompt_text"]) if kw.get("prompt_text") is not None else None,
            "prompt_prefix_sha": (_sha(str(kw["prompt_text"])[:2000])
                                  if kw.get("prompt_text") is not None else None),
            "response_sha": _sha(kw["response_text"]) if kw.get("response_text") is not None else None,
            "headers": {k: v for k, v in (kw.get("headers") or {}).items()
                        if str(k).lower() in KEEP_HEADERS},
        }
        return rec

    def _segment_path(self, shard: "_Shard" = None) -> str:
        """The segment currently being appended to, ROLLING when it exceeds MAX_BYTES.

        T157: takes a SHARD. Called with none, it answers for this journal's own agent, which is
        what the pre-shard callers and pins mean by "the current segment".

        D1, found by the wire-next design workflow and reproduced before the fix: the previous
        implementation wrote to one file per day and, whenever that file exceeded MAX_BYTES,
        deleted the OLDEST file -- on every record. Measured 15 files -> 1 in 13 records. A size
        cap intended to bound the store had become a per-record shredder, and it destroyed exactly
        what a forensic store exists to keep. Deleting history to make room for a write is never
        the right answer; rolling to a new segment is.

        MEASURED, and the reason this is not a naive scan: probing from segment 1 on every record
        is O(segments). At 800 segments that cost 13,747us per call -- inside the lock, on the
        request thread. That regression was introduced BY the D1 fix above and caught only by the
        verification suite, which is the argument for having one. The cursor makes it amortized
        O(1): we walk forward from where we last were, and only when the segment is actually full.
        """
        if shard is None:
            shard = self._shard_for(self.agent)
        # The shard directory is created HERE rather than at the call site, so the returned path
        # is always one a caller may append to. Costs the same stat the write path already paid,
        # and without it _segment_path() hands back a path inside a directory that does not exist
        # yet -- which is exactly how it broke the D1 regression pin when shards landed.
        try:
            os.makedirs(shard.dir, exist_ok=True)
        except OSError:
            pass                               # unwritable dir is the write path's problem to count
        day = time.strftime("%Y%m%d")
        if shard.day != day:                   # new day -> restart the cursor
            shard.day, shard.n = day, 1
        while True:
            p = os.path.join(shard.dir, f"wire-{day}-{shard.n:03d}.jsonl")
            try:
                if os.path.getsize(p) <= MAX_BYTES:
                    return p
            except OSError:
                return p                       # does not exist yet -> this is the one to write
            shard.n += 1

    def _rotate(self, shard: "_Shard" = None):
        """Bound the store by TOTAL size and segment count -- never as a side effect of one write.

        Deletion happens only while genuinely over budget, and the newest segment is never a
        candidate: an investigation reaches for what just happened.

        T157: the budget is PER SHARD. That is the isolation property, and without it sharding
        would be a naming convention -- a runaway player would still evict every other player's
        history, which is exactly the blindness a semi-trusted pool must not be able to cause.
        The cost is that worst-case disk is now MAX_FILES * MAX_BYTES * shards rather than a
        single global budget; bounding the fleet is the shard CAP's job, not this loop's.
        """
        files = self._shard_files(shard) if shard is not None else self.files()
        while len(files) > MAX_FILES:
            try:
                os.remove(files[0])
            except Exception:
                break
            files = files[1:]
        try:
            budget = MAX_BYTES * MAX_FILES
            total = sum(os.path.getsize(f) for f in files)
            while total > budget and len(files) > 1:
                oldest = files[0]
                sz = os.path.getsize(oldest)
                os.remove(oldest)
                total -= sz
                files = files[1:]
        except Exception:
            pass

    # ---------------------------------------------------------------- read
    def _shard_files(self, shard: "_Shard"):
        """One shard's segments -- the unit rotation and quota operate on."""
        try:
            return sorted(os.path.join(shard.dir, f) for f in os.listdir(shard.dir)
                          if f.startswith("wire-") and f.endswith(".jsonl"))
        except Exception:
            return []

    def files(self, agent: str = None):
        """Every segment: shard directories PLUS pre-T157 segments at the journal root.

        Legacy files are included deliberately. A telemetry store that loses its history on
        upgrade is a worse failure than the convoy this slice removed, and the old flat segments
        are still perfectly good records -- they simply predate the shard layout.

        `agent` narrows to one shard, which is the file SELECTION read_all()'s docstring promised
        when it said this filter "becomes a file selection rather than a scan". It is a fast path
        only: sanitisation is lossy, so the caller must still verify the in-record agent.
        """
        self._flush_for_read()                 # same reason as read_all: reads see what was accepted
        out = []
        root = self._journal_dir
        try:
            for entry in sorted(os.listdir(root)):
                p = os.path.join(root, entry)
                if os.path.isdir(p):
                    if agent is not None and entry != shard_name(agent):
                        continue
                    out += sorted(os.path.join(p, f) for f in os.listdir(p)
                                  if f.startswith("wire-") and f.endswith(".jsonl"))
                elif entry.startswith("wire-") and entry.endswith(".jsonl"):
                    out.append(p)              # pre-T157 flat segment
        except Exception:
            return []
        return out

    def read_all(self, limit: int = 0, agent: str = None):
        """`agent` scopes to one seat's records.

        Needed the moment a reader iterates a fleet: doctor examines every agent, so an unscoped
        read rendered the same finding 15 times -- one per agent -- which is noise dressed as
        signal. Scoping also pre-figures T157, where the journal shards per agent and this filter
        becomes a file selection rather than a scan.
        """
        # T157: a READ drains pending writes first, so "record then read" still sees your record.
        # Async moved the write off the caller's thread; it must not also move the goalposts for
        # every reader. Consistency belongs HERE because this is not the hot path -- the whole
        # point of the slice is that the API thread never waits, and a reader waiting a few
        # milliseconds costs nothing. Without this, doctor renders a report that is stale by up to
        # a queue's worth of records and has no way to know it.
        self._flush_for_read()

        rows = []
        # Scoping is now a file SELECTION (one shard directory) instead of a whole-store scan.
        # The in-record filter below still runs and is AUTHORITATIVE -- shard names are sanitised
        # and therefore lossy, so 'team/one' and 'team:one' can share a directory.
        for p in self.files(agent=agent) if agent else self.files():
            try:
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            continue           # a torn line is one lost record, not a dead reader
            except Exception:
                continue
        if agent:
            rows = [r for r in rows if str(r.get("agent") or "") == str(agent)]
        return rows[-limit:] if limit else rows

    def summarize(self, limit: int = 0, agent: str = None) -> dict:
        """THE READER (W6). Ships with the writer, because `cognitive_metrics` is the standing
        proof of what happens otherwise: five runners feeding an accumulator nothing reads.

        This is the Expert Info panel in miniature -- it does not print packets, it says what is
        WRONG. Every aggregate distinguishes MEASURED from UNKNOWN (W7): a field the provider
        never sent renders as UNKNOWN, never as 0, because a zero here would be a lie that reads
        like a measurement.
        """
        rows = self.read_all(limit, agent=agent)
        out = {
            "records": len(rows),
            "dropped_captures": self.dropped,
            "journal_dir": self._journal_dir,
        }
        if not rows:
            for k in ("reasoning_tokens", "total_tokens", "cache_hit_rate", "truncated",
                      "errors", "retries", "fingerprints"):
                out[k] = UNKNOWN
            return out

        def _sum(field):
            vals = [r.get(field) for r in rows if isinstance(r.get(field), (int, float))]
            return sum(vals) if vals else UNKNOWN

        out["total_tokens"] = _sum("total_tokens")
        out["reasoning_tokens"] = _sum("reasoning_tokens")
        out["truncated"] = sum(1 for r in rows if r.get("finish_reason") == "length")
        out["errors"] = sum(1 for r in rows if r.get("error"))
        out["retries"] = sum(1 for r in rows if (r.get("attempt") or 0) > 0)
        # A fingerprint CHANGE is the silent-model-swap signal -- the set, not a count.
        out["fingerprints"] = sorted({r.get("system_fingerprint") for r in rows
                                      if r.get("system_fingerprint")})
        hit, miss = _sum("cache_hit_tokens"), _sum("cache_miss_tokens")
        if isinstance(hit, (int, float)) and isinstance(miss, (int, float)) and (hit + miss) > 0:
            out["cache_hit_rate"] = round(hit / (hit + miss), 4)
        else:
            out["cache_hit_rate"] = UNKNOWN
        return out

    def expert(self, limit: int = 0, agent: str = None):
        """Expert Info: the wrong things, named. Wireshark's real value is not the packet list.

        Each finding below is the LLM analogue of a transport diagnostic -- truncation is a cut
        frame, a retry is a retransmission, a fingerprint change is a route flap. Returns a list
        of (severity, headline, detail) so a caller can render or alert.
        """
        s = self.summarize(limit, agent=agent)
        findings = []
        if s["records"] == 0:
            return [("info", "no traffic captured", "journal is empty -- is the transport hooked?")]
        if isinstance(s.get("truncated"), int) and s["truncated"]:
            findings.append(("warn", f"{s['truncated']} truncated response(s)",
                             "finish_reason=length -- the answer was cut off, not finished"))
        if isinstance(s.get("retries"), int) and s["retries"]:
            findings.append(("warn", f"{s['retries']} retried round trip(s)",
                             "retransmission-class: the SDK re-sent inside one call"))
        if isinstance(s.get("errors"), int) and s["errors"]:
            findings.append(("error", f"{s['errors']} failed round trip(s)", "see .error per record"))
        # Found by the first live run: a 401 produced no finding, because only EXCEPTIONS were
        # counted and an HTTP error status is a perfectly successful round trip at the transport.
        # A forensics tool that stays quiet about 4xx/5xx is the blindness it was built to cure.
        bad = {}
        for r in self.read_all(limit, agent=agent):
            st = r.get("status")
            if isinstance(st, int) and not (200 <= st < 300):
                bad[st] = bad.get(st, 0) + 1
        for st, n in sorted(bad.items()):
            sev = "warn" if st in (408, 409, 429) or st >= 500 else "error"
            findings.append((sev, f"HTTP {st} x{n}",
                             "auth/quota/server-side -- correlate with x-ds-trace-id for support"))
        if len(s.get("fingerprints") or []) > 1:
            findings.append(("error", "system_fingerprint CHANGED mid-capture",
                             f"{s['fingerprints']} -- the provider may have swapped the model "
                             f"behind the endpoint; any A/B comparison spanning this is invalid"))
        if s.get("cache_hit_rate") == UNKNOWN:
            findings.append(("info", "cache hit rate UNKNOWN",
                             "provider reported no cache fields -- not the same as a 0% hit rate"))
        elif isinstance(s["cache_hit_rate"], float) and s["cache_hit_rate"] < 0.2:
            findings.append(("warn", f"cache hit rate {s['cache_hit_rate']:.0%}",
                             "cached prompt tokens bill ~10x cheaper; a low rate is the largest "
                             "cost lever available -- compare prompt_prefix_sha across turns"))
        if s.get("dropped_captures"):
            findings.append(("warn", f"{s['dropped_captures']} capture(s) dropped",
                             "the recorder failed open -- these round trips are NOT in the journal"))
        return findings or [("info", "no anomalies", f"{s['records']} round trip(s) clean")]


_DEFAULT = None


def journal() -> "WireJournal":
    """Process-wide journal. One per process keeps the drop counter meaningful."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = WireJournal()
    return _DEFAULT


def recording_http_client(timeout=None, **kw):
    """An httpx.Client whose transport journals every round trip -- pass to OpenAI(http_client=...).

    THIS is the layer the SDK hides. `client.chat.completions.create()` returns a parsed body with
    no HTTP response attached, so a wrapper around it cannot see status, headers, or the fact that
    the SDK already retried twice inside that one call. A transport sees each request as itself.

    Returns None if httpx is unavailable, so a caller can fall back to the ordinary client rather
    than fail: telemetry must never be the reason a runner cannot start.
    """
    try:
        import httpx
    except Exception:
        return None

    class _RecordingTransport(httpx.HTTPTransport):
        """One journal record per HTTP round trip (W1).

        RETRY DETECTION, stated honestly: httpx never tells a transport "this is a retry" -- the
        SDK simply calls again. So a repeat is INFERRED: same URL, previous attempt ended non-2xx
        or errored, within 120s. That is a heuristic and it is labelled as one; it is not a claim
        the transport was told anything.
        """

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._last = None            # (url, attempt, ok, ts)

        def _attempt_for(self, url):
            prev = self._last
            if prev and prev[0] == url and not prev[2] and (time.time() - prev[3]) < 120:
                return prev[1] + 1
            return 0

        def handle_request(self, request):
            url = str(request.url)
            attempt = self._attempt_for(url)
            t0 = time.time()
            try:
                resp = super().handle_request(request)
            except Exception as e:
                self._last = (url, attempt, False, time.time())
                journal().record(status=None, error=type(e).__name__, attempt=attempt,
                                 ms_first_byte=int((time.time() - t0) * 1000),
                                 model=request.headers.get("x-model"), stream=None)
                raise                     # never swallow the caller's error, only observe it
            ok = 200 <= resp.status_code < 300
            self._last = (url, attempt, ok, time.time())
            # Headers are available HERE and nowhere upstream. The body is deliberately not read:
            # touching resp.stream would consume the SSE stream the caller is about to iterate.
            journal().record(status=resp.status_code, attempt=attempt,
                             headers=dict(resp.headers),
                             ms_first_byte=int((time.time() - t0) * 1000))
            return resp

    return httpx.Client(transport=_RecordingTransport(), timeout=timeout, **kw)
