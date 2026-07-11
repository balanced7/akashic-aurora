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