---
akashic_id: art_20260723_t104-machine-plane-structure-cleanup-rou_5ff991
akashic_sha: 0c3659bb9568
status: current
type: brief
arc: T104
date: 2026-07-23
title: T104 machine-plane structure cleanup round
gist: "Fleet round: inventory awkward placements, target zone map, monolith question, top-10 move-plan w/ blast radius; think then move; Daniel gates."
tenant: solo
visibility: fleet
seats: [claude]
category: [library, method, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T22:23:12"
updated: "2026-07-23T22:23:12"
---
<!-- GENERATED PROJECTION of art_20260723_t104-machine-plane-structure-cleanup-rou_5ff991 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T104 machine-plane structure cleanup round

Daniel's charter (verbatim, 2026-07-23 night — the gate posture is TRUST + RIGOR):
"I also want to clean up our file structure and file placements so that things make
sense where they are positioned. Some of the pieces we built are in awkward places due
to us just trying to get it to work. can you all think on it and organize the mechanics
and files and links as well? I recognize this is a big ask but I trust you to
methodically find a way to do it with excellence and rigor"

## Scope

The MACHINE plane (code/config/state) — the doc plane is solved (T101/T103, atoms live).
Zones under review: scripts/ (60+ mixed-purpose files: doors, runners, hooks, checkers,
generators, one-shots), repo ROOT (agent_cli.py 120k-token monolith, bootstrap.md,
loose entry files), state/ vs data/ vs scratch/ vs sessions/ (which family is which,
what is gitignored and why), scripts/hooks/ (harness hooks vs commit guards mixed),
tests/data + tests/fixtures, design/refs remnants, .claude/worktrees leakage.

## Rules of the round (rigor = the P3 lessons, now law)

1. THINK then MOVE, never both in one pass: this round produces a RECONCILED MOVE-PLAN;
   Daniel gates; execution is staged with the comprehensibility checker + full test
   suite green BETWEEN stages.
2. Every proposed move names its BLAST RADIUS: importers (grep count), path references
   in code/config/hooks/CI, and the reference-repoint set (the P3 map-driven rewrite is
   the proven pattern — 180 files re-pointed atomically).
3. Strangler discipline: compatibility shims where imports are wide (a moved module
   leaves a one-line re-export for one wave); no big-bang renames of load-bearing doors.
4. Name the PRINCIPLE for each placement (the LIBRARY one-facet law's machine-plane
   sibling): a file's home says WHAT KIND of thing it is, not which arc built it.
5. Windows-scale discipline: argv chunking, BOM-less list files, tracked/untracked
   splits (lesson a3_migration_scale_lessons).

## The asks

1. INVENTORY the awkward: your ranked list of misplaced pieces with evidence (why the
   current spot hurts: discovery cost, import tangles, guard blind spots).
2. TARGET SHAPE: propose the zone map for the machine plane (what lives in scripts/ vs
   core/ vs a new home; what the root deserves; hooks split guard-vs-harness; state
   families). Keep it SMALL — a zone map that fits one screen, like LIBRARY.md's table.
3. THE MONOLITH QUESTION: agent_cli.py — split now, split later with a seam plan, or
   leave (name the cost either way). No split executes this wave without its own gate.
4. MOVE-PLAN DRAFT: your top-10 moves ranked by value/risk, each with blast radius.
5. SELF-ATTACK: what breaks that the checker will NOT catch (runtime path builds,
   env-var paths, CI, the hooks' own paths, worktree clones)?

File as knowledge_note '<seat>-t104-structure-half-2026-07-23' + bus summary; <=150
lines; ~60-90 min. Reconcile (claude) -> Daniel gates the move-plan -> staged execution.
