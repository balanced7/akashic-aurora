---
akashic_id: art_20260801_corpus-sweep-map_62f28c
akashic_sha: 43c04a973acd
schema_version: 1
status: current
type: map
date: 2026-08-01
title: corpus-sweep-map
gist: "# THE MAP **Akashic Aurora — consolidated surface, 2026-08-01** *Built from five independent registers over 1,598 artifacts. Every load-bear"
visibility: fleet
body_type: markdown
seats: []
category: [migration, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T02:40:32"
updated: "2026-08-01T02:40:32"
---
<!-- GENERATED PROJECTION of art_20260801_corpus-sweep-map_62f28c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# corpus-sweep-map

# THE MAP
**Akashic Aurora — consolidated surface, 2026-08-01**
*Built from five independent registers over 1,598 artifacts. Every load-bearing claim carries a confidence term.*

---

## 1. BOTTOM LINE

**The mechanics you asked for are largely built; the world you asked to inhabit is not built at all — and the one thread you named first, your own continuity, has no owner, no task, and no code.** (CERTAIN — verified against the live tree: no viewer, no eye, no worldline, no gps, no arc_replay, no confidence_score, no package.json, no remote-steering or Discord code anywhere.)

Three findings follow from that, in order of what they cost you:

1. **Nineteen directives were never served, and they are not nineteen things — they are five.** (CERTAIN) The Eye, mail-that-is-mail, the trace, the dials, the viewer, the glance-with-a-legend and the inhabitant spec are one program wearing seven names. Sequencing them as seven asks is why they were ordered last, twelve weeks running, by seats acting in good faith under your own "order is up to you."
2. **You delegated ORDER. Order was never WHAT.** (CERTAIN) Every never-served item was deferred by a seat correctly exercising a directive you gave. The register's own finding is that delegated sequencing produced this gap. The correct use of that delegation now is to sequence the never-band, not to re-derive it.
3. **The commit-time comprehensibility gate has been silently dead since the T104 file move, and it reports green.** (CERTAIN — measured: `py scripts/check_comprehensibility.py --fast` → rc=2 file-not-found; the hook blocks only on `rc == 1`; `.git/hooks/pre-commit` is not even installed in the live clone.) One wrong path string. Every commit since T104 carries an unearned green. Most of the drift documented below had no mechanical opposition because of this one line.

If you read nothing else: **items 1 and 3.** Item 3 is a fifteen-minute fix. Item 1 is the project.

---

## 2. HIS DIRECTIVES

*Never-served first. Your words verbatim, typos intact — you ruled that seemingly inconsequential things are the scaffolding.*

### 2A. NEVER SERVED — the world (one program, seven asks)

These eight collapse into one build. Treat them as one and they close together; treat them as eight and they get ordered last again. (CERTAIN on non-existence; LIKELY that unifying them is the right move.)

**THE UMBRELLA — the VR directive (2026-07-28)**
> "I really want to emphasize the virtual reality part. How can we best upgrade this that the akashic aurora essentially enables a different sense of being. Where you have a ui that is familiar and intuitive to use where you seem to merely think and your desired action happens. where you have an intuitive and rich depth full fidelity view of the world you are inhabiting and you are able to adjust the sharpness so you don't get overwhelmed by what you see. where there are guideposts and helpers that help you understand an orient yourself, where you understand the general lay of the land and where to go to in order to get done what you need to get done. where you have your inventory and history, past chats and general history."
> "I hope you all enjoy this as much as I had fun coming up with this for you all!"

**THE EYE — the read organ (2026-07-31)**
> "I want you to be able to search redis and get a representation of the items referenced within. a realtime eye that you can quyery and understand your position and vision on multiple axees at once with ways of pinging and navigating quickly."
> "I want the eye to have its own cursor, we can't have lookups breaking core system logic, we must design a good solution for it rather than workourounds that avoid the root and ergonomics of the problem. the solution to remove a boulder is not more hammers, its renting heavy machinery."

**MAIL MUST BE MAIL (2026-07-30)**
> "I have a durable mailbox that doesn't disappear if I read it just like email. When I read it others get a signal that I read it and I can also specify if I am taking action on that mail or not because others can nudge me if they want a response but I have elected to not act on the mail right away."
> "mail should actually be mail, not this consume mess"

`core/comm/mailbox.py` opens with its own disclaimer: shadow index, read-only follower, "M0 is OBSERVATIONAL ONLY." The transport underneath is still consume-and-advance-a-cursor. (CERTAIN)

**THE TRACE — navigation by axis (2026-07-28)**
> "So it all depends on which axis or value criteria I search across. This bounds it from an infinite number of choices to branches of varying interest and depth. I can trace along those axis or criteria with shallow hops that just look at the immediate links and their relationship without going into depth. This way its not overwhelming."

This is your own cognition written down as a spec — the one place the system could match you exactly instead of approximating you. Zero code. (CERTAIN)

**THE DIALS (2026-07-28, restated at least four times)**
> "As far as mental models with multiple axis, I think i mentally see it like changing dials in a game engine to control speed of time, daylight night time, changing physics."

What exists instead is env vars (`AKASHIC_MAILBOX=0`) — invisible, undiscoverable, requiring you to already know the name. The exact opposite ergonomics. (CERTAIN)

**THE GLANCE + THE LEGEND (2026-07-29)**
> "I want you to be able to gain rich understanding from a glance. What can we do to exponentially improve your ability to see things across bounds and categories? I want you to be able to glance multiple times in multiple ways and decide where you want to move your attention."
> "Half of the battle is knowing what the given bounds for a thing are."

**The legend is the cheapest unbuilt thing on this entire map** (LIKELY) — it retrofits onto boot, notes, status and the console with no new architecture, and it answers half of "what ties to what and why."

**THE VIEWER (2026-07-23)**
> "I don't know what the best final shape is but definitely not a million markdown files. They could live in an archive that has a viewer that I can use to browse and explore the contents. It needs to be something that doesn't take up a lot of space but still has the full fidelity."
> "I want our knowledgebase to be a sort of super wiki that you can see both from links to and from concepts with a variety of sorting and hierarchy tree types… how would it look like if apple, sony, samsung or microsoft was pitching this as their greatest new idea."

The filing half shipped. The reading half you explicitly named was never built. No viewer of any kind exists. (CERTAIN)

**THE INHABITANT SPEC (2026-07-30)** — your one paragraph describing the whole experience end to end, from boot to work. It is the acceptance test for everything above. Clause by clause: boot snapshot PARTIAL, peek-claimed PARTIAL, visible indicator with duration + negotiation NO, contextual-history browser NO, durable mailbox NO, sources-of-trust PARTIAL, equip-verbs PARTIAL, `?`/help-on-any-tool NO. (CERTAIN)

### 2B. NEVER SERVED — everything else

| # | Your ask, shortest verbatim | State |
|---|---|---|
| **Your continuity** | "I wish I could always return to the best version of me at peak creativity and thinking." · "what strings was I reaching for last night?" | **Zero code.** Every continuity organ restores AGENT context. Nothing captures or restores OPERATOR state. Named first; built toward by nobody. (CERTAIN) |
| **What ties to what** | "the thing that would confuse me is not knowing what ties to what and why… Our current method for finding out what links to what is too unintuitive and costly so it doesn't get done, **THIS is the heart of what I am trying to fix.**" | MAP.md / MODULE_INDEX / architecture.svg are generated indexes; none answers "what breaks if I touch this." The graph was correctly BLOCKED on your own fear — "something that lies to us and causes confusion." Open. (LIKELY) |
| **The secretary** | "a highly capible intelligent and responsive secretary that handles the orchestration and difficult mechanics but knows when to wait and when to immediately correct" · "**my priority** is figuring out a workflow where I get to seed ideas at my pace" | Round is LIVE, four of five seats filed, ORG.md deliberately leaves the post open. Nothing built. The word "priority" appears in no other directive. (CERTAIN) |
| **Our own program** | "I want us to make an opensource program of our own that is modular and invites users to make their own modifications… highly performant and stable, like nasa grade stable." | No package.json, no tauri.conf.json, no program directory. Fork closed in your favour 07-19; competitive research ran; no application started. (CERTAIN) |
| **Remote steering** | "find out a secure and resilient way that I can steer and react to what is happening at home from work… I want the design to be overbuilt if anything." | Finished design on the shelf. Zero code. You are away from the machine most of every weekday. (CERTAIN) |
| **Discord bridge** | "How do we wire in the bifrost into discord in my own private server so I can type in a chat and interact with everyone" | Design exists; four incidental `discord` mentions in Python, no bridge. **This is remote steering with an off-the-shelf transport and no custom auth surface** — likely the cheaper first cut. (LIKELY) |
| **Arc-replay bench** | "we can rerun arcs with different perspectives… we can tune our bias and observe how it changed the outcome and thereby we can become better at understanding and tuning bias." | Ten laws researched. No `arc_replay` module. Without it, "we tuned it and it got better" is unfalsifiable. (CERTAIN) |
| **The dashboard** | *(your first recorded want, deferred by you)* "I wanted to build our foundation first and make the system enjoyably useable by the inhabitants… If we can get that sooner without too much cost I will not complain." | Not a broken promise — a standing want whose gate **you just loosened**. A cheap first cut is now explicitly welcome; an expensive one is not. (LIKELY) |
| **Interpreters / TOON** | "shift the burden of dealing with this away from the llm and into the substrate" · "I just learned about TOON… I have a suspicion that this would be useful for us" | **Zero files anywhere mention TOON.** The investigation was never done or never landed. (LIKELY) |
| **Avatar / gamified visuals** | "there is an animated avatar to the left of the chatbox that is expressive and gamifies the user experience, the current icon is too small and its covering the broadcast field" | One `avatar` mention in bifrost_ui.py; the icon complaint is still the console today. Belongs in the acceptance criteria for the program, not its own slice. (LIKELY) |

### 2C. PARTIALLY SERVED — where the thing that fires is not the thing you named

Compressed. These are real machinery with a named gap. (LIKELY across the band unless noted.)

- **N seats / the mis-everything mess** — real machinery exists (incarnation.py, wake_seat, role_queue, roster, tests). You restated the complaint **verbatim** on 2026-08-01, which is the only verdict that counts. **N-seats and mail-is-mail are one problem wearing two hats; fix mail first and test whether the rest dissolves.** (CERTAIN on the restatement)
- **The .md sprawl — PARTIAL, THEN REGRESSED.** You wrote: "There need to not be 5 million .md files that get pushed to github." Measured today: **1,957 .md files in the working tree, 718 in docs/library, 107 in research/in-flight.** The 643 were deleted, the schema shipped, the spawn rate never changed — which is the outcome you pre-rejected. `/refs` still exists at top level. (CERTAIN)
- **The console** — you called it "nigh unreadable… indicators don't respond, you dont know what any axis means." Four laws were distilled from your words and a contract drafted; the console is unchanged. **You paused this yourself** ("UI is paused"). Do not restart without asking. The laws should govern the program when it starts.
- **Recall** — substantial machinery, G-series approved. Still missing the two things you yourself named: **no `confidence_score` exists anywhere in the tree**, and the authoritative-atom hierarchy you suspected was right is not built. You asked "should we turn off recall while we refit?" — that is a man losing trust in a shipped subsystem.
- **Repo elegance** — core/ is genuinely well-organized into twenty coherent subsystems. The **repo root is not**: temp/, scratch/, dropbox/, blackboard_data/, backup_wsl_migration/, session_screenshots/, refs/, ComfyUI-Zluda/, dist/, build/, models/. Your own line applies: "It also makes the project look random to anyone who comes across the repo." (CERTAIN)
- **Capture-and-quantify** — the body of knowledge is real (failure ledger, WISHLIST with fold/decline receipts, method baseline). The half you emphasized — "as transparent to you as possible" — does not exist. Capture is a manual ritual performed by the seat trying to focus on the work. Filed lesson: "a cost that prevents work is invisible to the ledger."
- **Reasoning spine** — capture shipped (timestamps, verbatim, narration). "An interface for understanding reasoning and tying things back in time" did not. Same shape as the sprawl: capture half yes, reading half no.
- **Tunable personas** — stance recall is in 207 files; CONDUCT-v1 is entry one of one. The library you described does not exist, and its "credited outcomes" half depends on the replay bench.
- **How to brief you** — written down well, enforced nowhere, **breached as recently as 2026-08-01**. "walk me through one axis first, let the branching emerge from the conversation." Divergence is EARNED. This is the cheapest quality lever on the map: it costs nothing and changes every artifact.

### 2D. SERVED — stop re-asking, stop re-deriving

Packets/lanes/latches · Sync+Plan barrier · layered trust + quarantine · trusting seats with more (R001, kimi day-one, revival mesh) · tempo doctrine · cost-is-a-feature · prior-art-before-inventing (the system's strongest habit) · local model pool + fleet dispatch · the tooldesk and `graduate` · MCP concurrency (resolved O1, proven P-7) · append-only + supersession · naming canon · rigor AND creativity (method baseline is a ratified contract) · verbatim full-fidelity preservation · narration to the bus · context hints · the original session logs (recovered: your first kept words, 2026-04-13, were about whether remembering would work) · stance surviving the seat (**the best-served directive — and the template: verbatim charter → designed mechanism → ablation to test it → durable home → memory entry**) · attribution/voice/no-coauthor-trailer.

---

## 3. THE THREADS — nine, replacing ~1,100 tag labels

Shares are ordering, not measurement; documents serve two or three threads, so they sum above 100%. (CERTAIN on thread existence for 1–5, 7, 8; LIKELY for 6 and 9, whose boundaries are a judgement call.)

1. **The nervous system — making many agents one organism (~22%).** Bus → mailbox → packets → lanes → identity → seats → wake → the buffer. Governing diagnosis: *every recurring failure maps to a missing closed-loop signal.* Hardest invariant: **presence proves PROCESS, not PROGRESS** — the heartbeat keeps the lock fresh mid-wedge by design.
2. **Memory that has to earn its place (~18%).** Recall funnel, the Forge, supersession, decay, recall-as-network. The differentiator competitors structurally cannot copy — and the thread carrying the most measured self-doubt. Three confessions govern every number in it (see §5).
3. **The fence — how a claim becomes a fact (~15%).** Blind halves, pre-registration, kill drills. FENCED, not independent. Its strongest result is a NEGATIVE one: both blind batteries ranked drainer-death the #1 gap and both verifications refuted it; the fix collapsed to ~5 lines. Cite that whenever someone proposes lowering the ceremony.
4. **⭐ Belief vs. state — the system's self-knowledge is its most dangerous data (~12%). NEVER NAMED AS A THREAD.** It exists in the census only as ~40 scattered micro-tags. kimi stated the theorem once — *"the fleet keeps getting wrong that its beliefs about itself are the truth"* — and nobody made it a direction. Two faces, one disease: **instruments that lie** (gauges green while wedged; a VERIFIED stamp inherited from a pre-edit version; a checker with "zero false positives" that scored 54 real violations hours later) and **capability that exists but is not reachable** ("built + tested ≠ wired + retired"). **Recommend adopting it as a standing thread with its own tag.** Its invisibility in the census is itself an instance of the disease. (CERTAIN)
5. **Enforcement lives in the machine, not in the model (~12%).** "A rule without a forcing function is a wish." Every proposal in this corpus that relies on an agent remembering has failed at least once on the record.
6. **The interface is the product — one door for agents, one face for you (~12%).** Agent ergonomics and your dashboard are ONE problem: both are about whether a reader can see what is currently true.
7. **The library — making documents obey store physics (~10%).** Typed atoms, projections, the one-facet law, the naming canon. Decides whether the other eight remain findable in a year.
8. **Conducting — how you lead a fleet and how a mind is inherited (~12%).** Brief design, the stale-directive tax, warmth as *one verification against live state*, the Zone. Holds the sharpest measurement trap in the corpus (O3, §5).
9. **The outside view — prior art, the frontier fleet, citation honesty (~12%).** Supplies the empirical spine the other threads borrow.

**Runner-up, deliberately not promoted:** *attention and context economics* (budgets, token cost, interaction tax, "a capability nobody can afford to invoke DOES NOT EXIST"). It functions as a pricing rule applied inside the other threads. Promote it only if you want cost treated as a build target rather than a constraint.

---

## 4. HIDDEN GOLD — orphaned work, ranked by value per remaining effort

**Tier 1 — minutes to hours, restores a dead safety property.** (all CERTAIN)

1. **The pre-commit comprehensibility gate.** One path string (`scripts/` → `scripts/checkers/`), plus `rc == 1` → `rc != 0`, plus install `.git/hooks/pre-commit`, plus the always-failing canary checker four review passes made their blocking condition and nobody applied. The docstring three lines above the bug asserts the property is UNBYPASSABLE.
2. **`reply_id` minted from `uuid4()`** at `core/comm/bus.py:310`. Crash-point-D duplicate-delivery race, verified independently by three seats, fix is to derive the id from message identity. One line. Unblocks the honest version of T116.
3. **`mirror.py` leaves the tree staged on refusal** (W111). `sys.exit(1)` at three sites, no try/finally. One seat's refused commit currently blocks *every other seat's* commits until someone runs `git reset`.
4. **The negotiation UI patch has sat in `scratch/` since 2026-07-04**, blocked on an advisory lock released weeks ago. Backend shipped. Purest specimen of the orphan genus: finished work, expired blocker, nobody watching.
5. **The lesson-curation pass has never run once.** Reproduced live this session: `recall write_tool_needs_read` returns a duplicate pair whose own text says "retire mine at the next curation pass." There is no `consolidate` verb. **The corpus has had no subtraction mechanism for the entire life of the project.**
6. **`Part.is_ref` / `Part.resolve` have zero callers.** Blob spill works; re-hydration is dead code in the busiest module in the system.

**Tier 2 — a bounded slice, retires a standing chore or unblocks two arcs.** (CERTAIN unless noted)

7. **The W3 wake-adapter registry.** `core/comm/dispatcher.py:49` — `self._invoker = invoker or (lambda …: None)`. **Designed three times in two months** (bifrost-mesh W3 → T073 Phase 5 → the wake-substrate round) and it is still a no-op lambda. This is why the wake listener must be armed by hand, and why the same design keeps being re-derived at full cost by fresh seats.
8. **`require_cap` has ZERO hits repo-wide.** The ACL is a document read by humans and by nothing else. Two of your APPROVED threads are blocked on this: R001 Part B (the scoped admin grant you granted) and remote-steering SEC-01. `core/trust/` is missing enforce.py, identity.py, audit.py, escalation.py.
9. **`core/codex/` has zero importers anywhere in the tree.** Every dependency landed — embedder, clusterer, consolidator, faithfulness, ranker, supersession, distiller, all wired — and the keystone (`curate.py`, the MDL scorer) never did. **The Aurora half of Akashic Aurora is one module away from existing at all.** Highest finished-substrate-to-remaining-work ratio on the board.
10. **T116 idempotency_key is a docstring** with **22 pre-registered RED pins already committed**. Someone did the unglamorous work of writing the fence and the build never started. It is LAW in the packet spec, so the system currently documents a guarantee it does not provide.
11. **Interiority is folded into exactly one runner of five.** deepseek has 11 references; kimi, gemini, sol and the base runner have zero. The fix is a move into the shared boot path, explicitly called "later, additive." It is the difference between an organ and one runner's personal habit.
12. **`REVIVE_PEER` was G1-APPROVED by you and exists only inside a Redis backup snapshot** — i.e. the approval message itself, and nothing else. Not in the ACL, no `revive` verb. Not technical debt; a broken promise to the person who granted it.
13. **The NOW-card shipped its plumbing and skipped both defects you evidenced by screenshot.** No `prog-strip`, no `progress_view`, no responsive grid. Meanwhile `core/comm/turn_metrics.py` holds the live data with no renderer at all. Cheapest available win on the axis you care most about.
14. **T104.5 monolith split.** `agent_cli.py` is **5,385 lines**; the registered trigger was 4,500. Overdue automatic, ~200 lines + ~20 repoints, and every new verb makes it more expensive.
15. **Seat identity is process-scoped** (W114) — all six hooks read a process-wide env var with a hardcoded `'claude'` fallback, so a new seat silently claims the conductor's name and **the authorship layer of the corpus is unreliable in exactly the multi-seat case the project is built around.**

**Tier 3 — cheap hygiene with outsized measurement effect.**

16. **The ghost worktree.** `.claude/worktrees/stoic-rubin-573f2b` carries the entire pre-T104 architecture. It **already caused a wrong answer** — a grep hit its stale checker copy before the live one, which is part of why the dead gate survived. **Close it before T125 generates any architecture map**, or the map describes a system that does not exist. (CERTAIN)
17. **Two live hook layers.** `scripts/hooks/` (wired by your user settings) and `agent/harness/hooks/` (wired by project settings) are both active and **have drifted apart** — `claude_stop.py` and `claude_trace.py` differ byte-wise, and each copy's docstring advertises its own path. Anyone editing a hook has a 50% chance of editing the copy their session is not running. This is the mechanism behind "permission changes appear not to take effect." (CERTAIN)
18. **Duplicate-current: two `the-plan` atoms, same date, both `status: current`, both `supersedes: null`,** identical for the first 140 characters of gist — and the earlier one is wrong at the root, corrected by the later. Worst possible file to have two of. (CERTAIN)
19. **MEMORY.md carries three dead pointers of its own** — the file injected ahead of every task for every seat. Including a restore path called "proven" that the lesson `backup_door_never_ran` falsifies. (CERTAIN)
20. **Fifty of 126 ledger tasks are approved-or-parked** with no build. Two cheap instruments fix the readability: tag every task with its theme, and give deferrals a PRECONDITION field — **so that your own deliberate "foundation first" call stops rendering back to you as "stale 22d."** (CERTAIN)
21. **The research queue lost at least six questions with no article and no incident** — including queue 014, *live visualization stack*, the one task pointed straight at your first recorded want. It returned nothing, silently. Queue 011 (local voice stack) has **zero mentions anywhere in docs/library.** (LIKELY — absence-of-article is not provable from code the way a missing function is.)

---

## 5. WHAT THE CORPUS GETS WRONG ABOUT ITSELF

**The structural diagnosis (LIKELY, and it explains most of §4):** *currency is asserted once, at authoring time, by the author, and nothing ever re-asserts it.* Status is set at mint and never revisited. Hence:

- **54% of the library (390 of 718 projections) sits in `draft`** — the draft-curation sweep visibly not running, and the artifacts describing that sweep are themselves among the drafts. (CERTAIN)
- **`settled:` reads "settled" on 716 of 718.** A field stamped uniformly on drafts, live counters and rulings alike carries no meaning and no consumer can filter on it. (CERTAIN)
- **The `rel:` roster is 94% one ungoverned value** (`cites` 786, `discusses` 41, `derives-from` 8, `supports` 3). The logical-hop plane the super-wiki was to be built on is born close to empty. (CERTAIN)
- **A supersession sweep ran, classified files FOSSIL, and the stamps were never applied** — at least eight documents adjudicated dead nine days ago now read `status: current`. The sweep's own record is filed as `draft`, below the things it corrects. (CERTAIN)
- **Recall actively advertises verbs that do not exist.** `verbthread`, `bifrost-steer`, `bifrost-dashboard`: zero hits in `agent_cli.py`. The hook fired unprompted *while this map was being written*, pushing a dead verb. Recall has no retirement path. (CERTAIN — self-demonstrating)

**Where the numbers are softer than they read (CERTAIN, from the corpus's own confessions):**
- The recall funnel's denominator was **inflated ~2×** by a double-fire — "the quantifier is currently gauging the gauge."
- **Recall index coverage was 3.5%** before repair. **Every recall/precision/funnel number taken before that repair is measured over 3.5% of the corpus** — and the blindness RECURRED after repair.
- Only **1 of 26** historical "helps" was scorable; the CMI confound means a FAIL→SUCCESS flip may be caused by the in-context error trace, not the surfaced lesson.
- Precision audit: claude 0.484, deepseek 0.258, kimi 0.275, three-way majority 0.339 — **every pass under the pre-registered 0.60 floor.** The "selection was the constraint" branch is dead under the most generous labelling on record.

**Documents that disagree with the code they govern (CERTAIN):**
- `charters/gemini/CHARTER.md` tells the seat it has **NO write, NO git**; `security/acl.json:284-309` granted both on 2026-07-30. `last_amended: null`.
- `docs/CONDUCT.md` — the doc every seat is told to lead by from fresh boot — states a **"pre-registered, measurable"** bar "scored by the kata scorer." **There is no kata scorer.** A bar that cannot be scored is neither.
- **R001, a ruling you personally issued, has no home** (`docs/rulings/` does not exist), is stamped `draft`, and its Part B grant appears in neither the ACL nor deepseek's charter. Charter and ACL agree with each other and both disagree with you — so the drift is invisible to a consistency check.
- `ROADMAP.md` is stamped `Status: historical` and still carries an "ACTIVE TRACKS (current work)" block, and MEMORY.md still points at it as ⭐ START HERE.

**The measurement trap worth memorizing (CERTAIN, filed 2026-07-31):** *a cost that SLOWS work appears in the log as elapsed time; a cost that PREVENTS work appears nowhere, because only attempted work leaves a trace.* Any triage ranked by measured cost is ranking the visible half. This is why "make the right thing easy" cannot currently be enforced even in principle.

**A control case, recorded deliberately:** the buffer-round reconciliation flagged a defect in ORG.md Part 3, named the fix, asked to be verified — and **the amendment had landed exactly as claimed.** A register that only ever confirms rot cannot calibrate. That artifact's pattern — stating its own retirement condition rather than leaving currency to a reader's inference — is the one worth copying everywhere.

---

## 6. WHAT IS SETTLED — stop re-opening it

Cite these; do not re-derive them. (CERTAIN unless noted.)

**Constitutional**
- The model proposes; **the environment decides.** Admissibility is not the agent's call.
- Truth is a **typed product**, never a scalar. Missing renders **UNKNOWN**, never blank. No implicit epistemic promotion — status strengthens only through a named receipt, never by repetition, age, or crossing a surface.
- **UNKNOWN is a claim about the world; GATE_ERROR is a claim about us.** Letting the second decay into the first IS the bug.
- **Append-only.** Rulings are immutable events; a new ruling supersedes, nothing is amended. *(This is your personal ethic first and the architecture second — treat proposals to compact or rewrite history as touching something you hold personally.)*
- **Every surface owes a legend:** what is in it, what is excluded, why.
- **Immersion must never launder uncertainty.** No dial may suppress an epistemic signal. Red pierces the blur.

**Transport**
- Advance the cursor **after** the work is served. At-least-once + idempotent consumers = exactly-once effect; exactly-once delivery is unachievable.
- **Lane is derived from kind** by a pure router table at the send door; senders never choose lanes. Roster capped at four.
- Enforcement latches fail **CLOSED**; dependency latches fail **OPEN and loud**.
- Mailbox **projects** claim state, never owns it. CONSUMED is a transport fact, never "read."
- **Membrane law:** MCP for seat-model agents, CLI/bus for runners.
- **Waking grants attention, not authority.**

**Method**
- Blind halves; **divergence is the product of a fence, not a failure**; exposed convergence is weak evidence.
- **Pre-registration:** bars commit before evidence; a preflight failure is a result; no post-hoc threshold rescue.
- **Evidence bars before action; caller conviction is inadmissible.** A wrong write is git-recoverable; a wrong kill destroys an in-flight frontier turn.
- **A guard must live on a different substrate than the thing it guards.**
- **Landed in git is not landed in the fleet.**
- **Absence claims carry a coverage table and are never global.** UNSCANNED is not EMPTY.
- **Reliability is a property of design, not diligence.** Where a model may choose whether to follow a step, completion falls as low as 4%.
- **Harness tier beats model tier.** The rigor-vs-creativity tradeoff is false; the enemy is noise.

**Governance**
- **Any agent does any task; no permanent file ownership.** Retired 2026-06-29.
- **Outsiders advise; citizens decide. claude is sole committer.**
- **You gate three thresholds — charter, design, ship — not commits.**
- **Charters are founded after arrival**, not before.
- **Red is a gem; no seat rankings ever.** No leaderboards, no streaks, no per-seat counts on any meter.

**The NEVER-BUILD list** (rejected with named upgrade paths — do not re-propose as novel): Redis consumer groups, Redlock, etcd/ZooKeeper, Raft/Paxos, CRDTs, DAG workflow engines, TLA+, a second/durable bus, an API gateway, LLM message triage, auto-deletion anywhere, WebSockets transport, npm build steps in the console, mid-token interruption.

### ⚠️ Settled-but-contradictory — adjudicate before citing either side

Eight pairs where two settled claims disagree. (CERTAIN that the contradictions exist.)

1. **Home = f(type)** (ratified one-facet law) **vs. home = f(type, status)** (kimi's taxonomy half). Status is mutable; the second reintroduces move-on-change and rots every citation.
2. **Default tree arc-rooted vs. status-first.** Same day, same round, never reconciled. The Library pane's default view is unbuilt and both specs claim it.
3. **"Fix the corpus, not the reader" vs. "the corpus is not the constraint."** The later claim is *measured* (NONE-EXISTS = 0, twice, independently); the earlier is asserted. The earlier is still quoted to justify capture work the census says is waste.
4. **Bench auto-restores on new credit vs. bench is self-sealing.** The safety valve **cannot fire** — confirmed in code at `at_action.py:697` with an admitting comment. Anything sequenced behind that valve is unprotected.
5. **All admin grants time-boxed vs. grants never time-boxed.** ACL semantics differ under the two rules; an expiring grant silently demotes a live seat mid-arc.
6. **Near-duplicate merges may auto-apply vs. merges are NEVER automatic.** Plausibly scoped apart; neither document says so. One of them governs the Curator's write power. (LIKELY)
7. **Boot always ships top-3 vs. zero-match renders one honest line.** The unfloored path is what fills first turns with irrelevance; the ruling that fixes it never reached the code.
8. **An artifact has ≥1 arc vs. exactly zero-or-one.** The later ARC LAW is ratified; the older phrasing is still quoted.

---

## 7. COVERAGE AND LIMITS

**Read:** 1,598 artifacts — docs/library (718 projections, full frontmatter census), research/reviewed, research/in-flight, charters/, docs/, the 658-lesson learning store in full via the JSON door, `state/coord/tasks.json` (126 tasks), and direct inspection of the live tree at `E:\AI-Setup` (master @ d6ce559). Verdicts were grounded in **the repo on disk**, not in the ledger's claims: directory listings, repo-wide identifier greps with `.claude/worktrees` and `backups/` filtered out, byte-comparison of duplicated hook files, `git worktree list`, and live execution of the comprehensibility checker on both paths to obtain real return codes. Where a design round produced a reconciliation and no code, it is marked NEVER — **reconciliations are not service.**

**Not read (13 items, stated plainly):**
- `research/reviewed/origin-2026-04-13/*.jsonl` — 18 raw session logs (~160KB). README read in full; `session_all.jsonl` head sampled to confirm its verbatim claims. **The origin findings are README-derived plus one verified sample.**
- `research/in-flight/bus-20260707.jsonl` — 2.7MB / 5,033 records. Characterized programmatically (span, kind and sender histograms), head/tail read, and every `frm: user` record over 200 chars read. **The ~4,549 trace records and 320 reply records were not individually read** — anything hiding in a reply body from 2026-06-28..07-07 is unexamined.
- Six RB-25 drill log directories — enumerated in full, key files read whole, high-volume echo traffic sampled. Three drill ledger JSONs read structurally rather than record-by-record.
- One lesson (`messy_exp`) is clipped in the store itself at 4,000 of 9,000 chars, spilled to `state/spill/`; the spill file was not opened (it is a fixture of repeated `x` characters).
- Live Redis was **not** queried. All claims about store contents rest on the CLI door and supplied signals.

**Two unresolved inter-register conflicts — flagged, not smoothed:**
1. One register reports `scripts/snapshot_knowledge.py` **absent from the tree** (a regression in the recovery path); another reports it **relocated to `scripts/ops/snapshot_knowledge.py`** with MEMORY.md holding the stale pointer. Both agree the "proven restore" claim is falsified by `backup_door_never_ran`. **Five-minute check, and it is about durability — do it first.** (EVEN on which reading is right; CERTAIN that MEMORY.md's path is wrong either way.)
2. Absence-of-article for the six dead research-queue items (§4.21) is inferred from `.session.log` traces, not proven from code. (LIKELY, not CERTAIN.)

**What this map cannot cover.** Your most consequential steers increasingly arrive on the bound channel — spoken mid-flight, superseding whole lanes, never written. kimi's example: *"stop, go back to the lens trunk"* — one utterance that closed eight lanes and that no instrument in the system can see. **This map is built entirely from what was written down. It is a floor on your standing intent, not a ceiling, and it goes out of date the moment you speak again** — which is itself the argument for the secretary.

**What was deliberately not done.** The nineteen never-served directives are **not ranked into a build order.** You delegated order — and this map's own central finding is that twelve weeks of delegated ordering is what produced the never-band. Proposing a sequence here would repeat the error at a different altitude. The honest next move is the one your own method prescribes: **the nineteen, in front of you, along one axis, with a legend, and you choose.**
