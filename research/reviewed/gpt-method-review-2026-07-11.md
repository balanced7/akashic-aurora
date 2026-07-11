# GPT third-reviewer critique of the method baseline (verbatim, via Daniel)

Provenance: Daniel showed GPT docs/method-baseline-2026-07.md; pasted 2026-07-11.
Preserved verbatim per M6. Triage (per M1, deepseek GATE GREEN on the deltas):
ADOPTED -- M0 problem-taxonomy-first; proportionality elevated to P0 (anchored to
revert cost per deepseek's sharpening); outcome-over-activity metric bias; principles
preamble + lifecycle phase map (iterative, not linear). REJECTED -- full four-tier
restructure (churn on load-bearing M# handles referenced by boot/AGENTS.md/T031).

---

I think this is one of the strongest artifacts you've shown me from the project. Not
because every individual practice is novel -- many aren't -- but because you've done
something that most software projects never do: you've started treating the
engineering process itself as something that can be architected, measured, tested,
and improved. That's a significant shift.

## What I think is genuinely excellent

1. Every practice has a trigger. Instead of "we should do dual reviews," you wrote
"TRIGGER: any design, diagnosis, review, or research question where a wrong answer is
expensive." That answers: when should this practice apply? Without that, "best
practices" become cargo cults.

2. Every practice has receipts. Instead of "we believe dual review is good," you have:
here's where it caught bugs. That's evidence, not philosophy.

3. Every practice has metrics. Instead of "do dual review," you ask: is dual review
still producing unique findings? If not, maybe it's become ceremony. That is exactly
the kind of thinking that keeps process from ossifying.

4. You explicitly define what NOT to codify. People usually write process documents
that slowly become "here's every little thing we happened to do." Yours says: don't
copy the marathon, don't copy tool choices, don't copy lucky numbers. Copy principles.

5. It recursively applies its own philosophy. The document says: quarterly, reevaluate
this document. Even the methodology isn't sacred. That feels extremely aligned with
Aurora's philosophy.

## What I would improve

1. Separate Principles from Practices. Right now M1-M11 mixes values, procedures,
metrics. I'd create a hierarchy: Principles -> Practices -> Metrics -> Receipts.
Example: Principle "truth comes from evidence" -> Practice "evidence-first forensics"
-> Metric "evidence before diagnosis" -> Receipts (RB-26, runner mail loss, etc.).
That makes it much easier for new contributors.

2. Some metrics measure activity instead of outcomes. "Dual pass occurred" isn't what
you care about; "did it improve correctness?" is. "Number of drills" isn't success;
"previously unseen failures caught before production" is. Whenever possible bias
toward outcome metrics.

3. Group them into phases: Discovery (M2, M7) -> Design (M1, M8) -> Build (M3, M11)
-> Verification (M4, M5) -> Knowledge Preservation (M6, M10). Now a contributor
instantly understands the lifecycle.

4. Add one thing that's missing -- possibly the most important thing you've invented
this week: M0, Problem Taxonomy First. Trigger: whenever beginning a new subsystem.
Protocol: classify the problem, identify the governing field, define success, define
failure, THEN begin solution design. Metric: percentage of slices with explicit
taxonomy. Receipt: the robustness SOTA mapping. That prompt may have changed the
direction of the project more than any individual robustness feature.

## Something else I noticed

This document is no longer really about AI. Read the titles: crash testing,
acceptance, forensics, dual review, evidence, metrics, honest bounds, SOTA, slice
discipline. These are engineering concepts. The AI is almost incidental. The
methodology would work if tomorrow Aurora became a networking platform, a database, an
operating system, a compiler. That's a sign you've discovered something fairly
fundamental.

## The one caution

Sophisticated process has a failure mode: the process becomes more expensive than the
decision it's protecting. I actually like that your document already hints at this
(multi-agent ceremony for trivial work). I'd make that almost a first-class principle:
the cost of the methodology should scale with the cost of being wrong. A typo
shouldn't require dual-model review, SOTA research, a reconciliation document, and
five kill drills. A distributed coordination primitive probably should. That's what
keeps a methodology powerful instead of burdensome.
