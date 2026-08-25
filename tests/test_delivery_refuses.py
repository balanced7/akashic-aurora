"""RED pins: the delivery layer must REFUSE, not report success on a non-delivery.

FOUR receipt-without-delivery failures in twelve hours, 2026-08-24/25, all mine, all while
shipping fixes for exactly this class:

  1. bifrost-send --to daniil  -> a ghost inbox (50 unread, no runner). Returned a message
     id for a word that reaches nobody. The UNATTENDED warning printed; I read past it to
     the id underneath.
  2. `discord send`            -> posted to the GLOBAL webhook, not Daniil's lane with this
     seat. He replied "your reply didn't go to the vandor chat".
  3. forward(msg with 'text')  -> render_parts reads msg['content'], so the body rendered
     EMPTY and the head posted alone. Simon: "getting empty responses here labeled reply".
     Three times.
  4. and then I told him it had landed, because no exception was raised -- from a function
     whose docstring says NEVER RAISES and which returns its verdict as a value I did not
     read.

THE COMMON SHAPE: every one reported on the CALL and not on the ARRIVAL. None was a
knowledge gap; in two cases the rule was on screen. So the fix is not another lesson. Each
of these should be a REFUSAL AT THE DOOR -- per the instrument-honesty capstone, a refusal
must name a specific condition to fire, while a confirmation can be produced by absence.

This file pins the two that live in core. The CLI-side refusals (an oversize --text that
gets read as a filename; a global-webhook default) are a second slice.

Written before the implementation (M3). RED on arrival.
"""
from __future__ import annotations

import pytest

from core.comm import discord_bridge as DB


def _sent(calls):
    """A post() double that records instead of posting, so every pin runs offline."""
    def _post(url, content):
        calls.append((url, content))
        return True
    return _post


# ------------------------------------------------- 1: an empty body is a REFUSAL
def test_an_empty_body_REFUSES_instead_of_posting_a_bare_header():
    """THE defect Simon hit. A post carrying only '**claude** `reply`' looks like a
    delivered answer and contains nothing -- indistinguishable, to the reader, from a
    delivery failure. It must never leave the house."""
    calls = []
    out = DB.forward({"frm": "claude", "kind": "reply", "content": ""},
                     url="https://example.invalid/hook", force=True, post=_sent(calls))
    assert not out.ok, f"an empty body must FAIL, got {out}"
    assert calls == [], "nothing may be posted for an empty body"


def test_the_refusal_NAMES_the_condition_so_the_caller_can_fix_it():
    """A refusal that says only 'failed' is the original silence with punctuation. This one
    must say the body was empty -- which is what would have told me, instantly, that I had
    passed 'text' where the renderer wanted 'content'."""
    out = DB.forward({"frm": "claude", "kind": "reply", "content": ""},
                     url="https://example.invalid/hook", force=True, post=_sent([]))
    assert "empty" in out.why.lower() or "no body" in out.why.lower(), out.why


def test_the_WRONG_FIELD_case_refuses_rather_than_posting_a_header():
    """The exact call I made three times: a bus-shaped dict whose body lives in 'text'.
    render_parts reads 'content', finds nothing, and used to post the head alone."""
    calls = []
    out = DB.forward({"frm": "claude", "kind": "reply", "text": "a real message body"},
                     url="https://example.invalid/hook", force=True, post=_sent(calls))
    assert not out.ok, f"a body in the wrong field must FAIL, got {out}"
    assert calls == [], "a headers-only post must never be sent"


def test_a_real_body_still_posts_normally():
    """Calibration: the refusal must not eat the working path, or it is not a guard, it is
    an outage."""
    calls = []
    out = DB.forward({"frm": "claude", "kind": "reply", "content": "a real body"},
                     url="https://example.invalid/hook", force=True, post=_sent(calls))
    assert out.ok and not out.partial, out
    assert len(calls) == 1 and "a real body" in calls[0][1]


def test_forward_still_NEVER_RAISES_on_a_refusal():
    """It is a listener on a substrate that must not care about it. A refusal is a returned
    verdict, never an exception into a bus caller."""
    for bad in ({}, {"frm": "claude"}, {"content": None}, {"content": "   "}):
        out = DB.forward(dict(bad, kind="reply"), url="https://example.invalid/hook",
                         force=True, post=_sent([]))
        assert not out.ok, bad


# ------------------------------- 2: 'ok' is not 'done' -- the house vocabulary
# T181: done = ok AND NOT partial | PARTIALLY = ok AND partial | failed = not ok.
# Lesson boundary_outcome_ok_includes_partial_double_strike: never test bare ok as done.
# I broke this myself all morning -- every delivery check I made was `ok=True`, which is
# the unsound test the lesson names. They happened to be partial=False, so nothing went
# wrong; the CHECK was still the one that lies.
def test_a_partial_delivery_is_not_reported_as_done():
    """A multi-part post where one part fails must NOT read as delivered. This is the pin
    that stops a two-chunk answer being half-sent and fully believed."""
    state = {"n": 0}

    def flaky(url, content):
        state["n"] += 1
        if state["n"] > 1:
            raise RuntimeError("second chunk rejected")
        return True

    body = "x" * (DB.DISCORD_MAX + 500)          # forces >1 part
    out = DB.forward({"frm": "claude", "kind": "reply", "content": body},
                     url="https://example.invalid/hook", force=True, post=flaky)
    assert not (out.ok and not out.partial), \
        f"a half-sent message must not read as done: {out}"


def test_the_house_vocabulary_is_expressible_from_the_outcome():
    """done / PARTIALLY / failed must each be derivable, so a caller branching
    failed -> partial -> done (in that order) can be written at all."""
    ok = DB.forward({"frm": "claude", "kind": "reply", "content": "body"},
                    url="https://example.invalid/hook", force=True, post=_sent([]))
    bad = DB.forward({"frm": "claude", "kind": "reply", "content": ""},
                     url="https://example.invalid/hook", force=True, post=_sent([]))
    assert (ok.ok and not ok.partial) is True, "the good path must render as done"
    assert (not bad.ok) is True, "the refusal must render as failed"


# ============================================================================
# GUARD C: `discord send` must not have a silent global-webhook default.
#
# 2026-08-25, Daniil: "Your reply didn't go to the vandor chat". agent_cli's discord
# command resolves url = DB.webhook_url() -- the GLOBAL channel -- while per-seat lanes
# exist and work (discord_feed.seat_channel_url), and the AUTOMATIC feed already routes
# operator-directed traffic to them. Only the MANUAL verb never learned.
#
# It printed "[discord] posted", which was true about the call and wrong about the
# arrival. The guard is not "remember to pass a lane" -- it is that the target is chosen
# BY CONSTRUCTION and any fallback is SAID OUT LOUD.
# ============================================================================
from core.comm import discord_feed as DF


def test_send_prefers_the_callers_own_seat_lane():
    """His lane with THIS seat is where he is reading. That must be the default, not an
    option I have to remember at 1am."""
    url, source, note = DF.send_target("claude", seat_url="https://lane/vandor",
                                       global_url="https://global/hook")
    assert url == "https://lane/vandor", (url, source)
    assert "lane" in source.lower() or "seat" in source.lower(), source


def test_a_fallback_to_global_is_ANNOUNCED_never_silent():
    """A silent fallback is how a reply ends up in the wrong room while the sender reads
    'posted'. If we cannot resolve the lane, the operator hears about it."""
    url, source, note = DF.send_target("claude", seat_url="",
                                       global_url="https://global/hook")
    assert url == "https://global/hook"
    assert note, "falling back to the global channel must produce a spoken note"
    assert "global" in note.lower(), note


def test_no_target_at_all_REFUSES_rather_than_returning_something_falsy_and_quiet():
    url, source, note = DF.send_target("claude", seat_url="", global_url="")
    assert not url
    assert note and ("not configured" in note.lower() or "no " in note.lower()), note


def test_the_happy_path_says_WHERE_it_is_going():
    """Yesterday's whole arc: a receipt must name what it proved. 'posted' is not a
    receipt if it cannot tell you which room."""
    _, source, _ = DF.send_target("claude", seat_url="https://lane/vandor",
                                  global_url="https://global/hook")
    assert source and source.strip(), "the target must be nameable in the receipt"
