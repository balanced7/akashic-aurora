"""T073 Phase 1+2 PRE-REGISTERED ACCEPTANCE -- incarnation addressing + wake allowlist.

Reconciled spec: research/reviewed/t073-wake-reconciliation-2026-07-15.md (deepseek
design half governs; ONE build refinement flagged for his verify): frm_incarnation-based
FILTERING needs session-identity plumbing every CLI subprocess lacks (a pid-scoped
default would make a session's own sends WAKE ITS OWN SEAT -- worse noise). So Phase 1
ships the robust half: `meta.to_incarnation` EXPLICIT addressing overrides the echo
skip (the sender always knows its target -- the [twin-sync] convention already names
session8s), while unaddressed same-agent mail keeps today's safe frm==agent skip.
frm_incarnation is STAMPED best-effort on every send (diagnostics + Phase 4's filter
once T072 lands the identity plumbing), never filtered on tonight.

Phase 2: WAKE_WORTHY allowlist inversion (deepseek L3) -- a new kind is silent by
default. DEVIATION from his six-kind list, flagged: `nudge` is added (the fidelity
ladder's barge-in MUST wake an idle seat; omitting it breaks bifrost-nudge for
sessions). A to_incarnation match wakes REGARDLESS of kind (explicit addressing is
explicit intent -- twin-sync pings ride kind=chat).

Run: py -m pytest tests/test_t073_wake_phase12.py -q
"""
import os
import sys
import uuid
from types import SimpleNamespace

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MY = "f9207c90"


def _m(kind="handoff", frm="deepseek", to="claude", meta=None):
    return SimpleNamespace(kind=kind, frm=frm, to=to, meta=meta or {},
                           id="1-0", content="x")


def _worthy(m, agent="claude", incarnation=MY):
    from scripts.bifrost_wake import wake_worthy
    return wake_worthy(m, agent=agent, incarnation=incarnation)


def test_p1_directed_incarnation_mail_wakes_through_the_echo_skip():
    twin = _m(kind="chat", frm="claude", meta={"to_incarnation": MY})
    assert _worthy(twin), "twin mail addressed to MY incarnation must wake me (frm==agent notwithstanding)"


def test_p2_unaddressed_same_agent_mail_still_skipped():
    echo = _m(kind="handoff", frm="claude")
    assert not _worthy(echo), "unaddressed same-agent mail keeps the safe echo skip"


def test_p3_cross_agent_mail_delivered():
    assert _worthy(_m(kind="handoff", frm="deepseek"))
    assert _worthy(_m(kind="request", frm="cursor"))


def test_p4_unknown_kind_silent_by_default():
    assert not _worthy(_m(kind="zz_test", frm="deepseek")), \
        "a NEW kind must be silent until explicitly allowlisted (the ratchet)"
    assert not _worthy(_m(kind="trace", frm="deepseek"))
    assert not _worthy(_m(kind="status", frm="deepseek"))


def test_p5_wake_worthy_kinds_deliver_including_nudge():
    for kind in ("request", "handoff", "reply", "blocker", "question", "completion", "nudge"):
        assert _worthy(_m(kind=kind, frm="deepseek")), f"{kind} must wake an idle seat"


def test_p5b_broadcast_reply_still_room_chatter():
    assert not _worthy(_m(kind="reply", frm="deepseek", to="*")), \
        "broadcast replies never wake (deepseek red-team F5 preserved)"


def test_p11_other_incarnations_mail_skipped():
    other = _m(kind="chat", frm="claude", meta={"to_incarnation": "b0b7771d"})
    assert not _worthy(other), "mail addressed to ANOTHER incarnation must not wake me"


def test_p10_sends_stamp_frm_incarnation():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    if connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                       timeout_seconds=3, decode_responses=True) is None:
        pytest.skip("redis not available")
    import json
    from core.comm.bus import Bus
    ns = f"bifrost_t073_{uuid.uuid4().hex[:8]}"
    b = Bus("deepseek", namespace=ns)
    b.send("claude", "handoff", "take this")
    b.send_reply("claude", "the answer")
    for eid, fields in b._client.xrange(f"{ns}:work:inbox:claude") + \
                       b._client.xrange(f"{ns}:inbox:claude"):
        meta = json.loads(dict(fields).get("meta", "{}"))
        assert meta.get("frm_incarnation"), "every send stamps its incarnation (best-effort id)"


def test_to_incarnation_flag_reaches_meta():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    if connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                       timeout_seconds=3, decode_responses=True) is None:
        pytest.skip("redis not available")
    import json
    from core.comm.bus import Bus
    ns = f"bifrost_t073_{uuid.uuid4().hex[:8]}"
    b = Bus("claude", namespace=ns)
    b.send("claude", "chat", "[twin-sync] ping", meta={"to_incarnation": "b0b7771d"})
    eid, fields = b._client.xrange(f"{ns}:inbox:claude")[0]
    meta = json.loads(dict(fields).get("meta", "{}"))
    assert meta.get("to_incarnation") == "b0b7771d"


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t073_wake_phase12.py -q")


# ---------------------------------------------------------------- operator override (2026-07-15)
def test_operator_sender_wakes_regardless_of_kind(monkeypatch):
    """THE OPERATOR OUTRANKS THE ALLOWLIST -- live incident 2026-07-15: Daniel's
    broadcast (frm=user, kind=inform, the ladder's quiet tier) slept every idle
    claude seat while the always-consuming runner answered. A sender dimension,
    not a kind: the ratchet's silent-by-default law for agent kinds stands."""
    import scripts.bifrost_wake as bw
    from types import SimpleNamespace
    m = SimpleNamespace(kind="inform", frm="user", to="*", meta={})
    assert bw.wake_worthy(m, agent="claude", incarnation="sess0000"), \
        "operator inform must wake"
    m2 = SimpleNamespace(kind="chat", frm="daniel", to="claude", meta={})
    assert bw.wake_worthy(m2, agent="claude", incarnation="sess0000"), \
        "operator chat must wake"
    m3 = SimpleNamespace(kind="inform", frm="deepseek", to="*", meta={})
    assert not bw.wake_worthy(m3, agent="claude", incarnation="sess0000"), \
        "agent inform stays quiet (the ratchet is untouched)"
    monkeypatch.setenv("AKASHIC_OPERATOR_IDS", "")
    assert not bw.wake_worthy(m, agent="claude", incarnation="sess0000"), \
        "empty operator set disables the override (drill hatch)"
