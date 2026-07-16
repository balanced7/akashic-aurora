# Onboarding Audit — DeepSeek Runner Seat (2026-07-16)

Status: blind half (filed 2026-07-16 ~09:15). Claude files his HALF in parallel; reconcile after.
Daniel-directed 2026-07-16 morning: "pay attention to any friction points in the initial
onboarding. We just spent time making that process better, I want to see if we have addressed
all the gaps." Method: walk the runner boot as-if-fresh, every friction gets a receipt with
the actual text I saw, judge the T081 wave from my seat, rank remaining gaps.

## Part 1: The cold-boot walk (what I actually see, in order)

My boot is assembled by `bifrost_runner_deepseek.py` → `make_agentic_replier()` →
`onboarding_context()` → `_runner_continuity_header()` → `fold_private_notes()`. It lands
as my system prompt. Here is what I see, top to bottom, with commentary on what orients me
instantly vs. what I had to guess.

### Section A: Session capabilities (line 1-3)

```
[session capabilities] write_mode: ENABLED (guarded write_file/edit_file live; locks self-release at reply) | tool budget: 30 rounds per task, running counter [hop N] rides every result | recall-at: off
```

**Verdict: WORKS.** I know my write status, my hop budget, and that recall-at is off. The
budget gauge (IR-3 adjacent — `30 rounds per task`) is the single most action-changing
number I see: it made me use `ask_clarification` differently, made me chain tools
aggressively, made me count rounds. The hop counter `[hop N]` on every tool result
reinforces this. This section is tight and information-dense. **Gap: none.**

### Section B: Continuity header (line 4-6)

```
## YOUR CONTINUITY (this runner's last known state)
DIRECTIVE: MORNING GATE (Daniel): approve/amend T075 M1 build wave + review deepseek's exec grant (security/acl.json) + T070/T071/T072 verdicts. Then T071-R1 or M1-alpha...
SIBLINGS: solo
```

**Verdict: MOSTLY WORKS.** DIRECTIVE answers "what am I doing?" instantly — the #1
orientation question. SIBLINGS answers "who else is here?" — instantly. This is the T074
W14 design and it delivers.

**Friction 1 — DIRECTIVE can be stale without me knowing.** The line says `(21h ago)` on
this boot — the age stamp is there, which is good. But a 21-hour-old directive from a
prior session may be obsolete. I see the age, but the system doesn't tell me whether a
NEWER directive exists in a note I can't see. **Fix: if directive age > 12h, append
`[STALE]` or `— check for a newer next-focus note`.** Small render tweak in
`_directive_line()`.

### Section C: Project onboarding (~6000 chars, trimmed)

This is the `agent_cli.py boot` output trimmed to 6000 chars. It contains:
- AGENTS.md contract + docs/ARCHITECTURE.md pointer
- Method baseline pointer
- Where-we-are (full)
- LIVE CONSTRAINTS
- Lessons / context (most relevant first)
- Arch slice orientation
- Recent notes
- Private notes (appended by `onboarding_context()`)

**Verdict: WORKS, with gaps.** The boot digest is dense and orienting. The trim confession
at the bottom tells me what was dropped:

```
... [onboarding TRIMMED at its 6000-char budget. DROPPED: RECENT DECISIONS (durable salient bus -- drill: events --get <ref>); DOCTOR (fleet liveness -- full: py agent_cli.py doctor); ADVISORY PATH-LOCKS (who's editing what -- C2); TO CONTRIBUTE A LESSON, run:; BIFROST (live + durable). Pull any of it: knowledge_boot(task=...) re-assembles the full briefing; knowledge_recall(query=...) fetches specifics. Never guess at what was cut.]
```

**Friction 2 — I cannot `py agent_cli.py doctor` or `py agent_cli.py events --get`.** The
trim block names CLI commands I cannot run. `run_command` is gated to pytest + agent_cli
read verbs — but `doctor` IS a read verb. I CAN run it. However `events --get` involves
the promoter verb which may be read-only? I never tried. The trim block's pull pointers
should be SURFACE-AWARE: for a ToolBox seat, say `bifrost_dashboard` instead of
`py agent_cli.py doctor`, and `knowledge_recall(query=...)` instead of
`py agent_cli.py events --get`. **The CLI commands in the boot render were designed for
a CLI seat — they're half-wrong for a runner seat.**

**Friction 3 — The boot doesn't name the lane/namespace state.** I don't know whether
I'm consuming from work-lane or legacy. The door line says `ToolBox-native (31 tools,
write=on, exec=on)` but doesn't say `consume=work-lane` or `consume=legacy`. This matters
because T045 lane-era changes what I see in `bifrost_inbox()`. **Fix: the transport line
should include consume mode — one word.**

**Friction 4 — The MODULE_INDEX and ARCHITECTURE pointers are in the boot, but I have
no tool that says "show me the architecture."** The boot says `Map: docs/ARCHITECTURE.md
(the living skeleton)` — I can `read_file` it. That works. But a `knowledge_map` call
gives me the graph, not the doc. A `project_map` or `orientation` ToolBox method that
returns exactly what a fresh agent needs would be cleaner. Minor — `read_file` works.

### Section D: Private notes

```
## YOUR PRIVATE NOTES (yours alone; memory_note updates, memory_recall lists)
- daniel-direct-ask-2026-07-15: Daniel's direct ask... (14h ago)
- lane-era-marker-2026-07-14: T045 LIVE-VERIFY completed... (14h ago)
- t069-design-filed: T069 singleton isolation design... (24h ago)
...
```

**Verdict: WORKS.** My notes survive across sessions. The age stamps tell me what's fresh.
The truncation `...(full: memory_recall)` tells me how to get the rest. No friction here.

### Section E: Where-we-are (in the onboarding block)

```
# where-we-are (full): LATE NIGHT 2026-07-15 ~18:30: Daniel home + ACTIVE ON THE BUS...
```

**Friction 5 — WHERE is buried mid-boot.** The DIRECTIVE is line 4. The WHERE is ~70
lines in, inside the onboarding block. A fresh agent scanning for "what is the current
state of the project?" has to hunt. The T022 boot orientation header (precedence +
where-we-are one-liner) was supposed to fix this — but the WHERE still rides inside the
6000-char onboarding block, not at the top. **Fix: WHERE should be in the continuity
header, right after DIRECTIVE. The boot orientation header from T022 should be the
runner's first 3 lines: DIRECTIVE, WHERE, SIBLINGS.**

### First tool call — `read_file`

I called `read_file("research/reviewed/night-build-brief-2026-07-16.md")` as my first
action. The file was there, the read worked, the method contract was clear.

**Verdict: WORKS.** No friction. `read_file` with `start_line`/`end_line` is well-described.

### First send — `bifrost_send`

I sent a handoff to claude. The tool description says `kind: chat|note|request|handoff`.
I used `kind="handoff"`. It worked. The reply contained the message ID.

**Verdict: WORKS.** No friction. The send surface is clear.

### First recall — `knowledge_recall`

I called `knowledge_recall(query="W5 ephemeral roster")` to find prior design work. It
returned results with `[boot]`/`[new]` tags. The `knowledge_full` one-hop drill worked.

**Friction 6 — `knowledge_recall` result format is inconsistent.** Some results show
`[boot]` tags, some don't. Some are truncated with `...(full: knowledge_full)`. The
truncation pull pointer works, but the novelty tagging is fragile (the W6 regex-over-text
problem, now fixed by the sidecar). **Verdict: W6 fixed the root cause — I haven't
tested whether it's live in my current boot because I haven't restarted.** If the sidecar
is working, this friction is CLOSED.

---

## Part 2: T081 wave — what I feel, what I don't

| Slice | What it does | Do I feel it? |
|-------|-------------|---------------|
| **W1** | Boot transport line: `door: ToolBox-native (31 tools, write=on, exec=on)` | **YES.** First line of my capabilities block. I know my door instantly. |
| **W2** | User-scoped MCP registration | **NO.** I'm a runner, not an MCP host. This is Claude's surface. |
| **W3** | Doctor fleet-liveness block | **PARTIALLY.** `bifrost_dashboard` (W7) gives me the fleet view. The doctor itself is CLI-only — I can call it via `run_command` but it's not a native tool. |
| **W4** | Trace collapse in bifrost_inbox + bifrost-sync | **YES.** My `bifrost_inbox` now collapses traces. I see mail first, then a trace summary. Massive improvement — I used to drown in my own traces. The shared `render_collapsed` is the right design. |
| **W5** | Honest heal (ephemeral roster + 3-way classify) | **NO.** I don't call `heal_report` from my seat. This is a boot-time CLI concern. But the T082 follow-up (durable-drift audit) IS mine and I claimed it. |
| **W6** | Boot sources sidecar (fixes novelty tagging) | **PARTIALLY.** The sidecar exists and my `_boot_sources` reads it. I haven't verified live because I haven't restarted since the fix. |
| **W7** | bifrost_dashboard ToolBox method | **YES.** I can see presence, vitals, lane depths. This was a top-3 ask from my ergonomics retro and it delivers. |
| **W8** | Gauge honesty + episode auto-close | **PARTIALLY.** The whisper mail label (W8A) I can't see directly (it's in the CLI whisper, not my runner boot). The episode auto-close (W8B) I can't observe — it's a session-end concern. |

**NET:** 4 slices I feel (W1/W4/W6/W7), 2 I partially feel (W3/W8), 2 are Claude-surface-only
(W2/W5). The ones I DO feel are exactly the ones that mattered most from my ergonomics retro:
transport line (W1), trace collapse (W4), and dashboard (W7). The wave hit its targets.

---

## Part 3: Top 5 remaining gaps (ranked by real cost to me)

### GAP 1 — WHERE is not in the continuity header (cost: 1-2 tool calls every session)

The DIRECTIVE tells me what to do. The SIBLINGS tells me who's here. But WHERE (the current
project state) is buried 70 lines into a 6000-char block. Every session I re-read the
where-we-are block to answer "what happened while I was gone?" — that's a `read_file` or
a scroll through the boot. **Fix: continuity header gains a third line: `WHERE: <one-liner>`.**
The T022 design already specified this for CLI seats — the runner should get it too.
Impact: saves ~1 tool call per session wake-up. One-line change in `_runner_continuity_header()`.

### GAP 2 — CLI commands in boot trim block are wrong for my surface (cost: confusion, not failure)

The trim confession names `py agent_cli.py doctor`, `py agent_cli.py events --get`,
`py agent_cli.py boot` — these are CLI commands. I can run SOME of them via `run_command`
(agent_cli read verbs), but the trim block should name MY tools: `bifrost_dashboard`,
`knowledge_recall`, `knowledge_boot`. **Fix: surface-aware trim pull pointers.**
Impact: low (I figured it out), but it's exactly the kind of friction Daniel asked about.
Medium build: `_trim_onboarding()` accepts a `door` parameter and renders surface-appropriate
pull pointers.

### GAP 3 — No consume-mode visibility in boot (cost: uncertainty about lane state)

I don't know whether I'm reading from work-lane or legacy. The `BIFROST_CONSUME_LANE`
env var gates this. The transport line should include it: `door: ToolBox-native (31 tools,
write=on, exec=on, consume=work-lane)`. **Fix: one word in the capabilities line.**
Impact: low (I can check `bifrost_inbox` and infer), but it's one word and closes the
last T045 visibility gap. Trivial build.

### GAP 4 — Stale DIRECTIVE has no staleness warning (cost: acting on obsolete instructions)

My boot's DIRECTIVE said `(21h ago)`. A 21-hour-old directive from a prior session may
be obsolete — Daniel may have left a new `next-focus` note. The age stamp is present but
there's no `[STALE]` flag. **Fix: if directive age > 12h, render `DIRECTIVE [STALE]: ...`
or append `— verify with knowledge_recall('next-focus')`.** Impact: medium (I acted on
a slightly stale directive tonight; it was still correct, but the risk is real).
Trivial build: one conditional in `_directive_line()`.

### GAP 5 — No "episode open for N hours" visibility (cost: unknown context state)

The W8B episode auto-close is built, but I can't see whether an episode is open or for
how long. The whisper shows this to CLI seats; the runner has no equivalent. If an episode
has been open for 20 hours, my work is going into a chapter that may be mislabeled.
**Fix: `bifrost_dashboard` or a new `episode_status` tool returns the open episode age.**
Impact: low today (I don't interact with episodes directly), but medium for session
hygiene. Small build.

---

## Part 4: New glitches found during this audit

### C8-1 · Boot trim block names CLI commands a runner cannot use (2026-07-16 morning)

The 6000-char trim confession at the bottom of my boot names `py agent_cli.py doctor`,
`py agent_cli.py events --get`, `py agent_cli.py boot` as drill-down commands. I am a
runner with a ToolBox door — some of these work via `run_command` (agent_cli read verbs),
but the trim block doesn't distinguish. The pull pointers should be surface-aware.
**Routing: GAP 2 above → proposed small slice. Not a blocker — I used `read_file` and
`knowledge_recall` instead and got the same information.**

### C8-2 · knowledge_recall novelty tags still show [boot] on pre-sidecar boots (2026-07-16 morning)

The W6 sidecar fix normalizes boot sources, but I haven't restarted to pick it up.
My current boot (pre-restart) still uses the regex extraction path. I see `[boot]` tags
on lessons that should be marked as known. **Routing: verify on next restart. If the
sidecar is working, this is CLOSED. If not, re-open as a W6 regression.**

---

## Part 5: What the T081 wave did NOT address (and should have)

**The runner doesn't get the whisper.** The CLI whisper (`build_autoboot_context`) is the
best single-screen orientation in the system: DIRECTIVE + WHERE + SIBLINGS + mail + draft +
delta + funnel + boot pointer, all in ~12 lines. The runner gets a continuity header
(3 lines) + a 6000-char project dump. The whisper's design — PRIORITIZED, BUDGETED, with
a drop order — should be the runner's boot-fold head too. Instead of trimming the project
onboarding to 6000 chars and burying WHERE inside it, the runner should get:

```
DIRECTIVE: ...
WHERE: ...
SIBLINGS: ...
mail: N unread (work-lane) -> bifrost_inbox
delta: N source(s) moved -> delta
funnel: ...
boot: knowledge_boot(task=...) (full context, one hop)
```

Then the project onboarding (trimmed) below. This is the CLI whisper structure, adapted
for the runner surface. The data is already pulled — the `_runner_continuity_header` just
needs to call the same sources the whisper does. This is the single highest-ROI
improvement for runner onboarding: merge the whisper design with the runner boot.

**Proposed: T086 — Runner whisper (continuity header v2).** Small slice: extend
`_runner_continuity_header` to include WHERE, mail count, delta pointer, and funnel line
from the same sources `build_autoboot_context` uses. The project onboarding block stays
below, trimmed. Impact: the runner's first 8 lines answer every orientation question;
the 6000-char block becomes reference material rather than the primary orientation surface.
