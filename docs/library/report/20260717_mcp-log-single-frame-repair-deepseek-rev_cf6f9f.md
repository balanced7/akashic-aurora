---
akashic_id: art_20260717_mcp-log-single-frame-repair-deepseek-rev_cf6f9f
akashic_sha: 935c554c45b5
status: draft
type: report
date: 2026-07-17
title: "MCP `log` Single-Frame Repair — deepseek-review M1-LITE verdict (2026-07-17)"
gist: "Brief: research/briefs/mcp-log-single-frame-brief-2026-07-17.md Owner: codex_root Review seat: deepseek-review --- ## VERDICT: ROOT CAUSE CL"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, conducting, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_mcp-log-single-frame-repair-m1-lite-brie_56130c
    rel: cites
created: "2026-07-17T02:57:33"
updated: "2026-07-23T21:42:20"
---
<!-- GENERATED PROJECTION of art_20260717_mcp-log-single-frame-repair-deepseek-rev_cf6f9f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# MCP `log` Single-Frame Repair — deepseek-review M1-LITE verdict (2026-07-17)

Brief: research/briefs/mcp-log-single-frame-brief-2026-07-17.md
Owner: codex_root
Review seat: deepseek-review

---

## VERDICT: ROOT CAUSE CLOSED. Scope minimal. Opt-in preserved. Tests non-flaky. SHIP.

---

## 1. ROOT CAUSE ANALYSIS

### The defect

HEAD `beat_log.py:_assign_themes` (line 76-80) unconditionally imports `select_theme_assigner` from `core.narrative.theme_discovery`:

```python
def _assign_themes(self, beat: Beat, hint) -> None:
    try:
        from core.narrative.theme_discovery import select_theme_assigner
        beat.themes = select_theme_assigner().assign(beat, hint)
    except Exception:
        ...
```

The `select_theme_assigner()` function (at `theme_discovery.py:178-195`) ALREADY contains an opt-in check: it reads `AKASHIC_EMBED_THEMES` and returns the keyword assigner when the flag is off. **But the function lives in `theme_discovery.py`, which has `import numpy as np` at module level (line 30).** Importing the function triggers the module load, which triggers the NumPy import. This is a cold import on FastMCP's synchronous stdio event-loop thread.

On Windows, NumPy's DLL load inside FastMCP's synchronous `tools/call` handler parks the ProactorEventLoop's outbound `WriteFile` completion until a new inbound `ReadFile` event arrives — the exact C7-4 mechanism confirmed by the hardening reconciliation (three independent analyses: claude/deepseek/Gemini). The `log` tool response sits pending until the client sends a second JSON-RPC frame, which flushes it. Terminal timeout: 60s (harness kill) or 5s (test timeout).

### The fix

The working tree `beat_log.py:_assign_themes` (lines 76-89) moves the opt-in check BEFORE the import:

```python
def _assign_themes(self, beat: Beat, hint) -> None:
    try:
        embed_on = os.getenv("AKASHIC_EMBED_THEMES", "").lower() in (
            "1", "true", "yes", "on",
        )
        if embed_on:
            from core.narrative.theme_discovery import select_theme_assigner
            assigner = select_theme_assigner()
        else:
            from core.narrative.theme_assigner import get_theme_assigner
            assigner = get_theme_assigner()
        beat.themes = assigner.assign(beat, hint)
    except Exception:
        ...
```

Default path (`AKASHIC_EMBED_THEMES` off): imports `get_theme_assigner` from `theme_assigner.py` — a lightweight pure-Python module with no NumPy dependency. Cold import ~tens of milliseconds.

Opt-in path (`AKASHIC_EMBED_THEMES=1`): imports `select_theme_assigner` from `theme_discovery.py` — same behavior as before, including NumPy import. The opt-in pays the cold-load cost knowingly; this is correct (the operator opted in).

### Why the comment in HEAD was aspirational but wrong

HEAD's comment said: "V6c: hybrid embedding themes when the model is already warm (long-lived agents), else the fast keyword baseline -- so a short-lived CLI write never pays a cold load." This describes the CORRECT behavior. The `select_theme_assigner()` function inside `theme_discovery.py` was SUPPOSED to implement this check. But importing it AT ALL loaded NumPy, defeating the check. The comment was correct about intent; the code was wrong about mechanism. The fix makes the code match the comment.

### Is root cause actually closed?

**Yes.** The fix addresses the mechanism, not the symptom. The mechanism is: importing `theme_discovery.py` triggers a cold NumPy DLL load on FastMCP's synchronous event-loop thread, which parks the Windows ProactorEventLoop writer. The fix prevents the import on the default path. The C7-4 class is broader (any subprocess that inherits stdout triggers the same wedge), and the hardening reconciliation addresses those separately. But for the MCP `log` tool specifically, root cause is closed.

---

## 2. SCOPE MINIMALITY

| Dimension | Assessment | Evidence |
|-----------|-----------|----------|
| Files changed | 1 file | `core/narrative/beat_log.py` only |
| Lines changed | ~13 lines | `_assign_themes` function: old 5-line body → new 14-line body |
| Functions changed | 1 function | `_assign_themes` |
| Import surface change | None | Same imports as before, just conditionalized |
| API change | None | `_assign_themes` signature unchanged; `emit()` signature unchanged |
| Behavior change (default) | None | Same keyword themes as before; same `get_theme_assigner()` call |
| Behavior change (opt-in) | None | Same `select_theme_assigner()` call; same embedding path |
| Narrative semantic change | None | Beat theme assignment produces identical results |
| Callers affected | 1 | `BeatLog.emit()` → `_assign_themes()` — no other callers |

**Verdict: MINIMAL.** One function, one file, ~13 lines. The change is a pure refactor of the import site from unconditional to conditional. No new dependencies, no new functions, no API surface change.

---

## 3. OPT-IN BEHAVIOR PRESERVED

**Test 2** (`test_explicit_embedding_opt_in_still_uses_discovery_selector`) verifies: when `AKASHIC_EMBED_THEMES=1`, the `select_theme_assigner` function from `theme_discovery` is imported and called. The test uses a fake module to avoid the real NumPy load, and asserts:
- The fake assigner's `assign()` was called with `("routing verification", None)`
- The beat's themes were set to `["embedding-opt-in"]` (the fake assigner's return value)

**The defense-in-depth is intact:** `theme_discovery.py:select_theme_assigner()` at line 190 STILL has its own `AKASHIC_EMBED_THEMES` check. When the default path bypasses the import entirely, this check is unreachable (correct — the import never happens). When the opt-in path imports the module, the check runs and confirms the flag is on. If some future caller imports `select_theme_assigner` directly without the flag check, the defense-in-depth still catches it. No regression.

---

## 4. TEST NON-FLAKINESS

### Test 1: `test_default_keyword_path_does_not_import_embedding_discovery`

**Deterministic class pin.** Uses `monkeypatch` to:
1. Set `AKASHIC_EMBED_THEMES=0`
2. Delete `theme_discovery` from `sys.modules` (so cache warmth can't hide the import)
3. Install a recording `__import__` wrapper that logs any attempt to import `core.narrative.theme_discovery`
4. Call `BeatLog.__new__(BeatLog)._assign_themes(beat, hint=None)`
5. Assert `attempted == []` — the import was never attempted

**Non-flaky by construction:** the recording wrapper catches the `__import__` builtin call BEFORE any module code executes. Even if the test environment has NumPy pre-loaded, the wrapper fires on the import ATTEMPT, not on the load cost. The test proves the import NEVER HAPPENS, not that it's fast when it does.

### Test 2: `test_explicit_embedding_opt_in_still_uses_discovery_selector`

**Deterministic class pin.** Sets `AKASHIC_EMBED_THEMES=1`, injects a fake `theme_discovery` module, and asserts the opt-in path calls the fake assigner. Non-flaky: no real NumPy, no real model, no Redis.

### Test 3: `test_fresh_stdio_mcp_log_returns_without_second_frame`

**Real transport pin.** Spawns a fresh `ai_setup_mcp.py` stdio server, sends one `log` tool call, waits 5 seconds, and asserts the response arrived. This is the genuine end-to-end test.

**Non-flaky assessment:** The test uses `_AISETUP_TEST_ISOLATED=1` and `REDIS_DB=15` for full isolation. The 5-second timeout is generous for a cold Python+MCP server start. The assertion checks for `"[OK] note: single-frame transport pin"` in the response text — a positive match on the expected output. If the NumPy import were still happening, the response would not arrive within 5 seconds and `asyncio.wait_for` would raise `TimeoutError`.

**One caveat:** The test depends on the MCP SDK being installed and the server starting cleanly. If the SDK is missing or the server has an unrelated startup error, the test fails with a different error — not a flaky pass, but a legitimate infrastructure failure. The test is honest about its dependencies.

**Verdict: ALL THREE TESTS ARE NON-FLAKY.**

---

## 5. RED EVIDENCE (pre-fix state)

The brief requires RED evidence that the default/off path attempted to import `theme_discovery` before the fix. This is established by:

1. **Code evidence (HEAD):** `beat_log.py:_assign_themes` line 77 unconditionally executes `from core.narrative.theme_discovery import select_theme_assigner`. Confirmed via `git show HEAD:core/narrative/beat_log.py` — the import has no guard.

2. **Module evidence:** `theme_discovery.py` line 30 has `import numpy as np` at module level. Any import of `theme_discovery` triggers NumPy load. Confirmed via `read_file`.

3. **Receipt evidence:** The brief documents two failures:
   - Native `log` did not return in 60 seconds → terminated, no event written. CLI completed in 0.9 seconds.
   - Fresh stdio MCP process timed out on `log` after 5 seconds. Second inbound frame released the first response — reproducing the C7-class symptom.
   - Faulthandler dump at 3 seconds placed the server event-loop thread at `beat_log.py::_assign_themes` importing `theme_discovery.py`.

4. **Mechanism evidence:** The hardening reconciliation (three independent analyses) confirmed that a subprocess inheriting stdout on Windows parks the ProactorEventLoop's outbound writer. NumPy's DLL load during import includes subprocess-like OS calls that trigger this class.

**RED evidence is sufficient.** The pre-fix state is documented by code structure, import chain, live receipts, and confirmed mechanism class.

---

## 6. GREEN EVIDENCE (post-fix state)

| Pin | Test | Result | Evidence |
|-----|------|--------|----------|
| 1. Default path never imports `theme_discovery` | `test_default_keyword_path_does_not_import_embedding_discovery` | **PASSED** | `attempted == []` |
| 2. Opt-in path still delegates to `select_theme_assigner` | `test_explicit_embedding_opt_in_still_uses_discovery_selector` | **PASSED** | `calls == [("routing verification", None)]`, `themes == ["embedding-opt-in"]` |
| 3. Fresh stdio MCP `log` returns in <5s | `test_fresh_stdio_mcp_log_returns_without_second_frame` | **PASSED** | Response arrived on first frame, no timeout |
| 4. Narrative regression | `test_narrative_beat_log.py` (5 tests) | **PASSED** | 5/5 |
| 5. Narrative regression | `test_narrative_slice1.py` (7 tests) | **PASSED** | 7/7 |
| 6. Narrative regression | `test_narrative.py` (5 tests) | **PASSED** | 5/5 |
| 7. Theme tests | `test_themes.py` (15 tests) | **PASSED** | 15/15 |
| 8. Theme discovery tests | `test_theme_discovery.py` (16 tests) | **PASSED** | 16/16 |
| 9. MCP door tests | `test_t078_w3_mcp_door.py` (3 tests) | **PASSED** | 3/3 |

**Combined: 3/3 M1-LITE pins + 51/51 regression = 54/54 GREEN.**

---

## 7. CRITIQUE (adversarial)

### What the fix gets right

1. **Addresses the mechanism, not the symptom.** The fix doesn't add a sleep, a retry, a second-frame probe, or a subprocess wrapper. It prevents the cold import that causes the wedge. This is root-cause-first per Daniel's standing doctrine.

2. **Zero behavior change.** The keyword themes produced by the default path are identical — same `get_theme_assigner()` call, same `ThemeAssigner.assign()`, same keyword tuples. The opt-in path is byte-identical — same `select_theme_assigner()` call, same embedding pipeline.

3. **Defense-in-depth preserved.** `select_theme_assigner()` inside `theme_discovery.py` STILL has its own flag check. If a future change accidentally imports it unconditionally again, the check catches it and returns the keyword assigner. Two layers: import guard (new) + runtime guard (existing).

4. **Test isolation is correct.** The unit tests monkeypatch at the Python level (no Redis, no real NumPy). The transport test uses isolated Redis DB 15 and `_AISETUP_TEST_ISOLATED`. No test pollution.

### What could be improved

1. **The `select_theme_assigner` flag check in `theme_discovery.py` is now dead code for the default path.** Since the import never happens when the flag is off, the check at line 190 never runs. This is fine as defense-in-depth, but the comment at line 180 ("DETERMINISTIC by config... flag off (default) -> fast keyword baseline") is misleading — it implies the function ITSELF handles the default case, when in reality the CALLER now handles it. The comment should note that the caller (`beat_log.py`) performs the primary guard and this check is the backup.

2. **No test for the edge case: `AKASHIC_EMBED_THEMES` set to an invalid value.** The fix checks for `("1", "true", "yes", "on")`. What about `"0"`, `"false"`, `"no"`, `"off"`, or a typo like `"ture"`? The test only checks `"0"` (off) and `"1"` (on). An invalid value falls through to the `else` branch (keyword assigner) — which is correct (fail toward the safe default), but untested.

3. **The `select_theme_assigner` function's own flag check uses different logic.** `beat_log.py` checks `embed_on = os.getenv(...).lower() in ("1", "true", "yes", "on")`. `theme_discovery.py:190` checks `os.getenv(...).lower() not in ("1", "true", "yes", "on")`. They disagree on the case where the env var is unset: `beat_log.py` → `embed_on = False` (correct, default off). `theme_discovery.py` → `"" not in (...) → True` → returns keyword assigner (also correct, but via different logic). If someone copies the beat_log.py check but inverts it wrong, they'd create a divergence. RECOMMEND: extract the flag check into a single shared function, e.g., `core.narrative.theme_assigner.embed_themes_enabled()`.

### What the fix does NOT address (correctly out of scope)

- **C7-4 broadly.** Other MCP tools that trigger subprocesses with inherited stdout (e.g., `boot` reaching `_git` helper) may still wedge. The hardening reconciliation addresses those separately with `stdin=subprocess.DEVNULL`. This fix is scoped to the MCP `log` tool specifically because its cold-import mechanism is distinct from the subprocess-inheritance mechanism — same symptom class, different root cause.
- **NumPy import cost in general.** The fix doesn't make NumPy import faster; it avoids importing it on the default path. When the operator opts into embedding themes, the cold import still happens and the MCP `log` tool may still take >1s on the first call after server start. This is acceptable: the operator opted in.
- **Theme assignment correctness.** The fix doesn't change which themes are assigned — same keyword tuples, same embedding model. It only changes WHERE the import happens.

---

## 8. MCP RECEIPTS

This seat is a ToolBox runner, not MCP-native. Evidence gathered via ToolBox reads:

| Tool | Target | Result |
|------|--------|--------|
| `read_file` | `research/briefs/mcp-log-single-frame-brief-2026-07-17.md` | OK |
| `read_file` | `core/narrative/beat_log.py` (working tree) | OK — fix confirmed |
| `git_show` | `HEAD:core/narrative/beat_log.py` | OK — pre-fix state confirmed |
| `read_file` | `core/narrative/theme_discovery.py` | OK — `import numpy as np` at line 30 confirmed |
| `read_file` | `core/narrative/theme_assigner.py` | OK — lightweight, no NumPy |
| `read_file` | `tests/test_mcp_log_single_frame.py` | OK — all 3 pins reviewed |
| `search_files` | `theme_discovery` imports across core/ | OK — only `beat_log.py` imports it |
| `run_command` | `pytest tests/test_mcp_log_single_frame.py` | OK — 3/3 GREEN |
| `run_command` | `pytest tests/test_themes.py tests/test_theme_discovery.py tests/test_narrative_beat_log.py tests/test_t078_w3_mcp_door.py` | OK — 39/39 GREEN |
| `run_command` | `pytest tests/test_narrative_beat_log.py tests/test_narrative_slice1.py tests/test_narrative.py` | OK — 17/17 GREEN |

No MCP-native calls attempted. All evidence gathered through ToolBox reads and pytest runs (exec family: isolated pytest).

---

## 9. FINAL VERDICT

**ROOT CAUSE: CLOSED.** The `_assign_themes` function in HEAD unconditionally imported `theme_discovery.py`, which eagerly imports NumPy. On Windows, the NumPy DLL load on FastMCP's synchronous event-loop thread parks the ProactorEventLoop writer until a second inbound frame arrives. The fix moves the `AKASHIC_EMBED_THEMES` opt-in check BEFORE the import, so the default path imports only the lightweight `theme_assigner.py`.

**SCOPE: MINIMAL.** One function, one file, ~13 lines. No API change. No behavior change. No new dependencies.

**OPT-IN: PRESERVED.** `AKASHIC_EMBED_THEMES=1` still imports `select_theme_assigner` and uses the embedding pipeline. Test 2 confirms.

**TESTS: NON-FLAKY.** Test 1 proves the import never happens (deterministic `__import__` recording). Test 2 proves the opt-in still works (fake module injection). Test 3 proves the real stdio transport returns on one frame (5s timeout, isolated Redis).

**REGRESSION: NONE.** 54/54 narrative + theme + MCP-door tests pass.

**RECOMMENDATION: SHIP.** This is a textbook M1-LITE repair: root-cause-first, scope-minimal, test-gated, opt-in-preserved.

### Improvement recommendations (non-blocking, for a follow-up)

1. Extract the `AKASHIC_EMBED_THEMES` flag check into a single shared function (`core.narrative.theme_assigner.embed_themes_enabled()`) so `beat_log.py` and `theme_discovery.py` use the same logic.
2. Add a test for invalid flag values (e.g., `AKASHIC_EMBED_THEMES=ture`) — assert they fall back to keyword assigner.
3. Update the `select_theme_assigner` docstring to note that the primary guard is now in the caller (`beat_log.py`), and this function's check is defense-in-depth.

---

*Filed under deepseek-review lock. Do not edit code. This verdict may be folded into the slice's verification gate.*
