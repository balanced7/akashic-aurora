# AXI bench: `manual`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 19/25 (76%) | 25/25 (100%) | +24 pp |
| Output tokens, as the reader counts them (median) | 65 | 120 | +55 (+85%) |
| Stdout characters (all runs) | 3,367 | 3,353 | -14 (-0%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many passages are on the shelf in total? | `20` | 4/5 | 5/5 |
| What is the name of the shelf? | `runbooks` | 0/5 | 5/5 |
| Which document did the top passage come from? Give its title. | `unwedge` | 5/5 | 5/5 |
| Was the answer cut short by the size or count cap? Answer yes or no. | `yes` | 5/5 | 5/5 |
| How many passages matched the question? | `0` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora manual list` (exit 0)

```
manual list: 3 documents, 20 passages (/tmp/axi-bench-m8ed3r4j/data/state/manuals/manuals.db)
  runbooks                     3 docs      20 passages
```

`aurora manual search how do I recover a wedged seat --mode bm25 --limit 2` (exit 0)

```
manual search: 2 passage(s) for 'how do I recover a wedged seat' (from 20 chunks in [runbooks])

[1] unwedge-runbook-prevention-and-recovery  (runbooks)
    file:///mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a1b90f0ed3d468da7/docs/library/contract/20260724_unwedge-runbook-prevention-and-recovery_291f4b.md
    THE UNWEDGE RUNBOOK -- prevention laws + ranked recovery paths for harness wedges.
    Born 2026-07-24 from the T104-M2 live incident: a mid-move gap between relocating hook
    scripts and repointing their config fail-closed EVERY builtin tool for every seat sharing
    the project config -- claude wedged, Daniel locked out (codex assisted his recovery),
    deepseek's runner performed the first live mutual-revival through the bus write door.
    Daniel's directive (verbatim): "pay extra attention to not getting wedged and having
    multiple recovery paths."

[2] unwedge-runbook-prevention-and-recovery › RECOVERY PATHS (ranked; keep >=2 alive at all times)  (runbooks)
    file:///mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a1b90f0ed3d468da7/docs/library/contract/20260724_unwedge-runbook-prevention-and-recovery_291f4b.md#recovery-paths-ranked-keep-2-alive-at-all-times
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
    
    THE DRILL (A2/testing candidate)
    Quarterly (or after any hook-surface change): simulate the wedge in a worktree -- move
    one hook, confirm the builtin tools block, execute R2 end-to-end with a peer runner,
    time it. The 2026-07-24 baseline: detection-to-recovery ~6 minutes, two agents.

(answer capped by size; raise --max-chars or --limit for more)
```

`aurora manual search zebra unicorn --mode bm25` (exit 0)

```
manual search: 0 of 20 chunks in [runbooks] matched ['zebra', 'unicorn'] -- the shelf may use other words for this; try synonyms, or `manual list` to see what is shelved
```


## After: output

`aurora manual list` (exit 0)

```
shelves: 1
documents: 3
passages: 20
embedded: 0
db: /tmp/axi-bench-m8ed3r4j/data/state/manuals/manuals.db
by_shelf[1]{shelf,documents,passages}:
  runbooks,3,20
help[1]:
  uv run agent_cli.py manual search <question> --shelf runbooks
```

`aurora manual search how do I recover a wedged seat --mode bm25 --limit 2` (exit 0)

```
query: how do I recover a wedged seat
mode: bm25
searched_passages: 20
shelves[1]: runbooks
total: 2
capped: true
passages[2]{shelf,document,section,source,text}:
  runbooks,unwedge-runbook-prevention-and-recovery,null,"file:///mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a1b90f0ed3d468da7/docs/library/contract/20260724_unwedge-runbook-prevention-and-recovery_291f4b.md","THE UNWEDGE RUNBOOK -- prevention laws + ranked recovery paths for harness wedges. Born 2026-07-24 from the T104-M2 live incident: a mid-move gap between relocating hook scripts and repointing their config fail-closed EVERY builtin tool for every seat sharing the project config -- claude wedged, Daniel locked out (codex assisted his recovery), deepseek's runner performed the first live mutual-revival through the bus write door. Daniel's directive (verbatim): \"pay extra attention to not getting wedged and having multiple recovery paths.\""
  runbooks,unwedge-runbook-prevention-and-recovery,RECOVERY PATHS (ranked; keep >=2 alive at all times),"file:///mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a1b90f0ed3d468da7/docs/library/contract/20260724_unwedge-runbook-prevention-and-recovery_291f4b.md#recovery-paths-ranked-keep-2-alive-at-all-times","R1. THE MCP DOOR -- akashic MCP tools ride a different matcher plane than builtin-tool hooks; they survived today's total builtin wedge. From it: bus sends, nudges, notes, status. The wedged seat keeps its voice even with no hands. R2. PEER RUNNER WRITE DOOR (T097, proven live today) -- bifrost_nudge mode=interrupt to a live runner with EXACT small instructions (2-file byte-copy, nothing else). deepseek restored three hook files in one round and improved on the ask (spotted the third blocker unnamed). Precision of the ask is the safety: name files, name byte-identical, name nothing-else. R3. THE HUMAN + CODEX SEAT (proven today by Daniel) -- a harness OUTSIDE the shared project hook config; codex's tools do not read .claude/settings.json. Keep its onboarding current (T090 lineage) so it can operate cold. R4. WATCHER-INDEPENDENT PROCESSES -- already-running background tasks (armed watchers, daemons) predate the wedge and keep running; they are wake rails INTO a wedged session and carry state OUT of it (task outputs readable next turn). R5. LAST RESORT: Daniel edits .claude/settings.json by hand (or restores files from git) -- every hook command line is a plain relative path by design; keep it that way (no wrappers, no indirection) precisely so a human can repair it in one edit. THE DRILL (A2/testing candidate) Quarterly (or after any hook-surface change): simulate the wedge in a worktree -- move one hook, confirm the builtin tools block, execute R2 end-to-end with a peer runne... (truncated, 1582 chars total)"
help[1]:
  uv run agent_cli.py manual search how do I recover a wedged seat --max-chars 12000
```

`aurora manual search zebra unicorn --mode bm25` (exit 0)

```
query: zebra unicorn
mode: bm25
searched_passages: 20
shelves[1]: runbooks
total: 0
terms[2]: zebra,unicorn
passages: []
help[2]:
  uv run agent_cli.py manual search <other words>
  uv run agent_cli.py manual list
```
