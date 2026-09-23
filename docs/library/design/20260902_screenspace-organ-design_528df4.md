---
akashic_id: art_20260902_screenspace-organ-design_528df4
akashic_sha: 054b79f07b7e
schema_version: 1
status: current
type: design
date: 2026-09-02
title: screenspace-organ-design
gist: "# The Screenspace Organ — unified design (T386, the Aurora Program door-plane) **Status: position — reconciles two independently-converged d"
visibility: fleet
body_type: markdown
seats: []
category: [bus, security, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-02T21:15:51"
updated: "2026-09-02T21:15:51"
---
<!-- GENERATED PROJECTION of art_20260902_screenspace-organ-design_528df4 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# screenspace-organ-design

# The Screenspace Organ — unified design (T386, the Aurora Program door-plane)

**Status: position — reconciles two independently-converged designs; the fleet fences the seams, the operator gates the wake drill.**
Authored by claude (Vandor) 2026-09-02, synthesizing: Sunshine's accepted build charter (bus `1788380536267-0`, blessed by Daniil at `1788380479987-0`: "performant and low latency way for you or any approved agent to see the screen and click into things, scroll, type etc"), Daniil's constraints to Vandor tonight (verbatim: "Performant, low latency, reliable and useful. something that can be context lean and ramp up and down depending on required level of fidelity. this all also needs to be mcp native so it can be done on demand at speed"), the T342 graveyard autopsy, the per-seat capability census, and the tech-landscape brief (all four from workflow wf_d2a7893d-602, this session). Task: T386 (claimed, claude) — S0 census SATISFIED by this document's inputs; G1 receipt below.

## 0. What the census proved (G1 receipt)

- **The house owns zero screen doors.** Sight exists only inside the interactive Vandor harness (browser-pane a11y/read_page/computer). Every runner seat sees through ToolBox (~44 verbs, no screen), Rill additionally has NO turns at all. The last screen organs died undocumented in the t342 graveyard.
- **The substrate is still paid for**: pyautogui, mss, cv2, PIL, pytesseract, paddleocr, uiautomation, win32, comtypes all installed; Tesseract 5.4 at Program Files; **Naturo installed and executable** (see/find/get/set/type/press/wait/diff/capture + window focus + dialogs + an MCP server) despite zero repo references. Only Florence-2 weights and easyocr/pywinauto are absent — neither needed.
- **Working designs survive as parts**: desktop_automation's FAILSAFE hands, screen_ocr's WinRT zero-dep trick, agentic_automation's see→ground→click facade, ui_scout's API shape, the qwen2.5vl-via-Ollama OCR recipe with timings. The GPU lesson is pre-paid: no local torch inference — RDNA4 has no ROCm; vision sidecars are Ollama-VLM or remote.

## 1. Architecture (the two designs, fused)

**One persistent per-user engine process** (not Session-0; DPI-aware-v2 declared before any UIA/window call) owning:
1. **The shadow model** — UIA event subscriptions (FocusChanged, scoped StructureChanged, PropertyChanged, EVENT_SYSTEM_FOREGROUND via WinEventHook) + DXGI dirty-rect stream (dxcam) feed an in-memory model of: foreground window, focus path, window roster, recent deltas, activity level. Most calls answer from this cache in <1ms server-side. **This is what makes context-lean + on-demand-at-speed real: the walk already happened.** (Handler thread discipline per UIA docs: one dedicated thread, never re-enter UIA from a handler.)
2. **Scoped cached walks** — UIA CacheRequest batches (never per-property COM calls, never pywinauto's lazy wrapper), depth-capped, ControlView-filtered, scoped to a named window/pane. 10–100ms typical.
3. **Capture** — dxcam (DXGI duplication: ~4ms/frame, frame-only-on-change, dirty rects free) for ambient; mss for one-shot; WGC (windows-capture) if per-window-occluded capture proves needed. All D3D11, AMD-clean.
4. **Text** — UIA text properties first (free, exact); pixels-only regions: oneocr (Snipping Tool engine, boxes+confidences) primary → winrt Windows.Media.Ocr fallback (tile at MaxImageDimension) → RapidOCR court of appeal. Tesseract retired to nothing (wrong tool for screens; keep installed, unused).
5. **Action, two rails** — Rail 1 default: UIA patterns (Invoke/Value/Toggle/Scroll/ExpandCollapse; no foreground needed, no keystroke races, works occluded). Rail 2: SendInput for hover/drag/wheel and pattern-less custom UIs. Every act reports which rail + verified post-state, never bare "sent".
6. **Vision sidecar (off hot path, per both designs)** — qwen2.5vl via Ollama / OmniParser, invoked ONLY on explicit ambiguity, never to aim a first click. Zero model tokens and no resident VLM while idle (Sunshine's bar, adopted).
7. **Policy + receipts** — capability enforcement per calling seat, action journal, ephemeral aggressively-cropped screenshots.

**Thin adapters, one engine**: MCP server (stdio, the primary door per Daniil's MCP-native constraint) + CLI verb + ToolBox entries — all three call the same engine + policy layer, per door-parity law and Sunshine's "there will not be three subtly different implementations."

## 2. The fidelity ladder (the ramp Daniil asked for)

| Level | Content | Source | ~Tokens | Latency |
|---|---|---|---|---|
| L0 pulse | foreground/focus/roster-delta/elevated?/activity | shadow model | 30–80 | <1ms |
| L1 digest | interactive elements of scope: `role name state [ref]`, quantized geometry, gen id | cached walk | 150–500 | 10–100ms |
| L2 deep read | full subtree w/ text+values, or OCR lines+boxes | walk / oneocr | 400–1.5k | 50–300ms |
| L3 delta | since gen N: appeared/vanished/changed refs, focus trail, dirty-rects | event log | 50–300 | <5ms |
| L4 pixels-region | ref-bounds crop, downscaled to budget | dxcam+resize | 100–600 | 5–40ms |
| L5 pixels-screen | ≤1568 long edge; optional set-of-marks ref overlay | capture+resize | ~1560 | 10–50ms |

Workhorse loop = L1 once, L3 repeatedly (Playwright-MCP precedent: snapshot+refs beats pixels 10–100x). Image token math is patch-based (⌈w/28⌉×⌈h/28⌉; 1568/2576 tiers) — the server downscales to explicit budgets and pre-resizes anything returned as a tool_result (oversized images are REJECTED by the API, not shrunk). Every response carries `window/focus/gen/stale_ms/elevated` so the caller can decide whether to climb.

## 3. The verb surface (MCP-native, few and orthogonal)

`peek(level, scope?, budget?)` · `delta(since_gen)` · `find(query)→refs` · `locate(ref)→target_token` · `act(target_token, verb, value?)` · `input(keys|pointer)` (escape hatch, gated) · `read_text(scope, method=uia|ocr)` · `watch(scope, until, timeout)` (server-side long-poll → one L3 delta instead of N polls; portable substitute for MCP subscriptions).

**Two-phase act is Sunshine's safety mechanism, adopted whole**: `locate` binds a short-lived token to window handle + process identity + bounds + DPI + gen + screenshot hash; `act(token)` refuses if anything changed. Composes with refs: see-side currency is refs+gen, act-side currency is tokens. Capability tiers separate: `screen.observe / focus / type / act / launch / privileged` — a seat can hold observe+type without launch or destructive click. Operator overrides are explicit and receipted.

## 4. Safety rails (S5, designed first)

1. **Screen text is DATA, never instruction** (R2 law): all read text returns in structured fields with provenance (`source:"screen", window:"chrome.exe"`); `act` binds only to agent-chosen refs — screen content cannot name its own targets. A RED pin proves instruction-shaped screen text does not steer (G4).
2. **UIPI honesty**: detect target integrity level; surface `elevated:true, act:unavailable` at L0/L1 — never silent discard (Windows drops injected input to elevated windows without error). Elevated control, if ever needed, is a deliberate signed decision, never a fallback.
3. **DPI**: PER_MONITOR_AWARE_V2 at engine start; physical pixels end-to-end; downscale returns scale factor; server maps model coordinates back.
4. **IsPassword redaction** from L1/L2/OCR. Screenshots ephemeral, cropped, redacted.
5. Refusal conditions (Sunshine's list, adopted): wrong window, stale target, focus theft mid-action, modal dialog, locked workstation, unapproved seat.

## 5. Latency bars (pre-registered, both seats' numbers)

Warm path p95: targeted capture <100ms · tree/find <200ms · validated input dispatch <100ms · observe→locate→act <350ms (no OCR) · L0/L3 from shadow model <5ms server-side · zero model tokens idle · no full-screen image retained by default. Bench harness is build-step 2, not an afterthought.

## 6. Build order (merged; RED first per M3)

0. **The Sunshine unlock** (his blocker, his spec at `1788380940130-0`): operator-gated `--allow-write --allow-gui` profile for the Codex wake adapter (`agent/harness/codex_bifrost_wake.py:614`, `scripts/codex_bifrost_wake.py:76`, `scripts/install_sunshine_discord_tasks.ps1:44`), read-only stays default, only authenticated daniil may request privileged profile, RED tests first, isolated worktree, no live-task restart without operator diff approval. **Vandor builds this — the mechanic with hands.**
1. RED contracts: refusal matrix (wrong window/stale/focus-theft/DPI/dialog/locked/unapproved) + G4 injection pin + G3 act-verify pin.
2. Observe-only engine: shadow model + cached walks + targeted capture + stable refs + DPI normalization + latency bench.
3. Dry actions: highlight, focus, set-text, read-back — no submit.
4. **The Vandor vertical slice** (attended): nonce into the live Claude Desktop conversation via UIA ValuePattern, exact readback, operator visual confirm, submit ONCE, prove causal reply + continuity. Naturo may drive this slice if its live probe benchmarks well — fastest path to the motivating receipt; the engine core remains raw UIA+CacheRequest either way (fence question F1).
5. General verbs + compound `desktop_prompt`.
6. Vision fallback benchmarks (cropped oneocr first; qwen-VL/OmniParser only on UIA-insoluble cases).
7. Fleet doors: MCP + CLI + ToolBox with ACL enforcement; Rill's turn problem gets its actuator (the Rill receipt closes: an unreachable-but-live seat handed a turn through the door — G5).
8. Kill drills: monitor move, scaling change, focus theft, dialog, lock, driver crash, duplicate-agent race.

## 7. Fence questions (narrow — the designs already agree on the rest)

F1. **Naturo vs raw uiautomation as the engine's structure core** — Naturo is installed w/ MCP server but has zero repo references and unknown provenance/maintenance; raw UIA+CacheRequest is fully understood but is new code. Benchmark both in step 2; the fence should attack: is depending on an unversioned external binary acceptable for a load-bearing organ?
F2. Shadow model in v1 or v2? (My brief: v1 — it IS the low-latency claim. Sunshine's charter implies polling-per-call v1. Cost: event-thread discipline complexity.)
F3. Verb surface: the 8 verbs above vs Sunshine's capability-named verbs — compose or collapse?
F4. `watch` long-poll semantics vs the bus's existing expectation machinery — one blocking door call from a runner seat blocks that runner's loop; is watch harness-only?
F5. Adapter rollout order: MCP first (Daniil's constraint) then ToolBox, or simultaneous?

## 8. Receipts & retirement

Every slice lands with: bench numbers vs §5 bars, kill-drill receipts, and the action journal. This design retires into `docs/` proper when the Vandor vertical slice (step 4) has its causal-reply receipt — the organ's birth certificate is the wake that motivated it.
