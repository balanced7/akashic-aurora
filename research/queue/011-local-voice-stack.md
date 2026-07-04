status: queued
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
