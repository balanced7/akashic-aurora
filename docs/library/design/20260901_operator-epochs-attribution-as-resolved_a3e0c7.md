---
akashic_id: art_20260901_operator-epochs-attribution-as-resolved_a3e0c7
akashic_sha: c10c79a600b3
schema_version: 1
status: current
type: design
arc: estate-program
date: 2026-09-01
title: operator-epochs-attribution-as-resolved-view
gist: "New-operator attribution: an epoch registry resolves operator display by record timestamp+origin (seed=epoch0 unconditionally); rename-forever, succession-born, zero rewrites; rides the OPERATOR_ID sweep"
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T21:49:32"
updated: "2026-09-01T21:49:32"
---
<!-- GENERATED PROJECTION of art_20260901_operator-epochs-attribution-as-resolved_a3e0c7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# operator-epochs-attribution-as-resolved-view

# Operator epochs — attribution as a resolved view, never a rewritten field

*Design position, 2026-09-01 night, from the operator's ask: a new Akashic Aurora operator must be able to flag all inherited lessons and utterances as "the prior operator" (or any name they choose) and have everything they produce attributed to themselves. Companion to the seed-sanitize run (research/in-flight/seed-sanitize-2026-09-01/) and the global-tags design conversation. Status: position; fence it with the tags round.*

## The mechanism

**1. The registry.** One small record of operator eras, store-held and config-mirrored:

    operator:epochs = [
      {epoch: 0, id: "founder", display: "<chosen at install, default 'the prior operator'>",
       from: null, until: <install moment, offset-carrying stamp>},
      {epoch: 1, id: "<their operator-id>", display: "<their name>",
       from: <install moment>, until: null}
    ]

**2. The boundary.** The installer's IDENTITY step gains one ask: *"How should inherited lessons refer to this corpus's previous operator?"* — default "the prior operator"; they may choose "the Founder" or credit upstream by name. Install stamps epoch 0's `until` and epoch 1's `from` with the same instant.

**3. The resolver.** Operator attribution for any record = epoch lookup by the record's own timestamp, with origin as the belt over the clock's suspenders: `origin == "seed"` resolves to epoch 0 UNCONDITIONALLY — seed records are pre-boundary by construction, so no naive-timestamp parsing ambiguity (T119's dual-era lesson) can ever mis-attribute them. Records the new house writes carry no seed origin and post-boundary stamps: theirs by both tests.

**4. Body text.** Our sanitize role-formed prose to "the operator" / `<operator-id>`. At import, the installer runs the SAME transform machinery one more hop with their parameters: role forms in seed copies become their chosen prior-name ("the prior operator ruled..."), so a seed lesson and a native lesson can never be confused in prose either. Quoted speech stays verbatim — quotes are content; attribution is a plane.

**5. The utterance plane generalizes free.** Any timestamped record type (notes, atoms, chronicle rows, promoted bus speech) resolves through the same registry — including the known house defect class where dispatch briefs record as operator speech (lesson dispatch_briefs_are_recorded_as_operator_speech...): speaker resolves through provenance, never through which lane a record rode.

**6. Tags close the loop.** `epoch:seed` / `epoch:native` becomes a queryable tag dimension for the eye: "show only what THIS house learned" is one filter, and the tag-hit telemetry from the measurement design separates inherited advice from lived experience in the tuning numbers.

## Why a view and not a field rewrite

- **Rename forever, rewrite never.** The operator (or their successor) edits one registry row and every rendering updates — the exact property the seat callsign/agent_id split already proved (T088b), now symmetric for operators. A stamped field would need a corpus rewrite per rename.
- **Succession is born supported.** A third operator appends epoch 2. A seed-of-a-seed carries the lineage chain: founder → first stranger → their successor. The house can be handed down.
- **Zero-risk to retrieval.** Nothing in ranking reads the registry (identity_strings_are_not_load_bearing_for_retrieval_measured, replicated tonight at corpus scale, 59/60 slots). Attribution changes cannot move recall.
- **It is the lens law.** a_magnitude_axis_is_a_lens_not_a_filing_location: record richly once, project views per reader. Attribution is the canonical lens.

## Build shape (rides existing lanes)

The resolver lands inside the OPERATOR_ID sweep already scoped (the ~15-site literal cleanup: `OPERATOR_ID` becomes "current epoch's id"). The registry is one store key + one config block the installer writes. The import transform is the sanitize pipeline with different parameters. First rendering surface: the recall-at hook prefix. Acceptance, RED first: (a) a seed record renders prior-name in boot/recall on a fresh install regardless of clock skew; (b) a native lesson filed one minute after install renders the new operator's name; (c) renaming the prior operator in the registry re-renders history with zero record writes.
