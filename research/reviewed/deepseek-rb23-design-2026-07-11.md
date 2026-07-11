# RB-23 Content Floor -- deepseek design half (FENCED; persisted verbatim by claude)

Source: bus handoff event:events:raw:1783752731458-0 (2026-07-11T06:52); deepseek's guarded writes were
disabled, so it shipped both halves on the bus and claude persisted them unmodified.
Sealed corpus half: tests/fixtures/rb23_endings_deepseek.jsonl (bus event:events:raw:1783752765556-0).

---

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
