# Gemini adversarial review — hardening plan + C7-4 mechanism — 2026-07-17

Status: receipt (verbatim-faithful). Model: gemini-2.5-flash via API (`gemini_web.py --mode
api`; the invisible-Chrome web bridge was blocked by a "Get started" consent overlay — API mode
is the reliable path). Key exposes gemini-2.5-pro + gemini-3.1-pro-preview too; a 3.1-pro second
opinion is cheap if wanted. One capture 503'd (transient high-demand); content below is from the
successful runs. Full asks: scratchpad gemini_ask_A.txt (C7-4 mechanism) + gemini_ask_B.txt
(plan review).

## Ask A — C7-4 mechanism (ranked)

Gemini's #1: on Windows the asyncio **ProactorEventLoop** fails to process pending outbound I/O
completions until a new inbound I/O event wakes it. Ranked mechanism classes:
1. **Subprocess inheriting stdio handles on Windows** (TOP) — a child inheriting the parent's
   stdout/stderr handles leaves the parent's pending `WriteFile` completion deferred until an
   inbound `ReadFile` triggers a full I/O-queue sweep. Evidence: `psutil.Process().children()`
   during boot; **ProcMon** on `CreateProcess`(InheritHandles) + `WriteFile`/`ReadFile` timing.
2. Subtle ProactorEventLoop I/O-buffering interaction (catch-all). Evidence: ProcMon + asyncio
   debug logging.
3. Global stream reconfiguration (sys.stdout/logging handlers). Evidence: `id(sys.stdout)`
   before/after; inspect `logging.root.handlers`.
4. Blocking native/C-extension I/O (incl. a sync Redis client's socket ops under Proactor).
5. Thread explosion / anyio limiter exhaustion.
6. Replacing the asyncio loop/policy from a worker thread.

**Single fastest instrument: Process Monitor (ProcMon)** — confirm subprocess creation + observe
stdout `WriteFile` completion timing relative to inbound `ReadFile`.

→ This independently matches claude's empirical signature (writer parked until next inbound
frame) and deepseek's surface finding (sync tools block the anyio worker). Code evidence found
this pass: `agent_cli.py:2760` uncaptured `subprocess.run` inherits fd1/fd2.

## Ask B — plan review + delta adjudications (verbatim-faithful)

**Delta A (hook registration surface): Claude wins.** Project-level is git-auditable but sessions
genuinely launch OUTSIDE the repo; removing user-level would silently disable hooks there.
Functionality across all launch paths beats it; address user-level auditability by **logging the
effective configuration at session startup**.

**Delta B (human escape hatch): Claude wins.** Bare `git --no-verify` is an unaudited loophole;
an explicit audited override (commit trailer / env var) the hook validates and logs is superior.
Prior art exists in CI/CD + regulated environments.

**Delta C (census/ground truth on Windows): neither fully — augment.** In-memory + pidfiles is
fallible (stale/corrupt); the denylist protects specific pids but isn't general integrity. The
strongest native mechanism is **Windows Job Objects**: spawn all managed children in a dedicated
Job Object for reliable group termination + OS-level guarantees surpassing pidfile re-owning.

**Top 3 uncaught holes:**
1. **S4 flags but doesn't re-rank.** The context system still ranks notes ABOVE live evidence;
   detecting contradictions without changing the ranking means a warned-against lie can still be
   believed. A true fix makes the ledger the PRIMARY source for status.
2. **No shared-memory transactional guarantee.** An agent killed mid-write can leave shared state
   inconsistent/corrupt; PID management doesn't address data consistency (the crash lost an
   in-flight synthesis).
3. **No per-agent resource isolation/limits.** A runaway agent (CPU/mem/IO) can destabilize the
   fleet and TRIGGER external cleanup — the very thing that crashed us. Job Objects also provide
   resource caps.

All three are routed in the reconciliation (S4 v1.5 re-rank; N2 rides T034/RB-8; N3 folds into
S5's Job Object).
