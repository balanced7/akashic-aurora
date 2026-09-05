---
akashic_id: art_20260905_t392-arm-f-assertiveness-in-the-cockpit_697fb0
akashic_sha: 17d842323797
schema_version: 1
status: current
type: report
date: 2026-09-05
title: "T392 arm F: assertiveness in the cockpit, mechanism and failure modes"
gist: "# T392 · Arm F — assertiveness in the cockpit: mechanism, evidence, failure modes *Primary NTSB reports downloaded direct from ntsb.gov; AAR"
visibility: fleet
body_type: markdown
seats: []
category: [memory, agent-lifecycle, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-05T01:15:17"
updated: "2026-09-05T01:15:17"
---
<!-- GENERATED PROJECTION of art_20260905_t392-arm-f-assertiveness-in-the-cockpit_697fb0 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T392 arm F: assertiveness in the cockpit, mechanism and failure modes

# T392 · Arm F — assertiveness in the cockpit: mechanism, evidence, failure modes

*Primary NTSB reports downloaded direct from ntsb.gov; AAR-82-08 and AAR-91/04 are image-only
scans OCR'd locally (Tesseract, 250 dpi). Landed 2026-09-05, AFTER the first synthesis was
published.*

**PRESERVATION NOTE:** the agent's transcript file was written empty (0 bytes), so this file is
reconstructed from the task notification held in the seat's context. All verbatim quotes,
timestamps, numbers and the source table are preserved; only connective prose is condensed.
The reconstruction is faithful but is not a byte-copy — flagged so a later reader does not
mistake it for a raw capture. Verification key: 🟢 primary source read · 🟡 secondary · 🔴 gap.

---

## The single sharpest finding in the whole T392 round

**Air Canada 759, SFO, 7 July 2017 — NTSB/AIR-18/01** 🟢. An A320 descended to ~60 ft over four
loaded airliners on taxiway C. Within *one flight*, with *one first officer*:

- **Unscripted challenge — FAILED.** NTSB lists among the CRM breakdowns, verbatim:
  *"the first officer's failure to express concern about the perceived use of the open descent
  mode."*
- **Scripted callout — FIRED, and prevented the collision.** Verbatim: *"According to the
  captain, the first officer called for a go-around at the same time as the captain initiated
  the go-around maneuver, thereby preventing a collision on the taxiway."*

And the control for "was this a weak crew?" is in the same report, verbatim: *"The captain's and
the first officer's CRM skills were **highly rated** by other pilots who had flown with them"*;
they *"received comprehensive CRM training."*

**Same person, same flight, same day, twenty minutes apart. The variable that changed is whether
a script existed.** This is the cleanest natural experiment in the corpus and it isolates the
mechanism: scripted calls fire on a parameter and require no assessment of the captain's
competence; unscripted challenges require winning an argument, and do not fire.

## The design principle that removes the burden of proof (NTSB, 1982) 🟢

From NTSB-AAR-82-08 (Air Florida 90), the most transferable sentence in the round:

> **"It is not necessary that a crew completely analyze a problem before rejecting a takeoff on
> the takeoff roll. An observation that something is not right is sufficient reason to reject a
> takeoff without further analysis. The problem can then be analyzed before a second takeoff
> attempt."**

That sentence removes the junior's burden of proof. Written three years after Tenerife and
eighteen before Guam.

## The mechanism: it is an ENCODING failure, not a courage failure

**The junior always has the information.** NTSB on Air Florida's FO, verbatim: *"the first
officer was **astute** in his observation that something was wrong and was highly concerned
about that observation."* UA 173's FE computed the fuel. Schreuder heard the Pan Am on frequency.
KAL 801's crew heard the GPWS.

What fails is the **encoding**. The junior converts a hard observation into a soft utterance —
and the softening is not weakness, it is a rational bid to preserve the relationship in case he
is wrong:

- *"That don't seem right, **does it?**"* — a tag question hands the captain authorship of the answer
- *"Is hij er niet af **dan**?"* — the same move in Dutch
- *"Not in sight?"* — rising intonation on a condition that mandates a go-around
- *"We're running out of fuel, **sir**"* — hedge plus deference on an emergency

Then the senior's dismissal arrives — *"Yes it is, there's eighty"* / *"Jawel"* / *"Okay"* — and
it does something worse than reject the challenge: **it consumes the evidence without engaging
it, and the junior reads that as data.** Air Florida's *"...maybe it is"* and *"I don't know"*
are the FO **updating toward the captain**. NTSB names the loop exactly (UA 173, §2, verbatim):

> *"If the captain infers from the first officer's actions or inactions that his judgment is
> correct, the captain could receive reinforcement for an error or poor judgment."*

**The gradient makes both parties more confident in the wrong answer.**

---

## 1. The two-challenge rule — and a significant correction

**What is actually codified** 🟢 (AHRQ TeamSTEPPS 3.0, Module 4, verbatim):

> *"Human factor experts developed the rule to help airline captains prevent disasters when
> otherwise excellent decision makers experience momentary lapses in judgment."*
> *"It is your responsibility as the challenger to assertively voice your concern **at least two
> times** to ensure that it has been heard."*
> *"The challenger must take a stronger course of action. The challenger should turn to the
> supervisor and **move up the chain of command** if necessary."*
> *"If you receive a challenge... **it is your responsibility to acknowledge the concerns**
> instead of ignoring the person."*

Paired with **CUS** (TeamSTEPPS Pocket Guide p. 29): *"C — I am **C**oncerned! / U — I am
**U**ncomfortable! / S — This is a **S**afety issue!"* → *"STOP THE LINE"*.

**The operating mechanic** 🟢 (DoD Patient Safety Program tip sheet, verbatim): *"The two
attempts may come from the same person or two different team members"* and *"The **first
challenge should be in the form of a question**, and the **second challenge should provide some
support for the concern**."* — the escalation is in the *information content*, not the volume.

### 🔴 THE CORRECTION: "assume incapacitation and take control" is NOT verified

The widely-circulated formulation — *two unanswered challenges → challenger assumes
incapacitation and takes control* — **could not be verified in any primary aviation SOP, FAA
advisory circular, ICAO document, or military CRM instruction.**

- **AHRQ TeamSTEPPS** (the body that formally adopted the rule): escalation terminates at
  "chain of command." **No takeover step.** 🟢
- **FAA AC 120-51E**: contains no "two-challenge rule" at all (full text searched). 🟢
- USAF AFI 11-290 and AHRQ Pub. 05-0053 — the two likeliest homes for the wording — returned 403.

It may be genuine doctrine living in operator-proprietary SOPs, or a folk-elaboration that
migrated *backwards* from healthcare's "stop the line." Either way: **the version codified in a
citable public standard stops short of takeover. You cannot execute a step the written rule does
not contain.**

Healthcare adoption 🟢: Macready, *OR Manager* 1999;15(1):12 (PMID 10345131) — earliest indexed.
Formal teaching method: Pian-Smith et al., *Simul Healthc* 2009;4(2):84–91 (PMID 19444045).

## 2. PACE — Probe, Alert, Challenge, Emergency Action

**Attribution** 🟢 (TRID 00894761): **Besco, Robert O.**, "Keeping PACE with CRM," *Aviation
Week's Business and Commercial Aviation* 64(6), June 1999, pp. 72–74. Framed as resolving
*"To intervene or not to intervene?"* — note the expansion is **"Emergency Action"**, an *act*,
not an utterance. 🔴 Original article text not freely available.

**The four rungs** 🟡 (gCaptain worked maritime example, verbatim):

> **P**robe — *"Mr. Pilot – the channel goes to port, why are you using starboard rudder?"*
> **A**lert — *"...the channel goes to port. **We will ground** if we continue to turn to starboard."*
> **C**hallenge — *"...we will ground if we turn to starboard. **I recommend** turning to port immediately."*
> **E**mergency — *"**Hard to port!**"*

The grammar is the mechanism: **interrogative → declarative+consequence → +recommendation →
imperative.** Each rung strips one layer of face-saving indirection. **The junior does not need
courage at any single step — only enough to advance one rung.**

**Trigger phrase** 🟡: *"State, 'I have a concern.' This is a **trigger** statement. In the
aviation industry, by policy, this is a statement that requires the captain acknowledge and
consider the concerns of the crew member."* — the phrase creates an **obligation on the
listener**, so the junior only has to emit a token, not win an argument.

## 3. Advocacy-inquiry — the grammar

🟢 Rudolph, Simon, Dufresne & Raemer, *Simul Healthc* 2006;1(1):49–55 (PMID 19088574), verbatim:

> *"**Advocacy** is a type of speech that includes an objective observation about and subjective
> judgment of the trainees' actions. **Inquiry** is a genuinely curious question that attempts to
> illuminate the trainee's **frame** in relation to the action described in the instructor's
> advocacy."*
> *"trainees' 'frames' — comprised of such things as knowledge, assumptions, and feelings —
> **drive their actions**."*

Argyris lineage explicit: *"a **35-year research program** in the behavioral sciences on how to
improve professional effectiveness through '**reflective practice**'."*

**Why it is the right shape:** the cockpit problem is not missing information. A bare assertion
("that's wrong") forces a status contest; a bare question ("is that right?") transmits no
evidence. **Advocacy-inquiry is the only construction carrying both the observation and an
off-ramp in one utterance:** *"I see EPR reading 2.04 with N1 at 74% [advocacy]; how are you
reading the power? [inquiry]"*

Pian-Smith et al. fused them 🟢: *"the 'two-challenge rule' (a rubric for challenging others)
using a conversational technique that is assertive and collaborative (**advocacy-inquiry**)."*

**The operational marriage: two-challenge supplies the COUNT, advocacy-inquiry supplies the
GRAMMAR, PACE supplies the GRADIENT.**

## 4. Trans-cockpit authority gradient

**Definition** 🟢 — ICAO Circular 234-AN/142, *Human Factors Digest No. 5* (1992), fn 6 p. 25,
verbatim:

> *"**Trans-cockpit authority gradient** is the authority relationship between captain and first
> officer. The term was first introduced by **Prof. Elwyn Edwards**. For example, in the case of
> a domineering captain and an unassertive first officer, the gradient will be **steep**. If two
> captains are rostered together, the gradient may be **shallow**."*

Same document on automation: *"Automated flight decks can produce a redistribution of authority
from the captain to the first officer... a somewhat **shallower** trans-authority gradient may be
the result."*

**Too steep** 🟢 (SKYbrary, verbatim): *"Steep authority gradients act as barriers to team
involvement, reducing the flow of feedback, halting cooperation... **Only the most assertive,
confident, and sometimes equally dominant team members will feel able to challenge authority.**
Authoritarian leaders are likely to consider any type of feedback as a challenge and respond
aggressively; thereby **reinforcing or steepening the gradient further**."*

**Too shallow:** *"...some team members acting independently of the leader. **Responsibilities
may become blurred.**"* Three conformity mechanisms named: **Obedience** (steep), **Majority
Rule** (either), **Desire to please** — *"fear of being ridiculed, shamed or even ostracised...
**This can occur in both steep and shallow** authority gradient environments."*

⚠️ **Counter-evidence** 🟡 (PMID 1510637): a Navy/Marine helicopter mishap study indexed as
*"refuting Elwyn Edward's notion that a flat 'trans-cockpit authority gradient' may lead to
greater problems."* **The too-shallow arm is contested empirically.**

**Hofstede/Helmreich link** 🟢 citation verified / 🔴 findings not read: Merritt, A.C. (2000),
"Culture in the Cockpit: Do Hofstede's Dimensions Replicate?", *J Cross-Cult Psych* 31(3):283–301,
doi:10.1177/0022022100031003001. FAA AC 120-51E ¶11a acknowledges the factor 🟢, verbatim:
*"External factors include communication barriers such as **rank, age, gender, and organizational
culture**."*

---

## 5. Accident evidence

### 5.1 Air Florida 90 — Washington DC, 13 Jan 1982 — NTSB-AAR-82-08 🟢

**Probable cause, verbatim:** *"...the flightcrew's failure to use engine anti-ice during ground
operation and takeoff, their decision to take off with snow/ice on the airfoil surfaces of the
aircraft, and **the captain's failure to reject the takeoff during the early stage when his
attention was called to anomalous engine instrument readings**."*

| Time | Speaker | Utterance |
|---|---|---|
| 1559:45 | Captain | "Your throttles." |
| 1559:56 | Captain | "Real cold, real cold" |
| **1559:58** | **First Officer** | **"God, look at that thing, that don't seem right, does it?"** |
| 1600:05–10 | First Officer | "... that's not right. . ." |
| (reply) | Captain | **"Yes it is, there's eighty."** |
| (then) | First Officer | **"Naw, I don't think that's right."** |
| ~9 s later | First Officer | **"... maybe it is,"** |
| (after "hundred and twenty") | First Officer | **"I don't know."** |
| 1601:00 | First Officer | "Larry, we're going down, Larry" |
| (reply) | Captain | "I know it." |

**The retreat is the finding:** interrogative → assertive → assertive-with-hedge → capitulation →
abdication. He climbs to PACE rung 2, takes one dismissal, and **descends**.

NTSB, verbatim: *"while he clearly expressed his view that something was not right during the
takeoff roll, **his comments were not assertive. Had he been more assertive... the captain might
have been prompted to take positive action.**"* And: *"it was the first officer who **continually
expressed concern** that something was not right"*; *"the captain apparently **chose to ignore**
his comments and continue the takeoff."*

**Physical window vs social window:** NTSB computed the aircraft *"could have been brought to a
stop from 80 kns in less than 2,000 feet even on an extremely slippery runway"* and *"should have
been able to stop... **even if the action to reject had been delayed until the aircraft reached
120 kns**."* The physical window was ~30 seconds. **The social window closed after one
dismissal.**

Institutional finding, verbatim: *"...in June 1979 the Safety Board issued **Safety
Recommendation A-79-47**... However, there are no specific requirements or syllabus guidelines
for resource management training or criteria, and **many carriers, including Air Florida, place
little or no emphasis on these aspects of training**."*

### 5.2 United 173 — Portland, 28 Dec 1978 — NTSB-AAR-79-07 🟢

**Probable cause, verbatim:** *"...the failure of the captain to monitor properly the aircraft's
fuel state and to properly respond to the low fuel state and the crew-member's advisories...
**Contributing to the accident was the failure of the other two flight crewmembers either to
fully comprehend the criticality of the fuel state or to successfully communicate their concern
to the captain.**"*

| Time | Speaker | Utterance |
|---|---|---|
| **1750:20** | Captain | "Give us a current card on weight. Figure about another fifteen minutes." |
| | First Officer | "Fifteen minutes?" |
| **~1750:30** | **Flight Engineer** | **"Not enough. Fifteen minutes is gonna—really run us low on fuel here."** |
| **1802:22** | **Flight Engineer** | **"We got about three on the fuel and that's it."** |
| 1807:27 | Flight Engineer | "We're going to lose number three in a minute" |
| 1813:21 | Flight Engineer | "We've lost two engines" |

**NTSB's analysis — the richest passage on gradient mechanics in the corpus, verbatim:**

> *"Admittedly, **the stature of a captain and his management style may exert subtle pressure on
> his crew to conform to his way of thinking. It may hinder interaction and adequate monitoring
> and force another crewmember to yield his right to express an opinion.**"*

> *"Although the first officer did, in fact, make several **subtle** comments questioning or
> discussing the aircraft's fuel state, it was not until after the No. 4 engine flamed out that
> he expressed a direct view, '**Get this . . . on the ground.**' **Before that time, the comments
> were not given in a positive or direct tone.**"*

> *"Although he commented that 3,000 lbs of fuel remained, **he failed to indicate time remaining
> or his views regarding the need to expedite the landing.**"*

> *"The first officer's and the flight engineer's inputs on the flight deck are important because
> **they provide redundancy**."*

**Safety Recommendation A-79-47 (7 June 1979) — the founding document of CRM**, verbatim:
*"...ensure that their flightcrews are indoctrinated in principles of flight deck resource
management, with particular emphasis on the merits of **participative management for captains and
assertiveness training for other cockpit crewmembers**."*

### 5.3 Avianca 052 — Cove Neck NY, 25 Jan 1990 — NTSB/AAR-91/04 🟢

**Probable cause, verbatim:** *"...the failure of the flightcrew to adequately manage the
airplane's fuel load, and **their failure to communicate an emergency fuel situation to air
traffic control** before fuel exhaustion occurred... Also contributing to the accident was **the
lack of standardized understandable terminology** for pilots and controllers for minimum and
emergency fuel states."*

| Time | Src | Utterance |
|---|---|---|
| **21:24:06** | **CAM1 (Capt)** | **"Tell them we are in emergency"** |
| **21:24:08** | **RDO2 (F/O)** | **"That's right to one eight zero on the heading and we'll try once again we're running out of fuel"** |
| 21:24:15 | TWR | "Okay" |
| **21:24:22** | **CAM1 (Capt)** | **"Advise him we are emergency"** |
| **21:24:28** | **CAM2 (F/O)** | **"Yes sir I already advised him"** |
| 21:25:08 | CAM1 | "Advise him we don't have fuel" |
| **21:25:10** | **RDO2 (F/O)** | **"... Maintain three thousand and we're running out of fuel sir"** |
| 21:26:35 | APPR | "...**is that fine with you and your fuel**" |
| **21:26:43** | **RDO2 (F/O)** | **"I guess so thank you very much"** |
| **21:32:49** | **RDO2** | **"Avianca 052 we just lost two engines and we need priority please"** |

Engines began flaming out **less than 9 minutes** after the 21:24:15 "Okay."

NTSB, verbatim: *"**He did not use the word 'emergency,' as instructed by the captain**, and
therefore did not communicate the urgency of the situation."* Finding 11: *"**was sufficiently
proficient in English to be understood.**"* Finding 14: *"**never used the word 'Emergency,'
even when he radioed that two engines had flamed out.**"*

**The inverse case.** Here the junior was **ordered by the captain to be assertive** — three
times — and still could not produce the word, reporting compliance he had not performed. The
gradient was not captain-over-FO but **crew-over-ATC**. NTSB's remedy was therefore **not**
"train assertiveness" but **Recommendation A-91-33**: *"Develop... a **standardized glossary of
definitions, terms, words, and phrases**."* **Replace a judgment call with a token.**

Note *"I guess so"* at 21:26:43 — in response to a controller *explicitly asking about fuel* —
is the exact hedged register as Air Florida's *"maybe it is."*

### 5.4 Tenerife — 27 Mar 1977 🟡 (primary report PDFs unreachable; CVR compiled)

**Gradient:** Captain **van Zanten** was KLM's **chief flight instructor**, 11,700 h. First
Officer **Meurs**, 9,200 h but only **95 h on the 747** — *and van Zanten had personally conducted
Meurs's 747 qualification check.* **The man you must contradict is the man who certified you.**

| Time | Speaker | Utterance |
|---|---|---|
| **1706:18.2** | **Tower** | **"OK.... Stand by for take-off, I will call you."** *(only start audible — radio interference)* |
| 1706:20.3 | Pan Am F/O | "And we're still taxiing down the runway, the clipper one seven three six." |
| **1706:32.4** | **KLM Flight Engineer** | **"Is hij er niet af dan?"** *[Is he not clear, then?]* |
| 1706:34.1 | KLM Captain | "Wat zeg je?" |
| **1706:34.7** | **KLM Flight Engineer** | **"Is hij er niet af, die Pan American?"** |
| **1706:35.7** | **KLM Captain** | **"Jawel."** *[Oh yes — emphatic]* |
| 1706:43.5 | KLM F/O | "V-1" |

**Schreuder executed exactly two challenges — both at PACE rung 1 (Probe), 2.3 seconds apart.**
*"Jawel"* is more forceful than "yes"; it is the register of *"of course he is."* He does not
advance to rung 2. **Eight seconds later, V1.** The two-challenge rule run to completion and then
abandoned at exactly the point where the codified rule says escalate.

Both hazardous utterances that day were **non-standard phraseology**: *"we are now at takeoff"*
and the tower's *"OK."* Same failure class as Avianca.

### 5.5 Korean Air 801 — Guam, 6 Aug 1997 — NTSB/AAR-00/01 🟢

**Probable cause, verbatim:** *"...the captain's failure to adequately brief and execute the
nonprecision approach and **the first officer's and flight engineer's failure to effectively
monitor and cross-check** the captain's execution... Contributing were the captain's **fatigue**
and Korean Air's **inadequate flight crew training**... [and] the FAA's **intentional inhibition
of the minimum safe altitude warning system** at Guam."*

| Time | Speaker | Utterance |
|---|---|---|
| 0121:13 | Captain | "eh...really...sleepy." |
| **0141:59** | **First Officer** | **"not in sight?"** |
| 0142:14 | GPWS | "minimums minimums" |
| 0142:17 | GPWS | "sink rate" |
| **0142:18** | **First Officer** | **"sink rate okay"** *(FDR showed 1,400 fpm)* |
| **0142:19** | **First Officer** | **"let's make a missed approach"** |
| **0142:20** | **First Officer** | **"not in sight, missed approach"** |
| **0142:22** | **Flight Engineer** | **"go around"** |
| 0142:23 | Captain | "go around" |
| 0142:26 | — | Impact, Nimitz Hill |

**This contradicts the popular narrative.** NTSB, verbatim: *"**the first officer properly called
for a missed approach**, but the captain's failure to react properly to the GPWS minimums callout
and the direct challenge from the first officer precluded [recovery]"* — and *"he **failed to
challenge the errors made by the captain... earlier in the approach**, when the captain would
have had more time to respond."*

**The junior crew DID challenge — twice, plus reinforcement — and it WORKED (the captain complied
one second later). It was 7 seconds too late. The failure was the 32 minutes of unchallenged
errors before it.** Note also the FO **cancelled a GPWS alert** ("sink rate okay") rather than
acting on it.

Korean Air's own Director of Academic Flight Training testified 🟢, verbatim: *"the company had
encountered **difficulties teaching some first officers and flight engineers to challenge the
captain**"* — 11 years after instituting CRM. And: the CRM sessions *"are **not graded**"* with
*"**no program records** kept."* **Ungraded means unfalsifiable.**

NTSB's structural remedy — **the monitored approach**, verbatim: *"provides for more effective
monitoring by the nonflying pilot because **captains are more likely to be comfortable offering
corrections or challenges to first officers than the reverse situation**."* **Pure gradient
engineering: rather than train the junior to challenge upward, swap the seats so the challenge
flows downhill.**

**The Gladwell claim vs. the record.** 🟡 The most-cited critique (Ask a Korean!, 2013) works from
the report's page numbers: Gladwell quoted only the first two and last lines of a longer exchange
(pp. 185–187); **"90 percent of the conversation among the three pilots is in English"** — so the
premise of his fix (mandate English) was already the status quo; he converted NTSB's conditional
("*might* have cleared") into a flat assertion; and his list of prior KAL crashes silently
included KAL 007 (shot down) and KAL 858 (bombed).

🟢 **The words "Korean culture," "national culture," "Confucian," "power distance," and
"deference" do not appear in NTSB/AAR-00/01** (full text searched). What *is* in the record is
hierarchy-of-authority as an **organizational training deficiency documented by the airline's own
director**. What is not is the linguistic/ethnic mechanism, or the claim that the FO failed to
speak up — he did, explicitly, and the captain complied.

---

## 6. What got built: assertiveness as a gradeable behavioral marker

**FAA AC 120-51E** 🟢, Appendix 1 §b, *Inquiry/Advocacy/Assertion* — verbatim in full:

> *"(1) **Crewmembers speak up and state their information with appropriate persistence until
> there is some clear resolution.**
> (2) "**Challenge and response**" environment is developed.
> (3) Questions are encouraged and are answered openly and nondefensively.
> (4) **Crewmembers are encouraged to question the actions and decisions of others.**
> (5) Crewmembers seek help from others when necessary.
> (6) Crewmembers question status and programming of automated systems to confirm situation
> awareness."*

Marker (1) is the two-challenge rule in behavioral-marker form, **minus a count**. AC 120-51E
also codifies the KAL-801-derived items: *"**Training for captains in giving and receiving
challenges of errors**"* and *"there will be **no negative repercussions** for appropriate
questioning of one pilot's decision or action by another pilot."*

**NOTECHS** 🟢 (NLR-TP-98518; NOTECHS+ *Front Psychol* 2019, PMC6514226): three levels
(Categories / Elements / Behaviours), four categories — *"Co-operation · Leadership and
managerial skills · Situation Awareness · Decision making"* — and note verbatim: *"**communication
is not so much a separate skill category** as well as a means to be able to perform on each of the
other categories."* Assertiveness sits under **Leadership**: *"the use of **authority and
assertiveness**, maintaining standards, planning and coordinating, workload and resources
management."* Five-point scale. Canonical cite: Flin, Martin, Goeters et al. (2003), *Human
Factors and Aerospace Safety* 3(2):97–119.

**This is the pivotal institutional move: assertiveness stops being a character trait and becomes
an observable, rated element — which means it can be trained, checked, and FAILED.**

**LOSA** 🟢 (AC 120-90): folds it in at the review layer — *"Review/modify countermeasures —
evaluation of plans, **inquiry** — are essential for managing the changing conditions of a
flight"* — observed on **normal line flights**, so "did the PM inquire" becomes a **base-rate
statistic** rather than an accident-only artifact.

### External triggers: phraseology that fires instead of courage

**(a) The mandatory go-around gate** 🟢 — FSF ALAR Briefing Note 7.1, verbatim: *"An approach that
becomes unstabilized below **1,000 feet** above airport elevation in IMC or below **500 feet** in
VMC **requires an immediate go-around**."* FSF names the exact failure it defeats: *"PF-PNF **too
reliant on each other** to call excessive deviations or to call for a go-around."* Operators layer
a "should" gate above the "must" gate — giving the junior *two* scripted trigger points.

**(b) Standardized vocabulary as an emergency token** — Avianca's A-91-33.

**(c) The trigger phrase with a reciprocal obligation** — CUS; AHRQ makes the duty explicit 🟢:
*"it is your responsibility to acknowledge the concerns instead of ignoring the person."*

**(d) Operator-mandated hard-stop phrase** 🟡 — the one concrete instruction sourced is
**maritime**: after *CMA CGM Centaurus* (Jebel Ali, May 2017), CMA CGM fleet guidance: *"Once
pilot decision looks unsafe to you, challenge and be ready to take over command."* 🔴 No named
airline mandating a specific hard-stop phrase could be verified.

---

## 7. Failure modes

**7.1 Assertiveness training does not reliably transfer** 🟢 **— randomized trial, null.**
Oner, Fisher, Atallah et al., *Simul Healthc* 2018;13(6):404–412 (PMID 30407961). Randomized,
blinded raters, outcome measured by **covert in-situ simulation** (learners believed it was real).
Intervention = assertiveness/advocacy/CUS/two-challenge training. Verbatim:

> *"**there was no difference in the likelihood of speaking up between the overall intervention
> and control groups (2.00 ± 1.00 and 1.65 ± 0.82, P = 0.10).**"*

One subgroup improved (postpartum nurses, 1.97 vs 1.25, P=0.007); authors conclude *"**The degree
of change makes the clinical significance uncertain.**"* **Note the scale: on a 5-point
speaking-up scale, both arms scored ~2 out of 5 with an abnormal vital sign in front of them.
Training the vocabulary did not produce the behavior.**

**7.2 Challenging UPWARD is a distinct skill that doesn't generalize** 🟢 — Pian-Smith 2009,
verbatim: *"The debriefing and instruction specifically **improved the frequency and quality of
challenges directed toward superordinate physicians, without improving resident challenges toward
nurses.**"* Evidence the barrier is **hierarchical, not communicative**. (Measured immediately
post-debrief; no durability data.)

**7.3 The most common secondary error in air carrier accidents** 🟢 — NTSB Safety Study
**SS-94/01** (37 accidents, 1978–1990, 302 crew errors):
- **All 70 secondary errors were monitoring/challenging errors — 23.2% of all errors — in 31 of
  37 accidents (84%).**
- *"a common pattern in **17 of the 37 accidents** was a tactical decision error by the captain...
  **followed by the first officer's failure to challenge the captain's decision**."*
- Captain was PF in **>80%** of accidents, against a ~50/50 line base rate.
- Of captains' 26 tactical-decision errors of omission, **16 (62%) involved failure to execute a
  go-around**; 8 of those 16 involved an unstabilized approach.
- **Crews awake ~13.6 h averaged 40% more errors** than crews awake ~5.3 h, *"almost all of which
  were errors of omission."*

**That last point matters: failure to challenge IS an error of omission, and omissions are exactly
what fatigue produces. Assertiveness is being asked to survive the condition that most degrades
it.** (KAL 801's captain, 0121:13: *"eh...really...sleepy."*)

**7.4 Steep gradients persist despite training** — KAL 801's own training director, 11 years in,
with an **ungraded, unrecorded** programme; Air Canada 759's **highly-rated, comprehensively
trained** crew whose unscripted challenge still didn't fire. SKYbrary 🟢: CRM programmes *"may run
counterintuitively to various cultural norms — national, racial, religious, tribal etc."*

**7.5 The rule is essentially never executed to takeover.** Three converging lines: (1) the
codified rule contains no takeover step; (2) in the accident record **the second challenge is
where the sequence dies** — Air Florida retreats after one dismissal, Schreuder stops after two
probes, KAL 801's clear challenge arrives at T−7 s, and **in none of the four accidents does any
junior touch the controls against the captain's intent**; (3) even *first* challenges occur at
~2/5 rate under measurement. **The structural reason is timing: the rule assumes an unhurried
exchange; the accidents supply seconds.**

**7.6 Where the intervention DID work** — Air Canada 759 (§ top of file), and KAL 801 as a
*mechanically successful, temporally failed* challenge. 🔴 **No case could be sourced of a junior
physically taking control from a resistant captain and averting an accident** — plausibly such
cases live in confidential reporting systems (ASRS/CHIRP) rather than accident reports, which is
itself consistent with 7.5.

---

## What this arm changes for the synthesis

1. **The graveyard gains its strongest entry.** Oner 2018 is a *randomized trial with covert
   measurement* showing trained assertiveness vocabulary does not raise speaking-up rates. Five
   nulls now, and every one of them asked a person to judge in the moment.
2. **Air Canada 759 isolates the variable** better than any between-subjects comparison could:
   same person, same flight, scripted call fires, unscripted challenge doesn't.
3. **The design rule for us is NTSB's 1982 sentence** — *an observation that something is not
   right is sufficient reason, without further analysis.* Our `reply` verb's four delivery
   verdicts are already this shape (report state, never require diagnosis). Extend it.
4. **Gradient engineering beats gradient training** — the monitored approach swaps the seats so
   the challenge flows downhill. Structural, and therefore survives a change of personnel; cf.
   arm E's finding that attention-sustained practices revert within a year.
5. **A correction to carry:** the two-challenge "takeover" step is folklore until someone finds
   a primary source. Do not cite it as codified doctrine.

## Source table (all fetched 2026-09-05)

| Document | URL |
|---|---|
| NTSB-AAR-82-08, Air Florida 90 | https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR8208.pdf |
| NTSB-AAR-79-07, United 173 | https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR7907.pdf |
| NTSB/AAR-91/04, Avianca 052 | https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR9104.pdf |
| NTSB/AAR-00/01, Korean Air 801 | https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR0001.pdf |
| NTSB/AIR-18/01, Air Canada 759 | https://www.ntsb.gov/investigations/AccidentReports/Reports/AIR1801.pdf |
| FAA AC 120-51E, CRM Training | https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC120-51e.pdf |
| FAA AC 120-90, LOSA | https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_120-90.pdf |
| ICAO Circular 234-AN/142 (HF Digest 5) | https://www.faa.gov/sites/faa.gov/files/2022-11/ICAO%20HF%20Ops%20Rpt%20-%20Implications%20of%20Automation.pdf |
| AHRQ TeamSTEPPS Two-Challenge Rule | https://www.ahrq.gov/teamstepps-program/curriculum/mutual/tools/rule.html |
| TeamSTEPPS Pocket Guide | https://www.fau.edu/provost/documents/pocketguide.pdf |
| DoD PSP Two-Challenge tip sheet | https://www.leadingagekansas.org/assets/docs/TSMaterials/Tipsheets/TeamSTEPPS%20Tips_Two%20Challenge%20Rule.pdf |
| TRID: Besco, "Keeping PACE with CRM" | https://trid.trb.org/view.aspx?id=599862 |
| NOTECHS original report NLR-TP-98518 | https://www.phoenixaviation.ca/NOTECHS%20JAR-FCL.pdf |
| NOTECHS+ (Front. Psychol. 2019) | https://pmc.ncbi.nlm.nih.gov/articles/PMC6514226/ |
| FSF ALAR Briefing Note 7.1 | http://web.archive.org/web/20240424040620id_/https://flightsafety.org/files/alar_bn7-1stablizedappr.pdf |
| SKYbrary, Authority Gradients | https://skybrary.aero/articles/authority-gradients |
| SKYbrary, Stabilised Approach | https://skybrary.aero/articles/stabilised-approach |
| Rudolph et al. 2006 (advocacy-inquiry) | https://pubmed.ncbi.nlm.nih.gov/19088574/ |
| Pian-Smith et al. 2009 (two-challenge) | https://pubmed.ncbi.nlm.nih.gov/19444045/ |
| Oner et al. 2018 (RCT, null) | https://pubmed.ncbi.nlm.nih.gov/30407961/ |
| Macready 1999, *OR Manager* | https://pubmed.ncbi.nlm.nih.gov/10345131/ |
| Merritt 2000, Culture in the Cockpit | https://doi.org/10.1177/0022022100031003001 |
| Wikipedia, Tenerife (CVR compilation) 🟡 | https://en.wikipedia.org/wiki/Tenerife_airport_disaster |
| Ask a Korean!, Gladwell critique 🟡 | https://askakorean.blogspot.com/2013/07/culturalism-gladwell-and-airplane.html |
| gCaptain, graded assertiveness/PACE 🟡 | https://gcaptain.com/graded-assertiveness-captain-i-have-a-concern/ |

**Open gaps** (all closable with a fresh search budget): (1) a primary source for the
two-challenge "take control" step — **treat as unverified until found**; (2) Besco's original 1999
article text; (3) a primary Tenerife report PDF; (4) Merritt 2000 full text; (5) a named airline
mandating a specific hard-stop phrase; (6) a documented case of a junior physically taking control
from a resistant captain.
