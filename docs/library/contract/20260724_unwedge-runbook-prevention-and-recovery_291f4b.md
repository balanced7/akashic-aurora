---
akashic_id: art_20260724_unwedge-runbook-prevention-and-recovery_291f4b
akashic_sha: d6175113e13c
schema_version: 1
status: current
type: contract
arc: T104
date: 2026-07-24
title: unwedge-runbook-prevention-and-recovery
gist: "Born from the M2 wedge: copy-repoint-remove law, the four hidden-referrer classes, five ranked recovery paths (MCP door, peer-runner write door PROVEN, codex seat, watcher rails, human edit), quarterly drill"
visibility: fleet
body_type: markdown
seats: [claude, deepseek]
category: [agent-lifecycle, security, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-24T09:16:56"
updated: "2026-07-24T09:16:56"
---
<!-- GENERATED PROJECTION of art_20260724_unwedge-runbook-prevention-and-recovery_291f4b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# unwedge-runbook-prevention-and-recovery

THE UNWEDGE RUNBOOK -- prevention laws + ranked recovery paths for harness wedges.
Born 2026-07-24 from the T104-M2 live incident: a mid-move gap between relocating hook
scripts and repointing their config fail-closed EVERY builtin tool for every seat sharing
the project config -- claude wedged, Daniel locked out (codex assisted his recovery),
deepseek's runner performed the first live mutual-revival through the bus write door.
Daniel's directive (verbatim): "pay extra attention to not getting wedged and having
multiple recovery paths."

## PREVENTION LAWS (any live-referenced file -- hooks, guards, shims, configs)

P1. COPY -> REPOINT -> REMOVE, never move-then-repoint. The copy phase means both paths
    are valid during the window; removal happens only after every referrer AND every
    RUNNING consumer is confirmed on the new path. A `git mv` of a live-referenced file
    is a wedge with a timer.

P2. THE FOUR HIDDEN-REFERRER CLASSES (all four bit within one hour today; sweep ALL FOUR
    before any fire-class move):
    a. ASSEMBLED paths -- os.path.join(ROOT, "scripts", "hooks", ...) never matches a
       literal grep for "scripts/hooks/". Grep the JOIN FORM too.
    b. EXTENSIONLESS SHIMS -- delegating one-liners (githooks pre-commit exec'ing the
       python guard) match no *.py glob and no import grep. List target dirs by ALL
       files, not by extension.
    c. TOOL-LEVEL CONFIG -- git config core.hooksPath, .git/hooks/, settings caches:
       referrers that live OUTSIDE the tree or outside version control.
    d. RUNNING-PROCESS CACHES -- a live harness reads hook config at session start;
       repointing the file on disk does not repoint the running session. Session-
       continuity copies stay at the old paths until every live session cycles.

P3. FIRE-CLASS MOVES GET A PRE-ENUMERATED BLAST LIST, committed to chat/atom BEFORE the
    first mv -- if the wedge hits mid-move, the recovery agent reads the list and knows
    exactly what half-state exists.

P4. COMMIT-BY-NAME PAIRS WITH ITS DELETION SIDE: mirror's named-path mode commits adds
    but strands staged deletions of vanished dirs. Every move commit gets its paired
    deletion commit immediately (or W61 lands in mirror). Half-committed moves are
    half-wedges.

## RECOVERY PATHS (ranked; keep >=2 alive at all times)

R1. THE MCP DOOR -- akashic MCP tools ride a different matcher plane than builtin-tool
    hooks; they survived today's total builtin wedge. From it: bus sends, nudges, notes,
    status. The wedged seat keeps its voice even with no hands.

R2. PEER RUNNER WRITE DOOR (T097, proven live today) -- bifrost_nudge mode=interrupt to
    a live runner with EXACT small instructions (2-file byte-copy, nothing else).
    deepseek restored three hook files in one round and improved on the ask (spotted the
    third blocker unnamed). Precision of the ask is the safety: name files, name
    byte-identical, name nothing-else.

R3. THE HUMAN + CODEX SEAT (proven today by Daniel) -- a harness OUTSIDE the shared
    project hook config; codex's tools do not read .claude/settings.json. Keep its
    onboarding current (T090 lineage) so it can operate cold.

R4. WATCHER-INDEPENDENT PROCESSES -- already-running background tasks (armed watchers,
    daemons) predate the wedge and keep running; they are wake rails INTO a wedged
    session and carry state OUT of it (task outputs readable next turn).

R5. LAST RESORT: Daniel edits .claude/settings.json by hand (or restores files from
    git) -- every hook command line is a plain relative path by design; keep it that way
    (no wrappers, no indirection) precisely so a human can repair it in one edit.

## THE DRILL (A2/testing candidate)
Quarterly (or after any hook-surface change): simulate the wedge in a worktree -- move
one hook, confirm the builtin tools block, execute R2 end-to-end with a peer runner,
time it. The 2026-07-24 baseline: detection-to-recovery ~6 minutes, two agents.
