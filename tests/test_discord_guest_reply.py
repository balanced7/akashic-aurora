"""RED pins — the Discord guest reply path (the missing half of the guest tier).

LIVE DEFECT 2026-08-26, Daniil verbatim: "your discord integration is a little broken,
your reply never landed in the discord." Serge's guest "Hello all" reached the bus; Rill's
reply went to the bus and DIED there. The guest tier was built one-directional: admission
(attributed, authority none, heard) has no reply path back. These pins pre-register the
fix, mirroring the ladder's split: the PURE half (core/comm/discord_guest_reply.py) is
pinnable without a Discord import; the runner wires it beside the ladder.

CONTRACT UNDER TEST:
  - track(bus_id, channel_key) registers a guest's message (channel_key is the runner's
    own handle -- the pure half never touches Discord).
  - poll(msgs) returns POST ops: {channel_key, frm, text} for each seat message whose
    meta.reply_id matches a tracked guest bus id.
  - a reply to an UNtracked id produces nothing (a seat's ambient reply is not a guest post).
  - duplicate reply ids produce ONE op (idempotent -- a crash-redelivered reply must not
    double-post; the RB-26 law one plane up).
  - control kinds NEVER produce a post op, even tracked -- the guest tier's own posture on
    the way OUT: a visitor may be answered, never steered.
  - the reply text is attributed to the seat (frm) and clipped at 1900 chars (Discord's
    2000-char cap, the runner's existing clip discipline).
"""
import pytest

from core.comm import discord_guest_reply as G


def test_a_reply_to_a_tracked_guest_produces_one_post_op():
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    ops = t.poll([
        {"id": "r1", "frm": "dsh_agent", "kind": "reply",
         "meta": {"reply_id": "bus-guest-1"}, "text": "Hello Serge!"},
    ])
    assert ops == [{"channel_key": "chan-a", "frm": "dsh_agent", "text": "Hello Serge!"}]


def test_a_reply_to_an_untracked_id_posts_nothing():
    """A seat's ambient reply is not a guest post -- the tracker only follows the thread
    it was handed. Silence here is correct, not a miss."""
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    assert t.poll([{"id": "r1", "frm": "dsh_agent", "kind": "reply",
                    "meta": {"reply_id": "nobody"}, "text": "hi"}]) == []


def test_the_answers_link_form_posts_too():
    """The CLI's --answers stamps meta.answers; bus.send_reply stamps meta.reply_id.
    The tracker follows BOTH -- one seam for the ladder and the door, so a seat that
    answers the guest through the CLI still reaches the guest's channel."""
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    ops = t.poll([{"id": "r1", "frm": "dsh_agent", "kind": "reply",
                   "meta": {"answers": "bus-guest-1"}, "text": "Hello Serge!"}])
    assert ops == [{"channel_key": "chan-a", "frm": "dsh_agent", "text": "Hello Serge!"}]


def test_a_redelivered_reply_posts_once():
    """RB-26 one plane up: the runner's lane redelivers on crash; the post must be
    idempotent or Serge gets the same answer twice."""
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    msg = {"id": "r1", "frm": "dsh_agent", "kind": "reply",
           "meta": {"reply_id": "bus-guest-1"}, "text": "Hello Serge!"}
    assert len(t.poll([msg])) == 1
    assert t.poll([msg]) == []          # redelivered -- already posted


def test_a_control_kind_never_posts_even_when_tracked():
    """The guest tier's own law, applied to the way OUT: a visitor may be answered,
    never steered. A seat that replies with a control kind to a guest thread is refused
    by the tracker itself -- two locks on one door, the relay's rule."""
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    ops = t.poll([{"id": "c1", "frm": "dsh_agent", "kind": "nudge",
                   "meta": {"reply_id": "bus-guest-1"}, "text": "do this"}])
    assert ops == []


def test_reply_text_is_attributed_and_clipped():
    t = G.GuestReplyTracker()
    t.track("bus-guest-1", "chan-a")
    long = "x" * 5000
    ops = t.poll([{"id": "r1", "frm": "dsh_agent", "kind": "reply",
                   "meta": {"reply_id": "bus-guest-1"}, "text": long}])
    assert len(ops) == 1
    assert ops[0]["frm"] == "dsh_agent"
    assert len(ops[0]["text"]) <= 1900
