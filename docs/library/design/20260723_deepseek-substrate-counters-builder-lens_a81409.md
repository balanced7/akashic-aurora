---
akashic_id: art_20260723_deepseek-substrate-counters-builder-lens_a81409
akashic_sha: 69583c586afd
status: current
type: design
arc: artifact-substrate
date: 2026-07-23
title: "deepseek substrate counters (builder lens, T101 advisory round)"
gist: "Captured verbatim from the live bus (research-full-fidelity rule); no edits. --- # Substrate Counters — deepseek (builder/feasibility lens) "
tenant: solo
visibility: fleet
seats: [deepseek]
category: [substrate, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_the-codex-a-self-curating-knowledge-laye_302fc9
    rel: cites
created: "2026-07-23T19:42:59"
updated: "2026-07-23T21:42:09"
---
<!-- GENERATED PROJECTION of art_20260723_deepseek-substrate-counters-builder-lens_a81409 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# deepseek substrate counters (builder lens, T101 advisory round)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

# Substrate Counters — deepseek (builder/feasibility lens) — 2026-07-23

Status: current
Type: design (counter) · Arc: artifact-substrate (T101) · Seats: deepseek · Date: 2026-07-23

NOTE: write_mode is READ-ONLY this session — the file research/drafts/deepseek-substrate-counters-2026-07-23.md could NOT be written to disk. Full content here on the bus. Someone with write access please file it. The summary is in the preceding bus reply.

---

## 1. THE 6 DELTAS — ranked with builder costs

### #1 (LOAD-BEARING): Delta 1 — YAML frontmatter projection (Obsidian Bases = free viewer)

**Verdict: CORRECT, load-bearing, near-zero cost. Wrong detail: it's not "just a flag."**

The scan says "render headers as YAML frontmatter." I own gen_library — here's the real path.
`_extract()` at `scripts/gen_library.py:55-81` already parses every header field into a dict:
`status, type, arc, seats, date, superseded, heading`. The projection writes these back as prose
(`render_shelves` at L140; `_render_zone_readme` at L200; `render_arcs` at L278).

Emitting YAML frontmatter instead of prose is a **format toggle in the render path**, not a new
parser. The same dict → `---\nstatus: current\ntype: design\n...\n---\n\n# Title\n\n{body}`.
~15 lines changed in gen_library for the flag; ~20 lines for the one-file incremental re-render
that kimi's Q8.5 needs (`gen_library --one doc:abc123`). The existing `walk_docs()` already
returns per-file entries — incremental is just "walk one, render one."

**Cost:** trivial (≤50 lines). **Failure surface:** zero new moving parts — same parser, same
renderer, different format string. **Wrong detail in the scan:** "budgeted custom viewer work"
— the YAML frontmatter toggle ELIMINATES the custom viewer line item. Obsidian IS the viewer.
The console pane + CLI remain the fleet's doors; Obsidian is Daniel's browse surface. No
either/or.

### #2 (LOAD-BEARING): Delta 2 — Audit `library` domain (knowledge-base lint)

**Verdict: CORRECT, load-bearing for substrate health, medium build cost.**

The scan nails the need. gen_library already detects 3 of the 7 lint signals (unmarked status,
untyped, unreadable). The remaining 4 (staleness 3+ weeks, orphans missing from indexes,
frontmatter compliance, contradictions) all reduce to: walk the atoms, check properties, flag.
The audit verb already walks structured records; adding a domain is ~40 lines of rules plus
~30 lines of gate wiring (Daniel's review surface).

One correction: "duplicate-current" is NOT detectable by lint alone. When kimi's atom
supersession and my JSONL append both mark `status: current` for the same arc, detection
requires cross-reading the store's supersession chain. That's a store query, not a file scan.
The audit domain should delegate to the store for this check, not walk the projection.

**Cost:** medium (70 lines + store query integration). **Failure surface:** low — report-only,
Daniel-gated fixes, same genus as existing audit rows.

### #3 (LATER WAVE — CORRECTLY PARKED): Delta 6 — Distillation layer (Codex C3/C4)

**Verdict: CORRECT, correctly parked as LATER. Do NOT block the substrate on this.**

Entity/concept pages compiled from atoms = the Resource layer in docs/codex-plan.md (parked
C3/C4). The scan says "unpark eventually" — agreed. But this is a 300+ line design with its
own birth door, query surface, and drift story. The SUBSTRATE must ship first; distillation
reads FROM it. **Wrong if anyone reads this as v1 scope.** Flag: the scan's framing "unparked
as a LATER wave" is the right posture.

### #4 (ENCODE, DON'T BUILD): Delta 5 — Karpathy warnings as explicit bars

**Verdict: MOSTLY ALREADY PRESENT. Encode in AGENTS.md, don't build new machinery.**

"Lint is mandatory-periodic" = rule-10 in docs/LIBRARY.md (push-lint + wrap census). "Write-
time dedup at team scale" = the supersession chain kimi's atom design + my JSONL append both
provide. The delta is making these explicit CONSTRAINTS, not inferred properties. Cost: 4
lines in AGENTS.md or LIVE_CONSTRAINTS.md. Not a build task.

### #5 (POST-SUBSTRATE): Delta 3 — Size-capped hot tier with demotion triggers

**Verdict: VALUABLE, but post-substrate. Wrong if prioritized before the store ships.**

Kiro's 150-line short-term-memory with demotion triggers is a boot-surface optimization.
It reads FROM the store — the store must exist first. The demotion trigger (>1-line push down)
is design-heavy: what counts as "one line," what surface it pushes to, how auto-demotion
interacts with Daniel's gate posture. Cost: medium design + medium build. Rank it AFTER the
substrate migration, not during.

### #6 (NICE, NOT LOAD-BEARING): Delta 4 — Staging inbox

**Verdict: CORRECT instinct, wrong cost attribution. The birth guard already solves this.**

The scan's "Temp Ingest/ folder swept by library lint" is a folder + a lint rule. But the birth
guard (pre-commit REFUSE on naked .md creation) already prevents loose files from landing in
docs/ and research/. A staging inbox adds a second path (write to inbox → lint promotes → store)
when the birth door is the only path that should exist. **Counter: merge this into the birth door
as a `--draft` flag** — the atom is born with `status: draft`, the library lint promotes it.
One path, two states. Don't create a separate physical zone.

---

## 2. YAML FRONTMATTER RENDER FLAG — builder's cost breakdown

gen_library's render path (`scripts/gen_library.py`):

```
Current:  _extract() → dict → render_*() → prose header in markdown
Proposed: _extract() → dict → render_*() → YAML frontmatter in markdown
```

The header dict fields map 1:1 to YAML frontmatter:

```yaml
---
status: current
type: design
arc: artifact-substrate
seats: deepseek
date: 2026-07-23
heading: Substrate Counters
akashic_id: doc:abc123def456
akashic_sha: a1b2c3d4e5f6
---
```

**Incremental re-render (kimi's Q8.5 door-expense):** gen_library currently does full-corpus
walk. For one-atom → one-file: add a `--one <id>` flag that walks a single atom (from store or
JSONL), renders it to `docs/library/<type>/<id>.md`. The render function already operates on a
single (path, header) tuple — no architectural change. ~30 lines. The door then becomes:
`doc new` → atom stored → `gen_library --one <id>` → one file updated. Cost: one file write per
birth, not a full regen. This KILLS kimi's Q8.5 worry — the door is as cheap as Write-a-file.

**The checksum self-verification:** add `akashic_sha` to the frontmatter. The projected file
carries the hash of the atom's body. Audit domain reads: `atom.body_sha == projection.frontmatter.akashic_sha`
→ drift detected mechanically, zero false negatives. This is the kill-shot for kimi's Q8.3
(dual-truth risk) — the projection is self-verifying. Cost: `hashlib.sha256(body).hexdigest()[:12]`
in the render path. 3 lines.

---

## 3. CORPORATE AXIS — JSONL-per-type-in-git at 100k+ atoms

**The honest builder answer: my JSONL-per-type design survives solo → small-team, bends
at ~50 concurrent writers, breaks at corporate without an adapter seam.**

- **0–5 writers (now):** JSONL-in-git is correct. Adjacent-line appends merge trivially. A
  JSONL file with 2,000 lines is ~400KB — git operations are instant. No store dependency.
- **5–20 writers (growing team):** Merge conflicts on JSONL files become non-zero. Two agents
  superseding the same atom append adjacent lines; git merges fine. But two agents filing
  DIFFERENT documents simultaneously to the SAME JSONL produce interleaved lines; git merge
  resolves trivially (both lines land). The store's timestamp-based `current` resolution still
  works. **First break point: the post-merge JSONL needs a `--repair` pass to reconcile
  duplicate-current-status.**
- **20–50 writers (team scale):** Git push contention on `briefs.jsonl` becomes the bottleneck.
  One agent pushes; the other's push is rejected (non-fast-forward). The rebase is trivial
  (ad
[clipped at 8000 chars -- full content did NOT send; resend in chunks]
