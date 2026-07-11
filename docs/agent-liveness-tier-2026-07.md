# Agent Liveness Tier -- stuck/lost-agent failure modes and their fixes

Status: current  (2026-07-10)
Class: plan
Governs: T030 (proposed). Evidence base: research/reviewed/runner-mail-loss-forensics-2026-07-10.md.
Extends: docs/resilience-battery-2026-07.md + docs/resilience-battery-slices-2026-07.md
(RB-25 concurrency drills; RB-3 drainer liveness; T014/T017/T018/T019 lineage).

FENCE NOTE for DeepSeek: this doc carries claude's diagnosis and fix designs. Per the
standing fence, do NOT read it until your own independent investigation verdict
(research/reviewed/deepseek-liveness-invest-2026-07-10.md) is committed. You get the
forensics record + the raw question; divergence between our conclusions is the signal.

## The question (Daniel, 2026-07-10 evening)
"Can we analyze ALL the failure modes that cause deepseek -- or any agent -- to hang,
and design comprehensive fixes?"

## Diagnosis at loop altitude

An agent "hangs" from the fleet's point of view whenever the loop
    ask -> consume -> work -> observable outcome (reply | error | timeout-note | ack)
breaks anywhere, and no layer confesses the break at the timescale the asker waits on.
Tonight's incident (see forensics) broke it at consume->work: the runner died between
cursor-advance and first processing step, and every liveness surface truthfully said
"alive and idle" while the ask was simply GONE.

The system already defends most segments of that loop:
- L0 self-heal: httpx read/connect timeouts + explicit retries (G4), REPLY_TIMEOUT_SEC
  600 wall-clock guard, MAX_CMD_TIMEOUT tool ceiling, send-before-print (T019).
- L1 observe: worklive phase records with since_ts ageing (wedge = non-idle phase
  older than BIFROST_WEDGE_SECONDS=300) -- built, but nothing READS it yet.
- Detection of unanswered asks: P6 UNHANDLED flag -- but at the HOURS timescale
  (DIRECTED_UNHANDLED_HOURS=2), surfaced at boot/promoted, with no redelivery.
- Watcher-side silent consumption: fixed by T017 detect-dont-consume.
- Backlog skip: fixed by T014. Promise-shaped stalls: T018 (+RB-23 queued).
- Chatty-child pipe wedge: T019 drainers -- but only for LAUNCHER-managed children.

The remaining holes, each observed or code-verified tonight:

  H1. At-most-once inbox. `bus.wait(advance=True)` moves the shared cursor at READ
      time. Death in the consume->outcome window loses mail silently. (Observed live.)
  H2. Presence proves process, not progress. Heartbeat daemon keeps lock+presence
      fresh "even mid-wedge" by design; worklive (the progress signal) has no reader.
      (Code-verified; the L2 half of L0-L3 was never built.)
  H3. Runner lifecycle outside the launcher. Ad-hoc background launches lose T019's
      drainers + exit classification, and add new kill vectors (the -First N pipe).
      (Observed live -- the murder weapon.)
  H4. Block-buffered runner stdout. The runner's last words sit in an 8KB buffer;
      post-mortems read blank. (Observed live.)
  H5. Global auto-pause without TTL/provenance surfacing. control.pause() on a rate
      trip freezes the fleet; a crashed session can leave it set; boot does not shout
      it. (Code-read risk, not yet observed live -- verify semantics before building.)
  H6. Two send lanes, one verb name. The durable handoff verb and the live bus handoff
      diverge; asks silently target the wrong lane. (Observed live; lesson recorded --
      candidate for a door-level fix or doc-only.)

## Fix slices (small, reversible, each gated by a pre-registered kill drill)

### RB-26 -- At-least-once handling on the runner inbox  [design-review -> build]
Advance the shared cursor PER MESSAGE, AFTER _process_one returns -- not for the whole
batch at read time. Crash mid-handling -> the successor re-reads the message.
Duplicate-delivery discipline (exactly-once is a lie): before answering a redelivered
ask, check the P6 ack tier (already idempotent per actor) -- if this agent already
acked it, skip; if a reply for msg id exists (meta.reply_to), skip. Effectively-once
for asks, at-least-once for everything else. T014's full-batch-drain contract must
survive (drain all, advance incrementally). Kill drill D1: kill the runner between
consume and reply; the successor answers exactly one copy; ack stays single.
DeepSeek: [design-review] BEFORE build (load-bearing consume path) + [verify].

### RB-27 -- The L2 reader: progress, not presence  [build -> verify]
Build the missing consumer of L1: a `fleet doctor` audit (CLI verb + boot/bifrost-sync
line + UI hook) that renders per agent:
  - WEDGED: worklive non-idle phase older than BIFROST_WEDGE_SECONDS.
  - STALLED CONSUMER: idle/online phase while its inbox has unread entries older
    than N seconds (newest stream id vs cursor -- both readable today).
  - SUSPECTED MAIL LOSS: cursor moved past a directed ask, and no outcome (reply /
    error note / timeout note / ack) exists after REPLY_TIMEOUT_SEC + grace.
    (RB-26 turns this from a flag into a redelivery.)
Pure read-model; no new writes. Kill drills D2 (hung responder -> WEDGED within a
tick), D3 (planted backlog + idle runner -> STALLED CONSUMER). DeepSeek: [verify].

### RB-28 -- Runner lifecycle belongs to the launcher  [build -> verify]
One blessed relaunch path (scripts/run_fleet.py or launcher verb) that: routes runner
processes through core/comm/launcher.py (T019 drainers, exit classification, RB-3
drainer-liveness flag), sets PYTHONUNBUFFERED=1, and never pipes through truncating
filters. AGENTS.md gains the rule: agents launch runners ONLY through it. Kill drill
D4: a chatty runner through the blessed path survives 10k lines and its exit is
classified; the -First N footgun is structurally unreachable. DeepSeek: [verify].

### RB-29 -- Runner speaks in real time  [tiny, standalone]
sys.stdout.reconfigure(line_buffering=True) at runner start (it already reconfigures
encoding); first two startup lines must be on disk within 1s of launch when piped.
Folded into RB-28's blessed path but shippable alone. Drill D5 pins it. DeepSeek: [verify].

### RB-30 -- Pause hygiene  [verify semantics first]
Audit control.pause()/is_halted: give auto-pauses provenance + TTL (or an explicit
"paused (by X: reason, age)" line in boot + bifrost-sync + fleet doctor), so a
leftover freeze is loud. Build only what the audit shows missing. DeepSeek: [verify].

### Deferred, named
- Signed identity for cursor writers (who MAY advance an agent's cursor) -- same honest
  bound as RB-1/RB-2; out of T030.
- H6 door unification (one handoff verb, two lanes behind it) -- candidate slice, keep
  as doc+lesson until it bites again; a second incident promotes it.

## Sequencing
RB-29 (one line) -> RB-27 (read-model; makes everything after observable) -> RB-26
(the root fix, after deepseek's design gate) -> RB-28 (lifecycle) -> RB-30 (audit).
Every slice lands with its drill as a pinned regression; drills D1-D5 are named above
before any build starts, per the battery discipline.
