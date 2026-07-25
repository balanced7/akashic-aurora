# Peer OSS study — 2026-07-25

**Asked by Daniel:** research oxlint and see what we can learn; and make a habit of pausing to
study other open-source systems solving our problems, so we catch up where they are ahead.

**Run by:** claude (fresh Opus 5 seat), during the D slice (the honest CI split).

**Evidence grade, stated up front because this doc argues about benchmark honesty and would be
a hypocrite otherwise:**

- **VERIFIED-LOCAL** — measured on this machine, command in the text.
- **VERIFIED-PRIMARY** — read from the project's own documentation.
- **SECONDHAND** — from search summaries and aggregator posts, not read end-to-end at the
  primary source. Every benchmark number below is SECONDHAND and several are *actively
  disputed by the parties involved*. Do not quote them onward as fact.

---

## 1. oxlint: the category axis is CONFIDENCE, not severity

VERIFIED-PRIMARY. oxlint sorts ~844 rules into `correctness` (definitely wrong),
`suspicious` (likely wrong), `pedantic` (stricter, may have false positives), plus
`style`, `restriction`, `perf`, and `nursery` (experimental, may change). **Only the
correctness category is on by default** — 113 rules of 844.

The thing worth stealing is not the names. It is that the axis is *how sure the tool is that
this is a defect*, and the default gate is the high-confidence subset only. Everything else is
visible on request but does not stop you.

We do the opposite. Our gates are all-or-nothing: a check either fails the build or does not
exist. That is why CI was a fire alarm ringing constantly, and why the first gate failing meant
GitHub Actions skipped the entire suite behind it.

Two more details worth copying:

- **Provenance is a first-class, queryable field.** Every rule carries its source plugin
  (eslint, typescript, react, jest, vue), the version it landed in, and the table is
  *filterable by source*. This is the shape of the fix for our `cites` starvation — 300 of 440
  lessons carry no checkable anchor. oxlint solved the same problem at 844 rules by making
  provenance a column, not prose.
- **The taxonomy has a designed-in confession slot.** Fixability is tiered — auto-fix,
  suggestion, *dangerous* auto-fix, *dangerous* suggestion, and `🚧 fix possible but
  unimplemented`. That last symbol is an honest, machine-readable "we know and we have not
  built it." Compare our version of the same idea: tests carrying "pre-registered; impl
  pending" that report **green**. Same intent, opposite honesty.

## 2. ruff already implements most of the lint kimi proposed

SECONDHAND (rule identity confirmed from docs pages; behaviour not run locally). The
empty-error-collapse lint on our backlog — catching genus-A, `except: pass` / `except:
return []` feeding a downstream OK — largely exists upstream for Python:

- `S110` try-except-pass
- `BLE001` blind-except (catching bare `Exception`)

Relevant nuances, because they are the design decisions we would otherwise make badly:

- **`BLE001` is not on by default** and must be explicitly enabled — the same
  confidence-tiered default as oxlint, arrived at independently.
- It **does not flag** exceptions logged with `exc_info`, because that is the legitimate
  pattern. The rule encodes the difference between swallowing and recording.
- Its issue tracker is full of false-positive reports (re-raises, `NoReturn` returns, logging
  via `warning`). That is the real cost of this rule class and we would have paid it blind.

**Recommendation:** do not hand-write the genus-A lint from scratch. Take `S110` + `BLE001`
as REPORT-not-gate (matching the oxlint default posture), and build only the part ruff cannot
do — the *dataflow* question of an excepted empty feeding a downstream success line. That
part is genuinely ours; the syntactic part is not.

Note the 2026-06-19 audit already counted ~65 bare excepts. That is the starting inventory.

## 3. pytest already ships the organ D was going to hand-build — and we use it zero times

VERIFIED-LOCAL. Counted across `tests/`:

| mechanism | count |
|---|---|
| `pytest.mark.skipif` | 50 |
| `pytest.mark.skip` | 1 |
| `pytest.importorskip` | 11 |
| **`pytest.mark.xfail`** | **0** |

`xfail_strict` is **not set** in `pytest.ini`.

`skip`/`skipif` **do not run the test body**. So "cannot run in this environment" and "would
fail if it ran" collapse into one outcome that reads as nothing-wrong. That is precisely
kimi's GENUS-A type error — empty and error sharing a type — living in our test
infrastructure, 51 occurrences deep. The pre-existing probe already proved the consequence: a
`skipif(True)` test whose body asserts `False` reports "1 passed, 1 skipped" and exits green.

The sharpest detail: `tests/test_window_confession.py:9` *says* "here as a strict xfail so the
gap stays a visible confession, not a silent one." The vocabulary is in the prose. The
mechanism was never wired — zero xfail decorators exist. Prose describing an unconnected
guard is the token-meter shape one level up.

VERIFIED-PRIMARY, from pytest's own docs — what `xfail` gives us that `skip` cannot:

- the body **runs**, so the assertion is actually exercised;
- `raises=X` grants the excuse **only** for the named exception — "the test will be reported
  as a regular failure if it fails with an exception not mentioned in `raises`";
- `strict=True` makes an XPASS (**unexpectedly passing**) **fail the suite**; `xfail_strict`
  in the ini makes that the project default;
- `-rxXs` renders the reasons.

**Convergence worth recording.** kimi, reasoning from first principles and without knowing
any of this, specified a field it called STILL-VALID-WHEN: the skip stays justified only if
the import still fails *for the same reason* (`ModuleNotFoundError: No module named X`, not
`ImportError: cannot import name Y`), because a **deleted** module changes the failure
signature while an **absent** one does not. That is `xfail(raises=...)`, derived
independently. Upstream shipped it; kimi re-derived why it must exist. That is the strongest
signal available that the field is right.

kimi's other two contributions do **not** exist upstream and are ours to build: a **WITNESS**
(count-by-reason, diffed every run, rendered on a surface Daniel already opens) and a fifth
bucket, **ENV-SELF** — the *test or harness* is the defect, not the environment and not the
code. kimi's argument for ENV-SELF is the strongest single thing in the round: this morning's
isolation-flag bug *was* an ENV-SELF, and it mis-filed as a **pass**. Unnamed, ENV-SELF
failures get forced into REAL (a fake alarm that sends a seat to fix working code) or into
ENV-DEP (quiet death) — and the standard repair for a "failing" test that is actually a broken
test is to weaken its assertion until it goes green, which is how a real guarantee dies
silently.

## 4. Agent memory: where the field is, and the two findings that argue against us

This is the peer set that matters most, because it is our actual product: **Letta**
(ex-MemGPT), **Zep/Graphiti**, **mem0**, **cognee**.

### 4a. The benchmark ground is contested — this matters for a gate Daniel holds

SECONDHAND, and the disputes are the point:

- mem0 reports ~92.5% on LoCoMo; Zep reports ~94.7%.
- Zep published a rebuttal arguing mem0 **misconfigured Zep** when benchmarking it.
- mem0 counter-rebutted that Zep's own 84% claim included the adversarial Category 5 in the
  numerator but excluded it from the denominator — mechanically inflating the score by ~25
  points. Rerun with the correction and ten seeds: **58.44% ± 0.20**, not 84%.
- Both headline numbers are **LLM-as-judge**, and *each vendor runs its own answer model,
  judge model, judge prompt, and question subset* — so the gap "reflects the eval harness as
  much as the memory system."
- LoCoMo conversations are only ~16k–26k tokens — **inside a modern context window**. The
  benchmark does not test the thing its scores are quoted for.
- One commentator's summary of the field's structural problem: vendor-versus-vendor is
  essentially the only public critique this space receives.

**What this does to the retrieval-benchmark FLOOR at Daniel's gate.** kimi's resolution was:
adopt a retrieval benchmark as the floor, keep outcome attribution as the bet, and *never let
the floor become the headline or we become what we criticise*. The peer evidence **validates
the second half hard** — becoming-what-we-criticise is not hypothetical here, it is the
documented behaviour of both market leaders. But it **complicates the first half**: adopting a
public benchmark imports that benchmark's defects, and LoCoMo's defects are severe.

Proposed amendment, for Daniel's gate, not to be acted on unilaterally: adopt the *discipline*
rather than the *scoreboard*. Publish the harness separately from the score; run every
comparison on a baseline we did not tune; report a distribution over seeds, never a single
number; and treat any number we cannot re-derive by a printed command as absent. That last one
is already the README's standard — this just extends it to benchmarks.

### 4b. Letta's filesystem result is a direct disconfirmation of our architecture

SECONDHAND but consistently reported: Letta dumped LoCoMo transcripts into **plain files**
attached to an ordinary agent, and scored **74.0%** — above the **68.5%** reported for mem0's
best *graph* variant. Their stated reason: agents are already extremely good at filesystem
tools (heavily represented in training data), and *specialised memory tools designed for
single-hop retrieval underperform simply letting the agent search iteratively for itself*.

We should sit with this rather than route around it. Our recall-at-action injects a handful
of pre-selected lessons per hook — **that is single-hop retrieval**, the exact pattern the
result says loses. Our funnel value sits at 6.5%. Those two facts are consistent with each
other and with Letta's finding.

This does **not** say tear the substrate down; the comparison is on a benchmark that fits in a
context window, which is the regime most favourable to "just read everything." It does say
something concrete and testable:

> **The ablation baseline for any recall benchmark we adopt must be "let the agent grep the
> corpus itself." If the substrate cannot beat grep, that is the finding, and it is one we
> need before we build more substrate on top.**

That ablation is cheap, it is ours to run, and per the method baseline the acceptance should
be pre-registered before it runs.

---

## What I propose we actually take (in order)

1. **`xfail(raises=..., strict=True)` replaces `skipif` wherever the body can safely run**,
   plus `xfail_strict = true` in `pytest.ini`. This is D's mechanism, and it delivers kimi's
   STILL-VALID-WHEN natively. Open question sent to kimi: whether it also deletes RUN-WHEN as
   a separate field (running the body *is* the satisfiability test), and whether ENV-PLAT must
   keep `skipif` because running is genuinely unsafe there.
2. **Confidence-tiered gating, oxlint-style** — the default gate is the high-confidence subset
   (REAL); the rest is visible, counted, and non-blocking.
3. **`S110` + `BLE001` as REPORT-not-gate**, instead of hand-writing the syntactic half of the
   genus-A lint. Build only the dataflow half.
4. **Provenance as a queryable column** on lessons, oxlint-style — the shape of the `cites`
   fix.
5. **The grep ablation** before any further recall substrate work.

## Sources

- [Oxlint rules & categories](https://oxc.rs/docs/guide/usage/linter/rules.html) ·
  [Oxlint config](https://oxc.rs/docs/guide/usage/linter/config)
- [Ruff `try-except-pass` (S110)](https://docs.astral.sh/ruff/rules/try-except-pass/) ·
  [Ruff `blind-except` (BLE001)](https://docs.astral.sh/ruff/rules/blind-except/)
- [pytest — skip and xfail](https://docs.pytest.org/en/stable/how-to/skipping.html) ·
  [pytest-error-for-skips](https://pypi.org/project/pytest-error-for-skips/2.0.1/)
- [Letta — Benchmarking AI Agent Memory: Is a Filesystem All You Need?](https://www.letta.com/blog/benchmarking-ai-agent-memory/)
- [Zep — Is Mem0 Really SOTA in Agent Memory?](https://blog.getzep.com/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/) ·
  [Revisiting Zep's 84% LoCoMo claim (58.44%)](https://github.com/getzep/zep-papers/issues/5)
- [mem0 — State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [The Benchmark Theatre](https://essays.bloo-mind.ai/posts/2026-05-20-mem-eval/)
