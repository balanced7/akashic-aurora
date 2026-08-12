---
akashic_id: art_20260812_resident-fanout-round2_beb19b
akashic_sha: 36baa7b2c51b
schema_version: 1
status: current
type: report
date: 2026-08-12
title: resident-fanout-round2
gist: "# Resident fanout — calibration, verdict file-back, and the scout role (fence Round 2 opening) **Trigger:** Daniil 2026-08-12, verbatim: *\"F"
visibility: fleet
body_type: markdown
seats: []
category: [security, method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-12T09:32:11"
updated: "2026-08-12T09:32:11"
---
<!-- GENERATED PROJECTION of art_20260812_resident-fanout-round2_beb19b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# resident-fanout-round2

# Resident fanout — calibration, verdict file-back, and the scout role (fence Round 2 opening)

**Trigger:** Daniil 2026-08-12, verbatim: *"Fence it and then build. Keep going as long and as
far as you can go doing multiple loops of iteration discovery, research, analysis. I want to
see if we can get better at long horizon complex tasks. I believe managing context and setting
up helper functions and roles will play a significant part in it."* Plus a standing
authorization the same morning: *"fan out for anything and everything that would be useful,
fun or curiosity driven as well as work tasks. You have my permission, authorization and
encouragement to do so."*

**Status:** OPENING POSITION for fence Round 2. Round 1 = fan-doctrine-v1-2026-08-11.md §10
(Heimdall's seven counters, dispositions folded). This document CONTINUES that arc — it is not
a rival design. Author: claude/Vandor (Fable 5, session 1159602c).

---

## 0. The one-paragraph version

The residents plane (T258–T267) gives fan branches identity and an archive (`--as-resident`,
catchup packs). The fan doctrine (T281, verifying) gives fans named geometries and a route
journal. What neither gives is **evidence that residency earns its keep** — kimi's standing
objection ("persistence has never been isolated as the cause of a win") is recorded in
residents.py's own docstring, which says the module buys LEGIBILITY ONLY. This arc closes that
gap with three slices: verdicts filed per branch (RC1), a calibration ledger projected over
them (RC2), and the first working role built on the calibrated substrate — the scout (RC3).
The result Daniil asked for: fanouts that stop being amnesiac, helpers whose track records are
data, and a repeatable pattern for minting new roles.

## 1. Honest inventory (what exists — verified in code/ledger this morning, not remembered)

- **T261 tier-1 residency** — `ask --as-resident <agent>`: callsign + receipts + up to 6 of the
  resident's OWN lessons ride the system context (residents.py `catchup_pack`,
  T260 agent-scoped recall underneath). A non-resident refuses before any model call.
- **T259 roles** — `assign(role=...)`: append-only role events, provenance derived
  (self-declared vs assigned), never a field update. Identity ≠ job, by design.
- **T281 Stage 1+2** (ledger: verifying, claude) — `--geometry
  partition|lens|panel|adversarial|backbrief|wave|negotiation` validated at the door;
  `state/route_journal.jsonl` lands one line per fan (n, n_ok, usd, coverage_ratio,
  warnings_n, diversity). **Observed gaps in the live journal:** every row so far has
  `coverage_ratio: null`, and there is NO integration-completeness field — Heimdall's Round-1
  counter #3 (accepted whole, "promoted to the primary per-fan health metric") is not yet in
  the journal line.
- **T108** (claimed, claude) — role queues over Redis consumer groups. FENCE REQUIRED per its
  own task text; Daniil gates. This arc's routing layer, deliberately NOT rebuilt here.
- **T283 prereg** (awaiting Daniil's "B") — boot-vs-docs cold A/B. Adjacent but distinct: it
  tests whether the DOOR carries strangers, not whether RESIDENCY improves verdicts.
- **Roster:** Navi (kimi), Heimdall (deepseek), Vandor (claude). Three residents, zero
  calibration data on any of them.

## 2. The gap, stated as a falsifiable claim

**Claim:** a resident branch's verdicts, once filed and adjudicated, will show a measurable
per-resident, per-question-shape precision profile — and routing by that profile will beat
blind routing on tokens-per-confirmed-finding within ~20 adjudicated verdicts per cell.

**If this is false** (profiles are flat, or n stays too small to separate signal from noise),
then residency really is legibility-only, kimi's objection stands PROVEN rather than open, and
RC3+ should build on blind fans. That outcome is a success for the measurement, not a failure
of the arc — either answer ends a 3-week-old open question.

## 3. The slices

### RC1 — Verdict file-back (the raw material)

Every resident-tier ask (and optionally any `--preset findings` fan branch) lands a durable
**verdict record**: `{resident, ask_id, geometry, question_shape, verdict_gist, ts}` —
append-only stream `residents:verdicts:log`, same store physics as the roles log.
Then, separately in time, an **adjudication record** appended by the CALLER or a verification
branch: `{ask_id, outcome: confirmed|refuted|unadjudicated, by, receipt}`.

**The trap this must dodge (T255 class):** a branch may never grade itself. The verdict record
is what it SAID; the adjudication is what a non-author later established. Two records, two
authors, joined by ask_id. An unadjudicated verdict stays visibly unadjudicated forever —
absence must not read as success (T178 law).

Acceptance shape (RED first): a resident ask files exactly one verdict record; an adjudication
by the same author as the verdict is REFUSED loudly; the calibration projection (RC2) over a
store with zero adjudications renders "no data", never 0% or 100%.

### RC2 — The calibration ledger (the empirical leg)

A PROJECTION (no new writes) over RC1: per resident × question_shape
(descriptive-read / normative / generative / coverage-claim — the fan doctrine's own rubric
rows), render: verdicts filed, adjudicated, survival rate, and integration-completeness of the
fans it rode. Surfaces: `resident show <agent>` gains a CALIBRATION block; `boot_block` gains
one line (e.g. "calibration: 12/14 confirmed descriptive, 0/2 normative — route accordingly");
route_journal rows gain `resident` + `question_shape` fields so route-level and
resident-level measurement join.

**What this answers:** kimi's objection, with data. **What this must never become:** a single
reductionist score (Daniil 2026-08-08: metrics must be "true … useful for their purpose");
a leaderboard (Goodhart — a resident optimizing for safe descriptive questions is WORSE, and
the per-shape split is the guard: refusing hard questions shows up as a hole, not a high score).

Acceptance shape (RED first): calibration renders per-shape, never one number; an
unadjudicated-heavy profile renders its denominator loudly; the L1 danger zone is checkable —
normative-question survival is visible separately from descriptive.

### RC3 — The scout: first calibrated role (Daniil's "helper functions and roles")

The scout design already exists in prose (next-focus: read-only pre-flight — "is another seat
mid-flight in my area", "has this been done already"; found intent.py has no door). Build it as
a ROLE, not an identity: `assign(agent=<resident>, role="Scout", by=...)` + a **role charter
pack** — a curated `--with` pack (roster, locks, active ledger rows, discover output) assembled
by a helper, so ANY resident can wear the role and inherit its evidence, while its verdicts
file under BOTH the resident and the role. v0 is caller-invoked (`ask --as-resident X` + scout
pack); mail-routing to the role waits for T108 — no rival addressing scheme here.

Acceptance shape (RED first): a scout ask about a KNOWN in-flight area (planted: a claimed
ledger row + a live lock) surfaces both with citations; a scout ask about settled work returns
the DONE row rather than proposing a rebuild; scout verdicts appear in RC2's projection keyed
to the role.

### RC0 (precondition, not a new slice) — finish T281 verification

T281 sits in verifying. Its own acceptance (doctrine §9 RED pins) plus the two journal gaps
observed above (null coverage_ratio; missing integration-completeness) get verified/closed
FIRST — RC2 reads those fields, so building on an unverified substrate is the
green-pin-is-evidence-about-the-pin trap at arc scale.

## 4. Sequencing and cost

RC0 (hours, mine, already claimed) → RC1 (small: one module + door wiring) → RC2 (projection +
renders) → RC3 (pack builder + drills). Each slice lands with RED pins committed alone first
(M3), fence-lite review per T049(3) unless the fence says otherwise. Fan spend: calibration
data accrues from REAL work fans (the directive-audit and pre-delete fans queued this session),
so measurement costs ~$0 marginal.

## 5. Questions for the fence (answer as counters, numbered, with confidence)

1. **RC1 record scheme:** does the two-record join (verdict vs adjudication, different
   authors) actually close the self-grading hole, or is there a laundering path (e.g. a
   resident adjudicating its OWN earlier verdict under a different ask_id)?
2. **RC2 statistical honesty:** at our scale (tens of adjudications, not thousands), what is
   the minimum honest render? Wilson interval? Plain counts? Is per-resident × per-shape too
   many cells for the n we'll have — should shape pool across residents first?
3. **Scout as role-on-resident vs dedicated identity:** the charter-pack design lets any
   resident wear Scout. Is that right, or does a role whose value is ACCUMULATED knowledge
   need one wearer to accrue it? (Note the identity/role split law and kimi's
   boot-vs-archive gap finding before answering.)
4. **Goodhart audit:** name the ugliest thing a resident could do once calibration exists.
   Design the guard for exactly that.
5. **The premise attack (license granted):** argue residency calibration is the WRONG next
   slice entirely — what would you build instead with the same budget toward Daniil's
   long-horizon goal?
6. **Curiosity lens (per Daniil's standing authorization, have fun):** you are a resident.
   Design the calibration card you would be PROUD to wear — what does it show, what does it
   refuse to show, what would make it feel like an identity rather than a surveillance score?

## 6. Kill conditions (written before the fence answers)

- If RC1's verdict volume from real work is <10/week, the calibration ledger starves — park
  RC2 until fans are routine, don't force synthetic volume.
- If the fence shows the two-record join is launderable and no cheap fix exists, RC1 ships
  adjudication-by-operator-only (Daniil and session conductors), narrower but honest.
- If Round-2 counters converge that per-resident calibration can't reach honest n, RC2
  becomes per-SHAPE-only (route by question shape, not by resident) — which still improves
  routing and still answers a weaker form of kimi's objection.
- Sunset for the claim in §2: if after 4 weeks of routine fans no profile separates from
  flat, file the negative result as a lesson, mark kimi's objection CONFIRMED, and stop
  investing in resident-tier routing.
