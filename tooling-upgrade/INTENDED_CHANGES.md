# Intended-change register

Status: current
Class: reference

Every oracle DIFF that a goal means to cause is registered here BEFORE the commit that causes
it (invariant I4). `oracle.py compare` reads the ```toml blocks below: an entry covers a diff
item when its `component` matches and its `key` glob (fnmatch) matches the item key printed in
the DIFF line (for example `help:agent_cli.py`, `name:core.x.f`, `id:tests/test_x.py::t`).

Fields: `id` (IC-NNNN, never reused), `component` (O1-O10), `key` (glob), `reason`,
`goal` (the goal that registered it). A test renamed without loss carries `maps_to`.

## IC-0001: one launcher on every OS (G1.P5)

`core.paths.python_launcher()` names the command that runs Aurora's Python in text shown to
agents (help, hints, hook messages). Before G1 it returned `py` on Windows even with uv
installed; after G1 it returns `uv run` wherever uv and pyproject.toml are present, falling
back to `py` (Windows) or `python3`. On Linux and macOS the text is unchanged (`uv run` already),
so no oracle run on this machine can show the difference: the key below matches nothing on
Linux on purpose, so it can never mask an unrelated diff.

```toml
id = "IC-0001"
component = "O4"
key = "windows-only:python_launcher"
reason = "Windows text names `uv run` instead of `py` when uv is installed (plan G1.P5)"
goal = "G1"
```

## IC-0002: PEP 585/604 annotation spelling in annotation-sensitive modules (G3.P1, UP wave)

The `UP` wave rewrites `List[str]` to `list[str]` and `Optional[X]` to `X | None` (UP006,
UP045, target py311). In the 89 annotation-sensitive modules O5 records the full signature
text, so the spelling change shows as `annot:<module>.<name>` items. The types are the same
objects at runtime for every consumer that reads them (typing.get_type_hints, pydantic, the MCP
SDK's schema builder); the proof of that is O4c (the MCP tool list with full input schemas),
which must stay EQUAL, and O5's `bare` signatures (names, kinds, defaults), which must not
change. Covers annotation-text items only, never `sig:` or `name:` items.

```toml
id = "IC-0002"
component = "O5"
key = "annot:*"
reason = "PEP 585/604 spelling of the same annotation types (ruff UP006/UP045, plan G3.P1); O4c stays EQUAL"
goal = "G3"
```

## IC-0003: five rule families moved from G3's zero set to the stretch ratchet (D-G3-1)

Plan G3 Fallback: a demoted family carries an entry here. PTH (5,158 findings), BLE (2,423),
T20 (3,968 outside scripts/), S (1,700) and N (808) have no autofix for ~13k of their findings,
and zeroing them would need either more suppressions than T4 allows (S603/S607/S310 alone ~550
against ~320 of room) or test renames that change pytest node ids (N802; O1 must keep every
id). The operator chose on 2026-10-02 to ratchet them instead (counts in
tooling-upgrade/ratchet.json may never rise). No runtime behaviour changes; no toml block, so
this entry can mask no oracle diff.

## IC-0004: bare `except:` becomes `except Exception:` (G3.P3, E722)

A bare `except:` also catches `KeyboardInterrupt`, `SystemExit` and `GeneratorExit`;
`except Exception:` does not, so Ctrl-C and `sys.exit()` inside those `try` bodies now
propagate instead of being swallowed. Plan G3.P3 policy. Each converted site is checked for a
code path that relies on catching those three (listed in the G3.P3 ledger row). Not visible to
the oracle (no toml block).

## IC-0005: implicit Optional made explicit (G3.P3, RUF013)

`def f(x: str = None)` becomes `def f(x: str | None = None)`: the annotation now states what the
default already allowed. No call behaves differently. In annotation-sensitive modules O5 shows
`annot:` items; the MCP protocol module (ai_setup_mcp.py) keeps its one implicit Optional (`find(limit)`,
suppressed with a reason), so O4c (tool input schemas) is unaffected and must stay EQUAL.

```toml
id = "IC-0005"
component = "O5"
key = "annot:*"
reason = "implicit Optional made explicit (ruff RUF013, plan G3.P3); O4c stays EQUAL"
goal = "G3"
```


## IC-0006: annotation corrections for the type checker (G4.P2)

G4.P2 tier (2) corrects or completes annotations so basedpyright can check the code: a return
type that can be `None` says so, a parameter annotated `str` that takes `Path | str` says so,
generics get their type arguments. In annotation-sensitive modules O5 shows these as `annot:`
items. As with IC-0002, the proof that no runtime consumer sees a different type is O4c (MCP
tool input schemas), which must stay EQUAL, plus O5's `sig:`/`name:` items, which this entry
never covers. The MCP tool functions in ai_setup_mcp.py keep their annotations unchanged.

```toml
id = "IC-0006"
component = "O5"
key = "annot:*"
reason = "annotation-only corrections for basedpyright (plan G4.P2 tier 2); O4c stays EQUAL"
goal = "G4"
```

## IC-0007: narrowing that only differs on an unreachable branch (G4.P2)

Where the checker cannot see that a value is never `None` (or never the other union member),
G4.P2 narrows it explicitly: `assert x is not None` in tests (a test assertion; O9 counts may
only rise), and in runtime code `assert` / `isinstance` / `typing.cast` only at sites where the
generator shows from the surrounding code that the other branch cannot happen (the value was
just set, checked, or produced by a call that never returns `None` for these arguments). On that
unreachable branch the exception type would differ (AssertionError instead of AttributeError or
TypeError); on every reachable path nothing changes. Sites where the other branch IS reachable
are real defects and get their own `Fixes-latent` entries with regression tests, or stay
suppressed with a LATENT reason. Not visible to the oracle (no toml block).

## Latent-bug fixes found by the type checker (G4.P2, batch A)

Each entry: the defect, the fixing commit (`fix_commit`) and a regression test that fails on
the fix's parent and passes on HEAD (`certify.py assert-latent-regressions`). The `key` matches
no oracle item on purpose: these entries document behaviour fixes and mask no diff.

### IC-0008: fixes latent bug: continuity-drift-memory

agent_cli.py `_continuity_drift` called `get_agent_memory` without importing it; with notes=None the NameError was swallowed, so the boot drift line never appeared. Now imported.

```toml
id = "IC-0008"
component = "O1"
key = "latent:continuity-drift-memory"
reason = "fixes latent bug: continuity-drift-memory (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "b92d55cdf9fc76ca7fe49526d2909d3d6ebea5d7"
regression_test = "tests/test_g4_latent_continuity_drift_memory.py"
```

### IC-0009: fixes latent bug: wish-capture-event

agent_cli.py `cmd_wish` and `cmd_wish_curate` called `capture_event` without importing it, inside `suppress(Exception)`, so no wish event was ever captured. Now imported.

```toml
id = "IC-0009"
component = "O1"
key = "latent:wish-capture-event"
reason = "fixes latent bug: wish-capture-event (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "553229e7fdf470d4112f4907076b88d745e98a0f"
regression_test = "tests/test_g4_latent_wish_capture_event.py"
```

### IC-0010: fixes latent bug: season-score-round-file

agent_cli.py `cmd_season_score --round-file` used `io.open` without `import io`: every run with a round file crashed with NameError. Now reads the file with `Path.read_text`.

```toml
id = "IC-0010"
component = "O1"
key = "latent:season-score-round-file"
reason = "fixes latent bug: season-score-round-file (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "3e9b3e9c03d80f1d5c3dbe89006efb2d83529bb5"
regression_test = "tests/test_g4_latent_season_score_round_file.py"
```

### IC-0011: fixes latent bug: locks-age

agent_cli.py `cmd_locks` used `time.time()` without importing `time`; the per-lock except swallowed the NameError, so the lock age/ttl annotation never rendered. Now imported.

```toml
id = "IC-0011"
component = "O1"
key = "latent:locks-age"
reason = "fixes latent bug: locks-age (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "4425d8fdc043dfe33bcacc8dacfabc8e1e406ab5"
regression_test = "tests/test_g4_latent_locks_age.py"
```

### IC-0012: fixes latent bug: tool-run-unsandboxed

agent_cli.py `cmd_tool_run --no-sandbox` passed `cwd=REPO`, an undefined name: every unsandboxed run crashed with NameError. Now uses the same repo root as the sandboxed path.

```toml
id = "IC-0012"
component = "O1"
key = "latent:tool-run-unsandboxed"
reason = "fixes latent bug: tool-run-unsandboxed (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "1f354378d53ad795f3eccf5ffe24687ecee648e4"
regression_test = "tests/test_g4_latent_tool_run_unsandboxed.py"
```

### IC-0013: fixes latent bug: floors-json-exit

arsenal/__main__.py `floors --json` read `hard`, which was computed only in the text branch: UnboundLocalError. Now computed before the branch, so --json exits with the same code as text mode.

```toml
id = "IC-0013"
component = "O1"
key = "latent:floors-json-exit"
reason = "fixes latent bug: floors-json-exit (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "04f1dfe221d0f22a2fe7704601fd3be3739added"
regression_test = "tests/test_g4_latent_floors_json_exit.py"
```

### IC-0014: fixes latent bug: sift-junction-record

agent_cli.py `cmd_sift --junction` recorded `p.occurrences`/`p.truncated`, which JunctionPack does not have: every non-dry-run junction sift crashed after the paid tiers ran. Now records the junction count and truncated=False.

```toml
id = "IC-0014"
component = "O1"
key = "latent:sift-junction-record"
reason = "fixes latent bug: sift-junction-record (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "6112c542569c56d3da42ce03d5660d38975e7294"
regression_test = "tests/test_g4_latent_sift_junction_record.py"
```

### IC-0015: fixes latent bug: mcp-http-port

ai_setup_mcp.py `--http` called `mcp.run(..., port=...)`, but the installed FastMCP.run has no `port` parameter: TypeError at startup. Now sets `mcp.settings.port` and runs; no MCP tool function or schema changed.

```toml
id = "IC-0015"
component = "O1"
key = "latent:mcp-http-port"
reason = "fixes latent bug: mcp-http-port (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "459577af061611cac6f1d44a6afaca9c740fcbe6"
regression_test = "tests/test_g4_latent_mcp_http_port.py"
```
