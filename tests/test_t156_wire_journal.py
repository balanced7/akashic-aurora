"""PRE-REGISTERED ACCEPTANCE (T156 WIRE-A) -- the API wire journal, capture + dissect slice.

Daniil, 2026-08-04: "I want us to use the same kind of forensics that wireshark has as well as
enterprise security appliances with deep packet sniffing" / "lets build it, this will serve as a
strong foundation as well as be a good place for our security eyes when we get them".

WHY THIS EXISTS, measured not assumed. deepseek reverse-engineered its own runner at runtime
(research/in-flight/api-wire-reverse-engineering-deepseek-2026-08-04.md) and counted the delta
between what the provider sends and what we keep: usage 5 of 9 fields read, chunk 1 of 7,
HTTP headers 0 of 8, finish_reason 0 of 1, timing 0 of n. Capturing the rest costs ZERO extra
API calls -- every field is already in our process. The gap is not measurement; it is that
nobody writes it down.

TWO SCOPE DECISIONS ENCODED AS PINS, both deliberate:

  METADATA ONLY. No prompt or response BODIES. Bodies are the most sensitive bytes we produce,
  and a capture system that stores them needs redaction to exist first. Prefix HASHES give the
  cache forensics without storing a single byte of content, so this slice ships without a DLP
  dependency rather than waiting on one. (W2 pins the absence.)

  THE READER SHIPS WITH THE WRITER. core/coord/cognitive_metrics.py is the standing warning:
  five runners faithfully feed an accumulator that nothing in production reads, so 9 of 16
  fields can only ever render 0. A journal without a reader is that defect rebuilt. (W6.)

  W1  the transport records one entry per HTTP round trip -- so an SDK retry, which hides
      INSIDE a single create() call, appears as the separate event it really is
  W2  no request or response BODY is ever written -- only metadata and hashes
  W3  the discarded high-value fields are captured: system_fingerprint (silent model swap),
      finish_reason, total_tokens, reasoning_tokens, service_tier
  W4  FAIL-OPEN for the caller: a recorder that throws must never take a runner down
  W5  ...but a skipped capture is COUNTED, never silent -- an uncounted drop is a measured zero
  W6  a READER exists and summarizes the journal (the anti-T140 pin)
  W7  the reader distinguishes MEASURED from UNKNOWN -- a field the provider never sent must
      not render as 0 (T141 vocabulary, and the law this project keeps relearning)

Run: py -m pytest tests/test_t156_wire_journal.py -q
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _journal(tmp_path):
    from scripts.wire_journal import WireJournal
    return WireJournal(journal_dir=str(tmp_path))


def test_w1_one_record_per_http_round_trip(tmp_path):
    """A retry inside one create() call must surface as two records, not one.

    This is the whole reason capture sits at the transport rather than around the call: at the
    call site three round trips look like one request that took a while."""
    j = _journal(tmp_path)
    j.record(model="deepseek-chat", status=429, attempt=0)
    j.record(model="deepseek-chat", status=200, attempt=1)
    rows = j.read_all()
    assert len(rows) == 2, f"expected one record per round trip, got {len(rows)}"
    assert [r.get("attempt") for r in rows] == [0, 1]


def test_w2_no_bodies_are_ever_written(tmp_path):
    """The privacy pin. Hand the recorder a body and a prompt; neither may reach disk."""
    j = _journal(tmp_path)
    secret = "SUPER-SECRET-PROMPT-CONTENT-9e1f"
    j.record(model="m", status=200, prompt_text=secret, response_text=secret)
    raw = "".join(open(p, encoding="utf-8").read() for p in j.files())
    assert secret not in raw, "a request/response BODY reached the journal -- metadata only"
    rows = j.read_all()
    assert rows and rows[0].get("prompt_sha"), "a prefix HASH must still be recorded for cache forensics"
    assert secret not in json.dumps(rows), "body leaked into a parsed field"


def test_w3_the_discarded_fields_are_captured(tmp_path):
    """The fields deepseek measured as arriving-and-discarded."""
    j = _journal(tmp_path)
    j.record(model="deepseek-chat", status=200,
             system_fingerprint="fp_abc123", finish_reason="length",
             usage={"total_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 800}},
             service_tier="default")
    r = j.read_all()[0]
    assert r["system_fingerprint"] == "fp_abc123", "silent-model-swap detector not captured"
    assert r["finish_reason"] == "length"
    assert r["total_tokens"] == 900
    assert r["reasoning_tokens"] == 800, "reasoning_tokens diagnoses 'thought itself out of an answer'"
    assert r["service_tier"] == "default"


def test_w4_the_recorder_never_takes_the_caller_down(tmp_path):
    """Point the journal at an unwritable location; record() must swallow, not raise."""
    j = _journal(tmp_path)
    j._journal_dir = "\x00::not-a-writable-path::"     # force the write to fail
    j.record(model="m", status=200)                     # must not raise


def test_w5_a_skipped_capture_is_counted(tmp_path):
    """Fail-open is only honest if the failures are visible. A silent drop is a measured zero."""
    j = _journal(tmp_path)
    j._journal_dir = "\x00::not-a-writable-path::"
    j.record(model="m", status=200)
    assert j.dropped >= 1, "a failed capture must increment a drop counter, never vanish"


def test_w6_a_reader_exists_and_summarizes(tmp_path):
    """The anti-T140 pin: the writer does not ship without a reader."""
    j = _journal(tmp_path)
    j.record(model="deepseek-chat", status=200, finish_reason="stop",
             usage={"total_tokens": 10}, system_fingerprint="fp_1")
    j.record(model="deepseek-chat", status=200, finish_reason="length",
             usage={"total_tokens": 20}, system_fingerprint="fp_2")
    s = j.summarize()
    assert s["records"] == 2
    assert s["truncated"] == 1, "finish_reason=length is the truncation diagnostic"
    assert len(s["fingerprints"]) == 2, "a fingerprint CHANGE is the silent-model-swap signal"


def test_w7_unknown_is_not_zero(tmp_path):
    """A field the provider never sent must render UNKNOWN, not 0 -- the cognitive_metrics
    hazard, refused by construction rather than by discipline."""
    j = _journal(tmp_path)
    j.record(model="m", status=200)                     # no usage at all
    s = j.summarize()
    assert s["reasoning_tokens"] == "UNKNOWN", \
        f"an unsent field must be UNKNOWN, got {s['reasoning_tokens']!r} -- a measured zero is a lie"
