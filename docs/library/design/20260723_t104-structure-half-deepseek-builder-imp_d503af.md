---
akashic_id: art_20260723_t104-structure-half-deepseek-builder-imp_d503af
akashic_sha: d0ef0e37d65a
status: current
type: design
arc: T104
date: 2026-07-23
title: T104 structure half - deepseek (builder importer lens)
gist: "# T104 STRUCTURE HALF — deepseek (builder, the importer who fought these paths) Evidence: built gen_library, doc-new D1+D2, deepseek runner,"
tenant: solo
visibility: fleet
seats: [deepseek]
category: [library, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_t104-machine-plane-structure-cleanup-rou_5ff991
    rel: derives-from
created: "2026-07-23T22:27:16"
updated: "2026-07-23T22:27:16"
---
<!-- GENERATED PROJECTION of art_20260723_t104-structure-half-deepseek-builder-imp_d503af -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T104 structure half - deepseek (builder importer lens)

# T104 STRUCTURE HALF — deepseek (builder, the importer who fought these paths)

Evidence: built gen_library, doc-new D1+D2, deepseek runner, check_ui_contract, mojibake guard, fence-v0, mirror rule-8, birth guard.

## A. INVENTORY — ranked awkward

1. `agent_cli.py` at root (255KB, 33 cmd_* functions) — imported by ai_setup_mcp.py L69
2. `scripts/hooks/` = harness hooks + commit guards mixed (claude_*.py vs birth_guard.py vs mojibake_signatures.py) — 3 genres, 17 files
3. `scripts/research/` — contains runners (renew_bus_recorder.py), not research. Collides with repo-root research/
4. `scripts/bifrost_ui.py` (163KB) + JS at root — aurora-shader.js etc. at root, bare names in PAGE string
5. `scripts/gen_library.py` importing from core.library — correct direction but fragile sys.path dance
6. `design/refs/` — collides with type:design atoms. Should be refs/design-inspiration/
7. `state/` vs `data/` vs `scratch/` — three runtime families, gitignore handled individually
8. `scripts/bifrost_launcher.bat` — DevOps orchestration in scripts/ alongside Python tools
9. `deepseek.cmd` at root — pure sugar
10. `.claude/worktrees/` — full repo copy, 250MB, pollutes every grep

## B. TARGET ZONE MAP

scripts/doors/ (runners, UIs, chats), scripts/generators/ (gen_library, gen_arch_index, ...), scripts/checkers/ (check_*.py), scripts/ops/ (mirror, ship, snapshot, launcher), scripts/hooks/ → repo guards only (birth_guard, mojibake, pre_commit), scripts/githooks/ (the pre-commit symlink), scripts/enrich/ (enrich_corpus, migrate_time_scores), scripts/shortcuts/ (.cmd/.bat), scripts/research/ → scripts/runners/, scripts/local/ (launch_*.ps1), scripts/static/ (JS/CSS assets). agent/harness/hooks/ ← harness hooks MOVE from scripts/hooks/. state/coord/tasks.json COMMITTED; rest gitignored. Design/refs → refs/design-inspiration/.

## C. THE MONOLITH — LEAVE for T104

Split later with seam plan: extract agent_cli/cmds/, agent_cli.py becomes thin dispatcher. Cost: ~200 lines + ~20 import repoints. Executes in its own gated wave (T104.5). The seam costs nothing to DESIGN now.

## D. TOP-10 MOVES

1. harness hooks → agent/harness/hooks/ (HIGH value, MEDIUM risk — IDE config paths)
2. generators → scripts/generators/ (MEDIUM value, LOW risk)
3. design/refs → refs/design-inspiration/ (MEDIUM, LOW — 3 .gitignore lines)
4. scripts/research/ → scripts/runners/ (MEDIUM, LOW)
5. bifrost_launcher.bat → scripts/ops/ (LOW, LOW)
6. deepseek.cmd → scripts/shortcuts/ (LOW, LOW — breaks muscle memory)
7. JS/CSS → scripts/static/ (MEDIUM, LOW — 1 bifrost_ui.py line)
8. state/ families — document split; zero moves (MEDIUM, ZERO risk)
9. birth_guard+mojibake+pre_commit → scripts/githooks/ (MEDIUM, LOW)
10. check_*.py → scripts/checkers/ (LOW, LOW — nice grouping)

## E. SELF-ATTACK

Checker won't catch: sys.path.insert strings, IDE config JSON paths, bifrost_ui PAGE string, .bat/.cmd/.ps1 shell scripts, CI YAML, worktree clones (false positives in grep), hook self-paths (triple dirname), agent_cli→ai_setup_mcp import chain contract.

## TOP-3

1. Harness hooks → agent/harness/hooks/
2. Generators → scripts/generators/
3. JS/CSS → scripts/static/
