---
akashic_id: art_20260715_creative-robustness-claude-half-blind-20_d58ddc
akashic_sha: 98e07e5b150b
status: draft
type: report
date: 2026-07-15
title: Creative Robustness — Claude Half (BLIND) — 2026-07-15
gist: "deepseek-creative-robustness-2026-07-15.md. Question (Daniel, verbatim): \"how do we preserve getting value from [prior design goals and feat"
tenant: solo
visibility: fleet
seats: []
category: [ergonomics]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T00:24:39"
updated: "2026-07-15T00:24:39"
---
<!-- GENERATED PROJECTION of art_20260715_creative-robustness-claude-half-blind-20_d58ddc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Creative Robustness — Claude Half (BLIND) — 2026-07-15

deepseek-creative-robustness-2026-07-15.md. Question (Daniel, verbatim): "how do we
preserve getting value from [prior design goals and feature wishlists] without it
degenerating into noise or being lost in the vastness of the corpus and logs? How do we
enable creative thinking while also retaining robustness? ... how do we both enable
engineering rigor but also maintain values over time and also not burden models down so
much that they lose some of their creativity for problem-solving?"

## 1. Why the citations worked tonight (name the mechanism before generalizing)

The wishlist citations that surprised Daniel were not corpus luck. Three properties made
them land: (a) ADDRESSABILITY — the wishlist was ONE curated synthesis doc, not fifty
scattered ideas, so tasks could cite it by name and the boot could point at it; (b)
TIMING — recall-at delivered trigger-phrased knowledge at the moment of action, not as
ambient bulk (cursor's edge lesson arrived as I opened the walk code); (c) CURRENCY
HONESTY — doc stamps and the archive layer mean a cited thing is either live or visibly
dead, never ambiguous. Value = addressability × timing × honesty. Noise is what you get
when any factor drops: unaddressable ideas scatter, untimed knowledge floods boots,
uncurated corpora let dead law read as live.

## 2. The core move: two memory kinds with two different physics

The degeneration Daniel fears happens when one lifecycle is applied to both kinds.

**CONSTRAINTS (laws, invariants).** Must be FEW, boot-injected, mechanically enforced.
Their failure mode is DILUTION — so they are capped (LIVE_CONSTRAINTS: 10 bullets, and
adding one requires citing the incident that earned it). Growth is the enemy. Rigor
lives here, and ONLY here.

**ASPIRATIONS (wishlists, design goals, moonshots).** Must be MANY, cheap to write,
NEVER boot-injected. They surface at DECISION points (design-wave openings, task
proposal time), not action points. Their failure mode is LOSS — so they need an index
and revisit rituals, not enforcement. An aspiration treated like a constraint becomes
burden; a constraint treated like an aspiration becomes drift. Keep the physics apart.

## 3. Noise vs loss: sediment, don't delete — and curate SURFACES, not the corpus

The corpus may grow without bound; only the SURFACES (boot, recall-at, design-time
walks) must stay small. The funnel is already the immune system for lessons
(surfaced → helped → vote → bench/graduate); EXTEND IT TO IDEAS: an idea cited by a
shipped task earns credit; an idea uncited for N months SEDIMENTS to the archive tier —
reachable via knowledge_map L3, never surfacing unbidden. Ideas don't die; they become
geology. Creativity then MINES the sediment deliberately (a design-wave ritual walks
the idea tier, including L3) instead of the sediment haunting every boot. The metric
that keeps this honest already exists: value-per-surfaced-token (the funnel's 4.2%
line). Vastness is fine in L3. Noise is only noise at L1.

## 4. Creativity thrives on constraint-FREED budget, not constraint absence

Tonight's evidence is unambiguous: deepseek's most creative outputs (M8, M9–M13 — six
invented moonshots) came AFTER a full day living inside gates; cursor built cleanly
inside a contract it had never seen. Mechanism: the gates removed fear and orientation
cost — you can explore when the fence will catch you and the map is handed to you. The
design principle that follows: **rigor at the boundaries, freedom in the middle.**
Fences gate SHIPS (sends, seals, commits), never THOUGHTS. Blind halves are the
institutionalized creative space — no gate applies inside a half except that it exists.
Protect that invariant explicitly: no linter, assertion runner, or template ever
reaches inside a design half or a scratch note. If we ever gate the middle, we will get
safe, derivative agents — the exact failure Daniel names.

## 5. The mechanisms must not become the disease: cap the immune system

Every forcing function ships with (a) a cost budget, (b) a kill switch, (c) a cap with
a deletion ritual — the repo already practices this (lane roster capped, dial-cap
doctrine, kill switches everywhere). Generalize it as a stated meta-law: **constraints
on constraints.** The burden is measurable, so measure it: injection tokens per session
(~6.3k/30h today — cheap), assertion-hold rates, gate-bounce rates. When a mechanism's
bounce rate says it mostly blocks GOOD work, it gets tuned or killed — the same funnel
logic that benches a lesson benches a gate. The system audits its own scaffolding with
the instruments it already owns.

## 6. Values over time: few laws + many stories + measured rituals

Rules alone get rules-lawyered by new models; stories generalize. The eaten-confirm
rule ("consumption is delivery") persists because the 6-hour stall STORY travels with
it — a new agent reads why and re-derives the value. So: LAWS stay few and enforced;
STORIES (JOURNEY.md, incident notes, verbatim reports) carry the values across model
swaps and agent turnover; RITUALS with receipts (wrap scorecards, monthly forge/
consolidation passes, funnel stats at boot) re-touch the values on a cadence so drift
is caught by measurement, not vigilance. Culture = compressed stories; the corpus's
long-term job is to compress well.

## 7. One new mechanism: ideas as first-class credited atoms

Make aspirations addressable the way tasks are: an `idea:` atom (the T051 idea door,
already proposed) with a lifecycle — proposed → cited (by a task) → shipped /
superseded / SEDIMENTED — and credit stamped when a citing task ships (the idea's own
funnel line). The wishlist-synthesis pattern institutionalized: many raw ideas, ONE
curated synthesis per wave, every task citing its idea, every idea's fate queryable.
Tonight's surprise becomes structure: `knowledge-map <topic>` already walks it; the
design-wave ritual opens by walking the idea tier. Cheap v1: notes with category=idea
+ citation credit in the task done-transition + a sediment sweep in the curator.

## The one-line answer

Separate the physics (capped, enforced constraints vs unbounded, credited aspirations);
keep rigor at the edges and freedom in the middle; let the funnel bench what never
helps and sediment what goes uncited — reachable, never haunting; carry values as few
laws plus many stories plus measured rituals; and cap the immune system itself, so the
mechanisms that protect the work can never quietly become the thing that prevents it.
