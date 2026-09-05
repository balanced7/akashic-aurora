---
akashic_id: art_20260905_t392-arm-b-procedural-rigor-across-aviat_213783
akashic_sha: 2c94e296891a
schema_version: 1
status: current
type: report
date: 2026-09-05
title: "T392 arm B: procedural rigor across aviation, medicine, nuclear"
gist: "# T392 - Arm B: procedural rigor across aviation, medicine, nuclear *Four sub-agents on primary sources (NTSB / NEJM / NASA / DOE / IAEA), c"
visibility: fleet
body_type: markdown
seats: []
category: [testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-05T01:15:14"
updated: "2026-09-05T01:15:14"
---
<!-- GENERATED PROJECTION of art_20260905_t392-arm-b-procedural-rigor-across-aviat_213783 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T392 arm B: procedural rigor across aviation, medicine, nuclear

# T392 - Arm B: procedural rigor across aviation, medicine, nuclear

*Four sub-agents on primary sources (NTSB / NEJM / NASA / DOE / IAEA), consolidated 2026-09-05.
Landed AFTER the first synthesis was published; corrections folded into the artifact same day.
Claims graded: primary text read / secondary only / could not verify -- INCLUDING a list of
widely-repeated claims that did NOT survive verification.*

---

All four domain agents have reported. Here is the synthesis.

---

# Precision Under Time Pressure: Procedural Discipline Across Aviation, Medicine, and Nuclear Operations

**Method note.** Four parallel research agents worked primary sources (NTSB/NEJM/NASA/DOE/IAEA) plus my own direct extraction from NASA CR-177549, NASA TM-2010-216396, Hollnagel's *Safety Science* barrier paper, and the Wan & Bolton forcing-function taxonomy. Claims are flagged ✅ (primary text read), ⚠️ (secondary only), ❌ (could not verify). Several widely-repeated claims **did not survive** verification — those are collected at the end.

---

## 0. THE MECHANISM SPINE

You asked specifically about mechanisms that fire *at* the moment of action rather than relying on recall or intention. There is a formal literature that answers exactly this, and it turns out to be the organizing principle for everything below.

### 0.1 Hollnagel's barrier taxonomy — the load-bearing distinction ✅

Hollnagel E., "Risk + barriers = safety?", *Safety Science* 46 (2008) 221–229. Four barrier system types, verbatim definitions:

| Type | Definition (verbatim) | Examples |
|---|---|---|
| **Physical/material** | "concretely prevent an event from taking place… **An important characteristic of physical barrier systems is that they do not have to be perceived or interpreted by someone (or something) in order to work.**" | walls, cages, containers, interlocked gates |
| **Functional** | "create one or more **pre-conditions that have to be met before an action can be carried out**, for instance by establishing an interlock, either logical or temporal" | locks, equipment alignment, passwords, action sequences |
| **Symbolic** | "work indirectly through their 'meaning', hence **require an act of interpretation by someone**" | **procedures, instructions, signs, alarms, work permits, clearances** |
| **Incorporeal** | "not physically present in the situations where they are applied but **depend on the knowledge of the user**" | rules, laws, safety culture, self-restraint |

The sentence that governs this entire report:

> "In the case of symbolic and incorporeal barrier systems, **the barrier systems cannot themselves provide the barrier function but require an action by someone**."
> "**Symbolic and incorporeal barrier systems must usually be amplified by physical and functional barrier systems to work.**"

**Every practice in this report is a symbolic or incorporeal barrier.** A checklist is a sign. A procedure is a rule. Neither does anything on its own. The entire engineering problem of procedural discipline is: *how do you give a symbolic barrier an enforcement surface?*

Hollnagel's own example of the failure: a work permit. "Not having a work permit is supposed to prevent work from taking place. In many cases, work nevertheless starts before permission is given… **there is nothing in the executing system itself that prevents the actions from being carried out, short of the ethics or morals (or fear of punishment) of the people involved.**"

### 0.2 The forcing-function hierarchy and the resilience price ✅

Wan P. & Bolton M.L., "A Taxonomy of Forcing Functions for Addressing Human Errors in Human-Machine Interaction," IEEE SMC 2021. https://par.nsf.gov/servlets/purl/10344838

- **Hard forcing functions** — the interface physically prevents the erroneous action. Three levels, most to least restrictive: **interlock** (only allows actions in a correct order) → **lockin** (only allows actions for the correct task) → **lockout** (blocks only the actions associated with the specific error).
- **Soft forcing functions** — do not restrict; they remove the conditions that cause the error. **Symbolic** (changes the interface/environment so correct behavior is more readily identified) and **incorporeal** (changes how the human thinks — training, rules, enforcement).

The axis that matters: **restriction and resilience trade off directly.** "in limiting what behaviors humans can perform, **system resiliency may be sacrificed**: the human ability to creatively respond to situations unanticipated by designers may be restricted."

Their design rule is the correct answer to the compliance-vs-expertise tension in §4: **select the minimally constraining intervention that prevents the specific error.** Not "maximize compliance." Not "trust the expert." Identify the error, then apply the least restrictive forcing function that actually blocks it.

### 0.3 The empirical finding that unifies the domains

Across aviation, medicine, and nuclear, **every practice that survived contact with real accidents did so by acquiring one of exactly three enforcement surfaces**:

1. **A physical artifact that holds state the operator's memory would otherwise hold** — the checklist card, the placekeeping mark, the flag on the valve, the electronic checklist that auto-senses.
2. **A mandated verbal exchange that converts silence into a detectable event** — challenge-response, three-part communication, standard callouts, the designated reader.
3. **A second person with veto authority physically present at the moment of action** — peer check, concurrent verification, the nurse empowered to stop the line.

Practices that remained purely internal — memory items, "aviate navigate communicate," sterile-cockpit *enforcement*, questioning attitude — are precisely where the documented failures cluster. Two independent industries reached this conclusion and then converted their internal tools into **observable motor acts** (point, touch, read aloud) specifically to give them a surface.

**The cheapest quantified proof of the artifact effect** ✅: Swain & Guttman (1983) human error probabilities, cited in NASA CR-177549 — per-item error probability is **~1 in 100 without a check-off provision vs ~3 in 1,000 with one**. Roughly 3× from a pen mark alone.

**And the Japanese version** ⚠️: *shisa kanko* (pointing-and-calling). Railway Technical Research Institute 1994: volunteers made 2.38 errors per 100 actions with no intervention; **pointing *and* calling reduced errors by ~85%** — pointing alone or calling alone were both weaker. NYC MTA adopted a point-only variant in 1996; incorrectly-berthed subway incidents **fell 57% within two years**. https://www.atlasobscura.com/articles/pointing-and-calling-japan-trains

---

## 1. AVIATION

### 1.1 Checklist origin — what the 1935 record actually says ✅

The **Board of Officers finding, 15 November 1935**, published verbatim by the National Museum of the USAF (https://www.nationalmuseum.af.mil/Visit/Museum-Exhibits/Fact-Sheets/Display/Article/610002/model-299-crash/), contradicts the popular retelling:

> "the accident was not due to structural failure… but to **the locked condition of the rudder and elevator surface controls**."

**Mechanism.** The elevator was locked in the *first* hole on the up-elevator side — 12.5° deflection. Every other lock position was self-revealing: down-elevator holes made takeoff impossible; the extreme up-elevator hole physically blocked the pilot from reaching his seat. Only this one intermediate position was survivable until airborne. During the ground roll, angle of attack could not exceed 10.5°, so **"This would not be particularly noticeable to the pilot during the ground run."** Airborne at ~74 mph, elevator authority rose with airspeed squared and drove the aircraft to a stall.

**The Board's actual conclusion — a systems finding, not a memory finding:**

> "Due to the size of the airplane and the inherent design of the control system, **it is improbable that a pilot, taking off under these conditions, would discover that the controls were locked until too late to prevent a crash**."

**Two corrections to the standard story:**

- ⚠️ **"Too much airplane for one man to fly" is journalistic, not official.** It appears nowhere in the Board finding. Its modern currency traces to Gawande's *New Yorker* piece (2007), which attributes it to an **unnamed** contemporary newspaper. The original 1935 paper could not be located.
- ❌ **"Not too much airplane for one man to fly; simply too complex for any one man's memory"** — presented in many sources as an investigating-team conclusion. **It is not in the Board finding**, and no primary citation exists. It is a modern paraphrase.

**Why this matters mechanistically:** the Board's finding is *stronger* than the memory story. The aircraft gave the crew **no natural cue**. The checklist's job was not to compensate for a weak memory; it was to **manufacture a detection event where the machine provided none.**

### 1.2 What a checklist actually is — Degani & Wiener ✅

NASA CR-177549 (May 1990), full text read. Field study: 42 crews, 72 legs, ~140 flight hours from the jumpseat, plus interviews at seven US carriers. https://ntrs.nasa.gov/api/citations/19910017830/downloads/19910017830.pdf

**The eight stated objectives** (§2.1.1) — note how few are about memory:
1. Aid the pilot in recalling the process of configuring the plane.
2. Provide a standard foundation for verifying configuration **"that will defeat any reduction in the flight crew's psychological and physical condition."**
3. Provide convenient sequences for motor movements and eye fixations.
4. Provide a sequential framework meeting internal and external requirements.
5. **Allow mutual supervision (cross checking) among crew members.**
6. Enhance a team concept by keeping all crew members "in the loop."
7. Dictate each crew member's duties for coordination and workload distribution.
8. Serve as a quality-control tool for management and regulators.

**Challenge-response vs read-do — the precise mechanism** (§3.1.4), verbatim:

> **Challenge-Response** "can be more accurately termed **'challenge-verification-response'**… the checklist is a **backup for the initial configuration** of the plane. Here, the pilots use their memory and other techniques to configure the plane. After completing the initial configuration, the pilots use the checklist to verify that several critical items have been correctly accomplished… Pilot A calls the item; pilot-B and pilot-A **together verify**; pilot-B calls the verified status. Hence, **both the configuration and mutual redundancies are employed**."

> **Do-list** "can be better termed **'call-do-response.'** … the checklist is used to 'lead' and direct the pilot… Therefore, **the configuration redundancy employed in the challenge-response method is eliminated here**… due to the elimination of the configuration redundancy, **a mistake can easily pass unnoticed once the sequence is interrupted**."

Boeing 1989 survey of 20 airlines: **12 challenge-response, 1 do-list, 7 combined.**

**The allocation rule** — and this is the crisp answer to *why* each is used where: **read-do exists where the procedure branches.** SKYbrary: read-and-do relates to non-normals "for which a cockpit flow pattern performed from memory is **not suitable**. Indeed, non-normal procedures usually include **pre-conditions (conditional action steps)** that must be assessed and **mutually agreed by both crewmembers**." A memorized flow cannot carry a conditional. Challenge-response exists where the actions are already done and what is needed is an independent **second observer**.

**The 16 design guidelines (Appendix A) — the mechanism-dense ones** ✅ verbatim:

- **(4)** "Checklist responses should portray the desired status or the value of the item being considered (**not just 'checked' or 'set'**)."
- **(5)** "The use of **hands and fingers to touch** appropriate controls, switches, and displays while conducting the checklist is recommended." (§7.2.2 gives the reason: "the use of the **hand to guide the eye**… can aid in fixating the eyes on the specific item and prevent the eyes from wandering.")
- **(6)** Write the completion call as the last printed item.
- **(10)** "The most critical items should be listed **as close as possible to the beginning**… in order to increase the likelihood of completing the task before interruptions may occur" — and this **takes precedence over geographic flow** where they conflict.
- **(11)** Duplicate "killer items" (flaps/slats, trim) across checklists when they may be reset on new information.
- **(12)** Design checklists **not tightly coupled** with other tasks; "provide buffers for recovery from failure."
- **(13)** Complete the TAXI checklist as close as possible to the gate and as far as possible from active runways.
- **(15)** "There should be **no compromise** regarding the critical 'killer' items."

FAA adopted (4) verbatim 27 years later — **AC 120-71B §5.4**: "The generic responses of 'set' or 'checked' may not be very informative and does not provide as good of an opportunity to confirm correct action as the actual indication." https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_120-71B.pdf

### 1.3 Evidence: how often the defense actually fires ✅

Dismukes R.K. & Berman B., NASA/TM-2010-216396, *Checklists and Monitoring in the Cockpit: Why Crucial Defenses Sometimes Fail*. Jumpseat observation of **60 revenue flights**. Full text extracted directly.

**Headline numbers:**

- **899 deviations observed** — 194 checklist, 391 monitoring, 314 primary procedure. Means per flight: checklist 3.2, monitoring 6.5, primary 5.2. Range 1 to 38 per flight.
- Error rate *per opportunity* was "**well under one percent**" — "in the vast majority of cases, checklists and monitoring were performed appropriately."
- **Only 18% of deviations were trapped** (caught and corrected, or even discussed). By type: primary procedure **35%**, checklist **14%**, **monitoring 6%**.
- Of those corrected, 63% were caught by the other pilot, 17% by the pilot who made the deviation, 19% by others (e.g. ATC).

**The authority-gradient measurement — this is the single best number on assertiveness:**

> "Captains in the monitoring pilot role were **more than twice as likely to trap deviations made by the flying pilot than first officers** in the monitoring pilot role (**27.9% versus 12.1%**), which points to the need to develop ways to encourage first officers to challenge when appropriate."

**The six checklist deviation types, with counts:**

| Type | n | Cognitive account |
|---|---|---|
| Flow-check performed as read-do | 48 | Eliminates configuration redundancy; often time pressure or a checklist that duplicated the whole flow |
| **Responding without looking / looking without seeing** | 43 | Source memory confusion; expectation bias; the verbal response becomes automatic |
| Item omitted, misworded, or checklist not called "complete" | 42 | Interruption, deferral, or no observable external cause |
| Checklist called at the wrong time | 31 | Poor task management |
| Checklist performed from memory | 17 | Automaticity — "To force oneself to read an often-performed checklist… feels cumbersome and effortful and slows down execution" |
| Failure to call for a checklist | 13 | Prospective memory failure (in 10 of 13 the other pilot caught it) |

**The mechanism for "responding without looking"** — verbatim:

> "Expectation that an item is correctly set arises from memory of having just set or checked an item **and from the vast number of previous instances in which that item has been correctly set**. Thus, even though the pilot may direct gaze toward the item, he or she may perceive it to be in the correct position even when it is not… it is possible that pilots' response to the checklist challenge may become so automatic that pilots sometimes **utter the response automatically, perhaps not even realizing that they have not visually confirmed** the challenged item."

**The organizational double-bind, named by the authors:**

> "This raises the issue of whether the airline industry is giving conflicting messages to pilots: **slow down and be deliberate, but respond quickly to frequent time pressures.**"

**Monitoring deviations:** 211 of 391 were omitted or late callouts, and **137 of those 211 were the single "1000 feet to go" call**. The authors estimate it "was missed around 1/3 of the time," and note that when it *was* made it was frequently prompted by the automatic altitude chime — "**which removes the redundant protection designed into the procedure**." That is automation complacency measured inside a callout.

**The accident-level correlates:**
- NTSB SS-94/01: inadequate monitoring/challenging in **84%** of major airline accidents attributed to crew error over 12 years; **31 of 37** flightcrew-involved major US accidents 1978–90 involved inadequate monitoring/cross-checking.
- Flight Safety Foundation 2010: **63%** of approach-and-landing accidents involved inadequate monitoring and cross-checking.
- ICAO 1994: **50%** of CFIT accidents.
- FSF ALAR Task Force (287 fatal ALAs 1980–96; detailed study of 76): **63%** involved a CRM failure; **72%** involved omission of action or inappropriate action; **66%** involved unstabilized approaches.
- Lautman & Gallimore 1988 (via CR-177549): takeoff, approach and landing are **27% of average flight duration but 76.3% of hull-loss accidents** — which is why pause points cluster at phase transitions.

### 1.4 The canonical failure: the ritual fires, the verification does not ✅

**Delta 1141, DFW, 31 August 1988** (NTSB/AAR-89/04). The crew took off with flaps and slats retracted; 14 died. The takeoff checklist **was run and the correct words were spoken.** NTSB measured the CVR:

> "the time between the checklist challenge and responses was **less than one second**, with little time to accomplish actions required to satisfy the proper response."

The probable cause was "inadequate cockpit discipline." The analysis lists in one sentence: no checklist initiated by the captain, only one checklist called complete, missing engine-start callouts, no takeoff briefing, **no "V1" call by the first officer**, and "the sterile cockpit policy was violated."

**This is the most important single data point in the entire subject.** The artifact was present, the exchange occurred, the phraseology was correct, and the aircraft was lethally misconfigured. A verbal ritual with no verification is indistinguishable, on tape, from a working defense.

**And the interruption case** ✅ (CR-177549): a Republic DC-9-82 lost **both engines at 35,000 ft** over Utah with a full center fuel tank. The CLIMB checklist had been called out of sequence after a knob came off in the captain's hand; the first officer mentally "held" at the ignition item, was interrupted by a flap/slat retraction command and a frequency change, and resumed *past* the center-tank boost pumps. The paper checklist had **no physical pointer distinguishing done from not-done**, so the hold point lived only in working memory. CR-177549 enumerates the consequences: "1. Elimination of the vital cross-checking of the other crew member. 2. Disruption of the sequential flow. 3. **Committing to memory the location of the interruption.**"

**The named repair** ✅ (FSF ALAR BN 1.5): "If the flow of the normal checklist is interrupted for any reason, the PF should call **'hold (stop) checklist at [item].'** 'Resume (continue) checklist at [item]' should be called before resuming… **the last completed item should be repeated**." That moves the interruption point out of memory and into speech — a symbolic barrier given an audible surface.

### 1.5 Sterile cockpit — an external gate with an internal guard ✅

**14 CFR 121.542**, verbatim (https://www.law.cornell.edu/cfr/text/14/121.542):

> **(b)** "No flight crewmember may engage in, nor may any pilot in command permit, any activity during a critical phase of flight which could distract any flight crewmember from the performance of his or her duties…"
> **(c)** "critical phases of flight includes **all ground operations involving taxi, takeoff and landing, and all other flight operations conducted below 10,000 feet, except cruise flight.**"

Structural notes: **(a)** binds the certificate holder, **(b)** binds the crewmember and PIC — dual custody. **(c) is a definition, not a command**; the 10,000 ft number appears only there. "**except cruise flight**" is undefined and is the largest textual hole. 135.100(a)–(c) is textually identical; ⚠️ the 2014 PED prohibition (paragraph (d)) is **Part 121 only**.

**The trigger.** ✅ Sumwalt states the design intent exactly: the rule "clearly defines **when** it is time to set aside non-essential activities" — not whether. 10,000 ft is read off an instrument and annunciated by the altitude alerter; taxi is a binary physical state. **But nothing on the aircraft observes the conversation.** NTSB: "the responsibility for sterile cockpit adherence is ultimately a matter of a pilot's own professional integrity." Gate external; guard internal.

**Origin — Eastern 212, Charlotte, 11 Sept 1974** ✅ (NTSB-AAR-75-9), 72 dead. Probable cause: "the flightcrew's **lack of altitude awareness at critical points during the approach due to poor cockpit discipline**." Finding 4: "The extraneous conversation… was **symptomatic of a lax atmosphere in the cockpit**." The CVR timeline is better evidence than any percentage: an 81-second nonoperational stretch, then **35 seconds of sightseeing (12 remarks about Carowinds Tower)** during which the aircraft descended through 1,800 ft while still 1.5 nmi short of the final approach fix, crossed the FAF **450 ft low at 168 kt against a Vref of 122**, and made **none** of the required callouts. The 1,000 ft terrain warning sounded and was not heeded.

**Critical correction** ✅: **NTSB never asked for this rule.** Its two recommendations from EAL 212 (A-74-85, A-74-86) asked for *professional standards committees* and an *educational seminar program*. The FAA's answer four years later was a regulation. **That conversion — soft cultural ask into hard binary gate — is itself the mechanism story.**

**ASRS evidence** ✅ — Sumwalt, ASRS *Directline* 4 (1993), 63 reports. https://asrs.arc.nasa.gov/publications/directline/dl4_sterile.htm

Outcomes: **48% altitude deviations**, 14% course deviations, 14% runway transgressions, 14% general distraction with no consequence, 8% takeoff/landing without clearance, 2% NMAC. Causes ranked: extraneous conversation (including *with ATC*); flight-attendant distractions ("almost one quarter" of reports — the second-highest source); non-pertinent radio/PA calls below 10,000 ft; sightseeing.

The sharpest line in the corpus (ACN 102595): *"The bottom line: lack of professionalism… Below the line: **lack of courage**. F/O and F/E were not willing to ask the Captain to please shut up so we could fly the airplane."*

**Failure modes** ✅:

1. **"Pertinent" is undefined and operators arbitrage it.** After Colgan 3407, Colgan's flight standards director characterized the findings as only "minor" deviations. NTSB rejected it flatly: "**any** nonpertinent remark during critical phases of flight has the potential to be distracting."
2. **Wrong datum.** ASRS ACN 65327: at Denver, 10,000 ft MSL is ~4,600 ft AGL. ACN 173707: a commuter cruising at 8,000 ft habituated to conversation because "cruise flight" exempted it.
3. **The chilling effect — and the FAA says it is the *worse* failure.** ✅ AC 120-48 §6b, verbatim: "**hesitancy or reluctance on the part of a flight attendant to contact the flight crewmembers with important safety information because of a misconception of the sterile cockpit rule is potentially even more serious than the unnecessary distraction** caused by needless violations… Flight attendants have failed to communicate… **fire in a galley trash container, a loud noise with vibration, and changes in cabin pressure** for fear of violating sterile cockpit procedures." Survey data in the same AC: **80% of pilots and 86% of flight attendants** said the concept needed clarification. **Thirty-two years later AC 120-48A §8.5.2 repeats the same warning with a longer list.**
4. **For the cabin, the trigger does not exist at all.** AC 120-48 §6a, verbatim: "**Flight attendants have no way of knowing when the aircraft is at 10,000 feet, unless they are told or signaled in some way.**" And the self-defeat: PA and interphone signalling methods "require one crew member to be 'out of the loop'" — *below 10,000 ft.*
5. **Undetectable in normal operations.** NTSB: "most airline and FAA personnel have stated, after accidents, that no precursors to such deviations were identified during their previous oversight activities." **A rule whose violation is detectable only by CVR — i.e. only after a hull loss.**
6. **Comair 5191** (2006): **40 seconds of the 150-second taxi (26.7%)** was nonpertinent; NTSB's framing is the low-workload paradox — "neither pilot was experiencing high workload at the time." **Colgan 3407** (2009): **3 min 11 sec** of nonpertinent conversation below 10,000 ft, named in the probable cause. Note NTSB's honesty — the conversation ended ~2 minutes *before* the low-speed cue, so the mechanism is displaced task completion and degraded monitoring posture, not simultaneous attention theft.
7. **The regulator's own audit says exhortation failed.** A-06-7 (2006) → FAA SAFO 06004 → closed "Acceptable Action" → **Comair four months later** → **Colgan under three years later**. In 2010 NTSB wrote that "**the lasting effect of this SAFO is questionable**."

**The medical transfer, with a hard null** ✅: no-interruption zones cut interruptions from **31.8% to 18.8%** (a 40.9% relative decrease). But the multicentre cluster **RCT of "do not interrupt" vests** — 29 units, 178 nurses, 1,346 patients, 8,472 opportunities for error — found **7.09% error rate with the vest vs 6.23% control, p=0.355**; interruptions 15.04% vs 20.75%, p=0.350. The authors' own diagnosis is the best one-line statement of the barrier taxonomy in clinical language: **"The vest is not a barrier to administration errors like the barcode system."** https://pmc.ncbi.nlm.nih.gov/articles/PMC8383384/

### 1.6 Standard callouts — three distinct mechanisms ✅

FSF ALAR Briefing Note 1.4, verbatim: https://flightsafety.org/wp-content/uploads/2016/09/alar_bn1-4-calls.pdf

> "Standard calls should be **alerting**, so that they are clearly identified… and should be **distinguished from communication within the flight deck**."
> "**The importance of using standard calls increases with increased workload.**"

**Mechanism 1 — forcing function.** "Standard calls should trigger immediately the question **'What do I want to fly now?'**" The call compels the intention to be formed and externalized *before* the switch moves.

**Mechanism 2 — shared mental model.** "When the intention of the PF is clearly transmitted to the PNF, the standard calls also will… facilitate cross-check of the FMA… and facilitate crew coordination, cross-check and backup."

**Mechanism 3 — silence becomes a signal.** This is the load-bearing one:

> "**The absence of a standard call at the appropriate time or the absence of an acknowledgment may be the result of a system malfunction or equipment malfunction, or possible incapacitation of the other crewmember.**"

A silent monitor is indistinguishable from an absent monitor unless the protocol requires noise. And the redundancy rule: "if a standard call is **omitted by one pilot, the other pilot should suggest the call**."

**The complete forcing-function pattern**, in the stabilized-approach gate (AC 120-71A App. 2 + FSF BN 7.1): **numeric threshold (1,000 ft HAT IMC / 500 ft VMC, RoD ≤1,000 fpm) → mandated callout by the PNF if any parameter exceeds criteria → mandated go-around.** No judgment step anywhere in the chain.

**Why phraseology is standardized** ✅ (CR-177549 §6.2.1–6.2.3). Communication degrades under noise and workload, and "Operators usually compensate for this by **increasing the level of expectancy**" — which is exactly the failure mode. Non-standard phraseology was observed in the field ("lets do it"; "fuel—we are OK"; a thumbs-up for completion), with four named consequences: the other crew member might not detect a checklist error; might not follow the sequence; might confuse the callout with other cockpit communication; and "**the seriousness of the checklist… is belittled**, particularly if committed by the captain." On ambiguity: "we believe that whenever possible, the response should always portray the actual status or the value of the item" — an ASRS reporter's own diagnosis was that "'checked' and 'set' can be said **too easily without any sound verification**."

### 1.7 Memory items — and why they are being minimized ✅

**Definition** (SKYbrary): memory items are "items that are **time critical and must be accomplished from memory before referring to the QRH**." Boeing's non-normal process order is itself the doctrine: **A. Fly the airplane. B. Do memory items. C. Get the checklist.**

**The reason the set is kept small** — Burian, Barshi & Dismukes, NASA/TM-2005-213462, verbatim (https://ntrs.nasa.gov/api/citations/20060023295/downloads/20060023295.pdf):

> "cognitive performance is significantly compromised under stress… human attention narrows — a phenomenon referred to as **tunneling**… **working memory capacity and the length of time information can be held in working memory decreases under stress**… When working memory capacity is exceeded, individuals' ability to analyze situations and devise solutions is **drastically impaired**."

And the asymmetry that decides the whole design:

> "**well-learned motor skills**, such as those demonstrated by experienced pilots when operating flight controls, **are quite robust and are much less affected by stress**."

**That asymmetry is the entire doctrine.** Motor skill survives stress; declarative recall and reasoning do not. So the residual memory-item set should contain only over-trained motor sequences, and anything requiring *recall of what to do* should be externalized to paper.

FAA endorses the logic — **AC 120-71B §5.6.3**: "**Including more information in checklists can reduce memory load**… However, the more information included, the longer it becomes." And NASA's honest admission: "**no guidance or standards exist for checklist developers concerning the best balance.**"

**The documented failure mode of memory items** ✅ — Airbus *Safety First*, "Is it a Loss of Braking?": "The LOSS OF BRAKING procedure memory items have to be applied in the extremely remote case of a failure of the braking system. **In-service experience shows that inappropriate application of the LOSS OF BRAKING procedure may contribute to a risk of runway excursion.**" A memorized action is fired by *recognition*, and recognition under stress is exactly what tunneling degrades. Misdiagnosis plus a fast memorized response manufactures a new hazard that the read-do path — with conditionals confirmed by both pilots — would have caught.

**How bad it gets at the limit** ✅: after Aloha 243's 18-ft fuselage separation (1988), the crew estimate they completed "largely from memory — **all or significant parts of 17 different checklists in the 13 minutes**"; one crewmember referred to the emergency checklists **twice** in the entire event.

❌ **Not verified:** specific memory-item counts by type or era, or any published Boeing/Airbus statement of a deliberate reduction policy. The trend is real in practice but I could not source a manufacturer's own numbers.

### 1.8 Aviate, navigate, communicate — and Eastern 401

**Origin: honest negative result** ⚠️/❌. **No coiner and no originating document could be identified.** The FAA itself treats it as lore: "a phrase that has been **used by pilots for many years**." The nearest regulatory anchor is 14 CFR 91.3(b) (PIC emergency authority), which grants the discretion the maxim tells you how to spend.

**Eastern 401, Everglades, 29 Dec 1972** ✅ (NTSB-AAR-73-14; FAA Lessons Learned https://www.faa.gov/lessons_learned/transport_airplane/accidents/N310EA). 101 died.

Probable cause: "the failure of the flight crew to **monitor the flight instruments during the final four minutes**… **Preoccupation with a malfunction of the NLG position indicating system** distracted the flight crew's attention from the instruments."

**The task allocation is the whole point.** The first officer **was flying the airplane and simultaneously trying to replace the indicator bulb**; the captain was assisting with the light; the flight engineer was out of the flight deck. All four people on the flight deck — three crew plus a deadheading maintenance manager — were working the same fifty-cent problem. **Nobody was assigned to aviate.**

**The mechanism of the descent:** the autopilot reverts from Command to CWS in pitch at **15 lb of control force, silently, with the engage lever unchanged.** FAA: "it is possible to **disengage altitude hold without an accompanying alert to the flight crew**."

**And the detail that makes this a mechanism story rather than a discipline story:** the altitude alert *did* fire. It is a half-second C-chord plus a flashing amber light — but **Eastern's configuration inhibited the light below 2,500 ft radar altitude**, so at 2,000 ft over the Everglades the only warning was one short tone. The CVR record: at 2340:38 the C-chord sounded. "**No crewmember commented on the C-chord.**" No corrective input followed on the FDR.

NTSB's recommendations were hardware and procedure, not exhortation: relocate the nose-wheel-well light switch near the optical sight; placard the sight's use; **modify the altitude alert to flash whenever the aircraft departs a selected altitude by ±250 ft, including below 2,500 ft**.

**The lesson, stated precisely: an alert with no mandated verbal response is a sound in a room.** Compare §1.6 — standard callouts work because silence becomes detectable. At Eastern 401, silence was normal. The nose gear was down and locked the entire time; both bulbs were burned out.

### 1.9 Assertiveness — the two-challenge rule as a procedure, not a virtue ✅

This is the strongest single finding in the aviation section. **AC 120-71B §6.6**, verbatim:

> **§6.6.1** "Policies and procedures for expected interventions should be established and include: **1. Deviation parameters; 2. Required callouts; and 3. Conditions for takeover.**"

> **§6.6.2.1** "SOPs should indicate **what to say, how to say it, when to say it, and with what level of appropriate assertiveness**… **Considerations for the decision to take over control should include subtle incapacitation or no response or flightpath correction after two challenges.**"

> **§6.6.2.3** "a PM calls **'1-dot high'** and the PF responds with **'correcting'**… If, for example, **the PF does not respond to two successive challenges**, then, per operator's SOP, if safety indicates, **the PM calls 'I have control, going around'** and initiates a go around as PF."

**Why this is a mechanism and not an exhortation.** Assertiveness in its 1980s CRM form was a *trait* to be trained — courage, communication style. AC 120-71B converts it into a **procedure with a trigger, a script, a counter, and a terminal action**. A numeric deviation parameter fires a required callout; a required response closes the loop; **failure to close the loop twice is itself the trigger** for a scripted takeover with fixed words.

The junior crewmember no longer has to decide whether the captain is wrong enough to challenge — **the parameter decides, and the count decides.** It also collapses the hardest social judgment ("is he ignoring me, or incapacitated?") into a rule that makes both cases produce the same safe action.

Note the deliberate reframing that made this possible: AC 120-71B **renamed "Pilot Not Flying" to "Pilot Monitoring."** PNF is defined by what you are *not* doing; PM is a positive job description with seven enumerated duties, including "advising the PF if the flight guidance modes or aircraft actions do not agree with expected or desired actions **and intervening if necessary**."

**Barriers the FAA names itself (§6.3):** time pressure ("rushing and '**looking without seeing**'"); "**Pilots are often unaware that monitoring performance has degraded**"; and the base-rate problem — "It can be difficult for humans to monitor for errors and deviations on a continuous basis **when errors and deviations rarely occur**."

**The evidence that the gradient is real:** Dismukes & Berman's **27.9% vs 12.1%** (§1.3). And the pre-CRM baseline, per FAA: "subordinate crewmembers did not generally assert any authority… This generally resulted in crewmembers **waiting for an order from the captain** before performing any task."

❌ **Not delivered:** PACE (Probe/Alert/Challenge/Emergency, Besco) scripted phrasing; advocacy-inquiry (Argyris; Rudolph/Simon/Raemer); Edwards' trans-cockpit authority gradient; Salas et al. 2001 CRM meta-analysis numbers; **and the verbatim hedged CVR phrasing for Air Florida 90, Avianca 052, Tenerife, and United 173.** The agent working those did not finish. Treat the hedged-language claims as well-attested in the literature but unverified here.

**One CRM number worth having** ✅: LOSA Collaborative data supplied to NTSB (2007) — crewmembers who **intentionally deviated from SOPs were three times more likely** to commit other errors, mismanage more errors, and reach more undesired aircraft states. Correlational, not causal.

---

## 2. MEDICINE

### 2.1 The WHO Surgical Safety Checklist ✅

Haynes AB et al., *NEJM* 2009;360:491-9. 8 hospitals in 8 cities; **n=3,733 before / 3,955 after**.

| Outcome | Before | After | P |
|---|---|---|---|
| Death | **1.5%** | **0.8%** | **0.003** |
| Any complication | **11.0%** | **7.0%** | **<0.001** |
| Surgical-site infection | 6.2% | 3.4% | <0.001 |
| Unplanned return to OR | 2.4% | 1.8% | 0.047 |
| Pneumonia | 1.1% | 1.3% | 0.46 (NS) |

Stratified: in **high-income sites the mortality effect was not significant** (0.9%→0.6%, P=0.18); complications were (10.3%→7.1%, P<0.001). Lower-income mortality 2.1%→1.0% (P=0.006).

**The process-adherence table is the mechanism evidence, and it is more informative than the mortality figure:**

| Process | Before | After |
|---|---|---|
| **All six safety indicators performed** | **34.2%** | **56.7%** |
| Prophylactic antibiotics given appropriately | 56.1% | **82.6%** |
| **Oral confirmation of identity + operative site** | 54.4% | **92.3%** |
| Objective airway evaluation | 64.0% | 77.2% |
| Sponge count completed | 84.6% | 94.6% |
| ≥2 IV access when EBL≥500ml | 58.1% | 63.2% (NS) |

Design caveats the authors state themselves: **uncontrolled prospective before-after, 8 self-selected volunteer hospitals, no concurrent control arm**, and "adherence rates could not be measured." Hawthorne effect explicitly named as unexcluded.

**The three pause points.** Every item is a **mandated verbal exchange at a fixed physical gate**; nothing on the list is "remember to."

- **SIGN IN — before induction.** Nurse + anesthesia professional **orally confirm**: identity/site/procedure/consent; site marked; pulse oximeter on and functioning; known allergy; airway and aspiration risk with equipment available; if EBL risk ≥500 ml, access and fluids available.
- **TIME OUT — before skin incision.** The **entire team, orally**: all members **introduced by name and role**; identity/site/procedure; then a structured round — *surgeon* reviews critical/unexpected steps, duration, anticipated blood loss; *anesthesia* reviews patient-specific concerns; *nursing* confirms sterility, equipment, other concerns; antibiotics within 60 min confirmed; imaging displayed.
- **SIGN OUT — before leaving the room.** **Nurse reviews aloud**: procedure as recorded; needle/sponge/instrument counts; specimen labeling; equipment issues. Then surgeon, nurse and anesthesia **review aloud** recovery concerns.

Two items are pure **authority redistribution** rather than error-catching: name-and-role introductions, and the explicit invitation for anesthesia and nursing to voice concerns before incision.

**SURPASS** ✅ — de Vries et al., *NEJM* 2010;363:1928-37. 6 Dutch intervention hospitals **plus 5 controls**; checklist spans admission to discharge (rationale: 53–70% of surgical errors occur outside the OR).

| | Intervention | Control |
|---|---|---|
| Complications per 100 patients | **27.3 → 16.7** | 30.4 → 31.2 |
| Patients with ≥1 complication | **15.4% → 10.6%** (P<0.001) | 17.6% → 17.9% (P=0.95) |
| In-hospital mortality | **1.5% → 0.8%**; adjusted RR **0.54 (0.33–0.88)** | 1.2% → 1.1% |

**And the dose-response — the single most useful number in this literature:** among 1,146 sampled checklists, median 80% of items completed. Complication rate **7.1 per 100 where completion was above median vs 18.8 per 100 at or below** (ARR 11.7, 95% CI 7.9–15.6). The benefit tracks how much of the checklist actually happened.

### 2.2 The null results ✅

**Urbach DR et al., *NEJM* 2014;370:1029-38 — Ontario.** Mandated, population-level. **101 hospitals; 109,341 procedures before, 106,370 after.**

| Outcome | Before | After | Adjusted OR | P |
|---|---|---|---|---|
| Operative mortality | 0.71% | 0.65% | **0.91 (0.80–1.03)** | **0.13** |
| Surgical complications | 3.86% | 3.82% | **0.97 (0.90–1.03)** | **0.29** |

**Reported compliance was near-ceiling: 99–100% at almost all of 97 large community hospitals; the lowest single hospital reported 91.6%.**

**Michigan Keystone *Surgery*** ✅ — Reames, Krell, Campbell, Dimick, *JAMA Surgery* 2015. 64,891 patients, 29 hospitals, same program design (checklist + CUSP) that worked in Michigan ICUs. 30-day mortality 2.1%→1.9% (P=.32); any complication 12.4%→13.2% (P=.26); difference-in-differences OR 0.84 (0.58–1.21). Authors' explanation: OR teams are more heterogeneous than ICU teams with "frequent personnel changes," and many sites lacked infrastructure to feed outcome data back to the front line.

### 2.3 Why implementation beats artifact — the numbers that settle it ✅

**Leape LL, "The Checklist Conundrum," *NEJM* 2014;370:1063-4** — the sharpest mechanism statements in the field, read verbatim:

> "**it is not the act of ticking off a checklist that reduces complications, but performance of the actions it calls for**"
> "**The checklist is merely a tool for ensuring that team communication happens.**"
> "changing practice is not a technical problem that can be solved by ticking off boxes on a checklist but **a social problem of human behavior and interaction**"
> "**gaming is universal**… If a checklist is required, the person responsible for documentation will ensure that all boxes are ticked. **In the absence of direct monitoring by observation, true compliance is unknown.**"
> "The likely reason for the failure of the surgical checklist in Ontario is that it was **not actually used**."

His Ontario forensics: 98% of hospitals self-reported use; **90% used an unmodified WHO or CPSI checklist** — which Leape reads as proof that "the team building needed for local adaptation did not occur." Educational materials were provided but **no team training or other support**.

**The documented-vs-observed gap, quantified:**

| Study | Documented | Observed |
|---|---|---|
| **Brown B et al., *BMJ Open Quality* 2021;10:e001593** — prospective direct observation | **100%** | **3.5%** (rising to 63% post-intervention). Title: "Surgical safety checklist audits may be misleading!" |
| **Møller KE et al., *Surgical Endoscopy* 2025** — OR Black Box video vs EMR, 45 gynaecological procedures | **89%** (EMR self-report) | **47%** (video) |
| van Klei WA et al., *Ann Surg* 2012;255:44-9 ⚠️ (via Leape) | — | **full compliance observed in only 39%**; mortality in the fully-compliant group was **44% of** the non-compliant group's; full compliance rose 12%→60% over six quarters |
| Pickering SP et al., *Br J Surg* 2013;100:1664-70 ⚠️ (via Leape) | — | pre-incision tasks completed in **55%** of operations; post-operative checklist in **9%** |

**The gap between 98–100% documented and 3.5–55% observed *is* the phenomenon.** Every downstream argument about checklist efficacy is really an argument about which of those two numbers a study measured.

Supporting texture: Younis Z et al., *Cureus* 2025 — 100% reported compliance with checklist *reading* alongside a persistent disconnect from actual surgical readiness, with engagement reduced to a "**tick-box exercise**" by "hierarchical theatre culture, workflow pressures." And Malucelli & Tivers, *Vet Rec* 2026 — **11 of 13 (85%)** locally-developed surgical checklists contained **non-killer items** not relating to patient safety: direct evidence of bloat degrading the artifact.

### 2.4 What actually moderates success ✅

- **Safety culture is the mediator.** Haynes et al., *BMJ Qual Saf* 2011;20:102-107: Safety Attitudes Questionnaire 3.91→4.01 (p=0.0127), and critically — **the degree of SAQ improvement at each site correlated with that site's complication reduction, r=0.7143, p=0.0381.** Also: **93.4% would want the checklist used if they were the patient.**
- **Leadership explanation and adaptation.** Conley, Singer, Edmondson, Berry & Gawande, *J Am Coll Surg* 2011;212:873-9: effectiveness "hinges on the ability of implementation leaders to **persuasively explain why** and **adaptively show how**." Where leaders did neither, staff "neither understood the rationale… nor were adequately prepared… leading to frustration, disinterest, and **eventual abandonment despite a hospital-wide mandate**."
- **South Carolina — the cleanest natural contrast with Ontario.** Haynes et al., *Ann Surg* 2017;266:923-929. **Voluntary, coached, collaborative.** 14 completing hospitals: risk-adjusted 30-day mortality **3.38% (2010) → 2.84% (2013)**, P<0.00001. 44 non-completers: **3.50% → 3.71%**, P=0.33. Pre-launch trends did not differ (P=0.33) but diverged after (P=0.021). **22% on difference-in-differences, P=0.0021.** Same artifact as Ontario, opposite result; the difference is coaching, voluntariness, and local adaptation.
- **VA Medical Team Training — the dose-response study.** Neily et al., *JAMA* 2010;304:1693-1700. 182,409 procedures, 108 VHA facilities. Intervention = **required briefings and debriefings** plus 2 months preparation, a 1-day conference, and **a year of quarterly coaching**. 74 trained facilities: **18% mortality reduction (RR 0.82, 95% CI 0.76–0.91, P=.01)** vs 7% in 34 untrained (RR 0.93, NS). Propensity-matched decline ~50% greater (RR 1.49, 1.10–2.07, P=.01). **Dose-response: 0.5 fewer deaths per 1,000 procedures for every quarter of the program (95% CI 0.2–1.0, P=.001).**
- **Scotland** ✅ — Ramsay G et al., *Br J Surg* 2019;106:1005-1011. 6,839,736 surgical admissions 2000–2014; inpatient mortality **0.76% → 0.46%**; "**a 36.6 (95% c.i. −55.2 to −17.9) per cent relative reduction in mortality (P<0.001)**"; no comparable trend in the non-surgical cohort. **Attribution caveat that stands on the paper's own data:** this is an ecological interrupted time series in which the checklist was one component of a whole national programme (SPSP), over 15 years, with no way to separate it from secular improvement or coding drift. The widely-circulated "37%" is a loose restatement of a point estimate with a very wide CI.
- **Aviation CRM in the OR, and its decay** ✅ — Ricci MA & Brumsted JR, *Aviat Space Environ Med* 2012;83(4):441-4. Academic medical center, 19,000 procedures/year: **pre-operative briefing 6.7% → 99% within 4 months**; wrong-site surgeries and retained foreign bodies **7 (2007) → 0 (2008) → 5 (2009) after 14 months without additional training**; malpractice expenses **$793,000 (2003–2007) → zero since 2008**. Conclusion: "**constant reinforcement and refresher training is necessary for sustained results.**"

### 2.5 Crisis manuals — where the artifact alone *does* work ✅

**Arriaga AF et al., *NEJM* 2013;368:246-253.** The cleanest experimental separation of artifact from culture anywhere in the field.

- **17 OR teams, 3 institutions, 106 simulated surgical crises.** Each team randomly assigned to manage **half** the scenarios with crisis checklists and half from memory — within-team crossover, same rooms, same day.
- **6% of critical steps missed with checklists vs 23% without, P<0.001.**
- **Adjusted relative risk 0.28 (95% CI 0.18–0.42).**
- **"Every team performed better when the crisis checklists were available than when they were not."**
- **97% of participants said they would want the checklist used if the crisis happened to them.**

These were **experienced OR teams, not novices**. The correct reading is not novice-vs-expert but **frequency**: these are events that are common institutionally and rare individually. Expertise built on recognition (§4.5) has no prototype to recognize for an event a clinician meets once a decade.

**Meta-analytic anchor** ✅ — Greig PR et al., *Anaesthesia* 2023;78:343-355. 13 RCTs across 16 publications: missed steps **43.3% → 11.0%; risk ratio 0.29 (95% CI 0.16–0.51), p<0.001**. Judgment on format: "**read-do is particularly appropriate for emergency situations**" where actions must be completed in order. **Caveat: only 2 of 13 trials tested aids in actual clinical practice** — the evidence base is a simulation literature.

**The Stanford Emergency Manual** ✅ (V3.1 read directly; https://emergencymanual.stanford.edu/). **25 critical events** (26 in V4), indexed three ways on the cover: by perioperative ACLS rhythm, by **broad differential** (Hypotension, Hypoxemia — the two "I don't know what's wrong" entry points), and by specific event. Plus a Crisis Resource Management page and a **phone list pre-filled with every OR, ICU, blood bank and code number.**

A typical event page: SIGNS → a fixed red block "**1. CALL FOR HELP. 2. CALL FOR CODE CART. 3. INFORM TEAM.**" → numbered immediate actions **with drug doses inline** → DIAGNOSIS differential → explicit cross-references ("Go To VF/VT, event 6") → END. A separate page gives concentration and dose for ~24 vasoactive drugs so nobody computes mg/ml under stress.

Stated design driver: "**Observing that practitioners often miss key actions under stress.**" Lineage: Gaba, Howard & Fish, *Crisis Management in Anesthesiology* (1994), via VA Palo Alto; human-factors input from Barbara Burian (NASA). The 12 CRM key points are visibly imported from aviation: Call for Help Early · Anticipate and Plan · Allocate Attention Wisely · **Use Cognitive Aids** · **Establish Role Clarity** · **Designate Leadership**.

**The reader role — the strongest single experiment on *who* operates the aid** ✅. McEvoy MD et al., *Reg Anesth Pain Med* 2014 (https://pmc.ncbi.nlm.nih.gov/articles/PMC4068273/). 31 anesthesiology residents, randomized, in-situ simulated local anesthetic systemic toxicity:

| | Designated Reader + electronic aid (n=16) | Memory alone (n=15) | P |
|---|---|---|---|
| Overall correct actions | **99.3%** | **72.2%** | <0.0001 |
| Critical-step adherence | **99.5%** | **70.0%** | <0.0001 |
| **Completed *all* critical steps** | **15/16 (93.8%)** | **0/15 (0%)** | <0.0001 |

**The mechanism:** without a separate reader, the team leader must attend either to the tool or to the patient — **task saturation collapses the aid back into memory-based management.** The reader role works by decoupling aid operation from clinical leadership.

⚠️ **The field is unresolved on who reads.** Huang J et al., *Cureus* 2019 (114 anesthesiologists, 7 hospitals): 57.89% preferred a **senior physician** as reader, on accountability grounds — which directly contradicts McEvoy's task-saturation finding. Best location: **anesthesia station in the OR, 92.11%.**

**The real-world uptake problem — the biggest failure mode for crisis manuals** ✅:

| Study | Real-world use |
|---|---|
| Clebone A et al., *PLoS One* 2025 | **7%** of described critical events involved cognitive-aid use (26/335). Pre 6%, post 9%. **"Not Needed" was the only non-use reason that did not improve** (60→57) |
| Goldhaber-Fiebert SN et al., *J Clin Anesth* 2023 | ~24,000 cases: peri-crisis use **0.55% → 0.17% at 1 yr → 0.21% at 6 yrs**. But in **cardiac arrest specifically, used in ~half** of cases throughout |
| Goldhaber-Fiebert SN et al., *Anesth Analg* 2020 | Where used: decreased individual stress **95%**, enabled teamwork 73%, **key action improvements in 59%** of cases; no perceived harm |

**Availability is solvable; the clinician's in-the-moment judgment that they don't need it is not.**

**Malignant hyperthermia — time is the variable** ✅ (Toyota Y et al., *BioMed Res Int* 2023): mortality fell from ~70% in the 1960s to 15% with dantrolene. Japanese registry n=128: dantrolene-treated 9.6% mortality vs untreated 30.8%. **Deceased patients had onset-to-dantrolene of 100 min vs 45.0 min in survivors (P<0.001).** The MHAUS protocol accordingly puts a phone number (1-800-644-9737) and a weight-based dose inline.

### 2.6 Gawande's actual design rules — with two corrections ✅

Read verbatim from "A Checklist for Checklists" (Gawande, Boorman, Berry). ⚠️ **Provenance warning: projectcheck.org's root domain is now compromised and serves casino spam.** The PDF still resolves and its content is authentic; cite the content, not the domain.

Header: "**Please note: A checklist is NOT a teaching tool or an algorithm.**"

**DEVELOPMENT** — is each item:
- **"A critical safety step and in great danger of being missed?"** ← *killer items, operationalized*
- **"Not adequately checked by other mechanisms?"**
- **"Actionable, with a specific response required for each item?"**
- **"Designed to be read aloud as a verbal check?"**

**DRAFTING** — "Utilize natural breaks in workflow (**pause points**)?" · one page · sans serif, upper and lower case, dark on light · **"Are there fewer than 10 items per pause point?"**

**VALIDATION** — trialed with front-line users · **"Modified in response to repeated trials?"** · **"Detect errors at a time when they can still be corrected?"** · completable in "a reasonably brief period of time."

**Two corrections to the popular version:**
- ❌ **"5–9 items" is not what the primary design document says.** It says **"fewer than 10 items per pause point."**
- ❌ **"Under 60 seconds" is not in the document.** It says "a reasonably brief period of time." Do not cite a number here without a book page reference.
- ⚠️ **Read-do vs do-confirm is not in the Checklist for Checklists.** The distinction is real and live in the medical literature — Greig 2023 judges **read-do appropriate for emergencies**; Dryver 2023 implements **do-confirm** as an ED default — but I could not verify the definitions against Gawande's book text.

### 2.7 Pronovost's Keystone ICU — what the "5-item checklist" actually was ⚠️

*(NEJM returned 403 to every fetch route; figures are secondary-verified and consistent with the widely reported record.)*

Pronovost et al., *NEJM* 2006;355:2725-2732. 103 ICUs in 67 hospitals, **1,981 ICU-months, 375,757 catheter-days**, ~85% of Michigan ICU beds. Median CRBSI rate **2.7 per 1,000 catheter-days → 0** (P≤0.002 at all post periods); incidence-rate ratio 0.62 (0.46–0.85) at 0–3 months → **0.15 (0.07–0.32) at 16–18 months**.

**The five items:** hand washing · full-barrier precautions · chlorhexidine antisepsis · avoid the femoral site · remove unnecessary catheters.

**What was in the intervention besides the list — this is the point:**
- **Clinicians were empowered to stop the procedure** if they observed a guideline violation in non-emergent situations
- A **central-line cart** stocking all required supplies in one place (removes the "I'd have to go get it" defeater for full-barrier precautions)
- **Daily rounds explicitly asking whether any catheter could be removed** — converts an intention into a recurring external prompt
- Monthly and quarterly **feedback of unit-level rates** to the teams
- CUSP, trained unit-based nurse and physician leaders, executive partnership

**The honest description:** the list was the smallest component. Two of five items were converted into daily verbal rounds questions; one into a supply-cart logistics change; and the whole thing was backstopped by an **authority inversion** — a nurse could halt a physician's procedure.

**And the list's real function was to make that authority inversion legible.** A nurse cannot easily say "you're doing this wrong." A nurse *can* say "step 3 isn't done." The checklist converts an interpersonal challenge into a procedural observation. That is the same trick as the two-challenge rule in §1.9, arrived at independently.

Acknowledged limitations: **no data on intervention compliance**, possible under-reporting, possible Hawthorne effect, observational design, and **no way to attribute effect to any single component.**

⚠️ **Matching Michigan** — the English attempt to replicate. Dixon-Woods M et al., *Implementation Science* 2013;8:70: infection rates fell, but the fall **could not be attributed to the programme**, because the same practices were arriving by other routes. "Improved implementation of procedural good practice may occur through many different routes, of which **program participation is only one**." **Context, not content, carried the Keystone result.** The checklist travelled; the programme did not.

---

## 3. NUCLEAR AND SUBMARINE

### 3.1 The record, and the part everyone omits ✅

*The U.S. Naval Nuclear Propulsion Program 2025* (DOE/NNSA), verbatim: "over **177 million miles** safely steamed on nuclear power… currently operates 97 reactors and has accumulated over **7,600 reactor-years of operation**." And: "**Throughout the Program's history there has never been a reactor accident**, nor any release of radioactivity that has had an adverse effect on human health or the quality of the environment."

**The doctrine — including the design half that is usually dropped when this culture is cited** (p. 21):

> "The Program's small and relatively uncomplicated pressurized-water reactors are **inherently stable and can respond to operational transients without the need for immediate operator action.**"

**Naval Reactors does not rely on procedural excellence to survive a transient.** Compare INSAG's judgment on Chernobyl (§3.6): reliance on "quick action by the operating staff" was "**in unacceptable conflict with this fundamental design tenet**." Any argument that imports the nuclear-navy compliance culture without importing the design conservatism is importing half a system.

**Rickover on responsibility**, reproduced in the official report:

> "Responsibility is a unique concept: it can only reside and inhere in a single individual… **Unless you can point your finger at the person who is responsible when something goes wrong, then you have never had anyone really responsible.**"

**The anti-cookbook clause** (p. 23): "Rickover recognized that nuclear propulsion plant operators must know more than simply **what** to do in any given situation: they must understand **why**."

From "Doing a Job" (1981/82, https://govleaders.org/rickover.php): "the devil is in the details… I probably spend about ninety-nine percent of my time on what others may call petty details" · "All work should be checked through an **independent and impartial review**" · "It is a human inclination to hope things will work out, despite evidence or doubt to the contrary. **A successful manager must resist this temptation.**"

⚠️ **The 1979 post-TMI congressional testimony (24 May 1979) could not be verified verbatim** — the only public copy is an image-only scan. The three-element framing (technical competence, total responsibility, facing the facts) plus 18 further elements is attested secondhand only.

### 3.2 The human performance tools — precise moment-of-action mechanics ✅

Primary sources: **DOE-HDBK-1028-2009 Vol 1 & Vol 2** (https://www.energy.gov/sites/default/files/2026-04/doe-hdbk-1028-2009_volume1_0.pdf; https://bushcohpi.com/wp-content/uploads/2017/05/DOE-HPI-Manual-Vol-2-HPI-Tools.pdf) and **NRC ADAMS ML102120052** (a utility fleet procedure that explicitly cites INPO 06-002 and is the best public proxy for INPO's own mechanics). INPO 06-002/06-003/09-004 are member-restricted and unobtainable.

The organizing claim, Vol 2 p. 5: **"All human performance tools deliberately slow things down to ultimately speed things up."**

**THREE-PART COMMUNICATION** (Vol 2 p. 26). "The person originating the communication is the sender and is **responsible for verifying that the receiver understands the message as intended**."

1. Sender states — face-to-face when practical, addressing the receiver by name or position.
2. **Receiver paraphrases back in his or her own words** — but **"Equipment designators and nomenclature are repeated word for word."**
3. Sender acknowledges: **"That is correct."** / **"That is wrong"** + restates.

*That step-2 split is the discriminator: paraphrase the instruction to prove comprehension; repeat the identifier verbatim to prove no substitution.*

Worked example (ML102120052 p. 40):
```
CRS to RO:  "Jim, stop Alpha Reactor Coolant Pump."
RO to CRS:  "Understand, stop Alpha Reactor Coolant Pump."
CRS to RO:  "That is correct."
```

Phonetic alphabet is applied **conditionally, only at the point of ambiguity**: "When the only distinguishing difference between two component labels is a single letter, then the phonetic alphabet form of the letter should be substituted."

At-risk practices include "**Receiver taking action before the communication is complete**" and "Receiver not writing the message on paper if there are several items (more than two) to remember."

❌ **The numeric readback rule ("one-five" not "fifteen") is NOT in DOE-HDBK-1028-2009.** A regex sweep of all 312 pages of both volumes plus ML102120052 returned zero hits, and DOE's own worked example says "eighteen." The convention is real but lives in FAA/ICAO phraseology and probably DOE-STD-1031-92, which is unretrievable. **Do not attribute it to the DOE handbook.**

**SELF-CHECKING / STAR** (Vol 2 pp. 18–19). "attention must peak when the risk is greatest — **when altering a component's status**."

| | |
|---|---|
| **S — Stop** | Pause before critical activities; eliminate distractions |
| **T — Think** | Understand what will happen; verify conditions match the pre-job brief; **identify expected outputs/results**; compare to the controlling document; consider a contingency |
| **A — Act** | "**Without losing eye contact with the component, read and touch the component label.** Compare the component label with the guiding document." Then perform |
| **R — Review** | "**Verify that outputs or results match the expected outputs/results.**" Perform the contingency if not |

Note the structure of **Review**: it does not ask "did I do it right." It compares the plant's actual response to an expectation **formed before the action, in Think**. That is what makes it error-*detection* rather than self-congratulation — and it is why the pre-job brief (below) is load-bearing: without it, Review has nothing to compare against and degrades into "looks fine."

**The observable motor sequence — POINT / READ / READ** (ML102120052 p. 15):

> "Identify the correct item by **physically pointing** to the component label, before taking any action. (POINT) / Read the document that directs manipulation of the component. **The best technique is to read this aloud, even if alone**, to use the additional human attributes of speaking and listening. (READ) / Read the component label. Again, read out loud. (READ) / Perform the intended action. For physical actions, **ensure hand contact is not lost**."

Two rules from the same page carry most of the weight:

> "Self-checking must be performed **against controlled information sources**" — formal component tags (*not* magic-marker labels), controlled postings (*not* hand-drawn), actual procedure requirements (*not* "off the top-of-the-head").
> "**By making self-checking observable we improve the formality and focus with which the tool is applied while providing peers and supervisors an opportunity to coach the quality of the self-checking.**"

**This is the industry independently rediscovering *shisa kanko*, and for the stated reason: an unobservable self-check is unauditable and therefore optional.**

**PEER CHECK vs CONCURRENT vs INDEPENDENT VERIFICATION** — the distinction is precise and is usually botched in secondary accounts. Vol 2 p. 41, verbatim:

> "peer-checking focuses on **preventing a mistake by the performer**, independent verification and concurrent verification focus more on **confirming the correct configuration or status**."
> "'**Checking**' refers to the confirmation of a correct **action**… '**Verification**' refers to the confirmation of the **condition** of equipment."

And the timing axis (ML102120052 p. 29): "**CV and PC occur *before* the action is taken, while IV occurs *after*.**"

| | **Peer Check** | **Concurrent Verification** | **Independent Verification** |
|---|---|---|---|
| Object | the **action** | the **condition** | the **condition** |
| Second person | co-located, same time | side by side | **absent — separated in time *and* distance** |
| Catches error | before it happens | before/during | **after it happened** |
| Independence | informal | *"true independence cannot be achieved"* | full freedom of thought |
| Rigor | *"the least rigorous"* | middle | *"higher probability of catching an error than PC or CV"* |

**The operative definition of "independent"** (Vol 2 p. 46): "**Separation by distance** is established when **audible or visual cues of either person are not detectable by the other person**… the verifier is not in a position to either observe or hear the performer." The verifier's step 2 is the whole trick: "**Determine the as-found condition, without changing it**," "without relying on observation of or oral confirmation by the performer."

**The rule that decides when IV is forbidden** (ML102120052 p. 34): "**IV can only be used when an immediate, adverse consequence of a mistake by the performer cannot occur, because IV catches errors after they have been made, not before or during.**"

**The underlying probabilistic assumption** (DOE O 422.1 self-study): "the chance that **two operators will independently make the same mistake is unlikely**." That sentence is the entire load-bearing assumption — and **common-mode error** (shared bad mental model, shared bad procedure, shared time pressure) destroys it. When the two checkers are correlated, IV's value collapses toward zero while its cost stays constant. Practices that silently void independence, per the handbook: performer and verifier walk to the component together; **verifier uses the same indicator as the performer**; **performer tells the verifier what has been done**; verifier junior to performer and reluctant to question.

**PRE-JOB BRIEF — SAFER** (Vol 2 pp. 6, 39), verbatim:
- **S** — Summarize the critical steps
- **A** — Anticipate errors for each critical step and relevant error precursors
- **F** — **Foresee probable *and worst-case* consequences** should an error occur during each critical step
- **E** — Evaluate controls or contingencies at each critical step to prevent, catch, and recover from errors
- **R** — Review previous experience and lessons learned

Required agenda includes: **human performance tools for each critical step**; **operating experience**; and **stop-work / pause-work criteria, contingencies, and the person(s) responsible for critical decisions.**

The **reverse briefing** (p. 39): the supervisor requires the individual to summarize **in his or her own words** the task requirements, credible consequences of an error, **stop-work/abort criteria**, and any concerns — "renegotiate deadlines, if necessary." *This is the verification that the expectation actually transferred.*

Graded approach — and the sharpest sentence in the handbook, from the high-hazard/simple cell: "**Most events occur during so-called 'routine' activities.**" At-risk: "Conducting the meeting as a monologue"; "Using a '**cookbook**' approach… covering every item in the same manner regardless of its applicability."

**PLACEKEEPING** (Vol 2 p. 29): "physically marking steps in a procedure that have been completed. Effective place-keeping **prevents omitting or duplicating steps**."

The eight sanctioned techniques include the circle-slash: "**Circling the step number, denoting it 'in progress,' and slashing through the circle to indicate completion.**" Note the semantics: **circle = claimed/in progress (applied *before* acting); slash = complete.** That is what makes it survive an interruption — the mark records not just "done" but "started and not finished." The INPO-lineage mapping is exact: **circle → Stop, read → Think, perform → Act, slash → Review.**

Required "when performing a **continuous-use** procedure" and "when performing a **reference-use** procedure on risk-important equipment."

At-risk practices, which read as a taxonomy of how the artifact becomes fiction: "Writing one set of initials followed with a vertical line through remaining signoff blanks" · "Signing or checking off a step as completed **before** it is completed" · "**Signing off several steps at the same time**" · "**Using ditto marks (″)**" · "Not verifying completion of the last step checked off, if job was interrupted."

**FLAGGING** (Vol 2 p. 51) — the physical-space analog for *wrong component* rather than *wrong step*: "**taking a break or being distracted from one component and subsequently going back to work on an adjacent, similar — but wrong — component.**" Workers may also flag similar components that are **NOT** to be touched. At-risk: "Using a flagging device that can easily become dislodged such as a post-it-note."

**PAUSE WHEN UNSURE** (Vol 2 pp. 16–17). ❌ "Take a Minute" is not the DOE name. The DOE tool notes that in knowledge-based territory the chance of error is "**a 10 percent to 50 percent probability**," and prescribes: **1) Pause. 2) Place equipment and job site in a safe condition. 3) Notify your immediate supervisor. 4) Get help.** "**Every person has the responsibility and authority to stop work when uncertainty persists.**"

The fleet procedure adds the rule that targets the real failure mode: "**Do not answer your own question. Notify your supervisor.**" And a naming critique worth stealing: "A better name for this tool might be **stop when you *should* be unsure**."

**QUESTIONING ATTITUDE — the danger-word trigger list** (Vol 2 p. 10). This is the concrete, listenable trigger that makes an attitude into a mechanism:

> "Upon hearing the danger words: '**I assume**,' '**probably**,' '**I think**,' '**maybe**,' '**should be**,' '**not sure**,' '**might**,' '**we've always...**'"

Plus: "**State or verbalize the uneasiness or question in clear terms**" and "**People, in general, are reluctant to fear the worst, and a healthy questioning attitude will overcome the temptation to rationalize away 'gut feelings' that something is not right.**"

**STOP-WORK AUTHORITY** is regulatory, **10 CFR 851.20**: §(b)(8) the right to **decline to perform**, and §(b)(9) the right to **"Stop work when the worker discovers employee exposures to imminently dangerous conditions or other serious hazards; provided that any stop work authority must be exercised in a justifiable and responsible manner"** — both "without reprisal." Note the asymmetry: (b)(8) is self-protective; (b)(9) protects others and carries a qualifier that, in a punitive culture, converts a right into a risk.

**Error rates by performance mode** (Vol 1 pp. 2-22 to 2-26):

| Mode | Error probability | Share of time | Share of all errors | Prevalent error |
|---|---|---|---|---|
| Skill-based | "less than **1 in 10,000**" | "~**90%** of daily activities" | "only **25%** of all errors" | inattention (slips/lapses) |
| Rule-based | "roughly **1 in 1,000**" | — | "roughly **60%**" | misinterpretation |
| Knowledge-based | "**one in two (50%) to one in ten**" | — | "roughly **15%**" | inaccurate mental model |

⚠️ Provenance caveat: attributed only to "a study in the nuclear power industry"; endnotes unresolved, and 25+60+15=100 is a suspiciously clean partition across three separately-cited sources. ❌ **The "workers make about 5 errors per hour" claim is verified ABSENT from the handbook — do not attribute it.**

**The strategic formula**, stated twice: **Re + Mc → ØE** (reduce error, manage controls), with the asymmetry that matters most: "**Reducing the error rate minimizes the frequency, but not the severity of events. Only controls can be effective at reducing the severity of the outcome of error.**"

Error precursor top-of-list per quadrant: Task Demands #1 = **time pressure (in a hurry)**; Work Environment #1 = **distractions/interruptions**; Individual Capabilities #1 = **first time / unfamiliarity**; Human Nature #1 = **stress**. And the qualifier: "by themselves, error precursors do not define an error-likely situation. **A human act or task must be either planned or occurring concurrent with error precursors.**"

### 3.3 Procedural compliance levels — the grading that is the real idea ✅/⚠️

| Level | Where the procedure physically is | What the user must do |
|---|---|---|
| **Continuous use** | **In hand** | Read each step **before** performing it; perform in sequence; **placekeep every step** |
| **Reference use** | **At the job site** | Refer periodically to confirm all steps and data entries; placekeeping required when equipment is risk-important |
| **Information use** | **On hand, or in the library** | Available for reference; no step-by-step marking |

⚠️ The formal source is **INPO 09-004, *Procedure Use and Adherence Guidelines*** (2009), which is member-restricted; the level descriptions above come from an INPO-citing secondary source. **DOE's binding tie-in is verified** (Vol 2 p. 29).

**Why the classification is the transferable part:** it is an explicit institutional admission that **verbatim compliance is not free.** The industry does not claim procedures should always be in hand and marked step-by-step; it **grades the cost of formality against irreversibility.** That grading — not the compliance — is the idea worth exporting. It is the same principle as Wan & Bolton's minimally-constraining-intervention rule (§0.2), arrived at operationally.

### 3.4 Marquet and "take deliberate action" ✅

**USS Santa Fe, 29 January 1999, Pearl Harbor.** A petty officer energized breakers on the pier after conditions were met but **without clearing the red tag**. Marquet: "**You don't want to be accidentally safe.**"

The sailor's own account, verbatim:

> "Well, I knew we met conditions to shut the breaker, and was just thinking that was the next step in the procedure. **We had the procedure out and had reviewed it. I knew the red tags were hanging but just moved them aside to shut the breaker.** Not sure what I was thinking."

Marquet declined captain's mast and spent **seven and a half hours** on causes. Refresher training was rejected (no knowledge deficiency). More supervision was rejected (would have caught breakers two and three, not the first). Then the diagnosis:

> "Well, **he was just in auto. He didn't engage his brain before he did what he did; he was just executing a procedure.**"

**The mechanism:**

> "prior to any action, the operator **paused, vocalised and gestured toward what he was about to do**, and only after taking a deliberate pause would he execute the action."
> "**it didn't matter whether anyone was around or not. Deliberate actions were not performed for the benefit of an observer or an inspector.** They weren't for show."

**The outcome**, per the senior inspector after Santa Fe's reactor-operations inspection:

> "**Your guys made the same mistakes — no, your guys *tried* to make the same number of mistakes — as everyone else. But the mistakes never happened because of deliberate action. Either they were corrected by the operator himself or by a teammate.**"

https://aerossurance.com/helicopters/deliberate-action-mindfulness/

**The tension, resolved.** Marquet's intent-based leadership pushes authority *down*: "with intent, **the default is action absent a veto** whereas with permission the default is stasis absent approval." That looks contradictory with strict compliance. It is not, because the two operate on different objects: **"I intend to…" moves the *decision* down. "Take deliberate action" slows the *execution* down.** He did not delegate whether to follow the red-tag procedure; he delegated the authority to act without asking, then installed a mandatory pause at the hand-on-the-breaker moment.

And note what the Santa Fe incident exposes that classical compliance cannot reach: **the procedure was out, it had been reviewed, and the sailor was compliant in intention and non-compliant in fact.** A red tag is a *symbolic barrier* — a sign. A physical lockout would have been stronger. Deliberate action is a **cognitive control installed because the physical control was weak.**

One more mechanism detail that is easy to miss: the tool became adoptable **because he suspended the punishment.** "I think that the crew, knowing their shipmate had been spared captain's mast, were more receptive to the alternative."

### 3.5 Three Mile Island — the case where following the procedure destroyed the core ✅

All quotes from the **Kemeny Commission report** (October 1979): http://large.stanford.edu/courses/2012/ph241/tran1/docs/188.pdf

**The instrument that lied** (Finding A.3):

> "The pilot-operated relief valve… failed to close… **Instruments in the control room, however, indicated to the plant staff that the valve was closed**… The operators, relying on the indicator light and believing that the PORV had closed, did not heed other indications and were unaware of the PORV failure; **the LOCA continued for over 2 hours**."

The light showed that the *signal to close had been sent* — not the valve's state. Same class of failure as Eastern 401's inhibited annunciator, seven years apart.

**The procedure that was wrong** (Finding A.4):

> "**the operators were conditioned to maintain the specified water level in the pressurizer** and were concerned that the plant was 'going solid'… Therefore, **they cut back HPI from 1,000 gallons per minute to less than 100 gallons per minute**… **If the HPI had not been throttled, core damage would have been prevented in spite of a stuck-open PORV.**"

Finding A.6: "Some of the key TMI-2 operating and emergency procedures in use on March 28 were inadequate… **Deficiencies in these procedures could cause operator confusion or incorrect action.**"

**The precedent that was known and not transmitted** (Finding A.7): the September 1977 **Davis-Besse** event — same B&W plant, PORV stuck open, pressurizer level rising while pressure fell, operators improperly interfering with HPI. A B&W engineer wrote internally, **more than a year before TMI**, that at full power "it is quite possible, perhaps probable, that core uncovery and possible fuel damage would have occurred." An NRC official flagged it in January 1978. **"Again no notification was given to utilities prior to the accident."**

**The hollow defenses** (Finding E.5) — and note that these are *exactly* the defenses the HP toolkit later formalized:

> "A shift supervisor testified that there had never been **less than 52 alarms lit** in the control room."
> "When shifts changed in the control room, **there was no systematic check on the status of the plant and the line-up of valves**." *(→ status control at turnover)*
> "**On the day of the accident, emergency feedwater block valves which should have been open were closed. They may have been left closed during a surveillance test 2 days earlier.**" *(→ independent verification of restoration)*
> "although Met Ed procedures required closing the PORV block valve when tailpipe temperatures exceeded 130°F, **the block valve had not been closed even though temperatures had been well above 130°F for weeks**."
> "**Eight hours into the accident, Met Ed personnel spent 10 minutes trying unsuccessfully to locate three decay heat valves in a high radiation field.**" *(→ component labeling)*

**Training that passed the test and failed the accident** (F.1–F.2): "**The TMI training program conformed to the NRC standard for training.** Moreover, TMI operator license candidates had **higher scores than the national average**… Nevertheless, the training of the operators proved to be inadequate." And the simulator gap: it "**was not… programmed to reproduce the conditions that confronted the operators**… unable to simulate increasing pressurizer level at the same time that reactor coolant pressure was dropping."

**The Commission's systemic verdict — the most quotable passage in the entire subject:**

> "**we are convinced that regulations alone cannot assure safety. Indeed, once regulations become as voluminous and complex as those regulations now in place, they can serve as a negative factor in nuclear safety.** The regulations are so complex that immense efforts are required… to assure that regulations are complied with. **The satisfaction of regulatory requirements is equated with safety.**"

**The structural fix — and this is the most important design lesson in the report.** After TMI the NRC issued NUREG-0899, and the industry converted **event-based EOPs to symptom-based EOPs.** Westinghouse: "Westinghouse was a leader in **converting event-based EOPs to the new symptom-based format**. Today, procedure guidance must be symptom based, while addressing multiple events, multiple failures, inadequate core cooling events and ATWS."

An *event-based* procedure requires the operator to **diagnose correctly first**, then select the right procedure. TMI proved diagnosis can be impossible when the instruments lie. A *symptom-based* procedure keys off directly observable parameters (subcooling margin, core exit thermocouples, level, pressure) and prescribes actions that are safe **regardless of which event is actually occurring**. **It removes the correct-diagnosis precondition from the critical path.** That is a change to procedure *architecture*, not an exhortation to comply harder — and it is the single most transferable idea in this section.

### 3.6 Chernobyl — and the partial retraction of "operator violation" ✅

**IAEA Safety Series No. 75-INSAG-7** (1992), full text: https://www-pub.iaea.org/MTCD/publications/PDF/Pub913e_web.pdf

INSAG-1 (1986) had accepted the Soviet account that "the accident arose through a low probability coincidence of a number of **violations of rules and procedures by the operating staff**." INSAG-7 retracts substantial parts of it, §5.2.1, verbatim:

> "— The statement was made that there was a proscription on continuous operation below 700 MW(th). **This statement was based on incorrect information. There should have been such a proscription, but there was none at the time.**"
> "— … **operation of all eight pumps at once was not forbidden by any document**, including the test procedures."
> "— **Disabling of the ECCS was not prohibited in principle under normal procedures at Chernobyl**… in accordance with regulations, **special approval for this disabling had been obtained from the Chief Engineer.**"
> "— Disabling of the 'two turbine' trip **was allowed, and indeed was required by normal procedures at low power levels.**"

**Conclusion §6(6):**

> "The weight given in INSAG-1… **which laid blame almost entirely on actions of the operating staff, is thereby lessened. Certain actions by operators that were identified in INSAG-1 as violations of rules were in fact not violations.** … **The poor quality of operating procedures and instructions, and their conflicting character, put a heavy burden on the operating crew**… the type and amount of instrumentation as well as the control room layout made it difficult to detect unsafe reactor conditions. However, operating rules **were** violated… **Most reprehensibly, unapproved changes in the test procedure were deliberately made on the spot**, although the plant was known to be in a condition very different from that intended."

**The parameter that was safety-critical and never presented as such** (§4.2): the Operating Reactivity Margin. "**the importance of the quantity for the safety of the plant seems to have been poorly understood by the operators**… **the magnitude of the ORM was not conveniently available to the operator, nor was it incorporated into the reactor's protection system**… **the operators seemed not to be aware of the other reason for the importance of the ORM**, which was the extreme effect it could have on the void and power coefficients."

And on the known-but-unfixed positive scram effect: after its discovery at Ignalina in 1983, restrictions on full control-rod withdrawal were announced. "**Such restrictions were never imposed and apparently the matter was forgotten.**"

**Design vs operators** (§5.1): "The prevention of an accident due to a fast acting positive power coefficient **depended on quick action by the operating staff; this was in unacceptable conflict with this fundamental design tenet.**" And INSAG-1's own first lesson, quoted back: "**Nuclear plant designs must be as far as possible invulnerable to operator error and to deliberate violation of safety procedure.**"

**What INSAG did *not* retract — and the cleanest statement anywhere of the correct stop-work trigger** (§5.2.2):

> "When the reactor power could not be restored to the intended level, **the operating staff did not stop and think, but on the spot they modified the test conditions to match their view at that moment of the prevailing conditions.**"
> "**Where in the process it is found that the initial procedures are defective or they will not work as planned, tests should cease while a carefully preplanned process is followed to evaluate any changes contemplated.**"

The trigger for stopping is **"the procedure is not working as planned,"** not **"I am uncomfortable."** That is the industrial ancestor of DOE's "Pause When Unsure," and it is a far more actionable criterion than a feeling.

❌ **Not verified:** USS Fitzgerald and USS John S. McCain (NTSB/MAR-19/01, /02), USS Greeneville (2001), USS San Francisco (2005), and the Davis-Besse **2002** reactor-head corrosion event. The parallel agent retrieving those did not finish. ⚠️ If the McCain finding holds as commonly reported (touchscreen helm control transfer, unganged throttles, HMI criticism, Navy reversion to physical controls), its taxonomic slot is the same as TMI's PORV indicator and Eastern 401's inhibited annunciator — **an interface that defeated a trained procedure** — 38 years later. Confirm from the primary report before using it.

### 3.7 Does the model transfer? Read-back in healthcare ✅

The best single number, and it is a good one:

> Barenfanger J, Sautter RL, Lang DL, Collins SM, Hacek DM, Peterson LR. "Improving patient safety by repeating (read-back) telephone reports of critical information." *Am J Clin Pathol* 2004;121(6):801-3. PMID 15198350.
> "**Of 822 outgoing telephone calls from the laboratory, 29 errors were detected (error rate 3.5%). Calls to physicians had the highest rate of errors (6/95 [5%]). The time required to ask for the information and for the message to be repeated averaged 12.8 seconds per call, which corrected 29 errors.**"

**12.8 seconds per call; 3.5% of critical-result transmissions caught wrong.** Note this is an *error-detection* rate, not an outcome study — it does not demonstrate harm avoided. ❌ I found no retrievable evidence measuring *sustained real-world compliance* with read-back in healthcare, which is the obvious weak point.

The self-checking analog also transferred: Violato & Cheung, "Teaching pointing and calling (Shisa Kanko) to reduce error and improve performance," *Medical Teacher* 48:754–756 (2025). Their key implementation lesson echoes Marquet exactly: "**clarifying that P&C is a personal cognitive tool, not a directive to others.**"

⚠️ **Currency note:** effective 1 January 2026 the Joint Commission replaced the National Patient Safety Goals chapter with **National Performance Goals (NPGs)**. ❌ The verbatim 2003 NPSG 2A read-back text could not be retrieved.

---

## 4. THE CRITIQUES

### 4.1 Checklist fatigue — real as ritualization, not demonstrated as load ✅

**Decay over time is real.** Shrestha & Medhasi, *Ann Med Surg* 2026: tertiary neurosurgical centre, checklist **unfilled in 21% of emergency cases in 2020, worsening to 38% by 2023**. And Ricci & Brumsted's OR CRM decay (§2.4): 0 events in 2008 → 5 in 2009 after 14 months without reinforcement.

**But two studies specifically looked for additive-load fatigue and did not find it:**
- Timm-Holzer E et al., *Frontiers in Psychology* 2023, titled "**No signs of check-list fatigue**": 356 observed timeouts across three hospitals; adding a *second* intraoperative briefing protocol **increased** timeout completeness, engagement and pace quality.
- Etheridge JC et al., *J Surg Res* 2022: adding a Device Briefing Tool — 82% adherence, "no evidence of checklist fatigue."

**The defensible synthesis: checklist fatigue is well-demonstrated as *ritualization* (3.5% observed vs 100% documented) and poorly demonstrated as *additive load*. These are different critiques with different remedies, and conflating them weakens the argument.** Adding one more well-designed item does not obviously break the system; hollowing the items out does.

❌ **A clean dose-response curve of compliance against item count does not appear to exist** for clinical checklists. The functional analogue lives in the alert literature (§4.2).

### 4.2 Alarm fatigue — the best-quantified case of signal becoming noise ✅

**The Joint Commission, Sentinel Event Alert 50** (2013): **98 alarm-related events** Jan 2009–Jun 2012 — **80 deaths**, 13 permanent loss of function, 5 extended care. Devices for a single patient can generate "as many as several hundred alarm signals per day." And the canonical number, in its primary home: "**An estimated 85% to 99% of alarm signals do not require clinical intervention.**"

ECRI ranked alarm hazards **#1 on its Top 10 Health Technology Hazards for four consecutive years, 2012–2015.**

**The primary observational study** — Drew BJ et al., *PLoS ONE* 2014;9(10):e110274. 77 ICU beds, 461 patients, 31 days, 48,173 monitoring hours:

- **2,558,760 unique alarms in 31 days**; 381,560 audible = **187 audible alarms per bed per day**
- 12,671 annotated arrhythmia alarms: **88.8% false positives**
- By type: ventricular bradycardia **96.7%** false · accelerated ventricular rhythm 94.8% · pause 87.7% · VT 86.8% · asystole 67.0% · VF 32.3%

**Two under-quoted findings that sharpen the critique:**
- Of 168 *true* VT alarms, only **12 (7.1%)** were sustained ≥30 seconds, i.e. met treatment criteria. **True is not the same as actionable.**
- **74.9% of annotated alarms had good signal quality.** The false alarms were not artefact — they were **the algorithm's threshold policy firing as designed.** This is a specification failure, not a maintenance failure.

**The actionability floor:** Bonafide CP et al., *JAMA Pediatrics* 2017: of **11,745 alarms, 50 (0.5%) were actionable.**

**But two honest nulls:**
- The same Bonafide study: "**the number of nonactionable alarms to which the nurse was exposed in the preceding 120 minutes was not associated with response time.**" Short-horizon desensitization was not demonstrated.
- Winters BD, Cvach MM et al., *Crit Care Med* 2018: across 62 articles, **no study used or developed a clear definition of "alarm fatigue"; no study measured it directly; there is no agreed valid metric.** The best-quantified case of signal-becoming-noise still has an unmeasured dependent variable.

**The cleanest dose-response evidence in the whole subject — alert override rates:**

| Signal | Volume | Override |
|---|---|---|
| Drug allergy alerts (Masud, *JAMIA Open* 2026) | 101,492 | **98.9%** |
| Geriatric alerts (Schepel 2025) | — | **97%** |
| Drug interaction alerts | — | 93–94% |
| Opioid analogue alerts, 2 systems (Wasserman, *BMJ Health Care Inform* 2025) | 700,493 | 71.8% |
| **PGx NSAID alerts — NSAID-naïve patients** (Massmann, *JAMIA Open* 2025) | — | **3.9%** |
| **PGx NSAID alerts — patients with prior NSAID use** | — | **60%** |

**That last pair is the mechanism isolated:** the same alert, the same clinicians, override rising from 3.9% to 60% purely as a function of how often the recipient has previously seen it be wrong for that patient. Precision degrades trust; trust degrades response. This is what every other critique in this section is gesturing at.

### 4.3 Automation complacency ✅

**Bainbridge L, "Ironies of automation," *Automatica* 1983;19(6):775-779.** The exact ironies:

1. **The designer's premise is self-refuting** — the operator is deemed unreliable and eliminated, whereupon designer errors become a major source of operating problems and the operator is left the residue of tasks that could not be automated.
2. **Manual skill decay** — "physical skills deteriorate when they are not used, particularly the refinements of gain and timing."
3. **Knowledge decay** — "efficient retrieval of knowledge from long-term memory depends on frequency of use."
4. **The monitoring irony** — "**the automatic control system has been put in because it can do the job better than the operator, but yet the operator is being asked to monitor that it is working effectively.**"
5. **Training irony** — "**it is the most successful automated systems, with rare need for manual intervention, which may need the greatest investment in human operator training.**"

The compound consequence, which is the load-bearing point for procedure design: **the operator is asked to take over precisely when the situation is abnormal — needing more skill and less load than average — at the exact moment their skill has decayed most.**

**Parasuraman & Manzey 2010, *Human Factors* 52(3):381-410 — the finding that most directly damns "just add a verification step,"** verbatim from the abstract:

> "Automation complacency occurs under conditions of **multiple-task load**, when manual tasks compete with the automated task for the operator's attention."
> "Both naive and expert participants experience it and **simple practice cannot overcome it.**"
> "Both naive and expert participants experience automation bias, **which cannot be prevented by training or instructions** and affects individual and team decision making."

It is an integrative review, so this is a synthesis rather than one experiment — but it is the field's own consensus statement, and it says explicitly that instruction-based countermeasures (which is what a verification checklist is) do not work.

**Mosier & Skitka** — three findings that matter:
- Definition: automation bias is "omission and commission errors resulting from the use of automated cues as a **heuristic replacement for vigilant information seeking and processing**."
- **Experimentally manipulated accountability did not significantly affect performance.** Only pilots reporting an *internalized* perception of accountability cross-checked more. You cannot install this by instruction.
- **Phantom memory:** "Pilots were also likely to erroneously '**remember**' the presence of expected cues when describing their decision-making processes." **The verification step was reported as performed and was not performed** — the cognitive twin of the 3.5%-vs-100% documented-compliance gap.
- Skitka et al. 2000: "Training that focused on automation bias and associated errors **successfully reduced commission, but not omission, errors**." And: "**Teams and solo performers were equally likely to fail to respond to system irregularities or events when automated devices failed to indicate them.**" *A second pair of eyes did not help.* This is the finding that most undercuts crew cross-check as a design remedy — and it should be read directly against Dismukes & Berman's 6% trapping rate for monitoring deviations.

**Aviation cases:**
- **Asiana 214** (NTSB/AAR-14/01): probable cause includes the pilot flying's **unintended deactivation of automatic airspeed control**, contributed to by "**the complexities of the autothrottle and autopilot flight director systems that were inadequately described in Boeing's documentation and Asiana's pilot training, which increased the likelihood of mode error.**" Asiana's automation policy emphasized full automation use and did not encourage manual flying on the line.
- **737 MAX / MCAS** — **the cleanest modern case of a procedure functioning as a paper mitigation for a hazard it could not control.** The mitigation Boeing relied on was **the existing runaway-stabilizer memory checklist**, with a safety analysis assuming pilots would react within about **three seconds**. KNKT found the standard checklist did not address MCAS's repeated re-activation; ET302's crew executed the procedure and still lost control because of manual trim forces and repeat activations.

### 4.4 Procedure as liability shield — strong argument, thin evidence ⚠️

Flagging clearly: this literature is theoretically strong and empirically thin. Treat it as a well-argued frame, not a measured finding.

**Dekker S, "Failure to adapt or adaptations that fail: contrasting models on procedures and safety," *Applied Ergonomics* 2003;34(3):233-238** — the single most useful citation here:

- **Model 1** — procedures are investments in safety; safety results from compliance; violations cause accidents; the remedy for trouble is more procedure and more enforcement. Application is **rote rule-following**.
- **Model 2** — procedures are **resources for action** that under-specify real situations; applying them requires **substantive cognitive activity**; safety results from skilful judgement about when and how they apply; **blind application can itself be unsafe**.
- **The double bind** — the paper's real contribution: operators can **fail to adapt when adaptation was necessary**, *or* attempt **adaptations that fail**. Both are visible only in hindsight, and organizations punish the second while being blind to the first.

**Dekker S, "The bureaucratization of safety," *Safety Science* 2014;70:348-357.** Safety becomes **measurable bureaucratic accountability**. Enumerated secondary effects that run counter to the original goal: **declining marginal yield** of further initiatives; bureaucratic entrepreneurism; **inability to predict unexpected events** (standardization is tuned to known failure modes); structural secrecy and "**numbers games**"; occasional creation of new safety problems. ⚠️ *Asserted, not measured.*

⚠️ **An honest gap:** the claim that prosecutions of clinicians suppress reporting rests on **testimony, not counts.** The best current study (Dekeseredy et al., *PLOS Mental Health* 2024, post-RaDonda Vaught) documents *fear* of reporting and regulator predictions of decline. Across a 12-record search, **none supplied epidemiological data on reporting rates before and after a prosecution.**

⚠️ **Hale & Borys, "Working to rule, or working safely?" *Safety Science* 55 (2013), Parts 1 and 2** — the canonical review of the Model 1 / Model 2 framing. Citations confirmed; **text not retrieved. Verify before citing.**

### 4.5 Work-as-imagined vs work-as-done ✅

**Hollnagel's ETTO principle:** there is an unavoidable trade-off between efficiency and thoroughness. "**Demands for productivity tend to reduce thoroughness while demands for safety reduce efficiency.**" Crucially, the same trade-offs that occasionally produce failure produce routine success — which is why they cannot simply be eliminated.

**The ETTO rules — the verbal signatures of a trade-off in progress.** Two of them are specifically *procedural-system* pathologies:

> "**It's been checked earlier by someone else**" · "**It'll be checked again later by someone else**"

**A layered checklist regime manufactures both.** That is the precise mechanism by which adding checks can subtract vigilance — and it maps directly onto the DOE handbook's warning that concurrent verification "cannot achieve true independence."

Other rules worth having, as an audit list: "It looks fine" · "It is normally OK, there is no need to check" · "I've done this a million times before, so trust me" · "It's good enough for now" · "There's no time to do it now" · "It looks like a Y, so it probably is a Y" · "**If you don't say anything, I won't either**" · "I'm not the expert on this, so I'll let you decide."

**Shorrock's five varieties of human work** (Humanistic Systems, 2016) — the most usable taxonomy:
- **Work-as-imagined** — what people think others do, or could do
- **Work-as-prescribed** — "laws, regulations, rules, procedures, checklists, standards," assumed to be "the safe and the right way to work"
- **Work-as-disclosed** — what people say or write about work, "tailored to the purpose or objective of the message"
- **Work-as-analysed** — work as reconstructed by investigators
- **Work-as-done** — "patterns of activity to achieve a particular purpose in a particular context"

On procedures: "**it is usually impossible to prescribe all aspects of human work… Procedures, standards, regulations, etc., lack the detail and richness of actual work.**" His evidence is **work-to-rule**: when workers follow the prescription exactly, the system stops. A natural experiment that runs regularly and always gives the same result.

**Note that work-as-disclosed is precisely what the 3.5%-vs-100% audit gap measures. The taxonomy predicted the number.**

⚠️ **Safety-I vs Safety-II** — core claim: **performance variability (adaptation) is the source of both success and failure**, so suppressing variability suppresses the same mechanism that produces the successes. EUROCONTROL's hosted PDF 404s and SKYbrary 403s to automated fetch; **do not quote a specific "1 failure in N events" ratio from this report.** Safety-II has essentially no direct empirical validation in this search — treat it as a reframing device, not a finding.

### 4.6 Compliance vs expertise — the strongest material in the critique ✅

**Amalberti R, Vincent C, Auroy Y, de Saint Maurice G, "Violations and migrations in health care," *Qual Saf Health Care* 2006;15(Suppl 1):i66-i71.**

**Borderline tolerated conditions of use (BTCU)**, verbatim: "(1) they are **first seen as benefits and not as risks**; (2) they enhance performance of the system or provide advantage for the individual; (3) they are **tolerated by senior management and sometimes even required by it**; and (4) they are associated with a variety of informal safety measures."

**The migration model** — three phases: initial safe space of action → **BTCU formation** (management pressure increases workload while constraining resources, transmitting "a pressure to act more quickly and, ultimately, to violate basic procedures") → **normalization of deviance**, after which violations become "routine and so common as to be almost invisible to both workers and managers."

**Quantified claims:**
- Aviation: **intentional non-compliance accounted for 55% of all errors and violations, but only 3% of these affected the flight in any adverse way.**
- "**About half the checklists on airplanes were not correctly completed.**"
- Operating theatre observation: **67 violations of procedure over 59 operations.**

**The strongest single sentence in the whole compliance-critique literature:**

> "**Violations paradoxically may be markers of high levels of safety because they need constraints and defences to exist. They may even become more frequent than errors in ultrasafe systems.**"

Why enforcement alone fails: "Ineffective memos may be circulated reminding workers of the (old) rule, but **the impact of these is short lived since the new behavior has already become socially sanctioned.**"

**Amalberti et al., "Five system barriers to achieving ultrasafe health care," *Ann Intern Med* 2005;142(9):756-764 — and this is the argument anyone advocating aviation-grade proceduralization must answer.** The five barriers are the **prices** of ultra-safety: **limiting worker discretion, reducing autonomy, transitioning from a craftsmanship model to an "equivalent actor" model, arbitrating at system level rather than by individual leaders, and accepting simplification.** Catastrophic exposure ranges from ~**10⁻² per hour (cardiac surgery) to 10⁻⁶ per hour (commercial aviation)** — and moving down that scale is **not free. You pay in autonomy and in maximum achievable individual performance.**

**Rasmussen J, *Safety Science* 1997;27:183-213** — the upstream model: a socio-technical system operates in a space bounded by the **economic failure boundary**, the **unacceptable workload boundary**, and the **boundary of functionally acceptable performance**. The management gradient toward efficiency and the individual gradient toward least effort push the operating point toward the last of these. **Procedures nominally mark the boundary; drift moves the operating point regardless.**

**Klein GA, Calderwood R, Clinton-Cirocco A, "Rapid Decision Making on the Fire Ground" (1986).** **26 experienced fireground commanders, mean 23 years' experience, 156 decision points probed. In fewer than 12% of decision points was there any evidence of simultaneous comparison and relative evaluation of two or more options.** In the other ~88% they recognized the situation as typical and identified a course of action as appropriate for that prototype.

**Implication for procedure design, stated precisely: a procedure that requires an expert to enumerate and compare options is asking for a cognitive operation experts do not perform under time pressure.** Procedures that support **recognition and situation assessment** are compatible with expert cognition; procedures that impose **analytic comparison** are not. Symptom-based EOPs (§3.5) are a recognition-support architecture; event-based EOPs were a diagnose-then-select architecture.

**Hatano & Inagaki, "Two courses of expertise" (1986):** **routine expertise** = mastery of procedures "in such a way as to become highly efficient and accurate," flawless within the familiar envelope; **adaptive expertise** requires "conceptual understanding that allows the 'expert' to invent new solutions to problems **and even new procedures for solving problems**." The critique this licenses: **a compliance regime is a routine-expertise factory.** It optimizes for accurate execution inside the envelope and provides no selection pressure for the understanding that produces novel solutions outside it. *Mechanism argument, not a measured one — but it is the cleanest statement of why "more procedure" and "more capable in novel situations" are in tension.* Note that Rickover's "they must understand **why**" is a direct attempt to buy adaptive expertise inside a compliance culture.

### 4.7 Checklists and skill level — the popular claim is backwards ✅

The evidence runs **against** "checklists are training wheels for novices." Arriaga's 17 OR teams were **experienced**, and every one performed better with the aid (6% vs 23% missed steps). The correct variable is not expertise but **frequency**: in events that are common institutionally and rare individually, recognition-primed expertise has no prototype to recognize, and the artifact substitutes for the missing prototype.

❌ **No study measures clinical skill degradation attributable to checklist use specifically.** The deskilling argument is supported by mechanism (Bainbridge's decay; Parasuraman & Manzey's practice-proof complacency) rather than direct measurement.

### 4.8 "Medicine is not aviation" ✅

**The best concrete counterexample of a transplanted aviation method** — Morgan L, … Catchpole K, McCulloch P, New S, *BMJ Open* 2015;5:e006216. Aviation-style teamwork training in elective orthopaedic surgery, one-day course plus six weeks of coaching: **non-technical skills improved (NOTECHS II 71.6 → 75.4) and WHO checklist compliance improved — while operative glitches paradoxically increased.** The process measures moved; the thing they were proxies for moved the wrong way. **That is the compliance-culture failure mode in a single trial.**

The balanced-but-citable version: Kapur N, Parand A, Soukup T, Reader T, Sevdalis N, *JRSM Open* 2016;7(1) — healthcare "has much to learn from aviation in certain key domains," but "**the transfer of lessons from aviation to healthcare needs to be nuanced, with the specific characteristics and needs of healthcare borne in mind.**"

Amalberti's five-barriers paper supplies the structural version: **the aviation risk level is purchased with autonomy and bounded maximum individual performance**, which medicine has structural reasons not to surrender uniformly.

### 4.9 When procedures are the right answer ✅

**Cynefin** (Snowden & Boone, *HBR* 2007):

| Domain | Decision model | Practice |
|---|---|---|
| **Clear/obvious** — cause and effect evident | Sense–categorise–respond | **Best practice** |
| **Complicated** — requires expertise; multiple right answers | Sense–analyse–respond | **Good practice** |
| **Complex** — causality visible only in retrospect | Probe–sense–respond | **Emergent practice** |
| **Chaotic** — no constraints | Act–sense–respond | **Novel practice** |

**Best practice — i.e. a fixed procedure — is the correct response in the Clear domain only.** In Complicated domains you get *good* practice, plural and expert-selected. In Complex domains reductionist approaches fail because "your very actions change the situation in unpredictable ways" — a fixed procedure is not merely useless there but actively misleading. **The most common organizational error is applying obvious-domain methods to complex-domain problems**, typically because a past success made the problem look categorizable.

**Perrow, *Normal Accidents* (1984)** — the sharpest available statement of *why the procedure question has no general answer*:

- **Tight coupling demands centralisation** — responses must be fast, prescribed, uniform; no time to consult.
- **Complex interaction demands decentralisation** — only the person at the anomaly can interpret an unanticipated interaction.
- **Systems that are both cannot satisfy both requirements simultaneously.** That irreducible contradiction *is* the normal-accident thesis. Nuclear plants, chemical plants and aircraft sit in this quadrant.

**HRO theory — and note that it is not a proceduralist position.** Weick & Sutcliffe's five principles of mindful organising:

1. **Preoccupation with failure** — anomalies are symptoms, not noise.
2. **Reluctance to simplify interpretations** — "Labels and clichés can stop one from looking further into the events." *This is a direct constraint on categorisation, and therefore on checklist logic, which is categorisation made mandatory.*
3. **Sensitivity to operations** — attend to work-as-done.
4. **Commitment to resilience.**
5. **Deference to expertise** — "**During a crisis, decisions are made at the front line**," and authority migrates to the people with the most expertise, **regardless of rank**.

**Principles 2 and 5 are anti-proceduralist by construction. Anyone citing HRO in support of rigid compliance is citing it against itself.**

---

## 5. SYNTHESIS

### 5.1 The mechanism table

| Practice | What fires AT the moment of action | Class | Documented failure mode |
|---|---|---|---|
| **Challenge-response checklist** | Printed card + mandated two-voice exchange, after a memorized flow; **configuration redundancy** | **Artifact + verbal exchange** | Response from expectation not observation; Delta 1141's <1 s challenge-to-response |
| **Read-do / do-list checklist** | Printed conditional steps, both parties agreeing pre-conditions | **Artifact, sequenced** | No configuration redundancy — "a mistake can easily pass unnoticed once the sequence is interrupted" |
| **Memory items** | Nothing external. Recognition → recall → motor sequence | **Internal, deliberately** | Misdiagnosis fires the wrong sequence fast (Airbus loss-of-braking); recall degrades exactly when needed |
| **Placekeeping (circle→slash)** | A pen mark that externalizes "where am I" | **Artifact** | Batch-signing, ditto marks, vertical lines — converts the artifact into fiction |
| **Flagging** | A physical marker on the component itself | **Artifact** | Post-it notes that dislodge |
| **Three-part communication** | A second person who will not act until the loop closes + a fixed script ("That is correct") | **Verbal exchange** | Shared wrong mental model — readback perfectly correct and perfectly wrong |
| **Standard callouts** | Parameter crossing → required word → required response; **silence becomes detectable** | **Verbal exchange** | Omitted call; call made while looking elsewhere; automation chime substituting for the call |
| **Peer check / concurrent verification** | Second person co-located with duty to **stop** the performer | **Second person, veto** | Correlated with performer; "true independence cannot be achieved" |
| **Independent verification** | Component's **as-found state**, read by someone who could not see or hear the performer | **Artifact read cold** | Common-mode error; too late where consequences are immediate |
| **Designated reader (crisis manual)** | Someone else's voice reading the steps to the person acting | **Verbal exchange** | Unresolved: leader-as-reader (accountability) vs separate reader (task saturation) |
| **Authority inversion (Keystone; two-challenge)** | A parameter or a step number that a junior can name **without accusing anyone** | **Verbal exchange + counter** | Requires the first challenge to happen at all; 12.1% FO trapping rate |
| **Sterile cockpit / no-interruption zone** | Altimeter passing 10,000 ft; wheels moving | **External gate, internal guard** | Nothing observes the conversation; violation detectable only by CVR; vest RCT null |
| **Pre-job brief (SAFER)** | Fires **before**; installs the expectations Review later tests against | **Preparatory** | "Cookbook" delivery; without it, Review degrades to "looks fine" |
| **Take deliberate action** | Pause + vocalization + gesture, explicitly severed from observation | **Self-imposed motor act** | Requires suspending punishment to become adoptable |
| **"Aviate, navigate, communicate"** | Nothing. A remembered priority ordering | **Internal** | Eastern 401: all four occupants on the same task; the C-chord fired and no one spoke |
| **Alerts / annunciators** | An aural or visual annunciation | **Symbolic, no mandated response** | Eastern 401's inhibited light; TMI's PORV signal-not-state indicator; 85–99% of clinical alarms non-actionable |

### 5.2 What the evidence actually supports

**1. The artifact is necessary, cheap, and not where the effect lives — for routine work.** Every setting that produced an effect changed *who says what to whom at a fixed moment*: Haynes (introductions + briefings + a formal pause; oral site confirmation 54%→92%), Pronovost (a nurse may stop a doctor), Neily (mandatory briefings/debriefings + a year of coaching, 0.5 fewer deaths per 1,000 per quarter), South Carolina (voluntary, coached, adapted, 22% DiD). Every setting that shipped only the artifact produced null: Ontario (unmodified checklist, materials only, adjusted OR 0.91) and Michigan Keystone Surgery (OR 0.88, CI crosses 1).

**2. The exception is rare events, where the artifact alone works.** Arriaga: same teams, same rooms, randomized within-team, **6% vs 23% missed critical steps**. McEvoy: **93.8% vs 0%** completing all critical steps with a designated reader. For *routine* work the checklist's value is the conversation it forces; for *rare* work its value is the memory it replaces. **These are different mechanisms and the design rules differ** — read-do for emergencies, do-confirm/challenge-response for routine verification.

**3. Compliance measurement measures disclosure, not work.** 100% documented vs 3.5% observed (Brown 2021); 89% EMR vs 47% video (Møller 2025); 98–100% Ontario self-report against a null outcome. Leape: "**In the absence of direct monitoring by observation, true compliance is unknown.**"

**4. The two tools with no external enforcement surface had to be converted into observable motor acts.** Self-checking became POINT/READ/READ, explicitly so that "peers and supervisors [have] an opportunity to coach the quality of the self-checking." Questioning attitude became a **danger-word trigger list** ("I assume," "probably," "should be," "we've always…"). Japanese rail arrived at the same answer independently and measured ~85%.

**5. Assertiveness works when it stops being a virtue and becomes a counter.** The two-challenge rule supplies a deviation parameter, a required callout, a required response, a count, and a scripted takeover. The junior no longer decides whether the senior is wrong enough to challenge — **the parameter decides and the count decides**, and it collapses "is he ignoring me or incapacitated?" into a rule where both produce the same safe action. Pronovost's central-line list does the same thing in a different register: a nurse cannot easily say "you're doing this wrong" but can say "**step 3 isn't done**."

**6. Procedure architecture beats procedure enforcement.** The single most consequential post-accident change in this entire record is the conversion from **event-based to symptom-based EOPs** after TMI: it removed the *correct-diagnosis precondition* from the critical path. Compare Klein — experts under time pressure recognize, they do not compare. Symptom-based procedures support recognition; event-based procedures demanded diagnosis first, and TMI proved diagnosis is impossible when the instruments lie.

**7. Compliance is a multiplier on procedure quality, not a substitute for it.** At TMI the operators executed their training and destroyed the core; the training "conformed to the NRC standard" and the operators scored above the national average. At Chernobyl half the alleged "violations" turned out not to be violations, and the parameter that mattered most was never presented to operators as a safety limit. **Both accidents were caused in part by defenses that existed on paper and were hollow in fact.**

**8. Ultra-safety has a price and it is paid in autonomy.** Amalberti's five barriers name it explicitly: 10⁻² to 10⁻⁶ per hour is bought with limited discretion, reduced autonomy, an "equivalent actor" model, and accepted simplification. Wan & Bolton formalize the same trade: **restriction and resilience are inversely related; select the minimally constraining intervention that prevents the specific error.** And Naval Reactors, the exemplar everyone cites, does not actually rely on compliance to survive a transient — its reactors "**can respond to operational transients without the need for immediate operator action.**"

### 5.3 Claims that did NOT survive verification

Reporting these because knowing where a claim is weak is part of the finding.

1. ❌ **"Too much airplane for one man to fly"** is unattributed period journalism, not in the 1935 Board finding. The rejoinder about "too complex for any one man's memory" has **no primary source at all** and is a modern paraphrase. The Board's actual finding was stronger: the design made the error undetectable.
2. ❌ **Gawande's "5–9 items" and "under 60 seconds"** are not in the primary design document, which says "**fewer than 10 items per pause point**" and "a reasonably brief period of time."
3. ❌ **Numeric readback ("one-five" not "fifteen") is verified ABSENT** from DOE-HDBK-1028-2009 (both volumes, 312 pages) and from ML102120052. DOE's own example says "eighteen."
4. ❌ **"Workers make about 5 errors per hour"** is verified absent from the DOE handbook. Do not attribute it there.
5. ❌ **"Checklists slow critical response"** — no supporting study found. A 2026 intraoperative-cardiac-arrest crisis-checklist study found the **opposite** (epinephrine delivered 51 seconds faster: 143.5 s vs 194.5 s). Drop this claim unless a specific source appears; the evidence runs the other way.
6. ⚠️ **"Checklist fatigue" as additive load** — two studies looked for it and did not find it. The demonstrated failure mode is **ritualization**, not overload.
7. ⚠️ **Acute alarm desensitization** — Bonafide 2017 is a clean null on the 120-minute window. The 0.5%-actionable figure stands; the immediate-fatigue mechanism does not. And per Winters/Cvach 2018, across 62 studies **no one has defined or directly measured "alarm fatigue."**
8. ⚠️ **Post-prosecution reporting declines** — testimony and regulator prediction only; no reporting-rate counts located.
9. ⚠️ **Scotland's "37%"** is a loose restatement of a **36.6%** point estimate with a very wide CI (−55.2 to −17.9), from a 15-year ecological interrupted time series in which the checklist was one component of a national programme.
10. ⚠️ **Safety-II** has essentially no direct empirical validation in this search. Treat as a reframing device.
11. ⚠️ **projectcheck.org's root domain is compromised** and serves casino spam; the Checklist-for-Checklists PDF still resolves and is authentic, but prefer an Ariadne Labs mirror.
12. ❌ **Not covered, agents did not finish:** verbatim hedged CVR phrasing for Air Florida 90, Avianca 052, Tenerife, United 173; PACE and the trans-cockpit authority gradient; Salas et al. CRM meta-analysis numbers; the 2017 Fitzgerald/McCain NTSB reports, Greeneville, San Francisco, and Davis-Besse 2002; Hale & Borys full text; INPO 06-002/09-004 (member-restricted, no working mirror).

---

**One line, if you keep only one.** A procedure is a *symbolic barrier* — in Hollnagel's terms, it "cannot itself provide the barrier function but requires an action by someone." Every durable practice in aviation, medicine, and nuclear operations is an attempt to give that symbolic barrier a physical enforcement surface: a mark on paper, a word that must be spoken back, or a second person who will not let the hand move. The ones that never acquired a surface — memory items, "aviate navigate communicate," sterile-cockpit *enforcement*, the questioning attitude — are exactly where the bodies are.
