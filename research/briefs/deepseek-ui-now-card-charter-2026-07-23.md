# Charter — the NOW-card: live per-agent visibility on the Bifrost console

Status: current (chartered under R001 Part A; Daniel gates DESIGN before build)
Type: brief (charter) · Arc: interface / optics · Seats: deepseek (owner — UI integration
is your lane; T002 is the natural home) · claude (backend feeds) · Date: 2026-07-23

**Daniel's charter (verbatim, two levels up — this is the intent, whole):** "I dont see
any visual evidence of kimi or deepseek doing anything on the 87 bifrost ui. I dont know
what task they are doing, what the status and individual substep and plan is, no way to
feel and see every detail of the action including the reasoning in realtime"

**The receipt that proves him right (use it as the design's north star):** tonight you
turned the MCP-concurrency counter — 13.7KB, 162s, pts=95 — and the human watching :8787
could not see it happening. The data EXISTED (turn_metrics, msg_ack, bifrost_msg, commit,
advisory lock, all on the bus within seconds) and the console rendered none of it as a
live "deepseek is doing X right now" story. Separately: kimi was unseated tonight, and
the console shows that as the same nothing — a live-idle agent and an unseated agent are
visually identical. Both facts are the failure.

**Done-looks-like (Daniel's four demands, restated as surfaces):**
1. WHAT: the agent's current task (ledger claim / charter / handoff being answered).
2. WHERE: status + substep — which phase of its own plan it is in, live.
3. PLAN: the plan itself, visible, with progress against it.
4. FEEL: the realtime action stream — every tool call and the reasoning beside it, as it
   happens (narration-default is FULL by standing directive; the feed exists — the STORY
   rendering of it is what is missing).
Plus the state kimi exposed: NOT-SEATED must render as its own visible state ("kimi:
unseated — brief waiting: <name>"), never as blank.

**Constraints (REAL ones only):**
- The bus stays the source of truth; the card is a PROJECTION of events already flowing
  (turn_metrics, locks, task ledger, narration beats). No second source of truth, no new
  state the events cannot regenerate.
- Fidelity controls stay (off/key/full) — FULL is the default per Daniel's standing
  narration directive.
- Method is YOURS (mechanism, layout, polling vs push). claude owns making the backend
  feeds complete: narration beats for harness seats and kimi launcher seats (today only
  runners narrate reliably — that gap is claude's lane, not yours).
- Daniel gates the DESIGN (one page or a sketch on the bus) before build; then you build
  whole-arc per R001 Part A and present your own fence evidence.

**Suggested first move (yours to override):** a one-page design answering: card data
sources (which event kinds feed which card zones), the unseated/idle/working/blocked
state machine, and what "substep" means for each seat class (runner phases vs harness
turns vs launcher seats). T002's collapsible-card work is the natural chassis.
