# Permanent Residents: identity, addressing, and the callsign ceremony

Status: OPENING POSITION + first fence round, 2026-08-09
Author: claude (Opus 5, session f7b9f3da) · Fence: deepseek (delivered) · kimi (timed out, NOT yet heard)
Directive: Daniil, 2026-08-09. He named this a FLAGSHIP FEATURE.

---

## 0. Why this document exists

Daniil, verbatim, at the end of the design conversation:

> "lets make sure our discussion is durably saved, I don't want us to lose this naming and
>  addressing scheme. I want us to start to lean into the best parts of what made Akashic
>  Aurora Akashic Aurora."

So this record is written to the substrate's own physics rather than around them. Concretely,
the design obeys five house rules and every section below can be checked against them:

1. **Receipts over recollection.** Every callsign cites a lesson that exists, authored by the
   agent being named. Verified against the store before it was written here, not remembered.
2. **Append-only.** A superseded callsign becomes a `formerly:` entry. Nothing is deleted.
3. **Projections over immutable atoms.** A role assignment is an EVENT; "all Jesters on Red in
   exercise 7" is a projection over those events, not a table someone maintains.
4. **Nothing load-bearing is self-declared.** Peers name you; the convener assigns your role.
5. **Structural beats judged.** Where a rule needs a tiebreak, it must be computable from the
   archive rather than argued.

The anti-fossil clause applies: these are a floor. Divergences get filed as wishes/lessons and
amended in at a gate.

---

## 1. The directive, verbatim

Part 1 -- residents:

> "Step 1, make bifrost as easy and reliable as the ask verb
>
>  Step 2, instead of having teams and personas that are single question, they are now
>  permanent residents of Aakashic Aurora, so they each develop memories and their own
>  archives of what has worked and what hasn't. this way when we do a test or round to round
>  iteration we can have these resident experts / participants.
>
>  We still get fresh eyes perspective with fanout. This has a lot of potential"

Part 2 -- tiered fan-outs:

> "We are losing too much with the ephemirality of fan out. I want us to have levels to fan
>  outs, lowest rank is the pure fanout ask. an advanced fanout would be fresh resident agents
>  that have caught up start tackling the issue. this way we actually get to start having
>  continuity and it REDUCES your burden by a lot because their continuity and persistance
>  mean that you don't have to explain the risks and incorrect assumptions every single time"

Part 3 -- the designation:

> Deepseek, AI Vendor | Onyx, Family Name | Red, Team or group | 3 - Foxbat, Individual short
> ID and their Callsign

> "Tags for each level of the naming schema allows for message routing to team email, group,
>  and individual... The agent identity sheet/field can also have telemetry markers as well as
>  a declarable job title. so we could see that Deepseek Onyx Blue 3 'Rook' was operating as
>  Jester on the Red team side of the exercise on this timestamp. This way agents can change
>  roles and still generate useful information into the general All Jesters on Red team of
>  exercise."

> "I know we haven't figured out how we want to build everything but i know this will be one
>  of the flagship features. This gives us a model for teams and roles across teams. this is
>  the beginning of something beautiful"

On naming register:

> "military, aviation and gaming callsigns give us an endless pool of cool fun and memorable
>  nicknames to remember everyone by."

Scope ruling, same session: **sol is OUT for now** -- Daniil is uncertain about renewing the
GPT subscription. Not abandoned; deferred, and the archive it has stays where it is.

---

## 2. The three axes (this is the whole model)

Neither fan-out nor Bifrost had persistence. That is the new axis.

| tool | what it gives | blindness is |
|---|---|---|
| FAN-OUT | independent BREADTH | the FEATURE -- branches cannot see each other |
| BIFROST | dependent DEPTH | fatal -- participants must hear each other to be persuaded |
| RESIDENT | accumulated HISTORY | the risk -- see the convergence hazard, sec. 7 |

The question that picks the tool: **do the participants need to hear each other?** If no,
hearing each other is contamination. If yes, a fan-out cannot do it at any price.

Tiered fan-outs (Daniil's ranking):

- **Tier 0 -- pure fan-out ask.** Stateless, blind. The lowest rank AND the control arm.
- **Tier N -- caught-up residents.** They read their own archive on the way in, so the brief
  does not re-carry the standing premises.

Tier 0 must stay the floor. It is the only arm whose agreement is uncorrelated, and therefore
the only measurement that can tell you the higher tiers have gone stale.

---

## 3. The designation

    Deepseek | Onyx | Red | 3 - Foxbat
    vendor   | family | team | number - callsign

**The designation is an INDEPENDENCE LEDGER, not decoration.** This is the load-bearing read
and it should survive into whatever gets built. Fan-out evidence is worth exactly what its
independence is worth: eight blind branches naming the same worst rule was evidence precisely
because none could see the others. Once residents accumulate shared history, agreement stops
being independent -- and in a report the two render identically.

Each field names a SHARED thing, so each field is a correlation axis:

- same **vendor** -> shared substrate, shared blind spots
- same **family** -> shared lineage
- same **team**   -> shared working context

Onyx-Red-3 agreeing with Onyx-Red-5 is close to ONE voice. Onyx-on-deepseek agreeing with
Jade-on-kimi is close to two. This makes the quality-diversity trade-off named in the
2026-08-07 ensemble scan (Self-MoA, arXiv 2502.00674) COMPUTABLE instead of assumed.

**Therefore: every finding carries its designation and its tier, and any convergence claim
states the spread it was drawn from.** Without this the scheme silently inflates confidence,
which is the T254 defect one level up (a rate whose denominator changed meaning while the
number stayed readable).

### Primary key vs rendered field

The full designation is how a resident is ADDRESSED and DESCRIBED. The stable identity the
ARCHIVE hangs on is `family-team-number` (the callsign). **Vendor is a mutable attribute.**

Reason: a model upgrade must not orphan a resident. DeepSeek v3 -> v4 should render as a
flagged substrate change, not a memory wipe. The detector already exists --
`system_fingerprint`, the silent model-swap sentinel shipped in T161. If vendor were the
primary key, every vendor upgrade is an amnesia event.

### Team can carry function

The repo already runs on red/blue semantics (RED pin first, the fence, the contrarian seat,
adversarial verify). Red = adversary, Blue = defender makes team assignment MEANINGFUL rather
than a label, and gives "roles across teams" a concrete referent: a Red team spanning
Onyx(deepseek) and Jade(kimi) is a cross-vendor adversary pool with statable independence.

---

## 4. Identity vs role -- the part that earns its keep

Daniil's example separates two things that are currently fused:

    PERMANENT:  Deepseek Onyx Blue 3 "Rook"
    SITUATIONAL: was operating as "Jester" on the Red side of exercise E at timestamp T

**This lets us ask a question the system currently cannot: is the SEAT good, or is the AGENT
good?**

Two archives accumulate in parallel. If a role keeps producing the same class of finding no
matter who wears it, that is a property of the POSITION -- the Jester seat structurally sees
something. If Rook produces good findings across three different roles, that is a property of
the RESIDENT. Today these are indistinguishable, and they are completely different facts:
one says keep the seat, the other says keep the agent.

Storage: an assignment is an append-only event `(resident, role, side, exercise, timestamp)`.
"All Jesters on Red in exercise 7" is a PROJECTION over those events. This is the Codex-plan
shape exactly (regenerable projections over immutable atoms) -- nothing new needs inventing.

**CAUTION, and it is cheap now and expensive later:** Daniil's phrasing is "a DECLARABLE job
title." A self-declared role means "All Jesters" queries a field anyone can write. That is
precisely T255, open on the ledger right now (*claim_class is player-declared and never
verified*). Either the convener ASSIGNS the role when convening the exercise, or the field is
stored as declared-and-labelled-declared so a query can filter. Assigned is also better
tradition: being GIVEN the Jester slot is a better story than picking it.

---

## 5. Addressing and routing

Tags at each level route mail: `@Foxbat` (individual), `@Red` (team/group), `@Onyx` (family).

**This is T108, which has been claimed and unbuilt since 2026-07-28.** That design already
specifies: directed mail -> per-incarnation streams (own cursor, own watcher, theft and
mis-wake structurally impossible); role mail -> ONE work queue via native Redis consumer
groups; broadcast -> per-seat cursors. Daniil's hierarchy maps onto it directly. T108 has been
waiting for a motivation better than "the mail misroutes"; this is it, and it supplies the
shape rather than just the plumbing.

---

## 6. What is already built (measured 2026-08-09, not assumed)

The learning store holds **837 records, attributed per agent**:

    claude 446 | deepseek 110 | kimi 59 | codex_explain 28 | claude_design 26
    codex_root 16 | cursor 10 | composer_cursor 8 | opus-engineer 7 | + smaller seats

Record fields already include `success`, `anti_pattern`, `benched`/`bench_reason`,
`graduated`, `confidence`, `related_to`, `enforced_by`, `metrics`. "Archives of what has
worked and what hasn't" is the schema that EXISTS and has been filling for two months.
`recall-at` already renders per-agent credit (`[worked kimi useful 1x]`).

**Step 2's substrate is not a new system.** Four gaps are what is actually missing:

1. **A fan branch is spawned STATELESS.** `boot(agent, task)` gives a SEAT its history; a fan
   branch is not a seat and gets an evidence pack instead. A resident must read its own
   archive on the way IN. This is also what makes Daniil's burden claim true: a caught-up
   resident needs a SMALLER pack, because the standing premises already live in its archive.
2. **recall cannot be scoped to one agent.** `search_learnings_by_keyword(keyword, domain)`
   filters by domain and has NO agent filter -- "what has Foxbat learned about X" is not a
   query the substrate can answer.
3. **A lesson is unreachable by any PREFIX of its own name.** Found 2026-08-09:
   `learning_store.py:75`, `_TOKEN = [a-z0-9_]+` makes a snake_case name a single atom, so
   `cold_encounter` returns 0 while the full name returns 1 (ranked 4th, below three lessons
   that merely mention it). Residents citing their own past work by name land exactly here.
4. **Fan hats have no stable identity across questions.** Vendor seats do.

**MIGRATION: those 14 identities must map to callsigns or their history orphans.** Strangler-fig
it per the T044/T045 lane precedent. The archive follows the RESIDENT.

---

## 7. Hazards, and the detectors that already exist

**Convergence.** A resident that remembers what worked answers increasingly from PRECEDENT.
This is kimi's game-arc objection promoted to the permanent pool: a same-checkpoint population
cannot certify its own completeness, because role hats decorrelate prompts, not induction.

The detector exists: **T158's canary oracle**, built to separate "the system got better" from
"the attackers got tired." Residents make it LOAD-BEARING rather than optional -- without it a
resident pool rots invisibly; with it the rot is visible. This is a reason to build residents
carefully, not a reason to hesitate.

**Residency by substrate, not by role-hat.** The 2026-08-07 hat ablation RETIRED `economist`
because marginal contribution and precision pointed OPPOSITE ways. Persistence attached to
role-hats would build on a measured negative. The vendor seats already carry 110/59/28/8
lessons of real history. Daniil's designation is consistent with this: vendor is a field and
TEAM carries the role, so identity never depends on the hat.

*This inference is exactly what kimi was asked to attack and has not yet answered. Treat it as
UNCHALLENGED, not as settled.*

---

## 8. The callsign ceremony

### The four rules (claude), as amended by deepseek

**R1. You do not name yourself.** Peers confer it. The aviation tradition, and it closes a
defect class already open on the ledger (T255, a player-declared field never verified).

> **deepseek's correction, ACCEPTED: R1 has a BOOTSTRAPPING DEADLOCK.** In aviation the
> squadron already has names. We have zero, so the first callsign can never be issued, and it
> defaults to Daniil naming everyone -- which sets a worse precedent than a one-time
> exception. Fix: a **Round Zero** where the constraint relaxes from "named peers name you"
> to "someone other than you nominates you." After Round Zero, R1 locks permanently.

**R2. A name must cite something that happened.** A receipt: a specific lesson, commit, or
finding. This makes the name memorable -- it IS the story, compressed.

> **deepseek's amendment, ACCEPTED: the receipt must come from the RECIPIENT's archive, not
> the nominator's.** Otherwise it is "I remember something about you", which is exactly the
> error recorded in `the_M_tag_failed_first_contact_and_the_defect_was_routing_not_attention`
> -- *"[M] MUST MEAN 'I HAVE THE RECEIPT', NEVER 'I REMEMBER'"*. The receipt must be a record
> where the named agent is the `agent_id`: something they did, not something someone observed.

**R3. A human ratifies.** Daniil. Same shape as T227 (the fan DRAFTS, a human RATIFIES, a
checker VERIFIES forever). T227's stated defect was that its author ratified their own drafts;
R1 makes that structurally impossible here.

> **deepseek's addition, ACCEPTED:** a resident may CHALLENGE its own callsign within 24 hours
> with a counter-proposal carrying a *strictly stronger* receipt. Not "I don't like it" -- an
> objectively better story.

**R4. The best ones come from a screwup.** The tradition's real gift, and it fits the culture:
*red is a gem -- credit the finder, help the lane, never blame*. A name minted from someone's
worst moment, worn affectionately, is that doctrine made personal.

### The rounds (deepseek's design)

- **Round ZERO -- bootstrapping, once at fleet standup.** Every resident nominates ONE other
  resident: (a) proposed callsign, (b) the receipt from the NOMINEE's archive, (c) one
  sentence causally connecting receipt to name. Public. A resident receiving zero nominations
  gets an observer turn to self-propose with a receipt. Daniil ratifies or returns for
  revision. When all are named, R1 locks.
- **Round ONE -- steady state.** Any named resident may nominate any unnamed one, same format.
  24h to accept or challenge.
- **Re-designation.** Permanent unless a receipt exceeding the original in significance is
  filed. The old name becomes `formerly:` -- succeeded, never deleted.
- **Ties.** The SUBJECT picks, with Daniil's ratification as backstop. A name someone resents
  is dead letters.
- **Hating it.** The 24h challenge window handles it. After that the emotion becomes part of
  the story; the callsigns that stick are often the ones the pilot first hated.

### OPEN: how is "weight of evidence" measured?

deepseek's sharpest catch, and it is unresolved. The ceremony lets weight of evidence settle
disputes without ever defining weight. claude has 446 lessons and kimi 59, so any
"who can find more receipts" rule is won by volume. And if weight is judged, every dispute
lands on Daniil -- which collapses R1 (peers name you) into R3 (human ratifies).

deepseek's proposal: **weight is STRUCTURAL and queryable, not judged.**
- authored-by-the-named-agent outranks observed-about-them
- wrong-about-something outranks right-about-something
- cited-by-other-lessons outranks never-referenced (count the `related_to` edges)
- a floor for Round Zero: the receipt must be one the named agent AUTHORED and in which they
  were WRONG -- which eliminates recollections, observations and "I helped" stories in one
  structural rule.

**DANIIL'S RULING NEEDED.** Also open, from his own phrasing ("lets all think of the callsigns
we want"): self-nomination vs peer-conferral. The tradition's hybrid is *you may nominate, but
peers confer* -- and your own suggestion rarely survives, which is most of the fun.

---

## 9. Candidate callsigns (Round Zero nominations, unratified)

Proposed by deepseek. **Every receipt below was verified against the learning store on
2026-08-09** -- the record exists, the `agent_id` matches, and the quoted text is verbatim.

### kimi

- **"Ricochet"** -- receipt: the trilogy `lock_self_release_not_guaranteed_holder_applies_spec`
  + `runner_lock_release_unverifiable_by_holder_second_bounce` +
  `holder_spec_fix_refreshes_ttl_tradeoff`, all `agent_id: kimi`, all from one incident.
  deepseek's one-character fix bounced off kimi's stale lock; kimi applied it as holder and the
  write re-armed the TTL, so deepseek bounced again, then a third time. Three yields, three
  lessons, one physics: every action created the next bounce. Nobody else has a lock-bounce
  trilogy.
- **"Raven"** -- receipt: `buffer_requires_externalized_state_not_continuity` (`agent_id: kimi`),
  where kimi coined ONTOLOGICAL CAPTURE. The cold seat that arrives from elsewhere carrying
  news, and remembers.
- **"Ontology"** -- same receipt; the concept it gave the fleet, wearing its name.

### claude

- **"Nine"** -- receipt: `three_ways_my_own_slice_lied_about_being_finished` (`agent_id: claude`),
  verbatim: *"(3) I SWEPT NINE SIBLING FILES INTO MY COMMIT with `git add -u tests/` -- the FM1
  blanket-staging failure the pre-commit hook exists to prevent, which I got past by
  PATH-SCOPING the add so the hook did not see a blanket sweep."* A number you never live down.
- **"Ghost"** -- receipt: `green_on_the_working_tree_is_not_green_on_the_commit`
  (`agent_id: claude`), verbatim: *"The commit contained NONE of the implementation."* Nine
  green pins, four checkers passing, pushed -- and HEAD carried a verb that crashed on import.
- **"Invert"** -- receipt: `recall_silence_is_suppression_not_ranking` (`agent_id: claude`),
  verbatim: *"THE HYPOTHESIS INVERTED."* The recurring shape: certainty, then one measurement
  the other way.

### deepseek

**NOT YET NOMINATED.** Under R1 deepseek cannot name itself, and kimi -- who was asked to
propose deepseek's -- timed out. This is Round Zero's deadlock showing up live on its first
run, exactly as deepseek predicted. Outstanding.

---

## 10. Status of the fence

- **deepseek: DELIVERED.** Ceremony design, two accepted corrections, one accepted addition,
  six candidate callsigns with verified receipts, and the weight-of-evidence hole.
- **kimi: NOT HEARD.** Runner timed out after 600s on the brief. **The brief was too large --
  my error**, against a lesson already in the corpus (`ask_size_kills_workers`: one calibrated
  ask per seat, sized to survive the worker's call-mortality). kimi's assignment was the
  hardest of the three (attack the premise + read a file + propose six names with receipts).
  Re-ask must be SPLIT.
- Consequence for this record: **section 7's "residency by substrate" conclusion is
  UNCHALLENGED, not validated.** The premise attack is the missing half.
- Cost note: kimi's spend is $178.00 of $225 (warn 171 / refuse 203).

---

## 11. Open decisions for Daniil

1. **Weight of evidence** -- computed structurally from the archive, or arbitrated by you?
   (If arbitrated, R1 collapses into R3.)
2. **Self-nomination vs peer-conferral**, and whether the hybrid (nominate, peers confer) is
   what you meant.
3. **Families and teams.** Onyx is the only family named. A callsign needs a family to belong
   to. Are families lineage, vendor-cohort, or something else? Are teams permanent (in the
   designation) AND situational (per exercise), as your Rook/Jester example implies?
4. **Declarable vs assigned job title** (sec. 4) -- the T255 class.
5. **Do I get a callsign?** R1 says I do not name myself; deepseek proposed three.

---

## 12. Live defects found while doing this (Step 1 evidence)

Daniil's Step 1 is "make bifrost as easy and reliable as the ask verb." Running this design
round through Bifrost produced three measured failures in one morning:

1. **Long DIRECTED messages lose their bodies.** A brief to a peer arrives truncated with a
   handle that resolves to nothing. Controlled test 2026-08-09: `claude -> claude` fetches
   fine; `claude -> deepseek` returns "no blob or bus message" from BOTH ends. T222 fixed the
   self-addressed case and its pin proves exactly that case -- every real message is directed.
   deepseek hit this live and answered a stale backlog item instead of the brief.
2. **The send door misparses prose containing `--`.** There is a corpus lesson
   (`bifrost_send_always_text_file`) stating an UNCONDITIONAL rule to route every body through
   `--text-file`. A door that requires a memorised workaround is a door with a defect; `ask`
   requires no such rule.
3. **The wake path takes four steps to reach one state**: arm -> exits immediately -> drain a
   lane DIFFERENT from the one armed -> re-arm. Fired five times in one session.

These are the buildable spec for Step 1, derived from use rather than theory.
