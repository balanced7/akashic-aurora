# Retro, shader school 2026-10-13: the later half of the subagent transcripts

Status: draft · Type: report · Author: claude (Vandor), retro lane "subagents-late" · Written 2026-10-13

Daniel asked, verbatim: "What did we learn from all of this? Would you mind fanning out agents to capture every friction point, hand rolled script, re derivation and any other thing that would've made the process better, i know we have a rich wealth of information waiting to be surfaced".

This lane read the later half of the overnight subagent transcripts (90 agent transcripts and 12 workflow journals, 9:00 to 18:00 UTC on 2026-10-13) and the 23 workflow scripts.

## Summary

The agents did good work. The friction came from the shell, the harness and the house tools. Briefing gaps made it worse.

- **Six fixes would remove most of the repeated cost.** In order of payoff:
  1. Set `PYTHONIOENCODING` and a repo-inclusive `PYTHONPATH` once in the harness `env` block. Agents typed the encoding prefix 606 times, wrote `sys.path.insert` 153 times and set `PYTHONPATH` by hand another 40 times.
  2. Give `licence-line` a `--paths` filter and an `--out` option. It ran 108 times across 44 agents, and 103 hand-rolled scripts filtered its JSON down to "my files". It crashed 9 times on a field named `breaches`, which holds a count, not a list.
  3. Fix `py -m arsenal shader --help`. It prints the top-level usage instead of the shader verbs: 29 attempts by 18 agents.
  4. Give every agent its own scratch folder. 19 top-level scratch filenames were written by more than one agent. Four parallel agents overwrote one another's `px.py` within 31 seconds, and one run failed on it.
  5. Set a distinct agent id for each workflow subagent, or brief them to lock as `claude`. Two agents locked files under made-up ids and then blocked their own edits 10 times. Every subagent runs as `AKASHIC_AGENT_ID=claude`, so a lock cannot tell siblings apart. Python-driven edits skip the lock check entirely.
  6. Replace the 21 hand-copied RULES blocks with one house brief template. The template should also carry the rules every agent had to rediscover. Each rule should be ON or OFF per run: GPU, corpus, read-only, review-JSON. The one-line PowerShell fix belongs in this template.
- **Hand-rolled tools that want to be verbs:**
  - pixel probes and contact sheets: 29 scripts by 14 agents, plus 51 inline contact-sheet builds
  - mutation checks that prove a pin "bites": 8 scripts by 7 agents
  - per-file atlas lookups: `atlas.json` loaded directly 158 times by 36 agents. The brief itself said to "filter by file".
  - Python string-replace patchers instead of the Edit tool: 70 inline patch calls by 16 agents, plus 19 patch scripts
- **Context cost:**
  - The root AGENTS.md (13.4 KB) was injected into 84 of 90 agents. It mostly tells them to boot, learn and use the bus, which several briefs then forbid.
  - Recall-at-action injected 716 hints (395 thousand characters). One off-topic hint ("discord: watch the fleet from your phone") reached a licence-line fixer 51 times.
- **What went well:**
  - Zero git-mutating commands across 90 agents.
  - Recovery from the common errors took one turn: a median of 3 to 5 seconds to the next clean call.
  - Long runs went to the background properly (93 reads of task output files by 34 agents).
  - Pin-first discipline was visible: 69 red test results across 19 agents were deliberate reds.

## How to read the evidence

- `<SUB>` = `%USERPROFILE%\.claude\projects\E--\9d62784c-bd34-488c-a370-94b7d333fbb9\subagents\workflows`
- `<SCRATCH>` = `%USERPROFILE%\AppData\Local\Temp\claude\E--\9d62784c-bd34-488c-a370-94b7d333fbb9\scratchpad`
- `<WFS>` = `%USERPROFILE%\.claude\projects\E--AI-Setup\9d62784c-bd34-488c-a370-94b7d333fbb9\workflows\scripts`
- A citation like `wf_ab3d7b01-cf2/agent-a433896f451d7685a.jsonl:42 (10:26:38Z, batchA:hash-noise)` means: that transcript under `<SUB>`, JSONL line 42 (the tool-result record), the UTC timestamp in the record, and the agent's label.

Workflow ids in this half:

| id | workflow |
|---|---|
| wf_ae993e74-ec3 | shader-school-build-1-fix |
| wf_760d007f-ff6 | shader-school-foundation-fix |
| wf_32d773d9-bd6 | shader-school-build-1-fix-2 |
| wf_ab3d7b01-cf2 | shader-school-build-2a |
| wf_2857fa6c-f17 | shader-school-build-2b |
| wf_07b70c9d-63b | shader-school-build-2c-fix |
| wf_7108d788-f9d | shader-school-final-round |
| wf_5d01ae05-3d2 | reverse-engineering-arsenal |
| wf_cba2d412-d17 | reverse-engineering-arsenal-fix |
| wf_5776878b-3fd | reverse-engineering-arsenal-fix-2 |
| wf_e267ca8b-f7c | deconstruct-the-house |
| wf_9bd9ac72-509 | deconstruct-the-house-fix |

**Counting method.** A streaming Python pass collected every tool call and tool result, matched them by id and classified the errors by their text. The pass read one JSONL line at a time and never held a whole transcript in memory. Sums are over the 90 agents unless stated. "Calls" means tool calls. "Agents" means distinct transcripts.

**Tool mix:**

| tool | calls |
|---|---|
| Bash | 3327 |
| Read | 2224 |
| Edit | 1323 |
| PowerShell | 1237 |
| Grep | 743 |
| WebFetch | 571 |
| Write | 547 |
| WebSearch | 217 |
| StructuredOutput | 48 |
| Glob | 7 |

**Errors.** 284 tool results were flagged as errors. 69 of them were deliberate red tests. The rest are the items below.

---

## Items

### 1. Python output encoding is carried by hand on every call (friction)

- **Evidence:** `PYTHONIOENCODING` appears in 606 shell calls by 40 agents; `stdout.reconfigure` in 9 more. Four agents crashed first with `UnicodeEncodeError: 'charmap' codec can't encode character` (cp1252) before adding it:
  - `wf_ab3d7b01-cf2/agent-a433896f451d7685a.jsonl:42` (10:26:38Z, batchA:hash-noise)
  - `wf_2857fa6c-f17/agent-adbec0580df2a509c.jsonl:18` (11:42:20Z, fix:bench-shelf-atlas)
  - `wf_2857fa6c-f17/agent-af450251bab060b72.jsonl:40` (11:42:27Z, fix:noise-seed)
  - `wf_2857fa6c-f17/agent-afe594ed16e29edc1.jsonl:46` (11:42:40Z, batch-B:2d)

  Nine workflow scripts mention `PYTHONIOENCODING`, but only for printing the previous review JSON. `%USERPROFILE%\.claude\settings.json` lines 2-5 set an `env` block (`AKASHIC_AGENT_ID`, `PYTHONPATH`) with no encoding variable.
- **Occurrences:** 606 prefixed calls; 4 crashes; 2 of the crashes were on the brief's own review-JSON file.
- **Cost:** one wasted turn per crash. The rest is token noise: 606 copies of the prefix.
- **Fix:** add `"PYTHONIOENCODING": "utf-8"` (or `"PYTHONUTF8": "1"`) to the `env` block of the user settings. This is a config change, so it is Daniel's call.

### 2. Scratch scripts cannot import the repo (friction)

- **Evidence:** `ModuleNotFoundError: No module named 'arsenal'` in 5 agents:
  - `wf_ab3d7b01-cf2/agent-a298346af0992ea7c.jsonl:316` (10:16:22Z)
  - `wf_ab3d7b01-cf2/agent-a433896f451d7685a.jsonl:346`
  - `wf_2857fa6c-f17/agent-af450251bab060b72.jsonl:106`
  - `wf_2857fa6c-f17/agent-a1bad7126e661cc69.jsonl:217`
  - `wf_07b70c9d-63b/agent-a4fc73a8b22ec1fbd.jsonl:290`

  Each recovered within about 3 seconds by setting `PYTHONPATH=E:\AI-Setup`. The cause is visible in `%USERPROFILE%\.claude\settings.json` line 4: `"PYTHONPATH": "E:/AI-Setup/scripts/quiet"` replaces any default. A script run from the scratchpad therefore cannot see the repo root.
- **Occurrences:** 153 calls with `sys.path.insert(0, <repo>)` by 31 agents and 40 calls setting `PYTHONPATH` by 12 agents, all hand-carried. 5 crashes.
- **Cost:** 5 turns, plus the boilerplate in about 190 calls.
- **Fix:** append the repo root to that `PYTHONPATH` (`E:/AI-Setup/scripts/quiet;E:/AI-Setup`), or add a `.pth`. This is a config change, so it is Daniel's call.

### 3. PowerShell 5.1 turns native stderr into errors and truncated pipes into failures (friction)

- **Evidence:**
  - 406 of 1237 PowerShell calls used `2>&1` on `py`/`node`, although the PowerShell tool description warns against it.
  - 28 results were flagged `NativeCommandError`/`RemoteException` even when the program worked. Example: `py -m arsenal shader card ... 2>&1` at `wf_2857fa6c-f17/agent-a55597111b12d29fa.jsonl:367`.
  - 25 more came back as `Exit code 255` with good output, because `Select-Object -First N` closed a native pipe. Example: `wf_32d773d9-bd6/agent-a5159d6ae973e64b1.jsonl:436` printed `secs 48.69` and was still marked failed.
  - A `gh api` loop failed for every repository in PowerShell and worked unchanged in Bash (`wf_5d01ae05-3d2/agent-ad2827ea2c619f6c4.jsonl:208,217` then `:222`).
  - PowerShell parse errors hit `py -c` bodies containing `|`, `$c:` or `<<` four times. Example: `Missing file specification after redirection operator` at `wf_07b70c9d-63b/agent-afaf271492ab044ff.jsonl:309`.
- **Occurrences:** 57 flagged results, 41 of them outside item 4: 28 native-stderr wraps (16 of which are item 4's help calls), 25 exit-255 false failures and 4 parse errors. Plus 406 risky calls.
- **Cost:** about 41 extra turns beyond item 4. Agents also had to learn to ignore red results that were not red.
- **Fix:** one line in the house brief template: "run py, pytest, node and gh through Bash; use PowerShell only for cmdlets". Four early scripts (lean-light, story-foundation) already said "use Bash"; the shader and reverse-engineering scripts did not.

### 4. `py -m arsenal shader --help` does not show the shader verbs (friction)

- **Evidence:**
  - `arsenal/__main__.py` lines 165-167 register `shader` with `add_help=False` and `nargs=argparse.REMAINDER`, so `--help` is taken by the top-level parser.
  - The help text on line 166 itself advertises `py -m arsenal shader --help`.
  - 29 calls by 18 agents. Every one printed `usage: py -m arsenal [-h] {serve,plan,...,shader}` and 16 were flagged errors.
  - Five corroboration agents ran the identical command within 2 seconds (14:08:29 to 14:08:31Z, e.g. `wf_5d01ae05-3d2/agent-ac0c55292d8b0e386.jsonl:19`).
  - One found the workaround `cmd /c "py -m arsenal shader 2>&1"`, which lists the verbs through the "verb required" error (`wf_5d01ae05-3d2/agent-a3b9e2b147ee84d15.jsonl:35`, 14:08:46Z).
- **Occurrences:** 29 calls, 18 agents.
- **Cost:** 2 to 3 turns per agent on verb discovery.
- **Fix:** pass `-h`/`--help` through to `shaders/cli.main` when it follows `shader`, and pin it with a test that `shader --help` lists `licence-line`, `card` and `atlas`.

### 5. `licence-line` scans the whole repo, has no path filter, and its JSON misleads (hand-rolled script and friction)

- **Evidence:**
  - `arsenal/shaders/licence_line.py` lines 1029-1033: the verb takes only `--root`, `--corpus`, `--allow` and `--baseline`.
  - Lines 920-921: in the JSON, `breaches` is a count and the list lives in `hits`.
  - The repo-wide verdict was BREACH most of the run because of other agents' in-flight files: 14 "licence line: BREACH" results seen by 7 agents. One example is "BREACH (82 breaches, 516 baseline, 41 exempt, 0 failures)" at `wf_32d773d9-bd6/agent-a5159d6ae973e64b1.jsonl:549`.
  - So every agent ran the full scan and then filtered to its own files:
    - 108 licence-line runs by 44 agents, about 46 minutes of foreground wall time at a mean of 27 seconds, plus 6 runs in the background
    - 103 hand-written filter commands, and 17 filter scripts by 10 agents (`licence_mine.py`, `ll_mine.py`, `lic_filter.py`, `rr_ll_filter.py` ...)
    - one agent copied files into a mirror folder to scan a subset with `--root` (`wf_5d01ae05-3d2/agent-ad5abd8ab5e79dece.jsonl:394`)
  - Nine crashes with `TypeError: object of type 'int' has no len()` or `'int' object is not subscriptable` on `d['breaches']`. Two of them:
    - `wf_ab3d7b01-cf2/agent-ad060ac80802a2c3a.jsonl:544` (10:30:19Z)
    - `wf_7108d788-f9d/agent-aaddad9749ac61907.jsonl:469`
  - Agents learned the shape by reading the source: `licence_line.py` was read by 15 agents, 26 times.
- **Occurrences:** 108 runs; 103 filters; 9 crashes.
- **Cost:** about 46 minutes of scanning, at least 9 turns of crashes, and 17 throwaway scripts.
- **Fix:**
  - add `licence-line --paths <file ...>`, which scans only those files against the corpus
  - add `--out FILE`, which writes plain UTF-8 (see item 6)
  - rename or document the JSON fields in `--help`, so `breaches` reads as a count and `hits` as the list

### 6. JSON redirected by PowerShell gains a byte-order mark (friction)

- **Evidence:** `JSONDecodeError("Unexpected UTF-8 BOM ...")` in 9 agents. Four of them:
  - `wf_2857fa6c-f17/agent-a55597111b12d29fa.jsonl:571` (12:17:44Z)
  - `wf_2857fa6c-f17/agent-abadb13dbf0a25920.jsonl:101`
  - `wf_07b70c9d-63b/agent-a2643981321211915.jsonl:236`
  - `wf_7108d788-f9d/agent-a1c66d0ec08ab698d.jsonl:903` (fix:aurora-fringe)

  The cause in each case: `py -m arsenal shader licence-line --json > file` or `atlas --json > file` in PowerShell, whose `>` writes UTF-8 with a BOM. 41 calls by 12 agents then used `encoding='utf-8-sig'`. Only 2 workflow scripts mention it.
- **Occurrences:** 9 crashes.
- **Cost:** 9 turns, with a median of 5 seconds to the next clean call.
- **Fix:** the JSON verbs take `--out FILE`, so no shell redirect is needed. The brief template says "read shell-redirected JSON with utf-8-sig".

### 7. Advisory locks: subagents lock against themselves, and Python edits skip the check (friction)

- **Evidence:**
  - AGENTS.md says `py agent_cli.py lock <your_agent_id> <path>`. Agents picked sub-ids, but the Edit hook judges by `AKASHIC_AGENT_ID`, which `settings.json` line 3 sets to `claude` for every subagent. The hook source is `scripts/hooks/claude_pretooluse.py` lines 235-244.
  - **triage:licence** (`wf_32d773d9-bd6/agent-a16ea05775025b37b.jsonl`):
    - locked six files as `claude-licence-triage` at line 233
    - had 6 Edits refused at lines 238-248 (10:55:43 to 10:55:49Z): "is locked by claude-licence-triage"
    - unlocked at line 252
    - retried with `--why` and got "unrecognized arguments" at line 260
    - relocked as `claude` at line 263
  - **fix:lab-safety** (`wf_2857fa6c-f17/agent-a2688a47ecaa7e365.jsonl`):
    - hit the `--why` error at line 150
    - locked as `claude-labgpu` at line 157
    - had 4 Edits refused at lines 168-174
    - unlocked at line 178, relocked as `claude` at line 183
  - **groups:g2** also tried `lock claude-g2 ... --why` and got a usage error (`wf_2857fa6c-f17/agent-a3084eb892e308c06.jsonl:312`).
  - **Inference from the same hook code:** since every subagent is `claude`, a lock held by one subagent does not stop a sibling. The lock veto runs only for Edit, Write and NotebookEdit; shell tools get only the git veto (`claude_pretooluse.py` lines 265-268). So the 70 inline Python patch calls and 19 patch scripts in item 15 are never lock-checked.
- **Occurrences:** 10 refused Edits in 2 agents; 3 agents used the nonexistent `--why`.
- **Cost:** about 20 turns, and no real protection between parallel siblings.
- **Fix:** the workflow harness (or each brief) sets a distinct `AKASHIC_AGENT_ID` per subagent, for example `claude-<label>`. Until then, the brief says "lock as claude". Either add `--why` to `lock` or drop it from habit.

### 8. Bash heredocs and `py -c` quoting break Python (friction)

- **Evidence:**
  - Six agents hit `bash: -c: line N: unexpected EOF while looking for matching ''` on `py - <<'EOF'` bodies that contained Python quotes:
    - `wf_ab3d7b01-cf2/agent-a35553e7dce3d8a32.jsonl:452` (10:55:48Z)
    - `wf_ab3d7b01-cf2/agent-ae69fc909d12ce8f1.jsonl:593`
    - `wf_2857fa6c-f17/agent-af450251bab060b72.jsonl:225`
    - `wf_2857fa6c-f17/agent-a2688a47ecaa7e365.jsonl:626`
    - `wf_2857fa6c-f17/agent-abadb13dbf0a25920.jsonl:687`
    - `wf_760d007f-ff6/agent-a3c7ec96e975c959d.jsonl:98`

    Every recovery was the same: Write the script to a file, then run it. The median time to the next clean call was 31 seconds; the total was 189 seconds.
  - Another 14 failures in 11 agents were quoting or escaping: `replace('\','/')` unterminated, PowerShell eating `\"`, and Python 3.11's "f-string expression part cannot include a backslash". Examples:
    - `wf_2857fa6c-f17/agent-ad751e633f71c365f.jsonl:121`
    - `wf_07b70c9d-63b/agent-a4fc73a8b22ec1fbd.jsonl:264`
    - `wf_cba2d412-d17/agent-a3f10f95575874161.jsonl:204` (truncated `\UXXXXXXXX` escape from a Windows path in a docstring)
  - This retro lane hit the same thing 3 times while counting it.
- **Occurrences:** 20 failures; 1014 inline `py -c` calls by 88 agents, 332 `py - <<` heredocs by 41 agents and 137 `cat > file <<` by 31 agents.
- **Cost:** about 20 turns, with the heredoc ones costing about 30 seconds each.
- **Fix:** brief template line: "any script over five lines: Write it to your scratch folder with the Write tool, then run it; use raw strings or forward slashes for Windows paths".

### 9. The shared scratchpad is a flat namespace, and parallel agents overwrite each other (friction)

- **Evidence:**
  - 19 top-level filenames in `<SCRATCH>` were written by more than one agent (265 distinct names).
  - **px.py.** Four corroboration agents each wrote their own pixel tool as `px.py` between 14:09:28 and 14:09:59Z:
    - corroborate:1 at `wf_5d01ae05-3d2/agent-a4e374169c1917993.jsonl:45`
    - corroborate:5 at `.../agent-a3b9e2b147ee84d15.jsonl:57`
    - corroborate:2 at `.../agent-ac0c55292d8b0e386.jsonl:58`
    - corroborate:3 at `.../agent-ad068b3b0a2507c42.jsonl:53`

    corroborate:5 saw "updated" instead of "created" and moved the file away (line 62). corroborate:2's run then failed with "can't open file px.py" (line 65). It went on to copy whichever `px.py` was there, a different tool ("Pixel probes for corroboration"), at line 76, and finally wrote `corr2/px2.py`.
  - **ll.json** was written by 10 agents, **licence.json** by 8 and **atlas.json** by 7. batch-B:2d and batch-B:volume_atmos wrote `licence.json` 19 seconds apart (12:08:36 and 12:08:55Z) while one licence-line run takes about 27 to 48 seconds, so their runs overlapped on the same file.
  - The retro workflow's own lanes collided too: this lane's Write of `<SCRATCH>\retro\extract.py` at 14:12 reported "updated" (the file already existed, from a sibling lane).
- **Occurrences:** 19 shared names.
- **Cost:** 3 to 4 turns observed, plus an unknown risk of an agent reading a sibling's results as its own.
- **Fix:** the conductor gives every agent `<SCRATCH>\<workflow>\<label>\` in the brief (or the harness creates it), and the template says "write only there".

### 10. The previous review is passed as a path to a big JSON, so every fixer re-parses it (friction and rediscovery)

- **Evidence:** 38 of the 90 briefs point at a `tasks\w*.output` file and say "print with py and PYTHONIOENCODING=utf-8". Examples: `OUT2A` in `<WFS>\shader-school-build-2b-wf_2857fa6c-f17.js` line 12; `B2C` and `RE2` in `shader-school-final-round` lines 7-8. Agents touched those files 74 times. Ten near-identical opening commands parsed the same `wl3w52...output` between 14:06:30 and 14:06:39Z (fix:batchB+atlas, fix:aurora+uniforms and others). Two of the four cp1252 crashes in item 1 were on `wwv8t60gy.output`.
- **Occurrences:** 38 briefs; 74 calls.
- **Cost:** several orientation turns per fixer.
- **Fix:** the conductor passes each fixer its own review section as text in the prompt (the scripts already hold the earlier result), or writes one small file per fixer. Alternatively, a verb `py agent_cli.py wf-result <file> <json-path>` prints one section in UTF-8.

### 11. Tests that are red by design surprised many agents (rediscovery)

- **Evidence:**
  - `FAILED tests/test_glsl_index.py::test_the_committed_index_matches_the_library_files` appeared in 29 results across 20 agents, first at `wf_32d773d9-bd6/agent-a2421b8932467b135.jsonl:337` (10:11:21Z). It is red because `lib index --write` was reserved for Vandor at the end ("Do NOT run 'lib index --write'", `<WFS>\shader-school-build-2b-wf_2857fa6c-f17.js` line 19).
  - The atlas plan tests (`test_every_name_the_built_library_provides_is_planned` and `..._has_the_signature_the_atlas_shows`) were red for 10 agents, because the atlas was owned by another slice. First seen at `wf_2857fa6c-f17/agent-adbec0580df2a509c.jsonl:519`.
  - The repo-wide licence test was red for 7 agents.

  Each agent had to work out that these failures were not its own.
- **Occurrences:** 58 red results (29 + 14 + 15); the largest single group was 20 agents.
- **Cost:** a few turns per agent, plus the risk of "fixing" someone else's file.
- **Fix:** the brief carries a "known red at launch" list that the conductor generates with one quick run, or such tests skip under an in-flight marker until the final index step.

### 12. A stale house rule: "Glob does not work on E:\ paths" (rediscovery, inverted)

- **Evidence:** the clause is in 13 of 23 workflow scripts (for example `<WFS>\shader-school-build-2a-wf_ab3d7b01-cf2.js` line 21) and in memory. But all 5 Glob calls on `E:\AI-Setup` in this half returned files:
  - `wf_2857fa6c-f17/agent-a926e304d7b98ebfd.jsonl:66` returned the `tests\test_glsl_*.py` list
  - fix:aurora-fringe at `wf_7108d788-f9d/agent-a1c66d0ec08ab698d.jsonl` lines 63 and 892
  - rr:lab-view-only at `wf_7108d788-f9d/agent-a9d6f75591a247796.jsonl` lines 54 and 90

  These line numbers are the tool-call records.
- **Occurrences:** 13 scripts carry the rule; 5 of 5 observed calls contradicted it.
- **Cost:** small. Agents fell back to `ls` and Grep, which is fine. A stale rule still erodes trust in the rest of the block.
- **Fix:** re-verify Glob on E:\, then retire or narrow the rule in memory and in the template.

### 13. The Read tool cannot open PDFs on this host (friction)

- **Evidence:** "pdftoppm is not installed" in 6 research agents. Examples: `wf_5d01ae05-3d2/agent-ad2827ea2c619f6c4.jsonl:98` and `wf_5d01ae05-3d2/agent-a5ea776d6ba294a46.jsonl:119`. Each then probed for `pypdf`/`fitz` by hand, for example at `wf_5d01ae05-3d2/agent-ad5a673946ed70032.jsonl:120`.
- **Occurrences:** 6.
- **Cost:** 6 to 12 turns, with a median of 8 seconds to the next clean call.
- **Fix:** install poppler, or add a house `pdf-text` verb, and put one line in the research brief template.

### 14. StructuredOutput rejects long payloads with Windows paths (friction)

- **Evidence:** "StructuredOutput was called with input that could not be parsed as JSON":
  - `wf_5d01ae05-3d2/agent-a986eff7c61bb0d9d.jsonl:384` (13:18:23Z)
  - `wf_5d01ae05-3d2/agent-a8aabe0ed4851b0a3.jsonl:443` and `:447`

  The fix was to switch to forward slashes and shorten the payload, which took 26 to 69 seconds per retry. No workflow script mentions it.
- **Occurrences:** 3 failures in 2 agents.
- **Cost:** 3 turns, about 2.3 minutes.
- **Fix:** template line: "in structured output, write paths with forward slashes".

### 15. Python string-replace patchers stand in for the Edit tool (hand-rolled script)

- **Evidence:**
  - 70 shell calls by 16 agents edit repo files with an `assert old in s; s.replace(old, new)` patcher.
  - 19 patch or edit scripts by 9 agents. The reverse-engineering fixers wrote ten `edit_*.py` files for skill references (`edit_archero.py`, `edit_audio.py`, `edit_gfx.py` ...).
  - These patchers produced most of the heredoc failures in item 8, and one assertion failure: `wf_ab3d7b01-cf2/agent-ad060ac80802a2c3a.jsonl:665`, `patch_shelf.py`.
  - They also bypass the lock veto (item 7).
- **Occurrences:** 89.
- **Cost:** unknown turn count, plus a governance gap.
- **Fix:** prefer the Edit tool for repo files. If many-site edits are truly needed, use a house `apply-edits <json>` verb that runs the same lock check and reports each replacement.

### 16. Pixel probes and contact sheets are rebuilt by every agent (hand-rolled script)

- **Evidence:**
  - 29 image-probe scripts by 14 agents (`px.py` four times, `px2.py`, `corr1_px.py`, `measure.py`, `look_probe.py`, `fringe_corners.py`, `preview.py` ...).
  - 43 inline calls that open a PNG to read pixels, and 51 inline contact-sheet builds (`Image.new` plus `paste`).
  - The briefs ask for this: "a contact sheet of your cards (Pillow) under state/arsenal/shaders/cards/" (`<WFS>\shader-school-build-2b-wf_2857fa6c-f17.js` line 29).
- **Occurrences:** 29 scripts, 94 inline builds.
- **Cost:** a few minutes of authoring per agent, and inconsistent measurements between reviewers.
- **Fix:** add `py -m arsenal shader look <png> stats|sample x,y|crop|channel-min` and `py -m arsenal shader card --sheet <names>`.

### 17. "Does the pin bite?" mutation checks are hand-rolled each time (hand-rolled script)

- **Evidence:**
  - 8 mutation scripts by 7 agents (`mutate.py` in two different workflows, `mutants.py`, `mutate_pins.py`, `mutant_light_probe.py`, `mutant_rays_probe.py` ...).
  - 42 calls involving `mutat`/`MUTANT`.
  - Example: the env-switch mutants loop at `wf_32d773d9-bd6/agent-a5159d6ae973e64b1.jsonl:429` and `:528`.
- **Occurrences:** 8 scripts, 42 calls.
- **Cost:** about 10 to 20 minutes of authoring per reviewer.
- **Fix:** a small house helper that applies a named mutant (a text patch or a monkeypatch), runs the named tests, restores the file and prints caught or missed. It fits the pin-first rule that 12 scripts already carry.

### 18. Atlas lookups by file are done by hand (rediscovery and hand-rolled script)

- **Evidence:**
  - `arsenal/shaders/atlas.json` was opened directly in 158 shell calls by 36 agents, while `py -m arsenal shader atlas` ran 39 times by 20 agents.
  - The verb filters only by family, category, status, built, groups, ledger, tags and rulings. Its `--help` output is at `wf_2857fa6c-f17/agent-a3084eb892e308c06.jsonl:42`.
  - The brief says to read the atlas rows with "py -m arsenal shader atlas --json, filter by file" (`<WFS>\shader-school-build-2a-wf_ab3d7b01-cf2.js` line 46).
  - The 198 KB `primitive-atlas-draft.md` was read by 14 agents, 27 times. 7 agents wrote the atlas JSON to the same `<SCRATCH>\atlas.json`: four batch-A agents within 6 seconds (10:26:19 to 10:26:25Z) and two batch-B agents within 5 seconds (11:42:22 to 11:42:27Z) (item 9).
  - One agent crashed on `KeyError: 'uvCentered'` hand-walking the structure (`wf_2857fa6c-f17/agent-abadb13dbf0a25920.jsonl:110`).
- **Occurrences:** 158 direct loads.
- **Cost:** many orientation turns.
- **Fix:** add `atlas --file <glsl path>` and `atlas --name <function>`, which print just those rows. Write `atlas --json --out FILE` as plain UTF-8.

### 19. Contracts were learned by reading source (rediscovery)

- **Evidence:**
  - `arsenal/shaders/modules.py` was read by 15 agents (29 reads), `licence_line.py` by 15 (26), `cards.py` by 12 (19) and `serve.py` by 10.
  - `arsenal/web/glsl/README.md` was read by 18. The README existed, but agents still went to the source for lint rules, hook declarations and the card receipt shape.
  - The lint message "calls expose(), which no module provides and no hook declares" shows the rule lives in code (`wf_ab3d7b01-cf2/agent-a35553e7dce3d8a32.jsonl:355`).
- **Occurrences:** 15, 15, 12 and 10 readers of the four sources (the sets overlap; the distinct total was not computed).
- **Cost:** reading cost; several 1000-line files.
- **Fix:** put the lint rules, the hook syntax, the card receipt fields and the licence-line JSON schema into `arsenal/web/glsl/README.md` and into each verb's `--help`.

### 20. Big files were read in truncated slices (friction)

- **Evidence:** 15 "PARTIAL view" truncation notices, for example:
  - `toy-runtime.js` "lines 1-846 of 1828" at `wf_760d007f-ff6/agent-af4b3978867fdd043.jsonl:33`
  - `stage.js` "1-826 of 1204" three times, and later "1-825 of 1475"
  - `explain.py` "1-928 of 1236"

  `toy-runtime.js` was read by 12 agents (24 reads) and `stage.js` by 9 (21).
- **Occurrences:** 15 notices.
- **Cost:** extra Read turns.
- **Fix:** a top-of-file function index in these modules, or a doc map, so an agent can jump with `offset`.

### 21. The root AGENTS.md is injected into every subagent (friction: context cost)

- **Evidence:**
  - The nested-instructions hook injected the root `AGENTS.md` (13,426 bytes) into 84 of 90 agents, and `arsenal/web/AGENTS.md` into 39. That is 129 injections and about 1.26 million characters, roughly 300 thousand tokens at about 4 characters a token. The first example is at `wf_ae993e74-ec3/agent-acda0f5264b1a8dbb.jsonl:32`.
  - Its first screen tells the reader to boot, learn, lock under its own id and sync the bus.
  - The deconstruct brief forbids exactly that: "NEVER: boot, learn, note, handoff, wrap, grant, lock/unlock, bifrost-send" (`<WFS>\deconstruct-the-house-wf_e267ca8b-f7c.js` line 18).
  - One research agent obeyed AGENTS.md, tried `boot vandor-re-audio` and was refused under the identity law (`wf_5d01ae05-3d2/agent-a8aabe0ed4851b0a3.jsonl:61`).
- **Occurrences:** 84 injections of the root file.
- **Cost:** about 300 thousand tokens of context in this half, plus conflicting instructions.
- **Fix:** a short workflow-subagent preface at the top of AGENTS.md, for example: "a workflow subagent follows its brief; do not boot or learn unless told". Alternatively, scope the injection.

### 22. Recall-at-action repeats off-topic hints (friction: context cost)

- **Evidence:**
  - 716 recall injections (394,901 characters) in this half.
  - The same block repeated within one agent up to 51 times: "[verb] `py agent_cli.py discord` — watch the fleet from your phone" in fix2:L (`wf_32d773d9-bd6/agent-a5159d6ae973e64b1.jsonl`, first at line 50). The same hint reached fix:L 22 times, and "[verb] `py agent_cli.py tail`" reached fix:lab-safety 19 times.
  - Across agents, the `tail` hint appeared 107 times in 32 agents.
  - All 90 agents carry one `sessionId` (the parent's). `claude_pretooluse.py` line 272 says per-session anti-repeat "prevents the same lesson repeating", but the observed repeats show it does not, at least for verb hints. The cause is unknown.
- **Occurrences:** 716 injections; up to 51 repeats per agent.
- **Cost:** about 100 thousand tokens, plus noise next to every Bash and Edit call.
- **Fix:** key anti-repeat by agent id (present in every transcript record), and hold `[verb]` hints to a relevance floor.

### 23. Orientation is long, and the same probes run at the same second (rediscovery)

- **Evidence:** across all 90 agents, a median of 41 tool calls and 8.1 minutes passed before the first Edit or Write (the 90th percentile is 95 calls). Research and review lanes write late by design. Identical early commands by several agents:
  - three batch-A agents ran `grep -n "^#" .../unified-architecture-draft.md` at 10:26:18Z
  - four agents ran `wc -l` on the three in-flight shader-school docs
  - three deconstruct-card agents ran `ls -la` on the in-flight folder at 13:18:06 to 08Z
  - four corroboration agents listed `state/arsenal/shaders/study` and `renders` at 14:08:20 to 21Z
  - `build-spec-reconciled.md` was read by 46 agents and `unified-architecture-draft.md` by 18 (30 reads)
- **Occurrences:** 27 distinct early commands were run by more than one agent.
- **Cost:** minutes per agent.
- **Fix:** the conductor computes the table of contents, file inventory and section pointers once and puts them in the brief.

### 24. Unwritten conventions that every agent carries (rediscovery)

- **Evidence:** no brief mentions these, yet agents typed them hundreds of times:
  - `-p no:cacheprovider` in 391 pytest calls by 49 agents (`pytest.ini` line 6 has only `addopts = -q`)
  - `timeout <N> py` in 268 calls by 30 agents
  - `GIT_OPTIONAL_LOCKS=0` in 47 calls
  - `Set-Location E:\AI-Setup` in 716 calls and `cd E:/AI-Setup` in 616, because the shell resets the working folder
  - the full scratchpad path literal in 1489 calls by 87 agents
- **Occurrences:** see counts.
- **Cost:** tokens and attention.
- **Fix:**
  - if `no:cacheprovider` is the house rule for parallel runs, put it in `pytest.ini` addopts
  - give agents a short `$SCRATCH` variable through the `env` block or the brief
  - write `timeout` and `GIT_OPTIONAL_LOCKS` into the template, so the habit is a rule

### 25. The Remove-Item guard blocks harmless scratch deletes (friction)

- **Evidence:** the harness guard misread variable-built paths in 4 agents:
  - `Remove-Item "$s\cards\*.card"` (scratch) was refused as "Remove-Item on system path 'E:\AI-Setup' is blocked" (`wf_07b70c9d-63b/agent-afaf271492ab044ff.jsonl:1040`)
  - `Remove-Item -Recurse -Force $m`, a scratch mirror, was refused as `'E:\AI-Setup\arsenal\web\lib\*'`, the source of a later Copy-Item (`wf_7108d788-f9d/agent-aaddad9749ac61907.jsonl:492`)
  - `Remove-Item Env:PYTHONHASHSEED` was refused as `'\\rr2_dump_'` (`wf_5776878b-3fd/agent-ac366bf38830c3095.jsonl:167`)
  - the guard refused `'/'` at `wf_2857fa6c-f17/agent-a1bad7126e661cc69.jsonl:346`
- **Occurrences:** 4.
- **Cost:** 4 turns, with a median of 8 seconds to the next clean call.
- **Fix:** template line: "delete scratch files with literal paths, or from Python (`shutil`)". The false positives are worth reporting to the harness owners.

### 26. Waiting by sleeping is blocked (friction)

- **Evidence:** "Blocked: sleep 60 followed by ..." at `wf_32d773d9-bd6/agent-a902e574f48691bee.jsonl:59` and `wf_7108d788-f9d/agent-a89517df2ba319cad.jsonl:302`. Other agents used `run_in_background` with Monitor or `until` loops (9 calls) correctly.
- **Occurrences:** 2.
- **Cost:** 2 turns.
- **Fix:** template line: "long runs go to run_in_background; wait with Monitor or until, never sleep".

### 27. A safety classifier stopped two research writes (other)

- **Evidence:** "Not run: the response that made this tool call was stopped by a safety classifier" on the Write of two reverse-engineering research reports: the legal and clean-room method lane, and the web and protocol lane. The records are `wf_5d01ae05-3d2/agent-ad2827ea2c619f6c4.jsonl:398` (13:14:06Z) and `wf_5d01ae05-3d2/agent-a5ea776d6ba294a46.jsonl:363` (13:14:09Z). Both agents then reported honestly that nothing was written. The final-round script later added "If a safety check stops you, stop and report what you completed" (`<WFS>\shader-school-final-round-wf_7108d788-f9d.js` line 13).
- **Occurrences:** 2 of 8 research lanes lost their report in that run.
- **Cost:** two lanes of research time (about 17 minutes each) had to be redone or absorbed elsewhere.
- **Fix:** keep the stop-and-report clause in the template. Route such lanes the way the existing memory note about safeguard ejects advises. Have the lane write its report in sections, so a stop loses one section, not the file.

### 28. Small tool frictions (friction)

- **Evidence:**
  - The Grep tool refused nested brace alternation in a glob (`wf_ab3d7b01-cf2/agent-aadbce3a55a9d4119.jsonl:264`).
  - Grep on the `tasks` directory was refused (`wf_ae993e74-ec3/agent-a398ba48bcb9c9e5d.jsonl:217`).
  - `card --render --out <scratch>` was refused: "outside E:\AI-Setup\state; pass --allow-tracked" (`wf_07b70c9d-63b/agent-a4fc73a8b22ec1fbd.jsonl:864`).
  - `pytest --runslow` was unrecognized; slow tests run with `-m slow` (`wf_07b70c9d-63b/agent-a91016d585ce01c59.jsonl:88`).
  - Edit "String to replace not found" happened 4 times, and "File has been modified since read" once, while another slice touched `arsenal/shaders/cli.py` (`wf_ab3d7b01-cf2/agent-a298346af0992ea7c.jsonl:268`).
  - Browser zoom timed out once (`wf_2857fa6c-f17/agent-ad751e633f71c365f.jsonl:637`).
- **Occurrences:** 9.
- **Cost:** about 9 turns.
- **Fix:** template lines for `-m slow` and for renders living under `state/`. The rest needs nothing.

### 29. Went well: the read-only git rule held (went well)

- **Evidence:** a search of all 4564 shell calls for `git stash|checkout|reset|restore|add|commit` found no mutating command. The only hit was `git stash list`, which reads (`wf_ab3d7b01-cf2/agent-a1668c14851d548da.jsonl:242`). `git status` ran 46 times, `git diff` 38 and `git log` 39. The clause is in 12 scripts.
- **Occurrences:** 0 violations.
- **Cost:** none.
- **Fix:** keep the clause, in the template.

### 30. Went well: fast recovery, background runs and pin-first discipline (went well)

- **Evidence:**
  - The median time to the next clean call after a cp1252, BOM or import error was 3 to 5 seconds (one turn).
  - 34 agents read their own background task output files 93 times rather than blocking.
  - Monitor was used and `sleep` was blocked only twice.
  - 69 red test results across 19 agents were deliberate pin-first reds.
  - Reviewers built mutation checks to prove the pins bite (item 17).
  - Three agents loaded the shader-craft skill when touching shaders (`wf_2857fa6c-f17` groups:g1 line 175, groups:g2 line 230, `wf_07b70c9d-63b` fix:aurora+uniforms line 50).
- **Occurrences:** see counts.
- **Cost:** none.
- **Fix:** keep it. Making items 1, 2, 6 and 9 impossible would remove most of the one-turn recoveries.

---

## The briefs: what every script repeated by hand

I read all 23 scripts in `<WFS>` and extracted the 21 RULES-like constants (`RULES`, `HOUSE_RULES`, `REPO`, `REPO_RULES`). They run from 292 to 3122 characters.

**Copied by hand in each script:**

- `const R = 'E:\\AI-Setup'`, redefined in most scripts.
- The three shader-school document paths (the spec, the architecture draft and the atlas draft), redefined in five scripts.
- The session's absolute `tasks\w*.output` paths (`OUT`, `OUT2A`, `B2C`, `RE2`), pasted from the previous run, and the absolute scratchpad path.

**Clauses repeated in many scripts:**

| clause | scripts |
|---|---|
| GPU safety: render only through the shader verbs, never the browser pane, never port 8793 | 14 |
| "other agents are editing these files" | 14 |
| "Glob does not work on E:\\ paths" (stale, item 12) | 13 |
| "never copy corpus code" | 13 |
| "No git command that changes anything (Vandor commits)" | 12 |
| "pin first, see it fail" | 12 |
| "PYTHONIOENCODING=utf-8" (only for printing the previous review) | 9 |
| "Daniel is a non-programmer, plain words, hardware analogies" | 5 |
| "Use 'py'. LF endings." | most |

**Missing from every brief, but rediscovered by agents in this half:**

| rule | scripts that carry it |
|---|---|
| UTF-8 for all Python output (item 1) | 0 general (9 for review JSON only) |
| utf-8-sig for redirected JSON (item 6) | 2 |
| import path for scratch scripts (item 2) | 0 |
| lock identity (item 7) | 0 |
| Bash for native programs (item 3) | 4 old scripts only |
| write scripts to files, not heredocs (item 8) | 0 |
| own scratch subfolder (item 9) | 0 |
| known-red tests (item 11) | 0 |
| forward slashes in structured output (item 14) | 0 |
| `arsenal shader --help` workaround (item 4) | 0 |
| licence-line JSON shape (item 5) | 0 |
| `-m slow` (item 28) | 0 |
| waiting rule (item 26) | 1 |

**Prompt sizes.** In this half the median brief was 3879 characters. The largest was 29,260 characters: a reviewer brief with the fixers' reports pasted in.

**Verdict.** The briefs carry intent well. Daniel's words appear verbatim in 8 scripts, and each slice names its files. The house rules, however, are a copy-paste lineage: they drift, keep one stale rule, and omit the rules agents paid for. Three changes would fix this:

1. **One house rules block, kept in one file.** For example, a section of the workflow-authoring skill or `docs/` that the conductor inlines. It has switches (repo, gpu, corpus, read-only, review-json, research-web) and includes every "missing" line above.
2. **A per-agent scratch folder and a per-agent lock id**, set by the conductor in the brief (or by the harness).
3. **The review section as text.** Pass each fixer its own review section in the prompt instead of a path to a large JSON.

---

## Coverage

**Read:**

- **Transcript set.** The subagent folder held 393 files at 14:11 local time. That includes 13 files from this retro workflow (`wf_4e140bc0-2ea`), which I excluded because it is the run doing the reading; the remaining 380 match the brief's count. Of these, 201 are `.jsonl` transcripts and journals (the rest are `.meta.json`). Sorted by modification time, the later half is 101 files from `wf_ae993e74-ec3/agent-acda0f5264b1a8dbb.jsonl` (mtime 2026-10-13 05:38:15 local) to the last at 13:58:28 local. I added `wf_760d007f-ff6/agent-a3c7ec96e975c959d.jsonl`, which falls in the later half when counting all 380 files including meta. That makes 102 files (90 agent transcripts and 12 workflow journals), about 278 MB, plus their `.meta.json` for labels.
- **Extraction.** Every file was streamed line by line with Python, with no whole-file loads and each process well under 1 GB. I extracted every tool call (input truncated at 3000 characters), every tool result (truncated at 1500 characters), the first user message (the brief, truncated at 20,000 characters), the final assistant text, and every hook attachment (counted and sized in full).
- **Workflow scripts.** All 23 were scanned for constants and clauses; 6 were read in detail: build-2a, build-2b, final-round, reverse-engineering-arsenal, deconstruct-the-house and the retro script's RULES.
- **Repo files, to confirm causes:**
  - `arsenal/__main__.py` lines 150-179
  - `arsenal/shaders/licence_line.py` (argument definitions; JSON shape lines 920-921)
  - `arsenal/shaders/cli.py` (parser list)
  - `scripts/hooks/claude_pretooluse.py` lines 225-284
  - `%USERPROFILE%\.claude\settings.json` lines 1-70
  - `pytest.ini` (addopts)
  - `AGENTS.md` (size and first screen)

**Skipped, and why:**

- **Assistant thinking and mid-turn text:** not analysed semantically. Rules rediscovered only in prose, never in a tool call, are undercounted.
- **Tool results past 1500 characters:** errors whose decisive text came later may be misclassified. 52 nonzero exits were sub-classified by hand (item 3 and others).
- **The earlier half of the transcripts, the main transcript and `tool-results/`:** other lanes cover them.
- **The private shader corpus and study notes:** not opened.
- **No renders, browser, servers or GPU.**
- **Token costs:** estimated from character counts at about 4 characters a token, not measured.
- **Turn costs:** counted as model round trips, not seconds or tokens. Wall-clock figures come from the gap between the tool-use and tool-result timestamps.
- **Counts marked "unknown"** could not be derived from the extraction. Examples: the exact turn cost of item 15, and whether any agent actually read a sibling's scratch result as its own (item 9).
