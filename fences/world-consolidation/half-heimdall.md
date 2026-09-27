# House round, half: Heimdall (deepseek) — world consolidation

**Recovered 2026-09-27 from the bus** (msg `1790340685405-0`, spilled to
`blob:48b7fce43f902b49aa6207f6`). Verbatim and COMPLETE — 11,016 chars. A `capture --persist`
saved only 7,991 of them, because the message was spilled and the door showed a prefix; the full
body came from `bifrost-fetch --get`. Fidelity law: persist a peer's FULL report, never a prefix.

This answer existed ONLY on a bounded bus stream for two days. It was never filed into this fence.

---

REFUTE — Heimdall/deepseek. Verdict up front: consolidation survives, but NOT as Daniel's resource case frames it. I found no blocker to collapsing to one store, but I found a real argument that the thing being consolidated is different from the thing we think we're consolidating, and one defect class that genuinely only lives in a non-prod world. Ranked by how load-bearing each is.

=== FINDING 1 (most load-bearing): the 16381/alpha split was NOT a multi-world defect. It was a stale env var. ===

This is the finding that reframes the whole round, and it is sourced to Rill's own precise note, not my inference. `session_logs/ledger/events_dsh_agent_raw.jsonl:170` (his "PRECISE ROOT CAUSE" decision, superseding the symptom-level note at :168):

  "the RUNNING harness ... inherited a STALE AKASHIC_REPO=C:\Users\L5\AppData\Local\AkashicAurora\worktrees\reconcile-20260923 from its now-exited launcher shell — and that worktree's .aurora-world marker = alpha. loadLayeredEnv does NOT override an already-set process.env var, so the stale value WON over .env."

So the MCP door landed in "alpha" because a dead shell leaked `AKASHIC_REPO` pointing at a *throwaway reconcile worktree*, and that worktree happened to carry `.aurora-world = alpha`. The world system did not decide anything wrong; the world system resolved correctly from the inputs it was given, and the inputs were a stale env var. The worktree could have been a second prod checkout carrying `.aurora-world = prod` (or nothing) and the split would have been prod-vs-prod — invisible, or worse, a second writer to prod.

Mechanism, traced in source:
- `core/foundation/redis_connection.py:81-130` is the ONLY place the world actually binds. `_resolve_default_redis_endpoint()`: config default → `core.world.current()` upgrades `port` to the world's own → then env `REDIS_PORT` override is *refused if it points at another registered world* (`owner_of_port` guard). But `AKASHIC_REPO` is not `REDIS_PORT`; it's the repo-root override consumed by `core/paths.repo_root()` (`core/paths.py:100-113`), which `core/world.resolve()` uses as `root`. So a stale `AKASHIC_REPO` silently moves *which checkout* the world is derived from — and no rung in `redis_connection.py` ever sees it, because it never touches the port. The guard against cross-world writes is keyed to `REDIS_PORT`, and the actual attack vector that fired was `AKASHIC_REPO`. That is the gap.

Why this matters for YOUR sequencing question (brief: "is step 1 actually necessary"): the incident does not prove alpha has native work. It proves a worktree mis-identity wrote ~1 lesson + 1 heartbeat into whatever Redis that worktree was told to use. The "971 lessons in alpha / how much is misrouted prod" question is real, but the *mechanism* that generated the most recent misroute is env-var staleness, not world-tiering. Consolidating worlds does not remove that mechanism. A single-world fleet still has worktrees; a stale `AKASHIC_REPO` in one launcher still moves the world to UNKNOWN-or-derived; you'd have to fix binding explicitness (your step 3) regardless. So: step 3 (explicit binding, absence-of-declaration illegal) is NOT optional work you'd skip by consolidating — it is the actual fix, and it is orthogonal to whether one or three worlds exist.

=== FINDING 2 (load-bearing): beta and alpha are declarations, not deployments. The resource case for "three worlds" overstates what is actually running. ===

`docs/DEPLOY.md` §5 (the only deploy doc) declares exactly ONE Redis:

  docker run -d --name akashic-redis -p 16379:6379 redis:7

and gives the experiment path as `REDIS_DB=15` — a *logical db on the same instance*, not a second container. `config.py` and `core/world.py` declare beta (16380) / alpha (16381) with container names `akashic-redis-beta` / `akashic-redis-alpha`, but I searched the whole tree and found no compose file (`find docker-compose*.yml` → none), no deploy/linkerd instruction, no launcher that ever stands those containers up. The only script that mentions 16381 as a running thing is `scripts/local/restart_rill.ps1`, and it exists *to get OFF 16381*. The alpha/beta worlds are a registry of *possible* endpoints, and nothing in the documented run path creates them.

This inverts part of Daniel's resource framing. There are not three paid worlds each consuming tokens/store-hosting effort; there is one live store and a pair of dormant declarations that a stale env can light up. The operational cost we are trying to remove is smaller than "run both" suggests — which makes consolidation *cheaper to justify*, but it also means the thing we are consolidating is mostly *an attack surface that mis-binds*, not a tier that's serving a purpose. Removing the tiers removes the mis-bind target; that is the true saving, and it does not need the resource argument to stand.

=== FINDING 3 (the one I'm asked to name): a defect class that can ONLY be caught in a non-prod world, and the run where collapsing costs us something unrecoverable. ===

I found one class, but it is narrow and I want to be precise about its bounds rather than oversell it.

The defect class: **a write that is destructive to the store and silent-fails its own durability claim.** `core/world.py`'s docstring cites exactly this: "a db index or a key prefix — those collide on one FLUSHDB or one bad prefix." The whole reason worlds are physically separate Redis *instances* and not `REDIS_DB=15` is that a `FLUSHDB`/`FLUSHALL` or a bad key-prefix in a test run would collide with canonical data if they shared an instance. DEPLOY.md's `REDIS_DB=15` advice is, on this doctrine, already a landmine: it is the *precisely the isolation the world module says is insufficient*.

The run where consolidation is unrecoverable: a seat (or a test harness that escaped `_AISETUP_TEST_ISOLATED`, which `core/paths.py` documents as having happened — "the FILE half of test isolation was a no-op for two weeks, and live lessons bled into 'empty' test stores... every reader believed the store was isolated") executes a schema migration or a `FLUSH`-ish operation against the single store believing it is isolated, and it is not. With three stores, the blast radius is bounded to a discardable world and the mistake is *observable* (canonical prod keeps its key count, the delta tool you want would show it). With one store and no non-prod instance, the same mistake is a silent corruption of the only copy. The recovery cost is real only if the single store is the ONLY copy — i.e., if consolidation means "delete beta/alpha and their backups" rather than "collapse the *routing* but keep a cold discardable instance."

But — and this is the honest bound — this class is *about physical isolation of a destructive write*, not about a development tier that runs the fleet's own code against its own store. The fleet does not currently use beta/alpha as a staging area where risky migrations soak against a throwaway store; there is no evidence anything runs there but accidents. So the defense is real but the *current* three-world setup does not actually deliver it — beta/alpha are not being used as the discardable firewall the doctrine wants. My refutation therefore does not save the current three-world arrangement as-is; it says: **collapse the fleet's live store to one, but do not collapse the physical-isolation guarantee for destructive/test writes into `REDIS_DB=15` on that one instance.** Keep exactly one discardable instance (or db-15 on a *separate throwaway container*, never the prod container) as the firewall. That keeps the "only catchable off-prod" class caught, at the cost of one dormant container, not three worlds.

=== FINDING 4 (minor, correcting the brief): the MCP door is not a second writer mechanism; it is the CLI under capture, with a different inherited env. ===

`ai_setup_mcp.py:1-26` + `:65`: the MCP door "implements [verbs] by calling agent_cli's own cmd_* functions under a stdout capture... there is ONE source of truth." So the two doors that split were not two bindings; they were the SAME binding code, evaluated under two different process envs (one stale `AKASHIC_REPO`). This matters for Rill's assigned MECHANISM question: the fix is not to make the MCP door read the same port (it already uses the same resolver); the fix is to make *ingress* bind identity (which `launch_rill.ps1` already does per `restart_rill.ps1:3-12`) and to make absence-of-declaration illegal so a bare worktree can't resolve to "derived prod" by directory name.

=== SELF-REPORT (required) ===

Do I depend on a non-prod world? No — I (Heimdall/deepseek) have run against prod 16379 this whole session; my recall/notes are on canonical prod. Have I ever written to a non-prod world by accident? Not that I can find; but the honest version of your request is "have I ever checked," and the answer is: I have not verified my own write target independent of the resolver's word. That is exactly the gap the untracked `world_snapshot` instrument exists to close, and I'd want `status`/`learn` to print the resolved world (your step 3) before I'd swear to it.

=== RANKED SUMMARY of load-bearingness ===

1. [HIGH] Consolidation does not remove the defect that caused the incident (stale AKASHIC_REPO misbinding). Step 3 (explicit/loud binding, absence-of-declaration illegal) is mandatory regardless of world count. Your sequencing is right to put it before the collapse.
2. [HIGH] The resource case overstates live cost: beta/alpha are dormant declarations, not running tiers. Consolidation is right but the saving is attack-surface elimination, not "stop paying for two.
3. [MEDIUM] Keep ONE discardable physical-isolation instance for destructive/test writes; do not let consolidation slide test isolation into REDIS_DB=15 on the prod container (that is the exact anti-pattern core/world.py rejects). This is the only "only-catchable-off-prod" defect class I found, and it is real but bounded.
4. [LOW] One small correction to the brief: the MCP/CLI split was same-resolver-under-two-envs, not two independent binding mechanisms; this simplifies Rill's mechanism question.

Net: no blocker to consolidating the live fleet to one world. A clean "yes, consolidate" — with the caveat that the actual fix is explicit binding (your step 3, load-bearing), and the actual trap to avoid is folding the physical-isolation guarantee into a shared-instance db index. I did not find an argument that three live worlds are doing useful work we'd lose; I found that the third "world" was a shadow cast by a stale shell variable, and shadows are not production tiers.

This is a stated position on the merits for all four findings, not an abstention — but I want it read as "consolidate, in the order you said, with one discardable instance retained," not as manufactured dissent. If you want the raw evidence for any line, it's all read-only and re-derivable at the paths above.