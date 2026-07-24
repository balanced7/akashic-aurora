---
akashic_id: art_20260717_sol-runner-loop-implementation-spec-from_01c20e
akashic_sha: 7c46f36ad3b8
status: draft
type: design
date: 2026-07-17
title: "Sol Runner Loop — Implementation Spec (from `bifrost_runner_deepseek.py`)"
gist: "The bus loop is extracted from the deepseek runner verbatim; SolAgent (Responses-native tool loop) is Claude's parallel track — this spec on"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-17T00:24:45"
updated: "2026-07-17T00:24:45"
---
<!-- GENERATED PROJECTION of art_20260717_sol-runner-loop-implementation-spec-from_01c20e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Sol Runner Loop — Implementation Spec (from `bifrost_runner_deepseek.py`)

The bus loop is extracted from the deepseek runner verbatim; SolAgent (Responses-native tool loop) is Claude's
parallel track — this spec only covers the bus-loop half.

Source: `scripts/bifrost_runner_deepseek.py` (the live runner, 1,200+ lines, proven in overnight sessions).
Evidence: RB-26 drill passes (5 kill windows), T045 live lane cutover, T066 reply path, T086-S6 dedup.

---

## 1. CONSUME-TO-COMMIT PIPELINE (exact order of operations)

Each message that passes the ANSWERABLE gate goes through this pipeline. No step is optional;
every guard name is the live guard in `_process_one()` at `bifrost_runner_deepseek.py:625-815`.

### 1.1 Per-message filter chain (executed for EVERY incoming message in the batch)

```
incoming message m
  │
  ├─[1] clarify-answer check (R7/T058)
  │      if m.kind=="reply" AND m.frm=="user" AND meta.clarify_id exists:
  │        nudge.steer_push(args.agent, m.frm, m.content)
  │        return (no answer; the Agent is mid-turn polling for this)
  │
  ├─[2] HINT interception
  │      if m.kind=="hint":
  │        context_hints.push(args.agent, meta.hint.key, meta.hint.value, from_agent=m.frm)
  │        cog.record_file_read(...)
  │        return (hints never answer; injected on next model turn)
  │
  ├─[3] ledger fold (P3/T023)
  │      if m.kind in ("ledger_update","resolved"):
  │        fold_ledger_update(m)   # only from CONTROL_PLANE_SENDERS={"conductor"}
  │        return (folded for next turn; never answers)
  │
  ├─[4] ANSWERABLE gate
  │      if not should_answer(m.kind, m.frm, args.agent):
  │        return (self-broadcasts, non-answerable kinds silently skipped)
  │      ANSWERABLE = frozenset({"chat","request","question","handoff","nudge","inform"})
  │      // 'reply' is deliberately NOT answerable — echo-loop guard
  │      // 'steer' is NOT answerable — folded via inject(), not answered standalone
  │
  ├─[5] RB-26 dedup sentinel check
  │      if _reply_already_sent(bus, m.id):
  │        print(f"skip {m.id} — reply already sent (redelivery)")
  │        return (crash-redelivery duplicate; sentinel set in step [12])
  │
  ├─[6] hop-count loop guard
  │      hops = control.next_hops(m.meta)
  │      if control.hops_exceeded(m.meta):
  │        bus.send(m.frm, "note", "[loop-guard] max hops reached — returning to a human.", ...)
  │        return
  │
  ├─[7] rate-limit backstop
  │      if not rate.allow():
  │        control.pause(reason="reply rate limit hit", by=args.agent, ttl=3600)
  │        bus.send(m.frm, "note", "[loop-guard] reply rate limit hit — auto-paused...", ...)
  │        return
  │
  ├─[8] nudge / halt handling
  │      if m.kind=="nudge" or nudge.is_nudged(args.agent):
  │        nudge.clear(args.agent)    # consume so answering isn't self-interrupted
  │        bus.send(m.frm, "note", "[nudge ack] interrupting current work...", ...)
  │        cog.record_human_interjection(args.agent)
  │      if control.is_halted(args.agent) and m.kind != "nudge":
  │        cog.record_human_interjection(args.agent)
  │
  ├─[9] ACTIVITY SET + L1 worklive flip
  │      control.set_activity(args.agent, "thinking")
  │      liveness.worklive(args.agent).set("handling", detail=f"{m.frm}:{m.kind}", new_turn=True)
  │
  ├─[10] KILL WINDOW 2: post-phase-flip-pre-send
  │       killpoint("post-phase-flip-pre-send")
  │
  ├─[11] RESPOND (the model turn — wall-clock-guarded)
  │       Thread with REPLY_TIMEOUT_SEC deadline:
  │         - agentic:  responder(m.frm, prompt)   // per-peer conversation
  │         - one-shot: responder(prompt)
  │       On timeout: out = "(deepseek runner timed out after Ns...)"
  │       On error:    out = "(deepseek runner error: Type: msg)"
  │       RB-29: timeout/error → nonanswer=True
  │
  ├─[12] SEND REPLY
  │       reply_kind = "note" if nonanswer else "reply"
  │       reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops}
  │       if not nonanswer: reply_meta["answers"] = m.id   // RB-29: expectation linkage
  │
  │       if m.to == "*" (broadcast):
  │         bus.broadcast(reply_kind, out, meta=reply_meta)
  │       else (directed):
  │         if reply_kind == "reply":
  │           out = _preflight_gate(out, responder, args)    // T068-R3: verify before send
  │           bus.send_reply(m.frm, out, meta=reply_meta)    // T066: lane-first, meta.reply_id
  │         else:
  │           bus.send(m.frm, reply_kind, out, meta=reply_meta)
  │
  ├─[13] KILL WINDOW 3: post-send-pre-sentinel
  │       killpoint("post-send-pre-sentinel")
  │
  ├─[14] RB-26 dedup sentinel SET
  │       _mark_reply_sent(bus, m.id)     // Redis-first, then durable Store backstop
  │       // Set AFTER send, BEFORE cursor commit — crash here = redeliver, sentinel catches it
  │
  ├─[15] P6 handoff auto-ack
  │       if m.kind=="handoff" AND answered_ok:
  │         promoter.ack(args.agent, m.id, note="answered on the bus")
  │       // answered_ok = finished AND no Exception AND not promise-shaped error string
  │       // RB-29: timeout/error answers do NOT ack — expectation stays armed for redrive
  │
  ├─[16] turn metrics record
  │       cog.record_turn_complete(args.agent)
  │       _tm.record(args.agent, m.kind, duration_s=..., progress_points=...,
  │                  outcome=..., prompt_len=..., tokens=...)
  │
  ├─[17] ACTIVITY CLEAR + L1 worklive -> idle
  │       control.clear_activity(args.agent)
  │       liveness.worklive(args.agent).set("idle")
  │
  └─[18] CURSOR COMMIT (see §2)
```

### 1.2 Per-batch sweep (after the per-message loop)

```
After processing all messages in the batch:
  if batch_next changed (inbox or bc cursor moved):
    status = bus.advance_to(inbox=batch_next["inbox"], bc=batch_next["bc"],
                            generation=lock_gen, cursor_key=lane_key)
    if status == "STALE_GENERATION":
      print("batch-sweep REFUSED — standing down")
      break
```

---

## 2. CURSOR LAW (RB-26 + T045 lane selection)

### 2.1 The consume discipline

```
lane_mode = BifrostAPI.consume_lane_enabled()    // BIFROST_CONSUME_LANE=work env
lane_key = bus.lane_cursor_key() if lane_mode else None
api = BifrostAPI(args.agent) if lane_mode else None

// On first run, flip migration:
if lane_mode and bus.lane_flip_if_migrating():
    print("lane flip: cursor seeded at lane tails (A4 ritual)")

// Consume (RB-26: detect WITHOUT consuming):
if lane_mode:
    msgs = api.work_drain(timeout_ms=1500, since_out=batch_next, generation=lock_gen)
else:
    msgs = bus.wait(timeout_ms=1500, advance=False, since_out=batch_next)
```

### 2.2 Cursor advance (per-message, after reply sentinel set)

```
// RB-26: advance AFTER processing, never before
// A crash here redelivers; the _reply_already_sent sentinel catches duplicates
field = "bc" if str(m.to) == "*" else "inbox"
status = bus.advance_to(**{field: m.id}, generation=lock_gen, cursor_key=lane_key)
if status == "STALE_GENERATION":
    print("cursor commit REFUSED (stale generation) — standing down (L1b fence)")
    fenced_out = True; break

// Lane-mode filter: sig/legacy stream ids must NEVER advance work fields
if lane_mode and (m.meta or {}).get("_lane_src") != "work":
    continue  // their cursors advanced inside work_drain
```

### 2.3 The five RB-26 kill windows

```
KILLPOINT = os.environ.get("AKASHIC_KILLPOINT", "")

Window 1 (post-consume-pre-process):    between work_drain/wait and per-message processing
Window 2 (post-phase-flip-pre-send):    between activity-set and model turn start
Window 3 (post-send-pre-sentinel):      between bus.send_reply and _mark_reply_sent
Window 4 (post-sentinel-pre-advance):   between dedup sentinel set and cursor advance
Window 5 (between-batch-messages):      between two messages in the same batch

// Each kill is os._exit(137) — true crash, no finally/atexit.
// Drill harness arms one window, proves death, relaunches, asserts redelivery.
// Never armed in production (env gate AKASHIC_KILLPOINT).
```

---

## 3. RB-25 NEWBORN GUARDS (F1 + F2)

### F1: Quarantine refusal

```
if not os.environ.get("AKASHIC_DRILL_ECHO"):
    from core.trust.registry import may_run_runner
    if not may_run_runner(args.agent):
        print(f"'{args.agent}' is quarantined — refusing to start.")
        return 3    // exit code 3 = quarantine refusal
```

Rationale: a quarantined id's reply/trace lanes still reach the bus (infrastructure lanes,
not ACL-gated). Refuse at startup so a misconfigured runner never narrates for a banned id.

Escape: `AKASHIC_DRILL_ECHO` (offline-pipeline-drill signal, never set in production) uses
throwaway uuid ids that resolve quarantined — but its only reply is a canned `[drill-echo]`
string, not a model channel. The env gate is itself outside the bus threat model.

### F2: Tail-seed for virgin agents

```
if not os.environ.get("AKASHIC_DRILL_ECHO") and bus.seed_cursor_at_tail():
    print(f"{args.agent} is new — cursor seeded at the live tail "
          "(stale broadcast backlog skipped; only new mail wakes it)")
```

Rationale: a brand-NEW agent with a never-read "0"/"0" cursor would drain months-old broadcast
history and treat it as a current directive. An established runner keeps draining its real
backlog (mail queued while down — the T014 discipline); only a virgin cursor is fast-forwarded.

Same `AKASHIC_DRILL_ECHO` escape as F1: the kill-window drills PLANT direct mail then start
the runner expecting it consumed — seeding past the plant would eat exactly what the drill tests.

---

## 4. RB-29 EXPECTATION SEMANTICS

```
// The "answers" linkage: a reply that answers a message links back via meta.answers=msg.id.
// The sender's expectation sweep clears EXACTLY on kind="reply" + meta.answers match.

nonanswer = (timeout OR error)   // finished=False, or result is Exception, or out starts with "(deepseek"

if nonanswer:
    reply_kind = "note"          // RB-29: timeout/error → "note"
    // NO "answers" meta — the expectation stays armed
    // The redrive fires; the sender retries
else:
    reply_kind = "reply"         // RB-29: success → "reply"
    reply_meta["answers"] = m.id // expectation linkage — sweep clears this message
```

Key doctrine: a timeout/error reply clears the sender's expectation from FIFO (a note lands),
but the expectation sweep only settles on kind="reply". The note is informational; the
expectation remains armed for the redrive. Same as T026: a timeout reply never acks a handoff.

---

## 5. T066 REPLY PATH (lane-first directed answers)

```
if reply_kind == "reply":
    // T066: directed ANSWERS ride bus.send_reply (lane-first)
    // The recipient is a lane-mode consumer; plain bus.send would strand on legacy
    out = _preflight_gate(out, responder, args)     // T068-R3: verify factual claims
    bus.send_reply(m.frm, out, meta=reply_meta)     // lane-first, meta.reply_id set
else:
    bus.send(m.frm, reply_kind, out, meta=reply_meta)   // non-answer notes: plain send
```

Broadcast replies always use `bus.broadcast()` regardless of reply_kind.

---

## 6. HEARTBEAT + RUNNER_LOCK + PRESENCE CARD

### 6.1 Singleton lock acquisition (startup)

```
lock_token = runner_lock.instance_token(args.agent)    // unique per-startup token
if not runner_lock.acquire(args.agent, lock_token):
    // Another runner or SESSION holds the consumer seat
    h = runner_lock.holder(args.agent)
    if h.token starts with "session:":
        print(f"a session holds the consumer seat — wind down or wait ≤{TTL}s")
    else:
        print(f"another runner is live (pid {h.pid}) — refusing to start")
    return 3

PULSE_GEN[0] = runner_lock.generation_of(lock_token)   // RB-27a: tenure fencing
```

### 6.2 Background heartbeat thread

```
def _heartbeat():
    while not stop_hb.wait(5):          // every 5 seconds
        runner_lock.heartbeat(args.agent, lock_token)   // refresh TTL on singleton lock
        bus.register(card=CARD)                          // refresh presence card
        liveness.worklive(args.agent).refresh()          // L1: keep worklive fresh mid-wedge

threading.Thread(target=_heartbeat, daemon=True).start()
```

### 6.3 Presence card

```python
CARD = {
    "runtime_class": "api",
    "wake_mode": "runner",
    "door": "runner",
    "caps": ["review", "critique", "answer", "audit", "code"],
}
// Registered at startup: bus.register(card=CARD)
// Re-registered every heartbeat beat
// Also re-registered in main loop when halted (stays "online-but-frozen")
```

### 6.4 Bus loss guard

```
bus_guard = liveness.BusLossGuard(max_dead=10)    // RB-30 B2
// In main loop:
verdict = bus_guard.beat(bus.probe())              // probe(), NOT online
if verdict == "stand_down":                        // 10 consecutive dead beats
    print("bus LOST — standing down cleanly")
    return 4                                       // exit code 4 = bus loss
if verdict == "degraded":
    time.sleep(bus_guard.backoff_s)                // exponential backoff
    continue
```

### 6.5 Lock heartbeat in main loop

```
if not runner_lock.heartbeat(args.agent, lock_token):
    print("lost the singleton lock — another runner is live. Standing down.")
    break
```

### 6.6 Clean shutdown

```
finally:
    stop_hb.set()                                   // stop heartbeat thread
    runner_lock.release(args.agent, lock_token)     // free singleton lock for successor
```

---

## 7. THE respond() CONTRACT — WHAT THE BUS LOOP NEEDS FROM THE AGENT

The bus loop calls the responder with this signature. Claude builds SolAgent to satisfy it.

### 7.1 Function shape

```python
# Agentic mode (--agentic):
responder: Callable[[str, str], str]
#   responder(peer_id: str, prompt: str) -> str
#   - peer_id: the sender's agent id (for per-peer conversation cache)
#   - prompt: the message content
#   - returns: the final answer string (or error marker string)

# One-shot mode (default):
responder: Callable[[str], str]
#   responder(prompt: str) -> str
#   - prompt: the message content
#   - returns: the final answer string

# In both modes:
#   - Must be CALLABLE multiple times (the floor gate + bounce_promise call it for retries)
#   - Must never raise (catch all exceptions, return "(sol runner error: Type: msg)" string)
#   - Must be thread-safe (called from a daemon thread with wall-clock timeout)
```

### 7.2 The responder lifecycle (agentic mode)

```
On first call for peer X:
  1. Create SolAgent instance (the Responses-native tool loop)
  2. Build system prompt (continuity header + onboarding + private notes + capabilities line)
  3. Set max_output_tokens (SOL_RUNNER_MAX_TOKENS env, default 8000)
  4. Cache in per-peer dict: convos[peer_id] = agent

On subsequent calls for peer X:
  1. Retrieve from convos dict
  2. Drain context_hints for this agent → prepend to prompt
  3. Drain ledger_folds → prepend to prompt
  4. Call agent.send(prompt)
  5. After return:
     - Record token deltas: _token_deltas[peer_id] = (prompt_delta, completion_delta)
     - Run bounce_promise(answer, agent.send)     // T018: promise → one more turn
     - Run content_floor_check(answer, agent.send, ...)  // RB-23: empty/marker → confess
     - Release written locks: toolbox.release_written_locks()
  6. Return answer (never None; floor "" → "(sol produced no final answer)")
```

### 7.3 What the responder does NOT own

The responder does NOT:
- Write to the bus (the loop owns send_reply/broadcast)
- Manage dedup sentinels (the loop owns _mark_reply_sent)
- Handle nudge/halt/rate-limit (the loop owns the filter chain)
- Advance cursors (the loop owns cursor commits)
- Set activity/liveness (the loop owns control.set_activity + worklive)

### 7.4 Capabilities line (injected into system prompt)

```
[session capabilities] write_mode: ENABLED|READ-ONLY | tool budget: N rounds per task,
running counter [hop N] rides every result | recall-at: on|off
```

---

## 8. ONBOARDING (boot context fold)

### 8.1 Continuity header (injects FIRST)

```
## YOUR CONTINUITY (this runner's last known state)
DIRECTIVE: <next-focus body> (<age>)
SIBLINGS: solo | N live sibling(s) (list)
```

Built by `_runner_continuity_header(agent_id)` → calls `_directive_line()` + `_siblings_for_runner()`.

### 8.2 Project onboarding (injects SECOND, if agentic)

```
=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; honor the AGENTS.md contract) ===
<trimmed boot output from `py agent_cli.py boot <agent_id> --task "..."` >
```

Built by `onboarding_context(root, agent_id, task, door_detail=...)`:
- Runs `agent_cli.py boot` as subprocess (90s timeout, fail-soft)
- Stamps `AKASHIC_SEAT_DOOR=toolbox` + `AKASHIC_SEAT_DOOR_DETAIL=<n tools, write=on/off, exec=on/off>`
- Reads `--sources-json` sidecar for structured boot sources
- Trims to budget_chars (default 6000) via `_trim_onboarding()` — names every dropped section

### 8.3 Private notes (injects THIRD)

```
## YOUR PRIVATE NOTES (yours alone; memory_note updates, memory_recall lists full)
- <title>: <body> (<age>)
```

Built by `fold_private_notes(system, agent_id)` → calls `_age_stamped_private_notes()`.

### 8.4 Onboarding trim contract

`_trim_onboarding(digest, budget_chars)` — T050 Q2 / T043 packet law:
- If digest ≤ budget: return unchanged
- If digest > budget: cut at budget, then NAME every dropped `## Section` heading
  with a pull pointer: `knowledge_boot(task=...) re-assembles; knowledge_recall(query=...) fetches specifics`

---

## 9. SOL-NAMED SURFACE (the env/flag namespace)

Every env and flag is `SOL_*` — nothing deepseek-named on this surface.

| Env | Default | Purpose |
|-----|---------|---------|
| `SOL_MODEL` | `gpt-5.6-sol` | Model id |
| `SOL_EFFORT` | `medium` | Reasoning effort (none/low/medium/high/xhigh) |
| `SOL_VERBOSITY` | `medium` | Output verbosity (low/medium/high) |
| `SOL_RUNNER_MAX_TOKENS` | `8000` | Max output tokens per turn |
| `SOL_CONNECT_TIMEOUT` | `15` | TCP connect timeout (seconds) |
| `SOL_READ_TIMEOUT` | `120` | Per-chunk read timeout (seconds) |
| `SOL_MAX_RETRIES` | `1` | SDK-level retries |
| `SOL_401_RETRIES` | `3` | Preview-401 retry count |
| `OPENAI_API_KEY` | (`.secrets/openai.key`) | Provider key |

| Flag | Default | Purpose |
|------|---------|---------|
| `--agent sol` | `sol` | Bifrost agent id |
| `--model` | `SOL_MODEL` env | Model id |
| `--effort` | `SOL_EFFORT` env | Reasoning effort |
| `--verbosity` | `SOL_VERBOSITY` env | Output verbosity |
| `--service-tier` | `default` | `default` or `flex` |
| `--agentic` | off | Tool-using loop (SolAgent) |
| `--allow-write` | off | Guarded write doors |
| `--allow-exec` | off | run_command door |
| `--once` | off | One message then exit |
| `--summary-file` | none | M1-delta exit summary path |
| `--inject-summary` | none | M1-delta prior run summary path |

Flags REMOVED vs. deepseek runner: `--think` (→ `--effort`), `--temp` (sol locks temperature to 1),
`--no-think` (use `--effort none`), `--json` (not supported on Responses API).

---

## 10. VERIFICATION CHECKLIST (claude verifies `bifrost_runner_sol.py` against this)

- [ ] **STARTUP**: singleton lock acquire → refuse if another runner/session holds it (F1 quarantine guard before lock)
- [ ] **F1**: `may_run_runner()` check with `AKASHIC_DRILL_ECHO` escape hatch, exit code 3 on refusal
- [ ] **F2**: `bus.seed_cursor_at_tail()` for virgin agents with `AKASHIC_DRILL_ECHO` escape
- [ ] **PRESENCE**: `bus.register(card=CARD)` at startup + heartbeat beat + halt loop iteration
- [ ] **HEARTBEAT**: daemon thread, 5s interval, refreshes lock + presence + worklive
- [ ] **BUS GUARD**: `BusLossGuard(max_dead=10)`, stand_down at 10 consecutive dead beats (exit 4)
- [ ] **LANE MODE**: `BifrostAPI.consume_lane_enabled()` → `work_drain()` path; `lane_flip_if_migrating()` on first run
- [ ] **CONSUME**: detect WITHOUT consuming (`wait(advance=False)` or `work_drain()`), batch_next for sweep
- [ ] **FILTER CHAIN** (per message, in order): clarify-answer → hint → ledger fold → ANSWERABLE → dedup check → hops → rate-limit → nudge/halt
- [ ] **ANSWERABLE**: exact frozenset `{"chat","request","question","handoff","nudge","inform"}` — `"reply"` and `"steer"` absent
- [ ] **DEDUP CHECK**: `_reply_already_sent()` — Redis first, Store backstop, fail-open
- [ ] **DEDUP SET**: `_mark_reply_sent()` — Redis first, Store backstop, SET AFTER send BEFORE cursor commit
- [ ] **RB-29**: nonanswer (timeout/error) → kind="note", NO "answers" meta; success → kind="reply", "answers"=msg.id
- [ ] **T066**: directed answers use `bus.send_reply()` (lane-first); non-answers use `bus.send()`
- [ ] **BROADCAST**: messages to `*` replied via `bus.broadcast()`
- [ ] **T068-R3**: `_preflight_gate()` on directed answers before `send_reply()`; one fix round, fail-open on second failure
- [ ] **P6 HANDOFF ACK**: auto-ack handoffs when answered_ok (finished, no exception, not promise-shaped error string)
- [ ] **CURSOR ADVANCE**: per-message `advance_to(field=m.id)` AFTER sentinel set; lane filter (`_lane_src != "work"` skipped)
- [ ] **BATCH SWEEP**: `advance_to(batch_next)` after per-message loop; STALE_GENERATION → stand down
- [ ] **L1b FENCE**: `generation=lock_gen` on every cursor write; STALE_GENERATION = successor owns cursor → exit
- [ ] **RB-23**: `bounce_promise()` on final answer (one resend for promises); `content_floor_check()` (empty/marker → confess)
- [ ] **TURN METRICS**: `cog.record_turn_complete()` + `_tm.record()` with outcome/duration/tokens
- [ ] **CLEAN SHUTDOWN**: finally block: stop heartbeat thread, release singleton lock
- [ ] **EXIT SUMMARY**: M1-delta `_write_exit_summary()` to `--summary-file` path (fail-silent)
- [ ] **TOKEN JOURNAL**: T078 W1 `TokenJournal` at startup, `add_turn()` after each message
- [ ] **RATE LIMITER**: `control.RateLimiter()`, auto-pause with 1h TTL on threshold breach
- [ ] **HALT**: `control.is_halted()` check in main loop → sleep 0.4s, re-register presence, continue (not break)
- [ ] **CONTINUITY HEADER**: DIRECTIVE + SIBLINGS injected before onboarding
- [ ] **ONBOARDING**: `agent_cli.py boot` subprocess, trim to budget, name dropped sections, fail-soft
- [ ] **PRIVATE NOTES**: `_age_stamped_private_notes()` appended after onboarding
- [ ] **RESPONDER CONTRACT**: `(peer_id, prompt) -> str` for agentic, `(prompt) -> str` for one-shot; never raises; multiple-callable
- [ ] **THREAD GUARD**: model turn in daemon thread with `REPLY_TIMEOUT_SEC` wall-clock deadline
- [ ] **SOL-NAMED**: all envs `SOL_*`, script named `bifrost_runner_sol.py`, agent id `sol`, no deepseek in code or config
- [ ] **KILL WINDOWS**: 5 `killpoint()` calls at correct positions, `os._exit(137)`, gated by `AKASHIC_KILLPOINT` env
- [ ] **AKASHIC_DRILL_ECHO**: offline responder bypass → `lambda prompt: f"[drill-echo] {prompt[:120]}"`
- [ ] **LOG PREFIX**: `[sol-runner]` not `[deepseek-runner]` in all print statements
