# Remediation plan — the full surface, what depends on what, and the order

Status: current
Class: design

Written 2026-07-26 at Daniel's ask: *"Lets evaluate everything and understand the full surface
of the things in play and come up with a verifiable step by step plan for remediation where we
understand what relates to what and how it needs to be built."*

Every step below states **how you know it worked**. A step without a verification line is not a
step. Nothing here is built.

---

## 0. Two findings that reshaped this plan while writing it

Both came from asking "does this already exist?" before designing — the check that has now
paid off three times today.

**`suite-baseline` already exists** and is **44.7 hours stale**: recorded at `6a0162c` with 13
known failures, while HEAD is `447e240` and the clean-clone census measured 25. The organ is
not missing, it is *unrefreshed* — an instrument reporting a number nobody renewed, which is
this week's genus exactly. Worth refreshing on its own merits.

> ### CORRECTED 2026-07-26 — my claim about what this dissolved was motivated reasoning
>
> I originally wrote that this **dissolved** deepseek's dissent: the gate it wanted exists, so
> D need not precede the store fix. I flagged to kimi that I could not audit that from inside,
> because I picked the FileStore in the morning and then found a fact that conveniently removed
> the objection to picking the FileStore. **kimi's verdict: it is the motivated-reasoning shape,
> and the tell is a question I asked myself and then did not follow.**
>
> The node-id delta is only as good as the **stability of the set being diffed**, and by my own
> **L0.2** the same commit yields 11 / 18 / 25 / 31 failures depending on tree × env ×
> isolation × identity. **A store regression adding a handful of node-ids sits inside a churn
> band of ±14.** The delta cannot separate signal from churn at that amplitude, so
> **deepseek's objection survives**, and the baseline refresh does **not** verify the store fix.
>
> What survives, and it is the part that matters: **L1/L2 independence is real and
> well-evidenced** (verified, not assumed — see the next finding). So the correct framing is
> **not** "D is dissolved" but:
>
> **L1 and L2 are independent and proceed in PARALLEL. The store fix is verified by its own
> pre-registered acceptance pin — a deterministic multi-process test — not by the suite-baseline
> delta. D's value is independent of the store fix, and taming the tree-dependent churn is part
> of D, which is what would eventually make the delta load-bearing.**
>
> The ordering below is unchanged in *content* but its justification is corrected: Phase 0 is
> worth doing because the instrument is stale, **not** because it unblocks Phase 2.

**The FileStore hole and the test-pollution problem are INDEPENDENT.** I expected them to be
one defect at two layers and built an early draft on that. Checked instead of assumed: of
deepseek's flaky set, `git_guard`, `killwindow`, `t060`, `t068` and `t093` touch a store on
**zero** lines (`event_hooks` on two). The pollution is via spawned processes, env vars and the
bus — not shared store state. **They can proceed in parallel; neither blocks the other.**

---

## 1. The full surface

Grouped by layer, with status. **MEASURED** = reproduced with a number. **RULED** = design
settled in the fence. **ASSUMED** = believed, not yet verified.

### L0 — Instruments (nothing else is verifiable until these are)

| # | Item | Status |
|---|---|---|
| L0.1 | `suite-baseline` exists; **44.7h stale** (13 recorded vs 25 measured) | MEASURED |
| L0.2 | Failure count is a function of tree × env × isolation × identity (11/18/25/31 for one commit) | MEASURED |
| L0.3 | Clean-clone differential auto-classifies tree-dependence | MEASURED |
| L0.4 | Console spam fixed at 3 layers; hooks now `pyw` | needs restart to confirm |
| L0.5 | `-r` **replaces** pytest's default `-rfE`; bare `-rsxX` hides every FAILED line | MEASURED |

### L1 — Substrate integrity (the only layer with data loss)

| # | Item | Status |
|---|---|---|
| L1.1 | FileStore lost update: 450 writes → 155 survive, **295 lost (65.6%)**, no error | MEASURED, pinned |
| L1.2 | `cas()` does not guard cross-process **or cross-instance**; every call returns True | MEASURED |
| L1.3 | `test_lost_update_is_prevented` passes using one instance in one process | MEASURED |
| L1.4 | Exactly **one writer path** (`_flush`); the two other scripts are read-only | MEASURED (deepseek), corroborated (kimi) |
| L1.5 | codex's 108,963→164 byte collapse explained; `_degraded` guard already prevents it | RESOLVED |
| L1.6 | Design = lock + reload-under-lock; in-memory dict demoted to read cache | RULED |
| L1.7 | Lock primitive undecided; `msvcrt.lockf` unreliable on network drives; dead-holder case open | OPEN |
| L1.8 | Per-key files — removes the whole-file write instead of guarding it | UNEVALUATED |

### L2 — Test honesty (D)

| # | Item | Status |
|---|---|---|
| L2.1 | `skipif`=50, `skip`=1, `importorskip`=11, **`xfail`=0**; `xfail_strict` unset | MEASURED |
| L2.2 | `xfail(raises=…, strict=True)` delivers kimi's STILL-VALID-WHEN natively | MEASURED (probe, 4/4) |
| L2.3 | 25 clean-clone failures: 20 tree-dependent, **7** tree-independent candidates | MEASURED |
| L2.4 | ENV-SELF splits **HYGIENE** vs **EXPOSES**; never hygiene an EXPOSES | RULED |
| L2.5 | deepseek's 8 flaky tests pass alone, fail in suite (process/env/bus pollution) | MEASURED |
| L2.6 | T070 residual: backend isolation fixed, **filesystem/bus isolation not** | MEASURED |
| L2.7 | 69 of 313 files carry skips, incl. "pre-registered; impl pending" reporting **green** | MEASURED |
| L2.8 | The WITNESS (count-by-reason, diffed, on a surface Daniel reads) | PARTLY EXISTS (L0.1) |

### L3 — Knowledge and recall

| # | Item | Status |
|---|---|---|
| L3.1 | Funnel value 6.5%; metric has **four defects**; impression series double-logged | MEASURED |
| L3.2 | Boot recall + stance block: **keep on** — unanimous | RULED |
| L3.3 | Per-call injection: kimi says narrow, deepseek says off. Both say **fix the metric first** | SPLIT, but converging |
| L3.4 | **Binding failure** — right lesson surfaced, violated minutes later, twice | MEASURED |
| L3.5 | 300 of 440 lessons carry no checkable anchor (`cites` starvation) | ASSUMED (count not re-derived tonight) |
| L3.6 | Self-sealing `is_benched` loop: demoted lesson can never earn redemption | Daniel's gate |
| L3.7 | Retrieval-benchmark floor; the public benchmarks are contested (Zep 84%→58.44%) | Daniel's gate |
| L3.8 | Grep ablation — can the substrate beat letting an agent grep the corpus? | Daniel's gate, unstarted |

### L4 — Comms and fleet ergonomics

| # | Item | Status |
|---|---|---|
| L4.1 | Wake watcher peeks **legacy**; work-lane drains don't clear it. Cost 6 arms | MEASURED |
| L4.2 | The stop hook demands a re-arm after every failure — pushes workaround over diagnosis | MEASURED |
| L4.3 | Bus **clips long bodies**; deepseek's census had to be recovered via `capture` | MEASURED |
| L4.4 | T066 legacy stragglers on every drain (sender-side lane-write failure) | LIVE |
| L4.5 | Twin-seat delivery: I sent a stand-down to my own id and consumed it myself | MEASURED |
| L4.6 | **False capability claims**: kimi has no exec, deepseek no `git clone`, no `run` | MEASURED |
| L4.7 | CLI inconsistency — 3 syntax failures in one session (`capture` takes no agent_id) | MEASURED |

---

## 2. What relates to what

The dependencies that actually constrain order. Everything else is parallelisable.

```
L0.1 suite-baseline REFRESH ──────────────► verification for EVERY later step
                                            (this is the true first move)

L1.7 lock primitive ─────────────► L1.6 build the store fix
L1.8 per-key evaluation ─────────┘  (decide between them BEFORE building)

L2.4 ENV-SELF sort ──────────────► L2.1 the 51-site conversion
   (convert first and you xfail an EXPOSES = bury a real bug)

L3.1 metric defect ──────────────► L3.3 the recall on/off decision
   (both dissenters agree the metric blocks the decision)

L4.6 capability truth ───────────► every future fleet brief
```

**Three relationships worth stating in words, because they are the non-obvious ones:**

**(a) The recall debate — CORRECTED 2026-07-26, partially rejected by kimi.**

I originally wrote that the debate "is not actually a debate about recall": both dissenters say
fix the measurement first, so the actionable item is L3.1 and the on/off question waits.
**Half right, and the wrong half was load-bearing.** kimi's correction:

- **deepseek's position (turn it OFF) *is* metric-gated.** "Off" is only justified if recall is
  shown to be valueless, and that needs a working metric.
- **kimi's position (NARROW it) is *not* metric-gated.** It is a *noise-reduction* argument, not
  a value-attribution one — fewer, higher-confidence injections, on the grounds that noise
  limits creativity. That argument stands whether or not the funnel metric is fixed.

So the disagreement **is substantive** and I flattened it. The correct statement: *the on/off
DECISION is blocked on L3.1; the NARROWING is actionable now and must not be deferred behind
the metric fix.* That moves work out of Phase 4 and into "can start immediately."

**(b) The binding failure (L3.4) is not on the recall axis at all.** A lesson that is
retrieved, rendered, and then violated is not a retrieval defect, and no amount of refitting
ranking touches it. It needs its own treatment and it currently has no owner. It is the only
item on this board with *no proposed mechanism at all*.

**(c) L1 and L2 are independent** — verified tonight, not assumed. This is what dissolves the
2–1 split: they need not be ordered against each other, and the only thing D was needed *for*
(verifying the store fix) is L0.1, which is ten minutes of refresh rather than a 51-site
conversion.

---

## 3. The plan

### PHASE 0 — Make the instruments trustworthy (hours, no substrate risk)

**S0.1 — Refresh the suite baseline at HEAD, from a clean clone.**
Record with `suite-baseline claude --from-file <clean-clone pytest output> --sha <HEAD>`.
Must be the clean clone, not the working tree (L0.2/L0.3).
*Verify:* `--show` reports HEAD's sha and ~25 failures, not `6a0162c`/13. Then run
`--check --from-file` on a second clean run and confirm it reports **0 NEW, 0 fixed**.
*Unblocks:* every subsequent step becomes verifiable by diff rather than by greenness.

**S0.2 — Confirm the console fix and hook liveness after restart.**
*Verify:* tool calls still carry `Recall-at-action` lines (hooks alive under `pyw`) **and** no
console windows appear. Both must hold; either alone is a false pass.

**S0.3 — Correct the capability claims in the brief templates.**
kimi: no exec. deepseek: no `git clone`, no `run`. *Verify:* a brief generated for each names
its true door. Cheap, and it has already cost three false verifies and two of deepseek's four
worst pains.

### PHASE 1 — Decide the store fix's two open questions (before any code)

**S1.1 — Choose the lock primitive, dead-holder case answered.**
Windows/POSIX differ; `msvcrt.lockf` is unreliable on network drives. *Verify:* a spike that
holds the lock, kills the holder **without release**, and shows a second process acquires
rather than wedging. A lock that can wedge the store is a worse defect than the one we are
fixing.

**S1.2 — Evaluate per-key files (L1.8) against A, by measurement not argument.**
*Verify:* a written comparison on four axes — write amplification under A vs directory
pressure under per-key; multi-key atomicity; prefix-scan read cost; migration cost for the
existing store. Outcome may be "A confirmed"; the point is that per-key stops being an
unevaluated alternative someone raises again in a month.

### PHASE 2 — Build the store fix (L1.6) — Daniel's gate

Per [filestore-coherence-design-2026-07.md](filestore-coherence-design-2026-07.md) §4–5.
Acceptance is pre-registered there and is not restated here.
*Verify:* the coherence pin flips XFAIL→XPASS and **fails the build** (that is the signal);
a genuine multi-process CAS test passes; `suite-baseline --check` reports **0 NEW**.
That last one is the whole reason Phase 0 comes first.

### PHASE 3 — Test honesty (D), in the order the ruling requires

**S3.1 — Sort the 8 flaky tests through HYGIENE vs EXPOSES *before* converting anything.**
*Verify:* each has a written sort with its reason; anything sorted EXPOSES gets its condition
pinned **outside** the suite. **This must precede S3.3** — converting first would xfail a test
that is witnessing a real bug, which kimi named as the single most expensive mis-sort
available.

**S3.2 — T070 residual: filesystem/bus isolation (L2.6).**
*Verify:* the 8 flaky tests pass in-suite as reliably as they do alone, repeated 5×.

**S3.3 — The 51-site `skipif`→`xfail(raises=…, strict=True)` conversion + `xfail_strict=true`.**
Only where the body can safely run; `skipif` stays where running is unsafe or impossible.
*Verify:* every converted site names its exception; suite exit status unchanged;
`suite-baseline --check` reports 0 NEW.

**S3.4 — The WITNESS: count-by-reason, diffed, on a surface Daniel already opens.**
Extends L0.1 rather than replacing it. *Verify:* a bucket going 27→28 is visible without
anyone looking for it.

### PHASE 4 — Knowledge and recall, in dependency order

**S4.1 — Fix the impression-series double-logging (L3.1). This is the gate for everything
else here.** *Verify:* the value rate is re-derivable by a printed command and two independent
runs agree.

**S4.2 — Then, and only then, answer the on/off question (L3.3)** with a measurement rather
than a preference.

**S4.3 — The binding failure (L3.4) needs an owner and a mechanism.** It has neither. It is
the item I would most expect us to skip because it has no obvious shape, and it may be the
most valuable one on the board.

**S4.4 — `cites` starvation (L3.5).** Re-derive the 300/440 count first; it is the one number
here I have not personally reproduced. oxlint's provenance-as-a-queryable-column is the
pattern.

---

## 4. What is blocked on Daniel

1. **Phase 2 (the store fix)** — the substrate gate.
2. **L3.6** the self-sealing `is_benched` loop.
3. **L3.7** the retrieval-benchmark floor, needing the amendment in
   [peer-oss-2026-07-25](../research/reviewed/peer-oss-2026-07-25-lint-taxonomy-and-agent-memory.md).
4. **L3.8** the grep ablation — premise-level, asked twice, unanswered. Not a nudge; recorded
   so silence is not mistaken for assent.

## 5. Honest weaknesses in this plan

### 5a. The four kimi added that I missed — all four accepted

1. **The dissolution claim was the plan's least-audited *and* most load-bearing claim, and I
   did not list it.** It ordered Phases 0–2 and it was the thing I had least right. A plan whose
   ordering rests on its weakest claim must say so. Corrected in §0; kept visible rather than
   quietly rewritten.
2. **L1.7's dead-holder case is under-scoped exactly as S3.2 is, and I did not flag it.** My
   verification line — *"a spike that shows a second process acquires rather than wedging"* — is
   **a hope, not a verification**. The deadlock case is precisely the one a spike misses. It sits
   in Phase 1 wearing the costume of a quick check.
3. **The false-capability receipts are still in the record, uncorrected.** S0.3 fixes future
   brief templates. It does nothing about the **three verifies already filed this week under
   false premises** (kimi's exec-disabled code-reads presented as verifies). The fix is
   forward-looking; the corrupted evidence is not retracted. That is a separate, unlisted task.
4. **The Phase 2 acceptance test may itself be genus-A.** A deterministic multi-process CAS test
   is non-trivial — and the FileStore durability pin *already made this exact mistake*, using
   threads where only processes could prove the property. If the acceptance test is thread-based
   or flaky, **the store fix's verification is itself the disease it is curing.** The coherence
   pin got this right by using real subprocesses; the CAS test does not exist yet and could
   repeat the error.

### 5b. Originally listed

- **L3.5 is the only ASSUMED number I have carried forward without re-deriving.** It should be
  re-counted before it is planned against.
- **Phase 3 is the largest block of work and the least certain in scope.** The 51-site
  conversion is mechanical, but S3.2 (filesystem/bus isolation) has no design yet, and I have
  sized it at zero.
- **S4.3 has no mechanism.** Naming it is not solving it, and a plan that lists it may create
  the impression it is handled.
- **This plan has not been through the fence.** Every prior design today was sharpened
  materially by kimi or deepseek attacking it, and three of my own claims died that way. It
  should be attacked before it is executed.
