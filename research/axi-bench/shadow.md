# AXI bench: `shadow`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 317 | 359 | +42 (+13%) |
| Stdout characters (all runs) | 1,999 | 2,427 | +428 (+21%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is the subject allowed to perform this action? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which capability is missing? | `['bus.send']` | 0/5 | 5/5 |
| What risk level does the preview assign? | `elevated` | 5/5 | 5/5 |
| How many proposed effects are listed? | `4` | 5/5 | 5/5 |
| Was anything actually sent? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which actions are supported? List them separated by commas. | `['toolbox:bifrost_send', 'toolbox:bifrost_nudge', 'toolbox:bifrost_steer']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora shadow toolbox:bifrost_send --agent bench --args-json {"to": "kimi", "kind": "request", "text": "please rerun the suite"}` (exit 0)

```
# shadow subject=bench action=toolbox:bifrost_send fingerprint=14410f354563
  target seat:kimi (addressed as 'kimi')
  fidelity message:request | authority=refused allowed=False
  risk elevated | commit=required_unenforced
  cost chars=22 rough_tokens=6 recipient_turns=[0, 1]
  -> [expected] bifrost.message.enqueue: lane/legacy delivery is appended
  -> [expected] wake.bell.publish: the recipient doorbell is rung
  -> [expected] sender.presence.refresh: sender presence is refreshed
  -> [conditional] recipient.turn.wake: an armed watcher may spend a recipient model turn
  preview effects=none
  blind: preview does not prove bus availability, recipient attendance, or eventual adoption; commit is disclosed but no execution token is enforced yet; token estimate covers message content only, not prompt or tool overhead
```

`aurora shadow toolbox:bifrost_nudge --agent bench --args-json {"to": "kimi", "text": "wake"}` (exit 0)

```
# shadow subject=bench action=toolbox:bifrost_nudge fingerprint=a853aa659221
  target seat:kimi (addressed as 'kimi')
  fidelity interrupt | authority=refused allowed=False
  risk high | commit=required_unenforced
  cost chars=4 rough_tokens=1 recipient_turns=[0, 1]
  -> [expected] peer.control.interrupt_flag: a TTL-bounded barge-in flag is set
  -> [expected] bifrost.message.enqueue: lane/legacy delivery is appended
  -> [expected] wake.bell.publish: the recipient doorbell is rung
  -> [expected] sender.presence.refresh: sender presence is refreshed
  -> [conditional] recipient.turn.interrupt: a cooperating runner stops at its next round boundary
  preview effects=none
  blind: preview does not prove bus availability, recipient attendance, or eventual adoption; commit is disclosed but no execution token is enforced yet; token estimate covers message content only, not prompt or tool overhead
```

`aurora shadow toolbox:delete_everything --agent bench` (exit 2)

```
ERROR: unsupported intent-shadow action 'toolbox:delete_everything'; supported: toolbox:bifrost_send, toolbox:bifrost_nudge, toolbox:bifrost_steer
```

`aurora shadow toolbox:bifrost_send --agent bench --args-json {bad` (exit 2)

```
ERROR: --args-json must be one JSON object (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))
```


## After: output

`aurora shadow toolbox:bifrost_send --agent bench --args-json {"to": "kimi", "kind": "request", "text": "please rerun the suite"}` (exit 0)

```
subject: bench
action: "toolbox:bifrost_send"
target: "seat:kimi"
fidelity: "message:request"
allowed: no
authority: refused
missing_caps[1]: bus.send
risk: elevated
commit: required_unenforced
reversibility: irreversible_after_observation
content_chars: 22
rough_tokens: 6
recipient_turns: 0-1
effects[4]{certainty,effect,claim}:
  expected,bifrost.message.enqueue,lane/legacy delivery is appended
  expected,wake.bell.publish,the recipient doorbell is rung
  expected,sender.presence.refresh,sender presence is refreshed
  conditional,recipient.turn.wake,an armed watcher may spend a recipient model turn
executed: nothing (a preview has no effects)
blind[3]: "preview does not prove bus availability, recipient attendance, or eventual adoption",commit is disclosed but no execution token is enforced yet,"token estimate covers message content only, not prompt or tool overhead"
fingerprint: 14410f354563
```

`aurora shadow toolbox:bifrost_nudge --agent bench --args-json {"to": "kimi", "text": "wake"}` (exit 0)

```
subject: bench
action: "toolbox:bifrost_nudge"
target: "seat:kimi"
fidelity: interrupt
allowed: no
authority: refused
missing_caps[2]: bus.nudge,bus.send
risk: high
commit: required_unenforced
reversibility: irreversible_after_observation
content_chars: 4
rough_tokens: 1
recipient_turns: 0-1
effects[5]{certainty,effect,claim}:
  expected,peer.control.interrupt_flag,a TTL-bounded barge-in flag is set
  expected,bifrost.message.enqueue,lane/legacy delivery is appended
  expected,wake.bell.publish,the recipient doorbell is rung
  expected,sender.presence.refresh,sender presence is refreshed
  conditional,recipient.turn.interrupt,a cooperating runner stops at its next round boundary
executed: nothing (a preview has no effects)
blind[3]: "preview does not prove bus availability, recipient attendance, or eventual adoption",commit is disclosed but no execution token is enforced yet,"token estimate covers message content only, not prompt or tool overhead"
fingerprint: a853aa659221
```

`aurora shadow toolbox:delete_everything --agent bench` (exit 2)

```
error: "unsupported intent-shadow action 'toolbox:delete_everything'; supported: toolbox:bifrost_send, toolbox:bifrost_nudge, toolbox:bifrost_steer"
code: USAGE
help[1]:
  uv run agent_cli.py shadow toolbox:bifrost_send --agent <id> --args-json '{"to": "<seat>", "text": "..."}'
```

`aurora shadow toolbox:bifrost_send --agent bench --args-json {bad` (exit 2)

```
error: "--args-json must be one JSON object (Expecting property name enclosed in double quotes: line 1 column 2 (char 1))"
code: USAGE
help[1]:
  uv run agent_cli.py shadow toolbox:bifrost_send --agent <id> --args-json '{"to": "<seat>", "text": "..."}'
```
