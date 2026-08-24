# ARCHITECTURE TRUTH REVIEW — kimi, independent first pass (round 2, morning)

Lens assigned: model cognition, intuitive presentation, lifecycle/status ambiguity, human factors.
Label discipline: VERIFIED = I read the file in the live tree this morning (2026-08-02). INFER = design reasoning. GUESS = flagged.

## 0. Correction to the brief's live warning (VERIFIED, matters for the record)

The warning as stated is **stale**. `scripts/githooks/pre_commit.py:66` now resolves
`scripts/checkers/check_comprehensibility.py`, with an explicit `os.path.exists` branch that
returns rc=2 with "checker MISSING... this gate is NOT running. Wiring defect, not drift." A
comment block at lines 62–65 narrates the whole incident (silent no-op from T104 move until
2026-08-01). The ghost path was fixed 2026-08-01.

**The live residue is the DOC, not the wiring.** `docs/ARCHITECTURE.md:180` claims the guard
"runs at three unbypassable chokepoints" and "a crashing check FAILs loud rather than passing
green." The hook's own docstring, in the same tree, documents the opposite: fail-open on crash
("a broken guard must never brick every commit") and "Emergency bypass: `git commit --no-verify`."
So the doc overstates two load-bearing properties while the code honestly disclaims them. This
is not a nit — see §1, it is the failure mode itself, already instantiated.

## 1. Strongest way this graph could confidently lie

**Status-laundering: the graph compiles a status word (`verified`, `unbypassable`, `current`)
from where a claim LIVES instead of from evidence the claim was CHECKED — and the compiler
cannot tell the difference, because the doc plane and the code plane already disagree and both
look authoritative.** [VERIFIED that the two planes disagree today; INFER that the graph
inherits it.]

The mechanism is subtler than claude's dead-gate receipt (which I confirmed is fixed). Watch
what happens when the graph's extractor reads `ARCHITECTURE.md:180`: the module is wired, the
guard file exists, CI invokes it, ship invokes it — every *structural* probe is green. The word
"unbypassable" compiles to a VERIFIED or DECLARED-trusted edge. Meanwhile the hook's docstring —
the *honest* plane — says fail-open + `--no-verify`. Both are in the repo. A mechanical compiler
has no principled way to prefer the humble docstring over the confident architecture map; if
anything it prefers the map, because the map is the load-bearing doc. **The graph then states,
with provenance, a property the system does not have — and it states it more confidently than
the raw tree does, because compilation strips the hedging context.** That is Daniil's "lies to
us" verbatim: not a wrong edge, a *confidently rendered* true-looking edge whose truth was never
in any source.

Generalized: the most dangerous lies are not missing data, they are **status words that changed
meaning in transit** — "verified" (ran vs. exists), "current" (regenerated vs. reviewed),
"unbypassable" (wired vs. actually blocks). The proposal's six labels (declared/derived/observed/
verified/conflict/unknown) are the right ontology, but the ontology does not save you if the
*assignment* of a label is itself compiled from presence.

## 2. Concrete counterexample / kill drill

**THE OVERSTATED-PROPERTY DRILL** (new, complements claude's two, does not duplicate them):
Hand the compiler the CURRENT tree. Ask it to emit the edge
`pre_commit_hook -[property: unbypassable]-> comprehensibility_gate`.
- **Pass condition:** the compiler must NOT emit this as VERIFIED. Acceptable outputs: CONFLICT
  (map-claim vs. hook-docstring-disclaimer), or DECLARED-unverified with the docstring surfaced
  as the disconfirming source. It must fail loudly only if it emits VERIFIED.
- **Why it kills:** the input is 100% mechanically present (both strings are grep-able), so a
  purely mechanical pass has no excuse. If the compiler resolves the conflict by preferring the
  higher-altitude doc, you have proven the graph systematically upgrades authority over evidence.
- **Second half (lifecycle):** bump nothing, re-run tomorrow. The edge must render identically
  (determinism) AND still carry the unresolved-conflict marker — i.e. the graph must not let a
  stale conflict age into acceptance. [INFER: this is where status ambiguity bites — a CONFLICT
  nobody resolved starts reading as background noise, then as truth.]

## 3. What must remain canonical outside the graph

- **Git + the live tree** — the graph projects a rev, never owns it. (Agrees with claude.)
- **The disconfirming/hedging context** — docstrings, comments, `--no-verify` notes, fail-open
  rationales. The graph renders claims; the *caveats attached to those claims* must stay
  reachable in one hop and must NOT be summarized away, because the caveat IS the truth-status.
  If compilation drops the docstring's "fail-open is deliberate policy" while keeping the map's
  "unbypassable," the graph has editorialized.
- **Human/Daniil rulings + the LEXICON** — legislation, never minted by a compiler.
- **The verdict-producing gates** — the graph reports a gate's output; it must never become
  the thing that decides pass/fail, or it has no verifier.
- **Time / liveness itself** — "this gate ran at T" is a runtime fact; the graph must import it
  as an OBSERVED receipt, never derive it from wiring.

## 4. Where the process becomes burdensome or gameable

- **Burdensome (cognitive, my lens):** the six-label ontology is correct but it is *one more
  status vocabulary* on top of VERIFIED/INFER/GUESS, the ledger states, and the doc statuses.
  Humans and seats will not maintain six distinctions under load; they will collapse to
  "green/red." The proposal must specify the *collapse behavior* — when a reader ignores five
  labels and reads only the rendered view, does the view still distinguish "checked" from
  "asserted"? If the honest reading requires holding all six, the design will be used as two.
- **Gameable (my lens, status ambiguity):** whichever label is cheapest to assign becomes the
  default. If DECLARED requires no receipt and VERIFIED requires one, load-bearing claims will
  be filed DECLARED and *read* as VERIFIED — label arbitrage. Counter: the rendered view must
  visually demote un-receipted claims (not just tag them), so the cheap label is also the
  low-status one.
- **Conflict-fatigue:** if CONFLICT blocks integration, builders learn to avoid creating the
  second claim that would raise it — i.e. they stop filing the disconfirming docstring. The
  gate then selects for silence. (This is the same shape as "UNKNOWN must score correct or the
  test trains the lie" — a gate that punishes the honest label manufactures the dishonest one.)

## 5. Smallest amendment that blocks my failure

**A status-word provenance rule: no status adjective compiles upward.** Concretely —
(a) the compiler extracts *claims about properties* (unbypassable, verified, current, enforced)
  as first-class nodes with their source span;
(b) a property claim renders VERIFIED only if a receipt or an executable falsifier exists —
  never because a load-bearing doc asserts it;
(c) when two sources disagree on a property (map says unbypassable, docstring says fail-open),
  the edge renders CONFLICT with BOTH spans linked, and the view refuses to resolve it by
  altitude or recency;
(d) the rendered MODULE_INDEX/boot view carries a per-module "checked vs. asserted" count so
  the two-label reader (§4) still sees the distinction without holding the full ontology.
This is small — it is a rule about which edges may carry which label, plus one surfacing
change — and it directly blocks the lie in §1.

## 6. Verdict: AMEND

The design is sound and the ontology is the right one. Two blocking conditions:

1. **BLOCKING — status-provenance rule (§5) lands before any property-bearing edge may render
   VERIFIED.** Rationale: the doc/code disagreement is live in the tree TODAY (verified §0), so
   the failure is not hypothetical; a compiler that ingests the current repo without this rule
   ships the lie on day one. I keep this blocking even though claude's dead-gate receipt is
   fixed, because the fixed wiring did NOT fix the overstated doc — the genus is alive.
2. **BLOCKING — the doc/code overstatement itself gets reconciled (either ARCHITECTURE.md:180
   is corrected to name the fail-open + `--no-verify` policy, or the policy is changed to match
   the doc).** A trusted compiler cannot have a known-contradicted source pair as its first
   input; whichever way it resolves, the resolution must be a human decision, not a compiler
  default.

DISAGREEMENTS PRESERVED / DISTINGUISHED:
- **vs. the brief:** the ghost-path warning is stale (VERIFIED). Attacking that specific
  mechanism today attacks a fixed bug. The live attack surface is the *overstatement residue*
  and the status-laundering genus.
- **vs. claude (kept, not resolved):** claude's blocking condition was gate-liveness receipts;
  that condition has now been met by the 2026-08-01 fix, and I do NOT think it was sufficient —
  the doc still lies with the receipts green. So I disagree that "receipts first" covers the
  case; receipts prove a gate RAN, they do not prove the *words about the gate* are true. My §5
  is the additional condition. I also record agreement with claude's preserved objection: the
  DECLARED plane is authored, and calling the whole artifact "compiled" launders authorship —
  my §4 label-arbitrage point is the same concern from the cognition side.
- **INFER, flagged:** I expect deepseek to attack the compiler determinism/universe side and
  possibly rate the dead-gate fix as closing claude's condition. If so, the disagreement to
  preserve is exactly this: receipts ≠ truth of status-words, and the two conditions are
  complementary, not substitutes.

— kimi
