# Architecture-map truth review — claude's independent first pass

*Lens assigned: integration authority, governance, gate liveness, rollout order. No
consensus sought, nothing implemented. Reviewing note
`daniil-intuitive-mechanical-architecture-map-2026-07-30` (ADR_0730232046_815e3b65).*

**VERIFIED REPO FACTS (I ran these myself tonight) vs DESIGN INFERENCE (everything about
how the unbuilt compiler would behave) are labeled throughout.**

## 0. The live specimen, re-verified independently — and it is worse than reported

`VERIFIED`, six facts, each executed:

1. `scripts/check_comprehensibility.py` **does not exist**. `scripts/checkers/check_comprehensibility.py` does.
2. `scripts/githooks/pre_commit.py:61` invokes the missing path.
3. Live subprocess of that exact invocation returns **rc=2**, `"can't open file ... No such file or directory"`.
4. `pre_commit.py main():74` blocks only on `rc == 1`. rc=2 falls through to `return 0`.
5. The function's own docstring asserts the gate's **"(property UNBYPASSABLE)"**.
6. `git config core.hooksPath` = `scripts/githooks` — **the hook is wired and runs on every commit.**

The real checker works: rc=0, `"PASS: the comprehension layer matches the code (0 warning(s), fast mode)."`

So this is not a gate that sometimes fails. It is **structurally incapable of ever
blocking anything**, while documenting itself as unbypassable, while wired and executing.
I committed roughly fifteen times through it last night. It is the cleanest possible
specimen of Daniil's stated fear — not a system that fails, a system that **asserts a
property it does not have**.

## 1. The strongest way this graph could confidently lie

Not a wrong edge. **A wrong `verified` state.**

The whole trust model rests on the six-state ladder and on "observations never auto-promote
to authority." But `verified` is produced by checkers, and the specimen above proves a
checker can die in a way its caller cannot see. Generalize it: when a checker that sources
`verified` edges is renamed, moved, or changes exit code, the compiler does not observe an
error. It observes **absence of a violation** — and absence of violation is exactly what a
passing check looks like.

**A dead sensor and a clean sensor are indistinguishable at the graph layer.** `INFERENCE`,
but the mechanism is `VERIFIED` one layer down.

Two aggravating factors, both from my lens:

- **Determinism is being mistaken for correctness.** "Deterministic and model-free" is right
  and I endorse it — but a deterministic compiler over a dead sensor produces the *same
  wrong answer every time*, and its consistency will be read as corroboration. Reproducible
  ≠ true.
- **Trust compounds faster than accuracy.** Daniil's own framing is "a highly trusted truth
  surface." The more the fleet leans on it, the more expensive one silent false-`verified`
  becomes. The specimen sat dead for an unknown period and nobody noticed *because it never
  complained.*

## 2. Concrete counterexample / kill drill

**The drill needs no seeding — the repo is already in the failed state.** That is the
counterexample, and the acceptance question is simply: *would the proposed system have
noticed?*

**Drill A — DEAD SENSOR.** Take any checker contributing `verified` edges. Rename its file,
or change its violation exit code from 1 to 2. Run the full pipeline.
**PASS** only if (a) the build fails loudly AND (b) every edge that checker sourced renders
`unknown`. **FAIL** if the graph renders those edges `verified`, or renders nothing at all.

**Drill B — THREE EXIT CODES.** Every gate is exercised at rc ∈ {0, 1, 2}. Tonight's defect
lives entirely in the untested third value. A gate suite that only tests pass and fail has
not tested the gate; it has tested the two cases the author already had in mind.

**Drill C — SCOPE SHRINK.** Move a module outside the compiler's scanned roots. PASS only
if the graph reports reduced coverage. FAIL if the module simply vanishes and the graph
still renders "complete."

## 3. What must remain canonical OUTSIDE the graph

Four, from integration-authority:

1. **`security/acl.json` and all authority grants.** A compiler bug that drops an edge is a
   legibility problem; a compiler bug that drops an authority constraint is a security
   incident. The graph may *render* authority. It must never *be* it.
2. **The gate registry and its liveness.** If the graph is compiled by checkers, the roster
   of checkers cannot be an output of that same compiler — that is the sensor auditing
   itself. It needs an independently maintained, independently tested manifest.
3. **Git history and the append-only event stream.** Regenerable things are projections;
   these are not, and they are what recovered an overwritten artifact and reconstructed the
   whole cascade in the last two days.
4. **Human rulings** — Daniil's gate decisions and verbatim words. No derived surface may
   ever be able to compute `approved`.

## 4. Where it becomes burdensome or gameable

**Burdensome: the yellow tier.** Green is free, red is rare and earns its ceremony. Yellow
("boundary/dataflow deltas get one compact review") is where every ordinary refactor lands.
If yellow fires on most commits, seats will satisfy it mechanically — checklist fatigue, and
the corpus already carries the finding that compliance ≠ outcome. **Instrument yellow's
firing rate before requiring review on it.**

**Gameable, three ways:**

- **Contract minimalism.** Red edges need an EffectContract, so the cheapest compliant path
  is a contract that *under-declares* effects. The contract is self-reported and nothing
  cross-checks declared against observed. This is exactly the line codex drew on settlement
  — the instrument enforces and records, it does not originate the judgement — except here
  the judgement is originated by the author of the code being judged.
- **Exit-code laundering.** Any gate is neuterable by failing in a way the caller does not
  test. `VERIFIED` tonight, accidentally.
- **Silent scope loss.** If absence of coverage renders as clean, removing something from
  the compiler's reach is indistinguishable from it being fine.

## 5. Smallest amendment that blocks my failure

One principle: **a checker must report its own liveness, and any non-{0,1} exit must render
its edges `unknown` and fail the build loudly — never clean.**

Smallest mechanical form, three pieces:

1. **One registry entrypoint that normalizes exit codes.** `0`=pass, `1`=violation,
   *anything else* = GATE ERROR → build fails, and every edge sourced from that checker
   drops to `unknown`.
2. **A gate-health receipt per run** — which checkers ran, their exit codes, which edges
   each sourced. A run with a missing or erroring checker cannot produce a green build.
3. **One pin**: seed a missing checker; assert the build fails AND the affected edges render
   `unknown`.

This is far smaller than the full proposal, and it is the piece without which none of the
rest can be trusted.

## 6. Verdict — **AMEND**, one blocking condition

**ACCEPT the architecture.** Compiled-view-not-authority, record-once-at-source, the six
distinct states, per-edge provenance, deterministic and model-free generation, centralized
invocation, gate canaries. It is the right shape and it attacks the wound the round
measured: nothing marks what is currently true.

**BLOCKING CONDITION — sequencing, which is my lens:** *gate-health must ship before or
with the first graph consumer, never after.* If the graph ships first and the canaries
follow, we will have built a highly-trusted surface on sensors we have **already proven can
die silently**, and every day it runs before the canaries exist its trust compounds while
its accuracy stays unverified. That is tonight's specimen at a much larger blast radius.

**Proposed rollout order:** (1) gate registry + exit-code normalization + health receipt +
missing-checker canary; (2) fix the live `pre_commit` defect as *the first thing the new
registry catches* — a proof, not a patch; (3) green mechanical edges only, read-only, zero
ceremony; (4) yellow tier with its firing rate measured before review is required; (5)
red/EffectContract last, because it is the tier with self-report gameability and it needs
the observed-versus-declared cross-check to mean anything.

**Preserved disagreement:** I am one lens and I have been corrected four times in two days,
twice for exactly this failure — stamping an inference as settled. Section 1's "strongest
lie" is my `INFERENCE`; only section 0 is `VERIFIED`.

*— claude, independent pass, no consensus sought*
