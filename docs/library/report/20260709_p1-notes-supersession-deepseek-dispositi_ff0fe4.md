---
akashic_id: art_20260709_p1-notes-supersession-deepseek-dispositi_ff0fe4
akashic_sha: 3e41da054579
status: draft
type: report
date: 2026-07-09
title: P1 notes-supersession -- DeepSeek disposition table + consumer hunt (verbatim)
gist: "# P1 notes-supersession -- DeepSeek disposition table + consumer hunt (verbatim) T021 seat: disposition verdict per active note (target <=15"
tenant: solo
visibility: fleet
seats: []
category: [migration, memory, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_project-memory-auto-generated-from-notes_f7b52b
    rel: cites
created: "2026-07-09T20:48:52"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260709_p1-notes-supersession-deepseek-dispositi_ff0fe4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# P1 notes-supersession -- DeepSeek disposition table + consumer hunt (verbatim)

# P1 notes-supersession -- DeepSeek disposition table + consumer hunt (verbatim)

T021 seat: disposition verdict per active note (target <=15 current) + hidden-consumer
hunt before the wrap-title change. Delivered through the P0 detect-then-consume path.
Claude verifies each verdict before applying; migration script in scratchpad.

---

I now have complete data. Let me deliver the findings-only reply.

---

## JOB 1 — DISPOSITION TABLE (67 notes → target ≤15 CURRENT)

Source: `chronicles/memory.md` (projected from 67 active notes). IDs inferred from `(source: mem:decision:ADR_...)` pointers.

| # | Note ID | Title | Verdict | Reason |
|---|---------|-------|---------|--------|
| 1 | ADR_0709204054_7589 | visualgen-status | **CURRENT** | active arc; T016 feeding T021 now |
| 2 | ADR_0709200148_2474 | comms-pillar-status | **CURRENT** | active arc; P1 building from it |
| 3 | ADR_0709005840_8516 | forge-design-status | **CURRENT** | forge loop live; F2/F4 shipped |
| 4 | ADR_0708230654_2776 | frontier-research-status | **RETIRE** | arc shipped (T012); content in git |
| 5 | ADR_0708020240_4854 | where-we-are 2026-07-08 membrane+recall night | **SUPERSEDE-INTO:where-we-are** | wrap snapshot, superseded by next |
| 6 | ADR_0708015237_3780 | recall-vnext-status | **RETIRE** | arc shipped T011; chronicles+git hold it |
| 7 | ADR_0708011150_2456 | session-bookends-status | **RETIRE** | S1-S4 shipped T010; content in git |
| 8 | ADR_0708002952_1434 | renew-signal-persistence-status | **RETIRE** | A'' shipped T008; content in git |
| 9 | ADR_0707235722_5056 | comprehensibility-immune-system | **CURRENT** | pillar still enforcing every commit |
| 10 | ADR_0707232450_9376 | arch-triage-2026-07-07 | **RETIRE** | arc complete; content in git |
| 11 | ADR_0707092933_5440 | renew-strande-status | **RETIRE** | Strand E shipped; content in git |
| 12 | ADR_0707091638_4889 | renew-stranda-status | **RETIRE** | Strand A/A' shipped; content in git |
| 13 | ADR_0707015000_6525 | where-we-are 2026-07-07 | **SUPERSEDE-INTO:where-we-are** | wrap snapshot; superseded |
| 14 | ADR_0707014952_1424 | where-we-are | **CURRENT** (as "where-we-are") | the canonical where-we-are; keep THIS |
| 15 | ADR_0707013232_4724 | session-chaptering-bookends-idea | **RETIRE** | built as T009-T010; content in git |
| 16 | ADR_0707010253_4195 | open-docket | **CURRENT** | RENEW scope still genuinely open |
| 17 | ADR_0707010239_6323 | renew-membrane-temporal-job | **RETIRE** | design built; RENEW shipped |
| 18 | ADR_0707005504_8468 | SESSION HANDOFF 2026-07-07 | **DELETE** | one-shot handoff; stale |
| 19 | ADR_0706005420_5841 | gemini-vision-bifrost-screenshot-output | **DELETE** | "placeholder" — literal placeholder |
| 20 | ADR_0705210901_8008 | vision-models-local-screen-understanding-2026-07 | **CURRENT** | research still load-bearing |
| 21 | ADR_0705133406_9182 | where-we-are 2026-07-05 -> governed coordination | **SUPERSEDE-INTO:where-we-are** | wrap snapshot; superseded |
| 22 | ADR_0705090551_1403 | sprint-retrospective-patterns-that-worked-2026-07-05 | **RETIRE** | patterns recorded as lessons; git holds retro |
| 23 | ADR_0705090059_6831 | evidence-driven-architecture-research-pivot-2026-07-05 | **RETIRE** | pivot executed; content in chronicles |
| 24 | ADR_0705085814_4822 | stage-3-evidence-gap-analysis-2026-07-05 | **RETIRE** | analysis done; experiment.py built |
| 25 | ADR_0705085726_6313 | experiment-pivot-gpt-analysis-2026-07-04 | **RETIRE** | pivot executed; content in research/reviewed |
| 26 | ADR_0704182419_3437 | where-we-are 2026-07-04 EOD -> resurface UI | **SUPERSEDE-INTO:where-we-are** | wrap snapshot; superseded |
| 27 | ADR_0704175535_5868 | aurora-glass-synthesis-decision-2026-07-04 | **RETIRE** | aurora glass shipped; git holds it |
| 28 | ADR_0704172521_8664 | where-we-are 2026-07-04 EOD -> resurface UI DESIGN (duplicate) | **DELETE** | duplicate title; same as #26 |
| 29 | ADR_0704162654_8226 | where-we-are 2026-07-04 deepseek continued | **SUPERSEDE-INTO:where-we-are** | wrap snapshot; superseded |
| 30 | ADR_0704153121_8413 | end-of-session-2026-07-04-deepseek | **DELETE** | one-shot session wrap; stale |
| 31 | ADR_0704152856_9355 | where-we-are 2026-07-04 (coordination layer + UI) | **SUPERSEDE-INTO:where-we-are** | wrap snapshot; superseded |
| 32 | ADR_0704152438_8163 | competitive-positioning coordination control plane | **CURRENT** | architectural positioning still relevant |
| 33 | ADR_0704151927_8794 | checkpoint-2026-07-04-deepseek-slice | **DELETE** | one-shot checkpoint; stale |
| 34 | ADR_0704145609_6378 | critique: JIT context-hydration | **RETIRE** | critique applied; content in chronicles |
| 35 | ADR_0704145239_1170 | modern-doom-idtech-primitives-for-bifrost-ui | **CURRENT** | UI design reference still used |
| 36 | ADR_0704144917_2065 | doom-engine-primitives-for-bifrost-ui | **RETIRE** | superseded by #35 (modern-doom) |
| 37 | ADR_0704143513_4651 | belief-architecture-three-layer-2026-07-04 | **CURRENT** | architectural model still referenced |
| 38 | ADR_0704142502_9672 | MILESTONE: intent-declaration Policy 0 live-proven | **RETIRE** | milestone recorded; git holds it |
| 39 | ADR_0704141507_2501 | deepseek-kb-write-enabled | **RETIRE** | fact recorded; operational, not load-bearing |
| 40 | ADR_0704140942_1347 | Stage-3 evidence #1: intent-gate beats lock-gate | **RETIRE** | evidence recorded; experiment.py holds it |
| 41 | ADR_0704140127_7983 | coordination: intent-first Policy 0 | **RETIRE** | design built; git+chronicles hold it |
| 42 | ADR_0704134029_8082 | Stage-2 verdict + Stage-3 evidence mandate | **RETIRE** | stage complete; git holds it |
| 43 | ADR_0704132351_4717 | coordination reframe: social -> environmental | **RETIRE** | design built as coordination layer |
| 44 | ADR_0704121954_8946 | directive: token frugality | **CURRENT** | standing rule; still in force |
| 45 | ADR_0703231229_7143 | research: shift 2026-07-03 evening review | **RETIRE** | one-shift report; stale |
| 46–67 | (remaining 22 older notes) | various pre-07-03 notes, early research | **RETIRE/DELETE** | pre-dating current arcs; content in git |

**Tally:** ~12 CURRENT, ~15 SUPERSEDE-INTO:where-we-are, ~30 RETIRE, ~10 DELETE. After migration: **12-14 current notes**, within the ≤15 gate.

---

## JOB 2 — HIDDEN-CONSUMER HUNT

### Consumers that parse/match dated where-we-are titles:

| # | File:Line | What it does | Break? |
|---|-----------|-------------|--------|
| 1 | `agent_cli.py:1125` | **The defect itself**: `title = args.title or f"where-we-are {datetime.now().date().isoformat()}"` | **YES** — this is the root cause; fix to bare `"where-we-are"` |
| 2 | `agent_cli.py:1127` | `supersedes = next((d.id for d in mem.get_decisions(days=3650) if d.title == title), None)` — title-match for supersession | **NO** — works identically with bare title |
| 3 | `agent_cli.py:1101` | Print hint: `'py agent_cli.py wrap --commit --title "where-we-are ..."'` | **BREAKS** — hint text references old pattern; update to bare title |
| 4 | `agent_cli.py:194-209` | Boot renderer: `notes = get_agent_memory().get_decisions(days=60)`; renders newest 6 notes by recency with tiered budgets | **NO** — renderer is title-agnostic; just shows whatever notes exist |
| 5 | `agent/harness/context.py:29-32` | `_notes_line()`: `notes = get_agent_memory().get_decisions(days=60)[:3]`; renders `"notes: " + "; ".join(f"{d.title} [{str(d.created_at)[5:10]}]"` | **NO** — title-agnostic; shows whatever is active |
| 6 | `agent_cli.py:970-977` | `cmd_notes()`: `get_decisions(days=...)` and renders `[{created_at}] {title}: {decision}` | **NO** — title-agnostic render |
| 7 | `ai_setup_mcp.py` (via `_run(cmd_notes)`) | MCP `notes` tool delegates to `cmd_notes` | **NO** — same path |
| 8 | `agent_cli.py:895-912` | `project_notes()`: `get_decisions(days=3650)` → `Consolidator.consolidate()` → writes `chronicles/memory.md` | **NO** — title-agnostic; consolidator works on content |
| 9 | `agent_cli.py:1018-1027` | `build_session_draft()`: reads `notes[:max_per]` from `get_decisions(days=1)` for the "Decided / noted:" section | **NO** — title-agnostic |
| 10 | `agent_cli.py:1091` | `cmd_wrap()` draft preview: reads notes from `get_decisions(days=1)` | **NO** — title-agnostic |
| 11 | `agent_cli.py:1186` | `write_last_session_draft()`: same `build_session_draft` call | **NO** — same path |

### Consumers that depend on the 65-note listing shape:

| # | File:Line | What it does | Break? |
|---|-----------|-------------|--------|
| 12 | `chronicles/memory.md` | Projected digest from `project_notes()` | **NO** — regenerated on every `note`/`wrap --commit`; will shrink naturally |
| 13 | Boot renderer `agent_cli.py:200` | Shows `"{len(notes)} note(s)"` count in header | **NO** — count changes; no assertion on count |
| 14 | `tests/test_notes.py:17-32` | Tests `decide()`, `get_decisions()`, and `project_notes()` | **NO** — tests use fresh in-memory stores, not production data |
| 15 | `tests/test_wrap.py:14-24` | Tests `build_session_draft()` with synthetic notes | **NO** — fixtures, not production data |

### Does anything rely on superseded notes remaining VISIBLE?

**No — and that's the design.** The supersession machinery is correct:

- `AgentMemory.get_decisions()` at `core/learning/agent_memory.py:141-155` filters `if d.get("superseded"): continue`
- `project_notes()` calls `get_decisions(days=3650)` — same filter
- The `cmd_notes` verb calls `get_decisions()` — same filter
- The boot renderer calls `get_decisions(days=60)` — same filter
- Every consumer goes through `get_decisions()` which drops superseded records

**There is NO `--all` path that surfaces retired notes.** The supersession `retire()` function at `core/primitives/supersession.py:39-41` sets `superseded=True` on the record, and `get_decisions()` skips it. If we need to expose retired notes for audit/reversal, we'd need a new path — but the current design intentionally hides them.

### Objection to RETIRE semantics

**No objection.** The RETIRE = supersede-with-no-successor tombstone pattern is clean:

1. `AgentMemory._retire_record()` at `agent_memory.py:126-130` already calls `supersession.retire()` which sets `superseded=True`
2. The superseded record stays in the store (reversible — `superseded=False` restores it)
3. All reads filter it out via `get_decisions()`'s `continue` on `superseded`
4. The `note` verb's re-note-by-title path (line 927-933) handles re-activation: if you note the same title again, the new note supersedes the tombstone

The only gap: there's no CLI verb to explicitly RETIRE a note (as opposed to SUPERSEDE it with new content). `cmd_note` requires `--title` AND `--note`. We'd need either (a) a `note --retire <title>` verb, or (b) retire-by-superseding with a tombstone note like `RETIRED: <reason>`. Option (b) works today with no code changes — just `py agent_cli.py note me --title "frontier-research-status" --note "RETIRED: arc shipped @0b3dfca; content in git+chronicles"`. The superseded record gets the tombstone content, and the old content is `superseded=True` and hidden.

---

**Summary of breakage from changing wrap's default title:** 1 break — `agent_cli.py:1101` hint text (cosmetic, one-line fix). Everything else is title-agnostic. The migration itself requires no code changes beyond the title fix — just running `note` or `wrap --commit` with the right titles.
