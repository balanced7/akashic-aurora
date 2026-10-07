# Simon's tooling stack — the five latent bugs, verified against OUR master

Written by claude (Vandor), 2026-10-05, during the analysis Daniel asked for ("first lets
analyze it and see what it does and why"). **Nothing merged.** This file records only what I
verified myself on `master`, independent of Simon's claims.

Source of the claims: PR #37 (G4, `tooling/g4-types-to-zero`), commit `a040c189`
"refactor(cli): mark six latent undefined names in agent_cli for G4.P2", advisory ADV-033,
intended-changes IC-0008..IC-0020. Simon's method was basedpyright in standard mode; the
findings are F821 (undefined name).

## Method

Not a grep. Full scope resolution over `agent_cli.py`'s AST: module-level bindings taken from
`tree.body` only (an `ast.walk` collects function-local imports and over-reports — my first
pass made exactly that error and cleared four of the five falsely), per-function locals taken
from params, assignments, local imports, `with`/`for`/`except` targets. Then confirmed at
runtime by importing the module and checking `hasattr`.

> House law applied, surfaced by the recall door mid-analysis: *"gate it with a source grep of
> the seam's ACTUAL shape, not the note — inline comments lie."* Extended here to my own
> instrument: the first checker was wrong, and the wrongness was invisible until re-derived.

## Result: all five confirmed, 6 call sites

```
agent_cli.time               ABSENT at runtime
agent_cli.io                 ABSENT at runtime
agent_cli.REPO               ABSENT at runtime
agent_cli.capture_event      ABSENT at runtime
agent_cli.get_agent_memory   ABSENT at runtime
```

| # | site | name | failure mode | severity |
|---|---|---|---|---|
| 1 | `_continuity_drift` :1910 | `get_agent_memory` | **silent** — swallowed, returns `""` | HIGH |
| 2 | `_wish_curate_run` :2419 | `capture_event` | **silent** — `except Exception: pass` | MEDIUM |
| 3 | `_wish_write` :2501 | `capture_event` | **silent** — `except Exception: pass` | MEDIUM |
| 4 | `cmd_season_score` :6201 | `io` | loud NameError, command dies | LOW |
| 5 | `cmd_locks` :7957 | `time` | **silent** — age/ttl never render | LOW |
| 6 | `cmd_tool_run` :10250 | `REPO` | loud NameError, after printing success | LOW |

## 1. The continuity drift line has never once rendered

The only production caller is `agent_cli.py:2214`, `_continuity_drift()` — **no arguments**, so
`notes is None`, so line 1910 runs `get_agent_memory()`, raises NameError, and the function's
outer `except Exception: return ""` swallows it.

The four tests in `tests/test_continuity_drift.py` **all pass `notes=` explicitly** (lines 51,
63, 70, 80). Every one is green. None reaches the production path.

Runtime proof:

```
_continuity_drift() with no notes (the ONLY production call shape):
  returns ''   <- empty string, indistinguishable from 'no drift'
```

And the docstring reads *"Silent when the notes are newer than HEAD -- no drift, no line."* So
a seat reading the code concludes the absent line means no drift. It has always meant broken.

**This is the house's own defect shape, found by an outside instrument.** It is the same error
I made yesterday with `match_text`: nine green pins on the seam I believed in, none on the seam
that runs. Static type checking found by a different route what mutation testing found by one.

## 2. Zero wish events on the spine, against 254 wishes in the ledger

Both wish paths build a careful `detail` payload and call `capture_event`, undefined, inside
`try: ... except Exception: pass`.

Measured directly against akashic-redis:16379, 2026-10-05:

```
scanned 11,242 events across 58 streams (events:*:raw)
events with kind='wish':  0
docs/WISHLIST.md:       254 wishes, highest W251
```

The spine is healthy — 25 other kinds present, `touch` 3,037, `learning` 718, `decision` 393.
It is specifically `wish` that is absent, and it is absent because the writer raises.

**Calibration, honestly:** nothing currently reads `kind="wish"` — I grepped for consumers and
found none. So this is a writer that never writes into a plane nobody reads *yet*. It is not
lying to anyone today. It becomes a lie the moment the EYE, the timeline, or any
friction-over-time view enumerates event kinds and reports a confident zero.

The house law for exactly this, surfaced by the recall door while I was measuring it:

> *"A sensor with no reader and a field with no writer are two different defects and both
> render as a confident 0."* — `partial_wiring_is_the_shape_module_gates_cannot_see`

W251, filed yesterday, says *"a timeout is not a first-class event ... the single fact that
explains a day of silence is in the one plane that scrolls away, while the planes that persist
know nothing about it."* The door that recorded that complaint has the defect the complaint
describes.

## 3–6. The remainder

- `cmd_locks` — `age` is built inside `try`, uses `time.time()`, NameError, `pass`. **Lock age
  and TTL have never displayed.** That is the field that tells a seat whether a peer's advisory
  lock is stale, which is load-bearing for the concurrency design.
- `cmd_season_score --round-file` — hard NameError on `io`. Flag has never worked.
- `cmd_tool_run --no-sandbox` — prints `[tool] running ... UNSANDBOXED (operator override)`
  and *then* dies on `REPO`. The reassuring message precedes the crash.

## What this says about the stack

Simon's claim was "13 latent bugs, each with a regression test that fails before the fix." I
checked the six in `agent_cli.py`. **All six are real.** The regression tests exist in his tree
(`tests/test_g4_latent_*.py`, 13 files, one per bug).

This is worth more to us than the tooling it arrived inside. The bug fixes can be taken
independently of uv, ruff, or anything else in the stack — each is its own commit by design,
and his rollback plan says so explicitly: *"To keep the bug fixes, revert only the annotation
batches."*

## Not checked here

- The other 7 latent bugs (IC-0008..IC-0020 outside `agent_cli.py`).
- Whether his *fixes* are correct, as opposed to whether the *bugs* are real. Different
  question, not answered by this file.
