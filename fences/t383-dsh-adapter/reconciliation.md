# t383-dsh-adapter — RECONCILIATION (Vandor/claude, 2026-08-24)

Both halves sealed blind; they converge on every load-bearing seam. What follows is the
settled design, the two divergence rulings, and the build assignments.

## SETTLED (both halves agree; citations live in the halves)
- ADAPTER SHAPE: thin JS translator in the DSH profile layer + Python policy in the repo
  (a-V19/V20, b-V2). Five listeners: session/created+assemble (T2), tools/post-execute
  (T3 one-beat-late + T4 direct via isError), user/message→next-assemble (T5 derived),
  session/flush+disposed (T6). tools/pre-execute is gate-only — no injection (both halves,
  inventory-confirmed).
- T3 rides the ALREADY-EXTRACTED pure contract core/recall/actions.py::recall_context with
  an EXPLICIT session key, never env (a-V7, b-V4, b-V8).
- T4 is DIRECT (Cursor precedent, no transcript synthesis) via resolve_action_outcome
  (a-V10, b-V5).
- T5 is DERIVED and stays [UNCERTAIN] until a capture proves the assemble carries it;
  kill switch AKASHIC_PLAN_RECALL=0 (b-V6, a-V16/V17, a-V28-RISK3).
- IDENTITY: explicit keys everywhere; the plugin pins itself observe-only if
  AKASHIC_AGENT_ID resolves to anything but dsh_agent at startup (b-V8). The env-read leak
  in core/recall/at_action.py::_log_outcome_stage (line ~1007) is REAL and must be fixed by
  threading identity through parameters, never by setenv in the plugin (a-V13/V14,
  b-R3). Fix lands WITH the extraction.
- MIGRATION: strangler-fig, RED pins first, DSH never copies the orchestration
  (a-V24, b-V12).

## RULING 1 — extraction module: agent/harness/actions.py, three functions
half_a proposed agent/harness/recall_block.py::recall_block (one fn). half_b proposed
agent/harness/actions.py with recall_block + outcome_block + plan_block, citing the tiers
doc's own pre-declaration ("extract it first (the deferred actions.py)", doc lines
131-132) [b-V9 CERTAIN]. RULING: half_b's site and split win — the doc named the module
two months ago, and the three-way split also absorbs the plan_block duplication half_a did
not cover. half_a's signature survives inside it. Final signatures:
  recall_block(session_key, seen_key, path, command) -> str        # surface: recall_at→render→mark_seen→mark_impression→log_injection, fail-open ""
  outcome_block(session_key, seen_key, target, success, agent_id) -> str  # resolve_action_outcome→flip ledger→nudge under rate limit
  plan_block(prompt, session_key, seen_key) -> str                 # plan-altitude recall (absorbs claude_userpromptsubmit copy)
agent_id threads from outcome_block into the at_action logging path (the leak fix); the
other two derive attribution from session_key exactly as the contract does today.

## RULING 2 — T4's "second external contract fn" lands one layer up
half_a wanted core/recall/actions.py to grow resolve_tool_outcome. half_b observed [V10
CERTAIN] that core/recall/actions.py is deliberately PURE (returns a dict, writes
nothing) — and outcome resolution is inherently side-effectful. RULING: the T4 entry
point for ALL harnesses is agent/harness/actions.py::outcome_block (side-effect layer);
core/recall/actions.py stays pure and T3-only. half_a's gap (V11) is closed — the
importable seam exists — without polluting the pure module. The DSH bridge calls
outcome_block exactly as it calls recall_block.

## GRADE POLICY (the registry never flatters)
b-V13's tier strings are the TARGET block, adopted verbatim — but they enter
agent/harness/registry.py under the EXISTING "deepseek-harness" key ONE RUNG AT A TIME,
each flip carrying its receipt: T1 flips on the cold-start proof (pending), T2-T6 flip as
each seam is wired AND a captured payload pin proves it. Until then the strings stay
"pending -- designed (t383): <seam>", which supported() reads as not-automated. The
drill doctrine applies to the matrix itself: an unwired tier wearing "yes" is the exact
flattery the pending-gate (landed 3559f478) forbids.

## RISKS CARRIED FORWARD (build items, not prose)
- R1 context-drop (includeRuntimeContext:false discards listener additions): once-per-
  session marker probe, loud "context dropped" finding.
- R2 HMR generation race (reload can leave a listener absent silently): register a
  dsh-invariants check ("post-execute listener present") + activation logging.
- a-V27 target-join: capture a surface+resolve pair for the SAME action and assert
  target equality before trusting any credit number (goes in tests/test_dsh_contract.py).

## M1-PV ACKNOWLEDGMENT (out-of-repo citations, each named and hand-verified)
PV cannot resolve paths outside the repo. Every MISSING citation below was HAND-VERIFIED
2026-08-24 by claude at the real base
C:/Users/L5/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/ (the packages
nest under the dsh package's own node_modules; half_b's shorter base is otherwise exact).
TRUE at the cited lines, all:
- deepseek-ai/dsh-session/lib/types/index.d.ts (:32 events block, :44 session/created,
  :54 session/disposed, :66 session/event, :75 session/flush Promise-awaited)
- deepseek-ai/dsh-session/lib/types/types.d.ts (:262 'user/message': UserMessage)
- deepseek-ai/dsh-tools/lib/types/index.d.ts (:24 module decl opening the tools/* events
  range, :51-55 thrown tools reach the waterfall as errors, :61 tools/post-execute,
  :83 tools/result observe-only, :427 PostToolDecision)
- deepseek-ai/dsh-tools/lib/index.js (:3358 isError/content ferry into the active batch)
- deepseek-ai/dsh-system-prompt/README.md (:12 and :55 runtime-context discard — R1's
  exact mechanism; :25 assemble waterfall)
- deepseek-ai/dsh-agent-loop/README.md (:17 agentEvents + assembleContextFor per step)
- deepseek-ai/dsh-agent-loop/lib/index.js (:497 assemble(assembleContextFor(...)))
- deepseek-ai/dsh-mcp-client/README.md (:32 HMR hot-swap without process restart;
  :65 generation re-sync/rollback — R2's mechanism)
- deepseek-ai/dsh-scope/README.md (:5 scopeTarget scoped-event routing)
FORWARD REFERENCES (files the file plan creates, named not-yet-on-disk by design):
tests/test_dsh_contract.py; the plugin's lib/index.js.

## CONDUCTOR AMENDMENTS (format only, zero substance)
half_a was authored with exec OFF (Heimdall could not run the seal checker): all 28
verdict tags sat at paragraph end; I moved each onto its V-line (M1-CF requires it).
half_a also numbers two pairs twice — cite them as V25-EXTRACTION / V25-SUPERSEDES and
V26-GRADE / V26-RISK1. One mojibake char in V26-RISK1 left as-is (cosmetic).

## PRESENCE (Daniil, mid-fence 2026-08-24: "how can we integrate dsh liveliness and
## rich presence on the bifrost ui?")
No new seams needed — the five listeners ARE the liveliness signals. The bridge stamps
roster.heartbeat(dsh_agent) plus a rich presence hash (phase idle/thinking/tool-running,
profile web|tui|headless, session key, hop count, plugin generation) on every event it
already handles; session/flush clears to a clean offline. The R2 invariant doubles as a
"DSH running WITHOUT the akashic plugin" badge — the silent-absence risk made visible on
the dashboard. Ownership per the standing boundary: claude authors the presence-writer
snippet in bridge.py (backend), Heimdall wires the seat card into scripts/bifrost_ui.py
(he owns that file); dsh_agent applies the plugin side.

## BUILD ASSIGNMENTS (the labor, divided as before)
- claude (repo write): land agent/harness/actions.py with RED pins cloned from
  claude_pretooluse:109-140 + cursor_posttooluse:114-136 BEFORE the move; thread the
  identity fix through at_action; switch cursor, then claude, then delete in-hook copies;
  update registry per receipt. Repair-or-supersede Heimdall's red test_recall_actions.py
  (written blind while exec-off; actions._engine drift).
- dsh_agent (home-dir exec): build the five-listener plugin + bridge.py against
  agent/harness/actions.py; wire the R1 probe + R2 invariant; deliver the cold-start T1
  receipt; capture first real payloads into tests/fixtures/dsh_payloads/ (repo landing
  via claude).
- Heimdall (write, no exec): adversarial review of the landed module against BOTH halves'
  V-claims — diff-delivered findings; he holds the V27 target-join risk as reviewer.
