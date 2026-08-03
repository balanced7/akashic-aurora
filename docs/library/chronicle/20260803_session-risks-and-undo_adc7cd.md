---
akashic_id: art_20260803_session-risks-and-undo_adc7cd
akashic_sha: e1d55ba4c28a
schema_version: 1
status: current
type: chronicle
date: 2026-08-03
title: session-risks-and-undo
gist: "# Session 2026-08-03 — what changed, what it risks, and how to undo any of it Written for Daniil, who authorized ratification on the conditi"
visibility: fleet
body_type: markdown
seats: []
category: [security, governance, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-03T09:27:31"
updated: "2026-08-03T09:27:31"
---
<!-- GENERATED PROJECTION of art_20260803_session-risks-and-undo_adc7cd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# session-risks-and-undo

# Session 2026-08-03 — what changed, what it risks, and how to undo any of it

Written for Daniil, who authorized ratification on the condition that risks are documented and
undo options provided. **Every mutation below is one `git revert` away**; nothing was deleted,
and no history was rewritten.

The one-line version: two jobs he greenlit — extend the wiring check, retire what is no longer
needed — plus two defects found while doing them, both fixed with pins.

---

## The blunt summary of risk

| # | Change | Risk | Undo |
|---|---|---|---|
| 1 | `check_wiring.py` gains a FUNCTION-level gate | **Low.** Could block a commit on a false positive | `git revert 1a4ffe8` |
| 2 | `self_invoking_modules` excludes re-exported modules | **Low-medium.** Could re-open a false positive | `git revert a0115d7` |
| 3 | Ledger `CLAIMED -> VERIFYING` transition | **Medium — read this one** | `git revert 3dca734` |
| 4 | Four entries closed, three abandoned, five minted | **Low.** Reversible data | `git revert 3dca734` + see §4 |

Nothing here touches Redis, the bus, the runners, the mail lanes, or any live seat's state.
Changes 1–2 affect a checker; 3 affects a transition table; 4 is data in a version-controlled JSON.

---

## 1. The function-level wiring gate (`1a4ffe8`)

**What.** `check_wiring.py` walked the import graph over MODULES. It passed for months while
`core/comm/mailbox.py::declare_intent` had zero production callers — mailbox.py *is* imported by
the CLI door, so the module read wired while the capability inside it was dead. It now also asks
whether each public function is ever named on a production path.

**Validated against the real case, not a synthetic one.** In throwaway worktrees at the two actual
commits:

- `95e0c55` (declare_intent built, 8/8 pins, no door) → **FAIL** on `mailbox.py::declare_intent`
- `b945813` (the door added) → **silent**

`b945813`'s own commit message reads *"built was not wired -- no door exposed the M1 verbs"*.
A human diagnosed that by hand once. The gate now does it at commit time.

**Risk.** It runs in `pre_commit.py` and `ship.py`, so a false positive would block commits —
for every seat, not just mine. Three things bound that:

- Evidence is deliberately weak. "Referenced" means *mentioned by name* anywhere on a production
  path — call, attribute, bare name, import alias, kwarg, or an exact-match string constant. So
  `getattr(mod, "promote")` counts as wiring. Only ZERO-mention capability is reported.
- It ratchets against a frozen baseline of today's 114 findings. Only NEW orphans fail.
- 9 pre-registered pins, committed RED and alone at `c61fa98` before any implementation.

**Residual risk I have not eliminated:** a function whose name is assembled at runtime
(`"declare_" + verb`) is invisible to it. Stated in the module docstring rather than discovered
later. If the gate ever blocks a commit wrongly, the fast unblock is to add the entry to
`scripts/checkers/wiring_function_baseline.json` — no revert needed.

**The loudest finding it produced:** `core/coord/cognitive_metrics.py` has **eight** public
functions and not one caller — `record_prompt_tokens`, `record_completion_tokens`,
`record_reasoning`, `record_abandoned`, `record_context_refresh`, `record_tool_call`, `dump_all`,
`disable`. A whole instrumentation module built and never wired to anything that runs. Not touched;
it is on the backlog for a decision, and it is a genuine "no longer needed?" candidate.

---

## 2. A `__main__` block in a library is a stub, not an entry point (`a0115d7`)

**What.** The gate was warning that `core/state/session_recovery.py`'s exception was stale —
"now wired (or gone)". It was neither. Traced: no importer, no shell caller. The only thing
calling it wired was a rule added 2026-08-01 that reads any `if __name__ == "__main__":` as an
entry point. Its entire guard body is `recovery = main()`, and `core/state/__init__.py:21`
re-exports it. **Nothing about the module changed — the gate changed and silently reclassified it**,
then invited someone to delete a still-accurate exception.

**Why I did not just clear the warning.** That is the trap. Deleting the entry would have hidden a
genuinely dead module permanently. The failure direction matters: a false positive is loud and
gets argued with; a gate that quietly stops asking gets believed.

**The discriminator**, checked against the three modules that rule was written for:

| module | re-exported by its package? | verdict |
|---|---|---|
| `core/foundation/durable_reconcile.py` | no | genuine tool |
| `core/foundation/migrate_to_sqlite.py` | no | genuine tool |
| `core/recall/pack_replay.py` | no | genuine tool |
| `core/state/session_recovery.py` | **yes** | library with a stub |

4 of 4. **Risk:** if some genuine tool is also re-exported by its package, it would return to the
unwired list — a *loud*, easily-corrected failure, not a silent one. 4 pins, RED at `5df699d`.

**Also in this commit:** `core/comm/runner_lib.py`'s exception was removed — genuinely stale. Its
own text said "UNWIRE-WHEN: a runner imports the factory", and `scripts/kimi_chat.py:41` now does,
reached from `scripts/bifrost_runner_kimi.py:52`. Exceptions 18 → 17.

---

## 3. The ledger transition — the one worth your attention (`3dca734`)

**What.** `CLAIMED -> VERIFYING` is now a legal transition.

**Why it was needed.** Four entries were completion records misfiled as proposals. `DONE` was
reachable only through `VERIFYING`, `VERIFYING` only through `IN_PROGRESS`, and `IN_PROGRESS` is
serialized one-at-a-time (held by T086). Closing four week-old deliveries meant faking four
IN_PROGRESS events. The only reachable terminal was `ABANDONED` — which asserts the intent *died*
when it was *delivered*, and would drop four commits of receipts out of the record.

**This is not a new idea; it is the same fix the file already made once.** `task_ledger.py:80`
records the precedent in its own words: *"16 FALSE in_progress events in an audited ledger purely
to reach a legal state. A ledger you cannot cut honestly is a ledger that grows."* That fix added
`PARKED` as reachable from `CLAIMED`. This adds `VERIFYING`, because verification is literally the
work being done — checking a claimed sha against the commit.

**Why I judge it safe, and what would make me wrong:**

- The evidence bar did not move. `done` still refuses without a commit **AND** a verification
  record ("no proof, no close"). Pinned as L2.
- `APPROVED -> VERIFYING` is still illegal, so a fresh proposal walks the whole lifecycle. Pinned
  as L4.
- The serialize gate is untouched — it tests `to == IN_PROGRESS` specifically, so the receipt path
  never takes a slot. T086 kept the slot throughout. Pinned as L3.
- 5 pins green, plus all 39 tests across `test_task_ledger`, `test_ledger`, `test_t083_c5_parked`
  and `test_proposed_decay`.

**The honest risk:** this makes it *possible* to close a task without ever having marked it
in-progress. A seat that wanted to skip the lifecycle could claim → verify → done in three calls.
It would still need a real commit sha and a verification string, so the lie would be recorded and
attributable — but the path exists now where it did not before. **If you dislike that trade, revert
`3dca734`**; the four closures in §4 would need re-doing another way, and nothing else depends on it.

---

## 4. What changed in the ledger

**Closed on verified receipts** — for each, I read the commit message and matched it to the entry:

| entry | sha | what the commit actually says |
|---|---|---|
| T110 | `08f6016` (+`c2244b6`) | per-model pricing, cache-aware, UNPRICED state |
| T111 | `31e6737` | per-incarnation lane cursor, with the inheritance guard |
| T112 | `c94e1f4` | oversize tool payloads spill to blobs |
| T113 | `2cc5dc6` | check_advertised_verbs |
| T133 | `f419596` | mail states load-bearing, M1–M6 (44 pins green) |

Three of those four had **titles naming a different T-number than their own id**. I recorded the
mismatch in each `verified_by` rather than quietly tidying it. The real T115 (an unrelated
faithfulness diagnosis) is untouched and still `proposed`.

**Minted BEFORE closing anything**, because closing a parent without re-filing its named
follow-ups is exactly how work disappears:

- **T135** — kimi-k3 and sol have no rate in PRICES; cost-aware routing cannot price those lanes
- **T136** — deepseek's open question on the read-only cursor inheritance drain window
- **T137** — MCP twin for `bifrost_fetch` (5 known CLI↔MCP gaps)
- **T138** — T133's M6 residual: harness receipts are green-by-pin, never proven green-by-run
- **T139** — the ledger receipt path itself (§3)

**Abandoned as ABSORBED — and only where the author declared it**, each pointing at the LIVE
successor rather than at another tombstone:

- **T036, T037** → T088. T072 says verbatim *"Supersedes/absorbs proposed T036+T037"*.
- **T072** → T088. T088 says verbatim *"Absorbs T072 + T036 scope"*.

**What I did NOT do, and why.** The census proposed that **T108 absorbs T036/T037/T072**. I read
T108's full text: **it declares no absorption anywhere**. That merge was the analyst's inference,
not an author's declaration, so I left it for you.

I also **did not execute the UI chain** (T033 / T060-M7 / T079 → T098), although T098 *does*
declare it verbatim. The reason is a hazard the census did not flag: **T098 is itself on your
"never started, needs a decision" list.** Absorbing three *approved* entries into a program whose
own existence is an open question would mean that if you abandon T098, three live entries go with
it. That merge should happen after you rule on T098, not before.

**Undo for §4 specifically:** `state/coord/tasks.json` is version-controlled, so
`git revert 3dca734` restores the pre-consolidation ledger wholesale. To undo one entry only, edit
its `status` back in that file — every transition also left an event, so the history survives either
way.

---

## Still yours to decide (I deliberately did not)

1. **T088's naming/display-name half** — its own entry, or folded into T108?
2. **T003 / T005** — small shipped-UI fixes, approved six weeks ago, untouched. Still wanted?
3. **The eleven never-started design programs** — T020, T028, T032, T041, T051, T085, T090, T092,
   T098, T103, T105. These need a decision, not an analysis. T098 in particular gates the UI merge
   above.
4. **T047** — the census argues it deserves *promotion*, not consolidation: every entry in the
   lane/cursor/mis-delivery family exists because dual-write is still live. Retiring the legacy
   stream removes the class. I agree with that reading and did not act on it.

---

## Test state, stated plainly

The suite has **23 failures at HEAD**. I checked whether any are mine by running the same file set
in a throwaway worktree at `957cbb3` (the commit I booted on): **24 failures there.** Failures move
in *both* directions between runs, which is the signature of flakiness, not regression.

Three candidates failed at HEAD but not at baseline. Run in isolation:

- `test_t060_n0_shadow_router` → **passes**  (suite interference)
- `test_t078_w3_mcp_door` → **passes**  (suite interference)
- `test_runner_gemini_pins::test_p3` → fails on a 15-second **subprocess timeout** launching
  `bifrost_runner_gemini.py`, which the incoming handoff already named as known-failing from
  another seat's mid-flight code (`d11ffe6`)

**Conclusion: zero regressions attributable to this session's changes.** My own new pins — 9 + 4 + 5
— are all green, as are the 44 T133 pins and the 39 ledger tests.

A caveat I will not paper over: a clean full-suite baseline was **impossible** to take. The
worktree at `957cbb3` cannot even collect three test files, because the working tree depends on
untracked files from other lanes. The comparison above is the best available, not a perfect one.
