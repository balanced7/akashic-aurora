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

## Folded (exemplars — the loop works)

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
  (f6a96df -> b727096); history changed under you -- inspect: git log b727096..f6a96df`. That
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

*(W54/W55 were double-filed by two claude seats during the C2 audit collision — merged into
the numbered entries above, 2026-07-21; all content folded, nothing dropped.)*

## Declined

*(none yet — when one lands here, it keeps its reason.)*
