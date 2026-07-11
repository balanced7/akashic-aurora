"""
T030 L4 / RB-29 -- sender-side deadline + redrive: pre-registered acceptance
(committed BEFORE impl, M3/T031). Spec: docs/agent-liveness-tier-2026-07.md L4 BUILD
SPEC (claude concretization of the adopted deepseek half; deepseek design-review gates
impl).

Contract frozen here:
  core.comm.expectations.arm(sender, orig_id, to, kind, content, within_s) -> bool
      (clamp within_s >= 30; records anchor = recipient-reply stream tail AT ARM TIME,
       so a reply CONSUMED before the sweep still clears -- stream entries outlive
       cursor consumption)
  core.comm.expectations.sweep(sender, now=None) -> {"redriven": [...], "dead": [...],
      "cleared": [...]}   (now injectable: pins never sleep)
  core.comm.expectations.REDRIVES == 3
  redrive copy carries meta {redrive_of: orig_id, attempt: n}
  exhaustion emits a durable event kind='expectation_dead' (spied here, not written)
  linked reply (meta answers=orig_id) clears EXACTLY its expectation; an unlinked reply
      from the recipient clears the OLDEST for that recipient (FIFO fallback)
  doors: bifrost-send --expect-reply-within (CLI) + sweep wired into bifrost-sync/boot

Run: py -m pytest tests/test_t030_l4_expectations.py -q
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.comm import expectations
    from core.comm.bus import Bus
    _BUILT = hasattr(expectations, "arm") and hasattr(expectations, "sweep")
except ImportError:
    expectations = Bus = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("rb29-probe").online)
except Exception:
    _ONLINE = False

pytestmark = [
    pytest.mark.skipif(not _BUILT, reason="L4 pins pre-registered; impl pending (assertions frozen)"),
    pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline"),
]


@pytest.fixture()
def pair():
    """(sender, recipient) with teardown of every touched key. Both cursors park at the
    live broadcast tail (harness-only, the RB-21 _quiesce lesson: a live runner's trace
    backlog must not leak into pin reads; gen-0 commit valid on never-fenced agents)."""
    s = f"rb29snd-{uuid.uuid4().hex[:8]}"
    r = f"rb29rcv-{uuid.uuid4().hex[:8]}"
    for aid in (s, r):
        b = Bus(aid)
        b.advance_to(bc=b.tail().get("bc"), generation=0)
    yield s, r
    try:
        c = Bus(s)._client
        for k in (f"bifrost:expect:{s}", f"bifrost:inbox:{s}", f"bifrost:inbox:{r}",
                  f"bifrost:cursor:{s}", f"bifrost:cursor:{r}",
                  f"bifrost:presence:{s}", f"bifrost:presence:{r}"):
            c.delete(k)
    except Exception:
        pass


def _arm(s, r, within=60, content="answer me"):
    orig = Bus(s).send(r, "request", content)
    assert orig
    assert expectations.arm(s, orig, r, "request", content, within)
    return orig


# --- P1: arm records; sub-minimum deadlines clamp to >= 30s ---

def test_arm_records_and_clamps(pair):
    s, r = pair
    t0 = time.time()
    _arm(s, r, within=5)
    res = expectations.sweep(s, now=t0 + 29)
    assert res["redriven"] == [] and res["dead"] == [], \
        "within=5 clamped to 30 -- nothing fires before the floor"


# --- P2: a sweep before the deadline is a no-op ---

def test_sweep_before_deadline_noop(pair):
    s, r = pair
    t0 = time.time()
    _arm(s, r, within=60)
    res = expectations.sweep(s, now=t0 + 10)
    assert res["redriven"] == [] and res["dead"] == [] and res["cleared"] == []


# --- P3: past deadline -> ONE redrive copy with linkage meta, budget decremented ---

def test_redrive_past_deadline(pair):
    s, r = pair
    t0 = time.time()
    orig = _arm(s, r, within=60)
    res = expectations.sweep(s, now=t0 + 61)
    assert res["redriven"] == [orig]
    copies = [m for m in Bus(r).inbox(limit=50, advance=False)
              if (m.meta or {}).get("redrive_of") == orig]
    assert len(copies) == 1 and copies[0].meta.get("attempt") == 1
    res2 = expectations.sweep(s, now=t0 + 61)
    assert res2["redriven"] == [], "same sweep moment never double-fires (fresh deadline)"


# --- P4: exhaustion after REDRIVES -> durable expectation_dead + record gone ---

def test_exhaustion_emits_dead_event(pair, monkeypatch):
    s, r = pair
    seen = []
    monkeypatch.setattr(expectations, "_emit_dead",
                        lambda *a, **k: seen.append((a, k)))
    t0 = time.time()
    orig = _arm(s, r, within=60)
    now = t0 + 61
    for i in range(expectations.REDRIVES):
        assert expectations.sweep(s, now=now)["redriven"] == [orig]
        now += 3600
    res = expectations.sweep(s, now=now)
    assert res["dead"] == [orig] and len(seen) == 1
    assert expectations.sweep(s, now=now + 3600)["dead"] == [], "record deleted after death"
    assert expectations.REDRIVES == 3


# --- P5: a LINKED reply clears exactly its expectation; unlinked clears FIFO;
#         a reply CONSUMED before the sweep still clears (anchor beats cursor) ---

def test_linked_reply_clears_exactly_and_survives_consumption(pair):
    s, r = pair
    t0 = time.time()
    first = _arm(s, r, within=60, content="q-first")
    second = _arm(s, r, within=60, content="q-second")
    Bus(r).send(s, "reply", "answering the SECOND", meta={"answers": second})
    Bus(s).inbox(limit=50, advance=True)          # sender READS its mail before sweeping
    res = expectations.sweep(s, now=t0 + 10)
    assert res["cleared"] == [second], "exact linkage; consumption cannot hide the reply"
    Bus(r).send(s, "reply", "unlinked answer")
    res2 = expectations.sweep(s, now=t0 + 12)
    assert res2["cleared"] == [first], "unlinked reply clears the OLDEST (FIFO fallback)"


# --- P7 (post-incident registration, 2026-07-11: the T030 gate ask's own 600s runner
#     TIMEOUT reply cleared the expectation guarding it -- a non-answer masquerading as
#     the answer; that live incident is this pin's RED): non-answers never clear ---

def test_nonanswer_note_does_not_clear(pair):
    s, r = pair
    t0 = time.time()
    orig = _arm(s, r, within=60)
    Bus(r).send(s, "note", "(runner timed out -- api call abandoned)")
    res = expectations.sweep(s, now=t0 + 10)
    assert res["cleared"] == [], \
        "kind=note is a NON-answer: the expectation stays armed and the redrive will fire"


def test_runner_sends_nonanswers_as_notes():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "scripts", "bifrost_runner_deepseek.py"),
               encoding="utf-8").read()
    assert 'reply_kind = "note" if nonanswer else "reply"' in src, \
        "timeout/error outcomes ship as kind=note without the answers link (T026 doctrine)"


# --- P6: the doors are wired (built != wired) ---

def test_doors_wired():
    cli = open(os.path.join(_ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert "--expect-reply-within" in cli, "bifrost-send grew the flag"
    assert "sweep" in open(os.path.join(_ROOT, "agent", "bifrost_pull.py"),
                           encoding="utf-8").read(), \
        "the pull floor (bifrost-sync/boot) sweeps expectations at render"
