# AXI bench: `eye`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 32/35 (91%) | 33/35 (94%) | +3 pp |
| Output tokens, as the reader counts them (median) | 150 | 153 | +3 (+2%) |
| Stdout characters (all runs) | 2,394 | 2,775 | +381 (+16%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many events match the phrase in total? | `5` | 5/5 | 5/5 |
| Are all of the matching events listed in this output? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many indexed events are in the operator voice? | `23` | 4/5 | 5/5 |
| What verdict did the frequency check reach? Give the verdict only. | `standing-directive` | 5/5 | 5/5 |
| How many records make up the same utterance as the traced event? | `3` | 5/5 | 5/5 |
| Which recurring directive does no durable plane cite? Quote the phrase. | `always fence the migration path before shipping it` | 5/5 | 4/5 |
| Was an event found at the address? Answer yes or no. | `no` | 3/5 | 4/5 |

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

`aurora eye find sword` (exit 0)

```
  session_alpha:1  [operator/user]  I want the fixture payrolls sword to be sharper every week
  session_alpha:2  [agent/assistant]  Understood - sharpening the fixture sword now.
  session_beta:1  [operator/user]  beta session opening: the fixture sword idea again, third time
  session_gamma:1  [operator/user]  gamma opening: sharpen the gamma sword
  session_beta:2  [agent/assistant]  Beta acknowledges the fixture sword.
[eye] 5/5 hit(s), ~58 tok -- drill: uv run agent_cli.py eye get <event_id>
```

`aurora eye find sword --limit 2` (exit 0)

```
  session_alpha:1  [operator/user]  I want the fixture payrolls sword to be sharper every week
  session_alpha:2  [agent/assistant]  Understood - sharpening the fixture sword now.
[eye] 2/5 hit(s), ~25 tok -- drill: uv run agent_cli.py eye get <event_id>
```

`aurora eye stats` (exit 0)

```
[eye stats] 40 events | 8 sessions | time-fog 0.0% (0 timeless)
  by voice: {'agent': 13, 'operator': 23, 'system': 4}
  by kind:  {'assistant': 13, 'queue-operation': 9, 'system': 1, 'user': 17}
```

`aurora eye freq sword` (exit 0)

```
[eye freq] 'sword'
  VERDICT: STANDING-DIRECTIVE  -- 3 operator event(s) across 3 session(s); 5 total (by voice: {'operator': 3, 'agent': 2})  span 2026-08-01 -> 2026-08-02
    session_alpha: 1 op / 2 total  refs: session_alpha:1, session_alpha:2
    session_beta: 1 op / 2 total  refs: session_beta:1, session_beta:2
    session_gamma: 1 op / 1 total  refs: session_gamma:1
```

`aurora eye trace session_gamma:5` (exit 0)

```
# session_gamma:5  (operator, user)
  gamma queued directive with a twin
  one utterance, 3 record(s): session_gamma:3, session_gamma:4, session_gamma:5
  UPSTREAM (where this came from):
    [recorded/follows] agent: gamma reply one - sharpening
    [recorded/follows] operator: gamma opening: sharpen the gamma sword
  DOWNSTREAM (what followed):
    [recorded/follows] agent: gamma reply two - directive taken
    [inferred/adjacent] operator: recurring cross session directive about mechanics
    [recorded/follows] agent: gamma reply three - continuing
  [FOG] 1 inferred edge(s) crossed (adjacency, not a recorded link) -- this ancestry is a positional guess
```

`aurora eye standing` (exit 0)

```
[eye standing] 1 recurring directive(s) that NO durable plane cites  (1 examined)
  [strong] said in 2 session(s), 2 utterance(s)
      "always fence the migration path before shipping it"
      check it: uv run agent_cli.py eye get session_watch_a:1
  (this instrument PROPOSES -- it files nothing. Known false-positive class: agent-authored briefs pasted into a fresh seat read as operator speech.)
```

`aurora eye get nope:1` (exit 2)

```

```


## After: output

`aurora eye find sword` (exit 0)

```
total: 5
tokens: 58
hits[5]{event_id,voice,type,snippet}:
  "session_alpha:1",operator,user,I want the fixture payrolls sword to be sharper every week
  "session_alpha:2",agent,assistant,Understood - sharpening the fixture sword now.
  "session_beta:1",operator,user,"beta session opening: the fixture sword idea again, third time"
  "session_gamma:1",operator,user,"gamma opening: sharpen the gamma sword"
  "session_beta:2",agent,assistant,Beta acknowledges the fixture sword.
help[1]:
  uv run agent_cli.py eye get session_alpha:1
```

`aurora eye find sword --limit 2` (exit 0)

```
total: 5
shown: 2
tokens: 25
hits[2]{event_id,voice,type,snippet}:
  "session_alpha:1",operator,user,I want the fixture payrolls sword to be sharper every week
  "session_alpha:2",agent,assistant,Understood - sharpening the fixture sword now.
help[2]:
  uv run agent_cli.py eye get session_alpha:1
  uv run agent_cli.py eye find sword --limit 5
```

`aurora eye stats` (exit 0)

```
events_total: 40
sessions: 8
time_fog: 0.0%
timeless: 0
by_voice:
  agent: 13
  operator: 23
  system: 4
by_kind:
  assistant: 13
  "queue-operation": 9
  system: 1
  user: 17
```

`aurora eye freq sword` (exit 0)

```
verdict: standing-directive
operator_events: 3
sessions: 3
events_total: 5
by_voice:
  operator: 3
  agent: 2
first: 2026-08-01
last: 2026-08-02
per_session[3]{session,operator,events,refs}:
  session_alpha,1,2,"session_alpha:1 session_alpha:2"
  session_beta,1,2,"session_beta:1 session_beta:2"
  session_gamma,1,1,"session_gamma:1"
help[1]:
  uv run agent_cli.py eye get session_alpha:1
```

`aurora eye trace session_gamma:5` (exit 0)

```
node: "session_gamma:5"
voice: operator
type: user
text: gamma queued directive with a twin
same_utterance[3]: "session_gamma:3","session_gamma:4","session_gamma:5"
upstream[2]{event_id,evidence,edge,voice,snippet}:
  "session_gamma:2",recorded,follows,agent,gamma reply one - sharpening
  "session_gamma:1",recorded,follows,operator,"gamma opening: sharpen the gamma sword"
downstream[3]{event_id,evidence,edge,voice,snippet}:
  "session_gamma:6",recorded,follows,agent,gamma reply two - directive taken
  "session_gamma:7",inferred,adjacent,operator,recurring cross session directive about mechanics
  "session_gamma:9",recorded,follows,agent,gamma reply three - continuing
fog: "1 inferred edge(s) crossed (adjacency, not a recorded link) -- this ancestry is a positional guess"
help[1]:
  uv run agent_cli.py eye get session_gamma:2
```

`aurora eye standing` (exit 0)

```
examined: 1
unheeded: 1
directives[1]{shape,sessions,utterances,phrase,ref}:
  strong,2,2,always fence the migration path before shipping it,"session_watch_a:1"
note: "proposals only; false positives: agent briefs pasted into a fresh seat read as operator speech"
help[1]:
  uv run agent_cli.py eye get session_watch_a:1
```

`aurora eye get nope:1` (exit 2)

```
error: "no event at 'nope:1': the address is session:line (full id or a unique sid8 prefix)"
code: NOT_FOUND
found: false
help[1]:
  uv run agent_cli.py eye find "<phrase>"
```
