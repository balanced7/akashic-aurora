# Portability fan — five-shard classification of AI-Setup path references

*2026-08-24, ask fan (partition geometry, 5 workers), launched per Daniil's
"we can use fanouts with cli to check for these things". Full branch answers verbatim.*

## Shard 0

FINDINGS:
- agent/harness/hooks/claude_pretooluse.py:11 DOC-PROSE -- instructional comment example uses `E:/AI-Setup/...`; no runtime effect.
- core/foundation/store.py:369 DEFAULT-WITH-OVERRIDE -- override=env `AI_SETUP`; fallback `E:\AI-Setup` is non-portable and `mkdir` will fail on C:-only if `AI_SETUP` is unset.
- core/library/atoms.py:70 DEFAULT-WITH-OVERRIDE -- override=function arg `repo_root`; hardcoded default used only when `jsonl_dir` is relative and caller does not pass `repo_root`.
- core/signals/coordinator_api.py:102 DEFAULT-WITH-OVERRIDE -- override=env `AI_SETUP`; fallback `E:\AI-Setup` is non-portable and `mkdir` will fail on C:-only if `AI_SETUP` is unset.

REASONING:
The comment hit is prose, not executable. The three code hits are fallback defaults with named overrides, so they are not unconditional hardcoded uses by code shape. However the two `AI_SETUP` defaults are not the canonical `repo_root()`/`AKASHIC_REPO` resolver and will break on a fresh C:-only clone if the override is not set; they should be migrated to the canonical resolver.

CHECK:
Could not verify from the excerpt whether peer environments set `AI_SETUP`, what `DEFAULT_JSONL_DIR` is in atoms.py, whether atoms callers pass `repo_root`, or whether `mkdir` on a missing `E:` is otherwise caught.

BLIND:
Excerpt-level audit cannot see all callers of these classes/functions, setup/env conventions, or other hardcoded `E:\AI-Setup` occurrences outside the listed hits.

## Shard 1

FINDINGS:
- agent/harness/hooks/claude_userpromptsubmit.py:31 DOC-PROSE -- hardcoded `E:/AI-Setup` appears only in module docstring example config; no runtime path execution from that string literal.
- core/infrastructure/health_check.py:21 DEFAULT-WITH-OVERRIDE -- fallback default is `E:\AI-Setup`; override is env var `AI_SETUP` (not the canonical `AKASHIC_REPO`/`repo_root()`).
- core/library/projection.py:94 DEFAULT-WITH-OVERRIDE -- function parameter default `repo_root="E:\\AI-Setup"`; override is the `repo_root` argument supplied by the caller.
- core/state/session_checkpoint.py:41 DEFAULT-WITH-OVERRIDE -- same pattern as health_check; fallback `E:\AI-Setup`; override is env var `AI_SETUP`.

REASONING:
- `claude_userpromptsubmit.py:31` is inside a docstring, so importing/using the module does not execute the `py E:/AI-Setup/...` command.
- `health_check.py:21` and `session_checkpoint.py:41` do run at module import: `Path(...).mkdir(parents=True, exist_ok=True)`. On a fresh C:-only clone with `AI_SETUP` unset, the default `E:\AI-Setup` is unsafe. They are classified as DEFAULT-WITH-OVERRIDE because an env var can override, but the default does not use `repo_root()` and can still break peers.
- `projection.py:94` only uses the hardcoded path when callers do not pass `repo_root`.

CHECK:
- Cannot verify from the excerpt whether peer instances actually set `AI_SETUP` or pass `repo_root`; if not, the two log_dir cases become runtime hazards.
- Cannot see callers of `render_atom()`.
- Cannot verify whether the docstring hook snippet is ever used as copy-paste setup by peers.

BLIND:
- Other files outside these hits may contain additional `E:\AI-Setup` or `AI_SETUP` references.
- Cannot see configs/scripts that may export `AI_SETUP` or `AKASHIC_REPO`.
- Cannot compare against the canonical `core/paths.py::repo_root()` implementation from these excerpts alone.

## Shard 2

FINDINGS:
agent/harness/scope.py:6 DOC-PROSE -- comment mentions “AI-Setup lessons” only; no path used at runtime.
agent/harness/scope.py:57 DOC-PROSE -- docstring mentions “AI-Setup path / agent_cli.py”; no runtime path.
core/learning/consolidation.py:81 DEFAULT-WITH-OVERRIDE -- fallback `E:\AI-Setup\chronicles` overridden by `chronicle_dir` arg or env `AI_SETUP`.
core/narrative/chronicler.py:149 DEFAULT-WITH-OVERRIDE -- fallback `E:\AI-Setup\chronicles` overridden by `chronicle_dir` arg or env `AI_SETUP`.
core/state/session_recovery.py:306 DOC-PROSE -- print instruction hardcodes `E:\AI-Setup\dockerized-ai\redis`; no filesystem/runtime effect.

REASONING:
The two path hits are real path construction but are guarded by an explicit `chronicle_dir` parameter and an `AI_SETUP` env lookup, so they are fallback defaults rather than unconditional hazards. They do not use the canonical `repo_root()` / `AKASHIC_REPO` resolver, so a fresh C:-only clone is only safe if one of those overrides is supplied. The other hits are comments/docstrings or a printed instruction; they do not touch the filesystem.

CHECK:
I could not verify from this excerpt whether callers always pass `chronicle_dir` or set `AI_SETUP`, so the actual runtime risk of the two default-with-override hits is not fully confirmed. I also could not see `core/paths.py` or any bootstrap code that might set these variables.

BLIND:
This excerpt-level audit cannot see other hardcoded absolute paths outside the listed files, call sites of these functions, environment setup, or whether `repo_root()` is consistently used elsewhere.

## Shard 3

FINDINGS:
core/foundation/ledger.py:186 REAL-HAZARD -- hardcoded default `E:\AI-Setup\session_logs\ledger` is used with immediate `mkdir`, so a fresh C:-only clone fails unless `base_dir`/`AI_SETUP` is supplied.
core/learning/learning_store.py:198 REAL-HAZARD -- hardcoded default `E:\AI-Setup\coordinator_logs` is used with immediate `mkdir`, so a fresh C:-only clone fails unless `AI_SETUP` is set.
core/learning/learning_store.py:227 DEFAULT-WITH-OVERRIDE -- `AI_SETUP` overrides the `E:\AI-Setup` fallback; `exists()` is a read-only probe, so it likely skips legacy import rather than crashes.
core/paths.py:4 DOC-PROSE -- module docstring defect-count text; no runtime effect.
core/paths.py:6 DOC-PROSE -- same docstring narrative; no runtime effect.
core/world.py:5 DOC-PROSE -- docstring example of an old clone-resolution defect; no runtime effect.
core/world.py:6 DOC-PROSE -- docstring example continuation; no runtime effect.
core/world.py:167 DOC-PROSE -- function docstring leaf-name mapping; no runtime effect.

REASONING:
The two `mkdir` lines (`ledger.py:186`, `learning_store.py:198`) turn the hardcoded default into an actual write/creation attempt, so they break on C-only machines when `AI_SETUP` is unset. `learning_store.py:227` only calls `exists()`, so the absolute fallback does not create a path; it can silently skip legacy import. The `paths.py` and `world.py` hits are docstring/prose, not executed. None of these code paths uses the canonical `core/paths.py::repo_root()` resolver, which is the main reason they remain portability hazards.

CHECK:
I could not verify call sites of `Ledger.__init__()` or the learning-store constructor, so I cannot tell whether `base_dir` is always supplied. I also could not verify from this excerpt whether `AI_SETUP` or `AKASHIC_REPO` is set in the actual target environment, nor the exact Windows `Path.exists()` behavior on an invalid `E:` drive; 227 assumes it returns false rather than raising.

BLIND:
This excerpt cannot see all other hardcoded `E:\AI-Setup` occurrences, especially unconditional `.py/.ps1/.bat` uses. It also cannot see whether `repo_root()` has already been adopted at higher layers and whether any bootstrap/config sets `AI_SETUP`, `AKASHIC_REPO`, or an E: drive before these modules run.

## Shard 4

FINDINGS:
core/foundation/redis_connection.py:74 DOC-PROSE -- comment text records `E:/AI-Setup-Alpha` as a measurement example; no executable runtime path on this line.
core/learning/vfx_chunk_lessons.py:141 DEFAULT-WITH-OVERRIDE -- `E:\AI-Setup` is a fallback default overridden by `AI_SETUP` env and `--chunks` arg, but it ignores `repo_root()`.
core/recall/anchors.py:63 DEFAULT-WITH-OVERRIDE -- `E:\AI-Setup` is the fallback `ROOT`, overridden only by `AI_SETUP` env.
scripts/checkers/check_boundaries.py:57 DEFAULT-WITH-OVERRIDE -- hardcoded `E:\AI-Setup` is a last-resort fallback after `repo_root()` and then `AI_SETUP` env.

REASONING:
The redis hit is inside the comment block `redis_connection.py:73-77`; the cited line has no runtime effect. The two `AI_SETUP` defaults are runtime fallbacks with named overrides, so they are not unconditional REAL-HAZARDs based on the excerpt, but they do bypass the canonical `core.paths.repo_root()`/`AKASHIC_REPO` mechanism. `check_boundaries.py` prefers `repo_root()` first (`scripts/checkers/check_boundaries.py:54-55`), so its hardcoded fallback is less likely to be reached on a healthy C-only clone.

CHECK:
I could not verify from the excerpts alone whether the `ROOT` in `anchors.py` and `repo` in `vfx_chunk_lessons.py` are actually used later for filesystem reads/writes; the excerpts only show assignment and argparse default construction. I also could not verify whether `AI_SETUP` is set/propagated on peer instances, or whether `repo_root()` ever raises in `check_boundaries.py`.

BLIND:
This excerpt-level audit cannot see other hardcoded `E:\AI-Setup` or `E:/AI-Setup*` occurrences outside these four excerpts, nor the downstream usages of these variables across the rest of their files. It also cannot see runtime environment setup, import-time execution order, or whether switching these fallbacks to `repo_root()` would break other behavior.
