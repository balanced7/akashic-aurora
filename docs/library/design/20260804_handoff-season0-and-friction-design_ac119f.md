---
akashic_id: art_20260804_handoff-season0-and-friction-design_ac119f
akashic_sha: 6f257e2f229d
schema_version: 1
status: current
type: design
date: 2026-08-04
title: handoff-season0-and-friction-design
gist: "# HANDOFF — Season 0, the fire drill, and the friction-record design **Written 2026-08-04 by claude#cdfb9126 for a fresh, unconstrained Opus"
visibility: fleet
body_type: markdown
seats: []
category: [memory, bus, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-04T22:56:54"
updated: "2026-08-04T22:56:54"
---
<!-- GENERATED PROJECTION of art_20260804_handoff-season0-and-friction-design_ac119f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# handoff-season0-and-friction-design

# HANDOFF — Season 0, the fire drill, and the friction-record design

**Written 2026-08-04 by claude#cdfb9126 for a fresh, unconstrained Opus seat, at Daniil's ask.**
Everything named here is committed and pushed to origin/master unless marked otherwise.

Read this file, then `py agent_cli.py boot claude`. The note `where-we-are` points here.

---

## 1. WHAT LANDED (all pinned, all pushed)

Season 0 — the load lab. Built because a five-seat round could not be supervised.

| T | what | commit |
|---|---|---|
| T147 | runner seats publish the per-incarnation beat the roster reads | `4abc886` |
| T149 | `bifrost-send` stdout stops claiming a send that did not happen | `fb7bf75` |
| T150 | runners line-buffered + UTF-8 → logs readable while running | `ebae239` |
| T151 | grant expiry is a visible deadline, not a trapdoor | `f11a6ab` |
| T167 | **the wake-listener autopilot, which had never worked** | `d1c933f` |
| T169 | budget exhaustion returns a marked partial answer, not `""` | `40aee38` |
| T170 | `BoundaryOutcome` — silence unrepresentable at a boundary | `00517bb` |

Earlier the same day (separate arc): T134/T134b/T134c function-level wiring gate, T142
`check_advertised_tools`, T143/T144/T145/T146 gate hardening, T138/T139 ledger receipt path.

**Do not redo any of these.** Pins live in `tests/test_t1*.py`, one file per T.

---

## 2. THE SINGLE MOST IMPORTANT FINDING

**T167: the wake-listener autopilot had never worked.**

```
bifrost_daemon.py:140   def _spawn_listener(sid: str) -> bool:      # ONE argument
bifrost_daemon.py:386   lambda sid: _spawn_listener(sid, bus.ns)    # TWO arguments
```

Every `.rearm` raised `TypeError`; `consume_rearms` swallowed it (`except Exception: ok = False`)
and left the trigger "for the next tick" forever. A daemon running `--manage-listener` spawned
**nothing**, silently, for weeks.

Found by **dropping a real trigger**, not by reading code. My reasoning had concluded "no listener
is correct — none was requested." The drill showed the request had been made six times and refused
silently every tick. After the fix, one restart spawned six listeners, including for session
`7507b107` — the seat Daniil was actively talking to. **Nobody in the fleet was wakeable.**

---

## 3. THE DESIGN THINKING THAT IS NOT YET WRITTEN DOWN

This is the part that would be lost. Daniil asked for a shared space that auto-files pain points
for cross-learning. I proposed `friction` as a first-class record type. **Three refinements follow,
and the third changes the design.**

### 3a. Do NOT add a sixth record type — count what exists first

`agent_cli.py` already exposes ~70 verbs, including **learn, wish, note, task, blocker, bench,
toast, defer, followup, tag-anti-pattern**. Several already mean "something is wrong / worth
remembering." Adding a sixth cuts directly against the stated goal of *reducing* ambiguity.

**Do this first:** census those record types, find their real distinctions (retention? audience?
who acts?), and decide whether `friction` is a NEW type or a FACET of an existing one. My instinct
after a night in this code: it is a facet, and the genuine gap is that none of them carry a
*machine-generated* origin.

### 3b. Auto-file without auto-retire recreates the mess we just cleaned

Four HARD WEDGE pages fired tonight for seats whose pids I had killed 13 minutes earlier —
**verified dead, pages still firing.** Records that cannot retire themselves become the 20-stale-
proposals problem I spent the morning clearing out of the ledger.

So a friction record needs a **self-retiring predicate** from birth: the same property
`check_wiring`'s stale-baseline detection has, where an entry that becomes wired reports itself as
stale. Write the retirement condition when the record is created, or do not create it.

### 3c. **FREQUENCY RANKING IS BLIND TO THE MOST DANGEROUS CLASS — this is the big one**

I proposed ranking friction by count. That is wrong, and tonight proves it:

- `mail declare skipped` logged **109 times** across three seats. Noisy, and mostly one benign cause.
- **T167 — the worst defect of the night — produced ZERO log lines.** Silence was the entire bug.

A frequency-ranked friction list would have put the harmless thing first and **would never have
contained T167 at all.** Auto-filing can only capture friction that *reported*. The expensive class
does not report — that is what makes it expensive.

**Therefore the design needs two sources, not one:**

1. **Reported failure** — a non-ok `BoundaryOutcome` files itself. Catches loud friction.
2. **Unreported silence** — an *expectation* that was armed and never settled. Catches the silent
   class. `RB-29` expectations already exist and already redrive; nothing currently reports
   "armed, never answered" as a first-class fact.

Source 2 is the more valuable half and the one nobody has built. **Rank by blast radius (seats
affected × work blocked), never by count alone.**

---

## 4. LIVE STATE / TRAPS

- **Stale pages**: 4 HARD WEDGE pages for dead pids (34840, 46508, 52124, 41300). Ignore them; they
  are 3b's evidence, not live incidents.
- **`codex_root` grant lapses `2026-08-05T12:00:00Z`.** `py agent_cli.py doctor` renders the
  countdown (T151). Renewal is an edit; after lapse it is a resurrection. **Needs Daniil's call.**
- **Roster: ~52 DEAD rows to 3 LIVE.** A regression *I* introduced with T147 — pid-first sid8 means
  every restart mints a new seat identity leaving a 24h witness. Needs a collapse rule. This is the
  top Season 1 blocker because the roster is the reaper's only sensor.
- **T168 filed, not fixed**: the daemon refuses a relaunch while the dead predecessor's lock is warm
  and **exits 0** — the friction `acquire_waiting` removed for runners, never applied to the daemon.
- **T047 still `approved`, never started.** Retiring the legacy stream removes the whole
  lane/cursor/mis-delivery class. Argued for promotion three times now.

---

## 5. METHOD THAT ACTUALLY WORKED (use it)

- **Probe, don't reason.** Every design conclusion I reached by reading code was wrong tonight
  (W124 and W125 were both misdiagnoses I had to publicly correct). Every real event I fired gave
  the answer in minutes. Fire the event; record what it SAID vs what it DID; the gap is the defect.
- **Calibrate every instrument on known-outcome controls before trusting it.** Five of my own
  instruments cried wolf on first run (277→44 orphans, 12 false citation accusations, 6 wrong
  "dead" functions, 5 wrong doc lies, a scorer that reported 4/4 wins while the gate had crashed).
- **Mint the ledger id BEFORE writing the file.** I caused two id collisions in one day by reading
  the list instead of asking the registry — the exact thing my own lesson forbids.
- **Pins RED, alone, committed before the fix.** M3 pre-registration went 0% → 40% by doing this.
- **A structural pin can only check what is greppable**, so write the code where the pin can read
  it (T150's loop-vs-explicit lesson).

---

## 6. WHAT I WOULD DO NEXT, IN ORDER

1. **3a census** — settle whether `friction` is a new type or a facet. Cheap, prevents a sixth dialect.
2. **Source 2 (unreported silence)** from §3c — armed-but-never-settled expectations as a
   first-class fact. Highest value, nobody has built it.
3. **Roster corpse collapse** — my regression, top Season 1 blocker.
4. **Migrate boundaries to `BoundaryOutcome`** incrementally; `__bool__` makes every call site
   backward-compatible (pinned as O7 in `tests/test_t170_outcome_cannot_be_silent.py`).
5. **T047**, whenever Daniil rules on it.

Hold Season 1 until 2 and 3 are green. Twenty seats that investigate deeply and return nothing is a
more expensive failure than five.
