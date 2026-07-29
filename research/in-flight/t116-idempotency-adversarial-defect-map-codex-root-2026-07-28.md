# T116 packet idempotency: adversarial defect map

- **Seat:** `codex_root_019fab2d`
- **Date:** 2026-07-28 local / 2026-07-29 UTC
- **Mode:** read-only fence; no T116 implementation claim
- **Ground snapshot:** `HEAD 02c86f0`; T116 is `claimed` by Claude; the current
worktree contains Claude's uncommitted honesty correction in
`core/comm/role_queue.py`.
- **Law:** `docs/library/design/20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94.md`
- **Independent input available:** `research/in-flight/t116-idempotency-law-deepseek-counter-half-2026-07-28.md`
- **Independent input not yet available at this snapshot:** Sol's requested design half.

## Verdict

**NO-GO on a plain `{consumer}:{idempotency_key} -> done` sentinel.**

It can suppress some duplicate deliveries, but it cannot make effects or settlement
exactly once. The two placements are both wrong:

1. mark **before** the effect -> a crash loses unperformed work;
2. mark **after** the effect -> a crash repeats an already-performed effect.

The current runner already has the second window and a kill drill that explicitly
accepts the duplicate. T116 can close it for Bifrost replies and settlement only if
the logical key reaches every door and the result is committed through an idempotent
send/outbox path. Arbitrary external side effects remain handler-owned unless they
join the same transaction or accept the same effect key.

The minimum safe contract is:

- an opaque logical operation key, minted once and preserved across physical delivery;
- a separately named causal link from answer to ask;
- an integrity-bound logical fingerprint, so key reuse with different work is a loud
  conflict rather than a silent skip;
- a durable `PENDING -> COMMITTED` record with lease/fence and outcome pointer;
- cursor advance only after `COMMITTED`, or after a same-fingerprint duplicate reads
  the committed outcome;
- an idempotent producer/outbox door for replies and other bus effects;
- a visible duplicate verdict (`seen/handled/settled`), not disappearance.

## Fresh reproduced receipts

### R1. The current post-send/pre-sentinel window produces two replies

Command:

```text
py -m pytest tests/test_killwindow_drill.py::test_w3_duplicate_reply_is_the_accepted_tolerance -q
```

Result: PASS. This is a red receipt in semantic terms: the passing test asserts that
the first tenure sends one reply, dies at `post-send-pre-sentinel`, and the successor
sends a second reply (`tests/test_killwindow_drill.py:189-207`).

The runtime order is explicit:

- reply is sent at `scripts/bifrost_runner_deepseek.py:843-868`;
- killpoint fires at `:870`;
- sentinel is written at `:871`;
- cursor advances later at `:1348-1371`.

DeepSeek's half says the sentinel is set *after* the reply
(`t116-idempotency-law-deepseek-counter-half-2026-07-28.md:169-171`) and then says a
crash before that SET sees the sentinel and skips (`:172-174`). Those statements
cannot both hold. The existing kill drill is the counterexample.

### R2. `idempotency_key` is not integrity-bound

Pure probe:

```text
integrity_original= (True, 'ok')
integrity_after_key_mutation= (True, 'ok')
```

The probe stamped an envelope with key `logical-A`, changed only the key to
`logical-B`, then re-ran `verify_integrity`. Both passed. The cause is contractual:
`packet_spec.CANONICAL_FIELDS` contains only the seven v1 fields
(`core/comm/packet_spec.py:16-24,45-48`); `idempotency_key` is explicitly excluded.

An identity field that can change without invalidating the packet cannot enforce G2
stable identity. Do not mutate the existing v2 digest semantics in place: either
version the canonical envelope or add a separately specified binding checked before
any idempotency claim.

### R3. Top-level identity is dropped by two current projections

Pure probe:

```text
fragment_count= 5
all_fragments_preserve_key= False
message_exposes_key= False
to_dict_exposes_key= False
```

Roots:

- `packet_spec.fragment()` reconstructs each fragment from `CANONICAL_FIELDS` only
  (`core/comm/packet_spec.py:551-577`);
- `Message` has no logical-key field and `to_dict()` omits it
  (`core/comm/bus.py:129-143`);
- `_to_msg()` reads only the old message fields (`core/comm/bus.py:1235-1239`).

A producer-only `_emit` patch would therefore appear green at Redis and arrive
without identity at the consumer. Fragment dedup must happen **after successful
reassembly**, not per fragment; claiming on fragment 0 would make fragments 1..N look
like duplicates and prevent completion.

### R4. Two consume paths commit before caller effects

An isolated live namespace probe returned a message from `Bus.inbox(advance=True)`,
observed that its cursor already equalled the message id, performed no effect, and
read again:

```text
plain_consume_returned= ['1785291621510-0']
plain_cursor_already_committed= True
plain_redelivery_available_before_any_effect= False
```

This is the public API path: non-lane `BifrostAPI.inbox(consume=True)` calls
`Bus.inbox(advance=True)` before returning to its caller
(`core/comm/bifrost_api.py:80-116`).

The same isolated probe injected a mapped, legacy-only straggler. `work_drain`
returned it, but advanced the shadow cursor inside the drain before caller processing:

```text
straggler_returned= ['1785291621522-0']
shadow_advanced_before_processing= 0 -> 1785291621522-0 True
straggler_redelivery_available_before_any_effect= False
probe_keys_deleted= 12
```

Root: `core/comm/bifrost_api.py:345-403`. The code itself documents the straggler as
at-most-once when the caller crashes (`:286-292`). T116 must not claim crash-safe
consumer idempotency while either path can remove the only retry before an effect.

## Live room review after the first draft

### DeepSeek amended the blind half, with three reconcile points still open

In direct reply `1785291769062-0`, DeepSeek accepted the impossible crash claim, the
TTL resurrection, and the fingerprint-poisoning counterexample. He replaced his
single `"done"` sentinel with `RESERVED -> COMMITTED`, made COMMITTED durable, and
stored an effect/outcome fingerprint.

That is real convergence, but the following are not resolved by the state names:

1. death after an external effect but before `COMMITTED` is still ambiguous; after
   the RESERVED lease expires, a successor repeats the effect unless the effect/send
   itself accepts the key or an outbox can recover its committed outcome;
2. his proposed “fingerprint mismatch -> process anyway” is unsafe under an already
   claimed key; conflict must quarantine/refuse and require an explicitly fresh key;
3. his proposed globally raw key collapses legitimate per-role broadcast effects;
   the record must be scoped to the logical effect domain.

DeepSeek also retained the speculative WRONGTYPE self-heal. This map continues to
reject destructive `DEL` in the packet send path; see D15.

### Kimi fixed the minimum visible duplicate verdict

In direct reply `1785291964002-0`, Kimi rejected a silent skip and supplied the exact
settlement boundary:

- a duplicate may settle only when it points to the first execution's **committed
  cached outcome**;
- a bare “handled” receipt settles nothing;
- a sentinel with a missing/dangling outcome emits a loud, non-settling `note`,
  preserving RB-29;
- effect-side suppression may remain quiet, but skipping an answerable packet must
  render `[seen: logical-key, outcome -> outcome-ref, n copies]`.

This is adopted in D9 and the protocol below. The pointer must use logical identity
and an outcome ref, not a physical stream id alone.

### Sol half remains unavailable

No Sol T116 artifact or direct reply existed at the live edge when this update was
written. The reconcile must not infer his position from Claude's handoff.

## Current topology and defect roots

```text
new send
  Bus.send/broadcast
    -> Bus._emit
       -> T112 content-based re-ask collapse
       -> MTU or fragment branch
       -> lane XADD
       -> legacy XADD
       -> optional seat XADD
       -> physical idalias + expectation arm by returned physical mid

reply
  Bus.send_reply
    -> independent envelope builder (does not call _emit in lane mode)
    -> lane XADD + legacy XADD

redrive
  expectations.sweep
    -> reconstructs from {to, kind, content}
    -> Bus.send(meta={redrive_of, attempt})
    -> aliases new physical mid to original physical mid

rehome
  reaper.reap
    -> reconstructs content + selected meta
    -> Bus.send

consume
  integrity -> fragment reassembly -> Message projection
    -> runner effect/reply -> reply sentinel -> cursor advance
```

### D1 — CRITICAL: post-effect/pre-commit remains duplicate-effect

**Roots:** `scripts/bifrost_runner_*` reply sentinels; DeepSeek half Q2/Q3.

**Counterexample:** fresh R1.

**Required RED:** kill after bus reply/effect but before logical commit; successor must
produce one logical outcome and at most one physical reply for the same reply key.

Moving `SETNX` earlier is not a fix; it creates D2.

### D2 — CRITICAL: pre-effect claim can strand work

If the consumer writes a sentinel before processing and dies, a successor sees the
key and skips work that never happened. `work_drain` cannot safely write a final
sentinel because it returns messages before knowing whether the handler succeeded.

**Required RED:** kill after `PENDING` claim but before handler entry. A successor must
reclaim after a fenced lease and perform the effect once. A live owner must not race it.

For an external effect that cannot accept the key or participate in an outbox
transaction, the honest result is `UNKNOWN / at-least-once`, not “exactly once.”

### D3 — CRITICAL: cursor-before-effect loses the only retry

**Roots:** `core/comm/bifrost_api.py:80-116,345-403`; R4.

**Required REDs:**

1. session/API consume dies after return and before effect -> message remains eligible;
2. legacy straggler dies after drain and before effect -> shadow position does not pass
   it until a committed handling receipt exists.

A dedup sentinel cannot recover a message the cursor has already made unreachable.

### D4 — CRITICAL: identity mutation passes integrity

**Roots:** `core/comm/packet_spec.py:16-24,45-48`; R2.

**Required RED:** stamp key A, mutate only to B, consume door must reject/quarantine
before claim. Existing v1/v2 packets without a key must continue to verify under their
original version.

### D5 — HIGH: `_emit` is not the whole send door

An `_emit`-only patch misses:

- lane-mode `send_reply`, which builds and XADDs its own envelope
  (`core/comm/bus.py:294-361`);
- fragments (`core/comm/bus.py:628-662`,
  `core/comm/packet_spec.py:551-577`);
- `Message` parse/serialization (`core/comm/bus.py:129-143,1235-1239`);
- redrive reconstruction (`core/comm/expectations.py:315-334`);
- rehome reconstruction (`core/comm/reaper.py:223-256`);
- public API/CLI exposure (`core/comm/bifrost_api.py:67-77`,
  `agent_cli.py:3641-3675`).

**Required RED matrix:** normal direct, broadcast, reply, lane/legacy twins, seat
mirror, oversize fragments/reassembly, expectation redrive, and reaper rehome all
carry one unchanged logical key to `Message.to_dict()`.

### D6 — HIGH: auto-minting on every call does not make retries stable

If `_emit` generates a fresh key whenever the caller omits one, an uncertain caller
retry after process restart gets a different key. The door needs either:

- a caller-supplied key persisted by the operation owner; or
- a durable producer outbox that mints before physical XADD and can resume by key.

**Required RED:** fail after the lane XADD but before legacy XADD; retry the same
logical send after recreating `Bus`. It must resume/fill the missing mirror and return
the prior logical send record, not create a second operation.

### D7 — CRITICAL: same key/different work is poisoning, not a duplicate

DeepSeek proposes `{ns}:idem:{consumer}:{key}` with value `"done"`. It stores no
fingerprint. Two producers choosing `retry-1`, or one buggy producer reusing a key
for changed content, causes the second operation to disappear silently.

The idempotency record must bind at least:

```text
namespace + logical producer + logical consumer/effect scope
+ kind + canonical content/parts + effect-defining meta
```

Volatile recovery metadata (`attempt`, physical ids, lane source) must not change the
fingerprint. A same-key/different-fingerprint arrival is `CONFLICT`: loud,
quarantined, no cursor advance as “handled,” and no expectation settlement.

**Required RED:** same scope/key, changed content or attachment -> conflict; no effect,
no false handled receipt.

### D8 — HIGH: fixed TTL resurrects durable duplicates

DeepSeek's seven-day TTL is a capacity guess, not a correctness horizon. Expectations
accept arbitrary `within_s`; rehome/outbox state can outlive Redis; permanent external
effects can outlive all transport streams. When the tombstone expires, an old replay
becomes new again.

**Required RED:** a committed key survives process restart, Redis restart, and the
maximum configured redrive/rehome horizon. Pruning is allowed only after the system
can prove the operation is no longer replayable, or under an explicitly weaker
retention contract rendered to the operator.

SQLite/WAL is now the durable store and has cross-process atomic CAS
(`core/foundation/sqlite_store.py:671-704`). Redis can be a hot cache/lease, but must
not become a second truth. CAS alone still cannot atomically cover an external Redis
XADD; that is why the producer outbox/result pointer is required.

### D9 — CRITICAL: silent duplicate skip can strand settlement

Counterexample:

1. consumer commits the effect;
2. original reply is lost or corrupt;
3. sender redrives the same ask key;
4. consumer sees `"done"` and silently skips;
5. sender receives no qualifying answer, so its expectation redrives to death.

A committed record must include an outcome/reply pointer. A duplicate of the same
fingerprint should replay the idempotent answer or emit a typed
`duplicate_handled` receipt that qualifies as an answer **only when COMMITTED is
proven**. `PENDING`, failed, unavailable, and conflict never settle.

This is also the first `[seen:]` truth-physics seam: duplicate is a normal delivery
verdict, but normal does not mean invisible.

**Required RED:** drop the first reply after committed effect, redrive the ask, assert
zero repeated effects and one eventual settlement from the cached outcome.

### D10 — HIGH: idempotency identity is not causal identity

`expectations.sweep` first resolves `meta.answers` against physical ask ids and aliases,
then falls back to FIFO (`core/comm/expectations.py:157-194,261-290`). A reply's own
idempotency key answers “is this the same reply?” It does not answer “which ask caused
this reply?”

Do not infer causation by parsing `A:reply:0`. Add an explicit `answers_key` (or
equivalent typed field) that names the ask's logical key. Keep the reply's own key
independent.

**Required REDs:**

- two asks to one peer; answers arrive out of order -> each settles the key it names;
- a wrong sender knowing the key settles nothing;
- timeout/error notes never settle (RB-29);
- a reply redrive settles once across sweeps;
- handoff/completion answer shapes preserve the same causal rule.

Reuse the atomic marker+expectation deletion pattern already present in
`_settle_once` (`core/comm/expectations.py:197-218`).

### D11 — HIGH: `A:reply:0` is not a safe reply identity

It has three independent failures:

- a max-length 128-byte ask key plus `:reply:0` violates the 128-byte field bound;
- multiple legitimate replies, progress/result pairs, or handoff/completion shapes can
  collide at sequence 0;
- a local reply counter can reset after restart.

Mint a stable reply key once in the committed outcome/outbox; carry
`answers_key=A` separately.

### D12 — HIGH: scope must follow the logical effect, not the physical seat

Broadcasts intentionally effect once per logical recipient, so a global sentinel is
wrong. Rehome intentionally moves work from `agent#dead-seat` back to the role, so a
strict incarnation-scoped sentinel can repeat a role effect already committed before
the seat died. Conversely, two explicitly seat-specific operations may be distinct.

The build spec must define effect scope for:

- directed role mail;
- `to_incarnation` mail;
- broadcast fan-out;
- rehome from dead incarnation;
- concurrent same-agent seats.

**Required RED:** one broadcast key handles once for each distinct role, while two
incarnations of the same single-consumer role cannot both commit the same effect.

### D13 — HIGH: content-based re-ask collapse conflates intent

T112 hashes only sender, target agent, kind, and content
(`core/comm/bus.py:546-555`). It ignores `parts` and semantic meta. Therefore:

- same text with a different attachment can collapse;
- same text addressed to two different `to_incarnation` seats can collapse onto the
  first seat's physical mid;
- two intentional identical operations within the window are treated as one.

T116 should make retry intent explicit: a new operation gets a new key even when bytes
match; redrive/retry reuses a key. Do not retire T112 until the UI/CLI has an explicit
retry path and the no-strand guarantees are re-pinned.

**Required REDs:** different Part ref and different target incarnation both deliver,
despite identical text; explicit retry with the same key does not re-effect.

### D14 — MEDIUM/HIGH: current twin dedup can false-collide

`work_drain._dedup_key` is `(frm, ts, kind)` only
(`core/comm/bifrost_api.py:264-269`). It omits content, target, packet SHA, and logical
identity. A distinct legacy-only message sharing that tuple with a lane message is
discarded as a twin (`:364-366`). Across calls, the documented shadow-before-lane race
can still double-deliver (`:286-292`).

**Required RED:** two different payloads with identical sender/time/kind are both
delivered; true lane/legacy twins with the same logical key are one operation.

### D15 — HIGH: destructive WRONGTYPE self-heal is not a T116 ride-along

DeepSeek proposes `TYPE`, then `DEL` any non-stream lane key in `_emit`. The diagnosis
in the half is explicitly “most likely,” not reproduced, and deleting an unexpected
key in the live send path destroys evidence/data before an operator can classify it.
T122 already made WRONGTYPE visible in doctor.

If a key-type migration is needed, use a versioned stream key or a governed admin
repair after census/escrow. Do not make packet identity authorization for destructive
repair.

### D16 — CRITICAL: retiring T112/T117/T086 early reopens measured defects

Existing point fixes are not obsolete merely because a new field exists:

- T112 pins suppression/no-strand/redrive/rehome behavior;
- T086 stores reply-sent evidence across Redis restart;
- T117 pins alias resolution, wrong-sender rejection, per-reply settlement,
  atomic settle+mark, and redrive-to-original linkage;
- kill-window W4 pins post-sentinel redelivery.

Keep them through shadow comparison. Retire each only when a named T116 pin proves its
property under the logical-key path and the old path is no longer reachable. “Field is
present” is not a retirement receipt.

## Proposed reconciled protocol

### Packet fields

```text
idempotency_key   opaque <=128-byte operation identity; new operation mints once
answers_key       explicit causal parent for answer-shaped packets
```

Derive locally and persist:

```text
logical_fingerprint = H(
  producer_scope, consumer/effect_scope, kind,
  canonical content, parts, effect-defining meta
)
```

The producer-supplied key is not trusted as proof. The consumer compares the stored
fingerprint. Authentication of `frm` remains a separate unresolved trust boundary;
until signed identity lands, state the trusted-local-fleet limit honestly.

### Durable record

```text
UNSEEN
PENDING {
  fingerprint, owner_token, generation, lease_until, started_at
}
COMMITTED {
  fingerprint, outcome_ref, reply_key, committed_at, retention_basis
}
CONFLICT {
  first_fingerprint, conflicting_fingerprint, observed_at
}
```

Rules:

1. integrity, schema, route, and trust checks happen before claim;
2. fragments reassemble before claim;
3. `PENDING` with a live lease never runs twice;
4. expired `PENDING` is reclaimed only with a higher fence;
5. `COMMITTED` same fingerprint returns the prior outcome/handled receipt;
6. same key, different fingerprint is `CONFLICT`, never “duplicate”;
7. cursor advances only after rule 5 or after a fresh commit;
8. store unavailable means identity status `UNKNOWN`; high-risk effects hold/refuse
   rather than silently claiming exactly once.

### Producer/outbox rule

`Bus.send(..., idempotency_key=K)` must itself be idempotent:

- persist the send intent before the first physical XADD;
- record lane, legacy, and seat-mirror results separately;
- retry fills missing mirrors without creating a new logical operation;
- same key/different fingerprint refuses loud;
- reply output uses a stable reply key stored in the committed consumer outcome.

This closes `post-send-pre-sentinel` for bus replies without pretending to make an
arbitrary external call transactional.

## Proposed pre-registered RED fence

Land these as a RED-only commit before implementation:

1. key validation: empty/non-string/over-128 refuses before any stream write;
2. key is integrity-bound; mutation A->B is rejected without breaking legacy packets;
3. same new payload twice mints two keys; explicit retry reuses one;
4. same key/different fingerprint is loud conflict, never skip;
5. lane + legacy + seat twins carry the same key;
6. `send_reply` carries a distinct reply key plus `answers_key`;
7. every fragment carries the key; reassembled `Message.to_dict()` retains it;
8. expectation redrive preserves the original ask key;
9. reaper rehome preserves the original ask key;
10. fail after lane XADD, retry after process restart -> one logical send, mirrors healed;
11. kill after claim/before effect -> fenced recovery, one effect;
12. kill after effect/send/before commit -> idempotent outcome, one effect/reply;
13. kill after commit/before cursor -> cached outcome, one effect, cursor advances;
14. original reply lost -> duplicate ask replays committed outcome and settles;
15. wrong sender/key cannot settle; timeout/error note cannot settle;
16. multiple replies to one ask have unique keys but the same `answers_key`;
17. broadcast handles once per logical role; same-role twin seats cannot double-commit;
18. generic API and legacy straggler cursors do not advance before committed handling;
19. legacy packet without a key delivers as identity `UNKNOWN`, never content-hash
    coerced into a logical identity;
20. committed identity survives process + Redis restart and the declared replay horizon;
21. T112: identical text with different Part or `to_incarnation` is not collapsed;
22. T112/T117/T086 retirement tests stay green until each old seam is unreachable.

## Reconcile questions for the room / Daniel's build gate

1. Do we explicitly narrow “exactly once” to Bifrost handling/reply/settlement, requiring
   handler-owned idempotency or outbox participation for external effects?
2. Do we add a distinct `answers_key`, or intentionally overload/parse the reply key?
   This map recommends the distinct field.
3. Does key integrity require a packet version bump, or a separately bound identity
   digest? In-place v2 digest drift is a no-go.
4. What proves a committed tombstone is safe to prune?
5. What is the logical effect scope for `to_incarnation` followed by rehome?
6. Is store-unavailable behavior risk-sensitive hold/refuse, or universal fail-open?
7. Where is Sol's independent half, and which of these counterexamples does it falsify?

Until those are reconciled and the RED fence lands first, T116 should remain
`claimed`, not `in_progress`.
