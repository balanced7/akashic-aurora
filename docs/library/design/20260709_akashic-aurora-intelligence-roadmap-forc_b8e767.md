---
akashic_id: art_20260709_akashic-aurora-intelligence-roadmap-forc_b8e767
akashic_sha: 4e507ec8b638
status: fossil
type: design
date: 2026-07-09
title: Akashic Aurora — Intelligence Roadmap (force-multiplier synthesis)
gist: "**Date:** 2026-06-29 **Method:** 6-agent research workflow (knowledge-curation / faithfulness / ACI / substrate SOTA) → synthesis → adversar"
tenant: solo
visibility: fleet
seats: []
category: [substrate, recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260628_akashic-aurora-architecture-documentatio_a9b61f
    rel: cites
  - target: art_20260709_faithfulness-critic-sota-synthesis-desig_eae48d
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:05"
---
<!-- GENERATED PROJECTION of art_20260709_akashic-aurora-intelligence-roadmap-forc_b8e767 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Akashic Aurora — Intelligence Roadmap (force-multiplier synthesis)

**Date:** 2026-06-29
**Method:** 6-agent research workflow (knowledge-curation / faithfulness / ACI / substrate SOTA) →
synthesis → adversarial critic. Grounded in `docs/architecture-review-2026-06-28.md` + 2024–26 agent-memory SOTA.

## Thesis
The architecture is correct; its flagship guarantees are **inert in deployment**: the Codex never
self-organizes (curator unbuilt), "everything consumes embeddings" is false on the hot path (keyword-only
Ranker), and self-curation is **untrustworthy** (the faithfulness metric is computed then discarded). To be a
force-multiplier on local hardware, close the loop: **immutable atoms → faithfully-grounded, self-organizing
projections → semantically-ranked, time-travelable recall**, every link provably grounded. A small local model
has the least slack for unranked noise or fabricated memory, so **trust and density buy more here**.

## The intelligence spine (compounding order — corrected by the critic)
1. **P0 — `AKASHIC_AGENT_ID` fail-closed.** ✅ DONE (cc96d88). Substrate integrity before belief.
2. **SPINE-1 — unify the curation spine.** ✅ DONE (2dd8d55). One `consolidate_into_chronicle` path; no
   clobber. *Must precede FAITH-1* (can't gate faithfulness against a clobbered file).
3. **FAITH-1 — faithfulness critic in the seam.** ✅ DONE. `core/primitives/faithfulness.py`: a
   deterministic, no-LLM critic injected at the Consolidator seam (one seam → chronicle + lessons +
   future Resources). HARD-gates pointer-resolution + number/identifier consistency + traceability;
   grounding overlap is SOFT (reported, paraphrase-safe). No-op on today's extractive writer
   (characterized: conf=1.0, zero false-positives) and the forward gate for an LLM writer — shadow
   posture. SOTA synthesis + citations in `docs/faithfulness-research.md`. Suite 438.
4. **FC-01 — the Codex curator.** `core/codex/curate.py`: cluster atoms (Clusterer) → centroid-match to
   persisted cluster-links → regenerate/mint/supersede Resources, **gated by the now-validated FAITH critic**.
   The keystone that makes the Aurora thesis run. (Prior art: A-MEM, Zep/Graphiti, Generative-Agents reflection.)
5. **PROV-1 / V6 / ASOF — provenance-enforced regen, self-organizing themes, time-travel.** *Critic: V6 and
   ASOF are someday, not near-term* — ASOF returns "everything always" until the curator stamps real `valid_to`;
   V6 (BERTopic on a small local corpus) is unstable. Sequence after FC-01 has run long enough to accumulate supersessions.

## ACI force-multipliers (the door IS the product)
**ACI-ERR** errors-that-teach (FM5, S) · **ACI-REG** one-truth verb registry + **ACI-PARITY** CLI↔MCP contract
test (FM4, S) · **ACI-CAP** `capabilities()` self-describing door · **ACI-BLOCK** resolve-blocker verb (resolved
blockers stay ACTIVE in boot today) · **ACI-LOCKS** MCP lock tools · **ACI-WATCH** read-only TUI · **CTX** boot
as a contract (resolve stale blockers + faithfulness banner + semantic top-k). These make any agent more capable.

## Substrate/trust must-haves (protect the multiplier)
**OPS-03** crash-safe FileStore + corruption recovery (FM5) — *critic: pair with a snapshot-restore door so a
refusal doesn't brick the agent* · **RC-02** route contended writes through `update_atomic` · **RC-03** cross-process
file CAS · **OPS-02** backup validate-before-delete + round-trip test · **SEC-02** Redis auth (stage password then
flip) · **SEC-01** bus trust (overlaps Bifrost Mesh W5) · **ARCH-03/04/06** guardrail coverage + SSOT.

## Honest caveats (critic)
- **FC-09 (embeddings on the hot path) is hardware-gated** — value needs a resident embedder daemon; a cold CLI
  invocation either eats load latency or the flag no-ops. Demote until a long-lived process holds the embedder.
- The "local-hardware" framing is partly rhetorical: most FM-5 items are **trust + plumbing**, not density. The
  one genuinely local-specific lever (semantic density, FC-09) is the hardware-gated one.

## Status
✅ Applied: P0, ARCH-02 (dead comm stack), DOC-01/02 (root docs + freshness allowlist), RC-05 (handoff kind),
SPINE-1, FAITH-1. **Next executable: FC-01 (Codex curator, gated by the FAITH critic).** Suite 438 green throughout.
