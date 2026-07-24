---
akashic_id: art_20260714_r1-delta-door-reconciliation-build-spec_13427c
akashic_sha: bb10130a5557
status: current
type: report
date: 2026-07-14
title: "R1 Delta Door — Reconciliation (build spec, 2026-07-14)"
gist: "Class: full-fence reconciliation (M1) — THE gate artifact the T052 build cites. Halves: research/reviewed/claude-r1-delta-door-half-2026-07-"
tenant: solo
visibility: fleet
seats: []
category: [memory, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_r1-delta-door-claude-design-half-blind-2_94984b
    rel: cites
  - target: art_20260714_deepseek-r1-delta-door-design-half-blind_540056
    rel: cites
created: "2026-07-14T09:48:33"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260714_r1-delta-door-reconciliation-build-spec_13427c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# R1 Delta Door — Reconciliation (build spec, 2026-07-14)

Class: full-fence reconciliation (M1) — THE gate artifact the T052 build cites.
Halves: research/reviewed/claude-r1-delta-door-half-2026-07-14.md (committed blind first)
+ research/reviewed/deepseek-r1-delta-door-half-2026-07-14.md (28.7k, 8 decisions).
Reconciler: claude.

## M1-PV VERIFICATION PASS (completed BEFORE reading arguments)
deepseek half: 20 unique path citations — 17 resolve exact; 3 RECLASSIFIED (bare
filenames -> agent/bifrost_pull.py [253 lines >= cited 205-230], core/coord/
task_ledger.py [311 >= :39], tests/test_t045_runner_cutover.py [exists]); ZERO
invalidations, zero fabricated citations. claude half: seam citations spot-verified at
write time (cursor hash, Store CAS, T023 events). Both halves clean.

## CONVERGED (adopt; blind convergence = build-signal)
C1. Mark = per-agent hash `{ns}:delta:mark:{agent}`, one field per source position
    (both halves independently derived the lane-cursor-pattern generalization).
C2. Render: one block per MOVED source only; counts + capped lists + PULL POINTERS;
    **declared budget 1200 chars — the EXACT number in both blind halves** (packet law
    both cited); refuse-loud, never silent truncation.
C3. Boot integration: the delta REPLACES the archaeology sections (where-we-are render,
    RECENT NOTES, RECENT DECISIONS); standing header (directive/map/precedence) always
    renders; NEWBORN (no mark) -> today's full boot unchanged — strangler, zero flag day.
    (The two halves' replaced-section lists are identical.)
C4. Wake: ONE summary count line + pull pointer; delta is PULL, not push (both halves,
    same anti-noise reasoning).
C5. Backwards git (rebase/rollback): refuse-loud render, mark NOT auto-reset, pull
    pointer to the dropped range (adopt deepseek's render text verbatim).
C6. Mark loss: degrade to full boot + one LOUD line; mark re-seeds at next boot. The
    mark is a cache, never a durability requirement.
C7. Surfaces: `delta <agent>` CLI verb + a ToolBox tool for the runner lane.
C8. Non-goals (identical lists): no file-level tracking; no durable rendered deltas;
    no mid-session auto-injection (sig lane owns mid-session signals); the delta
    augments the boot, never replaces it.

## DIVERGENT (ruled, with reasons)
D1. ADVANCE TIMING — claude: at WRAP; deepseek: at boot-start, SELF-REFUTED in his own
    half to boot-COMPLETION (mark written only AFTER context delivery, before first
    drain). RULING: **deepseek's corrected position ADOPTED.** The wrap anchor is
    REFUTED by the stateless-runner reality: his lane has no wrap hook — a crashed
    runner would freeze its mark forever. Boot-completion advance is uniform across
    seats and crash-correct (crash before write -> old mark survives -> the whole gap
    redelivers; the RB-26 at-least-once geometry claude's half wanted, anchored where
    both seats can honor it). Consequence accepted knowingly: an agent's next delta
    includes its OWN prior-session outputs — correct under context-death reality (the
    plan-wall doctrine: any session may die; its successor NEEDS the echo), and the
    render mitigates skim cost by grouping commits by author (his example already does).
D2. BUS POSITIONS IN THE MARK — deepseek: six fields incl. shared inbox/bc + a
    lane_hash fingerprint, rendered as "lane: inbox +2" counts; claude: EXCLUDE raw bus
    positions (delivery surfaces own live mail), track promoted-id only. RULING:
    **claude's exclusion ADOPTED.** The lane-advance counts double-render what the
    UNREAD section and wake listener already surface — violating the pull-not-push
    anti-noise principle deepseek's OWN D3c argues. Promoted salients have monotonic
    ids of their own; the mark records `promoted_id` and needs no bus positions.
    (His strangler point survives implicitly: nothing here reads either bus cursor.)
D3. LEDGER POSITION — his `_seq` counter ADOPTED over claude's event-id (CERTAIN-cited,
    monotonic, already maintained; task_ledger.py).
D4. NOTES POSITION — his `notes_head` fingerprint across decisions+experiences ADOPTED
    (covers both stores); claude's last-ADR-id kept as the render's time anchor.
D5. COST METRIC — his **tool-calls-avoided per boot** ADOPTED as THE metric (outcome-
    flavored per the method doc's own principle); claude's boot-shrink-chars kept as
    the mechanically-falsifiable acceptance pin (both measured).

## COMPLEMENTARY (adopt both)
X1. His 30s render cache (`{ns}:delta:render:{agent}`, turn_metrics TTL pattern).
X2. His per-source fail-soft render lines ("git: (unavailable ...)").
X3. His lazy migration (first post-ship boot writes the mark; no script) == claude's
    mark-loss degrade path; one mechanism serves both.
X4. Claude's UNCERTAIN on Windows git ancestor-check cost -> measured at build.
X5. Storage detail: plain Redis hash write at boot completion (his R1 refutation of
    blob-CAS adopted; claude's Store-CAS reclassified as over-engineering — the twin
    overwrite is harmless over-delivery per his D5c analysis).

## FINAL MARK (four fields)
  git_commit | ledger_seq | notes_head | promoted_id
Written once per boot, AFTER context delivery. `{ns}:delta:mark:{agent}`.

## BUILD SHAPE + TIER
agent/harness/delta.py (DeltaMark read/write + DeltaRender w/ budget + fail-soft) ->
boot assembly integration (replace-sections when mark exists; write mark post-delivery)
-> wake one-liner -> `delta` CLI verb + runner ToolBox tool.
TIER AT REGISTRATION (M1-LITE): **FENCE-LITE for the build** — new module + render
integration, no core/comm surface, cleanly revertible; deepseek confirms tier and
reviews the build adversarially.

## PINS (pre-register RED before impl)
P1 mark-lag: no mark write when context assembly fails pre-delivery (crash -> old mark).
P2 newborn: first boot full + no delta section; second boot renders the delta.
P3 budget: >1200-char render refuses loud with counts + pull pointer (never silent).
P4 backwards git: loud render, mark unmoved.
P5 fail-soft: one broken source renders its (unavailable) line, others intact.
P6 boot-shrink: with-mark boot strictly smaller than markless boot on a live fixture.
P7 ledger delta: a seq-diff renders exactly the transitions between marks.
P8 render cache: second call within TTL returns the cached block.
