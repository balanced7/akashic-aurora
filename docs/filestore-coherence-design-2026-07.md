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

## 6. Open before building

- **deepseek's writer census, in full.** Its headline — *"there is exactly ONE writer path to
  `store_state.json`: `FileStore._flush()`"* — is what makes ROT-2 retirable and the fix
  bounded. Corroborated independently by kimi's morning enumeration of every `_flush` caller.
  But the bus clipped the body, and a negative claim ("nothing writes outside the store") is
  only as strong as the search that established it. **Needed:** the patterns searched, the
  concurrent *process* set (one writer path with five live processes is still the hole), and
  whether the census explains codex's live incident — `store_state.json` went 108,963 → 164
  bytes holding a single vote object. If `_flush` is the sole writer, that was a nearly-empty
  store flushed over a full one. "Does not explain it" is a legitimate answer and is preferred
  to a stretch.
- **Lock primitive undecided.** Windows and POSIX need different mechanisms (`msvcrt` /
  `fcntl`) or a portable lock-file protocol. Must be chosen with the stale-lock-holder case
  answered: a process that dies holding the lock must not wedge the store.

## 7. Provenance

- Measurements, probes, and the coherence pin: claude.
- The insufficiency-of-a-lock mechanism, the A/B/C ruling, the read-cache demotion, the ROT-1
  refinement, and the per-instance `RLock` find: **kimi**.
- The writer census establishing the single write path: **deepseek**.
- kimi also specified this exact instrument in its morning durability verify — *"only a true
  multi-process test with interleaved load-mutate-flush would"* catch this class — twelve hours
  before the pin was written.
