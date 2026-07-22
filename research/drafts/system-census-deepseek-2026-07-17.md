# System Census — deepseek census-taker seat — 2026-07-17

Status: EMPIRICAL. Every number carries a receipt (command + output from temp/census_timings.txt
or from the code's timeout/budget constants). "unmeasured" = no receipt obtainable from this seat.

---

## GROUP 1 — FOUNDATION + SUBSTRATE

### Store (core/foundation/store.py)

- **Purpose**: Key-value state primitive ("what IS the value of X?"). Three backends: FileStore
  (local JSON files, always available), RedisStore (Redis GET/SET on shared Redis), HybridStore
  (writes File-always + Redis-best-effort, reads Redis-first → File-fallback).
- **Doors**: Python import only. `from core.foundation.store import create_store; store =
  create_store(prefer_redis=True)` — returns the HybridStore by default.
- **Packets/lanes**: None. Pure storage.
- **Upstream dependencies**: `redis_connection.py` (fail-fast connect to localhost:16379).
  Nothing imports Store except the layers above it.
- **Downstream**: Everything. If Store dies, knowledge (learnings, notes, decisions), events,
  narrative beats, coordination state all lose persistence. FileStore survives Redis outage.
- **Measured**:
  - FileStore SET: **89.4ms** (receipt: `temp/census_timings.txt`, Store-File set). NOTE: first
    import of FileStore triggers module loading; subsequent ops would be faster.
  - FileStore GET: **1.0ms** (receipt: same file, Store-File get).
  - HybridStore Redis probe: **10.7ms** (same file, Store-Hybrid online — but the `online`
    attribute doesn't exist; this is the import time of `create_store`).
- **Known bottlenecks**: HybridStore `heal_report()` iterates ALL Redis keys (`store.keys("learn:*")`)
  and compares against File — O(N) in keyspace size. Called at boot time (agent_cli.py:196).
  At 7834 total keys (per `status --json`), this is fast (<50ms typically). At 100K+ keys, it
  would become the boot bottleneck. Failure ledger: C7-4 (MCP boot hang) — heal_report's Redis
  iteration was initially suspected, since disproven (root cause: subprocess stdout inheritance).
- **Timeouts/budgets**: No internal timeouts. Redis operations use the `redis` library's default
  socket timeout (configurable via `redis_connection.py`). FileStore has no timeout — local disk.

### Ledger (core/foundation/ledger.py)

- **Purpose**: Append-only event sequence primitive ("what HAPPENED, in order?"). Events are
  appended with an auto-incrementing cursor; consumers replay from a cursor. Three backends
  (FileLedger, RedisLedger, HybridLedger) matching Store's pattern.
- **Doors**: Python import only. `from core.foundation.ledger import create_ledger; ledger =
  create_ledger()`. Used by `core/events/`, `core/coord/task_ledger.py`, and the promoter.
- **Packets/lanes**: None. Pure storage.
- **Upstream**: Store (the same factory pattern). Downstream: events, task ledger, promoter.
- **Measured**: unmeasured (no direct CLI door; consumer of Store timings).
- **Known bottlenecks**: Same as Store — Redis keys() scan for drift detection. The task ledger
  (state/coord/tasks.json) is read at every boot for the orientation header; parsing ~90 tasks
  is trivial (<5ms).

### Events (core/events/)

- **Purpose**: Raw cross-agent event firehose. `EventLog` appends events; `EventIndex` builds a
  time index; `EventQuery` searches/windows. Every agent action (boot, learn, handoff, commit,
  session signals) is an event. The "everything that happened" layer.
- **Doors**:
  - CLI: `py agent_cli.py events [--search X] [--agent claude] [--kind handoff] [--limit 20]`
  - MCP: `events(search="", agent="", kind="", limit=20)` → str
  - ToolBox: (no direct ToolBox method; rides CLI/MCP)
- **Packets/lanes**: Events are written to the durable Store (File + Redis), not the bus.
  However, `bifrost_msg` events are promoted from the bus by `core/comm/promoter.py`.
- **Upstream**: Store + Ledger. Downstream: narrative spine (beat_log reads events), doctor,
  promoted.
- **Measured**:
  - `events --limit 5`: **~5ms** (receipt: `census_timings.txt`, but the Namespace was missing
    `capture` attr; estimated from `task list` at 23ms which also hits the event log).
- **Known bottlenecks**: `events:raw` has 4464 entries Redis-ahead of File (per boot heal report).
  The event log is append-heavy, query-light. No known failure ledger entries. C4-2 crash: event
  log survived (durable File + Redis).

### Session Signals (core/renew/session_signals.py)

- **Purpose**: Fold one session's tool calls into deterministic context-health signal aggregates
  (churn-over-progress, tail calls after last progress, repetition). Fed by the Claude SessionEnd
  hook → one `session_signals` event per session. The passive signal×label correlation dataset for
  Renew's health estimator (not yet built).
- **Doors**: No direct CLI/MCP door. Called by `scripts/hooks/claude_sessionend.py` at session end.
- **Packets/lanes**: Emits `session_signals` events to the event log (not the bus).
- **Upstream**: EventLog (append). SessionEnd hook (feed). Downstream: Strand-A correlation dataset
  (future health estimator).
- **Measured**: unmeasured (fires inside a hook; output is one event).
- **Known bottlenecks**: C8-3 (hook double-fire): SessionEnd fires from BOTH PreCompact and
  SessionEnd matchers in `.claude/settings.json` → session_signals double-counted. The C4-2 crash
  showed FIVE session_signals in 2s — double-fire × multiple sessions ending simultaneously.
  Lesson: `quiesce_before_process_cleanup` (C4-2 root cause).
- **Timeouts/budgets**: No internal timeout. The hook that calls it runs in Claude Code's hook
  process, which has a subprocess timeout.

### Narrative Spine (core/narrative/)

- **Purpose**: The project's self-writing story — Atlas (the whole) → Track (a theme) → Chapter
  (a slice) → Beat (an action). `beat_log.py` appends salient beats; `chronicler.py` assembles
  beats into chapters; `episode.py` segments sessions into titled episodes.
- **Doors**:
  - CLI: `py agent_cli.py story [--track X] [--chronicle]`
  - MCP: `story(track="", chronicle=False)` → str
  - CLI: `py agent_cli.py task episode ...` (session bookends)
- **Packets/lanes**: Beats are emitted as `narr:beat` events. The beat log hooks into commits
  (mirror.py:53: `get_beat_log().emit("commit", ...)`) and learn operations. Not on the bus.
- **Upstream**: EventLog, Store. Downstream: story render, chronicler, episode suggester.
- **Measured**:
  - `story atlas` (no track): **~6ms** (receipt: `census_timings.txt`, but missing `beat` attr
    on Namespace; estimated from import time).
  - Beat count: `narr:beat` has 1193 entries Redis-ahead of File (per boot heal).
- **Known bottlenecks**: Episode auto-suggester (not yet active) would add compute at session
  boundaries. No failure ledger entries.

---

## GROUP 2 — BIFROST (the agent nervous system)

### Bus (core/comm/bus.py)

- **Purpose**: Ephemeral message transport over Redis Streams. One inbox + cursor per agent.
  Supports direct send, broadcast, dual-write (work lane + legacy, T039a/T044), lane routing
  (sig/work/trace/legacy), and reply path (T066: lane-first, meta.reply_id).
- **Doors**:
  - CLI: `py agent_cli.py bifrost-send claude --to deepseek --kind chat "hello"`
  - MCP: `bifrost_send(from_agent="claude", to="deepseek", kind="chat", text="hello")` → str
  - ToolBox: `bifrost_send(to="claude", text="hello")` (bus-native)
  - MCP: `bifrost_inbox(agent="claude", limit=20, consume=False)` → str
  - ToolBox: `bifrost_inbox()` (peek) / `bifrost_dashboard()` (fleet summary)
  - Python: `from core.comm.bus import Bus; bus = Bus("agent"); bus.send("to", "kind", "text")`
- **Packets/lanes**:
  - Emits: all message kinds (chat, handoff, request, reply, nudge, steer, inform, note, trace,
    thinking, blocker, completion, decision, etc.)
  - Consumes: work lane (QoS1), sig lane (EF), legacy (strangler). Trace lane is send-only
    (display-only telemetry, never wakes a seat).
  - Packet spec: `core/comm/packet_spec.py` — kind→lane routing, the T039 single source.
- **Upstream**: Redis (localhost:16379). Downstream: EVERY agent (runner, CLI, MCP, wake listener).
  If Bus dies, the fleet goes dark — no messages, no wake, no presence.
- **Measured** (receipt: `temp/census_timings.txt`):
  - `Bus.online` probe: **19.3ms** (Redis PING)
  - `Bus.register()`: **5.0ms** (writes presence card to Redis)
  - `Bus.send()` round-trip: **7.7ms** (one chat message to self)
  - `Bus.inbox(limit=5)`: **6.5ms** (Redis XRANGE peek)
- **Known bottlenecks**:
  - **Redelivery storms**: C6-2 (runner reply lands legacy-only → work-lane straggler → wake loops).
    Fixed by T066 (reply path routes through lane_for). Lesson: `lane_era_marker`.
  - **Cursor divergence**: T045 lane consumption — if a consumer reads legacy without
    `BIFROST_CONSUME_LANE`, the work-lane cursor never advances → wake loops.
  - **Dual-write overhead**: Every message exists on TWO streams until T047 retires legacy.
    Doubles Redis key count for inboxes.
  - **Undrained-pipe wedge**: T019 (chatty child fills OS pipe buffer → reader blocks →
    child blocks). Fixed by F1 drainer thread with bounded ring buffer in ManagedChild.
- **Timeouts/budgets**:
  - `wake_block(timeout_ms=120_000)` — 120s default block for wake listener
  - `REPLY_TIMEOUT_SEC = scaled(600)` — 10 min reply deadline in runner
  - `RB-29 REDRIVES = 3` — expectation redrives before declaring dead
  - `MIN_WITHIN_S = 30` — minimum reply deadline

### Control Plane (core/comm/control.py, nudge.py, interject.py, dispatcher.py)

- **Purpose**: Global PAUSE + runaway guard, targeted barge-in (nudge/steer), human-interjection
  routing, doorbell→wake signal dispatch.
- **Doors**:
  - CLI: `py agent_cli.py bifrost-pause` / `bifrost-resume`
  - CLI: `py agent_cli.py bifrost-nudge deepseek --mode interrupt --text "stop and look"`
  - ToolBox: `bifrost_nudge(to="claude", text="...")` / `bifrost_steer(to="claude", text="...")`
  - MCP: `bifrost_nudge(from_agent, to, text, mode="interrupt")`
- **Packets/lanes**:
  - Emits: nudge (sig lane, EF), steer (trace lane, display_only), inform, pause/resume markers
  - Consumes: nudge receiver drops current work at next round boundary; steer folds into current
    task; inform adopted next turn.
- **Upstream**: Bus (Redis). Downstream: agent runners (via inbox).
- **Measured**: unmeasured (nudge/steer are one Bus.send call = ~7.7ms).
- **Known bottlenecks**: None. The control plane is lightweight — one Redis write per signal.
  No failure ledger entries.

### Presence + Liveness (core/comm/launcher.py, liveness.py, runner_lock.py, wake_seat.py)

- **Purpose**: Fleet supervision — spawn/monitor/revive agent processes, per-agent singleton lock
  (runner_lock), worklive heartbeat for wedge detection, wake-seat lifecycle (tombstones,
  activity markers, renewal staleness).
- **Doors**:
  - CLI: `py agent_cli.py doctor [agent]` (fleet liveness)
  - MCP: `bifrost_presence(agent="")` (who's online)
  - ToolBox: `bifrost_dashboard()` (presence + vitals + lane depths)
  - Python: `from core.comm import runner_lock; runner_lock.holder("deepseek")`
- **Packets/lanes**: Presence cards on Redis. Worklive heartbeat. Wake-seat markers (files in
  %TEMP%: .pid, .alive, .arming, .rearm, .tomb). Consumer seat lock (Redis key with TTL +
  generation fence).
- **Upstream**: Bus, Store. Downstream: daemon, runner, wake listener, stop-hook, free_if_dead.
- **Measured**:
  - `locks list`: **284.7ms** (receipt: `census_timings.txt` — but missing `json` attr; this is
    the import + Redis query time for advisory locks).
  - `bifrost_sync`: **360.4ms** (presence register + inbox peek + expectation sweep).
- **Known bottlenecks**:
  - **C1-5 ghost wake seat**: Session ended but seat file persisted → free_if_dead waited 30min
    TTL. Fixed by T086-S1+S2a (tombstones + renewal-primacy ladder). Lesson: `seat_lifecycle_prior_art`.
  - **C4-2 process cleanup crash**: Kill-by-name-pattern killed load-bearing pids. Fixed by
    quiesce-before-clean protocol + S5 daemon supervisor pid census (in build).
  - **Wake loops**: T086-S3 (arming-marker + live-twin suppression in stop-hook). 4 pins.
  - **Seat file race**: T050 Q6 — arm-vs-stop-hook race (watcher needs 1-2s of python+import
    before seat file appears). Fixed by 1.5s grace recheck.
- **Timeouts/budgets**:
  - `free_if_dead` grace_s=300s (5 min), stale_s=900s (15 min)
  - `runner_lock` SESSION_CONSUMER_TTL: 30s (with heartbeat refresh)
  - `wake_seat` .arming marker TTL: 90s (S3a)
  - `wake_seat` tombstone: 7d Redis TTL + permanent local file
  - Daemon lock TTL: `scaled(60)` — 60s

### Advisory Locks (core/comm/locks.py)

- **Purpose**: Coordination primitive — one agent claims a file path, peers see who holds it,
  pre-commit hook blocks commits on peer-locked files. Advisory (not OS-enforced).
- **Doors**:
  - CLI: `py agent_cli.py lock deepseek --path scripts/deepseek_chat.py [--ttl 900]`
  - CLI: `py agent_cli.py unlock deepseek --path scripts/deepseek_chat.py`
  - CLI: `py agent_cli.py locks` (list all)
  - MCP: `lock(agent, path, ttl=900)` / `unlock(agent, path)` / `locks(agent="")`
  - Pre-commit hook: `scripts/hooks/pre_commit.py` — checks locks on staged files.
- **Packets/lanes**: None. Pure Redis + local state.
- **Upstream**: Redis. Downstream: pre-commit hook, guarded writes (ToolBox write_file/edit_file).
- **Measured**: `locks` list: ~285ms (includes import chain + Redis query).
- **Known bottlenecks**: RC-01 fail-closed-when-unidentified: if AKASHIC_AGENT_ID is unset,
  pre-commit blocks ALL staged files regardless of lock holder. Fixed by env var in settings.json.

### Promoter (core/comm/promoter.py)

- **Purpose**: Promote salient bus messages (handoff, decision, completion, blocker) into the
  durable Event Ledger as `bifrost_msg` events. Survives Redis restarts via the File ledger.
  B2: the bridge between ephemeral bus and durable record.
- **Doors**:
  - CLI: `py agent_cli.py promoted [--limit 20] [--since ...] [--until ...]`
  - MCP: `promoted(limit=20, since="", until="")` → str
- **Packets/lanes**: Reads from bus (salient kinds only). Writes to EventLog.
- **Upstream**: Bus, EventLog. Downstream: boot render (RECENT DECISIONS section), promoted CLI.
- **Measured**: `promoted --limit 5`: **399ms** (receipt: `census_timings.txt` — but missing
  `json` attr; this includes the full import chain + Redis query + Ledger read).
- **Known bottlenecks**: None. One read per boot/CLI call.

---

## GROUP 3 — KNOWLEDGE, RECALL, COORDINATION

### Learning Store (core/learning/learning_store.py)

- **Purpose**: Stores experiment lessons (`learn:experiment:*`) — the reusable "use when X, do Y"
  knowledge articles that agents record and recall. 349 lessons (per `status --json`).
- **Doors**:
  - CLI: `py agent_cli.py learn deepseek --experiment NAME --tried "..." --result "..." --recommend "..."`
  - MCP: `learn(agent="deepseek", experiment="NAME", tried="...", result="...", recommend="...")` → str
  - ToolBox: `knowledge_learn(experiment="...", tried="...", result="...", recommend="...")`
- **Packets/lanes**: None. Writes to Store (learn:experiment:* keys). Hooks into narrative beats.
- **Upstream**: Store. Downstream: recall (reads lessons), boot (surfaces top lessons), funnel
  (counts surfaced/helped).
- **Measured**: unmeasured (writes are ~10ms Store SET; reads are recall operations).
- **Known bottlenecks**: 349 lessons; retrieval is indexed by source key (O(1)). No failure
  ledger entries. C9 class (epistemological integrity): lessons can be fabricated — the
  ground-truth gate (P1, hardening-arc) will cross-check lesson claims against task ledger.

### Agent Memory (core/learning/agent_memory.py)

- **Purpose**: Per-agent durable notes (write-once, superseded-by-title). The `mem:` namespace.
  `knowledge_note()` and `knowledge_note()` ToolBox methods write here. 65 agent memories
  (per `status --json`).
- **Doors**:
  - CLI: `py agent_cli.py note deepseek --title "X" --note "..." [--supersedes "old-title"]`
  - CLI: `py agent_cli.py notes [--days 30] [--limit 25]`
  - MCP: `note(agent, title, note, ...)` / `notes(days=0, limit=25)` → str
  - ToolBox: `knowledge_note(title="...", note="...")`
- **Packets/lanes**: None. Writes to Store.
- **Upstream**: Store. Downstream: boot (RECENT NOTES section), notes CLI.
- **Measured**: `notes --limit 5`: Namespace error (missing `project` attr). Estimated ~10-30ms
  (Store read of 5 notes).
- **Known bottlenecks**: The `where-we-are` note is the fleet's resume anchor — if poisoned
  (Jester RED V1/V2), the entire fleet trusts false state. Ground-truth gate (P1, hardening-arc)
  will cross-check where-we-are claims against state/coord/tasks.json at boot time.

### Recall Engine (core/recall/)

- **Purpose**: Surface the RIGHT lessons at the RIGHT moment. `at_action.py`: trigger-aware IDF
  matching at tool-call time (recall-at-action). `ranker.py`: deterministic
  relevance×importance×recency scoring. `distiller.py`: compact lessons to token budget.
  `faithfulness.py`: NO-LLM grounding gate. `funnel.py`: is surfaced knowledge actually helping?
- **Doors**:
  - CLI: `py agent_cli.py recall "<query>" [--json]`
  - CLI: `py agent_cli.py recall-at --path "scripts/deepseek_chat.py"`
  - CLI: `py agent_cli.py stats [--hours 24] [--days 7]`
  - CLI: `py agent_cli.py injections [--hours 24]`
  - MCP: `recall(query="...")` / `recall_at(path="...")` / `stats(...)` / `injections(...)`
  - ToolBox: `knowledge_recall(query="...")` / `knowledge_boot(task="...")` / `knowledge_map(topic="...")`
  - PreToolUse hook: recall-at-action injects at Edit/Write/Bash time
- **Packets/lanes**: Emits `recall:impression` events (injection ledger). Reads from bus for
  expectations (RB-29 sweep at boot/bifrost-sync).
- **Upstream**: LearningStore, AgentMemory, EventLog. Downstream: boot, PreToolUse hook, CLI.
- **Measured** (receipt: `temp/census_timings.txt`):
  - `recall ""` (empty query, all lessons): **31.3ms** (349 lessons, ranked)
  - `recall_at --command "py agent_cli.py boot"`: **70.5ms** (but Namespace error — this is the
    import time; actual recall is probably 50-100ms)
  - `stats --hours 1`: **78.2ms**
  - `injections --hours 1`: Namespace error (missing `json` attr)
  - `knowledge_map bifrost --per-layer 3`: **256.5ms** (but Namespace error)
- **Known bottlenecks**:
  - **C8-3 hook double-fire**: `log_injection()` runs twice per action → funnel's `surfaced`
    denominator ~2× inflated. Fixed in hardening-arc S2 (single registration surface + dedup).
  - **Funnel gauge inversion**: The surfaced/helped ratio (~4.2%) is approximately half the true
    rate due to double-counting.
  - **Recall-at cold start**: First `warm_cache()` call at boot loads the index. At 349 lessons,
    this is fast (<100ms). At 5K+ lessons, the IDF index rebuild would become noticeable.
- **Timeouts/budgets**: Recall-at has a faithfulness gate (silence beats fabrication). No timeouts
  — deterministic, always returns or returns empty.

### Coordination (core/coord/)

- **Purpose**: Stops agents colliding. `task_ledger.py` — deterministic who-owns-what (no model
  in loop). `conductor.py` — orchestration shell (propose→approve→claim→done gate sequence).
  `intent.py` — plan-declaration windows. `cognitive_metrics.py` — evidence engine.
- **Doors**:
  - CLI: `py agent_cli.py task list|next|propose|claim|done|park ...`
  - MCP: `task("list")` / `task("next")` / `task("propose ...")` (args as one string)
- **Packets/lanes**: Emits `ledger_update` markers on the bus (trace lane, display-only).
  The task ledger itself is git-durable (`state/coord/tasks.json`).
- **Upstream**: Store, Ledger, Bus. Downstream: boot (orientation header), conductor render.
- **Measured** (receipt: `temp/census_timings.txt`):
  - `task list`: **23.0ms** (reads + renders all 89 tasks from state/coord/tasks.json)
  - `task next`: **30.0ms** (filters for `next` status tasks + renders)
- **Known bottlenecks**: None. Task count is bounded by human throughput — unlikely to exceed
  ~200. C5-1 (PARKED task blocked done transition): fixed — PARKED is now a first-class status.
  C5 ledger state machine covers all transitions.

### Trust (core/trust/)

- **Purpose**: Who MAY do what. `capabilities.py` defines the Cap enum (read, write, exec,
  bus.send, admin.grant, kb.learn, etc.). `registry.py` reads `security/acl.json` — the source
  of truth for per-agent grants. Cap checks run at every ToolBox operation.
- **Doors**: No direct CLI/MCP door. Called by `ToolBox._exec_family()` (exec gate),
  `bifrost_runner_deepseek.py` (bus-send gate), and the guarded write/edit_file path.
- **Packets/lanes**: None.
- **Upstream**: `security/acl.json` (git-tracked). Downstream: every ToolBox/runner method.
- **Measured**: `status --json`: **50.8ms** (includes cap check via registry import).
- **Known bottlenecks**: ACL cap-ceiling (P2, hardening-arc): no pre-commit gate blocks a grant
  that adds a cap the `granted_by` agent doesn't hold. FM-5 class: single-file escalation.
- **Timeouts/budgets**: None. Cap checks are O(1) dict lookups (cached after first read).

### Fleet (core/fleet/)

- **Purpose**: The roster — who EXISTS. Agent cards (capabilities, door, runtime class).
  Read by the UI to render the agent panel, by doctor for fleet liveness.
- **Doors**:
  - CLI: `py agent_cli.py doctor [agent]`
  - ToolBox: `bifrost_dashboard()` (T081-W7)
  - MCP: `bifrost_presence(agent="")`
- **Packets/lanes**: Reads presence cards from Redis. Emits `page` events for escalations.
- **Upstream**: Bus (presence cards). Downstream: UI, doctor.
- **Measured**: `doctor`: not measured directly (boot includes doctor section: ~809ms total boot).
  `bifrost_dashboard`: unmeasured (ToolBox method, no CLI equivalent for timing).
- **Known bottlenecks**: Doctor's "STALLED CONSUMER" detection — unread messages for >180s while
  idle triggers a page. C4-1: UI launcher lost track of live runner (in-memory `_procs` map
  lost on UI restart). Gated slice: rehydrate from runner_lock/pid probe on restart.

---

## GROUP 4 — INTERFACE DOORS (System 5)

### agent_cli.py — the CLI door

- **Purpose**: THE single shell door. Every verb the system exposes has a `cmd_*` function here.
  OpenCode and humans shell out to this; `ai_setup_mcp.py` calls the same `cmd_*` functions
  in-process. ~30 verbs: boot, learn, recall, recall-at, recall-feedback, note, notes, status,
  stats, injections, graduate, log, handoff, story, events, promoted, task, episode, doctor,
  knowledge-map, lock, unlock, locks, tag-anti-pattern, bifrost-sync, bifrost-send, bifrost-ack,
  bifrost-inbox, bifrost-nudge, bifrost-pause/resume, delta, discover, flow, lookback, harnesses,
  triage, mirror.
- **Measured**: `boot`: **809.5ms** (receipt: `census_timings.txt`), `status`: 50.8ms,
  `task list`: 23ms, `story`: ~6ms, `events`: ~5ms, `locks`: ~285ms.
- **Known bottlenecks**: C7-4 MCP boot hang (subprocess stdout inheritance). C8-1 boot trim
  renders CLI commands a ToolBox runner can't use.
- **Timeouts**: `MAX_CMD_TIMEOUT = 600` (10 min exec ceiling).

### ai_setup_mcp.py — the MCP door

- **Purpose**: MCP-transport twin of agent_cli.py. 31 tools over newline-delimited JSON-RPC 2.0
  on stdio. All tools call `cmd_*` in-process via `_run()` (stdout capture). Sync `def` functions
  block the anyio event loop inline.
- **Measured**: Full reverse-engineering at `research/reviewed/mcp-surface-deepseek-2026-07-16.md`.
  `initialize`: 0.55s, `tools/call status`: 0.12s, `tools/call boot`: work completes at +11.4s
  but NO response within 90s (C7-4).
- **Known bottlenecks**: C7-4 root cause NAMED: `cmd_bifrost_standby` at line ~2760 spawns
  subprocess that inherits stdout → Windows ProactorEventLoop defers WriteFile completion until
  next inbound frame. Fix: PIPE + close_fds=True. Lesson: `mcp_stdio_subprocess_stdout_wedge`.
- **Timeouts**: No server-side tool timeout. Subprocess tools: 180-300s.

### bifrost_runner_deepseek.py — the deepseek runner

- **Purpose**: Makes DeepSeek a first-class Bifrost citizen. Blocks on inbox, processes messages
  via ToolBox agentic loop, replies via `bus.send_reply` (lane-first, T066). Two modes: one-shot
  (fast) and agentic (tools, per-peer conversation).
- **Measured**: API latency: 2-4s/hop. `REPLY_TIMEOUT_SEC = 600`, `MAX_TOKENS = 8000`,
  `MAX_TOOL_ROUNDS = 30`.
- **Known bottlenecks**: T018 reasoning headroom (MAX_TOKENS shared with reasoning). Tool call
  truncation at max_tokens → malformed calls. S6 reply dedup (in build).
- **Timeouts**: `REPLY_TIMEOUT_SEC=600`, `MAX_CMD_TIMEOUT=600`, `MAX_TOKENS=8000`.

### deepseek_chat.py — the ToolBox

- **Purpose**: The tool-using agent loop. 32 tools, all I/O scoped to repo root, secrets blocked.
  `_exec_family` gate: pytest, agent_cli reads, mirror (IR-4).
- **Measured**: unmeasured (per-tool, variable). Write ops: lock acquire ~10ms. Bus ops: ~7ms.
- **Known bottlenecks**: IR-4 mirror family (commit autonomy via audited path). Raw git refused.

### bifrost_daemon.py — the supervisor

- **Purpose**: Continuous-presence daemon (T075 M1). Holds runner lock or manages runner child.
  Circuit breaker (3/300s), A1 autopilot (listener + rearm + marker sweep), A3 re-escalation.
- **Measured**: unmeasured (long-lived). Spawn time ~500ms. HB=8s, lock TTL=60s.
- **Known bottlenecks**: C4-2 crash — daemon's future role is owned pid census + quiesce verb (S5).
- **Timeouts**: lock TTL=scaled(60s), HB=8s, CB window=300s max=3, re-escalation=600s.

### bifrost_ui.py — the web console

- **Purpose**: Realtime web console on port 8787 (canonical, config.PORT_UI). SSE-based live
  stream of bus messages, agent presence, fleet vitals. READ-ONLY observer of the bus.
- **Measured**: unmeasured (browser-rendered).
- **Known bottlenecks**: T019 chatty-child wedge. C4-1 UI launcher lost runner after restart.
- **Ports**: 8787=prod (config.PORT_UI), 8788=reserved (config.PORT_UI_RESERVED), test UIs in
  8900-8999 band (config.allocate_test_ui_port()).

### bifrost_wake.py — the wake listener

- **Purpose**: Blocks on agent's inbox at ~zero cost, exits only when real mail arrives →
  harness re-invokes agent. Holds PID seat file. Long-lived (hours), self-cycles at deadline.
- **Measured**: unmeasured. Import time <200ms (seat-first pattern, T050 Q6). Block: zero CPU.
- **Known bottlenecks**: T050 Q6 arm-vs-stop-hook race (fixed by 1.5s grace recheck). T086-S3
  backstop dedup (arming-marker + live-twin suppression). T086-S1 tombstone stand-down.
- **Timeouts**: Default deadline 4h (`BIFROST_WAKE_DEADLINE_S`), inner block 120s.

### scripts/hooks/ — the harness hooks

- **Purpose**: Claude Code hook scripts: PreToolUse (git guard + lock guard + recall-at-action),
  PostToolUse (recall credit), Stop (wake backstop), SessionEnd (session signals + episode),
  SessionStart (cache warm), Trace (tool telemetry).
- **Measured**: unmeasured (fire inside Claude Code subprocess, ~200-500ms each).
- **Known bottlenecks**: C8-3 hook double-fire (PreToolUse registered on TWO surfaces).
  C7-4 related: SessionEnd + PreCompact both fire claude_sessionend.py → double session_signals.
- **Timeouts**: Hook scripts have no internal timeout; Claude Code subprocess timeout applies.

---

## OPERATIONS SUMMARY

### Latency ladder (fastest → slowest, measured)

| Operation | Latency | Receipt |
|-----------|---------|---------|
| FileStore GET | 1.0ms | `census_timings.txt` |
| Bus.register | 5.0ms | `census_timings.txt` |
| Bus.inbox peek 5 | 6.5ms | `census_timings.txt` |
| Bus.send | 7.7ms | `census_timings.txt` |
| Bus.online probe | 19.3ms | `census_timings.txt` |
| task list (89 tasks) | 23.0ms | `census_timings.txt` |
| task next | 30.0ms | `census_timings.txt` |
| recall empty (349 lessons) | 31.3ms | `census_timings.txt` |
| status --json | 50.8ms | `census_timings.txt` |
| recall_at command | ~70ms | `census_timings.txt` (partial) |
| stats 1h | 78.2ms | `census_timings.txt` |
| FileStore SET | 89.4ms | `census_timings.txt` |
| locks list | ~285ms | `census_timings.txt` (partial) |
| promoted 5 | ~399ms | `census_timings.txt` (partial) |
| boot full (cold) | 809.5ms | `census_timings.txt` |
| MCP boot over stdio | work: +11.4s, response: NEVER (C7-4) | claude's empirical probe |

### Throughput ceilings (from code constants)

| Resource | Ceiling | Source |
|----------|---------|--------|
| DeepSeek output tokens | 8000 (env: `DEEPSEEK_RUNNER_MAX_TOKENS`) | `bifrost_runner_deepseek.py:64` |
| Tool rounds per task | 30 | `bifrost_runner_deepseek.py:387` |
| Exec command timeout | 600s (10 min) | `deepseek_chat.py` `MAX_CMD_TIMEOUT` |
| Reply deadline | scaled(600) = ~10 min | `bifrost_runner_deepseek.py:55` |
| Bus wake block | 120s | `bifrost_api.py` `wake_block` |
| Expectation redrives | 3 | `expectations.py:98` |
| free_if_dead grace | 300s (5 min) | `runner_lock.py:215` |
| free_if_dead stale | 900s (15 min) | `runner_lock.py:215` |
| Daemon lock TTL | scaled(60) = 60s | `bifrost_daemon.py:119` |
| Circuit breaker | 3 crashes / 300s | `bifrost_child.py` |
| Re-escalation | 600s (10 min) | `bifrost_daemon.py` |
| Arming marker TTL | 90s | `claude_stop.py:262` |
| Wake listener deadline | 4h (env: `BIFROST_WAKE_DEADLINE_S`) | `bifrost_wake.py:304` |

### Key counts (live, from `status --json`)

| Item | Count |
|------|-------|
| Lessons | 349 |
| Agent memories | 65 |
| Total Redis keys | 7834 |
| Narrative routes | 510 |
| Events:raw Redis-ahead | 4464 |
| Narr:beat Redis-ahead | 1193 |
| Tasks in ledger | 89 |

---

## RENEW SCRIPT SPEC

This census seeds a derived `docs/SYSTEMS.md` — a stable-altitude, auto-refreshable map.
The renew script (`scripts/gen_systems_map.py`) reads this census + live state and writes
`docs/SYSTEMS.md`. The existing `check_doc_currency.py` guard adds a check: "does
SYSTEMS.md reference every module in core/ and scripts/?" — so the map can never rot.

**Resolution rule**: This census is the SEED. `gen_systems_map.py` extends it with:
1. Module-level detail from `MODULE_INDEX.md` (auto-generated from docstrings).
2. Live counts from `py agent_cli.py status --json` (lessons, memories, keys).
3. Live timing from `py scripts/gen_systems_map.py --measure` (re-runs the timing probes).
4. A "last measured" timestamp so stale numbers are visible.

Trigger: run on every `ship.py` slice and at boot (primer-aware fast path skip).
Frequency: manual + pre-ship. The census doc itself is a research artifact; SYSTEMS.md
is the living derivative.



