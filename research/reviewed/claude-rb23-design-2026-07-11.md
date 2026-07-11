# RB-23 Content Floor -- claude design half (FENCED)

Date: 2026-07-11. Author: claude, blind half of the fenced dual design (method-baseline M-fence).
DeepSeek's half: research/reviewed/deepseek-rb23-design-2026-07-11.md (unread at authoring time).
Corpus discipline: my dev-set half (tests/fixtures/rb23_endings_claude.jsonl, 41 rows) was authored
and committed BEFORE the detector parameters below were frozen; deepseek's half stays sealed until
I declare the implementation frozen on the bus.

## Seam analysis (evidence)

Reply pipeline in scripts/bifrost_runner_deepseek.py `make_respond`:

    answer = ag.send(prompt)                      # may return "" (reasoning ate the final answer)
    answer = bounce_promise(answer, ag.send)      # T018: ONE bounce, promise-shaped only
    return answer or "(deepseek produced no final answer)"   # :296 -- THE GAP

Three failure classes, from the two live bites (2026-07-10/11, lesson
runner_reasoning_eats_final_answer) plus the slice text:

- **F-A marker ships as done.** Empty answer -> `bounce_promise` sees no final paragraph -> no
  excerpt -> unchanged -> the `or` substitutes the literal marker string, which ships to the asker
  as the final word. Never bounced, never flagged. Work stranded in runner logs. (Both bites.)
- **F-B second bad reply always ships.** One bounce per message by design (one is a nudge, two is
  a wedge). Bounced reply that is ALSO a promise or empty ships as-is. "Successive empty promises"
  is exactly the undetected state the slice names.
- **F-C below-floor non-empty.** "ok" / "..." on an analytical ask: outcome grammar, no promise
  opener, no content. Rare but real; handled conservatively (post-bounce position only) to protect
  precision.

## Design

### D1. `below_floor(text) -> reason | None` -- pure, beside `promise_shaped`

Lives in scripts/hooks/claude_stop.py next to `promise_shaped` (the slice names this reuse seam;
the runner already imports from there). Below floor iff any of:

1. **empty**: stripped text is empty (F-A root).
2. **marker**: matches `^\((?:[a-z0-9_-]+) produced no final answer\)$` -- the marker CLASS, not
   one agent's string (Daniel ruled the marker bounceable; the claude twin exists in the corpus).
3. **no-content**: fewer than FLOOR content units after stripping whitespace, markdown decoration
   (bullets/emphasis/fences), and bare punctuation runs. **Script-aware on purpose**: a CJK
   codepoint counts as 2.5 units, other word chars 1 -- corpus rows cl-32/cl-33 are short-in-chars
   but content-rich zh outcomes and must pass. Proposed FLOOR = 20 units (calibrated on the dev
   half only; "done, 3 tests green" = 17 latin word chars + digits -> passes at 20 with punctuation
   stripped -- verify against dev set before freezing; the held-out half is the honest check).

Returns the reason tag (empty|marker|floor) for the teaching reprompt and the stall envelope.

### D2. Bounce path rework (scripts/bifrost_runner_deepseek.py)

Positions: floor is judged at BOTH positions; the no-content floor (D1.3) additionally requires
the post-bounce position for short-but-nonempty text (F-C precision guard). Empty and marker are
below-floor at ANY position.

    attempt 0 reply
      -> below_floor(empty|marker)? bounce with no-content reprompt   (bounce kind: floor)
      -> else promise_shaped? bounce with promise reprompt            (bounce kind: promise)
    attempt 1 reply (post-bounce)
      -> below_floor(any reason, incl. no-content)? -> CATCH (D3)
      -> promise_shaped again? ship as-is (unchanged T018 wedge rule for promises)

**Bounce budget (T018 cost ceiling):** MAX 2 resends per inbound message, at most 1 per kind
(floor, promise). Each bounce = one paid completion; worst case one message costs 3 completions.
A promise bounce whose re-reply is EMPTY consumes the floor bounce next (they chain), then catches.
The existing promise one-bounce semantics are unchanged when content is above floor -- T018 pins
keep passing.

### D3. "Caught" = confession, not silence (Wave-2 spirit)

When the budget is spent and the reply is still below floor:

1. **Ship a stall envelope to the asker, never the bare marker:**
   `[stall] <agent> produced no deliverable after N attempts (reason: empty|marker|floor). Work may
   exist in runner logs: <runner window/log path>. Flagged to the doctor.`
   The asker's next move is informed; nothing pretends to be done.
2. **Emit the stall durably:** turn_metrics outcome records the stall (new outcome value `stall`
   alongside ok|error|timeout|abandoned -- one enum value, no new subsystem) so the fleet doctor's
   L2 reader can surface repeated stalls per agent; plus one `capture_event("runner_stall", ...)`
   firehose line for the audit trail.
3. **No auto-retry beyond the budget, no auto-kill** -- detection and honest reporting only; the
   doctor decides escalation (stays inside T030 L2's progress-not-presence doctrine).

### D4. Grading protocol (the pre-registered check)

Harness: tests/test_rb23_endings_corpus.py loads BOTH fixture halves (utf-8), evaluates pure
detectors only (no bus, no completions):

- label=promise rows: expect `promise_shaped` truthy at first-reply position (runner's wider net
  incl. bare "let me" openers).
- label=outcome rows: expect NO action at first-reply position (neither detector fires).
- label=stall rows: expect `below_floor` truthy at post-bounce position; empty/marker forms also
  truthy at first-reply position.

**Bounds (proposed):** on the held-out (deepseek) half: precision >= 0.95 on the combined
would-act signal (false actions on outcomes are the expensive class -- they teach distrust);
recall >= 0.80 on promises (known-hard bulletless imperatives like cl-10 may miss by design);
recall = 1.0 on stall rows with form empty|marker (mechanical -- no excuse to miss). Dev half is
tunable; held-out numbers are the gate.

### D5. Acceptance tests (pre-registered, committed BEFORE impl per M3 / T031 hook 2)

1. Two successive empty replies -> stall envelope shipped + stall outcome recorded; marker string
   never ships bare. (The slice's named acceptance.)
2. Marker-string reply at attempt 0 -> floor bounce fires (marker is bounceable).
3. "done, 3 tests green" at attempt 0 -> untouched (no bounce, no flag).
4. Short zh outcome (cl-33 class) at any position -> not below floor (CJK weighting).
5. Bounce budget: crafted empty->promise->empty sequence -> exactly 2 resends, then catch.
6. Existing T018 promise one-bounce pins unchanged (regression).
7. Corpus bound test (D4) -- xfail-armed until the seal lifts, then required green at verify.

## Open questions for reconciliation

1. FLOOR value + CJK weight: 20 units / 2.5x are dev-half calibrations -- deepseek's half may
   argue differently; reconcile on data from both halves' NEGATIVES.
2. Bare "ok" (cl-41): I labeled it stall (post-bounce-only catch). Legitimate ack in some chat
   flows -- if his half labels the class outcome, precision wins and it moves to outcome.
3. Ceiling: is 2-resends-1-per-kind the right cost cap, or flat 1 total (cheaper, weaker)?
4. Does the floor also belong in claude's own stop-hook lane now, or runner-only until a second
   bite? (My lean: runner-only; the stop hook has the human in the loop already.)
5. Stall envelope routing: reply-to-asker only, or also bifrost-nudge INFORM to Daniel's console
   on repeat stalls (>=2 in a session)?
