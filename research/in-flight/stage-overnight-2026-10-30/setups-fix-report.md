# Lane S (setup fixes): Rill's report, branch `stage-night`, 2026-10-30

Worktree `E:\AI-Setup\.claude\worktrees\stage-night`, branch `stage-night`, from `stage-v4` @ `e9f5e3cbc`.

## What this seat could and could not do (read this first)

**No render was possible from this session.** Chrome cannot start under the DSH file sandbox: every launch dies at
`mojo/public/cpp/platform/platform_channel.cc:112  Check failed: Access is denied (0x5)`, which is the sandbox denying
named pipes, before any flag (`--single-process`, `--no-zygote`, `--disable-breakpad`, `--headless=old`) or the
`danger-full-access` escalation, which had **no approval channel**. Consequences, stated plainly:

- **No stills, and no contact sheet.** `research/in-flight/stage-night/setups-beams-sheet.png` does **not** exist and no
  `stage_stills.mjs --setup <id>` run was made from this branch.
- **No `stage_verify --gpu` run.** Phases `load, flash, storm, bank, setups, phonebar` were **not** run here; the branch
  has no fresh stage receipt. The receipts quoted below are the ones already on disk from 2026-10-29.
- What *was* run: the whole node suite, in this worktree — **307 passed, 0 failed** (304 at `e9f5e3cbc`, plus three new
  checks), each file run directly (`node tests/stage_x.test.mjs`) because `node --test` cannot spawn children here
  (EPERM, the same sandbox).

For whoever has the GPU, the two commands that close the gap:

    node --test tests/stage_*.test.mjs
    node arsenal/lanes/stage_verify.mjs --gpu --lock-dir E:\AI-Setup\state\arsenal\gpu-render.lock \
         --phases load,flash,storm,bank,setups,phonebar

## Commits

- `6c67ab3b2` Setups, the beams: a head group's wheel range is its OWN placement
- `43ceb044e` Phone bar: the colour strip wears kick 5's BANK colours, and its check is re-registered

Nothing pushed. No `Co-Authored-By`, no vendor trailers.

## Job 1 — "the beams stay on the palette's wheel plan (violet)"

**The mechanism was real but not the one described.** `setupSlots()` built ONE wheel range for the whole rig out of ALL
of a setup's colours, and `_setupAllowed()` cached it per fixture TYPE; so every beam group drew from the same union and
a beam could legally sit on a slot belonging to the lasers, the cubes or the halo. Now the range is the group's own
placement (`setups.js groupColours`, over the whole bank turn), keyed per (setup group, part, fixture type).

**But the frame-level claim does not reproduce at the layer this seat can measure.** At bank 0 the beams are on their
own placements in all eight setups, and the wheel slot each group shows is **unchanged by the fix** (ice-spine 8
`#2a3cff`, gold-sapphire 3 `#ffd21a`, neon-split 10 `#ff2ad6`, aurora-column 6 `#19f0ff`, source-fan 6 `#19f0ff`,
ember-cathedral 2 `#ff8a1a`, cyan-crown 8, black-and-one 0). So this commit removes colours a group never had; it cannot
be what Daniel sees change.

Measured off the receipts already on disk (`stage-20261029-220836/setups-*.png`, hue shares of the frame): ice-spine
blue 67 %, source-fan green 41 %/blue 29 % — their setups' own colours. Ember-cathedral is violet 78 % / orange 0 %,
**but that is kick 5's BANK at bank 3**: the phase presses the bank three times, and Ember's cycle is orange, deep-blue,
gold, indigo, so bank 3 *is* indigo/deep-blue. Earlier runs of the same phase show Ember orange 44 % / yellow 37 %, which
is the same code at a different bank. **The violet in those frames is the bank working, not the palette's plan.** That is
why I did not "fix" the beams further: my change cannot move a pixel Daniel sees, and any change that did would be a
guess.

## Job 2a — S3, the limiter under a setup: **OPEN**

Recorded counts (protection ON, 480 frames, `stage-20261029-220836`): off 0, ice-spine 0, neon-split 10, aurora-column
12, source-fan 12, cyan-crown 12, black-and-one 12, gold-sapphire 13, ember-cathedral 18. Bar = 0 × 1.25 + 10 = 10, so
**six of the eight setups fail S3, not two.** No limit was loosened and the bar was not moved: nothing in this branch
touches `flash.js`, `FlashGate`, the limiter, the red cap or any throttling.

Two hypotheses this seat could test **without a render**, both measured and **both refuted** (numbers reproducible with a
short node probe against `Programmer` over the same 480 frames):

1. *"A setup's light is brighter, or swings harder."* Mean emitted light: off 1084, setups 1123–1155; the worst
   frame-to-frame swing is the **same frame 24** (the first white kick) in off and in every setup, dominated by
   `rings.slats`, and p95/p99 are 9.9–11.4 / 90.5–91.5 for all nine pages. The setups' light is not bigger and does not
   swing harder than the palette's own look.
2. *"The beams' far moves (the move in black) cost the limiter frames."* Counted `bankDip` starts in the same 480 frames:
   ice-spine **144 dips and 0 limited frames**, cyan-crown 96 dips and 12, source-fan/ember/black-and-one 240 dips and
   12/18/12. **No correlation** — the dip theory is dead, and worth recording so nobody re-derives it.

What is left is a rendered-frame question, and the repo already holds the one measured fact that narrows it: the
`setups.js` LEVEL note records that **with the beams mastered off the limiter never acted under any setup** (0 of 480),
and 10–18 with them on. So the beams' *rendered* contribution is the cause, but not their brightness (levelled), not
their count of black moves (counted above), and not the LED groups' level swings (measured above). The cheapest decisive
bisect for a seat with the GPU, one command each, same burst:

    node arsenal/lanes/stage_verify.mjs --gpu --phases setups --sheet-dir <dir> --features beams=0
    node arsenal/lanes/stage_verify.mjs --gpu --phases setups --sheet-dir <dir> --features "beams=0,veil=0"
    node arsenal/lanes/stage_verify.mjs --gpu --phases setups --sheet-dir <dir>          # the baseline

then, on the worst setup only (ember-cathedral, 18), the same with `features "halo=0"`, `"rings=0"`, `"lasers=0"` to find
the layer that owns the frames. `--features` already exists in the lane (`--features beams=0,veil=0`).

## Job 2b — the phone bar's colour-strip check: **re-registered**

The strip wore the palette's two kick LIFT colours and the check asserted them; kick 5 became the colour BANK, so the
strip promised colours a press no longer deals. Now `programmer.bankHex()` is the single source (the setup's own cycle
under a setup, else the palette's bank cycle), both `arsenal:palette` and `arsenal:setup` carry `bank` + `bankSetup`, the
strip paints from `d.bank` (ladder kept as the fallback, so an older page cannot break the bar), and the check fails if the
strip falls back to the ladder while the bank deals something else. The strip press now asserts the bank moved one place
(`bankCount + 1`) plus a live colour kick; the landing check asserts the same strip semantics after the palette lands.

Pinned in node (`tests/stage_setups.test.mjs`, 19 of 19): every setup's `bankHex` is its own cycle colour for colour,
resolved independently from `sets/setups.json`; the palette's bank cycle with no setup; the page publishes the bank on both
events; the strip reads `d.bank`; both re-registered check titles exist in the lane. **The three re-registered checks are
registered-but-unrun** — they have no GPU receipt from this branch, and the first thing they should do on the GPU is fail
if the strip still wears the ladder.

## Not verified (the honest list)

1. No still, no contact sheet, no `stage_stills` run: the sheet path in the brief does not exist.
2. No `stage_verify --gpu` phase — not `setups` (S3 unmeasured after the change), not `phonebar` (the re-registered checks
   unrun), not `load/flash/storm/bank` (no fresh safety receipt from this branch).
3. Job 1's frame-level claim: not reproduced and not refuted by a render; refuted at the programmer layer, explained at
   the frame layer by the bank.
4. Job 2a: no cause found and no fix landed; two candidate causes measured and ruled out.
5. The strip's new wash has never been seen on a phone.
