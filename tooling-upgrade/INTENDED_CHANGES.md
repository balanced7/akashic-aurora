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
