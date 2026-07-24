---
akashic_id: art_20260703_infra-note-2026-07-03-evening-review-tim_612f40
akashic_sha: 9ea263595b8a
status: draft
type: design
date: 2026-07-03
title: "infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes"
gist: "# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes # stdout+stderr for the full 35m) -- the head"
tenant: solo
visibility: fleet
seats: []
category: [memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T23:11:31"
updated: "2026-07-03T23:11:31"
---
<!-- GENERATED PROJECTION of art_20260703_infra-note-2026-07-03-evening-review-tim_612f40 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes
#   stdout+stderr for the full 35m) -- the headless process produced no output at all, an infra
#   hang not a content problem. See runlog-2026-07-03.md; 6 of 12 shift tasks hit this pattern.
#   Requeued as-is. Next shift: OLLAMA_KEEP_ALIVE set longer before relaunch (see where-we-are).
# TASK: Can MoE expert-placement tuning (experts in RAM, attention on GPU) speed up 19-21GB MoE models on a 16GB-VRAM / 64GB-RAM box, and does Ollama expose it?
feeds: SQ5 (fleet throughput -- the CPU/GPU split is the current bottleneck for the 30B-MoE class)
seeds:
- https://github.com/ggml-org/llama.cpp/discussions
- https://docs.ollama.com/
notes: Context: glm-4.7-flash runs 25pct/75pct CPU/GPU on this box (21GB vs 16GB VRAM)
  and times out on heavy tasks; gpt-oss:20b fits VRAM fully. MoE models activate ~3B
  params/token -- naive layer-split wastes the pattern. Chase: (1) llama.cpp
  --override-tensor / n-cpu-moe expert-pinning flags -- current syntax + measured
  speedups others report for 30B-A3B-class models; (2) whether Ollama exposes any
  equivalent (Modelfile num_gpu? env? open feature requests); (3) practical fallback:
  running llama.cpp server directly with an Anthropic-compatible proxy, effort vs gain;
  (4) reported tok/s before/after on comparable hardware (16GB cards + DDR5). Search
  first; fetch what you cite. "Done" = a try-this-next list with expected gains and the
  config lines, or an honest "not exposed in Ollama, llama.cpp-direct is the only path".
