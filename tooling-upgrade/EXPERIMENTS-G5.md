# G5.P1 test-tooling experiments

Status: current
Class: reference

Plan G5.P1: adopt each tool only on evidence. Each experiment ran the full suite through the
oracle (`oracle.snapshot(..., mutate=<pyproject addopts edit>)` in a throwaway tree, so every run
is recorded `dirty` and can never pass as the official suite record) and compared O1 with g0
(`oracle.py compare g0 <label> --components O1`). Raw logs: `tooling-upgrade/snapshots/<label>/raw/`
(git-ignored working records). The `certify.py assert-experiments` check (G5.experiments-verdicts)
reads the toml blocks below and checks that the configuration matches each verdict.

## pytest-xdist (`-n auto --dist loadfile`)

Two full-suite runs at 0a498377 (label `exp-xdist`). Both aborted at collection, so O1 compared
`DIFF` (no test ran: "collects 0 < baseline"):

- `Different tests were collected between gw7 and gw4` (run 1: 4 workers; run 2: 22): the
  parametrize ids of `tests/test_remote_bridge_listener_pins.py::test_refusal_is_flat_on_the_wire`
  embed a signed payload stamped with the current time, so workers that collect in different
  seconds see different node ids.
- `tests/test_install_showcase.py` mints into the shared `data/verb-registry/` at import time;
  workers raced on the same file (`FileNotFoundError ... deepseek.json.tmp`).
- Every test process also flushes the shared Redis test db 15 on import (tests/isolate_canonical),
  so concurrent workers would erase each other's state.

Making the suite xdist-safe means editing test files (deterministic ids, import-time writes into
a per-worker directory) and a per-worker Redis db -- more than "a small conftest change", so the
suite stays serial.

`test-fast` (the plan's fallback: xdist for test-fast only), measured on the clean worktree after
the randomly runs: the smoke set (2 files, 54 tests) takes 1 s serial and 2 s with `-n auto
--dist loadfile`; a 60-file selection (`tests/test_t1*.py`, first 60) takes 70 s serial and 31 s
with xdist, but xdist adds a failure the serial run does not have
(`tests/test_t157_wire_sharded_async.py::test_p3_the_caller_no_longer_does_the_work`) in 2 of 3
runs. A gate that flakes is worse than a slower gate, so test-fast stays serial too.

```toml
experiment = "xdist"
verdict = "REJECT"
evidence = "snapshots/exp-xdist: 2/2 runs aborted at collection (workers collected different ids; import-time registry race); O1 DIFF. test-fast: smoke set no faster (1 s vs 2 s); 60-file selection 70 s -> 31 s but a new failure in 2/3 xdist runs (test_t157_wire_sharded_async)"
```

## pytest-randomly (3 seeds)

Labels `exp-rand-1`, `exp-rand-2`, `exp-rand-3`: one full run each with `-p randomly
--randomly-seed=<n>`, isolated reruns of every non-pass with `-p no:randomly`.

| seed | passed | failed | skipped | O1 vs g0 |
|---|---|---|---|---|
| g0 (file order) | 7336 | 106 | 71 | -- |
| 1 | 7252 | 132 | 129 | DIFF: skip count 129 > 71 |
| 2 | 7060 | 194 | 267 | DIFF: skip count 267 > 71; tests run 7261 < 7379 (T7) |
| 3 | 7339 | 110 | 71 | EQUAL |

Seeds 1 and 2 are not O1 EQUAL (seed 3 is), so pytest-randomly stays installed and OFF by default
(`addopts = [..., "-p", "no:randomly", ...]`, unchanged since G1). The failures pass when rerun
alone (so they are order-dependent, not broken); the extra skips are Redis-backed tests that
decide "redis not available" after an earlier test has left the client or its config patched.
The 298 order-dependent test ids (70 files; each was stable-pass at g0 and skipped or failed under at least one seed) are listed in tooling-upgrade/order-dependent-tests.txt, referenced from BACKLOG.md (ADV-042). Seed 1 ran while an unrelated
`tests/test_pre_commit.py` process flushed db 15 once; seeds 2 and 3 ran undisturbed and reach
the same verdict.

```toml
experiment = "randomly"
verdict = "REJECT"
evidence = "snapshots/exp-rand-1..3: O1 DIFF on seeds 1 and 2 (skips 129 and 267 vs 71), EQUAL on seed 3; order-dependent ids in BACKLOG ADV-042"
```

## --doctest-modules on the RUNTIME packages

`pytest --import-mode=importlib --doctest-modules core agent arsenal <8 root runtime modules>` in
a throwaway tree at 0a498377 (REDIS_DB=15, temp AI_SETUP): collection of all 360 RUNTIME
modules is clean, and it collects **0** doctest items (exit 5, "no tests collected"); the only
`>>>` in RUNTIME code are shell-marker strings in agent_cli.py and seat_topology.py. With the
default import mode it does not even collect (`import file mismatch`: arsenal/fl/vfx/arsenal_patterns.py
vs .../generated/arsenal_patterns.py). Nothing to gain, and exit 5 would make a gate red.

```toml
experiment = "doctest"
verdict = "REJECT"
evidence = "0 doctest items in 360 RUNTIME modules (pytest exit 5); default import mode: collection error on a duplicated basename"
```

## Coverage (always on)

`poe test` captures O1 and O10 (branch coverage of core, agent, arsenal, scripts) and compares
both with g0: a package dropping more than 0.5 pp fails it. `[tool.coverage.run]` carries the
same branch/source settings O10 passes on its command line (commit e522a0da).

```toml
experiment = "coverage"
verdict = "ADOPT"
evidence = "poe test = snapshot suite --components O1,O10 + compare g0 suite --components O1,O10 (e522a0da)"
```
