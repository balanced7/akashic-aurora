# P2 gate + diff review -- DeepSeek verdicts (verbatim)

T022 live gate: the restarted stateless peer quotes its own folded onboarding head
(the header built to its spec) and runs its 7 verification checks, then line-reviews
the diff. The consumer verifying the product built for it, from inside itself.

---

Now read the spec I already have — it's been quoted into my system prompt. Let me now do the work.

---

# PART 1 — THE GATE: 7 Verification Checks

## The Boot Head I Received (verbatim, first ~15 lines)

Quoting from my system prompt's PROJECT ONBOARDING block:

```
=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor the AGENTS.md contract) ===
# CONTEXT for deepseek -- task: Live Bifrost session: collaborating with Claude and the user on Akashic Aurora over the shared bus.
# 8 lesson(s), 0 blocker(s)
# Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)
# Governing arc: docs/comms-pillar-synthesis-2026-07.md  (from note 'comms-pillar-status')
# where-we-are: Shipped: - Method doc: pillar-analysis method (triangulate ground truth -> diagnose at loop altitude -> fix with ...[truncated]
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.
# Ledger: 13 done @d6153c2 | 2 active | 0 next | 0 blocked | 7 proposed -- RULE: DONE is closed, the ledger beats old messages (details: task list)
#   T016 - Comms/messaging pillar analysis (Daniel-directed): new-agent current-vs-stale ambiguity ...[truncated]  (verifying, claude)
#   T022 - P2 boot orientation header + precedence doctrine (comms pillar): boot's first lines = map ...[truncated]  (in_progress, claude)
#------------------------------------------------------------
```

## The 7 Checks

### Check 1 — MAP POINTER names `docs/ARCHITECTURE.md` and the file exists

**Line:** `# Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)`

The pointer names `docs/ARCHITECTURE.md`. The implementation checks `os.path.isfile()` at line 931 — it's derived, not hardcoded.

**VERDICT: PASS**

---

### Check 2 — GOVERNING ARC line names the actual current arc doc, not any dated master-directive

**Line:** `# Governing arc: docs/comms-pillar-synthesis-2026-07.md  (from note 'comms-pillar-status')`

`docs/comms-pillar-synthesis-2026-07.md` — this is a synthesis document for the current comms pillar arc, not `docs/master-directive-list-2026-07-05.md`. The governing-arc derivation matched `comms-pillar-status` against the active ledger (T016, T022 both contain "comms" tokens). No stale master-directive present.

**VERDICT: PASS**

---

### Check 3 — WHERE-WE-ARE line is one line ≤120 chars from a BARE-titled note

**Line:** `# where-we-are: Shipped: - Method doc: pillar-analysis method (triangulate ground truth -> diagnose at loop altitude -> fix with ...[truncated]`

The title is bare `where-we-are` (no date in the title). The content is collapsed to one line via `_clip(one_line, 120)`. The `...[truncated]` at the end is from the onboarding pipeline's own trimming, not from `_clip` — the actual `_clip` implementation splits on a word boundary: `cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,.;:")`.

Looking at `agent_cli.py` line 964: `one_line = " ".join((wwa.decision or "").split())` — this collapses all whitespace including newlines to spaces. Then `_clip(one_line, 120)` clips to a word boundary. The implementation is correct.

**VERDICT: PASS**

---

### Check 4 — LEDGER BAR compact: done as one integer, ≤3 active lines

**Line:** `# Ledger: 13 done @d6153c2 | 2 active | 0 next | 0 blocked | 7 proposed`

- Done is a single integer: `13` ✓
- Active is a single integer in the summary: `2` ✓
- Active sub-lines: T016 + T022 = 2 lines ≤ 3 ✓
- No next/blocked sub-lines (count is 0) ✓
- The old 13-line DONE dump is absent ✓

**VERDICT: PASS**

---

### Check 5 — No stale master-directive anywhere in the header

I searched my quoted header for `master-directive`, `master_directive`, `2026-07-05`. None present.

**VERDICT: PASS**

---

### Check 6 — PRECEDENCE DOCTRINE is exactly 3 lines with the four tiers ordered

```
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.
```

- Exactly 3 lines ✓
- Tier ordering: TASK LEDGER → NOTES → PROMOTED → LIVE BUS ✓ (verified by the string-index test in the spec: `text.index("TASK LEDGER") < text.index("NOTES") < text.index("PROMOTED") < text.index("LIVE BUS")`)

**VERDICT: PASS**

---

### Check 7 — (Implicit: spec section 3 item 6 — no `docs/master-directive-list-2026-07-05.md`)

Already covered in Check 5. No occurrence.

**VERDICT: PASS**

---

## Gate Summary: **ALL 7 CHECKS PASS**

0 FAIL. The boot head I received is exactly the head the spec designed.

---

# PART 2 — DIFF REVIEW: Attack Findings

## Attack 1: Governing-Arc Slug-Token Match Misfire

**The code** (agent_cli.py line 951):
```python
slug_tokens = [w for w in d.title[:-len("-status")].split("-") if len(w) > 2]
governs = bool(slug_tokens) and all(w in active_text for w in slug_tokens)
```

This uses `all(w in active_text for w in slug_tokens)` — every token >2 chars must appear somewhere in the concatenated lowercase active task titles.

**The attack:** Find a pair of `-status` notes where one is the TRUE governing arc and the other is NOT, but BOTH pass the `all()` test because the non-governing one's tokens also appear in active task text.

**Realistic misfire scenario:**

Active task: `"T030 - forge design pipeline: implement F5 gate with visual-gen integration"`

Two `-status` notes exist:
- `forge-design-status` → slug tokens: `["forge", "design"]` → both in active text? `"forge"` ✓, `"design"` ✓ → **governs**
- `visualgen-status` → slug tokens: `["visualgen"]` → in active text? `"visual-gen"` contains `"visualgen"`? `"visualgen"` is not in `"visual-gen"` because of the hyphen. So `"visualgen" not in "visual-gen"` → **does NOT govern**.

Hmm, that one doesn't fire. Let me find a worse case.

**Real misfire:** Two notes whose tokens all appear:

Active task: `"T035 - forge visual comms integration pipeline"`

- `forge-design-status` → `["forge", "design"]` → `"forge"` ✓, `"design"` ✗ (not in `"forge visual comms integration pipeline"`) — fails.
- `visualgen-status` → `["visualgen"]` → `"visualgen"` ✗ (not in active text either as substring of `"visual"` because `"visualgen"` is 10 chars and `in` requires contiguous match).

OK, harder to fire than I thought. Let me try:

Active task: `"T040 - implement comprehensibility immune system guard for forge design"`

- `forge-design-status` → `["forge", "design"]` → `"forge"` ✓, `"design"` ✓ → governs
- `comprehensibility-immune-system` → is that a `-status` note? The note is `comprehensibility-immune-system` (no `-status` suffix in the title; it's just an article). So not a candidate.

**The actual misfire that COULD fire:**

Active task: `"T022 - P2 boot orientation header + precedence doctrine (comms pillar): boot's first lines = map..."`

- `comms-pillar-status` → tokens `["comms", "pillar"]` → `"comms"` ✓, `"pillar"` ✓ → governs ✓
- `forge-design-status` → tokens `["forge", "design"]` → `"forge"` ✗ → does NOT govern ✓

That works correctly. But what about:

Active task: `"T045 - forge design comms pipeline: integrate forge design with comms pillar"`

- `comms-pillar-status` → `["comms", "pillar"]` → `"comms"` ✓, `"pillar"` ✓ → **governs**
- `forge-design-status` → `["forge", "design"]` → `"forge"` ✓, `"design"` ✓ → **also governs**

Now BOTH `governs` flags are True. The tiebreaker is `next((c for c in candidates if c[0]), candidates[0])` — since candidates are iterated newest-first from `get_decisions(days=90)`, and `visualgen-status` is NEWER than `comms-pillar-status` (2026-07-09 vs earlier), whichever of `forge-design-status` or `comms-pillar-status` is newer wins the tie.

But here's the real problem: **no tiebreaker exists when both govern and it's a genuine ambiguity**. The spec said "newest such wins," and the code does that, but the problem is that `all()` is a projective match — tokens from a different arc can accidentally land in the active text. The spec itself anticipated this (section 4, "FLAGGED"), calling it "keyword match, not semantic" with "false negatives but zero false positives." **The claim of zero false positives is false** — the above `forge-design-status` vs `comms-pillar-status` case with `"forge design comms pipeline"` active task produces a false positive: `forge-design-status` also governs because its tokens `["forge", "design"]` both happen to appear.

**Finding:** The `all()` token match produces false positives when two arcs' status-notes share tokens that appear in the active task text. The spec's claim "zero false positives" is incorrect. The actual worst-case scenario: a task titled `"finish forge design and comms pillar docs"` makes BOTH `forge-design-status` and `comms-pillar-status` govern. The newest wins — that's deterministic, but it could be the WRONG arc if the newer note is the less-relevant one.

---

## Attack 2: `where-we-are` Single-Line Collapse

**The code** (line 963-964):
```python
one_line = " ".join((wwa.decision or "").split())
lines.append(f"# where-we-are: {_clip(one_line, 120)}")
```

`" ".join(s.split())` collapses all whitespace — including `\n\n` paragraph breaks, bullet points, and markdown formatting — into single spaces. Then `_clip` cuts at 120 chars on a word boundary using `rsplit(" ", 1)[0]`.

**Attack:** What if the where-we-are note body starts with a bulleted list using `- ` markers? The collapse turns:

```
Shipped:
- Method doc: pillar-analysis method...
- Fix with evidence discipline
```

into:

```
Shipped: - Method doc: pillar-analysis method... - Fix with evidence discipline
```

The `- ` markers become mid-sentence noise. But the spec only required "first 120 chars," not semantic coherence. The `_clip` function at line 52 clips on a word boundary and strips trailing `" ,.;:"`. So `_clip("Shipped: - Method doc:... - Fix...", 120)` would break at the last space before 120 and strip punctuation, potentially leaving `Shipped: - Method doc: pillar-analysis method (triangulate ground truth -> diagnose at loop altitude -> fix` — note the trailing `- ` from a bullet marker could be stripped by `rstrip(" ,.;:")` since `-` is not in that set.

**Real finding:** The collapse works mechanically. The `_clip` rstrip set `" ,.;:"` does NOT include `-`, so a line ending in `-` (from a mid-clip bullet) would leave a trailing dash. Cosmetic only — not a correctness defect. **No functional defect.**

---

## Attack 3: Fail-Open Behavior When Ledger/Store Is Down

**The code** has two `try/except` blocks:

1. **Notes block** (lines 938-966): wraps both `get_agent_memory()` and the governing-arc + where-we-are derivations. If the store is down, the entire `try` block is skipped → no governing arc line, no where-we-are line. But the `except` is bare `pass` — it silently swallows EVERYTHING including `ImportError`, `AttributeError`, `KeyError`.

2. **Ledger block** (lines 968-985): wraps `state_view()` and the ledger bar rendering. Also bare `except: pass`.

**Finding:** The fail-open behavior works — a broken store doesn't crash boot. BUT: when the notes store is down, there's no governing arc and no where-we-are. The header prints:

```
# Map: docs/ARCHITECTURE.md (the living skeleton) + AGENTS.md (the door contract)
# Precedence when sources conflict: TASK LEDGER (git-durable, gated transitions) beats durable
# NOTES (write-once, superseded-by-title) beats PROMOTED bus messages (salient, immutable) beats
# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired.
# Ledger: 0 done | 0 active | 0 next | 0 blocked | 0 proposed -- RULE: DONE is closed...
```

That's 5 lines of orientation: map, precedence, and an empty ledger. A cold agent would not know what governs or where we are. The spec didn't mandate fallback text for this case, but it's a real gap — the agent gets a structurally valid but semantically empty head. **No defect in the implementation, but a spec gap.**

---

## Attack 4: Pin That Passes While a Defect Survives

**`test_precedence_doctrine_is_exactly_three_lines_with_ordered_tiers`**

This test checks:
```python
lines = agent_cli.PRECEDENCE_DOCTRINE.split("\n")
assert len(lines) == 3
```

The constant is `PRECEDENCE_DOCTRINE = (...)` — a single string with embedded `\n`. But note: the string uses Python implicit concatenation across three parenthesized lines. There's a subtlety: the constant ends with `"# LIVE BUS (ephemeral).  [STALE] = a newer source supersedes this; absent = retired."` — no trailing newline. `split("\n")` on a string without a trailing newline gives 3 elements (no empty string at the end). That's correct.

BUT: the test does NOT verify that the string is embedded into the header output correctly. The test passes if the constant is 3 lines, but what if `_orientation_header` accidentally adds an extra `\n` before or after? The test doesn't catch that.

**The real defect survivor:** `test_where_we_are_renders_single_clipped_line` verifies `"\n" not in wwa and len(wwa) < 150`. But `" ".join(s.split())` ALREADY removes all newlines — the assertion `"\n" not in wwa` will always pass regardless of whether the clip works correctly. The 150-char bound is loose (spec says 120). A bug where `_clip` returns 400 chars would still pass `len(wwa) < 150` if the input was short to begin with. The test doesn't actually prove 120-char clipping — it passes on a 80-char body without exercising the clip path at all. **The test uses `"x" * 400` but only checks `len(wwa) < 150`, which means it'd catch a complete clip failure but not a 130-char clip (which would violate the ≤120 spec).**

---

## Attack 5: Cold-Start Drill — Subprocess Pin

**`test_cold_start_drill_answers_the_four_questions`**

This runs a real subprocess. The assertions are:

1. `"# Map: docs/ARCHITECTURE.md" in head` — passes if file exists ✓
2. `"# Governing arc: docs/" in head` — passes if ANY `docs/` path appears in ANY governing-arc note's decision ✓
3. `"# where-we-are:" in head` — passes if a `where-we-are` note exists ✓
4. `"Precedence when sources conflict" in head` — passes if the constant is printed ✓
5. `"RULE: DONE is closed" in head` — passes if ledger renders ✓

**BUT** — assertion 2 (`"# Governing arc: docs/" in head`) is a substring check. If the governing arc derivation FAILS and the empty-ledger fallback is active, the header line would be `"# Governing arc: (none declared -- check notes/ledger)"` which does NOT contain `"docs/"`. So the test would FAIL. But what if the derivation picks the WRONG arc doc? The test only checks that SOME `docs/` path is present — it doesn't verify it's the CORRECT one (`comms-pillar-synthesis-2026-07.md`). The `forge-design-status` misfire from Attack 1 would pass this test with `docs/forge-design-something.md` in the governing-arc line, and the pin would be GREEN while the defect (wrong arc) survives.

**Additionally:** assertion 6 (`"DONE (closed -- do NOT redo):" not in head`) is a negative check that the old DONE dump is gone. But note it checks for `"DONE (closed -- do NOT redo):"` — if the old format was slightly different (e.g., `"DONE (closed -- do not redo):"`), the check passes vacuously. The diff shows the old line was `DONE (closed -- do NOT redo):` from `format_state`, so this is likely correct, but it's fragile to format changes.

---

## Summary of Findings

| # | Attack | Severity | Detail |
|---|--------|----------|--------|
| 1 | Slug-token all() misfire | **Real defect** | Two arcs' tokens can both match active task text; newest wins but it may be wrong. Spec claimed "zero false positives" — false. Example: `forge-design-status` tokenizes to `["forge","design"]` and both appear when a task mentions "forge design." |
| 2 | where-we-are collapse | No defect | Cosmetic bullet-marker noise; mechanically correct. |
| 3 | Fail-open when store is down | Spec gap | Header prints with no governing arc and no where-we-are. Structurally valid, semantically empty. The agent gets map+precedence+empty-ledger and has to infer context. |
| 4 | `test_where_we_are` doesn't prove 120-char clip | **Weak pin** | Asserts `len < 150`, spec says ≤120. A 130-char result passes the test but violates the spec. |
| 5 | Cold-start drill doesn't verify CORRECT governing arc | **Weak pin** | Only checks `"docs/"` substring in governing arc line. Wrong arc doc passes. |
| Gate | All 7 checks PASS | — | The shipped head is correct. |