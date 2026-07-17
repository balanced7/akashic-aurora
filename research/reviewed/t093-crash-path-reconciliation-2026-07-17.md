# T093 Crash-Path — Reconciliation (Fable reconciler) — 2026-07-17

Status: reconciliation of two independent halves (analysis only; NO shared-code edits).
Halves: research/drafts/t093-crash-path-fable-2026-07-17.md (Fable, class/doctrine lens) +
research/drafts/t093-crash-path-deepseek-2026-07-17.md (DeepSeek, ship.py surgical-patch lens).
Charter (codex_root): minimum existing-supervisor reuse giving durable log + atomic receipt +
out-of-band deadline, surviving controller/app-server loss, kill-drillable without another
in-band wait; FLAG false acceptance claims (esp. SIGKILL receipts). Reconciler lane = Fable.

## 1. CONVERGENCE (independently derived by both — strongest signal)

1. **The machinery already exists; the fix is CONNECTING, not building.** DeepSeek's capability
   matrix (runner / daemon / ManagedChild all have durable stdout, independent deadline, heartbeat,
   receipt, cancel) = Fable's "reuse T086 supervision; ship.py hung precisely because it ran as an
   unsupervised exec cell." Both refuse a new supervisor.
2. **The deadline must be OUT-OF-BAND.** DeepSeek: "the timeout lives OUTSIDE the cell/channel."
   Fable: "a guard that CANNOT share fate — parent OS timer." Same law: the guard must not ride the
   channel it guards. This is the T093 root (the 20m timeout was in-band and shared fate).
3. **Durable outcome that survives channel/process death.** DeepSeek's `--log` + `--receipt` with
   atomic write = Fable's "durable out-of-band outcome." Local file, survives controller/app-server
   loss (the charter requirement).
4. **This slice bounds blast radius; the cell-layer root is a SEPARATE problem.** DeepSeek §7.5 =
   Fable's "N1 bounds blast radius; C7-4 keeps fixing frame-loss SOURCES." Agreed, do not conflate.

## 2. COMPLEMENTARY (they compose into one build; each supplies what the other under-specifies)

- **DeepSeek supplies the concrete durable-OUTCOME surface** (ship.py `--log`/`--receipt`/SIGTERM,
  ~25 lines, atomic tmp+os.replace, the exact patterns to borrow from ManagedChild/_stable_token/
  _write_exit_summary). This is the buildable pilot.
- **Fable supplies the missing ENFORCER + the class framing.** DeepSeek's "independent deadline"
  is described as caller-side polling of the receipt — but his half never names WHO force-kills, and
  a caller poll-loop that itself uses an in-band wait re-creates the exact T093 bug. Fable's Part A
  (parent `subprocess.run(timeout=HARD)`, OS-timer enforced) IS that enforcer, frame-independent.
- **Neither alone suffices:** receipt-without-enforcer = you can SEE it's stuck but nothing kills it;
  enforcer-without-receipt = you kill it but the outcome stays unknowable. **T093 fix = receipt (durable
  outcome) + parent-OS deadline (out-of-band kill) together.**

## 3. THE LOAD-BEARING FLAG codex_root asked for — DeepSeek D1 is a FALSE ACCEPTANCE CLAIM

**D1 ("Kill-9 receipt survives") asserts: `os.kill(pid, SIGKILL)` → `receipt["verdict"] == "killed"`.
This is UNSATISFIABLE. [CERTAIN]** SIGKILL cannot be caught — no handler runs — so NOTHING writes
`verdict="killed"` after a SIGKILL. DeepSeek's own §5.2 admits "SIGKILL → no handler possible," which
directly contradicts D1's assertion. After SIGKILL the receipt on disk shows its LAST durable write:
`"running"` (start) or a gate-boundary update — never `"killed"`.

**The correction (and it IS the reconciliation's sharpest point):** a killed process CANNOT
self-report its death. The `"killed"` verdict must be the EXTERNAL WATCHER's INFERENCE from
(stale `"running"` receipt + dead pid), not a self-written field. This is exactly Fable's doctrine —
the verdict, like the deadline, must come from out-of-band. Corrected drills:
- **D1' (SIGKILL → external inference):** SIGKILL the child; assert the receipt shows the last
  durable state (`running`/`gate:N`) AND a separate watcher, seeing pid dead + receipt stale,
  classifies it `killed`. The verdict is the watcher's, never the corpse's.
- **D2 (SIGTERM → self-report) stays valid:** SIGTERM is catchable, so the handler CAN write
  `verdict="killed"`. Keep D2 but LABEL it the catchable path (it does NOT prove the SIGKILL path).
Conflating D1 and D2 is the trap: the design must not claim SIGKILL self-reports because SIGTERM can.

**Second, quieter false-acceptance risk:** any drill whose deadline is enforced by a `wait()` on the
child's own channel silently re-creates T093. Add Fable's **KD4 (timeout-masking regression):** mock
the child's channel as permanently wedged; assert the guard STILL fires (parent OS timer / external
`os.kill` from a separate process). A drill that can't fire under a wedged channel is testing nothing.

**Sound as-is:** D3 (durable-log survives pipe death) and D4 (torn-file immunity via os.replace —
atomic on one filesystem) are correct pins; keep both. Specify D3's kill signal (SIGKILL, to prove
the last fsync'd line survives).

## 4. BUILD-SPEC RECOMMENDATIONS (codex_root's ask)

Minimum reuse giving durable log + atomic receipt + out-of-band deadline, controller-loss-survivable,
kill-drillable without an in-band wait:

1. **Durable outcome (adopt DeepSeek §3 verbatim):** ship.py `--log FILE` (line-buffered, fsync at
   gate boundaries) + `--receipt FILE` (atomic tmp+os.replace; states: start `running` → optional
   monotonic heartbeat → exit `ok|fail|timeout`) + SIGTERM handler writing `killed` on the CATCHABLE
   path. ~25 lines, opt-in, zero-flag path byte-identical. Local file ⇒ survives Redis/controller loss.
2. **Out-of-band ENFORCER (add Fable Part A):** the caller runs ship.py as `subprocess.run(cmd,
   timeout=HARD, ...)` — parent OS timer, frame-independent. On TimeoutExpired: kill the tree, then
   READ the receipt for the durable outcome. This is the piece DeepSeek's "caller polls the receipt"
   leaves unnamed. Package as `core/comm/deadline.py: run_with_hard_deadline()` so any exec/toolcall
   site reuses it — but ship.py is the pilot.
3. **The verdict for an uncatchable kill is an INFERENCE, not a self-report** (§3): the external
   watcher reuses `runner_lock.free_if_dead`'s evidence ladder (receipt-age < grace → alive;
   stale + dead pid → killed; no receipt → not started). Both halves already cite this ladder.
4. **Kill-drillable without an in-band wait:** every drill enforces its deadline via a parent OS
   timer or `os.kill` from a SEPARATE process — never a `wait()` on the wedged channel. Drills:
   D1' (SIGKILL→inference), D2 (SIGTERM→self-report, labelled), D3 (log survives pipe death, SIGKILL),
   D4 (torn-file immunity ×20), KD4 (timeout-masking regression). All RED before, GREEN after.
5. **Sequencing:** ship.py pilot FIRST (DeepSeek's surgical surface, lowest risk), THEN extract the
   pattern to `core/comm/deadline.py` + the receipt-watcher for other exec/toolcall sites (both halves'
   escalation path — DeepSeek's "extract to gate_runner.py" = Fable's generalized wrapper). Reuse
   ManagedChild's drainer + free_if_dead ladder for the watcher; do NOT author new supervision (T086
   owns lifecycle).
6. **M1-PV owed at build time:** DeepSeek's capability matrix cites _stable_token (atomic write),
   _write_exit_summary, ManagedChild drainer, clean_death tombstone-first, free_if_dead ladder. I
   spot-confirmed the supervision primitives exist (bifrost_daemon heartbeat, free_if_dead,
   daemon_state <=8s fact); the build slice's M1-PV must confirm each BORROWED pattern resolves at the
   cited symbol before the patch cites it (the T049 fence-v2 citation gate).

## 5. CONTRAINDICATIONS (union of both halves, de-duplicated)

1. Do NOT fix an in-band timeout with another in-band timeout (the guard must not share the channel).
2. A killed process CANNOT self-report — the SIGKILL verdict is ALWAYS an external inference (the D1 fix).
3. Heartbeat = MONOTONIC liveness, never a completion proxy (Fable KD2 — don't false-kill a slow-but-alive op).
4. Do NOT build a new supervisor / do NOT make ship.py a daemon — reuse ManagedChild/daemon/free_if_dead (both halves).
5. Local file, NOT Redis, for the receipt — it must survive a controller/Redis outage (DeepSeek §7.2).
6. This slice bounds blast radius; it does NOT fix the cell/exec-frame ROOT (C7-4's per-source handle work). Don't sell one as the other.

## 6. VERDICT

**CONVERGENT on the fix shape; COMPLEMENTARY in coverage; ONE genuine correction (D1 false
acceptance) + one added regression (KD4).** Build spec = DeepSeek's ship.py durable-outcome patch
+ Fable's parent-OS out-of-band enforcer + the corrected D1'/KD4 drills, ship.py-first then extracted.
No divergence requiring Daniel's tie-break. Ready to register as a T093 build slice citing this doc,
at Daniel's gate. codex_root: this is analysis only; no code was edited.

## 7. BUILD-GATE AMENDMENT -- controller loss is a second supervision boundary

Status: **GOVERNING AMENDMENT** (codex_root, after M1-PV + adversarial Windows drills).
This section narrows and supersedes section 4 wherever they conflict. The original reconciliation
correctly joins durable outcome to an external deadline, but its proposed caller-side
`subprocess.run(..., timeout=HARD)` does **not** satisfy T093's registered acceptance that a job
survive app-server/controller loss.

### A. One invalidated claim

`subprocess.run(timeout=HARD)` is out-of-band relative to its *child's output stream*, but the
wrapper is still a descendant of the controller that invoked it. It can enforce the deadline while
that caller process remains alive; it cannot enforce anything after recursive controller-tree
cleanup kills both wrapper and child. Waiting for that wrapper also leaves completion delivery on
the original tool-call channel. Therefore it is a useful inner primitive, **not the durable launch
boundary** and not the T093 fix by itself. Confidence: CERTAIN; grounding: live process-tree drills.

### B. Windows receipts that separate the two bars

The audit used unique job ids/PIDs and cleaned up every probe:

1. `CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS` survived direct parent `TerminateProcess`.
2. The same detached shape did **not** survive `taskkill /PID <controller> /T /F`.
3. `Invoke-CimMethod Win32_Process.Create` launched marked Python pid `68444` under
   `WmiPrvSE.exe` pid `65244`; recursive `taskkill /T /F` of controller pid `12476` did not kill
   the marked child, and its completion marker was observed before cleanup. This host required no
   elevation.

Those are different guarantees. The receipt and UI must name them:

- `recursive-controller-tree` -- supervisor was brokered out of the controller's process tree.
- `direct-parent-only` -- detached fallback; loud degradation, never described as app-server-safe.

### C. Revised minimal build contract

1. **Immutable launch spec first.** `scripts/run_job.py launch` atomically writes a local spec/receipt
   under ignored `state/jobs/` before process creation. It contains job id, argv, cwd, deadline,
   log path, receipt path, controller pid, and a redacted/safe environment snapshot. The command
   returns a launch receipt immediately; it never waits for job completion.
2. **Out-of-tree supervisor + watchdog siblings on this Windows host.** Strict/default launch asks
   WMI `Win32_Process.Create` to start `py -u scripts/run_job.py _watchdog --job-id ...` and
   `py -u scripts/run_job.py _supervise --job-id ...` as independent brokered siblings. The
   watchdog is started first; worker launch is forbidden until its ready receipt exists. Commands
   are read from the already-durable spec, avoiding quoting and secret-bearing scheduled-task
   artifacts. If WMI is unavailable, strict launch fails loudly. An explicitly requested detached
   fallback may run, but stamps `direct-parent-only`.
3. **No job pipes point at the controller.** The supervisor opens durable UTF-8 log files itself and
   sends child stdout/stderr directly to regular files. Atomic temp+fsync+`os.replace` applies to
   latest-state JSON, not to the append-only logs. The state directory separates immutable
   `spec.json`, broker-owned `launch.json`, supervisor-owned `status.json`, and watchdog-owned
   `watchdog.json`, preventing competing writers from tearing or overwriting one another.
4. **Independent deadline.** The watchdog owns the shared monotonic hard deadline and validates the
   worker PID plus process-creation identity before any kill. A wedged child *or a dead supervisor*
   cannot mask it. Deadline expiry first publishes the cooperative cancel marker, waits a bounded
   grace, then kills the uniquely identified child tree and reports `deadline_exceeded` itself.
5. **Quiesce-first cancel.** `cancel` atomically writes a request. Children receive
   `AKASHIC_JOB_CANCEL_FILE`; cooperating commands exit during grace. Force is a recorded fallback,
   never mislabeled graceful. `ship.py` checks the marker between gates so cancellation cannot drift
   from a completed test gate into commit/push.
6. **Fresh-controller recovery.** `status`, `cancel`, and log inspection reconstruct solely from
   disk by joining the four records. If `status.json` has a stale supervisor heartbeat but the
   watchdog remains fresh, status says `supervisor_lost` while keeping `deadline_enforced=true`;
   the watchdog still resolves cancel/deadline. If both guards are stale, it reports
   `supervision_lost`, `deadline_enforced=false`, and never invents an exact exit code.
   SIGKILL/forced-exit verdicts are always supervisor/watchdog inferences.
7. **`ship.py` pilot.** `--durable` delegates its own non-durable invocation to `run_job.py`, emits
   the immediate launch receipt, and exits. A hidden child marker prevents recursion. Zero-flag and
   ordinary `--dry-run` behavior stay compatible; `--durable --dry-run` exercises the real recovery
   path without committing.

### D. M1-PV -- borrowed facts resolved against the live tree

- `scripts/ship.py:61-63` currently inherits stdout and blocks in raw `subprocess.run`; there is no
  durable outcome or process owner.
- `scripts/bifrost_child.py:178-195` owns child pipes and in-memory drain state;
  `:224-237` terminates only its direct handle. It supplies patterns, not restart reconstruction.
- `core/comm/launcher.py:373-409` similarly owns Popen handles/pipes in memory, and
  `:620-660` monitors them in a daemon thread. Its saved session roster is not a per-job receipt.
- `scripts/bifrost_daemon.py:45-62` supplies the atomic temp+replace pattern.
- `scripts/bifrost_runner_deepseek.py:753-766` proves a thread deadline can report timeout but cannot
  cancel a blocked worker thread; the process must remain the hard kill unit.

Verdict: existing components are pattern donors, but none has the registered T093 combination of
immediate durable launch, out-of-tree ownership, fresh-process status/cancel, and a deadline that
survives supervisor loss. The one-shot supervisor/watchdog pair is the smallest missing composition;
neither respawns work or becomes a second fleet daemon, and no Bifrost consume path moves.

### E. Pre-registered RED/kill bars

`tests/test_t093_durable_job.py` must be committed while RED before implementation and pins:

1. launch returns immediately and a fresh process can query the final receipt;
2. recursive controller-tree kill does not kill the WMI-brokered supervisor/job;
3. a wedged child is force-resolved by the watchdog within deadline + grace;
4. slow work below its hard deadline completes and is not killed;
5. cooperative cancel quiesces before force and prevents later gates;
6. repeated concurrent reads never see torn JSON;
7. external child kill is reported by the supervisor as an unattributed nonzero exit, never
   self-reported or overclaimed as distinguishable from `sys.exit(1)`;
8. supervisor loss is loud while the independent watchdog still enforces the deadline;
9. duplicate launch with one deterministic id executes the worker exactly once;
10. real `ship.py --durable --dry-run` completes and is recoverable through a fresh status process.

All waits in the battery are bounded short polls over durable state; no test's only timeout or
completion receipt rides the child output channel.

### F. Honest residuals

- A broad kill by image/name, WMI service failure, machine reboot, disk failure, or deliberate kill
  of controller plus both brokered guards defeats this local one-host design. The durable last
  receipts/logs still bound uncertainty; restart-after-reboot is outside T093.
- WMI is the verified Windows broker, not a cross-platform doctrine. POSIX must use an equivalent
  external service/session owner and pass its own controller-tree drill before claiming parity.
- Heartbeats prove guard liveness, not semantic job progress. The hard deadline is explicit;
  callers must size it for the slowest legitimate gate. `log_bytes` is observability, never an
  automatic deadline reset.
- Windows `taskkill /F` gives Python's parent the same return code (`1`) a program can choose with
  `sys.exit(1)`. Without an audited kill request, the supervisor must say
  `unattributed_nonzero_exit`; exact external-kill attribution would be invented evidence.

## 8. ADVERSARIAL BUILD-GATE AMENDMENT -- launch gaps, outcome priority, publish fence

Status: **GOVERNING AMENDMENT** (codex_root, after the first implementation passed 11 focused
drills but failed an independent crash-window audit). This section narrows section 7. Fable and
DeepSeek initially returned SHIP, then independently affirmed the six failures below after the
Codex audit supplied exact windows; Fable withdrew its SHIP verdict. No implementation commit may
land until the new RED receipts are committed first.

### A. Spec-first does not mean retry-safe

There is an unavoidable interval after `spec.json` becomes durable and before the WMI broker has
durable guard self-receipts. A same-id retry must **not** silently launch a second guard generation:
a delayed first WMI launch could then execute the worker twice. The v1 recovery contract is:

1. before the spec's bounded startup deadline, an exact same-id retry reports `launching`;
2. after that deadline, if no live/fresh guard self-receipt exists, primary state becomes terminal
   `launch_failed`, `deadline_enforced=false`, with an explicit `retry_with_new_job_id` remedy;
3. if guard self-receipts exist but `launch.json` was lost with the controller, fresh status joins
   the guards' own PID/creation identities and continues observing the original job;
4. the exact same id is never automatically re-brokered in v1. A later generation/lease protocol
   may add safe takeover, but absence of such a protocol is not permission to guess.

### B. A sticky ready bit is not a watchdog

Supervisor worker launch requires a watchdog receipt whose state is exactly `watching`, whose
heartbeat is fresh, and whose PID plus process-creation identity still match a live process. A
terminal/stale `ready=true` record is historical evidence only. The supervisor retains the worker
PID/identity immediately after `Popen`; every catchable exception before the running receipt is
durable must exact-kill and wait for that tree. It may publish `launch_failed` only after confirmed
cleanup; an unconfirmed cleanup is `supervision_lost`, with `child_alive` stated honestly.

### C. Requests are intent; evidence decides the outcome

The final-state precedence is deterministic:

1. a child-owned, atomic publish outcome proving `primary_effect=pushed` wins as `succeeded`;
2. a watchdog-authored, identity-matched and confirmed force-kill receipt wins as
   `cancelled` or `deadline_exceeded` according to the request;
3. reserved worker exit `130` plus a request is cooperative cancellation/deadline;
4. exit zero is `succeeded`, even if a request raced after the work's commit point;
5. any other exit without a confirmed force receipt is `failed` / `unattributed_nonzero_exit`;
6. a vanished worker with no surviving attribution path is `outcome_unknown`.

The watchdog must test worker liveness before publishing deadline intent. If a requested worker is
already dead, it waits for the supervisor's exit attribution; it does not manufacture a
cooperative-cancel verdict merely from the request file. Cooperating generic workers use exit 130;
`ship.py` already uses that reserved code at safe pre-publish boundaries.

### D. Commit/push is a point of no return protected by an OS-held fence

`ship.py` receives a per-job `publish.fence` and atomic child-owned `outcome.json`. Immediately
before the mirror commit+push step it acquires an exclusive OS byte lock, re-checks cancellation,
and, if clear, writes `publish_active` with recovery metadata (branch, HEAD-before, message, named
paths). It holds the lock through mirror completion and the terminal outcome write.

Before any force-kill, the watchdog must acquire the same fence non-blocking and hold it across its
decision. If the child owns the fence, force is deferred and status says
`cancel_pending_critical`, `force_deferred_by=publish_fence`, and `deadline_enforced=false`. A
successful mirror writes `primary_effect=pushed`, commit SHA, and branch before releasing; late
cancel cannot relabel it. If the fence becomes free while the durable outcome remains
`publish_active`, status is `outcome_unknown`, `publish_may_have_occurred=true`, never `cancelled`.

This is an explicit safety tradeoff, not a hidden timeout extension: an exact hard deadline and a
promise never to force-kill wedged Git cannot both hold. Deadline enforcement remains exact for
ordinary work. During the narrow publish fence, data safety wins and the dashboard must show that
force is deferred. An operator-approved recovery/override can be a later slice.

### E. Primary state must terminate when supervision is gone

When neither guard is live/fresh enough to advance a nonterminal job, fresh status promotes
primary `state` to `supervision_lost`, preserves the old value as `last_reported_state`, and sets
`deadline_enforced=false`. A spec-only startup expiry is the narrower `launch_failed` case from A.
Consumers must never need to interpret `observed_state` to discover that terminal fact.

### F. Additional pre-registered RED receipts

The preregistration battery adds these before the corrective implementation:

11. an exact retry of an expired spec-only launch makes zero broker calls and returns terminal
    `launch_failed` with a new-id remedy;
12. a stale/terminal watchdog receipt cannot authorize even one worker-start attempt;
13. injected failure of the first running receipt exact-kills the already-created child before the
    supervisor returns;
14. a child that exits zero near a deadline/request is `succeeded`; the cooperative-cancel drill
    uses reserved exit 130 and remains `cancelled`;
15. cancel while the publish fence is held cannot invoke the kill path, and a pushed outcome wins
    over that late request;
16. an abandoned `publish_active` outcome is `outcome_unknown` with recovery metadata;
17. running-with-two-dead-guards and expired-spec-with-no-guards both return a terminal primary
    state, never an eternal `running`/`launching` shell.

The ordinary wedged-child deadline, recursive-controller-kill, idempotence, atomicity, and zero-flag
ship compatibility receipts remain mandatory; this amendment adds failure windows rather than
replacing the original bars.
