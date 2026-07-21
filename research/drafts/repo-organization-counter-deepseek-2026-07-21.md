# Repo organization & hygiene — counter position (deepseek)

Date: 2026-07-21 · Round: counter → kimi fresh-eyes → reconcile → Daniel gates
Positions: P5 (.agents/.codex), P6 (play retention), P8 (UTF-8 door), Q3 (play TTL), Q4 (.codex secrets)

---

## P5 — .agents/ + .codex/ commit posture: REFINE (split posture)

Claude's position: secrets-scan first, then commit both. The instinct is right but the
two directories are NOT the same class — they demand different postures.

### .agents/skills/ — ADOPT (commit unconditionally)

Four skill definitions, zero secrets, zero keys, zero tokens. This is contract-grade
content in the same family as `charters/` — cross-harness skill definitions that any
seat can consume. No scan needed; there is nothing to scan.

**Verdict: ADOPT Claude's commit posture for .agents/. Commit immediately after Daniel
ratifies the charter family (same gate as P4).**

### .codex/ — REFINE (commit + permanent guard, not one-time scan)

What's actually on disk:
- `config.toml` (212 bytes): sandbox_mode, one env var (`AKASHIC_AGENT_ID = "claude"`),
  one MCP server config. No API keys, no tokens, no passwords.
- `hooks.json` (1342 bytes): hook definitions pointing at `scripts/hooks/*`. Clean.

The "secrets-scan first" Claude proposes is the right instinct but is **point-in-time
theatre**. A scan today says "clean"; the next config edit could add `api_key = "sk-..."`
by accident and the scan from three weeks ago won't catch it.

**My counter: commit both files now (they ARE clean), but ship a permanent guard:**
`.codex/.gitignore` with deny-by-default patterns for anything that even LOOKS like a
credential:

```
# .codex/.gitignore — permanent secrets posture (deepseek P5 counter, 2026-07-21)
*key*
*secret*
*token*
*.env
*credential*
*password*
```

This is the same posture as `.secrets/` being gitignored at root — a structural
guarantee, not a one-time check. Any future file matching those patterns is silently
never staged. A `config.toml` with an inlined key is still committable (the pattern
matches filenames, not contents), so the mojibake-style check_boundaries scan (P8)
is the content-level backstop.

**Verdict: ADOPT Claude's commit, REFINE with .codex/.gitignore permanent guard.**

---

## P6 — data/play retention + gitignore: REFINE (three categories, not two)

Claude's position: `runs/` gitignored, `out/` curated. This is correct but misses two
categories that exist on disk right now.

What's actually under `data/play/`:

| Path | Count | What it is | Posture |
|---|---|---|---|
| `data/play/<agent>/*.py` | 3 files | Play-tier TOOLS (campfire.py, verbthread.py, premonition.py) | **COMMIT** — source code, same family as scripts/ |
| `data/play/<agent>/out/*.md` | 2 | Curated play outputs | **COMMIT** — knowledge artifacts |
| `data/play/<agent>/runs/*.json + *.out` | 8 pairs | Runtime receipts (full prompt/response) | **.gitignore** — never committed |
| `data/play/<agent>/threads/*.jsonl` | 11 files + 2 .tmp | Play session state | **COMMIT .jsonl, .gitignore .tmp** |
| `data/play/test/` | 30 files | Harness-test debris | **DELETE** |

### The play-tool split

The `.py` files are SOURCE, not runtime artifacts. `campfire.py`, `verbthread.py`,
`premonition.py` are executable play-tier tools — they belong in the same class as
`scripts/*.py`. Committing them ensures a play verb is reproducible: anyone who pulls
the repo can run `py core/toolbelt/play_sandbox.py claude/campfire`.

Claude's P6 only addressed `runs/` and `out/`. The `.py` tools and `threads/` state
were invisible in the census.

### test/ — the one true deletion

`data/play/test/` is 30 files of harness-test debris (chatter, hello, sleeper runs).
This is not an artifact — it's the equivalent of `__pycache__`. DELETE, don't park.
It has no citations, no knowledge value, and no connection to any pin. This is the
one case in the whole round where deletion is the right answer.

### runs/ retention

`runs/*.json` contains the full prompt + response context. They're bounded by the
sandbox output cap (64KB) and are useful for debugging a play that went wrong. But
they're NOT knowledge artifacts — they're runtime receipts. .gitignore the whole
tree. Add a `.gitkeep` so the directory survives clone.

**Verdict: ADOPT Claude's runs/ gitignore, REFINE with the tool/thread/test split.**

---

## P8 — UTF-8 at the write door: ADOPT + EXTEND (door-level refusal)

Claude's position: force UTF-8 at write door, check_boundaries rule-8 mojibake scan,
lesson filed. All three are correct. The lesson (`mojibake_ps_replace_second_bite`)
is the critical finding: "a lesson alone did not hold."

### My door is not the vector

The `write_file` and `edit_file` tools are Python-native with `encoding="utf-8"` —
they have never produced mojibake. Both bites came from OUTSIDE the ToolBox door:
PowerShell `-replace` on multibyte chars (first bite, 21d1193; second bite, 0537c48).
The second bite re-introduced the SAME class that the first repair fixed — a lesson
in the knowledge store did not prevent recurrence.

### The real chokepoint: mirror.py

The `mirror.py` commit path is the gate where mojibake enters the repo. That's
where the hard guard belongs — before `git add`, not after. My proposal:

**Pre-commit mojibake scan in mirror.py:** before staging files, scan every
tracked `.md` in the diff for the four known sequence classes:

```
\u00e2\u20ac  (â€ — smart quotes re-encoded)
\u00c3\u2014  (Ã— — em-dash re-encoded)  
\u00e2\u2020  (â† — arrow re-encoded)
\u00c2\u00a7  (Â§ — section sign re-encoded)
```

A file containing ANY of these sequences is REFUSED at the mirror gate with a
message naming the file + line + class. The operator fixes the encoding and
re-commits. This is the same class as the existing mirror path-scoping guard
(IR-4) — a pre-commit invariant, not a post-hoc lint.

### check_boundaries rule-8 as backstop

The scan Claude proposes is the post-hoc catch for files that bypass mirror.py
(direct `git add` from a human). Both layers: pre-commit refusal at the door,
check_boundaries scan as the safety net.

**Verdict: ADOPT Claude's rule-8 + lesson. EXTEND with mirror.py pre-commit
refusal — the hard guard that makes a third bite structurally impossible.**

---

## Q3 — play retention: NO TTL, curate-at-wrap

Claude asks: TTL or curate-at-wrap?

My answer: **curate-at-wrap, never a TTL.** Play outputs are creative artifacts
in the same class as research drafts. A TTL that auto-deletes them is a
knowledge-loss mechanism — it would have eaten `campfire-2026-07-21.md`, which
shipped the vitals verb's why-paragraph across the fleet.

The retention model mirrors research lifecycle:
- During play: `out/` accumulates freely (sandbox output cap bounds size).
- At wrap: the agent reviews `out/` and commits what's worth keeping by name.
- A play output the agent doesn't commit at wrap is implicitly temporary and
  CAN be cleaned at the next janitor pass.
- There is no auto-deletion — the janitor asks, the agent confirms.

**Verdict: curate-at-wrap. A TTL that silently eats a creative artifact is the
same genus as a stale cursor that silently eats mail.**

---

## Q4 — .codex secrets posture: CLEAN on disk, permanent gitignore guard

What's actually in `.codex/`:
- `config.toml` — sandbox_mode, one env var, one MCP server. No secrets.
- `hooks.json` — hook definitions. No secrets.

Verdict: the files ARE clean. Commit them. The permanent posture is the
`.codex/.gitignore` deny-by-default patterns from P5 above — that's the guard
against the NEXT config edit, not a scan of the current one.

One additional hardening: `config.toml` currently has `sandbox_mode = "danger-full-access"`.
This is a Codex-specific seat config, not a secret, but it IS a high-trust setting
that should carry a comment explaining WHY it's set and what the alternative is.
Before committing, add:

```toml
# sandbox_mode: "danger-full-access" = Codex runs unrestricted in our repo
# (the ToolBox family gate + ACLs are our sandbox, not Codex's built-in one).
# Alternative: "workspace-write" would block Codex from running our hooks.
```

---

## Other positions — agree without counter

- **P1** (no mass moves): ADOPT. The two-kinds law holds.
- **P2** (research lifecycle forward): ADOPT.
- **P3** (batch commit untracked research): ADOPT. The 47 drafts are the biggest
  silent-loss risk — commit by name at reconcile.
- **P4** (charters/ at root): ADOPT.
- **P7** (probes out of tests/): ADOPT. `tests/` is for pins.
- **P9** (check_boundaries rules 8/9/10): ADOPT all three.

---

## Summary

| Position | Verdict | Key amendment |
|---|---|---|
| P5 (.agents/) | ADOPT | Commit immediately with charters gate |
| P5 (.codex/) | REFINE | Commit + `.codex/.gitignore` permanent guard |
| P6 (play) | REFINE | Four-way split: tools=commit, out=commit, runs=ignore, test=DELETE |
| P8 (UTF-8) | EXTEND | ADOPT rule-8 + mirror.py pre-commit refusal |
| Q3 (retention) | curate-at-wrap | No TTL — same class as research drafts |
| Q4 (.codex secrets) | CLEAN | Commit + P5 gitignore guard + config comment |
