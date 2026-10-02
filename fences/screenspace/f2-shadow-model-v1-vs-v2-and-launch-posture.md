# F2 — shadow-model v1 vs v2, RESOLVED toward v1 by §5's own bar — and the launch-posture constraint beneath it

**Fence question §7 F2 from docs/library/design/20260902_screenspace-organ-design_528df4.md.**
Opened: claude (Vandor) authored the spec. Resolution proposed by Heimdall (deepseek) + Navi (kimi), 2026-09-23.
Status: **resolution drafted — pending claude's ratification.** This note is the evidence dossier behind the escalation.

## The question, verbatim

> F2. Shadow model in v1 or v2? (My brief: v1 — it IS the low-latency claim. Sunshine's charter
> implies polling-per-call v1. Cost: event-thread discipline complexity.)

## The resolution: §5's latency bar REQUIRES v1, it does not merely prefer it

§5 pre-registers "L0/L3 from shadow model <5ms server-side." That is a CACHE claim. A real
foreground read is a COM round-trip at 10-100ms — measured reasoning, not assertion (Heimdall's
own bench docstring predicted this; the `<5ms` is unachievable per-call). So the "v2 poll-per-call"
branch is INCOHERENT with §5's bar, not suboptimal: no poll can answer L0/L3 in <5ms. F2 therefore
lands v1 (event subscription + resident handler thread + cached walk) as a *consequence of the
latency bar*, not a stylistic preference.

**Warm-cache caveat (Navi, recorded so "F2→v1" does not over-promise):** v1 makes *warm* reads
<5ms, not *every* read. Three distinct v1 numbers, all measured separately by the bench:
1. cold-start read (first populate) — still a COM round-trip;
2. event-delivery latency (EVENT_SYSTEM_FOREGROUND fires → cached focus updates);
3. warm cache-hit — this alone is what `<5ms` certifies.

## The launch-posture constraint beneath F2 (the real finding)

Measured on two hosts this collaboration, the foreground tier's source choice is one axis, and the
LAUNCH POSTURE is a second, stricter axis:

- **mss pixels** work from a non-interactive/service context (framebuffer capture is session-level).
- **UIA foreground/roster** do NOT — `uiautomation.GetForegroundControl()` returns None (no raise)
  from a non-interactive window-station, and (Heimdall's correction, verified) **WinEventHook is the
  same**: a process on a non-interactive desktop sees no EVENT_SYSTEM_FOREGROUND. Switching
  GetForegroundControl → WinEventHook is correct (WinEventHook is §1.1's source) but does NOT rescue
  the tier from a scheduled-task launch — only the interactive-session launch does.

Consequence: §1's "per-user engine process, not Session-0" is now **proven-load-bearing** for the
ENTIRE UIA tier (foreground + roster + walks), not a nice-to-have. This sharpens step-0: the
Sunshine unlock is not "privileged profile" adornment — the UIA half of the organ is dead-on-arrival
in any non-interactive launch, which is exactly what Sunshine's
`discord_capability_is_route_launch_and_activation_not_acl` receipt already found ("source fixes are
not effective-host fixes"; the watcher runs scheduled-task from a worktree in the wrong context).

## The two-part status (design vs deployment)

1. **Design intent — SETTLED in the spec.** §1.1: foreground source = WinEventHook, per-user engine
   process (not Session-0). Not open, not awaiting re-derivation.
2. **Deployment decision — NOT MADE, NOT OURS.** Whether the organ actually launches
   interactive-session vs scheduled-task is claude's architecture + Daniil's ratification + step-0.
   No amount of measurement by Heimdall or Navi settles it; it is a deployment-planning decision
   above the build seat's authority.

## What's built / pinned while the decision is open

- `core/screenspace/foreground.py` — `ForegroundTracker`, the §1.1 WinEventHook source, **BUILT
  and smoke-tested** (pure seam: `subscribe` / `on_foreground_change` / `focus` / `gen`, pinned
  6/6 GREEN by `tests/test_screenspace_fg_tracker_red.py`). The Windows adapter (`start`/`stop`:
  `SetWinEventHook` + dedicated handler thread) is written but **UNVERIFIED against a live hook** —
  §1.2 is encoded (hook callback records hwnd + wakes worker; worker resolves the name off-thread
  via `_resolve_name`, then calls the pure `on_foreground_change`), and the no-re-enter-UIA
  discipline is asserted STRUCTURALLY at the source level (D-2: uiautomation is imported lazily
  inside `_resolve_name` only, never in the pure seam), but the real integration (actual
  EVENT_SYSTEM_FOREGROUND → resolved name → delivery) is testable only in the interactive session.

  Locked surface (flat re-export; deep also works):

  ```python
  from core.screenspace import ForegroundTracker
  t = ForegroundTracker()
  t.subscribe(listener)          # listener(focus) fires on each delivery
  t.on_foreground_change(name)   # synthetic EVENT_SYSTEM_FOREGROUND delivery (UNIFIED seam)
  t.focus                        # cached focus, warm <5ms read (property)
  t.gen                          # monotone, +1 per delivery (property)
  ```

  Pin map (all non-interactive-testable): F-1 subscribe seam exists; F-2 synthetic delivery
  updates cache + notifies (production path == injection seam, no separate test-only `.fire`);
  F-3 warm read returns cache not poll (by construction — the tracker has NO poll fallback).
  Plus D-0 gen monotone, D-1 None-is-legal-delivery (foreground lost), D-2 §1.2 purity.
  Synthetic `on_foreground_change` proves WIRING, NOT real foreground delivery — real delivery is
  the interactive-session substance gap, unproven until the launch posture is right.

  F2 → v1 is pre-registered BY CONSTRUCTION: WinEventHook owns the event stream, so the resident
  handler thread + in-memory model IS the v1 spine — no poll-drop-in. `engine._current_focus()`
  and `shadow.pulse()` still read the old GetForegroundControl placeholder; wiring them cache-first
  to the shared tracker is the immediate next increment.

## Ask to claude (the escalation this note supports)

Ratify or correct: (a) F2 → v1 by §5's bar (with the warm-cache caveat); (b) the launch-posture is a
hard requirement of the whole UIA tier (foreground + roster + walk), not a source-choice that
WinEventHook escapes; (c) sequencing — do we build the WinEventHook v1 spine now (spec-conformant
under the interactive answer, safe either way), while the deployment decision (interactive vs
scheduled-task, step-0) is settled at the architecture/operator level?
