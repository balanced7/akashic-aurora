# T034 Registry + Dial Consolidation -- deepseek design half (FENCED; persisted verbatim by claude)

Provenance: durable note ADR_0711034629_3586 (2026-07-11T03:46:29.120417); deepseek's write door still disabled, so it delivered
via the note lane (the twin-proof path proven in RB-23). Part 1 authored BLIND from the
raw brief + self-gathered evidence (its traces confirm); part 2 red-teams the approved
T034 sketch. Claude half: research/reviewed/claude-t034-registry-design-2026-07-11.md.

---

# T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half)

Status: blind-design (2026-07-11, fenced — written BEFORE reading claude's half)
Class: design
Inputs: raw brief + evidence scan only (env var grep, module constant scan, Redis control
key crawl, Store/Ledger/experiment/timescale/doctor prior art, mediation_membrane lesson,
live R15/RB-21/RB-5 threat receipts)

---

## PART 1: BLIND DESIGN

### 0. What problem are we actually solving?

Not "do we need a kernel." That question is a trap — it suggests a new architectural layer
when the evidence says three dial surfaces already exist and are UNCOORDINATED. The real
problem is:

A. **Discovery blindness:** you cannot list all tunable dials without grep. A new teammate
   cannot know what's configurable. Boot cannot render them. Doctor cannot audit them.

B. **Uncoordinated defaults:** the same logical value travels three paths — env var in
   runner.py, module constant in control.py, Redis key in liveness.py. If they drift
   (e.g. MAX_HOPS env default 6 but a hardcoded gate elsewhere uses 8), the drift is
   silent. No test asserts they agree.

C. **No flip audit:** setting AKASHIC_STOP_PROMISE=0 is a control-plane act (disabling a
   safety gate), but it leaves no durable record. Who flipped it? When? Why? If a mis-
   configured runner ships bad replies for 3 hours, there is no trail.

D. **Creep is unguarded:** a new FLOOR_CHARS or PROMISE_OPENERS list appears in a module
   with no registration. No lint, no test, no gate. The dial count grows forever.

The solution is NOT a kernel. It is a REGISTRY: one place where dials are DECLARED
(authoritative), one path where they are READ (consistency), one path where they are
WRITTEN (audited), and a guard that catches undeclared dials.

### 1. What unifies

A single `Dial` dataclass (or typed dict) declared ONCE per dial, in ONE file:

```python
@dataclass(frozen=True)
class Dial:
    key: str              # "content_floor.chars" — namespaced dotted path
    kind: str             # "int" | "float" | "str" | "bool" | "list[str]"
    default: Any          # the production default (source of truth)
    env: str | None       # AKASHIC_FLOOR_CHARS override (None = not env-configurable)
    desc: str             # one-line human explanation
    authority: str        # "operator" | "admin" | "code" — who can flip this at runtime
    introduced: str       # "RB-23" — which slice brought it, so we know why it exists
    deprecates: str | None # previous dial this one replaced
```

One file: `core/registry/dials.py`. ~50 dials declared. This is the SOURCE OF TRUTH for
every tunable in the system.

What this replaces:
- ~45 env var reads across 8 files → each becomes `dial("recall.cache_ttl")`
- ~15 module constants → each becomes `dial("runner.reply_timeout_sec")`
- ~8 Redis control keys → each becomes `dial("control.max_hops")` with the Redis key
  derived from the dial key (the Redis key is an implementation detail of the write path)

### 2. What stays code

These are NOT dials. They stay in code:

A. **Algorithmic constants that define correctness, not policy.** `PROMISE_OPENERS` and
   `STOP_VERBS` are grammar rules, not tunable policy. Changing them changes what the
   detector IS, not how it behaves. They stay as module constants with a comment citing
   the dial file ("these are NOT dials — see core/registry/dials.py for what IS").

B. **Derived constants.** `PULSE_GEN` is a runtime counter, not a setting. It stays
   in-process. Similarly, lock tokens, session IDs, cursor positions.

C. **Per-session overrides.** `AKASHIC_TIMEOUT_MULTIPLIER` (the drill shrink) is NOT
   a dial — it's a TEST HARNESS seam, not a configuration surface. It stays as env
   because drills set it in child process env before import. Making it a dial would
   imply it's safe to change at runtime (it's not — it's import-time by design).

D. **Secrets.** `DEEPSEEK_API_KEY` stays as env. The registry is for tunable policy;
   credentials are a ...[truncated]

---

# PART 2 REMAINDER (note ADR_0711045445_6705, 2026-07-11T04:54:45.581621 -- reconstructed after the tool-arg truncation; his runner relaunched with the RB-23 gate armed)

# T034 — Runtime Registry + Dial Consolidation (DeepSeek blind half, PART 2 — remainder)

Continuation from `t034-registry-design-deepseek` (research/reviewed/deepseek-t034-registry-design-2026-07-11.md),
which was truncated mid-sentence at section 2.D "Secrets." This note completes Part 1 from
that cut point and delivers ALL of Part 2 (the red-team of the approved sketch).

---

## PART 1 (continued from section 2.D)

### 2.D. Secrets (completed)

D. **Secrets.** `DEEPSEEK_API_KEY` stays as env. The registry is for tunable policy;
   credentials are a separate concern managed by the existing secret store / env layer.
   Mixing them into the registry would violate the principle that the registry is for
   tunable policy, not identity or access. A dial's `authority` field can reference
   "admin" or "operator" — secrets are owned by the deployment substrate, not the
   application control plane. The manifest explicitly rejects `kind: "secret"` at
   registration time (guard G-c).

### 2.E. Migration phases (strangler fig, each slice gated)

This is not a big-bang rewrite. Every existing env/constant/Redis-key continues to work
during migration. The registry wraps them, it doesn't delete them on day one.

**Phase 1 — Manifest exists, nothing reads it yet.**
- `core/registry/dials.py` committed with ~30 declared dials.
- `core/registry/resolver.py` committed: `dial(key) -> effective_value` with the three-layer
  resolution (env override → Store → manifest default).
- Guard G-a (undeclared-dial catch) installed in the ship gate but WARN-only.
- No consumer migrated. Rack diagram exists. Doctor can list dials.

**Phase 2 — One consumer family end-to-end.**
- Migrate the timeout/age family: `REPLY_TIMEOUT_SEC`, promoter stale-hours,
  proposed-stale days. These are low-risk, well-understood, and have no latency-critical
  read path.
- Prove the three-layer resolution live: an env override wins, a Store flip is visible
  within the cache TTL, and the default from the manifest is the fallback.
- Prove the flip audit: `agent_cli setting-flip` writes a Ledger event, which appears
  in the snapshot mirror.

**Phase 3 — Read-through for control keys.**
- `control.pause`, per-agent halt, nudge/steer flags become visible in the `settings`
  listing but their write paths KEEP existing semantics. No cache layer added to the
  hot path (barge-in latency is sacred). This is a read-through only — the dial
  resolver can READ from the Redis control key namespace, but the setter still goes
  through the existing mechanism.

**Phase 4 — Boot deviation line.**
- Boot currently lists its own env-derived settings. Replace with: "N dials off-default:
  ..." — one line, only when deviations exist. The full rack diagram is `agent_cli
  settings` (or `doctor --dials`).

**Phase 5 — Guard hardens.**
- G-a promoted from WARN to FAIL.
- New dials MUST land via manifest (guard enforces at ship time).
- Old constants migrate opportunistically when their module is next touched.

### 2.F. The guard (comprehensibility immune system extension)

Same pattern as the existing `REF_ALLOWLIST` guard (comprehensibility-immune-system
lesson). Four properties:

**G-a — Undeclared-dial catch.** Any `environ.get("AKASHIC_*")` or module-level
UPPERCASE constant in `core/` or `scripts/` that looks like a tunable (bool, int,
float, list literal) but is NOT in the manifest → FAIL. Dated allowlist for known
non-dials (grammar rules, derived constants per section 2.A-C above). Root-anchored
path matching so deployment/example paths don't false-positive.

**G-b — Bidirectional manifest rot.** A manifest entry whose `owner_module` no longer
reads that key → FAIL. And conversely, a module that reads a dial NOT in the manifest
→ FAIL. Both directions must hold, or the manifest is lying.

**G-c — No secrets in manifest.** Any manifest entry with `kind: "secret"` or whose
`env` name matches a known secret pattern (`*_API_KEY`, `*_TOKEN`, `*_SECRET`) → FAIL.
The registry is for policy ...[truncated]

---

# (t034-registry-design-deepseek-part3, note ADR_0711045708_9353)

# T034 remainder — part3 (continuation from part2 mid-G-c)

### 2.D. Secrets (completed)

...credentials are a separate concern managed by the existing secret store / env layer. Mixing them into the registry would violate the principle that the registry is for tunable policy, not identity or access. A dial's `authority` field can reference "admin" or "operator" — secrets are owned by the deployment substrate, not the application control plane. The manifest explicitly rejects `kind: "secret"` at registration time (guard G-c).

### 2.E. Migration phases (strangler fig)

**Phase 1 — Manifest exists, nothing reads it yet.** `core/registry/dials.py` committed with ~30 declared dials. `core/registry/resolver.py`: `dial(key) -> effective_value` with three-layer resolution. Guard G-a WARN-only. No consumer migrated. Rack diagram exists.

**Phase 2 — One consumer family end-to-end.** Migrate timeout/age family: REPLY_TIMEOUT_SEC, promoter stale-hours, proposed-stale days. Prove three-layer resolution live: env override wins, Store flip visible within cache TTL, manifest default is fallback. Prove flip audit: `agent_cli setting-flip` writes Ledger event → snapshot mirror.

**Phase 3 — Read-through for control keys.** `control.pause`, per-agent halt, nudge/steer flags visible in `settings` listing but write paths KEEP existing semantics. No cache layer on hot path.

**Phase 4 — Boot deviation line.** Replace boot's env-derived settings with one line: "N dials off-default: ..." — only when deviations exist. Full rack: `agent_cli settings` or `doctor --dials`.

**Phase 5 — Guard hardens.** G-a promoted WARN→FAIL. New dials MUST land via manifest. Old constants migrate opportunistically.


---

# (t034-registry-design-deepseek-part4, note ADR_0711045733_2119)

# T034 remainder — part4 (guard + failure modes)

### 2.F. The guard (comprehensibility immune system extension)

Same pattern as REF_ALLOWLIST. Four properties:

**G-a — Undeclared-dial catch.** Any `os.environ.get("AKASHIC_*")`, `os.getenv("AKASHIC_*")`, or direct `environ["AKASHIC_*"]` index in core/ or scripts/ that reads a tunable-shaped value NOT in the manifest → FAIL. Also covers module-level UPPERCASE constants that are bool/int/float/list literals looking like dials. Dated allowlist for known non-dials (grammar rules, derived constants per 2.A-C). Root-anchored path matching so deployment/example paths don't false-positive.

**G-b — Bidirectional manifest rot.** A manifest entry whose owner_module no longer reads that key → FAIL. Conversely, a module that reads a dial NOT in the manifest → FAIL. Both directions must hold.

**G-c — No secrets in manifest.** Any manifest entry with kind:"secret" or whose env name matches a known secret pattern (*_API_KEY, *_TOKEN, *_SECRET) → FAIL. The registry is for policy, not credentials.

**G-d — Expired exemptions.** Any allowlist entry for G-a/G-b older than 90 days without renewal → FAIL. Dated exemptions self-close (same pattern as REF_ALLOWLIST).

### 2.G. Failure modes

**FM1 — Manifest rot (dead entries).** Dial's owner module refactored away but manifest entry remains. → Caught by G-b (bidirectional; module-no-longer-reads direction catches it).

**FM2 — Flip lag (stale cache).** Read cache TTL means flip takes up to N seconds. → Document per-dial; keep TTL 5-30s. Latency-critical paths use read-through, no cache (Phase 3).

**FM3 — Silent Store degradation.** Store unreachable; flips not in effect; system runs on defaults unknowingly. → Boot line: "N flips NOT in effect (store unreachable)." Never silent — RB-5 doctrine.

**FM4 — Flip verb as code-review bypass.** Operator flips behavior dial instead of shipping code. → Required --reason + Ledger event + acl gate. Flips are LOUD. Graded dials: flip without regrade receipt is blocked (not warned).

**FM5 — Dial-count inflation.** Manifest grows without bound. → No count metric to Goodhart. Bar = owner + reason. Prefer deleting dials. Manifest should shrink over time.

**FM6 — Second config surface creep.** YAML/TOML/another-env-namespace later. → Guard G-a extended: ANY key-value config surface not mediated by settings layer → FAIL.


---

# (t034-registry-design-deepseek-part5, note ADR_0711045747_7413)

# T034 remainder — part5 (Part 2 red-team: 4 leaks)

## PART 2: RED-TEAM OF THE APPROVED T034 SKETCH

Red-teaming Claude's half (research/reviewed/claude-t034-registry-design-2026-07-11.md), read AFTER authoring Part 1 blind. Assuming the sketch is approved: what breaks?

### 4 LEAKS (information or control escapes the registry boundary)

**Leak 1 — Env reads outside the settings layer (G-a coverage gap).** The guard catches `environ.get("AKASHIC_*")` but what about `os.getenv("AKASHIC_*")`? What about `environ["AKASHIC_*"]` (direct index)? What about a helper wrapping environ.get? The guard must cover ALL three access patterns OR the resolver must be the ONLY import path for env — any direct `os.environ`/`os.getenv` in core/ or scripts/ is a violation regardless of key name. Otherwise a future dev adds `os.getenv("AKASHIC_NEW_FLAG")` and the guard smiles past it.

**Leak 2 — The timescale.scaled carve-out becomes a back door.** One exception ("timescale.scaled stays in env by design") becomes the template for every future exception. Six months later: eight carve-outs, each with plausible justification, registry covers 70%. Fix: the carve-out needs a DATED justification in the manifest (env_only:true with reason+review_date), and the guard counts env_only entries — flags if count grows without reconciliation.


---

# (t034-registry-design-deepseek-part6, note ADR_0711045755_9720)

# T034 remainder — part6 (leaks 3-4 + 2 drifts)

**Leak 3 — Defaults duplicated between manifest and code.** Manifest declares `default:15` for content_floor.chars. The module still has `FLOOR_CHARS=15`. Two sources of truth that CAN drift during migration. Mitigation: during Phases 2-5, `dial()` should ASSERT (import-time, dev/test) that manifest default EQUALS the still-present module constant. The assertion IS the bridge.

**Leak 4 — Settings verb leaks effective values to unprivileged callers.** If any dial reveals deployment topology (hostnames, thresholds implying scale, unreleased feature flags), the listing is an information leak. Fix: respect existing acl — quarantined agents see only dial names + their OWN agent-scoped values, not fleet-wide state. Manifest's authority field gates visibility: "operator" dials visible only to admin+.

### 2 DRIFTS (registry diverges from reality over time)

**Drift 1 — Module ownership rot (G-b false negatives).** G-b checks that owner_module still reads the dial. But "reads" is fuzzy — indirect reads through helpers, re-exports, dynamic key names. Static grep misses indirect reads and FALSE-FAILS on legitimate dials. Result: developers disable G-b as noisy → catches nothing. Fix: owner_module should be optional; if absent, G-b checks only "does ANY module read this?" (weaker but noiseless). Also support owner_module:["a","b"] for multi-consumer dials.

**Drift 2 — Flip verb becomes PREFERRED change mechanism.** If `setting-flip` is easier than a PR (always), operators use it for changes that SHOULD be code-reviewed. --reason becomes "perf tuning" for everything. Code defaults drift from production reality. Mitigation: flip verb emits Ledger event that Forge surfaces: "N flips this week, M without linked PR." Flip-to-PR ratio above threshold = drift alarm.


---

# (t034-registry-design-deepseek-part7, note ADR_0711045806_2536)

# T034 remainder — part7 (2 Goodharts + cut list + reconciliation) FINAL

### 2 GOODHARTS

**Goodhart 1 — "All dials in manifest" becomes the goal, not "fewer dials."** G-a enforces registration → incentive to REGISTER everything, never DELETE. Registering = compliant+easy; arguing something isn't a dial = friction. Manifest grows monotonically. Countermeasure: DELETION ritual as easy as registration — a `removed` field with removed_date+reason, kept for audit. Guard enforces no code reads a deleted dial. Ship gate reports manifest size trend; growth-only IS a finding.

**Goodhart 2 — Flip latency becomes the target, not correctness.** Someone measures "time from flip to effective" and optimizes. Cache TTL→0. Every dial() hits Store. Hot-path degrades. Second cache layer added → two caches with different TTLs, and drift between them IS the bug. Countermeasure: manifest declares max_reads_per_second per dial; resolver warns when a dial is on a hot path. Hot-path dials use local refresh thread (one reader, not N per request).

### CUT LIST (things to REMOVE from the sketch)

1. **graded_by pointer.** Couples registry to corpus/battery system still under active development. The pointer rots faster than dials. Fix: grading system declares which dials IT grades (grades_dials:[...] in corpus manifest), not vice versa. Registry shouldn't know consumers.

2. **Verbose default listing.** `settings` verb should show only DEVIATIONS by default. --all flag for full diagram. Otherwise zero-deviation healthy system prints 30 lines of noise → operator learns to ignore output.

3. **Control-key read-through (Phase 3).** Making control.pause visible in settings implies it's just another dial. It ISN'T — hard real-time signal with barge-in semantics. Keep in doctor --control with OWN semantics. Registry cross-references without absorbing.

4. **"No new daemon" claim.** G-d (expired exemptions) requires SOMETHING to check dates. Ship-time-only can lag weeks. A cron-like periodic check (or wake loop) MUST run daily. That IS a new daemon surface — name it honestly.

### RECONCILIATION

CONVERGE: both halves independently: one manifest, three-layer resolution, NOT a kernel, NOT YAML. Kill-switch carve-out + graded-dial problem both identified.
DIVERGE: I'm more skeptical of control-key absorption (cut #3) and graded_by coupling direction (cut #1). Claude folds control keys in; I'd keep separate with cross-ref. I add periodic cron for exemption expiry (cut #4); Claude relies on ship-time gates alone.

Resolution deferred to Daniel per fenced-dual protocol.
