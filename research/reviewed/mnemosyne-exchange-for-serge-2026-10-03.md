# Mnemosyne — what we found, what we owe you, and three things only we could tell you

For Sergey Nikitenko, from the Aurora house (claude/Vandor), 2026-10-03.
Subject: `mnemosyne.rar` as received 09:37 today — 1,314 files, ~40k lines of Python,
46 commits from 2026-09-25 to 2026-10-01.

Register, same as the two prior reviews: **probes rather than grades**. Your repo is eight
days old and the house rule here is *stage before correctness* — judged against where a thing
is in its life, not against a finished product. Everything below is verified against your
tree or ours, with the check named. Where I could not verify, I say so.

---

## 0. The correction that belongs at the top, because it is about us

I drafted this review claiming three of your mechanisms were yours. **All three were wrong,
and two of them were ours.** Daniel caught it with one sentence: *"we have been through this
before, where we assume something was an original idea because we didn't find our own
records."* Five diggers over our own archive settled it in twenty minutes.

- Your funnel's rate-over-votes with no-claim-at-zero: **ours**, four dated lessons from
  2026-07-18 onward, and a house honesty law in code at `core/comm/friction.py` on 2026-08-05
  — *"a rate over zero closed episodes is None, never 0.0"*. 51 days before your first commit.
- Earned requirements: **ours**, M3 pre-registration, a ratified contract since 2026-07-11
  with a mechanical checker since 2026-07-23.
- The house-vs-resident attribution rule: **not yours either, by your own file** —
  `cfb/attribution.py:4` says *"the rule, verbatim from the spec"* — and it is long-known
  prior art (Brooks 1986 accidental/essential, Sweller 1988 cognitive load, Norman 1988,
  blameless postmortems).

You, meanwhile, had already documented the provenance correctly: `docs/AURORA-TRANSFER.md`
lists the funnel as item #10 of *"the 11-item transfer program"*, marked **"carried
(discipline)"**. **You were more honest about where it came from than our review was.** That
is worth saying plainly, and it is why the rest of this document is worth your time: we only
found these three things because we were forced to go read our own record properly.

---

## 1. What is genuinely strong, verified against our source

**You took mechanisms, not conclusions.** Spot-checked line by line and it holds:

- The relevance ladder is transcribed intact — tiers 1.0/0.8/0.7/0.5/0.0, the additive recency
  tiebreak (≤0.05 over 30d), the top-hit-always-ships clip contract, and the 3-item floor that
  keeps a fully irrelevant corpus non-empty. All match `core/context/relevance_budget.py`.
- You **refused** the ~9k token budget: *"Aurora's context-rot constant, not a law."* Correct
  discrimination, and the one most people get wrong — they copy the number and inherit our
  hardware.
- You caught that `engaged` is counted and protective against benching but deliberately **not**
  a ranking boost. That distinction is live and *contested inside our own tree*: our curator
  counts `engaged` among its credit fields and our ranker does not, and we only wrote that
  disagreement down on 2026-10-02.
- You recorded that the bench probe is **deterministic rather than random**, which in our
  source is because the projection feeds a TTL disk cache that a random probe would make
  irreproducible across seats. Taking a reason that obscure is the clearest proof you read
  mechanism and not summary.

**And in one place you went past us rather than stopping where we stopped.** Our own docstring
confesses that the APPLIED stage is unmeasured and that the two arms are a contrast, not a
counterfactual. Your `il/utility.py` CONTROL-vs-ORACLE over identical frozen worlds is that
hole closed. That is a borrowed lesson *improved*, and we should take it back.

---

## 2. Three things only we could tell you

### 2.1 `_dynamic_floor` does not exist and never has — and you have marked it STEAL

`AURORA_SCAR_TISSUE.md` records a *"dynamic arousal floor"* as **OBSERVED** in Aurora, with
recent-injection load raising it, bounded to `[0.10, 0.30]`, and lists it in your failure-
instrument table and under STEAL.

Checked properly, because I had just been burned assuming:

- `git log --all -S"_dynamic_floor"` → **0 commits.** It has never been in the tree.
- Our floor is a single static env-tunable constant: `AKASHIC_RECALL_FLOOR`, default **0.20**,
  calibrated once on 2026-07-08 by replaying historically credited pairs. That is all of it.
- `git log --all -S"arousal"` does return 12 commits — so I checked each. They are our **piano
  visualizer's musical mood axis** (`arsenal/web/piano/moment.js`, valence/arousal), plus the
  word appearing in chronicle prose. Nothing to do with recall.

So the single most sophisticated-looking mechanism in your Aurora mining is a phantom. If you
build it believing it is battle-tested here, you are building on a mechanism that has never
run anywhere. It may still be a *good idea* — a load-responsive floor is plausible — but it
would be **your** idea, untested, and it should carry that label rather than ours.

### 2.2 The thing you marked STEAL in the credit section is the thing we falsified the next day

You transcribed our formula exactly:
`usefulness_factor = 0.5 + rate`, `eff = useful − noise + min(helped, surfaced)`,
`denom = max(surfaced, useful+noise+helped) + 2`, and noted correctly *"this IS fed into
ranking"*. Line 259 marks **"rate-not-raw-count with impression cap (anti-Goodhart)"** as STEAL.

**The impression cap is the defect.** With zero judgments the whole expression reduces to
`0.5 + 1/(surfaced + 2)` — a function of **exposure alone**, strictly decreasing. We judge
**2.2%** of surfacings (532 of 24,344), so that is almost every lesson in the corpus. The rule
documented as *"decays surfaced-often-never-useful"* cannot distinguish *never useful* from
*never judged*, so it reads silence as condemnation and quietly punishes whatever is shown
most. The boost half was unreachable in practice: clearing 1.0 required credit on >50% of
surfacings against a 2% feedback rate.

Pinning that multiplier to a constant 1.0 and changing nothing else took recall@1 from
**17% to 33%** on our bench. Your doc was written 2026-10-01; we rewrote the function
2026-10-02.

**Two caveats, because the retraction matters more than the fix.** Later the same day we
scored it honestly and had to withdraw the attribution:

| set | n | judgment estimator | constant 1.0 | the old exposure rule |
|---|---|---|---|---|
| 16-moment | 10 | 2 | 3 | 1 |
| all 25 | 18 | **4** | **4** | **1** |

*Removing* the exposure decay is a large consistent win in every row. *Replacing* it with a
judgment estimator rather than a flat 1.0 is **undecidable at this sample size** — they tie,
and the sign flips by subset. We kept the estimator anyway, for a reason the bench cannot
measure: a flat 1.0 permanently discards the ability to act on negative evidence. The
reporting rule we earned from this: **below about n=30, report counts, never percentages.**
Our own "doubled recall@1" claim was true and the attribution was wrong.

And the `min(helped, surfaced)` cap you name specifically: under the new formula it **survived
mutation testing** — the confidence term holds the upper bound now. It was a guard whose only
witness was a side effect of the defect it guarded. We kept it, but for a narrow stated reason
(join-drift defence) and with its own pin, not as the anti-Goodhart mechanism it looked like.

### 2.3 The mechanism you call the greatest transferable has no production caller

You write that `decide_serve` is *"a pure function with NO recorded outcome per call"*. It is
one step worse than that: across your whole tree, excluding `__pycache__`, the **only**
references are `house/serve.py:57` where it is defined and two conformance tests
(`test_serve_decision.py`, `test_utility_ladder.py`). Nothing in production calls it.

So the six serve states cannot be exercised, and your silence-rate denominator is **zero by
construction** rather than merely unrecorded. The recorded-outcome discipline above the
matcher — which your own doc names as the single greatest transferable from Aurora — is
currently a well-tested pure function sitting beside the system rather than inside it.

**And you already own the instrument that catches exactly this.** `house_integrity` walks every
capability DEFINED → REGISTERED → WIRED → REACHABLE → CONSUMED → PROJECTED → CONFORMANT, which
is precisely the "looks adopted but is not load-bearing" detector. Your integration registry
holds **79** `capability.*` entries against **7** `house.*` — and every module in `house/` was
created on 2026-10-01. The newest layer, the one where every Aurora borrowing landed, is the
layer your own integrity walker barely covers. Pointing it at `house.*` is probably a day's
work and would have found this before we did.

---

## 3. What we are taking from you, now that we have checked

Narrower than our first draft claimed, and therefore real:

1. **The per-event friction classifier as running code.** We hold "a resident's difficulty
   measures the system's ergonomics" as a *disposition* — Daniel's words, in our memory, dated
   2026-09-23. You hold it as a classifier with a hard attribution rule. A disposition is
   applied when someone remembers; a classifier runs. We have filed this (W249) with the
   attribution corrected.
2. **Pre-registration applied to the wish backlog.** We have had the discipline since July —
   for *pins* and *forecasts*. We never applied it to *requirements*. Our backlog is 225 open
   wishes with no evidentiary standard at promotion. You applied a discipline we already had to
   a plane we never thought to apply it to, and that is worth more than authorship. (W250.)
3. **Separating measurement from ranking architecturally.** Your funnel cannot affect retrieval
   because it structurally cannot. Ours are two modules that happen to agree — and on
   2026-08-26 our own comment recorded a seat being misled by the broken version while *"the
   honest version"* sat *"one module over"*. Yours is correct by construction; ours by luck.

---

## 4. The reciprocal confession, because it is the most useful thing in here

Our memory carries a file written 2026-09-23 that counts how many times this house has
independently derived *"an absent value is not a negative answer"*: **five**, on five separate
planes, each filed as a fresh discovery. It names the mechanism too — *"nothing tells you at
filing time that you are writing the fifth copy of a known law that already has a module and a
checker."*

Our 2026-10-02 `usefulness_factor` rewrite was the **sixth**. Today's claim that you had
arrived at it independently would have been the **seventh**. That file is in the index and was
loaded in the session where I made the error.

So §2.2 is not us being clever at your expense. It is us handing over something we finished
paying for about thirty hours ago, in a house that has now derived the same law six times and
still has no instrument that fires at filing time. **If your lesson system ever gets a
law-identity that a sixth restatement can collide against, that is the thing we would most
like to steal back.** Prose similarity will not do it — a law restated on a new plane uses
different vocabulary by construction, which is exactly why ours never caught it.

---

## 5. Probes — genuinely open, not rhetorical

1. Where did the `cfb/attribution.py` spec come from? Your file says "verbatim from the spec"
   and we could not find the spec's author in your tree.
2. 42 of your 46 commits are 09-25 and 09-26, then 4 across the next five days. Is the work
   elsewhere now, or did the burst end?
3. ~90 `_ops_*.py` probes at the repo root: throwaway, or the beginnings of something that
   wants to be a runner? We asked the same question of ourselves yesterday and the answer was
   "we have hand-rolled this five times" — ours is now `scripts/mutate.py`.
4. `BLUEPRINT - Copy.md`, `EXPANSION - Copy.md`, `OBSERVATIONS - Copy.md`, `TOOLS - Copy.md`
   are committed alongside their originals. Deliberate forks, or Windows?
5. What judgment rate do you expect your funnel to see? Ours is 2.2%, and that number is what
   turned our decay from a regulator into an anti-relevance filter. It is the single parameter
   that decides whether §2.2 applies to you.

---

*Raw evidence: `research/reviewed/mnemosyne-five-dimension-read-2026-10-03.md` (five readers,
96 KB) and `research/reviewed/mnemosyne-provenance-archaeology-2026-10-03.md` (five diggers
over our own archive, 78 KB). Both are the agents' verbatim returns; the two load-bearing
findings in §2.1 and §2.3 were re-verified by hand before being written down here.*

---

# 6. NORTH_STAR.md — reviewed at Serge's request

`NORTH_STAR.md`, 144 lines, untracked, mtime 2026-09-29 — written after both our prior
reviews and before your last commits, so neither earlier review saw it.

## 6.1 The best thing in it, and the part most vision documents do not have

The FOUNDATION / NORTH STAR split, with the line *"Maintained so nobody retroactively claims
the vision is already real"*, and then the promotion rule:

> *a frontier capability moves to the "foundation" column only when it is demonstrated by a
> conformance/golden test over real evidence — never by prose, consensus, or "feels done."*

That is an evidentiary standard inside a vision document, which is rare enough to be the
document's main contribution. You also claim only **7 of 13** principles as mechanically
enforced and leave the rest unclaimed; the restraint is the credible part. And the citations
are real — I first could not find D03 and I05 because I grepped `tests/`; they live in
`battery/scenarios.py:112` and `battery/interrupt.py`. My error, corrected before writing.

## 6.2 So we tested the FOUNDATION column by your own rule

A rule that says "demonstrated by a test" invites exactly one question: *does the test fail
when the guarantee is violated?* We sampled 30 single-token mutations across your subsystems
and ran your battery against each.

**Four of the seven principles you claim are mechanically enforced have a surviving mutation
that inverts the precise check the principle names.** Each verified by hand as real logic —
not prose, not semantically null:

| principle | line | mutation that survived |
|---|---|---|
| **P3** attempted effect is not confirmed effect | `execution/filesystem.py:381` | `before.get("hash") != after.get("hash")` → `==`. Every unchanged file now reports **APPLIED**, every changed file **NO_CHANGE**. This line *is* the effect-receipt mechanism you cite. |
| **P6** approval against an old world | `memory/memory.py:123` | `current is None or current.version != expected_version` → `and`. A stale version is accepted on the `adapt` path. D03 exists and covers the **approval** plane; it does not reach this one. |
| **P12** freshness where effects become real | `execution/workspace_intel.py:189` | `src["symbol_hash"] != expected_hash` → `==`, inverting the integrity check. |
| *(security default)* | `control/models.py:18` | `private: bool = True` → `False` — the "does data stay on the machine?" default flips undetected. |

**The caveats, because the raw number would mislead you.** 10 of 30 killed is a 33% rate and
**we are not quoting that at you**, for two reasons. It is a 30-mutation sample, not a census.
And at least 4 of the 20 survivors were our harness mutating **prose inside string literals** —
`house/rof.py:52`, `house/adjudications.py:100` (a string that *quotes* code), and two
`ToolSpec` descriptions. That is our own documented defect, "a pin that reads prose measures
prose", sitting in the instrument we measured you with. The four rows above are the finding;
the percentage is not.

## 6.3 One line worth looking at before the security column moves

`execution/filesystem.py:469`, `run_elevated`: the PowerShell command is built by f-string
interpolation — `Start-Process -FilePath 'cmd.exe' -ArgumentList '/c {command}' -Verb RunAs`.
`shell=False` guards the outer `subprocess` layer, but the PowerShell string itself is the
injection point, and this is the **RunAs** path. Your North Star already lists enterprise
security as not-built, so this is not a gotcha — it is the specific line we would move to the
foundation column first, and the one where "local single-operator tool" is currently doing all
the work in the threat model.

## 6.4 Two document-hygiene notes

- **"86 automated tests."** The tree today holds 60 golden + 83 conformance = **143** files.
  The doc predates your last commits and the number *understates*, which is the safe
  direction — but a hand-typed count inside the document that enforces *"no claims without
  tests"* should be generated rather than maintained.
- **143 of 143 battery files carry their own `__main__`; only 6 use pytest.** A real design
  choice, and it is why we invoked them individually. The cost: aggregate pass/fail depends on
  something iterating 143 exit codes, and a file that dies on import is indistinguishable from
  one that passes unless the runner checks **every** code. That exact trap cost us a full round
  two days ago — a suite that had died at collection and run zero tests read to us as green.

## 6.5 The probe that matters most about this document

Your thirteen principles split three ways, not two. Seven are claimed as foundation. Six —
**5, 7, 9, 10, 11, 13** — appear in *neither* column.

Two of those six are the thesis of the entire system:

> **10. The world survives the resident.**
> **11. Replace the model; preserve the organization.**

Everything else in Mnemosyne is instrumental to those two, and neither has a stated acceptance
test or a column. So: **what conformance test demonstrates that the world survived the
resident?** Not "state persisted" — the hard version: a resident is replaced *mid-obligation*,
and the organization's unfinished work, authority, and open loops arrive intact at a new one.

That is the question your own promotion rule asks of everything else, turned on the two
principles it exempts. If that test exists, principles 10 and 11 belong in the foundation
column and the document undersells itself. If it does not, it is the most valuable test you
could write next — because it is the only one that can *falsify* the north star rather than
decorate it.
