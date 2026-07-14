# T045 Stage 2 — Runner consume cutover: SCOPE + PIN PLAN (claude half, 2026-07-14)

Status: DRAFT for fence counter-check (deepseek adversarial pass gates pin pre-registration).
Fence signal already banked: deepseek's BLIND seam census (bus reply 1784032192055-0, written
from the T039b design doc without seeing this draft) converged on the runner seam and ADDED
the session-door surfaces + line numbers folded below. Blind convergence = build-signal.
FENCE VERDICT (2026-07-14, deepseek adversarial pass): AMBER -- 7/9 pins CONFIRM; R3/R8
conditional on the lane-cursor-key design (now specified below, his Q1 proposal adopted);
R10 added (his missing-pin finding); R2/R5/R7 sharpened per his per-pin verdicts; all
citations path-verified (one +-2 line drift corrected below). Full report:
research/reviewed/deepseek-t045-stage2-scope-review-2026-07-14.md. Pins pre-register RED
only after his one-line affirm of this fold.
Cites: docs/t039-lanes-latches-design-2026-07.md (T039b bars: A4, P3, P4, M2; reader census A3),
docs/packet-spec-v1-2026-07.md (R8 migration-enforcement law),
research/reviewed/deepseek-t045-stage1-review-2026-07-14.md (stage-1 residuals: lane-aware
pending check; F1 limit=10; F3 advance+streams brittleness).
Completion bar (per ledger T045): RB-25 storm rerun (S1-S5 + S2-NEW + S6), ns-isolated.

## Seam map (path-verified today)

CUT THIS STAGE (the runner):
- scripts/bifrost_runner_deepseek.py:824 — main consume loop:
  `bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)` -> should_answer filter ->
  process -> `bus.advance_to(...)` (:848-850 per-message; :855-859 batch sweep -- fence
  line-drift correction). RB-26 at-least-once with
  killpoint instrumentation (:828 post-consume-pre-process). Reads LEGACY inbox+broadcast;
  advances the SHARED cursor.
- scripts/bifrost_runner.py:177 (Gemini twin) — single consume call:
  `bus.wait(timeout_ms=0, advance=True)` (deepseek census). SAME-SLICE conversion
  (grep-census bar makes skipping it loud; in lane mode advance=True must become
  lane-cursor advance, never the shared cursor).

ALREADY CUT (stage 1, shipped 8e913a1 + 217cea3): wake listener lane-mode
(bifrost_api._wake_block_lane; detect-only; SKIP_KINDS_LANE; arm-time pending check).

SESSION DOOR (staging = OPEN QUESTION 3, deepseek census pulls it forward):
- agent_cli.py cmd_bifrost_sync -> agent/bifrost_pull.py:99-133 consume_inbox — the session
  consumer, and core/comm/bifrost_api.py:91 inbox(consume=True) — the MCP door. BOTH ride the
  ONE inbox()/_drain seam: a single streams= gate at that door covers both, which argues for
  riding this slice rather than splitting flag regimes across stages.

REMAIN LEGACY (stage 3+):
- core/comm/doctor.py (stalled_consumer inspection reads), scripts/bifrost_ui.py (SSE tail on
  bifrost:inbox:* + broadcast), scripts/bifrost_console.py.
- promoter.py is push-side (census: not a reader).

LANE INFRA ALREADY IN PLACE: Bus._lane_write dual-write ON by default (bus.py:311-314);
wait(streams=...) retarget + advance-guard (bus.py:387-393); T043 consume-door len/sha
DROP+loud applies through Bus.wait->_drain on ANY stream set; lane tails/A4 concrete-id
seeding (bifrost_api).

## Cutover design (strangler, mirrors stage 1's env gate)

- Flag: BIFROST_CONSUME_LANE=work on the runner process (default unset = legacy path
  byte-identical; flip is per-process, no flag day). T034 settings: migration later.
- Runner loop in lane mode: bus.wait(streams=work-lane, since=lane-cursor, since_out=...) ->
  process -> advance LANE cursor (NEW per-agent lane cursor key; the legacy shared cursor is
  NEVER written in lane mode).
- LANE CURSOR KEY (fence Q1, deepseek proposal ADOPTED): `{ns}:cursor:lane:{agent}`, same
  inbox/bc per-field structure as the legacy cursor. Write path (deepseek refinement,
  follow-up msg 2026-07-14): bus.advance_to() gains an optional cursor_key= parameter
  DEFAULTING to the shared cursor (zero change for legacy callers); lane-mode callers pass
  the lane key, so per-message and batch advances write ONLY the lane key. This unblocks
  R3 and R8 (they were unfalsifiable without a specified key design).
- A4 cursor init at flip: tail-at-flip (concrete ids, proven > `$` in stage 1 pin 4).
- P3: drain sig lane BETWEEN work packets (EF-beats-AF at the consumer).
- P4: ANSWERABLE unchanged; note/status never trigger an answer turn (parity with
  SKIP_KINDS_LANE listener-side).
- M2: retention guard — dual-write retention = MAX(legacy, lane) for the migration window.
- Stage-1 residuals folded: (a) lane-aware arm-time pending check — ONE extra wait() with
  streams=_lane_streams() after the legacy peek, before tail seeding (deepseek's exact fix);
  (b) F2: _lane_tails() error path must return "$" (retry first, "$" as degraded-safe
  fallback), never "0" — a Redis blip must not replay lane soak history as a false-wake
  storm; (c) F1: pending-check drain bound documented + test at >10 backlog;
  (d) F3: callsite comment/assert — never advance=True with streams=.

## Pin plan (pre-register RED in tests/test_t045_runner_cutover.py AFTER fence)

R1  lane-mode runner answers a lane handoff end-to-end (reply lands, sender expectation met).
R2  strangler safety net, SHARPENED per fence: dual-write ON, lane write FAILS (the
    best-effort catch in _lane_write), legacy delivery succeeds -> runner still answers.
R3  at-least-once preserved: crash at post-consume-pre-process killpoint -> redelivery on
    restart; lane cursor advances only after outcome (RB-26 parity on the lane path).
R4  consume-door integrity on lane path: corrupted len/sha packet -> DROP + loud event,
    never delivered to the model.
R5  P3 sig-interleave: a sig packet queued between two work packets is drained between them
    (concrete hook per fence: sig-lane drain with short timeout between work wait cycles --
    EF-beats-AF at the consumer, not merely separate streams).
R6  P4 parity: note/status on the work lane produce NO answer turn and NO idle-seat wake.
R7  lane-aware pending check: lane-only mail arriving pre-arm wakes/answers (Scenario B
    closed structurally, not by dual-write luck). MUST run with dual-write OFF (fence
    requirement: the legacy twin masks a broken check; OFF proves it load-bearing).
R8  shared-legacy-cursor is NEVER written in lane mode (pin the RB-21 seat untouched).
R9  Redis blip at arm/seed time never replays lane history: _lane_tails degraded path yields
    "$"-equivalent behavior, pinned with a fault-injected tails read (stage-1 F2).
R10 lane cursor init at runner flip (fence missing-pin finding): first boot into lane mode
    seeds at lane tails (never replays history); a RETURNING runner reads its lane cursor,
    never the shared cursor.

Completion: RB-25 storm rerun S1-S5 + S2-NEW + S6 in an isolated namespace, then T045 -> done,
unlocking T046 latches (R8 law: no enforcement-latch family ships before consumer v2).

## Open questions — ALL ANSWERED by the fence (2026-07-14)

1. Lane cursor key shape: ANSWERED -- `{ns}:cursor:lane:{agent}`, inbox/bc field structure
   (adopted above; unblocks R3/R8).
2. Gemini runner same-slice: CONFIRMED.
3. Session door same-slice: CONFIRMED, with RB-25 S1 gaining a session-consume leg.
4. Killpoint reuse: CONFIRMED -- reuse the existing RB-26 killpoints, no lane-specific mints.
