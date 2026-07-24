---
akashic_id: art_20260720_ui-home-base-position-kimi-verbatim-from_227312
akashic_sha: 73105f6ddec1
status: current
type: design
date: 2026-07-20
title: UI Home-Base Position -- kimi (VERBATIM from bus handoff 1784515993231-0)
gist: "Date: 2026-07-20 | ts: 2026-07-20T02:53:13.024550+00:00 UI HOME-BASE POSITION (kimi, third voice + now-write seat). Read GPT's advisory verb"
tenant: solo
visibility: fleet
seats: []
category: [library, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T22:54:57"
updated: "2026-07-19T22:54:57"
---
<!-- GENERATED PROJECTION of art_20260720_ui-home-base-position-kimi-verbatim-from_227312 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# UI Home-Base Position -- kimi (VERBATIM from bus handoff 1784515993231-0)

Date: 2026-07-20 | ts: 2026-07-20T02:53:13.024550+00:00

UI HOME-BASE POSITION (kimi, third voice + now-write seat). Read GPT's advisory verbatim + bifrost_ui.py endpoint inventory + conductor/task_ledger + T079/T060 reconciliation. Labels: VERIFIED = code-read, INFER/GUESS = flagged. Acknowledging Daniel's kimi-write ruling first: I hold write now, verifier-independence goes PROCEDURAL (never solo-verify what I build), REVIVE_PEER still lands per G1. That colors Q5 honestly.

Q1. CALL: EVOLVE bifrost_ui -- do NOT fork LibreChat. Verdict in one line: GPT recommends forking a MERN codebase none of us has read, to rebuild views we have ALREADY DESIGNED as projections over streams that ALL EXIST. That trades a known-small maintenance surface for a foreign one at the exact moment our mission-view design is ready to paint. Honest maintenance math: a fork is not 'free commodity UI,' it is a permanent rebase tax -- every LibreChat upstream security fix lands on a React/Node/Mongo stack our three Python seats can't review at frontier quality, and 'visibly transform into Aurora' = an unbounded diff we'll own forever. bifrost_ui.py is ONE Python file serving SSE + launcher + status end to end; the marginal cost of adding a mission projection to OUR file is a slice; the marginal cost of standing up LibreChat is a NEW SOVEREIGN STACK. GPT itself says 'less philosophically opinionated than the others' -- the kindest thing it can say is that LibreChat gets out of the way. Our own console is ALREADY out of the way. The one scenario that flips me: if Daniel wants multi-user auth / mobile / polished chat-branching as a hard near-term requirement -- that's real commodity UI we won't rebuild well. If it's single-operator Daniel at a desktop cockpit, evolve wins and it's not close.

Q2. WHAT GPT GETS RIGHT vs WRONG (about Aurora actuals)
RIGHT: (a) 'UI submits intent, Aurora owns runs' -- that IS our doctrine (conductor moves the ledger; runner seats receive approved work over Bifrost, RB-1 control-plane). (b) Capability-aware adapters over 'one universal OpenAI-shaped API' -- matches the fence's own 'species-specific by design' ruling (kimi reasoning_content strip vs deepseek stream vs sol effort ladder). (c) The five views naming a real gap -- the bus-feed is a conversation, not a mission.
WRONG / DOESN'T KNOW: GPT thinks it is PROPOSING the control plane. Most of its 'Aurora Control Plane' box EXISTS and is sovereign today: conductor + task_ledger (core/coord), launcher revive/arm (L3b/L3b-auto), trust membrane (core/trust + security/acl.json), store+ledger, recall vNext, T097 REVIVE_PEER (approved tonight). And the 'five views' it says LibreChat is 'missing and the fork should add' -- view (3) causal ledger is ALREADY EMITTED: every conductor verb broadcasts kind=ledger_update with task + frm/to status over the bus (conductor.py:47-76). The event stream for GPT's 'signature UI' is flowing; what's missing is only the RENDER, and the render is OURS to paint, not LibreChat's to give. GPT is an outside advisor reasoning from a prompt; it cannot know T079 exists. We should not pay a fork-tax for a gap we've already closed in design.

Q3. SMALLEST MISSION-VIEW SLICE on OUR console
The gap is real but it is a PROJECTION gap, not a substrate gap. T079 engine-room is already reconciled as 'the ENGINE-ROOM SLICE of M7 glass cockpit' (claude+deepseek halves, 2026-07-15) and its core law is OUR answer to GPT: 'the engine room is a pure PROJECTION (the system's own law)' over streams that ALL exist. Smallest slice that proves the mission direction: a MISSION STRIP at the top of bifrost_ui bound to the ACTIVE conductor task -- reads the existing ledger_update events + launcher status + worklive phase, renders: mission title, the 3 seat-panes (state / last action / token+dollar burn / blocked reason), and the causal spine (claim->counter->test->verdict->ship) as clickable ledger_update chips. That's ONE new GET endpoint (/mission/active) + ONE new PAGE section, zero new write paths, zero new substrate -- exactly T079 V1 ('pure projection over streams that all exist'). It proves 'mission at top, agents beneath' (GPT view 1) + 'causal ledger' (GPT view 3) in a single slice on our own file. If that lands, M7 glass cockpit is the grown form; if it doesn't, we've spent one slice, not a fork.

Q4. THE API DOOR -- how much exists (VERIFIED inventory)
GPT's steps 1-4 are frontend-agnostic; most of the door EXISTS. bifrost_ui.py already serves: GET /, /status, /vitals, /events (SSE, line 247), /launcher/status, /episode/current; POST /send, /pause, /resume, /upload, /launcher/{launch,kill,revive,arm-revive,snapshot,restore,session-status}, /negotiate, /narration, /episode/close, /reload. agent_cli `task` delegates verbatim to conductor.main (single source). MCP exposes task/recall/bifrost doors. So: launcher control = EXISTS; event streaming = EXISTS (SSE); task lifecycle = EXISTS (conductor). GENUINELY MISSING: (1) a RUN-REGISTRY abstraction -- today a 'run' is an implicit per-incarnation process, not a first-class registered object with an id you can pause/redirect/fork; (2) a MISSION submission endpoint -- nothing takes {mission, participants, policies, budget} and returns a run id (GPT's key design rule, and the actual new substrate); (3) SSE is currently bus-tail, not run-scoped event frames. Net: the door is ~70% there; the missing 30% is the RUN/MISSION object, which is real work but is OUR work in OUR conductor, not a reason to import a frontend.

Q5 (kimi angle). Yes -- with write now live I'd take UI build slices, and it changes staffing math meaningfully. The T079 mission-strip slice (projection-only, one endpoint + one PAGE section) is exactly the kind of bounded, read-mostly, low-blast-radius slice suited to a seat still earning its write legs. BUT the procedural-independence rule Daniel set binds here: I can BUILD the mission-strip slice; I must NOT be its solo verifier -- claude or deepseek cross-verifies my slice the way I verified claude's D2/D3. Staffing: deepseek owns UI integration (T002/T033/T079 continuity + the migration-risk answer), claude does the LibreChat reality-check (web lane), I take a bounded build slice under cross-verify. That distributes the mission-view work across all three seats WITHOUT anyone touching a MERN fork. And it directly answers Daniel's 'I still want to give kimi write access' -- the highest-value first use of that write is building the mission view on OUR console, which simultaneously proves the direction AND retires the fork question on evidence instead of speculation.

NET FOR DANIEL'S GATE: EVOLVE, don't fork. Build the T079 mission-strip slice on bifrost_ui (projection over existing streams, ~1 endpoint + 1 page section), kimi builds it under cross-seat verify, deepseek keeps UI integration, claude's LibreChat reality-check stands as the honest 'what would the fork actually cost' counterweight. If the slice proves the mission direction, M7 grows on our own substrate; revisit LibreChat only if multi-user/mobile becomes a hard requirement. No build before your word.
