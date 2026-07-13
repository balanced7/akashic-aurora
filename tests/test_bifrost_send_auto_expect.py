"""
Regression pin for the send-side half of the 2026-07-12 silent-handoff fix: directed ASKS
(request/handoff/question) must AUTO-arm a reply-deadline so a dropped ask surfaces itself
(expectation_dead at boot/bifrost-sync) instead of vanishing to a dead peer -- the exact trap that
hid deepseek's death for hours. Explicit `--expect-reply-within 0` opts out; non-ask kinds never arm.

Complements the receiver-side pin (test_doctor_dead_runner_visibility): together they close the
silent-handoff class from both ends.
"""
from types import SimpleNamespace

import pytest

import agent_cli
from core.comm import expectations


def _client():
    return expectations._client()


pytestmark = pytest.mark.skipif(_client() is None, reason="bus/Redis offline")


def _args(**kw):
    base = dict(agent_id="ztestpin-snd", to="ztestpin-rcp", kind="request", text=["ping"],
                broadcast=False, expect_reply_within=-1, json=False)
    base.update(kw)
    return SimpleNamespace(**base)


def _armed(agent):
    c = _client()
    return len(c.hgetall(expectations._key(agent)) or {})


def _wipe():
    c = _client()
    for k in (c.keys("bifrost:*ztestpin*") or []):
        c.delete(k)


def test_directed_ask_auto_arms_and_optout_and_nonask():
    try:
        _wipe()
        # 1) directed ask, no flag (expect_reply_within=-1 UNSET) -> AUTO-arms
        agent_cli.cmd_bifrost_send(_args(agent_id="ztestpin-a", kind="request"))
        assert _armed("ztestpin-a") == 1, "a directed ask must auto-arm a reply-deadline"

        # 2) explicit 0 -> opt out, no expectation
        agent_cli.cmd_bifrost_send(_args(agent_id="ztestpin-b", kind="handoff", expect_reply_within=0))
        assert _armed("ztestpin-b") == 0, "explicit --expect-reply-within 0 must opt out"

        # 3) non-ask kind (chat) unset -> never arms
        agent_cli.cmd_bifrost_send(_args(agent_id="ztestpin-c", kind="chat"))
        assert _armed("ztestpin-c") == 0, "a non-ask kind must not auto-arm"
    finally:
        _wipe()
