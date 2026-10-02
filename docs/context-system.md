# The context system

Status: current · Type: contract · Arc: context-system · Seats: fleet (claude builds Wave 0; Navi
authors the schema and verifies blind; Heimdall prices the ring; Sunshine pins redaction and
reproduces the card; Rill owns Gap 5)

**What it is.** One canonical key for a location, one record of what touched it, and one door that
answers for it across every plane. Build spec: `fences/context-system/reconciliation.md` section 4,
as folded by `fences/one-spine/reconciliation.md`. Schemas: `research/in-flight/context-system-navi-m1.md`
(amended by `-m1-amendment-1.md`) and `-m2.md`.

**What it is for**, in Daniel's words, and this is the acceptance test on every slice below:

> "when the design is finished I won't have to remind you whats related to what and the importance
> of it, you will be able to see it."

---

## The five questions, and which plane answers each

| Question | Plane | State today |
|---|---|---|
| What did the code do here? | `git` | **live** — `git log` for the path, each row a `sha:` ref |
| Who touched this, and in which incarnation? | `touches` | **live** — `events:raw` filtered by the typed key |
| What did we learn about it? | `lessons` | not joined — lessons key on `files_affected` and 39 of 1,526 carry one |
| Who wrote it? | `authorship` | not joined — needs the ledger's rewrite-stable key (Heimdall's B5.3) |
| Who is holding it right now? | `locks` · `focus` | not joined — both key on their own path spellings, which is what W0.1 exists to unify |

A plane that cannot answer says `UNCHECKABLE` **with its reason**, never zero. That distinction is
the system's whole point; see "the four states" below.

---

## The three schemas

### `context.target.v1` — the key (W0.1, `core/coord/target.py`)

Any spelling of a location resolves to one string. Repo-relative, backslashed absolute, slashed
absolute and drive-case variants all collapse; a worktree carries `work:<name>:`; a directory is
marked by its trailing slash and only by that; `path:line:col` are separate fields and the colon
string is input and display only.

- **Ref kinds, closed at eight:** `event:` `sha:` `task:` `lesson:` `mem:` `doc:` `session:` `seat:`.
  Aliases rewrite at parse: `commit:`→`sha:`, `git:`→`sha:`, bare 40-hex→`sha:`,
  `learn:experiment:`→`lesson:`, `file:`→the path anchor.
- **Opaque, joinable but not parsed:** `bifrost:` and `blob:` — real keys the by-reference index
  uses, deliberately outside the grammar.
- **Worktree naming is collision-only:** the bare git leaf when unique, `parent-leaf` when it
  collides (48 worktrees share the leaf `shadow` today), and a loud refusal when the parent cannot
  break it either. An order-dependent key is not a key.
- **Columns carry a unit:** `utf16CodeUnits`, declared, because SARIF, LSP, GCC and git grep each
  count a column differently and an undeclared one cannot join.

### `touch.v1` — what a seat touched (W0.2, `core/events/touch.py`)

One record per tool call from the PostToolUse hook, on `events:raw`, carrying typed targets and the
**session id from the payload** (env is only the fallback, and the source rides along). It absorbs
Gap 3 of the record-is-total map: a hook firing *is* the idle-to-active transition, so there is no
separate `activity` kind — one fact on the spine twice would be a second writer.

`targets: null` means the command could not be seen into (a script on stdin, a command
substitution). `targets: []` means it was read and touched nothing. Both carry
`targets_incomplete`; collapsing them is the failure this system exists to end.

**Both hook copies carry it.** User settings invoke `scripts/hooks/`, project settings invoke
`agent/harness/hooks/`, and the wiring gate deliberately does not walk the first. Patching one ships
to half the fleet, invisibly; a parity pin holds them together.

### `context.scene.v1` — the answer (W0.5, `core/coord/scene.py`)

One anchor across every plane. Fields: `schema`, `subject`, `anchor`, `level`, `generated_at`,
`planes[]`, `span`, `fog[]`, `epistemic`, `drill`, `effects` (always `[]`, because a context read
performs none and the field exists to say so).

**The four states, which are the point:**

| State | Means |
|---|---|
| `ok` | asked, joined, has rows |
| `empty` | asked, and there genuinely is nothing |
| `UNCHECKABLE` | could not ask — **the reason is required**, or the state decays into a silent zero |
| `error` | asked and it broke, with the exception in the fog line |

Three rules hold that shape: **a plane is never absent** (a missing plane is indistinguishable from
one that does not exist); **every row carries a ref the doors resolve**, and a row that cannot mint
one moves to `fog` by name, because a row you cannot follow is a claim you cannot check; and a
resolver that raises becomes an `error` plane rather than a hole.

---

## The doors

| Command | What it does |
|---|---|
| `py agent_cli.py context <anchor> [--level 0\|1\|2]` | the scene. L0 summaries, L1 rows, L2 receipts |
| `py agent_cli.py context --stats [--hours N]` | the instrument (W0.4) |
| `py agent_cli.py recall-bench [--limit k]` | grade recall against the answer key (W0.3) |

All three are on the CLI, the MCP door and the ToolBox, because an instrument only a shell-holder
can read belongs to whoever happens to have a shell.

## The ring, and what it costs

Touches ride the existing `events:raw` firehose (maxlen ~100k) — no second store, no second writer.
Retention is measured rather than assumed: `context --stats` reports the oldest record's age and
**flags when the window asked for is longer than the ring reaches**, because every rate over such a
window is a floor rather than a measurement. Heimdall rules A5b (shared firehose or its own ring)
on 24 hours of that number, which is why W0.4 shipped the same night as the emit.

Two figures the instrument reports as `UNCHECKABLE` rather than estimating: p95 hook latency
(nothing stamps a duration yet) and anchor resolve cost (W0.6's timing is not instrumented). An
invented number is worse than an admitted hole, because the invented one gets quoted.

---

## Wave 0, and what remains

| Slice | What | State |
|---|---|---|
| W0.1 | `context.target.v1` | **done** `653b5723` |
| W0.2 | the touch, with session id | **done** `f9a1bbe2` |
| W0.2a | Gap 2: phase changes on the spine | **done** `a41ce48b` |
| W0.2b | Gap 4: expected / retract / revoke (= T424) | Heimdall builds, claude reviews blind |
| W0.2c | Gap 1: wire metadata | **blocked** — the record's whole body-derived half has no writer; the call-site writer lands first |
| W0.2d | Gap 5: the machine's own change journal | Rill owns it, from his 2026-09-24 design |
| W0.3 | `recall-bench` and the answer key | **done** `e0d9f0f6` — 4 of 40 moments seeded, 36 commissioned blind |
| W0.4 | the instrument | **done** `39ddc412` |
| W0.5 / W0.6 | the scene and the door | **done** `04daf044` — 2 of 6 planes live |
| W0.7 | this document | **done** |

**The two numbers Wave 0 can be judged on**, both re-runnable:

- session coverage, `context --stats`: **12.3%** (51 of 415 in 24 h). It was 89 of 6,918, all of one
  kind, before W0.2.
- recall, `recall-bench`: **0%** at both @1 and @5 over the seeded moments. That reproduces the
  2026-08-08 misses dossier mechanically, two months on.

**Standing decisions carried from the rounds:** no second ledger or capture path · the session id is
forwarded on every capture in the hook path · one engine for docs and lessons · promotion to gates
is never automatic · the spine carries pointers and never bodies (Daniel's D1) · map before weld
(D2) · and one spine with the plane kept legible **on** it, because Daniel's 2026-08-07 ruling was
"there should be both flavors in the system" and cross-matching what one plane knows and another
does not is a goal rather than an accident of having several stores.
