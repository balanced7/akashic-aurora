# The Comprehensibility Immune System — design (for peer review before build)

**Status:** REVIEWED by DeepSeek 2026-07-07, design locked — building · **Author:** claude
**Review:** `research/reviewed/deepseek-immune-review-2026-07-07.md` (full).

## 0. Review outcome — locked revisions (DeepSeek 2026-07-07)

- **A 4th property: NON-EVADABLE.** Escape hatches (allowlist / `rot-ok`) become a permanent dumping
  ground → the guard goes green while refs rot. **Exemptions must be time-bound + reasoned:**
  `<!-- rot-ok: YYYY-MM-DD reason -->`; expired marker → the guard FLAGS it. So the pillar has FOUR
  properties: **COMPLETE · UNBYPASSABLE · TRUSTWORTHY · NON-EVADABLE.**
- **The real chokepoints already exist — use them (mirror.py is leaky; `git push` bypasses it):**
  - **CI (`.github/workflows/ci.yml`, runs on every push+PR)** currently runs only boundaries +
    doc-freshness + pytest. **ADD `check_comprehensibility` + `check_wiring` + `check_door_parity`** →
    the unbypassable REMOTE gate (any push, any path, gets checked). *This replaces "wire into mirror".*
  - **pre-commit hook (`core.hooksPath → scripts/githooks/pre-commit`, runs on EVERY `git commit`)** —
    add the FAST F+G drift checks (stale-ref + case). Local prevention on every commit path.
  - `ship.py` unchanged (full guard, slice gate).
- **Scan roots MUST include `docs/`** — docs→docs stale links (a living doc citing a deleted
  `docs/FAQ.md`) are the MOST common drift and my code-only roots missed them entirely.
- **Case check MUST include code filenames** — `core/Utils.py` vs `core/utils.py` ships fine on
  Windows and breaks on Linux CI. Guard git-tracked case repo-wide, not just `docs/`.
- **Guard CRASH must FAIL LOUD, never silent-WARN-pass** — a hidden stack trace behind a WARN is
  indistinguishable from green; that IS the false-confidence cascade. A scan exception → FAIL with a
  distinct "the guard itself is broken, fix it" message (not a drift-FAIL, not a pass).
- Q4 confirmed: name-lies (c) partially caught by F (a docstring citing a deleted path fails); explicit
  semantic-rot FAIL + LEXICON-coverage stay WARN/deferred (too subjective to FAIL).
**Why this is a pillar:** as the codebase grows across many agents, it must stay *comprehensible* — to
agents (who navigate via docs + guards) and to Daniel. If comprehension rots, agents mis-navigate →
make wrong changes → the multi-agent knowledge system degrades → everything downstream cascades. The
guards ARE the immune system. This hardens it.

---

## 1. What already exists (audited 2026-07-07 — do NOT rebuild)

Six guards + an auto-index, strong on **structure**:

| Guard | Enforces | Level | Runs in |
|---|---|---|---|
| `check_comprehensibility.py` | (A) every `core/` subpkg in ARCHITECTURE.md · (B) MODULE_INDEX current · (C) docstrings · (D) doc age · (E) living docs in INDEX | A,B FAIL; C,D,E WARN | ship.py |
| `gen_arch_index.py` | auto-generates MODULE_INDEX from line-1 docstrings | — | ship.py (via B) |
| `check_boundaries.py` | layer imports · no bare-except · no dup class/module names | FAIL | ship.py |
| `check_wiring.py` | no built-but-unwired `core/` module | FAIL | ship.py |
| `check_door_parity.py` | CLI↔MCP verb parity | FAIL | ship.py |
| `check_doc_freshness.py` | repo root holds only living docs | FAIL | ship.py |

`ship.py` runs all 5 guards + full pytest, aborts on first failure. **`--no-test` skips everything.**

## 2. The three holes (all currently EXPLOITED — evidence collected)

- **H1 — BYPASSABLE.** Guards run in `ship.py` ONLY. `mirror.py` (commit+push, the publish path I used
  for every doc commit this session), plain `git commit`, and the `pre_commit.py` hook run **zero**
  guards. Drift walks straight into the shared repo via `mirror`. *This is the deepest hole.*
- **H2 — BLIND TO CONTENT DRIFT.** No check catches:
  - **stale references** — a living doc naming a deleted/renamed module. *3 live instances now*
    (`ROADMAP.md` → a nonexistent test; `DEPLOY.md` → 2 paths — but those are legit deployment targets,
    the false-positive lesson).
  - **filename case-mismatch** — `LEXICON.md` (git) vs `lexicon.md` (disk). *1 live instance*; bit us
    twice this session (silent half-commits, since git pathspecs are case-sensitive on a
    case-insensitive FS).
- **H3 — UNTESTED IMMUNE SYSTEM.** `check_comprehensibility` / `check_boundaries` / `check_doc_freshness`
  have **no tests** that inject drift and prove the guard FAILs. Only `door_parity`/`wiring` have (manual)
  ratchet probes. An immune system nobody tests can silently stop working — the worst failure mode
  because it *looks* green.

## 3. Design — three properties a pillar-grade immune system needs

### P1. COMPLETE — catch the drift that actually happens
Two new **FAIL** checks (added to `check_comprehensibility.py`, the existing home):

- **F. Stale repo-path references.** Scan living docs (UPPERCASE `docs/*.md` + `AGENTS.md` + `CLAUDE.md`)
  **and every `core/` module docstring** for repo-relative code paths under known roots
  (`core/ scripts/ tests/ agent/ context/ infrastructure/ security/`). FAIL if a referenced path does
  not exist on disk. **False-positive control (load-bearing):** only paths under those roots are
  checked; an inline `<!-- rot-ok: reason -->` marker OR a small `REF_ALLOWLIST` exempts legit non-repo
  paths (deployment `aurora/…`, illustrative examples). *Also catches "name-lies about dependencies" —
  a module docstring citing a renamed sibling.*
- **G. Filename case-canonicalization.** FAIL if (i) a `docs/` file's on-disk case ≠ its git-tracked
  case, or (ii) a living doc is referenced from another doc with the wrong case. Catches the
  `lexicon.md`/`LEXICON.md` class before it half-commits.

*(Deferred, WARN-only, later slice: (e) new LEXICON term coverage — too subjective to FAIL on.)*

### P2. UNBYPASSABLE — run on every path that reaches the shared repo
- Wire the **FAIL-level** checks into `mirror.py` (the commit+push publish path) — run before staging,
  abort the push on drift. This is the single highest-value point (it's what agents actually use).
- Keep `ship.py` running the full guard (belt).
- `mirror.py` gets a `--no-verify` escape hatch (emergencies); `ship.py` passes it (ship already gated,
  no double-run). Default = verify ON.
- *(Optional: also invoke from the `pre_commit.py` hook for plain `git commit` — suspenders.)*

### P3. TRUSTWORTHY — the immune system is itself tested
New `tests/test_comprehensibility.py` (real pytest, not a manual probe) that, per drift class:
- asserts the guard **PASSES** on a clean fixture,
- **injects** each drift (missing subpackage, stale MODULE_INDEX, stale ref, wrong-case filename) and
  asserts the guard **FAILS** with the right message,
- asserts **NO false-positive** on the allowlisted cases (deployment path, `<!-- rot-ok -->`).
Promote the `door_parity`/`wiring` manual probes into this suite too, so every ratchet is CI-proven.

## 4. Also fix the live drift (so the hardened guard passes)
- Fix the 3 stale refs (correct `ROADMAP.md`; allowlist/annotate the 2 `DEPLOY.md` deployment paths).
- Resolve the `LEXICON.md`/`lexicon.md` case inconsistency (canonicalize to UPPERCASE on disk + git).

## 5. Robustness discipline (baked in)
- **FAIL only when objective + low-false-positive.** Stale-ref and case are deterministic; the
  allowlist + root-scoping keep false-positives near zero (a noisy guard gets disabled — the anti-goal).
- **Fail-SOFT on a guard *crash*, fail-HARD on detected *drift*.** A bug in the guard must not brick all
  commits; but real drift must block. (Wrap the scan; a scan exception → WARN + pass, never a false FAIL.)
- **One source of truth.** `check_comprehensibility.py` stays the single guard; `mirror`/`ship`/hook all
  invoke it. No logic duplication.
- **Every new check has a test** (P3) — no untested addition to the immune system.

## 6. Slice plan
- **S1** — F (stale-ref) + G (case) FAIL checks in `check_comprehensibility.py` + fix live drift + tests.
- **S2** — wire FAIL-checks into `mirror.py` (`--no-verify`, ship passes it) — close H1.
- **S3** — `tests/test_comprehensibility.py` full drift-injection suite + promote door/wiring probes.
- *(S4 optional — pre-commit hook invocation; LEXICON-term WARN.)*

## 7. Questions for DeepSeek
- **Q1 (false positives).** Is root-scoping + `<!-- rot-ok -->` + a small allowlist enough to keep the
  stale-ref check from crying wolf, or do you want a stricter reference grammar (only backticked paths)?
- **Q2 (unbypassable vs latency).** Gating `mirror.py` on every commit adds a doc-scan + index-regen
  compare. Acceptable, or should mirror run only F+G (cheap) and leave A+B (index regen) to ship?
- **Q3 (case fix).** Safest way to canonicalize `lexicon.md`→`LEXICON.md` on a Windows case-insensitive
  FS without a half-rename? (two-step `git mv`?)
- **Q4 (scope).** Is deferring (c) name-lies and (e) LEXICON-coverage to WARN/later right, or is one of
  them load-bearing enough to FAIL now?
- **Q5.** What did I miss — any drift vector or failure mode absent here?
