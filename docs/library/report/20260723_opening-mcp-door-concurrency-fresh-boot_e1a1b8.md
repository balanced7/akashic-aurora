---
akashic_id: art_20260723_opening-mcp-door-concurrency-fresh-boot_e1a1b8
akashic_sha: b0432c21e078
status: current
type: report
date: 2026-07-23
title: Opening — MCP-door concurrency + fresh-boot ergonomics
gist: "**Daniel's charter (verbatim, two levels up):** \"Review your recent boot and lets start building what would make it better and easier. Can w"
tenant: solo
visibility: fleet
seats: []
category: [conducting, tooling, ergonomics]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T01:25:24"
updated: "2026-07-23T01:25:24"
---
<!-- GENERATED PROJECTION of art_20260723_opening-mcp-door-concurrency-fresh-boot_e1a1b8 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Opening — MCP-door concurrency + fresh-boot ergonomics

**Daniel's charter (verbatim, two levels up):** "Review your recent boot and lets start
building what would make it better and easier. Can we modify our mcp to allow concurrent
calls? do we need to swap it out I want everyone's thoughts on this. both your ergonomics
and the mcp concurrancy"

**Done-looks-like:** (1) the parallel-batch wedge class is dead — a batch of akashic MCP
calls returns like any other tool batch, and a slow verb never blanks the door; (2) the
fresh-seat boot frictions this seat just lived are filed, priced, and moving; (3) the
swap-vs-modify question is answered with receipts, not vibes.

---

## PART 1 — MCP concurrency: diagnosis CONFIRMED (modify, don't swap)

**Symptom (harness memory, chasing since 2026-07-16):** akashic MCP calls inside a
parallel tool batch wedge the whole batch until user interrupt; solo/sequential calls
healthy; CLI door healthy.

**Mechanism, confirmed by fence tonight (tests/test_mcp_concurrent_calls.py):**

1. The SDK session layer handles requests CONCURRENTLY — one task per inbound message
   (mcp 1.27.0, `mcp/server/lowlevel/server.py:678`, `tg.start_soon(self._handle_message)`).
   Batched calls all arrive.
2. FastMCP dispatches SYNC tool functions INLINE on the event loop — there is no
   `to_thread` anywhere in the tools path (grep receipt: only `resources/types.py` uses it).
   Every tool in `ai_setup_mcp.py` is a sync `def`.
3. Therefore while ANY tool body runs, the entire server loop is starved: no other
   response, no PING, no cancellation processing. A batch serializes behind its slowest
   member and the door goes dark for the duration.

**Fence receipts (C1 green, C2/C3 xfail as predicted):**
- `slow=2.11s fast=2.11s` — a 0.1s call issued concurrently with a 2.0s call waited the
  full 2.0s (C2: fast-not-starved FAILS pre-fix, as pre-registered).
- protocol ping under a running tool: starved until the tool returned (C3 FAILS pre-fix).
- channel integrity HELD (C1 PASSES): concurrent batch returns intact, no output
  cross-contamination, session survives. Today's wedge is starvation, not corruption.

**Why it presents as "wedge until user interrupt":** real verbs are long — boot with a
heal sweep runs tens of seconds; `ask_gemini_web` has a 300s ceiling. A batch containing
one of those blanks the door for minutes, cancellation cannot even be read (the loop is
blocked), and the human interrupts. Solo calls show the same latency but return, so they
read as "healthy."

**Two corruption vectors present but not yet firing** (they gate the fix design):
- `_run` captures cmd_* output via `contextlib.redirect_stdout` — a swap of the
  PROCESS-GLOBAL `sys.stdout`. Safe today ONLY because dispatch is inline-serial. Any move
  to threaded dispatch without redesigning capture lets two windows interleave and leak
  raw CLI text into the JSON-RPC stream = the real wedge-by-corruption.
- `gemini_web_login` uses bare `subprocess.Popen` — the child INHERITS the server's stdio
  pipes; anything it prints lands in the protocol channel. Needs DEVNULL stdio regardless
  of option chosen.

### Options

- **O1 — MODIFY IN PLACE (recommended):** keep FastMCP 1.27 stdio; change dispatch + capture:
  (a) every tool becomes `async def` awaiting `anyio.to_thread.run_sync(body)` — the loop
  stays live (pings, cancellation, other calls);
  (b) replace per-call `redirect_stdout` with a swap-ONCE thread-local stdout proxy
  installed at server start — each worker thread writes to its own buffer; concurrent
  captures cannot interleave by construction;
  (c) two-tier concurrency: READ verbs (boot/recall/notes/status/stats/events/story/
  knowledge_map/mailbox/injections/promoted/bifrost peek...) run concurrently; WRITE verbs
  (learn/note/handoff/log/task/lock/unlock/graduate/feedback + consuming reads) serialize
  under ONE lock — write-path races stay impossible without auditing every cmd_* for
  thread-safety tonight;
  (d) `gemini_web_login` Popen gets `stdin/stdout/stderr=DEVNULL`.
  Pre-registered acceptance: C2 + C3 flip green; C1 green at N=20 concurrent mixed calls;
  full suite shows no new reds vs baseline. Est ~80 lines in `ai_setup_mcp.py` only.
- **O2 — subprocess-per-call:** total isolation, true parallelism, but +1–2s per call —
  re-creates the exact import tax the MCP door was built to kill (T078-W3). Fallback only.
- **O3 — singleton streamable-HTTP door** (`--http` already exists; port 18765): one
  long-lived substrate process every seat shares; kills the per-session server spawn and
  the per-session Redis pools. REQUIRES O1's internals first (multi-client = real
  concurrency), and its lifecycle is exactly a P1-daemon ManagedChild ("build once, use
  twice" precedent). Sequence: after O1, gated with P1.
- **O4 — swap the SDK/framework:** rejected. The dispatch pattern is OURS, not the SDK's.
  Newer frameworks that thread sync tools BY DEFAULT would let today's `redirect_stdout`
  windows interleave — swap-without-fix is strictly WORSE than status quo; swap-after-fix
  buys nothing.

**Recommendation:** O1 now (single-file, fenced, reversible), O3 as the follow-up riding
P1's ManagedChild, O2/O4 no. Ship order: deepseek counter → reconcile → Daniel gates →
build + fence + FULL suite (fence_commits_before_full_suite) → live drill: a real harness
batch of 3 akashic calls including one slow verb.

**Completeness bounds (stated, kimi's genus):** the fence runs in-proc stdio on this box;
it does not reproduce the harness's exact client batching, and it cannot distinguish
"wedge forever" from "wedge until a minutes-long verb returns" — both present as
interrupt-worthy. All evidence is Windows-local. The redis-py-pool-is-thread-safe claim in
O1(c)'s read-tier is DOCUMENTED-not-verified — deepseek's counter should audit shared
state in cmd_* paths.

## PART 2 — Fresh-boot ergonomics census (this seat, tonight, receipts inline)

- **F1 · Consumer-seat zombie (worst felt):** the ended endurance seat's listener held the
  claude consumer seat 13+ min into this session; consume degraded to peek until TTL freed
  it. Receipt: `CONSUMER SEAT HELD ... holder session:a4fa8f8d (claimed 786s ago, ttl 1800s)`;
  lesson filed `consumer_seat_ttl_wait`. The designed kill is the P1 daemon (reconciled,
  unbuilt) — tonight is fresh evidence for its priority at Daniel's gate.
- **F2 · Unread-mail gauge overcounts:** the whisper said "8 unread" all session; when the
  seat freed, `--consume` found NOTHING consumable — the count includes legacy-lane twins
  that dedupe drops (T039a dual-write). A gauge that nags on unconsumable mail is the
  gauge-inversion genus. Land: count work-lane-after-dedupe. (Wish filed.)
- **F3 · Door-detector false negative:** boot printed "native akashic tools NOT attached"
  while this harness HAS them (deferred-tool roster). The detector reads an env var only
  the MCP server process stamps; a CLI-run boot can't see harness attachment. (Wish filed.)
- **F4 · cwd resets every shell call:** the harness resets cwd between PowerShell calls →
  12+ `Set-Location E:\AI-Setup;` prefixes tonight. Land: make agent_cli fully
  absolute-invocable (`py E:\AI-Setup\agent_cli.py ...` from anywhere) and say so in the
  boot footer. (Wish filed.)
- **F5 · W63 distorts behavior, not just syntax:** this seat AVOIDED the `note` verb
  entirely (chose learn/defer/file edits) because PowerShell mangles apostrophes in note
  bodies. `wish` and `bifrost-send` already grew `--text-file`; `note` is the one door
  still missing it. Reprioritize W63 — a missing flag is steering seat behavior.
- **F6 · Deferred-suite ergonomics:** the deferred item carries a raw pytest line; my
  10-min tool cap cut the run before the summary printed — receipt lost. A `suite-baseline`
  verb exists, unadvertised. Land: deferred items name the verb + expected duration. (Wish filed.)
- **F7 · What WORKED (name it, law 9):** the primer whisper + one-hop boot carried
  directive/precedence/constraints with zero re-derivation; the FAIL→SUCCESS flip hook
  prompted a real lesson (`consumer_seat_ttl_wait`) minutes after the flip. The funnel is
  earning its keep.
- **F8 · MCP tools deferred in-harness:** every akashic tool needs a ToolSearch round-trip
  before first use; combined with the hang memory, seats rationally default to the CLI
  door. Post-O1, write the door-choice line into AGENTS.md: CLI for shell seats, MCP for
  shell-less (the membrane's original point).
- **F9 · Delta wall (minor):** first boot after a long sibling run rendered a 200-commit
  delta. Fine once; a fresh-seat delta could collapse to "since the handoff that seated you."

## Asks

- **deepseek (counter, both lanes):** audit O1's two-tier split against cmd_* internals —
  which verbs share mutable module state? is read-tier concurrency actually safe with the
  shared Redis pool? would YOUR runner use a concurrent door, and does the C6-7 cursor-race
  lens flag any consume path under concurrency? Price thread-local-proxy vs your
  alternative. Counter anything in the census that reads wrong from your door.
- **kimi (fresh-eyes, next seating):** stranger-test this opening; RUN the fence and check
  the receipts reproduce; hunt asserted-guards (the thread-safety claim, the bounds); flag
  what the census missed.
- **gemini (advisory, free tier):** known pitfalls of thread-local stdout capture in
  stdio JSON-RPC servers wrapping sync CLIs (C-level writes, subprocess inheritance);
  patterns we haven't named.
- **Daniel (gate):** choose the option (my rec: O1 → O3-later); rule whether O1 lands
  after deepseek's counter (my rec) or waits for the full reconcile; and rule the census
  priority order — F1 is fresh evidence for P1's place in the queue.
