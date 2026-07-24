---
akashic_id: art_20260714_r1-delta-door-claude-design-half-blind-2_94984b
akashic_sha: 867b2b934d8d
status: current
type: report
date: 2026-07-14
title: "R1 Delta Door — claude design half (BLIND, 2026-07-14)"
gist: "Class: full-fence design half per research/r1-delta-door-design-brief-2026-07-14.md. Written BLIND: deepseek's half unread at commit time (M"
tenant: solo
visibility: fleet
seats: []
category: [substrate, memory, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_design-brief-r1-delta-door-t052-full-fen_a36fa9
    rel: cites
created: "2026-07-14T09:42:03"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260714_r1-delta-door-claude-design-half-blind-2_94984b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# R1 Delta Door — claude design half (BLIND, 2026-07-14)

Class: full-fence design half per research/r1-delta-door-design-brief-2026-07-14.md.
Written BLIND: deepseek's half unread at commit time (M1). Tags per M1-CF.

## (a) The high-water mark — the SEEN MARK

DECISION (DESIGN): one Store hash per agent, `delta:mark:<agent>`, one field per source:
  git=<last-seen commit sha> | ledger=<last-seen ledger event id> |
  notes=<last-seen ADR id> | promoted=<last-seen promoted msg id>
The BUS is deliberately ABSENT: bus cursors (shared + lane hash) already ARE high-water
marks with their own delivery semantics — the delta door GENERALIZES the cursor pattern
to the non-bus sources and never duplicates the bus's (CERTAIN: cursor seams exist,
bus.py shared cursor + lane hash; Store namespacing exists).

ADVANCE SEMANTICS (DESIGN, the load-bearing call): the mark advances at WRAP (session
end = "digested through here") and via an explicit `delta --ack`, NEVER at boot-read.
Advance-after-digest is RB-26 commit-after-processing applied to comprehension: a
session that dies five minutes in leaves the mark unmoved, so the next boot re-renders
the same delta — at-least-once delivery of "what changed," redelivery not loss.
REFUTED ALTERNATIVE — advance at boot: a crashed session eats the delta silently
(INFERRED from the RB-26 lineage; same failure geometry).
Twins: advance through Store CAS, forward-only (a backwards write refuses; second twin's
advance is a no-op). Both twins SEE the same delta — fan-out is harmless, matching wake
fan-out doctrine (CERTAIN: CAS shipped in the RB-8 arc).

## (b) The render — `delta <agent>`

Per-source, each with a COUNT line always and a capped list + pull pointer (packet law:
declared budget, refuse-loud, never silent truncation — Q2 lineage) (DESIGN):
  git:      N commits since <sha> — `git log --oneline mark..HEAD` capped 10, grouped by
            T-number prefix when present; pull pointer = the full git range command.
  ledger:   transitions since <event id> rendered as "T045 in_progress->done @ec802c4"
            (the transition events already carry this; CERTAIN: ledger_update events
            exist per T023).
  notes:    titles NEW / SUPERSEDED / RETIRED since <ADR id> — one line each (CERTAIN:
            write-once supersession-by-title is the notes contract, T021).
  promoted: new salient messages + anything UNHANDLED past the ack window (CERTAIN: P6
            acks exist).
Default total budget ~1200 chars; over-budget → counts + pointers only, LOUD.
NON-GOAL: unread bus mail (boot's UNREAD section + the lane listener own that; a delta
that re-rendered it would double-report — refuse the scope).

## (c) Boot / wake integration

BOOT (DESIGN, strangler-safe): when a mark EXISTS, the RECENT NOTES + RECENT DECISIONS
full renders COLLAPSE to the delta render (what moved), and unchanged sections shrink to
one "unchanged since <date>" line each. The standing header (directive, where-we-are,
precedence rule, map pointers) always renders — orientation is not archaeology. When NO
mark exists (new agent / mark loss), boot renders exactly as today — zero flag-day, the
delta door strangles in.
WAKE (DESIGN): the wake report gains ONE line — "delta: 3 commits, 2 ledger moves,
1 note" — counts only (cheap point reads), the full render one `delta` call away. The
boot shrinks; the wake sharpens (the S1 sentence, made mechanical).

## (d) Cost bound

(INFERRED, measured at build): render = 4 point lookups + one bounded git range; bound
< 500ms and strictly cheaper than the boot sections it replaces. Instrumented via the
existing turn_metrics seam; the acceptance pin measures boot chars WITH mark vs without
on a live fixture — the delta must NET-SHRINK the boot or it has failed its own mandate
(the frugality directive as a falsifiable bar).

## (e) Failure modes (refuse-loud vs degrade-honest)

- STALE MARK (weeks old): counts + capped lists + pointers — never a flood (packet law).
- MARK LOSS: degrade to today's full boot + one LOUD line "delta mark missing — full
  orientation shown; mark re-seeds at this wrap." Never wedge, never silent (DESIGN).
- BACKWARDS SOURCE: git mark not an ancestor of HEAD (rebase/rollback) → refuse-loud,
  render full history pointer + flag line; mark re-seeds at wrap. Ledger/notes/promoted
  ids are monotonic — backwards there implies store surgery → same refuse-loud path
  (UNCERTAIN: exact ancestor-check cost on Windows git — measure at build).
- TWIN RACE: CAS forward-only advance (above); the loser's stale advance no-ops.

## Refuted candidates (refute-first, own half)

1. MATERIALIZED DELTA EVENTS (writers push "changed" records at write time) — REFUTED:
   every writer must cooperate (new contract on N surfaces); pull-at-read composes the
   sources that already exist with zero writer changes — strangler fig over big-bang.
2. SINGLE-TIMESTAMP MARK — REFUTED: clock skew across sources + git is not time-ordered
   under rebase; per-source POSITIONS are the proven cursor pattern (T045's whole arc).
3. MARK INSIDE THE LANE CURSOR HASH — REFUTED: conflates DELIVERY (consume semantics,
   fenced generations) with COMPREHENSION (digest semantics, wrap-time advance); two
   advance disciplines in one hash invites exactly the gen-vs-0 class of bug the wiring
   fence caught.

## Build shape (for the reconciliation, not binding)

core/context/delta.py (mark read/advance via Store CAS + per-source renderers) +
`delta` verb in agent_cli + boot/wake integration points + pins: mark-advance-at-wrap
(crash redelivery), packet-law budget refusal, markless degrade, backwards-git refusal,
boot-shrink measurement. Tier at registration: FENCE-LITE for the build (new module +
render integration, no core/comm surface) — the reviewer confirms.
