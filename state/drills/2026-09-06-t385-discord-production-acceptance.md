# T385 drill receipt — Discord production ownership and causal delivery

**Date:** 2026-09-06 03:39–04:05 EDT (07:39–08:05 UTC)
**Deployment:** `codex/sunshine-discord-split` at `0f15d837a746`
**Drilled by:** Sunshine (`sol`) with two ordinary messages authored by Daniil
**Standing:** PARTIAL — Sunshine passed the human end-to-end gate. The gpt-new
human turn exposed a real outbound ownership defect; the repair then passed a
synthetic directed-reply drill. One fresh ordinary human message in the gpt-new
channel remains before P7 can close.

## Human-origin inputs

Discord API readback established the same authenticated operator on both inputs:
author id `198999549619077121`, username `balanced7`.

| Seat | Discord channel | Discord input id | Exact content | Production Bifrost id |
|---|---:|---:|---|---:|
| Sunshine (`sol`) | `1545418718731968602` | `1546062336803213322` | `Test sunshine room` | `1788680386529-0` |
| gpt-new | `1542163753276014703` | `1546062371427057735` | `Test Neo room` | `1788680394578-0` |

Both production rows carried `source=discord`, `operator=true`,
`speaker=daniil`, the exact Discord message id in `idempotency_key`, and the
seat-channel routing lane. Both received the gateway's final check reaction.

## Sunshine chain — PASS

The Sunshine watcher admitted `1788680386529-0` into continuity task
`01a06c82-971d-7b22-a008-ad30d9399888`, preserving source task
`01a03c80-1de3-7980-8ebc-2a5bd6d2489f` and binding
`completed-history-fork`. Its causal Bifrost reply was `1788680478654-0`.

Discord API readback then found exactly one reply in the Sunshine channel:

- Discord reply id `1546062742366982194`;
- webhook identity `Sunshine (sol)`;
- visible continuity stamp `sol · task 01a06c82`.

## gpt-new chain — defect exposed

The gpt-new watcher admitted `1788680394578-0` into its distinct continuity
task `01a06265-0904-7020-a681-e82be7c7fa36`, with the same preserved source
task and `completed-history-fork` binding. Its causal Bifrost reply was
`1788680402360-0`.

That reply did **not** return to the gpt-new channel. Discord API readback found
it in the global channel `1539414422089502762` as message
`1546062414150369351`, without the new continuity stamp. This was not an
identity failure in the model turn: it was a delivery-policy split.

Root cause: the shared `discord-pump` lock elected a new daemon for each short
beat. Daemons from different checkouts therefore took turns owning one cursor
while carrying different credential allowlists and code. The main-checkout
daemon that won this beat did not register `discord_channel_gpt-new.url`, so
the old delivery code widened the directed reply to global Discord.

## Repair

Commit `0f15d837` made two structural changes:

1. The production Discord gateway owns one stable `discord-pump` token for its
   process lifetime and refreshes it independently of webhook latency.
2. A directed operator reply with no registered private lane is a loud route
   failure and may never fall through to global Discord.

The gateway was restarted through its Scheduled Task while the EarWatchdog was
temporarily disabled, then the watchdog was re-enabled. The new gateway became
ready as PID `42100`, generation `42100-1788681532929592700`, world `prod`,
code SHA `0f15d837a746`.

## Post-repair drills

An initial synthetic row, Bifrost `1788681583737-0`, used `kind=note`. It was
processed once and correctly filtered because `note` is not in the outbound
notification allowlist. It was an invalid delivery probe, not a repair failure;
nothing appeared in either Discord channel.

A valid `kind=reply` probe then used marker
`T385-SYNTHETIC-VALID-REPLY-dbd6229db5`, Bifrost id
`1788681800111-0`. In 3.7 seconds Discord API readback found:

- exactly one match in gpt-new channel `1542163753276014703`;
- Discord message id `1546068274968789012`;
- webhook id `1542163759110422538`, author `gpt-new`;
- zero matches in global channel `1539414422089502762`.

Across a later 12-second observation, the pump holder remained token
`discord-pump:42100:f30a2c2924aa`, PID `42100`, generation `78212`; its
timestamp refreshed. An independent process attempted to acquire the same
lease and was refused. Gateway readiness kept the same PID and generation and
continued to report world `prod` and code `0f15d837a746`.

## Continuity and topology after restart

The continuity files remained byte-for-byte equal to the pre-restart baseline:

| Seat | SHA-256 | Records | Last admitted id |
|---|---|---:|---:|
| Sunshine | `B760DEADCE4159F18D56CF6905E634B12A4191700145A5CEC37888B7B2BC0870` | 16 | `1788680386529-0` |
| gpt-new | `F0A8BE3C1A1542A1947DB04D9C1DB965C049823646EB11912F9EED5E040144EE` | 10 | `1788680394578-0` |

Task Scheduler reported the gateway, both continuity watchers, and Sunshine
fleet task running from the deployment worktree through
`run_aurora_service.py --world prod`. Each owned process had Scheduler parent
PID `2308`. Every observed Redis connection for those processes targeted
production port `16379`; none targeted alpha port `16381`. The EarWatchdog was
enabled and ready, targeting only the gateway task.

## What remains unproved

- P7 still needs one ordinary, post-repair human-origin message in the gpt-new
  channel followed through ingress, watcher admission, causal answer, and exact
  same-channel Discord API readback. Synthetic evidence cannot replace it.
- The existing Task Scheduler result-code presentation can show a nonzero prior
  result while a persistent task is currently running and process-owned
  readiness is healthy. That telemetry ambiguity was observed but not changed
  in this slice.
- This repair prevents heterogeneous daemons from taking outbound ownership
  while the gateway is healthy. Folding the fix into the canonical main branch
  remains necessary before every fallback daemon carries the same fail-closed
  policy.
