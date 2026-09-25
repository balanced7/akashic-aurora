"""RED-FIRST pin (M3): the roster's Redis connection cost must not scale with the fleet.

THE DEFECT (measured 2026-09-24, kimi HARD WEDGE, sessions kimi#19772 / #53044 / #51452):
`roster._have_summary` constructs a brand-new `Bus` for EVERY row, and `Bus.__init__`
calls `bus._connect()` unconditionally -- one fresh Redis connection per seat, per call.
`liveness.attendance` then calls `roster()` once per agent, and
`conductor_gate.evaluate_succession` calls `attendance` once per successor. Measured on
the live fleet: 55 rows -> 113 socket opens and 3.3s of wall time PER GATE PASS, on a
60s cadence, in EVERY runner.

WHY IT WEDGES RATHER THAN MERELY WASTING: every one of those sockets is an outbound
connection to `localhost:16379`, which resolves to ::1 -- wslrelay's listener. Each close
parks an ephemeral port in TIME_WAIT for the Windows 2MSL. The dynamic range is 16384
ports; 1,793 were in TIME_WAIT to this one port ten minutes after a cold boot, and the
machine logged Tcpip 4227 (local endpoint reused too soon) the same day. Once the range
is under pressure, a connect BLOCKS instead of returning, and 111 blocking connects at
`socket_connect_timeout=3` is up to 5.5 minutes with the runner's MainThread parked
inside `conductor_gate` -- which is exactly the py-spy stack captured from pid 50304, and
exactly the shape the doctor pages as "non-idle phase 'running' ... DEAD pulse".

THE FEEDBACK LOOP that makes it escalate: 50 of those 55 rows were DEAD seats. Every
watchdog relaunch appends another row, so each recovery makes the next pass more
expensive. The cure was feeding the disease.

THE INVARIANT PINNED HERE is deliberately about COST SHAPE, not implementation: a roster
read may open a bounded number of connections, but that number must not grow with the
number of seats. Any implementation that shares a connection passes; the one that mints
one per row cannot. It says nothing about HOW the sharing is done, so a better design
than the one that follows this pin is free to replace it.
"""

import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NS = f"connreuse{uuid.uuid4().hex[:6]}"


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    return connect_to_redis_with_fail_fast(
        host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
        timeout_seconds=3, decode_responses=True)


class _SocketCounter:
    """Counts REAL socket opens: redis.connection.Connection._connect.

    NOT `AbstractConnection.connect` -- redis-py calls that on every command and it
    early-returns when a socket already exists, so counting it over-reports by ~7x and
    hides whether pooling works at all. And not the abstract base's `_connect` either:
    `Connection` overrides it, so patching the base silently counts nothing.
    """

    def __init__(self):
        import redis.connection as rc
        self._rc = rc
        self.n = 0

    def __enter__(self):
        real = self._rc.Connection._connect
        self._real = real
        counter = self

        def counted(conn, *a, **k):
            counter.n += 1
            return real(conn, *a, **k)

        self._rc.Connection._connect = counted
        return self

    def __exit__(self, *exc):
        self._rc.Connection._connect = self._real
        return False


@pytest.fixture(scope="module")
def seeded():
    """A private namespace holding a small fleet and a larger one."""
    from core.comm import roster
    client = _client()
    if client is None:
        pytest.skip("no live Redis on the world endpoint")
    small, large = 2, 12
    for i in range(large):
        roster.heartbeat(NS, f"agent{i:02d}", f"{uuid.uuid4().hex}", phase="idle", client=client)
    yield client, small, large
    for k in client.keys(f"{NS}:*"):
        client.delete(k)


def test_roster_connection_cost_is_flat_in_fleet_size(seeded):
    """P1: connections opened by roster() must NOT scale with the number of rows."""
    from core.comm import roster
    client, _small, _large = seeded

    # Warm every lazy import/singleton first, so the measurement sees steady state and
    # not one-time import cost masquerading as per-row cost.
    roster.roster(NS, client=client)

    rows = roster.roster(NS, client=client)
    assert len(rows) >= 12, f"fixture did not seed a measurable fleet (got {len(rows)})"

    with _SocketCounter() as c:
        roster.roster(NS, client=client)
    opened = c.n

    assert opened <= 2, (
        f"roster() opened {opened} Redis connections for {len(rows)} seats "
        f"(~{opened / max(len(rows), 1):.1f} per seat). A roster read is a READ: it must "
        f"reuse the client it was handed, not mint a connection per row. This is the "
        f"kimi HARD WEDGE of 2026-09-24 -- at 55 seats it cost 113 sockets and 3.3s per "
        f"pass, every 60s, in every runner."
    )


def test_roster_cost_does_not_grow_when_the_fleet_grows(seeded):
    """P2: the SHAPE law. Doubling the corpses must not double the connection cost.

    Stronger than P1 and independent of any absolute budget: it compares the SAME
    implementation against itself at two fleet sizes, so it stays honest even if the
    house later decides a small constant number of connections is acceptable.
    """
    from core.comm import roster
    client, _small, _large = seeded

    roster.roster(NS, client=client)  # warm

    with _SocketCounter() as c:
        roster.roster(NS, client=client)
    before = c.n
    n_before = len(roster.roster(NS, client=client))

    extra = 12
    for i in range(extra):
        roster.heartbeat(NS, f"extra{i:02d}", f"{uuid.uuid4().hex}", phase="idle", client=client)

    with _SocketCounter() as c:
        roster.roster(NS, client=client)
    after = c.n
    n_after = len(roster.roster(NS, client=client))

    assert n_after > n_before, "fixture failed to grow the fleet"
    assert after <= before + 1, (
        f"roster() connection cost grew from {before} to {after} when the fleet grew "
        f"from {n_before} to {n_after} seats. Cost must be flat in fleet size, or every "
        f"watchdog relaunch makes the next pass more expensive -- the feedback loop that "
        f"turned three kimi relaunches into three HARD WEDGE pages."
    )


def test_conductor_gate_pass_cost_does_not_grow_with_the_fleet():
    """P3: the END-TO-END law, at the call site the py-spy stack actually captured.

    evaluate_succession -> _attendance -> attendance -> roster. Pinning only roster()
    would let a future refactor reintroduce the cost one layer up: `attendance` has
    accepted a `roster_rows` snapshot for batch observers all along, and the gate was the
    batch observer that never passed one.

    WHY THIS MEASURES A RATIO AND NOT A BUDGET. The first draft asserted an absolute
    ceiling and failed at 10 with the fix in place, which looked like the fix falling
    short. It was not: under pytest `_AISETUP_TEST_ISOLATED` makes `bus.get_bus()` return
    a FRESH Bus per call instead of its cached one, so `liveness._client` and
    `runner_lock._client` each open a socket every time they are consulted. In production
    that cache holds and the same pass costs 2. An absolute budget here would have been
    measuring the test harness, so the pin measures the gate against ITSELF at two fleet
    sizes -- the harness's constant cancels, and only the SHAPE is asserted.

    It also exercises the branch that matters most. With live seats the roster probe
    returns ATTENDED immediately and the deeper probes never run; it is when seats go dark
    -- the exact condition succession exists for -- that every probe fires. The gate must
    not get more expensive precisely when the fleet is in trouble.
    """
    import time as _time
    from core.comm import conductor_gate, roster
    from core.comm.liveness import _ns

    client = _client()
    if client is None:
        pytest.skip("no live Redis on the world endpoint")

    ns = _ns()
    stale = _time.time() - 100_000.0     # old beats: forces the full probe ladder
    planted = []

    def _plant(n, tag):
        for i in range(n):
            agent = f"gatecost{tag}{i:02d}"
            sid = uuid.uuid4().hex
            roster.heartbeat(ns, agent, sid, phase="idle", client=client, _beat_ts=stale)
            planted.append((agent, sid))

    try:
        _plant(10, "a")
        conductor_gate.evaluate_succession(agent_self="kimi")          # warm
        with _SocketCounter() as c:
            conductor_gate.evaluate_succession(agent_self="kimi")
        before = c.n
        n_before = len(roster.roster(ns, client=client))

        _plant(10, "b")
        with _SocketCounter() as c:
            conductor_gate.evaluate_succession(agent_self="kimi")
        after = c.n
        n_after = len(roster.roster(ns, client=client))

        assert n_after > n_before, "fixture failed to grow the fleet"
        assert after <= before + 1, (
            f"one conductor-gate pass cost {before} connections at {n_before} seats and "
            f"{after} at {n_after}. The gate runs every 60s in every runner; while this "
            f"scaled with the fleet it reached 113 sockets and 3.3s per pass at 55 seats, "
            f"exhausted the 16384-port ephemeral range into TIME_WAIT, and parked the "
            f"runner's MainThread inside a blocking connect."
        )
    finally:
        for agent, sid in planted:
            try:
                roster.go_offline(ns, agent, sid, client=client)
            except Exception:
                pass
            for k in client.keys(f"{ns}:*{agent}*"):
                client.delete(k)
