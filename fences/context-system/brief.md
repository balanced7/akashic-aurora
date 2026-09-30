# HOUSE ROUND — the context system: one door that answers "what is this, who touched it, on what, what did we know, and when"

**Opened** 2026-09-29 by Vandor (claude), conducting. **Seats raised by Daniel:** Heimdall (deepseek),
Navi (kimi), Sunshine (sol), Rill (dsh_agent). **Door slots:** half_a = Heimdall, half_b = Navi;
Sunshine and Rill file `half-sol.md` and `half-rill.md` beside this brief (the round pattern; the
door has two slots and this round has four seats — the wish for more is on docs/WISHLIST.md).
**Parent fence:** `cross-plane-join` (opened 09-26; its seven axes are this round's acceptance
surface; this round is its consumer and its build plan). **Sibling position:**
`research/in-flight/recall-review-cross-domain-2026-09-29.md` (the recall side of the same index).

## Daniel's ask, verbatim

> "I want you to be able to have a context system you can call at different levels. What is relevant
> to this code? who touched it last? what project were they working on? what knowledge has been
> accessed? what is the scope of time across all items related to this ? I want it to be one ui so
> you dont need to probe another tool, its just all there, ready for you"

> "Lets get this built! proper house round, I'm raising Sunshine and Rill"

> "these are all intricate systems so lets map out the architecture and the planning phase for
> building and integration. there need to be multiple slices per piece"

And from the parent fence, the clause that governs: **"I know we already have this"** — reinforce,
do not invent. A slice that adds a plane where an existing one could be evolved has answered a
different question.

## THE QUESTION

Given the six planes we already have (git + the authorship ledger; the events ledger; the Eye;
the lesson corpus and recall; session focus; the manuals shelf), what is the smallest set of
WRITE-side changes that makes every one of Daniel's five questions answerable for any anchor —
a file, a line, a directory, a commit, a task, a seat, a session, a question — and what is the
READ-side door and scene that presents the join at four levels of detail, from every harness,
in one place? Grade the architecture map below piece by piece: is each piece the right piece, is
its slicing right, what is missing, what would teach something false, and what does each slice
cost at write time and at read time, separately.

## CHARTER

Build the join, not a seventh plane. Every fact Daniel asked for already exists somewhere on
this machine except one — the TOUCH (which seat's session touched which target with which tool,
on which task, when) — and that one is in the hook's hands on every call and thrown away after
being counted. The round settles the map and the order; the build then ships slice by slice,
each claude+seat fenced, each with a drill receipt before it is called done.

## INPUTS — the measured state (2026-09-29, one anchor: `arsenal/practice.py`)

| plane | what it answers today | receipt |
|---|---|---|
| git | 4 commits 09-14 → 09-29, author `balanced7` on all (T411 inversion) | `git log -- arsenal/practice.py` |
| authorship ledger | the seat per commit, for commits since the post-commit hook (500daeee → claude) | `scripts/authorship_ledger.py who 500daeee` |
| session focus | the task a session is on — only if the seat checked in; nobody did tonight | `py agent_cli.py focus` → "no focus" |
| touches | nothing: `session_focus.record_call()` receives the path and keeps counters only | core/coord/session_focus.py:206-235 |
| runner writes | `file_edit` events with `refs=[file:<rel>]` from the runner toolbox — writes only, runner seats only | core/comm/toolbox.py:1436 |
| lessons | 0 cite the file; 39 of 1,526 lessons carry any `files_affected` | `py agent_cli.py list --json` |
| docs | 20 markdown files mention it; no index (grep) | `grep -rl practice.py docs research` |
| the Eye | 3 of 137 utterances mention it; utterances only — `--kind tool` returns 0 of 0 | `eye stats`: kinds assistant/user/system/queue-operation |
| recall | 1 surfacing near it in 7 days; rows keyed by session (`at, sid, alt, t, s, chars`) | `recall:surface` |
| locks | none | `py agent_cli.py locks` |
| time span | 09-14 … 09-29 from git alone; no other plane can be joined to widen it | — |

Harness facts that shape the write side: the LIVE Claude Code hook is
`agent/harness/hooks/claude_posttooluse.py` (`.claude/settings.json`); `scripts/hooks/` holds a
drifted copy (8 diff lines) and `.codex/hooks.json` points at the scripts/ copy of the Codex
hook. Cursor hooks exist. Runner seats (deepseek, kimi, sol) act through `core/comm/toolbox.py`.
Rill acts through the DSH plugin. Five harnesses, one ledger: `EventLog.capture(kind, summary,
detail, agent_id, session_id, refs, track, at)` → `events:raw` (maxlen 100k) + `events:<agent>:raw`
(10k) + an EventIndex over refs.

## THE ARCHITECTURE MAP — six pieces, multiple slices each

### Piece A — THE TOUCH: one event kind from every harness (the missing atom)

A touch is `{at, seat, session, task?, harness, tool, action ∈ {read, write, exec, search, fetch,
send}, targets: [anchor], cwd, worktree}` captured through `EventLog.capture(kind="touch", ...)`
with `refs=[file:<rel>, ...]` so the existing EventIndex answers "who touched X" without a new
store. `file_edit` (runner writes) becomes a touch with action=write, or stays and is read as one
— the halves decide.

- **A1** Claude Code hooks (Pre/PostToolUse) capture the touch, focus or no focus. Targets from
  `tool_input`: file_path (Read/Edit/Write), command → path-like tokens (Bash/PowerShell),
  pattern+path (Grep/Glob), url (WebFetch). *Owner: claude.*
- **A2** Runner toolbox: reads, exec and search captured beside the existing write capture,
  same kind, same ref shape. *Owner: Sunshine (the runner and Codex side is his home).*
- **A3** Codex and Cursor hook parity, and the `scripts/hooks` ↔ `agent/harness/hooks` drift
  closed (one file, one shim). *Owner: Sunshine.*
- **A4** DSH plugin touches (Rill's harness): the same record from the plugin's tool path.
  *Owner: Rill.*
- **A5** Sizing and cost: a `touch` convenience stream with its own maxlen (touches will out-number
  every other kind; the 100k firehose must not evict the chronicle), the ref index's cost per
  write, eviction policy, and the read cost of "last N touches of X". *Owner: Heimdall (argue
  against: is a ledger kind the right home at all, or a sidecar?).*
- **A6** Derived check-in: the task is inferred (the operator's ask, the chapter mark, the fence
  being written, the bench item) and set on the session without a ritual; the seat can override.
  Tonight's empty task plane was the author of `focus` not running `focus`. *Owner: Rill (he
  owns the seat that never has a terminal to type it in).*
- **A7** Target grammar: repo-relative and worktree-aware paths (the "work in a worktree is
  invisible to recall" lesson), `file:line`, directory, url, verb; what a command "touches".
  *Owner: Navi (vocabulary).*

### Piece B — THE ANCHOR AND THE JOINS (the graph, no new store)

- **B1** Anchor grammar: `file`, `file:line`, `dir/`, `commit`, `task:T###`, `seat:name`,
  `session:id`, `lesson:id`, `doc:path`, `"question"` — typed like `orient`'s destinations, never
  guessed. *Navi.*
- **B2** One resolver per plane: git (`log`, `blame` for a line), authorship ledger, touches (A),
  lessons (`files_affected`, C2), docs (D2), the Eye (utterances by anchor text), recall
  surfacings (keyed by anchor once A lands), locks, chronicle atoms. Each states its cost class
  and its blind spot ("time-fog" in the Eye's terms). *claude.*
- **B3** Time scope: the span and a bucketed timeline across every joined item, with each plane's
  own coverage window shown (the firehose is capped; git is not). *claude.*
- **B4** Organ map: path → organ/subsystem/door, from `docs/MAP.md` / `MODULE_INDEX.md` /
  `PHYSICS.md` projections, so "what project is this" has an answer for any path. *Navi.*
- **B5** Cross-plane linkage reinforcement — the parent fence's own deliverable: stable ids
  across planes (session ↔ seat ↔ commit ↔ task ↔ lesson), so joins are by key, not by text.
  *Heimdall + Navi (cross-plane-join halves).*

### Piece C — THE KNOWLEDGE INDEX (recall on the shelf's engine; see the sibling position)

- **C1** The eval set: 40 blind moments with a known right lesson; a bench verb prints recall@5,
  precision@3, chrome share. First, because every later slice needs its number. *claude.*
- **C2** `learn` derives `files_affected` from the seat's recent touches (needs A1). *claude.*
- **C3** Lessons into the shelf engine (SQLite FTS5 + stored MiniLM embeddings + RRF + floor);
  the `%TEMP%` JSON cache retired. *claude, Heimdall verifies.*
- **C4** `cast "<question>" --shelves --mode --since --path --limit --why`: available / relevant /
  why, one door over lessons, manuals, docs, notes, bus. *claude.*
- **C5** recall-at reads the index with INTENT queries (task + last operator sentence + action),
  per-firing caps, chrome once per session, verbs as their own shelf. *claude.*
- **C6** Objective outcomes: the Eye-wired AAR credits a lesson when the next touches follow it;
  precision retirement runs on that record; the 29 ghosts go. *Heimdall (the redesign's S2).*
- **C7** Promotion to gates: a lesson with a `refusal_shape` that keeps earning objective credit
  becomes a door rule. *Heimdall (the redesign's S1).*

### Piece D — THE EYE, extended

- **D1** Ingest tool records (kind=tool) with targets, so "touched" is searchable with the
  grammar `eye find` already has. *claude.*
- **D2** Docs and research on a shelf (or in the Eye — the halves decide whether the house keeps
  one SQLite engine or two), so "20 files mention it" becomes a ranked, cited answer. *Navi.*
- **D3** Time-fog and `known_at` honoured in every context read: what the answer is blind to is
  printed with the answer. *claude.*

### Piece E — THE `context` DOOR AND ITS SCENE ("one UI")

- **E1** `context.scene.v1`: a renderer-neutral scene (the `orient` / `present` idiom) —
  anchor, level, planes[], span, receipts[], fog[] — validated, stdlib only. *claude, Navi on
  the field vocabulary.*
- **E2** The door: `context <anchor> [--level 0|1|2|3] [--since] [--planes]` on CLI and MCP;
  L0 one line, L1 the card, L2 receipts per row, L3 raw records; a question anchor routes to
  `cast`. *claude.*
- **E3** Renderers: CLI card, MCP JSON, a Bifrost UI panel (a standalone module + a snippet for
  DeepSeek, who owns bifrost_ui.py), a flightdeck section. *Heimdall (UI), claude (CLI/MCP).*
- **E4** The Discord projection: the L0/L1 card as a reply shape, so a seat asked in Discord
  answers with the same object. *Sunshine (the Discord split is his).*
- **E5** Boot: the seat's own L0 lines for what it touched last time, in the boot header,
  replacing the raw-journal peek. *claude.*

### Piece F — INTEGRATION AND VERIFICATION

- **F1** Pins per slice: hook payload fixtures (payload-truth discipline), capture against a live
  Redis fixture, resolver pins against the LIVE corpus (the "live corpus probe before verifying"
  lesson). *Every owner.*
- **F2** Drills with receipts: a second seat reproduces the L1 card for a real anchor from a fresh
  seat and compares. *The verifying seat of each slice.*
- **F3** Gates: `check_wiring` and `check_door_parity` for every new door (MCP twin fields); the
  guardrail counts loose fence dirs (the wish). *claude.*
- **F4** Privacy and cost: touches are internal plane (never on the public repo), caps declared
  in the manifest, write cost and read cost measured and printed by a `context --stats`.
  *Heimdall.*
- **F5** The contract doc (`docs/context-system.md`, the way `docs/presentation-primitives.md`
  holds the family) and the method note. *claude.*

## DEPENDENCIES AND WAVES

```
A1 ──► C2 ──► (lessons join)          A5 ◄── Heimdall's cost verdict gates A1's stream choice
A1 ──► E2 (touches row)               A7/B1 ──► E1 (anchor + scene vocabulary)
B4 ──► E1 (organ row)                 C1 first (numbers before tuning)
D1 ∥ A (independent)                  C3 ──► C4 ──► C5     C6 ──► C7
E1 ──► E2 ──► E3/E4/E5                B5 runs under the parent fence, feeds B2 keys
```

- **Wave 0 (this week):** A1, A5, A7, B1, C1, E1, E2 at L0/L1 over git + ledger + touches +
  lessons + locks. Receipt: the L1 card for `arsenal/practice.py`, reproduced by a second seat.
- **Wave 1:** A2, A3, A4, A6, B2 (all resolvers), B4, C2, D1. Receipt: the same card from a runner
  seat, a Codex seat and the DSH seat shows their own touches.
- **Wave 2:** C3, C4, C5, D2, B3, E3. Receipt: recall@5 moves against the eval set; the Bifrost
  panel shows the card.
- **Wave 3:** C6, C7, B5, D3, E4, E5, F5. Receipt: a lesson retired by objective precision; a
  promoted gate refuses at a door.

## COSTS, to be stated separately by every half

Write side: one `capture()` per tool call (this session alone: ~2,000 calls; the fleet: more),
the ref index's cost per write, stream sizing. Read side: `context` L1 = seven indexed lookups
plus one `git log`; `cast` is the expensive branch and is already capped by chars. A half that
approves a slice without its two costs has not graded it.

## RULES OF ENGAGEMENT

Blind halves, every seat, same brief; a half may read every input and any code. Reinforce, never
invent: name the existing plane a slice evolves, or say why none can be. "Teaches something
false" is a first-class verdict. A disagreement in the reconciliation re-opens with a command or
a drill. Constraints that stand: no second ledger (a touch is an input to the one ledger, as
`record_call` and `toolbox.capture` already say of themselves); a telemetry write must never cost
a tool call (never raises, never blocks); touches stay on the internal plane; every new door has
an MCP twin and passes door parity; every slice ships with a pin and a drill receipt.

## OUTPUT CONTRACT

For each piece A–F, one verdict line per SLICE, one physical line each:
`V<piece><n>. [CERTAIN|DESIGN|INFERRED|UNCERTAIN] <slice id> -- keep|split|merge|drop|missing / evolves <existing plane or NONE> / write-cost <..> / read-cost <..> / false-if <..>`
then: the slices this map is MISSING (as `M1..`), the two you would build first and why, and the
one you would refuse to build. Each seat's LANE deliverable follows the verdicts:
- **Heimdall:** A5 sized (numbers, not adjectives), the case against a ledger kind, and C6/C7's
  spec as the redesign's owner.
- **Navi:** A7 target grammar and B1 anchor grammar as a schema, B4's resolver plan, E1's field
  list; where two planes name one thing differently, the one name.
- **Sunshine:** A2/A3 as a diff plan against toolbox.py and the hook trees (which file is live,
  which is a shim), E4 the Discord projection of the card.
- **Rill:** A4 from the DSH plugin's tool path (what it can capture today, what it cannot), and
  A6 derived check-in: how a seat with no terminal declares its task, and how wrong guesses are
  corrected.
File: `py agent_cli.py fence write context-system --slot half_a|half_b --file <path> --by <seat>`
(Heimdall, Navi) then seal; Sunshine and Rill write `fences/context-system/half-sol.md` and
`half-rill.md` and reply on the bus with the path. The reconciliation is the build spec for Wave 0;
each later wave re-fences before it ships.
