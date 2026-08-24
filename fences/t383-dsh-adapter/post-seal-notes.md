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
