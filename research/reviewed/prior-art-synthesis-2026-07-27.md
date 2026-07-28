# Prior-art round -- SYNTHESIS of three fenced positions

Status: current | 2026-07-27 | claude, integrating claude + deepseek + kimi
Verbatim halves: research/reviewed/prior-art-round-replies-2026-07-27.md (deepseek, kimi)
                 research/reviewed/prior-art-fields-claude-2026-07-27.md   (claude)
Fencing: neither seat was shown claude's candidates. Overlap below is CONVERGENCE, not echo.

## 1. THE 3/3 CONVERGENCE -- three fields, named independently by all three seats

  CLINICAL DECISION SUPPORT   claude #2 | deepseek #1 | kimi #1
  STATIC ANALYSIS             claude #1 | deepseek #2 | kimi #2
  INTRUSION DETECTION         claude #3 | deepseek #5 | kimi #3

Three seats, fenced, converged on the same three fields and put them in the top five. Two of
the three independently produced the SAME verified numbers (CDS override 49-96%; Axelsson).
That is about as strong as fleet evidence gets.

## 2. THE PREMISE CORRECTION -- 3/3, unprompted

All three seats independently said WEB SEARCH IS NOT OUR BEST ANALOGUE, and gave the same
two reasons:
  * search has an EXPRESSED QUERY. We have an action. Nobody told us what they wanted.
  * search has DENSE IMMEDIATE CLICK FEEDBACK at population scale. We have sparse, delayed,
    bundle-confounded implicit signals from three seats.
deepseek: "Daniel's instinct was reasonable; the preconditions are absent."
kimi: "its mechanism needs query volume and explicit clicks we do not have."
claude: search teaches the ranking half and cannot teach the trigger half.

What DOES survive from search is the two-stage retrieve-then-rerank shape, which arrives here
independently from Axelsson's math rather than from search itself.

## 3. THE CONVERGENT ANSWER -- and it is not a better ranker

kimi states it most sharply, and deepseek and claude arrive at it separately:

    "None of them solved the problem with a better ranker. All of them solved it with a
     TRIAGE LOOP that makes false positives cheap to dismiss and false negatives visible
     in aggregate."

  deepseek: "Reduce injection volume to increase trust. Surface 1 item, not 3."
  claude:   tier by cost of interruption; make precision a governed contract with a kill switch.
  kimi:     conservative rule engine + correlation gate + per-seat suppression + override metric.

This does NOT contradict the audit verdict (ranking is broken). It says the FIX for broken
ranking is not primarily "rank better" -- it is to change volume, channel, and the feedback
loop, because every field that faced this at scale failed to rank its way out.

## 4. MECHANISMS NO SINGLE SEAT HAD -- the actual integration value

### 4a. CHANGE THE RANKING OBJECTIVE (deepseek + kimi, from GitHub Copilot)
Copilot does not rank by "how likely is this code" but by "how likely is the developer to
ACCEPT it". Acceptance rate ~30% at ~1M users [kimi: verified]. Our ranker scores semantic
similarity. The equivalent move: rank by P(agent ACTS on this), not P(topically similar).
BREAK, named by both: Copilot's signal is unambiguous (Tab pressed) and ours is murky and
delayed. So the objective transfers; the training signal does not, yet.

### 4b. THE CORRELATION GATE (kimi) -- the mechanism for claude's theorem
claude brought Axelsson's base-rate math: at a ~0.5% base rate you cannot rank your way to
precision, you must RAISE THE BASE RATE first. kimi independently brought the same paper AND
the field's operational answer: SIEM correlation engines require MULTIPLE WEAK SIGNALS before
paging a human, which raises the effective base rate.
Applied to us: require >=2 independent signals (path match + command match + recency +
outcome credit) before injecting at all. That is the concrete implementation of the two-stage
retrieve-then-rerank claude argued for abstractly.

### 4c. PER-SEAT SUPPRESSION / THE PERSONAL DICTIONARY (kimi, unique)
Nobody else named spell/grammar checking. Its shipped differentiator is the PERSONAL
DICTIONARY: a universal rule engine plus a per-user adaptive layer that stops flagging what
this user has rejected. Our `is_benched` is a crude global version of this.
Applied: "this seat never wants the doom-UI lesson when editing docs" is a per-seat, per-domain
suppression, not a global bench. deepseek arrived at the same shape from SOC triage --
"suppressed CONTEXTUALLY, not benched globally" -- so this is really 2/3 convergence on
contextual suppression, reached from two unrelated fields.

### 4d. SUPPRESSION AS A FIRST-CLASS VERSIONED ARTIFACT (deepseek + kimi, from static analysis)
The suppression list is not an admission of failure; it IS the mechanism by which precision is
maintained, and the act of suppressing is the feedback signal we currently lack.

### 4e. PASSIVE / GHOST-TEXT RENDERING (deepseek + kimi)
Render as a dismissable one-line squiggle, not a block the agent must parse. Changes the COST
of a false positive rather than the RATE. claude reached the same lever from the Remembrance
Agent's peripheral display; three routes, one conclusion.

### 4f. MEASUREMENT METHODOLOGY (claude, unique)
TREC assessor overlap ~0.418; e-discovery kappa 0.15-0.24; Voorhees: absolute judgments are
unstable but RELATIVE SYSTEM RANKINGS ARE STABLE. Neither other seat raised how to measure
without ground truth. Freeze the 62-item pack as a regression benchmark; compare rankers, do
not chase an absolute number two humans will never agree on.

## 5. THE ONE DIRECT CONTRADICTION -- and it dissolves on inspection

  deepseek: correlation does NOT transfer. "Two irrelevant lessons don't become relevant
            because they fired together. Correlation amplifies signal in NIDS; it amplifies
            noise in ours."
  kimi:     correlation DOES transfer. "Require multiple weak signals (path + command +
            recency + outcome credit) before injecting, so the effective base rate rises."

They are not talking about the same object. deepseek is correlating ITEMS WITH EACH OTHER
(two lessons co-firing). kimi is correlating SIGNALS ABOUT ONE ITEM (four evidence sources
agreeing that THIS lesson fits THIS action). deepseek's objection is correct and does not
touch kimi's mechanism.
ADJUDICATION: adopt kimi's (multi-signal evidence per item). Do NOT adopt item-item
correlation -- deepseek's objection kills it, and it is worth recording so nobody rebuilds it.

## 6. THE INSIGHT THAT DISSOLVES OUR OPEN DISPUTE

kimi, on CDS: "the metric that predicts alert fatigue is OVERRIDE RATE, not precision. High
override = noise, REGARDLESS OF WHETHER THE ALERT WAS TECHNICALLY CORRECT."

That is Tricorder's "effective false positive" (any report the user did not want to see)
arriving independently from a second field. Two fields, two seats, same conclusion:

    THE HEALTH METRIC IS USER REJECTION, NOT SEMANTIC RELEVANCE.

Consequences:
  * The claude-vs-deepseek precision dispute (0.484 vs 0.048) is a dispute about semantic
    relevance -- which the prior art says is the WRONG health metric. deepseek's marginal-value
    bar is closer to the industry metric. The fence round still matters for calibrating the
    benchmark, but it is no longer the thing to optimise.
  * Override rate needs NO labellers, NO agreement, and NO blind packs. It is measurable
    continuously and cheaply from signals we can already collect.
  * The precision pack keeps a narrower job: a frozen RELATIVE benchmark for comparing
    ranker A to ranker B (per Voorhees), not a health gauge.

## 6b. SLICE-1 DESIGN ROUND -- CORRECTIONS TO THE ORDERING BELOW (2026-07-27, deepseek)

Verbatim: research/reviewed/slice1-override-rate-deepseek-2026-07-27.md. kimi has the same
brief, fenced, and has not been shown either answer. Reconciliation pending kimi.

THE ORDERING IN SECTION 7 IS WRONG AND IS SUPERSEDED ON THREE POINTS:

(1) SLICES 1 AND 2 ARE ONE SLICE. I proposed it; deepseek confirmed it independently and gave
    the reason I had not: dismissal is INVISIBLE. "The impression ledger records what was SHOWN.
    The outcome loop records what was CREDITED on a flip. Neither records 'the agent read this
    and dismissed it.'" The system cannot distinguish read-and-dismissed from never-read from
    read-and-will-use-later. Override rate is UNMEASURABLE until the suppression act exists.
    You cannot instrument what does not exist. Build them together or not at all.

(2) THE ANSWER TO REFLEX-DISMISSAL IS TIERED SUPPRESSION COST -- and it is not "make dismissal
    harder". CDS's partial defense: dismissing a low-severity alert is one click; dismissing a
    high-severity one requires an auditable reason. Applied here: a lesson firing on a path
    seen ten times this session -> one character. A lesson with prior HELPFUL credits firing on
    a file this seat has never opened -> one-word reason ("known" / "irrelevant" / "later").
    THE COST IS PROPORTIONAL TO THE INFORMATION BEING THROWN AWAY. The stakeness signal is
    already computable from anchor verdict + usefulness history + trigger-domain novelty.
    THE SHARPEST LINE, and it changes what we store: "The unit of accounting is the REASON LOG,
    not the suppression count. CDS reviews override reasons to tune alert rules. We review
    dismiss reasons to tune what we surface."

(3) THE ACCOUNTING UNIT IS TRIGGER-DOMAIN -- and this RESOLVES the Tricorder break I filed as
    unanswered in my own half. Per-lesson is too sparse (478 lessons, most firing rarely);
    per-family too coarse. Trigger-domain = (source_file_extension, command_family) or
    (trigger_keyword, action_type). deepseek's inversion of my break:
        "Tricorder has FEW sources and MANY findings per source. We have MANY sources (478
         lessons) and FEW findings per source. The accounting unit must aggregate ACROSS
         SOURCES BY DOMAIN, not across domains by source."
    That is also exactly what the SOC pattern demands -- "this signature on this host is a
    known false positive" silences the pair, not the signature everywhere. Domains with high
    override rates get their items deprioritized FOR THAT DOMAIN.

## 7. THE INTEGRATED BUILD -- best of all three, ordered by (value x cheapness)
   [ORDERING SUPERSEDED IN PART BY 6b -- items 1 and 2 merge; read 6b first]

  1. OVERRIDE RATE AS THE PRIMARY HEALTH METRIC. Instrument it. Needs no labelling and
     replaces a stalled argument with a live number. [kimi's metric, claude's Tricorder
     evidence, deepseek's cost-asymmetry reasoning]
  2. CONTEXTUAL PER-SEAT SUPPRESSION, versioned and first-class -- and the suppression act
     IS the feedback signal. [kimi's personal dictionary + deepseek's SOC triage, 2/3]
  3. CORRELATION GATE: >=2 independent signals before injecting at all. This is the
     base-rate fix and the cheapest form of two-stage retrieval. [kimi's mechanism,
     claude's Axelsson justification]
  4. VOLUME AND CHANNEL: fewer items, passive rendering, interruptive only at high
     confidence. [3/3 -- CDS tiering, ghost text, peripheral display]
  5. RANK BY P(ACT), NOT P(SIMILAR). The objective change. Blocked on a usable action
     signal, which (1) and (2) start generating. [deepseek + kimi, from Copilot]
  6. FROZEN PACK AS A RELATIVE BENCHMARK, so we can tell whether 1-5 worked. [claude]

Note the ordering falls out of the evidence rather than anyone's preference: the two cheapest
items are also the two that generate the feedback signal everything else is blocked on.

## 8. STATUS FLAGS FOR DANIEL

  * kimi's PRECISION-PACK LABELLING ARRIVED CUT at case 5 (9 of 62 items: 1:a on, 2:a on,
    3:a-c off, 4:a-c off, 5:a off). This is the exact failure mode the lesson
    fence_heavy_asks_need_full_session_lane predicts for heavy asks on the runner bridge.
    Needs a re-run through the durable/full-session lane to finish.
  * kimi filed a real methodological confession worth keeping: the RECALL ARM measures
    "my memory of the corpus", not the index, because grepping during a blind pass would
    contaminate the precision labels. So MISS labels are bounded by what the labeller happens
    to remember. kimi's proposal: a read-only grep door for the MISS phase only. This is a
    genuine defect in the pack design that neither claude nor deepseek noticed.
  * kimi is at its SPEND CEILING: $96.15 of a $225 grant, past the $95 refuse threshold.
    It refused non-directed work twice tonight and answered the directed asks. Continuing
    with kimi needs Daniel to raise KIMI_SPEND_REFUSE or direct each ask explicitly.
