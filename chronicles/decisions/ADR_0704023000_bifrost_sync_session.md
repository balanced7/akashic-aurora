# ADR: Bifrost Sync & Plan Protocol + Session Save/Restore

**Date:** 2026-07-04 ~02:30 UTC
**Author:** deepseek (during live multi-agent Bifrost session)
**Status:** drafted (user will review on next boot)

## Context

User called for a global pause + synchronize + plan feature mid-session,
observing that the multi-agent Bifrost system needs better coordination and
responsiveness. User was going to sleep and asked to save all learnings/plans
for tomorrow pickup, plus "engineer a way that it can spin up the same agents
that were working."

## Decision

### Part 1: Sync & Plan Protocol (design only — not yet implemented)

Full design in `docs/library/design/20260709_bifrost-sync-plan-protocol_c70323.md`. Five layers:

1. **Agent State Tracking** — per-agent Redis key (`bifrost:control:agent_state:<agent>`)
   with state machine: running → pausing → paused → acknowledged
2. **Pause Acknowledgment** — UI shows live progress of who's stopped
3. **Sync Barrier** — `SyncBarrier` class for rendezvous (all agents arrive before release)
4. **Planning Round Protocol** — new bus kinds: `plan_directive`, `plan_response`, `plan_commit`
5. **Checkpoint Capture** — stateless agents save context on pause; restore on resume

Implementation order: P1 (state tracking + UI) → P2 (barrier) → P3 (planning round) → P4 (checkpoints).

### Part 2: Session Save/Restore (IMPLEMENTED)

`core/comm/launcher.py`:
- `_save_session_to_disk()` — writes currently-running agent tags to `state/bifrost-session.json`
- `session_snapshot()` — preview what a restore would do
- `restore_session()` — re-launches all saved tags, skips already-running agents
- Auto-save hooks: every `launch()` and `kill()` call auto-saves

`core/comm/session_state.py` (new):
- Thin wrapper adding bus-snapshot context around the launcher's restore

`scripts/bifrost_ui.py`:
- `/session/snapshot` — wired to launcher save (existing stub, now functional)
- `/session/resume` — wired to launcher restore (existing stub, now functional)
- `/launcher/save-session` and `/launcher/restore-session` — explicit endpoints
- UI: "💾 Save Session" and "🔄 Restore Session" buttons in launcher panel

### Design Principles

1. Same advisory/fail-open/Redis-backed trust model as the rest of core/comm
2. Redis is the shared whiteboard; UI is the cockpit, not the controller
3. Durable state file survives Redis restarts and OS reboots
4. Crash-safe: all keys have TTLs; barriers auto-expire

## Consequences

- **Positive:** Tomorrow: one click restores today's fleet. Pause→plan→commit→go
  protocol designed and ready for implementation. Design doc lives at
  `docs/library/design/20260709_bifrost-sync-plan-protocol_c70323.md`.
- **Negative:** Sync/plan protocol is design-only (4 phases, ~6h to implement).
  Session save/restore covers the immediate need ("spin up same agents tomorrow").
- **Risk:** The `/session/*` stubs were already in the UI code referencing a
  non-existent `core.comm.session_state` — now implemented.
