# Teardown card: RECALL (how knowledge reaches an agent at the right moment)

Date: 2026-10-13. Seat: Vandor (claude), a read-only subagent of the "deconstruct the house" run.
Method: `teardown-card.md` (draft v1), all eight rows, every claim labelled, loop altitude per
`docs/pillar-analysis-method.md`.
Scope: boot's lesson section, `recall "<words>"`, `recall-at` and the hooks that fire it before
edits and commands, plan-time recall, the funnel and its counters, and the lesson lifecycle
(votes, anti-patterns, benching, graduation). Code is `core/recall/*` plus the doors that call it.

**What I did NOT change.** I made no edits to house files. I ran no boot, learn, note, vote, curate
`--apply` or counters `--fold`. Three side effects I could not avoid, stated so nobody mistakes them
for organic traffic:
(a) every `recall_at` call, including the CLI `recall-at` and `recall-bench` (which are read verbs),
appends one row to the temp-folder silence log (`_record_outcome`, `at_action.py:147`). My probes
added roughly 60 rows.
(b) the user-level PreToolUse hook fired on my own ~35 shell calls. It bumped the `surfaced`
counter on about 40 lessons and wrote injection-ledger rows. My commands are visible in today's
`injections` output.
(c) I did not cast `recall-feedback` votes, because this run is read-only. That is itself a finding
(see Loop L4): an auditor who cannot write cannot close the credit loop.

---

## The picture in one paragraph (for Daniel)

Recall is the house's **prefetcher**. A CPU prefetcher watches the addresses a core is about to
touch and pulls the right cache lines in *before* the load instruction needs them. Recall does the
same with lessons:
- **Boot** is the cold-start prefetch: it loads a working set when a seat starts.
- **recall-at** is the hardware prefetcher keyed on the *address* of the next action (the file path
  or shell command).
- **Plan recall** is a hint at the start of a turn.
- **The funnel** is the performance-counter block (impressions, hits, useful prefetches).
- **The curator** is the replacement policy: it evicts lines that are fetched but never used.
- **Graduation** is moving a check out of microcode into fixed-function hardware: the rule becomes
  a gate and no longer needs reminding.

Prefetchers are judged on two numbers: **accuracy** (of what I fetched, how much got used) and
**coverage** (of the misses that happened, how many I prevented). Hold onto those two words; the
whole card is about them.

**Thesis (one sentence).** The counters are excellent and keep multiplying, but four of the six
wires that should carry their readings back into behaviour are cut in production:
- two by silent wiring defects that no instrument shows,
- one by a scan horizon that a firehose has shrunk to hours,
- one by a hand-crank nobody has turned in 33 days.

---

## Row 1: Purpose

- **What it is for.** Put the few lessons that matter in front of an agent at the moment it acts,
  and say nothing otherwise. **observed**: `at_action.py:1-24` (module docstring: "read the right
  knowledge AT THE MOMENT of action ... SHOW NOTHING unless it clears a relevance floor"); `AGENTS.md`
  "Before you EDIT a file or run a command (recall-at-action)".
- **For whom.** Every seat (claude, deepseek, codex, kimi, sol, DSH-harness seats). There are three
  harness adapters plus an external contract. **observed**: `agent/harness/actions.py:1-27`
  (claude / cursor / DSH share one `recall_block`); `core/recall/actions.py` docstring (external
  consumers); `agent/harness/hooks/codex_pretooluse.py:87`.
- **The outcome that would make it worth keeping.** Agents *prefer* the store because it stops them
  failing (Daniel's success bar, quoted in `_log_outcome_stage`, `at_action.py:1408-1410`: "you prefer
  what stops you failing, not what rescues you"). In prefetcher terms that is **coverage**
  (prevented misses), not only **accuracy**. **observed** (the docstring); **inferred** (the mapping).

## Row 2: Observables (what we can see without trusting its self-description)

All numbers below are from today's live house (2026-10-13, about 13:20 UTC).

| what | value | where it came from |
|---|---|---|
| corpus | 1,624 lessons; 1,577 tracked by counters; 29 ghost counters | `py agent_cli.py stats --days 14`, `triage` |
| impressions all-time | 28,847 surfaced | `stats` |
| explicit votes | useful 509, noise 39 (judged 548 of 28,847 = 1.9%) | `stats` |
| automatic "helped" credits (fail-then-success flips) | 189 all-time | `stats` |
| value triage | protect 406, cost-without-return 926, noise-voted 12, dormant 76 | `triage` |
| recall-at calls, last 24 h | 6,288 calls: 631 fired, 5,657 silent (89%); silent split: excluded (already shown / self-echo) 5,186, below floor 376, failed faithfulness check 92, empty query 3 | `stats --silence` |
| push cost, last 24 h | 633 injections, about 285,000 tokens | `injections` |
| answer-key bench | rank-1 hit 5 of 18; top-5 hit 10 of 18; **abstained 0 of 6** when silence was right; right answer reachable at all 15 of 18 | `recall-bench` |
| prevention contrast, durable 7 days | first-try success 97.6% with a lesson shown (n=2,205) vs 97.3% without (n=15,474); lift +0.26 points | `at_action.durable_outcomes` → `_contrast` (stateless XREAD, checked `core/foundation/ledger.py:156-158`) |
| flip credit by join axis | coarse 29, exact 9 | same stream |
| lifecycle state | benched 56, graduated 3, tagged anti-pattern 56 | direct read of `LearningStore` |
| curator queue | 369 bench candidates, 5 unbench, 18 ghosts to prune, 11 credited ghosts kept | `recall-curate` (report only) |
| last curator apply | bench stamps dated 07-08 (3), 08-01 (48), 08-07 (3), 09-10 (2); **none since 2026-09-10** | `benched` field timestamps |
| recall-at latency | first call in a process 506 ms; warm call 153 ms; fresh CLI process 0.82 s wall; raw cache read 9 ms | `time.perf_counter` around `recall_at`; `time py agent_cli.py recall-at` |
| cache file | 3.5 MB, 1,540 items, 1,120 with a parsed "Use when" trigger, **2** with mined trigger terms, 3 bench probes | read of `%TEMP%\akashic_recall\lesson_items.json` |

**Lived experience (observed, my own session; relevance judged by me, so inferred).** The
recall-at hook fired on about 17 of my shell calls and showed about 40 lessons:
- About 15 were on target. Two of them *predicted defects I then found*:
  - `dsh_v27_join_break_prejoined_target_evaporates_join` fired just before I found boot's dead
    credit join.
  - `advisory_prints_evaporate` fired just before I found the curator's print-only nudge.
- About 15 were off target (identity, shader, Discord lessons on generic `py -c` calls).
- About 10 were tangential.

None of this is recorded anywhere, because I am read-only and cannot vote.

## Row 3: Mechanism (how inputs become what we observe)

The value chain, link by link. Each link has a label and a pointer.

1. **Capture.** `learn` writes a lesson hash to the LearningStore. The convention is a trigger
   phrase, "Use when <symptom>, before <action>: <advice>". **observed**: `AGENTS.md` lines 40-75;
   1,168 of 1,624 recommendations open trigger-shaped (my regex, mirroring `_TRIGGER_RE`,
   `at_action.py:260`).
2. **Project to a cache.** `_project_items` (`at_action.py:336-431`) drops graduated lessons and
   benched lessons (except up to 3 "probes"). It picks ONE field to *show* (claim vs evidence is
   tagged) but matches on all three text fields. Then `_cached_items` (`:434-462`) adds mined
   trigger terms and counters and writes a 120-second disk cache. **observed**.
3. **Build a query from the action.** `_query_from` turns a path or command into words. Words of
   3 letters or fewer, and a stop-list that includes `py`, `git`, `test`, `path`, `file`, are
   dropped (`at_action.py:51-62`, `:633`, `:663`). `cd`/`Set-Location` statements are stripped as
   preamble (`:1045`). **observed**: `cd scripts && py run.py` becomes the query `scripts`;
   `git add -A` becomes an empty query (`recall-at --json`).
4. **Rank.** The shared Ranker multiplies three things:
   - relevance: IDF-weighted word overlap, trigger-aware, and "a trigger may only help, never
     cost" (`:681-729`);
   - importance;
   - recency.

   It is then multiplied by `usefulness_factor`, which is earned from judgments only and is 1.0
   when nothing was judged (`:739-840`). A floor of 0.2 decides silence (`_floor_default`
   returned 0.2). **observed**.
5. **Withhold.** Anti-repeat (already shown this session) and self-echo (you wrote it in the last
   2 h) remove items. **observed**: `:96-130`; 5,186 of 5,657 silences today.
6. **Gate.** A faithfulness check per item (a fabricated or unresolvable pointer is dropped). A
   dissent finder looks for the strongest counter-lesson. **observed**: `:2175-2217`.
7. **Surface.** Lessons are rendered with provenance tags (`worked` = the author's own report,
   `helped` = automatic credit, `useful` = a vote, `probation` = a bench probe), plus an age cue.
   **observed**: `:2288-2337`; the hook output in this very session. Three doors use this:
   - the PreToolUse hook on Bash/PowerShell and Edit/Write/NotebookEdit only. **Not** Read or
     Grep: **observed** in the user-level hook registration matchers.
   - the UserPromptSubmit plan recall (limit 2): `agent/harness/actions.py:121-142`.
   - boot's fixed-budget lesson section: `core/context/relevance_budget.py`, a *separate*
     ranker with a tier ladder.
8. **Influence.** Whether the seat changed what it did. **unknown by design**: the "applied" stage
   leaves no trace unless the seat declares it (`at_action.py:1494-1496`).
9. **Outcome.** The PostToolUse hook resolves every action. Every resolution is logged as a
   "stage" row, in the temp folder and in a durable Redis stream `recall:outcome` with maxlen
   20,000. **observed**: `:1392-1463`.
10. **Credit.** Three channels:
    - `helped`: a target that FAILED and then SUCCEEDED credits whatever was surfaced for it.
      Exact join first, then a coarse fallback (`:1329-1372`).
    - `useful` / `noise`: votes, prompted at wrap time (`agent_cli.py:4479-4480`).
    - `engaged`: a `recall --full` pull (`:948-969`).

    **observed**.
11. **Curate.** The curator benches lessons with 10+ impressions, no credit, and age over 10 days.
    It unbenches on any credit and prunes zero-credit ghosts (`core/recall/curator.py`). It runs
    **only** when someone types `recall-curate --apply`; wrap prints a nudge
    (`agent_cli.py:4705-4714`). Graduation is a manual verb. **observed**.
12. **Back to matching.** Credit feeds `usefulness_factor` at recall-at (through `_with_usefulness`,
    canonical keys, `:583-591`) and at boot (through `relevance_budget._default_credit_fn`,
    *bare* keys, see Loop L2). Mined trigger terms come from credited flips in the newest 2,000
    events (`:603`). **observed**.

## Row 4: First principles (each tested: what evidence or law does it rest on?)

| # | principle | label | rests on | axiom or assumption? |
|---|---|---|---|---|
| F1 | A weak hint at the moment of action costs more than silence (attention is the scarce resource; "context rot"). | observed in design and code | vNext calibration: 59 of 60 lessons injected in 24 h before the floor existed (`20260701_recall-vnext...md:118-120`); field literature cited in the module docstring | **Assumption, well supported.** But the house has not yet achieved it: the bench abstains on 0 of 6 silence moments. |
| F2 | Fire on an observable (the path or command), not on the agent's own diagnosis of relevance. | observed in design | September redesign (`20260905_recall-redesign...md:62-75`, Hollnagel barrier ladder, the "do not interrupt" vest trial p=0.355) | **Assumption grounded in outside evidence.** In-house support is weak: prevention lift +0.26 points. |
| F3 | Zero is not no: absence of judgment is not evidence of noise. | observed | `usefulness_factor` rewrite (`at_action.py:744-836`): exposure decay had *punished relevance*; removing it moved bench rank-1 hits from 1 to 4 of 18 | **Axiom-grade.** It is a law of inference, and the house measured what breaking it costs. |
| F4 | Observability must not steer ranking until the stages are separately observed. | observed | `funnel.py:107-111` ("never feed it back into ranking ... a proxy under optimization pressure Goodharts"); `_log_outcome_stage` docstring | **Axiom** (Goodhart's law) applied deliberately. |
| F5 | A silence must be a recorded row with a reason. | observed | `_record_outcome` reasons `fired / empty_query / floor_silent / excluded_silent / unfaithful_silent / error_empty` (`at_action.py:2228-2252`) | **Axiom-grade.** An unrecorded silence is unfalsifiable. |
| F6 | Recall must never brick the action (fail open). | observed | `try/except` on every exit; `error_empty` keeps "could not look" apart from "nothing relevant" (`:2264-2285`) | **Operator value** (work outranks hints). |
| F7 | A rule that can be enforced belongs in a gate, not a reminder. | observed in design | September redesign S1 "promotion ladder"; repeats ledger: 9 of 28 repeats happened *with recall firing* (`stats`) | **Assumption, well supported.** Not built: `refusal_shape` was found nowhere in `core/`, `agent/` or `scripts/`. Graduation total is 3 of 1,624. |
| F8 | Lessons carry their own trigger, so matching on the trigger is precise. | observed | 1,120 of 1,540 cached items parse a trigger; bench: 3 of 18 right answers are unmatchable and ambiguous triggers cap rank-1 at 15 of 18 | **Assumption, partly holding.** The trigger names a *situation*; the query sees only *words in a path or command*. |
| F9 | "After warm-up a call is a ~1ms file read + rank" (`at_action.py:27`); the warm-cache file read is "~1ms" (`:65`, `:442`). Corrected at review: this row once said the docstring priced the whole call at 1 ms. It prices the **file read**; the rank is never priced. | observed as a claim | the file read measured 9 ms; the whole warm call measured 153 ms (506 ms first call, 0.82 s CLI) | **Trap 1: a stale measurement dressed as a design fact.** A 1 ms read is claimed and 9 ms is measured. The cost that matters, the whole call, was never priced in the docstring: per-call corpus-wide re-tokenizing is most of it (profile: IDF weights 129 ms, ranker 107 ms, dissent 51 ms). |

## Row 5: Capabilities (what you would need to HAVE to build or run it)

- A durable key-value and stream store with a file fallback (Redis on 16379 plus a FileStore).
  **observed**: `create_store`, `HybridStore` in boot (`agent_cli.py:379-389`).
- A harness that can inject text **before** a tool runs and report **after** it: Claude Code
  PreToolUse `additionalContext`, PostToolUse / PostToolUseFailure, UserPromptSubmit,
  SessionStart. **observed**: the hook registrations, `claude_pretooluse.py:15-26`.
- Deterministic information retrieval: tokenizing, IDF, a ranker with a relevance seam, and a
  faithfulness check. No model on the hot path. **observed**: `core/primitives/ranker.py:69-105`,
  `faithfulness.py`.
- A **corpus discipline** that people actually follow: trigger-phrased lessons with failed
  attempts recorded. This is a social capability, not code. **inferred** from 1,168 of 1,624
  trigger-shaped lessons and the 203 lessons written in the last 30 days (`stats`).
- An **answer key**: labelled moments with a known right lesson (`recall-bench`, 25 of 40 seeded).
  **observed**.
- **Human judgment** for curation and graduation (the triage docstring keeps selection human).
  **observed**: `funnel.py:121-124`.
- Time: the corpus grew from about 60 lessons (July calibration) to 1,624 (today). **observed**:
  the vNext doc and `stats`.

## Row 6: Required steps (build order from nothing; what blocks what)

1. Lesson schema and write door, with the trigger convention.
2. Store and keyword query (`recall "<words>"`).
3. **Answer key and bench (recall@k, abstention).**
4. Boot assembly under a fixed budget.
5. Hook wiring and query construction from the path or command.
6. Floor, anti-repeat and self-echo (precision before volume).
7. Impression counters and the injection ledger (what pushing costs).
8. Outcome join (fail-then-success credit) and stage logging.
9. Votes at the reflective moment (wrap).
10. Credit into ranking.
11. Curation and graduation.
12. Promotion ladder (reminder to gate).

Critical path: 1 → 5 → 6 → 8 → 10. Nothing in 10 or 11 can be judged without 3.

**inferred, from the house's own history.** This house built step 3 *last*:
- `bench.py` docstring: "the first number recall has ever been judged on".
- The fence `W0.3` dates from the late-September context-system round.

That was about three months after the floor was calibrated on n=1 credited pair
(`20260701_recall-vnext...md:103-111`). Several of today's failed predictions are tunings made
without a bench, so in a rebuild the bench moves up to step 3, which is why it sits there above.

## Row 7: Invariants and failure modes

| invariant | status today | what a break looks like from outside |
|---|---|---|
| I1 Fail open | **holds** (observed: every exit guarded) | n/a |
| I2 Silence beats fabrication (faithfulness per item) | **holds** (observed: 92 unfaithful silences in 24 h) | a pointer that does not resolve, shown as fact |
| I3 One counter key per lesson (`recall:use:learn:experiment:<name>`, `at_action.py:529` prefix plus the lesson's canonical source) | **BROKEN at boot's reader** (observed, see V1) | nothing at all: numbers look normal, proven lessons simply do not climb. The worst kind of break. |
| I4 Graduated and benched lessons stay off the surfaces ("cache/boot", `curator.py:11`, `learning_store.py:1212`) | **holds at recall-at, BROKEN at boot for benched** (observed, see V2) | a benched lesson re-appears in a boot briefing |
| I5 Measurement never steers ranking | **holds** (observed: the prevention and value rates are read nowhere in ranking) | n/a |
| I6 A silence is a row with a reason | **holds** (observed: `stats --silence`) | n/a |
| I7 The trend instruments cover the window they print | **BROKEN** (observed, V6 and V7) | a 14-day chart of zeros; a "durable" stream that forgets after 7 days |
| I8 Bench probes rotate | **BROKEN by coupling** (observed, V9) | the same 3 benched lessons probe forever; the other 53 never get a second look |

Failure modes seen in the data:
- **Banner blindness.** 9 of 28 recorded repeats happened while recall had fired: a *reading*
  failure, not a targeting one. **observed** (`stats` repeats). This is a floor, not a rate.
- **Verb blindness.** The query cannot see `cd`, `git`, `rm`, `mv` or flags. **observed** (V4). So
  the hazards that live in a command's *verb* reach recall only through nouns, or not at all.
- **Coarse-join credit.** 29 of 38 durable flip credits came through the coarse fallback.
  **observed**. Whether those are true joins is **unknown** (not audited).
- **Hot-path cost.** Each recall-at call costs 150-500 ms in-process. **observed**. That it delays
  every Bash/Edit call by about that much is **inferred** from the harness hook model (the
  context must exist before the tool runs). I did not measure it from the harness side.

## Row 8: Verification (predictions that could fail, the test, the result)

| # | prediction (and whose) | cheapest test | result |
|---|---|---|---|
| V1 | Boot multiplies proven lessons up by their credit (`relevance_budget.py:20-22`, "funnel credit joins MULTIPLICATIVELY") | call boot's own `_default_credit_fn` for `bootstrap_mcp_handoff_session` (helped 5) and `bifrost_mesh_comm` (helped 2, useful 3) | **FAILED.** The bare key returns `{}`, giving factor **1.0**; the canonical key would give **1.42**. 1,577 counter keys exist, **0** bare ones. Boot looks up `lesson["experiment_name"]` (`relevance_budget.py:114`), so it reads `recall:use:<name>`; counters live at `recall:use:learn:experiment:<name>` (the `recall:use:` prefix is `at_action.py:529`). |
| V2 | Benched lessons stay out of boot (`curator.py:11`) | feed each of the 56 benched lessons to `select_within_budget` with a task built from its own category | **FAILED.** 56 of 56 admitted. Only `is_graduated` is imported (`relevance_budget.py:143-149`, `learning_loader.py:131-132`). |
| V3 | A generic filler prompt stays silent (vNext probe battery) | `recall-at --command "lets continue working on the system"` | **HELD.** "nothing relevant". |
| V4 | A `cd`-into-subfolder command surfaces the protected lesson `bash_cd_into_subdir_wedges_all_local_tools_for_session` (helped 3) | `recall-at --command "cd scripts && py run.py" --json` | **FAILED.** Query was `scripts`; 0 shown, 0 above floor. `git add -A` produced an **empty** query. |
| V5 | A warm recall-at call is about 1 ms (my reading of `at_action.py:27`, "a ~1ms file read + rank"; corrected at review: the docstring prices the file read, not the call) | time two in-process calls; time the CLI; time the cache read alone | **FAILED, for the claim the docstring makes too:** the file read it prices at ~1 ms took 9 ms. The whole call, which the docstring never priced, took 506 ms then 153 ms in-process and 0.82 s from the CLI; corpus-wide re-tokenizing per call is most of it (cProfile). |
| V6 | The 14-day flip trend shows 14 days (`funnel.trend`) | check how far back `event_log.scan(limit=5000)` reaches; compare with the durable outcome stream | **FAILED.** The scan reaches only back to 06:59 today (6.4 h; 4,558 of 5,000 events are file `touch` rows). The durable stream shows flips on 10-06 (1), 10-07 (5), 10-08 (1), 10-10 (4), 10-11 (1), 10-12 (13) that the trend prints as **0**. The renderer does add one caveat line. |
| V7 | The durable outcome stream holds "roughly two months" (`at_action.py:247`) | read the stream's oldest row | **FAILED.** Oldest row is 2026-10-06 03:35, about 7 days. Real volume is 400-6,200 rows a day, not "a few hundred". |
| V8 | Credited flips sharpen matching ("mined triggers", vNext loop 2) | count cache items with `trigger_terms`; measure how far back `recent(limit=2000)` reaches | **FAILED in effect.** 2 of 1,540 items carry mined terms; the window reaches 2.3 h back (5 flips, 1 credited). |
| V9 | If the curator stops, the probe rotation freezes (the code's own warning, `at_action.py:316-320`) | compute `_bench_probe_set` now | **HELD**, and it is a bad outcome. The 3 probes are all benched 2026-07-08 and have probed ever since. |
| V10 | The curator has run within its own 10-day age gate | newest `benched` timestamp | **FAILED.** Newest is 2026-09-10 (33 days ago), with 369 candidates and 5 unbenches waiting. |
| V11 | The bench abstains when silence is right | `recall-bench` | **FAILED.** 0 of 6. |
| V12 | The outcome sink is `<state dir>/recall_outcomes.jsonl` (`at_action.py:87-89`) | print `_OUTCOME_DIR`; list the folder | **FAILED, harmless.** `_OUTCOME_DIR` is redefined at `:990`, so the sink lives in `outcome/`, next to the per-session files `prune_state` sweeps. It survives only because it is appended to constantly. |
| V13 | A graduated rule (`concurrency_c0_git_guard`) does not resurface for `git add -A` | `recall-at --command "git add -A"` | **INCONCLUSIVE.** Nothing surfaced, but the query was empty, so silence was guaranteed either way. This test could not fail for the right reason, which is trap 4 in miniature. |

---

## Loop altitude (does the signal flow back?)

| loop | from → to | status | evidence |
|---|---|---|---|
| L1 | credit → recall-at ranking | **closed** | `_with_usefulness` reads canonical keys at cache build (`at_action.py:583-591`); cache items carry `_use` |
| L2 | credit → boot ranking | **OPEN (silent wiring defect)** | V1 |
| L3 | curation → surfaces | **OPEN at boot** (V2); **hand-cranked at recall-at** (V10); probe rotation frozen as a result (V9) | `curator.py`, `agent_cli.py:4705-4714` (nudge is a print) |
| L4 | seat experience → votes → ranking | **partly closed.** Votes went from 4 useful / 0 noise in July to 509 / 39 today, but cover 1.9% of impressions and are self-selected (93% useful). A read-only seat (this one) cannot vote at all. | `stats`, vNext doc line 26 |
| L5 | outcomes → matcher (mined triggers) | **OPEN (starved)**: 2.3 h horizon | V8 |
| L6 | outcomes → prevention measurement | **designed-open on purpose** (measure only, never steer) | `_log_outcome_stage` docstring. This one is a fence, not a defect. |
| L7 | repeats → reminder-to-gate promotion | **OPEN (not built).** 3 graduations ever, all hand-made; `refusal_shape` absent. | lifecycle read; grep |
| L8 | funnel trend → operator | **OPEN (instrument blind past 6.4 h)** | V6, V7 |

## The five traps, where I saw them

1. **False first principles.** "a ~1ms file read" (V5: 9 ms measured; the 153 ms call was never priced), "two months" (V7), "benched leave boot" (V2), "boot
   joins credit" (V1). Each is a docstring sentence that was true, or intended, when written and
   was never re-measured. `AGENTS.md:98` still tells every agent that "lessons shown often but
   never useful decay on their own". That decay was deliberately removed on 2026-10-02
   (`at_action.py:833-836`), and its replacement, benching, has not run since 09-10.
2. **Chesterton's fence.**
   - **Anti-repeat silence.** It produces 5,186 of 5,657 silences (92%; 82% of all calls). That
     looks like a target, but it exists so one lesson does not repeat on every call of a long
     session. Leave it.
   - **The four-letter word filter.** It blinds the verb, but it exists to stop `py`, `git` and
     `the` from matching half the corpus. Do not delete it; add a separate channel.
   - **The hand-cranked curator.** It may be a deliberate human gate (`funnel.py:121-124` keeps
     selection human), so the proposal below makes the crank *visible* first. It does not automate
     it by default.
   - **Prevention as observation only.** It is a Goodhart guard. Keep it.
3. **Reductionism.** The frozen probes (V9) are not a defect in the probe code. The probe code is
   correct and even predicts the failure. The behaviour lives in the coupling between the probe
   and a curator that stopped.
4. **The map is not the territory.**
   - V13: a "pass" that could not have failed.
   - The 14-day trend: a chart of confident zeros.
   - Boot's credit join: a design document describing a wire that is not connected.
5. **Goodhart.**
   - The value rate is guarded well; the house prints it as coverage, not quality.
   - `helped` credit is still association. 76% of it comes through the coarse join, and a lesson
     earns it by having been *on screen* when a retry succeeded.
   - Today's 285,000-token push cost is inflated by today's own fan-out, including this run (my
     commands are in the ledger). So any before/after comparison taken today measures the
     auditors as much as the house.

---

## Great Sage report

> **Notice.**
> - Boot looks up credit under the bare lesson name (`recall:use:<name>`), but all 1,577 counters
>   live under `recall:use:learn:experiment:<name>` (`at_action.py:529`). Every lesson gets a
>   neutral 1.0 at boot; a proven one should get 1.42 (`relevance_budget.py:97-114`, V1).
> - Boot admits benched lessons: 56 of 56 (`relevance_budget.py:143-149`, V2).
> - The curator last applied on 2026-09-10. 369 bench candidates are waiting, and the three bench
>   probes have been the same lessons since 2026-07-08 (V9, V10).
> - The flip trend scans the newest 5,000 events, which reach 6.4 hours back, so it prints zeros
>   on days that had flips (V6). The "durable" outcome stream keeps 7 days, not two months (V7).
> - Mined triggers come from a 2.3-hour window, and 2 of 1,540 lessons have any (V8).
> - The matcher drops every word of three letters or fewer, so `cd` and `git add -A` produce empty
>   or noun-only queries (V4).
> - The docstring prices the warm file read at ~1 ms; it takes 9 ms. The whole warm call takes
>   153 ms, a cost the docstring never states (V5).
> - The bench: rank-1 hit on 5 of 18 moments, top-5 on 10 of 18, abstained on 0 of 6 (V11).
> - Prevention lift is +0.26 points on a 97% first-try-success baseline.
>
> **Analysis.**
> - The house builds instruments faster than it re-reads them (from V1, V2, V5, V7: four docstring
>   claims, none re-measured).
> - The two quiet defects, the boot key and the boot bench filter, share a root: boot has its own
>   ranker (`relevance_budget.py`) beside recall-at's, and fixes landed in one and not the other.
>   The canonical-key migration (S2a) and the bench filter both reached `at_action.py` only (from
>   V1, V2 and the two-ranker layout).
> - The firehose that makes the house observable (4,558 `touch` rows per 6 hours) is the same
>   thing that shrank the trend and mining horizons. Success in one organ starved another (from
>   V6, V8).
> - Recall's measured weakness is **coverage of verbs and abstention**, not accuracy of nouns
>   (from V4, V11, and 9 of 28 repeats being reading failures).
>
> **Unknown.**
> - I did not run boot (forbidden). I tested its selector functions directly, not the rendered
>   briefing.
> - I did not audit whether the 29 coarse-join credits were true joins.
> - I did not measure how long the hook delays a tool from the harness side.
> - I did not exercise the codex, cursor and DSH adapters or the MCP door.
> - `knowledge_map`, `lookback`, `forge`, `anchors`, `staleness`, `shadow_shelf` and
>   `precision_audit`: docstrings only.
> - Whether wraps happened since 09-10 cannot be read, because the event scan horizon is 6.4 h.
> - The "applied" stage (did a seat change course?) is unobservable by design.
> - Search boundary: `core/recall/*`, `core/context/{relevance_budget,learning_loader}.py`,
>   `agent/harness/actions.py`, the Claude hooks, `agent_cli.py` doors, the live store, the
>   temp-folder state, and the `recall:outcome` stream.
>
> **Proposal** (smallest first; nothing is deleted; each states why the part exists):
> 1. *One line.* Boot's credit lookup uses the canonical key, with a pin test on a canonically
>    keyed counter. Exists because: R1-b promised that proven lessons climb at boot.
> 2. *One line.* Boot skips benched lessons, matching graduation. Exists because: the curator's
>    contract says benched lessons leave boot.
> 3. *One line.* `warm_cache` builds through the same path as `_cached_items`, so the first
>    120 seconds after boot keep the mined triggers. Today `at_action.py:494` skips
>    `_with_mined_triggers`.
> 4. *Prose only.* Correct the five stale claims:
>    - `at_action.py:27`, `:65`, `:442` ("~1ms" read: measured 9 ms; and price the whole call, 153 ms)
>    - `:247` ("two months")
>    - the dead first `_OUTCOME_DIR` at `:89`
>    - `relevance_budget.py:154` ("noise decay → 0.5x")
>    - `AGENTS.md:98` ("decay on their own")
> 5. *Instrument.* `stats` prints "last curator apply: N days ago, M waiting". Then Daniel
>    chooses: schedule `--apply` (deterministic, reversible, never a delete) or keep it a human
>    gate. Either way the crank's age stops being invisible.
> 6. *Small slice.* The trend and the trigger mining read flips from the `recall:outcome` stream
>    (rows with `flipped`), not from the newest N rows of a firehose that is 91% `touch`. Size
>    that stream for the window it claims (raise maxlen or downsample).
> 7. *Small slice.* Compute IDF weights and token sets once, at cache build, not on every call.
>    That is 129 + 107 ms of the 153 ms; the target, about 20 ms, is an *estimate*.
> 8. *Design conversation.* Give recall a command-shape channel (the command head plus flags) so
>    verb hazards can match. Or decide they belong to gates, and build the September S1
>    promotion ladder. Abstention at 0 of 6 belongs in the same conversation.
>
> **Verification.** 13 predictions, all run read-only: 2 held (V3, V9; V9's holding is itself
> the defect), 10 failed (V1, V2, V4, V5, V6, V7, V8, V10, V11, V12), 1 inconclusive (V13).
>
> **Proceed?** YES / NO. Every proposal waits for Daniel. Proposals 1-4 are one-line or prose
> fixes; 5-7 are small slices; 8 is a design conversation.
