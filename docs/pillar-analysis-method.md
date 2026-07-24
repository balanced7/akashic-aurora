# The Pillar Analysis Method — how to take a subsystem to its next level

Status: current  (2026-07-09, P4: Standing method; stable altitude)

**Origin:** distilled 2026-07-08 from the recall vNext arc (docs/library/design/20260701_recall-vnext-closing-the-four-loops-2026_b93539.md), which
followed it end-to-end; the membrane/Renew and bookends arcs used the same shape. Written at
stable altitude (process, not code specifics) so it doesn't rot. Apply it to any pillar:
coordination, narrative spine, trust, the doors, the UI.

## Phase 1 — Triangulate ground truth (never analyze from one source)

1. **Read the design** (docs + notes): what the pillar is SUPPOSED to be. Note its own stated
   principles — they are the standards you'll hold it to.
2. **Read the code**: what it actually IS. "We built X" claims are half-true by default
   (mediation_membrane_is_the_hook_layer; built≠wired). Verify wiring, not existence.
3. **Pull the system's own telemetry about itself.** Akashic instruments itself — funnel counters,
   injection/event ledgers, task history, session signals. The numbers usually contain the
   diagnosis already (recall: 2,850 impressions → 26 helped; triage had named the waste for weeks).
4. **Add lived experience.** Use the feature while doing real work first; log your own hits,
   misses, and frictions. When your felt experience and the telemetry agree, trust the diagnosis
   (the funnel's one `protect` lesson was also the one that had genuinely helped at boot).

## Phase 2 — Diagnose at LOOP altitude, not feature altitude

5. **Map the value chain end-to-end** (e.g. capture → store → match → surface → influence →
   credit → curate → back to match). Name every link.
6. **For each link ask: does the signal flow BACK?** The standard failure in a system that builds
   ahead is not missing machinery — it is a **designed-open loop**: measurement without actuation
   (triage nobody acts on), a credit valve too narrow to distinguish value from noise, a report
   that never becomes state.
7. **Say the thesis in one sentence** before building ("the pipes are excellent; the water isn't
   flowing back"). If you can't, you haven't diagnosed yet — you're still describing.

## Phase 3 — Fix with evidence discipline

8. **Fix the corpus/root, not the reader/symptom** (multiagent_context_credit_not_tags). Prefer
   closing a loop over adding a part.
9. **Earn every threshold by replay**: labeled history vs the live population — never by feel.
   Record the calibration IN the design doc, with its honest bounds (n=1 is a bound, not a shame).
10. **Probe-driven iteration with BOTH probe classes**: adversarial cases (must be silent/refuse)
    AND golden cases (must fire/rank first). When a probe fails, root-cause the mechanism —
    never tune until green. Expect probes to find real bugs in your fix (scale-invariance,
    a dampener biting the legit lone-rare-hit case, boundary marks polluting the next span).
    A probe failure may also mean the TEST is wrong — decide from first principles, then pin it.
11. **Layered defenses, one named justification per layer.** A layer you can't justify in one
    sentence is tuning, not design.
12. **Deterministic + reversible everywhere**: flags not deletes (bench/unbench), state not
    history mutation, kill switches and env tunables on every new behavior.
13. **Live-prove on real state** in the same session (the feature acting on the system that built
    it is the strongest smoke test), ship through the gates, record the lesson WITH a 'Use when'
    trigger clause, and write the honest-bounds + deferred list into the design doc.

## The tells that a pillar is ready for this treatment
- Its telemetry names waste nobody has acted on; growth without decay (corpus/backlog only grows).
- Its feedback channel exists but sits unused (votes at 4/0 forever = friction at the wrong moment
  — move the ask to the natural reflective boundary, don't exhort).
- Its docs claim more than its wiring delivers.
- You feel friction using it but the metric says "fine" (or vice versa) — the aperture is wrong.

*Worked example with all numbers: docs/library/design/20260701_recall-vnext-closing-the-four-loops-2026_b93539.md. Companion discipline:
investigate-before-delete, blind-crosscheck fencing, evidence-gate-every-slice (see LESSONS).*
