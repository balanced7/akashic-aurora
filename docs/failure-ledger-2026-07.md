# Failure Ledger — 2026-07

Status: current (2026-07-16)

DANIEL DIRECTIVE 2026-07-16 (verbatim, note `ironman-directive`): *"address all of the system
failures and glitches as they come up and compile a list and work together to resolve those
categories of errors. Every friction point needs to get addressed not worked around (within
reason)."*

**The contract:** this is a LIVING ledger. When any agent hits a system failure, glitch, or
friction point, it gets an entry HERE (as it occurs, not batched later), with a category, a
root-cause hypothesis, and a routing (fix now / gated task / accepted boundary + why). A
workaround without an entry is a defect. Categories get RESOLVED — the entry closes only when
the class can't recur, not when one instance was dodged (fix-root-causes doctrine). Convention:
newest entries at top of each category; closed entries move to the CLOSED section with their
fix receipt.

## Category index

- **C1 Seat & lease lifecycle** — consumer seats, wake seats, runner locks, TTL vs liveness
- **C2 Concurrent-write collisions** — two writers, one file/key
- **C3 CLI ergonomics footguns** — quoting, arg parsing, cwd, silent clipping
- **C4 Process/launcher state** — supervisor loses track of children
- **C5 Ledger state machine** — transitions that block legitimate work
- **C6 Message/lane integrity** — dual-write stragglers, redelivery, count drift
- **C7 Harness-level quirks** — the seat's tools misbehaving (tracked; often not ours to fix)

---

## OPEN

### C1 Seat & lease lifecycle

**C1-1 · Consumer seat held by dead sibling for full TTL** (2026-07-15 night, claude seat)
A prior session (29f15d47) died holding the `claude` consumer seat; the claim timestamp was
static (no refresh) yet the seat blocked all consumes for the remaining ~17 min of its 1800s TTL.
Cost: my wake-arm loop (C1-2) had no drain path; three stop-hook cycles.
Root cause: seat freeing is TTL-only — a *dead* holder is indistinguishable from a *quiet* one.
Prior art: k8s node leases (holder heartbeats; a controller frees leases whose holder object is
gone), fencing tokens (Redlock discussions): liveness = lease renewal, not lease existence.
**Routing: FIX NOW (tonight, C1 fix #1)** — the seat-held error path verifies holder liveness
(session-pid probe) and frees a provably-dead holder's seat immediately, with an audited event.
Never force-frees a live holder (fencing safety).

**C1-2 · Wake-arm insta-loop on undrained inbox** (2026-07-15 night ×3 stop-hook cycles)
Arming the wake seat with wake-worthy stale mail present exits instantly; the stop hook demands
a re-arm; loop. Root cause: arm-before-drain ordering + C1-1 blocking the drain.
**Routing: TRACKED (T075-γ/T077 daemon owns arm/consume ordering) + tonight's C1-1 fix removes
the blocked-drain leg. Operational rule until then: consume-then-arm (proven live tonight).**

### C2 Concurrent-write collisions

**C2-1 · Two agents clobbered the same new test file** (2026-07-16, W4: both wrote
`tests/test_t081_w4_trace_collapse.py`; deepseek's write clobbered claude's — silent, caught by
a file-modified notice.)
Root cause: advisory locks cover *existing hot files*; NEW files have no lock and we had no
per-lane naming convention. Lesson `w4_two_writer_test_clobber` captured.
**Routing: convention SHIPPED (per-surface test names) + PROPOSE guard: guard_write /
Write-hook warns when creating a file another agent referenced on the bus in the last hour
("name collision likely"). Gated small slice; needs deepseek's half (his ToolBox write door).**

### C3 CLI ergonomics footguns

**C3-1 · bifrost-send text swallowed CLI flags** (2026-07-16: a message BODY containing
`--sources-json` got parsed as arguments after PowerShell quote-mangling; send failed with an
argparse error.)
Root cause: message text rides argv; anything flag-shaped in prose is hostile input to argparse,
and PowerShell quoting multiplies the risk. Prior art: `git commit -F <file>` / `--` end-of-flags.
**Routing: FIX NOW (tonight, C3 fix #2)** — `bifrost-send --text-file PATH` (+ honor `--` as
end-of-options) so long/flag-bearing bodies never ride argv. Complements T064 (handoff --note
clipping → file overflow).

**C3-2 · `Shell cwd was reset` on every PowerShell call** (all session)
Harness resets cwd between calls; every CLI invocation needs a `Set-Location` prefix.
**Routing: MITIGATED by T081-W2 (MCP-native door, awaiting Daniel's one-command apply) — the
shell-out dance disappears when the door attaches. Residual: acceptable harness boundary (C7).**

### C4 Process/launcher state

**C4-1 · UI launcher lost track of a live runner** (2026-07-16: launcher/status showed all
deepseek rows `never_launched`/empty while runner_lock showed pid 5320 alive; the UI process had
restarted and its in-memory `_procs` map was gone.)
Root cause: Launcher tracks children in process memory; a UI restart orphans the mapping (the
session-file restore exists but only restores *tags on click*, not live-process adoption).
Prior art: systemd re-reads unit state on daemon-reexec; supervisord reattaches via pidfiles.
**Routing: GATED SLICE (propose)** — Launcher.__init__ rehydrates: for each spec, if
runner_lock/pid probe shows a live holder, adopt it as `running` (read-only adoption; kill/revive
still work via pid). Medium slice; rides T030 (launcher-owned lifecycle).**

### C5 Ledger state machine

**C5-1 · T081 done-transition blocked by a PARKED in-progress task** (2026-07-16: `task done
T081` blocked — T075 is in_progress but explicitly PARKED behind T047; the one-in-progress rule
can't express "parked".)
Root cause: the state machine lacks a parked/paused status, so a deliberately-shelved wave
permanently occupies the single in_progress slot.
Prior art: issue-tracker state machines (Jira "blocked/on-hold" as first-class states).
**Routing: FIX NOW (tonight, C5 fix #3)** — conductor gains `park <tid> --reason` /`unpark`
(park = in_progress→parked, excluded from the serialize-check; unpark reverses). Migrate T075 to
parked citing its own PARKED note. Then T081 transitions cleanly.**

### C6 Message/lane integrity

**C6-1 · Unread-count drift across gauges** (whisper 8 vs sync 10 vs peek 19, all session)
**CLOSED 2026-07-16 → see CLOSED section (W8A).**

### C7 Harness-level quirks (tracked, usually not ours to fix)

**C7-1 · Glob `scripts/*.py` returned nothing while `**/bifrost_ui.py` matched** (2026-07-15).
Harness tool quirk; cost one extra probe. **Routing: ACCEPTED BOUNDARY (log-only) — not Aurora
code; workaround (recursive patterns) is zero-cost. Revisit only if it recurs with cost.**

**C7-2 · Browser screenshot times out on the SSE-heavy UI page** (2026-07-15 ×2).
get_page_text works; screenshots stall. **Routing: ACCEPTED BOUNDARY (log-only), same test.**

---

## CLOSED (fix receipts)

**C6-1 unread-count drift** → CLOSED by T081-W8A (2026-07-16): gauges now NAME their denominator
(whisper `mail: N unread (work-lane|all lanes)`; sync `N unread (all lanes, peek)`) via one shared
scope check. Counts explained, not forced to agree. Receipt: 6 pins + live renders.

**(pre-ledger) Trace spam burying mail** → CLOSED by T081-W4 both surfaces (shared
`render_collapsed`; live receipt: a 17-message consume rendered as 2 lines).

**(pre-ledger) Heal wolf-cry (4867 orphans)** → CLOSED by T081-W5 3-way honest heal; residual
real signal (259 unknowns + durable-drift question) is T082's charter, not noise.

**(pre-ledger) 189h dangling episode** → CLOSED by T081-W8B (SessionEnd auto-close, empty-safe,
both paths unified).
