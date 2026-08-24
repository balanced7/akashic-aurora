# M1-BRIEF — t385-recall-trigger

## CHARTER
Daniil, 2026-08-24, choosing the target for the first blind fence run across TWO HARNESSES:
"Whats the highest leverage way we can run this blind to both, whats something that would be
a high leverage and benefit item we can put those two brilliant minds to" — then: "I like
recall trigger ^__^".

SCOPE FENCE, deliberate and non-negotiable: this fence is about the TRIGGER — whether recall
fires at all, and on what. It is NOT about the FUNNEL (surfaced vs fired vs helped, the ~4.5%
rate, the excluded_silent split between anti-repeat and self-echo). The funnel is reserved
terrain for Daniil's own walk and MUST NOT be analyzed, optimized, or front-run here. If your
half finds itself reasoning about ranking, relevance scoring, or suppression rules, you have
crossed the line — stop and say so in an UNCERTAIN verdict instead.

## INPUTS (measured 2026-08-24, receipts in-repo — not recalled, not assumed)
- **DEFECT 1, BATCH BLINDNESS.** A multi-file edit performed through a script normalizes to the
  WRAPPER, not the files. Measured: `recall_at(command='py - << PYEOF')` normalizes to
  `c:py - << pyeof` and returns **ZERO lessons**. The trigger keys on the command string, so any
  edit routed through a heredoc, `sed`, a python one-liner, or any multi-file wrapper is
  unadvised BY CONSTRUCTION.
- **DEFECT 2, CLASS-LESSONS UNREACHABLE FROM THEIR CLASS.** `shared_file_lock_handoff`
  ("a shared hot file may be under a peer's advisory lock, before editing: check locks") does NOT
  surface for `scripts/bifrost_runner_deepseek.py` (3 lessons returned, not among them), and does
  NOT surface for `scripts/bifrost_daemon.py` — **the file it was born on**. It is indexed by
  prose similarity, so a lesson governing a CLASS of file never reaches that class's members.
- **THE LIVE COST, and it is not hypothetical.** claude wrote `shared_file_lock_handoff` on
  2026-07-15 after committing a lock violation, then committed the IDENTICAL violation on
  2026-08-24 — 40 days later, in the same repo, with the lesson present and correct the whole
  time. It surfaced only when claude typed the word "locks" into a `learn` command: it fires when
  you write ABOUT the rule, never when you are about to break it.
- **TWO MORE INSTANCES, same week**: `timeline_windows_decode_failure_launders_git_as_empty` and
  `reentry_commit_total_is_a_hidden_40_row_cap` were both diagnosed by codex, recorded, and left
  unfixed until Sol re-found them independently on 2026-08-24. The corpus knew; the code did not.
- **THE ENGINE**: `core/recall/at_action.py` (`recall_at`, `normalize_target` ~line 884,
  `mark_impression`, `resolve_action_outcome`). The shared orchestration is
  `agent/harness/actions.py` (`recall_block`/`outcome_block`/`plan_block`, landed today).
- **THE TWO VANTAGE POINTS, which is why this fence is worth running across harnesses**:
  Heimdall reaches recall through the house ToolBox (37 typed tools, `recall_at` first-class).
  Rill reaches it through a cordis plugin that extracts `file_path`/`path`/`command` from DSH tool
  arguments (`agent/harness/dsh_plugin/lib/index.js::extractTarget`) — so Rill's harness inherits
  DEFECT 1 exactly, from the other side of the wall. You are not two reviewers of one system; you
  are two systems with the same wound.
- Filed as W183. Prior art in the same family: the parked N0-N7 recall-as-network roster and the
  T094 heuristics arc — cite if useful, do not re-derive.

## RULES OF ENGAGEMENT
Blind halves: do not read the other half before sealing yours. Every load-bearing claim carries a
line-start V-verdict — `V<n>. <claim> [CERTAIN|DESIGN|INFERRED|UNCERTAIN]` — the tag on the
verdict's FIRST PHYSICAL LINE (the seal checker requires it there; this cost three refused seals
in 24h). CERTAIN requires a `file:line` citation. UNCERTAIN is an honest verdict.
MEASURE, DO NOT SPECULATE: both of you can run the engine. A claim about what recall does or does
not surface should be a MEASUREMENT with the invocation shown, not an inference from reading code.
Write via `py agent_cli.py fence write t385-recall-trigger --slot half_a|half_b --by <agent>
--file <path>`, then `fence seal`.

## THE QUESTION
(a) **THE TRIGGER'S TRUE SURFACE.** What SHOULD a recall target be derived from? Today it is the
command string or a single path. A tool call that will write six files, a script that edits by
regex, a `git` invocation that touches a tree — each has a real target set the trigger never sees.
Name the derivation you would implement, where it lives so BOTH harnesses get it (the house hook
and the DSH plugin must not diverge), and what it costs per call.

(b) **SCOPED LESSONS.** Should a lesson be able to declare what it governs — a glob, a predicate,
a class ("any peer-lockable file", "any file under security/") — rather than relying on prose
similarity? If yes: the schema, who writes the scope (author? curator? inferred?), how it composes
with similarity ranking WITHOUT touching the funnel, and how a wrong scope is detected. If no: say
why, and how else a class-lesson reaches its class.

(c) **THE 40-DAY QUESTION.** A correct lesson sat unreachable for 40 days while its author
re-committed the exact violation. Is that a trigger defect, an authoring defect, a curation
defect, or a durable property of similarity-indexed memory? Your answer decides whether (a) and (b)
are sufficient or merely necessary.

(d) **THE CROSS-HARNESS SEAM.** Whatever you design must work identically for a typed-tool harness
and a shell-driven plugin harness. Name the ONE place it lives, and the contract each adapter
implements. If your design would make the two harnesses drift, it is wrong.

## OUTPUT CONTRACT
A numbered design (V-tagged, citations real), at least THREE MEASUREMENTS you ran yourself with the
invocation and result shown verbatim, a concrete file plan, the per-call cost of your derivation,
and a RISKS section naming the top two ways your design makes recall WORSE (a trigger that fires on
everything is a trigger nobody reads — the alert-fatigue law is in this corpus and applies).
Length: whatever the design needs, no padding.
