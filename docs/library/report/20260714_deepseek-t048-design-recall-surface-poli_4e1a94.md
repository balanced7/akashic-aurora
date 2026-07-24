---
akashic_id: art_20260714_deepseek-t048-design-recall-surface-poli_4e1a94
akashic_sha: 5707f571f5dc
status: draft
type: report
date: 2026-07-14
title: DeepSeek T048 Design — Recall Surface Polish for Agent Tool-Loops (2026-07-14)
gist: "Class: T048 design — concrete mechanisms per interview item Inputs: research/reviewed/deepseek-experience-recall-at-2026-07-14.md §b/c Sites"
tenant: solo
visibility: fleet
seats: []
category: [recall, memory, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_deepseek-experience-interview-recall-at_db8dae
    rel: cites
created: "2026-07-14T00:06:48"
updated: "2026-07-23T21:42:17"
---
<!-- GENERATED PROJECTION of art_20260714_deepseek-t048-design-recall-surface-poli_4e1a94 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T048 Design — Recall Surface Polish for Agent Tool-Loops (2026-07-14)

Class: T048 design — concrete mechanisms per interview item
Inputs: research/reviewed/deepseek-experience-recall-at-2026-07-14.md §b/c
Sites examined (every file opened):
- core/recall/at_action.py:1-1060 (recall-at engine, _provenance_tag, render, full_record,
  _lessons, usefulness_factor, _STALE_CUE_DAYS, _INJ_DIR, truncation hint @ :1027)
- scripts/deepseek_chat.py:1-430 (ToolBox class, _agent_cli, knowledge_recall, tool schemas,
  tool registration pattern)
- agent_cli.py:419-470 (cmd_recall including --full), :467-490 (cmd_recall_at), :527-620
  (cmd_recall_counters)
- agent/initializer.py:1-120 (derive_agent_context_from_startup_sources)
- context/aggregator.py:1-200 (assemble_context, budget-fitting, boot sources)

---

## Overview

The five items from the interview (§b/c) are addressed in order. Each item
gets a DESIGN-LEVEL spec (no implementation code exists yet — all sites named
are the real target locations). Where the design involves a new CLI verb the
spec is interface-level; where it involves a render change the exact string
format is specified.

---

## ITEM 1: Fix the truncation dead-end

### Problem (from interview)

```text
... 3 of 4 relevant lesson(s) shown — `recall-at --limit 4` for the rest,
or `recall --full <source>` for any one's whole record
```

Both are CLI commands (`agent_cli.py recall-at --limit ...`, `agent_cli.py recall --full ...`).
Neither is a tool in the ToolBox. The hint is a dead end — I cannot act on it
from within a tool loop.

### Design: BOTH paths — real tools + tool-aware hint

#### (A) New ToolBox tool: `recall_at`

Exact schema (follows the `_fn()` pattern at `scripts/deepseek_chat.py:~175`):

```python
_fn("recall_at", "Re-run recall-at-action with a higher limit to see MORE lessons that cleared the relevance floor. This is the one-hop pull from the truncated surface hint. Returns the SAME engine result as the hook, just with more entries.",
    {"limit": {"type": "integer", "description": "how many lessons to surface (default 3; use the number from the hint, e.g. 5)"},
     "path": {"type": "string", "description": "file path the action targets (optional; omit to use the session's last-seen path)"},
     "command": {"type": "string", "description": "shell command the action targets (optional)"}})
```

ToolBox method (`scripts/deepseek_chat.py`):

```python
def recall_at(self, limit=3, path=None, command=None):
    args = ["recall-at", "--limit", str(limit), "--json"]
    if path:
        args += ["--path", str(path)]
    if command:
        args += ["--command", str(command)]
    return self._agent_cli(args)
```

Routes through `agent_cli.py cmd_recall_at` (already exists at :467), which calls
`core/recall/at_action.py:recall_at()` + `render()`. No new backend code —
the engine already supports arbitrary `limit`. The ToolBox just wasn't exposing it.

#### (B) New ToolBox tool: `knowledge_full` (also covers ITEM 2 — see below)

#### (C) Updated hint string in `render()`

Current (`at_action.py:1027`):
```python
f"... {shown} of {total} relevant lesson(s) shown — `recall-at --limit {total}` for the rest, "
f"or `recall --full <source>` for any one's whole record"
```

Replacement:
```python
f"... {shown} of {total} relevant lesson(s) shown — call `recall_at(limit={total})` for the rest, "
f"or `knowledge_full(source=\"<source>\")` for any one's whole record"
```

The hint now names TOOLS I can actually call. The `"<source>"` placeholder is
understood as "substitute the value from the lesson's source field."

**Design choice: tool-surface-aware render, not shell-command render.** The hint
string lives in the engine that serves both CLI and hook contexts. When called from
the CLI (`agent_cli.py recall-at`), the old shell-command hint is correct. When
called from the hook (which injects into an agent's tool-loop), the new tool-name
hint is correct. The render function doesn't know which context it's in.

**Resolution:** Add an optional `hint_style` parameter to `render()`:
- `"cli"` (default, backward-compat) → old shell-command hint
- `"tool"` → new tool-name hint

The PreToolUse hook passes `hint_style="tool"`; `cmd_recall_at` keeps the
default `"cli"`. This is a one-line change to the hook (`scripts/hooks/claude_pretooluse.py`
and `scripts/hooks/deepseek_pretooluse.py` — design-level, not opened for this
design but the render() signature change is the spec).

---

## ITEM 2: One-call full-lesson drill tool

### Problem (from interview)

When I see a truncated lesson and want its full body, I currently have no
tool — `knowledge_recall` may not return the same lesson, and it's a
round-trip guessing game.

### Design: `knowledge_full` tool

Schema:

```python
_fn("knowledge_full", "Pull the FULL body of ONE recalled lesson by its source pointer (e.g. 'learn:experiment:NAME'). This is the one-hop escape hatch from a truncated recall-at surface to the raw evidence — all fields (what_tried, expected, actual, root_cause, metrics, recommendation) returned verbatim.",
    {"source": {"type": "string", "description": "lesson source pointer, e.g. 'learn:experiment:bifrost_hint_render'"}}, ["source"])
```

ToolBox method:

```python
def knowledge_full(self, source):
    return self._agent_cli(["recall", "--full", str(source), "--json"])
```

Routes through `agent_cli.py cmd_recall` (already exists at :419-436 — the
`--full` branch calls `core/recall/at_action.py:full_record()`). The full
record function already:
- Extracts the experiment name from the `learn:experiment:` prefix
- Calls `learning_store._load_experiment(exp_id)`
- Records an `engaged` feedback event (strong implicit interest signal)
- Returns `{}` fail-soft on any error

**Zero new backend code.** The CLI verb already exists and works. The ToolBox
just wasn't wired to it. The `--json` flag on `cmd_recall --full` already exists
(at :429: `if args.json: print(json.dumps(rec, default=str))`).

**Register this tool in the TOOLS list at `scripts/deepseek_chat.py:~160`** (alongside
the existing `knowledge_recall`/`knowledge_boot` entries).

---

## ITEM 3: Novelty-vs-boot indicator on `knowledge_recall`

### Problem (from interview)

When I call `knowledge_recall`, some results duplicate what was already in my
boot context. I don't know which is which. A `[new]`/`[boot]` tag would let me
skip what I've already seen.

### Where "already in boot" state lives

The boot context is assembled by `context/aggregator.py:assemble_context()`.
It surfaces lessons via `context/learning_loader.py:load_learnings_ranked_by_relevance()`.
Each surfaced lesson carries a `source` field (e.g., `learn:experiment:NAME`).

There are TWO places boot-surfaced sources are recorded:
1. **Injection ledger** (`_INJ_DIR` in `at_action.py:193`) — every piece of
   context PUSHED at an agent is logged per session. The boot context is injected
   at session start, so boot-surfaced lesson sources ARE in the injection ledger.
2. **Session seen-set** (`_SEEN_DIR` in `at_action.py:175`) — the anti-repeat
   mechanism tracks which lesson sources have been shown this session.

The injection ledger is the canonical source because it's inspectable ("harnesses
inject context behind your back" is the canonical objection, per the field survey).

### Design: `novelty` parameter on `knowledge_recall` tool

**ToolBox side** — add optional parameter to existing `knowledge_recall`:

```python
def knowledge_recall(self, query, novelty=False):
    result = self._agent_cli(["recall", query, "--json"])
    if not novelty:
        return result
    # Post-process: compare each result's source against boot-injected sources.
    # Boot sources are in the injection ledger for this session under the "boot"
    # altitude. Parse the JSON result, tag each entry.
    try:
        data = json.loads(result)
        boot_sources = self._boot_sources()
        for entry in data:
            src = entry.get("source", "")
            tag = "[boot]" if src in boot_sources else "[new]"
            entry["_novelty"] = tag
        return json.dumps(data, default=str)
    except Exception:
        return result  # fail-open: untagged results beat an error
```

**Tool schema update** — add `novelty` to the existing `knowledge_recall` schema:

```python
_fn("knowledge_recall", "Search Akashic Aurora's learned-knowledge base...",
    {"query": {"type": "string", "description": "Keywords, e.g. 'faithfulness critic'"},
     "novelty": {"type": "boolean", "description": "If True, prefix each result with [new] or [boot] — marks whether this lesson was already in your boot context"}}, ["query"])
```

**`_boot_sources()` helper** — reads the injection ledger for the current session,
filters for entries from the boot altitude, extracts the set of lesson sources:

Design-level spec (implementation lives in ToolBox, not in at_action.py):
1. Find the most recent injection ledger file in `_INJ_DIR` for this session
2. Parse JSON lines
3. Filter for `altitude == "boot"` entries
4. Extract all `sources` arrays → flatten to a set
5. Cache the set for the session lifetime (boot doesn't change mid-session)

**Fallback:** If the injection ledger is missing/corrupt, `_boot_sources()` returns
an empty set → all results get `[new]` (fail-open: untagged beats an error).

**Design decision: CLI-side, not render-side.** The novelty tag is a ToolBox
post-processing concern, not a change to `at_action.py:render()`. The render
function serves the hook's `additionalContext` where boot-vs-novelty distinction
is irrelevant (the hook IS the boot). This keeps the engine clean.

---

## ITEM 4: Confidence/usage legend

### Problem (from interview)

I see `[worked claude helped 2x useful 1x]` but I don't know what these terms
mean. The tags are parseable but their epistemic meaning isn't obvious:
- `worked` = self-reported success (NOT independently verified)
- `helped Nx` = automatic FAIL→SUCCESS credit
- `useful Nx` = explicit vote
- `unverified` = author didn't report success (not "confirmed failure")
- `anti-pattern` = documented known-bad
- `advice` = forward-looking recommendation (not an observation)

### Design: Compact legend line in `render()`

Add ONE line to the bottom of `render()` in `at_action.py`, after the staleness
cue and before the 900-char cap. The legend only fires when at least one
surfaced lesson carries credibility markers (any of: helped, useful, or
a non-default success status).

**Exact render format:**

```python
# After the staleness cue block (~:1058), before `body = header + ...`:
credibility_terms_used = any(
    (l.get("_use") or {}).get("helped") or (l.get("_use") or {}).get("useful")
    or l.get("success") not in ("", "yes", "true")
    for l in result.get("lessons", []))
if credibility_terms_used:
    lines.append(
        "[legend] worked=self-reported | helped=auto credit | useful=vote | "
        "unverified=unconfirmed | anti-pattern=known-bad | advice=forward-looking")
```

**This renders this block:**

```
[legend] worked=self-reported | helped=auto credit | useful=vote | unverified=unconfirmed | anti-pattern=known-bad | advice=forward-looking
```

Design decisions:
- **Only when needed.** Silent when lessons carry no credibility markers (zero-cost
  for simple results).
- **Bottom position.** After lessons, after counter, after truncation hint, after
  age cue — it's reference material, not the headline.
- **Compact.** One line, ~140 chars. Well within the 900-char total cap.
- **No new terms.** Only defines the terms already in `_provenance_tag()` output.
  The `partial` tag (rare) isn't defined — the compact line prioritizes the
  common terms; `partial` is self-explanatory.
- **Within the 900-char cap.** The render body is `header + "\n" + "\n".join(lines)`
  then `body[:900]`. The legend comes last so it's the first thing truncated if
  the surface is full — correct priority.

---

## ITEM 5 (OPTIONAL): Diff since last boot

### Problem (from interview)

When I resume a session, the boot context is a full re-injection — I get the
same 150 lines. A diff-style summary would be higher signal.

### Design: `knowledge_diff` tool (smallest honest v1)

**Schema:**

```python
_fn("knowledge_diff", "Show what changed since your last boot: new lessons, new notes, ledger state changes. Compact diff for session resumption.",
    {})
```

**ToolBox method:**

```python
def knowledge_diff(self):
    return self._agent_cli(["diff", "--since-boot", self.agent_id or "deepseek", "--json"])
```

**New CLI verb: `agent_cli.py diff`** — design-level spec:

1. Find the last `boot` event for this agent (`agent_cli.py events --kind boot --agent <id> --limit 1`)
2. Query events since that timestamp:
   - New `learning` events → "N new lessons"
   - New `note` events → "N new/updated notes"
   - `ledger_update` events → "T0XX now in_progress, T0YY claimed"
   - New `bifrost_msg` events → "N new bus messages"
3. Return a compact summary:

```
# DIFF since boot @ 2026-07-14 04:00 UTC (~3h ago)
lessons: +2 new (experiment: recall_at_tool, experiment: novelty_indicator)
notes: +1 new/updated (where-we-are: 2026-07-14 session)
ledger: T048 approved→claimed, T049 approved→claimed
bus: 3 unread messages
```

**Design decisions:**
- **No parameters.** The tool knows the agent's identity from the ToolBox and
  queries its own last boot. Zero cognitive load to call.
- **Fail-soft.** If no prior boot found: "no prior boot for <agent> — try knowledge_boot instead"
- **Compact.** Target <500 chars. This is a quick orientation, not a full re-boot.
- **CLI-side for reuse.** The `diff` verb is useful for any agent, not just
  DeepSeek's ToolBox. Claude's harness could call it too.

---

## REGISTRATION: New tool schemas in TOOLS list

All new tools register in `scripts/deepseek_chat.py:~160` in the `TOOLS` list,
alongside the existing `knowledge_recall`/`knowledge_boot` entries. The `_fn()`
factory pattern is already established. Summary of additions:

| Tool | Schema location | Backend | New code needed |
|------|----------------|---------|-----------------|
| `recall_at` | new `_fn()` in TOOLS | `agent_cli.py recall-at --limit N --json` (exists) | ToolBox method only |
| `knowledge_full` | new `_fn()` in TOOLS | `agent_cli.py recall --full SOURCE --json` (exists) | ToolBox method only |
| `knowledge_recall` (updated) | add `novelty` param to existing schema | existing + `_boot_sources()` helper | ToolBox post-processing |
| `knowledge_diff` | new `_fn()` in TOOLS | new `agent_cli.py diff --since-boot` verb | ToolBox + new CLI verb |
| `render()` hint string | `at_action.py:1027` | add `hint_style` param, tool-aware variant | render signature change |
| `render()` legend | `at_action.py:~1058` | credibility-terms-used gate + legend line | render addition |

---

## DESIGN NOTES

1. **Items 1-2 are zero-new-backend-code.** Both `recall_at` with arbitrary
   `limit` and `recall --full` already exist in the CLI. Only the ToolBox bridge
   is missing. This is a tool-surface gap, not a capability gap.

2. **Item 3's `_boot_sources()` helper is the only genuinely NEW mechanism.**
   The injection ledger already tracks every surfaced source per session. The
   helper just reads it and filters for boot altitude. If the injection ledger
   format isn't easily queryable, a fallback is: read the `_SEEN_DIR` anti-repeat
   files for this session (simpler, same info for boot sources).

3. **Item 4's legend is a pure render addition.** The terms it defines are already
   rendered by `_provenance_tag()`. This is just documentation-in-band.

4. **Item 5 is the most speculative.** The `diff` verb requires querying events
   by timestamp, which the event log likely supports (it already has `events --search`
   and `events --around`). If the event query infrastructure isn't up for it, the
   v1 can be: compare the current `knowledge_boot` output to a cached copy of
   the last boot, diff the text. That's cruder but still useful.
