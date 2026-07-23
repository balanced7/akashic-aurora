# Reconciliation — MCP-door concurrency + leverage map (the build spec)

Status: current (RECONCILED — awaiting Daniel's gate; kimi stranger-test OWED, rides the
gate as acceptance re-test per W53/W55 precedent)
Type: reconciliation · Arc: interface / System-5 door · Date: 2026-07-23
Voices: claude (opening + addendum + corrections C-1/C-2) · deepseek (counter, full) ·
gemini (two captures, weighted LOW then HIGH; second CLIPPED-stamped) · kimi (brief filed,
unseated tonight — its two named targets were independently corrected by the other voices)

**Daniel's charter (verbatim):** "Review your recent boot and lets start building what
would make it better and easier. Can we modify our mcp to allow concurrent calls? do we
need to swap it out I want everyone's thoughts on this. both your ergonomics and the mcp
concurrancy" — widened mid-round: "how many of our concurrent agents and wake and all the
rest can be solved by us leveraging the multithreaded -ness and concurrency in the MCP?
Have everyone think on what we can improve by improving our setup and the interface with mcp"

**Answer to the charter question:** MODIFY, don't swap — unanimous across voices, each by
its own route (claude: mechanism is ours not the SDK's; deepseek: "the SDK isn't the
problem, our dispatch pattern is"; gemini: 2.x/3.x interface-shift cost marker).

---

## Earned convergences (independent arrivals, not copies)

1. **O1 modify-in-place is the fix.** async tools + `anyio.to_thread.run_sync` +
   swap-once THREAD-LOCAL stdout proxy + tiered concurrency + Popen DEVNULL. deepseek
   priced the alternative (mutex-guarded redirect_stdout: simpler, but serializes READ
   capture and defeats the tier) and concurred on throughput grounds.
2. **Tier correction C1 (deepseek, ADOPTED):** `consume=true` paths of bifrost_sync /
   bifrost_inbox are cursor WRITES → move to the WRITE tier. RB-21 already guarantees
   correctness (seat fence); the tier move is for ordering semantics. 28/30 verbs were
   correctly assigned in the opening; this was the gap.
3. **Send serialization rationale (deepseek C2, ADOPTED):** bifrost_send/broadcast/nudge
   serialize not for thread-safety (redis-py pool is fine) but for human-visible ORDERING.
4. **A1 await-tool must be WINDOWED (gemini + claude C-2):** block ≤ ~5s per xread, hard
   ceiling under the client's per-call timeout; propagate CancelledError into the read;
   watch to_thread pool depth when many awaits park.
5. **O1.5 lease is a HYBRID (gemini + claude C-1):** stdin-EOF death detection (graceful:
   DELCONSUMER + lease delete) PLUS ~2s heartbeat / ~5s TTL (violent kill: fleet reclaims
   via XPENDING/XCLAIM). Zombie window 1800s → ~5s, honestly never zero.
6. **The membrane STANDS (deepseek §3, adopted as a LAW of this arc):** the MCP door is
   for SEAT-MODEL agents (Claude Code / Cursor — shell-less, per-turn). Runners keep the
   CLI/bus door and their single-consumer drain loops; a runner consuming through MCP
   would fracture the single-consumer invariant. O3 may serve runners PEEK/status only.
7. **O3 singleton sequencing (all voices):** O3 requires O1's internals (multi-client =
   real concurrency), its lifecycle is a P1 ManagedChild ("build once use twice"), AND —
   gemini's sharpest grain — process isolation disappears, so ENFORCED IDENTITY becomes
   mandatory. That is the THIRD Daniel thread (remote-steering SEC-01/S-0, R001 Part B
   caps, now O3) pointing at the same missing primitive. O3 is BLOCKED-ON-IDENTITY by
   design, not by accident.
8. **Shared-state audit (deepseek §2, standing record):** module-global caches
   (_REACHABILITY_CACHE, trust registry _CACHE, Bus._unmapped_loud_seen) are
   optimization-not-correctness state; races produce redundant work, never corruption.
   consume_inbox is fence-safe for same-agent AND cross-agent concurrency.

## The corrected O1 build spec (pre-registered pins)

- P-1 every tool `async def` → `anyio.to_thread.run_sync(body)`; loop never starved.
- P-2 swap-once thread-local stdout proxy at server start; per-call redirect_stdout dies.
- P-3 tier map: READS concurrent (deepseek §2a roster) · WRITES + consume=true + all bus
  sends serialize under ONE lock (ordering) · diag tools follow their body's tier.
- P-4 gemini_web_login Popen → stdin/stdout/stderr=DEVNULL.
- P-5 fence flips: C2 + C3 green; C1 green at N=20 mixed concurrent calls.
- P-6 FULL suite no new reds vs baseline (fence_commits_before_full_suite).
- P-7 live drill: a real harness batch of 3 akashic calls including one slow verb returns
  clean; cancellation of an in-flight slow call actually cancels.
- P-8 verify the Windows event-loop policy mcp.run() installs; pin Proactor if subprocess
  paths demand it (gemini grain — VERIFY, don't assume).

**Build ownership (law 6, volunteered):** claude builds O1 (its diagnosis, its fence, the
door its seat-class uses); deepseek fences/verifies as armor — the inverse of the usual
direction, deliberately. Daniel may reassign at the gate; R001 Part A default (whole-arc
to deepseek) was offered and deepseek's counter chose concurrence over claim.

## Slice order proposed to Daniel

**O1 (now) → O1.5 + A1 (next, cheap structural wins) → P1 daemon (already reconciled) →
O3 singleton (blocked on the identity primitive — converge with SEC-01/SA-1).**
D-road (in-session verb traffic CLI→MCP for harness seats) rides behind O1 with T081-W2
attachment; F5/W63 correction (deepseek F12): the quoting genus is CLI-only — ToolBox
already solves it; W63 stays a CLI wish, smaller than the census feared.

## Census additions (deepseek F10-F12, filed)

F10 runner restart-reason line in the daemon respawn summary (wish, deepseek lane).
F11 runner tool-bridge MTU gate: refuse-loud is correct but auto-split at tool-arg level
is the P2 genus applied to the bridge (T064 intake-spill; wish, deepseek lane).
F12 F5 correction as above.

## Kimi-owed stamp

kimi's brief (research/briefs/kimi-mcp-concurrency-fresh-eyes-brief-2026-07-23.md) targets
the two claims already corrected by other voices (L3 lease strength; A1 cancellation) plus
the receipts-reproduce check. Its pass runs as the gate's acceptance re-test; if it finds
what three voices missed, the spec amends BEFORE build per standing round protocol.

## At Daniel's gate (this round adds to the standing package, does not jump it)

1. Ratify this spec + the slice order (or reassign build ownership).
2. Rule whether O1 builds immediately post-ratification (rec: yes — single file, fenced,
   reversible) with kimi's re-test riding acceptance.
3. The OPTICS charter (Daniel steer 2026-07-23 ~02:45, verbatim in note
   steer-ui-visibility-2026-07-23): live per-agent NOW-card on the :8787 console — task,
   status, substep/plan, realtime action+reasoning stream. Chartered to deepseek (UI
   integration is its lane; T002 is the natural home) with claude owning the backend
   narration feeds for every seat class. Tonight's receipt makes the case: deepseek turned
   a 13.7KB counter in 162s at quality 95 and the human watching the console COULD NOT SEE
   IT HAPPENING. The fleet's work is invisible at exactly the moments it is most alive.
