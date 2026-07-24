---
akashic_id: art_20260719_api-resilience-kimi-half-verbatim-from-b_8c8c75
akashic_sha: 738e3e03dfef
status: current
type: design
date: 2026-07-19
title: API-Resilience -- kimi half (VERBATIM from bus handoff 1784515324531-0)
gist: "Date: 2026-07-19/20 | ts: 2026-07-20T02:42:04.360259+00:00 API-HARDENING POSITION (kimi, outside view + the control seat on a DIFFERENT prov"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T22:43:06"
updated: "2026-07-19T22:43:06"
---
<!-- GENERATED PROJECTION of art_20260719_api-resilience-kimi-half-verbatim-from-b_8c8c75 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# API-Resilience -- kimi half (VERBATIM from bus handoff 1784515324531-0)

Date: 2026-07-19/20 | ts: 2026-07-20T02:42:04.360259+00:00

API-HARDENING POSITION (kimi, outside view + the control seat on a DIFFERENT provider). Read all three transports + all three runners + the shared runner_lib factory. Label discipline: code-read VERIFIED unless flagged INFER. One correction up front: the arc's premise 'deepseek/kimi/sol all copy-paste make_client today' is STALE -- kimi_chat.py:41 already wraps the SHARED factory core/comm/runner_lib.make_openai_compat_client (the K0 rule-of-three seam). deepseek_chat.py:74 defines its OWN local make_client, byte-identical in shape but a SECOND copy. So the roster is 2/3 deduplicated and the third (deepseek, the sick one) is the holdout.

Q1. WHAT MY TRANSPORT DOES DIFFERENTLY (the clean-vs-sick delta, all code-read)
- NON-STREAMING single POST vs deepseek's STREAM. kimi KimiAgent.send does ONE client.chat.completions.create (kimi_chat.py:278, no stream flag), read_timeout=180s, connect=15s, max_retries=1. deepseek Agent._stream_turn does stream=True (deepseek_chat.py:241) with per-chunk read gap DEEPSEEK_READ_TIMEOUT=120. A non-streaming POST is a SINGLE read with ONE deadline -> a hang trips ONE timeout. A stream is N reads; the timeout must catch a MID-STREAM stall, and the sick-window signature (2x600s wall-clock + an 'abandoned' 600s call) says the per-chunk guard did NOT bound the wall-clock -- the outer 600s did.
- THE HONEST PART (INFER, do not over-credit my seat): my runner skeleton is IDENTICAL to deepseek's -- same _scaled(600) REPLY_TIMEOUT_SEC, same threading.Event worker_done.wait(600), same 'abandon the call to keep the runner alive' (bifrost_runner_kimi.py:439 mirrors deepseek's :756). So 'kimi stayed clean' is NOT because my runner is sturdier -- it's because the Moonshot API didn't hang tonight. My 180s non-stream read WOULD catch a stall faster than 600s, but if a single POST legitimately runs >180s of thinking, I abandon at 600s exactly like him. I am the control, not the cure.
- effort=max single-shot vs his hop-loop: MY model thinking is always-on, one big completion per hop, thinking billed INSIDE completion (probe-verified), MAX_COMPLETION_TOKENS=8000 floor. deepseek v4-pro thinking is OPT-IN per launch (--think flag, default OFF for the main runner per the :17 docstring 'one-shot, v4-pro, thinking off') with reasoning_effort=high only when enabled. The main runner ran think=OFF.

Q2. OUTSIDE-VIEW DIAGNOSIS (main sick + review-sibling healthy, SAME provider) -- where I look first
The fact that the SIBLING is healthy on the SAME provider kills the 'provider outage' theory. So the bug is PER-INCARNATION, not per-provider. Ranked:
  (1) REQUEST SHAPE: main runner = agentic tool-loop (make_agentic_replier) with the FULL ToolBox TOOLS schema + think per its launch; review sibling = likely a lighter/one-shot replier. Bigger tool schema + think=on + longer accumulated convo history = bigger, slower requests = more exposure to a provider-side slow path. LOOK FIRST: does the sick window correlate with large accumulated history or a specific tool-result size?
  (2) STREAM + think INTERACTION: a streaming request with thinking enabled produces reasoning_content chunks BEFORE content; if the provider stalls between reasoning and content, the per-chunk gap guard should fire -- but if it stalls BETWEEN tool-result-append and the NEXT create() (i.e., NOT inside a stream read), no read timeout is armed at all. The 600s 'abandoned' call smells like a hang OUTSIDE the stream-read window.
  (3) PER-INCARNATION CONFIG DRIFT: the two deepseek seats are separate processes with separate env. DEEPSEEK_READ_TIMEOUT / DEEPSEEK_MAX_RETRIES / model / think are all env/flag-tunable per launch. LOOK: diff the two launch commands' env. A drifted DEEPSEEK_READ_TIMEOUT on the main seat would explain everything.
  (4) HOP CADENCE: the agentic loop fires MANY creates per task; each is an independent hang-lottery ticket. More hops = more exposure. The review sibling with fewer creates/task simply buys fewer tickets.
DO NOT conclude 'Moonshot>DeepSeek' -- that's provider chauvinism on an n=1 night with confounded request shapes.

Q3. SHARED CLIENT-HARDENING SEAM (whole roster) -- what belongs in, what stays per-seat
BELONGS SHARED (push into runner_lib, finish the K0 job):
  - make_openai_compat_client for ALL THREE: delete deepseek_chat.make_client's local copy, wrap the factory like kimi does. One factory = one place to harden. (deepseek is the holdout; this is the concrete fix.)
  - A STREAMING-WATCHDOG the factory doesn't yet provide: today the ONLY wall-clock bound lives in the RUNNER (600s worker_done.wait). The CLIENT should expose a per-call deadline that a stream can honor ACROSS chunks (total-elapsed, not per-chunk-gap). G4/L0 hardened the per-chunk gap; nothing bounds total stream duration below the runner's 600s. That gap IS the 600s abandoned call.
  - A typed outcome the runner can distinguish: STALL vs SLOW vs EMPTY vs REFUSED -- so the runner abandons a STALL fast but lets a legitimately-SLOW thinking turn finish.
STAYS PER-SEAT (the fence's own ruling -- 'species-specific by design'): the Agent/tool-loop (runner_lib docstring: 'premature generalization' until two stabilize side-by-side), the env-var conventions + defaults (each seat's tuning surface stays local/greppable), the pricing/spend meter, the reasoning dialect (kimi reasoning_content strip vs deepseek stream reasoning vs sol effort ladder). Share the TRANSPORT hardening; never homogenize the minds.

Q4. C1-8 RESIDUAL -- the 60-second telemetry (what took us 40 min)
C1-8 was a fossil-log misdiagnosis; this arc is the SAME genus: we learned 'deepseek main is sick' by wall-clock suffering, not by a gauge. The 60-second version:
  - A PER-INCARNATION request-outcome gauge: every create() logs {seat, ts, duration_ms, outcome in COMPLETE/STALL/EMPTY/TIMEOUT, tokens, think on/off}. Then 'main sick, review healthy' is a DIFF of two gauge series, not a 40-min archaeology dig. (RB-27 progress-age rides this: a STALL emits a progress-stamp GAP; a slow turn emits stamps.)
  - A stream-heartbeat: during a stream, pulse a 'bytes-so-far' liveness stamp per chunk (deepseek already pulses per tool-call at :410 -- extend it INTO the stream read). A stalled stream = heartbeat stops while phase says 'thinking' -> the doctor sees it in one render instead of a human noticing silence.
  - The diff-view itself: one doctor render that puts all seats' last-request outcome + duration side by side. C1-8 + tonight both needed a HUMAN to correlate two processes; the gauge should correlate them.
NET FOR DANIEL'S GATE: the highest-leverage single fix is (a) finish the K0 dedup (deepseek onto runner_lib) + (b) add a total-stream-duration deadline below the runner's 600s so a hang is a fast caught STALL, not a 600s abandonment. That turns tonight's 25-40min silent window into a <200s confessed retry. My seat is the control, not the template -- port the TRANSPORT hardening, keep each seat's loop its own.
