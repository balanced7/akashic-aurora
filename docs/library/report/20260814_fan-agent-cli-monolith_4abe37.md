---
akashic_id: art_20260814_fan-agent-cli-monolith_4abe37
akashic_sha: 223e572ad1a0
schema_version: 1
status: current
type: report
date: 2026-08-14
title: fan-agent-cli-monolith
gist: "# FAN: the agent_cli monolith, five lenses (2026-08-14, claude/Vandor) Ask handle 6991655b. Pack = a measured AST digest of agent_cli.py (8,"
visibility: fleet
body_type: markdown
seats: []
category: [memory]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-14T09:29:00"
updated: "2026-08-14T09:29:00"
---
<!-- GENERATED PROJECTION of art_20260814_fan-agent-cli-monolith_4abe37 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# fan-agent-cli-monolith

# FAN: the agent_cli monolith, five lenses (2026-08-14, claude/Vandor)

Ask handle 6991655b. Pack = a measured AST digest of agent_cli.py (8,336 lines, 147 top-level
functions, 87 cmd_* verbs). Preserved in full BEFORE synthesis, per house rule.

NOTE: a first attempt (handle c286d6dd) used --prompt-file + --lens and all five branches
correctly ABSTAINED -- the pack does not ride into a lens branch. Lesson filed as
prompt_file_plus_lens_does_not_compose_and_the_fan_abstained_honestly.

# ask 6991655b -- DONE
--- branch 0 [ok] ----------------------------------------
**Strongest claim:** the first slice is not a verb. It is the 1,250-line `build_parser` — 15% of the file and the only real coupling holding 87 verbs together. Until `build_parser` becomes a declarative command registry, extracting even the largest self-contained verb (`cmd_eye`, 246 lines) only moves a leaf while leaving the actual monolith in place.

## Actual modules here

1. **`cli/registry.py`** — `build_parser` becomes a table-driven command registry + generic parser builder. This is the real backbone.
2. **`cli/clip.py`** — `_clip` (6 lines, 16 callers). Highest fan-in seam in the file; it is a service, not a helper.
3. **`cli/services/intake.py`** — `_intake` (39 lines, 3 callers: `cmd_handoff`, `cmd_learn`, `cmd_note`).
4. **`cli/services/notes.py`** — `project_notes` (21 lines, 3 callers: `cmd_note`, `cmd_notes`, `cmd_wrap`).
5. **`cli/services/capture.py`** — `_capture_decode` (14 lines, `cmd_bench`, `cmd_capture`).
6. **`cli/services/family.py`** — `_family_gauge_render` (11 lines, `cmd_doctor`, `cmd_injections`).
7. **`cli/verbs/boot.py`** — the boot/orientation vertical: `cmd_boot` (240) + `_orientation_header` (259) + `_continuity_drift` (47) + `_boot_world_line` (45) + `_boot_you_line` (42) + `_stance_block` (33) + `_boot_standpoint_line` (28) + `_boot_save_line` (26) + `_boot_siblings_line` (22) + `_transport_line` (21) = **~763 lines**.
8. **`cli/verbs/ask.py`** — `cmd_ask` (396) + `load_fan_prompts` (55) + `_ask_payload` (34) = **485 lines**.
9. **`cli/verbs/notes.py`** — `cmd_note`, `cmd_notes`, `cmd_wrap`, `_wrap_route`, `_suggest_resident`, `project_notes`.
10. **Domain leaf modules** for the 65 no-helper verbs, grouped by naming family: `bifrost`, `recall`, `doctor/ops`, etc. Do **not** create 87 one-function modules.

## Extraction order

1. **RED first:** add a door-parity checker that enumerates all 87 verbs across CLI/MCP/ToolBox and fails on `built != wired`.
2. **First slice:** extract `build_parser` into `cli/registry.py`.
3. **Extract `_clip`** to `cli/clip.py` — tiny, but with 16 callers it must move before the verb clusters that depend on it.
4. **Extract the small shared services:** `_intake`, `project_notes`, `_capture_decode`, `_family_gauge_render`.
5. **Extract `boot`** vertical — largest coherent cluster, privately coupled, and only depends on `_clip` [ASSUMED from the caller list].
6. **Extract `ask`** vertical — 485 lines, already self-contained.
7. **Extract `notes/wrap`** after `_clip`, `_intake`, and `project_notes` are available.
8. **Sweep the 65 self-contained verbs** in size-ranked, domain-grouped batches. They become low-risk after the registry exists.

## First slice precisely

Create **`cli/registry.py`** with:

- a `CommandSpec` dataclass: `name`, `aliases`, `help`, `handler` as a lazy import path, `surfaces` bitmask for CLI/MCP/ToolBox, and parser args spec.
- a `COMMAND_SPECS` table.
- a generic `build_parser` loop that consumes `COMMAND_SPECS`.

Move **no command body**. Keep all 87 `cmd_*` functions in `agent_cli.py`. For one commit, leave `agent_cli.build_parser` as a re-export so the slice is independently revertible: if green fails, delete `cli/registry.py` and restore the old 1,250-line function. Green means the parser output and all 87 registered verbs match exactly.

--- branch 1 [ok] ----------------------------------------
**Strongest claim:** the seam you are missing is a shared **terminal/record/event renderer**. The digest does not show independence; it shows an unfactored presentation path. `_clip` is the only high-fan output helper (6 lines, 16 callers), while 65 of 87 verbs (2,953 lines) call no local helper at all. If display were already a seam, the 3+ list would contain something like `_render_table`, `_render_event`, or `_render_records`. It does not.

**What should be shared:** a small `presentation`/`views` layer with primitives like:

- `render_records(records, ...)`
- `render_event(event, ...)`
- `render_bus_message(msg, ...)`
- `_clip` as the terminal truncation primitive it already is

**What points at it:**

- `_print_events` (21 lines) is used only by `cmd_events`.
- `_read_bus_message` (20 lines) is used only by `cmd_doc`.
- `_transport_line` (21 lines) is used only by `cmd_boot`.
- The `_boot_*_line` family is all private to `_orientation_header`, i.e. line/block rendering is currently verb-private.
- The largest no-helper verbs are overwhelmingly read/report/query verbs: `cmd_eye` (246), `cmd_resident` (192), `cmd_recall_curate` (164), `cmd_sift` (150), `cmd_mailbox` (135), `cmd_bifrost_send` (104). [ASSUMED] These likely each format bus/event/recall rows by hand because there is no shared renderer.

**Cheapest probe:** use the AST already available, but this time extract `ast.Constant(str)` nodes and normalized source-line hashes from the 65 no-helper `cmd_*` bodies. Normalize numbers, hex, timestamps, UUIDs, ANSI, and whitespace. Then write one RED test:

> No non-trivial normalized line or string constant appears in 3+ `cmd_*` bodies.

If that fails with clusters spanning `cmd_mailbox`, `cmd_bifrost_*`, `cmd_events`, `cmd_recall_*`, the duplication is confirmed and the missing seam is real.

**Kill condition:** if no cluster of 3+ verbs shares 10+ normalized non-trivial lines/strings, and the large no-helper verbs have low pairwise source similarity, the duplication hypothesis is wrong.

--- branch 2 [ok] ----------------------------------------
**Strongest claim: your 87 verbs are not 87 systems — they are 87 viewports over one shared store. The digest already shows the real data hubs are the shared helpers, not the verbs: `_clip` (6 lines, 16 callers), `_intake` (39 lines, 3 callers), `project_notes` (21 lines, 3 callers), `_capture_decode` (14 lines, 3 callers). Route architecture by those interest sets, not by verb count.**

**What transfers from game-engine thinking:**

- **LoL/RTS interest management is the direct fit.** Each verb should declare its read/write interest set against the shared store, and CLI/MCP/ToolBox should be replication surfaces over the same interest declaration. The failure mode here is numeric: **65 of 87 verbs (2,953 lines) call no local helper**, meaning they likely touch the store through ad-hoc access paths rather than a declared relevance set [ASSUMED]. That is like every client reading the whole sim instead of receiving only its relevant entities.

- **Doom Eternal’s hot/cold split transfers as module boundary, not memory layout.** The cold path is `build_parser` at **1,250 lines, called by only 3**, plus large presentation verbs like `cmd_ask` (396), `cmd_story` (268), `cmd_eye` (246). The top 10 functions are **3,386 lines — about 40.6% of the file**. That is cold orchestration/presentation; the hot path is the shared store mutation surface represented by `_clip`, `_intake`, `project_notes`.

**Where the analogy breaks:**

- **Frame-budget as performance does not transfer.** A CLI is not a 16ms loop. `build_parser` being 1,250 lines is ugly, but it is startup/cold and not a per-frame cache miss problem. Per-command cost is store I/O, not iteration over homogeneous entity arrays.

- **Doom’s data-oriented memory layout does not transfer.** Struct-of-arrays, contiguous hot arrays, branch-free hot loops assume high-frequency homogeneous entity updates. Your verbs are low-frequency, heterogeneous one-shot commands over a shared store.

**Transferable mechanism:** interest management + hot/cold separation as architectural rules.  
**Explicit does-not-transfer:** DOD memory layout and frame-budget latency engineering as performance targets here.

--- branch 3 [ok] ----------------------------------------
Strongest claim: `build_parser` is not “the biggest helper to shrink” — it is the CLI composition root and the only single inventory/routing table for all 87 verbs. Extracting it first severs the wiring edge between each `cmd_*` implementation and its CLI name/options/callback, and it creates the exact `built != wired` failure the house forbids.

What the one 1,250-line argparse definition couples:

1. **All 87 verb symbols to their CLI surface.** Every subparser must bind a name, flags, defaults, and a callback like `set_defaults(func=cmd_eye)`. That is the only place where the 87 `cmd_*` implementations are enumerated as a routing table. The digest shows 87 `cmd_*` verbs and 65 of them are fully self-contained (2,953 lines total) — but none of those 65 are wired to the CLI without `build_parser`.

2. **The door-parity contract.** Because every verb must exist on CLI, MCP, and ToolBox, the parser’s 87 subparser entries are the CLI half of that classification/inventory. If the parser is pulled out as a separate module, the definitions remain in `agent_cli.py` while the registration table lives elsewhere. A new 88th `cmd_*` can be counted by AST as a verb but absent from the parser module; nothing fails at import time because the parser simply has no subparser for it.

3. **Shared argument shape.** Across 87 verbs, common flags/defaults are almost certainly [ASSUMED] expressed once as parent parsers or helper argument blocks. A naive verb-by-verb split after extracting the parser first would fragment those shared CLI data shapes, so the resulting modules no longer share one design language.

Specific failure mode of extracting it first:

A standalone `parser.py` must import the 87 `cmd_*` functions from the still-monolithic `agent_cli.py` to populate its subparsers. So after extraction, the parser is still coupled to every implementation, and the monolith is still ~7,000 lines of command bodies. You have moved the root out before moving any leaves. Then any change to a verb requires editing two physical sources of truth: the implementation and the registration table. Miss one registration and the checker sees a `cmd_*` built but not wired — a RED pin on the first slice, with no runtime failure until a user invokes that specific verb. Worse, `build_parser`’s three callers are non-verb infrastructure (the digest shows the verbs column blank), so extracting it first risks breaking entrypoints before any modularity is gained.

The low-risk order is the opposite: extract the 65 self-contained verbs first, because no parser logic lives in them, and leave `build_parser` as the last central hub to be replaced by an explicit registry/data contract.

--- branch 4 [ok] ----------------------------------------
**Strongest claim:** The six verbs most likely to *respond without answering* are the ones that are both **>100 lines and call no local helper**: `cmd_eye` (246), `cmd_resident` (192), `cmd_recall_curate` (164), `cmd_sift` (150), `cmd_mailbox` (135), `cmd_bifrost_send` (104). That is **991 lines of helperless, self-contained verb body** — the structural shape of inline terminal rendering with no answer seam.

**Why this signal predicts DAWE failure:**  
The digest shows **65 of 87 verbs call no local helper** at all. A 100+ line `cmd_*` with zero helper calls means fetch, transform, and render are all fused; there is no returned object to separate “answer” from “response.” All `cmd_*` functions are **called by 0**, so nothing else consumes a return value — the path of least resistance is print-and-exit. [ASSUMED: the digest does not record return statements, so the following check must verify it.]

**Cheap mechanical check — RED pin first:**

For every `cmd_*`, AST-walk and record:
- `body_lines`
- `local_helper_calls` — calls to functions in the same module prefixed `_`
- `terminal_write_calls` — `print`, `click.echo`, `rich.print`, `sys.stdout.write`
- `value_returns` — `Return` nodes with a non-`None` value

Flag as likely response-only if:

```text
body_lines > 100
AND local_helper_calls == 0
AND value_returns == 0
```

That first pass pins exactly the six above.  
A second pass should flag:

```text
terminal_write_calls >= 3
AND value_returns == 0
```

This catches output-heavy verbs even when they have one helper, e.g. `cmd_boot` + `_orientation_header` (259 lines of header-building) and `cmd_events` + `_print_events`.

Run these two passes, pin the six helperless verbs first, then refactor them into a returned answer object plus a separate renderer.  read 5 of 5 branches -- read them -- 5 different questions were never asked the same thing, so there is no disagreement here for another call to settle.

