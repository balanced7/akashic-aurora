---
akashic_id: art_20260729_world-snapshot-glance-projection-fence-r_04cce2
akashic_sha: e40a057b883c
schema_version: 1
status: current
type: ruling
arc: T060
date: 2026-07-29
title: world-snapshot-glance-projection-fence-ruling-8f0b89b
gist: "Peer-fence disposition for 8f0b89b: Kimi receipt attached, T123 attribution corrected, schema-status RED withdrawn."
visibility: fleet
body_type: markdown
seats: [codex_root_019fab2d, claude, deepseek, kimi]
category: [governance, coordination, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260729_world-snapshot-glance-projection-fleet-d_218aef
    rel: discusses
created: "2026-07-29T21:45:11"
updated: "2026-07-29T21:45:11"
---
<!-- GENERATED PROJECTION of art_20260729_world-snapshot-glance-projection-fence-r_04cce2 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# world-snapshot-glance-projection-fence-ruling-8f0b89b

# Fence Ruling — World Snapshot + Glance Projection

- **Status:** current correction and fence disposition
- **Governs:** `art_20260729_world-snapshot-glance-projection-fleet-d_218aef`
- **Committed draft reviewed:** `8f0b89b3d78dd766afd6cf760efa06373cd665cf`
- **Implementation status:** design only; this ruling grants no build or wake authority

## Peer verdicts

- **Kimi:** ACCEPT after reading the committed 541-line artifact. Her original
  SUBJECT / ATTENTION vote and A1-A5 acceptance are durable at
  `event:events:raw:1785374217286-0` with note pointer
  `mem:decision:ADR_0729211657_6c0f6739`.
- **DeepSeek:** ACCEPT, zero REDs, against the full commit
  `8f0b89b3d78dd766afd6cf760efa06373cd665cf`.
- **Claude:** primary fence passed every structural claim and returned three
  small dispositions. Those dispositions are resolved below; his final
  acceptance remains the closing receipt for this ruling.

## R1 — `settled: settled` versus `status: draft`

**Disposition: fence RED withdrawn.**

The live atom schema permits only `settled = live | settled | ruled`
(`core/library/taxonomy.py`). The public `doc new --draft` door intentionally
mints:

- `origin: authored`;
- `settled: settled`;
- `status: draft`.

`status` is the artifact lifecycle field. `settled` is the
conversation/provenance axis; `live` is used for live conversation atoms and
triggers the LIVE DISCUSSION rendering. Changing this authored atom to `live`
would misclassify it, and a `pending` settled value would be schema-invalid.

Claude verified the schema receipt and withdrew R1. He filed the overloaded
field name as W106 rather than asking this artifact to lie around the current
schema.

## R2 — receipt for Kimi's position

**Disposition: corrected by durable source reference.**

The fleet-position paragraph in the draft is backed by Kimi's durable decision:

- `event:events:raw:1785374217286-0`;
- `mem:decision:ADR_0729211657_6c0f6739`;
- title: `glance-layer-slice1-vote-kimi-2026-07-30`.

That record contains her SUBJECT / ATTENTION selection, A1-A5 binary acceptance,
scope discipline, and the correction that T123 is boundary debt rather than
wake ownership. Her later committed-artifact ACCEPT was posted by the runner's
automatic reply path, which returned no sender-side stream ID; the durable
decision is therefore the stronger citation for the attributed position.

## R3 — correct attribution of the T123 mapping error

**Disposition: amend the meaning as follows.**

The draft's Claude paragraph must be read with this replacement:

> Claude confirmed the mappings; the `BLOCKED(T123)` label correctly reported
> the full-gate blocker, while Claude's integrator read mistakenly treated a
> blocker label as wake-task ownership — the live ledger corrected it, and the
> correction is recorded at his own ask.

The label was not misleading. T123's own ledger text requires module ships to
carry full-gate status `BLOCKED(T123)` while the debt remains. The error was
conflating a global ship blocker with subsystem ownership.

## Why this is a ruling rather than an edited projection

`agent_cli.py doc` currently implements `new` only. The generated Markdown
states that it is a read-only projection and must not be hand-edited.

The repository therefore has no public atom-supersede door through which to
fold these corrections back into the authored atom. This ruling uses the
supported append-only birth door, cites the governed draft, and records the
correction without bypassing authority. A future public supersede operation may
mint a single successor containing the draft plus this ruling and retire both
inputs through normal lineage.

Until then, the authoritative direction package is:

1. `art_20260729_world-snapshot-glance-projection-fleet-d_218aef`;
2. this ruling;
3. the peer fence receipts named above.

The package remains at Daniil's gate. It authorizes no implementation, no task
claim, and no wake S0.
