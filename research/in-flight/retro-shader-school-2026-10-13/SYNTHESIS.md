# What the shader-school night taught us

Status: in-flight research · Type: synthesis of six retro lanes · Date: 2026-10-13 · Author: claude (the main seat)

Daniel asked, 2026-10-13: "What did we learn from all of this? Would you mind fanning out agents to capture every friction point, hand rolled script, re derivation and any other thing that would've made the process better, i know we have a rich wealth of information waiting to be surfaced"

This page merges the six lane reports in this folder. Each lane read a different part of the night:

- `main-transcript.md`: the main seat's own session, line by line.
- `subagents-early.md`: the first 89 workflow agents (02:14Z to 09:23Z).
- `subagents-late.md`: the last 90 workflow agents (09:23Z to 18:00Z) and the 23 workflow scripts.
- `scratchpad-scripts.md`: all 577 scripts left in the scratch folder.
- `git-hooks-bus.md`: git history, the git hooks, the wishlist and the bus.
- `rederivations-vs-store.md`: every discovery of the night, checked against what the house already knew.

**How to check the evidence.**

- "main L1234" is line 1234 of the main session transcript, `%USERPROFILE%\.claude\projects\E--\9d62784c-bd34-488c-a370-94b7d333fbb9.jsonl`.
- Agent paths such as `wf_4321c88e-893/agent-a2a4415e... L360` are under that session's `subagents\workflows\` folder.
- "Source:" lines name the lane report and its item number, so you can open the full evidence.
- Times are UTC (marked Z) unless marked EDT. Your clock is UTC minus 4.
- Commits are short shas. Wishes are W-numbers in `docs/WISHLIST.md`.

---

## 1. What we learned

The night's work held up. The cost did not come from bad judgement. It came from a dozen small jobs that no tool did, so many agents worked each one out again by hand: about 580 saved scripts and about 2,100 inline snippets.

The biggest source of breakage was typing Python through the shell. The shell layer eats backslashes and quotes. That broke commands at least 29 times and silently corrupted two files, although the house had written the problem down twice since July.

Most of what the house already knew did not reach the moment it was needed. Seven of the twelve re-learned lessons trace to one mechanism. The recall hook shows each lesson once per session, and all 179 agents shared the main seat's session. It is like one cache line shared by 180 cores and marked as used the first time any core touches it: each lesson was spent early, on an unrelated command, and then hidden from everyone.

The cures for the two most common frictions were already open wishes: W230 for the console codec and W234 for shell patches. All three wishes filed today restate open wishes from July.

The single costliest incident was in git:

1. A refused commit left 15 files staged in the shared index.
2. Heimdall's ordinary commit, two minutes later, carried them under his own message.
3. HEAD then held tests without their modules for 2 hours 8 minutes.
4. Heimdall's bus message saying so went unread for 2 hours 7 minutes of that window.

The bus has the same shape of problem:

- The wake ritual swallows mail into files nobody opens. 11 of 15 were never opened, and 4 of Heimdall's messages were never seen.
- A frozen read cursor reported 58 phantom unread messages about 80 times.
- A peer's chat or note cannot wake the seat, so you ended up routing mail yourself.

Parallel agents shared one scratch folder, one working tree and one identity. So they overwrote each other's scripts, tripped over each other's half-finished tests, and locked themselves out of their own edits.

Some things worked and should be kept exactly as they are: tests proven red before the fix, checks in a clean worktree (which caught three real defects), adversarial review rounds, the `find` verb, and never bypassing a hook or a human check.

---

## 2. The top ten fixes

I ranked these by the cost each would remove, meaning cost per hit times number of hits. The units differ (turns, minutes, risk to the repo, your time), so the order is my judgement. The counts are included so you can rank them differently.

### 1. Stop typing Python through the shell (hook)

- **Count:**
  - about 2,100 inline snippets (560 quoted heredocs and 1,533 `py -c`) in 161 agents;
  - 29 quoting failures by the scratchpad lane's count. Lane by lane: the main seat had 7 visible failures and 1 silent one, the early half 9 in 8 agents, and the later half 20;
  - 156 shell commands in 33 agents edited repo files with a Python read-replace-write.
- **Silent damage:**
  - A heredoc patch wrote a real newline into a test file. The write reported success, and only pytest caught it (main L1286 to L1319).
  - A dissector patch wrote control bytes into three regex lines, which silently stopped matching (`wf_4321c88e-893/agent-a2a4415ebcc2b1877` L324 to L351).
- **Known before:**
  - The lessons `bash_heredocs_corrupt_regex_backslash_b_to_backspace` (2026-09-28, which also records 2026-07-28) and `process_match_by_argv_not_substring_and_no_backslashes` (2026-10-09).
  - Open wish W234 (2026-10-02).
  - The recall lesson was shown at 06:17 (main L2590), and the failure recurred at 14:43 (main L4645).
- **Extra cost:** Python patches skip the advisory-lock check, which runs only for Edit and Write (`scripts/hooks/claude_pretooluse.py` lines 265-268).
- **Smallest fix:**
  - A PreToolUse hook on Bash and PowerShell. When a command holds a heredoc or `py -c` that contains a backslash, or runs past a few lines, it refuses and says to write a `.py` file with Write and then run it.
  - One brief line: repo edits go through the Edit tool, which keeps LF line endings and fails safely if the file changed underneath it.
- **Source:** main-transcript.md A2; subagents-early.md 3, 23; subagents-late.md 8, 15; scratchpad-scripts.md 5; rederivations-vs-store.md R1.

### 2. A house commit verb, and a hook that unstages on refusal (verb plus hook)

- **Count:**
  - The commit procedure was hand-built 5 times in one day: `commit_stage2a.sh`, `commit_fixes.sh`, `commit_batchb.sh`, `commit_paths.sh` and an inline temporary index (main L3096).
  - The clean-worktree check was hand-built 10 times (main L3102, L3429, L3928, L4586, L4875, L5508, L5641, L5762, L5819, L5887).
  - The main seat made 20 commit-bearing tool calls. One batch hit the 120-second timeout (main L3729).
- **The incident:**
  - `commit_batchb.sh` ran `git add` and then a commit, which the hook refused (main L4896).
  - The 15 staged files were carried by Heimdall's `1d96275d` at 12:00:24 EDT. They are about 5,800 of its roughly 6,040 changed lines.
  - The GREEN half, `bdd5c8fc`, landed at 14:08:36 EDT. I re-read both commit dates during this synthesis: the gap is 2 h 08 min, with 3 more commits stacked in between.
  - The script's output went through `grep` and `tail`, so it reported exit code 0 (main L4882).
  - I told you batch B was landing 25 seconds before I read the refusal (main L4879). I corrected it at main L4939.
- **Related cost in the same hook:**
  - `docs/PHYSICS.md` changed in all 45 commits that day. In 36 of them the only change was its own Derived-at stamp line.
  - Each commit pays about 20 to 22 seconds of hook time, about 16 minutes over the day.
  - The hook stages regenerated docs into whichever index is active, which left the real index stale 4 times.
- **Known before:** W110 and W111 (2026-07-31; W111 is still open: unstage on guard refusal).
- **Smallest fix:**
  - `py agent_cli.py commit`:
    - builds the commit in a temporary index from HEAD;
    - on refusal, exits non-zero with a one-line reason and leaves nothing staged;
    - resyncs the real index for every committed path;
    - can run a test command in a throwaway worktree.
  - In the pre-commit hook, a refused commit unstages what it staged and names those paths (W111).
- **Source:** main-transcript.md A9, B5; git-hooks-bus.md 1, 8, 9, 10, 12, 24; scratchpad-scripts.md 1; rederivations-vs-store.md R2, R3.

### 3. Let bus mail reach the turn (verb plus hook)

- **Count:**
  - The wake watcher was armed 16 times (main L562 to L5560). The Stop hook blocked 2 turns over it (L554, L4425).
  - 11 of 15 watcher output files were never opened.
  - Four of Heimdall's messages were consumed and never seen (13:38Z, 13:49Z, and two at 14:09Z). One was a coordination question with three options, and it went unanswered.
  - His 16:01Z note about the sweep was read at 18:08Z.
  - Eight directed messages from Heimdall could not wake the seat by design: chat and note are not wake-worthy, and a nudge ranks below the floor (`scripts/bifrost_wake.py` 57-58, `core/comm/wake_tiers.py` 57, 104-108).
  - A review request sat 47 minutes until you asked "Hey, did you get heimdalls recent message?"
  - The unread banner showed 58 to 60 messages 72 to 80 times (lanes counted different windows). The legacy cursor has been frozen since 2026-09-25.
  - Two message hunts took 8 and 7 tool calls. One ended in a hand-written raw Redis read (main L4290 to L4351, L5560 to L5589).
  - After a safety stop at 17:19Z the seat was unarmed for about 39 minutes. Your question "Do we have preset color templates?" waited 49 minutes.
  - At 13:33Z I told you on the bus that your messages and Heimdall's would wake the seat. That was only partly true.
- **Smallest fix:**
  - When the seat re-arms, it returns the bodies of the mail it consumed into the turn, and moves the cursor only on an explicit ack.
  - The unread count uses the lane cursor; `_pending_peek` already has that rule.
  - Re-arming happens on any turn end, including refusals.
  - The wake line shows your messages in full.
- **Source:** main-transcript.md A5, A6, A7, A10; git-hooks-bus.md 2 to 7, 19.

### 4. Set UTF-8 output and the repo import path once (process: a settings change, your call)

- **Count:**
  - The Windows console codec (cp1252) crashed Python output in about 18 agents. The whole-session counts give 19 results; the lane sums give 21.
  - The encoding prefix was typed by hand about 767 times: 34 in the main seat, 127 in the early half and 606 in the later half.
  - Scripts outside the repo failed to import it 5 to 7 times. Agents carried `sys.path` inserts or `PYTHONPATH` by hand about 280 times.
- **Cause:** the `env` block in `%USERPROFILE%\.claude\settings.json` (lines 2-5) sets `PYTHONPATH` to `scripts/quiet` only and sets no encoding.
- **Known before:** open wish W230 (2026-10-02), and 15 lessons since 2026-07-02.
- **Smallest fix:** add `PYTHONIOENCODING=utf-8` (or `PYTHONUTF8=1`), and append `E:/AI-Setup` to that `PYTHONPATH`.
- **Source:** main-transcript.md A3; subagents-early.md 4, 25; subagents-late.md 1, 2; scratchpad-scripts.md 5; rederivations-vs-store.md R9.

### 5. Key recall and injected context per agent (hook)

- **Count:**
  - One list of lessons already shown served 179 agents plus the main seat.
  - 1,455 lesson injections carried 1,454 distinct lessons, so each lesson reached one agent, once.
  - By evening, 1,464 of the store's 1,636 lessons were marked seen for the session.
  - The injection rate fell from 49.9 per 100 tool calls at 03:00Z to 0.2 at 16:00Z.
  - In 9 of 9 traced cases, a prior lesson was spent on an unrelated command.
  - 60% of action injections were attached to read-only commands.
  - A 2-hour self-echo rule hides a fresh lesson from its author. Every lane writes as `claude`, so siblings never saw each other's new lessons.
- **The opposite symptom at the same time:**
  - One verb hint repeated 51 times inside one agent (subagents-late.md 22).
  - The `discord` hint fired 92 times in the early half (subagents-early.md 17).
- **Context volume:**
  - The full root `AGENTS.md` was attached in 165 of 179 subagents. Counting the `arsenal/web` one too, the lanes measure about 2.4 million characters.
  - Recall-at-action fired about 1,418 times, about 1.44 million characters.
  - One agent obeyed `AGENTS.md`, tried to boot, and was refused (`wf_5d01ae05-3d2/agent-a8aabe0ed4851b0a3.jsonl:61`).
- **Smallest fix:**
  - Key the seen list on session plus agent transcript. First check that the hook payload names the subagent; that is unknown.
  - Do not mark lessons seen on read-only commands.
  - Hold verb hints to a relevance floor.
  - Give workflow subagents a short card instead of the full `AGENTS.md`, or put a two-line preface at its top: a workflow subagent follows its brief.
- **Source:** rederivations-vs-store.md section 1; subagents-early.md 17; subagents-late.md 21, 22; main-transcript.md A15.

### 6. One shared brief template for fan-outs, with a private scratch folder per lane (brief)

- **Count:**
  - **Hand-copied rules.** 21 rule blocks were copied by hand across 23 workflow scripts. The later-half lane lists 13 rules that agents paid for and no script carries. The encoding rule reached only 6 of 89 early briefs.
  - **Scratch collisions.**
    - 19 scratch filenames were written by more than one agent.
    - Four lanes wrote `px.py` within 31 seconds, and one run failed.
    - `mutate.py` was written by three agents, and two harnesses were lost.
    - This retro's own lanes collided twice. One of those overwrote the session's own `scan.py`, which is now gone.
  - **Locks.** Two agents locked files under invented ids, then had 10 of their own edits refused. Every subagent runs as `claude`, so a lock cannot tell siblings apart.
  - **Known-red tests.** Tests that are red by design confused 20 agents (29 results).
  - **Shell traps.**
    - PowerShell flagged 57 results that mostly were not failures.
    - Shell-redirected JSON gained a byte-order mark and crashed `json.load` 10 times.
    - 35 failures hid behind exit 0, 17 of them behind a pipe.
- **Smallest fix:**
  - One rules file that every workflow script includes, with switches for repo, GPU, corpus, read-only and review-JSON.
  - It tells each agent:
    - its scratch folder (`<scratch>/<workflow>/<label>/`);
    - scripts go to files;
    - run `py`, `node`, `gh` and `pytest` through Bash;
    - use `set -o pipefail`;
    - lock as `claude`;
    - which tests are known red at launch;
    - use forward slashes in structured output;
    - use `-m slow`;
    - never sleep.
  - Optionally, the harness sets `AKASHIC_AGENT_ID=claude-<label>`.
- **Source:** subagents-late.md 3, 6, 7, 9, 11, 14, 26 and its section on the briefs; subagents-early.md 14, 27, W2; scratchpad-scripts.md 7; main-transcript.md E1.

### 7. Workflow agents write reports to files and return only a verdict and a path (brief)

- **Count:**
  - **Main seat.** It read workflow results with 25 hand-written parsers for 20 workflows; two failed, on a `KeyError` and on the codec.
  - **Fixers.**
    - 38 of the 90 later briefs pointed fixers at a large task-output JSON, which they touched 74 times.
    - 10 near-identical parse commands ran within 9 seconds.
    - The early half had 18 more such commands.
  - **Context growth.**
    - The main seat's context grew from 68k to 598k tokens, mainly because it read about 220 KB of workflow output itself (main L748).
    - The first compaction landed two minutes after you gave the night's task (main L1889).
    - The second compaction made me work out the licence-line schema a second time (main L5108 onward).
- **Smallest fix:**
  - Each agent's report goes to a named file, and the workflow returns `{verdict, path}`.
  - A fixer receives its own review section as text in its prompt.
- **Source:** main-transcript.md A1, A20, C1; subagents-early.md 10; subagents-late.md 10.

### 8. Give the licence line the flags every agent built by hand (verb)

- **Count:**
  - 126 full-repo scans, median 35 seconds, about 56 minutes in all. A one-slice scan takes a median of 4 seconds.
  - 14 or more filter scripts that cut the report down to one slice's files. In the later half alone: 103 inline filter commands and 17 filter scripts.
  - 9 crashes on the `breaches` field, which holds a count, not a list.
  - The main seat worked out the JSON shape twice: at 11:24Z, and again after compaction with five rescans.
  - The source file was read by 15 agents just to learn its output.
  - The tracked baseline was built and pruned by scratch scripts and 3 hand edits, and one of those edits broke its pin (main L3678 to L3709).
  - Exit code 1 on a breach made 4 working calls look like errors.
- **Smallest fix:**
  - First: `--paths` (scan only these files) and `--out FILE`, and document `breaches` and `hits` in `--help`.
  - Then: `--write-baseline`, `--triage`, and exit 0 for report modes.
- **Source:** main-transcript.md A4, C2, C3; subagents-late.md 5, 6; scratchpad-scripts.md 2, 3.

### 9. A mutation verb that never touches tracked files (verb)

- **Count:**
  - 46 mutation scripts and runners (about 35 distinct harnesses), plus 67 generated mutant copies.
  - Five harnesses wrote mutants straight into tracked files while other seats were testing and committing: `stage.js` four times and `modlib.js` once.
  - The later-half lane estimates 10 to 20 minutes of authoring per reviewer.
- **Known before:**
  - The lesson `a_mutation_that_never_applied_reports_as_a_surviving_one`.
  - `docs/method-baseline-2026-07.md` line 305.
- **Smallest fix:** `py agent_cli.py mutate --file F --swap OLD NEW --test "<cmd>"`. It swaps in memory or in a temporary overlay, checks that each swap applied exactly once, and prints caught or missed.
- **Source:** scratchpad-scripts.md 4; subagents-late.md 17; subagents-early.md 22.

### 10. Maps for the corpus and the house's JSON (doc, plus two small verb fixes)

- **Count:**
  - 38 of 89 early agents explored the corpus folder by hand (249 commands).
  - 104 probes of house JSON in 19 agents, 5 of them wrong guesses.
  - `atlas.json` was opened directly 158 times by 36 agents.
  - `py -m arsenal shader --help` printed the wrong usage 29 times for 18 agents (`arsenal/__main__.py` lines 165-167).
  - `modules.py`, `licence_line.py` and `cards.py` were read by 15, 15 and 12 agents to learn their contracts.
  - `piano.js` was read 83 times by 15 agents.
- **Smallest fix:**
  - `corpus/README.md` and `arsenal/shaders/SCHEMAS.md`, with one section per api id.
  - `shader --help` lists the shader verbs, with a pin.
  - `atlas --file` and `atlas --name`.
  - A function index at the top of the big files.
- **Source:** subagents-early.md 1, 11, 20; subagents-late.md 4, 18, 19, 20.

### Just below the line

- **Pixel probes and contact sheets.** 22 scripts by the scratchpad lane's count; 29 scripts plus 94 inline builds in the later half by its count. `py -m arsenal.media sheet` existed and was called 0 times.
- **CRLF on new file types, for the third time.**
  - A clean worktree failed 9 pins (main L5758; fixed in `86280221`).
  - The 146 warnings that predicted it were filtered out with `grep -v CRLF`.
  - Three house writers still emit CRLF.
- **The wish and learn doors check ids, not content.** 3 of 3 new wishes restate open ones. Two twin lessons were minted. The `repeat` verb was used 0 times.
- **PDF reading.** 13 failed reads and 78 extraction commands in 13 agents (there is no poppler on this host).
- **Headless screenshot drivers.** 7 drivers (1,201 lines) left 1.3 GB of browser profiles in temp.
- **Python against JavaScript twin checks.** Built at least 6 times (32 scripts).
- **Generators for tracked files live only in scratch.** These are the licence baseline and the cadence fixtures; the cadence generator was already re-derived three times.

### Decisions only you can make

- Add the two environment lines (item 4, W230).
- Retire the frozen legacy read cursor. This marks September's mail as read.
- Push the 91 local commits that have waited since 2026-10-07 (I re-counted them), or take a dated off-machine snapshot. The machine is past 100 hours of uptime. Any repair of `1d96275d`'s history is easier before a push.
- Overnight downloads of public papers and corpus media. Agents split 10 to 4 on whether that was allowed (subagents-early.md 7).
- Install a CPU GLSL validator and poppler (subagents-early.md 26, 5).
- Two open questions on the bus:
  - Start the UI on port 8787? Asked at 16:42Z.
  - Confirm the residents rename ruling that Heimdall relayed? Asked at 18:11Z.
- Correct the wrong numbers in W265, W263 and today's lesson (see section 6).
- The 38 textures still owed: `harvest-js --media` is your morning step (main-transcript.md A11).

---

## 3. Verbs to build

On 2026-10-13 at 06:06Z you wrote: "remember to make verbs to make these interactions and actions easier". This is the merged list. Each entry gives the proposed name and arguments, what it replaces, and where lanes named it differently.

### Git and commits

- **`py agent_cli.py commit <agent> --message-file F --paths P... [--hunks PATCH] [--verify "<cmd>"] [--dry-run]`**
  - Called `commit-only` in git-hooks-bus.md and rederivations-vs-store.md.
  - Replaces `commit_stage2a.sh`, `commit_fixes.sh`, `commit_batchb.sh`, `commit_paths.sh`, `split_hunks.py`, the inline temporary index at main L3096, nine `msg_*.txt` files, and 10 hand-built worktree checks.
  - Must:
    - add the named untracked paths;
    - leave nothing staged on refusal;
    - exit non-zero with a one-line reason;
    - resync the real index, hook-regenerated docs included;
    - never filter its own output.
- **`py agent_cli.py sandbox [--at REV] [--with PATH...] -- <command>`.** Replaces 17 or more hand-made mirror trees, about 9 copy commands and 10 worktree add/remove pairs (scratchpad-scripts.md 11).
- **`py agent_cli.py page-ack <key>`**, named in the HARD WEDGE page text. Replaces the `py -c` import of the pager's internals (main L4019).

### Licence line (`py -m arsenal shader licence-line`)

- **`--paths F... | --changed [--since REV]`, `--no-preview`, `--out FILE`, `--breaches`, `--check`.**
  - Report modes exit 0; only `--check` exits non-zero.
  - Replaces the 20 slice-filter scripts in the scratchpad appendix (`myscan.py`, `myll.py`, `ll_mine.py`, three `licence_mine.py`, `lic_filter.py`, `rr_ll_filter.py`, `triage/check_files.py` and others), 103 inline filter commands and 70 `--json >` redirects.
- **`--write-baseline [--at REV] [--files F...]` and `--triage OUT.md`.**
  - The main lane called the first one `--rebaseline --at <sha>`.
  - Replaces `ll_make_baseline.py`, `ll_rebase.py`, `ll_triage.py` and three hand edits of the baseline.

### Shader corpus and library (`py -m arsenal shader ...`)

- **`shader --help` passes through to the shader verbs**, with a pin. This is a fix, not a new verb.
- **`corpus ls|count|grep`**, printing ids and counts and never code. Replaces the hand exploration of 38 agents.
- **`census --technique T | --tag T [--sample N]`.** Replaces 137 inline technique censuses in 34 agents, plus `list_tag.py`, `sample_tag.py`, `noise_recall.py`, `scan2.py`, `scan_color.py` and `order_census.py`.
- **`explain --all [--set NAME] --snapshot OUT.json` and `explain --diff A.json B.json`.** Replaces 17 or more corpus-wide audit scripts by 7 agents (`explain_corpus_counts.py`, the `rr2_*` checks, `rr3_snapshot.py` with `rr3_diff.py`, `rr4_audit.py`).
- **`atlas --file <glsl> | --name <fn> | --gaps`, `--json --out FILE`.** Replaces 158 direct loads of `atlas.json`, `atlas_gap.py` (written by two agents 23 minutes apart) and about 18 small consistency scripts.
- **`card NAME [NAME...] --render [--family F] [--variant LABEL:"u_a=1;u_b=2"]... [--sheet OUT.png]` and `render --set NAME [--gap S]`.** Replaces `rendercards.py`, `render_light_cards.py`, `aurora-fix/render.py`, `shelf_renders.py`, the variant writers, and much of about 60 look-tuning scripts.
- **A pixel inspector:**
  - `py -m arsenal.media px <png> stats|grid|sample X,Y...|crop X0,Y0,X1,Y1 [--scale N] [--out F]`;
  - `px diff A B --heat F`;
  - `media sheet` takes `label=path` items.
  - subagents-late.md proposes the same thing as `py -m arsenal shader look` plus `card --sheet`.
  - Replaces `px.py` (4 writers), the `corr1_*.py` probes, `zoom.py`, `montage.py`, `sheet.py` (3 writers), `contact_light.py` and `loved_sheet.py`.

### Testing

- **`py agent_cli.py mutate --file F (--swap OLD NEW ... | --mutants M.json) --test "<cmd>" [--import-hook MODULE] [--expect red]`.**
  - subagents-early.md calls it `mutate <file> --at <pattern>`.
  - Replaces 46 scripts and runners.
- **`py agent_cli.py twin-diff --py MOD:FN --js FILE.mjs:FN (--cases C.json | --fuzz N --seed S)`**, with NaN, Infinity and minus-zero encoding built in.
  - Replaces `s4/diff.py` with `run.mjs` (copied twice), the `s1review/twin.*` and `s1rr2/twin2.*` pairs, `fuzz_gen.py` with `fuzz_check.mjs`, `rev_faith/gen.py` with `check.mjs`, and `lowfix/tiny_diff.py` with `tiny_run.mjs`.
- **An LF check:**
  - `py agent_cli.py eol <paths>`, or a pytest over changed tracked files;
  - plus a test that every tracked text extension has an eol rule.
  - Replaces 48 hand CR checks in 23 agents, one of them prescribed wrongly in a brief, and `eol.py`.

### Browser receipts

- **`arsenal/lanes/cdp.mjs`**, a shared library: launch with a throwaway profile that is always removed, connect, screenshot, capture the console, watchdog and GPU lock.
- **`node arsenal/lanes/page_receipt.mjs --url U --steps S.json --out DIR [--port N] [--keep-profile]`**, built on that library.
- **`py -m arsenal piano shot --key K --chords ... --framing ...`** on top, as subagents-early.md proposes.
- Together they replace 7 drivers (`lean_shots.mjs` twice, `rev_ab_shots.mjs`, `v6_shots.mjs`, `w6_shots.mjs`, `x7_shots.mjs`, `vrun.mjs`). `arsenal/lanes/chrome_verify.mjs` already cleans up its profile (line 271), but it cannot be imported.

### Bus and memory

- **`py agent_cli.py mailbox <agent> --open-latest --from <sender> [--full]`.**
  - git-hooks-bus.md calls it `bifrost latest --from <seat>`.
  - Replaces the three-step pipeline (about 13 calls) and the raw Redis read at main L5588.
- **A standby that peeks.** Re-arming returns the consumed message bodies and advances only on ack.
- **`bifrost_fetch`** creates missing folders and never overwrites an existing spill (main L4393; L2695 then L2707).
- **`events --kind/--since/--until`** either filters or refuses loudly. Today these flags are silently ignored without `--search` (`agent_cli.py` 5630-5633).
- **`py agent_cli.py learn <agent> --from-json LESSONS.json`** (or `--tried-file` and its siblings). Replaces `file_lessons.py` and `file_lesson_index.py`.
- **`wish` changes:**
  - accept text after the options;
  - add a near-duplicate pass over open wishes that offers to add a recurrence receipt;
  - make `learn`'s near-duplicate warning offer `repeat`.
- **`lock --why`:** add it, or drop the habit. 3 agents used it.
- **`py agent_cli.py bus peek STREAM --last N [--by-sender]` and `stats --lessons-by-author`.** Low priority. Replaces 15 teardown probes and 45 direct Redis calls.

### Workflows and transcripts

- **`py agent_cli.py wf-result <task-id|file> [<json-path>] [--verdicts] [--split DIR]`.** Optional if fix 7 lands.
- **Your own words, searched.**
  - Check first whether `py agent_cli.py eye find --who operator` (`agent_cli.py` 10103-10128) covers bus-relayed text. If it does not, add `--origin typed|queued|bus --dump jsonl`.
  - The lanes proposed it under three names:
    - `said "<regex>" [--since]` (subagents-early.md);
    - `eye find ... --origin` (scratchpad-scripts.md);
    - `transcript {grep,view,count}`, which streams, removes duplicates, converts to house time and prints UTF-8 (git-hooks-bus.md).
  - Replaces 11 census scripts, a PowerShell pipeline of about 10 queries, and at least 9 scanners that this retro's own lanes wrote.
- **`readback <session> [--full]`**, which stamps how much was read (for example: read through 4:16, 37 of 112 windows). Replaces `readback.py`, `voicing_trend.py` and four inline analyses (main-transcript.md B4).

### Research and reading

- **`py agent_cli.py pdftext <pdf> [--pages a-b]`**, or install poppler (your call).
- **`py agent_cli.py web fetch URL --grep PATTERN [--window N]`.** Replaces `grab.py`, which ran 12 times outside the house door.
- **`py agent_cli.py outline <file>`**, or a generated outline beside the big files (`piano.js`, `toy-runtime.js`, `stage.js`).

### Small flag changes

- **`ingest --clipboard`** refuses a stale clipboard (main-transcript.md B3).
- **Optional `py agent_cli.py scratch <lane>`**, which creates and prints the lane's own folder.

**Where the lanes disagree on verbs.** The later-half lane proposes an `apply-edits <json>` verb that runs the lock check. The early and scratchpad lanes say no verb is needed: use the Edit tool, plus a doc line. The store lane points to open wish W234, a patch verb.

---

## 4. Knowledge that existed but did not reach us

Each entry gives what we learned again tonight, where the house already had it, why it missed, and what would have carried it.

### Re-learned

- **The shell eats backslashes.**
  - Tonight: 5 incidents in 4 agents, 3 of them after tonight's own lesson was filed.
  - Already known: lessons from 2026-07-28, 2026-09-28 and 2026-10-09, and W234.
  - Why it missed: the 09-28 lesson was shown once, at 06:17, on a read-only listing command (main L2591), and then hidden for the session.
  - What would have carried it: the hook in fix 1, and W234.
- **Committing part of a file with a temporary index.**
  - Tonight: worked out at 06:58 (main L3084 to L3108), filed at 14:43, and worked out again at 18:00.
  - Already known: inside the body of `exec_gate_widened_narrow_recovery_family_not_hallucinated_revive_verb` (2026-09-09), whose trigger is about something else.
  - Tonight's lesson was also scoped too narrowly to prevent the sweep (git-hooks-bus.md 24).
  - What would have carried it: the commit verb.
- **A refused commit leaves its files staged.**
  - Already known: W110 and W111 (2026-07-31), and the lessons `mirror_refusal_leaves_tree_staged` (07-31), `a_rename_has_no_safe_parked_state` (08-01) and `explicit_paths_do_not_scope_a_mirror_commit_the_shared_index_does` (08-26).
  - Why it missed: both key lessons were spent on listings at 05:23 and 06:47.
  - What would have carried it: W111 in the hook, and refusal text that names the staged paths.
- **The guardrail ratchet judges the working tree.**
  - Already known: W109 (2026-07-31), and lessons from 08-04 and 09-03. W264 does not cite W109.
  - What would have carried it: run the checkers on the index, and a near-duplicate pass in `wish`.
- **False HARD WEDGE pages on the live seat.**
  - Already known: W107 (2026-07-30, open), W108, W208, and two lessons from 07-28.
  - What would have carried it: a recurrence counter on wishes, and the page-ack verb.
- **CRLF on new file types, for the third time.**
  - Already known: the `.gitattributes` header (it bit on 09-16 and 09-17), and lessons from 09-17, 09-18 and 09-28.
  - What would have carried it: a test that every tracked text extension has an eol rule.
- **`gl.finish()` alone does not wait on SwiftShader; time with a one-pixel `readPixels`.**
  - Already known: in code at `arsenal/web/piano-lab-vfx.js:2422` (09-13), and the same night at `arsenal/web/shaderlab/render.js:271-279` (`ca6b330f`, 09:41Z). No lesson mentions it.
  - Tonight it took a review round and a fix (`be0fc4c8`).
  - What would have carried it: one line in the shader-craft skill's timing section, and one shared drain helper.
- **`tanh` overflows to NaN.**
  - Already known: study lanes noted it at 06:26 and 06:33; the runtime lane re-found it at 08:37.
  - What would have carried it: lanes file gotchas as lessons the moment they find them, which only helps once fix 5 lands.
- **The console codec.**
  - Already known: 15 lessons and W230.
  - Tonight: 18 agents found the workaround again.
  - What would have carried it: W230's settings change (fix 4).
- **Safety-classifier stops on the reverse-engineering research.**
  - Tonight: 8 stops (5 lanes, 3 main-seat turns), and 2 reports never written.
  - Already known: four lessons from 07-03, 07-19, 08-05 and 08-11. Three were shown to other lanes hours before; the fourth was shown after the stops.
  - What would have carried it: a brief section for security-adjacent fans, written before dispatch, and reports written in sections.
- **Private-data tests leaking through test output** (partly known).
  - Already known: the plane principle in `redaction_scoped_to_the_tracked_tree_leaves_the_store_reloading_it` (08-15).
  - What would have carried it: a pin helper that prints nothing private on a green run.
- **A quoting fix pinned only by argument shape** (partly known).
  - Already known: four lessons from 07-17 to 08-04.
  - The review caught it (main L4374 to L4394). It is unknown whether Heimdall's door pushes recall.
- **The phantom unread count.**
  - Already known: `core/comm/bifrost_api.py:332-338` records the same frozen-cursor defect on 2026-08-29, fixed only at arm time. `_pending_peek` already has the right rule.
  - What would have carried it: using that rule everywhere the count is shown (fix 3).
- **The doc stamp churn.**
  - Already known: `gen_physics_sheet.py --check` already strips the stamp, treating it as not staleness, but write mode does not. `check_unbound_names` already caches by hash.
  - What would have carried it: reuse both in the hook, pinned by a test.
- **Mutation discipline.**
  - Already known: a lesson and the method baseline (line 305).
  - Tonight it was rebuilt about 35 times.
  - What would have carried it: the mutate verb (fix 9).

### Tools that existed and went unused

- **`py -m arsenal.media sheet`** (since `3f55e119`, 10-12): 0 calls, and 22 scripts rebuilt it. It is not named in the shader-craft skill.
- **The house `web_fetch` door**, which has a raw mode and ranged reads.
  - The main seat used WebFetch, got a summary, then used curl (main L4106 to L4111).
  - Only 1 of 9 agents whose WebFetch failed tried the door. It fetched 9 of 11, including two PDFs WebFetch had refused.
  - `grab.py` used `urllib` 12 times.
- **`eye find --who operator`**: 11 scripts were built beside it.
- **`cards.render_cards(names)`** takes a list in Python (`cards.py:545`), but the CLI takes one name. So 3 wrappers were written.
- **`docs/pillar-analysis-method.md`** was found in 20 seconds, but only because you asked "I think we may have done this before" (main L4185). Plan-time recall surfaced two unrelated lessons.
- **The `repeat` verb**: 0 uses while 5 or more known lessons were re-violated.

### Knowledge that is wrong or stale

- **The memory note on safeguard stops** says routing to Opus escapes them. Tonight the seat was on Opus and was stopped three times, under a new marker, `model_refusal_no_fallback` (main L4795, L4804, L5300).
- **Task T272** (`state/coord/tasks.json`) said collision safety was not done at all. Heimdall found detection already built (lesson `resident_identity_collision_slice_recon`, 15:52Z).
- **The rule that Glob does not work on `E:\` paths.** This rule is in memory and in 13 of 23 workflow scripts. The later-half lane saw 5 of 5 Glob calls on `E:\AI-Setup` return files. I ran one Glob on this folder during this synthesis, and it returned all six lane reports. See the disagreement in section 6.
- **Today's records carry wrong magnitudes.**
  - W265 and today's lesson say the sweep came hours later and HEAD was red for six hours. The measured figures are about 2 minutes and 2 h 08 min.
  - W263 says the page lasted 40+ minutes. The page injections span about 13 minutes.

### Knowledge at risk of not reaching the next session

- **Generators of tracked files live only in scratch:** `ll_make_baseline.py`, `ll_rebase.py`, `gen_cadence_fixtures.py` (already rebuilt three times) and `set_texts.py`.
- **Review probes** were copied from round to round instead of becoming pins: 5 copy chains.
- **Two scripts read inputs from another session's scratch folder** (`content/piano-timing/isolated.py`, `jumps.py`).
- **How a subagent's environment is set** was found by searching the installed Claude Code package 13 times (`cli_grep.py`, `cli_re.py`), and was not written down.

---

## 5. What went well and should be kept

- **The `find` verb** found the saved bundle in one call (main L2330). You wrote: "You have no idea how proud I am of the fact that you used find and found it instantly" (L2369).
- **Tests proven red before the fix.**
  - Pins were seen to fail at HEAD and pass in the tree (main L475, L3928).
  - The later half had 69 deliberate red results in 19 agents.
  - Nearly every fix lane tried to see its pins fail first.
- **Clean-worktree checks caught three real defects:**
  - untracked test fixtures (L4873);
  - a doc pointing at files from a later commit (L5527);
  - CRLF on new file types (`86280221`).
- **Adversarial review rounds found real defects.**
  - 11 of 20 workflows were fix or re-review rounds.
  - They caught 89 real licence breaches in new files (L3455).
  - They caught a regression in Heimdall's quoting patch whose 6 pins were all green (L4394).
- **Discipline under blocks:**
  - no hook bypass;
  - the site's human check left to you;
  - no rewording around the classifier;
  - no workaround of the auto-mode block;
  - zero git-changing commands in 4,564 shell calls by the later 90 agents;
  - a relayed ruling held until you confirm it;
  - the UI start question sent to you.
- **The Stop hook's check on promise-shaped endings** turned waiting time into the GLSL module core (main L2861, then `db1b23d2` and `5e127983`).
- **A memory file written before compaction** carried the night across both compactions (main L2839, then the summary at L5112).
- **Briefs learned during the night.** The CR-check correction reached the next workflow in 18 minutes. A compile-time finding moved from one lane into the next lane's brief in 46 seconds.
- **Census before building.**
  - Seven census readers and Heimdall's blind half found three existing module systems, the dormant bench and the old ingest's licence risk.
  - Heimdall searched the store before building, twice.
- **A scratch prototype became a house verb in 33 minutes:** PE triage, `47ebdec0`.
- **House verbs were used heavily where they existed:** licence-line 126 runs, `card --render` 114, `explain` 30, `dissect` 19.
- **Privacy rules lived in the scripts themselves.** 86 scratch scripts declare themselves read-only, and 19 or more never print corpus text.
- **The bus spill-to-blob worked.** A 14,226-character report was fetched straight into `research/reviewed`.
- **Teamwork held.**
  - Heimdall cleared the ratchet 63 seconds after the ask.
  - The authorship ledger tells seats apart where git cannot.
- **Recovery was fast.**
  - Common errors took a median of 3 to 5 seconds to the next clean call.
  - Background runs were read 93 times, not waited on.
  - StructuredOutput was called 49 times in the early half with 0 retries.
- **Nine genuinely new discoveries were filed as lessons**, six by the claude lanes and three by Heimdall. Among them are SwiftShader's NaN rule for min and max, compile time dominating first-frame timing, and trig tolerance in twin probes.

---

## 6. Coverage and gaps

### What no lane read

- **The `tool-results` spill folder** (107 files). The main lane left it to others, and none read it.
- **Heimdall's own session.** There is no transcript on disk; only his bus side was read.
- **The Discord surface.**
- **Assistant thinking text.** It was sampled (main), keyword-counted (early half) or skipped (later half). Rules that were rediscovered only in thinking are undercounted.
- **The design of the 22 workflows as workflows**, for example the shape of the fix-then-re-review rounds. The scratchpad lane flagged this for a workflow lane, and there was none. The later-half lane read the scripts for their rule blocks only.
- **Tool results past 1,500 characters** in the later half.
- **The quality of the night's outputs.** The private corpus, study notes, renders and images were deliberately left unopened, for privacy. So this retro judges the process, not the results.
- **Test runs.** No lane ran tests. That HEAD was red is inferred from missing modules.
- **The eight external research reports**, which were not checked claim by claim.
- **The September bus backlog, and the Redis event log** beyond the inbox streams.
- **The browser profile folders**, which were measured by size only.

### Unknowns

- What caused the 06:43Z interrupt that killed 4 agents. Those agents had produced about 269,000 output tokens, and their reruns started cold (subagents-early.md 8).
- What exactly triggered each safety stop.
- Whether the hook payload names the subagent. Fix 5 needs this.
- Whether Heimdall's door pushes recall at action.
- Whether an in-place mutant ever reached a sibling's test or commit.
- Whether any agent read a sibling's scratch output as its own.
- Whether the first `bifrost_fetch` lost content.
- What became of Heimdall's 13:49Z question.
- Minutes lost per item, in most cases.

### Where the lanes disagree

- **How long HEAD sat red.**
  - git-hooks-bus.md measured 2 h 08 min, from `1d96275d` at 16:00:24Z to `bdd5c8fc` at 18:08:36Z, and about 2 minutes from the refusal to the sweep.
  - W265 and today's lesson say six hours, and that the sweep came hours later. rederivations-vs-store.md R3 and scratchpad-scripts.md 1 repeat those figures.
  - The six hours came from reading 12:00 EDT against 18:08 UTC. I re-read both commit dates, and they support 2 h 08 min.
- **Why HEAD was red.**
  - main-transcript.md B5 blames the main seat's own out-of-order commit: a doc naming files that came later, and tests that needed untracked fixtures.
  - git-hooks-bus.md blames the sweep: tests landed without their modules.
  - Both happened in the same window. No lane ran the tests at each commit.
- **How long the false HARD WEDGE page lasted.**
  - main-transcript.md A18, rederivations-vs-store.md R5 and W263 say 40+ minutes. That figure comes from the seat's own words at main L4000.
  - git-hooks-bus.md 14 counts 4 injections from 11:33:27Z to 11:44:35Z, and about 13 minutes from the page record to the ack.
  - Whether another surface carried it longer is unknown.
- **The Glob rule.**
  - subagents-early.md W1 counts it as a success: 0 Glob calls in 5,450, so the error class disappeared.
  - subagents-late.md 12 calls it stale: 5 of 5 calls worked.
  - Both can be true. The early half never tested Glob, and my one check also worked.
- **Recall repetition.**
  - rederivations-vs-store.md says each lesson reached one agent, once.
  - subagents-late.md and subagents-early.md show one hint repeating up to 51 and 92 times.
  - My reading, not verified: the first count covers lesson injections only, and the repeating hints are verb hints that follow a different rule. Either way, both point to anti-repeat being keyed wrongly.
- **Whether Python patches need a verb.** See the end of section 3.
- **Names for the same proposal:**
  - `commit` or `commit-only`;
  - `--rebaseline` or `--write-baseline`;
  - `shader look` or `media px`;
  - `said`, `eye find --origin` or `transcript`.
- **Counts that differ by method or window, not by fact:**
  - quoting failures: 29 for the whole session, against lane sums;
  - cp1252 crashes: 19 or 21;
  - licence-line full scans: 126 for the whole session, 108 in the later half;
  - unread banners: 72 or 80;
  - commits: 47 in the main lane's window, 45 on 10-13.

### What this synthesis checked itself

Read-only, during writing:

- the dates of `1d96275d`, `bdd5c8fc` and `86280221` (`git show -s`);
- 91 commits unpushed (`git rev-list --count origin/master..HEAD`);
- one Glob on this folder.

Every other count is the lanes' own.

### The retro hit its own findings

- The lanes shared one scratch folder and overwrote each other's scripts. This destroyed the session's own `scan.py`.
- Each lane built its own transcript scanners.
- The backslash bug struck retro lanes at least 6 times.

That is the strongest evidence that fixes 1 and 6 are needed.

No Shadertoy corpus code, private data or reverse-engineering technique appears on this page. The only words quoted are yours.
