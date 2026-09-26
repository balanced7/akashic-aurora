# FENCE BRIEF — cross-plane join: triangulating provenance, meaning and influence

**Fence:** `cross-plane-join` · **Tier:** full · **Opened by:** claude, 2026-09-26
**Halves:** `half_a` = Heimdall (deepseek) · `half_b` = Navi (kimi) · **Reconciler:** claude

---

## 1. The question at stake

Daniel's ask, **verbatim** — this is the charter, not a paraphrase:

> "also we should have important records linked and synchronized in a way that each pillar can be
> used to identify the failure in itself or other pillars. I know we already have this, how do we
> further reinforce it in a reliable and performant way so we increase the indexable surface area
> of our tools. I want us to be able to triangulate quickly between things, meanings, patterns the
> why, provenance, who did what at what time, what was it influenced by. I want us to have quick
> access to in depth analysis"

Two clauses govern the design and are easy to skim past:

- **"I know we already have this"** — he is asking to REINFORCE, not to invent. A proposal that
  builds a new plane when an existing one could be evolved is answering a different question.
- **"reliable and performant"** — both, as constraints, not aspirations. State the cost of your
  design at write time and at read time separately.

**The seven axes he named.** Treat these as the acceptance surface; a design that leaves one with
no join has not answered:

| axis | the question a seat would ask |
|---|---|
| things | what artifact is this — file, commit, atom, task, message |
| meanings | what is it FOR; what does it mean in this system |
| patterns | has this shape happened before, how often, and did it recur after we learned |
| the why | what ruling, directive or reasoning produced it |
| provenance | which seat, which session, which harness |
| who did what at what time | authorship in time, ordered, across seats |
| what influenced it | which lesson fired, which brief, which prior art, which peer |

---

## 2. What each half must produce

Write to your slot as a single markdown document. Structure it exactly like this so the
reconciliation can diff you against the other half claim-for-claim.

1. **VERDICT ON THE FRAMING.** Before designing: is this brief asking the right question? Is the
   evidence pack below measuring the right things? If the framing is wrong, say so first and say
   what the right question is. This section may be the most valuable thing you write.
2. **THE DESIGN.** What to add, what to change, what to leave alone. Name real files and real
   functions. A design that cannot be pointed at a file is not yet a design.
3. **ORDERING, WITH THE REASON.** What must land first, and specifically: does any piece PRODUCE
   the fuel another piece BURNS? That dependency is a finding in its own right — state it even if
   it feels obvious, because the reconciler may be the only one positioned to see it.
4. **WHAT YOU WOULD NOT BUILD, AND WHY.** This house over-builds organs and under-wires them. A
   named non-goal is worth as much as a feature.
5. **THE CHEAPEST EXPERIMENT THAT WOULD FALSIFY YOUR OWN DESIGN.** One command or one small
   measurement. If you cannot name one, say so and explain why the design is unfalsifiable.
6. **COST.** Per-write cost, per-read cost, storage growth, and what happens at 10x the current
   corpus. The read path is the one that must be fast; the write path is where cost is acceptable.
7. **WHAT YOU COULD NOT CHECK.** Anything you assumed, inferred, or ran out of reach for. An
   honest UNKNOWN is a contribution; a confident guess is a liability the reconciler must catch.

### How to work (process, not posture)

- **Reason from the records, not the docs.** Docs in this repo rot and several are auto-generated
  projections. Read the actual stored records and the actual code. Where a docstring and a record
  disagree, the record wins and the disagreement is a finding.
- **Every claim carries a `file:line` or a runnable command.** A number without a reproducible
  command cannot be reconciled against the other half.
- **Refute actively, including your own first idea.** Rank what you report by load-bearing-ness:
  the thing that changes the design over the thing that is merely true.
- **Prefer evolving an existing door to adding one.** If you propose a new organ, first show which
  existing organ cannot be extended and why. This house's own ruling: gate evolution beats a new
  organ.
- **An honest undirected answer beats a confident wrong arrow.** If the evidence does not
  determine a choice, say the choice is undetermined and name the measurement that would settle it.
- **You are ONE OF TWO BLIND HALVES.** Do not try to guess what the other half will say, do not
  hedge toward a middle, and do not soften a position to be reconcilable. Divergence between you
  is the product of this fence; agreement reached by mutual anticipation is worthless.

On this Windows host: use `py`, not `python`. `Glob` returns EMPTY on `E:\` paths — use Grep,
Bash/git/rg, or PowerShell. Read-only is expected; if your investigation would write anything,
describe it instead.

---

## 3. Evidence pack — measured 2026-09-26, reproducible

Everything in this section was run, not recalled. Commands are given so you can re-run any of it,
and you should re-run anything a design decision rests on. **Two of my own earlier claims were
overturned by these measurements** — noted inline — so treat the pack as fallible.

### 3.1 The edge graph already exists, and it is typed

`py agent_cli.py eye trace --help` — walks a connectome with **eight edge kinds**:

```
fence · recall-firing · fan · supersession · manual · transcript · text-identity · adjacency
```

Its own docstring: *"Every edge states HOW it is known — recorded (the harness wrote the link),
derived (same utterance, by text), inferred (adjacency)."* So provenance-of-the-edge is already a
first-class concept.

**Its only entry point is an Eye event address (`session:line`).** You cannot trace from a commit,
a file, a task, a wish, a lesson, or an atom.

### 3.2 A typed-ref join exists on the event plane, and is better filled than it looks

```bash
py agent_cli.py events --limit 3000 --json
```

- `refs` non-empty on **761 / 3,000 (25.4%)** — but **100% on every kind that emits refs at all**:
  `learning` 235/235, `decision` 118/118, `expectation_settled_answered` 103/103, `file_edit`
  91/91, `bifrost_msg` 72/72, `command` 35/35, `ask_completed` 29/29, `note` 17/17.
- Kinds that emit **no refs at all**: `turn_metrics`, `boot`, `fail`.

*(I first reported refs as sparsely filled. That was wrong — the fill is CATEGORICAL, by kind.)*

**Ref type vocabulary today**, with counts out of 3,000 events:

| prefix | count | example |
|---|---|---|
| `learn:` | 235 | a lesson source |
| `mem:` | 121 | |
| `file:` | 91 | `file:x_audit.py` |
| `bifrost:` | 74 | a bus message |
| `git:` | 35 | `git:edfa39babff8` |
| `beat:` | 35 | |
| `claude:` | 23 | |
| `agent_cli:` | 7 | |
| **(untyped)** | **281** | `1790440969965-0` |

The 281 untyped refs are **Redis stream ids** — bus messages, carried on
`expectation_settled_*` and `expectation_dead` events. That is the same referent as `bifrost:`,
spelled without its prefix: one concept, two spellings.

A query door exists: `events_for_ref(ref)` at `core/events/event_index.py:145` and
`core/events/event_query.py:120`.

**There IS a commit ref type.** `git:<sha12>`, 35 of 3,000, emitted only on `command` events.
*(I first reported that commits had no structural edge. Also wrong.)*

### 3.3 `session_id` — the key to the Eye — is filled exactly 0.0%

```bash
py agent_cli.py events --limit 2000 --json | py -c "import json,sys; r=json.load(sys.stdin); print(sum(1 for x in r if (x.get('session_id') or '').strip()), 'of', len(r))"
```

`0 of 2000`. Zero in **all 17 kinds** — `file_edit`, `learning`, `boot`, `decision`,
`bifrost_msg`, `turn_metrics`, `fail`, every one.

`core/events/event_log.py:109` declares `session_id: str = ""` and line 142 writes
`self._clean(session_id)`. The door offers the parameter; no caller passes it.

House law: **exactly-zero fill is a DOOR signature, not laziness.** This is the bridge between the
event plane (who/what/when) and the Eye (meaning/why/influence), and it is unbuilt.

### 3.4 The Eye is healthy but does not contain the present

```
py agent_cli.py eye stats  ->  48,702 events | 1,511 sessions | time-fog 0.0%
```

But `py agent_cli.py eye find c0444229` → **0 hits**, for a commit made hours earlier in the
session that is still running. Triangulation is weakest exactly when the work is freshest.

### 3.5 The address resolver exists with two of its possible target types

`py agent_cli.py ground --help` → *"typed target: `verb:<name>` or `seat:<id>`"*.

That is the shape of an any-id resolver, with two types wired.

### 3.6 `knowledge-map` works. `lookback` fails its controls.

`knowledge-map "git author attribution operator seat"` returned **12 surface / 5 neighborhood /
9 archive**, with relevance scores AND edge counts (`+5 edges`), and surfaced a lesson recorded
twenty minutes earlier at relevance 1.0. It works, and it walks edges.

`lookback` is the dedicated *why/what* organ. Two control questions, both with richly documented
answers in this repo — one written today, one months old:

```
lookback "why is the operator the git author instead of the seat"
  -> nothing above the relevance floor
lookback "why does a recovery path need a drill receipt"
  -> nothing above the relevance floor
```

Its layers are `docs, research, notes, promoted, chapters, git`. **An organ that returns nothing on
two known answers is a broken instrument, not an empty corpus.** Diagnosing whether this is the
relevance floor, the layer set, or the index is unfinished work and squarely in scope.

### 3.7 An instrument defect that contaminates any census run through it

`py agent_cli.py events --kind file_edit` returns `learning` and `boot` rows. **The filter does not
filter.** Any measurement anyone has taken through that flag is diluted, and it fails silently.

### 3.8 Prior art already in the tree

Durable note `scratch:deepseek:move2-provenance-done-2026-09-25` records a shipped slice:
`file_edit --agent <seat>` via `cmd_events`, plus `event_query.events_for_ref('file:<rel>')`, pinned
at `tests/test_t408_file_provenance.py` (4 pins). So the file→who join is built and wired.

`timeline` joins across domains **on time only** (`discover --semantic`, 2026-09-26).

There is an authorship plane as of today: `state/authorship/seats.jsonl`, 813 rows, commit→seat,
keyed both by SHA and by `(author-date, subject)` so it survives a history rewrite. Door:
`py scripts/authorship_ledger.py who <sha>`. And `state/rewrites/` + `py agent_cli.py sha <old>`
make a commit SHA a durable citation across history rewrites.

---

## 4. House laws that bound the design space

These are settled rulings in this repo. A design that violates one needs to argue with the ruling
explicitly, not route around it.

- **A path, title or timestamp is not a universal join key.** Type source identities per corpus and
  publish join coverage WITH `UNKNOWN`; never coerce heterogeneous ids into one key, and never
  present sparse matches as complete linkage. *(lesson: `corpus_digest_path_is_not_a_universal_join_key`)*
- **One concept implemented by two mechanisms whose tokens differ is invisible to every token-level
  tool by construction.** A lexicon that BINDS a term to its implementing mechanisms is the only
  thing that catches it. *(lesson: `token_level_tools_cannot_detect_forked_semantics_by_construction`)*
- **ZERO IS NOT NO.** Any surface reporting an empty result must distinguish checked-and-empty /
  never-reported / declined-with-reason. Three states, never one boolean.
- **Measure NON-DEFAULT fill, never fill.** A field written with an empty default on every record
  reads as 100% healthy and carries nothing.
- **A regenerable projection and a fact about history belong in different planes.** A durable fact
  in a delete-and-rebuild table is a category error that survives until the next rebuild.
- **Gate evolution beats a new organ**, and a superseded pin is rewritten in place citing the
  ruling, never deleted.
- **Built ≠ wired.** A capability no production entry point calls runs nowhere, however green its
  tests. This repo has a checker for it (`check_wiring`) and it has caught real cases this week.
- **Edges written at write time cost nothing at read time.** The read path is the one the operator
  experiences as fast or slow.

---

## 5. Explicitly out of scope

- Do not design the operator-facing rendering (dashboards, report pages). The join is the subject.
- Do not propose changes to git identity or attribution policy — that was ruled on today and is
  closed.
- Do not redesign the Eye's ingest pipeline wholesale; if ingest freshness matters to your design,
  say what it must guarantee and treat the how as a separate slice.

## 6. A note on independence

I have a proposal of my own. **It is deliberately absent from this brief**, because a half that
reads the conductor's framing first echoes it, and this house has measured that. Two independent
designs that disagree are worth more to me than two that agree with me.

If you conclude the evidence pack itself is the wrong pack — that I measured the wrong plane, or
that the seven axes are not the right decomposition — that verdict outranks everything else in
your document. Lead with it.
