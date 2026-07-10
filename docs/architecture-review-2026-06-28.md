# Akashic Aurora — Architecture & Documentation Review

Status: historical  (2026-07-09, P4: Dated review snapshot; ARCHITECTURE.md lives)

**Date:** 2026-06-28
**Method:** multi-agent review (29 agents): 8 subsystem maps → 7 review dimensions, each adversarially
verified against the actual code → themed feature ideation + judge → synthesis + completeness critic.
61 findings survived verification; 23 candidate features ranked. IDs (RC-/ARCH-/SEC-/OPS-/FC-/DOC-/TEST-)
are stable handles for drill-down.

---

## Verdict

The core design is genuinely strong — the Akasha/Aurora split (immutable Ledger+Store vs. regenerable
projections), the one-embedding-seam, the rule-of-three primitive factoring (Consolidator), the fail-fast
Redis connector. **The single recurring problem is "built + tested ≠ wired + retired."** Three flagship
guarantees are inert in deployment: peer-lock enforcement (the `AKASHIC_AGENT_ID` keystone is set nowhere),
the self-curating Codex (the curator file doesn't exist), and "everything consumes embeddings" (the
consolidation hot path uses a keyword-only Ranker). On top sits contained debt: three overlapping comm
stacks (one dead but still MCP-wired), ~12 stale pre-rename root docs that actively mislead, and an
unauthenticated Redis. Not rot — an unfinished strangler-fig plus a config gap. Most is mechanical to close.

## P0 — the one-line keystone

**Set `AKASHIC_AGENT_ID` at the door** (`RC-01`/`ARCH-05`). Both peer-lock vetoes
(`claude_pretooluse._check_write`, `pre_commit.check_staged`) fail open silently because the var is never set
in any runtime config. Add an `env` block to `.claude/settings.json` + the Cursor equivalent; make the hooks
fail-closed-with-a-teaching-error when a locked path is touched but no id is set; surface an unset-id warning
in `boot`/`status`. *Caveat: this arms the gate; agents still share one tree until C1 worktrees are provisioned.*

## Robustness fixes (P1 → P3)

- **P1 `RC-02`** — `Store.cas`/`update_atomic` (C3) has zero production callers; `ROUTER_ACTIVE`,
  `rebuild_track_chapter_list`, theme-membership still do non-atomic get→mutate→set → concurrent writes
  silently clobber. Route through `update_atomic` or native `sadd`/`zadd`.
- **P1 `RC-03`** — FileStore CAS is a false cross-process guarantee in the advertised Redis-down two-peer
  mode (stale in-memory snapshot + whole-file flush → last writer wins). OS file lock around re-load→modify→flush,
  or document CAS as single-process-only when Redis is down.
- **P1 `OPS-03`** — FileStore silently resets to empty on a corrupt load, then flushes empty over the
  recoverable file. Rename-aside + restore + `is_available()→False` + schema-version field.
- **P2 `RC-04`** — HybridStore serves stale reads after a swallowed Redis write; `check_drift` compares key
  *names* not *values* (same-key divergence reports in_sync, reconcile never fires). Degrade reads to File; diff values.
- **P2 `RC-05`** — `handoff` beats are silently downgraded to weight-1 `note` before validation (not in
  `BEAT_KINDS`). Add `handoff` at weight ≥4; `emit()` should error on unknown kinds, not silently rewrite.
- **P3** — non-atomic lock re-entrant refresh + fencing token validated by no gate (`RC-07`); EventIndex
  payload-before-index ordering (`RC-08`); chronicler persist loops swallow failures without the `health.bump`
  pattern (`RC-09`).

## Architecture cleanup ("built but not wired/retired")

- **HIGH `ARCH-02`** — kill the dead comm stack: `mcp_servers/agent_comm/server.py` imports 4 missing modules
  (→ `COMM_AVAILABLE=False`) yet is still a registered live MCP server; `fast_agent_comm.py` carries the exact
  bugs Bifrost fixed (port 6379, broadcast via load-balancing group, µs/ms XTRIM). `git rm` both.
- **HIGH `ARCH-01`** — finish the 4→1 comm consolidation: three incompatible "handoff" vocabularies. Document
  `core/signals` as durable-audit-only, make `core/comm` the single transport, add LEXICON Bus entry + a guardrail rule.
- **HIGH `ARCH-03`** — two incompatible `SessionRecovery` classes; `__init__.py` docstring advertises methods
  that exist on neither. Rename by genus, one canonical export, fix docstring, remove the allowlist suppression.
- **MEDIUM `ARCH-06`** — `fast_cache.py` bypasses Store, hardcodes `RAM_DISK='X:\'`, `os.makedirs` at import
  (latent crash). Delete or guard. **MEDIUM `ARCH-04`** — `check_boundaries` only scans `core/`; extend to
  scripts/mcp/root + hardcoded-Redis + persist-through-Store rules.

## Documentation

- **HIGH `DOC-01`** — archive ~12 stale pre-rename root docs (`AGENT_ONBOARDING.md` tells agents to import a
  nonexistent `agent_init`; `docs/INDEX.md` points to 5 missing files; `SYSTEMS_ARCHITECTURE.md` etc. describe
  the obsolete system). `git mv` to `_archive/`.
- **HIGH `DOC-02`** — `check_doc_freshness.py` only matches STATUS/INVENTORY/CHECKPOINT names → every harmful
  doc passes. Flip to an allowlist of permitted living root docs.
- **MEDIUM** — reconcile three conflicting "System N" numberings; fix `codex-plan.md`/`bifrost-plan.md` stamped
  "no code yet" while live; LEXICON marks shipped subsystems "planned" + has no Bus entry.

## Security & operability (trust + data-safety, not crypto)

- **HIGH `SEC-02`** — authenticate Redis: no `requirepass`/`--bind`, protected-mode off, on `0.0.0.0`. The
  whole substrate is exposed. Password + bind 127.0.0.1 + protected-mode; reconcile compose port vs canonical 16379.
- **HIGH `SEC-01` (+ completeness-critic escalation)** — the `bifrost_runner`→Gemini loop is a **capability**
  risk, not just prompt-injection: bus messages are unauthenticated (`frm` spoofable), injected verbatim into
  another agent's boot context, AND auto-answered by driving an authenticated logged-in browser session
  (`gemini_web.py`). An injected message can induce real authenticated actions and flow back to an agent that
  runs shell/git. Wrap injected mail in data delimiters + "information not commands"; reject `frm` ≠ connection
  identity; rate-limit + allow-list kinds before Ledger promotion; runner must refuse command-shaped/salient kinds.
- **HIGH `OPS-01`** — FileLedger/FileStore rewrite the entire file per append/write (twice per captured event).
  Make it genuinely append-mode. **HIGH `OPS-02`** — prove the backup restore (`_restore_redis` deletes db0
  before validating, regenerates stream IDs, zero round-trip test). Validate-before-delete, stage-then-swap,
  preserve IDs, test, schedule.
- **MEDIUM** — `print_recovery_report` hardcodes "Redis UNAVAILABLE" with no probe; BlobStore + the **embedding
  cache** (`embed:*`, no eviction) grow unbounded; every fail-open guard should emit a loud counter.

## Feature-completeness to finish

- **HIGH `FC-01`** — the Codex curator is unbuilt: `curate.py`/`faithfulness.py` don't exist; `Clusterer.propose()`
  has zero consumers. The "Resources = regenerable projections" thesis doesn't run. Mark Codex "schema-only" until built.
- **HIGH `FC-09`** — Embedder not wired into the consolidation Ranker (keyword-only despite the "one seam" claim).
  Pass `Ranker(relevance_fn=get_embedder().relevance)`.
- **HIGH `TEST-05`** — 755 LOC of crash-recovery code has zero dedicated tests (+ the duplicate-class ambiguity).
- **MEDIUM** — door-parity gaps (MCP lacks `lock`/`unlock`/`locks`; resolved blockers stay ACTIVE in boot
  because writes are argparse-only); the V6 consolidation re-theme pass; perspectives is data-only; orphaned `services/`.
- **Coherence (critic):** the curation spine is *duplicated* — `LearningStore` (`learn:`) vs `AgentMemory`
  (`mem:`), two `consolidate_*`, two consolidators writing the SAME `lessons.md`. Primitive factored once,
  callers forked — contradicts the rule-of-three the rest of the system honors.

## Recommended new features (themed, top 8, leverage-per-effort)

1. **CLI↔MCP parity contract test** — one-truth-two-doors from convention to enforced invariant. Ship first.
2. **Faithfulness critic in the Consolidator seam** — the seam is empty; a working metric
   (`chronicler._compute_metrics`) already exists and is discarded. Promote it.
3. **Curator: Clusters → Resources** (`core/codex/curate.py`) — the missing keystone; every primitive exists.
4. **Tag-governance agent door** — thin CLI+MCP over the built-but-unreachable CRDT loop.
5. **`capabilities()` self-describing door** — generated manifest of verbs/args/which-door.
6. **`--as-of` bitemporal time-travel story** — generalize `supersession.is_active` to `is_active_at`.
7. **Faithfulness ledger + drift alarm** — persist each chronicle run's faithfulness; honesty banner in boot/status.
8. **`watch` — live read-only observability TUI** — presence, inbox, held locks, firehose tail, health counters.

**Rejected:** Ledger hash-chain (crypto ceremony vs a non-existent adversary — local, single-owner,
git-backed); Task Board / Reputation / Conflict-Arbiter (stack on unbuilt features + unprovisioned concurrency).

## Known un-assessed (flagged by the completeness critic)

The MCP transport/trust boundary itself wasn't assessed (Cursor-owned, but it's a network door into the
substrate) — worth a dedicated pass. The theming-determinism subtlety (`ThemeDiscoverer._ok` cached at first
construction) is mitigated by V6c's flag-gating + default-keyword, but is a thesis-adjacent caveat to keep in view.
