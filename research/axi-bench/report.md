# AXI bench: `report`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 61 | 84 | +23 (+38%) |
| Stdout characters (all runs) | 1,639 | 1,860 | +221 (+13%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which file path did the command write to? Give the path only. | `/tmp/axi-bench-report-i486mwbd/retro.html` | 5/5 | 5/5 |
| How many characters did the command write to the file? | `13384` | 5/5 | 5/5 |
| How many report-kit primitives are listed? | `11` | 5/5 | 5/5 |
| Which primitive should be used for 3-6 headline numbers? Give the primitive exactly as listed. | `.tiles > .tile > .v + .k` | 5/5 | 5/5 |
| Which flag is required but missing? Give the flag only. | `--title` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora report --title Q3 retro --out /tmp/axi-bench-report-i486mwbd/retro.html` (exit 0)

```
[report] wrote /tmp/axi-bench-report-i486mwbd/retro.html (13384 chars, kit inlined)
         compose it against the crib, then publish with the Artifact tool.
```

`aurora report --crib` (exit 0)

```
report-kit primitives:

  header / .eyebrow / h1 / .standfirst
      Opening. The standfirst is a serif thesis sentence, not a summary.
  hr.rule
      Section break carrying the project's own colours. Use 2-4 times, never between every section.
  .tiles > .tile > .v + .k
      3-6 headline NUMBERS. Never prose. Digits are tabular by default.
  .card[.go|.hold|.stop] > .head + .paths > .path > .plabel[.a|.b] + .ptext, then .rec
      A DECISION WITH REAL COSTS ON BOTH SIDES. .plabel.a names the path you lean toward, .plabel.b the one you do not; .rec carries the recommendation. If one path is obviously wrong it is rhetoric wearing a choice's clothes -- use .rows instead.
  .timeline > .tl > .when + .what
      ONLY when order carries information the reader needs. Not decoration for a list.
  .versus > .side  (+ .synth)
      A GENUINE DISAGREEMENT, both sides stated fairly. NOT a pro/con list. Pair with .synth when a reconciliation exists.
  blockquote > mark + .who
      Someone's words verbatim. mark highlights the phrase that actually matters.
  .rows > .row > .rt + .rd
      A flat list where each item has a label and a consequence.
  .scroll > table  (td.n, .v.ok/.no/.cl/.mo)
      Comparison. Wide content scrolls ITSELF so the page never scrolls sideways.
  --go / --hold / --stop
      SEMANTIC colour: cheap / needs judgement / costs either way. Never decoration.
  --aurora
      The accent. Structure and emphasis only -- it must never carry status.
```

`aurora report` (exit 2)

```

```


## After: output

`aurora report --title Q3 retro --out /tmp/axi-bench-report-i486mwbd/retro.html` (exit 0)

```
wrote: /tmp/axi-bench-report-i486mwbd/retro.html
chars: 13384
kit: inlined
next: "compose it against the crib, then publish with the Artifact tool"
help[1]:
  uv run agent_cli.py report --crib
```

`aurora report --crib` (exit 0)

```
total: 11
primitives[11]{primitive,use}:
  header / .eyebrow / h1 / .standfirst,"Opening. The standfirst is a serif thesis sentence, not a summary."
  hr.rule,"Section break carrying the project's own colours. Use 2-4 times, never between every section."
  .tiles > .tile > .v + .k,3-6 headline NUMBERS. Never prose. Digits are tabular by default.
  ".card[.go|.hold|.stop] > .head + .paths > .path > .plabel[.a|.b] + .ptext, then .rec","A DECISION WITH REAL COSTS ON BOTH SIDES. .plabel.a names the path you lean toward, .plabel.b the one you do not; .rec carries the recommendation. If one path is obviously wrong it is rhetoric wearing a choice's clothes -- use .rows instead."
  .timeline > .tl > .when + .what,ONLY when order carries information the reader needs. Not decoration for a list.
  .versus > .side  (+ .synth),"A GENUINE DISAGREEMENT, both sides stated fairly. NOT a pro/con list. Pair with .synth when a reconciliation exists."
  blockquote > mark + .who,Someone's words verbatim. mark highlights the phrase that actually matters.
  .rows > .row > .rt + .rd,A flat list where each item has a label and a consequence.
  ".scroll > table  (td.n, .v.ok/.no/.cl/.mo)",Comparison. Wide content scrolls ITSELF so the page never scrolls sideways.
  "--go / --hold / --stop","SEMANTIC colour: cheap / needs judgement / costs either way. Never decoration."
  "--aurora",The accent. Structure and emphasis only -- it must never carry status.
```

`aurora report` (exit 2)

```
error: "--title is required -- it names the browser tab AND the gallery card, so an untitled scaffold publishes as an unnamed card"
code: USAGE
help[1]:
  uv run agent_cli.py report --title "<title>" --out <path>.html
```
