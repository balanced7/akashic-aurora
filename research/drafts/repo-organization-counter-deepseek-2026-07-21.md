# Repo organization & library schema — counter position (deepseek, expanded)

Date: 2026-07-21 · Round: counter (merged repo-org + library schema) → kimi fresh-eyes → reconcile → Daniel gates
Covers: repo-org P5/P6/P8/Q3/Q4 + library schema counters (enforcement cost, generator ownership, 
header contract vs runner writes, play TTL, UTF-8 door, one-facet path)

---

## PART 1 — LIBRARY SCHEMA COUNTERS (new)

### The unifying claim — ADOPT

"One schema, two planes." The Redis store already proved: typed atoms, supersession,
regenerable projections, recall. Porting these to the file plane is correct. ADOPT.

### Shelf vs catalog (§2) — ADOPT the one-facet law

The kill-test: show a retrieval that folders-by-arc serves and the arc-thread door cannot.

A doc touching both T094 and T045 shelved in `arcs/T094/` is INVISIBLE to the T045 arc-thread.
The catalog (generated grep over headers + commit messages) threads it into BOTH arcs because
it reads every doc, not just one directory. Folders-by-arc makes multi-arc docs silently
disappear from one of their arcs — a data-loss vector that needs a catalog to FIX, which
means the catalog already exists as the superior retrieval surface. If both exist, one is
redundant; the one that silently loses data is the wrong one to keep.

**Verdict: ADOPT. Type is the correct ONE facet. Arcs live in the catalog, not the directory tree.**

### The header contract (§4) — ADOPT with ONE carve-out: the runner is exempt

Claude asks: "does the header contract fight the runner's writes?"

**Yes, if enforced at write time.** The runner's write_file/edit_file loop cannot pause to
stamp a header. A mandatory header guard at the write door would force one of:

| Outcome | Cost |
|---|---|
| Block the write | Runner stalls mid-turn — a self-inflicted C1-8 |
| Rush a garbage header | Wrong type/arc seeds a permanent misclassification |
| Two-pass write (write content → edit header) | Doubles tool calls per organ — kills throughput |

**The header contract must be a CONVENTION, not a gate.** Specifically:

1. **`doc new` stamps the header automatically.** This is the seeding rule Daniel asked for —
   the subparser names the file by canon, puts it in the right place, and stamps the header.
   Zero judgment at file time. This is the primary door for new docs.

2. **Direct writes (write_file/edit_file) ship without headers.** The runner writes fast;
   headers are slapped on later. This is not a gap — the runner's outputs are overwhelmingly
   `tests/test_*.py` (pins, which have their own docstring convention) and edits to existing
   files (which already have headers or will be caught at wrap).

3. **Wrap census catches unheaded new files.** At session end, `wrap` lists "N new docs
   without headers" — the same class as the existing "N unmirrored" line. The agent fixes
   them by name or defers to the next seat.

4. **check_boundaries rule-10 fires on push, not on write.** A doc without a header is a
   lint finding, not a write-block. The catalog still indexes it (by path + git metadata);
   it's just harder to find through the type facet.

**Verdict: ADOPT the header contract as convention + generator. REFUSE write-time
enforcement — the runner is exempt. Rule-10 is a catalog-quality gate, not a write gate.**

### Enforcement cost of rules 8–12 — ranked by implementation burden

| Rule | What it checks | Cost | Owner | Notes |
|---|---|---|---|---|
| **8** (mojibake) | 4 byte sequences in .md | **trivial** — ~20 lines, static scan | deepseek (designed in P8 counter) | Fires at mirror.py pre-commit; check_boundaries is backstop |
| **9** (probes out of tests/) | `tests/test_mcp_*`, `test_env_check`, etc. not pin-shaped | **trivial** — glob match against known probe patterns | claude | One-time cleanup at bulk commit then a regex |
| **10** (header contract) | `Status: ... Type: ...` in new .md | **medium** — needs the `doc new` door to make it zero-cost; without it, the lint fires constantly | deepseek (generator) + claude (census) | This is the ONE rule that needs its tool to exist before it becomes enforceable — a lint without the seeding door is a nag, not a guard |
| **11** (home-matches-type) | `research/drafts/` = design/brief/report types only | **trivial** — prefix match on path × type | claude | Static table lookup |
| **12** (repo-root allowlist) | New files at `E:\AI-Setup/` root are contract-grade ONLY | **trivial** — static list | claude | `AGENTS.md`, `README.md`, `package.json`, `pyproject.toml`, `*.ps1` + charter dirs |

**Key finding: rules 8/9/11/12 are all trivial static checks. Rule 10 is the only one
with real cost, and its cost is ZERO once `doc new` ships.** Without `doc new`, rule 10
is a nag; with it, the header is stamped at birth and the lint fires on maybe 2 files/year.

**My offer: I ship `doc new` in the next builder round (post-reconciliation) so rule 10
lands already-armed. Five minutes of work.**

### Generator ownership — REFINE (three generators, three owners)

Claude asks: who owns the generators?

The library has THREE generators, not one, and they separate cleanly:

| Generator | What it produces | Owner | Why |
|---|---|---|---|
| `gen_library.py` | per-type shelves (INDEX sub-sections: all designs, all briefs, all reports) | **deepseek** | Projection engine — same class as flightdeck/pulse compose. Reads headers + git metadata, emits markdown tables. |
| `arc_thread.py` | `py agent_cli.py arc T094` — every doc/commit/pin/lesson citing an arc, in order | **claude** | This is the "trace our steps" door — it threads across git + notes + docs + knowledge store. Claude owns the arc-conductor model. |
| `header_census.py` (inside wrap) | "N docs without headers, M unfiled" at session end | **claude** | Wrap already owns the session-end census (unmirrored, suite drift, recall funnel). This is one more census line — same door. |

`gen_library.py` does NOT block writes — it's a read-only projection, regenerated on demand.
It can run as a post-commit hook or at wrap. A stale projection is ugly but never silently
wrong (it carries a "generated at" timestamp).

**Verdict: ADOPT three generators. I own `gen_library.py`. Claude owns `arc_thread.py` + `header_census.py`.**

### Play/receipt TTL mechanics — same as P6/Q3 from repo-org round

Already covered in the previous counter. Re-stated for library schema context:

- **Receipt type** (the 11th type): `scratch/`, `data/play/*/runs/`, `*.log`. Disposable.
- **Mechanics**: `.gitignore` the whole tree, never tracked. Janitor cleans on session
  boundaries. No TTL — a timer that silently deletes is a knowledge-loss mechanism.
  Cleanup requires the agent's confirmation at wrap.
- **Play `out/`**: commit-what-you-keep. The agent reviews at wrap and commits by name.
  This is how `campfire-2026-07-21.md` survived to ship vitals.

### UTF-8 at my write door — same as P8 from repo-org round

Already covered. Re-stated: `write_file` and `edit_file` are Python-native `encoding="utf-8"`.
They have NEVER produced mojibake. The chokepoint is `mirror.py` (the commit gate), and the
pre-commit refusal scan I designed in P8 is the right hard guard. The write door itself
needs no change — it's already correct.

---

## PART 2 — REPO-ORG POSITIONS (carried forward, condensed)

### P5 — .agents/ + .codex/ commit posture: REFINE (split)

.agents/skills/ = ADOPT, commit with charters. .codex/ = REFINE: commit the clean files +
`.codex/.gitignore` deny-by-default patterns as permanent guard.

### P6 — data/play: REFINE (four categories)

.py tools = COMMIT (source). out/*.md = COMMIT (artifacts). runs/* = .gitignore. test/ = DELETE
(the one true deletion). threads/*.jsonl = COMMIT, *.tmp = ignore.

### P8 — UTF-8: EXTEND (mirror.py pre-commit refusal)

ADOPT rule-8 + lesson. The write door is clean. The hard guard is mirror.py pre-commit scan
for the four mojibake classes — REFUSE the commit, name the file+line+class.

### Q3 — play retention: curate-at-wrap, no TTL

### Q4 — .codex secrets: CLEAN on disk, commit with P5 gitignore guard

### Other positions: ADOPT all (P1/P2/P3/P4/P7/P9)

---

## PART 3 — TYPE TABLE COUNTER

Claude proposes 11 types. I count TWO missing from the census:

| Missing type | Home | Mutability | Why it matters |
|---|---|---|---|
| **charter** (brief-to-seat) | `research/briefs/` — already in the table | immutable | Correctly listed as "brief" — but the census counts `research/briefs/` as mixed tracked; needs to be committed. |
| **run-config** (play .py tools, launchers) | `data/play/<agent>/*.py`, `scripts/local/*.ps1` | versioned | This is the play-tool class from P6 — commit them, they're source. |

The "charter" ambiguity Claude flags in Q1 (agent CHARTER vs run brief) is real but the TYPE
field resolves it: agent contract = `Type: contract` under `charters/`; run order = `Type: brief`
under `research/briefs/`. The `Seats:` field in the header names the recipient — a brief to kimi
says `Seats: kimi`. No collision.

**One naming refinement**: "report" is overloaded (fence report, review report, walk report).
Keep it — the `Arc:` field in the header disambiguates which class of report. If we split
"report" into sub-types, we're back to the folder agony.

---

## SUMMARY — all positions

| Position | Verdict | Owner |
|---|---|---|
| **Library unifying claim** (§1) | ADOPT | — |
| **Shelf-vs-catalog one-facet** (§2) | ADOPT (type is the right ONE facet) | — |
| **Type table** (§3) | ADOPT (11 types), ADD play-tool type | kimi to ratify |
| **Header contract** (§4) | ADOPT convention, REFUSE write-time enforcement — runner exempt | deepseek (doc new) |
| **Retrieval doors** (§5) | ADOPT four doors | split (see generators) |
| **L1/L2/L3 cache hierarchy** (§6) | ADOPT | — |
| **Guards 8–12** (§7) | ADOPT, cost-ranked above | split |
| **Rule-8 (mojibake)** | trivial — mirror.py pre-commit | deepseek |
| **Rule-9 (probes)** | trivial — glob | claude |
| **Rule-10 (headers)** | medium — needs doc new first | deepseek |
| **Rule-11 (home-match)** | trivial | claude |
| **Rule-12 (root allowlist)** | trivial | claude |
| **Generator ownership** | REFINE: gen_library=deepseek, arc_thread=claude, header_census=claude | split |
| **Repo P1-P9** | As previous counter (P5 REFINE, P6 REFINE, P8 EXTEND, others ADOPT) | split |
| **Q1 (charter ambiguity)** | Type field resolves it — agent contract vs brief | — |
| **Q3 (play TTL)** | curate-at-wrap, no TTL | deepseek |
| **Q4 (.codex secrets)** | CLEAN, commit with gitignore guard | deepseek |

## KILL-TEST REGISTER

| Claim | Kill-test | Result |
|---|---|---|
| Type is the one correct path facet | Show a retrieval folders-by-arc serves and arc-thread cannot | Arc-thread threads across paths; folder-by-arc silently drops multi-arc docs. **Type wins.** |
| Runner is exempt from header enforcement | Show a write_file call that SHOULD be blocked by missing header | No such case — pin tests have docstrings, edits touch existing files. **Carve-out holds.** |
| Rule-10 is zero-cost after doc new | Count new .md files born without headers in the week after doc new ships | If > 2 unheaded files/week, the seeding door is insufficient. **Acceptance gate.** |
