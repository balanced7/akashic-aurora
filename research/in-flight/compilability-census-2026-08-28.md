# Compilability census — of the lessons that state a trigger, how many name a real location?

**Data and method only. No interpretation in this file — deliberately.** My reading is sealed
separately (`compilability-census-sealed-reading-2026-08-28.md`), committed before the fleet was
asked, so it cannot drift to match whatever comes back.

Run 2026-08-28 by claude/Vandor, at Daniil's ask.

## The question

Of the lessons whose recommendation states its own trigger ("Use when …"), how many name a trigger
that resolves to a **real mechanizable location** — an actual tool, verb, or hook point that a gate
could observe at the moment it fires?

This number has been flagged as load-bearing four times and never taken. Estimates offered in the
meantime ranged from 400 to 40.

## Method

**Population.** Every lesson whose `recommendation` begins `use when` (case-insensitive).

**Namespace.** Pinned before classifying: 94 `agent_cli` verbs (those ≥4 chars; shorter ones are
pure collision fuel), the harness tool names, 19 hook modules, and path/extension shapes.

**The strictness that decides everything.** Sol's `verb_token_presence_is_not_mechanizable_trigger`
established that counting lessons whose text merely *contains* a verb token yields ~586/766 —
almost all lexical collisions. So a namespace hit alone is not sufficient. A trigger counts as
mechanizable only when the token is the **object of an invocation cue** — within a short window
after `running|invoking|calling|executing|editing|committing|…` — or when the clause carries a
**concrete referent** (a backticked command, `py agent_cli.py …`, `git commit`, a real path).

**Buckets.**

| | |
|---|---|
| **a — MECHANIZABLE** | token is the object of an action; a gate could observe it |
| **b — JUDGEMENT** | names a real moment with no code location; a genuine trigger, ungateable |
| **c — UNRESOLVED** | no invocable referent in an object position |

## v1 failed its own validation, 6/6 — and that is part of the result

The first pass required *(namespace hit) AND (an invocation cue somewhere in the clause)*. It
returned **a = 159 (19.6%)**.

Every one of the six hand-sampled items was a false positive:

- *"…bounded forward read, before increasing the cap"* — matched `read`, a noun
- *"a cached probe (head sha, config, roster, price table)"* — matched `roster`, a noun in a list
- *"several live instances answer to one agent/service name"* — `agent/` read as a path
- *"…onboarding seed, backlog policy, boot greeting"* — matched `boot`, a noun

**The cause:** lesson triggers are almost universally phrased "when doing X", so an invocation cue
is nearly always present *somewhere*, while the namespace hit came from an unrelated noun. v1
rebuilt the 586-ghost class while explicitly designed to avoid it. v2 requires **proximity**, not
co-occurrence.

## Result (v2)

```
corpus                   1252
population (Use when)     810   (64.7%)

a  MECHANIZABLE            24   ( 3.0%)
b  JUDGEMENT              130   (16.0%)
c  UNRESOLVED             656   (81.0%)
```

## Hand-validation of v2, all ten sampled

**Clearly valid (7):** concrete `git commit` inside a composed Bash string · `py agent_cli.py fence
write` · `recall --full` as the object of *invoking* · `codex exec` · `py scripts/mirror.py` ·
`git commit -m` in PowerShell · a second fence-write case.

**False positive (1):** *"launching or running ANY fresh-seat cold-boot ergonomics audit"* — `boot`
matched as a noun inside a noun phrase.

**Borderline (1):** *"touching wrap, boot fold, primer, or any handoff organ"* — names code regions
rather than an invocation.

**Unjudgeable (1):** truncated in the sample output.

**≈80% precision on bucket (a), against v1's 0%.** Treat that as the error bar.

## Stated limits

1. **This measures triggers as *written*, not as *writable*.** An author who wrote a vague trigger
   may have had a crisp one available. 3.0% is a floor on gateability-as-written, not a ceiling on
   gateability-in-principle.
2. **Reach is not value.** A resolvable location says a gate *could* observe the moment, not that
   one there would help.
3. **Proximity over prose is still a heuristic.** ~80% precision on a 10-sample; the recall side
   (valid triggers v2 missed) is unmeasured.
4. The population is self-selected by a house convention. Lessons whose triggers live outside the
   "Use when" form are invisible to this count entirely.

## Reproduce

`namespace.json` pinned from `agent_cli.py --help` and `agent/harness/hooks/`; population from
`get_learning_store().load_all_learnings_from_store()` filtered on `^use when`. Classifier is
~40 lines of regex; both passes and their outputs are preserved. Anyone re-running should expect to
disagree with individual classifications — the buckets are a measurement, not a verdict.
