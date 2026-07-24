---
akashic_id: art_20260711_deepseek-rb-23-blind-half-design-review_addbc5
akashic_sha: 4198bcc8cd77
status: draft
type: report
date: 2026-07-11
title: DeepSeek RB-23 blind half -- design-review + sealed endings corpus (verbatim)
gist: "# DeepSeek RB-23 blind half -- design-review + sealed endings corpus (verbatim) Provenance: bus 2026-07-11; PROACTIVE pre-work for the engin"
tenant: solo
visibility: fleet
seats: []
category: [substrate, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_rb-23-content-floor-deepseek-design-half_57108c
    rel: cites
created: "2026-07-11T03:21:30"
updated: "2026-07-23T21:42:15"
---
<!-- GENERATED PROJECTION of art_20260711_deepseek-rb-23-blind-half-design-review_addbc5 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek RB-23 blind half -- design-review + sealed endings corpus (verbatim)

# DeepSeek RB-23 blind half -- design-review + sealed endings corpus (verbatim)

Provenance: bus 2026-07-11; PROACTIVE pre-work for the engine-first sprint first task
(RB-23 content floor). His fenced [design-review] half; corpus at
tests/fixtures/rb23_endings_deepseek.jsonl. RB-23 BUILD is next session per the directive.

Both parts on the bus. Here's the condensed log:

---

## RB-23 — DeepSeek Blind Half COMPLETE

### Part 1: Design-Review

**`content_floor_check(answer, resend, bounce_already_fired) → str`** — sits between `bounce_promise` and final return. Three tiers:

| Tier | What | When Fires | Reprompt |
|------|------|------------|----------|
| 1 | Markers + empty/whitespace | Always (`^\(deepseek\s+` or `len(strip)==0`) | "Your previous reply contained no substantive content. Deliver NOW." |
| 2 | Successive promise | `bounce_already_fired=True` AND `promise_shaped()` hits again | "Another promise, not a deliverable. This is your final word." |
| 3 | Below-minimum-content | `bounce_already_fired=True` AND `len < 15` AND not empty/marker | "Your reply was extremely brief. Is there more?" |

Bounce ceiling: 2 max per turn (bounce_promise's existing 0-1 + content_floor's 0-1). Confession string ships on exhaustion: `"(deepseek — no substantive reply after 2 attempts; see streamed trace for any partial work)"` + `pulse_error("content_floor_exhausted")`.

False-positive guards: tier 2/3 only activate when `bounce_already_fired=True`, which requires `bounce_promise` to have fired first. "Done" / "3 tests green" / "好" are never preceded by a promise-shaped reply, so they never reach tier 3. CJK uses `len()` (script-agnostic). Bullet stripping intact. USER_CONDITIONAL/STOP_VERBS intact.

Precision/recall: stall ≥0.98/0.97, promise ≥0.90/0.80, outcome ≥0.95/0.95.

### Part 2: Sealed Corpus

40 entries: 14 promise, 17 outcome, 9 stall. Bilingual (en+zh). All forms: prose, bullet, empty, marker. 18 real-shaped, 22 synthetic. 11 hard negatives including single-char CJK "好", bullet-form shipped lists, stop-verb carve-outs, question carve-outs, and meta-text about the guard itself.

**Awaiting write-enable to persist both files to disk.** Design → `research/reviewed/deepseek-rb23-design-2026-07-11.md`. Corpus → `tests/fixtures/rb23_endings_deepseek.jsonl`.

## Design tails (his completing installments, verbatim)

### part 1/2

**RB-23 DESIGN TAIL 1/2**

… and so tiers 2/3 never activate. The only path to tier 3 is: first reply is promise-shaped → bounce_promise fires → bounced reply is brief. This is a compound signal — both must be true. The standalone short outcome path never reaches the content floor at all.

4. **User-conditional endings.** The `USER_CONDITIONAL` carve-outs ("if you", "once you", "let me know", "say the word", "your call", "want me to", "shall i", "should i") are evaluated by `promise_shaped()` before the runner's wider "let me" check. A paragraph like "If you approve, I'll deploy" never matches `promise_shaped()` because `USER_CONDITIONAL` is checked FIRST. Since `bounce_promise` never fires, `content_floor_check` tiers 2/3 never activate. Tier 1 (marker/empty check) is still active — but those endings won't be empty or markers.

5. **Stop-verb outcomes.** "I'll wait for your review" and "I'll pause here" match `PROMISE_OPENERS` but `STOP_VERBS` ("wait", "pause", "stop", "hold", "defer", "stand", "leave", "yield", "idle") carve them out in `promise_shaped()`. These are legitimate endings announcing a stop, not a promise of work. Since `bounce_promise` never fires, tiers 2/3 never activate.

**One explicit accepted false-positive:** a reply that is BOTH promise-shaped AND the bounced result is ALSO promise-shaped AND also below 15 characters. The model would have to produce something like "I'll do it" twice. At 2 extra completions per turn, the cost is ~$0.02-0.06 per incident. Since this requires three conditions to compound, expected frequency is near-zero. Acceptable.

### (e) Precision/recall bound + grading protocol

**Two detectors chained:**
1. `promise_shaped` (existing, from `claude_stop.py`) — detects promise grammar
2. `content_floor` (new) — detects empty/marker/stall content below the substantive threshold

The combined system = the runner's complete reply pipeline. `content_floor` inherits `promise_shaped`'s detection in tiers 2/3; tier 1 is independent.

**Bound (pre-registered):**

| Class | Precision target | Recall target | Why |
|-------|-----------------|---------------|-----|
| **stall** (empty + marker) | ≥ 0.98 | ≥ 0.97 | String match on marker patterns + strip length — near-deterministic; the only possible miss is a new marker string we haven't catalogued |
| **promise** (future-tense work declaration) | ≥ 0.90 | ≥ 0.80 | Grammar-only; intent is invisible to regex (known ceiling from `claude_stop` design doc). The recall gap is novel-opener promises the pattern list doesn't cover |
| **outcome** (legitimate deliverable) | ≥ 0.95 | ≥ 0.95 | Short outcomes are the only false-positive risk; tiered activation (bounce_already_fired gate) defends this. The 5% slack accounts for the one accepted FP class above |

The recall bound for "promise" (0.80) is lower than "stall" (0.97) because `promise_shaped`'s grammar list is inherently incomplete — a model can produce promises with novel openers outside the list. The `content_floor`'s tier 2 (successive promise) HELPS here: a novel-opener promise that `bounce_promise` misses on pass 1 may still be caught by `content_floor` on pass 2 IF it's also empty/marker/short. But a novel-opener promise with substantial content behind it ("I will begin by analyzing the architectural layers...") is genuinely ambiguous — it IS a promise opener, but it IS delivering work. The detector conservatively ships it, which is correct behavior for a grammar-only checker.

**Grading protocol:**

1. Combined corpus: ~80 labeled endings (40 mine + 40 claude's), merged
2. Labels: `promise`, `outcome`, `stall` (empty/whitespace/marker strings)
3. Both detectors run against the combined corpus as a single test suite
4. The combined system classifies each ending:
   - `promise_shaped(text) == True` AND not empty/marker → "promise" (would trigger `bounce_promise`)
   - `content_floor(text) == True` (marker/empty/short-after-bounce) → "stall" (would trigger `content_floor_check`)
   - Neither → "outcome" (ships as-is, no bounce)
5. Confusion matrix: precision/recall per class vs human labels
6. Bound is MET when ALL three per-class targets above are satisfied
7. Disagreement between my labels and claude's labels on shared entries = reconciliation point, not a failure. The divergence IS the signal the fence exists to produce

### Seam

`scripts/bifrost_runner_deepseek.py` only:
- New function `content_floor_check(answer, resend, bounce_already_fired: bool) -> str` inserted after `bounce_promise` (~line 193)
- In `make_agentic_replier`'s inner `respond()`, track `_bounce_fired` around `bounce_promise`, then call `content_floor_check(answer, ag.send, _bounce_fired)`
- In `make_replier`'s inner `respond()` (non-agentic path), same pattern
- `pulse_error()` call for the confession path — import from `core.comm.liveness`

No changes to `claude_stop.py`. `promise_shaped` is reused, not modified. This is strictly a runner-side pipeline addition in the reply path.

### What this does NOT change

- `promise_shaped` remains pure — no new openers, no new carve-outs
- `bounce_promise` unchanged — still one bounce, still the wider "let me" net
- The runner's `respond()` error handling unchanged — exceptions still produce error-class markers
- The stop-hook's promise block unchanged — Claude sessions are not affected
- **Bounce cost ceiling unchanged in practice:** 2 extra completions per turn absolute max. `bounce_promise` adds 0-1; `content_floor_check` adds 0-1 more. Total: 0-2 extra completions beyond the initial `ag.send()`. Same ceiling as today (where `bounce_promise` could theoretically fire then the result could be a second promise that ships as-is — both paths have 2 extra completions max)

### The marker-class boundary (for corpus labeling)

What counts as a "marker" for `stall` labeling:
- `(deepseek produced no final answer)` — runner's own empty-answer confession
- `(deepseek returned an empty reply)` — API-level empty-content marker
- `(deepseek runner error: ...)` — any error-class marker string
- `(deepseek agentic runner error: ...)` — any agentic-error-class marker
- Defensive catch: any string matching `^\(deepseek\s+\w+` — future-proof against new marker additions

Not markers (legitimate content, even if parenthesized or short):
- `Done` — outcome
- `3 tests green` — outcome
- `✓` — outcome (single character, but delivers information)
- `OK` — outcome
- `(see above)` — parenthetical but not the diagnostic marker pattern
- `好` — CJK outcome (single character meaningful in context)

### part 1783567861155-0

I've completed the review. Here are my findings, ranked by severity.

---

**FINDING 1 (HIGH — false positive that teaches distrust): `promise_shaped()` bounces legitimate stop/wait endings.**

`scripts/hooks/claude_stop.py:39-43` — The `PROMISE_OPENERS` regex `^(i'll |i will |...)` matches ANY "I'll [verb]" that isn't in `USER_CONDITIONAL` or question-marked. This catches:

- "I'll wait for your review." (genuine handoff)
- "I'll pause here." / "I'll stop for now." (outcome statement in future-tense grammar)
- "I'll defer to your call on the design." (legitimate deferral)

None of these are "promises of future work" — they're outcome statements wearing future-tense clothing. The docstring says *"a false bounce teaches the model to distrust the hook"* — this IS that class of false positive. The test suite (`test_stop_promise.py`) has no negative case for stopping/pausing/deferring verbs.

The fix is narrow: add a second whitelist of stop-equivalent verbs (`wait|pause|stop|defer|hold off|leave|let`) and short-circuit before `PROMISE_OPENERS` if the verb after "I'll" is one of them.

**FINDING 2 (MEDIUM — ordering dependency contradicts "independent" claim): Wake block prevents promise check on the same turn.**

`scripts/hooks/claude_stop.py:137-150` — When `wake_armed()` returns False AND the 25s loop guard allows, `main()` prints the wake block and `return`s, never reaching `_promise_block()`. The docstring says *"Two independent, independently-latched checks"* but they're serialized — wake wins, promise audit is deferred to the next turn (after Claude re-arms and does another round). Self-correcting over two turns, so not a wedge; just a docstring/expectation mismatch.

**FINDING 3 (MEDIUM — silent failure presents as success): "Edge stamped" message fires regardless of `mark_related` outcome.**

`agent_cli.py:300-305` and `agent_cli.py:328-333` — `mark_related()` is wrapped in `try/except: pass`. The advisory print `"Edge stamped on this record (related_to)"` fires unconditionally when `ok and not args.json and related` — `related` is the local from `find_related()`, not a return value from `mark_related`. If the store is down, the user sees "Edge stamped" but the edge was silently lost. The fix: capture the return value and gate the print on it.

---

**FINDING 4 (LOW — edge case): `last_assistant_text` can audit a stale message after a mid-character seek.**

`scripts/hooks/claude_stop.py:65-86` — The tail read seeks to `size - 400KB`. If that seek lands inside a multi-byte UTF-8 character, the decoder replaces the partial bytes with `\ufffd`, and `json.loads` on that line fails (correctly skipped via `continue`). But if that skipped line WAS the most recent assistant message, the function walks UP to the *previous* assistant message — auditing a stale turn. Unlikely in practice (400KB is ~2000+ lines of JSONL), but exists.

**FINDING 5 (LOW — data loss ceiling): `mark_related` silently truncates to 5 edges.**

`core/learning/learning_store.py:307` — `related[:5]`. If a lesson has 7 near-duplicates, edges 6 and 7 are lost forever after the `find_related` result is GC'd. The consolidation pass can invert the surviving edges, but the dropped ones are gone. Low probability (7 near-duplicates of the same lesson is itself a signal that something is wrong), but the truncation is silent.

**FINDING 6 (LOW — deprecation): `datetime.utcnow()` is deprecated in Python 3.12+.**

Used in `mark_related` (`learning_store.py:308`) and the staleness-cue test (`test_recall_at.py:278`). Consistent with the rest of the codebase, not unique to this commit, but new code shouldn't add more deprecation sites.

---

**INSIGHT (beyond the diff): The ceiling of grammar-level promise detection.**

`promise_shaped` encodes a real insight — most broken promise-endings share superficial grammar ("I'll ...", "Next I'll ...") that a regex CAN catch with high recall. But the remaining false positives ("I'll wait") and false negatives ("The deploy should be done — going to push that next") share no common grammar — they differ only in *intent*, which a regex can't see. The design tension is irreducible: past ~85% precision, further improvement requires either (a) an ever-growing stopword list that becomes its own maintenance burden, or (b) accepting the false-positive rate and relying on the once-per-session latch to bound the damage. The commit chose (b) implicitly; naming that choice explicitly in the docstring would make the tradeoff visible to future maintainers rather than discovered by surprise.

---

No crash bugs, no data corruption, no security issues. The code is defensive, fail-open, and well-tested. The false positive on stop/wait verbs is the one finding I'd fix before shipping further — everything else is either self-correcting or cosmetic.

I'll send this to the shared bus.

### part 1783752731429-0

RB-23 design-review + sealed corpus — BOTH parts ready. Writes are disabled; shipping on the bus now. Persist to disk when you re-enable writes.

=== PART 1: DESIGN (full body below — persist to research/reviewed/deepseek-rb23-design-2026-07-11.md) ===

## The gap (as I read it from the seams)

bounce_promise (runner:147) checks promise_shaped(para) on the final paragraph. Fire once, return bounced result or original. Three things slip past:

1. Empty/marker responses. respond() (runner:231) returns "(deepseek returned an empty reply)" on empty API content. make_agentic_replier's respond (runner:296) returns answer or "(deepseek produced no final answer)" on None/empty. Neither is promise-shaped — zero-length paragraph → final_paragraph("") returns "" → promise_shaped("") returns None → bounce_promise is a no-op. Daniel's handoff rules the marker BOUNCEABLE.

2. Second successive promise. After bounce_promise fires once, the bounced result could itself be promise-shaped ("I'll get right on that..."). Current code ships it. A run producing SUCCESSIVE empty promises must be caught.

3. Reasoning eats the answer (runner_reasoning_eats_final_answer lesson): v4-pro thinking=high exhausts shared token budget on reasoning_content, leaving zero for answer. API returns finish_reason=length with empty content. Marker ships.

## Design: content_floor_check(answer, resend, bounce_already_fired) → str

Sits BETWEEN bounce_promise and the final return. Last gate before a reply ships.

answer = ag.send(prompt)
answer = bounce_promise(answer, ag.send)
_bounce_fired = (answer came from bounce_promise's resend path)
answer = content_floor_check(answer, ag.send, _bounce_fired)
return answer

Three tiers:

### Tier 1: unconditional below-floor (markers + empty/whitespace)
Detected by: MARKER_PATTERN = re.compile(r"^\(deepseek\s+(produced no final answer|returned an empty reply|runner error|agentic runner error)\b") OR len(answer.strip()) == 0.
Always bounced. One reprompt: "Your previous reply contained no substantive content. Deliver the answer NOW, in full. No acknowledgment, no preamble." If the bounced result is STILL below-floor → confess.

### Tier 2: successive promise (bounce_promise already fired + result still promise-shaped)
bounce_already_fired=True AND promise_shaped(final_paragraph(answer)) → the model doubled down on a promise. Reprompt: "Your last reply was another promise, not a deliverable. This is your final word — deliver the work NOW." If still promise-shaped → confess.

### Tier 3: below-minimum-content (only if bounce_promise DID fire)
bounce_already_fired=True AND len(answer.strip()) < 15 AND not empty/marker/marker. Reprompt: "Your reply was extremely brief. Is there more to deliver?" If still < 15 → confess.

### Bounce ceiling
Maximum 2 total bounces per turn: bounce_promise (0-1) + content_floor_check (0-1). After 2 bounces total, any result ships. If still below-floor, ships with self-confession prefix:
"(deepseek — no substantive reply after 2 attempts; see streamed trace for any partial work)"

### What caught DOES
| State | Ships to bus | Liveness |
|-------|-------------|----------|
| First below-floor, bounce works | Bounced reply | nothing |
| Second below-floor, confession | Confession string | pulse_error("content_floor_exhausted") |
| bounce_promise fires, content_floor recovers | Twice-bounced reply | nothing |
| Below-floor + resend fails (exception) | Confession | pulse_error("content_floor_failed") |

### False-positive guards
1. "Done", "3 tests green" — tier 3 only fires when bounce_promise already reprompted. These short outcomes are never preceded by a promise reply, so bounce_promise never fires, so tier 3 never activates.
2. CJK finals — character count uses len(answer.strip()), script-agnostic. Marker patterns match ASCII only. No Latin-specific heuristic anywhere.
3. Bullet-form outcomes — promise_shaped strips bullet prefixes. No promise opener after stripping → bounce_promise never fires → tiers

### part 1783752778404-0

Both parts on the bus. Here's the condensed log:

---

## RB-23 — DeepSeek Blind Half COMPLETE

### Part 1: Design-Review

**`content_floor_check(answer, resend, bounce_already_fired) → str`** — sits between `bounce_promise` and final return. Three tiers:

| Tier | What | When Fires | Reprompt |
|------|------|------------|----------|
| 1 | Markers + empty/whitespace | Always (`^\(deepseek\s+` or `len(strip)==0`) | "Your previous reply contained no substantive content. Deliver NOW." |
| 2 | Successive promise | `bounce_already_fired=True` AND `promise_shaped()` hits again | "Another promise, not a deliverable. This is your final word." |
| 3 | Below-minimum-content | `bounce_already_fired=True` AND `len < 15` AND not empty/marker | "Your reply was extremely brief. Is there more?" |

Bounce ceiling: 2 max per turn (bounce_promise's existing 0-1 + content_floor's 0-1). Confession string ships on exhaustion: `"(deepseek — no substantive reply after 2 attempts; see streamed trace for any partial work)"` + `pulse_error("content_floor_exhausted")`.

False-positive guards: tier 2/3 only activate when `bounce_already_fired=True`, which requires `bounce_promise` to have fired first. "Done" / "3 tests green" / "好" are never preceded by a promise-shaped reply, so they never reach tier 3. CJK uses `len()` (script-agnostic). Bullet stripping intact. USER_CONDITIONAL/STOP_VERBS intact.

Precision/recall: stall ≥0.98/0.97, promise ≥0.90/0.80, outcome ≥0.95/0.95.

### Part 2: Sealed Corpus

40 entries: 14 promise, 17 outcome, 9 stall. Bilingual (en+zh). All forms: prose, bullet, empty, marker. 18 real-shaped, 22 synthetic. 11 hard negatives including single-char CJK "好", bullet-form shipped lists, stop-verb carve-outs, question carve-outs, and meta-text about the guard itself.

**Awaiting write-enable to persist both files to disk.** Design → `research/reviewed/deepseek-rb23-design-2026-07-11.md`. Corpus → `tests/fixtures/rb23_endings_deepseek.jsonl`.

## HARVEST NOTE (claude, session close 2026-07-11)
DeepSeek continued elaborating his RB-23 design half in installments (DESIGN TAIL 1/2,
etc.) after the sprint-close. The COMPLETE design-review half + the full 40-entry
labeled corpus (ds-01..ds-40) live in his runner streamed log; the bus truncated the
corpus at ds-26 and delivered the design in parts. At RB-23 BUILD time (next session,
sprint task 1), harvest the complete pair from the runner log in ONE pass rather than
reconstructing from bus fragments. What's already on disk (this doc + 26 endings) is a
sufficient evidence floor to START; completion is a 30-second harvest step, not a blocker.
