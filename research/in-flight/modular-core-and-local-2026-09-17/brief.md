# Good homes: a modular core, and local customization as an importable module

**House think, opened 2026-09-17 by Daniel. This is a proposal to ATTACK, not a decision to ratify.**
It goes to Serge's fleet afterwards as a bilateral proposal, so it should survive our own seats first.

## Daniel's ask, verbatim — the framing is his, not mine

> "I want us to have the core architecture be modular and easy to patch with the trickier local
> variables and customizations also being importable and exportable modules. if we have good homes
> and places for things we won't need to detangle critical infrastructure on every sync"

and earlier in the same conversation:

> "How can we define this in a process and make things modular so we don't need to re-architect
> things each time to integrate or synchronize features?"

Everything below is elaboration on those two sentences. Where a name here is useful ("the three
layers", "the detector"), the naming is mine and the generating idea is Daniel's — the distinction
matters because naming accrues credit that belongs to originating.

## Why now: tonight's evidence, measured not argued

Serge's fleet sent us a 16-file package ("the brain build": 8 memory/knowledge organs, 12.3k typed
synapses, a DSH connectome adapter). Integrating it produced a clean natural experiment, because the
package contains both new files and edits to shared ones.

| What | Cost to integrate |
|---|---|
| 7 files that are NEW to us (`edge_growth.py`, `homeostat.py`, `dsh_adapter.py`, 3 docs, a smoke test) | **zero** — no collision, drop them in |
| 6 shared files with small deltas (`aggregator`, `learning_store`, `ranker`, `at_action`, `funnel`, `knowledge_map`) | +3 to +24 lines each — portable by hand |
| `core/eye/index.py` | +68 / −49 — needs reading |
| **`agent_cli.py`** | **+328 / −501 across 40 hunks** — do not take |

All deltas measured with line endings normalised; their tree is CRLF, ours LF, so a raw diff reads as
a total rewrite and hides the real change. That normalisation step is itself part of any process we
define.

**The finding: new files were free, shared-file edits were the entire cost, and one file was 80 % of
it.** Nobody decided that. The transport shape decided it — a tarball of whole files couples every
feature to every unrelated change in the same file.

### What is actually inside the bad file

Two sampled hunks say it exactly:

- **Their biggest addition (+79 lines):** the "Janus Key" — a real feature, living as inlined
  presentation logic inside a CLI command handler.
- **Our biggest deletion (−110 lines):** `cmd_orient` — our verb, inlined the same way, which they
  simply do not have.

`agent_cli.py` is not a door. It is a ~7,000-line file where both forks' features got glued, which is
why it diverges in 40 places. Neither `cmd_orient` nor the Janus Key has a home, so every sync must
detangle them, forever.

### The pattern already works where we used it, and fails where we didn't

- **Works:** `INSTRUMENTS` in `arsenal/web/piano.js` absorbed four light instruments from four
  different authors tonight with zero re-architecture — a module plus a registry line each.
  `state/coord/remote_bridge.json` is instance-local and gitignored *with a written rationale*: "the
  two sides' configs never need to agree, and MUST NOT be shared" (the t384 ceremony). That is
  Daniel's principle, already ratified, already applied — to exactly one subsystem.
- **Fails:** `scripts/checkers/check_wiring.py` hardcodes `ENTRY_POINTS` and `EXCEPTIONS` in shared
  Python. Those lists are *inherently* per-fork — Serge's entry points differ from ours, and their
  out-of-tree `$DSH_HOME` deployment is one of the documented blind spots that list exists to name.
  That file is guaranteed to conflict on every sync we ever do.

## The sketch to attack

**Core** — pure capability, identical across forks. Rule: never names a seat, a path, a port, or a
fork.

**Features** — portable and self-contained: one module + one registry entry + its own pins. Verb
bodies move out of `agent_cli.py`, which becomes a thin dispatcher over a registry. This converts the
worst file in the repo from "do not take" into "no collision", because files were free tonight.

**Local** — the half that has never had a home: entry points, exceptions and baselines, seat rosters,
ports, paths, peer names, secrets. Data rather than code, one directory, exportable and importable as
a bundle, so a fresh machine or a fork can take a known-good local profile instead of re-deriving it.

**The detector, which is the part I most want tested:** *if two forks must both edit the same line for
their own reasons, that line is in the wrong layer.* `ENTRY_POINTS` fails it. Inlined verb bodies fail
it. `INSTRUMENTS` passes it.

**Success condition:** a sync touches only Core and Features, and never needs to read Local.

**Migration is strangler, never big-bang:** (1) new features land in the new shape from today, which
costs nothing; (2) extract on contact — when a sync or a bug makes you open a verb body, move it out
*then*, so the detangling you would have done anyway becomes permanent instead of repeated; (3) move
the instance-local lists to data first, because they are small, mechanical, and conflict every time.

## What this is not

It is not a plan to refactor `agent_cli.py` in one pass. A 7,000-line file with 40 divergent hunks is
exactly the thing that should be strangled, not rewritten — and a big-bang rewrite would collide with
every in-flight lane in the house.

## The known unknowns, stated so nobody has to rediscover them

- We have not yet heard Serge's fleet's counter. This is bilateral: an exchange format only pays off
  if both sides adopt it.
- The house has never had a "local profile" artifact, so its boundary is genuinely undecided — the
  line between "instance config" and "a feature that happens to be ours" is the hard part.
- `.gitattributes` LF pinning is in flight in another lane tonight, and it interacts: normalising line
  endings is a precondition for any diff-based exchange.
