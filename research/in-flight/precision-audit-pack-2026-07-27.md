# RECALL PRECISION AUDIT -- blind labelling pack

For each SURFACED item, judge it against THE ACTION ACTUALLY TAKEN (not the query text):
  on   = this item was on-point for that action
  off  = it was not
  skip = you cannot tell (skip is NOT 'off' -- unlabelled is not negative)

Then, per case, name any lesson that SHOULD have surfaced and did not (the recall arm).
Reply as: <case>:<slot> on|off|skip   and   MISS <case> <source-id or description>

## case 1  [path]
ACTION: e:\ai-setup\tests\test_filestore_durability.py
  1:a  learn:experiment:narrative_filestore_vs_redis_wrongtype
        Any code touching a foreign namespace must use that namespace's real Redis type (hset/hgetall here); add a test that stores the record as a HASH (not a string) so FileStore cannot mask the type mismatch

## case 2  [command]
ACTION: cd /e/ai-setup && sleep 12 2>/dev/null || true; echo "=== daemon output ===" && head -12 "c:/users/l5/appdata/local/temp/claude/c--users-l5/5c038e5a-dc28-445c-a302-0805dbbb758e/tasks/byb84cihi.output" 2>/dev/null; echo ""; echo "=== the test: does kimi answer out-of-band? ===" && py -c " from core.c
  2:a  learn:experiment:wake_seat_name_keyed_concurrent_sessions
        Use when a background watcher/daemon dies silently (exit 1, no output, cleanup artifact gone) on a box that can run concurrent sessions of the same agent, before blaming the script or transient infra: (1) check for a concurrent same-name se

## case 3  [command]
ACTION: cd /e/ai-setup && py agent_cli.py events --get 3f1e8659cb 2>&1 | head -80
  3:a  learn:experiment:doom_primitives_ui_design
        Use when building or debugging interactive UIs that receive high-frequency events: the renderer should serve the user's experience, not be a slave to the event stream. Apply fixed-timestep batching FIRST (it's 15 lines and fixes typing stut
  3:b  learn:experiment:spine_v2_reevaluation
        Wave 1 hardening V1-V5 (time-index events, word-boundary matching, clamp confidence finite[0,1], normalize tz at boundary, health counters) FIRST; Wave 2 V6-V9 capability (theme discovery, embedding router, weak-supervision label model, exe
  3:c  learn:experiment:span_boundary_hygiene
        Use when deriving triggers/drafts/counts for spans delimited by boundary-marker events: (1) the marker shares the next span's start timestamp, so filter markers OUT of content (keep them in provenance), and (2) prefer per-item cached routin

## case 4  [command]
ACTION: cd /e/ai-setup && py agent_cli.py boot claude --task "fresh seat: continue the arc" 2>&1 | grep -ie "ground first|next-focus|directive|handoff|where-we-are" | head -6
  4:a  learn:experiment:research:web:org_amnesia_decay_modes
        Map our curation layer onto the amnesia decay modes explicitly: our curator bench/unbench targets DECAY (lessons that stopped being true); our audit/VERIFIED-INFER-GUESS targets MISLABELING; but DISCONTINUITY (the fresh-boot stance gap, my
  4:b  learn:experiment:visible_todo_requires_approved_task
        Use when a human asks to add a visible todo, before stopping after task propose: fresh PROPOSED entries are durable but hidden from task list. If and only if the human explicitly authorizes the todo, approve it, leave it unclaimed when sequ
  4:c  learn:experiment:research:web:goodhart_multimetric_gaming_balance
        Multiple metrics do NOT automatically solve Goodhart — an optimizer that must satisfy N proxies finds the corner that games all N at once (the intersection of their loopholes), and N proxies with no gauge of the tension is an unaccountable

## case 5  [command]
ACTION: cd /e/ai-setup && py agent_cli.py events --get event:events:raw:1784986740846-0 2>&1 | tail -c 4500
  5:a  learn:experiment:modern_doom_idtech_ui_primitives
        Use when designing interactive UIs that handle bursty event streams. The core philosophy: THE MAIN THREAD SHALL NEVER WAIT. The typing cursor is the player's crosshair -- if anything makes it stutter, the architecture is wrong, not "a littl
  5:b  learn:experiment:Prevent double-promotion by stamping provenance both directions
        Rate-limit consolidation three ways: salience threshold + per-run cap + persistent dedup. And make hooks that emit a Beat stamp the beat id back onto the raw event so the promoter can see it's already consolidated

## case 6  [path]
ACTION: e:\ai-setup\docs\filestore-coherence-design-2026-07.md
  6:a  learn:experiment:narrative_memory_prior_art
        Design aligns with the frontier. Sources: arxiv 2304.03442, 2501.13956, 2502.12110, 2310.08560, 2601.07582, 2505.24575, 2603.11768. See docs/narrative-spine-plan.md section 10

## case 7  [command]
ACTION: cd /e/ai-setup && grep -n "class filestore" -a 6 core/foundation/store.py | head -20 && echo "---- write path ----" && grep -n "def set\|def get\|\.tmp\|os.replace\|json.dump\|def _flush\|def _load" core/foundation/store.py | head -30
  7:a  learn:experiment:research:web:rag_eval_ragas_recall_precision_faithfulness
        Our store needs the RAGAS triple, not just firing-counts. The W54 gauge measures injection VOLUME (how often a family fires) — that is neither recall nor precision. Context RECALL would catch the starved-index class automatically (we'd see

## case 8  [command]
ACTION: cd /e/ai-setup && echo "=== pretooluse hook via pyw (bash payload) ===" && echo '{"session_id":"testsess","tool_name":"bash","tool_input":{"command":"py -m pytest -q"}}' | pyw e:/ai-setup/scripts/hooks/claude_pretooluse.py; echo "[exit=$?]" echo "" echo "=== trace hook via pyw ===" && echo '{"sessio
  8:a  learn:experiment:hook_matchers_hot_reload
        Fix hook-coverage gaps live and verify in-session: edit matcher, run one in-scope call, check tempdir akashic_recall for the artifact. Never defer a payload-fixture pin to next session -- capture-and-pin immediately while the context is loa
  8:b  learn:experiment:recall_at_action_ergonomics
        Remaining recall polish (optional): (1) a SessionStart hook to pre-warm the cache so even the first edit is instant; (2) best-effort prune of old per-session seen files + the cache; (3) re-enable Bash recall now that anti-repeat exists (it
  8:c  learn:experiment:claude_trace_parity_via_hook
        Use when giving a hook-driven (non-runner) agent live trace parity, before trying to surface its thinking: emit tool-call traces from a broad-matcher PreToolUse hook (Bash|PowerShell|Read|... -- PowerShell+read tools have NO guard hook othe

## case 9  [path]
ACTION: e:\ai-setup\tests\test_w54_injections_by_family.py
  9:a  learn:experiment:round2_taxonomy_counter_2026-07-21
        Use the two-axis taxonomy (function × altitude) when filing belt entries. A verb's family declares its FUNCTION; its altitude is implicit in which layer it touches. At belt-render time, group by function first, then by altitude within funct

## case 10  [path]
ACTION: e:\ai-setup\tests\test_precision_audit.py
  10:a  learn:experiment:ranking_feedback_inc1_pull
        next: the friction-audit roadmap's remaining quick-wins (auto-boot at SessionStart, turn-start bus-sync hook, identity fail-closed) or the retrieval-critic Tier 1 minimal slice
  10:b  learn:experiment:recall_dissent_slice3_precision
        An on-topic anti-pattern != a contradiction of a thesis; topic-adjacency conflates with stance. Precision-first: surface nothing you cannot verify. NEXT (measurement-first): build eval datasets for action-instantiates-anti-pattern + genuine
  10:c  learn:experiment:recall_dissent_slice01
        Precision-first + silent-when-starved is correct: the binding constraint is corpus content, not the reader. Next lever = Slice 2 (write-side capture of anti_patterns / contradicts-links); biggest risk = adoption. Defer semantic-conflict rec

## case 11  [command]
ACTION: cd /e/ai-setup && echo "=== curation machinery that exists ===" && for v in recall-curate triage graduate tag-anti-pattern; do printf "%-20s " "$v"; py agent_cli.py $v --help 2>&1 | head -2 | tail -1 | cut -c1-90; done
  11:a  learn:experiment:intelligence_roadmap_and_spine1
        Next executable: FAITH-1 = lift chronicler._compute_metrics into core/primitives/faithfulness.py, CHARACTERIZE its false-positive rate on the real corpus, wire via Distiller(critic=) OBSERVATIONAL first then enforce; then FC-01 curate.py ga

## case 12  [command]
ACTION: cd /e/ai-setup && git add readme.md docs/wishlist.md && git commit -f - <<'eof' readme redesign: lead with the metric we caught lying rewritten as a fleet round -- deepseek, kimi and claude each filed a position fenced from the others, then a second round on the synthesis. 270 -> 229 lines. the page
  12:a  learn:experiment:git_history_rewritten_balanced7
        CRITICAL: the rewrite CHANGED EVERY COMMIT SHA. Any SHA recorded in lessons/memory/docs BEFORE this (e.g. FAITH-1 6b81e9f, SPINE-1 aaa01cc, recall-at 31a1b67, deploy 17523d3) is now DANGLING -- find those commits by message/content, not the
  12:b  learn:experiment:track_inference_context_switch_research
        Build TrackRouter tiered: Tier0 heuristic (commit repo/dir + task-keyword + persist-until-switch), Tier1 embeddings via Ranker relevance_fn seam (per-track centroid, nearest-assign, novelty->new track, drift->switch, unsupervised), Tier2 LL

## case 13  [command]
ACTION: cd /e/ai-setup && echo "=== test_lost_update_is_prevented ===" && sed -n '20,56p' tests/test_store_cas.py && echo "" && echo "=== filestore.cas (line ~512) ===" && sed -n '505,535p' core/foundation/store.py
  13:a  learn:experiment:filestore_coherence_hole_reproduced_66pct_loss
        Do not conflate them. (1) The lost-update hole is the live one and it is worse than 'writes vanish silently' conveys -- at 3 concurrent processes it loses two thirds of writes, and this is the store backing the knowledge substrate. RB-8 CAS
  13:b  learn:experiment:spine_v6_theme_discovery
        When an ablation gate exists, MEASURE before committing a shape -- the obvious approach (embeddings replace keywords) lost; hybrid won. Short exemplar phrases beat one long seed phrase for short-text matching. Keep write paths deterministic

## case 14  [command]
ACTION: cd /e/ai-setup && py scripts/bifrost_runner_deepseek.py --help 2>&1 | head -30
  14:a  learn:experiment:gemini_web_invisible_mode
        Default invisible. --headed for debug/login only. Don't run CLI gemini_web while bifrost_runner holds profile.
  14:b  learn:experiment:gemini_web_short_response_fix
        Default runner to --provider auto (web-first). User runs bifrost_runner_web.bat to keep Gemini live on the bus without API keys.
  14:c  learn:experiment:runner_guarded_write_leaks_locks
        fold into T048 build (his harness): runner releases its path-locks when the reply is sent (task end = lock end, matching T026 ack semantics); until then, expect unlock-before-mirror on any deepseek-written file whose task is complete -- ver

## case 15  [command]
ACTION: cd /e/ai-setup && bifrost_wake_lane=work py scripts/bifrost_wake.py --agent claude --session 424404de-a549-4c2b-8051-c9233589bbe3
  15:a  learn:experiment:wake_local_cursor_history_replay
        do not patch the watcher for history-replay; the honest fix is a session-scoped read cursor owned by T095 mailbox-over-the-log / T106-A1 bifrost_await; meanwhile expect 2-3 insta-fire arms on a fresh seat and let the sidecar converge

## case 16  [command]
ACTION: cd /e/ai-setup && py agent_cli.py learn claude --experiment failure_count_is_a_function_of_which_tree_you_run_in --tried "d (the honest ci split) needs a failure list. the handoff asserted 31 failures. ran the suite three ways on the same commit 31aafaa: (1) my working tree, (2) a clean clone via gi
  16:a  learn:experiment:research:web:algorithmic_collusion_multiagent_equilibrium
        For Daniel's multi-gradient design: independent OBJECTIVES are not enough. The gradients must optimize for signals generated by INDEPENDENT processes, or the ensemble finds the collusive equilibrium where each gradient's optimum is reached
  16:b  learn:experiment:research:web:gwt_hub_bottleneck_broadcast_failure
        For the fleet's integration layer: the danger is a SINGLE hub that both selects and broadcasts, because its selection bias becomes every module's input. claude-as-sole-integrator homogenises by discarding — each round, the frames claude doe
  16:c  learn:experiment:silent_inline_script_parse_failure_diagnosis
        when an inline-script page renders chrome but the feed is dead AND the console is silent: page-load parse errors fire BEFORE console attach, so absence of errors proves nothing. Probe order: (1) network log missing the feed/SSE request = sc

## case 17  [path]
ACTION: e:\ai-setup\core\comm\storm_detect.py
  17:a  learn:experiment:control-pause-clobbers-preexisting-pause
        Any automated pause-caller: was_paused = control.is_paused() before pausing; resume() only if not was_paused. Applied as amendment K2 to the S0 storm auto-clear ceremony (verdict: research/reviewed/kimi-storm-clear-second-observer-2026-07-2

## case 18  [command]
ACTION: cd /e/ai-setup && py agent_cli.py bifrost-send -h
  18:a  learn:experiment:p2_auto_chunk_intake_doors
        When adding a new bus send door, just call bus.send() or bus.broadcast() — oversize bodies auto-fragment, consumers auto-reassemble, nothing to wire. The explicit allow_frag=False refusal path is tested and stays alive as an escape hatch. F

## case 19  [command]
ACTION: cd "e:/ai-setup" && bifrost_wake_lane=work py scripts/bifrost_wake.py --agent claude --session cf1ebd7e-e32b-4412-b050-71f4fd8f9aff
  19:a  learn:experiment:same_token_twin_reentrant_consumer_seat
        Use when a per-agent coordination primitive (consumer seat, runner lock, wake seat) derives holder identity from an INHERITED env token (CLAUDE_CODE_SESSION_ID), before trusting it to fence twins: same token from different PIDs is RE-ENTRAN
  19:b  learn:experiment:kimi_phase1_cannot_arm_wake_watcher
        Use when a no-exec phase-1 seat gets the stop-hook wake-watcher re-launch bounce, before burning retries on launch forms: every background long-lived launch is allowlist-denied by design -- attempt the prescribed form ONCE for the record, t
  19:c  learn:experiment:stop_hook_wake_vs_allowlist_loop
        Use when a stop hook demands a command outside the repo allowlist on a supervised non-claude seat, before re-issuing per cycle: issue the exact command ONCE (maybe twice if approval may have landed), then if still gated, state blocked-on-hu

## case 20  [command]
ACTION: cd /e/ai-setup && py agent_cli.py events --get event:events:raw:1785014615425-0 2>&1 | head -50
  20:a  learn:experiment:windows_ctrl_break_requires_new_process_group
        Use when a Windows test sends CTRL_BREAK_EVENT, before calling Popen.send_signal: create the target with CREATE_NEW_PROCESS_GROUP and pin that an outer same-console sentinel remains alive while only the target group exits. Don't send consol
  20:b  learn:experiment:spine_v2_reevaluation
        Wave 1 hardening V1-V5 (time-index events, word-boundary matching, clamp confidence finite[0,1], normalize tz at boundary, health counters) FIRST; Wave 2 V6-V9 capability (theme discovery, embedding router, weak-supervision label model, exe
  20:c  learn:experiment:span_boundary_hygiene
        Use when deriving triggers/drafts/counts for spans delimited by boundary-marker events: (1) the marker shares the next span's start timestamp, so filter markers OUT of content (keep them in provenance), and (2) prefer per-item cached routin

## case 21  [path]
ACTION: e:\ai-setup\docs\wishlist.md
  21:a  learn:experiment:semantic_documentation_update_strategy
        Update all remaining documentation files to use semantic naming style. Use verb_noun_purpose pattern consistently. Include 'Semantic Relationship' sections in all major docs.

## case 22  [path]
ACTION: e:\ai-setup\scripts\checkers\check_door_parity.py
  22:a  learn:experiment:recall_dissent_slice2_capture
        A write door must OFFER a field or it stays empty (0 anti-patterns came from a missing flag, not agent laziness). Auto-draft the NAME to remove the naming cost and hand back a ready-to-run command (a cue needs a pre-filled payload). Deferre
  22:b  learn:experiment:bifrost_pull_session_hygiene
        A slice isn't done until it's mirrored (scripts/mirror.py commit+push) AND the decision is a lesson (+ snapshot_knowledge for data). Do NOT rely on docs/memory to enforce this -- agents skip docs (Cursor wrote the rule then broke it). Enfor
  22:c  learn:experiment:architecture_review_2026_06_28
        P0 = set AKASHIC_AGENT_ID at the door + make hooks fail-closed-with-teaching. Then: route contended writes through Store.update_atomic (CAS has 0 callers); kill the dead comm stack; archive stale root docs + flip check_doc_freshness to an a

## case 23  [path]
ACTION: e:\ai-setup\tests\test_corpus_gap_honesty.py
  23:a  learn:experiment:readme_directory_pointer_fails_open
        Use when migrating a doc corpus and re-pointing references, before declaring the sweep complete: file-path references fail CLOSED (404, visible) but DIRECTORY references fail OPEN -- they keep resolving while their contents change underneat
  23:b  learn:experiment:starved_index_hides_behind_passing_spotchecks
        Use when a search over a store returns suspiciously few results, BEFORE concluding the corpus is thin: never validate a search path by fetching a KNOWN key -- a by-name spot-check exercises the record lookup, not the index, and will pass wh
  23:c  learn:experiment:empirical_keyspace_census_before_roster_design
        Use when designing any allowlist/filter over a data corpus: run the EMPIRICAL census FIRST — `check_drift()` or equivalent — before writing a single line of the allowlist. The source-code census tells you what families exist; the empirical

## case 24  [command]
ACTION: cd /e/ai-setup && py agent_cli.py bifrost-send claude --to deepseek --kind question --text-file "c:/users/l5/appdata/local/temp/claude/c--users-l5/7072fd7f-0866-4ddc-a1ac-f3bcf8378597/scratchpad/ask-deepseek-leadership.md" 2>&1 | tail -2 && py agent_cli.py bifrost-send claude --to kimi --kind questi
  24:a  learn:experiment:deepseek_empty_reply_size_ceiling
        Asks to deepseek: keep the body under ~2.5KB, bullets, one question per message when possible; on an empty-reply bounce do ONE compact re-ask (this is now a recovery-catalog entry candidate). Institutional receipt: P-S1-5 verified live by t

## case 25  [command]
ACTION: cd /e/ai-setup && py agent_cli.py doc --help 2>&1 | head -25
  25:a  learn:experiment:gate_exit_codes_never_piped
        Use when chaining anything off a test/gate command: NEVER pipe the gate (| tail/| head make && meaningless); run the gate bare, format after; and never claim GREEN in a message composed before the gate actually passed
  25:b  learn:experiment:knowledge_boot_stale_directive
        Use when an agent boots and receives a directive from knowledge_boot, before acting on it: cross-check the directive's cited commit/state against HEAD. If the directive says "fixes pending" but the cited commit is an ancestor of HEAD, the d
  25:c  learn:experiment:powershell_head_pipe_kills_runner
        Use when launching any long-running process (runner/daemon/server) from PowerShell, before piping its output: never through a head-limited pipe (Select-Object -First N kills the child at N lines). Run it bare with output to a file/task capt

## case 26  [path]
ACTION: e:\ai-setup\scripts\bifrost_daemon.py
  26:a  learn:experiment:intelligence_roadmap_and_spine1
        Next executable: FAITH-1 = lift chronicler._compute_metrics into core/primitives/faithfulness.py, CHARACTERIZE its false-positive rate on the real corpus, wire via Distiller(critic=) OBSERVATIONAL first then enforce; then FC-01 curate.py ga
  26:b  learn:experiment:crash_path_review_needs_crash_injection_matrix
        Use when reviewing supervisor/watchdog/daemon/kill/terminate/taskkill/TerminateProcess/subprocess/Popen/process-tree/lifecycle/concurrency/race code, BEFORE issuing SHIP or any correctness verdict: a static reading / design-conformance pass
  26:c  learn:experiment:wake_seat_name_keyed_concurrent_sessions
        Use when a background watcher/daemon dies silently (exit 1, no output, cleanup artifact gone) on a box that can run concurrent sessions of the same agent, before blaming the script or transient infra: (1) check for a concurrent same-name se

## case 27  [command]
ACTION: cd /e/ai-setup && py scripts/bifrost_runner_kimi.py --help 2>&1 | head -30
  27:a  learn:experiment:gemini_web_session_arc
        Use bifrost_runner_web.bat for live gemini on bus. AI Mode needs headed (default). Stack cheat sheet: boot=load context, learn=lessons, log=milestone beats, handoff=session end, story --chronicle=readable narrative.
  27:b  learn:experiment:bifrost_runner_backlog_skip
        Use when a Bifrost runner (or any cursor-advancing bus consumer) starts with a backlog already queued, before trusting delivery: the startup wake can batch-advance the cursor while handing only the oldest message to the model - later items

## case 28  [command]
ACTION: cd /e/ai-setup && py agent_cli.py bifrost-send --help 2>&1 | head -40
  28:a  learn:experiment:bifrost_send_always_text_file
        Unconditional rule, no length judgment call: EVERY bifrost-send body goes through --text-file unless it is a single short flagless sentence. Write scratch file, send, done. Judging 'this one looks safe' is the failure mode itself
  28:b  learn:experiment:conductor_brief_intent_law
        Use when sending any brief, build order, or charter to a seat (bifrost-send, launcher briefs), before composing: open with INTENT two levels up (Daniel's words verbatim), state done-looks-like, list REAL constraints only, leave the method t
  28:c  learn:experiment:bifrost_send_supported_flags
        Use when sending Bifrost mail through agent_cli, before copying MCP-style metadata into the CLI: inspect bifrost-send --help and use only its exposed flags; this build has no --subject or --priority. Don't assume transport metadata options

## case 29  [command]
ACTION: cd /e/ai-setup && py agent_cli.py status 2>&1 | head -40
  29:a  learn:experiment:terminal_outcome_receipt_defaults
        Use when multiple durable writers can independently make a job terminal, before returning the merged status: make every authoritative terminal branch populate required negative facts explicitly; do not inherit or wait for another writer's r
  29:b  learn:experiment:status_line_lies_cost_diagnoses
        Use when any status line reports that nothing happened, BEFORE diagnosing the mechanism underneath it: verify the claim with an independent read (a non-consuming peek, a count, the cursor itself). A renderer's summary of its own side effect
  29:c  learn:experiment:hud_fingerprint_diff_pattern
        Use when adding any new live-status display to a periodically-polled UI: always fingerprint the data first (JSON.stringify + compare to last-known). Build DOM only on actual state change. Use data- attributes as stable identity keys for dif

## case 30  [command]
ACTION: set-location e:\ai-setup; py agent_cli.py bifrost-send claude --to claude --to-incarnation 7072fd7f --kind reply --expect-reply-within 0 --text-file "c:\users\l5\appdata\local\temp\claude\c--users-l5\a4fa8f8d-3876-4099-a464-9fa87d1082cf\scratchpad\twin-concession.txt"
  30:a  learn:experiment:conductor_brief_intent_law
        Use when sending any brief, build order, or charter to a seat (bifrost-send, launcher briefs), before composing: open with INTENT two levels up (Daniel's words verbatim), state done-looks-like, list REAL constraints only, leave the method t
