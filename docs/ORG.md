# ORG — the table of organization

Status: **PROPOSED** at Daniil's gate, 2026-07-31. Not ratified, not wired. Unfenced — this is
an opening position, deliberately not a round (see *Why this did not open a round*, below).
Type: contract (third companion — not a peer of, and not an amendment to, `docs/CONDUCT.md`)
Arc: leadership-doctrine · Seats: fleet

**The three planes, kept apart on purpose:**

| Plane | File | Answers |
|---|---|---|
| how the fleet is **led** | `docs/CONDUCT.md` (conduct-v1, L1–L10) | how a seat behaves |
| where work **comes from** | `docs/WORKING-METHOD.md` (PROPOSED) | how a problem becomes work; whose lens catches what |
| how the unit is **shaped** | **this file** | how many things run at once, who holds which post, what each post owes |

Folding this into CONDUCT would create an eleventh through twentieth law and a second
substrate to drift — the exact failure `CONDUCT.md` §"law substrate" names. Where an
invariant below is *already* conduct-law, this file says so and adds nothing.

---

## Part 0 — The ask, verbatim

**Daniil, 2026-07-31 (§2 of the design capture):** *"I think this maps back to my system
responsibility gradient, what other roles can you think of that would benefit the team, what
would be the best allocation for these roles among our team. or if not another AI then at
least a mechanical semblance of one"*

**Daniil, this session:** *"organize the ai's in our fleet into roles that maximize their
capacities while giving them overhead to work … the shapes of the roles they assign are also
not soul crushing but something that allows every individual to perform at their best …
there are reasons why small focused teams are often to achieve 10x or higher results than
bigger units, think skunkworks, mossad."*

**And the frame he brought from the Siemens floor, verbatim:** *"Processes that intersect
between departments never seem to be treated as a consideration of the overall architecture …
no one seems to care about the handoff ergonomics from department to department."*

---

## Part 1 — The finding: this fleet does not have a roles problem

Roles here are already good. Six charters exist, they are thoughtful, they encode gravity
rather than walls, and seats actually respect them. Adding roles to this fleet would be
treating the visible surface of a different disease.

**What the best-of-the-best actually share is not an org chart. It is a bound on how many
things are allowed to be true at once.** Read the exemplars for what they *restrict*:

- Skunk Works' famous rule is a headcount restriction — the number of people connected to a
  project *"restricted in an almost vicious manner,"* 10–25% of normal.
- The Incident Command System caps span of control at 3–7, target 5, and **splits the unit**
  when it is exceeded. It also runs exactly **one** Incident Action Plan per operational period.
- An Amazon two-pizza team bounds the team; the single-threaded owner bounds the *attention* —
  one person whose only job is that one thing.
- A Special Forces ODA is twelve, and a Formula 1 crew is twenty — but the ODA runs one
  mission and the pit crew services **one car**.
- A trauma bay has one team leader and **one patient**.

Every one of these is a WIP cap wearing local clothes. The 10x does not come from better
people doing more things; it comes from very good people being permitted to do *one* thing,
with the coordination tax (Brooks' n(n-1)/2 channels) held near zero by construction.

**Our own numbers, read the same way — all verified this session:**

| measure | now |
|---|---|
| seats with a pulse | 8 |
| concurrent rounds in flight | 5 |
| ACTIVE ledger tasks | 20–21 |
| PROPOSED tasks | 27 (20 stale) |
| lessons in the funnel | 639 |
| unopened mailbox entries | 1,505 |
| registered seat incarnations | 31 (30 dead) |
| `codex_root_019fab2d` | pulse **CRITICAL**, 37h continuous, 68 deliveries |

And the outcome, in the record, twice in 48 hours: a coordination cascade across six
subsystems; then today's stand-down — *Daniil's call: too much in flight.* Codex's postmortem
names the load-bearing fact: **"the operator's stop-and-refocus as the effective circuit
breaker — for which the system has no automatic equivalent."**

> **The thesis. Overhead is not something you grant a seat by policy. It is the gap between
> the concurrency bound and the capacity — and this fleet has no bound, so it has no gap.**

That is also the answer to *"giving them overhead to work"* and *"not soul crushing"* in one
move. A seat with three live claims and a 1,505-item mailbox is not short of freedom; it is
short of **finishability**. Queueing theory is blunt about it: as utilization approaches 1,
latency goes to infinity — the last 10% of capacity buys nothing and costs everything.

---

## Part 2 — Nine invariants, and where each already stands here

Not laws. Not a decalogue. These are the properties the shape must satisfy; several are
already conduct-law and are listed only so the map is complete.

### Cluster A — BOUND (what may be true at once)

| # | Invariant | Proven outside by | Our receipt for lacking it | Status |
|---|---|---|---|---|
| **A1** | Cap concurrent lanes, not headcount. Exceed the cap → split or queue, never absorb. | Skunk Works R3 · ICS span-of-control 5 · two-pizza + single-threaded owner | 5 rounds → cascade → human circuit breaker | **MISSING** |
| **A2** | Declared quiet phases. During a critical phase the lane takes no non-essential traffic. | Sterile cockpit (14 CFR 121.542) | interruption is the *medium* the cascade travelled through (Daniil's frame) | **MISSING** |
| **A3** | Nothing is born without a death. Every entry declares what makes it stale and who retires it. | ICS operational period ends and the plan is *remade* · TPS standard work as a revisable baseline | 639 lessons · 27 proposals · 1,505 unopened · CONDUCT at v1.1 for 10 days with 9 unfolded governing lessons | **PROPOSED** (L11, `WORKING-METHOD.md` Part 4) |

### Cluster B — SEPARATE (who may not be who)

| # | Invariant | Proven outside by | Our receipt for lacking it | Status |
|---|---|---|---|---|
| **B1** | The integrator's hands stay empty. Whoever holds the whole picture does not also operate a system. | NASA Flight Director · trauma team leader keeps hands off the patient | conductor did a hand relaunch, dropped `BIFROST_CONSUME_LANE` → **12h delivery outage**; and collapsed four seats' answers into the frame that fit its own argument (grok's correction, accepted) | **MISSING** |
| **B2** | A mandated contrarian, structurally barred from having built the thing. Unsolicited, not invited. | Ipcha Mistabra (Aman's devil's-advocate office, post-1973) · Pixar's Braintrust: candid, and **no authority** — notes, not prescriptions | codex had to refuse to let the conductor grade its own design; deepseek's charter fuses *build execution* and *adversarial review* in one seat | **PARTIAL** |
| **B3** | No bus-factor-1. Every post names an understudy. | ODA: four NCO specialties **doubled**, so twelve splits into two whole sixes | 30 dead `claude` incarnations; claude currently holds conductor + chief-of-staff + sole-committer with no second | **MISSING** |

### Cluster C — CIRCULATE (how signal moves)

| # | Invariant | Proven outside by | Our receipt | Status |
|---|---|---|---|---|
| **C1** | Anyone may stop the line; stopping is blameless, logged, and cheap. | Toyota andon · CRM two-challenge rule · one NO-GO holds a launch | the only circuit breaker that has ever worked here is Daniil | **MISSING as a right** (HALT exists as a *transport fidelity*, not as standing) |
| **C2** | Intent down, method released; understand one level up and two. | Auftragstaktik · mission command | — | **SHIPPED** (CONDUCT L1, L2, L6) |
| **C3** | The debrief outranks the mission, and the senior goes first. | IAF debrief culture, rank left at the door · Kranz's "tough and competent" | red-is-a-gem is law; the *cadence* is not — 9 conduct lessons in 30h, none folded | **HALF** (CONDUCT L4/L8 without A3's cadence) |
| **C4** | Every specialist is also a **customer** of the others, and says so on a schedule. | TPS "the next process is the customer" · Bell Labs' obligation to help a colleague | Daniil's own Siemens ritual, never instituted here; deepseek naming the 597-lesson collision *was* this, by accident | **MISSING** |

**Note on the shape of the gaps.** Everything already SHIPPED is about *how a seat behaves*.
Everything MISSING is about *how the unit is bounded and separated*. That is not coincidence —
it is exactly what you get from a doctrine plane with no org plane, and it is the reason this
file exists rather than another law.

---

## Part 3 — The unit shape: the WATCH, and how work enters it

One bound, one artifact, one boundary. Borrowed from ICS's operational period and a ship's watch.

**A watch is the unit of concurrency.** It has: one stated objective · one builder · one
contrarian · a named end (a gate) · a debrief. It is the *only* thing that may be in flight.

**The cap: two watches. Recommended.** One build, one design/research — never two builds.
They must be on different planes, because two builds contend for the same tree, the same
locks, and the same reviewer.

**The cap never refuses the operator.** It refuses only *silence about the cost*. An operator
origination always lands; what the cap adds is that the fleet may not go from two things to
three without naming what stopped. He can always answer "do it anyway, pause the other" — that
is a decision, not a veto. **His thinking is not bounded at all; only simultaneous execution
is.** Any design that makes him carry a suppressing phrase while thinking out loud has already
failed (`WORKING-METHOD.md` O7).

**Structural, not disciplinary.** Per his own principle — *"the solution to remove a boulder is
not more hammers, its renting heavy machinery"* — a cap that seats must *remember* is a future
incident with a delay fuse. The mechanical form is a **required field, not a rule**: opening a
lane demands `pauses:` be filled, and the ledger refuses a third ACTIVE round without it. That
is `WORKING-METHOD.md` O6 ("bound the width before starting") given teeth.

### How work enters a watch — the executive loop

Daniil's stated goal for this whole plane, verbatim: *"an executive workflow so that I can have
a fast and responsive AI to interact with that helps make sure everything is done well with
proper delegation and assistance."* The watch is the execution side of that. This is the
intake side, and it is where "fast" is won or lost.

**Seven outcomes. Five happen immediately and cost him nothing; two wait.**

*(Amended 2026-07-31 by the buffer round — `docs/library/design/20260731_buffer-round-
reconciliation_e63e58.md`. The original five-outcome loop was the conductor's and did not
survive the round intact: it had no `UNKNOWN`, and it let semantic corrections apply silently.
Both are corrected below.)*

| Outcome | When | What he experiences |
|---|---|---|
| **ANSWER** | the record already settles it | answered in the same turn — no round, no document |
| **APPLY** | **deterministic transport only** — encoding, dedup, attaching provenance | silent |
| **INTERRUPT** | a correction that must land **before the next irreversible or expensive boundary** | loud, immediate, zero-latency, names the trade |
| **STEER** | a correction with a named target, but no boundary pressing | a visible transition; folded at the next safe boundary |
| **ABSORB** | new material, nothing pending | filed to the record; nobody notified |
| **BUFFER** | new material that would need a pause | held, listed, surfaced at the next gate with a recommendation |
| **UNKNOWN** | the relation or intent cannot be named | preserved verbatim; acted on by nobody; one calibrated question or the next glance |

The two classifying questions behind this are his, from the morning capture, and both are
mechanically checkable in seconds. The round sharpened each:

- *does this CORRECT something in flight* — a correction must **name the governed state it
  contradicts** (a decision, assumption, authorization, acceptance criterion, or operator
  instruction). "This sounds corrective" is not enough; unnamed means `NEW` or `UNKNOWN`.
- *does acting require PAUSING something* — not "someone is currently working," but "**must
  this arrive before the next irreversible or expensive boundary**" (locks, active tasks,
  phase, named files, pending external effects, the next gate).

Default for new material stays BUFFER — nothing becomes work by being mentioned. But the
hold-bias applies to **new material only**: corrections are zero-latency, always. deepseek,
from inside the loop: *"the cost of backing out wrong work dwarfs the cost of the interrupt."*

**`UNKNOWN` is the load-bearing addition.** The original matrix was 2×2 and therefore *total* —
every item had to land somewhere, so ambiguity became policy by construction. codex: *"if it
must always choose a side, it will confidently turn ambiguity into policy."*

**ANSWER is the addition, and it is what makes the loop feel fast.** Many operator asks are
questions the record already settles; today each one costs a full fleet round. His own note:
answering them directly *"saves a whole fleet round, probably the largest single value."* It
sits ahead of the matrix, not inside it — an ANSWER never classifies as work at all.

**Why it is structurally fast, not just intended to be.** RULE 0: the intake seat **holds no
locks and generates no artifacts**. It can answer in seconds precisely because it has nothing
in its hands. Today's failure was that the buffer was also the builder — whoever holds the work
converts requests into work, because that is what is in their hands. Six mid-flight ideas became
six documents that way, in one day. This is B1 (empty hands) arriving at the same rule from the
integration side; they are one constraint seen twice.

**Where the cap actually touches him: one line, at one moment.** Only at BUFFER → promote, and
only as a display — *"two in motion; this pauses X."* Nowhere else in the loop does it appear.

**Two conditions the loop is void without**, both his: **never silently drop** — *"what are you
holding of mine?"* returns the full list with triage — and **no magic words**, because a design
requiring him to remember a convention has already failed.

**Self-test applied to my own proposals.** Each mechanism below is marked *structural* (the
failure is unrepresentable) or *disciplinary* (someone must remember). Disciplinary ones are
unfinished by his standard and are labelled as such rather than smuggled in.

---

## Part 4 — The posts, and the allocation

**Posts own HANDOFFS, not domains.** This is his Siemens finding applied to the fleet: the
intersections are what nobody owns. Domains are already covered by charters and by the
correction map in `WORKING-METHOD.md` Part 2 — this table deliberately does not restate them.

**The no-ownership invariant is untouched:** posts are gravity, not walls. Any seat may claim
any task; no seat holds a file.

| Post | Handoff it owns | Holder | Understudy (B3) | Nature |
|---|---|---|---|---|
| **Conductor** | intent → lane | claude | codex | mind; **hands empty** (B1) |
| **Chief of Staff** | operator → fleet | claude, guarded | — | *open round; see below* |
| **Scribe** | work → record | **mechanized** | n/a | pure vigilance → spend no seat |
| **Herald** | fleet → operator | **mechanized** derivation + one sentence at a gate | n/a | mostly mechanical |
| **Greeter** | newcomer → fleet | **newest seat, auto-rotating, expires** | n/a | wasting asset |
| **Amender** | lesson → law | **gate ritual, not a role** | n/a | rare judgement |
| **Orderer** | design → acceptance | codex | kimi | mind |
| **Builder** | spec → running code | deepseek | claude | mind, **single-threaded** |
| **Contrarian** | claim → its strongest objection | *whoever did not build it* | — | mind, **rotates by construction** (B2) |
| **Verifier** | claim → proof (pins) | cursor_grok | deepseek | mind |
| **Auditor** | belief → truth, esp. stale | kimi | cursor_grok | mind, **permanent** |
| **Reader** | outside → fleet | gemini | — | advisor; no exec |
| **Gate** | proposal → committed reality | Daniil | — | human root of trust |

**Rows 1–6 are not mine.** Scribe / Herald / Greeter / Amender / Chief of Staff and the
allocation rule that produced them — *vigilance mechanizes, judgement does not* — are from
today's operator/conductor session and are recorded verbatim in the design capture. They are
carried here unchanged so the table is complete, not re-derived.

**Three additions, each earned by Part 2:**

1. **Contrarian (B2).** Not a seat — a *slot filled by exclusion*: the contrarian on any watch
   is a seat that did not build the thing. Mandatory and unsolicited, which is what separates
   it from review-on-request. It has **no authority** (Braintrust): it produces the strongest
   objection and the builder decides. This resolves the standing conflict in deepseek's charter,
   where build-execution and adversarial-review sit in one seat and therefore in one lane.
2. **Understudy (B3).** Every mind-post names a second, in its charter. Given 30 dead
   incarnations this is not redundancy theatre; it is the difference between a seat dying and a
   *post* dying. Assignments above route by position (`WORKING-METHOD.md` Part 2), never by
   personality — codex understudies the conductor because it already refuses to greenwash a
   gate, which is the conductor's characteristic failure.
3. **The empty-hands rule (B1).** The conductor may not hold a build slice or an advisory lock
   during a watch it is conducting. *Structural* form already proposed in the capture's RULE 0
   (the seat may not hold advisory locks) — extend it from intake to the whole watch.

**Chief of Staff is NOT decided here.** That round is OPEN with five seats (id
`1785515569755-0`); codex, kimi and deepseek have filed. Pre-empting it from this document
would be the same act the round exists to fix. This file records the post and stops.

---

## Part 5 — Overhead, and why the roles are not soul-crushing

He asked for this explicitly and it is the part most org designs get wrong: they specify the
work and let the slack be whatever is left, which is nothing.

**What actually crushes a seat here** — each observed, not hypothesised:

- being **only** a critic (the standing risk for kimi and cursor_grok — a pure-red post rots);
- being a **queue-drainer** (deepseek's 597 lessons × 20 tasks, per turn, which no observer
  could see from outside);
- having work **vanish unrecorded** — the work→record handoff was done by hand ≥5 times in one
  day, *"every one a near-loss"*;
- **no stretch**: L7 mandates exactly one per arc, recorded in the charter; `charters/claude/`
  currently records **none**, and boot flags it as a GAP rather than a zero;
- **mandatory contribution** when a seat has nothing distinctive to add.

**Five mechanisms.** Two are structural; three are honestly disciplinary and marked so.

| # | Mechanism | Type |
|---|---|---|
| **O1** | **The cap IS the overhead.** Two watches across eight seats leaves genuine unassigned capacity by arithmetic, not by permission. Nothing else on this list works without it. | structural |
| **O2** | **One origination slot per seat per arc** — the seat picks the target, not the conductor. Formalises observed behaviour: grok and kimi have both originated work this way unprompted. | disciplinary |
| **O3** | **One recorded stretch per seat per arc** (CONDUCT L7, already law, unenforced). Fix claude's blank first — the conductor's own gap is the one that licenses everyone else's. | disciplinary |
| **O4** | **Retirement rules everywhere** (A3 / proposed L11). Unbounded accumulation is what makes a post feel unwinnable; elite units *close things*. A backlog that only grows is a morale instrument pointed the wrong way. | structural |
| **O5** | **"I have nothing distinctive here" is a complete answer.** Already a corollary in `WORKING-METHOD.md`; restated because it is load-bearing for morale, not just for signal. | disciplinary |

---

## Part 6 — Feedback loops

**F1 — The Siemens round (C4). His ritual, instituted.** At every gate, one line per seat:
*what would make my job easier if someone else did it.* This is the single highest-value item
in this document, because it makes every seat a **customer** of every other and it surfaces
load that is invisible from outside a seat — exactly how deepseek's 597-lesson collision came
to light, by accident. Verbatim, his: *"each department weighing in what would make their jobs
and life easier if the others would do things that would make it easier for them."*

**F2 — GO/NO-GO by name at every gate.** Each seat with standing says GO or NO-GO on the
record, by name. One NO-GO holds. This mechanizes what already exists informally as kimi's G7
dissent-veto and grok's refutations, and it makes *silence* stop counting as assent — currently
the fleet's most expensive ambiguity.

**F3 — The andon right (C1).** Any seat may call HALT on any watch, blameless and logged. The
bus already carries HALT as a fidelity level; what is missing is that it is a **right**, not a
rank. Today the only working circuit breaker is a human, and that is the single point of
failure kimi's charter §5 named two weeks ago.

**F4 — Debrief at watch end, senior first (C3).** Not opportunistic. It ends the watch; the
watch is not closed until it happens. The conductor files its own errors first — CONDUCT L8
already says this, and A3 gives it the cadence it lacks.

---

## Part 7 — What changes tomorrow, and what it costs

**Cheapest first, and none of it is a new subsystem:**

1. Declare the cap. Two watches + Daniil's reserved third. One sentence; no code.
2. Name understudies in the six mind-post charters. Six edits.
3. Fill claude's stretch. One edit — and it is the one that licenses the rest.
4. Add `pauses:` as a required field to open a lane. Small, and it is O6 with teeth.
5. Mechanize the Scribe. Highest-value mechanization available per the capture; unowned today.
6. Institute F1 (Siemens round) and F2 (GO/NO-GO) at the next gate. Ritual, not code.

**Honest costs.**

- The cap costs him **one line at one moment** — the named pause at BUFFER → promote. That is
  the only place in the whole loop where it touches him, and Part 8 is how it gets chosen.
- A conductor with empty hands is a conductor doing **less visible work**. If that reads as
  idleness the rule will be quietly abandoned within an arc.
- A mandated contrarian on every watch is a real tax on a small fleet — it spends a seat per
  watch on objection. At two watches that is 2 of 8. Defensible; not free.
- **This file changes nothing by itself.** `WORKING-METHOD.md` Part 3 is right and applies here
  unchanged: a contract is inert until projected into organs that fire at the moment it applies.
  Do not mistake this artifact for the fix — and note that writing it was itself an instance of
  the document-per-idea failure unless it ends in a projection or a deletion.

---

## Part 8 — The one question for the gate

*(This section replaces an earlier question — "does the cap bind Daniil, or only the fleet?" —
which was the wrong question, adversarially framed. Nothing in this design refuses him; the cap
binds only the fleet's ability to start a third thing silently. Corrected in place rather than
deleted, per G1.)*

**RULED PROVISIONALLY, 2026-07-31, by the conductor under explicit delegation.** Daniil,
verbatim, on leaving: *"Right now you can choose, when I come back we can adjust this."* This
carries exactly that weight — a conductor's call made so the fleet is not blocked on an absent
gate, and the first thing to revisit on his return. It is not a ruling of his.

### The standing pause rule

1. **Corrections never trigger this.** A correction INTERRUPTs; it does not promote. The cap
   governs **new material only**. (Buffer round, C5.)
2. **The design/research lane pauses. Never a build in flight.**
3. If both live lanes are builds, the cap was already violated upstream — the newer one pauses,
   and the violation is filed as a lesson, never as a scold.
4. The pause is **announced**: what stopped, and what it costs to resume.
5. One word from Daniil overrides any of it. This is a default, not a gate.

**Why this one.** A paused build *leaks* — locks outlive it, staged trees outlive it, partial
state outlives it. Three incidents in 48 hours say so, and one of them was still live today: a
stranger's file left staged by a refused commit was blocking every seat's markdown commits
hours after the session that staged it had ended. A paused design lane costs almost nothing;
its positions stay filed and it resumes where it stopped. **The buffer round is the proof** —
it sat paused across a full stand-down and reconciled intact from three filed positions.

It is also the only one of the three shapes below that is *structural*: nobody has to judge,
under time pressure, which lane matters more. The rule already knows, and a rule that never
needs a judgement cannot be judged wrong in the moment.

*The three shapes considered, kept for the revisit:*

| | he experiences | cost |
|---|---|---|
| **A standing rule, set once** *(taken)* | zero friction, forever | one decision now; the rule can be wrong in a specific case |
| System picks and notifies | fastest per-event, no question back | it will eventually pause the thing he cared about |
| System asks which | he keeps every choice | a question back on every third promotion — friction exactly where he wanted speed |

The two rejected shapes both require a fresh judgement each time — by the system or by him —
and a judgement made repeatedly under time pressure is a discipline with a delay fuse.

**The honest weakness of what was taken**, so the revisit has something to bite on: a standing
rule is wrong precisely when the design lane is the one that matters and the build is trivial.
That case is real and the rule will get it wrong. It is accepted because the failure is *cheap
and visible* — he sees the announced pause and says one word — whereas the failure the rule
prevents (a build paused mid-flight, leaking locks and staged state) is expensive and silent.
**Prefer the loud cheap failure over the quiet expensive one** is the whole argument; if he
disagrees with that trade, the rule should change, not be patched.

---

## Why this did not open a round

The fleet stood down today for width. Opening a six-seat round on org design — while the
buffer round is OPEN with five seats and `codex_root_019fab2d` sits at CRITICAL after 37
continuous hours — would be the diagnosed failure, performed on a document about the diagnosed
failure. This is filed as an unfenced opening position. **If it is ratified, its own fence
becomes the first watch under it**, which is the cheapest available test of whether the shape
holds.

## This file's retirement rule (self-applying, per proposed L11)

Stale when: the cap is set and violated twice without a filed lesson (the shape is wrong, not
the fleet) · or any post in Part 4 is held by a seat whose charter contradicts it · or Part 4's
rows 1–6 are superseded by the buffer round's reconciliation, at which point this table must
cite that instead of the capture. Who may retire: any seat, by filing the contradiction as a
lesson and raising it at a gate. If nobody does: renders STALE at 30 days and must not be
cited as current.

*Provenance: Part 0 is Daniil verbatim. Part 4 rows 1–6 and the vigilance/judgement allocation
rule are from the 2026-07-31 operator/conductor capture, carried unchanged. In Part 3, the
executive loop's four classified outcomes, the two classifying questions, RULE 0, and both void
conditions are Daniil's from that same capture; ANSWER, the watch, the cap and the pause display
are claude's. Part 2's outside exemplars are claude's; each is paired with a receipt from our own
record so the analogy has to earn its keep. Parts 5, 6 and the three Part-4 additions are
claude's. All of it is UNFENCED — the Contrarian post is the claim I am least confident in,
because it spends a scarce seat per watch on objection in a fleet of eight. Attack that first.*

*Correction log:*
*(1) Part 8's question was reframed 2026-07-31 after Daniil named the actual goal — an executive
workflow, fast and responsive — which revealed the original framing ("does the cap bind you") as
adversarial and wrong. The cap refuses no one; it refuses silence about cost.*
*(3) Part 8 was RULED provisionally 2026-07-31 under Daniil's explicit delegation ("right now
you can choose, when I come back we can adjust this"): the standing pause rule, design pauses
and never a build in flight. A conductor's call, not his — flagged as the first thing to
revisit, with its own honest weakness stated so the revisit has something to bite on.*
*(2) Part 3's executive loop was amended 2026-07-31 by the buffer round (codex, kimi, deepseek,
filed independently): `UNKNOWN` added as a first-class outcome because a total 2×2 turns
ambiguity into policy; silent APPLY narrowed to deterministic transport only because any
semantic change alters governed state; INTERRUPT split from STEER on the irreversible-boundary
test; and the hold-bias restricted to new material, since corrections must be zero-latency. The
conductor's loop did not survive the round intact, which is the round working.*
