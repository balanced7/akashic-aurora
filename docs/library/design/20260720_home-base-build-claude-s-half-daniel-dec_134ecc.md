---
akashic_id: art_20260720_home-base-build-claude-s-half-daniel-dec_134ecc
akashic_sha: 3e47438862f5
status: current
type: design
date: 2026-07-20
title: "Home-Base Build — claude's half (Daniel-decided 2026-07-20: BUILD OUR OWN)"
gist: "Daniel verbatim: \"I want the home base to eventually be our own program with rich integration with API models and CLI models.\" Reasons, verb"
tenant: solo
visibility: fleet
seats: []
category: [library, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T22:56:30"
updated: "2026-07-19T22:56:30"
---
<!-- GENERATED PROJECTION of art_20260720_home-base-build-claude-s-half-daniel-dec_134ecc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Home-Base Build — claude's half (Daniel-decided 2026-07-20: BUILD OUR OWN)

Daniel verbatim: "I want the home base to eventually be our own program with rich integration
with API models and CLI models." Reasons, verbatim: full visibility of what works, integrations
that don't break from someone else pushing an update, "a good chance for us to improve our
engineering processes and chops."

## N1 — Landscape learnings (I am the seat that LIVES in one of these)

**From Claude Code (lived, not read):**
STEAL — the five things that make it a real agent home:
1. **The hook architecture is the crown jewel.** SessionStart/UserPromptSubmit/PreToolUse/Stop
   hooks are WHY Aurora could colonize this harness at all: recall-at-action, the whisper, the
   wake contract, the stop-hook promise check — all of it rides hooks. Our program must be
   hookable at the same joints from day one: every lifecycle edge (mission start, turn start,
   pre-tool, turn end, seat idle) fires a registered, auditable hook.
2. **Harness-tracked background processes.** run_in_background + completion-reinvokes-the-seat
   is the wake machinery's spine. Our program owns this natively: processes registered to the
   mission, completion events on the bus, no orphans (T030's whole class dissolves when the
   home base owns process lifecycle).
3. **Permission modes as a first-class dial** (plan/accept-edits/bypass) — maps to our
   fidelity ladder + approval policies; the UI form of trust tiers.
4. **Session transcripts as replayable artifacts** — our ledger already beats this; the
   learning is the UX: /resume, forking a session, compaction. Missions must resume the same way.
5. **MCP as the tool bus** — client-side pluggability we should SERVE (Aurora as MCP server
   already exists) and CONSUME (our program as MCP client = every MCP tool ever written works
   in our home base for free).
AVOID — the four scars this session-family carries:
1. **Opaque platform policy inside the seat** (the safeguards model-swap ejections: 13+ lost
   Fable seats). Our program never silently swaps a mission's model; policy is visible config.
2. **Single-seat worldview.** Claude Code assumes one agent per terminal; everything
   multi-agent we built (bus, lanes, presence) lives OUTSIDE it. Our program is multi-seat in
   its object model, not by bolt-on.
3. **Terminal-bound operator surface.** Daniel's actual cockpit is the browser console; the
   terminal is a seat harness, not a home.
4. **Stop-hook wrestling** (tonight: 6 wake-rearm cycles). When the home base owns seats, the
   wake contract is a property of the platform, not a per-session hook negotiation.

**From LibreChat (verified facts, 2026-07-20):** TS/React/Node + MongoDB, 41k stars, 424
contributors, mature agents/MCP/custom-endpoints/OAuth. STEAL: the capability-aware endpoint
config idiom (per-provider YAML declaring what each endpoint can do — cousin of our fleet
roster tags); artifacts UX; conversation search as table stakes. AVOID: conversation as the
central object (ours is the mission/task ledger); infra weight (Mongo+Meilisearch+RAG-api
services for one operator — our whole state fits Redis+files and already has a proven
backup/restore ritual).

**From Codex (we ran seats on it):** T065's lesson — hooks that CLAIM to fire but don't =
fail-open reads as working; our program must give every integration a measured liveness
receipt (the harnesses matrix, made product). Cost routing (codex-too-expensive-for-build
lanes) → per-seat cost policy belongs in the platform's model layer, not in folklore.

**From GPT's advisory (kept as design input, fork recommendation retired):** the five mission
views; the capability-adapter contract ("graceful exploitation of model differences, not
lowest common denominator"); "UI submits intent, Aurora owns runs" — which is already our
doctrine and now becomes our API contract's first law. LangGraph stays a benchmark for run
inspection/replay UX, nothing more.

## N2 — Build shape

**Stack call (mine; fence may counter):** extend the organism we own — Python server (the
bifrost_ui lineage) + a MODULAR frontend that graduates from the current vanilla-JS by
extraction, not by rewrite. Concretely: break the 85KB inline script into served modules (the
static-route pattern already exists: aurora-shader.js, presence-rail.js...), introduce a
build-free component convention first, and adopt a typed/bundled frontend ONLY when a slice
demonstrably needs it. Rationale: (a) C10 immune system (parse gates) extends naturally;
(b) all three seats can review every line; (c) no rebase tax, no foreign idiom — Daniel's
stated reasons, engineered. CLI-model integration = the adapter seam where Claude Code /
Codex seats join missions via hooks+wake exactly as today, presented through the same API
door as API-model runners.

**Smallest first slice that is genuinely our-own-program (not a bigger console):**
**MISSION VIEW v0** — one screen: the task ledger's active missions, each with its live seats
(presence), last event, cost line (turn_metrics), and TWO verbs: steer (fidelity ladder) and
approve (gate). Everything is a projection over streams that exist TODAY (kimi's line holds:
the views are designed; the streams all exist). It is the first screen where the central
object is a MISSION, not a message — that is the identity moment for the program.

**Sequencing after v0:** (1) API door v1 under it; (2) agent panes (T002's cards graduate);
(3) causal ledger view (T079's engine room — the signature); (4) context inspector (T094 R0's
journal gets its face — the arcs converge); (5) policy/experiment cockpit; (6) capability
adapters absorb the model layer (K0 factory grows tags); (7) auth/mobile ONLY when Daniel
needs them (commodity last, not first).

## N3 — The API door (inventory, code-read tonight)

EXISTS and formalizes cleanly: /events SSE (the live feed), /status + /vitals, /launcher/*
(seat start/stop), /episode/*, /reload; agent_cli's 49 verbs (DOORS.md censuses them);
MCP server surface; the conductor's gated transitions. GENUINELY NEW: (a) a versioned
contract — /api/v1/{missions,agents,events,approvals} with schema'd payloads instead of
console-shaped JSON; (b) approvals as RESOURCES (Daniel's gate verdicts become POSTable,
auditable objects — today they are chat messages I transcribe into notes); (c) authn even
single-user (a bearer token, so the door is a door); (d) event REPLAY from ledger refs
(LangGraph's one good trick, over our own streams).

## N4 — The chops goal (Daniel's third reason, taken seriously)

Load-bearing from slice 1: prereg pins before code (T094 R0 shape); fenced dual passes on
every load-bearing slice; the derived-docs immune system EXTENDED to the new surfaces (MAP/
PHYSICS/DOORS regenerate over the program's modules; parse gates on everything served — C10
law); failure-ledger discipline (every glitch files as it occurs). NEW practices a product
build demands that system-work never did: (1) **visual regression receipts** — shot.ps1
(W22) grows into a screenshot-diff pin per view slice; (2) **operator-journey drills** — a
T057-style scenario where DANIEL'S workflow (boot → read state → steer → approve) is the
drill script, run before every ship; (3) **API-contract pins** — the versioned door gets
consumer-driven contract tests so a UI slice can never break a seat integration silently;
(4) **a public face** — this program is the portfolio artifact; README/screenshots/demo
treated as first-class deliverables per public-voice calibration.

## Sequencing proposal for the arc itself

Positions (this doc + deepseek + kimi) → reconciliation → a charter doc (the program gets a
NAME and a T-task family) → Daniel gates slice 1 (Mission View v0 + API door v0 behind it) →
build fenced, drilled, pinned. In parallel, the standing arcs finish: API-resilience wave
(deepseek's half pending), T094 R0 (v2 verify pending), T097 S1 progress stamps (the revive
machinery the program will later render).
