---
akashic_id: art_20260703_infra-note-2026-07-03-evening-review-tim_bf46a9
akashic_sha: bdb3f8ad1cce
status: draft
type: design
date: 2026-07-03
title: "infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes"
gist: "# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes # stdout+stderr for the full 35m) -- the head"
tenant: solo
visibility: fleet
seats: []
category: [memory, voice]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T23:11:32"
updated: "2026-07-03T23:11:32"
---
<!-- GENERATED PROJECTION of art_20260703_infra-note-2026-07-03-evening-review-tim_bf46a9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes

# infra-note (2026-07-03 evening review): TIMEOUT with a completely EMPTY session log (0 bytes
#   stdout+stderr for the full 35m) -- the headless process produced no output at all, an infra
#   hang not a content problem. See runlog-2026-07-03.md; 6 of 12 shift tasks hit this pattern.
#   Requeued as-is. Next shift: OLLAMA_KEEP_ALIVE set longer before relaunch (see where-we-are).
# TASK: What is the best local voice I/O stack (STT + TTS) for a Windows assistant on our hardware, and what latency is realistic?
feeds: A-series (assistant layer -- voice loop feasibility; user end-goal revealed 2026-07-03)
seeds:
- https://github.com/SYSTRAN/faster-whisper
- https://github.com/thewh1teagle/kokoro-onnx
notes: Target: talk to the assistant, hear it answer, on RX 9070 XT (16GB, Vulkan -- NOTE
  faster-whisper wants CTranslate2/CUDA; check CPU int8 performance and any AMD paths) +
  61GB RAM, Windows 11. Chase: (1) faster-whisper model-size vs latency vs accuracy on
  CPU int8 (small/base/distil variants) -- real numbers from users; (2) Kokoro ONNX TTS:
  quality reports, latency, Windows setup friction; (3) alternatives worth one line each
  (whisper.cpp Vulkan?, Piper TTS, Windows native speech); (4) wake-word/hotkey options
  (openwakeword? plain global hotkey is fine for v0). "Done" = a recommended v0 stack
  with expected end-to-end voice-turn latency and the install steps.
