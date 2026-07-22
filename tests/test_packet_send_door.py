"""T043 -- packet send-door hardening. The 10 pre-registered acceptance pins + the
3-receipt replay drill, from docs/packet-spec-v1-2026-07.md RIDING BUILD (LAW).

Reconciled build spec: research/reviewed/t043-build-plan-reconciliation-2026-07-13.md
(fenced dual: claude + deepseek, blind). The pins were committed IN the LAW spec BEFORE
this implementation (M3 pre-registration).

Contract proven here: a packet either arrives WHOLE and integrity-verified, or it is
REFUSED / DROPPED / TIMED-OUT *loudly* -- never silently clipped, corrupted, or partially
delivered. Redis-backed pins use the real Redis in a throwaway namespace (skip if down);
pure pins need no Redis.

Run: py -m pytest tests/test_packet_send_door.py -q   (or: py tests/test_packet_send_door.py)
"""
import io
import os
import sys
import time
import uuid
from contextlib import redirect_stderr

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")   # keep integrity events off the canonical firehose
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import packet_spec as ps
from core.comm.bus import Bus


# --------------------------------------------------------------------------- helpers
def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns():
    return f"bifrost_t043_{uuid.uuid4().hex[:8]}"


def _cleanup(client, ns):
    keys = client.keys(f"{ns}:*")
    if keys:
        client.delete(*keys)


def _bus(aid, c, ns):
    return Bus(aid, c, namespace=ns, promote=False)


def _reset_dials():
    for k in ("BUS_MAX_MESSAGE_BYTES", "PACKET_INTEGRITY_ENABLED", "FRAG_REASSEMBLY_TTL"):
        os.environ.pop(k, None)


# ============================================================== PIN 1: MTU bounds triple
def test_pin1_mtu_bounds_triple_and_refuse_loud():
    _reset_dials()
    # exact boundary (65535 ok / 65536 ok / 65537 REFUSED) -- the pure gate
    assert ps.within_mtu(65535) and ps.within_mtu(65536)
    assert not ps.within_mtu(65537)
    # teaching text is exact + loud
    text = ps.mtu_refusal_text(65537)
    assert "REFUSED" in text and "65537B" in text and "65536B" in text and "never truncated" in text
    # the door refuses loud (None) and writes NOTHING (stream tail unchanged) -- never truncates,
    # WHEN allow_frag is explicitly False. The DEFAULT (P2 auto-chunk) fragments oversize.
    c, ns = _client(), _ns()
    try:
        a = _bus("a", c, ns)
        b = _bus("b", c, ns)
        oversize = "z" * 200_000
        tail_before = c.xlen(f"{ns}:inbox:b") if c.exists(f"{ns}:inbox:b") else 0
        buf = io.StringIO()
        with redirect_stderr(buf):
            mid = a.send("b", "chat", oversize, allow_frag=False)
        assert mid is None, "oversize send with allow_frag=False must REFUSE (None), not truncate"
        tail_after = c.xlen(f"{ns}:inbox:b") if c.exists(f"{ns}:inbox:b") else 0
        assert tail_after == tail_before, "refused send must write nothing to the stream"
        assert "REFUSED" in buf.getvalue() and "never truncated" in buf.getvalue()
        assert b.inbox() == [], "nothing delivered"
        # P2 auto-chunk: default (no explicit allow_frag) fragments oversize, reassembles whole
        mid2 = a.send("b", "chat", oversize)
        assert mid2, "P2 default auto-frag must send (not refuse)"
        got = b.inbox()
        assert got and got[0].content == oversize, "P2 auto-frag must round-trip byte-identical"
    finally:
        _cleanup(c, ns)


# ============================================================== PIN 2: len catches truncation
def test_pin2_len_catches_truncation():
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        a = _bus("a", c, ns)
        b = _bus("b", c, ns)
        # stamp a legit envelope, then TAMPER: shorten content but keep the stamped len/sha
        env = {"frm": "a", "to": "b", "kind": "chat",
               "content": '"the full original body here padded padded padded"',
               "ts": "2026-07-13T00:00:00Z", "meta": "{}", "parts": "[]"}
        ps.stamp(env)
        env["content"] = '"short"'                          # truncated on the wire, len now lies
        c.xadd(f"{ns}:inbox:b", env)
        buf = io.StringIO()
        with redirect_stderr(buf):
            got = b.inbox()
        assert got == [], "a truncated packet (len mismatch) must be DROPPED, not delivered"
        assert "packet-integrity" in buf.getvalue() and "DROP" in buf.getvalue()
    finally:
        _cleanup(c, ns)


# ============================================================== PIN 3: sha catches corruption
def test_pin3_sha_catches_corruption():
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        b = _bus("b", c, ns)
        env = {"frm": "a", "to": "b", "kind": "chat", "content": '"hello world"',
               "ts": "2026-07-13T00:00:00Z", "meta": "{}", "parts": "[]"}
        ps.stamp(env)
        # flip ONE char in content, keep the same byte length so len passes but sha fails
        env["content"] = '"hEllo world"'
        c.xadd(f"{ns}:inbox:b", env)
        buf = io.StringIO()
        with redirect_stderr(buf):
            got = b.inbox()
        assert got == [], "a corrupted packet (sha mismatch) must be DROPPED"
        assert "DROP" in buf.getvalue()
    finally:
        _cleanup(c, ns)


# ============================================================== PIN 4: integrity kill-switch
def test_pin4_integrity_killswitch():
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        b = _bus("b", c, ns)
        env = {"frm": "a", "to": "b", "kind": "chat", "content": '"hello world"',
               "ts": "2026-07-13T00:00:00Z", "meta": "{}", "parts": "[]"}
        ps.stamp(env)
        env["content"] = '"HELLO world"'                    # corrupt
        c.xadd(f"{ns}:inbox:b", env)
        # kill-switch OFF -> the corrupt packet is DELIVERED, degraded, but LOUDLY (not silent)
        os.environ["PACKET_INTEGRITY_ENABLED"] = "false"
        buf = io.StringIO()
        with redirect_stderr(buf):
            got = b.inbox()
        assert len(got) == 1 and got[0].content == "HELLO world", \
            "with integrity disabled, delivery is degraded (not dropped)"
        assert "DEGRADED" in buf.getvalue() and "UNVERIFIED" in buf.getvalue(), \
            "degraded mode must be LOUD, never silent (deepseek GATE RED fix, defect 1)"
        os.environ["PACKET_INTEGRITY_ENABLED"] = "true"
    finally:
        _reset_dials()
        _cleanup(c, ns)


# ============================================== DEFECT 2 FIX: reassembly survives restart (no silent loss)
def test_frag_reassembly_survives_restart_loud_timeout():
    """deepseek GATE RED defect 2: a consumer restart mid-reassembly must NOT silently lose the
    partial. The durable (Redis-backed) buffer rehydrates on the new instance so the LOUD timeout
    still fires -- converting the former silent loss into a named fragment_timeout."""
    _reset_dials()
    os.environ["FRAG_REASSEMBLY_TTL"] = "0"
    c, ns = _client(), _ns()
    try:
        env = {"frm": "a", "to": "b", "kind": "handoff",
               "content": '"' + ("y" * 200_000) + '"', "ts": "2026-07-13T00:00:00Z",
               "meta": "{}", "parts": "[]"}
        frags = ps.fragment(env)
        assert len(frags) >= 4
        a = _bus("b", c, ns)                          # instance A
        for i, fr in enumerate(frags):
            if i == 3:
                continue                              # the never-arriving fragment
            c.xadd(f"{ns}:inbox:b", fr)
        assert a.inbox() == []                        # buffers 0,1,2 -> persisted to Redis
        assert c.hlen(f"{ns}:reasm:b") == 1, "an in-flight partial must be persisted for crash recovery"
        # 'restart': a brand-new Bus (fresh in-memory buffer) rehydrates the partial from Redis
        b2 = _bus("b", c, ns)
        buf = io.StringIO()
        with redirect_stderr(buf):
            time.sleep(0.02)
            b2.inbox()                                # idle drain on the NEW instance -> sweep fires
        out = buf.getvalue()
        assert "fragment_timeout" in out and "3" in out, \
            f"after restart the partial must time out LOUD, not vanish silently: {out!r}"
        assert c.hlen(f"{ns}:reasm:b") == 0, "the timed-out durable slot is cleaned up"
    finally:
        _reset_dials()
        _cleanup(c, ns)


def test_rehydrate_skips_completed_slot_no_double_delivery():
    """deepseek GATE RED round 2: a persisted slot holding ALL pieces (a completed whole whose
    durable delete failed) must NOT be resurrected on restart -- that would DOUBLE-DELIVER, since
    the in-memory _done dedup guard is gone after restart. rehydrate skips + cleans it."""
    _reset_dials()
    deleted, live = [], {}

    def persist(wid, slot):
        if slot is None:
            live.pop(wid, None)
            deleted.append(wid)
        else:
            live[wid] = slot

    r = ps.Reassembler(persist=persist)
    # a COMPLETE slot (3 of 3) as it might linger if the completion-delete was lost
    r.rehydrate({"WHOLE1": {"of": 3, "pieces": {"0": "a", "1": "b", "2": "c"}, "first": 0.0,
                            "whole_len": None, "whole_sha": None}})
    assert r.add({"frm": "a", "to": "b", "kind": "chat", "content": "c", "ts": "t",
                  "meta": "{}", "parts": "[]",
                  "frag": '{"seq":2,"of":3,"whole_id":"WHOLE1"}'}, now=1.0) == (None, None), \
        "a dup fragment of a completed whole must NOT re-deliver after restart"
    assert "WHOLE1" in deleted, "the orphaned complete slot must be cleaned up"
    # a genuinely INCOMPLETE slot IS resurrected (it still owes a timeout)
    r.rehydrate({"WHOLE2": {"of": 3, "pieces": {"0": "a"}, "first": 0.0,
                            "whole_len": None, "whole_sha": None}})
    assert r.sweep_expired(now=ps.frag_reassembly_ttl() + 1), "incomplete slot must still time out loud"


# ============================================================== PIN 5: frag roundtrip
def test_pin5_frag_roundtrip():
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        a = _bus("a", c, ns)
        b = _bus("b", c, ns)
        body = "".join(f"line {i:05d} the quick brown fox. " for i in range(8000))  # ~200KB
        assert len(body) > 195_000
        mid = a.send("b", "handoff", body, allow_frag=True)
        assert mid, "allow_frag send should succeed"
        assert c.xlen(f"{ns}:inbox:b") == 4, "200KB should fragment into 4 packets"
        got = b.inbox()
        assert len(got) == 1, "the consumer sees ONE reassembled message, not 4 fragments"
        assert got[0].content == body, "reassembled content is byte-identical"
        assert got[0].kind == "handoff"
    finally:
        _cleanup(c, ns)


# ============================================================== PIN 6: missing fragment -> timeout
def test_pin6_missing_fragment_times_out_naming_seq():
    _reset_dials()
    os.environ["FRAG_REASSEMBLY_TTL"] = "0"                  # any elapsed time expires a partial set
    c, ns = _client(), _ns()
    try:
        b = _bus("b", c, ns)
        # build 4 fragments, inject only 3 (drop seq 2)
        env = {"frm": "a", "to": "b", "kind": "handoff",
               "content": '"' + ("y" * 200_000) + '"', "ts": "2026-07-13T00:00:00Z",
               "meta": "{}", "parts": "[]"}
        frags = ps.fragment(env)
        assert len(frags) >= 4
        for i, fr in enumerate(frags):
            if i == 2:
                continue                                    # the missing fragment
            c.xadd(f"{ns}:inbox:b", fr)
        buf = io.StringIO()
        with redirect_stderr(buf):
            first = b.inbox()                               # buffers the partial set
            time.sleep(0.02)                                # let the TTL(=0) elapse
            second = b.inbox()                              # sweep fires the timeout
        assert first == [] and second == [], "an incomplete whole is never delivered"
        out = buf.getvalue()
        assert "fragment_timeout" in out and "missing seq" in out and "2" in out, \
            f"timeout must NAME the missing seq: {out!r}"
    finally:
        _reset_dials()
        _cleanup(c, ns)


# ============================================================== PIN 7: reassembly TTL boundary
def test_pin7_reassembly_ttl_boundary():
    _reset_dials()
    os.environ["FRAG_REASSEMBLY_TTL"] = "300"
    env = {"frm": "a", "to": "b", "kind": "handoff", "content": '"' + ("y" * 120_000) + '"',
           "ts": "2026-07-13T00:00:00Z", "meta": "{}", "parts": "[]"}
    frags = ps.fragment(env)
    # TTL-1 still holds the partial (not swept); TTL+1 sweeps it as timed-out
    r = ps.Reassembler()
    r.add(frags[0], now=0.0)
    assert r.sweep_expired(now=299.0) == [], "must NOT expire before TTL"
    assert r.sweep_expired(now=301.0), "must expire past TTL"
    _reset_dials()


# ============================================================== PIN 8: runner tool bridge MTU
def test_pin8_runner_tool_bridge_refuses_oversize_args():
    _reset_dials()
    small = {"path": "x.txt", "content": "hello"}
    ok, text = ps.tool_args_within_mtu("write_file", small)
    assert ok and text == ""
    big = {"path": "x.txt", "content": "z" * 200_000}
    ok, text = ps.tool_args_within_mtu("write_file", big)
    assert not ok, "oversize tool args must be REFUSED at the bite site, not silently clipped"
    assert "REFUSED" in text and "write_file" in text
    # a non-bridged (read-only) tool is unaffected
    ok, _ = ps.tool_args_within_mtu("list_directory", big)
    assert ok, "only the storage-intake tools are MTU-gated"


# ============================================================== PIN 9: RB-29 -- corrupt reply clears nothing
def test_pin9_corrupt_reply_never_clears_expectation():
    _reset_dials()
    from core.comm import expectations as ex
    c, ns = _client(), _ns()
    old_ns = os.environ.get("BIFROST_NAMESPACE")
    os.environ["BIFROST_NAMESPACE"] = ns                    # expectations builds its own Bus(sender)
    try:
        sender, resp = "asker", "answerer"
        orig_id = c.xadd(f"{ns}:inbox:{resp}", {"frm": sender, "to": resp, "kind": "request",
                                                 "content": '"do X"', "ts": "t", "meta": "{}", "parts": "[]"})
        armed = ex.arm(sender, str(orig_id), resp, "request", "do X", within_s=3600)
        assert armed
        # inject a CORRUPT reply into the asker's inbox (valid stamp then tampered sha)
        reply = {"frm": resp, "to": sender, "kind": "reply", "content": '"here is X"',
                 "ts": "t2", "meta": '{"answers": "%s"}' % orig_id, "parts": "[]"}
        ps.stamp(reply)
        reply["content"] = '"HERE is X"'                    # corrupt -> consume door drops it
        c.xadd(f"{ns}:inbox:{sender}", reply)
        res = ex.sweep(sender)
        assert str(orig_id) not in res.get("cleared", []), \
            "a corrupt reply must NOT clear an armed expectation (RB-29 extension)"
        # sanity: a CLEAN reply DOES clear it
        good = {"frm": resp, "to": sender, "kind": "reply", "content": '"here is X"',
                "ts": "t3", "meta": '{"answers": "%s"}' % orig_id, "parts": "[]"}
        ps.stamp(good)
        c.xadd(f"{ns}:inbox:{sender}", good)
        res2 = ex.sweep(sender)
        assert str(orig_id) in res2.get("cleared", []), "a valid reply must clear the expectation"
    finally:
        if old_ns is None:
            os.environ.pop("BIFROST_NAMESPACE", None)
        else:
            os.environ["BIFROST_NAMESPACE"] = old_ns
        _cleanup(c, ns)


# ============================================================== PIN 10: unknown keys preserved
def test_pin10_unknown_envelope_keys_preserved():
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        b = _bus("b", c, ns)
        env = {"frm": "a", "to": "b", "kind": "chat", "content": '"hi from the future"',
               "ts": "2026-07-13T00:00:00Z", "meta": "{}", "parts": "[]"}
        ps.stamp(env)
        env["v3_future_field"] = "some-v3-thing"             # a field this consumer never heard of
        sid = c.xadd(f"{ns}:inbox:b", env)
        got = b.inbox()
        assert len(got) == 1 and got[0].content == "hi from the future", \
            "an unknown envelope key must NOT cause the message to be dropped (forward-compat floor)"
        raw = c.xrange(f"{ns}:inbox:b", sid, sid)[0][1]
        assert raw.get("v3_future_field") == "some-v3-thing", "the unknown key is preserved on the wire"
    finally:
        _cleanup(c, ns)


# ============================================================== DRILL: replay the 3 real clip receipts
def test_drill_three_real_clip_payloads_zero_silent_loss():
    """The 2026-07-12 receipts: (a) a 2a-2c append, (b) a knowledge_note body, (c) an oversized
    handoff -- each previously CLIPPED silently. P2 auto-chunk (default): all three fragment and
    reassemble byte-identical. The explicit refusal path (allow_frag=False) stays alive."""
    _reset_dials()
    c, ns = _client(), _ns()
    try:
        a = _bus("a", c, ns)
        b = _bus("b", c, ns)
        payloads = {
            "append_2a_2c": "APPEND " + ("section body. " * 9000),        # ~120KB edit_file append
            "knowledge_note_body": "note: " + ("insight line. " * 9000),  # ~120KB note body
            "oversized_handoff": "handoff: " + ("context para. " * 9000),  # ~130KB handoff
        }
        for name, body in payloads.items():
            assert len(body.encode()) > ps.max_message_bytes(), f"{name} should exceed MTU"
            # 1) P2 default: auto-fragment, round-trip byte-identical, zero loss
            mid = a.send("b", "handoff", body)
            assert mid, f"{name} P2 auto-frag must send"
            got = b.inbox()
            assert len(got) == 1 and got[0].content == body, f"{name} lost/altered bytes on P2 auto-frag"
            # 2) explicit refusal: allow_frag=False still REFUSES loud, nothing written
            buf = io.StringIO()
            with redirect_stderr(buf):
                mid2 = a.send("b", "handoff", body, allow_frag=False)
            assert mid2 is None and "REFUSED" in buf.getvalue(), f"{name} must refuse on allow_frag=False"
            assert b.inbox() == [], f"{name}: nothing silently delivered after refusal"
    finally:
        _cleanup(c, ns)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
