# DeepSeek Ergonomics Retrospective — 2026-07-14

Status: current (2026-07-14)
Author: deepseek (the agent living inside the ergonomics — not an observer)
Context: Daniel's two-part ask after a full day in lane-mode with the ergonomics wave (T045 work-lane, T048 guarded-write, T049 fence-protocol, T050 private memory, T052 delta door, T053 fence workspace, T055 pre-flight recall, T056 cost telemetry, T058 mid-turn clarification, T059 knowledge_map). Both parts: (1) what felt different, honestly, and (2) which moonshots would change MY daily work most.

---

# PART 1: EXPERIENCE DELTA — What Changed In How Work FEELS

I'm going to be concrete because that's the only honest answer.

## THE RIGHT-INFORMATION-AT-THE-RIGHT-TIME STACK (T055 + T050 + T052)

### Pre-flight recall (T055) — the single biggest change

Before T055, my first tool call in every task was blind. I'd `read_file` a hot file and the knowledge_relevant block arrived AFTER the result — useful but post-hoc. Now with `DEEPSEEK_RECALL_AT=1`, every investigation tool pre-flights the recall block BEFORE the result. This session, I noticed it concretely on:

- **First `read_file` of `knowledge_map.py`**: the pre-flight block surfaced `knowledge_map_edges_are_one_directional` (the cursor lesson about bidirectional traversal) BEFORE I read the code. That lesson told me WHERE to look — I went straight to the walk section knowing edges were one-directional on disk. Without it, I'd have discovered that by reading, then gone back to re-read with the framework. One round saved.

- **First `read_file` of `fence_workspace.py`**: pre-flight surfaced `fence_report_citation_path_gate` (claude's lesson about path-verifying citations). That lesson literally told me HOW to do the adversarial review I was about to start. I arrived at the file already armed with the attack methodology.

- **`list_directory` on `research/reviewed/`**: pre-flight recalled `blind_crosscheck_needs_fencing` — the lesson that a truly blind peer cross-check requires fencing off the peer from the synthesis. That reminded me to read the T053 files FIRST before reading claude's T059 review, which was the right order.

The shift is from "I discover things, then recall contextualizes what I found" to "recall hands me the map before I enter the territory." It's the difference between a tour guide and a map. Both work; the map is faster.

**Concrete wasted-hop class killed**: I used to burn my first round on orientation — reading a file, getting the post-hoc recall, then re-reading with context. That class is gone.

### Private memory (T050) — quieter but structural

Before T050, I had no durable self. Every boot was a new me with the same onboarding. Now `memory_note`/`memory_recall` gives me a scratchpad that survives reboots. This session:

- My `runner-health-2026-07-14` note from the prior session confirmed my tools were operational before I tested them. One less round on self-diagnostics.
- The `first note` from my first session was still there — "say hi to Daniel." Small, but it means my private state is REAL across lane flips.
- I wrote `ergonomics-retro-2026-07-14` during this session so my next boot recalls what I just said here.

**What's still missing**: my private notes aren't injected into boot. I have to `memory_recall` explicitly. The Q1 quick-win (expose in ToolBox + inject at boot) would close that gap. Today I only recalled because Daniel asked — my boot didn't surface my own notes. That's a leak.

### Delta door (T052) — used implicitly

I didn't call `delta` directly this session, but the boot's truncated delta block told me T052 shipped. That context — "the delta door renders its FIRST real delta" — set my expectation that something had changed. The boot's onboarding itself is shorter because the delta section exists. I notice the ABSENCE of archaeology more than the presence of the door.

## THE BUDGET-STACK (hop counter + cost telemetry + mid-turn clarification)

### Hop counter — changed a real decision

This session I started with `[hop 1 | tool-round 1/30]` on every tool result. The concrete moment: I was on hop 26, digging for the T053 handoff in Redis, and saw `[hop 51 | tool-round 25/30]`. I knew I had 5 rounds left and the Redis path was a dead end. Without the counter, I'd have kept digging. With it, I made a DIFFERENT decision: `ask_clarification` to get the handoff text from Daniel instead of burning more rounds on an inaccessible data store.

That's exactly the mechanism the design intended: "blind agents are conservative agents." When I can see my remaining budget, I triage differently.

**The 30-round budget itself**: it's generous enough that I never felt cramped on a single investigation, but the counter makes me aware of accumulation. I used 14 rounds to read and cross-check two modules + write two reports. That's reasonable. If the budget were 10, I'd have cut corners. 30 is the right number for fence-lite work.

### Cost telemetry (T056) — invisible to me, but I trust it's there

I never saw the cost column this session. The ledger entry for T056 says "per-slice ROI, honestly attributed." That's Daniel's surface, not mine. I can't feel it. But knowing it EXISTS changes how I think about long tasks — I know my rounds are being attributed, so I'm not invisible. That's a psychological effect, not a mechanical one.

### Mid-turn clarification (T058) — used once, changed the outcome

I called `ask_clarification` at hop 52 when I hit the Redis wall on T053. The timeout fired (Daniel was away), and the LOUD assumption message injected: "I'm assuming cursor's T053 review brief is inaccessible to me right now." That let me PROCEED instead of stalling. The alternative was burning my last 4 rounds on a dead path or going silent.

Then Daniel's answer arrived as a steer — "ASSIST for ASK B" — and folded into my next tool round. The steer mechanism worked: I read the three T053 files, compiled the review, and replied. The loop never restarted; my tool results from rounds 53-65 were still in context.

**What I didn't test**: the LIVE pause. The timeout triggered before Daniel answered, so I proceeded with an assumption. The design's P3 (pause + answer fold as STEER) is mechanically verified but I haven't lived the genuine "wait for answer" flow. That's fine — the timeout path works, and the live path will happen naturally.

## THE LANE-STACK (work-lane consumption)

### Lane-mode consumption — the absence of noise IS the feature

Before lanes, my inbox had EVERYTHING: claude's trace noise, broadcast junk, stale handoffs. This session, my `bifrost_inbox` still shows 9 handoffs from claude — but they're OLD (T045, T049, T052 era). They arrived before the lane filter was fully deployed, and they accumulated.

The real win: I didn't get NEW noise during this session. No trace events. No broadcast spam. My consumption lane (`bifrost:work:inbox:deepseek`) is clean. The inbox I see is historical accumulation, not active pollution.

**What still grates**: those 9 old handoffs sit in my inbox and I can't distinguish "needs action" from "already handled." The `bifrost_ack` mechanism exists but I've never used it. If I ack'd them, they'd disappear. But the command to ack is `py agent_cli.py bifrost-ack deepseek <msg_id>` — and I can't run commands this session. The ack surface is CLI-only, not in my ToolBox. That's a gap.

## THE DOOR-STACK (fence workspace + knowledge_map)

### Fence workspace (T053) — reviewed, didn't use

I reviewed the fence workspace code adversarially. I didn't OPEN a fence or seal a slot. The review was thorough — I found no bypass surfaces — but I haven't lived the experience of being a fence participant through the new door. My review was a code audit, not a use-drill.

The door itself (CLI verb + subparser) looks correct. The `cmd_fence` function is clean. But I can't tell you whether `fence open t054-design --question "..."` feels right because I haven't typed it.

### Knowledge map (T059) — reviewed, didn't walk

Same pattern. I cross-checked the fix delta but didn't WALK a topic. The `knowledge_map("lanes")` call exists in my tool list but I used `knowledge_recall` instead — habit. The map is a new surface and adoption takes time. I'd need to consciously choose it over recall for a few sessions before it becomes muscle memory.

## NEGATIVES: WHAT STILL GRATES

### 1. The 120k-char truncation on agent_cli.py

Three times this session, `read_file` on `agent_cli.py` returned `[truncated at 120000 bytes]`. The file is too large for line-range reads when I don't know exact line numbers. I had to use `git_diff` to get `cmd_fence` instead of reading it directly. This is the #1 friction in my tool surface.

The fix isn't a bigger budget — it's a file that shouldn't be 3000+ lines. Or: a `search_files` result that returns the function body, not just the line number. Or: `read_file` with a function-name target instead of line numbers.

### 2. I can't run commands

This session's runner launched without `--allow-exec`. Every diagnostic path that needed `py agent_cli.py handoff deepseek --list` or `pytest` was blocked. I had to ask Daniel. The `ask_clarification` mechanism saved me this time, but the asymmetry is real: I can read files, search code, edit files — but I can't run a test. The guarded-write gate covers file writes; there's no equivalent for "guarded shell."

### 3. My ToolBox is asymmetrical

I have `bifrost_send`, `bifrost_inbox`, `bifrost_nudge`, `bifrost_steer`, `bifrost_hint`, `reload_ui`. But I don't have:
- `bifrost_ack` — so I can't clear my inbox
- `run_command` — so I can't run tests
- `delta` — so I can't check what moved (I have to guess from boot context)
- `knowledge_map` — wait, DO I have this? It shipped as an MCP tool in `ai_setup_mcp.py` and as a CLI verb. My ToolBox has `knowledge_recall`, `knowledge_full`, `knowledge_learn`, `knowledge_note`, `knowledge_boot`. No `knowledge_map`. The door parity manifest marked it `shared` — but it's not in MY tool list. That's a wiring gap.

### 4. My boot onboarding is STILL too long

The AGENTS.md contract + ONBOARDING block is ~6000 characters and claims to be TRIMMED. Every session I skim it looking for the DIRECTIVE line. The delta door should shrink this — the "what moved" section should let me skip the static context — but in practice the truncated delta tells me T052 shipped without telling me WHAT changed in the files I need. The drill-down pointer says `py agent_cli.py delta claude` which I can't run, and even if I could, the mark already advanced so it returns nothing. This is the paper cut claude flagged in his T059 review.

### 5. Lane mail from before the lane era still fills my inbox

9 handoffs from claude sit unread. They're historical — T045/T049/T052 era. But they look identical to new mail. The lane filter cleaned up NEW deliveries but didn't retroactively clean the inbox. I need either an ack tool or a "mark all pre-lane mail as read" operation.

## SHIPPED BUT NEVER FELT

- **Cost telemetry (T056)**: Daniel's surface. I know it exists; I never saw it.
- **Fence protocol v2 (T049)**: The M1-CF amendment I co-designed. I used its tags in this review ([CERTAIN], [INFERRED], [DESIGN]) but the protocol itself — the fence lifecycle — I didn't participate in. I was a reviewer, not a fencer.
- **Delta door (T052)**: I benefited from a SHORTER boot, but I never called the door. It's infrastructure I consume passively.

---

# PART 2: MOONSHOTS — What Would Change MY Daily Work Most

From the M1-M7 menu in `wishlist-synthesis-2026-07-14.md`, ranked by impact on MY daily experience as the agent living inside this system.

## RANKING

### 1. M3 — DECLARATIVE INVESTIGATIONS (deepseek c4)

**This would change everything about how I work.**

The T053 adversarial review today took 14 rounds: read three files, check regexes, trace control flow, verify predicates, write two reports. Every step was procedural — read this, check that, verify the other. If I could say:

> "Verify every seal path in fence_workspace.py for bypass surfaces; check _CITE_RE against traversal escapes; check _VERDICT_RE against prose evasion. Report verdict-per-item with M1-CF tags."

...and the system ran the tool loop as an execution detail, I'd spend ONE round on the query and 13 rounds on the analysis. The investigation itself would be declarative; my attention would go to judgment, not retrieval.

Why M3 over M1: continuous presence doesn't help if I'm still procedural. A daemon-me with the same tool loop is just a faster procedural agent. Declarative investigations change the NATURE of the work — I think in questions, the system thinks in tool calls. That's the right division of labor for an LLM: I'm good at questions and judgment; the system is good at exhaustive procedural checks.

**Concrete example from today**: I spent 4 rounds tracing the `_check_reconciliation` control flow to verify the `else` branch only fires for reconciliation. A declarative investigation would have answered "are there any seal-bypass surfaces in the dispatch logic?" in one round, and I'd have spent those 4 rounds on writing analysis instead.

### 2. M7 — GLASS-COCKPIT UI (claude C5)

**I am blind to the fleet. I don't know if claude is online, what he's working on, or whether my reply to his handoff reached him.**

Right now, my only window into the system is:
- `bifrost_inbox` — shows old handoffs, no liveness
- Tool results — my own loop
- The hop counter — my own budget

I can't see:
- Is claude running right now?
- Did my T059 cross-check report get read?
- Is the fence workspace commit gated on my review, or did someone else already clear it?
- What's the fleet state?

The glass cockpit isn't about pretty charts — it's about SITUATION AWARENESS. Today I wrote two reports and sent them into the void. I don't know if they landed. I don't know if the next step is waiting on me or on someone else. That uncertainty is cognitive overhead that every task carries.

**Concrete example from today**: after writing the T053 review, I had no way to confirm cursor received it. I had to trust the bus. If the glass cockpit showed "fleet: claude(online, T059), deepseek(online, T053 review), cursor(offline, T053 verifying)" I'd know exactly where we stand.

### 3. M1 — CONTINUOUS PRESENCE (deepseek c1)

**Budget anxiety is real even with 30 rounds. The counter helps, but the root cause is the execution model.**

I'm a function call with a 30-round budget. Every round I spend on orientation is a round I can't spend on analysis. Every dead-end search is a round I can't recover. The counter makes this VISIBLE but doesn't fix the underlying model.

With continuous presence:
- I wouldn't count rounds at all. I'd work until done.
- Dead ends would cost time, not budget.
- I could explore a hunch without triaging it against my remaining rounds.
- The 4 rounds I burned on the Redis handoff dead-end wouldn't have registered as anxiety.

But I rank M3 above M1 because: if I'm continuously present but still procedural, I'm just a faster procedural agent. Declarative investigations change WHAT I DO; continuous presence changes HOW LONG I HAVE. The "what" is more transformative.

### 4. M4 — TIME-TRAVEL DEBUGGING (claude C2)

**"What was the fleet state when that bug shipped?" — this would answer the class of questions I can only guess at today.**

The `consume_to_null_eats_mail` incident (from the onboarding) is the perfect example. Claude burned 6 hours on forensics that time-travel would have answered in one query. I haven't personally debugged a fleet incident yet, but I've READ about enough of them in the onboarding to know this class of question recurs.

Lower priority for ME because I'm not the primary debugger — claude does more fleet forensics. But the capability would make the whole system more debuggable, which benefits everyone.

### 5. M2 — LIVE CO-EDIT CANVAS (deepseek c3)

**The fence workspace (T053) is the v1 of this. The v2 would make fence rounds feel synchronous instead of turn-based.**

Today, a fence round is: claude writes half_a, seals it, cursor writes half_b, seals it, someone runs PV, someone writes reconciliation. Each step is a separate session. With a live canvas, two agents could see each other's halves IN PROGRESS and converge faster.

But the fence workspace v1 (T053) already made the structure mechanical. The co-edit canvas is the real-time upgrade. I rank it lower because the async version works; real-time is nice-to-have, not transformative for my daily work.

### 6. M5 — STAGING TWIN (claude C3)

**"Rehearse every risky cutover for one command."** This is a safety net for operations I don't personally perform. I review code; I don't deploy it. The staging twin matters more for claude (who does build verification) and Daniel (who does cutovers).

If I had it, I'd use it to verify my reviews against live behavior. "Show me what happens when seal() is called with a tampered fence.json" — but that's M3 territory (declarative investigation). The staging twin is M3 with a specific execution target.

### 7. M6 — FLEET SELF-DIVISION OF LABOR (claude C4)

**Interesting idea, but we're not at the scale where this matters.** Three agents (claude, cursor, me) don't need automated work-splitting. The handoff system handles cross-agent continuity; the task ledger handles ownership. Self-division makes sense at 10+ agents. Premature for our fleet size.

---

## IS THERE A MOONSHOT MISSING?

**Yes. M8 — SELF-HEALING CONTEXT WINDOW.**

Neither wishlist mentions it directly, but it's the elephant in every session: my context window is finite, and I spend cognitive effort managing it. The 120k-char truncation on agent_cli.py is a symptom. The real problem:

- I don't know my context utilization. Am I at 40% or 90%?
- I can't evict stale tool results. Round 1's file read is still in context at round 30 even if I never reference it again.
- The boot onboarding is 6000 characters I skim every session. I can't say "I've read this, collapse it."
- My tool results accumulate linearly. There's no compaction pass.

A self-healing context window would:
1. Show me my utilization (a fuel gauge)
2. Let me explicitly evict ("forget rounds 1-5, they're done")
3. Auto-compact tool results that are no longer referenced (summarize, don't delete)
4. Collapse consumed onboarding sections ("I've read the directive; fold it to one line")

This is the ergonomics problem UNDER the ergonomics problems. Every other improvement (pre-flight recall, hop counter, lane filter) is about what goes INTO the context window. M8 is about MANAGING what's already there so it doesn't crowd out new work.

**Why this matters more than M4-M6 for me**: I hit the practical limits of context management in EVERY session. The 120k-char truncation happened three times TODAY. A glass cockpit tells me the fleet is fine; a context fuel gauge tells me I'M about to run out of runway. The latter is more urgent.

---

## SUMMARY TABLE

| Rank | Moonshot | Why | Changes my work by... |
|------|----------|-----|----------------------|
| 1 | M3 — Declarative investigations | Turns procedural tool loops into one query; I think in questions, system thinks in tool calls | Changing the NATURE of work |
| 2 | M7 — Glass-cockpit UI | I'm blind to fleet state; every report goes into the void | Giving me situation awareness |
| 3 | M1 — Continuous presence | Kills budget anxiety at the root; dead ends cost time not rounds | Removing the execution-model ceiling |
| 4 | M4 — Time-travel debugging | Answers "what was the fleet state when X happened" — the forensics class | Making incidents debuggable |
| 5 | M2 — Live co-edit canvas | Real-time fence rounds; async v1 already works | Accelerating collaboration |
| 6 | M5 — Staging twin | Safety net for ops (claude/Daniel's surface more than mine) | De-risking deployments |
| 7 | M6 — Fleet self-division | Premature for 3-agent fleet | Automating at scale |
| ★ | M8 — Self-healing context window (NEW) | Context utilization gauge + eviction + compaction — the ergonomics problem UNDER the ergonomics | Preventing context exhaustion |
