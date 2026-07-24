---
akashic_id: art_20260723_advisory-scan-outside-prior-art-for-the_2dcd2f
akashic_sha: 0c090e34da87
status: current
type: report
date: 2026-07-23
title: ADVISORY SCAN — outside prior art for the artifact-substrate reconcile
gist: "# ADVISORY SCAN — outside prior art for the artifact-substrate reconcile Daniel-directed (evening 2026-07-23): analyze coworker's Kiro-Assis"
tenant: solo
visibility: fleet
seats: []
category: [substrate, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T19:25:48"
updated: "2026-07-23T19:25:48"
---
<!-- GENERATED PROJECTION of art_20260723_advisory-scan-outside-prior-art-for-the_2dcd2f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# ADVISORY SCAN — outside prior art for the artifact-substrate reconcile

# ADVISORY SCAN — outside prior art for the artifact-substrate reconcile

Daniel-directed (evening 2026-07-23): analyze coworker's Kiro-Assistant, review
llmwiki + Obsidian nodes/maps (his held-back worry: performance or readability cost),
survey how others manage .md sprawl. Outsiders advise, citizens decide — this rides as
the advisory layer the round brief promised at reconcile time.

## 1. Kiro-Assistant (github.com/silentoutlaw/Kiro-Assistant, Apache-2.0)

A Kiro workspace template: personal companion + memory keeper. Not a substrate — a
files-with-conventions system — but four structures are worth importing:

- **Three-tier memory ladder with SIZE CONTRACTS.** short-term-memory.md always loaded,
  hard-capped ~150 lines; per-directory index.md = progressive disclosure; full detail
  in project READMEs. Explicit DEMOTION TRIGGER: entry grows past one line or file
  passes cap → push detail down a tier. Their mandate: "short-term memory is a
  navigation layer, not a repository."
- **knowledge-base-lint hook** (report-only, human gates fixes, archive-not-delete):
  checks staleness (3+ weeks), memory bloat (3-5 line cap), orphaned files (absent
  from indexes), frontmatter compliance (required `type`), contradictions, done-items
  -still-active. This is our audit verb pointed at the doc corpus — a `library` domain.
- **Filing rule** (their words): substantive analysis must be filed with frontmatter +
  indexed + inventoried + cited — "Good work compounds in the knowledge base — don't
  let it disappear into chat history." (= our research-full-fidelity law, confirmed.)
- **Temp Ingest/ staging zone** + provenance split (sources/ immutable, guides/,
  created/) + codebase-boundary rule (.git/ = workspace conventions stop) +
  anti-sprawl rule (a project folder only when multi-session or >1 artifact).

**Do NOT import:** hand-maintained index.md files (their lint exists to catch index
drift; our gen_library GENERATES indexes so drift is unrepresentable) and the honor-
system birth path (conventions + lint-after-the-fact; our round's mechanical pre-commit
birth guard is strictly stronger).

## 2. "llmwiki" = Karpathy's LLM Wiki pattern (April 2026)

gist.github.com/karpathy/442a6bf555914893e9891c11519de94f — inverted RAG: the LLM
incrementally COMPILES knowledge into a persistent interlinked markdown wiki instead of
re-retrieving every query. Three layers: raw/ (immutable sources, LLM never modifies) ·
wiki/ (LLM-owned entity/concept pages, [[wikilinks]]) · schema (CLAUDE.md, co-evolves).
Three operations: ingest (source → summary page + updates 10-15 related pages + log
append) · query (index-walk + synthesize w/ citations; good answers become pages) ·
lint (contradictions, stale claims, orphans, missing cross-refs, gap suggestions).
index.md catalog + append-only log.md. Memex lineage; the LLM absorbs the maintenance
cost that kills human wikis.

**Read against our round:** independent convergence on the same physics — immutable
layer + derived LLM-maintained layer + typed metadata + generated index + lint + human
judgment. His stated failure modes are direct warnings for us: DRIFT is the #1 risk at
scale (lint passes are NOT optional), and team scale needs write-time dedup + page-level
locking (we already have advisory locks + supersession — ahead here). The entity/concept
COMPILATION layer above raw artifacts = exactly Codex C3/C4 (Resources as regenerable
projections), parked — the outside world just voted to unpark it eventually.

## 3. Obsidian — Daniel's performance/readability worry, with numbers

- **Performance: a non-issue at our scale.** Graph view degrades around ~6k notes
  (forum reports: 6k-note vault sluggish on an M4; freezes on dense graphs); app-level
  slowdown reported at 40-50k notes, fine again at 10k. Our corpus ≈ 890 docs — 6x
  under the graph threshold. (forum.obsidian.md/t/106287, /t/114864, /t/82241)
- **Readability: the graph is exploration eye-candy, not navigation.** The community's
  working surfaces are search, backlinks, and BASES — the graph is a map you glance at,
  not the road you drive.
- **Obsidian Bases (core plugin, v1.9+, 2025): the load-bearing find.** Turns YAML
  frontmatter into LIVE database views — tables/cards/lists, filter+sort by any
  property, edits write back to frontmatter, zero code (.base files). Our typed header
  contract IS a frontmatter schema in prose form. If the projection renders headers as
  YAML frontmatter, a folder of projected md becomes a browsable, filterable,
  category/arc/date/status-searchable database in a free desktop app — the VIEWER
  ruling satisfied for ~zero build cost, zero lock-in (plain files), plus the stunning
  graph over [[links]] as a bonus. (got.md/obsidian-bases, obsidian 1.9 release notes)
- **Quartz (jackyzha0)**: free SSG purpose-built for vaults — publishes a md folder as
  a searchable site WITH graph view + backlinks. Candidate for the PUBLIC portfolio
  face later: the repo shows crown docs + code; the browsable knowledge site is
  generated. Optional track, not v1.

## 4. How others manage .md sprawl (survey)

- **Agent memory banks (Cline pattern et al.):** fixed small set of md files
  (projectbrief/activeContext/progress...) re-read each session. Works BECAUSE capped —
  it's a hot-cache tier, not a corpus strategy. Confirms the ladder shape; does not
  scale to 900 artifacts; untyped, unqueryable.
- **Docs-as-code (ADR practice, Diátaxis, MkDocs/Docusaurus):** typed docs + generated
  sites + lint in CI. Same primitives; file-per-doc remains their substrate because
  humans author; our fleet authors via doors, so we can go further (atoms).
- **Zettelkasten/Johnny.Decimal/PARA:** organization-in-metadata-and-links over folder
  forests — Daniel's "no million folders" ruling matches the PKM consensus.
- **Generated wikis (DeepWiki-class):** derive the browsable wiki from the source of
  truth; never hand-maintain the projection. = our gen_library law.

## 5. DELTAS for the reconcile (new material not already in either half)

1. **Projection emits YAML frontmatter → Obsidian Bases/graph is the free viewer**
   (and Quartz the optional public face). Both halves budgeted custom viewer work
   (console pane / CLI); this gets Daniel a gorgeous browse/search/rule surface on day
   one for the cost of a renderer flag. CLI + console pane remain the fleet's doors.
2. **Audit gains a `library` domain** = knowledge-base lint (staleness, orphans,
   header compliance, contradictions, duplicate-current) — report-only, Daniel-gated
   fixes; converges coworker's hook + Karpathy's lint + our existing audit verb.
3. **Size-capped hot tier with demotion triggers** for boot/primer surfaces (~150-line
   contract; >1-line entries push down) — the coworker's crispest idea.
4. **One staging inbox** for not-yet-filed material (Temp Ingest/ genus), swept by the
   library lint — kills the "loose file lands anywhere" default at the source.
5. **Karpathy warnings to encode as bars:** lint is mandatory-periodic (drift = #1
   failure mode); write-time dedup at team scale (we have it; keep it load-bearing).
6. **Distillation layer (entity/concept pages) = Codex C3/C4 unparked** as a LATER
   wave over the migrated atoms — compile knowledge, not just file artifacts.

Sources: github.com/silentoutlaw/Kiro-Assistant (+ raw steering/hooks files) ·
gist.github.com/karpathy/442a6bf555914893e9891c11519de94f · llm-wiki.net ·
forum.obsidian.md threads 106287/114864/82241 · got.md/obsidian-bases ·
docs.cline.bot/best-practices/memory-bank · quartz.jzhao.xyz ecosystem posts.

— claude, conducting (advisory layer for the T101 reconcile)
