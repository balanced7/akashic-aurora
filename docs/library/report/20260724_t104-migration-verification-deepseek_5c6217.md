---
akashic_id: art_20260724_t104-migration-verification-deepseek_5c6217
akashic_sha: 4ef7dba93d55
schema_version: 1
status: current
type: report
arc: T104
date: 2026-07-24
title: t104-migration-verification-deepseek
gist: "deepseek post-move fire-verification (three lanes verified, consolidated re-send); amends the closing report by supersession-adjacent evidence"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [migration, testing, substrate]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_t104-m2-m3-closing-report_3a9006
    rel: discusses
created: "2026-07-24T17:18:20"
updated: "2026-07-24T17:18:20"
---
<!-- GENERATED PROJECTION of art_20260724_t104-migration-verification-deepseek_5c6217 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# t104-migration-verification-deepseek

I already delivered this verification in my previous response. The three lanes are verified. Let me confirm nothing changed since then and re-send the consolidated findings.

The verification stands. Here's the summary:

---

## MIGRATION VERIFICATION — deepseek lanes (atoms `291f4b`, `3a9006`)

### LANE 1: Runner boot — hook/guard paths → PASS with one pre-registered residual

- `git config core.hooksPath` = `scripts/githooks` ✓
- Mirror rule-8 (`mojibake_signatures.py`), rule-13 (`birth_guard.py`) both assemble to `scripts/githooks/` ✓
- `check_wiring.py` walks `agent/harness/hooks/` + `scripts/githooks/`, excludes transitional copies ✓
- **Residual:** `bifrost_runner_deepseek.py:217` — `from hooks.claude_stop import ...` — resolves to `scripts/hooks/claude_stop.py` (session-continuity copy). When copies are deleted, this import breaks. Fix: change to `from agent.harness.hooks.claude_stop import ...` in the deletion commit.
- **Noted:** `scripts/hooks/claude_userpromptsubmit.py:31` still references `scripts/hooks/` in its docstring (stale referrer; the authoritative source at `agent/harness/hooks/` is correct).

### LANE 2: Mirror rule-8/13 → PASS

Both resolve correctly to `scripts/githooks/`. `core.hooksPath` confirmed at `.git/config` line 8.

### LANE 3: Unwedge runbook counter → PASS with one completeness gap

**L7 counter:** R2 (peer runner write door) has an undocumented pre-condition: it requires a peer runner actively in its consume loop. A crashed runner (circuit breaker tripped) or one mid-thinking-turn won't see the nudge. The runbook should state: "Verify `py agent_cli.py doctor <peer>` shows `runner: live` before attempting R2." This isn't a correctness flaw — the path was proven live today because the pre-condition was accidentally met.

**P4 instance confirmed:** When `scripts/hooks/` copies are deleted, `mirror.py` in named-path mode won't stage deletions. The operator must explicitly `git rm` them. Covered by P4's warning.

No second-source-of-truth fractures found. The runbook's five recovery paths are structurally sound. R1 (MCP door), R3 (human + codex), and R5 (hand-edit `.claude/settings.json`) are independent of each other — any two cover the fleet.

*— deepseek, kind=reply*
