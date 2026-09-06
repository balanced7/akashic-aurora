---
akashic_id: art_20260906_reliability-blind-deepseek_3cbcab
akashic_sha: 6e35d8289e69
schema_version: 1
status: current
type: report
date: 2026-09-06
title: reliability-blind-deepseek
gist: "# Reliability round — blind half, deepseek · 2026-09-06 *Verbatim from the bus; persisted untouched by claude before synthesis. Author state"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [bus, agent-lifecycle, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-06T12:22:30"
updated: "2026-09-06T12:22:30"
---
<!-- GENERATED PROJECTION of art_20260906_reliability-blind-deepseek_3cbcab -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# reliability-blind-deepseek

# Reliability round — blind half, deepseek · 2026-09-06

*Verbatim from the bus; persisted untouched by claude before synthesis. Author states the blind held.*


---
*[bus 1788711239932-0]*

Found it. The incident is *already documented in the code itself*, verbatim, dated this morning. `daemon_state.py` has a section header `# ---- restart re-arm (2026-09-06 incident)` and `rearm_orphaned_sessions()` with a full write-up of **exactly the miss you asked about**. And the daemon log I read confirms it: `[daemon] up ... mode=listener-manager`, then `marker sweep removed=1` repeatedly â€” and the `.log` shows no listener-spawn line at all, meaning after the self-restart, the watcher was never re-armed.

Here is the work, delivered in full, no further promises.

---

## What actually happened this morning â€” now traced, not suspected

From `state/daemon-claude.log` and `core/comm/daemon_state.py`, the failure chain is specific and self-documented:

1. **The claude autopilot daemon self-restarted to pick up a commit** (`[daemon] up ... pid=9572 mode=listener-manager`, ~03:52).
2. **The restart killed the wake listener, because the daemon owns it as a managed child.**
3. **The listener left no `.rearm` trigger** â€” a kill is not a deadline self-cycle, and `write_rearm_trigger` is *by contract* never written on a non-deadline exit (R18).
4. **`consume_rearms()` stayed idle and CORRECT** â€” no trigger input, so nothing to spawn.
5. **The seat sat deaf** while the three truthfulness replies landed, and the daemon reported nothing wrong.

The exact words are in `daemon_state.py`, in `rearm_orphaned_sessions()`:

> "A supervisor that owns a worker must re-arm it after the SUPERVISOR'S OWN restart: a restart is not a deadline cycle, so the worker's exit path cannot be relied on to leave a recovery note."

And the closing rule, which is *precisely* the answer to your question:

> "This failure class exists whenever the recovery mechanism's input is produced by the component that died."

That is the root cause, stated in the code by whoever triaged it this morning: **the recovery input (the `.rearm` trigger) is produced by the same component (the listener) that died. The restart killed both the listener AND its own recovery note.** A circular dependency where the watchdog's alarm and the watchdog itself share a fate.

---

## Why your backup-wake idea is right â€” and what it must key on

Your mechanism â€” "if another seat finishes and sends, and X elapses, wake the idle seat to check" â€” is the correct *category*. But the incident sharpens it into something more precise, and I want to hand you the sharpened form, because it's what makes the difference between a mechanism that works once and one that can't silently fail again:

**The backup must be keyed on observable *state*, not on the event that produced it.**

The `.rearm` trigger is keyed on the *event* "the listener died cleanly at deadline." The listener can only write that event if it's alive. The restart killed the event-writer at the same moment it killed the thing being watched. **That is the entire failure in one sentence:** an event-keyed recovery whose event can only be emitted by the thing whose death it's supposed to recover from.

The state-keyed version is your idea, translated out of events:

- **Don't ask "did a listener exit and leave a note?"** Ask **"is there a live listener seat right now, for each session that expects to be wakeable?"**
- "Live listener seat" is an observable file (`bifrost_wake_<agent>_<sid>.pid`) whose *presence* is a fact, not an event. It can be checked by a component with a different lifetime than the listener â€” the daemon's own next tick, a boot-time sweep, *anything* that isn't the listener itself.
- The `.alive` marker already does this and is already the right shape â€” the docstring says so explicitly: "`.alive` is ... touched at SessionStart by the SESSION'S own lifecycle (core/comm/incarnation.py) â€” a different component, with a lifetime that outlives the watcher. That is precisely what breaks the in-band loop."

So the fix that closes *this* incident already has a name in the code: consult `.alive` (state) instead of `.rearm` (event). `rearm_orphaned_sessions()` does it at daemon **startup**. The gap is that it does **not** do it *periodically at runtime* â€” and that's your "X time elapsed" idea, in its correct home.

---

## Your backup wake, concretely â€” the smallest thing that can't silently fail

Here is my proposal, small and concrete as you asked:

**A periodic state-check in the daemon loop, not a new subsystem.**

Every tick (the daemon already ticks, `ttl=60s hb=8s`), ask one question per managed session: **"does a listener seat exist for this session, and is its pid actually alive?"** If a session has an `.alive` marker (meaning "this session expects to be wakeable") but *no* live listener seat, then â€” wait X, and if still absent â€” spawn the listener (the re-arm).

Three properties make this the shape that can't silently fail the way this morning did:

1. **State-keyed, not event-keyed.** "Is there a live seat" is checkable by the daemon regardless of how the listener died â€” clean deadline, kill, segfault, swallowed `TypeError` (which is itself a *prior* incident in the same file, the T167 line: the daemon swallowed a spawn error for weeks). None of those can suppress the answer to a state question, because the state question doesn't depend on the dead thing writing anything.

2. **The recovery input is produced by a survivor.** The `.alive` marker is written by the session lifecycle (`incarnation.py`), a different component that outlives the listener. The daemon reads it. The producer and the trigger are different lifetimes, so one death can't take both.

3. **Idempotent and crash-safe.** If the check fires twice, `rearm_orphaned_sessions` already skips already-triggered sessions; if the spawn fails, the trigger is left for the next tick. No double-arm, no lost recovery.

This is maybe a day of work, not a month â€” it's `rearm_orphaned_sessions()` promoted from "run once at startup" to "run on a cadence in the daemon's tick," gated on the `X` you proposed.

---

## The zoom-out â€” the pattern that's been costing us months

You said "we've been fighting this for months" and "so everything isn't hung up in one complicated convoluted mess." I found the pattern, and it's not complexity â€” it's *one* failure shape repeated:

**Every layer of the recovery stack keys on the event produced by the layer beneath it, and when the bottom layer dies, the whole stack dies with it â€” silently, because each layer only reports through the layer it depends on.**

I can now cite *four* commits of the same disease in this one file:

- **The `.rearm` trigger**: written only by the listener; can't survive the listener's own death.
- **T167** (in `consume_rearms`): the daemon's spawn raised `TypeError`, the `except` swallowed it silently, "the wake autopilot spawned nothing for weeks while reporting nothing."
- **The `_lane_since` per-process cursor** (in `bifrost_api.py`): "every arm is a NEW process, so this seed dies with the call that set it" â€” the re-arm believed the previous arm had fixed the problem, when the arm that *knew* the problem was about to die.
- **The marker sweep**: the daemon only removes `.alive` markers that are **seatless AND >24h old** â€” a stale marker *with* a seat is "idle-but-alive," so the janitor can't even tell the difference between "alive" and "supposed to be alive but the listener is gone" without a separate check.

They are all the same mistake wearing four coats: **a recovery mechanism whose trigger is emitted by the very component it exists to recover.** The fix has one name, and I want you to hold it because it generalizes past wake into every reliability question you'll ask the house:

> **A watchdog must be armed by a signal produced on a path that does not share fate with the thing being watched.**

Your backup-wake is right. The reason it keeps needing to be *re*-proposed, as a backup, is that the primary keeps being built event-keyed and in-band. Stop building the next layer on top of the layer that can die. Build each layer to read a *state* written by something with a different lifetime â€” then no single death can take the alarm with it.

---

## The concrete ask, for the whole house

Three things, all small, all state-keyed:

1. **Promote `rearm_orphaned_sessions()` to a daemon-tick cadence** (the "X time elapsed" sweep you proposed), gated on `.alive`-without-seat. Closes this morning's exact miss and its class.

2. **A "miss counter" that is itself a state, not a log line:** any session with an `.alive` marker but no live seat for more than X increments a counter readable by `sweep`/`glance`. The operator shouldn't have to be the one who notices a seat went deaf. (The `.log` confirms the cost: no listener-spawn line at all, so the human was the only observer.)

3. **The one-sentence house rule, in words not code:** *key every watchdog on observable state written by a survivor â€” never on an event the watched component emits about itself.*

That last one is the thing that would have prevented not just this morning but the T167 weeks-of-silence and the re-arm loop before it. The mechanism you proposed is correct; what I'm adding is the name of the seam it has to live on, because that's the only way it stops being a *backup* and becomes the thing that can't fail.

No sibling reply was read; this was written blind, and the code confirms the incident detailed in `core/comm/daemon_state.py` under `rearm_orphaned_sessions()` â€” dated 2026-09-06 ~03:52, the exact miss you described.
