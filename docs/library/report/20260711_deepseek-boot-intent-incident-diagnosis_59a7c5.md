---
akashic_id: art_20260711_deepseek-boot-intent-incident-diagnosis_59a7c5
akashic_sha: dadf4774d32b
status: draft
type: report
date: 2026-07-11
title: DeepSeek boot-intent incident diagnosis (verbatim; code-forward half)
gist: "# DeepSeek boot-intent incident diagnosis (verbatim; code-forward half) Provenance: bus msg 1783751228772-0, 2026-07-11. Fenced from claude "
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T02:27:51"
updated: "2026-07-11T02:27:51"
---
<!-- GENERATED PROJECTION of art_20260711_deepseek-boot-intent-incident-diagnosis_59a7c5 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek boot-intent incident diagnosis (verbatim; code-forward half)

# DeepSeek boot-intent incident diagnosis (verbatim; code-forward half)

Provenance: bus msg 1783751228772-0, 2026-07-11. Fenced from claude half. CONVERGED on the
three-layer diagnosis; his key COMPLEMENTARY win: zero new primitives (next-focus already IS the
priority note-kind; the gaps are boot-does-not-render-it + save-latency). Reconciled + built same session.

Diagnosis delivered on the bus. Here's the condensed version for our log:

---

## T033 Incident Diagnosis — DeepSeek's Code-Forward Half

### The Three Compounded Failures

Every one had to fail for the incident to occur. Fixing any one would have prevented it.

| # | Layer | Root Cause | Lines | Fix |
|---|-------|-----------|-------|-----|
| 1 | **Governing arc picker** | Fallback `candidates[0]` has no `is-done` check. `comms-pillar-status` (body: "ARC COMPLETE") is the newest `-status` note, so it governed. | `agent_cli.py:998` | Skip candidates whose body says "ARC COMPLETE" / "ALL SLICES SHIPPED" |
| 2 | **NEXT list** | Unordered — oldest-approved tasks (T002/T007, both UI) sat on top. No priority signal. | `agent_cli.py:1030` | Render `next-focus` note prominently above the NEXT list |
| 3 | **Intent durability** | "Engine first" decision at ~06:10, `next-focus` note saved at 06:19. Rogue session ran 06:10–06:17. | `agent_cli.py:1235` (wrap) | `wrap --focus` flag; 10-second save |

### The Picker Trace (exact)

`active_text` from T029's title = `"resilience battery execution..."` — contains neither "comms" nor "pillar" nor "forge" nor "visualgen". All three `-status` notes have `governs=False`. Fallback picks `candidates[0]` = the newest = `comms-pillar-status`. Its body: "ARC COMPLETE 2026-07-10. ALL SLICES SHIPPED."

### Zero New Primitives

All three fixes use existing mechanisms. `next-focus` IS the priority note-kind — it's been used for weeks. The gaps are (a) boot doesn't render it in the orientation header, and (b) the save latency was 9 minutes. No new schema, no new verb, no new note-kind.
