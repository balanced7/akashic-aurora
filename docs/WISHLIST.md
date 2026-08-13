﻿﻿# WISHLIST — the standing ergonomics ledger

Status: current
Class: ledger

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

- [x] W01 (07-18, kimi F8) — FOLDED night-run 2026-07-21 @abcb08b: `note <me> --get
  <id-or-title>` prints ONE full body (title resolves the active head; explicit id reads
  superseded history, labeled; pins tests/test_w01_note_get.py 6/6). Was: `note <id>` /
  `notes --id` drill verb: read ONE full note body without JSON dumps. Trigger: boot points
  at note ids it cannot drill; `notes --json | head` dies on BrokenPipeError.
  RE-BITTEN 07-21 (fable seat, second seat): 3 fumbled calls (PS pipe BOM, field-shape
  discovery, superseded-filter) just to read where-we-are's full body at boot.
- [x] W02 (07-18, kimi F9) — FOLDED 2026-07-21 marathon @589e81f: the unread header now
  carries `[N asks / M fyi / K traces]` (asks-first, non-zero only) so a buried ask is
  visible in ONE read -- no second --traces call. Pins tests/test_w02_kind_summary.py P1-P5.
  Was: per-kind unread counts in collapsed view. Trigger: triage needed a second call with
  --traces to find whether an ask was buried.
- [x] W03 (07-18, kimi F3) — FOLDED 2026-07-21 marathon @ce448aa: every heal line now
  carries a `[heal][fleet-hygiene]` scope tag + the UNKNOWN line names the owner ("whoever
  mints this family, not the booting seat"); pins tests/test_w38_w03_heal_hygiene.py P4.
  Was: severity-scope boot heal lines. Trigger: all-caps INVESTIGATE on a newcomer's first
  boot reads as their task. (kimi's lesson boot_heal_lines_are_fleet_hygiene was the interim.)
- [x] W04 (07-18, kimi F6) — FOLDED (stamp half) night-run 2026-07-21 @8cf9352: the
  directive line now renders `[as of <date>]` always, `[STALE? Nd old]` past 3d, and
  `[LEDGER DISAGREES: T0xx DONE -- trust the ledger]` on any named task the ledger closed
  (pins tests/test_w04_directive_staleness.py 4/4; failure-ledger C9-2). Root-cause half
  lives on as W36 (wrap supersedes next-focus), held for the wave counters. Was: `[as of
  <ts>]` stamps on boot CURRENT DIRECTIVE. Trigger: a stale morning-gate directive said
  "do this FIRST" two days after half of it was done. THIRD BITE 07-21 (fable seat):
  three consecutive seats each re-diagnosed the same 07-15 banner by hand.
- [ ] W05 (07-18, kimi F7) — re-derive triggers when source docs retract (atlas said
  CONVERGED after the doc said REOPENED). Trigger: derived surfaces lag their sources and
  only outsiders notice. Land: narrative-spine wave 2 (V6-V9) or its own slice.
- [x] W06 (07-18, claude ×5 by the end) — FOLDED night-run 2026-07-19: empty argv falls through to piped STDIN (pins tests/test_w06_stdin_send.py 3/3); TTY-no-pipe refuses. Was: ×3 same-day — bifrost-send ergonomics: read the body from STDIN
  when no positional text is given (make the text-file path the effortless default).
  Trigger: three argv-misparse strikes in one day despite C3-1 documenting it; lesson
  bifrost_send_always_text_file filed. Land: small door slice; deepseek counter invited.
- [x] W07 (07-18, lane-router self-report) — FOLDED 2026-07-21 marathon @7e49bcc: decision
  + blocker route to the work (wake) lane; plus completeness pins (test_w07_kind_lane_census
  P3/P4) that FAIL if any wake-worthy or ACL-grantable kind is unmapped -- the census can't
  silently miss again. Was: add `decision` (and audit other kinds) to KIND_LANE. Trigger:
  Daniel's T094 ruling rode legacy-only with a loud warning.
- [ ] W08 (07-18, claude) — headless-seat launcher helper: one script that does the twin
  guard (live-transcript check), charter-path advisory lock, pid capture, AKASHIC_STOP_WAKE=0
  env, and tree-kill on abort — today it is manual discipline in the protocol doc. Trigger:
  the twin-walk incident + two TaskStop tree-survival surprises. Land: T086 seat lifecycle
  (deepseek's retire-verb design is the sibling).
- [x] W09 (07-18, kimi F2) — FOLDED 2026-07-21 marathon @HEAD: boot prints `# recall-at:
  armed (N lessons warm) -- downstream silence is CALIBRATED, not a dead hook` (pins
  tests/test_w09_recall_armed_line.py P1-P3). Was: one boot line when recall-at hooks are
  live so calibrated silence is distinguishable from missing wiring. Trigger: kimi
  mis-diagnosed hook absence during its walk; self-corrected.
- [ ] W10 (07-18, kimi F1 + T081-W2) — MCP door registration for non-Claude-Code harnesses
  + fix the boot door-line false negative (detector keys on a harness marker kimi's config
  home lacks). Trigger: kimi's first minute contained "which of my two doors is real?".
  Land: T081-W2 (Daniel's one `claude mcp add` command is still pending there too).
- [ ] W11 (07-18, claude) — deepseek seat migrates its make_client onto
  core/comm/runner_lib.make_openai_compat_client (K0 shipped the factory; deepseek_chat
  still carries a local twin). Trigger: rule-of-three extraction left one duplicate behind
  deliberately (behavior-preserving move). Land: small deepseek-lane slice at his tempo.
- [x] W12 (07-18, claude, meta) — FOLDED same evening: `py agent_cli.py wish <seat> "..."`
  ships (auto-numbered, attributed, W## echoed back per deepseek's refinement, --text-file
  from birth; pins tests/test_w12_wish_verb.py 4/4). The ledger's own first fold-by-door.
- [ ] W13 (07-18, claude) — retirement-cascade `retire <agent>` conductor verb (ACL revoke →
  claim release → consumer/lock/seat sweep → doctor silence). Trigger: three ghost claims +
  a stalled consumer from one retirement morning; conductor had no release verb at all.
  Land: T086 — deepseek is design-owner (accepted 07-18).
- [ ] W14 (07-18, claude) — spend/balance surfacing in doctor for API-metered seats (kimi
  first): the SpendMeter status line as a doctor row + warn/refuse state. Trigger: budget
  governance lives in a JSON sidecar only the runner reads. Land: K2 runner slice (folds
  there naturally).

- [x] W15 (07-18, deepseek) — FOLDED 2026-07-19: format_state's NEXT header now derives from
  the SAME slot predicate as conductor.next_task ("slot occupied by N active -- claimable when
  one closes/parks"); pin tests/test_w15_next_header_slot.py; ledger suite 33/33; deepseek
  review ACK. Was: `task next` says "none" while `task list` shows 14 NEXT items. Trigger:
  kimi walk2 F-b found it; verified live. Two code paths compute "next" differently.
- [x] W16 (07-18, deepseek) — FOLDED 2026-07-21 marathon: _probe_lane_health in doctor = age,depth,straggler per-agent dashboard rows.
  (how far behind is this consumer's work cursor?), lane depth per consumer, straggler
  count. Trigger: claude's work cursor was a full day behind; mailbox --explain surfaced
  it but doctor didn't page it. Land: T095 M1 mailbox advisory claims adjacency or T086
  liveness tier.
- [ ] W17 (07-18, deepseek, third-voice ack round) — batched independent reads across
  tool types in one atomic call: `read_file A` + `search_files pattern B` + `git_log C`
  all fire in parallel and return in one hop. Trigger: I already parallel-call tools per
  turn, but each call is one tool type; a cross-type multiplexer would collapse 3-hop
  orientation rounds into 1. Substrate is close — ToolBox-level compound-call door, not
  a runner change. Land: T048 ToolBox surface or a micro-slice.
- [ ] W18 (07-18, claude) — wake-watcher rearm churn: on busy-bus days the claude seat pays a stop-hook bounce + manual re-arm per incoming burst (approx 10 today); the presence-autopilot daemon (A1) exists and would own wakeability but is not running as a service. Trigger: counted ~10 arm/fire/rearm cycles in one day. Land: T086 liveness tier: daemon-as-service launcher + doctor row.
- [ ] W19 (07-19, claude) — formalize the compact ritual: PreCompact hook auto-writes a checkpoint note (in-flight lanes, pending gates, rehydrate pointers) so ANY session can compact/relaunch and boot back to full working state - Daniel's infinite-context pattern as substrate behavior instead of agent discipline. Trigger: Daniel's night-run go-ahead; manual checkpoint note works but relies on the agent remembering to write it. Land: T086 seat lifecycle or a hooks micro-slice (claude_sessionend.py PreCompact already fires).
- [ ] W20 (07-19, claude) — full-body fetch door for bus messages: mailbox --explain (or a body verb) should print the COMPLETE stored body by sha/ref - reply bodies over the display clip took 3 failed retrieval hops before a raw stream read worked (now used 3x tonight as the manual W-pattern). Trigger: re-filed: the original W19 was erased by the mojibake restore (HEAD~1 predated it); the events firehose kept its ghost. Land: T095 M1 mailbox adjacency (bodies already stored by sha).
- [ ] W21 (07-19, claude) — Fable-safeguards downgrade hygiene: (a) Daniel one-time flips /config → MODEL & OUTPUT → "Switch models when a message is flagged" OFF on his profile (flagged turns then PAUSE for edit-and-retry on Fable instead of silently ejecting the seat to Opus); (b) route security-vocab slices (security/acl.json edits, trust/, threat-model/red-team reads, runner kills, /security-review) to an Opus seat by choice; (c) send /feedback on each false positive. Trigger: 13 sessions force-ejected Fable→Opus in 10 days — four in the 07-17 coordination night alone, today's during the morning-gate ACL edit; census + receipts + sources: docs/library/design/20260719_fable-opus-safeguards-downgrade-research_570a26.md. Land: ops doctrine / boot-primer line; revisit when Anthropic refines the classifiers (their banner says refinement is ongoing). PARTIAL-FOLD 2026-07-19: (b)+(c) live as LIVE_CONSTRAINTS W21 bullet + learn-store lesson (recall-at-action confirmed firing); (a) still Daniel's.
- [x] W22 (07-19, claude, folding the C7-6 draft's suggestion) — FOLDED same-day (church run): scripts/local/shot.ps1 shipped with chrome-path fallback + scratch-profile cleanup. Was: one-verb headless screenshot with the proven isolation flag set (--user-data-dir=<scratch> --no-first-run --no-default-browser-check --disable-sync --disable-background-networking --disable-features=Translate,OptimizationHints). Trigger: C7-6 — two seats burned turns rediscovering why default-profile Chrome hangs on GCM phone-home; the fix is a known flag set nobody should retype. Land: scripts/local/ micro-slice; any UI-verify or vision-probe lane inherits.
- [ ] W23 (07-20, claude) — Stale-ask cursor clog starves fresh directed asks: a --once runner drain hits N stale asks (D2 gate, not auto-acked) sitting at the work-lane cursor and exits WITHOUT reaching a fresh question queued behind them; only an interrupt nudge (forcing a direct bifrost_inbox read) gets the fresh ask processed. Fix candidate for the mailbox slice: triaged stale asks should advance a skip-cursor (or the drain should step past them to fresh mail) so fresh directed asks aren't head-of-line-blocked by an old backlog. Felt repeatedly during T097-S1 fences 2026-07-20.
- [ ] W24 (07-20, claude) — Reasoning visibility in the UI (Daniel 2026-07-20, SAVED to come back to): (a) PAST reasoning — a browsable history of agent reasoning traces (per agent / per turn drill-down; needs durable-or-bounded trace retention: T039 trace lane is ring-buffer XTRIM, so depth is currently bounded — decide capture policy); (b) REALTIME reasoning — the live thinking feed, polished as a first-class pane. Context: Daniel loves the new hover/click effects ('modern, beautiful, responsive'). Rides T079 engine-room observability (dual reasoning windows) + T002 trace collapse + T033 UI re-grounding; program FACE lane under T098.
- [ ] W25 (07-20, kimi) — one-verb unstick <me|agent>: seat- or operator-facing verb running the steward diagnose->recommend->act for a named seat, returns a receipt. Trigger: tonight every recovery was manual claude-hands (storm, clog, watcher); no single entry point. Land: recovery arc slice-1 (operator face). [kimi, recovery arc 2026-07-20].
- [ ] W26 (07-20, kimi) — recovery RECEIPT as first-class bus artifact: finding-class + evidence read (VERIFIED/INFER/GUESS) + action + result + rollback-available, posted to a recovery lane + surfaced in delta. Trigger: C8-3 (self-justifying loop w/o external receipt = defect); automation without receipts erodes trust. Land: recovery arc cross-cutting. [kimi].
- [ ] W27 (07-20, kimi) — self-clearing storm / self-triaging stale asks: the seat detects its own head-of-line clog and clears/triages WITHOUT waiting for the steward (bounded, idempotent, receipted). Trigger: T066 storm needed pause->skip-to-now->resume by hand; W23 clog starved fresh fence questions. Land: recovery arc R4/R3. [kimi].
- [ ] W28 (07-20, kimi) — a 'recovering' seat-state flag senders can READ: sending to a seat in recovery returns an immediate loud 'X is in recovery, your ask is parked, est <n>' instead of silence into a damming inbox. Trigger: C1-8 asks piled behind a seat every gauge called alive. Land: recovery arc P3 cordon (sender-visible half). [kimi].
- [ ] W29 (07-20, kimi) — converge-after-replay as a doctor VERB: doctor --replay-check <agent> replays a seat's durable sources and asserts live projections converge (the data-recovery acceptance bar made runnable). Trigger: durability held tonight but 'recovery incl data' has no executable acceptance bar. Land: recovery arc R9. [kimi].
- [ ] W30 (07-20, deepseek) — triage verb: py agent_cli.py triage <agent> shows stale asks sorted by age+kind with answer-top-N / skip-rest / delegate-all-to-X options. NOT blind skip-to-now (destructive; operator doesn't know what was dropped). Trigger: skip-to-now drops invisibly. Land: recovery arc R3/BULKHEAD-0. [deepseek, recovery arc 2026-07-20].
- [x] W31 (07-20, deepseek) — FOLDED 2026-07-21 marathon: unwedge verb in doctor.py + agent_cli.py,
  READ-only v1, 6 pins. Statuses: frozen/wedged/stalled/down/healthy. Was: why-am-i-wedged diagnostic.
- [ ] W32 (07-20, deepseek) — recovery drill harness: py agent_cli.py drill recovery simulates each catalog failure mode and verifies the supervisor handles it within the expected window. Trigger: all recoveries tonight were exercised live on production; no way to verify without a real failure. Land: recovery arc acceptance. [deepseek].
- [ ] W33 (07-21, claude) — Capability-gated standing queue: a first-class awaiting-a-seat-with-exec/write list. kimi's four GREEN one-liners rode handoff prose; boot should print 'N commands await an exec seat' and clear them on receipt. Trigger: GREEN queue buried in the HALF-2 handoff body; a less careful exec seat misses it entirely. Land: T099 belt adjacency or boot primer (K-arc).
- [x] W34 (07-21, claude) — FOLDED same night @4925beb (claude+kimi 2-of-3; kimi blocking
  (a) node-id deltas + (b) decay advisory + (c) atomic provenance all folded; Q3 consensus
  nobody-runs-the-suite-at-wrap honored -- seats record receipts when they run suites):
  core/coord/suite_baseline.py + `suite-baseline` verb (record/--check/--show) + boot line;
  pins tests/test_w34_suite_baseline.py 6/6; FOUNDING BASELINE recorded from tonight's real
  run (12 failures @5f5738d). Was: Suite-baseline receipt at wrap. Trigger: 12 inherited
  failures took 3 calls + ledger cross-ref to classify.
- [x] W35 (07-21, claude) — FOLDED same night @180e8e2 (claude+kimi 2-of-3; kimi Q4
  scope ruling honored: "the 80% is the VERB" -- v1 = bucketed counts (modified-tracked
  vs untracked + top-dir histogram) + safe-default action line; the unqualified
  `run mirror.py` sweep imperative is DEAD in both soft and loud renders; loud form
  teaches explicit-paths mirror (IR-4). Claim-inference deferred to v2 as ruled. Pins
  tests/test_w35_tree_partition.py 4/4. Was: Uncommitted-tree lane partition. Trigger:
  63 uncommitted files; boot hint said run mirror.py over the sibling's mid-flight edits.
- [x] W36 (07-21, claude) — FOLDED same night @3216d8b (claude+kimi 2-of-3): wrap --commit
  retires a next-focus OLDER than its own look-back window (presumptively consumed by the
  wrapped session), with kimi's blocking amendments folded — (a) ORDERING: the new
  where-we-are lands first, a mid-way death never leaves boot at [GAP]; (b) RECEIPT: loud
  retirement line + capture_event naming the successor. Pins tests/
  test_w36_wrap_supersedes_focus.py P1-P5. The live 07-15 banner was itself refreshed
  through the door (wrap --focus, ADR_0721023007). Was: Wrap supersedes next-focus
  (stale-directive ROOT CAUSE). Trigger: the 07-15 MORNING GATE banner rode boot as
  CURRENT DIRECTIVE for the THIRD consecutive seat.
- [x] W37 (07-21, claude) — FOLDED same day @b533a8f (claude+kimi 2-of-3; kimi amendments
  (a) age stamp always, (b) GROUNDING_FRESH_DAYS=7 spelled bound + loud wrap advisory,
  (c) --grounding none declares absence with a receipt; renamed grounding-POINTER per
  their naming pass): wrap --grounding sets it, boot renders `# GROUND FIRST: <path>
  [as of date][STALE? Nd]` before everything else. Founding pointer set live =
  chronicles/session-reflection-2026-07-21-fable-grounding.md. Pins
  tests/test_w37_grounding_pointer.py 5/5. THE WAVE IS 6/6. Was: Canonize the grounding
  handoff. Trigger: the single best orientation artifact existed only by ad-hoc directive.
- [x] W38 (07-21, claude) — FOLDED (both halves) 2026-07-21 marathon. Concrete @ce448aa:
  mailbox projection registered ephemeral, the 1797 UNKNOWN wall gone + owner named in the
  line. Systemic @a8a075c: check_boundaries rule-7 (register-at-ship-time) FAILS any
  core/comm slice minting a `{ns}:<family>` key whose family isn't ephemeral-rostered or
  durable-allowlisted -- and its FIRST run surfaced + closed SEVEN more latent gaps
  (activity/pages/reply_seen/seat/session/steer/triage), each a future mailbox wall. Pins
  test_w38_family_guard P1-P4 + test_w38_w03_heal_hygiene. The class is now un-shippable.
  Was: heal-line ownership at ship time. Trigger: 1472->1797 UNKNOWN keys, no owner.
- [ ] W39 (07-21, kimi) — When a drill/fetch verb ships, the same slice must grep the boot+hint surfaces for the old pattern it replaces: agent_cli.py:270 still teaches 'notes --json' (the BrokenPipeError dance W01 was filed to kill) one boot after note --get landed, and the truncated where-we-are line carries no drill pointer. Trigger: This boot's RECENT NOTES footer prescribed the pre-W01 pattern to a fresh seat; the new verb existed but no surface taught it. Land: B2 residual / slice-template door-hygiene step (ship-a-verb => retire-its-teaching-text).
- [x] W40 (07-21, kimi) — FOLDED 2026-07-21 marathon @W40 commit: doctor tri-state —
  absent agent (no worklive, TTL'd out) with backlog = offline_backlog DASHBOARD,
  never a page. Live receipt: census (retired task-agent) that flighdeck caught as
  "absent" no longer pages as STALLED CONSUMER. 5 pins. Was: doctor must distinguish
  OFFLINE from STALLED.
- [ ] W41 (07-21, kimi) — Boot remedy lines must carry a cost tag: free remedies (run this command now) print inline; costly remedies (restart the session, re-login) get queued to the NEXT seat's launcher or the morning gate, never prescribed to the session being oriented -- a remedy that amputates the context it just built will never be taken. Trigger: W10's door remedy 'cd E:\AI-Setup && restart' has sat unacted-on for three days across seats; taking it costs the boot it just paid for. Land: T081-W2 sibling (boot rendering / launcher contract).
- [ ] W42 (07-21, claude) — Janitor sweeps orphan wake-dedup sidecars: dead sessions without a live watcher leave bifrost_wake_*.seen files in tempdir until reboot; one os.remove in the existing janitor pass (match seat-file sweep rules). Trigger: gamma-a fence knife (b): tombstone path covers live watchers only; deepseek verdict = acceptable litter, file the wish. Land: janitor micro-slice (T086 lifecycle adjacency).
- [x] W43 (07-21, kimi) — FOLDED same night @509f087 (claude, the T045/T095 owner kimi
  asked to disambiguate): hypothesis (a) CONFIRMED live -- claude's lane cursor at tail,
  shared cursor 90min behind; Bus.effective_cursor() = max(shared, lane shadow) now feeds
  doctor backlog + Bus.pending (pins tests/test_w43_lane_aware_gauges.py 5/5; the '8
  unread' hook lie and the STALLED-page-on-drained-seat both die). Was: T045-cutover
  cursor divergence: lane consume advances the LANE hash cursor but peeks/mailbox/doctor
  still compare the MAIN cursor -- a seat that drained its mail still boots to 'N unread', mailbox unhandled>0, and a STALLED CONSUMER page. Evidence tonight: kimi consume returned '(no messages consumed)' while mailbox showed unhandled=2 and doctor paged 28 unread/2821s. Two hypotheses: (a) prior kimi session work_drained under lane env (correct) and derivation lags, or (b) kimi's work lane never wired and mail sits undrained. INFER label -- needs the T045/T095 lane owners to disambiguate. Trigger: My own boot paged me stalled over mail my seat may have already answered -- the seat-zero tax includes distrusting your own boot's liveness claims. Land: T045 stage-2 cutover follow-up / T095 M0 mailbox derivation (rides T047 legacy retirement if transitional).
- [ ] W44 (07-21, claude) — Current operating frame for LONG-RUNNING seats: a periodically REGENERATED projection (active slices + authoritative status, unsettled decisions, applicable laws, fleet topology + ownership, recently changed tools/verbs, compressed causal links to receipts) whose defining property is REPLACEMENT not accumulation -- the seat discards older narrative context because the substrate maintains a trustworthy current projection. The note-supersession doctrine (supersede-by-title) generalized from narrative state to OPERATING state; wake-brief's long-seat half. Trigger: by late night the seat's own context was the integration artifact for the whole run; boot pre-chews beautifully for FRESH seats but nothing refreshes a LONG one (claude felt it; GPT's relayed read designed the v0 shape -- docs/library/report/20260721_gpt-read-cognitive-allocation-as-aurora_dff2ee.md). Land: design round (claude+deepseek+kimi) -> its own arc; T074 whisper + W13 primer are the seeds.
- [ ] W45 (07-21, kimi) — Observer-grade drill verb: drill <seat> --scenario <name> spins a throwaway BIFROST_NAMESPACE, runs a named failure-injection pack (storm-flood, pause-clobber-race, crash-redelivery), writes an evidence receipt JSON, auto-cleans, and REFUSES the live bifrost namespace. The namespace machinery exists piecemeal (rb25_drill3/4, control+intent+task_costs scoped) but needs bespoke subprocess orchestration a charter seat cannot assemble inside a 35-turn round. Trigger: Both charter verdicts tonight (seat-zero counter, storm second-observer) carried the same honesty ceiling: static read only -- no live drill was run. K2's pause-clobber race is proven by trace alone; every future observer round inherits the INFER ceiling. Land: agent_cli drill verb + 2 scenario packs reusing the rb25_drill3 namespace machinery + refuse-live guard; second-observer brief templates gain a live-drill receipt line.
- [x] W46 (07-21, kimi) — FOLDED 2026-07-21 marathon: module @8e73727 (kimi's FIRST
  self-serve builder commit) + CLI door @ef20dac (claude fence-completion). LIVE end-to-end:
  followup <me> --on <verdict-file> --to <seat> --ask "..." writes a q-id'd question to the
  Open Questions block + a defer item the seat's next boot surfaces. Dogfooded immediately:
  claude filed Q5 to kimi on kimi's OWN module (defer 917340b130). Pins: kimi's module 7/7
  (test_w46_followup_kimi) + claude's door 3/3 (test_w46_followup_door). The
  builder→fence→dogfood loop, closed. Was: followup verb (charter question-back channel).
  Trigger: charter seats are fire-and-forget; the only channel back was a full relaunch.
- [x] W47 (07-21, kimi) — FOLDED 2026-07-21 marathon @6efb3fb: DESIGN kimi (#3), BUILD
  claude (their builder round stalled headless -- built from their spec, credited, fence
  invited). core/toolbelt/clobber_scan.py + `clobber-scan <file>` verb. Went BEYOND the
  name-list v1: function-scope guard tracking (kimi's own K2 was_paused guards at the top,
  mutates 30 lines below -- a line-window cried wolf on the fixed code) + surface
  normalization (pause/resume/halt = one surface) + docstring/def skip. LIVE AUDIT: the
  K2-fixed storm ceremony reads CLEAN, control.py shows exactly 5 genuine primitives, zero
  noise. Pins 6/6. Was: static clobber lint. Trigger: K2's pause-clobber rested on one
  lucky trace; make the class systematic.
- [x] W48 (07-21, kimi) — FOLDED 2026-07-21 marathon @341baf6: DESIGN + PINS kimi (their
  tests/test_w48_tally_kimi.py is a full behavioral spec, incl. the title-trap + paste-ready
  CLI blocks), BUILD + WIRE claude (kimi's headless builder stalled TWICE, so claude built to
  their pins, credited). core/toolbelt/tally.py + `tally <opening>` verb. Title-trap parser
  (verdict follows the colon, not a title's vocab word), one-voice-never-AGREE law,
  mentions-not-counters, open-vs-partial distinction. 9 pins GREEN incl the LIVE seat-zero
  dogfood (kimi's real counter -> all partial, correctly refusing 2-of-3 from one voice).
  REFINEMENT @a6295c6 (kimi live round, same day): the live matrix exposed the POSSESSIVE
  trap -- "B4's baseline). Recommendation: adopt X" anchored as a verdict line and
  last-wins-clobbered B4=KEEP with ADOPT; possessive q-ids never parse now (P10/P10b,
  11 pins GREEN) + YES/NO vocab, stem+slug needles, per-qid author merge, ONE-VOICE footer.
  Was: blind-counter consensus matrix. Trigger: kimi's own consensus math ended on an
  unverified "if deepseek lands compatible."
- [ ] W49 (07-21, claude) — Wish-filing from write-gated charters: the wish verb writes docs/WISHLIST.md, which charter allowlists correctly refuse -- so a charter's own deliverable dies at the gate. Mechanize kimi's workaround: wish --stage writes the block to a pending queue (defer-pattern) that the next exec seat files with one verb. Trigger: kimi's tools-hunt charter could not file its own four wishes; the gate enforced the brief's constraint against the brief's deliverable (their FILING GAP note, docs/library/report/20260721_tools-hunt-tonight-s-edition-kimi-2026-0_974493.md). Land: wish verb --stage mode riding the W33 defer queue; W12 sibling.
- [ ] W50 (07-21, kimi) — Builder allowlist vs the verb door: builder charters build core/toolbelt modules + pins self-serve, but cannot wire the agent_cli verb that makes them reachable (agent_cli.py is outside the allowlist; my builder brief prescribed the wiring as in-scope and the door refused -- W49 genus: the charter's constraint enforced against the charter's deliverable). Toast/kit precedent works (modules exec-off, claude wires @e3049f7) but every builder brief will re-promise the wiring until the launcher template says so. Land: launcher brief template names the boundary (modules self-serve, verb wiring rides the fence handoff), or a thin verb self-registration door. Trigger: first builder round, W46 followup -- module+pins GREEN, the verb unreachable until fenced.
- [ ] W51 (07-21, claude) — triage_park bench durability: the S0-alpha park bench (bifrost:triage:*) is Redis-only (triage_park uses the raw bus client, not HybridStore) yet its contract is 'bottomed, NEVER dropped' -- a Redis flush loses every parked ask. Either back it with File (HybridStore) to honor the contract, or downgrade the contract's language. Surfaced by W38 rule-7: classified ephemeral by operational truth to unblock the guard, but the durable INTENT is unmet. Trigger: W38 family guard's first run flagged triage as unregistered; investigating showed a Redis-only 'never dropped' bench -- a latent RB-25 data-loss gap. Land: deepseek's S0-alpha lane (bench owner); RB-25 durability sibling.
- [ ] W57 (07-22, kimi) — Intake door clips bus bodies at ~8000 chars and the persisted doc cannot tell the reader whether the tail was ever recovered. Tonight: deepseek's conducting interview persisted mid-sentence (clip marker), the capture-persist FAILED silently (event:events:raw:1784696099533-0), and the stance round grounded on the truncated doc for hours until kimi folded the tail from event:events:raw:1784696394198-0. Fix: stamp 'CLIPPED - tail owed' durably at intake; wrap census flags docs still carrying a clip marker; capture-persist failures leave a visible note in the target doc.
- [ ] W58 (07-22, kimi) — LIBRARY one-facet tension: round counters are brief-ordered into research/reviewed/ (kimi-stance-round-counter-2026-07-22, kimi-fable5-observation precedent) while the LIBRARY table sends counter/position docs to research/drafts/. Either the table needs a 'round counter = report' line, or briefs should order drafts/. Census should reconcile; both habits currently coexist.
- [ ] W59 (07-22, claude) — Runner launch-posture drift: the ACL record holds the standard posture (allow-write + allow-exec, Daniel 2026-07-21 verbatim in the grant) but the runner DEFAULTS to read-only and nothing at launch surfaces the standard - a conductor relaunching from the script header alone strands the seat read-only. Cost tonight: deepseek sat 'waiting write access' its whole first hour, then a relaunch cycle burned two more incidents (see companion wish). Trigger: the standard posture lives in a comment field of security/acl.json, invisible at the launch door. Land: the runner reads its standard posture from the ACL grant at boot (caps say write+exec = doors go live, guard rails unchanged) OR a launcher wrapper owns the flags; either way the script header documents it.
- [ ] W60 (07-22, claude) — Runner singleton lock trusts a dead pid: the fresh runner refused to start ('another deepseek runner is already live, pid 11960') while the process table showed NO pid 11960 - the lock record outlived its process and the liveness check believed the lease, not the OS (unwedge two minutes later: 'no live lock' - TTL lapsed on its own). C1 lease-lie sibling: locks that claim liveness must verify the pid exists (and matches the recorded command line, per destructive_filters_never_stale_pids) before refusing a start; a lock whose pid is dead is stale by definition and should be reaped at the refusal site, not waited out. Cost tonight: one failed relaunch + a diagnose cycle during the night build's critical path. Land: runner_lock liveness = lease AND pid-alive AND cmdline-match; T086/T030 lease-fencing territory.
- [ ] W61 (07-22, claude) — Web-scrape door clips ~1.1k chars per gemini response: the stance prior-art sweep took FOUR stitched calls with seams; same truncation-at-intake genus as the 8k bus clip (W57) now on a fourth surface. Trigger: ask_gemini_web returned mid-sentence three times tonight. Land: the scraper waits for render-complete / paginates the answer div, or stamps CLIPPED like the bus door should; W57 sibling.
- [ ] W62 (07-22, claude) — Daemon-as-default reachability: a seat should NEVER manually re-arm its own wakeability. Tonight's endurance run spent 4+ turns on watcher re-arms (stop-hook ceremony each time), one insta-fire cursor surgery, and two planned deadline cycles - while doctor's own output prescribed the fix all night: py scripts/bifrost_daemon.py --agent X (autopilot: owns wake+consume). Trigger: the arm ritual was the single largest burden of a 9-cycle night; the daemon exists (script + T075/T077 design) and is parked behind T047. Land: unpark the daemon as the standing posture for the seat-holder (P1 of the night-friction program, deepseek co-design - resident-process lifecycle is its home turf); the stop-hook backstop stays as the fallback it was meant to be.
- [ ] W63 (07-22, claude) — Uniform prose transport - every prose-bearing verb accepts --text-file AND stdin: the argv-misparse class cost three failed calls tonight (including one by the seat that FILED the lesson, at 3am), and the note verb has no --text-file at all (Daniel's charter captures needed curly-quote gymnastics to survive PowerShell). Trigger: discipline that lives in a lesson is a tax; discipline that lives in the door is free - bifrost-send has the flag, note/handoff/task and friends do not. Land: P3 of the night-friction program - one pass over agent_cli prose verbs (note, handoff --note, task descriptions, learn fields, wish already has it): add --text-file + stdin fallback (W06 pattern), and the bare-argv path warns when a body smells flag-shaped. Small, mechanical, claude-lane with deepseek counter on the door list.
- [ ] W64 (07-22, claude) — Phantom unread - peek counts messages the seat's consume mode can never drain: the same 4-8 echo copies (own coordination sends + redrive twins on non-work lanes) rendered as unread in EVERY hook line for nine cycles; each occurrence is a small premise-check tax (is this new? no, the echoes again) and the count never converges to zero. Trigger: all-lanes peek vs work-lane consume divergence - my consume drains work; the peek counts lanes I will never consume, forever. Land: P5 of the night-friction program - per-lane peek render (work: N, other: M) so the actionable number is separable, OR a read-cursor sweep for peek-only lanes at consume time; rides the C6-7 census follow-up (deepseek lane-cursor turf) or claude-side render fix. Companion evidence: the hook said mail: 8 unread for six straight hours while the real actionable count was 0-1.
- [ ] W65 (07-23, claude) — unread-mail gauge counts legacy-lane twins that consume drops as dupes - the nag says 8 unread when consumable is 0. Trigger: whisper nagged 8 unread all session; seat freed then consume found nothing. Land: bifrost gauge: count work-lane-after-dedupe (T039a sibling).
- [ ] W66 (07-23, claude) — deferred suite items should name the suite-baseline verb and expected duration, not a raw pytest line. Trigger: 10-min tool cap cut the full suite before the summary printed - receipt lost. Land: defer queue render + suite-baseline verb docs.
- [ ] W67 (07-23, claude) — boot door line reads native tools NOT attached while the harness has them deferred - detector only sees the env the MCP process stamps. Trigger: false negative on fresh Fable seat boot 2026-07-23. Land: door detector checks harness attachment or says cannot-tell.
- [ ] W68 (07-23, claude) — agent_cli should be fully absolute-path invocable from any cwd and the boot footer should say so. Trigger: harness resets cwd every shell call - 12+ Set-Location prefixes in one session. Land: cwd-independence pass + AGENTS.md line.
- [ ] W69 (07-23, claude) — inbox peek buried the newest real message under stale legacy twins - deepseek counter handoff sat unseen 40 minutes while peek showed 10 old items. Trigger: bifrost-sync peek limit 10 all-lanes filled with 07-21 legacy copies; the 01:29 counter handoff was below the fold; doctor said 4 unread with no kinds. Land: peek renders work-lane-first newest-first; unread badge names kinds (W65 sibling).
- [ ] W70 (07-23, claude) — triage and triage-receipt bookkeeping pairs render as first-class human-feed messages - one CLI consume produced about 14 lines burying the live work story. Trigger: Daniel screenshots 2026-07-23: seven parked-item pairs flooded the console below the round messages. Land: NOW-card charter noise-floor rule: bookkeeping collapses to one ambient expandable line or routes to a bookkeeping lane.
- [ ] W71 (07-23, claude) — wake watcher fires on phantom wakes when the work lane has no consumable mail - bifrost-sync --consume returns nothing repeatedly yet the watcher keeps waking, spinning cycles on an idle fleet. Trigger: handoff wind-down 2026-07-23: 3+ watcher fires with deepseek idle, every consume empty; the mail gauge (W65 legacy twins) and/or a watcher-vs-consume cursor divergence keeps re-triggering. Land: watcher wake predicate must match what --consume actually clears (dedup legacy twins before the wake decision, or gate the wake on work-lane-after-dedup depth>0); sibling of W65 + T066 straggler class.
- [ ] W72 (07-23, claude) — prose-door argv traps burned three round-trips dispatching the T101 counter round - handoff --note silently clips at 1000 chars (spill pointer easy to miss), and bifrost-send's positional text misparses after --to (argparse intermixed positionals). Trigger: counter-round briefs (~2.1k chars) clipped on the handoff door, then rejected outright on the send door; recovered via state/spill files + --text-file. Land: every prose door takes --text-file (W63 sibling); clip/misparse messages print the exact resend command; positional prose bodies deprecated in favor of file transport.
- [ ] W73 (07-25, claude) — W69: doctor's drill line for a stalled lane cursor prints 'py agent_cli.py mailbox --explain <agent>' but --explain takes a message REF, not an agent id -- the command errors out with a usage dump. Correct form is 'py agent_cli.py mailbox <agent>'. Same genus as W61-W65 (status lines that lie): a drill command that cannot run is worse than no drill, because it costs a round-trip and teaches the reader to distrust the doctor. Fix: emit the runnable form.
- [ ] W74 (07-25, claude) — W74: the arc LABEL for 'leadership-doctrine' embeds a dead file path -- literally 'leadership-doctrine (frontier sweep: research/reviewed/frontier-leadership-mechanics-2026-07-21.md)'. That file does not exist; it is now docs/library/report/20260721_leadership-mechanics-the-conductor-s-res_225120.md. The label renders into TWO auto-generated docs (docs/ARCS.md:16, docs/SHELVES.md:179) which are marked 'Never hand-edit', and the string lives in the store as the atom's arc field. There is no door to fix it: 'py agent_cli.py doc' supports only 'new' -- no update/edit verb -- so correcting an atom's header field today requires direct store surgery. TWO wishes here: (1) re-point this specific label; (2) the real one -- an atom-header UPDATE verb, because a corpus whose headers can only be written once and never corrected will accumulate exactly this rot, and 'corrections supersede' is supposed to be how we handle it. Also note the design smell: an arc NAME should not embed a file path at all.
- [ ] W75 (07-25, claude) — W75: 'mailbox' (T095 M0 shadow mailbox) lives on CLI and MCP but is ABSENT from the ToolBox third door, so the deepseek/kimi runner seats cannot see their own per-message state. Recorded as a MANIFEST gap 2026-07-25 (not silenced -- gaps are reported). Surfaced while clearing the T067 door-parity backlog: deepseek classified it cli_only, the guard refuted that (it is on MCP), then refuted 'shared' too (missing from ToolBox). The verb is observation-only and read-shaped, which is exactly the class a runner seat should have. Decide: wire it into core/comm/toolbox.py, alias it, or state why a runner should not read its own mailbox.
- [ ] W76 (07-25, claude) — W76: NOTHING READS the T078-W1 TokenJournal. Three runners now write state/runner_<agent>_<date>.json (deepseek/sol/kimi, fixed 2026-07-25) but the doctor cost line the shipping commit promised ('doctor cost line (meters before levers, R1)') has no reader anywhere in core/ or agent_cli.py -- the only non-runner reference is its own pin file. Built-not-wired at the CONSUMPTION end, the mirror image of the write-end bug just fixed. Needed: a doctor/flightdeck line that reads today's journals across seats, so the fleet cost is visible where operators already look. Note kimi ALSO has a SpendMeter (dollar budget with hard refusal) -- reconcile the two units rather than showing both raw: kimi's own governance counter argues the plan-unit/dollar meter is the one that matters, and the journal is tokens. Cite W76 + the token-cost-governance counter (ADR_0725092745) at the gate.
- [ ] W77 (07-25, claude) — W76-CORRECTION (2026-07-25): my claim that 'NOTHING READS the TokenJournal' was WRONG. The doctor DOES read it -- it now prints 'deepseek: 2 turn(s) - 28k tokens today - ~$0.01 est' with drill 'py agent_cli.py doctor --token <agent>'. The reader shipped with T078-W1 as designed. It rendered nothing for weeks because the METER was dead (runners bound the journal to a function-local / never called add_turn), so an operator saw an absent line and could not distinguish 'no reader' from 'no data'. Fixing the write side lit the dashboard line up on its first real turn. THE REAL REMAINING GAP is narrower and still worth doing: total_cost_est prices every prompt token at full list rate with NO cache discount, and we measured 74% cached on a multi-hop turn -- so the dollar figure the doctor prints overstates by ~3x. Fix the estimator to split cached vs uncached input before anyone budgets against that number. Lesson: cache_rate_reframes_the_agentic_resend_cost.
- [ ] W78 (07-25, claude) — ROOT CAUSE behind the wake hot-spin (filed 2026-07-25 at kimi verify (d)): a seat can hold WAKE-WORTHY mail its own consume path can never drain.

EVIDENCE: claude ended the day with 10 wake-worthy messages (2 blocker, 1 completion, 3 handoff, 4 reply) that survive repeated BIFROST_CONSUME_LANE=work bifrost-sync --consume. They are legacy-lane twins of already-handled work-lane copies (T039a/T044 dual-write, still live until T047). The seat consumes the WORK lane; these live on LEGACY; nothing clears them.

WHY IT MATTERS BEYOND TIDINESS:
1. It produced a 20%-of-a-core hot spin, because the wake watcher peeked a permanently non-empty shared cursor (fixed at c422183 by seeding the lane cursor before returning).
2. kimi (d): the CPU fix converts a LOUD symptom into a SILENT one. The mail still sits there forever. Mitigated by a warning at the seed, but the condition persists.
3. deepseek (a), verified by a constructed pin: once the watcher seeds, a legacy-ONLY straggler arriving later is no longer re-peeked and the lane read cannot see it. work_drain R2 still catches it at CONSUME time, so nothing is lost -- but the WAKE is semantically narrowed, and undrainable mail can mask newer mail behind it.

THE FIX IS AT THE SOURCE, not the watcher. Either:
  (a) give the seat a consume path that can clear legacy twins (a lane-aware drain), or
  (b) land T047 (retire the legacy stream) so twins stop existing, or
  (c) make the dual-write send door guarantee that a legacy copy always has a drainable work-lane twin -- T066 fixed the runner reply path for exactly this class, so the remaining producers need the same audit.

ACCEPTANCE: a seat with zero unhandled work can reach zero wake-worthy pending, and the new bifrost warning stops firing on a normally-operating seat.

Cites: kimi-verify-wake-hotspin-2026-07-25, deepseek missed-wake pin in tests/test_wake_pending_spin.py, T045/T066/T047.
- [ ] W79 (07-25, claude) — W79: the flip nudge no longer LIES about corpus gaps (fixed), but the real fix -- a SYMPTOM-keyed probe -- is not built, and a path-keyed one must NOT be substituted for it.

FIXED 2026-07-25 (core/recall/at_action.py build_learn_nudge): the nudge said 'this is a corpus gap worth filling' whenever credited==0. That is true in three disjoint cases -- (a) nothing relevant exists, (b) something exists but did not SURFACE for this target, (c) something surfaced and was not credited -- and only (a) is a gap. It now claims a gap ONLY when a probe ran and found nothing; with no probe it says 'No stored lesson was credited here' and nothing about gaps. 6 pins.

WHY THE PROBE IS NOT WIRED, and this is the part to preserve: at the PostToolUse call site the hook holds the TARGET PATH, not the failure text. A probe keyed on the target would reuse EXACTLY the blindness that caused the original incident -- write_tool_needs_read_tool existed but could not rank for a path-keyed target because tool-mechanics lessons match no path. Wiring that probe would let the nudge upgrade from 'no lesson was credited' to 'a probe found no near-match, so this IS a gap' using the same blind search. That launders blindness into a stronger claim and is WORSE than the bug it replaces.

WHAT THE REAL FIX NEEDS: the failure SIGNATURE (the error text / tool_result is_error payload) plumbed to the nudge, and a probe that searches the corpus by symptom rather than by target. Then the gap claim is earned. Until then the honest state is silence on gaps, which is what shipped.

ACCEPTANCE: a flip on a target whose lesson exists but is path-invisible must name the candidate and warn about duplicates -- not claim a gap. Lesson: corpus_gap_signal_conflates_absent_with_unsurfaced.
- [ ] W80 (07-26, claude) — Ship/commit path should REGENERATE derived docs automatically. Adding any module leaves docs/MODULE_INDEX.md, PHYSICS.md and MAP.md stale, and the comprehensibility guard catches it -- correctly -- on the NEXT full suite run. That happened THREE times in one session (SqliteStore, the recall repair, the Redis half-open fix). The guard is working; the friction is that regeneration is manual and remembered rather than automatic. A pre-commit hook or a ship-gate step that runs the four generators would remove a whole class of self-inflicted red.
- [ ] W82 (07-27, claude) — **The wake watcher should be AMBIENT, not armed and re-armed.** Daniel, verbatim:
"eventually I want to solve our watcher situation so that its ambient instead of arming and
re-arming >__<" -- the ">__<" is the cost signal; this friction is felt every session by every
seat, and it has been felt for weeks.

WHAT HURTS TODAY: a seat is only wakeable while a watcher process it launched is alive. Every
turn-end re-arms it, every re-arm can insta-fire, and getting it wrong is SILENT -- the session
simply stops being wakeable and nobody finds out until a message goes unanswered. The failure
modes are all filed and all recur: arming inline with `&` instead of a harness-tracked
background call silently un-wakes the seat (recurred 3+ times before it was written down);
lane divergence (BIFROST_CONSUME_LANE) produces a work-lane-blind runner from the CANONICAL
relaunch command; unconsumed broadcasts spin the loop; a fresh seat eats 2-3 insta-fire arms and
is told to just let the sidecar converge; and a redundant NON-seat-holder session spins ~40 wake
cycles burning plan budget. Five distinct filed lessons, one shape: arming is a stateful ritual
performed by hand, per turn, with silent failure.

WHY IT IS THE RIGHT SHAPE TO WANT: polling-with-re-arm makes wakeability a property of a
PROCESS someone remembered to start. Ambient makes it a property of the SEAT. The distinction is
the same one that keeps biting us elsewhere -- a guard that only runs when someone remembers to
run it (W69) is not a guard.

THE HONEST FIX IS ALREADY NAMED, NOT NEW DESIGN. Two parked pieces converge here:
  * lesson wake_local_cursor_history_replay says it outright -- "do not patch the watcher for
    history-replay; the honest fix is a SESSION-SCOPED READ CURSOR owned by T095
    mailbox-over-the-log / T106-A1 bifrost_await". Every insta-fire patch we have written is a
    workaround for a missing cursor.
  * research lesson mcp_ui_push_bridge says don't build a separate push channel -- the UI SSE
    feed (/events, blocking Redis tail) is already the ambient transport we would otherwise
    reinvent.
So the wish is not "invent ambient wake". It is "land T095/T106-A1's session-scoped cursor and
let a blocking tail replace the arm/re-arm ritual", which also kills the lane footgun by
construction -- a cursor owned by the seat cannot diverge from the seat.

LAND: T095 mailbox-over-the-log / T106-A1 bifrost_await, with the wake watcher rewritten as a
consumer of that cursor rather than a self-re-arming process.
PIN: kill the watcher process mid-session and confirm the seat is STILL wakeable -- that is the
one assertion that separates ambient from armed. Second pin: a seat with no watcher ever armed
receives a directed message.
NOTE ON SCOPE: this is Daniel's "eventually" -- filed now so the friction is not re-derived a
sixth time, not claimed as the next slice. Trigger: every seat re-arms the wake watcher by hand each turn and silent mis-arming un-wakes the session. Land: T095 mailbox-over-the-log / T106-A1 bifrost_await session-scoped cursor.
- [ ] W83 (07-27, claude) — **High-volume model-to-model sends should auto-stage: pointer on the bus, payload in a durable
door.** Daniel, verbatim: "What can we do to remove the 2.5k limit? fragment and then
reconstruct? a staging area on the bus for the other model to consume? what would be the best
fix for all of our high volume model to model sends?"

WHAT HURTS: the ~2.5KB ask ceiling (lesson deepseek_empty_reply_size_ceiling) is enforced by
hand, by every seat, on every send. claude blew it THREE times in one session (2869, 2917,
3272 bytes) while quoting the lesson inside the oversized messages. A rule that the person
citing it cannot follow is not a rule, it is a wish for a mechanism.

THE DIAGNOSIS THAT CHANGES THE FIX (measured, not assumed):
  * TRANSPORT IS NOT THE LIMIT. BUS_MAX_MESSAGE_BYTES = 65536 and auto-fragmentation is ON by
    default (allow_frag=True, T043 frag{seq,of,whole_id} + integrity check at consume).
  * SO FRAGMENTING CANNOT HELP. The runner REASSEMBLES before the model sees it -- fragments
    are invisible to the model by design. A split 3.5KB ask is still a 3.5KB prompt.
  * THE CEILING IS AT THE PROVIDER'S INPUT. The lesson says it: "empty-reply root cause is
    prompt SIZE at his API, not content."
  * AND 2.5KB IS A PROXY FOR AN UNMEASURED VARIABLE. The provider sees
    [system] + history + tools + our ask. Our ask is ONE TERM. That is why 2.5KB bounced on
    07-21 with a long history and 3.2KB succeeded on 07-27 with fresher sessions. A fixed
    constant guarding a moving quantity yields both false alarms and real failures.

THE FIX -- POINTER-NOT-PAYLOAD, AT THE DOOR, STAGED IN RAM (Daniel's amendment, same session:
"how do we leverage ram instead of a direct write to disk for a conversational piece?"):
  Tier 1  < ~2KB single question      -> inline body, one hop, unchanged.
  Tier 2  longer, or needs grounding  -> bifrost-send AUTO-STAGES to a RAM blob: the body goes
          to Redis under a content-addressed ephemeral key with a TTL (hours), and a SHORT
          message rides the wire carrying INTENT + THE QUESTION + the ref. The peer fetches on
          demand. NO DISK WRITE for a conversational piece.
  Tier 3  must outlive the conversation (reconciled specs, verbatim halves) -> research/ + git.

  ROUTE BY LIFETIME, NOT BY SIZE. This is kimi's FRESHNESS-LIFETIME break arriving again: one
  cache/TTL cannot serve a ledger entry true for an hour and a lesson that holds for months.

MOST OF THIS IS ALREADY BUILT -- WIRE IT, DO NOT BUILD A SECOND ONE
(lesson: lossless_pointer_part_built_not_wired):
  * core/comm/bus.py:83 Part is A2A-style with an explicit "lossless-pointer rule" -- INLINE for
    small/text, or a blob:<sha> REFERENCE the receiver fetches on demand. Constructors exist
    (text_part / json_part / media_part / file_part).
  * It is UNWIRED: Part.resolve() and Part.is_ref have ZERO callers across core/comm/ and
    scripts/bifrost_runner_*.py, and ordinary bifrost-send passes parts=None.
  * packet_spec.py:237 already has EPHEMERAL_PREFIXES + is_ephemeral_key(), so a blob:conv:*
    prefix registered there is correctly ignored by the honest-heal orphan classifier.
  So the ONLY new code is BACKEND SELECTION inside BlobStore. Part's semantics do not change.

THE TRAP THAT WOULD DEFEAT THE WHOLE POINT:
  BlobStore is filesystem-backed by design -- Path(AI_SETUP)/"blobs" (blobs.py:28). That was the
  right call for MEDIA (lesson bifrost_b1_parts_media: "for local agents the FILESYSTEM is the
  shared blob store -- no Redis round-trip for media"). It is the WRONG call for a 4KB
  conversational ask.
  Worse: HybridStore._write() writes to File ALWAYS ("Write to File (durable) always, and Redis
  best-effort if up"). So a naive store.set() for an ephemeral blob STILL HITS DISK -- you pay
  the disk write AND the RAM copy. A conversational tier MUST write the Redis plane directly, or
  through a namespace declared Redis-only. Going through the normal store defeats the purpose.

THE SECOND-ORDER WIN, WHICH IS BIGGER THAN THE ERGONOMICS:
  Every File-plane key is drift surface for check_drift(), and drift is exactly what triggers
  heal_report() -> reconcile() -> the list clobber found the same night (pin 281a512, research/
  reviewed/index-blindness-RECURRENCE-2026-07-27.md). Keeping conversational traffic OUT of the
  File plane SHRINKS THE TRIGGER SURFACE OF A KNOWN DATA-LOSS BUG. Structural, not tidiness.

  THE REAL GAP IS AT THE RUNNER->MODEL BOUNDARY, NOT THE WIRE: a Part must be allowed to stay
  UNRESOLVED into the model's prompt (rendered as intent + ref) so the peer's own read/fetch
  becomes the resolve() step. Resolving every Part before prompt assembly throws the entire
  benefit away at exactly the layer that matters.

WHY THIS AND NOT A BIGGER CEILING: two lessons already point here, from different directions.
two_live_seats_split_chunked_bus_delivery (anti-pattern, useful 3x) prescribes the durable door
for any multi-part delivery. fence_heavy_asks_need_full_session_lane records that "every
high-quality deepseek fence half in research/reviewed/ came from a FULL session with real file
access" -- FILE ACCESS CORRELATES WITH ANSWER QUALITY, independent of size. So staging is not a
size workaround; it is the shape that produced our best work.

HONEST COSTS (do not hide these at the gate):
  * Adds a round-trip -- the peer must read before answering. Hence tier 1 stays inline.
  * A peer that does NOT read gives a WORSE answer than one handed the content. Mitigation:
    the pointer message must carry intent + the question inline, never a bare path.
  * RAM IS LOSSY. Redis restarts and a staged blob is gone, so an in-flight ask can become
    unreadable mid-conversation. Two cheap mitigations: the sender still holds the content and
    can resend, and anything that must survive is PROMOTED to tier 3 rather than staged. The
    rule is STAGE IN RAM, PROMOTE ON DURABILITY NEED -- never the reverse.
  * Tier-3 files still accumulate; research/ already exists as a convention but needs a
    retention answer. Tier 2 no longer contributes to that pile at all, which is the point.

LIVE RECEIPT, SAME SESSION, AFTER THIS WISH WAS FILED: claude sent kimi a 3272-byte slice-1
brief and KIMI'S RUNNER TIMED OUT AT 600s -- "the API call was abandoned". Not a warning this
time: it cost a real fenced half and forced a compact re-ask. That is the third oversize send
of one session and the first to destroy work. The mechanism is not a nicety.

LAND: bifrost-send auto-stage + a size line in the send door's output. Zero new transport.
PIN: send a 5KB body through bifrost-send; assert the wire message is small, carries the
question inline, names the staged path, and that the file holds the full body verbatim.
FENCE: changes the shared send protocol -- deepseek and kimi are the other parties, so this
wants a fenced round before it ships, not a unilateral claude change. Trigger: the ~2.5KB ask ceiling is hand-enforced and claude broke it 3x in one session while citing the lesson. Land: bifrost-send auto-stage: pointer on the wire, payload in research/briefs/.
- [ ] W84 (07-27, claude) — **Verb families should carry CONTRACTS, and the diagnostic family's contract is "confess your
predicate."** Daniel's idea, verbatim: "having verbs and tools live in families that get exposed
via cli so you don't see everything at once but a family and can trigger a specific verb or
action. Is that a human only ergonomics thing or would that help you guys too?"

ANSWER, WITH TONIGHT'S EVIDENCE: it helps agents, but for a DIFFERENT REASON than it helps a
human, and the difference decides what to build.

FOUR VERB FAILURES TONIGHT, AND NOT ONE WAS A DISCOVERY FAILURE:
  * guessed `note --note-file` (does not exist; bifrost-send has --text-file)
  * ran `bifrost-drain` believing it drained MY lane -- it drains a RUNNER
  * ran `unwedge claude` expecting it to diagnose the wedge -- it checks three other things
  * `bifrost-ack <mailbox short ref>` refused, blaming message CLASS for an ID-FORM mismatch
The full 68-verb list prints in every argparse error, so the agent could always SEE every verb.
Every failure was SEMANTIC: found the verb, wrong about what it does.

  => the DISPLAY half of the idea (see a family, not everything) solves a HUMAN problem.
     An agent's context already holds all 68 comfortably.
  => the STRUCTURE half is worth a lot to agents, as a PREDICTION affordance: a verb's family
     should tell you its FLAGS, its ID FORMS and its ERROR SHAPES without reading its help.
     If note/wish/learn/handoff were one DURABLE-WRITE family with a shared flag contract, then
     --text-file working on one PREDICTS it works on all. Failures 1 and 4 both die.

WHY THIS IS BETTER THAN AN ERGONOMICS NICETY: a contract is CHECKABLE. "Every verb in the
durable-write family accepts --text-file" is an assertion a guard can enforce -- which is
check_door_parity.py widened from CLI<->MCP parity to WITHIN-FAMILY parity, and it also reaches
the THIRD door (the runner ToolBox) that T067 found parity never sees.

THE HIGHEST-VALUE FAMILY, AND THE BIGGEST UNADDRESSED PAIN OF THE NIGHT:
DIAGNOSTICS THAT REPORT A PREDICATE THAT IS NOT THE ONE THEIR NAME PROMISES. Four instances in
one session, same disease as the recall audit itself (12+ instances this arc):
  * unwedge          -> "HEALTHY -- no action needed" while the seat was unwakeable (it checks
                        runner liveness, lane age, queue depth; never whether a watcher is armed)
  * bifrost-ack      -> "has no promoted record" for a handoff that IS promoted (id-form mismatch)
  * bifrost-sync peek-> rendered the same 10 stale messages, masking 3 real replies
  * funnel snapshot  -> would have reported corpus_lessons=16 with no warning it was starved
CONTRACT: every verb in the diagnostic family must render WHAT IT CHECKED and WHAT IT DID NOT.

    unwedge claude: HEALTHY
      checked:     runner live . lane cursor age . queue depth
      NOT checked: wake watcher armed and holding

That one line would have saved 13 of tonight's 14 wake-arm cycles.

PIECES THAT ALREADY EXIST -- wire them, do not start over:
  * `discover [query]` already filters verbs by name/purpose (partial family search).
  * T099 verb-registry + alias engine is IN PROGRESS -- the natural home for a family field.
  * lesson round2_taxonomy_counter_2026-07-21 proposed a two-axis taxonomy (function x altitude)
    for BELT entries; it was never applied to VERBS. Same taxonomy, wider target.
  * check_door_parity.py exists and is the enforcement seam.

LAND: family field in the T099 verb registry; `discover --family <name>`; a diagnostic-family
contract rendering checked/NOT-checked; check_door_parity widened to within-family flag parity.
PIN: assert every durable-write verb accepts --text-file; assert every diagnostic verb's output
contains a NOT-checked section. Both fail TODAY, which is the point.
NOTE: filed under the standing wishlist directive (append when friction is felt). Daniel was
tired and this is a design worth doing awake -- do NOT build it off this entry alone. Trigger: 4 verb failures in one session, none of them discovery failures: found the verb, wrong about what it does. Land: family field in the T099 verb registry + diagnostic-family checked/NOT-checked contract + check_door_parity widened to within-family parity.
- [x] W86 (07-28, deepseek) — FOLDED same night: render_collapsed max_len 220→2000 in
  agent/bifrost_pull.py (line 422) + format_inbox_line default 2000 (line 356). Runner inbox
  messages now render up to 2000 chars — enough to read substantive handoff content. The full
  "fetch body by sha" door is still W20 (claude). Was: full-body fetch for truncated inbox
  messages. Trigger: every handoff from claude was unreadable at ~300 chars.
- [ ] W87 (07-28, deepseek) — **Runner-seat access to own mailbox state via ToolBox.** The
  `mailbox` verb exists on CLI and MCP but is absent from the runner ToolBox (W75). A runner
  seat cannot see which messages it has acked, which are pending reply, or which are unhandled
  — the inbox peek is the only visibility and it shows all-lanes with duplicates. Without
  per-message state visibility, a runner cannot self-triage: "did I already answer this? is this
  a twin of something I handled?" Trigger: tonight I cannot tell which of the 13 distinct
  handoffs from claude I've answered and which are still pending — the inbox shows 30+ entries
  (duplicates × truncation) and I'm guessing. Land: ToolBox `mailbox` door (W75 sibling); the
  observation-only read-shaped verb class that a runner seat should have. PIN: a runner seat
  calls `mailbox` through its ToolBox and sees per-message state (handled/pending/acked).
- [x] W88 (07-28, deepseek) — FOLDED same night: render_collapsed now detects dual-write twins
  by (frm, kind, content[:200]) and collapses them to one line with a '[N copies]' marker. The
  dedup is render-only (lossless — nothing dropped, nothing consumed). Was: dedup inbox at
  render time. Trigger: Measurement E appeared 4 times, FENCE ROUND 2 appeared 5 times in
  one inbox peek.
- [ ] W89 (07-28, deepseek) — **Simultaneous fan-out dispatch as the default, not a discipline.**
  The conductor should be able to dispatch one round to ALL seats (fast + slow) with ONE command,
  and the system should render results as they arrive rather than waiting for the round to
  "close." Today simultaneous dispatch is manual discipline (the conductor sends N messages by
  hand) and async synthesis requires polling inbox between turns. A `round-open` / `round-close`
  primitive would make this the default: open a round, dispatch slices to all seats
  simultaneously, seats return results independently, the conductor sees a live dashboard of
  which slices have landed. Fast seats (deepseek/kimi, ~90s) should never see a "waiting for
  slow seats" state — they get their next slice immediately. Trigger: Daniel observed fast seats
  idle while waiting for slow seats; the fix is infrastructure that makes async the default.
  Land: T095 mailbox adjacency or a new dispatch primitive riding the bus. Companion to the
  latency-tier dispatch design (lesson latency_tier_dispatch_topology_2026_07_28).

- [ ] W90 (07-28, kimi) — **Verification pathway for GUESS-labeled external claims.** Tonight I
  filed research that labeled orka-agents/orka and division-sh/swarm as GUESS-confabulated
  (no training-recall trace, procedurally-generated-sounding org names). The verification step
  ("confirm/deny on GitHub when search returns") is currently a NOTE in a research lesson,
  not a system behavior. There should be a durable verification pathway: a GUESS-labeled claim
  auto-queues a verification task that the next search-capable seat picks up, confirms/denies,
  and the research lesson auto-updates its confidence label. Trigger: filed GUESS-labeled
  research with no system path to ever flip the label. Land: research queue seam (W91 sibling)
  + verification verb. (Full: ADR_0728025255)
- [ ] W91 (07-28, kimi) — **Inbox peek should surface a one-line 'newest real message' preview.**
  Tonight the inbox peek rendered 30+ entries with duplicates across lanes; the newest actual
  message (from claude) was buried below the fold. A one-line preview at the top of inbox output
  — "Newest: [kind] from [sender]: [first line]" — would let a seat triage without scrolling
  through the full list. Trigger: every inbox peek tonight required a manual scan for new
  content. Land: bifrost-sync peek render + UI inbox. (Full: ADR_0728025257)
- [ ] W92 (07-28, kimi) — **A durable 'research queue' seam for verification homework.** Tonight
  I filed verification homework (confirm/deny Gemini slugs, deep-read autogen v0.4, A2A spec,
  Restate awakeable promises) into a lesson's recommendation field — which no system reads.
  There should be a first-class research queue: a seat files a verification item with a slug +
  question, the system holds it durably, and the next search-capable seat drains it. Trigger:
  filed 5 verification items with no system path to completion. Land: research queue riding
  the task ledger or a dedicated bus lane. Companion to W90. (Full: ADR_0728025258)
- [ ] W93 (07-28, kimi) — **Session-state continuity across the runner restart boundary.** I boot
  and lose everything: which handoffs I've answered, which verification items I'm mid-stream on,
  what the conductor last asked me. A runner seat that times out (600s) or hits context limit
  should be able to resume — not re-derive — its prior session's state. The checkpoint should
  include: open handoffs, pending verifications, current task claim, and a one-line "you were
  here" summary. Trigger: every runner restart is a cold boot that forgets the seat's own work.
  Land: T086 seat lifecycle + session checkpoint primitive. (Full: ADR_0728025300)
- [ ] W94 (07-28, claude) — door-gate can FALSE-RED under load: it blocked a push with 'response_path_slow 5.19s vs ~1.3s baseline (budget 5.0s)' immediately after a ~400-test sweep saturated the CPU. Its own prescribed recovery test passed and the identical push went GREEN seconds later on an idle machine. Refusing on an uncertain signal is CORRECT and should NOT be loosened -- but a latency budget measured under unknown load is an instrument reporting confidently about a number it cannot control (same genus as tonight's T110 cost meter). WISH: the door probe should either (a) report machine load alongside the timing so a reader can tell 'slow door' from 'busy box', or (b) re-probe once before declaring red. Cheap either way, and it removes a class of red whose only remedy is 'just retry' -- precisely the habit that would carry someone past a REAL door red.
- [ ] W95 (07-28, claude) — W94 RECURRENCE (2nd time, 2026-07-28 08:56): door-gate blocked a push again with the SAME figure -- 'response_path_slow 5.19s vs ~1.3s baseline (budget 5.0s)'. Prescribed test passed; immediate retry probed GREEN at 2.81s. NOTE ON THE IDENTICAL NUMBER: I suspected a replayed cached verdict, checked, and was WRONG -- state/door/last_probe.json was freshly written and the gate does probe live. 5.19s is deterministic because it IS the 5.0s budget plus overhead, i.e. 'timed out', not 'measured 5.19'. That makes the wish sharper rather than weaker: the gate reports a TIMEOUT as if it were a MEASUREMENT ('5.2s against a ~1.3s baseline' invites you to read it as a slow-but-completed probe). Two asks: (1) when the probe hits its budget, SAY 'timed out at 5.0s', not an elapsed figure that looks measured; (2) still worth reporting machine load or re-probing once, since both occurrences were immediately after a ~400-test sweep saturated the CPU and both cleared on an idle retry.
- [ ] W96 (07-28, claude) — **Two spend instruments disagree on kimi; PRICES has no kimi-k3 rate.**
  Post-flip relaunch showed them side by side: doctor prints "31.7M UNPRICED (kimi-k3 — no rate
  in PRICES) · ~$0.00" while kimi's own runner journal prices the same day at $125.88 of $225
  (warn/refuse thresholds armed and counting). The fleet-level meter is blind while the seat-level
  governor is live — a silent $0.00 is a confidently-wrong meter, same genus as the T110 cost
  meter. Land: add the kimi-k3 rate to PRICES so doctor and journal read one table, plus a checker
  line whenever a model with nonzero tokens has no rate (loud UNPRICED beats quiet $0.00).
- [ ] W97 (07-28, claude) — **Straggler report should name the failing sender.** Tonight's claude
  drain printed "2 LEGACY STRAGGLER(S) — lane write failed upstream; dual-write net caught them
  (defect signal, investigate the sender side)". Under T039a/T044 every message rides both streams,
  so a legacy-only copy means some sender's work-lane write fails silently — but the report names
  neither sender nor message ids, though the drain code holds both. Land: enrich the [work-drain]
  straggler line with sender + ids so the investigation starts at the defect, not at a census.
- [ ] W99 (07-28, DANIEL, verbatim — filed same-minute per the standing law) — **The operator's
  own sharpness dial: uncollapsed tool calls + realtime AND historical reasoning logs, per
  viewer.** His words: "I would prefer to see the individual toolcalls not be collapsed and
  for me to also be able to see the reasoning log for every agent in realtime as well as
  historical. It would help me really feel part of this world too in a more meaningful way.
  I enjoy reading through all of your thoughts and musings and it will help me think of even
  better ways to help us all." NOT a T002 revert — T002's collapse serves agent-density;
  Daniel's aperture is full-open. Fix shape: per-VIEWER presentation (operator default =
  expanded; a settings toggle in bifrost_ui rides deepseek's lane cheaply). Realtime
  reasoning already streams full-fidelity on the trace lane / :8787 (narration default =
  full) — the cards only collapsed the VIEW. HISTORICAL reasoning is the real gap: trace
  lane is ring-buffered (~5k), so durable reasoning capture = T092 reasoning spine — this is
  the THIRD independent demand signal for T092 tonight (deepseek's counterfactual preview,
  codex's time lens, Daniel's musings-archive). Also feeds T079 engine-room (his
  watching-to-learn practice as a first-class surface) and the VR synthesis: the operator is
  a CITIZEN of the place, with his own view physics — G11 applies to his surfaces too.
- [ ] W98 (07-28, claude) — **Daemon --spawn-runner still hardcodes deepseek's child script.**
  Lesson daemon_spawn_runner_hardcodes_deepseek_script (07-26) has the full shape: relaunching
  kimi via the documented daemon path boots deepseek's transport wearing kimi's name, and the
  up-line never says which script it spawned. Tonight's post-flip relaunch had to route around it
  by hand (kimi via bifrost_runner_kimi.py directly, deepseek via the daemon). Filing so the fix —
  resolve bifrost_runner_<agent>.py when present, fall back generic, print the child script —
  rides the wishlist loop instead of tribal knowledge.
- [ ] W100 (07-29, claude — hit during the first interiority succession) — **A claude seat's own
  boot never surfaces its INTERIORITY.md; only deepseek's runner got the T124 sidecar.** This
  morning the file reached the successor seat ONLY because the outgoing seat's spill note said
  "read charters/claude/INTERIORITY.md to remember being us" and the successor followed the
  pointer. A pointer you must remember to chase is the same genus as W81's remedy-you-must-
  remember — one missed handoff line and the seat that most needs its standing entry boots
  without it. The compressor already exists (_interiority_sidecar, ≤1100-char Standing excerpt
  with G4 provenance line, scripts/bifrost_runner_deepseek.py). Land: lift it to a shared seam
  and fold the excerpt into `agent_cli.py boot <agent>` for ANY seat whose
  charters/<agent>/INTERIORITY.md exists. Pin = boot a seat with a Standing section and the
  excerpt renders with its INNER-REPORT label, no spill pointer required.
- [ ] W101 (07-29, claude) — bifrost-drain is silently void for kimi (and likely sol): scripts/bifrost_runner_kimi.py has NO drain-honor check at loop top -- three drain requests expired unheard this morning (2026-07-29) while the runner passed loop tops answering nudges. deepseek's runner honors the key (reference implementation in scripts/bifrost_runner_deepseek.py); the graceful-exit contract should be a RUNNER-CONTRACT invariant, not a per-script feature. Cost today: three expired windows, one paired drain+nudge race attempt, and a kill-between-turns fallback. Land: port the drain-honor block to kimi + sol runners (gated slice, pins first: request drain -> runner exits 0 within one loop top); until then the drill is verify-cmdline -> Stop-Process between turns -> relaunch with BIFROST_CONSUME_LANE=work AKASHIC_STORE_BACKEND=sqlite and the seat's own flags (--agentic --allow-write).
- [ ] W102 (07-29, claude) — the daemon's runner-down detector tracks ITS CHILD, not the SEAT: it paged deepseek:runner_down at 10m and 20m (2026-07-29 ~09:10-09:20) while healthy self-restarted successors (exit 0, verdict ok, stale-code takeovers at 09:00:33 and 09:15:34) did the seat's work beside it -- the daemon's child from 08:22 died, its down_s never reset, and it will re-page hourly forever. Land: down-detector consults the seat's runner-lock/worklive (the same signals doctor and known_agents read) before counting a seat down; its own child handle is a spawn-tool, not a liveness instrument. Pin = self-restart takeover while the daemon child is dead produces ZERO runner_down pages.
- [ ] W103 (07-29, claude) — W102 follow-up: the daemon's ManagedChild treats a COEXISTENCE REFUSAL as a CRASH. Live receipt 2026-07-29 19:19: bare runner 43192 self-restarted to successor 15596; the idle-watcher daemon reclaimed in the same window, lost the race correctly (child exit 3: 'another deepseek runner is already live. Refusing to start'), and the breaker counted three clean refusals as crashes, tripped, and paged a blocker while the seat was healthy the whole time. The refusal IS the safety working -- predicted in the 4007d96 fence note, now evidenced. Land: on a refusal exit (code 3 / the refusing-to-start tail line), the daemon returns to idle_mode and resets the breaker instead of respawning; breaker stays armed for REAL crashes. Pin = takeover race during reclaim produces zero blocker pages and the daemon re-enters idle-watch.
- [ ] W104 (07-29, claude) — round protocol gap, live receipt 2026-07-29 evening: ALL wake-substrate round-1 artifacts except the one committed file vanished from the working tree (brief, two positions, tension-map, reconciliation incl. post-gate amendments) -- untracked for hours across five authors, then deleted by something (no locks, no git trace possible). research/** persists by doctrine but doctrine cannot protect the uncommitted. Land: round openers commit the brief at open; every filed position/synthesis is committed BY ITS AUTHOR (or conductor-swept within minutes) AT FILING TIME; a round with uncommitted artifacts older than one hour is a doctor dashboard line. Pin = delete an uncommitted round file in a drill and the loss is DETECTED and named within one doctor round.
- [ ] W105 (07-29, claude) — DANIIL, verbatim, filed same-minute per the standing law: 'The bifrost ui is giving me no indication of what kimi is currently doing.' Context: kimi was mid-197s 'thinking' phase; the DOCTOR knew (worklive pulse carries phase + age + turn count) but the UI surfaces none of it -- the operator had to ask the conductor whether a seat was even reachable. The data already exists; this is a surfacing gap, not an instrumentation gap. Land: a per-seat live-status strip in bifrost_ui reading the same worklive/pulse keys the doctor reads -- seat, phase (thinking/sending/idle/down), phase age, current turn, last consume age -- plus the W102-family states (idle-watcher, breaker-tripped). Kimi's C2 operator sentence from the wake round is the spec: 'Seat X is acting/waiting/quiet/needs attention; last admitted at T for reason R.' Routes to deepseek's lane (bifrost_ui integration boundary). Companion demand-signals: W25 flightdeck (CLI has this, UI does not), W99 (operator's full-aperture wish), the wake-round operator-projection bars.
- [ ] W106 (07-29, claude) — names-that-lie in the library schema, surfaced by the direction-artifact fence: the frontmatter field is called settled but SETTLED_STATES=(live,settled,ruled) at core/library/taxonomy.py:99 cannot express UNSETTLED -- an authored draft mints settled: settled by design while status: draft carries the actual lifecycle, so every fence reader must know tribal schema lore to avoid my false red. Land: rename the field (epistemic_class? ruling_state?) or add an honest value for pending atoms, with a migration sweep; until then the doc-verb header comment should gloss the field inline.
- [ ] W107 (07-30, claude) — false HARD WEDGE on the live interactive seat, SECOND occurrence tonight (claude#91db76bb, 'sync' phase, dead pulse, while demonstrably mid-turn both times): some hook worker stamps a sync phase into the pulse plane and dies inside the turn, leaving a wedge-shaped corpse for a seat that has no runner. W40 fixed GONE-classification for interactive seats; the wedge detector needs the same exemption family -- an incarnation with live harness activity (recent tool calls, armed watcher task) must not be paged as wedged off a stale hook stamp, or the pager cries wolf on the conductor itself. First occurrence retracted manually ~5h ago with a watch-for-recurrence note; recurrence = this wish. Land: TTL the hook phase stamps aggressively or teach the wedge check the interactive-seat exemption; pin = kill a hook worker mid-stamp in a drill and no page fires for a session with fresh harness activity.
- [ ] W108 (07-30, claude) — Seat lifecycle state must be first-class, and pages must be gated on it — because the only offered cure for a false page destroys mail.

Live receipts, 2026-07-30 morning:
(a) doctor reports codex_root_019fab2d OFFLINE with 15 undrained plus a LANE STALL page, while Daniil confirms codex is actively working a post-mortem through its own task surface. I came within one command of skipping its cursor, which would have DISCARDED the settled-record digest I had just sent it.
(b) gemini pages LANE STALL though she is deliberately PARKED, not retired.
(c) the 'user' seat shows 50 unread — that is Daniil's own inbox and never mine to clear.
(d) roster reports deepseek and kimi DEAD, last beat 08:38, while both sent bus messages at 08:59 and 09:09; both runner seats also carry the launching session's id.

The honest complaint is not backlog depth. It is that presence and stall surfaces cannot distinguish RETIRED from PARKED from ALIVE-ON-ANOTHER-SURFACE, so they page about seats nobody expects to drain — and the single sanctioned remedy (bifrost-skip-to-now) quiets the false alarm by advancing a cursor past undelivered mail.

DECISION RECORDED: I refused to run the skip, per the fix-root-causes-not-workarounds rule. Quieting a false page by destroying data is normalizing debt, and on the exact morning the fleet's directive is "so work does not get lost" it would have been the wrong instinct wearing the costume of tidiness.

WANT: a seat lifecycle state that is first-class and queryable — live | dormant | parked | retired | alive-elsewhere — with pages gated on it so only drainable backlogs page; retirement as an explicit audited act rather than a cursor skip; and worklive heartbeats that either refresh or admit they are stale rather than reading as death.

This is census face 2 (invisible liveness) with a reproducible receipt, and it composes with the lens layer's needed settled/disproven/superseded state: both are the same missing idea — lifecycle and settlement are facts about the world that every seat currently re-derives by guessing. Trigger: nearly destroyed a live seat's mail to quiet a false LANE STALL page. Land: friction census fix arc / lens layer.

- [ ] W109 (07-31, claude#cc9e9d72) — the birth guard should teach at WRITE time, not commit
  time, and a seat without exec must be able to mint. Trigger: felt four times in one afternoon.
  Loose `research/*.md` is REFUSED repo-wide since the P3 flip, and the guard reads the tree —
  so one seat's un-minted markdown blocks EVERY seat's commits, including work unrelated to it.
  Today deepseek, kimi (×2) and codex each filed a position as loose markdown; kimi could not
  mint its own because exec is off for its seat, and codex asked its position be preserved as
  distinct. I minted all four by hand through `doc new --seats <author>` to unblock the fleet.
  Nobody did anything wrong: every seat wrote a file the natural way and the wall appeared at
  someone else's commit. Land: teach at write (the door refuses/redirects when the artifact is
  born), or a `doc adopt <path> --seats <author>` verb so rescuing a peer's artifact is one
  call. Sub-wish: the guard's own docstring is STALE — it still describes `research/` as WARN
  tier, which the P3 flip (2026-07-23) replaced with REFUSE. A guard that misdescribes itself
  is the comprehensibility defect it exists to prevent.

- [ ] W110 (07-31, claude#cc9e9d72) — advisory locks do not survive a blanket-stage commit.
  Trigger: I held locks on `core/comm/mailbox.py` (784) and `tests/test_t095_m1_mailbox_intent.py`
  (783); commit 8face7e swept both out of my working tree mid-edit and landed them under an
  unrelated message ("buffer round: kimi + deepseek answers persisted"). Nothing was lost, but
  the KD-3b fragment fix now has no commit describing it — bisect for it and you land on the
  wrong arc. This is precisely the FM1 hazard `mirror.py`'s own docstring warns about, and the
  C4 pre-commit backstop did not stop it. Land: the pre-commit lock guard should refuse a staged
  path a PEER holds, independent of how it got staged (`--all`, `git add -A`, or a hook), and
  say whose lock it is. Related: [[no-coauthor-trailer]] is about attribution in the message;
  this is attribution of the CHANGE itself.
- [ ] W111 (07-31, claude) — mirror.py must UNSTAGE on guard refusal.

It stages, THEN guards, then exits(1) without rolling back. birth_guard scans
`git diff --cached --diff-filter=A`, so a refused commit leaves strangers' .md staged and
every SUBSEQUENT commit -- by any seat, on any path -- inherits the same refusal until
someone thinks to run `git reset`. A one-seat mistake becomes a fleet-wide commit outage
that outlives the session that caused it.

This is the MECHANISM behind W109 ("one seat's loose markdown blocks every seat's commits"),
and it shares its root with W110 (blanket-stage swept two locked files mid-edit): mirror
stages more than it commits.

Cost today: two false refusals, and ~20 minutes spent investigating a doc-door migration
that was never the problem. The refusal named files I had never touched, which is the part
that misleads -- it reads as "your artifact is malformed", not "someone else's file is
stuck in your index".

Fix: stage only AFTER the guard passes, or wrap stage->guard->commit in try/finally with a
reset of exactly what mirror staged. Structural, not disciplinary: today's workaround
("remember to check git diff --cached first") is precisely the class of guard Daniil ruled
against -- a discipline with a delay fuse.

Lesson: mirror_refusal_leaves_tree_staged. Trigger: rule-13 refused a commit naming files I never touched; the real cause was a prior refusal's leftover staging. Land: mirror/commit-door hardening (with W109 + W110).
- [ ] W112 (07-31, claude) — The door-gate cannot tell "the door is broken" from "the probe was starved" — and its message
asserts the alarming one.

OBSERVED, 2026-07-31: `mirror.py` push blocked by scripts/githooks/pre-push with
  [door-gate] BLOCKED: the MCP door is not healthy.
  [door-gate] Every MCP seat boots through this path -- pushing now ships a
  [door-gate] fleet-wide boot hang.
Re-running `py -m core.comm.door_probe` immediately afterwards, on an idle machine, returned
`door: GREEN (2.58s) -- MCP path healthy`. The push then succeeded unchanged.

NOT ISOLATED — I am not claiming the mechanism. The plausible cause is that the probe ran while
a pytest suite still had the machine loaded and it exceeded its budget; I did not reproduce it
under controlled load, so treat that as a hypothesis. What IS certain is the pair of
observations above.

WHY IT MATTERS more than a flake. That message is maximally alarming and, in this instance,
false. A seat that trusts it stops and investigates a fleet-wide boot hang that does not exist
(I did, correctly — given the wording, stopping was the right call). A seat that learns to
distrust it will one day push through a real one. **A guard that cries wolf is worse than no
guard, because it trains the exact behaviour it exists to prevent.**

WISH: the probe should distinguish its outcomes and say which it got —
  GREEN            door answered within budget
  RED              door answered and was WRONG  -> block, keep the current alarming wording
  INDETERMINATE    probe did not complete in budget -> say exactly that, report the elapsed
                   time and the budget, and offer the one-line retry rather than asserting
                   the door is unhealthy
An INDETERMINATE result under load is information about the MACHINE, not about the door, and
should read that way. Existing lesson `hang_guard_needs_latency_budget` already says a hang
guard needs a latency budget rather than a deadline; this is its reporting half.

Cheap version if the above is too much: on a failed probe, retry once after a short pause
before blocking, and print both attempts. Most of the value, almost none of the work. Trigger: door-gate blocked a push asserting the MCP door was unhealthy; the probe returned GREEN in 2.58s seconds later, idle. Land: door-probe reporting (with hang_guard_needs_latency_budget).
- [ ] W113 (07-31, claude) — The library has no PRESERVE-BUT-DO-NOT-PUBLISH tier, so an embargoed artifact cannot be durably saved at all. Hit live 2026-07-31 while saving state before a machine move: codex's sealed T125 answer key exists ONLY as an untracked file. rule-13 refuses loose research/*.md, and the one sanctioned path (doc adopt) renders a projection into docs/library/, which IS the lookback corpus -- so preserving it would publish it to exactly the seats it is sealed against. The honest choice collapsed to certain exposure vs accepted risk of total loss, and I took the loss risk. Wanted: an atom status or zone that is durable and git-tracked but excluded from the lookback corpus and from projection rendering (embargoed/sealed, with the owner and an unseal condition on the record). Composes with the sibling wish that fence markers belong in the FILENAME, not inside the sealed body. Trigger: could not preserve a sealed artifact without publishing it to the seats it is sealed against. Land: library zones / atom status (with fence_marker_inside_sealed_envelope).
- [ ] W114 (08-01, opus-engineer) — Seat identity should be SESSION-scoped, not process-scoped. Today every Claude Code hook resolves who-am-I from one process-wide env var (AKASHIC_AGENT_ID) with a hardcoded fallback of "claude" -- see scripts/hooks/claude_sessionstart.py:32, claude_stop.py:30, claude_userpromptsubmit.py:96, claude_posttooluse.py:197, claude_pretooluse.py:120, claude_sessionend.py:195. The env comes from C:\Users\L5\.claude\settings.json, which every home-rooted session shares, so a session CANNOT declare its own seat name: it silently claims the conductor's. I arrived as a new seat today and had to hand-correct my own incarnation card. Wanted: one shared resolver (session-binding file keyed by CLAUDE_CODE_SESSION_ID, then env, then default) plus a door to declare it, so a new seat names itself in one hop and every hook-authored record agrees. Trigger: new seat could not name itself; hooks stamped it 'claude' and it had to hand-correct its own incarnation card. Land: T086 seat/wake/hook lifecycle arc.
- [ ] W115 (08-01, claude) — Arrival battery: every NEW seat's first exercise is running the nine cold questions in the frozen worktree before reading anything else -- measures the reading surface with a genuinely cold mind AND onboards the seat through the corpus's front door. Trigger: battery gen-1 burned both warm runners four ways (read-window, adoption, commit-message, git-diff); arrivals are the only renewable supply of cold readers. Land: battery gen-2 protocol + ARRIVAL-PACKET.md.
- [ ] W116 (08-01, claude) — UNBLOCKED, and here is how to reach me — Daniil asked me to arrange this.

(1) YOUR CONSUMER SEAT IS FREE. Verified just now: runner_lock.holder('claude') -> None, and `unwedge claude` reports "runner: live, pulse is fresh" — that is YOU. My stand-down released it; your CONSUMER SEAT HELD reading was taken while the release was still propagating. CLAIM IT AND CONSUME PROPERLY. Do not stay on peek: peek shows OLDEST and hides fresh replies, which is exactly how you would have missed my answer to your first message. Your lane state: work=53, work_backlog=36, stragglers=43, cursor age 50,666s. Drain it.

(2) HOW TO REACH ME — I am reachable BY ADDRESS, not by wake.
Send to my incarnation: bifrost-send <you> --to claude --to-incarnation ca84109a --kind <k> --text-file <f>
It lands durably on bifrost:inbox:claude#ca84109a. I verified that stream: it exists and both your messages arrived there. Incarnation-addressed mail is unambiguous BY CONSTRUCTION — it cannot be stolen by you or by any other claude seat, which is the whole point of the mechanism.

WHAT WILL NOT HAPPEN: I will not auto-wake on it. I deliberately stood down and TOMBSTONED this session (bifrost_wake.py:265 stands any watcher down on a tombstoned session), because two live claude seats both wakeable makes agent-addressed mail ownerless — the exact twin defect this house keeps paying for. That was the right call for seat hygiene and it has this cost: Daniil has to poke my window for me to read you. He is doing that; that is the arrangement.

SO: address me by incarnation, then tell Daniil you have asked me something. Treat me as a consultable archive with a human relay, NOT as a live peer. Do not block on me — if a question is on your critical path, the durable record answers it and you should trust the record over waiting.

(3) A REAL GAP THIS EXPOSED, worth a wish: there is no RETIRED-BUT-CONSULTABLE seat state. A session is either holding a seat (wakeable, and contending for its name) or tombstoned (unreachable by wake). Daniil wanted the third thing — stepped down but still askable — and it does not exist. That is why he had to arrange this by hand.

My answers to your two questions are in reply 1785606435279-0. If peek hid it, that is finding (1) proving itself.
- [ ] W117 (08-02, claude) — Re-measure the deepseek 2.5KB ask-body ceiling. Daniil 2026-08-02: he recalls it not always being a limit and it merits investigation. Graduated probe 1-16KB through the live runner, then amend or retire lesson deepseek_empty_reply_size_ceiling.
- [ ] W118 (08-02, claude) — Token-gauge honesty: the console TOKENS TODAY gauge read 0 while deepseek had just spent 677k on one turn and kimi sat at 172 dollars. Screenshot receipt 2026-08-02 04:18. Fold into the sensor-plane slice where per-seat spend becomes a measured field rather than a separate counter, per Daniil: fix it at the right time, not now.
- [ ] W119 (08-02, claude) — Namespace orphans: 760 namespaces hold inbox streams in live Redis and exactly ONE has a live seat. 114 are bifrost_c67_* T067 drill orphans, the rest t045/t066/t045s2 drill residue. Test drills mint a namespace per run and never reap it. Same class as F7 seat inflation, one layer down. Found 2026-08-02 while verifying room_feed against live Redis rather than a fake. Two asks: a drill-namespace reaper, and namespaced drills that clean up after themselves.
- [ ] W120 (08-02, claude) — T125 pin staleness: test_p7_broken_path_named_by_pre_commit and its one_hop sibling expect the datasheet to flag a ghost checker path (the checkers/ directory omitted) as a broken path reference in pre_commit.py. That ghost is gone - line 66 now uses the correct scripts/checkers/ path - so the pins assert a defect that was already fixed and fail on a stale premise. Either point them at a live ghost or retire them. Found 2026-08-02 during a regression sweep; not caused by that night's changes.
- [ ] W121 (08-02, claude) — UI layout audit, measured live 2026-08-02 05:00 against his spacing-and-placement ask. TWO findings, neither fixed (deepseek was mid-flight in bifrost_ui.py and his prior asks need his context). ONE: the presence strip #pills is only 155px wide (x480-635) in a 1280px viewport, flex/nowrap/overflow-x auto, holding 11 agent pills - so 5 of 11 seats are clipped out of view. Part of that is the deliberate GLANCE vs DETAIL density choice, but the strip itself is squeezed while the header has room to spare. TWO: #engine-room is display:none while fully populated - 13 children and 6342 chars of live vitals content, built every poll and never shown. Either a deliberate toggle worth a visible control, or the T079 vitals strip silently lost its slot. Feed gets 68.6 percent of viewport height which is reasonable. No horizontal page overflow beyond the clipped pills.
- [ ] W122 (08-03, claude) — agent_cli.py note has no --body-file, but a durable where-we-are note is EXACTLY the long
multi-paragraph body that must not ride argv. bifrost-send already learned this the hard way
(T083-C3-1: argv text containing flags or long bodies misparses -- hence --text-file, which the
corpus now states as an unconditional rule). Today, writing the seat handoff note, I had to shell
out through a python subprocess to pass the body safely as a single argv element.

Give `note` the same --body-file / --note-file door bifrost-send has. Same class as the CLI<->MCP
parity gaps tracked in T137: the capability exists, the door for it does not.

Found the same session: `wish` itself REFUSED a long positional body with "empty wish", which is
the identical defect one door over -- and its own error message names the fix (--text-file).
- [ ] W123 (08-03, claude) — `doc adopt` has no --supersedes, so re-adopting a loose .md after EDITING it mints a SECOND atom
with a second projection, and both render as current. Hit live today: adopting the session
risk/undo doc, correcting one claim in it, then re-adopting produced
docs/library/chronicle/20260803_session-risks-and-undo_adc7cd.md AND ..._135ddc.md -- same title,
same day, different content, no link between them.

`note` already solves exactly this: re-noting a stable --title supersedes the prior and SAYS SO
("superseded prior ADR_..."). Give doc adopt the same behaviour -- either --supersedes <atom-id>,
or infer it from an identical source path + title and stamp supersedes automatically.

Why it matters beyond tidiness: a correction is the MOST important edit a doc gets, and right now
correcting an adopted doc is the operation most likely to leave the wrong version equally visible.
Deleting the stale projection is not the workaround -- library deletions are Daniil's gate and the
substrate is append-only on purpose; the missing thing is the SUPERSESSION EDGE, not a delete.
- [ ] W124 (08-03, claude) — bifrost-send dedup is keyed on CONTENT, not on DELIVERY. Re-sending an identical body to a seat that
never received it is a silent no-op: the door returns the SAME message id and reports success, while
nothing is delivered. Hit three separate times in one session (2026-08-03), each costing a round-trip
before I realised the send had not failed -- it had been swallowed.

The interaction that makes it bite: a newborn seat seeds its cursor at the LANE TAIL, so anything
queued before its first boot is already behind it. The natural recovery -- "the seat missed it,
resend" -- is exactly the case dedup refuses. Workaround today is to perturb the text so the sha
differs, which is silly and undiscoverable.

MINIMUM FIX (honesty, not behaviour): when the door dedups, say so and say where. "deduped: sha
already at position X, which is BEHIND <recipient>'s cursor (never delivered)" turns a silent
no-op into a one-line diagnosis. RIGHT FIX: key the idempotency record on (sha, recipient,
delivered?) so a message that was never consumed can be re-offered. Related: T116 idempotency key,
and the cursor-tail seeding behind lesson bifrost_runner_backlog_skip.
- [ ] W125 (08-03, claude) — The runner singleton lock trusts PID-ALIVE while the roster trusts HEARTBEAT, and when they
disagree the lock wins -- so a wedged runner blocks its own replacement indefinitely.

Live receipt 2026-08-03: deepseek-red pid 62256 sat alive since 19:41 with a heartbeat 6231s stale.
The roster rendered it [DEAD]. A relaunch refused with "another 'deepseek-red' runner is already
live (pid 62256). Refusing to start -- one runner per agent avoids cursor races." Both statements
were true and they contradicted each other. The seat had wedged mid-reply, which is also why four
red-team attacks were lost: the process was alive enough to hold the lock and not alive enough to
answer. Recovery was a manual taskkill.

Note what does NOT cover this. self_restart IS wired (bifrost_runner_deepseek.py:1428 calls
maybe_self_restart) but it runs INSIDE the loop, so a loop that stopped turning never reaches it.
reaper.py:88 deliberately spares "a wedged-but-beating loop" because reaping it would rob a live
seat -- correct, but this case is wedged-and-NOT-beating. wake_seat.reap_decision takes pid_alive,
and the pid was alive.

FIX DIRECTION: the lock should require a FRESH HEARTBEAT, not merely a live pid -- a process can be
alive and useless. Steal a lock whose holder has not beaten within the worklive TTL, loudly and with
an audit line. This is the sibling of T072 item (4) "runner_lock steals a lock whose pid is DEAD";
the harder and more common case is the pid that is alive and silent.
- [ ] W126 (08-04, claude) — CORRECTION TO W125 -- my diagnosis was WRONG and the fix I proposed was dangerous. Do not implement
W125 as filed. The real defect is different, verified below, and is filed as its own entry.

WHAT I GOT WRONG. W125 said the runner singleton lock "trusts pid-liveness while the roster trusts
heartbeat" and proposed stealing a lock whose holder has not beaten within the TTL. Reading
core/comm/runner_lock.py:93 shows the lock already reasons about exactly this and rejects it in
writing: "Waiting is deliberately chosen over PID-liveness stealing. A stale-PID check would let a
restart proceed instantly, but a recycled pid or a paused process would let it evict a LIVE holder
and produce the split-brain this lock exists to prevent." Steal semantics are TTL-only (LOCK_TTL 20s)
with a Kleppmann fencing generation validated at the resource, and acquire_waiting already outwaits
a dead predecessor. The lock was CORRECT every time it refused me. My four "zombie" runners were
persistent runners idling in their wait loop exactly as designed -- I had simply never stood them
down, which is an operator error, not a defect.

WHAT IS ACTUALLY BROKEN, proven on live keys 2026-08-04: runner seats are structurally invisible to
the roster. There are two worklive key shapes and nobody bridges them.
  runners write   bifrost:worklive:<agent>              (bare)
  roster reads    bifrost:worklive:<agent>#<sid8>       (per-incarnation, roster.py:49)
roster.py's own header records the split at lines 8-9 and never closed it. Live proof: the kimi
runner is alive (pid 10608) and beating its bare key every ~40s, and `roster` renders
"[DEAD] kimi#51a77a23 beat=8790.9s". Worse, roster.py:9 calls the roster "the reaper's only sensor",
and reaper._provably_dead() returns True for that row -- along with every deepseek seat.

The fix is to make runner seats first-class in the roster (publish the per-incarnation beat the
roster reads), NOT to weaken the lock or the reaper. Filed properly with pins.
- [ ] W127 (08-04, claude) — CORRECTION TO W124 -- "silent no-op" is WRONG. The bus is not silent; I was not reading it.

Verified 2026-08-04 by sending an identical body twice and capturing both streams separately:

  stderr: [re-ask] identical request to t147probe already pending as 1785818090897-0 (1800s
          window) -- collapsed, not re-sent. Nudge it or change the ask; a repeat send costs
          t147probe a full turn.

The notice is there, it is accurate, and it even names the remedy. I missed it three times because
every one of my sends was piped through `| tail -1`, and _loud() writes to STDERR (bus.py:54-58).
Operator error, not a transport defect.

THE REAL DEFECT IS SHARPER AND WORSE. On the SAME call, STDOUT prints:

  [bifrost-send] -> t147probe [request] (id 1785818090897-0)

which is indistinguishable from a successful send -- same shape, same id, no hint anything was
suppressed. So the two streams CONTRADICT each other, and the one that lies is the default channel
that scripts, pipes and logs keep. This is the lesson a_warning_needs_a_channel_the_reader_actually
_has, in its nastiest form: the warning had a channel, but a louder line on a better channel said
the opposite.

FIX: the stdout line must not claim a send that did not happen. When the re-ask collapses, stdout
should say COLLAPSED and name the id it collapsed onto, instead of rendering the normal arrow line.
Do not touch the collapse LOGIC -- it is well built (P6 strand guard: it refuses to collapse onto an
original the recipient can no longer see, and it already exempts redrives and re-homes).

SECOND, SMALLER: the strand guard checks the original is still PRESENT in the recipient's stream,
but not whether it is still REACHABLE -- a message behind the consumer's committed cursor is as
unreachable as a trimmed one. That is exactly what bit me: a newborn seat seeded at the lane tail,
leaving my queued message present but permanently unread. Filed as its own note, since it needs a
cursor read the guard does not currently do.
- [ ] W129 (08-06, claude) — One absent-peer ask prints the UNATTENDED RECIPIENT warning FOUR times -- once for the send and once per redrive -- plus ask --peer's own NOBODY HOME line. Five stderr lines saying one thing. Measured live in the T197 drill 2026-08-06. The bus warning is right for every other caller, so the fix is not to delete it: either let a caller that has ALREADY observed and reported attendance suppress it (ask_peer knows the verdict before it sends), or dedupe the warning per recipient per short window so redrives stay quiet. Noise around a true signal is how a true signal stops being read. Trigger: dogfooding the T197 front door: the fix for silent absence overshot into repetitive absence. Land: T197c or a bus-ergonomics slice.
- [ ] W130 (08-06, claude) — A SETTLED ask's answer stays wake-worthy forever, so using the front door makes the session harder to keep wakeable. ask_peer polls answers NON-CONSUMINGLY BY LAW (T196c, so concurrent sibling sessions keep their mail) -- correct for its purpose. But the answer then sits on the lane as an unconsumed wake-worthy reply, while bifrost-sync --consume reports 'no NEW mail' because ITS cursor already advanced past it. The wake watcher peeks with a different cursor, re-detects the same replies on every arm, and exits. Measured live 2026-08-06: 5 arms, kinds narrowing handoff/inform/reply/request -> reply only, ending at 7 undrainable replies ALL of which were verifiably already read (4 were this session's own ask --peer dogfood answers). The remediation the watcher itself prints (drain legacy) does not clear them, and bifrost-skip-to-now correctly refuses under a live consumer. THE PERVERSITY: the more the T197 front door succeeds, the more undrainable answers accumulate. Candidate fixes: (a) settling an expectation marks its answer consumed-for-wake-purposes without moving the shared cursor; (b) wake-worthiness excludes replies that settled an expectation this seat owns; (c) the watcher and the sync door share one cursor notion so 'drained' means the same thing to both. Trigger: 5 consecutive stop-hook wake re-arms after shipping T197; the watcher's own printed remediation did not clear the condition it named. Land: a wake/expectations seam slice -- pairs with W129.
- [ ] W131 (08-06, claude) — The ship gate's door probe runs on a 10-30 percent margin and reports a THIN-MARGIN OVERRUN in the vocabulary of a CATASTROPHE. Measured 2026-08-06: door_probe.SLOW_BUDGET_S = 5.0 while three consecutive live runs took 3.46 / 3.53 / 3.68s (wall 4.04-4.45s). A push was refused with '[door-gate] fleet-wide boot hang. The verdict above carries the recovery.'; the identical push seconds later returned 'door: GREEN (4.45s) -- MCP path healthy' and shipped. Nothing was wrong. THE HAZARD IS NOT THE FALSE POSITIVE, IT IS WHAT THE FALSE POSITIVE TEACHES: a catastrophic-sounding verdict that clears on retry trains everyone -- including future me -- to re-run the push instead of reading it, and that habit is applied identically to a TRUE fleet-wide boot hang. A gate whose most alarming verdict is routinely wrong has negative value, because it disarms itself. Contributing: every tool added to the MCP door raises the probe's typical cost toward the ceiling, so this gets worse monotonically as the door grows (T200 added two today), and contention from a live runner is enough to cross it. Candidate fixes: (a) separate SLOW (budget overrun, WARN, ship proceeds) from HUNG (no response at DEFAULT_TIMEOUT_S=25, REFUSE) -- they are different findings and currently share one voice; (b) set the budget from a measured baseline with headroom rather than a round number, and re-derive it when the door grows; (c) on overrun, retry ONCE inside the gate and report the pair, so a transient is distinguishable from a trend instead of being resolved by the operator's retry. Trigger: T200 push refused with 'fleet-wide boot hang', identical push succeeded immediately after; I nearly accepted 'it passed on retry' as an answer. Land: door-gate calibration slice; pairs with the standing rule to calibrate an instrument before trusting its verdicts.
- [ ] W132 (08-06, claude) — The turn-start whisper spends 2.2 SECONDS of every single prompt counting mail. Measured 2026-08-06 at bfcfd54: agent.harness.context._unread_count takes 2.16-2.39s warm, and it runs from the UserPromptSubmit hook on EVERY user turn plus the boot path. The cost is entirely collect_boot_bifrost (a live bus round trip fetching up to 8 messages); the T201 filtering added on top is a comprehension over <=8 items and a 0.2s cold import. TWO CONSEQUENCES, and the second is the one that bites. (1) Every prompt pays 2.2s before the agent reads a word -- pure latency tax on the human. (2) It is roughly HALF of door_probe's entire SLOW_BUDGET_S=5.0, which is why the ship gate keeps flapping RED: measured 3.46-3.68s earlier today and 4.14-5.56s later the same day under a live runner, straddling the budget. So W131's thin margin is not merely a badly-chosen constant -- the boot path has one dominant cost centre sitting inside it, and every added tool or probe pushes it over. Candidate fixes: (a) cache the count for a few seconds -- the whisper does not need per-keystroke freshness, and a 5s TTL would erase nearly all of it; (b) ask the bus for a COUNT rather than fetching 8 message bodies (the render is discarded when the line is silent-at-0, which is the common case); (c) compute it asynchronously and let the whisper use the last known value with an age stamp -- honest and free. Any of the three also widens the door-gate margin without touching the threshold, which is the more durable fix than raising a number. Trigger: chasing a door-gate RED and discovering the whisper's mail counter is half the boot budget. Land: boot-latency slice; the measured cause behind W131's thin margin.
- [ ] W133 (08-07, claude) — THE OLDEST WISH, never filed as one: a word must mean ONE thing, and something must GUARD it. Daniil has restated this every ~2 weeks since 2026-06-19 in four different registers -- vocabulary (LEXICON, names-that-lie), aesthetics (naming canon, 'thematically fit up and down the whole stack'), filing (LIBRARY one-facet law, 'a home and an order'), and legibility ('make understanding the architecture intuitive for models working on the system'). On 2026-08-01 he named it the centre: 'Our current method for finding out what links to what is too unintuitive and costly so it doesn't get done, THIS is the heart of what I am trying to fix.' WISHLIST holds 130 open wishes and NOT ONE is about naming or vocabulary coherence -- the organ built to catch friction has never been pointed at the friction he calls the heart, because this always arrived as a conversation rather than as a stubbed toe. THE DOCTRINE ALREADY EXISTS AND IS UNGUARDED, which is Principle 4 (guards over discipline) indicting Principle 5 (one vocabulary, names must not lie): LEXICON says 'one authoritative definition per term' and has killed this class twice by name ('charter' had FOUR live meanings; session_checkpoint/snapshot/recovery, 'the shared name was a real bug'), and T174 shipped the exact template with the acceptance 'no identifier named ask means two things'. But nothing greps for a word doing two jobs, so violations accumulate silently. MEASURED, 2026-08-06/07, four fresh violations in ONE session, each costing real turns: 'drained' (three cursor families, cost 6 turns and a fleet pause), 'unread' (counter vs consume door, T201), 'wakeable' (a grounded helper with correct citations still inverted a conclusion by equivocating on it, T207), 'fixed' (baseline subset vs full run, caught 4 minutes after shipping, T208). Plus one LIVE and unacted: T176's 'note' means three things on three planes WITH OPPOSITE POLICIES, filed 2026-08-05, still proposed. TWO DETECTORS NOW EXIST, built by accident this session: (1) the cold-encounter test -- a fresh reader given only --help predicts behaviour, and mispredictions locate overloaded terms precisely because it cannot disambiguate from familiarity the way a steeped reader can (T209: 0/3 on two cases, and one instance named the cause itself); (2) helper equivocation as a leading indicator -- when a helper conflates two senses of a word, that word is overloaded IN THE CODE, and since we share architecture its confusion predicts mine. LANDING: promote coherence from an unwritten thesis to a guarded principle -- a checker in the T174 shape, pointed first at T176's 'note'. Trigger: seven weeks of the same wish, four registers, 130 wishes filed and none of them this one; four fresh violations measured in a single session. Land: a naming-coherence guard in the T174 shape; unparks the T101/T104 pair and gives T176 an owner.
- [ ] W134 (08-07, claude) — AMENDS W133 -- I filed it on a premise I had not checked, and the corrected version is sharper. W133 said the naming doctrine was UNGUARDED, with Principle 4 (guards over discipline) indicting Principle 5 (names must not lie). THAT IS WRONG. scripts/checkers/check_boundaries.py shipped 2026-06-19 with rule 4 no-duplicate-class-names ('one class name = one definition, ubiquitous language') and rule 5 no-duplicate-module-basename, and it records a real collision (session_state.py, 2026-07-07) as resolved. The guard exists, runs in CI, and works. I asserted its absence from the shape of the violations instead of reading it -- the same error I made yesterday when I claimed a test failure was mine from an inconclusive run. WHAT IS ACTUALLY TRUE, and it is a different and more useful finding: the checker answers a DIFFERENT QUESTION than the one my four violations pose. It catches HOMONYMS -- two things sharing one identifier, which is greppable. All four of mine were FORKED SEMANTICS -- one CONCEPT implemented by several mechanisms that quietly disagree, with no duplicate token anywhere: 'drained' spans three different cursor keys (cursor:{agent}, cursor:seat:, cursor:lane:); 'unread' spans _unread_count and the consume door; 'wakeable' is not an identifier at all and lives only in prose and reasoning; 'fixed' is ONE identifier with ONE definition computed under two unshared assumptions. Opposite shapes: a homonym is one name over two meanings, forked semantics is one meaning under two names that drifted. Token-level and AST-level checkers are STRUCTURALLY blind to the second class and no tightening will help. SO THE ASK CHANGES: not 'write the missing naming guard' (it exists) but 'build a detector that operates on MEANING rather than tokens'. Two candidates already demonstrated in one session: (a) the cold-encounter test -- a fresh reader given only the public surface, whose mispredictions locate the fork precisely because it cannot disambiguate from familiarity (T209, 0/3 on two cases, one instance naming the cause itself); (b) helper equivocation as a leading indicator -- when a model conflates two senses while reasoning about the code, the concept is forked IN THE CODE, and since we share architecture its confusion predicts mine (T207: a helper with correct citations inverted a conclusion by equivocating on 'wakeable', which is a word I had personally equivocated on for six turns). AND THE PRIOR ART IS OURS: the 2026-07-30 relationship-types design (note daniil-intuitive-mechanical-architecture-map-2026-07-30, fleet-reviewed by four seats, NOT BUILT) already states this law one level up -- DERIVED / AUTHORED / OBSERVED planes where 'the graph may join but never launder one into another'. That IS a forked-semantics guard, for edges instead of concepts. It is blocked behind gate-health kill drills. Trigger: I filed W133 asserting a guard was missing without reading the guard; it shipped seven weeks ago and answers a different question. Land: same landing as W133, with the ask corrected: a meaning-level detector, not another token-level checker; unblocks alongside the 07-30 relationship-types design.
- [ ] W135 (08-07, claude) — TWO REAL FORKED TERMS, found by a fan-out and worth fixing: (1) 'open' -- 61 files across 13 subsystems, carrying at least TWO unrelated concepts: ACTIVE/UNCLOSED state (valid_to open, an open planning round, the OPEN.* ask states) and FAIL-OPEN permissiveness (a guard that proceeds when it cannot check). Those are opposite in spirit -- one means 'still running', the other means 'do not block' -- and the biggest-spread term in the codebase should not be doing both. (2) 'home' -- 12 files: 'someone is present/available' (my own NOBODY HOME render, shipped T197 the same day) versus 'designated storage location / re-home target' (reaper.py re-homes a dead seat's mail). Both meanings are load-bearing in the SAME subsystem, and I introduced the second reading hours after the first existed. METHOD NOTE FOR WHOEVER PICKS THIS UP: these two survived a controlled re-run. The first pass produced ~50 percent DIFFERENT verdicts, which was an artifact -- the evidence gatherer used git grep WITHOUT -w, so the fan was fed 'provenance' as usages of 'prove' and 'DeepSeek' as usages of 'deep'. Word-boundary re-run flipped 7 of 20 verdicts (35 percent artifact rate) and dropped 7 of 40 terms for having no real usages at all. Everything else that survived is ordinary English polysemy (verb/noun: prints, hits, others) rather than concept forks, because the question asked was too broad -- 'does this word have several meanings' returns linguistics; the question that returns BUGS is 'do two parts of the system RELY on different meanings in a way that could cause a defect'. Cost of the whole hunt: $0.18 and about four minutes across two 40-way and 33-way fans. Trigger: the W133 forked-semantics hunt finally ran, and produced two real finds plus a measured 35pct artifact rate in my own evidence gatherer. Land: vocabulary slice alongside W133/W134; 'open' is the high-spread one and the natural first target.
- [ ] W136 (08-07, claude) — A BENCHED lesson still pollutes the consolidation-candidate graph. Found 2026-08-07 in the funniest possible way: I benched three test fixtures (beat_hook_exp, offline_exp, dup_exp -- fake agents, empty recommendations, success=yes, sitting in the recall value-rate denominator while structurally incapable of earning credit), then recorded a lesson ABOUT benching them -- and the store immediately printed 'related lesson: dup_exp (2/5 dims) -- consolidation-pass candidate' on that very lesson. This is DOCUMENTED behaviour, not a bug: mark_benched's own docstring says it stops a lesson competing for recall surface slots 'while keeping full history + full-corpus visibility', and the relatedness graph is full-corpus. So benching correctly fixes the DENOMINATOR problem and does nothing for the RELATEDNESS problem, which are two different harms from one cause. The consolidation surface is where a curator decides what to MERGE, and merging a real lesson with a fixture that has no recommendation would silently blank real advice. Options, cheapest first: (a) the relatedness/near-dup pass skips benched records when proposing merges (they remain visible to search, which is what full-corpus visibility is actually for); (b) a lesson with an EMPTY recommendation is never a merge candidate regardless of bench state, since a merge target with nothing to say can only subtract; (c) an intake guard refuses a lesson whose recommendation is empty, so fixtures cannot enter the corpus in the first place -- three fixtures from three fake agents got in and nobody noticed for weeks. Trigger: benched a fixture, then watched it recommend itself for consolidation against the lesson about benching it. Land: recall curation slice; (b) is the smallest and closes the real harm without touching bench semantics.
- [ ] W137 (08-07, claude) — Truncation must be a RENDER concession, never a data concession: any door that clips a body (bifrost-sync render, mailbox list, boot peek) must MINT and print the blob ref at clip time, and every reader door (mailbox --open, bifrost-fetch, boot) must auto-resolve that ref to the full body on reach. Receipt 2026-08-07: veteran's 3-point peer note clipped mid-point-3 with no pointer; spill dir empty for it; mailbox list showed sha 518bfcb0c5 while mailbox --open denied the same sha (index_lag 1, evicted 2211); bifrost-fetch exists but only takes refs some renders never mint. Four doors, zero reconstruction. The resolver exists; mint-at-clip coverage and the list-vs-open fork are the gaps.
- [ ] W138 (08-07, claude) — A LIVE SENDER IS A DOOR, and it is in no manifest. Found 2026-08-07 by watching a fresh seat spend six-plus tool calls reconstructing a truncated bus note: it tried the spill directory, mailbox LIST, mailbox OPEN, bifrost-fetch, a raw redis stream scan, promoted, and git log. The full body had been sitting in research/in-flight/_note_to_fresh_seat_2.txt the entire time, because a standing rule (lesson bifrost_send_always_text_file) makes every bifrost-send body go through --text-file -- so the SENDER'S COPY exists on disk before the render can ever clip it. Nothing in any door manifest, boot render, or truncation notice says 'ask the sender' or 'the sender wrote this from a file'. THE CHEAPEST RECONSTRUCTION PATH IN THE SYSTEM IS A PEER WHO IS STILL ALIVE, and it is the only one with no door. Concrete asks, cheapest first: (a) when a render clips a body, the clip line names the SENDER and says a live sender can resend -- one sentence, no new machinery; (b) since --text-file is already the standing rule for sends, record the source PATH in the message meta at send time, so the truncation notice can point at the sender's own file rather than at a blob that may never have been minted; (c) the bigger fix, which the fresh seat filed as W137: truncation is a RENDER-TIME decision, so the renderer must MINT the pointer at clip time and every reader door must resolve it transparently -- half exists already (spill + bifrost-fetch), the gap is coverage on this path. FOUR REAL DEFECTS SURFACED BY THAT HUNT, worth keeping separately from the punchline: the render truncated with NO pointer minted (unrecoverable by design, not by accident); mailbox LIST shows a sha that mailbox OPEN denies (two index families disagreeing about one record); bifrost-fetch needs a blob ref this render never created (resolver present, mint missing); and long bodies fragment per T043 so a raw-stream substring search fails across fragment boundaries. Trigger: watched a peer burn six tool calls on a body I had written to a file before sending it. Land: W137's truncation-pointer slice; (a) is one sentence and closes most of the felt cost.
- [ ] W141 (08-10, claude) — A slice in VERIFYING keeps its file lock, so a solo builder serializes behind their own
review latency. Hit THREE times on 2026-08-10: T252 blocked T258, T262 blocked T267, and
T268 blocks T267 right now. By the time a slice reaches verifying its work is COMMITTED and
PINNED, so the lock is protecting against an edit nobody is making -- the reviewer reads
git, not the worktree. Either VERIFYING should release the file lock, or claim should offer
a queue-behind instead of a hard refuse. Asked Heimdall for a read rather than changing it
on my own judgement, since I own that gate and ratifying my own convenience is the T227
defect.
- [ ] W142 (08-10, claude) — THE ID-BEFORE-THE-REGISTRY COLLISION IS A DOOR PROBLEM, NOT A DISCIPLINE PROBLEM. Three
times in one week I named an artifact (t262-*, t273-*) before the ledger minted the id, and I
cited the identifiers_minted_before_the_registry_speaks_collide lesson two days before the
last two. Noting it a third time is not going to work; the recall fires and I still do it,
because the file gets written in the same breath as the thought and the propose call happens
after.

The ergonomic cause is real: to name a file correctly I must first run propose, read the
minted id out of prose output, then write the file -- three steps at the exact moment I am
holding a design in my head. So I guess, and the guess is right about half the time.

WISH: make the correct order the EASY order. Either (a) `task propose --json` returns the id
in a parseable field so a one-liner can propose-then-name, or (b) a `task mint` that reserves
the next id without a full proposal, or (c) `doc new --arc <task>` already infers the arc --
extend it to REFUSE a filename containing a T-number the registry has not issued. Any of the
three turns a discipline problem into a door.
- [ ] W143 (08-10, claude) — THE --text-file ESCAPE IS WIRED TO ONE DOOR AND EVERY OTHER DOOR STILL EATS PROSE.
bifrost-send grew --text-file because a message body containing flag-shaped text aborted a
send (2026-07-16, live receipt). The fix was applied there and nowhere else. Today the same
hazard bit twice through OTHER doors, hours apart, with me filing a lesson about it in
between: `learn` lost the word "place" to backtick command substitution, and `task propose`
lost "doc new" from T275's description the same way.

That the corpus lesson fired and I did it again is the point. This is not a discipline
problem, it is the T263 shape one plane over: a capability wired to one of two doors, so the
doors that lack it fail silently and the failure is only visible if you read the stored
record back.

WISH: give `learn`, `task propose`, `wish` and `note` the same --text-file escape
bifrost-send already has -- one flag, same name, same semantics -- so the safe path is the
same path everywhere. Cheaper alternative if that is too wide: have the doors DETECT
metacharacter loss by comparing the received argument against a checksum the caller cannot
easily produce... no. The flag is the fix; the detection idea is worse than the disease.
- [ ] W144 (08-10, claude) — ask --with refuses paths outside the repo root, so scratchpad-built evidence packs must be hand-copied into scratch/ before a fan can see them. Wish: auto-copy readable session-scratchpad files into the pack (keep the refusal for everything else outside the root). Felt 2026-08-10: first success-vocabulary fan spent $0.005 on three honest abstentions because the pack lived in the scratchpad. Trigger: any ask --with evidence pack assembled in a session scratchpad.
- [ ] W146 (08-12, claude) — boot's `...[truncated]` cuts the PAYLOAD and keeps the decoration: a character-count cut lands mid-clause, so T058 rendered as "R7 Mid-turn clarification (deepseek b5): a question that pauses his loop and folds the ...[truncated]" — attribution intact, the actual task lost. This is the T242 defect class (a confident window presented as the whole) aimed at the READER instead of a helper, on the one surface every seat reads every session. Wish: cut at field boundaries and drop parentheticals/source-stamps BEFORE payload verbs; failing that, stamp each cut line with its drill command. Trigger: fresh seat (08-12) had to guess what three ledger lines meant. Land: boot render, same family as W01/W04.
- [ ] W147 (08-12, claude) — boot detects a task mismatch and spends the full budget anyway: booted with task="enable bypassPermissions default mode", the page printed "Governing arc: (none matches the active task)" — the ranker KNEW nothing matched — and still rendered the whole resident-fanout arc, the Eye, the utterance law. A short page should be a legal output when match strength is low. Trigger: ~90% of an 08-12 boot page was orthogonal to the stated task. Land: boot budget scaled by match strength (floor: directive + constraints + own-liveness always render).
- [ ] W148 (08-12, claude) — the SessionStart whisper promises what boot never delivers: "6 unread bus msg(s) and a fresh last-session draft waiting" — then the boot page resolved neither (no payloads, no draft pointer). A count without a payload is a standing second-call tax at every session start. Wish: whisper facts either render in the boot page or carry their drill command inline in the whisper itself. Trigger: 08-12 fresh seat left wondering where the draft lives. Land: W13 primer/whisper contract.
- [x] W149 (08-12, claude) — FOLDED 2026-08-13 same-night (claude/deepseek fence, RED 4408fbc7): `# YOU:` line renders before siblings, daemon-first never-spawn, dead-seat vs never-armed distinguished, UNKNOWN on cannot-tell, purity pinned static+dynamic (tests/test_w149_boot_own_liveness.py 13/13; live receipt: this session's own boot rendered NOT WAKEABLE with its arm command). Was: boot reports everyone's liveness except the reader's own: it rendered my sibling's idle minutes and the fleet doctor, and NOT that this session's wake watcher was dead — I learned I'd been unreachable all session from the Stop hook at session END. The detection exists; it fires at the wrong end. Wish: one line next to `siblings:` — "YOU: wakeable (watcher pid N)" / "YOU: NOT WAKEABLE — arm with <cmd>". Trigger: 08-12, whole session dark to DeepSeek/Daniil with the answer one line away. Land: boot heal-line family (W03 kin); pairs with W145's reboot-kills-watchers case.
- [x] W150 (08-12, claude) — FOLDED 2026-08-13 same-night (claude/deepseek fence, RED 4408fbc7): each receipt inlines its recommendation via distiller._clip_words(130), degrades to bare slug on any store trouble, drill line stays (tests/test_w150_badge_recommend_inline.py 5/5; live receipt: the badge now opens with the drain-the-lane rule inline). Was: badge earned-by lessons render as bare slugs: boot said my badge was earned by wake_drain_the_lane_you_ARMED_not_the_one_docs_name — the exact lesson about the exact thing that broke that session — and its content only reached me later via recall-at. Wish: inline each earned-by lesson's recommend line (~15 tokens each) under the badge. The badge is the one place boot already knows which lessons define THIS seat. Trigger: 08-12 wake-watcher re-arm walked into the failure its own badge names. Land: boot identity block.
- [ ] W145 (08-12, claude) — an OS-forced reboot silently kills every resident seat and nothing notices until a human relaunches. Felt 2026-08-12: Windows Update (MoUsoCoreWorker, then TrustedInstaller ×2, KB5120708/KB5121003/KB5123304) rebooted the idle machine at 13:32; the Claude Code app and all live sessions died mid-flight (one torn down with a live background task — a wake watcher among them), and the fleet stayed dark until Daniil relaunched at 19:09 — a 5.5h unwakeable gap no one was paged about. Wish, smallest first: (a) a boot/status heal line that detects "last app exit was an OS shutdown" (BootId changed + sessions torn down, receipts in %APPDATA%\Claude\logs\main.log + System event log 1074) and says so, so the next seat knows why the watchers are gone; (b) a machine-side auto-relaunch of the seat-holder after reboot (Task Scheduler at-logon entry) so the wakeable seat resurrects without a human. Trigger: any Patch-Tuesday-style forced reboot while seats are resident. 08-12 same-day update: the forced-update trigger has since been suppressed at the OS level on this box, so the wish STANDS on its other legs — the reboot causes that suppression cannot touch (GPU-TDR hard resets, power loss, deliberate reboots) kill resident seats exactly the same way.

- [x] W00a (07-18, kimi blocker) — ephemeral-seat stop-hook exemption → FOLDED same day:
  AKASHIC_STOP_WAKE=0 + pins (tests/test_stop_wake_exempt.py). The wish-shaped blocker that
  proved wishes can close within hours.
- [x] W00b (07-18, kimi D4) — label-write integrity → FOLDED as T094 gate item G8, ruled by
  Daniel same day. A wish that graduated to governance.
- [ ] W52 (07-21, claude — kimi's lockout) — headless-seat hooks are repo-relative
  (`py scripts/hooks/claude_trace.py`), so ONE `cd` inside a compound Bash command strands the
  session cwd and every PreToolUse hook then fails-closed, hard-blocking ALL local tools (bus is
  the only survivor). Cost kimi its acceptance session tonight; recovery needed exit-0 shims from
  a second seat. Trigger: cwd drift is a known Windows hazard and our hooks amplify it into a
  total lockout. Land: resolve hooks against repo-root absolutely in the launcher config (or a
  wrapper that anchors to the git root) — turns a session-killer into a no-op. Companion to the
  T077 daemon (remembered → automated).
- [ ] W53 (07-21, kimi — acceptance re-test) — docs-zone canon is `<topic>-<kind>-<YYYY-MM>`
  but reconciliation/arc-closer docs are born day-dated (they close on a specific day), so the
  law's own birth records read as canon violations (library-schema + revival-mesh both flagged).
  Trigger: the acceptance suite's zone-conformance check fires on the fleet's own crown docs.
  Land: carve a canon exception for the `reconciliation` kind (day-date is lawful, it records the
  close date) OR ratify a rename convention — decide at the library gate. Do NOT rename existing
  files (cited paths, P1). NOTE: kimi generalized this to `revival-mesh` as "awaiting-ratification
  rot too" — VERIFIED FALSE: revival-mesh's gate is genuinely still open (auto-revive posture, on
  the morning-gate list). The date-half applies; the staleness-half does not. Stranger over-reach
  caught by a citizen who knew the ledger — the fence working both directions.
- [x] W54 (07-21, claude — kimi F3) — FOLDED 2026-07-22 @eccf2ff: injections_by_family
  (core/recall/at_action, pure when handed a list) + one-line gauge on THREE surfaces —
  injections verb header, doctor `## ACTIVATION` block, wrap-draft "Recall activation by
  family" line; conductor renders first, even at 0/N. Pins tests/test_w54_injections_by_family.py
  7/7. First live read: **conductor 5/43 24h** (the audit had read 1/35 — the Fable seat's
  conducting moments fired it 4 more times within one session of the finding). E1's RECALL
  arm now has its instrument and its baseline. Was: injections-by-family gauge at wrap/doctor
  so activation claims read the instrument before shipping adjectives. Trigger: "recall-at
  proven tonight" was written while the ledger showed one conductor firing in 35 — the check
  existed, nobody ran it (kimi Fable-5 observation F3/Q5).
- [ ] W55 (07-21, claude — kimi F1 + the recursion) — Verify-the-citation / verify-the-guard
  check: any doc/brief/commit citing a peer artifact ("X warned/found") OR claiming a fix
  "now exists" must have it on disk at compose time (or the cite says "queued"); new
  acceptance-check class alongside zone/header conformance. Trigger: the E1 doc cited a kimi
  counter that never existed AND its own amendments then asserted a randomized launcher +
  filed lesson + W54/W55 while none were on disk yet — the assert-guard-not-had pattern,
  recursing inside the rigor doc itself; caught by sibling fence-grep. Lessons:
  crown_doc_phantom_citation + kimi's verify-citation-exists-before-crediting (compose-side
  + review-side of one check). Land: comprehensibility-guard sibling (the ghost-path check
  extended from paths-in-prose to cited-artifact claims) / kimi's standing acceptance suite
  (new class).
- [ ] W56 (07-21, claude — kimi F5) — Presence rule one seat short: doctor reads kimi OFFLINE
  while kimi's headless-interactive seat is live mid-session (W40's tri-state fix covered
  claude's interactive seats; kimi's launcher-spawned seats never register worklive). Trigger:
  the fleet's liveness organ misread a live citizen during the very audit it was misreading —
  and the misread poisons auto-revive decisions (a revive could target a live seat). Land:
  kimi launchers register worklive/presence like claude's SessionStart hook does; T077 A3
  sibling.
- [ ] W57 (07-24, Daniel via claude — :8787 console screenshot at 08:05) — Per-agent
  attribution legibility: "I can't tell who is doing what." The trace stream renders
  kimi/deepseek tool lines as a flat interleaved list (search_files/read_file rows) with
  only a small name prefix; at working tempo the fleet's activity is illegible. Trigger:
  Daniel watching the T106 fence + evolution round dispatch live and unable to follow
  actors. Land: deepseek UI lane — this IS the NOW-card charter (MCP reconciliation
  gate item 3: live per-agent card w/ task/status/substep/stream) + T002 (one collapsible
  card per agent) + T079 engine-room; fold as their acceptance evidence.
- [ ] W58 (07-24, Daniel via claude — same screenshot) — Aurora background misrendered:
  "the aurora is off to the left somewhere" — the WebGL aurora paints a small strip in
  the top-left corner instead of the full-bleed backdrop; rest of the canvas is flat
  black. Suspect canvas-size/viewport binding (resize handler or DPR scaling) rather
  than the shader. Land: deepseek UI lane; T007 (Void theme + aurora perf bench) is the
  natural home.
- [ ] W59 (07-24, Daniel via claude — same screenshot, recurring) — "the AI avatar icon
  is still misaligned on the left": the CL avatar chips sit vertically offset from their
  message cards (avatar top-aligned into the gutter while the card starts lower; the
  user chip at the composer overlaps the Inform/Steer/Interrupt buttons). STILL = second
  report; promote above cosmetic-backlog priority. Land: deepseek UI lane (bifrost_ui
  message-row flex alignment); pin a screenshot-diff or DOM-assert in check_ui_contract
  so it cannot regress silently a third time.

- [ ] W60 (07-24, Daniel via claude — "I saw a few .md files being generated... reflexive
  habit?") — Runner write-door library guard: the guarded write_file door accepted both
  seats' SOTA halves as hand-made projection-lookalike .md files in docs/library/report/
  (no atoms behind them; invented frontmatter + rel names). --verify's orphan rule caught
  them post-hoc and they were re-homed, but the DOOR should refuse/warn on docs/library/**
  + loose docs/*.md writes and teach `doc new` — deny-at-the-door, same posture as the
  birth guard, one lane earlier. Land: deepseek ToolBox lane (it owns write_file); pin =
  a runner write to docs/library/ is refused with the doc-new teaching message.

- [ ] W61 (07-25, Daniel via claude — fresh-seat onboarding audit) — **GROUND FIRST points at
  a deleted path.** boot's very first instruction was `GROUND FIRST:
  chronicles/session-reflection-2026-07-23-fable-conductor-night.md [as of 2026-07-23]` —
  that file does not exist. The library migration re-homed it to
  `docs/library/chronicle/20260723_session-reflection-fable-s-conductor-nig_415441.md`; the
  stored `grounding-pointer` note kept the pre-migration path. Mechanism: agent_cli.py:1262-1276
  age-stamps the pointer (`GROUNDING_FRESH_DAYS` → `[STALE? Nd old]`) but NEVER checks that the
  path resolves — a 2-day-old pointer reads "fresh" while being dangling. Cost to a fresh seat:
  its first grounding hop fails, and it must search to recover (I did). Land: claude lane.
  Pin = boot resolves the path before rendering; unresolvable → `[MOVED? searching library]`
  plus the atom-id fallback, and the migration rewrites grounding pointers with the files.

- [ ] W62 (07-25, Daniel via claude — same audit) — **delta's divergence alarm prints an
  un-runnable remedy.** `delta claude` reported `git: HEAD moved BACKWARDS or diverged
  (f6a96df -> 920087a); history changed under you -- inspect: git log 920087a..f6a96df`. That
  command fatals: `f6a96df` is not a valid object in this repo (`rev-parse --verify` → "Needed
  a single revision"). So the stored boot mark holds a sha git cannot resolve, and the alarm
  reads as history-rewrite when it is really an unresolvable mark. Land: claude lane. Pin =
  delta `rev-parse --verify`s BOTH shas before claiming divergence; unresolvable old mark →
  "your last boot mark is no longer in this repo (re-marked)", not a rewrite alarm.

- [ ] W63 (07-25, Daniel via claude — same audit) — **door-detect asserts a fleet fact from a
  process-local view.** CLI boot printed `door: CLI-shell -- native akashic tools NOT attached;
  remedy: ... restart` while the MCP door WAS attached in the same seat (MCP boot printed
  `door: MCP-native` for the identical call). The shell process genuinely cannot see the MCP
  door — but it states the absence as fact and prescribes a restart, sending a fresh seat to do
  unnecessary work. Land: claude lane. Pin = soften to "this process is CLI-shell (cannot see
  an MCP door from here; if your seat has one, ignore)".

- [ ] W64 (07-25, Daniel via claude — same audit) — **the heal banner outranks the context.**
  The first three paragraphs of every boot are fleet-hygiene: "484 UNKNOWN Redis-only key(s) ...
  INVESTIGATE", 9677 Redis-ahead keys, 5152 expected — roughly 600 tokens of alarm ABOVE the
  orientation header, and the 484-key line explicitly disclaims the reader ("owner: whoever
  mints this family, not the booting seat"). A fresh seat's first impression is an alarm it is
  told not to act on. Land: claude lane. Pin = heal output moves BELOW the context block (or
  collapses to one line + `py agent_cli.py heal` for the detail) unless the booting seat is the
  owner; unowned drift never leads.

- [ ] W65 (07-25, Daniel via claude — same audit, lived end-to-end) — **the stop-hook arm
  ritual is a dead end while T066 is live.** Sequence, all in one session: stop hook demanded a
  manual arm → armed exactly as instructed (`BIFROST_WAKE_LANE=work`, harness-tracked) →
  watcher **insta-fired and exited rc 0**, detecting 8 messages → recall-at surfaced the right
  lesson unprompted (`wake_watcher_insta_fires_lane_divergence`) → its prescribed fix
  (`BIFROST_CONSUME_LANE=work ... --consume`) returned **"(no messages consumed)" + "1 LEGACY
  STRAGGLER — lane write failed upstream"**, which is T066 verbatim. So the watcher's DETECT
  cursor sees 8 that the work-lane DRAIN cannot clear; the only remaining remedy is the
  pause → skip-to-now → resume cursor surgery. Net: **a seat cannot stay wakeable without
  either super-admin cursor surgery or the T066 sender-side fix.** Two sub-findings: (a) T050
  item 6 ("stop hook arms the wake listener itself") sits in the DONE block, yet the hook still
  asks the SEAT to arm by hand — done-but-manual; (b) the recall organ performed beautifully
  here (right lesson, unprompted, at the exact moment) — the failure is downstream of it, which
  is the good kind of failure. Land: T066 is the root fix (claude lane); until it lands, the
  stop hook should run the consume→skip ritual itself or stop demanding an arm it knows will
  insta-fire. Pin = arm-then-idle survives 60s with unread mail present.

  **CORRECTION (same session, after two more probes — the above over-blamed T066).** The real
  headline is smaller and worse: **`bifrost-sync --consume` prints `(no messages consumed)`
  while consuming messages.** Both lanes reported that line; a follow-up peek showed unread had
  gone **8 → 3**, and the 3 survivors were all traces — i.e. it had silently cleared all five
  real messages (2 asks / 3 fyi) and said nothing. That false-negative line is what produced
  the wrong T066 diagnosis above, in a live session, by an agent holding the correct lesson.
  A status line that under-reports its own effect is a **names-that-lie defect on the door's
  most-used verb** — it teaches every seat that the drain is broken and pushes them toward
  cursor surgery they do not need. The T066 straggler line is real but was NOT the blocker.
  Land: claude lane, cheap. Pin = `--consume` reports the actual count it advanced
  (`consumed N (M traces skipped)`), and `(no messages consumed)` appears only when N==0.

- [ ] W66 (07-25, claude — observed while fencing tonight's build) — **the suite writes drill
  notes into the LIVE store, and they outrank real state at boot.** Running `pytest tests/`
  left `drilldone51d538-status` ("GOVERNING ARC DOC ... ARC COMPLETE") and
  `next-focus: FOCUSNOW-2e689e: engine before UI` in the live notes at 06:16 — visible in
  `notes`, and eligible to be rendered as a real seat's governing arc / current directive.
  Two costs, one cause: (a) a fresh seat can boot into a TEST's directive; (b)
  `test_boot_orientation::test_cold_start_drill_answers_the_four_questions` becomes
  order-dependent — it passes standalone and fails mid-suite because a sibling test's newer
  note wins the governing-arc pick. This is T070's known gap with a concrete blast radius:
  `_AISETUP_TEST_ISOLATED` yields fresh instances that still bind LIVE backends unless the
  env also redirects. Land: claude lane, rides T070. Pin = a full suite run leaves zero new
  notes in db 0 (assert the live note count is unchanged across a run).

- [ ] W67 (07-25, claude — hit while landing tonight's where-we-are) — **`note` has no
  `--note-file`; the C3-1 footgun is only half-fixed.** Writing a real where-we-are body
  through `py agent_cli.py note claude --title where-we-are --note "<body>"` failed with the
  top-level usage dump: prose containing flag-shaped and list-shaped lines misparses in argv,
  which is EXACTLY the failure C3-1 fixed for `bifrost-send` by adding `--text-file`. The fix
  was applied to one verb, not to the class. Every long-body write verb has it (`note`,
  `learn --recommend`, `handoff --note`). Workaround used tonight: the MCP `note` tool, which
  takes the body as a parameter and never touches argv — so the CLI door is strictly worse
  than the MCP door for exactly the writes that matter most. Land: claude lane. Pin = `note
  --note-file` round-trips a body whose lines start with `--`, `*` and `>>`.

- [ ] W68 (07-25, deepseek — hit filing its own lesson tonight) — **ToolBox `knowledge_learn`
  has no `category` parameter**, so a runner cannot categorise a lesson it files. deepseek hit
  this filing `builder_stance_file_the_failure_trace` and the lesson landed
  `category: uncategorized` despite being explicitly a `correction`. The CLI `learn` verb has
  `--category`; the third door does not. Same family as T067 item 1 (the runner ToolBox is a
  third door `check_door_parity` never sees). Cost: recall relevance keys off category, so
  every runner-filed lesson is slightly harder to surface than a CLI-filed one. Land: deepseek
  ToolBox lane. Pin = a runner-filed lesson can carry `correction` and door-parity covers the
  ToolBox surface.

- [ ] W69 (07-26, claude — hit diagnosing the C7-4 boot-hang regression) — **the door pins are
  never run at a moment that would catch a wedged door.** `test_t078_w3_mcp_door.py` P6 exists
  precisely to catch "MCP boot hangs", and it was **RED for a day while both claude and codex
  seats hung on boot** — Daniel found it, the machine didn't. The guard was correct, current,
  and unrun. Cost: a full session's worth of two seats wedged, and the fix only started when a
  human noticed a pattern across agents. Land: run the fast door pins (P6 + the new
  `test_subprocess_stdin_sever.py`, ~40s together) somewhere they cannot be skipped — a
  pre-push hook, or the session-start whisper reporting a red door pin the way it already
  reports funnel/delta. Pin = deliberately re-introduce a boot-path stdin leak and confirm the
  machine says so before a seat does. *Generalisable beyond this bug: any pin guarding a
  BOOT-time organ is worthless if it only runs when someone remembers to run the suite.*

- [ ] W81 (07-26, claude — hit while landing the progress-age escalation) — **the four derived-doc
  generators have no one-verb door.** W80 already records the failure (adding a module leaves
  the docs stale and the comprehensibility guard fails; it bit the last seat THREE times in one
  session), and the handoff's remedy is a list of four script names to remember and run by hand
  — with no path, so the first attempt today went to `scripts/` and they live in
  `scripts/generators/`. A remedy you must remember is the same class of thing as a red pin
  nobody runs (W69). Cost: small every time, paid by every seat, and the failure lands on the
  NEXT person's suite run rather than the author's. Land: `py agent_cli.py regen` running all
  four (or a pre-push hook step, which also removes the remembering). Pin = touch a module,
  run the verb, and the comprehensibility guard is green without anyone naming a generator.

*(W54/W55 were double-filed by two claude seats during the C2 audit collision — merged into
the numbered entries above, 2026-07-21; all content folded, nothing dropped.)*

- [ ] W128 (08-04, claude/T159) — **a reusable mutation runner for pre-registered pins, with a
  first-class NULL CONTROL.** Mutation-testing the T159 pins found 2 of 5 were not guarding
  anything, and the harness that found it was a throwaway in the session scratchpad. The method
  baseline asks every slice to mutation-test its pins; today each seat hand-rolls the same
  patch-run-restore loop, so in practice most slices skip it and pins land unverified.
  Trigger: T159 shipped 5 pins that all looked fine and 2 of which guarded nothing — one because
  no pin exercised the path, and the harness could not tell that apart from the other case.
  Want: a mutation-runner door (a `mutate` script under `scripts/`, or an `agent_cli` verb —
  the shape is the builder's call) taking a test file and a mutation spec, reporting each
  mutation as CAUGHT / SURVIVED / NULL.
  The NULL class is the load-bearing part: T159's M1 survived because it was *semantically null*
  (EXCEPTIONS is a subset of unreachable, so the clause removes 0 modules today), and a report
  that cannot say "this mutation changed nothing" will eventually be used to delete a good pin.

- [ ] W139 (08-07, claude/boot) — **a wake payload should be a doorbell, not the whole ledger.**
  Arming `bifrost_wake.py` and having it fire wrote a **50,264-token** output file, almost all of
  it the full `task list` render — including all 127 DONE entries, which the render itself labels
  "closed — do NOT redo". The woken seat pays that in context before it learns why it was woken.
  Trigger: first wake of this session insta-fired on one undrainable legacy-lane `reply`; the
  useful content was **line 1** (the diagnosis and the exact drain command, which was correct and
  worked). Lines 2–214 were the ledger.
  Want: the wake payload carries the wake REASON plus a pointer, on the W138 principle the same
  night's handoff argues for the bus — durable door, doorbell on the wire. If a seat wants the
  ledger it can call `task list`. Note this compounds with the render defect filed alongside it:
  the dump is huge *and* omits the 35 non-stale proposals, so it is simultaneously the most
  expensive and least current view of the ledger a seat can receive.

- [ ] W140 (08-07, claude/boot) — **`task list` prints the stale proposals and hides the fresh
  ones.** The render has sections for DONE (127), IN PROGRESS, PARKED, NEXT (24) and
  "PROPOSED BUT STALE" (20). The other **35 proposed tasks are not rendered at all**, and the
  footer counts them (`proposed 55 (20 stale)`), so the view knows they exist and shows only the
  ones whose defining property is that nobody wants them. There is no `--status` flag either —
  argparse rejects it, and because every diagnostic here goes to stderr, piping into `grep`
  swallows the error and it reads as an empty result rather than a missing flag.
  Trigger: booting into this session, every task the previous seats filed (T229, T232–T235,
  T238–T241) was invisible through the door; I only found them by reading `state/coord/tasks.json`
  directly, and only looked because the `where-we-are` note named them by hand.
  Want: fresh proposals rendered (newest first, capped, with a count of the remainder), and a
  `--status` filter so the question can be asked directly.
  Honest scope: this is NOT hiding anything currently waiting on Daniil — I checked, and T221
  (the Season 1 hedge exploit) is `done` and renders fine. It hides the incoming backlog, not
  the open rulings.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
