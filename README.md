# Akashic Aurora

*A self-curating memory and knowledge system for AI agents — local-first, append-only, and built to get better over time instead of decaying.*

---

## The name

- **Akasha** — in Sanskrit, the *aether*: the medium that holds the record of everything. Here it is the
  immutable, append-only **substrate** — the Ledger of every atom the system has ever seen (learnings,
  narrative beats, raw events). The record is sacred; it is never rewritten or deleted.
- **Aurora** — the light that *dawns and dances across that sky*. Here it is the self-organizing **knowledge**
  that emerges over the record: the narrative spine, the Codex, the moment of recall and insight. Order, lit up.

> **Akashic Aurora**: order emerging luminously from the total record. Anti-entropy as a dawn that keeps coming.

## What it is

A single-user, local-first environment that lets autonomous coding agents (Claude, Cursor, OpenCode) **remember
their own work as a navigable story**, **self-curate** what they've learned so it sharpens rather than sprawls,
and **coordinate** with one another — all on one machine, degrading gracefully when infrastructure is down.

Two organizing ideas:

1. **One immutable substrate, many derived projections.** *Atoms* are append-only and sacred. Everything else —
   tags, chapters, knowledge resources — is a *regenerable projection* over atoms, never a precious hand-edited
   file. The **narrative spine** projects atoms by *time* (`Beat → Chapter → Atlas`); the **Codex** projects them
   by *topic* (`Resource → tree`). Both share the same machinery.
2. **Governance-as-CRDT.** Derived values are confidence-scored *opinions* over immutable *facts*; the resolver is
   a lattice join (`max by confirmed, confidence, recency`), so repeated or reordered cleanup runs **converge and
   can never degrade data**. Corrections *supersede*, they don't delete.

## Architecture, in one breath

- **Foundation (S0):** `Store` (Redis+File hybrid, graceful fallback), `Ledger` (append-only streams), a tz-safe
  time layer, a 66-type relationship vocabulary.
- **Primitives (cross-cutting):** `Ranker`, `Distiller`, `Supersession`, `Consolidator`, `Embedder`, `Clusterer`.
- **Domain (S1–3):** learning store + episodic memory, an event firehose with a time-indexed read model, agent
  coordination signals.
- **Projections (S4):** the **narrative spine** (Chronicler, TrackRouter, bi-temporal chapter lifecycle,
  tag-governance CRDT) and the **Codex** (Resources over embedding clusters); **Perspectives** (swappable lenses).
- **Interface (S5):** a single CLI "agent door" + the agent-comm bus.

## Status

- **Wave 1 — spine hardening:** complete (silent recall loss, router precision, confidence robustness, timezone
  safety, observability).
- **Wave 2 — the Codex (self-curating knowledge):** in progress — embedding substrate, shared consolidator,
  clusterer, and the Resource lifecycle are in; the curator loop is next.
- Built in small, test-gated slices with an automated layer-boundary checker. **297 tests green** at last mirror.

## Where to read next

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the synthesis (layers, waves, what's done)
- [`docs/LEXICON.md`](docs/LEXICON.md) — the ubiquitous language
- [`docs/codex-plan.md`](docs/codex-plan.md) + [`docs/codex-inventory.md`](docs/codex-inventory.md) — the current build
- [`docs/tag-governance-plan.md`](docs/tag-governance-plan.md) — the CRDT governance + safety invariants
- [`AGENTS.md`](AGENTS.md) — the agent-facing contract

*A personal research project. Names must not lie; the record must not decay.*
