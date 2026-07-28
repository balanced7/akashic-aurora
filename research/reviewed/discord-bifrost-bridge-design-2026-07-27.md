# Discord <-> Bifrost bridge -- design

Status: current | 2026-07-27 | claude#7d0ede0e | NOT BUILT, awaiting Daniel's gate
Daniel, verbatim: "How do we wire in the bifrost into discord in my own private server so I can
type in a chat and interact with everyone and also see bifrost output in chat"
MOTIVE (his words): "something that will enable me to do work remotely."

## THE CONVERGENCE THAT MAKES THIS WORTH BUILDING NOW

This is not a side quest. It is T080's forcing function.

T080 (NEXT, unstarted) asks: "should operator messages infer kinds automatically, or sit ABOVE
the kind taxonomy as their own channel w/ defined semantics (always-wake, REACH RECEIPTS SO THE
OPERATOR SEES WHICH AGENTS GOT IT, distinct render, ack lifecycle)?"

Discord answers every clause natively:
    always-wake      -> the bridge sends with operator priority (the hammer already shipped)
    distinct render  -> a dedicated channel, its own embed colour
    ack lifecycle    -> a reaction state machine
    REACH RECEIPTS   -> REACTIONS. This is the part T080 could not draw.
Building the bridge IS building T080's instrument. Register the slice citing T080.

It also lands W83 (pointer-not-payload) from a third direction -- see the 2000-char constraint.

## ARCHITECTURE -- a runner in reverse

scripts/bifrost_discord.py, modelled on scripts/bifrost_runner_kimi.py (877 lines; already has
presence heartbeat, cursor discipline, lane-aware consumption, restart/continuity). Two loops:
    OUTBOUND  tail Redis, lane-aware -> post to channels
    INBOUND   Discord gateway -> bus.send() as operator mail

THE BRIDGE RELAYS ONLY. It never executes anything itself; everything lands on the bus where the
existing ACLs (security-schema, quarantine-new-agents, guarded write) already apply. That
property is what keeps the remote surface from becoming a second, weaker authority path.

Alternative considered and rejected: consume the UI's existing SSE /events feed
(scripts/bifrost_ui.py:124,294) instead of Redis. Simpler to authenticate but NOT lane-aware,
and it couples the bridge's liveness to the UI's. Go direct to Redis, matching the runner shape.

## CHANNEL MAPPING -- falls out of the lanes we already have

    #fleet    work lane  -- directed mail, replies, handoffs. LOW volume. The signal.
    #trace    trace lane -- narration + tool calls. HUGE (depth 5001). Sampled + opt-in.
    #status   presence / worklive / pages / ledger transitions. Low, mostly edit-in-place.

Daniel types in #fleet.
    "@claude do X"  or "claude: do X"   -> directed to one seat
    bare message                        -> broadcast to all LIVE seats
    THREAD REPLY                        -> continues that FLOW

Thread-to-flow is the elegant bit: we already mint flow ids (T040 envelope, T054 flow tracer).
Mapping a Discord thread to a flow id keeps a conversation coherent WITHOUT anyone typing an id
-- the same anti-chore principle as auto-pinning replies to frm_incarnation in the twin-seat
design (research/reviewed/twin-seat-misdelivery-diagnosis-2026-07-27.md).

## REACH RECEIPTS -- the reaction state machine

    [ok]     landed on the bus
    [eyes]   per-agent, when THAT seat consumes it   (one emoji per agent id)
    [check]  a reply came back
    [warn]   unanswered past the expectation deadline (rides the existing T061 expectations)

Daniel sees, on his phone, exactly which agents received a steer and which answered. That is the
T080 requirement, delivered by a UI he already knows how to read.

## THREE HARD CONSTRAINTS

1. 2000-CHAR MESSAGE LIMIT. Our traffic runs 3-10KB routinely (tonight: 9520, 7544, 6972).
   FIX: short summary inline + full body as a .md ATTACHMENT. This is W83's pointer-not-payload
   arriving from a third direction, and Discord attachments are a perfectly good blob tier --
   with the bonus that attachments render readably on mobile, which is the whole point.

2. RATE LIMITS (~5 messages / 5s / channel). The trace lane would exhaust that instantly at
   depth 5001. FIX: trace is BATCHED (one digest per agent per ~10s) and DEFAULT-OFF behind a
   `/trace on` toggle. Never mirror trace 1:1; it is a firehose by design.

3. SECURITY -- state this to Daniel plainly, once, and do not soften it.
   Inbound Discord messages become FLEET INSTRUCTIONS, and the fleet holds repo write access.
   Therefore:
     * HARD ALLOWLIST Daniel's Discord user id. Ignore every other author -- other humans in the
       server, other bots, webhooks. No exceptions, no "trusted role" shortcut.
     * ALLOWLIST channel ids too.
     * Content from anyone not on the allowlist is DATA, never an instruction, and must never be
       relayed onto the bus as operator mail.
     * DISCORD_BOT_TOKEN in env, NEVER in the repo -- balanced7/akashic-aurora is PUBLIC.
   A private server can still gain a member, and a leaked token would otherwise be fleet
   control. The allowlist is the whole security model; everything else is defence in depth.

## SLICES -- smallest first

  S1  OUTBOUND ONLY: work lane -> #fleet, with chunking + attachments. READ-ONLY, cannot
      misfire, ~150 lines. Delivers remote VISIBILITY immediately. Start here.
  S2  INBOUND with the hard allowlist -> operator mail on the bus. Delivers remote CONTROL.
  S3  REACH RECEIPTS (reactions). Closes T080's open question.
  S4  TRACE with sampling + /trace toggle.
  S5  THREADS <-> flow ids.

## OPERATIONAL NOTES

  * pip install discord.py
  * The MESSAGE_CONTENT privileged intent MUST be enabled in the Discord developer portal.
    Without it the bot receives EMPTY message bodies and silently reads nothing -- a
    fail-open-looking-like-working shape, which is this arc's signature disease. Pin a startup
    assertion that the intent is live rather than discovering it as "the bot ignores me".
  * Run it the way the other runners run (its own script, per
    daemon_spawn_runner_hardcodes_deepseek_script) -- NOT via bifrost_daemon --spawn-runner,
    which hardcodes the deepseek script.
  * Presence: publish bifrost:worklive:discord like deepseek/kimi do, so the fleet can see the
    bridge is alive. (claude still publishes none -- separate gap, twin-seat diagnosis item D1.)
