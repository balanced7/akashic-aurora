# Retro, subagent transcripts (early half): shader school night, 2026-10-12/13

Daniel asked, 2026-10-13: "What did we learn from all of this? Would you mind fanning out agents to capture every friction point, hand rolled script, re derivation and any other thing that would've made the process better, i know we have a rich wealth of information waiting to be surfaced".

This lane covers the earlier half of the session's subagent folder: 190 of its 380 files by modification time. That is 89 agent transcripts, 10 workflow journals and 91 meta files. Agent work runs from 2026-10-13 02:14Z to 09:23Z, plus one inventory agent from 2026-10-12 12:58Z. Two arcs share this half. The piano story layer and its "lean" light account for 33 agents in 7 workflows. The shader school accounts for 55 agents in 5 workflows: studies, census, research, synthesis, the harness, runtime and dissector builds, the S0/S1/S4/licence-line slices, and the reviews and fixes. Transcript timestamps are UTC; local time was UTC-4.

## Summary

The agents made 5,450 tool calls. 85 were flagged errors (1.6%), and 35 more failed while exiting 0. Most of the cost did not come from errors. It came from things every agent had to work out again:

1. **The corpus had no map.** 38 agents explored `state/arsenal/shaders/corpus` by hand (249 shell commands). They guessed `meta.json` field names, and 34 of them wrote their own regex censuses of techniques. The folder still has no README.
2. **Windows shell traps hit dozens of agents.** Inline scripts were mangled by the Bash tool: backslashes and quotes inside heredocs broke 9 commands. The cp1252 console crashed Python output in 15 agents, yet only 6 of 89 briefs said to set `PYTHONIOENCODING`. Other traps: a `pytest.ini` that hides its own summary line (9 agents), a prescribed CR check that gives wrong counts in Git Bash, and PowerShell writing a BOM. Each rule ended up in some briefs but not others, because each workflow script copied its own preamble.
3. **Agents in parallel slices shared one working tree.** One slice's edit failed 6 seconds after another slice edited the same file. One builder spent 13 transcript lines proving that 24 failing tests were a sibling's red-first pins. A fixer watched another lane render with its half-edited driver.
4. **Tools existed but were not named.** The house `web_fetch` door fetched papers that WebFetch refused as over 10 MB, but only 1 of the 9 agents whose WebFetch calls failed tried it. Hooks injected `AGENTS.md` into 81 subagents (1.18M characters), plus 570 "recall-at-action" notes. The most frequent note named a verb no agent ever ran. Meanwhile 4 agents hand-wrote headless piano screenshot drivers (about 49 KB in total), and 2 agents in two workflows each built their own pipeline for "find Daniel's words".
5. **The work order put guards and ground truth late.** The licence line was built after the code it polices; its first run found 462 breaches. The 14 shader studies ran "blind" (inferring the picture from the code) because the runtime was built in parallel with them. The corpus had no media or preview images, so the fidelity judge could not confirm a fix.

What went well: the Glob rule was in 74 of 89 briefs, and agents made zero Glob calls in 5,450. Briefs learned during the night: the CR-check correction reached the next workflow 18 minutes after it was found. StructuredOutput was called 49 times with zero retries. Map agents obeyed the "spawn few processes" rule, with 1 to 9 shell calls each.

Evidence uses the form `label ln N`, meaning a line in that agent's transcript `.jsonl`. The appendix maps every label to its file. Labels that ran twice are told apart by agent id prefix.

---

## Items

### 1. The corpus layout and schema were worked out again by 38 agents
- **Kind:** re-derivation. **Fix:** a verb plus a doc.
- **Occurrences:** 249 shell commands touching `state/arsenal/shaders/corpus/shaders`, in 38 of 89 agents.
- **Evidence:**
  - All 14 study agents opened with the same exploration: list the shader folder, `cat meta.json`, list `study/`. Examples: study:dryice ln 13, study:glow ln 13, study:materials ln 14, study:aurora ln 13.
  - Hand-written scans guessed at field names, each falling back between two candidate keys for the title and the author (research:pattern-fractal-2d ln 25, research:water-sims-feedback ln 25, research:sdf-raymarching ln 29).
  - census:piano-studies ln 217 failed with `TypeError: unhashable type: 'dict'`: the licence field is an object, not a string.
  - The brief said the corpus held 336 shaders. The dissector found 335 (`workflows/wf_4321c88e-893/journal.jsonl` line 9).
  - Checked today: `state/arsenal/shaders/corpus/` holds `harvests/`, `sets.json` and `shaders/`, with no README. No Markdown file in the repo names the `arsenal.shader-meta/v1` api (grep).
- **Cost:** 1 to 3 orientation calls per agent across 38 agents, plus the failed guesses. Minutes: unknown.
- **Fix:** add `corpus/README.md` covering the layout, the `meta.json`, `shader.json` and `sets.json` fields, and the shape of the licence object. Add a `py -m arsenal shader corpus ls|count|grep` verb that prints ids and counts, never code. Put one line in every shader brief: "corpus map: see corpus/README.md".

### 2. Technique censuses over the corpus were hand-rolled, one per researcher
- **Kind:** hand-rolled script. **Fix:** a verb.
- **Occurrences:** 137 inline scripts classified as corpus scans, in 34 agents.
- **Evidence:**
  - research:lighting-materials ln 29 ran a grep loop that counted shaders per technique.
  - research:noise-procedural ln 313 used a regex table over the GLSL files.
  - research:color-post ln 266 failed with `re.error: invalid group reference 3` in its own `scan2.py`, then patched it with `sed` at ln 270.
  - research:sdf-raymarching ln 29 matched shaders by name and tag.
  - All eight research agents started between 06:35Z and 06:43Z. The dissector, which classifies techniques, finished at 07:51Z.
- **Cost:** about 4 scripts per researcher. Counts were not comparable between agents because each used different regexes.
- **Fix:** add `py -m arsenal shader census --technique <name>` on top of the dissector, with per-shader counts and a Loved flag. Order research after the dissector, or hand researchers its census file.

### 3. The Bash tool mangles backslashes and quotes in heredocs and inline scripts
- **Kind:** friction. **Fix:** brief.
- **Occurrences:** 9 flagged failures in 8 agents. This retro hit the same problem 3 times.
- **Evidence:**
  - fix:arch-anchor ln 74: a JS regex arrived with a collapsed backslash, giving `SyntaxError: missing ) after argument list`.
  - census:daniel-voice ln 84 and integrate:round1 ln 494: `unterminated string literal`.
  - `unexpected EOF while looking for matching '` at build:dissector ln 153, synthesis:atlas+architecture ln 146 (while appending a long Markdown section), integrate:round1 ln 373 and fix:runtime ln 213.
  - research:color-post ln 267: a regex escape broke.
  - verify:melody ln 215: an unquoted `(` in a for-list.
  - Agents described the cause themselves: build:runtime ln 202 found the tool decoded an escaped backslash and switched to `chr(92)`; census:daniel-voice ln 86 dropped the heredoc and wrote the file instead.
- **Cost:** 9 failed commands, each followed by a rewrite. One synthesis append had to be redone.
- **Fix:** add a preamble line: "any script longer than one line, or containing a backslash: create it with the Write tool, then run it. Never `py - <<EOF` or multi-line `py -c`." Item 23 explains why this matters more than it looks.

### 4. The cp1252 console crashes Python printing
- **Kind:** friction. **Fix:** process (environment).
- **Occurrences:** `UnicodeEncodeError` in 16 shell results across 15 agents. 6 were flagged as errors; the rest hid behind exit 0. `PYTHONIOENCODING` was typed 127 times by 15 agents.
- **Evidence:**
  - Flagged: verify:melody ln 115, census:daniel-voice ln 283, research:noise-procedural ln 175, research:water-sims-feedback ln 94, research:pattern-fractal-2d ln 170, synthesis:atlas+architecture ln 77.
  - Hidden behind exit 0: verify:vis ln 180, research:lighting-materials ln 115, S0:atlas ln 264.
  - Only 6 of 89 briefs carried the rule: the three fixers in wf_ae993e74 and the three in wf_760d007f, all from 08:44Z.
  - A house script fails on the default console: census:methodology (a0aaa76b3) ln 365-368 got a cp1252 traceback from `scripts/vfx_probe_chroma.py`.
- **Cost:** 16 failed or partial outputs, plus re-runs.
- **Fix:** set `PYTHONUTF8=1` (or `PYTHONIOENCODING=utf-8`) once in the harness environment, so every `py` child inherits it. House CLIs that print corpus or paper text should also call `sys.stdout.reconfigure(encoding="utf-8")`.

### 5. Reading PDFs fails, so every researcher wrote their own extractor
- **Kind:** friction. **Fix:** a verb.
- **Occurrences:** 7 failed PDF reads in 7 agents; 78 inline PDF-extraction commands in 13 agents.
- **Evidence:**
  - `pdftoppm is not installed` at research:vis ln 59, research:melody ln 39, research:tension ln 36, research:noise-procedural ln 57, research:water-sims-feedback ln 62, research:pattern-fractal-2d ln 159 and research:gpu-perf-glsl (a3c8b9a8b) ln 84.
  - Agents then probed for libraries. research:noise-procedural ln 60 found pypdf present, `fitz` deprecated and pdfminer missing.
  - `python` resolved to the Microsoft Store alias (exit 49) at research:melody ln 46 and verify:tension ln 29.
  - Printing the extracted text hit cp1252 on ligatures (research:noise-procedural ln 175, research:pattern-fractal-2d ln 170).
- **Cost:** about 6 commands per researcher before any paper text was readable.
- **Fix:** add `py agent_cli.py pdftext <pdf> [--pages a-b]`, which writes UTF-8 text to scratch (PyMuPDF is installed), and name it in research briefs. Alternatively, install poppler so the Read tool renders PDFs.

### 6. The house web_fetch door was already there, and 1 of 9 failing agents found it
- **Kind:** missed existing tool. **Fix:** brief.
- **Occurrences:** 26 of 441 WebFetch calls failed:
  - 10 MB cap: 6
  - domains the fetcher refuses: 5 (web.archive.org 3 times, stackoverflow.com, one unverifiable domain)
  - TLS or certificate errors: 6
  - network errors: 9
- **Evidence:**
  - Size-cap failures: research:lighting-materials ln 60 and 123, research:noise-procedural ln 112, research:volumes-atmosphere ln 48, 84 and 124.
  - research:volumes-atmosphere alone tried `mcp__akashic-aurora__web_fetch`. It noted the door's behaviour was unknown (ln 127). 9 of its 11 calls came back `ok: true`, including two PDFs WebFetch had refused for size (ln 133, ln 141).
  - Other agents fell back to memory or secondary sources (research:lighting-materials ln 63 and 120, research:water-sims-feedback ln 85).
- **Cost:** primary sources were skipped. That cost is unknown.
- **Fix:** research briefs should say: "if WebFetch refuses (size or domain), use the house `web_fetch` door".

### 7. Agents split on whether downloads were allowed
- **Kind:** other. **Fix:** process, and the rule is Daniel's call.
- **Occurrences:** 10 agents ran `curl` downloads into scratch (33 commands). 4 agents declined for permission reasons. 3 of 89 briefs mention downloading at all.
- **Evidence:**
  - Downloads: research:melody ln 69, research:tension ln 56, research:sdf-raymarching ln 138, research:gpu-perf-glsl (a3c8b9a8b) ln 323.
  - Declines:
    - research:volumes-atmosphere ln 66 and research:lighting-materials ln 120 skipped paper PDFs.
    - research:gpu-perf-glsl ln 411 noted that an offline GLSL validator would need a download.
    - integrate:round1 ln 86 used procedural stand-ins for missing shader textures.
- **Cost:** sourcing was inconsistent across topics, and the fidelity renders used stand-ins (see item 16).
- **Fix:** Daniel rules on overnight fetches of public papers and of corpus media. Briefs state the rule. Fetches go through the house door, which keeps a receipt.

### 8. A mid-run interrupt killed 4 agents, and their reruns started cold
- **Kind:** friction. **Fix:** process.
- **Occurrences:** 4 agents in 2 workflows. All ended with `[Request interrupted by user]` between 06:43:31Z and 06:44:22Z, under the same prompt id.
- **Evidence:**
  - The four killed agents:
    - research:gpu-perf-glsl (a720bd002) ln 51.
    - build:harness (aec8bc531) ln 224, after 50 calls and 19 minutes.
    - build:dissector (a8e42a51f) ln 88. Its last record before the interrupt is at 06:33:24Z, so about 10 minutes of generation never landed.
    - census:methodology (aa15ec8df) ln 406, after 95 calls.
  - The journals restart the same labels with new agent ids (`wf_4321c88e-893/journal.jsonl` lines 5-6, `wf_60f63f69-3ea/journal.jsonl` lines 47-48). For build:harness, both briefs had the same length (8,231 characters), and the second did not mention the earlier attempt.
  - The rerun build:harness (a7ccd4064, ln 20 and 29) found its predecessor's files and spent turns working out whether a crash or another agent had written them.
- **Cost:** about 269,000 output tokens from the four killed agents, plus the reruns' orientation. The cause of the interrupt is not visible from this lane.
- **Fix:** when a workflow resumes a killed agent, add one paragraph to the brief: "a previous attempt was interrupted at T; it wrote these files: ...". The journal and the killed transcript hold both facts.

### 9. Parallel slices shared one working tree
- **Kind:** friction. **Fix:** process.
- **Occurrences:** 63 mentions of sibling or concurrent work in the thinking of 23 agents. The 6 cases below have direct evidence.
- **Evidence:**
  - S0:atlas ln 194, 08:12:22Z: an Edit of `arsenal/shaders/cli.py` failed with `File has been modified since read`. L:licence-line had edited the same file at 08:12:15Z (ln 146). Both slices registered verbs there.
  - S0:atlas ln 250-262: S0 proved that 24 failing tests were S1's red-first pins and S1's not-yet-written `modlib.js`. S1 wrote that file at 08:15:58Z (ln 201). S0 copied HEAD's tests to scratch to check its own work.
  - fix:harness ln 291-300: another lane's render was already running fix:harness's half-edited driver. ln 343-348: a sibling's edited test file failed the licence test inside fix:harness's run.
  - build:port ln 91: the oracle directory was mid-write by build:oracle.
  - build:lean-v0 ln 339 and 346: `piano.js` held another seat's uncommitted edits with CRLF endings.
- **Cost:** each case cost several turns of forensics. Two slices reported test results polluted by their siblings.
- **Fix:** give each build slice its own git worktree, or a scratch copy, and add an integration step. Run slices that edit a shared registry (`cli.py` VERBS) one after the other, or make verb registration one file per verb.

### 10. Fix agents dug their review out of another workflow's task-output JSON
- **Kind:** re-derivation. **Fix:** process (workflow script).
- **Occurrences:** 18 commands in 7 agents.
- **Evidence:** fix briefs pointed at a `tasks/<id>.output` file plus an index such as `result.reviews[2]`. Agents then printed keys to find their slice: fix:S1 ln 12 and 19, fix:harness ln 12 and 17, fix:dissector ln 12 and 18, review:S0:atlas ln 49.
- **Cost:** 2 to 3 calls per fixer. There was also a risk of reading the wrong slice's review.
- **Fix:** the workflow writes each review and each builder report to its own Markdown file (for example `reviews/S1.md`) and passes that path.

### 11. Agents guessed the shapes of house JSON
- **Kind:** friction. **Fix:** doc.
- **Occurrences:** 104 inline probes of house JSON in 19 agents, most of them printing keys first. 5 failed on a wrong guess.
- **Evidence:**
  - census:piano-studies ln 217: the licence field is an object, not a string.
  - build:dissector ln 704: `TypeError: 'bool' object is not iterable` on a check report.
  - fix:harness ln 359: `load_allow() missing 1 required positional argument`.
  - fix:runtime ln 572: a TypeError on licence-line baseline entries.
  - fix:runtime ln 604: `KeyError: 'rows'` on a check report.
  - Every one of these files carries an `api` id (`arsenal.<x>/v1`). No doc found describes them.
- **Fix:** add `arsenal/shaders/SCHEMAS.md`, with one short section per `api` id: its fields, and what writes and reads it. Briefs that hand an agent a JSON file name its `api` id.

### 12. The LF rule was checked by hand, and the prescribed check was broken
- **Kind:** friction. **Fix:** test.
- **Occurrences:** the rule appeared in 37 briefs. Agents ran 48 CR-byte checks in 23 agents.
- **Evidence:**
  - The first brief that carried the rule (wf_af668d0e, 03:24Z) prescribed `grep -c $'\r'`. In this Git Bash that count is unreliable, and it made build:port believe it had written CRLF (ln 91, 98).
  - parity:level-A ln 187 passed the correction on. Briefs from wf_699e9662 (03:46Z) onward say to count CR bytes with Python instead.
  - Observed: files written with Write and Edit had 0 CR bytes (parity:level-A ln 187, review:privacy-house ln 105).
- **Cost:** one check per agent, plus one false alarm that cost build:port several turns.
- **Fix:** one shared check, either `py agent_cli.py eol <paths>` or a pytest that fails on CR bytes in tracked text files changed since HEAD. The preamble cites that check instead of teaching a shell one-liner, and states that Write and Edit write LF.

### 13. pytest hides its own summary
- **Kind:** friction. **Fix:** test (config).
- **Occurrences:** 20 commands in 9 agents.
- **Evidence:** `pytest.ini` sets `addopts = -q`, and its comment names `py -m pytest -q` as the standard command. Together they make pytest double-quiet, which drops the pass/fail summary line. Agents worked around it with `-o addopts=""`: parity:level-A ln 180 (it explains why at ln 187), fix:review-findings ln 165, 210 and 215, review:faithful ln 90, verify:independent ln 182.
- **Fix:** remove `-q` from `addopts`, or from the documented command. This is a one-line change.

### 14. Failures hid behind exit 0
- **Kind:** friction. **Fix:** brief.
- **Occurrences:** 35 shell results contained a traceback or SyntaxError but exited 0, in 20 agents. 17 of them were piped through `tail`, `head`, `grep` or `sed`.
- **Evidence:** census:methodology (a0aaa76b3) ln 365, build:dissector ln 660 and 664, S1:composer ln 122 and 127, fix:S1 ln 254, S0:atlas ln 258.
- **Cost:** a failure is invisible until an agent reads the output text. Some agents were spending effort on an error they had not noticed yet.
- **Fix:** add a preamble line: "Bash: start pipelines with `set -o pipefail`, or append `; echo exit=$?`".

### 15. The licence line was built after the code it polices
- **Kind:** other. **Fix:** process.
- **Occurrences:** 1 ordering, which caused 3 agents to rewrite their own code.
- **Evidence:**
  - The harness, runtime and dissector were written from 06:24Z to 07:51Z. The licence-line slice was built from 08:01Z to 08:22Z.
  - Its first run printed `licence line: BREACH (462 breaches, 4 exempt hits)` (L:licence-line ln 165). Some breaches were pre-existing house files such as `scripts/aurora-shader.js` (review:L:licence-line ln 36). Two were lines in `arsenal/shaders/dissect.py` written that night (integrate:round1 ln 625).
  - Later, build:dissector (ln 827), fix:dissector (ln 158) and fix:harness (ln 364-371) rewrote code or test fixtures to clear it. fix:harness ln 345 shows 10 flagged runs in `tests/test_shader_dissect.py`.
- **Fix:** build guards first, as slice zero. That means the licence line, and the renderer refusal and GPU lock checks. Builders then run the guard on their own files before reporting.

### 16. The studies were blind, and nothing on disk gave a ground-truth picture
- **Kind:** other. **Fix:** process.
- **Occurrences:** 14 study agents. One fidelity verdict was left unconfirmed.
- **Evidence:**
  - The study brief asked for "what you see" inferred from code, because the shader could not be run (study:glow ln 2).
  - The studies started at 06:21:40Z; the runtime and harness builds started at 06:24:40Z.
  - study:glow ln 125 tried to recall what the shader looks like on the site.
  - `integrate:judge1` (`wf_4321c88e-893/journal.jsonl` line 13) could not confirm a fidelity fix without a GPU reference such as the site's preview image. It reported 4 Loved shaders rendered with stand-ins for missing media and 2 without audio.
  - build:runtime ln 32: `corpus/media: No such file or directory`.
- **Fix:** order the work render-first. Harvest preview images and media together with the corpus, render stills under the lock, then study with the pictures. The fidelity judge then has a reference.

### 17. Hooks injected large amounts of context, mostly noise for subagents
- **Kind:** friction. **Fix:** hook.
- **Occurrences:**
  - The full `AGENTS.md` was attached 82 times to 81 of 89 subagents (1.18M characters, roughly 300k tokens). `arsenal/web/AGENTS.md` was attached 21 times.
  - Recall-at-action fired 570 times in 78 agents (813k characters).
- **Evidence:**
  - The most frequent recall injections were `py agent_cli.py discord` (92 times, on Write) and `py agent_cli.py tail` (39). No agent ran either.
  - `agent_cli.py` was run 16 times in total, and `boot` once (build:dissector ln 37).
  - Agents spent reasoning on whether `AGENTS.md`'s boot step applied to them (study:clouds ln 42, build:dissector ln 36, L:licence-line ln 69).
  - Median context at the first turn: 58,368 tokens per agent.
- **Fix:** hooks should recognise workflow subagents (meta `agentType: workflow-subagent`, `isSidechain`) and send a 15-line subagent card instead of `AGENTS.md`. Recall-at-action should drop repeats within a session and suppress verbs below a relevance bar.

### 18. A desktop Write hook opened pages in the Browser pane during a GPU-sensitive night
- **Kind:** friction. **Fix:** hook.
- **Occurrences:** 3 auto-opens in 2 agents, and 8 nudges to `preview_start` in 6 agents.
- **Evidence:**
  - The PostToolUse:Write hook reported that the written file "is now visible in the Browser pane":
    - build:lean-v0 ln 433 and 436 (05:12Z, `arsenal/web/piano.html`), while its brief said Daniel was playing on the live page.
    - build:harness ln 115 (06:32Z, a WebGL probe page).
  - build:harness listed the tabs (ln 119) and closed its own tab (ln 123). A `piano.html` tab was still open (ln 121). It was most likely the one build:lean-v0's write had opened 80 minutes earlier. It then routed later HTML writes through Bash heredocs (ln 125), which is the fragile path of item 3.
  - The "No preview server is running" nudge reached builders whose briefs forbade browsers and servers: build:port ln 45, integrate:round1 ln 115 and 337, fix:S4 ln 137, among others.
- **Fix:** turn off the auto-open and the preview nudge for workflow subagents, or for this repo. A WebGL page in the desktop pane renders on the real GPU, which is exactly what the house GPU rule avoids.

### 19. Two agents built separate pipelines to find "Daniel's words"
- **Kind:** re-derivation. **Fix:** a verb.
- **Occurrences:** 2 agents in 2 workflows. One used about 10 PowerShell queries, the other 9 Python scripts.
- **Evidence:**
  - map:intent-doctrine (02:14Z, story layer) used `Select-String` and `ConvertFrom-Json` over the session transcript and the rolling transcript archive (ln 140-162, 237), plus `recall` (ln 255 exited 2, ln 261).
  - census:daniel-voice (06:33Z, shader school) wrote `extract_human.py`, `extract_human2.py`, `search.py`, `search2.py`, `dump.py`, `prose.py`, `imgturns.py`, `extract_queued.py` and `extract_discord.py` (ln 38-286). Two of its commands failed (ln 84 and 283).
  - Both agents first had to find the two transcript stores (census:daniel-voice ln 13-33).
- **Fix:** add `py agent_cli.py said "<regex>" [--since date]`, which searches only Daniel's own turns across both stores and prints timestamped quotes.

### 20. `piano.js` is read over and over
- **Kind:** re-derivation. **Fix:** doc.
- **Occurrences:**
  - 83 Read calls by 15 agents. build:lean-v0 alone read it 21 times, and census:piano-core 15 times.
  - 54 Grep calls by 16 agents.
  - 72 shell commands naming it, in 16 agents.
- **Evidence:** the file served at 319,530 bytes (verify:arch-visual ln 97). Agents paged through it with offset and limit, then grepped for function names.
- **Fix:** commit a generated outline (section or function mapped to its line range) next to the file, or provide `py agent_cli.py outline <file>`. Splitting the file is the longer-term fix.

### 21. Headless piano screenshot drivers were hand-written 4 times
- **Kind:** hand-rolled script. **Fix:** a verb.
- **Occurrences:** 4 agents wrote driver scripts, about 49 KB in total. Chrome DevTools driver code appears in the inputs of 8 agents.
- **Evidence:**
  - build:lean-v0 ln 252 wrote `lean_shots.mjs` (9.0 KB).
  - review:visual ln 50 wrote `rev_ab_shots.mjs` (10.6 KB).
  - fix:lean-findings ln 306 wrote `lean_shots.mjs` (11.8 KB).
  - verify:arch-visual ln 92 wrote `x7_shots.mjs` (17.7 KB).
  - The last three repeat the same Chrome launch-flag block. Each driver turns the practice log off, takes the GPU lock, injects chords and takes screenshots (build:lean-v0 ln 257, 267).
- **Fix:** add a `py -m arsenal piano shot --key K --chords ... --framing ...` verb. It should assert the log is off, hold the lock, release it in `finally` and write a receipt. Reviewers would then compare like with like.

### 22. Every reviewer built their own twin-parity or mutation harness
- **Kind:** hand-rolled script. **Fix:** a verb.
- **Occurrences:** 9 agents, more than 20 scratch scripts.
- **Evidence:**
  - parity:level-A ln 101-111: `fuzz_gen.py`, `fuzz_check.mjs`, `mutate.mjs`.
  - review:faithful ln 63-68: `gen.py` and `check.mjs`, run on 30,000 random cases.
  - review:pins ln 45-63: a `harness.mjs` of 12.4 KB, plus a mutant copy made with `sed` at ln 49.
  - fix:review-findings ln 73: `mutants.mjs`.
  - verify:independent ln 65-168: 7 scripts.
  - L:licence-line ln 313: `mutate.py`.
  - review:S4:params ln 99: `diff.py`.
  - review:S1:composer ln 89-113: `exp1.py` and `exp2.py`.
  - build:port ln 134 linked the private oracle into a mutant tree with a directory junction.
- **Cost:** each reviewer spent its first third building scaffolding. The harnesses are not reusable, so no two verdicts rest on the same cases.
- **Fix:** add `py agent_cli.py twin-diff --py <module:fn> --js <module#fn> --cases <file|gen:N>` and `mutate <file> --at <pattern>` verbs. Briefs for twin slices name them.

### 23. Edits went around the Edit tool
- **Kind:** friction. **Fix:** doc.
- **Occurrences:** 19 Python string-replace patches into repo files, in 9 agents. build:dissector made 8 of them.
- **Evidence:**
  - Failures: build:dissector ln 153 (quoting mangled), ln 184 (`AssertionError`, the replace target was not found), and ln 234 (`FileNotFoundError` for a block file).
  - census:first-light-present ln 312 gave the reason: multi-hunk changes felt safer as one Python replace, and it worried about newlines.
- **Fix:** add a doc line stating that Edit keeps LF and fails safely when the file changed underneath it. For several hunks, use several Edit calls. Together with item 3, this removes the main reason for Python patching.

### 24. Huge inlined briefs, and the same content read again from disk
- **Kind:** friction. **Fix:** brief.
- **Occurrences:** 6 agents.
- **Evidence:**
  - critic:completeness, judge:rulings, judge:feasibility and judge:truth received briefs of about 158,000 characters and started at 123,600 to 124,300 context tokens. The median agent started at 58,400.
  - The three judges also re-read the discovery reports from disk: 10, 10 and 7 reads.
  - synthesis:atlas+architecture received a 294,334-character brief and started at 187,365 tokens. It then wrote two long documents in parts, and one append failed (ln 145-146, item 3).
- **Fix:** pass paths and a one-paragraph abstract, not whole reports inline. Write long documents as part files with Write, then join them with one `py` call.

### 25. Windows path and shell dialect slips
- **Kind:** friction. **Fix:** doc.
- **Occurrences:** at least 7 failures. `/c/Users/...`-style paths were typed 123 times in 18 agents. `sys.path.insert(0, ...)` appears 87 times in 22 agents.
- **Evidence:**
  - Git Bash paths passed to Python or Node:
    - integrate:round1 ln 72: `FileNotFoundError: [WinError 3]` on a `/c/...` path.
    - build:dissector ln 47: a `/e/AI-Setup/...` path.
    - fix:arch-anchor ln 158: a `file:` URL glued to a Windows path, giving ENOENT.
  - PowerShell:
    - fix:runtime ln 558: a `>` redirect wrote a BOM, giving `JSONDecodeError: Unexpected UTF-8 BOM`.
    - design:audience ln 128: a multi-line `.Replace()` chain failed to parse.
    - fix:harness ln 359: native stderr was wrapped as NativeCommandError.
    - map:offline-grammar ln 132: PowerShell 5.1 strips double quotes for native programs, so the agent wrote a script file.
  - review:S0:atlas ln 64: a scratch script run from outside the repo failed with `No module named 'arsenal'`.
- **Fix:** add a ten-line "Windows shells" card to the shared preamble:
  - give `py` and `node` Windows paths;
  - run repo code with `py -m` from the repo root, or set `PYTHONPATH`;
  - in PowerShell 5.1, write JSON from `py`, never with `>`;
  - put multi-line logic in a script file.

### 26. No offline GLSL validator on the host
- **Kind:** other. **Fix:** process, and installing one is Daniel's call.
- **Occurrences:** 2 agents probed for one.
- **Evidence:**
  - build:runtime ln 62 checked for `glslangValidator`, `glslc`, `naga` and `spirv-val`: no Vulkan SDK, no `glslang` module.
  - research:gpu-perf-glsl (a3c8b9a8b) ln 411-413 ran the same probe and noted that any validator would need a download.
  - As a result, every compile check went through headless Chrome under the GPU lock: 42 lock receipts in 14 agents.
- **Fix:** decide whether to install a CPU GLSL validator. It would give fast lint without taking the lock.

### 27. All subagents shared one scratchpad
- **Kind:** other. **Fix:** brief.
- **Occurrences:** low.
- **Evidence:**
  - research:melody ln 72 and 105, and research:tension ln 95, saw each other's downloaded papers. research:melody reused one of them.
  - One scratch path was written by two agents: `lean_probe/probe.mjs`, by review:truth and fix:lean-findings.
  - Later shader briefs used per-slice subfolders (`sliceb/`, `integ/`, `s1review/`) and had no collisions.
- **Fix:** the preamble names a per-agent scratch subfolder (`scratch/<label>/`).

---

## What went well

### W1. A rule carried in the brief removes the error class
74 of 89 briefs said Glob returns empty on `E:\` paths. There were 0 Glob calls in 5,450 tool calls, and 0 misses of that kind. The other rules in items 3, 4, 12, 13 and 25 would behave the same way if every brief carried them.

### W2. Briefs learned during the night
- The CR-check problem was found at 03:28Z (build:port ln 98) and was in the next workflow's briefs at 03:46Z.
- `PYTHONIOENCODING` reached the fix briefs at 08:44Z.
- Concurrent-edit warnings ("another workflow is editing these files; do not touch them") were in 70 of 89 briefs.

The weakness is that each lesson lived in one workflow script's string, so the next script had to copy it again. A single shared preamble file, included by every workflow script, would carry a lesson once.

### W3. Discipline held where it was asked for
- Map agents told to "keep process spawning to a minimum" made 1 to 9 shell calls each (map:live-signals: 1).
- StructuredOutput: 49 calls, 0 schema retries.
- No Read call failed for file size; agents paged with offset and limit.
- The GPU lock was taken for every render burst (42 receipts). When the lock was held, fix:harness queued its check in the background rather than fighting it (ln 289-292).

---

## Numbers at a glance

| measure | value |
|---|---|
| files in this half | 190 (89 transcripts, 10 journals, 91 meta) |
| tool calls | 5,450: Bash 1,957, Read 1,248, Edit 615, Grep 486, WebFetch 441, WebSearch 271, Write 206, PowerShell 143, StructuredOutput 49, ToolSearch 19, house web_fetch 11, Glob 0, Skill 0 |
| flagged errors | 85 (see breakdown below) |
| failures hidden behind exit 0 | 35 in 20 agents (17 behind a pipe) |
| inline scripts (`py -c`, `py -`, heredocs) | 642 commands: `py -c` 400 in 65 agents, `py -` 180 in 29 agents |
| scratch scripts written with Write | 96 in 26 agents |
| output tokens | 10.18M |
| median context at first turn | 58,368 tokens |
| median tool calls before a builder's or fixer's first edit | 21 |
| agents killed by the 06:43Z interrupt and rerun | 4 |

Breakdown of the 85 flagged errors:
- WebFetch network: 9
- shell quoting or backslash mangling: 9
- expected red test runs: 8
- PDF read with no poppler: 7
- path dialect or missing file: 7
- WebFetch TLS: 6
- cp1252: 6
- WebFetch 10 MB cap: 6
- other: 6
- JSON shape guess: 5
- WebFetch domain refused: 5
- benign nonzero exit (`ls` of a missing path, `wc` on a directory, `git diff --no-index`): 3
- `python` Store alias: 2
- PowerShell parse or native stderr: 2
- stale Edit: 1
- module import path: 1
- GPU lock held: 1
- BOM: 1

---

## Coverage

**What I read.**
- I listed all 393 files in the folder by modification time. I excluded the 13 files of this retro's own workflow (`wf_4e140bc0-2ea`, born after the task was written), which leaves 380, matching the brief.
- I took the earlier 190. The last file in this half is `workflows/wf_760d007f-ff6/agent-a65ba60ee609c2469.jsonl`, at 05:23:01 local (09:23:01Z). The later half begins one second after.
- Two agents straddle the boundary: their meta file is in this half and their transcript in the later one. I left those transcripts to the later lane.

**How.** I streamed every transcript and journal in this half line by line with `py`, never holding more than one record in memory, in four passes:
1. Tool uses and results: errors, commands, reads, writes, hooks and briefs.
2. Signature counts over the full tool inputs, results and thinking.
3. A rule scan over the first two user messages of each agent, which is the whole brief.
4. A masked-failure scan.

I also read selected transcript ranges in full to confirm the items above. Repo checks were read-only: `pytest.ini`, `.gitattributes`, the corpus folder listing, and a grep for schema docs.

**What I skipped.**
- I did not read any corpus GLSL.
- I did not quote agent prose; the only quotes are Daniel's own words and short tool error strings.
- I did not follow the browser-profile and practice-log paths that appear in some transcripts.
- I did not open the later half of the folder.

**Limits.**
- Error categories come from regexes over the error text. "Other" holds 6 that fit no rule.
- Thinking-text counts (concurrency mentions, for example) are keyword matches, not judgements.
- "Retries" are not counted precisely: the transcripts do not mark a retry. Items cite the observed failure-then-rewrite sequences instead.
- Durations and token costs are taken from the transcripts. Minutes lost per item are unknown unless stated.
- The cause of the 06:43Z interrupt is not visible in subagent transcripts.

---

## Appendix: agent labels and transcript files

All paths are relative to the session's `subagents/` folder. Times are UTC.

| label (phase) | workflow | transcript file | start (UTC) | tool calls | flagged errors |
|---|---|---|---|---|---|
| Inventory arsenal/media toolkit (-) | (top) | agent-a000aaec5601070ce.jsonl | 2026-10-12 12:58:48 | 17 | 0 |
| map:live-signals (Map) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a36aae59346a466de.jsonl | 2026-10-13 02:14:46 | 87 | 0 |
| map:offline-grammar (Map) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a258c84a285fea2a9.jsonl | 2026-10-13 02:14:48 | 65 | 0 |
| map:intent-doctrine (Map) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a605b214ae7377735.jsonl | 2026-10-13 02:14:48 | 85 | 1 |
| research:tension (Research) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a5d3213c6031e211b.jsonl | 2026-10-13 02:21:44 | 91 | 2 |
| research:vis (Research) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a58c6512dafa82051.jsonl | 2026-10-13 02:21:45 | 88 | 1 |
| research:melody (Research) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-aac8f2522dcd16649.jsonl | 2026-10-13 02:21:45 | 93 | 3 |
| verify:vis (Verify) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a63c1b1dc466b3af6.jsonl | 2026-10-13 02:30:45 | 76 | 3 |
| verify:melody (Verify) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-aa458d44d6414ad4a.jsonl | 2026-10-13 02:31:55 | 76 | 2 |
| verify:tension (Verify) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a4fbe2853f851eaba.jsonl | 2026-10-13 02:34:43 | 59 | 1 |
| critic:completeness (Critic) | wf_39e2cf44-316 | workflows/wf_39e2cf44-316/agent-a60ed0466ecb37de5.jsonl | 2026-10-13 02:40:16 | 12 | 0 |
| design:performer (Design) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-afaee3b12f44b9c3a.jsonl | 2026-10-13 02:48:07 | 45 | 0 |
| design:idiom (Design) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-aad8d064a6cba01bd.jsonl | 2026-10-13 02:48:07 | 54 | 0 |
| design:audience (Design) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-aaeb3dc71c453e6e2.jsonl | 2026-10-13 02:48:07 | 50 | 1 |
| judge:rulings (Judge) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-afde2476e5c462c0d.jsonl | 2026-10-13 03:11:11 | 22 | 0 |
| judge:feasibility (Judge) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-a2ee5d0d833dc0422.jsonl | 2026-10-13 03:11:12 | 37 | 0 |
| judge:truth (Judge) | wf_960d30ea-fe5 | workflows/wf_960d30ea-fe5/agent-a21f74a2ab21d4012.jsonl | 2026-10-13 03:11:12 | 23 | 0 |
| build:oracle (Build) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-aa4f0b66459632766.jsonl | 2026-10-13 03:24:28 | 18 | 0 |
| build:port (Build) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-a8e3c2fe3dae607ff.jsonl | 2026-10-13 03:24:29 | 27 | 2 |
| parity:level-A (Parity) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-a44519cf9f17d8c1e.jsonl | 2026-10-13 03:29:52 | 38 | 0 |
| review:faithful (Review) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-ab384b144cdf9ba18.jsonl | 2026-10-13 03:40:22 | 26 | 0 |
| review:privacy-house (Review) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-a4e3b0f9cf2476ad8.jsonl | 2026-10-13 03:40:23 | 19 | 0 |
| review:pins (Review) | wf_af668d0e-46f | workflows/wf_af668d0e-46f/agent-acb9d55a559883df1.jsonl | 2026-10-13 03:40:23 | 18 | 0 |
| fix:review-findings (Fix) | wf_699e9662-28e | workflows/wf_699e9662-28e/agent-ae1408061853ed627.jsonl | 2026-10-13 03:46:12 | 47 | 0 |
| verify:independent (Verify) | wf_699e9662-28e | workflows/wf_699e9662-28e/agent-a2894298581a14bf1.jsonl | 2026-10-13 03:51:45 | 51 | 0 |
| build:lean-v0 (Build) | wf_29f7007b-3d1 | workflows/wf_29f7007b-3d1/agent-ac618adff1ae264ad.jsonl | 2026-10-13 04:50:51 | 181 | 0 |
| review:truth (Review) | wf_29f7007b-3d1 | workflows/wf_29f7007b-3d1/agent-a1e963bbd914f8d58.jsonl | 2026-10-13 05:26:55 | 29 | 1 |
| review:visual (Review) | wf_29f7007b-3d1 | workflows/wf_29f7007b-3d1/agent-acf02aaaf1469b685.jsonl | 2026-10-13 05:26:56 | 43 | 0 |
| review:house (Review) | wf_29f7007b-3d1 | workflows/wf_29f7007b-3d1/agent-ac83b7439a80274d0.jsonl | 2026-10-13 05:26:56 | 37 | 1 |
| fix:lean-findings (Fix) | wf_d119a4ae-412 | workflows/wf_d119a4ae-412/agent-a994e3842884fc3bc.jsonl | 2026-10-13 05:37:16 | 91 | 0 |
| verify:truth (Verify) | wf_d119a4ae-412 | workflows/wf_d119a4ae-412/agent-a09e244d64a90914b.jsonl | 2026-10-13 06:00:32 | 25 | 0 |
| verify:visual (Verify) | wf_d119a4ae-412 | workflows/wf_d119a4ae-412/agent-a1b34a97ec92eab8a.jsonl | 2026-10-13 06:00:33 | 25 | 0 |
| study:aurora (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-aa430f7151b7c2b70.jsonl | 2026-10-13 06:21:38 | 39 | 0 |
| census:piano-core (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a038dc8a1b59cd0c0.jsonl | 2026-10-13 06:21:38 | 59 | 0 |
| census:piano-studies (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a7949b3d27f6ee063.jsonl | 2026-10-13 06:21:40 | 77 | 1 |
| study:clouds (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a19e237fe0ce54b99.jsonl | 2026-10-13 06:21:40 | 16 | 0 |
| study:dryice (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-adcb107cb0ae4df56.jsonl | 2026-10-13 06:21:40 | 11 | 0 |
| study:humanimation (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a52a23a1645517c57.jsonl | 2026-10-13 06:21:40 | 16 | 0 |
| study:tdhooper-b (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a06209fd4ce544a1e.jsonl | 2026-10-13 06:21:40 | 23 | 0 |
| study:mrange (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-aeb9ed7ba0f8f2c37.jsonl | 2026-10-13 06:21:40 | 26 | 0 |
| study:hexglitch (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-af09615ed78330e06.jsonl | 2026-10-13 06:21:40 | 14 | 0 |
| study:tdhooper-a (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-aae122e0d4deb44b7.jsonl | 2026-10-13 06:21:40 | 14 | 0 |
| study:cubes (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-acdd433d73aef7c99.jsonl | 2026-10-13 06:21:40 | 17 | 0 |
| study:glow (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a36714a9e72eb6be1.jsonl | 2026-10-13 06:21:40 | 38 | 0 |
| study:audio (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a88046e62a42480bd.jsonl | 2026-10-13 06:21:40 | 21 | 0 |
| study:raymarch (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-af31d36aef7013c56.jsonl | 2026-10-13 06:21:40 | 18 | 0 |
| study:demoscene (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a1d018a3a35352465.jsonl | 2026-10-13 06:21:40 | 16 | 0 |
| study:materials (Study) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a4a459ecd74a0c5f6.jsonl | 2026-10-13 06:21:40 | 21 | 0 |
| fix:arch-anchor (Fix) | wf_98988993-e87 | workflows/wf_98988993-e87/agent-ae128dac732bfe672.jsonl | 2026-10-13 06:22:57 | 68 | 1 |
| build:harness, killed (Build) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-aec8bc5310caddb1c.jsonl | 2026-10-13 06:24:40 | 50 | 1 |
| build:dissector, killed (Build) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a8e42a51fa55eeb3b.jsonl | 2026-10-13 06:24:40 | 19 | 0 |
| build:runtime (Build) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a4eac539e46c92553.jsonl | 2026-10-13 06:24:40 | 44 | 0 |
| census:vfx-bench (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a7790953f04b2aa34.jsonl | 2026-10-13 06:28:47 | 64 | 0 |
| census:first-light-present (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a711a19a82ac9ec48.jsonl | 2026-10-13 06:32:30 | 81 | 1 |
| census:methodology, killed (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-aa15ec8dfc2d2a56d.jsonl | 2026-10-13 06:32:38 | 95 | 0 |
| census:daniel-voice (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a799cc2219080ca8e.jsonl | 2026-10-13 06:33:07 | 94 | 2 |
| census:arcs (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-afb5ea9ed0e9accaf.jsonl | 2026-10-13 06:33:48 | 103 | 1 |
| research:sdf-raymarching (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a98bd8d33909f9bb7.jsonl | 2026-10-13 06:35:41 | 99 | 0 |
| research:noise-procedural (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a598372d41eaaa248.jsonl | 2026-10-13 06:36:18 | 110 | 7 |
| research:lighting-materials (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a0013bd7bffc6a46b.jsonl | 2026-10-13 06:36:32 | 94 | 3 |
| research:volumes-atmosphere (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a684ace14242616bb.jsonl | 2026-10-13 06:36:58 | 105 | 5 |
| research:water-sims-feedback (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-aceacc52cd19c5d53.jsonl | 2026-10-13 06:37:17 | 99 | 4 |
| research:pattern-fractal-2d (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a5cf6a1202f0ba3b8.jsonl | 2026-10-13 06:37:38 | 136 | 4 |
| research:color-post (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a92c526c126bc2af9.jsonl | 2026-10-13 06:37:45 | 102 | 2 |
| research:gpu-perf-glsl, killed (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a720bd002c0ac9fe1.jsonl | 2026-10-13 06:39:10 | 11 | 1 |
| research:gpu-perf-glsl (Research) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a3c8b9a8b2d2e96f5.jsonl | 2026-10-13 06:43:31 | 170 | 6 |
| build:harness (Build) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a7ccd406406cabc16.jsonl | 2026-10-13 06:43:32 | 68 | 0 |
| build:dissector (Build) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a2a4415ebcc2b1877.jsonl | 2026-10-13 06:43:35 | 194 | 5 |
| census:methodology (Census) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a0aaa76b3610caf24.jsonl | 2026-10-13 06:44:22 | 110 | 0 |
| verify:arch-visual (Verify) | wf_98988993-e87 | workflows/wf_98988993-e87/agent-acc030a1ca0dffac7.jsonl | 2026-10-13 06:47:57 | 45 | 1 |
| synthesis:atlas+architecture (Synthesis) | wf_60f63f69-3ea | workflows/wf_60f63f69-3ea/agent-a2be3b11af11ac3b7.jsonl | 2026-10-13 07:22:19 | 73 | 2 |
| integrate:round1 (Integrate) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-aad178f6464018a20.jsonl | 2026-10-13 07:51:59 | 159 | 3 |
| S0:atlas (Build) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a569f19b5e3833ccc.jsonl | 2026-10-13 08:01:08 | 73 | 1 |
| S1:composer (Build) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a7d0427d66428e92e.jsonl | 2026-10-13 08:01:08 | 64 | 1 |
| L:licence-line (Build) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a04ede0eaad0d81f7.jsonl | 2026-10-13 08:01:08 | 75 | 2 |
| S4:params (Build) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a614f7ef7dc5f9c07.jsonl | 2026-10-13 08:01:08 | 54 | 1 |
| review:S1:composer (Review) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a61c78f4201ebda2b.jsonl | 2026-10-13 08:26:09 | 35 | 0 |
| review:S0:atlas (Review) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a0ae5dd5ff10bbcd7.jsonl | 2026-10-13 08:26:09 | 71 | 1 |
| review:S4:params (Review) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a40d259641d4b3715.jsonl | 2026-10-13 08:26:09 | 43 | 0 |
| review:L:licence-line (Review) | wf_13cdd186-852 | workflows/wf_13cdd186-852/agent-a1634fbc2e91af157.jsonl | 2026-10-13 08:26:09 | 56 | 0 |
| integrate:judge1 (Integrate) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a182ce4f49eee3d0d.jsonl | 2026-10-13 08:39:09 | 1 | 0 |
| review:house-rules (Review) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a7f66fcaa76386da2.jsonl | 2026-10-13 08:39:15 | 56 | 0 |
| review:fidelity (Review) | wf_4321c88e-893 | workflows/wf_4321c88e-893/agent-a52246cff9ca5b860.jsonl | 2026-10-13 08:39:15 | 27 | 0 |
| fix:S0 (Fix) | wf_ae993e74-ec3 | workflows/wf_ae993e74-ec3/agent-ad885cc0486542adc.jsonl | 2026-10-13 08:44:58 | 65 | 0 |
| fix:S1 (Fix) | wf_ae993e74-ec3 | workflows/wf_ae993e74-ec3/agent-a0c9d23e4d21c30dd.jsonl | 2026-10-13 08:44:58 | 78 | 0 |
| fix:S4 (Fix) | wf_ae993e74-ec3 | workflows/wf_ae993e74-ec3/agent-aa74449c20034102d.jsonl | 2026-10-13 08:44:58 | 104 | 0 |
| fix:harness (Fix) | wf_760d007f-ff6 | workflows/wf_760d007f-ff6/agent-a5f2ce465df79a039.jsonl | 2026-10-13 08:53:27 | 111 | 6 |
| fix:runtime (Fix) | wf_760d007f-ff6 | workflows/wf_760d007f-ff6/agent-a65ba60ee609c2469.jsonl | 2026-10-13 08:53:27 | 170 | 4 |
| fix:dissector (Fix) | wf_760d007f-ff6 | workflows/wf_760d007f-ff6/agent-aaef1be63e47cf6fe.jsonl | 2026-10-13 08:53:27 | 93 | 1 |

"Flagged errors" counts results the tool marked `is_error`, plus shell results whose first line is a nonzero `Exit code`.
