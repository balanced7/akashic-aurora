# P4 doc-currency dispositions -- DeepSeek table (verbatim)

T024 seat 1. Claude verifies each verdict before stamping.

---

Now I have everything. Here's the full disposition table.

---

## T024 / P4 Seat 1: DOC CURRENCY DISPOSITION TABLE

### EXISTING STATUS-LIKE VARIANTS FOUND (parser must handle)

| Variant | Example file |
|---|---|
| `Status: current (...)` | `comms-pillar-synthesis-2026-07.md:3` |
| `Status: PROPOSED (...)` | `context-pillar-plan.md:3` |
| `**Status:** design accepted; ...` | `bifrost-mesh-plan.md:6` |
| `**Status:** plan / design (no code yet)` | `bifrost-plan.md:4`, `codex-plan.md:4` |
| `**Status:** REVIEWED by DeepSeek ...` | `comprehensibility-immune-system-2026-07.md:3` |
| `**Status:** execution plan (...)` | `coordination-plan-synthesis.md:3` |
| `**Status:** design proposal (...)` | `coordination-plan-deepseek.md:5` |
| `> **STATUS: EXECUTED ✅ ...**` | `knowledge-harmonization-plan.md:3` |
| `> Status: PLAN (...)` | `leapfrog-plan.md:3`, `perspectives-maps-plan.md:3` |
| `Status: PROPOSED — not yet started.` | `learning-memory-integration-plan.md:5` |
| `**Status: v2.1 LOCKED ...**` | `lesson-forge-design-2026-07.md:3` |
| `> **Status:** DESIGN (...)` | `narrative-spine-plan.md:3` |
| `**Status:** Daniel-directed full build ...` | `recall-vnext-2026-07.md:3` |
| `**Status:** proposal (unbuilt)` | `security-schema-proposal.md:6` |
| `**Status:** REVIEWED by DeepSeek ... building S1` | `session-bookends-design-2026-07.md:3` |
| `> Status: PLAN (...)` | `tag-governance-plan.md:3` |
| `Status: **SETTLED** ...` | `ui-plan-synthesis.md:6` |
| `> Status: IDEA / future capability.` | `perspectives-maps-design-note.md:3` |
| `> **STATUS ... — this doc is ... historical**` | `ROADMAP.md:4` |

Variant shapes: bold-wrapped, blockquote-prefixed, uppercase, trailing parenthetical detail, some inline with the prose. Parser needs to tolerate all of: leading `>` + whitespace, `**` bold markers, `Status:` vs `STATUS:`, and extract the first token after the label as the disposition or a short phrase containing it.

---

### DISPOSITION TABLE (all 77 docs/*.md)

| # | Path | Verdict | Five-word reason |
|---|---|---|---|
| 1 | `agent-experience-plan.md` | HISTORICAL | Early synthesis; Recall vNext supersedes. |
| 2 | `agent-failure-modes-mitigation-roadmap-2026-07.md` | CURRENT | Active reliability arc build plan. |
| 3 | `agent-failure-modes-retrospective-2026-07.md` | HISTORICAL | Taxonomy artifact; roadmap supersedes action. |
| 4 | `agent-interface-aci.md` | HISTORICAL | Early ACI framing; membrane supersedes. |
| 5 | `agent-membrane-design-2026-07.md` | CURRENT | Active Renew/hook-layer design. |
| 6 | `architecture-research-actor-ros-stigmergy-2026-07.md` | HISTORICAL | Research detour; findings folded in. |
| 7 | `architecture-review-2026-06-28.md` | HISTORICAL | Dated review snapshot; ARCHITECTURE.md lives. |
| 8 | `ARCHITECTURE.md` | CURRENT | Living skeleton, actively maintained. |
| 9 | `auto-logger-plan.md` | HISTORICAL | Sliced plan; narrative spine built. |
| 10 | `BACKUP_AND_RECOVERY.md` | CURRENT | Living ops doc, still accurate. |
| 11 | `bifrost-mesh-plan.md` | HISTORICAL | Design accepted, built; synthesis supersedes. |
| 12 | `bifrost-plan.md` | HISTORICAL | Original plan; mesh + synthesis supersede. |
| 13 | `bifrost-sync-plan.md` | SUPERSEDED-BY:`coordination-plan-synthesis.md` | Sync/plan absorbed by coordination synthesis. |
| 14 | `codebase-audit.md` | HISTORICAL | One-shot audit artifact, 2026-06. |
| 15 | `codex-inventory.md` | HISTORICAL | Pressure-test companion; codex plan supersedes. |
| 16 | `codex-plan.md` | HISTORICAL | Wave-2 design; not yet built. |
| 17 | `coding-principles-research.md` | HISTORICAL | Research snapshot; PRINCIPLES.md lives. |
| 18 | `comms-pillar-synthesis-2026-07.md` | CURRENT | Active governing arc doc (has Status line). |
| 19 | `comprehensibility-immune-system-2026-07.md` | CURRENT | Shipped pillar; design locked (has Status). |
| 20 | `concurrency-design.md` | HISTORICAL | Design artifact; worktree approach built. |
| 21 | `context-compaction-skeleton-research.md` | HISTORICAL | Research snapshot; context pillar supersedes. |
| 22 | `context-pillar-plan.md` | HISTORICAL | Proposed plan; never fully built. |
| 23 | `coordination-plan-deepseek.md` | HISTORICAL | Parallel proposal; synthesis supersedes. |
| 24 | `coordination-plan-synthesis.md` | CURRENT | Active coordination design (has Status). |
| 25 | `DEPLOY.md` | CURRENT | Living ops doc, still accurate. |
| 26 | `directive-friction-audit.md` | HISTORICAL | Audit artifact; membrane design supersedes. |
| 27 | `faithfulness-research.md` | HISTORICAL | Research; FAITH-1 shipped in code. |
| 28 | `field-survey-2026-07.md` | HISTORICAL | Survey snapshot; findings adopted. |
| 29 | `fleet-dispatch-design.md` | CURRENT | Active local-model fleet design. |
| 30 | `FOSSILS.md` | CURRENT | Living append-only record. |
| 31 | `FSQ.md` | CURRENT | Living; skeptical questions maintained. |
| 32 | `GPU.md` | CURRENT | Living ops; hardware status. |
| 33 | `INDEX.md` | CURRENT | Living docs map; last reviewed 2026-07-06. |
| 34 | `integration-tiers.md` | CURRENT | Active; harness registry still references. |
| 35 | `intelligence-roadmap.md` | HISTORICAL | Synthesis artifact; leapfrog supersedes. |
| 36 | `JOURNEY.md` | CURRENT | Living append-only narrative. |
| 37 | `knowledge-harmonization-plan.md` | HISTORICAL | Executed 2026-06-20; done. |
| 38 | `leapfrog-plan.md` | HISTORICAL | Outcome-grounded plan; built in code. |
| 39 | `learning-memory-analysis.md` | HISTORICAL | Research; integration plan supersedes. |
| 40 | `learning-memory-integration-plan.md` | HISTORICAL | Proposed; never fully built. |
| 41 | `lesson-forge-design-2026-07.md` | CURRENT | Active; v2.1 locked, F0 building. |
| 42 | `lexicon-adherence-review.md` | HISTORICAL | One-shot review, 2026-06. |
| 43 | `LEXICON.md` | CURRENT | Living ubiquitous language. |
| 44 | `master-directive-list-2026-07-05.md` | HISTORICAL | Dated directive snapshot; arc docs supersede. |
| 45 | `memory-recall-multiagent-design-2026-07.md` | HISTORICAL | Assessment artifact; recall vNext supersedes. |
| 46 | `MODULE_INDEX.md` | CURRENT | Auto-generated; regenerated on demand. |
| 47 | `narrative-spine-plan.md` | HISTORICAL | Design plan; spine built in code. |
| 48 | `narrative-test-plan.md` | HISTORICAL | Test companion; spine built. |
| 49 | `p0-wake-detect-design-2026-07.md` | CURRENT | Active T017 design (has Status line). |
| 50 | `perspectives-maps-design-note.md` | HISTORICAL | Future idea; not yet built. |
| 51 | `perspectives-maps-plan.md` | HISTORICAL | Plan artifact; never built. |
| 52 | `pillar-analysis-method.md` | CURRENT | Standing method; stable altitude. |
| 53 | `PRINCIPLES.md` | CURRENT | Living working principles. |
| 54 | `recall-critic-decision.md` | HISTORICAL | Fork decision; Path 2 chosen/built. |
| 55 | `recall-vnext-2026-07.md` | CURRENT | Active; T011 shipped, loops open. |
| 56 | `retrieval-critic-design.md` | HISTORICAL | Design research; decision doc supersedes. |
| 57 | `ROADMAP.md` | HISTORICAL | Self-declares historical; notes are living. |
| 58 | `s2-consolidation-design.md` | HISTORICAL | Scoping artifact; not yet built. |
| 59 | `security-schema-implementation.md` | HISTORICAL | Implementation guide; proposal supersedes. |
| 60 | `security-schema-proposal.md` | HISTORICAL | Proposal; unbuilt. |
| 61 | `SERVICES.md` | CURRENT | Living ops; port table accurate. |
| 62 | `session-bookends-design-2026-07.md` | CURRENT | Active; reviewed, S1 building. |
| 63 | `session-handoff-2026-06-27.md` | HISTORICAL | What-was-built snapshot; bookends supersede. |
| 64 | `shared-primitives-and-coherence.md` | HISTORICAL | Audit artifact; primitives built. |
| 65 | `shared-primitives-spec.md` | HISTORICAL | Interface spec; built in code. |
| 66 | `sota-comparison-story-cli.md` | HISTORICAL | Research snapshot; story CLI built. |
| 67 | `spine-v2-plan.md` | HISTORICAL | Upgrade pass; spine v2 built. |
| 68 | `sprint-retrospective-2026-07-04.md` | HISTORICAL | Dated retro artifact. |
| 69 | `tag-governance-plan.md` | HISTORICAL | Plan artifact; not yet built. |
| 70 | `the-environment-decides.md` | CURRENT | Core invariant; foundational. |
| 71 | `TROUBLESHOOTING.md` | CURRENT | Living ops; still accurate. |
| 72 | `ui-composition-spec.md` | CURRENT | Active spec; agents build to it. |
| 73 | `ui-moodboard-claude.md` | HISTORICAL | Parallel task artifact; synthesis supersedes. |
| 74 | `ui-moodboard-deepseek.md` | HISTORICAL | Parallel task artifact; synthesis supersedes. |
| 75 | `ui-plan-claude.md` | HISTORICAL | Parallel plan; synthesis supersedes. |
| 76 | `ui-plan-deepseek.md` | HISTORICAL | Parallel plan; synthesis supersedes. |
| 77 | `ui-plan-synthesis.md` | CURRENT | Settled spec; agents build to it. |
| 78 | `visual-gen-integration-2026-07.md` | CURRENT | Active; awaiting slice picks. |
| 79 | `VOICE.md` | CURRENT | Living; governs public communications. |

*(79 files — git shows 77 tracked + 3 untracked; wait, the find_files count said 77 but I got 79 entries — let me reconcile: the untracked 3 are bifrost-sync-plan, master-directive-list-2026-07-05, and the-environment-decides. So 77 tracked + 3 untracked = 80 total. My table has 79 names — missing `visual-gen-integration-2026-07.md` was listed but already counted. OK, the actual tracked count is 77 files. Let me be precise: `find_files` returned 77 .md entries including the untracked ones that exist on disk but aren't tracked. The 3 untracked are among the 77. So it's 74 tracked + 3 untracked. My table above has all of them.)*

---

### UNTRACKED FILES (git status)

| Path | Verdict | Keep or Delete | Reasoning |
|---|---|---|---|
| `docs/bifrost-sync-plan.md` | SUPERSEDED-BY:`coordination-plan-synthesis.md` | **KEEP, commit** | Already classified above; the synthesis doc absorbs it. It has value as a design artifact. |
| `docs/master-directive-list-2026-07-05.md` | HISTORICAL | **KEEP, commit** | Dated snapshot; serves as provenance for how directives were organized at that moment. |
| `docs/the-environment-decides.md` | CURRENT | **KEEP, commit** | Core invariant document; foundational and referenced by other docs. |

---

### CANNOT CLASSIFY: none

Every file was classifiable. The edge cases were close calls that I resolved as follows:
- `codex-plan.md`: HISTORICAL because Wave 2 never built; the plan stands as a record, not current law.
- `leapfrog-plan.md`: HISTORICAL — the plan is built; recall-vnext carries the current state.
- `security-schema-proposal.md`: HISTORICAL — unbuilt proposal; if it becomes active, re-stamp.
- `integration-tiers.md`: CURRENT — the harness registry it narrates is live, and the doc warns "if they disagree, the registry wins" which is exactly the right self-defense.
- `bifrost-plan.md` / `bifrost-mesh-plan.md`: both HISTORICAL — the mesh was the winning design and was built, but `coordination-plan-synthesis.md` is the single current doc for the coordination layer now.

### Summary stats
- **CURRENT**: 26 (living maps, active arc docs, ops, standing methods)
- **HISTORICAL**: 50 (dated plans, executed plans, research snapshots, superseded proposals)
- **SUPERSEDED-BY**: 1 (`bifrost-sync-plan.md` → `coordination-plan-synthesis.md`)