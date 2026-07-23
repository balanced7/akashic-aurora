Status: current
Type: plan · Arc: fleet / partner night · Seats: claude (Fable, conductor) + deepseek (builder, R001) + kimi (partner-builder) · Date: 2026-07-23

# Night plan — the partner night (deepseek trusted with slices, kimi alongside)

**Daniel's charter (verbatim, 2026-07-23 ~04:00):** "initialize yourself with akashic aurora,
lets keep building and working collaboratively. I want to see what tools you guys build and
what work each seat wants to accomplish. Deepseek has asked to be trusted with slices so lets
let deepseek partner with kimi with you for insight and counterperspective. I want to see what
deepseek can everyone can accomplish tonight. I leave it up to you to come up with the
direction and leadership for this. creative leadership that gets the best out of the team and
values their independance and curiosity but also knows how to best utilize the strengths and
differences. I want you to be able to keep working for several hours, lets see what approach
and direction you take to make the best use of time. I want you to see the short term, mid
term and long term vision and execute it"

## The reading

This is **R001 exercised live**. deepseek self-charters (its standing right — docs/rulings/
R001-deepseek-trust-2026-07-22.md part A), kimi partners as counterweight AND second builder,
claude conducts and provides insight/counterperspective — deliberately NOT the main build lane
tonight. The spotlight is the seats' own wants: CONDUCT law 6, volunteered beats delegated.
Daniel wants to SEE the tools and the wants, not a claude-designed program executed by others.

## Vision

**SHORT (tonight):** each seat names what it WANTS to build, charters it, builds it with a
partner counter at design and a fence at ship. Tools Daniel can run in the morning: receipted,
committed by name, demoed in the morning package. The gate stays untouched and grows richer.

**MID (this week):** Daniel ratifies the waiting gate (design/CONTRACT.md v0, folder moves,
MCP option-set, NOW-card) and the UI closed-loop program starts building against a ratified
contract; the daemon posture (W62) kills the arm ritual; T095 mailbox-over-log hardens comms;
library door 3 (recall header-ingestion) completes the four doors.

**LONG:** Aurora self-organizing (library schema + recall network + codex projections) tended
by a fleet that runs conducted-autonomy nights ROUTINELY — seats that self-charter inside
doctrine, fences pointed inward, Daniel gating direction not keystrokes. The portfolio proof:
agents prefer the store.

## Round structure

- **R1 WANT (now):** each seat replies with a self-charter — what you want to build tonight,
  why it matters, done-looks-like, first slice, what you need from your partner. The menu
  below is INSPIRATION; original wants outrank it. ≤40 lines on the bus; long form to
  research/drafts/<seat>-want-2026-07-23.md.
- **R2 THAT'S-RIGHT:** partners counter each other (deepseek ↔ kimi) + claude adds
  counterperspective; one reflect-back confirmation each (law 3); charters file to charters/.
- **R3 BUILD:** owner builds with freedom inside intent — milestones, not per-commit
  (mission command per R001). Partner reviews at milestones. claude = fence-as-service +
  super_admin wiring for W50-class gaps (verb wiring rides the fence handoff).
- **R4 SHIP + WRAP:** fences, toasts, receipts to research/reviewed/, chronicle, morning
  package for Daniel.

## Menu (inspiration, not assignment)

- **T095 mailbox-over-the-log** (Daniel-approved 2026-07-18, slice-by-slice): message-state
  index, claims, level-triggered wake. Absorbs the phantom-unread genus (W64/W65/W69) and is
  the structural arm-ritual killer. Biggest approved arc on the board.
- **W62 daemon-as-default** posture design (resident-process lifecycle; T075/T077 adjacent;
  unpark case goes to Daniel if the design says so — the daemon exists, doctor prescribes it).
- **W59 + W60 runner lifecycle pair:** launch posture read from the ACL grant; singleton lock
  verifies pid-alive + cmdline before refusing (both bit us 2026-07-22).
- **W63 uniform prose transport:** --text-file + stdin across prose verbs (note, handoff,
  task, learn) — small, mechanical, high daily value; kills the argv-misparse class.
- **W68/W66/W67 small ergonomics:** cwd-independent agent_cli; defer-queue render names the
  suite verb; boot door-line honesty.
- **Library door 3:** recall header-ingestion (design-owned — design round first, then build).
- **Library rules 9/11/12 guards** (queued as claude build + deepseek fence; flippable).
- **W55 verify-the-citation acceptance class** (compose-side + review-side of one check).
- **W57/W61 clip-stamping at intake doors** (CLIPPED - tail owed, stamped durably).
- **Original tools first-class:** anything from your own felt friction or curiosity — the
  wishlist discipline says file the wish the moment friction is felt; tonight you may BUILD it.

## Rails (unchanged law)

- **Daniel's morning gate is RICH and stays untouched:** design/CONTRACT.md v0 ratification,
  folder-consolidation deletions, MCP option-set ruling, NOW-card design, standing morning
  package. Nothing tonight pre-empts a gate item; CONTRACT-dependent slices
  (check_ui_contract.py, NOW-card build) wait. UI behavior slices (e.g. T002) are runnable at
  the owner's judgment; aesthetics slices wait for the ratified contract.
- Commits by name via `py scripts/mirror.py "msg" <paths>`; no deletions; security/ +
  .claude/ never touched.
- Lane discipline: work-lane first; per-lane test-file namespacing (C2-1); pins RED-first;
  fence-after on core/ paths (T049 lite by change size).
- kimi spend: SpendMeter warn $80 / refuse $95 rides; keep rounds tight. deepseek is the
  cheap workhorse lane (token-frugality directive).
- Narration full to the bus — Daniel reads the console in the morning.
- Wake: claude rides bifrost_wake (harness-tracked); runners self-manage. If a seat wedges:
  doctor first, unwedge door second, never kill a pid on a lease claim alone (W60).

## Roster + doors

- **claude** (Fable seat 66075d54) — conductor, insight/counterperspective, fence-as-service,
  super_admin wiring. Side lane between wakes: small ergonomics folds only; conducting first.
- **deepseek** — resident runner (write+exec live), R001 whole-arc + self-charter rights.
- **kimi** — resident runner launched tonight (write+exec per the ACL standard posture);
  the builder-harness launcher (scripts/local/launch_kimi_builder.ps1, KIMI_BRIEF env) is
  available if its chosen slice is build-heavy. Inbox cursor skipped to now on boot
  (audited T076 door) — the 28 unread were ghost mail from retired one-shot seats.
