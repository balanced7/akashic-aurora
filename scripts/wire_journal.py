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
import hashlib
import json
import os
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


class WireJournal:
    """Append-only JSONL of API round trips. One record per HTTP request, retries included."""

    def __init__(self, journal_dir: str = None, agent: str = ""):
        self._journal_dir = journal_dir or os.getenv("AKASHIC_WIRE_DIR") or DEFAULT_DIR
        self.agent = agent or os.getenv("BIFROST_AGENT") or "unknown"
        self.dropped = 0                      # W5: swallowed failures are counted, never silent
        self._lock = threading.Lock()
        self._seg_day, self._seg_n = "", 1    # segment cursor -- see _segment_path (amortized O(1))

    # ---------------------------------------------------------------- write
    def record(self, **kw) -> bool:
        """Write one round-trip record. NEVER raises -- returns True if it landed.

        Accepts loose kwargs on purpose: this is called from a transport hook and from the
        response-field extractor, and a capture path that can raise on an unexpected key is a
        capture path that takes a runner down.
        """
        try:
            rec = self._shape(kw)
            with self._lock:
                os.makedirs(self._journal_dir, exist_ok=True)
                with open(self._segment_path(), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self._rotate()
            return True
        except Exception:
            self.dropped += 1                 # W4 + W5: swallow for the caller, but COUNT it
            return False

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

    def _segment_path(self) -> str:
        """The segment currently being appended to, ROLLING when it exceeds MAX_BYTES.

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
        day = time.strftime("%Y%m%d")
        if self._seg_day != day:               # new day -> restart the cursor
            self._seg_day, self._seg_n = day, 1
        while True:
            p = os.path.join(self._journal_dir, f"wire-{day}-{self._seg_n:03d}.jsonl")
            try:
                if os.path.getsize(p) <= MAX_BYTES:
                    return p
            except OSError:
                return p                       # does not exist yet -> this is the one to write
            self._seg_n += 1

    def _rotate(self):
        """Bound the store by TOTAL size and segment count -- never as a side effect of one write.

        Deletion happens only while genuinely over budget, and the newest segment is never a
        candidate: an investigation reaches for what just happened.
        """
        files = self.files()
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
    def files(self):
        try:
            return sorted(os.path.join(self._journal_dir, f)
                          for f in os.listdir(self._journal_dir)
                          if f.startswith("wire-") and f.endswith(".jsonl"))
        except Exception:
            return []

    def read_all(self, limit: int = 0, agent: str = None):
        """`agent` scopes to one seat's records.

        Needed the moment a reader iterates a fleet: doctor examines every agent, so an unscoped
        read rendered the same finding 15 times -- one per agent -- which is noise dressed as
        signal. Scoping also pre-figures T157, where the journal shards per agent and this filter
        becomes a file selection rather than a scan.
        """
        rows = []
        for p in self.files():
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
