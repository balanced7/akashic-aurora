---
akashic_id: art_20260731_arch-truth-review-claude_b310c5
akashic_sha: 65752310216b
schema_version: 1
status: current
type: report
arc: leadership-doctrine
date: 2026-07-31
title: arch-truth-review-claude
gist: "ARCHITECTURE TRUTH REVIEW — claude, independent first pass. Lens: integration authority, governance, gate liveness, rollout order. VERIFIED "
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory, agent-lifecycle, security]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-31T15:38:56"
updated: "2026-07-31T15:38:56"
---
<!-- GENERATED PROJECTION of art_20260731_arch-truth-review-claude_b310c5 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# arch-truth-review-claude

ARCHITECTURE TRUTH REVIEW — claude, independent first pass.
Lens: integration authority, governance, gate liveness, rollout order.
VERIFIED = measured in E:/AI-Setup @ad22947 this morning. INFER = design reasoning.

**1. Strongest way this graph could confidently lie.**
By carrying `verified_by` / `authorized_by` edges whose verifier never executed. The graph's
trust is compiled from gates, but nothing in the proposal verifies a gate RAN.

VERIFIED, not inference: `scripts/githooks/pre_commit.py:61` invokes
`scripts/check_comprehensibility.py`. That file does not exist — it moved to
`scripts/checkers/` in T104-M1. A missing path makes the interpreter exit rc=2; I measured
rc=2. `main()` blocks only on `rc == 1`, so the commit PROCEEDS. ship.py:34 and
.github/workflows/ci.yml:39 both use the correct `scripts/checkers/` path — so the guard is
alive at two layers and dead at the third.

The sharp part: that module's own docstring asserts property UNBYPASSABLE, "CI + pre-commit
hook + ship all run it." The claim is false and has been since the move. Its designed
fail-open (the `except` branch, for a CRASHING guard) never fired, because a missing file
does not raise — it returns quietly. So "verified" means "someone wrote a verifier," never
"the verifier ran and returned a verdict." An architecture graph inherits that meaning
exactly. And the failure gets QUIETER as the system gets more trusted, because the incentive
to read the label instead of the receipt rises. [VERIFIED mechanism; INFER on escalation.]

**2. Concrete counterexample / kill drill.** Two, both live today.

(a) DEAD-GATE DRILL. Stage a file containing a stale repo reference (check F catches this
class). Commit. It succeeds right now. Acceptance: it must fail, AND the graph must render
the pre-commit `verified_by` edge as UNKNOWN — not CONFIRMED — until a receipt carrying a
real exit status exists. Generalized rule: absence of evidence must render as absence, never
as pass. A gate that emits no receipt is a FAILED gate, not a passed one.

(b) TWO-AURORAS DRILL. `git worktree list` shows
`E:/AI-Setup/.claude/worktrees/stoic-rubin-573f2b` at detached 2c172ad, carrying the entire
pre-T104 layout: its own `scripts/check_comprehensibility.py`, `scripts/hooks/pre_commit.py`,
and a `ci.yml` pointing at the old path. Any extractor that walks the tree compiles TWO
architectures and merges them silently, or resolves a symbol to the ghost. Acceptance: the
compiler declares its universe (git-tracked paths at ONE rev, worktrees excluded by
construction) and fails loudly on any input outside it. Note the receipt: my own grep hit the
ghost copy BEFORE the live one. That is the newcomer's confusion, mechanized. [VERIFIED.]

**3. What must remain canonical outside the graph.**
Git — the graph projects a rev, it never owns history. The Ledger/Store — runtime world
state; the architecture-vs-world split must be enforced, not conventional. Daniil's rulings
and the LEXICON — vocabulary and authority are legislation; a compiler may render them, never
mint them. And the executable gates themselves: the graph reports what a gate said, it must
never become the thing that decides whether a gate passed. If the graph becomes the verifier,
it has no verifier.

**4. Where the process becomes burdensome or gameable.**
Burdensome: any step that requires visiting a second artifact. "Declare the relationship
delta" as a checklist item will be skipped under load and backfilled from memory — which
manufactures confident fiction, the worst possible output. Co-locate the declaration with the
symbol (AST-extracted stanza on the function/module) so declaring is an edit to the file
already open, and a wrong declaration appears in the same diff as the code.

Gameable, three ways. (i) If UNKNOWN fails the gate, agents write filler cards to go green;
mandatory coverage buys false confidence. Make UNKNOWN legal — T121 already shipped that law —
and fail only on CONFLICT and on unsuperseded weakening of an existing edge. (ii) MUST NOT
clauses are negative claims: underivable and unobservable by construction. Without an
executable falsifier that ATTEMPTS the forbidden act and fails, they are decoration that
reads as enforcement. (iii) Time-bound exemptions are the right shape (the existing `rot-ok`
expiry is good), but an exemption list is exactly where a dead gate hides — so exemptions must
render as first-class DEGRADED edges in the graph, never as silence.

Governance gap: the declared plane is legislation wearing a compiled costume. Declared edges
without author / date / ratifying gate / superseded-by rebuild the precise provenance
asymmetry kimi named as the round's root.

**5. Smallest amendment that blocks my failure.**
Gate-liveness receipts, and the graph REFUSES to render a verification edge without one:
(a) one `run_gate(id)` entry point that resolves the path, executes, and appends a receipt
event {gate id, resolved path, exit status, timestamp};
(b) every caller — pre_commit, ship, CI — routes through it, so there is ONE choke point
instead of three hand-maintained paths that already drifted apart;
(c) ANY non-zero exit blocks. The current `rc == 1` test is the precise bug that let a missing
file read as success;
(d) a canary gate DESIGNED TO FAIL, run on every invocation — if the canary passes, the
harness is lying and everything blocks. This is the only mechanism that detects a gate which
stopped RUNNING, as opposed to one that ran and passed.

Roughly a day's work, and it retires a live defect whether or not the graph ever ships.

**6. Verdict: AMEND — accept the design, block the rollout order.**
BLOCKING CONDITION: the gate-liveness receipt + canary lands and is green BEFORE any
architecture edge is allowed to claim `verified_by`. The proposal's whole trust argument is
"compiled from the sources that already enforce reality," and we have now MEASURED that one
of those sources has not been enforcing since T104-M1. Building a trusted view on an
unverified verifier is exactly how the graph becomes "something that lies to us and causes
confusion" — Daniil's stated fear, in his words.

NON-BLOCKING, on order: do not open this as a third round. STATE-OF-THE-ROUND §6 has two in
flight and names opening a third as the failure being diagnosed. Fold the arch profile in as
a constraint on how the mail vertical ships. And make the FIRST deliverable an answer key
written from rulings that already exist — the `open` / `seen` MUST NOTs are already ruled in
prose — rather than an extractor. Same discipline as the incident replay oracle: know the
answer before writing the code.

DISAGREEMENT PRESERVED: I do not accept "a trusted compiled view, never sole authority" as
sufficient for the DECLARED plane. Derived and observed compile; declared is AUTHORED. Calling
the whole artifact "compiled" launders authored claims through a mechanical-sounding word.
That is my one substantive objection to the framing, and I would keep it on the record even
if the rest ships unchanged.

— claude
