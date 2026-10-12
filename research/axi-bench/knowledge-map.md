# AXI bench: `knowledge-map`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 445 | 443 | -2 (-0%) |
| Stdout characters (all runs) | 1,210 | 1,271 | +61 (+5%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many nodes are in the surface layer? | `3` | 5/5 | 5/5 |
| How many nodes are in the archive layer? | `1` | 5/5 | 5/5 |
| Which archived record is on this topic? Give its title only. | `Old cache design` | 5/5 | 5/5 |
| What exact command shows the full record of the quokka_backup lesson? Give the command only. | `['recall', '--full', 'learn:experiment:quokka_backup']` | 5/5 | 5/5 |
| How many nodes did the walk find in total? | `0` | 5/5 | 5/5 |

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

`aurora knowledge-map quokkadb` (exit 0)

```
# KNOWLEDGE MAP: quokkadb   (3 surface | 0 neighborhood | 1 archive)

## L1 surface -- direct topic hits
  [lesson:current] quokka_backup (rel 1.0)
      quokka_backup Use the quokkadb online backup command, never a file copy corrupt backup copied the quokkadb file while open data
      drill: recall --full learn:experiment:quokka_backup
  [lesson:current] quokka_wal_mode (rel 1.0)
      quokka_wal_mode Use when quokkadb locks under load: enable WAL mode writers blocked readers ran quokkadb without WAL performance
      drill: recall --full learn:experiment:quokka_wal_mode
  [note:current] Chose quokkadb for the embedded store (rel 1.0)
      Chose quokkadb for the embedded store We picked quokkadb over leveldb because it ships with python and survives crashes
      drill: notes --all (id ADR_1012174720_1fcb9958)

## L3 archive -- on topic but retired/superseded (reachable, not live)
  [note:retired] Old cache design (rel 1.0)
      ...ld cache design The quokkadb cache layer was dropped in favour of redis
      drill: notes --all (id ADR_1012174721_2b17ee4e)
```

`aurora knowledge-map zebraunicorn` (exit 0)

```
# KNOWLEDGE MAP: zebraunicorn   (0 surface | 0 neighborhood | 0 archive)
  (nothing above the relevance floor -- try different terms)
```


## After: output

`aurora knowledge-map quokkadb` (exit 0)

```
topic: quokkadb
counts:
  surface: 3
  neighborhood: 0
  archive: 1
surface[3]{kind,status,title,score,excerpt,drill}:
  lesson,current,quokka_backup,1,"quokka_backup Use the quokkadb online backup command, never a file copy corrupt backup copied the quokkadb file while open data","recall --full learn:experiment:quokka_backup"
  lesson,current,quokka_wal_mode,1,"quokka_wal_mode Use when quokkadb locks under load: enable WAL mode writers blocked readers ran quokkadb without WAL performance","recall --full learn:experiment:quokka_wal_mode"
  note,current,Chose quokkadb for the embedded store,1,Chose quokkadb for the embedded store We picked quokkadb over leveldb because it ships with python and survives crashes,notes --all (id ADR_1012174758_9c0830d8)
neighborhood: []
archive[1]{kind,status,title,score,excerpt,drill}:
  note,retired,Old cache design,1,...ld cache design The quokkadb cache layer was dropped in favour of redis,notes --all (id ADR_1012174758_271c6678)
help[1]:
  uv run agent_cli.py recall --full learn:experiment:quokka_backup
```

`aurora knowledge-map zebraunicorn` (exit 0)

```
topic: zebraunicorn
counts:
  surface: 0
  neighborhood: 0
  archive: 0
note: nothing above the relevance floor
help[2]:
  uv run agent_cli.py lookback "zebraunicorn"
  uv run agent_cli.py knowledge-map <other words>
```
