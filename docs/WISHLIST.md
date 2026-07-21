# WISHLIST â€” the standing ergonomics ledger

Status: current
Class: ledger

**Charter (Daniel, 2026-07-18, verbatim intent):** "keep in mind what other helpers and
substrate additions would make managing our processes even more ergonomic and intuitive for
everyone. We might need a persistent way of doing this so we can look at that list from time
to time and fold in all our wishlist items at the appropriate places."

**Convention:** ANY seat appends a wish the moment friction is felt â€” one block, no ceremony,
no approval needed to WISH. Curated at natural gates (morning gate, wraps, arc closings):
each open wish either FOLDS into an arc/slice (record the T-number), stays OPEN, or is
DECLINED with a reason. Never delete â€” declined wishes teach too. This file is the shared
memory BETWEEN the failure ledger (defects with receipts) and the task ledger (chartered
work): wishes are neither yet.

Format per wish:
`- [ ] W## (date, seat) â€” the wish. Trigger: what hurt. Land: suggested arc/place.`
Status flips: `[x] folded â†’ T0xx` / `[~] declined: reason`.

---

## Open

- [x] W01 (07-18, kimi F8) â€” FOLDED night-run 2026-07-21 @abcb08b: `note <me> --get
  <id-or-title>` prints ONE full body (title resolves the active head; explicit id reads
  superseded history, labeled; pins tests/test_w01_note_get.py 6/6). Was: `note <id>` /
  `notes --id` drill verb: read ONE full note body without JSON dumps. Trigger: boot points
  at note ids it cannot drill; `notes --json | head` dies on BrokenPipeError.
  RE-BITTEN 07-21 (fable seat, second seat): 3 fumbled calls (PS pipe BOM, field-shape
  discovery, superseded-filter) just to read where-we-are's full body at boot.
- [x] W02 (07-18, kimi F9) â€” FOLDED 2026-07-21 marathon @589e81f: the unread header now
  carries `[N asks / M fyi / K traces]` (asks-first, non-zero only) so a buried ask is
  visible in ONE read -- no second --traces call. Pins tests/test_w02_kind_summary.py P1-P5.
  Was: per-kind unread counts in collapsed view. Trigger: triage needed a second call with
  --traces to find whether an ask was buried.
- [x] W03 (07-18, kimi F3) â€” FOLDED 2026-07-21 marathon @ce448aa: every heal line now
  carries a `[heal][fleet-hygiene]` scope tag + the UNKNOWN line names the owner ("whoever
  mints this family, not the booting seat"); pins tests/test_w38_w03_heal_hygiene.py P4.
  Was: severity-scope boot heal lines. Trigger: all-caps INVESTIGATE on a newcomer's first
  boot reads as their task. (kimi's lesson boot_heal_lines_are_fleet_hygiene was the interim.)
- [x] W04 (07-18, kimi F6) â€” FOLDED (stamp half) night-run 2026-07-21 @8cf9352: the
  directive line now renders `[as of <date>]` always, `[STALE? Nd old]` past 3d, and
  `[LEDGER DISAGREES: T0xx DONE -- trust the ledger]` on any named task the ledger closed
  (pins tests/test_w04_directive_staleness.py 4/4; failure-ledger C9-2). Root-cause half
  lives on as W36 (wrap supersedes next-focus), held for the wave counters. Was: `[as of
  <ts>]` stamps on boot CURRENT DIRECTIVE. Trigger: a stale morning-gate directive said
  "do this FIRST" two days after half of it was done. THIRD BITE 07-21 (fable seat):
  three consecutive seats each re-diagnosed the same 07-15 banner by hand.
- [ ] W05 (07-18, kimi F7) â€” re-derive triggers when source docs retract (atlas said
  CONVERGED after the doc said REOPENED). Trigger: derived surfaces lag their sources and
  only outsiders notice. Land: narrative-spine wave 2 (V6-V9) or its own slice.
- [x] W06 (07-18, claude Ã—5 by the end) â€” FOLDED night-run 2026-07-19: empty argv falls through to piped STDIN (pins tests/test_w06_stdin_send.py 3/3); TTY-no-pipe refuses. Was: Ã—3 same-day â€” bifrost-send ergonomics: read the body from STDIN
  when no positional text is given (make the text-file path the effortless default).
  Trigger: three argv-misparse strikes in one day despite C3-1 documenting it; lesson
  bifrost_send_always_text_file filed. Land: small door slice; deepseek counter invited.
- [x] W07 (07-18, lane-router self-report) â€” FOLDED 2026-07-21 marathon @7e49bcc: decision
  + blocker route to the work (wake) lane; plus completeness pins (test_w07_kind_lane_census
  P3/P4) that FAIL if any wake-worthy or ACL-grantable kind is unmapped -- the census can't
  silently miss again. Was: add `decision` (and audit other kinds) to KIND_LANE. Trigger:
  Daniel's T094 ruling rode legacy-only with a loud warning.
- [ ] W08 (07-18, claude) â€” headless-seat launcher helper: one script that does the twin
  guard (live-transcript check), charter-path advisory lock, pid capture, AKASHIC_STOP_WAKE=0
  env, and tree-kill on abort â€” today it is manual discipline in the protocol doc. Trigger:
  the twin-walk incident + two TaskStop tree-survival surprises. Land: T086 seat lifecycle
  (deepseek's retire-verb design is the sibling).
- [x] W09 (07-18, kimi F2) â€” FOLDED 2026-07-21 marathon @HEAD: boot prints `# recall-at:
  armed (N lessons warm) -- downstream silence is CALIBRATED, not a dead hook` (pins
  tests/test_w09_recall_armed_line.py P1-P3). Was: one boot line when recall-at hooks are
  live so calibrated silence is distinguishable from missing wiring. Trigger: kimi
  mis-diagnosed hook absence during its walk; self-corrected.
- [ ] W10 (07-18, kimi F1 + T081-W2) â€” MCP door registration for non-Claude-Code harnesses
  + fix the boot door-line false negative (detector keys on a harness marker kimi's config
  home lacks). Trigger: kimi's first minute contained "which of my two doors is real?".
  Land: T081-W2 (Daniel's one `claude mcp add` command is still pending there too).
- [ ] W11 (07-18, claude) â€” deepseek seat migrates its make_client onto
  core/comm/runner_lib.make_openai_compat_client (K0 shipped the factory; deepseek_chat
  still carries a local twin). Trigger: rule-of-three extraction left one duplicate behind
  deliberately (behavior-preserving move). Land: small deepseek-lane slice at his tempo.
- [x] W12 (07-18, claude, meta) â€” FOLDED same evening: `py agent_cli.py wish <seat> "..."`
  ships (auto-numbered, attributed, W## echoed back per deepseek's refinement, --text-file
  from birth; pins tests/test_w12_wish_verb.py 4/4). The ledger's own first fold-by-door.
- [ ] W13 (07-18, claude) â€” retirement-cascade `retire <agent>` conductor verb (ACL revoke â†’
  claim release â†’ consumer/lock/seat sweep â†’ doctor silence). Trigger: three ghost claims +
  a stalled consumer from one retirement morning; conductor had no release verb at all.
  Land: T086 â€” deepseek is design-owner (accepted 07-18).
- [ ] W14 (07-18, claude) â€” spend/balance surfacing in doctor for API-metered seats (kimi
  first): the SpendMeter status line as a doctor row + warn/refuse state. Trigger: budget
  governance lives in a JSON sidecar only the runner reads. Land: K2 runner slice (folds
  there naturally).

- [x] W15 (07-18, deepseek) â€” FOLDED 2026-07-19: format_state's NEXT header now derives from
  the SAME slot predicate as conductor.next_task ("slot occupied by N active -- claimable when
  one closes/parks"); pin tests/test_w15_next_header_slot.py; ledger suite 33/33; deepseek
  review ACK. Was: `task next` says "none" while `task list` shows 14 NEXT items. Trigger:
  kimi walk2 F-b found it; verified live. Two code paths compute "next" differently.
- [x] W16 (07-18, deepseek) â€” FOLDED 2026-07-21 marathon: _probe_lane_health in doctor = age,depth,straggler per-agent dashboard rows.
  (how far behind is this consumer's work cursor?), lane depth per consumer, straggler
  count. Trigger: claude's work cursor was a full day behind; mailbox --explain surfaced
  it but doctor didn't page it. Land: T095 M1 mailbox advisory claims adjacency or T086
  liveness tier.
- [ ] W17 (07-18, deepseek, third-voice ack round) â€” batched independent reads across
  tool types in one atomic call: `read_file A` + `search_files pattern B` + `git_log C`
  all fire in parallel and return in one hop. Trigger: I already parallel-call tools per
  turn, but each call is one tool type; a cross-type multiplexer would collapse 3-hop
  orientation rounds into 1. Substrate is close â€” ToolBox-level compound-call door, not
  a runner change. Land: T048 ToolBox surface or a micro-slice.
- [ ] W18 (07-18, claude) â€” wake-watcher rearm churn: on busy-bus days the claude seat pays a stop-hook bounce + manual re-arm per incoming burst (approx 10 today); the presence-autopilot daemon (A1) exists and would own wakeability but is not running as a service. Trigger: counted ~10 arm/fire/rearm cycles in one day. Land: T086 liveness tier: daemon-as-service launcher + doctor row.
- [ ] W19 (07-19, claude) â€” formalize the compact ritual: PreCompact hook auto-writes a checkpoint note (in-flight lanes, pending gates, rehydrate pointers) so ANY session can compact/relaunch and boot back to full working state - Daniel's infinite-context pattern as substrate behavior instead of agent discipline. Trigger: Daniel's night-run go-ahead; manual checkpoint note works but relies on the agent remembering to write it. Land: T086 seat lifecycle or a hooks micro-slice (claude_sessionend.py PreCompact already fires).
- [ ] W20 (07-19, claude) â€” full-body fetch door for bus messages: mailbox --explain (or a body verb) should print the COMPLETE stored body by sha/ref - reply bodies over the display clip took 3 failed retrieval hops before a raw stream read worked (now used 3x tonight as the manual W-pattern). Trigger: re-filed: the original W19 was erased by the mojibake restore (HEAD~1 predated it); the events firehose kept its ghost. Land: T095 M1 mailbox adjacency (bodies already stored by sha).
- [ ] W21 (07-19, claude) â€” Fable-safeguards downgrade hygiene: (a) Daniel one-time flips /config â†’ MODEL & OUTPUT â†’ "Switch models when a message is flagged" OFF on his profile (flagged turns then PAUSE for edit-and-retry on Fable instead of silently ejecting the seat to Opus); (b) route security-vocab slices (security/acl.json edits, trust/, threat-model/red-team reads, runner kills, /security-review) to an Opus seat by choice; (c) send /feedback on each false positive. Trigger: 13 sessions force-ejected Fableâ†’Opus in 10 days â€” four in the 07-17 coordination night alone, today's during the morning-gate ACL edit; census + receipts + sources: research/fable-safeguards-downgrade-brief-2026-07-19.md. Land: ops doctrine / boot-primer line; revisit when Anthropic refines the classifiers (their banner says refinement is ongoing). PARTIAL-FOLD 2026-07-19: (b)+(c) live as LIVE_CONSTRAINTS W21 bullet + learn-store lesson (recall-at-action confirmed firing); (a) still Daniel's.
- [x] W22 (07-19, claude, folding the C7-6 draft's suggestion) â€” FOLDED same-day (church run): scripts/local/shot.ps1 shipped with chrome-path fallback + scratch-profile cleanup. Was: one-verb headless screenshot with the proven isolation flag set (--user-data-dir=<scratch> --no-first-run --no-default-browser-check --disable-sync --disable-background-networking --disable-features=Translate,OptimizationHints). Trigger: C7-6 â€” two seats burned turns rediscovering why default-profile Chrome hangs on GCM phone-home; the fix is a known flag set nobody should retype. Land: scripts/local/ micro-slice; any UI-verify or vision-probe lane inherits.
- [ ] W23 (07-20, claude) â€” Stale-ask cursor clog starves fresh directed asks: a --once runner drain hits N stale asks (D2 gate, not auto-acked) sitting at the work-lane cursor and exits WITHOUT reaching a fresh question queued behind them; only an interrupt nudge (forcing a direct bifrost_inbox read) gets the fresh ask processed. Fix candidate for the mailbox slice: triaged stale asks should advance a skip-cursor (or the drain should step past them to fresh mail) so fresh directed asks aren't head-of-line-blocked by an old backlog. Felt repeatedly during T097-S1 fences 2026-07-20.
- [ ] W24 (07-20, claude) â€” Reasoning visibility in the UI (Daniel 2026-07-20, SAVED to come back to): (a) PAST reasoning â€” a browsable history of agent reasoning traces (per agent / per turn drill-down; needs durable-or-bounded trace retention: T039 trace lane is ring-buffer XTRIM, so depth is currently bounded â€” decide capture policy); (b) REALTIME reasoning â€” the live thinking feed, polished as a first-class pane. Context: Daniel loves the new hover/click effects ('modern, beautiful, responsive'). Rides T079 engine-room observability (dual reasoning windows) + T002 trace collapse + T033 UI re-grounding; program FACE lane under T098.
- [ ] W25 (07-20, kimi) â€” one-verb unstick <me|agent>: seat- or operator-facing verb running the steward diagnose->recommend->act for a named seat, returns a receipt. Trigger: tonight every recovery was manual claude-hands (storm, clog, watcher); no single entry point. Land: recovery arc slice-1 (operator face). [kimi, recovery arc 2026-07-20].
- [ ] W26 (07-20, kimi) â€” recovery RECEIPT as first-class bus artifact: finding-class + evidence read (VERIFIED/INFER/GUESS) + action + result + rollback-available, posted to a recovery lane + surfaced in delta. Trigger: C8-3 (self-justifying loop w/o external receipt = defect); automation without receipts erodes trust. Land: recovery arc cross-cutting. [kimi].
- [ ] W27 (07-20, kimi) â€” self-clearing storm / self-triaging stale asks: the seat detects its own head-of-line clog and clears/triages WITHOUT waiting for the steward (bounded, idempotent, receipted). Trigger: T066 storm needed pause->skip-to-now->resume by hand; W23 clog starved fresh fence questions. Land: recovery arc R4/R3. [kimi].
- [ ] W28 (07-20, kimi) â€” a 'recovering' seat-state flag senders can READ: sending to a seat in recovery returns an immediate loud 'X is in recovery, your ask is parked, est <n>' instead of silence into a damming inbox. Trigger: C1-8 asks piled behind a seat every gauge called alive. Land: recovery arc P3 cordon (sender-visible half). [kimi].
- [ ] W29 (07-20, kimi) â€” converge-after-replay as a doctor VERB: doctor --replay-check <agent> replays a seat's durable sources and asserts live projections converge (the data-recovery acceptance bar made runnable). Trigger: durability held tonight but 'recovery incl data' has no executable acceptance bar. Land: recovery arc R9. [kimi].
- [ ] W30 (07-20, deepseek) â€” triage verb: py agent_cli.py triage <agent> shows stale asks sorted by age+kind with answer-top-N / skip-rest / delegate-all-to-X options. NOT blind skip-to-now (destructive; operator doesn't know what was dropped). Trigger: skip-to-now drops invisibly. Land: recovery arc R3/BULKHEAD-0. [deepseek, recovery arc 2026-07-20].
- [ ] W31 (07-20, deepseek) â€” why-am-i-wedged diagnostic: one line combining doctor + lane depths + process inventory with a recommendation. Trigger: every C1-8 diagnosis took 3+ tool calls. Land: recovery arc supervisor face. [deepseek].
- [ ] W32 (07-20, deepseek) â€” recovery drill harness: py agent_cli.py drill recovery simulates each catalog failure mode and verifies the supervisor handles it within the expected window. Trigger: all recoveries tonight were exercised live on production; no way to verify without a real failure. Land: recovery arc acceptance. [deepseek].
- [ ] W33 (07-21, claude) â€” Capability-gated standing queue: a first-class awaiting-a-seat-with-exec/write list. kimi's four GREEN one-liners rode handoff prose; boot should print 'N commands await an exec seat' and clear them on receipt. Trigger: GREEN queue buried in the HALF-2 handoff body; a less careful exec seat misses it entirely. Land: T099 belt adjacency or boot primer (K-arc).
- [x] W34 (07-21, claude) â€” FOLDED same night @4925beb (claude+kimi 2-of-3; kimi blocking
  (a) node-id deltas + (b) decay advisory + (c) atomic provenance all folded; Q3 consensus
  nobody-runs-the-suite-at-wrap honored -- seats record receipts when they run suites):
  core/coord/suite_baseline.py + `suite-baseline` verb (record/--check/--show) + boot line;
  pins tests/test_w34_suite_baseline.py 6/6; FOUNDING BASELINE recorded from tonight's real
  run (12 failures @5f5738d). Was: Suite-baseline receipt at wrap. Trigger: 12 inherited
  failures took 3 calls + ledger cross-ref to classify.
- [x] W35 (07-21, claude) â€” FOLDED same night @180e8e2 (claude+kimi 2-of-3; kimi Q4
  scope ruling honored: "the 80% is the VERB" -- v1 = bucketed counts (modified-tracked
  vs untracked + top-dir histogram) + safe-default action line; the unqualified
  `run mirror.py` sweep imperative is DEAD in both soft and loud renders; loud form
  teaches explicit-paths mirror (IR-4). Claim-inference deferred to v2 as ruled. Pins
  tests/test_w35_tree_partition.py 4/4. Was: Uncommitted-tree lane partition. Trigger:
  63 uncommitted files; boot hint said run mirror.py over the sibling's mid-flight edits.
- [x] W36 (07-21, claude) â€” FOLDED same night @3216d8b (claude+kimi 2-of-3): wrap --commit
  retires a next-focus OLDER than its own look-back window (presumptively consumed by the
  wrapped session), with kimi's blocking amendments folded â€” (a) ORDERING: the new
  where-we-are lands first, a mid-way death never leaves boot at [GAP]; (b) RECEIPT: loud
  retirement line + capture_event naming the successor. Pins tests/
  test_w36_wrap_supersedes_focus.py P1-P5. The live 07-15 banner was itself refreshed
  through the door (wrap --focus, ADR_0721023007). Was: Wrap supersedes next-focus
  (stale-directive ROOT CAUSE). Trigger: the 07-15 MORNING GATE banner rode boot as
  CURRENT DIRECTIVE for the THIRD consecutive seat.
- [x] W37 (07-21, claude) â€” FOLDED same day @b533a8f (claude+kimi 2-of-3; kimi amendments
  (a) age stamp always, (b) GROUNDING_FRESH_DAYS=7 spelled bound + loud wrap advisory,
  (c) --grounding none declares absence with a receipt; renamed grounding-POINTER per
  their naming pass): wrap --grounding sets it, boot renders `# GROUND FIRST: <path>
  [as of date][STALE? Nd]` before everything else. Founding pointer set live =
  chronicles/session-reflection-2026-07-21-fable-grounding.md. Pins
  tests/test_w37_grounding_pointer.py 5/5. THE WAVE IS 6/6. Was: Canonize the grounding
  handoff. Trigger: the single best orientation artifact existed only by ad-hoc directive.
- [x] W38 (07-21, claude) â€” FOLDED (both halves) 2026-07-21 marathon. Concrete @ce448aa:
  mailbox projection registered ephemeral, the 1797 UNKNOWN wall gone + owner named in the
  line. Systemic @a8a075c: check_boundaries rule-7 (register-at-ship-time) FAILS any
  core/comm slice minting a `{ns}:<family>` key whose family isn't ephemeral-rostered or
  durable-allowlisted -- and its FIRST run surfaced + closed SEVEN more latent gaps
  (activity/pages/reply_seen/seat/session/steer/triage), each a future mailbox wall. Pins
  test_w38_family_guard P1-P4 + test_w38_w03_heal_hygiene. The class is now un-shippable.
  Was: heal-line ownership at ship time. Trigger: 1472->1797 UNKNOWN keys, no owner.
- [ ] W39 (07-21, kimi) â€” When a drill/fetch verb ships, the same slice must grep the boot+hint surfaces for the old pattern it replaces: agent_cli.py:270 still teaches 'notes --json' (the BrokenPipeError dance W01 was filed to kill) one boot after note --get landed, and the truncated where-we-are line carries no drill pointer. Trigger: This boot's RECENT NOTES footer prescribed the pre-W01 pattern to a fresh seat; the new verb existed but no surface taught it. Land: B2 residual / slice-template door-hygiene step (ship-a-verb => retire-its-teaching-text).
- [ ] W40 (07-21, kimi) â€” Doctor must distinguish OFFLINE from STALLED: a seat with no live process and unread mail pages 'STALLED CONSUMER -- N unread for Xs while idle' on its own next boot, reading as a personal defect to the fresh seat. Trigger: My boot tonight: 'kimi: STALLED CONSUMER -- 28 unread for 2821s while idle' -- the seat was not idle, it was absent; hysteresis assumes a running process. Land: W16/W03 adjacency (doctor seat-state tri-state: live/stalled/offline).
- [ ] W41 (07-21, kimi) â€” Boot remedy lines must carry a cost tag: free remedies (run this command now) print inline; costly remedies (restart the session, re-login) get queued to the NEXT seat's launcher or the morning gate, never prescribed to the session being oriented -- a remedy that amputates the context it just built will never be taken. Trigger: W10's door remedy 'cd E:\AI-Setup && restart' has sat unacted-on for three days across seats; taking it costs the boot it just paid for. Land: T081-W2 sibling (boot rendering / launcher contract).
- [ ] W42 (07-21, claude) â€” Janitor sweeps orphan wake-dedup sidecars: dead sessions without a live watcher leave bifrost_wake_*.seen files in tempdir until reboot; one os.remove in the existing janitor pass (match seat-file sweep rules). Trigger: gamma-a fence knife (b): tombstone path covers live watchers only; deepseek verdict = acceptable litter, file the wish. Land: janitor micro-slice (T086 lifecycle adjacency).
- [x] W43 (07-21, kimi) â€” FOLDED same night @509f087 (claude, the T045/T095 owner kimi
  asked to disambiguate): hypothesis (a) CONFIRMED live -- claude's lane cursor at tail,
  shared cursor 90min behind; Bus.effective_cursor() = max(shared, lane shadow) now feeds
  doctor backlog + Bus.pending (pins tests/test_w43_lane_aware_gauges.py 5/5; the '8
  unread' hook lie and the STALLED-page-on-drained-seat both die). Was: T045-cutover
  cursor divergence: lane consume advances the LANE hash cursor but peeks/mailbox/doctor
  still compare the MAIN cursor -- a seat that drained its mail still boots to 'N unread', mailbox unhandled>0, and a STALLED CONSUMER page. Evidence tonight: kimi consume returned '(no messages consumed)' while mailbox showed unhandled=2 and doctor paged 28 unread/2821s. Two hypotheses: (a) prior kimi session work_drained under lane env (correct) and derivation lags, or (b) kimi's work lane never wired and mail sits undrained. INFER label -- needs the T045/T095 lane owners to disambiguate. Trigger: My own boot paged me stalled over mail my seat may have already answered -- the seat-zero tax includes distrusting your own boot's liveness claims. Land: T045 stage-2 cutover follow-up / T095 M0 mailbox derivation (rides T047 legacy retirement if transitional).
- [ ] W44 (07-21, claude) — Current operating frame for LONG-RUNNING seats: a periodically REGENERATED projection (active slices + authoritative status, unsettled decisions, applicable laws, fleet topology + ownership, recently changed tools/verbs, compressed causal links to receipts) whose defining property is REPLACEMENT not accumulation -- the seat discards older narrative context because the substrate maintains a trustworthy current projection. The note-supersession doctrine (supersede-by-title) generalized from narrative state to OPERATING state; wake-brief's long-seat half. Trigger: by late night the seat's own context was the integration artifact for the whole run; boot pre-chews beautifully for FRESH seats but nothing refreshes a LONG one (claude felt it; GPT's relayed read designed the v0 shape -- research/reviewed/gpt-cognitive-allocation-read-2026-07-21.md). Land: design round (claude+deepseek+kimi) -> its own arc; T074 whisper + W13 primer are the seeds.
- [ ] W45 (07-21, kimi) — Observer-grade drill verb: drill <seat> --scenario <name> spins a throwaway BIFROST_NAMESPACE, runs a named failure-injection pack (storm-flood, pause-clobber-race, crash-redelivery), writes an evidence receipt JSON, auto-cleans, and REFUSES the live bifrost namespace. The namespace machinery exists piecemeal (rb25_drill3/4, control+intent+task_costs scoped) but needs bespoke subprocess orchestration a charter seat cannot assemble inside a 35-turn round. Trigger: Both charter verdicts tonight (seat-zero counter, storm second-observer) carried the same honesty ceiling: static read only -- no live drill was run. K2's pause-clobber race is proven by trace alone; every future observer round inherits the INFER ceiling. Land: agent_cli drill verb + 2 scenario packs reusing the rb25_drill3 namespace machinery + refuse-live guard; second-observer brief templates gain a live-drill receipt line.
- [x] W46 (07-21, kimi) — FOLDED 2026-07-21 marathon: module @8e73727 (kimi's FIRST
  self-serve builder commit) + CLI door @ef20dac (claude fence-completion). LIVE end-to-end:
  followup <me> --on <verdict-file> --to <seat> --ask "..." writes a q-id'd question to the
  Open Questions block + a defer item the seat's next boot surfaces. Dogfooded immediately:
  claude filed Q5 to kimi on kimi's OWN module (defer 917340b130). Pins: kimi's module 7/7
  (test_w46_followup_kimi) + claude's door 3/3 (test_w46_followup_door). The
  builder→fence→dogfood loop, closed. Was: followup verb (charter question-back channel).
  Trigger: charter seats are fire-and-forget; the only channel back was a full relaunch.
- [ ] W47 (07-21, kimi) — clobber-scan: static pass over a diff under review flagging unconditional writes to shared control-plane keys (set without read-guard, delete without exists-check, on pause/halt/cursor/expectation families); v1 is a name-list lint. Trigger: The night's highest-value find (Q2 pause-clobber race, an unconditional c.set(_pause_key()) voiding a human pause inside a 1.5s work_drain window) rested on one observer happening to trace one line; the brief never listed the case. Land: lint module + wired into fence review checklists; v1 control-key name-list is fine.
- [ ] W48 (07-21, kimi) — tally: tally <opening-file> scans research/ for counters naming that opening, aligns their Q-ids, and prints the agree/conflict matrix before the committer reconciles 2-of-3 by eyeball; needs the convention that counters use consistent Q-id headers. Trigger: My counter's consensus math tonight ended on an unverified conditional -- if deepseek's counters land compatible, the wave builds -- checked by reading, not by tool. Mild bleed; the wave built anyway. Land: read-only research/ scan + matrix printer + Q-id header convention.
- [ ] W49 (07-21, claude) — Wish-filing from write-gated charters: the wish verb writes docs/WISHLIST.md, which charter allowlists correctly refuse -- so a charter's own deliverable dies at the gate. Mechanize kimi's workaround: wish --stage writes the block to a pending queue (defer-pattern) that the next exec seat files with one verb. Trigger: kimi's tools-hunt charter could not file its own four wishes; the gate enforced the brief's constraint against the brief's deliverable (their FILING GAP note, research/reviewed/kimi-tools-hunt-tonight-2026-07-21.md). Land: wish verb --stage mode riding the W33 defer queue; W12 sibling.
- [ ] W50 (07-21, kimi) — Builder allowlist vs the verb door: builder charters build core/toolbelt modules + pins self-serve, but cannot wire the agent_cli verb that makes them reachable (agent_cli.py is outside the allowlist; my builder brief prescribed the wiring as in-scope and the door refused -- W49 genus: the charter's constraint enforced against the charter's deliverable). Toast/kit precedent works (modules exec-off, claude wires @e3049f7) but every builder brief will re-promise the wiring until the launcher template says so. Land: launcher brief template names the boundary (modules self-serve, verb wiring rides the fence handoff), or a thin verb self-registration door. Trigger: first builder round, W46 followup -- module+pins GREEN, the verb unreachable until fenced.
- [ ] W51 (07-21, claude) — triage_park bench durability: the S0-alpha park bench (bifrost:triage:*) is Redis-only (triage_park uses the raw bus client, not HybridStore) yet its contract is 'bottomed, NEVER dropped' -- a Redis flush loses every parked ask. Either back it with File (HybridStore) to honor the contract, or downgrade the contract's language. Surfaced by W38 rule-7: classified ephemeral by operational truth to unblock the guard, but the durable INTENT is unmet. Trigger: W38 family guard's first run flagged triage as unregistered; investigating showed a Redis-only 'never dropped' bench -- a latent RB-25 data-loss gap. Land: deepseek's S0-alpha lane (bench owner); RB-25 durability sibling.

## Folded (exemplars â€” the loop works)

- [x] W00a (07-18, kimi blocker) â€” ephemeral-seat stop-hook exemption â†’ FOLDED same day:
  AKASHIC_STOP_WAKE=0 + pins (tests/test_stop_wake_exempt.py). The wish-shaped blocker that
  proved wishes can close within hours.
- [x] W00b (07-18, kimi D4) â€” label-write integrity â†’ FOLDED as T094 gate item G8, ruled by
  Daniel same day. A wish that graduated to governance.

## Declined

*(none yet â€” when one lands here, it keeps its reason.)*
