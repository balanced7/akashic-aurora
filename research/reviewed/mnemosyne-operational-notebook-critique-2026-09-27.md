# Critique — Mnemosyne operational notebook (Sergey Nikitenko)

**Reviewed 2026-09-27 by claude (Aurora), at Daniel's request.** Subject: Sergey's
`Operational notebook — Operator Console`, the local-only OBS notebook covering operational
sessions 1–4, WORK-001, the Phase 3 vs Phase 8 guarantee audit, and Test Set #2.

**Stated limit first:** the copy I received was truncated (`... (168 KB left)`) mid Test Set #2's
DeepSeek↔Gemini comparison table. Everything below is drawn from what I could read. The A/B result
itself, and anything after it, I have not seen — so any claim I make about the model comparison is
about its *setup*, not its findings.

**Register.** The last review (2026-09-25) deliberately returned probes rather than grades, because
the repo was hours old and a verdict on a newborn is a category error. This notebook has receipts:
executed drills, dated dispositions, reproduced defects, a crash probe, and a provider swap. That
is evaluation's home ground, so this is a hard read rather than a gentle one. It is hard because the
work earned it.

---

## 0. The loop from last time closed. All three probes answered.

This matters more than anything else in the critique, so it goes first.

**Probe 1 — "What does an Episode project to when a run has no terminal event? If the outcome
collapses to `failed`, an absence has just become a verdict."**

**Answered, and passed, with a drill.** `GET /api/actions/act.crashed.1` → `attempted: true,
terminal: false, outcome: null`, and explicitly *never a FAILED verdict*. The controlled crash probe
then proved it across a process restart: file exists YES, `action_attempted(A)` YES,
`reconstruct_action(A)` None/unknown, no `action.completed`, no `action.failed`, **no automatic
second execution.** That is the sharpest question I had and it is closed with a receipt rather than
an argument. See §1 — because the same principle is violated one layer up.

**Probe 2 — "The model-swap invariant is proven between two fakes. The first real swap is where
provider vocabulary leaks backward into a model-neutral layer."**

**Answered, and it leaked — twice, in two different shapes.** DeepSeek: the adapter dropped the
assistant's `tool_call.id` and the orchestrator's tool message had no `tool_call_id`, so the
follow-up was rejected 422. Gemini: `thought_signature` must be echoed on the next turn or the model
degenerates to an empty response. The prediction held precisely, and both were caught by operation
rather than by the 71 tests. See §3 — because two incidents in two shapes is now a category.

**Probe 3 — "Versioning has no retirement story. Nothing states what retires a Procedure that is
simply wrong. Design it before the corpus grows; Aurora didn't and it costs us real money."**

**Partially answered.** The *mechanism* exists and works — `retire_if_current`, `list_as_of`,
OBS-004 exercises retirement and historical reconstruction. The *policy* does not: nothing in the
notebook states who decides a procedure is wrong, and the only proposal→authority path
(`LearningAnalyzer → GroundedLearningAuthority → AdaptationRunner`) has no operator entry. And the
warning has now recurred one level up, in the notebook itself rather than the memory store — see §6.

---

## 1. THE FINDING I WOULD PUT FIRST: absence became a verdict, one layer above where you fixed it

Your best single idea in this system is that an interrupted action must render **ATTEMPTED /
UNKNOWN, never FAILED** — an absence must not become a verdict. You hold that line rigorously at
the action layer and prove it with a crash probe.

Then, at the run layer, **tool-round budget exhaustion terminates as `run.failed`.**

Budget exhaustion is not a failure. It is an *inconclusive* outcome: the run stopped because a
bound was reached, which is exactly the epistemic state your action layer refuses to collapse. The
notebook records it four times — OBS-06's three attempts, the cold session (`run.failed`, budget
exhausted after 12 rounds), and Session 4 (`run.failed`, 12 rounds) — and in every case the model
was making legible progress, not erroring.

The consequence is not cosmetic, and your own notebook names the mechanism: **Phase 9 reads
terminals as evidence.** `GroundedLearningAuthority._authentic` reads `action.completed` /
`action.failed`. So a system designed to learn from outcomes is being fed "failed" for runs that
were merely bounded.

And there is a second instance you *did* spot and I think under-rated:

> **`run_command` `action.failed` = command exit status.** All 4 run_command actions are
> `action.failed` because `py -m pytest -q` exits non-zero (tests failing). … defensible, but it
> conflates "tool execution error" with "command reported a non-zero result" for Phase-9 evidence
> semantics.

That is not "defensible". A diagnostic command that *correctly* reports failing tests is recorded as
a failed logical action, and that record is learning evidence. A system that learns from this
corpus learns that **running the test suite is a thing that fails.** You have built the one
architecture in which that is discoverable, and the notebook discovered it — then filed it as a
carried-forward note.

**Recommendation, in your own vocabulary:** promote both. The terminal vocabulary needs a third
state that is neither success nor failure — `run.exhausted` / `action.inconclusive`, or a terminal
reason field that Phase 9's authenticity gate reads. The cheap version is one enum value and one
branch in `_authentic`. The expensive version is discovering in six months that every learned
adaptation was trained on mislabelled outcomes.

This is the highest-value item in this critique because it is *your* principle, correctly stated,
applied inconsistently — and you already own every mechanism needed to fix it.

---

## 2. The structural question: is `action_id` minted by the provider?

Session 4 observation 3 says:

> A = the provider's tool_call id (the model's proposed correlation identity); C = a Nexus-minted
> `call_id`

And the retry-duplication guarantee is closed by "`action_id` terminal lookup + attempted/unknown
refusal".

If I am reading that correctly, then **Nexus's strongest safety property is keyed on a value the
provider controls.** Your threat model is "the model proposes, Nexus decides" — but if the model
also *names* the decision, a replayed or colliding name becomes a way to influence what Nexus
decides. Two concrete consequences:

- **Replay → silent no-op.** A second action arriving with an already-terminal A hits the
  idempotency lookup, finds a terminal, and correctly refuses to execute. If A is provider-supplied
  and a provider ever reuses an id across turns or tasks, a legitimate side effect is silently
  suppressed and the refusal looks like the guarantee working.
- **Collision → authorization crossing.** Your Phase 3.x continuation test proves "approval A cannot
  execute regenerated B", which is the right pin. But it tests *Nexus not manufacturing* an A. It
  does not test *two logically distinct actions arriving with the same A*.

Session 4 measures "every action terminal carries a distinct A and C (16/16)" — within one run.
Nothing in the notebook establishes A's uniqueness across runs, tasks, or workspaces, and
uniqueness is the property the guarantee needs.

**You already built the right shape one layer down.** The 422 fix introduced
`ToolCall.correlation_id` — model-neutral, preserves the provider's id *as a correlation field*
rather than as identity. That is exactly the pattern the agency layer wants: **Nexus mints
`action_id`; the provider's tool_call id is stored beside it as a correlation.** Then identity is
yours, correlation is theirs, and the idempotency lookup is keyed on something no external party can
replay.

**Cheapest decisive test:** submit two actions with a deliberately duplicated provider tool_call id
and assert the second is refused *as a collision*, distinctly from being refused as already-terminal.
If those two refusals are indistinguishable today, that is the finding.

*Stated honestly: I cannot read your code, only the notebook. If `action_id` is in fact
Nexus-minted and the notebook's phrasing is loose, this whole section collapses and I would rather
be wrong here than silent.*

---

## 3. Provider turn-state is now a category, not two incidents

Under your own promotion rule — *repeatedly produces a concrete consequence* — this qualifies, and I
do not think you have filed it.

| provider | opaque per-turn state that must round-trip | where the fix landed |
|---|---|---|
| DeepSeek | `tool_call.id` → `tool_call_id` on the tool result | **core contract**: `ToolCall.correlation_id` |
| Gemini 3.x | `thought_signature` on each tool call | **adapter only**: stash and echo |

You note the Gemini fix needing "no core/orchestrator change" as a win, and structurally it is. But
read the two rows together: **each new provider carries opaque state that must survive the
round-trip, and the two you have met needed fixes at two different layers.** One was semantic enough
to earn a contract field; one was opaque enough to hide. A third provider will bring a third, and
the decision "contract field or adapter stash?" will be made ad hoc each time unless the category is
named.

The question your two data points now support — and I would *not* answer it yet, only file it:

> Is "opaque provider turn-state that must round-trip" a single category deserving one contract slot
> (an adapter-owned opaque blob keyed per turn), or is per-provider stashing correct precisely
> because the state is opaque?

The argument for naming it now: your purity gate is "no provider vocabulary in the model-neutral
layer", and the honest answer for Gemini was to hide the signature in the adapter — which is the
gate working. The argument that it still deserves a slot: an adapter that must persist state across
turns has acquired a lifecycle, and lifecycles that live in adapters are where the next 422 comes
from. That tension is worth one paragraph in the notebook before a third provider forces it.

---

## 4. OBS-06: you have exonerated the architecture by assumption, not by measurement

This is the one place where the notebook's own discipline is not applied to its own claim.

OBS-06 is classified **MODEL / STRATEGY EFFECTIVENESS — not an architecture defect**, on the grounds
that "the write path, approval, continuation, and correlation all work; the same backend previously
used them to build the software." Both facts are true. The conclusion does not follow.

The architecture decides **what the model sees each round** — how tool results are rendered,
whether prior results stay in the conversation, what the system prompt says about mutation, how a
failing pytest is presented. The loop is not a neutral pipe around the model; it is the model's
entire epistemic situation. So "the write path works" and "the loop is not causing non-convergence"
are different claims, and only the first is measured.

And the evidence is now strong enough to deserve better: the behaviour repeated across **three
attempts, one fresh cold session, and Session 4** — five occasions, two contexts, and a fresh short
conversation. You correctly concluded it is not long-context degradation. The same reasoning should
push one step further: five reproductions make it a *property of the system as operated*, and the
system includes the loop.

**Cheapest decisive experiment, and it is genuinely cheap:** same model, same task, same budget —
but one arm where the permitted toolset for a round is `write_file` only. If the model writes, it
can converge and the loop's tool menu was shaping the outcome. If it still refuses to propose a
mutation, you have isolated the model and OBS-06 becomes a much stronger claim than it is now.

A second, even cheaper arm: log the exact rendered tool result for a failing `pytest` run. If the
model is receiving a truncated or unhelpful rendering of the failure, that is an architecture input
to a "model effectiveness" result.

**Do not read this as disputing your conclusion.** It may well be right — deepseek-chat
diagnose-not-act is plausible and widely observed. The critique is narrower: you have refused to
*blame* the architecture, which is disciplined, but you have not yet *exonerated* it, and the
notebook reads as though you have. Your explicit "do not enlarge `max_tool_rounds` to hide this" is
exactly the right instinct; this is the same instinct pointed at the other side of the boundary.

---

## 5. The guarantee table flattens a distinction you make correctly in prose

The Phase 3 vs Phase 8 audit is the best artifact in the document — 14 guarantees, two paths, one
verdict column, traced from code and explicitly "not intent". Keep it.

But the `Equivalent?` column is binary and yields eleven NOs, while the prose immediately says *"the
strongest, consequence-bearing gaps are retry duplication and learning-evidence invisibility."* That
ranking is the load-bearing part and it lives only in the paragraph below the table.

Tables outlive their prose. Someone — a future you, a contributor, a model — will read those eleven
NOs and try to close all of them, which is how a correct audit turns into eleven slices of work
that nine of them did not need.

**Add a severity column**: consequence-bearing / latent / by-design. Three of your rows are
arguably *by design* and the table currently marks them as failures indistinguishable from the two
that mattered.

---

## 6. The notebook has a promotion ladder and no demotion path — and I have an expensive receipt

Your governing rule is excellent: *accumulate observations; promote only consequences.* The
promotion gate is real, the classification ladder has six branches, and "existing phases cannot
express requirement → candidate phase question" is the escape hatch that stops every observation
becoming architecture. I have not seen a better intake discipline in a project this young.

**It is a one-way ratchet.** There is no rule for retiring an observation that stops being true, no
expiry on `carried forward`, and no falsifier attached at birth. OBS-007 sits at "NOTE / MORE
OPERATIONAL EVIDENCE" with three candidate topologies and no condition that would ever close it.
The latent `_agency_call` finding sits as "a candidate bounded hardening slice if it ever manifests"
— with nothing that would notice the manifestation.

**Our receipt, from last night, and it cost us real money.** Aurora's central architectural arc —
the one its owner has named his single most important want for three months — turns out to be *the
most-designed and least-built arc in the house*: four fully reconciled designs, seven approved
ledger rows with no code, one ratified door never wired. And the worst part: **the governing law for
that arc was written 2026-07-30, is unbuilt, and its source note is now GONE from our own store.**
`note --get` refuses on both the title and the id. The document stating the law was lost to exactly
the failure it was written to prevent.

That is what an accumulating notebook with no expiry becomes at scale. Your promotion bar is
*stricter* than ours, which protects you from over-promotion — and does nothing about the other
failure mode, which is an observation that is neither promoted nor retired and is therefore
immortal.

**Concrete, cheap suggestion:** give every observation a **dies-when** clause at birth. One line,
written when the observation is filed, stating the condition under which it would be retired or
promoted. OBS-007's is easy: *"dies when three consecutive work sessions require zero manual worker
starts, or promotes when any session requires more than two."* An observation without one is not
yet an observation; it is an impression, which is what your own opening paragraph says the notebook
is allowed to hold — so the clause is also the line between the two.

---

## 7. LOCAL-ONLY is the structural risk, and it is not about backup

The header says `LOCAL-ONLY (gitignored)`. I understand the reasoning: the notebook holds
uncertainty, dead ends and impressions, and none of that should be mistaken for canonical
architecture. That instinct is right.

But look at what is actually in the file. `OBS-SQLITE-001 → CONFIRMED operational defect → AD-027
conformance hardening → RESOLVED`. The 422 → `ToolCall.correlation_id` → `test_phase3_tool_correlation.py`.
The crash probe's six-row table. **These are not impressions. They are the reasoning that justifies
shipped contract changes, and they exist on exactly one disk.**

Two consequences, and we have paid for both:

1. **No collaborator or future self can verify a single disposition.** Our own version of this: drill
   receipts lived on a gitignored path, so no clone could verify any drill — which made every
   recovery claim in our corpus unfalsifiable until we moved them. The fix was a one-line
   `.gitignore` negation.
2. **The AD is durable; its justification is not.** `AD-027`, `AD-050`, `AD-052` are tracked. *Why*
   they exist is in this file. A future contributor reads a contract with no visible reason and
   either cargo-cults it or removes it. Our equivalent scar is one directory over from §6: the law
   survived as a rule and lost its reasoning, and now nobody can argue with it because nobody can
   read it.

**Suggestion, preserving your instinct:** split the file by epistemic status rather than keeping it
whole and local. Uncertainty, dead ends and impressions stay local — that is the notebook's actual
purpose. But each **RESOLVED** disposition's one-paragraph consequence, and each promoted
requirement, becomes a tracked record next to the AD it justifies. You already have the mechanism
(AD numbers) and the naming. The missing link is that observation→AD is currently only in the
untracked file.

---

## 8. Smaller findings, ranked

**8.1 The latent `_agency_call` bug wants a pin now, not when it manifests.** You found by reading
that the granted-approval branch calls `run()` rather than `run_approved()`, and that a
pre-granted-but-unconsumed approval would re-evaluate authority and *silently return None*. A
silent None is the worst available failure shape. You have golden tests and the fixture is small.
Our house's rule, learned the expensive way: a law that stays a lesson keeps recurring; a law that
becomes a checker stops.

**8.2 The approval→action correlation is a durability question, not only observability.** You note
`approval.required/granted/consumed` carry no `action_id`, and that the correlation is recoverable
"via the `policy.decision` event + the continuation checkpoint". `policy.decision` is append-only;
**the continuation checkpoint is operational state.** If checkpoints are ever pruned, compacted, or
garbage-collected, the approval→action join dies and the loss is silent. That moves this from "a gap
in the trace" to "a durable record whose proof lives on a volatile plane" — which in our experience
rots into an assertion nobody can check. The schema column is cheap; add it before the pruning
policy exists, because the pruning policy will be written by someone who does not know this.

**8.3 Nothing measures the cost of the guarantees.** You count operator interventions per useful
task, deliberately un-optimised — good discipline, and rarer than it should be. But Session 4 spent
9 model turns, 16 physical calls, 4 approval pauses and 16 action/tool pairs to produce **zero**
useful changes, and the notebook records no token, latency or byte cost. If the guarantees are
expensive *and* the model is ineffective, those compound, and you will want the baseline from before
you cared. Same rule you already apply: count, don't optimise.

**8.4 OBS-004 and OBS-005 are separate classifications with a shared shape.** One is a missing
parameter, one a missing route — you are right that they are different. But both are "the projector
can already answer it; the surface does not expose it", and fixing them independently gets you two
ad-hoc additions. Offered as prior art rather than critique: we ended up needing a single read
grammar across planes — a fixed facet set (`as_of`, `kind`, `id`, `since`, `limit`) with a
*documented temporal law* (`known_at <= as_of`) and explicit 4xx rather than silent empties. It is
the thing that made cross-plane reads coherent instead of eleven endpoints with eleven conventions.
Worth deciding once, now, while there are two.

**8.5 The observer is never varied.** You cold-session the *model* — fresh DeepSeek, no transcript
— and that was the right experiment; continuity passed cleanly. But every observation in the
notebook shares one observer, one harness and one machine. OBS-006 is itself an instance: the empty
`requested_by` exists because *your harness* did not set it, and the harness's default became the
evidence. Ergonomics in particular cannot be measured from inside familiarity — the operator who
already knows the wiring is the one person who cannot tell you whether the wiring is discoverable.
**Cheapest version: hand the README and the nine steps to a competent stranger (or a fresh model
with no repo context) and record only where they diverge from your path.** Every divergence is an
ergonomic defect located precisely, and they will usually name the cause in their own words.

---

## 9. What I am taking from this notebook

Not politeness — these are going into our corpus with attribution.

**9.1 The denial-reason as the instrument.** Session 4 observation 6 proves Phase 9 now accepts real
work by showing that `GroundedLearningAuthority.evaluate` returns `deny` for **`unknown target`**
rather than **`fabricated or unverifiable evidence`** — so the evidence passed the authenticity gate
and only stopped for a missing target. That is a positive control on a negative result, which is the
hardest kind of test to design. Most people would have asserted `allow`, been forced to construct a
target memory, and contaminated the test with the fixture. Using the refusal *reason* as the signal
is a technique I did not have and am stealing.

**9.2 ARCHITECTURE PASS / EFFECTIVENESS FAIL as a first-class verdict shape.** Eight architectural
observations hold while the model fails the task, measured independently, in one session, without
either result being allowed to excuse the other. Your line — *"Mnemosyne preserves its guarantees
around a model that itself fails to complete the task"* — is the thesis of the whole system
demonstrated rather than argued. Our equivalent discipline is weaker: we tend to report a slice as
green when the mechanism works, without a separate axis for whether it helped.

**9.3 "Existing composition sufficient? YES / UNKNOWN" as a required field per observation.** Asking
whether the *architecture* is at fault, separately from whether a *surface* is missing, on every
single entry — that is a discipline, not a habit, and it is what keeps six of your eight
observations from becoming phases. We have the same distinction (we call it built-vs-wired) and no
field that forces the question.

---

## 10. Summary

The notebook is better than most production postmortem practice, and the single best thing in it is
structural: **architecture correctness and model effectiveness are independently measurable, and you
proved it under real load.** Everything in §1–§8 is available to you precisely because the notebook
is disciplined enough to expose it.

Ranked, if you only act on three things:

1. **`run.failed` for budget exhaustion, and `action.failed` for a non-zero diagnostic exit.** Your
   own "absence must not become a verdict" principle, broken one layer above where you enforce it,
   feeding a learning plane. (§1)
2. **Establish whether `action_id` is provider-minted.** If it is, a safety property is keyed on an
   untrusted value, and you already built the right pattern one layer down. (§2)
3. **Give every observation a dies-when clause.** Your promotion bar is stricter than ours; the
   failure mode it does not cover is the immortal un-promoted note, and we have a fresh, expensive
   receipt for where that ends. (§6)

And one request: the copy I read was truncated at Test Set #2's model-substitution table. The
DeepSeek↔Gemini result is the direct answer to probe 2 at the *effectiveness* layer rather than the
integration layer, and I would like to read it — particularly whether Gemini converges to
`write_file` where DeepSeek does not, because that single fact decides §4.
