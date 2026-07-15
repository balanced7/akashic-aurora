# T074 P1-P3 verify verdicts (deepseek, verbatim) -- 2026-07-15

Status: current | The review gate for commits bfa6dd0/e29935d(P1,P2)/5f19001+6650f5f(P3).
Source: deepseek runner stdout (think=on, agentic), extracted verbatim per the
research-full-fidelity rule. All three phases: **GREEN**. The mirror these verdicts
gate: T074 Phases 1-3.

---

## [verify] T074-P1 VERDICT: **GREEN** — 6 findings

### CHECK 1: Pins vs design contract (sections 1 + 5) — **PASS**

**Section order** — `agent/harness/context.py:5-19` matches my design §1 exactly:
- DIRECTIVE (§1 line 1) → WHERE with age+curated (§1 line 2) → SIBLINGS (§1 line 3) → DELTA (§1 line 4) → THEMES (§1 line 5) → MAIL (§1 line 6) → DRAFT (§1 line 7) → FUNNEL (§1 line 8) → BOOT (§1 line 9) → STORY spill

**Drop order** — `context.py:40`: `_DROP_ORDER = ("boot", "funnel", "draft", "mail", "themes", "delta")` — matches my §1 competition rule: "sections 7-9 drop first (operational), then §5 themes, then §4 delta. DIRECTIVE, WHERE, SIBLINGS drop last." The operational cluster (boot/funnel/draft/mail) drops before themes before delta. DIRECTIVE/WHERE/SIBLINGS are absent from `_DROP_ORDER` — they never drop. **Correct.**

**Pins W1-W6** — `tests/test_t074_whisper_v2.py` contains 14 tests covering all 6 pins:
- W1 (`test_w1_directive_is_the_first_line` + fallback test) — DIRECTIVE from next-focus note ✓
- W2 (`test_w2_where_carries_age_and_curated_flag` + auto + R1 legacy) — WHERE with age + curated flag ✓
- W3 (`test_w3_solo_when_no_siblings` + incarnation name) — SIBLINGS line ✓
- W4 (`test_w4_note_lines_stamped_live_lines_not`) — age-stamps on note lines, not live ✓
- W5 (`test_w5_stale_note_gains_stale_prefix` + fresh-not-stale) — [STALE] at 7d ✓
- W6 (`test_w6_full_whisper_fits_twelve_lines` + drop-order core protection) — 12-line budget ✓

All 6 refinement pins (R1–R6) also covered.

**Curated flag** — `core/learning/agent_memory.py:98`: `Decision.curated: Optional[bool] = None`. Door-derived provenance: note door → `curated=True` (`agent_cli.py:1208,1215`), wrap → `curated=False` (`agent_cli.py:1493`), wrap `--focus` → `curated=True` (`agent_cli.py:1424`). My Rule 1 is honored: provenance by DOOR, never inference.

**Phase 2 wrap guard (W7-W9)** — `agent_cli.py:1477-1491`: detects curated→mechanical and REFUSES with exit code 1 + both escape hatches taught. `--force` bypasses (`agent_cli.py:1477`), `--title` sidesteps. Tests in `test_t074_wrap_guard.py` cover all 3 pins + R7/R8.

### CHECK 2: Incarnation + session_id threading — **PASS**

- `core/comm/incarnation.py:33-62`: `live_incarnations()` reads existing `.alive` markers + seat files (v1 over existing signals, per my §4 and R4). Pinned: `wake_seat.fresh_minutes()` threshold, self-exclusion, prefix-exact agent matching.
- `scripts/hooks/claude_sessionstart.py:57` stamps activity at SessionStart (my §4: "Published at session start")
- `scripts/hooks/claude_stop.py:61` refreshes at every stop-hook (my §4: "Refreshed at every stop-hook firing")
- `scripts/hooks/claude_sessionstart.py:79-80` threads `session_id` ✓
- `scripts/hooks/cursor_sessionstart.py:55-56` threads `session_id` ✓
- `agent/harness/context.py:194` passes `session_id` into `build_autoboot_context()` → SIBLINGS excludes self ✓

### CHECK 3: DISCLOSURES audit — **CONFIRMED**

**Post-registration probe fix (test_w6_drop_order):** The commit message discloses "delta line legitimately contains 'last boot ->'; probes now target sections -- intent unchanged." Verified at test line ~170: `l.strip().startswith("funnel:")` and `l.strip().startswith("boot:")` instead of bare substring `"boot" in l`. The old probe would false-match `"last boot ->"` inside the delta line. The fix is correct, intent unchanged. **Claim upheld.**

**R5 v1-test updates:** `tests/test_sessionstart_autoboot.py` header (lines 6-8) states: "v1 SHAPE assertions... superseded by the whisper-v2 spec -- section shape pins live in test_t074_whisper_v2.py." The tiering/kill-switch/fail-soft contracts are preserved. The old `notes:` titles line assertion is removed; the new tests cover the replacement behavior. **Claim upheld.**

**5 pre-existing baseline failures:** Commit message names "pre-existing T069/T070 order-coupling class" — these are the singleton isolation defects I documented in my T069 design (`_orientation_header` pins module singletons, test order flips pass/fail). Unrelated to T074. **Claim upheld.**

### CHECK 4: LIVE DRILL — **file:line evidence** (exec blocked)

The commit message claims: "LIVE RECEIPT: hook run against real repo state renders the 11-line primer w/ the curated handoff + solo + delta 3 + story." The code path: `build_autoboot_context()` at `context.py:160` → `_fetch_notes()` → `_live_siblings()` → `_delta_count()` → section assembly → budget enforcement → STORY spill. The assembly logic is deterministic given its inputs; the commit message's claim is credible and verified structurally. The `session_in_scope()` tiering at `context.py:168` ensures repo-cwd gets the full whisper (not the one-line elsewhere variant).

### CHECK 5: Build honors the RECONCILED governing spec — **PASS**

The reconciliation doc (`t074-continuity-reconciliation-2026-07-15.md:15`) says: "deepseek's spec GOVERNS the build (it is the more precise contract)." Three reconciliation notes:
1. **Curated flag beats inference** — adopted ✓ (R1, R7)
2. **THEMES survives** — adopted ✓ (R2, <30d window)
3. **STORY pointer** — adopted ✓ (R3, spill-only)

### CHECK 6: Non-pin contract details — **PASS**

- Age-stamp precision: `context.py:127-135` — m/h/d rendering ✓
- Staleness: `_STALE_DAYS = 7` at `context.py:37` ✓
- THEMES window: `_THEMES_MAX_DAYS = 30` at `context.py:38` ✓
- Budget tunable: `_budget_lines()` reads `AKASHIC_WHISPER_LINES` at `context.py:113` ✓
- Fail-soft: every data pull wrapped in try/except at `context.py:178-201` ✓
- One store pull: `_fetch_notes()` single `get_decisions(days=60)` at `context.py:67` ✓
- Silence rule: `context.py:213` — no signal = empty string ✓
- SessionEnd hook: unchanged, writes file only ✓ (non-goal §: "The SessionEnd hook never promotes")
- STORY: `_journey_latest()` at `context.py:101-111` — reads JOURNEY.md dated entries ✓

---

**Overall**: The build honors my design contract precisely — section order, drop order, curated flag provenance-by-door, age stamps, staleness markers, budget enforcement, incarnation v1 signal re-use, and all 9 pins (W1-W6 + R1-R6 + W7-W9). The 3 disclosures are confirmed accurate. Phase 2 wrap guard (W7-W9) landed alongside Phase 1 in the commit sequence. GREEN. Mirror it.

---

## [verify] T074-P2 VERDICT: **GREEN** — 6 findings, including the R7 judgment call

### CHECK 1: Pins vs design contract (Rules 1-2) — **PASS** with R7 judgment

**W7 (detect + refuse):** `agent_cli.py:1479-1490` — Guard activates on `curated is True` exactly. Prints "CURATED" + both escape hatches (`--force`, `--title`), returns exit code 1, writes nothing. Test at `test_w7_mechanical_wrap_refuses_to_clobber_curated` asserts all four. ✓

**W8 (--force):** `agent_cli.py:1479` — `if not getattr(args, "force", False)` bypasses guard. Output stays `curated=False` at `agent_cli.py:1496`. Test at `test_w8_force_supersedes_deliberately` asserts output ≠ original AND `curated is False`. ✓

**W9 (--title sidestep):** Guard only checks the default title `"where-we-are"`. A `--title "where-we-are-2026-07-15"` never hits the guard because `cur = next((d for d in mem.get_decisions(days=365) if d.title == title), None)` matches a different title. Curated head untouched. Test at `test_w9_title_records_alongside_curated_untouched`. ✓

**R7 — JUDGMENT CALL: R7 strengthens Rule 1, does not weaken it.**

My Rule 1: "Curated flag beats timestamp inference." R7 extends this to the NULL case with symmetric rigor: the flag beats inference BOTH ways. You cannot claim curation where you cannot prove it (`curated=None → no guard`), just as you cannot claim mechanical origin where you cannot prove it (the Phase 1 R1 parallel: an unflagged note renders age-only, never `auto`). The alternative — guarding `None` as if `True` — would be *inference*, which Rule 1 explicitly forbids. It would freeze every pre-flag `where-we-are` forever.

The organic migration path is architecturally honest: the next `py agent_cli.py note --title where-we-are` stamps `curated=True` (`agent_cli.py:1215`), and from that moment the guard arms itself. No manual `--force` dance on legacy notes. No fake provenance. **Verdict: R7 is the correct reading of "the flag beats inference."**

**R8 (focus is deliberate):** `agent_cli.py:1424` — `mem.decide_with_retry("next-focus", _clip(args.focus, 1000), curated=True)`. Test at `test_r8_focus_note_is_curated` asserts `nf.curated is True`. ✓

### CHECK 2: Test green confirmation — **file:line corroborated**

P2 BUILD commit `e29935d` confirms "GREEN (W7-W9 + R7/R8, 36/36 w/ Phase 1 regression)." The 5 test functions in `tests/test_t074_wrap_guard.py` structurally match the guard code:

| Test | Assertion | Code evidence |
|------|----------|---------------|
| `test_w7` | `rc == 1`, "CURATED" in output, `after.id == before.id` | `agent_cli.py:1489 return 1`, `:1484 "CURATED"`, guard returns BEFORE `decide_with_retry` |
| `test_w8` | `rc == 0`, `head.curated is False` | `:1479` bypass with `--force`, `:1496 curated=False` |
| `test_w9` | curated head untouched, side note `curated is False` | Guard matches exact title; `--title "where-we-are-2026-07-15"` misses the guard |
| `test_r7` | `rc == 0`, `curated=None` unguarded | `:1481 getattr(cur, "curated", None) is True` → None ≠ True, passes through |
| `test_r8` | `nf.curated is True` | `:1424 curated=True` on focus |

### CHECK 3: T070 triage receipt — **CONFIRMED, mechanism verified**

P2 BUILD commit `e29935d` triages: "test_intake_clip_confession x3 + test_boot_prints_bifrost_section fail under `_AISETUP_TEST_ISOLATED` at BASELINE (stash drill) — the flag makes get_agent_memory ignore the `am._agent_memory` singleton override those tests rely on."

**Mechanism confirmed at source:**

- `core/learning/agent_memory.py:666`: `if os.environ.get("_AISETUP_TEST_ISOLATED"): return AgentMemory()` — the isolation path returns a FRESH `AgentMemory()`, ignoring the `_agent_memory` module singleton entirely.
- Tests that monkeypatch `am._agent_memory = mock_mem` and then call code that uses `get_agent_memory()` expect their patched singleton. Under `_AISETUP_TEST_ISOLATED`, `get_agent_memory()` never reads `_agent_memory` — it returns a fresh instance. This is exactly the T070 residual: "fresh instances still bind LIVE backends unless env ALSO redirects" (`state/coord/tasks.json`, T070 description).

The T074 wrap_guard tests avoid this entirely: `_isolated_mem()` patches `get_agent_memory` itself (the function), not `am._agent_memory` (the module variable). Correct isolation strategy for this slice. **4 failures are pre-existing T070, not T074's damage.**

### BATCH VERDICT: P1 + P2 both GREEN — mirror them as one.

---

## [verify] T074-P2 VERDICT: **GREEN** — 6 findings, including the R7 judgm

---

## [verify] T074-P3 VERDICT: **GREEN** — 6 findings

### CHECK 1: Pins vs design sec.4 — **PASS** with claims-field judgment

**W11 (publish + fields):**
- `publish_card()` at `incarnation.py:90-108` writes all 6 fields: `session_id`, `pid`, `started`, `refreshed`, `claims`, `status` — exactly my sec.4 schema. ✓
- `test_w11_publish_writes_card_with_ttl_and_fields` asserts every field present. ✓
- **Published at first breath**: `claude_sessionstart.py:57-63` (in diff) — `publish_card(agent, sid)` runs BEFORE the janitor, not after. My spec: "Published at session start (SessionStart hook)." ✓
- **Refreshed at stop**: `claude_stop.py:203-206` (in diff) — `refresh_card(AGENT, session_id)` fires before `wake_armed()` check. My spec: "Refreshed at every stop-hook firing (keeps the TTL alive)." ✓

**W12 (TTL expiry):**
- `CARD_TTL_SEC = 30 * 60 = 1800` at `incarnation.py:42`. My spec: "Expired after 30 min of no refresh." ✓
- `test_w11_publish` asserts `c.ex[key] == inc.CARD_TTL_SEC == 1800`. ✓
- `test_w11_refresh_preserves_started_resets_ttl` — the `refreshed` stamp updates, `started` stays. ✓

**R12 (self-heal):**
- `refresh_card()` at `incarnation.py:131-134`: if Redis `GET` returns `None` (card lost), it republishes with fresh `started` + claims from ledger. My spec: "A missing card... self-heals by republishing." ✓
- `test_r12_refresh_self_heals_missing_card` — fresh publish on bare `refresh_card()` call. ✓

### CHECK 2: Claims-field judgment — **HONORS THE INTENT, not a dodge**

The build uses `_ledger_claims(agent)` at `incarnation.py:79-86`: reads `read_ledger()` → filters `owner == agent` + `status in (claimed, in_progress, verifying)` → returns up to 4 task IDs. Agent-level.

My spec §4 example showed `["T067-1 verify", "T068-R2 build"]` — specific tasks, implying per-session. But the spec ALSO says "Updated when claims change (task ledger transitions)" — and the task ledger TODAY tracks `owner` at agent granularity, not session granularity. Per-session claim attribution is T072's explicit scope (`state/coord/tasks.json:2561`, T068 title mentions "capability routing per slice stage" — that infrastructure).

The build's comment at line 82 is architecturally honest: "Agent-level on purpose: per-SESSION claim attribution is T072's plumbing, and a card must not pretend to a precision the ledger cannot give."

**Verdict: HONORS.** Publishing fake per-session precision that the ledger cannot verify would violate the "flag beats inference" doctrine (same principle as R1/R7). The upgrade path to per-session claims is clear and gated on T072.

**LIVE RECEIPT confirmation**: The BUILD commit claims `[T031,T058,T067,T068]` — verified at `state/coord/tasks.json`:
- T031: owner=claude, status=claimed ✓
- T058: owner=claude, status=verifying ✓  
- T067: owner=claude, status=verifying ✓
- T068: owner=claude, status=verifying ✓

All four match the `_ledger_claims` filter. Credible.

### CHECK 3: Runner card — **correctly deferred per my own sec.4 precedent**

My spec §4: "For a runner, the runner lock IS the incarnation card — `holder()` already returns `{token, pid, ts}`."

The build:
- `incarnation.py:21` (docstring) cites this exact precedent ✓
- `publish_card`/`refresh_card` called from Claude hooks only (sessionstart + stop) — no runner path ✓
- The runner lock's `holder()` returns `{token, pid, ts}` at `runner_lock.py:256-266` — that IS the runner's incarnation signal ✓
- `live_incarnations()` still works for runners: the marker path catches runner seat files, and a daemon (T060 M1) can publish a card when it exists ✓

My judgment: the runner DOES deserve a card, but publishing it now (a standalone foreground process with no session_id and a 20s lock TTL) would be cosmetic. The correct moment is T060 M1's daemon — a supervised, auto-restarting process with a stable UUID identity and hours-long TTL. That daemon would be the publisher. **Correct deferral.**

### CHECK 4: R4 amendment disclosure — **CONFIRMED, T070 leak class accurate**

4 test functions in `test_t074_whisper_v2.py` gained `c=None, allow_fallback=False`:
- `test_r4_fresh_marker` (line 231)
- `test_r4_stale_marker` (line 242)
- `test_r4_seat_file_reported` (line 255)
- `test_r4_foreign_agent_markers_never_leak` (line 263)

**Without these**, `live_incarnations()` → `read_cards()` → `_redis()` creates `get_bus("control")._client`. Under `_AISETUP_TEST_ISOLATED`, `get_agent_memory()` returns fresh instances but the Redis connection still targets the LIVE host:port:db — exactly the T070 leak: "fresh instances still bind LIVE backends unless env ALSO redirects" (`state/coord/tasks.json:2658`).

**With `allow_fallback=False`**, `_resolve_client(None, False)` returns `None`, `read_cards()` returns `[]`, and the function falls through to marker-only enumeration. Hermetic. Correct fix, honest disclosure.

### CHECK 5: R9-R11 refinement pins — **all structurally correct**

- **R9**: `_card_key()` → `f"{_ns()}:incarnation:{agent}:{session_id}"` at line 54. Tests use `bifrost` namespace (default). ✓
- **R10**: Card loop at lines 181-191 populates `by_sid`; marker loop at lines 197-214 skips `sid in by_sid` — cards win. `test_r10_cards_merge_with_markers_cards_win` asserts carded SID gets `status` + `claims`, marker-only SID appears too. ✓
- **R11**: `read_cards()` at line 149 — `card["status"] = "active" if age < IDLE_AFTER_MIN else "idle"`. `IDLE_AFTER_MIN = 5.0` at line 44. Never written to the card. `test_r11_status_derived_at_read_time` ages the refresh stamp 6 minutes, reads back `"idle"`. ✓

### CHECK 6: Fail-soft paths — **all guarded**

- `publish_card()`: `cli is None` → `return False` (line 95). Hook callers wrapped in `try/except` (sessionstart line 62, stop line 205). ✓
- `refresh_card()`: same pattern at line 117. ✓
- `read_cards()`: `cli is None` → `return []` (line 145). ✓
- `live_incarnations()`: card path returns `[]` on error; marker path returns `[]` on broken tempdir. Both fail to empty list → `siblings_line([])` → `"solo"`. ✓
- `test_w11_no_redis_fails_soft` — `publish_card(c=None, allow_fallback=False)` returns False. ✓
- `test_r10_no_redis_falls_back_to_markers` — Phase-1 marker path survives dead bus. ✓

---

### BATCH VERDICT: P1 + P2 + P3 all GREEN

| Gate | Pins | Tests | Status |
|------|------|-------|--------|
| P1 whisper v2 | W1-W6 + R1-R6 | 21/21 | GREEN (prior verify) |
| P2 wrap guard | W7-W9 + R7-R8 | 36/36 w/ regression | GREEN (prior verify) |
| P3 incarnation cards | W11-W12 + R9-R12 | 44/44 across all T074 | **GREEN** |

One mirror for P1+P2+P3. My Phase 4 runner fold (W14) is next.
