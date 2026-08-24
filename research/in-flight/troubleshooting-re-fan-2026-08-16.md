# Troubleshooting + RE methodology -- 6-branch deepseek fan, 2026-08-16

Provenance: Daniil's ask ('what do the best troubleshooters do... how do reverse engineering efforts do their tasks') -> fan by seat 7b78fb20 (ask 354da0f0: debugging method / SRE-incident / non-software diagnostics / RE workflow / time-travel debugging / route-record synthesis). Feeds the T323 fence. Confidence tags are the branches' own.

# ask 354da0f0 -- DONE
--- branch 0 [ok] ----------------------------------------
1. **Scientific debugging (Zeller)** — Treat a failure as a rule-out experiment: enumerate hypotheses and the observations that would distinguish them.  
   **Mechanism:** A probe only changes belief if its predicted outcome differs across hypotheses; this forces each observation to carry discriminative weight.  
   **Confidence:** [well-known]

2. **Delta debugging / ddmin** — From a failing input, repeatedly remove chunks and test whether the reduced input still fails; keep reductions that preserve failure, restore those that do not.  
   **Mechanism:** Monotonic failure-under-reduction exploits redundancy to isolate the minimal set of elements necessary to reproduce.  
   **Confidence:** [well-known]

3. **Git bisect** — Binary search over an ordered revision history using only a repeated good/bad oracle.  
   **Mechanism:** A monotonic ordering plus a reliable binary test gives logarithmic elimination; the discipline is protecting the oracle from noise.  
   **Confidence:** [well-known]

4. **Half-splitting** — Probe the midpoint of a signal/call path and ask whether the fault is upstream or downstream of the probe point.  
   **Mechanism:** A single directional observation on a causal chain discards half the remaining search space.  
   **Confidence:** [well-known]

5. **Hypothesis ledger** — Before each probe, write the hypothesis, the expected result if true/false, the actual result, and the revised hypothesis.  
   **Mechanism:** Pre-commitment prevents post-hoc reinterpretation of failure and leaves a checkable trail of reasoning.  
   **Confidence:** [likely]

6. **Cheapest discriminating test first** — Rank candidate probes by information gain per unit cost and run the cheapest test that splits the current hypothesis set.  
   **Mechanism:** Value-of-information maximization avoids expensive depth-first pursuit of a single plausible cause.  
   **Confidence:** [likely]

7. **Rubber-duck / explain-to-commit** — Explain the intended fix or current reasoning to an inert listener or in a commit message before acting.  
   **Mechanism:** Forced sequential articulation exposes hidden assumptions and missing causal links because the explainer must generate sentences, not merely recognize a symptom.  
   **Confidence:** [likely]

8. **Breadth-first orientation before depth** — Experts first map system topology, recent changes, and symptom class; novices dive into the first suspect.  
   **Mechanism:** Cheap structural priors localize the fault upstream and reduce anchoring on salient but irrelevant code.  
   **Confidence:** [likely]

9. **Symptom-vs-cause discipline / refuse to patch before reproduce** — Treat the error or stack trace as a symptom, not the cause; do not edit until the failure is reproduced.  
   **Mechanism:** A repeatable reproducer is a reusable oracle; without it, a change cannot be known to fix rather than mask the fault.  
   **Confidence:** [well-known]

10. **Minimal failing test before reasoning** — Shrink the reproducer and environment to the smallest failure-preserving subset before deep explanation.  
    **Mechanism:** Smaller surfaces remove confounds and expose the necessary condition(s) for failure.  
    **Confidence:** [well-known]

---

**Most transferable to CONTEXT:**

1. **Hypothesis ledger / pre-registered probe** → attach to the **task ledger**.  
   Gate investigation transitions so a seat must write the hypothesis, predicted Eye/connectome address, and expected observation before a probe is allowed. This turns saved routes into checkable, supersede-not-mutate records.

2. **Breadth-first orientation / cheapest discriminating test** → attach to **THE EYE**.  
   Before following a trace deep, use `find/freq` across THE EYE to enumerate candidate prior sessions/routes, then choose the next hop that most cheaply splits the candidate set instead of chasing the first hit.

3. **Minimal reproducer / refuse to patch before reproduce** → attach to **recall-at-action**.  
   Fire a stored lesson before any “patch/fix/edit” action requiring the seat to cite a reproducible address (`session:line`) or a minimal route that provokes the failure, gating action on evidence.

--- branch 1 [ok] ----------------------------------------
1. **Symptom-keyed runbooks/playbooks.** Alert or observed symptom maps directly to a playbook branch ("if you have hit this, go here"). MECHANISM: retrieval key is the symptom, not a hypothesized root cause, so response starts before diagnosis converges. [well-known]

2. **Brendan Gregg's USE method.** For every resource, sweep Utilization / Saturation / Errors. MECHANISM: forced per-resource coverage prevents anchoring on the first plausible resource; saturation and errors catch failures that utilization alone misses. [well-known]

3. **RED method.** Rate / Errors / Duration per service. MECHANISM: the three-part signature separates demand, failure, and latency, letting a specific RED pattern key a specific runbook. [well-known]

4. **Incident command roles: driver + scribe.** Driver acts and narrates; scribe records timeline, commands, decisions. MECHANISM: route capture is a dedicated role, so the route gets written even when the driver is overloaded. [well-known]

5. **Blameless postmortem closes the loop into runbook update.** The incident timeline becomes a correction or extension of the symptom-keyed runbook. MECHANISM: every incident improves the reusable route; failure is converted into a better next entry point. [well-known]

6. **Game days / drills.** Teams re-walk runbooks against injected failures. MECHANISM: exercise tests route validity and refreshes recall, acting as cache invalidation by rehearsal rather than by waiting for real incidents. [well-known]

7. **On-call handoff notes.** Outgoing responder persists current position, completed branches, and next steps. MECHANISM: incoming responder resumes from saved state instead of replaying from scratch. [likely]

**Most transferable to Akashic Aurora:**

1. **Symptom-keyed retrieval** → attach to **recall-at-action**: store routes with "Use when <symptom>, before <action>" as the firing key.  
2. **Scribe as route-recorder** → attach to **THE EYE**: write route steps as append-only, addressable session:line events during the walk, not after-the-fact reconstruction.  
3. **Closed-loop postmortem → runbook update** → attach to **connectome**: after a route is walked, add a superseding route edge or evidence link instead of mutating the old route.

--- branch 2 [ok] ----------------------------------------
1. Kepner-Tregoe IS / IS-NOT — Practice: define a problem by what it is and is not across what/where/when/extent. Mechanism: recording the negative space forces any candidate cause to explain both presence and absence, sharpening a vague symptom into a bounded target. Confidence: well-known.

2. Kepner-Tregoe distinctions and changes — Practice: compare unique features of the IS side against the IS-NOT side, then ask what changed at those distinctions. Mechanism: converts open-ended “why” into a small candidate set where only changes aligned with distinctions can survive. Confidence: well-known.

3. Clinical differential diagnosis — Practice: maintain an explicit ranked list of candidate hypotheses ordered by base rates (“hoofbeats → horses”) before testing. Mechanism: a mandatory prior stops rare/exotic causes from displacing common ones without differentiating evidence; ranking makes the next investigation a deliberate choice. Confidence: well-known.

4. Clinical discriminating tests — Practice: choose the next test/observation by how much it should move probability between the top hypotheses, then revise the ranking. Mechanism: evaluates evidence by its ability to discriminate among alternatives, not merely by whether it is positive or negative. Confidence: well-known.

5. NTSB factual-record-before-analysis — Practice: assemble and freeze a shared factual record before causal analysis begins. Mechanism: separates collection from interpretation so early pet theories cannot suppress contradictory facts; every later causal claim has a checkable factual base. Confidence: well-known.

6. NTSB timeline reconstruction — Practice: reconstruct the event sequence as an uninterpreted timeline, then overlay causal links afterward. Mechanism: temporal order exposes precursors, concurrency, and impossible causes; sequence stays separate from explanation and can be walked forward/backward. Confidence: well-known.

7. NTSB fault trees — Practice: model failure as AND/OR prerequisites (accident requires hazard AND failed controls). Mechanism: reveals hidden conjunctions and missing defenses rather than forcing one root cause; intermediate nodes become stable savepoints for revision. Confidence: well-known.

8. 5-whys / fishbone failure modes — Practice: 5-whys pursues one linear causal chain; fishbone brainstorms causes into categories. Mechanism: both are cheap divergence/generation, but they usually select a familiar single cause and offer no ranking or test; they fail when multiple interacting causes or negative evidence matter. Confidence: well-known.

9. TRIZ contradiction analysis — Practice: restate the problem as a contradiction between two desired parameters, then apply known cross-domain principles to resolve it. Mechanism: reframes the issue as a structural trade-off rather than a search for a guilty component; most transferable for persistent design conflicts, less for one-off factual failure. Confidence: likely.

Most transferable to Akashic Aurora:

- NTSB factual-record-before-analysis → attach to THE EYE: require an addressable raw timeline/route segment to be committed before connectome edges or recall-at-action lessons cite it; causal claims then cite that committed segment.  
- Clinical ranked differential + discriminating tests → attach to TASK LEDGER: represent competing hypotheses as ordered tasks whose gated transitions require a discriminating evidence address to promote/demote them.  
- Kepner-Trego IS / IS-NOT → attach to CONNECTOME: add typed negative-evidence edges and distinction fields so routes record absence, negative space, and “where it did not happen,” not only what happened.

--- branch 3 [ok] ----------------------------------------
1. **Annotated database as the artifact** — Practice: analysts persist names, comments, bookmarks directly onto the binary in the shared project database. Mechanism: the database is a durable, addressable overlay on an immutable object; annotations accumulate and outlive the session, making understanding a transferable artifact. [well-known]

2. **Cross-reference chains** — Practice: follow xrefs from known sources/sinks to trace who-uses-what. Mechanism: each reference is a typed, navigable edge; traversal turns scattered local answers into a walkable graph. [well-known]

3. **BinDiff-style annotation transfer** — Practice: diff a new binary against an already-reversed similar one and port names/comments. Mechanism: structural correspondence between code graphs allows the annotation map to transfer; a recognized rhyming problem reuses prior understanding instead of re-deriving it. [likely]

4. **FLIRT signatures** — Practice: match known library code by signature and auto-apply names. Mechanism: memoized recognition of already-understood code; identification happens at match time, so known regions are never re-reversed. [well-known]

5. **Anchor-point triage** — Practice: start from strings, imports, entry points and walk inward. Mechanism: known anchors provide stable coordinates in an unlabeled space; effort is concentrated where signal already exists. [well-known]

6. **RE notebook discipline** — Practice: log hypotheses with addresses, evidence, and confidence as analysis proceeds. Mechanism: checkable provenance keeps claims anchored and revisable; understanding is attached to addresses, not to memory. [likely]

Most transferable to CONTEXT:

1. **Annotated database as artifact → THE EYE**: route annotations, comments, and savepoints must be durable, addressable overlays on `session:line` events, supersede-not-mutate, not ephemeral chat.
2. **Cross-reference chains → connectome**: expose typed `formed_by/formed_at/formed_via/evidence` edges as walkable xref-style chains so a saved route is a reified path through existing edges.
3. **FLIRT-style memoized recognition → recall-at-action**: store compact fingerprints/signatures of known problem shapes keyed to symptom; on match, fire the known route/payload before the seat acts, so a known problem is never re-derived from scratch.

--- branch 4 [FAIL] ----------------------------------------
(model returned an empty answer (finish_reason=stop))

--- branch 5 [ok] ----------------------------------------
1. Practice: Use a fixed, small step vocabulary rather than prose.  
Mechanism: Each step is a typed node with a predicate and an address — observation, discriminating-test, decision, dead-end, anchor, handoff — so a route is executable and diffable, not a paragraph to re-read.  
Confidence: [well-known]

2. Practice: Record dead ends as first-class negative results, not footnotes.  
Mechanism: A dead-end step stores the hypothesis tested, the test that refuted it, and the receipt. Future walkers skip that branch and keep the IS-NOT space as a pruned search tree.  
Confidence: [well-known]

3. Practice: Make discriminating tests branch by outcome.  
Mechanism: A test step carries a predicate and an outcome map `{result -> next_step}`. The route becomes a decision graph, so one saved route covers multiple paths and can terminate early.  
Confidence: [well-known]

4. Practice: Use anchors as stable semantic landmarks, not raw line numbers.  
Mechanism: An anchor step stores a content-derived signature or event title, with its current address. When the terrain shifts, only the address pointer is superseded; the route topology stays intact.  
Confidence: [likely]

5. Practice: Use handoff steps to jump to another route or corpus address.  
Mechanism: Handoff edges reuse already-verified sub-routes and allow long traversals to be assembled from small, independently maintained fragments.  
Confidence: [well-known]

6. Practice: Separate the trigger signature from the route body.  
Mechanism: Metadata stores the symptom fingerprint — event types plus payload shape — so recall-at-action can key on it without parsing route content, making matching fast and indexable.  
Confidence: [well-known]

7. Practice: Store entry preconditions as checkable assertions.  
Mechanism: Preconditions reference anchors or observations; if they fail, the route refuses to start, preventing misapplication in a different territory.  
Confidence: [well-known]

8. Practice: Carry last-verified and a small set of staleness flags.  
Mechanism: A route is `active`, `stale`, or `superseded`, with a last-verified timestamp. Trust decays with age, but staleness cues a “walk but verify” mode rather than blocking use.  
Confidence: [well-known]

9. Practice: Count walks as a confidence signal.  
Mechanism: Increment `walk_count` on attempted or completed walks. High count plus recent verification promotes the route; a low/stale count deprioritizes it, like a cache-hit counter.  
Confidence: [likely]

10. Practice: When a step target is superseded, do not rewrite it; add a forward pointer.  
Mechanism: The old step gets `superseded_by` pointing to the new session:line or route. Append-only remains true, and the walker resolves indirection to the current terrain.  
Confidence: [well-known]

11. Practice: Let a route degrade partially, not fail totally.  
Mechanism: A step whose target is missing or superseded is marked `dangling` with its last-known-good address. The surrounding segments remain walkable, and the route reports an uncertain leg instead of aborting.  
Confidence: [likely]

12. Practice: Compose routes through shared anchors.  
Mechanism: Two routes touching the same anchor become a graph. Walkers can switch paths at that node, so routes merge/split at stable landmarks without duplicating territory.  
Confidence: [likely]

13. Practice: Let conflicting routes coexist; rank at walk time, do not delete.  
Mechanism: Multiple routes with the same trigger but different next steps remain as forks. Walk-time ranking by `walk_count`, `last_verified`, and staleness resolves competition without erasing history.  
Confidence: [likely]

14. Practice: Minimal schema as JSON.  
Mechanism: One slice holds the route, steps, edges, and enough metadata to pin and resolve it.  
Confidence: [well-known]

```json
{
  "route_id": "r_<hash>",
  "schema_version": 1,
  "trigger_signature": {
    "event_types": ["..."],
    "payload_match": {"...": "..."}
  },
  "preconditions": [
    {"assert": "...", "receipt": "session:line"}
  ],
  "last_verified_at": "address-or-ISO8601",
  "status": "active|stale|superseded",
  "walk_count": 0,
  "steps": [
    {
      "id": "s1",
      "type": "observation|discriminating-test|decision|dead-end|anchor|handoff",
      "target": "session:line|route_id|artifact",
      "receipt": "session:line",
      "is_not": ["refuted-hypothesis"],
      "outcome": {"if": "...", "next": "s2"},
      "supersedes": null,
      "superseded_by": null,
      "step_status": "current|dangling|superseded"
    }
  ],
  "edges": [
    {"from": "s1", "to": "s2", "label": "true|false|next|handoff", "evidence": "session:line"}
  ]
}
```

The 3 mechanisms most transferable to CONTEXT:

1. Dead-end steps as first-class IS-NOT records with receipts → attach to **THE EYE**, so exclusions become indexable, findable, and freq-countable negative space.  
2. Supersede-by-forward-pointer with dangling markers → attach to the **connectome**, so route steps are typed edges that resolve to the latest target without mutation and preserve provenance.  
3. Trigger signature separated from route body plus walk-count ranking → attach to **recall-at-action**, so “if you have hit this” matches on symptom fingerprint and retrieves the best route by usage and last-verified.
py :   read 5 of 6 branches -- read them -- 5 different questions were never asked the same thing, so there is no 
disagreement here for another call to settle.
At line:1 char:318
+ ... :\AI-Setup; py agent_cli.py ask --get 354da0f0 > "C:\Users\L5\AppData ...
+                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (  read 5 of 6 b...call to settle.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 

