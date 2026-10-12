# AXI bench: `link`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 34/35 (97%) | 35/35 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 52 | 104 | +52 (+100%) |
| Stdout characters (all runs) | 581 | 921 | +340 (+59%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many links does this fleet have? | `2` | 5/5 | 5/5 |
| What is our role in the link opslink? | `owner` | 4/5 | 5/5 |
| What is the label of our own fleet in the link teamlink? | `benchfleet` | 5/5 | 5/5 |
| How many records wait unpromoted in teamlink's quarantine? | `0` | 5/5 | 5/5 |
| What is this device's label? | `benchfleet` | 5/5 | 5/5 |
| How many records are in teamlink's quarantine? | `0` | 5/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora link list` (exit 0)

```
teamlink             315b758b746b3066  role owner    members 1  epoch 0
opslink              6e6cf0380465a480  role owner    members 1  epoch 0
```

`aurora link status teamlink` (exit 0)

```
teamlink  315b758b746b3066988c6739f00f05ed2adb0d97ecabba1b4f8a333639331b43
  epoch 0  our role owner  acl entries 1
  benchfleet (us): owner
    benchfleet     26f22ffb5949141d head 0     last contact never
  quarantine: 0 unpromoted
```

`aurora link whoami` (exit 0)

```
device 26f22ffb5949141d  label benchfleet
fingerprint 15998 20376 66087 14030 92504 96482
certificate valid until 2027-01-10 15:24
```

`aurora link inbox teamlink` (exit 0)

```
quarantine is empty
```

`aurora link inbox` (exit 2)

```
[link] usage: aurora link inbox <link> [--limit 20]
```


## After: output

`aurora link list` (exit 0)

```
total: 2
links[2]{name,link,role,members,epoch}:
  teamlink,313084abfc26282b,owner,1,0
  opslink,4645d05e062e396e,owner,1,0
help[2]:
  uv run agent_cli.py link status <name>
  uv run agent_cli.py link invite <name>
```

`aurora link status teamlink` (exit 0)

```
name: teamlink
link: 313084abfc26282b2b628b41082b149ef11638ff23b508f9dfdacf3e87726aa7
epoch: 0
role: owner
acl_entries: 1
quarantine_unpromoted: 0
members[1]{fleet,state,verified}:
  benchfleet,owner,us
devices[1]{fleet,device,id,head,last_contact,state}:
  benchfleet,benchfleet,26f22ffb5949141d,0,never,ok
help[1]:
  uv run agent_cli.py link invite teamlink
```

`aurora link whoami` (exit 0)

```
device: 26f22ffb5949141d
label: benchfleet
fingerprint: 15998 20376 66087 14030 92504 96482
cert_expires: "2027-01-10 15:24"
renew_soon: false
```

`aurora link inbox teamlink` (exit 0)

```
link: teamlink
quarantined: 0
records: []
help[1]:
  uv run agent_cli.py link status teamlink
```

`aurora link inbox` (exit 2)

```
error: "usage: aurora link inbox <link> [--limit 20]"
code: USAGE
help[1]:
  uv run agent_cli.py link --help
```
