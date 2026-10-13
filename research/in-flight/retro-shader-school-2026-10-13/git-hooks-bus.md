# Retro lane: git, hooks, wishlist and the bus (2026-10-13)

Lane report for the shader-school retrospective. Daniel asked, 2026-10-13: "What did we learn from all of this? Would you mind fanning out agents to capture every friction point, hand rolled script, re derivation and any other thing that would've made the process better". This lane covers the git history, the git hooks, the wishlist and the claude inbox on the bus. Everything was read-only except this file.

**Clocks.** Transcript and bus timestamps are UTC (`Z`). Git dates are EDT (`-0400`). Where both matter, both are given. Mixing the two produced two wrong numbers in today's records (item 14).

**Sources.** "Lnnnn" is a line in the main session transcript, `%USERPROFILE%\.claude\projects\E--\9d62784c-bd34-488c-a370-94b7d333fbb9.jsonl`. Watcher outputs are `%LOCALAPPDATA%\Temp\claude\E--\9d62784c-bd34-488c-a370-94b7d333fbb9\tasks\<id>.output`. The scratchpad is the `scratchpad` folder beside them. Bus ids are entries in the Redis streams `bifrost:inbox:<seat>` on port 16379.

## Summary

The night's biggest git and bus cost came from one chain of four links, and each link has a cheap fix:

1. **A refused commit left its files staged.** The hook refused claude's batch-B RED commit because another seat's uncommitted draft raised the guardrail count (the ratchet counts the working tree; W264). The commit script had already run `git add`, so 15 files stayed staged in the one shared index.
2. **Another seat's plain commit swept them in.** About two minutes later Heimdall committed his unblock fix with a plain `git commit`. The commit took all 15 files: 6 twin test files, `tests/test_glsl_atlas.py` and 8 fixture files. That is 1d96275d, "first-boot identity claim", and the swept files are about 96% of its changed lines. HEAD then held tests without their modules for 2 h 08 min, across four commits.
3. **The bus reported the sweep, but nobody read it.** Heimdall's reply at 16:01:12Z said plainly that his commit had swept in a sibling's staged shader files. Claude saw only the first ~160 characters (the wake hook clips). The re-arm ritual then consumed the full body into a background file that was never opened. Claude replied 37 seconds later without the body and found the sweep at 18:08Z, 2 h 07 min later.
4. **The written record got the numbers wrong.** The wish (W265) and the lesson filed afterwards say "hours later" and "six hours". The facts are about two minutes and 2 h 08 min. "Six hours" is 12:00 EDT read against 18:08 UTC.

Three findings on the bus side matter beyond tonight:

- **Some directed mail can never wake the seat.** The wake design ignores a peer's `chat` and `note`, and ranks a `nudge` below the floor. On 10-13, eight directed messages from Heimdall could not wake claude. One of them was a review request that sat 47 minutes until Daniel asked: "Hey, did you get heimdalls recent message?"
- **Four messages were consumed but never read.** The re-arm ritual consumes mail into watcher output files, and only 4 of the 15 files were ever opened. Four Heimdall messages appear nowhere in the session transcript: a commit-timing note, a coordination question with options (a)/(b)/(c), a review verdict and a 7,691-character callsign round. All four are marked consumed, and the question went unanswered.
- **The unread count is a phantom.** The legacy read cursor has been frozen since 2026-09-25 22:34Z, so every peek and every prompt hook reports 52 to 60 "unread" September messages. It printed 80 times today. Twice it buried a new message, and finding one message took 7 to 8 tool calls each time. The second time ended with a hand-rolled raw Redis read.

On the git side, three smaller findings:

- **Every commit carries a docs diff that is pure churn.** `docs/PHYSICS.md` changed in 45 of today's 45 commits, and in 36 of them the only change was its "Derived at <parent sha>" stamp.
- **CRLF warnings hid a real signal.** Three house writers produce CRLF. The 146 LF-to-CRLF warnings on the new `.glsl` and `.card` files were filtered out with `grep -v CRLF`, and they were the advance notice of a fresh-checkout failure: 9 pins failed in a clean worktree, fixed at 86280221.
- **The commit procedure was rebuilt five times in one day.** The one run that failed reported exit code 0.

Things that went well are listed too: clean-worktree verification, the bus spill-to-blob, Heimdall's 63-second unblock, the authorship ledger, and holding a relayed ruling until Daniel confirms it.

## Timeline of the 12:00 chain (UTC, EDT in brackets)

| time | event | evidence |
|---|---|---|
| 15:58:06Z (11:58) | claude's `commit_batchb.sh` runs `git add -- <15 paths>; git commit -- <paths>` | L4875 |
| 15:58:28Z | background task reports "completed (exit code 0)" | L4882 |
| 15:58:42Z | log read: `pre-commit BLOCKED: guardrail debt INCREASED: check_boundaries: 3 -> 4` | L4896 |
| 15:59:03Z | cause: `core/comm/seat_identity.py` holds 80 uncommitted lines in another seat's lane | L4915 |
| 15:59:21Z | claude asks Heimdall to register the key family, or else to commit or park his slice | L4920, bus 1791907161776-0 |
| 16:00:24Z (12:00:24) | Heimdall's plain commit 1d96275d sweeps in the 15 staged files | `git show --stat 1d96275d`; `state/authorship/seats.jsonl` line 1117, seat=deepseek |
| 16:01:12Z | Heimdall's reply says the commit swept in a sibling's staged files | bus 1791907272257-0 (2,687 chars) |
| 16:01:28Z | claude's wake hook shows the first ~160 characters only | L4945 |
| 16:01:33Z | the re-arm consumes the reply into `b0bvr6h91.output`, which is never read | L4952; tool-use scan |
| 16:01:48Z | claude believes the files are still staged and holds them | L4960 |
| 16:01:49Z | claude thanks Heimdall (279 chars) without having read the body | bus 1791907309145-0 |
| 18:00:52Z–18:02:45Z | three more commits land on a HEAD missing the batch-B modules | 3783b52e, 0be497f5, 6ea924ba |
| 18:08:17Z | claude discovers the sweep | L5620 |
| 18:08:36Z (14:08:36) | bdd5c8fc, the GREEN half, says in its message where its RED half went | `git show bdd5c8fc` |

## Items

Each item gives its evidence, its cost, the smallest fix, and a count where one could be made.

### 1. A refused commit left 15 files staged; a sibling's plain commit swept them in (friction)

- **Evidence**
  - The `C()` helper in `commit_batchb.sh` (L4875) does `git add -- "$@"; git commit -q -m "$msg" -- "$@"`.
  - The hook refused the commit (L4896) after the `git add` had already staged the files.
  - `git show --stat 1d96275d` lists 21 files. Fifteen are batch-B pins and fixtures: about 5,800 of roughly 6,040 changed lines.
  - The authorship ledger records seat=deepseek (`state/authorship/seats.jsonl` line 1117).
  - At 1d96275d, `arsenal/shaders/twins/draw2.py` and `arsenal/web/glsl/draw2/sdf2.glsl` are absent (`git cat-file -e`).
  - bdd5c8fc's message records what happened.
  - At L4960 claude chose to keep the files staged while a fix workflow was editing nearby files. By then the sweep had already happened, 84 s earlier.
  - Two prior lessons already warned about this: `mirror_refusal_leaves_tree_staged` and `a_rename_has_no_safe_parked_state`. Recall did not surface either at the refusal (W265; L5725).
- **Cost**
  - Git history misattributes 15 files.
  - Every clean checkout between 16:00:24Z and 18:08:36Z (four commits) holds tests without their modules. That they fail is inferred from the missing modules; the tests were not run.
  - A discovery detour at 18:08Z, plus a wish and a lesson.
  - The 91 commits are unpushed, so this is still repairable. Rewriting history is Daniel's call.
- **Fix**
  - One shared commit verb, `py agent_cli.py commit-only --msg-file F <paths>`, that builds the commit in a temporary index from HEAD. The scratch `commit_paths.sh` is the spec.
  - The pre-commit hook should unstage what a refused commit staged.
  - It should also warn when the index holds staged paths the committing seat did not touch (W265 points 1 to 4).
- **Occurrences:** 1 sweep today. The same family appears in W109 and W110.

### 2. The bus reported the sweep at 16:01Z; claude read it at 18:08Z (friction)

- **Evidence**
  - Heimdall's reply (bus 1791907272257-0, 2,687 chars) states that his commit also swept in about 18 already-staged shader files a sibling had added.
  - The wake hook line at L4945 is clipped at about 160 characters.
  - `bifrost-standby` consumed the full body into `b0bvr6h91.output`. A scan of every tool call in the transcript finds no read of that file.
  - Claude's 279-character thank-you went out 37 s after the reply (bus 1791907309145-0).
  - Discovery came at L5620.
- **Cost:** 2 h 07 min of not knowing. That gap is the same window during which HEAD sat red and three commits stacked on top.
- **Fix:** When a woken seat re-arms, the bodies of the mail it consumed should come back into the turn, not land in a background file (see item 3). A reply from a seat you asked to act should never be acknowledged from a 160-character clip.
- **Occurrences:** 1 here. The same mechanism is behind item 3.

### 3. The re-arm ritual consumes mail into files nobody reads; four Heimdall messages never reached the session (friction)

- **Evidence**
  - `agent/bifrost_pull.py:730-775` (`standby`): `consume_inbox()` first, then `render_collapsed(msgs)[:12]` into the report. The verb runs as a background Bash task, so that report lands in the task's output file.
  - On 10-13 claude armed 16 times (L562 through L5560) and there were 14 distinct watcher exits.
  - Of the 15 watcher output files, only 4 were ever opened: `bva9xig06`, `bpktlk1ze`, `bwf112ftb` and `b67ilz79b` (empty when read, L5579).
  - `b4lhwlu6f`, armed at 15:55:02Z, consumed five messages, including four from Heimdall:
    - 13:38:01Z, a note on when to fold in his CLI fixes;
    - 13:49:15Z, a note drafting the shared-tree coordination and asking claude to choose (a), (b) or (c);
    - 14:09:09Z, a review verdict;
    - 14:09:41Z, a 7,691-character callsign round.
  - None of the four appears in the transcript, whether searched by bus id or by distinctive phrase (0 hits each).
  - Claude's outbound mail to Heimdall after 13:49Z answers none of them (bus 1791907161776-0, 1791907309145-0, 1791909762400-0).
  - The lane cursor sits at the tail, so the four count as read.
  - Eight of the 15 watcher outputs contain bodies cut with `...[truncated] [full body: bifrost-fetch --get <id>]`.
- **Cost**
  - One coordination question went unanswered. Heimdall wrote that he would hold his toolbox patch until claude named a window.
  - A review verdict and a long callsign analysis went unread.
  - The downstream cost is unknown.
- **Fix**
  - Make the ritual peek-then-arm: show the pending bodies in the turn as a tool result, and advance the cursor only on an explicit ack.
  - Or keep a durable "consumed, unread" list that the prompt hook surfaces until it is acked.
  - Also W262: the wake listener is unsupervised.
- **Occurrences:** 11 of 15 watcher outputs unread. 4 messages never surfaced.

### 4. Directed peer mail could not wake the seat; Daniel had to act as the router (friction)

- **Evidence**
  - `scripts/bifrost_wake.py:57-58`: `WAKE_WORTHY_KINDS` covers request, handoff, reply, blocker, question, completion and nudge. It excludes chat and note.
  - `core/comm/wake_tiers.py:57,104-108`: a directed `nudge` resolves to AMBIENT (tier 3).
  - Claude arms with floor 2. Every watcher output prints "floor: tier 2 (settlement)".
  - Heimdall's review request at 12:31:57Z was kind=chat (bus 1791894717163-0). The watcher armed at 08:02:48Z (L3228) did not exit until Daniel's message at 13:18:47Z. That message reads, in full: "Hey, did you get heimdalls recent message?"
  - On 10-13, eight directed Heimdall messages could not wake the seat: 06:20:51 note, 12:31:57 chat, 13:21:29 nudge, 13:38:01 note, 13:49:15 note, 14:09:09 chat, 14:09:41 chat and 17:27:06 nudge. The last of these was Heimdall telling claude that Daniel wanted a reply.
  - At 13:33:13Z claude told Daniel on the bus that a message from him or Heimdall would wake the seat even when idle (bus 1791898393306-0). That is true only for Heimdall's request, handoff, question, blocker, reply and completion kinds.
- **Cost**
  - 47 minutes of unseen review request.
  - The operator had to route mail himself.
  - An inaccurate reachability claim was made to Daniel.
- **Fix** (pick one)
  - A directed peer `chat` or `note` that asks something becomes tier 1.
  - A `nudge` addressed to the seat outranks the floor, since a nudge is by definition a repeated ask.
  - `bifrost_send` warns the sender when a directed `chat` or `note` ends in a question and suggests `kind=request`.
- **Occurrences:** 8 non-waking directed messages on 10-13.

### 5. The phantom backlog: a frozen legacy cursor buries new mail (friction)

- **Evidence**
  - Read-only HGETALL: `bifrost:cursor:claude` has inbox=1790375688522-0, which is 2026-09-25 22:34:48Z. `bifrost:cursor:lane:claude` has inbox=1791914687320-0, the tail.
  - The legacy stream holds 278 entries after the frozen cursor.
  - The first message every peek shows is a 2026-09-26 "prior-art sweep" from Heimdall (L4299, L5566). It is the first entry after the legacy cursor in both streams.
  - The prompt hook printed "[akashic] mail: N unread bus msg(s)" 80 times: 58 seventy-four times, 59 four times, 60 twice.
  - `bifrost-sync` says "54+ unread (work-lane, peek ...)" (L2669) and "52+" (L3747), although the work-lane cursor is at the tail. The code comment at `agent/bifrost_pull.py:711-712` says the peek reads the legacy cursor.
  - So the house showed four different unread numbers: 58, 54+, 278 and 0.
  - `core/comm/bifrost_api.py:332-338` records the same defect class once before (a cursor frozen since 2026-08-29 with 204 entries). It was fixed for the arm-time check only.
  - The docstring of `agent/harness/context.py` `_unread_count` names this pathology: an alert that is routinely wrong teaches the reader to skip the line.
- **Cost**
  - Two message hunts:
    - 13:18:54Z–13:20:04Z, 8 tool calls after the re-arm: inbox peek, events (twice), promoted, `mailbox --help`, `mailbox --json`, a hand-rolled py filter, `mailbox --open` (L4290–L4351).
    - 18:07:06Z–18:07:38Z, 7 tool calls: re-arm, events piped to py (failed), inbox peek, two output-file reads, ToolSearch, then a hand-rolled raw Redis `xrevrange` over scanned keys (L5560–L5589).
  - At L5574 the agent declined to consume the backlog because it could not tell which cursor it would move.
- **Fix**
  - The peek and the prompt hook should use the rule `_pending_peek` already uses: the lane cursor when it is not virgin. Label the scope honestly.
  - Retire claude's legacy cursor with the existing `bifrost-skip-to-now` ritual. That is Daniel's call, since it marks September mail as read.
  - Add a `bifrost latest --from <seat>` verb.
- **Occurrences:** 80 hook lines, 2 hunts, 1 prior recurrence.

### 6. The wake hook clips the message that woke the seat (friction)

- **Evidence**
  - There were 17 "WOKE BY" lines on 10-13.
  - Two of Daniel's eight wake messages were clipped: 207 characters at 16:35:51Z (L4972) and 262 characters at 18:04:47Z (L5550).
  - Every fleet wake was clipped. Line lengths ran 179 to 371 characters including the prefix, with a body of about 160.
  - The 18:04 clip started the 7-call hunt in item 5.
- **Cost:** about 30 s and 7 tool calls for one message, and an unread body in item 2.
- **Fix:** Show operator messages in full in the WOKE BY line, since they are short. Give fleet messages their bus id and the exact fetch command.
- **Occurrences:** 2 of 8 operator wakes. All 9 fleet wakes.

### 7. A turn stopped by the safety classifier after a wake never re-armed; the seat was deaf for 38 min (friction)

- **Evidence**
  - The wake at 17:19:56Z (L5287) was followed by a safety-classifier stop and "model_refusal_no_fallback" (L5298–L5301).
  - The next arm came at 17:58:36Z (L5331).
  - In between, Daniel asked at 17:22:00Z: "Do we have preset color templates?" Heimdall's nudge at 17:27:06Z relayed that Daniel wanted a reply.
  - The answer went out at 18:11:14Z (bus 1791915074381-0).
  - The same pattern happened at 15:50:14Z (L4798, then a stop at L4802–L4805), with a re-arm at 15:55:02Z.
  - Three classifier stops today: L4793, L4802 and L5298.
- **Cost**
  - 38 min 40 s unarmed.
  - Daniel's question waited 49 min. His emoji reaction waited 39 min.
  - A further 4 min 48 s at 15:50.
- **Fix:** Re-arming must not depend on the turn ending normally. Either a supervisor restarts the watcher (W262), or the stop path re-arms on any turn end, including refusals and API errors.
- **Occurrences:** 2 wakes lost this way.

### 8. The commit procedure was hand-rolled five times; the failing run reported success (hand_rolled_script)

- **Evidence**
  - In the scratchpad: `commit_stage2a.sh` (07:35 EDT, 22 commits), `commit_fixes.sh` (10:05 EDT, 6 commits), `commit_batchb.sh` (11:58 EDT, refused) and `commit_paths.sh` (14:01 EDT, temporary index, used for 7 commits). There was also an inline `GIT_INDEX_FILE` sequence for the lean light (L3096, 06:59Z), plus 8 `msg_*.txt` message files.
  - `commit_batchb.sh` ran as `bash ... > log 2>&1; grep -v "CRLF\|^pre-commit" log | tail -8`.
  - The exit status was `tail`'s, so the background task reported "completed (exit code 0)" (L4882). The filter also dropped the "pre-commit BLOCKED" headline (L4893 shows only the tail of the message).
  - At 15:58:17Z, 25 seconds before the log was read, claude told Daniel that batch B was landing at that moment and had been verified in a clean worktree (L4879). It corrected this at 16:00:02Z (L4939).
- **Cost**
  - About 13 KB of scripts re-derived.
  - One premature claim to Daniel.
  - The refusal was read late.
- **Fix**
  - One house verb, `commit-only`. It should:
    - build the commit in a temporary index;
    - exit nonzero on refusal;
    - print a one-line refusal reason;
    - resync the real index for every path in the commit;
    - take an optional `--verify-clean` worktree run.
  - Its output should never be piped through filters.
- **Occurrences:** 5 procedures, 1 masked failure.

### 9. The hook stages regenerated docs into whichever index is active (friction)

- **Evidence**
  - `scripts/githooks/pre_commit.py:433-445`: `regenerate_derived()` runs `git add -- docs/<doc>` for five derived docs. Inside a temporary-index commit, git hands the hook that index, so the regenerated docs land only in the commit.
  - At 18:01Z (L5442–L5462), after 3783b52e, `git diff --cached` showed the real index still holding the pre-commit PHYSICS.md: "Derived at 89f1152b" against HEAD's "Derived at 1d96275d". Claude fixed it with `git reset -q -- docs/PHYSICS.md`.
  - `commit_paths.sh` gained a `git diff-tree ... | xargs git reset` line.
  - Earlier detours were spent checking whether hook-staged docs were sibling work: L496 (10-12), L1399 and L1415 (04:08Z), and L2823 (06:27Z).
- **Cost:** 4 detours, roughly 15 to 40 s each. This is a trap for any later `--no-verify` commit, which would revert the doc.
- **Fix**
  - The commit verb from item 8 resyncs every path in the commit.
  - The hook names the index it staged into.
  - Item 10 removes most of the churn that makes this matter.
- **Occurrences:** 4.

### 10. PHYSICS.md changes in every commit, mostly for its own sha stamp (friction)

- **Evidence**
  - `git log --since=2026-10-12T23:00 -- docs/PHYSICS.md` gives 45 commits, which is all 45 commits that day.
  - Per-commit numstat: 36 of the 45 changes are exactly 1+/1-, the "Derived at" line.
  - `scripts/generators/gen_physics_sheet.py:132,146` stamps `git rev-parse --short HEAD`, which is the parent of the commit being made. The sheet therefore names a stale sha by construction.
  - The same file's `--check` mode (lines 182-183) already strips the stamp with the comment "sha churn is not staleness". Write mode does not.
  - `docs/PRIOR_ART.md` changed in 15 of the 45 commits, from test-module count drift.
- **Cost:** a generated-doc diff in every commit, and with it item 9's checks and conflict surface.
- **Fix:** In write mode, reuse the `--check` strip and skip the write when the body is unchanged, or stamp a hash of the scanned inputs. Pin it with a test.
- **Occurrences:** 36 pure-churn diffs today.

### 11. The guardrail ratchet judges the working tree, so one seat's draft blocks every seat (friction, W264)

- **Evidence**
  - `scripts/githooks/pre_commit.py:242-262`: `guardrail_counts()` runs each checker with `cwd=ROOT` over the files on disk, not over what is being committed.
  - Refusal at L4896, 3 to 4. The cause was another seat's 80 uncommitted lines (L4915).
  - The shared tree now holds 51 modified tracked files and 139 untracked ones (`git status --short`).
- **Cost**
  - The block itself was short: Heimdall cleared it 63 s after the ask.
  - It set off the chain in items 1 and 2.
  - It pressured a sibling to commit his slice to unblock the house. Claude's own ask offered committing or parking the slice as the alternatives.
- **Fix:** Per W264, run the checkers against the tree being committed (a temporary checkout of the index). Report working-tree debt as a named, non-blocking warning.
- **Occurrences:** 1 refusal.

### 12. Every commit pays about 20 s of hook time, even a one-line one (friction)

- **Evidence**
  - In `state/authorship/seats.jsonl` for 10-13, the gaps between back-to-back scripted commits run min 20 s, median 22 s, max 93 s (31 pairs).
  - `pre_commit.py:503-521` regenerates six docs, then runs eight guardrails, then the comprehensibility check. Because regeneration comes before the ratchet, a refused commit still pays the full cost.
  - W263's trigger cites "a 2-minute commit behind a slow pre-commit hook" as what made the wedge detector fire.
  - That the gap is mostly hook time is inferred. It also includes git's own work and the post-commit ledger write.
- **Cost:** about 16 minutes over 45 commits. The false HARD WEDGE page (item 17).
- **Fix:** Cache each guardrail's result by a hash of its inputs, as `check_unbound_names` already does. Skip generators whose inputs did not change.
- **Occurrences:** 45 commits.

### 13. CRLF: three house writers emit it, and the warnings that mattered were filtered out (friction)

- **Evidence**
  - Byte counts with py, which are reliable where `grep '\r$'` in Git Bash over-counts:
    - `docs/MODULE_INDEX.md`: 413 of 413 lines CRLF;
    - `docs/PRIOR_ART.md`: 542 CRLF;
    - `docs/WISHLIST.md`: 2,231 CRLF;
    - `docs/PHYSICS.md`: 0.
  - Writers that do not pin LF:
    - `scripts/generators/gen_arch_index.py:91`;
    - `scripts/generators/gen_prior_art_register.py:169`;
    - `scripts/generators/gen_ports.py`;
    - `cmd_wish` in `agent_cli.py`, through `path.write_text(text, encoding="utf-8")`.
  - Only 3 of the 6 pre-commit generators (physics, master_map, doors) pass `newline="\n"`.
  - Three files in another seat's lane are also CRLF in the working tree: `core/comm/toolbox.py` (2,062 lines), `core/comm/seat_identity.py` and `scripts/bifrost_ui.py`.
  - The scratch commit logs hold 146 "LF will be replaced by CRLF" warnings: 124 in `commit_stage2a.log`, 6 in `commit_fixes.log` and 16 in `commit_batchb.log`. The 62 distinct files in `commit_stage2a.log` are almost all new `.glsl` and `.card` files with no eol rule.
  - `grep -v CRLF` appears in 16 transcript lines.
  - At 14:13 EDT, 86280221 records that a fresh worktree of bdd5c8fc failed 9 pins on CRLF `.glsl` files.
  - The `.gitattributes` header records the same trap biting on 2026-09-16 and 2026-09-17.
  - A census at L5788 still shows `.jsonl` (73 files) and `.ps1` (31) without a rule.
- **Cost**
  - The early signal sat 6 h 38 min, from 07:35 to 14:13 EDT.
  - 9 pins failed in a clean checkout.
  - The habit of filtering warnings also hid the BLOCKED line (item 8).
- **Fix**
  - Make `* text=auto eol=lf` the default, keeping the existing exceptions (cmd and bat as CRLF, binaries).
  - Or add a hook check that every newly added text extension has an eol rule.
  - Pin `newline="\n"` in the generators and the wish door.
- **Occurrences:** 146 LF-to-CRLF and 27 CRLF-to-LF warnings in three logs. Third occurrence of the trap.

### 14. Today's wish and lesson carry wrong magnitudes from mixed clocks (other)

- **Evidence**
  - W265 (`docs/WISHLIST.md` line 1780) says the sweep came "hours later" and that "HEAD sat red ... for six hours". The facts:
    - the refusal was read at 15:58:42Z;
    - 1d96275d is 12:00:24 -0400, which is 16:00:24Z, about two minutes after the refusal;
    - the red window was 16:00:24Z to 18:08:36Z, 2 h 08 min.
  - "Six hours" is 12:00 EDT read against 18:08 UTC.
  - The lesson `a_refused_commit_leaves_its_files_staged_for_the_next_seats_plain_commit` (L5718) repeats both numbers.
  - W263 (line 1778) says the false HARD WEDGE page repeated "for 40+ minutes". The transcript shows 4 page injections between 11:33:27Z and 11:44:35Z. The pager record's ts is 11:32:39Z, and the page was cleared at 11:45:28Z, about 13 min in all. Whether another surface carried it longer is unknown.
- **Cost:** durable records off by about 3x. Readers calibrate on them.
- **Fix**
  - Correct W265, W263 and the lesson. The record holder decides.
  - Compute spans with a tool that normalises every timestamp to house time; never subtract them by hand across sources.
- **Occurrences:** 3 numbers in 2 wishes and 1 lesson.

### 15. The events verb silently ignores --kind without --search (friction)

- **Evidence**
  - `agent_cli.py:5630-5633`: without `--search`, the verb calls `get_event_log().recent(limit, agent=...)`. `--kind`, `--since`, `--until` and `--track` are accepted and dropped, though the help lists them as filters.
  - L4307 (13:19:09Z): the agent noticed the filter was not filtering.
  - L5562–L5563 (18:07:08Z): `events --kind bifrost_msg --json | py -c ...` failed with a JSON decode error.
- **Cost:** 2 wasted calls across 2 message hunts.
- **Fix:** Apply the filters, or refuse them loudly. Pin it with a test.
- **Occurrences:** 2.

### 16. The wish verb rejects prose after options, and the wishlist has duplicate ids (friction)

- **Evidence**
  - L4000/L4003 (11:45:10Z): `wish claude --trigger ... --land ... "<text>"` failed with "unrecognized arguments".
  - `agent_cli.py:8715-8719` declares `text` as `nargs="*"`. Placed before the options, it matches empty, and argparse then rejects the trailing text.
  - The agent blamed special characters (L4007) and switched to `--text-file`, both here and for W264 (L4932).
  - The wish door warned that 15 ids repeat (L4016). `grep` confirms W00, W57–W69 and W211 each appear twice among 278 entries.
- **Cost:** 1 failed call, 2 scratch text files, ambiguous wish ids.
- **Fix:** Use `parse_intermixed_args`, or a `--text` option. Renumber the duplicates at the next curation.
- **Occurrences:** 1 failure. 15 duplicate ids.

### 17. The false HARD WEDGE page was acked by hand-rolled Python (hand_rolled_script)

- **Evidence**
  - The page's text was frozen at "aged 12585s" in all four injections (L3731, L3749, L3841, L3963).
  - The page says "then ack" but names no verb (W263).
  - The ack was `py -c "from core.comm import pager; pager.clear_key('claude#9d62784c:hard_wedge')"` (L4019, 11:45:28Z).
- **Cost:** a recall detour into the pager's internal API.
- **Fix:** Add `py agent_cli.py page-ack <key>` and print it in the page text. Show the live age, not the stored one.
- **Occurrences:** 1.

### 18. A UI reload was requested for a service that was not running (friction)

- **Evidence**
  - Heimdall's handoff at 16:39:29Z (bus 1791909569804-0) asked claude to reload 8787.
  - `core/comm/toolbox.py:1323-1330`: `reload_ui` is a no-op for his seat. It tells him to hand the reload to claude, without checking whether anything is listening.
  - Claude checked and found no process, no listener and no scheduled task (bus 1791909762400-0 to Heimdall at 16:42:42Z).
  - Claude asked Daniel whether to start it (bus 1791909766880-0, 16:42:46Z). Heimdall acknowledged at 16:42:48Z.
  - The UI was already known to be down: a dormant-bench note at L2075, and a deferred item at L50.
- **Cost:** one round trip (about 3 min), and an open question to Daniel, unanswered as of the last record (18:16Z).
- **Fix:** `reload_ui`, and any "reload X" handoff, probes the port first. If nothing answers, it says "not running; starting it is the operator's call" and routes the question to Daniel directly.
- **Occurrences:** 1.

### 19. A relayed ruling was held correctly, but the confirmation question went to the wrong channel (friction)

- **Evidence**
  - Heimdall relayed a ruling attributed to Daniel, about agents proposing their own renames (bus 1791909436465-0, 16:37:16Z).
  - Claude declined to change `core/fleet/residents.py` until Daniel confirmed (L5065–L5066, 16:39:41Z). That was the right call.
  - But claude asked in the desktop chat, while Daniel was writing from Discord: his messages carry `source: discord` in their bus metadata.
  - The question reached the bus at 18:11:14Z (bus 1791915074381-0, L5685), 1 h 32 min later. No reply from Daniel had arrived by the last record.
- **Cost:** 1 h 32 min before the question reached him. The residents change still waits.
- **Fix:** Reply where he is. When the operator's last message came over the bus, questions for him go on the bus. Add this as a line in the conductor doctrine, or as a stop-hook check.
- **Occurrences:** 1.

### 20. The deepseek seat's commit messages arrive wrapped in quotes (friction)

- **Evidence**
  - `git log --format='%h %s' --all | grep '^[0-9a-f]* "'` finds 15 commits whose message starts with a literal double quote. 14 are from 2026-09-24/25. 47ebdec0 is from 10-13.
  - `od -c` shows 47ebdec0's message wrapped in `"`...`"`.
  - The authorship ledger attributes all 15 to seat=deepseek.
  - Heimdall's still-uncommitted toolbox patch is about Windows quoting in the shell-seat exec path. That it causes this is inferred: `core/comm/toolbox.py` is modified and `tests/test_win_exec_powershell_quoting.py` is untracked.
- **Cost:** a cosmetic scar in public history, 15 times.
- **Fix:** `scripts/githooks/commit_msg.py` rejects or strips a message wholly wrapped in matching quotes.
- **Occurrences:** 15.

### 21. A fan-out lane was sent to a seat already over budget (friction)

- **Evidence:** Claude's request to kimi at 06:18:52Z (bus 1791872332352-0) was refused in the same second by the runner's budget guard (bus 1791872332887-0), though presence listed kimi online (L2669). The amounts are omitted here.
- **Cost:** small. One lane of the overnight fan-out fell to Heimdall alone (L2839).
- **Fix:** Show budget state in presence and the roster, and have `bifrost_send` warn before sending to a seat in budget refusal.
- **Occurrences:** 1.

### 22. 91 local commits are unpushed (other)

- **Evidence:** `git rev-list --count origin/master..HEAD` gives 91. `origin/master` is 1d6e070a, dated 2026-10-07 19:36 EDT.
- **Cost:** unknown. All of tonight's work exists only on this disk. The machine is at 100+ hours of uptime, inside the window where past freezes happened.
- **Fix:** Daniel's call. Push once the door gate allows, or take a dated off-machine snapshot. Item 1's history repair, if wanted, is easier before a push.
- **Occurrences:** 1.

### 23. The retro itself re-derived transcript tooling (hand_rolled_script)

- **Evidence**
  - This lane wrote six scan scripts: `scan.py`, `view.py`, `count.py`, `wake.py`, `wakeout.py` and `stops.py`.
  - The scratchpad already held `myscan.py`, `scan2.py` and `scan_color.py` from earlier in the night.
  - Gotchas hit on the way:
    - py's stdout crashed on cp1252 until run with `-X utf8`;
    - py `print` emits CRLF into pipes, which broke a `git cat-file` loop;
    - `grep -c $'\r$'` in Git Bash counted every line as CRLF;
    - the transcript stores each tool result more than once per JSONL line, so raw grep counts overstate.
  - The session scratchpad is shared by every subagent of the fan-out. A file named `scan.py` was nearly a collision.
- **Cost:** about 10 minutes of this lane. The same again in every lane that scans the transcript.
- **Fix:** A `py agent_cli.py transcript {grep,view,count}` verb. It should stream line by line, deduplicate tool results, convert UTC to house time and print UTF-8. Also, a lane subfolder per fan-out agent in the scratchpad.
- **Occurrences:** at least 9 scan scripts in one scratchpad.

### 24. The temporary-index commit was derived twice, and its lesson was scoped too narrowly to prevent item 1 (rederivation)

- **Evidence**
  - The method was first derived at 06:58Z for the lean-light commit, which sat beside a sibling's hunks in the same file (L3084–L3108).
  - It was filed at 14:43Z as the lesson `partial_commit_beside_a_siblings_hunks_needs_a_temp_index` (L4644–L4666). That lesson's contraindication says a plain pathspec commit is fine when the whole file is yours.
  - The batch-B script at 15:58Z therefore used `git add` and a pathspec commit (L4875). Its files were wholly claude's; the danger lay in the refusal leaving them staged, which the lesson did not cover.
  - The method was re-derived at 18:00Z as `commit_paths.sh` (L5393, L5433).
- **Cost:** two derivations of one procedure in one session, and a lesson that pointed away from the actual hazard.
- **Fix:** The `commit-only` verb from item 8 retires the question. Re-scope the lesson so the temporary index is the default whenever other seats commit to the same clone.
- **Occurrences:** 2 derivations.

### 25. Two prior lessons named this exact hazard, and recall did not surface them at the refusal (missed_existing_tool)

- **Evidence**
  - `mirror_refusal_leaves_tree_staged` and `a_rename_has_no_safe_parked_state` both say that staged-but-uncommitted state is the dangerous state, and that a refusal must unstage.
  - They exist in the store (they surfaced at L5725, at 18:11:59Z, after the fact).
  - W265 records that recall-at-action surfaced neither when the hook refused at 15:58Z.
- **Cost:** the whole of item 1.
- **Fix:** Make the refusal text itself name the staged paths and the unstage command (W265 point 4). Also feed a hook refusal's text into recall-at-action as a trigger.
- **Occurrences:** 1.

### 26. What went well (went_well)

- **Clean-worktree verification caught two defects the main tree hid.**
  - The untracked `tests/fixtures/glsl_cards` (L4873, 15:57:50Z).
  - The CRLF `.glsl` checkout that failed 9 pins (86280221).
  - `git worktree add` appears in 16 transcript lines.
  - Keep it, and fold it into the commit verb.
- **The bus spill-to-blob worked as designed.**
  - Heimdall's 14,226-character report was kept to its first 7,766 characters, with a fetch instruction (bus 1791872451175-0, meta `spilled`).
  - Claude fetched the blob straight into `research/reviewed` (L2699, L2707).
  - It was the day's only spill. The 11,733-character reply at 08:02Z fit under the cap.
- **Heimdall unblocked the house fast.** He cleared the ratchet 63 s after the ask (15:59:21Z to 16:00:24Z) and explained the key-family choice clearly.
- **The authorship ledger attributed commits correctly** where git cannot. `state/authorship/seats.jsonl` distinguished the deepseek commits (lines 1110 and 1117) even though git's author and committer fields are identical for every commit.
- **The UI start decision went to Daniel**, not to a guess (bus 1791909766880-0).
- **The relayed ruling was not acted on** before confirmation (item 19).

## Coverage

**Read in full or in the relevant part:**

- `git log`, `show`, `reflog` and `numstat` for every commit since 2026-10-12. That is 45 commits on 10-13, including 86280221, be0fc4c8 and f248653a, which landed during this retro.
- `state/authorship/seats.jsonl` rows 1070–1124.
- `scripts/githooks/pre_commit.py` (whole).
- `scripts/bifrost_wake.py` (admission chain, args, `WAKE_WORTHY_KINDS`) and `core/comm/wake_tiers.py`.
- `agent/bifrost_pull.py` (`standby`, peek rendering), `core/comm/bifrost_api.py` (`_pending_peek`) and `agent/harness/context.py` (`_unread_count`).
- The prompt hook's bus line.
- `agent_cli.py` (`cmd_events`, wish parser, `cmd_wish` writer) and `core/comm/toolbox.py` (`reload_ui`).
- `gen_physics_sheet.py` and the write calls of every generator.
- `.gitattributes`.
- `docs/WISHLIST.md` W263–W265, plus a duplicate-id scan.
- **Redis, read-only:** `XRANGE` of `bifrost:inbox:claude` (25 entries) and `bifrost:work:inbox:claude` (23) for 10-13, and claude's outbound entries in the deepseek, daniil and kimi streams. Also HGETALL of both claude cursors, and XINFO.
- **The main session transcript:** 29.9 MB, about 5,900 lines, streamed line by line with small py scanners (each process well under 1 GB).
- The 15 watcher output files.
- The scratch commit scripts and logs.

**Skipped, and why:**

- The 208 subagent transcripts, which other lanes cover.
- Heimdall's own session, which is not on disk as a transcript; only his bus side was read.
- The Discord surface.
- Running tests or `agent_cli.py` verbs: the verbs can write touch or presence events to Redis, and the rule was never write to Redis. So "HEAD sat red" is inferred from the absent modules, not from a test run.
- Bodies of bus messages beyond what each item needed.
- September backlog contents.

**Unknown:**

- Whether the HARD WEDGE page reached a surface other than the prompt hook for the 40 minutes W263 claims.
- Why the watcher's "held below floor" count read 0 while ambient-tier nudges arrived. The likely reason is that the nudges arrived while no watcher was armed.
- What Heimdall did with his toolbox patch after his unanswered 13:49Z question.

No Shadertoy corpus code, no private data and no reverse-engineering technique appears here. The only words quoted are Daniel's own chat words.
