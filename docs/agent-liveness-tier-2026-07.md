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

FENCE LIFTED 2026-07-10 ~21:3x: both halves committed (deepseek's blind verdict at
research/reviewed/deepseek-liveness-invest-2026-07-10.md). Reconciliation below
(sec. "Reconciliation"); the FINAL SLICE LIST supersedes the draft slices in this doc.

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

## Sequencing (draft -- superseded by the reconciled list below)
RB-29 (one line) -> RB-27 (read-model; makes everything after observable) -> RB-26
(the root fix, after deepseek's design gate) -> RB-28 (lifecycle) -> RB-30 (audit).

## Reconciliation (2026-07-10, fence lifted -- two blind halves compared)

CONVERGED (identical conclusions, independently):
- Root cause, verbatim from both: cursor advances BEFORE processing; every loss mode
  (kill, wedge, lock-theft, pipe-kill) shares that one shape, and no redelivery path
  exists. Both proposed the SAME fix at the SAME seam (wait(advance=False) + explicit
  per-message advance after the reply sends). Two identical blind designs = the
  strongest design gate this fleet can produce; RB-26 is cleared to build.
- Both independently REJECTED Redis consumer groups (overkill for one-runner-per-agent)
  and refused to couple redelivery to signed identity.
- Both flagged the launcher gap (ad-hoc shells are unmonitored) and the hours-scale
  latency of the only existing detector (P6 ack tier).

COMPLEMENTARY (different angles, both adopted):
- deepseek's intra-phase PROGRESS PULSE (worker thread touches bifrost:progress:<agent>
  ~1s, TTL 5s) gives the wedge detector ground truth and kills the F2 false-wedge
  (long legit work vs dead worker) -- claude's fleet-doctor READER surfaces it plus the
  states a pulse cannot see (STALLED CONSUMER, SUSPECTED MAIL LOSS). Writer + reader
  are two halves of one slice pair.
- deepseek's SENDER-SIDE deadline/redrive (bifrost-send --expect-reply-within, 3
  redrives then alert; zero runner changes) covers the modes receiver-side redelivery
  cannot reach (C2/C3 runner absent, D1 stream eviction while offline). Adopted.
- deepseek's pipe-kill IMMUNITY (BrokenPipeError -> devnull degrade wrapper) is deeper
  than claude's launcher-only discipline; both land (immunity in the runner, blessed
  path in the launcher).
- Duplicate-reply discipline on redelivery: runner-side ack-check for handoffs (the P6
  tier is already the idempotency registry) + duplicates tolerated for chat kinds.
  (claude's runner-side check preferred over sender-side dedup -- fewer moving parts.)

DEEPSEEK-ONLY FINDS (folded in):
- B2: Redis lost mid-session -> heartbeat fail-open spins the loop forever, agent
  invisible-but-running (presence expired, worklive expired, loop alive). Gets its own
  slice (reconnect/backoff + stand-down after N dead beats).
- A3 mid-batch loss named explicitly; E1 lock-TTL overlap window; D1 offline eviction.

CLAUDE-ONLY FINDS (kept):
- H5/RB-30 pause hygiene (leftover control.pause freeze is loud at boot).
- The mail-gap check (idle + unread backlog older than N) in the doctor.
- H6 two-lane handoff verb (stays doc+lesson; second bite promotes it).

## FINAL SLICE LIST (T030 build order)
  L1. RB-26 at-least-once inbox -- advance-after-handle + ack-idempotent redelivery.
      Drill: kill between consume and reply -> successor answers exactly one copy.
      (Design converged blind; deepseek [verify] after build.)
  L2. RB-27a progress pulse (deepseek design) + RB-27b fleet-doctor reader (claude
      design): WEDGED / STALLED CONSUMER / SUSPECTED MAIL LOSS / paused-by-whom.
      Drills: hung worker flags in 5s; long legit call does NOT; planted backlog on an
      idle agent flags.
  L3. RB-28 pipe immunity + line-buffered stdout in the runner; blessed launcher path
      (PYTHONUNBUFFERED, no truncating pipes) + AGENTS.md rule.
      Drill: the -First N pipe cannot kill it; first lines visible within 1s.
  L4. RB-29 sender-side deadline + redrive (bifrost-send --expect-reply-within).
      Drill: kill recipient before reply -> auto-redrive -> relaunched runner answers.
  L5. RB-30 B2 bus-loss stand-down (reconnect/backoff; dead-beat exit) + pause hygiene.
      Drill: kill Redis under a live runner -> visible degraded state, clean stand-down,
      no spin; leftover pause renders loud at boot.
Every slice lands with its drill as a pinned regression, deepseek [verify] after each,
per the battery discipline.

## L1 + L1b BUILD SPEC (reconciled from the dual SOTA deep-read, 2026-07-10 -- this is
## the design-review record; both fenced halves converged on every mechanism)
Halves: research/reviewed/claude-sota-reading-2026-07-10.md +
research/reviewed/deepseek-sota-deepread-2026-07-10.md (verbatim). GATE: GREEN by
convergence + explicit deepseek reviewer-mode spec.

1. Loop: bus.wait(advance=False); per message _process_one then advance -- fold/filtered
   kinds advance immediately after handling; reply-owed kinds advance AFTER the reply
   sends. Batch semantics: cursor reflects 1..K on a crash at K+1; K+1..N redeliver.
2. Fencing (L1b, MANDATORY per Kleppmann): runner_lock.acquire INCRs
   bifrost:generation:<agent> (atomic monotone token). Cursor advance = ONE Lua script,
   conditional: refuse if new_gen < stored gen (STALE_GENERATION); store generation in
   the cursor hash. On refusal the runner LOGS LOUDLY AND STANDS DOWN -- no retry.
   Honest remaining window: post-advance-to-pre-next-heartbeat (~5s), 4x smaller than
   the unfenced E1 window; named, not hidden.
3. Dedup (all answerable kinds, not just handoffs): reply_sent:<msg_id> sentinel (TTL
   REPLY_TIMEOUT_SEC+60) set AFTER bus.send succeeds, BEFORE cursor advance. The
   sentinel is THE dedup gate (verify-corrected wording: it is set for handoffs too);
   the P6 ack tier is the DURABILITY record, not a second dedup check -- past the
   sentinel's TTL the sender has long moved on. Crash windows analyzed: send->sentinel
   = duplicate reply accepted (chat-grade, pinned as W3 tolerance); sentinel->advance =
   redelivered, sentinel fires, loud skip. Effectively-once for asks, at-least-once
   everywhere.
4. Drill harness (acceptance): five killpoint(name) sites (os._exit(137) when
   AKASHIC_KILLPOINT matches), AS-BUILT names (verify-corrected: the sentinel split is
   more granular than the draft's post-reply/post-advance pair, and the ack lands inside
   _process_one BEFORE the advance): post-consume-pre-process / post-phase-flip-pre-send
   / post-send-pre-sentinel / post-sentinel-pre-advance / between-batch-messages. Harness
   phases SETUP->EXECUTION->CHECK->METRICS; CHECK = invariants + ReferenceBus
   comparison (pure-dict mirror of send/deliver/reply/ack/cursor -- catches off-by-one
   the invariants miss); AKASHIC_TIMEOUT_MULTIPLIER shrinks timeouts BUGGIFY-style;
   every run seed-stamped.
5. Launcher deltas (L3, pulled forward where they touch L1's drill): kill = single
   SIGKILL (no graceful window -- crash-only; the finally block IS the recovery path);
   restart always when auto_restart, exit classification demoted to diagnostic;
   clear_if_pid checks the OS (pid liveness) before force-clearing, else trust TTL.
6. Methodology upgrade (Regehr, both halves): dual passes vary the METHOD, not just the
   analyst -- one static (code-read) one dynamic (drill/trace), or top-down vs
   bottom-up; fencing alone leaves shared-method blind spots.
