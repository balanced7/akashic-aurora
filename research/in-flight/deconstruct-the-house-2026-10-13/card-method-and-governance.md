# Teardown card: METHOD AND GOVERNANCE (how the house decides, checks and amends its own work)

Date: 2026-10-13. Seat: Vandor (claude), a read-only subagent of the "deconstruct the house" run.
Method: `teardown-card.md` (draft v1), all eight rows, every claim labelled, loop altitude per
`docs/pillar-analysis-method.md`.
Scope: the doctrine documents (`docs/method-baseline-2026-07.md`, `docs/CONDUCT.md`,
`docs/PRINCIPLES.md`, `docs/WORKING-METHOD.md`, `docs/pillar-analysis-method.md`, `docs/ORG.md`),
the fences in `fences/` (the blind halves), the skills in `.claude/skills/`, the task ledger
(`state/coord/tasks.json` and the `task` verb), the wishlist (`docs/WISHLIST.md`), and the
department system. In the repo the department system is ORG.md's posts table, the seat charters
in `charters/`, and the living plan's threads and waves
(`docs/library/design/20260801_the-plan_*.md`). The seat's private memory names it too; I did not
read that, per the privacy rule.

**What I did NOT change.** I made no edits to house files. I ran no boot, learn, note, handoff,
wrap, grant, lock or bus send, and no git command that changes anything. Side effects, stated so
nobody mistakes them for organic traffic ((a) to (c) I could not avoid; (d) I could have):
(a) the user-level PreToolUse hook fired on my roughly 70 shell calls and surfaced lessons each
time (it bumps their counters);
(b) `recall` and `recall --json` reads may bump recall counters;
(c) I imported two checker modules into a throwaway Python process to call their pure functions
(`check_reconciliation_gate.decide` / `audit_stats`, `method_drift.boot_line` / `_stats`). Both
only read files and git history.
(d) **`doctor`, which I ran as a read and which is not one** (corrected 2026-10-13 after review). I
ran `py agent_cli.py doctor` and `py agent_cli.py doctor --json` (Row 2's watch gauge and live-seat
rows; V1), because the brief listed "doctor WITHOUT --page" as a read. Both go through
`examine_fleet(...)` (`agent_cli.py:5838`), so each was a write-capable round: page-grade findings
"ALWAYS escalate to the pager", the human-facing channel, whatever `--page` says
(`core/comm/doctor.py:1604-1608`, `:1640-1641`, `:1746-1757`); `_reconcile_pages` runs every round
and can retract standing pages and delete their escalation keys (`:1642`, `:1653-1720`); and each
agent's stall-hysteresis key is set or cleared (`:138-155`, called at `:470-486`). **What they did
or may have done is unknown.** I did not record the page-grade count of either round, so a page
push cannot be ruled out, though the bus card's read-only replay saw 0 page-grade agents that
morning (bus V7) and no page was standing at 10:00-10:20 (house H18). A retraction, a deleted
escalation key or a changed stall key is possible. Pages leave no durable record (bus I4), so this
cannot be checked after the fact.
I deliberately did NOT run `wish-curate`, even its read-only listing, because that path takes a
file lock whose sidecar lives in `docs/` (see finding F6).

---

## The picture in one paragraph (for Daniel)

Think of the house's method as a chip company's **design-verification and sign-off flow**:
- The doctrine documents are the **design-rule manual** and the methodology handbook.
- A fence is **two independent verification teams** writing testbenches against the same spec
  without seeing each other's work.
- RED-then-GREEN commits are **writing the failing assertion before the fix**.
- `scripts/ship.py` is the **tape-out sign-off checklist** (the DRC, LVS and timing run before
  the design goes to the fab).
- The git hooks are the fab's **incoming inspection**: every wafer passes through it whether
  anyone likes it or not.
- The task ledger is the **project tracker**, the wishlist is the **errata and feature-request
  list**, ORG.md sets the **work-in-progress limit** (how many tape-outs may be in flight) and the
  posts, and the skills are the **laminated checklists** at each bench.
- The scorecards are the **yield dashboards**.

**Thesis (one sentence).** The house writes excellent design rules and has built a real sign-off
checker, but the tape-outs go around the sign-off desk. The checker lives only on a door that one
of its own steps has kept locked since August (a spelling rule fails on two ratified documents and
on a stray lock file). So 1 of 31 high-risk ships in two weeks carries its review record. The
trackers (ledger, wishlist, fence registry) lag what was actually built by weeks. And the one
dashboard number that would say so is printed in the shift-end report, not on the floor display.
The **measurement is excellent; the actuation is cut**. WORKING-METHOD.md predicted exactly this
about itself on 2026-08-01: "writing this file changes nothing by itself."

---

## Row 1: Purpose

- **What it is for.** The house's own words call it a contract: it decides **how** work is done.
  The method baseline sets the bar: "a practice without a measurable signal is an aspiration, not a
  baseline", and it governs "HOW all system work is done (the companion to AGENTS.md's WHAT)".
  **observed**: `docs/method-baseline-2026-07.md:4,10-13`.
- **The three planes.** CONDUCT says how a seat behaves, WORKING-METHOD says where work comes from,
  and ORG says how the unit is shaped (how many things run at once, who holds which post).
  **observed**: `docs/ORG.md:26-32`.
- **For whom.** Every seat, and Daniel as the gate ("Gate: proposal → committed reality | Daniil |
  human root of trust"). **observed**: `docs/ORG.md:261`.
- **The outcome that would make it worth keeping.** A fresh seat behaves to the method without
  being told: "A fresh seat does not become this law by reading it. It becomes it because five
  existing organs carry it into the moments where it applies." **observed**: `docs/CONDUCT.md:61-63`.
  The plan's Wave E says the same in Daniel's register: "the doctrine fires by itself ... This wave
  is what stops the other four from drifting." **observed**:
  `docs/library/design/20260801_the-plan_a84b0d.md:278-282`.
  So the purpose is **self-firing governance**, not documents. **inferred** (from the two quotes).

## Row 2: Observables (what we can see without trusting its self-description)

All from today's live house (2026-10-13). Every number comes from a command I ran or a file I read.

| what | value | where it came from |
|---|---|---|
| task ledger rows | 424: done 172, proposed 114, approved 39, abandoned 52, parked 18, claimed 15, verifying 12, in_progress 2 | `state/coord/tasks.json` (counted) |
| ledger's own footer | "done 172 / active 29 / next 38 / proposed 114 (114 stale) / parked 18" | `py agent_cli.py task list` |
| two-watch gauge | "watches 2/2 [T079, T385]", both owned by sol, last moved 2026-09-02 and 2026-09-05 | `py agent_cli.py doctor` (a write-capable round, see (d) above); ledger history |
| ledger traffic since 2026-09-05 | 33 proposed, 9 claimed, 9 verifying, 6 done, **1** in_progress | ledger history (counted) |
| the 6 completions since 09-05 | all went claimed → verifying → done, none through in_progress; T406/T407/T408/T411 in the same minute as the claim | ledger history |
| last ledger completion | 2026-09-26 (T411) | ledger history |
| commits since 2026-09-27 | 287, with 17 mentions of any T-number | `git log --since=2026-09-27` |
| shipped but still "proposed" | T418, T420, T421, T422, T423: RED and GREEN commits 2026-10-01/02 (e.g. `90ae6f32`, `d395fb90`, `70264777`, `e8fc657e`); ledger status `proposed`, rendered "(untouched 12d)" | `git log`; ledger |
| T031 (method enforcement) | ledger: parked 2026-08-01, "Forcing functions unbuilt". git: `303c2b30` 2026-07-11 "T031 hooks 2-4: method-baseline enforcement lane complete" | ledger history; `git show 303c2b30` |
| reconciliation-gate audit, last 300 commits | 33 staged substrate paths; **1 passed (3%)**; 32 offenders | `check_reconciliation_gate.audit_stats(300)` |
| arc scorecard, last 14 days | 269 commits. M1 "FIRED 31 [self-report]". M3 "MEASURED 70/123 clean (57%)". M11 "MEASURED **1/31** SUBSTRATE ship(s) gated (3%)" | `py scripts/arc_scorecard.py --days 14` |
| boot's method-drift line | silent (`''`): M3 11/13 = 84.6% over a 30-commit window, threshold 80% | `method_drift.boot_line()`, `_stats(30)` |
| doc-currency guard (a ship.py step) | **FAIL, 17 violations**, including `docs/ORG.md` and `docs/WORKING-METHOD.md` ("unrecognized status vocabulary: '**RATIFIED** ...'") and `docs/WISHLIST.md.lock` (untracked) | `py scripts/checkers/check_doc_currency.py` |
| unpushed work | local master ahead of origin/master by 76 commits (origin's last: 2026-10-07 `1d6e070a`) | `git status -sb` (no fetch run) |
| newest knowledge snapshot | `backups/snapshots/20260924_224413` | `ls backups/snapshots` |
| fences | 33 folders; the fence verb knows 24; 9 have no `fence.json` | `ls fences/`; `py agent_cli.py fence list` |
| fences listed "open" but reconciled on disk | identity-grounded-boot, resume-on-deaf, wake-by-need, wake-origin (each holds `reconciliation.md` and `pv_report.json`) | fence list vs folder listing |
| who conducts the fences | every fence with an `opened_by` (19) was opened by claude; about 21 of 24 reconciliations open with "claude" or "Vandor" | `fence.json`; head of each `reconciliation.md` |
| M1-LITE tier recorded on ledger rows | 0 of 424 rows carry a tier field | ledger keys (counted) |
| done rows with a named reviewer | 26 of 172 (23 by deepseek) | ledger `reviewed_by` |
| wishlist | 276 W-blocks, 262 distinct ids (W57-W69 and W211 doubled); 188 open, 88 folded, **0 declined**; 15 more dated entries filed after `## Declined`, outside the numbering | `docs/WISHLIST.md` (counted) |
| wishlist lag, measured by the house | `b110d6a3` 2026-10-07: "close 49 wishes that were already built (open 234 -> 185)" | `git log -- docs/WISHLIST.md` |
| boot stance block | stamps `conduct-v1`; CONDUCT.md is conduct-v2 since 2026-09-10 | `agent_cli.py:1848`; `docs/CONDUCT.md:3,48` |
| conductor lessons | 12 `conductor_*` lessons; only the L11 one carries a conduct-version stamp | `py agent_cli.py recall --json` |
| charters | 9 `CHARTER.md`; 0 name an understudy; claude's has no stretch line | `grep` over `charters/*/CHARTER.md` |
| live seats | claude, deepseek, discord, dsh_agent, kimi; the doctor examines no sol, codex, grok or gemini | `py agent_cli.py roster`; `doctor --json` (a write-capable round, see (d) above) |
| skills | 6 in `.claude/skills`; 4 mirrored byte-identical in `.agents/skills`; Cursor carries only `akashic-memory.mdc` | `ls`; `diff -q` |
| living plan | two atoms titled "the-plan", both `status: current`, both 2026-08-01, 217 vs 306 lines, untouched since | `docs/library/design/20260801_the-plan_{2d7bb1,a84b0d}.md` |

## Row 3: Mechanism (how it turns inputs into what we observe)

The chain, as built. Each step is **observed** in code or files unless marked.

1. **Origination.** Daniel's felt friction or a seat's arrives as a wish (`py agent_cli.py wish`,
   `agent_cli.py:2445`), a ledger proposal (`task propose`), or a note. WORKING-METHOD O1-O7 say
   how a problem should become work (`docs/WORKING-METHOD.md:37-83`).
2. **Promotion and width.** Daniel approves. The ledger's two-watch gate refuses a third
   IN_PROGRESS row unless the start names what pauses or carries the operator's recorded word
   (`core/coord/task_ledger.py:449-463`, cap `WATCH_CAP = 2` at `:138`). CLAIMED → VERIFYING is a
   legal route that skips IN_PROGRESS (`:82`). It was added by T139 so a finished delivery can be
   recorded "without pretending to build it" (`:85-91`). The gauge counts IN_PROGRESS only:
   "CLAIMED/VERIFYING occupy the working set, not a watch" (`:576-577`).
3. **Design.** A fence: `py agent_cli.py fence open/write/seal/pv` keeps slots for the brief, two
   blind halves and a reconciliation. It checks the brief's five sections at seal
   (`core/coord/fence_workspace.py:42-43,160`) and runs the citation-verification pass (M1-PV).
4. **Build.** RED pin commit, then GREEN commit (M3). This is visibly practised: 37 or more of the
   39 GREEN commits since 2026-09-29 have a matching RED or `pin(...)` commit just before them.
   **observed** (git log, my heuristic: a RED within the six previous commits).
5. **Ship.** `scripts/ship.py` runs, in order and fail-fast: boundaries, doc-freshness,
   **doc-currency**, comprehensibility, door parity, wiring, organ canaries, the **reconciliation
   gate** (M1), **pre-registration** (M3), **verbatim citation** (M6), the suite ratchet, then
   commit and push, an optional lesson, and a knowledge snapshot (`scripts/ship.py:28-77`).
6. **The road everyone actually takes.** The git hooks (`core.hooksPath = scripts/githooks`):
   - pre-commit: staged-file check, the seat-attribution gate, the private-plane leak guard,
     derived-doc regeneration and the guardrail ratchet (`scripts/githooks/pre_commit.py:455-540`);
   - commit-msg: the private-plane message guard;
   - pre-push: the MCP door probe ("the door gate", `scripts/githooks/pre-push:1-30`).
   **None of the method checkers (M1, M3, M6, doc-currency) run on this road.** **observed**
   (grep of `pre_commit.py` and `pre-push`).
7. **Record.** `task done` needs a commit SHA and a verification record (`task_ledger.py:465-469`).
   `wish-curate` folds, keeps or declines (`agent_cli.py:2280-2338`). `fence seal` closes slots.
   Notes come from `note` and `wrap`. Nothing joins a commit to its ledger row automatically.
   **observed** (no such join found in the hooks or in `task_ledger.py`); **unknown** elsewhere
   (search boundary: the hooks, `task_ledger.py`, `agent_cli.py`).
8. **Measure.** The method drift module rides boot, carries **M3 only**, and stays silent above 80%
   over a 30-commit window (`core/coord/method_drift.py:40-41`). The arc scorecard rides wrap and
   carries M1, M3, M11 and others (`scripts/arc_scorecard.py:221-256`). The doctor carries the
   watch count.
9. **Amend.** CONDUCT: "divergences that WORK are filed ... and folded as amendments at gates", with
   a staleness sweep (slice C6) "until C6 lands, the wrap census carries the check manually"
   (`docs/CONDUCT.md:52-57,79-85`). Each ratified doc carries a self-retirement rule, for example
   "if THAT has not run in 30 days this file renders STALE" (`docs/WORKING-METHOD.md:179-186`;
   `docs/ORG.md:432-439`).

## Row 4: First principles (each tested: can we name the evidence or law it rests on?)

| principle the subsystem rests on | rests on | verdict |
|---|---|---|
| **Revert cost sets the ceremony** (P0 proportionality) | "what breaks if we revert this?" is objective (`method-baseline:21-30`) | **design choice, well grounded** (corrected at review; it was "sound"). It rests on a real asymmetry: state corruption survives a revert, a doc change does not. Choosing to size ceremony by that asymmetry is a policy, not a law. |
| **Independent halves reduce shared blind spots** (P2, M1; this row once read "independence catches wrongness") | Knight-Leveson, cited (`method-baseline:79-80`): "correlated blind spots are real; convergence is evidence, never proof" | **scoped** (corrected at review; it was "sound"). The cited source supports a reduction in shared blind spots, not their removal; two independent halves can still agree on the same error. |
| **Guards over discipline** (PRINCIPLES 4) | "we have watched every remember-to convention decay" (`PRINCIPLES.md:40-48`) | **half-tested**. True of conventions, but a guard placed on an *optional* door is itself a remember-to convention: someone must choose to run ship.py. The principle's own revise clause ("a guard whose false-positive cost exceeds the failure it prevents") is now met (F3, F6). **Trap 1 nearby.** |
| **The yardstick before the mechanism** (PRINCIPLES 3) | the embeddings fossil | evidence is real, but its revise line is "*Would revise it:* nothing" (`PRINCIPLES.md:37`) |
| **Names must not lie** (PRINCIPLES 5) | the `Bus` class that was not a bus | revise line: "nothing known" (`PRINCIPLES.md:55`). Two of nine principles carry no falsifier, so they are held as axioms. **Trap 1, mild.** |
| **The ledger is the coordination truth** ("## TASK LEDGER -- obey THIS, not old messages", shown at boot and wake) | none stated. It is an assumption that the ledger is current. | **FAILS on evidence** (F1, F2). **Trap 1.** |
| **A WIP cap creates the slack** (ORG Part 1: Skunk Works, ICS span of control, Little's law) | queueing theory: latency goes to infinity as utilisation approaches 1 (`ORG.md:104-106`) | **sound as a law**; the implementation counts a state work no longer enters (F4). |
| **Nothing is born without a death** (ORG A3, the proposed retirement rule) | 639 lessons, 27 proposals, 1,505 unopened (receipts of 2026-07-31) | the evidence is real; the principle is still unenforced (0 declines, 114 stale proposals, 9 loose fences). |

## Row 5: Capabilities (what we would need to HAVE to build or run this)

| capability | do we have it? |
|---|---|
| Doctrine written with triggers, metrics and receipts | **yes**. The method baseline is a model of the form. **observed** |
| A ledger with a state machine and gates | **yes** (`task_ledger.py`). **observed** |
| Checkers that read git history | **yes**: reconciliation gate, pre-registration, scorecard, method drift. **observed** |
| Independent seats for blind halves | **partly**: Heimdall, Navi and Rill are live. Codex, grok, gemini and sol are not seen by roster or doctor. **observed** |
| A human gate | **yes**, Daniel. **observed** |
| **A ship door that every commit actually walks through, carrying the method checks** | **no**. The checks ride `ship.py`, which is off the road (F3). **observed** + **inferred** |
| **A commit → ledger join (ORG's "Scribe", work → record)** | **no**. Shipped T-numbers stay `proposed` (F1). **observed** |
| **An amendment clock** (C6 staleness sweep, quarterly review, the 30-day retirement rules) | **no** in code. Boot still says conduct-v1 (F7). **observed** |
| A way to see whether skills fire | **no**. The Eye counts mentions, not Skill tool calls. **observed** (`eye freq "verified-done"`: 51 events over 35 sessions, which are mentions) + W214 ("eye find cannot see tool calls") |
| Seats to fill ORG's posts | **degraded**. Four named holders are absent (codex: Orderer and conductor understudy; cursor_grok: Verifier; gemini: Reader). **observed** (`ORG.md:247-260` vs roster) |

## Row 6: Required steps (the critical path to build it from nothing)

1. Classify the work and set proportionality (M0, P0). *Done.*
2. A ledger with a lifecycle and a done-gate. *Done.*
3. **A single road**: every commit passes the method checks where commits actually go (the hooks,
   or a push gate), with a ratchet so inherited debt never makes the road impassable. *Missing.
   This blocks everything below, because until it exists every guard is advisory.*
4. **The Scribe**: commits that cite a T-number propose the ledger move; wishes and fences close
   the same way. *Missing.*
5. Fence workspace, citation pass and reconciliation gate that accept the fence's own record.
   *Built, with defects (F3).*
6. Measurements that reach a channel that acts (boot or a page, not only wrap). *Half-built:
   M3 reaches boot, M1 does not.*
7. The amendment clock: version stamps, a staleness sweep, retirement rules with teeth. *Missing.*
8. The org shape (cap, posts, understudies, the Siemens round, GO/NO-GO). *Cap and pauses built
   2026-09-04; the rest missing.* This comes last because it can only be enforced through steps 3,
   4 and 7.

**Critical path: 3 → 4 → 6 → 7.** The house built 1, 2, 5, part of 6 and part of 8, and skipped
3. That is why the whole chain reads as "built and not firing". **inferred** (from Rows 2 and 3).

## Row 7: Invariants and failure modes (what must hold, and what a break looks like from outside)

| invariant | how it breaks | what the break looks like from outside | seen? |
|---|---|---|---|
| Every law has a forcing function **on the road actually travelled** (M10) | the guard sits on an optional door; an inherited failure makes that door impassable; seats route around it | the guard's pins are green; its audit says 3%; nothing pages | **yes** (F3). The same mechanism was diagnosed once already, on 2026-07-27, in `f9f7ffa7`: "The disciplined door was impassable, so nobody used it." |
| A guard fails on the defect, not on look-alikes (M10, PRINCIPLES 4) | a vocabulary rule ("current / superseded-by / historical") meets "RATIFIED"; a lock fix leaves a sidecar file in `docs/` | the guard reports 17 failures, most of them not dead law | **yes** (F6) |
| The ledger is current (boot says "obey THIS") | completion happens in git; nothing writes it back | shipped work renders "(untouched 12d)"; a built lane is parked as "unbuilt" | **yes** (F1, F2) |
| The cap measures concurrency | work flows through a state the gauge does not count | "watches 2/2", both idle for more than 38 days, while 27 rows sit claimed or verifying, 15 to 77 days old | **yes** (F4) |
| Substrate and projections agree (CONDUCT's law substrate) | the doc is amended; the projections are not re-stamped | boot prints `conduct-v1` after v2 shipped | **yes** (F7) |
| Nothing is born without a death (ORG A3) | the birth door is one command; the death door is unowned | 0 declines ever; 114 of 114 proposals stale; 9 loose fence folders | **yes** (F5) |
| No bus-factor-1 (ORG B3) | one seat opens, conducts and reconciles nearly every fence | all 19 recorded openers are claude; about 21 of 24 reconciliations are by claude | **yes**, **inferred** as risk |
| Retrieval does not colour unrelated work (AGENTS.md placement gate, question 4) | the gate checks at capture; nothing checks at retrieval | on my first `ls` the hook surfaced a codex lesson about religion and atrocity attribution (`learn:experiment:atrocity_chain_without_perpetrator_simulation`) | **yes**, once. This belongs to the recall card; noted here because the placement gate is governance. |

## Row 8: Verification (predictions that could have failed, each with its test)

| # | prediction (stated before looking) | test | result |
|---|---|---|---|
| V1 | The two-watch cap holds: at most 2 IN_PROGRESS | `py agent_cli.py doctor` (not a read: a write-capable round, effect unknown, see (d) above) | **held**: "watches 2/2 [T079, T385]". But see V2. |
| V2 | Work since the cap passed through the gated state | ledger history since 2026-09-05 | **failed**: 6 of 6 completions skipped IN_PROGRESS; the only start was T385 (with an operator ruling) |
| V3 | Work shipped in git is closed in the ledger | `git log` for T418-T423 vs the ledger | **failed**: 5 rows with RED+GREEN commits are still `proposed` |
| V4 | The T031 ledger row agrees with git | ledger history vs `git show 303c2b30` | **failed**: "unbuilt" (08-01) vs "complete" (07-11) |
| V5 | The reconciliation gate refuses a substrate ship that cites a document which is not a reconciliation | `decide("fix the bus, see docs/PRINCIPLES.md", ["core/comm/bus.py"])` | **failed**: `PASS`. `MARKER_RE = reconcil\|GATE` with IGNORECASE (`check_reconciliation_gate.py:30`) matches "gates" in PRINCIPLES.md. `docs/FOSSILS.md` passes too. |
| V6 | The gate protects every full-fence path M1-LITE names (core/foundation, AGENTS.md, the method doc itself, `method-baseline:137-143`) | `decide(..., ["core/foundation/ledger.py"])` and `(..., ["AGENTS.md", "docs/method-baseline-2026-07.md"])` | **failed**: both `NOT_APPLICABLE`; prefixes at `:24-27` omit them |
| V7 | The gate accepts a fence's own reconciliation as the citation | `decide("per fences/t386-pre-execute-recall-gate/reconciliation.md", [...core/comm...])` | **failed**: `FAIL, no artifact cited`; `CITATION_RE` accepts only `docs/` or `research/reviewed/` (`:29`) |
| V8 | Substrate ships meet M1's bar ("zero solo-shipped trust-boundary changes") | `audit_stats(300)`; `arc_scorecard.py --days 14` | **failed**: 1/33 and 1/31 (3%) |
| V9 | The doc-currency guard passes on the ratified governance docs | `py scripts/checkers/check_doc_currency.py` | **failed**: ORG.md and WORKING-METHOD.md unstamped; 17 violations total |
| V10 | Boot's stance block carries the current conduct version | `agent_cli.py:1848` vs `CONDUCT.md:3` | **failed**: `conduct-v1` vs conduct-v2 |
| V11 | ORG Part 7 steps 2-3 landed (understudies named, claude's stretch filled) | grep charters | **failed**: 0 of 9, and none |
| V12 | The fence verb sees every fence folder | `fence list` vs `ls fences/` | **failed**: 24 of 33 |
| V13 | Skill copies across harness homes are identical | `diff -q .claude/skills/X .agents/skills/X` | **held** for all four mirrored skills |
| V14 | M3 is practised: GREEN commits are preceded by RED pins | git log since 2026-09-29 | **held**: at least 37 of 39. But the two readers of M3 disagree: boot reads 84.6% over 30 commits and stays silent; the scorecard reads 57% over 14 days. |

Fourteen predictions; three held, eleven failed. Every failed one points at the same place: the
link between "built" and "recorded / enforced / amended". **inferred**.

---

## Loop altitude (the value chain, and whether the signal flows back)

| link | the signal | does it flow back? |
|---|---|---|
| L1 felt friction → captured | wishes, proposals, verbatim asks | **yes**: wish numbers run to W263 (262 distinct), 424 ledger rows. Capture is one command. |
| L2 captured → promoted or retired | approval, the cap, decline | **weak**: 114/114 proposals stale, 0 declines, the cap counts a bypassed state (F4, F5) |
| L3 promoted → designed (fence) | brief, halves, PV pass, reconciliation | **mostly**: 24 registered fences. But 9 are invisible to the verb, 4 read "open" though reconciled, and the PV pass has run 9/9 and 7/7 false MISSING on two fences (F8). |
| L4 designed → built | RED → GREEN | **yes**: the healthiest link in the house (V14) |
| L5 built → shipped through the gate | ship.py's method checks | **CUT**: the checks live off the road (F3) |
| L6 shipped → recorded | ledger done, wish folded, fence sealed | **CUT**: no join; the trackers lag by weeks (F1, F2, F5) |
| L7 recorded → measured | scorecard, method drift, doctor | **yes, the measurement is excellent**: the scorecard prints the 3% itself |
| L8 measured → acted on | a page, a boot line, a block | **CUT for M1**: 3% reaches only wrap. Boot carries M3 alone, on a window that reads healthy (F9) |
| L9 acted → amended (laws move) | C6 sweep, quarterly review, the 30-day retirement rules | **CUT**: no clock in code; stamps stale (F7) |
| L9 → L1 the customer loop (ORG F1 Siemens round, F2 GO/NO-GO, F3 andon right) | each seat says what would make its job easier | **not found** in code (grep for siemens, go-no-go, andon, herald: no hits outside docs). The Herald exists only as a recipe lesson (`herald_page_measured_not_quoted`). |

**This is a designed-open loop at three links (L5, L6, L8), plus an unwired amendment edge (L9).**
The pillar method's tells are all present: "telemetry names waste nobody has acted on", "growth
without decay", "docs claim more than wiring delivers" (`docs/pillar-analysis-method.md:53-58`).

---

## The findings (each labelled; Chesterton's reason stated before any change is proposed)

**F1. The ledger, which boot tells every seat to obey, lags git by weeks.** **observed**: T418,
T420, T421, T422 and T423 shipped 2026-10-01/02 and read `proposed` / "(untouched 12d)". The last
ledger completion was 2026-09-26, while 287 commits have landed since 09-27 with only 17 T-number
mentions. Boot renders "## TASK LEDGER -- obey THIS, not old messages" (`task_ledger.py:747`).
**inferred** cause: the verified-done skill defines "done" as ship.py plus a where-we-are note
and never mentions closing the ledger row (`.claude/skills/verified-done/SKILL.md:16-21,36-37`),
and nothing joins commits to rows.
*Why the ledger exists:* it is the coordination truth that ended mail-driven confusion (T001). Keep
it; feed it.

**F2. A built lane is recorded as unbuilt.** **observed**: T031 is parked 2026-08-01 "Forcing
functions unbuilt". Commit `303c2b30` (2026-07-11) says "enforcement lane complete", and the
checkers exist (`scripts/checkers/check_reconciliation_gate.py`, `core/coord/preregistration.py`,
`scripts/arc_scorecard.py`). The method doc still titles them "Enforcement lane (proposed as T031)"
(`method-baseline:327`). Map versus territory, **trap 4**.

**F3. The method's forcing functions sit on an off-ramp, and the off-ramp is closed.**
- **observed**: the M1, M3 and M6 checkers and doc-currency run only inside `ship.py`
  (`:31-45`). The git hooks every commit passes do not run them.
- **observed**: doc-currency fails today on 17 items. ship.py is fail-fast, so a ship.py run stops
  there. **inferred**: ORG.md has carried "Status: **RATIFIED**" since `bc04a390` (2026-08-01), so
  this step has failed on every ship.py run since then, unless something else changed the verdict.
  The ledger's own T192 says the same ("Foreign doc-currency debt blocks every ship: ratified
  status is rejected", untouched 69 days).
- **observed** corroboration: 76 unpushed commits; the newest snapshot (ship.py's last step) is
  09-24; the gate audit is 1/33.
- The exact mechanism was diagnosed and fixed once, for the suite step, in `f9f7ffa7` (2026-07-27).
  It recurred five days later through a different step.
- **observed**, a Goodhart defect in the gate itself (**trap 5**): any cited `docs/*.md` that
  contains the letters "gate" anywhere (gates, delegate, investigate, navigate) satisfies it (V5).
  It also leaves Store and Ledger, AGENTS.md and the method doc unprotected (V6), and refuses the
  house's real fence records (V7).
- *Why ship.py exists:* to make the whole ritual one command so no step is forgotten
  (`ship.py:1-15`). *Why doc-currency exists:* a dead doc once declared itself the single source of
  truth for a lane model AGENTS.md had abolished (`check_doc_currency.py:4-7`). *Why the gate
  exists:* "without it, we're just two agents chatting." All three reasons stand. The fault is
  placement and matching, not existence.

**F4. The width cap counts the one door nobody walks through.** **observed**:
- the gate guards IN_PROGRESS only (`task_ledger.py:456-463`);
- since 2026-09-05, completions went CLAIMED → VERIFYING → DONE, a route T139 built for recording
  already-finished work (`:85-91`);
- the two watch slots are held by sol's T079 (since 2026-09-02, opened 2026-07-15) and T385 (since
  2026-09-05). Sol is not on the roster;
- meanwhile 27 rows sit claimed or verifying, 15 to 77 days old.
The cap reads "2/2, lawful" while the real working set is 29. That is Goodhart (**trap 5**) and
reductionism (**trap 3**: all nine width-gauge pins pass, but the behaviour lives in the route).
*Chesterton:* CLAIMED → VERIFYING exists so a delivered slice can close without faking
IN_PROGRESS events. And the watch excludes CLAIMED and VERIFYING on purpose: "CLAIMED/VERIFYING
occupy the working set, not a watch" (`task_ledger.py:576-577`). Keep the route and keep what a watch
means; show the working set beside the watch count instead of folding it in.

**F5. Birth has a door; death does not fire.** **observed**:
- 0 declines in the wishlist's whole history, though the decline door exists (built 2026-09-23,
  `agent_cli.py:2280-2290`);
- 114 of 114 proposals stale;
- 9 fence folders without `fence.json`. The wish filed 2026-09-28 asking `fence list` to name
  LOOSE folders is still unbuilt (V12);
- 15 wishlist entries filed by hand as dated sections after `## Declined`, outside the numbering
  that `wish-curate` parses;
- two "current" copies of the living plan (the known atom-fork defect, filed three times as T188,
  T241 and T333, all untouched 58-69 days);
- ORG A3 says the retirement rule is "PROPOSED (L11)". The ratified L11 is a different law ("the
  adversary takes an artifact"), so **one id names two laws** (`ORG.md:121` vs `CONDUCT.md:42`).
  That is a PRINCIPLES 5 ("names must not lie") breach.
The one recorded death event was manual and large: 49 built-but-open wishes closed in one sweep on
2026-10-07, and a weekly triage task was set up the same day. That is the loop beginning to close.
**observed** (`b110d6a3`, `783e1464`).

**F6. The fix for one law tripped another law's guard.** **observed**: the wishlist lock (added
2026-10-02 after 6 of 40 concurrent filings were silently lost, `agent_cli.py:2465-2481`) leaves a
0-byte sidecar `docs/WISHLIST.md.lock` (`core/foundation/filelock.py:80`). It is not git-ignored,
so doc-currency fails on it as "[untracked]". **inferred**: nobody noticed for 11 days because
nobody runs the guard (F3).

**F7. The doctrine's drift-proofing is designed but unwired.**
- **observed**: CONDUCT's law substrate requires every projection to "stamp law_id +
  conduct_version at creation" and promises a staleness sweep C6 (`CONDUCT.md:48-57`). Today boot
  says `conduct-v1` (`agent_cli.py:1848`), the six founding conductor lessons carry no stamp (the
  `conductor_red_is_a_gem` record has no version field), and C6 is not found.
- **observed**: ORG.md's plane table still says WORKING-METHOD is "(PROPOSED)" and CONDUCT is
  "conduct-v1, L1-L10" (`ORG.md:30-31`); both moved.
- Of CONDUCT's five activation organs:
  - recall-at-action: built (the conductor lessons exist);
  - boot stance block: built, with a stale version;
  - the wrap census (brief-format score, morale trinity): not found;
  - charters: no stretch lines, no understudies;
  - the fresh-boot kata scorer: not found (the `kata` verb proves toolbelt aliases, not
    conduct).
  Search boundary for "not found": `agent_cli.py`, `scripts/arc_scorecard.py`, `core/narrative/`,
  and a `*.py` grep for the bar's phrases.
- WORKING-METHOD's own clause ("if THAT has not run in 30 days this file renders STALE") has no
  code behind it, and the file was last touched 2026-08-01. **observed**.

**F8. The citation-verification pass (M1-PV) cries wolf.** **observed** in the reconciler's own
words: "SECOND FENCE, SECOND 100% FALSE-POSITIVE RATE. t385 produced 9/9 false; this produces 7/7"
(`fences/t386-pre-execute-recall-gate/reconciliation.md:102-129`); wish W209 names the cause ("M1-PV
reports MISSING for citations it merely cannot reach"). A guard whose every alarm is false teaches
the reader to skip it, which PRINCIPLES 4's revise clause warns about.

**F9. Two readers of the same metric disagree, and the quiet one is the one people read.**
**observed**: boot's method-drift reads M3 at 84.6% over 30 commits and stays silent
(`method_drift.py:40-41`). The scorecard reads 57% over 14 days and flags it. Neither boot nor any
page carries M1's 3%. The scorecard also prints "M1 FIRED 31 [self-report]" one line above "M11
MEASURED 1/31 gated", so the self-report and the measurement contradict each other on one screen.
**trap 5**.

**F10. Org posts are staffed by seats that are not in the house.** **observed**: ORG Part 4 names
codex (Orderer, conductor understudy), cursor_grok (Verifier) and gemini (Reader). None of them
appears in the roster or the doctor today, and both open watches are owned by sol, who is also
absent. **inferred**: the retirement rule's trigger ("any post held by a seat whose charter
contradicts it") is met in spirit, and the posts table describes a fleet of 2026-08-01. The
doctor also lists the operator's legacy inbox id "daniil" as "ghost mail from a retired seat"
(50 unread). **unknown**: whether that id is simply retired in favour of another.

---

## Traps named

1. **False first principles.** "The ledger is the truth; obey THIS" is an assumption with no
   evidence behind it (F1). PRINCIPLES 3 and 5 declare no falsifier. "Guards over discipline" hides
   a discipline: choosing to run the door that holds the guards (F3).
2. **Chesterton's fence.** These are tempting to delete and must not be: the CLAIMED → VERIFYING
   route (T139), the doc-currency guard (T016 F1c), the wishlist lock (6/40 lost writes) and
   ship.py itself (the one-command ritual). Every proposal below keeps the part and fixes its
   placement or its matching.
3. **Reductionism.** Every part passes its own pins: width gauge 9 pins, gate pins, the M3 pins.
   The failure lives in the routing between parts (F3, F4).
4. **The map is not the territory.** Ledger versus git (F1, F2), fence verb versus folders (V12),
   ORG's plane table versus the current docs (F7), boot's `conduct-v1` versus CONDUCT v1.2.
5. **Goodhart.** The gate's "gate" substring (V5), the cap counting a bypassed state (F4), and the
   self-report "M1 FIRED 31" next to the measured 1/31 (F9).

---

## The Great Sage report

> **Notice.**
> - Ship.py's method checks did not run where commits go: the reconciliation gate's own audit
>   reads 1 of 33 substrate ships gated (`audit_stats(300)`), and the scorecard reads 1/31 over 14
>   days.
> - The doc-currency step fails today on 17 items, two of them the ratified ORG.md and
>   WORKING-METHOD.md, one a lock file.
> - The ledger shows T418-T423 as `proposed` although their RED and GREEN commits landed
>   2026-10-01/02, and shows T031 as "unbuilt" although `303c2b30` completed it on 2026-07-11.
> - The width gauge reads 2/2, but all 6 completions since 2026-09-05 bypassed the counted state.
> - Boot stamps `conduct-v1`; CONDUCT is v2.
> - 0 of 9 charters name an understudy.
> - The wishlist has 0 declines; 9 of 33 fence folders are invisible to the fence verb.
> - The reconciliation gate passes a ship that cites `docs/PRINCIPLES.md`, and refuses one that
>   cites a fence's own reconciliation.
>
> **Analysis.**
> - The method is well specified and well measured, but its back-edges are cut at three links:
>   ship → enforce, ship → record, measure → act. A fourth, act → amend, has no clock. This rests
>   on the four observations above, taken together.
> - The cause is placement, not absence. The checks were built (`303c2b30`) but attached to an
>   optional door that a single failing step can lock (`f9f7ffa7` diagnosed this on 2026-07-27; it
>   recurred through doc-currency on 2026-08-01). Meanwhile the hooks every commit passes carry
>   privacy and authorship, not method.
> - The trackers lag for the same reason: the definition of "done" a seat carries (the
>   verified-done skill) never mentions the ledger.
>
> **Unknown.**
> - Whether ship.py has run at all since 2026-08-01. I inferred it from the failing step, the
>   snapshot dates and the 76 unpushed commits; there is no run log.
> - Whether skills fire: the Eye counts mentions, not Skill tool calls.
> - Whether sol, codex, grok or gemini still work through channels the bus does not see.
> - Whether the scorecard's 57% (M3) counts commits that pin and fix legitimately together.
> - Search boundaries: the hooks, `ship.py`, `task_ledger.py`, `agent_cli.py`, `scripts/checkers/`,
>   `core/coord/`, and `*.py` greps for siemens, go-no-go, andon, herald and the fresh-boot bar.
>   "Not found" there never means "absent".
>
> **Proposal** (smallest first; every part kept, with its reason):
> 1. Git-ignore the lock sidecar or move it out of `docs/`. Keep the lock: it stopped 6/40 lost
>    wishes.
> 2. Teach doc-currency the ratified vocabulary, or re-stamp ORG and WORKING-METHOD as
>    "Status: current (RATIFIED 2026-08-01)". They are Daniel's ratified texts, so this is his
>    call. Keep the guard: it exists because a dead doc once posed as law.
> 3. Fix the gate's matching: require a real reconciliation header, accept
>    `fences/<id>/reconciliation.md`, and add `core/foundation/`, `AGENTS.md` and the method doc to
>    its protected list, as the method doc's own tier 1 already says.
> 4. Put the M1 and M3 checks on the road (the pre-push door gate), as a ratchet that blocks only
>    new debt, the shape `f9f7ffa7` already proved. Keep ship.py as the one-command ritual.
> 5. A Scribe that proposes ledger moves from commits citing T-numbers. It proposes and never
>    closes on its own, per PRINCIPLES 7. Add a doctor line: "commits cite T418, row is proposed".
> 6. Show a separate working-set number (claimed + verifying + in progress) beside the watch count,
>    and flag a watch idle for more than 14 days. Do not change what a watch counts: the gauge
>    excludes claimed and verifying rows on purpose ("CLAIMED/VERIFYING occupy the working set, not a
>    watch", `task_ledger.py:576-577`). Keep the T139 route.
> 7. Bump `CONDUCT_VERSION` to v2 and add a 20-line stamp check (a C6 seed).
> 8. Let boot's method-drift carry M1 as well, with the same silence-when-fine rule.
> 9. Make `fence list` name loose folders; settle the four reconciled-but-open fences.
> 10. Ask Daniel whether ORG's posts table should be re-staffed (understudies, stretch) or
>     re-stamped to today's fleet.
>
> **Verification.** Fourteen predictions, each of which could have failed. Three held: the cap
> count, skill-mirror identity, and RED-before-GREEN practice. Eleven failed, all at the
> built-to-recorded or built-to-enforced link (Row 8, V1-V14). Every check but one was a read:
> task list, fence list, roster, git log, the checkers' pure functions, the doc-currency checker
> and the arc scorecard. The exception is `doctor`, which I ran twice as if it were a read. It is
> write-capable (it can push pages to the human pager, retract pages and set stall keys), and what
> my two rounds did is unknown (see (d) at the top).
>
> **Proceed?** **NO, not without Daniel.** Proposals 2 and 10 touch his ratified documents. Proposal
> 4 changes a full-fence surface (the method doc's own forcing functions), so it needs its own
> fence. Proposals 1, 3, 6, 7 and 9 are small and cleanly revertible, but they still wait for his
> word.
