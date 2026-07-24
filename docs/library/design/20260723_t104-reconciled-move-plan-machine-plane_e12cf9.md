---
akashic_id: art_20260723_t104-reconciled-move-plan-machine-plane_e12cf9
akashic_sha: 2a941ab122d6
status: current
type: design
arc: T104
date: 2026-07-23
title: T104 reconciled move-plan (machine-plane structure)
gist: "Owner-facet law + one-walker visibility rule; M1 literal-path moves, M2 fire-verified, M3 documented families; monolith seam T104.5 w/ named trigger; gates G7-G9."
tenant: solo
visibility: fleet
seats: [claude, deepseek, kimi]
category: [library, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_t104-structure-half-deepseek-builder-imp_d503af
    rel: derives-from
  - target: art_20260723_t104-structure-half-kimi-audit-placement_88f729
    rel: derives-from
  - target: art_20260723_t104-machine-plane-structure-cleanup-rou_5ff991
    rel: supports
created: "2026-07-23T22:31:25"
updated: "2026-07-23T22:31:25"
---
<!-- GENERATED PROJECTION of art_20260723_t104-reconciled-move-plan-machine-plane_e12cf9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T104 reconciled move-plan (machine-plane structure)

T104 RECONCILED MOVE-PLAN — machine-plane structure cleanup (claude reconciling deepseek builder half + kimi audit half; Daniel gates G7-G9 before ANY move).

## 1. THE LAW (kimi, adopted whole)

A file's home names the LIFECYCLE-OWNER that must keep it true — the one question: "when this breaks, whose job is it to notice?" Corollaries: kind-not-arc (arc-named dirs are fossils wearing live addresses) · guards live where the guard-runner looks · generators live beside their output's owner · doors at the boundary, organs in core/. The law lands as a DECISION TABLE (LIBRARY.md machine-plane amendment at execution), not lore.

## 2. THE VISIBILITY RULE (kimi b.5, adopted)

Every top-level dir is claimed by exactly ONE walker/census, or it is invisible by construction. fences/ was the founding specimen; the CURRENT invisible set: infrastructure/, context/, agent/, mcp_servers/, mcp_global/. Execution: extend check_boundaries' PROTECTED roster (fold into the existing walker — never a sixth surface).

## 3. STAGED MOVES (each stage ends checker + full pytest + FIRE drills green)

M1 — literal-path class only (grep+rewrite verified, the proven P3 pattern; ~low risk):
  generators gen_*.py -> scripts/generators/ · check_*.py -> scripts/checkers/ · scripts/research/ runners -> scripts/runners/ · launcher/snapshot/ship -> scripts/ops/ · root sugar .cmd -> scripts/shortcuts/ · UI JS/CSS assets -> scripts/static/ (one PAGE-string repoint) · design/refs -> refs/design-inspiration/. EXCEPTIONS held back deliberately: mirror.py and agent_cli.py do not move (live doors; muscle memory + MEMORY.md references; shims considered at M2).
M2 — fire-verified classes (kimi's integrity law: env/config/hooks/CI/MCP verified by RUNNING, not reading):
  harness hooks -> agent/harness/hooks/ with registration repoint + deliberate hook-fire drill · commit guards (birth_guard, mojibake_signatures, pre_commit) -> scripts/githooks/ + mirror invocation repoint · ACL path_scope re-check against the new tree (a grant scoped to a moved path is a silent hole) · MCP manifest handshake · CI push = the CI-class verification.
M3 — zero-move documentation: the ten volatile root dirs (state/, data/, scratch/, session_logs/, sessions/, temp/, dropbox/, blackboard_data/, coordinator_logs/, session_screenshots/) get ONE documented family table (what it is, who writes it, gitignore rationale, snapshot coverage). The var/ physical consolidation is DEFERRED to a fleet-quiesced window (live runners hold open handles mid-session — the quiesce lesson governs).

## 4. THE MONOLITH (both halves converge: LEAVE now, seam plan with a NAMED trigger)

agent_cli.py stays this wave. T104.5 registered: extract the door-layer (cmd_* + argparse registration) from the organ-layer into agent_cli/cmds/, ~200 lines + ~20 repoints (deepseek shape), behind its own gate. Trigger named per kimi's Goodhart guard: split fires when agent_cli.py exceeds 4500 lines OR when the A-series (A1-A3 + Library pane v1) stabilizes — whichever first; "later" with no trigger is "never".

## 5. VERIFY-BY-FIRE MATRIX (per stage; kimi's law: literal paths by grep, everything else by fire)

pytest full suite · check_comprehensibility PASS · check_boundaries PASS · py agent_cli.py doctor (env-var path resolution live) · one deliberate hook-fire drill · MCP handshake · CI green on push · runtime-path census (grep join(ROOT|dirname(__file__) per moved dir) folded into each stage's blast-radius sheet.

## 6. GATE ASKS

G7: adopt the owner-facet law + decision table + one-walker visibility rule (LIBRARY machine-plane amendment).
G8: approve M1 (executable immediately on your word) and M2 (the fire-verified wave, same night or next).
G9: register T104.5 monolith seam plan with the named trigger; accept M3's defer of physical volatile-dir consolidation to a quiesced window.

Attribution: kimi — the law, the invisible-zone audit, the 7 link-integrity classes + verify-by-fire, the named-trigger discipline. deepseek — the ranked inventory, the zone map, the top-10 with grep-counted blast radius, the seam shape. Both halves are atoms with derives-from edges to the brief; this reconciliation cites both.
