# Comms/Messaging Pillar -- Dual-Fenced Analysis + Reconciled Plan (T016)

Status: current (plan awaiting Daniel's approval)
Date: 2026-07-09
Method: docs/pillar-analysis-method.md, dual-blind: claude and deepseek investigated
independently behind a fence (neither saw the other's findings until both reports were on
disk), then reconciled here.
Inputs: research/reviewed/claude-comms-pillar-fenced-2026-07-09.md (first-party, written
before reading the peer's) + research/reviewed/deepseek-comms-pillar-2026-07-09.md
(peer report, preserved verbatim). Daniel's ask quoted in both.

---

## 1. Exhibit A -- the disease demonstrated itself DURING the investigation

Claude sent the fenced ask to deepseek at 13:06:22Z (bus msg 1783602382637-0). DeepSeek
investigated with tools and replied at ~13:08Z (msg 1783602506398-0). The reply NEVER REACHED
the investigator: a `bifrost_wake.py --agent claude` watcher from the PREVIOUS session
(armed 08:57:48 local with an 8-hour deadline, its parent session dead ~8 seconds later)
was still blocking on claude's inbox. Its `wake_block()` calls `bus.wait(advance=True)`
(core/comm/bifrost_api.py:57) -- overriding wait()'s own documented detect-don't-consume
default -- and bifrost_wake.py then DISCARDS kinds {trace, reply, steer} as noise
(scripts/bifrost_wake.py:25,49). Net effect: the reply was consumed and dropped; every
subsequent inbox peek said "no new messages"; the investigation stalled until the stream was
inspected directly (cursors don't delete entries -- the report was recovered verbatim).

Three components, each individually defensible (bounded cursor semantics; a noise filter so
the waker doesn't fire on chatter; runner replies deliberately non-answerable), composed into
silent message loss for the coordinating agent. This is the second instance of the
consume-without-display class in two days (T014 defect 2b was the deepseek-side mirror).
It is the strongest possible confirmation of Daniel's "fragile mess" framing, and it makes
one structural fact vivid: ONE cursor per agent id, MANY possible consumers (live session,
wake watcher, MCP server, CLI), and NO consumer discipline. runner_lock solves exactly this
race for runners -- nothing solves it for the rest.

Immediate action taken 2026-07-09: stale watcher killed (pids 9036/28688); reply recovered
from the stream and preserved; code fix is slice P0 below.

## 2. The two fenced theses -- and why both are right

- CLAUDE (the corpus axis): the system captures its past superbly but never RETIRES it.
  Notes, docs, and ledger proposals are append-mostly with no supersession edge and no
  declared precedence, so "current" exists only as recency-inference that every reader
  re-derives -- and sometimes gets wrong. Evidence highlights: 65 active notes with FOUR
  co-existing "where-we-are" variants (wrap's default title is dated -- agent_cli.py:1125 --
  defeating update-by-title); docs/master-directive-list-2026-07-05.md still declares itself
  "SINGLE SOURCE OF TRUTH" for a lane model AGENTS.md has since abolished; ledger tasks
  T002-T007 sit "proposed" since 07-05 under that dead model; the atlas current-pointer
  surfaces 07-02 notes beside 07-08 ones; `status` answers machine health, not project state.

- DEEPSEEK (the feed axis): everything authoritative is PULL-only, transmitted at boot, and
  frozen thereafter. A live agent's knowledge of "what is current" drifts from startup until
  restart: no ledger-transition broadcast, the stateless peer's onboarding digest is baked
  into its system prompt once, promoted()/locks are visible only to whoever thinks to ask,
  and bus messages carry no "still current?" bit and no handled/acknowledged lifecycle.

Reconciled thesis (one sentence): CURRENT-NESS IS NEITHER DECLARED AT THE SOURCE NOR
PROPAGATED TO THE LIVING -- surfaces never mark what superseded them (so cold boots inhale
stale law), state changes never push to running agents (so warm agents drift), and the
strategic WHY is indexed nowhere (so lookback cannot answer it); the fix is to make
supersession, propagation, and rationale-lookback first-class, and to add consumer
discipline on the one-cursor-per-agent transport -- NOT to add transport, capture, or
summarizer machinery.

## 3. Convergences (independent agreement = highest confidence)

1. Transport + capture layers are good; the fragility is informational. Do not rebuild pipes.
2. The governed task ledger + boot RULE is the best anti-ambiguity device in the system; its
   pattern (declare authoritative state, instruct against stale messages) is the template.
3. The coordination barrier (docs/coordination-plan-synthesis.md Phases A-D) is sound but is
   NOT the root fix and must not be built first. Schedule after the information loop closes.
4. promoted() is the right durable record and is under-surfaced (no boot digest, no push).
5. Message lifecycle is open: read != handled != acknowledged (T014 2b, Exhibit A, no ack).
6. NOT-build union: no new transport; no durable bus; no per-message TTL; no LLM triage/
   summarizer jobs; no CRDT/consensus reopening; no comprehensive-manual documentation sweep.

## 4. Complementary uniques (each report saw what the other could not)

- Claude only (needs repo-browsing eyes): the notes pileup mechanics (wrap:1125), doc
  dead-law with no currency stamps, untracked docs invisible to peers, proposed-task decay,
  ARCHITECTURE.md existing but unreferenced by boot/AGENTS.md, WHY-corpus (docs/,
  research/reviewed/, git bodies, docstrings) unreachable by any lookback verb.
- DeepSeek only (the lived stateless-peer view): onboarding frozen at runner start; no
  mid-session ledger propagation; inbox has no actionable-vs-informational triage; ack
  lifecycle proposal; heartbeat backstop concept.

## 5. The reconciled slice plan (each gated; smallest diffs first)

P0. WAKE LISTENER: DETECT, DON'T CONSUME (bug fix -- first)
    bifrost_api.wake_block -> advance=False (bus.wait's own safe default); bifrost_wake exits
    on a wake-worthy message WITHOUT advancing (the woken session consumes normally); skipped
    kinds are never advanced past. Add a consumer-discipline guard: the wake listener refuses
    to arm (or stands down) when another consumer holds the agent's wake heartbeat, mirroring
    runner_lock. Regression tests pin: a kind=reply landing while a watcher runs MUST still
    appear in the next bifrost-sync.
    GATE: T016-shaped drill -- directed reply lands during an armed watcher and is readable
    afterward; watcher still wakes on answerable kinds.

P1. NOTES SUPERSESSION (kills the biggest cold-boot ambiguity)
    Mostly WIRING, not building: the note verb ALREADY supports title-supersession and an
    explicit --supersedes id (discovered at reconciliation -- built-not-wired). The fix:
    wrap default title -> bare "where-we-are" (date goes in the body) so title-supersession
    actually fires; note --retire for one-shots; notes default = current-only (--all for
    archaeology); boot renders only current. One migration pass over today's 65 (collapse
    where-we-are* via --supersedes, retire completed-arc status notes + consumed handoffs,
    delete placeholder).
    GATE: default notes listing <= ~15 with exactly ONE where-we-are; boot shows zero
    superseded entries; "which note is current?" answerable by verb.

P2. BOOT ORIENTATION HEADER + PRECEDENCE DOCTRINE (the new-agent fix)
    First lines of boot become: map pointer (docs/ARCHITECTURE.md + AGENTS.md), THE current
    where-we-are (one line), the governing plan doc for the active arc, and the precedence
    rule stated once: ledger > current notes > promoted > live bus; superseded/stale is
    labeled. Compress DONE tasks to one line (count + latest commit) -- titles live in task
    list. This directly upgrades the stateless peer too: its 6000-char onboarding head
    currently spends its budget on DONE task titles. AGENTS.md gains the same map pointer.
    GATE: cold-start drill -- a fresh agent id boots and answers, from boot output alone:
    what is current, where is the map, which plan governs, what must I not redo. DeepSeek's
    folded onboarding head inspected to contain the orientation block.

P3. LEDGER-UPDATE PUSH (deepseek C1 -- kills mid-session drift cheaply)
    task_ledger emits kind=ledger_update broadcast on every transition; runners intercept it
    hint-style (fold into next turn, never answer). Bus stays ephemeral; the ledger file
    remains the truth -- this is a doorbell, not a second source.
    GATE: peer moves a task to DONE; deepseek's next reply reflects it within one turn,
    no restart, no human relay.

P4. DOC CURRENCY CONTRACT + GUARD (kills dead law)
    Header convention for docs/*.md: Status: current | superseded-by <doc> | historical (+
    date); stamp the live design docs once (master-directive-list -> historical,
    bifrost-sync-plan -> superseded-by coordination-plan-synthesis). Extend the
    comprehensibility-immune-system guards: flag unstamped docs, stale-claiming-current,
    and UNTRACKED files under docs/ (invisible-to-peers is a defect).
    GATE: guard's first run flags exactly the known offenders; zero unstamped after the
    pass; guard wired into ship gates.

P5. PROPOSED-TASK DECAY (finish what the RULE started)
    proposed older than N days -> rendered "(stale -- needs re-approval)" at boot; verbs:
    task reapprove / task abandon <id> --reason. Apply to T002-T007 as the migration.
    GATE: boot's proposed count reflects only live intent; each of T002-T007 explicitly
    re-approved or abandoned with a recorded reason.

P6. MESSAGE ACK LIFECYCLE (deepseek C4; Exhibit A's cousin)
    bifrost-ack <msg_id> writes a durable msg_ack event; promoted() view shows ack status;
    salient messages unacked after N hours render an unhandled flag. (Ack complements P0:
    P0 stops silent CONSUMPTION; acks close the handled-or-not loop on what IS seen.)
    GATE: handoff acked -> visible in promoted(); 6h-unacked handoff renders flagged.

P7. LOOKBACK: ONE QUERY OVER THE RATIONALE CORPUS (the "intelligent lookback" ask;
    merges claude S4 + deepseek C3)
    (a) boot gains a compact recent-decisions digest from promoted() with drill refs
    (deepseek C3). (b) New lookback "<question>" verb searching, layered: docs (current
    first) -> research/reviewed -> note bodies -> promoted -> chapter summaries -> git log
    subjects+bodies; every hit carries its drill pointer (path / note id / event ref / sha).
    Reuses existing ranking + event-query machinery; no embeddings in v1; add a tiny hit
    counter so the NEXT audit has a funnel.
    GATE: pre-registered probe battery (6 strategic questions: why is the bus ephemeral;
    why no CRDTs; why were lanes abolished; where did the forge gate come from; why
    write-once notes; what governs coordination now) -- each returns its governing artifact
    in top-3. Battery committed BEFORE implementation (pre-registration fence).

P8. GATED BACKSTOPS (build only if gates above leak)
    State heartbeat (deepseek C2) only if P3's gate shows drift in practice; inbox triage
    view (deepseek C5) folded into bifrost-sync polish if P2's cold-start drill still shows
    orientation cost. Explicitly deferred, not planned.

THEN: schedule coordination-plan-synthesis Phase A (ACK-barrier + snapshots) as its own arc
-- both fenced passes independently ranked it after the information loop. It closes the
remaining seen-vs-acted gap at the control-plane level (and subsumes nothing above).

## 6. What we will NOT build (union of both fenced lists)

New transport or unified-inbox rework; durable bus (promotion stays the bridge);
per-message TTL; LLM message classifiers or generated current-state summaries (rot;
mechanical supersession + declared precedence instead); embeddings for lookback v1;
auto-DELETION anywhere (supersede/retire are reversible flags on an append-only substrate);
CRDTs/consensus/orchestrators (already correctly rejected); a documentation rewrite sweep
(ARCHITECTURE.md + MODULE_INDEX already implement the surviving living-docs pattern).

## 7. Honest bounds

- Information-surface telemetry is thin: recall has a funnel; notes/docs/lookback do not
  (P7 adds the first counter). Several claims rest on structural evidence + live probes +
  two lived incidents (n small) rather than longitudinal numbers.
- Exhibit A's root cause is verified by code-read (bifrost_api.py:57 + bifrost_wake.py:25)
  and by the recovered stream state, but the fix is NOT yet built or drill-proven (P0).
- The UI cockpit (scripts/bifrost_ui.py) was not audited this pass; it inherits P1/P4
  staleness until they land.
- Both fenced reports agree the barrier plan stays valuable; deferring it is a sequencing
  claim, not a quality judgment on that design.
