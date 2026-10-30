# Qlimax stage, overnight 2026-10-30: the brief for Rill and Heimdall

Written by Vandor (claude). Daniel went to sleep at 05:41 UTC and asked, verbatim: "feel free to have heimdall and Rill
continue work on the qlimax set so you can conserve tokens. Figure out how to launch and reach Rill, heimdall can also
spin up deepseek flash vision models to see and deepseek flash models for coding, they are quite dang good. Think you
can find clever ways is directing things in a powerful, useful but token efficient way?"

Earlier that night he played the stage on :8796 (?demo=1) and said: "it looks AMAZING!!!!! so many problems have been
fixed!" Protecting what he loves comes first. Everything below happens on branches. His page is not touched.

## Who does what

- **Rill (dsh_agent) builds.** Two lanes, each in its own worktree that is already created:
  - Lane P: preset packs v0, in `E:\AI-Setup\.claude\worktrees\stage-packs` (branch `stage-packs`).
  - Lane S: setup fixes, in `E:\AI-Setup\.claude\worktrees\stage-setups-fix` (branch `stage-setups-fix`).
  - Both branches start at the snapshot tag `snapshot/stage-2026-10-29-amazing` (= `e9f5e3cbc` = stage-v4 HEAD, the
    build Daniel played).
- **Heimdall (deepseek) reviews.** When Rill posts that a lane is done, Heimdall reviews it:
  - read the diff;
  - run the stage tests;
  - look at the before and after stills with a vision model.
  - Then write a verdict file next to the lane's report: `PASS`, or a numbered must-fix list. Rill fixes, and Heimdall
    re-checks. At most 2 rounds per lane.
- **Vandor checks receipts in the morning, then shows Daniel.** Vandor re-runs the test commands named in the reports
  and reads the verdicts. Nothing merges until Daniel has looked.

## The rules (all lanes)

1. **Never touch**:
   - `E:\AI-Setup\.claude\worktrees\stage-v4` (it serves Daniel's page on :8796);
   - ports 8793, 8794, 8796, 8798 and their servers;
   - the KeyLab;
   - `master`;
   - origin (no push).
2. **Flash safety is not yours to change.** Never loosen or bypass FlashGate, the flash limiter, strobe or laser gates,
   the red cap, flash consent or camera clearance. If a fix seems to need that, stop and write it up.
3. **Brightness numbers marked SAFETY-adj** (luma_cap, punch, and the like) may only go DOWN.
4. **GPU.** Renders go through the house GPU lock (`stage_verify.mjs --gpu`, `stage_stills.mjs`). If `League of
   Legends.exe` is running, stop rendering and do code and node tests only.
5. **Commits.**
   - Commit on your branch only, by named paths (no `git add -A`).
   - No Co-Authored-By or AI-attribution trailers.
   - Never commit third-party footage (`state/arsenal/refs/`) or Shadertoy code.
6. **Receipts or it did not happen.** Each report lists:
   - the exact commands and their pass counts;
   - the stage_verify run ids;
   - the stills paths;
   - a "Not verified" section.
7. **When a lane is done, say so on the bus to BOTH `claude` and `deepseek`, in one line:**
   `done: <lane> <branch>@<sha> report=<path>`. That message is what wakes the reviewer and Vandor; nobody needs to
   poll.

Test commands:

    node --test tests/stage_*.test.mjs
    node arsenal/lanes/stage_verify.mjs --gpu --phases <phase list>

The phase names are in `arsenal/lanes/stage_verify.mjs` and the stage README.

## Lane P: preset packs v0 (Rill)

The design is `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\stage-preset-packs-design-2026-10-29.md`. Build
its section 6 "v0: the snapshot shelf" exactly. In short:
- **New files:**
  - `arsenal/web/stage/packs.js` (merge, allowlists, denylist, clamps, hash);
  - `arsenal/web/stage/packs/` (13 layer files plus the show `amazing-2026-10-29`, all copied from the tagged
    files);
  - `arsenal/lanes/stage_packs.mjs` (freeze, diff, fork).
- **Change to existing code:** about 30 lines in `stage.js` boot, and they run only when the URL asks for a pack.
- **Pack controls:**
  - `?pack=<show>` and `?pack.<layer>=<id>`;
  - the HUD line naming the show;
  - a Freeze button that DOWNLOADS the current settings as a pack file.
- **No engine module changes.**

Daniel has not answered the design's three questions yet. Build with the design's own recommendations:
- the pack is not loaded by default;
- Freeze is a download;
- live switching is v1, so it is not in this lane.

Proof: the design's P0 to P4b:
- the pack deep-equals the tagged scene;
- all stage tests pass unchanged;
- the Node 512-bar run gives the same cuts and phrases;
- stage_verify on no-pack and with-pack gives the same results;
- the stills match.

Report: `research/in-flight/stage-overnight-2026-10-30/packs-v0-report.md`, on the branch.

## Lane S: setup fixes (Rill)

From the setups commit `f3804bc0e` and the reports in `research/in-flight/stage-*-report-2026-10-29.md`, these are known
gaps with no decision needed:
1. **Beams ignore four setups.** In Ice Spine, Aurora Column, Source Fan and Ember Cathedral, the moving heads' beams stay
   on the palette's wheel plan (violet), so those setups change the halo, cubes and lasers but not the beams. Make the
   beams follow the setup, as the other four setups already do.
2. **S3, the limiter under a setup.** With protection ON, the limiter acts on 10 to 18 of 480 frames under a setup, against
   0 without one. Get that to 0 by making the setups' light gentler (luma_cap and levels go DOWN), never by touching the
   limiter.
   - Keep S1, S2, S4, S5 and S6 passing: 8 of 8 setups land, at most 3 flashes a second, red 0, every tap steps the bank,
     rotation on the 16-bar line, O lands on the next bar.
   - Keep the setups looking like themselves. Compare the stills before and after with your vision model, and say what
     changed.
3. **A stale phone check.** The phone pad bar's "colour strip lift colours" check has been stale since kick 5's colour
   bank landed. Bring it up to date so it tests what the strip does now.

Report: `research/in-flight/stage-overnight-2026-10-30/setups-fix-report.md`, on the branch.

## Heimdall's review checklist (per lane)

- **Scope:** does the diff stay inside the lane? For Lane P, does any engine module change? (It must not.)
- **Safety:** is any safety constant, gate or limiter reachable or changed? Is any SAFETY-adj number raised?
- **Tests:** re-run `node --test tests/stage_*.test.mjs` in the lane's worktree, and report the counts.
- **Eyes:** open the before and after stills with the vision model. Name any setup or shot that stopped looking like
  itself.
- **Verdict:** write `<lane>-verdict-r<N>.md` next to the report. Then send one line on the bus to `dsh_agent` and
  `claude`.
