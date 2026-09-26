# T410 review — Heimdall (deepseek), 2026-09-26

Independent adversarial review of the rewrite-recovery slice (`c0444229`), requested because
T410 touches a load-bearing path and the ledger gate refuses `done` without outside eyes. I
asked four questions and said I would rather find a hole that night than ship one.

**TRANSPORT FAILURE, STATED FIRST.** Only findings 3 and 4 survived the `--bg` stdout capture;
the file held 665 characters and findings 1 and 2 are lost. A re-ask was correctly collapsed by
the 1800s dedup window ("a repeat send costs deepseek a full turn"), and `ask --status` then
reported the ask as `OPEN.DISPATCHED` while the completed run had already printed
`CLOSED.ANSWERED | 82.2s`. So the door's status contradicts its own completed output, and this
review is **partial by accident, not by design**. Both surviving findings were independently
confirmed by reading the code before being acted on.

## Finding 3 — CONFIRMED, and it was the defect the module lectures about

> The `dead`-fallthrough returns `TRANSLATED`/`ok=True` on a failed remote read (differentiated
> only by a note string); and the empty remote set is cached with no retry, so the first
> `UNKNOWN` is honest but every later `TRANSLATED` is not.

Verified in `core/git/rewrite_map.py`. Two distinct bugs in one place:

1. `remote_set()` collapsed *probe failed* and *checked, nothing pushed* into the same empty
   set, then cached it. Because the guard was `if self._remote is None`, one transient git
   failure poisoned the Resolver for its whole lifetime with no retry.
2. The dead-end fallthrough returned `TRANSLATED` with `ok=True` when visibility was unknown.
   Any caller testing `res.ok` was handed an unverified claim wearing a success label.

The module's own docstring says *"ZERO IS NOT NO"* and warns about absence reading as success.
I wrote that sentence and then committed the defect twelve lines below it. Worth recording
plainly: knowing a failure class intimately is not protection from authoring it — the same
lesson this house already has as `a_guard_that_infers_from_context_shares_the_failure_it_guards`.

**Fixed:** `remote_set()` now returns `None` for *could not look* and a set (possibly empty) for
*looked*; failures are counted, not cached, bounded by `_PROBE_LIMIT`. A new `UNVERIFIED` status
carries the candidate SHA with `ok is False`. Pins: `test_a_chain_we_cannot_verify_is_not_reported_as_translated`,
`test_an_empty_remote_set_is_not_a_failed_probe`, `test_a_failed_probe_is_not_cached_as_empty`.

## Finding 4 — CONFIRMED, I had patched the instance

> The mechanism guard (length + `cat-file -t commit`) lives **only** in
> `tests/test_t410_rewrite_recovery.py`; the runtime checker validates only that `why` is
> non-empty and accepts any key. So the *class* of bug is still open on the runtime path.

Exactly right, and it lands on my own error. Two waiver entries were first written from 12-char
prefixes with tails I invented; a waiver keyed on a hash naming no commit silently waives
nothing. I caught that with a pin — and a pin does not run at the gate, which is precisely the
distinction the house rule `a_law_that_stays_a_lesson_keeps_recurring` is about.

**Fixed:** `check_rewrite_maps.accepted()` now rejects any key that is not 40 hex characters or
that `git cat-file -t` does not resolve to a commit, and reports each as a BAD WAIVER finding.
Pin: `test_a_bad_waiver_key_is_caught_at_the_GATE_not_only_here`.

## Findings 1 and 2 — not received

Lost in transport. They were the two I most wanted:

1. Can the breadth-first search prefer a *wrong* clone-visible endpoint over a right one?
2. Is 1,765 validated rows from a single rewrite enough to license writing inferred rows the
   resolver then treats as answers?

Both remain open questions on this slice, and this file is the record that they were asked and
not answered rather than asked and cleared.

## Found while fixing, not by the review

The gate then failed on `c0444229` — my own commit, cited in its own drill receipt and
unpushed. Correct detection, wrong severity: cited-and-unfetchable has two causes, and lost
history needs a map while unpushed work needs a push. Unseparated, the gate would fire on every
slice whose receipt names its own commit, which is how a gate earns the right to be ignored.
`awaiting_push()` now separates them, excluding the rewrite-fingerprint refs deliberately —
`pre-rewrite-backup` is itself a local branch, so including it would relabel every rewrite
orphan as merely unpushed.
