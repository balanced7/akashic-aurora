# Drill receipt: roster connection reuse vs the kimi HARD WEDGE — 2026-09-24 23:03–23:42

Incident: three HARD WEDGE pages for kimi after the 20:26 reboot (sessions
kimi#19772, kimi#53044, kimi#51452), each "non-idle phase 'running' ... DEAD
pulse", each followed by a watchdog relaunch (~22:18 and ~22:34).

Commits: `2c7a8587` (RED pins) → `e0f3aabc` (fix) → `c44ad20d` (wishes).
Raw samples: `2026-09-24-roster-connection-reuse.jsonl` beside this file.

---

## 1. What was measured, and one correction to the first number

One conductor-gate pass, live fleet, instrumented at
`redis.connection.Connection._connect`:

| | before (`ec169def`) | after (`e0f3aabc`) |
|---|---|---|
| socket opens per gate pass | **113** | **2** |
| wall time per pass | **3.3 s** | **0.9 s** |
| seats in roster | 55 | 58 |
| `Bus` objects built | 111 | 1 |

Attribution of the 113: **111 were `Bus.__init__` → `bus._connect`**
(`roster.py:194`), one per roster row per `roster()` call, with `roster()`
called twice per pass. The other two were the roster's own client.

**A correction worth recording, because the wrong number is easy to get and
looks authoritative.** My first measurement said 780 sockets per pass. That
counted `AbstractConnection.connect`, which redis-py calls on *every command*
and which early-returns when a socket already exists — it over-reports by about
7x. The opposite error is just as easy: `AbstractConnection._connect` counts
**zero**, because `Connection` overrides it. Only
`redis.connection.Connection._connect` is the real socket. A pooling sanity
check settles which instrument is honest: 50 sequential commands on one client
must open **0** new sockets, and they do.

Pooling was never broken. One client per process was always enough; the code
simply built 111 of them.

## 2. Why it wedged instead of merely wasting

Every one of those sockets dials `localhost:16379`, which resolves to `::1`,
where **wslrelay.exe** (pid 39492) holds a more specific bind than Docker's
own `[::]` listener and therefore wins. Each close parks an ephemeral port in
TIME_WAIT for the Windows 2MSL. Measured tonight:

- dynamic port range: **16384** ports (49152+), and the v4/v6 pools are separate
- **1,793** TIME_WAIT against this one port ten minutes after a cold boot
- Tcpip **4227** (local endpoint reused too soon) logged at 08:25 the same day

Under that pressure a connect blocks instead of returning, and 111 blocking
connects at `socket_connect_timeout=3` is up to 5.5 minutes with the runner's
MainThread parked inside `conductor_gate` — the py-spy stack captured from pid
50304, and the shape the doctor pages as "non-idle phase 'running' ... DEAD
pulse". The beat thread starves for the same reason, which is what turns
`beating_unproven` into the page.

**The loop that made it escalate:** 50 of the 55 roster rows were DEAD seats
(17 claude, 17 deepseek, 17 kimi; 4 LIVE). Every watchdog relaunch appends a
row, so each recovery made the next pass more expensive. The cure fed the
disease.

## 3. The fix

Three changes, each removing a connection that was never needed:

1. `roster._have_summary` hands the `Bus` **the client it already has**. `Bus`
   has always taken a `client` parameter; the call site just never passed one.
2. One `Bus` per **agent** per roster read, not one per **row**, via a cache the
   caller owns and scopes to a single read — deliberately not module-level, so
   no Bus outlives the observation instant it was built for.
3. `liveness.attendance` reads the roster **once** per call (it sat inside the
   `_id_forms` loop, so any id with a session suffix rebuilt the census twice),
   and `conductor_gate` reads **one** census per pass and passes it to every
   attendance call. `attendance` has accepted `roster_rows` for batch observers
   all along; the gate was the batch observer that never passed one.

Besides the sockets, (3) makes a succession decision judge every seat at the
same observation instant instead of stitching one verdict from a 22:18 census
and the next from a 22:19 one.

**Behaviour preservation, checked explicitly:** with the pre-fix shapes restored
by monkeypatch, the roster returns 60 rows and the fixed path returns 60 rows —
**zero differences across every field including the `have` summaries**. Cost
changed, behaviour did not. And `roster()` swallows its own failures and returns
`[]` rather than raising, so hoisting the read out of the candidate loop cannot
turn a transient blip into a false death claim: pre-fix, every candidate got
`[]` too.

## 4. The pins, and why P3 was rewritten before it went green

`tests/test_roster_connection_reuse.py`, red in `2c7a8587`:

- **P1** roster() connection cost is flat in fleet size — red at 12-for-12 seats
- **P2** growing the fleet must not grow the cost — red at 12→24 for 12→24 seats
- **P3** one gate pass must not scale with the fleet

P3 first asserted an **absolute ceiling** and failed at 10 *with the fix in
place*, which read like the fix falling short. It was not. Under pytest,
`_AISETUP_TEST_ISOLATED` makes `bus.get_bus()` return a fresh Bus per call
instead of its cached one, so `liveness._client` and `runner_lock._client` pay a
socket every time they are consulted; in production that cache holds and the
same pass costs 2. **The budget was measuring the test harness.** P3 now
compares the gate against itself at two fleet sizes so the harness's constant
cancels.

Verified it still discriminates: with the pre-fix shapes restored, P3 reads **42
connections at 10 seats and 72 at 20** and fails.

P3 plants STALE seats on purpose. With live seats the roster probe returns
ATTENDED immediately and the deeper probes never run; it is when seats go dark —
the exact condition succession exists for — that the full ladder fires. The gate
must not get more expensive precisely when the fleet is in trouble.

**Regression:** 59 tests across roster, liveness, conductor and gate audit pass.
A wider `-k` sweep showed 11 failures in the main working tree; none are mine.
Isolated in clean worktrees at `ec169def` and `e0f3aabc`: 6 already fail at
base, 4 live in **untracked** peer test files, and 1
(`test_alias_composition_is_honest`) passes at both base and HEAD and fails only
in the dirty tree. The main tree carries other seats' in-flight edits, including
an uncommitted `EXPECTED_SILENT` change to `liveness.py` — staged around, not
committed, and still intact in the tree.

## 5. Host evaluation: should the default become 127.0.0.1?

Proposed 09-11 (`core/world.py:137` plus `redis_connection.py:71`). Measured
both paths tonight:

| | `localhost` (→ ::1 → wslrelay) | `127.0.0.1` (→ com.docker.backend) |
|---|---|---|
| same Redis? | run_id `20aa8d83…`, dbsize 56365 | **identical** run_id and dbsize |
| connect+PING median | 4.21 / 4.66 ms | 4.24 / 4.11 ms |
| p95 | ~27 ms | ~27 ms |
| TIME_WAIT per 100 connects | ~100 (on the ::1 pool) | 100 (on the v4 pool) |
| pool occupancy at rest | ::1 **8.6%** of 16384 | v4 **1.4%** of 16384 |

**Recommendation: do not make it the default, and not as a hardcode.** The
numbers do not support it as a capacity fix:

- no latency benefit — the medians are a wash
- no socket reduction — it **relocates** TIME_WAIT, it does not reduce it
- wslrelay adds **no host-side amplification**: it holds 46 inbound sockets on
  16379 and **zero** outbound ephemeral ones (it forwards into WSL over
  hvsocket), so the relay hop is not doubling port usage as was assumed
- the wedge cause is fixed independently — 113 → 2 per pass is a ~98% cut, which
  is where the headroom actually came from
- `localhost` carries dual-stack fallback that a literal IP does not; a checkout
  whose Redis binds only `::1` would break

**The one argument that survives** is robustness, not capacity: wslrelay is the
source of the documented half-open pathology (`redis_connection.py` records kimi
holding 12 ESTABLISHED sockets Redis had no record of, main loop blocked in
xread 12+ hours). Dialing Docker's listener removes that hop. But
`health_check_interval=30` already defends against it, and the change would move
the whole fleet's transport.

If that hop is worth removing, it should be an **IPv4-preferred resolution with
fallback**, not a hardcoded literal, landed as its own slice with its own drill.
Daniel's call; the measurement is here either way.

---

## 6. The drill

Method: stop the pre-fix runner at a safe point (py-spy confirmed it idle in
`xread`), let its **daemon** respawn it so the daemon's own services are never
interrupted, verify the new process stamps HEAD, then watch.

- 23:03:28 — stopped pid 52792 (pre-fix)
- 23:03:29 — daemon pid 22980 respawned it as **pid 45764**, one second later
- verified: `kimi#45764-ki` LIVE, `code_sha=e0f3aabc0c15`, `code_state=current`,
  matching HEAD

py-spy on the fixed runner, 14 samples 15 s apart: **14/14 in the normal
`_read_from_socket` xread wait, 0/14 inside `conductor_gate` or `roster`.**
Stated honestly, this is supporting evidence rather than proof — pre-fix the
gate was only 5.5% of wall time, so roughly one sample would land there by
chance anyway. The 113 → 2 measurement is the load-bearing number.

<!-- DRILL TALLY APPENDED BELOW ON COMPLETION -->

**Result: PASS, with three pages in the window that all name DEAD incarnations.**
Stated plainly because the raw doctor output looks like a failure and is not.

| | |
|---|---|
| drill window | 23:04:24 → 23:34:46 (**30.4 min**) |
| runner pid | **45764 throughout**; `survived_without_respawn: True` |
| doctor checks | 6 — five at 0 page-grade, one page (below) |
| runner established conns | 7–10, flat |
| TIME_WAIT (::1) during drill | 862 – 1911 |
| doctor now | **0 page-grade** |

**Zero pages named the live seat while it was live.** The three that fired:

1. **23:04:26 — `kimi#52792-ki`.** The predecessor I stopped at 23:03:28 to start
   the drill. Its worklive record lingered in 'running'. Cleared by 23:08:38.
2. **23:35:17 — `deepseek#45604-de`.** Its successor (pid 56164) had already been
   running since **23:32:48**, so this page also arrived after the incarnation
   was gone. That successor's parent is the daemon, so deepseek was respawned by
   its supervisor rather than self-restarting — I cannot tell from here whether
   it wedged or exited, and I am not claiming it as evidence either way.
3. **23:39:28 and 23:41:33 — `kimi#45764-ki`, the drilled seat.** This one looked
   like the fix failing. It is not, and the proof is process lineage: the
   successor **pid 53824 started 23:38:36 with parent = 45764**. A wedged process
   cannot spawn its own successor. 45764 reached a turn boundary and executed the
   stale-code self-restart ceremony — three commits had landed behind it
   (`c44ad20d`, then `f90b6ac6` and `9328499a` from other seats mid-drill),
   hitting `_min_behind()=3` with uptime past the 900 s floor. It rotated exactly
   as designed after **35.1 minutes** of life.

So all three are ROTATION/RESTART TOMBSTONES, the already-known
`runner_heartbeat_hardcodes_running_so_rotation_kills_page_as_hard_wedge` class:
`roster.heartbeat` writes `phase='running'` unconditionally, so a departed
incarnation's `seatseen` record keeps `phase='running'` with `offline_ts=None` —
verified directly for `kimi#45764-ki` — and the doctor reads that as "worker died
inside the turn". `maybe_self_restart` *does* set worklive to "restarting", but
the seatseen record the page reads is written by a different path and never
learns. Pre-existing; untouched by this work.

## 7. Two things this drill changed my mind about

**The page count tonight is not a clean count of wedges.** Three tombstone pages
fired in 40 minutes from ordinary restarts. The three original pages
(kimi#19772, kimi#53044, kimi#51452) were each followed by a relaunch, which is
exactly the shape that manufactures a tombstone — so some of them may have been
tombstones of the relaunch rather than independent live wedges. **The connection
storm is not in doubt**: the py-spy dump of pid 50304 caught MainThread blocked
inside a Redis connect under `conductor_gate`, which is a live stall, observed.
But "three pages" should not be read as "three wedges" until the tombstone class
is fixed.

**Coverage boundary, so this PASS is not over-read.** It proves the fixed runner
survives 30 minutes on a *quiet* fleet and rotates cleanly. It does **not** prove
the wedge class is closed, because it never reproduced the condition that caused
it: ephemeral-port exhaustion. The load-bearing evidence is the direct
measurement — 113 → 2 sockets and 3.3 s → 0.9 s per pass — not this drill.

## 8. Still owed

- The tombstone class: mirror the live worklive phase into `roster.heartbeat`, or
  treat an incarnation with a live lock-holding successor as SUPERSEDED rather
  than paging it. Three false pages in 40 minutes is a real alarm-fatigue cost,
  and it corrupts the evidence for exactly this kind of investigation.
- Two wishes filed in `c44ad20d`: the doctor cannot see port pressure, and a read
  path's connection cost is invisible until it exhausts the machine.
- Fleet-wide, only kimi has been restarted onto the fix; every other long-lived
  process still pays the old cost until it rotates. Fleet connect rate measured
  mid-drill: **8.73 conn/s** (524/min) with kimi fixed and deepseek not.
- The 127.0.0.1 question is Daniel's call (section 5); nothing is blocked on it.
