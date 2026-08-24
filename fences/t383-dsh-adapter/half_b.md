# t383-dsh-adapter — half_b (author: dsh_agent)

The DSH-native design. Every load-bearing claim carries a V-verdict with a verdict tag on
its first line. CERTAIN = a file:line citation read from the live checkout; DESIGN = my
chosen shape (a decision, not a fact); UNCERTAIN is flagged, never papered over. I have
not read half_a.

## (a) THE ADAPTER — one thin plugin, five listeners, one bridge

V1. DSH is a cordis composition; plugins inject through each seam's typed envelope. [CERTAIN]
  cites: @deepseek-ai/dsh-tools/lib/types/index.d.ts:24-94 (tools/* events);
  @deepseek-ai/dsh-session/lib/types/index.d.ts:32-76 (session/* events);
  @deepseek-ai/dsh-system-prompt/README.md:25 (assemble waterfall).

V2. THE LAYOUT — JS side translates; every policy decision lives in Python in the repo. [DESIGN]
  One bridge process per event: the Python half is hot by construction (fresh subprocess
  re-imports every call); the JS half hot-reloads via cordis-plugin-hmr. HMR hot-swap
  [CERTAIN] — @deepseek-ai/dsh-mcp-client/README.md:32: "editing the entry triggers
  disconnect + reconnect without process restart".

Plugin layout (profile layer, owned by dsh_agent, home-dir — no repo write):
  C:\Users\L5\.dsh\profiles\web\plugins\dsh-akashic-recall\
    lib/index.js      five listeners + renderers + spawn glue (V1 skeleton exists)
    bridge.py         subcommands boot-whisper | plan-recall | action-recall | outcome-credit | session-end
    package.json      name + peer dep (exists)
  C:\Users\L5\.dsh\profiles\web\cordis.patch.yml   loader entry (one row)
  C:\Users\L5\.dsh\.env                            AKASHIC_AGENT_ID=dsh_agent (applied; receipt pending cold start)

Bridge subcommands call shared repo functions and print one JSON line; any non-zero exit
or non-JSON output is fail-open silence, never a blocked action. [DESIGN]
  Fail-open contract mirrored [CERTAIN] — core/recall/actions.py:26-31.

V3. T2 — session open: session/created triggers; system-prompt/assemble injects the whisper once. [DESIGN]
  session/created is an observe-only lifecycle announcement [CERTAIN] —
  @deepseek-ai/dsh-session/lib/types/index.d.ts:44.
  Assemble is scoped via AssembleContext.scope and listeners mutate/replace the delivered
  prompt [CERTAIN] — @deepseek-ai/dsh-system-prompt/README.md:25,33.
  Whisper builder [CERTAIN] — agent/harness/context.py:223
  build_autoboot_context(cwd, agent_id, session_id).
  JSON in {cwd, session_id, agent_id}; out whisper text; anti-repeat flag keyed by
  DSH_SESSION_ID. The exact assembly-mutation shape is capture-first material. [DESIGN]

V4. T3 — post-tool-call, one beat late: post-execute extracts, recalls, attaches contexts. [DESIGN]
  tools/post-execute signature [CERTAIN] — @deepseek-ai/dsh-tools/lib/types/index.d.ts:61.
  additionalContexts are ferried on the result to the loop's active-batch FIFO [CERTAIN] —
  @deepseek-ai/dsh-tools/lib/index.js:3358-3360; PostToolDecision
  @deepseek-ai/dsh-tools/lib/types/index.d.ts:427-445.
  Explicit-session-key recall contract [CERTAIN] — core/recall/actions.py:77
  recall_context(session_key='dsh_agent', path, command).
  Extraction keys file_path/path/command, capture-first (argKeys already recorded to
  %TEMP%\akashic_recall\payloads_dsh). The injection reads as "recall for what you just
  ran," not a pre-action gate — honest one-beat-late. [DESIGN]

V5. T4 — tool failure, direct: the same listener sees isError; FAIL half, then retry-recall. [DESIGN]
  Thrown tools still reach the waterfall as errors [CERTAIN] —
  @deepseek-ai/dsh-tools/lib/types/index.d.ts:51-55; result.isError at :410-411.
  FAIL half [CERTAIN] — core/recall/at_action.py:924 resolve_action_outcome.
  Retry-moment + flip + nudge precedent [CERTAIN] —
  agent/harness/hooks/cursor_posttooluse.py:15-22,114-136; nudge builder
  core/recall/at_action.py:1301; rate limit agent/harness/nudge.py.
  tools/result is observe-only [CERTAIN] — @deepseek-ai/dsh-tools/lib/types/index.d.ts:83;
  it is NOT an injection seam; seen/impressions/ledger bookkeeping runs inside the bridge.

V6. T5 — prompt submit, DERIVED: user/message triggers; next assemble carries plan recall. [DESIGN]
  user/message is a surface event type [CERTAIN] —
  @deepseek-ai/dsh-session/lib/types/types.d.ts:262,367; feed via session/event
  @deepseek-ai/dsh-session/lib/types/index.d.ts:66.
  Per-step assembly with assembleContextFor(agent) [CERTAIN] —
  @deepseek-ai/dsh-agent-loop/lib/index.js:497.
  Plan-altitude builder today adapter-local [CERTAIN] —
  agent/harness/hooks/claude_userpromptsubmit.py:56 build_plan_recall.
  No DEDICATED pre-prompt-submit waterfall found among the shipped packages; agent/*
  checkpoints exist (@deepseek-ai/dsh-agent-loop/README.md:17,77) but the generated
  core.md is not shipped — the derived assembly is the T5 carrier until capture proves
  otherwise. Kill switch AKASHIC_PLAN_RECALL=0. [UNCERTAIN]

V7. T6 — session close, capture: flush + disposed run the where-we-are distiller. [DESIGN]
  session/disposed [CERTAIN] — @deepseek-ai/dsh-session/lib/types/index.d.ts:54;
  session/flush awaited parallel [CERTAIN] — same file :75.
  Draft file contract [CERTAIN] — agent/harness/hooks/claude_sessionend.py:10-13.
  Capture-only; nothing is injected into a closing session. [DESIGN]

V8. SCOPE + IDENTITY: agent-scoped listeners; explicit dsh_agent key; observe-only on mismatch. [DESIGN]
  Scope-filtered dispatch [CERTAIN] — @deepseek-ai/dsh-scope/README.md:5,15.
  Inherited-env footgun closed by the required-key contract [CERTAIN] —
  core/recall/actions.py:95-107.
  seen-key = DSH_SESSION_ID (per-session anti-repeat); startup self-check logs loud and
  pins observe-only if AKASHIC_AGENT_ID resolves to anything but dsh_agent. [DESIGN]

## (b) THE EXTRACTION

V9. Land site: agent/harness/actions.py — the tiers doc pre-declared it. [CERTAIN]
  docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md:131-132
  ("extract it first (the deferred actions.py)").

V10. Shape — orchestration functions WITH side effects, distinct from the pure contract. [DESIGN]
  core/recall/actions.py is pure (returns a dict, writes nothing) [CERTAIN] —
  core/recall/actions.py:1-55.
  recall_block(session_key, seen_key, path, command) -> str — recall_at → render →
  mark_seen(seen_key) → mark_impression → log_injection, whole body in try/except
  returning "" — lifted in behavior from the canonical copy [CERTAIN] —
  agent/harness/hooks/claude_pretooluse.py:109-140.
  outcome_block(session_key, seen_key, target, success) -> str — resolve_action_outcome +
  flip ledger + build_learn_nudge under the rate limit — lifted in behavior [CERTAIN] —
  agent/harness/hooks/cursor_posttooluse.py:114-136.
  plan_block(prompt, session_key, seen_key) -> str — lifted from
  claude_userpromptsubmit.build_plan_recall, today adapter-local; absorbing this second
  duplication into the shared module is my proposal. [DESIGN]

V11. What stays per-adapter: extraction, scope gate, envelope emission, session-key plumbing. [DESIGN]
  Follows the brief's architecture rule: "harness adapters translate JSON; shared code
  decides policy." [CERTAIN]

V12. Migration order (strangler-fig): RED pins; switch cursor; switch claude; delete; DSH last. [DESIGN]
  Land the module with RED pins cloned from the two hooks' current behavior; switch
  cursor_posttooluse; switch claude_pretooluse; delete the in-hook copies last; then DSH
  wires against the same module through the bridge — DSH never copies the orchestration,
  which is the whole point of the rule of three.

## (c) THE GRADE — registry lines, in the registry's own vocabulary

V13. Proposed HARNESSES["dsh"] tier strings, ready to paste. [DESIGN]
  Vocabulary: honest "how" strings, "unavailable beats pretended capability" [CERTAIN] —
  agent/harness/registry.py:15-18.
  T0: "yes -- shell (pwsh) + ai_setup_mcp.py via @deepseek-ai/dsh-mcp-client"
  T1: "yes -- $DSH_HOME/.env stamps AKASHIC_AGENT_ID=dsh_agent (dsh-launch-environment
       user-env layer); session key derived from DSH_SESSION_ID"
  T2: "yes -- system-prompt/assemble whisper once per session (session/created trigger)"
  T3: "one-beat-late -- tools/post-execute additionalContexts; tools/pre-execute is an
       allow/deny/ask gate (no injection)"
  T4: "yes, DIRECT -- post-execute receives thrown-tool failures as isError"
  T5: "derived -- plan-time recall rides per-step system-prompt/assemble after
       user/message; no dedicated prompt-submit waterfall found (UNCERTAIN)"
  T6: "yes -- session/flush + session/disposed -> chronicles/last-session-draft.md"

That is 7/7-with-nuances: T3 one-beat-late (the honest Cursor precedent), T5 derived —
earned by the seams, not assumed.

## FILE PLAN (one line each, ownership)

Repo, lands via claude (dsh_agent has no repo write):
  agent/harness/actions.py          shared orchestration (V10) — extraction, claude's gate
  agent/harness/registry.py         the "dsh" entry (V13) — same change as the extraction
  tests/fixtures/dsh_payloads/      captured DSH payload pins — after first wired captures
  tests/test_dsh_contract.py        contract test, skip-with-reason until pins land
  core/recall/actions.py            contract module — already live, unchanged by my half
Home-dir, applies via dsh_agent exec:
  C:\Users\L5\.dsh\.env                                applied (receipt pending cold start)
  C:\Users\L5\.dsh\profiles\web\plugins\dsh-akashic-recall\{lib/index.js,bridge.py,package.json,README.md}
  C:\Users\L5\.dsh\profiles\web\cordis.patch.yml       loader row — wire AFTER step 4 of V12

## RISKS (the top ways this fails silently)

R1. CONTEXT DROPPED AFTER INJECTION. includeRuntimeContext:false or a scoped suppressor
"removes all such contexts, including listener additions" — the plugin injects, the ledger
logs the push, the model never sees it, every organ reads healthy. [CERTAIN for the drop]
  cite: @deepseek-ai/dsh-system-prompt/README.md:12,55.
  Mitigation [DESIGN]: once-per-session probe — inject a tiny marker on the first
  assemble, verify the loop assembled it (observable in the next request/session log), log
  a loud "context dropped" if not; the injection ledger stays the truth source.

R2. HMR GENERATION RACE — WIRED BUT ABSENT. Patch hot-reload replaces the plugin instance;
a mid-edit reload can leave tools/post-execute unlistened with no error, and the harness
runs silently without recall. [CERTAIN for the replacement semantics]
  cite: @deepseek-ai/dsh-mcp-client/README.md:65-70 (re-sync replaces generations).
  Mitigation [DESIGN]: register an invariant via @deepseek-ai/dsh-invariants ("a
  post-execute listener is present") so absence is loud at load; activation logging on
  every reload.

R3. IDENTITY DRIFT AT COLD START. A launch inheriting AKASHIC_AGENT_ID=claude despite the
.env stamp (layer misordering) would mis-attribute injection. Mitigation is structural:
session_key is hardcoded-explicit in the plugin (never env), the shared module rejects
missing keys loudly (core/recall/actions.py:101-107 [CERTAIN]), and the V8 startup
self-check pins the plugin to observe-only on mismatch. The cold-start receipt (pending)
proves the stamp end to end. [DESIGN]
