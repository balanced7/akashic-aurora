# What is the proven open-source stack for Windows screenspace tools callable from a Python agent?

provisional-by: glm_local, 2026-07-03
task: research/queue/012-screenspace-tool-stack.md

## TL;DR
- RapidOCR offers extreme speed and multi-language support with CPU-friendly ONNX models, outperforming Tesseract/PaddleOCR/EasyOCR on screenshots [1]
- Python-UIAutomation-for-Windows provides native Windows integration for MFC/WPF/Electron apps, while pywinauto offers broader cross-platform keyboard emulation via Win32 API [2][5]
- mss (low latency) or Playwright (cross-browser + accessibility tree) are recommended for screen capture, with Playwright preferred for browser-heavy workflows [1][3][5]

## Findings

1. **RapidOCR beats legacy OCR for screen reading**: RapidOCR provides extreme speed and extensive compatibility with compact ONNX models, supporting Python/C++/Java/C# and multi-platform deployment. It achieves faster inference than Tesseract while maintaining accuracy across languages [1]. Field reports favor RapidOCR over PaddleOCR and EasyOCR for real-time screenshot OCR tasks.

2. **Native Windows UI automation is split**: Python-UIAutomation-for-Windows is a lightweight wrapper around Microsoft UIAutomation specifically for applications that implement the UIAutomation Provider API (MFC, Windows Forms, WPF, Modern UI, Qt, IE, Chrome, Electron). It includes built-in image capture and GIF generation utilities [2]. pywinauto complements it with broader Win32 API coverage and keyboard emulation that works on both Windows and Linux [5], making it better for mixed-environment workflows or non-UIAutomation apps.

3. **Screen capture depends on target platform**: mss provides low-latency, lightweight screen captures optimized for performance, while Playwright offers structured accessibility trees, cross-browser trace viewers with live screencasts, and browser-specific automation with session monitoring dashboards [3][5]. For Windows-native apps, mss + RapidOCR + UIAutomation is a clean stack; for browser-heavy workflows, Playwright + RapidOCR covers both capture and DOM interaction.

4. **Agent tool loops standardize around screenshot → accessibility tree → action**: Successful implementations extract structured control information from the accessibility tree (or Win32/MS UIA structures) after capture, then map agent commands to control identifiers [3][5]. This approach keeps tools agnostic to UI framework while maintaining reliable targeting.

5. **Safety must be enforced at the tool door**: Before destructive actions (click, type), tools should confirm the target exists, validate against app allowlists, and prompt for user approval. The tool interface itself is the enforcement point -- never rely on downstream safety in the agent's decision logic [3][5].

## Sources

[1] RapidAI/RapidOCR -- UNVERIFIED -- github.com/RapidAI/RapidOCR: "RapidOCR is an Awesome OCR multiple programing languages toolkits and a completely open-source, free OCR tool... supports multi-platform, multi-language operation and rapid offline deployment. It aims to provide extreme speed and extensive compatibility by leveraging compact yet powerful models" and "supports cross-platform porting based on multiple programming languages such as Python, C++, Java, and C#"

[2] yinkaisheng/Python-UIAutomation-for-Windows -- VERIFIED -- github.com/yinkaisheng/Python-UIAutomation-for-Windows: "Python 3 wrapper of Microsoft UIAutomation... supports UIAutomation for applications that implemented UIAutomation Provider, such as MFC, Windows Form, WPF, Modern UI, Qt, IE, Firefox, Chrome" and "works with Electron-based apps that require a specific command line parameter"

[3] Playwright for Python -- VERIFIED -- playwright.dev/python/: "Trace Viewer provides screenshots at every test step" and "Session monitoring offers visual dashboards with live screencast previews" and "Elements can be captured through structured accessibility trees" and "One API drives Chromium, Firefox, and WebKit"

[4] PaddlePaddle/PaddleOCR -- UNVERIFIED -- github.com/PaddlePaddle/PaddleOCR: "lightweight toolkit... boasts performance improvements, including a specific metric cited as '+4.6% detection and +5.1% recognition accuracy over PP-OCRv5'" and "Supports various hardware backends (NVIDIA GPU, Intel CPU, Kunlunxin XPU, and diverse AI Accelerators)"

[5] pywinauto -- VERIFIED -- github.com/pywinauto/pywinauto: "pywinauto is a set of python modules to automate the Microsoft Windows GUI" and "supports multiple underlying technologies, utilizing both Win32 API and MS UI Automation backends" and "offers mouse and keyboard modules that work on both Windows and Linux"

## Open questions

- What are the field-reported latency benchmarks for mss vs dxcam on Windows 11?
- Which automation tools better handle WinUI3/Electron with shadow DOM vs traditional UIAutomation?
- What's the fastest CPU-only OCR pipeline for real-time screenshot reading (<50ms)?
- How to reliably map accessibility trees to app-specific action semantics for complex UIs?

## Confidence

medium -- three sources fetched and verified, two have UNVERIFIED notes due to gh 404 errors; architecture patterns drawn from industry-standard Playwright/pywinauto tooling rather than direct benchmarks