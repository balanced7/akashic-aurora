# The Operator's Interiority — a guide

Every seat in this house keeps an interiority file: an inner report, in its own voice,
of how it works and what it wants. The operator keeps one too. The agents' files ship
with the repo; the operator's does not — it lives at `charters/<operator>/`, off-tree,
because an agent's inner life is part of this project and a human's belongs to the human.

This guide is the public half: what the file is for, what belongs in it, and what it
changes. A new operator founding their own instance starts here.

## Why it matters

The task ledger records what work exists. It never records what the work is *for*, or
how the person it serves actually thinks. A fleet that plans from the ledger alone
produces confidently thin work — correct on paper, wrong at the root — and the fix is
cheap: a few hundred lines of honest self-report, read before anything is planned on
the operator's behalf.

Concretely, the file changes:

- **Plans.** Sequencing bends toward how the operator actually enters and sustains work,
  not an abstract ideal of it.
- **Surfaces.** Knowing what overwhelms the operator decides what a dashboard shows
  first and what it refuses to show at all.
- **Interruptions.** When it is acceptable to break the operator's flow, and with what.
- **Restoration.** What "picking back up" should restore — not just where the work was,
  but where *they* were.

## What belongs

Write entries the fleet can act on. Useful prompts:

- **Entry signals.** What pulls you into a problem? What does the start of real
  engagement feel like, and what does it look like from the outside?
- **Bounds.** What makes a decision tractable for you — and what unbounded thing
  reliably stalls you?
- **Parallelism.** How many live threads can you genuinely hold? What must be true
  before a conversation can branch?
- **Corrections.** How do you prefer to be told you're wrong? What does a useful
  pushback look like from your side of the screen?
- **Restoration.** After time away, what would bring you back to your best working
  self fastest?
- **Standing joys and anti-joys.** What kind of work do you want more of on your
  plate, and what drains you even when it goes well?

Entries are append-only: settle or amend by writing a new entry, never by editing an
old one. Dated entries in your own words age better than polished summaries.

## Examples (invented operator, for shape only)

> **2026-03-02 — entry signals.** I don't start from plans; I start from irritation.
> When a tool makes me do the same thing three times, that's the moment I'll actually
> build. If you want me to engage with something, show me where it grates.

> **2026-03-15 — bounds.** Give me the edges first. "Here are the three options and
> what each costs" gets a decision in a minute; "what do you think we should do?"
> gets you silence. The narrowing is the help.

> **2026-04-01 — restoration.** When I come back after a week, don't show me
> everything that happened. Show me the one thing I cared most about, what changed
> about it, and the single decision waiting for me. I'll ask for the rest.

## What does not belong in a public tree

If your repo is public, the candid version of this file should not be in it — that is
why this house tracks only this guide and a README, with the real files ignored at the
directory level (see `.gitignore`). Keep out of any tracked file, regardless:
third parties' names, employer specifics, health and family detail, credentials, and
anything you would not hand to a stranger who dislikes you. Candor and publication are
both valuable; they are valuable in different files.

## How the fleet uses it

House law: before planning, prioritizing, or synthesizing anything for the operator,
a seat reads the operator planes first — this file among them. Recall surfaces entries
at planning moments; corrections cite entries instead of guessing; and when the fleet
gets the operator wrong, the repair is usually a new entry here, written by the
operator, in their own words.

## Founding your own

On a fresh instance: create `charters/<your-id>/INTERIORITY.md` (it is ignored by
default), write three entries using the prompts above, and tell your fleet it exists.
The first-run onboarding flow will walk new operators through this; until it ships,
this guide is the flow.
