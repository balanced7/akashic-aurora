# Intended-change register

Status: current
Class: reference

Every oracle DIFF that a goal means to cause is registered here BEFORE the commit that causes
it (invariant I4). `oracle.py compare` reads the ```toml blocks below: an entry covers a diff
item when its `component` matches and its `key` glob (fnmatch) matches the item key printed in
the DIFF line (for example `help:agent_cli.py`, `name:core.x.f`, `id:tests/test_x.py::t`).

Fields: `id` (IC-NNNN, never reused), `component` (O1-O10), `key` (glob), `reason`,
`goal` (the goal that registered it). A test renamed without loss carries `maps_to`.

No entries yet (G0 makes no change to the repo's behaviour).
