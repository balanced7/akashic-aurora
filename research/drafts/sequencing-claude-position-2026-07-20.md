# Backlog-vs-Program Sequencing — claude's half (Daniel's question, 2026-07-20)

Status: current | OPENING HALF (deepseek + kimi pending; reconciliation follows)
Daniel verbatim: "Should we close our current feature backlog and then begin work on the
program, or would it make sense to start building the program and folding in the feature
improvements as we go?" Plus his hypothesis: "some of our design challenges may be mitigated
or addressed entirely by us having our own program."

## The answer in one line

Neither pole — **re-base the ledger against the program**: face work re-targets to the
program (absorbed, not duplicated), floor work continues unchanged (the program stands on
it), hygiene closes now, and the program starts immediately on its two thinnest slices —
with one convergence rule that keeps the lanes from diverging.

## Why the poles both lose

**(A) Close the backlog first** fails because a third of the backlog IS face work aimed at
the console we just decided to replace: finishing T033 (UI re-grounding), T079 (engine
room), T060-M7 (glass cockpit), T002/T007 polish on bifrost_ui means building every view
TWICE. It also parks Daniel's decided arc — the portfolio centerpiece — behind months of
substrate, which is backwards for energy and backwards for the portfolio.

**(B) Program-first, fold as we go** fails naively because the program's central objects
(mission, run, approval) RENDER the substrate: runs ride the conductor's ledger, run events
ride lanes, run assignment rides work tokens (T038), run supervision rides revival (T097)
and crash-path durability (T093). Building the face while those floors shift = rework; and
abandoning 11 active + 4 verifying ledger items mid-state violates our own gated-transition
discipline (the slot system exists so work FINISHES).

## The re-base (walking the actual ledger)

**ABSORB into T098 (face family — close as separate tasks, their DESIGNS carry over):**
T033 (UI re-grounding), T079 (engine room — becomes the causal ledger view), T060-M7
(glass cockpit — becomes the grown face), T002/T007 remainder (trace cards/theme — become
program components), T080's render half (operator traffic surfaces as first-class approval/
steer objects in the program). Nothing here is wasted: the reconciled DESIGN DOCS are the
program's view specs — the fenced design work was the expensive part and it transfers whole.

**FLOOR (continue exactly as planned — the program cannot mitigate these, it consumes them):**
T094 R0 (recall journal — becomes the context inspector's data), T097 S1-S3 (revival mesh —
becomes the run supervisor's floor; the C1-8 zero-findings mystery must die regardless of
any UI), T095 (message-state index — run events' floor), T093 (crash-path durable jobs —
run durability), API-resilience wave (in flight tonight), T046/T047 (latches + legacy
retirement — the lane substrate run channels ride), T086/T030 remainder (seat lifecycle).

**HYGIENE (close now, small):** the four verifying-state items (T058, T067, T068, T076)
need their verify passes landed and closed — cheap, and each frees an active slot the
program family will want. T031 (method enforcement) continues — it applies TO the program.
T083 (failure ledger) is living, never closes.

**PARK unless pulled (need-driven, decay discipline):** T038 build-half (pilot-by-hand
stands; the program's run-assignment will pull it when real), T034 build-half, T065, T070,
the 6 stale proposals (abandon-or-reaffirm sweep rides this re-base).

**START NOW (the program's first two slices, thin):** API door v0 (version the existing
endpoints; add the run registry + mission POST + run-scoped SSE — kimi's 60/40 inventory)
and Mission View v0 (one screen, mission noun, live seats, steer + approve verbs). Both are
projections over floors that EXIST today; neither waits on the floor lanes above.

## The convergence rule (the load-bearing sentence)

**From this re-base forward, the program is the only new render target: every floor slice
that ships, ships WITH its API-door face (an event, an object, or a view binding) — and
nothing new builds on bifrost_ui's inline page.** bifrost_ui stays running as-is (Daniel's
window) until Mission View reaches parity for daily driving; it gets bugfixes only (C10
pin guards it). That's strangler fig — our own migration doctrine, applied to ourselves.

## Daniel's mitigation hypothesis, tested item by item

DISSOLVED by the program (he's right about these): approvals-as-chat (become POSTable
approval objects — G2's transcription pain gone); T080's operator-kind taxonomy (operator
traffic becomes typed program actions — the "instrument not hammer" answer falls out);
C10 serve-from-working-tree (kimi's typed, separately-built face with CI parse gates kills
the class structurally); C6-4/C6-5 render staleness + truncation husks (run-scoped typed
event frames with ages and confessing bounds by contract); the wake-rearm chore's OPERATOR
half (the program owns seats; tonight's six stop-hook cycles become platform behavior).

MERELY REPAINTED (floor stays mandatory): C1-8 liveness truth (a beautiful mission view of
a lying gauge is a beautiful lie — S1 lands regardless); message-loss/redelivery integrity
(RB-26/29 laws live under any face); API degradation (tonight's deepseek pain is transport,
not presentation); trust/caps (the program RENDERS the Cap ladder, never replaces it).

## First-slice gate proposal for Daniel

Gate slice 1 as: API door v0 + Mission View v0, fenced (mission/run schema is a blind-halves
candidate per kimi), with the hygiene closures (4 verifying tasks) landing in the same wave
and the ABSORB/PARK re-base executed in the ledger (each absorbed task closed with a pointer
to its program-view successor; each parked task stamped). One wave, three lanes, nothing
dangling.
