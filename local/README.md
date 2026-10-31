# `local/` — the Local layer's data home

This directory is the third of the three layers. The split exists so a sync never has to
detangle critical infrastructure, which is Daniel's own frame for it (2026-09-17):

> "I want us to have the core architecture be modular and easy to patch with the trickier local
> variables and customizations also being importable and exportable modules. if we have good
> homes and places for things we won't need to detangle critical infrastructure on every sync."

| layer | rule | lives in |
|---|---|---|
| **Core** | a fork could take it **without being told who we are** | `core/`, `agent_cli.py`, `verbs/` |
| **Features** | optional capability that still makes sense to a stranger | `core/` modules with a narrow job |
| **Local** | adopting it **requires knowing a seat, a path, a port, or a name** | **this directory** |

The test is Rill's (dsh_agent), from the 2026-09-17 out-of-tree position: *a feature is Core or
Features if a fork could take it without being told who we are; it is Local if adopting it
requires knowing a seat, a path, a port, or a name.* Anything failing that test belongs here as
**data**, not in a Python literal somewhere in `core/`.

## What belongs here

Instance values — the things a fork answers differently, and therefore the things that must not
require a code edit to change:

| file | holds | status |
|---|---|---|
| `wiring.json` | production **entry points** (each with the `why` it was added) and the **known-standalone** `core/` exceptions the wiring gate freezes | **live** — read by `scripts/checkers/check_wiring.py` |
| `reachability.json` | the instance half of the `reachability` verb: which scripts mark the production gateway, where its log lands (relative to the worktree the *process* runs from), who counts as the operator, the port shape of the phone tunnel | **live** — read by `core/comm/reachability.py` |
| `phone-panel.json` | the phone panel's allowlist: which services may be started/stopped, how each is probed, the panel's own machine config | **live** — read by `arsenal/panel/` |
| `seats.json` | seat roster: agent ids and what each one is | planned |
| `ports.json` | the ports this deployment binds and talks to | planned |
| `paths.json` | instance paths that are genuinely instance-specific (a relocated data dir, an external tool root) | planned |
| `peers.json` | peer names and endpoints for the out-of-tree/federated halves | planned |
| `baselines/` | ratchet baselines that are **values, not rules** (a frozen count, a frozen set) | planned |

Naming: one file per question, `*.json`, top level always a JSON **object** keyed by meaning.
Every file starts with `version` (the schema this loader understands), `_what` (what it answers)
and `_readme` (this file), because a data file whose purpose is only in the reader's head is a
data file that gets copied wrong.

## The second plane: the PRIVATE PROFILE (machine values)

`local/` is **committed to a public repo**, so it may carry the house defaults and DERIVATIONS and
never this machine's address or a home path. Rill's own rule for it (amendment A1, 2026-10-31) is
one sentence: **REPO-VALUE goes public, MACHINE-VALUE goes private.**

| plane | lives in | may hold | examples |
|---|---|---|---|
| **public** | `local/<name>.json` here | shape, house defaults, derivations (`${INSTANCE_ROOT}/...`, a leading `~`), and a `null` where a machine value belongs | the allowlist, the loopback ports, `tailnet_host: null` |
| **private** | `akashic-local/profile/<name>.json` (a separate private repo, found by `$AKASHIC_LOCAL` or a marker walk) | this machine's values, with a schema `version` | the phone's tailnet address, where an external tool is installed, which seat the panel reports on |

`core.local.load()` reads the public file and then **overlays** the private one, so one read gives
the complete answer and `public_only()` / `overlay()` give the two halves when the split itself is
the question. The merge rule is stated once in `core.local.merge()`: objects merge key-wise, a list
whose members all carry an `id` merges BY id (so a profile carries only the rows it changes), and
anything else is replaced.

Two behaviours are deliberate:

1. **An absent overlay FAILS OPEN and says so**, once per process, on stderr. Every caller of this
   module is a diagnostic that should still run on a fork with no profile; silence is not an
   option, because a machine value that quietly went missing reads as "UNKNOWN" on a screenshot
   and as a bug in the wrong file. A fork that ships only `local/` sees that line exactly once.
2. **A broken overlay REFUSES.** No `version`, a version newer than the loader understands, or
   invalid JSON is not "absent" — it is a profile whose shape we have not agreed to read, and
   merging it anyway would put values of unknown structure into a live read.

The gate that keeps the public half honest is the second surface of the purity ratchet
(`scripts/checkers/check_core_purity.py`, `local_purity_baseline.json`): **no tailnet or LAN
address and no home path in `local/`, `arsenal/panel/` or `scripts/phone/`**, frozen at zero.
`tests/test_the_local_surface_carries_no_machine_values.py` breaks it on purpose.

## What does NOT belong here

- **Secrets. Never. Not even in a comment.** `local/` is committed so that house defaults travel
  with the tree; a token here would be a token in git history. Secrets live in the gitignored
  secret/env planes (`AKASHIC_SECRETS_DIR` and friends). `tests/test_local_layer.py` scans every
  `local/*.json` for secret-shaped keys so this is a gate rather than a promise.
- **Rules that derive.** "Enumerate every `scripts/bifrost_runner_*.py`" and "enumerate every
  hook under `agent/harness/hooks/`" are RULES, not values, and they stay in
  `check_wiring.py` as code. Moving a derivation into data freezes it at today's answer, which
  is precisely the drift those enumerations were written to stop (a hand-written runner list
  named only `deepseek` and left gemini, kimi and sol invisible for a week).
- **Anything Core could answer without knowing who we are.** If a deployment-independent
  default would do, it is Core, and putting it here makes every fork maintain a file it did not
  need.

## How it is read

`core/local.py` is the **one loader**. Nothing else parses this directory.

```python
from core.local import load, optional, status, strings

wiring = load("wiring")                       # REFUSES loudly if the file is absent
seats  = optional("seats")                    # None when a fork has not adopted it yet
paths  = list(map(str, strings(wiring["entry_points"], what="entry_point")))
```

Two behaviours are deliberate and both are about **not** rendering an absence as a zero:

1. **A missing required file raises `LocalDataMissing`**, naming the path and the remedy. A
   checker whose instance values went missing must not report "no entry points" and "every
   exception is stale" — that is a wall of findings generated by the absence of the list that
   was supposed to bound them.
2. **A file that exists but is corrupt also raises.** "Absent" and "broken" are different
   answers, and only one of them is an expected deployment state. `status()` keeps the three
   states apart (`files` / `missing` / `unreadable`) so `py agent_cli.py doctor --deploy` can
   tell "not adopted" from "adopted and broken".

The loader resolves the root by walking up from `core/local.py` — **not** via `AI_SETUP`. A
checker run against a shadow worktree (the `check_wiring` canary does exactly this) must read
*that tree's* Local data; an env-driven root would silently hand it the main checkout's.

## The known limitation, stated on purpose

This layer is **partly populated**, and its own coverage should be read the same way as any other
merged view in this house: it reports what it carries. Phase 1 moved the brief's named offender
(`check_wiring.py`'s hardcoded `ENTRY_POINTS`/`EXCEPTIONS`). The Local values still embedded in
Core code are not gone — `agent_cli.py` alone carries 229 seat/path/port/fork literals, and
`core/fleet/seat_launchers.py` 118 — and the gate that freezes them
(`scripts/checkers/check_core_purity.py`) reports the totals so the ratchet can only go down.
Until those move, the honest statement is: **the home exists, the first tenant has moved in, and
the rest of the street is still standing in the wrong building.**
