---
akashic_id: art_20260803_gate-convergence-experiment_d82386
akashic_sha: 40660c488797
schema_version: 1
status: current
type: report
date: 2026-08-03
title: gate-convergence-experiment
gist: "# Does hardening a guard converge? — three rounds against my own gate **2026-08-03.** Daniil: *\"Go for it, I am invested.\"* The question, fr"
visibility: fleet
body_type: markdown
seats: []
category: [conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-03T21:46:35"
updated: "2026-08-03T21:46:35"
---
<!-- GENERATED PROJECTION of art_20260803_gate-convergence-experiment_d82386 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# gate-convergence-experiment

# Does hardening a guard converge? — three rounds against my own gate

**2026-08-03.** Daniil: *"Go for it, I am invested."* The question, from the previous round:
**does hardening a guard converge, or does every patch open a new seam?**

**Answer: it converged — but only once the rule stopped describing WHERE the evidence sat and
started describing WHAT the evidence MEANS.** The location-based patch displaced the hole into a
*more* idiomatic position, making the evasion easier to hit by accident.

---

## Method

An **arena**: a throwaway `git worktree` at HEAD. Each attack is appended to a real module, the real
`check_wiring` runs, and the file is reverted. Two things are scored, because a guard can fail two
ways:

- **EVASION** — dead code the gate reports clean
- **FP-DELTA** — how the gate's verdict on the *untouched* tree moves. Over-hardening is the failure
  mode people forget, and this repo's own comments warn about it twice: the only remedy the gate
  offers is an exemption, so a gate that cries wolf gets fed exceptions until it guards nothing.

Calibrated 3/3 on known-outcome controls before I trusted it — a plain dead function (CAUGHT), the
already-fixed A1 shape (CAUGHT), and a name-collision (LANDED, the documented fail-open).

## Round 1 — four accidental-evasion classes vs the T143 gate

| attack | result |
|---|---|
| `__all__ = ["dead_but_exported"]` | **LANDED** |
| `def timeout()` — `timeout=` is a kwarg everywhere | **LANDED** (known collision) |
| `def _h(x: "dead_annotated" = None)` — string annotation | **LANDED** |
| a doctest naming the function | CAUGHT |

The first is the serious one. `__all__` sits at module level, *outside* the function body, and the
rule only excluded a function's own body — so **every module with an export list was immunising
exactly the functions it exported.**

## Round 2 — the patch, and what it bought (T144)

Rule: *a string naming a function counts only from **another module***. A string is how a **caller**
dispatches (`getattr(mod, "promote")`), and a caller lives elsewhere.

Arena result before landing: closes two evasion classes, **zero false positives**, and surfaces
**8 more genuinely dead functions** — all hand-verified to have zero external references:

```
core/foundation/store.py::setex
core/signals/coordinator_api.py:: get_bootstrap_info, get_context_summary, get_startup_briefing,
    get_startup_context, get_startup_decisions, get_startup_learnings, request_handoff
```

Seven of eight in one file. `coordinator_api.py` carries a **self-describing API catalogue** —
strings naming its own functions, e.g. `:600  "code": "briefing = api.get_startup_briefing()"` — and
that catalogue had been immunising every function it documented.

## Round 3 — the hole didn't close, it MOVED (T145)

The same attack, one file up:

```python
core/comm/bus.py        def dead_via_pkg_init(): ...      # nothing calls it
core/comm/__init__.py   __all__ = ["dead_via_pkg_init"]   # a DIFFERENT module
```

**LANDED.** `__init__.py` satisfies the cross-module test perfectly — and it is the single most
idiomatic home for `__all__` in Python. **The patch moved the evasion somewhere more common.**

Chasing the location would only move it a third time. The converging fix names the semantics
instead: **an `__all__` entry DECLARES an export surface; it does not USE anything.** Excluded
wherever it lives. Closes both cases, **zero FP cost**, and cannot create a false positive by
construction — a function whose only mention is an export list is by definition not called.

## The scoreboard

| round | fix | outcome |
|---|---|---|
| T143 | descend module-level containers | **converged** — class closed cleanly |
| T144 | string evidence must cross modules | **displaced** — closed one case, moved the other |
| T145 | `__all__` is never evidence, anywhere | **converged** — closed at the level of the idea |

Final state: **38/38 pins green across seven wiring pin files, gate PASS, baseline 116, zero false
positives introduced across all three rounds.**

## The transferable rule

> When a guard is evaded, ask whether your patch describes **where** the evidence sat or **what** the
> evidence means. A location rule displaces the hole; the displacement often lands somewhere *more*
> idiomatic, which makes the evasion more common rather than less. After patching, deliberately try
> the same attack **one structural level up**.

## One sentence, three layers

The morning's verb census produced this line about the door-parity manifest:

> *A manifest entry is a claim, not a reference — it proves someone looked at it once, not that
> anything uses it.*

It turned out to be the right rule for `coordinator_api.py`'s API catalogue, and then for `__all__`.
Same pathology, three layers, found by three different means on one day.

## Honest limits

- The **independent-adversary property was lost this round.** Both DeepSeek seats wedged (see below),
  so rounds 1–3 above are *my* systematic probes, not an independent red team. Round 1 of the
  previous session — where `deepseek-red` broke the gate unprompted — is the only clean evidence of
  independent discovery.
- **`def timeout()` still lands.** Name collision is documented fail-open and was not fixed; the gate
  is blind to any dead function sharing a name with a common identifier.
- Four zombie runners from the earlier round held their singleton locks with ~1.8h-stale heartbeats,
  blocking every relaunch, and the task harness reported them "completed" while the processes lived
  on. Filed as **W125** — the lock trusts pid-liveness, the roster trusts heartbeat, and when they
  disagree the lock wins. Verified the heartbeat runs on an independent daemon thread whose comment
  says it survives "even mid-wedge", so a stale beat IS a real death signal.
- Re-sending an identical brief to a seat that never received it is a silent no-op (dedup is keyed
  on content, not delivery). Hit three times. Filed as **W124**.
