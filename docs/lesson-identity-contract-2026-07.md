# Lesson & Note Identity — the Observation/Projection Contract

Status: current  (2026-07-20, written to make an already-shipped discipline explicit)

Purpose: pin down, in one place, the identity + replay semantics our append-only substrate
already practices — so "never rewrite" can never quietly drift into duplicate inflation or
an accidental last-write-wins store. Nothing here is new behavior; every rule below cites
the shipped mechanism that enforces it. (Prompted by an external convergence question,
answered entirely from our own architecture; no external code was consulted.)

## The law

1. **Identity is a stable logical key, chosen at birth.**
   - Lessons: `experiment_name` ([learning_store.py](../core/learning/learning_store.py), dedup key).
   - Notes: the `title` ([agent_cli.py](../agent_cli.py) `note` verb — "re-note same title to update").
   - Bus replies: the answered message id (reply-sent sentinel,
     [bifrost_runner_deepseek.py](../scripts/bifrost_runner_deepseek.py) `REPLY_SENT_PREFIX`).

2. **Observations are immutable appends under that identity.** The Ledger/event stream is
   append-only; a correction, a counter-evidence finding, or a re-run is a NEW observation
   under the SAME identity — never an edit of a prior record.

3. **The current fact is a projection (a fold), never the last write.**
   - Notes: latest-by-title wins the *render*; priors are retained and labeled
     `superseded` (T021 supersession; `--supersedes` / `--retire` are explicit verbs,
     and boot renders current-only).
   - Lessons: evidence ACCUMULATES and is WEIGHED — usefulness/noise counters
     (`recall-feedback`, the funnel), anti-pattern tags (`tag-anti-pattern` marks an
     existing lesson as known-bad without deleting it). A contradicted lesson is not
     overwritten; it is out-projected by its own evidence trail.

4. **Exact replay is a no-op; changed content is a new observation.** Same identity +
   same content deduplicates (LearningStore dedup-as-idempotency; RB-26 consumers stay
   idempotent under at-least-once redelivery; the reply sentinel makes answers
   effectively-once). Same identity + changed content appends.

## New identity vs. new observation — the decision test

> **Does this record make a claim about the same subject as an existing record?**
> Same subject → same identity, new observation (correction, counter-evidence, refinement).
> New subject → new identity (and link it: `[[related]]` edges / `mark_related`).

Practical corollaries:
- A fix to a wrong lesson = new observation under the same `experiment_name`
  (or an anti-pattern tag on the old one) — never a near-duplicate name. Near-duplicate
  names are the "duplicate inflation" failure the stable key exists to prevent.
- A note that replaces a plan = re-note the SAME title (supersession chain), unless the
  plan's subject genuinely changed (then new title + `--supersedes` the old id).

## Replay & recovery semantics (the part that must hold under crash)

- **File is the source of truth; Redis is a projection.** Boot heals Redis FROM the durable
  File — live receipt 2026-07-20: `[heal] Redis was behind -- backfilled 330
  key-structure(s) from the durable File (File is source of truth)`.
- **Acceptance is convergence, not completion:** after replaying the same completed
  observation sequence, the projected state (boot context, notes render, recall surface)
  must converge to the same facts — proven by the snapshot/restore drill
  (scripts/snapshot_knowledge.py, restore-tested) and the boot heal path.
- Append/TTL-trimmed families may legitimately run Redis-ahead of File (events, beats);
  UNKNOWN Redis-only keys in a durable family are a defect signal, not noise
  (the boot heal report already grades these).

## What this contract forbids

- Editing a persisted observation in place (that is a rewrite, not a supersession).
- Retiring evidence by deletion (use anti-pattern tags / supersession labels; archaeology
  must stay possible: `notes --all`).
- Minting a new identity to dodge a bad track record (the funnel's counters are the
  record; a rename that resets them is a Goodhart move).
- Any projection that resolves conflicts by wall-clock last-write-wins instead of an
  explicit fold rule (supersession chain, evidence weighing).
