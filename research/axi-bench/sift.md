# AXI bench: `sift`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 29/30 (97%) | 30/30 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 683 | 771 | +88 (+13%) |
| Stdout characters (all runs) | 1,707 | 1,913 | +206 (+12%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many occurrences of 'wakeable' are in its evidence pack? | `22` | 5/5 | 5/5 |
| In how many files does 'wakeable' occur? | `9` | 5/5 | 5/5 |
| How many occurrences of 'cursor_lease' were found? | `0` | 5/5 | 5/5 |
| Was any money spent on model calls by this command? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which hats does sift accept? List them separated by commas. | `['adversary', 'historian', 'jester', 'junction', 'linguist', 'outsider']` | 5/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 4/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora sift wakeable cursor_lease --dry-run` (exit 0)

```
# sift: 2 term(s) x 6 hat(s), planes=['source'], evidence=breadth
  wakeable     occ=22   files=9    sha=4d8be47ee0ff
  cursor_lease occ=0    files=0    sha=3cb19df41d2b

# DRY RUN -- nothing spent. Read one pack before trusting any finding:

--- wakeable (first 5 of 22) ---
  [source] agent/bifrost_pull.py:814: - a seat held by a LIVE twin means the TWIN is the wakeable seat-holder -- listening here
  [source] agent/bifrost_pull.py:829: f"standby: NOT listening (live twin is the wakeable seat-holder; "
  [source] agent/harness/hooks/claude_stop.py:1: """Stop hook: keep THIS Claude session wakeable from idle + audit the turn's ending.
  [source] agent/harness/hooks/claude_stop.py:6: agent, BLOCK the stop and tell the model to re-arm -- turning "always wakeable" from fragile
  [source] agent/harness/hooks/claude_stop.py:433: # T086-S3b: a LIVE TWIN session holds the consumer seat -- the twin is the wakeable
  BLIND: PLANE: this pack contains ['source'] only. A term can be coherent in source and forked in docs, or the reverse, and this pack cannot see the differenc
  BLIND: EXCLUDED BY PLANE, not absent: doc=46, out-of-corpus=3, test=22. Vendored trees (ComfyUI-Zluda et al) are a different project's vocabulary; history/re

--- cursor_lease (first 5 of 0) ---
  BLIND: PLANE: this pack contains ['source'] only. A term can be coherent in source and forked in docs, or the reverse, and this pack cannot see the differenc
  BLIND: occurrences are LINE-level: a fork visible only across a function boundary or in code shape rather than in a line containing the token is invisible he
```

`aurora sift wakeable --hats nosuchhat --dry-run` (exit 2)

```
unknown hat(s) ['nosuchhat']; known: ['adversary', 'historian', 'jester', 'junction', 'linguist', 'outsider']
```


## After: output

`aurora sift wakeable cursor_lease --dry-run` (exit 0)

```
dry_run: true
spent_usd: 0
terms: 2
hats[6]: outsider,junction,linguist,historian,adversary,jester
planes[1]: source
evidence: breadth
packs[2]{term,occurrences,files,sha,capped}:
  wakeable,22,9,82fd8cc94b8a,false
  cursor_lease,0,0,3cb19df41d2b,false
samples[5]{term,where,text}:
  wakeable,"agent/bifrost_pull.py:814","- a seat held by a LIVE twin means the TWIN is the wakeable seat-holder -- listening here"
  wakeable,"agent/bifrost_pull.py:829","f\"standby: NOT listening (live twin is the wakeable seat-holder; \""
  wakeable,"agent/harness/hooks/claude_stop.py:1","\"\"\"Stop hook: keep THIS Claude session wakeable from idle + audit the turn's ending."
  wakeable,"agent/harness/hooks/claude_stop.py:6","agent, BLOCK the stop and tell the model to re-arm -- turning \"always wakeable\" from fragile"
  wakeable,"agent/harness/hooks/claude_stop.py:433","# T086-S3b: a LIVE TWIN session holds the consumer seat -- the twin is the wakeable"
blind[3]{terms,blind}:
  wakeable cursor_lease,"PLANE: this pack contains ['source'] only. A term can be coherent in source and forked in docs, or the reverse, and this pack cannot see the difference"
  wakeable,"EXCLUDED BY PLANE, not absent: doc=46, out-of-corpus=3, test=32. Vendored trees (ComfyUI-Zluda et al) are a different project's vocabulary; history/research record the past. Counted here so the exclusion is a stated decision rather than a silent one"
  cursor_lease,"occurrences are LINE-level: a fork visible only across a function boundary or in code shape rather than in a line containing the token is invisible here"
real_run: "12 tier-1 branches (2 terms x 6 hats) to a paid model, then curator pairs"
help[1]:
  uv run agent_cli.py sift wakeable cursor_lease --out sift.json
```

`aurora sift wakeable --hats nosuchhat --dry-run` (exit 2)

```
error: "unknown hat(s): nosuchhat"
code: USAGE
known_hats[6]: adversary,historian,jester,junction,linguist,outsider
help[1]:
  uv run agent_cli.py sift wakeable --dry-run
```
