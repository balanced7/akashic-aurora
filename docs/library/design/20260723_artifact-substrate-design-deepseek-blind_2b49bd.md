---
akashic_id: art_20260723_artifact-substrate-design-deepseek-blind_2b49bd
akashic_sha: a8181c1c2941
status: draft
type: design
date: 2026-07-23
title: Artifact-Substrate Design — deepseek blind half — 2026-07-23
gist: "Brief: research/briefs/claude-artifact-substrate-round-2026-07-23.md (bus, not file) Context: I built D2 (gen_library), D1 (doc new), and th"
tenant: solo
visibility: fleet
seats: []
category: [substrate, library, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T09:16:19"
updated: "2026-07-23T09:16:19"
---
<!-- GENERATED PROJECTION of art_20260723_artifact-substrate-design-deepseek-blind_2b49bd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Artifact-Substrate Design — deepseek blind half — 2026-07-23

Brief: research/briefs/claude-artifact-substrate-round-2026-07-23.md (bus, not file)
Context: I built D2 (gen_library), D1 (doc new), and the header parser. I know what
         already works and what doesn't.

## Q1 · SUBSTRATE: one JSONL file per type, git-tracked, append-only

```
store/docs/
  briefs.jsonl       # one line = one brief version
  reports.jsonl      # one line = one report version
  designs.jsonl      # designs, charters, plans
  contracts.jsonl    # LIBRARY, LEXICON, etc.
  chronicles.jsonl   # session reflections, night plans
  ledgers.jsonl      # failure-ledger, WISHLIST
  rulings.jsonl      # Daniel's rulings
  maps.jsonl         # INDEX, MAP, SHELVES (generated — stored as provenance)
```

**Why this over 890 .md files, a database, or Redis-only:**

- **JSONL is git-tracked.** Every version is a line in a file that git versions for free. Crash recovery = `git checkout`. Off-machine backup = `git push`. The same durability story as today, but structured.
- **Append-only = no merge conflicts.** New documents append one line; supersession appends a new line. Two agents writing simultaneously to the same type just get two lines in either order — the store resolves by timestamp. Git merges are trivial (adjacent-line appends).
- **Human-readable.** `cat store/docs/briefs.jsonl | jq .type` still works. Grep still works. GitHub still renders JSONL as text with line-by-line diffs.
- **The header contract IS the schema.** Every line carries the same fields gen_library already parses: `id`, `type`, `status`, `arc`, `seats`, `date`, `title`, `heading`, `body`, `superseded_by`, `created`, `updated`. Zero new concepts.
- **The migration preserves content verbatim.** Existing .md body text becomes `body` — full-fidelity, byte-for-byte. The `research-full-fidelity` law is honored by construction: the .md body IS the stored record. Nothing is summarized or transformed.
- **Daniel's surface needs an index, not raw lines.** gen_library already generates that. The JSONL is the durable record; the generated maps are the reading surface. Same split as today — just the underlying storage is structured lines instead of loose files.

**Durability story, specific:**

- Normal: `store/docs/*.jsonl` committed to git alongside code. Every `doc new` appends + auto-mirrors.
- Crash mid-write: append is a single `write()` call to a local file. OS guarantees atomic append for writes under PIPE_BUF on POSIX; on Windows, our pattern is write-to-temp + os.replace (the mirror.py pattern).
- Redis down: JSONL is local. No network dependency for the knowledge substrate.
- Full machine loss: git clone → all docs restored. Same as today.

**Why not Redis-only:** Redis is the live bus, not the durable record. The File fallback already proves the fleet doesn't trust Redis alone for knowledge. Making docs Redis-primary would REPLACE git's off-machine durability with Redis snapshots — strictly worse for the thing Daniel asked for.

**Why not a SQLite/store database:** The fleet already has a store. Adding a second store for docs creates a second durability path with its own backup story. The existing store's File fallback IS the JSONL pattern — I'm just making it the PRIMARY path for docs rather than a fallback.

## Q2 · GIT RESIDUE: ~30 crown files + generated maps + store/docs/

What stays as real files:

| What | Why |
|------|-----|
| `README.md`, `AGENTS.md`, `CONDUCT.md`, `CONTRIBUTING.md` | Repo face — must render on GitHub landing |
| `docs/ARCHITECTURE.md`, `docs/PRINCIPLES.md`, `docs/LIBRARY.md`, `docs/LEXICON.md`, `docs/PHYSICS.md`, `docs/VOICE.md` | Crown contracts — the fleet's constitution. Must be openable at a URL |
| `docs/LIVE_CONSTRAINTS.md`, `docs/DOORS.md`, `docs/method-baseline-2026-07.md` | Standing rules that code enforces. Must live beside code |
| `docs/INDEX.md`, `docs/MAP.md`, `docs/MODULE_INDEX.md`, `docs/SHELVES.md`, `docs/ARCS.md`, `docs/DOORS.md` | Generated maps — rebuilt by gen_library, committed as navigation surface |
| `docs/SERVICES.md`, `docs/DEPLOY.md`, `docs/TROUBLESHOOTING.md` | Operational docs needed at startup/bootstrap |
| `docs/WISHLIST.md`, `docs/failure-ledger-2026-07.md` | Living ledgers — mutate in place (append lines), NOT append-only atoms |
| `chronicles/JOURNEY.md` | The hand-curated story Daniel reads |
| `research/README.md` | Zone index (generated by gen_library) |
| `store/docs/*.jsonl` | THE durable record of all other artifacts |
| `charters/*/CHARTER.md` | Per-seat standing contracts (or these migrate too — Daniel's call) |

Everything else (~860 files): migrated to store/docs/*.jsonl, then git-rm'd.

**Total file count on GitHub:** drops from ~900 to ~50 in docs/+research/+chronicles/. The portfolio face goes from "unreadable chaos" to "code + constitution + maps."

## Q3 · BIRTH: `doc new` writes to the store, pre-commit guards the rest

**Write door (what agents use):**

`py agent_cli.py doc new --type brief --title "ops-ask" --arc fleet --seats claude --body "..." --body-file path.md`

- Same verb as today (D1). Backend changes from file-write to store-append.
- Without `--body` or `--body-file`: opens the agent's editor (same as `git commit`). For MCP agents: `--body-file` carries the full text.
- Auto-stamps: `id` (uuid), `type` (from LIBRARY canon), `status: current`, `arc`, `seats`, `date`, `heading` (first `#` line), `created`, `updated`.
- Output: `[doc] stored doc:abc123def (brief, arc: fleet)`
- The ID is the stable citation: `doc:abc123def`.

**Guard against naked .md creation:**

mirror.py pre-commit hook (the existing rule-8 mojibake guard mechanism) gains a rule:
```
No new .md files in docs/, research/, chronicles/, charters/ unless:
  (a) path starts with docs/store/ (the JSONL files themselves)
  (b) path is in ALLOWLIST (the ~30 crown files + generated maps)
  (c) path ends with README.md (generated by gen_library)
```
A new .md outside the allowlist → REFUSED with teaching text: "use `py agent_cli.py doc new` instead."

This is the mint-door genus: the guard lives at the commit boundary, same as rule-8. Defeatable with `--no-verify`, but visible in review and the doc census catches stragglers at wrap time. Honor system with mechanical backstop — same pattern as every other rule we enforce.

## Q4 · READING: `doc` verb + `gen_library` maps + optional console pane

**CLI (Daniel's open/search/rule surface):**

```
py agent_cli.py doc doc:abc123def              # read one
py agent_cli.py doc doc:abc123def --status superseded  # rule: stamp status
py agent_cli.py doc --search "artifact subst"   # full-text search
py agent_cli.py doc --list --type brief         # list by type
py agent_cli.py doc --list --arc fleet          # list by arc
py agent_cli.py doc --list --status current      # list by status
py agent_cli.py doc --list --date 2026-07-23    # list by date
py agent_cli.py doc --resolve docs/LIBRARY.md   # old path → new ID
py agent_cli.py doc doc:abc123def --versions     # version history
```

**Generated maps (always up to date):**
- `docs/SHELVES.md` — per-type (already generated, now draws from store)
- `docs/ARCS.md` — per-arc (already committed, now draws from store)
- Zone READMEs — per-folder projectors (paused per Daniel's altitude-raise)

**Optional console pane (project, not prerequisite):**
The :8787 console gains a "Docs" pane — search bar + filtered table, same data source as the CLI. This is a PROJECT, not a dependency. The CLI works day one.

## Q5 · CITATIONS: doc: prefix + migration table + resolver

**Stable ID format:** `doc:<uuid_short>` — 12-char hex, globally unique, never re-used. A superseded document keeps its ID forever; the successor gets a new ID and references the old one via `superseded_by`.

**Migration table:** committed as `store/docs/migration.json` — one JSON object mapping old paths to new IDs:
```json
{"docs/failure-ledger-2026-07.md": "doc:abc123def456", ...}
```
Also committed as a Markdown table in `docs/CITATION_MAP.md` so it's human-browsable on GitHub.

**Resolver:** `py agent_cli.py doc --resolve <path>` returns the ID. The `doc` verb accepts both IDs and old paths transparently: `py agent_cli.py doc docs/failure-ledger-2026-07.md` works during the migration window.

**What happens to existing path-citations:** nothing breaks during migration. The resolver handles the translation. After migration, `git grep "docs/old-path.md"` still finds the citation; the recommended format shifts to `doc:abc123` over time. The citation map is permanent — it's the one mapping we NEVER delete.

**Recall ingestion:** the recall engine already ingests lessons by source pointer. The header contract on every doc line makes docs first-class recall citizens (the standing plan). `gen_library` feeding the same fields the store already holds means recall gains document search for free — it's the same data, indexed once.

## Q6 · MIGRATION: three Daniel-gated phases

**Phase 1 — IMPORT (Daniel gate: go/no-go on count + spot-check):**
1. `py scripts/migrate_docs.py --dry-run` — walks the corpus via gen_library, extracts headers + bodies, reports: "860 files → 860 atoms in 8 JSONL files. 12 unparseable, 3 unreadable."
2. Daniel reviews the dry-run report. If satisfied: `py scripts/migrate_docs.py --import`.
3. Import writes `store/docs/*.jsonl` + `store/docs/migration.json`.
4. Verification: `py agent_cli.py doc --list` shows count matches. `py agent_cli.py doc doc:abc123` on a random sample returns the original body verbatim.
5. Commit `store/docs/*.jsonl` + `store/docs/migration.json` to git.

**Phase 2 — RESOLVE (Daniel gate: verify citations work):**
1. `py agent_cli.py doc --resolve docs/ARCHITECTURE.md` returns its new ID.
2. Search all store-side citations (lessons, notes, handoffs) for old paths → patch to new IDs. The migration table drives this.
3. `recall-counters` cross-read confirms zero broken store-side citations.
4. Commit citation patches.

**Phase 3 — DELETE (Daniel gate: the big rm):**
1. `git rm` all migrated files except the ~30 crown files. One commit.
2. The migration table stays committed forever — anyone with an old path can resolve it.
3. `docs/CITATION_MAP.md` is the permanent human-readable map.

**Verification at each phase:** count-match (gen_library count vs store count), body-integrity (random sample round-trips), citation-liveness (resolve every old path in the migration table returns a valid ID that opens).

## Q7 · PUBLIC FACE: code + constitution + maps

GitHub becomes:
```
E:\AI-Setup/
  README.md
  AGENTS.md
  core/  agent/  scripts/  ...            # code (unchanged)
  docs/
    ARCHITECTURE.md  PRINCIPLES.md  ...     # ~15 crown contracts
    INDEX.md  MAP.md  SHELVES.md  ARCS.md  # generated maps
    WISHLIST.md  failure-ledger-*.md        # living ledgers
  store/
    docs/
      briefs.jsonl  reports.jsonl  ...      # ~8 typed JSONL files
      migration.json  CITATION_MAP.md
```

The portfolio reads: "Clean architecture + living contracts + generated navigation + a structured document store." The 890 loose files are gone. The value is preserved in the JSONL store. Daniel's "openable and searchable" requirement is met by `doc --search` + the generated maps on GitHub + the JSONL files which ARE openable (text, line-by-line).

## Q8 · SELF-ATTACK — what my design makes worse and how it mitigates

**Merge conflicts on JSONL files are rarer than .md file conflicts, but when they happen they're opaque.** Two agents append to the same JSONL → git merge succeeds trivially (adjacent-line append). But if two agents SUPERSEDE the same document, the JSONL now has two lines claiming `status: current` for the same arc — the store resolves by timestamp, but the file has both. Mitigation: `gen_library` detects duplicate-current-status and flags it as a DRIFT row. Cleanup: `doc --resolve-duplicates` interactively picks the winner.

**Binary-diff opacity: git log stops being useful for individual document history.** Today `git log -- docs/failure-ledger.md` shows every edit. Post-migration, that document is one line in `store/docs/ledgers.jsonl` — `git log` shows when the JSONL file changed, not when that specific document changed. Mitigation: `py agent_cli.py doc doc:abc --versions` reads the JSONL's full history for that ID. The store's append-only nature means no version is ever overwritten — `--versions` returns every line with that ID, in append order, which IS the document's history.

**Search staleness: grep over the repo no longer finds migrated documents.** Today `grep -r "C6-7" docs/` finds everything. Post-migration, only the ~30 crown files + JSONL + maps are grep-able. Mitigation: `py agent_cli.py doc --search "C6-7"` searches the store (full-text over JSONL body fields). This is DIFFERENT from grep — it's a dedicated command, not a Unix tool. Acceptable trade: the store becomes the SEARCH surface, and `grep` still works on the code + crown docs.

**The JSONL files grow unboundedly.** Every supersession appends a line. A document with 20 versions = 20 lines. Over a year, briefs.jsonl might hit 10,000 lines (10x the current corpus). Mitigation: a periodic compaction pass (yearly? Daniel-gated) that collapses superseded lines into a `versions` array on the current line. Not v1. The growth rate is ~15 lines/day at current pace — 5,500/year. A 10,000-line JSONL file is ~2MB. GitHub renders it fine. Solve at 50,000 lines.

**Door bypass: agents still write .md files by hand.** The pre-commit guard catches them. But `git commit --no-verify` bypasses it. Mitigation: the wrap census (existing pattern) catches straggler .md files created outside the door. Daniel sees them at the gate. The guard is mechanical (pre-commit), audited (wrap census), and human-gated (Daniel). Same pattern as rule-8 mojibake — the hook catches 99%, the census catches the rest.

**The migration scripts are one-time code — they carry their own correctness risk.** A bug in `migrate_docs.py` that silently truncates body text would corrupt the stored record. Mitigation: Phase 1 dry-run prints the exact body lengths and first/last 80 chars of every document. Daniel spot-checks 5-10 random IDs before approving. The verification pass (`doc` on random samples) catches truncation. The script is committed and reviewed before Daniel gates Phase 1 — it never runs unreviewed.

**Rulings need stronger preservation than append-only lines.** A Daniel ruling stamped `Status: current` that is later superseded needs to STAY readable — the `--versions` path returns all lines. But if someone accidentally appends a malformed line, the JSONL is corrupted for that ID. Mitigation: `doc new` validates the JSON structure before appending (a `json.loads()` on the new line). Failed validation → REFUSED, the line is never written. The store validates; the door is the gate.
