# Drill receipt — rewrite recovery (T410)

**Date:** 2026-09-26 · **Run by:** claude · **Slice:** T410 · **Commit under test:** `c0444229`, re-executed at `9269227d`
**Verdict:** PASS on both properties. Executed, not reasoned about.

House law: a recovery path without an executed drill receipt is presumed broken. This slice
claims two things, and each is drilled where it can actually fail.

## Drill A — do the maps travel?

The property the whole slice exists for. Before tonight, 877 of the 1,436 commit SHAs our
tracked corpus cites resolved on **this machine only**, pinned by `refs/heads/pre-rewrite-backup`
and `refs/original/refs/heads/master`. A clone is the one instrument that structurally cannot
see those refs, so it is the only honest test.

```
git clone --no-hardlinks --single-branch E:\AI-Setup <temp>
```

| observation | result |
|---|---|
| maps present in the clone | 4 (`2026-07-23` 1,127 · `2026-08-12` 1,980 · `2026-09-26-cited-gap` 1 · `2026-09-26-unmapped-residue` 116) |
| `py agent_cli.py sha 0007d13d` **inside the clone** | `TRANSLATED bd12017512ec [2026-08-12]` |
| clone's pre-rewrite refs | **none** — checked explicitly, or the test proves nothing |

The clone resolved a pre-rewrite citation with no local refs to lean on. That is the whole
claim, demonstrated on the artifact a stranger would receive rather than on my working tree.

## Drill B — does capture work on a real rewrite?

`git filter-repo` present. A throwaway repo, four commits, a real purge of `secret.txt`:

| step | result |
|---|---|
| pre-rewrite SHA | `510f9c1d4a94` |
| post-rewrite SHA | `3c6817e30613` (changed: yes) |
| `rewrite_recover.py capture --label drill` | captured 4 remaps, 0 dropped |
| resolve `510f9c1d…` through the captured map | `TRANSLATED 3c6817e30613 [2026-09-26-drill]` |

**Honest bound:** the repo is synthetic, so this drills the *mechanism* — filter-repo runs,
capture finds and archives the map, the resolver reads it — not our scale. Drill A carries the
scale claim on the real corpus.

## What is NOT drilled

- **Reconstruction** was validated against ground truth instead (1,765 recorded rows from the
  08-12 map: 100% agreement, 0 wrong, 2.3% declined). The 07-23 map contributes nothing
  testable because its outputs were themselves rewritten later, so that validation covers one
  rewrite, not both. Stated rather than averaged away.
- **The 577-commit rewrite still queued.** Run `census` before it and after it; `capture`
  immediately, before any second filter-repo run overwrites `.git/filter-repo/commit-map`.
  That file is how the 07-23 map came within one command of being lost while supplying most of
  our recovery coverage.

## Reproduce

```bash
py scripts/checkers/check_rewrite_maps.py --gate
```

Gate green at the time of writing: 0 stranded citations, 8 accepted-with-reasons.

---

## Re-executed at `9269227d`, after two rounds of review fixes

The resolver changed substantially between the first run and this one -- endpoint ranking
replaced the greedy walk, a per-path DFS replaced the global `seen` set, `UNVERIFIED` was added,
and the reconstructor now requires structural corroboration. A receipt earned against different
code is not a receipt, so both drills were run again.

| drill | result |
|---|---|
| A — fresh clone, no pre-rewrite refs, resolves `0007d13d` | **PASS** |
| B — real `git filter-repo`, captured, resolved (`fec012b8` -> `1453a5d1`) | **PASS** |

25 pins green. `check_rewrite_maps.py --gate` green: 0 stranded, 8 accepted-with-reasons, and 2
cited commits reported as awaiting a push rather than counted as lost history.
