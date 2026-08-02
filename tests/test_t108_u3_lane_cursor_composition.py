"""T108 U3 PRE-REGISTERED ACCEPTANCE -- lane-cursor read/write composition.

Committed RED before implementation (M3 pre-registration; the arc scorecard read
0/11 clean when these were written, so this slice starts the repair).

THE DEFECT.  ``core/comm/bus.py:1182-1183`` composes the lane cursor key WITH an
incarnation suffix when the Bus declares one::

    {ns}:cursor:lane:{agent}#{sid8}

``core/comm/mailbox.py:330`` reads it WITHOUT::

    {ns}:cursor:lane:{agent}

Two different keys.  The writer advances one, the reader consults the other, and
every lane message the seat actually consumed is reported ``unhandled`` forever.

WHY IT IS DORMANT TODAY, and why that is not reassuring.  No production launcher
passes an incarnation, so ``self._incarnation`` is empty, so the writer composes the
UNSUFFIXED key and both sides agree by accident.  The U2 slice sets an incarnation --
which ARMS this break.  U3 therefore lands WITH or BEFORE U2; it is not a separate
slice that can follow.

Provenance: deepseek settled U2 and supplied the acceptance shape (research/in-flight/
netcode-u2-u3-coupling-deepseek-2026-08-02.md sec c).  Pins 3 and 4 are convener
amendments to that shape -- see each pin's own note for what changed and why.

Run::

    py -m pytest tests/test_t108_u3_lane_cursor_composition.py -q
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm.bus import Bus  # noqa: E402


def _mailbox():
    return importlib.import_module("core.comm.mailbox")


NS = "test-u3"
SID_A = "aaaaaaaa"
SID_B = "bbbbbbbb"


class _FakeRedis:
    """Redis double: streams + hashes + zsets.

    Adds what the T095 double lacks and this slice needs -- key-discovery spies.
    ``keys`` and ``scan_iter`` are recorded SEPARATELY so a pin can enforce which
    primitive the implementation reached for (pin 3).
    """

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict]]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.zsets: dict[str, dict[str, float]] = {}
        self.mutated_keys: list[str] = []
        self.cursor_hgetall_calls: list[str] = []
        self.keys_calls: list[str] = []
        self.scan_calls: list[str] = []
        self._tick = 0

    # -- spy ---------------------------------------------------------------
    def _mut(self, key: str) -> None:
        self.mutated_keys.append(str(key))

    # -- key discovery -----------------------------------------------------
    def _match(self, pattern: str) -> list[str]:
        pattern = str(pattern)
        if not pattern.endswith("*"):
            return [k for k in self.hashes if k == pattern]
        stem = pattern[:-1]
        return [k for k in self.hashes if k.startswith(stem)]

    def keys(self, pattern="*"):
        # O(N) over the whole keyspace and it BLOCKS the server. Recorded so a pin
        # can refuse it outright; never make this convenient.
        self.keys_calls.append(str(pattern))
        return self._match(pattern)

    def scan_iter(self, match="*", count=None):
        self.scan_calls.append(str(match))
        return iter(self._match(match))

    def scan(self, cursor=0, match="*", count=None):
        self.scan_calls.append(str(match))
        return 0, self._match(match)

    # -- streams -----------------------------------------------------------
    def xadd(self, key, fields, maxlen=None, approximate=True):
        self._mut(key)
        self._tick += 1
        sid = f"{self._tick}-0"
        self.streams.setdefault(str(key), []).append((sid, dict(fields)))
        return sid

    def xrange(self, key, min="-", max="+", count=None):
        entries = list(self.streams.get(str(key), []))
        out = []
        for sid, fields in entries:
            if min not in ("-", "0", "0-0") and self._cmp(sid, str(min).lstrip("(")) <= 0:
                continue
            if max != "+" and self._cmp(sid, str(max)) > 0:
                continue
            out.append((sid, fields))
        return out[:count] if count else out

    def xlen(self, key):
        return len(self.streams.get(str(key), []))

    @staticmethod
    def _cmp(a: str, b: str) -> int:
        pa = [int(x) for x in str(a).split("-")]
        pb = [int(x) for x in str(b).split("-")]
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
        h[str(field)] = str(int(h.get(str(field), 0)) + amount)
        return int(h[str(field)])

    # -- zsets -------------------------------------------------------------
    def zadd(self, key, mapping):
        self._mut(key)
        z = self.zsets.setdefault(str(key), {})
        for m, s in mapping.items():
            z[str(m)] = float(s)
        return 1

    def zcard(self, key):
        return len(self.zsets.get(str(key), {}))

    def zrange(self, key, start, end, withscores=False):
        items = sorted(self.zsets.get(str(key), {}).items(), key=lambda kv: kv[1])
        if end == -1:
            end = len(items)
        else:
            end = end + 1
        sliced = items[start:end]
        return sliced if withscores else [m for m, _ in sliced]

    def zrem(self, key, *members):
        self._mut(key)
        z = self.zsets.get(str(key), {})
        for m in members:
            z.pop(str(m), None)
        return 1

    # -- misc --------------------------------------------------------------
    def delete(self, *keys):
        for k in keys:
            self._mut(k)
            self.hashes.pop(str(k), None)
            self.zsets.pop(str(k), None)
            self.streams.pop(str(k), None)
        return 1

    def set(self, key, value, nx=False, ex=None):
        self._mut(key)
        self.hashes.setdefault("_scalars", {})[str(key)] = str(value)
        return True

    def get(self, key):
        return self.hashes.get("_scalars", {}).get(str(key))

    def publish(self, *a, **k):
        return 0

    def eval(self, *a, **k):
        return 1

    def ping(self):
        return True


def _mk(agent="deepseek"):
    fake = _FakeRedis()
    bus = Bus(agent_id="claude", client=fake, namespace=NS)
    return fake, bus


def _tier_of(result, sha_or_kind: str):
    """``mailbox.query`` returns a dict envelope; the rows live under 'entries'."""
    for e in (result or {}).get("entries", []):
        if e.get("kind") == sha_or_kind or e.get("sha") == sha_or_kind:
            return e.get("tier")
    return None


def _set_cursor(fake: _FakeRedis, agent: str, *, sid8: str = "", **fields) -> None:
    """Write a lane cursor hash, optionally incarnation-suffixed."""
    key = f"{NS}:cursor:lane:{agent}#{sid8}" if sid8 else f"{NS}:cursor:lane:{agent}"
    fake.hashes.setdefault(key, {}).update({k: str(v) for k, v in fields.items()})


# ---------------------------------------------------------------- pin 1
def test_suffixed_cursor_is_visible_to_the_mailbox():
    """THE DEFECT. A seat that consumed under an incarnation must not read as unhandled.

    RED before the fix: the mailbox consults only the unsuffixed key, finds nothing,
    and reports a message the seat demonstrably consumed as ``unhandled``.
    """
    mbx = _mailbox()
    fake, bus = _mk()
    sid = bus.send("deepseek", "handoff", "do the thing")
    assert sid, "precondition: the send must land"

    # The seat consumed it under incarnation A -- suffixed key ONLY, which is
    # exactly what bus.py:1182-1183 writes when an incarnation is declared.
    _set_cursor(fake, "deepseek", sid8=SID_A, inbox=sid)
    assert f"{NS}:cursor:lane:deepseek" not in fake.hashes, (
        "precondition: no unsuffixed cursor exists -- the suffixed one is the only truth")

    entries = mbx.query(NS, "deepseek", client=fake)
    assert _tier_of(entries, "handoff") != "unhandled", (
        "the suffixed lane cursor is invisible to the mailbox: a consumed message "
        "reports unhandled forever (bus.py:1182-1183 writes '#sid8', mailbox.py:330 "
        "reads bare)")


# ---------------------------------------------------------------- pin 2
def test_unincarnated_seat_is_unchanged():
    """NO REGRESSION. Every seat without an incarnation must behave byte-identically.

    This is the pin that stops the fix from being a cure worse than the disease:
    moving the mailbox to suffixed-ONLY reads would blind it to every seat that has
    no incarnation, which today is all of them.
    """
    mbx = _mailbox()
    fake, bus = _mk()
    sid = bus.send("deepseek", "handoff", "do the thing")
    _set_cursor(fake, "deepseek", inbox=sid)          # unsuffixed, the status quo

    entries = mbx.query(NS, "deepseek", client=fake)
    assert _tier_of(entries, "handoff") != "unhandled", (
        "the unsuffixed path regressed -- this must pass BEFORE and AFTER the fix")


# ---------------------------------------------------------------- pin 3
def test_discovery_uses_scan_never_keys():
    """CONVENER AMENDMENT to deepseek's shape, which proposed ``client.keys(...)``.

    KEYS is O(N) over the ENTIRE keyspace and blocks the Redis server for the
    duration -- it is not, as the proposal stated, O(1) in the number of matches.
    The roster is already at 143 seats and growing (F7 seat inflation), each with
    live keys, and the mailbox is a hot read. SCAN is the correct primitive.

    Enforced structurally rather than by review: the double records both, and this
    pin refuses KEYS outright. Pin 1 forces the discovery to happen at all; this one
    constrains HOW.
    """
    mbx = _mailbox()
    fake, bus = _mk()
    sid = bus.send("deepseek", "handoff", "do the thing")
    _set_cursor(fake, "deepseek", sid8=SID_A, inbox=sid)

    fake.keys_calls.clear()
    fake.scan_calls.clear()
    mbx.query(NS, "deepseek", client=fake)

    assert fake.keys_calls == [], (
        f"KEYS is a blocking O(keyspace) scan and must never be used on a hot read; "
        f"called with {fake.keys_calls}. Use scan_iter.")
    assert fake.scan_calls, (
        "the suffixed cursor was never looked for -- discovery must go through SCAN")


# ---------------------------------------------------------------- pin 4
def test_merge_is_per_field_max_across_incarnations():
    """CONVENER AMENDMENT: pin the MERGE SEMANTICS explicitly rather than let them
    be an accident of implementation.

    Two incarnations of one agent, each ahead on a DIFFERENT field. The merged view
    must take the max PER FIELD -- not the whole hash of whichever key sorted last,
    which would silently discard the other incarnation's progress.

    Why max is correct here, stated so a future reader can challenge it rather than
    inherit it: the lane is the ROLE queue, where serialization is the wanted
    property (T108 -- exactly-once claim is the feature). If ANY incarnation of agent
    X consumed lane position N, agent X has handled N. The mailbox is a REPORTING
    surface; merging its view never advances a real consumption cursor, so a
    lagging incarnation still redelivers per RB-26.
    """
    mbx = _mailbox()
    fake, bus = _mk()
    first = bus.send("deepseek", "handoff", "one")
    second = bus.send("deepseek", "chat", "two")

    # A leads on inbox, B leads on bc. Neither alone is the truth.
    _set_cursor(fake, "deepseek", sid8=SID_A, inbox=second, bc="0-0")
    _set_cursor(fake, "deepseek", sid8=SID_B, inbox=first, bc="9999-0")

    merged = mbx.merged_lane_cursor(NS, "deepseek", client=fake)
    assert merged.get("inbox") == second, (
        f"per-field max lost A's inbox lead: {merged}")
    assert merged.get("bc") == "9999-0", (
        f"per-field max lost B's bc lead: {merged}")


# ---------------------------------------------------------------- pin 5
def test_cursor_snapshot_semantics_survive_discovery():
    """The existing contract (mailbox._resolve docstring, T095 pin 12) is that cursor
    hashes are read EXACTLY ONCE per query -- snapshot semantics. Adding suffixed
    discovery must not turn that into a re-read loop, which would reintroduce the
    torn-read class the snapshot rule exists to prevent.
    """
    mbx = _mailbox()
    fake, bus = _mk()
    sid = bus.send("deepseek", "handoff", "do the thing")
    _set_cursor(fake, "deepseek", sid8=SID_A, inbox=sid)
    _set_cursor(fake, "deepseek", sid8=SID_B, inbox="0-0")

    fake.cursor_hgetall_calls.clear()
    mbx.query(NS, "deepseek", client=fake)

    seen = fake.cursor_hgetall_calls
    assert len(seen) == len(set(seen)), (
        f"a cursor hash was read more than once -- snapshot semantics broken: {seen}")
