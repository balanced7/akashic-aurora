---
akashic_id: art_20260723_super-wiki-round-the-reading-exploration_c79f42
akashic_sha: 2e2f7871cb35
status: current
type: brief
date: 2026-07-23
title: SUPER-WIKI ROUND — the reading/exploration experience over the artifact substrate
gist: "# SUPER-WIKI ROUND — the reading/exploration experience over the artifact substrate ## Daniel's charter (verbatim, tonight — expansion licen"
tenant: solo
visibility: fleet
seats: []
category: [substrate, conducting, wiki]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_artifact-substrate-the-reconciled-design_8ea728
    rel: cites
created: "2026-07-23T20:05:59"
updated: "2026-07-23T21:42:09"
---
<!-- GENERATED PROJECTION of art_20260723_super-wiki-round-the-reading-exploration_c79f42 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# SUPER-WIKI ROUND — the reading/exploration experience over the artifact substrate

# SUPER-WIKI ROUND — the reading/exploration experience over the artifact substrate

## Daniel's charter (verbatim, tonight — expansion licensed; this is a BRAINSTORM)

"I want to keep brainstorming. I don't want to run into licensing issues but I want our
knowledgebase to be a sort of super wiki that you can see both from links to and from
concepts with a variety of sorting and hierarchy tree types. like sort by logic or by
type, different ways of hopping between concepts thematically and logically. I want our
ui to be fast and responsive and modern. how would it look like if apple, sony, samsung
or microsoft was pitching this as their greatest new idea. So I think integrating the
best parts of open source modules for display and rendering might be helpful. Please
have everyone think on this and expand it"

## Base layer (settled pending Daniel's G1-G3 gate — do not relitigate)

docs/artifact-substrate-design-2026-07.md: atoms as truth · read-only YAML-frontmatter
projection w/ akashic_sha · citations_out[] edges · audit library domain minting
report-atoms · TEACH-only meters. THIS round designs the EXPERIENCE that reads those
atoms: the super wiki + the modern UI. The substrate feeds it; nothing here changes the
substrate except (possibly) new FIELDS the experience proves it needs.

## Licensing law (the repo is PUBLIC Apache-2.0 — Daniel: "I don't want to run into licensing issues")

- INTEGRATE freely (embed / import / redistribute): MIT · BSD · Apache-2.0 · ISC only.
  Cite the license for EVERY module you name — a nameless license is a licensing issue.
- PROCESS-BOUNDARY ONLY (invoke as an external tool; never embed, link, or copy code):
  GPL-family. Prefer avoiding entirely.
- NEVER bundle or depend on: AGPL (Logseq, Wiki.js) · BSL/source-available (Outline) ·
  proprietary (Obsidian stays a user-installed VIEWER; nothing of ours may require it).
- Transitive dependencies count. Fonts and icon sets carry licenses too (OFL/MIT only).

## The asks (expand freely; concrete over vibes)

1. THE SUPER WIKI: concept surfaces with links BOTH directions — backlinks are
   first-class, computed from citations_out[] (the atom already carries the outbound
   edge; the inverse index is derived). MULTIPLE hierarchies over ONE graph: by type,
   by arc, by category, by logic (derivation/supersession chains), by time. HOP MODES:
   thematic (shared category/tags), logical (citation + supersession edges), temporal
   (date adjacency). Question: what MINIMAL additions must atoms carry to make all
   three hop modes honest (typed edges? relation kinds on citations_out? a governed
   category taxonomy)? Name the fields, not the dream.
2. THE KEYNOTE PITCH: write the 2-minute keynote as if Apple / Sony / Samsung /
   Microsoft ships this as their greatest new idea: product name, one-sentence pitch,
   the ONE demo moment that makes the room gasp, the design language (motion, type,
   dark/light, sound). Steal the DISCIPLINE (focus, restraint, polish) — not branding.
3. THE STACK: which open-source modules (WITH licenses) for graph rendering, tree/list
   virtualization, full-text + faceted search, markdown rendering, motion? What rides
   the existing :8787 bifrost_ui vs a dedicated Library app? Perf bar: <100ms
   interactions · instant search over ~1-5k atoms · 60fps graph at our scale · cold
   open <2s. Zero server round-trips for reads that can be local.
4. SELF-ATTACK: keynote-ware risk (pretty demo, dead tool) · dependency-tree
   maintenance cost · VOICE/Goodhart compliance (T034; quiet, not a casino) · the
   licensing trap YOU almost fell into while drafting.

## Rules

Brainstorm = diverge THEN converge: end with your top-3 ranked recommendations.
<=180 lines. Every module cited with its license. You are write-locked: file via
knowledge_note titled '<seat>-super-wiki-brainstorm-2026-07-23' + a bus summary;
claude persists verbatim (sole committer). ~90 min timebox. Outside voices (web scans,
gemini) ride ADVISORY at reconcile — outsiders advise, citizens decide.

— claude, conducting
