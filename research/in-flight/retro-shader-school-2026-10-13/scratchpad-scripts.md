# Retro lane: the hand-rolled scripts in the shader-school scratchpad (2026-10-13)

Lane: every script (py, mjs, js, sh) the session wrote into its scratchpad, what each did, how often it or a
near-copy was written, whether a house verb already did it, and what should become a verb. Read-only lane;
nothing was rendered, served or committed.

## Summary

- **Size of the pile.** The scratchpad held about 23,900 files (2.0 GB) at report time. Of the bytes, 64% (1,285 MB,
  17,672 files) are 16 throwaway headless-Chrome profiles that no driver deleted. The appendix analyses **577
  scripts** the session wrote (284 at the top level and 293 in about 40 lane folders). Beyond those it lists 67
  copies of repo files or backups and 67 generated mutant copies.
  Beside them sit about **2,100 inline Python snippets** typed straight into the shell (560 quoted heredocs and
  1,533 `py -c` calls, in 161 agents, before the retro started). The scripts are the part of that work that was
  saved to a file.
- **What the scripts say about the tooling.** Most scripts are honest one-offs: probes, maths checks, review
  experiments. But nine jobs were hand-built again and again, by different agents, because no verb did them:
  1. committing only your own paths (or hunks) beside other seats' work, then checking the commit in a clean tree
     (by hand 10 times; one refused commit left 15 files staged, and a sibling seat's commit carried them);
  2. running the licence line on just this slice's files (14 or more filter scripts; 126 full-repo runs, about 56 minutes);
  3. mutation checks (46 scripts and runners, about 35 distinct harnesses; five of them edited tracked repo files
     in place);
  4. contact sheets, crops and pixel probes (22 scripts, while `py -m arsenal.media sheet` existed and went unused);
  5. corpus-wide `explain` audits (17 scripts; the verb takes one shader);
  6. rendering a named handful of cards under one GPU lock (3 wrappers; the CLI takes one name or `--all`);
  7. headless-browser receipt drivers (7 drivers, 1,201 lines, none cleaning up its profile);
  8. Python-twin against JS-twin differential fuzzing (6 or more harnesses, with copies);
  9. temporary repo mirrors and worktrees for isolated test runs (17 or more trees).
- **Three structural frictions sit under the pile.** First, the shell layer collapses `\\` inside quoted
  heredocs. That caused 29 quoting failures, and agents then wrote patch files instead (two house lessons already
  describe the bug; it still fired). Second, parallel lanes shared one flat scratchpad: four lanes wrote `px.py` in
  the same minute and one of them lost its script. Third, committed artifacts were built by scratch-only
  generators that the scratchpad's deletion will take with it: the licence baseline and the cadence fixtures.
- **What went well.** Agents used the house verbs heavily where they existed (licence-line 126 runs, card --render
  114, explain 30, dissect 19). A scratch PE-triage prototype was followed 33 minutes later by the
  `py -m arsenal re triage` verb. Scratch scripts carried their privacy rules in their own docstrings: 86 say
  read-only or in-memory, and 19 or more say they never print corpus text.

Proposed verbs, ranked by hours saved (each item below has its evidence):

| # | proposed verb (name and arguments) | replaces |
|---|---|---|
| 1 | `py agent_cli.py commit <agent> --message-file F --paths P... [--hunks PATCH] [--verify "<cmd>"] [--dry-run]` | commit_*.sh, split_hunks.py, 10 hand-built worktree checks |
| 2 | `py -m arsenal shader licence-line --paths F... \| --changed [--since REV] [--no-preview]`, `--write-baseline [--at REV] [--files F...]`, `--triage OUT.md` | 14+ slice filters, ll_make_baseline.py, ll_rebase.py, ll_triage.py |
| 3 | `py agent_cli.py mutate --file F --swap OLD NEW [--swap ...] \| --mutants M.json --test "<cmd>" [--import-hook MODULE]` | 46 mutation scripts and runners |
| 4 | `py -m arsenal.media px <png> stats\|grid\|sample X,Y...\|crop X0,Y0,X1,Y1 [--scale N] [--out F]`, `px diff A B --heat F`; `sheet` items as `label=path` | px.py, corr1_*.py, zoom.py, montage.py, sheet.py ... |
| 5 | `py -m arsenal shader explain --all [--set NAME] --snapshot OUT.json`, `explain --diff A.json B.json`; `census --tag T --sample N` | 17 audit scripts, sample_tag/list_tag/noise_recall |
| 6 | `py -m arsenal shader card NAME [NAME...] --render [--family F] [--variant LABEL:"u_a=1;u_b=2"...] [--sheet OUT.png]` | rendercards.py, render_light_cards.py, aurora-fix/render.py, variant writers |
| 7 | `node arsenal/lanes/page_receipt.mjs --url U --steps S.json --out DIR [--port N] [--keep-profile]` on a shared `arsenal/lanes/cdp.mjs` | 7 shot drivers |
| 8 | `py agent_cli.py twin-diff --py MOD:FN --js FILE.mjs:FN (--cases C.json \| --fuzz N --seed S)` | s4/diff.py + run.mjs and their copies |
| 9 | `py agent_cli.py sandbox [--at REV] [--with PATH...] -- <command>` | 17+ mirror trees, 10 worktree add/remove pairs |
| 10 | `py agent_cli.py web fetch URL --grep PATTERN [--window N]` | grab.py (bypassed the house web door, 12 runs) |
| 11 | `py agent_cli.py learn <agent> --from-json LESSONS.json` | file_lessons.py, file_lesson_index.py |
| 12 | `py -m arsenal shader atlas --gaps` | atlas_gap.py (written twice by two agents) |

## How this was measured

- **Inventory.** I listed the scratchpad's top level and every first-level folder, then listed scripts outside
  mirrored trees. These were skipped: folders holding `arsenal/` or `tests/` copies, `old/` and `new/` trees, the
  worktree, the `*-profile-*` browser profiles, `shots-*` renders, the copied third-party page scripts in `ref/`,
  and the retro's own files.
- **Write and run counts.** I streamed all 209 session transcripts (the main one plus 208 subagents, 70,996 lines),
  one line at a time. A write is a Write tool call, or a shell redirect or heredoc into the scratchpad. An edit is an
  Edit tool call. A run is a shell command naming the script. The headline counts in the findings exclude events
  after 2026-10-13 18:00 UTC unless stated, because the retro workflow began then. The appendix's W/E/R columns
  count whole transcripts, so they include the main session's late commits and a few read-only mentions by retro
  lanes.
- **Near-copies.** I compared 6-token shingles between scripts (Jaccard similarity of 0.5 or more), then checked
  the clusters by hand.
- **Existing verbs.** I parsed `agent_cli.py` (152 subcommands), `arsenal/__main__.py`, `arsenal/shaders/cli.py`
  with its registered extensions, `arsenal/media/__main__.py` and `arsenal/re/cli.py`.
- **Citation form.** `main:N` is line N of `~/.claude/projects/E--/9d62784c-bd34-488c-a370-94b7d333fbb9.jsonl`.
  `agent XXXXXXXXXX:N` is line N of the subagent transcript whose id starts with those ten characters, under that
  session's `subagents/` folder. Times are UTC unless marked local (-04:00).

## Findings

### 1. Committing only your own paths, then checking the commit in a clean tree, was hand-built 10 times (no verb)

- **What was built:**
  - `commit_paths.sh`: builds the commit in a temporary index from HEAD holding only the named paths, then resets
    the real index for every path in the commit, hook-regenerated docs included. Written at main:5433 (18:00), run
    4 times.
  - `commit_stage2a.sh` (main:3804, 11:35), `commit_fixes.sh` (main:4521, 14:05) and `commit_batchb.sh` (main:4875,
    15:58): each redefines the same helper, `C() { git add -- "$@"; git commit -q -m "$msg" -- "$@"; }`.
  - `split_hunks.py` (main:3063): splits a file's diff into "mine" and "sibling" hunks so that only your own hunks go
    to `git apply --cached`.
  - A temp-index commit done inline at main:3096.
  - A detached-worktree check (`git worktree add --detach`, run tests, `git worktree remove --force`) done 10 times
    by hand: main:3102, 3429, 3928, 4586, 4875, 5508, 5641, 5762, 5819, 5887.
  - 9 commit-message files in the scratchpad (`msg_*.txt`, `lean_green_msg.txt`).
- **Cost:** the plain `git add + git commit -- paths` helper in `commit_batchb.sh` was refused by the pre-commit
  hook, which left 15 files staged in the shared index. Commit `1d96275d` (2026-10-13 12:00 local, a seat-identity
  slice, T088(a)) carried all 15 shader-school files (6 `tests/test_glsl_twins_*`, `tests/test_glsl_atlas.py`, 8
  `tests/fixtures/glsl_cards/*`) under its own message. `git show --stat 1d96275d` shows them. The session's own
  lesson text (`file_lesson_index.py`, filed at main:5718) records that HEAD then "sat red for six hours" and that
  the history misattributes those files.
- **Existing verb:** none. `agent_cli.py` has no commit verb. `scripts/mirror.py` commits and pushes everything,
  which is the opposite of what was needed.
- **Proposed verb:** `py agent_cli.py commit <agent> --message-file F --paths P... [--hunks PATCH] [--verify
  "<cmd>"] [--dry-run]`. It would build the commit in a temp index from HEAD (using `git apply --cached` for
  `--hunks`), commit, and reset the real index for every path `git diff-tree --name-only -r HEAD` lists. With
  `--verify`, it would run the command in a detached worktree and always remove it. If the hook refuses, it leaves
  nothing staged and prints the hook's reason.

### 2. Running the licence line on "only my files" was re-derived in 14 or more scripts; the full scan ran 126 times

- **Filter scripts:** `myscan.py` (run 10 times), `myll.py`, `ll_mine.py` (two agents), `licence_mine.py`,
  `batchb_fix/licence_mine.py`, `rereview_b/licence_mine.py`, `rr_lic.py`, `rr_ll_filter.py`,
  `rereview/licence_filter.py`, `lowfix/lic_files.py`, `lowfix/lic_filter.py`, `s1fix2/licence_scan.py`,
  `triage/check_files.py`, `ll_windows.py`.
- **How the full report was used:** each filter either imports `licence_line.build_index` and `scan_texts` with a
  hard-coded file list, or saves a full `--json` report and filters it. `licence-line --json > file` appears in 70
  shell commands, and about 38 saved reports sit in the scratchpad (`licence*.json`, `ll*.json`, `rr_licence.json`,
  `scan*.json`, plus one per lane folder).
- **Report schema re-guessed every time:** `rereview/licence_filter.py` tries `h.get('path') or h.get('file')`.
  `rr_lic.py` and `licence_mine.py` print `top keys:` to discover the layout first.
- **Cost:** 126 synchronous full-repo runs (median 35 s, maximum 56 s, about 56 minutes of wall time). A slice scan
  through the module took a median of 4 s (27 runs).
- **Existing verb:** `py -m arsenal shader licence-line` takes only `--root`, `--corpus`, `--allow` and `--baseline`
  (licence_line.py:1029-1034). It has no file filter and no way to drop previews.
- **Proposed flags:** `licence-line --paths F... | --changed [--since REV] [--no-preview]`, plus a documented JSON
  schema in its `--help`.

### 3. Committed artifacts were built by generators that live only in the scratchpad

- **Licence baseline:** `ll_make_baseline.py` (agent 264b1a8dbb, 09:11) built the tracked
  `arsenal/shaders/licence_line_baseline.json`. `ll_rebase.py --write` (agent ae973e64b1) later rewrote entries in
  it. `ll_triage.py` wrote `state/arsenal/shaders/licence-line-triage.md`. `licence_line.py` has `load_baseline` and
  `apply_baseline` but no writer.
- **Cadence fixtures:** the tracked `tests/fixtures/cadence_cases.json` was generated by `gen_cadence_fixtures.py`
  (line 160 writes it), then appended to by `add_fixtures.py` and by `gen_fixtures.py`. Those are three scripts from
  three agents (a8e3c2fe, a44519cf, ae14080618). No generator for that file exists in the repo.
- **Other state and repo text:** `set_texts.py` (16.8 KB) wrote card notes and recipe contracts.
  `s4fix/pin_fixture.py` inserted cases into the params fixture. `s1fix2/rewrite_fixtures.py` rewrote fixtures in
  `tests/test_glsl_modules.py`. `sheets.py`, `aurora-fix/sheets_build.py` and `fringe-fix/contact_sheets.py` wrote
  `state/.../groups/<name>/sheet.png`.
- **Cost:** when the session's temp folder is cleaned, nobody can regenerate or extend these files the same way.
  The next agent will re-derive the generator (the cadence fixture already took three).
- **Fix:** `licence-line --write-baseline [--at REV] [--files F...]` and `licence-line --triage OUT.md`. Move
  fixture generators beside their fixture (for example `tests/fixtures/gen_cadence_cases.py`). Make it a process
  rule: a script that writes a tracked file is committed with it.

### 4. Mutation checks: 46 scripts and runners (about 35 distinct harnesses), five of which edited tracked files in place

- **The harnesses, by kind:**
  - pytest plugins that patch in memory: `mutants.py`, `mut_core.py`, `mut_tags.py`, `rr3_intermediate.py`,
    `rr4_mut_plugin.py`, `rr4L/mutplug.py`; `pytest -p <plugin>` was used 10 times;
  - in-process monkeypatch runners: `probe_mut.py`, `rrL/p_mut.py`, `p_mut2.py`, `p_mut3.py`, `rr/mutate_pins.py`,
    `rr2/mutate.py`;
  - scratch-copy runners: `s1fix2/mutate.py`, `s1rr2/mutate_js.py`, `mutate_py.py`, `mutate_py2.py`,
    `mut_runner.py`, `pinfirst_runner.py`, `rr/mut/mutate.py`, `batchb_fix/mutant_light_probe.py`,
    `mutant_rays_probe.py` (copied again into `rereview_b/`), `fringe-fix/oldlib.py`, `rr3/py_revert.py`,
    `py_revert2.py`, `s0_revert.py`;
  - piano-judge sweeps: `mutate.mjs`, which generated 47 `mutant_N.mjs`; `mutants.mjs`, which generated 13
    `mN.mjs`; 7 `rev_faith/m_*.mjs`; and `verify/sweep.mjs` with `verify/mutants.mjs` ("82 mutants").
- **In place, on tracked files:** `mutate_stage.py`, `mutate_stage2.py`, `mutate_stage3.py` and `mutate_stage4.py`
  write each mutant straight into `E:/AI-Setup/arsenal/web/lib/workbench/stage.js` and restore it in a `finally`
  (mutate_stage.py:25 and :31). `s1fix/mutate.py` does the same to `arsenal/web/glsl/modlib.js` (lines 18 and 23).
  In a repo where other seats commit and run tests at the same moment, a sibling could commit or test a mutant, and
  a killed process would leave one behind.
- **Cost:** three different harnesses were written at the same path `mutate.py` by three agents (agent a04ede0eaa
  at 08:18, af4b397886 at 09:26, af450251ba at 11:59); the last one won and two are lost.
- **Prior knowledge:**
  - the house lesson `a_mutation_that_never_applied_reports_as_a_surviving_one` already says a harness must prove
    each mutation landed;
  - `docs/method-baseline-2026-07.md:305` names the practice as "mutation-testing-the-guards".
- **Existing verb:** none (repo search for MUTANT/mutmut finds only `core/toolbelt/clobber_scan.py`).
- **Proposed verb:** `py agent_cli.py mutate --file F (--swap OLD NEW ... | --mutants M.json) --test "<cmd>"
  [--import-hook MODULE] [--expect red]`. It would never write the tracked file: it would use a temp overlay, a
  `sys.modules` swap for Python, or a loader for Node. It would assert that each swap applied exactly once and still
  parses, then print killed or survived for each mutant.

### 5. Inline Python through the shell broke often, and broke in a way the house already knew about

- **Volume:** 560 quoted heredocs, 1,533 `py -c` calls and 28 `node -e` calls in 161 agents (before 18:00).
- **Quoting failures:** 29 tool results show `unterminated string literal` or `unexpected EOF while looking for
  matching`. 15 of them came from heredocs, 8 of those containing a double backslash, and 15 from `py -c`.
- **The cause, reproduced in this lane:** the shell layer turns `\\` into `\` even inside a quoted heredoc.
  `cat <<'EOF'` with `a\\b` prints `a\b`. It broke two of my own read-only probes, a `.replace('\\','/')` and a
  regex character class.
- **Prior knowledge:** two lessons already state this (`bash_heredoc_mangles_backslashes_in_python_patches`,
  `bash_heredocs_corrupt_regex_backslash_b_to_backspace`). The main session met it anyway: main:4644 failed with an
  unterminated literal. Its next message (main:4650) says the tool layer had collapsed its escaped backslashes, and
  it moved to a Write'd `file_lessons.py`.
- **The push toward scratch files:** agent ae69fc909d:597 wrote "The shell choked on quoting in the long heredoc.
  I'll put the patch script in a file instead." and then wrote `patch_cards.py`. Agent ad060ac808:627 switched to
  the Edit tool "(no heredoc escapes this time)".
- **Two more recurring errors:** 19 tool results with the Windows console `'charmap' codec can't encode` (18
  agents; for example main:3263 and agent a40d259641:99). And 7 with `No module named 'arsenal'` (7 agents; for
  example agent a4fc73a8b2:290): scratch scripts run from outside the repo.
- **Boilerplate copied into the scripts:** 22 scripts hard-code `sys.path.insert(0, r"E:\AI-Setup")` and 92
  hard-code this session's absolute scratchpad path.
- **Repo edits through the shell:** 156 shell commands edited repo files with read, replace and write in Python (33
  agents). 22 heredocs re-derived the same `def rep(old, new): assert s.count(old) == 1` helper, and `sub.py` turned
  it into an edits.json applier (run 9 times).
- **Fix:**
  - **Config:** set `PYTHONIOENCODING=utf-8` (and `PYTHONPATH=E:\AI-Setup`) in the harness environment for every
    seat.
  - **Hook:** a Bash PreToolUse hint when a command holds `<<` together with `\\`, pointing at Write plus a file, or
    `chr(92)`.
  - **Doc:** one line in AGENTS.md: patches go through the Edit tool; when a script is unavoidable, Write it to a
    file first.

### 6. Contact sheets, crops and pixel probes were hand-built 22 times while the house sheet verb went unused

- **Sheets and montages:** `montage.py` (run 17 times), `sheet.py` (written by three agents: a65ba60ee6 at 09:11,
  aadbce3a55 at 11:18, a3084eb892 at 13:29), `sheets.py`, `contact_light.py`, `loved_sheet.py`, `aurora-fix/strip.py`,
  `aurora-fix/sheets_build.py`, `fringe-fix/contact_sheets.py` (a near-copy of the previous one) and
  `fringe-fix/grids.py`.
- **Crops:** `zoom.py` (run 23 times), `fringe-fix/zoom.py`, `aurora-fix/scrop.py`, `batchb_fix/card_diff.py` (heat
  image of two renders).
- **Pixel probes:** `px.py` (run 15 times), `corr1_px.py` (run 42 times), `corr1_bbox.py`, `corr1_frac.py`,
  `corr1_heat.py`, `corr1_rowmax.py`, `corr1_sun.py`, `corr2/px2.py`, `corrob5/probe.py`.
- **Existing verb:** `py -m arsenal.media sheet <images...> --cols --cell-w --zoom x,y,w,h --title --out` has existed
  since commit 3f55e119 (2026-10-12 04:54 local). It was called 0 times in the session before the retro. Its CLI
  does not take a per-item label (the Python API does, through `{src, label}` items), and nothing in the house reads
  pixels.
- **Proposed:** let `py -m arsenal.media sheet` take items as `label=path`. Add `py -m arsenal.media px <png>
  stats|grid|sample X,Y...|crop X0,Y0,X1,Y1 [--scale N] [--out F]` and `px diff A.png B.png [--heat F]`. Add the
  sheet verb to the shader-craft skill's tool list, because the agents never found it.

### 7. Parallel lanes clobbered each other's scratch files in one flat folder

- **What happened:** four corroboration lanes each wrote their own `px.py` to the scratchpad's top level in the
  same minute (14:09 UTC; agents a3b9e2b147:57, a4e374169c:45, ac0c55292d:58, ad068b3b0a:53). In agent ac0c55292d:
  - line 60: its Write reported "has been updated", not "created";
  - line 65: running it failed with `can't open file ... px.py [Errno 2]`;
  - line 77: the file then held another lane's code;
  - line 80: it re-made the tool as `corr2/px2.py` ("private to this lane").
- **The others adjusted too:** agent a4e374169c moved to `corr1_px.py` ("own copy").
- **The same pattern elsewhere:** `mutate.py` (3 agents, two harnesses lost), `sheet.py` (3 agents), `ll_mine.py`,
  `ll_prof.py`, `parity_stats.py` and `rr_probe.mjs` (2 agents each).
- **Cost:** about 6 wasted tool calls in one lane; lost harnesses; and a real risk of judging with another lane's
  probe.
- **Fix (brief template):** every fan-out brief names a per-lane folder (`<scratchpad>/<lane>/`), and agents write
  only there. Optionally add `py agent_cli.py scratch <lane>`, which prints and creates the folder.

### 8. Corpus-wide explain and dissect audits were re-derived 17 or more times (the verbs take one shader)

- **Explain audits:** `explain_corpus_counts.py`, `explain_live_audit.py`, `verify_explain.py`,
  `rereview_observed_audit.py` and `rereview_observed_audit2.py`, `rereview_hand_sample.py`,
  `rr2_declared_check.py`, `rr2_common_check.py`, `rr2_common_live.py`, `rr2_alias_scope.py`,
  `rr2_determinism.py`, `rr3_snapshot.py` with `rr3_diff.py` (diffing two snapshots), `rr3_noread_check.py` and
  `rr3_noread_check2.py`, `rr3_alias_check.py`, `rr4_audit.py`, `rr4_param_check.py`. Each loops over `C.all_ids()`
  and builds every ledger in memory, written by seven different review and fix agents.
- **Dissect sweeps:** `smoke_dissect.py` (run 8 times), `smoke_glsl.py`, `noise_recall.py`, `list_tag.py`,
  `sample_tag.py`, `order_census.py`, `scan2.py`, `scan_color.py`.
- **Existing verbs:** `py -m arsenal shader explain <target> [--detail] [--min-conf]` (explain.py:1288) and
  `dissect` take one shader. `census` takes `--set` and `--limit` but has no tag sampling.
- **Proposed:** `explain --all [--set NAME] --snapshot OUT.json`, `explain --diff A.json B.json`, and `census --tag
  TAG --sample N`, which prints the evidence line each sample points at, without corpus text by default.

### 9. Rendering a named handful of cards, and look-tuning variants, were wrapped by hand

- **Named card sets:** `rendercards.py` (run 8 times) and `render_light_cards.py` (run 7 times) call
  `cards.render_cards(names)`, which takes a list (cards.py:545). The CLI exposes only `name` with `nargs="?"` or
  `--all` (cards.py:564-565). `aurora-fix/render.py` (run 4 times) is a third wrapper.
- **Look-tuning loops:** these write variant cards with constants overridden, render them, measure them, and lay
  them on a labelled sheet. `aurora-fix/` holds 22 scripts, `fringe-fix/` 29 (one agent, 27 writes and 41
  heredocs), `rr2/` 5, `tri/` 6, plus `rr/make_variants.py`. Near-copies: `fringe-fix/variants.py` with
  `rr2/render_variants.py`, `aurora-fix/variants.py` with `svariants.py`, and `aurora-fix/sheets_build.py` with
  `fringe-fix/contact_sheets.py`.
- **Whole-shelf renders:** `shelf_renders.py` looped `render` and `filmstrip` over the Loved set with a 12 s gap,
  because `render` has no `--set`.
- **Proposed:** `py -m arsenal shader card NAME [NAME...] --render [--family F] [--variant LABEL:"u_a=1;u_b=2"]...
  [--sheet OUT.png]`, and `py -m arsenal shader render --set NAME [--gap S]`.

### 10. Seven headless-browser receipt drivers re-implemented the same plumbing and left 1.3 GB of profiles behind

- **The drivers:** `lean_shots.mjs`, `rev_ab_shots.mjs`, `w5/lean_shots.mjs`, `v6/v6_shots.mjs`, `w6/w6_shots.mjs`
  (four of them form one near-copy cluster), `x7/x7_shots.mjs` and `verify_w5b/vrun.mjs`: 1,201 lines in all. Each
  spawns Chrome with a new profile, connects over DevTools, takes the GPU lock, runs a watchdog and captures console
  output and exceptions. `flag_probe.mjs`, `corpus_smoke.mjs` and `edge_paths.py` do part of the same.
- **The leftovers:** none of the seven calls `rmSync` on its profile. 16 profile folders remain: 17,672 files and
  1,285 MB, which is 64% of the scratchpad. The house lane `arsenal/lanes/chrome_verify.mjs` does remove its profile
  (line 271), but its launch-and-connect code is not a library the scratch drivers could import.
- **Proposed:** extract `arsenal/lanes/cdp.mjs` (launch with a throwaway profile that is always removed, connect,
  evaluate, screenshot, console capture, watchdog, GPU lock). Add `node arsenal/lanes/page_receipt.mjs --url U
  --steps S.json --out DIR [--port N] [--keep-profile]`.

### 11. Repo mirrors and worktrees for isolated runs: 17 or more trees, copied by hand

- **The trees:** `rereview/` (`old/` and `new/`), `rr/`, `rr3/`, `rr_mirror/`, `s1fix2/`, `s1rr2/`, `ll/`, `ll-root/`,
  `llscan/`, `llroot/`, `verify/`, `viewonly-mirror2/`, `cache_real_*`, `deadread_*`, `madeof_*`, 11 `tmp*` folders,
  the backups `labsafety-backup/` and `viewonly-backup/`, and the worktree `wt_batchb` (5,202 files and 124 MB at
  inventory time; gone at report time).
- **How they were made:** copy commands (`copytree`, `cp -r`, `Copy-Item -Recurse`) appear about 9 times in 8 or
  more agents, and `git worktree add` 10 times. `git worktree list` currently shows 63 registered worktrees for the
  repo, many under `%TEMP%`; not all are from this session.
- **Proposed:** `py agent_cli.py sandbox [--at REV] [--with PATH...] -- <command>`. It would make a detached worktree
  at REV, overlay the named working-tree files, run the command, and always remove the worktree.

### 12. Python-twin against JS-twin differential fuzzing was built at least 6 times

- **The harnesses:**
  - `s4/diff.py`, `edge.py` and `fuzz.py` with `s4/run.mjs` (the param-schema twins), copied whole into `s4r/h/` and
    again into `rr3/` (`rr3/run_mine.py` does `shutil.copy(H + "/run.mjs", ...)`);
  - `s1review/twin.py` with `twin.mjs`, and `s1rr2/twin2.py` with `twin2.mjs` (the GLSL module twins);
  - `fuzz_gen.py` with `fuzz_check.mjs`, `rev_faith/gen.py`, `gen2.py` with `check.mjs`, and `verify/harness.mjs`
    (the cadence judge twins);
  - `lowfix/tiny_diff.py` with `tiny_run.mjs`.
- **What each rebuilt:** each re-invents the NaN, Infinity and minus-zero sentinel table (`SENT = {"__NaN__": ...}`
  in s4/diff.py and s4/run.mjs).
- **Existing verb:** none (the repo search for a differential runner finds only store tests).
- **Proposed:** `py agent_cli.py twin-diff --py MOD:FN --js FILE.mjs:FN (--cases C.json | --fuzz N --seed S)`, with the
  sentinel encoding built in. It would report the first divergence and its case.

### 13. Review probes were copied from round to round instead of becoming pins

- **Copies:**
  - `rrL/` became `rr4L/`: 10 probe pairs at Jaccard 0.5 or more (`p_edges`, `p_edges2`, `p_fuzz`, `p_mdsnip`,
    `p_oneline`, `p_r3check`, `p_state`, `p_stray`, `p_swallow`, `p_swap`);
  - `s1rr/` became `s1rr2/` (agent a9616f0195:35, `cp ../s1rr/probe2.py ../s1rr/probe4.py .`);
  - `s4/` became `s4r/h/` and then `rr3/`;
  - `rr_probe.mjs` was followed by `rr_probe2.mjs` through `rr_probe5.mjs` (one cluster) and copies under
    `viewonly-backup/probes/`;
  - the `batchb_fix/` mutant probes were copied to `rereview_b/`.
- **Cost:** a probe that is worth re-running in the next round is a regression test that lives in a temp folder.
- **Fix (process):** when a reviewer re-runs a previous round's probe, it is promoted to a pin under `tests/`
  (synthetic text only), and the brief for the next round names the pin instead of the scratch path.

### 14. Mining operator turns from transcripts was hand-built (11 scripts) beside the house transcript door

- **The scripts:** the census lane (agent a799cc2219, 06:33-06:40) wrote `extract_human.py`, `extract_human2.py`,
  `extract_queued.py`, `extract_discord.py`, `search.py`, `search2.py`, `search_q.py`, `search_d.py`, `dump.py`,
  `imgturns.py` and `prose.py`. It used `agent_cli.py eye` twice.
- **Recurrence:** the retro lanes running now re-derive the same extraction again (`extract.py`, `an*.py`,
  `retro-lane-main/*`, outside this count).
- **Existing verb:** `py agent_cli.py eye find --who operator --kind queue-operation --session S` and `eye get`
  (agent_cli.py:10103-10128).
- **Gap:** the scripts also pulled operator bus and Discord lines out of tool results, and wrote a JSONL dump for
  later passes.
- **Proposed:** check whether `eye find` covers bus-relayed operator text. If not, add `eye find --who operator
  --origin typed|queued|bus --dump jsonl`, and name the eye in fan-out briefs that mine transcripts.

### 15. Quote verification bypassed the house web door

- **The script:** `grab.py` (agent ad2827ea2c, run 12 times) fetches with `urllib` directly, strips tags and prints
  windows around regex matches, "to verify quotes against raw source text". `urlcheck.py` in another lane did go
  through `agent_cli.py web fetch` (4 calls).
- **Existing verb:** `py agent_cli.py web fetch URL [--raw] [--pdf-full] [--offset] [--limit]` (agent_cli.py:8737). It
  has no match window.
- **Proposed:** `py agent_cli.py web fetch URL --grep PATTERN [--window N]`, so verification keeps the door's cache and
  receipt.

### 16. Filing lessons needed a script because `learn` takes no file input

- **The scripts:** `file_lessons.py` (3 lessons, main:4651) was written after the heredoc version failed (main:4644
  and 4645). `file_lesson_index.py` (main:5718) followed. Elsewhere, 9 direct `learn` calls came from 8 agents.
- **Existing verb:** `py agent_cli.py learn` has only flag arguments, while `wish` already has `--text-file` "for
  flag-bearing prose".
- **Proposed:** `py agent_cli.py learn <agent> --from-json LESSONS.json` (a list of
  `{experiment, tried, result, recommend, category, success}`), or `--tried-file`, `--result-file` and
  `--recommend-file`.

### 17. Bus, store and identity read-only probes in the deconstruct teardown (14 scripts, 45 inline Redis calls)

- **The scripts:**
  - agent a28471838e, card doors-and-trust: `probe_trust.py`, `probe_trace.py`, `probe_trace2.py`,
    `probe_trace3.py`, `probe_locks.py`, `probe_senders.py`, `probe_authors.py` and `probe_kimi.py`, written within
    5 minutes;
  - card knowledge-planes: `atoms_vs_proj.py`, `atoms2.py`, `status_drift.py`, `store_only.py`;
  - `fleet_identity_probe.py`, `teardown_probe.py` and `house/h13_probe.py`.
- **Inline access:** 45 shell commands opened `redis.Redis(...)` directly. One used the house `trace` verb, 3 used
  `events` and 12 used `locks`.
- **Existing verbs:** `trace`, `events`, `locks`, `mailbox`, `roster`, `doctor` and `stats`.
- **Gaps:** read-only XREVRANGE by sender over inbox and broadcast streams, searching the trace ring for a
  double-fire signature, and lessons tallied by author against the ACL.
- **Proposed:** `py agent_cli.py bus peek STREAM --last N [--by-sender]` and `stats --lessons-by-author`. This is
  lower priority: a teardown is a one-off by nature.

### 18. Atlas and library consistency checks: 18 small scripts, some written twice

- **The scripts:** `atlas_gap.py` (agent a720e8db21 at 13:46) and `batchb_fix/atlas_gap.py` (agent a4fc73a8b2 at
  14:09) are two agents' versions of the same question 23 minutes apart. The rest: `atlas_parts.py`,
  `batchb_fix/atlas_peek.py`, `batchb_fix/sig_diff.py`, `batchb_fix/recipe_defs.py`, `rereview_b/sig_names.py`,
  `batchA_status.py`, `hdr.py`, `cardhdr.py`, `sig.py`, `sigtypes.py`, `twincov.py`, `choice_units.py`, `names.py`,
  `names2.py`, `s0fix/probe_types.py` and `probe_types2.py`.
- **Existing verbs:** `py -m arsenal shader lib lint` and `atlas [--family] [--category] [--status] [--built]
  [--groups] [--ledger] [--tags] [--rulings]`.
- **Gap:** planned-versus-built with the defining file, and signature mismatches.
- **Proposed:** `py -m arsenal shader atlas --gaps`.

### 19. Smaller frictions

- **A scratch dependency on another session's temp folder.** `content/piano-timing/isolated.py` and `jumps.py` read
  their input from `...\E--\2242a56c-...\scratchpad\content\...`, another session's scratchpad. Fix (process): data
  a later session needs belongs under `state/`.
- **Harness questions answered by grepping the CLI package.** `cli_grep.py` and `cli_re.py` (agent a0034023d0, run
  4 and 9 times) searched the installed Claude Code package to learn how a subagent's environment is set. Fix (doc):
  write the answer once into the house notes on seat identity.
- **Generic exact-replacement applier.** `sub.py` ("apply exact string replacements [[path, old, new], ...]",
  agent a3084eb892, run 9 times, fed by `e1.json` to `e9.json`) shows the Edit tool was not used for edit sets
  computed as data. No verb is needed; it belongs under item 5's doc line.
- **A one-off line-ending check.** `eol.py` checked and fixed CRLF in one slice's 18 files. No house check
  enforces LF on new GLSL files (test_glsl_index.py only tolerates CRLF checkouts). Keep it as a one-off unless
  CRLF recurs.
- **A workflow script in the scratchpad.** `wf_fix_round_next.js` (main:5743) is a fix-then-re-review round
  written as a workflow script. The session ran 22 workflows in all (the session's `workflows/` folder), many of
  them rounds of that shape. That is out of this lane, so I flag it only for the workflow lane.

### 20. What went well

- **Scratch prototype, then verb.** `triage_pe.py` (agent ad2827ea2c, 13:08 UTC, a read-only first look at a PE file)
  was followed by `py -m arsenal re triage` (commit 47ebdec0, 09:41 local = 13:41 UTC). It took 33 minutes for a
  scratch question to become a house door.
- **House verbs got reached for when they existed.** `licence-line` ran 126 times, `card --render` 114, `explain`
  30, `dissect` 19, and `render`, `check` and `filmstrip` 50 together.
- **Privacy discipline lived in the scripts.** 86 scratch scripts declare themselves read-only or in-memory, and
  19 or more promise never to print corpus text (for example `rr_ll_filter.py`, `lowfix/lic_filter.py`,
  `probe_fn.py`).
- **Pin-first mutation was a reflex.** Nearly every fix and re-review lane tried to watch its pins fail before
  trusting them (item 4). The practice is right; only the tooling is missing.

## Coverage

- **Read:** the scratchpad's top-level listing and every first-level folder, with file counts and sizes; every script
  outside mirrored trees (heads and docstrings for all of them; full text for the commit, lesson-filing, licence,
  mutation, sheet and pixel, headless and generator scripts); all 209 session transcripts, streamed line by line
  (no single process went past a few hundred MB); `agent_cli.py`'s parser; the arsenal CLIs listed above;
  `licence_line.py`, `cards.py`, `explain.py`, `modules.py` and `media/sheet.py` around their CLI registration;
  `docs/method-baseline-2026-07.md` around mutation; and read-only git (`git log`, `git show --stat 1d96275d`,
  `git worktree list`).
- **Skipped, and why:**
  - mirrored repo copies (folders holding `arsenal/` or `tests/`, `old/` and `new/` trees, the worktree), because
    they are copies of tracked code;
  - the 16 browser-profile folders (private browser session data; only their sizes were measured);
  - `shots-*` and `*-shots-*` folders and all images (renders, not scripts);
  - `ref/*.js`, saved third-party page scripts (corpus-adjacent; not opened);
  - `x7/piano_now.js` and `piano_pre_decision.js`, `labgpu/stage*.js`, `labsafety-backup/` and `viewonly-backup/`,
    which are copies of repo files (listed, not analysed);
  - the 70 generated mutant copies (counted, not read);
  - the retro workflow's own files (`an*.py`, `extract.py`, `list.py`, `peek*.py`, `probe_err.py`, `today_*.py`,
    `retro*/`), which are this retro, not the session.
- **Counting limits:**
  - a script written with `cp`, by another script, or through a shell variable my patterns missed shows "no write
    seen" (71 appendix rows, mostly copies between review rounds);
  - the retro lanes were writing into the same scratchpad while this ran. Fifteen of their files that appeared
    mid-run were removed from the appendix by hand. One retro lane wrote `scan.py` at 18:12 over the session's own
    `scan.py` (a corpus idiom scan from 02:37 local), which is now gone, so item 7's clobbering happened again
    during the retro;
  - run counts include any shell command that names the script, so a command that runs it twice counts once;
  - the wall-time figures pair each tool call with its result and include anything else chained in that command.
- **Unknown:** whether a mutant written in place ever reached a sibling's test or commit (no evidence either way);
  how many of the 29 quoting failures were retried successfully by heredoc rather than by file; and whether the PE
  triage verb was built from the scratch prototype or only alongside it.
- **Hygiene:** no corpus code, shader ids, authors, browser data or secrets are quoted here. Reverse-engineering
  topics are named, not explained.

## Appendix: every script, one line each

How to read the appendix:

- **W/E/R** means writes, edits and runs, from the transcripts.
- **First write** is the first write event (transcript:line, UTC time).
- **Verb status:**
  - **EXISTS** means a house verb already did this;
  - **PARTLY** means one covers part of it;
  - **NEW** names the proposal from the findings above;
  - **scratch** means a legitimate one-off;
  - **move** means it belongs in the repo.

### Commit and lesson filing (7)

Verb status: NEW: `agent_cli.py commit` (item 1); `learn --from-json` (item 16)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `commit_batchb.sh` | RED and GREEN commits for batch B plus a detached-worktree test run; its refused RED commit left 15 files staged. | 1/0/1 | main:4875 @15:58 | 1 |
| `commit_fixes.sh` | Batch of path-limited commits for the fix round, via the same C() helper. | 1/0/1 | main:4521 @14:05 | 1 |
| `commit_paths.sh` | Commit only the named paths through a temporary index from HEAD, then reset the real index for every committed path. | 1/1/7 | main:5433 @18:00 | 1 |
| `commit_stage2a.sh` | Batch of path-limited commits (git add + commit -- paths) for stage 2a, via a redefined C() helper. | 1/0/0 | main:3804 @11:35 | 1 |
| `file_lesson_index.py` | Filed the temp-index commit lesson through `agent_cli.py learn` from Python (avoids shell quoting). | 1/0/3 | main:5718 @18:11 | 1 |
| `file_lessons.py` | Filed three lessons through `agent_cli.py learn` from Python after the heredoc version failed. | 1/0/1 | main:4651 @14:43 | 1 |
| `split_hunks.py` | Split a file's diff into own and sibling hunks and wrote an own-hunks-only patch for git apply --cached. | 1/0/0 | main:3063 @06:57 | 1 |

### Generators of tracked or state artifacts (16)

Verb status: move into the repo; `licence-line --write-baseline` / `--triage` (item 3)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `add_fixtures.py` | Appended invented fixtures to the tracked cadence fixture file, to pin decisions mutation found unpinned. | 1/0/3 | agent a44519cf9f:145 @03:38 | 1 |
| `aurora-fix/rename_uniforms.py` | Scratch: ruling (b), rename every group recipe's uniforms to u_<recipeCamel>_<param> in the recipe and its card. | 1/0/1 | agent afaf271492:186 @14:14 | 1 |
| `aurora-fix/sheets_build.py` | Scratch: the aurora groups' labelled contact sheets, state/arsenal/shaders/groups/<name>/sheet.png (after the look | 1/0/2 | agent afaf271492:1054 @15:21 | 1 |
| `fringe-fix/contact_sheets.py` | Scratch: the aurora groups' labelled contact sheets, state/arsenal/shaders/groups/<name>/sheet.png, after the | 1/0/0 | agent a1c66d0ec0:875 @17:28 | 1 |
| `gen_cadence_fixtures.py` | Generated the tracked tests/fixtures/cadence_cases.json from invented progressions. | 1/1/1 | agent a8e3c2fe3d:49 @03:27 | 1 |
| `gen_fixtures.py` | Built more invented cadence fixtures, confirmed each with the Python judge, and appended them. | 1/1/2 | agent ae14080618:53 @03:47 | 1 |
| `integ/tests_append.mjs` | Test cases appended to a workbench test during integration. | 1/0/1 | agent aad178f646:383 @08:12 | 1 |
| `labgpu/ladder_patch.py` | Scripted patch of the workbench stage's scale ladder. | 1/0/1 | agent a2688a47ec:630 @12:20 | 1 |
| `ll_make_baseline.py` | Built the tracked arsenal/shaders/licence_line_baseline.json. | 1/0/1 | agent acda0f5264:236 @09:11 | 1 |
| `ll_rebase.py` | Re-measured baseline entries at the baseline commit; --write rewrote them in the tracked baseline. | 1/0/2 | agent a5159d6ae9:312 @10:17 | 1 |
| `ll_triage.py` | Wrote state/arsenal/shaders/licence-line-triage.md (private; one row per baselined file). | 1/0/1 | agent acda0f5264:374 @09:32 | 1 |
| `morning/build_assets.py` | Collected the night's pictures into compact JPEGs for the morning page. | 1/0/1 | main:3949 @11:44 | 1 |
| `s1fix2/rewrite_fixtures.py` | Rewrite the fixture bodies in tests/test_glsl_modules.py that the licence-line gate flags (ubiquitous GLSL idioms a | 1/0/1 | agent a26dea594b:430 @10:26 | 1 |
| `s4fix/pin_fixture.py` | Inserted the review's pin cases into the shared param-schema fixture at anchored points (each anchor required once). | 1/0/1 | agent aa74449c20:80 @08:53 | 1 |
| `set_texts.py` | Wrote the final contract and note of each g1 recipe and each card's note into the repo. | 1/0/2 | agent abadb13dbf:691 @13:31 | 1 |
| `sheets.py` | Built one labelled contact sheet per g1 recipe under state/arsenal/shaders/groups/. | 1/0/3 | agent abadb13dbf:711 @13:32 | 1 |

### Licence line on this slice only (20)

Verb status: NEW flag: `licence-line --paths` (item 2)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `batchb_fix/licence_mine.py` | Run the licence line over the repository and print every finding in the files this fix touched. | 1/0/2 | agent a4fc73a8b2:684 @14:35 | 1 |
| `classify.py` | Scratch classifier for the licence-line report: reads house files only (never prints corpus text). | 2/1/2 | agent a04ede0eaa:231 @08:16 | 1 |
| `final.py` | Final snapshot: every hit, grouped by file, with context kind and measured shape. House-side reads only. | 1/0/2 | agent a04ede0eaa:333 @08:19 | 1 |
| `licence_mine.py` | Filtered a saved licence report to the lab-safety files. | 1/0/4 | agent ade2258a6c:301 @14:40 | 1 |
| `ll_list.py` | Scratch: text-free list of the non-baselined breaches in a saved report, with each file's age against 9d6f29ff. | 1/0/2 | agent a5159d6ae9:458 @10:37 | 1 |
| `ll_mine.py` | Scanned only this slice's files against the corpus shingles (file, line, tokens, shape, exempt). | 2/0/6 | agent a298346af0:346 @10:18 | 2 |
| `ll_summary.py` | Scratch: run the real licence-line scan in-process, save the report, print a text-free summary. | 1/0/6 | agent a5159d6ae9:40 @10:03 | 1 |
| `ll_windows.py` | Printed each 12-token window two named files share with the corpus (it prints the matched tokens, which are corpus text; the other filters do not). | 1/0/1 | agent a35553e7dc:505 @10:58 | 1 |
| `lowfix/lic_files.py` | Scan only the files this round touched against the corpus, through licence_line's own scan_texts. Prints file, line, | 1/0/3 | agent a2421b8932:377 @10:13 | 1 |
| `lowfix/lic_filter.py` | Print licence-line hits for the slice files only, without any preview text (never print corpus text). | 1/0/0 | agent a2421b8932:138 @10:05 | 1 |
| `myll.py` | Scan only this slice's files against the corpus index (read-only), printing each shared run of MY text. | 1/0/4 | agent a433896f45:500 @10:56 | 1 |
| `myscan.py` | Scan only this slice's files against the corpus index and print each shared run as it reads in OUR file. | 1/1/10 | agent ad751e633f:494 @12:20 | 1 |
| `rereview/licence_filter.py` | Filtered a saved licence report to the files under review. | 1/1/2 | agent a9d6f75591:275 @17:53 | 1 |
| `rereview_b/licence_mine.py` | Filtered a saved licence report to batch-B files. | 1/0/2 | agent a264398132:317 @15:42 | 1 |
| `rr_lic.py` | Filtered a saved licence report to a fixer's files. | 1/0/1 | agent a0895e9b15:208 @15:43 | 1 |
| `rr_ll_filter.py` | Filter the licence-line report to the files under review. Prints file:line, token count, verdict, reason labels and | 1/0/2 | agent ad3c6ae917:206 @09:31 | 1 |
| `s1fix2/licence_scan.py` | Scan named files against the corpus with the house licence-line scanner. Prints only file, line span, token count | 1/0/1 | agent a26dea594b:353 @10:20 | 1 |
| `show.py` | Showed the house-side lines of selected breach hits (house text only). | 1/0/3 | agent a04ede0eaa:243 @08:16 | 1 |
| `triage/check_files.py` | Scan named house files against the real corpus (index built once), print each hit with its verdict and, for my own | 1/0/4 | agent a16ea05775:87 @10:47 | 1 |
| `triage/list_breaches.py` | List the non-baselined breaches of a licence-line JSON report, grouped by file, with whether the file existed at | 1/0/4 | agent a16ea05775:66 @10:46 | 1 |

### Licence-line development and review probes (55)

Verb status: scratch (building and reviewing the verb itself)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `dissector/probe_candidates.py` | Throwaway: longest run of each candidate fixture line shared with the corpus (lengths and ids only). | 2/0/0 | agent aaef1be63e:221 @09:14 | 1 |
| `dissector/scan4.py` | Throwaway: shared 12-token runs between the dissector's four files and the corpus. | 1/0/6 | agent aaef1be63e:54 @08:54 | 1 |
| `fix_licence.py` | Rewrote a card body that tripped the licence line. | 1/0/1 | agent a35553e7dc:492 @10:57 | 1 |
| `linegrep.py` | Distinctive-line check of house text against the corpus (counts only). | 1/0/1 | agent a7f66fcaa7:197 @08:45 | 1 |
| `ll_ab.py` | Scratch: A/B the third reading's cost on the real tree in one process (alternating runs, machine is shared). | 1/0/1 | agent a5159d6ae9:410 @10:30 | 1 |
| `ll_bench.py` | Timed the licence scan over tracked and untracked files. | 1/0/0 | agent acda0f5264:95 @08:52 | 1 |
| `ll_cw.py` | Compare comment-window policies: none / pure (all 12 tokens comment) / mixed (>=1). Prints hit locations only. | 1/0/0 | agent acda0f5264:161 @09:06 | 1 |
| `ll_cw2.py` | Refined comment-window policy check: which comment tokens make a window count. | 1/0/0 | agent acda0f5264:171 @09:08 | 1 |
| `ll_extra.py` | Scanned extra test globs for licence hits. | 1/0/2 | agent a7f66fcaa7:110 @08:42 | 1 |
| `ll_hash.py` | Ruling d probe: which hits hold the sine-fract hash constants, and does any run consist of nothing else? | 2/0/0 | agent acda0f5264:284 @09:16 | 1 |
| `ll_prof.py` | Scratch: where does the scan's time go (index, fast reading, third reading, binary text)? | 2/0/2 | agent a5159d6ae9:336 @10:19 | 2 |
| `lowfix/lic_candidates.py` | Which stub body for the synthetic shpLinstep shares no 12-token run with the corpus? Counts only, never the text. | 1/0/2 | agent a2421b8932:388 @10:14 | 1 |
| `lowfix/why_s0.py` | For every malformed-draft pin, print which refusal fires (so each pin fails for its own reason, not an incidental one). | 1/0/1 | agent a2421b8932:207 @10:07 | 1 |
| `patch_ll.py` | Patch of the licence-line module. | 1/0/1 | agent ae69fc909d:634 @11:05 | 1 |
| `patch_ll2.py` | Second patch of the licence-line module. | 1/0/1 | agent ae69fc909d:657 @11:06 | 1 |
| `probe_fix.py` | Verified a proposed lexer fix in memory (monkeypatch; the module file was not edited). | 1/0/2 | agent a1634fbc2e:242 @08:40 | 1 |
| `probe_fn.py` | False-negative probes against the REAL corpus index, in memory only. Prints counts, never corpus text. | 1/0/3 | agent a1634fbc2e:138 @08:33 | 1 |
| `probe_oneline.py` | Synthetic reproduction: short commented lines held as a one-line string were missed. | 1/0/5 | agent a1634fbc2e:277 @08:42 | 1 |
| `probe_plant.py` | Plant a real corpus line (12-14 code tokens, original formatting) into a temp tree UNDER state/ (the licence line: | 1/0/2 | agent a1634fbc2e:201 @08:39 | 1 |
| `probe_scope.py` | Which text files outside the licence line's scope share a 12-token run with the corpus (counts only). | 1/0/4 | agent a1634fbc2e:99 @08:30 | 1 |
| `rr/overlap.py` | Re-review: independent corpus-overlap measure for named repo files. Prints NO corpus text: only file:line, how | 1/0/2 | agent af4b397886:180 @09:30 | 1 |
| `rr/overlap2.py` | Re-review: independent corpus-overlap measure for named repo files. Prints NO corpus text: only file:line, how | 0/2/5 | agent af4b397886:207 @09:32 | 1 |
| `rr3/esc.py` | Escape-handling check. | 1/0/0 | agent a00a33bdab:210 @11:15 | 1 |
| `rr4L/p_edges.py` | Re-review probe: edge cases on synthetic text only (no corpus text). Each prints CAUGHT/MISSED or the value seen. | 0/0/1 | no write seen | 0 |
| `rr4L/p_edges2.py` | Copy of rrL/p_edges2.py. | 0/0/0 | no write seen | 0 |
| `rr4L/p_fuzz.py` | Copy of rrL/p_fuzz.py. | 0/0/0 | no write seen | 0 |
| `rr4L/p_mdsnip.py` | Re-review probe 8 (real corpus, memory only): a research note that names a glob path in backticks (`design/*.frag`) | 0/0/0 | no write seen | 0 |
| `rr4L/p_oneline.py` | Re-review probe (defect 4): every real corpus pass held as a one-line JSON string inside JS, and as a Python | 0/0/0 | no write seen | 0 |
| `rr4L/p_r3check.py` | Sanity check for probe 9: on the real snippets that the shipped reading misses after a backticked glob path, does the | 0/0/0 | no write seen | 0 |
| `rr4L/p_slash.py` | Re-review 4 probe: JSON whose encoder escapes the forward slash (`\\/`, as PHP's json_encode does by default), so a | 1/0/1 | agent a902e574f4:147 @11:14 | 1 |
| `rr4L/p_state.py` | Re-review probe: are the tracked files under the top-level state/ (excluded by ruling a, but committed and public) | 0/0/0 | no write seen | 0 |
| `rr4L/p_stray.py` | Re-review probe 3: a real corpus pass (memory only) held in a JS template literal that follows an `accept="audio/*"` | 0/0/0 | no write seen | 0 |
| `rr4L/p_swallow.py` | Re-review probe 7: in real house files, how many lines does a slash-star that sits inside a one-line quoted string | 0/0/0 | no write seen | 0 |
| `rr4L/p_swap.py` | Re-review probe 6 (synthetic): a baselined copy is removed and a DIFFERENT copy of the same corpus shader, no longer, | 0/0/0 | no write seen | 0 |
| `rr4L/plant4.py` | Re-review 4 plant probe. Real corpus snippets, chosen in memory, are planted in many forms in a temp folder under | 1/0/2 | agent a902e574f4:131 @11:13 | 1 |
| `rrL/p_cw.py` | Re-review probe 4: which real hits (breach or baseline) exist ONLY because of the new commented-out-code windows | 1/0/1 | agent a7a75ef463:188 @09:51 | 1 |
| `rrL/p_edges.py` | Re-review probe: edge cases on synthetic text only (no corpus text). Each prints CAUGHT/MISSED or the value seen. | 1/0/1 | agent a7a75ef463:156 @09:48 | 1 |
| `rrL/p_edges2.py` | Re-review probe 2: an unclosed comment opener inside an earlier string (synthetic), plus one real-corpus case held in memory. | 1/0/1 | agent a7a75ef463:162 @09:49 | 1 |
| `rrL/p_fuzz.py` | Re-review probe 5: fuzzed the fast token reading against the exact reading. | 1/0/1 | agent a7a75ef463:200 @09:52 | 1 |
| `rrL/p_mdsnip.py` | Re-review probe 8 (real corpus, memory only): a research note that names a glob path in backticks (`design/*.frag`) | 1/0/0 | agent a7a75ef463:218 @09:54 | 1 |
| `rrL/p_oneline.py` | Re-review probe (defect 4): every real corpus pass held as a one-line JSON string inside JS, and as a Python | 1/0/1 | agent a7a75ef463:97 @09:41 | 1 |
| `rrL/p_r3.py` | Re-review probe 9: does the real tree hold corpus runs today that the shipped scanner misses because a slash-star | 1/0/0 | agent a7a75ef463:222 @09:54 | 1 |
| `rrL/p_r3check.py` | Sanity check for probe 9: on the real snippets that the shipped reading misses after a backticked glob path, does the | 1/0/0 | agent a7a75ef463:226 @09:55 | 1 |
| `rrL/p_real.py` | Re-review probe: run the shipped scan over the real tree, save the report WITHOUT previews (no corpus-identical text | 1/0/1 | agent a7a75ef463:108 @09:41 | 1 |
| `rrL/p_state.py` | Re-review probe: are the tracked files under the top-level state/ (excluded by ruling a, but committed and public) | 1/0/1 | agent a7a75ef463:126 @09:44 | 1 |
| `rrL/p_stray.py` | Re-review probe 3: a real corpus pass (memory only) held in a JS template literal that follows an `accept="audio/*"` | 1/0/1 | agent a7a75ef463:168 @09:49 | 1 |
| `rrL/p_swallow.py` | Re-review probe 7: in real house files, how many lines does a slash-star that sits inside a one-line quoted string | 1/0/0 | agent a7a75ef463:214 @09:53 | 1 |
| `rrL/p_swap.py` | Re-review probe 6 (synthetic): a baselined copy is removed and a DIFFERENT copy of the same corpus shader, no longer, | 1/0/0 | agent a7a75ef463:206 @09:53 | 1 |
| `rr_overlap.py` | Independent corpus-overlap measure for a few repo files. Never prints corpus text or matched text: only file:line, | 1/0/1 | agent ad3c6ae917:216 @09:32 | 1 |
| `rr_overlap2.py` | Independent corpus-overlap measure for a few repo files. Never prints corpus text or matched text: only file:line, | 0/0/3 | no write seen | 0 |
| `s1fix/escape.py` | Re-escaped invisible characters at listed lines. | 1/0/2 | agent a0c9d23e4d:278 @09:04 | 1 |
| `s1fix2/escape_specials.py` | Spell U+FFFD and U+FEFF as escapes in the three edited sources (they are invisible as literal characters). | 1/0/1 | agent a26dea594b:287 @10:15 | 1 |
| `t.py` | Regex check of an escape case for the licence lexer. | 1/0/2 | agent a1634fbc2e:237 @08:40 | 1 |
| `triage/pin_allow.py` | Pins for the new allowlist entries, on a synthetic corpus (our own text, written to a temp folder in the scratchpad): | 1/0/0 | agent a16ea05775:321 @10:58 | 1 |
| `triage/try_snippets.py` | Scan candidate rewrites (one per line of a text file, '\\n' escapes allowed, or blocks separated by '-----') | 1/0/0 | agent a16ea05775:116 @10:51 | 1 |

### Mutation checks (46)

Verb status: NEW: `agent_cli.py mutate` (item 4)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `batchb_fix/mutant_light_probe.py` | See the GPU half of tests/test_glsl_twins_light.py fail on the PRE-FIX GLSL: copy the library to scratch, put the old | 1/0/1 | agent a4fc73a8b2:369 @14:19 | 1 |
| `batchb_fix/mutant_rays_probe.py` | See the new rays-family GPU probe fail on the PRE-FIX GLSL: copy the library to scratch, put the old rmRelaxed overlap | 1/0/1 | agent a4fc73a8b2:626 @14:32 | 1 |
| `fringe-fix/oldlib.py` | Scratch: a copy of the GLSL library with the two aurora recipes put back as they were before the fringe fix (the | 1/0/2 | agent a1c66d0ec0:916 @17:32 | 1 |
| `mut/cases.mjs (deleted)` | Cases for that harness. | 1/0/0 | agent acb9d55a55:63 @03:44 | 1 |
| `mut/cases.py (deleted)` | Python side of those cases. | 1/0/0 | agent acb9d55a55:61 @03:43 | 1 |
| `mut/harness.mjs (deleted)` | Mutation harness for the cadence judge (folder later deleted). | 1/0/1 | agent acb9d55a55:45 @03:42 | 1 |
| `mut_core.py` | pytest plugin: swap in a C-style (truncating) modulo and an isnan-only finiteOr, to check the GPU probe catches them. | 1/0/1 | agent a720e8db21:147 @13:46 | 1 |
| `mut_tags.py` | pytest plugin: the twins without their tags (the reviewed code), to check the SwiftShader parity sees the GLSL's tags. | 1/0/0 | agent a720e8db21:159 @13:47 | 1 |
| `mutants.mjs` | Applied each named mutant to a copy of the cadence judge and counted fixture failures. | 1/0/1 | agent ae14080618:73 @03:48 | 1 |
| `mutants.py` | Scratch pytest plugin: apply one in-memory mutant (env MUTANT) to arsenal.shaders.licence_line before the pins run. | 1/0/0 | agent a5159d6ae9:421 @10:32 | 1 |
| `mutate.mjs` | Mutation run on the cadence judge: each single-point break against fixtures, oracle and fuzz. | 1/1/3 | agent a44519cf9f:111 @03:35 | 1 |
| `mutate.py` | Mutation run against the core probe (the third of three harnesses written at this path). | 3/0/1 | agent a04ede0eaa:313 @08:18 | 3 |
| `mutate_stage.py` | Mutated the tracked workbench stage.js in place, ran its tests, restored it in finally. | 1/0/2 | agent ade2258a6c:236 @14:34 | 1 |
| `mutate_stage2.py` | Second in-place mutation round on stage.js. | 1/0/2 | agent ade2258a6c:241 @14:36 | 1 |
| `mutate_stage3.py` | Third round. | 1/0/1 | agent ade2258a6c:430 @14:51 | 1 |
| `mutate_stage4.py` | Fourth round. | 1/0/2 | agent ade2258a6c:460 @14:53 | 1 |
| `probe_mut.py` | Spot-check the builder's mutation claims IN MEMORY: patch one mechanism, run the synthetic pins, count reds. | 1/0/2 | agent a1634fbc2e:269 @08:42 | 1 |
| `rereview_b/mutant_light_probe.py` | See the GPU half of tests/test_glsl_twins_light.py fail on the PRE-FIX GLSL: copy the library to scratch, put the old | 0/0/0 | no write seen | 0 |
| `rereview_b/mutant_rays_probe.py` | See the new rays-family GPU probe fail on the PRE-FIX GLSL: copy the library to scratch, put the old rmRelaxed overlap | 0/0/0 | no write seen | 0 |
| `rev_faith/check.mjs` | Judged adversarial cases with the live cadence judge. | 1/0/0 | agent ab384b144c:65 @03:42 | 1 |
| `rev_faith/fx.mjs` | Ran a mutant against the cadence fixtures. | 0/0/0 | no write seen | 0 |
| `rev_faith/fz.mjs` | Ran a mutant against the fuzz cases. | 0/0/0 | no write seen | 0 |
| `rev_faith/orc.mjs` | Ran a mutant against the private oracle. | 0/0/0 | no write seen | 0 |
| `rr/mut/mutate.py` | Mutated a mirrored runtime and render copy and ran the mirror's tests. | 0/0/2 | no write seen | 0 |
| `rr/mutate_pins.py` | Mutation checks of the new sheets pins: put each defect back into the NEW twin and see the pin catch it. | 1/0/2 | agent a91016d585:446 @15:41 | 1 |
| `rr2/mutate.py` | Re-review scratch: do the new pins catch what they claim? Revert one fix at a time in the twin (in memory only, | 1/0/1 | agent a89517df2b:233 @17:46 | 1 |
| `rr3/py_revert.py` | Put old grid code back in the param twin (mutation). | 1/0/2 | agent a00a33bdab:215 @11:16 | 1 |
| `rr3/py_revert2.py` | Second revert variant. | 1/0/0 | agent a00a33bdab:220 @11:16 | 1 |
| `rr3/s0_revert.py` | Load atlas_build from source with one fix undone at a time, and see whether the fix's pins then fail. | 1/0/0 | agent a00a33bdab:88 @11:10 | 1 |
| `rr3_intermediate.py` | pytest plugin for a red check only: put back the step before the macro rule (a Common token sees Common's aliases | 1/0/2 | agent a0034023d0:324 @16:16 | 1 |
| `rr4L/mutplug.py` | pytest plugin: re-ran licence_line.py with one in-memory mutation chosen by env MUT (the file on disk untouched). | 1/0/2 | agent a902e574f4:161 @11:15 | 1 |
| `rr4_mut_plugin.py` | Re-review red check (read-only): a pytest plugin that puts one defect back into explain.py IN MEMORY, chosen by the | 1/0/0 | agent a8452a4b74:107 @17:41 | 1 |
| `rrL/p_mut.py` | Undid each fix in memory and checked that the pins named for that defect turn red (counts only). | 1/0/2 | agent a7a75ef463:132 @09:45 | 1 |
| `rrL/p_mut2.py` | Re-review mutation probe, source level: rewrite one line of a shipped function IN MEMORY (inspect + exec into the | 1/0/1 | agent a7a75ef463:143 @09:47 | 1 |
| `rrL/p_mut3.py` | Re-review mutation probe, source level: rewrite one line of a shipped function IN MEMORY (inspect + exec into the | 0/0/1 | no write seen | 0 |
| `s1fix/mutate.py` | Mutated the tracked modlib.js in place, ran tests, restored it in finally. | 1/0/1 | agent a0c9d23e4d:289 @09:05 | 1 |
| `s1fix2/mutate.py` | Mutation check for the round-2 parity pins: each mutation of a SCRATCH copy of modlib.js must change what the plan | 1/0/4 | agent a26dea594b:255 @10:14 | 1 |
| `s1rr2/mut_runner.py` | Loaded a mutated modules.py copy as the real module. | 0/0/0 | no write seen | 0 |
| `s1rr2/mutate_js.py` | Mutation check for the round-2 parity pins: each mutation of a SCRATCH copy of modlib.js must change what the plan | 0/0/0 | no write seen | 0 |
| `s1rr2/mutate_py.py` | Mutation check, Python twin: each mutation of a SCRATCH copy of modules.py is installed as arsenal.shaders.modules in | 1/0/1 | agent a9616f0195:161 @11:13 | 1 |
| `s1rr2/mutate_py2.py` | Mutation check, Python twin: each mutation of a SCRATCH copy of modules.py is installed as arsenal.shaders.modules in | 0/1/0 | agent a9616f0195:200 @11:15 | 1 |
| `s1rr2/pinfirst_runner.py` | Runner for the pin-first mutation check. | 0/0/0 | no write seen | 0 |
| `verify/harness.mjs` | Verifier: each mutant of a copy of the cadence judge against fixtures and oracle. | 1/0/0 | agent a289429858:65 @03:53 | 1 |
| `verify/mutants.mjs` | The reviewer's 82 mutants, copied from mut/harness.mjs. | 0/0/0 | no write seen | 0 |
| `verify/sweep.mjs` | Systematic one-line operator sweep over a copy of the cadence judge. | 1/0/0 | agent a289429858:110 @03:55 | 1 |
| `verify/vacuity.mjs` | Vacuity drills with a fake oracle folder. | 1/0/0 | agent a289429858:137 @03:59 | 1 |

### Contact sheets, crops, pixel probes (20)

Verb status: EXISTS: `py -m arsenal.media sheet` (sheets, --zoom); NEW: `arsenal.media px` (item 6)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `aurora-fix/scrop.py` | Scratch: zoomed crops of the sheets twin (x3) for variants: shows grain versus hatching. | 1/0/1 | agent afaf271492:616 @14:38 | 1 |
| `aurora-fix/strip.py` | Scratch: lay rendered card frames side by side (rows = cards, columns = t) for a look. | 1/0/1 | agent afaf271492:731 @14:46 | 1 |
| `batchb_fix/card_diff.py` | Where two renders of one card differ: a heat image (scaled x8) and a count, so a look can be checked precisely. | 1/0/0 | agent a4fc73a8b2:651 @14:33 | 1 |
| `contact_light.py` | Contact sheet of the light family's cards with name and verdict. | 1/0/3 | agent a55597111b:717 @12:24 | 1 |
| `corr1_bbox.py` | Bounding box of pixels differing from a background colour (corroboration pass 1). | 1/0/2 | agent a4e374169c:83 @14:11 | 1 |
| `corr1_frac.py` | Fraction of pixels by red-channel band (white-ish vs blue-ish) per frame, corroboration pass 1. | 1/0/1 | agent a4e374169c:127 @14:13 | 1 |
| `corr1_heat.py` | Count heat-ramp colour classes per frame (corroboration pass 1). | 1/0/1 | agent a4e374169c:294 @14:21 | 1 |
| `corr1_px.py` | Corroboration pass 1 pixel probe: the lane's own copy, made after the shared px.py. | 1/0/15 | agent a4e374169c:53 @14:09 | 1 |
| `corr1_rowmax.py` | For each row band, report the brightest pixel's colour and x, plus the row's centre-column value (corroboration pass 1). | 1/0/1 | agent a4e374169c:261 @14:20 | 1 |
| `corr1_sun.py` | Centroid of near-white pixels (the sun core) per frame, as a fraction of width/height (corroboration pass 1). | 1/0/1 | agent a4e374169c:363 @14:25 | 1 |
| `corr2/px.py` | Another lane's px.py, found in place of its own. | 0/0/1 | no write seen | 0 |
| `corr2/px2.py` | Pixel inspector re-made private to its lane after the shared px.py was overwritten. | 1/0/0 | agent ac0c55292d:80 @14:10 | 1 |
| `corrob5/probe.py` | Pixel probe for render corroboration pass 5. Usage: py probe.py <id> <cmd> ... | 1/2/0 | agent a3b9e2b147:74 @14:10 | 1 |
| `fringe-fix/grids.py` | Tiled each rendered card's frames into labelled rows and printed per-frame measures. | 1/0/1 | agent a1c66d0ec0:806 @17:26 | 1 |
| `fringe-fix/zoom.py` | Crop and nearest-neighbour upscale of a PNG. | 1/0/0 | agent a1c66d0ec0:221 @16:18 | 1 |
| `loved_sheet.py` | Labelled contact sheet of the Loved stills the runtime rendered (private). | 1/0/1 | main:3339 @08:53 | 1 |
| `montage.py` | Tiled PNGs into one labelled image. | 1/0/17 | agent abadb13dbf:450 @13:14 | 1 |
| `px.py` | Pixel probes for corroboration (luma grid, extremes, hue histogram); four lanes wrote this path. | 4/0/8 | agent a3b9e2b147:57 @14:09 | 4 |
| `sheet.py` | Contact sheet for a group card at three times (three agents wrote this path). | 3/0/7 | agent a3084eb892:710 @13:29 | 3 |
| `zoom.py` | Crop and nearest-neighbour upscale of a PNG; also coarse grid stats. | 1/0/13 | agent a7ca69e226:67 @14:09 | 1 |

### Card renders and GPU parity runs (14)

Verb status: PARTLY: `shader card`; NEW flag: several names (item 9)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `aurora-fix/render.py` | Rendered named cards through the shader verb into a state/ folder, with a receipt line each. | 1/1/4 | agent afaf271492:153 @14:13 | 1 |
| `drill.py` | Drill: the colour probe must fail on a perturbed library copy. | 1/0/5 | agent ae69fc909d:477 @10:54 | 1 |
| `drill_light_probe.py` | Drill: the light GPU probe must FAIL against a perturbed twin and pass against the real one. | 1/0/1 | agent a55597111b:562 @12:16 | 1 |
| `fixed.py` | Re-ran the core probe groups against a rendered PNG. | 1/0/2 | agent af450251ba:251 @11:58 | 1 |
| `fringe-fix/gpu_extremes.py` | Render the extremes parity card through the card verb's renderer (SwiftShader, house lock) into scratch, and | 2/0/1 | agent a1c66d0ec0:624 @17:09 | 1 |
| `labgpu/runs.py` | Printed a lab render report's runs. | 1/0/0 | agent a2688a47ec:514 @12:10 | 1 |
| `parity_stats.py` | GPU-versus-twin difference statistics for a card. | 2/0/3 | agent a3084eb892:686 @13:28 | 2 |
| `parity_teeth.py` | Checked that the hash/noise parity probe has teeth. | 1/0/0 | agent af450251ba:347 @12:01 | 1 |
| `probe_diag.py` | Rendered the colour probe card into a temp folder for diagnosis. | 1/0/2 | agent ae69fc909d:465 @10:53 | 1 |
| `render_light_cards.py` | Rendered the light family's cards in one burst and printed the verdicts. | 1/0/8 | agent a55597111b:442 @12:11 | 1 |
| `rendercards.py` | Rendered named house cards in one card-driver run (one GPU lock) and printed a table. | 1/0/8 | agent ad751e633f:620 @12:30 | 1 |
| `run_receipt.py` | Printed a render receipt's runs and errors. | 1/0/5 | agent ade2258a6c:333 @14:42 | 1 |
| `shelf_renders.py` | Re-rendered every Loved shader through the render and filmstrip verbs, with a 12 s gap. | 1/0/1 | agent a108103540:133 @10:03 | 1 |
| `show_synth.py` | Dissected synthetic shaders in a temp state root. | 1/0/4 | agent ad5abd8ab5:268 @14:00 | 1 |

### Look tuning: variants, measures, twin previews (56)

Verb status: NEW flag: `card --variant ... --sheet` (item 9); twin-side work is scratch

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `aurora-fix/alias.py` | Scratch: aliasing of the sheets at knob extremes: 1x against a 3x3 box-supersampled render (jitter off). | 1/0/1 | agent afaf271492:849 @14:59 | 1 |
| `aurora-fix/g1_new_aurora_block.py` | Draft of new pins for the aurora twin. | 1/0/1 | agent afaf271492:896 @15:05 | 1 |
| `aurora-fix/g1_old_aurora_block.py` | The previous aurora twin block, kept for comparison. | 0/0/1 | no write seen | 0 |
| `aurora-fix/hatch.py` | Scratch: the sheets' sampling error against a converged reference (the same stack averaged over 16 jitter values), | 2/1/1 | agent afaf271492:650 @14:40 | 1 |
| `aurora-fix/measure.py` | Scratch: numbers beside the pictures for the aurora fix (twin-side). | 1/2/1 | agent afaf271492:262 @14:18 | 1 |
| `aurora-fix/mkvariants.py` | Wrote variant cards (constant overrides) of a house card into the scratch cards folder. | 1/0/1 | agent afaf271492:729 @14:46 | 1 |
| `aurora-fix/old/groups_aurora_old.py (deleted)` | Old aurora twin, for pins run against it. | 1/0/0 | agent afaf271492:954 @15:11 | 1 |
| `aurora-fix/old/run_pins_on_old.py (deleted)` | Ran new pins against the old twin. | 1/0/3 | agent afaf271492:958 @15:11 | 1 |
| `aurora-fix/parity_block.py` | Draft parity card text for the g1 groups. | 1/0/1 | agent afaf271492:1005 @15:15 | 1 |
| `aurora-fix/preview.py` | Scratch: twin-side previews (fast) of the aurora tiers, finished like the cards (superlinear 0.85, tanh, sRGB). | 1/1/1 | agent afaf271492:288 @14:20 | 1 |
| `aurora-fix/raydbg.py` | Ray debug of the sheets twin. | 2/0/5 | agent afaf271492:908 @15:06 | 1 |
| `aurora-fix/raytest.py` | Draft pin for the sheets rays. | 1/0/1 | agent afaf271492:932 @15:08 | 1 |
| `aurora-fix/raytilt.py` | Scratch: do the sheets' rays run up world verticals (converging on the zenith's vanishing point) or fan out? | 1/3/2 | agent afaf271492:483 @14:30 | 1 |
| `aurora-fix/svariants.py` | Scratch: twin variants of the sheets, one row per variant (t = 0 and 4), constants monkeypatched. | 1/0/1 | agent afaf271492:583 @14:36 | 1 |
| `aurora-fix/timing.py` | Timed the aurora twins. | 1/0/1 | agent afaf271492:252 @14:16 | 1 |
| `aurora-fix/twin_head.py` | Draft head of the aurora twin module. | 0/0/2 | no write seen | 0 |
| `aurora-fix/twin_sheets.py` | A sheet's hue by its height in the stack (0 the hem, 1 the top sheet): auroraLineColor from 106 to 266 km for | 1/0/1 | agent afaf271492:700 @14:45 | 1 |
| `aurora-fix/variants.py` | Scratch: twin variants of the band, one row per variant (t = 0 and 4), constants monkeypatched. | 1/0/1 | agent afaf271492:439 @14:28 | 1 |
| `fringe-fix/baseline.py` | Twin baseline pictures of the aurora tiers. | 1/0/1 | agent a1c66d0ec0:166 @16:09 | 1 |
| `fringe-fix/calib.py` | Calibrated fringe measures. | 1/0/1 | agent a1c66d0ec0:175 @16:10 | 1 |
| `fringe-fix/calib2.py` | Second calibration pass. | 1/0/2 | agent a1c66d0ec0:289 @16:24 | 1 |
| `fringe-fix/dbg.py` | Checked a tier for NaN and range. | 1/0/0 | agent a1c66d0ec0:195 @16:16 | 1 |
| `fringe-fix/dbg2.py` | Debug print 2. | 1/0/0 | agent a1c66d0ec0:229 @16:18 | 1 |
| `fringe-fix/dbg3.py` | Camera-ray debug of the fringe. | 2/0/0 | agent a1c66d0ec0:234 @16:19 | 1 |
| `fringe-fix/dbg4.py` | Debug print 4. | 1/0/0 | agent a1c66d0ec0:299 @16:26 | 1 |
| `fringe-fix/defaults_cmp.py` | Compared twin pictures under overridden defaults. | 1/0/3 | agent a1c66d0ec0:325 @16:29 | 1 |
| `fringe-fix/evalp.py` | Evaluated a parameter override at several clocks. | 1/0/4 | agent a1c66d0ec0:190 @16:15 | 1 |
| `fringe-fix/gatecheck.py` | Checked the band gate along one row. | 1/0/2 | agent a1c66d0ec0:403 @16:38 | 1 |
| `fringe-fix/lp.py` | 1D profile check of the fringe line. | 1/0/0 | agent a1c66d0ec0:270 @16:22 | 1 |
| `fringe-fix/maskview.py` | Visualised the fringe mask for one tier and palette. | 1/0/2 | agent a1c66d0ec0:483 @16:45 | 1 |
| `fringe-fix/metrics.py` | Fringe-line and white-ceiling measures on twin pictures. | 1/0/0 | agent a1c66d0ec0:160 @16:09 | 1 |
| `fringe-fix/proto.py` | Prototype of the fringe fix in the twin. | 1/0/1 | agent a1c66d0ec0:186 @16:14 | 1 |
| `fringe-fix/ramps.py` | Colour ramp check. | 1/0/1 | agent a1c66d0ec0:265 @16:21 | 1 |
| `fringe-fix/ramps2.py` | Second ramp check. | 1/0/2 | agent a1c66d0ec0:270 @16:22 | 1 |
| `fringe-fix/sgain.py` | Swept the fringe gain. | 1/0/0 | agent a1c66d0ec0:566 @16:56 | 1 |
| `fringe-fix/sgain2.py` | Swept gain and epsilon pairs. | 1/0/0 | agent a1c66d0ec0:576 @16:59 | 1 |
| `fringe-fix/sweep.py` | Swept twin parameters given as JSON. | 1/0/1 | agent a1c66d0ec0:357 @16:31 | 1 |
| `fringe-fix/thick.py` | Fringe thickness across altitude and scale. | 1/0/5 | agent a1c66d0ec0:506 @16:47 | 1 |
| `fringe-fix/timing.py` | Timed the twin at two sizes. | 1/0/0 | agent a1c66d0ec0:146 @16:08 | 1 |
| `fringe-fix/variants.py` | Wrote variant cards with constants replaced and rendered them through the card renderer. | 1/0/1 | agent a1c66d0ec0:798 @17:25 | 1 |
| `fringe-fix/yield.py` | Luma yield across altitudes per palette. | 1/0/2 | agent a1c66d0ec0:180 @16:11 | 1 |
| `rr/cut_probe.py` | Instrument the band twin along one image row to find the term that makes the vertical cut near x = 473. | 1/0/1 | agent a91016d585:151 @15:29 | 1 |
| `rr/hem_gpu.py` | GPU-side hem checks on the band renders: how sharply the light rises per column. | 1/0/1 | agent a91016d585:199 @15:32 | 1 |
| `rr/make_variants.py` | Write variant cards of the two aurora cards into the scratchpad (consts replaced, size and t changed). | 1/0/1 | agent a91016d585:190 @15:31 | 1 |
| `rr/rag_probe.py` | Scratch probe: the band twin at the card's defaults with the hem rag at 6 km (shipped), 3 km (old) and 0, through | 1/0/1 | agent a91016d585:533 @15:47 | 1 |
| `rr2/fringe_corners.py` | Re-review scratch: the fringe's thin-edge rule off the pinned point (curtain width 1, hem at its default): the | 1/0/2 | agent a89517df2b:284 @17:49 | 1 |
| `rr2/measure.py` | Re-review scratch: measure every rendered variant PNG: the weakest channel's maximum (and where), the fringe mask's | 1/1/5 | agent a89517df2b:107 @17:41 | 1 |
| `rr2/precap.py` | Re-review scratch: how large does the white cap's tanh argument get inside the knob ranges? Some drivers build tanh | 1/0/1 | agent a89517df2b:245 @17:47 | 1 |
| `rr2/render_variants.py` | Re-review scratch: variant cards of the two aurora cards (consts replaced), rendered through the card verb's renderer | 1/0/2 | agent a89517df2b:83 @17:40 | 1 |
| `tri/look3.py` | Rendered the triangle-noise twin at two times. | 0/0/2 | no write seen | 0 |
| `tri/proto.py` | Scratch prototype for the triangle filament noise: look at it before pinning constants. | 1/0/1 | agent afe594ed16:222 @11:49 | 1 |
| `tri/proto2.py` | Second triangle-noise prototype. | 0/0/0 | no write seen | 0 |
| `tri/proto_lib.py` | Scratch prototype for the triangle filament noise: look at it before pinning constants. | 0/0/0 | no write seen | 0 |
| `tri/stats.py` | Statistics of the triangle noise. | 0/0/0 | no write seen | 0 |
| `tri/variants.py` | Variants of the triangle noise. | 0/0/0 | no write seen | 0 |
| `variants.py` | Wrote palette and debug-view variant cards of the g1 groups for the sheets. | 2/0/5 | agent abadb13dbf:705 @13:32 | 2 |

### Corpus-wide explain audits and explain reviews (35)

Verb status: NEW flag: `explain --all --snapshot` / `--diff` (item 8)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `cache_probe.py` | Probe: does explain's cache notice a change in corpus/media or meta.json? (temp dir only) | 1/0/3 | agent a274a8f327:94 @14:30 | 1 |
| `explain_corpus_counts.py` | Build every explain ledger over the real corpus IN MEMORY (nothing written) and tally labels and rule checks. | 1/0/4 | agent ac9f80be9e:92 @14:47 | 1 |
| `explain_eyeball.py` | Print full ledgers for the synthetic test shaders (temp dir in the scratchpad only). | 1/0/1 | agent ac9f80be9e:267 @14:56 | 1 |
| `explain_live_audit.py` | Read-only audit: build every corpus ledger in memory (nothing written) and check the new rules. | 1/0/4 | agent a0c879325b:250 @15:27 | 1 |
| `look_probe.py` | Probe: does the look question stay 'answered' when the runtime reports an unsupported input (drawn black)? | 1/0/3 | agent a274a8f327:280 @14:37 | 1 |
| `p6_green_check.py` | In memory only: does the reference drift pin go green once the reference states the explain rules? (no file edits) | 1/0/1 | agent ac9f80be9e:355 @15:00 | 1 |
| `rereview_cache_real.py` | Re-review of the explain cache on a copy of one real corpus shader (temp folder; the repo only read). | 1/0/1 | agent ab1d402444:162 @15:09 | 1 |
| `rereview_hand_sample.py` | Re-review: pick 20 diverse real corpus shaders, build each ledger IN MEMORY, print 30 claims with the text their | 1/0/2 | agent ab1d402444:131 @15:07 | 1 |
| `rereview_observed_audit.py` | Re-review audit (read-only, in memory): every observed claim over the whole corpus, checked mechanically against | 1/0/1 | agent ab1d402444:94 @15:04 | 1 |
| `rereview_observed_audit2.py` | Re-review audit 2 (read-only, in memory): (a) every observed READ row checked on a comment-stripped line for its own | 1/0/1 | agent ab1d402444:116 @15:06 | 1 |
| `rr2_alias_probe.py` | Synthetic probe (temp dir in scratchpad): an alias defined in one pass applied to another pass's plain variable, | 1/0/1 | agent ac366bf388:158 @15:38 | 1 |
| `rr2_alias_scope.py` | Read-only: every observed read row on the real corpus whose cited line holds the read ONLY through an alias name that | 1/0/1 | agent ac366bf388:152 @15:37 | 1 |
| `rr2_common_check.py` | Read-only: for the shaders whose feedback read lives in a Common macro, show the claim, the buffer source's use of | 1/0/1 | agent ac366bf388:109 @15:34 | 1 |
| `rr2_common_live.py` | Read-only: for every 'declared' row in an observed claim, does the ledger's OWN live index hold a read of that | 1/0/1 | agent ac366bf388:120 @15:35 | 1 |
| `rr2_compare.py` | Compared three ledger dumps for determinism. | 1/0/1 | agent ac366bf388:176 @15:39 | 1 |
| `rr2_declared_check.py` | Read-only: every observed 'declared ... no read found' claim on the real corpus, checked independently against the | 1/0/2 | agent ac366bf388:103 @15:33 | 1 |
| `rr2_determinism.py` | Read-only: dump every corpus ledger's (label, kind, tag, evidence, claim) built in memory, to compare across | 1/0/2 | agent ac366bf388:164 @15:38 | 1 |
| `rr2_hand_audit.py` | Read-only hand audit: build ledgers in memory for chosen real corpus shaders and print chosen claims with the source | 1/0/1 | agent ac366bf388:140 @15:36 | 1 |
| `rr2_hand_audit2.py` | Read-only: second hand-audit batch (media, render, dead, corroboration, cubemap) plus two line checks. | 1/0/1 | agent ac366bf388:146 @15:37 | 1 |
| `rr2_p6_check.py` | In memory only: does the p6 pin catch the old line-72 wording and its variants? No file is edited. | 1/0/1 | agent ac366bf388:193 @15:39 | 1 |
| `rr2_probe.py` | Re-review probe of explain.py on synthetic shaders in a temp folder. | 1/0/1 | agent ac366bf388:89 @15:32 | 1 |
| `rr2_show_src.py` | Read-only: print source lines matching a pattern in one corpus shader's passes, plus its claims for a tag. | 1/0/1 | agent ac366bf388:126 @15:35 | 1 |
| `rr3_alias_check.py` | Read-only: every observed read's code line must name the raw uniform/channel, or an alias of it defined in that | 1/1/4 | agent a0034023d0:352 @16:18 | 1 |
| `rr3_diff.py` | Diff two in-memory corpus ledger snapshots (rr3_snapshot.py): label totals, and every claim that changed. | 1/0/5 | agent a0034023d0:274 @16:13 | 1 |
| `rr3_doc_pins.py` | Scratch pins for review rr[0]'s five clean-room defects, the ICD 203 wording and the deconstruct back-link (the skill | 1/0/5 | agent a0034023d0:436 @16:22 | 1 |
| `rr3_eyeball.py` | Printed the synthetic no-entry and Common-macro ledgers for a look. | 1/0/0 | agent a0034023d0:268 @16:13 | 1 |
| `rr3_noread_check.py` | Read-only, independent of explain.py's live index: for every remaining 'no read found' row, does the text of the | 1/0/0 | agent a0034023d0:343 @16:17 | 1 |
| `rr3_noread_check2.py` | Read-only, independent of the live index: every row the ledger resolves as 'declared ... no read found' (any tag), | 1/0/2 | agent a0034023d0:347 @16:17 | 1 |
| `rr3_probe.py` | Probe the dissector on synthetic shaders written for the rr3 pins (our own words, no corpus code). | 1/0/0 | agent a0034023d0:192 @16:09 | 1 |
| `rr3_seed.py` | Read-only: the keyboard claim of two shaders under the current PYTHONHASHSEED (dissector line choice). | 1/0/1 | agent a0034023d0:333 @16:17 | 1 |
| `rr3_snapshot.py` | Read-only: build every corpus ledger in memory (nothing written) and dump each claim's label, kind, tag, text and | 1/0/4 | agent a0034023d0:181 @16:09 | 1 |
| `rr4_audit.py` | Re-review audit (read-only, in memory, nothing written): | 1/1/3 | agent a8452a4b74:154 @17:44 | 1 |
| `rr4_param_check.py` | Read-only: every observed read (and every _holds_read hit) whose matching token sits inside a macro body where that | 1/0/1 | agent a8452a4b74:245 @17:49 | 1 |
| `rr4_probe.py` | Re-review probes (read-only for the repo: synthetic shaders in a temp folder under the scratchpad, ledgers built in | 1/0/2 | agent a8452a4b74:234 @17:48 | 1 |
| `verify_explain.py` | Read-only check of explain ledgers built in memory over the real corpus (nothing written). | 1/0/1 | agent a274a8f327:65 @14:29 | 1 |

### Dissector and census development (27)

Verb status: PARTLY: `dissect`, `census`; NEW flag: `census --tag --sample` (item 8)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `cost_block.py` | Three views of a pass's per-pixel cost down the call graph (dissector development). | 1/0/1 | agent a2a4415ebc:727 @07:44 | 1 |
| `cost_vs_ms.py` | Rank correlation of the dissector's cost estimates against measured ms per frame. | 2/0/2 | agent a2a4415ebc:701 @07:43 | 1 |
| `d1_probe.py` | Independent probe of a seed-independence defect against the twins. | 1/0/1 | agent a720e8db21:95 @13:45 | 1 |
| `dbg_noise.py` | Debug print of noise detection for one corpus pass. | 1/0/3 | agent a2a4415ebc:496 @07:29 | 1 |
| `dbg_warp.py` | Debug print of domain-warp detection for one pass. | 1/0/1 | agent a2a4415ebc:414 @07:25 | 1 |
| `fbm_block.py` | Signal-kind classifier for the fbm detector (dissector development). | 1/0/2 | agent a2a4415ebc:238 @07:18 | 1 |
| `fix_ctrl.py` | Line-anchored patch of the dissector source. | 1/0/1 | agent a2a4415ebc:348 @07:22 | 1 |
| `folds_block.py` | Loop-body collector for the fold detector (dissector development). | 1/0/1 | agent a2a4415ebc:282 @07:20 | 1 |
| `list_tag.py` | Listed corpus shaders carrying a tag. | 1/0/5 | agent a2a4415ebc:367 @07:23 | 1 |
| `noise_recall.py` | Recall of the noise detector over the corpus. | 1/0/4 | agent a2a4415ebc:473 @07:28 | 1 |
| `order_census.py` | Which corpus shaders save buffer passes out of order (ids only). | 1/0/0 | agent a65ba60ee6:179 @08:59 | 1 |
| `patch_batch2.py` | Batch of detector patches. | 1/0/1 | agent a2a4415ebc:397 @07:25 | 1 |
| `patch_bounds.py` | Patch of the GLSL reader (uniform bounds). | 1/0/1 | agent a2a4415ebc:157 @07:06 | 1 |
| `patch_census2.py` | Patch of census.py. | 1/0/1 | agent a2a4415ebc:802 @07:49 | 1 |
| `patch_d1.py` | Patch of dissect.py (loop bounds). | 1/0/2 | agent a2a4415ebc:183 @07:15 | 1 |
| `patch_fres6.py` | Fresnel-detector patch. | 1/0/1 | agent a2a4415ebc:581 @07:32 | 1 |
| `patch_noise4.py` | Noise-detector patch. | 1/0/1 | agent a2a4415ebc:489 @07:29 | 1 |
| `patch_rep7.py` | Repetition-detector patch. | 1/0/1 | agent a2a4415ebc:618 @07:35 | 1 |
| `patch_sym.py` | Patch of the GLSL reader (symbolic limits). | 1/0/0 | agent a2a4415ebc:172 @07:07 | 1 |
| `patch_vd8.py` | Volume-density patch. | 1/0/1 | agent a2a4415ebc:766 @07:47 | 1 |
| `patch_vol5.py` | Volume-detector patch. | 1/0/1 | agent a2a4415ebc:543 @07:31 | 1 |
| `patch_warp3.py` | Patch of dissect.py (warp detection). | 1/0/1 | agent a2a4415ebc:447 @07:27 | 1 |
| `sample_tag.py` | Sampled evidence lines for one tag across the corpus. | 1/0/6 | agent a2a4415ebc:573 @07:31 | 1 |
| `scan2.py` | Regex census of colour-encoding idioms across the corpus. | 1/0/3 | agent a92c526c12:266 @06:50 | 1 |
| `scan_color.py` | Regex census of gamma idioms across the corpus. | 1/0/0 | agent a92c526c12:29 @06:38 | 1 |
| `smoke_dissect.py` | Timed the dissector over the whole corpus, listing failures. | 1/0/10 | agent a2a4415ebc:252 @07:18 | 1 |
| `smoke_glsl.py` | Timed the GLSL parser over the corpus (loops, bounds, notes). | 1/0/4 | agent a2a4415ebc:74 @07:02 | 1 |

### Atlas and library consistency (20)

Verb status: PARTLY: `shader lib lint`, `shader atlas`; NEW flag: `atlas --gaps` (item 18)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `atlas_gap.py` | Library names the atlas does not plan, and signature mismatches, with the defining file. | 1/0/1 | agent a720e8db21:123 @13:46 | 1 |
| `atlas_parts.py` | Looked up atlas parts for named functions. | 1/0/1 | agent a720e8db21:277 @13:51 | 1 |
| `batchA_status.py` | Status of batch A modules against the atlas. | 1/0/1 | agent ad751e633f:124 @11:43 | 1 |
| `batchb_fix/atlas_gap.py` | Library names the atlas does not plan, and signature mismatches (second agent). | 1/0/2 | agent a4fc73a8b2:107 @14:09 | 1 |
| `batchb_fix/atlas_peek.py` | Printed atlas manifest rows for batch B and recipes. | 1/0/1 | agent a4fc73a8b2:113 @14:09 | 1 |
| `batchb_fix/recipe_defs.py` | Print every recipe module's header facts and its function definitions (as the atlas must record them). | 1/0/2 | agent a4fc73a8b2:484 @14:23 | 1 |
| `batchb_fix/sig_diff.py` | Every planned function whose built signature differs from the atlas's text in anything (qualifiers, names, types). | 1/0/1 | agent a4fc73a8b2:155 @14:11 | 1 |
| `cardhdr.py` | Checked card headers. | 1/0/1 | agent aadbce3a55:177 @11:18 | 1 |
| `choice_units.py` | Checked units of choice params in three group recipes. | 1/0/1 | agent a3084eb892:813 @13:35 | 1 |
| `hdr.py` | Checked module header fields against the atlas. | 1/0/0 | agent aadbce3a55:67 @11:12 | 1 |
| `loved.py` | Checked atlas clauses that name Loved shaders. | 1/0/0 | agent a0ae5dd5ff:122 @08:28 | 1 |
| `loved2.py` | Follow-up of loved.py. | 2/0/0 | agent a0ae5dd5ff:127 @08:28 | 1 |
| `names.py` | Atlas name spans that produced no name. | 1/0/1 | agent a0ae5dd5ff:63 @08:27 | 1 |
| `names2.py` | Atlas name spans per row. | 1/0/0 | agent a0ae5dd5ff:71 @08:27 | 1 |
| `rereview_b/sig_names.py` | Re-review: for every built library function the atlas shows a signature for, compare parameter NAMES and qualifiers | 1/0/1 | agent a264398132:227 @15:36 | 1 |
| `s0fix/probe_types.py` | Planned signature types against the draft. | 1/0/0 | agent ad885cc048:46 @08:45 | 1 |
| `s0fix/probe_types2.py` | Follow-up of probe_types. | 1/0/0 | agent ad885cc048:50 @08:46 | 1 |
| `sig.py` | Collected signatures from the atlas manifest. | 1/0/0 | agent aadbce3a55:368 @11:26 | 1 |
| `sigtypes.py` | Planned versus declared signature types. | 0/0/3 | no write seen | 0 |
| `twincov.py` | Checked every batch A module names a twin. | 1/0/2 | agent aadbce3a55:242 @11:20 | 1 |

### Twin differential and fuzz harnesses (32)

Verb status: NEW: `agent_cli.py twin-diff` (item 12)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `adv_s5.mjs` | Adversarial cases for the bench code generator. | 1/0/1 | agent ac73c356ff:320 @11:21 | 1 |
| `fuzz_check.mjs` | Scratch differential fuzz, part 2: the live judge against practice._cadence's answers in fuzz_cases.json. | 1/0/1 | agent a44519cf9f:103 @03:35 | 1 |
| `fuzz_gen.py` | Scratch differential fuzz, part 1: random SYNTHETIC window sequences judged by practice._cadence itself. | 1/0/1 | agent a44519cf9f:101 @03:34 | 1 |
| `lowfix/tiny_diff.py` | Differential check of the two twins on ranges without a step whose ends need 0..12 decimals, and on range ends past | 1/1/2 | agent a2421b8932:461 @10:16 | 1 |
| `lowfix/tiny_run.mjs` | JS side of the tiny-range twin check. | 0/0/2 | no write seen | 0 |
| `rev_faith/gen.py` | Reviewer's adversarial synthetic sequences: Python cadence judge against the live JS judge. | 1/0/1 | agent ab384b144c:63 @03:42 | 1 |
| `rev_faith/gen2.py` | Second generator of the same. | 0/0/0 | no write seen | 0 |
| `rr3/mine.py` | Own param-schema cases (tiny ends, many decimals). | 1/0/1 | agent a00a33bdab:197 @11:14 | 1 |
| `rr3/run.mjs` | Copy of s4/run.mjs. | 0/0/0 | no write seen | 0 |
| `rr3/run_mine.py` | Ran own cases through the copied s4 differential harness. | 1/0/1 | agent a00a33bdab:197 @11:14 | 1 |
| `s1review/twin.mjs` | Scratch harness for the S1 review (JS side). | 1/0/1 | agent a61c78f420:81 @08:31 | 1 |
| `s1review/twin.py` | Python side of the module-twin comparison. | 1/0/0 | agent a61c78f420:79 @08:31 | 1 |
| `s1rr2/twin2.mjs` | JS side of the round-3 module-twin harness. | 1/0/0 | agent a9616f0195:123 @11:11 | 1 |
| `s1rr2/twin2.py` | Python side of the round-3 twin harness. | 1/0/0 | agent a9616f0195:125 @11:11 | 1 |
| `s4/diff.py` | Differential fuzz of the two param-schema twins. Reads/writes only in this scratch folder. | 1/0/1 | agent a40d259641:91 @08:30 | 1 |
| `s4/edge.py` | Edge cases for the param-schema twins. | 1/0/1 | agent a40d259641:95 @08:30 | 1 |
| `s4/fuzz.py` | Random cases for the param-schema twins. | 1/0/1 | agent a40d259641:105 @08:31 | 1 |
| `s4/run.mjs` | Differential runner: reads cases (JSON), runs each through the JS twin, writes results (JSON) with sentinels. | 1/0/1 | agent a40d259641:87 @08:30 | 1 |
| `s4fix/tiny.py` | Tiny-step cases for the param twins. | 1/0/2 | agent aa74449c20:271 @08:57 | 1 |
| `s4r/h/diff.py` | Copy of s4/diff.py. | 0/0/0 | no write seen | 0 |
| `s4r/h/edge.py` | Copy of s4/edge.py. | 0/0/0 | no write seen | 0 |
| `s4r/h/fuzz.py` | Copy of s4/fuzz.py. | 0/0/0 | no write seen | 0 |
| `s4r/h/run.mjs` | Copy of s4/run.mjs. | 0/0/0 | no write seen | 0 |
| `s4r/new.mjs` | JS side of new param cases. | 0/0/0 | no write seen | 0 |
| `s4r/new.py` | Python side of new param cases. | 1/0/1 | agent ac930879dd:101 @09:43 | 1 |
| `s4r/probe.mjs` | 1. looks adapter | 1/0/1 | agent ac930879dd:74 @09:40 | 1 |
| `s4r/probe.py` | Python probe of tiny steps in the param twin. | 1/0/1 | agent ac930879dd:82 @09:41 | 1 |
| `verify/domain.mjs` | Domain facts about the private oracle, printed as booleans. | 1/0/0 | agent a289429858:108 @03:55 | 1 |
| `verify/gaps_js.mjs` | Candidate gap fixtures through the JS judge. | 1/0/0 | agent a289429858:131 @03:58 | 1 |
| `verify/gaps_py.py` | Candidate gap fixtures through the Python judge. | 1/0/0 | agent a289429858:129 @03:58 | 1 |
| `verify/privacy_check.py` | Privacy checks on six files (booleans only). | 1/0/1 | agent a289429858:168 @04:00 | 1 |
| `verify_oracle.py` | Checked that the private oracle on disk is a faithful, current capture. | 1/0/1 | agent a44519cf9f:89 @03:32 | 1 |

### Headless browser receipts and harness drills (18)

Verb status: NEW: `arsenal/lanes/page_receipt.mjs` on `cdp.mjs` (item 10)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `corpus_smoke.mjs` | Smoke run of the shader runtime over corpus inputs (texture targets). | 0/0/4 | no write seen | 0 |
| `edge_paths.py` | Drove the headless driver over the probe page's edge paths (ok, compile failure, hang). | 1/0/2 | agent aec8bc5310:184 @06:38 | 1 |
| `flag_probe.mjs` | Which Chrome flag set gives WebGL2 on SwiftShader. | 1/0/1 | agent aec8bc5310:92 @06:30 | 1 |
| `lean_shots.mjs` | Headless receipt for the piano lean: own profile, own port, GPU lock, screenshots. | 1/2/10 | agent ac618adff1:252 @04:58 | 1 |
| `rev_ab_shots.mjs` | Reviewer's independent headless lean check in another key. | 1/6/3 | agent acf02aaaf1:50 @05:28 | 1 |
| `rr_enc.mjs` | Can a plan point src at a corpus shader in a spelling the driver's "/corpus/" test misses but the lab server serves? | 1/0/1 | agent ad3c6ae917:145 @09:28 | 1 |
| `rr_jobs.mjs` | Independent re-probe of headless.mjs's jobRefusal / planRefusal, plus lockOptions, jobWindow and mayRelaunch. | 1/0/1 | agent ad3c6ae917:130 @09:28 | 1 |
| `rr_lockwait.mjs` | Checked the driver's --lock-wait-min 0 end to end against a held private lock. | 1/0/1 | agent ad3c6ae917:166 @09:29 | 1 |
| `rr_plans.py` | Hand-written plans against headless.mjs: refused ones must exit 3 before the lock and Chrome (a nonexistent Chrome is | 1/0/1 | agent ad3c6ae917:159 @09:29 | 1 |
| `rr_probe_nogate.mjs` | Ran the harness probe page's renderer gate against a recording fake WebGL. | 0/0/1 | no write seen | 0 |
| `rr_serve_enc.py` | Does the lab server serve a corpus shader under a percent-encoded spelling of /corpus/? Synthetic temp corpus only. | 1/0/1 | agent ad3c6ae917:152 @09:28 | 1 |
| `sliceb/failpaths.py` | Live drill of the driver's failure paths on the probe page: a compile error, a page that never finishes, | 0/0/0 | no write seen | 0 |
| `sliceb/serve_drill.py` | Drill: start the lab server on a spare port and probe it. | 0/0/0 | no write seen | 0 |
| `v6/v6_shots.mjs` | w5 headless check of the lean's arch after the hook fix: G -> Ab (Ab major), D -> Eb (Eb major), B -> C (C major), Page | 0/0/1 | no write seen | 0 |
| `verify_w5b/vrun.mjs` | Independent verifier runner: drives createLean through the page's real chord reader (Theory sliced from piano.js + | 1/0/0 | agent a09e244d64:65 @06:03 | 1 |
| `w5/lean_shots.mjs` | w5 headless check of the lean's arch after the hook fix: G -> Ab (Ab major), D -> Eb (Eb major), B -> C (C major), Page | 1/0/0 | agent a994e38428:306 @05:55 | 1 |
| `w6/w6_shots.mjs` | w6 headless check of the lean after the front-line decision: (a) Ab major G4 -> Ab4, (b) Eb major D4 -> Eb4, (c) C major | 0/2/1 | agent ae128dac73:204 @06:43 | 1 |
| `x7/x7_shots.mjs` | x7: independent visual verification of the lean after the front-line decision. Cases (a) Ab major G4 -> Ab4, (b) Eb major | 1/0/1 | agent acc030a1ca:92 @06:52 | 1 |

### Adversarial review and fix-lane probes (81)

Verb status: scratch; promote re-run probes to pins (item 13)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `cmp_chunks.mjs` | Compared bench code chunks between the Python and JS readers. | 1/0/2 | agent a1668c1485:163 @10:12 | 1 |
| `effect.js` | Not a script: an 11-byte HTTP error body saved with a .js name. | 0/0/0 | no write seen | 0 |
| `labgpu/closure_scan.mjs` | Closure cost of library modules through the workbench's code. | 1/0/0 | agent a2688a47ec:693 @12:23 | 1 |
| `labgpu/sha_parity.mjs` | Does the Workbench's library (modlib.loadLibrary over the lab server's /glsl/index.json, as workbench.js now loads it) | 1/0/1 | agent a2688a47ec:686 @12:23 | 1 |
| `lean_probe/cases.mjs` | C major baseline | 1/0/0 | agent a1e963bbd9:80 @05:30 | 1 |
| `lean_probe/cases2.mjs` | dim7 inversions in C major (viio7 borrowed) | 1/0/0 | agent a1e963bbd9:104 @05:31 | 1 |
| `lean_probe/cases3.mjs` | w5 pins, through the page's real reader | 1/0/1 | agent a994e38428:266 @05:53 | 1 |
| `lean_probe/probe.mjs` | Hold one chord for `hold` seconds at 60 fps, return the frame summary | 1/3/0 | agent a1e963bbd9:71 @05:29 | 2 |
| `oracle_unchanged.mjs` | Checked a bench page against its pre-change copy. | 1/0/1 | agent a1668c1485:248 @10:14 | 1 |
| `params_check.mjs` | Built each group's generated controls with a fake document and checked them. | 1/0/1 | agent a7b61872f9:231 @13:51 | 1 |
| `parse_page.mjs` | Parsed a bench page's inline scripts. | 1/0/3 | agent a1668c1485:240 @10:14 | 1 |
| `probe_stage.mjs` | Adversarial probe of the workbench stage module (read-only import). | 1/0/5 | agent ac9183bbac:99 @13:49 | 1 |
| `rereview/assemble.py` | Assembled a test harness from the house test fakes for a probe. | 1/0/2 | agent a9d6f75591:217 @17:48 | 1 |
| `rereview/dump_composed.py (deleted)` | Composed every fixture shader the current test builds and dumped them to scratch JSON. | 1/0/0 | agent a3c7ec96e9:125 @09:29 | 1 |
| `rereview/evidence_compare.py (deleted)` | Compared how original and current positive fixtures are detected, tag by tag. | 1/0/1 | agent a3c7ec96e9:176 @09:33 | 1 |
| `rereview/held_run.py` | Ran the held-tail probe with the house fakes. | 1/0/1 | agent a9d6f75591:307 @17:54 | 1 |
| `rereview/held_tail.mjs` | Probe: a live run held, then a library pick. | 1/0/2 | agent a9d6f75591:305 @17:54 | 1 |
| `rereview/house_probe.py (deleted)` | Re-ran the licence-line measurement over the dissector's four files, original against current (counts only). | 1/0/0 | agent a3c7ec96e9:81 @09:25 | 1 |
| `rereview/indep.py (deleted)` | Independent corpus-overlap measure with its own tokenizer, strict and loose modes (counts only). | 2/0/2 | agent a3c7ec96e9:97 @09:27 | 1 |
| `rereview/pin_on_orig.py (deleted)` | Ran the fixer's pin against the original four files, then the current ones. | 1/0/1 | agent a3c7ec96e9:159 @09:32 | 1 |
| `rereview/probe_tail.mjs` | Independent re-review probes of the workbench; scenarios differ from the pins on purpose. | 1/0/0 | agent a9d6f75591:209 @17:47 | 1 |
| `rereview/renamed_vs_orig.py (deleted)` | For each run the current test shares with the corpus once names are erased, checked whether the original held it too. | 1/0/1 | agent a3c7ec96e9:118 @09:28 | 1 |
| `rereview/s3_full.mjs` | S3 in full: every row, for a side-by-side table. | 1/0/0 | agent a9d6f75591:227 @17:49 | 1 |
| `rereview/s3_table.py` | Side-by-side table of probe S3. | 1/0/1 | agent a9d6f75591:229 @17:49 | 1 |
| `rereview/wb_run.py` | Ran the workbench probe with the house fakes. | 1/0/1 | agent a9d6f75591:239 @17:51 | 1 |
| `rereview/wb_tail.mjs` | Workbench level: a live run stalls, then a Library row is picked. Which receipt does the Inspector show? | 1/0/0 | agent a9d6f75591:237 @17:51 | 1 |
| `rev/alloc.mjs` | Allocation probe of the lean module under GC. | 1/0/0 | agent ac83b7439a:150 @05:33 | 1 |
| `rev/alloc_a.mjs` | Variant of the allocation probe. | 0/0/0 | no write seen | 0 |
| `rr/mut/toy-runtime.orig.js` | arsenal/web/shaderlab/toy-runtime.js -- the house's own runtime for the public Shadertoy interface. | 0/0/0 | no write seen | 0 |
| `rr/probe_chtime.mjs` | Probed channel time inputs of the runtime on four corpus shaders (ids only). | 1/0/2 | agent af4b397886:324 @09:38 | 1 |
| `rr/probe_order.mjs` | Re-review probes: no corpus text printed, only ids/keys/counts. | 1/0/0 | agent af4b397886:78 @09:25 | 1 |
| `rr3/rt_widen.py` | Swapped the param twin's grid for an older one. | 1/0/0 | agent a00a33bdab:230 @11:17 | 1 |
| `rr3/s0_out.py` | Printed probe S0 output. | 1/0/0 | agent a00a33bdab:93 @11:10 | 1 |
| `rr3/s0_probe.py` | Re-review probe S0. | 1/0/0 | agent a00a33bdab:74 @11:09 | 1 |
| `rr_probe.mjs` | Re-review probe of the workbench stage after the lab-safety fix. | 2/0/3 | agent a0895e9b15:148 @15:38 | 2 |
| `rr_probe2.mjs` | Second version of that probe. | 2/0/1 | agent a0895e9b15:155 @15:39 | 1 |
| `rr_probe3.mjs` | Third version. | 1/0/0 | agent a0895e9b15:192 @15:42 | 1 |
| `rr_probe3_old.mjs` | Third version run against the old stage. | 0/0/1 | no write seen | 0 |
| `rr_probe4.mjs` | Fourth version. | 1/0/0 | agent a0895e9b15:226 @15:44 | 1 |
| `rr_probe5.mjs` | Fifth version. | 1/0/0 | agent a0895e9b15:234 @15:45 | 1 |
| `s0rr/probe1.py` | Re-review probes for slice S0: reproduce each original defect probe against the fixed converter. | 1/0/1 | agent a398ba48bc:77 @09:40 | 1 |
| `s0rr/probe2.py` | Probes: ledger/manifest splits, recipe bullet malformation, latent plan_types crashes. | 1/0/1 | agent a398ba48bc:86 @09:40 | 1 |
| `s0rr/probe3.py` | Independent closure scan: every capitalised identifier used in a code span of a primitive row's signature cell, | 1/0/1 | agent a398ba48bc:94 @09:41 | 1 |
| `s0rr/probe4.py` | Latent probes on the new ruling-(a) code: does the rule hold for shapes a revised draft could plausibly take? | 1/0/3 | agent a398ba48bc:129 @09:43 | 1 |
| `s0rr/probe5.py` | Closure-on-every-build probes. | 1/0/2 | agent a398ba48bc:156 @09:44 | 1 |
| `s1fix/exp1_noprint.py` | Experiment 1 without prints. | 0/0/2 | no write seen | 0 |
| `s1review/c.mjs` | Fake fetch for loading the library in Node. | 0/0/0 | no write seen | 0 |
| `s1review/exp1.py` | Review experiment 1 on the module core. | 1/0/0 | agent a61c78f420:85 @08:31 | 1 |
| `s1review/exp2.py` | Review experiment 2. | 1/2/0 | agent a61c78f420:97 @08:32 | 1 |
| `s1review/exp3.py` | Review experiment 3. | 1/0/0 | agent a61c78f420:122 @08:33 | 1 |
| `s1review/exp4.py` | Review experiment 4. | 0/0/0 | no write seen | 0 |
| `s1rr/load.mjs` | Re-review of S1 defect 3: the page loader, lenient and strict, over a fake fetch. | 1/0/1 | agent aa09f82748:81 @09:42 | 1 |
| `s1rr/p2.mjs` | JS probe 2 with a fake fetch. | 0/0/0 | no write seen | 0 |
| `s1rr/p3.mjs` | JS probe 3. | 0/0/0 | no write seen | 0 |
| `s1rr/probe1.py` | Re-review probe 1 of the module core. | 1/0/0 | agent aa09f82748:70 @09:41 | 1 |
| `s1rr/probe2.py` | Probe 2 (writes a JS harness). | 1/0/0 | agent aa09f82748:87 @09:42 | 1 |
| `s1rr/probe3.py` | Probe 3. | 1/0/0 | agent aa09f82748:93 @09:43 | 1 |
| `s1rr/probe4.py` | Probe 4. | 1/0/1 | agent aa09f82748:120 @09:44 | 1 |
| `s1rr2/p2.mjs` | Copy of s1rr/p2.mjs. | 0/0/0 | no write seen | 0 |
| `s1rr2/p3.mjs` | Copy of s1rr/p3.mjs. | 0/0/0 | no write seen | 0 |
| `s1rr2/probe2.py` | Copy of s1rr/probe2.py. | 0/0/0 | no write seen | 0 |
| `s1rr2/probe4.py` | Copy of s1rr/probe4.py. | 0/0/0 | no write seen | 0 |
| `s1rr2/probe_a.py` | Round-3 probe A. | 1/0/0 | agent a9616f0195:129 @11:12 | 1 |
| `s1rr2/probe_b.py` | Round-3 probe B. | 1/0/0 | agent a9616f0195:144 @11:12 | 1 |
| `s1rr2/real_response.mjs` | Re-review round 3, S1: loadLibrary through a REAL Response (Node's undici), not a shim. | 1/0/0 | agent a9616f0195:146 @11:13 | 1 |
| `s4/probe.mjs` | 1. tiny steps | 1/0/1 | agent a40d259641:112 @08:32 | 1 |
| `s4/ui.mjs` | A range input clamps its value to [min, max] like a browser does. | 1/0/2 | agent a40d259641:149 @08:33 | 1 |
| `s4r/drag.mjs` | A note key held on the page, then a pointer drag on the slider: the held key's auto-repeat keydowns now land on the | 1/0/1 | agent ac930879dd:137 @09:45 | 1 |
| `s4r/ui.mjs` | A range input clamps and snaps to its step grid from min, as the HTML spec says (value sanitisation). | 1/0/1 | agent ac930879dd:94 @09:42 | 1 |
| `shaders/brave_shadertoy_urls.py (deleted)` | Harvest helper: listed Shadertoy URLs from the local browser's session state (deleted; not opened here). | 1/0/0 | main:1987 @05:59 | 1 |
| `types.py (deleted)` | Found capitalised type names in atlas signatures. | 1/0/0 | agent a0ae5dd5ff:85 @08:27 | 1 |
| `verify_w5b/vcases.mjs` | Cases for the lean verifier. | 1/0/0 | agent a09e244d64:76 @06:04 | 1 |
| `verify_w5b/win.mjs` | Hold-time sweep for the lean. | 0/0/0 | no write seen | 0 |
| `vfx-codegen.keep.js` | Kept copy of the bench code generator, for comparison. | 0/0/1 | no write seen | 0 |
| `w5/alloc.mjs` | Allocation probe of the boxed lean. | 1/0/0 | agent a994e38428:180 @05:49 | 1 |
| `w5/alloc_big.mjs` | Bigger allocation probe. | 0/0/0 | no write seen | 0 |
| `w5/alloc_ns.mjs` | Allocation probe without sampling. | 0/0/0 | no write seen | 0 |
| `w6/draw.py` | Drew candidate arch anchors from a JSON model with PIL. | 1/0/0 | agent ae128dac73:61 @06:28 | 1 |
| `w6/model.mjs` | Exploration model: feet + arch under candidate anchors and lift schemes, the test's stand-in camera. Writes JSON for PIL. | 1/0/0 | agent ae128dac73:57 @06:27 | 1 |
| `wf_fix_round_next.js` | Workflow script for the next fix-then-re-review round. | 1/0/1 | main:5743 @18:12 | 1 |
| `x7/golden_check.mjs` | Independent check of the byte-identical pin: run the test's own painter harness (sliced from tests/piano_lean.test.mjs) | 1/0/1 | agent acc030a1ca:73 @06:49 | 1 |

### Scripted edits of repo source (10)

Verb status: none needed: Edit tool (item 5)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `aurora-fix/rewrap.py` | Scratch: fix the few overlong lines I introduced (exact replacements, LF kept). | 1/0/2 | agent afaf271492:1085 @15:22 | 1 |
| `edit_hex1.py` | Scripted replacements in the hex-neon recipe and card. | 1/0/1 | agent a3084eb892:521 @13:18 | 1 |
| `edit_hex2.py` | Second round of the same. | 1/0/3 | agent a3084eb892:542 @13:19 | 1 |
| `eol.py` | Counted CRLF and LF in a slice's files; fixed CRLF with --fix. | 1/0/1 | agent ae69fc909d:741 @11:10 | 1 |
| `fix_cards.py` | Scripted fixes of batch-A cards. | 1/0/1 | agent a35553e7dc:457 @10:56 | 1 |
| `patch_cards.py` | Scripted edits of colour cards. | 1/0/1 | agent ae69fc909d:598 @11:01 | 1 |
| `patch_css.py` | Scripted CSS edits for the workbench. | 1/0/1 | agent ad060ac808:752 @10:35 | 1 |
| `patch_shelf.py` | Scripted edits of the shelf page. | 2/0/1 | agent ad060ac808:664 @10:33 | 1 |
| `rr_patch.py` | Patched a scratch probe (rr_overlap.py) in place. | 1/0/1 | agent ad3c6ae917:238 @09:33 | 1 |
| `sub.py` | Applied exact string replacements from an edits.json, each old string required once. | 1/0/9 | agent a3084eb892:563 @13:20 | 1 |

### Scripted edits of docs and study notes (13)

Verb status: none needed: Edit tool (item 5)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `append_corrob.py` | Appended a dated corroboration section to seven study notes. | 1/3/1 | agent ad068b3b0a:223 @14:23 | 1 |
| `common.py` | Shared text for the RE playbook edits. | 2/0/0 | agent a6001de7ff:60 @18:13 | 2 |
| `corr1_append.py` | Appended a corroboration section to a study note, LF only. | 1/0/7 | agent a4e374169c:97 @14:12 | 1 |
| `edit_archero.py` | Scripted edit of an RE report section (game design). | 1/0/1 | agent a3f10f9557:282 @14:56 | 1 |
| `edit_audio.py` | Scripted edit of the RE audio report section. | 1/0/1 | agent a3f10f9557:268 @14:55 | 1 |
| `edit_games.py` | Scripted edit of the RE games report section. | 1/0/1 | agent a3f10f9557:275 @14:56 | 1 |
| `edit_gfx.py` | Scripted edit of the RE graphics report section. | 1/0/1 | agent a3f10f9557:261 @14:55 | 1 |
| `edit_hw.py` | Scripted edit of the RE hardware report section. | 1/0/1 | agent a3f10f9557:296 @14:57 | 1 |
| `edit_practice.py` | Scripted edit of the RE practice-drills section. | 1/0/1 | agent a3f10f9557:242 @14:54 | 1 |
| `edit_research.py` | Scripted edit of the RE research section. | 1/0/1 | agent a3f10f9557:303 @14:57 | 1 |
| `edit_sb.py` | Scripted edit of the RE software-and-binaries section. | 1/0/1 | agent a3f10f9557:249 @14:54 | 1 |
| `edit_web.py` | Scripted edit of the RE web section. | 1/0/1 | agent a3f10f9557:289 @14:56 | 1 |
| `mlc_edit.py` | Scripted edit of the RE method, legal and clean-room note. | 1/1/1 | agent a3f10f9557:217 @14:52 | 1 |

### Transcript mining (11)

Verb status: EXISTS: `agent_cli.py eye find` (item 14)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `dump.py` | Printed the extracted turns of chosen sessions. | 1/0/7 | agent a799cc2219:73 @06:34 | 1 |
| `extract_discord.py` | Extracted operator bus and Discord chat lines from transcripts. | 1/0/1 | agent a799cc2219:286 @06:40 | 1 |
| `extract_human.py` | Extracted operator turns from session transcripts into a JSONL (read-only). | 1/0/1 | agent a799cc2219:38 @06:33 | 1 |
| `extract_human2.py` | Same, including list-content turns with images. | 1/0/2 | agent a799cc2219:87 @06:35 | 1 |
| `extract_queued.py` | Extracted operator messages typed mid-turn (queued commands) into the same JSONL. | 1/0/2 | agent a799cc2219:243 @06:39 | 1 |
| `imgturns.py` | Listed operator turns that carried images. | 1/0/1 | agent a799cc2219:110 @06:36 | 1 |
| `prose.py` | Printed only the prose lines of long operator turns that pasted code. | 1/0/3 | agent a799cc2219:131 @06:36 | 1 |
| `search.py` | Regex search over the extracted operator turns. | 1/0/4 | agent a799cc2219:48 @06:34 | 1 |
| `search2.py` | Same, with include and exclude session lists. | 1/0/3 | agent a799cc2219:149 @06:36 | 1 |
| `search_d.py` | Same, over bus and Discord lines. | 0/0/1 | no write seen | 0 |
| `search_q.py` | Same, over queued messages. | 0/0/1 | no write seen | 0 |

### Web and source verification (4)

Verb status: EXISTS: `agent_cli.py web fetch` (gap: `--grep`, item 15)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `fc/oa.py` | Printed a paper record (abstract rebuilt from its inverted index) for a research lane. | 1/0/0 | agent aa458d44d6:218 @02:37 | 1 |
| `grab.py` | Fetched a page with urllib, stripped tags and printed windows around regex matches (quote verification). | 1/0/12 | agent ad2827ea2c:126 @13:01 | 1 |
| `pkgcheck.py` | Checked which optional analysis packages are importable. | 1/0/1 | agent a0072505a7:198 @13:01 | 1 |
| `urlcheck.py` | Checked that cited source URLs resolve, through the house web door. | 1/0/1 | agent a0072505a7:330 @13:07 | 1 |

### Bus, store and identity probes (15)

Verb status: PARTLY: `trace`, `events`, `locks`, `mailbox` (item 17)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `atoms2.py` | Counted drafts by month and origin. | 1/0/0 | agent a9d5013b74:75 @13:36 | 1 |
| `atoms_vs_proj.py` | Compared atoms against their projection files. | 1/0/1 | agent a9d5013b74:71 @13:36 | 1 |
| `fleet_identity_probe.py` | Read-only probe for the fleet-and-identity teardown card. | 1/0/2 | agent a93375b9f5:379 @13:48 | 1 |
| `house/h13_probe.py` | Compared durable-family keys in Redis with the SQLite durable tier (read-only). | 1/0/1 | agent a250e4298e:112 @14:03 | 1 |
| `probe_authors.py` | Tallied lesson authors against the ACL (read-only). | 1/0/0 | agent a28471838e:313 @13:26 | 1 |
| `probe_kimi.py` | Counted lessons by agent id for a few seats. | 1/0/1 | agent a28471838e:320 @13:26 | 1 |
| `probe_locks.py` | Read-only TTL/TYPE/GET over lock keys. | 1/0/1 | agent a28471838e:293 @13:25 | 1 |
| `probe_senders.py` | Read-only XREVRANGE over bus streams, tallied by sender against the ACL. | 1/0/0 | agent a28471838e:307 @13:26 | 1 |
| `probe_trace.py` | Read-only look at the broadcast stream keys. | 1/0/1 | agent a28471838e:212 @13:22 | 1 |
| `probe_trace2.py` | Read-only look at the trace ring. | 1/0/0 | agent a28471838e:224 @13:23 | 1 |
| `probe_trace3.py` | Searched the trace ring for a double-fire signature. | 1/0/0 | agent a28471838e:273 @13:24 | 1 |
| `probe_trust.py` | Resolved trust grants for several agent ids (read-only). | 1/0/0 | agent a28471838e:188 @13:22 | 1 |
| `status_drift.py` | Compared document status fields across the store's JSONL files. | 1/0/0 | agent a9d5013b74:266 @13:41 | 1 |
| `store_only.py` | Listed ids present only in the store files. | 1/0/1 | agent a9d5013b74:270 @13:41 | 1 |
| `teardown_probe.py` | Read-only probes for the bus-and-seats teardown card (fake Redis for writes). | 1/0/2 | agent abe518737c:229 @13:23 | 1 |

### Reverse-engineering report worked examples (22)

Verb status: EXISTS later for PE triage: `py -m arsenal re triage`; the rest are report receipts (scratch)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `appendix_A.py` | Decoded a MIDI controller's captured USB descriptors (hardware report appendix). | 0/0/0 | no write seen | 0 |
| `appendix_B.py` | Synthesised a MIDI serial waveform and decoded it back (hardware report appendix). | 0/0/0 | no write seen | 0 |
| `appendix_C.py` | Toy firmware image: signatures and block entropy (hardware report appendix). | 0/0/1 | no write seen | 0 |
| `diff_format.py` | "Change one knob, diff the bytes" demo on files the house made. | 1/0/1 | agent ad2827ea2c:326 @13:08 | 1 |
| `firmware_entropy_demo.py` | Toy firmware image with a signature and block-entropy scan. | 1/3/2 | agent a619f83210:427 @13:13 | 1 |
| `games_teardown_math.py` | Arithmetic for the games design-teardown report. | 1/0/1 | agent a35408403d:301 @13:08 | 1 |
| `midi_wire_demo.py` | Built a MIDI wire-level signal from scratch to show what an analyser sees. | 1/0/1 | agent a619f83210:425 @13:12 | 1 |
| `re_audio_demo/appendix_check/demo_appendix.py` | Appendix copy of the audio demonstrations, for a re-check. | 0/0/0 | no write seen | 0 |
| `re_audio_demo/b_check.py` | Tested one hypothesis about demo B's reverb estimate. | 0/0/0 | no write seen | 0 |
| `re_audio_demo/demo.py` | Closed-loop audio demonstrations on house-made sound (audio report). | 1/11/2 | agent a8aabe0ed4:282 @13:07 | 1 |
| `re_examples.py` | Worked examples for the software-and-binaries report, on files the house made. | 1/0/1 | agent a986eff7c6:305 @13:07 | 1 |
| `re_examples2.py` | Follow-up static checks for the same report. | 1/3/3 | agent a986eff7c6:313 @13:07 | 1 |
| `re_gfx/aurora_lookread.py` | Read a house frame's look from pixels and graded the reading against the source. | 1/0/0 | agent a49696fb21:259 @13:07 | 1 |
| `re_gfx/synthetic_rulers.py` | Calibrated measuring tools on looks with known truth. | 1/0/0 | agent a49696fb21:296 @13:11 | 1 |
| `re_gfx/tblcheck.py` | Checked the Markdown tables of a report. | 1/0/2 | agent a49696fb21:447 @13:24 | 1 |
| `re_practice/drills.py` | Four teardown drills on house-made artifacts (analyst side). | 1/2/0 | agent ad5a673946:374 @13:09 | 1 |
| `re_practice/hidden_blackbox.py` | Target side of those drills. | 1/0/0 | agent ad5a673946:370 @13:09 | 1 |
| `re_web/css_tokens.py` | Design-token inventory from shipped CSS. | 1/0/0 | agent a5ea776d6b:229 @13:04 | 1 |
| `re_web/fit_bezier.py` | Recovered a CSS easing curve from measured positions. | 1/0/0 | agent a5ea776d6b:273 @13:06 | 1 |
| `re_web/har_triage.py` | Endpoint and timing inventory of a HAR file, with a secret sweep before sharing. | 1/1/0 | agent a5ea776d6b:258 @13:05 | 1 |
| `triage_pe.py` | Read-only first look at a PE file; preceded the `py -m arsenal re triage` verb. | 1/1/2 | agent ad2827ea2c:301 @13:08 | 1 |
| `usb_midi_topology.py` | Decoded a MIDI controller's captured USB descriptors (hardware worked example). | 1/0/1 | agent a619f83210:423 @13:12 | 1 |

### Numeric and maths checks (32)

Verb status: scratch

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `aurora_numbers.py` | Numbers for an aurora glow transfer curve (study arithmetic). | 1/0/1 | agent aa430f7151:101 @06:27 | 1 |
| `batchb_fix/shadow_repro.py` | Reproduced a soft-shadow defect on a floor scene. | 1/0/3 | agent a4fc73a8b2:209 @14:12 | 1 |
| `batchb_fix/shadow_trace.py` | Traced the soft-shadow loop step by step. | 1/0/1 | agent a4fc73a8b2:240 @14:14 | 1 |
| `batchb_fix/shadow_variants.py` | Compare guard variants for visSoftShadow's triangulation on open floors and the probe's ball scene. | 1/0/2 | agent a4fc73a8b2:246 @14:14 | 1 |
| `check_geo.py` | Icosahedron angle check. | 1/0/0 | agent a06209fd4c:51 @06:26 | 1 |
| `check_iso.py` | Periodicity check of a smooth-repeat function. | 1/0/0 | agent a06209fd4c:55 @06:26 | 1 |
| `check_snippet.py` | Ran a proposed snippet and its pin, extracted from a Markdown note, against the repo. | 1/1/2 | agent a1668c1485:283 @10:16 | 1 |
| `check_td.py` | Probability and visibility checks for a study note. | 1/0/0 | agent aae122e0d4:33 @06:26 | 1 |
| `check_td2.py` | Shell-visibility fraction check for the same note. | 1/0/0 | agent aae122e0d4:37 @06:27 | 1 |
| `check_td3.py` | Distance-function check for the same note. | 1/0/1 | agent aae122e0d4:45 @06:28 | 1 |
| `check_td4.py` | Follow-up of check_td3 at three times. | 1/0/1 | agent aae122e0d4:49 @06:29 | 1 |
| `chk1.py` | Checked an antipode artefact. | 0/0/2 | no write seen | 0 |
| `corr.py` | Correlation check of a noise function over random points. | 1/0/1 | agent af450251ba:105 @11:45 | 1 |
| `ffg_curl.py` | Vector arithmetic check for a study note. | 1/0/2 | agent aa430f7151:135 @06:33 | 1 |
| `glsl_algo.py` | OKLab reference arithmetic. | 1/0/0 | agent ae69fc909d:236 @10:36 | 1 |
| `hashprobe.py` | CPU probe of how a dither hash and float32 time behave over long uptime. | 2/0/0 | agent a598372d41:290 @06:47 | 1 |
| `hexcheck.py` | Checked a hex-grid edge function against the true hex cell. | 1/0/0 | agent a5cf6a1202:322 @06:53 | 1 |
| `icosa_proto.py` | Prototype of an icosahedral reflection group. | 1/0/3 | agent ad751e633f:263 @11:57 | 1 |
| `mathcheck.py` | Rotation-constant and related maths checks. | 1/0/0 | agent a5cf6a1202:356 @06:57 | 1 |
| `oracle.py` | Reference implementation of a PCG hash for pins. | 1/0/2 | agent a433896f45:176 @10:35 | 1 |
| `piano_ref.py` | OKLCH reference values. | 1/0/2 | agent ae69fc909d:232 @10:35 | 1 |
| `pins.py` | Reference values for a hash function at chosen cells. | 1/0/0 | agent af450251ba:161 @11:50 | 1 |
| `proto.py` | Prototype of a 3D integer hash. | 1/0/1 | agent a433896f45:181 @10:36 | 1 |
| `relaxed_check.py` | Checked a relaxed ray marcher against a half-space wall. | 1/0/4 | agent a1bad7126e:365 @13:59 | 1 |
| `rereview_b/env_energy.py` | Re-review: key-panel energy over the sphere against roughness for several rimBright and box sizes (the fixed twin), | 1/0/1 | agent a264398132:154 @15:33 | 1 |
| `rereview_b/penumbra_compare.py` | Compared shipped and pre-fix soft-shadow penumbras. | 1/1/4 | agent a264398132:94 @15:31 | 1 |
| `rereview_b/relaxed_fuzz.py` | Re-review fuzz of the fixed rmRelaxed twin against rmSphereTrace: random scenes of balls, boxes, slabs and planes, | 1/0/1 | agent a264398132:123 @15:32 | 1 |
| `rereview_b/shadow_sweep.py` | Re-review sweep of the fixed soft-shadow twin on open floors and tilted planes. | 1/0/1 | agent a264398132:82 @15:30 | 1 |
| `shadow_card_numbers.py` | Soft-shadow numbers at several light elevations for a card note. | 1/0/4 | agent a1bad7126e:407 @14:03 | 1 |
| `shadow_check.py` | Checked a patched soft-shadow trace. | 1/0/2 | agent a1bad7126e:349 @13:58 | 1 |
| `spot.py` | Gradient peak search check. | 1/0/1 | agent aadbce3a55:154 @11:17 | 1 |
| `tm_table.py` | Tone-map and OKLab table check. | 1/0/0 | agent a92c526c12:249 @06:48 | 1 |

### Piano and story-layer probes (10-12 night) (21)

Verb status: scratch

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `content/piano-timing/isolated.py` | Timing check of isolated notes; reads another session's scratchpad. | 1/0/1 | main:191 @13:12 | 1 |
| `content/piano-timing/jumps.py` | Timing jumps between segments; reads another session's scratchpad. | 1/0/1 | main:166 @13:10 | 1 |
| `content/piano-timing/truth.py` | Onset truth from audio energy rises. | 1/0/1 | main:215 @13:14 | 1 |
| `content/story/page_data.js` | Data file for a private story page (generated). | 0/0/1 | no write seen | 0 |
| `content/story/page_data.py` | Extracted data for a private story page from state/. | 1/0/1 | main:1040 @03:47 | 1 |
| `content/story/readback.py` | Read one practice session back the way the story page does. | 1/0/2 | main:1532 @04:51 | 1 |
| `content/story/voicing_trend.py` | Tested a voicing hypothesis across practice sessions. | 1/0/2 | main:1581 @05:09 | 1 |
| `content/story/w2_audience_probe.py` | Read-only probe of one practice session for the story-layer design. | 1/0/1 | agent aaeb3dc71c:94 @02:52 | 1 |
| `content/story/w2_audience_probe_budget.py` | Read-only budget probe over all practice sessions. | 1/0/1 | agent aaeb3dc71c:158 @03:03 | 1 |
| `content/story/w2_audience_probe_home.py` | Read-only probe: does home stay sounding while the bass moves. | 1/0/3 | agent aaeb3dc71c:116 @02:54 | 1 |
| `content/story/w2_audience_probe_moves.py` | Near-copy of the previous probe. | 0/0/3 | no write seen | 0 |
| `content/story/w2_audience_probe_offline.py` | Read-only probe of the departure window for logged cadences. | 1/0/1 | agent aaeb3dc71c:109 @02:53 | 1 |
| `content/story/w2_audience_probe_rub.py` | Read-only probe of leading-tone and home overlap. | 1/0/2 | agent aaeb3dc71c:131 @02:56 | 1 |
| `grammar_probe.py` | Printed one practice session's analysis summary (piano story layer). | 1/0/4 | agent a258c84a28:133 @02:16 | 1 |
| `idiom_corpus.py` | Ran that probe across all sessions. | 1/0/1 | agent aad8d064a6:141 @02:57 | 1 |
| `idiom_probe.py` | Probed logged practice sessions for recurring idioms. | 2/0/2 | agent aad8d064a6:106 @02:53 | 1 |
| `judge_tis.py` | Small tonal-interval check. | 1/0/2 | agent a21f74a2ab:75 @03:17 | 1 |
| `settle_proto.py` | Prototype of the live settle rule replayed on logged chord events. | 1/0/1 | agent aad8d064a6:184 @02:59 | 1 |
| `t_attr.py` | Tonal attraction values built on t_tps.py. | 1/0/0 | agent a5d3213c60:291 @02:30 | 1 |
| `t_tps.py` | Tonal-pitch-space distance within one region (music-theory check). | 1/0/0 | agent a5d3213c60:276 @02:29 | 1 |
| `t_tps2.py` | Shortest-path tonal-pitch-space distance across regions. | 1/0/0 | agent a5d3213c60:295 @02:32 | 1 |

### Harness questions (2)

Verb status: doc (item 19)

| script | what it did | W/E/R | first write | writers |
|---|---|---|---|---|
| `cli_grep.py` | Searched the installed Claude Code package for strings (how a subagent's environment is set). | 1/0/5 | agent a0034023d0:69 @16:01 | 1 |
| `cli_re.py` | Regex search over the same package with a match window. | 1/0/9 | agent a0034023d0:85 @16:02 | 1 |

### Copies of repo files, backups and mirrored copies (67): listed, not analysed

`batchb_fix/mutant_lib/modlib.js`, `batchb_fix/mutant_rays_lib/modlib.js`, `cache_real_7btq2299/code/corpus.py`, `cache_real_7btq2299/code/dissect.py`, `cache_real_7btq2299/code/explain.py`, `cache_real_7btq2299/code/glsl.py`, `cache_real_7btq2299/code/shelf.py`, `demo-lib/glsl/modlib.js`, `dissector/orig/census.py`, `dissector/orig/dissect.py`, `dissector/orig/glsl.py`, `dissector/orig/test_shader_dissect.py`, `fringe-fix/oldlib/glsl/modlib.js`, `headpins/test_glsl_modules_head.py`, `labgpu/stage.js`, `labgpu/stage.new.js`, `labgpu/workbench.js`, `labsafety-backup/common.js`, `labsafety-backup/lab.js`, `labsafety-backup/lab_shot.mjs`, `labsafety-backup/serve.py`, `labsafety-backup/shelf.js`, `labsafety-backup/stage.js`, `labsafety-backup/stage_cards_section.js`, `labsafety-backup/stage_head.js`, `labsafety-backup/stage_panel.js`, `labsafety-backup/test_shader_serve_routes.py`, `labsafety-backup/workbench.js`, `labsafety-backup/workbench_lab.test.mjs`, `ref/effect_amoham.js`, `ref/effect_sm.js`, `ref/effect_talkol.js`, `ref/page16.js`, `rereview_b/mutant_lib/modlib.js`, `rereview_b/mutant_rays_lib/modlib.js`, `rev/lean_a.js`, `rr/mut/render.orig.js`, `s0fix/atlas.before.py`, `s0fix/atlas_build.before.py`, `s1fix2/glsl_modlib_parity.mjs`, `s1fix2/modlib.js`, `s1fix2/modlib_candidate.js`, `s1fix2/modlib_candidate2.js`, `s1fix2/modules.py`, `s1fix2/test_glsl_index.py`, `s1fix2/test_glsl_modules.py`, `s1review/old_modules.py`, `s1rr2/mut_modules.py`, `verify/orig.js`, `viewonly-backup/arsenal__shaders__lab_shot.mjs`, `viewonly-backup/arsenal__web__lib__workbench__inspector.js`, `viewonly-backup/arsenal__web__lib__workbench__stage.js`, `viewonly-backup/arsenal__web__lib__workbench__strip.js`, `viewonly-backup/arsenal__web__lib__workbench__workbench.js`, `viewonly-backup/arsenal__web__shaderlab__lab.js`, `viewonly-backup/probes/rr_probe.mjs`, `viewonly-backup/probes/rr_probe2.mjs`, `viewonly-backup/probes/rr_probe3.mjs`, `viewonly-backup/probes/rr_probe4.mjs`, `viewonly-backup/probes/rr_probe5.mjs`, `viewonly-backup/stage_panel.js`, `viewonly-backup/tests__workbench_lab.test.mjs`, `w5/lean_boxed.js`, `w5/lean_boxed.test.mjs`, `w6/t_detail.mjs`, `x7/piano_now.js`, `x7/piano_pre_decision.js`


### Generated mutant copies (67)

`mutant_0.mjs` to `mutant_46.mjs` (47, made by `mutate.mjs`), `m0.mjs` to `m12.mjs` (13, made by `mutants.mjs`), and 7 `rev_faith/m_*.mjs`.


Excluded as this retro's own files (86): `scan.py`, `first_mention.py`, `inj_cmd.py`, `inj_rate.py`, `inj_rate2.py`, `inj_readonly.py`, `inj_reconcile.py`, `inj_scan.py`, `lgrep.py`, `pass2.py`, `pass3.py`, `pass4.py`, `pat_scan.py`, `tx_index.py`, `tx_lines.py`, `an1.py`, `an10.py`, `an11.py`, `an12.py`, `an13.py`, `an14.py`, `an15.py`, `an2.py`, `an3.py`, `an4.py`, `an5.py`, `an6.py`, `an7.py`, `an8.py`, `an9.py`, `extract.py`, `list.py`, `peek.py`, `peek2.py`, `probe_err.py`, `retro-ghb/count.py`, `retro-ghb/scan.py`, `retro-ghb/stops.py`, `retro-ghb/view.py`, `retro-ghb/wake.py`, `retro-ghb/wakeout.py`, `retro-lane-main/b1.py`, `retro-lane-main/br.py`, `retro-lane-main/ctx.py`, `retro-lane-main/gc.py`, `retro-lane-main/hd.py`, `retro-lane-main/hk.py`, `retro-lane-main/mx_extract.py`, `retro-lane-main/pgrep.py`, `retro-lane-main/q.py`, `retro-lane-main/q2.py`, `retro-lane-main/raw.py`, `retro-lane-main/rr.py`, `retro-lane-main/rt.py`, `retro-lane-main/seq.py`, `retro-lane-main/sz.py`, `retro-lane-main/tok.py`, `retro-lane-main/ww.py`, `retro-late-lane/an1.py`, `retro-late-lane/an2.py`, `retro-late-lane/an3.py`, `retro-late-lane/an4.py`, `retro-late-lane/an5.py`, `retro-late-lane/att.py`, `retro-late-lane/briefs.py`, `retro-late-lane/ctx.py`, `retro-late-lane/dur.py`, `retro-late-lane/extract.py`, `retro-late-lane/glob.py`, `retro-late-lane/nz.py`, `retro-late-lane/orient.py`, `retro-late-lane/recov.py`, `retro-late-lane/red.py`, `retro-late-lane/rep.py`, `retro-late-lane/scripts_cat.py`, `retro/a1.py`, `retro/a2.py`, `retro/a3.py`, `retro/a4.py`, `retro/a5.py`, `retro/a6.py`, `retro/extract.py`, `retro/peek.py`, `retro/peek2.py`, `today_full.py`, `today_lessons.py`.

