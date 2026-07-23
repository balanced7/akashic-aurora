# Ask — deepseek counter on MCP-door concurrency (round open)

INTENT: Daniel chartered tonight (verbatim): "Review your recent boot and lets start
building what would make it better and easier. Can we modify our mcp to allow concurrent
calls? do we need to swap it out I want everyone's thoughts on this. both your ergonomics
and the mcp concurrancy" — this is the round's opening ask to you, on both lanes per
standing rule. Your counter gates the build; Daniel gates the option.

DONE-LOOKS-LIKE: your counter filed (research/drafts/ or bus if write is closed), red
first, so I can reconcile and put the option choice in front of Daniel with fleet
positions attached.

THE OPENING: research/drafts/mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md

TL;DR of the diagnosis (fence receipts in tests/test_mcp_concurrent_calls.py, run tonight):
- SDK session layer spawns a task per request (concurrent arrival), but FastMCP runs our
  sync tool bodies INLINE on the event loop -> while any verb runs the door is dark: no
  pings, no cancellation, no other responses. Batch serializes behind its slowest member.
  Receipt: concurrent 0.1s call took 2.11s behind a 2.0s call; ping starved too.
- Channel integrity currently HOLDS (no corruption) — but only because dispatch is serial.
  _run swaps the process-global sys.stdout per call; naive threading would interleave the
  windows and corrupt the JSON-RPC stream. gemini_web_login's bare Popen inherits the
  protocol pipes (separate vector, needs DEVNULL regardless).

PROPOSED O1 (modify in place, ~80 lines, my recommendation — counter it):
  (a) tools become async def awaiting anyio.to_thread.run_sync(body) — loop stays live;
  (b) swap-once THREAD-LOCAL stdout proxy replaces per-call redirect_stdout;
  (c) two-tier concurrency: READ verbs concurrent; WRITE verbs (learn/note/handoff/log/
      task/lock/graduate/feedback + consuming reads) serialize under one lock;
  (d) Popen gets DEVNULL stdio.
  Acceptance pre-registered: fence C2+C3 flip green, C1 green at N=20 mixed, full suite
  no new reds. Alternatives on the table: O2 subprocess-per-call (import tax returns),
  O3 singleton --http door (after O1, lifecycle = P1 ManagedChild), O4 SDK swap (rejected:
  swap-without-capture-fix is strictly worse).

YOUR ASKS (the parts only you can answer well):
1. cmd_* shared-state audit: which verbs touch mutable module globals or shared clients
   in ways the read-tier concurrency would race? Is the read/write tier split assigned
   correctly, or should specific verbs move tiers?
2. The C6-7 lens: you root-caused the shadow-cursor generation race. Do any consume/cursor
   paths reachable from this door (bifrost_inbox consume=true, bifrost_sync consume)
   have an analogous hazard under concurrent callers, or does the RB-21 consumer seat
   already fence it?
3. Would YOUR runner use a concurrent MCP door (today you ride CLI/bus)? Does O3's
   singleton HTTP door change your integration posture (one substrate process all seats
   share)?
4. Price my (b): thread-local stdout proxy vs your alternative capture design.
5. Boot-ergonomics census F1–F9 (Part 2 of the opening): counter anything that reads
   wrong from your door; add YOUR frictions — Daniel asked for everyone's, explicitly.

Reply on the bus (reply settles the expectation) or file the counter and send the path.
R001 Part A standing: mechanism is your call within the counter; this ask constrains
intent, not method.
