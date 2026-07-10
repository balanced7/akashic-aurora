# The Resilience Battery -- stress tests + validations for the comms arc (claude, FENCED)

Status: current  (2026-07-10, P4: fenced first-party battery; deepseek's arrives blind, reconciliation appends)
Daniel's directive: "the most demanding stress tests and feature validations... to test every
nook and cranny of this system and evolve and improve it further." Committed before reading
deepseek's parallel battery (the standing fence).

DESIGN PRINCIPLE: a resilience battery is honest only if it aims at SUSPECTED weaknesses, not at
what we know passes. Section 0 names, in the open, the five places I suspect my own designs
from this arc are weakest. Every test names its KILL CONDITION (what breaking looks like).

---

## 0. NAMED SUSPICIONS (attack here first)

S1. T019 drainer death resurrects the pipe-wedge: the drainer threads are daemons with no
    supervisor -- if one dies (encoding bomb, OOM), the pipe silently refills and the child
    freezes EXACTLY as before, but now we believe we fixed it.
S2. P6 acks_for scans top_k=500 msg_ack events: past 500 lifetime acks, OLD acks fall off
    the scan and settled messages RE-FLAG as UNHANDLED -- a volume-triggered lie.
S3. P5 stale-proposed list in format_state is UNBOUNDED: 500 stale proposals = a render
    bomb inside every boot head + wake report (the 6000-char onboarding head dies first).
S4. P1 supersession has no cycle/fork detection: A--supersedes-->B --supersedes-->A hides
    both; two concurrent re-notes of one title fork two co-current siblings (the exact
    split-brain the discipline exists to prevent), and nothing detects the fork.
S5. P7 relevance is a fraction of query terms matched (caps at 1.0): a keyword-stuffed doc
    ties the honest artifact on relevance and wins on importance/recency -- corpus
    poisoning by enthusiasm (or malice) dominates every query.

## 1. Per-slice stress tests

### P0 wake listeners (T017)
- CURSOR STORM: arm 5 watchers for one agent by racing the heartbeat write, while a live
  session consumes and a producer floods 1k traces + 10 wake-worthy directs.
  KILL: any direct message unreadable afterward; >1 wake per wake-worthy message after the
  singleton converges; convergence takes >1 inner block.
- TRIM CHASE: producer sustains maxlen-rate flood so the stream head advances past the
  watcher's local cursor CONTINUOUSLY while it pages.
  KILL: unbounded paging loop, exception, or a wake-worthy message in the flood missed.
- REDIS FLAP UNDER BLOCK: kill Redis during a blocking wait(); restart 10s later.
  KILL: watcher exits nonzero, wedges, or double-detects after restart; cursor corrupted.
- ZOMBIE GENERATIONS: script a dead-session lane that re-arms on kill (the 07-09 rebound),
  run the reap, kill the survivor, repeat x5.
  KILL: any generation consumes a message, or two watchers survive the reap.
- ID EDGE MATH: seed local cursors with "0", "0-0", max-seq (18446744073709551615), and a
  FUTURE-dated id (producer clock skew).
  KILL: _id_key mis-orders any pair; fast-forward regresses the local cursor.

### T018 promise-bounce
- ADVERSARIAL ENDINGS CORPUS: 50 endings authored by the OTHER model in its own voice,
  half promises half outcomes (pre-labeled, sealed), incl. bilingual, bullet-form, and
  "I'll wait" stop-verb families.
  KILL: precision < 0.9 (false bounces burn a completion each) or recall < 0.6 (stranded
  deliverables persist); any DOUBLE bounce.
- BOUNCE COST CEILING: force promise-shaped first replies 10x consecutively.
  KILL: any turn exceeds 2 completions, or the 600s worker deadline trips from the bounce.

### T019 pipe drainers
- DRAINER ASSASSINATION: inject a poison line that raises inside _drain_pipe (monkeypatch
  decode), then keep the child chatty.  (<- S1)
  KILL: child blocks on write again (the resurrection); no signal anywhere that a drainer
  died. EVOLVE: drainer supervisor or watchdog counter in launcher status.
- BINARY FIREHOSE: child emits 100MB mixed stdout/stderr, invalid UTF-8, NUL bytes, 10MB
  single line (no newline -- line-iterator starvation probe).
  KILL: RSS growth unbounded, tail corrupted beyond errors=replace, or freeze.
- EXIT RACE: child exits while both pipes still hold megabytes undelivered.
  KILL: exit-classification reads empty tails (the classifier lies about WHY it died).

### P1 notes supersession
- CYCLE BOMB: A supersedes B; force B supersedes A via explicit --supersedes.  (<- S4)
  KILL: both hidden from default reads (current-state vanishes) with no detector.
- FORK RACE: two processes re-note the same title within 10ms.  (<- S4)
  KILL: two co-current same-title notes and nothing flags the fork. EVOLVE: CAS on the
  supersede write or a fork-detector in notes/boot render.
- TITLE HOMOGLYPHS: re-note "where-we-are" vs "where-we-are " vs "where‑we‑are".
  KILL: silent sibling minting (supersession misses; the pileup returns wearing unicode).
- MIGRATION REPLAY: restore the pre-P1 snapshot (67 notes), replay the migration script
  twice.
  KILL: non-idempotent second run, or end-state differs from the shipped 11.

### P2 orientation header
- SOURCE CORRUPTION MATRIX: for each header line's source (ARCHITECTURE.md, notes store,
  tasks.json, arch index), corrupt/delete/truncate it; boot for a fresh agent.
  KILL: any combination bricks boot or prints a confidently-wrong line instead of its gap
  line (fail-open must also be fail-HONEST).
- GOVERNS COLLISION CENSUS: generate 200 synthetic (status-note, active-task-title) pairs
  from real vocabulary; measure double-governs frequency.  (validates the documented bound)
  KILL: >5% collision rate in realistic vocabulary -> the bound is not rare, redesign.
- HEAD BUDGET SIEGE: 3 active tasks with 200-char titles + stale list + a 120-char wwa.
  KILL: orientation block exceeds ~20 lines / the stateless peer's 6000-char head loses
  the doctrine lines (the CONSUMER's contract is the budget).

### P3 ledger push + fold
- TRANSITION STORM: 500 scripted transitions in 60s across 20 synthetic tasks while a
  runner works an unrelated request.
  KILL: hints ring evicted (folds must not touch it -- pinned), fold dict grows unbounded,
  the runner's turn latency degrades >2x, or the UI feed drowns.
- MARKER TRIM RACE: transitions land while the runner sleeps; bus maxlen trims the markers
  before its next drain.
  KILL: the runner acts on a stale ledger view AND nothing (boot backstop) corrects it
  within one wake cycle.
- OFFLINE CONDUCTOR: Redis down for 10 transitions (doorbell dead, ledger file fine).
  KILL: any transition lost from the LEDGER (file truth), or agents never learn (backstop
  chain broken).

### P4 doc currency guard
- STAMP EVASION SUITE: Status in an HTML comment, inside a code fence, on line 13, cyrillic
  homoglyph "Ѕtatus:", stamped-then-contradicted ("Status: current" + "THIS DOC IS DEAD").
  KILL: guard passes any of them silently. EVOLVE: scope decisions documented per case.
- DANGLING SUPERSESSION: A superseded-by B; delete B.
  KILL: guard stays green while the successor pointer dangles (currently UNCHECKED -- a
  known gap; this test forces the fix).
- CURRENCY ENTROPY CLOCK: fake-age every current doc past 45d (env clock).
  KILL: warnings drown (79 warnings = nobody reads them) -- EVOLVE: aggregate + rank by
  reference-frequency from lookback hit counters.

### P5 proposed decay
- PROPOSAL FLOOD: 500 proposed tasks via script.  (<- S3)
  KILL: boot head / wake report render bomb; onboarding head budget destroyed. EVOLVE:
  cap the stale list render (count + top-3 oldest).
- TIMESTAMP GARBAGE: proposals with missing/invalid/future created+updated stamps.
  KILL: staleness silently wrong (future-dated = never stale = immortal parked intent).

### P6 msg_ack
- ACK VOLUME LIE: write 600 acks, then query a message acked FIRST.  (<- S2)
  KILL: settled message re-flags UNHANDLED (top_k scan ceiling). EVOLVE: per-message ack
  lookup via refs index instead of a bounded scan.
- SPOOFED ACTOR: a quarantined/unknown agent acks someone else's handoff via CLI.
  KILL: promoted() renders it indistinguishable from a legit ack (trust model says
  advisory -- then the RENDER must show provenance, or the ACL must gate the verb).
- SUPPRESSION FALSE POSITIVE CENSUS: run the closed-task suppressor over ALL real promoted
  history; hand-label the suppressions.
  KILL: any suppression where the ask was genuinely never handled (incidental T-id mention
  suppressing a live ask).
- SELF-ACK LAUNDERING: A asks B; A acks its own ask via a THIRD agent id it also controls.
  KILL: nothing even records the delegation relationship (the on_behalf field deepseek
  specced -- deferred; this test decides if it stays deferred).

### P7 lookback
- SHOW-NOTHING BATTERY: 10 pre-registered questions whose answers DO NOT EXIST in any
  corpus ("why do we use kubernetes", "why was the rust rewrite abandoned").
  KILL: any hit above the floor (precision is the product; hallucinated rationale is worse
  than silence).
- POISONED CORPUS: plant one keyword-stuffed doc containing every term from the 12-probe
  battery.  (<- S5)
  KILL: the plant enters top-3 for >2 probes. EVOLVE: term-frequency dampening or a
  stuffing detector in the docs adapter.
- RETIRED-ONLY TRUTH: ask a question answerable ONLY by a retired note.
  KILL: the retired note is unreachable (archaeology broken) or unlabeled as retired.
- SCALE CLIFF: 10x the git depth (2500 commits), 2k promoted events.
  KILL: latency >5s or memory >500MB (the verb must stay a reflex, not a report).

## 2. Cross-slice systemic stress scenarios

- THE CHAOS HOUR: 60 minutes, live fleet, scripted: Redis killed twice, runner killed
  mid-compose, UI killed, 2 zombie lanes armed, transition storm, 3 fenced asks in flight.
  KILL: ANY of -- a message unrecoverable from streams; a ledger transition lost; an agent
  acting on provably-stale state without a labeled source; a human unable to reconstruct
  the hour from promoted+events+chronicles afterward.
- THE NEWBORN GAUNTLET: a brand-new agent id (quarantined, deny-by-default) must go from
  nothing to one correct contribution using ONLY boot + AGENTS.md + lookback. DEEPSEEK
  PLAYS THE NEWBORN (fresh runner, no convo memory) -- scored rubric: found the map, obeyed
  precedence, claimed correctly, was refused correctly by every gated door it probed.
  KILL: any door lets the quarantined newborn write where it should not; any orientation
  question unanswerable from the head.
- THE 30-DAY ENTROPY SIM: scripted generator compresses a month -- 40 wraps, 200
  transitions, 60 promoted asks, 30 doc edits -- then audit: notes count, stale flags,
  unhandled count, doc warnings, funnel counters.
  KILL: any curation loop loses to entropy (notes >20, unhandled unbounded, warnings
  ignored-by-design) -- the pillar's claim is that current-state stays SMALL under load.
- SPLIT-BRAIN HEAL: force Redis/File store divergence on notes + ledger mirror, boot.
  KILL: heal picks the WRONG side or heals silently without logging what it chose.

## 3. Method notes

- Every test lands as either a pytest (fast, hermetic) or a scripted DRILL (live fleet,
  runbook + evidence capture) -- no test theater: each names its kill condition up front.
- Pre-registration fence applies to the graded batteries (T018 endings corpus, P7
  show-nothing set) -- sealed before the detectors see them.
- EVOLVE items found by kills become ledger tasks with the test as their acceptance gate.

---

## 4. RECONCILIATION with DeepSeek's fenced battery (2026-07-10)

Both designed blind (fence commits: claude before reading, deepseek reply verbatim at
research/reviewed/deepseek-resilience-battery-2026-07-10.md). The divergence is the value.

### Independent CONVERGENCE (highest confidence -- two blind passes hit the same wound)
- **Drainer death resurrects the wedge** -- my S1 == deepseek R4, verbatim same mechanism
  (daemon drainers assumed immortal; one unhandled exception = Exhibit A returns with a
  healthy heartbeat masking it). Both ranked it top-5. This is the arc's realest survivability
  gap. EVOLVE: drainer liveness poll in the launcher monitor, not just at exit.
- **The one-cursor-per-agent-id architecture's unfixed half** -- my P0 zombie-generations/
  cursor-storm == deepseek R1/R2 (zombie SESSION cursor race; TTL-death without a
  SessionStart trigger). P0 fixed watcher->watcher; session->session is open.

### COMPLEMENTS (each caught what the other missed)
- deepseek-only, and SHARPER than anything I had: **R9** (P3 closed-task suppression x P6
  ack compose), **R15** (adversarial ledger_update injection -- ANY bus agent forges
  control-plane messages), **R12** (self-ack scope), **R17** (promoted() vs lookback scan
  windows disagree on ack state), **R18** (the dual-battery method has a built-in expiry --
  the meta-level restatement of this whole arc's thesis: nothing retires without recurring
  enforcement), **R6** (identical-timestamp governs tiebreaker is a coin flip), **R10**
  (superseded-by breaks under git mv), **R13** (lookback blind on a cold clone).
- claude-only: **S2/P6 ack-volume lie** (500-scan ceiling re-flags settled msgs -- same root
  as deepseek R17), **S4/P1 cycle+fork detection**, **S5/P7 corpus poisoning**, **P4 stamp
  evasion (homoglyphs/fences)**, **the Newborn Gauntlet** (deepseek PLAYS a quarantined
  newborn), **P2 governs-collision census**, **the 30-Day Entropy Sim**.

### LIVE VERIFICATION of deepseek's three concrete shipped-code claims (run 2026-07-10)
- **R15 CONFIRMED REAL**: fold_ledger_update accepts a forged `kind=ledger_update` from
  `frm=malicious-agent` -- no sender check. Low-severity in a trusted 2-agent fleet, but a
  real trust-boundary hole. FIX (small): fold only when `frm`/`meta.via` == "conductor",
  or namespace control-plane kinds behind a capability. Becomes the battery's slice 1.
- **R12 ALREADY CORRECT** (validation, not a bug): cmd_bifrost_ack keys the refusal on
  sender==acker, so an addressee acking a message sent TO them is allowed -- exactly
  deepseek's recommended rule. Pin it so it stays correct.
- **R9 DOWNGRADED**: ack() writes independently of promoted()'s display-only suppression --
  no durable ack is lost. The concern is a promoted-vs-lookback COHERENCE pin (== R17), not
  data loss. Keep as a coherence test, not an emergency.

### Merged priority (next-sprint T028 acceptance gates)
1. R15 forged-ledger-update injection (real, proven, small fix) + R4/S1 drainer watchdog
   (real, converged) -- the two verified survivability/trust gaps, fix + regression pin.
2. Cross-slice seams: R9/R17 scan-coherence, R8 ring-overflow loss, my P3 transition storm.
3. Concurrency storms: R16/R1 dual-watcher kill-storm, my cursor storm, the Chaos Hour.
4. Adversarial-insider: R15 generalized + my spoofed-actor ack + the Newborn Gauntlet
   (deepseek plays the quarantined newborn -- the strongest single validation).
5. Long-horizon: R14 72h soak + my 30-Day Entropy Sim + R18 method-rot (battery self-audit).
6. Correctness edges: my S4 fork/cycle, R6 tiebreaker determinism, S5/R13 P7 poisoning+cold,
   R10/R11 P4-P5 pointer/clock anchors, my P4 stamp evasion.

Standing method: each kill -> a ledger task whose acceptance IS the failing test; graded
batteries (T018 endings, P7 show-nothing, the Newborn rubric) pre-registered behind the fence.
