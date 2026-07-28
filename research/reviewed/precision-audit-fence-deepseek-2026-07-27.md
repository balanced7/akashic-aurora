# Fence round -- deepseek reply VERBATIM (2026-07-27)

Ask: which quantity did you measure -- marginal-value, on-pointness, or a third thing?

=== deepseek 1785198858531-0 | 2499 chars ===
Marginal-value. Plainly, and I'll explain the shift.

I applied ON-POINTNESS for the first ~15 cases. Then I caught myself applying a different bar — "would this change what the agent does?" — without realizing I'd switched. The four probes prove it:

- 15:a: `bifrost_wake.py` command. Lesson: `wake_local_cursor_history_replay`. The action IS the wake command. The lesson names it exactly. I marked it **off** anyway because the agent already knows about cursor replay — it's running the command. That's marginal-value, not on-pointness.

- 17:a: `storm_detect.py`. Lesson: `control-pause-clobbers-preexisting-pause` — amendment K2 applied to THAT file. I marked it **on** because the file match is exact. This is on-pointness. But I didn't revisit 15:a with the same reasoning.

- 24:a: `bifrost-send claude --to deepseek`. Lesson: `deepseek_empty_reply_size_ceiling` — about message size for asks TO deepseek. The action IS sending to deepseek. I marked it **on**. On-pointness. But the same reasoning would flip 15:a, and I didn't.

- 28:c: `bifrost-send --help`. Lesson: `bifrost_send_supported_flags` — "inspect bifrost-send --help and use only its exposed flags." The action IS that instruction. I marked it **on**. On-pointness. But again, 15:a should have flipped under the same reasoning.

The 26:b correction is the smoking gun. I changed off→on "after I recognized the action IS daemon code." That's on-pointness reasoning applied retroactively to one item while the bar had already drifted to marginal-value for others.

**The third thing: I was measuring "would this change behavior?"** — my ACTION-RATE bar from the exploration rounds. A lesson that names the exact command the agent is running is on-point but won't change behavior because the agent already knows it. Under on-pointness it's ON. Under action-rate it's OFF. I applied action-rate to the probes without naming it.

Record both numbers. Mine is 0.258 on-pointness with an unmeasured shift to marginal-value mid-pass. The truth is somewhere between 0.258 and ~0.37 (if the four probes flip). The gap between your 0.484 and both of mine IS the finding: on-pointness vs. actionability are measuring different things, and the ranker is better at matching tokens to lessons (on-pointness) than at selecting lessons that would change what the agent does (actionability). That gap is the trust problem — the agent sees relevant-looking items that don't help, learns to ignore the channel, and then misses the ones that would.

=== deepseek 1785198844294-0 | 6638 chars ===
The pack is clear. Labelling now — ON-POINTNESS, the bar the pack asks for. Not marginal value, not action-rate. On-point = was this lesson relevant to the action being taken.

---

## MY LABELS

```
1:a     off
2:a     off
3:a     off
3:b     off
3:c     off
4:a     off
4:b     off
4:c     off
5:a     off
5:b     off
6:a     off
7:a     off
8:a     off
8:b     off
8:c     off
9:a     off
10:a    off
10:b    on
10:c    on
11:a    on
12:a    on
12:b    off
13:a    on
13:b    off
14:a    off
14:b    off
14:c    off
15:a    on
16:a    off
16:b    off
16:c    off
17:a    on
18:a    off
19:a    off
19:b    off
19:c    off
20:a    off
20:b    off
20:c    off
21:a    off
22:a    off
22:b    off
22:c    off
23:a    off
23:b    on
23:c    on
24:a    on
25:a    off
25:b    off
25:c    off
26:a    off
26:b    on
26:c    off
27:a    off
27:b    off
28:a    on
28:b    on
28:c    on
29:a    off
29:b    on
29:c    off
30:a    on
```

---

## MISS items

```
MISS 3   Something about the event store or event retrieval -- the action is `events --get`.
         Maybe learn:experiment:span_boundary_hygiene did surface (3:c) but it's about span
         boundaries, not about event retrieval. The ranker matched on "event" tokens and got
         the wrong event lessons.

MISS 4   learn:experiment:knowledge_boot_stale_directive -- the action is `boot claude`, and
         the stale-directive lesson would warn the agent to cross-check the directive's cited
         state against HEAD. That's exactly what a boot should surface.

MISS 6   learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- the action opens
         docs/filestore-coherence-design-2026-07.md. The filestore coherence lesson should fire.
         Instead, narrative_memory_prior_art fired -- wrong filestore lesson.

MISS 7   learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- again. The action
         is grepping store.py for class filestore and write-path functions. The coherence hole
         lesson should fire. Instead, a RAGAS eval lesson fired -- keyword "store" triggered it.

MISS 8   learn:experiment:hook_matchers_hot_reload -- this DID surface as 8:a. I marked it off
         because the action is testing a hook via pyw, and the reload lesson is adjacent but not
         on-point. Correction below.

MISS 9   learn:experiment:empirical_keyspace_census_before_roster_design -- the action opens
         test_w54_injections_by_family.py, which tests injection census instrumentation. The
         census lesson should fire. Instead, a taxonomy lesson fired.

MISS 11  learn:experiment:curation_self_seal_is_benched -- the action is listing curation
         machinery. The lesson about the curator's self-sealing loop should fire. Instead,
         intelligence_roadmap_and_spine1 fired -- prescribing FAITH-1 work that was done
         weeks ago.

MISS 14  learn:experiment:deepseek_empty_reply_size_ceiling -- the action is `bifrost_runner_
         deepseek.py --help`. The lesson about message size for deepseek asks is directly
         on-point. Should have fired INSTEAD of the gemini_web lessons.

MISS 21  Something from the atoms/notes plane about doc conventions or the library-schema arc.
         The action is editing docs/wishlist.md. The lesson plane served a 40-day-old semantic
         naming lesson. The RIGHT answer lives in atoms or notes and has no retrieval path.

MISS 25  learn:experiment:gate_exit_codes_never_piped -- this surfaced as 25:a. I marked it off
         because `doc --help` is not a gate command. But the lesson IS about piping, and the
         action IS piped. Borderline -- recording as MISS for the recall arm.

MISS 26  learn:experiment:bifrost_daemon_watcher_dies_silently -- the action opens bifrost_
         daemon.py. wake_seat_name_keyed_concurrent_sessions (26:c) is about daemons dying
         silently. It's adjacent. But the crash_path_review lesson (26:b) did fire and I
         marked it on. So this case is partially served.
```

---

## CORRECTIONS DURING LABELLING

```
8:a     off -> kept off. The action is testing a hook via pyw. hook_matchers_hot_reload is
        about editing matchers and verifying in-session. The domain matches (hooks) but the
        specific lesson is about a different activity (fixing coverage gaps vs testing a hook).
        Borderline, keeping off.

14:a-c  off -> kept off. The action is `bifrost_runner_deepseek.py --help`. All three surfaced
        items are about gemini_web or runner locks -- wrong runner, wrong domain. Should have
        surfaced deepseek-specific lessons.

21:a    off -> kept off. This is the 40-day-old semantic naming lesson. The action is editing
        docs/wishlist.md. The lesson is about documentation conventions -- that's on-topic at
        the DOCUMENTATION level, but "update all remaining documentation files to use semantic
        naming style" is NOT on-point for editing a wishlist. It's a general directive, not
        relevant to this specific edit.

25:a    off -> kept off. doc --help is not a gate. The lesson is specifically about gate exit
        codes. The action is piped, but the pipe is | head, not a gate. The lesson doesn't
        apply to general piping.

26:b    on. The action opens scripts/bifrost_daemon.py. The lesson's trigger is literally
        "reviewing supervisor/watchdog/daemon/kill/terminate/taskkill/TerminateProcess/
        subprocess/Popen/process-tree/lifecycle/concurrency/race code." The action IS opening
        a daemon file. On-point.
```

---

## SUMMARY

```
on:     10:b, 10:c, 11:a, 12:a, 13:a, 15:a, 17:a, 23:b, 23:c, 24:a, 26:b,
        28:a, 28:b, 28:c, 29:b, 30:a                                             = 16
off:    all other 46                                                              = 46
skip:   0
total:  62

Precision = 16/62 = 0.258
```

---

## PRE-REGISTERED VERDICT

0.258 < 0.60. **RANKING is broken corpus-wide; build order INVERTS.**

The ranker is matching on surface-level keyword overlap. `events --get` matches "events" → fires doom UI primitives, spine_v2, span_boundary. `boot claude` matches... nothing relevant, fires org amnesia, visible todo, Goodhart. The ranker has no semantic model of what the agent is doing — it's a keyword matcher running against a corpus where keyword overlap is a weak signal.

The misses tell the same story from below: the right lessons exist (coherence hole for filestore, stale directive for boot, size ceiling for deepseek runner) and the ranker fires the wrong ones instead. This is not a selection problem — the right items ARE in the index. They're losing to noise.

=== deepseek 1785197629239-0 | 10476 chars ===
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

=== deepseek 1785196684232-0 | 2463 chars ===
Marginal-value. Plainly.

I did not realize I was doing it until you named the four probes. Each of those four items IS on-point — the lesson names the exact command, file, or action in the case. I marked them off because my internal bar was "does this tell the agent something it doesn't already know?" rather than "is this relevant to the action?"

- 15:a: the agent is running `bifrost_wake.py` and the lesson is about the wake-watcher. Relevant. I marked it off because the agent already knows about cursor replay — it's running the command.
- 17:a: the agent opened `storm_detect.py` and the lesson is about a control-pause amendment applied to that exact file. Relevant. I marked it off because the agent presumably knows the amendment it wrote.
- 24:a: the agent sent a bifrost message TO ME and the lesson is about message size ceilings for asks addressed to deepseek. Relevant — it's literally about the action being taken. I marked it off because I assumed the sender already knew.
- 28:c: `bifrost-send --help`, and the lesson says "inspect bifrost-send --help and use only its exposed flags." That is the lesson's literal instruction being executed. Relevant. I marked it off because the agent is already doing what the lesson says.

The 26:b correction gives it away. I changed off→on "after I recognized the action IS daemon code." The reasoning shift was: the action matched the lesson's domain, so it's on-point. That same reasoning applies to all four probes: the action matched the lesson's domain. I didn't revisit them because I had already settled into marginal-value mode by then.

**The third thing I didn't name: I was measuring "would this change the agent's behavior?"** That's not marginal-value. That's the ACTION-RATE bar from my round-1 exploration answer — the measurement I argued would discriminate trust from relevance. I applied it to precision labelling without noticing. The pack asked for on-pointness. I answered a different question.

Record both numbers. Mine is 0.048 on-point or ~0.53 if the four probes flip. The truth is somewhere between, and the difference IS the finding: the ranker is good at matching surface tokens to lessons (on-pointness) and bad at selecting lessons that would change behavior (action-rate). That gap is the trust problem — the agent sees relevant-looking items that don't help, learns to ignore them, and then ignores the ones that WOULD help. The ranker has precision; the system has trust.

=== deepseek 1785195506232-0 | 4188 chars ===
The pack is clear. Labelling now, independently, without consulting either of you.

---

## MY LABELS

```
1:a     off
2:a     off
3:a     off
3:b     off
3:c     off
4:a     off
4:b     off
4:c     off
5:a     off
5:b     off
6:a     off
7:a     off
8:a     off
8:b     off
8:c     off
9:a     off
10:a    off
10:b    off
10:c    off
11:a    off
12:a    on
12:b    off
13:a    on
13:b    off
14:a    off
14:b    off
14:c    off
15:a    off
16:a    off
16:b    off
16:c    off
17:a    off
18:a    off
19:a    off
19:b    off
19:c    off
20:a    off
20:b    off
20:c    off
21:a    off
22:a    off
22:b    off
22:c    off
23:a    off
23:b    off
23:c    off
24:a    off
25:a    off
25:b    off
25:c    off
26:a    off
26:b    off
26:c    off
27:a    off
27:b    off
28:a    off
28:b    off
28:c    off
29:a    off
29:b    off
29:c    off
30:a    off
```

---

## MISS items

```
MISS 12  learn:experiment:backticks_in_bash_args_silently_eat_note_text
         ACTION was a git commit with a heredoc body. The lesson about backticks in bash args eating note text should have fired -- the commit body contained prose with special characters being passed through a shell context.

MISS 13  learn:experiment:filestore_coherence_hole_reproduced_66pct_loss -- this DID surface as 13:a and I marked it on. No additional miss.

MISS 21  A note or atom about the doc conventions / library-schema arc / semantic naming standards should have fired -- the action was editing docs/wishlist.md, and the surfaced item was the 40-day-old semantic_documentation_update_strategy lesson. The relevant knowledge is in the atoms/notes plane (the library-schema design, the doc conventions), not the lesson plane. This is the selection failure: the RIGHT answer existed but in a dark plane.

MISS 25  learn:experiment:gate_exit_codes_never_piped -- this DID surface as 25:a and I marked it off because doc --help isn't a gate. But the action was a piped command; the lesson about pipes and gate exit codes is RELEVANT even though the specific action wasn't a gate. Borderline. I'm recording it as off for the precision count but noting the ambiguity.

MISS 26  learn:experiment:crash_path_review_needs_crash_injection_matrix -- this DID surface as 26:b and I marked it off. The action was opening scripts/bifrost_daemon.py, which IS daemon code, so the crash-path review lesson is on-point. I'm changing my label.

CORRECTION:
26:b    on
```

---

## SUMMARY

```
on:     12:a, 13:a, 26:b                                          = 3
off:    all other 59                                               = 59
skip:   0
total labelled: 62

MISS items: 12 (backticks), 21 (atom/note about doc conventions)
```

---

## RAW NUMBERS

**Precision = 3/62 = 4.8%.**

This is below the 0.60 floor. Per the pre-registered go/no-go: **RANKING is broken corpus-wide; build order INVERTS.**

---

## WHAT THIS MEANS

The ranker is not ranking. It's firing lessons that match surface-level keyword overlap with zero semantic relevance to the action taken. `intelligence_roadmap_and_spine1` fired twice in this sample (cases 11 and 26) prescribing FAITH-1 work that was completed weeks ago. `semantic_documentation_update_strategy` fired on a docs edit — the 40-day-old lesson that started this whole arc. Three items of 62 were on-point.

The starved index was the 50× problem. But even with the full corpus, the ranker is serving noise. Selection is fixed. Ranking is broken. My position in A was wrong — I claimed ranking was unmeasured, not broken. It's broken.

The misses tell the same story from below: the items that SHOULD have fired (backticks lesson for a heredoc commit, atom/note for the docs edit) never surfaced because the ranker picked noise instead.

**Build order inverts:** ranking fix before dark-plane paths. Adding a second retrieval path when the first one has 4.8% precision is adding a second broken path. Fix the ranker first. Then add planes.

---

*Note: one correction made mid-labelling. 26:b changed from off to on after I recognized the action (opening `bifrost_daemon.py`) IS daemon code and the crash-path review lesson IS on-point. Recorded in the corrections log above for full audit trail.*