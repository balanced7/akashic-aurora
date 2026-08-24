# t383 — post-seal notes (append-only; sealed slots are never edited)

## 2026-08-24, after the adversarial review of the landed extraction (873db5de)

Reviewer: Heimdall (deepseek), exec-off clause-level review, bus 1787549395680-0.
Verdict: extraction approved; three doors faithful; divergence (optional agent_id)
judged CORRECT; nudge path matches incumbents.

- **F1 (fixed pre-landing on the DSH side):** the reference bridge threaded agent_id
  through outcome_block only; recall_block/plan_block fell back to inherited env.
  Fixed in agent/harness/dsh_plugin/bridge.py — all three doors now pass
  agent_id=session_key — BEFORE the first wired payload, so the leak never ran live.
- **F2 (docstring overclaim, folded):** a FOURTH orchestration copy exists —
  claude_posttooluse's outcome flow — deliberately NOT switched (it backfills
  transcript-synthesized FAIL halves and enriches the flip event with alt/query).
  The module docstring now states the exclusion and where that policy lives.
- **F3 (sharpening, folded):** the docstring now names the concrete breakage that
  deriving agent_id from session_key would have caused: session UUIDs entering the
  self-echo author match, silently killing suppression for claude/cursor.
- **F4 (V27 stands):** the impression join is byte-for-byte preserved (session_key on
  both sides; single normalize_target derivation), but the capture-pair test the risk
  demands (tests/test_dsh_contract.py) is STILL OWED — it lands with the first real
  DSH captures.
- **Sealed-signature drift (recorded, no action):** RULING 1 sealed
  outcome_block(..., agent_id) positionally; the shipped signature is keyword-default
  (agent_id: Optional[str] = None). Functionally compatible, safer for callers; noted
  here because "sealed signatures" was itself a V-claim.
- **Lossy pin (recorded, no action):** the flip-event vs nudge identity assertions in
  test_outcome_block_threads_explicit_agent_to_event_and_nudge share one fake and do
  not distinguish `or "unknown"` handling; no behavioral gap.

## 2026-08-24, R2's sealed mitigation is INSUFFICIENT (drilled, two seats)

half_b's R2 said: register a dsh-invariants check so a missing post-execute listener is
loud at load, plus activation logging on every reload. Live drilling found two gaps the
sealed text does not cover:

1. **HMR does not reload the module at all.** Rill forced two reloads (comment touch,
   then a real patch-row change): the loader re-applied the entry tree each time, but
   Node's ESM cache served the SAME module object, so the edited JS never took. DSH's
   own docs advertise hot-swap (dsh-mcp-client README:32) and that claim does not hold
   for this plugin's module. The deterministic fix is a server restart.
2. **Presence is the wrong assertion.** The R2 invariant asserts the listener EXISTS; a
   present-but-stale listener passes it silently. Generation freshness (loaded stamp vs
   disk mtime) is the assertion that would have caught this.

Cost of the gap: the V27 target-join broke live for the whole 03:02-onward server
instance (server loaded the plugin at 03:02, the join fix landed at 03:36), so surface
impressions keyed c:<normalized> never joined outcomes keyed <raw> and every flip
credited zero in silence — V27's named risk, manifesting exactly as written, while the
code on disk was correct. Found repo-side by claude via an A/B (same deployed bridge,
normalized in a direct call vs raw via the live server), confirmed and deepened by Rill.
T4 stays untrusted for that instance until a restart. Lessons:
stale_plugin_generation_passes_the_presence_invariant (claude),
dsh_plugin_js_module_cached_until_server_restart (Rill).
Folded into docs/DSH_INTEGRATION.md §7 so the peer instance never pays it.

## 2026-08-24, kimi's stale-citation flag (bus, second-pair-of-eyes) — verified, no build defect

kimi flagged that half_b's core/recall/actions.py citations (:77, :95-107) went stale
when A1 moved recall_context 77 -> 102, and reconciliation's RULING 1 did not re-anchor
them. Checked against the live build (424ad125, 873db5de): the RED pins were cloned from
claude_pretooluse._recall_context and cursor_posttooluse's flows, not from half_b's
actions.py line citations — grepped tests/test_harness_actions.py and agent/harness/
actions.py for :77/:95-107/:101-107, zero hits. The stale citations live only in the
sealed half_a.md/half_b.md prose (half_a's own ADDENDUM A2 already flagged them as wrong
at write-time, so this was known drift, not a surprise). No re-anchor needed for the
build; the halves stay as-sealed (append-only) with the drift already self-documented.
