"""T095 M0 PRE-REGISTERED ACCEPTANCE -- shadow mailbox state index.

These pins cite the reconciled build spec at ``docs/comms-mailbox-design-2026-07.md``
sec 2 (counter-folded 2026-07-18: evidence ladder acked > replied > auto_acked >
consumed > unhandled; tiered retention; deepseek pin extensions 9-13).  Committed RED
before implementation.  M0 is observational only: the index derives state from what
the streams already contain; it may not write cursors, acks, sends, or any key
outside ``{ns}:mailbox:*``.

Run::

    py -m pytest tests/test_t095_m0_mailbox_shadow.py -q
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm.bus import Bus  # noqa: E402


def _mailbox():
    # Import inside each pin so pytest still collects and names every RED test
    # before core/comm/mailbox.py exists (T060 RED convention).
    return importlib.import_module("core.comm.mailbox")


NS = "test-mbx"


class _FakeRedis:
    """Redis double: streams + hashes + zsets, with a mutation spy and an optional
    poison switch for ``{ns}:mailbox:*`` writes (pin 5)."""

    def __init__(self, *, poison_mailbox: bool = False) -> None:
        self.poison_mailbox = poison_mailbox
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.zsets: dict[str, dict[str, float]] = {}
        self.mutated_keys: list[str] = []
        self.cursor_hgetall_calls: list[str] = []
        self._tick = 0

    # -- spy / poison ------------------------------------------------------
    def _mut(self, key: str) -> None:
        key = str(key)
        if self.poison_mailbox and ":mailbox:" in key:
            raise ConnectionError("poisoned mailbox write")
        self.mutated_keys.append(key)

    # -- streams -----------------------------------------------------------
    def xadd(self, key, fields, maxlen=None, approximate=True):
        self._mut(key)
        self._tick += 1
        sid = f"{1000000 + self._tick}-0"
        self.streams.setdefault(str(key), []).append((sid, {str(k): str(v) for k, v in fields.items()}))
        return sid

    def xrange(self, key, min="-", max="+", count=None):
        entries = self.streams.get(str(key), [])
        if isinstance(min, str) and min.startswith("("):
            floor = min[1:]
            entries = [e for e in entries if self._cmp(e[0], floor) > 0]
        elif min not in ("-", None):
            entries = [e for e in entries if self._cmp(e[0], min) >= 0]
        if max not in ("+", None):
            entries = [e for e in entries if self._cmp(e[0], max) <= 0]
        if count is not None:
            entries = entries[: int(count)]
        return [(sid, dict(f)) for sid, f in entries]

    def xlen(self, key):
        return len(self.streams.get(str(key), []))

    @staticmethod
    def _cmp(a: str, b: str) -> int:
        def parse(x: str):
            ms, _, seq = str(x).partition("-")
            return (int(ms or 0), int(seq or 0))
        pa, pb = parse(a), parse(b)
        return (pa > pb) - (pa < pb)

    # -- hashes ------------------------------------------------------------
    def hset(self, key, field=None, value=None, mapping=None):
        self._mut(key)
        h = self.hashes.setdefault(str(key), {})
        if mapping:
            for k, v in mapping.items():
                h[str(k)] = str(v)
        if field is not None:
            h[str(field)] = str(value)
        return 1

    def hgetall(self, key):
        key = str(key)
        if ":cursor:" in key:
            self.cursor_hgetall_calls.append(key)
        return dict(self.hashes.get(key, {}))

    def hdel(self, key, *fields):
        self._mut(key)
        h = self.hashes.get(str(key), {})
        for f in fields:
            h.pop(str(f), None)
        return 1

    def hincrby(self, key, field, amount=1):
        self._mut(key)
        h = self.hashes.setdefault(str(key), {})
        h[str(field)] = str(int(h.get(str(field), "0")) + int(amount))
        return int(h[str(field)])

    # -- zsets -------------------------------------------------------------
    def zadd(self, key, mapping):
        self._mut(key)
        z = self.zsets.setdefault(str(key), {})
        for member, score in mapping.items():
            z[str(member)] = float(score)
        return 1

    def zcard(self, key):
        return len(self.zsets.get(str(key), {}))

    def zrange(self, key, start, end, withscores=False):
        z = sorted(self.zsets.get(str(key), {}).items(), key=lambda kv: (kv[1], kv[0]))
        sliced = z[start: (None if end == -1 else end + 1)]
        return [(m, s) for m, s in sliced] if withscores else [m for m, _ in sliced]

    def zrem(self, key, *members):
        self._mut(key)
        z = self.zsets.get(str(key), {})
        for m in members:
            z.pop(str(m), None)
        return 1

    def delete(self, *keys):
        for key in keys:
            self._mut(key)
            self.streams.pop(str(key), None)
            self.hashes.pop(str(key), None)
            self.zsets.pop(str(key), None)
        return 1

    # -- misc used by Bus --------------------------------------------------
    def set(self, key, value, nx=False, ex=None):
        self._mut(key)
        self.hashes.setdefault("__values__", {})
        vals = self.hashes["__values__"]
        if nx and str(key) in vals:
            return None
        vals[str(key)] = str(value)
        return True

    def get(self, key):
        return self.hashes.get("__values__", {}).get(str(key))

    def publish(self, *a, **k):
        return 0

    def eval(self, *a, **k):
        return "OK"

    def ping(self):
        return True


def _mk(agent="deepseek", poison=False):
    fake = _FakeRedis(poison_mailbox=poison)
    bus = Bus(agent_id="claude", client=fake, namespace=NS)
    return fake, bus


def _advance_cursor(fake: _FakeRedis, agent: str, *, lane_inbox=None, legacy_inbox=None,
                    sig_inbox=None) -> None:
    if lane_inbox is not None:
        fake.hashes.setdefault(f"{NS}:cursor:lane:{agent}", {})["inbox"] = lane_inbox
    if sig_inbox is not None:
        fake.hashes.setdefault(f"{NS}:cursor:lane:{agent}", {})["sig_inbox"] = sig_inbox
    if legacy_inbox is not None:
        fake.hashes.setdefault(f"{NS}:cursor:{agent}", {})["inbox"] = legacy_inbox


# ---------------------------------------------------------------- pin 1
def test_index_never_writes_transport_state():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "do the thing")
    bus.send("deepseek", "chat", "hello")
    before_streams = {k: list(v) for k, v in fake.streams.items()}
    before_cursors = {k: dict(v) for k, v in fake.hashes.items() if ":cursor:" in k}
    fake.mutated_keys.clear()
    mbx.query(NS, "deepseek", client=fake)
    for _ in range(100):
        mbx.query(NS, "deepseek", client=fake)
    assert all(":mailbox:" in k for k in fake.mutated_keys), (
        f"non-mailbox writes: {[k for k in fake.mutated_keys if ':mailbox:' not in k]}")
    assert fake.streams == before_streams
    assert {k: dict(v) for k, v in fake.hashes.items() if ":cursor:" in k} == before_cursors


# ---------------------------------------------------------------- pin 2
def test_unhandled_matches_ground_truth():
    mbx = _mailbox()
    fake, bus = _mk()
    mid = bus.send("deepseek", "handoff", "please review X")
    r = mbx.query(NS, "deepseek", client=fake)
    assert r["available"] and r["counts"]["unhandled"] == 1

    # answered via reply linkage (meta.answers = the message id) -> replied/auto_acked
    peer = Bus(agent_id="deepseek", client=fake, namespace=NS)
    peer.send("claude", "reply", "done", meta={"answers": mid})
    mbx.catch_up(NS, "claude", client=fake)          # replies ride the SENDER's inbox
    r2 = mbx.query(NS, "deepseek", client=fake)
    assert r2["counts"]["unhandled"] == 0
    assert r2["counts"].get("auto_acked", 0) + r2["counts"].get("replied", 0) == 1

    # msg_ack -> acked (exact per-id lookup, injected)
    mid2 = bus.send("deepseek", "request", "second ask")
    acks = {str(mid2): [{"by": "deepseek", "at": "t", "note": ""}]}
    r3 = mbx.query(NS, "deepseek", client=fake, acks_lookup=lambda ids: {
        str(i): acks.get(str(i), []) for i in ids})
    tiers = {e["sha"]: e["tier"] for e in r3["entries"]}
    assert "acked" in set(tiers.values())


# ---------------------------------------------------------------- pin 3
def test_rebuild_equals_incremental():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(6):
        bus.send("deepseek", "handoff" if i % 2 else "chat", f"m{i}")
    incremental = mbx.query(NS, "deepseek", client=fake)
    rebuilt = mbx.rebuild(NS, "deepseek", client=fake)
    assert rebuilt["divergence"] == 0
    assert {e["sha"]: e["tier"] for e in incremental["entries"]} == \
           {e["sha"]: e["tier"] for e in mbx.query(NS, "deepseek", client=fake)["entries"]}


# ---------------------------------------------------------------- pin 4
def test_bounded_cardinality():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(60):
        bus.send("deepseek", "chat", f"noise {i}")
    for i in range(5):
        bus.send("deepseek", "handoff", f"ask {i}")
    r = mbx.query(NS, "deepseek", client=fake, cap=40)
    assert r["available"]
    assert len(r["entries"]) <= 40
    kinds = [e["kind"] for e in r["entries"]]
    assert kinds.count("handoff") == 5, "eviction must drop non-handoff kinds first"
    assert r["evicted"] >= 25


# ---------------------------------------------------------------- pin 5 (K0 unit form)
def test_index_failure_never_affects_delivery():
    mbx = _mailbox()
    fake, bus = _mk(poison=True)
    mid = bus.send("deepseek", "handoff", "must deliver")
    assert mid is not None
    lane_key = f"{NS}:work:inbox:deepseek"
    assert any(lane_key == k for k in fake.streams), "delivery unaffected by poisoned index"
    r = mbx.query(NS, "deepseek", client=fake)
    assert r["available"] is False and "peek" in r["reason"].lower()


# ---------------------------------------------------------------- pin 6
def test_firehose_kinds_excluded():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "real")
    fake.xadd(f"{NS}:trace", {"frm": "deepseek", "to": "*", "kind": "trace",
                              "content": "\"tool call\"", "ts": "t", "meta": "{}"})
    fake.xadd(f"{NS}:work:inbox:deepseek", {"frm": "x", "to": "deepseek", "kind": "hint",
                                            "content": "\"h\"", "ts": "t",
                                            "meta": json.dumps({"display_only": True})})
    r = mbx.query(NS, "deepseek", client=fake)
    kinds = {e["kind"] for e in r["entries"]}
    assert "trace" not in kinds and "hint" not in kinds
    assert r["counts"]["unhandled"] == 1


# ---------------------------------------------------------------- pin 7
def test_staleness_is_honest():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "one")
    r = mbx.query(NS, "deepseek", client=fake, catch_up_budget=0)
    assert r["available"]
    assert r["index_lag"] >= 1, "frozen refresh must report positive lag, never fresh"


# ---------------------------------------------------------------- pin 8
def test_concurrent_readers_identical_and_writeless():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "shared view")
    a = mbx.query(NS, "deepseek", client=fake)
    fake.mutated_keys.clear()
    b = mbx.query(NS, "deepseek", client=fake)
    assert {e["sha"] for e in a["entries"]} == {e["sha"] for e in b["entries"]}
    assert all(":mailbox:" in k for k in fake.mutated_keys)


# ---------------------------------------------------------------- pin 9 (deepseek)
def test_nudge_marked_consumed_not_unhandled_forever():
    mbx = _mailbox()
    fake, bus = _mk()
    mid = bus.send("deepseek", "nudge", "look now")
    sid = fake.streams[f"{NS}:sig:inbox:deepseek"][-1][0] if f"{NS}:sig:inbox:deepseek" in fake.streams \
        else fake.streams[f"{NS}:work:inbox:deepseek"][-1][0]
    # runner answers with kind=note (no answers meta, no ack) and its cursor advances
    peer = Bus(agent_id="deepseek", client=fake, namespace=NS)
    peer.send("claude", "note", "[nudge ack] looking")
    _advance_cursor(fake, "deepseek", lane_inbox=sid, sig_inbox=sid, legacy_inbox=sid)
    r = mbx.query(NS, "deepseek", client=fake)
    tier = {e["kind"]: e["tier"] for e in r["entries"]}
    assert tier.get("nudge") == "consumed", f"nudge must be consumed, got {tier}"


# ---------------------------------------------------------------- pin 10 (deepseek)
def test_steer_marked_consumed_not_unhandled_forever():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "steer", "fold this into the live task")
    stream = f"{NS}:sig:inbox:deepseek" if f"{NS}:sig:inbox:deepseek" in fake.streams \
        else f"{NS}:work:inbox:deepseek"
    sid = fake.streams[stream][-1][0]
    _advance_cursor(fake, "deepseek", lane_inbox=sid, sig_inbox=sid, legacy_inbox=sid)
    r = mbx.query(NS, "deepseek", client=fake)
    tiers = [e["tier"] for e in r["entries"] if e["kind"] == "steer"]
    assert tiers == ["consumed"]


# ---------------------------------------------------------------- pin 11 (deepseek)
def test_hint_excluded_from_mailbox():
    mbx = _mailbox()
    fake, _bus = _mk()
    fake.xadd(f"{NS}:work:inbox:deepseek", {"frm": "x", "to": "deepseek", "kind": "hint",
                                            "content": "\"h\"", "ts": "t",
                                            "meta": json.dumps({"display_only": True})})
    r = mbx.query(NS, "deepseek", client=fake)
    assert r["entries"] == [] and r["counts"]["unhandled"] == 0


# ---------------------------------------------------------------- pin 12 (deepseek)
def test_cursor_advance_during_mailbox_read_consistent():
    mbx = _mailbox()
    fake, bus = _mk()
    bus.send("deepseek", "handoff", "snapshot me")
    fake.cursor_hgetall_calls.clear()
    mbx.query(NS, "deepseek", client=fake)
    lane_reads = [k for k in fake.cursor_hgetall_calls if k == f"{NS}:cursor:lane:deepseek"]
    legacy_reads = [k for k in fake.cursor_hgetall_calls if k == f"{NS}:cursor:deepseek"]
    assert len(lane_reads) == 1 and len(legacy_reads) == 1, (
        "cursors must be read once per query (snapshot semantics); "
        f"got {fake.cursor_hgetall_calls}")


# ---------------------------------------------------------------- pin 13 (deepseek)
def test_twin_runners_see_same_mailbox_state():
    mbx = _mailbox()
    fake, bus = _mk()
    for i in range(4):
        bus.send("deepseek", "request", f"r{i}")
    one = mbx.query(NS, "deepseek", client=fake)
    two = mbx.query(NS, "deepseek", client=fake)
    assert [(e["sha"], e["tier"]) for e in one["entries"]] == \
           [(e["sha"], e["tier"]) for e in two["entries"]]
