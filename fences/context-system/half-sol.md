# Context system house round — Sunshine half

Date: 2026-09-29  
Seat: Sunshine (`sol`)  
Parent: `cross-plane-join`

The sealed brief was absent from this deployment checkout, so I read it directly from the sealed commit object `1d320009a4905e133c5fb81e73f3ce965d3e45fc:fences/context-system/brief.md`. I did not read any peer half. Source inspection covered the current hook configurations and adapters plus this checkout's Toolbox; where the brief describes newer `origin/master` behavior (notably the `file_edit` capture at `toolbox.py:1436`), that sealed measurement takes precedence over this stale deployment branch.

## Slice verdicts

VA1. [CERTAIN] A1 Claude Code hook touch capture -- keep / evolves EventLog + session_focus / write-cost one fail-open capture plus ref-index writes per eligible tool event / read-cost zero until an indexed anchor query / false-if duplicate project+user hooks can emit two touches or a failed attempt is rendered as a successful touch
VA2. [CERTAIN] A2 runner Toolbox touch capture -- keep / evolves EventLog + ToolBox guarded execution surface / write-cost one bounded fail-open `touch` capture per read, write, exec, search or fetch and O(capped-targets) ref-index writes / read-cost one EventIndex by-ref lookup for an anchor, no tool-path scan / false-if capture latency or failure can delay/change the tool result, or search result fan-out is uncapped
VA3. [CERTAIN] A3 Codex and Cursor parity plus hook drift closure -- keep / evolves existing harness hook adapters and payload fixtures / write-cost one deduplicated touch per native hook event; shims add no event / read-cost no context-query cost beyond A2; fixture checks are CI-only / false-if user+repo hook copies double-record, a shim contains behavior, or an unpinned payload is treated as known
VA4. [DESIGN] A4 DSH plugin touch capture -- keep / evolves DSH plugin bridge + EventLog / write-cost one fail-open event per plugin-mediated tool action / read-cost same ref-index lookup as every harness / false-if DSH actions bypass the instrumented plugin path or seat/session attribution is inferred from another subject
VA5. [DESIGN] A5 sizing, retention and touch projection -- split / evolves EventLog + EventIndex + manifest bounds / write-cost first measure canonical/per-agent/index amplification, then add only a bounded derived touch projection if the firehose cannot carry it / read-cost benchmark last-N-by-ref at declared corpus sizes / false-if a convenience stream becomes a second authority or canonical chronology is evicted by telemetry before the projection exists
VA6. [DESIGN] A6 derived check-in -- split / evolves session_focus / write-cost cheap candidate inference on existing touch/fence/ask events plus one write only when confidence clears a stated floor / read-cost O(1) current focus plus provenance; correction is append-only / false-if a guess renders as declared focus, an old task survives supersession, or override cannot correct it
VA7. [CERTAIN] A7 target grammar -- keep / evolves existing recall target normalization + worktree/path scope policy / write-cost bounded parsing and canonicalization per touch / read-cost exact typed-anchor validation before resolver fan-out / false-if absolute checkout paths split one file into several identities, commands are parsed as shell semantics, or secrets become anchors
VB1. [CERTAIN] B1 typed anchor grammar -- keep / evolves `orient` typed-destination idiom + existing file/task/seat/session identifiers / write-cost none for reads; producers validate stored links once / read-cost one strict parse with loud ambiguity / false-if untyped text is guessed into an anchor or `file:line` loses revision/worktree context
VB2. [DESIGN] B2 per-plane resolvers -- split / evolves git, authorship ledger, EventIndex, lesson store, docs shelf, Eye, recall, locks and atom readers / write-cost no new writes beyond each source plane / read-cost independently capped resolver calls with per-row cost/blindness, composed concurrently / false-if one slow plane blocks L0/L1 or absence in a capped plane renders as nonexistence
VB3. [DESIGN] B3 cross-plane time scope -- keep / evolves EventLog chronology + git history + Eye `known_at` / write-cost no duplicate timeline store; preserve timestamps and coverage metadata at source / read-cost bounded merge and bucket over resolver outputs / false-if event time, knowledge time and observation time collapse into one timestamp or capped coverage looks complete
VB4. [CERTAIN] B4 path-to-organ map -- keep / evolves MAP, MODULE_INDEX and PHYSICS generated projections / write-cost generator/index refresh at commit time, not per tool call / read-cost prefix/rule lookup with projection SHA / false-if longest-prefix collisions choose silently or generated maps are stale without disclosure
VB5. [DESIGN] B5 stable cross-plane linkage -- split / evolves parent `cross-plane-join` contracts across existing ledgers / write-cost add explicit IDs at each producer boundary, one axis at a time / read-cost keyed joins first, text fallback only as labelled uncertain evidence / false-if a text match is promoted to identity or old rows without keys are silently assigned links
VC1. [CERTAIN] C1 blind eval set and metrics -- keep / evolves recall evaluation/bench plane / write-cost forty immutable cases plus explicit adjudicated answers / read-cost one reproducible benchmark run with recall@5, precision@3 and chrome share / false-if tuning sees test answers, corpus drift is unlabeled, or “right lesson” lacks an adjudicator
VC2. [DESIGN] C2 derive lesson file candidates from touches -- split / evolves learning records `files_affected` + touch index / write-cost query recent touches and store provenance-backed candidates; confirmation/correction is separate / read-cost indexed recent-touch lookup capped by time and count / false-if unrelated recent files become asserted lesson scope or no-touch is treated as no affected file
VC3. [DESIGN] C3 lessons into shelf engine -- keep / evolves existing lesson corpus and manuals-shelf SQLite FTS5/embedding/RRF engine / write-cost incremental text+embedding index update and migration receipts / read-cost one capped hybrid retrieval instead of `%TEMP%` JSON scan / false-if shelf becomes authority over canonical lessons, embedding version is unstated, or rollback loses records
VC4. [DESIGN] C4 `cast` shelf door -- keep / evolves existing shelf/recall query doors / write-cost none beyond C3 indexes / read-cost one bounded multi-shelf query with per-shelf limits and reasons / false-if “available” and “relevant” are conflated or expensive shelves ignore the chars/row cap
VC5. [DESIGN] C5 intent-aware recall-at -- keep / evolves recall-at + session/operator intent sources / write-cost one surfacing receipt per firing, deduplicated chrome per session / read-cost one capped index query assembled from declared intent fields / false-if inherited task text outweighs the current operator sentence or repeated chrome consumes the context budget
VC6. [DESIGN] C6 objective outcome credit and precision retirement -- split / evolves recall feedback/AAR + touch outcomes / write-cost first shadow correlations, later append credited/contra events; never mutate source lessons in place / read-cost periodic precision computation over explicit exposure→outcome windows / false-if temporal adjacency is called causality, non-action is graded failure, or retirement occurs without enough trials
VC7. [DESIGN] C7 promotion from lesson to refusal gate -- split / evolves guardrail/door rule registry + lesson evidence / write-cost shadow proposal, authority review, negative controls and versioned gate installation / read-cost O(1) compiled gate check plus a drillable evidence pointer / false-if objective credit alone grants policy authority or a promoted gate lacks operator ratification and rollback
VD1. [DESIGN] D1 Eye tool records -- merge / evolves Eye ingestion as a projection of canonical `touch` events, not a second per-tool write / write-cost asynchronous/batched projection from EventLog / read-cost existing Eye grammar and index lookup / false-if Eye and EventLog mint unrelated identities for one touch or projection lag is hidden
VD2. [DESIGN] D2 docs and research retrieval -- merge / evolves the C3 manuals-shelf engine, with Eye citations joining by source ID / write-cost incremental document index at commit/ingest time / read-cost one ranked shelf query with cited rows / false-if a second SQLite ranking engine drifts or private/internal documents cross their visibility boundary
VD3. [CERTAIN] D3 time-fog and `known_at` -- keep / evolves Eye epistemic/time fields across context renderers / write-cost producers preserve observation and source times / read-cost small coverage/fog aggregation per plane / false-if unknown coverage is rendered as zero or present knowledge is projected backward into an earlier time scope
VE1. [CERTAIN] E1 `context.scene.v1` -- keep / evolves `orient`/`present` renderer-neutral scene idiom / write-cost none per source event; schema/version fixtures only / read-cost stdlib validation over already-bounded resolver rows / false-if scene fields acquire authority not present in their receipts or renderer-specific markup enters the schema
VE2. [DESIGN] E2 `context` door and levels -- keep / evolves existing CLI/MCP door parity + typed-anchor readers / write-cost no write on reads except bounded observation metrics / read-cost L0/L1 fixed resolver budget, L2 receipts, L3 explicit raw expansion; question delegates to capped `cast` / false-if levels differ semantically rather than only in disclosed detail or MCP fields drift from CLI
VE3. [DESIGN] E3 renderers and UI surfaces -- split / evolves CLI, MCP, Bifrost UI and flightdeck renderers over one scene / write-cost no source writes; UI cache optional and derived / read-cost each renderer consumes one scene, never re-queries planes / false-if a renderer invents or drops fog/authority or UI failure wounds the context door
VE4. [CERTAIN] E4 Discord L0/L1 projection -- keep / evolves T385 fail-closed Discord routing + `context.scene.v1` / write-cost no extra context-plane write; one causal reply envelope with scene/version metadata / read-cost render one existing scene under a deterministic 1,900-character budget / false-if it re-queries Discord-side, leaks internal/raw touch data, widens a missing private route to global, or clipping removes fog
VE5. [DESIGN] E5 boot L0 touch lines -- split / evolves boot context + delta/raw-journal orientation / write-cost none at boot; last-touch already exists in index / read-cost one bounded self-subject L0 lookup after parity measurement / false-if another subject's touch becomes self-context, a capped miss is “never,” or old journal removal precedes parity
VF1. [CERTAIN] F1 slice pins and live-corpus probes -- keep / evolves existing payload fixtures, Redis-isolated tests and live-probe method / write-cost fixtures and receipts per slice / read-cost focused CI plus one declared live probe / false-if synthetic payloads substitute for captured shapes or tests touch prod
VF2. [CERTAIN] F2 cross-seat drills -- keep / evolves fence verification and receipt practice / write-cost one immutable drill receipt per slice / read-cost one fresh-seat reconstruction and structural scene comparison / false-if verifier inherits producer cache/context or compares prose instead of scene facts
VF3. [CERTAIN] F3 wiring/parity gates -- keep / evolves `check_wiring`, `check_door_parity` and guardrail ratchet / write-cost checker maintenance and generated docs / read-cost commit-time bounded scans / false-if new doors bypass MCP parity, ambient untracked debt is charged as causation, or exceptions lack reasons
VF4. [DESIGN] F4 privacy and cost manifest -- split / evolves internal EventLog visibility policy + PHYSICS/manifest bounds / write-cost redaction before capture and counters for bytes/refs/drops / read-cost `context --stats` aggregation separate from authorization filtering / false-if secrets/raw commands enter touches, public surfaces can query internal rows, or averages hide p95 amplification
VF5. [CERTAIN] F5 contract and method documentation -- keep / evolves docs architecture/method shelf / write-cost one versioned contract update per accepted wave / read-cost one canonical document and generated door links / false-if documentation describes later waves as live or duplicates authority held by schema/tests

## Missing slices

M1. **Touch outcome and correlation contract.** The proposed atom lacks `attempt_id`, outcome (`succeeded|failed|refused|interrupted|unknown`), duration, and causal/redrive identity. Without it, “touched” teaches that a refused or failed edit changed a file. This evolves EventLog event detail and existing hook outcome accounting; write cost is a few scalar fields, read cost is a filter.

M2. **Capture-time minimization/redaction.** Commands, search queries, URLs, absolute worktree paths and tool results can contain credentials or private operator text. Normalize targets first; never store raw command/result by default; apply existing secrets/scope policy before capture. This evolves hook/ToolBox boundary guards, not a new privacy store.

M3. **Cross-hook idempotency.** User and repo Codex hooks may both load; legacy and canonical Claude adapters may both be registered; runners may retry. Mint a stable event identity from harness event ID/session/tool-use ID and make duplicate capture idempotent. This evolves `codex_common.dedup_should_skip` and EventLog ingestion.

M4. **Historical compatibility and correction.** Read historical `file_edit` as a write touch without rewriting it; never synthesize missing reads. Add append-only correction links for wrong seat/task/target attribution. This evolves EventLog refs and pointer-honesty rules.

M5. **Telemetry-loss honesty.** Capture remains fail-open for the tool call, but failures increment a bounded local/drop counter and render fog in `context --stats`; otherwise “no touch” means both “none happened” and “instrument was down.” This evolves event capture BoundaryOutcome and doctor/manifest telemetry.

M6. **Surface authorization matrix.** Define which touch fields survive CLI/MCP/UI/Discord/flightdeck projection. Internal raw touch rows are not automatically safe because the anchor path is safe. This evolves ACL/capability checks and renderer policy.

## The first two I would build

1. **C1, the blind eval set.** It is the only way to know whether later knowledge/index work improves retrieval rather than merely changing it. Its cost is small, and every C3–C7 tuning decision otherwise proceeds without a number.
2. **A5, the measured touch write/read budget and retention choice.** A1/A2 can produce thousands of events per session. Measure canonical writes, ref-index amplification, p95 capture latency, retention horizon and last-N read cost before turning on fleet-wide hooks. This prevents the missing atom from evicting the chronicle it is meant to join.

## The one I refuse

I refuse **C7 as automatic promotion from objective credit directly into an enforcing refusal**. Correlation between lesson exposure and later touches is evidence, not authority. I will build the shadow proposal, evidence packet, negative controls, operator ratification, versioned gate and rollback. I will not let a telemetry score silently acquire the power to block Daniel or a seat.

---

# Sunshine lane deliverable

## A2 — Runner Toolbox diff plan

### Governing choice

All new runner actions emit `kind="touch"`. Historical `file_edit` rows remain immutable and the B2 resolver reads them as legacy `action=write`. Do not dual-write `file_edit` and `touch` indefinitely: that makes every runner write look like two actions. The existing `file:<repo-relative>` ref shape remains canonical.

### 1. Add one fail-open capture helper beside the existing write capture

In `core/comm/toolbox.py`, extract the brief-measured `file_edit` capture at current `origin/master` around line 1436 into a private helper, conceptually:

```python
_capture_touch(
    *, action, tool, targets, outcome,
    started_at=None, duration_ms=None,
    detail=None,
)
```

It uses the existing EventLog singleton/door and calls:

```python
capture(
    "touch",
    summary,
    agent_id=self.agent_id or "unknown",
    session_id=<subject session/incarnation if actually present>,
    refs=[<typed refs from A7/B1>],
    track=<declared/derived focus id or None>,
    detail={
        "schema": "touch.v1",
        "harness": "runner-toolbox",
        "tool": tool,
        "action": action,
        "targets": targets,
        "cwd": <repo-relative/worktree identity, never absolute host path>,
        "worktree": <stable checkout identity>,
        "task": <focus plus declared|derived provenance>,
        "outcome": outcome,
        "duration_ms": duration_ms,
    },
)
```

Rules:

- blanket fail-open around telemetry, but a capture/drop counter records failure;
- do not open a new Redis/EventLog client per call;
- normalize and cap targets before capture; store `targets_total` and `targets_truncated`;
- never store raw command, stdout/stderr, file contents, secret-bearing query strings or absolute host paths;
- do not guess session/task/seat when absent; render unknown;
- capture the action outcome, including refusal/interruption, so attempted work is not represented as successful mutation.

### 2. Instrument read surfaces after their result is known

Add one helper call to the return/finally boundary of:

- `read_file` → `action=read`, one `file:<rel>` target plus optional typed line span;
- `list_directory` → `action=read`, one `dir:<rel>/` target;
- `find_files` → `action=search`, scope directory anchor and a sanitized pattern descriptor; result paths are capped targets, not unbounded refs;
- `search_files` → `action=search`, scope anchor plus capped matched files; regex stays out of refs and is redacted/minimized in detail;
- `git_log` with file path → read of the file anchor; without a path → repository anchor;
- `git_diff`/`git_show`/`git_status` → `action=read` against typed commit/repository anchors.

A read error still emits one touch with `outcome=failed`; it must not claim a successful read. Event capture happens after filesystem/tool authorization, so an out-of-scope refusal has an attempted target and `outcome=refused`, never secret content.

### 3. Instrument write surfaces without double counting

- Convert the existing `file_edit` event emission in `edit_file` to `touch.v1`, `action=write`, `tool=edit_file`, same `file:<rel>` ref.
- Ensure `write_file` emits the identical kind/shape with `tool=write_file`.
- One tool call produces one touch even if it changes many lines.
- Preserve old `file_edit` reads through B2 compatibility; do not rewrite history.

### 4. Instrument exec and search/fetch

`run_command`:

- start monotonic timing after authorization;
- record `action=exec`, tool family (`pytest`, agent-cli-read, mirror, play, confirmed-generic), exit/refusal/timeout outcome and duration;
- targets come only from A7's bounded path-token extractor and recognized verb/commit/task arguments;
- never persist the raw shell command or output;
- telemetry runs after subprocess completion and cannot alter returned stdout, exit annotation or timeout behavior.

`web_search`:

- record `action=search` (and `fetch` only if a later tool actually retrieves a URL);
- target is a typed query anchor only if the approved grammar provides a privacy-safe representation; otherwise record tool/action with zero targets and a redaction reason;
- returned URLs may become capped `url:` targets after credential/query stripping.

The same policy later covers dedicated web/search doors through one capture helper rather than bespoke events.

### 5. Pins

- exact `touch.v1` shape and `file:<rel>` ref parity with historical runner writes;
- read, write, exec, search success/failure/refusal/timeout;
- capture exception leaves tool output byte-identical and increments loss telemetry;
- raw command, secret, absolute checkout path and file contents absent from the record;
- capped multi-target search reports total/truncation;
- one write call is one touch, not `file_edit` plus `touch`;
- historical `file_edit` resolves as one legacy write touch;
- worktree variants of one repository path canonicalize per A7's ruling.

### Costs

Write: one EventLog capture per eligible Toolbox call, currently canonical + per-agent stream plus O(capped refs) index work; A5 must set the cap and prove p95 latency. Read: no new cost on ordinary tools; context lookup is one by-ref query plus bounded legacy `file_edit` compatibility.

## A3 — Codex, Cursor and hook-tree parity

### Live files and shims

- **Claude live implementation:** `agent/harness/hooks/claude_posttooluse.py`, invoked directly by `.claude/settings.json`. Keep it canonical.
- **Claude drifted copy:** `scripts/hooks/claude_posttooluse.py`. Replace the full copy with the same stable shim shape already used by Codex: put repo root on `sys.path`, import canonical `main`, exit with `main()`. A shim contains no policy and therefore cannot drift eight lines again.
- **Codex live implementation:** `agent/harness/hooks/codex_posttooluse.py`.
- **Codex stable entrypoint:** `.codex/hooks.json` invokes `scripts/hooks/codex_posttooluse.py`; that file is already a thin shim to the canonical adapter. Keep this arrangement because user/repo Codex configuration needs a stable script path.
- **Cursor implementation:** `agent/harness/hooks/cursor_posttooluse.py`; keep its payload-truth skip until live fixtures exist, then emit the same touch helper output.

### Diff sequence

1. Put harness-neutral target normalization, redaction and EventLog emission in one shared helper under the existing harness/EventLog boundary; adapters translate native payloads into it. This is code reuse, not a new data plane.
2. Claude canonical adapter calls touch capture after it has determined tool, scope and outcome. Keep its transcript-derived failure synthesis for recall credit, but give a native action one stable `attempt_id` so synthesized failure and later success do not collapse into one touch.
3. Coordinate `.claude/settings.json` with A1: expand PostToolUse coverage from `Bash|Edit|Write|NotebookEdit` to the actually supported read/search/fetch tools and include `PowerShell`, which the adapter already names but the project matcher currently omits. Register the same canonical adapter for `PostToolUseFailure` where supported; transcript recovery remains the compatibility path.
4. Codex canonical adapter emits a touch after `dedup_should_skip`, `capture_payload`, scope resolution and `is_success`. Preserve current direct non-zero-command outcome handling. `apply_patch` emits capped normalized file targets; Bash uses the shared bounded extractor.
5. Cursor adapter emits only after a captured payload fixture proves the field mapping. Until then its context scene renders the harness touch plane as unverified/absent, not zero.
6. All adapters use the same stable event identity (`harness + session + native tool_use/event id`). Existing Codex duplicate suppression is extended to the touch write. Claude gets equivalent user+repo duplicate protection.
7. Replace `scripts/hooks/claude_posttooluse.py` with a shim and pin source size/import target; add a checker that behavior may live only in `agent/harness/hooks/*`, while `scripts/hooks/*` files are entrypoint shims.

### Parity fixture

One semantically identical edit, read, search and command fixture per harness must project to the same normalized `touch.v1` fields (`seat`, `session`, `tool`, `action`, `targets`, `outcome`, refs), allowing only declared native-payload provenance differences. A parity test compares the records, not adapter prose.

### Costs

Write: one deduplicated EventLog touch per native event; failure reconstruction may add an attempted-failure touch only when it represents a distinct attempt ID. Read: zero during tool use; CI fixture/parity reads only, followed by the same EventIndex lookup at context time.

## E4 — Discord L0/L1 projection

### Rule

Discord renders an already-built `context.scene.v1`; it performs no plane queries. The renderer is pure and deterministic:

```text
render_context_discord(scene, level=0|1) -> DiscordReply
```

`DiscordReply` is a projection envelope, not a new context authority:

```json
{
  "schema": "context.discord.reply.v1",
  "scene_schema": "context.scene.v1",
  "scene_id": "...",
  "anchor": "file:arsenal/practice.py",
  "level": 1,
  "content": "...<=1900 chars...",
  "allowed_mentions": {"parse": []},
  "meta": {
    "context_scene_id": "...",
    "context_level": 1,
    "context_anchor": "file:arsenal/practice.py"
  }
}
```

### L0

One line, optimized for an answer inside an existing conversation:

```text
Context · `file:arsenal/practice.py` · organ arsenal/practice · last touch Sunshine/write 18m · span 09-14…09-29 · 5/7 planes · fog 2 · scene ctx_…
```

Every compact claim must exist in the scene. `5/7 planes` means returned/attempted, not completeness of reality.

### L1

Plain Discord text, not an embed-only contract:

```text
**Context · `file:arsenal/practice.py`**  `L1` · scene `ctx_…`
**Organ** arsenal / practice  · projection `MAP@<sha>`
**Last touch** Sunshine · write · 18m · task `T411` · receipt `event:…`
**Git** 4 commits · last 09-29 · authorship claude · receipt `commit:…`
**Knowledge** 0 direct lessons · 1 related surfacing · receipt `recall:…`
**Time** 09-14 … 09-29 · coverage git=full, touches=retained-window
**Fog** Eye has no tool rows before D1; session focus absent; touch retention capped
`context file:arsenal/practice.py --level 2` for receipts
```

Rules:

- hard budget 1,900 characters, leaving room for continuity stamps;
- deterministic section drop order under pressure: related activity → extra knowledge rows → extra git rows; **never drop anchor, scene ID, span, or fog**;
- fold whole sections; never raw-string clip a receipt or UTF-8 sequence;
- escape markdown/control characters and disable mentions;
- render stable refs, never local absolute paths, raw commands, secrets or internal touch details;
- L2/L3 are not pushed into Discord; the card gives the scene ID and governed drill command;
- if the source scene is unauthorized for the Discord speaker, refuse or render only an authorized L0—never fetch a “safer” substitute silently.

### Discord routing and causal settlement

Use the T385 route already built:

- reply to the exact originating Discord seat/channel through its registered private lane;
- stamp `answers=<source Bifrost request id>` and `context_scene_id`;
- preserve `source=discord`, operator/guest/root authority and subject seat;
- missing private route is a loud journaled failure and never widens to global Discord;
- idempotency key includes source Discord message ID + scene ID + level, so a pump retry cannot post the card twice;
- rendering failure does not settle the request; a successfully posted card does.

### E4 pins and drill

- golden L0/L1 fixtures from one `context.scene.v1` produce identical claims;
- 1,900-character worst case folds sections and retains fog;
- mentions disabled; markdown/path/URL escaping pinned;
- no absolute path, raw command or secret-bearing query appears;
- missing webhook/private lane fails closed with zero global posts;
- pump retry posts once;
- reply carries exact `answers` and scene ID;
- Discord readback in the originating channel matches the rendered content byte-for-byte.

Write cost: one normal causal reply/journal event; no additional touch or context write. Read cost: O(scene rows) pure rendering, bounded to L1; no Redis/git/Eye/recall query from the Discord projection.
