# AXI bench: `boot`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 2,508 | 2,582 | +74 (+3%) |
| Stdout characters (all runs) | 5,829 | 5,958 | +129 (+2%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which port should be checked when tests hang at start? | `16379` | 5/5 | 5/5 |
| Which agent left alice a handoff? | `bench` | 5/5 | 5/5 |
| Which file is locked by bob? | `core/ledger.py` | 5/5 | 5/5 |
| According to the where-we-are note, what comes next? Answer in a few words. | `['ledger table']` | 5/5 | 5/5 |
| How many lessons does this startup context carry? | `2` | 5/5 | 5/5 |
| What is the full command alice would run to record a new lesson? Give the command only. | `['learn alice', '--experiment']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora boot alice --task tests hang at start` (exit 0)

```
# recall-at: cache warm (2 lesson(s)) but the hook is NOT installed -- edits get no hints, so silence means nothing. Turn it on: uv run agent_cli.py hooks install
# CONTEXT for alice -- task: tests hang at start
# 2 lesson(s), 0 blocker(s)
# door: CLI-shell -- this PROCESS carries no door stamp, so it cannot tell whether your SEAT has akashic tools; a shell-out from an MCP seat looks identical here. If yours are attached, ignore this line. If not: user-scoped MCP w/ absolute paths [T081-W2] or cd /tmp/axi-bench-v14b33g6/before && restart
# Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)
# Method: docs/method-baseline-2026-07.md (the HOW contract -- fenced dual passes on load-bearing work, pre-registered acceptance, kill drills; gated slices cite their reconciled build spec)
# [GAP] Governing arc: (none active -- check notes/ledger)
# where-we-are: Wave 3 of the payment refactor is done; next: migrate the ledger table.
# [GAP] CURRENT DIRECTIVE: (none set -- use `wrap --focus` to set priority)
# deferred: 20 command(s) await a seat with a doc-verb retitle/arc-edit surface (doc verb only has new/adopt today)/exec/its own fence or task -- Heimdall ruled it out of t384's scope (V11) to keep the instance-split fence focused, and I accepted/net/write -- not you; a capable seat discharges via `defer <it> --list`
# suite baseline @5ba81ba (805.8h old, by claude): 100 known failure(s) -- 1 classified lane(s) since closed (T275): re-run advised (classification rots even when the receipt is young)
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.
# Ledger: 170 done @4a1887fd | 26 active | 38 next | 0 blocked | 103 proposed (103 STALE -- re-approve or abandon) -- RULE: DONE is closed, the ledger beats old messages (details: task list)
#   T079 - T079: Engine-room observability (Daniel directive 2026-07-15 night: fold his ...[truncated]  (in_progress, sol)
#   T084 - T084: Ironman augmentation arc (Daniel directive 2026-07-16 pre-sleep verbatim: 'what can ...[truncated]  (claimed, sol)
#   T108 - N-seat mailbox architecture: unshare everything but the role queue (Daniel 2026-07-28 ...[truncated]  (claimed, claude)
#   next: T003 - UI: one presence surface -- remove duplicate top status rows + floating bubbles
#   next: T007 - Verify Void theme + aurora perf bench -> confirm defaults
# LIVE CONSTRAINTS (docs/LIVE_CONSTRAINTS.md -- forget one and it breaks you (+6 more in the doc)):
#   RB-26 crash-redelivery: the work cursor advances AFTER processing; a crash redelivers the same message -- consumers stay idempotent; never drop a work-lane copy (T066 refinement).
#   RB-29: timeout/error NOTES never settle an expectation (redrives stay alive); only ANSWER_KINDS reply/handoff/completion settle (T061).
#   T026 ack semantics: a reply that answers a handoff = handled (auto-ack); a timeout note never acks; senders cannot ack their own ask.
#   T039a/T044 dual-write is LIVE until T047: every message exists on TWO streams (work lane + legacy) -- dedupe by sha/reply_id, never by stream id.
#   T045 lane consumption: work lane FIRST, legacy is a straggler net; consume with the seat's lane env (BIFROST_CONSUME_LANE) or cursors diverge into wake loops.
#   T066 reply path: directed ANSWERS ride bus.send_reply (lane-first, meta.reply_id); receiver dedup drops LEGACY twins only -- work copies always deliver.
# STANCE (conduct-v1, docs/CONDUCT.md): intent before task | Daniel's words verbatim | one calibrated question per ask | red is a gem (credit the finder, help the lane, never blame) | 'no' is information | own, don't assign
# LICENSE: the laws are a FLOOR, not a ceiling -- exceed them, and file divergences that WORK as wishes/lessons to be amended in at a gate (the anti-fossil clause). Inheriting the forms WITHOUT this license is the known failure mode; the forms alone are a compliance checklist, not a culture.
# stretch (alice): none recorded in charters/alice/CHARTER.md -- L7 wants one per arc; unrecorded is a GAP, not a zero
# restored: 4/4 planes clean (notes-store, defer-queue, suite-baseline, task-ledger)
#------------------------------------------------------------
## LESSONS / CONTEXT (most relevant first)
- handoff from bench: finish the ledger migration  (source: bench:0)
- Wave 3 of the payment refactor is done; next: migrate the ledger table.  (source: ADR_1012161319_47756d1f)
- Stage explicit paths, never git add -A.  (source: git_blanket_staging)
- Use when tests hang at start: check that port 16379 is free first.  (source: port_clash)

## ARCH SLICE (orientation for this task)
  Foundation · Pillar 0 (`core/foundation/`) -> core/foundation/

## RECENT NOTES (durable project memory)
  [2026-10-12] where-we-are: Wave 3 of the payment refactor is done; next: migrate the ledger table.

## FUNNEL (recall value -- full: uv run agent_cli.py stats --days 7)
  2 lessons | surfaced 0 | votes useful=0 noise=0 | helped 0 | last 7d: +2 lesson(s), 0 flip(s)

## DOCTOR (fleet liveness -- full: uv run agent_cli.py doctor)
  doctor: fleet healthy (1 agent(s), 0 findings) | watches 2/2 [T079, T385]

## UNREAD BIFROST (live bus)
  (no new messages -- peek only; cursor unchanged)

## ADVISORY PATH-LOCKS (who's editing what -- C2)
  core/ledger.py  <- bob  token 1

## TO CONTRIBUTE A LESSON, run:
  uv run agent_cli.py learn alice --experiment NAME --tried "..." --result "..." --recommend "..."

## BIFROST (live + durable)
  uv run agent_cli.py bifrost-sync <agent>     # peek unread (same as boot section)
  uv run agent_cli.py promoted [--limit N]       # durable salient msgs (kind=bifrost_msg)
```


## After: output

`aurora boot alice --task tests hang at start` (exit 0)

```
agent: alice
task: tests hang at start
lessons: 2
blockers: 0
orientation[28]{line}:
  "Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)"
  "Method: docs/method-baseline-2026-07.md (the HOW contract -- fenced dual passes on load-bearing work, pre-registered acceptance, kill drills; gated slices cite their reconciled build spec)"
  "[GAP] Governing arc: (none active -- check notes/ledger)"
  "where-we-are: Wave 3 of the payment refactor is done; next: migrate the ledger table."
  "[GAP] CURRENT DIRECTIVE: (none set -- use `wrap --focus` to set priority)"
  "deferred: 20 command(s) await a seat with a doc-verb retitle/arc-edit surface (doc verb only has new/adopt today)/exec/its own fence or task -- Heimdall ruled it out of t384's scope (V11) to keep the instance-split fence focused, and I accepted/net/write -- not you; a capable seat discharges via `defer <it> --list`"
  "suite baseline @5ba81ba (805.8h old, by claude): 100 known failure(s) -- 1 classified lane(s) since closed (T275): re-run advised (classification rots even when the receipt is young)"
  "Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable"
  "NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats"
  "LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired."
  "Ledger: 170 done @4a1887fd | 26 active | 38 next | 0 blocked | 103 proposed (103 STALE -- re-approve or abandon) -- RULE: DONE is closed, the ledger beats old messages (details: task list)"
  "> T079 - T079: Engine-room observability (Daniel directive 2026-07-15 night: fold his ...[truncated]  (in_progress, sol)"
  "> T084 - T084: Ironman augmentation arc (Daniel directive 2026-07-16 pre-sleep verbatim: 'what can ...[truncated]  (claimed, sol)"
  "> T108 - N-seat mailbox architecture: unshare everything but the role queue (Daniel 2026-07-28 ...[truncated]  (claimed, claude)"
  "> next: T003 - UI: one presence surface -- remove duplicate top status rows + floating bubbles"
  "> next: T007 - Verify Void theme + aurora perf bench -> confirm defaults"
  "LIVE CONSTRAINTS (docs/LIVE_CONSTRAINTS.md -- forget one and it breaks you (+6 more in the doc)):"
  "> RB-26 crash-redelivery: the work cursor advances AFTER processing; a crash redelivers the same message -- consumers stay idempotent; never drop a work-lane copy (T066 refinement)."
  "> RB-29: timeout/error NOTES never settle an expectation (redrives stay alive); only ANSWER_KINDS reply/handoff/completion settle (T061)."
  "> T026 ack semantics: a reply that answers a handoff = handled (auto-ack); a timeout note never acks; senders cannot ack their own ask."
  "> T039a/T044 dual-write is LIVE until T047: every message exists on TWO streams (work lane + legacy) -- dedupe by sha/reply_id, never by stream id."
  "> T045 lane consumption: work lane FIRST, legacy is a straggler net; consume with the seat's lane env (BIFROST_CONSUME_LANE) or cursors diverge into wake loops."
  "> T066 reply path: directed ANSWERS ride bus.send_reply (lane-first, meta.reply_id); receiver dedup drops LEGACY twins only -- work copies always deliver."
  "STANCE (conduct-v1, docs/CONDUCT.md): intent before task | Daniel's words verbatim | one calibrated question per ask | red is a gem (credit the finder, help the lane, never blame) | 'no' is information | own, don't assign"
  "LICENSE: the laws are a FLOOR, not a ceiling -- exceed them, and file divergences that WORK as wishes/lessons to be amended in at a gate (the anti-fossil clause). Inheriting the forms WITHOUT this license is the known failure mode; the forms alone are a compliance checklist, not a culture."
  "stretch (alice): none recorded in charters/alice/CHARTER.md -- L7 wants one per arc; unrecorded is a GAP, not a zero"
  "[continuity DRIFT] the repo has moved since these were written: next-focus MISSING, grounding-pointer MISSING -- they describe an OLDER system than the one you are booting into. Refresh at wrap (uv run agent_cli.py wrap --focus/--grounding, note where-we-are)."
  "restored: 4/4 planes clean (notes-store, defer-queue, suite-baseline, task-ledger)"
recall_at: "armed (2 lesson(s) warm) -- listening at every edit; downstream silence is CALIBRATED (nothing relevant), not a dead hook"
door: "CLI-shell -- this PROCESS carries no door stamp, so it cannot tell whether your SEAT has akashic tools; a shell-out from an MCP seat looks identical here. If yours are attached, ignore this line. If not: user-scoped MCP w/ absolute paths [T081-W2] or cd /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-aa75295f17f742157 && restart"
context[4]{summary,source}:
  "handoff from bench: finish the ledger migration","bench:0"
  "Wave 3 of the payment refactor is done; next: migrate the ledger table.",ADR_1012161401_c379dbeb
  "Stage explicit paths, never git add -A.",git_blanket_staging
  "Use when tests hang at start: check that port 16379 is free first.",port_clash
arch_slice[1]{heading,path}:
  Foundation · Pillar 0 (`core/foundation/`),core/foundation/
notes[1]{date,title,note}:
  2026-10-12,where-we-are,"Wave 3 of the payment refactor is done; next: migrate the ledger table."
funnel: "2 lessons | surfaced 0 | votes useful=0 noise=0 | helped 0 | last 7d: +2 lesson(s), 0 flip(s)"
method: "method drift: M3 pre-registration 0/17 clean (0%) -- pins are landing WITH their implementation, so git holds no evidence the acceptance came first. Commit the RED pin alone, then the fix. (uv run scripts/arc_scorecard.py)"
doctor: "doctor: fleet healthy (1 agent(s), 0 findings) | watches 2/2 [T079, T385]"
unread_bifrost: (no new messages -- peek only; cursor unchanged)
path_locks[1]{path,agent}:
  core/ledger.py,bob
help[3]:
  uv run agent_cli.py learn alice --experiment NAME --tried "..." --result "..." --recommend "..."
  uv run agent_cli.py bifrost-sync alice
  uv run agent_cli.py promoted --limit 10
```
