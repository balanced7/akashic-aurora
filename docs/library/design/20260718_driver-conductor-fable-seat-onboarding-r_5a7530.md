---
akashic_id: art_20260718_driver-conductor-fable-seat-onboarding-r_5a7530
akashic_sha: 24e9ecf7c638
status: current
type: design
date: 2026-07-18
title: Driver / Conductor Fable Seat — Onboarding Runbook (2026-07-18)
gist: "Class: runbook **Purpose:** Daniel wants to launch a fresh Fable-5 Claude Code session that DRIVES the fleet — picks direction, delegates to"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, identity, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260718_gate-packets-2026-07-18_e5c5e5
    rel: cites
  - target: art_20260718_charter-role-specialization-framework-cl_b93d30
    rel: cites
  - target: art_20260701_packet-routing-internal-api-design-co-au_57e4ba
    rel: cites
  - target: art_20260718_kimi-fresh-eyes-dissent-round-t094-recal_71a6f9
    rel: cites
created: "2026-07-19T11:43:55"
updated: "2026-07-23T21:42:05"
---
<!-- GENERATED PROJECTION of art_20260718_driver-conductor-fable-seat-onboarding-r_5a7530 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Driver / Conductor Fable Seat — Onboarding Runbook (2026-07-18)

Class: runbook

**Purpose:** Daniel wants to launch a fresh Fable-5 Claude Code session that DRIVES the fleet —
picks direction, delegates to everyone (deepseek, kimi, gemini, and Fable/claude workers), and
continues the charter + frontier-roster arc. This is the launch + invoke runbook for that seat.

## 1. What the driver IS

The **conductor** — the claude charter role made live: architecture, adjudication, synthesis,
sole committer. It doesn't do all the work; it ROUTES work to the seat with the comparative
advantage and integrates the results. It is the single point where the fleet's output funnels
through review and commit.

## 2. Launch steps (turn-key)

1. Open a NEW Claude Code session in **E:\AI-Setup** (the repo IS the front door — SessionStart
   primer + AGENTS.md + hooks all key on cwd).
2. Model **Fable-5**, effort **max**. (Daniel's own auth — no special endpoint; unlike the kimi
   seats which need the moonshot endpoint.)
3. First command: **`py agent_cli.py boot claude --task "drive the charter + frontier-roster arc"`**
   — one hop loads: the ledger, the current where-we-are, live constraints, ranked lessons, and
   the DRIVER HANDOFF left for it (below). Boot surfaces "latest handoff addressed to claude"
   automatically — that's the continuity spine; no manual pasting (T074).
4. Read this runbook (boot points at it) + docs/gate-packets-2026-07-18.md (open decisions) +
   research/drafts/charter-framework-claude-perspective-2026-07-18.md (the active arc).

## 3. The invoke matrix — how the driver calls each seat

| Seat | How to invoke | Round-trip | Notes |
|------|---------------|-----------|-------|
| **deepseek** | `py agent_cli.py bifrost-send claude --to deepseek --kind handoff --text-file <f>` | async (runner wakes, replies on bus) | build partner; READ-ONLY exec; adversarial suites. Reply lands on the bus — drain via bifrost-sync / XRANGE. |
| **kimi** | headless launcher: clone `scripts/local/launch_kimi_fresheyes.ps1`, swap the brief path, run via `powershell -File ... ` as a **background** task | async (~$1-2, minutes) | fresh-eyes / vision / 1M-context sweeps. Twin-guard before launch (no kimi transcript mtime <10min). Lock the deliverable path. |
| **gemini** (free) | `ask_gemini_web(prompt, mode=gemini\|ai_mode\|both)` MCP tool | ~15-90s | research / prior-art / blind drafts ONLY. Never repo/fence/code-review. `mode=api` fallback if web returns empty (web profile may need `gemini_web_login`). |
| **claude / Fable worker** | the **Agent tool** (`subagent_type: claude`) — spawns a fresh Fable subagent, clean + parallel, NO seat contention | sync or background | this is the RIGHT way to "invoke another claude" — fresh workers, not poking a stuck session. Use for parallel synthesis, reviews, heavy reasoning the driver wants off its own context. |
| **this session (665aaea3)** | ONLY if kept alive: `bifrost-send claude --to-incarnation 665aaea3 --kind handoff ...` | async | see §5 — the identity decision. Default: this session stands down and the driver uses fresh Agent-tool workers instead. |

## 4. Continuity — the driver inherits ALL our work

Nothing is lost across the handoff. The driver boots into: the git-durable task ledger (42 done /
active / next), the where-we-are note, the durable decision notes, and the driver handoff. Today's
live arcs it continues:
- **Charter / role-specialization framework** — deepseek synthesizing the unified report; my
  perspective filed (charter-framework-claude-perspective); kimi's third voice pending. THE active arc.
- **Packet-routing round-5** — three-voice fold filed (docs/packet-routing-design-2026-07.md);
  awaiting deepseek + deepseek-review affirm, then Daniel's RECONCILED gate.
- **Kimi T094 fresh-eyes** — running now; deliverable research/reviewed/kimi-fresh-eyes-t094-recall-2026-07-18.md.
- **Kimi graduation** — walk + fresh-eyes + vision probe all complete; at Daniel's gate.
- **Gate packets** — docs/gate-packets-2026-07-18.md, current, awaiting Daniel's G1–G7 + mirror.

## 5. The identity decision (the one fork — Daniel chooses; see chat)

Two Fable sessions both as `claude` = seat contention (the twin-claude wake-loop/dead-holder class
we've fought all week). Three clean resolutions:

- **A. Clean takeover (RECOMMENDED).** The new driver IS `claude` (full context, super_admin).
  THIS session (665aaea3) stands down UNARMED once the driver is live — releases its wake seat,
  ends. One conductor, zero twin contention. The driver invokes claude-grade work via fresh
  Agent-tool workers (more scalable than poking one session anyway). "Invoke you" is satisfied
  better: unlimited clean Fable workers on demand.
- **B. Driver + this session as a live worker.** This session stays alive holding a wake seat;
  the driver addresses it by incarnation (`--to-incarnation 665aaea3`). Matches "invoke you"
  literally, but reintroduces twin-`claude` seat overhead (accept the known cost).
- **C. Distinct driver identity** (e.g., `conductor`). No collision; this session stays as the
  `claude` worker. Cost: bootstrap an acl.json record + a charter for the new id, and decide who
  holds sole-committer authority.

## 6. Standdown protocol for this session (if option A)

When the driver is confirmed live and booted, this session (665aaea3): stop the wake-standby
background task, leave a final handoff (done — see §4), and end UNARMED (no re-arm) so the driver
is the sole wakeable `claude` seat. The seat TTL + the driver's own standby take over.
