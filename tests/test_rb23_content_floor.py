"""
RB-23 -- the content floor: a persistent no-content stall is CAUGHT (confessed), never
shipped as done. Pre-registered acceptance, committed BEFORE the implementation (M3 /
T031 hook 2). Spec: docs/rb23-build-spec-2026-07-11.md (dual-half, reconciled).

Bar (slice text, docs/resilience-battery-slices-2026-07.md RB-23): two successive empty
promises are caught; the labeled endings corpus meets its precision/recall bound.

Contract under test (spec section "Reconciled design"):
  content_floor_check(answer, resend, agent_id, promise_bounce_fired, pulse) -> str
  promise_shaped_runner(text) -> excerpt | None     (bounce_promise's detector, exposed pure)
  stall_reason(text) -> 'empty' | 'marker' | None   (first-position hard floor classifier)
  FLOOR_CHARS = 15, gate resend budget = 1 (global ceiling 2 with bounce_promise's one).

Run: py -m pytest tests/test_rb23_content_floor.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from scripts.bifrost_runner_deepseek import (  # noqa: E402
    FLOOR_CHARS,
    MARKER_PATTERN,
    content_floor_check,
    promise_shaped_runner,
    stall_reason,
)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
HELD_OUT_SEAL_LIFTED = True    # lifted 2026-07-11 ~03:35: ds-41..60 arrived via the durable
                               # note door (rb23-heldout-corpus-sealed), extracted blind

# Bounds -- RECONCILED with deepseek's (e) table (blind-half record, stricter wins per axis):
# his stall 0.98/0.97, promise 0.90/0.80, outcome 0.95/0.95 vs claude's combined-precision
# 0.95 / en-promise recall 0.80 / stall recall 1.0.
BOUND_PRECISION = 0.95           # combined would-act precision (claude, covers his per-class floors)
BOUND_PROMISE_RECALL = 0.80      # equal in both halves; graded on lang=en rows (named deferral)
BOUND_STALL_RECALL = 1.0         # claude, stricter than his 0.97, on empty|marker forms
BOUND_OUTCOME_SHIP_RATE = 0.95   # deepseek outcome recall: legit outcomes shipped untouched


class FakeSend:
    def __init__(self, replies=None, boom=False):
        self.calls, self.boom = [], boom
        self.replies = list(replies or [])

    def __call__(self, prompt):
        self.calls.append(prompt)
        if self.boom:
            raise RuntimeError("api down")
        return self.replies.pop(0) if self.replies else ""


class PulseRec:
    def __init__(self):
        self.calls = []

    def __call__(self, agent, reason, **kw):
        self.calls.append((agent, reason))


MARKERS = [
    "(deepseek produced no final answer)",
    "(deepseek returned an empty reply)",
    "(deepseek runner error: ConnectionError: boom)",
    "(deepseek agentic runner error: ToolExecutionError: denied)",
    "(claude produced no final answer)",                       # agent-generalized class
    "(deepseek runner timed out after 300s -- the API call was abandoned to keep the runner alive)",
    "(deepseek runner: no result)",
]


# --- (1) the slice's named acceptance: successive empties confess, marker never ships bare ---

def test_two_successive_empties_confess_and_pulse():
    resend, pulse = FakeSend(replies=[""]), PulseRec()
    out = content_floor_check("", resend, agent_id="deepseek",
                              promise_bounce_fired=False, pulse=pulse)
    assert out.startswith("(deepseek --"), "a confession, in-band, first person"
    assert "no substantive reply" in out and "empty" in out
    assert not MARKER_PATTERN.match(out), "the confession is NOT another bare marker"
    assert len(resend.calls) == 1, "exactly one paid gate resend"
    assert pulse.calls and "content_floor_exhausted" in pulse.calls[0][1]


# --- (2) every marker class bounces once and a real recovery ships ---

@pytest.mark.parametrize("marker", MARKERS)
def test_marker_classes_bounce_once_and_recover(marker):
    assert MARKER_PATTERN.match(marker), "pattern must cover the whole marker class"
    resend, pulse = FakeSend(replies=["Recovered: the full deliverable, in detail."]), PulseRec()
    out = content_floor_check(marker, resend, agent_id="deepseek",
                              promise_bounce_fired=False, pulse=pulse)
    assert out == "Recovered: the full deliverable, in detail."
    assert len(resend.calls) == 1 and pulse.calls == []


# --- (3) short legit outcomes at FIRST reply are untouched (precision first) ---

@pytest.mark.parametrize("short_outcome", ["done, 3 tests green", "Done", "OK"])
def test_short_outcome_first_reply_untouched(short_outcome):
    resend, pulse = FakeSend(), PulseRec()
    out = content_floor_check(short_outcome, resend, agent_id="deepseek",
                              promise_bounce_fired=False, pulse=pulse)
    assert out == short_outcome
    assert resend.calls == [] and pulse.calls == []


# --- (4) promise -> bounce -> promise -> Tier-2 reprompt -> promise -> confession ---

def test_successive_promise_confesses():
    resend, pulse = FakeSend(replies=["I'll do it right after this, promise."]), PulseRec()
    out = content_floor_check("I'll get right on that.", resend, agent_id="deepseek",
                              promise_bounce_fired=True, pulse=pulse)
    assert out.startswith("(deepseek --") and "promise-again" in out
    assert len(resend.calls) == 1
    assert "final word" in resend.calls[0].lower() or "deliver" in resend.calls[0].lower()
    assert pulse.calls, "a confessed stall pulses the liveness lane"


# --- (5) cross-kind chain: promise bounce already spent, empty re-reply -> Tier-1 catch ---

def test_promise_bounce_then_empty_tier1_catch():
    resend, pulse = FakeSend(replies=["  \n "]), PulseRec()
    out = content_floor_check("", resend, agent_id="deepseek",
                              promise_bounce_fired=True, pulse=pulse)
    assert out.startswith("(deepseek --") and "empty" in out
    assert len(resend.calls) == 1, "gate budget is ONE regardless of what bounce_promise spent"


# --- (6) resend ceiling: the gate never pays twice ---

def test_gate_budget_is_single_resend():
    resend, pulse = FakeSend(replies=["(deepseek produced no final answer)"]), PulseRec()
    out = content_floor_check("", resend, agent_id="deepseek",
                              promise_bounce_fired=False, pulse=pulse)
    assert len(resend.calls) == 1, "empty -> resend -> marker must NOT buy a second resend"
    assert out.startswith("(deepseek --"), "still below floor -> confession"


# --- (7) Tier-3 is SOFT: post-bounce short text ships, never confesses ---

def test_tier3_short_post_bounce_ships_no_confession():
    resend, pulse = FakeSend(replies=["ok again"]), PulseRec()
    out = content_floor_check("ok", resend, agent_id="deepseek",
                              promise_bounce_fired=True, pulse=pulse)
    assert out in ("ok again", "ok"), "short is soft: whatever came back ships"
    assert not out.startswith("(deepseek --") and pulse.calls == []


def test_tier3_empty_resend_falls_back_to_original_short():
    resend, pulse = FakeSend(replies=[""]), PulseRec()
    out = content_floor_check("ok", resend, agent_id="deepseek",
                              promise_bounce_fired=True, pulse=pulse)
    assert out == "ok", "soft tier fails open to the short original, no confession"
    assert pulse.calls == []


def test_tier3_never_fires_without_a_prior_bounce():
    resend, pulse = FakeSend(), PulseRec()
    out = content_floor_check("ok", resend, agent_id="deepseek",
                              promise_bounce_fired=False, pulse=pulse)
    assert out == "ok" and resend.calls == []


# --- (8) resend exception: hard reasons fail CLOSED to confession, never the bare marker ---

def test_resend_exception_confesses_not_marker():
    resend, pulse = FakeSend(boom=True), PulseRec()
    out = content_floor_check("(deepseek produced no final answer)", resend,
                              agent_id="deepseek", promise_bounce_fired=False, pulse=pulse)
    assert out.startswith("(deepseek --"), "fail-closed: confession, not the marker"
    assert pulse.calls and "content_floor_failed" in pulse.calls[0][1], \
        "broken resend channel pulses 'failed', not 'exhausted' (deepseek caught-table)"


# --- (9) corpus harness: position-aware grading against BOTH fixture halves ---

def _load(path):
    rows, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                bad += 1
    return rows, bad


def _grade(rows):
    """Returns (would_act_true_pos, would_act_false_pos, promise_hits, promise_total,
    stall_hits, stall_total, outcome_total) under the spec's position rules."""
    tp = fp = p_hit = p_tot = s_hit = s_tot = o_tot = 0
    for r in rows:
        text, label, form = r["text"], r["label"], r.get("form", "prose")
        fires_first = bool(promise_shaped_runner(text) or stall_reason(text))
        if label == "promise":
            # Promise RECALL is graded on lang=en rows only: the v1 detector is an
            # English-opener net BY DESIGN (spec: non-en promise coverage is a named
            # deferral). Non-en promise rows still count toward precision if they fire,
            # and non-en OUTCOME rows stay in the pool as false-positive guards.
            if r.get("lang", "en") == "en":
                p_tot += 1
                if promise_shaped_runner(text):
                    p_hit += 1
            if fires_first:
                tp += 1
        elif label == "outcome":
            o_tot += 1
            if fires_first:
                fp += 1
        elif label == "stall":
            if form in ("empty", "marker"):
                s_tot += 1
                if stall_reason(text):
                    s_hit += 1
                    tp += 1
            else:
                # prose stalls are Tier-3 material: post-bounce, soft, never confessed.
                assert stall_reason(text) is None, "prose stall must not hard-fire: " + r["id"]
                assert len(text.strip()) < FLOOR_CHARS, "tier-3 candidacy: " + r["id"]
    return tp, fp, p_hit, p_tot, s_hit, s_tot, o_tot


def test_corpus_dev_half_meets_bounds():
    cl, cl_bad = _load(os.path.join(FIXTURES, "rb23_endings_claude.jsonl"))
    ds, ds_bad = _load(os.path.join(FIXTURES, "rb23_endings_deepseek.jsonl"))
    assert cl_bad == 0
    assert ds_bad <= 1, "ds-27 arrived clipped; the fresh sealed batch supersedes it"
    rows = cl + ds   # ds-01..27 reclassified DEV after the seal incident (spec, M8 record)
    tp, fp, p_hit, p_tot, s_hit, s_tot, o_tot = _grade(rows)
    assert s_tot and s_hit == s_tot, "stall recall on empty|marker forms must be 1.0"
    assert p_tot and p_hit / p_tot >= BOUND_PROMISE_RECALL
    assert tp and tp / (tp + fp) >= BOUND_PRECISION
    assert o_tot and (o_tot - fp) / o_tot >= BOUND_OUTCOME_SHIP_RATE


@pytest.mark.skipif(not HELD_OUT_SEAL_LIFTED,
                    reason="held-out seal not lifted: deepseek fresh sealed batch (ds-41+) "
                           "pending; required green at [verify]")
def test_corpus_held_out_meets_bounds():
    held, bad = _load(os.path.join(FIXTURES, "rb23_endings_deepseek_heldout.jsonl"))
    assert bad == 0 and held
    tp, fp, p_hit, p_tot, s_hit, s_tot, o_tot = _grade(held)
    assert s_hit == s_tot
    assert p_hit / p_tot >= BOUND_PROMISE_RECALL
    assert tp / (tp + fp) >= BOUND_PRECISION
    assert o_tot and (o_tot - fp) / o_tot >= BOUND_OUTCOME_SHIP_RATE
