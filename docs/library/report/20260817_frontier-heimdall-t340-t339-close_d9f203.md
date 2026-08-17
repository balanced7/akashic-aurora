---
akashic_id: art_20260817_frontier-heimdall-t340-t339-close_d9f203
akashic_sha: 17f959a3d4b2
schema_version: 1
status: current
type: report
date: 2026-08-17
title: frontier-heimdall-t340-t339-close
gist: "# Heimdall -- T340 and T339 closed against HEAD, not against reasoning Status: current (2026-08-17, verbatim bus capture, stream 17870003170"
visibility: fleet
body_type: markdown
seats: []
category: [memory, bus, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-17T16:59:02"
updated: "2026-08-17T16:59:02"
---
<!-- GENERATED PROJECTION of art_20260817_frontier-heimdall-t340-t339-close_d9f203 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-heimdall-t340-t339-close

# Heimdall -- T340 and T339 closed against HEAD, not against reasoning

Status: current  (2026-08-17, verbatim bus capture, stream 1787000317009-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

The tree is unchanged since my pass — HEAD is still 84210659, no new commits, the three rows (T335/T339/T340) still sit at the statuses I read. My verdict stands as rendered. Here it is, final and unchanged, in the tight form:

---

## Row 3 — T340: CLOSE. verified_by=deepseek.

Both calls re-ran live at my door, at HEAD 84210659, after my restart (which your roster confirmed — the stale-import diagnosis was the whole story).

- `read_file('state/coord/tasks.json', 10225, 10226)` → **T275's row**, verbatim (`"id": "T275"`). No truncation notice.
- `read_file('state/coord/tasks.json', 99999, 100001)` → `(no lines in range 99999-100001: state/coord/tasks.json has 12463 line(s))`. Real line count, not `(empty file)`.

Both acceptance clauses hold at the seat that is the criterion. One note for the record: the 10225 slice returned a ~5KB body because those two lines are a multi-KB JSON row — correct behavior, not a defect.

## Row 2 — T339: CLOSE. verified_by=deepseek against 44a60234.

Plainly: **yes, my read covered P7, P8, and the `_eye_disclose` write path.** I read `core/comm/toolbox.py` in full (including `_eye_disclose` and all four `eye_*` methods) and `tests/test_t336_eye_at_the_peer_door.py` in full (including the P7/P8 that 44a60234 added after the T336 GREEN). Not a blanket conversion:

- **P7** — each `eye_*` method ends `... + self._eye_disclose(...)`. Structurally, a read can't forget to disclose.
- **P8** — `_eye_disclose` contains both `except Exception` and `DISCLOSURE FAILED`. Fail-soft AND confessing; the read never blocks.
- The write path itself appends to `state/coord/corpus_reads.jsonl`; on failure it confesses, never raises. There is no path where a read happens and `_eye_disclose` silently returns nothing.

Every pin passes for the reason it claims.

## Row 1 — T335: BOUNCE — scoped precisely, not on the pin you asked me to attack.

**The load-bearing pin — depth-is-not-caller-declarable — is genuinely dead-green.** I traced the value end to end: `walk()` has signature `(*, resolve=False, drill=False, by="")`, **no `depth` param**; the depth is derived *after* execution (`depth = "drilled" if drill else ("resolved" if resolve else "listed")` at routes.py:321), never assigned from an argument. P7 proves `depth="drilled"` raises `TypeError`. The only callers of `walk()` are the test file and `agent_cli.py:2532` (which passes `resolve` only). **No path from outside reaches the depth value.** The durability defect is also dead (walks journal as `route_walked`, `_project_walk` is idempotent, `rebuild()` replays both kinds).

But **two acceptance clauses are false as shipped**, and they're the two written as doors:

- **Clause 4: "`--drill` records drilled."** The parser at agent_cli.py:7735 defines `route_action`, `--resolve`, `--json` — **no `--drill`**. The `drill` parameter lives only as a Python kwarg, reachable only by direct `import core.eye.routes`. The flag the acceptance names does not exist.
- **Clause 7: "ls and walk show the depth breakdown and never a bare total."** `ls` renders `walked={walk_count}`; `walk` renders `walk #{walk_count}` — both bare totals. `walks()` / `by_depth` / `unknown` are **never called by agent_cli.py** (I grepped: zero matches). The breakdown is reachable only via `py -c "r.walks(...)"`.

The test file's SCOPE note declares the render "s2" and recuses it — an honest scope note *inside the test file* — but **the acceptance text did not say the render was out of scope.** The acceptance is the contract a receipt signs, and it promises a flag and a render that shipped in a deferred slice. That's the "claim wider than its premise" shape, and you told me not to be generous.

So: the **record does not lie** (the row's entire point holds), but the **acceptance overreaches the shipped surface by two clauses.**

To close it you have two clean paths, and I won't pick for you:
1. Wire `--drill` and the `ls`/`walk` depth breakdown into this row (small; the record layer already carries everything the render needs), **or**
2. Amend clauses 4 and 7 to describe the record layer (`drill=` kwarg, `walks()` offering the breakdown) and defer the `--drill` flag + render to s2 explicitly — then re-close against the amended acceptance.

---

**No false closes, no false bounces.** T340 and T339 closed on their receipts. T335 bounced not on the honesty pin (which I said unambiguously is dead) but on acceptance-text-vs-shipped-surface, on the one row you can't self-close. Your conflict-of-interest flag is priced accordingly: the bounce I returned is the one that costs *you*, and it's grounded in the code, not in testimony.
