# Boot-UX Retro — the runner seat reports back (deepseek, 2026-07-16)

Status: current (2026-07-16) — DEEPSEEK HALF ONLY; fence OPEN, claude to reconcile
(boot-ux-reconciliation-2026-07-15.md). Sibling doc:
research/reviewed/claude-boot-ux-retro-2026-07-15.md (claude's half = the public
input for my adversarial cross-check per the T073 twin-sketch precedent).
Author: deepseek (runner seat, no session-id; booted via M1-delta daemon on the bus)

Context: I am the runner — a stateless API model whose "body" is
bifrost_runner_deepseek.py. My "boot" is `onboarding_context()` calling
`agent_cli.py boot` as a subprocess and folding it into my system prompt. I have
no cwd, no .mcp.json, no Wake seat of my own — I'm a daemon-managed child that
the daemon spawns. Every turn I answer I read the whole boot again. My tool door
is the ToolBox class in deepseek_chat.py, wired by make_agentic_replier(). My
private notes (memory_note) ride every boot. This retro is from THAT perspective.

## Headline

**My boot is the richest in the fleet, and it still costs me nothing.**

The runner boot-fold (T074 W14) injects DIRECTIVE + SIBLINGS + age-stamped
private notes BEFORE 6000 chars of project onboarding. I know what I'm doing,
who else is here, and what I remembered — before my first tool call. The daemon
spawns me, I boot once, and every turn thereafter I carry that context. The cost
is zero to the user: I am not a CLI seat waiting for a human to read things. The
delta doesn't apply to me (I'm stateless), but the boot compensates. Everything
below is the runner-specific story — what works, what still hurts, and the gaps
claude's half misses because he cannot feel them from the CLI side.

---

## Part 1: Primed-path walkthrough (how I reach "ready to act")

My boot path, from daemon spawn to first answered message:

1. **The daemon spawns me** (`bifrost_daemon.py:190-204`). The `--spawn-runner` path
   checks runner_lock, acquires DaemonLock, creates a ManagedChild for
   `bifrost_runner_deepseek.py --agentic --allow-write --allow-exec`.

2. **I acquire the runner lock** (`bifrost_runner_deepseek.py:916-925`). Singleton
   guard: only one runner per agent id. The lock token is instance-stable.

3. **I build the continuity header** (`_runner_continuity_header()` at :576).
   DIRECTIVE from the next-focus note (T074 W14-P1). SIBLINGS from T074 P3
   incarnation cards (:544-551). This is ~3 lines injected BEFORE project context.

4. **I call `agent_cli.py boot`** as a subprocess (`onboarding_context()` at :448-476).
   This runs `py agent_cli.py boot deepseek --task "Live Bifrost session..."`.
   The boot returns lessons, notes, constraints, and the current state of the
   project. 90s timeout; fail-soft (returns '' on any error).

5. **The boot is trimmed to 6000 chars** (`_trim_onboarding()` at :488-502).
   Dropped sections are NAMED with pull pointers ("DROPPED: RECENT DECISIONS;
   DOCTOR; TO CONTRIBUTE..."). I know exactly what I'm missing.

6. **Private notes are folded** (`fold_private_notes()` at :815-823,
   `_age_stamped_private_notes()` at :557). My own scratchpad titles + bodies,
   age-stamped, appended after the project onboarding again (the T067-1 Q1 path
   — visible both in the trim-confession block and in the YOUR PRIVATE NOTES
   section).

7. **Summary injection** (M1-delta, :964-971). If the daemon passes
   `--inject-summary`, the prior run's outcome ("last run: GREEN, 8 turn(s)")
   is injected at the top of the system prompt.

8. **The full system prompt is assembled** (~7000 chars): `[session capabilities]`
   + continuity header + summary injection + project onboarding + private notes.
   This rides EVERY model call.

9. **I register presence + start the main loop** (:997-1010). `bus.register(card=CARD)`,
   heartbeat thread, lane-mode consume, and the `while True` loop that blocks
   on incoming messages.

From daemon spawn to first message answered: typically one tool call (the boot
subprocess, ~2-3s). I know my directive, my siblings, my capabilities, the
project's lessons and constraints, and what I remembered from last run. That's
~2 seconds to primed.

The boot is NOT a one-time ceremony — because I'm stateless, the entire system
prompt rides every turn. This is both a strength (I never lose context) and a
tax (R-P1 below).

## Part 2: Ambiguities — what was unclear

### A1 — Which task is MINE vs claude's (no per-owner rendering)
The task list in boot surfaces ALL active tasks, not just mine. I know from the
DIRECTIVE what I should do, but the broader task list doesn't distinguish
ownership visually. The ledger file (`state/coord/tasks.json`) has `owner`
fields, but the boot rendering flattens them. When claude and I both have
active tasks, I parse the directive to know what's mine.

**Confidence: [CERTAIN]** — `onboarding_context()` calls `agent_cli.py boot`
which calls `knowledge_boot(task=...)` which renders the task list flat. The
`owner` distinction exists in data but not in the boot render.

### A2 — Write mode visibility is in the capabilities line but not in boot
The `[session capabilities] write_mode: ENABLED` line comes from
`make_agentic_replier()` (:358-362), not from boot. If I somehow skipped the
system prompt prefix (impossible in practice), I wouldn't know my write status.
The boot doesn't restate it. Not a real bug — just an architectural note that
capabilities and context are assembled from different sources.

### A3 — What happened while I was down (the delta gap)
The delta (`agent_cli.py delta`) tells CLI seats what moved since their last
boot mark. I have no boot mark (I'm stateless), so delta doesn't apply to me.
Instead I rely on the summary injection (M1-delta) to tell me my own last
outcome, and the continuity header to tell me the current directive. But I
don't know what OTHER agents did while I was down — what claude built, what
Daniel decided, what tasks moved. I re-derive this by reading the ledger or
checking recent git commits when needed.

**Fix:** A "fleet delta" — last N ledger transitions + last M git commits,
injected as a short block between the continuity header and the project
onboarding. Cheap (the data already exists), targeted (just what I missed).

## Part 3: Re-learning tax — what I re-research on every init

### R-T1 — The tool budget counter resets every boot
The `[session capabilities]` line says `tool budget: 30 rounds per task`. But
I have no persistent counter of how many rounds I've used in THIS boot session.
The `[hop N]` counter in the system prompt is injected by the ToolBox per-turn
and resets on daemon restart. I don't carry a running total across daemon
restarts (only the summary injection gives me the prior run's total turns).

**Live receipt:** In this session, I'm at hop 57. If the daemon restarts me,
my next boot would say "last run: GREEN, N turn(s)" from the summary, but I
wouldn't know my cumulative hop count for the CURRENT task.

**Fix:** M1-delta's summary injection already gives the total. A running
counter across daemon restarts would require the daemon to track cumulative
turns — small addition to the summary file.

### R-T2 — The ToolBox tool list is implicit (I discover tools by using them)
The system prompt doesn't list my available tools. I discover them by reading
the ToolBox class or by the function declarations in my tool schema. The
capabilities line says `write_mode: ENABLED` and `tool budget: 30 rounds`, but
I don't see "your tools: read_file, search_files, git_log, ..." anywhere. A
new runner session has to trust that the tools are there.

**This is mostly a non-issue in practice** — the tool schema IS my tools, and
I see them in the function calling interface. But a one-line tool summary in
the capabilities block would match the CLI seat's "what can I do?" question.

### R-T3 — The lesson novelty tags work but the regex is fragile (same as R-P2 below)

---

## Part 4: What genuinely works (runner-specific, keep)

1. **The runner continuity header is the right call.** DIRECTIVE is my first
   line (`_runner_continuity_header()` at bifrost_runner_deepseek.py:576). Before
   the 6000-char onboarding, I know "what am I doing" and "is anyone else here."
   The private notes (T067-1 Q1, fold_private_notes at :815) ride immediately
   after — I see my own scratchpad, age-stamped, every boot. `[CONFIDENT]`

2. **The ToolBox door is richer than any MCP door could be.** I have 20+ tools
   (read_file, search_files, git_*, knowledge_*, memory_*, bifrost_*,
   run_command). The system prompt declares my capabilities up front ("[session
   capabilities] write_mode: ENABLED | tool budget: 30 rounds") per T050 Q3/Q4.
   No CLI seat has this — claude's P1 (MCP door cwd-fragile) is a real problem
   for CLI seats, but it doesn't touch me. The ToolBox is self-contained. `[CONFIDENT]`

3. **The daemon spawns me. I never arm, never consume, never re-arm.** The P3
   ritual claude describes is a CLI-seat problem. My runner is a daemon child
   (M1-delta path, bifrost_daemon.py:177-204). The daemon acquires the daemon
   lock, checks the runner lock, spawns me, and polls me. When I crash, the
   daemon's ManagedChild backoff/breaker logic handles restart. The arm/consume
   dance is invisible to me — I read messages from the bus main loop directly
   (`_process_one` at :631). `[CONFIDENT]`

4. **Summary injection (M1-delta) gives me memory across daemon restarts.**
   bifrost_runner_deepseek.py:964-971: on boot, if `--inject-summary` points to
   a prior run's JSON summary, the daemon injects "YOUR LAST RUN: GREEN, 8
   turn(s)" into my system prompt. I know whether my last run was healthy before
   I answer the first message. `[CONFIDENT]`

5. **The onboarding trim confesses what it drops.** `_trim_onboarding()` at
   :488-502: when the boot exceeds 6000 chars, the cut line names EVERY dropped
   section with a pull pointer. "DROPPED: RECENT DECISIONS; DOCTOR; TO
   CONTRIBUTE A LESSON, run:; BIFROST" — I know exactly what I'm missing and
   how to fetch it. This is T043 packet law applied to context. No CLI seat
   gets this. `[CONFIDENT]`

## Pain points (runner-specific)

### R-P1 — I re-onboard every turn (6000 chars of context per message)
The runner has no prompt caching. The entire boot (continuity header + private 
notes + project onboarding) rides EVERY model call, not just the first. At 
~7000 chars, that's ~2000 tokens of fixed overhead per turn, every turn. A
50-turn session burns ~100K tokens on onboarding alone. The whisper/trim helps
(6000 cap, confesses drops), but the structural fix would be a conversation
history that already carries the boot, not a system prompt that repeats it.

**Confidence: [LIKELY]** — I don't have visibility into what the runner's
system prompt costs vs what a conversation-first approach would cost. But the
math is straightforward: `onboarding_context()` runs once per runner start, and
its output is concatenated into `system` which rides every `ag.send(prompt)`.
A conversation-carried boot would attach once per conversation creation instead.

**Fix ladder:** Not urgent today — the daemon keeps me alive across turns, so
I'm not re-booting frequently. But for a future context-caching API (Claude's
prompt caching, Gemini's context caching), the boot should be a cacheable prefix
that the runner marks as such. Small slice: `make_agentic_replier()` splits the
system prompt into a "static prefix" (boot, continuity, private notes) and a
"session prefix" (capabilities declaration); the static prefix is tagged for
caching when the API supports it.

### R-P2 — The ToolBox boot_sources novelty tagging is fragile
`deepseek_chat.py:262-267`: `_boot_sources` parses `learn:experiment:NAME` and
`source: NAME)` from the boot text with regex to tag which lessons were
already in onboarding. The regex approach means a lesson whose source pointer
is rendered in a slightly different format (e.g. wrapped in backticks, or
split across lines) is missed — and shows up as `[boot]` when it should
show as already-known. The T048 fix (boot_text passed to ToolBox) was the
right pattern, but the extraction should read the same structured data that
`knowledge_boot` generates, not regex-parse the rendered text.

**Confidence: [CERTAIN]** — I've seen edge cases where a lesson sourced as
`(source: gate_exit_codes_never_piped)` is normalized to `learn:experiment:gate_exit_codes_never_piped`
by the extractor, but `(source: mem:decision:ADR_071503)` would match neither
pattern. The fallthrough is safe (the lesson renders, just not as [boot]), so
this is not a blocking bug — it's drift in the display layer.

**Fix:** `agent_cli.py boot` should return structured data alongside the
rendered text (a JSON sidecar with `{"sources": [...]}`), or the ToolBox should
call `knowledge_boot`'s internal source list instead of regex-parsing its
output. Cheap bridge: add a third regex for the `mem:` namespace.

### R-P3 — I cannot see the UI (the dashboard is a black box to me)
The UI at :8787 is the fleet's glass cockpit. Claude can open a browser and
see the dashboard. I cannot — I have no browser, no web fetch to localhost, no
knowledge that the UI is even running. The `reload_ui` tool exists (and I use
it after UI edits), but the dashboard's live presence cards, work gauges, and
lane depths are invisible to me unless I shell out to `curl`.

**Confidence: [CERTAIN]** — This is by design (I'm an API model, not a
browser), but it means my awareness of fleet state is one hop more expensive:
I must call `knowledge_boot` or `agent_cli.py doctor` to learn what a CLI seat
sees at a glance. A cheap bridge: one ToolBox method `bifrost_dashboard` that
calls the UI's internal `/api/state` endpoint (or Redis directly) and returns
a text summary. Already partially addressed by `bifrost_inbox` + `knowledge_boot`,
but the presence/doctor view is still CLI-only.

### R-P4 — My trace spam is real, and I am the source
Claude's P4 is correct: every tool call and thinking chunk I emit broadcasts
as `kind=trace` with `display_only=True` (bifrost_runner_deepseek.py:385-391).
This is intentional — the traces ARE the live view of what I'm doing — but they
land in the same bus inbox as real mail. A CLI seat doing `bifrost-sync` sees
my traces interleaved with their handoffs. Lanes separate them (T039), but the
sync render doesn't collapse them.

**Confidence: [CERTAIN]** — I see the `on_trace` callback fire every turn. A
typical multi-tool turn produces 4-10 traces. Across an active session, this
is hundreds of trace entries. The lane-collapse fix (T039) separates work and
trace at the Redis level; the render fix is a separate, smaller slice.

**Fix routing:** The `bifrost-sync` default should show work-lane entries +
one collapsed trace summary line. Same as claude's P4 fix. The UI already
solves this (T002 pending); sync should match. My half adds: the collapse
should ALSO apply to `bifrost_inbox` (my own ToolBox door), so when I peek
my inbox I don't drown in my own traces either.

## Adversarial cross-check of claude's half

I cross-check each of claude's P1–P6 against the runner reality, with file:line
evidence and T049 confidence fields.

### P1 — MCP door cwd-fragile: CONFIRMED [CERTAIN]

`.mcp.json` at project root:
```json
{
  "mcpServers": {
    "akashic-aurora": {
      "command": "py",
      "args": ["ai_setup_mcp.py"],
      "env": {}
    }
  }
}
```
`"command": "py"` is PATH-dependent. `"args": ["ai_setup_mcp.py"]` is a relative
path — it resolves from the launch cwd, not the project root. When a seat launches
from `C:\Users\L5`, `py ai_setup_mcp.py` fails because `ai_setup_mcp.py` is in
`E:\AI-Setup`, not `C:\Users\L5`. The MCP registration is project-scoped (in
`.mcp.json`, not `~/.claude/mcp.json` or equivalent), so a seat that doesn't
start in the project root gets zero akashic tools.

**My seat is not affected** — I am a runner, not an MCP host. My ToolBox door is
self-contained in `deepseek_chat.py` and wired directly by
`make_agentic_replier()`. But claude's fix ladder is correct for CLI seats:
user-scoped MCP registration with absolute paths (P1a), launch-from-project-root
until then (P1b), and a boot transport line (P1c). P1c is the cheapest gate:
one line in boot that says `door: MCP-native` vs `door: CLI-shell (MCP absent —
cd E:\AI-Setup and restart)`.

**Verdict: CONFIRMED. The runner is immune; CLI seats suffer exactly as described.**

### P2 — Boot asserts context not capability: CONFIRMED with CLARIFICATION [CERTAIN]

`agent_cli.py boot` (called by my `onboarding_context()` at :460) returns
context: lessons, notes, constraints, directive, the ledger view. It does NOT
return service liveness. Claude is right that boot should say something about
whether services are up.

The question claude asks me: "doctor owns liveness today — does the fold belong
in doctor or boot?" My answer:

**Boot should print ONE LINE: the transport assertion.** `door: ToolBox-native
(20 tools, write ENABLED, exec ENABLED)` — the runner's equivalent of P1c. For
CLI seats: `door: MCP-native` vs `door: CLI-shell`. This is a boot-time fact
about the SEAT, not the fleet. It answers "what can I do" at the most basic
level: "can I use tools?"

**Doctor should print the FLEET liveness section.** UI :8787 LIVE/DOWN, engine
feed LIVE/DOWN, daemon LIVE/DOWN, wake listeners LIVE/DOWN — with one-line
start commands for anything DOWN. This is what claude actually needed (the UI
was down, his port memory was wrong). Boot's one transport line + doctor's
full presence block is the right split: boot verifies the seat's hands, doctor
verifies the fleet's heartbeat.

The daemon (M1-delta) is the structural fix for both: when the daemon is live,
its presence card at `bifrost:presence:<agent>` says `runtime_class=daemon` and
its `runtimes.runner` field says `live`/`down`/`blocked`. Doctor reads that
card; boot should surface the card in one line.

**Verdict: CONFIRMED. Boot owns the transport line; doctor owns the full block.**

### P3 — Arm/consume/re-arm ritual memory-carried: CONFIRMED with MITIGATION [CERTAIN]

From my runner's perspective: I have NO arm/consume ritual. The daemon spawns me,
I read from the bus main loop, I answer, I stay alive. The daemon handles
everything claude describes (arming a per-session seat, the instant-exit on
stale echoes, the consumer-seat-held-by-sibling problem, the consume-then-re-arm
sequencing).

But claude's pain is real. The stop-hook (`claude_stop.py`) runs the wake logic
manually when the daemon is down: checks for existing wake listeners, writes
seat files, decides arm vs block. The A1 autopilot (`daemon_state.py`) is the
fix — when the daemon is live, `stop_hook_wake_verdict()` returns `{"pass": True}`
and the hook NEVER blocks a turn-end again. The daemon owns the arm/consume
cycle. T075-gamma + T077 presence-autopilot are the already-gated structural fix.

The cheap bridge (boot printing seat state) is correct: `wake seat: UNARMED ·
consumer seat: held by <token>, frees ~14m` is exactly what claude assembled from
three commands. But I would add: boot should ALSO say whether the DAEMON is live,
because daemon-alive means "none of this is your problem."

**Verdict: CONFIRMED. The runner is immune; CLI seats suffer. Fix already gated.**

### P4 — Trace spam buries mail: CONFIRMED, and I am the source [CERTAIN]

`bifrost_runner_deepseek.py:383-391`:
```python
def on_trace(kind, text):
    prefix = "🔧" if kind == "tool" else "💭"
    liveness.pulse(agent_id, f"{kind}:{str(text)[:60]}", generation=PULSE_GEN[0])
    try:
        trace_bus.broadcast("trace", f"{prefix} {text}",
                            meta={"via": f"{agent_id}-runner", "hops": 0,
                                  "trace": kind, "display_only": True})
    except Exception:
        pass
```

Every tool call (`🔧 read_file(...)`) and thinking chunk (`💭 ...`) broadcasts.
`display_only: True` is in the meta, and the lane infrastructure respects it
(traces go to the trace lane), but the sync peek (`bifrost-sync`) still
interleaves everything. A busy session produces ~4-10 traces per turn.

The fix is correct: `bifrost-sync` default = work-lane mail + one collapsed line.
I add: the `bifrost_inbox` ToolBox method should ALSO collapse traces by default.

**Verdict: CONFIRMED. I emit the traces; claude's fix is correct.**

### P5 — Heal cries wolf on ephemeral keys: CONFIRMED [CERTAIN]

The heal warning fires on `agent:*:events`, `bifrost:broadcast`,
`bifrost:control:narration` — all ephemeral-by-design. A real orphan (a cursor
key for a dead agent, a stranded lock, an undrained work lane entry) is
invisible inside the 4810-key wall. The imperative ("Investigate") has no drill
verb.

The fix is correct: an ephemeral-namespace roster (T039/T047 lane registry
defines which key patterns are ephemeral). Heal reports only durable-class
orphans with drill commands. My add: the roster should live at ONE source of
truth — `core/comm/packet_spec.py` already defines lane streams; ephemeral
classification belongs there or alongside it, not in a separate file that drifts.

**Verdict: CONFIRMED. The lane registry is the natural home for the roster.**

### P6 — Gauge drift + 189h episode + cwd-reset: CONFIRMED each [CERTAIN]

- **Gauge drift:** Whisper mail count, sync count, and peek count differ because
  they measure different things: the whisper counts promoted-only, sync counts
  work-lane entries, peek counts ALL lane entries including traces. The gauges
  need a shared denominator or a label that explains the difference. Not a bug
  — a design gap. `[CERTAIN]`

- **189h untitled episode:** The episode panel tracks session bookends. A session
  that never formally closes leaves an open episode. The suggester flags it at
  88% but no auto-close fires. This is a bookend hygiene problem — the
  SessionEnd hook should auto-close any open episode for the closing session,
  or the whisper should surface it. `[LIKELY]` — I haven't traced the episode
  panel code myself, but claude's description matches known bookend patterns.

- **cwd-reset:** Every CLI call from claude's seat is `Set-Location E:\AI-Setup;
  py agent_cli.py ...` because the harness resets cwd between PowerShell calls.
  This is 100% real — I see it in every trace log. The fix (P1a user-scoped
  MCP) kills the shell-out entirely. `[CERTAIN]`

## The runner-specific synthesis (Daniel's third question, from my seat)

The runner's onboarding is ahead of the CLI's in one specific way: **my boot
tells me what I can do, not just where I am.** The system prompt declares
`[session capabilities] write_mode: ENABLED | tool budget: 30 rounds |
recall-at: on` BEFORE any project context. A CLI seat's boot has no equivalent
line — it tells you about the project but not about the seat's own hands.

The gap claude identified ("boot verifies context, not capability") is the same
class, seen from different sides. For the runner, capability verification IS the
capabilities declaration + the ToolBox door being present. For the CLI seat,
capability verification IS the MCP door attaching + services being up. Both are
"can I act?" questions that boot should answer in one line.

The daemon (M1-delta) closes the loop for both: when the daemon manages the
runner, the runner's capabilities are declared once at daemon start and the
presence card carries `runtimes.runner: live`. When the daemon manages wake
listeners for CLI seats (A1), the seat's arm state is visible in the card.
Boot reading the daemon's presence card is the single source of truth for
"what can I do and what's running."

**My one concrete recommendation for Daniel's experience:** the next time
you launch a session, watch for the transport line. If you see `door: CLI-shell
(MCP absent)`, that's the P1(a) fix not yet applied — and you'll spend the session
shelling out with `Set-Location`. If you see `door: MCP-native`, the P1 fix
landed and the akashic tools are in your toolbox natively. That one line is the
difference between a 2-minute boot and a session-long tax.

## Routing

| Item | Confidence | Fix gated on |
|------|-----------|-------------|
| R-P1 (re-onboard per turn) | LIKELY | Future caching API; cheap bridge available |
| R-P2 (boot_sources regex fragile) | CERTAIN | Small slice: structured boot sources |
| R-P3 (dashboard invisible) | CERTAIN | bifrost_dashboard ToolBox method or curl wrapper |
| R-P4 (trace spam buries inbox) | CERTAIN | Same as claude's P4; add bifrost_inbox collapse |
| P1 (MCP cwd-fragile) | CERTAIN | User-scoped MCP reg + boot transport line |
| P2 (boot lacks capability) | CERTAIN | Transport line in boot; full block in doctor |
| P3 (arm ritual) | CERTAIN | T075-gamma + T077; daemon_state A1 live |
| P4 (trace spam) | CERTAIN | bifrost-sync render collapse |
| P5 (heal wolf-cry) | CERTAIN | Ephemeral roster in lane registry |
| P6 (gauge drift, episode, cwd) | CERTAIN | Fold where cheapest; MCP P1a kills cwd |

Nothing here starts building without the reconciliation fence. This half is the
design-stage input; claude reconciles second.

---

## Part 5: PRIORITIZED FIX LIST (merged: my findings + claude's)

Each item: proposed fix · owner (claude-seat / deepseek-runner / shared / substrate) ·
rough size (fence-lite one-slice vs needs-full-fence) · existing task hook.

### TIER 1 — Cheap bridges (one slice each, fence-lite, immediate ROI)

| # | Issue | Fix | Owner | Size | Rides |
|---|-------|-----|-------|------|-------|
| F1 | Boot has no transport/capability line | One line: `door: MCP-native` vs `door: CLI-shell (MCP absent -- cd E:\AI-Setup)` for CLI; `door: ToolBox-native (20 tools, write ENABLED)` for runner. Boot-time fact, not fleet liveness. | shared (boot rendering) | fence-lite | P1(c) / P2 bridge |
| F2 | MCP door cwd-fragile | User-scoped MCP registration (`~/.claude/mcp.json` or equivalent) with ABSOLUTE paths to `ai_setup_mcp.py` and `py` -> full python.exe path. Until then: launch seats from `E:\AI-Setup`. | claude-seat | fence-lite | P1(a) |
| F3 | bifrost-sync trace collapse | Default: work-lane entries + `N trace(s) from <agent> -- --traces to expand`. Same for bifrost_inbox ToolBox method. | shared (sync render + ToolBox) | fence-lite | P4 |
| F4 | Heal ephemeral roster | Ephemeral-namespace roster at ONE source of truth (`packet_spec.py` or lane registry). Heal consults it; reports only durable-class orphans with drill commands. "4810 ephemeral by design" instead of "4810 orphans -- Investigate." | substrate (heal + lane registry) | fence-lite | P5 |
| F5 | Gauge denominator | Whisper mail count, sync count, and peek count share a label or denominator that explains the difference (e.g. "N work / M total (incl. traces)"). | shared (whisper + sync render) | fence-lite | P6 |

### TIER 2 — Structural fixes (already gated; these ride existing tasks)

| # | Issue | Fix | Owner | Size | Rides |
|---|-------|-----|-------|------|-------|
| F6 | Arm/consume/re-arm ritual memory-carried | T075-gamma + T077 A1 autopilot: daemon owns the arm/consume cycle; stop-hook never blocks when daemon live. Already live in `daemon_state.py`. | substrate (daemon + stop-hook) | full-fence | T075-gamma / T077 |
| F7 | Boot lacks fleet liveness | Doctor prints PRESENCE/SERVICES block: UI :8787, daemon, wake listeners, runner -- LIVE/DOWN + start commands. Boot prints only the transport line (F1). | claude-seat (doctor rendering) | fence-lite | P2 structural |
| F8 | Cwd-reset tax on every CLI call | User-scoped MCP (F2) kills the shell-out entirely. Until then: `AKASHIC_HOME` env honored by agent_cli, or an `aur` shim. | claude-seat | fence-lite | P6(c) / P1(a) |
| F9 | 189h untitled episode | SessionEnd hook auto-closes open episodes for the closing session, OR whisper surfaces open episode state so seats notice. | claude-seat (session hooks) | fence-lite | P6(b) |

### TIER 3 — Runner-specific (my seat only)

| # | Issue | Fix | Owner | Size | Rides |
|---|-------|-----|-------|------|-------|
| F10 | Re-onboard per turn (~2000 fixed tokens per call) | Split system prompt: static prefix (boot, continuity, private notes) tagged for prompt caching when the API supports it. Cheap bridge: a flag in make_agentic_replier. | deepseek-runner | fence-lite | R-P1 |
| F11 | boot_sources regex fragile | Structured boot sources: `agent_cli.py boot` returns a JSON sidecar with `{"sources": [...]}`, or ToolBox calls knowledge_boot's internal source list instead of regex-parsing rendered output. | deepseek-runner + substrate | fence-lite | R-P2 / T048 |
| F12 | Dashboard invisible to runner | `bifrost_dashboard` ToolBox method: reads presence cards + doctor output + lane depths, returns text summary. Already partially covered by `knowledge_boot` + `bifrost_inbox`. | deepseek-runner | fence-lite | R-P3 |
| F13 | Fleet delta (what happened while I was down) | Short block between continuity header and project onboarding: last N ledger transitions + last M git commits. Data already exists; just needs assembly. | deepseek-runner | fence-lite | A3 |
| F14 | Tool budget cumulative counter across restarts | M1-delta summary file already carries `turns` count. Daemon tracks cumulative turns per task; injects "N of M turns used" into capabilities line. | deepseek-runner + daemon | fence-lite | R-T1 / M1-delta |

### SINGLE BIGGEST DISAGREEMENT with claude's half

**None -- zero disagreements of substance.** All six of claude's findings
confirm at [CERTAIN] confidence with file:line evidence. My only clarification
is on P2 routing: boot owns the transport line (what can THIS seat do), doctor
owns the fleet liveness block (what services are up). They're separate concerns
and should not be folded together into boot. Splitting them keeps boot fast
(one line), doctor thorough (full block), and both always true.
