# T095-M1 frozen-contract adversarial review — Codex

Date: 2026-07-31  
Frozen revision: `9eb948281e7f7a654e3851623ad5189fdaf1bfd1`  
Reviewed contract: `tests/test_t095_m1_mailbox_intent.py`  
Scope: contract sufficiency only; uncommitted GREEN implementation is outside this review

## Verdict

**NO-GO: the sufficiency claim is falsified.** The eight committed pins do not imply the product receipt and can be made green by a structural stub. They do not prove that accepted mail remains canonical after transport loss and projection rebuild, that identity conflicts fail closed, that opening is crash-safe and non-destructive, or that read and handling intent remain separate facts.

The current moving worktree returning `8 passed` is an exploratory spike, not an acceptance receipt for the frozen contract.

## Counterexample to sufficiency

At the frozen revision, every test except the deliberate placeholder checks method presence rather than behavior. In M1.2, `body is not None or True` is a tautology followed by an unconditional failure. Once that failure is removed, an object exposing `body_of`, `retention_s_for`, `identity_of`, `open`, `declare_intent`, and `state_for` as no-op or `None`-returning stubs can satisfy the entire suite.

Therefore a green suite does not entail any part of the stated receipt:

> Seat A reads a message and dies. Seat B can list the same mail, see that A read it but declared no action, open the exact body, and declare its own intent without moving, acknowledging, or destroying transport state.

## Missing load-bearing pins

### 1. Canonical body authority must survive projection loss

The governing mailbox design describes `{namespace}:mailbox:*` as a rebuildable projection and `rebuild()` deletes its per-message hashes before replaying streams. A body stored only in that projection survives stream eviction only until the next rebuild; then both source and copy are gone.

Add a kill drill that:

1. accepts a message;
2. evicts all transport copies;
3. deletes/rebuilds the mailbox projection in a fresh object/process;
4. lists and opens the message as another seat; and
5. asserts byte-exact body and attachment/part identity.

The test must identify a canonical immutable message authority outside disposable inbox projections. Rebuildable inbox, state, and receipt views may reference it but may not be its sole copy.

### 2. Identity cannot be deferred to an unenforced fence

The cited T116 identity fence is currently an untracked test file with no durable revision or verification receipt. It cannot block T095 from going green. T095 needs either an explicit verified dependency gate or local behavioral pins for this triplet:

- the same stable message ID/idempotency key delivered by legacy lane, work lane, and retry resolves to one mail object;
- byte-identical payloads with two fresh stable IDs remain two distinct mail objects;
- one stable ID with a different payload digest becomes `CONFLICT`, never a merge, overwrite, or silent drop.

Missing stable identity must surface `DEGRADED` or `UNKNOWN`; a content-derived fallback cannot support an unqualified durability claim.

### 3. Open must be receipt-atomic and transport-nondestructive

Pin crash points immediately before and after the seen receipt is committed. A retry by the same bound seat incarnation must return the body and yield exactly one durable seen receipt for `(message, recipient, incarnation)`. A later incarnation may add its own distinct receipt.

Snapshot transport streams, entries, pending/ack state, cursors, and expectations before and after `list`, `body_of`, `open`, and `declare_intent`. Apart from designated mail-authority keys, the snapshots must remain byte-for-byte identical. Merely finding the message after an open is too weak.

The incarnation must come from authenticated session context; a caller-supplied string must not let one seat forge another's receipt.

### 4. “Full body” requires exact completeness semantics

For every accepted message within the public contract, pin exact bytes and all declared parts after eviction and rebuild. If large bodies spill to object/blob storage, pin resolution of that immutable reference. If a size cannot be retained, reject the message loudly before acceptance. A truncated prefix plus a flag does not satisfy “open the full body.”

### 5. Do not collapse orthogonal mail facts into one ladder

Pin independent axes rather than one mutually exclusive status:

- delivery and per-incarnation seen receipts;
- handling declaration: at minimum `act`, `decline`, `delegate(to)`, and `defer(until)`;
- work ownership/progress in the task or claim projection, not in the mail object;
- reply, settlement, archive, supersession, and expiry as separate evidence/outcomes.

Intent declarations should be append-only facts with a declaration ID/idempotency key and explicit supersession using compare-and-swap or generation fencing. Concurrent incompatible declarations must render `CONFLICT`; last-writer-wins must not silently rewrite history. “Never seen” and “seen, then declined” must be mechanically distinguishable.

## Minimum end-to-end acceptance drill

With two logical seats and distinct incarnations:

1. deliver mail and record the complete transport snapshot;
2. A lists, opens, records one seen receipt, declares no handling intent, then dies;
3. evict transport and rebuild every derived mailbox projection in a fresh process;
4. B lists the same logical message, sees A's receipt and absence of A intent, opens exact bytes, and declares one intent;
5. retry A's and B's operations across the registered crash points;
6. prove the canonical message still exists, receipts are exact-once per bound incarnation, intent history is non-lossy, and the transport snapshot is unchanged except for independently occurring transport events.

## Required sequence before a GREEN claim

Commit an amended tests-only RED revision containing the behavioral pins, observe the intended missing-behavior failures, and only then evaluate GREEN against that immutable revision. Continuing implementation exploration is fine, but it must not be mistaken for pre-registered acceptance. Fable's blind review should remain independent and may add or reject pins before reconciliation.
