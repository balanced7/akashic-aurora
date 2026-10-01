# Advisory backlog

Status: current
Class: reference

ADVISORY verifier findings and observations that never fail a phase (plan section 9). A later
goal may harden any of them.

| Id | Raised in | Finding | Suggested owner |
|---|---|---|---|
| ADV-001 | G0.P1 | The repo's pre-commit stage fails on `master` itself with nothing staged: the guardrail ratchet (boundaries 5 vs baseline 3, comprehensibility 8 vs 0, wiring 1 vs 0) and `check_comprehensibility --fast` (3 drift FAILs, stale references in docs/SHELVES.md). It also regenerates and stages 5 derived docs (docs/MODULE_INDEX.md, MAP.md, PHYSICS.md, DOORS.md, PRIOR_ART.md) on every commit; they are stale on master and PHYSICS.md embeds the HEAD sha. Hooks are not installed in any checkout (core.hooksPath unset). | repo owner |
| ADV-002 | G0.P1 | A full suite run inside a checkout mutates it: it rewrote the tracked `data/verb-registry/deepseek.json` and an untracked `docs/*.md` file disappeared during the run (culprit test not isolated). The oracle runs every suite in a throwaway worktree and records `tree_side_effects` per run in O1. | G5 (test tooling) |
| ADV-003 | G0.P2 | 17 argparse entry points exit 1 under `--help` when run as `python <path>` (relative imports or `core` not on sys.path, e.g. arsenal/band.py, core/coord/conductor.py). Recorded as-is in O4; they work as `python -m`. | G6 or later |
| ADV-004 | G0.P2 | `scripts/generators/gen_doors.py --help` rewrites docs/DOORS.md (side effect under --help); recorded N/A in O4 per the G0 Fallback. | repo owner |
| ADV-005 | G0.P4 | Ruff 0.16.9 `format --check` PANICS in its default `full` diagnostic renderer (ruff_annotate_snippets/src/renderer/source_map.rs:185) on scripts/arc_scorecard.py and tests/test_exec_env_identity.py. Bisected per file. The formatter itself is fine on both (`--output-format concise` and `--diff` exit 1 = would reformat), so no exclusion is registered; G2's `fmt-check` task should pass `--output-format concise` until a Ruff release fixes the renderer. | G2 |
| ADV-006 | G0.P4 | basedpyright 1.40.1 `--outputjson` crashes in V8 (exit 245/251, no message) on the full in-scope set; the text output completes (3,175 errors). certify.py T2 reads `filesAnalyzed` from `--outputjson`, so G4 must either get JSON working (fewer diagnostics, newer release) or read the count another way. | G4 |
| ADV-007 | G0.P1 verifier | The plan copy reached the branch by fast-forward to the operator's master commit d5f0615d (identical content) instead of a branch commit `docs(plan): ...`. | none (recorded) |
| ADV-008 | G0.P1 verifier | One check result line was overwritten by NUL bytes when certify output was redirected to a file: a check subprocess appears to share the stdout descriptor. Cosmetic. | G1 (certify) |
| ADV-009 | G0.P3 verifier | certify.run_check runs check commands in the caller's environment, not oracle_env (REDIS_DB=15 is not forced). No G0 check touches Redis. | G1 (certify) |
| ADV-010 | G0.P3 verifier | oracle.ast_equal reads blobs as text with errors="replace"; a change confined to non-UTF-8 bytes could be masked. Read bytes before G2's format proof. | G2 |
| ADV-011 | G0.P3 verifier | G1-G7 checks omit a few plan exit criteria (G4 "no baseline file" outside its Fallback, G5 hook-stage unit test, G6 fresh-clone install); add them (append-only) when those goals start. Also D14's presence probe is `poe -d oracle`, so it reads "gate absent" until G1 adds that task; selftest-d14 covers the mechanism. | G4, G5, G6 |
| ADV-012 | G0.P3 verifier | Commit d5c53283 bundles the compare_o1 signature fix with the measure workarounds (atomicity). | none (recorded) |
| ADV-013 | G0.P2 verifier | Requirements-consumer detection misses hyphenated names: scripts/gemini_web_login.bat runs `pip install -r requirements-gemini-web.txt` (a file that does not exist; only requirements/gemini-web.txt is tracked). G1.P4 must treat this .bat as a pip consumer. | G1 |
| ADV-014 | G0.P2 verifier | ARCHIVAL rejection is conservative: generated catalogs (docs/PHYSICS.md env table, data/corpus-digests, store/docs/*.jsonl) and unique-basename matches keep ~67 history files in scope. Safe direction; costs G3/G4 effort. | G3/G4 (may tighten the proof, with evidence) |
| ADV-015 | G0.P2 verifier | annotation_sensitive excludes TEST files (~20 have dataclass/inspect.signature/@mcp.tool triggers); tooling facts omit .mcp.json's `uv run ai_setup_mcp.py`; doc_commands is the curated 5-command O7 list. | G3 Verifier B |
