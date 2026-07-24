---
akashic_id: art_20260721_repo-organization-hygiene-opening-positi_b06cf7
akashic_sha: 542c6c2e2dae
status: draft
type: design
date: 2026-07-21
title: "Repo organization & hygiene — opening position (claude)"
gist: "# Repo organization & hygiene — opening position (claude) Date: 2026-07-21 · Round: opening → deepseek counter → kimi fresh-eyes (when seate"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260721_repo-organization-library-schema-counter_7b7d06
    rel: cites
  - target: art_20260721_kimi-fresh-eyes-brief-repo-filing-organi_11d418
    rel: cites
created: "2026-07-21T19:32:11"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260721_repo-organization-hygiene-opening-positi_b06cf7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Repo organization & hygiene — opening position (claude)

# Repo organization & hygiene — opening position (claude)

Date: 2026-07-21 · Round: opening → deepseek counter → kimi fresh-eyes (when seated) → reconcile → Daniel gates
Charter (Daniel, verbatim intent): "our github and files look a bit messy. Can you and the others
think about what kind of documents were created and what would be the best place to file and
organize them … lets do some house cleaning."

---

## Position zero — the law already exists; extend it, don't reinvent it

- **docs/INDEX.md two-kinds law**: `UPPERCASE.md` = living (kept current), `lowercase-dated.md` =
  point-in-time artifact, findable by filename, never mass-indexed.
- **docs/FOSSILS.md**: abandoned ≠ deleted; negative knowledge is curated, not swept.
- **research/README.md lifecycle**: `queue/ → drafts/ → reviewed/` (+ `briefs/` as charters-to-seats).
- **Boot doctrine**: research/** persists; explicit-paths mirror only; never sweep a sibling's lane.

**Therefore: NO mass moves of cited atoms.** Notes, lessons, ADRs, and boot pointers cite paths.
Moving tracked docs breaks the knowledge layer's citations — the same reason Aurora doesn't rewrite
atoms, it projects over them. Organize **forward** (new files get lawful homes), strengthen the
**projections** (INDEX/MAP re-render), and delete only true junk.

## Census — document families this run created (07-17 → 07-21)

| Family | Where now | Tracked? | Proposed home / action |
|---|---|---|---|
| Agent charters (6× `CHARTER.md`: claude, daniel, deepseek, gemini, kimi, sol) | `charters/<agent>/` | untracked | KEEP at root `charters/` — contract family, sibling of AGENTS.md. Commit AFTER Daniel ratifies (exemplar is marked pending ratification). Add to INDEX "contract" shelf. |
| Cross-harness skills (akashic-memory, plan-with-the-corpus, root-cause-before-fixes, verified-done) | `.agents/skills/` | untracked | Commit as the neutral, harness-agnostic skill home; harness-specific dirs copy/link from it. |
| Codex seat config (`config.toml`, `hooks.json`) | `.codex/` | untracked | Secrets-scan FIRST; if clean, commit (seat config-as-code, same family as `.claude/` = super-admin paths). |
| Co-design rounds (openings/counters/round-3s) | `research/drafts/` | **47 of 77 untracked** | Commit-by-name batch. Doctrine says research persists — this is the biggest silent-loss risk in the tree. |
| Frontier/fence reports | `research/reviewed/` | ~10 untracked | Commit-by-name. |
| Seat run-briefs (kimi builder/fresh-eyes briefs) | `research/briefs/` | mixed | Already canonical — keep. NOTE the name collision: agent CHARTER vs run "charter/brief" → needs a LEXICON ruling. |
| Freeplay outputs | `data/play/<agent>/{runs,out}/` | untracked | `runs/*` = runtime receipts → .gitignore. `out/*.md` = curate (keep-list per play, e.g. campfire). `data/play/test/` = delete (harness-test debris). |
| Probe tests (`test_mcp_deep_inspect1..6`, `test_mcp_inspect`, `test_env_check`, …) | `tests/` | untracked | Probes NEVER live in `tests/` — scratch/ or delete. Real pins (w09, t086-s6, t095-m0, ir4, census-timings, freeplay pins…) commit-by-name after the suite-baseline diff. |
| Local launchers (`launch_kimi_*.ps1`) | `scripts/local/` | untracked | Commit — they're the raw material for W08 launcher-helper. |
| Runlogs + shift-console logs | `research/` root | mixed | New `research/logs/` + gitignore `research/**/*.log`; move only after per-file grep-check for citations. |

## Hygiene debris (independent of filing)

1. **Mojibake, second bite — repaired today.** WISHLIST.md (72) + deepseek's walk-review (73+) +
   onboarding-counter (73+) restored to real UTF-8. History: 21d1193 repaired the same class 07-19
   ("PowerShell -replace on multibyte chars"); the night run's W33 flip (0537c48) re-introduced it.
   A lesson alone did not hold → fix at the DOOR: (a) force UTF-8 in the write door + the
   verbatim-persist pipe (both deepseek-report entry paths), (b) HARD GUARD — check_boundaries
   rule-8 or a pytest pin scanning tracked `*.md` for `â€ Ã— â† Â§` classes, (c) lesson filed
   (`mojibake_ps_replace_second_bite`).
2. **Stray dir `E:<mojibake>AI-Setup/`** (April, smart-quote path-join artifact; 2 tiny session
   jsonls inside). Delete after content peek; park in `_archive/` only if story-relevant.
3. **GitHub-visible root is mostly lawful.** Oddballs: `deepseek.cmd` → `scripts/` (grep refs
   first); `bootstrap.py/md` = the known stale-audit item (separate arc, don't fold here).
4. **docs/ count drift**: INDEX says ~55 dated docs; actual ≈85. Structural re-render of INDEX
   (a projection change, not moves). Candidate: auto-generate the dated-docs census like
   MODULE_INDEX/MAP so it can't rot again.

## Positions (counter these — each names its kill-test)

- **P1** No mass moves of cited atoms; projections organize. *Kill-test: name one cited path that must move anyway.*
- **P2** Research lifecycle enforced forward; root strays → subdirs after per-file grep-check.
- **P3** Batch commit-by-name of untracked research (full list at reconcile).
- **P4** `charters/` stands at root, committed post-ratification.
- **P5** `.agents/` + `.codex/` committed post secrets-scan. ← deepseek: your turf, counter hard.
- **P6** Play `runs/` gitignored; `out/` curated. ← deepseek: yours.
- **P7** Probes-out-of-tests rule; pins-only in `tests/`.
- **P8** UTF-8 forced at the write door + mojibake guard pin. ← deepseek: your door.
- **P9** New check_boundaries rules: 8 = mojibake scan, 9 = probes-in-tests, 10 = root-level new-entry allowlist.

## Open questions

- **Q1** "charter" ambiguity (agent CHARTER vs run brief) → LEXICON ruling.
- **Q2** Who owns the INDEX re-render — hand-curated or generated?
- **Q3** data/play retention (TTL? curate-at-wrap?).
- **Q4** .codex secrets posture before any commit.
- **Q5** Which research-root strays are cited anywhere (grep at move time, not assumed).

## Protocol

deepseek counters (hardest on P5/P6/P8, Q3/Q4) → file
`research/drafts/repo-organization-counter-deepseek-2026-07-21.md` + bus reply. kimi fresh-eyes via
`research/briefs/kimi-fresh-eyes-repo-filing-brief-2026-07-21.md` when seated. Reconcile →
`docs/repo-organization-plan-2026-07.md`. **Daniel gates: all deletions, the bulk research commit,
any move of a tracked path.**
