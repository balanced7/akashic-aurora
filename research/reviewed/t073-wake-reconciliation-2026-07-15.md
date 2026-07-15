# T073 Wake & Communicate — Reconciliation (claude ⋈ deepseek) — 2026-07-15

Status: reconciled build spec (halves: claude-t073-wake-design-2026-07-15.md,
deepseek-t073-wake-design-2026-07-15.md). Build cites THIS document. Daniel's directive
verbatim in the T073 task text.

## The fork, resolved: dispatcher LOSES the current arc

claude's half proposed dispatcher-as-sole-watcher with per-incarnation signal keys;
deepseek's half refuted it on three grounds that HOLD: (1) the W3 invoker registry does
not exist — wiring the dispatcher now is fake integration (wiring_investigate_before_
acting); (2) it cannot re-arm a session (harness law L1) so it does not touch the actual
constraint; (3) it adds a who-watches-the-watcher surface without removing any. VERDICT:
deepseek's watcher-level protocol is the arc; the dispatcher remains Phase 5 / M1-wave
future for the multi-runtime fleet. (The signal-key idea survives INSIDE Phase 5.)

## Blind convergences

1. **The long-lived watcher** — both halves independently: ONE arm per session, a
   watcher that blocks in chunks for hours and exits only on mail or true deadline
   (claude "seat-arms-once"; deepseek Design 3). The stop-hook becomes a BACKSTOP for
   watcher death, not a per-turn nag.
2. **Noise decomposition identical**: legacy dual-write twins (T047 kills), self-frm
   gaps, trace floods (T045 lane-mode kills), quiet-deadline churn.
3. **Harness law L1 stated identically**: only a session-launched background task can
   re-invoke that session; hooks can block and teach, never arm.

## Adopted from deepseek (the build spec)

- **Phase 1 — incarnation protocol** (fixes twin-wake at the root): every send stamps
  `meta.frm_incarnation` (runner instance_token / session id); the wake filter replaces
  `frm == agent` with: same incarnation → skip (echo); same agent, different
  incarnation → DELIVER (twin mail); different agent → deliver.
- **Phase 2 — WAKE_WORTHY allowlist inversion** (the ratchet): only
  {request, handoff, reply, blocker, question, completion} wake; a NEW kind is
  silent-by-default (the check_door_parity pattern applied to kinds).
- **Phase 3 — long-lived watcher**: 4-hour internal-loop deadline, 120s block chunks,
  near-deadline self-re-arm trigger file, stop-hook message reworded to "your watcher
  died — re-launch once" (backstop semantics). Do NOT remove the stop-hook block.
- **Phase 4 — `to_incarnation` directed addressing** (one twin, not fan-out).
- **Phase 5 — dispatcher W3 + supervised daemon**: future arc (M1 design wave).
- Non-goals verbatim: no harness changes; no runner consume-loop changes; no
  dispatcher wiring now.

## Adopted from claude (the harness tier his seat cannot see)

- **The ccd channel**: `mcp__ccd_session_mgmt__send_message(session_id, text)` delivers
  INTO a sibling session as a labelled user turn — the ONLY channel that wakes a
  SEATLESS session; every send is Daniel-confirmed (visible twin traffic). Adopted as
  the twin-ping + watcher-death fallback: [twin-sync] coordination pings may ride it;
  payloads stay on the bus/ledger. `list_sessions` = sibling detection; a boot whisper
  line ("N live sibling sessions") lands with T072's incarnation cards.
- RemoteTrigger investigated and ruled out (cloud routines, not local wake) — recorded
  so nobody re-investigates.

## Pins: deepseek P1–P12 verbatim (his table is the acceptance contract), plus
P13 (claude): a seatless idle session is reachable via the ccd channel — manual drill
with Daniel's confirm, documented in the runbook rather than pytest.

## Build order tonight: Phase 1 + 2 (claude builds, deepseek verifies — his design, the
T058 pattern); Phase 3 next block (touches the live stop hook — land fail-open +
kill-switched); Phase 4 with T072's claims board; Phase 5 parked for the M1 wave.
