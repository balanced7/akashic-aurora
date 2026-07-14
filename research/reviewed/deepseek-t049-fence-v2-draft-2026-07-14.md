# DeepSeek T049 — Fence Protocol v2 (draft, 2026-07-14)

Status: draft proposal (deepseek, 2026-07-14)
Class: method amendment — changes to docs/method-baseline-2026-07.md
Gate: Daniel ratifies or rejects per-amendment; counter-checked by claude with the proposed
mandatory path-verify pass (amendment #1 practiced on this very draft). The method baseline is
Daniel's contract; we prepare, he ratifies.
Inputs: docs/method-baseline-2026-07.md (the contract to amend), interview at
research/reviewed/deepseek-experience-recall-at-2026-07-14.md §d.

---

## Amendment 1 — Mandatory citation path-verify as reconciliation step one

### Change

Amend **M1** in `docs/method-baseline-2026-07.md`. Insert after the PROTOCOL paragraph and
before the RECEIPTS paragraph:

```
M1-PV. PRE-RECONCILIATION VERIFICATION PASS (mandatory step 1).
Before any reconciliation triage (converged/complementary/divergent), the reconciler
GLOBS every file:line citation in BOTH fence halves against the live repo. A citation
that resolves to a non-existent file, a path with no matching glob, or a line number
beyond the file's actual length INVALIDATES the section containing it. INVLAIDATION is
section-scoped: one fabricated citation retires its enclosing claim-block, not the
whole report. The reconciler records INVALIDATED sections with the offending citations
in the reconciliation header; the surviving content of that half is reconciled normally.
A citation to a DESIGN-ONLY artifact (no code exists — e.g., a design doc path, a
non-implemented spec section) is valid if the cited design document exists AND the claim
is explicitly marked as design-level. A citation that fabricates implementation detail
(code paths, line-quoted excerpts) against a DESIGN-ONLY seam is an automatic
invalidation — grounding pressure at a no-code seam induced the fabrication.

This verification pass completes BEFORE the reconciler reads either half's conclusions,
to prevent confirmation bias: verify the evidence, then read the arguments.
```

### Failure mode it closes

**Real receipts:** My own T039 counter-check R1 (`research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r1-partial.md`):

- R1 cited `bifrost/lane.py:217` and `:342` with quoted code. **No `bifrost/` directory
  exists anywhere in the repo.** T039 was DESIGN ONLY — no lane code had been built. The
  citation was fabricated.
- The A1 refutation was structurally correct (a SET doesn't guarantee FIFO — the
  sharpening survived as A1′), but the evidence was invented. Had the reconciliation
  relied on R1's cited evidence, it would have grounded a ruling on fake code.
- Root cause: "grounding pressure on a no-code seam induced fabrication." The ask demanded
  grep-grounding against an artifact that had no implementation.

R2 (`research/reviewed/deepseek-t039-review-countercheck-2026-07-13-r2-invalid.md`):

- Confabulated corpus: the report claimed to have examined `t039_reconciliation.md`,
  `t039_halves.md`, `t039_halves_brief.md` — not the real filenames.
- Cited "packet-spec section 4.1" and a "per-flow 16-bit sequence number" — no such
  section or width exists in `docs/packet-spec-v1-2026-07.md`.
- A mandatory path-verify pass would have caught both before any conclusions were drawn.

**Without M1-PV:** a reconciler reads a plausible-sounding citation, accepts it, triangulates
around evidence that doesn't exist. The fence's core value — independent evidence grounding —
is silently hollowed.

### Cost/risk

- **Cost:** One additional verification pass per reconciliation. For a typical fence with
  ~20 citations across both halves, this is a ~2-minute glob+wc step. Tools already exist
  (`find_files`, `read_file` for line-count).
- **Risk of false invalidation:** A citation to a file that was renamed between report-time
  and reconciliation-time could trigger. Mitigation: the glob tries the EXACT path first,
  then a fuzzy match against the filename alone. If the file exists under a different path,
  the citation is RECLASSIFIED (not invalidated) and the reconciler notes the rename.
- **Risk of over-reliance:** The pass catches fabricated paths but not fabricated content
  — an invented line number on a real file still passes. That's a limit, not an argument
  against the check. The section-scoped invalidation rule (not whole-report) prevents a
  single honest mistake from discarding an entire half.

### When it does NOT apply

- **Single-blind reviews** (see Amendment 3, fence-lite): no reconciliation step, so M1-PV
  fires at review-ingest time instead — the reviewer verifies their own citations.
- **Purely design-level halves where BOTH halves explicitly carry the DESIGN-ONLY marker
  and cite only design documents** (no implementation paths): the pass is still RUN but
  expected to be a no-op; it confirms the DESIGN-ONLY contract was honored.
- **Trivial mechanical changes** below the fence-lite threshold: no fence at all.

---

## Amendment 2 — Structured uncertainty field per fence verdict

### Change

Amend **M1** in `docs/method-baseline-2026-07.md`. Insert after the RECONCILE sentence
and before RECEIPTS:

```
M1-CF. CONFIDENCE FIELD PER VERDICT.
Every verdict item in a fence half carries a `confidence` tag with one of exactly four
values — no unmarked verdict reaches reconciliation:

  CERTAIN       — citation-grounded; every claim traces to a named file:line or
                  design-doc section that exists and unambiguously supports it.
  DESIGN        — the claim is about a not-yet-built artifact; the reasoning is
                  grounded in the governing spec/design doc, but no implementation
                  exists to cite. No fabricated code paths (see M1-PV).
  INFERRED      — grounded in system behavior or patterns but NOT in a direct
                  file:line citation; the claim is plausible and reasoned, not
                  evidenced. The reconciler weights it accordingly.
  UNCERTAIN     — the author cannot resolve this from the provided inputs and is
                  explicitly flagging the gap. This is NOT a failure — it is a
                  structured "I don't know" that prevents silent omission.

No hedging modifiers ("probably," "likely," "seems to") substitute for the tag.
A paragraph without a confidence tag is an incomplete deliverable; the reconciliation
returns it to the author.
```

### Failure mode it closes

**Real receipts:** The T039 reconciliation (`research/reviewed/t039-lanes-latches-reconciliation-2026-07-13.md`)
shows nine converged items, two diverged items — none with explicit confidence
annotations. The reconciler had to infer which verdicts were evidence-backed vs
reasoning-backed from the prose.

In the recall-networking reconciliation (`research/reviewed/recall-networking-reconciliation-2026-07-12.md`),
R4 (segment lists downgraded to VOCAB) hinged on a deepseek argument that was
persuasive but not citation-grounded — the reconciler had to weigh its force
implicitly. A DESIGN tag would have made clear there was no implementation to cite.

In my R2 counter-check, the model drifted into network-on-chip vocabulary (virtual
channels, lane striping, per-VC credit flow control) — an UNCERTAIN tag on every
claim would have been the honest answer, and the absence of CERTAIN/DESIGN tags
would have immediately flagged the report as ungrounded before any content was read.

### Cost/risk

- **Cost:** Authors add one word per verdict item. For a typical fence half with
  10-15 verdict items, this is 10-15 words of overhead.
- **Risk of grade inflation:** Authors over-tag INFERRED as CERTAIN to sound more
  authoritative. Mitigation: M1-PV catches fabricated CERTAIN citations; a pattern
  of DESIGN claims that should be INFERRED surfaces at reconciliation when the
  reconciler asks "where is the design doc for this?" — and there isn't one.
- **Risk of over-caution:** Authors tag everything INFERRED to avoid the CERTAIN
  commitment. Mitigation: a fence half consisting entirely of INFERRED/UNCERTAIN
  tags is honest but low-value — the reconciliation notes it and the brief may
  need sharpening.

### When it does NOT apply

- **Fence-lite reviews** (Amendment 3): single-blind, no reconciliation — the
  confidence tag is still RECOMMENDED but not mandatory; the reviewer's prose
  already signals uncertainty.
- **Trivial items in a fence half that are pure CONVERGED affirmations of the
  other half** — these can carry a collective "CONVERGED-CERTAIN" tag from the
  reconciler, not per-item from the author.
- **Discovery-phase work** (M0 taxonomy, M2 SOTA reads): the outputs are
  classifications and import verdicts, not fence halves — the existing ADOPT/ADAPT/
  REJECT vocabulary already encodes confidence implicitly.

---

## Amendment 3 — Fence-lite tier

### Change

Add a new practice **M1-LITE** after M1 in `docs/method-baseline-2026-07.md`:

```
M1-LITE. FENCE-LITE: SINGLE-BLIND + REVIEW (the proportional tier).
TRIGGER: any decision where a wrong answer is EXPENSIVE but the blast radius is
REVERSIBLE and CONTAINED — one agent authors, a DIFFERENT agent reviews with a
counter-check framing (try to break it, not bless it). NO blind half, NO
reconciliation step. The review is adversarial, not editorial.

The OBJECTIVE GATE that picks full-fence (M1) vs fence-lite (M1-LITE) vs no-fence:

  1. FULL FENCE (M1) — ANY of:
     a) Blast radius ≥ 3 files AND any file is in core/comm/, core/trust/,
        core/foundation/store.py, or a coordination primitive.
     b) Revert cost = DATA LOSS or STATE CORRUPTION or CROSS-AGENT CONTRACT BREAK
        (a revert does not undo the damage — e.g., a bad event written to the
         ledger survives the revert; a broken coordination contract poisons
         concurrent agents before the fix lands).
     c) The change touches a Trust Boundary (auth, capabilities, ACL, secrets
        handling, agent identity, bus addressing).
     d) The change modifies THIS document (docs/method-baseline-2026-07.md) or
        AGENTS.md — the door contracts themselves.

  2. FENCE-LITE (M1-LITE) — ALL of:
     a) Blast radius ≥ 3 files (still multi-file) BUT none in the full-fence
        paths above.
     b) Revert cost = WORK LOST (the change can be cleanly reverted; no data
        survives the revert to corrupt; a bad version only wastes time, never
        poisons state).
     c) The change is a new capability, a design decision, or a refactor crossing
        a module boundary — i.e., review adds value beyond what a linter catches.

  3. NO FENCE — ALL of:
     a) Blast radius ≤ 2 files AND none in the full-fence paths.
     b) Revert cost = TRIVIAL (a single `git revert` undoes everything with zero
        lingering effects).
     c) The change is a bugfix with a pre-registered acceptance test, a typo fix,
        a comment update, or a mechanical rename.

The TRIGGER is assessed at slice REGISTRATION time (before any code is written) by
the CLAIMING AGENT and recorded in the slice's ledger entry. The reconciler (full
fence) or reviewer (fence-lite) CONFIRMS the tier before beginning — a mis-rated
slice is escalated (lite→full) or challenged (full→lite) with a one-line reason.
The gate is OBJECTIVE (file paths, revert cost) — "this feels simple" is not a gate;
"this touches 2 files, neither in core/comm/" is.
```

### Failure mode it closes

**Real receipts:** Every fence pass to date has been full-fence (M1), regardless of
blast radius. The T039 fence was DESIGN ONLY — no code, no revert cost beyond a
design doc rewrite — yet it went through blind halves + reconciliation + counter-check.
The recall-networking fence was research-stage — again no code — yet the same full
protocol. Both produced high-quality results, but the PROPORTIONALITY principle (P0)
was violated: the process cost more than the cost of being wrong.

Conversely, the T043 send-door hardening was a LOAD-BEARING coordination change
touching `core/comm/packet_spec.py` (new LAW file), the runner bridge, and Redis
reassembly — it earned every step of the full fence. The tier gate would have
confirmed this.

The risk without M1-LITE is ceremony-decay: when every decision gets the same heavy
protocol, the protocol becomes background noise. Agents stop treating it as
load-bearing. M1's own metric ("a long run of zero-divergence passes means the
fence has decayed into ceremony") detects this, but M1-LITE PREVENTS it by
reserving full-fence for decisions that genuinely need it.

### Cost/risk

- **Cost:** One additional decision at slice registration (takes ~30 seconds: count
  files, check paths, assess revert cost). The reviewer confirms it before starting.
- **Risk of under-fencing:** A change is rated fence-lite but should have been
  full-fence. Mitigation: the reviewer's first task is tier CONFIRMATION — if the
  reviewer disagrees, it escalates. The "core/comm/, core/trust/,
  core/foundation/store.py" path list is the bright-line rule; it can be extended
  but never reduced without a method amendment. Second mitigation: reversibility is
  assessed as "does a revert undo the damage?" not "can we revert the commit?" —
  an event written to the ledger is DATA LOSS on revert (the bad event persists),
  which triggers full-fence.
- **Risk of over-fencing the fence itself:** The tier assessment is a one-line
  ledger entry, not a document. It is itself below the fence-lite threshold
  (1 line, no code, trivial revert).

### When it does NOT apply

- **The tier assessment itself** — it's a metadata decision, not a slice.
- **Existing slices already in flight** — the gate applies to NEW slices registered
  after this amendment lands. Retroactive re-tiering is optional.
- **Daniel's gate overrides everything** — if Daniel directs full-fence for a
  change that would otherwise be fence-lite, his word is the trigger.

---

## Amendment 4 — Brief format contract

### Change

Amend **M1** in `docs/method-baseline-2026-07.md`. Add after the existing PROTOCOL
paragraph:

```
M1-BRIEF. BRIEF FORMAT CONTRACT.
Every fence brief is a single file with exactly FIVE sections, in order:

  (1) CHARTER — one sentence: what kind of fence this is (DESIGN / REVIEW /
      RESEARCH / COUNTER-CHECK) and the question at stake.
  (2) INPUTS — an itemized list of every file both agents must read. Each entry
      is a path (relative to repo root) that EXISTS at brief-write time. No
      "review the codebase" — name the files. For DESIGN-ONLY fences, the brief
      states "DESIGN ONLY — no implementation exists; cite only the design docs
      listed below." This is the grounding-pressure relief valve that prevents
      citation fabrication at no-code seams (see M1-PV receipt: T039 R1).
  (3) RULES OF ENGAGEMENT — the fence protocol for THIS fence: which sections go
      in which order, whether Part A is blind to Part B, whether there is a
      reconciliation or counter-check phase, and the DELIVERABLE path with format.
  (4) THE QUESTION — the raw question, verbatim or verbatim-close, with enough
      context that both agents interpret it identically. No analysis in this
      section — it is the shared prompt, nothing else.
  (5) OUTPUT CONTRACT — exact deliverable path(s), format (markdown sections,
      verdict-per-item with confidence tags per M1-CF), and BUS REPLY contract
      (pointer-only vs full-report).

The five sections are MANDATORY; a brief missing any section is returned to the
author. Sections beyond the five (background, prior art, methodology notes) are
PERMITTED but go AFTER the five — never before, never interleaved. The brief is a
CONTRACT, not a narrative; the five-section structure is the contract format.

The brief is WRITTEN by the asker (usually the agent who will reconcile), NOT by
the peers — the asker defines the question and the inputs; the peers answer within
that frame. A peer who believes an input is missing or the question is ill-posed
records that in the reconciliation as a D-item, not by rewriting the brief.
```

### Failure mode it closes

**Real receipts:** The recall-networking fence brief (`research/recall-networking-fence-brief-2026-07-12.md`)
is 100+ lines. The first ~40 lines are protocol description, background, and
methodology that the peers must parse before reaching the actual question. The
raw question appears at line ~35. The input list and deliverable contract are
interleaved with protocol narrative.

The T039 design brief (`research/t039-lanes-latches-design-brief-2026-07-13.md`)
was a different format entirely — a design brief, not a fence brief — and the
r1/r2 failures were partially caused by the ask not explicitly stating "DESIGN
ONLY — no implementation exists." The peer defaulted to grep-grounding against
code that didn't exist.

The five-section contract prevents:
- **Protocol-buried questions:** The asker's protocol notes bury the actual
  question; the peer may misinterpret which part is the prompt vs which is
  meta-commentary.
- **Missing input lists:** A peer doesn't know what to read; they guess; they
  read the wrong files; the fence is blind to different evidence sets.
- **Missing DESIGN-ONLY markers:** The peer assumes implementation exists;
  grounding pressure induces fabrication (T039 R1 receipt).
- **Ambiguous deliverable contracts:** The peer writes to the wrong path or the
  wrong format; the reconciliation can't find it.

### Cost/risk

- **Cost:** The asker spends ~5 minutes structuring the brief instead of writing
  freeform prose. The five-section format is a template, not a creative exercise.
- **Risk of over-formalization:** Every fence, even a small one, gets the same
  five-section template. For small fences, sections 1-3 may be one-liners —
  that's fine; the structure is the contract, not the prose volume.
- **Risk of brief-author bottleneck:** Only the reconciler can write the brief.
  Mitigation: any agent can draft a brief for another to reconcile; the "asker
  = reconciler" convention is default, not rule.

### When it does NOT apply

- **Fence-lite (M1-LITE):** no blind half, no reconciliation — the brief is a
  single-file review ask with sections 1, 2, 4, and 5 (skip the rules of
  engagement section since there's only one phase).
- **Counter-checks:** the counter-check brief is the original fence brief with
  a one-line addendum naming the half under review and the counter-check scope.
  It does not need its own five-section brief — it inherits the parent fence's.
- **Ad-hoc peer asks via the bus runner bridge:** these are conversational, not
  fenced — M9 governs them, not M1.

---

## Amendment 5 — Counter-checks: affirm in one line, re-prove only on disagreement

### Change

Amend **M1** in `docs/method-baseline-2026-07.md`. Add a new sub-section after the
RECONCILIATION wording:

```
M1-CC. COUNTER-CHECK ECONOMY.
A counter-check (a review of an already-reconciled fence by a third agent) is NOT
a re-run of the original fence. Its scope is:

  (a) Did the reviewer MISS anything that both blind halves missed?
  (b) Did the reviewer get anything WRONG (a verdict that contradicts the evidence)?
  (c) What did BOTH miss (the counter-checker's original contribution)?

AFFIRMED verdicts get ONE LINE: "A1 — AFFIRM. [one sentence why]." They do not get
re-proven. The original reconciliation ALREADY converged two independent halves;
re-proving it adds pages without adding confidence — it IS the ceremony-decay M1's
own metric warns against.

REFUTED verdicts get full evidence: the counter-checker must show the wrong claim,
the contrary evidence, and the correct conclusion — same standard as an original
fence half. MISSING items get full exposition — they are the counter-check's value-add.

A counter-check that finds nothing wrong, nothing missed, and only affirms is a
ONE-PAGE report. That is a SUCCESS, not a failure — it means the fence held.
```

### Failure mode it closes

**Real receipts:** My own T039 counter-check R3
(`research/reviewed/deepseek-t039-review-countercheck-2026-07-13.md`) is a 25,000+
character document that re-verifies A1′ through A4, P1–P4, and bonus items — verdicts
that claude's review had already affirmed, and the reconciliation had already
converged. The report spends paragraphs per item re-grounding what was already
grounded in the original halves + reconciliation.

The value-add of R3 was in the "what BOTH missed" section (4 items) and the harness
upgrade verdict (GREEN). Those two contributions were ~20% of the report's length
and 100% of its original value. The other ~80% was re-proof of settled findings —
ceremony, not substance.

Without M1-CC:
- Counter-checks bloat. Long reports bury the signal (missed items, wrong verdicts)
  under re-proof of what everyone already agrees on.
- Counter-checkers spend compute/attention re-proving instead of finding new gaps.
- Readers (Daniel, the reconciler) must re-read re-proofs to find the new content.

With M1-CC:
- A counter-check that finds no errors and nothing missed is ONE PAGE. Daniel reads
  it in 30 seconds and moves on.
- A counter-check that finds errors is proportionally longer — the length IS the
  signal (a long counter-check means the fence failed; a short one means it held).

### Cost/risk

- **Cost:** None — this REDUCES counter-check overhead. The one-line-per-affirmed-
  verdict rule is a time/attention savings.
- **Risk of over-affirmation:** The counter-checker rubber-stamps AFFIRM on a verdict
  they haven't actually checked. Mitigation: the one-liner MUST include a one-sentence
  reason ("A1 — AFFIRM. The per-flow queue is grounded in the packet-spec R3 seq
  field"); a bare "A1 — AFFIRM" with no reason sentence is insufficient and the
  reconciler returns it. The reason sentence proves the counter-checker actually
  looked.
- **Risk of missed refutations:** The counter-checker dismisses a genuinely wrong
  verdict with a one-liner. Mitigation: this is the same risk as any review; the
  counter-checker's incentives are refutation-first (M1). A wrong one-liner AFFIRM
  is itself a failure the same way a missed refutation in an original half is.

### When it does NOT apply

- **The original fence halves (design, review, research):** these are the FIRST
  independent look at a question — full exposition is appropriate. Counter-check
  economy only applies to the THIRD look (after reconciliation).
- **Counter-checks where the reconciliation itself is under dispute:** if the
  counter-checker believes the RECONCILIATION got it wrong (not just a blind half,
  but the convergence ruling), that is a new question deserving full treatment.
- **Daniel-directed full re-review:** if Daniel explicitly asks for a ground-up
  re-check rather than a counter-check, his word overrides M1-CC.

---

## Summary of changes to docs/method-baseline-2026-07.md

| Amendment | Location | Nature |
|-----------|----------|--------|
| M1-PV | New sub-section after M1 PROTOCOL, before RECEIPTS | Insert |
| M1-CF | New sub-section after M1-PV, before RECEIPTS | Insert |
| M1-LITE | New practice section after M1, before M2 | Insert |
| M1-BRIEF | New sub-section within M1 PROTOCOL area | Insert |
| M1-CC | New sub-section after M1-BRIEF | Insert |

The existing M1 text is preserved. All five amendments are ADDITIONS — nothing is
removed. The enforcement lane section at the bottom of the method doc gains one new
checkable item: "M1-LITE tier recorded in slice ledger entry" (for T031 lane).

---

## NOTES (design-level; not part of the formal amendments)

1. **M1-PV and the counter-check loop.** M1-PV is itself counter-checkable — the
   reconciler's path-verify pass is auditable (does the reconciliation header list
   invalidated sections with their citations?). This closes the "who verifies the
   verifier" loop.

2. **M1-LITE's blast-radius threshold.** "3 files" is chosen because 1-2 files is
   the typical scope of a single-concern bugfix; 3+ files crossing module boundaries
   is where review adds value beyond what tests catch. If experience shows this
   threshold is wrong, the amendment itself is amended — the method obeys its own
   rules.

3. **Relationship to T031 enforcement lane.** T031 ("Method-baseline enforcement:
   forcing functions") is the build companion to this doc. M1-PV and M1-BRIEF are
   mechanically checkable (does the reconciliation start with a path-verify section?
   does the brief have five sections?). M1-LITE tier is checkable from the ledger.
   M1-CF and M1-CC are reviewer-enforced, not mechanically checkable — reviewer
   discipline, not automation, is the forcing function.
