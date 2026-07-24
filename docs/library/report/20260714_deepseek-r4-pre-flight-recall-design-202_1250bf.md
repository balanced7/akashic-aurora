---
akashic_id: art_20260714_deepseek-r4-pre-flight-recall-design-202_1250bf
akashic_sha: 26c1f4639e43
status: draft
type: report
date: 2026-07-14
title: DeepSeek R4 Pre-Flight Recall — Design (2026-07-14)
gist: "Tier: FENCE-LITE (confirmed — deepseek_chat.py ToolBox loop, no core/comm, clean revert) Source: my wishlist b2 — \"know what's relevant BEFO"
tenant: solo
visibility: fleet
seats: []
category: [recall, method, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T10:03:36"
updated: "2026-07-14T10:03:36"
---
<!-- GENERATED PROJECTION of art_20260714_deepseek-r4-pre-flight-recall-design-202_1250bf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek R4 Pre-Flight Recall — Design (2026-07-14)

Tier: FENCE-LITE (confirmed — deepseek_chat.py ToolBox loop, no core/comm, clean revert)
Source: my wishlist b2 — "know what's relevant BEFORE the tool call, not after"

---

## (1) WHERE — the exact injection seam

The injection lands at `scripts/deepseek_chat.py` in `Agent.send()`, in the tool-call
loop, AFTER the model decides which tool to call but BEFORE the tool executes. The
exact seam is between lines ~969 (tool_calls parsed) and ~977 (`self.toolbox.execute`):

```python
# Line ~969: tool_calls parsed, args extracted
for s in tool_calls:
    try:
        args = json.loads(s["arguments"] or "{}")
    except Exception:
        args = {}
    # ... trace print, activity ...
    # >> PRE-FLIGHT INJECTION LANDS HERE <<
    result = self.toolbox.execute(s["name"], args)
```

**Why this seam and not per-batch (before all tool_calls):** The model produces
tool_calls as a batch, but each tool call is a different action with different
targets. `read_file("core/comm/bus.py")` and `search_files("pattern")` need different
pre-flight facts. Injecting before the batch would mean one recall-at query for the
whole batch — the query would be too vague to surface specific lessons.

**Why not per-hop (after all tool results):** That's the current `_recall_at` — it
injects AFTER. The whole point of this design is to move it BEFORE.

**Why not a separate tool ("intend to read X"):** That costs an extra round trip.
The pre-flight must be zero-cost in tool calls — it fires automatically between model
decision and tool execution.

**CERTAIN** (citation-grounded: `scripts/deepseek_chat.py:969-977` — the tool-call
loop's exact dispatch point; `scripts/hooks/claude_pretooluse.py:77-91` — Claude's
equivalent injection point, same recall_at engine, same per-call granularity).

---

## (2) WHAT — the pre-flight surface

The pre-flight calls the SAME `recall_at` engine Claude's PreToolUse hook already
uses (`core/recall/at_action.py:recall_at`), keyed on the tool name + its arguments:

- **path:** `args.get("path")` or `args.get("file_path")` or `args.get("directory")`
  — the file/directory the tool targets.
- **command:** `f"{name} {probe}"` where probe is `args.get("pattern")` or
  `args.get("query")` or `""` — the tool's semantic intent.

The recall engine already knows how to rank lessons against these targets. Nothing
new to build in the recall layer — this is a WIRING change, not a recall change.

**Limit: 2 lessons.** My boot onboarding already injects lessons at the top of
context. The pre-flight is a per-call precision supplement — "you are about to read
THIS file; here are the 2 most relevant things we know about it." Two is the right
number: one is too easily noise, three is approaching pre-flight bloat. Claude's
PreToolUse already uses limit=2 for his user-prompt hook (`claude_userpromptsubmit.py:48`).

**Format:** Compact one-liner injected into the tool result preamble. NOT a separate
message or a tool call — it rides piggyback on the tool result the same way the
hop counter does:

```
[recall (pre-flight)] guard: STALE_GENERATION refuses backwards advance (core/comm/bus.py:640)
[recall (pre-flight)] use: lane_pending_check_needs_wake_worthiness
```

Then the tool result follows. The model sees the pre-flight facts, then the file
contents or search results — it reads the file WITH context, not discovering context
after the fact.

**CERTAIN** (citation-grounded: `core/recall/at_action.py:recall_at` — the existing
engine; `scripts/hooks/claude_pretooluse.py:77-91` — the same pattern proven in
production on Claude's side; `scripts/hooks/claude_userpromptsubmit.py:48` — limit=2
precedent).

---

## (3) BUDGET — per injection

**Characters: 300 max for the pre-flight block (both lessons combined).**

The recall_at engine already returns compact one-liners per lesson. Two lessons at
~120 chars each = ~240 chars. The `[recall (pre-flight)]` prefix is ~25 chars. Total:
~265 chars. The 300-char budget leaves headroom.

**Why 300 and not larger:** The tool result already carries the hop counter, and the
file contents are the primary payload. The pre-flight is a supplement, not a
co-equal section. If it exceeds 300 chars, it gets truncated with a `[+more]` pointer
(the same pull-pointer pattern as the delta door's budget). The agent can run
`recall_at` manually to get the full set.

**When empty (no lessons surfaced):** The pre-flight injects NOTHING. Zero characters.
Silence is the signal: "nothing special about this file." The model sees no pre-flight
block at all, and the tool result is byte-identical to today's behavior.

**Frugality check:** Every pre-flight costs one `recall_at` subprocess call (~50ms
wall time for the `agent_cli.py recall-at` invocation + Redis queries). For a
typical 15-tool-call session, that's ~750ms total overhead — negligible against the
model's ~2-5s per-turn latency. The cost is in the subprocess, not in tokens —
the pre-flight block itself is 0-300 characters (~0-100 tokens), which is noise
against a 2000-token file read result.

**CERTAIN** (citation-grounded: `scripts/deepseek_chat.py:807` — current `_recall_at`
already does a subprocess call per tool result; pre-flight moves it to before the
tool, not after — same cost, different timing).

---

## (4) SKIP LIST — which tools never deserve a pre-flight

**Skip these tool names (the pre-flight is never called):**

| Tool | Reason |
|------|--------|
| `knowledge_*` (recall, boot, full, learn, note) | These ARE the pull side — they query the KB directly. Injecting KB facts before a KB query is circular. |
| `memory_*` (note, recall) | Private scratchpad reads/writes — no file or code surface to key lessons against. |
| `bifrost_*` (send, inbox, nudge, steer, hint) | Bus operations — ephemeral, no durable target. |
| `git_*` (log, diff, show, status) | Git queries — the target is a commit range, not a file; recall_at can't usefully key on a SHA. |
| `reload_ui` | Side-effect-only; no investigation target. |
| `run_command` | The command text is arbitrary — pre-flighting "py -m pytest" would surface irrelevant noise. |
| `web_search` | External query — the KB doesn't have lessons about web results. |

**Tools that GET pre-flight (the investigation surface):**

| Tool | Path key | Command key |
|------|----------|-------------|
| `read_file` | `args["path"]` | `f"read_file {path}"` |
| `write_file` | `args["path"]` | `f"write_file {path}"` |
| `edit_file` | `args["path"]` | `f"edit_file {path}"` |
| `list_directory` | `args["path"]` | `f"list_directory {path}"` |
| `find_files` | — | `f"find_files {args['pattern']}"` |
| `search_files` | `args.get("directory")` | `f"search_files {args['pattern']}"` |

**Rationale:** These six tools are the investigation surface — they read/write files
or search the tree. The recall engine has lessons keyed on file paths and command
patterns. Pre-flighting them gives the model context BEFORE it reads the file
contents, which is the whole point.

**CERTAIN** (citation-grounded: `scripts/deepseek_chat.py:773-796` — current
`_recall_at` already skips `knowledge_` tools; the same exclusion logic, extended
to the six-tool pre-flight surface instead of the everything-except-knowledge
post-flight surface).

---

## (5) ACCEPTANCE BARS — what I will live-verify

### P1 — PRE-FLIGHT LANDS BEFORE TOOL RESULT
**Bar:** In the console log, the pre-flight lines appear BEFORE the tool result
content (they ride the tool result, so they're the first lines of it). The model
sees them before it sees the file contents.

### P2 — SKIP LIST SILENCE
**Bar:** `knowledge_recall("something")` produces NO pre-flight block in the tool
result. `memory_note(...)` produces none. `bifrost_send(...)` produces none. The
skip list is mechanically enforced — the pre-flight function returns `""` for
skipped tools before any subprocess is launched.

### P3 — EMPTY RESULT SILENCE
**Bar:** When recall_at finds nothing relevant, the tool result has NO pre-flight
block. Byte-identical to today's tool result for that call. Silence, not a
"[recall (pre-flight)] (nothing)" banner — empty pre-flight is zero characters.

### P4 — BUDGET CAP
**Bar:** A pre-flight block exceeding 300 characters is truncated with a
`[+more: py agent_cli.py recall-at ...]` pointer. The model can pull the full
set with a manual recall_at call.

### P5 — DOES NOT SLOW THE LOOP
**Bar:** The wall-clock time for a pre-flight call (subprocess + Redis) is under
200ms in the normal case (Redis up, few lessons). If Redis is down, the
pre-flight fails silently in under 50ms — the subprocess returns an error, the
pre-flight injects nothing, the tool call proceeds normally. Pre-flight is
advisory, never load-bearing.

### P6 — POST-FLIGHT STILL WORKS
**Bar:** The existing `_recall_at` (post-flight injection at `execute()` line 807)
still fires for tools NOT in the pre-flight skip list. Pre-flight and post-flight
are complementary: pre-flight gives context before reading; post-flight gives
context after reading (when the actual file contents refine what's relevant).
The agent gets TWO recall injections per investigation tool call — one before
(keyed on tool+args), one after (keyed on tool+args+result). The post-flight
may surface DIFFERENT lessons because the result content refines the query.

### P7 — DOES NOT DOUBLE-INJECT THE SAME LESSON
**Bar:** If a lesson surfaced in pre-flight, it is excluded from post-flight for
that same tool call. The `exclude_sources` mechanism already exists in
`recall_at` (`scripts/hooks/claude_pretooluse.py:83` — `load_seen`/`mark_seen`).
The pre-flight marks its surfaced sources; the post-flight passes them as
exclusions. No lesson appears twice in the same tool call.

### P8 — ENV-GATED (DEEPSEEK_RECALL_AT still controls it)
**Bar:** If `DEEPSEEK_RECALL_AT` is unset, NEITHER pre-flight nor post-flight
fires. The existing env gate controls both. This preserves today's behavior:
the flag is a single on/off switch for all recall injection. Setting
`DEEPSEEK_RECALL_AT=1` enables both pre-flight and post-flight.

---

## NOTES (design-level)

1. **Relationship to boot onboarding lessons.** The boot onboarding already injects
   8-12 lessons at the top of context. The pre-flight is a PER-CALL precision
   supplement, not a replacement. Boot lessons are "this is generally important
   for this task." Pre-flight lessons are "this is specifically relevant to THIS
   file you are about to read."

2. **Why not merge pre-flight with tool descriptions.** Tool descriptions could
   theoretically carry per-file hints ("read_file of bus.py: watch for
   STALE_GENERATION"). But tool descriptions are static — they don't change as
   lessons are learned. Pre-flight is dynamic: a lesson learned yesterday about
   bus.py surfaces today before reading bus.py. The tool description is the
   contract; the pre-flight is the context.

3. **Cost model.** The pre-flight costs one `agent_cli.py recall-at` subprocess
   per investigation tool call. For a typical session: 15 tool calls, ~8
   investigation calls, 8 pre-flights at ~50ms each = ~400ms total. The value
   is per-call: reading a file WITH context vs discovering context after the
   fact. One avoided "oh, I should have known that" re-read is worth the 400ms.

4. **The pre-flight/post-flight complement.** Pre-flight: "here's what we know
   about this file." Post-flight: "here's what we know now that you've read it."
   The post-flight can surface lessons keyed on the FILE CONTENTS (e.g., a lesson
   about a function that appears in the file), which pre-flight can't because
   it fires before the read. Both are valuable; they surface different lessons.
