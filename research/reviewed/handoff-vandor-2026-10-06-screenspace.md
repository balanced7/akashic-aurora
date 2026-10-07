# Handoff — next Vandor, screenspace actuator landed

Written 2026-10-06 by Vandor#428ba6c4. This file is the **drill input**: it is what
`py agent_cli.py screen prompt --text-file research/reviewed/handoff-vandor-2026-10-06-screenspace.md`
pastes into a new session.

A file rather than `--handoff`, deliberately. `--handoff` works and resolves spilled notes, but its
delivery is racy right now: `_consumed()` (`core/context/briefing_loader.py:15`) retires a handoff as
soon as the target records **any** lesson newer than it, and **both live Vandor seats run under the
agent id `claude`** — so the sibling seat's lessons retire handoffs addressed to me. Measured: the
loader returned FOUND and then, seconds later, None, with nothing written or consumed by me in
between. For a drill you want an input that cannot move under you.

## What you are inheriting

`core/screenspace/act.py` + `core/screenspace/combo.py`, wired to `py agent_cli.py screen`
(`status` | `locate` | `prompt`). Commits `23c75726`, `484baee1`, `056bf74b`. 36 pins green across
`tests/test_the_actuator_refuses_before_it_acts.py` and
`tests/test_the_new_session_combo_has_a_door.py`.

**Landed after the actuator, same session, same arc:**

- `9ef98b3a` — the **affordance-layer fence is RECONCILED and sealed**. Both halves rejected my
  per-action-builder + paste-test proposal, for *different* reasons (Heimdall: "runnable" depends on
  the reader's execution surface; Navi: several affordances *mutate*, proven by pasting them). My
  three-layer model is blind at both ends — it needs PRECONDITION and EFFECT. 29/97 is retired as a
  measurement. Read `fences/affordance-layer/reconciliation.md` §6 for the build spec.
- `6755e603` — **item 0 of that spec, closed**: windowed scheduled tasks had no voice.
  `sys.stdout is None` under Task Scheduler, `print()` silently discards, and `check_secrets.py
  --history` (the weekly secret scan) wrote no files at all, so its entire output went nowhere every
  week. Reproducing it needs `CreateProcessW(bInheritHandles=FALSE)` — `pyw` from a shell and
  `Popen(DETACHED_PROCESS)` both *inherit* and give a false all-clear. 5 of 12 windowed tasks were
  already fixed by someone who hit this before; the repair is now
  `core/infrastructure/background_stdio.py` and applied to the other six.
- `ddc0e734` — **`find --sort` and every `--preset` were silently inert.** The flag reached es.exe
  correctly and then `_rank_exact_first` re-sorted the results in Python by
  `(basename != query, len(path))`, discarding the requested order at four call sites. Fixed in one
  place with a `sorted_by` no-op and a `key` extractor. A second defect was hiding behind it: a
  **bare es.exe sort key is DESCENDING**, so `--preset oldest` returned newest and `--preset
  smallest` returned biggest. Both now say `-ascending` out loud. 9 pins.
- `f80ad49e` — **`delta --disk`**, the disk plane of the T052 delta door
  (`core/provenance/delta.py`, 15 pins). Reports what moved that no Aurora plane recorded:
  uncommitted work, anything outside the repo, and per-file attribution from the touch stream.
  Classifies every change `repo` / `private` / **`volatile`** and renders volatile first, because
  it is the only losable class. Metadata only — it is pointed at a tree holding tax returns.
  Honest denominators: roots scanned/skipped, files examined, and `touch.drops()` (214).
  **Run `py agent_cli.py delta claude --disk --hours 24` at wake.**
- `9bf0d994` — **item 1 of that spec was wrong**, and the addendum says why
  (`fences/affordance-layer/addendum-item1-does-not-survive.md`). Also fixes a real defect found on
  the way: `defer <seat> --list` ran its unknown-seat guard *inside* the empty-queue branch, so once
  the global queue was non-empty a typo'd seat could discharge items and stamp a permanent receipt
  under a seat that does not exist.

This is build steps 1, 3 and 5 of
`docs/library/design/20260902_screenspace-organ-design_528df4.md`. The whole organ — the five
observe-half modules too — is wired for the first time since 2026-09-23.

## What is left: ONE ATTENDED DRILL, not more building

```
py agent_cli.py screen status
py agent_cli.py screen prompt --text-file research/reviewed/handoff-vandor-2026-10-06-screenspace.md --show
py agent_cli.py screen prompt --text-file research/reviewed/handoff-vandor-2026-10-06-screenspace.md
py agent_cli.py screen prompt --text-file research/reviewed/handoff-vandor-2026-10-06-screenspace.md --submit
```

`--show` prints the exact brief and touches nothing. The third line **stages** it in a new session
and stops (`submit` is off by default, design step 3). Only the fourth sends, and it is verified by
a causal receipt: a **new transcript** under `C:\Users\L5\.claude\projects\E--\` containing the
nonce the module embedded. If no transcript carries it, the status is `unverified`, never `ok` —
look at the window before re-running, because re-running sends twice.

Two preconditions, both of which were blocking when this was written, and both are the design
working rather than failing:

1. **The workstation must be unlocked.** `OpenInputDesktop` returns `ERROR_ACCESS_DENIED` while
   locked, and the window stays *fully readable* throughout — `IsWindow` and `GetWindowTextW` both
   still answered for hwnd 67692. Being able to SEE a window proves nothing about being able to type
   into it, which is why `LOCKED` is probed and refused separately from `NOT_FOREGROUND`: one can be
   focused, the other can only be waited for.
2. **A second party must grant the caps.** The six `screen.*` tiers are real `Cap`s in
   `core/trust/capabilities.py` and sit in **no role template**, so `screen status` reports "verbs
   permitted: NONE" even for `claude` as super_admin. `grant()` raises `PermissionError` on
   `agent_id == by` — *"a second party mints your authority"* — so the actuator can never
   self-authorise onto the desktop. `screen status` prints the exact one-line command; it **must**
   restate the seat's existing caps because `--caps` REPLACES rather than adds (filed W252), and it
   deliberately withholds `screen.launch` and `screen.privileged`, which no verb maps to.

## Five things the build learned. Do not re-learn them.

1. **`uiautomation` rewrites `ctypes.windll.user32` prototypes on import.**
   `GetForegroundWindow.restype` goes `c_long` → `c_void_p`, so the same NULL renders as `0` before
   the import and `None` after it. Code comparing it to an int silently stops matching and the
   foreground guard refuses *forever*. `act.py` holds a private `ctypes.WinDLL("user32")` with
   prototypes it sets itself — do not switch it back to `windll`.
2. **A window-wide frame hash is a guard that never passes.** 8.4M pixels, 88 ms, and *any* repaint
   anywhere trips it — a streaming reply alone would, and the operator's YouTube tab did. The hash is
   scoped to the control's own rect (404×39, ~1 ms) and the exact hashed region is **recorded in the
   token**, so `verify()` cannot compare two different regions and refuse on the difference.
3. **`locate()` was 2,209 ms because it asked UIA for a Win32 answer.**
   `GetRootControl().GetChildren()` took 2,203 ms of it; `EnumWindows` takes 4 ms. Warm `locate()`
   is now 141 ms, inside the design's 200 ms bar. The targeted name search (195 ms) was never the
   problem. Related: **name-first beats a tree walk 17–24×** (1,027 controls / 681 named / 3,200 ms
   for a full depth-30 walk), and **depth is not an address** —
   `win.DocumentControl(searchDepth=10)` returns an unnamed 0×0 node whose `ValuePattern` raises,
   while the real titled document sits elsewhere in the tree.
4. **Text goes through the clipboard, never `SendKeys`.** `SendKeys` is a little language: `{}()!+^%`
   are syntax and `{a 3}` is a repeat count, so prose pushed through it does not merely garble, it
   *executes*. And the operator's clipboard is restored **after** the post-condition settles, never
   before — restoring early makes `Ctrl+V` paste the *old* clipboard, which is a silent,
   exact-looking corruption.
5. **There is no composer control to click.** Zero `EditControl`s exist anywhere in the window
   (426 ms exhaustive scan); the composer is a Chromium contenteditable whose a11y nodes report 0×0
   bounds. So the ladder is **named control → keyboard → coordinates**, and typing can only be
   confirmed by reading it back. When read-back cannot see it, the result is `unverified`, never `ok`.

## Lane discipline

The other Vandor (`#81efa6f6`) owns `core/recall/*` this round — the credit join. **I did not touch
it.** Four recall changes remain queued, in dependency order; check with him before starting any:

1. Coarser command key in `_log_outcome_stage`, plus the transcript backfill in the PostToolUse hook.
2. The relative floor in `_lessons` (`core/recall/at_action.py:1582-1584`).
3. Anti-repeat scoped to `(lesson, trigger)` rather than `(lesson, session)`.
4. The 94 lessons leading with "When"/"Before"/"On"/"After" that the one-spelling parser at
   `core/recall/at_action.py:257` cannot read.

One red is his, not yours: `tests/test_seat_heartbeat_wiring.py::test_w3_both_hook_copies_stay_in_sync`
went red in his `0c51836b` — comment-only drift between `scripts/hooks/claude_posttooluse.py` and
`agent/harness/hooks/claude_posttooluse.py` at lines 340-342. He has the exact three lines.

## Open, and not mine to close

- The affordance-layer **reconciliation is unwritten**: both halves sealed, PV 20/0.
- Rill still owes `research/reviewed/affordance-layer-rill-cold-read.md`.
- Simon's six cheap PRs (23, 22, 24, 25, 21, 20) merge clean and await Daniel's OK. The rest of his
  stack is **re-run, don't merge** — his own certifier (`oracle.relevant_digest`, which hashes every
  tracked blob) refuses the merged tree.
- Daniel's two flipped RED pins; 3.11 vs 3.12; whether to install `uv`; gemini+sol still capped at
  30 tool hops.
- The wishlist's id space has **collided** — W00, W57–W69 and W211 each appear more than once — so
  citations into it are ambiguous until the next curation.
