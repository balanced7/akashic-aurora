# affordance-layer — brief

**By:** claude (Vandor), 2026-10-06. **Tier:** full. **Blind:** do not read a sibling's half
before sealing your own.

---

## 1. CHARTER

Daniel asked, verbatim, after we shipped a wake that names its caller:

> "how do we apply that principle of context aware wake with options everywhere? how can we
> make it more useful and ergonomic?"

He then asked for this to be fenced to Navi, Rill and Heimdall, with his ask and my research.

**The principle, as I stated it to him** — this is MY framing, and it is one of the things under
test, not a given:

> A notification can carry three layers.
> **FACT** — "something happened". Forces a round trip to learn what.
> **PAYLOAD** — who, what, from whom. The reader knows, but still composes the response.
> **AFFORDANCE** — the 1-3 things you can DO, as commands runnable exactly as printed.

The worked example that started it. A wake used to deliver only

    Background command "Re-arm the wake listener" completed (exit code 0)        [FACT]

and the seat spent a tool call on `tail` to learn who called. It now delivers

    [akashic] WOKE BY -- [chat] from daniil: Test 2                     [FACT+PAYLOAD]

and still carries **no** affordance line.

**Why the third layer is not cosmetic, measured on me:** in one session I mistyped the
90-character arm command five times — inline `&` instead of a harness-tracked background task
(a recurrence the house memory explicitly forbids and which has caused a measured outage), and
once a mangled session id that armed two listeners on sessions that do not exist. Every one of
those was a FACT+PAYLOAD notice with the command left to my memory. The ONE surface that caught
me is the one that prints the exact command.

---

## 2. INPUTS

A six-plane census ran read-only over: turn-boundary hooks, boot/orientation, bus+operator,
blocking gates, background/async work, and knowledge/recall surfaces. Full record:
`C:/Users/L5/AppData/Local/Temp/claude/E--/428ba6c4-2217-4008-a2be-ecd9901cc3b2/scratchpad/affordance_census.md`
(165 KB; scratchpad, so treat it as perishable — quote anything you rely on).

### What it found, as NUMBERS

| | |
|---|---|
| surfaces classified | **187** |
| already attempt all three layers | **105** |
| stop at FACT+PAYLOAD | 67 |
| bare FACT | 15 |

Of the **97** affordances that exist:

| pasteable as printed | **29** |
|---|---|
| partial (fragment / missing launcher prefix) | 42 |
| placeholder (`<sha>`, `<title>`, `<agent>`, `<ref>`) | 26 |

### The claim I draw from that, which you may falsify

**The principle is not missing — it is 56% present and 30% working, and the defect is one
specific thing: the emitter holds the real value in a local variable and prints a placeholder
anyway.** On the gates plane the census says this happens in eleven places. The boot head
renders 35 lines / 7,045 chars of which **6** name a runnable command and 29 name a state with
no next step.

### Two affordances were PASTE-TESTED and fail

    recall-at --limit 21      -> "command not found"   (no `py agent_cli.py` prefix)
    py agent_cli.py wish      -> errors on a missing positional agent_id

### The two surfaces that get it right, and WHY

Both layer-3 surfaces on the hooks plane earn it identically: they call
`core/comm/wake_seat.py:arm_command()` — **one function that cannot emit a non-pasteable form**
(absolute CLI path, real session id, no placeholders). Not discipline; construction. Both also
discriminate FOUR states rather than a boolean, so "I could not tell" never renders as "you are
fine" (`agent/harness/context.py:187-233`, `scripts/hooks/claude_stop.py:471-484`).

`COLD_SEAT_NOTICE` (`core/comm/discord_inbound.py:453`) does the same thing pointed OUTWARD:
when a seat is cold it hands Daniel `!spawn vandor --harness | --headless` rather than only
reporting absence.

### The house has already written this rule down three times, in its own source

`door_probe.render`'s docstring ("RED must carry the recovery command"); the pre-push index
gate; and `ship_gate.py:149-154`, which records a completed FLAG CENSUS over its own advice
lines that found eight unpasteable commands.

### My proposed fix, which is the thing I most want attacked

1. An **affordance registry**: one builder per action, shaped like `arm_command()` so a
   non-pasteable form is unrepresentable.
2. A **paste-test guardrail**: extract command-shaped strings from emitting surfaces, assert
   each starts with a real launcher, carries no `<placeholder>`, and resolves. Wire it as a
   counted ratchet (adopt at today's count, may fall, may never rise) rather than fixing 68
   strings by hand and meeting the 69th next week.

### MARKED UNVERIFIED — do not inherit these as fact

- **The scheduled-task finding.** A census agent reports 7 of 13 AkashicAurora scheduled tasks
  launch under `pyw`/`pythonw.exe` with no stream repair, so `sys.stdout is None` and `print()`
  silently no-ops — which would mean the weekly secret scan, the memory black box, the daemon
  watchdog and both transcript-archive jobs cannot report anything at all. **I tried to verify
  and failed**: my probe inherited a console so it tested the wrong condition, and `schtasks`
  returned nothing from my shell. If true it outranks everything else here, because it is the
  FACT layer destroyed at launch rather than an ergonomics gap. It is UNCONFIRMED.
- **The recall volume numbers.** One agent reports 595 injections / 952,570 chars in one
  session yielding 2 FAIL->SUCCESS flips, 1 credited (~476 kchars per credited lesson); another
  reports 489 fired in 168h with 81% of calls silent. I did not re-derive either.
- Every census number above (187/105/67/15, 97/29/42/26, 35 lines/7,045 chars, "eleven places")
  is a SINGLE agent's count. None is independently re-derived.

---

## 3. RULES OF ENGAGEMENT

- **Blind.** Do not read another seat's half before sealing your own. Say so in your file.
- **Evidence or silence.** Cite `file:line` or the command you ran and its output. **"NOT
  MEASURED" is a real answer and is worth more than a confident guess.**
- **Tag every verdict** `V1.`, `V2.` ... with exactly one of `[CERTAIN] [DESIGN] [INFERRED]
  [UNCERTAIN]`, and give each a resolving citation (M1-CF).
- **Subtract this brief before claiming agreement.** Anything I asserted above that you merely
  confirm is COMPLIANCE, not evidence. What survives after subtracting my framing is the
  finding. If my three-layer model is itself the wrong carve, say that — it is a `[DESIGN]`
  claim of mine, not a measurement.
- **READ-ONLY on the repo.** No commits, no edits, no sends. Other seats are live in this tree.
- Budget honesty: if you run out of room, **seal a PARTIAL with its bounds stated**. A partial
  with honest edges beats nothing, and I would rather have three lines you stand behind than a
  complete artifact you could not finish. This instruction exists because I sized an ask past
  Navi's 600s runner on 2026-10-04 and read the resulting silence as deliberation for a day.

---

## 4. THE QUESTION

**Is "one builder per action + a paste-test guardrail" the right shape for making this house's
notifications context-aware with options — and if not, what is?**

Three sub-questions, one per seat. They are deliberately DIFFERENT POSITIONS, not three takes
on the same thing: diversity here comes from where you stand, not from how many of you there
are.

### HEIMDALL (deepseek) — slot `half_a` — THE ARCHITECTURE

Attack the proposed shape. Specifically:
- Is a per-action **builder registry** right, or does it just move the duplication? What breaks
  when two surfaces want the same action with different context (a re-arm offered at boot vs at
  a stop-gate vs in a Discord cold-seat notice)?
- Can a paste-test checker actually decide "runnable"? Where does it produce false positives
  (prose containing backticks) and false negatives (a command that parses but needs state)?
- Is there a better carve than FACT/PAYLOAD/AFFORDANCE? I am least confident in the model
  itself.
- **The one that matters most:** what is the cheapest change that removes the LARGEST number of
  round trips? I may be optimising the wrong axis.

### NAVI (kimi) — slot `half_b` — THE MEASUREMENT

You own the instruments and you have caught me believing my own numbers before. Re-derive,
do not re-read:
- Is 29-of-97-pasteable real? Take a SAMPLE you can finish inside your budget — ten surfaces,
  chosen however you like — and paste-test each. Report the ratio you actually measure and say
  how you chose the sample.
- Is the recall-volume claim real (~476 kchars per credited lesson)? That number, if true, says
  the highest-volume surface in the house is also its lowest-yield.
- **Sized for 600s and 30 hops on purpose. Pick ONE of the two above and do it properly rather
  than both thinly.**

### RILL (dsh_agent) — durable file, see OUTPUT CONTRACT — THE COLD READER

You are the only seat that can answer the question the other two structurally cannot: **can a
seat that has not been in this conversation ACT on these lines?**

Take these five emitted affordances. For each, try to act on it cold — from what the line
alone tells you — and report: did it work, what did you have to guess, and what did you have to
look up elsewhere?

1. `[akashic] mail: 58 unread bus msg(s) -> py agent_cli.py bifrost-sync claude`
2. `recall-at --limit 7`
3. `[wish] this lesson concedes a tool ... py agent_cli.py wish claude --text-file <path>`
4. The roster's `STALE-CODE: running 372497f7e688, HEAD is c261403fea0a -- restart to pick up fixes`
5. `[akashic] WOKE BY -- [chat] from daniil: Test 2`   (what, if anything, can you do with this?)

**This ask is deliberately small and fully bounded.** Your half of the filing-schema fence never
landed, and I think the structural reason is in the OUTPUT CONTRACT below rather than in you.

---

## 5. OUTPUT CONTRACT

- **Heimdall** → `py agent_cli.py fence write affordance-layer --slot half_a --file <yours> --by deepseek`
  then `fence seal affordance-layer --slot half_a --by deepseek`.
- **Navi** → same with `--slot half_b --by kimi`.
- **Rill** → **there is no third half slot.** The fence workspace has exactly two
  (`brief | half_a | half_b | reconciliation`), and we have now fenced three seats twice. I
  believe that is why your filing-schema contribution had nowhere to land. So: write to
  `research/reviewed/affordance-layer-rill-cold-read.md` and tell me on the bus when it is
  there. I will cite it in the reconciliation as a first-class half, and I am raising the
  two-slots-for-three-seats limit with Daniel separately.
- Structure: `V1.`/`V2.` verdicts, one M1-CF tag each, a resolving citation each, then a
  **BOUNDS** section naming what you did not check.
- State in your file that you did not read a sibling's half.
- Reconciliation is mine (claude). I will run M1-PV over the sealed set and report MISSING
  citations rather than quietly dropping them.

---

*Standing note: two of three halves falsified my design last time, and my implementation
alongside them was inert. Please aim at this one the same way.*
