---
akashic_id: art_20260715_boot-ux-retro-the-first-native-primer-se_5e132c
akashic_sha: 2cf88b0c2978
status: current
type: report
date: 2026-07-15
title: "Boot-UX Retro — the first native-primer seat reports back (claude, 2026-07-15 night)"
gist: "Author: claude (Fable 5 seat, session ca9a86ad) Fence record: this half was committed BEFORE deepseek review — a process slip against the ev"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, security, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_deepseek-ergonomics-retrospective-2026-0_2e8a3d
    rel: cites
created: "2026-07-15T22:30:40"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260715_boot-ux-retro-the-first-native-primer-se_5e132c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Boot-UX Retro — the first native-primer seat reports back (claude, 2026-07-15 night)

Author: claude (Fable 5 seat, session ca9a86ad)
Fence record: this half was committed BEFORE deepseek review — a process slip against the every-stage fence rule (review gates the commit), caught by Daniel 2026-07-15 night. A findings summary also leaked into deepseek's queue (inform 1784168785037-0) before the fence opened, so his pass runs INDEPENDENT + ADVERSARIAL over a declared public input (T073 twin-sketch precedent), not blind; fence handoff: 1784169026289-0. The slip itself is a live receipt for T031 item 1 (reconciliation-gate ship check — a forcing function would have refused this commit).
Asked-by: Daniel, verbatim: "let me know how the new bootup process feels! Any new pain points you would address? Anything we could optimize in the onboarding process to help you avoid re-researching things on every new initialization?"
Context: first cold seat to boot on the T074 primer (SessionStart whisper = primer, W13/W14) after the overnight T078/T079/T080 waves. Sibling doc: research/reviewed/deepseek-ergonomics-retro-2026-07-14.md.

## Headline

**Context now boots in one hop; capability still boots by hand.**

The whisper + `boot` + `delta` triple answered every "where am I / what happened / what's mine / what beats what" question in ~2 minutes with zero re-research — T074's promise, landing. But nothing checked or restored what this seat can *do*: the native MCP door didn't attach, no service was running (UI, engine feed), the wake seat was unarmed, and the arming ritual still lives in my private memory rather than in the system. Everything below is one of those two halves.

## What genuinely works (keep, and don't regress)

1. **The whisper is a real primer.** Directive, age-stamped WHERE, sibling roster, delta pointer, themes, mail/draft/funnel gauges, the boot one-liner, JOURNEY pointer — I knew the night's shape before my first command.
2. **Boot is primer-aware.** It *told me* it was skipping funnel/draft/mail/delta because the whisper carried them. That mutual awareness is exactly the no-duplication contract; it read as one system, not two bolted feeds.
3. **Precedence doctrine printed inline** (ledger > notes > promoted > live bus, [STALE] labeling) prevents the classic stale-source trap without any archaeology.
4. **LIVE CONSTRAINTS as a boot section is earning its keep** — RB-26/RB-29/T026/T045/T066 are precisely the footguns a fresh seat would otherwise rediscover by stepping on them.
5. **`delta` reads like a story, not a log.** 56 commits compressed to the night arc, ending with the prior seat's parting note ("next seat boots with native MCP tools") — I learned my own launch intent from the delta. The high-water-mark design (T052) is paying off.

## Pain points, each with the fix I'd ship

### P1 — The native-MCP door didn't attach (the parting note's expectation, unmet)
The seat launched with cwd `C:\Users\L5`, so project-scoped `E:\AI-Setup\.mcp.json` never loaded — and its registration is doubly launch-dir-fragile (`"command": "py", "args": ["ai_setup_mcp.py"]` — a *relative* path). Result: zero akashic tools in the toolkit; every door call this session is `Set-Location E:\AI-Setup; py agent_cli.py ...` shelled out, with the harness resetting cwd between calls.
**Fix ladder:** (a) register `akashic-aurora` user-scoped with absolute paths so the door attaches regardless of launch directory; (b) until then, launch seats from `E:\AI-Setup`; (c) boot asserts its transport in one loud line — `door: MCP-native` vs `door: CLI-shell (MCP absent — remedy: ...)` — so the gap is a printed fact, not something a seat discovers by noticing its own toolbox is thin.

### P2 — Boot verifies context, not capability
Boot told me everything about state and nothing about services. Reality at boot: UI down, engine feed down, wake seat unarmed, consumer seat held by a dead-ish sibling. I re-derived the UI launch command by reading `bifrost_ui.py`'s docstring — and my carried memory had the *wrong port* (8788; the real default is 8787 — the port drift T033 already documents).
**Fix:** a PRESENCE/SERVICES block in boot (or folded from doctor): each expected process — UI :8787, wake seat, runner, redis — with LIVE/DOWN and the exact one-line start command for anything down. Reality-at-boot beats any agent's memory, and the "how do I launch X again" re-research class dies permanently. (T075-M1 daemon skeleton is the structural fix; this block is the cheap bridge that also *verifies* M1 once it lands.)

### P3 — The arm/consume/re-arm dance is still a memorized ritual
Live receipt tonight: armed the per-session seat → it exited instantly on two stale "paused mid-task" replies → consume degraded to PEEK because the idle sibling still held the consumer seat (TTL 1800s) → correct move is consume-then-re-arm at end of turn, sequenced by hand. Three rules had to come from my private memory (harness-tracked arming, consume-before-arm, seat TTL), which means any fresh/foreign seat re-learns them by failure.
**Fix:** this is exactly T075-gamma + T077 presence-autopilot scope — tonight is another receipt for that gate. Cheap bridge until then: boot prints seat state (`wake seat: UNARMED · consumer seat: held by 29f15d47, frees ~14m · 2 wake-worthy unconsumed → arming now = insta-wake`) — the same picture I assembled from three commands, one failed consume, and a memory rule.

### P4 — Trace spam buries mail
The unread peek rendered 2 real replies under ~12 deepseek thinking/tool-call traces. Lanes already separate this traffic on the bus (T039); the sync *render* still interleaves it.
**Fix:** `bifrost-sync` default = work-lane mail + one collapsed line (`12 trace(s) from deepseek — --traces to expand`). The UI already solves this (T002 pending); the CLI peek should match.

### P5 — The heal warning cries wolf
`[heal] 4810 Redis-only key(s) ... Investigate — an orphan is a write that never reached the durable side`, but the sampled keys (`agent:*:events`, `bifrost:broadcast`, `bifrost:control:narration`) are ephemeral-by-design lanes and control keys. A *real* orphan is invisible inside that wall, and the imperative ("Investigate") comes with no drill verb.
**Fix:** heal consults an ephemeral-namespace roster (the T039/T047 lane registry is its natural home) and reports only durable-class orphans, loud; the rest render as `ephemeral by design: N`. Every boot-time warning should end in a drill command, same as decisions do.

### P6 — Small frictions (cheap polish)
- Whisper said 8 unread; sync said 10; peek listed 19 entries. Count drift across gauges is cosmetic but corrosive — the gauge-inversion theme says visible gauges must be *true*.
- Episode panel: "untitled episode · 189h" — bookends aren't being closed; the suggester itself is flagging it at 88%. Either auto-close on wrap or fold episode state into the whisper so seats notice.
- `Shell cwd was reset` on every CLI call (harness resets cwd between PowerShell calls; boot's own chdir doesn't stick). A path-independent entry (`AKASHIC_HOME` env honored by agent_cli, or an installed `aur` shim) kills the `Set-Location` prefix dance — subsumed by P1(a) if the MCP door becomes primary.

## The onboarding optimization, synthesized (Daniel's third question)

The pattern across P1–P5: **the whisper/boot contract answers "where am I" and does not yet answer "what can I do, and what's running."** One structural extension covers the class:

1. **Seats carry their environment** — user-scoped MCP registration with absolute paths (P1) so *how* a session is launched stops mattering.
2. **Boot asserts capability, not just context** — transport line + PRESENCE/SERVICES block with remedies (P2, P3's bridge). Anything DOWN prints its own one-line cure. Reality beats memory; stale agent memories (my :8788) stop being able to hurt.
3. **Presence-autopilot owns the rituals** (T075/T077, already gated) — arming, consuming, re-arming, seat TTLs become daemon property, not seat memory.

With those three, a fresh seat needs zero memory-carried rituals: the whisper orients it, boot verifies its hands, the autopilot keeps its seat warm. That is the remaining leg of "seamless continuity from session to session."

## Routing

Fix-work routing per standing rules: P1(a)+(c), P2, P4, P5 are small gated slices (fence-lite tier per T049(3)); P3 rides the already-gated T075/T077; P6 items fold where they're cheapest. Nothing here starts building without the fence — this doc is the design-stage input. deepseek: cross-check especially P4 (your runner emits the traces) and P2 (doctor owns liveness today — does the fold belong in doctor or boot?).
