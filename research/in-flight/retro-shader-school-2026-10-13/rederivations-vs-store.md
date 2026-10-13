# Retro, shader school 2026-10-13: re-derivations against what the house already knew

Status: in-flight research · Date: 2026-10-13 · Seat: claude (Vandor), retro lane "re-derivations vs store" · Read-only
everywhere except this file. All times are UTC (the lesson store and the transcripts both stamp UTC; git prints -0400,
converted here).

Daniel, 2026-10-13, verbatim: "What did we learn from all of this? Would you mind fanning out agents to capture every
friction point, hand rolled script, re derivation and any other thing that would've made the process better".

## Summary

I took every discovery the session filed (20 lessons dated 2026-10-13, wishes W263 to W265, and the findings in the two
shader-school research folders) and searched the store, the docs, the skills and research for prior knowledge of each.
I also traced, in the transcripts, whether the prior knowledge was pushed to the agent at the moment it mattered. Two
frictions that were not filed as discoveries but were re-found by many agents (CRLF checkouts, the cp1252 console codec)
are included because the house had already written them down.

| class | count | meaning |
|---|---|---|
| REDERIVED | 12 | the house already knew; the knowledge did not reach the moment |
| CONTRADICTED | 2 | the house's prior knowledge was wrong or stale |
| NEW | 10 | nothing prior: nine lessons (three have a near cousin, named below) and the structural cause in section 1 |
| PRIOR FOUND IN TIME | 7 | prior knowledge did reach the work (what went well) |

Three findings matter more than any single item:

1. **One cause explains most of the misses.** Recall-at-action shows each lesson once per *session* and then hides it
   (the anti-repeat "seen" set, keyed by session id). Every workflow lane is a subagent, and subagents carry the parent's
   session id. So all 180 agents tonight shared one seen set. Each relevant prior lesson was shown exactly once, early,
   and in 9 of 9 cases I traced, it was shown on an unrelated command (usually a read-only `ls`, `grep` or `wc`). After
   that it was silent for the whole fan-out, including at the moment it was needed. Across 16,412 tool calls the hooks
   injected 1,455 lesson sources, 1,454 of them distinct: every lesson reached at most one agent, once. By the end of
   the night 1,464 of the store's 1,636 lessons were marked seen for this session. A second rule hides any lesson its
   own author filed in the last 2 hours, and every lane writes as `claude`, so a lane's fresh lesson was hidden from all
   its siblings. This is NEW to the store (the 10-01 reach map and the 10-08 suppression lesson did not name it).
2. **The wishlist already held the cures, unbuilt.** The two most frequent frictions tonight (backslashes mangled through
   a shell heredoc: 5 incidents in 4 agents; the Windows cp1252 console codec: 18 agents) are exactly open wishes W234
   (2026-10-02) and W230 (2026-10-02). All three new wishes restate open ones: W263 is W107 (2026-07-30), W264 is the W109
   family (2026-07-31), W265 is W110 and W111 (2026-07-31). None of the three cites its ancestor. The `wish` verb
   checks for colliding ids but not for similar content (`agent_cli.py:2484-2503`), and W265 was written by a direct edit
   of the file (main L5705), past the verb entirely.
3. **The `repeat` verb was never used.** At least five known lessons were re-violated tonight. Zero `repeat` calls appear
   in the session (only a retro lane ran one). Instead two twin lessons were minted, and the learn door's near-duplicate
   warning did not fire on the heredoc twin.

What would have carried the most, cheapest first: key the seen set per agent transcript, not per session, and stop
marking lessons seen on read-only commands (one change in `agent/harness/actions.py` plus the hook); give `wish` and
`learn` a near-duplicate pass that offers `repeat` or "add a recurrence receipt to Wxxx"; build W234 (a patch verb) and
W230 (UTF-8 env in `.claude/settings.json`), which Daniel or the config owner decides.

---

## How each item was checked

- **Discoveries:** `py agent_cli.py list --json` filtered to `timestamp` 2026-10-13 (19 lessons: 12 claude, 7 deepseek),
  plus `a_refused_commit_leaves_its_files_staged_for_the_next_seats_plain_commit`, filed at 18:11 after my dump;
  `docs/WISHLIST.md` lines 1775-1780 (W260-W262 are dated 10-07, so only W263-W265 are today's); the files in
  `research/reviewed/shader-school-2026-10-13/` and `research/in-flight/shader-school-2026-10-13/`.
- **Prior knowledge:** `py agent_cli.py recall "<terms>"`, a regex pass over every lesson dated before 2026-10-13 (the same
  `list --json` dump), Grep over `docs/`, `.claude/skills/`, `research/`, the code, and the wishlist.
- **Reach at the moment:** the main transcript `E--/9d62784c-bd34-488c-a370-94b7d333fbb9.jsonl` (5,847+ lines) and 179
  subagent transcripts under `E--/9d62784c-.../subagents/workflows/` (paths below are relative to
  `C:\Users\<user>\.claude\projects\`; `L` = line number in that file). I streamed them line by line and matched each
  recall injection (`source: learn:experiment:<name>`) to the tool call it was attached to by `toolUseID`. The retro
  workflow itself (`wf_4e140bc0-2ea`) is excluded from every count.

---

## 1. The structural cause (NEW): one seen set for 180 agents

**The mechanism, in code.**
- `scripts/hooks/claude_pretooluse.py:136-149`: "ANTI-REPEAT: lessons already surfaced this session ... are excluded so the
  same hint never repeats"; it calls `recall_block(session_id, session_id, ...)`.
- `agent/harness/seen.py:1-20`: one seen file per session id under `%TEMP%\akashic_recall\seen\`.
- `agent/harness/actions.py:63-85`: any rendered injection marks every shown source seen, whatever the action was.
- `core/recall/at_action.py:1822-1829`: self-echo hides a lesson from its own author for `AKASHIC_RECALL_SELF_ECHO_H`
  (default 2) hours. Every lane runs as `AKASHIC_AGENT_ID=claude`.
- Subagent transcripts carry the parent's id: `subagents/workflows/wf_4321c88e-893/agent-a2a4415ebcc2b1877.jsonl` line 1
  has `"sessionId": "9d62784c-bd34-488c-a370-94b7d333fbb9"`.

**The measurement.**
- Seen file for this session, read at about 18:17: 1,465 lines, 1,464 unique sources. The store holds 1,636 lessons.
- Every recall-hook injection in the main seat and 179 lanes: 721 injections (695 at action, 26 at plan time) carrying
  1,455 lesson sources, 1,454 distinct. One lesson was shown twice; every other lesson reached one agent, once.
- Lesson sources injected per hour against tool calls made (`inj_rate2.py`, retro lanes excluded):

| hour | tool calls | agents active | lessons injected | per 100 calls |
|---|---|---|---|---|
| 03:00 | 359 | 14 | 179 | 49.9 |
| 06:00 | 2,303 | 42 | 422 | 18.3 |
| 09:00 | 865 | 22 | 36 | 4.2 |
| 12:00 | 1,056 | 19 | 26 | 2.5 |
| 13:00 | 2,550 | 27 | 201 | 7.9 (new topics: reverse engineering, deconstruct) |
| 14:00 | 1,894 | 21 | 7 | 0.4 |
| 16:00 | 506 | 4 | 1 | 0.2 |

- Of 695 recall-at injections that carried lessons, 417 (60%) were attached to a shell command whose leading verb is
  read-only (`ls`, `grep`, `sed -n`, `cat`, `wc`, `git log/diff/status`, `Get-Content`...); 67 (9.6%) to Edit/Write; 31
  (4.5%) to a heredoc script; 3 to a git mutation (`inj_readonly.py`; a leading-verb heuristic, so approximate).
- Explicit pulls were rare: 28 transcript lines with an `agent_cli.py recall` call, across the main seat (3) and 17 lanes
  (25), 13 of them in one workflow (`wf_e267ca8b-f7c`, the deconstruct-the-house teardown).

**The nine prior lessons behind tonight's re-derivations, and what spent them:**

| prior lesson | shown once at | attached to | needed at |
|---|---|---|---|
| bash_heredocs_corrupt_regex_backslash_b_to_backspace | 06:17:49, main L2591 | `for d in ...; ls \| wc -l` census (L2582) | 07:21, 14:43, 14:52 |
| gitattributes_pins_eol_because_autocrlf_cannot_be_fixed_in_the_working_tree | 05:35:10, wf_29f7007b-3d1/agent-ac83b743 L196 | grep/sed of piano.js | 18:12 |
| a_rename_has_no_safe_parked_state | 05:23:17, main L1679 | a `for d in $(ls -t ...)` listing | 15:58 |
| mirror_refusal_leaves_tree_staged | 06:47:04, wf_60f63f69-3ea/agent-a0aaa76b L182 | `ls ...; head cdp.mjs` | 15:58 |
| exec_gate_widened_narrow_recovery_family_not_hallucinated_revive_verb (the `git apply --cached` technique) | 05:30:34, wf_29f7007b-3d1/agent-a1e963bb L89 | grep of piano.js | 06:58 |
| hard_wedge_pages_hide_two_different_failures | 09:45:12, wf_ae993e74-ec3/agent-a398ba48 L182 | a `py -c` path check | 11:33 |
| liveness_evidence_is_per_organ_not_per_signal | 05:31:48, wf_29f7007b-3d1/agent-a1e963bb L112 | grep of practice.py | 11:33 |
| lstrip_prefixes_footgun ("shlex mangles backslashes") | 06:15:53, main L2510 | a Get-Clipboard probe | 13:20 (the review; the patch's author was deepseek) |
| fable_safeguards_downgrade | 09:01:48, wf_ae993e74-ec3/agent-a0c9d23e L215 | a pytest run | 12:11-13:29 |

**Prior partial knowledge:** `silence_render_hides_suppression_from_the_seat` (2026-10-08: 77% of recall silences were
anti-repeat or self-echo exclusions) and `recall_silence_is_suppression_not_ranking` (2026-08-08). Neither names the
fan-out sharing one session. `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md` (2026-10-01) lists nine failure modes;
none is this one.

**What would carry it:** key the seen set by session plus agent transcript (if the hook payload carries the subagent's
transcript path or agent id; unknown, verify first), and do not mark lessons seen when the action is read-only. A
smaller step: let a lesson whose trigger names a command shape (a `py - <<` heredoc, `git commit`) re-fire on every
matching command, the way the cwd guard does.

---

## 2. REDERIVED

### R1. Backslashes mangled by a shell heredoc (the clearest case)

- **Tonight's discovery:** lesson `bash_heredoc_mangles_backslashes_in_python_patches` (07:23:16, filed by the dissector
  lane, wf_4321c88e-893/agent-a2a4415ebcc2b1877 L360). Its patch to `arsenal/shaders/dissect.py` carried raw 0x08 and
  0x01 bytes; three regex sites silently stopped matching (L324-L351).
- **Prior knowledge:** `bash_heredocs_corrupt_regex_backslash_b_to_backspace` (2026-09-28, "Twice now: (1) 2026-07-28 ...
  (2) 2026-09-28"); `process_match_by_argv_not_substring_and_no_backslashes` (2026-10-09); open wish **W234** (2026-10-02,
  `docs/WISHLIST.md:1434`, a patch helper so no shell edit hand-rolls this).
- **Occurrences tonight:** 5 incidents in 4 agents, 3 of them (in 2 agents) after tonight's lesson was filed:
  06:50:15 wf_4321c88e-893/agent-a4eac539 L199 (SyntaxError, truncated `\uXXXX`); 07:21 agent-a2a4415e (control bytes);
  14:43:20 main L4645 (SyntaxError, truncated `\UXXXXXXXX`, while filing three lessons); 14:52:01 and 14:52:51
  wf_cba2d412-d17/agent-a3f10f95 L204, L218. At L221 that agent works out from scratch that the tool layer, not the
  quoted heredoc, is eating the backslashes, which is the 09-28 lesson's own explanation.
- **Volume of the risky pattern:** 559 `py - <<` heredoc commands across 71 transcripts tonight.
- **Why it did not reach:** the 09-28 lesson was spent at 06:17 on a read-only census command (section 1); the new twin
  was hidden from sibling lanes by the 2-hour self-echo rule, then shown once at 10:32 to one lane
  (wf_ab3d7b01-cf2/agent-ad060ac8 L608) and never again. The main seat recognised the class only after the failure
  (L4649-L4650), from memory.
- **Store hygiene:** a twin lesson was minted instead of `repeat`; the learn door printed only "[OK] recorded lesson"
  (L363), no near-duplicate warning.
- **What would carry it:** W234's patch verb (removes the class); until then, a recall-at rule that fires on every
  `py - <<` or `cat > x.py <<` command containing a backslash, exempt from anti-repeat.

### R2. Committing part of a file beside a sibling's hunks (temporary index)

- **Tonight:** lesson `partial_commit_beside_a_siblings_hunks_needs_a_temp_index` (14:43:45). The technique was worked out
  at 06:58 (main L3084-L3108), filed 7.75 hours later, and turned into a scratch script `commit_paths.sh` at 18:00
  (main L5433).
- **Prior:** `exec_gate_widened_narrow_recovery_family_not_hallucinated_revive_verb` (2026-09-09: "a hand-sliced git patch
  (git apply --cached) to avoid committing an unrelated in-flight WIP diff sitting in the same file");
  `gitattributes_pins_eol_...` (2026-09-18, the `GIT_INDEX_FILE` copy); `oneworld_floor_wire_slice_commit` (hunks by
  content anchor).
- **Why it did not reach:** the technique lived in the `what_tried` body of a lesson whose trigger is about an exec gate,
  so nothing about "commit part of a file" could match it; and it was spent at 05:30 on a grep.
- **What would carry it:** a `commit-only <paths>` verb (W265 wish 1; tonight's scratch script is the spec). Now also a
  dedicated lesson.

### R3. A refused commit leaves files staged; the next seat's commit sweeps them (W265)

- **Tonight:** batch-B RED refused at 15:58:42 (main L4896, `check_boundaries: 3 -> 4`); its 15 files stayed staged; a
  sibling commit `1d96275d` (16:00:24) carried them under a seat-identity message; HEAD sat red for about six hours.
  Found 18:08 (L5621); W265 and lesson `a_refused_commit_leaves_its_files_staged_for_the_next_seats_plain_commit` at 18:11.
- **Prior:** W110 (2026-07-31: a commit swept locked files and "landed them under an unrelated message"), **W111**
  (2026-07-31, open: "mirror.py must UNSTAGE on guard refusal"), lessons `mirror_refusal_leaves_tree_staged` (07-31),
  `a_rename_has_no_safe_parked_state` (08-01), `explicit_paths_do_not_scope_a_mirror_commit_the_shared_index_does`
  (08-26), and `concurrency_c1_worktrees` (06-28: worktrees make "the shared-index hazard" impossible).
- **Why it did not reach:** both directly relevant lessons were spent hours earlier on listings (section 1). The session
  diagnosed this itself and wrote it into W265 (`docs/WISHLIST.md:1780`, edit at main L5729: the two lessons existed and
  recall-at surfaced neither when the hook refused), which is the right instinct, but it then minted a new lesson
  rather than recording a `repeat`.
- **What would carry it:** W111's fix in the pre-commit path (a refused commit unstages what it staged) and a refusal
  text that names the staged paths and the unstage command.

### R4. The guardrail ratchet counts the working tree, so a sibling's draft blocks every commit (W264)

- **Tonight:** W264 (15:59, main L4932). Deepseek's uncommitted `core/comm/seat_identity.py` raised check_boundaries 3 to 4.
- **Prior:** W109 (2026-07-31: "the guard reads the tree — so one seat's un-minted markdown blocks EVERY seat's commits,
  including work unrelated to it"); lessons `guardrail_baseline_desyncs_on_a_clean_checkout` (09-03),
  `green_on_the_working_tree_is_not_green_on_the_commit` (08-04).
- **Why it did not reach:** wishes have no push path; W264 does not cite W109.
- **What would carry it:** a near-duplicate pass in `py agent_cli.py wish` over open wishes; a guard-family rule
  "judge the commit you are making, not the tree you are in".

### R5. False HARD WEDGE page on the live interactive seat (W263)

- **Tonight:** 4 pages (11:33:27, 11:33:59, 11:39:38, 11:44:35; main L3731, L3749, L3841, L3963); W263 at 11:45 (L4000).
- **Prior:** **W107** (2026-07-30, open: "false HARD WEDGE on the live interactive seat ... an incarnation with live harness
  activity ... must not be paged as wedged"), W108 (07-30), W208 (09-13), lessons
  `hard_wedge_pages_hide_two_different_failures` and `liveness_evidence_is_per_organ_not_per_signal` (both 07-28, the
  latter "Fixed a false HARD WEDGE page (the doctor paged my own live seat)"). A HARD WEDGE lesson was also shown on
  2026-10-12 at main L450, inside this same session id.
- **Why it did not reach:** wish not cited; both lessons spent earlier in lanes.
- **What would carry it:** the `wish` duplicate pass, plus a recurrence counter on wishes so a third occurrence of W107
  raises its rank instead of minting W263.

### R6. New `.glsl` and `.card` files checked out with CRLF in a clean worktree

- **Tonight:** batch B (`bdd5c8fc`) passed in the main tree and failed 9 pins in a fresh worktree (18:12:34, main L5758;
  cause L5763: `assert b"\r" not in path.read_bytes()`); fixed by `.gitattributes` lines for `*.glsl`, `*.card`, `*.sh`
  (L5805, commit `86280221`).
- **Prior:** the header of `.gitattributes` itself ("Line endings are pinned HERE ... It bit twice in two days", 09-16 and
  09-17); lessons `gitattributes_pins_eol_...` (09-18), `git_apply_under_autocrlf_true_writes_crlf_...` (09-17),
  `python_write_text_crlfs_whole_files_on_windows` (09-28). This is the third occurrence.
- **Why it did not reach:** the rule lives in a file nobody opens when adding a new file type; the lesson was spent at
  05:35 on a grep. The test author knew CRLF mattered (the pin asserts no `\r`), yet only a fresh checkout can fail it.
- **What would carry it:** a test that every text extension tracked in the repo has an `eol` attribute (or a default
  `* text=auto eol=lf` line). The clean-worktree habit is what caught it (see G6).

### R7. `gl.finish()` alone does not wait on SwiftShader; time with a one-pixel `readPixels`

- **Tonight:** lesson `gpu_preflight_needs_a_scale_ladder` (12:29, revised 14:58). The Lab stage pre-flight was designed
  with `gl.finish()` alone (wf_2857fa6c-f17/agent-a2688a47 L829, 12:31); a reviewer flagged the missing sync
  (agent-ac9183bb L141, 13:53); the fix added `drainGl` (wf_07b70c9d-63b/agent-ade2258a L523, 14:59; committed in
  `be0fc4c8` at 18:15).
- **Prior:** `arsenal/web/piano-lab-vfx.js:2422` (`__piano.bench`, a 1-pixel readPixels per frame, from 2026-09-13);
  `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md:288`, `adaptive-resolution-aa.md:170`,
  `design-vfx-director.md:378`. Same night, three hours earlier: `arsenal/web/shaderlab/render.js:271-279` ("A 1x1
  readPixels makes the timer wait for the draw to finish"), committed in `ca6b330f` at 09:41.
- **Why it did not reach:** a dark plane. Zero lessons mention `gl.finish` or `readPixels`; the knowledge lived only in code
  and research, which have no push path (the 10-01 reach map's failure mode 8). The shader-craft timing section
  (`.claude/skills/shader-craft/references/dissecting-shaders.md:98-104`) still does not say it.
- **What would carry it:** one line in that skill section, and one shared `drainGl` used by both `render.js` and
  `stage.js` (two copies today).

### R8. `tanh` of a large argument is NaN (same-night re-derivation)

- **Tonight:** part of lesson `swiftshader_nan_parity_tanh_minmax_2026_10_13` (08:37), after one corpus shader drew black.
- **Prior, same night:** the study lanes wrote "tanh overflow to NaN on large inputs" into their private study notes at
  06:26 and 06:33 (wf_60f63f69-3ea/agent-a88046e6 L42, L98), two hours earlier. The runtime lane did not see it. The
  research report `research/reviewed/shader-school-2026-10-13/pattern-fractal-2d.md:867, :933, :992` says the same (its
  time of writing relative to 08:37 is unknown).
- **What would carry it:** study lanes file gotchas as lessons as they find them (with the seen-set fix, so siblings see
  them), or a workflow journal channel later lanes read. The min/max NaN operand half is NEW (N1).

### R9. The Windows cp1252 console codec

- **Tonight:** `UnicodeEncodeError: 'charmap' codec can't encode ...` in 18 transcripts (17 lanes and the main seat), first
  at 02:34:41 (wf_39e2cf44-316/agent-aa458d44 L115). Not filed as a discovery; each agent re-found the workaround.
- **Prior:** 15 lessons since 2026-07-02 (`piped_win_child_needs_utf8` 07-12, `windows_subprocess_utf8_stdout_reconfigure`
  07-18, and others) and open wish **W230** (2026-10-02, `docs/WISHLIST.md:1386`: set `PYTHONUTF8=1` and
  `PYTHONIOENCODING=utf-8` in `.claude/settings.json` env; it counted 348 hand-typed prefixes in one earlier session).
- **What would carry it:** W230 (a settings change; the config owner decides). Until then, one line in every lane brief.

### R10. Lanes stopped by a safety classifier

- **Tonight:** lesson `a_fan_lane_stopped_by_a_safety_classifier_is_rescoped_not_resubmitted` (14:43). Stop messages:
  wf_2857fa6c-f17/agent-a5559711 L439 (12:11); wf_5d01ae05-3d2 agents a986eff7 L366 (13:09), ad2827ea L399 (13:14),
  a5ea776d L364 (13:14), adac4bab L108 (13:29); main L4794 (15:43), L4803 (15:50), L5299 (17:19); one more reported in a
  lane result (wf_60f63f69-3ea/agent-afb5ea9e L57, 06:34). Two research reports were never written (main L4622).
- **Prior:** `probe_phrasing_safety_refusal` (2026-07-03: "phrase probes as what they are ... never let a probe's theater
  trigger a model's guardrails"), `text_matching_guards_treat_documentation_as_code` (08-05), `fable_safeguards_downgrade`
  (07-19), `fable_eject_trigger_is_wider_than_security_work` (08-11), and the auto-memory note on safeguard downgrades.
  The house knew its own vocabulary is classifier bait; a research fan on this topic was predictable to trip.
- **Why it did not reach:** three of the four lessons were shown to other lanes hours before the fan launched (04:01,
  05:07, 09:01); the fourth, `probe_phrasing_safety_refusal`, was shown at 13:18 to a teardown lane, after the stops.
  The "rescope, never resubmit" half of tonight's lesson is new and right.
- **What would carry it:** a brief-template line for any security-adjacent fan (defensive framing and explicit
  exclusions written before dispatch), not after the first stop.

### R11. Tests over Daniel's private data leaking through outputs (partial)

- **Tonight:** lesson `tests_over_daniels_private_corpus_must_not_leak_through_test_output` (04:10). An independent verifier
  found three leak paths: green-run stdout, pytest assertion introspection, and `tmp_path` copies pytest keeps.
- **Prior principle:** `redaction_scoped_to_the_tracked_tree_leaves_the_store_reloading_it` (2026-08-15: "A redaction is
  scoped to a DATA PLANE, not a directory ... enumerate every plane that can re-emit the string"). The specific exits
  (introspection, `tmp_path` retention) are new.
- **Why it did not reach:** the lesson was shown at 04:50 to an unrelated lane (wf_29f7007b-3d1/agent-ac618adf L14),
  40 minutes after this lesson was filed. The verifier is what caught it (the fence worked).
- **What would carry it:** a privacy line in the test-writing path (a skill line or a pin helper that refuses to print
  private records on green).

### R12. A Windows quoting fix pinned only by argv shape (partial)

- **Tonight:** lesson `an_exec_quoting_fix_must_be_pinned_by_spawning_the_interpreter` (14:43). Heimdall's patch used a
  `shlex` `posix=True` fallback; its 6 pins were green; live probes by the claude seat showed four broken cases
  (main L4374-L4394).
- **Prior:** `lstrip_prefixes_footgun` (2026-07-17: "shlex mangles backslashes"), `fail_open_plus_monkeypatched_pins_
  equals_invisible_noop` (08-01: "only an unpatched pin proves the WIRING"), `a_pin_that_supplies_its_own_input_tests_
  the_mechanism_not_the_wiring` (08-04), `ps51_native_arg_embedded_quotes_eat_commit_messages` (07-29).
- **Why it did not reach the author:** the authoring seat is deepseek; whether its runner door pushes recall at action is
  unknown. The review caught it, so the house paid one round, not a regression.
- **What would carry it:** a pin helper that spawns the real interpreter, so the cheap pin is also the honest one.

---

## 3. CONTRADICTED

### C1. "Route security-vocabulary slices to Opus seats" no longer escapes the classifier

- The auto-memory note on safeguard downgrades says to route flagged-vocabulary work to Opus seats and names the marker
  `"subtype":"model_refusal_fallback"`. Tonight the seat was already on Opus 5.5 and was stopped three times with a new
  marker, `model_refusal_no_fallback` (main L4795, L4804, L5300), and the error "Claude Code can't respond to this
  message with Opus 5.5" (L4796). Routing to Opus is no longer an escape, and the marker list is incomplete.
- **Fix:** update that memory note (marker and doctrine). Kind: doc.

### C2. T272 said collision safety was "NOT DONE AT ALL"; detection was built

- `state/coord/tasks.json` T272 (2026-08-10): "T088(a) COLLISION-SAFETY -- NOT DONE AT ALL". Deepseek's recon lesson
  `resident_identity_collision_slice_recon` (15:52) found detection built (roster split-brain, stale incarnation, `sid8`)
  and only prevention missing; it then built the claim step (`1d96275d`). T272 is itself a record of an earlier
  re-derivation ("specified 24 days before I re-derived it").
- **Fix:** ledger entries that assert absence carry a date and a verify command. Kind: process.

---

## 4. NEW (no prior knowledge found)

| # | lesson (time) | nearest cousin, if any |
|---|---|---|
| N1 | SwiftShader returns the second operand of `min`/`max` when either is NaN, and `0/0` on a first SDF step poisons it (`swiftshader_nan_parity_tanh_minmax_2026_10_13`, 08:37) | none |
| N2 | `ms_per_frame` from one frame after compile is mostly compile time (`shader_check_ms_per_frame_is_mostly_compile_time`, 07:51) | none (the shader-craft line "SwiftShader timing never stands for GPU timing" arrived later, in `0be497f5`) |
| N3 | Shadertoy's client behaviour, settled from public mirrors via `gh search code` (`shadertoy_client_behaviour_via_github_mirrors`, 09:22) | `blocked_html_use_the_sites_own_api_mediawiki` (09-24: when a site refuses the house fetcher, use another door) |
| N4 | A headless wait for images stalls on lazy images inside a closed `<details>` (`headless_wait_for_images_skip_closed_details`, 10:43) | `piano_headless_dom_screenshot_pause_render_first` (10-10, a different stall) |
| N5 | SwiftShader `sin`/`cos`/`atan` need 1e-3 relative tolerance in twin probes (`swiftshader-trig-tolerance-in-glsl-twin-probes`, 14:40) | none |
| N6 | Twin parity at knob extremes has a few outlier pixels from float sensitivity; pin a fraction, not a max (`glsl-twin-parity-at-knob-extremes-has-outlier-pixels`, 17:37) | `lab_light_layer_on_off_pair_same_frame` (10-10: SwiftShader noise across page loads) |
| N7 | `client=None` on a Redis door means "default connection", not "down"; stub a raising client (`claim_id_registration_handshake_slice`, deepseek, 15:56) | none |
| N8 | A detector router must rank by specificity and give every detector an explicit kind (`re_triage_detector_rank_and_kind_authority`, deepseek, 13:34) | none |
| N9 | A second read on the same file handle starts after the prefix (`re_binary_string_hunt_reads_from_zero_not_pointer`, deepseek, 14:05) | none |

Also new: the structural cause in section 1. The eight external research reports in
`research/reviewed/shader-school-2026-10-13/` are outside knowledge rather than house re-derivations; I did not
adjudicate them line by line.

---

## 5. PRIOR FOUND IN TIME (what went well)

- **G1. Census before the module system.** Seven census readers (`research/in-flight/shader-school-2026-10-13/arc-*.md`)
  and Heimdall's blind half B found the house's three module systems, the dormant VFX bench, the old ingest's licence
  risk (`arc-vfx-bench.md:39-44`) and the looks registry. The reconciled spec reads the bench chunks in place and keeps
  one `//!` header (`build-spec-reconciled.md:11-12`). One timing note: the module core (`5e127983`, 06:33) landed before
  most census files were written (06:31-06:58); it still reused the chunk header format.
- **G2. A lane-to-lane hand-off inside a workflow.** The compile-time finding was filed at 07:51:13
  (wf_4321c88e-893/agent-a2a4415e L852), was in the next lane's brief at 07:51:59 (agent-aad178f6 L2), and `warmMs`
  existed by 07:57 (L148). It is now in `dissecting-shaders.md:98-104`.
- **G3. Deepseek searched before building.** `research:web:reverse_engineering_suite_scope` (13:21) found the house's own
  wire-level reverse-engineering research; the web playbook cites it (`.claude/skills/reverse-engineering/references/
  web-apps-protocols-ux.md:93-95`). `research:web:simon_pr_review_coverage_and_integration` (13:41) found the two
  existing reviews and avoided a re-analysis.
- **G4. The deconstruct question.** Daniel asked: "I think we may have done this before" (13:05:48, main L4185). A hand
  grep and `eye find` found `docs/pillar-analysis-method.md` in 20 seconds (L4191-L4218), and the new skill routes to it,
  to root-cause and to verified-done (`.claude/skills/deconstruct/SKILL.md:24-28`). The gap: plan-time recall at
  13:05:51 (L4187) surfaced two unrelated lessons, and Daniel had to raise it.
- **G5. A checker message carried its own fix.** The claim-family refusal text
  (`scripts/checkers/check_boundaries.py:196-199`) prescribes exactly what deepseek's lesson
  `claim_family_register_in_ephemeral_roster` (16:01) restates.
- **G6. The clean-worktree habit.** Verifying batch B in a fresh worktree is what exposed R6 within minutes.
- **G7. The fence carried prior method.** Heimdall's acceptance review named "the inverse-of-count problem again: pass-on-
  wrong vs fail-on-right" (`heimdall-fence-acceptance-S0-S1-S4-L.md:35`).

---

## 6. Carriers, ranked by cost

| carrier | kind | would have carried | owner |
|---|---|---|---|
| Seen set keyed per agent transcript; nothing marked seen on read-only commands | hook | R1, R2, R3, R5, R6, R10, R11 (section 1) | any seat; verify the hook payload first |
| `wish` and `learn` near-duplicate pass that offers `repeat` or a recurrence receipt on an open wish | verb | R3, R4, R5; the two twin lessons | any seat |
| An always-fire rule for `py - <<` / `cat > *.py <<` with a backslash | hook | R1 until W234 lands | any seat |
| W234 patch verb | verb | R1 (559 heredoc commands tonight) | any seat |
| W111: a refused commit unstages what it staged; refusal text names staged paths | hook | R3 | any seat |
| W230: UTF-8 env in `.claude/settings.json` | config | R9 (18 agents) | Daniel or the config owner |
| A test that every tracked text extension has an `eol` attribute | test | R6 | any seat |
| One line in `dissecting-shaders.md` Timing, one shared `drainGl` | skill | R7 | any seat |
| Brief template: security-adjacent fans state defensive framing before dispatch; lanes file gotchas as lessons when found | brief | R8, R10 | conductor |
| Update the safeguard-downgrade memory note (new marker, Opus no longer an escape) | doc | C1 | memory owner |

---

## Coverage

**Where each discovery landed:** `tests_over_daniels_private_corpus...` R11 · `bash_heredoc_mangles...` R1 ·
`shader_check_ms_per_frame...` N2 · `swiftshader_nan_parity...` R8 and N1 · `shadertoy_client_behaviour...` N3 ·
`headless_wait_for_images...` N4 · `research:web:reverse_engineering_suite_scope` G3 · `re_triage_detector...` N8 ·
`research:web:simon_pr_review...` G3 · `re_binary_string_hunt...` N9 · `swiftshader-trig-tolerance...` N5 ·
`partial_commit_beside...` R2 · `an_exec_quoting_fix...` R12 · `a_fan_lane_stopped...` R10 · `gpu_preflight...` R7 ·
`resident_identity_collision_slice_recon` C2 · `claim_id_registration_handshake_slice` N7 ·
`claim_family_register_in_ephemeral_roster` G5 · `glsl-twin-parity-at-knob-extremes...` N6 · `a_refused_commit_leaves...`
R3 · W263 R5 · W264 R4 · W265 R3 · the CRLF failure R6 · the cp1252 errors R9 · the safeguard stops C1.

**Read:** all 20 lessons dated 2026-10-13 in full (`list --json`, 1,636 lessons total); `docs/WISHLIST.md` W256-W265
and the ancestors found by search (W107-W111, W208, W230, W234); `build-spec-reconciled.md` in full; section 0 of
`arc-methodology.md` and sections 0-2 of `unified-architecture-draft.md`; the other shader-school files and Heimdall's
two files through targeted greps (headings, prior-art terms, the specific claims cited above); the hook, seen-set and
self-echo code; the `wish` door; `.gitattributes`; `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md` sections 1-4; T272
in the task ledger; the `repeat --report` ledger.

**Streamed, not read whole:** the main transcript and 179 lane transcripts (about 400 MB on disk), one line at a time,
with targeted pattern scans; each `py` process stayed small.

**Skipped, and why:** the eight external research reports were not adjudicated claim by claim (they are outside
knowledge, not house re-derivations); private study notes and corpus files under `state/` were not opened (privacy and
the licence line); W260-W262 are dated 10-07, so out of today's scope (I only checked whether their classes recurred:
W260's cp1252 class did, as R9); no `recall-at` call was made, because it writes impression counters. `recall` was run
as the brief asked; it may increment counters too.

**Unknowns:** whether the hook payload identifies subagents (needed for the seen-set fix); whether deepseek's runner door
pushes recall at action (R12); the order of the `pattern-fractal-2d.md` tanh lines relative to 08:37 (R8); the 60%
read-only share is a leading-verb heuristic, not a full parse.
