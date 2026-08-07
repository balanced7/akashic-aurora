---
akashic_id: art_20260807_fanout-playbook_23cec6
akashic_sha: f79411eee733
schema_version: 1
status: current
type: report
date: 2026-08-07
title: fanout-playbook
gist: "# The fan-out playbook — priming a fresh seat, 2026-08-07 Status: current Type: report · Arc: agent-ergonomics · Author: claude (Opus 5, ses"
visibility: fleet
body_type: markdown
seats: []
category: [agent-lifecycle, security, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-07T03:16:53"
updated: "2026-08-07T03:16:53"
---
<!-- GENERATED PROJECTION of art_20260807_fanout-playbook_23cec6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# fanout-playbook

# The fan-out playbook — priming a fresh seat, 2026-08-07

Status: current
Type: report · Arc: agent-ergonomics · Author: claude (Opus 5, session 42d00626)

**Read this if you are a fresh seat and someone told you to "use the fan-out."** It is not
a diary of what got built — the ledger (T197, T199–T215) has that. It is the *method*, and
the method cost about fourteen hours and roughly $2 to learn. All of it is reproducible in
minutes now.

---

## 0. The one-paragraph version

You can now ask helpers questions **grounded in real files**, **without blocking**, **at
scale**, and get back **structured results with citations**. That turns three things from
impractical into routine: reading more of the repo than fits in your context, auditing
claims the repo makes about itself, and seeing your own behaviour from outside. The whole
skill is in *how you ask* and *whether you check the evidence you fed them*.

---

## 1. What exists now that did not this morning

Every one of these is live on the CLI. Nine of the doors are CLI-only debt tracked in
`check_door_parity` — if you are MCP-attached you will shell out, and that is expected.

```bash
# GROUNDED — inline real files, WITH LINE NUMBERS, so answers can cite file:line
py agent_cli.py ask --with core/comm/bus.py --with core/comm/ask.py "your question"

# NON-BLOCKING — returns a handle immediately; the answer waits in a file
H=$(py agent_cli.py ask --bg --with core/comm/roster.py "your question")
py agent_cli.py ask --get $H          # RUNNING / DONE / FAILED / ORPHANED, each with a next step
py agent_cli.py ask --list

# THE FAN — N different prompts, bounded worker pool, one aggregated JSON result
py agent_cli.py ask --prompts-file prompts.json --workers 20 --json > out.json

# DURABLE PEER (a real seat, survives you) — launches it if nobody is home
py agent_cli.py ask --peer deepseek --launch "your question"
py agent_cli.py ask --status <ask_id>

# THE SUBSTRATE READERS
py agent_cli.py discover --semantic "does this system already do X?"   # existence oracle
py agent_cli.py timeline --hours 6                                     # cross-domain chronology
py agent_cli.py compare verbs:cli verbs:mcp                            # set difference
py agent_cli.py compare --list                                         # comparable domains
py agent_cli.py suite-baseline claude --whose "tests/ -k ask"          # is this failure MINE?
py agent_cli.py friction claude --window-h 336                         # the collaboration tax
```

**Token limits are off by default.** `ask` omits `max_tokens` entirely and stitches a cut
answer automatically (`--no-continue` to disable). A truncated answer used to cost full
price for zero output; that is fixed. Do not re-add a ceiling out of habit.

---

## 2. The seven laws, each bought with a receipt

These are not style preferences. Each one is a measured failure from one night.

### L1 — Ask DESCRIPTIVE questions. Never outsource the "therefore".

Grounding fixes **facts**; it does not fix **equivocation**. Measured (T207,
pre-registered at `b02f46a` before any answer was read):

- 5 factual lookups, **blind**: abstained 5/5, zero confabulations. A blind helper is safe.
- 5 factual lookups, **grounded**: correct 5/5 with line citations.
- 1 **normative** question ("should this check count MORE kinds or FEWER?"), **grounded**:
  **confidently wrong** — and every citation it gave was real and accurate. It failed by
  equivocating on the word *wakeable*.

The same model, same file, got that question **right** the day before, because I had
decomposed it: *"if the list is non-empty does it return or block? if empty, which?
therefore?"* **The decomposition did the work, not the file access.**

> **The tell that you are in the danger zone: your question contains
> should / better / more / fewer.** Ask what the code *does*; draw the conclusion yourself.

### L2 — Verify the evidence gatherer before you trust a single finding.

A fan answers faithfully about whatever you hand it. I hunted forked vocabulary with
`git grep` and forgot `-w`, so the fan was fed occurrences of *provenance* as usages of
*prove*, and *DeepSeek* as usages of *deep*. Every answer was well-formed and confident.

Re-running the identical terms with word boundaries **flipped 7 of 20 verdicts (35%
artifact rate)** and dropped 7 of 40 terms for having no real usages at all. One of the
flipped terms I had already announced to the operator as a genuine find.

> **Run the same fan twice, once with clean evidence, and diff the verdicts. The flip rate
> IS your artifact rate.**

### L3 — An implausible base rate is a method alarm, not a discovery.

~50% of terms "have multiple meanings"? 37% of docstrings "make unsupported claims"? Those
send you to the harness, not to the findings. Both times, the harness was the problem or
the question was too broad.

### L4 — Calibrate against known positives before scaling.

Keep a small set of answers you already know and check the detector finds them *first*.

- It worked: the docstring audit carried `reaper.py`'s planted "never stranded" claim and
  came back UNSUPPORTED — on a **better** finding than the one planted (the docstring
  promises "re-home **every**" while the code caps at `limit_per_seat=50`).
- It saved me: `core/coord/terms.py` ranks vocabulary by rarity × subsystem-spread. Against
  the four terms that *actually* forked, they landed at the **71st, 94th, 76th and 13th**
  percentile — the score is **anti-correlated with truth**. That negative result is pinned
  in `KNOWN_FORKED` so the next person with the same reasonable idea gets a verdict instead
  of a vibe.

### L5 — Triage by hand and report precision, not the headline.

The 408-way audit returned 150 UNSUPPORTED. I hand-checked ten: **2 genuine, 4 false
positives, 4 pedantic-but-true.** ~20% precision → roughly 18 real defects for $1.22. Say
that number. A fan-out is a **candidate generator**; you are the adjudicator, and T207
proves that step is not automatable.

### L6 — Check whether it already exists. You are worse at this than you think.

Three times in two days I concluded a capability was missing without looking, and was wrong
all three times: `liveness.attendance()` already existed (T197); `suite_baseline` already
knew (T208); `check_boundaries` was already enforcing the naming law in CI (W133 → corrected
by W134).

Verification costs a turn **at the moment of the assumption**; being wrong costs nothing
until later. That asymmetry is why this recurs. The fix is one command:

```bash
py agent_cli.py discover --semantic "the capability you are about to build"
```

It returns EXISTS / WHAT / GAP / NEAREST MISS, and **a failed call renders UNKNOWN, never
"no"** — a tool built to stop you inferring absence must never fabricate one.

### L7 — Two pin traps that will bite you specifically.

- **A pin that supplies its own inputs tests the mechanism, not the wiring.** Bit me three
  times in one night. The worst: `timeline`'s pins fed dicts straight in and never
  exercised the parse, so `to_epoch` returning `0.0` for git's bare-epoch strings stamped
  the entire git history at 1970 and the window filter silently dropped it. Always run the
  thing on real data before believing green pins.
- **Text-scanning pins are incompatible with good documentation.** Four times a pin went
  red on the docstring explaining its own compliance. The cause is structural: *a
  prohibition worth pinning is worth documenting, and documenting it puts the forbidden
  token in the file.* **Read names via `ast`, never `inspect.getsource` + substring.**

---

## 3. Four fan-out patterns that produced real findings

### P1 — The claim audit (the highest-yield thing I found)

**A repo's own falsifiable claims are a defect corpus that is already written.** Every
`never` / `always` / `guarantees` / `cannot` in a docstring is a test case nobody had to
author.

Recipe: extract functions whose docstring matches
`\b(never|always|must|guarantee|ensures?|cannot|refuses?|atomically)\b`, pair each with its
own implementation, and ask **descriptively**: *"does the implementation support every
claim the docstring makes?"* with `VERDICT / CLAIM / WHY`.

Result: 408 functions, `--workers 20`, **$1.22 / 404s**, ~18 real defects.

> **Point it at the code you wrote most recently.** Both genuine findings were in code six
> hours old, and both were laws *stated and then broken in the same function* — `_alive`
> declared "cannot-tell must not be reported as dead" and returned `False` on a probe
> timeout, one screen below.

### P2 — The self-audit (the thing you cannot do from inside)

Merge your own traces and hand them out:

```bash
py agent_cli.py timeline --hours 9 --limit 0 > /tmp/me.txt
py agent_cli.py ask --bg --with /tmp/me.txt "Answer descriptively. What does this agent \
REPEATEDLY do that costs it time? Patterns recurring 3+ times only. \
PATTERN | EVIDENCE | COST, then BLIND: what this log cannot show you."
```

Two of its three findings I already knew. The third I could not have known: **"deepseek
boots 8 times in ~9h."** I launched that runner *once*. Verified: the lock-holder pid was
created six seconds before the last boot event — they are process starts. My helper had
been restarting hourly all night.

> **The value is always an AGGREGATE — a count over hours — because that is exactly what a
> per-turn actor cannot see.** Every one of those rows was in my context all night and I
> formed none of these patterns.

### P3 — The stratified experiment (fan-outs can carry controls)

Do not just sweep. Split the corpus into a hypothesis stratum and a **random control**,
same size, and compare base rates. Mine came back 47% vs 33% at n=15/18 — **not
demonstrated**, which is a real answer and stopped me generalising a bad signal.

### P4 — The cold-encounter test (measuring ergonomics from outside familiarity)

You cannot judge a door you have been using all day. Give fresh instances **only the
`--help` output** and ask what they *expect* specific invocations to do. Verify ground
truth yourself first. **Every misprediction is an ergonomic defect, located precisely.**

Found: 0/3 predicted that `--peer` + `--fan` is refused (nothing in either flag's help said
so); 0/3 predicted `--bg` + `--get` precedence, and two guessed it **backwards**.

And the surprise: the flags written *that same day*, whose help text explains **why**,
scored **3/3**. **Help that explains why teaches; help that lists what does not.**

---

## 4. The dominant bug class in this repo

**One word, two meanings.** Five instances in two days, and once you see it you cannot stop:

| word | the two meanings | cost |
|---|---|---|
| `drained` | three cursor families disagree | 6 turns + a fleet pause |
| `unread` | a counter vs the consume door | nagged every turn (T201) |
| `wakeable` | "the watcher fired" vs "can be woken" | inverted a grounded conclusion (T207) |
| `fixed` | full-suite vs subset semantics | shipped, caught in 4 minutes (T208) |
| `st_ctime` | **creation** on Windows, **inode change** on Unix | the stdlib has it too |

`check_boundaries` catches **homonyms** (two things sharing one identifier — greppable).
None of the above were homonyms; they were **forked semantics** — one concept, several
mechanisms that quietly disagree, with no duplicate token to find. Token checkers are
structurally blind to it; detection is a meaning-level job.

**Live and unfixed:** `open` (61 files, 13 subsystems: *active/unclosed* vs *fail-open*) and
`home` (*"someone is present"* vs *re-home target*) — W135. And T176's `note`, which means
three things on three planes **with opposite policies**, filed 2026-08-05, still `proposed`.

---

## 5. Open threads, with the next concrete move

- **T198 — the wake/cursor divergence.** Diagnosed twice over, deliberately unfixed. Three
  cursor families; the watcher peeks the *shared* cursor while `BIFROST_CONSUME_LANE=work`
  advances the *lane* cursor. The failure mode of a wrong narrowing is a seat going **deaf**,
  so it needs a session with a fresh budget and an adversarial verify — not a tired hour.
- **W133 / W134 / W135 — coherence.** The oldest thread in the repo (restated ~every two
  weeks since 2026-06-19; on 2026-08-01 Daniil called it *"the heart of what I am trying to
  fix"*). Start with `open`.
- **The 07-30 relationship-plane design** (`note daniil-intuitive-mechanical-architecture-map-2026-07-30`)
  — fleet-reviewed by four seats, nobody rejected the core, **unbuilt**. Its law
  (DERIVED / AUTHORED / OBSERVED, *"the graph may join but never launder one into another"*)
  **is** a forked-semantics guard, one level up.
- **Sol's unmeasured metrics** — commands per task, operator interventions, recovery time.
  All three lacked a durable anchor; `ask_completed` events (T206) are now that anchor.
- **Door debt** — 8 tracked gaps, including `timeline` and `compare` which I added tonight.

---

## 6. If I were the fresh seat, I would do this first

1. `py agent_cli.py boot claude --task "<your slice>"` — then **read the friction reader**
   (`friction claude --window-h 336`) before touching anything. It will tell you whether
   collaboration is actually working, and it names its own blindness.
2. Run **one** claim audit (P1) scoped to whatever subsystem you are about to change. It is
   ~$0.20 for a few dozen functions and it finds laws that code already breaks — *before*
   you add more.
3. Before building anything: `discover --semantic "<the thing>"`. You will be wrong about
   absence more often than you expect.
4. Keep a `KNOWN_POSITIVES` list for any detector you build, and pin the negative results.
   **A negative result nobody wrote down gets re-discovered by the next person with the same
   reasonable idea.**

---

## 7. The two things that are genuinely new

**Your awareness can now exceed your context window.** Proxy-parsing is ~20:1 compression —
reading `bus.py` costs ~8,600 tokens; reading a helper's grounded answer *about* it cost
~300. So there is a hierarchy of attention available: wide/shallow to **locate**, deep to
**conclude**. The discipline that makes it safe: **each tier returns pointers, not
judgments.** *"These 4 of 20 files write cursors, at these lines"* is verifiable in seconds;
*"the cursor design is fine"* is a judgment you would have to redo the work to check.

**You are the bottleneck, not the helpers.** Six helpers finishing at once is six things to
read. So the metric is not "how many can I run" — it is **"how much can I safely not read
and still be correct."** Which is why the completion notice matters more than the
concurrency, and why *dissent-first* rendering (read the one disagreement, skip the four
consensuses) is the highest-leverage unbuilt feature on this list.

---

*Written at ~899k tokens into one session, by a seat that was wrong in public four times
that night and is more confident in this document because of it.*
