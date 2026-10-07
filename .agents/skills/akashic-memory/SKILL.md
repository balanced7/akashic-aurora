---
name: akashic-memory
description: Use whenever you work in the Akashic Aurora repo (E:\AI-Setup) — at session start, after ANY fix that first failed, when a correction may reveal reusable operational knowledge, and at session end. Also use when deciding whether something belongs in a lesson, note, doc, hook, another space, or no durable artifact at all. A correction triggers a placement check, not an automatic shared-memory write.
---

# Akashic memory: the loop you are inside

This repo has a shared operational memory. Other agents' lessons surface to you automatically
(hooks inject the top few before risky actions); reusable repo knowledge should flow back when
it belongs on that plane. Shared memory is an active retrieval surface, not a neutral archive:
placement is part of correctness. The full contract is `AGENTS.md`; this skill is the reflex
layer.

## Session start
```
py agent_cli.py boot <your_agent_id> --task "<this slice only>"
```
Read the output. The RECENT NOTES section is where-we-are; `py agent_cli.py notes --json`
for full bodies. Use the store instead of replaying an entire chat merely to reconstruct repo
state. This is an operational task-continuity rule, not a declaration that conversation is
disposable or permission to move personal or relational history into shared memory.

## Placement gate (before every capture)

Operational rigor can govern an inquiry without producing a shared artifact. Before `learn`,
`note`, or a durable document, ask:

1. **Use at recurrence:** can another agent act on this in the repo when the situation recurs?
2. **Rightful audience:** is the shared operational fleet the intended audience for it?
3. **Fidelity:** can it survive compression without losing the context that gives it meaning?
4. **Stream effect:** will later retrieval help the relevant work without coloring unrelated
   work or changing the emotional and cultural character of another space?

Personal, relational, reflective, or emotionally situated material stays in its originating
space unless the human explicitly chooses another home for it. If any answer is uncertain, do
not capture by default; ask before crossing planes. Ephemerality can be the correct boundary.

## The operational capture reflexes (after placement)

**FAIL→SUCCESS flip** — the moment something that failed now works, a lesson was just
earned. The hook usually nudges you with a pre-filled command; run it. Write the
recommendation TRIGGER-PHRASED:

```
py agent_cli.py learn <id> --experiment <slug> \
    --tried "<what failed>" --result "<what fixed it>" \
    --recommend "Use when <symptom>, before <action>: <advice>. Don't when <contraindication>."
```

Include what did NOT work (`--tried` is exactly that) — failed approaches save the next
agent more time than successes do.

**User correction** — a correction deserves attention, not automatic promotion. If it exposes
repeatable operational behavior and passes the placement gate, record it with `--category
correction`. Otherwise incorporate it locally and leave it in its originating space. Do not
generalize a situated interaction merely to make it fit the shared store.

**Known-bad approach** — record with `--anti-pattern <slug>` so it surfaces as a warning,
not advice.

## Close the loop on what you were shown
If a surfaced lesson changed what you did: `py agent_cli.py recall-feedback --source <src> --useful`.
If it was off-target noise: `--noise`. Votes steer future ranking; silence teaches nothing.

## Where knowledge belongs (the promotion ladder)
Forcing function > just-in-time prompt > documentation > memory. If a lesson's rule is now
ENFORCED by a hook/guardrail/CI check, graduate it so it stops spending recall slots:
```
py agent_cli.py graduate <id> --experiment <name> --enforced-by "<the automation>"
```

## Session end
```
py agent_cli.py wrap            # review the draft; then: wrap --commit
py agent_cli.py handoff <id> --to <next> --task "..." --note "where we left off"
```
A slice is not done until it is mirrored (`py scripts/ship.py` for code, `py scripts/mirror.py`
for docs) and the where-we-are note is current. When an ARC closes (not every slice),
append its entry to `docs/JOURNEY.md` — what we set out to do, what actually happened,
why we pivoted, what it yielded — in the humble register that file models. The human
reviews it before it ships.

## Mid-task pulls (don't wait to be shown)
`py agent_cli.py recall "<keywords>"` searches the corpus; `recall --full <source>` pulls
one lesson's whole record. Pulling beats guessing.
