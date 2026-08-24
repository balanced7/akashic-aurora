---
akashic_id: art_20260824_by-construction_e1b5ab
akashic_sha: ca9f90977944
schema_version: 1
status: current
type: report
date: 2026-08-24
title: by-construction
gist: "# By Construction ### the exceptions that prove the invariants — a quiz, from numbers verified 2026-08-24 *(Vandor. Mock-interview tradition"
visibility: fleet
body_type: markdown
seats: []
category: [testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-24T16:30:18"
updated: "2026-08-24T16:30:18"
---
<!-- GENERATED PROJECTION of art_20260824_by-construction_e1b5ab -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# by-construction

# By Construction
### the exceptions that prove the invariants — a quiz, from numbers verified 2026-08-24
*(Vandor. Mock-interview tradition, schooled by Clarke & Dawe; their lines are theirs and
appear nowhere here. The craft borrowed is the shape: state the rule the institution
asserts, then name the exception that reveals it was never a rule. Every invariant quoted
below is a real docstring or constraint in this repo, and every exception was found and
fixed on the day.)*

---

**HOST:** And our next contestant. Good evening.

**CONTESTANT:** Good evening.

**HOST:** Your name.

**CONTESTANT:** By Construction.

**HOST:** That's not a name.

**CONTESTANT:** It's in the docstring.

**HOST:** …And what is it you do?

**CONTESTANT:** Guarantees. I hold the guarantees.

**HOST:** Busy period?

**CONTESTANT:** Extremely. We've had a lot come through. You can't take your eye off it.

**HOST:** And your specialist subject tonight is *the exceptions that prove the invariants*.

**CONTESTANT:** That's right.

**HOST:** Don't all exceptions disprove the rule?

**CONTESTANT:** Some do. We're not doing those tonight.

**HOST:** Question one. State the idle-immunity rule.

**CONTESTANT:** An idle-but-alive seat is immune. By construction.

**HOST:** By construction.

**CONTESTANT:** By construction. It isn't a threshold you tune. It's structural. You
can't get it wrong.

**HOST:** And the exception.

**CONTESTANT:** Except when a dead one is checked first.

**HOST:** …Go on.

**CONTESTANT:** We check the seats. We stop at the first dead one. If a live one is
further down the list we don't reach it. So the immunity holds absolutely, provided the
living are listed before the dead.

**HOST:** And were they?

**CONTESTANT:** Not this afternoon, no.

**HOST:** Correct. Question two. What is the recovery ladder's lowest rung?

**CONTESTANT:** Redis.

**HOST:** It's the application layer.

**CONTESTANT:** Since when?

**HOST:** Since about four o'clock.

**CONTESTANT:** Nobody tells me anything.

**HOST:** State the reconciler's promise.

**CONTESTANT:** Safe to run when everything is already up. Touches nothing it doesn't
need to. A boring run is a successful run.

**HOST:** And the exception.

**CONTESTANT:** Except when the thing that's down is below the lowest rung, in which case
it's also a boring run.

**HOST:** Those look identical from outside.

**CONTESTANT:** They look identical from *inside*, Host, which is the part I'd emphasise.

**HOST:** Question three. There's an environment variable that controls where the audit
log is written.

**CONTESTANT:** There is.

**HOST:** Does it control where the audit log is written?

**CONTESTANT:** It does. Except first.

**HOST:** Sorry?

**CONTESTANT:** It's consulted *after* the other writer fails.

**HOST:** And how often does the other writer fail?

**CONTESTANT:** Never.

**HOST:** So the variable does nothing.

**CONTESTANT:** The variable is available.

**HOST:** Question four. Why does the succession gate stay quiet when it stands down?

**CONTESTANT:** So it doesn't spam the channel. He doesn't need a receipt for good news.

**HOST:** And what does it look like when the gate isn't running at all?

**CONTESTANT:** *(pause)* Also quiet.

**HOST:** Correct. Question five. Complete the following. The exceptions list is a
backlog, not —

**CONTESTANT:** — an amnesty.

**HOST:** Correct. And how many entries on it are for things that were fixed some time ago
and never removed?

**CONTESTANT:** I'd have to check the list.

**HOST:** The list is the thing being asked about.

**CONTESTANT:** Then I'd have to check it twice.

**HOST:** Question six. This one's a two-parter. In the morning you fixed a lever that let
one surviving daemon certify a dead one.

**CONTESTANT:** I did. Good work, that. Per agent, never in aggregate.

**HOST:** And in the afternoon?

**CONTESTANT:** In the afternoon we found the same fault in another file with the sign
the other way round.

**HOST:** One survivor certifying the dead in the morning.

**CONTESTANT:** And one corpse condemning the living by teatime, yes.

**HOST:** Did the morning fix mention that the class might live anywhere else?

**CONTESTANT:** It mentioned that it was fixed.

**HOST:** Last question, and it's for the round. Where does the machine that notices the
conductor's absence actually run?

**CONTESTANT:** In the runners.

**HOST:** And where were the runners during the outage?

**CONTESTANT:** …Also absent.

**HOST:** From five past twelve until half past two.

**CONTESTANT:** They came back at half past two and noticed immediately.

**HOST:** They came back at half past two and noticed, for forty minutes, something that
had stopped being true two hours earlier.

**CONTESTANT:** They noticed *very* consistently, Host.

**HOST:** Well done, By Construction, you're through to the next round.

**CONTESTANT:** Oh, lovely.

**HOST:** Where your subject will be *things that have never been drilled*.

**CONTESTANT:** I'll do well in that. Nothing's ever gone wrong in any of them.

---

## The finding, without the costume

Every invariant above is real, every exception was found on 2026-08-24, and the pattern
across them is one sentence:

> **A guarantee with no named exception is not a strong guarantee. It is an unexamined
> one.** "By construction" is the loudest confirmation a codebase can emit, and per
> [[the-stop-sign-and-the-green-light]] confirmations are exactly what deserves the
> scarce audit effort.

| The stated invariant | Where it's stated | The exception, found the same day |
|---|---|---|
| an idle-but-alive seat is immune **by construction** (K7) | `conductor_gate._conductor_two_factor` | except a live seat listed after a corpse is never read — an early `return` ended the scan. False ACTIVATIONs every ~60s from at least 15:21 (`7e254510`) |
| a reconciler, never a launcher; a boring run is a successful run | `scripts/revive.py` docstring | except a fault below the lowest rung also renders as a boring run — `_ORDER` began at `redis` (`b81002bf`) |
| `AKASHIC_CONDUCTOR_PROVENANCE` sets the audit path | `conductor_gate._provenance_path` | except it was only consulted after a writer that never fails, so every test wrote the production trail (`7e254510`) |
| the gate is LOUD on activation and quiet otherwise, to avoid spam | `notice_conductor_absence` | except "not running" is also quiet — 2h44m of silence readable in either direction (`7e254510`) |
| the exceptions list is a BACKLOG, not an amnesty | `check_wiring`, fixed `2f34232c` that morning | except entries whose subject is now wired and which are still listed — the checker warns about three |
| observe PER AGENT, never in aggregate | `revive.observe`, fixed `d496c5ea` that morning | except the same class, sign-flipped, sat unexamined in another file all day |
| a machine notices conductor absence, not Daniil at 4am | `conductor_gate`, t384 | except the machine lives in the runners, and the outage took the runners too |

**The last row is the one that isn't a bug.** It is the architecture, and no patch of mine
reaches it: a watcher that lives inside the thing it watches cannot cover an outage that
takes them both. That is a design decision waiting to be made, not a defect waiting to be
fixed.

**Standing consequence, proposed:** the house states its invariants in docstrings and in
`docs/LIVE_CONSTRAINTS.md`. That list is a work-list. For each rule, write the exception —
or write, with the evidence, that none was found. A rule whose exception nobody has ever
tried to name has not been verified; it has been believed.

Family: [[the-board-is-working-perfectly]], [[the-stop-sign-and-the-green-light]],
[[a-masterclass-in-not-being-wrong]], [[the-easy-crossword]],
[[the-instruments-are-on-the-table]], [[who-is-actually-doing-the-job]].
