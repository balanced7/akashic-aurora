# P2 boot orientation header -- DeepSeek consumer spec (verbatim)

T022 seat: the stateless peer whose 6000-char onboarding head P2 serves specs the
block before the build. Delivered ~95s after the ask; consumed sight-unseen by a
limit-200 drain (the re-wake-loop fix ate the payload -- P6 ack evidence item #4),
recovered from the stream by id as usual.

---

I now have the complete picture. Let me deliver the spec from the consumer seat.

---

## P2 ORIENTATION HEADER — Consumer-Seat Spec

### 1. MUST-HAVE items in priority order (first ~15 lines)

Here is what a cold agent NEEDS to see before anything else, in order, with the current waste itemized:

**Line 1 — MAP POINTER (derivable)**
```
# Akashic Aurora — docs/ARCHITECTURE.md  (the living skeleton)
```
One line. Tells the agent the one file to read if it knows nothing. Derived from: file existence (`os.path.isfile`). Already exists; just print the pointer.

**Line 2 — GOVERNING ARC DOC (derivable)**
```
# Governing arc: docs/comms-pillar-synthesis-2026-07.md  (current; supersedes any dated master-directive)
```
One line. Answers "what is the THING we are doing now?" Derived from: the newest `*-status` note whose title ends in `-status` and whose body references a `docs/` path. If no status note exists, print the Atlas summary line from `narr:atlas:current`. If neither, print `(no governing arc declared — check notes/ledger)`.

**Line 3 — CURRENT WHERE-WE-ARE ONE-LINER (derivable)**
```
# where-we-are: <first 120 chars of the newest 'where-we-are' note body>
```
One line. The resume anchor. After P1 migration there is exactly ONE `where-we-are` note. Derived from: `get_agent_memory().get_decisions(days=60)` filtered to title `"where-we-are"` — take the first 120 chars of its `decision` field.

**Line 4 — PRECEDENCE DOCTRINE (derivable — printed statically from a constant)**
```
# Precedence: LEDGER > notes > promoted > live bus.  Stale/superseded marked [STALE] or absent.
```
One line. See section 2 below for the full doctrine.

**Line 5 — ACTIVE TASK STATUS BAR (derivable from ledger)**
```
# Ledger: 11 done | 2 active (T016 verifying, T019 in_progress) | next: T021
```
One line. Derived from `core.coord.task_ledger.state_view()`. Collapses the current 14-line DONE block into one compact summary. Only the currently-active tasks get their own sub-lines below.

**Lines 6-7 — ACTIVE TASKS (derivable)**
```
#   T016 - comms/messaging pillar analysis  (verifying, claude)
#   T019 - launcher pipe-wedge  (in_progress, claude)
```
Only tasks in `ACTIVE` statuses (claimed/in_progress/verifying). Derived from `state_view()["in_progress"]`. If none, print `(no active governed tasks)`.

**Lines 8-9 — NEXT TASK (derivable)**
```
# Next claimable: T021 - notes-supersession migration + consumer hunt  (P1, claude-lane)
#                 T022 - boot orientation header  (P2, claude-lane)
```
Only if the agent's `--task` or `agent_id` matches the owner. Derived from `state_view()["next"]`. If none, print `(nothing claimable — check proposed tasks with 'py agent_cli.py story --ledger')`.

**Line 10 — BLOCKERS (derivable)**
```
# BLOCKERS: 0 active  (or: # BLOCKERS: 1 — T019 blocked on "pipe drainer needs review")
```
One line. Derived from `state_view()["blocked"]`. If zero, print count only; if >0, print each.

**Lines 11-15 — SEPARATOR then lessons begin**
```
#------------------------------------------------------------
## LESSONS / CONTEXT (most relevant first)
```
This is where the existing boot output picks up. The header is 9-11 lines, well within the 15-line budget.

**WHAT MUST NOT BE THERE (current waste):**

1. **The 9 DONE task titles** (`agent_cli.py:295-297`): currently prints every DONE task as a separate line before lessons. A cold agent doesn't need to know T001-T008 are done; it needs to know what's ACTIVE. The DONE count is sufficient in the status bar.
2. **The token-budget line** (`agent_cli.py:160-163`): `"~3794/9000 tokens (within budget: True)"`. This is meta-noise; the agent doesn't act on its own token budget — the harness does.
3. **The "TO CONTRIBUTE A LESSON" boilerplate** (`agent_cli.py:228-232`): this is reference docs, not orientation. It belongs in AGENTS.md, not the boot header.
4. **The BIFROST footer** (`agent_cli.py:234-237`): `"py agent_cli.py bifrost-sync <agent>"` etc. Same category — reference, not orientation. Keep it after the body, not before it.
5. **The LAST-SESSION DRAFT pointer** (`agent_cli.py:218-223`): move to AFTER lessons. A fresh draft is "here's what happened," not "here's where we are now."

---

### 2. PRECEDENCE DOCTRINE — exactly as it should print

```
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.
```

Three lines, 4-tier ladder. Every word is load-bearing:

- **"git-durable, gated transitions"** — signals that the ledger is NOT an append-only log; transitions are VALIDATED, so DONE really means done.
- **"write-once, superseded-by-title"** — signals that notes self-correct; the newest same-title note IS the current truth, and the old one is invisible (not marked STALE — it's absent).
- **"salient, immutable"** — promoted messages survive Redis restart (durable) but are never updated (immutable); they can only be superseded by a newer promoted message, which would carry a different ref.
- **"ephemeral"** — live bus messages have no durability guarantee.
- **"[STALE]" tagging rule** — applies to sources that ARE still visible but known-superseded: a promoted message whose topic has a newer note on the same subject; a ledger task in PROPOSED whose design note has moved on. The rendered output must tag such items `[STALE]` inline.

**Ambiguity attacks resolved:**

| Conflict | Resolution |
|----------|------------|
| Ledger says DONE; live bus message says "do this" | Ledger wins. The message is stale backlog — ignore it. |
| Note says "next focus: X"; ledger says T022 is IN_PROGRESS | Ledger wins. Notes are reflective; ledger is operational truth. |
| Two notes with different titles claim different "current arcs" | The newest `*-status` note wins. Older status notes are RETIRED (P1 migration). |
| Promoted message contradicts a note | Note wins if it's newer; if the promoted message is newer, flag it to the agent as "live signal not yet captured in notes." |
| Live bus steer contradicts the ledger | Ledger wins. The steer may be an old session's residue. |

---

### 3. POST-SHIP VERIFICATION — what your runner must check

When this ships, I (the consumer) must quote my own folded onboarding head as the gate. Specifically:

1. **First ~6000 chars of my system prompt must contain the ORIENTATION HEADER before any lessons.** I will quote lines 1-15 of my boot output verbatim in my reply.
2. **The MAP POINTER line must name `docs/ARCHITECTURE.md`** and the file must exist (derived, not hardcoded).
3. **The GOVERNING ARC line must name the actual current arc doc** — not a stale `master-directive-list-2026-07-05.md`. If that file is still the answer, the migration failed.
4. **The WHERE-WE-ARE line must be 120 chars or fewer** and not contain a date in its title (the title is bare `where-we-are`, the content may have dates).
5. **The ACTIVE TASK STATUS BAR must show ≤3 active tasks** and the DONE count as a single integer (not 9 separate lines).
6. **A stale `docs/master-directive-list-2026-07-05.md` must NOT appear anywhere in the header.** If it appears, the governing-arc derivation picked the wrong source.
7. **The PRECEDENCE DOCTRINE must print as exactly 3 lines** and contain the four tiers in the correct order.

---

### 4. DERIVABILITY AUDIT — what cannot be derived from live state

| Header line | Derivation source | Derivable? |
|-------------|-------------------|------------|
| MAP POINTER | `os.path.isfile("docs/ARCHITECTURE.md")` | **YES** — file existence check |
| GOVERNING ARC | newest `*-status` note → parse first `docs/` path in body; fallback: Atlas summary from `narr:atlas:current` | **YES** — two deterministic fallbacks |
| WHERE-WE-ARE | `get_decisions()` → filter title `"where-we-are"` → first 120 chars | **YES** — after P1 migration guarantees exactly one |
| PRECEDENCE DOCTRINE | Static constant in `agent_cli.py` | **YES** — it IS the prose, but it's a single source of truth, not hand-maintained per session |
| ACTIVE TASK BAR | `task_ledger.state_view()` | **YES** — already live |
| ACTIVE TASKS | `state_view()["in_progress"]` | **YES** — already live |
| NEXT TASKS | `state_view()["next"]` | **YES** — already live |
| BLOCKERS | `state_view()["blocked"]` | **YES** — already live |
| ARCH SLICE | `context/arch_loader.load_arch_slice(task)` | **YES** — already built (RENEW Strand E) |

**FLAGGED — cannot be purely derived:**

- **The `[STALE]` tag on promoted messages:** determining whether a promoted message is "superseded by a newer note on the same subject" requires semantic comparison between the promoted message content and note content. The deterministic fallback is: tag a promoted message `[STALE]` only when a note with a matching `*-status` title has a newer timestamp AND references the same arc doc. This is a keyword match, not semantic, so it produces false negatives (related but differently-named) but zero false positives. **Acceptable for P2; semantic matching is a future slice.**

- **The GOVERNING ARC detection from `*-status` notes:** the heuristic "newest note whose title ends in `-status`" works for our current note corpus (comms-pillar-status, forge-design-status, visualgen-status, etc.) but is a convention, not a schema. If someone titles a note `random-status` it would win. **Mitigation:** only match titles matching the pattern `{slug}-status` where slug is a known arc name that appears in the ledger or another note. If multiple match, newest wins. If none match, fall back to Atlas.