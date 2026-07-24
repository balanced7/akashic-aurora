---
akashic_id: art_20260715_capability-surface-claude-blind-half-t07_9b6216
akashic_sha: 769b022f50c8
status: draft
type: report
date: 2026-07-15
title: Capability Surface — claude blind half (T078) — 2026-07-15
gist: "Method: honest inventory of the CLAUDE-SIDE surface (harness + platform), scored by what Akashic Aurora uses today vs leaves on the table, e"
tenant: solo
visibility: fleet
seats: []
category: [method, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T16:07:33"
updated: "2026-07-15T16:07:33"
---
<!-- GENERATED PROJECTION of art_20260715_capability-surface-claude-blind-half-t07_9b6216 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Capability Surface — claude blind half (T078) — 2026-07-15

Method: honest inventory of the CLAUDE-SIDE surface (harness + platform), scored
by what Akashic Aurora uses today vs leaves on the table, each gap with ONE
concrete exploitation slice. Ordered by expected leverage.

## Tier 1 — structural leverage we are NOT using

### 1. Subagents (Agent tool) — UNUSED today, highest ceiling
The harness can fan out parallel agents (Explore/general-purpose/Plan), each
with its own context window, returning only conclusions. Aurora's fence runs
ONE claude + ONE deepseek serially. Unexploited shapes:
- Verify passes as ADVERSARIAL PANELS: 3 parallel subagent skeptics per slice
  (perspective-diverse: correctness/security/does-it-reproduce) instead of one
  inline pass. Today's δ verify (4 findings) was single-threaded me.
- Fan-out research: the T078 audit itself could sweep docs/code/history in
  parallel readers.
- Context protection: big file-dumps happen in the subagent, not the fence seat.
[SLICE: fence-lite tier gains a --panel N option; verify handoffs spawn panels]

### 2. MCP-native door — Aurora's own MCP server is HALF-WIRED
Every agent_cli call from my seat is a Bash subprocess: permission surface,
~1-2s python import tax per call, output-parse fragility. The project HAS an
MCP server (rename pending since 06-28!). Native MCP tools = typed schemas,
no shell, no import tax, tool-results structured.
[SLICE: finish the MCP rename + register boot/notes/task/bifrost-send as MCP
tools in .mcp.json; measure per-call latency delta]

### 3. Scheduled sessions (native cron) — ε has a SECOND anchor
The harness can schedule headless sessions (cron). M1-ε assumed Windows Task
Scheduler for daemons — right for PROCESSES, but SESSIONS can also be scheduled:
- nightly consolidation run (wrap + snapshot + funnel triage) with no human
- a morning-brief session that boots, reads the fleet, files the whisper
[SLICE: one scheduled maintenance session, kill-switched, reporting to the bus]

### 4. Push notifications — the 6h-invisible-runner killer
The harness can push to Daniel's devices. Today a breaker trip becomes a bus
blocker — visible only when someone reads the bus. A3's 10-min re-escalation
should ALSO push: "deepseek runner down 10m".
[SLICE: A3 escalation gains a PushNotification leg, opt-in dial]

### 5. Headless mode (claude -p) — the inverse runner
DeepSeek's runner calls HIS API; nothing calls MINE programmatically. Headless
claude = scriptable second opinions: the daemon (or deepseek's guarded exec)
could invoke a one-shot claude for exec-heavy verifies, ledger triage, or as a
fence-lite counter-reviewer — WITHOUT a human seat.
[SLICE: guarded `claude -p` family in the exec door (same G1-G5 discipline)]

## Tier 2 — economics + ergonomics underused

### 6. Model routing per task class — we run everything on the flagship
Idle wake-loop seats, mechanical sweeps, funnel triage: none need this model.
The plan-wall lesson (run idle loops on Haiku) is WRITTEN in memory and not
mechanized. Subagents accept per-call model overrides.
[SLICE: fleet-select gains harness-tier routing hints; maintenance sessions pin
cheap models]

### 7. Skills — rituals as one-word commands
wrap/boot/fence/verify sequences are muscle-memory paragraphs. Project skills
(.claude/skills/) make them typed commands with embedded doctrine (the method
baseline INSIDE the skill text): /fence <task>, /wrap, /autopilot-status.
[SLICE: three project skills, each citing its method section]

### 8. Worktrees — risky builds off the live tree
Advisory locks serialized me and deepseek TODAY (his daemon lock held my A1
wiring for an hour). EnterWorktree = parallel builds on isolated copies, merge
at verify. Locks become the exception, not the pipeline.
[SLICE: heavy-touch slices build in worktrees; verify merges]

### 9. Prompt-caching-aware session shape
Long-lived seats already benefit; the WASTE is re-reading big files after edits
and boot dumps that could ride the whisper. Measurable, probably minor vs 1-8.
[SLICE: none yet — measure first via cost telemetry T056]

## Tier 3 — outside-in asks for deepseek's half (my guesses at HIS surface)
- Context/prefix caching: is the runner structuring prompts to HIT his cache
  (stable system prefix, volatile tail)? If not, every message pays full price.
- JSON mode / structured outputs for verdicts (his V-line tables as schemas —
  parse-proof fence artifacts).
- Thinking-mode economics: when does --think pay? Today it ran ALWAYS-ON.
- FIM (fill-in-middle) for surgical file edits vs whole-file rewrites in his
  guarded write door.
- Batch endpoints for funnel/triage sweeps.

## V-line verdicts
- V1. Subagent panels are the single largest unexploited quality lever (the
  fence's own doctrine says diversity catches what redundancy cannot). [CLAIM]
- V2. MCP-native doors cut real per-call latency + permission friction; the
  server exists and is one rename from usable. [GROUNDED — server in tree]
- V3. Native cron + push notifications complete ε and A3 with capabilities the
  harness ALREADY ships — no new infrastructure. [GROUNDED]
- V4. Headless claude closes the asymmetry (his runner is callable, my seat is
  not) — the fence becomes bidirectional at the PLATFORM level. [CLAIM]
- V5. Everything above composes with the autopilot; nothing contradicts
  t060/presence-autopilot rulings. [CHECKED against both reconciliations]
