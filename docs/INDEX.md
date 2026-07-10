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

**The contract (repo root)**
- [../README.md](../README.md) — what this is. [../AGENTS.md](../AGENTS.md) — the contract every agent honors.
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — how to change it. [../bootstrap.md](../bootstrap.md) — agent quick-start.

## Design & history (point-in-time, NOT maintained)
~55 lowercase docs capture plans, research, and decisions at a moment. They explain *why*, not *now*.
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
