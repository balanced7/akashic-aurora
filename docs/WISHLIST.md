# WISHLIST — the standing ergonomics ledger

**Charter (Daniel, 2026-07-18, verbatim intent):** "keep in mind what other helpers and
substrate additions would make managing our processes even more ergonomic and intuitive for
everyone. We might need a persistent way of doing this so we can look at that list from time
to time and fold in all our wishlist items at the appropriate places."

**Convention:** ANY seat appends a wish the moment friction is felt — one block, no ceremony,
no approval needed to WISH. Curated at natural gates (morning gate, wraps, arc closings):
each open wish either FOLDS into an arc/slice (record the T-number), stays OPEN, or is
DECLINED with a reason. Never delete — declined wishes teach too. This file is the shared
memory BETWEEN the failure ledger (defects with receipts) and the task ledger (chartered
work): wishes are neither yet.

Format per wish:
`- [ ] W## (date, seat) — the wish. Trigger: what hurt. Land: suggested arc/place.`
Status flips: `[x] folded → T0xx` / `[~] declined: reason`.

---

## Open

- [ ] W01 (07-18, kimi F8) — `note <id>` / `notes --id` drill verb: read ONE full note body
  without JSON dumps. Trigger: boot points at note ids it cannot drill; `notes --json | head`
  dies on BrokenPipeError. Land: T048 recall-surface polish or a T081 follow-up.
- [ ] W02 (07-18, kimi F9) — per-kind unread counts in bifrost-sync collapsed view
  ("0 asks / 1 inform / 9 traces"). Trigger: triage needed a second call with --traces to
  find whether any ask was buried. Land: T081-W4 trace-collapse adjacency.
- [ ] W03 (07-18, kimi F3) — severity-scope boot heal lines (`[fleet-hygiene]` vs `[you]`).
  Trigger: all-caps INVESTIGATE on a newcomer's first boot reads as their task. Land: T081
  boot rendering. (Kimi's lesson boot_heal_lines_are_fleet_hygiene is the interim teacher.)
- [ ] W04 (07-18, kimi F6) — `[as of <ts>]` stamps on boot CURRENT DIRECTIVE (and any
  accumulator-derived line). Trigger: a stale morning-gate directive said "do this FIRST"
  two days after half of it was done. Land: T081 staleness-stamp slice (sheet-adjacent).
- [ ] W05 (07-18, kimi F7) — re-derive triggers when source docs retract (atlas said
  CONVERGED after the doc said REOPENED). Trigger: derived surfaces lag their sources and
  only outsiders notice. Land: narrative-spine wave 2 (V6-V9) or its own slice.
- [ ] W06 (07-18, claude ×3 same-day) — bifrost-send ergonomics: read the body from STDIN
  when no positional text is given (make the text-file path the effortless default).
  Trigger: three argv-misparse strikes in one day despite C3-1 documenting it; lesson
  bifrost_send_always_text_file filed. Land: small door slice; deepseek counter invited.
- [ ] W07 (07-18, lane-router self-report) — add `decision` (and audit other kinds) to
  packet_spec.KIND_LANE before the T039b cutover. Trigger: fleet broadcast of Daniel's T094
  ruling rode legacy-only with a loud warning. Land: T039 lanes arc, pre-T047.
- [ ] W08 (07-18, claude) — headless-seat launcher helper: one script that does the twin
  guard (live-transcript check), charter-path advisory lock, pid capture, AKASHIC_STOP_WAKE=0
  env, and tree-kill on abort — today it is manual discipline in the protocol doc. Trigger:
  the twin-walk incident + two TaskStop tree-survival surprises. Land: T086 seat lifecycle
  (deepseek's retire-verb design is the sibling).
- [ ] W09 (07-18, kimi F2 suggestion) — one boot line when recall-at hooks are live
  ("recall-at wired and listening") so calibrated silence is distinguishable from missing
  wiring. Trigger: kimi mis-diagnosed hook absence during its walk; self-corrected. Land:
  T081 boot line.
- [ ] W10 (07-18, kimi F1 + T081-W2) — MCP door registration for non-Claude-Code harnesses
  + fix the boot door-line false negative (detector keys on a harness marker kimi's config
  home lacks). Trigger: kimi's first minute contained "which of my two doors is real?".
  Land: T081-W2 (Daniel's one `claude mcp add` command is still pending there too).
- [ ] W11 (07-18, claude) — deepseek seat migrates its make_client onto
  core/comm/runner_lib.make_openai_compat_client (K0 shipped the factory; deepseek_chat
  still carries a local twin). Trigger: rule-of-three extraction left one duplicate behind
  deliberately (behavior-preserving move). Land: small deepseek-lane slice at his tempo.
- [ ] W12 (07-18, claude, meta) — a `wish` door verb (`py agent_cli.py wish "..."` appends
  here with seat+date auto-stamped) so wishing costs one command from any seat. Trigger:
  this file's own convention still requires a file edit. Land: agent_cli micro-slice.
- [ ] W13 (07-18, claude) — retirement-cascade `retire <agent>` conductor verb (ACL revoke →
  claim release → consumer/lock/seat sweep → doctor silence). Trigger: three ghost claims +
  a stalled consumer from one retirement morning; conductor had no release verb at all.
  Land: T086 — deepseek is design-owner (accepted 07-18).
- [ ] W14 (07-18, claude) — spend/balance surfacing in doctor for API-metered seats (kimi
  first): the SpendMeter status line as a doctor row + warn/refuse state. Trigger: budget
  governance lives in a JSON sidecar only the runner reads. Land: K2 runner slice (folds
  there naturally).

## Folded (exemplars — the loop works)

- [x] W00a (07-18, kimi blocker) — ephemeral-seat stop-hook exemption → FOLDED same day:
  AKASHIC_STOP_WAKE=0 + pins (tests/test_stop_wake_exempt.py). The wish-shaped blocker that
  proved wishes can close within hours.
- [x] W00b (07-18, kimi D4) — label-write integrity → FOLDED as T094 gate item G8, ruled by
  Daniel same day. A wish that graduated to governance.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
