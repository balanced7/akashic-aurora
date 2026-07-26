# Docs map — what to read, and what's living vs. history

Status: current  (2026-07-09, P4: Living docs map)

The one-screen guide to the documentation. Two kinds of docs live here, and telling them apart is
the whole point (an old design note read as current truth is how a project stops being understandable):

- **LIVING docs** (`UPPERCASE.md`) — kept current; the map you trust *now*. Listed below.
- **Design & history** (`lowercase-*.md`, often dated) — point-in-time plans/research/decisions.
  Valuable for the *why*, NOT maintained as current. Read them as artifacts, findable by filename.

> **Convention:** if a doc must stay true, name it `UPPERCASE.md` and keep it in the living set. If it
> captures a moment (a plan, a research pass, a decision), give it a lowercase, ideally dated name and
> let it fossilize honestly. `check_comprehensibility.py` guards the living set.
> **Amendment (library law, 2026-07-21): the header beats the filename.** A doc's `Status:` line
> is the living-marker; UPPERCASE is the *recommended dress* for contracts, not the law (this is
> what keeps `method-baseline-2026-07.md` lawful). Filing + finding: [LIBRARY.md](LIBRARY.md).

---

## Start here (read order)
1. **[ARCHITECTURE.md](ARCHITECTURE.md)** — the whole system at subsystem altitude (the map).
2. **[LEXICON.md](LEXICON.md)** — the ubiquitous language (one term, one meaning).
3. **[PRINCIPLES.md](PRINCIPLES.md)** — *why* the software is shaped this way.
4. `py agent_cli.py boot claude` — the live "where are we right now" state.
5. **[ROADMAP.md](ROADMAP.md)** — the sequenced plan and what's next.

## The living docs (kept current)

**Comprehension — the mental model**
| Doc | What it is | Rot-guard |
|-----|-----------|-----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | the layer map, subsystem altitude | stable altitude + `check_comprehensibility.py` |
| [MODULE_INDEX.md](MODULE_INDEX.md) | every module's one-line job | auto-generated (`gen_arch_index.py`) |
| [MAP.md](MAP.md) | the master census matrix (module x pin/paper/flags + GAP queue) | auto-generated (`gen_master_map.py`) |
| [LIBRARY.md](LIBRARY.md) | where things live and why — types, header contract, four doors | header contract + guards 8–12 |
| [PHYSICS.md](PHYSICS.md) | the machinery's static bounds + config flags | auto-generated (`gen_physics_sheet.py`) |
| [DOORS.md](DOORS.md) | the agent-door I/O reference (CLI verbs + inputs) | auto-generated (`gen_doors.py`) |
| [PRIOR_ART.md](PRIOR_ART.md) | every subsystem beside what the field already built (GAP/DRIFT coverage) | auto-generated (`gen_prior_art_register.py`); entries authored in `data/prior-art/register.json` |
| [LEXICON.md](LEXICON.md) | the ubiquitous language | stable altitude |
| [PRINCIPLES.md](PRINCIPLES.md) | the earned working principles | stable; each names what would revise it |
| [JOURNEY.md](JOURNEY.md) | the story of how we got here | append-only narrative |
| [FOSSILS.md](FOSSILS.md) | abandoned decisions + what they taught | append-only |

**Plan & voice**
- [ROADMAP.md](ROADMAP.md) — the layered plan + sequenced next steps.
- [VOICE.md](VOICE.md) — the rules for anything the project says publicly.
- [FSQ.md](FSQ.md) — frequently anticipated skeptical questions (honest answers).

**Operations (how to run/fix it)**
- [DEPLOY.md](DEPLOY.md) · [SERVICES.md](SERVICES.md) · [GPU.md](GPU.md) ·
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md) · [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md)

**Living ledgers & constraints (maintained, current)**
- [LIVE_CONSTRAINTS.md](LIVE_CONSTRAINTS.md) — the break-you rules, rendered into every boot ·
  [WISHLIST.md](WISHLIST.md) — the standing ergonomics ledger · [PORTS.md](PORTS.md) — the port map ·
  [CONDUCT.md](CONDUCT.md) — the conductor's standing law (ten laws + activation map + fresh-boot bar).

**The contract (repo root)**
- [../README.md](../README.md) — what this is. [../AGENTS.md](../AGENTS.md) — the contract every agent honors.
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — how to change it. [../bootstrap.md](../bootstrap.md) — agent quick-start.

## Design & history (point-in-time, NOT maintained)
The dated docs capture plans, research, and decisions at a moment; they explain *why*, not *now*.
(Census: generated into SHELVES.md once `gen_library` lands — the hand counts of 2026-07-21 ran
~2× stale, so this file no longer counts by hand.)
Notable recent ones (2026-07):
- [agent-failure-modes-retrospective-2026-07.md](agent-failure-modes-retrospective-2026-07.md) +
  [-mitigation-roadmap-2026-07.md](agent-failure-modes-mitigation-roadmap-2026-07.md) — the reliability arc (L0–L4).
- [architecture-research-actor-ros-stigmergy-2026-07.md](architecture-research-actor-ros-stigmergy-2026-07.md) — the supervisor-tree / stigmergy research.
- [memory-recall-multiagent-design-2026-07.md](memory-recall-multiagent-design-2026-07.md) — the multi-agent recall assessment.

The rest (`*-plan.md`, `*-research.md`, `*-design.md`, `codex-*`, `bifrost-*`, `narrative-*`, …) are
historical design records — grep `docs/` by topic. If one becomes load-bearing-current, promote it to
an `UPPERCASE.md` living doc; otherwise let it stand as the dated artifact it is.

---
*Keep this list to the LIVING set (it changes rarely). Don't index every dated design doc here — that
would make this rot too. Last structural review: 2026-07-06 (replaced a 2026-04 fossil).*
