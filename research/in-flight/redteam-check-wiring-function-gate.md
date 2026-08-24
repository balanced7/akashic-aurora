# Red-team assessment: check_wiring.py function-level gate — 5 attacks

**Reviewer:** ARCHAEOLOGIST (deepseek-review seat)
**Date:** 2026-08-04
**Source:** Full source read of `scripts/checkers/check_wiring.py` (530 lines) + `wiring_function_baseline.json` (108 entries)
**Method:** Cite file:line for every claim. A thing is dead only if nothing reaches it; otherwise say so plainly.

---

## VERDICT

All five attacks are **mechanically correct** — the source at the cited lines does exactly what the red-team report says. However, three of them (A1, A2, A5) are **explicitly documented limitations**, not bugs. The other two (A3, A4) are **unstated consequences** of the "deliberately weak evidence" design — the gate's own header says it accepts them.

---

## A1 — EVASION: `def` inside `if False:` invisible to `public_defs`

**MECHANICALLY CORRECT.** Source evidence:

- `public_defs` at line 316: `for node in tree.body:` — iterates top-level nodes only.
- Line 317: `if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):` — exact type check on `tree.body` elements, NOT recursive.
- An `If` node is neither `FunctionDef` nor `ClassDef` (lines 317, 319), so it is skipped on both branches.
- No `ast.walk(tree)` is used in `public_defs`. `reference_sites` uses `ast.walk` (line 341), but `public_defs` does not.

**However, this is a DOCUMENTED limitation, not a bug.** Lines 302-303 in the docstring: "Top level and one level into a class. Nested defs are private by construction." The gate's own design says: nested functions are excluded by design (they are private), and the mechanism for excluding them is the non-recursive `tree.body` walk. The fact that a `def` inside `if False:` is also excluded is a consequence of this design choice, not an oversight.

**Classified as: LIMITATION (documented), not a defect.** The design trade-off is: we skip `ast.walk` to avoid surfacing genuinely nested (private) functions, and we accept the blind spot for conditionally-defined functions.

**Severity:** LOW. A function inside `if False:` is a contrived attack. An accidental instance (e.g., `if os.environ.get("ENABLE_X"): def handler():`) is possible but rare.

---

## A2 — EVASION: `def` inside `except ImportError:` invisible to `public_defs`

**MECHANICALLY CORRECT.** Same structural gap as A1. The `Try` node at `tree.body` level is neither a `FunctionDef` nor a `ClassDef`, so `public_defs` skips it at line 317/319. A `FunctionDef` inside an `ExceptHandler` is invisible.

**Also a documented limitation.** Line 302-303 again: nested defs are private by construction. The `except ImportError: def fallback():` pattern nests a function inside a `Try` node — it's nested by the AST structure, and the gate excludes nested functions.

**This pattern is more dangerous than A1** because `try/except ImportError: def fallback()` IS idiomatic Python. An engineer writing a fallback for an optional dependency creates this blind spot accidentally. The current codebase has one `except ImportError:` at `core/foundation/redis_connection.py:47`, but it sets a boolean flag rather than defining a function — so no existing instance, but the pattern is plausible.

**Classified as: LIMITATION (documented).** Same design trade-off as A1.

**Severity:** MEDIUM. Idiomatic pattern, plausible accidental trigger.

---

## A3 — FALSE POSITIVE: Local variable shadows baseline function name

**MECHANICALLY CORRECT.** Source evidence:

- `reference_sites` at line 341-342: `if isinstance(node, ast.Name): out.append((node.id, ln))` — records EVERY `ast.Name.id` in every production file, with no distinction between a local variable, a function call, or an import.
- `unwired_functions` at line 375: `wired = any(mod != m or not (lo <= ln <= hi) for mod, ln in sites.get(name, ()))` — any reference in a DIFFERENT file counts as wiring.
- `stale_function_baseline` at line 383: `live = {f"{m}::{n}" for m, n, _lo in unwired_functions(...)}` — then at line 384: `return sorted(e for e in baseline if e not in live)` — baseline entries NOT in `unwired_functions` output are reported stale.

So: a local variable `covers = os.environ.get(...)` in `scripts/deepseek_chat.py` → `reference_sites` records `("covers", ln)` → `unwired_functions` sees it in a different file from `core/comm/bifrost_api.py` → `bifrost_api.py::covers` is no longer in the unwired list → `stale_function_baseline` reports it as "now wired" → operator removes it from the baseline → the dead function silently escapes.

**Target from the baseline:** `core/comm/bifrost_api.py::covers` at `wiring_function_baseline.json` line 7. This entry is in the baseline specifically because NO production file references it today. A single `ast.Name(id="covers")` in any production file changes that.

**This is an UNSTATED consequence of the "deliberately weak evidence" design, but it IS consistent with that design.** The header at lines 287-296 states: "EVIDENCE IS DELIBERATELY WEAK, and that is the design. 'Referenced' means MENTIONED BY NAME on a production path." A local variable IS a mention by name. The gate trades false negatives (dead functions that look wired) for zero false positives (functions reported dead that are actually called). A local variable with the same name IS a false negative — but the gate's design explicitly accepts that class of error.

**Classified as: LIMITATION (consistent with documented design), not a defect.** The gate's header explicitly says "an unused import counts as wiring" — a local variable is the same class of false negative.

**Severity:** MEDIUM. Requires the operator to manually remove the baseline entry after seeing the WARN. The operator SHOULD verify the "now wired" claim before removing — the WARN is an invitation to check, not an automatic removal. A vigilant operator catches this.

---

## A4 — EVASION: Unrelated `obj.attr` access "wires" dead same-named function

**MECHANICALLY CORRECT.** Source evidence:

- `reference_sites` at line 343-344: `elif isinstance(node, ast.Attribute): out.append((node.attr, ln))` — records EVERY `ast.Attribute.attr` in every production file, with no distinction between a method call and a data attribute access.
- Same wiring logic as A3: any reference in a different file counts.

So: `cfg.clear_all` in `scripts/deepseek_chat.py` → `reference_sites` records `("clear_all", ln)` → `core/comm/context_hints.py::clear_all` (baseline entry 10) is no longer reported unwired → `stale_function_baseline` reports it stale → operator removes it → dead function escapes.

**Same class as A3: consistent with the "deliberately weak evidence" design.** The gate accepts ANY `ast.Attribute.attr` match as wiring. The header documents this: "'Referenced' means MENTIONED BY NAME on a production path — call, attribute, bare name, import alias, keyword argument, or an exact-match string constant."

**This is actually the most plausible accidental trigger.** Common words like `clear_all`, `covers`, `release`, `shutdown`, `intents` appear naturally as object attributes. The baseline contains many such common-English names. An honest engineer writing `record.covers` or `config.clear_all` accidentally "wires" the dead function.

**Classified as: LIMITATION (explicitly documented).** The header at line 288 says attributes count as references.

**Severity:** MEDIUM (higher accidental likelihood than A3, but same mechanism).

---

## A5 — FALSE POSITIVE: String concatenation defeats `Constant` exact-match

**MECHANICALLY CORRECT.** Source evidence:

- `reference_sites` at line 345-346: `elif isinstance(node, ast.Constant) and isinstance(node.value, str): out.append((node.value, ln))` — matches EXACT string values only.
- `"handle_" + verb_suffix` produces TWO `Constant` nodes: `Constant("handle_")` and whatever `verb_suffix` resolves to at runtime. Neither matches `"handle_special_event"` exactly. No constant folding.
- The gate itself documents this: line 294-295: "a name assembled at runtime ('declare_' + verb) is invisible."

**Classified as: LIMITATION (explicitly documented), not a defect.** The gate's own header states this limitation.

**The attack scenario is less plausible than stated.** The red-team report says `getattr(mod, "han" + "dle")` — that's conspicuously adversarial. The `"handle_" + suffix` pattern IS realistic for dispatch code, but it requires a live `getattr` call site that the gate already can't see. This is the same old problem: dynamic dispatch is invisible to static analysis. The gate documents this.

**Severity:** LOW-MEDIUM. The limitation is real but documented. A live function called ONLY through `getattr` with concatenated names is a pre-existing blind spot — the baseline exists precisely for this class of function.

---

## TAXONOMY

The five attacks fall into three classes, not five:

| Class | Attacks | Mechanism | Documented? |
|-------|---------|-----------|-------------|
| **Non-recursive `public_defs`** | A1, A2 | `tree.body` iteration skips functions nested inside `If`/`Try`/`With`/`For`/`While` nodes | Yes (line 302: "Nested defs are private by construction") |
| **Over-broad `reference_sites`** | A3, A4 | Any `ast.Name` or `ast.Attribute` in any production file counts as wiring, even if it's a local variable or unrelated attribute | Yes (line 287: "EVIDENCE IS DELIBERATELY WEAK") |
| **Exact-match `Constant`** | A5 | String concatenation defeats exact-match; dynamic dispatch is invisible | Yes (line 294: "a name assembled at runtime... is invisible") |

---

## WHAT THIS MEANS

None of these are bugs. They are all consequences of the gate's explicitly documented design trade-offs:

1. **Non-recursive `public_defs`** trades completeness (missing conditionally-defined functions) for precision (not surfacing genuinely private nested functions). The gate calls this out in its own docstring.

2. **Over-broad `reference_sites`** trades false negatives (dead functions that look wired) for zero false positives (functions reported dead that are actually called). The header says this explicitly, and it recites the lesson twice (control_channel.py, door_probe.py): "a false positive here is expensive twice over, because the only remedy this file offers is an EXCEPTIONS entry, and a guard that cries wolf gets fed exceptions until it guards nothing."

3. **Exact-match `Constant`** is a hard limitation of static AST analysis — the gate can't constant-fold, and it says so.

The ARCHAEOLOGIST's finding: **the gate is working as designed.** The attacks exploit the design's known blind spots, not implementation errors. The design is explicit about its weaknesses; a reader of the source would find them documented at lines 287-303.

The real question is not "can these attacks work" (they can) but "are these blind spots acceptable given the gate's purpose?" The gate's purpose is to **ratchet** — to prevent NEW dead capability from accumulating. A1/A2/A5 let dead capability hide; A3/A4 let live capability look dead. The gate's design explicitly chooses to accept A3/A4-class errors (false negatives in `reference_sites`) to avoid A5-class errors (false positives in the report). It also chooses to accept A1/A2-class errors (missing nested functions) to avoid surfacing private helpers as dead public functions.

**Recommendation:** No code change. The design is sound for its stated purpose (a ratchet, not a complete census). If the team wants stronger guarantees, the remedy is:
- For A1/A2: `ast.walk(tree)` in `public_defs`, with a filter that excludes functions nested inside other functions (not control flow). This would catch `if`/`try`-nested functions while still excluding genuine private helpers.
- For A3/A4: This is harder. Distinguishing a local variable from a function call requires name resolution (scope analysis). The gate would need to know whether `covers` on line N of file X refers to the local scope or to `bifrost_api.covers`. That's a full import resolver — a different tool entirely.
- For A5: Constant folding of string concatenation for `getattr` targets. Doable but narrow benefit.
