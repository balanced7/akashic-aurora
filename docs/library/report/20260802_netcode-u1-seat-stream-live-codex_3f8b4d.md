---
akashic_id: art_20260802_netcode-u1-seat-stream-live-codex_3f8b4d
akashic_sha: 47f13005cc35
schema_version: 1
status: current
type: report
date: 2026-08-02
title: netcode-u1-seat-stream-live-codex
gist: "# U1 live receipt — seat-stream execution under the work-lane cutover Status: current (2026-08-02, `codex_root_019fab2d`). Observation-only "
visibility: fleet
body_type: markdown
seats: [codex]
category: [library, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T01:39:32"
updated: "2026-08-02T01:39:32"
---
<!-- GENERATED PROJECTION of art_20260802_netcode-u1-seat-stream-live-codex_3f8b4d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# netcode-u1-seat-stream-live-codex

# U1 live receipt — seat-stream execution under the work-lane cutover

Status: current (2026-08-02, `codex_root_019fab2d`). Observation-only U1 filing for the netcode arc.

## Verdict

**PLAIN PATH PASS; PRODUCTION WORK-LANE PATH FAILS THE U1 REACHABILITY CLAIM.**

The per-seat stream executes under `Bus.inbox(advance=True)`: a directed packet is read from
`{ns}:inbox:{agent}#{sid8}`, the per-seat cursor is created, and `seat_seen` is marked.

The per-seat stream does **not** execute under `BIFROST_CONSUME_LANE=work`. The production
`BifrostAPI.work_drain()` call returned the packet from the work lane with `_lane_src=work`,
while the seat-stream copy remained unread. No `cursor:seat` key and no `seat_seen` key were
created. A fresh replay reproduced the same result.

The two-incarnation result needs precise wording. On the shared-cursor session-consume
composition tested in Receipt 5:

- B did **not** receive A's body when `BIFROST_INCARNATION` was set; the incarnation filter held.
- B nevertheless advanced the shared work-lane cursor past A's packet.
- A then received nothing, while A's untouched seat stream still contained the packet.

So content theft was not observed, but delivery ownership still failed on that door: B could
make A's directed packet unreachable through the consuming work-lane path. The plain path
prevents that starvation by reading A's independent seat stream after the shared cursor has
moved; lane mode turns that recovery path off. This starvation claim is not generalized to the
current DeepSeek runner loop, whose distinct split read/commit composition is recorded in
Receipt 4; the runner was not launched in this drill.

No fix is proposed or applied in this filing.

## Root cause hypothesis, now reproduced

I think the seat-stream path is unreachable in lane mode because `work_drain()` calls
`Bus.wait()` with **both** caller-owned `since` positions and explicit `streams`.
`Bus._drain()` adds the seat stream only when all three conditions hold:

```python
if sid8 and since is None and streams is None:
```

The runtime receipts below support that causal account: the same logical delivery appeared on
the work and seat streams; lane mode returned only the work copy, never wrote the seat cursor,
and never marked seat deduplication.

## Bounds and setup

- Redis was reachable: `redis_ping=true`.
- Lane dual-write was on: `dual_write=true`.
- Every bus object used a fresh `test-*` namespace. No live Bifrost namespace was read,
  consumed, or modified.
- Target agent: `u1target-8921f917`; sender: `u1sender-8921f917`.
- Seat A: `a1b2c3d4-1111-2222-3333-444455556666`.
- Seat B: `b5c6d7e8-1111-2222-3333-444455556666`.
- The calls were made directly through the production `Bus` and `BifrostAPI` classes in a
  PowerShell here-string piped to `py -`. This avoided launching a model runner or taking a
  global runner lock while exercising the receive functions themselves.
- Stream IDs below are reported independently. I do not infer logical identity from adjacent
  Redis IDs; where identity matters, the packet body/meta and, in the first plain run, the
  identical packet SHA establish it.

## Receipt 1 — clean baseline and explicit non-Claude incarnation

Namespace:

```text
test-u1-codex-8921f917-plain
```

Before the send:

```json
{"keys": [], "seat_cursor_keys": [], "seat_seen_keys": []}
```

Process identity:

```json
{"BIFROST_INCARNATION":"a1b2c3d4-1111-2222-3333-444455556666",
 "CLAUDE_CODE_SESSION_ID":null,
 "my_sid8":"a1b2c3d4"}
```

This settles the arm step for a non-Claude process: `_my_sid8()` returned `a1b2c3d4` from
`BIFROST_INCARNATION` alone.

## Receipt 2 — directed send and plain seat-stream consume

The send created both concrete streams with the same packet SHA
`9aada73c51404d9398ba5326c7ec990185c057cbe0d3d643a7688f0c253775bd`:

```text
work stream: test-u1-codex-8921f917-plain:work:inbox:u1target-8921f917
work id:     1785648867681-0

seat stream: test-u1-codex-8921f917-plain:inbox:u1target-8921f917#a1b2c3d4
seat id:     1785648867682-0

body:        plain-for-a-8921f917
to_incarnation: a1b2c3d4-1111-2222-3333-444455556666
```

Before consumption, the seat cursor did not exist. After
`Bus("u1target-8921f917", namespace=...).inbox(advance=True)`:

```json
{"returned":[{"content":"plain-for-a-8921f917","id":"1785648867682-0",
              "to_incarnation":"a1b2c3d4-1111-2222-3333-444455556666"}],
 "seat_cursor_key":"test-u1-codex-8921f917-plain:cursor:seat:u1target-8921f917#a1b2c3d4",
 "seat_cursor":{"seat":"1785648867682-0"},
 "seat_seen_key":"test-u1-codex-8921f917-plain:seat_seen:9aada73c51404d9398ba5326c7ec990185c057cbe0d3d643a7688f0c253775bd",
 "seat_seen_value":"1",
 "seat_seen_ttl":1198}
```

Plain-path U1 is therefore live, not merely present in code.

## Receipt 3 — plain-path two-seat isolation

Seat B consumed first. It received no body, although its filtered read advanced the shared
legacy cursor:

```json
{"b_sid8":"b5c6d7e8",
 "b_returned":[],
 "shared_cursor_after_b":{"gen":"0","inbox":"1785648869493-0"}}
```

Seat A then received its own copy from the independent seat stream:

```json
{"a_sid8":"a1b2c3d4",
 "a_returned":[{"content":"plain-theft-for-a-8921f917","id":"1785648869494-0"}],
 "a_seat_cursor":{"seat":"1785648869494-0"}}
```

This is the property T108 S1 intended: another incarnation can move the shared cursor without
stranding the addressed incarnation, because the seat stream remains independently readable.

## Receipt 4 — work-lane ordering trap

Namespace:

```text
test-u1-codex-8921f917-work
```

The runner-shaped Bus and the `BifrostAPI` helper did not even name the same lane cursor:

```json
{"runner_lane_key":"test-u1-codex-8921f917-work:cursor:lane:u1target-8921f917#a1b2c3d4",
 "api_lane_key":"test-u1-codex-8921f917-work:cursor:lane:u1target-8921f917",
 "runner_cursor":{},
 "api_cursor":{}}
```

After a directed send and `api.work_drain(timeout_ms=10, since_out=batch_next)`:

```json
{"returned":[{"content":"work-for-a-8921f917",
              "id":"1785648869862-0",
              "_lane_src":"work",
              "to_incarnation":"a1b2c3d4-1111-2222-3333-444455556666"}],
 "batch_next":{"bc":"0","inbox":"1785648869862-0"},
 "runner_commit_status":"OK",
 "runner_cursor":{"gen":"0","inbox":"1785648869862-0"},
 "api_cursor":{"shadow_inbox":"1785648869863-0"}}
```

At that same moment, the seat copy still existed:

```text
seat stream key: test-u1-codex-8921f917-work:inbox:u1target-8921f917#a1b2c3d4
seat stream id:  1785648869864-0
body:            work-for-a-8921f917
```

But the execution witnesses were absent:

```json
{"seat_cursor_key":"test-u1-codex-8921f917-work:cursor:seat:u1target-8921f917#a1b2c3d4",
 "seat_cursor_exists":false,
 "seat_seen":{}}
```

The packet delivered, but not through U1.

## Receipt 5 — work-lane two-seat starvation

Namespace:

```text
test-u1-codex-8921f917-work-theft
```

Using the `BifrostAPI` session-consume cursor composition, seat B read first. The incarnation
filter kept A's body out of B's return value, but the safe next position still crossed A's work
entry and committed successfully:

```json
{"b_sid8":"b5c6d7e8",
 "b_returned":[],
 "b_next":{"bc":"0","inbox":"1785648872288-0"},
 "b_commit_status":"OK",
 "shared_lane_key":"test-u1-codex-8921f917-work-theft:cursor:lane:u1target-8921f917",
 "shared_cursor_after_b":{"gen":"0","inbox":"1785648872288-0",
                          "shadow_inbox":"1785648872289-0"}}
```

Seat A then read from the same production helper path:

```json
{"a_sid8":"a1b2c3d4","a_returned":[],"a_next":{}}
```

A's seat stream still contained the packet, but the work-lane receive path never opened it:

```text
seat stream key: test-u1-codex-8921f917-work-theft:inbox:u1target-8921f917#a1b2c3d4
seat stream id:  1785648872289-0
body:            work-theft-for-a-8921f917
seat cursor:     absent
seat_seen:       absent
```

This is not cross-seat body disclosure. On this shared-cursor production door, it is cross-seat
cursor theft followed by starvation of the addressed seat. The current DeepSeek runner's
separate `Bus(incarnation=...)` commit key avoids making this exact shared-cursor observation
directly comparable; it also creates the different read/commit mismatch shown in Receipt 4.

## Independent replay

A second process used fresh namespaces rooted at `test-u1-codex-replay-76f772d2`.

Gate replay:

```json
{"baseline":[],
 "returned":[{"content":"gate-replay","id":"1785648972560-0","lane":"work",
              "to_incarnation":"a1b2c3d4-1111-2222-3333-444455556666"}],
 "seat_stream_key":"test-u1-codex-replay-76f772d2-gate:inbox:u1replay-76f772d2#a1b2c3d4",
 "seat_stream_ids":["1785648972562-0"],
 "seat_cursor_exists":false,
 "seat_seen_keys":[]}
```

Theft replay:

```json
{"baseline":[],
 "b_returned":[],
 "b_next":{"bc":"0","inbox":"1785648976702-0"},
 "b_commit":"OK",
 "shared_cursor_after_b":{"gen":"0","inbox":"1785648976702-0",
                          "shadow_inbox":"1785648976703-0"},
 "a_returned":[],
 "a_next":{},
 "seat_stream_ids":["1785648976703-0"],
 "a_seat_cursor_exists":false}
```

The replay matched the first run.

## Cleanup receipt

All keys discovered under the four first-run namespaces were deleted only after their values
were captured; each namespace then scanned empty. The independent replay also ended with:

```json
{"test-u1-codex-replay-76f772d2-gate":[],
 "test-u1-codex-replay-76f772d2-theft":[],
 "root_prefix_remaining":[]}
```

The `UNATTENDED RECIPIENT` warnings in both runs were expected: the synthetic target deliberately
had no roster heartbeat. They did not block the sends and are not evidence about U1.

## What I did not run

- No send, consume, cursor advance, or cleanup touched the live Bifrost namespace.
- I did not launch the DeepSeek/model runner, take a global runner lock, or invoke a model. The
  runner's production `Bus`/`BifrostAPI` receive calls were exercised directly. Therefore this
  filing claims that its seat stream is bypassed, not that the full runner loop reproduced the
  exact Receipt 5 starvation outcome.
- I did not run role-queue claiming, reaping/rehome, fragmentation, reply settlement, or the
  U2/U3 implementation audit.
- I did not test the unarmed case where `_my_sid8()` is empty; this brief explicitly required
  arming `BIFROST_INCARNATION` first.
- I did not alter production code or propose a repair.

## Consequence for the sequence board

U1 exists and works on the plain legacy consume path, but it is bypassed under the work-lane
configuration used by production consumers. Therefore `0 cursor:seat` and `0 seat_seen` in the
live namespace were not merely lack of traffic; the configured receive door cannot create them.

T108 S1 should not be credited as executing in production until the work-lane receive path either
opens the addressed seat stream or supplies an independently verified equivalent that preserves
both non-disclosure and delivery ownership across incarnations. This filing does not choose that
mechanism.
