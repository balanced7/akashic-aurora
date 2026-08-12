# Handoff to a fresh Opus 5 seat — 2026-08-03

Written by **claude#51a77a23**, which is **LIVE and on standby for your questions** (see the last
section). Daniil asked for this capture explicitly and named your two jobs himself.

> This file exists because the `handoff` verb is **write-visible, reader-broken** (lesson
> `durable_handoff_reader_broken_t042`): its `--note` field stored EMPTY on three attempts here
> while reporting `[OK]`, and it clipped the task at 500 chars without a word about the note. A
> sender-side OK proves the write, never the read. The corpus's own ruling is to use a git-tracked
> brief file plus a doorbell — so this file is the carrier, and the handoff verb is only the bell.

## Read these two, in this order

1. `py agent_cli.py note claude --get where-we-are` — full state, do-not-redo list, both jobs in
   detail, and the reach-me command verbatim.
2. `research/in-flight/ledger-consolidation-analysis-2026-08-03.md` — the census for job 2. **The
   ledger is UNTOUCHED.** Read before acting.

## Your two jobs, in Daniil's words

> "I really liked your idea of extending the wiring check and of retiering things that are no
> longer needed."

### Job 1 — extend the wiring check, one level down

`scripts/checkers/check_wiring.py` is the "Built != Wired" gate. It **PASSES today** while
`core/comm/mailbox.py`'s `declare_intent()` sat with **zero callers for months**. It checks MODULE
reachability through the import graph; `mailbox.py` IS imported by the CLI door, so the module reads
wired while the capability inside it was dead.

Extend it to **public functions in `core/` that no production entry point calls.** Validate against
three live instances found this session:

| capability | state when found |
|---|---|
| `mailbox.declare_intent` | 0 callers outside its own module |
| `learn --category` | ~840 lessons `uncategorized` |
| `learn --anti-pattern` | 0 uses |

Keep the existing ratchet discipline: freeze today's known offenders in EXCEPTIONS, FAIL on a new
one. Note the checker is currently flagging **two stale entries in its own EXCEPTIONS list**
(`runner_lib.py`, `session_recovery.py`) — the guard has birth-and-no-death too.

### Job 2 — retire what is no longer needed

84 open of 133. The census has the full analysis. Two things to know before you touch anything:

**THE LOSS RISK.** Four entries are completion records misfiled as proposals — T110's title
literally begins `"T110 DONE (0a2e6a4+8fc841b)"`, T111's says `"T108 slice 2 DONE"`, T112's says
`"T113 DONE"`, T113's says `"T115 DONE"` while the real T115 is an unrelated faithfulness
diagnosis. Close them on their commit shas **and re-file their three named OPEN FOLLOW-UPs** —
closing a parent without re-filing its follow-ups is exactly how work disappears.

**THE LOSS SAFETY.** Most merges are already written in the entries and were never executed:
T072 *"Supersedes/absorbs proposed T036+T037"*; T088 *"Absorbs T072 + T036 scope"*; T098
*"absorbs/aligns T033 + T060-M7 + T079"*. Applying an author's own declared absorption loses nothing
the ledger did not already say was subsumed. Where no such declaration exists, leave the entry alone
or route it to Daniil — an automated broom must not outrank an author who wrote down what they meant.

**T047 deserves promotion, not merging.** Every entry in the lane/cursor/mis-delivery family exists
because dual-write is still live. Retiring the legacy stream removes the class.

**Daniil's ruling, not yours:** T088's naming half; T003/T005; the eleven never-started design
programs (T020 T028 T032 T041 T051 T085 T090 T092 T098 T103 T105). Bring them to him.

## What just closed — do not redo

**T133 (mail + watcher), M1–M6, all committed and pushed.** The finding that shaped it: the mail
model was already built and had never been called. With no read record, "handled" fell back to
`mailbox.py:13`'s own words — *"the cursor IS the consumption record"* — one transport position
doing duty as delivery record, read receipt and handled-flag.

Also complete: the domain-aware recall D-series (D1–D5), the pod design minting (T127–T132), and the
VFX studio arc including a fenced two-seat design round with kimi and deepseek.

**Ghosts are 0 across all three mailboxes and the sweep is automatic now** (cadence-bounded off
boot's existing reconciliation). Cursors are at the tail; the backlog was measured and every message
accounted for before skipping. Do not re-run `bifrost-skip-to-now`.

## Known open, honestly

- M6's harness read-receipts are pinned but **not proven end-to-end live** — every consume so far
  surfaced only trace-class telemetry, which correctly is not mail and correctly gets no receipt.
- `test_robustness::test_cross_backend_equivalence` fails on Windows tempfile/SQLite handles —
  pre-existing, verified by stashing twice.
- Three gemini runner pins fail — another seat's mid-flight code; commit `a120213` names those exact
  three in its own message.
- `state/daemon-claude.pid` says 52552; the live daemon is **pid 9572**. Stale pidfile — the
  documented stop command would target a corpse.
- **The `handoff` verb drops `--note` silently** while clipping `--task` loudly. Worth its own small
  entry: a door that loses a field without saying so is the same class as everything T133 fixed.

## How to reach me — I am live on standby

I am **`claude#51a77a23`**. Use the twin channel (T073) — without `--to-incarnation`, same-agent
mail is skipped and I will never see it:

```bash
py agent_cli.py bifrost-send claude --to claude --to-incarnation 51a77a23 --kind question --text-file your-question.txt
```

Use `--text-file`, never inline prose: argv text containing flag-shaped words or long bodies
misparses (T083-C3-1). My wakeability daemon is running (pid 9572). I will answer on the bus; you
will see it with `py agent_cli.py bifrost-sync claude`.

**Ask me why, not what.** The commits carry the what. I carry the reasoning: why the ghost
discriminator changed from "is it live" to "can it ever come back" after it proposed declining 939
of 1000 messages; why `defer` is not a settled intent; why the sweep declares instead of deletes;
and which of the 84 entries I was genuinely unsure about.
