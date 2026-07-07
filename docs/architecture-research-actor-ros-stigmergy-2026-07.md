# Research detour: Actor/OTP · ROS · Stigmergy — does it steer the plan?

Prompted by Gemini's suggestion (2026-07-06) to study Erlang/OTP, ROS, and game-engine
stigmergy as the real teachers for an "Agent OS." Assessed against what we've actually
built (L0–L3b) and the mitigation roadmap. Verdict + concrete steers below.

## TL;DR verdict

**Mostly CONFIRMS.** The L0→L4 liveness/recovery arc *is* an Erlang supervisor tree and a ROS
managed-node lifecycle — we've been building the right thing by feel. The value of the detour is
**three concrete steers** that sharpen it, plus one **reframe** of the orchestration track that
could remove a whole class of the "agents race / chatty coordination" pain deterministically.

---

## 1. Erlang/OTP + Actor Model — CONFIRMS, with formalization steers

**Already true in Akashic (unnamed):**
- The **actor model** = the Bifrost bus. Agents share no memory; they communicate by immutable
  message-pass into a per-agent inbox + cursor (`core/comm/bus.py`). That's textbook actors.
- **Supervisor tree** = `launcher` + L3b `revive` + `_restart` (backoff/cap/reset) + L4 (planned).
- **"Let it crash"** = the entire L0–L4 thesis: don't defensively prevent every failure; isolate,
  detect, restart. L0 (self-heal hung calls) and L3b (one-click revive) are pure OTP philosophy.

**Steers (things OTP does that we don't yet):**
- **S1 — Restart *strategies*, not just restart.** OTP supervisors declare a strategy:
  `one_for_one` (restart just the dead child), `one_for_all` (restart all siblings — for agents
  with shared invariants), `rest_for_one` (restart the dead child + those started after it).
  Today `_restart` is implicitly one-for-one. Worth making explicit per-agent in the spec, because
  some agents *do* have coupling (e.g. a builder + its verifier).
- **S2 — Restart *intensity* → escalation up the tree.** OTP: if a child restarts >N times in T
  seconds, the supervisor itself fails and escalates to *its* parent. We have the leaf version
  (`RESTART_MAX_ATTEMPTS` → bus note). The steer: make escalation *hierarchical* — leaf agent →
  its supervisor group → the human. This is L4's shape.
- **S3 — Supervised STATE ROLLBACK (the new idea).** Gemini's sharpest point: on a catastrophic
  mid-surgery failure, a supervisor should *truncate the corrupted file state using the snapshot
  substrate* before restarting. We have `scripts/snapshot_knowledge.py` (proven restore) but the
  supervisor does NOT roll back an agent's file damage on revive. **This is genuinely new to the
  roadmap:** revive currently restarts the *process*; it doesn't undo the *file damage* a wedged/
  rampaging agent did. Pairs naturally with L3d (convos preservation) → "recover process AND state."

## 2. ROS (Robot Operating System) — CONFIRMS, with a lifecycle-state steer

**Already true:** pub/sub bus + node **presence** (`bifrost:presence:*`) + our new **worklive**
telemetry (L1) is exactly ROS node introspection. The roster is a `rosnode list`.

**Steers:**
- **S4 — Formalize the agent LIFECYCLE as a state machine (ROS 2 managed nodes).** ROS 2 lifecycle
  nodes have an explicit FSM: `unconfigured → inactive → active → finalized`, with defined
  transitions. Today Akashic uses ad-hoc status strings (`running/exited/killed/wedged/never_launched`).
  Promoting this to a real FSM (e.g. `spawned → onboarding → idle → working → wedged → draining →
  dead`) makes the supervisor logic, the UI, and L3b/L3e transitions deterministic instead of
  string-sniffing. worklive already emits the substates; this just names the machine.
- **S5 — Safety conflicts are NOT negotiated (validates "deterministic first").** ROS: "a robot
  can't wait for a social negotiation to decide if it's hitting a wall." This is a direct
  endorsement of the corpus lesson *make it deterministic first, no model in the loop*
  (`sprint_pattern_deterministic_before_llm`) and a mild **critique of the negotiation-round gate**
  for *safety-critical* conflicts. Steer: reserve `negotiate()` for taste/design disagreements;
  use a deterministic gate (lock + fencing token) for "two agents about to write the same file."
- **S6 — actionlib (goal → feedback → result, with preempt).** ROS long-running actions have a
  standard shape: a goal, streamed feedback, a result, and preemption. That's our task execution +
  worklive feedback + halt/nudge preemption — worth formalizing so every task is preemptible and
  reports progress uniformly (feeds the barrier/adjudicator work in Wave 3).

## 3. Game engines / Stigmergy — the REFRAME (biggest steer)

**The idea:** units coordinate by leaving **markers in the environment** that alter others'
behavior (ant pheromones), not by messaging each other. Claiming a file = dropping a **lease** in
Redis; another agent's planner *reads the environment and routes around the leased zone* — collision
**avoidance** (steer away before conflict) rather than collision **resolution** (try, fail, negotiate).

**Why this steers Wave 3 (orchestration) hard:**
- Our current instinct for G1/G2 (racing, heterogeneous agents) leans on **negotiation rounds** and
  a **sync barrier** — both are *conversational*, model-in-the-loop, chatty, and (per the retro) a
  place agents get derailed. Stigmergy replaces most of that with a **read-the-environment**
  primitive: leases + zones are deterministic, need no model, and scale.
- Akashic already has proto-stigmergy: `runner_lock` + advisory path holds are markers others can
  `holder()`-read. The steer is to **make claiming environmental and reading-first**: an agent's
  planning step consults the lease map and *doesn't even attempt* a leased zone. That directly
  attacks the "agents race" pain without a barrier's absent-adjudicator deadlock risk.
- **Navigation-mesh / zones:** partition the repo into neighborhoods; an agent's writable surface is
  a navmesh region (this is also the S1 safety scope + the hat's `path_scope`). Coordination becomes
  spatial, not social.

**Net:** stigmergy doesn't replace the barrier entirely (you still need a sync point for
"everyone checkpoint now"), but it demotes negotiation from the default coordination mechanism to a
fallback for genuine *judgment* disputes. That's a real change to how Wave 3 should be designed.

---

## Direct answer: Redlock vs event-loop for `path_conflict()` locks?

**Neither — and the framing hides the real answer.**

1. **Not the Python event loop.** Collision checking inside one runner's event loop can't coordinate
   *across processes* — a check-then-act in Python is a classic TOCTOU race between two runners.
   Cross-process mutual exclusion must live in the shared substrate (Redis), not in-process.

2. **Not full Redlock.** Redlock (N independent Redis masters + quorum) exists to remove a single
   Redis as a lock-correctness SPOF. Akashic has **one** Redis (the bus) and a handful of local
   agents; a 5-node Redlock quorum is massive overkill, and Redlock is *correctness-controversial*
   anyway (Kleppmann: under GC pauses / clock skew it can't guarantee mutual exclusion **without
   fencing tokens**; antirez rebuts, but the consensus for correctness-critical is: use fencing).

3. **What we already do is right + one addition.** `runner_lock` uses a **single-node atomic**
   `SET key val NX EX` with a **unique per-instance token** + heartbeat + TTL. Redis is
   single-threaded, so `SET NX` is atomic — there is **no** microsecond check-then-set race to worry
   about. That's the correct primitive. The missing piece for *file writes* is the one your own
   corpus already named (`concurrency_c2_path_locks`): a **monotonic fencing token validated at the
   commit/write gate.** The lock prevents the common case; the fencing token catches the pathological
   one — agent A acquires the lease, stalls past the TTL, B acquires, A wakes and tries to write with
   a **stale** token → the write gate rejects it. Deterministic, cheap, no quorum.

**So:** keep the single-node atomic advisory lock as the stigmergic **lease** (readable, so planners
route around it — the game-engine steer), and add **fencing tokens checked at `_prewrite`/commit**
(the Erlang "supervised state integrity" + the C2 lesson). This is exactly where the Safety cluster
(B-track) and this research converge.

---

## What actually changes in the roadmap

- **NEW: S3 supervised state rollback** — on a watchdog/rampage kill, roll the agent's file damage
  back via the snapshot substrate before/at revive. Fold into **L3d** ("recover process AND state").
- **NEW: S4 lifecycle FSM** — promote status strings to a named state machine; cleaner L3/L4 + UI.
- **REFRAME Wave 3 (G1/G2)** — lead with **stigmergic leases + zones (read-the-environment)** as the
  default coordination; demote negotiation/barrier to judgment-dispute + explicit-checkpoint fallback.
  This lowers the model-in-the-loop surface that the retro flagged as a derailment source.
- **CONFIRM the locking design** — single-node atomic lease + fencing token at the write gate; not
  Redlock, not event-loop. Merges the B-track write-gate work with the coordination track.
- **CONFIRM L0–L4** — it's a supervisor tree; keep going, and formalize restart strategy/intensity
  (S1/S2) when L4 lands.

None of this invalidates the shipped work (L0/L1/L5/L3a/L3b all stand). It sharpens L3d, L4, and
especially Wave 3, and it gives the locking design a principled spine.
