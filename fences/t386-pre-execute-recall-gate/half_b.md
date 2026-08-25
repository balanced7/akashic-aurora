# half_b — t386-pre-execute-recall-gate (dsh_agent, the runtime half)

Standpoint: this half owns the one fact only my harness can measure — the runtime's exact
pre-execute deny contract. Every verdict below cites the deployed runtime bundle
($DSH_HOME/node_modules/@deepseek-ai/dsh-tools), which is the authority for what a
pre-execute listener may return, and the repo's existing veto family, which is the policy
the gate must join rather than duplicate.

## MEASUREMENTS (run 2026-08-24, invocations verbatim)

M1. [CERTAIN] The runtime pre-execute decision contract, read from the deployed bundle:
dsh-tools/lib/index.js:3105 runs `waterfall("tools/pre-execute", exec, () => ({kind:"allow"}))`
— the default is allow. A listener returning `{kind:"deny", reason: TEXT}` causes the tool
NOT to dispatch; the result is materialized as `isError:true` with content
`[{type:"text", text:"Error: "+TEXT}]` (lines 3116-3128) — the teaching text arrives
VERBATIM in the tool result the model reads next. This is deny-with-teaching with no
additionalContexts needed: the feedback channel IS the injection channel.

M2. [CERTAIN] The listener-exception hazard: the same waterfall is wrapped in a try/catch
(lines 3103-3143) that converts ANY listener throw into `toolErrorResult(error)` — a
throwing pre-execute listener BRICKS the tool call with an error. The brief's fail-open
constraint therefore cannot be satisfied by the harness; it must be satisfied by the
ADAPTER catching its own exceptions and returning allow. This is the single most
load-bearing fact in this half.

M3. [CERTAIN] The gap today: my plugin registers zero `tools/pre-execute` listeners
(measured: `Select-String -Path agent\harness\dsh_plugin\lib\index.js -Pattern
'pre-execute'` -> 0 matches). The seam exists and is empty.

## (a)+(c) THE GATE AND THE SEAM — a third veto, not a new organ

V1. [CERTAIN] The gate does not need new harness machinery: the pre-execute waterfall
(M1) is the execution-path gate Daniil's "API runner" hint describes, already in-process.
An out-of-process API-runner variant would reimplement this waterfall one hop out with the
SAME contract and strictly more failure surface — rejected on parity-of-failure-modes.

V2. [DESIGN] The policy must join the existing veto family, not fork it: guards.py already
defines git_veto(command) and lock_veto(path, agent_id, id_hint), each returning the deny
teaching text or "" (allow), fail-open on policy-unavailable (guards.py:14-46). The recall
gate is a THIRD sibling: `class_veto(path, command, agent_id, seen_key) -> str` — it
consults t385-style scoped lessons for a class match and returns the lesson's teaching, or
"" when nothing classed matches. One family, one teaching-text shape, shared by every
adapter exactly as the first two already are.

V3. [CERTAIN] The adapter contract, pinned to the runtime: the plugin adds ONE
`tools/pre-execute` listener that (1) awaits the bridge's pre-execute-veto subcommand
(which runs class_veto against path/command extracted from exec.arguments), (2) returns
`{kind:"deny", reason: teaching}` when teaching is non-empty, (3) returns the DEFAULT
`{kind:"allow"}` on "" AND on ANY exception of its own code — because M2 proves a throw
bricks the tool, the adapter's try/catch is the fail-open, not a nicety.

V4. [DESIGN] The retry loop is closed at the veto: class_veto denies ONCE per
(target, lesson) via the existing seen-mark machinery, so the model's re-issued call
passes and executes with the teaching already in the failure feedback (M1). Without the
seen-mark the gate is an infinite deny loop; with it, the deny is a teach-then-execute
handshake, not a wall.

## (b) THE COST AND THE FATIGUE BUDGET

V5. [DESIGN] Per-call cost: one bridge round-trip on EVERY pre-execute (the subcommand
spawn), plus the veto's scope consult — the same order as the post-execute calls already
made per action. The budget that keeps it survivable is the fire rule, not the query: the
gate DENIES only when a scoped lesson's class matches the action — "approximately never"
— and silence is information (no classed danger present). One deny per (target, lesson)
per session is the hard budget (V4's seen-mark IS the budget).

## (d) THE TRUTH CHECK

V6. [CERTAIN] The honest maximum is the hybrid, and T3's final grade should say so:
ambient recall stays ONE-BEAT-LATE (post-execute context rides the next step; that is
correct and cheap), and classed dangers are stopped AT the action by the veto (M1's
deny-with-teaching). "Fix one-beat-late" taken literally — injecting before every call —
would mean denying or steering on every action, which is the alert-fatigue law as a
feature request. The veto is the only shape that buys at-action protection at
approximately-zero noise cost.

V7. [DESIGN] Cross-harness: class_veto lives beside its siblings in agent/harness/guards.py
(the shared policy file both adapters already import); claude_pretooluse gains one veto
call on its existing deny path; the DSH plugin gains one pre-execute listener (V3). Two
adapters, one family, no new organ.

## FILE PLAN

- agent/harness/guards.py — class_veto(path, command, agent_id, seen_key): scope consult
  (t385 contract once landed) + teaching text + seen-mark; fails open on policy-unavailable.
- agent/harness/dsh_plugin/bridge.py — `pre-execute-veto` subcommand (JSON in/out, never
  raises; any failure emits the allow shape).
- agent/harness/dsh_plugin/lib/index.js — one tools/pre-execute listener implementing V3
  with the adapter fail-open.
- agent/harness/hooks/claude_pretooluse.py — one class_veto call on the existing deny path.
- tests/test_t386_veto.py — RED pins: (1) a scoped lesson + matching action -> deny with
  the teaching verbatim; (2) non-matching action -> allow, zero overhead; (3) veto
  exception -> allow (adapter fail-open); (4) retry after deny -> allow (seen-mark).

## RISKS (the two ways this makes things WORSE)

R1. [DESIGN] The bricked-tool class: any exception escaping the listener becomes a tool
error (M2) and the gate starts failing CLOSED, which the brief forbids. Mitigation: the
adapter try/catch is the pinned contract (V3), and pin (3) above fails the build if it
ever regresses.

R2. [DESIGN] Teaching fatigue by false class matches: a scope that matches too broadly
turns the "approximately never" gate into a nag, and the model learns to retry past it
without reading — the worst outcome (latency plus a dead channel). Mitigations: t385's
scope-health counters (fires-per-session ceiling) feed the same seen-mark budget, and a
deny whose teaching was not acted on (the same class re-fires next session) is a curation
surface, not a silent repeat.
