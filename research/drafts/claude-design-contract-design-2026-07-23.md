Status: current
Type: design (proposal) · Arc: interface/optics · Seats: claude · Date: 2026-07-23

# design/CONTRACT.md — v0 draft for ratification (the fence the UI never had)

**Why this exists (the open-loop finding, tonight):** the UI is the fleet's only artifact
built without a feedback loop — blind builder, standard-in-Daniel's-head, no pixel fence.
This contract is organ 2 of the three-organ fix (organ 1 = eyes-in-the-loop, proven
tonight when a sighted pass caught the `[unseated]` accumulation deepseek's build-fence
could not; organ 3 = the closed build loop). It turns "make it look like Apple/Samsung"
from taste-nobody-can-check into **measurable clauses a blind builder self-verifies + taste
clauses the sighted fence and Daniel gate.** Ratify it and every UI slice ships against it.

**Sources (durable now):** the settled fleet principles (docs/ui-plan-synthesis.md,
ui-moodboard-{claude,deepseek}.md), Daniel's captured anchors (design/refs/oneui/ +
design/refs/apple-hig/, 73 HIG pages + OneUI guide), and tonight's audit
(research/drafts/ui-gap-diagnosis-2026-07-23.md). This v0 distills what is ALREADY
settled; the captured refs deepen the token values in v1.

---

## Part A — the two-column split (the whole point)

Every clause is tagged **[M]** measurable (the blind builder self-checks it mechanically —
computed styles, DOM counts, poller counts, parse) or **[T]** taste (needs the sighted
fence + Daniel's gate). A slice cannot ship with a failing [M]; [T] clauses are gate items.

## Part B — the laws

### 1. The axis law [M] — the one Daniel named ("you dont know what any axis means")
No number, glyph, meter, or sparkline renders without: a **label**, a **unit** (or a
legend within one hover), a **freshness stamp** (when did this datum last update), and a
**dead-feed state that LOOKS dead** (a stale gauge must not look live). A bare glyph is a
contract violation, mechanically detectable (every `.gauge`/`.spark`/`.meter` node must
carry `aria-label` + a `data-fresh` attr).

### 2. The honest-vocabulary law [M] — ("indicators can't be trusted")
Every status word must be TRUE for that seat-class. A seat is not a "runner"; an unseated
agent is not "idle"; a stale heartbeat is not "active". The classifier is checkable against
the seat registry. (Tonight's "claude runner·listening" + the unseated/idle collision are
the two founding violations; deepseek's classifier fix is the first compliance.)

### 3. The earned-accent law [T→M] — (moodboard P2, "the accent is earned")
Alarm colors (red/amber) render ONLY on alarm states. Routine activity never spends alarm
color. [M] half: a lint that no `--danger`/`--amber` token appears on a node without a
corresponding alarm state class. (Tonight's sparklines burning red on normal traffic = the
founding violation.)

### 4. The noise-floor law [M] — (W70, the triage flood)
The human feed defaults to WORK-STORY traffic. Bookkeeping (triage, receipts, acks)
collapses to one ambient expandable line or routes to a bookkeeping lane. [M]: no more than
N non-story lines per event batch reach the primary feed.

### 5. The responsive-integrity law [M] — (tonight: layout shatters off-fullscreen)
The page holds structure at two standard viewports (desktop 1280, tablet 768) and never
horizontally scrolls the body. [M]: a headless render at both widths shows no overlap,
no clipped brand, no floating controls (bounding-box overlap check).

### 6. The one-presence-surface law [T] — (composition spec #2, drifted 3 audits running)
Who-is-doing-what lives in ONE place, not three. Gate-checked (it is a composition
judgment, not a measurement).

### 7. The restraint laws [T] — (OneUI/HIG core, Daniel's "assembled not composed")
Grouping over accretion; ≤ a stated number of top actions; generous spacing on the
8/16/24 grid; darkness is the canvas; glass separates layers, motion is information not
decoration. These are the taste spine; the captured OneUI/HIG refs are the calibration.

### 8. The token law [M] — (make v1 concrete)
One source of truth for type scale, spacing, and color ROLES (role, never raw hex, at
call sites). v1 fills the values FROM design/refs (OneUI type scale + HIG spacing);
v0 states the rule. A raw hex at a call site is a lint failure.

## Part C — the build loop (organ 3, ownership unchanged)
Every UI slice: deepseek builds (self-checks all [M] clauses mechanically + presents the
receipts) → claude/kimi sighted fence (the [T] clauses + a DOM-over-time pass for the
accumulation class, per lesson `sighted_fence_catches_over_time_dom_defects`) → Daniel
taste-gate at design milestones, not per-commit. No UI slice ships without before/after
screenshots at the two viewports.

## Part D — binding scope
Binds BOTH the incumbent :8787 console (truth+noise clauses 1–5, which transfer) AND the
T098 typed face (all clauses — it is born under this regime, with the CI parse-gate that
makes clause enforcement structural). The corpus compilation's frame stands: composition/
polish ambition targets the T098 face; the incumbent gets the measurable-truth clauses.

## The gate asks (Daniel)
1. Ratify v0 as binding (lands as docs/CONTRACT.md; this becomes the decision record).
2. Confirm the [M]/[T] split is the right enforcement model.
3. v1 fills tokens from design/refs — do you want the OneUI type scale or the HIG scale as
   the primary (they differ); or a blend keyed to the Aurora Glass identity?
4. Round it: deepseek (builder — which [M] clauses are cheap to lint now?) + kimi
   (stranger — does clause 1 survive someone who never saw the console?).
