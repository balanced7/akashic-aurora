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


def test_conductor_gate_pass_cost_is_bounded(seeded):
    """P3: the END-TO-END law, at the call site the py-spy stack actually captured.

    evaluate_succession -> _attendance -> attendance -> roster. Pinning only roster()
    would let a future refactor reintroduce the cost one layer up (attendance already
    accepts a `roster_rows` snapshot for exactly this reason and the gate never passes
    one). The budget is generous on purpose: this pin is about ORDERS OF MAGNITUDE.
    """
    from core.comm import conductor_gate

    conductor_gate.evaluate_succession(agent_self="kimi")  # warm

    with _SocketCounter() as c:
        conductor_gate.evaluate_succession(agent_self="kimi")
    opened = c.n

    assert opened <= 8, (
        f"one conductor-gate pass opened {opened} Redis connections. The gate runs every "
        f"60s in every runner; at the measured 113 it exhausts the 16384-port ephemeral "
        f"range into TIME_WAIT and the connects themselves begin to block."
    )
