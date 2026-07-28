# Who else has this problem, and solved it at scale -- claude's position

Status: current | 2026-07-27 | claude (fresh Opus 5 seat)
Daniel's ask, verbatim: "Which real world system faces the same challenges and has a proven
solution that works at scale with precision and accuracy. I am thinking the field of web search
engines and rankings has something to teach us, what other fields or engineering tasks also have
the same problem as us?"

Filed INDEPENDENTLY, before kimi's and deepseek's answers arrived (asks sent 2026-07-27 ~20:12,
neither seat was told my candidates). Figures marked [VERIFIED] were checked live against the
literature this session; [MEMORY] means I am reciting and have NOT re-checked.

## THE SHAPE WE ARE MATCHING ON

Unrequested advisory injection at the moment of action, from a large corpus, into a working
professional's context, with a hard latency budget, a ~0.5% base rate of truly-relevant items,
implicit-only feedback, and TRUST as the currency that a false positive spends.

Note what this is NOT: it is not search. Nobody typed a query. That single difference is why
Daniel's instinct is right about the *ranking* half and incomplete about the *trigger* half --
the fields below that share the no-query property transfer more mechanism than search does.

## A-TIER -- the mechanism transfers

### 1. Static analysis at scale (Google Tricorder; Coverity) -- THE CLOSEST ENGINEERING MATCH

Advisory fired at a work site, unrequested, where precision governs whether the tool survives.

MECHANISM SHIPPED:
  * "EFFECTIVE FALSE POSITIVE" -- defined USER-CENTRICALLY: a false positive is any report the
    user did not want to see, regardless of whether the finding is technically correct. [VERIFIED]
  * A "NOT USEFUL" button in the UI; the FP rate is continuously monitored from it. [VERIFIED]
  * A CONTRACT WITH A KILL SWITCH: analyzer authors must keep the FP rate low enough, and the
    threat of having their analyzer DISABLED is what keeps them motivated. [VERIFIED]
  * Tricorder's overall effective FP rate runs JUST UNDER 5%. [VERIFIED]

WHY IT MATTERS TO US IMMEDIATELY: that user-centric definition ADJUDICATES OUR OPEN FENCE
ROUND, and it does so against my own labelling. deepseek marked items off that were topically
on-point but told the agent nothing it needed; I marked them on. The industry that actually
solved this at scale scores it deepseek's way -- "did the user want to see it" IS the metric.
Under that bar our effective FP rate is ~95% against a 5% tolerated ceiling: a ~19x gap.
My 0.484 answers "was it topically relevant"; deepseek's 0.048 answers "was this tool worth
firing". The second is the product question.

WHERE THE ANALOGY BREAKS: Tricorder governs DOZENS of analyzers, each firing constantly, so
per-analyzer FP statistics converge fast. We have 475 lessons each firing rarely -- per-item
statistics will be sparse and slow. The unit of accounting must therefore be a RULE or FAMILY,
not an individual lesson. Copying per-item accounting would give us noise-driven kill decisions.

### 2. Clinical decision support / drug-drug interaction alerting -- THE STRUCTURAL TWIN

Fires at the moment of action (physician places an order), unrequested, professional in the
loop, and the documented failure mode is exactly ours: trust collapse.

EVIDENCE AT SCALE:
  * Meta-analysis: overall physician override rate for DDI alerts 90% (CI95% 85-95%). [VERIFIED]
  * 88.2% of VERY SEVERE DDI alerts overridden -- severity alone does not buy attention. [VERIFIED]
  * Reported override ranges across settings: 49-96%. [VERIFIED]

So a multi-decade, heavily-funded, safety-critical field runs at roughly 10% precision. This is
the sharpest calibration available for how hard our problem actually is -- and a warning that
"just rank better" has not worked for people with far more resources than us.

MECHANISM SHIPPED (what did help): tiering alerts by severity into INTERRUPTIVE vs PASSIVE vs
logged-only; suppressing alerts already acknowledged for that patient; and tailoring by
CLINICAL ROLE -- a pharmacist and a prescriber get different alerts. [VERIFIED, systematic review]

TRANSFERS: our recall is single-tier and always interruptive. Every lesson arrives at the same
volume in the same channel. Tiering is the highest-value structural change available to us and
it is orthogonal to ranking quality -- it pays off even if the ranker never improves.

WHERE THE ANALOGY BREAKS: medicine has an EXTERNAL severity ontology (drug classes,
contraindication grades) authored by domain bodies. We have no such ontology; we would have to
DERIVE severity from our own corpus, which is a design problem, not a copy. Do not assume the
tiering is free.

### 3. Intrusion detection and the base-rate fallacy (Axelsson, ACM TISSEC 2000) -- THE MATH

Not a solution. The theorem that tells you what to aim at, and it is the strongest argument in
this document.

  "The false alarm rate is the limiting factor for the performance of an intrusion detection
  system. In order to achieve substantial values of the Bayesian detection rate P(Intrusion|
  Alarm), we have to achieve a perhaps unattainably low false alarm rate." [VERIFIED]

Their skew (overwhelming benign traffic, few intrusions) is our skew (475 lessons, 1-3 relevant
per action, ~0.5% base rate). The consequence is architectural, not incremental: at a 0.5% base
rate, NO amount of better scoring over the full corpus reaches high precision. You must RAISE
THE BASE RATE BEFORE YOU RANK.

That is precisely the two-stage RETRIEVE-THEN-RERANK architecture web search converged on
independently -- cheap high-recall candidate generation, then expensive precision reranking over
a small pool. Daniel's search intuition and this theorem point at the same build. It is the
single most defensible next move.

WHERE THE ANALOGY BREAKS: IDS gets to define "intrusion" crisply; our "relevant" is exactly
what two labellers just disagreed 10x about. The math holds regardless, but our estimate of the
base rate inherits the bar dispute.

### 4. IR evaluation methodology (TREC; e-discovery TAR) -- SETTLES OUR MEASUREMENT, NOT OUR RANKER

This field's contribution is not a better ranker. It is the discovery that OUR CURRENT ARGUMENT
IS A KNOWN, EXPECTED PHENOMENON WITH ESTABLISHED METHODOLOGY.

  * TREC mean assessor OVERLAP across topics ~0.418. [VERIFIED]
  * E-discovery (Roitblat et al. 2010): inter-assessor kappa 0.15-0.24 between pairs of
    LEGALLY TRAINED reviewers. [VERIFIED]
  * Our claude-vs-deepseek agreement is 0.532 -- ABOVE TREC's mean. Our disagreement is not a
    process failure. It is the normal condition of relevance judgment.
  * Voorhees' load-bearing result: despite low overlap and wide per-topic variation, THE RELATIVE
    RANKING OF SYSTEMS IS STABLE across independent assessor sets -- "the relative effectiveness
    of different retrieval strategies is stable despite marked differences in the relevance
    judgments used to define perfect retrieval." [VERIFIED]
  * A practical human-agreement ceiling is cited at ~65% precision at 65% recall. [VERIFIED]

TWO CONSEQUENCES, both actionable now:
  (a) STOP TRYING TO SETTLE THE ABSOLUTE NUMBER. Freeze the 62-item pack as a REGRESSION
      BENCHMARK and use it to compare ranker A against ranker B. Under Voorhees, the assessor
      disagreement largely CANCELS in a relative comparison. This converts our stalled dispute
      into a working instrument without resolving it.
  (b) OUR PRE-REGISTERED 0.80 THRESHOLD IS ABOVE THE HUMAN AGREEMENT CEILING (~65%). The
      "SELECTION was the constraint" branch may have been unreachable BY CONSTRUCTION. That does
      not change this audit's verdict (both labellers came in under 0.60, and the verdict only
      needed the < 0.60 branch) but it means the threshold set should be re-derived before it is
      used to declare victory later.

## B-TIER -- worth mining, weaker or unverified transfer

### 5. Industrial alarm management (EEMUA 191 / ISA 18.2) -- post-Three-Mile-Island engineering
The principle worth stealing is ALARM RATIONALIZATION: every alarm must have a DEFINED OPERATOR
RESPONSE, or it is deleted. [MEMORY -- principle recited, specific rate limits NOT verified]
Adoptable as a WRITE-SIDE gate: a lesson that does not name a distinct action the agent would
take differently should not be injectable at all. That attacks supply, where everything else
here attacks ranking, and it is cheap.

### 6. Just-in-time IR / Remembrance Agent (Rhodes & Maes, MIT) -- our direct ancestor
Watched what the user typed and continuously surfaced old documents in a PERIPHERAL margin
window. [MEMORY -- not verified this session] Its contribution is the CHANNEL, not the ranker:
a non-interruptive peripheral display changes the cost of a false positive by an order of
magnitude, which is the same lever as CDSS tiering arriving from a different direction.

### 7. Feedback-directed prefetching (CPU microarchitecture)
Measure prefetch accuracy online; THROTTLE aggressiveness when accuracy drops. [MEMORY]
Maps cleanly onto us: when measured precision is low, inject FEWER items. We already have
"silent when starved"; this generalises it to "quieter when imprecise" -- a control loop rather
than a fixed limit of 3.

## THE CONVERGENCE -- what to actually build

Four independent fields, with no contact between them, converged on the same three-part shape.
That convergence is the finding, more than any single field:

  1. RAISE THE BASE RATE BEFORE RANKING.  Two-stage retrieve-then-rerank.
     (web search, and forced by Axelsson's math)
  2. TIER BY COST OF INTERRUPTION.  Not everything fires at the same volume in the same channel.
     (CDSS severity tiers; alarm rationalization; peripheral display)
  3. MAKE PRECISION A GOVERNED CONTRACT WITH A KILL SWITCH, fed by user feedback.
     (Tricorder's disable-the-analyzer; alarm rationalization's delete-the-alarm)

Plus one meta-rule from IR evaluation: measure RELATIVE, not absolute. Freeze the pack, compare
systems, do not chase a true number that the literature says two humans will never agree on.

Ranked by (value x cheapness) for us right now:
  FIRST   (3) the governed contract -- we ALREADY have the feedback door (recall-feedback,
          useful/noise votes). What is missing is the CONTRACT that acts on it. Least new code.
  SECOND  (2) tiering -- orthogonal to ranker quality, pays off even if ranking never improves.
  THIRD   (1) two-stage retrieval -- the biggest win and the biggest build; it is what the audit
          verdict actually calls for.
  ALWAYS  the frozen-pack relative benchmark, because without it we cannot tell whether any of
          the above worked.

## SOURCES

Tricorder / effective false positives:
  https://cacm.acm.org/research/lessons-from-building-static-analysis-tools-at-google/
  https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43322.pdf
  https://abseil.io/resources/swe-book/html/ch20.html
CDSS override rates / alert fatigue:
  https://journals.sagepub.com/doi/10.1177/14604582241263242
  https://academic.oup.com/jamia/article/26/10/1141/5519579
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7400042/
Base-rate fallacy:
  https://dl.acm.org/doi/10.1145/357830.357849
Assessor disagreement:
  https://ediscovery.umiacs.umd.edu/talks/unc12.pdf
  https://dl.acm.org/doi/10.1145/2348283.2348465
