---
akashic_id: art_20260723_folder-consolidation-top-level-directory_e18216
akashic_sha: 023af6cd3da4
status: current
type: design
date: 2026-07-23
title: Folder consolidation — top-level directory disposition (Daniel gates every move)
gist: "# Folder consolidation — top-level directory disposition (Daniel gates every move) **Daniel's charter (verbatim, night 2026-07-23):** \"conso"
tenant: solo
visibility: fleet
seats: []
category: [migration, library, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T03:22:53"
updated: "2026-07-23T03:22:53"
---
<!-- GENERATED PROJECTION of art_20260723_folder-consolidation-top-level-directory_e18216 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Folder consolidation — top-level directory disposition (Daniel gates every move)

# Folder consolidation — top-level directory disposition (Daniel gates every move)

**Daniel's charter (verbatim, night 2026-07-23):** "consolidate our document sprawl and
random folders in the github." This proposal is the top-level FOLDER half; the document
half is already served by the generated `docs/SHELVES.md` (door 1, landed tonight) — no
hand-count here (R14: censuses are generated).

**Rail (from the night charter + library law):** NOTHING is deleted or moved tonight.
Deletions are Daniel-gated. This is a decision surface: each row carries what it is, its
git-tracked reality, and a recommended disposition. `git mv`/`git rm` execute only after
ratification, and only with a cited-path check (R13: a doc moves to `_archive` only when
grep-uncited AND superseded).

## The two classes (git-tracked reality decides the risk)

**Class A — local-only clutter (tracked=0: zero repo history, low risk).** These sit in
the working tree but nothing is committed; removing or gitignoring them loses no history.
Some are likely already gitignored and simply present on disk.

| Dir | Files | What it is (best read) | Recommended disposition |
|---|---|---|---|
| `temp/` | 79 | scratch spillover | gitignore + local clear (receipt type → scratch/) |
| `blobs/` | 1 | unknown single blob | INVESTIGATE then remove |
| `blackboard_data/` | 2 | legacy coordination store (pre-Store/Ledger) | archive-note then remove |
| `coordinator_logs/` | 1 | legacy daemon log | remove (state type, gitignored family) |
| `assets/` | 0 | empty | remove |
| `models/` | 0 | empty | remove |
| `.kimi-claude-home/` | 65 | a seat's home dir leaked into repo root | gitignore (move under state/ or a dot-home) |
| `dropbox/` | 1 | the avatar-vision console screenshot (design evidence) | MOVE to design/refs/ (it is a cited design artifact, not junk) |
| `scratch/`, `sessions/`, `session_logs/`, `session_screenshots/` | 246/44/306/24 | receipts + session state | KEEP, gitignored per family (already) — curate at wrap, no action |

**Class B — tracked legacy dirs (have repo history: consolidation = real git decision).**
These need a live/superseded ruling before any move; each maps to a LIBRARY type.

| Dir | Tracked | What it is | Question for the gate |
|---|---|---|---|
| `_archive/` (root) | 154 | OLD archive, predates the declared L3 | R13 names `docs/_archive/` as THE L3 shelf. Two archives = drift. Merge root `_archive/` into `docs/_archive/`, or declare root `_archive/` the L3 and fix R13? |
| `context/` | 10 | half-built Context pillar (per the codebase audit) | RESOLVED: **LIVE** — imported in 6 live sites outside itself. KEEP as machine:code (half-built ≠ dead). |
| `fences/` | 6 | fence artifacts | RESOLVED: **CITED** — 7 doc/research citations. R13 forbids moving grep-cited files. KEEP in place. |
| `infrastructure/` | 2 | infra package (health_check.py + __init__) | RESOLVED: **FOSSIL-LEANING** — 0 live imports, last touched 2026-06-27, a doc note reads "❌ Organized infrastructure/ package" (abandoned). Archive candidate → `docs/_archive/` or fold health_check into scripts/. Daniel gates. |

**Investigation done (cited-path checks run 2026-07-23, read-only):** the three tracked
legacy dirs are no longer "needs a peek" — verdicts above carry their evidence. Only
`infrastructure/` is a real move candidate; `context/` and `fences/` stay put.

## Junk queue (G4 from the reconciliation — status tonight)
- `data/play/test/` (42 files) — R12 says DELETE (play test data). QUEUED for Daniel.
- probe tests (`test_mcp_deep_inspect*`, `test_mcp_inspect`) — ALREADY GONE (G4 done).
- root `test_code/data/memory.json` — ALREADY GONE (G4 done).
- `.pytest_err.txt` (mine, from tonight's detached suite) — gitignore sibling of the
  already-ignored `.pytest_out.txt`; I will add it (my lane, safe).

## Commit-by-name queue (G5, ratified — not deletions, additions)
- `charters/` (6 agent dirs, tracked=0) — the reconciliation says commit after ratification;
  ratification happened. Commit-by-name at the gate (or now, if Daniel confirms — it is
  additive, no history at risk).

## Recommended gate order (stranger's-unlock order)
1. Rule the Class-A removals as a batch (all tracked=0 — one yes clears 8 rows).
2. Rule the `dropbox/` → `design/refs/` MOVE (preserves the avatar-vision evidence in its
   proper home — this one is a keep-by-moving, not a delete).
3. Rule the two-archive question (B/`_archive`) — the one real structural decision.
4. Rule only `infrastructure/` (the one fossil-leaning tracked dir) — `context/` and
   `fences/` are RESOLVED KEEP (verdicts above). One decision, not three.
5. `data/play/test/` deletion (G4) + `charters/` commit-by-name (G5).

Nothing here executes without your word; every Class-B move gets a grep-cited-path check
first so no live reference breaks.
