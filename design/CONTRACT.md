# design/CONTRACT.md — v1, One UI grounded

Status: current (2026-08-01) · Ratified scale: **One UI**, Daniil's ruling
Supersedes: the v0 draft (art_20260723_design-contract-md-v0-draft-for-ratifica_05075e), which
sat unratified since 2026-07-23 blocked on exactly one question — OneUI or HIG type scale. Answered.

**Why this file exists.** The UI is the only open-loop artifact in this system. Code has the suite,
builds have fences, recall has the funnel. The console was built by a text-only seat that had never
seen a rendered pixel, against a standard that lived only as images in chat, with no pixel-level
acceptance check — so the sole feedback signal was Daniil's frustration, arriving rarely and long
after shipping. An open-loop controller cannot converge on a target it never observes. Effort does
not fix that; instrumentation does. Diagnosis:
`docs/library/report/20260723_the-ui-gap-why-the-console-looks-like-th_32fec3.md`.

**The governing critique, Daniil 2026-07-05, still unmet:** *"assembled, not composed"* — too many
surfaces competing.

**The v1 ask, Daniil 2026-08-01 verbatim:** *"i just want it stable, performant, intuitive and
beautiful with support for realtime dynamic elements without bogging the system down, I want the
final version to render things at 60fps performantly."*

---

## 0. REFERENCES — durable, not chat-resident

The v0 draft's blocking ask was "drop or point us at the Apple/Samsung references". Now pinned:

- **One UI Design Guide (93pp, the ratified scale):**
  https://design.samsung.com/global/contents/one-ui/download/oneui_design_guide_eng.pdf
- One UI layout / grid: https://developer.samsung.com/one-ui/layout/grid.html
- One UI accessibility, layout & typography:
  https://developer.samsung.com/one-ui/accessibility/layout-and-typo.html
- Apple HIG — retained as a SECONDARY reference for interaction patterns only. Where the two
  differ, **One UI wins** (the ruling). Do not blend scales; blending is how you get neither.

Anything cited from the PDF must land here as a quoted number with a page reference. A token whose
provenance is "someone remembered it" is not in this contract.

## 1. TOKENS — the measurable half

Every value below is either quoted from the references or DERIVED and labelled as such. A blind
builder can self-verify all of §1 mechanically (computed-style dumps); none of it needs eyes.

**Spacing — 4dp base, 24dp gutter.**
One UI states a hard minimum: *"display information and place interactive components with margins
of at least 24 dp on both the left and right sides"* (grid.html). The project's own composition
spec already carries "24dp grid" as restraint cut #4 — it came from here, so this is a
re-grounding, not a new rule.
`--sp-1:4px --sp-2:8px --sp-3:12px --sp-4:16px --sp-6:24px --sp-8:32px --sp-12:48px`
Page gutter is `--sp-6` (24px) minimum. Nothing may be positioned off-grid without a comment
naming why.

**Type — 1.2–1.4 line-height, scalable to 200%.**
One UI: line spacing 1.2–1.4× the font size; all text except subtitles and in-image text must be
resizable to 200% without loss of content or function. Consequence, and it is binding: **no fixed
px heights on text-bearing containers.** A chip that is `height:28px` breaks at 200%.
Sizes DERIVED on a 1.25 ratio from a 13px body (the console's existing body size, kept so this is
a re-grounding rather than a visual reset):
`--fs-xs:10.5px --fs-sm:11.5px --fs-body:13px --fs-lg:16px --fs-xl:20px --fs-2xl:25px`
`--lh-tight:1.2 --lh-body:1.4`

**Color ROLES, not hues.** Alarm colors are spent only on alarms. The 2026-07-23 audit found
per-agent sparklines rendering red/orange for *normal activity* — alarm color spent on non-alarms,
so real alarms have nowhere left to escalate to. Trust erosion by color.
`--role-ok --role-info --role-warn --role-alarm --role-idle --role-unknown`
`--role-alarm` and `--role-warn` may not appear on any element whose state is nominal. Ever.

**Motion budget — the 60fps clause. This is the binding perf rule.**
MEASURED 2026-08-01 on the live console: **261 elements running CSS animations simultaneously**,
and the count scales with fleet size — the same unbounded-by-roster-count disease as the roster
popover height (was max-height:none) and the header pill strip (was 998px of a 1180px bar).
Every added agent multiplies pulses, sparklines, chroma-breaths and puff trails.
  - **Ceiling: ≤ 24 concurrently animating elements**, fleet size irrelevant. If a surface wants
    motion per row, it gets motion on the ACTIVE row only.
  - Animate `transform` and `opacity` only. Never `width/height/top/left/box-shadow/filter` in a
    loop — they force layout or paint every frame.
  - Off-screen animates nothing: `content-visibility:auto` on feed rows; pause loops when
    `document.visibilityState !== 'visible'`.
  - One rAF scheduler for the whole page. Modules subscribe; they do not each own a loop.
    (Five separate scripts load today: aurora-shader, bifrost_viz, theme-void, presence-rail,
    presence-cloud.)
  - `@media (prefers-reduced-motion:reduce)` disables all ambient motion.

**Layout — grid, not islands.** The audit found "absolute-positioned islands, no grid": at
mid-size the layout shatters, the brand crops to "ifrost", toolbar buttons hover mid-feed.
Confirmed still live 2026-08-01 — the header row overflowed by 399px (`scrollWidth` 1579 vs
1180) because `.pills` took 998px with no `min-width:0`, crushing `#epiChip` from 162px of
content into 22px of box.
  - Any flex child that can grow with data carries `min-width:0` and `overflow` of its own.
  - Control clusters are `flex:none`. Data strips are `flex:1 1 0; min-width:0` and scroll
    internally. A picker never grows the page; it scrolls (roster-pop, ash-content — both bounded).

## 2. THE AXIS LAW

No number, glyph, meter or sparkline ships without: **a label · a unit · a hover explanation · a
freshness stamp · a dead-feed state that LOOKS dead.**

Daniil, on the current console: *"you dont know what any axis means."* The audit confirmed five
unlabelled glyphs per agent row — dot, second dot, sparkline, capsule, badge — with no legend, no
hover, no units. He was literally correct; nobody could.

Corollary — **state vocabulary must be true per seat class.** The audit caught claude's status
reading "runner · listening" when claude is a seat, not a runner. A gauge whose words are wrong
teaches the operator to distrust every gauge.

## 3. THE LOOP — how a change is allowed to ship

The contract is not the fix. The loop is. The fix is structurally three organs, and organ 1 is
already running as of tonight:

1. **EYES IN THE LOOP.** No UI change ships without before/after MEASUREMENTS from a sighted seat
   at two viewports — DOM rects, computed styles, console errors, animation count. Not
   impressions. Tonight's rounds did this: the avatar fix was verified by
   `AVATAR_OVERLAPS_LADDER:false` + a 12px measured gap, and it caught a real bug — the mount
   succeeded while the class was silently wiped by a `className=` assignment, which "looks right"
   would have missed.
2. **THIS CONTRACT**, gated by Daniil. §1 is mechanical; §2 is mechanical; taste is his.
3. **A CLOSED BUILD LOOP:** build (with mechanical self-checks) → sighted fence → Daniil
   taste-gate at milestones, not per-commit.

**Known instrument bound, stated rather than hidden:** `requestAnimationFrame` does not tick in a
non-compositing pane, so a headless seat CANNOT measure real FPS. It can measure every structural
cause of jank — animation count, poller rate, DOM size, layout-thrashing properties, long tasks.
Any "60fps" claim must come from a visible window or a trace, never from a hidden pane. Do not
report an FPS number you did not observe.

## 4. WHAT THIS CONTRACT DOES NOT PROMISE

Matching Apple/Samsung *polish* is a taller bar than any checklist. It needs the contract,
iteration under the fence, and possibly a component-level rebuild of the console's frontend
substrate rather than continued accretion onto one 3,259-line file. That is a costed decision for
a gate — priced there, not promised here. No-build options that would fit this stack if it is
taken: Open Props (tokens only, ~1.5KB), Pico (classless, ~2KB), Shoelace / Web Awesome (web
components).

---

*v1 supersedes the v0 draft. Ratified scale: One UI (Daniil, 2026-08-01). The six restraint cuts
of the 2026-07-05 composition spec remain binding and are not restated here:
collapse reasoning · ONE presence surface · composer focus-block · 24dp grid · ≤3 top actions ·
keep dark/aurora/glass/Razer.*
