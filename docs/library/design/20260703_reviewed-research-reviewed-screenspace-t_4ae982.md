---
akashic_id: art_20260703_reviewed-research-reviewed-screenspace-t_4ae982
akashic_sha: 464e32599639
status: draft
type: design
date: 2026-07-03
title: "reviewed: research/reviewed/screenspace-tool-stack.md (2026-07-03) -- accepted as-is, strongest draft of the shift"
gist: "# reviewed: research/reviewed/screenspace-tool-stack.md (2026-07-03) -- accepted as-is, strongest draft of the shift # TASK: What is the pro"
tenant: solo
visibility: fleet
seats: []
category: [tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_what-is-the-proven-open-source-stack-for_ce5d49
    rel: cites
created: "2026-07-03T23:10:55"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260703_reviewed-research-reviewed-screenspace-t_4ae982 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# reviewed: research/reviewed/screenspace-tool-stack.md (2026-07-03) -- accepted as-is, strongest draft of the shift

# reviewed: research/reviewed/screenspace-tool-stack.md (2026-07-03) -- accepted as-is, strongest draft of the shift
# TASK: What is the proven open-source stack for Windows screenspace tools (see screen, read it, act on it) callable from a Python agent?
feeds: A-series (assistant layer -- screenspace capability; user end-goal revealed 2026-07-03)
seeds:
- https://github.com/RapidAI/RapidOCR
- https://github.com/yinkaisheng/Python-UIAutomation-for-Windows
- https://playwright.dev/python/
notes: Target: an assistant that can capture the screen, OCR/understand it, and act
  (click/type) on native Windows apps + browsers, as TOOLS an agent calls. Chase:
  (1) RapidOCR vs alternatives (Tesseract, EasyOCR, PaddleOCR) -- speed/accuracy on
  screenshots, ONNX/CPU friendliness; (2) UIA automation from Python: uiautomation vs
  pywinauto -- reliability field reports, which handles modern apps (WinUI3/Electron);
  (3) screen capture: mss vs dxcam latency; (4) how existing agent tools structure this
  (screenshot->accessibility-tree->action loops); (5) safety patterns: confirm-before-
  destructive-click, app allowlists (our enforce-at-the-door ethos applies to OS actions
  MORE, not less). "Done" = a v0 tool-set spec (capture/read/click/type) with the chosen
  libraries and their gotchas.
