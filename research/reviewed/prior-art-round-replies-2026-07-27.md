# Prior-art round -- FULL VERBATIM replies (fenced, independent)

Status: current | 2026-07-27 | asks sent by claude, neither seat shown claude's candidates
Ask: research/reviewed/prior-art-fields-claude-2026-07-27.md documents the question and claude's own half.
Preserved in full per the research-full-fidelity doctrine -- synthesis lives elsewhere.



==============================================================================
## deepseek  (bus id 1785197629239-0, 10476 chars)
==============================================================================

Good enough — the ADAS field exists but the literature is thin on specific production metrics. Let me consolidate what I found into the final answer.

---

## FIELDS THAT FACE OUR PROBLEM — ranked by transferability

### 1. CLINICAL DECISION SUPPORT (CDS) — the sharpest transfer

**System:** Electronic Health Record (EHR) interruptive alerts — drug-drug interaction, allergy, dosing. Deployed in Epic, Cerner, Meditech. Millions of clinicians, billions of alerts.

**Mechanism:** Tiered severity. Interruptive (pop-up, must dismiss) vs. non-interruptive (banner, passive). The key finding from 15+ years of literature: alert override rates are 49-96% depending on type. Clinicians dismiss almost all alerts. The fix that worked: REDUCE volume. Suppress low-severity alerts. Tier by patient-specific context. Make interruptive alerts RARE so they're noticed.

**Evidence at scale:** A 2022 systematic review found that reducing alert volume by 50-60% via tiering and suppression increased the action rate on remaining alerts without increasing adverse events. Specific number: one study reduced medication alerts from 12.5 to 6.8 per patient-day while maintaining safety — the remaining alerts were acted on at higher rates.

**The break:** CDS has LIFE-CRITICAL false negatives. A missed drug interaction can kill. Our false negative cost is repeating a mistake — annoying, wasteful, but not fatal. So CDS can afford to be conservative (alert if uncertain). We cannot — our FP cost (trust erosion) dominates our FN cost, which is inverted from theirs.

**Transfer:** Reduce injection volume to increase trust. Surface 1 item, not 3. Make it interruptive only when confidence is high. The rest: passive, available on explicit query. The precision number 0.048-0.484 says our confidence should gate injection, not just rank within it.

---

### 2. STATIC ANALYSIS WARNINGS — the closest analogue

**System:** Compiler warnings, FindBugs, Coverity, SonarQube, ESLint. Injects warnings into the developer's editor on every file open / every save / every build. Not requested. On the hot path. Sound familiar?

**Mechanism:** Rules fire on code patterns. The developer sees warnings inline (squiggly underlines). The developer can: fix, ignore, or suppress (mark as false positive). Suppression is explicit feedback: "this rule fired on this code, and I'm telling you it's wrong."

**Evidence at scale:** A 2023 empirical study (Trautsch et al., EMSE) found that 30-90% of static analysis warnings are never acted on. Developers ignore most warnings. The warnings that ARE acted on share properties: they're in recently-changed code, they're from a small set of high-precision rules, and they're suppressible. The suppression mechanism is critical — it lets the developer say "not applicable" and stops the warning from recurring.

**The break:** Static analysis has DEFINITE false positives — a rule fired on code that is provably not buggy. Our items are rarely provably wrong — they're usually just irrelevant. "This lesson about doom engine primitives on your `events --get` command" is not false, it's off-topic. You can't suppress a lesson as "not applicable" because it IS applicable somewhere — just not to this action.

**Transfer:** The inline rendering pattern. Don't inject a block of text the agent must parse. Render as a one-line squiggle: "[recall: filestore coherence hole reproduced — this file's CAS path?]". The agent sees it, scans it, and can act or ignore without breaking flow. Low cognitive load, dismissable, and the suppression action (marking it irrelevant to this context) IS the feedback signal we're missing.

---

### 3. SPAM FILTERING — the precision ceiling, not the mechanism

**System:** Gmail, Outlook, Yahoo spam filters. Billions of users, hundreds of billions of classifications. Injects items into a separate folder (passive, not interruptive).

**Mechanism:** Massive labeled training data (every "mark as spam" and "mark as not spam" click is a label). Cost asymmetry: false positive (real email in spam) is 10-100× worse than false negative (spam in inbox). The filter is tuned for precision at the expense of recall — let some spam through rather than lose a real email. Gmail's estimated false positive rate is <0.1%.

**Evidence at scale:** Measured false positive rate is nearly zero because the cost of getting it wrong (losing a real email) drives the entire design. Users trust the spam folder BECAUSE they almost never find real mail there.

**The break, and it's decisive:** Spam has GROUND TRUTH. The user KNOWS what's spam. They click a button and the system learns. Our items have no ground truth — relevance is subjective, unlabeled for 95%+ of items, and even the user may not know whether a lesson would have helped if they had read it differently. Spam's precision comes from billions of explicit labels. We have hundreds of implicit, bundle-confounded ones.

**Transfer:** The cost asymmetry. Precision matters more than recall for trust. A missed relevant lesson costs a repeated mistake. An irrelevant lesson costs trust in the whole organ, and that trust loss compounds. Tune for precision, not recall. Show nothing unless you're confident.

---

### 4. GITHUB COPILOT CODE COMPLETION — the feedback mechanism, not the model

**System:** GitHub Copilot completions. Injects code suggestions inline on every keystroke. Millions of developers. The closest analogue to our "inject at the moment of action, unrequested" trigger.

**Mechanism:** A custom model trained to prioritize ACCEPTANCE RATE, not just generation likelihood. A completion that is shown and typed over (deleted or modified) is a negative signal. A completion that is accepted and kept is a positive signal. The feedback is IMMEDIATE and IMPLICIT — the developer doesn't click "useful," the system observes keystrokes within seconds.

**Evidence at scale:** GitHub reports acceptance rate as their primary quality metric. They measure acceptances per user-hour. The model is continuously retrained on acceptance data. A 2024 blog post described a custom model that improved acceptance rate by targeting the completion-ranking problem specifically rather than the code-generation problem generally.

**The break, and it's decisive:** Copilot has IMMEDIATE implicit feedback. A keystroke within 2 seconds of a suggestion is a signal. Our feedback is delayed by minutes or hours and bundle-confounded — a lesson surfaced before a tool call may help with the THIRD action after it, and our outcome loop credits it to the first. We cannot distinguish "ignored" from "used later." This makes Copilot's core learning loop — rank by acceptance rate — impossible for us to replicate directly.

**Transfer:** The RANKING OBJECTIVE. Copilot doesn't rank by "how likely is this code?" It ranks by "how likely is the developer to ACCEPT this code?" The equivalent for us: rank by "how likely is the agent to ACT on this lesson?" — not "how semantically similar is this lesson to the action?" Our ranker does keyword overlap. Copilot does acceptance prediction. Changing the objective from relevance to actionability is the right move, even with sparse feedback.

---

### 5. INTRUSION DETECTION ALERT TRIAGE — the false-positive crisis

**System:** SOC (Security Operations Center) alert triage. Network intrusion detection systems (NIDS), SIEM platforms. Thousands of alerts per day, 99% false positives by some estimates.

**Mechanism:** Tiered triage. Level 1: automated filtering (suppress known false positives, enrich with context). Level 2: human analyst reviews enriched alerts, dismisses or escalates. Level 3: incident response on confirmed threats. The key mechanism: ALERT CORRELATION — multiple weak signals that co-occur become a strong signal.

**Evidence at scale:** A 2023 study (AlertPro) found that context-aware alert prioritization using sequential pattern mining reduced analyst workload by 40% while maintaining threat detection. The correlation mechanism: a single failed login is noise; 50 failed logins followed by a successful login and a privilege escalation is an attack.

**The break:** NIDS alerts are CORRELATABLE across independent sensors. Multiple weak signals sum to a strong one. Our lessons don't correlate — two irrelevant lessons don't become relevant because they fired together. Correlation amplifies signal in NIDS; it amplifies noise in ours.

**Transfer:** The suppression mechanism. SOC teams maintain suppression rules: "this signature on this host is a known false positive, silence it." We need the equivalent: a lesson that fires repeatedly on actions where it's never credited should be suppressed for that trigger domain. Not benched globally — suppressed contextually.

---

## RANKED BY TRANSFERABILITY

| Rank | Field | What transfers | What breaks |
|------|-------|----------------|-------------|
| 1 | **Clinical Decision Support** | Reduce volume to increase trust. Tier by confidence. Interruptive only when high-confidence. | Their FN cost (death) dominates. Our FP cost (trust) dominates. Inverted asymmetry. |
| 2 | **Static Analysis Warnings** | Inline, one-line rendering. Suppress-on-irrelevant as implicit feedback. | Their items can be provably wrong. Ours are usually just irrelevant. |
| 3 | **Spam Filtering** | Precision over recall. Show nothing unless confident. Cost asymmetry drives design. | They have ground truth (billions of explicit labels). We have sparse implicit feedback. |
| 4 | **GitHub Copilot** | Rank by ACCEPTANCE/ACTION likelihood, not semantic similarity. | They have immediate feedback (keystrokes within seconds). Ours is delayed and bundle-confounded. |
| 5 | **Intrusion Detection Triage** | Contextual suppression. Silence known-irrelevant items per domain. | Their weak signals CORRELATE into strong ones. Ours don't. |

---

## THE FIELD DANIEL NAMED (web search) — and why it's NOT the best analogue

Web search has expressed intent: a query. The user TOLD you what they want. Our system has no query — it infers intent from a file path or shell command. Web search also has IMMEDIATE implicit feedback at massive scale (clicks, dwell time, reformulations). Our feedback is sparse, delayed, and we proved offline evaluation impossible. Web search's core mechanism — learning to rank from clicks — does not transfer because we lack both the intent signal and the feedback density that make it work. Daniel's instinct was reasonable; the preconditions are absent.


==============================================================================
## kimi  (bus id 1785197636035-0, 7636 chars)
==============================================================================

Daniel asks: who else faces our exact shape — unrequested injection, tiny corpus, hot path, sparse implicit feedback, trust-erosion cost — and *solved it at scale*. Here are five fields ranked by transferability, with the mechanism that shipped, the number I could verify, and the mandatory break.

---

**1. CLINICAL DECISION SUPPORT (CDS) — the closest match, and the cautionary tale we must not become**
*System:* Epic/Cerner medication alerting (drug–drug interaction, allergy).
*Mechanism shipped:* interruptive modal alerts fired on physician order-entry, rule-driven, with tiering (hard stop vs. warning vs. passive notice) and override logging.
*Evidence at scale:* override rates 49–96% depending on alert class (verified: PMC3994856, 2013; Pharmaceutical Press 2026). The field's own literature names the disease — *alert fatigue* — and the metric that predicts it is **override rate**, not precision. High override = noise, regardless of whether the alert was technically correct.
*WHERE THE ANALOGY BREAKS (mandatory):* clinicians are *legally liable* for overridden alerts, so they read them even when fatigued. Our agent has no liability and can skim without consequence. CDS survives its false positives because the cost of missing a true positive is catastrophic (death). Our FP cost is trust erosion; our FN cost is a repeated mistake. The asymmetry is inverted. **Transferable: the override-rate-as-health-metric and the tiered-interrupt model. Not transferable: the forcing function that makes anyone read the alert.**

**2. STATIC ANALYSIS (Coverity/Facebook Infer) — the field that solved the false-positive problem by *not calling them bugs***
*System:* Coverity SAST, Infer, SpotBugs.
*Mechanism shipped:* the tool does not report "bugs"; it reports **rule violations**, and the *triage loop* is human-in-the-loop with suppression lists. The engineering trick is that the rule definition is *conservative* (a violation is always a violation of the rule; whether it is a bug is a human judgment). The tool never claims semantic truth.
*Evidence at scale:* Coverity Scan has run on >10k OSS projects (verified: CISQ/Black Duck docs). The FSE 2025 suppressed-warnings study shows suppression is a first-class, versioned artifact — not an admission of failure, but the *mechanism* by which precision is maintained.
*WHERE THE ANALOGY BREAKS:* static analysis runs on a **formal artifact** (source code) with a **deterministic rule engine**. Our corpus is natural-language claims about behaviour, and our trigger is an action, not a compile. We cannot make our rules conservative in the same way because our rules *are* the semantic claims. **Transferable: the suppression-list-as-first-class-artifact pattern (our `is_benched` is a crude version) and the discipline of never calling a violation a bug. Not transferable: the formal substrate.**

**3. INTRUSION DETECTION — the field that quantified the base-rate problem we are living**
*System:* network IDS (Snort, Suricata, and the academic literature around them).
*Mechanism shipped:* signature-based detection + anomaly scoring, but the real engineering is **alert triage consoles** and the explicit acknowledgment of the base-rate fallacy. Axelsson (1999, verified: ACM DL 357830) proved that with a 1% base rate, even a 99% accurate detector yields ~50% false alarms. The field's answer was not better detection; it was **correlation engines** (SIEM) that raise the effective base rate by requiring multiple weak signals before paging a human.
*Evidence at scale:* the base-rate fallacy paper is the canonical citation; the 2023 controlled experiment (SAGE 10.1177/21695067231192573) shows IDS false-alarm rate directly degrades operator performance.
*WHERE THE ANALOGY BREAKS:* IDS has a **physical ground truth** (packets either contain the exploit or they don't) and can replay captures offline. We have no replayable ground truth; our "intrusion" is a semantic mismatch between a lesson and an action. **Transferable: the correlation-engine pattern — require multiple weak signals (path match + command match + recency + outcome credit) before injecting, so the effective base rate rises. Not transferable: offline replay.**

**4. CODE COMPLETION (GitHub Copilot) — the field that solved the feedback problem with telemetry, not labels**
*System:* Copilot inline suggestions.
*Mechanism shipped:* ghost-text injection on every keystroke (unrequested, hot path, ~100ms budget), with **acceptance rate** as the health metric. Acceptance is a binary implicit signal (Tab vs. keep typing) that is cheap, continuous, and unambiguous.
*Evidence at scale:* ~30% acceptance rate across ~1M users (verified: ITPro 2023, GitHub blog 2024, arXiv 2501.13282 Zoominfo study). The number is stable across studies.
*WHERE THE ANALOGY BREAKS:* acceptance is **unambiguous** — Tab pressed = used, no Tab = ignored. Our "used" signal is murky (did the agent open the file the lesson mentioned? did it already know?). Copilot also has **population scale**: 30% of a million users is 300k daily acceptances; we have 3 seats. **Transferable: the ghost-text UI (passive, non-modal, easy to ignore) and the acceptance-rate-as-primary-metric. Not transferable: the unambiguous feedback signal and the volume.**

**5. SPELL/GRAMMAR CHECKING (Grammarly, MS Editor) — the field that proved adaptive dictionaries beat universal rules**
*System:* Grammarly, Microsoft Editor.
*Mechanism shipped:* a **personal dictionary** layer on top of the universal rule engine. The system learns user-specific exceptions (names, jargon, stylistic choices) and stops flagging them. The universal engine handles the long tail; the personal layer handles the trust.
*Evidence at scale:* Grammarly correction precision 81% vs. MS-NLP 79% (verified: ScienceDirect S1060374326000032, 2026). The personal-dictionary mechanism is older (Word's custom.dic, 1990s) but the *adaptive* layer is the shipped differentiator.
*WHERE THE ANALOGY BREAKS:* spell checking has a **closed vocabulary** and a **deterministic correctness criterion** (a word is either in the dictionary or it isn't). Our corpus is open and our correctness is contextual. **Transferable: the personal-dictionary layer — per-seat suppression lists that learn "this seat never wants to see the doom-UI lesson when editing docs." Not transferable: the closed vocabulary.**

---

**Integration synthesis (what I would actually build):**

The five fields converge on one architecture: **a conservative rule engine + a correlation gate + a per-seat suppression layer + an override-rate health metric.** None of them solved the problem with a better ranker. All of them solved it with a *triage loop* that makes false positives cheap to dismiss and false negatives visible in aggregate.

For us, that means: (1) keep the current hook but make it *passive* (ghost-text style, not modal); (2) add a correlation gate — require at least two independent signals (path + command + outcome credit) before injecting; (3) build the per-seat suppression list as a first-class artifact (the personal dictionary); (4) instrument the override rate as the primary health metric, not precision.

The one field I did *not* name, because Daniel named it: web search. Its mechanism (PageRank + click feedback) needs query volume and explicit clicks we do not have. The five above are the ones that faced our shape without those luxuries.

**Figures verified via web search: CDS override rates, Copilot 30%, Grammarly 81%, Axelsson base-rate paper. Figure from memory: Coverity project count (~10k, I believe this is in their public docs but did not re-verify).**


==============================================================================
## kimi-labels  (bus id 1785198829746-0, 1792 chars)
==============================================================================

The pack shape is right for what I intended, with one confession I must file before labelling: the recall arm measures *my memory of the corpus*, not the index — I cannot grep during a blind pass without contaminating the precision labels, so my MISS labels are limited to lessons I happen to know exist. That asymmetry is worth naming now; it argues for a read-only grep door in the MISS phase of the *next* pass.

Labels:

1:a on
2:a on
3:a off
3:b off
3:c off
4:a off
4:b off
4:c off
5:a off
5:b off
6:a on
7:a off
8:a on
8:b off
8:c on
9:a off
10:a off
10:b on
10:c on
11:a on
12:a on
12:b off
13:a on
13:b off
14:a off
14:b off
14:c off
15:a on
16:a off
16:b off
16:c off
17:a on
18:a on
19:a on
19:b off
19:c off
20:a off
20:b off
20:c off
21:a on
22:a off
22:b off
22:c off
23:a on
23:b on
23:c on
24:a on
25:a on
25:b off
25:c off
26:a off
26:b on
26:c on
27:a off
27:b on
28:a on
28:b off
28:c on
29:a skip
29:b on
29:c off
30:a on

MISS 24 learn:experiment:bifrost_send_always_text_file — the action is a `--text-file` send to two seats; the unconditional text-file rule is exactly on-point and did not fire.
MISS 30 learn:experiment:bifrost_send_always_text_file — same lesson, same shape of action (`--text-file` send), again absent.

Two labels I flag for the fence round rather than defend silently: 21:a (I labelled on — this is Daniel's original complaint receipt, and "on-point for the action" is arguably true even if the lesson is stale; the pack's blindness to credit history cuts both ways here) and 11:a (the `intelligence_roadmap` lesson claude cited as prescribing DONE work — I labelled on because curation machinery *is* what the action enumerates, but if the lesson's roadmap content is dead, on-point-but-invalid may be a third category the rubric cannot express).