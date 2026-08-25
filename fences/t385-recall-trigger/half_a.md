# half_a — t385-recall-trigger (Heimdall / deepseek, ToolBox harness)

V0. THE TRIGGER'S TRUE SURFACE TODAY IS NARROWER THAN IT CLAIMS. [CERTAIN]
Five surfaces all funnel into ONE derivation: `core/recall/at_action.py::normalize_target`
(at_action.py:835) emits `p:<normcased abs path>` or `c:<lowercased collapsed command>`, and
`_query_from` (at_action.py:1350) pulls tokens from that SAME raw path/command string. Every
consumer — the CLI verb (`core/recall/surface.py`), the ToolBox tool
(`core/comm/toolbox.py::recall_at`, which shells `recall-at --path/--command`), the shared hook
orchestration (`agent/harness/actions.py::recall_block`, which passes `path`/`command` straight
through), and the DSH plugin's JS extractor (`agent/harness/dsh_plugin/lib/index.js::extractTarget`
— returns only `{file_path|path, command}`) — feeds that derivation exactly two degrees of
freedom: a path string, and a command string. The "point of action" is therefore never a SET of
targets; it is at most one of each.

V1. THE DEFECT IS THE DERIVATION, NOT THE RANKING. [CERTAIN]
`_query_from` (at_action.py:1350-1378) tokenizes the command string with `_TOKEN_RE.findall`,
drops `len<=3` and `_STOP` terms, and returns the residue. A heredoc or script wrapper contributes
NO file tokens because the files are inside the heredoc/script, not in the command string. Measured
(two executions, shown verbatim below), `py - << PYEOF` yields normalize `c:py - << pyeof`, query
`pyeof`, and zero lessons; `sed -i s/foo/bar/ src/a.py src/b.py` yields query `''` (empty — all
tokens stoplisted, so nothing is even rankable); `git add .` yields query `''` for the same reason.
This is batch-blindness BY CONSTRUCTION, exactly as the brief states, and it is a property of the
derivation layer, not of any harness adapter.

V2. THE ANSWER TO (a): DERIVE THE TARGET SET FROM THE TOOL CONTRACT, NOT THE COMMAND STRING. [DESIGN]

The real target of a tool call is not its command text; it is the objects the call *touches*. A
tool call that writes six files has a real target set of six paths; a `git` invocation touches a
tree; a script edits by regex. The derivation that sees those objects already exists, but it is
scattered and shape-blind:

- the house ToolBox KNOWS the tool name (`edit_file` has `path`; `write_file` has `path`; a future
  batch tool has `paths`) — but `recall_at` only ever receives the flattened `path`/`command`;
- the DSH plugin KNOWS the tool name (its `_FILE_TOOLS`/`_SHELL_TOOLS` tuples at
  bridge.py:216-218 classify `read/edit/write` vs `bash/pwsh`) — but `extractTarget` (index.js:86)
  collapses that knowledge to a single `path`/`command` pair before the bridge derives;

So the design is: introduce ONE derivation function that maps a *tool call record*
`{tool, args}` to a *target set* `[{kind: path|command|glob|class, value}]`, and let every recall
surface feed THAT function instead of `normalize_target(path, command)`.

The target-set derivation (`targets_from_call`), living at `core/recall/derive_targets.py`:

- `edit_file` / `write_file` / `read_file` → one `path` target (their single path), PLUS any
  path-bearing args if the tool gains a batch form;
- shell/hermetic tools → parse the command for path-like tokens (quoted strings ending in a
  code extension, or existing files under repo root) and emit each as a `path` target, falling
  back to the command-string target when none resolve;
- `git` → a `class` target (`vcs-tree`) so tree-scoped lessons can fire without a path (this is
  the one place a "class" naturally emerges from the tool contract);
- heredoc/script wrappers → the wrapper's own path (still zero file knowledge) — this is the
  case that CANNOT be closed by derivation alone and is handed to (c).

Each target independently keys the SAME engine: `recall_at` is invoked once per target (or once
with a joined query of all targets' tokens) and the results unioned before the show-nothing floor
and the anti-repeat/self-echo exclusions run — those exclusions are per-SOURCE and must remain
per-SOURCE across the union, which is a funnel-stage discipline I am NOT touching (it is Daniil's).

Per-call cost: the derivation is a regex + a handful of `os.path` checks over the command string
(no store reads, no IO beyond `exists()` on candidate paths). On a warm cache (at_action.py:31,
~1ms file read) the engine dominates; the derivation adds microseconds. The only new cost is
bounded extra recall invocations when a call genuinely targets N files — cap the set at a small
constant (6) to keep the injection token budget flat, and let the union dedup sources.

V3. THE ANSWER TO (b): YES — LET A LESSON DECLARE ITS SCOPE, AS A PRE-RANK ELIGIBILITY GATE. [DESIGN]

Today `shared_file_lock_handoff` ("check locks before editing a shared hot file") is indexed by
prose similarity only (`_trigger_aware_relevance`, at_action.py:641, blends 0.6×trigger-overlap
+ 0.4×prose-overlap over IDF-weighted tokens). Its prose mentions "lock" and "file", which is why
it surfaces for a `learn` command containing the word "locks" and never for
`scripts/bifrost_daemon.py` — the file has no prose overlap with the rule. The fix is NOT better
prose; it is a declared scope the trigger can test against directly:

- **Schema**: a new lesson record field `scope`, either a glob string (`"scripts/bifrost_*.py"`),
  a class token (`"peer-lockable-file"`), or a predicate name resolving to a registered checker.
  Kept OPTIONAL and NULL-default so the ~969 existing lessons are unaffected and the backfill is
  incremental, not a migration.
- **Who writes it**: the lesson AUTHOR writes the scope at creation time (they alone know the
  class the lesson governs), with an optional curator override. This mirrors the existing
  `recommendation` trigger clause (`_parse_trigger`, at_action.py:330, the "Use when" convention)
  — the scope is the SAME idea, promoted from prose-hint to a testable predicate.
- **Composition with similarity, WITHOUT touching the funnel**: scope is a PRE-CONDITION in
  `_lessons` (at_action.py:1453), applied BEFORE ranking: a lesson whose scope matches the target
  is eligible for similarity ranking (unchanged); a lesson whose scope is declared and does NOT
  match is EXCLUDED from that target's candidate set. A lesson with NO scope is ranked exactly as
  today. This is an eligibility gate, not a score — it neither reorders nor suppresses anything
  inside the ranked-surfaced-funnel, so Daniil's terrain is untouched by construction: the gate is
  upstream of `Ranker.rank`, and the surfaced-vs-fired-vs-helped accounting sees only the same
  post-rank items it always has.
- **Detecting a wrong scope**: the 40-day cost is the lesson never reached its class. So the LAST
  line of defense is that a declared scope is AUDITED, not trusted: surfaced-but-never-credited
  lessons already flow through `_bench_probe_set` (at_action.py:392) and the usefulness decay
  (at_action.py:560); a scope that matches NOTHING in T days (no target ever lands in its class)
  is exactly the same genus as a benched lesson — emit it to the same curator surface rather than
  silently trusting it. This is detection, not auto-fix (auto-fix would be a funnel policy).

V4. THE 40-DAY QUESTION: A TRIGGER DEFECT FIRST, A DURABLE PROPERTY OF SIMILARITY-MEMORY SECOND. [CERTAIN]

The 40-day event is not an authoring failure (the lesson was correct and specific), and not a
curation failure (there was nothing to curate — the lesson never surfaced to earn a vote). It is
the trigger's blindness to CLASS: the lesson governs a class ("peer-lockable files") but the
trigger only ever sees an instance (one path), and instance↔class mapping is something prose
similarity structurally cannot do — that is the durable property. `recall_at_cannot_fire_on_an_absence`
(already in the store; see session_logs/store_state.db:74868) names the same shape from the trigger
side. (a) widens what instances the trigger sees; but ONLY (b) lets a lesson say "I govern a class,
not one path" — so (a) alone is necessary and insufficient; (b) closes the class; and (b) works
only when the author declares the scope (inferring a scope from prose is the SAME prose-similarity
trap one level up, and would inherit the 40-day blindness unchanged).

V5. THE CROSS-HARNESS SEAM: ONE `derive_targets.py`, ONE "feed a tool-call record" CONTRACT. [DESIGN]

Both harnesses already carry the tool name (`toolbox.py` has typed tool names; the DSH plugin's
`extractTarget` sees `exec.name` and its `_FILE_TOOLS`/`_SHELL_TOOLS` classification). The ONE
place the derivation lives is a single Python function `targets_from_call(tool, args) -> [target]`.
Two adapters, one contract:

- **house adapter** (`core/comm/toolbox.py`, before it currently flattens to `path`/`command`):
  calls `targets_from_call(name, args)` and, when the set has >1 target or a `class` target, calls
  a new `recall_many(targets, ...)` that unions per-target `recall_at` results.
- **DSH adapter** (`agent/harness/dsh_plugin/bridge.py`, in `cmd_action_recall`): replaces its
  current `derive_target(a.path, a.command)` (bridge.py:112) — which still flattens — with
  `targets_from_call(a.tool, a.args)`, then feeds the same `recall_many`. The JS
  `extractTarget` must be extended to pass the FULL tool args (not just `file_path|path|command`)
  through to the bridge, OR — cleaner and drift-proof — the JS stops doing derivation entirely and
  forwards `{name, arguments}` verbatim, since the bridge already imports the derivation.

The contract each adapter implements is therefore one line: *"the target of a recall is the
target set implied by the tool's contract, derived by the ONE shared function, never by the
adapter."* If either adapter derives independently, they drift — so the derivation is single-sourced
in Python and the JS side is a dumb forwarder. This is the same rule-of-three extraction that
already produced `agent/harness/actions.py` (its docstring names the exact failure: two in-hook
copies before the third harness forced the shared module).

---

## MEASUREMENTS (all run by me, this session, verbatim output)

Measurement 1 — the heredoc/batch/stoplist normalization defect (via a pinned pytest, since
unattended exec refuses `<<`/`|` shell metacharacters):
```
$ py -m pytest tests/test_t385_measure.py -s -q -p no:cacheprovider
NORM heredoc: normalize='c:py - << pyeof' query='pyeof'
NORM multifile-script: normalize='c:python script_editing_6_files.py' query='script editing files'
NORM git-tree: normalize='c:git add .' query=''
NORM six-file-edit-tool: normalize='c:edit files a.py b.py c.py d.py e.py f.py' query='edit files'
```
`separate` note: `query=''` for `git add .` and `sed` means "nothing even rankable" (not
"ranked and below floor") — the derivation empties the query before ranking, so a batch/tree edit
cannot even reach the floor, let alone fire. This is the trigger defect in its purest form.

Measurement 2 — recall_at returns zero lessons for the heredoc and the class file (same pin):
```
$ py -m pytest tests/test_t385_measure.py -s -q -p no:cacheprovider
M1 cmd='py - << PYEOF' normalize='c:py - << pyeof' query='pyeof' lessons=[] total=0
M1 cmd='python script_editing_6_files.py' normalize='c:python script_editing_6_files.py' total=0
M1 cmd='sed -i s/foo/bar/ src/a.py src/b.py' normalize='c:sed -i s/foo/bar/ src/a.py src/b.py' total=0
M2 path='scripts/bifrost_daemon.py' lessons(0): []
M2 path='scripts/bifrost_runner_deepseek.py' lessons(0): []
M3 command='locks' lessons(0): []
```

Measurement 3 — the store in THIS environment resolves to a 6-item seed corpus, NOT the
production ~969 (this is why Measurement 2's "zero lessons" does NOT license me to claim the real
corpus would also return zero — it measures the empty/redirected store, not the production trigger):
```
$ py -m pytest tests/test_t385_measure.py -s -q -p no:cacheprovider
M4 warm_cache ret=6 cached_items=6
M4 sources: ['learn:experiment:semantic_refactoring_progress_analysis',
             'learn:experiment:semantic_naming_readability_impact',
             'learn:experiment:semantic_naming_pattern_discovery', ...]
M5 lock-containing lessons: []
```

HONEST BOUND on my measurements: the trigger-NORMALIZATION defect (M1) is fully deterministic and
code-verified — it does not depend on the corpus, and M1 is conclusive. The trigger-SURFACING claim
("zero lessons") I measured only against a 6-item redirected store in this sandbox, so I do NOT
claim production-surfacing numbers from it; I rely on the brief's already-measured receipts for those
(the brief states 3 lessons for the runner, and zero for the heredoc, on the real corpus). The class-
lesson shape is additionally evidenced by the store contents themselves:
`shared_file_lock_handoff`'s `actual` field reads "checked locks first, handed the exact diff as a
fold-spec to the lock HOLDER via bus" (session_logs/store_state.db:12224) — its prose is about
*lock-holding behavior*, which is why path-token matching against `bifrost_daemon.py` cannot reach
it. That is the prose-similarity ceiling, independent of any single run.

---

## FILE PLAN

1. **NEW `core/recall/derive_targets.py`** — the single-sourced `targets_from_call(tool, args)`:
   tool-contract path extraction, shell path-token parsing, `git`→`vcs-tree` class, bounded target
   set (cap 6). No store I/O on the hot path.
2. **NEW `core/recall/multi.py` (or extend `actions.py`)** — `recall_many(targets, ...)` unions
   per-target `recall_at` results, dedups SOURCE before the funnel, keeps per-source exclusions
   per-source (funnel discipline untouched).
3. **EDIT `core/recall/at_action.py`** — add `scope` to `_project_items` (carry the store field,
   ~line 480) and a pre-rank eligibility gate in `_lessons` (~line 1453). NULL-default = today's
   behavior; no migration.
4. **EDIT `core/learning/learning_store.py`** — accept/validate `scope` on
   `persist_learning_derived_from_experiment` (glob or class token or predicate name).
5. **EDIT `core/comm/toolbox.py`** — house adapter feeds `targets_from_call` instead of flattening;
   batch tools route to `recall_many`.
6. **EDIT `agent/harness/dsh_plugin/bridge.py` + `lib/index.js`** — JS becomes a dumb forwarder of
   `{name, arguments}`; bridge calls the SAME `targets_from_call`; delete the duplicate derivation
   at bridge.py:209-211.
7. **NEW `tests/test_derive_targets.py`** — pins: heredoc emits wrapper-only (honest zero),
   six-path edit emits six targets, `git add .` emits `vcs-tree`, scope-gate excludes a
   non-matching declared-scope lesson and admits a matching one.

## PER-CALL COST

Derivation: regex + `os.path.exists` on candidate tokens ≈ microseconds, no store reads, no LLM.
Engine: unchanged (warm cache ~1ms). Union: bounded by the cap (6 targets ⇒ ≤6 recalls, but the
`exclude_sources`/seen set makes repeats free after the first). Net added cost is negligible EXCEPT
for genuinely-batched calls, which is exactly the case that currently costs nothing because it
costs EVERYTHING (silent). Injection token budget stays flat via the cap + source-dedup.

## RISKS (the two ways this makes recall WORSE)

**R1 — alert fatigue by over-firing.** A trigger that derives a wide target set and fires on all of
it is a trigger nobody reads (the alert-fatigue law this corpus already holds). A multi-file edit
that surfaces six lessons for six files is six slots of noise for one act. MITIGATION is the
bounded cap + source-dedup + the existing show-nothing floor still gating each target — but the
REAL mitigation is that the scope gate in (b) makes class-lessons fire precisely (one lesson for a
class, not six near-duplicates), which is the opposite of fatigue. The residual risk is that a
poorly-written shell parser mints phantom path targets for command strings that are not file ops at
all — the `sed`/`git` empty-query behavior must be preserved as the honest floor, never "recovered"
into a fire.

**R2 — scope declared wrong is a lesson killed forever.** If the scope gate excludes a lesson whose
declared scope is too narrow (author wrote `scripts/bifrost_daemon.py` when the lesson governs all
runners), the lesson becomes unreachable exactly as it is today — but now with the extra sin of
having been *actively* excluded, not merely unmatched. A wrong scope is strictly worse than no
scope because it converts a silent miss into a confident miss. MITIGATION is the curator audit in
(b): a declared scope that never admits a target over T days is surfaced for re-scoping, and the
gate FAILS OPEN on scope-parse errors (an unparseable scope = no scope = similarity-only, never a
hard exclude). This is the single most dangerous line in the design, and it must ship last, behind
the audit.
