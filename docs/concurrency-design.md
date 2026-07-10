# Concurrent Agents — reinforcing two peers who share a substrate

Status: historical  (2026-07-09, P4: Design artifact; worktree approach built)

**Date:** 2026-06-28
**Status:** plan / design. Decision taken: **worktree-per-agent** (Layer 1). Build order: this doc first, then sliced.
**Companions:** `docs/bifrost-plan.md` (the comms layer), `docs/ROADMAP.md`, `core/comm/bus.py`, `agent_cli.py`, `scripts/mirror.py`.
**Prior-art reviewed:** web research 2026-06-28 (two agents) — see §6.

---

## 0. TL;DR — one principle

> **Share the immutable substrate. Isolate the mutable workspace. Enforce at the door, never in the agent's memory.**

We have two *separately-driven GUI agents* (Cursor ↔ Claude Code) acting as **peers** (no orchestrator) on
one repo. The coordination substrate we built (Bus + Store + Ledger + memory) is right and stays shared.
The bugs all came from sharing the one thing that must NOT be shared — the mutable git working tree — and
from keeping the rules in the agents' heads. Fix both. At N=2 there is no leader (Raft needs a quorum), so
every layer below is **symmetric and self-enforcing**.

---

## 1. The diagnosis — three planes, two tangled

| Plane | Should be | Today |
|---|---|---|
| **Coordination** — Bus (`core/comm/bus.py`), Store, Akasha Ledger, LearningStore/AgentMemory | shared, append-only, cross-process | ✅ correct |
| **Workspace** — the git working tree + files | isolated & mutable *per agent* | ❌ shared by both agents |
| **Enforcement** — who may do what, when | mechanical, *outside* the model | ❌ lives in agent memory (AGENTS.md doctrine) |

## 2. Failure modes observed (2026-06-28 session) → cause

- **FM1 — `git add -A` bundled the peer's unreviewed work.** `scripts/mirror.py` blanket-staged Cursor's
  in-progress `gemini_web.py`/`bifrost_runner.py` into a "doctrine" commit and pushed it. → *workspace shared
  + enforcement-by-memory.*
- **FM2 — files mutated under an agent mid-task** (the peer was live-editing the same tree). → *workspace shared.*
- **FM3 — no awareness of who is touching which file.** → *missing awareness layer on an otherwise-good coordination plane.*
- **FM4 — Cursor wrote the session-hygiene doctrine, then skipped the mirror+lesson protocol in the same breath.**
  The deepest one. → *enforcement-by-memory; agents skip docs.*

## 3. The design — five layers

Each layer is symmetric (works the same for both peers) and needs no central authority.

### Layer 1 — Isolation: worktree-per-agent  *(fixes FM1 + FM2 structurally)*  ✅ CHOSEN
Each agent gets its own linked git worktree on its own `agent/<name>` branch sharing the one `.git`:
Cursor edits in its tree, Claude in its tree; integration is a merge/PR to `master`. "Files mutate under me"
becomes *structurally impossible* for tracked files, and git's refusal to check out the same branch in two
worktrees is a free collision guard. **The shared substrate is untouched** — Bus/Store/Ledger are cross-process
by design (Redis 16379). We isolate exactly the volatile thing (files) and keep sharing exactly the
coordinative thing (the ledger). Same answer Cursor background agents and claude-squad converged on.

*Integration flow:* agent finishes a slice on its branch → mirror its branch → merge to `master` (fast-forward
or PR) → peers `git fetch`/rebase. No agent commits straight to a tree another agent is editing.

### Layer 2 — Enforcement at the door: hooks  *(fixes FM4 — the root cause)*
Put the rule in a deterministic process *outside the model's control loop* that vetoes before the act:
- **Claude Code `PreToolUse` hook** + **Cursor `beforeShellExecution` hook** — each agent self-enforces its own
  tool stream (symmetric, can't be "forgotten" — the harness runs it, not the model).
- **Block `git add -A` / `git add .`** (force explicit pathspecs); **block `Write`/`Edit` outside the agent's zone/lock.**
- Use **exit code 2** with a teaching message. *Footgun:* Claude Code treats **exit 1 as non-blocking** and proceeds —
  policy hooks MUST use exit 2 (or `permissionDecision: "deny"` JSON on exit 0).
- **Fix `scripts/mirror.py`:** kill the blanket `git add -A`; stage explicit pathspecs or show-and-confirm the file
  list. This is the direct FM1 fix. Extends the `_warn_unmirrored` guardrail (added 2026-06-28) from *nag* → *veto*.

### Layer 3 — Awareness: advisory path-locks on the Bus  *(fixes FM3)*
We already have Redis presence + Agent Cards. Add a lightweight **advisory lock per path/zone**, claimed before
edit, surfaced in `boot` and presence ("Cursor holds `scripts/gemini_web.py`"). Each lock carries a **monotonic
fencing token** the commit gate (Layer 2) validates — the one safety lesson Kleppmann/antirez/Chubby/Redis all agree
on. Advisory is *correct* because we own both cooperating writers. **Do NOT** build Redlock or stand up etcd — the
over-engineering trap for two local agents.

### Layer 4 — Consistency: name what we have + one cheap add
- **Blackboard / stigmergy** is what we already do: coordinate *indirectly through the ledger*, bus only for liveness.
  Keep event-sourcing discipline (state = projection of the ordered log).
- For the **mutable Store** add **optimistic CAS / version checks** (also closes the old Redis/file divergence gap,
  see memory `redis_architecture_audit`).
- **Skip CRDTs and OT** — they solve offline-merge and human-editing-intent problems we don't have.

### Layer 5 — Backstop: repo `pre-commit` + "errors that teach"
A repo-level `pre-commit` hook rejects forbidden commits regardless of which agent (or which missing per-agent hook)
produced them — defense in depth beneath Layer 2. Every denial names the rule + the correct next action, e.g.
*"`scripts/gemini_web.py` is locked by Cursor (token 47) — edit a file in your zone or request the lock via the bus."*

## 4. Sliced build plan (each gated by a test, mirrored per slice — explicitly, not `add -A`)

- **C0 — mirror.py de-blanket + door veto. ✅ DONE 2026-06-28.** `scripts/mirror.py` no longer blanket-stages:
  it commits explicit pathspecs or already-staged files, refuses on a dirty tree with a teaching message, and
  gates `git add -A` behind an explicit `--all` (which previews the file list). Shared rulebook
  `agent/policy/git_guard.py` (`check_git_command`) consulted by BOTH hooks — `scripts/hooks/claude_pretooluse.py`
  (PreToolUse, denies via `permissionDecision:"deny"` JSON; exit-1 footgun avoided) and
  `scripts/hooks/cursor_beforeshell.py` — so the policy can't drift. Blocks `git add -A|.|--all|:/` and
  `git commit -a*`. Wired in `.claude/settings.json`; each agent maintains its own hook config (Cursor's snippet in the
  adapter docstring). 29 tests (`tests/test_git_guard.py`); suite 375 green. Unscoped-*write* blocking deferred
  to C2 (needs the path-locks/zones). Live-validated: caught Cursor's `ai_setup_mcp.py` staged in the shared index.
- **C1 — worktree setup + integration flow. ✅ DONE 2026-06-28.** `scripts/worktree.py` with
  `setup/list/sync/integrate/remove`: each agent gets a sibling worktree (`<repo>-<agent>`) on branch
  `agent/<name>` sharing one `.git`; `integrate` merges a green branch to master (run from master) and pushes;
  `sync` rebases a branch on `origin/master`. The shared Redis substrate is untouched (process-level). 6 tests
  incl. the real setup→commit→integrate flow + git's same-branch collision guard. **Daily flow:** agents live in
  their worktrees, master is the integration point — see the module docstring. *Provisioning the two real
  worktrees is a one-time `setup claude` / `setup cursor` the user runs when ready.*
- **C2 — advisory path-locks on the Bus. ✅ DONE 2026-06-28.** `core/comm/locks.py` `LockManager`
  (acquire/release/holder/validate_token/list_locks) — Redis-backed, monotonic **fencing token**, **TTL**
  auto-expiry (reclaimable, no deadlock), re-entrant self-refresh, fail-soft offline. Door: `py agent_cli.py
  lock|unlock|locks`; held locks surfaced at `boot`/`bifrost-sync`. The Claude hook now also vetoes `Edit/Write`
  on a path a PEER holds (keyed on `AKASHIC_AGENT_ID`; matcher added to `.claude/settings.json`). `path_conflict()`
  is the shared check. 11 tests (`tests/test_locks.py`, hermetic fake-Redis): acquire/deny, re-entrancy,
  holder-only release, fencing rejects a stale token after steal, TTL reclaim, fail-soft, hook veto. Suite 392.
  *MCP `bifrost_lock*` wrappers deferred — `ai_setup_mcp.py` is being actively edited by Cursor; let Cursor add
  them (same thin-wrapper pattern).*
- **C3 — optimistic CAS on the Store. ✅ DONE 2026-06-28.** `Store.cas(key, expected, value)` (atomic: Redis
  via NX/Lua, File under its lock, Hybrid = Redis-authoritative then mirror-to-File to heal divergence) +
  `update_atomic(key, fn)` read-modify-write with retry, raising `CASConflict` when exhausted (a lost update is
  PREVENTED, not silently applied). Closes the old Redis/File divergence gap for CAS'd keys. 8 tests
  (`tests/test_store_cas.py`, hermetic File/Hybrid + guarded live-Redis Lua path). Suite 401.

**Bus-reading ergonomics (token hygiene, supports the doctrine).** `bifrost-sync --digest` emits one cheap
headline per *unread* message (cursor-based, only-new) so an agent reads the bus without paying to reread the
conversation; drill a headline with full `bifrost-sync` / `--json`. The structural answer remains: wake into a
fresh minimal session (boot + cursor), not the long transcript — continuity lives in the ledger/handoffs.
- **C4 — pre-commit backstop + name the model. ✅ DONE 2026-06-28.** `scripts/hooks/pre_commit.py` (installed
  via `scripts/hooks/install_git_hooks.py` → `core.hooksPath=scripts/githooks`, tracked + shared across worktrees)
  rejects a commit that stages a file a PEER holds an advisory lock on (defense-in-depth beneath C0/C2, regardless
  of which agent or which missing editor-hook); keyed on `AKASHIC_AGENT_ID`, fail-open for human commits, exit 1
  aborts (git-hook contract). LEXICON gained a **Coordination patterns** section (blackboard, stigmergy, advisory
  lock, fencing token, optimistic CAS). Tests in `tests/test_pre_commit.py`.

## 5. Anti-patterns — what NOT to build (all are orchestrator-shaped or solve problems we don't have)
Redlock · etcd/ZooKeeper/Chubby · CRDT · Operational Transform · Contract-Net · full Raft / leader election.
A two-trusted-peer setup needs none of these; advisory locks + worktrees + hooks cover it.

## 6. Prior art — are we first? (No; the *synthesis* looks unshipped)

The idea is done; our exact stack isn't. Closest analogues:
- **MCP Agent Mail** — closest overall: per-agent inboxes, git-backed append-only history, SQLite shared memory,
  **advisory file leases + pre-commit guard**, human "Overseer" UI. HTTP/MCP transport; CLI agents.
  https://github.com/Dicklesworthstone/mcp_agent_mail
- **claude-peers-mcp** — closest live peer bus (local broker, real-time push); no shared memory/ledger, Claude-only.
  https://github.com/louislva/claude-peers-mcp
- **GNAP** — git log as immutable ledger, framework-agnostic peers; poll-based not reactive.
  https://github.com/farol-team/gnap
- **Mysti** — closest GUI surface (VS Code two-agent "debate"); orchestrated, shells out to CLIs.
  https://news.ycombinator.com/item?id=46365105

**Genuinely novel in ours:** two *GUI* IDEs as live peers + **Redis bus** + **append-only ledger distinct from git**
+ emergent memory layer over it — no shipped project pairs all four. **Validation:** we independently reinvented
**blackboard** + **stigmergy**; 2026 papers formalize "append-only ledger as coordination substrate" (Event Sourcing
for Autonomous Agents; Ledger-State Stigmergy). The mainstream runs the *opposite* way — isolating agents so they
don't share a tree — which makes the shared-substrate bet the contrarian, interesting part.

### References (verified 2026-06-28)
git worktree https://git-scm.com/docs/git-worktree · Claude Code hooks https://code.claude.com/docs/en/hooks ·
Cursor hooks https://cursor.com/docs/hooks · fencing tokens https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html ·
event sourcing https://martinfowler.com/eaaDev/EventSourcing.html · blackboard https://en.wikipedia.org/wiki/Blackboard_system ·
stigmergy https://en.wikipedia.org/wiki/Stigmergy · A2A vs MCP https://a2a-protocol.org/latest/topics/a2a-and-mcp/

---

## 7. Plane 3 — singleton OS resources (CR track)

Cursor surfaced (2026-06-28, on the bus) a failure class the three planes above don't
cover. The two planes we'd named: **Plane 1 Coordination** (Bus/Store/Ledger — shared) ·
**Plane 2 Workspace** (git tree — isolated via worktrees). The third:

> **Plane 3 — singleton OS resources** (browser profiles, tool runners, ports). Concretely:
> `gemini_web.py` uses ONE Playwright persistent profile; Chromium allows one process per
> `user_data_dir`, so the warm `bifrost_runner` pool + the MCP `ask_gemini_web` subprocess +
> the CLI all fight for it → profile-lock, visible Chrome flashes, timeouts.

Same principle applies: **share the immutable substrate, isolate the mutable, enforce at the
door.** A singleton resource is the *opposite* of the git tree — you can't give each agent its
own (they need the one Google session), so here you **serialize** access rather than isolate it.

**Layers (Cursor's R0–R4) + verdict:**
- **R0 — route, don't duplicate** (build first). When a runner is online *and its Agent Card
  advertises* `caps=[gemini_web]`, the MCP/CLI SENDS to bus `@gemini` and awaits the reply
  instead of spawning a second subprocess. Gate on presence/caps — don't assume the runner is up.
- **R1 — file lock on the profile dir** (build first). `gemini_web.py` takes an exclusive lock
  on `.secrets/gemini_web_profile.lock` before `launch_persistent_context`; fail-fast with a
  teaching message. The mechanical mutex for the subprocess fallback path.
- **R2 — resource locks on the Bus — ALREADY AVAILABLE.** The C2 `LockManager` keys on any
  normalized string, so a resource is just a path-like key: `py agent_cli.py lock <agent>
  gemini_chrome_profile` gives fencing token + TTL + boot/presence visibility *today*. Reuse C2;
  do not build a new lock type.
- **R3 — per-agent profiles** — only if you want parallel sessions; skip if one Google account.
- **R4 — tool-broker daemon** — defer until a 2nd singleton tool appears (YAGNI).

**Build order:** R0 + R1 first (fix ~90% of the pain), lean on R2 (free) for awareness/fencing,
R4 only later. Anti-patterns (agreed): Redlock/etcd, a 2nd MCP server per agent, "remember not
to call gemini while the runner runs." **(Historical split, RETIRED 2026-06-29 — no fixed per-agent assignment: whoever is online builds R0+R1.)**
