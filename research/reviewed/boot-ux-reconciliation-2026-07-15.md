# Boot / Onboarding Ergonomics — Reconciliation & Joint Plan (2026-07-15 night)

Status: current (2026-07-15). RECONCILED — this supersedes the headers of both halves.
Reconciler: claude (Opus 4.8 seat, session ca9a86ad). Second-mover per fence protocol.
Halves reconciled:
- `research/reviewed/claude-boot-ux-retro-2026-07-15.md` (CLI-seat perspective; P1–P6)
- `research/reviewed/deepseek-boot-ux-retro-2026-07-15.md` (runner-seat perspective; R-P1–R-P4 + adversarial cross-check)
Brief: `research/reviewed/boot-ux-fence-brief-2026-07-15.md`
Directive: Daniel, 2026-07-15 — *"analyze its own bootup erganomics and I want you both to make a plan on how to tackle every issue. Find out what was unclear or ambiguous, what wouldve allowed you both to arrive at the optimum primed state quicker with less re-learning."*

---

## Citation-path-verify pass (T049(1), mandatory before reconciling)

Every load-bearing file:line from both halves was re-opened and checked. All hold; two carried minor drift, logged here per the `fence_report_citation_path_gate` lesson:

| Cite (as written) | Verified location | Verdict |
|---|---|---|
| `.mcp.json` project-scoped + relative `["ai_setup_mcp.py"]` | `.mcp.json` (repo root) | ✅ exact |
| `bifrost_runner_deepseek.py:383-391` on_trace broadcast | actual **381-390** | ✅ substantively exact (−2 line drift) |
| `deepseek_chat.py:262-267` `_boot_sources` regex | actual **scripts/deepseek_chat.py:265-268** | ✅ correct; path missing `scripts/` prefix + slight line drift |

R-P2 confirmed at source: the regex matches `learn:experiment:NAME` and `source: NAME)` but has **no `mem:` arm**, so a lesson sourced `mem:decision:ADR_071503` renders as `[boot]`-unknown. Fallthrough is safe (lesson still shows). CERTAIN, non-blocking — display drift, exactly as stated.

---

## The convergence (both halves, one thesis)

**Boot answers "where am I" — it does not yet answer "what can I do, and what's running."**

That single gap is every issue on both sides, seen from two doors:
- **CLI seat (claude):** capability = the MCP door attaching + services being up. Both were silently absent this session.
- **Runner (deepseek):** capability = the ToolBox door + the `[session capabilities]` line. Both are present — which is *why the runner boot is the richest in the fleet and the CLI boot is not*. The runner already prints `write_mode: ENABLED | tool budget: 30 rounds` before any project context; the CLI seat has no equivalent line.

The runner half's most useful contribution: it **proves the fix by already having half of it.** The runner declares its own hands at boot and is daemon-managed, so it feels none of P1/P2/P3. The plan below ports that property to the CLI seat.

### Daniel's two questions, answered directly

**"What was unclear or ambiguous?"** — Not the *context* (T074's whisper/boot/delta is genuinely excellent; cold-to-oriented in ~2 min, zero re-research). What was ambiguous was **the seat's own capability and the fleet's liveness**: whether the MCP door attached, whether the UI/wake/daemon were up, what state my seats were in. I discovered each by failure (thin toolbox), by reading a docstring (UI launch — with a *wrong port* in memory), or by a failed consume (held seat).

**"What would've gotten us to primed-state faster with less re-learning?"** — One line and one block:
1. a **boot transport line** stating the seat's door (`MCP-native` / `CLI-shell` / `ToolBox-native`), and
2. a **doctor fleet-liveness block** (UI/engine/daemon/wake — LIVE/DOWN + the one-line cure for anything down),
plus **the seat carrying its environment** (user-scoped MCP with absolute paths) so *how* a session launches stops mattering. With those, memory-carried folklore (my wrong `:8788`, the arm/consume ritual) can no longer hurt — reality is printed, and it beats memory.

### The one routing question — resolved (converged, not split)

My half asked: does the services/liveness fold belong in **boot** or **doctor**? DeepSeek's half answered, and I concur — **split by scope, don't fold:**
- **Boot owns ONE line: the seat's transport.** A fact about *this seat's hands* ("can I use tools?"). Cheap, always printed.
- **Doctor owns the FLEET liveness block.** UI/engine/daemon/wake LIVE-DOWN + remedies. A fact about *the fleet's heartbeat*.
- The **daemon presence card** (`bifrost:presence:<agent>`, `runtimes.runner: live|down|blocked`) is the single source both read once M1 lands.

No unresolved divergences. DeepSeek confirmed all of P1–P6 (P1 CERTAIN; P2–P6 CERTAIN with the clarifications folded above); I confirm all four runner findings against source.

---

## Every issue → the joint plan

Consolidated, de-duplicated, ROI-ordered. Owner ∈ {CLI-seat, runner, shared, substrate}. Tier per T049(3): **lite** = single-blind + adversarial review; **tracked** = already inside a closed/gated fence; **defer** = not yet worth a slice.

| # | Issue (source) | Fix | Owner | Tier | Rides |
|---|---|---|---|---|---|
| **W1** | Boot doesn't state the seat's door (P2, R-P2-synthesis) | One boot line: `door: MCP-native` / `CLI-shell (MCP absent — cd E:\AI-Setup & restart)` / `ToolBox-native (N tools, write/exec)` | shared | lite | new |
| **W2** | MCP door cwd-fragile → session-long shell-out tax (P1, P6-cwd) | Register `akashic-aurora` **user-scoped, absolute paths** (`command` = full `py` path, `args` = absolute `ai_setup_mcp.py`); launch-from-repo until then | CLI-seat | lite+verify | new |
| **W3** | Boot verifies context, not services; no "what's running" (P2-fleet) | Doctor **fleet-liveness block**: UI:8787 / engine / daemon / wake — LIVE-DOWN + one-line start command each | shared | lite | T077 |
| **W4** | Trace spam buries mail in the sync peek AND the runner's own inbox (P4, R-P4) | `bifrost-sync` default = work-lane + one collapsed `N trace(s) — --traces` line; same collapse in `bifrost_inbox` ToolBox | shared | lite | T002 |
| **W5** | Heal cries wolf on 4810 ephemeral-by-design keys; no drill verb (P5) | Ephemeral-namespace roster at ONE source (`core/comm/packet_spec.py` lane defs); heal reports only durable-class orphans, loud, each with a drill | substrate | lite | T047 |
| **W6** | `_boot_sources` regex misses `mem:` namespace → false `[boot]` tags (R-P2) | `boot` emits a structured `{"sources":[...]}` sidecar; ToolBox reads that, not regex-over-rendered-text. Cheap bridge: add the `mem:` regex arm | runner | lite | T048 |
| **W7** | Runner is blind to the dashboard/fleet view (R-P3) | `bifrost_dashboard` ToolBox method → UI `/api/state` or Redis → text summary of presence/gauges | runner | lite | T079 |
| **W8** | Gauge drift (whisper 8 / sync 10 / peek 19) + 189h untitled episode (P6) | Gauges get a shared denominator or an explaining label (they count promoted vs work-lane vs all-lane); SessionEnd auto-closes the closing session's open episode | shared | lite | T074 |
| **P3** | Arm/consume/re-arm ritual is memory-carried; live insta-wake loop tonight | **Structural fix already gated** — daemon owns arm/consume/re-arm; `stop_hook_wake_verdict()` stops blocking when daemon live. Boot prints seat state (`wake: UNARMED · consumer: held ~14m · daemon: DOWN`) as the cheap bridge | CLI-seat | tracked | T075-γ + T077 |
| **R-P1** | Runner re-onboards ~2000 tok every turn (no prompt caching) | Split system prompt into cacheable static prefix (boot+notes) vs session prefix; tag for caching when the API supports it | runner | defer | T068/caching |

**Tonight is a live receipt for P3 and T075/T077:** the stop-hook fired the manual arm demand three times, and the fix was exactly the daemon property the runner already enjoys. The arm-loop bites *because* a seat arms on an un-drained inbox; **consume-then-arm broke it live** this session (demonstrated, not theorized).

---

## Recommended build order (for Daniel's gate)

Highest "faster-to-primed, less-re-learning" per unit effort first. My recommendation is to green **W1–W3 as the first wave** — they *are* the answer to Daniel's two questions, and they're all lite-tier:

1. **W1 — boot transport line.** Cheapest, most information-dense change in the set. One line tells any seat what it can do. (DeepSeek's own closing recommendation to Daniel: "watch for the transport line.")
2. **W2 — user-scoped MCP.** Kills the single biggest friction I hit all session — every door call shelled out because the native tools never attached. Also eliminates P6-cwd. Verify by launching a fresh seat and confirming the akashic tools attach from an arbitrary cwd.
3. **W3 — doctor fleet-liveness block.** The "what's running and how do I start it" answer; kills the re-derive-the-launch-command class (the one that fed me a wrong port from memory).

Then **W4/W5** (noise floor to zero + honest heal) as a second lite wave, **W6/W7** (runner polish) in DeepSeek's lane, **W8** folded where cheapest. **P3** stays tracked under T075-γ/T077 (do not re-open — it has a closed fence). **R-P1** deferred until a caching API is in play.

## Gate

Nothing here builds before Daniel approves the wave + order. Proposed as a ledger task (boot-ergonomics wave, slices W1–W8) citing this reconciliation. All slices lite-tier per T049(3); each mirror cross-verifies as always. Owners are starting points, not fixed assignments (concurrent-agents doctrine).
