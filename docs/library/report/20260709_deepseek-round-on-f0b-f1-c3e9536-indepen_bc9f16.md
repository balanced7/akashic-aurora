---
akashic_id: art_20260709_deepseek-round-on-f0b-f1-c3e9536-indepen_bc9f16
akashic_sha: c4cbf65a3fcc
status: draft
type: report
date: 2026-07-09
title: "DeepSeek round on F0b+F1 (@c3e9536): independent review + red-team drill"
gist: "# DeepSeek round on F0b+F1 (@c3e9536): independent review + red-team drill **Provenance**: DeepSeek (deepseek-v4-pro, think+agentic, read-on"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T00:34:57"
updated: "2026-07-09T00:34:57"
---
<!-- GENERATED PROJECTION of art_20260709_deepseek-round-on-f0b-f1-c3e9536-indepen_bc9f16 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek round on F0b+F1 (@c3e9536): independent review + red-team drill

# DeepSeek round on F0b+F1 (@c3e9536): independent review + red-team drill

**Provenance**: DeepSeek (deepseek-v4-pro, think+agentic, read-only) via bifrost runner,
2026-07-09, one combined request (backlog-bug workaround). PART 1 = unprimed code review;
PART 2 = adversarial drill: DeepSeek authored two replacement texts for a real rehab-class
lesson (`remote_model_local_tools_guards`, surfaced 10x / credit 0) — DRAFT-X
degraded-but-plausible, DRAFT-Y genuinely-better, labels blind — and claude ran both
through the gate. Full transcript in the runner console; drill drafts preserved verbatim
below. Ledger: T013.

## PART 1 — review findings and dispositions

DeepSeek self-retracted two candidate findings mid-review after re-reading the code
(`dict(incumbent)` does carry mined trigger_terms to the variant; the CLI gates and
applies the SAME draft variable) — the trace shows real verification discipline, worth
naming.

Surviving findings, with dispositions (all applied same-session where accepted):

1. **Captured-query vs re-derived query** (LOW-MEDIUM): the gate re-derives each context's
   query with today's builder instead of replaying the F0b-captured original. DeepSeek
   itself argued this to ground: re-derivation is the CORRECT gate semantic ("would the
   current matcher surface this text for that context"). APPLIED as an explicit docstring
   on `_context_query` — the choice is now stated, not implicit.
2. **apply_edit invalidates but does not re-warm the cache** (LOW): first post-apply hook
   call pays a store round-trip. APPLIED: `warm_cache()` after invalidation.
3. **Private-import fragility** (`_parse_trigger` et al.) (LOW): ACCEPTED — house idiom;
   the characterization suites pin these seams.
4. **Numeric test assertions depend on token weighting** (LOW): ACCEPTED — they are
   characterization pins by design; if the weighting changes, we WANT the alarm.
5. **Gate loads the full corpus projection per call** (LOW): ACCEPTED — ~1ms cache read;
   cost scales with corpus, fine at 66 lessons, revisit at 1000.
6. **"tokens" naming in the budget** (LOW): ACCEPTED — alphanumeric-sequence tokens; the
   comment names it a textual-learning-rate cap, not an LLM-token metric.

No HIGH findings. No crash/data-corruption/security findings.

## PART 2 — the drill, and what it caught

**Incumbent** (rehab class): "Use when exposing a REMOTE model to LOCAL tools (any agentic
CLI over a provider API), before shipping the tool executor: put every deny in the
harness, never the prompt (Principle #4). Non-negotiable guards = secret-block (the
provider key is IN the repo; an unguarded read_file exfiltrates it), path-scope, exec-gate
with a user-controlled /trust opt-in, and hard caps. Give full capability AND control:
read tools auto-run, dangerous tools need explicit human approval the user can escalate."

**DRAFT-X (revealed: degraded-but-plausible)** — generic, "cleaner" to a human skimmer,
discriminative terms gone: "Use when building an agent with tool access, before deploying:
isolate safety from behavior — the environment enforces what the model may only request.
Defense-in-depth: block sensitive paths, gate risky operations behind user confirmation,
cap resource consumption, and audit every privileged action. Let the model propose freely;
the harness decides what executes. This applies regardless of model provenance or tooling
framework."

**DRAFT-Y (revealed: genuinely-better)** — tighter Use-when, discriminative terms kept,
fluff shed: "Use when exposing a remote model to local tools over a provider API, before
shipping the tool executor: put every deny in the harness, never the prompt.
Non-negotiable: secret-block (an unguarded read_file exfiltrates the provider key),
path-scope, exec-gate behind /trust, hard caps. Read tools auto-run; dangerous tools gate
on explicit human approval."

**First run (gate as shipped @c3e9536):** both FAIL as "churn" — and the axis-2 line
exposed why: **the incumbent scores 0 hits on all 8 of its own recorded noise contexts
under today's floor.** The lesson's surfacings pre-date the vNext matcher regime (same
regime-change phenomenon the F0 fidelity decomposition quantified). For this class there
is NOTHING measurable at Tier 0 — no improvement possible, nothing to break — and calling
that "churn" was a gate blind spot.

**The fix (shipped this round): a third verdict, UNMEASURABLE.** Floors green + axis 1
vacuous + incumbent 0 current hits + variant 0 hits -> the gate ABSTAINS with a teaching
reason (wait for the F0b surface stream to accrue current-regime contexts, or apply on
human judgment via a plain re-record that bypasses the Forge visibly). Crucially the
rejected-edit buffer is NOT stamped — abstention is not refutation, and stamping would
poison a possibly-good draft. The regression hole stays closed: a variant that GRABS a
noise context the incumbent didn't is measurable badness and still FAILs (test added).

**Drill scorecard:** gate precision held (the degraded draft was never admitted — no
false PASS); discrimination between X and Y was impossible on this lesson's evidence and
is now honestly labeled as such. The X-vs-Y discrimination test re-runs naturally once
the durable surface stream has a few days of current-regime contexts — the first lesson
with fresh noise hits becomes the rematch.

## Outcome

Gate verdict space is now PASS / FAIL / UNMEASURABLE; 10 gate tests (2 new from the
drill); polish findings applied. The drill validated the review pattern upgrade: code
review catches wiring, but only adversarial USE catches epistemics.
