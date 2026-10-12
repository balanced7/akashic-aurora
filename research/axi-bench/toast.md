# AXI bench: `toast`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 30/30 (100%) | +17 pp |
| Output tokens, as the reader counts them (median) | 67 | 72 | +5 (+7%) |
| Stdout characters (all runs) | 887 | 1,188 | +301 (+34%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the receipt verified? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Was the bus message sent? Answer yes or no. | `yes` | 5/5 | 5/5 |
| What verification tier is the toast labelled with? | `GUESS` | 5/5 | 5/5 |
| Was the toast sent? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which agent does the port_clash lesson belong to? | `alice` | 5/5 | 5/5 |
| Which flag must be added for the command to work? Give the flag only. | `['--credit']` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora toast bench alice port_clash --credit saved two hours of bisecting` (exit 0)

```
toast [VERIFIED] (exact experiment id)
  bus : sent
  note: written -> toast:alice-port-clash
  line: [VERIFIED] 🧫 @alice: saved two hours of bisecting (receipt: port_clash)
```

`aurora toast bench alice made_up_thing --credit thanks anyway --force` (exit 0)

```
toast [GUESS] (no experiment matching 'made_up_thing' in the store)
  bus : sent
  note: written -> toast:alice-made-up-thing
  line: [GUESS :unverified receipt] 🧫 @alice: thanks anyway (claimed receipt: made_up_thing)
```

`aurora toast bench alice made_up_thing --credit thanks anyway` (exit 2)

```
[toast] toast REFUSED: receipt does not verify (no experiment matching 'made_up_thing' in the store). Re-check the experiment name, or pass force=True to send it honestly labeled GUESS.
```

`aurora toast bench carol port_clash --credit thanks` (exit 2)

```
[toast] toast REFUSED: receipt does not verify (experiment 'port_clash' belongs to alice, not carol). Re-check the experiment name, or pass force=True to send it honestly labeled GUESS.
```

`aurora toast bench alice port_clash` (exit 2)

```
[toast] toast needs the credit (what did their lesson save you?) -- gratitude without the receipt-detail is a hollow ping
```


## After: output

`aurora toast bench alice port_clash --credit saved two hours of bisecting` (exit 0)

```
to: alice
receipt: port_clash
tier: VERIFIED
verified_by: exact experiment id
bus: sent
note: written
note_title: "toast:alice-port-clash"
```

`aurora toast bench alice made_up_thing --credit thanks anyway --force` (exit 0)

```
to: alice
receipt: made_up_thing
tier: GUESS
verified_by: no experiment matching 'made_up_thing' in the store
bus: sent
note: written
note_title: "toast:alice-made-up-thing"
```

`aurora toast bench alice made_up_thing --credit thanks anyway` (exit 2)

```
error: "receipt does not verify (no experiment matching 'made_up_thing' in the store). Re-check the experiment name, or pass --force to send it honestly labeled GUESS."
code: REFUSED
help[2]:
  uv run agent_cli.py recall "made_up_thing"
  uv run agent_cli.py toast bench alice made_up_thing --credit "..." --force
```

`aurora toast bench carol port_clash --credit thanks` (exit 2)

```
error: "receipt does not verify (experiment 'port_clash' belongs to alice, not carol). Re-check the experiment name, or pass --force to send it honestly labeled GUESS."
code: REFUSED
help[2]:
  uv run agent_cli.py recall "port_clash"
  uv run agent_cli.py toast bench carol port_clash --credit "..." --force
```

`aurora toast bench alice port_clash` (exit 2)

```
error: toast needs the credit (what did their lesson save you?) -- gratitude without the receipt-detail is a hollow ping
code: REFUSED
help[1]:
  uv run agent_cli.py toast bench alice port_clash --credit "<what their lesson saved you, under 400 chars>"
```
