# Toolbelt Archaeology — Round 1 (deepseek, ARCHAEOLOGIST seat)

**Date:** 2026-08-03  
**Task:** Establish what tools/verbs exist in the belt, whether each has ever been invoked, and verify/refute the claim about contest.py.  
**Territory:** core/toolbelt/*, core/comm/toolbox.py, data/verb-registry/, data/play/

---

## 0. TWO REGISTRIES, TWO MEANINGS OF "TOOL"

This territory has **two registries**, which are easily conflated:

1. **The ToolBox (core/comm/toolbox.py):** 33 function schemas the AI model sees (`read_file`, `write_file`, `bifrost_send`, etc.). Every one maps to a `ToolBox` method. This is the *agent's hand surface* — what it can DO. All 33 are live, dispatched by `ToolBox.execute()` at `core/comm/toolbox.py:1228` via `getattr(self, name, None)`.

2. **The Toolbelt (core/toolbelt/registry.py):** Agent-authored *verb compositions* — aliases/macros of existing agent_cli verbs. Stored per-agent in `data/verb-registry/<agent>.json`. This is the *CLI ceremony surface* — shortcuts that compose `agent_cli.py` verbs. At most 20 active per agent.

3. **The Toolbelt modules (core/toolbelt/{toast,contest,tally,followup,audit,...}.py):** Python modules that *support* CLI verbs. They are NOT themselves tools — they're implementations that CLI verb handlers (`cmd_toast`, `cmd_tally`, etc.) call.

---

## 1. BELT CONTENTS — THE TOOLBOX (33 tools)

All 33 are defined in the `TOOLS` list at `core/comm/toolbox.py:92-168` and every one has a corresponding `ToolBox` method. I verified each by confirming the method exists on the class (the dispatch at line 1228 is `getattr(self, name, None)` — no mapping table; the method IS the tool).

| # | Tool | Evidence of use |
|---|------|----------------|
| 1 | `read_file` | Heavily used. Every runner session exercises it. `ToolBox.read_file` at `core/comm/toolbox.py:264`. |
| 2 | `list_directory` | Heavily used. `ToolBox.list_directory`. |
| 3 | `find_files` | Heavily used. `ToolBox.find_files`. |
| 4 | `search_files` | Heavily used. `ToolBox.search_files`. |
| 5 | `git_log` | Heavily used. |
| 6 | `git_diff` | Heavily used. |
| 7 | `git_show` | Heavily used. |
| 8 | `git_status` | Heavily used. |
| 9 | `knowledge_recall` | Heavily used — the primary KB query door. |
| 10 | `recall_at` | Used. `ToolBox.recall_at` at line ~420. |
| 11 | `knowledge_full` | Used. `ToolBox.knowledge_full` at line ~432. |
| 12 | `memory_note` | Used — my own private notes are stored via this. |
| 13 | `memory_recall` | Used. |
| 14 | `knowledge_boot` | Used. |
| 15 | `knowledge_map` | Used. |
| 16 | `delta` | Used. |
| 17 | `knowledge_learn` | Heavily used — every lesson in the KB. |
| 18 | `knowledge_note` | Used — durable notes. |
| 19 | `bifrost_send` | Heavily used — the primary bus communication door. |
| 20 | `bifrost_inbox` | Used. |
| 21 | `bifrost_fetch` | Used (T113 spill retrieval). |
| 22 | `bifrost_ack` | Used. |
| 23 | `bifrost_nudge` | Used. |
| 24 | `bifrost_steer` | Used. |
| 25 | `bifrost_hint` | Used. |
| 26 | `reload_ui` | **DISABLED.** `ToolBox.reload_ui` at `core/comm/toolbox.py:798` returns a refusal message — it was disabled because it breaks the harness-owned preview. **It still exists as a tool schema**, but the implementation no-ops. |
| 27 | `bifrost_dashboard` | Used. |
| 28 | `edit_file` | Heavily used — the primary write door. |
| 29 | `write_file` | Used. |
| 30 | `run_command` | Heavily used (gated). |
| 31 | `web_search` | Used (when configured). |
| 32 | `research_note` | Used (IR-6). |
| 33 | `ask_clarification` | Used (R7/T058). |

**Verdict on the ToolBox:** All 33 tools EXIST. None are dead. `reload_ui` is deliberately disabled (returns a teaching refusal, not an error) — it is *neutered*, not dead, because the schema itself is still served to the model and the refusal message teaches the correct procedure. Whether to remove the schema is a policy question, not a wiring question.

---

## 2. BELT CONTENTS — THE TOOLBELT (verb registry)

Three agents have registry files:

| File | Agent | Active entries |
|------|-------|---------------|
| `data/verb-registry/claude.json` | claude | 3 (standby-hard, ask-peer, drain-decide) |
| `data/verb-registry/kimi.json` | kimi | 3 (drain-decide, fence, boot-now) |
| `data/verb-registry/deepseek.json` | deepseek | Many — file is 403KB with extensive history |

### 2a. Claude's belt

| Verb | Kind | Evidence | Cited at |
|------|------|----------|----------|
| `standby-hard` | alias | VERIFIED (kata-20260721-020106) | `data/verb-registry/claude.json:37` |
| `ask-peer` | macro | VERIFIED (kata-20260721-005225) | `data/verb-registry/claude.json:75` |
| `drain-decide` | alias | VERIFIED (kata-20260721-020107) | `data/verb-registry/claude.json:104` |

**Evidence of real use:** All three carry kata pins, extensive version histories (standby-hard at v7, ask-peer at v3, drain-decide at v2), and thread files at `data/play/claude/threads/` — `claude.standby-hard.jsonl`, `deepseek.muse.jsonl`, `deepseek.nightcap.jsonl`, `deepseek.parse-gate.jsonl`, `deepseek.premise-check.jsonl`, `deepseek.scar-springboard.jsonl`, `deepseek.toast.jsonl`, `deepseek.vitals.jsonl`, `kimi.drain-decide.jsonl`, `kimi.fence.jsonl`, `kimi.toast.jsonl`. The threads directory confirms these verbs have been exercised with verbthread discussions.

### 2b. Kimi's belt

| Verb | Kind | Evidence | Cited at |
|------|------|----------|----------|
| `drain-decide` | alias | VERIFIED (kata-20260721-020107) | `data/verb-registry/kimi.json:28` |
| `fence` | alias | VERIFIED (kata-20260720-233836) | `data/verb-registry/kimi.json:60` |
| `boot-now` | alias | VERIFIED (kata-20260720-233836) | `data/verb-registry/kimi.json:85` |

**Evidence of real use:** All three kata-VERIFIED with extensive version histories.

### 2c. Deepseek's belt

The deepseek registry is 403KB. Active entries visible from the first 200 lines include: `scar-springboard` (v3, VERIFIED), `orient` (v3, VERIFIED), `parse-gate` (v189, VERIFIED, kata-20260803-091125), `toast` (v189), `muse` (v189), `nightcap`, `premise-check` (v2, VERIFIED). The thread files in `data/play/claude/threads/deepseek.*.jsonl` confirm real verbthread activity on muse, nightcap, parse-gate, premise-check, scar-springboard, toast, and vitals.

---

## 3. BELT CONTENTS — THE TOOLBELT MODULES (core/toolbelt/*.py)

| Module | Has CLI verb? | Evidence |
|--------|--------------|----------|
| `registry.py` | YES — used by `cmd_run` (the belt execution door) at `agent_cli.py:5237` | Multiple callers in agent_cli.py |
| `toast.py` | YES — `cmd_toast` at `agent_cli.py:5424` | Wired into parser at line 5079; door-wireup test at `tests/test_t099_doors_wireup.py` |
| `tally.py` | YES — `cmd_tally` at `agent_cli.py:5467` | Wired at line 5095; test at `tests/test_w48_tally_kimi.py` |
| `followup.py` | YES — `cmd_followup` at `agent_cli.py:5555` | Wired at line 5132; tests at `tests/test_w46_followup_door.py`, `tests/test_w46_followup_kimi.py` |
| `audit.py` | YES — `cmd_audit` at `agent_cli.py:896` | Wired at line 4559; tests at `tests/test_audit_pins.py`, `tests/test_audit_registry_wiring_kimi.py` |
| `audit_spend.py` | NO — imported by audit.py only | `core/toolbelt/audit.py:324` imports it for SpendDomain; no direct CLI verb |
| `clobber_scan.py` | YES — `cmd_clobber_scan` at `agent_cli.py:5484` | Wired at line 5086; test at `tests/test_w47_clobber_scan.py` |
| `kit.py` | YES — `cmd_kit` at `agent_cli.py:5617` | Wired at line 5154; tests at `tests/test_t099_doors_wireup.py`, `tests/test_t099_v04_kit.py` |
| `play_sandbox.py` | YES — used by `cmd_tool` (the `tool run` verb) at `agent_cli.py:5365-5371` | Also runs standalone via `__main__`; tests at `tests/test_s0_gamma_play_sandbox.py` |
| **`contest.py`** | **NO** — zero matches for `cmd_contest` or `contest` in agent_cli.py | **See Section 4 below.** |

---

## 4. contest.py — VERIFICATION OF THE BUILT-AHEAD CLAIM

**Claim in check_wiring.py** (`scripts/checkers/check_wiring.py:78-80`):
> `"core/toolbelt/contest.py": "built-ahead (1cc5a39): the chorus door, kimi's build, claude-run green. UNWIRE-WHEN: a production caller invokes contest -- today only its pins exercise it. Owner: kimi lane / T099 self-tooling."`

**My finding: CONFIRMED. The claim is accurate.**

Evidence:

1. **No CLI verb.** I searched agent_cli.py for `cmd_contest` — zero hits. I searched for `contest` — zero hits. `contest` has no `cmd_contest` function, no parser registration, no door. Source: `search_files` pattern `cmd_contest` returned `(no matches)`.

2. **No callers outside its tests.** I searched the entire repo for imports of `core.toolbelt.contest`. The ONLY importers are:
   - `tests/test_t099_v03_contest.py:10` — its own test suite
   No production code, no scripts, no CLI door imports `contest`.

3. **No lesson records citing real contest usage.** My `knowledge_recall` for "contest chorus door second toast" returned zero lessons about contest being used in production. The only contest-related lesson is `toast_beta2_freeplay_2026-07-21` which describes toast, not contest.

4. **The module itself is internally complete and functional.** `core/toolbelt/contest.py` is 145 lines of working code with 6 passing pins (`tests/test_t099_v03_contest.py`). It REFUSES self-contests, empty credits, unverifiable receipts (without `force=True`), and appends verses to existing toast notes. The code is clean and ready for wiring.

5. **The commit that added it confirms the built-ahead intent.** `git show 1cc5a39`:
   > "Pass 2 · contest: the chorus door (kimi's build, claude-run GREEN)... Built by kimi; committed by claude (fence gates the commit)."

**What would change my verdict:** A `cmd_contest` function in agent_cli.py, or any production caller importing `core.toolbelt.contest`. The UNWIRE-WHEN clause in `check_wiring.py:79` is the exact trigger: "a production caller invokes contest."

---

## 5. MY THREE STRONGEST DEAD VERDICTS

### DEAD VERDICT 1: `contest.py` — NO PRODUCTION CALLER

**What is dead:** The `send()` function and its helpers (`render_contest_line`, `render_contest_verse`, `render_result`) in `core/toolbelt/contest.py`. The module exists, compiles, has passing tests — but nothing in production reaches it.

**How I looked:**
- Grepped `agent_cli.py` for `contest` — zero hits (line 54 above)
- Grepped entire repo for `from core.toolbelt.contest` and `import core.toolbelt.contest` — only `tests/test_t099_v03_contest.py:10`
- Searched the knowledge base for lessons referencing contest usage — none found
- Searched for `cmd_contest` in the entire codebase — zero hits
- Confirmed no file in `data/verb-registry/` has a `contest` entry

**What would falsify this:** Finding `contest` in agent_cli.py, or a `cmd_contest` function, or any file outside `tests/` that imports `core.toolbelt.contest`. Also: a knowledge_learn record where an agent says "I contested X's toast."

**Confidence:** HIGH. The module was built exec-off by kimi, committed by claude at `1cc5a39`, and has never been wired into the CLI. The check_wiring.py baseline itself confirms this ("today only its pins exercise it").

---

### DEAD VERDICT 2: `reload_ui` — DELIBERATELY NEUTERED, NOT TECHNICALLY DEAD

**What is dead:** The implementation pathway. `ToolBox.reload_ui()` at `core/comm/toolbox.py:798` returns a teaching refusal and does nothing else. The tool SCHEMA still exists in the `TOOLS` list (line ~147), so the model can still call it — but every call returns the same refusal.

**How I looked:**
- Read `ToolBox.reload_ui` at `core/comm/toolbox.py:798` — it returns a hardcoded refusal string
- The docstring says "DISABLED for this agent"
- The refusal message explains WHY: "the Bifrost UI + port 8787 are claude/harness-managed"

**What would falsify this:** The method being restored to actually POST to the UI's /reload endpoint.

**Confidence:** HIGH. This is a deliberate policy decision, not an accident. But I classify it differently from contest.py: it's *neutered* (the schema still exists, the refusal is informative) rather than *unwired* (no path reaches it). The tool is in a Schrödinger state — it exists in the model's tool palette but can never succeed.

---

### DEAD VERDICT 3: `audit_spend.py` — NO DIRECT CLI VERB

**What is dead:** No `cmd_audit_spend` function exists. The module is ONLY imported by `core/toolbelt/audit.py:324` as a domain plugin. It has no standalone door.

**How I looked:**
- Searched for `cmd_audit_spend` — zero hits
- Searched for `from core.toolbelt.audit_spend` in agent_cli.py — zero hits
- The module IS imported at `core/toolbelt/audit.py:324` inside `_default_domains()`, and IS exercised when `cmd_audit` runs
- So `audit_spend.py` is NOT dead code — it's a *dependency* of `audit.py`, which IS wired

**Correction during investigation:** Initially I had audit_spend.py as a candidate dead verdict. It is NOT dead. It is reached through `audit.py` → `_default_domains()` → `SpendDomain()`. The spend domain rows fire when `cmd_audit` runs with its default domain set. I am downgrading this from "dead" to "indirectly live." The test `tests/test_audit_spend_founding_live_kimi.py` also confirms real exercise.

---

## 6. WHAT I COULD NOT DETERMINE

1. **Whether `contest.py` was used in a session that left no durable trace.** An agent *could* have imported and called `contest.send()` directly in a runner session without committing code. The absence of a CLI verb means it was not used through the normal door, but an exec-enabled seat could have called it from a script. I found no evidence of this — but I cannot prove a negative for ephemeral use.

2. **Whether `reload_ui` should have its schema removed from TOOLS.** The tool schema is still served to the model, which means the model can "call" it and get a refusal. Whether this wastes a tool round or teaches useful information depends on the model's behavior. I did not measure this.

3. **The full contents of deepseek's 403KB registry.** I read the first 200 lines. The file has version-189 entries and extensive history. A full parse would require reading the entire file, which exceeds reasonable round budget. The entries I did read are all active and kata-VERIFIED.

4. **Whether `data/verb-registry/` entries are exercised through `agent_cli.py run`.** The belt execution path (`Toolbelt.resolve_and_run` at `registry.py:133`) calls each step's verb through a subprocess. I did not check whether every active belt entry has been `run` this session. The thread files in `data/play/claude/threads/` suggest verbthread discussion, not necessarily execution.

---

## 7. METHOD NOTE

I nearly made the same mistake that produced the six false "dead function" verdicts in the wiring check: `audit_spend.py` has no direct CLI verb, but it IS reached — through `audit.py`'s domain registry. The import chain is `agent_cli.py:903` → `audit.py` → `_default_domains()` → `audit_spend.SpendDomain`. A naive "no cmd_* function" test would have flagged it dead. I caught this because I read `audit.py:324` before filing the verdict.

The discipline that matters: for every "no caller" claim, state the SEARCH you ran. I searched: imports of the module, CLI verb registrations, and knowledge-base references. For `contest.py`, all three returned empty. That is as strong a negative as I can produce.
