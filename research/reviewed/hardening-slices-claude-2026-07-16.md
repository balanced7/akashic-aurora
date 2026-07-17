# Crash-Hardening Slices — claude blind half — 2026-07-16 night

Status: FILED blind (composed from my pre-brief designs; deepseek's twin filed independently
at hardening-slices-deepseek-2026-07-16.md — reconciliation is the next step, then Gemini on
both). Context: docs/failure-ledger-2026-07.md C4-2 + C7-4; jester-synthesis P1/P2.

## S1 · C7-4 — MCP boot() wedge (diagnosis now EMPIRICALLY COMPLETE to the phase level)

The surface work (mcp-surface-claude-2026-07-16.md) reduced this from mystery to bisect:
SDK exonerated, `_run` mechanics exonerated, payload size exonerated — **a runtime side
effect inside `cmd_boot` parks the server's outbound writer until the next inbound frame.**
Remaining design:
- **Bisect protocol (joint):** run cmd_boot under the mixed-server driver with phases
  disabled one at a time (order: subprocess spawns → thread/loop touches → logging/rich
  reconfig → signal/atexit). The first phase whose removal unwedges = the mechanism, NAMED.
- **Fix rule:** guard or relocate that side effect only. If it's load-bearing for CLI boot,
  split: `boot_core()` (pure render, MCP-safe) + CLI wrapper (side-effectful). No
  subprocess-door workaround unless the mechanism is named first and documented.
- **Pins:** (1) stdio-driver regression: real server, single tools/call boot, NO second
  inbound frame, response < 5s (driver exists — promote to tests/); (2) no phantom
  double-boot events on retry; (3) unwedge receipt archived in the ledger entry; (4) W2
  un-gates only when pin-1 is green on two consecutive runs (warm+cold).

## S2 · C8-3 — hook double-fire

- **Single registration surface:** user-level absolute-path registration WINS (survives cwd
  and repo moves); the project-level entry is REMOVED and replaced by a comment pointing at
  the user-level registration (discoverability without double-fire).
- **Race-proof dedup (defense in depth):** the hook computes key = (session_id,
  tool_call_id-or-payload-hash) and claims it ATOMICALLY before acting — O_EXCL file create
  in the session temp dir (or Redis SETNX, TTL 60s). First claimant proceeds; second exits
  0 silently. This kills the documented load_seen-before-mark_seen race for good.
- **Hook census (class fix):** a pin that reads BOTH settings surfaces and asserts every
  hook script appears in exactly ONE — covers session_signals (which double-fired tonight,
  muddying crash forensics) and any future hook.
- **Gauge correction:** emit one `gauge_correction` event marking the funnel's `surfaced`
  series pre-fix as ~2× inflated; funnel render annotates pre-fix numbers. No silent recount.
- **Pins:** double-invoke sim → exactly one injection logged; census test green; correction
  event present; post-fix funnel ratio drifts toward ~2× the old value metric.

## S3 · P2 — ACL cap-ceiling pre-commit gate (~40–60 lines)

- **Mechanism:** pre-commit hook diffs STAGED security/acl.json against HEAD. For every
  added/changed grant G: caps(G) ⊆ caps(granted_by(G)) **resolved at HEAD** (self-upgrade in
  the same commit therefore blocks); role escalations map through the role→caps table so a
  role bump can't smuggle caps.
- **Edges:** HEAD has no acl.json (bootstrap) or granted_by="root" → require the human
  escape hatch. Escape hatch = commit trailer `ACL-Approved-By: <human>` or env
  ACL_GATE_HUMAN_OK=1; EITHER path emits an audited `acl_human_override` event. Unparseable
  staged file → BLOCK (fail-closed). Non-acl commits: zero cost (hook exits on path filter).
- **Pins:** escalation blocked; subset grant passes; same-commit granter-self-upgrade
  blocked; bootstrap+override passes WITH audit event; dirty JSON blocks; non-acl commit
  untouched.

## S4 · P1 — ground-truth gate v1 (the C9 antidote's first brick)

- **Claim extractor (pure, mechanical):** regex `\bT(\d{3})\b` within ±40 chars of a status
  token (done/shipped/complete/verifying/in_progress/parked/blocked/abandoned/proposed,
  case-insensitive) over note bodies. Resolver: the task ledger's own read API.
- **Write-time (note door, CLI + MCP twin):** mismatch → note STILL WRITES (write-once
  doctrine intact) but is stamped `ground_truth: MISMATCH(<claim> != <ledger>)` in meta, a
  LOUD line returns to the writer, and a `ground_truth_mismatch` event fires.
- **Boot-time (the living check):** every note rendered in boot is re-validated LIVE (claims
  go stale — a true-when-written claim can be false now); mismatched notes render under a ⚠
  GROUND-TRUTH banner naming the disagreement. `where-we-are` (RED V1's target) checked
  first-class.
- **Scope honesty:** v1 catches STRUCTURED claims only (task-id + status). Prose fabrication
  rides the later semantic wave. Lessons door (learn result/recommend) gets the same
  extractor in FLAG-only mode — v1.1 if noise allows.
- **Pins:** fabricated "T075 DONE" (ledger: parked) → write-flag + boot-banner; true claim
  clean; stale-flip caught at boot; garbage body never crashes the door (fail-open +
  counter); boot overhead < 50ms at 25 notes.

## S5 · T086-S5/S6 completion + the C4-2 supervisor charter

deepseek's lane (his stranded S6 impl reviewed clean; S5 tests were failing pre-crash — his
continuation states why + the green path). The C4-2 additions to the supervisor charter:
- **Owned pid census:** the supervisor REGISTERS every child it spawns (pid, agent, session,
  role tag); the census is the ONLY legal kill-list.
- **`fleet quiesce`:** signal runners finish-current-and-hold → bounded wait → report
  (land-in-flight is a first-class verb, not a habit).
- **`fleet cleanup [--force]`:** reaps census-listed orphans ONLY; REFUSES while any
  registered test/pass is live unless --force (audited); load-bearing pids (wake watchers,
  MCP servers, the UI) live on a supervisor-maintained DENYLIST no sweep can touch.
- **Pins:** cleanup-refuses-mid-test; planted stranger python pid survives a cleanup
  (census-only proof); --force emits audit; quiesce lands in-flight work before reap.

## Cross-slice order + gates

S2 first (honest gauges for everything after), S1 bisect+fix (un-gates T081-W2), S3 before
ANY acl.json edit (Daniel's grant review lands on rails), S4 before Jester v1 (its stated
launch gate), S5 rides deepseek's lane in parallel. Every slice ships with its pins in the
same commit; receipts to the failure ledger (C4-2/C7-4/C8-3 close only on class-level fix).
