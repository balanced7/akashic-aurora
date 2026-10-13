# AXI bench: `link`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 65/75 (87%) | 75/75 (100%) | +13 pp |
| Output tokens, as the reader counts them (median) | 58 | 117 | +59 (+102%) |
| Stdout characters (all runs) | 2,033 | 2,987 | +954 (+47%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many links does this fleet have? | `2` | 5/5 | 5/5 |
| What is our role in the link opslink? | `owner` | 5/5 | 5/5 |
| What is the label of our own fleet in the link teamlink? | `benchfleet` | 5/5 | 5/5 |
| How many records wait unpromoted in teamlink's quarantine? | `0` | 5/5 | 5/5 |
| What is this device's label? | `benchfleet` | 5/5 | 5/5 |
| How many records are in teamlink's quarantine? | `0` | 5/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 5/5 | 5/5 |
| What is the exact command to invite someone into the link that was just created? | `link invite newlink` | 0/5 | 5/5 |
| What role does someone joining with this invite get? | `reader` | 5/5 | 5/5 |
| Must the inviter approve the join after they join? Answer yes or no. | `yes` | 5/5 | 5/5 |
| How many other fleets' safety numbers are listed? | `0` | 0/5 | 5/5 |
| How many ACL entries went into the bundle? | `2` | 5/5 | 5/5 |
| How many records did the import refuse? | `0` | 5/5 | 5/5 |
| Are these policy files synced to the link's other members? Answer yes or no. | `no` | 5/5 | 5/5 |
| What is the file name the certificate was written to? | `cert.json` | 5/5 | 5/5 |

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
opslink              74b119c1ecfa3916  role owner    members 1  epoch 0
teamlink             c3e0e53d03d939b7  role owner    members 1  epoch 0
```

`aurora link status teamlink` (exit 0)

```
teamlink  c3e0e53d03d939b72b40feca83b1e05fb7ca18e1e095bac855485b99f3853760
  epoch 0  our role owner  acl entries 1
  benchfleet (us): owner
    benchfleet     df2fea5e4fcbb959 head 0     last contact never
  quarantine: 0 unpromoted
```

`aurora link whoami` (exit 0)

```
device df2fea5e4fcbb959  label benchfleet
fingerprint 71549 80971 81591 14856 41537 25697
certificate valid until 2027-01-11 01:26
```

`aurora link inbox teamlink` (exit 0)

```
quarantine is empty
```

`aurora link inbox` (exit 2)

```
[link] usage: aurora link inbox <link> [--limit 20]
```

`aurora link create newlink` (exit 0)

```
link newlink created: 83dd15a42c40042b7c099d0d1d4689401e3ad2d241e15f584611718e62c211ed
our fingerprint 71549 80971 81591 14856 41537 25697
```

`aurora link invite teamlink --role reader --ttl 2h --approval` (exit 0)

```
invite for reader in teamlink, single-use, expires 2026-10-13 04:26 (needs your approval after they join)

aurora-invite1:eyJmaW5nZXJwcmludCI6IjcxNTQ5ODA5NzE4MTU5MTE0ODU2NDE1MzcyNTY5NyIsImxpbmsiOiJjM2UwZTUzZDAzZDkzOWI3MmI0MGZlY2E4M2IxZTA1ZmI3Y2ExOGUxZTA5NWJhYzg1NTQ4NWI5OWYzODUzNzYwIiwibmFtZSI6InRlYW1saW5rIiwibm9kZSI6ImRmMmZlYTVlNGZjYmI5NTljYTY3YTc1M2VkNDdiZjQyMGM4MTg5OGQ3YzE1MGYzY2QxOTE0OTEzMzY3ODBlZWMiLCJzZWNyZXQiOiI3ZGFiMTlmMDQ1MDRkMTcwODk0NGJiOWMzZWY2NGQ5Mzg5OWZhNmM1MGRmOGQ1NWY1ZjQyYzExMDFjYjQyZTM5IiwidiI6MX0

our fingerprint 71549 80971 81591 14856 41537 25697  -- the joiner should see exactly this
```

`aurora link verify teamlink` (exit 0)

```


read it to them over a call or Signal; when both of you see the same, add --mark
```

`aurora link export teamlink --out /tmp/axi-link-files-6qoumyi3/bundle.json` (exit 0)

```
wrote 2 ACL entries and 0 records to /tmp/axi-link-files-6qoumyi3/bundle.json
```

`aurora link import /tmp/axi-link-files-6qoumyi3/bundle.json` (exit 0)

```
imported into c3e0e53d03d939b7: 2 ACL entries, 0 new records, 0 refused
```

`aurora link policy opslink` (exit 0)

```
promote policy /tmp/axi-bench-r0phh484/data/state/link/74b119c1ecfa391602b71a93bbd8e2597fbc410319c9536c633027522479c775/promote.toml
export policy  /tmp/axi-bench-r0phh484/data/state/link/74b119c1ecfa391602b71a93bbd8e2597fbc410319c9536c633027522479c775/export.toml
both are local and never synced
```

`aurora link rebuild teamlink` (exit 0)

```
rebuilt the quarantine stream from the store: 0 record(s)
```

`aurora link cert --out /tmp/axi-link-files-6qoumyi3/cert.json` (exit 0)

```
wrote this device's certificate to /tmp/axi-link-files-6qoumyi3/cert.json: hand it to a device already in the link
```


## After: output

`aurora link list` (exit 0)

```
total: 2
links[2]{name,link,role,members,epoch}:
  opslink,88175a57583a8f4b,owner,1,0
  teamlink,eed5fccc97afa336,owner,1,0
help[2]:
  uv run agent_cli.py link status <name>
  uv run agent_cli.py link invite <name>
```

`aurora link status teamlink` (exit 0)

```
name: teamlink
link: eed5fccc97afa3364a03daf5551ebc7214ed3606a80aab271e90a6f900051f59
epoch: 0
role: owner
acl_entries: 1
quarantine_unpromoted: 0
members[1]{fleet,state,verified}:
  benchfleet,owner,us
devices[1]{fleet,device,id,head,last_contact,state}:
  benchfleet,benchfleet,df2fea5e4fcbb959,0,never,ok
help[1]:
  uv run agent_cli.py link invite teamlink
```

`aurora link whoami` (exit 0)

```
device: df2fea5e4fcbb959
label: benchfleet
fingerprint: 71549 80971 81591 14856 41537 25697
cert_expires: "2027-01-11 01:26"
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

`aurora link create newlink` (exit 0)

```
name: newlink
link: 98d68361887f0a8be7c8a420a95adeed6eda526ff054f8b5091855be1f2ff73c
fingerprint: 71549 80971 81591 14856 41537 25697
role: owner
help[2]:
  uv run agent_cli.py link invite newlink
  uv run agent_cli.py link status newlink
```

`aurora link invite teamlink --role reader --ttl 2h --approval` (exit 0)

```
link: teamlink
role: reader
uses: one
expires: "2026-10-13 04:27"
needs_approval: true
fingerprint: 71549 80971 81591 14856 41537 25697
code: "aurora-invite1:eyJmaW5nZXJwcmludCI6IjcxNTQ5ODA5NzE4MTU5MTE0ODU2NDE1MzcyNTY5NyIsImxpbmsiOiJlZWQ1ZmNjYzk3YWZhMzM2NGEwM2RhZjU1NTFlYmM3MjE0ZWQzNjA2YTgwYWFiMjcxZTkwYTZmOTAwMDUxZjU5IiwibmFtZSI6InRlYW1saW5rIiwibm9kZSI6ImRmMmZlYTVlNGZjYmI5NTljYTY3YTc1M2VkNDdiZjQyMGM4MTg5OGQ3YzE1MGYzY2QxOTE0OTEzMzY3ODBlZWMiLCJzZWNyZXQiOiIyYTUzYTJhZDNkYmE5MmYyNWYxNWQ3MjMwYTkxNzZkOTc3ZWY0MzA0Y2ZkMjRmNzJkMTliYTJmNGJkNzkzODQ5IiwidiI6MX0"
note: the joiner should see exactly this fingerprint
help[2]:
  uv run agent_cli.py link status teamlink
  uv run agent_cli.py link accept teamlink <join id>
```

`aurora link verify teamlink` (exit 0)

```
link: teamlink
total: 0
members: []
note: "no other fleet in this link yet: nothing to compare"
help[1]:
  uv run agent_cli.py link invite teamlink
```

`aurora link export teamlink --out /tmp/axi-link-files-6qoumyi3/bundle.json` (exit 0)

```
link: teamlink
wrote: /tmp/axi-link-files-6qoumyi3/bundle.json
acl_entries: 2
records: 0
help[1]:
  uv run agent_cli.py link import /tmp/axi-link-files-6qoumyi3/bundle.json
```

`aurora link import /tmp/axi-link-files-6qoumyi3/bundle.json` (exit 0)

```
link: eed5fccc97afa336
acl_entries: 2
records_stored: 0
records_refused: 0
help[1]:
  uv run agent_cli.py link status eed5fccc97afa336
```

`aurora link policy opslink` (exit 0)

```
link: opslink
promote_policy: /tmp/axi-bench-r0phh484/data/state/link/88175a57583a8f4bd36ab37b12dc24df334abc8fc85f28061122808488f27f23/promote.toml
export_policy: /tmp/axi-bench-r0phh484/data/state/link/88175a57583a8f4bd36ab37b12dc24df334abc8fc85f28061122808488f27f23/export.toml
scope: both are local and never synced
```

`aurora link rebuild teamlink` (exit 0)

```
link: teamlink
records: 0
```

`aurora link cert --out /tmp/axi-link-files-6qoumyi3/cert.json` (exit 0)

```
device: df2fea5e4fcbb959
label: benchfleet
valid_until: "2027-01-11 01:26"
post_quantum: true
wrote: /tmp/axi-link-files-6qoumyi3/cert.json
next: hand the file to a device already in the link; it runs add-device with it
help[1]:
  uv run agent_cli.py link add-device <link> /tmp/axi-link-files-6qoumyi3/cert.json
```
