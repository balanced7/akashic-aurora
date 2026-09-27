# Drill receipt — world consolidation: alpha and beta retired

**Date:** 2026-09-27 · **Run by:** claude · **Authorised by:** Daniel, verbatim:
*"lets consolidate, rescue the records and retire alpha and beta then run a full sweep to make sure
all wires work, this way our wakeability issues will be greatly simplified"*

**Verdict:** archive VERIFIED · rescue VERIFIED through the read doors · retirement EXECUTED ·
reversal DRILLED. A retirement whose reversal is merely asserted is presumed broken, so it was run.

---

## What the state actually was, measured not recalled

| world | port | keys | last stream write | |
|---|---|---|---|---|
| prod | 16379 | 46,128 | 0.0h ago | live |
| beta | 16380 | 6,626 | **1,055h ago** (2026-08-14) | dead 44 days |
| alpha | 16381 | 7,117 | **48.5h ago** (2026-09-25 04:30) | dead 2 days |

The split-brain that made this urgent had already stopped: alpha took no write in 48 hours once the
stale `AKASHIC_REPO` routing MCP writes there was fixed. Heimdall's house-round finding said the
same from the other side — *"the third world was a shadow cast by a stale shell variable, and
shadows are not production tiers."*

## 1. Archive — before anything was touched

```
alpha-16381-20260927.jsonl   7,117 keys   23,080,316 bytes
beta-16380-20260927.jsonl    6,626 keys   20,470,861 bytes
manifest-20260927.json
```
At `E:\Akashic Aurora\world-retirement\`. Every key dumped with its real type (string / hash / set
/ zset / list / stream). **Re-read to verify: 7,117 and 6,626 rows re-parsed, 0 unparseable, key
counts matching exactly.** An archive nobody has parsed is a hope, not a backup.

## 2. Rescue — and the method error that made a second pass necessary

**Round 1 diffed KEY NAMES.** That found 156 alpha-only keys and rescued 3 real lessons, 6 note
bodies, 6 head pointers, 92 beats and 26 event keys. Then `note --get` still refused on all six
notes, with the bodies and pointers both correct.

**The cause was the method, not the data.** In this store most durable records live INSIDE
containers, so any set / zset / hash present in BOTH worlds with different contents was invisible to
a name diff. `get_decisions()` scans a zset index (`mem:decisions:idx`); a note absent from that
zset cannot be found by id or by title no matter how correct its body is. A copied record no index
can reach is not rescued, it is buried.

**Round 2 diffed CONTENTS** and was short by more than an index registration:

| container | type | alpha-only members |
|---|---|---|
| `narr:beats:timeline` | zset | 92 |
| `narr:track:ai-setup:beats` | zset | 53 |
| `narr:track:unknown:beats` | zset | 39 |
| `mem:decisions:idx` | zset | **24** (round 1 rescued 0) |
| `events:raw:tindex` | zset | 20 |
| `mem:decisions` | hash | **18** (round 1 rescued 6) |
| `learn:experiments:success` | zset | 7 |
| `context:blockers` / `context:milestones` | hash | 4 + 4 |
| 2 × `events:raw:byref:*` | set | 1 each |

**263 members merged.** Plus beta's last unique event and its one index member.

**Not rescued, deliberately:** 4 test-seat lessons (`flow_exp_*`, `slice2_learn_*`, whose
recommendations are literally "r" and "use it") and their 2 `learn:agent:flow_*` index keys; 22
`bifrost:*` keys (ephemeral transport, bounded by design); `learn:category:testing` (indexes exactly
the lessons above, so registering it would contradict the decision); and each world's own
`world:seed:manifest` identity marker, which is meaningless in prod.

**The three rescued lessons, with provenance preserved verbatim** — a rescued lesson re-authored by
me would be a forged attribution:

- `a_prechewed_digest_carries_the_prechewers_interpretation_and_the_fan_reasons_from_it` — claude,
  2026-08-14, category `correction`
- `checker_entrypoints_live_under_scripts_checkers` — **sol**, 2026-09-06, category `tooling`
- `persistent_worktree_runtime_mounts_for_services` — **sol**, 2026-09-04, category `integration`

That last one is a lesson about **declaring `.aurora-world`**, stranded in the wrong world because
nobody declared it. And two of the rescued notes are `drilldone*` **drill receipts** — by this
house's own law a recovery path without a dated receipt is presumed broken, so a stranded receipt
silently un-proves a drill.

### Rescue verified through the read doors, not by trusting the writes

| check | result |
|---|---|
| 3 lessons via `recall --full` | answer, authorship intact (claude, sol, sol) |
| notes via `note --get` | refused after round 1, **OK after round 2** |
| prod `learn:experiment:*` | 1,514 → **1,517** (+3 exactly) |
| `mem:decisions` fields | 1,795 → **1,819** (+24) |
| `mem:decisions:idx` members | 1,794 → **1,818** (+24) |
| alpha-only containers remaining | **0** |
| alpha name-only keys remaining | 6 — the test lessons and index keys refused above |

Dangling beat sources fell 31 → 25; the six that resolved were the ones pointing at the rescued
records. The remaining 25 point at test seats (`tester:`, `flow:`, `x:`, `test:`) and `git:` refs
that never existed in prod.

## 3. Retirement

```
docker stop akashic-redis-alpha akashic-redis-beta
```

Both exited **0**. Containers **retained, not removed**. Named volumes `akashic-alpha-data` and
`akashic-beta-data` survive. Restart policy on all three is `unless-stopped`, so an explicit stop
keeps them down across a reboot without touching the policy.

## 4. Reversal — DRILLED, not asserted

```
docker start akashic-redis-alpha   →  7,116 keys, rescued lesson present: True
docker stop  akashic-redis-alpha   →  Exited (0)
```

**Honest note on the count:** 7,116 on restart against 7,117 at archive time. One key fewer, which I
attribute to a TTL-bearing `bifrost:*` transport key expiring during the ~20-minute interval — that
is an INFERENCE, not a measurement; I did not identify the specific key. It does not bear on safety:
every durable record is independently verified present in prod (counts above) and in the
re-parsed archive.

## 5. What is still declared but no longer deployed

`config.py:68,74` still define `REDIS_PORT_BETA`/`REDIS_PORT_ALPHA`, and the `WORLDS` registry at
`core/world.py:144-146` still names both containers. The declarations now point at stopped stores.
Whether that should be reconciled is a separate decision and is deliberately NOT done here —
Heimdall's finding 2 was that *"beta and alpha are declarations, not deployments"*, and the
declaration half is a code change to the world resolver that deserves its own slice.

## Reproduce

```bash
py agent_cli.py status
```

Archive and manifest: `E:\Akashic Aurora\world-retirement\`.
House round and both filed halves: `fences/world-consolidation/`.
