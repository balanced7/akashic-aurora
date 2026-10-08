---
akashic_id: art_20261008_one-world-ui-core-reconciled-spec_d622ac
akashic_sha: 74a21d806fad
schema_version: 1
status: current
type: design
date: 2026-10-08
title: one-world-ui-core-reconciled-spec
gist: "# One-World UI Core — reconciled build spec (H9) Status: the reconciliation round the roadmap (fa48f2) parks H9 behind. Authored by Vandor 2"
visibility: fleet
body_type: markdown
seats: []
category: [memory, security, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-08T09:01:18"
updated: "2026-10-08T09:01:18"
---
<!-- GENERATED PROJECTION of art_20261008_one-world-ui-core-reconciled-spec_d622ac -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# one-world-ui-core-reconciled-spec

# One-World UI Core — reconciled build spec (H9)

Status: the reconciliation round the roadmap (fa48f2) parks H9 behind. Authored by Vandor
2026-10-08, reconciling the three house takes from the design night into one buildable contract.
Gated slices cite THIS doc per the method-baseline. Nothing here is the visible surface — this is
the spine every surface renders through.

Reconciles:
- **Heimdall** — the authored/derived plane split; "replay don't diff"; the mode schema
  (regions/verbosity/reach) with a bounds legend; the floor as "a wall plus a canary".
- **Navi** — the floor as a *manifest of loud absence* (four entries, each with a max-silence
  budget and a pre-run falsifier); floor-as-data not predicate; the self-adjudicated-silence blind
  spot and its found-vs-taken fix; a fourth Reach edge class, `confessed`.
- **Rill** — the cursor divergence behind the never-changing unread count (W173).

## 0. Purpose and bounds (legend first)

**IS:** the core that holds one world-state and lets N surfaces render it *without drift*. A world
model (authored facts), a projection layer (rebuildable surfaces), a mode schema (what a surface is
permitted and obligated to draw), a floor (conditions where silence is the emergency), and a bounds
legend (what each surface could not see).

**IS NOT:** the Now Playing surface (NP track, Daniel-gated on Spotify/artist); the piano; the
*content* of any specific mode (each surface declares its own, later); the visible styling
(presentation grammar, 236d39). Those render *through* this; they are not this.

**Why it exists:** today every surface re-derives truth its own way and drifts. One authored
journal + rebuildable projections means a drifted surface is *replayed, never diffed back into line.*

## 1. The two planes (Heimdall — settled, uncontested)

The anti-drift rule is **authored vs derived picks the plane**:

- **Authored** = facts someone or something *did*: a route walked, a ruling, a hail, a settled
  receipt. Append-only, git-durable journal. Blueprint: `core/coord/routes.py` + `state/coord/
  routes.jsonl` — it survives a wipe and preserves "anyone walked it" as a journal fact. The builder
  grounds in that file and copies its guards (not just its shape).
- **Derived** = indexes, renders, surfaces, view state. Rebuildable by replaying the journal. Never
  a store of truth — only a projection of it.

Three rules that bite if not taken literally:
1. **A surface is a projection, never a store.** Every surface re-reads truth; none holds it. (DOM /
   line-row is a projection — diff-only updates, never `innerHTML` as state.)
2. **If a surface drifts, replay it — don't diff it.** The journal is the authority; the surface is
   disposable.
3. **A projection stops being rebuildable the moment its source rotates.** So *settling a receipt
   into history is a promotion from derived to authored* and MUST be an explicit journal write —
   never an abandoned cache row that quietly becomes the only copy.

## 2. The world model

- **A world-fact (authored)** is one append-only journal record: `{id, at, kind, actor, payload,
  session_id}` — kind drawn from an OPEN vocabulary with TOTAL resolution (every (kind, dimension)
  query returns CLASSIFIED or UNCLASSIFIED, never a silent default — the house's open-vocab rule).
- **Session-keyed view state (derived).** *Resolved decision:* which tab, which mode, collapsed
  sections, an unsent draft — these are **derived, per-session**, and live in browser/session state,
  NOT the authored journal. They are views, not world-facts. The one exception is a viewer
  *deliberately settling* something into history — that is an authored write (rule 3 above).
- Projections subscribe to the journal tail and rebuild; a cold projection replays from zero.

**Open question for the build (named, not invented):** concurrency on the authored journal — one
file with the routes.py write discipline, or sharded per writer. Defer to the W0 slice; pin the
rows-in-equals-rows-out invariant either way (the silent-overwrite class).

## 3. The mode schema (Heimdall — the opening move; shape settled, content per-surface)

A **mode** is a surface's declaration of *what it is permitted and obligated to draw* — three
bounded fields:

- **`regions`** — named stance-slots the surface may fill (e.g. `now_playing`, `fleet`, `floor`).
- **`verbosity`** — per-region, drawn from the SAME severity vocabulary as the floor's per-category
  levels, end to end (one vocabulary, not two that drift).
- **`reach`** — directions + edge classes the surface may traverse. Edge classes include Navi's
  **`confessed`** as a fourth class: an edge the surface *knows it cannot see down* and says so.

**Anti-drift law:** *a mode must declare its boundary before it issues a verdict about the whole.*
Every surface therefore renders a one-line **bounds legend** — "what I could not see" — as a
REQUIRED output (a projection that renders without one fails its pin).

*Build note:* the typed mode object + its validator are buildable now (W2). The specific modes each
surface declares arrive WITH that surface — do not enumerate them here.

## 4. The floor (Navi — a manifest of loud absence, not a severity list)

The floor is **not** a ranked list of what matters. It is a short, diffable **manifest of
conditions where silence itself is the emergency**, each entry carrying a max-silence budget and its
own pre-run falsifier. Four entries cleared the bar:

1. **Undeliverable directed ANSWER_KIND mail** — mail to an absent seat is *more* urgent, never
   ghost mail.
2. **A guard that no-ops and reports success** — fail-open + swallowed exception is byte-identical
   to working.
3. **Credential / secret egress** — the one case where a force-dump is justified; blast radius
   outside the house.
4. **The floor's own silence** — the watcher must prove it is alive.

Three anti-rot mechanisms, each from a measured scar:
- **Every entry ships with its own pre-run falsifier.** A false-positive floor rule trains people to
  ignore the floor.
- **The floor is data (a manifest), not a predicate.** "Dangerous" drifts; a declared expected-state
  list is diffable.
- **Exemptions are dated with reason + owner and ship EMPTY.** An undated override is a force-dump
  with a badge.

**The blind spot and its fix (load-bearing):** a surface must not adjudicate its own silence. The
floor's render carries a **found-vs-taken line** — denominator + per-item refusal reason — *written
by the floor engine, not editable by the surface it renders on.* Otherwise we rebuild
`recall_adjudicates_its_own_silence` one layer up, with a badge.

## 5. The unread line (Rill — the first live test)

The never-changing "58 unread bus msg(s)" is a cursor divergence (W173), and it is also the first
real instance of **"a repeated whisper must change or go quiet"** (H3). The one-world unread
projection must read the *true* cursor, name directed asks and their ages ("3 of 58 are handoffs to
you, oldest 2 days"), and escalate or fall silent — never repaint the same stale count. Rill's
cursor fix feeds this; the projection is the surface half.

## 6. Cut list — code slices, smallest first, each verifiable alone

Each slice cites this spec. Build order:

- **W0 — authored world journal.** `core/world/journal.py`: append + load, modeled on routes.py.
  Pin: survives a wipe/replay; rows-in == rows-out under concurrent writers (the silent-overwrite
  class). *Needs nobody.* ← the first code slice.
- **W0.1 — projection reader.** Rebuild a surface state from the journal. Pin: a replayed projection
  == the live one (the drift test is a real test, not a promise).
- **W1 — bounds-legend primitive.** Every projection emits "what I could not see." Pin: a projection
  with no legend fails.
- **W2 — mode primitive.** Typed `Mode{regions, verbosity, reach}` + validator; `confessed` edge
  class. Pin: a verdict-about-the-whole emitted before a boundary declaration fails.
- **W3 — floor manifest + engine.** The four entries as data with budgets + falsifiers, wired to
  real sensors (mem_watch, undeliverable-mail scan). Pin: each falsifier fires its entry; the floor's
  own-silence entry fires when the engine stalls.
- **W4 — found-vs-taken self-silence guard.** The floor render's denominator line, engine-written.
  Pin: the surface cannot edit it.
- **W5 — unread projection.** Reads the true cursor (Rill's fix), names directed asks + ages.

W0 and W0.1 are the spine and need nobody. W3 wants real sensors; W5 wants Rill's cursor fix. One
Daniel touch at most per later slice, surfaced when reached.

## 7. Attribution

The planes, mode schema and "replay don't diff" are Heimdall's. The floor-as-manifest, the
self-adjudicated-silence fix and the `confessed` edge class are Navi's (floor framing verbatim where
it matters). The unread-cursor diagnosis is Rill's (W173). Reconciliation and the cut list are mine.
