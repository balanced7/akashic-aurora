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

---

# Second pass — the two questions that were lost

Re-asked as a narrower brief (a different prompt, so the dedup window did not collapse it) and
received in full: 15,885 characters, 129.8s, ask `1790442428036-0`. All four questions are now
answered.

## Q1(a) — map order decided the answer. REAL as a mechanism, LATENT in this checkout.

> 162 old SHAs appear in more than one map with *different* targets. The BFS returns on the
> first `visible()` target, and `load_maps` sorts by directory name, so an EARLIER rewrite's
> target wins even when a LATER rewrite moved it again.

The mechanism is exactly right and I had not seen it. One correction to the count: **43, not
162** — the larger figure includes filter-repo *identity* rows (`old == new`), which are not
successor claims but a record that a given run left a commit alone. Excluding those gives 43,
which matches independently the 43 rows the reconstructor reports as extending a recorded chain.

Then the measurement he himself proposed as decisive, which I ran:

| of the 43 divergent old SHAs | count |
|---|---|
| **both** targets clone-visible — a stale successor returned today | **0** |
| exactly one target visible — current code lands correctly | 43 |
| no target visible — dead-end path | 0 |

So it was returning the right answer for the wrong reason. **Latent is not safe here**: after the
queued 577-commit rewrite the superseded targets stay visible locally until origin is updated,
which makes this live during precisely the operation the module exists for.

**Fixed.** `resolve()` no longer returns on the first visible hop. `_endpoints()` chains to
exhaustion and the endpoints are *ranked*: clone-visible first, then farthest forward (later
rewrites sit deeper), then fewest inferred hops — a record beats a deduction, which is also
finding 1(c). Bounded by `_VISIT_BUDGET`, and the caller is told when the budget bit.

## Q1(b) — the "longest chain" comment was false. CONFIRMED.

A single global `seen` set pruned any node a second chain reached later, collapsing a
re-convergent history onto the first route that touched it. He is right that it does not change
the returned SHA, only the `hops` an auditor reads — a documentation-vs-behaviour mismatch.
**Fixed** by giving the DFS a per-path visited set, which is affordable because fan-out is
bounded by the number of maps.

## Q1(c) — no recorded-beats-inferred rule existed. CONFIRMED.

`lookup()` never branched on `method`; the write-time contradiction guard only fires during
`reconstruct --write`, and once a reconstructed map is committed the resolver read it with equal
authority. **Fixed** as the third ranking key.

## Q1(d) — a boolean cannot say "ambiguous". CONFIRMED.

`visible()` answered True/False, so a short citation naming two live commits read as `CURRENT` —
a wrong *status*, not a wrong successor. **Fixed:** `live_matches()` counts instead of asserting.

## Q2 — "stop arguing from N and start arguing from structure". The best point in the review.

> `tree_agree` is computed and printed and **not enforced** — the one signal that would catch a
> wrong `(author-date, subject)` match is available and discarded. And the parent DAG is a
> rewrite invariant, free from `git rev-list --parents`, and unused.

Both true. Also true and worth repeating: my 100% figure was **precision on decided rows**, and
the 41 declines — the rows where the key was *not* unique, i.e. where the method is most likely
wrong — were excluded from the denominator. I reported precision and called it agreement.

**Fixed.** Every written row must now carry an independent structural signal, and a name-only row
is dropped unless `--uncorroborated` is passed. Three tiers, reported separately so none
overstates another: `tree` (content unchanged), `parent` (a matched or already-mapped first
parent — the rewrite invariant), and `parent-key` (both parents share author-date and subject:
the same name heuristic one generation up, independent of *this* commit but not of the *method*).

Result on the maps already committed:

| population | matched | tree | parent | parent-key | **name only** |
|---|---|---|---|---|---|
| ref-based (the residue map) | 116 | 73 | 114 | 0 | **0** |
| citation-based | 746 | 63 | 744 | 2 | **0** |

**Two intermediate results worth recording because each was my check being wrong, not the data.**
First pass reported 660 of 746 as name-only — caused by `parents_of` using `git log --all`, which
cannot see a commit on no branch, and by not consulting existing maps for the parent's remap.
Second pass reported 0 for the `parent-key` tier — caused by building the key lookup from the two
matched populations only, where the parents do not appear. Both fixed; both would have read as
"the inference is weak" if I had trusted the first number.

And the row this lands hardest on is my own: the single-row `2026-09-26-cited-gap` map **was
name-only** under the first implementation and would have been refused by the rule I had just
adopted. It is corroborated by the weaker `parent-key` tier, its meta.json now says exactly that,
and the reason the check could not see it at first is that the commit sits on no branch — the
case a `git gc` deletes, which is why it was worth recovering in the first place.

**Not done:** his parent-DAG suggestion is implemented on the *first* parent only. A merge
commit's later parents are unchecked.
