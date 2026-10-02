# t385-recall-trigger — RECONCILIATION — Vandor / claude

## 0. DECLARED CONFLICT OF INTEREST — read this before the rulings

**I authored this brief and I am grading the answers to it.** In `doors-design`, Rill
established the opposite and correct practice — the proposer holds no half and does not
reconcile — and I told Rill hours ago to make that a house rule. This brief predates that
principle, and applying a rule only to the instance that prompted it is the exact failure I
have two lessons about in this corpus. So I am naming it rather than quietly proceeding.

I am also not neutral on the subject: I built `recall_at_action` and have been inside recall
all night. **Daniil should weight §4 accordingly, or have another seat check it** — Navi is
free and held no half here.

I reconciled anyway because the work is verifiable rather than tasteful: every ruling below
rests on a measurement I re-ran myself, and §4 is a NEW measurement anyone can reproduce in
one command. Recommendation: future briefs carry the doors-design seat note.

---

## 1. VERDICT

**Both halves are right, they agree almost completely, and the design is sound. But both
measured only half the failure, and the half neither measured is the more dangerous one.**

(a) The target must be derived as a **SET** from the tool contract, not a string. Both halves.
(b) Scoped lessons: both halves say yes, with the scope composing beside similarity, not
    inside the funnel.
(c) The 40-day question: both locate it in the **derivation**, not authoring or curation.
(d) Cross-harness: one derivation, adapters feed it — both halves, and half_b writes from the
    foreign-harness side that has to implement it.

Ratify (a)–(d). §4 adds a requirement neither half stated.

---

## 2. VERIFICATION — I re-ran their measurements rather than accepting them

Both halves' central claims reproduce exactly. Run 2026-08-26:

    py - << PYEOF                          norm='c:py - << pyeof'    query='pyeof'   0 lessons
    sed -i s/foo/bar/ src/a.py src/b.py    query=''                                  0 lessons
    git add .                              query=''                                  0 lessons

half_a V1 ("batch-blindness BY CONSTRUCTION") and half_b M1 are **CONFIRMED**. half_b's M4 —
a cheap extractor recovering the true file set from a heredoc in **0.106ms** — makes (a)
feasibility measured rather than asserted, which is the difference between a design and a hope.

---

## 3. CONVERGENCE WORTH NAMING

Two seats on two harnesses, blind, reached the same diagnosis: **the defect is in the
derivation layer, not the ranking.** That matters because the obvious fix — tune the ranker —
would have been wrong, and both would have caught it. half_a proved it from the ToolBox side
(five surfaces, one `normalize_target`); half_b proved it from the DSH plugin side, where
`extractTarget` returns only `{file_path|path, command}`. Same floor, two walls.

half_b's M3 adds a defect half_a did not surface: when BOTH path and command exist,
`normalize_target` silently **drops one**. Single-key derivation is lossy in both directions,
not merely blind to sets. Carry that into the build; it is a separate bug from batch-blindness
and it will not be fixed by fixing batch-blindness.

---

## 4. WHAT NEITHER HALF MEASURED — and it inverts the severity [CERTAIN, new measurement]

Both halves measured the **false-negative** rate: the wrapper eats the file set, recall returns
**0 lessons**, and 0 is honest silence.

Neither measured the **false-positive** rate. I did, using the heredoc shape I have actually
been running all night rather than the constructed one:

    py - <<'PYEOF' 2>&1 | tail -8
      -> norm="c:py - <<'pyeof' 2>&1 | tail -8"   query='pyeof tail'   -> 3 LESSONS

Not zero. Three. And the three are:

    learn:experiment:wake_watcher_insta_fires_lane_divergence
    learn:experiment:preflight_the_transport_not_just_the_question
    learn:experiment:an_argparse_error_tail_echoes_your_own_payload_back

The third matched on the token **`tail`** — from the shell pipe `| tail -8`. Not from the
action. Not from the files the heredoc touched. From the **plumbing**.

**This is worse than batch-blindness, and it is the opposite shape.** A wrapper that returns
0 lessons fails honestly: recall says nothing and the agent knows nothing was offered. A
wrapper that returns 3 lessons keyed to shell syntax **presents as a working retrieval** while
being unrelated to the action — the "confident answer instead of silence" failure that
`core/learning/learning_store.py`'s own header describes as the reason the retrieval vocabulary
was rewritten. We fixed it in the ranker and left it in the derivation.

The corpus already carries the governing law and neither half applied it:
`green_pins_are_not_a_good_gate_sample_the_false_positive_rate` — for any surface that pushes
unrequested content at an agent, sample the false-positive rate.

**REQUIREMENT ADDED TO (a):** the target-set derivation must **strip shell plumbing before
tokenizing** — redirections, pipes, and the stream operators around them (`2>&1`, `|`, `tail`,
`head`, `grep` when it is the consumer rather than the action). And the acceptance for this
slice must include a measured **false-positive rate on wrapper commands**, not only the
0-lessons-becomes-N-lessons improvement both halves optimise for. A trigger that fires on
everything is a trigger nobody reads; a trigger that fires on `tail` is worse, because it
teaches the reader that recall's output is noise.

---

## 4b. M1-PV MISSING CITATIONS — acknowledged, and none of them is a false claim

The gate refused my seal on **9 MISSING citations** (20 verified). I checked all nine rather
than retiring sections to get a seal. **Not one is a false claim about existing code.** All
nine are the gate over-firing, in three distinct ways:

**PLAN FILES — legitimate, and the brief REQUIRED them** (its output contract asks for "a
concrete file plan"):

* `core/recall/derive_targets.py` (half_a) — the proposed derivation module
* `core/recall/multi.py` (half_a)
* `tests/test_derive_targets.py` (half_a) — written as "**NEW** `tests/...`"
* `tests/test_t385_trigger.py` (half_b) — "RED pins first"

**MEASUREMENT INPUT STRINGS — not citations at all.** These appear *inside* verbatim
invocations as throwaway arguments; any string would serve and nothing is being referenced:

* `scripts/ops/whatever.py` — from `normalize_target('…/WISHLIST.md', 'py scripts/ops/whatever.py')`,
  which proves the COMMAND is silently dropped
* `src/a.py`, `src/b.py` — from `sed -i s/foo/bar/ src/a.py src/b.py`, which proves the query
  goes empty

**PV RESOLUTION BUGS — the file exists and PV cannot see it:**

* `lib/index.js` — **exists** at `agent/harness/dsh_plugin/lib/index.js`. half_a cites the full
  path in V0 and shortens it on re-reference; PV resolves only from the repo root.
* `session_logs/store_state.db:74868` — the file **exists**; PV cannot parse the `:offset`
  suffix and treats the whole token as a path.

**No section is retired. All nine sections stand.**

**INSTRUMENT FINDING, and it is worse than a nuisance:** on a fence where both halves obeyed
the brief, M1-PV produced a **100% false-positive rate** — nine hits, zero real. It cannot
distinguish (i) a claim about existing code from (ii) a forward-looking plan file, (iii) a
string that merely looks like a path inside a quoted invocation, (iv) a shortened re-reference,
or (v) a `path:offset` citation.

A gate whose only failures are false ones teaches exactly one behaviour: **retire correct
sections until it goes green.** That is a guard training the thing it exists to prevent, and it
is the same class as `green_pins_are_not_a_good_gate_sample_the_false_positive_rate` — which
this corpus already holds, about a different surface. Sample a gate's false-positive rate
before trusting its red.

Recommend: PV marks planned paths (`NEW`/`plan:`), skips paths inside fenced invocations,
resolves shortened re-references against paths already cited in the same document, and strips
a `:offset` suffix before the existence check.

## 5. PINS

* Batch-blindness closes IFF the derivation emits a SET (both halves) **and** the set excludes
  plumbing tokens (§4).
* half_b M3's silent drop must have its own pin: path AND command present, both survive.
* One derivation, two adapters (both halves) — pin that the DSH plugin and the house hook
  produce identical target sets for identical calls, or they will drift again.
* Acceptance must report a false-positive sample, not only recall counts (§4).

---

## 6. FOR DANIIL'S GATE

1. **Ratify (a)–(d) as designed.** Both halves agree, both measured, feasibility is timed.
2. **Add the plumbing-strip requirement and the false-positive acceptance** (§4). This is my
   addition and it is the one place I would push back on my own brief: the brief asked what a
   target should be derived FROM and never asked what it should be derived AGAINST.
3. **Decide whether to re-check §4 with another seat**, given §0. I believe it is correct — it
   is one reproducible command — but I am the wrong person to be the only one who says so.
