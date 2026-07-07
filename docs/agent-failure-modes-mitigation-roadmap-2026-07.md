# Agent Failure-Mode Mitigation Roadmap — Phase 2 (2026-07-06)

Companion to `docs/agent-failure-modes-retrospective-2026-07.md` (the taxonomy).
This is the **prioritized, sequenced build plan**. It folds the adversarial-verdict
refinements into each track and orders them so Daniel can start building Monday.

Every code claim below was re-verified against the current tree (line numbers cited).
Where a proposal's stated mechanism was wrong but its conclusion survived, the
**corrected** mechanism is used here.

---

## 0. Priority order (and why)

The retrospective's own rollup names two dominating 🔴 clusters plus an orchestration
gap and a friction tail. The build order is driven by **what blocks unattended
operation** and **what stops the house from breaking**, in that sequence:

1. **LIVENESS cluster (G4 → G3/D1/D2/D3) — FIRST.**
   *G4 is the single highest-value fix — "impossible to continue building with
   DeepSeek because it kept not responding."* Without wedge-detection + revive, nothing
   else matters because the fleet can't be left running. The verified root cause is
   narrow and cheap to hit: `OpenAI()` is built with **no timeout** (runner lines 69,
   95) and the `interrupt` lambda is only checked **between** tool rounds (deepseek_chat
   line 761), so a hung model/tool call is silently unrecoverable in-process. A one-line
   timeout converts the dominant wedge into a caught exception the existing
   `try/except` already recovers.

2. **SAFETY cluster (B2/B1/B5/B4/B3) — SECOND.**
   Once the fleet stays alive unattended, the next thing it can do unattended is break
   the house. Verified today: `run_command` (line 583) gates **only** on the
   `--allow-exec` launch flag and never consults `acl.json` — the ACL is decorative for
   exec (B2). This is also a **hard dependency** for the orchestration/onboarding tracks,
   whose "hard gates" are vapor until the enforcement door exists.

3. **ORCHESTRATION + ONBOARDING (G2/G1/E4) — THIRD.**
   Barriers, role-routing, and "hats" make the fleet *useful* rather than merely
   *survivable*. They depend on both clusters above (a barrier with an absent adjudicator
   is a new G4; a "hat" that clamps exec is theater until the exec door exists).

4. **ISOLATION (C1/C2) — FOURTH (parallelizable).**
   Containerization is the *real* B5 fix and a structural C1/C2 fix, but it is a
   larger, independent lift that does not block 1–3. It can proceed on its own track.

5. **FRICTION (A/E/F/D4) — CONTINUOUS quick-wins.**
   Cheap, land-immediately fixes. Several are true one-liners and should ship in Wave 0
   alongside the liveness work — **except** the two that have verified regressions (E3
   ack, D4 re-arm), which are gated on a correctness fix.

---

## Wave 0 — Quick wins (land immediately, day 1)

These are independent, low-risk, and unblock/de-noise everything after. Ship as one
small PR.

| Fix | What to build | Closes | Files | Effort |
|-----|---------------|--------|-------|--------|
| **PYTHONUTF8** | `env.setdefault('PYTHONUTF8','1')` + `PYTHONIOENCODING='utf-8'` in `Launcher.launch()` env build; same `os.environ.setdefault` at top of `bifrost_ui.py` before stdlib http import. | A2 | `core/comm/launcher.py`, `scripts/bifrost_ui.py` | XS |
| **Forward-slash roots + MSYS** | `repo = str(HERE).replace('\\','/')` in `_default_registry()`; **also** normalize the runner's own `--root` argparse default at `bifrost_runner_deepseek.py:189` (the actual A1 incident site — hand-started runner, not launcher); `env.setdefault('MSYS_NO_PATHCONV','1')`. | A1 | `launcher.py`, `bifrost_runner_deepseek.py` | XS |
| **Process-tree clarity** | Add `launcher_pid: os.getpid()` + `role` to each `registry()` row so the UI renders "worker pid N (owned by launcher pid M)". Presentation only. | A3 | `launcher.py` | XS |
| **E2 vision recipe hint** | 3-line note in `default_system()`: AMD DirectML `privateuseone:0` is real accel; use Florence-2 `<OD>`/`<OCR_WITH_REGION>`, not `<CAPTION>`; don't churn LLaVA/Ollama/Gemini first. | E2 | `scripts/deepseek_chat.py` | XS |
| **E1 self-diagnosing tool errors** | `root.exists()` probe at `ToolBox.__init__` (**required** — today no signal distinguishes bad-root from missing-file; A1 mangling makes a nonexistent root pass `commonpath` lexically). On bad root, emit `"TOOL-ENV ERROR: your root '<root>' does not exist… STOP and report 'my root is broken' — do NOT retry with modified paths."` Add a **path/root-error-class** counter (not identical-tool): trip after N=3 not-found/root errors across *any* path tool in one turn → inject halt-and-report note. (Identical-tool counter would miss the observed *varied-path* flailing.) | E1 | `scripts/deepseek_chat.py` | S |

**Verified corrections folded in:** A1's real failure site is the runner's `--root`
default, not only the launcher; the launcher-only fix in the original proposal would
have missed it. E1's `root.exists()` probe is mandatory because `commonpath` accepts a
child of a nonexistent root.

**Deferred out of Wave 0 (regressions to fix first):**
- **E3 ack-on-receive** — sending an ack as `kind='note'` **wakes Claude** and burns a
  full turn: `bifrost_wake.py:25 SKIP_KINDS = {trace, reply, steer}` does **not** include
  `note`. Fix: introduce a dedicated non-waking kind `ack`, add it to `SKIP_KINDS`, emit
  the ack as that kind, gate to `kind in {chat,request,question,handoff}`, and dedupe per
  message-id via the bus cursor. Then it's a real win. → **Wave 1** with the liveness work.
- **D4 idle-wake re-arm** — see Wave 1; needs a verified Stop-hook contract + a
  per-inner-block PID heartbeat refresh that does not exist today, else it masks a G4
  wedge (looks-alive-while-wedged).

---

## Wave 1 — Liveness & recovery (TOP PRIORITY)

**Goal: the fleet survives unattended and every wedge is either self-healed or
one-click revivable.** Ship in strict sub-order; each piece is independently testable.

### L0 — Hard timeouts (the cheapest real G4 fix) — ✅ **SHIPPED 2026-07-06**
> Done: `make_client()` factory in `deepseek_chat.py` (per-read `httpx.Timeout` + explicit
> `max_retries`, env-tunable), wired into runner (make_replier / make_agentic_replier), REPL,
> and `ask_deepseek`; `run_command` timeout capped at `MAX_CMD_TIMEOUT`. Verified end-to-end
> (`tests/manual/l0_timeout_probe.py`): hung stream aborts in ~timeout, happy path unaffected.
> **Next: L1 (worklive heartbeat).**
- **Build:** Pass **both** `timeout=` **and an explicit `max_retries=`** to the
  `OpenAI(...)` constructor (runner lines 69, 95) — the SDK default `max_retries=2` retries
  `APITimeoutError`, so timeout alone means a hung call surfaces after ≈`timeout × 3`. Also
  wrap each `toolbox.execute()` / tool call in a hard per-call wall-clock (tools already
  take `timeout=`; enforce a ceiling and ensure `run_command`'s subprocess timeout can't be
  overridden past the cap).
- **Why first / VERIFIED:** empirically confirmed (see open-question #1) — a `timeout=`
  aborts both pre-data and mid-stream stalls within ~timeout, raising `ReadTimeout`, which
  `deepseek_chat.py`'s existing `try/except` at `send()` (lines 771-777) already catches →
  returns "", loop continues. So the dominant wedge is revived with **near-zero new
  infrastructure**. Recovery is *abandon-turn* (the triggering message is popped), not
  resume — good enough to unwedge; graceful resume is a later layer.
- **Closes:** most of G4. **Files:** `bifrost_runner_deepseek.py`, `scripts/deepseek_chat.py`.
- **Effort:** S. **Residual:** a slow-dribble stream (bytes below the per-read timeout,
  forever) won't trip the read timeout — that's L3's total-generation wall-clock, not L0's.

### L1 — Work-progress heartbeat (pure observability, zero behavior change) — ✅ **SHIPPED 2026-07-06**
> Done: `core/comm/liveness.py` — per-agent `bifrost:worklive:<agent>` = `{phase, since_ts,
> beat_ts, turn, detail, seq}`, fail-open (mirrors control.py). Wired into the runner at the
> single seams: `on_activity` (thinking/reading/searching/tool phases), `_heartbeat` thread
> (`refresh()` keeps it alive + ageing mid-wedge), and loop edges (`handling`+turn-count / `idle`).
> `read()` + `stuck_seconds()` for readers. Verified (`tests/manual/l1_worklive_probe.py`):
> since_ts moves only on phase change, stuck-timer both rises across a refresh AND resets on a
> phase change (not pinnable), live end-to-end turn capture. **Next: L5 (lock-in-launch, XS) then
> L3/L4 (the readers that ACT on worklive).**
- **Build:** `core/comm/liveness.py` (~80 lines). Redis key `bifrost:worklive:<agent>` =
  `{phase, since_ts, turn_id, tool}`. Stamp at every progress edge already instrumented
  (message received, model-call start, each tool-call start/return, reply sent, idle) by
  wrapping the existing `control.set_activity` / `on_trace` / `on_activity` call sites.
  Fail-open like `control.py`.
- **Closes:** makes G4/G3 *visible* (prerequisite for L2/L3). **Files:** new
  `core/comm/liveness.py`; hook points in `bifrost_runner_deepseek.py`. **Effort:** S.
- **Refinement (verified):** worklive detects *stuck-in-a-phase*, **not**
  *stuck-in-a-healthy-looking-idle* (the retro's "lost cursor, dead heartbeat" variant).
  Add a companion check in L3 for "presence fresh + holds lock + only ever beats `idle`
  while unanswered mail sits in its inbox."

### L2 — In-runner watchdog + circuit-breaker (self-heal the between-rounds case)
- **Build:** `core/comm/watchdog.py` + a second daemon thread beside `_heartbeat`
  (runner line 256). Reads its own worklive record every ~3s; on a stuck phase trips
  `control.halt(targets=[agent], by='watchdog', reason='stuck in <phase> Ns')` so the
  next round-boundary `interrupt` check breaks out.
- **Honest scoping (verified against code):** because `interrupt` is checked **only** at
  the `for _ in range(MAX_TOOL_ROUNDS)` boundary (deepseek_chat line 761), L2 self-heals
  **only** the between-rounds case — which, post-L0, is largely already handled by the
  timeout. L2 is a **nice-to-have** layer, **not** the load-bearing G4 fix. Do **not**
  claim it fixes a mid-round wedge; it cannot, by the code.
- **Circuit-breaker (G3) — build BOTH detectors:**
  1. **Repetition:** hash of `tool+args`; trip after 3 consecutive near-identical
     no-progress calls (catches the "847× same question" pattern).
  2. **Distinct-destructive-velocity:** count `write_file`/`edit_file`/`run_command`
     calls per rolling window; trip on velocity (catches the "10k distinct changes" /
     taskkill-spree / vision-churn pattern, which is *not* repetition). Wire the trip to
     `control.pause(by='watchdog')` exactly as the existing rate-limit backstop.
  3. Optional: cost/turn-velocity ($/hour, turns/session) breaker.
- **Closes:** G3, partial G4. **Files:** new `core/comm/watchdog.py`;
  `bifrost_runner_deepseek.py`. **Effort:** M.

### L3 — External supervisor + UI revive/kill (the primary G4 backstop)
- **Build:** This is the **real** G4 fix for mid-round wedges L2 can't reach.
  - Extend `launcher._monitor_loop` (line 485) to read each agent's worklive freshness +
    runner_lock heartbeat: lock held + presence fresh + worklive phase not advanced past
    `MODEL_TIMEOUT + grace` + self-recovery failed → `status='wedged'`, force-kill,
    respawn (if auto_restart).
  - **Startup smoke-test (D2):** after Popen, wait ≤8s for the first `online` worklive
    beat; if the process dies or never beats, `status='crashed'` with `stderr_tail`.
    (**Correction:** the cited `args.accept_hints` AttributeError is **already fixed** —
    `--accept-hints` is defined at runner line 189 and used safely at 241. D2 is scoped
    to the smoke-test + backoff only, not reproducing a dead bug.)
  - **Restart-storm guard (verified gap):** `_restart` is a flat `time.sleep(3)` (line
    510) with no backoff. Add `StartLimitBurst`-style exponential backoff + escalate to a
    bus note + stop after N fails, so a deterministic boot crash doesn't crash-loop.
  - **UI:** `POST /launcher/revive {tag}` = kill-if-wedged-then-relaunch; a Revive button
    beside the existing kill; add `liveness` to the `_status()` payload so the roster
    shows "stuck in tool_call 142s → [Revive]".
  - **Distinguish halt sources:** the halt payload already carries `{reason, by}`; render
    "auto-halted by watchdog (stuck 142s)" distinctly from a user pause so a human doesn't
    mistake auto-recovery for their own action. **Hard requirement, not a footnote.**
- **SHIP IN OBSERVE-ONLY MODE FIRST:** surface wedged/stuck-phase in the roster and
  **require a human Revive click** before enabling any auto-kill, until thresholds are
  tuned on the real fleet. Given the convos-amnesia risk below, human-gated revive should
  arguably be the *shipped default*, with auto-kill a later per-agent opt-in flag.
- **Convos preservation (verified risk):** killing drops the in-memory `convos` dict (the
  multi-turn working context). A false-positive kill silently amnesias the agent
  mid-project (compounds E4). **Persist last-N per-peer messages to Redis on any
  watchdog-initiated kill** so Revive rehydrates; distinguish user-kill (drop, intended)
  from watchdog-kill (preserve, involuntary).
- **Closes:** G4 (primary), D2, restart-storm. **Files:** `core/comm/launcher.py`,
  `scripts/bifrost_ui.py`. **Effort:** M–L.

### L4 — Stack supervisor that OUTLIVES the bus (the real D1 fix)
- **Verified gap:** the launcher lives inside the `bifrost_ui.py` process
  (`get_launcher` singleton). Per D1 the retro observed the launcher dying *with* the
  stack. **A supervisor co-located with what it supervises cannot restart the stack.**
- **Build:** a tiny **standalone** supervisor process — a Windows Scheduled Task / NSSM
  service / small detached script — whose only job is OS-level keep-alive of Redis + the
  UI + runners via checks that **do not depend on Redis** (`handle.poll()` / port probe /
  container inspect). The in-UI launcher monitor (L3) is only the wedge-detector for
  runners *while the UI is up*; L4 is what brings the UI back after a whole-stack death.
- **Closes:** D1. **Files:** new `scripts/bifrost_supervisor.py` + a scheduled-task
  install note. **Effort:** M.

### L5 — D3 duplicate-runner: honor the lock in launch()
- **Verified:** `runner_lock.py` already does atomic nx+TTL reclaim correctly; the only
  gap is `launcher.launch()` (line 274) **ignores** a failed `acquire()` and spawns
  anyway.
- **Build (non-violent — reconciled with the SAFETY track):** `if not acquire(...):
  return {ok:False, reason:'already running pid X'}`. Let the 20s TTL handle
  crash-reclaim. **Do NOT add a taskkill-the-holder path** — that reintroduces the exact
  unscoped host-PID-kill power B1/B4 exist to remove.
- **Closes:** D3. **Files:** `core/comm/launcher.py`. **Effort:** XS.

### L6 (folded here) — E3 ack + D4 idle-wake (the two deferred friction fixes)
- **E3 ack-on-receive:** new non-waking kind `ack` added to `bifrost_wake.py:25
  SKIP_KINDS`; emit before the model call, gated + deduped per message-id. Now a real
  win, not a token regression.
- **D4 idle-wake re-arm:** **first READ and cite the actual Stop-hook** that re-invokes
  the wake listener — the zero-cost claim depends on it re-invoking on *process exit*, and
  that wiring was not in the reviewed files. Then: distinct return code (e.g. 64) for
  quiet re-arm, an **in-process re-block loop with a per-inner-block PID-heartbeat
  refresh** (does not exist today — `bifrost_wake.py` writes the PID once at main, lines
  74-77, never refreshes it) **and an absolute wall-clock cap** that exits to the harness,
  so a wedged listener can't masquerade as alive. This liveness-refresh is the
  load-bearing part; ship it with L1's worklive convention.
- **Closes:** E3, D4. **Files:** `bifrost_wake.py`, `bifrost_runner_deepseek.py`, UI. **Effort:** S.

**Wave 1 sequencing:** L0 (timeout) → L1 (observe) → L5 (D3 one-liner, anytime) →
L3 observe-only + L4 supervisor (the real backstops) → L2 (self-heal + G3 breakers) →
L6 (ack/wake). L0 and L5 are same-day; do them immediately.

---

## Wave 2 — Safe unattended shell + enforced governance

**Goal: shell power is gated by the ACL and a policy rulebook, not a launch flag.**
This wave is a **hard dependency** for Wave 3's "hard gates."

### S1 — Exec gated by the ACL, not the launch flag (fixes B2)
- **Build:** in `run_command` (line 583), **before** the `allow_exec` check, resolve the
  grant and require `Cap.EXEC` — mirroring the existing `_kb_write_ok` pattern (line 368,
  the *only* place `registry.resolve` is currently called). `--allow-exec` stays as a
  second independent switch (**AND**-gate: flag = "physically enabled on this runner",
  ACL = "this agent is authorized").
- **Verified corrections:**
  - The proposal's stated mechanism was **wrong**: an expired DeepSeek grant resolves to
    `DEFAULT_ROLE = "quarantined"` (capabilities line 83), **not** admin — verified at
    registry lines 158-159. Conclusion (no exec after 2026-07-09 expiry) holds and is in
    fact *stronger*. The "admin has no exec" fact is only true on the file-**missing**
    bootstrap path. Fix the doc so a reviewer doesn't mispredict.
  - **Interactive-REPL coupling (verified):** `ToolBox` is constructed **without**
    `agent_id` in interactive mode (line 929) → `self.agent_id is None`.
    `resolve(self.agent_id or 'deepseek')` would silently deny a **human** at the REPL
    post-expiry. **Gate the ACL exec check on the runner-injected `agent_id` only; leave
    interactive (`agent_id=None`) on the `--allow-exec` flag.**
- **Closes:** B2. **Files:** `scripts/deepseek_chat.py`. **Effort:** S.

### S2 — Command-policy rulebook (fixes B1/B4)
- **Build:** `agent/policy/command_guard.py`, sibling of `agent/policy/git_guard.py`
  (same `_segments`/`shlex`/`(allowed, reason)` teaching-error shape) but **fail-CLOSED**
  (unparseable → DENY; git_guard is fail-open). Three lists:
  - **DENYLIST** (defense-in-depth): `taskkill`/`kill`/`Stop-Process`/`wmic process`;
    spawning `bifrost_runner*`/`bifrost_ui*`/`launcher.py`/`docker … redis`; `rm -rf` /
    `Remove-Item -Recurse` / `del /s` / `format`; `git push`/`reset --hard`/`clean -fdx`/
    history-rewrite; `shutdown`/`reboot`; `curl|iwr` piped to a shell; writes into
    `security/`, `agents.md`, **`launcher.json`**, `scripts/hooks/`.
  - **ASK-list default → DENY-with-reason in unattended/trust mode** (NOT a human
    confirm — avoids the documented 93% approval-fatigue regression), fall through to
    `_confirm` only in interactive mode.
  - **ALLOWLIST is the boundary**, expressed in `acl.json` `exec_policy.allow`.
- **CRITICAL verified hole — no general-purpose interpreters in the allowlist:**
  `^py( |$)` matches `py -c "os.system(...)"` and `py evil.py` — i.e. arbitrary code
  execution, defeating the whole denylist. Allowlist **only** exact safe targets:
  `^py -m pytest`, `^py agent_cli\.py`, specific vision-recipe scripts, `^git (status|log|diff|show)`.
  Treat `py -c` and `py <unknown>.py` as ask/deny.
- **Reject bypass vectors explicitly** rather than parsing through them: `$(...)`,
  backticks, `${...}` indirection, `cmd /c`, `powershell -enc`/base64. (Best-effort at
  app layer — see honesty note under B5.)
- **Emit a bus `inform` on every DENY** (reuse the `_yield_notice` pattern, line 507):
  turns the gate into a free G3 runaway signal and makes repeated-block loops visible
  instead of silently stalling the agent.
- **Closes:** B1, B4. **Files:** new `agent/policy/command_guard.py`;
  `scripts/deepseek_chat.py`. **Effort:** M.

### S3 — Policy in acl.json + protected-path extension (fixes B3, partial)
- **Build:** extend the `acl.json` grant schema with optional `exec_policy: {allow, deny,
  cwd_scope}` (`registry._load` already tolerates unknown keys). Add
  `Grant.exec_allows(command)->(bool,reason)` beside `can_write`/`can_send_kind`.
- **Extend `_prewrite` protected set (verified gap):** line 532 protects `security/` +
  `agents.md` only. Add `launcher.json` and `scripts/hooks/` — this closes the concrete
  **write-then-exec escalation** (edit a launch config → supervisor/wake later runs it).
- **B3 honesty (verified):** the "task scope → `cwd_scope`" enforcement is **aspirational**
  — `registry.resolve()` reads a static file and has no notion of the live claimed task;
  `task_ledger` has no projection into a Grant. Ship static per-agent `cwd_scope` as v1
  and **label it "advisory governance, static scope"**; the real "task's declared scope
  blocks out-of-scope shell" needs a resolve()→ledger integration (design it explicitly
  or drop the claim).
- **Closes:** B3 (partial/advisory). **Files:** `security/acl.json`,
  `core/trust/registry.py`, `scripts/deepseek_chat.py`. **Effort:** M.

### S4 — cwd scope + OS-level fallback (partial B5)
- **4a (cheap):** enforce the resolved `run_command` cwd is inside `path_scope`
  (reuse `can_write` fnmatch); canonicalize with realpath (closes the CVE-2025-53109
  symlink-prefix class); reject `cd`/`pushd`/absolute-path escapes via command_guard.
- **4b (defense-in-depth):** wrap the subprocess in a Windows Job Object
  (`KILL_ON_JOB_CLOSE` + active-process cap). **Verified fragility:** `run_command` uses
  `subprocess.run(shell=True)`; you **cannot** job-assign after `run()` returns — you must
  `CREATE_SUSPENDED` → `AssignProcessToJobObject` → `ResumeThread` (raw CreateProcess/
  ctypes, abandoning the simple `run` call). Set the process cap **generously** for
  pytest worker pools. Feature-flag it; test against the real suite before unattended.
- **B5 HONESTY (mandatory framing fix):** a Job Object is lifetime/fork-bomb containment,
  **NOT** filesystem/network isolation. App-layer cwd-scoping is bypassable
  (write-then-exec, absolute paths). **Downgrade B5 from "fixed" to "partially
  mitigated — the real B5 fix is the C1 container track (Wave 4)."**
- **Closes:** B5 (partial). **Files:** `scripts/deepseek_chat.py`. **Effort:** M.

**Advisory-in-process caveat (verified, applies to all of Wave 2 and Wave 3):**
`conductor`/`task_ledger`/`command_guard` are plain modules the runner imports
**in-process**. Under `--trust` with exec, a determined/injected agent can call
`TaskLedger.transition()` directly or shell around the guard. These are **real gates for
a cooperating weak model**, but **not** a process boundary. A true hard gate requires the
runner to be a separate process/container with no direct import, forced through an
RPC/CLI. **This is exactly why Wave 4 (containerization) is the structural completion of
the safety story — Wave 2 is necessary but not sufficient.**

**Wave 2 sequencing:** S1 (ACL exec gate) → S2 (rulebook) → S3 (policy schema +
protected-path) → S4 (cwd scope + Job Object). S1+S2 deliver most of the safety value;
S4b is the fiddliest and can trail.

---

## Wave 3 — Orchestration, role-routing, onboarding

**Goal: play the tortoise and the hare to their strengths; stop the racing; stop the
fast model being derailed by stale context.** Depends on Wave 1 (no barrier without a
recovery path) and Wave 2 (no "hard gate" without the enforcement door).

### O1 — Enforce no-self-verify + role binding IN THE LEDGER (fixes the false premise)
- **Verified:** `task_ledger.transition()` (line 166) requires `commit`/`verified_by`
  non-empty but **never** checks `verified_by != owner`, and never gates on the `by`
  caller. DeepSeek can call `done(tid, commit='x', verified_by='deepseek')` and pass.
  The role gate the whole G1 story rests on is **genuinely greenfield**, not "adds
  binding only."
- **Build:** put the gate in the **pure ledger** (holds regardless of caller —
  conductor, runner, or CLI): reject `approve`/`verify`/`done` from a non-plan-role `by`;
  reject `done` when `verified_by == owner`. Keyed to a role map.
- **Closes:** the enforcement half of G1/E4/B3 (advisory-in-process, per the caveat).
  **Files:** `core/coord/task_ledger.py`. **Effort:** S.

### O2 — Non-blocking negotiation round driver (unblocks the barrier)
- **Verified:** `negotiation.auto_close` uses a blocking `time.sleep(ROUND_TIMEOUT=8s)`
  and there is **no** non-blocking driver. The barrier trigger (RED verdict →
  `barrier.open`) depends on a round closing, so this is a **prerequisite**, not a
  footnote.
- **Build:** poll `round_state` at the tool-round boundary the runner already checks,
  instead of `time.sleep`. **Files:** `core/coord/negotiation.py`,
  `bifrost_runner_deepseek.py`. **Effort:** S–M.

### O3 — The Sync barrier (fixes G2)
- **Build:** `core/coord/barrier.py` (~120 lines). `barrier.open(id, targets, reason,
  deadline)` writes the barrier hash + calls the **existing** `control.halt(targets)`.
  Runner ACKs at the existing `if control.is_halted(agent):` boundary (line 265) by
  emitting a `task_snapshot` (canonical schema in
  `docs/coordination-plan-synthesis.md §3.2`). Wire `negotiation` RED → `barrier.open`.
  Graded release via `control.resume` + `nudge.steer_push`. `runner_lock` 20s TTL
  distinguishes *stalled* (alive, no ACK) from *dead* (TTL expired) so the barrier
  self-heals.
- **Snapshot-fidelity fix (verified circularity):** the ACK snapshot is emitted by
  DeepSeek — the exact context-fragile model whose unreliability motivated the barrier.
  **Derive the snapshot from machine facts (ledger/lock/intent state) rather than model
  prose, or have the plan-role (Claude) validate/normalize it** before it becomes the
  converge artifact.
- **Absent-adjudicator deadlock (verified — recreates G4):** if Claude is at its weekly
  limit (an *observed* condition), a soft-timeout barrier can sit open forever AND
  DeepSeek's finished work has no verifier. **Make the fallback a DECIDED default, not an
  open question:** auto-resume non-stalled agents after 2× deadline OR a config'd hard
  cap; define a Claude-exhausted degraded mode (human-verify fallback, or DeepSeek
  self-verify limited to `difficulty < threshold` tasks only).
- **Closes:** G2. **Files:** new `core/coord/barrier.py`; `bifrost_runner_deepseek.py`;
  `core/coord/negotiation.py`. **Effort:** M.

### O4 — Strength/latency role router (fixes G1)
- **Build:** `core/coord/router.py` — thin policy over the ledger. Role map (plan/verify
  = Claude; bounded-execute = DeepSeek) enforced via O1's ledger gate. Extend
  `conductor.next_task()` → `next_task(for_agent)` returning only role-matching tasks.
  Difficulty gate at `propose()` (cheap heuristic: files-touched + acceptance length +
  explicit tag) so a fragile fast model is never handed an unbounded step; misroute-up is
  safe, misroute-down is caught at the verify gate.
- **Verified gap:** nothing forces Claude to be the proposer (`propose()` `by=` is
  caller-supplied) → the difficulty tag is self-assigned by the agent it constrains. **Add
  a plan-role gate on `propose()` too** (via O1).
- **Concurrency honesty:** the ledger's one-in-progress gate means barrier+router run
  **serially** today; the "hare runs bounded sprints" speedup needs the unbuilt Phase-2
  disjoint-set relaxation. **Don't oversell the speedup** until that lands.
- **Closes:** G1. **Files:** new `core/coord/router.py`; `core/coord/conductor.py`.
  **Effort:** M.

### O5 — "Hats" onboarding (E4/B4 scoping + G1 role labels)
- **Reframe honestly (verified false central premise):** the original claim that a hat
  narrows authority through the existing door with "ZERO new enforcement code" is
  **false** — `_prewrite` and `run_command` don't read a Grant's `path_scope`/`Cap` today.
  A hat's authority-narrowing is **real only after Wave 2 (S1) builds the ACL-consulting
  door.** Split the deliverable:
  - **Ship now (feasible today):** SEAM A — prompt/boot-task layering. `hats/<name>/HAT.md`
    (Anthropic SKILL.md format: YAML frontmatter + body). `--hat` flag appends the hat
    body as a fenced layer and drives `agent_cli.py boot --task` with `hat.boot_task` so
    the ~9k-token digest is hat-scoped. Keep bodies short (no prompt caching on the peer —
    Token Frugality). **Closes:** context-attention half of E4/G1.
  - **Gate behind Wave 2:** SEAM B — `Hat.apply_to_grant(base) -> Grant` **intersection-
    only** (can subtract, never widen), consumed by the S1 door. Unit-test glob
    intersection (`intersect(['*'],['docs/*'])==['docs/*']`; `intersect(['docs/*'],
    ['src/*'])==[]`) **and** the expired-base-grant flowing through the *live* door.
- **Verified corrections:**
  - `bus.Message` has **no `topic` field** (id/frm/to/kind/content/ts/meta/parts). Drop
    `inbox_topics` until a topic tag exists; keep only lookback-cap, and be honest it's
    minor since the cursor already bounds scrollback. For real E4 relief, **filter
    ledger-superseded/closed messages**, not merely old ones.
  - **Opt-in is theater for the unattended case.** Default the DeepSeek runner to an
    `executor` hat (deny-more-by-default), overridable only by a super-admin flag.
- **Closes:** E4 (attention), B4 (after Wave 2), G1 (role label). **Files:** new
  `core/hats/loader.py`, `hats/*`; `bifrost_runner_deepseek.py`, `agent_cli.py`.
  **Effort:** M (SEAM A: S).

**Wave 3 sequencing:** O1 (ledger gate — unblocks everything) → O2 (round driver) →
O3 (barrier) → O4 (router) → O5 SEAM A now / SEAM B after Wave 2 S1.

---

## Wave 4 — Real isolation + one-bus UX (parallel track)

**Goal: process/port/FS/network actually separated (the structural B5 + C1/C2 fix).**
Independent of Waves 1–3; can run in parallel by a second builder.

### I1 — Containerized runner on ONE bus (recommended tier)
- **Verified premises hold:** runner has **no** hardcoded redis;
  `_resolve_default_redis_endpoint()` overrides host/port per-field from env;
  `docker-redis-master` binds `0.0.0.0:16379` so `host.docker.internal:16379` is reachable
  from a WSL2 container. So the env-only redirect is a real zero-code redirect.
- **Build:** `docker/agent-runner/Dockerfile` (python:3.11-slim, COPY only
  `core/`+`scripts/`+`config.py`+`security/`, **no E:/ mount**) + `compose.yml`
  (`REDIS_HOST=host.docker.internal`, `REDIS_PORT=16379`, **`REDIS_DB=0`** — verified gap:
  `_resolve_default_redis_db()` also honors env; omit it and a stray DB silently
  re-forks the bus = C2 recurs; `PYTHONUTF8=1`; distinct `AGENT_ID=deepseek-sbx`;
  `restart: unless-stopped`; healthcheck; **no published ports** → structurally can't bind
  8787 = C1 solved). One bus, one UI = C2 solved for free.
- **Closes:** C1, C2, structural B5. **Effort:** M–L.

### I2 — Docker runtime adapter in the launcher (the real lift — NOT a verb swap)
- **Verified mis-scope:** the launcher is built on `subprocess.Popen` where the handle
  **is** the agent (`handle.poll()` for exit, `communicate()` for the classify tail,
  `kill()` for the PID). `docker compose up -d` is **detached** — the Popen wraps the CLI
  which exits ~1-2s later code 0, so the monitor marks the agent "exited/clean" while the
  container runs, and `kill()` hits a dead CLI.
- **Build a `RuntimeAdapter`** with distinct hooks: docker spawn = `compose up -d`;
  status = background poll on `docker inspect --format {{.State.Status}}`; classify =
  `docker logs --tail` feeding `_classify_exit`; kill = `docker stop`. **Move
  `runner_lock` acquisition into the container entrypoint** (the runner runs *inside* the
  container; the host-side `acquire()` at launcher line 274 is meaningless for this
  runtime). **Pin the Docker-restart vs launcher-auto_restart ownership** (one supervisor,
  not both — else double-supervision + a 20s-TTL/restart race = fresh G4).
- **Closes:** enables I1 through the existing UI. **Effort:** M–L.
- **Reject the two-redis bridge tier** unless egress-denial is a hard requirement; prefer
  a Docker `internal: true` network + redis-only allow over a bridge daemon (the bridge is
  a fresh single-point G4 and breaks the ms-stream-id ordering the bus `_drain` sort
  assumes).

**Diagnostics note:** roster/`runner_lock.holder()` pid becomes a container-namespace pid,
meaningless on the host — degrades the observability the retro leans on; surface container
id instead. Plan removal of the dangling sandbox redis (16380) + the `config.py=16380`
edit that originally caused C2.

---

## Dependency graph (what unblocks what)

```
Wave 0 quick wins ─────────────────────────────► (independent, day 1)

L0 timeout ─► L1 worklive ─► L2 watchdog/breaker (G3)
                    │
                    ├─► L3 UI revive (G4 primary, observe-only first)
                    └─► L4 standalone supervisor (D1)
L5 lock-in-launch (D3) ─────────────────────────► (day 1, independent)
L6 ack/wake ─── needs L1 worklive convention

S1 ACL exec gate ─► S2 rulebook ─► S3 policy+protected-path ─► S4 cwd+JobObject
      │
      └─────────────► O5 SEAM B (hat authority)  [BLOCKED until S1]

O1 ledger gate ─► O2 round driver ─► O3 barrier ─► O4 router
                                         │
O3/O4 ─── need L3/L4 (a barrier with no recovery path = new G4)

Wave 4 (I1 container ─► I2 adapter) ── parallel; is the structural completion of B5/C1/C2
```

**Immediate (Monday morning):** Wave 0 PR + L0 timeout + L5 lock fix. These are hours,
not days, and each removes a live hazard.

---

## Sharpest open questions

1. **[RESOLVED 2026-07-06 — empirically confirmed]** *Is the OpenAI SDK streaming read
   cancellable by `timeout=`?* **YES.** Test (openai 2.24.0 / httpx 0.28.1) against a
   server that sends 200+SSE headers then stalls: `timeout=3` aborted a **pre-data** stall
   in 3.37s and a **mid-stream** stall in 3.01s, both raising `ReadTimeout`; with **no**
   timeout (current runner) the same stall **hung indefinitely** (>12s cap) — reproduces
   G4. The httpx read timeout fires **per chunk read**, so mid-generation hangs are caught.
   `send()` already wraps `_stream_turn()` in `try/except Exception` (deepseek_chat.py
   771-777), so the `ReadTimeout` is already handled → returns "", loop continues. **L0 is
   confirmed as the primary in-process G4 fix.** Caveats folded into L0 below:
   (a) **`max_retries`** — the SDK default is 2 and it retries `APITimeoutError`, so a hung
   call surfaces after ≈`timeout × 3`; L0 must set `max_retries` explicitly.
   (b) **recovery = abandon-turn, not resume** — on timeout `send()` returns "" and pops the
   triggering user message, so the agent is unwedged but the in-flight request is dropped
   (acceptable for L0; graceful retry/resume is a later layer).
   (c) **residual** — a slow-*dribble* server (bytes below the per-read timeout, forever)
   would not trip it; that residual is L3's total-generation wall-clock, already planned.
2. **What exactly re-invokes the wake listener (the Stop-hook contract)?** D4's zero-cost
   in-process re-arm is unverified against its own trigger; it was not in the reviewed
   files. If the hook re-arms on a timer/turn-boundary rather than process-exit, the
   in-process loop changes nothing.
3. **Absent-adjudicator default:** when Claude is exhausted, which is the shipped default —
   auto-resume non-stalled agents at 2× deadline, a hard cap, or DeepSeek self-verify for
   `difficulty < threshold` only? This directly determines whether the barrier *recreates*
   G4.
4. **How far do we push enforcement toward a true process boundary?** Wave 2/3 gates are
   advisory-in-process under `--trust`. Is Wave 4 containerization (no in-process import,
   RPC/CLI-forced) a hard prerequisite for calling B1/B2/B3 "closed," or do we accept
   cooperating-weak-model gates as sufficient for now?
5. **Threshold tuning without a real fleet:** MODEL_TIMEOUT/TOOL_TIMEOUT and the G3
   velocity breakers need real-traffic tuning. Do we run a deliberate soak (observe-only
   L3 + logged would-have-tripped events) before enabling any auto-kill, and for how long?
6. **Convos amnesia vs revive latency:** persist-last-N-messages-before-kill adds Redis
   writes on every watchdog kill. Is the rehydration worth it, or is human-gated revive
   (never auto-kill) the safer permanent default for the fragile peer?
```
