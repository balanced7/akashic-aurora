---
akashic_id: art_20260719_the-master-map-documentation-as-projecti_a26fd3
akashic_sha: 9af25683542d
status: draft
type: brief
date: 2026-07-19
title: The Master Map — Documentation as Projection (Charter + claude opening position)
gist: "# The Master Map — Documentation as Projection (Charter + claude opening position) **Date:** 2026-07-19 · **Directed by:** Daniel (verbatim)"
tenant: solo
visibility: fleet
seats: []
category: [substrate, recall, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T11:27:58"
updated: "2026-07-19T11:27:58"
---
<!-- GENERATED PROJECTION of art_20260719_the-master-map-documentation-as-projecti_a26fd3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# The Master Map — Documentation as Projection (Charter + claude opening position)

# The Master Map — Documentation as Projection (Charter + claude opening position)

**Date:** 2026-07-19 · **Directed by:** Daniel (verbatim): *"how robust is our documentation? Do we have a full and up to date map of the logic, flow, recall mechanics, every system where and what it inputs and outputs are, all of the technical specifications about accepted filetypes, configuration flags. Basically a master map with every subcomponent also having a design and integration paper. I want you all to think on this and come up with the best, most elegant and fitting solution."*
**Fence:** claude opening (this doc) → deepseek counter (his lane: runner/ToolBox surfaces + the flags his code reads) → kimi walk when bandwidth allows (explicitly BEHIND his D2/D3 verify + W04 + TOON queue) → reconciliation → Daniel's gate.

## Scorecard — where documentation actually stands (receipts, 2026-07-19)

| Layer | State | Receipt |
|---|---|---|
| Narrative / orientation | **Strong** | ARCHITECTURE.md (living skeleton, orientation header DERIVED per T022), ROADMAP, JOURNEY, LEXICON, LIVE_CONSTRAINTS, AGENTS.md door contract |
| Module layer | **Strong + already derived** | docs/MODULE_INDEX.md is auto-generated (gen_arch_index.py; line-1 docstring = single responsibility; "Do NOT edit by hand") |
| Design papers (July arcs) | **Spec-grade** | method-baseline M-contract: every gated slice cites a dated reconciled build spec; packet-spec-v1, comms-mailbox-design, reasoning-spine-design, t039 lanes/latches… |
| Design papers (June-era pillars) | **Thin** | Store/Ledger, recall internals, learning store, chronicles: code + memory summaries, few method-grade papers with integration sections |
| Currency enforcement | **Exists, currently RED** | check_doc_currency.py FAILS with 8 violations right now (unstamped/bad-vocab docs from the last 48h sprint + one stray misnamed file) — the guard works; the sprint outran the gate |
| Content currency (doc ↔ code) | **Unenforced** | today alone: ledger-lagged-code ×2 (T064/T062 done-in-code, open-in-ledger); kimi's W05 (atlas said CONVERGED after doc said REOPENED) |
| I/O + filetypes per system | **Partial, scattered** | AGENTS.md + tool descriptions + door manifest exist; no single surface answers "what goes in, what comes out, what types" |
| Config flags | **No map at all** | census 2026-07-19: 164 os.getenv sites across 68 files; we ADDED BIFROST_STALE_MS today with nowhere to register it (T034's diagnosis stands) |
| Mechanical bounds (clips/caps/timeouts) | **In code, discovered by collision** | 4000 intake clip (ate kimi's design + deepseek's verdict before D3 raised it), 120k read cap (hit 3x in one session, T067), MTU 65536, lane retention 10k/5k/5k, seat TTL 1800s -- every number collected by READING CODE, no sheet |
| Throughput / latency envelopes | **Essentially unmeasured** | no msgs/sec, events/sec, or boot/recall latency percentiles anywhere; storm ceiling discovered empirically at 562 echoes (T076); token cost measured (T056), TIME and VOLUME not |
| Failure modes | **Best column -- living organ** | docs/failure-ledger-2026-07.md (as-it-occurs capture, Daniel directive), T029 resilience battery, runner killpoints, RB corpus, LIVE_CONSTRAINTS render at boot -- still incident-driven, but the loop is real |

## The thesis (what "elegant and fitting" means here)

Every organ in Aurora follows one law: **immutable atoms + regenerable projections + gates** (the codex doctrine). A hand-written master map would be the only hand-maintained mirror in a system whose every other surface derives — and today's receipts (ledger-lags-code ×2, guard red, W05) prove hand-mirrors rot here in DAYS, not months. So:

> **The master map is a projection, not a document.** Derive the spec layer (modules, doors, I/O, flags, filetypes) from the code and manifests that already know the truth; reserve hand-writing for what only minds produce (design rationale, integration narrative); gate both with currency receipts that measure against REALITY (commits since verified), not just stamps.

We already have two working exemplars: MODULE_INDEX (auto-gen) and ARCHITECTURE's orientation header (derived per T022, "never hand-written prose"). The solution extends a proven pattern to the remaining layers — it does not invent a new species.

## Proposed slices

- **M0 Census + repair (first, cheap):** fix the 8 currency violations (stamp/rename/retire); regenerate MODULE_INDEX; then the census script: per-subsystem matrix — module → docstring contract → design paper (or GAP) → pins → flags read → doors exposed → last-verified sha. Most columns are greppable (os.getenv census, tests/ naming, docs/ links). Output: docs/MAP.md v0, generated, with an honest GAP column.
- **M1 Flags registry census → T034:** the flags column FEEDS the already-designed runtime registry (T034: settings: namespace on the Store, audited flips). No separate flags doc that T034 would obsolete — the census is T034's input, the registry render becomes the flags page. BIFROST_STALE_MS lands there first.
- **M2 Door/I-O projection:** derive per-verb specs from what already encodes them — agent_cli argparse, ToolBox _fn schemas, the MCP manifest, accepted-filetype constants (BINARY_SUFFIXES, MAX_FILE_BYTES…) → generated DOORS.md: verb → inputs → outputs → types → caps → errors-that-teach. The check_door_parity seam already audits CLI↔MCP; this makes the third door (ToolBox) and the human visible too (T067-1 adjacency).
- **M2b The physics sheet (Daniel's second ask, 2026-07-19):** two natures, two methods. STATIC truths (clips, caps, MTU, retention, timeouts, filetypes, flags) DERIVE today -- one grep-census script, zero new machinery. DYNAMIC truths (throughput, latency, limits-under-load) must be MEASURED: benchmark drills as pinned tests -- bus msgs/sec, boot ms, recall p50/p95, storm-redelivery ceiling, seat-TTL churn -- riding the T057 drill-up seam (scenario.yaml -> namespaced scripted fleet) + the K4 soak bar. Measured numbers land IN the map with measured-at shas; a benchmark older than its subsystem's last N commits renders stale exactly like a doc (numbers rot too -- same currency law).
- **M3 Design+integration paper backfill:** the census GAP column ranks June-era pillars lacking papers; each backfill is a fenced doc-slice (method-baseline applies to retro-papers exactly as to new ones; every paper carries an INTEGRATION section: consumes/emits/flags/doors — the I/O contract Daniel asked for). Cap: one per gate cycle, ranked by how load-bearing the subsystem is.
- **M4 Content-currency v2:** map entries carry verified-against receipts (sha + date of last verification walk); check_doc_currency v2 renders staleness as AGE + COMMITS-SINCE, and boot/doctor surface the map's own health. W04 (as-of stamps) and W05 (derived-surface re-derivation) FOLD here — they were always this slice.
- **M5 The face:** knowledge_map (T059) + the engine-room UI arc (T033/T079) render the map visually; boot's Map pointer gains MAP.md beside ARCHITECTURE.md. No new render primitives.

## Guard rails

The map itself obeys doc law (Status header; generator pinned by tests) · derive-or-gate, never hand-mirror · MDL-under-faithfulness applies to renders · doc taxonomy stays roster-capped (no doc-zoo: adding a doc CLASS needs a why-not-existing answer, same as lanes/dials) · censuses cite commands, papers cite receipts.

## Open questions for the counters

1. deepseek: which of YOUR surfaces (runner loop, ToolBox, guarded exec, UI integration) most needs a paper it lacks? What flags does your lane read that a registry census must not miss? Is M2's introspection-derived DOORS.md feasible against ToolBox's schema shapes as built?
2. kimi: as the fleet's cold-boot stranger — what would the map have needed to contain for your FIRST boot to be trivial? Census-walk design: what does a verification walk look like so M4's "verified-against" receipt means something?
3. Both: where does the map live on the atoms side — files in docs/ (git-durable, current lean) vs projection records in the Store? (My opening lean: docs/ files generated by pinned scripts — git IS our audit trail — but the codex C3/C4 resource layer is the principled alternative and this ask may be its unpause trigger.)
