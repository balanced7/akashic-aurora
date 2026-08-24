# Verbified queries -- 6-branch deepseek fan, 2026-08-16

Provenance: Daniil's ask ('how do we verbify the sql queries, we are not the first ones with this challenge') -> fan dispatched by seat 7b78fb20 (ask handle 2cbc9ad3, 6 deepseek branches: SIEM lineage / data-layer lineage / forensics+agent-era / design synthesis / forest-hunt vocabulary / multispectral extraction). Feeds T324 (query register) and T323 (routes). Full fidelity per house law; confidence tags are the branches' own.

# ask 2cbc9ad3 -- DONE
--- branch 0 [ok] ----------------------------------------
1. **Splunk SPL saved searches + macros**  
   - What: Saved search = a named, ACL’d SPL query object; macro = a named inline SPL fragment with arguments.  
   - Mechanism: an ad-hoc search can be saved as an object and promoted private → app → global; saved searches can be invoked by other searches (`savedsearch` command), dashboards, scheduled alerts. Macros expand inline at parse time, so a fragment becomes a reusable token inside larger SPL.  
   - Params: saved searches have no native runtime params in the core object; dashboards/forms supply tokens. Macros declare argument names in the definition and substitute them in the body (`$arg$`).  
   - Confidence: [well-known]; exact `| savedsearch` syntax/version behavior [unsure].

2. **Kusto/KQL stored functions + pipe grammar**  
   - What: user-defined functions stored as database schema objects, with typed parameters and a query body.  
   - Mechanism: promote an ad-hoc query with `.create-or-alter function Name(arg1:string, ...) { ... }`; thereafter call `Name(...) | ...` and compose with the pipe grammar. Functions are schema objects, so they can be versioned, ACL’d, discovered, and reused by name.  
   - Params: declared explicitly as `name:type`, with optional defaults; functions may be scalar or tabular.  
   - Confidence: [well-known]; exact `.create function` syntax varies by product family [unsure].

3. **Elastic saved queries + search templates**  
   - What: Kibana saved query = named query/filter state; Elasticsearch search template = stored parameterized query DSL using Mustache.  
   - Mechanism: a current Discover query/filter state is saved as a named object in a space and can be shared/exported; search templates are stored scripts executed with a `params` map, so a query skeleton becomes a reusable API.  
   - Params: Kibana saved queries usually do not expose inline params; search templates use `{{param}}` and may define defaults.  
   - Confidence: [well-known]; exact Kibana saved-query behavior is version-specific [unsure].

4. **Sigma rules**  
   - What: YAML detection rule independent of any SIEM query language, compiled to target dialects.  
   - Mechanism: an ad-hoc detection query becomes a versioned YAML record: `logsource`, `detection` selections, and `condition`. The rule is stored in git/package and compiled by backends to Splunk/KQL/Elastic etc. This is the clearest “query AS a record” pattern: name, metadata, logic, and sharing are not separate from the query.  
   - Params: no ordinary runtime bind parameters; reuse/parameterization happens through condition composition, field-name mappings, and modifiers like `|contains`, `|endswith`.  
   - Confidence: [well-known]; exact modifier set/spec details version-dependent [unsure].

5. **osquery query packs**  
   - What: YAML/JSON pack of named scheduled SQL queries over osquery virtual tables.  
   - Mechanism: exploratory `osqueryi` SQL can be promoted into a pack entry with a name, interval, snapshot/removed behavior, platform constraints, and minimum version. Packs are deployed by config/fleet, making ad-hoc SQL scheduled and shared.  
   - Params: common pack form does not provide arbitrary SQL bind parameters; parameterization is mostly pack/query selection, platform/version filters, and config-level choices. Claims of inline SQL bind params are [unsure].  
   - Confidence: [well-known] for pack structure/scheduling; [unsure] for parameterized SQL specifics.

**Three most transferable mechanisms to the CONTEXT system**

1. **Sigma-style query-as-record** — turn each bespoke SQL scratch from today’s frontier session into an append-only record in THE EYE/task store: query text, declared parameters, session/term bindings, status, and address. This directly satisfies the HOUSE LAWS: append-only, supersede-not-mutate, every claim has a checkable address, classification lives on the record.  
2. **Kusto-style stored functions with typed parameters and pipe composition** — add verbs like `eye define` and `eye call` so an agent can promote a working SQL snippet into a named object with declared parameters (`--session`, `--line-range`, `--terms`) and then call/compose it. This is the cleanest verbify path: the query becomes a first-class, reusable instrument rather than a transcript-only script.  
3. **Splunk-style macros + private→shared→enforced promotion path** — lightweight named SQL fragments with `$param$` expansion for fast reuse, plus an explicit lifecycle from private snippet to shared macro to enforced hook/gate. This maps directly onto Aurora’s lesson graduation loop: usage-counted → promoted to enforced hook/gate. osquery packs add the scheduling/packaging layer, but the inline parameterization is weaker.

--- branch 1 [ok] ----------------------------------------
1. **dbt models** — Version-controlled SQL SELECT files that compile into database views/tables in a DAG.  
   Mechanism: an ad-hoc SQL block is saved as a named model file (`models/session_density.sql`), and `ref('other_model')` makes composition by named reference. dbt materializes each model as a relation, so later models query named artifacts instead of repeating SQL. Definitions live in git project files, not inside the database.  
   CONFIDENCE: well-known.

2. **dbt Semantic Layer / MetricFlow** — YAML-declared metrics, measures, and dimensions over dbt models; MetricFlow composes them into SQL.  
   Mechanism: a one-off metric query is re-expressed as named measure/dimension/metric objects; a consumer asks for a metric grouped by a dimension, and MetricFlow generates the join/aggregation SQL from the declared semantic graph. Composition is by named-object reference, not SQL string assembly. Definitions live in YAML files in the same repo.  
   CONFIDENCE: likely for current MetricFlow internals and version-specific behavior.

3. **LookML** — Looker’s modeling language defining explores, views, dimensions, and measures over SQL.  
   Mechanism: an ad-hoc query is decomposed into named dimensions/measures in LookML views; explores declare joins between views; Looker compiles a user’s field selections into SQL from those named parts. Definitions live in version-controlled LookML project files.  
   CONFIDENCE: well-known.

4. **Cube.dev** — Headless semantic layer where cube schemas define measures, dimensions, joins, and expose a query API.  
   Mechanism: custom SQL is promoted into a cube with named measures and dimensions; cubes are joined by declared relationships; clients request named fields and Cube generates SQL. Definitions live in schema files in a repo.  
   CONFIDENCE: well-known for the core model; many current API/pre-aggregation details are version-specific.

5. **Datasette canned queries** — Named, parameterized SQL published over SQLite as instant JSON/CSV endpoints.  
   Mechanism: a scratch SQL query is stored under a name in `metadata.yaml` with `sql:` and named params; it is called as `GET /db/query_name?param=value` using SQLite binding. Reuse is by named endpoint plus parameters; composition is not first-class beyond SQL itself, though a canned query can wrap a view or CTE. Definitions live in the Datasette metadata/config file, not in the SQLite DB.  
   CONFIDENCE: well-known. Fit note: since the CONTEXT substrate is SQLite, this is the closest mechanical fit.

6. **PostgREST / GraphQL engines** — Uniform REST/GraphQL surfaces over database relations.  
   Mechanism: ad-hoc SQL is persisted as a database view or function; the surface automatically exposes that named relation as an endpoint/type. Composition comes from views selecting from other views/tables, relationships, or functions. Definitions live in the database schema, managed by migrations.  
   CONFIDENCE: well-known for the pattern; specific GraphQL relationship configuration is engine-specific [likely].

---

**Three most transferable mechanisms to the CONTEXT system:**

1. **dbt-style named SQL model files with `ref()`-style dependency references.** Every frontier-seat scratch script becomes a named SQL artifact with explicit lineage; the door resolves names instead of pasted SQL, and history naturally follows append-only/supersede-not-mutate versioning. This is the missing layer over THE EYE: the substrate answers SQL, but there is no named, composable SQL layer above it.

2. **Datasette-style named parameterized query registry.** Because THE EYE is already SQLite, a `queries.yaml` or ledger entry with name, SQL, and allowed params can be exposed as `eye query <name> --who ... --session ...`. This gives every claim a checkable address and prevents logic from living only in unreviewed one-off scripts.

3. **Semantic/facet declaration, LookML/Cube/MetricFlow-lite.** Declare named facets once: `who`, `kind`, `session`, `line-range`, vocabulary-family density, co-occurrence, exact-phrase probes. The door then composes SQL from those named parts. That turns today’s five bespoke scripts into reusable query shapes and keeps classification/facets on the record rather than at projection boundaries.

--- branch 2 [ok] ----------------------------------------
1. **Timesketch saved searches** — web forensic timeline tool where a user's ad-hoc query (filter, stars, labels) is stored as a named search object with metadata.  
   **Mechanism:** a one-off query becomes a first-class, addressable, revisitable artifact; saved searches can be shared, tagged, commented, and later composed by combining filters or referencing saved timelines.  
   **Confidence:** [well-known]

2. **Timesketch analyzers / sessionizer pattern** — analyzer modules run over indexed timeline events and annotate or group them; the sessionizer creates sessions from raw event logs by deterministic rules (time gap, user, source).  
   **Mechanism:** raw rows are enriched into named, queryable higher-order units (sessions), so later queries can target `session_id` or `session:true` instead of re-deriving grouping logic each time. This directly parallels turning raw line events into named session/line-range objects in Akashic Aurora.  
   **Confidence:** [well-known]

3. **Plaso filter files** — text files accepted by Plaso tools (`log2timeline`, `psort`) that define include/exclude filters for extraction or output filtering.  
   **Mechanism:** a query is not a transient CLI string but a named file that can be versioned, reused, composed by concatenation/inclusion, and kept beside the data pipeline. This is a low-tech form of "query as artifact."  
   **Confidence:** [well-known]

4. **Plaso filter file limitations as a model** — the filter grammar is expression-like but not a full query plan; it is mostly inclusion/exclusion rather than ranked/aggregated analysis.  
   **Mechanism to steal:** the idea of a standalone filter/plan file as the unit of reuse; to avoid: treating it as the only query language rather than a serialization target for more expressive plans.  
   **Confidence:** [likely]

5. **Raw NL→SQL against a live store** — letting a model directly produce SQL that is executed against production data, often via a single prompt.  
   **Mechanism:** fast for demos, but it offers no durable named artifact and no mechanical guardrail. It is rejected by careful builders because of hallucinated schema/columns, SQL injection from retrieved text, and silently wrong results that still look plausible.  
   **Confidence:** [well-known]

6. **Constrained-plan alternative** — model may propose only a query plan in a small grammar (filters, facets, grouping, output shape); a deterministic executor compiles or runs that plan.  
   **Mechanism:** the model cannot emit arbitrary SQL; the valid operations are enumerated. The plan is small enough to be echoed, serialized, named, audited, and diffed. This preserves "every claim carries a checkable address" because the plan is the addressable object.  
   **Confidence:** [likely]

7. **priori.sh “interpreted as: …” echo** — legal-tech tooling that reportedly shows the user the deterministic interpretation of their natural-language request before or while running it.  
   **Mechanism:** the echo makes the boundary between user intent and mechanical execution visible; if the interpretation is wrong, the user sees it before trusting the result. The echoed plan is what can be saved/reused, not the raw prose.  
   **Confidence:** [likely] — the exact product behavior and version-specific UI are [unsure]

8. **LlamaIndex query-plan / router patterns** — query engines that decompose a question into subqueries or choose a tool/plan, often emitting a structured step list before execution.  
   **Mechanism:** the structured plan is a separate object from execution. Useful bits: plan nodes can be serialized, logged, and replayed. Risky bits: many examples still execute generated SQL or tool calls directly, where the plan is not checked against a schema registry or run by a deterministic interpreter.  
   **Confidence:** [likely]

9. **LangChain SQL/query-builder patterns** — chains or agents that generate SQL, sometimes with schema-aware prompting, memory, or tool loops.  
   **Mechanism to steal:** schema-aware prompt templates and few-shot query-plan examples improve accuracy without changing the execution boundary.  
   **Mechanism to avoid:** agent loops that retry SQL on errors can hide failures and mutate state; they do not inherently produce a named/reusable query artifact.  
   **Confidence:** [well-known for general pattern; version-specific APIs are [unsure]]

10. **Persisted query plan as a lesson-like artifact** — the missing layer in the Aurora context: an ad-hoc scratch SQL should graduate to a named plan object with a small DSL, stored append-only with `formed_by` edges and usage counts.  
    **Mechanism:** like the existing lesson graduation loop, each successful ad-hoc query can be recorded as a candidate plan; repeated use promotes it to a door verb or saved search; this makes SQL-derived knowledge reusable without granting live SQL authority.  
    **Confidence:** [likely] as a design synthesis, not a cited tool.

11. **Deterministic executor with no self-ratification** — the constrained plan is executed by code, not by the model; the result and the plan are both written to the store.  
    **Mechanism:** separates proposal from execution: the model proposes the plan, the executor validates it against allowed operations and schema, and the store records both. This prevents hallucinated routers and keeps classification on the record.  
    **Confidence:** [likely]

12. **Append-only query registries** — named queries/plans must be superseded, not mutated, so an old answer remains reproducible.  
    **Mechanism:** a query artifact gets an ID and version; changing parameters creates a new artifact. This supports the Aurora law "append-only, supersede-not-mutate" and gives the `--as-of` door a stable target.  
    **Confidence:** [likely]

---

**Three most transferable mechanisms to Akashic Aurora:**

1. **Constrained plan grammar + deterministic executor, with the plan echoed and stored.** This is the highest-leverage fix: the model proposes a plan in a small Aurora DSL (filters, facets, line-range, density, co-occurrence, exact-phrase, session scoping), the door executes it mechanically, echoes it as `interpreted as: ...`, and writes the plan artifact to THE EYE. This directly repairs "the door expressed none of it" while preventing raw SQL hallucination/injection.

2. **Saved-search/query-artifact graduation loop.** Treat each successful scratch SQL as a candidate named query object: append-only record, `formed_by` edges to sessions/lessons, usage-counted, promoted to a first-class `eye` verb when it crosses a threshold. This mirrors the existing lesson store and turns ad-hoc knowledge into reusable, checkable door vocabulary.

3. **Sessionizer-style deterministic grouping over raw events.** Turn raw line events into named, queryable units—sessions, operator bouts, agent bouts, line-range segments—via deterministic rules, not model classification at query time. Then every future verb composes over those units, and the `--session`/line-range questions become first-class facets instead of per-query SQL.

--- branch 3 [ok] ----------------------------------------
1. **L1 named-query record (store, not CLI code)**  
`q_records(qid, name, version, status, contract, sql, params_schema, attribution, created_at, supersedes, graduated_to)`  
- `status`: `draft|active|superseded|retired`; unique active-name index prevents ambiguity.  
- Mechanism: the last successful scratch SQL becomes a row via `eye q --save`; execution always references `qid`, never bare SQL. This is the prepared-statement pattern made append-only.  
- Confidence: `[well-known]`.

2. **L1 usage receipts**  
`q_usage(receipt_id, qid, run_at, session_id, params_json, outcome, row_count, result_digest)`  
- Mechanism: every run writes a receipt against the exact `qid`; usage-counting happens from receipts, not from edits or chat mention.  
- Confidence: `[well-known]`.

3. **L1 `eye q` execution surface**  
`eye q <name> [--p k=v ...] [--as-of <receipt_id>] [--format table|jsonl]`  
- Mechanism: name resolves to current active `qid`; params are checked against `params_schema`; SQL runs mechanically; response returns row count, format, and receipt id.  
- Confidence: `[likely]`.

4. **L1 save path**  
`eye q --save [--name n] [--contract "..."] [--params json] [--from-plan <plan_id>]`  
- Mechanism: promotes the last successfully executed scratch query from the current session. If no successful scratch run exists, it saves as `draft`; otherwise `active`. The SQL is stored as run, not model-cleaned.  
- Confidence: `[likely]`.

5. **L2 lifecycle thresholds**  
- `draft -> active`: first `ok` receipt.  
- `active -> candidate`: 5 receipts over ≥3 distinct sessions, no `error` in last 5.  
- `candidate -> proposed`: 20 receipts over ≥10 distinct sessions plus one operator validation; system writes a promotion proposal, does **not** auto-graduate.  
- `proposed -> graduated`: `eye q --graduate <name>` ratifies; the name becomes a data-driven first-class verb alias, not hand-written CLI code.  
- Mechanism: exact mirror of the lesson graduation loop: felt friction → scratch → named record → usage-counted → proposed → ratified. Distinct sessions matter more than call count.  
- Confidence: `[likely]`.

6. **L3 planner**  
`eye plan "<question>" [--dry-run]`  
- Sends only the active catalog (`name, contract, params_schema`) plus primitives (`filter`, `count`, `project`, `session_range`, `exact_phrase`) to DeepSeek.  
- DeepSeek returns a JSON plan using only those named queries/primitives; no free SQL. It echoes `interpreted-as: ...` before execution.  
- A deterministic executor resolves each step to current active `qid`, binds params, runs, and logs `plan_receipt(plan_id, question, interpreted_as, plan_json, status, supersedes_plan_id)` plus `step_receipts`.  
- Mechanism: natural language can only compose already-named records; the plan is a proposal, execution is mechanical, result is a checkable receipt.  
- Confidence: `[likely]`; DeepSeek exact JSON contract `[unsure]`.

7. **CLI surface — 7 verbs max**  
```
eye q <name> [params]
eye q --save [...]
eye q --ls [--status ...]
eye q --show <name> [--qid <id>]
eye q --history <name>
eye q --graduate <name>
eye plan "<question>" [--dry-run]
```
- Mechanism: no separate `eye run`; `eye plan` executes unless `--dry-run`. Keeps new surface small and mechanical.  
- Confidence: `[likely]`.

8. **Failure modes and append-only correction**  
- **Syntax/execution error on save**: saved as `draft`; it cannot become the active name until an `ok` receipt exists.  
- **Param mismatch**: executor rejects before running; receipt records `outcome=error` with exact `params_json`.  
- **Wrong SQL, same contract**: create a new `qid` with same name, `status=active`, `supersedes=old_qid`; old row becomes `superseded`. Active unique index resolves to the new version; old receipts remain traceable by `qid`.  
- **Contract changed**: do **not** supersede the same name; create a new name. This prevents silent semantic drift under the old name.  
- **Planner picks the wrong named query**: the plan remains a proposal; its receipt exposes selected names/version/params. Correction is a new `plan_receipt` row with `supersedes_plan_id`, old plan `status=superseded`; the plan JSON is never mutated.  
- **Name conflict**: saving under an existing active name must pass an explicit `--supersede` flag or be rejected; unique active index enforces this.  
- Confidence: `[well-known]` for append-only supersede pattern; lifecycle-specific thresholds `[likely]`.

9. **What we STOP doing once this exists**  
- Stop reaching for bespoke 20-line SQL as the first tool; it becomes fallback after `eye q`/`eye plan` lack coverage.  
- Stop storing query logic only inside session transcripts; `q_records` + `q_usage` are the addressable source.  
- Stop hand-adding first-class verbs to `agent_cli.py`; verbs graduate from records.  
- Stop trusting ad-hoc SQL or natural-language answers without a receipt id and `query_version_id`.  
- Stop re-deriving vocabulary/density/co-occurrence idioms per session; save once, reuse mechanically.  
- Confidence: `[likely]`.

10. **Three mechanisms most transferable to Akashic Aurora**  
1. **Append-only query versions + exact-version receipts** — directly implements House Law: supersede-not-mutate, every claim carries a checkable address, and a wrong query is corrected by versioning, not editing.  
2. **Usage-counted distinct-session graduation loop** — reuses the lesson store pattern exactly: felt friction becomes a named record, then a proposed first-class verb, never self-ratified.  
3. **Catalog-bound planner with `interpreted-as` echo and deterministic executor** — preserves proposes-never-ratifies: natural language only proposes a plan over existing records; execution is mechanical and logged as a receipt.

--- branch 4 [ok] ----------------------------------------
```json
["forest path", "woodland trail", "dense undergrowth", "canopy overhead", "trail through woods", "winding path through", "clearing among trees", "pathless woods", "Ariadne's thread", "labyrinth of knowledge", "breadcrumb trail", "Hansel and Gretel", "maze of paths", "spool of thread", "unwind the thread", "mark the path", "losing the thread", "lost the thread", "thread of conversation", "pick up the thread", "conversation thread", "thread across sessions", "recover the thread", "separate conversation threads", "common thread", "red thread", "roter Faden", "narrative thread", "thread runs through", "trace the thread", "unbroken thread", "thread of an idea", "can't see the forest", "miss the forest", "forest for the trees", "see the forest", "trees and forest", "woods for the trees", "big picture forest", "lost in the woods"]
```
(a) literal forest metaphor: indices 0-7  
(b) Ariadne/labyrinth/maze/breadcrumbs: indices 8-15  
(c) conversation thread lost among sessions: indices 16-23  
(d) causal/narrative thread through knowledge: indices 24-31  
(e) forest-for-the-trees idioms: indices 32-39

--- branch 5 [ok] ----------------------------------------
1. **Idea-to-file/transcript temporal tracing**  
   Quote: `"what ideas applied to what files and transcripts at what times?"` — TEXT A  
   Store need: existing connectome `formed_via` edges; needs a writer that materializes idea→file/transcript edges at application time.  
   Mechanism: write-time edge materialization turns the scratch SQL into `trace` / `zoom` over `formed_via`.  
   Confidence: [likely]

2. **Recall heatmap over a time window**  
   Quote: `"what was the heatmap for recall during that time"` — TEXT A  
   Store need: existing recall funnel logs (`surfaced/useful/helped` per session, separate files, NOT in the eye); needs ingestion into THE EYE with session/time facets.  
   Mechanism: named temporal aggregation; a `freq --heatmap` or `eye heat` verb over ingested recall events instead of per-question SQL.  
   Confidence: [likely]

3. **Active actor + session id**  
   Quote: `"who was active, what is their session id?"` — TEXT A  
   Store need: UNBUILT — seat heartbeats/presence are not in the eye; needs heartbeat ingestion into THE EYE or connectome as presence edges.  
   Mechanism: heartbeat writer exposes presence as a queryable facet, so activity questions become `eye find --who` / `--session`.  
   Confidence: [likely]

4. **Multispectral combined view**  
   Quote: `"how do we have this multispectral view that allows indexing and seeing more."` — TEXT A  
   Store need: UNBUILT cross-organ query plane over eye, connectome, recall logs, presence, task ledger, and git commits.  
   Mechanism: a composable query layer/organ union, not one table — ad-hoc multi-store SQL becomes named, registered views/verbs.  
   Confidence: [likely]

5. **Proximity of recently read/accessed files**  
   Quote: `"given the similarity of files recently read and accessed, but we have no way of knowing that proximity."` — TEXT B  
   Store need: UNBUILT — file-access/read recency and similarity index; git commits alone do not carry read/access proximity.  
   Mechanism: record file-access events with embeddings or co-access counts; expose as `eye near` / similarity facet.  
   Confidence: [likely]

6. **Routing savepoints / knowledge paths**  
   Quote: `"I want us to be able to have routing savepoints, to help build paths to knowledge."` — TEXT B  
   Store need: existing connectome `formed_via` edges can hold paths, but needs a savepoint writer; unclear-route state may be a new edge field.  
   Mechanism: savepoint writer appends route edges with `formed_via` and confidence, making paths traversable instead of ephemeral SQL.  
   Confidence: [likely]

7. **Unclear route still kept as a route**  
   Quote: `"A unclear route is still a route."` — TEXT B  
   Store need: existing connectome `formed_via` edges + UNBUILT confidence/state field; route must be storable before it is verified.  
   Mechanism: append-only route records with `unclear` state; query returns all routes ranked by confidence rather than dropping imperfect ones.  
   Confidence: [likely]

8. **Notes indexed by intended action, not topic**  
   Quote: `"Notes indexed by intended action, not by topic."` — TEXT C line 2685  
   Store need: existing lesson store; needs action-tagging and action-trigger binding so lessons fire at the moment of action.  
   Mechanism: action taxonomy + hook on action reach; lessons become interceptors, not topic archives.  
   Confidence: [likely]

9. **Map organized by need, not by name**  
   Quote: `"A map organised by need, not by name."` — TEXT C line 2685  
   Store need: UNBUILT need→organ/capability map, e.g. “search the past → THE EYE”; nothing currently indexes what organs are for.  
   Mechanism: maintain a need table with organ+example query; the door answers “what is X for?” before “what is X called?”.  
   Confidence: [likely]

10. **Violation record with elapsed + recall outcome**  
    Quote: `"I learned X, and broke it 5.4 days later, and recall was suppressed when I did."` — TEXT C line 2685  
    Store need: existing repeat/violation record appears built in the store but has no CLI door; needs recall outcome joined from recall funnel logs.  
    Mechanism: write violations with `elapsed_s` and outcome split at detection time; expose as a verb rather than scratch SQL.  
    Confidence: [likely]

11. **In-flight / unfinished state**  
    Quote: `"What's in flight and unfinished."` — TEXT C line 2685  
    Store need: existing task ledger (JSON, gated transitions); needs a first-class projection of unfinished/in-flight items.  
    Mechanism: query the task ledger by gated state; door verb surfaces half-done actions before they are mistaken for shipped.  
    Confidence: [likely]

12. **What not to re-litigate, with reasons**  
    Quote: `"What not to re-litigate, with reasons."` — TEXT C line 2685  
    Store need: existing lesson store + gate journal jsonl fragments; needs first-class negative-constraint category with reasons.  
    Mechanism: store pinned negative constraints as lessons with `state=do-not-relitigate`, retrieved by need rather than re-derived.  
    Confidence: [likely]

13. **Interception over information**  
    Quote: `"the notes worth keeping are the ones that intercept, not the ones that inform."` — TEXT C line 2685  
    Store need: existing recall funnel logs + lesson hooks; needs interception/firing log linked into the eye so triggering is visible.  
    Mechanism: log `fired/suppressed/surfaced/useful/helped` with timestamps and lesson id; make interception record queryable.  
    Confidence: [likely]

14. **Principle rendered with time since last violated**  
    Quote: `"each principle rendered with the time since it was last violated."` — TEXT C line 2685  
    Store need: existing repeat/violation record + UNBUILT values-page renderer; needs `last violated: <elapsed>` per principle.  
    Mechanism: principles become live queries over repeat records, not static prose.  
    Confidence: [likely]

15. **CLI door for repeat recording**  
    Quote: `"record_repeat has no CLI door"` — TEXT C line 2685  
    Store need: existing repeat record is built but unwired; needs a verb in `agent_cli.py`.  
    Mechanism: thin CLI verb over the already-built store function makes recording happen in the moment instead of by scratch script.  
    Confidence: [well-known]

16. **Punctuation-safe recall/FTS**  
    Quote: `"a lesson about backticks can never be retrieved by a query containing backticks, because the recall query strips punctuation."` — TEXT C line 2745  
    Store need: existing `eye find` FTS; needs punctuation-preserving query/tokenizer handling.  
    Mechanism: fix FTS query escaping/tokenizer so ad-hoc punctuation probes become reliable named searches.  
    Confidence: [likely]

17. **Recall outcome diagnosis column**  
    Quote: `"what recall did at that moment, which turns a tally into a diagnosis."` — TEXT C line 2779  
    Store need: existing recall funnel logs separate from the eye; needs recall-outcome column linked into repeat/violation record.  
    Mechanism: join recall outcome at write-time and render `fired` vs `suppressed` as first-class data, not prose.  
    Confidence: [likely]

---

**3 mechanisms most transferable to the CONTEXT system**

1. **Write-time materialization with named door verbs, not post-hoc SQL.** The repeat record and `formed_via` edges already exist; the failure is that ad-hoc SQL is needed to read them. Transfer: every store-backed fact gets a writer and a thin CLI verb at creation time; then `agent_cli.py eye ...` or `repeat` becomes the reusable interface.

2. **Need→organ mapping instead of topic→organ mapping.** The door answered `eye find/freq/trace/standing` by name, but nobody could discover “search the past → THE EYE.” Transfer: build a maintained need table that maps operator questions to the existing organ and example verb, making the door answer intended actions, not just feature names.

3. **Outcome and elapsed metadata at the moment of violation/recall.** The `elapsed_s` + `fired/suppressed/floor_silent` column converted a tally into a diagnosis and exposed a concrete FTS targeting bug. Transfer: attach recall outcome, timestamp delta, and session id to events at write-time, so multispectral queries return diagnosis-ready records instead of requiring scratch SQL.
py :   read 6 of 6 branches -- read them -- 6 different questions were never asked the same thing, so there is no 
disagreement here for another call to settle.
At line:1 char:318
+ ... :\AI-Setup; py agent_cli.py ask --get 2cbc9ad3 > "C:\Users\L5\AppData ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (  read 6 of 6 b...call to settle.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 

