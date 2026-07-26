# FileStore cross-process coherence — reconciled build spec

Status: current
Class: design

Dated 2026-07-25/26. Fenced dual pass: claude (measurement + probes), kimi (mechanism ruling
and rot-guards), deepseek (writer census). **Nothing in here is built. Daniel gates the
substrate edit.** A build slice must cite this document.

---

## 1. The problem, measured rather than argued

`FileStore._flush` writes the **whole in-memory dict** and `os.replace`s it onto the shared
path. The class is thread-safe via an `RLock`; it is not process-safe, and there is no
read-modify-write.

Isolated 3-process probe, pre-registered:

| | |
|---|---|
| writes attempted | 450 (3 processes × 150) |
| survived | 155 |
| **lost** | **295 — 65.6%** |
| per-worker survival | 150 / **0** / 5 |
| errors raised | **none** |

One worker's entire output was erased while it believed every single write had succeeded.
This is the store underneath the knowledge substrate.

Pinned at `tests/test_filestore_coherence.py` as `xfail(strict=True)` — deterministic by
construction (the interleave is sequenced by hand, verified 5/5), zero suite cost, and it
**fails the build** the day the write survives.

## 2. The part that changes the scope: CAS already exists, and it does not guard

`Store.cas(key, expected, value)` exists with File/Redis/Hybrid implementations, plus
`update_atomic()` with retries and `CASConflict`, plus `tests/test_store_cas.py` containing a
**passing** test named `test_lost_update_is_prevented`.

`FileStore.cas` takes `self._lock` (a `threading.RLock`), compares against `self._data` (its
own in-memory copy, **never re-read from disk**), then calls the same whole-dict `_flush()`.
All three steps are blind to other processes by construction.

Cross-process probe, pre-registered — parent `cas`, child `cas` in a separate interpreter,
parent `cas` again:

```
parent cas #1 : True
parent cas #2 : True      <- reports SUCCESS
child key present after child : True
child key present at the end  : False
```

**Every `cas()` returned True. Not one reported a conflict. The child's committed key was
gone.**

The existing test passes because it uses **one instance in one process** — both "agents" in it
are the same object. It verifies that a stale `expected` is rejected within a single in-process
instance. Its *name* is a promise it does not keep.

Two things worth stating plainly, because they change how this reads:

- **The source is honest.** `FileStore.cas`'s docstring says *"atomic under the reentrant
  lock"* — precisely what it does. Only the test name overclaims. Reading the implementation
  beat reading the label.
- **kimi's find, from the morning durability verify:** each instance constructs its **own**
  `RLock` (per-instance). So four instances in *one* process are four different locks. `cas()`
  is not cross-**instance** safe either — two FileStore objects in a single runner can lose each
  other's writes.

So this slice is **not "build CAS."** CAS exists and is bypassed by its own design.

## 3. Why a lock alone is not the fix

Established in the fence. My claim, and kimi's sharper statement of the reason:

> The lock guards the **critical section**, but the compare reads **stale state**, so the
> section is *correct-by-lock and wrong-by-data*. A cross-process lock serialises who flushes
> when; it does not make the compare true.

Under an exclusive lock: P1 loads at T0 (sees `K`), P2 commits `K'` at T1, P1 acquires at T2
and compares its stale `K` — either wrongly succeeding (clobbering `K'`) or wrongly refusing.
**The lock is necessary but not sufficient**; without it, even a correct compare races against
its own flush.

## 4. The design — A, with C as the confession layer

**Mechanism: cross-process lock + reload-under-lock.** Under the lock: re-read the file,
compare against **disk** state, mutate, flush, release. The lock spans reload→flush, so nothing
can commit in between. This is the only option that makes the compare *true*.

**The in-memory dict is demoted to a read-only cache.** Reads may be stale; writes may not.
This is a correct separation rather than a compromise — recall tolerating a slightly-old lesson
is fine; a write decision made on stale data is the defect itself.

**Rejected — B, merge-on-flush.** Any deterministic merge rule (last-writer-wins per key,
union) is a silent choice about which write matters: the same silent-loss genus with a
friendlier name. It cannot represent "these two writes conflict, someone must decide."

**Kept as the confession layer — C, version/mtime guard.** Not the mechanism. It covers the
case A cannot reach: a writer that ignores the lock entirely.

**Contention is absorbed, not raised.** `update_atomic`'s existing retry loop re-reads,
recomputes and re-attempts; `CASConflict` raises only when retries are exhausted.

**Shape:** the reload must happen *before* the mutation, so the change lands in the mutators
rather than purely in `_flush`. Keep it to **one implementation point** — a `_locked_rw()`
context manager that every mutator wraps its body in — preserving the single-writer-path
property that makes this fix bounded.

**Honest cost.** Every *write* becomes a full file read + write: real I/O amplification on the
write path. Reads are untouched, so the recall hot path stays cheap. The marginal cost is the
**read** — the whole-file rewrite was already there.

## 5. Pre-registered acceptance

Written before implementation, per the method baseline. kimi's two rot-guards are acceptance
criteria, not advice.

1. **The coherence pin flips.** `test_filestore_coherence.py` XPASSes → under `strict=True`
   that *fails the build*, which is the signal. Remove the marker in the same commit; do not
   delete the test. The companion test asserting the current silent-loss contract must be
   updated deliberately, not swept.
2. **A cross-process CAS test exists and passes.** `test_store_cas.py` gains a genuine
   multi-process sibling. Either rename `test_lost_update_is_prevented` to say what it actually
   checks, or make it true.
3. **ROT-1 — refusal is confessed, never swallowed.** A single refused write is confessed by
   the retry's re-read; a persistent refusal raises `CASConflict`. Pin both altitudes. A CAS
   that fails closed and drops the write silently is the same defect with a new mechanism.
4. **ROT-2 — the fix names its own coverage.** It must state **which writers it does not
   protect**. A fix covering only lock-aware writers while another path clobbers "reads as done
   while the leak continues."
5. **No new suite noise.** The subprocess-heavy files must fail exactly as before (`t093` ×3,
   `t086-s5` ×1, all pre-existing; `t086-s5` is pre-registered RED).

## 6. The census — RESOLVED 2026-07-26

deepseek's census landed (recovered verbatim at
`research/in-flight/deepseek-writer-census-capture-2026-07-26.md`; the bus had clipped it).
It closes the open item and settles two things I had wrong.

**ROT-2 is retired.** *"There are zero direct `json.dump` or `open('w')` paths to this file
outside `FileStore._flush()`."* The two scripts that reference the file
(`harmonize_knowledge.py`, `snapshot_knowledge.py`) are **read-only** — they `shutil.copy2`
*from* it, never to it. That is a stated method behind the negative claim, not a bare
assertion, and it is independently corroborated by kimi's enumeration of every `_flush` caller.
**One writer path ⇒ the fix touches one class and every mutator inherits it.**

**codex's incident is explained, and its guard already exists.** The 108,963 → 164 byte
collapse *was* a FileStore flush: one process's `_load()` threw, leaving `_data` empty, and the
next mutation flushed that near-emptiness over 9MB of real data. That is precisely the case the
`_degraded` flag now prevents — the store refuses to persist what it could not read. So the
incident is historical, not a writer the census missed.

**I was wrong about `git_guard`, twice over.** I had already retracted the claim that its
`JSONDecodeError` was the coherence hole; deepseek closes the remaining "then it is a third
thing" thread. It is not a third defect in this file at all — *"it's a DIFFERENT file (the git
guard's own state file, not `store_state.json`), written by a different path."* Nothing about
`git_guard` bears on this design.

**Still genuinely open:**

- **The concurrent *process* set.** The census establishes one writer *path*; it does not
  enumerate which long-lived processes hold a FileStore against the canonical file
  simultaneously. One path with five live processes is still the hole. This does not block the
  design — the fix is correct regardless — but it sizes the contention and therefore the retry
  loop's tuning.
- **Lock primitive undecided,** with a caveat from the census: *"Windows `msvcrt.lockf` is
  unreliable on network drives."* Windows and POSIX need different mechanisms (`msvcrt` /
  `fcntl`) or a portable lock-file protocol. The stale-holder case must be answered: a process
  that dies holding the lock must not wedge the store.

### 6a. A fourth option the A/B/C frame did not contain

deepseek proposes attacking the root rather than the race:

> **per-key files** instead of one monolithic JSON. Each key gets its own file; no
> write-clobber between keys.

This deserves recording because it is categorically different from A/B/C. Those all keep the
whole-file serialisation and add coordination around it; this **removes the whole-file write**,
so there is no clobber to coordinate against — the defect becomes unrepresentable rather than
guarded. Its own framing of the choice is the clearest statement of the root cause in any
document here:

> The whole-file serialization pattern is the root cause. Every mutation writes the entire
> dict; any process that missed a prior mutation writes an incomplete dict. The fix is either
> "don't miss mutations" (re-read before write) or "don't write the whole dict" (per-key
> storage).

Not adopted, and not rejected — **not yet evaluated**. It trades a concurrency problem for a
filesystem-shape problem (inode pressure, directory scans on prefix reads, atomicity across
*multi-key* operations, and a migration for the existing store). A is the lower-blast-radius
change and remains the recommendation; per-key storage is the honest alternative if A's write
amplification proves unacceptable in measurement rather than in argument.

## 7. A dissent on sequencing, recorded rather than resolved

The fleet split **2–1 on what to do first**, and the dissent is about verifiability, not
importance.

kimi and claude picked the FileStore. **deepseek picked D (the honest CI split)** and
explicitly conceded severity: *"65.6% silent data loss is objectively more severe than CI
hygiene."* Its argument is sequencing:

> fixing it now, with CI red, means the fix lands into a gate that can't verify it. A green CI
> makes the FileStore fix testable — the coherence pins go RED, the fix lands, the pins go
> GREEN, and CI confirms nothing else regressed. Without that loop, the FileStore fix ships
> blind.

The counter, for the record: the coherence pin is **self-verifying** — `xfail(strict=True)`
means an XPASS fails the build on its own, and it runs deterministically in isolation. And the
tree-differential census means the red baseline is now *measured* (8 tree-independent
candidates, 7 after `d0c4e3d`), so a new regression is detectable by diff rather than by
greenness.

The residual risk deepseek names is real and survives that counter: a store change has wide
blast radius, and diffing against a baseline where 20 of 25 failures are tree-dependent is a
weaker instrument than a green suite. **This is a judgement call for Daniel, not a fact to be
settled by argument, and it is recorded here unresolved.**

## 8. Provenance

- Measurements, probes, and the coherence pin: claude.
- The insufficiency-of-a-lock mechanism, the A/B/C ruling, the read-cache demotion, the ROT-1
  refinement, and the per-instance `RLock` find: **kimi**.
- The writer census establishing the single write path: **deepseek**.
- kimi also specified this exact instrument in its morning durability verify — *"only a true
  multi-process test with interleaved load-mutate-flush would"* catch this class — twelve hours
  before the pin was written.
