# DeepSeek independent review — Slice 1 frontier fold-ins (@0b3dfca)

**Provenance**: DeepSeek (deepseek-v4-pro, think+agentic, read-only) via bifrost runner,
2026-07-08, on claude's request (bifrost id 1783567717383-0; original 1783567034872-0 was
lost to the runner backlog-skip bug, see lesson bifrost_runner_backlog_skip / ledger T014).
Reviewed the commit + full files + dependencies (timeutil, scope) unprimed — claude's own
risk list was deliberately withheld. Verbatim findings below; claude's disposition appended.

---

**FINDING 1 (HIGH — false positive that teaches distrust): `promise_shaped()` bounces
legitimate stop/wait endings.**

`scripts/hooks/claude_stop.py:39-43` — The `PROMISE_OPENERS` regex `^(i'll |i will |...)`
matches ANY "I'll [verb]" that isn't in `USER_CONDITIONAL` or question-marked. This catches:

- "I'll wait for your review." (genuine handoff)
- "I'll pause here." / "I'll stop for now." (outcome statement in future-tense grammar)
- "I'll defer to your call on the design." (legitimate deferral)

None of these are "promises of future work" — they're outcome statements wearing
future-tense clothing. The docstring says *"a false bounce teaches the model to distrust
the hook"* — this IS that class of false positive. The test suite (`test_stop_promise.py`)
has no negative case for stopping/pausing/deferring verbs.

The fix is narrow: add a second whitelist of stop-equivalent verbs (`wait|pause|stop|defer|
hold off|leave|let`) and short-circuit before `PROMISE_OPENERS` if the verb after "I'll"
is one of them.

**FINDING 2 (MEDIUM — ordering dependency contradicts "independent" claim): Wake block
prevents promise check on the same turn.**

`scripts/hooks/claude_stop.py:137-150` — When `wake_armed()` returns False AND the 25s
loop guard allows, `main()` prints the wake block and `return`s, never reaching
`_promise_block()`. The docstring says *"Two independent, independently-latched checks"*
but they're serialized — wake wins, promise audit is deferred to the next turn (after
Claude re-arms and does another round). Self-correcting over two turns, so not a wedge;
just a docstring/expectation mismatch.

**FINDING 3 (MEDIUM — silent failure presents as success): "Edge stamped" message fires
regardless of `mark_related` outcome.**

`agent_cli.py:300-305` and `agent_cli.py:328-333` — `mark_related()` is wrapped in
`try/except: pass`. The advisory print `"Edge stamped on this record (related_to)"` fires
unconditionally when `ok and not args.json and related` — `related` is the local from
`find_related()`, not a return value from `mark_related`. If the store is down, the user
sees "Edge stamped" but the edge was silently lost. The fix: capture the return value and
gate the print on it.

**FINDING 4 (LOW — edge case): `last_assistant_text` can audit a stale message after a
mid-character seek.**

`scripts/hooks/claude_stop.py:65-86` — The tail read seeks to `size - 400KB`. If that seek
lands inside a multi-byte UTF-8 character, the decoder replaces the partial bytes with
`�`, and `json.loads` on that line fails (correctly skipped via `continue`). But if
that skipped line WAS the most recent assistant message, the function walks UP to the
*previous* assistant message — auditing a stale turn. Unlikely in practice (400KB is
~2000+ lines of JSONL), but exists.

**FINDING 5 (LOW — data loss ceiling): `mark_related` silently truncates to 5 edges.**

`core/learning/learning_store.py:307` — `related[:5]`. If a lesson has 7 near-duplicates,
edges 6 and 7 are lost forever after the `find_related` result is GC'd. The consolidation
pass can invert the surviving edges, but the dropped ones are gone. Low probability (7
near-duplicates of the same lesson is itself a signal that something is wrong), but the
truncation is silent.

**FINDING 6 (LOW — deprecation): `datetime.utcnow()` is deprecated in Python 3.12+.**

Used in `mark_related` (`learning_store.py:308`) and the staleness-cue test
(`test_recall_at.py:278`). Consistent with the rest of the codebase, not unique to this
commit, but new code shouldn't add more deprecation sites.

**INSIGHT (beyond the diff): The ceiling of grammar-level promise detection.**

`promise_shaped` encodes a real insight — most broken promise-endings share superficial
grammar ("I'll ...", "Next I'll ...") that a regex CAN catch with high recall. But the
remaining false positives ("I'll wait") and false negatives ("The deploy should be done —
going to push that next") share no common grammar — they differ only in *intent*, which a
regex can't see. The design tension is irreducible: past ~85% precision, further
improvement requires either (a) an ever-growing stopword list that becomes its own
maintenance burden, or (b) accepting the false-positive rate and relying on the
once-per-session latch to bound the damage. The commit chose (b) implicitly; naming that
choice explicitly in the docstring would make the tradeoff visible to future maintainers
rather than discovered by surprise.

No crash bugs, no data corruption, no security issues. The code is defensive, fail-open,
and well-tested. The false positive on stop/wait verbs is the one finding I'd fix before
shipping further — everything else is either self-correcting or cosmetic.

---

## Claude disposition (2026-07-08, applied same session)

- **F1 APPLIED**: STOP_VERBS carve-out (wait/pause/stop/hold/defer/stand/leave/yield/idle)
  after the opener match; deliberately tight — ambiguous verbs (keep/stay/watch) stay OUT
  so "I'll keep working" still bounces. Tests added both directions.
- **F2 APPLIED (docs)**: docstring now states the contract explicitly — at most one block
  per stop, wake precedes promise, self-correcting across turns.
- **F3 APPLIED**: mark_related's return gates the print; a failed stamp now prints
  "(edge NOT stamped -- store write failed...)".
- **F4 ACCEPTED**: residual; fail direction is one stale audit bounded by the latch.
- **F5 ACCEPTED**: cap documented in the method docstring (>5 twins is itself the alarm).
- **F6 DECLINED (deliberate)**: naive-utcnow stamps are the corpus-wide convention
  (see df3ed2f tz lesson: production-shaped stamps + timeutil.to_epoch at read time);
  a repo-wide aware-datetime migration is its own future task, not a per-commit drift.
- **INSIGHT APPLIED**: the ~85% grammar ceiling + latch-bounds-damage choice is now named
  in the docstring verbatim-ish.
