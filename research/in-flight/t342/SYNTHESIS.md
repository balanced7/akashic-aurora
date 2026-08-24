# T342 slice 1 — the graveyard, measured and read (2026-08-18 night)

Probe @93c110e1, evidence sweeps by three blind Explore subagents (verbatim in evidence-A/B/C.md),
synthesis by claude (Vandor). Method: git log --diff-filter=D → dead-at-HEAD intersect → last-seen
source extracted → per-module CAPABILITY-from-source + LIVE-equivalent hunt with file:symbol cites.

## The numbers (counted, not estimated)

- **1053** paths ever deleted; **1048 dead at HEAD** (deleted and never restored)
- **216 dead python modules**, all 216 sources extracted, 0 failures
- Verdicts across 216: **141 LIVE:YES** (equivalent exists, cited) · **74 LIVE:NO** (searched,
  nothing equivalent) · 1 N/A (empty file)
- Handoff's prior measurement (951 paths / 133 modules) was at an earlier HEAD with an unstated
  filter; tonight's numbers carry their method in the file and supersede it.

## The headline: 74 capabilities have NO live equivalent. They cluster into SEVEN planes, not 74 accidents.

1. **THE VISION PLANE (largest, ~20 modules).** Florence-2 screen understanding, OCR (Paddle/
   EasyOCR/Tesseract/Windows.Media), desktop + per-window capture, screenshot-with-reason logging,
   template-match clicking, video keyframes, VLM-OCR via qwen2.5vl. The live tree can see a
   BROWSER (Playwright) and nothing else. The operator's machine was once observable; today it is not.
2. **DESKTOP AUTOMATION (~6).** pyautogui/pygetwindow/naturo UI-tree click-type-drag — the hands
   that went with the eyes. Gone with them.
3. **SELF-HEALING INFRASTRUCTURE (~8).** keepalive_ollama (probe→restart→portproxy), stack_manager
   DAG-tiered launch with auto-restart + resource/memory monitors, launch_dashboard full bring-up,
   redis_ha_manager (Sentinel failover), deploy rollback + FaultInjector. Live equivalent: launcher
   for AGENT processes only; infra is hand-started and never self-heals. (Boot's own "deepseek:
   runner DOWN — restart the daemon" tonight is this absence speaking.)
4. **GOVERNANCE (1, heavy).** harness_enforcer: 10 named escape conditions (skip-verify,
   skip-logging, impatient-exit...), action journal, compliance report. Live policy is two vetoes
   (git_veto/lock_veto). The house's METHOD laws (M3 pre-registration...) are enforced today by
   discipline and scorecards, not by the harness — the scorecard's own M3 drift (11/16) is this gap.
5. **CACHING/ASSETS (~7).** fast_cache (RAM-disk + exec_fast), bifrost semantic prompt cache,
   context RAM cache, universal download cache + update checker, hardened web fetcher. fast_cache
   was deliberately killed with a receipt (chronicle 20260717, git:7bf9e467) — the ONE documented
   death among 74.
6. **COORDINATION PROTOCOLS (~5).** Blackboard propose/verdict state machine, generator/analyst
   pair protocol, help-request flow, declare/complete_operation manifests, service-endpoint
   discovery registry. Bus+locks survived; the PROTOCOLS over them did not.
7. **VOICE STACK (~10, known-legacy).** gemma_realtime (VAD, Whisper STT, Kokoro TTS, barge-in).
   The only plane whose death was an operator decision already recorded ([[project_ai_setup_stack]]).

Plus singles worth a line: the A-learns-to-B-benefits transfer test (the fleet's whole premise,
untested live), doc-self-sufficiency-in-N-lines gate, Windows toast notification wake.

## What the 141 LIVE:YES lines are worth

They are the strangler-fig receipts: session_logger→BeatLog, catchup→boot, escalation→ask,
operational_alerts→locks+pager, coordinator_service→read-time loaders. The re-derivations are
real and mostly BETTER (hash embeddings→real embeddings; delete-raw-after-summarize→lossless
pointers). T342's founding claim survives contact with evidence in the sharper form: **the house
re-derives well; what it lacks is the record that a thing existed** — 7 FOSSILS entries vs 74
undocumented capability deaths (10.6x, tighter than the handoff's 2-orders guess but the same wound).

## For the verb (the row's WHAT SHIPS, not built tonight — agent_cli.py held by T341)

The probe IS the verb's engine: deleted-paths ∩ live-tree, last-seen sha+date, WAS-LOST verdicts,
CANNOT-ESTABLISH honesty. This file + evidence-*.md are its first output, hand-run. Wiring it as
`agent_cli.py graveyard` is a one-sitting slice once the file claim frees.

## NOT judged here (per row scope)

Whether any death was a mistake. Many were correct (voice by decision, fast_cache with receipt,
scaffolding by obsolescence). The seven planes above are candidates for Daniil's eye, not a
resurrection list.
