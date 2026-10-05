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

### IC-0016: fixes latent bug: manual-probe-worklive-prefix

tests/manual/l1_worklive_probe.py, l3a_liveness_view_probe.py and l3b_auto_revive_probe.py still
read `core.comm.liveness.WORKLIVE_PREFIX`, a constant the namespace-isolation change replaced
with the per-call `_worklive_prefix()`: each probe raised AttributeError at its key write or
cleanup when run by hand. They now call `liveness._worklive_prefix()`.

```toml
id = "IC-0016"
component = "O1"
key = "latent:manual-probe-worklive-prefix"
reason = "fixes latent bug: manual-probe-worklive-prefix (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "87cdeca6ad884486ce6cb10351815b418a36832c"
regression_test = "tests/test_g4_latent_manual_probe_worklive_prefix.py"
```

### IC-0017: fixes latent bug: doctor-twin-legacy-seat

core/comm/doctor.py twin-sessions check joined `s[:8]` for every seat, but
`wake_seat.iter_seats()` yields `(path, None)` for the legacy session-less seat file: the
TypeError was swallowed and the "N LIVE SESSIONS share this agent id" finding vanished whenever a
legacy seat sat next to a session seat. The legacy seat is now labelled "legacy".

```toml
id = "IC-0017"
component = "O1"
key = "latent:doctor-twin-legacy-seat"
reason = "fixes latent bug: doctor-twin-legacy-seat (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "e3a211864e5a5e1ae833ac4d5d5ef4f5c93bfe68"
regression_test = "tests/test_g4_latent_doctor_twin_legacy_seat.py"
```

### IC-0018: fixes latent bug: ask-peer-poll-caught-kwarg

core/comm/ask.py `ask_peer` poll-failure handler called `BoundaryOutcome.caught(..., ask_id=...)`,
a keyword `caught()` does not accept: the handler itself raised TypeError, breaking ask_peer's
"never raises" contract whenever sweep()/state_of() failed during polling. The message id now
goes in `ref=`, the field BoundaryOutcome documents as the handle to act on.

```toml
id = "IC-0018"
component = "O1"
key = "latent:ask-peer-poll-caught-kwarg"
reason = "fixes latent bug: ask-peer-poll-caught-kwarg (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "fffe13bdae84b8f6d8deadf7b941b2260f8b2d4e"
regression_test = "tests/test_g4_latent_ask_peer_poll_caught.py"
```

### IC-0019: fixes latent bug: gemini-chat-smoke-agent-name

scripts/gemini_chat.py `--smoke` built its agents with `geminiAgent(...)`, but the class is
`GeminiAgent`: every smoke run died with NameError right after its "pre" line (ADV-034). The
smoke body moved into `_smoke()` unchanged except for the class name, so a test can run it offline.

```toml
id = "IC-0019"
component = "O1"
key = "latent:gemini-chat-smoke-agent-name"
reason = "fixes latent bug: gemini-chat-smoke-agent-name (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "ef7b97d0c71f3e6f5008eaea793985ef7cd57473"
regression_test = "tests/test_g4_latent_gemini_chat_smoke_agent.py"
```

### IC-0020: fixes latent bug: vfx-probe-none-delta

scripts/vfx_probe_chroma.py and vfx_probe_metrics.py formatted `{d * 100:.1f}` with the result of
`pixel_delta()`/`chroma_delta()`, which return None when no pixel is opaque in both renders: the
report died with TypeError mid-table. The percentage now prints "n/a" for that pair; real deltas
print exactly as before.

```toml
id = "IC-0020"
component = "O1"
key = "latent:vfx-probe-none-delta"
reason = "fixes latent bug: vfx-probe-none-delta (plan G4.P2 tier 1)"
goal = "G4"
fix_commit = "1055363795bba050bd4f4f96a6f4c3c7a94a0ad3"
regression_test = "tests/test_g4_latent_vfx_probe_none_delta.py"
```

## IC-0021: the pre-commit backstop gains a prek stage (G5.P2)

scripts/githooks/pre_commit.py runs `prek run` (the .pre-commit-config.yaml hooks: ruff check
--fix and format on Python files, uv lock/export, toml/yaml/merge-conflict/large-file checks,
zizmor, actionlint) over the STAGED files, after the private-plane guard and before the derived
docs are regenerated. A hook finding (prek exit 1, including a fixing hook that rewrote a staged
file) now blocks a commit that passed before; prek missing, a missing config or a prek crash
only warns, as the comprehensibility gate does. Hooks are git-side, so no oracle component sees
this (no toml block); tests/test_pre_commit.py `-k prek` pins both halves of the policy.

## IC-0022: the generated requirement files carry uv's own header (G5.P2)

requirements.txt and requirements/gemini-web.txt are now exactly what `uv export ...
--output-file <file>` writes, so the uv-export hooks and `poe lock-check` agree byte for byte.
The pins are unchanged; the three-line "GENERATED -- do not edit" header became uv's two-line
"This file was autogenerated by uv via the following command" header. Registered after its
commit (15d53088), which no oracle component sees (requirement files are on the O8 allowlist;
no toml block).

## Latent-bug fixes found during G5

### IC-0023: fixes latent bug: prior-art-launcher

scripts/generators/gen_prior_art_register.py names the launcher in PRIOR_ART.md's "Regenerate
with" line through core.paths.python_launcher(). Run as a script (`uv run python
scripts/generators/gen_prior_art_register.py`, its documented use), the repo root is not on
sys.path, the import failed, and the line fell back to `py`; check_comprehensibility imports the
generator with the root importable, renders `uv run`, and so reported the freshly regenerated
doc as stale on every run. `_pyl()` now puts the repo root on sys.path first.

```toml
id = "IC-0023"
component = "O1"
key = "latent:prior-art-launcher"
reason = "fixes latent bug: prior-art-launcher (found regenerating docs in G5.P4)"
goal = "G5"
fix_commit = "8bc3020a9bdcd23268c751bf07c04c47a35ccc89"
regression_test = "tests/test_g5_latent_prior_art_launcher.py"
```
