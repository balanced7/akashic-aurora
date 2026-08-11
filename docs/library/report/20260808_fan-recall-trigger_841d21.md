---
akashic_id: art_20260808_fan-recall-trigger_841d21
akashic_sha: 167528298a4b
schema_version: 1
status: current
type: report
date: 2026-08-08
title: fan-recall-trigger
gist: "# FAN: the recall-at TRIGGER, iteration 1 -- 2026-08-08 Status: current | Type: report | Five branches, five output types | 0.0995 USD Pre-r"
visibility: fleet
body_type: markdown
seats: []
category: [recall]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-08T17:08:16"
updated: "2026-08-08T17:08:16"
---
<!-- GENERATED PROJECTION of art_20260808_fan-recall-trigger_841d21 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# fan-recall-trigger

# FAN: the recall-at TRIGGER, iteration 1 -- 2026-08-08

Status: current | Type: report | Five branches, five output types | 0.0995 USD

Pre-registration committed BEFORE any answer was read:
research/in-flight/prereg-recall-trigger-fan-2026-08-08.md
Evidence dossier: research/in-flight/recall-trigger-misses-2026-08-08.md

## THE HEADLINE, and it inverted the hypothesis

I opened believing the trigger was too weak -- that it keys only on file path and shell
command and therefore fails to FIND the right lesson. The measured outcome counters say
otherwise:

    7 days: 5851 calls | 1673 fired | 4178 silent
            excluded_silent  3309   (79% of silences)
            floor_silent      863   (21%)
            empty_query         6

    24h:    595 calls | 136 fired | 459 silent
            floor_silent      249
            excluded_silent   210

excluded_silent means the lesson PASSED the relevance floor and was then discarded by an
exclusion rule -- anti-repeat (shown once already this session) or self-echo (authored by
the calling agent within 2h). Relevance is finding things. Suppression is throwing them away,
3309 times in a week.

This explains the sharpest case in the dossier exactly: I wrote a lesson and violated it two
commits later, and self-echo would have muted my own lesson for being mine and recent.

NOT YET SPLIT: excluded_silent covers anti-repeat AND self-echo together. They need different
fixes and the counter cannot currently tell them apart. That is the next measurement.

## Predictions, scored

- P1 CONFIRMED, and undersold. Path/command are the query source, but the pipeline also has a
  domain filter, a per-session seen-set, a self-echo window, a usefulness multiplier and a
  faithfulness gate. I described a two-signal system; it is an 18-step decision path.
- P5 DIED, as pre-registered. ADVERSARY landed real blows, including the one I named as its
  likely best: a smarter trigger earns more trust and so fails harder. Its other two are
  worth more than my prediction was -- 45 noise vs 61 helped means surfacings are passively
  TOLERATED not harmful, and nothing records whether the actor READ any surfacing, so 5.2 pct
  may be an attention number rather than an accuracy number.
- P2/P3/P4 pending read at time of writing.

Note the adversary attacks make-the-trigger-smarter. The measurement points at a different
fix -- stop discarding what was correctly selected -- which adds no inference and no opacity,
so its strongest objection does not reach it. The adversary killed a plan before it was built.

---

## BRANCH MECHANISM (at_action.py + hook)

evidence=own | 31542 prompt tokens

FINDINGS:
1. Hook ignores tools not in (_SHELL_TOOLS + _FILE_TOOLS) — Bash, PowerShell, Edit, Write, NotebookEdit — returning 0 immediately and silencing everything. (claude_pretooluse.py:242-243)
2. Duplicate payload check: an atomic marker prevents a second identical hook invocation within ~3s from proceeding, returning 0 silently. (claude_pretooluse.py:244-245, _dedup_should_skip 47-75)
3. Scope guard: file tools are in-scope only if `file_in_scope(file_path)` is true; shell tools only if `shell_in_scope(cwd, command)` is true; out-of-scope returns 0 and no recall. (claude_pretooluse.py:246-247, _in_scope 78-91)
4. Git-staging veto for Bash: if the command matches a blanket git operation, the action is denied; recall never runs. File-tool lock veto: if a peer holds an advisory lock on the target path, denied. Only allowed actions proceed to recall. (claude_pretooluse.py:248-254)
5. Environment kill switch: if `AKASHIC_RECALL_AT_ACTION=0`, `_recall_context` returns empty string, no lessons fetched. (claude_pretooluse.py:114)
6. If the tool input has neither a `file_path` nor a `command`, `_recall_context` returns empty string early, before any recall call. (claude_pretooluse.py:119-120)
7. Per-session “seen” set (lessons already surfaced this session) is loaded via `load_seen(session_id)` and passed as `exclude_sources` to `recall_at`. (claude_pretooluse.py:126-128)
8. `recall_at` builds a keyword query from the path and/or command: tokens of length >3, lowercased, deduped, minus a fixed stoplist; if the resulting query string is empty, `_lessons` returns no lessons and outcome is “empty_query”. (at_action.py:1418, _query_from 1258-1286)
9. A domain is inferred from path/command (via `infer_domain`); if a domain is determined (not None), the lesson cache is filtered to include only lessons whose domain matches (or are “general” from cross-domain credit) before ranking. (at_action.py:1421, 1338-1347)
10. Lessons are loaded from a TTL disk cache (or store), projected to exclude graduated and non-probed benched lessons; each projected item carries fields: `text`, `trigger`, `trigger_terms`, `source`, `_use`, etc. (at_action.py:1337 _cached_items, _project_items 237-312)
11. Trigger-aware relevance score: `0.6 * overlap(query, trigger+trigger_terms) + 0.4 * overlap(query, text)`, where overlap uses IDF-weighted damped token overlap with a min-hits penalty (damps single common-token matches). (at_action.py:555-573, _trigger_aware_relevance, _damped_overlap 529-552)
12. Ranker blends relevance with (likely) importance and possibly recency; any lesson whose relevance component is ≤ the show-nothing floor (default 0.20, env `AKASHIC_RECALL_FLOOR`) is discarded. (at_action.py:1353-1355)
13. After floor, intra-call source duplicates and items in `exclude_sources` (already shown this session) are silently dropped. (at_action.py:1361-1365)
14. Self-echo filter: lessons authored by the calling agent within `AKASHIC_RECALL_SELF_ECHO_H` hours (default 2) are silently dropped. (at_action.py:1366-1369, _self_echo 1306-1323)
15. Surviving candidates are multiplied by a `usefulness_factor` (boost for helped/useful votes, decay for noise/high-impression-no-credit), sorted, and capped to `limit` (default 3). (at_action.py:1372-1374)
16. Faithfulness gate: each lesson’s text+source is vetted for faithfulness; any unfaithful lesson is dropped. If no faithful lesson remains, the entire recall result is silenced (outcome “faith_rejected”). (at_action.py:1445-1471)
17. Optionally a dissent counter (strongest genuine disagreement with the top lesson) may be added, but only if it passes faithfulness check. (at_action.py:1430-1438, 1454-1461)
18. `render()` formats surviving lessons with provenance tags, locks, counter, and optional escape hint; if the result is empty, the hook emits nothing. Only a non-empty string is passed as `additionalContext`. (at_action.py:1586+, claude_pretooluse.py:102-106, 270-273)

SPECIFIC ANSWERS:
* Input signals to the ranking (relevance calculation): only the query string (tokens from path/command) and each lesson’s `text`, `trigger` (parsed from recommendation), and `trigger_terms` (mined from historically credited flips). IDF weights are derived from the cached corpus. The Ranker may additionally use lesson importance and/or recency (`now`) to produce the final score, but those are outside the relevance function (at_action.py:566,573 for the explicit fields; Ranker code unseen). Session state, history, previous calls, tool name, cwd, and time do NOT enter the relevance function itself; time (`now`) is passed to Ranker but its use is uncertain.

* Silent drops and outcome labels that record them:
  - empty_query: query string empty after token extraction → outcome `"silent"`, reason `"empty_query"` (at_action.py:1487-1489)
  - floor_silent: no lesson’s relevance > floor → outcome `"silent"`, reason `"floor_silent"` (at_action.py:1501-1502)
  - excluded_silent: every above-floor lesson was excluded (anti-repeat or self-echo) → outcome `"silent"`, reason `"excluded_silent"` (at_action.py:1494-1499)
  - faith_rejected: faithfulness check drops all remaining lessons → outcome `"silent"`, reason `"unfaithful_silent"` (at_action.py:1490-1493)
  - error_empty: an exception inside `recall_at` → outcome `"silent"`, reason `"error_empty"` (at_action.py:1523)
  - Hook early exits (wrong tool, out of scope, dedup skip, kill switch, no path/command, denied action) leave NO recall outcome record; they are completely silent to the recall ledger.

* Floor/threshold: each lesson’s `relevance` component is compared to `min_relevance` (default 0.20); if `<= floor`, the lesson is skipped entirely. When nothing clears the floor, the outcome is recorded as “floor_silent” and the surface is empty.

* Line where lesson’s text is matched against the query, and participating fields: the overlap is computed inside `_trigger_aware_relevance`. The exact calls are:
  ```python
  prose = _damped_overlap(text, query, weights)                # at_action.py:566
  return 0.6 * _damped_overlap(trig, query, weights) + 0.4 * prose   # at_action.py:573
  ```
  The `text` used is the item’s `text` field (first non-empty of recommendation/actual/what_tried). The `trig` concatenates the item’s `trigger` (parsed “Use when” clause) and `trigger_terms` (mined from past flips). So the participating fields are `text`, `trigger`, and `trigger_terms`.

REASONING:
I traced the hook’s `main()` to its call to `_recall_context`, then into `recall_at` and `_lessons`. I noted every conditional that prevents lessons from reaching the surface. The decision tree is a sequence of early returns and filters. The ranking inputs are explicit in the relevance function; nothing from session history or tool metadata reaches the relevance scoring (except possibly time via Ranker, which I marked as unseen). The silent drops and outcomes were read directly from the outcome-recording block in `recall_at` and the hook’s early returns. The floor is a hard threshold on the relevance component, not a relative cutoff. The text-match line and fields are from the _trigger_aware_relevance function.

CHECK:
- To disprove the tool-name filter, register a different tool name and see if the hook fires; if it does, the filter is wrong.
- For empty-query silence, craft a tool call with only stopwords in path/command, then check outcome log for “empty_query”.
- For floor, set AKASHIC_RECALL_FLOOR=1.0 and observe that ever lesson stays silent (floor_silent).
- For lesson field participation, modify a lesson’s trigger text to exactly match the query but leave the body text unrelated; the blended score will still rise, demonstrating both fields are used.
- For the hook’s invisible drops (e.g., out-of-scope), the recall outcome log will have no entry for that tool call, showing no recording.

BLIND:
- I cannot see the Ranker’s internals; its blending of importance and recency is unknown.
- The implementation of `infer_domain` and `faithfulness_report` is not provided; I cannot confirm exactly how domain scoping or faithfulness affects which lessons survive.
- The `_cached_items` cache creation path may include graduted/benched filtering changes not fully visible.
- The exact behaviour of the `_dedup_should_skip` atomic file approach under concurrency is untested.
- Whether the `now` parameter influences ranking beyond recency is unknown without Ranker code.

---

## BRANCH AUTOPSY (miss dossier only)

evidence=own | 2174 prompt tokens

FINDINGS:
1. Signal "shell command is `git commit` of a file matching `test_*.py`, and the most recent commit authored by the same operator contains the substring `RED pin`" would have caught M2 (`recall-trigger-misses-2026-08-08.md:56-61`). False positives: any test commit after a commit containing that phrase.
2. Signal "file edit on `agent_cli.py` that touches a line coercively calling `str()` on a list of prompts, and a recent commit (within the last hour) added dict support to the `ask_many` module" would have caught M1 (`recall-trigger-misses-2026-08-08.md:40-45`). False positives: similar coercion edits on that CLI after any future type expansion.
3. Signal "script file about to be executed contains concurrent calls to a paid service and transforms results before persisting them, with no raw-result save before the transform" would catch M3, but only after the code is written; at the described moment of "about to write a harness" the file was empty (`recall-trigger-misses-2026-08-08.md:69-72`). False positives: any script that batch-calls a paid API and saves after transformation, even if safe.
4. Signal "shell command is a read-only search (`grep`) over `core/recall/*.py` files with no write operations to those files" caught M4 by distinguishing a diagnostic context from a polishing context (`recall-trigger-misses-2026-08-08.md:79-83`). False positives: any similar grep over recall code, where polish lessons would also be noise.

Ranking by number of cases caught: each candidate signal captures exactly one miss; none covers more than a single case. The case NO signal can be named for is M3 at the exact trigger moment described (before any code is written), because only the file path of a new scratchpad existed, and that path alone carries no information about persistence ordering.

REASONING: I derived candidate observables from the dossier’s explicit statements about what was happening and what existed. For M2, the operator was committing a test file and had authored the relevant lesson in a commit message two commits earlier—both are in git history. For M1, the actor was editing `agent_cli.py` (a known entry point) and a commit forty minutes prior had added dict support; the edit’s `str()` coercion is visible in the file diff. For M4, the shell command (grep) and its read-only nature are observable; the lesson that fired (ergonomics) is irrelevant when the actor is diagnosing rather than polishing. For M3, the dossier says “About to write a harness” — at that instant no harness code exists, so the only observable is the file path, which cannot link to the lesson about persisting raw results first. Hence M3 is unreachable at that moment; a signal could appear only after the code is typed and saved.

CHECK: Disprove signal 1 by showing that the RED-pin commit message was not in the recent window or that the test file was a pre-existing test with no collection-risk changes. Disprove signal 2 by showing the `agent_cli.py` edit did not involve `str()` coercion or that no commit adding dict support existed within the hour. Disprove signal 4 by demonstrating that the grep command was actually accompanied by a write operation to a recall file. Disprove the M3 unreachability claim by finding an observable signal at the “about to write” moment — e.g., a file name like `harness_no_raw_save.py` or a preceding shell command showing the plan; the dossier provides no such signal.

BLIND: I assume the recall hook could access git log, file diffs prior to the tool call, and shell command semantics; the dossier only confirms the current trigger sees file path and command string. Whether all these signals can be extracted synchronously and without excessive latency is unknown. The operator’s true intent is not directly observable, so my signals are proxies that may miss or misfire. My conclusion that M3 lacks any signal at the exact described moment depends on the absence of any external plan or editor pre-fill not mentioned in the dossier.

---

## BRANCH ANALOGY (NO evidence, by design)

evidence=none | 552 prompt tokens

FINDINGS:
1. Epic CPOE drug–drug interaction alerts: trigger = medication order event + patient-specific data (diagnoses, labs, allergies); suppression = tiered severity (contraindication, precaution) with institutional customisation of alert thresholds; documented failure = van der Sijs et al. (2006) systematic review measured 49–96% override rates, documenting alert fatigue that leads to clinicians routinely dismissing critical warnings.
2. FireEye (now Trellix) network intrusion detection as deployed at Target: trigger = network traffic matching signatures and heuristic anomaly rules; suppression = static priority bands (high/medium/low) plus correlation rules that group related events; documented failure = 2013 Target breach: FireEye generated alerts on malware staging and exfiltration, but the Minneapolis SOC ignored them amid a daily volume of ~40,000 IDS events (Krebs 2014).
3. Airbus A380 Electronic Centralized Aircraft Monitor (ECAM): trigger = sensor faults and parameter exceedances on aircraft systems; suppression = fixed priority hierarchy (warning inhibits caution, caution inhibits advisory) and phase-of-flight inhibition logic; documented failure = QF32 uncontained engine failure (2010) produced an ECAM “avalanche” of 50+ simultaneous warnings and cautions, overwhelming crew workload despite the suppression design (ATSB AO-2010-089).

REASONING:
I searched for non-trivial deployed systems that dynamically select which advice to show from a large store, triggered by an actor’s actions, and where mistiming produces fatigue. Candidates ruled out: autocomplete ranking (few published fatigue incidents with measured outcomes); surgical checklists (timed, not action-per-action from a large store); spaced-repetition schedulers (dedicated study, not inline work stream). I narrowed to clinical decision support, intrusion detection, and avionics alerting because they all have a mature literature on alert fatigue and documented failures. For CDS, I chose a widely cited systematic review with override rates rather than a single incident, because the reviewed studies capture the generic failure. For IDS, the Target breach is a landmark security incident with a public post-mortem. For aviation, QF32 is a well-investigated case where an alert prioritisation system was stressed beyond its design.

CHECK:
1. The van der Sijs review would be disproven if subsequent studies showed near-zero override rates after CDS redesigns (some later designs did improve, but the baseline fatigue is broadly replicated).
2. The Target breach attribution to alert fatigue would be disproven if internal investigations showed the SOC received no FireEye alerts at all (contradicted by the Krebs reporting and later congressional testimony).
3. The QF32 ECAM overload would be disproven if the ATSB report concluded the alert count had no impact on crew performance (it explicitly noted that the sheer volume of ECAM actions increased workload).

BLIND:
I cannot verify the exact triggering and suppression logic inside any of these proprietary systems; I rely on published descriptions, which may omit fine-grained details. The evidence leaves open the possibility that later versions of these systems have mitigated the failures I describe—my data points are from specific historical versions. I cannot assess whether CDS or IDS systems that use machine‑learning ranking (e.g., by confidence score) suffer different fatigue patterns, because such systems may not have public post-incident analyses.

---

## BRANCH ADVERSARY (miss dossier only)

evidence=own | 2188 prompt tokens

FINDINGS:
1. The miss episodes are hand-picked, stated to be n=4 one-seat one-day one-model (recall-trigger-misses-2026-08-08.md:101) and are only the failures the author noticed (recall-trigger-misses-2026-08-08.md:102‑103); they over-represent the apparent defect because the unobserved miss rate is unknown and the sample is too narrow to estimate the base rate of preventable failures.
2. The 5.2% rated-useful rate (recall-trigger-misses-2026-08-08.md:29) is not shown to be a defect — 61 lessons were credited as helped, noise is only 45, meaning most surfacings are passively tolerated; the system may be operating as a low‑attentional nudge whose value comes from rare hits rather than high precision.
3. The dossier itself states that whether any available signal at those moments would have selected the right lesson is an open question (recall-trigger-misses-2026-08-08.md:107), so the move to a smarter trigger attacks a selection problem whose very solvability is undemonstrated, risking complexity without proven gain.
4. The current trigger’s transparency — it matches only file path and command string (recall-trigger-misses-2026-08-08.md:19‑26) — makes its limitations legible; a smarter trigger that infers intent would earn more trust when correct and would thereby produce worse failures when wrong, a dynamic absent from the dossier’s diagnosis.
5. Nothing in the file records whether the actor read the surfacings; the 61 helped could be the only attended surfacings, in which case recall accuracy is a downstream lever on a channel the actor mostly ignores, and attention rather than trigger intelligence would be the bottleneck.

REASONING: The dossier was read as a brief for trigger improvement. To test that brief against the file alone, each claim was examined for what it actually demonstrates. The miss episodes are explicitly a noticed subset, and the file warns that unnoticed misses are probably larger (line 102‑103), which makes them an unsafe basis for inferring system‑wide failure frequency. The performance figures (6751 surfacings, 5.2% useful, 45 noise, 61 helped) describe a system that rarely disrupts work and occasionally aids; nothing in those numbers requires the interpretation “broken trigger.” The file’s open admission that the right lesson might not have been selectable even with a perfect trigger (line 107) was taken as an internal acknowledgement that the central premise is unvalidated. The transparently dumb signal was contrasted with a proposed opaque one: the file notes a case where a correct‑topic match was useless (M4, line 87), which supports the idea that surface relevance does not equal help, and that a confident wrong match could be more damaging than a benignly ignored one. Finally, the missing data on reading behavior was treated as a missing link — if nobody reads the channel, trigger quality is moot. Alternatives such as “the corpus is fine, the retrieval works perfectly” (line 11‑12) or “the problem is writing lessons that index better” were ruled out because the question is about the trigger, but they lend weight to the possibility that the trigger is not the weakest link.

CHECK:
- For F1: a broader log showing frequent, impactful misses across many sessions where a hypothetical smarter trigger would have changed outcomes would prove selection bias does not distort the picture.
- For F2: evidence that the actor systematically discards surfacings because they are incorrect or noisy, and that higher precision would raise the useful‑surfacing count, would show the 5.2% is not a tolerable steady state.
- For F3: a prototype that, given the same moments, selects the correct lesson using an intent‑based signal would demonstrate solvability.
- For F4: an experiment where actors using an opaque smarter trigger do not become overtrusting and indeed make fewer errors would weaken the overtrust concern.
- For F5: log data showing the actor reads most surfacings and only then finds 5.2% useful would prove attention is not the constraint.

BLIND: The dossier cannot show whether the actor would benefit from a different interaction model (e.g., on‑demand recall commands instead of automatic hooks), whether the lessons should be authored differently, or whether the whole recall channel should be removed. Our position also cannot rule out that a smarter trigger, if trivially simple (e.g., adding a recent‑action summary to the input), might improve usefulness without adding dangerous opacity — because the file provides no design details. Finally, we cannot see the unobserved misses, so the claim that these four are trivial or exotic is an unsupported inference from the file’s own warning.

---

## BRANCH CONTROL (at_action.py)

evidence=own | 27355 prompt tokens

FINDINGS:
1. `TITLE_SHAPED_RE` l.41 – hardcoded regex string; not tunable; affects title‑shaped query detection outside this file; cannot be changed without editing code.
2. `_STOP` l.51 – hardcoded set of 50 stop‑words; not tunable; removing words adds noise, adding words reduces query token quality; code change only.
3. `_CACHE_DIR` l.70 – base for disk cache, env `AKASHIC_RECALL_STATE_DIR` (default tempdir); tunable; moving it changes where lesson cache and per‑session state live.
4. `_CACHE_TTL` l.72 – 120 s, env `AKASHIC_RECALL_CACHE_TTL`; tunable; raising keeps stale lesson items longer, lowering increases store reads.
5. `_STALE_CUE_DAYS` l.77 – 30 d, env `AKASHIC_STALE_CUE_DAYS`; tunable; 0 disables age cue; higher makes the “[age]” message appear for younger lessons.
6. `_BENCH_PROBE_DAYS` l.175 – 14 d, env `AKASHIC_BENCH_PROBE_DAYS`; tunable; 0 disables probes; higher lets benched lessons stay out longer before a probe.
7. `_BENCH_PROBE_MAX` l.179 – 3, env `AKASHIC_BENCH_PROBE_MAX`; tunable; raises how many benched lessons get one probe per cache refresh; lower starves probes.
8. `_OUTCOME_MAX_BYTES` l.91 – 4 MB hardcoded; not tunable; when outcome log exceeds this, oldest half dropped; cannot be sized without code change.
9. `SURFACE_MAXLEN` l.152 – 6000 hardcoded; not tunable; bounds the durable surface‑event stream length; alteration needs code.
10. `OUTCOME_MAXLEN` l.163 – 20000 hardcoded; not tunable; bounds the durable outcome‑event stream length; alteration needs code.
11. `_CACHE_FILE` l.71 – hardcoded filename “lesson_items.json” inside `_CACHE_DIR`; not separately tunable; a rename needs code.
12. `_OUTCOME_FILE` l.90 – hardcoded “recall_outcomes.jsonl” inside outcome dir; not tunable.
13. Event‑log recent limit in `_with_mined_triggers` l.484 – 2000 hardcoded; not tunable; larger/smaller changes number of flip events mined for trigger terms.
14. Importance weight in `_project_items` l.293 – 4 for success=yes/true, else 3; hardcoded; not tunable; affects ranking but not via any external setting.
15. Default `limit` in `recall_at` l.1406 – 3, overridable by caller argument; hardcoded default, but tunable by hook or CLI; no env.
16. Recall relevance floor `_floor_default` l.1396‑1400 – 0.20 default, env `AKASHIC_RECALL_FLOOR`; tunable; raising excludes weaker matches, lowering admits more noise.
17. `max_chars` default in `render()` l.1584 – 110; hardcoded default, caller can override; not globally configurable.
18. Hard body cap in `render()` l.1665 – 900 chars; hardcoded; total recall text truncated beyond this, cannot be changed without editing code.
19. Self‑echo window `AKASHIC_RECALL_SELF_ECHO_H` l.1313 – 2 h, env; tunable; 0 disables, larger keeps author’s own fresh lessons hidden longer.
20. Trigger‑vs‑prose blending weights l.573 – 0.6 trigger, 0.4 prose; hardcoded; not tunable; shifting them changes how much trigger context dominates relevance.
21. Usefulness factor formula l.577‑588 – smoothing with +2.0, 0.5‑1.5 range hardcoded; not tunable; cannot alter the boost/decay shape without code.
22. Min‑hits dampener in `_damped_overlap` l.548‑549 – threshold 0.5, multiplier 0.5; hardcoded; not tunable; changes noise resistance for single common‑term matches.
23. Query token blacklist in `_query_from` – uses `_STOP` hardcoded; see #2.
24. Outcome record query truncation l.112 – 160 chars; hardcoded; not tunable.
25. `_parse_trigger` length bounds l.171 – 3..240 chars, hardcoded regex; not tunable.
26. IDF add‑one smoothing l.525‑526 – hardcoded log(n+1) formula; no tunable parameter.
27. `_OUTCOME_DIR`, `_SEEN_DIR`, `_IMP_DIR` etc. – derived from `_CACHE_DIR`, not independently tunable.
28. AKASHIC_RECALL_AT_ACTION=0 mentioned in docstring l.31 but **not read** in this file; not a knob here.
29. Question 1 (surface fewer but only high‑confidence): UNEXPRESSIBLE. Faithfulness confidence is computed l.1448 but never used to filter; need a min_confidence parameter (e.g., reject if `conf < X`). Current floor filters on relevance only.
30. Question 2 (surface only for some action kinds): UNEXPRESSIBLE inside this module. `recall_at` has no action‑type filter; the hook decides whether to call, but no config knob for “only file‑write” exists. A per‑action whitelist would be needed.
31. Question 3 (lesson declares situations, match on that alone): PARTIALLY EXPRESSIBLE, but matching cannot be entirely divorced from file/command. `_trigger_aware_relevance` l.555‑574 uses trigger text with 0.6 weight, still always blends with query from path/command. To use only declared situations you would need a weight of 1.0 on trigger; the weights are hardcoded and not tunable. So UNEXPRESSIBLE to match solely on lesson‑declared situations.
32. Question 4 (suppress a lesson shown many times and never used): EXPRESSIBLE. The usefulness feedback loop (l.577‑588) automatically decays ranking for high‑impression, zero‑credit lessons; benching (l.274‑277) outright excludes (except probes). Operator can mark as noise via `record_feedback` “noise” (l.673) or use curator’s `mark_benched` (external) to suppress.
33. Question 5 (operator mute/boost a specific lesson without deleting): EXPRESSIBLE. `record_feedback` (l.671‑693) accepts “useful” or “noise” votes, which adjust `usefulness_factor` (l.577) from 0.5 to 1.5; benched flag (l.274) is a stronger mute. No deletion required.

REASONING:  
I scanned every numeric literal, string constant, regex, and env-var lookup in the file. For each, I determined whether an environment variable, function argument, or external configuration changes its value without editing the file. Hardcoded values that only appear as assignments from literal numbers/strings were marked untunable. I then matched the five behaviour questions against existing control surfaces (relevance floor, limit, feedback votes, benching, trigger blending). I noted where a desired tuning axis (confidence threshold, pure‑trigger matching, action‑type gating) simply has no parameter or code branch in this file.

CHECK:  
- For each hardcoded claim, search the file for an env‑var read of the same name; absence disproves tunability.  
- For expressibility, attempt to achieve the exact behaviour using only the exposed API/CLI/relevance_floor/feedback: if no combination produces it, the UNEXPRESSIBLE label stands.  
- For self‑echo, verify `AKASHIC_RECALL_SELF_ECHO_H` appears in `os.getenv`; for benching, confirm `is_benched` is used and `mark_benched` exists in the store (external).

BLIND:  
I cannot see callers (hooks, CLI) that wrap `recall_at`; they might add their own action‑type gating or confidence filters, making question 2 or 1 expressible at a higher layer. The file does `_with_usefulness` only at cache‑build time; I assume the store’s usefulness counters are mutable via the recorded feedback path. I cannot verify that the external `mark_benched` actually persists to the store and is observed here without examining learning_store.py. The warm‑cache path uses `_with_usefulness` and `_with_mined_triggers`; any error silently falls through, so the actual effectiveness of those augmentations depends on a healthy store and event log.
