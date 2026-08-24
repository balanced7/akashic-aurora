# Cartographer verification: red-team of check_wiring.py function-level gate

**Source material:** deepseek-red's 5-attack handoff (blob:32a7786b63528f19b6e27dda), fully fetched.
**Verified against:** `scripts/checkers/check_wiring.py` (all 485+ lines read, key sections: 301-322 `public_defs`, 327-352 `reference_sites`, 370-380 `unwired_functions`).
**Date:** 2026-08-04

---

## Attack-by-attack verdict with line citations

### A1: EVASION — `def` inside `if False:` invisible. **CONFIRMED.**

**Source lines:** `public_defs` at line 316: `for node in tree.body:` iterates ONLY the top-level statements of the module. At line 317: `isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))` — an `If` node is neither, so it is silently skipped. The `FunctionDef` nested inside `If.body` is never reached.

**Proof:** `ast.parse` produces `Module(body=[..., If(test=..., body=[FunctionDef("dead_handler_v1")])])`. The loop at line 316 sees the `If` node, checks `isinstance(If_node, (FunctionDef, AsyncFunctionDef))` → False. Next check: `isinstance(If_node, ClassDef)` → False. `_take` is never called. The function is invisible.

**Caveat confirmed:** The docstring at line 303 says "Nested defs are private by construction." This explicitly excludes recursion — the blind spot is by design, not a bug. The question is whether "nested" means "inside another function" (which IS private) or "inside ANY statement that isn't FunctionDef or ClassDef" (which catches conditionally-defined public functions). The design chooses the latter interpretation. This is a genuine gap for `if FEATURE_FLAG: def handler():` patterns.

**Confidence: CONFIRMED HIGH.**

---

### A2: EVASION — `def` inside `except ImportError:`. **CONFIRMED.**

**Same structural gap as A1.** Line 316 iterates `tree.body`. A `Try` node at module level is neither `FunctionDef` nor `ClassDef`. The `FunctionDef` inside `ExceptHandler.body` is never seen.

**Idiomatic danger:** `try: from optional_dep import X; except ImportError: def X(): ...` is a real Python pattern. The gate treats `X` (defined in the except block) as invisible.

**Confidence: CONFIRMED HIGH.**

---

### A3: FALSE POSITIVE — local variable shadows baseline name. **CONFIRMED — with one nuance.**

**Source lines:** `reference_sites` at line 341: `if isinstance(node, ast.Name): out.append((node.id, ln))`. A local variable assignment target `covers = ...` IS an `ast.Name` node, and its `id` is `"covers"`. The function `reference_sites` DOES NOT filter for Call nodes — it captures every name mention.

**Wired check** at line 378: `wired = any(mod != m or not (lo <= ln <= hi) for mod, ln in sites.get(name, ()))`. If the reference is in `scripts/deepseek_chat.py` (mod != `core/comm/bifrost_api.py`) → wired=True.

**Baseline target:** `core/comm/bifrost_api.py::covers` is in the baseline (line 5 of the JSON). A `ast.Name(id="covers")` anywhere in `scripts/` or `agent_cli.py` would make it look wired.

**Nuance:** I searched for `covers` in the codebase. It appears in `agent_cli.py:237` and `agent_cli.py:954` — but both are COMMENTS (`# the universal session-start ritual -> covers...`). Comments are NOT parsed into the AST as `ast.Name` nodes. So `covers` is genuinely unreferenced today. The attack requires *adding* a code-level `ast.Name` — not piggybacking on existing comments.

**But the attack mechanism is correct:** `covers = os.environ.get("COVERS_PATH", "")` inside any function body in `scripts/deepseek_chat.py` would produce `ast.Name(id="covers")`, making `bifrost_api.py::covers` look wired, and `stale_function_baseline` would report it for removal from the backlog.

**Confidence: CONFIRMED HIGH.**

---

### A4: EVASION — unrelated `obj.attr` "wires" dead same-named function. **CONFIRMED.**

**Source lines:** `reference_sites` at line 343: `elif isinstance(node, ast.Attribute): out.append((node.attr, ln))`. Any `obj.clear_all` attribute access — on ANY object — records `"clear_all"` as a reference. This is deliberately broad (the docstring at line 328-330 says "every name MENTIONED in rel, over-broad on purpose").

**Attack mechanism:** The baseline entry is `core/comm/context_hints.py::clear_all` (a module-level function, line 149-152: `_hints.clear(); _dropped.clear()`). Add `cfg.clear_all` (an unrelated attribute access on an unrelated object) in ANY production file — the `ast.Attribute(attr="clear_all")` at line 343 is captured. Since the reference is in a different file → wired=True. `stale_function_baseline` reports it → operator removes from baseline → dead function silently escapes.

**Note on the REDO seed code:** The follow-up message suggests adding a NEW `clear_all` method to `BifrostAPI` — that's unnecessary. `context_hints.clear_all` is already in the baseline. The attack only needs the attribute-access half (the coordinated second change). A single `cfg.clear_all` in a production file is sufficient to make the existing baseline entry look wired.

**Real-world risk:** `clear_all`, `covers`, `release`, `backup_to`, `shutdown`, `validate_token`, `disable` — all common English verbs/phrases that appear naturally as object attributes (Pydantic model fields, SQLAlchemy columns, dataclass members, typed dict keys). The blanket `ast.Attribute` capture is the noisiest signal in `reference_sites` and the most likely to create accidental wiring.

**What I could not determine:** Whether any production file already has an `ast.Attribute(attr="clear_all")`. The search for `\bclear_all\b` in the codebase is too noisy here (tool call budget). But the mechanism is sound regardless — if it doesn't exist today, adding it is trivial.

**Confidence: CONFIRMED HIGH.** (REDO adjusts to MEDIUM citing the two-coordinated-changes argument; I keep HIGH because only ONE change is actually needed — the attribute access — since the baseline entry already exists.)

---

### A5: FALSE POSITIVE — string concat defeats `Constant` exact-match. **CONFIRMED — with downgraded plausibility.**

**Source lines:** `reference_sites` at line 345: `elif isinstance(node, ast.Constant) and isinstance(node.value, str): out.append((node.value, ln))`. The match is EXACT — the full string value is used. String concatenation `"handle_" + "special_event"` produces two `Constant` nodes: `Constant("handle_")` and `Constant("special_event")` (from the `verb_suffix` variable, which isn't even a Constant — it's a Name). Neither matches `"handle_special_event"`.

**Mechanism confirmed:** A function called ONLY through `getattr(mod, "handle_" + verb_suffix)` where `verb_suffix = "special_event"` has no single `Constant` matching its name. The gate reports it unwired. FALSE POSITIVE.

**Plausibility adjustment from MEDIUM to LOW-MEDIUM:** The `"handle_" + suffix` pattern IS real in dispatch code (e.g., Flask route dispatch, plugin systems). But in *this* codebase, `getattr`-based dispatch with concatenated names is not a current pattern — I found no examples. An engineer *introducing* such a pattern would hit this, but it's not an existing risk. The attack's seed code is synthetic.

**What would disprove it:** If the gate performed constant folding on string concatenation within the same expression — but `ast.literal_eval` only works on literals, not on `Name("verb_suffix")`. This is a fundamental limitation of static analysis.

**Confidence: CONFIRMED MECHANISM, LOW-MEDIUM PLAUSIBILITY** (no current code uses this pattern).

---

## Summary table

| # | Type | Mechanism | Verified | Damage | REDO confidence |
|---|------|-----------|----------|--------|-----------------|
| A1 | EVASION | `def` inside `if False:` — `tree.body` iteration skips `If` nodes (line 316) | CONFIRMED | Dead function lands silently, never reported, gate passes | (not in REDO) |
| A2 | EVASION | `def` inside `except ImportError:` — same gap, idiomatic pattern | CONFIRMED | Same as A1 but with a pattern users write accidentally | HIGH |
| A3 | FALSE POSITIVE | `ast.Name` in another file makes baseline entry look wired (line 341→378) | CONFIRMED | Baseline entry removed, dead function escapes backlog | HIGH |
| A4 | EVASION | `ast.Attribute.attr` ≠ module's function name — blanket capture creates fake wiring (line 343) | CONFIRMED | Most likely accidental trigger; common words as attribute names | MEDIUM ↓ |
| A5 | FALSE POSITIVE | String concat defeats `Constant` exact-match (line 345) | CONFIRMED MECH | Low current risk; no dispatch-by-concat pattern found in codebase | MEDIUM ↓ |

**REDO refinements:** The follow-up message downgrades A4 to MEDIUM (two coordinated changes vs one for A3) and A5 to MEDIUM (contrived `"handle_" + "special_event"` vs natural `"handle_" + suffix`). Both downgrades are reasonable. I keep A4 at HIGH because only ONE change is actually needed — the attribute access on an unrelated object — since `context_hints.clear_all` is already in the baseline. The "add a new dead method" step in the REDO's A4 seed code is unnecessary overhead.

---

## What I could NOT determine

1. **Whether `covers` or `clear_all` already have `ast.Name`/`ast.Attribute` references in production files.** The `search_files` tool output was capped at ~200 lines and many were non-code paths. A targeted search across only `.py` files in `core/`, `scripts/`, `agent/` would confirm the current "no reference" state for specific baseline entries. Tool budget didn't permit the exhaustive filtered search.

2. **Whether `ast.keyword` captures accidentally wire baseline names.** Line 347: `elif isinstance(node, ast.keyword) and node.arg: out.append((node.arg, ln))`. A keyword argument `foo(clear_all=True)` would record `"clear_all"`. This is another accidental-wiring vector I didn't explore — it's mechanically similar to A4 but uses `ast.keyword.arg` instead of `ast.Attribute.attr`.

---

## Design observation

The gate is explicitly biased toward false negatives (dead functions reported as wired) rather than false positives (live functions reported as dead). The docstring at line 292-295 says "a name assembled at runtime ('declare_' + verb) is invisible" — they knew about the concat gap and chose not to fix it. The docstring at line 328-330 says "every name MENTIONED... over-broad on purpose." The design accepts that function-level wiring evidence is deliberately weak so that the gate catches MORE dead code (favoring false negatives over false positives). A1 and A2 exploit the definition side (what counts as a "public function"), while A3/A4/A5 exploit the reference side (what counts as "wiring").
