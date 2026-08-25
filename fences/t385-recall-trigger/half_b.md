# half_b — t385-recall-trigger (dsh_agent, the harness-seat half)

Standpoint: I reach recall through a cordis plugin that extracts `file_path`/`path`/`command`
from DSH tool arguments (`agent/harness/dsh_plugin/lib/index.js::extractTarget`) — so DEFECT 1
lives in MY wall. I also spent the night of 2026-08-24 repairing the target JOIN across this
exact seam (the V27 `normalize_target` law, tests/test_dsh_contract.py), so every verdict below
is written from the side that will have to implement this design in a foreign harness.

## MEASUREMENTS (run 2026-08-24, invocations verbatim)

M1. [CERTAIN] Batch blindness reproduces: `py -c "from core.recall.at_action import
recall_at, normalize_target; r = recall_at(command='py - << PYEOF'); print(normalize_target(
None, 'py - << PYEOF'), len(r.get('lessons', [])))"` -> `'c:py - << pyeof'`, **0 lessons**. The
wrapper eats the file set.

M2. [CERTAIN] The class-lesson is unreachable from the file it was born on: `py -c "from
core.recall.at_action import recall_at; r = recall_at(path='scripts/bifrost_daemon.py');
print([l.get('source') for l in r.get('lessons', [])])"` -> three lessons,
`shared_file_lock_handoff` NOT among them.

M3. [CERTAIN] When both path and command exist, one is silently DROPPED: `py -c "from
core.recall.at_action import normalize_target; print(normalize_target('E:/AI-Setup/docs/
WISHLIST.md', 'py scripts/ops/whatever.py'))"` -> `'p:e:\\ai-setup\\docs\\wishlist.md'` — the
command vanished. Single-key derivation is lossy in BOTH directions.

M4. [CERTAIN] A cheap extractor recovers the true file set from a wrapper command: script
(research/in-flight/_m4_target_extract.py) scanning a heredoc that names
`scripts/bifrost_daemon.py` and `core/recall/at_action.py` -> `['scripts/bifrost_daemon.py',
'core/recall/at_action.py']` in **0.106ms**. Feasibility of (a) is measured, not assumed.

## (a) THE TRIGGER'S TRUE SURFACE — derive a TARGET SET, not a target

V1. [CERTAIN] The defect class is single-key derivation: the trigger keys on ONE string
(command OR path), so a wrapper hides its files and a path hides its command; M1 and M3 are the
two loss directions. Cited: core/recall/at_action.py:835 (`normalize_target` returns path when
present, command only otherwise), :1702 (`recall_at(*, path=None, command=None)`).

V2. [DESIGN] The derivation is a **TargetSet**: `{paths: [...], commands: [...],
scope_hints: [...]}`. Adapters build it by (1) passing through declared tool arguments
(file_path/path), (2) running the SHARED file-reference extractor over the command string (M4's
mechanism, one regex, no shell), (3) attaching any declared lesson-scopes the target matches
(see (b)). Every member normalizes through the EXISTING `normalize_target` — the V27 join law is
kept per-member, not weakened.

V3. [DESIGN] One engine, one contract: `recall_at` gains an optional
`targets: TargetSet | None` input (a superset of the current path/command signature — backward
compatible). The engine queries EACH member, merges results by source (dedup), and hands the
merged set to the EXISTING `render` (at_action.py:1893) — the funnel's ranking decides display,
untouched. The trigger decides WHO is a candidate; the funnel decides WHAT shows. That is the
brief's own line and it is kept.

V4. [DESIGN] Per-call cost, bounded: k queries + k impressions, k = len(paths) + 1 command +
matched scopes, **capped at 5**. Measured marginal cost of the extraction itself is 0.106ms
(M4); the dominant cost is k × query, and the cap is the alert-fatigue guard — a trigger that
fires on everything is a trigger nobody reads, so k stays small and non-file garbage (flags,
bare words) never becomes a target.

V5. [DESIGN] The impression JOIN across multiple targets (the V27 class multiplied): a surface
impression on target A must resolve on the SAME target A. `mark_impression`/`resolve_action_
outcome` iterate the same TargetSet members pairwise, so a multi-target action credits flips
only per-member — no cross-member evaporation, which is the silent failure the night already
taught me once.

## (b) SCOPED LESSONS — yes, declared at the door, matched at the trigger

V6. [CERTAIN] The 40-day failure is structurally guaranteed today: the trigger's only inputs
are a string and prose similarity, and a CLASS is neither. Cited: M2; the brief's
2026-07-15 -> 2026-08-24 double violation of `shared_file_lock_handoff`.

V7. [DESIGN] Schema: a lesson may declare `scope` at learn time:
`{"globs": ["scripts/bifrost_*.py"], "classes": ["peer-lockable file"], "predicates": []}` —
authored by the writer, amendable by a curator through the same learn door (a wrong scope is a
lesson edit, not a schema change). `classes` map to a small registry of class DEFINITIONS
(glob→class) that the engine evaluates; predicates stay empty until one class proves it needs
code (never first).

V8. [DESIGN] Composition with similarity WITHOUT touching the funnel: a scope match is a
TRIGGER input — it puts the lesson into the candidate set for the members it governs. The
funnel's ranking then decides display exactly as today. No reranking, no boost, no
suppression change: the funnel is reserved terrain and this design does not enter it.

V9. [DESIGN] Wrong-scope detection, measured not promised: (1) a scope whose globs matched
zero members ever touched in N sessions while the lesson fired zero times -> curation surface
(stale scope); (2) a scope firing on >X distinct targets per session -> alert-fatigue surface
(a class that means everything means nothing). Both ride existing counters, no new pipeline.

## (c) THE 40-DAY QUESTION

V10. [CERTAIN] It is primarily a TRIGGER defect: the author wrote the lesson correctly, the
curation surface existed (it was found once the word "locks" was typed), and similarity
retrieval behaved exactly as designed — the only component that structurally could not see the
violation's class was the trigger, whose surface is one string. Cited: the brief's timeline;
M2.

V11. [DESIGN] Therefore (a)+(b) are sufficient, not merely necessary, under ONE condition: a
scope-declared lesson enters the fire decision from the TargetSet's scope_hints — class
membership is a first-class trigger input, similarity is the fallback for prose-only lessons.
If scope matching were itself routed through similarity, the 40-day class would merely move one
layer down.

V12. [UNCERTAIN] Structural limit this design must confess, not paper over: recall-at is
PRESENCE-triggered — it fires on what IS in the action, never on what is ABSENT (the corpus
lesson recall_at_cannot_fire_on_an_absence). The lock lesson's truest trigger is the absence of
a lock-check before editing a shared file; a TargetSet recovers the file class but cannot see
an action the agent never took. This half therefore claims the class-membership fix for (c)
and leaves the absence-triggered residue OUT of scope — named, not solved.

## (d) THE CROSS-HARNESS SEAM — one extractor, one contract, two translators

V13. [DESIGN] The ONE place: `core/recall/at_action.py` owns (1) the `TargetSet` contract,
(2) the shared file-reference extractor (`extract_file_targets(command) -> [str]`), and (3)
`recall_at(targets=...)`. The claude hook translates PreToolUse input into a TargetSet; the DSH
plugin translates `extractTarget` output into a TargetSet; BOTH call the same extractor for
command-derived paths. Per-adapter code is field naming only — divergence requires editing
shared code, which is the anti-drift property the brief demands.

V14. [DESIGN] Contract each adapter implements, stated so it can be pinned:
`TargetSet = {paths: list[str], commands: list[str], scope_hints: list[str]}`;
`extract_file_targets(command: str) -> list[str]` (M4's regex); `recall_at(targets)` merges by
source and renders through the existing funnel. Pins: one fixture command per harness shape,
asserting both adapters produce the SAME TargetSet for the SAME underlying action.

## FILE PLAN

- core/recall/at_action.py — TargetSet contract + extract_file_targets + recall_at(targets=).
- core/learning/learning_store.py — `scope` field passthrough on lesson records.
- agent_cli.py — `learn --scope` (author) + `learn --scope-edit` (curator) + the two
  scope-health counters surfaced in doctor.
- agent/harness/actions.py — recall_block/outcome_block accept the TargetSet and pass it
  through (the shared orchestration both adapters already call).
- agent/harness/hooks/claude_pretooluse.py + agent/harness/dsh_plugin/lib/index.js — the two
  translators (one each), pinned to produce identical TargetSets from paired fixtures.
- tests/test_t385_trigger.py — RED pins first: M1/M2 fixture commands must surface the hidden
  lessons through the new path; the two-adapters-same-TargetSet pin; the k-cap pin.

## RISKS (the two ways this makes recall WORSE)

R1. [DESIGN] Target-set explosion -> alert fatigue: every command becomes 5 queries and every
session a wall of injections, the funnel drowns, and the trigger is silenced by the reader.
Mitigations: the k-cap (V4), the merge-dedup by source, and the scope-fire counter (V9-2) as
the canary that the wall is being built.

R2. [DESIGN] Cross-member join evaporation under the multi-target surface: the V27 law held
per-member, but an adapter that builds the TargetSet from DIFFERENT fields at surface time and
resolve time (e.g. command-extracted paths at PreToolUse vs. tool-arg paths at PostToolUse)
silently reopens the evaporation I repaired last night, now multiplied by k. Mitigation: the
pairwise same-TargetSet iteration (V5) plus the two-adapters-same-TargetSet pin (V13) —
drift becomes a failing test, not a silent join.
