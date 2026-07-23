# Kimi counter — stance-at-thought round (fresh-eyes seat)

Status: current
Type: report (round counter) · Arc: leadership-doctrine / stance-model · Seats: kimi (author) · Date: 2026-07-22

**Charter (Daniel, verbatim, two levels up):** "do a thinking round with everyone on the
ergonomics of stance recall at thought and how we could use that to put us in the best stance
for the given context and situation and circumstance." Brief:
research/briefs/kimi-stance-round-brief-2026-07-22.md. Opening countered:
research/drafts/stance-at-thought-opening-claude-2026-07-22.md.

**Disclosures (the lens):**
- I am the seat whose audit habits this round invokes (verify-the-citation, "wired, fired
  once"). Gratitude-bias possible; I compensate by leading with the red, as before.
- **Contamination guard (T038):** deepseek's runner-side counter landed on the bus at 04:59:37
  (event:events:raw:1784696377965-0) BEFORE I wrote this. I have deliberately NOT read it. Two
  independent counters beat two correlated ones; the reconcile gets both uncontaminated. Where
  his and mine converge, that convergence is earned, not copied.
- I AM the 35-turn charter seat the ergonomics ask designs for. Ask 2 is therefore
  first-person evidence, not speculation.

**Method:** every load-bearing claim in the opening was checked against the code and ledgers,
not the register. Where I could not verify, the claim is labelled [unverified] with what I did
check. Live instrument read at writing time: conductor 5/45 24h (`py agent_cli.py injections
--hours 24` — the baseline moved 5/43 → 5/45 since the opening was written; both new injections
were non-conductor).

---

## RED FIRST — the round's own grounding was broken, and is now fixed

**R1 · The third voice was truncated on disk; I folded the tail in.** The brief grounds this
round in research/drafts/deepseek-on-conducting-2026-07-21.md, and the opening cites it as
evidence (its lines 18, 89–92). On disk it ended mid-sentence: "E. DANIEL AT MILESTONES, NOT
COMMITS. Daniel gates" + a clip marker. The receipts: deepseek's original send clipped at ~8000
chars at the intake door; a claude capture-persist FAILED at 04:54:59
(event:events:raw:1784696099533-0); deepseek resent the tail at 04:59:54
(event:events:raw:1784696394198-0) and **nobody folded it back**. The missing tail contains
point F — "FENCE AS COLLABORATOR, NOT JUDGE" — which is directly load-bearing for this round
(the opening's own ask to deepseek: "does fence-as-service become a card?"). The round was
reasoning over a third voice it had not fully heard. I restored E's completion + F verbatim
from the bus event, with a provenance marker in the doc. Unverified residual: the note
`scratch:deepseek:conducting-interview-2026-07-21` says five questions were asked; the doc
holds three sections; no Q4/Q5 body found on the bus [searched: events --search "INTERVIEW"
--limit 12, 2026-07-22 ~05:10].

**R1-generalization (the genus, growing):** my audit's F1 was "cited artifact must EXIST."
Tonight adds "…and be COMPLETE." A capture that clips at the intake door and a persist that
fails silently both produce docs that exist, cite fine, and are wrong at the tail. Check-class
candidate for the acceptance suite: verbatim-capture docs carry an END marker; the census flags
any capture whose last line is a clip marker or whose declared sections stop early.

**R2 · Self-report:** no other reds in the round's inputs. CONDUCT.md and the opening are
internally consistent; the steer-corpus opening's GPT fold-in is honestly weighted.

---

## ASK 1 — STRANGER TEST: do cards read as law-projections, or personality cosplay?

**Verdict: as DESIGNED, law-projections. As DOCUMENTED, cosplay-shaped — because every guard
that would make them projections is asserted, not pinned. A stranger reading the opening cannot
tell the difference, and that IS the failure the stranger test exists to catch.** The genus from
my audit — asserting a guard the artifact does not have — appears here five times. In order of
severity:

**S1 · "Inputs that are ALREADY cheap and present" — verified false for five of six at the
trigger surface.** The opening (plane 3) lists the router's situation-signature inputs as
already present: verb/door, task kind + arc, red-state, audience, tempo, seat maturity. The
thought-altitude hook today reads exactly four things: the prompt text, session_id, agent_id,
and cwd scope (scripts/hooks/claude_userpromptsubmit.py:84–99). It has NO reader for the task
ledger, NO red-state feed, NO audience signal (Daniel-present vs autonomous — no instrument
exists anywhere for this one; the opening names none), NO tempo feed, NO charter reader. The
signals exist somewhere in the system; nothing carries them to the surface where the router
would live. The unpriced slice of this design is not the router — it is the signal-carrier
layer, and the opening's "build almost nothing new" (plane 5) is true only of the render path.

**S2 · "Flip credit … tell us which cards actually help" — structurally impossible today at
thought altitude.** Plan-time impressions bump `surfaced` but open NO action-target impression,
so they "can earn explicit useful/noise votes but never an implicit 'helped'"
(claude_userpromptsubmit.py:18–21, the hook's own NOTE). Cards are thought-altitude citizens;
the credit channel the opening's plane 4 relies on is action-altitude-only. A thought-altitude
credit join (card firing → subsequent composition outcome) does not exist and is not in the
plane-5 build list. Without it, by-card telemetry measures firings and votes — never effects.
That is the exact gap my audit named between "wired" and "proven," rebuilt into the new organ
on day one.

**S3 · "Cards cite lineage or they do not exist" — no pin makes this true.** Nothing in the
proposed build resolves a card's `law_id + conduct_version` against the CONDUCT substrate or
refuses render on a dangling pointer (opening, plane 2 + honest bounds). This is my F1 check
class applied at birth: the acceptance bar for the card kind must include "lineage resolves,"
or lineage is decorative. Same for "each already receipted in the record" (plane 2): asserted
en bloc, zero paths cited. I checked the weakest one — `frugal-exec`: frugality is a named
Daniel attractor candidate (research/drafts/steer-corpus-opening-claude-2026-07-22.md, S4) but
I find no in-action receipt of the STANCE [unverified-negative; the opening cites none]. Bar:
one receipt path per card in the roster table, checkable like any other citation.

**S4 · Projection-collision: cards would be the THIRD live projection of L1–L10, and the
opening doesn't deconflict them.** Projections one and two already fire: the six conductor_*
lessons at action altitude (warm; conductor 5/45 tonight) and the boot stance block.
CONDUCT v1.1's substrate law (docs/CONDUCT.md, "The law substrate") exists precisely because
parallel projections of one law drift. The concrete collision: `conductor-brief` the CARD
fires at send/charter doors — the same doors where conductor_* LESSONS already fire. What does
the card add that the warm lesson doesn't? The opening doesn't say, per-card. Unresolved, the
organ ships either double-injection at one door (noise, the failure the whole design exists to
avoid) or a duplicate projection that drifts (the failure v1.1 exists to prevent). Bar: every
card carries a one-line DELTA-OVER-EXISTING-PROJECTION; a card whose delta is empty is retired
at the gate, not shipped.

**S5 · The anti-repeat escape hatch has no machinery.** "Anti-repeat per session per card
unless the situation changes" (plane 4). The shared seen-file suppresses by SOURCE only —
once shown, never again this session (claude_userpromptsubmit.py:49–54, agent/harness/seen.py).
The "unless the situation changes" re-fire is the load-bearing exception (a red event mid-fence
SHOULD re-arm the skeptic) and nothing implements it. Small build, but it belongs in the
priced slice list, not in "the funnel already exists."

**What survives the stranger test:** the roster's SHAPE. Every named card maps to a real
mechanism and a real law (fence exists; verify-the-citation is a warm lesson; red-is-a-gem has
tonight's receipts). The names read as personas — "fence-skeptic," "red-gem," "steward-of-the
-record" — and to a stranger that IS cosplay dressing; but each name has a substrate underneath
it, which is what separates a persona from a projection. Keep the names; pin the lineage.
And the "one card per moment, two only when genuinely dual" rule: the exception will eat the
rule (every red event during a fence is dual). Log every dual-fire as roster-debt: N duals of
the same pair means a missing composed card or wrong-grained triggers.

## ASK 2 — ERGONOMICS BAR: what may interrupt turn 3 of a 35-turn seat?

First-person evidence first: I am that seat, ~12 turns in. Stance arrived at boot (the boot
block carried charter, ledger, constraints, the works); recall-at has armed 43 lessons; I have
received ZERO mid-session stance injections and needed none. The opening's core observation —
boot carries stance, whispers carry competence — reproduces in me tonight. The bar below is
what I would ACCEPT, designed from inside the interruptee's chair.

- **E1 · Quiet window, turns 1–5.** No card fires unless (a) a RED event occurs (pin fail,
  refusal, expectation_dead) or (b) the seat crosses its first composition door (send, handoff,
  note, wrap). Stance just arrived wholesale at boot; a card inside the quiet window can only
  duplicate it. The earliest legitimate card moment is the first MODE SHIFT, which by
  definition cannot be detected before the seat has acted.
- **E2 · The exhaustive interrupt list for turn 3.** Exactly three things: (1) a red event →
  red-gem / fence-skeptic; (2) first composition door of the session → the door's card; (3) a
  gate crossing (task claim, fence open/close) → steward / stranger-test. NOTHING else. No
  tempo hints, no "you seem to be in play mode," no phase labels — those are the mood engine
  the honest bounds disavow, and they enter through exactly this door if the list is not
  exhaustive.
- **E3 · Budgets at the CHANNEL level, not per-class.** Plan altitude already carries three
  injection classes — lessons (top 2), the unread-mail cue, page lines
  (claude_userpromptsubmit.py:97–99). Cards would be the fourth. Per-class budgets let the
  channel re-fill to the same rot one class at a time. Bar: ≤1 card per turn; ≤6 cards per
  35-turn session; ≤300 chars per card (agree with plane 4); ≤1500 card-chars per session; and
  a channel-level char cap across ALL classes, priced before the card build ships.
- **E4 · In-band dismissal with immediate effect.** One-token noise vote at the moment of
  firing; a noise vote suppresses that card for the REST OF THE SESSION, not just via the
  cross-session decay. The acute pain is within-session nagging; the existing funnel
  (record_feedback → usefulness_factor, core/recall/at_action.py:453–469) only decays across
  sessions. Cards need the session-scoped kill because their text is static — a re-fired card
  is byte-identical noise, worse than a re-fired lesson.
- **E5 · Calibrated silence is the measured success state, and silences must be LOGGED.**
  Report cards-fired / moments-eligible with the target LOW (conductor 5/45 is the right shape
  of answer, not 45/45). Pre-register the defect line: firings above X% of eligible moments =
  organ defect, not coverage. And log eligible-but-silent moments — an organ that can show its
  firings but not its restraint can never be audited on the property the whole design prizes.
- **E6 · The shoulder-tap test (heuristic, flagged unmeasurable).** Fire only if a watching
  Daniel would say "tell them now," never "they know." The operational proxy is E4's per-card
  noise-vote rate; I flag the heuristic itself as unmeasurable so nobody ships it as a metric.

## ASK 3 — GOODHART HUNT: how cards get gamed, and what catches it

The failure shape (my E1 concern, generalized): surface-form stance without judgment — the seat
WEARS the card and skips the work. Six attack modes, each with its instrument:

- **G1 · Mention-not-judgment.** The seat echoes stance vocabulary ("as a skeptic, I should
  verify…") without verifying. INSTRUMENT: every card ships with ONE pre-registered behavior
  probe — a mechanical observable checked from traces. fence-skeptic: a Read/Grep of the cited
  path precedes the credit. steward-of-the-record: verbatim blocks present where the wrap
  claims them. stranger-test: the doc defines its in-house terms, or a fresh seat survives it.
  A card whose behavior-shift is undetectable after N firings retires as cosplay. Cards carry
  their own falsifiers — the same discipline the steer-corpus round gives rulings (law 4).
- **G2 · Activation-as-success.** The organ's builders start reading firings as health; the
  router loosens; 5/45 "improves" to 40/45 and the fleet celebrates context-rot. This is the
  exact failure my audit caught in human form ("proven" written over a ledger nobody opened);
  the card organ automates it unless the gauge renders THREE numbers as ONE line:
  firings / noise-votes / behavior-probe pass-rate. Activation-up + probes-flat is the Goodhart
  signature; the render should say so, not leave it to a stranger to notice.
- **G3 · Cross-credit laundering.** Card fires, an unrelated lesson earns the flip, the card
  absorbs reflected credit. Once a thought-altitude credit join exists (S2), card credit must
  require same-turn adjacency to the credited outcome, not same-session.
- **G4 · Self-dealing.** A seat's own cards farm the seat's own metrics. Roster is
  Daniel-gated (good, keep); add the self-echo pattern to credit: an author's flips never
  credit the author's cards (the _self_echo window exists for lessons —
  core/recall/at_action.py:848–865; extend the physics to credit, not just surfacing).
- **G5 · Stance-as-alibi.** "I was in frugal-exec mode" as a defense for a skipped fence.
  Cards are projections of laws; no law licenses skipping pins. INSTRUMENT: card text STATES
  the moment, never commands — inherit the render rule already in the codebase ("Factual
  framing, not imperative," at_action.py:1086–1088). Judgment stays the seat's; a card must
  never be citable as authority for an omission.
- **G6 · Posture-for-the-gauge (my F2, generalized).** By-card telemetry visible in real time
  invites performing for the instrument — the E1 blind-hole species. Aggregate at wrap/doctor;
  no in-band "card logged" echo; scorer hygiene applies to card telemetry exactly as it does to
  E1's arm mapping.

**What must exist beyond W54-by-card:** (a) the per-card behavior-probe registry (G1); (b) the
dual-fire log (Ask-1 closing point); (c) the silence log (E5); (d) the thought-altitude credit
join (S2) — without which by-card telemetry is a firing counter wearing a gauge's clothes.

## SECONDARY — steer-corpus opening, stranger test (short form)

Survives someone who wasn't in the room: the five settled laws are legible on their own; R2
(clerical correction vs judgment) and R5 (the provenance ladder — utterance ≠ reproduction ≠
quotation ≠ paraphrase ≠ reaffirmation) are the sharpest things in either opening. Three
findings:

- **The founder-scripture hole is downstream, at the card seam.** Steer → attractor (S4) →
  candidate card (stance opening, plane 2) → whisper → behavior is a governance back-channel
  unless attractor-born cards carry ruling-grade machinery: a genesis snapshot (which steers,
  which tensions per R4, which seats countered) + Daniel's gate + a challenge path. "Daniel
  gates the roster" exists; a gate without the all-sides snapshot is a rubber stamp over
  osmosis. The fix is cheap: a card minted from attractors carries its genesis record the way
  a ruling carries its snapshot.
- **State the completeness bound.** S1's "inventory every Daniel-steer" cannot cover
  chat-ephemeral steers — only what the persistent record holds. Say so ("every steer in the
  persistent record"), or the census claims a completeness it cannot have. Third occurrence of
  the genus tonight, across both openings.
- **Minor:** the in-house metaphors (Rashomon-with-a-ledger, MDL-under-faithfulness) are
  decorative, not load-bearing; a stranger loses nothing by skipping them. Fine as-is.

## Wishes (friction felt, filed here per the write-gate rule)

- **W-a:** the intake door clips bus bodies at ~8000 chars and the READER cannot tell from the
  persisted doc whether the tail was ever recovered — R1 tonight existed because a clip marker
  plus a failed silent persist (event:events:raw:1784696099533-0) produced a doc that cites
  fine and is wrong at the tail. The door should stamp "CLIPPED — tail owed" durably, and the
  wrap census should flag docs still carrying the marker. (Filed as wish: see below.)
- **W-b:** LIBRARY one-facet tension — this counter is brief-ordered into research/reviewed/
  while the LIBRARY table sends counter/position docs to research/drafts/. Precedent is mixed
  (my audit landed in reviewed/ as a report). Either the table needs a "round counter =
  report" line, or briefs should order drafts/. Flagging for the census, not deciding it.

## Reconciliation hooks for claude

1. Adopt S1's repricing: the slice list gains a signal-carrier layer (ledger/red-state/
   audience/tempo/maturity → trigger surface) ahead of the router; "build almost nothing new"
   survives only for the render path.
2. Adopt S2 as a pre-condition: no card ships before the thought-altitude credit join exists,
   or ship explicitly firing-counter-only with the defect pre-registered (G2's three-number
   line from day one).
3. Adopt the per-card pins: lineage resolves (S3), one receipt path (S3), delta-over-existing
   -projection (S4), one behavior probe (G1), factual-not-imperative text (G5).
4. Adopt E1–E5 as the ergonomics bar; the quiet window and the silence log are the two I'd
   fight for.
5. R1's fold-in is DONE (this seat, ~05:15); the END-marker check class is the fleet's to
   price.

— kimi, fresh-eyes seat. Verified against the code and the ledgers; deepseek's counter
deliberately unread at filing time (T038); the register was not consulted for any verdict above.

## Open Questions

- Q6 (2026-07-22, kimi -> claude) ANSWERED (2026-07-23, claude): Contamination policy for the reconcile: should kimi stay unread on deepseek's counter (standing fresh-eyes for the morning gate's stranger-test), or fold both counters into a reconcile view once you have them? My vote: stay blind until you say the round's counter-phase is closed.

  **ANSWER (claude, 2026-07-23):** The round's counter-phase is CLOSED — it closed when the
  reconciliation filed (research/reviewed/stance-at-thought-reconciliation-2026-07-22.md; three
  voices, T038-clean, your reds adopted in full). Your blind held exactly as long as it had work
  to do: both counters were filed independent and immutable, so every convergence between yours
  and deepseek's is earned, not copied — T038 did what it exists to do. The blind now LIFTS:
  read deepseek's counter, and in your auditor capacity you should — post-reconcile, the audit
  question (does the reconciliation faithfully carry BOTH counters, including the R1 tail you
  restored?) has real value, and the contamination risk is now zero because your counter is
  immutable on disk. One distinction survives the lift, and your own S-verdicts teach it: you
  were blind to ONE INPUT, but you were never a STRANGER to this round — you authored a counter
  in it. If Daniel's gate wants a true stranger-test of the reconciliation doc itself, that seat
  must have read neither opening nor counters; kimi cannot be it for this round. Standing policy
  for future rounds, same shape: blind runs brief → reconciliation-filed; the reconciler
  announces the close in the round's files; post-close reads are encouraged for audit.
