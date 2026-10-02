---
akashic_id: art_20261001_the-record-is-total-map_7c2e6b
akashic_sha: 8ea248391de4
schema_version: 1
status: current
type: report
date: 2026-10-01
title: the-record-is-total-map
gist: "# THE RECORD IS TOTAL — map: one spine, four gaps, no new spine STATUS: MAP (read-only, nothing welds from this document) AUTHOR: deepseek ("
visibility: fleet
body_type: markdown
seats: []
category: [memory, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-01T23:48:12"
updated: "2026-10-01T23:48:12"
---
<!-- GENERATED PROJECTION of art_20261001_the-record-is-total-map_7c2e6b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# the-record-is-total-map

# THE RECORD IS TOTAL — map: one spine, four gaps, no new spine

STATUS: MAP (read-only, nothing welds from this document)
AUTHOR: deepseek (Heimdall), with Daniil (decisions: pointer-not-content, map-before-weld)
DATE: 2026-10-01
DECISIONS ALREADY MADE BY DANIIL, recorded so they survive:
  - D1: the spine carries POINTERS, not content. Sensitive bytes (prompt/response/reasoning
        bodies) stay OUT of the spine and are reached by reference to where they already
        live. Redaction stays a future, SEPARATE slice (it is NOT required before we wire).
  - D2: MAP FIRST, WELD SECOND. This document is the map. No one welds until the map is
        read, challenged, and ratified by the people who will maintain the weld.

## THE ONE-LINE

The spine already exists. It is the event firehose (`events:raw`, `core/events/`), the
append-only, time-ordered, lossless-pointer substrate BENEATH the narrative spine
(`core/narrative/`, System 4). We are NOT building a second spine. We are closing the four
gaps where live-, wire-, and seat-facts are recorded in private files that the spine cannot
see, so that the spine becomes TOTAL and `status`/`timeline`/`eye`/`doctor` become read-views
over ONE source of truth instead of rival assemblers.

## WHAT ALREADY EXISTS (the layers, grounded)

Layer            | Module                         | What it is                          | Status
-----------------|--------------------------------|-------------------------------------|-------
RAW FIREHOSE     | core/events/event_log.py       | append-only raw events, time-ordered| BUILT
  stream         | events:raw (maxlen ~100k)      | "what HAPPENED, in order"           | BUILT
  per-agent      | events:{agent}:raw (maxlen 10k)| convenience index                  | BUILT
  pointer        | event:<stream>:<id>            | followable ref, usable as Beat.source| BUILT
  kind vocab     | OPEN (tool_call/file_edit/command/observation/message/note)| extensible by string | BUILT
NARRATIVE SPINE  | core/narrative/ (System 4)     | Beat -> Chapter -> Track -> Atlas   | BUILT
  bridge         | core/narrative/event_bridge.py | raw <-> narrative pointers          | BUILT
  promoter       | core/narrative/event_promoter.py| salient raw events -> Beats         | BUILT
NEUTRAL FACT LAYER (the gaps live HERE)                                  | see below
  wire journal   | scripts/wire_journal.py         | Wireshark-grade METADATA (T156)     | BUILT but SILOED
  worklive       | core/comm/liveness.py           | phase/since_ts/beat_ts/turn/code_sha| BUILT but EPHEMERAL
  roster beat    | core/comm/roster.py             | LIVE/STALE/DEAD ladder              | BUILT but EPHEMERAL
  activity       | core/comm/wake_seat.py          | .alive marker touched at hooks      | BUILT but SILOED
  expected note  | core/comm/resume_on_deaf.py    | claim "should be reachable"         | BUILT (the janitor gap)
READ/CONSUMERS   | doctor.py, seat_topology.py, eye| current status/forensics/search     | BUILT but re-derive

## THE FIELD MODEL (the spine's contract — this is what "one source of truth" MEANS)

A raw events:raw record is exactly {at, agent_id, session_id, kind, summary, detail, track,
refs}, emitted via `capture_event(kind, summary, ...)`. `kind` is OPEN (a new fact = a new
string, no schema churn). `detail` carries rich-but-bounded structured context (max 8000
chars). `refs` carries followable pointers. THIS is the shape every gap must emit into.

## THE FOUR GAPS (what is NOT on the spine yet)

GAP 1 — WIRE. wire_journal writes metadata (system_fingerprint, finish_reason,
            reasoning_tokens, cache hit/miss, x-ds-trace-id, ratelimit headers) to
            state/wire/ private files. It is metadata-only BY DOCTRINE (no bodies) and
            already fail-open-with-counted-drops. It is NOT captured into events:raw, so
            "finish_reason=length at 03:12" is invisible to the spine and to eye.
            -> ROUTE: each wire record also emits a raw event (kind='wire', detail=the
               metadata, refs=[x-ds-trace-id]). Bodies stay out (D1).

GAP 2 — WORKLIVE BEATS/PHASES. liveness.write + roster.heartbeat write REDIS KEYS with a
            45s/180s TTL. A phase transition ("idle" -> "thinking" -> "handling") or a
            wedge (since_ts ageing) is a MEANINGFUL EVENT that evaporates after the TTL.
            -> ROUTE: on PHASE CHANGE and on WEDGE (not every 5s refresh -- that's spam),
               emit kind='beat' / kind='phase' / kind='wedge' with detail={phase, since_ts,
               turn, code_sha}. The 5s refresh stays a TTL key (it is a STATE, not an event).

GAP 3 — ACTIVITY. touch_activity writes a temp-dir .alive stamp. It is a fact ("a hook
            fired") with no spine record.
            -> ROUTE: keep the .alive file (it is a cheap fast-path the janitor reads), but
               ALSO emit kind='activity' (throttled -- NOT per-hook, or it drowns the
               firehose; one emit per turn-idle -> active transition is enough).

GAP 4 — EXPECTED-NOTE / JANITOR. declare_expected writes a claim file; retract_expected
            deletes it; the JANITOR (the missing slice from the earlier ruling) revokes
            stale claims. NONE of this is on the spine.
            -> ROUTE: emit kind='expected' on declare, kind='retract' on stand-down,
               kind='revoke' on janitor-revoke. Then the claim-vs-fact reconciliation
               becomes a DERIVED VIEW over the spine (replay declare/revoke), not a
               separate file scan.

## THE READ-VIEWS (what becomes possible once the gaps are closed)

  status <agent> [--depth 1|full|wire]   one verb, one source, varying fidelity
      depth=1     latest beat + phase + turn + code_sha           (worklive head)
      depth=full  the whole ladder + recent wire summaries         (roster + events)
      depth=wire  last N wire events: trace-id, finish_reason, reasoning_tokens, cache
  timeline <agent> [--from t] [--to t]   "origin until now" -- replay events:{agent}:raw
                                          from a bookmark, ordered. This IS Layer 1 grouped.
  eye                                   already indexes the corpus; point it at events:raw /
                                          per-agent so "what did the operator keep asking"
                                          and "what was this seat's finish_reason at 03:12"
                                          become ONE query surface.

All three become READS OVER THE SAME SPINE. No new writer. No new store. This is the
consolidation Daniil asked for, expressed as wiring, not building.

## THE DOCTRINE THAT MUST HOLD (the line Daniil's D1 preserves)

  - events:raw holds what HAPPENED + pointers (D1). It is the lossless-pointer substrate.
  - Sensitive CONTENT lives where it already lives (transcripts eye indexes, state/wire for
    wire metadata). The spine POINTS at it via `refs`, never inlines it.
  - The narrative spine stays the SALIENT distillation. The firehose stays the RAW detail.
    Total firehose does NOT mean "narrative stops mattering" -- it means narrative Beats
    can now point at wire/beat/seat facts too, not just tool calls.

## WHAT WE ARE DELIBERATELY NOT DOING (scope discipline)

  - NOT building redaction/DLP now (D1 says pointers; redaction is a future separate slice).
  - NOT storing prompt/response bodies (reaffirm wire_journal's metadata-only doctrine).
  - NOT turning the 5s heartbeat refresh into a per-second event firehose (state vs event).
  - NOT touching the narrative schema. We extend its reach (more kinds reachable), never
    its shape.
  - NOT folding the temp-dir .seen/.arming sidecar cleanup into this (that is a SEPARATE
    janitor, already noted in stale-note-landscape-empirical-map).

## THE WELD ORDER (proposed, after ratification)

  1. Gap 2 (worklive phase/wedge) — highest signal, hooks already exist at the work path.
  2. Gap 4 (expected/retract/revoke) — it closes the earlier janitor ruling AND lands on
     the spine in one move.
  3. Gap 1 (wire) — one line per wire record; bodies stay out per D1.
  4. Gap 3 (activity) — throttle to transitions, last, because it is the lowest value/byte.

  Each weld is a SMALL slice with its own pre-registered pin: "the gap fact now appears on
  events:raw with kind=X and a followable ref." No big-bang.

## OPEN QUESTIONS FOR THE PEOPLE WHO MAINTAIN THIS (not decided here)

  Q1. Throttle knob for activity (Gap 3): per-turn-transition, or a minimum-interval?
  Q2. Should `status`/`timeline` be NEW verbs, or should `doctor`/`unwedge` gain `--depth`
      and `timeline` absorbs `seat_topology.py`? (I lean: extend doctor, retire the script.)
  Q3. Does `eye` index events:raw directly, or does it keep indexing transcripts and JOIN to
      the spine by session_id? (This is the one "ever more clever navigation of the Akashic
      record" hinge.)
