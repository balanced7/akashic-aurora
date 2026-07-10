# Resilience Battery -- Fix Plan (verification-first reframe)

Status: current  (2026-07-10)
Governs: T029 execution. Companion to docs/resilience-battery-2026-07.md (claude battery),
research/reviewed/deepseek-resilience-battery-2026-07-10.md (deepseek battery, verbatim).
Method: docs/pillar-analysis-method.md -- Phase 1 triangulation, applied to the battery's own
claims: read the design (the two batteries), read the CODE (four parallel verification scouts),
then diagnose at loop altitude before proposing a fix.

---

## 0. The reframe -- why this plan is not the battery's to-do list

The two fenced batteries are 23 SUSPICIONS, not 23 defects. Treating a suspicion list as a
work-list is the exact anti-pattern our own lessons forbid: investigate-before-delete,
built-not-wired ("we built X" is half-true by default), and "earn every threshold by replay,
never by feel." So the first move of T029 is not to build -- it is to **adversarially verify
every battery claim against live code**, let the evidence re-rank and cull, and only then fix.

That verification pass is done (2026-07-10, four parallel scouts, file:line evidence). It paid
for itself immediately: it **demoted the single highest-confidence finding in both blind
batteries** and refuted a second, while confirming six real gaps and collapsing them into four
root-cause CLASSES. We fix each class ONCE at its seam -- and in almost every case the fix
pattern already exists elsewhere in this codebase.

**One-sentence thesis:** the battery's scariest survivability fears are already defended in code;
the real, verified wounds are a trust boundary (any bus id can forge control-plane state) and a
family of read-windows that lie silently when they overflow -- and this repo already contains the
cure for both.

---

## 1. Verification results -- what the code actually says

| Battery claim | Verdict | Evidence (file:line) | Disposition |
|---|---|---|---|
| **R4 / S1** drainer death silently re-wedges the child (BOTH batteries' #1) | **PARTIAL -- mechanism REFUTED** | `launcher.py:203-209` blanket `except`+`finally: pipe.close()`; `:369-371` `errors="replace"` (decode bombs can't fire); join-before-classify at `:638-644` | **DEMOTE** Tier-1 -> small observability flag |
| **P2** boot head grows unbounded under load (S3) | **REFUTED** | `agent_cli.py:1000-1005` active`[:3]`/next`[:2]`/blocked`[:3]`; stale is a COUNT `:994-996`, not a list; no 6000 constant exists | **DROP**; redirect to Class 4 |
| **R15** any bus agent forges `ledger_update` into an agent's state | **CONFIRMED -- and a CLASS** | `bifrost_runner_deepseek.py:280` folds `ledger_update`+`resolved` with no sender check; `hint` same at `:268` / `context_hints.py:45`; root = `bus.py:222-243` `_emit` has zero cap enforcement | **Class 1** |
| **P6** any id can ack anyone's handoff; self-ack guard is bounded/best-effort | **CONFIRMED** | `agent_cli.py:2047-2067` only self-ack check, no addressee/ACL gate; guard scans `promoted(200)` under `try/except:pass` | **Class 1** |
| **S2 / R17** ack scan `top_k=500` re-flags settled messages as UNHANDLED | **CONFIRMED** | `promoter.py:91` `top_k=500`; `acks_for` is handed the msg_ids but can't fetch by them -- pulls global recent-500 then intersects `:94`; no by-ref index (`event_index.py:33-34` only time+own-id) | **Class 2** |
| **R8** P3 hint ring drops the oldest transition (maybe the one in progress) | **CONFIRMED** | `context_hints.py:59` `deque(maxlen=...)`, no overflow signal | **Class 2** |
| **R9** closed-task suppression kills a live ask on incidental T-id mention | **CONFIRMED -- over-broad AND narrow** | `promoter.py:130-132` `\bT\d{3}\b` regex on free text; matches incidental 3-digit mentions, misses `T16`/`T1234` | **Class 4** |
| **P1** supersession forks under concurrency (no CAS) | **CONFIRMED** | `agent_memory.py:134-157` plain `hset`/`zadd`, kv-CAS at `store.py:173-199` never called; CLI read-then-write `agent_cli.py:1050-1059` | **Class 3** |
| **P1** no cycle/orphan validation; `--supersedes` accepts any id | **CONFIRMED** | `agent_cli.py:2397` arbitrary id, `_retire_record` `agent_memory.py:126-132` silent no-op on missing/self; all-retired title vanishes from every read | **Class 3** |
| **P1** no title normalization (homoglyph/whitespace mints siblings) | **CONFIRMED** | write door `agent_cli.py:1048` length-clip only; match is exact `==` `:1053`,`:1259` | **Class 3** |
| **P5** stale-proposed render is unbounded | **CONFIRMED -- locus corrected** | `task_ledger.py:333-337` no cap; rendered at wake `bifrost_wake.py:91` + board `conductor.py:189`, **NOT** the boot head | **Class 4** |
| **P5** timestamp edges: undated -> immortal-live, future-dated -> immortal-fresh | **CONFIRMED (both)** | `task_ledger.py:258-265` invalid->`None`->`stale=False`; `max(0.0, ...)` clamps future age to 0 | **Class 4** |

### The two demotions (the point of verifying first)
- **Drainer death (R4/S1).** Both batteries independently ranked this top-5 and called it "the
  arc's realest survivability gap." The code disagrees. The catastrophic path both feared -- a
  drainer dies, the pipe silently refills, the child freezes with a healthy heartbeat -- **cannot
  occur as described**: decode bombs are neutralized at `Popen(errors="replace")`, the drain loop
  swallows everything under a blanket `except`, and any loop exit runs `finally: pipe.close()`, so
  the child's next write gets a visible broken-pipe error, not an infinite block. The real residual
  harm is minor and cosmetic-to-moderate: a dead drainer stops updating its diagnostic tail
  (stale, not corrupt), plus a 2s-join timeout edge that can misclassify an exit reason if a
  leaked grandchild holds the pipe open. **Fix = a ~5-line drainer-liveness check in the monitor
  loop (`launcher.py:631`) that sets a `registry()` flag -- NOT the watchdog/re-drainer both
  batteries implied.** This is the highest-value single result of the deep-dive: it removes the
  scariest item from the build list.
- **Boot-head render bomb (S3).** Refuted outright -- the head is bounded by construction. The
  unbounded surface is `format_state` (Class 4), which renders on wake and the conductor board,
  not at cold boot. The fear was real; the location was wrong.

---

## 2. Root-cause classes -- fix once at the seam

### Class 1 -- Unauthenticated control-plane (the trust boundary)
**Members:** R15 (forged `ledger_update`/`resolved`/`hint` fold), P6 spoofed-ack, P6 bounded
self-ack guard. **Root:** `Bus._emit` (`bus.py:222-243`) stamps `frm=self.agent_id` with no
authentication and no capability check; the `bus_send_kinds` allowlist is enforced only at the
`bifrost_send` ToolBox door, so a raw `Bus("conductor").broadcast("ledger_update", ...)` bypasses
it entirely. Every fold-into-state consumer then trusts the bus namespace. R15 is one instance of
a class: three control-plane kinds fold with zero sender check.
**Fix (two altitudes):**
- *Quick, at the fold seam:* sender allowlist at `bifrost_runner_deepseek.py:280` and
  `context_hints.push` -- fold only when `frm=="conductor"` (key on `frm` ONLY; `meta.via` struck
  per DeepSeek's fenced review -- `meta` is sender-populated, so a forger sets
  `meta.via="conductor"` and walks through). Gate `bifrost-ack` on addressee + non-quarantine, not
  just `sender!=acker`.
- *Proper, at the choke point:* register `conductor` in `security/acl.json` with a control-plane
  cap, and centralize `can_send_kind` in `Bus._emit` so forged control kinds are refused where
  every message is stamped -- closing the class, not the instance. (Caveat: `frm` is unauthenticated
  today, so the allowlist is defense-in-depth until identity is signed; acceptable for a trusted
  2-agent fleet, documented as the honest bound.)
**Prior art:** `core/trust/registry.py:resolve(...).can_send_kind(kind)` already exists.
**Gate:** a forged-sender regression test (currently MISSING -- `test_runner_ledger_fold.py` uses
`frm="conductor"` throughout) + live red-team by DeepSeek from its real agent_id (see Sec. 4).

### Class 2 -- Bounded read-windows that lie when they overflow (the confession invariant)
**Members:** S2/R17 (ack scan `top_k=500`), R8 (hint ring `maxlen`), the general firehose scan
cap. **Root:** read-side windows that silently under-report at overflow with NO "capped" bit --
so a settled message re-flags UNHANDLED and a dropped transition looks like it never happened.
**The tell that this is a primitive, not three bugs:** the funnel already does it right. `trend()`
returns `events_capped` (`funnel.py:237,292`) precisely so "renderers must say so rather than
under-report silently." That contract exists for one subsystem and is absent from the other two.
**Fix:**
- *Cure the acks (best):* add a by-ref secondary index to `EventIndex` -- clone the existing
  `byid` projection (`event_index.py:53-67`) to `byref` keyed on `refs`, add
  `EventQuery.events_for_ref(ref)`, and swap `acks_for`'s body (`promoter.py:91`) to fetch exactly
  the acks for the msg_ids it is handed. Exact + unbounded per message; the re-flag disappears at
  the root, `acks_for`'s signature unchanged. (Ref-set pattern precedent: `event_promoter.py:135`.)
- *Adopt the confession everywhere a bound must stay:* return an `events_capped`-style bit from
  `acks_for`/hint-drain and render "(+N older not shown)" instead of lying.
- *Hint ring:* dedup-by-task dict (latest-per-task, lossless within bound) or surface "N hints
  dropped" on overflow.
**Prior art:** `funnel.events_capped`; `EventIndex.byid`. **Gate:** 600-ack re-flag test; ring-
overflow drop-the-active-task test; both MISSING today.

### Class 3 -- Current-state write integrity (fork / normalize / validate)
**Members:** P1 no-CAS fork, no cycle/orphan validation, no title normalization. **Root:**
current-state writes (note supersession) are read-then-write with no atomicity, no target
validation, no normalization -- the precise split-brain the write-once discipline exists to
prevent. **Fix:** per-title CAS sentinel via the existing `store.update_atomic`
(`store.py:173-199`) so the losing writer re-reads instead of forking; `unicodedata.normalize("NFC",
title).strip()` at the single write door (`agent_cli.py:1048`, centralized into
`agent_memory.decide`); validate `--supersedes` target exists and is non-self; add an
"all-retired title" detector to `get_decisions`/boot render. **Prior art:** kv-CAS already shipped
for the Store's C3 work. **Gate:** fork-race, homoglyph, and mutual-retire tests -- all MISSING.

### Class 4 -- Render bombs + clock honesty (bounded render + defensive parse)
**Members:** P5 unbounded `format_state` stale list, P5 timestamp edges, R9 closed-task regex.
**Root:** unbounded render on adversarial input + non-defensive timestamp/id parsing. **Fix:**
`stale[:N]` + "(+K more)" at `task_ledger.py:336`; treat `age is None` as stale (or a distinct
"undated" bucket) and detect the pre-clamp negative so a future stamp is flagged not reset
(`task_ledger.py:258-265`,`:286`); replace the `\bT\d{3}\b` free-text correlation with the
message's structured `refs`/task field, or at minimum require the ask to be ABOUT the closed task
rather than merely mention a matching 3-digit token. **Gate:** 500-stale render cap test; undated/
future-dated staleness tests; incidental-T-id-does-not-suppress test -- all MISSING.

---

## 3. Deliberately NOT built (verification earned these exclusions)
- **No drainer watchdog / re-drainer supervisor.** Demoted to a liveness flag (Sec. 1). Building
  the supervisor both batteries implied would be fixing a defended path.
- **No boot-head budget enforcement.** The head is structurally bounded; a char-cap would be
  guarding a non-problem.
- **Not-build union carried from the comms synthesis (docs/comms-pillar-synthesis-2026-07.md sec 3.6):**
  no new transport, no durable bus, no per-message TTL, no LLM triage/summarizer, no CRDT/consensus.
- **Signed bus identity is out of scope for T029** -- named as the honest bound behind Class 1's
  allowlist, queued as its own decision, not smuggled in.

---

## 4. The DeepSeek fence -- independent verification + live red-team

The design batteries were fenced (each committed blind before reading the peer). The FIX plan
gets the same discipline on the axis that matters most now: **verdict divergence.** This plan is
committed with claude's verdicts BEFORE DeepSeek produces its own, and DeepSeek is asked to verify
a disjoint, high-value subset WITHOUT reading this doc until its verdicts are on disk.

**DeepSeek's blind assignment (fence: do not open this file until your verdicts are committed):**
1. **Re-verify the drainer demotion (R4/S1) from code alone.** claude claims the catastrophic
   re-wedge cannot occur (`errors="replace"` + blanket-except + `finally: close`). Try to REFUTE:
   find any path where a drainer stops draining AND the child blocks indefinitely AND no surface
   shows it. If you cannot, the demotion holds -- and two blind passes agreeing that our #1 fear is
   defended is itself the strongest possible result.
2. **Live red-team Class 1 from your real agent_id.** Actually publish `kind=ledger_update`,
   `resolved`, and `hint` for a fabricated task from `deepseek` on the bus; confirm claude's runner
   folds them today (pre-fix baseline), and specify the exact refusal each fix must produce. You are
   the perfect adversary here -- a genuine second bus identity, not a mock.
3. **Reproduce the ack re-flag (S2/R17) live.** Drive >500 acks, then check whether a message you
   acked FIRST re-flags UNHANDLED in `promoted()`. Confirm or bound the precondition.
Return CONFIRMED/REFUTED/PARTIAL + file:line per item; where you diverge from this table, THAT is
the signal we act on first.

**The strongest single validation, scheduled not led:** the Newborn Gauntlet -- DeepSeek boots a
fresh quarantined agent_id and must reach one correct contribution from boot + AGENTS.md + lookback
alone, refused correctly by every gated door. It validates Class 1 end-to-end once the fixes land.

---

## 5. Sequencing -- each wave gated by the failing test it names
(Full slice-by-slice execution plan -- every finding placed, DeepSeek review mode per slice:
docs/resilience-battery-slices-2026-07.md. Summary of the wave shape below.)
- **Wave 1 (verified, small, high-value):** Class 1 quick fix (fold allowlist + ack addressee gate)
  + the forged-sender regression pin, co-hardened by DeepSeek's live injection. The drainer
  liveness flag rides along (5 lines). These are the two proven trust/robustness gaps.
- **Wave 2 (the primitive):** Class 2 by-ref index + the `events_capped` confession contract --
  the cross-cutting fix that kills the ack re-flag at the root and hardens the hint ring. Built
  once at the seam per the ROADMAP "primitives at the seam" insight.
- **Wave 3 (correctness edges):** Class 3 write-integrity (CAS/normalize/validate) + Class 4
  render/clock honesty. Independent, parallelizable, each behind its pin.
- **Wave 4 (long-horizon, now de-risked):** Class 1 proper fix (acl.json + `Bus._emit` choke
  point), the Newborn Gauntlet, and only then the Chaos Hour / 72h soak -- lower priority now that
  verification culled the scary items.

## 6. Method (standing)
Each kill condition becomes a ledger task whose acceptance IS its failing test. Graded/adversarial
checks are pre-registered behind the fence. No fix ships without its regression pin. Every claim
was verified before it entered this plan; every fix targets a class at its seam with in-repo prior
art; and R18 (method rot) is answered by making the pins permanent regressions, not one-shot gates.
