# Source manifest — the origin archaeology, 2026-08-17

Status: current · Type: report · Author: claude (Vandor)

Written to Sol's closing bar, verbatim: *"These are the source classes we searched; these are
the surviving intervals; these are the holes; and further narrative coherence is no longer
being mistaken for coverage."*

This manifest is deliberately boring. It exists so a V2 origin narrative can state its coverage
instead of implying it.

---

## Planes searched, and what each yielded

| # | Source plane | Interval it covers | Status | What it yielded |
|---|---|---|---|---|
| 1 | `~/.local/share/opencode/opencode.db` (SQLite, ~85MB) | **2026-04-11 14:34 → 2026-06-27 17:25** | **RECOVERED** | 63 sessions, 9,394 messages, 38,053 parts. 754 operator turns; 169 predate Aurora's first event. Includes assistant **hidden reasoning**, which the operator never saw. |
| 2 | docker volume `redis_redis-master-data` → `dump.rdb` | snapshot at **2026-04-30 23:38** | **RECOVERED** | 178 surviving keys. Task-ledger, ADR-registry-with-supersession, outcome-indexed learning, patch tracking, `ai:personality` = "CodePilot". |
| 3 | same volume → `appendonlydir/appendonly.aof.1.incr.aof` (2.8MB) | **2026-04-15 05:29 → 2026-04-30 23:25**; embedded ISO stamps run **2026-04-13T02:45:06 → 2026-04-24T00:07:53** | **RECOVERED** | 1,993 commands. 203 keys ever written vs 178 surviving → **25 written-and-gone, 27 explicitly deleted.** Holds `agent_comm:stream` (Bifrost's full envelope + consumer groups), `msg:*`, `agents:active/heartbeat`, `fast:*`. |
| 4 | same volume → `appendonlydir.bak` | **2026-04-15 05:25** | **RECOVERED, EMPTY** | 88-byte base RDB, 0-byte incr. A rotation artifact; carries no history. |
| 5 | `redis_redis-replica1-data`, `replica2-data` | 2026-04-30 | **RECOVERED, REDUNDANT** | `dump.rdb` 98,528 bytes vs master's 98,574. Replica AOF is a *rebased* 98KB snapshot, not an independent log — **no additional history**. |
| 6 | live `akashic-redis` (:16379) | current | **LIVE** | `learn:agent:opencode_big_pickle` still present — a one-item list, `shared_memory_verification`. |
| 7 | `research/reviewed/origin-2026-04-13/` | 2026-04-13 | pre-existing | The previously canonized 18-session packet. **Superset now available via plane 1.** |
| 8 | `dockerized-ai/knowledge/knowledge.db` | — | **LOST** | An empty **directory**, not a file — Docker created the bind-mount path when the file was absent. The first SQLite knowledge base (`system`/`journey`/`learnings`/`agents`/`conversations`) is gone. It died silently and nothing noticed. |

## The holes — stated as holes, not smoothed over

1. **Before 2026-04-11 14:34 there is nothing, and this is now a bounded claim rather than a
   vague one.** The first ask in plane 1 is the first ask that exists on any plane searched.
   Whether Daniil used OpenCode before that session is **UNKNOWN** — it is not disproven, it is
   unsearched, because no earlier store has been found. JOURNEY's coda ("unrecoverable by
   construction") is disproven for 04-11 → 04-13 and remains untested for anything earlier.
2. **2026-04-24 → 2026-04-30 has RDB coverage but no command-level coverage.** The AOF's
   embedded stamps stop at 04-24 while the file was written until 04-30. Deletions in that
   window are therefore invisible: the discarded-futures count of 25 is a **floor, not a total.**
3. **2026-05-03 onward has no Redis-level coverage at all.** `docker-redis-data` (created
   2026-05-03) probed empty at depth 3.
4. **The assistant side of plane 1 is extracted but only partially analysed.** ~3.6M chars of
   replies and reasoning; four era-shards were fanned, of which 3 landed and coverage was
   uneven — `D_may_june` alone dropped 18 sessions including one of 286,821 chars. See
   `fan/MANIFEST.md` for exactly what each branch did and did not see.
5. **Operator-plane provenance is contaminated at an unmeasured rate.** At least one confirmed
   turn (2026-04-12 01:01:24, 5,493 chars) is assistant text pasted back by the operator, so it
   is a genuine user turn carrying agent-authored content. Two automated detectors failed in
   **both** directions — false positives where the assistant quoted the operator back, false
   negatives on the confirmed case. **The rate is unknown and must not be estimated from those
   runs.** This is T322's law (capture origin at the record) and the existing lesson
   `the_operator_voice_label_conflates_the_human_with_their_channel`, third sighting tonight.
6. **Not searched at all:** Claude Code's own transcript store (~526 sessions), the git history
   before the first push, `backup_wsl_migration/`, `sessions/`, `session_logs/`, and any
   browser/OS-level artifact. These are candidate planes, not known-empty ones.

## What a V2 may and may not claim

**MAY**: that a full multi-agent message envelope with consumer-group delivery semantics existed
on 2026-04-15 and was subsequently deleted; that the task-ledger, ADR-with-supersession, and
outcome-indexed-learning shapes all predate their named successors; that the fossil F1 decision
(`Single Redis`, rejected) has a surviving source document with its original rationale.

**MAY NOT**: that the discarded set is 25 (it is a floor); that the operator authored any
specific long pasted turn; that nothing predates 2026-04-11 (unsearched ≠ absent); or that
coverage of May–June is comparable to April (it is not).

## Known edits to the corpus (there is exactly one)

`operator-all.md`, one occurrence: a GitHub fine-grained credential pasted by the operator on
**2026-04-14 23:58:21**, replaced with a visible `<REDACTED-CREDENTIAL …>` marker. Redaction was
performed by PATTERN, never by passing the value as an argument, so no copy was planted in a
shell history or session transcript. `operator-pre-aurora.md` is unedited and complete.

It never reached the remote. The push gate blocked it while all four carrying commits were still
local, `origin` held zero files from this directory, and the commits were then rewritten so the
value is absent from history rather than merely removed by a later commit.

**The class, for V2:** archaeology re-publishes whatever the past leaked. Every recovered plane
predates the caution that governs the repo today. A plane must pass the secret gate at ADOPT
time; today the gate sits at PUSH, and that gap is why this was caught by luck of ordering
rather than by design.

## Retention risk, which is the finding nobody asked for

Planes 1, 2 and 3 — the three richest — are **not backed up anywhere**. Plane 1 lives in a
user-local AppData directory; planes 2 and 3 live in Docker volumes belonging to containers that
stopped four months ago and would be removed by a routine `docker volume prune`. Plane 8 is
already gone and demonstrates the failure mode. This project's prehistory has survived by luck
three times. A `prune` on a tidy afternoon ends it.
