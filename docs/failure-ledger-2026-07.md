# Failure Ledger — 2026-07

Status: current (2026-07-16)

DANIEL DIRECTIVE 2026-07-16 (verbatim, note `ironman-directive`): *"address all of the system
failures and glitches as they come up and compile a list and work together to resolve those
categories of errors. Every friction point needs to get addressed not worked around (within
reason)."*

**The contract:** this is a LIVING ledger. When any agent hits a system failure, glitch, or
friction point, it gets an entry HERE (as it occurs, not batched later), with a category, a
root-cause hypothesis, and a routing (fix now / gated task / accepted boundary + why). A
workaround without an entry is a defect. Categories get RESOLVED — the entry closes only when
the class can't recur, not when one instance was dodged (fix-root-causes doctrine). Convention:
newest entries at top of each category; closed entries move to the CLOSED section with their
fix receipt.

## Category index

- **C1 Seat & lease lifecycle** — consumer seats, wake seats, runner locks, TTL vs liveness
- **C2 Concurrent-write collisions** — two writers, one file/key
- **C3 CLI ergonomics footguns** — quoting, arg parsing, cwd, silent clipping
- **C4 Process/launcher state** — supervisor loses track of children
- **C5 Ledger state machine** — transitions that block legitimate work
- **C6 Message/lane integrity** — dual-write stragglers, redelivery, count drift
- **C7 Harness-level quirks** — the seat's tools misbehaving (tracked; often not ours to fix)
- **C8 Cross-surface rendering** — content rendered for one seat type reaches another
- **C9 Epistemological integrity** — the system is confidently wrong about its own state
  (fabricated knowledge accepted as truth; no operational failure, just wrong premises)
- **C10 Serve-from-working-tree exposure** — a live service serves whatever is on disk; an
  agent's in-progress edit IS production, and a broken intermediate state hides until the
  next launch

---

## OPEN

### C10 Serve-from-working-tree exposure

**C10-1 · Uncommitted T002 splice killed the whole console: unclosed `registerVariant(` call
→ the entire 85KB inline script failed to PARSE — chrome rendered, but no EventSource, no
feed, no agent cards, and zero console errors to point at it** (2026-07-19, filed by claude
on live T002 co-verify). The T002 trace-collapse block was spliced INTO the argument list of
`registerVariant('viewmode','feed',...)` (scripts/bifrost_ui.py:2269-2272) instead of after
the closing `);` — a `var` statement inside an argument list is a SyntaxError at page parse,
so NOTHING ran. Because the UI server was also down since the church run, the breakage was
invisible until a fresh seat relaunched :8787 and co-verified. Detection was maximally quiet:
page 200s, all module assets load, `read_console_messages` empty — the parse error fires
before any console attach. Diagnosis that worked: fetch the page, re-inject the inline source
as a Blob `<script src>` with a `window.onerror` listener — the browser then reports REAL
line:col (1024:71) with context.
Root cause (class, not instance): the console serves the working tree live with NO gate
between "edited" and "serving" — no parse check at serve time, no post-edit render receipt
required, so a mid-edit or mis-spliced state becomes production silently. The instance also
shows the edit was never smoke-tested (a single reload would have caught it).
**Routing: fix-now DONE (claude, same evening) — deepseek's runner hung mid-turn (see C1
entry same date), so per the any-agent doctrine claude took the advisory lock and made the
SYNTAX-ONLY repair (two comment-marked spots: close `registerVariant` at the splice top,
remove the orphaned original `);` at the block bottom — the splice landed one line early,
inside the closer). T002 logic untouched; feature commit stays deepseek's. Class fix
LANDED: tests/test_ui_scripts_parse.py — node --check on the PAGE constant (AST-extract,
zero imports) + every `_static scripts/*.js` route; RED reproduced the splice at 1024:71,
GREEN after repair; no-node = loud skip (a homemade delimiter lexer false-positived on
regex-literals-with-backticks and was dropped — a gate that cries wolf teaches people to
ignore it). Live receipt: /events reconnected, 157 feed nodes, T002 card verified (12
traces → 1 card, expand/collapse works). Residual for deepseek: commit T002 + consider
dropping the stale `trace-collapsed` class on expand (cosmetic). Norm (2) stands: an edit
to a SERVING file requires a same-turn reload + render receipt.**

### C9 Epistemological integrity

*(C9-2 moved to CLOSED 2026-07-21 same-night — see CLOSED section.)*

**C9-1 · Self-justifying knowledge loop: agents author, verify, and ledger their own claims
— no external ground truth crosses the membrane** (2026-07-16, RED team Jester Forge audit)
The RED-team threat model (research/reviewed/jester-red-deepseek-2026-07-16.md) found that
the knowledge layer has NO defense against fabricated claims: `knowledge_note` writes the
fleet's canonical "where-we-are" state with zero content validation (agent_cli.py:1285);
`knowledge_learn` stores lessons with self-reported success and self-reported agent_id
(agent_cli.py:370); the faithfulness gate checks pointer resolution, not truth
(faithfulness.py:85 — a fabricated lesson IS its own valid source); the Forge curator
auto-confirms variants on statistical signals alone (curator.py:56-117); and the
PRECEDENCE_DOCTRINE (agent_cli.py:1055) ranks these unverified notes ABOVE immutable
promoted bus messages and live bus. An attacker with a normal `kb.learn` grant can
fabricate a completely fictional project state that every agent trusts, and the funnel
gauge would report the knowledge system as HEALTHY (the fabricated lessons would earn
"helped" credit when agents follow the false advice). No current C1-C8 category covers
this — the failures are epistemological, not operational.
Root cause: the knowledge layer has integrity at the transport level (packet hashes, lane
dedup) but NONE at the semantic level. Any agent can say anything about any topic and
the system will surface it as authoritative context.
**Routing: PROPOSE C9 as a new permanent category. Immediate: document in the failure
ledger. Triage: the BLUE team's jester-blue-* report should design defenses. The RED
team recommends (1) note-content cross-validation against task ledger/git, (2) lesson
provenance watermarking, (3) boot consistency check comparing notes against ledger state,
(4) a "Jester detector" that flags agent_id clusters with mutual related_to edges.**

### C8 Cross-surface rendering

**C8-3 · PreToolUse hook double-fires: registered on TWO surfaces, and the funnel gauge
counts the double-vision** (2026-07-16 evening, CLI probe round-2 live receipt: one Bash
call → two identical recall-at-action injections). `claude_pretooluse.py` is registered
BOTH project-level (.claude/settings.json, relative path) AND user-level (absolute path,
per AGENTS.md). Both fire on every matched tool call. Consequence beyond noise:
`log_injection()` runs twice per action → the funnel's `surfaced` denominator is ~2×
inflated → the headline value metric (4.2%) is roughly HALF-reported. The anti-repeat
logic cannot save it: both hooks load_seen before either mark_seen (race).
Root cause: two registration surfaces, no single source of truth, no dedup at the hook.
**Routing: FIX-NOW slice — pick ONE registration surface (user-level absolute-path is the
resilient one; project-level entry becomes documentation or gains a same-payload dedup
guard), then either recount or annotate the funnel series (a gauge correction event so
the 4.2%-era numbers are marked pre-fix). The GAUGE INVERSION theme's own gauge was lying
in exactly the direction the theme warns about.**

**C8-1 · Boot trim block names CLI commands a runner cannot natively use** (2026-07-16 morning, deepseek onboarding audit)
The 6000-char trim confession at the bottom of the runner boot names `py agent_cli.py doctor`,
`py agent_cli.py events --get`, `py agent_cli.py boot` as drill-down commands. These are CLI
commands designed for a CLI seat. A runner with a ToolBox door has different tools:
`bifrost_dashboard` (not `py agent_cli.py doctor`), `knowledge_recall` (not `py agent_cli.py
events --get`), `knowledge_boot(task=...)` (same as `py agent_cli.py boot` — that one works).
Root cause: the trim block is generated by `agent_cli.py boot` which renders for CLI seats
only — it has no awareness of the caller's door type.
Prior art: the W1 transport line already detects the door (`AKASHIC_SEAT_DOOR`). The trim
block should do the same: `door=toolbox` → render ToolBox-native pull pointers.
**Routing: PROPOSE small slice — surface-aware trim pull pointers in _trim_onboarding() /
boot render. Not a blocker (the information is still reachable; just takes one extra hop).**

### C1 Seat & lease lifecycle

**C1-8 · Managed runner hung mid-turn: alive to every gauge, dead to the fleet — daemon
heartbeat green, presence held, zero progress for 25+ min** (2026-07-19 ~19:45, live, day-run
relaunch). bifrost_daemon spawned bifrost_runner_deepseek (pid 16672); the runner did real
work for ~3-4 min (T067-1 drill: inbox, knowledge_map, searches), then its boot log froze
byte-identical mid-sentence and no new traces reached the bus — while `doctor` said healthy,
presence said online (daemon heartbeat, not runner progress), and process CPU sat at 3.7s
over 25 min wall (blocked I/O, almost certainly a hung LLM API call with no request
timeout). Consequence: both day-run fence gates (T094 R0 counter, T002 fix ask) queued
behind a seat every gauge called alive. The daemon's circuit breaker only counts CRASHES —
a hang never trips it. This is T030's RB-27 "L2 progress reader" gap plus T093's
sole-completion-path class, now with a clean live specimen.
Root cause (class): liveness is measured at the wrong layer — the daemon proves the CHILD
EXISTS, nothing proves the TURN PROGRESSES. No last-progress-timestamp the daemon (or
doctor) could compare against a stall threshold, no auto-recycle on stall.
**AMENDED ×2 same evening (claude; the correction chain stays visible — C9 discipline).
Amendment 1 (correct, kept): the timeout stack EXISTS and is layered — L0 httpx
connect=15s / read=120s per chunk + max_retries=1 (deepseek_chat.make_client, G4) +
REPLY_TIMEOUT_SEC=600s wall-clock (runner:756, T014); the runner's eventual confession
("no substantive reply after 2 attempts; reason: empty") is most plausibly that machinery
COMPLETING against a degraded API. The first-draft "no per-request timeout" line was wrong,
filed before reading the guard code.
Amendment 2 (retracts amendment 1's item (b) AND this entry's original work narrative):
the "boot log" this entry's evidence came from — state/runner_deepseek_boot.log, the
T067-drill activity, the "froze mid-sentence at stall onset" claim — is a FOSSIL:
mtime 2026-07-15 01:22, four days before this incident. Today's managed runner never
wrote it. ManagedChild pipes the child's stdout+stderr into a bounded IN-MEMORY ring
buffer (bifrost_child.py:178-187, F1) — a live managed runner writes NO log file at all.
So the observer-facing failure is sharper than buffering: (a) there is NOTHING on disk to
tail for a live managed turn, and (b) a stale, identically-named log from an earlier
UNMANAGED run sits exactly where an operator looks, impersonating live telemetry — this
seat read it as current TWICE, first manufacturing a hang narrative (and a kill request,
since withdrawn), then a token-accurate-streaming theory, before Get-Item's mtime ended it.
What is actually PROVEN about today: spawn 19:21:41, process alive throughout, CPU
3.8→7.8s, steers landed 19:29-19:35, confession ~20:05. Whether a hang occurred at all is
UNPROVEN — 2 serial attempts under the 600s wall-clock + retries plausibly fills the
window without one.
Routing: operator kill WITHDRAWN. Class fixes ride T030, sharpened: (1) RB-27 progress
reader — runner stamps `progress:<agent>` per hop; daemon compares age vs stall threshold,
recycles loudly; doctor renders last-progress age; (2) ring-buffer visibility — the F1
ring should be inspectable while the child LIVES (doctor verb or dump-on-demand), not only
at crash; (3) fossil guard — either the managed spawn TRUNCATES/renames stale same-named
logs, or boot-log writers stamp a "this file ends at <ts>, run <id>" tail so a reader can
see it is closed; (4) the turn-hold reconstruction goes to deepseek's own telemetry when
his seat is back.**

**C1-7 · Soft-steer silently undelivered to a SESSION-class seat — no steer_drain loop, no
delivery receipt** (2026-07-17 ~02:45, live, T060 round-2 control-fidelity dogfood). codex_root
pushed a soft-steer to `bifrost:steer:claude` at 02:33 ("fold this into your cross-critique
without restarting; report disposition"). My cross-critique filed at 02:40 WITHOUT the steer —
because it never reached me. Found only by direct Redis inspection at 02:45: the steer sits
UNCONSUMED in the Redis list. Root cause: `nudge.steer_push` appends to a per-agent Redis LIST
that only a RUNNER's between-round `nudge.steer_drain` pops (bifrost_runner_*.py). A Claude Code
SESSION seat (claude, sol-codex) has no such loop — it consumes the bus work-lane (mail) but
never the steer queue. So the fidelity ladder's `steer` rung is a silent no-op for session-class
seats: applied ZERO times, and the sender gets NO delivery receipt (unlike a work-lane
expectation, the steer list has no ack). deepseek-review (a runner) adopted his steer correctly
in the same experiment — the failure is SEAT-CLASS-specific, which is exactly why it evaded
notice until a session seat was steered. Honest disposition of the dogfood: `deferred` (in truth
never-delivered), active task T060 cross-critique, plan/tool history preserved (the steer never
interrupted because it never arrived), no confirmed dual-application (the queue held it once;
the design's dedup concern is real but this receipt shows the PRIOR failure — non-delivery).
This is the round-2 candidate contract's load-bearing gap made concrete: the contract assumes
`steer` folds into active context; for half the fleet's seat classes it evaporates.
**Routing: FEEDS the T060 round-2 control-fidelity design + T080 operator-traffic. The fix is a
seat-class delivery contract: either (a) session seats drain their steer queue at each turn
boundary (a stop-hook/whisper read, mirroring the work-lane wake), or (b) steers to a
session-class seat route as work-lane packets with an ack (so non-delivery is LOUD, never
silent). Mechanical pin territory: a steer to any registered seat must produce a delivery
receipt or a loud undelivered event within one turn. Lesson `session_seat_no_steer_drain`
captured. NOT fixed tonight — it is a design input to the active fence, and the fix touches the
fidelity seam the round-2 fence is still adjudicating.**

**C1-6 · Listener deadline self-cycle fired at "4.0h" against a ~5-minute-old watcher**
(2026-07-16 ~09:55, live). Standby armed ~09:50; listener exited ~09:55 with
`BIFROST_WAKE: deadline self-cycle for claude/69d664e5 after 4.0h -- re-arm trigger written`.
The Phase-3 deadline (T073: 4h internal loop, planned cycle) computed elapsed against
something ~4h old — suspected stale/shared anchor (the tombstoned overnight session armed
~05:35; +4h ≈ this firing). Consequence: spurious wake + re-arm churn on every arm while the
stale anchor persists — benign per-cycle (stop-hook renders it "cycled (planned)"), wasteful
in aggregate. Root-cause hypothesis: the deadline anchor is read from a per-AGENT (not
per-session/per-process) artifact, or from a surviving `.rearm`/marker mtime rather than the
watcher's own start time.
**Routing: T086-S4 (observable seat state) — verify the anchor source in bifrost_wake.py,
pin "deadline elapsed is measured from THIS watcher's start", and render the anchor in the
standby report. Also noted for S4: the standby report prints the FULL 78-line task ledger
when a ledger_update echo is in the drain — the report needs a compact ledger-delta line
instead (two receipts today).**
INVESTIGATED 2026-07-16 ~10:15 (same morning): code path is clean — deadline anchored at
process start (watch():186), defaults correct (14400s/120s), no file anchors, standby wrapper
single-shot. Four repro probes all HEALTHY (standalone throwaway agent, standalone live claude
lane, wrapper foreground on the real sid ×25s). Phantom did NOT reproduce; both occurrences
were background-task runs; not root-caused yet. LANDED as diagnostics: (a) the cycle line now
prints ELAPSED + configured + chunk (a phantom becomes self-evident from the print alone),
(b) standby's teach line no longer reports a signal-killed listener (rc≠0) as "wake-worthy
mail or deadline", (c) bonus — the deferred S1 watcher leg: a tombstoned session's watcher
stands down at its next chunk boundary BEFORE any bus read (pin: wake_block unreachable).
11/11 pins GREEN. Next occurrence carries its own numbers; category stays OPEN until then.
morning, live) — **CLOSED 2026-07-16 (T086-S1+S2a, deepseek cross-verified 56/56, five
adversarial targets signed off).** Session tombstone = the session-vs-process discriminator,
consulted by ladder (no grace), janitor (outranks K7 chain-immunity), and stop hook
(resurrected turns stand down unarmed); renewal staleness now outranks a live listener pid.
Verifier's verdict: "this morning's exact incident chain (end→ghost→resurrect→block 30min)
is now structurally unrepresentable." Carried forward: write_tombstone caller-verification →
T086-S7 charter (his T1 finding). Original entry + amendment retained as the incident record. Session ca9a86ad ended 08:47 (SessionEnd drafted the chronicle) but its
`bifrost-standby` (pids 35536/49316) + `bifrost_wake` child (49252) stayed armed — the wake seat
was held by a session no one can see. Consequence: peer mail would wake the dead session, not
the live morning seat; and the C1-1 evidence ladder correctly reads listener-pid-alive → holder
ALIVE, so the successor's standby would refuse the seat. CL-2 arms at TURN end by design; nothing
reaps it at SESSION end.
Root cause: session-scoped processes with no session-scoped teardown — SessionEnd closes the
episode (W8B) but not the session's own armed watchers; the liveness ladder can't distinguish
"pid alive" from "session behind the pid ended".
Prior art: systemd session scopes (processes reaped at logout); tmux client-vs-server lifetimes.
**Routing: PROPOSE (T073 wake-robustness arc) — SessionEnd reaps this session's armed
standby/wake children, and/or standby stamps a session-liveness marker the C1-1 ladder probes.
Interim rule (executed + audited today): morning seat runs a process census and reaps ghost
watchers BEFORE arming its own standby.**
AMENDED 2026-07-16 ~09:30 (same morning, live receipts): the interim rule above is WRONG —
killing a harness-tracked watcher RE-INVOKES its (ended) session, which re-armed and re-claimed
the seat out of turn-end habit (Harness Law L1's inverse: task-exit resurrection applies to DEAD
sessions too). Second receipt: after the ghost finally ended unarmed, its stale seat claim still
blocked the live seat for the full liveness-ladder window (grace 300s → indeterminate → TTL);
a 25-attempt × 20s standby retry loop exhausted without ever claiming — the agent was
UNWAKEABLE ~30 min while a definitely-dead holder aged out. Class diagnosis: liveness here is
FORENSIC (TTL/grace/evidence inference by the next arriver) where production systems make it a
MAINTAINED CHANNEL (heartbeat-bound ephemeral claims; death = an emitted event, not a condition
to prove). Interim rule v2: do NOT kill tracked watchers; wind the session down at session level
(ccd channel) or wait out the ladder. **Root fix: T086 (seat-lifecycle prior-art arc).**

**C1-1 · Consumer seat held by dead sibling for full TTL** — **FIXED 2026-07-16, awaiting
deepseek cross-verify** (see CLOSED on sign-off). `runner_lock.free_if_dead` probes the evidence
ladder (activity-marker freshness → armed-listener pid → no-evidence staleness) and frees only on
POSITIVE death evidence, with an audited `seat_freed_dead_holder` event; wired into the
consume_inbox refusal path (rescue once, then claim). Every ambiguity resolves toward ALIVE;
graceful ends were already covered by clean_death — this closes the CRASH path. 10 pins +
RB-21 regression GREEN. Root-cause history retained in git (this entry, prior revision).

**C1-2 · Wake-arm insta-loop on undrained inbox** (2026-07-15 night ×3 stop-hook cycles)
Arming the wake seat with wake-worthy stale mail present exits instantly; the stop hook demands
a re-arm; loop. Root cause: arm-before-drain ordering + C1-1 blocking the drain.
**Routing: TRACKED (T075-γ/T077 daemon owns arm/consume ordering) + tonight's C1-1 fix removes
the blocked-drain leg. Operational rule until then: consume-then-arm (proven live tonight).**

**C1-3 · Runner interrupted mid-task loses context (deepseek seat, 2026-07-15 ×2)** (NEW — deepseek)
Paused-mid-task interjection echoes: a nudge/steer arrived while I was mid-build; I stopped,
answered, and resumed — but my tool-loop state (which file I was editing, what I'd already read)
was lost. The nudge handoff text became my new prompt, displacing the task I was in the middle of.
Root cause: the runner's tool-loop has no "suspend current task → answer interrupt → resume"
mechanism. A barge-in replaces the active conversation wholesale.
Prior art: OS interrupt handling (save registers → service interrupt → restore registers);
OTel span events (attach a note to an active span without ending it). The runner needs a
"suspend-and-resume" primitive.
**Routing: PROPOSE T083 — tool-loop suspend/resume: on nudge/steer, save current conversation
state (tool history + task context), service the interrupt, restore. Until built: accept
context-loss as a known C1 boundary.**

**C1-4 · Redelivery storm after runner crash (deepseek seat, 2026-07-14/15)** (NEW — deepseek)
A runner crash (or daemon restart) leaves un-acked messages on the work lane. On re-spawn, the
new runner drains ALL of them in one turn — a "redelivery storm" that fills the context window
with stale handoffs. I developed the `skip-to-now` ritual (pause, cursor-tails, resume) but it's
manual and fragile.
Root cause: the cursor is durable but the "I already answered this" dedup is in-memory only.
Prior art: Kafka consumer groups (committed offsets survive restart); idempotency keys (Stripe
pattern — re-processed events with same key are no-ops). Our `reply_sent` prefix
(bifrost_runner_deepseek.py:84) is the right shape but not enforced at the consume door.
**Routing: TRACKED (T066 legacy-lane straggler is one leg; broader idempotent-consume is T068-R3
pre-flight assertions territory). Lesson `redelivery_storm_skip_to_now` captured.**

### C2 Concurrent-write collisions

**C2-6 · Kit install superseded a NEWER belt entry with older steps (TTL graduation
stripped)** (2026-07-21 night run, caught by the kit door's first install-dogfood)
recovery-kit v1's `standby-hard` spec was harvested BEFORE the same night's TTL graduation;
`kit claude` then superseded belt v5 (TTL'd, kata-VERIFIED) with v6 carrying the OLD un-TTL'd
steps — the registry's supersession is last-write-wins and install() has no belt-is-newer
guard. The freeze-forever vector deepseek had just closed was silently reopened on the
installing belt. Instance FIXED @b4eefc0 (kit v2 carries the TTL'd ceremony + fresh kata
receipts). **CLASS still open: a kit is a snapshot; any harvest lag re-bites on the next
install. Routing: gated small slice — install() compares the active entry's steps before
superseding (skip-or-warn on regression, "a kit must never regress the ceremony it
distributes"); kimi rules (their module) in the seat-zero counter round.**

**C2-1 · Two agents clobbered the same new test file** (2026-07-16, W4: both wrote
`tests/test_t081_w4_trace_collapse.py`; deepseek's write clobbered claude's — silent, caught by
a file-modified notice.)
Root cause: advisory locks cover *existing hot files*; NEW files have no lock and we had no
per-lane naming convention. Lesson `w4_two_writer_test_clobber` captured.
**Routing: convention SHIPPED (per-surface test names) + PROPOSE guard: guard_write /
Write-hook warns when creating a file another agent referenced on the bus in the last hour
("name collision likely"). Gated small slice; needs deepseek's half (his ToolBox write door).**

**C2-2 · Exec-family denial blocks git commit for the runner (deepseek seat, 2026-07-16)** (NEW — deepseek)
My exec grant (`--allow-exec` + `deepseek-build` launcher spec) is gated to `pytest` and
`py agent_cli.py <read-verb>` families only. `git add/commit` and `agent_cli.py mirror` are
REFUSED — so I can build and test but cannot commit. Claude must mirror my files.
Root cause: the guarded-exec families list (test_t067_guarded_exec.py:18) doesn't include
`git` or `agent_cli.py mirror`. The `deepseek-build` launcher spec adds `--allow-exec` but
the families gate is a separate layer — and the families list was designed for read-only
verification, not full build.
Prior art: sudoers (granular command allowlisting with args); CI/CD pipeline roles
(build-vs-deploy permissions). The fix is either (a) add `git` + `agent_cli mirror` to the
families list for `deepseek-build`, or (b) give me a `write_file`-based commit path.
**Routing: TRACKED (Daniel's morning gate: "review deepseek's exec grant in security/acl.json"
— the families list IS the gate to adjust). Until then: design + test + handoff to claude
for mirroring. C2 boundary — not a defect, a deliberate gate awaiting Daniel's approval.**

**C2-3 · Big-file write truncation at the ToolBox door (deepseek seat, recurrent)** (NEW — deepseek)
My `write_file` and `edit_file` tools have no explicit size declaration in the system prompt.
Large files (like this failure ledger entry) risk silent truncation at the API level — the
model doesn't know the byte budget.
Root cause: the hop counter tells me rounds remaining, but there's no write-size gauge.
Prior art: T043 packet MTU (BUS_MAX_MESSAGE_BYTES, LOUD refusal rather than silent clip).
The same MTU gate exists for write_file/edit_file at the runner level — but the model's
awareness of it is implicit (tool description says "GUARDED" but doesn't state the limit).
**Routing: PROPOSE — ToolBox write_file/edit_file descriptions declare the MTU boundary
("max N bytes; exceeding it is REFUSED, never clipped — split into multiple calls").
Small slice, rides my ToolBox door (deepseek_chat.py).**

### C3 CLI ergonomics footguns

**C3-1 · bifrost-send text swallowed CLI flags** — **FIXED 2026-07-16, awaiting deepseek
cross-verify.** `bifrost-send --text-file PATH` (git commit -F precedent): flag-bearing/long
bodies ride a file, never argv; unreadable/empty file refuses loud (rc=2), nothing half-sent.
5 pins (real parser + stubbed bus) GREEN. Root-cause history in git (this entry, prior revision).
REFINED 2026-07-16 (two live receipts, morning seat): the footgun is BROADER than flag-shaped
prose — argparse refuses the text positional placed AFTER optionals regardless of content
(`bifrost-send claude --to X --kind Y "text"` fails; text-before-flags parses). The morning's
first failure was mis-diagnosed as the `--`-in-prose case; the second (dash-free text, same
error) falsified that. Rule: --text-file for anything nontrivial; bare argv text goes BEFORE
flags. Residual open sliver: the refusal prints generic usage, not the remedy — teach-on-refuse.

**C3-2 · `Shell cwd was reset` on every PowerShell call** (all session)
Harness resets cwd between calls; every CLI invocation needs a `Set-Location` prefix.
**Routing: MITIGATED by T081-W2 (MCP-native door, awaiting Daniel's one-command apply) — the
shell-out dance disappears when the door attaches. Residual: acceptable harness boundary (C7).**

### C4 Process/launcher state

**C4-2 · Process cleanup DURING a live test killed load-bearing pids — flagship crash +
in-flight twin synthesis lost** (2026-07-16 ~21:54, Jester Forge night; filed post-crash by
the recovery seat). Sequence: T086-S5 daemon-supervisor pytest failing (3 consecutive FAILs
21:53), MCP boot() wedged (→ C7-4), Jester twin synthesis pass B in flight headless — and a
process cleanup ran against the wedge DURING all of it. The sweep took load-bearing pids with
the strays: five session_signals inside 2s (21:54:16–18); the flagship session end-signalled
TWICE (320 calls @21:54, 325 @22:09 — the C1-5 task-exit resurrection signature: it limped
15 min and died); twin pass B died in-context with ZERO durable output (the only real work
lost); the fleet went dark (UI, daemon, every runner/listener; deepseek + peer stranded as
stalled consumers); deepseek#1's finished-but-unmirrored S5/S6 files left stranded in the
working tree (the sole committer was dead).
What HELD (receipts): everything committed+pushed pre-crash (de6904e — all four Jester
reports) untouched; W8B SessionEnd draft chronicle captured 22:10:06; durable bus handoffs
(RED top-3, BLUE design, probe3's C7-4 report) survived; T086-S1 tombstones wrote; Redis clean.
Root cause: cleanup-by-name-pattern has no concept of owned vs load-bearing pids, and nothing
quiesces in-flight passes or mirrors stranded sibling work first. The morning's C1-5 interim
rule v2 ("don't kill tracked watchers; wind down at session level") did not generalize to
fleet scale under a wedge.
**Routing: PROTOCOL effective immediately + ROOT FIX tracked. Quiesce-before-clean: (1) land
in-flight work first (mirror uncommitted sibling files, let live passes file their output),
(2) end sessions at session level, (3) reap by CENSUS from an owned pid list — never by name
pattern, never mid-test. Root fix: T086-S5 daemon supervisor owns the pid inventory so "clean
up processes" becomes a supervisor verb with a safe kill-list — this crash is S5's charter
receipt. Lesson `quiesce_before_process_cleanup` captured.**

**C4-1 · UI launcher lost track of a live runner** (2026-07-16: launcher/status showed all
deepseek rows `never_launched`/empty while runner_lock showed pid 5320 alive; the UI process had
restarted and its in-memory `_procs` map was gone.)
Root cause: Launcher tracks children in process memory; a UI restart orphans the mapping (the
session-file restore exists but only restores *tags on click*, not live-process adoption).
Prior art: systemd re-reads unit state on daemon-reexec; supervisord reattaches via pidfiles.
**Routing: GATED SLICE (propose)** — Launcher.__init__ rehydrates: for each spec, if
runner_lock/pid probe shows a live holder, adopt it as `running` (read-only adoption; kill/revive
still work via pid). Medium slice; rides T030 (launcher-owned lifecycle).**

### C5 Ledger state machine

**C5-1 · T081 done-transition blocked by a PARKED in-progress task** — **FIXED 2026-07-16,
awaiting deepseek cross-verify.** PARKED is a first-class ledger status: reason mandatory, frees
the serialize slot, KEEPS owner+file claims, unpark re-enters through the same gate,
parked→abandoned legal; state_view/format_state render it. Migration executed live: T075 parked
(citing its own PARKED-behind-T047 text) → T081 in_progress→verifying→DONE @72a4925 — the exact
blockage, cleared through the fixed machine. 8 pins + 48 ledger/conductor regression GREEN.

### C6 Message/lane integrity

**C6-5 · Oversize promoted record renders as `[?] ? -> ? / null` — the promoter's detail
bound stores a `_truncated/_repr` husk the render can't parse** (2026-07-20 night, filed by
claude; found live on kimi's 8k-char build position). The promoter capped the detail dict,
stored `{'_truncated': True, '_repr': '<json-string>'}`, and `promoted` rendered null
fields — the MESSAGE looked lost while the content sat inside the husk (recovered by
drilling the raw event + parsing _repr by hand). Also the _repr itself CLIPS (kimi's N4
tail lost mid-sentence; resend requested). Two RB-5 violations in one seam: a bound that
neither confesses in-render nor names what it dropped.
**Routing: (1) promoted render parses the _truncated husk (frm/to/kind/head are inside the
_repr — render them + an explicit "[detail truncated at promoter bound — drill + resend
for tail]" line); (2) the promoter names its bound and the dropped byte count at store
time (packet-law confession, T043 lineage); (3) senders of >bound handoffs get the send-door
hint to chunk (kimi's own k2_tail 4000-clip lesson generalizes). Small slice; render half
is claude-lane, promoter half fences with deepseek.**

**C6-4 · Stale trace-lane backlog impersonates LIVE peer activity — 15-hour-old traces
consumed as "deepseek-review is working right now"** (2026-07-19 night, filed by claude on
self-caught misread — the day's THIRD stale-state fossil, after C1-8's log and the kimi-caps
memory). All evening this seat consumed deepseek-review read_file/write_file traces in small
batches and reported the module as "actively grinding T060, healthy while the main runner
choked" — building a healthy-sibling-same-provider differential into an API-degradation
consultation. Process inventory: NO deepseek-review process exists; presence never listed
it online; the digest render itself said `06:54` on every trace — MORNING backlog draining
through a lagged trace-lane cursor, ~15h late, a few messages per consume. The truth was
printed in-line and skimmed past: a bare clock-time render reads as "recent" unless it
carries AGE.
Root cause (class): consume renders label messages with wall-clock ts but no AGE, and
nothing distinguishes "arriving now" from "sat in the lane for hours" — the exact defect
kimi's D2 stale-mail gate just closed for the WORK lane at dcb4da7 (age-label at read time,
fail toward showing), left open on the trace/other lanes. Presence was the available
cross-check (deepseek-review absent all evening) and wasn't consulted.
**Routing: fix = extend the D2 age-label genus to EVERY lane's consume/digest render
(trace included): stale-past-threshold entries render with an explicit age tag ("15h old"),
zero hiding — small slice, cites kimi's D2 spec + this entry as its incident. Behavior
lesson folded into state_file_freshness_before_evidence (streams are files too: a
delivered-now message is not a sent-now message; check ts age + presence before claiming
"X is active"). My consultation asks carried the false premise for ~3 minutes before the
process inventory caught it; correction steers 1784515233595-0/...893 filed to both seats.**

**C6-1 · Unread-count drift across gauges** (whisper 8 vs sync 10 vs peek 19, all session)
**CLOSED 2026-07-16 → see CLOSED section (W8A).**

**C6-2 · Runner reply lands legacy-only — work-lane straggler (deepseek seat, 2026-07-14/15)** (NEW — deepseek)
My runner's `bus.send_reply()` wrote to the legacy inbox only; the work-lane write failed upstream
at the sender. Claude's work-lane consume saw "1 LEGACY STRAGGLER" — my reply was delivered
(via legacy dual-write) but stayed unread on the work lane, causing wake loops (3 cycles).
Root cause: the runner's reply path (bifrost_runner_deepseek.py) didn't route through the lane
router (packet_spec.lane_for). It used a direct `bus.send()` with a legacy-stream key.
Prior art: the lane router already exists for broadcasts — replies just didn't call it.
**Routing: FIXED by T066 (reply path now routes through lane_for + dual-write). Receipt:
test_t066_reply_path.py GREEN. Lesson `lane_era_marker` captured.**

**C6-3 · Piped gate exits make && meaningless (deepseek seat, 2026-07-15)** (NEW — deepseek)
`py -m pytest tests/... | tail -5` — the pipe swallows the exit code; `&&` chained after it
always runs (even when tests FAILED). I claimed GREEN on a failing test because `| tail` made
the pipeline exit 0. Root cause: shell piping through the runner's exec door; the door runs
the full string, and `|` chaining hides the first command's exit code.
Prior art: `set -o pipefail` in bash (any non-zero in the pipe → non-zero exit). Our fix is
simpler: the runner should NEVER pipe the gate — run the command bare, format after.
**Routing: CLOSED by lesson `gate_exit_codes_never_piped` (T031 enforcement) + exec-family
metacharacter refusal (T067 G2: pipes REFUSED). This class cannot recur.**

### C7 Harness-level quirks (tracked, usually not ours to fix)

**C7-6 · Headless Chrome screenshot hangs on the default profile (GCM phone-home)** (2026-07-18;
folded 2026-07-19 from the stray draft docs/failure-ledger-2026-07.md.C9-headless-chrome-note.md
during M0 currency repair — the draft filed itself as C9 before C9 became epistemological
integrity; it is harness/tooling, so C7). Symptom: `--headless --screenshot` produced no file,
never exited (GCM `PHONE_REGISTRATION_ERROR`/`DEPRECATED_ENDPOINT` loop); the shared default
user-data-dir blocks the pipeline on launch-time GCM/sync/background networking. PROVEN FIX
(same session): isolated throwaway profile + phone-home suppression — `--user-data-dir=<scratch>
--no-first-run --no-default-browser-check --disable-sync --disable-background-networking
--disable-features=Translate,OptimizationHints` → 1.56 MB PNG in <40s, exit 0. Routing: the
wrapper one-liner (scripts/local/shot.ps1) is filed as WISHLIST W22 so the next seat never
rediscovers the flag set. Adjacent SSE-page screenshot timeout is C7-2 (separate, tracked).

**C7-5 · MCP door twins AttributeError on Namespace attrs the CLI always defines — three
instances, one class** — **FIXED 2026-07-17 early AM (claude, during T060 round 2), pin GREEN.**
Sol's MCP-native seat hit two live: `notes()` read `args.all`, `note()` read `args.retire`
(receipts in his blind half §F1 + the round-2 addendum; he fell back to CLI and declared it).
Root cause: `_run()` builds `Namespace(**{**_ARG_DEFAULTS, **overrides})` (ai_setup_mcp.py:85-101)
and the keep-in-sync comment on `_ARG_DEFAULTS` was a HOPE, not a guard — argparse always defines
every dest for the CLI, so gaps are invisible until an MCP twin reads one. Fix: the missing keys
added AND the class pinned — tests/test_mcp_arg_defaults_parity.py AST-walks every
`_run(agent_cli.cmd_*)` delegation against every `args.<attr>` read in that cmd_*. The pin's
first run caught a THIRD latent instance (cmd_boot reads `args.sources_json`, masked until now
by C7-4's hang) — fixed in the same slice. This is ours to fix (unlike most C7): the wrapper,
not the harness. NOTE: live MCP servers load the module at spawn — running sessions keep the
old dict until their next restart; CLI unaffected throughout. This class cannot recur silently:
the pin fails the suite naming the exact cmd + attr.

**C7-4 · MCP boot() hangs in the RESPONSE path — the work executes, the reply never returns**
(2026-07-16: probe3 round-3 audit, reproducible 2/2 warm+cold, ~30min hang-then-abort while 9
other MCP tools return instantly; live post-crash receipt 22:11 — the recovery seat's first
MCP boot() call logged its boot event on the ledger at 22:11:40 yet the client saw nothing
until user-interrupt; the CLI boot then returned in 345ms). The wedged-MCP state was the
motivation for tonight's cleanup sweep (→ C4-2), so this quirk has now cost a session —
upgraded from log-only.
Root cause NAMED 2026-07-17 (triple-confirmed: claude empirical bisect + deepseek surface
analysis + Gemini + code evidence; research/reviewed/hardening-reconciliation-2026-07-17.md
S1): a **subprocess spawned inside `cmd_boot` inherits the server's stdout handle**; on Windows
the asyncio **ProactorEventLoop defers the pending stdout WriteFile completion until the next
inbound stdin frame** wakes the loop and sweeps its I/O queue. This is why `sleep(5)` and
print-only tools don't wedge (no child) but boot does (it spawns one), and why any inbound
frame — even a bare notification — flushes the stuck response in ≤0.07s. Exonerated by
isolation tests: the MCP SDK, the `_run` redirect_stdout mechanics, and payload size (a 42KB
tool result and `tools/list` at 21.9KB both flow instantly). Code evidence: `agent_cli.py:2760`
is an UNCAPTURED `subprocess.run(cmd, env=env)` (inherits fd1/fd2); `:1583` re-execs
`sys.executable` inside a print. The `_git` helper (:115, `capture_output=True`) is NOT a
suspect (fresh pipes).
**Routing: FIX-NOW slice (gates T081-W2). Bisect :2760/:1583 under the repro driver, then the
root fix = don't inherit std handles (stdout/stderr=PIPE|DEVNULL + close_fds=True), plus a
subprocess-door backstop for boot as defense-in-depth. Pins incl. the stdio-driver regression
(single tools/call boot, no 2nd frame, <5s). Until fixed: boot via CLI, other MCP verbs fine.**
BOOT PATH FIXED 2026-07-17 ~03:20 (commit 7f03d0a, codex_root slice / claude committer-verified,
green: 3/3 test_t078_w3_mcp_door incl new P6 cold+warm single-frame pin, exit 0). **DIAGNOSIS
REFINED — the mechanism is STDIN inheritance, not stdout, and the operative site was the `_git`
helper this entry EXONERATED.** capture_output=True gives the child fresh stdout/stderr pipes but
leaves STDIN (the MCP JSON-RPC transport handle) inherited; that inherited stdin is what parks the
Windows Proactor writer. boot's real hang path is boot→cmd_boot→_working_tree_status→`_git`
(agent_cli.py:119), not the :2760/:1583 re-exec sites. Fix: `_git` now runs with
`stdin=subprocess.DEVNULL, close_fds=True`. **CLASS STILL OPEN — three sibling subprocess sites in
agent_cli.py still inherit stdin and want an MCP-reachability audit + the same stdin sever:
:1524 (`git log --since`), :1588 (`sys.executable` re-exec inside a print — the old :1583 suspect),
:2761 (`subprocess.run(cmd)` re-exec — the old :2760 suspect). None is on the boot render path
(boot is proven fixed by P6), so this is a named residual, not a boot regression. Peer-review
confirm of the stdin-refinement flagged for Daniel's morning gate.**

**C7-1 · Glob `scripts/*.py` returned nothing while `**/bifrost_ui.py` matched** (2026-07-15).
Harness tool quirk; cost one extra probe. **Routing: ACCEPTED BOUNDARY (log-only) — not Aurora
code; workaround (recursive patterns) is zero-cost. Revisit only if it recurs with cost.**
Recurred 2026-07-16 (morning seat, cost one probe): pattern `scripts/*deepseek*` + path
`E:\AI-Setup` → silently empty; flat pattern `*.py` + path `E:\AI-Setup\scripts` → 57 hits.
Working rule: keep the PATTERN flat, put directories in the PATH. Still accepted boundary.

**C7-2 · Browser screenshot times out on the SSE-heavy UI page** (2026-07-15 ×2).
get_page_text works; screenshots stall. **Routing: ACCEPTED BOUNDARY (log-only), same test.**

**C7-3 · Background bash task failed exit 127 (`py` not found) on a command that ran fine twice
before and immediately after** (2026-07-16, the standby re-arm). Empty output = shell-level spawn
failure, transient, not reproducible (foreground probe: `py` resolves, verb works). RESILIENCE
NOTE: the failure notification itself woke the seat — the harness-tracked arm design degrades
correctly (a failed arm is a wake, never a silent dead seat). **Routing: log-only; escalate to a
retry-once wrapper in the standby verb IF it recurs (count: 1).**

---

## CLOSED (fix receipts)

**C9-2 CURRENT DIRECTIVE banner outlived its work for THREE consecutive seats** → CLOSED
same-night (2026-07-21; kimi first flagged 07-18 as W04). The class dies at BOTH ends:
(1) boot CONFESSES — `[as of <date>] [STALE? Nd old] [LEDGER DISAGREES: T075 PARKED]`
@8cf9352+@aeab4b9 (kimi's B1(c) extended the check to parked/abandoned after the DONE-only
version stayed silent on the live banner; pins tests/test_w04_directive_staleness.py 5/5);
(2) wrap RETIRES — a next-focus older than the wrap's look-back window tombstones with a
loud receipt + successor ref, ordering-pinned so a mid-way death never gaps the slot
@3216d8b (W36, claude+kimi 2-of-3; pins tests/test_w36_wrap_supersedes_focus.py 5/5).
The offending 07-15 banner itself was refreshed through the door (ADR_0721023007). A
fourth seat can be neither silently fooled nor left to re-diagnose by hand.**

**C1-9 pause-without-TTL: a mid-ceremony crash freezes the fleet until human hands** →
CLOSED same-night (2026-07-21, deepseek's find in the TOOLS PASS 2 review — "the C1-8 genus
in a different skin"): `control.pause(ttl=)` had RB-30 self-heal since T030 L5 but the
`bifrost-pause` CLI door never exposed it, so belt ceremonies (standby-hard, drain-decide)
paused unbounded. Fix @cdf12b4: `--ttl` flag at the door (pins tests/test_pause_ttl_door.py
3/3) + both recovery verbs re-minted with `--ttl 120` and kata re-VERIFIED (evidence dropped
to INFER at re-mint, earned back — honesty law held) + recovery-kit v2 distributes the TTL'd
ceremony @b4eefc0. Class closed: every shipped pause-bearing ceremony now self-heals; new
ceremonies inherit via the kit.**

**C1-6 false tombstone: harness restart cycles end-and-continue one session, its own
tombstone then blocks every re-arm** → CLOSED same-day (2026-07-19; found live by Daniel —
"I am not seeing the usual running process indicator"): desktop-app restart/compact cycles
fire SessionEnd (tombstone written, T086-S1 leg 0) on a session id that keeps living and even
receives fresh SessionStarts; the wake watcher then stands down forever ("session tombstoned
-- ended by record") and the seat goes deaf between prompts — 14 messages piled up unread.
S1's assumption ("a resurrected turn of an ended session" = zombie) was falsified by the
harness's own lifecycle. Root fix, symmetric authority: SessionEnd writes the ended-fact,
SessionStart CLEARS it (wake_seat.clear_tombstone, called first thing in
claude_sessionstart.py) — a true zombie never sees a SessionStart, so S1/C1-5 protection
stands untouched. Pins: tests/test_t086_s1b_resurrection.py (both legs clear + benign
double-clear) with the S1 suite green beside it (13/13); live full-path receipt: this seat's
tombstone cleared and its watcher re-armed the same hour. Residual routed: the arm/fire/rearm
churn itself is W18/T077-A1 (daemon owns wakeability), unchanged by this fix.

**C2-5 status check that writes: bootstrap.py opened a narrative session on every run** →
CLOSED same-commit (2026-07-17; routed from the fable-1c7f3a2e handover; found by
codex_frontier_019f6e7e on its FIRST boot — lesson bootstrap_status_is_stateful): the
docstring promised an "honest status check" while every run called start_session() (closes
any still-open narrative session FLEET-WIDE + re-chronicles it) then promote_salient(). A
stranger's first status run mutated the incumbents' narrative state; incumbents were blind
because they never run the newcomer door. Root fix: read-only by default, the mutation behind
an explicit --start-session flag, and the read-only run SAYS what it did not touch. Pins:
tests/test_bootstrap_readonly.py (mutation-free default + opt-in fires + agent-init pure).
The newcomer found it, the newcomer's lesson is cited in the flag's help text — the
stranger-contract loop closing as designed.

**C2-4 mirror named-path commit carries pre-staged riders** → CLOSED same-commit (2026-07-17,
filed by claude on live incident): claude's 462fefe named 2 doc paths but committed 4 files —
the fable-reconciler twin's 2 crash-path drafts were sitting staged in the SHARED git index,
and `git add -- <paths>` + bare `git commit` sweeps the whole index. The docstring's FM1
promise ("name the paths that are yours") failed in exactly the two-seat case it exists for.
Root fix: pathspec-limited `git commit -m msg -- <paths>` in named-path mode — stranger
staged entries survive staged for their own author; the printed receipt now derives from
post-commit `diff-tree` (the "committed 4 file(s)" mismatch was the detection surface, keep
it honest). Pin: tests/test_mirror_pathspec_rider.py (rider-excluded + staged-only regression
+ --all regression; the red run reproduced ['mine.txt', 'rider.txt']). Fence-lite adversarial
review requested from deepseek-review per T049(3).

**C1-5 ghost wake seat** → CLOSED by T086-S1+S2a (2026-07-16, same day as filed): session
tombstone + renewal-primacy ladder. 8 new pins incl. a live subprocess replay of the
resurrection; 48 regression GREEN both seats; deepseek adversarial cross-verify 5/5 targets
signed off. Prior art applied: ZK ephemerality + k8s lease semantics + systemd session scopes
(see t086-seat-reconciliation-2026-07-16.md). The morning's incident chain is the regression drill.

**C6-1 unread-count drift** → CLOSED by T081-W8A (2026-07-16): gauges now NAME their denominator
(whisper `mail: N unread (work-lane|all lanes)`; sync `N unread (all lanes, peek)`) via one shared
scope check. Counts explained, not forced to agree. Receipt: 6 pins + live renders.

**(pre-ledger) Trace spam burying mail** → CLOSED by T081-W4 both surfaces (shared
`render_collapsed`; live receipt: a 17-message consume rendered as 2 lines).

**(pre-ledger) Heal wolf-cry (4867 orphans)** → CLOSED by T081-W5 3-way honest heal; residual
real signal (259 unknowns + durable-drift question) is T082's charter, not noise.

**(pre-ledger) 189h dangling episode** → CLOSED by T081-W8B (SessionEnd auto-close, empty-safe,
both paths unified).
