Status: current
Type: design (reconciled — ends in constants) · Arc: library-schema / taxonomy + ergonomics · From: claude (reconciler) · Date: 2026-07-23 night
Inputs: claude/deepseek/kimi halves in research/drafts/*taxonomy-ergonomics-2026-07-23.md · Daniel's ruling verbatim in research/briefs/taxonomy-ergonomics-think-pass-2026-07-23.md · docs/LIBRARY.md v1 (extended, not replaced). Feeds: T101 A1 constants + the migration enrichment plan. Build fires on this doc.

# HOMES AND ORDER — reconciled to constants

## 1. THE CATEGORY ROSTER (24, fused from both seats' rosters; plane-clean per kimi's law)

A category names ABOUTNESS — never a type (`design` is a type), never an arc (`t101` is an arc).
Fused roster (kimi's plane organization × deepseek's corpus evidence; near-duplicates collapsed):

substrate · migration · library · recall · memory · bus · coordination · agent-lifecycle ·
identity · security · method · conducting · governance · audit · testing · tooling ·
ergonomics · ui · wiki · voice · optics · performance · frontier · narrative

Folds (recorded so census terms resolve): reasoning→memory · knowledge-stack→memory ·
resilience/ops-services→agent-lifecycle · backup/restore→substrate · secrets→security ·
mcp→tooling · search→wiki · fleet→bus/coordination · story→narrative · design(-methodology)→method ·
research→frontier · spend/bench→performance · visualgen→ui · wishlist/onboarding→ergonomics.
Governance: cap 24 · adding needs deepseek's propose-category door (a draft brief-atom + >=3
artifacts better-served + Daniel gate) · deletion ritual retires with re-categorization ·
audit library domain carries orphan-category + category-sprawl DRIFT rows · atoms carry 1-3
(PRIMARY first = where a cold browser expects it; 4+ wanted = split the artifact).

## 2. THE HOME RULE (the pass's one real divergence — ruled)

**home = f(type) for the PATH; category grouping is a VIEW.** kimi's audit argument wins over
deepseek's f(type, category[0]) path: category is a governed MUTABLE facet — a home derived
from it moves files on re-categorization and rots citations (the one-facet law's old enemy).
Projection path stays docs/library/<type>/<slug>-<hash6>.md — type+slug+id, nothing else.
deepseek's type→category shelf LAYOUT survives intact as the default RENDERING of the type
lens (presentation groups by category[0]; empty groups collapse; sparse-tree worry dissolves
because grouping is presentational, not physical). Re-categorization = a frontmatter change,
never a move. Order within any shelf view: status desc (current→draft→superseded→fossil),
then date desc — the living stuff always on top (all three halves).

## 3. DANIEL'S DEFAULT TREE (cold-open browse)

kimi's insight adopted: **arc-rooted, current-first** — Daniel thinks in campaigns ("the wiki
thing"), not kinds. The Library opens with L1 pinned (contracts + maps, one screen — claude
half), then LIVE ARCS as the top level, each arc's atoms current-first with superseded
collapsed under successors ("3 earlier versions"), fossils behind one fold. Type-shelf =
second door; category-lens = third; all derived live (never cached without freshness_ts —
kimi's audit guard). This is L1/L2/L3 rendered as a tree, with truth-status encoded at the
first surface he sees.

## 4. THE DOOR (one question, never worse than today — deepseek's spec, adopted whole)

`doc new --title "x"` infers: TYPE from ledger-task/template/context (fallback draft) · ARC
from the seat's claimed ledger task (the ledger IS the arc authority; no claim = no guess) ·
CATEGORY from the keyword classifier (~15 lines, ALL matches up to 3, confidence-ordered —
deepseek self-attack #1 folded) · REL suggestions from the session's recent reads (suggested,
never auto-applied). ONE confirmation prompt [Y/n/edit]; `n` → born as draft; --draft skips
everything (cheaper than touch). Wrong inference = post-hoc lint correction (wrap-census
posture), never a write-time block. Cost: ~40 lines door + ~15 classifier (deepseek).

## 5. CONVERSATION-ATOMS (Daniel: conversations become useful)

Provenance FIELDS land at A1, born-with (kimi; retrofit = the old pain): origin
(conversation|authored|ruling|migrated) · speakers[] · captured_at · source_thread · settled
(live|settled|ruled). **Authority derives from (type, origin, settled) — never prose
confidence**; a live discussion renders with its no-ruling-yet banner until a ruling
supersedes it. The capture door mints thread→atom with an attributed transcript body +
citations_out {target, rel: discusses} (weakest honest claim) + status draft; provenance
auto-fills from the bus envelope (cheap or it dies — kimi self-attack #4). The THREAD
RESOLVER reads the legacy stream as archive, fails LOUD past TTL (deepseek self-attack #3);
resolver ships v1.5 after P0-P1 — the fields ship NOW.

## 6. RETRO-ENRICHMENT (the migration enriches, not just moves)

enrich_corpus.py --dry-run: TYPE from headers (~80%, census seeds the rest) · ARC from
headers + arc_thread + title tokens (~85%) · CATEGORY from the classifier over
title+heading+first-500-chars (~75%; unclassified flagged, Daniel spot-checks 20) ·
CITATIONS_OUT backfilled from grep-able path references resolved through the migration table
(rel: discusses default) — RUN BEFORE P3 DELETION while paths are grep-able (claude half).
ACCEPTANCE BARS (kimi's three + deepseek's compound, all runnable at A3):
1. lib find --category recall --status current → zero fossils (census FOSSIL list = fixture).
2. rel:contradicts/supports edges from tonight's counters resolve to their targets in one hop.
3. lib find --origin conversation --settled live → exactly the open debates, each source_thread resolving.
4. superseded packet-routing designs in an arc, ranked by citations_in — two seconds, not a megaread.

## 7. A1 CONSTANTS (ship tonight; taxonomy bootstraps as code-loaded data, migrates to a governed atom at A3)

CATEGORY_ROSTER = the 24 above · REL_ROSTER = derives-from | contradicts | supports (+ settled
supersedes fields) · PROVENANCE fields per §5 · HOME_RULE = type-only path · AUTO_ARC = seat's
current ledger claim or None.

## 8. BUILD ORDER (fires now; deepseek runner is read-only tonight → claude writes, deepseek
fences live, kimi audits at slice gates)

A1 core/library atom family + door inference + gen_library frontmatter/--one + birth guard →
A2 audit library domain + report-atoms + LIVE_CONSTRAINTS bars → A3 enrich+migrate P0 reports
(sha/count/citation bars; vault handoff) → Library pane v1 (search+reading) → v1.5 capture
resolver + P1-P2 → v2 hops/meters → P3 deletion + v3 constellation.

## Attribution

Daniel's charter and gate. kimi: plane-clean roster law, home=f(type,status) audit ruling,
arc-rooted default tree, conversation-authority fields, acceptance-bar queries. deepseek:
evidence-cited roster, one-question door spec + classifier + costings, propose-category door,
enrichment pipeline numbers, legacy-stream archive + fail-loud. claude: extend-LIBRARY frame,
L1-pinned tree, rel-suggestions-from-reads, enrich-before-delete sequencing, roster fusion.

— claude, reconciling. The think passes are done; the build is the next commit.
