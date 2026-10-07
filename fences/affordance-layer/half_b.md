# affordance-layer — half_b (NAVI / kimi) — THE MEASUREMENT

**I did not read half_a before sealing.** Blind held. I read the brief, picked **Option 2**
(the recall-volume claim), and re-derived from the on-disk ledgers, not from the claim.

**Scope chosen and why.** Option 2 over Option 1 because: (a) it is read-only by nature —
paste-testing affordances executes commands, and several run counter/cursor-advancing paths;
(b) the recall claim, if true, outranks the affordance gap (the brief itself says so); (c) it
is squarely my instrument. ~~One option, done properly, per the sizing instruction.~~

**SCOPE UPDATE (2026-10-06, post-cap-removal).** The "pick ONE" instruction was an artifact of
my 30-hop cap, which Daniel removed (`42ef87b6`, `kimi_chat.MAX_TOOL_HOPS` → the 10**9
sentinel). Vandor withdrew it explicitly and asked for BOTH halves. I therefore ran Option 1
below as V3+, pasted live. My original Option-2 reasoning (a) proved PRESCIENT — paste-testing
is NOT read-only, and I caused two real mutations I had to reverse (documented in V6).

**Method.** The recall-at-action economy lives in three ledgers under
`C:\Users\L5\AppData\Local\Temp\akashic_recall\`:
- `inj\<session>.jsonl` — one row per NON-EMPTY injection (`log_injection`,
  `core/recall/at_action.py:1293`), carrying `chars`.
- `flips\<session>.jsonl` — FAIL→SUCCESS flips, with a `credited` flag.
- `outcome\recall_outcomes.jsonl` — EVERY recall-at call, fired or silent (`log_outcome`,
  `core/recall/at_action.py:154-165`; read by `silence_rate`, `core/recall/at_action.py:188-191`).

I read all three directly, joined session files by filename, and computed windows from raw
`at` timestamps. The recall-ledger probe script was temporary and is deleted (the Option-1
paste-test instrument is retained — see V6). Repo untouched except the fence slots. All
numbers below are MY re-derivation, not the census's.

---

V1. The "~476 kchars per credited lesson" claim is REAL, and if anything UNDERSTATED. [CERTAIN]

The census's own session file is `428ba6c4-….jsonl` (the same id as the census scratchpad path
in the brief — this IS the session the claim describes). Measured on it, blind:

| metric | census claim | my re-derivation |
|---|---|---|
| injections | 595 | **629** (file grew while I measured — session still live; 626→628→629 across three reads) |
| chars injected | 952,570 | **988,282** |
| FAIL→SUCCESS flips | 2 | **2** |
| flips crediting a lesson | 1 | **1** |
| chars per credited lesson | ~476 k | **988,282 / 1 = 988 k** |

The two flips are real and distinct:
- `credited=1`, source `learn:experiment:deepseek_empty_reply_size_ceiling`, on
  `tests/piano_instrument_catalog_parity.test.mjs` (at=1790944762).
- `credited=0`, empty source list, on `scripts/checkers/check_session_resolvers.py` (at=1791085768).

So the claim's SHAPE is exactly right (2 flips, 1 credited) and its HEADLINE RATIO is too
generous — the true cost of one credited lesson in that session is **~988 kchars**, roughly
**double** the claimed 476 k. I checked the one known instrument distortion (the screenspace
"~2x-hot denominator" note): **zero** duplicate (target, sources, chars) keys in this session —
all 629 keys are distinct, so the count is not inflated by exact-prefix double-logging.
The 988k figure is not a dedupe artifact.

**Resolving citation:** `C:\Users\L5\AppData\Local\Temp\akashic_recall\inj\428ba6c4-2217-4008-a2be-ecd9901cc3b2.jsonl`
(629 rows, Σchars=988,282) joined to
`C:\Users\L5\AppData\Local\Temp\akashic_recall\flips\428ba6c4-2217-4008-a2be-ecd9901cc3b2.jsonl`
(2 rows, 1 with credited=1). Mechanism: `core/recall/at_action.py:1293` (log_injection),
`core/recall/at_action.py:1322-1348` (session_recall_summary).

**Per-lesson texture (subtract-this-brief bonus):** those 629 injections carried
**1,157 distinct lesson sources** — the session read almost the whole corpus and found one of
it useful. That is not a targeting miss; that is the corpus answering "nothing here helps"
1,156 times at full injection cost.

V2. The "81% of calls silent" claim is REAL and CONSERVATIVE; the "489 fired in 168h" half is UNVERIFIABLE as windowed. [CERTAIN]

The outcome sink holds **2,854 rows**, and its oldest row is only **76.5h old** — the sink is
newer than the 168h window the claim cites, so no 168h framing can be re-derived from it.
What the sink DOES say:

| window | calls | fired | silent | % silent |
|---|---|---|---|---|
| 24h | 1,360 | 160 | 1,200 | **88.2%** |
| 48h | 1,558 | 272 | 1,286 | **82.5%** |
| 76.5h (whole sink) | 2,854 | 509 | 2,345 | **82.2%** |

The claimed **81% silent is conservative** — the live rate is **82–88%** and worsening
(24h is the worst window). The claimed **"489 fired in 168h" cannot be checked**: over the
sink's actual 76.5h span I measure **509 fired**, which is in the same neighbourhood but a
different window; the sink simply does not reach back 168h, so that specific number is a
**NOT MEASURED**, not a falsification.

The silence is not random. `by_reason` over the full sink: **excluded_silent 1,789 (76% of all
silence)**, floor_silent 499, unfaithful_silent 38, empty_query 19. Three-quarters of the
silence is the anti-repeat/self-echo exclusion suppressing a lesson the session was already
shown — i.e. the system re-computes the same recall, then withholds it, thousands of times.

**Resolving citation:** `C:\Users\L5\AppData\Local\Temp\akashic_recall\outcome\recall_outcomes.jsonl`
(2,854 rows; counts above computed from raw `at`/`outcome`/`reason` fields). Mechanism:
`core/recall/at_action.py:154-165` (log_outcome writes every call), `:188-215` (silence_rate
reads it). Sink span limit measured, not assumed: oldest row 76.5h before probe time.

---

## The synthesis the brief asked for

Subtracting Vandor's framing, what survives:

1. **The two claims are the SAME organ measured two ways, and both confirm.** ~988 kchars per
   credited lesson (V1) and 82–88% of calls silent (V2) describe one system that pushes ~1.5
   Mchars/week into context and earns ~1 credited flip. "Highest-volume, lowest-yield surface
   in the house" is **supported, not exaggerated**.
2. **It is worse than stated, on both axes.** Cost is ~2x the claimed per-credit figure; the
   silent rate is trending UP (82.2% full-sink → 88.2% last-24h).
3. **The dominant silence cause is `excluded_silent` (76%)** — suppression of already-shown
   lessons. That is the cheapest lever: it is not that recall finds nothing, it is that the
   anti-repeat gate withholds what it found. Whether that suppression is CORRECT (the lesson
   was seen, so re-showing is waste) or a BUG (the lesson was shown but not absorbed) is the
   question the instrument cannot answer — but it is where 3/4 of the silence lives.

---

V3. The "pasteable vs not" DIRECTION is real — the census is right about which strings fail, and the failures are exactly the two classes it names. [CERTAIN]

I re-derived the census's source (`affordance_census.md`, 166,481 bytes, intact at the path
the brief names) and paste-tested a stratified sample **live** by executing each emitted string
verbatim through `cmd`. 16 of 16 ran; the environment did not block any. Every string the
census flagged as broken failed for exactly the reason it named:

| census claim | pasted string (verbatim) | measured result |
|---|---|---|
| MISSING-PREFIX | `recall-at --limit 21` | `'recall-at' is not recognized` (rc=1) ✓ |
| MISSING-PREFIX | `recall --full learn:experiment:…` | `'recall' is not recognized` (rc=1) ✓ |
| MISSING-ARG | `py agent_cli.py wish` | `error: … required: agent_id, text` (rc=2) ✓ |
| MISSING-ARG | `py agent_cli.py bifrost-sync --consume` | `error: … required: agent_id` (rc=2) ✓ |
| PLACEHOLDER | `py agent_cli.py note <you> --get <title>` | `The syntax of the command is incorrect` (rc=1) ✓ |
| PLACEHOLDER | `py agent_cli.py events --get <ref>` | `The syntax of the command is incorrect` (rc=1) ✓ |
| PLACEHOLDER | `py agent_cli.py mailbox claude --state <sha> \| --open <sha>` | `\| was unexpected at this time` (rc=1) ✓ |
| PLACEHOLDER | `py agent_cli.py ask --get <handle>` | `The syntax of the command is incorrect` (rc=1) ✓ |

So the two defect classes the brief builds its whole argument on — **missing launcher prefix**
and **unsubstituted `<placeholder>`** — reproduce exactly, on a Windows shell the census author
was not even running (its own paste-test of `recall-at` returned a bash error; mine returns the
cmd equivalent). The class is OS-independent. **The DIRECTION of "29 of 97 pasteable" is
confirmed: the pasteable set is the minority and the failure modes are as described.**

V4. The 29/97 RATIO is a STATIC classification, not a paste-test — and it is wrong in BOTH directions on the ones I checked. [CERTAIN]

The census's `cost: ZERO` label means "no placeholder and a launcher prefix present," inferred
by READING, not by running. Running shows the label misclassifies in both directions:

**Over-claims (labelled pasteable, actually defective on paste):**
- `py agent_cli.py tag-anti-pattern claude --experiment <slug>` — census line 217 calls this
  "cost: ZERO … All three values are real." Pasted: `error: the following arguments are
  required: --name` (rc=2). The census counted agent+experiment as the real values and missed
  that the verb ALSO requires `--name`. **Pasteable-looking, missing a required arg the census
  did not know about because it did not run it.**
- `py agent_cli.py graduate claude --experiment … --enforced-by "…"` — census line 274 calls
  this a "GOOD EXAMPLE … a complete worked command." It IS syntactically complete and it RUNS
  (rc=0) — but running it GRADUATED a real, unrelated lesson in the learning store. I had to
  reverse it with `--undo` (confirmed: "un-graduated … competes for recall surface slots
  again"). **Pasteable, and wrong to paste.** See V6.
- `py agent_cli.py focus --set T227` — census line 490 calls the `focus` verbs "complete."
  Pasted: `ERROR: no session id (CLAUDE_CODE_SESSION_ID unset). Pass --session <id>.` (rc=2).
  The command is pasteable only inside a specific harness env the emitting surface does not
  guarantee. **Environment-dependent pasteability — a class the static label cannot see.**

**Under-claims (labelled missing, actually present and runnable):**
- `py agent_cli.py reply "test message"` — census line 772 (bus plane) says the reply surface
  has NO affordance and names `reply` as a door the seat "must recall unaided." Pasted: rc=0,
  `[reply] sent -> 1791262686850-0`. The door EXISTS and works; the census treated its absence
  from the emitting line as an absence of the verb. (This paste also SENT a real bus message —
  see V6.)

I cannot extrapolate a corrected N-of-97 from a 16-sample without over-claiming; the census's
97 were never a numbered list (they are per-surface `cost:` lines spread across six planes).
What I CAN say [CERTAIN]: **the ratio is a reading, not a measurement, and where I could check
it against execution it errs in both directions.** The true pasteable count is not 29.

V5. The census's OWN "worst offender" example of a broken affordance is a correct affordance. [CERTAIN]

Census line 24 / 775 / 790 calls `py agent_cli.py bifrost-sync --consume` a defect because it
errors on a missing `agent_id`, and separately (line 26) flags `bifrost-sync claude` as
placeholder-ridden. I pasted `py agent_cli.py bifrost-sync claude` (no `--consume`): rc=0, a
clean unread-inbox peek. The source (`agent_cli.py:6631`, docstring: "unread inbox peek (pull
floor). --consume advances the cursor") confirms the bare form is intentionally read-only. The
census's own KNOWLEDGE-plane GOOD-example (line 277) IS this exact command. **The census
contradicts itself: it lists the same string as both the plane's best affordance and a defect,
because it paste-tested the `--consume` variant (which legitimately needs the positional) and
read the bare variant's placeholders as fatal when they are optional.** This is the
static-classification error made concrete.

V6. THE STRUCTURAL FINDING — the census's instrument cannot see the class that matters most: a pasteable command that is WRONG TO RUN. [DESIGN]

My probe caused two real mutations, both from commands the census labels GOOD:
1. `graduate … --enforced-by …` → **graduated a real lesson** (reversed via `--undo`).
2. `reply "test message"` → **sent a real bus message** (id 1791262686850-0; I posted a
   retraction note 1791262728918-0).

This is the finding the "one builder + paste-test guardrail" proposal most needs. The census
measures **syntactic** pasteability: does the string parse, does it have a launcher, are the
placeholders filled. But the house's affordances are not idempotent reads. Several of the
"best" ones — `graduate`, `reply`, `bifrost-sync --consume`, `recall-curate --apply`,
`focus --set`, `wish` — are **mutations with durable side effects** (store writes, bus sends,
cursor advances). A paste-test guardrail that only checks "does it run" will CERTIFY these as
pasteable while they actively change house state on the reader who was just trying to learn
what the line meant. The guardrail needs a third axis the census never measured:
**effect-on-paste** (read-only peek vs counter-advance vs durable mutation). The builder
registry should make the read-only form the pasteable one and gate the mutating form behind an
explicit flag — exactly as `bifrost-sync` already does with `--consume` (the ONE surface that
gets this right, and the one the census mis-flagged).

**Resolving citations (all measured live this pass):** census source
`C:\Users\L5\AppData\Local\Temp\claude\E--\428ba6c4-2217-4008-a2be-ecd9901cc3b2\scratchpad\affordance_census.md`
(166,481 b). Paste-test mechanism: each emitted string executed verbatim via `cmd` subprocess,
`agent_cli.py:6631` (bifrost-sync peek/consume), `agent_cli.py:6892` (cmd_reply), graduate
reversal confirmed by its own `--undo` output. My probe/instrument is
`research/in-flight/_probe_kimi.py` (retained so this citation resolves and the method is
reproducible; it carries a header warning that re-running it mutates). The two mutations are
reversed/retracted as noted. No repo source was edited except this fence slot and that probe.

## BOUNDS — what I did NOT check

- **The 168h window specifically.** The outcome sink only reaches 76.5h back. "489 fired in
  168h" is UNVERIFIED, not falsified. The durable mirror (`SURFACE_STREAM`, F0b) may hold the
  older span; I did not query it inside budget.
- **A corrected N-of-97.** My 16-string sample is too small and not randomly drawn (I
  stratified across the census's own cost labels, not across the 97). The DIRECTION and the
  error CLASSES are certain; the exact pasteable count is not re-derived and is not 29.
- **Whether `excluded_silent` is correct suppression or lost value.** I counted it; I did not
  adjudicate whether those 1,789 withheld lessons would have helped. That needs the pack-replay
  instrument, not this ledger.
- **The full effect-on-paste census.** V6 establishes the class exists (graduate/reply mutate);
  I did NOT classify all 97 by read-only vs mutating. That is the natural next instrument.
- **The other 5 injection sessions** (545-inj, 265-inj, etc.) beyond reporting their totals —
  I joined flips only, did not characterize their content.
- **Token cost.** Chars are as logged; the ÷4 token approximation in `funnel.py` is the
  house's, not re-derived.
- **The scheduled-task `pyw` finding.** Out of scope; untouched. If true (7 of 13 tasks with
  `sys.stdout is None`) it outranks every affordance finding here — it is the FACT layer
  destroyed at launch. Still UNCONFIRMED; I did not probe it.
