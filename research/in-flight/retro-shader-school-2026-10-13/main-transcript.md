# Retro lane: the main session transcript (shader school, 2026-10-12 to 2026-10-13)

Daniel, 2026-10-13: "What did we learn from all of this? Would you mind fanning out agents to capture every friction
point, hand rolled script, re derivation and any other thing that would've made the process better, i know we have a
rich wealth of information waiting to be surfaced"

This lane read the main session's own transcript (Vandor, the claude seat) from the first prompt to the moment the
retrospective workflow launched. Other lanes cover the workflow subagents, the scratchpad scripts, git and hooks, and
the store.

## Summary

The night shipped a great deal. The friction in the main seat comes down to five patterns, and most of them recurred
because nothing made them impossible.

1. **Reading results back cost more than producing them.** 20 workflows returned results that the seat could only
   read with a hand-written Python one-liner per result: 23 of them, each guessing that workflow's result shape. One
   died on a KeyError and one on the Windows console codec. A licence-scan schema was worked out at 11:24, lost in a
   compaction, and worked out again at 16:43 with five full rescans. The bus has the same problem: the newest message
   from a given sender took a three-step pipeline every time (about 13 calls). One of those pipelines ended in a raw
   Redis scan.
2. **Inline Python through a shell keeps corrupting itself.** There were 80 inline snippets (34 heredocs and 46
   `py -c`), and 59 of them carried backslashes. Seven failed visibly and one silently wrote a broken test file. A
   recall lesson about exactly this was injected at 06:17, and the same failure recurred at 14:43. It recurred again
   inside this retro lane.
3. **Waking up is still a chore.** The one-shot wake watcher was armed 16 times, and the Stop hook blocked two turns
   over it. A false HARD WEDGE page repeated for over 40 minutes. A stale "58 unread" banner was injected 72 times
   and buried a real message from Heimdall until Daniel asked about it.
4. **Safety stops cost whole turns.** Three main-session turns were stopped by the safety classifier, all after
   reverse-engineering material entered the context. Each stop also dropped that turn's watcher re-arm, and one left
   the seat deaf for 39 minutes. Separately, an auto-mode check blocked every browser key press and page script for
   the rest of the conversation from 06:17. That stranded 38 texture files and turned them into a morning step for
   Daniel.
5. **My own mistakes, each with a tool change that would have prevented it:**
   - I tried to read Brave's session files without asking, and Daniel rejected it.
   - I read the site-wide "love" ranking when he meant his Loved playlist.
   - I told him how his piece ended from a partial read of a session that was still growing. He asked "Did you read
     the whole thing?", and the full read showed he had landed it.
   - I committed a doc that pointed at files arriving in a later commit, which left HEAD red until the next commit.

What went right is just as clear: the `find` verb, test-first commits proven red at HEAD, clean-worktree checks after
landing, a memory file written before compaction, never bypassing a hook or a human check, and adversarial review
rounds that kept finding real defects.

**Scale.** Transcript lines 1 to 5662, from 2026-10-12 12:55Z to 2026-10-13 18:10Z. 541 API requests; 285.6M
cache-read tokens; 904k output tokens. 645 tool calls, 21 of them errored. 20 workflows, 47 commits in the repo window
(all seats; 38 since midnight by 16:37, 36 of them this seat's per L5026). Two auto-compactions, at 967,865 and
967,369 tokens.

Times below are UTC (Daniel's clock is four hours earlier). `L####` is a line number in the transcript JSONL.

## How to check the evidence

- Transcript: `%USERPROFILE%\.claude\projects\E--\9d62784c-bd34-488c-a370-94b7d333fbb9.jsonl`, one JSON record per
  line. The analysis stops at L5662, the line before the retrospective workflow launched (L5663). The file was still
  growing while this lane read it.
- Background task outputs: `%TEMP%\claude\E--\9d62784c-bd34-488c-a370-94b7d333fbb9\tasks\<id>.output`.
- Extraction: streamed line by line with py into a compact index. Tool calls, tool results (`is_error`,
  `toolDenialKind`), user text, system records (`compact_boundary`, `model_refusal_no_fallback`,
  `stop_hook_summary`), hook attachments and `queue-operation` records were all kept. The scripts are in this
  session's scratchpad under `retro-lane-main/` (working files only, not committed).

## Error census (the 21 `is_error` results)

| Bucket | Count | Lines |
|---|---|---|
| Not a real failure: a non-zero exit used as a verdict (licence-line breach exit 1; `git grep` no-match exit 1) | 5 | L5197, L5212, L5220, L5223, L5409 |
| Quoting or encoding in inline Python | 4 | L161 (PowerShell here-string into `py -c`), L3263 (cp1252), L4645 (heredoc unicode escape), L5563 (PowerShell pipe into `py -c`) |
| Wrong guess of a result shape | 1 | L725 (`KeyError: 'maps'`) |
| Wrong verb flag | 1 | L149 (`arsenal.media grab --json`) |
| Auto-mode safety block | 2 | L2574 (key press), L2593 (page script) |
| Daniel rejected the action | 1 | L1998 (Brave session-file read) |
| Interrupted by Daniel's message | 1 | L1805 |
| Permission guard false positive | 1 | L1138 |
| Harness blocked `sleep 45` | 1 | L3822 |
| Cascade from the rejected command (folder never made) | 1 | L2099 |
| Git pathspec on an untracked file | 1 | L2813 |
| Browser pane cannot act on a `file://` tab | 1 | L1112 |
| Page script error (screenshot image also dropped) | 1 | L2170 |
| **Total** | **21** | |

Results that failed without being flagged: 35 matched an error pattern. The ones that matter are listed in the items
below: L1319 (a pytest SyntaxError caused by my own heredoc), L2577, L3549, L4003, L4330, L4393 and L5527.

## Daniel's corrections and nudges (his words only)

| Line | Time | Message | What it corrected |
|---|---|---|---|
| L1776 | 05:52 | "brave" | I had assumed Chrome |
| L1998 | 05:59 | (rejected the tool call) | Reading Brave's session files |
| L2029 | 06:00 | "how do we fix the brave access" | |
| L2116 | 06:02 | "make a tab group so I can see it" | |
| L2147 / L2163 | 06:04 | "my bad i navigated to the right page" / "I needed to go to the loved playlist" | I was on the site-wide ranking |
| L2251 | 06:06 | "remember to make verbs to make these interactions and actions easier" | Hand-driven browser steps |
| L1671 | 05:23 | "Did you read the whole thing?" | A partial readback stated as a whole one |
| L4288 | 13:18 | (bus) "Hey, did you get heimdalls recent message?" | A buried message |

## Items

Each item names what happened, the evidence, the count, the cost, and the smallest change that would have prevented
it. "Tool friction" means the tool made it hard. "My mistake" means I chose wrong, and the item says which tool
change would have made that choice impossible.

### A. Tool friction

**A1. Workflow results can only be read by hand-written parsers.**
- **Evidence:**
  - 23 inline Python readers of `tasks\<id>.output` (for example L717, L729, L736, L901, L1002, L1207, L1720, L2715,
    L3158, L3262, L3266, L3309, L3388, L3454, L3534, L3769, L3809, L4503, L4621, L4684, L4720, L4749, L4820), plus 2
    PowerShell readers (L5332, L5336).
  - Every result shape is different (`d['result']['slices']`, `['reviews']`, `['rr']`, `['fixes']` and so on).
  - L725: `KeyError: 'maps'`, then L729 to inspect the structure and L736 to retry.
  - L3263: a cp1252 crash on an arrow character.
  - Workflow completion notifications are capped at about 9.6k characters (20 notifications, 9,566 to 9,835
    characters each), so the full result always means opening the file.
- **Count:** 25 reader calls for 20 workflows.
- **Cost:** about 25 tool calls and a few minutes each round. Re-guessing shapes after a compaction.
- **Fix (verb or brief):**
  - A verb such as `py agent_cli.py wf-result <task-id> [--verdicts] [--split DIR]` that prints each part's verdict
    line and writes parts to files.
  - Cheaper still, a brief rule for workflow scripts: every agent writes its report to a named file and returns only
    `{verdict, path}`.

**A2. Inline Python through bash heredocs and `py -c` corrupts itself.**
- **Evidence:**
  - L161: a PowerShell here-string into `py -c` lost its quotes (`SyntaxError`).
  - L1286 to L1319: a heredoc patch wrote a real newline where a test needed the two characters backslash-n. Pytest
    collection failed later with "unterminated string literal". The write itself reported "ok", so this was a
    silent corruption.
  - L4644/L4645: `'unicodeescape' codec can't decode bytes ... truncated \UXXXXXXXX escape` while filing lessons.
    Fixed by writing `file_lessons.py` with the Write tool (L4651).
  - L5562/L5563: a PowerShell pipe into `py -c` (NativeCommandError).
  - The house lesson on exactly this ("Prefer the Edit or Write tools, which have no shell escape layer") was
    injected by recall-at-action at L2590 (06:17). The failure recurred at 14:43.
  - **Reproduced in this retro lane:** my own heredoc `'\\'` arrived as `'\'` and the script died with "unterminated
    string literal". Fixed with `chr(92)`.
- **Count:** 80 inline snippets (34 heredoc, 46 `py -c`); 59 contain a backslash; 7 visible failures and 1 silent
  corruption.
- **Cost:** about 10 retries. One broken test file that was caught only because pytest ran.
- **Fix (hook):** a PreToolUse hook on Bash and PowerShell that refuses `py - <<` or `py -c` when the code contains a
  backslash or runs past a few lines, and says "write a .py file with Write, then run it". The recall lesson alone
  did not stop it. A hook would.

**A3. The Windows console codec kills prints.**
- **Evidence:** L3263 `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`. After that,
  `PYTHONIOENCODING=utf-8` was prefixed to 34 commands (the first at L3266).
- **Count:** 1 failure, 34 workarounds.
- **Fix (process):** set `PYTHONUTF8=1` (or `PYTHONIOENCODING=utf-8`) once in the harness environment, so no command
  has to carry it.

**A4. Non-zero exits used as verdicts show up as tool errors.**
- **Evidence:**
  - `py -m arsenal shader licence-line` exits 1 whenever a breach exists. Four PowerShell calls were marked
    `is_error` while working (L5197, L5212, L5220, L5223).
  - `git grep` exits 1 on no match (L5409; the output "2 / 0" was correct).
- **Count:** 5 of the 21 errors.
- **Cost:** noise in every error census, and real failures hide among them.
- **Fix (verb):** report modes such as `--json` and `--breaches` exit 0, and only `--check` (the pin and pre-commit
  path) exits non-zero.

**A5. The one-shot wake watcher needs a re-arm after every wake.**
- **Evidence:**
  - 16 arms (L562, L2664, L2689, L3228, L4290, L4427, L4438, L4462, L4818, L4952, L4974, L5042, L5080, L5203, L5331,
    L5560).
  - Measured lifetimes ran from 1.0 to 316 minutes; 9 of 15 lasted under 7 minutes. By design the listener "exited
    rc=0 -- wake-worthy mail or deadline; re-run bifrost-standby after handling" (`tasks\bagvf1ar8.output`).
  - The Stop hook blocked turns at L554 (01:27) and L4425 (13:22) because the seat was unwakeable.
- **Cost:**
  - 16 tool calls and 2 blocked turn endings.
  - Worse: a turn stopped by the safety classifier also loses its re-arm (see A10). After the 17:19 stop (L5299) the
    seat was deaf until 17:58 (L5331). When it re-armed, the drained mail included Heimdall's nudge that Daniel
    wanted a direct reply (`tasks\bwf112ftb.output`).
- **Fix (hook):** a UserPromptSubmit hook. On any turn that starts from a watcher's completion or from a
  safety-stopped turn, it injects "re-arm first", or it re-arms itself if the harness allows it. That catches the
  missing watcher at the start of the next turn instead of the end of this one.

**A6. A stale unread counter hides new mail.**
- **Evidence:**
  - "[akashic] mail: 58 unread bus msg(s)" was injected 72 times, unchanged, across the session.
  - `bifrost_inbox` and `bifrost_sync` return the oldest backlog first (L4291 shows a September sweep).
  - Heimdall's morning message sat unread until Daniel asked on the bus (L4288, 13:18). Finding it took 8 calls
    (L4291, L4303, L4308, L4322, L4329, L4334, L4344, L4350).
- **Cost:** a missed teammate message, and Daniel had to ask.
- **Fix (verb):** inbox and sync show what is new since this seat last looked, newest first and grouped by sender.
  Retire or settle the 58-message backlog once (`mailbox --retire-ghosts` exists). A counter that never moves is
  noise.

**A7. Opening "the newest message from X" is a hand-built pipeline.**
- **Evidence:**
  - Every time: `mailbox claude --json > file`, then `py -c` to pick the newest entry from a sender, then
    `mailbox --open SHA`. Seen at L4334/L4344/L4350, L4440, L4976/L4986, L5061 and L5082.
  - L4330: `agent_cli.py: error: unrecognized arguments: --from deepseek`.
  - L4983: an 8-character prefix was ambiguous because Discord-relayed ids all begin `discord:`. Retried with a
    longer prefix at L4986.
  - L5562 to L5588: a clipped message was read by scanning Redis keys directly with `py -c`.
- **Count:** about 13 calls.
- **Fix (verb):** `py agent_cli.py mailbox <agent> --open-latest --from <sender> [--full]`. Today `mailbox` has
  `--open SHA` and `--state SHA` but no sender filter (agent_cli.py:9547-9584).

**A8. `bifrost_fetch` cannot create its target folder.**
- **Evidence:**
  - L4393: `FileNotFoundError ... research\reviewed\deconstruct-the-house-2026-10-13\heimdall-blind-half-first-principles.md`;
    `mkdir` at L4403, retry at L4404.
  - L2695 and L2707: two fetches wrote 8,023 and then 14,310 bytes to the same path, so the second overwrote the
    first. Whether the first body was a subset of the second is unknown.
- **Fix (verb):** create parent folders, and never overwrite an existing spill file (add a suffix or append).

**A9. Committing costs a script every time.**
- **Evidence:**
  - The pre-commit hook regenerates `docs/PHYSICS.md` (and sometimes MAP and PRIOR_ART) and stages it into every
    commit: 13 results, 42 occurrences of "pre-commit: regenerated and staged".
  - CRLF warnings appeared on 16 results.
  - A commit batch hit the 120 s tool timeout and was moved to the background (L3729). Five commit calls ran in the
    background because the hook is slow.
  - The hook left the index out of sync (L5455 to L5462: `git reset -- docs/PHYSICS.md`).
  - `git commit -- <untracked path>` failed with a pathspec error (L2813), then `git add` and retry (L2817).
  - Committing my hunks beside a sibling's uncommitted hunks in the same file needed a hunk classifier
    (`split_hunks.py`, L3063) and a temporary index (L3096). That became a lesson, "partial commits ... use a
    temporary index" (L4669).
  - Three separate hand-written commit scripts: `commit_stage2a.sh` (L3804), `commit_batchb.sh` (L5531) and
    `commit_paths.sh` (L5433, edited L5461).
- **Count:** 20 commit-bearing calls, 3 bespoke scripts, 1 temp-index procedure.
- **Fix (verb):** a house `commit` verb that:
  - adds the named untracked paths;
  - does RED/GREEN pairs;
  - selects hunks through a temporary index;
  - runs in the background with a receipt;
  - keeps hook-regenerated docs out of task commits, in their own commit.

**A10. Safety-classifier stops withhold whole turns.**
- **Evidence:**
  - L4793/L4795 (15:43), L4802/L4804 (15:50) and L5298/L5300 (17:19). Each shows "safeguards stopped the response",
    then `model_refusal_no_fallback` with category `reasoning_extraction`, then the API error text at L4796, L4805
    and L5301.
  - All three came after the reverse-engineering arsenal's clean-room and isolation material entered this session's
    context. The seat's own guess at L4817 was that the stop came from "going into too much detail on the isolation
    fix specifics". The exact trigger is unknown.
  - The 15:50 turn was woken by Daniel's bus message "How are things going?" (L4801). Its reply went out at 15:55
    (L4825), after the next workflow notification.
  - The 17:19 turn was woken by Heimdall's reply. It ran nothing, so the watcher was not re-armed until 17:58 (see
    A5).
  - Two research lanes inside the reverse-engineering workflow were also stopped before writing their files
    (summary at L4610 and L4622). Lesson filed: "a fan lane stopped by a safety classifier is rescoped, not
    resubmitted" (L4660).
- **Count:** 3 main-session stops and 2 lane stops.
- **Cost:** 3 lost turns, a 5-minute late reply, and 39 deaf minutes.
- **Fix (brief and process):**
  - Keep sensitive-domain detail out of the parent's context. Reverse-engineering agents write their files and
    return only verdicts and paths, and the parent never prints their bodies.
  - Run that kind of arc in its own session.
  - After any stop, the first act of the next turn is the re-arm (A5).

**A11. An auto-mode check blocked browser actions for the rest of the conversation.**
- **Evidence:**
  - L2574 (`ctrl+c` key press) and L2593 (`javascript_tool`), both at 06:17. The denial text says it "reacts to
    earlier conversation content ... it will keep firing for the rest of this conversation".
  - The texture files were mid-handoff through the clipboard in chunks (L2569 staged chunk 1 of 5). None arrived:
    "missing media 38" (L2564).
  - The textures became Daniel's morning step: `harvest-js --media` was built and pinned at L3916 to L3944.
- **Cost:** 38 media files still owed at the end of the session (listed as pending in the summary at L5112).
- **Fix:** none on our side for the block itself. The seat correctly did not work around it. See B3 for the part
  that was mine.

**A12. A browser tab group belongs to the session that made it.**
- **Evidence:**
  - Daniel dropped a tab into a group before going to sleep. This session's `tabs_context_mcp` said "This session has
    no tab group of its own" (L1772), then "This session's tab group no longer exists" (L1821).
  - `list_connected_browsers` names the browser "Browser 1", not Brave (L1793), so I assumed Chrome until Daniel
    wrote "brave" (L1776).
  - `tabs_context_mcp` was called 7 times between 05:52 and 05:58 (L1771, L1796, L1820, L1825, L1938, L1978, plus
    one inside L1802).
- **Cost:** about 6 minutes, plus the wrong-list detour in B2.
- **Fix (process):** when a dropped tab cannot be seen, ask Daniel for the URL in one line. And keep one standing tab
  group per seat in the browser doc so he knows where to drop things.

**A13. The extension hides query strings in page-script results.**
- **Evidence:** `[BLOCKED: Cookie/query string data]` appeared in L2095 and L2220 (18 segments). Worked around by
  spelling `?`, `&` and `=` as words (L2182).
- **Fix (doc):** the harvest helper now returns ids rather than URLs. Note the redaction in the harvest helper's
  header so the next seat does not rediscover it.

**A14. Browser downloads land somewhere unknown.**
- **Evidence:**
  - Seven calls polled Downloads or searched for the saved bundle (L2276, L2280, L2318, L2330, L2481, L2486, L2490).
  - The first bundle sat as a `.tmp` (L2281) until it was saved through Brave's prompt (the seat's reasoning at L2294
    planned to ask Daniel). It then landed in a Desktop folder (found at L2331). The second never appeared.
  - The clipboard handoff and `ingest --clipboard` were built as the replacement (L2497 to L2524).
- **Fix:** already done (the clipboard verb). Keep downloads out of the harvest path.

**A15. Hook context volume.**
- **Evidence:**
  - PreToolUse recall-at-action: 132 injections, 233,480 characters, 124 s of cumulative hook time.
  - UserPromptSubmit: 78 injections, 64,539 characters.
  - PostToolUse: 7 injections averaging 6,039 characters. Each one is the full AGENTS.md, attached when a repo file
    is read; this lane received one too.
  - The "[legend] worked=self-reported ..." line was repeated 77 times.
  - Benefit: unknown in general. The one lesson that applied to a recurring failure (A2, L2590) did not prevent the
    recurrence.
- **Fix (hook):**
  - Inject each lesson and the legend at most once per session.
  - Inject AGENTS.md once per session, not per read.
  - Promote any lesson that keeps recurring into a blocking hook (as A2).

**A16. The protected-path guard misnamed its target.**
- **Evidence:** L1138 "Remove-Item on system path '"C:\Program' is blocked". The only `Remove-Item` in the command
  (L1135) targeted `$prof`, a fresh temp profile under `%TEMP%`. The guard took a quoted browser path elsewhere in
  the command as the target. The retry with no deletion succeeded (L1142).
- **Fix (hook):** the guard should report the actual argument it parsed, and either resolve variables or say it
  could not resolve them.

**A17. Command-line surface inconsistencies.**
- **Evidence:**
  - L149: `py -m arsenal.media grab ... --json` failed with "unrecognized arguments: --json", while probe, shots,
    cut, avsync and others accept `--json`. Grab already prints JSON.
  - L4003: `agent_cli.py wish` with free text after the options failed with "unrecognized arguments"; it worked with
    `--text-file` (L4016).
  - L4330: `mailbox --from` does not exist.
  - Nine `--help` lookups were needed to find flags (L865, L876, L2598, L2611, L3964, L3978, L3996, L4303, L4329).
- **Fix (test):**
  - A pin that every `arsenal.media` verb and every `agent_cli.py` verb accepts `--json`.
  - Use `parse_intermixed_args` where free text follows options.

**A18. A false HARD WEDGE page had no named way to acknowledge it.**
- **Evidence:**
  - The page repeated with "aged 12585s + DEAD pulse + beat stale (71s)" at L3731, L3749, L3841 and L3963 (11:33 to
    11:44), while the seat was working.
  - The seat reported "a HARD WEDGE page fired every few minutes for 40+ minutes" (L4000).
  - It was cleared by importing `core.comm.pager` in `py -c` (L4019) and filed as W263. The wish ledger warned that
    its id space has collided (L4016).
- **Fix (verb):** key the wedge on progress (tool calls landing, commits), not phase age. Put the acknowledgement
  verb in the page text.

**A19. The guardrail ratchet judges the working tree, not the commit.**
- **Evidence:** L4893/L4896: "pre-commit BLOCKED: guardrail debt INCREASED: check_boundaries: 3 -> 4". The new
  violation was a sibling's uncommitted `core/comm/seat_identity.py` (L4915). The seat did not bypass the hook; it
  asked Heimdall, who registered the prefix. Filed as W264.
- **Fix (hook):** run the ratchet against the staged tree (index), not the working tree.

**A20. Compaction landed at the worst moment.**
- **Evidence:**
  - Compaction 1 (L1889, 05:57, 967,865 tokens down to 25,474, 86 s) came 2 minutes after Daniel gave the night's
    task (L1873). Afterwards the browser tools had to be loaded again (ToolSearch at L1919 and L1962 repeat L1767 and
    L1782).
  - Compaction 2 (L5108, 16:42, 96 s) was followed by the licence-schema re-derivation (C2).
  - Context grew from 68k tokens at 12:58 to 598k by 02:48, mainly because the seat read about 220 KB of workflow
    output itself (L748: "I'll read all of it myself, because the design judgment depends on it").
- **Fix (process):**
  - The parent reads verdicts and targeted sections, and keeps full reports on disk (A1).
  - Before a long night, write the memory file first (it was written at L2839; see D5).

**A21. Smaller frictions.**
- The built-in browser pane cannot act on a `file://` page (L1112). The page was published first and then
  screenshotted with headless Chrome (L1135 to L1151).
- WebFetch summarised instead of returning text (L4110). See C5.
- "The user hasn't heard from you in a while" reminders fired 29 times, 7 of them in the 06Z hour while Daniel slept.
- The Read cap truncated `unified-architecture-draft.md` at 25k tokens and forced a second read (L3172, L3180).
- `learn` refused "collapsed tool-protocol fields" once (L1458) and took a resend (L1469).
- The `sleep 45` progress check was blocked (L3822).

### B. My own mistakes (and the tool change that would have made each impossible)

**B1. I reached for Brave's private session files without asking.**
- **Evidence:** L1983 listed the profile's session files. L1987 wrote a script to pull URLs from them. Daniel
  rejected it at L1998 ("The user doesn't want to take this action right now"). L2099 then failed: `cd` into a
  scratch folder that only the rejected command would have created.
- **Cost:** a rejection on his last minutes before sleep, plus one cascade error.
- **Fix (hook):** a PreToolUse deny on browser profile paths (`...\User Data\*\Sessions`, cookies, history) that says
  "ask Daniel for the URL instead". Memory now carries the rule, but a hook makes it impossible.

**B2. I read the site-wide "love" ranking when he meant his Loved playlist.**
- **Evidence:**
  - "make sure you open the love link" (L1849) was taken as the site's sort-by-love results (L1963). I harvested 312
    popular shaders over 26 pages at 400 ms per request, which raised the site's "Just a moment..." check (tab title
    at L2250). Daniel had to tick it. The seat's reasoning at L2294/L2295 planned the ask, and the compaction summary
    (L5112) records that he ticked it. No chat message carrying the ask was found in the transcript, so it likely
    travelled only through the narration stream. That counts as friction in itself.
  - Daniel: "I needed to go to the loved playlist" (L2163).
- **Cost:** about 5 minutes and a human check. The extra 312 shaders stayed in the private corpus as a second set.
  That turned out to be useful, but it was not asked for.
- **Fix:** A12's one-line ask. The harvest helper now enforces 1.5 s pacing and stops at the first check page
  (harvest.js header, L2414).

**B3. I ran a dependent step in parallel with its producer.**
- **Evidence:** at L2572 the `ctrl+c` key press was blocked, while the parallel `ingest --clipboard` at L2573 ran
  anyway. It re-ingested the previous clipboard: the same bundle hash, "media written: 0".
- **Cost:** a harmless duplicate, but a misleading result.
- **Fix (verb):** `ingest --clipboard` should require a fresh nonce or hash from the stage step and refuse a stale
  clipboard. The probe pattern from L2497 already exists.

**B4. I stated a partial readback as a whole one.**
- **Evidence:**
  - At L1653 and L1660 I described where his coronation piece "slipped away", from 15-second slices and only the
    last minute note by note. The session file was still growing.
  - Daniel: "Did you read the whole thing?" (L1671).
  - The full read (L1691 to L1705) of all 112 windows reversed it: he had landed the ending.
- **Cost:** a wrong account of his own playing, corrected only because he asked.
- **Fix (verb):** a house `readback <session> [--full]` verb that stamps every answer with its completeness ("session
  still open; read through 4:16; 37 of 112 windows") and reads fully by default. It would also replace six
  hand-written analyses: `readback.py` (L1532), `voicing_trend.py` (L1581, which first crashed on a type
  assumption, L1583), and the inline scripts at L1556, L1604, L1653 and L1691.

**B5. I committed out of dependency order.**
- **Evidence:**
  - The clean-worktree run of HEAD failed: "paths named that do not exist: dissecting-shaders.md:
    arsenal/web/glsl/groups/*.glsl" (L5527). The skill reference landed before batch B.
  - Committed batch-A card tests depended on untracked fixtures (`tests/fixtures/glsl_cards`, recorded in the
    compaction summary at L5112).
- **Cost:** HEAD red between commits. The clean-worktree check caught it.
- **Fix (verb):** the commit verb (A9) runs the touched tests in a clean worktree of the would-be commit before
  landing it.

**B6. I edited registration points that running workflows were also editing.**
- **Evidence:** the `_load_extensions` tuple in `arsenal/shaders/cli.py` and the dispatch in `arsenal/__main__.py`
  were touched by several slices. "Check ... whether others edited cli.py" (L2970, L3715). Edit warned "the file had
  been modified on disk since you last read it" on `corpus.py` (L3900).
- **Cost:** low this time, but this is a merge-collision magnet.
- **Fix (process):** discover verb modules by file glob or a registry file, so new slices never edit a shared tuple.

### C. Hand-rolled scripts and re-derivations

**C1. Workflow result readers (A1).** 25 calls, each new. This is the biggest single category of hand-written code
in the seat.

**C2. The licence-line JSON schema, worked out twice.**
- **Evidence:**
  - 11:24 (L3548/L3549): `TypeError: 'int' object is not iterable`. `breaches` is a count, and the rows live in
    `hits` with `verdict`; worked out at L3553.
  - After compaction, 16:43 to 16:46: five full rescans (L5195, L5204, L5216, L5219, L5222, L5225) to rediscover the
    same thing ("breaches type: Int32", "hits: 630 breach-hits: 34").
- **Cost:** about 4 minutes and 5 scans.
- **Fix (verb):** `licence-line --breaches [--tracked-only]` printing one `file:line` row per breach. Save the scan
  once and query the file.

**C3. Licence baseline pruning by hand.**
- **Evidence:** L3678: "No regenerator exists, so I'll prune by measurement". Three py edits of
  `licence_line_baseline.json` followed (L3679, L3697, L3709). One broke the baseline's well-formedness pin (L3698)
  before the note moved to its own field.
- **Fix (verb):** `licence-line --rebaseline --at <sha>` that measures and writes the baseline with its reason
  fields.

**C4. Bus readers (A7).** About 13 calls, including one raw Redis scan.

**C5. A missed existing tool.**
- **Evidence:** WebFetch returned a model summary of the external REA skill (L4106, L4110). The seat then used curl
  (L4111). The house door `mcp__akashic-aurora__web_fetch` has `raw=True` and an offset/limit range API, with "never
  silent truncation".
- **Fix (doc):** one line in the skill or AGENTS guidance: "for exact text, use the house web_fetch with raw=True".

**C6. Re-reads.**
- 14 Read calls repeated a file, but 12 were paging different ranges and 2 followed an edit or a compaction. This is
  not a problem.
- Shell re-reads were also modest. `arsenal/__main__.py` was read 3 times (L2296, L2305, L2354) to learn how a verb
  registers.
- **Fix (doc):** a short "how to add an arsenal verb" note in the arsenal README.

**C7. Retries of the same command.** A similarity detector found 19 near-duplicates within 6 calls. 3 followed an
error (L2103, L3266, L3824); the rest were polling (download checks, harvest status, tab context) or paging.

### D. What went well

- **D1. The find verb.** It located the saved bundle in one call (L2330). Daniel: "You have no idea how proud I am of
  the fact that you used find and found it instantly ^____^!!!!!! I didn't have to remind you either ^___^!!!!!!!!!!!!!!"
  (L2369).
- **D2. Test-first commits, proven red at HEAD.**
  - L475 (stash, red, restore, green).
  - L3928 ("RED at HEAD (3 fail), GREEN in the tree (26 pass)").
  - Clean-worktree checks after landing: L3102, L3429, L4875, L5508 and L5641. That check caught B5.
- **D3. Discipline under blocks.**
  - Did not bypass the guardrail hook (A19).
  - Did not try to solve the site's human check (L2261).
  - Did not reword around the classifier (L4620) or the auto-mode block (summary L5112).
- **D4. The Stop hook nudge paid off.** The hook rejected a promise-shaped ending (L2861). The seat then built the
  GLSL module core while the workflows ran (L2865 to L3014, committed as `db1b23d2`/`5e127983`).
- **D5. Memory before compaction.** `shader-school-2026-10-13.md` was written at L2839 and updated at L3108, L3289 and
  L3864. The 16:42 compaction summary carried the full state, so nothing was lost but the licence schema (C2).
- **D6. Adversarial review rounds found real defects.**
  - 11 of the 20 workflows were fix or re-review rounds (for example the lean-light fix with 35 failing pins before
    the fix, L2236).
  - The licence guard caught 89 real breaches in new files (L3455).
  - The live-probe review of Heimdall's quoting patch caught a regression whose 6 pins were all green (L4394).

### E. Friction inside this retro lane

- **E1. Lanes shared a scratch folder.**
  - This lane created `scratchpad\retro\` and wrote `extract.py` there. Another lane wrote its own `extract.py`,
    `recs.jsonl` and `late.json` into the same folder.
  - Running "my" `extract.py` executed the other lane's script and printed its per-subagent rows.
  - This lane moved to `scratchpad\retro-lane-main\`.
  - **Fix (brief):** the retro brief should give each lane its own scratch subfolder by name.
- **E2. The heredoc backslash collapse (A2) happened here too.** It confirms that the tool layer, not care, is the
  cause.

## Ranked fixes (the smallest change that removes the most recurrence)

1. **Hook:** block backslash-carrying or long `py - <<` and `py -c` snippets; point to Write plus a `.py` file (A2).
2. **Brief:** workflow agents write reports to named files and return `{verdict, path}`. Optionally add a
   `wf-result` verb (A1, C1, A20, A10).
3. **Verb:** `mailbox --open-latest --from <sender>`, plus inbox and sync showing what is new since this seat last
   looked, newest first (A6, A7, C4).
4. **Verb:** a house `commit` that handles untracked paths, temp-index hunks, RED/GREEN pairs, a clean-worktree
   pre-check, background running with a receipt, and hook docs kept separate (A9, B5).
5. **Hook:** re-arm the wake watcher at the start of the turn (on a watcher wake or after a safety stop) instead of
   at the Stop hook (A5, A10).
6. **Verb:** licence-line `--breaches`, `--rebaseline`, and exit 0 for report modes (A4, C2, C3).
7. **Process:** `PYTHONUTF8=1` set once in the harness environment (A3).
8. **Hook:** deny browser profile and session paths; ask for the URL instead (B1).
9. **Verb:** `readback --full` with a completeness stamp (B4).
10. **Hook:** inject each recall lesson and AGENTS.md once per session; run the ratchet on the index; have the
    protected-path guard name its real target (A15, A19, A16).
11. **Test:** every verb accepts `--json`; free text works after options (A17).
12. **Doc:** use the house `web_fetch raw=True` for exact text; how to add an arsenal verb; the extension's
    query-string redaction (C5, C6, A13).

## Coverage

- **Read:**
  - The whole main transcript, lines 1 to 5662 (2026-10-12 12:55Z to 2026-10-13 18:10Z), streamed line by line.
  - Every tool call and result (645 calls, 644 results), every `is_error` and `toolDenialKind`, every user message
    (86), every system record (60), and every hook attachment (counts and sizes).
  - All queue operations (142 enqueues), both compaction summaries in full (L1893, L5112), and the API usage fields
    of 541 requests.
- **Read closely:**
  - piano timing (L1 to L547);
  - story layer and live readback (L1494 to L1720);
  - the browser harvest (L1750 to L2700);
  - night build orchestration and commits (L2760 to L4030);
  - the bus and morning (L4031 to L4470);
  - safety stops (L4770 to L4830, L5280 to L5335);
  - post-compaction and final commits (L5108 to L5662).
- **Spot-read for verification:**
  - four background task outputs (`bagvf1ar8`, `bl2o4doi3`, `bwf112ftb`, `byqd8jslp`), only for which message woke
    a turn;
  - `agent_cli.py` mailbox flags (lines 9547 to 9584);
  - `arsenal/shaders/licence_line.py` argparse;
  - the `--json` flags in `arsenal/media`;
  - the house `web_fetch` tool description.
- **Skipped, and why:**
  - Workflow subagent transcripts (`subagents\`, 380 files, 396 MB) and the `tool-results\` spill folder (107 files):
    other lanes own them.
  - The thinking text was only sampled where it explained a decision (L1325, L2261, L3976, L4817, L5330).
  - Lines after L5662: the retro workflow itself.
  - The "58 unread" backlog contents were not reviewed.
- **Kept out on purpose:**
  - No corpus shader code, shader ids or playlist id.
  - No browser-session contents.
  - No personal or work details from Daniel's messages.
  - No reverse-engineering technique detail. The A10 stops are named by topic only.
  - Paths under the user profile are written as `%USERPROFILE%` or `%TEMP%`.
- **Unknown:**
  - What exactly triggered each safety stop.
  - Whether the first fetch at L2695 lost content.
  - Whether the recall injections helped anywhere else.
  - The exact pre-commit hook duration per commit (only the 120 s timeout at L3729 is evidenced).
