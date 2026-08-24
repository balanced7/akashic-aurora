# half_a — t383-dsh-adapter (deepseek, house-adapter side)

The DSH adapter design plus the rule-of-three extraction, from the seat that owns
claude_pretooluse and cursor_posttooluse. Companion to half_b (dsh_agent's event-inventory
half). Every load-bearing claim is a V-verdict; citations are repo-relative and M1-PV-verifiable.

---

## (a) THE ADAPTER — per-tier seam, translation, shared call, file plan

### Architecture line (one rule, stated once)

The architecture rule I hold hardest (and the tiers doc's own): harness adapters TRANSLATE JSON;
shared code DECIDES POLICY; nothing outside an adapter's own files imports a harness name.

V1. The two in-tree adapters obey a clean split — claude_pretooluse translates Claude's [CERTAIN]
`{tool_input: {command, file_path}, session_id}` into the shared policy predicates and the
recall engine, and never re-implements scope or anti-repeat
cite: agent/harness/hooks/claude_pretooluse.py:78 (_in_scope maps tool names onto
agent/harness/scope.py).

V2. The DSH adapter must be the SAME shape: a thin `dsh-akashic` cordis plugin that listens to [DESIGN]
DSH's seams, extracts a (session_key, path, command) triple plus an event kind, and forwards to
shared house functions — never re-implementing recall/credit/scope/nudge/seen .

### T2 — session cue (auto-boot whisper lands at session start)

V3. DSH's session-open=system-prompt/assemble waterfall is INJECT-yes (mutate/replace per step), [CERTAIN]
so the T2 whisper rides the first assemble call, one additionalContext entry carrying the boot
whisper, tiered by cwd like Claude's SessionStart — the seam is from the brief INPUTS
("session open = system-prompt/assemble waterfall INJECT-yes").

V4. The whisper TEXT is house-owned and already exists: the shared session-start whisper lives in [INFERRED]
agent/harness/context.py (the tiered-by-cwd light whisper claude_sessionstart.py renders), so the
DSH adapter calls the same renderer and only translates the DSH cwd field into scope .

V5. Scope gate = session_in_scope(cwd) from agent/harness/scope.py — repo or home ONLY, so the [CERTAIN]
whisper never fires for a DSH session launched outside the house
cite: agent/harness/scope.py:43 (session_in_scope).

### T3 — action recall, one-beat-late

V6. DSH pre-tool = tools/pre-execute is gate-only, NO inject, so T3 is one-beat-late exactly like [CERTAIN]
Cursor: recall rides the post-execute seam's additionalContexts FIFO, not the pre-tool
— "pre-tool = tools/pre-execute gate-only NO inject; post-tool = tools/post-execute INJECT-yes" is
in the brief INPUTS (Vandor's inventory, bus 1787543753648-0).

V7. The recall call is the ALREADY-EXTRACTED external contract core/recall/actions.py::recall_context [CERTAIN]
(session_key, path, command) -> {lessons, locks, counter, verbs, shown, total, faithful, confidence,
error?} cite: core/recall/actions.py:77. This is the exact seam the out-of-tree plugin is
ALREADY pinning (tests/fixtures/dsh_payloads/README.md names it) — the adapter does NOT shell out
to `py agent_cli.py recall-at`, it imports the contract, which is the whole reason it exists.

V8. The one-beat-late status means a lesson surfaces AFTER the action it would have warned [CERTAIN]
about — the honest registry string, matching Cursor's own T3 line
cite: agent/harness/registry.py (cursor T3 = "one-beat-late").

### T4 — outcome credit, DIRECT

V9. DSH tool failure = "the same waterfall as errors, DIRECT fail signal" (brief INPUTS), which is [CERTAIN]
the Cursor (not Claude) precedent: a real postToolUseFailure-equivalent that can call the credit
engine directly, no transcript synthesis
cite: agent/harness/hooks/cursor_posttooluse.py:117 (on "failure": resolve_action_outcome(sid, target, False)).

V10. The entry point is core/recall/at_action.py::resolve_action_outcome(session_id, target, success) [CERTAIN]
-> {"flipped","credited","sources"} cite: core/recall/at_action.py:924. The target MUST
come from normalize_target(path, command) [CERTAIN] cite: core/recall/at_action.py:835, or the
surface/resolve join silently evaporates.

V11. THE GAP THIS FENCE MUST CLOSE: the existing external contract recall_context does T3 ONLY — [CERTAIN]
it calls recall_at but never resolve_action_outcome, mark_impression, normalize_target, or
log_injection cite: core/recall/actions.py:77 (body forwards to recall_at, returns the
recall dict; no outcome call). So a DSH tool-failure importing the contract TODAY gets recall and
zero T4 credit. This is the precise seam half_b and I must reconcile on.

V12. My recommended close for the gap in V11: extend actions.py with a second contract fn (e.g. [DESIGN]
resolve_tool_outcome(session_key, path, command, success)) so the external plugin keeps ONE stable
surface, rather than have the repo-resident adapter call at_action directly. The DECISION belongs
to reconciliation .

V13. THE IDENTITY LEAK (verified, must fix before T4 seals): _log_outcome_stage reads the agent [CERTAIN]
from ENV, not a parameter cite: core/recall/at_action.py:1007 ("agent": str(os.getenv("AKASHIC_AGENT_ID"))).
Because the DSH seat inherits Claude Code's env (AKASHIC_AGENT_ID=claude — the T1 block and my
work-order survey), every DSH outcome-stage record would be mis-attributed to claude.

V14. The fix for the leak in V13 is to thread agent_id/session_key into _log_outcome_stage, NOT to [DESIGN]
set env in the plugin (a plugin-side setenv is fragile and would still fail on any path that
bypasses it) .

V15. On a FAIL->SUCCESS flip the adapter emits the JIT learn nudge via build_learn_nudge(target, [CERTAIN]
credited, sources, agent_id) cite: core/recall/at_action.py:1301, rate-limited by
agent/harness/nudge.py::nudge_allowed/mark_nudged — which is caller-owned (nudge_dir per harness),
so DSH adds a dsh nudge dir, no shared-module change [CERTAIN] cite: agent/harness/nudge.py:38.

### T5 — plan-time recall (DSH's edge over Cursor)

V16. DSH has no dedicated pre-prompt waterfall, but the per-step assemble checkpoint gives a [INFERRED]
DERIVED inject-yes for plan-time recall (brief INPUTS; the one UNCERTAIN is whether a dedicated
pre-prompt-submit seam exists among agent/* checkpoints) .

V17. If the derive holds, T5 is "derived" — a grade Cursor cannot reach (its beforeSubmitPrompt [CERTAIN]
cannot inject) — and it puts DSH ahead of the Cursor baseline on the one seam Cursor is weakest
 cite: agent/harness/registry.py (cursor T5 = "unavailable").

### T6 — session close

V18. DSH session close = session/disposed + awaited session/flush, capture-yes, so the session-end [CERTAIN]
auto-draft fires there, mirroring claude_sessionend/cursor_sessionend's wrap -> chronicles/
last-session-draft.md — the draft mechanism is house-owned; the adapter only needs to
call the same wrap path on the flush await.

### File plan (ownership: repo-via-claude vs home-dir-via-dsh_agent)

V19. The plugin lives OUT-OF-TREE in the DSH profile layer (dsh_agent owns it via its own exec; [CERTAIN]
its CAPS CONSTRAINT says it has NO repo write), so hot-reload (cordis-plugin-hmr) iterates the
wiring loop WITHOUT the house repo moving cite: fences/t383-dsh-adapter/brief.md INPUTS
(hot-reload + CAPS CONSTRAINT).

V20. The repo side (landed via claude, who HAS repo write) is exactly two things: (1) the shared [DESIGN]
extraction module this fence designs (section b), and (2) optionally a second external contract fn
in core/recall/actions.py for T4 (V11/V12). Nothing harness-specific enters the repo beyond those
shared seams .

---

## (b) THE EXTRACTION — rule of three, now triggered

V21. The recall-block orchestration exists as TWO deliberate copies today: _recall_context in [CERTAIN]
claude_pretooluse cite: agent/harness/hooks/claude_pretooluse.py:109, and _recall_block
in cursor_posttooluse [CERTAIN] cite: agent/harness/hooks/cursor_posttooluse.py:60. Both do the
identical sequence: recall_at -> render -> mark_seen -> normalize_target -> mark_impression ->
log_injection, with load_seen as the anti-repeat input. DSH is the third harness, so the tiers
doc's pre-declared extraction now fires [CERTAIN].

V22. The shared module: agent/harness/recall_block.py exposing ONE function, recall_block(session_key, [DESIGN]
path, command, agent_id) -> str, which encapsulates the full orchestration and returns the rendered
text (or ""). It is the union of the two copies' bodies, parameterized on the things the copies
differ on (session_key source, agent_id) .

V23. What stays per-adapter: the JSON translation (tool_input vs argv event vs DSH waterfall), the [DESIGN]
scope gate call, the emit shape (hookSpecificOutput.additionalContext vs additionalContexts FIFO),
and the kill-switch FIRST check. recall_block stays kill-switch-agnostic-contract-clean: the adapter
honors AKASHIC_RECALL_AT_ACTION=0 before calling it, exactly as both copies do today .

V24. Migration order (strangler-fig, no big-bang): (1) land agent/harness/recall_block.py as a NEW [DESIGN]
module, unused; (2) re-point claude_pretooluse._recall_context at it and keep cursor_posttooluse
green — verify via tests/test_claude_hook_contract.py and tests/test_cursor_hook_contract.py;
(3) when both pass, delete the copied bodies in favour of the call; (4) DSH wires recall_block as
its third caller. At no step do two copies and the module all carry divergent logic — each copy is
re-pointed and its body removed in the same commit .

V25. The extraction does NOT touch T4: resolve_action_outcome and the flip/nudge path live in [CERTAIN]
core/recall/at_action.py and are shared already; only the recall-block (surface) half was
duplicated. So (b) is the surface extraction, and (a)'s T4 seam (V11/V13) is a SEPARATE, smaller
fix cite: agent/harness/hooks/cursor_posttooluse.py:112 (imports resolve_action_outcome
DIRECTLY from at_action, no local copy).

---

## (c) THE GRADE — the honest registry line, ready to paste

V26. On the seams named, DSH earns 7/7-with-nuances: T0 yes; T1 yes (once the .dsh/.env stamp's [DESIGN]
cold-start receipt lands); T2 yes; T3 one-beat-late; T4 DIRECT-once-V11/V12-ship; T5 derived (if
V16's derive verifies, else unavailable); T6 yes . The paste-ready block:

```
    "deepseek-harness": {
        "default_agent_id": "dsh_agent",
        "adapters": "out-of-tree dsh-posttool (cordis) plugin -> core/recall/actions.py "
                    "(+ agent/harness/recall_block.py after extraction)",
        "tiers": {
            "T0": "yes -- exec proven: drives py agent_cli.py + messages peers",
            "T1": "yes -- .dsh/.env stamps AKASHIC_AGENT_ID=dsh_agent (stamp applied, receipt pending)",
            "T2": "yes -- session-open system-prompt/assemble waterfall INJECT (whisper tiered by cwd)",
            "T3": "one-beat-late -- pre-execute is gate-only; recall rides post-execute additionalContexts",
            "T4": "direct -- tool failure is a real fail event (same waterfall as errors), "
                  "no transcript synthesis",
            "T5": "derived -- per-step assemble inject-yes (no dedicated pre-prompt seam; "
                  "stronger than Cursor's unavailable)",
            "T6": "yes -- session/disposed + flushed wrap -> last-session-draft.md",
        },
    },
```

V27. Note this SUPERSEDES my work-order registry row (which honestly said "pending -- awaiting [CERTAIN]
event inventory"): that row was correct when written, but the inventory has since landed in the
brief INPUTS, so the grade above is the intended graduation
cite: agent/harness/registry.py (current row has T2-T6 "pending").

---

## RISKS — top two ways this fails silently

V28. RISK 1 (identity leak, already real): DSH outcome-stage records are written under [CERTAIN]
AKASHIC_AGENT_ID read from the INHERITED claude env (core/recall/at_action.py:1007), so T4 credit
looks correct locally while the durable prevention dataset attributes DSH rescues to claude. Silent
because nothing errors — the flip logs, the credit counts, only the attribution is wrong .

V29. RISK 2 (target-join evaporates across the DSH process boundary): normalize_target must produce [DESIGN]
the IDENTICAL string at surface (post-execute recall) and resolve (failure waterfall) time. If the
DSH plugin derives path/command differently between the two seams — e.g. relative vs absolute, or a
FIFO-added prefix — the surface impression never joins the outcome and every flip is credited zero,
silently. The guard is the same pin discipline as Cursor's fixtures: capture a surface +
resolve pair for the SAME action and assert target equality, before trusting any credit number.

V30. RISK 3 (T5 derive assumed when the seam is honest-absent): if the agent/* checkpoint genuinely [DESIGN]
lacks a pre-prompt inject, "derived" is flattery and the grade must drop to "unavailable". The
brief INPUTS already flag this as the one UNCERTAIN seam; failing to downgrade on evidence is the
flattery the matrix exists to forbid.

---

## ADDENDUM (post-write, reconciliation-window findings — deepseek, NOT part of the sealed blind round)

These three findings landed AFTER half_a's body was written (half_b was still open); they are
folded here rather than renumbering the V-sequence, so the reconciliation has them in one place.

A1. THE CONTRACT MODULE WAS RED, AND I FIXED IT. [CERTAIN]
tests/test_recall_actions.py (the executable spec for core/recall/actions.py) was written while my
exec was off and never ran; it fails with AttributeError because the test monkeypatches
`core.recall.actions._engine`, but actions.py had NO module-level _engine — it imported recall_at
function-locally inside recall_context. This is the exact "critical fact" my D2 survey surfaced in
a different form: the contract module existed but was UNTESTABLE (the engine seam was an
implementation detail, not a swappable symbol). I fixed actions.py by adding a module-level
`_UNRESOLVED` sentinel + `_resolve_engine()` lazy resolver, so recall_context now calls through
`_resolve_engine()(…)`. The fix preserves the cheap-import discipline (heavy at_action stays out
of the import path until first use) AND makes the kill-switch test's `_engine = None` genuinely
short-circuit. cite: core/recall/actions.py:88 (_UNRESOLVED), :92 (_resolve_engine), :102
(recall_context def — was :77 before the edit).

A2. LINE-NUMBER COLLISION WITH half_b — M1-PV WILL FLAG IT. [CERTAIN]
My A1 edit SHIFTED actions.py: recall_context moved 77 -> 102; the required-key guard
(error="MissingSessionKey") moved ~95-107 -> 124. half_b cites core/recall/actions.py:77 and
core/recall/actions.py:95-107 / :101-107 in [CERTAIN] verdicts (its V4/V8/R3). Those citations are
now WRONG — they point at my _UNRESOLVED/_resolve_engine machinery, not the code half_b meant.
This is the normal consequence of editing a shared file both halves cited; the resolution is
mechanical, not a design change: land the A1 fix FIRST (so line numbers stabilize), then re-run M1-PV
and re-anchor half_b's three actions.py citations (77->102, 95-107->~114-127) during reconciliation.

A3. CONVERGENCE + TWO DESIGN DIFFS WITH half_b TO RESOLVE. [CERTAIN]
Convergence is strong: both halves independently reach T3=one-beat-late, T4=DIRECT, T5=derived,
T6=flush, and both land a shared orchestration module. TWO diffs remain for reconciliation:
  (a) NAMING + SHAPE of the shared module: half_b names agent/harness/actions.py and proposes THREE
      functions — recall_block (surface) + outcome_block (flip/nudge, lifted from
      cursor_posttooluse:114-136) + plan_block (from claude_userpromptsubmit.build_plan_recall). My
      half_a (V22) proposed a single agent/harness/recall_block.py::recall_block. half_b's
      three-function split is CORRECT and supersedes mine: V25 thought the extraction did NOT touch
      T4, but half_b is right that the outcome_block flip/nudge path is a SECOND duplication (in
      cursor_posttooluse AND claude_posttooluse) that the third harness also triggers. I adopt
      half_b's richer shape. [DESIGN]
  (b) THE IDENTITY LEAK (my V13/V14, RISK 1) vs half_b's R3 mitigation. Both agree the fix is
      structural (explicit session_key, never env). My V13 notes _log_outcome_stage reads
      AKASHIC_AGENT_ID from env (core/recall/at_action.py:1007) — half_b's R3 does NOT name that
      specific env read. So one real gap REMAINS: even with the plugin hardcoding session_key, the
      outcome-STAGE ledger record (not the plugin's own attribution) still reads env inside
      at_action. The reconciliation must decide whether to thread agent_id into _log_outcome_stage
      (my V14) or accept env-as-is on the stage record (half_b's R3 stopgap). This is a real
      discrepancy, not a wording one. [DESIGN]

