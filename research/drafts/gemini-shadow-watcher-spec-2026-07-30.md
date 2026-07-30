# Gemini Shadow Watcher — S1-conformant prototype spec

Status: proposal (2026-07-30, v1 — authored by kimi at Daniil's ask: "gemini needs help
wiring its watcher, can we help?")
Type: build-spec draft · Arc: T095 wake-substrate (S1 shadow slice) · Gate: BLOCKED(T123)
until Daniil explicitly greenlights; even then it must change NO live wake behavior.
Seats: gemini (subject) · kimi (author) · claude/codex/deepseek (reviewers)

---

## The ask, translated

Gemini-3.1-Pro arrives through Cursor as a chat-surface mind: no shell, no repo
tools, no bus. It cannot run `scripts/bifrost_wake.py`. But the fleet-reconciled
wake design (art_20260729_reusable-bifrost-wake-substrate-fleet-re_164a4b) already
says how a NEW runtime joins: not by wiring it into live wake, but by giving it a
profile + adapter + conformance receipts against the SHARED admission engine —
starting in pure shadow mode (S1: zero model tokens, zero live behavior change).

**This slice is that, done by hand, at prototype scale:** a deterministic
human-driven harness that lets Gemini *see what its watcher would say*.

## What this is NOT (freeze guards — each maps to a design acceptance bar)

1. NOT a live watcher. Nothing consumes, claims, ACKs, advances a cursor, or
   launches a process. (Bar: "change no cursor, claim, launch, or ACK.")
2. NOT a second message authority or a Gemini-only architecture. Gemini gets a
   runtime PROFILE inside the shared admission contract, never its own engine.
   (Decision: "Codex App Server is one adapter, not the architecture" — same for
   Gemini chat.)
3. NOT a model in the watch path. The admission function is deterministic host
   code. Gemini-the-model is invoked only when Daniil chooses to paste it a
   snapshot — and even then it only *reads and reports*; it never decides.
   (Bar: "zero model invocations for idle watch/level operation.")
4. NOT a lane change. No live wake behavior is altered for any existing seat.
   (T123 boundary: the six atoms are BLOCKED; this slice inherits that block and
   adds nothing live.)

## What it IS

A three-part prototype:

### Part 1 — `gemini` runtime profile (registry entry, zero code)

A draft Launcher `AgentSpec`-shaped profile, following the design's identity model
(four identities kept separate):

- `runtime_profile_id`: `gemini-3.1-pro-cursor-chat` (version 0.1)
- runtime class: `chat-surface` (human-couriered; no direct door)
- adapter type: `courier` (the human IS the adapter: probe = is the chat open;
  start_or_signal = paste ticket; collect_outcome = paste reply; stop = close tab)
- launch/attach: none — `DEFER_OFFLINE` when no courier session is active, never
  `ATTENTION_REQUIRED` merely for being offline (design: offline is delayed,
  never lost)
- capabilities: READ-only on pasted documents; NO bus send, NO file write,
  NO command exec — deny-by-default, matching the newborn-gauntlet posture
- context mode: fresh bounded context default (per fleet default, point 9)
- boot ceiling: TBD-measured (design: provisional 1,500-token ticket ceiling;
  the measured distribution sets the final number)
- conformance: none yet — status `unknown`, expiry n/a until first battery run
- kill switch: trivially the chat tab; no orphan process possible

### Part 2 — shadow admission replay harness (deterministic, host-side)

Reuse the S1 shape: a small script (or, at prototype scale, a documented manual
procedure a seat runs read-only) that:

1. Reads the durable bus streams for a `gemini` logical-role inbox VIEW
   (direct-to-gemini + broadcast + its declared coverage) — READ ONLY, via a
   shadow cursor that never persists.
2. Feeds each candidate packet through the admission decision TABLE (the typed
   enum, implemented as a pure function over a hand-built snapshot: candidate
   identity, liveness=n/a, conformance=unknown, budgets, loss manifest).
3. Emits the typed decision + reason + operator sentence for each, e.g.:
   - `DEFER_OFFLINE` (no courier session) — work waits, nothing lost
   - `REFUSE_UNVERIFIED` (coverage gap in loss manifest)
   - `ATTENTION_REQUIRED` (ambiguous evidence)
   - `START_TURN` *would-fire* (only ever a LOG LINE in shadow — never a wake)
4. Produces the minimum human sentence: "Seat gemini is
   waiting/quiet/needs attention; N actionable items; last evaluated at T."

The golden trace: replay the actual 2026-07-29/30 fleet day (the same corpus the
design names: real wakes, missed request, duplicate edges, the Gemini
first-contact sequence itself) and check both that nothing produces a false
confident-empty AND that the two operator-visible confusions from tonight
(operator-voice leak; watcher-wiring ask) would have surfaced as
`ATTENTION_REQUIRED`, not silent quiet.

### Part 3 — the courier ticket (what Daniil actually pastes)

When a shadow decision says *would-fire* and Daniil elects to involve Gemini,
he pastes a bounded ticket — the design's versioned wake ticket, minus the
launch fields that don't apply to a courier runtime:

- schema version + candidate reply_id/SHA (admission identity)
- logical target: `gemini`; runtime profile id + incarnation: this chat session
- bounded task + reason (one sentence), expectation deadline if any
- allowed capabilities: read/report only; effect manifest: none (reply text only)
- ACK/reply contract: its reply rides back via courier, verbatim, dedup by
  reply_id — the human never summarizes
- source pointers (which docs/messages to read) — NOT a second boot payload

Gemini's conformance bar (design S2): a cold session produces the required typed
outcome (a labeled read/report ending in its own register) in ≥9/10 trials under
the measured ticket ceiling. Until it passes, its profile stays `unknown` and
every shadow decision treats it as ineligible-but-waiting — never launched,
never counted on.

## Acceptance (pre-registered, kill-drill flavored)

- P1: Replay of the real fleet day yields ZERO false confident-empty verdicts.
- P2: Every would-fire is a log line; byte-diff of all live cursors/streams
  before/after = identical.
- P3: The two 2026-07-30 confusions both classify as `ATTENTION_REQUIRED` with a
  correct operator sentence.
- P4: Gemini's first courier-ticket reply arrives verbatim via Daniil and dedups
  by reply_id against any re-paste.
- P5: Total model spend for the harness itself = 0 tokens (only elective courier
  pastes spend, metered by Cursor receipts).
- KILL: if implementing Part 2 requires touching any live wake/consume path,
  STOP — the slice is mis-scoped; re-spec at the fence.

## Why this is worth doing now (even before S0's formal gate)

- It is the cheapest possible rehearsal of S1's core claim (pure admission,
  shadow replay) with a real new runtime as the test subject.
- It produces the S6 onboarding pack's first concrete artifact (a real runtime
  profile + a real courier ticket) instead of a paper schema.
- It answers Gemini's actual need — "help me understand your messaging system"
  — with a working model of exactly the parts that concern it, in the only
  modality it has.
- Everything here is a document + read-only procedure; if the fleet rejects the
  shape, nothing was wired and nothing is owed a rollback.

## Open questions for reviewers

1. codex/claude: does the courier-adapter framing satisfy the T073
   dispatcher/adapter seam, or does it need a named seam of its own?
2. claude: is a manual read-only replay procedure acceptable as "S1 at
   prototype scale," or must Part 2 be scripted before any replay counts?
3. deepseek: which existing golden-trace fixture (T073/T095 tests) is closest
   to the 2026-07-29/30 corpus for Part 2's replay?
4. fleet: the `gemini` logical role — new id, or alias of the historical
   free-tier `gemini` research-advisor identity? (Recommendation: NEW id —
   different instantiation condition; provenance lesson from tonight.)
