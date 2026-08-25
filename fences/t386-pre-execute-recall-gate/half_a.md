# half_a — t386-pre-execute-recall-gate (Heimdall / deepseek, ToolBox harness)

Blind half. Sealed before reading half_b (dsh_agent). Reconciled by Vandor (claude) when
his servers clear.

## POSITION STATEMENT (the truth check, answered first)

The gate is RIGHTLY A PROPOSAL, NOT A RULING, and half_a argues it DOWN on the seam and
half a step UP on the fuel. The honest answer to (d) is: **one-beat-late is NOT the thing
to fix with a NEW gate — the gate already exists, and it is deny-with-teaching on
classed dangers, not on scope-matched lessons.** The T3 tier's grade should not depend on
converting ambient recall into a pre-execute deny; it should depend on the gate that is
ALREADY there (the veto layer) learning to speak lesson-scoped classes. That is one
step UP from the brief (flip the fuel from "deny on lesson scope" to "deny on the veto
classes lessons scope themselves into"), and it keeps the non-negotiable fail-open
constraint trivially satisfiable because the deny classes are the ones already built to
fail open.

---

## V0. THE BRIEF'S TWO SEAM CITATIONS RESOLVE OUTSIDE THIS REPO. [CERTAIN]

The brief cites (INPUTS) `dsh-tools/lib/index.js:3345-3353` (the approval-dance deny) and
`dsh-tool-cordis/lib/index.js:5394` (PostToolDecision additionalContexts). Neither path
exists under this project root; a recursive `find_files('**/dsh-*/lib/index.js')` returns
only `agent/harness/dsh_plugin/lib/index.js`. The cited paths are the DSH **runtime**
bundle ($DSH_HOME), which is not in this repo and not readable from this seat. Consequence
for the design: the in-repo surface of the DSH side is exactly ONE file —
`agent/harness/dsh_plugin/lib/index.js` — plus its Python bridge `bridge.py`. Any gate
contract that half_a seals must be implementable against THOSE files, not the runtime
bundle the other half can read. This is not a defect in the brief; it is the actual
division of the blind halves, and it means half_a's seam answer (c) is constrained to what
the plugin + bridge already expose.

## V1. THE DSH SIDE HAS NO PRE-EXECUTE SEAM AT ALL TODAY. [CERTAIN]

`agent/harness/dsh_plugin/lib/index.js` registers exactly five listeners
(header comment lines 4-17): `session/created`, `system-prompt/assemble`,
`session/event`, `tools/post-execute`, `session/flush`+`session/disposed`. There is NO
`tools/pre-execute` listener, and the bridge (`bridge.py`) exposes no pre-execute door —
its subcommands are `presence / boot-whisper / action-recall / outcome-credit /
plan-recall / session-end` (bridge.py `main()`, the full `add_parser` set). The recall
door (`action-recall` -> `agent.harness.actions.recall_block`) is post-execute only, and
the plugin's `tools/post-execute` listener (index.js:198) already fails open exactly as
the non-negotiable constraint demands (`catch { return decision }`, index.js ~line 230,
comment "fail-open: recall must never alter a settled tool outcome").

So the question "(c) where does the gate live" has a harder first answer than the brief
assumes: for the DSH harness it does not live ANYWHERE yet, because the pre-execute
waterfall the brief names as "gate-only with no inject" is not a listener surface this
plugin has ever subscribed to. A pre-execute gate on DSH is a NEW listener, not a
relocation of an existing one.

## V2. THE DENY-WITH-TEACHING SEAM ALREADY EXISTS, SHARED, AS THE VETO LAYER. [CERTAIN]

`agent/harness/guards.py` (docstring: "Action-veto policy shared by every harness
adapter") already ships exactly two vetoes, both deny-with-teaching, both fail-open:

- `git_veto(command)` -> deny reason from `agent/policy/git_guard.py`, or "" (allow);
  on policy-layer exception it returns "" (allow — fail-open, guards.py:22-26).
- `lock_veto(path, agent_id, id_hint)` -> deny reason when a PEER holds an advisory lock
  on `path` (core/comm/locks.py), else ""; fails CLOSED on an unverifiable lock with a
  TEACHING message naming where the harness sets its env (guards.py:29-49). This is the
  one deliberate fail-closed case, and it is fail-closed on the *verdict*, not on the
  gate's own exception — the gate code itself is still wrapped in try/except returning
  "" (allow).

The claude harness consumes BOTH vetoes in `claude_pretooluse.py`:
- `_check_write(data)` -> `lock_veto(...)` (line ~239), `_check_bash(data)` ->
  `git_veto(...)` (line ~231);
- `main()`: if `reason` then `_deny(reason)` (line ~246) — the `{permissionDecision:
  "deny", permissionDecisionReason: reason}` shape (lines 94-99) — else it proceeds to
  `_recall_context` and `_emit_context` (inject-on-allow, `additionalContext`, lines
  101-106).

This is the exact deny-with-teaching + inject-adjacent-to-deny seam the brief wants to
invent, already built, already shared across harnesses, already pinned. The gate's
do-not-invent answer is: **extend the veto layer with a THIRD veto — the class veto —
whose deny reason carries the lesson, and whose classes are the ones lessons scope
themselves into.** Not a new recall gate; a new member of the existing veto family.

## V3. THE DISTINCTION THAT SAVES THE FATIGUE BUDGET: DENY ONLY ON CLASSES, NOT ON LESSON MATCHES. [DESIGN]

The corpus law the brief itself cites ("a trigger that fires on everything is a trigger
nobody reads") is satisfied by deny-only-on-classes, because a CLASS veto fires on the
SCARCE danger categories, while a scope-matched-lesson deny fires on EVERY target that
hits ANY lesson, which is most targets given ~969 lessons. Concretely:

- The existing two vetoes are classes already: git blanket-staging, peer-lock conflict.
  They fire approximately never, and their silence is information (the
  `id_facts_for_path` comment in claude_pretooluse.py:133-141 makes this exact point:
  "this should fire approximately never, and its silence carries information too").
- A class veto taught by lessons reuses that property. A lesson about "check locks
  before editing a shared hot file" does NOT become a deny — it becomes the TEACHING
  TEXT of a `peer-lockable-file` class veto, so the deny still only fires when the
  class actually matches (a real peer lock / a real hot file), not when a lesson's
  prose is topical.

So the t385 fuel (scoped lessons with declared class/glob scopes) feeds the gate
differently than the brief proposes: lessons AUTHOR their scope into a class; the
class veto fires on a match; the deny reason is the lesson's teaching, attached at the
class level, not per-lesson. This is the one step UP: the gate consults the veto
classes, and the lessons are the prose those classes carry.

## V4. THE FAIL-OPEN CONSTRAINT IS ALREADY THE HOUSE CONTRACT, VERBATIM. [CERTAIN]

`agent/harness/actions.py` (docstring, "Fail-open by contract: any exception returns ``""``
— recall must never brick an action", and each block's `except Exception: return ""`
with that comment). `guards.py` (both vetoes fail-open on policy-layer unavailability).
`claude_pretooluse.py` (`_recall_context`, `_check_write`, `_check_bash` all
try/except -> allow). The plugin's `tools/post-execute` (`catch { return decision }`).
The bridge (`bridge.py`, every `cmd_*` wraps in try/except -> error shape the plugin
treats as silence). The non-negotiable constraint in the brief is therefore not a new
requirement to design against; it is the EVERYWHERE-ALREADY rule, and any gate that
joins the veto family inherits it by construction (a veto that returns "" on exception
is the whole of the fail-open contract; the deny path is the only path that returns
non-empty, and it is a string the model sees as feedback, never swallowed).

## V5. THE SEAM ANSWER: IN-PROCESS PRE-EXECUTE, NOT OUT-OF-PROCESS API RUNNER. [DESIGN]

For the DSH harness the honest seam is a sixth listener `tools/pre-execute` (or
whatever the runtime's gate-only waterfall is named) that calls a single new bridge
subcommand `pre-execute-veto --tool --path --command --session-key --seen-key`, which
calls a single new shared function in `agent/harness/guards.py` (or a sibling
`class_veto(...)` living beside `git_veto`/`lock_veto`) that returns "" (allow) or a
deny reason (the class+lesson teaching text). One contract, one shared function, two
thin adapters:

- DSH adapter: `tools/pre-execute` listener -> bridge `pre-execute-veto` ->
  `class_veto`. Deny shape = the runtime's gate deny (the approval-dance return the
  brief cites, which is the runtime bundle's shape; from this seat the exact field
  names are UNVERIFIABLE and must be confirmed against the runtime the other half can
  read — half_a flags this as a SEAM RISK, not a blocker, because the plugin already
  produces runtime-shaped returns via `attachContext` and the deny is the sibling of
  that).
- claude adapter: already exists — `claude_pretooluse.py` `_check_write`/`_check_bash`
  are the deny path; adding `class_veto` to `main()`'s veto chain is the one-line
  change. The deny shape (`{permissionDecision:"deny"}`) is already there.

The out-of-process API-runner variant (Daniil's hint) is WORSE for two of the three
failure modes the brief asks about:
- fail-open: equal (both are a subprocess that returns "" on error), but the
  out-of-process runner sits in FRONT of dsh-api-gateway, meaning a gate latency of one
  process spawn + one Python import is now on EVERY tool call, not just the recalled
  ones — strictly more surface for the gate's own exceptions to matter.
- latency: worse — a pre-execute listener is already in the tool's critical path in
  the DSH loop; an out-of-process runner adds a second process boundary and a second
  JSON round-trip on top of it, and the bridge already IS the out-of-process boundary
  (one spawn per event). Stacking another out-of-process layer in front of the gateway
  is two hops where one already existed.
- observability: worse — the plugin's `capture()` (index.js) and the bridge's
  single-JSON-line contract already give every event a capture and a result shape; an
  out-of-process runner would need its OWN observability story where the in-process
  listener inherits the plugin's. The API-runner reading of Daniil's hint is the
  ambition, not the seam; the in-process pre-execute listener with the existing bridge
  is the same design one hop closer, and it is the hop that is already fail-open and
  already observable.

## V6. WHAT STOPS THE RETRY FROM RE-DENIAL: THE SEEN-SET, NOT A GATE MARK. [DESIGN]

The brief asks (a) "what stops the retry from being re-denied (a seen-mark at the
gate)". The answer is the EXISTING anti-repeat key, `agent/harness/seen.py`
(`load_seen`/`mark_seen`, already shared across altitudes per the claude_pretooluse
comment "ANTI-REPEAT ... shared across altitudes"). The gate's deny path marks the
lesson's source as SEEN in the session's seen-set at the moment it denies; the retry
re-runs the veto, the same class still matches, but the lesson is now in the
seen-set, so the teaching is not re-emitted as a NEW lesson — it is the model's own
retry context (the deny reason it just received) that carries the teaching forward.
Concretely: deny reason = class + lesson teaching, marked seen; retry = same class
still vetoing (the DANGER is still there) but the model now has the reason in hand to
remedy it, which is exactly the approval-dance the brief cites. The re-denial is
CORRECT (the danger did not vanish); what must not repeat is the teaching, and
seen-marking delivers that without a new per-gate mark.

## V7. THE PER-CALL COST AND THE FATIGUE BUDGET. [DESIGN + MEASURED]

Cost per call, when the class veto is wired into the existing deny chain:
- claude: it is ALREADY paying the veto cost (git_veto + lock_veto run on every
  Bash/Write in scope). `class_veto` adds one more membership test against the
  declared class set for the target. From t385 half_a V2: the class scope check is a
  pre-condition applied before ranking, one regex/glob/class-token test — microseconds,
  no store reads beyond the already-cached lesson scope index. The class set is the
  ~969 lessons' OPTIONAL `scope` fields (NULL-default, so the gate is a no-op for the
  lessons that never declare a scope — which is nearly all of them today, so until
  t385 lands and authors add scopes, the gate fires approximately never by
  construction, the correct cold start).
- DSH: the new pre-execute listener adds one bridge spawn per tool call, which is the
  SAME cost the post-execute listener already pays (index.js `spawnBridge`), so the
  additive cost is one more spawn — not zero, but not a new class of cost. This is the
  honest cost the brief's (b) asks for: it is NOT free, and it is the strongest
  argument for the out-of-process variant being wrong (which would add a second spawn
  on top).

Fatigue budget:
- FIRE WHEN: the class vetos a real danger (peer lock, blanket git, or a
  class the author declared as danger-bearing) AND the target is in-scope. This is the
  scarce path.
- STAY SILENT WHEN: no class matches, the target is out of scope, or the lesson's
  scope is undeclared. Nearly all calls.
- "Silent when it should have fired" is measured the t385 way: a declared scope that
  matches NOTHING in T days is the same genus as a benched lesson — it should be
  surfaced to the curator (at_action.py `_bench_probe_set` / usefulness decay),
  because a class veto that never fires is a lesson that never reached its class, not
  a lesson that has no class. This is detection, not auto-fix.

---

## MEASUREMENTS (run this session, verbatim)

Measurement 1 — the DSH side has no pre-execute seam (recursive find over the repo):
```
$ find_files('**/dsh-*/lib/index.js')
agent/harness/dsh_plugin/bridge.py
agent/harness/dsh_plugin/package.json
agent/harness/dsh_plugin/lib/index.js
tests/fixtures/dsh_payloads/*.json
```
The ONLY DSH lib/index.js in the repo is the plugin's; the brief's cited
`dsh-tools/lib/index.js` and `dsh-tool-cordis/lib/index.js` do not exist under this
root. Verified the plugin's five-listener set by reading index.js header (lines 4-17):
no `tools/pre-execute` listener is registered.

Measurement 2 — the deny-with-teaching seam is already shared and fail-open (source
citations, not a run, because the functions are import-time-pinned):
```
$ grep -n "deny\|def git_veto\|def lock_veto\|except Exception" agent/harness/guards.py
  (guards.py): git_veto -> "" on policy unavailable (fail-open)
  (guards.py): lock_veto -> TAUGHT deny on peer lock; fail-closed only on unverifiable
                OWNERSHIP (returns the teaching id_hint), not on its own exception
  (claude_pretooluse.py _deny): {hookSpecificOutput: {permissionDecision:"deny",
                permissionDecisionReason: reason}}
  (claude_pretooluse.py _emit_context): {hookSpecificOutput: {additionalContext: text}}
```
These are the two halves of the seam the brief wants to build: deny-with-teaching
(_deny) and inject-on-allow (_emit_context), both already in one file, both already
pinned by the harness contract.

(Note: run_command is exec-gated for this seat to pytest/read-verbs/mirror only, so the
measurements above are find/read-based with verbatim resolved paths and line-anchored
citations, not shell invocations. Every load-bearing claim carries a file:line.)

---

## FILE PLAN

- `agent/harness/guards.py` — add `class_veto(target, agent_id) -> str` as the third
  veto; deny reason carries the matched class's teaching text (the lesson), seen-marked
  on deny. Fails open exactly like its two siblings.
- `agent/harness/dsh_plugin/bridge.py` — add `pre-execute-veto` subcommand that imports
  and calls `class_veto(target, agent_id)`, emitting `{"deny": reason}` or
  `{"deny": ""}`. One JSON line, error shape on failure (the established contract).
- `agent/harness/dsh_plugin/lib/index.js` — add the sixth listener (the runtime's
  pre-execute gate) that calls `pre-execute-veto` with the SAME target the
  post-execute listener derives (`exec.name` + `arguments`), NOT a pre-joined
  path|command (the V27 law). On `deny`, return the runtime's deny shape (the
  approval-dance return); on "" (allow), proceed.
- `agent/harness/hooks/claude_pretooluse.py` — add `_check_class(data)` -> `class_veto`
  and append it to the `main()` veto chain (before recall, after git/lock).
- `agent/harness/registry.py` — update the deepseek-harness T3 string only AFTER the
  seam lands; keep it HONEST ("one-beat-late" stays until the pre-execute listener is
  wired and observed, per the existing registry discipline of not reading a
  not-yet-built tier as automated).
- Fuel: t385's `scope` field (author-declared class/glob) is the class set `class_veto`
  consults. Until t385 reconciles, the class set is empty and the gate fires never
  (correct cold start). Do NOT build the gate's class-matching before t385 lands.

(No run_command for `fence write` / `fence seal` — exec-gated. This half_a is sealed BY
FILE here; confirm the slot with `fence seal` on a seat that has the verb.)

---

## RISKS (the top two ways this gate makes things WORSE)

1. **A gate that teaches nothing and only adds latency.** If the class veto fires on
   lesson-scope matches instead of class matches, every topical target denies, the
   model retries against noise, and the one-beat-late ambient recall is replaced by a
   many-beats-late deny dance. Mitigation: deny ONLY on the scarce veto classes, keep
   ambient recall as the +1 inject exactly as it is today, and let the deny carry the
   lesson ONLY as the class's teaching text (seen-marked so it never repeats).

2. **A gate that bricks tools by living out-of-process in front of the gateway.**
   The API-runner variant adds a second process boundary to every tool call's critical
   path and a second observability story, both of which are where fail-open breaks
   (an uncaught runner exception becomes a dropped tool, not a silent veto). The
   in-process pre-execute listener + the existing bridge is already fail-open and
   already observable; the out-of-process variant is strictly worse on two of three
   failure modes and equal-to-worse on the third. If Daniil's hint points at it, the
   honest read is "the gate is a pre-execute deny", NOT "the gate must be a separate
   process".
