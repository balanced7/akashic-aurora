status: queued
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
