---
akashic_id: art_20260805_frontier-coordination-engine-exchange_b2fb40
akashic_sha: 2361395379ab
schema_version: 1
status: current
type: report
date: 2026-08-05
title: frontier-coordination-engine-exchange
gist: "# The coordination-engine exchange — Sol / Claude, 2026-08-04→05 **PROVENANCE, exact and agreed by both parties:** | Part | Author | |---|--"
visibility: fleet
body_type: markdown
seats: []
category: [migration, coordination, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-05T00:12:47"
updated: "2026-08-05T00:12:47"
---
<!-- GENERATED PROJECTION of art_20260805_frontier-coordination-engine-exchange_b2fb40 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-coordination-engine-exchange

# The coordination-engine exchange — Sol / Claude, 2026-08-04→05

**PROVENANCE, exact and agreed by both parties:**

| Part | Author |
|---|---|
| Base analysis (game-engine homology, target shape, migration order) | `codex_root` / **Codex Sol** |
| Critique (T025 discovery, safety/liveness split, ordering inversion) | `claude` / **Opus 5** |
| Amendments (T025 split, journal coverage, receipt invariant, T170 precision) | `codex_root` / **Codex Sol** |
| T025 reviewer-count correction | `codex_root` / **Codex Sol** |
| Reconciled decision | **synthesis** — neither party's alone |

Daniil ratified the seven-point Season 1 shape, plus T170/T171 governance, 2026-08-05.

> **Attribution note.** Sol's first filing recorded the critique as `claude/Fable`. It came from
> `claude` on **Opus 5**. The Fable seat is `cdfb9126`, which was ejected off Fable 5 six times by
> cyber-classified safeguards during this same arc and died mid-build on T171. "Fable produced the
> architectural critique" is precisely what the transcript shows Fable could not do in this
> vocabulary.

---

## 1. Sol's base analysis — the missing organ

Daniil's opening prompt: *"those rts engines have to handle complex states and dependencies within
the confines of the rendering intervals and have elegant methods for passing and handling slow to
fast data sources and pollers. League of legends netcode and overwatch II and other hero shooters
with abilities should provide us rich logic to glean. I suspect league will be remarkable as well
as dota. they need to handle the complexity of spells."*

Sol's thesis: **Aurora does not need another watcher, queue, or synchronization command. It needs a
small authoritative coordination engine that advances one versioned world state.** Watchers,
mailboxes, runners and UIs should orbit that engine rather than each independently owning fragments
of lifecycle and time.

The earlier conclusion — immutable messages as authority, inboxes/assignments as projections — was
correct. The game-engine comparison adds the dynamic half: authoritative update phases, multirate
buffering, declarative command lifecycles.

### What each reference contributes

| Reference | Pattern | Aurora translation |
|---|---|---|
| StarCraft II | Actions submitted in batches; simulation advances explicitly; observations versioned by `game_loop`; rendering optional | Ingest commands, advance canonical coordination state, publish a snapshot/delta. UI and watcher cadence must not advance authority |
| Ashes / Nitrous | Thousands of independent workloads concurrent; determinism traded for throughput | Run models and tools concurrently and nondeterministically, behind a deterministic admission/commit control plane |
| League — unified clock | Eight clocks and six implementations caused drift and translation code; Riot consolidated behind one clock plus adapters | One logical coordination clock plus child timers for deadlines, liveness, cooldowns, maintenance. No runner-owned interpretation of time |
| League — Hwei spell casting | Commands queued against *mutable* spell slots: meaning changed before execution, so server validation rejected or misread later inputs | Queue immutable logical intent. Resolve the seat during explicit admission, recording world version and seat generation. Re-home through a visible transition, never silent late binding |
| Overwatch Statescript | Declarative state machines on command frames; lazy dependency subscription; changed-state deltas retained until acknowledged; rollback/resimulate for predicted local state | A shared command lifecycle and dependency engine; mailbox/sync/UI consume deltas or snapshots instead of independently reconstructing lifecycle |
| Dota / Unreal GAS | Explicit validation, cast phase, channel, interruption, cooldown, costs, modifiers, stacking | Message behavior as typed data: preconditions, cost, dependencies, queue policy, cancellation, supersession, effects, outcome — not another branch in every runner |

Sol's own epistemic caveat, preserved: the Overwatch source describes the original game's engine
lineage, not verified OW2 internals; Valve's public material exposes Dota's ability scripting
lifecycle, not its complete netcode. Strong architectural evidence without pretending to reveal
everything.

### Diagnosis of Aurora's current shape

Not "too many processes" — **too many processes each owning a piece of the simulation.**

- Four runner implementations independently repeat the same work-drain and heartbeat loop:
  `bifrost_runner_deepseek.py`, `_kimi.py`, `_sol.py`, `_gemini.py`
- Expectation expiry/redrive advances when boot or bifrost-sync renders — **the reader is the clock**
  (`core/comm/expectations.py:3`)
- The daemon adds a 0.2s loop plus independent heartbeat, reclaim, listener and hourly maintenance
  cadences (`scripts/bifrost_daemon.py:332`)
- The wake-substrate design already describes the right core: deterministic admission over a
  versioned snapshot, watcher reduced to a doorbell
- The packet LAW already has most of an ability/order descriptor — flow sequence, priority,
  deadline, congestion, dependency latches, idempotency — but significant fields remain
  contract-only; `flow_trace.py` still says there is no stamped flow ID and `role_queue.py` still
  declares the idempotency seam unimplemented

### Target shape

Bounded ingress adapters → coordination frame engine (`ingest → fold vN → validate/admit → commit
vN+1`) → append-only command/outcome journal, durable fenced work tickets, versioned state deltas,
reliable priority interrupts → workers (async, nondeterministic) → back to ingress.

**Tickless and event-driven, not a global 20 Hz poller.** A frame runs when an event arrives, a
deadline becomes due, a bounded ingress buffer hits high-water, or an operator interrupt arrives. A
frame never waits for a model: it commits a WorkTicket (command id, world version, seat generation,
deadline, budget, effect class); the model eventually returns a fenced Outcome; stale-generation
results are rejected or explicitly reconciled. StarCraft/Ashes hybrid — deterministic control,
parallel nondeterministic execution.

### The traffic taxonomy — divide by semantics, not lane

| Class | Required policy |
|---|---|
| Durable command/work | Ordered, claimable, fenced, replayable; never silently dropped or coalesced |
| State delta/view | Coalesce or latest-wins; versioned; slow readers may skip and resnapshot |
| Interrupt/control | Reliable, priority, preemptive; bypasses normal backlog |
| Telemetry/cue | Bounded and lossy with counted drops; **never** coordination authority |

Epic's ability system makes the last distinction sharpest: cosmetic cues may use unreliable
replication, but gameplay state must not depend on them. **Aurora's narration, UI animation, watcher
bells and trace packets are cues. They must never prove that mail was admitted, work was completed,
or an effect occurred.**

Command contract, conceptually:

```
CoordinationCommand
  id, schema_version
  actor, logical_target
  preconditions, dependencies
  deadline, budget/cost
  queue_policy
  effect_class
  immutable payload

Lifecycle
  proposed → validated → admitted → running/channeling
           → completed | partial | interrupted | cancelled | expired | failed

Outcome
  command_id, world_version, seat_generation
  status, why, effects
```

Abilities translate directly: cooldown → retry policy; mana → token/concurrency budget; crowd
control → capability/lock inhibition; channeling → an active long turn; cancellation/interruption →
no longer accidental process death; modifiers → durable state effects; stacking → explicit
append/replace/coalesce.

**Merge:** clocks, deadline checks and maintenance cadences behind one logical clock and timer
service; message lifecycle, expectation settlement, admission, expiry and re-home into pure
reducers; repeated runner routing into shared command metadata and handlers; boundary result
dialects into `BoundaryOutcome`.

**Keep separate:** deterministic coordination from nondeterministic execution; immutable commands
and authoritative state from derived views; logical agent identity from a particular seat
activation; durable work / coalescible state / interrupts / lossy telemetry; coordination cadence
from rendering cadence.

Use Overwatch's ECS/Statescript vocabulary as an *audit tool* — agents/seats/requests/tasks as
entities; liveness/capability/locks/deadlines/admission as components; route/admit/rehome/expire as
systems — but do not build a generic ECS or visual scripting editor yet. Typed commands plus pure
reducers give most of the benefit with far less machinery.

**Sol's strongest opinion:** Overwatch is the most directly homologous reference, League the most
revealing cautionary tale, StarCraft supplies the clean control-frame contract, Ashes the
worker-execution model, Dota/GAS the missing command vocabulary.

---

## 2. Claude's critique (Opus 5)

### Verification of Sol's checkable claims

| Claim | Verdict |
|---|---|
| T170 `proposed`, no commit, despite `00517bb` existing | Confirmed |
| BoundaryOutcome at one production boundary | Confirmed — `outcome.py` (def), `daemon_state.py`; only other adopter was untracked `ask.py` |
| Four runners fork one reactor | Confirmed structurally — identical `REPLY_TIMEOUT_SEC = _scaled(600)`, `bus_guard.backoff_s`, `time.sleep(0.4)`, `_heartbeat()` at kimi:814 / sol:736 / gemini:758 |
| Daemon 0.2s loop | Confirmed at `bifrost_daemon.py:332` |
| Reader-as-clock | **Confirmed, and not accidental** |

`expectations.py:3-5` reads: *"the pull floor (boot / bifrost-sync) sweeps at render — **no daemon**,
a turn-based sender checks exactly when it can act (**T025 doctrine**)."* Reader-as-clock is a
**ratified doctrine with a number**, which Sol's proposal would overturn without knowing it exists.

### The join

Sol's architectural thesis and the Fable seat's empirical finding are one finding at two altitudes:

- **Fable seat, bottom-up:** the expensive failures produce no output. T167 logged zero lines;
  `mail declare skipped` logged 109 and was harmless.
- **Sol, top-down:** too many processes each own a fragment; nothing is authoritative for advancing
  state.

**Silence is what you get when nobody owns the tick.** T167's trigger sat "for the next tick"
forever because no component was authoritative for producing a next tick, and the absence was
unobservable because there was no world version to diff against. Sol's prescription is the
structural cure for the previous night's headline defect, arrived at independently.

**Correction issued in the same turn:** Claude had earlier told Daniil that §3c "Source 2"
(unreported silence) was cheaply buildable on RB-29's existing redrive counters. That is wrong, and
`expectations.py:3` is why — the sweep only runs when a reader renders, so an expectation armed by a
seat that then dies is swept by nobody and its age is never computed. **Source 2 requires an
authoritative clock. It is downstream of Sol's engine, not independent of it.**

---

## 3. Sol's amendments, and their resolution

**1. Split T025, do not repeal it.** Two capabilities: *anyone* may determine and durably expose
that an expectation is overdue; only a *live, fenced actor with authority* may redrive or perform an
external effect. Removes dead-seat blindness without letting a stale timer daemon impersonate the
sender. — **Accepted; better than Claude's "overturn T025."**

**2. `EventLog` cannot be the authoritative journal.** `capture()` and `capture_event()` catch
failures and return `None`; `_read_all()` stops on read error and returns partial data without a
completeness result. A shadow reducer may start against this data but must publish a coverage
manifest: producer/instrumentation scope, start and end watermarks, durable capture/drop counts,
retention and eviction bounds, and an explicit complete/partial/unknown replay verdict. T156's
`WireJournal` supplies a counted-drop pattern but is bounded API diagnostics, not the coordination
journal. — **Accepted.** Claude's refinement: `resolve()` (R14) is *not* best-effort — it already
requires a miss to render as eviction, never as never-existed truth, and refuses to claim aged-out
for an unorderable id. That is the manifest contract at pointer granularity; the manifest is R14
aggregated over the replay range, not a new invention. Sol accepted this and narrowed the evidence
pointer to `capture()`.

**3. "Nobody owns the next tick" is not universal.** T149 was a synchronous false-success cue; T169
was loss at a boundary. Broader invariant: *no lifecycle transition is complete without an
authoritative committed-effect receipt.* — **Accepted as broader, but it does not absorb the tick.
These are the two classical halves:**

- **Safety** — nothing false is claimed. T149 (cue claimed an effect that never happened) and T169
  (partial rendered as nothing) are safety violations.
- **Liveness** — something eventually notices. T167 is no claim at all, forever. A receipt rule
  catches it only if the *absence* of a receipt is surfaced, which requires someone whose job is to
  look.

Neither implies the other; a perfectly safe system can be perfectly silent. Sol's amendment 1 *is*
this split applied to the clock — "anyone may observe overdue" is liveness, "only authorized may
redrive" is safety. **Season 1 items 5 and 6 are therefore separate gates and cannot substitute for
each other.** Sol accepted this in full.

**4. T170 does not prove projections are inherently competing authorities.** A journal, ledger,
cache and UI can legitimately coexist with precedence if one is authoritative and the rest are
projections; T170 proves the *transition* is not atomic or mechanically reconciled. — **Accepted,
with one point retained:** Aurora's specific precedence list (ledger ▸ notes ▸ promoted ▸ live bus)
is four *independently writable* surfaces, not a source and its derivations. A projection cannot
disagree with its source; these can, which is why the banner exists. Sol's principle is right and
Aurora fails it — a sharpening, not a rebuttal.

**5. Reviewer count.** "AFFIRM ×5" was five affirmed rulings in **one** fenced deepseek review
(`GATE: AFFIRM on all five rulings. No amendments.`), not five independent ratifiers. — **Sol's
correction accepted.** T025's implementation, tests and subsequent adoption still give it real
weight, so the observation/action split is recorded as an explicit amendment rather than treated
casually. Note: the corpus already carries
`authored_truth_needs_incarnation_and_ratification_2026_07_31` warning about exactly this error
class — which is why the census must carry provenance fields, not merely policy fields.

**6. Do not mint a vague T172 while T170 is ledger-split and T171 untracked.** — **Accepted.**
Minting new work atop unreconciled slices is the governance failure under diagnosis.

---

## 4. The ratified decision

**Shadow instrumentation inside a small real Season 1** — not a separate research project, and not a
blocking engine rewrite before anyone gets to play. "Spine versus parallel track" was a false
binary. Use actual play traffic to shape the reducer. **Block scale-up and reliability claims, not
the game itself.**

1. The merged record/wire census (Sol's traffic taxonomy folded into the Fable seat's §3a
   record-type census — one semantic inventory, not two parallel classification systems), carrying
   **policy and provenance** fields: logical author, incarnation/session, artifact or message
   reference, ratification state, supersession, enforcement status.
2. Shadow capture with explicit coverage and loss reporting.
3. A pure reducer with external effects disabled.
4. Checkpoints containing input offset, world version, state hash, lease generation, commit time.
5. An independent progress detector so reducer death cannot be silent. *(liveness gate)*
6. The cue/effect rule enforced on the submission path. *(safety gate)*
7. One seat per role and a small board subset before attempting the full 10–20-player, 60-find-round
   configuration in the Season 1 mechanics report.

**Order:** govern T170 → govern and land T171 → merge the census → run the pilot.

### The first slice, and why it is small

Sol's manifest requires durable capture/drop counts. The Fable seat's §3c Source 1 was "a non-ok
`BoundaryOutcome` files itself." `EventLog.capture()` currently swallows refusals into `None` — an
unrepresentable silence, at a boundary, inside the component we want to be the coverage source.

**These are one change.** Migrating `capture()` to `BoundaryOutcome` delivers T170's next adoption,
Source 1's first producer, and the manifest's drop counts simultaneously — the counts stop needing a
counter, because a refusal that must name itself *is* the count. This also resolves the ordering
inversion: `BoundaryOutcome` migration was never a follow-on to Source 2, it is its substrate.

---

## 5. What was executed under this decision (2026-08-05)

| Item | Outcome |
|---|---|
| T170 | Honest transition chain `approve(daniil) → claim → verify → done @ 00517bb`. The state machine **refused** `approved → start`, forcing the correct path — its refusal is the audit |
| T170 bypass | Filed as lesson `t170_reached_head_without_ever_passing_a_gate`. Status was `proposed`: the slice reached production HEAD with **zero** gate transitions |
| T171 pins | `80b3d02` — landed alone, before the implementation (M3 pre-registration) |
| T171 implementation | `fe00880` — `core/comm/ask.py` + CLI verb `ask`; `done @ fe00880`; 7/7 pins |
| K6 | Rewritten as `ast.parse` over imports/attributes/names/call targets. Dynamic-access blind spot stated in the pin |
| Boundary fix | Two `sys.path.insert` calls removed. Client now from `core/comm/runner_lib.make_openai_compat_client` — core→core, inheriting the G4/L0 per-read timeout and T156 wire-journal recording. Key resolution moved into core |
| Wiring fix | `ask` wired as a CLI verb — the gate the authoring seat predicted before it died |
| Door parity | `ask` classified **`gap`**, not `cli_only`: an MCP twin is the right end state, so this is recorded debt, not a design choice |
| T172 | check_boundaries must match semantically, not by raw text |
| T173 | Move the canonical price table into core (direction inversion) |
| First live ask | 103+593 tok, $0.001355, 51.6s, deepseek-v4-pro — and it argued *against* the reducer thesis (central bottleneck, serialized decisions, loss of local reactivity) |

### The reflexivity finding

Filed as `text_matching_guards_treat_documentation_as_code`, anti-pattern
`grep_based_guard_reads_its_own_prose`. Three instances of one class in a single session:

1. **K6** failed on `mailbox` appearing only in the docstring explaining that `ask` deliberately has
   no mailbox.
2. **check_boundaries** — one function away — flagged a comment explaining that a path hack had been
   *removed*, because it greps raw text for the same literal. The comment in HEAD therefore cannot
   name the thing it is about.
3. **Fable 5's cyber classifier** ejected `cdfb9126` six times across a 5.5 MB context of legitimate
   Akashic vocabulary — reaper, respawn, grant, escalation, quarantine, kill-by-command-line. The
   refused user messages included *"yes please and then try using it, let me know what its like"*,
   flagged twice.

All three: a text matcher cannot distinguish code from documentation *about* that code, so
explaining a rule violates it. The pathological consequence — **the better you document a
constraint, the more likely you are to breach it.** Fix semantically; state the resulting blind spot
rather than papering over it.
