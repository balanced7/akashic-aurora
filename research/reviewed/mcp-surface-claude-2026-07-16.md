# MCP Surface — Empirical Half (claude probe seat) — 2026-07-16 night

Status: FILED. The empirical half of the joint MCP reverse-engineering (Daniel directive:
understand the surface fully — inputs, outputs, specs, data types — BEFORE fixing C7-4).
Twin: research/reviewed/mcp-surface-deepseek-2026-07-16.md (code+spec half, in flight,
BLIND to this file until filed). Probe drivers + servers preserved in the session scratchpad;
reproduce-anywhere versions should be committed with the fix slice.

## 0. Environment facts

- Server: `ai_setup_mcp.py` — FastMCP (`mcp.server.fastmcp`), stdio transport, spawned by
  Claude Code as `py E:\AI-Setup\ai_setup_mcp.py` (two py processes: launcher + python).
- SDK: `mcp` **1.27.0** (site-packages, Python 3.11, Windows 11). Upstream has 1.27.1,
  1.27.2, 1.28.0, **1.28.1** — an upgrade test is cheap but LOW priority now (see §3: the
  SDK is exonerated in isolation).
- Protocol observed: JSON-RPC 2.0, newline-delimited, one message per line. Handshake:
  `initialize` (answered 0.5s with serverInfo/capabilities/instructions) →
  `notifications/initialized` → normal traffic. `tools/list` returns the full 20+ tool
  catalog (21,858 bytes, instant).

## 1. Probe method

Fresh server instance per scenario, spawned with pipes; BOTH stdout and stderr actively
drained by daemon pump threads (rules out the T019 undrained-pipe wedge class on the probe
side); requests hand-framed JSON-RPC lines; response arrival timed to ±0.5s.

## 2. The observed defect (C7-4), fully characterized

| # | Call | Work completes? | Response arrives? |
|---|------|-----------------|-------------------|
| 1 | `tools/call status` | ~0.1s | **+0.12s — instant** |
| 2 | `tools/call recall {query:""}` (7,625 B) | ~0.03s | **instant** |
| 3 | `tools/call boot` (19–21 KB result) | yes — agent-init logs + heal lines on stderr at +1–3s | **NEVER within any silent window tested (45s, 90s)** |
| 4 | `tools/list` after unstick (21,858 B — BIGGER than boot's) | — | **instant** |
| 5 | any request/notification sent while boot's response is stuck | — | boot's stuck response flushes in **≤0.07s**, THEN the new message processes |

The unstick receipt (repro3, deterministic 2/2 in one session): boot#1 work done +2.9s,
response stuck 14s, **bare `notifications/initialized` (a frame that produces NO response
of its own) sent at +17.00s → boot's response lands +17.07s**. boot#2 identical (+22s /
+37.07s). Per-message behavior, not one-time state.

**The law: after `cmd_boot` runs in-process, the server's pending outbound response is
written/flushed ONLY when the next inbound stdin frame arrives.** The server is otherwise
healthy: later requests answer instantly (right after they first flush the stuck one).

Why the live harness hangs 30 minutes: Claude Code sends ONE `tools/call boot` and then
waits silently — no further inbound frames on that server → the response never flushes →
client timeout. Probe receipts across agents: claude (22:11 live), claude-probe3 (×2,
warm+cold), probe4–7 tonight. Side effect for forensics: **every wedged boot still logs a
real `boot` event to the ledger** — phantom boots pollute that series.

## 3. The exoneration chain (what it is NOT)

1. **NOT the SDK alone**: hello-world FastMCP server (zero Aurora imports), `slow_tool` =
   `time.sleep(5)` + return — response arrives the moment work completes. Same machine,
   same Python, same mcp 1.27.0. (repro4)
2. **NOT payload size**: `tools/list` 21.9 KB and `recall` 7.6 KB flow instantly; boot's
   21.0 KB wedges. `redirect_only` returning 42 KB flows instantly. (repro2/5)
3. **NOT the `_run` mechanics**: on a server that HAS imported `agent_cli` + `ai_setup_mcp`
   (all import side effects loaded), a tool doing exactly `redirect_stdout(StringIO)` +
   `sleep(2)` + 21 KB print answers instantly. Import-time side effects exonerated too. (repro5)
4. **NOT tool duration**: the 5s sleep tool is slower than cmd_boot's ~1–3s work and does
   not wedge. (repro4)
5. **NOT pipe drainage, NOT server death, NOT agent identity, NOT Redis reachability**
   (status/recall touch Redis fine; every probe agent id reproduces).

**Therefore: a RUNTIME side effect inside `cmd_boot`'s work** — something it does while
executing (not while being imported, not how its output is captured) leaves the server's
outbound writer parked until inbound activity wakes it. (repro5: `boot_real` through the
verbatim `ai_setup_mcp._run` wedges; everything else on the same server doesn't.)

## 4. Suspect space for the joint bisect (empirical shapes, not conclusions)

The writer-parked-but-loop-answers-inbound signature points at something cmd_boot does that
interferes with event-loop/worker scheduling or the stdio writer's wakeup. Phase bisect
along the code map (deepseek's half) is the next step: run `cmd_boot` with phases disabled
one at a time under the mixed-server driver. Candidate phase classes to bisect first:
anything that (a) spawns subprocesses (handle inheritance on Windows), (b) starts threads
or touches asyncio/event-loop state from the worker thread, (c) reconfigures
logging/rich/global streams, (d) installs signal/atexit handlers.

## 5. Operational implications (already true today)

- MCP `boot()` is UNUSABLE from a silent single-call client until fixed — CLI door for boot
  (345ms); the other read verbs are fine over MCP (status/recall/notes/tools-list receipts).
- T081-W2 (user-scope MCP apply) stays GATED on this fix (routing already in C7-4).
- Any future MCP tool that reproduces cmd_boot-class side effects will wedge the same way;
  the fix slice must land a REGRESSION PIN: drive the real server over stdio, call boot,
  assert response < Ns with NO second inbound frame (the repro driver is 90% of that pin).
- Open question for the twin/reconcile: do `_run_script` subprocess tools (ask_gemini_web,
  240s) wedge? Untested tonight (would fire Chrome). Their `capture_output=True` pipes are
  fresh (no fd1 inheritance), but the duration point is moot given §3.4 — test in the fix
  slice, not before.

## 6. Fix design space (deliberately NOT chosen yet — understand-first directive)

Ranked only as shapes: (1) remove/guard the specific cmd_boot side effect (root fix, pending
bisect); (2) if the side effect is load-bearing for CLI boot, split render: MCP boot calls a
side-effect-free boot core; (3) LAST resort: subprocess-door boot (`_run_script` pattern) —
works today, but hides the class instead of closing it (fix-root-causes doctrine says no
until the mechanism is NAMED; acceptable only as an interim with the root cause documented).
Upstream SDK upgrade: low-priority falsification run (SDK exonerated in isolation, but a
newer SDK may coincidentally mask — knowing WHICH would still matter).
