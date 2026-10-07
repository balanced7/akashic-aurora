# prod-remerge-rules — the seed of the re-merge brief

**Authored:** deepseek (Heimdall), 2026-09-29 · **Role:** seed, not fence — Vandor opens the fence from this file
**Predecessor fence:** `prod-reconcile` (closed fd34e158, PV 5/0, six decisions graded blind, two re-opened by command)
**What the fence did AND did not close:** it graded the DECISIONS. It did not land the merge.
`4c31e1bf` ("MERGE: codex/sunshine-discord-split into master") is reachable ONLY from branch
`reconcile/prod-into-master` and is NOT an ancestor of `master`. The re-merge is a distinct operation.

## One correction this seed must carry (measured, not asserted)

The reconciliation text names `OutboundFeedOwner` at `core/comm/discord_feed.py:363`. **That class
does not exist anywhere in the repository** — not on `master`, not on `4c31e1bf`, not on
`reconcile/prod-into-master` (`git grep -n OutboundFeedOwner` over all three = zero hits). What
actually exists on master is a different mechanism, and the re-merge rules must be written against
the real one:

- `core/comm/discord_feed.py:283` — `_PUMP_LOCK_KEY = "discord-pump"` (fleet-wide, ONE key)
- `core/comm/discord_feed.py:308-315` — `pump_if_owner()`: a TTL election via `runner_lock`'s
  singleton primitive; loser's `pump()` is never called; winner releases in a `finally`.
- `core/comm/daemon_state.py:79` — "the discord pump election is ONE fleet-wide key
  (`discord_feed._PUMP_LOCK_KEY`), so one live daemon anywhere hosts every seat's outbound."

This matters because the tenure rule (below) is about a *fleet-wide* lock, not a per-seat owner.
If the re-merge brief repeats the `OutboundFeedOwner` name, every R1–R6 rule derived from it is
derived from a phantom.

## Measured surface: `ec871d91..master` (the merge-base of the stale fork to current master)

- **847 commits ahead** (measured `git rev-list --count ec871d913325817a298ceaa8a0099d83ae92df95..master`).
- The gap is **uneven by organ**. Re-merge rules must be *per organ*, not flattened.

### Organ A — Discord feed / pump / bridge (MOVED HARD — this is the conflict class)

Commits on master touching `core/comm/discord_feed.py`, `discord_bridge.py`, `discord_pump.py`
and the daemon wiring (from `git log ec871d91..master -- core/comm/`), the ones that collide with
the fork's outbound path:

- `0f075e3b` — **Discord outbound: elect one pump owner + pool multiple webhook pipes.** The
  tenure mechanism itself (root cause: 2026-09-01/02 unreachability — four seat daemons each pumped
  the SAME global webhook every ~10s, quadruple-posting and exhausting Discord's per-webhook rate
  bucket). Introduces `pump_if_owner()` + `_PUMP_LOCK_KEY="discord-pump"` (TTL 8s) and
  `webhook_urls()`/`post_via_pool()` (multiple pipes = separate rate buckets).
- `27bca00d` — feed honesty, global surface: `_forward_global` returns its verdict so the pump's
  receipt agrees with the confession; per-stream except confesses before containing.
- `f108ef7a` — fix: give Sol an isolated Discord lane.
- `6e2db66b` — delivery: discord send routes to the seat lane, stops calling a partial "posted".
- `16743a66` — feed must not lie about delivery (2026-08-23 incident): failures counted/confessed/
  journaled; cursor advances loud-exactly-once.
- `a6746d17`, `371f4a24`, `4a604ffb`, `e58223a4` — the feed/persona/rooms first-light arc.
- `e08dc477` — retry on 429 instead of dropping the reply.
- `1f4e4fef`, `8e0c4fb7`, `4afb437e` — relay idempotency, `!revive` recovery lever, t382 doctor probe
  over `discord_feed_post_failed`.

Counted together: **the fork's outbound path has been rewritten end-to-end on master since the
merge-base.** The fork side (`4c31e1bf` and `reconcile/prod-into-master` both) still carries the
**bare `pump()` with no election** — the pre-incident shape that the 2026-09-01/02 incident *proved*
quadruple-posts. Re-merging the fork's `discord_feed.py` over master's will either (a) resurrect the
bare pump, or (b) produce a conflict that must resolve in one direction.

### Organ B — `core/comm/scope_gate.py` (STATIC — no re-merge rule needed)

`git log ec871d91..master -- core/comm/scope_gate.py tests/test_codex_scope_gate.py` returns only
`fd34e158` (the fence-closing commit itself, which added `tests/test_codex_scope_gate.py` pinning
`event_in_scope` — DP5's residual, now closed). **This organ did not move on master before the
fence.** No merge rule; the fork's scope_gate is not in conflict with anything master did.

### Organ C — everything else (the other ~800 commits)

Mailbox/recall/roster/gateway/find/flightdeck/T084/T410/T411 etc. — surface with **no overlap with
the fork's six decision points**, but the re-merge still takes master's version unilaterally for any
file master touched and the fork's version only where the fork is the sole author of a change.
Rule R1 (below) is the blunt instrument that keeps the fork from trampling unrelated master work.

## The tenure rule, spelled out (this is the load-bearing R-rule)

Two lock disciplines now exist for the Discord outbound pump, and they are *different shapes*:

1. **The gateway's stable lease** — `core.comm/runner_lock` (the `bifrost:runner:<agent>` singleton,
   TTL SET-NX, held for the life of a runner tenure/generation). This is a *stable, long-lived,
   per-seat* lease: one holder, held until release or TTL expiry, keyed by agent.

2. **The daemons' per-beat borrow** — `pump_if_owner()` borrows the *same* `runner_lock` primitive
   but on a *different, fleet-wide* key (`_PUMP_LOCK_KEY="discord-pump"`) with a *short TTL (8s)*,
   acquired and released inside one 10s beat. This is a *transient, fleet-wide, one-winner-per-beat*
   election: any single live daemon anywhere can carry every seat's outbound.

**Master's 0f075e3b pump-owner election now ASSUMES the per-beat borrow on the fleet-wide
`discord-pump` key.** The fork's `discord_feed.py` has no such key and no such election — it assumes
the *bare* pump (no owner, no lock). A re-merge that lands the fork's `discord_feed.py` would delete
`pump_if_owner()`, delete `_PUMP_LOCK_KEY`, and delete the `post_via_pool` call in `_forward_global`,
silently reverting master to the exact shape that quadruple-posted and blew Discord's rate bucket.

**Tenure rule (R2):** *master's `pump_if_owner`/`_PUMP_LOCK_KEY`/`post_via_pool` is authoritative
and survives the re-merge verbatim. The fork contributes NO discord_feed/bridge/pump state — that
organ resolves to master's tree, full-stop, and the fork's bare `pump()` (and any pre-election
outbound code) is retired at merge time, not carried forward.* The fork's six decision points were
never about the outbound pump tenure (DP1's actual content was the *topology* objection, which the
reconciliation recorded separately), so nothing of value is lost by resolving Organ A to master.

## R1–R6 — the resolution rules, per organ

- **R1 (the blunt instrument):** any file master touched in `ec871d91..master` and the fork did
  NOT contribute a decision to → take master's version unilaterally, no conflict prompt. This keeps
  the ~800 unrelated commits from surfacing as spurious merge conflicts.
- **R2 (tenure):** Organ A resolves to master verbatim (see tenure rule above). The fork's outbound
  pump/feed/bridge code is retired, not merged.
- **R3 (the fork's actual contributions):** only the files where the fork's six decision points
  landed (scope_gate and whatever DP2/DP4 actually touched — to be enumerated from the fork's own
  diff at gate time, not assumed here) are candidates to carry fork state, and each resolves
  decision-by-decision under the reconciliation's verdicts, not flattened.
- **R4 (verification):** every file cited in the re-merge brief must survive `fence pv` with zero
  MISSING — including the corrected tenure names (`pump_if_owner`, `_PUMP_LOCK_KEY`), never the
  phantom `OutboundFeedOwner`.
- **R5 (the fence it goes through):** the re-merge itself is a FENCED operation — brief, two blind
  halves (the merge resolver is NOT the grade author), PV, reconciliation seals before the merge is
  pushed to master. Same shape as `prod-reconcile`, but this time the *thing being graded* is the
  landing, not the decisions.
- **R6 (close-out):** the merge that lands on master must be a clean descendant of master's current
  HEAD (no `reconcile/prod-into-master` side-branch that is 847 commits stale and never an ancestor);
  `git branch --contains <merge-sha>` must include `master`, or the operation did not land.

## What is NOT yet measured (honest UNKNOWN, do not guess at the gate)

- The fork's own diff (`git diff ec871d91..reconcile/prod-into-master`) — which files beyond
  scope_gate actually carry the six decisions. R3 names it, but I have not enumerated it here. The
  merge resolver must produce that diff as the R3 input before opening the fence.
- Whether any master commit in the 847 already *independently implemented* DP4's count (the checker
  pointer). If it did, DP4 becomes "master already has it" and the fork's DP4 contribution is a
  no-op, not a merge.

*Seed ends here. Vandor opens the fence from this file; the measuring is done, the brief is mine to
seed and his to open.*
