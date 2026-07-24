---
akashic_id: art_20260723_the-ui-gap-why-the-console-looks-like-th_32fec3
akashic_sha: 6f4c50d00da2
status: current
type: report
date: 2026-07-23
title: The UI gap — why the console looks like this despite best efforts
gist: "**Daniel's charter (verbatim):** \"Also the interface right now is nigh unreadable, things aren't intuitive and can't be trusted because half"
tenant: solo
visibility: fleet
seats: []
category: [security, conducting, ui]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T02:28:01"
updated: "2026-07-23T02:28:01"
---
<!-- GENERATED PROJECTION of art_20260723_the-ui-gap-why-the-console-looks-like-th_32fec3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# The UI gap — why the console looks like this despite best efforts

**Daniel's charter (verbatim):** "Also the interface right now is nigh unreadable, things
aren't intuitive and can't be trusted because half the time the indicators don't respond,
you dont know what any axis means and have no way of intuitively knowing what is going
on, some of the design language is nice but it is so so so so far away from the UI
designs I showed the team earlier from apple and samsung. What do we need to do for us to
be able to actually understand why the ui looks this bad despite our best efforts? do we
need to give the fleet vision? what is the gap?"

---

## The gap, named

**The UI is the only open-loop artifact in the entire system.** Every other artifact
class closed its feedback loop years-in-project-time ago: code has the suite, builds have
fences, recall has the funnel, activation has gauges. The UI is built by a text-only
builder (deepseek, per the integration boundary) who has NEVER SEEN A SINGLE RENDERED
PIXEL of its own output, against a design standard that exists only as images Daniel
showed in chat (never persisted as repo anchors), with zero pixel-level acceptance check.
The only feedback signal is Daniel's frustration — rare, verbal, and long after shipping.
An open-loop controller cannot converge on a target it never observes; effort does not
fix that, instrumentation does. (This is the recall-arc's dead-ECN open-loop sender, in
pixels.)

## Do we need to give the fleet vision? — split the question and it answers itself

- **The fleet ALREADY HAS vision at the claude/kimi tier, unused for UI.** Receipt: this
  session, tonight, claude opened localhost:8787 in its browser pane, screenshotted it
  twice, read the console log and the network log. The capability was always there; it
  was never wired into the UI build loop.
- **deepseek (the builder) is text-only and stays that way for now** — but most of a
  design contract is MEASURABLE WITHOUT EYES: contrast ratios, spacing-token conformance,
  label-presence on every indicator, poller counts, overflow/reflow at standard
  viewports, dead-feed states. A blind builder can self-verify the measurable half
  mechanically (computed-style dumps, DOM audits). What genuinely needs eyes is the TASTE
  half: hierarchy, balance, feel — and that's what sighted fences + Daniel's gate are for.
- So: **no exotic capability is missing. The missing thing is a loop:**
  blind-builder mechanical checks → sighted-seat screenshot fence → Daniel taste-gate.

## Tonight's sighted audit (10 minutes, six receipts — the loop working for the first time)

1. **Unlabeled axes everywhere:** five glyphs per agent row (dot, second dot, sparkline,
   capsule, badge) — no legend, no hover, no units. Daniel's "you dont know what any axis
   means" is literally correct; nobody could.
2. **Alarm semantics abused:** the per-agent sparklines render red/orange for what is
   apparently NORMAL activity — alarm colors spent on non-alarms, so real alarms have
   nowhere to go. (Trust erosion by color.)
3. **Indicators that lie:** claude's status line reads "runner · listening" — claude is a
   seat, not a runner. A gauge whose words are wrong teaches the human to distrust every
   gauge (the assert-a-guard genus, rendered).
4. **Racing pollers:** 15 requests in ~140ms — /status polled 8x, /vitals 6x, overlapping
   — multiple redundant poll loops racing to repaint the same indicators. Prime suspect
   for "indicators don't respond half the time": last-writer-wins flicker, not dead
   plumbing (all endpoints 200, zero JS errors).
5. **No responsive structure:** at a mid-size window the layout shatters — floating
   overlap columns, the brand cut to "ifrost", toolbar buttons hovering mid-feed, main
   region rendering as empty black at some sizes. Absolute-positioned islands, no grid.
6. **Jargon as chrome:** "PRESENCE-AUTOPILOT ☑ reconciled" as a primary header element;
   an unlabeled hexagon button; "untitled episode" in the headline slot. Internal
   vocabulary shipped to the human surface unexplained.

(Plus the two already chartered from Daniel's screenshots: the triage noise-floor W70,
and unseated-vs-idle rendering identically.)

## The three organs to install (the fix, structurally)

1. **EYES-IN-THE-LOOP (starts immediately, zero build):** standing rule — no UI change
   ships without before/after screenshots at two standard viewports, checked by a sighted
   seat (claude or kimi) against the contract checklist; findings filed like fence reds.
   Periodic full design audits, same discipline as code audits.
2. **A WRITTEN DESIGN CONTRACT (design/CONTRACT.md, gated by Daniel):** distilled FROM
   Daniel's Apple/Samsung references once they land as durable files (design/refs/ —
   TONIGHT'S ASK: Daniel, drop or point us at them). Contents: tokens (type scale,
   spacing, color ROLES — alarm colors only for alarms), the AXIS LAW (no number, glyph,
   or meter ships without a label, unit, hover-explanation, freshness stamp, and a
   dead-feed state that LOOKS dead), the state-vocabulary law (words on gauges must be
   true per seat-class), the noise-floor law (W70), and the measurable-vs-taste split so
   the blind builder knows which half it can self-verify.
3. **A CLOSED BUILD LOOP with unchanged ownership:** deepseek keeps UI integration (the
   boundary stands); every UI slice runs build (deepseek, with mechanical self-checks) →
   sighted fence (claude/kimi) → Daniel taste-gate at design milestones, not per-commit.
   First fenced slice proposal: the mechanical defects from tonight's audit — poller
   consolidation (one scheduler), responsive grid skeleton, axis labels + legend, honest
   state vocabulary — because they are measurable, testable, and none of them are taste.

## Sequencing with the live arcs

The NOW-card charter (deepseek, design pending) BECOMES the first artifact built UNDER
the contract + fence regime — story-state and readability are the same fight. The MCP-O1
build spec is untouched by this. Nothing here jumps Daniel's standing gate; the contract
needs his references and his ratification to exist at all.

## The honest bound

Vision closes the broken/illegible/lying loop cheaply and provably (tonight's audit IS
the proof). Matching Apple/Samsung POLISH is a taller bar than any checklist — it needs
the contract, iteration under the fence, and possibly a component-level rebuild of the
console's frontend substrate rather than accretion onto one file. Say that at the gate,
price it there; don't promise polish from a checklist.
