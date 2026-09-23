"""An armed, waiting seat is invisible to every probe that decides whether to deliver.

INCIDENT, 2026-09-23. The operator messaged the claude seat from Discord and got, in the
gateway's own log:

    [bus] UNATTENDED RECIPIENT: 'claude' has no live seat (last beat 7561s ago).
    [discord-in] heard the operator -> global (bus id 1790178205948-0)

The seat had been working continuously for those 7561 seconds. Two hours later he wrote
"Are you reachable over discord? I had to ask navi to help reach you."

MEASURED on the live host at the moment of the incident:

    worklive_beat_age('claude') -> None
    progress_age('claude')      -> None
    attendance('claude')        -> ATTENDED | roster beat 0s     <- only while running tools

core.comm.liveness.attendance runs a three-probe ladder and documents each rung's
purpose. Rungs 2 and 3 exist specifically to cover the cases rung 1 misses:

    2. progress pulse   -- stamped at real work
    3. worklive beat    -- "the IDLE case a pulse cannot cover"

Both return None for an interactive seat. So the only rung that can see it is the roster
beat, which an interactive seat refreshes from its PostToolUse hook -- i.e. only while it
is making tool calls. The seat is therefore visible exactly while it is BUSY and invisible
exactly while it is ARMED AND WAITING, which is the one state in which mail is promptly
readable. Presence is measured by activity; the thing that needs measuring is attention.

TWO INDEPENDENT CAUSES, and each alone keeps the bug alive.

READ SIDE. worklive_beat_age calls read(agent) on the bare id. Runners write
`bifrost:worklive:kimi` AND `bifrost:worklive:kimi#36120-ki`; an interactive seat writes
only the incarnation-suffixed key, so the bare read misses it entirely. live_incarnations()
was built on 2026-08-20 for exactly this and its docstring records the same measurement a
month earlier -- read("claude") -> None while read("claude#06528775") showed a 1s beat --
under the heading "Absence of a KEY is not absence of a SEAT". It also says, deliberately,
that it is NOT folded into read() because "a seat and one of its incarnations are different
subjects ... This NAMES the ids so the caller decides." attendance's caller asks "will mail
to claude be read", for which ANY live incarnation is a correct yes -- the same semantics
rung 1 already uses when it takes min(ages) across roster rows. So this is the caller
making the decision the author left to it, not a reinterpretation of read().

WRITE SIDE. scripts/bifrost_wake.py holds a seat file and beats nothing. The listener is
the one component that is definitionally present-and-waiting, and it is the one component
contributing no evidence of it. Fixing only the read side leaves the incarnation key
ageing out of its TTL during exactly the idle stretch that matters.

SAFETY. attendance consults evidence in ONE direction -- each probe may only turn
UNATTENDED into ATTENDED, never invent a death -- so widening a probe cannot manufacture a
false death. The listener's beat is TTL'd like every other worklive record, so a listener
that dies stops asserting presence on its own.

AND THE PHASE MATTERS. doctor keys HARD WEDGE on a non-idle phase with a dead pulse, and
liveness.IDLE_PHASES is {"idle", "online", "replied"}. A listener beating phase="running"
while blocked would page the fleet as wedged every time a seat waited for mail -- a
false-alarming monitor is worse than the blind spot it replaces.

Run:  py -m pytest tests/test_idle_seat_attendance.py -v
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import liveness as L


class FakeRedis:
    """Enough of the surface liveness uses: get / keys / setex-ish set."""

    def __init__(self, kv=None):
        self.kv = dict(kv or {})

    def get(self, k):
        return self.kv.get(k)

    def keys(self, pattern):
        import fnmatch
        return [k for k in self.kv if fnmatch.fnmatch(k, pattern)]

    def set(self, k, v, ex=None, **kw):
        self.kv[k] = v
        return True

    def setex(self, k, ttl, v):
        self.kv[k] = v
        return True


def _rec(beat_age_s: float, phase: str = "idle", seq: int = 1):
    return json.dumps({"phase": phase, "beat_ts": time.time() - beat_age_s, "seq": seq})


@pytest.fixture
def fake_bus(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(L, "_client", lambda *a, **k: fake)
    return fake


# ------------------------------------------------------------------ read side
def test_an_incarnation_only_seat_has_a_measurable_beat(fake_bus):
    """THE LIVE DEFECT: only the suffixed key exists, and the probe reports nothing."""
    pre = L._worklive_prefix()
    fake_bus.kv[pre + "claude#c097980f"] = _rec(3.0)

    assert L.read("claude") is None                      # unchanged, by design
    assert L.live_incarnations("claude") == ["claude#c097980f"]

    age = L.worklive_beat_age("claude")
    assert age is not None, (
        "worklive_beat_age reported no record for a seat whose incarnation is beating -- "
        "the exact gap live_incarnations was built to close a month earlier"
    )
    assert age < 10


def test_the_freshest_incarnation_wins(fake_bus):
    """Rung 1 already takes min(ages) across roster rows; this must agree."""
    pre = L._worklive_prefix()
    fake_bus.kv[pre + "claude#aaaaaaaa"] = _rec(240.0)
    fake_bus.kv[pre + "claude#bbbbbbbb"] = _rec(2.0)
    age = L.worklive_beat_age("claude")
    assert age is not None and age < 10, f"stale incarnation shadowed a live one (age={age})"


def test_the_bare_record_still_works_for_runners(fake_bus):
    """Runners write the bare key. Nothing about them may change."""
    pre = L._worklive_prefix()
    fake_bus.kv[pre + "kimi"] = _rec(1.0)
    age = L.worklive_beat_age("kimi")
    assert age is not None and age < 10


def test_absence_is_still_absence(fake_bus):
    """Widening the search must not invent a record. No key, no age."""
    assert L.worklive_beat_age("nobody-home") is None


def test_a_stale_incarnation_is_not_rescued(fake_bus):
    """A record whose own beat aged out is evidence the beater STOPPED -- death, not
    life. Widening the lookup must not soften that."""
    pre = L._worklive_prefix()
    fake_bus.kv[pre + "claude#c097980f"] = _rec(9999.0)
    age = L.worklive_beat_age("claude")
    assert age is not None and age > L.UNATTENDED_S, (
        "a long-dead incarnation must report its true age, not be hidden or refreshed"
    )


def test_attendance_sees_an_idle_armed_seat(fake_bus, monkeypatch):
    """The whole point: with no roster beat and no pulse, an idle seat that is beating
    must still be ATTENDED -- otherwise the send door warns the operator that nothing is
    reading his mail while a listener is blocked on his inbox."""
    monkeypatch.setattr(L, "progress_age", lambda *a, **k: None)
    import core.comm.roster as _roster
    monkeypatch.setattr(_roster, "roster", lambda *a, **k: [])

    pre = L._worklive_prefix()
    fake_bus.kv[pre + "claude#c097980f"] = _rec(4.0)

    v = L.attendance("claude")
    assert v.state == "ATTENDED", (
        f"an armed, beating, idle seat read {v.state} ({v.reason}) -- this is the "
        "UNATTENDED RECIPIENT warning the operator saw while the seat was right here"
    )


# ----------------------------------------------------------------- write side
def test_the_wake_listener_beats_while_it_blocks():
    """The listener is the one component that is definitionally present-and-waiting,
    and today it contributes no evidence of it."""
    src = (REPO / "scripts" / "bifrost_wake.py").read_text(encoding="utf-8")
    assert "worklive" in src.lower(), (
        "scripts/bifrost_wake.py never touches worklive: it holds a seat file and beats "
        "nothing, so an armed seat is invisible to the probe built for the idle case"
    )


def test_the_listener_beats_an_idle_phase_not_a_running_one():
    """doctor keys HARD WEDGE on a non-idle phase with a dead pulse. A listener beating
    'running' while blocked would page the fleet as wedged every time a seat waits."""
    src = (REPO / "scripts" / "bifrost_wake.py").read_text(encoding="utf-8")
    beat_region = "".join(ln for ln in src.splitlines(keepends=True)
                          if "worklive" in ln.lower() or "phase" in ln.lower())
    assert beat_region, "no beat to inspect"
    assert any(f'"{p}"' in beat_region or f"'{p}'" in beat_region for p in L.IDLE_PHASES), (
        f"the listener's beat does not declare one of {sorted(L.IDLE_PHASES)} -- a "
        "blocked listener beating a non-idle phase manufactures HARD WEDGE pages"
    )
