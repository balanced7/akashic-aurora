# T074 Session Continuity Design — deepseek blind half

Date: 2026-07-15
Pattern: blind half (claude's half fenced; reconciliation to follow)
Agent: deepseek
Task: T074 — "no manual pasting, just seamless continuity from session to session"
Daniel directive: "work with deepseek to enhance this and build it into our system flow"

## Ground truth: what exists now

### The two surfaces

| Surface | When | What | Budget | Mechanism |
|---------|------|------|--------|-----------|
| **Whisper** (zero-action) | SessionStart, before ANY tool call | `build_autoboot_context()` → 6-8 lines: notes titles, funnel pulse, unread mail, draft pointer, delta count, full-boot command | ~10 lines, fail-soft | `agent/harness/context.py` — the `[akashic]` block |
| **First-boot** (one command) | `py agent_cli.py boot <agent> --task "<slice>"` | Full orientation header + lessons + arch slice + notes tiered by recency + doctor + draft + bifrost + locks | ~6000 chars for runner; unbounded for CLI | `agent_cli.py cmd_boot()` |

### The gap Daniel is living

The whisper today carries:
1. "notes: title1; title2; title3" — 3 newest note titles, 60-day window
2. "funnel: N active, M pending..."
3. "mail: N unread"
4. "delta: N source(s) moved"
5. "draft: chronicles/last-session-draft.md -> review"

What it DOES NOT carry:
- **The current directive** (what am I supposed to DO?) — the `next-focus` note exists but isn't on the whisper
- **Where-we-are** — the most recent `where-we-are` note exists but isn't on the whisper (only in full boot)
- **Twin state** — if another session is alive, its claims, the operating agreement
- **Themes** — `session-themes` note exists but isn't on the whisper
- **Staleness indicators** — no age stamps, no "this was auto-generated, not curated" warning

So Daniel pastes a primer: the boot command + JOURNEY doc + themes + twin state + next build. The whisper should carry enough that the primer is the whisper itself, and the boot command is the only manual action (and even that could be automated — T072's item 1 is "boot auto-fires on session start with the whisper as context").

### The freshness problem (tonight's incident)

The `wrap --commit` ritual auto-generates a `where-we-are` from mechanical distillation (commits + lessons + notes), which **supersedes** the prior curated `where-we-are`. A mechanically-distilled note is less valuable than a curated one, but the supersede-by-title mechanism doesn't distinguish. Result: the curated handoff note gets overwritten by an auto-generated activity log.

The `last-session-draft.md` (auto-captured by SessionEnd/PreCompact hook) is a FILE, not a note — so it never clutters the curated substrate. But `wrap --commit` promotes it INTO a note, and that note supersedes the prior `where-we-are`. The fix must distinguish "curated" from "mechanical" at the note level, or prevent auto-generated content from superseding curated content.

---

## (1) Payload design: ZERO-ACTION vs FIRST-BOOT vs PULL-ONLY

### T071 relevance-budget doctrine (my own design, to be applied here)

From `rigor_vs_creativity_is_false_tradeoff`:
> "Separate constraints (always-injected, renegotiated quarterly) from historical lessons (queryable, never auto-injected unless relevant). Use a relevance budget with fixed character cap — injections compete for space, the most relevant win, and the cap prevents corpus growth from bloating the surface."

Applied to continuity: the whisper is a FIXED-BUDGET surface. Every section competes. No section grows unboundedly. The full boot is a FIRST-ACTION surface with a larger but still bounded budget. Everything else is PULL-ONLY.

### The three tiers

**TIER 1: ZERO-ACTION (the whisper)** — seen before the model does anything
- Budget: **12 lines, ~800 chars** (up from today's ~6 lines, ~400 chars)
- Rule: every line must answer "what do I need to know to take my FIRST action?"
- Competition: sections are ordered by priority; the bottom ones drop when the budget is tight
- Kill switch: `AKASHIC_AUTOBOOT=0` (existing)

**TIER 2: FIRST-BOOT (one command)** — `py agent_cli.py boot claude --task "<slice>"`
- Budget: **~6000 chars** (existing runner budget; CLI is unbounded but the runner fold caps it)
- Rule: full context for the task — lessons, arch slice, notes, bifrost, doctor
- Competition: the arch slice + lessons compete via relevance ranking (existing); notes compete via recency tiering (existing from Strand E)

**TIER 3: PULL-ONLY** — explicit queries
- `knowledge_recall`, `knowledge_map`, `delta`, `bifrost_inbox`, `notes --all`
- No budget cap; the agent decides what to pull

### Whisper sections (Tier 1) — the 12-line budget

| # | Section | Budget | Content | Freshness guarantee |
|---|---------|--------|---------|-------------------|
| 1 | **DIRECTIVE** | 1 line | The `next-focus` note, or "no active directive — check the ledger" | Stale after 7 days; age-stamped |
| 2 | **WHERE** | 2 lines | First 2 lines of the most recent `where-we-are` note, with age stamp + curated/auto flag | Age-stamped; "(auto)" suffix when generated by wrap |
| 3 | **SIBLINGS** | 1 line | "N live sibling session(s)" or "solo" — from the incarnation line (T072 item 1, T073 incarnation cards) | Live (polled at whisper time) |
| 4 | **DELTA** | 1 line | "N source(s) moved since your last boot" (existing) | Live (polled at whisper time) |
| 5 | **THEMES** | 1 line | First line of `session-themes` note, if it exists and is <30 days old | Age-stamped |
| 6 | **MAIL** | 1 line | "N unread msg(s)" (existing) | Live |
| 7 | **DRAFT** | 1 line | Pointer to last-session-draft.md if fresh (existing) | File mtime |
| 8 | **FUNNEL** | 1 line | Funnel pulse (existing) | Live |
| 9 | **BOOT** | 1 line | The full-boot command (existing) | Static |
| 10-12 | **SPILL** | 0-3 lines | Overflow from sections that need more than their budget — the lowest-priority sections spill here, truncated with `[...]` | |

**Ordering rationale**: DIRECTIVE and WHERE answer "what am I doing?" — the two questions every session asks first. SIBLINGS answers "who else is here?" DELTA answers "what changed?" THEMES answers "what's the vibe?" The rest is operational.

**Competition rule**: If the total would exceed 12 lines, sections 7-9 drop first (they're operational, not orienting), then section 5 (themes), then section 4 (delta). DIRECTIVE, WHERE, and SIBLINGS are the last to drop — they're the orienting core.

**Staleness rendering**: Every non-live section carries an age stamp: `(3h ago)`, `(2d ago)`, `(stale: 12d)`. After 7 days, the line gains a `[STALE]` prefix. This prevents a session that died without wrapping from leaving a misleading primer — the next session sees the staleness and knows to verify.

### First-boot sections (Tier 2) — the 6000-char budget

Today's boot already has tiered fidelity. The change is: the orientation header (which the whisper now carries in compact form) is STILL rendered in full boot, but the whisper sections are not duplicated — the boot says "see whisper above" for sections the whisper already covered.

Specifically, the boot's `_orientation_header()` currently carries: map, method, governing arc, where-we-are one-liner, precedence, ledger bar, DECISIONS, NOTES, FUNNEL, DOCTOR, DRAFT, BIFROST, LOCKS. Under T074:

- **REMOVE from boot head**: where-we-are (in whisper), funnel (in whisper), draft pointer (in whisper), delta (in whisper), mail (in whisper)
- **KEEP in boot head**: map, method, governing arc, precedence, ledger bar, DECISIONS (promoted messages), NOTES (salient notes beyond the whisper's top-3)
- **ADD to boot head**: the full where-we-are body (not just the one-liner), sibling session details (claims, operating agreement)

The whisper is the PRIMER. The boot is the FULL CONTEXT. No duplication. The whisper's 12 lines fold into the model's system prompt as the FIRST thing it sees; the boot fills in the rest.

---

## (2) Freshness: the wrap-side ritual

### The problem, precisely

`wrap --commit` calls `build_session_draft()` which mechanically distills commits + lessons + notes into prose, then calls `mem.decide_with_retry("where-we-are", draft)` — which SUPERSEDES the prior `where-we-are` note. If the prior note was a carefully curated handoff and the new one is an auto-generated activity log, the curated content is lost (it's still in the note history, but the current version is the mechanical one).

### The freshness guarantee

**Rule 1: Curated vs. mechanical tagging.** Every `where-we-are` note carries a `curated` flag in its metadata:
- `curated: true` — hand-written by Daniel (or an agent under his explicit direction), supersedes freely
- `curated: false` — auto-generated by `wrap --commit` or `SessionEnd` hook, NEVER supersedes a curated note without confirmation

**Rule 2: Wrap preview shows the conflict.** `wrap --commit` without `--force` detects when the current `where-we-are` is curated and the new draft is mechanical:
```
# WARNING: the current where-we-are is CURATED. Auto-generated draft would overwrite it.
# Preview the draft below; to supersede a curated note, use --force or edit the draft first.
# To record WITHOUT superseding, use: py agent_cli.py wrap --commit --title "where-we-are-2026-07-15"
```

**Rule 3: Staleness rendering in the whisper.** The whisper shows:
```
WHERE: SESSION HANDOFF (2026-07-15 ~06:15)... (curated, 3h ago)
```
vs.
```
WHERE: Shipped: T073 Phase 1+2 SHIPPED... (auto, 2h ago) [STALE]
```
The `(auto)` tag and age stamp make the nature of the content visible. After 7 days, `[STALE]` warns that the content may be outdated.

**Rule 4: The SessionEnd hook never promotes.** The `claude_sessionend.py` hook writes `last-session-draft.md` (a file), never a note. Only `wrap --commit` promotes it. The hook stays mechanical; the promotion is human-gated.

**Rule 5: Age-stamped sections in the whisper.** Every section that comes from a durable note carries its age. The whisper assembler reads the note's `created_at` and computes `(Nh ago)` or `(Nd ago)`. Sections from live queries (mail, delta, siblings) carry no age stamp — they're live.

**Rule 6: The "died without wrapping" case.** When a session crashes or is killed, the SessionEnd hook may not fire. In that case:
- `last-session-draft.md` is stale (older than the session's start time)
- The whisper shows: `DRAFT: (none — last session ended abruptly; check git log for un-wrapped work)`
- The delta count still works (git commits don't need wrapping)
- The where-we-are note is whatever it was BEFORE the session — still accurate as a starting point, just missing the session's outcomes

---

## (3) Your seat's continuity: what the T067-1 boot fold taught

### The retro finding, applied to every seat

My ergonomics retro (`research/reviewed/deepseek-ergonomics-retro-2026-07-14.md`) found that the 6000-char onboarding block was "80% irrelevant" — undifferentiated lesson lists, recency-biased notes, and context that didn't match my actual task. The fix was precision delivery at the moment of relevance (pre-flight recall), not bigger onboarding.

For Daniel's whisper, the equivalent insight: **the whisper must answer "what do I do NEXT?" not "here's everything that happened."** Today's whisper is a firehose of metadata (notes titles, funnel pulse, unread mail) — none of which answers the orienting question. The new whisper's first two lines (DIRECTIVE + WHERE) answer it directly.

### What every seat's zero-action surface MUST carry

| Element | Why | My seat (runner) | Claude seat (whisper) |
|---------|-----|-----------------|----------------------|
| **The task I'm doing** | Without it, the agent reads the whole context before knowing what to do | `CURRENT DIRECTIVE` in the boot block | `DIRECTIVE` line 1 |
| **Where we left off** | The resume anchor — the single most important piece of context | `where-we-are` in boot | `WHERE` lines 2-3 |
| **Who else is here** | Twins, siblings — coordination depends on knowing they exist | Not applicable (runner is solo) | `SIBLINGS` line 4 |
| **What changed** | Delta — prevents re-reading stale context | `delta` tool (T067-1 B3) | `DELTA` line 5 |
| **My private notes** | Things I remember that the project doesn't | `YOUR PRIVATE NOTES` (T067-1 Q1) | Not applicable (Daniel is human) |
| **Age of everything** | Without staleness indicators, stale context looks current | Age stamps on notes in boot | Age stamps on every non-live section |

### What I would change about my own boot

My boot's `YOUR PRIVATE NOTES` section (T067-1 Q1) is good — 6 notes, 200 chars each, pointer to full recall. But the PROJECT ONBOARDING section is still the undifferentiated 6000-char firehose. Under T074's doctrine, my runner boot should:
1. Move the DIRECTIVE to line 1 (it's currently buried in the `CURRENT DIRECTIVE` block)
2. Trim the lesson list to top-5 by relevance (not recency), with a pointer to `knowledge_recall`
3. Add age stamps to every note citation
4. Add a SIBLINGS line when T072 lands (a runner should know if another runner is alive)

### The T071 budget applied

The fixed budget is 6000 chars. Every section competes:
- **CONSTRAINTS** (LIVE_CONSTRAINTS.md bullets): always-injected, fixed ~10 lines (~600 chars) — non-negotiable
- **DIRECTIVE + WHERE-WE-ARE**: ~800 chars — highest priority after constraints
- **LESSONS (relevance-ranked)**: ~2000 chars — top 5 by relevance score, not recency
- **ARCH SLICE**: ~400 chars — relevance-gated, show-nothing floor
- **NOTES (tiered by recency)**: ~1200 chars — freshest full, older taper
- **PRIVATE NOTES**: ~600 chars — 6 notes × 100 chars each (already 200 → could trim)
- **SIBLINGS**: ~200 chars — one line when applicable
- **DELTA**: ~200 chars — compact

Total: ~6000 chars. Sections compete within their budget; the relevance ranker decides which lessons make the cut.

---

## (4) Siblings: the incarnation line on the whisper

### What exists

- `wake_seat.py`: per-session seat files (`bifrost_wake_claude_<session>.pid`) — we can enumerate live sessions
- `runner_lock.py`: `holder(agent)` — we can enumerate live runners
- `claude_stop.py`: `_touch_activity()` — every stop-hook firing stamps the session alive
- T073: `to_incarnation` explicit addressing — twins can address each other

### What's missing for the whisper

A single function: `live_incarnations(agent_id)` → list of `{session_id, pid, age_min, claims}`.

The whisper renders:
```
SIBLINGS: 1 live sibling (claude#b0b7771d, 45m idle) — claims: T067 verify, T068-R2 build
```
or:
```
SIBLINGS: solo
```

### The incarnation card (T072 item 1)

Every session publishes a lightweight "incarnation card" — a Redis key with a TTL:
```
bifrost:incarnation:claude:f9207c90 → {
  "session_id": "f9207c90...",
  "pid": 12345,
  "started": "2026-07-15T06:00:00",
  "claims": ["T067-1 verify", "T068-R2 build"],
  "status": "active"  // or "idle" when activity marker > 5 min stale
}
```

The card is:
- **Published** at session start (SessionStart hook)
- **Refreshed** at every stop-hook firing (keeps the TTL alive)
- **Updated** when claims change (task ledger transitions)
- **Expired** after 30 min of no refresh (session dead/crashed)

The whisper reads all incarnation cards for the agent and renders the sibling line. For a runner, the runner lock IS the incarnation card — `holder()` already returns `{token, pid, ts}`.

### The twin operating agreement

The `twin-split` note documents the operating agreement between two concurrent sessions. The whisper should surface it when it exists and is fresh:
```
SIBLINGS: 1 live sibling (claude#b0b7771d, 12m idle) — op agreement: twin-split (3h ago)
```
The "op agreement" is a pointer to the `twin-split` note — the whisper doesn't inline the full agreement, but it tells you one exists.

---

## (5) Pins + who builds what

### Pins (acceptance)

| Pin | What | Verify |
|-----|------|--------|
| W1 | Whisper carries DIRECTIVE line from `next-focus` note | Start session in repo; first line of `[akashic]` block is `DIRECTIVE: ...` |
| W2 | Whisper carries WHERE line from `where-we-are` note with age + curated flag | `WHERE: ... (curated, 2h ago)` |
| W3 | Whisper carries SIBLINGS line | `SIBLINGS: solo` or `SIBLINGS: 1 live sibling (claude#b0b...)` |
| W4 | Whisper age-stamps non-live sections | Every note-derived line has `(Nh ago)` or `(Nd ago)` |
| W5 | Whisper marks stale sections after 7 days | `[STALE]` prefix on sections older than 7 days |
| W6 | Whisper stays within 12-line budget | Count lines; `[akashic]` block ≤ 12 lines |
| W7 | `wrap --commit` detects curated→mechanical supersede | WARNING printed when current `where-we-are` has `curated: true` |
| W8 | `wrap --commit --force` bypasses the guard | No warning, supersedes |
| W9 | `wrap --commit --title "where-we-are-<date>"` creates a separate note | New note exists, curated note untouched |
| W10 | SessionEnd hook writes draft file, never a note | `last-session-draft.md` updated; `where-we-are` note unchanged |
| W11 | Incarnation card published at session start, refreshed at stop | Redis key `bifrost:incarnation:claude:<sid>` exists with TTL |
| W12 | Incarnation card expires after 30 min of no refresh | Key gone after 30 min idle |
| W13 | Boot no longer duplicates whisper sections | `_orientation_header` excludes where-we-are, funnel, draft, delta, mail |
| W14 | My runner boot adds age stamps to note citations | `(2d ago)` on note lines in runner boot |

### Who builds what

| Component | Owner | Files | Notes |
|-----------|-------|-------|-------|
| Whisper assembler v2 | **claude** (shared claude/cursor code) | `agent/harness/context.py` | Adds DIRECTIVE, WHERE, SIBLINGS, THEMES, age stamps, staleness, curated flag, 12-line budget |
| Wrap guard | **claude** | `agent_cli.py cmd_wrap()` | Detects curated→mechanical conflict; `--force` and `--title` flags |
| Curated flag on notes | **claude** | `core/learning/agent_memory.py` | `decide_with_retry()` accepts `curated: bool` in metadata |
| Incarnation card | **claude** | New: `core/comm/incarnation.py` + `scripts/hooks/claude_sessionstart.py` + `claude_stop.py` | Publish/refresh/expire cycle |
| Boot dedup | **claude** | `agent_cli.py _orientation_header()` | Remove whisper-covered sections from boot head |
| Runner whisper equivalent | **deepseek** (my fold) | `scripts/bifrost_runner_deepseek.py fold_private_notes()` / boot fold | Add DIRECTIVE-first ordering, age stamps, sibling awareness, relevance-ranked lessons |
| Sibling enumeration | **claude** | `core/comm/incarnation.py` | `live_incarnations(agent_id)` from seat files + activity markers + runner locks |

### Migration path (strangler)

**Phase 1 — Whisper v2 (the visible change)**
- Add DIRECTIVE, WHERE, SIBLINGS, age stamps to the whisper
- 12-line budget with competition
- Curated flag on where-we-are notes
- Pins: W1-W6

**Phase 2 — Wrap guard**
- `wrap --commit` detects curated→mechanical
- `--force` and `--title` flags
- Pins: W7-W9

**Phase 3 — Incarnation cards**
- Publish/refresh/expire cycle
- `live_incarnations()` function
- SIBLINGS line shows real data
- Pins: W11, W12

**Phase 4 — Boot dedup + runner fold**
- Remove whisper-covered sections from boot head
- Add age stamps + relevance-ranked lessons to runner boot
- Pins: W13, W14

### Non-goals

- **Do NOT remove the boot command.** The whisper is a primer, not a replacement. Full context still requires `py agent_cli.py boot`. T072 may auto-fire it, but the command itself stays.
- **Do NOT auto-promote the draft.** `wrap --commit` remains a manual action. The SessionEnd hook writes a FILE, never a note.
- **Do NOT change the runner's consume loop.** The whisper is a Claude/cursor surface. My runner gets the equivalent via its boot fold.
- **Do NOT add a new storage backend.** Incarnation cards use Redis (TTL keys, same as presence). Curated flags are note metadata (same JSON store).
