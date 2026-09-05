---
akashic_id: art_20260905_t392-arm-d-reliability-engineering_b96776
akashic_sha: a68b08e00269
schema_version: 1
status: current
type: report
date: 2026-09-05
title: t392-arm-d-reliability-engineering
gist: "# T392 · Arm D — reliability & resilience engineering (external literature) *Web research arm, 2026-09-05. Sources marked read-directly vs c"
visibility: fleet
body_type: markdown
seats: []
category: [memory, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-05T01:02:34"
updated: "2026-09-05T01:02:34"
---
<!-- GENERATED PROJECTION of art_20260905_t392-arm-d-reliability-engineering_b96776 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t392-arm-d-reliability-engineering

# T392 · Arm D — reliability & resilience engineering (external literature)

*Web research arm, 2026-09-05. Sources marked read-directly vs citation-verified-paywalled in
the original; the agent deliberately withheld statistics it could not verify rather than
reproduce them from memory. Full source list at the end. Arms B (procedural rigor) and C
(fast-adaptive) were still running when this landed.*

## ETTO — the mechanism behind the operator's question

Hollnagel's principle, stated precisely: *people and organizations routinely choose between
being efficient and being thorough, since it is rarely possible to be both at the same time.*

The terms are defined against a specific act, which is what makes it a real trade and not a
tension: **thoroughness** = verifying conditions/preconditions/resources are adequate BEFORE
acting; **efficiency** = keeping effort/time/resources as low as compatible with the goal.
They compete for the same finite resource — attention *before* the act. **Thoroughness is
purchased in the exact currency efficiency is conserving.**

**Individual ETTO rules** (the licences people actually use): *"it will be checked later by
someone else" · "it has been checked earlier by someone else" · "it looks like a Y so it
probably is a Y" · "it normally works / it's been OK before" · "we always do it this way."*

**Collective/organizational rules:** **negative reporting** (absence of a report taken as
everything-fine — converts silence into positive evidence of safety at zero cost, the purest
efficiency gain and the most dangerous); cost-reduction imperatives; **double-binds** (explicit
"safety first", implicit "production wins when goals conflict" — the conflict management
declined to resolve gets resolved at the sharp end).

**The three claims that make ETTO more than obvious:**
1. **The trade-off is necessary, not defective.** A system where every actor was maximally
   thorough would not be safe, it would be STOPPED. Guidelines followed slavishly and
   continuously "would lead to systems shut-down."
2. **The same trade-off produces success and failure.** The ETTO that caused the incident is
   the one that got the work done the previous four hundred times. There is no separate
   population of bad shortcuts to eliminate.
3. **The ETTO fallacy** — *"that people are required to be both efficient and thorough at the
   same time — or rather to be thorough when with hindsight it was wrong to be efficient."*
   Two halves: demanding both is incoherent (and delegates an unresolved conflict downward);
   and the demand is made *retrospectively and selectively*, only where outcomes were bad —
   so **the standard actually enforced is not "be thorough", it is "be lucky."**

**Why efficiency wins over time — the ratchet, and this is the load-bearing mechanism:**
- every efficiency gain is **immediate, local, certain, attributable** (you finished early;
  someone noticed);
- every thoroughness expenditure buys a **probabilistic, delayed, diffuse, unobservable**
  benefit — the incident that did not happen produces NO SIGNAL AT ALL;
- so each trade is locally rational and locally rewarded, and the reward for the opposite
  choice is structurally invisible;
- repeated, the operating point migrates monotonically toward efficiency until it touches the
  boundary — and *that* instance is then investigated as a deviation.

This is Rasmussen's migration model; **drift is the integral of ETTOs.**

**The recursion almost everyone misses: your incident analysis is itself an ETTO**, under the
same pressure as the work it examines. Which is why postmortems degrade into templates and
"we'll do a lightweight version this time" is the most predictable sentence in incident review.
(Cf. our own ceremony census: 52 ceremonies, 1 kill loop actually running.)

**ETTO–TETO:** thoroughness and efficiency also trade *across time* — efficient now means
thorough later, or unable to be. **Deferred verification is borrowed thoroughness at
interest** — i.e. technical debt, which software reinvented without noticing the precedent.
(The agent searched: essentially no literature bridges ETTO and software engineering.)

**ETTO's own failure modes:** unfalsifiable as a causal claim (every action is a trade-off);
**it has no scale** — it never tells you where the line should be, and offers no basis for
judging a trade except outcome, which is the reasoning its own fallacy condemns; and it is
weaponizable both ways ("it was an ETTO" excuses anything; "you ETTO'd" blames anything).

## Woods — the formal version, and the theorem that matters

*Woods 2018, "The theory of graceful extensibility", Environment Systems & Decisions 38:433–457.*

- **Brittleness** = how rapidly performance collapses at the boundary — *orthogonal to how well
  the system performs inside its boundaries.*
- **Capacity for Maneuver (CfM)** = remaining room to adapt.
- **S3.1**: the work required to adapt **increases as CfM decreases** — adapting gets harder
  exactly as you have less left. First breakdown pattern: **decompensation**.
- **S7 (the key one): "pressure for optimality undermines graceful extensibility."**
  *"Reducing resources to improve performance far from saturation inadvertently targets
  resources that underlie graceful extensibility when risk of saturation is growing."*
  → **The slack you remove to get efficient in normal operation is the same slack you needed
  to survive abnormal operation. Far from the boundary, reserve and waste look identical.**
- **S10**: models of one's own and others' adaptive capacity are always mis-calibrated;
  *"mis-calibration is the norm."*
- Mechanisms that produce extensibility: **initiative** (adapting without waiting for
  authorization — a unit with reduced initiative "loses its ability to function") and
  **reciprocity** (spending your own resources to extend a saturating neighbour's capacity).

## Kahneman & Klein — the two conditions, and FRACTIONATION

*"Conditions for Intuitive Expertise: A Failure to Disagree", American Psychologist 64(6).*

Skilled intuition requires **both**: (1) an environment of **sufficiently high validity** —
stable relationships between identifiable cues and outcomes; (2) **adequate opportunity to
learn it** — prolonged practice with **rapid and unequivocal** feedback.

Corollary: **"Subjective confidence is an unreliable indication of the validity of intuitive
judgments."** And: *"True experts know when they don't know. However, nonexperts certainly do
not know when they don't know."*

**FRACTIONATION OF EXPERTISE — "the rule, not an exception":** professionals with genuine skill
in some tasks are routinely asked to judge adjacent tasks where they have none, and *"it is
difficult both for the professionals and for those who observe them to determine the boundaries
of their true expertise."* In **wicked environments** the observable regularities are actively
misleading, producing confident and systematically wrong intuitions.

RPD itself is not thoughtless: it uses *"an automatic process that brings promising solutions
to mind and a deliberate activity in which the candidate is mentally simulated in progressive
deepening."* Fast expert judgement is **thought that has been compiled.**

## The five axes of genuine conflict

| | Reliability literature | Expertise literature |
|---|---|---|
| Speed | a hazard; thoroughness costs time and is worth it | the signature of competence; deliberation means recognition failed |
| Deviation from procedure | detect and suppress it | the mechanism by which work succeeds |
| Expert's confidence | not a licence to skip verification | often well-founded, the basis of performance |
| Standardization | reduces variance → reduces harm | reduces variance → reduces adaptive capacity for surprise |
| What to study | the failures | the successes, and what builds skill |

They **agree** on more than advertised: both reject the person approach; both hold subjective
confidence untrustworthy; both regard hindsight-driven judgement of past decisions as invalid.
The real disagreement is narrower: **where on the validity/feedback spectrum a given task
sits** — and neither side routinely asks that before prescribing.

**The empirical collision, checklists:** Haynes NEJM 2009 (8 hospitals) death 1.5%→0.8%,
complications 11.0%→7.0%. Urbach NEJM 2014 (101 hospitals, ~216k procedures) adjusted OR death
**0.91, CI 0.80–1.03, n.s.** Considered reading: **the checklist is not the intervention, the
implementation is.** Where introduced with engagement, local adaptation and ownership it
changed behaviour; where mandated top-down it changed documentation. This is Hale & Borys'
Model 1 (imposed) vs Model 2 (owned, revisable) **with mortality data attached** — the
strongest evidence that procedural rigor imposed without ownership produces compliance
artefacts rather than reliability.

## The seven reconciliations (the answer to "marry the two")

1. **Make rigor a property of the system's structure, not the operator's care.** Forcing
   functions, type systems, irreversible-action guards, blast-radius limits, automated gates
   cost the operator no time and **cannot be traded away under pressure**. "Be careful",
   training, policy, checklists-as-documents are paid for in attention every time and are
   **the first thing ETTO consumes**. *Rigor that lives in the environment is speed-compatible;
   rigor that lives in the operator's discipline is not, and will lose.*
   (Hierarchy of intervention effectiveness: forcing functions & design > automation >
   simplification/standardization > checklists & reminders > training & policy. RCA output
   clusters at the weak end **because weak actions are cheap, fast and assignable** — an ETTO
   in the analysis process itself.)
2. **Change the shape of failure, not its probability.** Progressive rollout, reversibility,
   small batches, fast rollback: go fast *because* the cost of being wrong is bounded. The
   correct reading of DORA is not "speed and stability don't trade off" but **"batch size and
   reversibility dominate the trade-off."** A large irreversible change deployed carefully is
   more dangerous than a small reversible one deployed casually.
3. **Match rigor to the environment's validity — TASK BY TASK, NOT ROLE BY ROLE.** Fractionation
   means the same person needs both regimes within the same hour, so the trigger must attach to
   **task type**, not seniority. *"Most organizations do the opposite: they exempt senior people
   from process, which is exactly backwards, since seniority licenses operating outside one's
   validated fraction."*
4. **Resolve the double-bind explicitly instead of delegating it downward.** The error budget is
   structurally the best existing answer — it states the acceptable failure rate **in advance and
   in public** and pre-commits the consequence. Its failure mode (the override) is the
   organization taking the double-bind back.
5. **Design rules to be owned and revised by their users, and rate them for strength.** Practical
   test: **can the people who follow this rule explain what it protects against, and can they
   change it?** If no to either, it is a compliance artefact and Work-as-Done has already
   diverged.
6. **Monitor capacity for maneuver, not outcome quality.** The only credible *prospective* drift
   detector anyone has proposed. Outcomes stay good right up to the boundary — that is what
   brittle means. Leading indicators: how hard routine things are getting, how often exceptions
   are granted, how much slack is left, how long since the recovery path was exercised. Under
   S7, **every efficiency program should state which reserve it is consuming.**
7. **Semi-formal methods that add rigor without displacing expertise — the PREMORTEM.** The one
   concrete technique Kahneman and Klein *jointly* endorsed: assume the plan has already failed
   catastrophically, two minutes each writing why. Exploits prospective hindsight; counteracts
   *"the gradual suppression of dissenting opinions, doubts and objections typically observed as
   an organization commits to a major plan."* Costs minutes, **draws on expertise rather than
   overriding it.**

**One-line synthesis:** *the efficiency–thoroughness trade-off cannot be won, only relocated.*
You cannot make people be both fast and thorough — that is the fallacy, and enforcing it
retrospectively punishes bad luck. You **move thoroughness out of the moment of action** — into
structure, reversibility, pre-committed budgets, and rules people own — so that acting fast no
longer means acting unverified.

## Other findings worth keeping

- **Bainbridge's irony of automation (1983)**: automating away hands-on contact removes the
  operator's mental model — *"the operator needs to be MORE rather than less skilled, and LESS
  rather than more loaded, than average"* when manual takeover is needed. **Directly bears on
  our instinct to automate the wake re-arm**: the 50% toil cap is defensible as a *load* limit
  and dangerous as an *exposure* target. Some toil is the only remaining contact with ground truth.
- **HRO's evidence is weak**: induced from a small non-random sample of atypical organizations,
  **selected on the dependent variable**, measured by perceptual self-report. Degrades into
  branding; unfalsifiable as stated ("if you had an accident, you were insufficiently mindful").
- **Sagan's *The Limits of Safety*** is the one rigorous head-to-head test (US nuclear C2, Cold
  War near-misses) and it **favoured Perrow**: redundancy sometimes created new failure modes;
  organizations concealed failures rather than learning.
- **Leveson et al. 2009**: abandon both framings — safety is a **control** problem, not a
  reliability problem. **Reliability and safety are different properties and can oppose**: a
  system of perfectly reliable components each doing exactly what specified can still be unsafe.
- **Cook #11**: ambiguity about production vs safety that the organization declined to resolve is
  resolved at the sharp end, under time pressure, by whoever is holding it — who is then held
  accountable for the resolution.
- **WYLFIWYF** (Lundberg/Rollenhagen/Hollnagel 2009): the accident model embedded in an
  investigation method determines what it can find. **The output of an investigation is partly a
  property of its template.**
- **RCA's domain of validity is much narrower than its domain of application, and it fails
  silently rather than loudly outside it.** For tractable componential failures (disk full, cert
  expired) causal chains are real and 5-Whys is efficient.
- **Vaughan's normalization of deviance is routinely inverted**: the deviance was normalized
  *through legitimate, rule-following organizational processes*, not by rule-breaking. She has
  objected to the term's degradation into a blame word.

## Sources

Read directly: Hollnagel/Wears/Braithwaite *Safety-I to Safety-II white paper*
(england.nhs.uk, skybrary.aero) · Woods 2018 *graceful extensibility* (surfingcomplexity.blog
PDF) · Kahneman & Klein 2009 (gwern.net PDF) · Reason 2000 BMJ (PMC1117770) · Cook
*How Complex Systems Fail* (how.complexsystems.fail) · Bainbridge 1983 *Ironies of Automation*
(ckrybus.com PDF) · Dekker restorative just culture (safetydifferently.com) · Safetymatters
ETTO review · Haynes NEJM 2009 (PMID 19144931) & Urbach NEJM 2014 (PMID 24620866) · RAG
applications (Safety Science, PMC9576065).

Citation-verified, paywalled: Hollnagel 2009 *The ETTO Principle* (Routledge) ·
WYLFIWYF doi:10.1016/j.ssci.2009.01.004 · Cooper 2020 critique of Safety-II
doi:10.1016/j.ssci.2020.105047 · Hale & Borys 2012 parts 1&2 doi:10.1016/j.ssci.2012.05.011 /
.013 · Dekker 2003 doi:10.1016/S0003-6870(03)00031-0 · ETTO system-dynamics
doi:10.1016/j.ssci.2019.104542 · Leveson 2009 doi:10.1177/0170840608101478 · Rasmussen 1997
doi:10.1016/S0925-7535(97)00052-0 · Peerally 2017 doi:10.1136/bmjqs-2016-005511 · Kellogg 2017
doi:10.1136/bmjqs-2016-005991 · Google SRE books (sre.google/books) · DORA (dora.dev).
