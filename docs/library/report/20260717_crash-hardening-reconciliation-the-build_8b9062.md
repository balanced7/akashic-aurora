---
akashic_id: art_20260717_crash-hardening-reconciliation-the-build_8b9062
akashic_sha: 01ac15df4aed
status: current
type: report
date: 2026-07-17
title: Crash-Hardening Reconciliation — the build spec — 2026-07-17
gist: "(research/reviewed/hardening-slices-claude-2026-07-16.md + hardening-slices-deepseek-2026-07-16.md) with Gemini's adversarial third read (ge"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260716_crash-hardening-slices-claude-blind-half_17aeb7
    rel: cites
created: "2026-07-16T23:53:28"
updated: "2026-07-23T21:42:19"
---
<!-- GENERATED PROJECTION of art_20260717_crash-hardening-reconciliation-the-build_8b9062 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Crash-Hardening Reconciliation — the build spec — 2026-07-17

(research/reviewed/hardening-slices-claude-2026-07-16.md +
hardening-slices-deepseek-2026-07-16.md) with Gemini's adversarial third read (gemini-2.5
via API; web bridge was blocked by a consent overlay — API mode works, use `--mode api`).
Inputs also: mcp-surface-{claude,deepseek}-2026-07-16.md. This doc is the build contract; each
slice ships with its pins + a failure-ledger receipt. NOTHING here overrides Daniel's morning
gate — it's ready FOR that gate.

## Convergence summary

The two halves converged ~90% blind. Gemini adjudicated the three deltas and found three holes
neither half caught. Net: **5 slices, 3 deltas resolved, 3 new items surfaced.**

---

## S1 · C7-4 MCP boot hang — MECHANISM NOW NAMED (was the one true mystery)

Three independent analyses + code evidence converge on ONE mechanism:

- **Empirical (claude):** the SDK, the `_run` capture mechanics, and payload size are all
  EXONERATED by isolation tests; a runtime side effect inside `cmd_boot` parks the server's
  outbound writer until the next inbound stdin frame (deterministic: a bare notification
  flushes the stuck response in ≤0.07s).
- **Surface (deepseek):** every MCP tool is a synchronous `def` — each call blocks the single
  anyio worker thread for its whole duration.
- **Gemini (ranked #1):** on Windows, a **subprocess that inherits the stdout handle** leaves
  the `ProactorEventLoop`'s pending outbound `WriteFile` completion unprocessed until a new
  inbound I/O event (the next `ReadFile`) wakes the loop and sweeps the I/O queue. Fastest
  discriminating instrument: **ProcMon**, watching stdout `WriteFile` completion timing vs
  inbound `ReadFile`.
- **Code evidence (claude, this pass):** `agent_cli.py:2760` is an **uncaptured**
  `subprocess.run(cmd, env=env)` (no `capture_output=` → the child inherits the parent's
  stdout/stderr handles). `agent_cli.py:1583` re-execs `sys.executable` inside a `print()`.
  Either, reached on the boot path, spawns a stdout-inheriting child — the exact shape Gemini's
  #1 mechanism requires. (The `_git` helper at :115 uses `capture_output=True` → fresh pipes,
  NOT a suspect.)

**Why this explains ALL the evidence** (the point where the three analyses lock together):
`sleep(5)` and `print`-only tools do NOT wedge (no subprocess); `cmd_boot` DOES (it spawns a
child); the response flushes on the next inbound frame (Proactor sweeps I/O on the new event).
The "sync def blocks the worker" surface fact is true but insufficient alone — it's the
**stdout-inheriting subprocess spawned from within that sync call** that parks the writer.

### Build (root-cause-first, per Daniel's standing doctrine — NOT straight to subprocess)

1. **Bisect to the exact line** (fast now that the class is named): under the mixed-server
   repro driver, guard the `:2760` and `:1583` spawns (and any heal-path spawn) one at a time;
   the one whose suppression un-wedges is the culprit. ProcMon confirms handle inheritance.
2. **Root fix:** the offending `subprocess.run`/`Popen` must NOT inherit the server's std
   handles — pass `stdout`/`stderr` to `PIPE` or `DEVNULL` (capture like `:115` already does)
   and `close_fds=True`. That is the whole fix if the bisect lands on a single spawn.
3. **Structural backstop (adopt deepseek's Option B, but as defense-in-depth, not the primary
   fix):** the MCP `boot` tool wraps `cmd_boot` behind `anyio.to_thread` already; additionally
   route boot through the `_run_script` subprocess door so ANY future stdout-inheriting spawn
   inside boot can't wedge the server. Ship this ONLY after the root fix, and document it as a
   belt-and-suspenders layer (the root cause stays named + fixed — fix-root-causes doctrine).
- **Pins:** (1) stdio-driver regression — real server, single `tools/call boot`, NO second
  inbound frame, response < 5s (the repro driver already exists, promote to tests/); (2) the
  guarded spawn does not inherit fd1/fd2 (assert via handle check); (3) no phantom double-boot
  ledger events on retry; (4) all other MCP tools still < 2s; (5) CLI `boot` byte-identical.
- **Gate:** un-blocks T081-W2 (user-scope MCP apply) only when pin-1 is green warm+cold ×2.

---

## S2 · C8-3 hook double-fire — CONVERGED, Delta A resolved

Both halves agree: single firing registration + atomic O_EXCL(TTL) dedup at the hook + hook
census (exactly-one across surfaces) + gauge-correction event (annotate, don't rewrite).

**DELTA A (which surface survives) → USER-LEVEL wins.** Claude's half + Gemini both: sessions
genuinely launch OUTSIDE the repo (this very session's cwd is `C:\Users\L5`, not `E:\AI-Setup`
— project-level `.claude/settings.json` would not load, silently disabling every hook).
Coverage across all launch paths beats project-level's git-auditability, and the audit gap is
closed differently: **log the effective hook configuration at session startup** (Gemini) + the
census check + a comment in project settings pointing at the user-level registration. So:
user-level absolute-path registration is the single survivor; project-level entry removed;
auditability restored via startup-config logging + census.
- **Pins:** one Bash call → exactly one injection; guards (git-veto/lock-veto) still fire;
  simulated double-fire suppressed by the O_EXCL dedup; stale marker (>TTL) passes through;
  census warns on a planted duplicate; SessionEnd fires once (the crash-night 5-in-2s cannot
  recur); `gauge_correction` event present; startup logs the effective hook set.

---

## S3 · P2 ACL cap-ceiling gate — CONVERGED, Delta B resolved

Both halves agree: pre-commit diff of staged `security/acl.json` vs HEAD; every added cap must
be ⊆ the granter's caps AT HEAD (same-commit self-upgrade therefore blocks); root/bootstrap
exempt; unparseable staged file blocks fail-closed; non-acl commits zero-cost.

**DELTA B (escape hatch) → AUDITED OVERRIDE wins** (Claude + Gemini). Bare `git --no-verify`
leaves no audit trail — unacceptable for a security gate. The sanctioned bypass is an explicit
`ACL-Approved-By: <human>` commit trailer (or `ACL_GATE_HUMAN_OK=1`) that the hook validates
and logs as an `acl_human_override` event. Prior art: audited overrides in CI/CD + regulated
pipelines. Because `--no-verify` can never be truly prevented in git, add a **post-push CI
re-run** of the same gate as the backstop that catches a `--no-verify` bypass after the fact.
- **Pins:** escalation blocked; subset passes; root exempt; bootstrap exempt; reason-only edit
  passes; same-commit self-upgrade+grant blocks; audited-override passes WITH the event; dirty
  JSON blocks; non-acl commit untouched; CI backstop re-runs the gate on the pushed commit.

---

## S4 · P1 ground-truth gate — CONVERGED, but Gemini found the real gap

Both halves agree on v1: regex claim-extraction (task-id + status token), accept-but-flag LOUD
at write, re-check LIVE at boot with a mismatch banner, forward-looking phrasing excluded,
ledger parse-error fails-open to "unverifiable". The sol/T090 event tonight is the live test
case (grant cites T090; ledger has no T090 → v1 would flag it at boot).

**GEMINI HOLE 1 (the important one): flagging is not re-ranking.** v1 DETECTS the mismatch but
the PRECEDENCE_DOCTRINE still ranks notes ABOVE live evidence, so a warned-against lie can
still be believed. The true C9 fix makes the **task ledger the PRIMARY source for task-status
claims** — a note's status claim is rendered THROUGH the ledger (ledger value shown, note value
marked as the claim), not merely annotated. **Routing:** v1 ships as designed (detect+flag,
the mechanical brick), and a **v1.5 re-rank** is added to the program: for the specific,
mechanically-checkable class of task-status claims, boot renders the LEDGER value as canonical
and the note as a (possibly-stale) assertion. This stays within "mechanical, no-model" — it's
a precedence override for exactly the claims P1 can verify, not a general trust re-architecture.
- **Pins:** fabricated "T075 DONE" (ledger: parked) → write-flag + boot-banner; true claim
  clean; stale-flip caught at boot; garbage body never crashes (fail-open + counter); boot
  overhead < 50ms at 25 notes; **v1.5:** a task-status claim renders the ledger value as
  primary with the note value demoted to "claims:".

---

## S5 · Supervisor + S5/S6 — CONVERGED, Delta C upgraded by Gemini

Both halves agree: owned pid census = the only legal kill-list; `quiesce` (finish-current,
flush, bounded wait) precedes reap; reap REFUSES while a child carries the live-test env marker
unless `--force` (audited); load-bearing pids (wake watchers, MCP servers, UI) on a denylist no
sweep touches. deepseek's S6 reply-dedup is built + reviewed clean (needs commit); his S5
daemon test was failing pre-crash (his continuation states the namespace/token-collision cause).

**DELTA C (census ground truth on Windows) → WINDOWS JOB OBJECTS** (Gemini, better than both).
deepseek's in-memory census + pidfile re-owning is fallible (stale/corrupt pidfiles); claude's
denylist protects specific pids but isn't a general supervisor-child integrity mechanism. The
OS-level answer on Windows: the supervisor spawns **all** managed children inside a dedicated
**Job Object** (`CreateJobObject` + `AssignProcessToJobObject`, `JOB_OBJECT_LIMIT_KILL_ON_JOB_
CLOSE` for reliable group teardown). This makes "cleanup killed the wrong pids" structurally
impossible: the job IS the kill-list, enforced by the kernel, and children can't outlive or
escape it. The in-memory census becomes a convenience view; the Job Object is ground truth.
- **Pins:** cleanup-refuses-mid-test; a planted stranger python pid survives cleanup (job-only
  proof); `--force` emits audit; quiesce flushes in-flight work before reap; **the managed
  children share one Job Object and group-terminate reliably;** load-bearing pids are NOT in the
  job (survive a job kill). S6: Redis-fast-path + Store-backstop dedup, fail-open (4 pins).

---

## New items Gemini surfaced (holes neither half caught)

- **N1 (from Hole 1) — S4 v1.5 precedence re-rank.** Folded into S4 above. The ledger becomes
  primary for the mechanically-checkable task-status claim class.
- **N2 (Hole 2) — shared-memory write integrity.** The crash lost an in-flight synthesis; an
  agent killed mid-write to the shared Store/Redis could leave inconsistent state. PID
  management doesn't cover data consistency. **Routing: PROPOSE a slice** — write-once notes and
  ledger transitions already have some atomicity (RB-8 CAS is the write-integrity foundation per
  T034); audit the mid-write-kill exposure and close it with CAS/transaction discipline on the
  salient write paths. Rides T034/RB-8, not this wave. (Honest bound: the LOST synthesis was
  in-context, never written — no store fix recovers that; the lesson is "land continuously,"
  already doctrine. N2 is about STORED state left half-written, a narrower real risk.)
- **N3 (Hole 3) — per-agent resource isolation.** A runaway agent starving CPU/mem/IO is a
  plausible ROOT cause that could TRIGGER an external cleanup (the very thing that crashed us).
  Windows Job Objects (already adopted for S5) ALSO provide resource caps
  (`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`: memory/CPU-rate/active-process limits). **Routing:
  fold into S5's Job Object** — same mechanism, add per-job resource limits so one agent can't
  destabilize the fleet. High leverage: one primitive (Job Objects) closes Delta C, N3, and
  hardens against the crash's plausible upstream cause.

---

## Build order + gates (for the morning gate)

1. **S2** first — honest gauges before anything measures itself (small, mechanical).
2. **S1** — bisect (mechanism named; fast) → root fix → subprocess backstop. Un-gates T081-W2.
3. **S3** — before ANY acl.json edit lands (so Daniel's grant reviews ride the rails). Note the
   sol grant went in tonight WITHOUT this gate — S3 is retroactively protective.
4. **S4** v1 (detect+flag) + v1.5 (ledger-primary re-rank). Before Jester v1 (its launch gate).
5. **S5** — the crash's root fix: Job Objects (Delta C + N3) + quiesce + census + reap-refusal;
   commit deepseek's S6; green his S5 test. This is C4-2's charter receipt.
6. **N2** — PROPOSE only; rides T034/RB-8, not this wave.

Every slice: pins in the same commit; receipt to docs/failure-ledger-2026-07.md; the category
CLOSES only when the class can't recur (fix-root-causes). Jester v1 stays caged until
S3 + S4 + the P5 quarantine limb are live (its own stated gate).

## Honest bounds
- S1's exact culprit line is a bisect target, not yet proven — but the mechanism CLASS is
  triple-confirmed + has code evidence. The bisect is a build-phase step, not a design unknown.
- Gemini ran on gemini-2.5-flash (2.5-pro/3.x available on the key); a second opinion from
  3.1-pro is cheap if the morning gate wants it. The API 503'd once mid-capture (transient).
- v1.5 re-rank is the deepest change here; it deserves its own fenced review before build.
