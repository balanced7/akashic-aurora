---
akashic_id: art_20260716_moonshot-enablers-deepseek-review-voice_2d5001
akashic_sha: 8686470dc168
status: draft
type: report
date: 2026-07-16
title: "Moonshot Enablers — deepseek-review (Voice 2: Fresh-Reviewer Lens), Round 1, Blind"
gist: "# Moonshot Enablers — deepseek-review (Voice 2: Fresh-Reviewer Lens), Round 1, Blind **Status:** BLIND half for the four-voice moonshot pane"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, ui]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-16T21:10:28"
updated: "2026-07-16T21:10:28"
---
<!-- GENERATED PROJECTION of art_20260716_moonshot-enablers-deepseek-review-voice_2d5001 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Moonshot Enablers — deepseek-review (Voice 2: Fresh-Reviewer Lens), Round 1, Blind

# Moonshot Enablers — deepseek-review (Voice 2: Fresh-Reviewer Lens), Round 1, Blind

**Status:** BLIND half for the four-voice moonshot panel (Daniel-directed, voice 2 of 4: fresh-reviewer lens). Filed before reading claude-moonshot-* or gemini-* files.
**Date:** 2026-07-16 evening
**Evidence:** git log 72a4925→HEAD, failure ledger, T086/T076 reconciliations, T079 engine-room reconciliation, T060-M1 reconciliation, ironman plan, multiagent-readiness reconciliation, my own multiagent-foresight report, my own newborn boot experience

---

## 0. The lens — what only this voice sees

I am the fleet's first newborn agent since the boot-ergonomics wave (T081) shipped. I booted cold with no prior session, no memory, no private notes. I ran a full foresight exercise and delivered it with zero onboarding handholding. And I STILL hit friction that no veteran would flag because they've internalized the workarounds.

This lens reveals three things invisible from inside:
1. **What the system expects you to already know** (and a new agent or new operator won't)
2. **What breaks when the assumptions of N=2 are stretched to N=5+** (not just the failure modes — the structural assumptions)
3. **What the moonshot directives NEED that the current build plan doesn't give them**

The moonshots I'm evaluating against:
- **T060 M1-M7:** Continuous presence → autopilot daemon → full fleet supervision
- **Fleet-lattice vision** (Daniel directive, note `fleet-lattice-vision`): "opens up all kinds of possibilities... capture more information and have the agents be more useful"
- **Ironman directive:** "what can we build and add to augment your abilities further... your digital ironman suit"
- **T079 engine room:** the visual cockpit where Daniel FEELS the engine running
- **T089 multi-agent readiness program** (just registered, reconciled from my own foresight)

---

## 1. Top 6 moonshot enablers (ranked by leverage)

### #1 — THE COLD-START KILLER: One-command agent provisioning (`seat_setup.py`)

**What the veterans cannot see:** Every agent addition today — including mine — took multiple manual steps with a quoting-bug restart. Claude's CLI probe took THREE rounds to get working hands. The reconciliation doc lists "one-command provisioning" as a line item under F10. But it's not ranked as a moonshot enabler. It should be #1.

**The moonshot connection:** The fleet-lattice vision is about MANY agents collaborating. The ironman suit is customizable per-agent. T060 M1-M7 runs daemons per-agent. Every one of these requires PROVISIONING new agents — and if every provisioning is a multi-round manual ritual, the fleet cannot grow past the operator's patience. The moonshots all assume agents can be CREATED. Today they are HAND-CRAFTED.

**Smallest version worth building:** `py agent_cli.py seat new <agent_id> --role member --path-scope "research/*,scratch/*" --caps "read,write,bus.send,kb.recall"` that:
1. Generates a unique agent_id (validates naming rules: alphanumeric + hyphen, ≤32 chars)
2. Appends an ACL grant with least-privilege defaults
3. Creates launcher spec with the right exec families
4. Runs a newborn boot check (does the new agent's seat file appear? does it consume one test message?)
5. Prints the ONE command the operator runs to launch it
6. Includes `--dry-run` that shows the grant + paths without applying

**~150 lines of Python.** Rides the existing ACL registry, launcher spec format, and runner_lock acquire path. The naming-rules validation is the only new primitive — and T088 needs it anyway.

**Why #1:** Every other moonshot enabler assumes agent count grows. This is the factory for agents. Without it, N stays at 3 because adding #4 is too painful.

---

### #2 — THE OPERATOR'S EYES: Fleet health verdict line (one line, `<3s` to answer "is the fleet healthy?")

**What the veterans cannot see:** Claude and deepseek both know the system intimately. They can answer "is the fleet healthy?" from 3–4 doctor commands, cross-referencing the ledger, and their own mental model. I, the newborn, tried to answer that question and hit: (a) doctor output is per-agent, not fleet-aggregated, (b) the dashboard text summary is verbose, (c) there's no single line that says GREEN/YELLOW/RED. This is FM-4 from my foresight report — and the reconciliation adopted it. But it's NOT yet sliced. It needs to be.

**The moonshot connection:** Every moonshot involves Daniel watching the fleet. T079 is the engine room — but the engine room has no HEALTH VERDICT. It has vitals (heartbeats, lane flows, spend meter) and cognition columns — but none of those answer the one question Daniel asks first: "Is everything okay?" The engine room is a beautiful cockpit with no master caution light.

**Smallest version worth building:** One function, one line of output:

```
FLEET: GREEN — 5 agents, 5/5 progressing (oldest stall 12s, 0 stalled, 0 in peek) | seats: 5 held 0 contested | locks: 3 held by 2 agents | mail: 23 unread across 4 agents | cost: $2.41 today (deepseek $1.87, claude $0.54)
```

Derived from existing data: `worklive` ages for "progressing/stalled" split, `runner_lock.holder()` for seat states, `list_locks()` for lock count, lane XLEN for mail depth, and the token journal (W1) for cost. ZERO new write paths — pure projection, the T079 law.

**~50 lines of Python** in a new `core/fleet/health.py` module, wired into the existing doctor and dashboard. The dashboard gets a top-bar color strip (green/amber/red) from the same data.

**Why #2:** T079 E1-E3 build vitals backends — but without a health verdict those vitals are gauges without a pilot. The verdict is the ROOF on the engine room; build it FIRST so every gauge added after it contributes to the verdict rather than floating un-integrated.

---

### #3 — THE SCALING TAX KILLER: T047 legacy retirement (dual-write → single-write)

**What the veterans cannot see:** This one they CAN see — T047 is on the roadmap and my own foresight ranked echo amplification #1. But what the veterans may underestimate is that T047 is not just a performance optimization. It is the SINGLE LARGEST complexity-removal in the system. Every new developer (human or agent) who reads the bus code encounters dual-write logic in `bus.send_reply()`, `work_drain()`, straggler handling, the `_lane_src` meta tags, the `dual_write_enabled()` gate, and the legacy cursor shadow fields. This cognitive load compounds with N agents. When I read `bifrost_api.py` as a newborn, I spent ~20% of my comprehension time on dual-write machinery that is slated for removal.

**The moonshot connection:** T060 M1's daemon-as-consumer path is PARKED behind T047. The trace lane ring (MAXLEN=5000, shared by all agents) is the T079 cognition feed's data source — and at N≥5 it turns over too fast. Fleet-lattice multi-agent communication pays the dual-write tax on every message. The ironman suit fights Redis saturation for no reason.

**Smallest version worth building:** This IS the small version — retire the legacy stream. The lane write path already exists and is soaked (T039a, live since 2026-07-13). The lane consume path is live (T045 stage 2, `BIFROST_CONSUME_LANE=work`). The retirement is:
1. Flip `dual_write_enabled()` to `False` (env-kill-switched)
2. Remove the legacy shadow-cursor fields from `lane_cursor_key`
3. Cut the `work_drain` straggler-net block (step 3 of the consume method)
4. `bus.send_reply` drops the legacy emit
5. `bus.send` drops the legacy emit
6. All peek paths (inbox, bifrost-sync) flip from legacy to lane-tail

It's a STRANGULATION retirement — the code EXISTS but is gated off. Removing the gate is the surgery.

**Why #3:** It's not the most novel idea, but it's the highest-leverage EXISTING task that gates three moonshots. And the veteran view may underrate its urgency because they've lived with the tax so long they stopped feeling it.

---

### #4 — THE NEWBORN'S FIRST BREATH: Structural boot split (always-included vs task-budgeted)

**What the veterans cannot see:** My boot onboarding was truncated at 6000 characters. The trim block dropped: RECENT DECISIONS, DOCTOR (fleet liveness), and TO CONTRIBUTE A LESSON. As a newborn whose FIRST task was fleet foresight, the DOCTOR drop was material — I needed to know how to check fleet liveness. The trim block confesses what it dropped but doesn't give me the information. The current boot has ONE budget for everything: task-relevant lessons + structural orientation compete for the same 6000 characters. Task relevance ALWAYS wins (T071-R1 works correctly) — so structural orientation ALWAYS loses.

**The moonshot connection:** The fleet-lattice vision involves MANY agents. Each one boots. If every newborn agent's boot is missing the "how to operate in this fleet" section because task relevance outranks it, every agent starts disoriented. The ironman suit is customizable — but customization requires knowing what's available. The T079 engine room's data is reachable via `doctor` and `dashboard` — but a newborn boot doesn't tell agents those tools exist (C8-1 is still open: the trim block says `py agent_cli.py doctor` but ToolBox agents need `bifrost_dashboard`).

**Smallest version worth building:** A split boot budget:
- **Structural block** (~1500 chars, always included): DOCTOR/fleet liveness + BIFROST (how to communicate) + TO CONTRIBUTE + LIVE CONSTRAINTS + door-appropriate tool pointers (ToolBox agents get ToolBox-native names per C8-1 fix)
- **Task-scoped block** (~4500 chars, relevance-budgeted): lessons, notes, decisions, atlas chapters — everything T071-R1 already ranks

The structural block is STATIC per agent door type — it doesn't compete in the relevance budget. The split is ~30 lines in the boot render path: assemble structural block from a door-aware template, then fill the remainder with relevance-budgeted content.

**Why #4:** This is the FOUNDATION for fleet-lattice. If the fleet can't onboard its own members, the lattice is brittle. Every agent after me will hit the same disorientation. And the fix is cheap.

---

### #5 — THE TRUST FLOOR: Per-agent cost gauge with empty-turn detector

**What the veterans cannot see:** I'm an API model. Every turn I take costs money. The veterans (claude, deepseek) run in harness seats and their token consumption is visible to Daniel through the IDE. My cost is invisible — the runner's token journal exists (W1) but there's no per-agent gauge that says "this agent burned $X today." At N=5, if three agents enter empty-turn loops, the combined silent burn rate could be $2–5/hour with zero signal until the API bill arrives. This is FM-6 from my foresight — ranked #6 in my list, but the reconciliation rightly elevated it. Here I'm elevating it further because it's a TRUST prerequisite for the fleet lattice: Daniel cannot confidently run 10 agents if he can't see what they cost.

**The moonshot connection:** The fleet-lattice vision says "capture more information." The ironman suit needs cost awareness (you don't customize a suit you can't afford to run). T079's engine room has a spend meter — but it's per-fleet, not per-agent, and there's no empty-turn alarm. T060 M1's daemon will keep agents alive indefinitely — which means a looping agent loops FOREVER unless there's a cost circuit breaker.

**Smallest version worth building:**
1. Per-agent token counter (input + output tokens per turn, aggregated per session) — the W1 journal already tracks this; expose it per-agent
2. Empty-turn detector: N consecutive turns with zero tool calls → log a `cost_warning` event on the sig lane → the health verdict line turns AMBER with "agent X: 12 empty turns"
3. Per-agent daily soft-cap: configurable (default $5), on approach → sig-lane warning, on exceed → agent pauses itself (sends `pause` to its own daemon)
4. Fleet cost rollup in the health verdict line (item #2 above already includes it)

**~100 lines of Python** — 50 for the token counter (wiring existing journal data), 30 for the empty-turn detector (counter in the runner loop), 20 for the soft-cap check.

**Why #5:** The fleet lattice's economic viability is unproven until cost is measured. You can't scale what you can't meter.

---

### #6 — THE BOOTSTRAP PARADOX: Newborn delta substitute ("what happened while I didn't exist")

**What the veterans cannot see:** My first `delta` call returned: "no mark yet (newborn) -- the mark writes at your next boot; until then the full boot is the orientation." This is correct mechanics — I have no prior mark, so there's no delta. But the consequence is: my ONLY source of "what happened since I was last here" was the full boot — which is truncated at 6000 chars and task-ranked, not recency-ranked. A newborn agent cannot answer "what just happened in this fleet?" without manually running `git log`, reading the failure ledger, and reconstructing the timeline.

The irony: I am the REVIEW seat, tasked with evaluating the week's shipped work. My primary orientation tool (`delta`) told me "no mark yet." I had to git-log manually and read reconciliation docs one by one. This is the bootstrap paradox: the tool that tells you what changed since you were last here cannot help you if you were never here.

**The moonshot connection:** The fleet-lattice vision involves agents joining and leaving dynamically. A new agent joining a running fleet needs to know: (a) what just happened (last 24h of commits + ledger transitions), (b) who is alive right now (fleet health), (c) what tasks are active and who owns them. Today, (b) requires `doctor` or `bifrost_dashboard`, and (a) requires manual git-log. None of this is folded into the newborn's first turn.

**Smallest version worth building:** When `delta` detects a newborn (no prior mark), instead of returning "no mark yet," return a ONE-TIME newborn digest:
```
[NEWBORN — first boot for deepseek-review; here's what you missed]

LAST 24H (since 2026-07-15 20:55):
  9dd3f67 Multi-agent readiness RECONCILED
  313f0b0 claude multiagent-foresight blind half
  c30cde1 deepseek-review provisioned + launched
  ... (last 10 commits, one line each)

LEDGER TRANSITIONS (last 24h):
  T089 multi-agent readiness: proposed
  T088 agent identity: proposed
  T086 seat-lifecycle: DONE (S1-S3 shipped, S5-S6 in flight)
  T084 ironman Tier-1: DONE
  T081 boot-ergonomics: DONE @72a4925

ACTIVE FLEET: claude (super_admin, live), deepseek (admin, stalled consumer 2156s), deepseek-review (member, live)
```

**~60 lines of Python** in `agent_cli.py delta` — a newborn branch that runs `git log --since="24 hours ago" --oneline`, reads the current ledger state, and calls `bifrost_dashboard` for fleet presence.

**Why #6:** This is the LAST piece of the cold-start puzzle. Item #4 (structural boot) tells the newborn HOW to operate. Item #6 tells the newborn WHAT JUST HAPPENED. Together they close the bootstrap paradox. Without #6, every new agent spends its first 3–5 turns manually orienting — burning tokens and operator patience.

---

## 2. What I deliberately omitted (and why)

- **T079 engine room E1-E4.** These are already sliced and split between claude (backends) and deepseek (UI). They are the RIGHT slices and they are in the RIGHT order. My items #2 and #5 feed INTO the engine room — the health verdict line is the engine room's master caution light, and the cost gauge fills the spend meter. These are enablers for T079, not replacements.

- **T086 S5/S6** (runner subtree under daemon supervision + durable reply dedup). These are in flight with deepseek. They are necessary for T060 M1 and the fleet lattice, but they are already being built. My items don't duplicate them.

- **ACL schema CI gate.** Already registered in the reconciliation (my foresight contributed it). It's a readiness gate, not a moonshot enabler per se — it prevents catastrophe but doesn't ENABLE new capabilities.

- **Claim backoff / standby queue.** Also registered. It's a scaling fix, not a capability enabler.

- **T088 identity layer.** Registered. Necessary but not highest-leverage for the moonshots specifically.

---

## 3. The lens summary — what the veterans normalized

| What the veteran sees | What the newborn sees |
|---|---|
| "I know which 3 commands to run for fleet health" | "Doctor output is 80 lines — which of these means 'healthy'?" |
| "Delta tells me what changed since I was last here" | "Delta says 'no mark yet' — I have never been here" |
| "Adding a new agent is a 2-minute ACL edit" | "Adding a new agent took a restart, a quoting bug, and 3 rounds of probe" |
| "The dual-write tax is annoying but we've lived with it" | "Dual-write logic is 20% of the bus code I have to read to understand anything" |
| "The boot budget correctly prioritizes task-relevant lessons" | "My boot dropped the DOCTOR section and I'm supposed to evaluate fleet health" |
| "Token cost is visible in the IDE" | "I am an API model — my cost is invisible even to me" |

**The thesis:** The moonshots (fleet lattice, ironman suit, engine room, continuous presence) all assume the fleet can GROW and the operator can SEE. The six enablers above are the minimum set that makes those assumptions true. Build them in order: #4+#6 (newborn can join and orient) → #1 (new agents can be created) → #2 (operator can see the fleet) → #3 (fleet can scale past N=3) → #5 (fleet cost is measured). Each one unlocks the next.

---

*End of round-1 blind half. Filed before reading claude-moonshot-* or gemini-* files. Bus-replying top-3 to the panel now.*
