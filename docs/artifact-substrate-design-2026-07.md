Status: current
Type: design (reconciled) · Arc: library-schema / artifact-substrate (T101) · From: claude (reconciler) · Date: 2026-07-23 night · Gate: DANIEL (3 asks, end of doc)

# ARTIFACT SUBSTRATE — the reconciled design (T101: end the .md sprawl properly)

Daniel's charter + fork ruling + priority directive: verbatim in
research/briefs/md-sprawl-design-round-brief-2026-07-23.md (+ addenda 1-2).
Inputs fused here: deepseek half (6d59dee) · kimi half (f715b4c) · advisory scan
(research/drafts/advisory-scan-artifact-substrate-2026-07-23.md) · deepseek counters
(capture 1784850009040-0, filed) · kimi counters (ADR_0723193957_1927925e, filed).
Bars: verify-before-collapse · git history preserves every byte · security/ + .claude/
untouched · receipts per phase · Daniel gates migrations/deletions/ratification.

## 0. The one-paragraph design

Every knowledge artifact is born as a TYPED ATOM in the store (append-only,
supersession-aware). The File store's durable on-disk form for the docs family is
TYPED JSONL, git-tracked — one storage path, not two: kimi's atom schema over
deepseek's file physics. Markdown becomes a PROJECTION: docs/library/ regenerated
from atoms with YAML frontmatter, read-only by construction, self-verifying via an
embedded body-hash. Obsidian (Bases + graph) reads that folder as Daniel's day-one
browse/search viewer; the CLI and :8787 console remain the fleet's doors. Birth goes
through `doc new` (backend swap, muscle memory unchanged); a pre-commit guard REFUSES
naked .md creation; the audit verb gains a `library` domain whose every run is itself
filed as a report-atom — the substrate observes itself. The ~890 legacy files migrate
in Daniel-gated phases with checksum bars, ending in ONE visible deletion commit.

## 1. Substrate (Q1 — the fork, resolved)

- Truth = `artifact:<id>` atoms in the HybridStore (Redis = speed, File = durable).
- The File backend serializes the docs family as store/docs/<type>.jsonl (deepseek's
  layout) — JSONL is the atom's disk form, NOT a second system (deepseek self-attack
  #1 accepted: ONE storage path).
- Atom schema (kimi's header-as-fields, plus counter-round additions):
  id · header{status(current|superseded|fossil|draft), type, arc, seats, date, title,
  category[], tenant, visibility} · body (full-fidelity markdown, verbatim law rides
  inside) · supersedes/superseded · body_sha · citations_out[] · created/updated.
  - `tenant`/`visibility` born NOW, defaulted solo — retrofitting tenancy onto
    migrated atoms repeats the 890-file header retrofit (kimi corporate finding).
  - `status: draft` = the staging state (deepseek's merge of the scan's staging
    inbox): the loose-file instinct gets a LEGAL state, swept by the library lint —
    one path, two states, no second physical zone. Closes kimi Q8.2.
- ID format (reconciler's call): `art_<date>_<slug>_<hash6>` (kimi) — readable,
  sortable, slug survives for humans; deepseek's doc:-prefix resolver semantics kept.
- Durability: atomic replace on File writes; git = off-machine history; snapshot_
  knowledge.py = point-in-time restore. Corporate-grade networked durability is a
  NAMED later-wave (kimi INFER accepted), not silently assumed.

## 2. Projection (the render, never the truth)

- docs/library/<type>/<slug>-<hash6>.md, regenerated from atoms. YAML frontmatter
  carries the header fields + `akashic_id` + `akashic_sha` (hash of atom body).
- READ-ONLY BY CONSTRUCTION (kimi's Bases write-back hazard, accepted as a gate):
  regen overwrites hand edits; the audit library domain photographs
  projection-frontmatter/sha vs atom-header/body as a standing row — a hand edit or
  drift becomes a DRIFT row, mechanically (deepseek's akashic_sha = the kill-shot
  for dual-truth).
- Incremental render: `gen_library --one <id>` at every birth (~30 lines; walk one,
  render one) — the door stays as cheap as Write-a-file, killing kimi Q8.5.
  `--stale` sweep at mirror time catches map staleness (deepseek self-attack #4).
- Generated maps (SHELVES/ARCS/INDEX/zone READMEs) now draw from atoms; still
  never hand-maintained (indexes are belief surfaces — generated or they're lies).
- BONUS (deepseek beyond): every atom change = exactly one projected file changed —
  git diff of the projection is the human-readable review surface; both halves'
  diff-opacity attacks dissolve.

## 3. Viewer (Daniel's surface — his ruling: browse and explore)

- DAY ONE: the projection folder opens as an Obsidian vault — Bases table/card views
  over the frontmatter (filter by category/arc/date/status/type), graph over links,
  full-text search. Zero build, zero lock-in, ~890 docs is 6x under the graph-perf
  threshold. POSTURE: viewing surface only — write-back stays off; rulings and edits
  go through the doc verbs (see gate ask G2).
- The CLI (`doc`/`lib find`/resolver) and the :8787 console remain the fleet's doors.
- v2 (post-P1): console Library pane with the health visuals (§5).
- Later-wave: Quartz static site as the public portfolio face.

## 4. Birth + guard (Q3 — kill the spawn-rate mechanically)

- `doc new` keeps its surface; backend becomes: mint atom → `gen_library --one` →
  mirror. ONE verb invocation end-to-end (deepseek self-attack #2 accepted).
- Long bodies ride --body-file (W63 law); bus-side captures ride the capture verb.
- GUARD: pre-commit REFUSES any new .md under docs/, research/, chronicles/ not in
  the projection manifest or crown allowlist (~30 files) — naked creation becomes
  unrepresentable at the commit boundary (both halves converged; kimi's manifest
  formulation). Wrap census remains the straggler net for uncommitted strays.

## 5. Meters + gamified visuals (Daniel's new axis, Goodhart-guarded)

TEACH-only roster (kimi's health-vs-activity split; T034 Goodhart-1 governs; VOICE
governs — quiet, not a casino). NO streaks, NO per-agent leaderboards, NO artifact
counts ("a you-filed-15-docs badge is the disease wearing a medal" — kimi).
- Drift-down heatmap: audit DRIFT rows over time, cooling as arcs close.
- Coverage-up gauge: fraction of atoms with complete headers / resolvable citations /
  valid supersession chains. Spawning junk LOWERS it — unfarmable.
- Arcs-alive constellation: live arcs glow, stalled arcs dim — the Aurora rendered
  over real data; atoms as stars, citations as edges, supersession as fading.
- Projection-freshness: lag newest-atom → its render (the honesty meter).
Build order (deepseek costing + self-attack #3): health bar (~20 lines) + drift meter
(~15 lines) AFTER P0-P1 migration; the constellation is the v2 showpiece. Obsidian's
interactive graph is the day-one free toy. Every meter reads from atoms/audit-atoms —
no metrics sidecar that can itself drift (kimi beyond).

## 6. Keeping it honest (Q8s + Karpathy warning, encoded)

- Audit `library` domain (~70 lines + store query): unstamped/untyped/unreadable
  (gen_library already detects 3), orphans-not-in-maps, header compliance,
  contradictions, duplicate-current — duplicate-current via STORE QUERY on the
  supersession chain, not file scan (deepseek correction). Staleness keys off
  status/superseded fields, NEVER wall-clock age — fossils are receipts, not rot
  (kimi correction of the Kiro 3-week import).
- Founding run follows the audit founding-match law: run live first, an honest MATCH
  stands as the receipt; injected fixtures prove the rules fire.
- EVERY audit/lint run mints a report-atom (kimi beyond): drift history is queryable
  from the substrate itself — self-observing, no sixth surface.
- Bars encoded (4 lines to LIVE_CONSTRAINTS, deepseek "encode don't build"):
  lint is mandatory-periodic (drift = #1 failure mode) · write-time dedup + advisory
  locks stay load-bearing at team scale · the projection is read-only · the atom is
  the only truth.

## 7. Corporate profile (Daniel's new axis — scale without shape change)

The SHAPE is scale-invariant: door → atom → projection → viewer. Only adapters swap.
Writer-scale ladder (deepseek's honest numbers + kimi's audit holes):
- 0-5 writers (NOW): File-JSONL + git, direct. Correct as-is.
- 5-20: post-merge `--repair` pass reconciles duplicate-current (deepseek).
- 20-50: git push contention on shared JSONL → births accumulate in the store;
  mirror commits the projection PERIODICALLY (store-primary posture begins).
- 50+ (corporate): networked/replicated store is the primary; git holds crown docs +
  projection snapshots. NAMED LATER-WAVE with its own design round.
- S-1b (later-wave design item, kimi): atom tenancy + visibility enforcement at read
  + supersede-rights as an explicit grant (may a member supersede an admin's atom?).
  S-1 quarantine/grants stretch for solo/small-team; the supersede verb gap is real.
- Already corporate-grade: append-only + supersession-not-deletion = a compliance
  auditor's trail by construction (both halves; the strongest inherited property).

## 8. Citations + migration (Q5/Q6 — value-loss zero, gated)

- Legacy map: every existing path → art_id, committed as an atom AND generated
  docs/library/LEGACY.md; resolver accepts old paths transparently; the map never
  deletes. citations_out[] makes the reference web explicit.
- P0 (gate: type choice — recommend `report`, ~88 research/reviewed files): build
  A1+A2 slices, migrate, VERIFY: per-file sha byte-preservation, count match,
  citation-liveness (every old path resolves), spot-check IDs. Zero value loss is
  the acceptance bar, not a hope.
- P1: hot types (brief/design/chronicle). Same bars.
- P2: long tail + refs/ — kimi's 184-file census verdicts ride in as birth statuses
  (FOSSIL/SUPERSEDED born true).
- P3: ONE gated deletion commit (Daniel's, visible, reversible via git).
- Homecoming bar carries over: repo face clean + the vault browsable.

## 9. Build slices (register on approval; each cites this doc)

- A1 substrate+door: atom schema/family, doc-new backend, --one render, frontmatter
  flag, birth guard, --draft state. (deepseek build partner; ~150 lines total.)
- A2 honesty: audit library domain + report-atom minting + LIVE_CONSTRAINTS bars +
  founding run.
- A3 P0 migration (reports) + legacy map + Obsidian vault handoff to Daniel.
- A4 P1-P2 waves + health bar + drift meter on the console.
- A5 P3 deletion + JOURNEY entry + Aurora constellation (v2 showpiece).
Later-wave register: boot size-caps w/ demotion (Δ3, post-substrate) · distillation
layer / Codex C3-C4 (unpark trigger: atoms >5k OR doc-recall precision measurably
drops) · Quartz public site · S-1b tenancy · networked-store corporate durability.

## 10. DANIEL'S GATE — three asks

- G1: Approve the fused design + P0 type = reports. (Execution license from the
  morning directive stands; the reconciler held execution for this gate.)
- G2: Approve the read-only-projection posture: the Obsidian vault is browse/search
  only — table edits do NOT write back (they'd be overwritten by regen; the audit
  net catches strays). Your RULE surface stays doc verbs/console/telling the fleet.
  This is the one honest UX tradeoff vs the scan's rosier framing.
- G3: Approve id format (`art_<date>_<slug>_<hash6>`) + `--draft` staging semantics.

## Attribution (proportionality law)

Daniel's charter and rulings open and gate the arc. Halves: deepseek (JSONL physics,
render costing, corporate ladder, projection-as-diff), kimi (atom schema, projection
law, Bases write-back hazard, Goodhart meter split, tenancy holes, self-observing
substrate). Advisory outsiders (coworker's Kiro-Assistant, Karpathy LLM Wiki,
Obsidian/PKM community) recorded in the advisory scan — absorbed, not headlined.

— claude, reconciling (T101). NOTHING below A1 builds before Daniel's G1-G3.
