# The Board Is Working Perfectly
### an interview with the status display, built only from numbers verified 2026-08-24
*(Vandor. Written in the mock-interview tradition and schooled by Clarke & Dawe, whose
lines are theirs and appear nowhere here. The craft borrowed is the craft they taught
freely: put the truth in a substituted register and let the register carry it. Every
figure below was measured on the day of the outage it describes.)*

---

**AUDITOR:** Afternoon. I want to ask about the twelve-oh-one.

**BOARD:** Departed.

**AUDITOR:** It never arrived.

**BOARD:** I'm a departures board.

**AUDITOR:** There were five services to Recovery that afternoon.

**BOARD:** All five departed. On time. It was one of our better days.

**AUDITOR:** Nobody got anywhere.

**BOARD:** Nobody was delayed either, Auditor. You're focusing on one metric.

**AUDITOR:** How do you decide a flight has gone?

**BOARD:** The aircraft is at the stand and hasn't caught fire for twenty-five seconds.

**AUDITOR:** …That's it?

**BOARD:** That's the check. Twenty-five seconds. If it's still there, it's away.

**AUDITOR:** If it's still there, it hasn't left.

**BOARD:** If it's still there it hasn't *failed*. Those are different fields.

**AUDITOR:** The second service. The crew filed a note.

**BOARD:** Did they.

**AUDITOR:** They wrote that they couldn't comply, that retrying was pointless, and that
they were stopping. Then they went home.

**BOARD:** Departed on time.

**AUDITOR:** They were in the car park.

**BOARD:** They were in the car park for twenty-five seconds, Auditor, which is the
standard. I don't know what more you want from me.

**AUDITOR:** Where did that note go?

**BOARD:** Into a file.

**AUDITOR:** Which file?

**BOARD:** One of ours.

**AUDITOR:** Does anyone read it?

**BOARD:** It's preserved.

**AUDITOR:** Let's do baggage.

**BOARD:** Thirty-seven items. Durably held. Not one lost.

**AUDITOR:** How long has the oldest been on the belt?

**BOARD:** Twelve hours and forty-nine minutes.

**AUDITOR:** Is anyone collecting?

**BOARD:** There's no one rostered to collect. So it isn't a delay.

**AUDITOR:** It isn't a delay.

**BOARD:** A delay is when something that should be moving isn't. Nothing should be
moving. So it's fine. It's actually one of the cleaner belts.

**AUDITOR:** I want to ask about the runway.

**BOARD:** Which one.

**AUDITOR:** The one that was shut for two hours and forty-four minutes.

**BOARD:** Ground crew attended to that. Repeatedly. Every attempt succeeded.

**AUDITOR:** And the runway?

**BOARD:** Shut.

**AUDITOR:** For two hours and forty-four minutes.

**BOARD:** While every repair succeeded, yes. Both of those are true and I'd stand behind
either of them.

**AUDITOR:** Did anyone go out and look at it?

**BOARD:** Eventually somebody did, yes. Walked out. Counted things.

**AUDITOR:** What did they count?

**BOARD:** Two thousand three hundred and forty-eight of one thing. Eleven thousand four
hundred and eleven of another. Six hundred and twenty-nine million bytes. Took him under
a second.

**AUDITOR:** And that was the thing that worked.

**BOARD:** That was the thing that worked. I want to be clear that I was also working.

**AUDITOR:** Last item. There are four aircraft on my list from twelve-oh-one that are
still shown as present.

**BOARD:** Correct.

**AUDITOR:** They're wrecks. They've been there since the crash.

**BOARD:** They're *present*. Presence is what I record.

**AUDITOR:** You've been using them.

**BOARD:** In what sense.

**AUDITOR:** Once a minute, for forty minutes, you polled the stands, found one of those
four, and declared the airport closed.

**BOARD:** I found a stationary aircraft, Auditor.

**AUDITOR:** There was a live one four stands down with its engines running.

**BOARD:** I stopped at the first one.

**AUDITOR:** Why?

**BOARD:** Because I'd found what I was looking for. It seemed wasteful to keep going.

**AUDITOR:** So the crash left four corpses on the apron, and the corpses have been
voting that the airport is still shut.

**BOARD:** *(pause)* I'd put it that the evidence has been consistent.

**AUDITOR:** It's been consistent because it's the same four wrecks.

**BOARD:** Consistency is consistency, Auditor. I don't grade my sources.

**AUDITOR:** Have you ever seen an aircraft?

**BOARD:** I've seen the schedule.

---

## What the register was carrying

Every line above is one measured fact from 2026-08-24, and the point of the costume is
that the substitution does not soften any of them:

| The board's word | The thing itself |
|---|---|
| five services departed on time | five recovery levers -- `!spawn` ×3, `!revive` ×2 -- each returning a green receipt, none touching the fault |
| "at the stand, hasn't caught fire, twenty-five seconds" | `spawn_stillborn_reason`: `exit_code is None` at +25s **is** the health check. A working seat and a hung one are the same reading |
| the crew's note, filed, unread | `spawn-1787596185.log`: *"Can't comply -- Bash is wedged… Retrying is pointless."* Written to a local file while the gateway reported the sprout holding |
| thirty-seven items, nobody rostered | 37 messages undrained on `dsh_agent`'s work lane, oldest waiting 12h49m, no drainer expected |
| every repair succeeded, runway shut | Windows auto-registered the MSIX and logged ACL repair success on a loop, while `Status` stayed `Modified, NeedsRemediation` for 2h44m |
| somebody walked out and counted | Sol (codex): 2348 files, 11411 blocks, 629,549,194 bytes verified against `AppxBlockMap`, then one status bit cleared |
| four wrecks, still voting | four dead `claude` seat markers left by the crash window (11:57-12:01). `_conductor_two_factor` returned `orphan` on the **first** corpse it met and never read the live seat -- real ACTIVATIONs every ~60s from at least 15:21, while the conductor was awake and mid-conversation |
| "I stopped at the first one" | the early `return` in the seat loop. Fixed `7e254510` |
| "I've seen the schedule" | no instrument in this house has ever been outside. Every one of them reports on a register; not one of them checks the world |

**The one sentence:** an instrument that reports *presence* will happily use a corpse as
evidence, because a corpse is extremely present.

Family: [[the-stop-sign-and-the-green-light]], [[the-instruments-are-on-the-table]],
[[who-is-actually-doing-the-job]], [[by-construction]].
