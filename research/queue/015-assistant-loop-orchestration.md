status: queued
# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes
#   stdout+stderr for the full 35m) -- the headless process produced no output at all, an infra
#   hang not a content problem. See runlog-2026-07-03.md; 6 of 12 shift tasks hit this pattern.
#   Requeued as-is. Next shift: OLLAMA_KEEP_ALIVE set longer before relaunch (see where-we-are).
# TASK: How should the thinnest talkable ASSISTANT LOOP be orchestrated -- hotkey/wake -> local STT -> route(local vs frontier) with akashic-memory injection -> stream -> TTS -- and how do open local assistants structure turn-taking, barge-in, and local/frontier routing?
feeds: A-series A0 (the talkable loop assembly -- 011 covers STT/TTS COMPONENTS, this covers the LOOP + routing) + consumes R013's small-model findings for the router/local leg
seeds:
- https://github.com/KoljaB/RealtimeSTT
- https://github.com/livekit/agents
- https://github.com/pipecat-ai/pipecat
notes: |
  Trigger: a-series vision (ADR_0703095414) -- A0 = "hotkey -> local STT -> claude/local route
  w/ akashic memory -> TTS out". 011 answers the STT/TTS component choices; THIS answers how to
  ASSEMBLE them into a low-latency conversational loop and how to route. Rika (ADR_0703094830)
  is the anti-pattern reference: it claims sub-300ms UNBENCHMARKED and ships "autonomy without
  governance" -- we ship gates-first + measured. Runs FREE on the fleet; BUILD gated behind S2.
  Chase, fetch-before-cite:
  (1) LOOP FRAMEWORKS: pipecat vs LiveKit Agents vs RealtimeSTT+custom -- do any run fully LOCAL
      on Windows (no cloud STT/TTS dependency), and what's the minimum viable hand-rolled loop
      (VAD -> STT -> LLM -> TTS with streaming) if the frameworks are too heavy for a solo tool?
  (2) TURN-TAKING + BARGE-IN: how is end-of-utterance detected (VAD/endpointing) and how is
      barge-in (user interrupts TTS) handled -- the two things that make a voice loop feel real
      vs painful. Real latency budgets per stage from field reports.
  (3) LOCAL/FRONTIER ROUTING: the policy for sending a turn to a LOCAL model (fast, free, from
      R013's picks) vs escalating to a FRONTIER model (Claude) -- confidence/complexity/cost
      signals, and how akashic recall context is injected at the routing boundary (our
      recall-at-action already exists; this is the assembly point). Prior art on router models.
  (4) STREAMING GLUE: token-stream -> sentence-chunk -> TTS so the assistant starts speaking
      before the full answer is generated (the single biggest perceived-latency win).
  (5) MEMORY WRITE-BACK: where in the loop does a turn become a note/lesson/beat (our existing
      doors) without blocking the response.
  "Done" = a v0 loop architecture (framework-or-hand-rolled decision + per-stage latency budget +
  the routing policy sketch), explicitly consuming R013's local-model pick for the local leg.
