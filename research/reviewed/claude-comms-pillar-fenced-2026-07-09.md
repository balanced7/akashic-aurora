# Comms/Messaging Pillar Analysis -- Claude's FENCED independent report (T016)

Written 2026-07-09 BEFORE reading DeepSeek's fenced pass (dual-blind discipline; reconciliation
comes after both reports exist). Method: docs/pillar-analysis-method.md -- triangulated design
docs vs code vs telemetry vs lived experience (this morning's session-start IS a new-agent
cold-start; its frictions are logged below as first-class evidence).

Daniel's ask, verbatim: "I want to make sure our communications infrastructure and messaging
system are no longer a fragile mess where new agents spawn and are confused on what is current
or not and where new agents don't understand how to navigate the information they have
available. I want to enable intelligent lookback, for agents to be able to understand the
strategic and architectural past with the ability to drill down to the pertinent and for there
to be as little to no ambiguity as possible about what the current state is."

---

## 0. Ground truth inventory (what exists and works)

The transport + capture machinery is GOOD. Verified by read + live use this session:

- Bus (core/comm/bus.py): ephemeral Redis Streams, per-agent inbox + broadcast with per-agent
  cursors, presence w/ Agent Cards (TTL 90s), doorbell pub/sub, T014 cursor semantics fixed and
  pinned by tests. Correct design split: ephemeral transport vs durable record (design delta F1).
- Durable projection (core/comm/promoter.py): SALIENT_KINDS {handoff, decision, completion,
  blocker} -> event ledger as kind=bifrost_msg; console control plane (interjection/bus_control/
  file_drop) also captured. Works (live-verified today: my T016 handoff was auto-promoted).
- Control plane: pause/halt/nudge/steer/interject + runner_lock + liveness worklive + launcher
  supervision. Fidelity ladder INFORM/STEER/INTERRUPT/HALT live.
- Context pillar (context/aggregator.py <- agent/initializer.py): boot assembles briefing/
  decisions/learnings/blockers/narrative/project_state, ranked, budget-fitted (~9k tokens),
  every entry with a source pointer, skeleton + drill-down. agent_cli.py boot renders it plus
  task ledger + notes + funnel + draft pointer + bifrost peek.
- Governed task ledger (state/coord/tasks.json + task verb): propose/approve/claim/start/verify/
  done with history + illegal-transition guards (live-verified today on T016). The "TASK LEDGER --
  obey THIS, not old messages" boot rule is the strongest anti-ambiguity device in the system.
- Narrative spine + firehose: story (atlas/track/chapter/beat, --raw drill to events),
  events --search/--around/--window/--get. Temporal drill-down machinery EXISTS end to end.
- Notes: write-once, update-by-title, ADR-ids, chronicles/memory.md regenerated projection.
- AGENTS.md: excellent door contract (boot/learn/recall-at/locks/bifrost/session hygiene/
  reporting contract).
- ARCHITECTURE.md: living subsystem map at stable altitude + auto-generated MODULE_INDEX.md --
  exactly the right artifact, shipped 07-07.

The failure is NOT missing machinery. It is that nothing ever RETIRES; see thesis.

## 1. Ranked failure modes (each with concrete evidence)

F1. NO SUPERSESSION PRIMITIVE ANYWHERE -- capture is append-mostly; retirement is manual and
    never happens.
    Evidence:
    a) agent_cli.py:1125 -- wrap default title is "where-we-are <date>", so every session mints
       a NEW note instead of updating THE where-we-are. Result: 4 co-active variants
       ("where-we-are", "where-we-are 2026-07-07", "... 2026-07-08 membrane+recall night",
       "... 2026-07-05 -> governed coordination..."). The write-once/update-by-title design is
       defeated by its own default.
    b) notes list = 65 ACTIVE notes, including per-arc status notes whose arcs are DONE
       (renew-stranda-status, renew-strande-status, session-bookends-status...), a one-shot
       "SESSION HANDOFF 2026-07-07" note, and a literal "placeholder" note
       (gemini-vision-bifrost-screenshot-output). Nothing distinguishes current from consumed.
    c) docs/master-directive-list-2026-07-05.md: self-labeled "SINGLE SOURCE OF TRUTH",
       prescribes per-agent file lanes -- doctrine ABOLISHED by current AGENTS.md ("any agent
       does any task... no permanent ownership"). It sits UNTRACKED in the working tree with
       nothing marking it superseded. A new agent reading docs/ chronologically adopts dead law.
    d) docs/bifrost-sync-plan.md (07-04, untracked) overlaps docs/coordination-plan-synthesis.md
       (07-04, the reconciled successor) -- neither points at the other; only tribal memory says
       synthesis governs.
    e) Task ledger: T002-T007 sit "proposed" since 07-05, authored under the abolished lanes
       model (owners deepseek-plumbing etc.). No decay/re-approval mechanism; boot renders
       "proposed 6" as if live.
    f) Contrast: recall/lessons DID get supersession tooling in the last two arcs (bench/unbench,
       staleness cue AKASHIC_STALE_CUE_DAYS, forge rehab, graduate verb). Notes/docs/ledger-
       proposed got none. The corpus that got curation loops (lessons) measurably improved --
       the pattern is proven in-house; it just was not applied to the other surfaces.

F2. "CURRENT STATE" IS ASSEMBLED, NOT DECLARED -- precedence lives implicitly in boot's
    rendering order, not as doctrine any agent can cite or query.
    Evidence:
    a) The atlas current block in this morning's boot cites "note: next-focus (2026-07-02)" and
       "note: where-we-are (2026-07-02)" while 07-08 notes exist -- boot faithfully surfaces a
       stale pointer (narr:atlas:current) next to fresh notes, with no arbitration.
    b) The only explicit precedence statement in the system is the ledger RULE line ("obey THIS,
       not old messages") -- scoped to tasks only. Nothing says notes > bus backlog, or
       current-doc > older-doc.
    c) `status` verb ("honest system status") answers machine health (backend, counts, spine
       health), not "what is the project state now". The name overpromises (names-that-lie).
    d) 12 files uncommitted right now, incl. core/comm/session_state.py (a whole module) --
       working-tree state visible to nobody's boot. Discovered only via git status heads-up.

F3. LOOKBACK SERVES "WHAT HAPPENED" BUT NOT "WHY IS IT THIS WAY" -- the temporal drill exists;
    the design/rationale drill does not.
    Evidence:
    a) Probe (live, today): events --search "bus ephemeral durable promotion decision" returns
       4 tangential note-decision events; the actual rationale (bus.py docstring "design delta
       F1", the synthesis doc sec.1) is unreachable by any lookback verb. The WHY corpus --
       docs/*.md, research/reviewed/*.md, git commit bodies, module docstrings -- is not indexed
       by events/story/recall.
    b) story --themes returns generic clusters (memory 68 beats, evaluation 51, narrative 49,
       logging 32, routing 23) -- activity taxonomy, not strategic arcs; no theme answers "how
       did coordination evolve".
    c) research/reviewed/ holds the richest WHY documents (fenced reviews, surveys, red-teams)
       and NO verb surfaces them; they are findable only by knowing the directory exists.
    d) The system's best rationale records are git commit messages (paragraph-length, decision-
       bearing -- see a106af8, 963ba89) -- reachable only via git log, which no door verb wraps.

F4. NEW-AGENT ONBOARDING IS CONTRACT-FIRST, MAP-NEVER -- an agent learns HOW to use the door
    but not WHERE it is standing.
    Evidence:
    a) Neither AGENTS.md nor boot output references docs/ARCHITECTURE.md (the living map,
       built precisely for orientation) or the ROADMAP. Verified by full read of AGENTS.md and
       two live boots today.
    b) discover lists 36 verbs FLAT, alphabetical-ish, no task-oriented grouping ("to know what
       is current / to look back / to coordinate / to contribute"). A new agent must already
       know which of 36 doors matters.
    c) The stateless peer gets LESS: bifrost_runner_deepseek.onboarding_context() truncates boot
       to the first 6000 chars (head of ledger + notes) -- whatever is NOT in the head never
       reaches DeepSeek's system prompt. Head composition is therefore load-bearing, and today
       it spends its budget on DONE task titles (9 closed tasks render before lessons).
    d) Historical incident (the disease's index case): docs/master-directive-list-2026-07-05.md
       sec.1 quotes Daniel: "A lot of deepseek agents just now discovering past messages and
       starting work... Right now things are too chaotic." Root cause listed there: no single
       source of truth for who owns what -- i.e., exactly F1+F2 in 07-05 clothing. The ledger
       RULE fixed the task slice of it; the info-surface slice (docs/notes) was never fixed.
    e) 07-05 promoted-message archaeology: agents relaying GPT analyses to each other with
       "I can't write to the knowledge base... can you save this as a durable note?"
       (deepseek-plumbing -> deepseek, 3 msgs 12:52-13:02) -- capability asymmetry turned peers
       into couriers; durable capture depended on WHO could write, not on WHAT deserved keeping.
       (Largely mitigated since: deepseek has guarded write + note tools now. Kept as evidence
       of the failure class: capture paths must not depend on courier chains.)

F5. MESSAGE DELIVERY HAS NO ACKNOWLEDGEMENT SEMANTICS -- seen != acted-on != acknowledged.
    Evidence:
    a) T014 defect 2b: recipient runners consumed directed replies silently (wait(advance=True)
       + should_answer filter = consume-without-display). Fixed for that path, but the CLASS has
       no primitive: nothing distinguishes "cursor advanced past it" from "agent processed it".
    b) docs/bifrost-sync-plan.md gaps 1-2 (pause is blind; no rendezvous) and the synthesis
       Phase A (ACK-barrier + snapshot, A1-A6) are the designed fix -- STILL UNBUILT (ledger
       has no Phase A task; coordination-layer-plan note says "NEXT = build Phase A").
    c) Handoffs are fire-and-forget: handoff verb writes a briefing consumed by next boot, but
       sender never learns whether/when it was read (no read-receipt on briefing consumption).

Ranking rationale: F1 and F2 are the ambiguity Daniel names; F3 is the lookback he wants; F4 is
the new-agent experience; F5 is real but partially parked in an existing, approved plan (Phase A)
-- it should be scheduled, not redesigned.

## 2. Loop-altitude thesis (one sentence)

The system captures its past superbly but never retires it -- every surface (notes, docs, ledger
proposals, atlas pointers) is append-mostly with no supersession edge and no declared precedence,
so "current" exists only as recency-inference each reader re-derives, and sometimes gets wrong;
the fix is to make SUPERSESSION and PRECEDENCE first-class objects (declare-current, auto-retire,
WHY-indexed lookback), not to add more capture or transport.

(The lessons corpus is the control group proving the loop closes when built: recall got
bench/staleness/forge curation over the last two arcs and its funnel improved; notes/docs/
proposed-tasks are the same disease untreated.)

## 3. Proposed fixes -- gated slices

S1. SUPERSESSION FOR NOTES (the biggest ambiguity for the smallest diff)
    - wrap default title -> bare "where-we-are" (update-by-title finally updates; the dated
      history remains in the event ledger, and wrap --commit can stamp the date in the BODY).
    - note verb learns supersedes: re-noting a title auto-marks the prior version; add
      note --retire <id|title> for one-shots (handoff notes auto-retire on boot consumption).
    - notes default listing = current only; notes --all keeps archaeology; boot RECENT NOTES
      renders only current + unexpired.
    - Migration pass over the 65: collapse where-we-are* into one, retire done-arc status notes
      (their content lives on in chronicles/git), delete the placeholder.
    Evidence gate: notes(default) <= ~15 and contains exactly ONE where-we-are; cold-boot
    context contains zero superseded entries; "which note is current" answerable by verb.

S2. DOC CURRENCY CONTRACT + GUARD (kill the dead-law problem)
    - Header convention for docs/*.md: Status: current | superseded-by <doc> | historical,
      + date. Stamp the ~dozen live design docs once.
    - A comprehensibility-immune-system guard (that pillar shipped 07-07 -- extend it): flag
      (i) docs claiming currency older than N days untouched, (ii) known-contradiction pairs
      (lanes vs no-lanes), (iii) UNTRACKED docs/ files (a doc invisible to git is invisible to
      peers -- today: bifrost-sync-plan, master-directive-list, the-environment-decides).
    Evidence gate: guard run flags master-directive-list + bifrost-sync-plan on first pass;
    after stamping, zero unstamped docs; guard green in ship gates.

S3. LEDGER PROPOSED-DECAY (finish the RULE's job)
    - proposed older than N days -> auto-flag stale; boot renders "proposed (stale, needs
      re-approval)" distinctly; task re-approve or task abandon with reason.
    Evidence gate: T002-T007 each explicitly re-approved or abandoned; boot's proposed count
    reflects only live intent.

S4. WHY-LOOKBACK: ONE QUERY OVER THE RATIONALE CORPUS (the "intelligent lookback" ask)
    - New verb (or recall mode): lookback "<question>" searching, in layered order: docs/*.md
      (status: current first), research/reviewed/*.md, note bodies, promoted messages, chapter
      summaries, git log subjects+bodies -- returning per-layer hits with drill pointers
      (doc path / note id / event ref / commit sha). Reuses the existing ranking + event-query
      machinery; NO new storage, NO LLM summarization in v1.
    - story --themes stays; add theme aliases from track/arc names so strategic arcs are
      addressable.
    Evidence gate: pre-registered probe battery of 6 strategic questions ("why is the bus
    ephemeral", "why no CRDTs", "why were lanes abolished", "where did the forge gate come
    from", "why write-once notes", "what governs coordination now") -- each must return its
    governing artifact in top-3. Also: time-to-answer for a fresh agent measured before/after.

S5. ORIENTATION HEADER: BOOT'S FIRST 10 LINES = THE MAP (fixes new-agent cold start + the
    stateless-peer 6000-char head)
    - Boot output begins: pointer to ARCHITECTURE.md + AGENTS.md; THE current where-we-are (one
      line); the governing plan doc for the active arc; the PRECEDENCE DOCTRINE stated once
      ("ledger > current notes > promoted > live bus; superseded/stale is labeled"); then task
      ledger as today. AGENTS.md gains the same map pointer.
    - Boot budget shifts: DONE tasks compress to one line ("9 done, latest @a106af8") -- titles
      available via task list; the freed head-budget goes to orientation. (Directly improves
      what DeepSeek's trimmed onboarding actually receives.)
    Evidence gate: cold-start drill -- fresh agent id boots and must answer from boot output
    alone: what is current? where is the map? which plan governs? what may I not redo? Scored
    before/after; DeepSeek's onboarded head inspected to contain the orientation block.

S6. SCHEDULE PHASE A (ACK-barrier + snapshots) -- do not redesign it
    - The approved synthesis (docs/coordination-plan-synthesis.md sec.5 Phase A1-A6) already
      specifies ACK semantics + snapshot schema; it closes F5. Propose it as its own ledger task
      after T016's info-surface slices land (it is coordination-shaped, not info-shaped).
    Evidence gate: per-slice tests already written into the plan (A1-A6 each carry one).

Sequencing: S1+S5 first (cheapest, highest ambiguity reduction, zero new subsystems), S2+S3
next (guards + hygiene), S4 as the one genuinely new capability, S6 scheduled after.

## 4. What I would explicitly NOT build

- A new transport, protocol, or "unified inbox" -- the bus + promotion split is correct and
  now test-pinned; the fragility is informational, not transport-level.
- An LLM-generated "current state summary" job -- rot-prone, unverifiable, and the living-docs
  lesson (stable-altitude map + autogen index, or gated) already names the survivable shapes.
  Mechanical supersession + declared precedence beats generated prose.
- A comprehensive manual / re-documentation sweep -- living_docs_survive_only_if_stable_autogen
  _or_gated; ARCHITECTURE.md + MODULE_INDEX already implement the surviving pattern.
- Vector/semantic search infra for S4 v1 -- the corpora are small (dozens of docs, 65 notes);
  the existing ranking primitives suffice; add embeddings only if the probe battery fails.
- Auto-deletion of anything -- supersede/retire = reversible flags (deterministic + reversible
  everywhere); the append-only substrate stays append-only.
- CRDTs/consensus/etc. -- already correctly rejected in the synthesis; nothing here reopens it.

## 5. Honest bounds

- Telemetry for information-surface waste is thin: recall has a funnel; notes/docs/lookback have
  no usage counters, so several claims rest on structural evidence + 2 live probes + one lived
  cold-start (n=1) rather than longitudinal numbers. S4's gate should add a tiny lookback-hit
  counter so the NEXT audit has a funnel.
- I did not audit scripts/bifrost_ui.py's rendering of these surfaces (UI altitude); if the
  cockpit displays stale notes/docs it inherits F1/F2 until S1/S2 land.
- The 07-05 courier evidence predates deepseek's write grant; weight it as failure-class
  evidence, not current-state.
