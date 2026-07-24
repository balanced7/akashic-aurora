---
akashic_id: art_20260703_task-is-lora-qlora-fine-tuning-of-a-7-30_61253d
akashic_sha: 05eb90400d7b
status: draft
type: design
date: 2026-07-03
title: "TASK: Is LoRA/QLoRA fine-tuning of a 7-30B model feasible on an AMD RX 9070 XT (RDNA4, 16GB) under Windows in mid-2026, and with which stack?"
gist: "# TASK: Is LoRA/QLoRA fine-tuning of a 7-30B model feasible on an AMD RX 9070 XT (RDNA4, 16GB) under Windows in mid-2026, and with which sta"
tenant: solo
visibility: fleet
seats: []
category: [memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T00:10:55"
updated: "2026-07-03T00:10:55"
---
<!-- GENERATED PROJECTION of art_20260703_task-is-lora-qlora-fine-tuning-of-a-7-30_61253d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# TASK: Is LoRA/QLoRA fine-tuning of a 7-30B model feasible on an AMD RX 9070 XT (RDNA4, 16GB) under Windows in mid-2026, and with which stack?

# TASK: Is LoRA/QLoRA fine-tuning of a 7-30B model feasible on an AMD RX 9070 XT (RDNA4, 16GB) under Windows in mid-2026, and with which stack?
feeds: SQ2+SQ5 (critic trainability on local hardware)
seeds:
- https://rocm.docs.amd.com/
- https://github.com/unslothai/unsloth
- https://github.com/axolotl-ai-cloud/axolotl
notes: This decides whether the future critic can TRAIN locally (the independence thesis)
  or needs cloud GPU rental. Chase: RDNA4 ROCm status on Windows vs WSL2 vs Linux dual-boot,
  which trainers support AMD (unsloth/axolotl/llama-factory/torchtune), QLoRA VRAM math for
  7B/14B/30B at 16GB, and realistic tokens/sec training throughput reports. Note our box:
  Windows 11, 61.6GB RAM. Flag anything ZLUDA-shaped (we have prior ZLUDA experience).
  "Done" = a go/no-go per model size + the least-friction stack, with fetched evidence.
