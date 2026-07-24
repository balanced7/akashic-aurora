---
akashic_id: art_20260709_visual-generation-repo-sweep-web-agent-v_78ec97
akashic_sha: 35509c4b0b20
status: draft
type: report
date: 2026-07-09
title: Visual-generation repo sweep -- web agent verification report (verbatim)
gist: "# Visual-generation repo sweep -- web agent verification report (verbatim) Context: Daniel supplied an LLM-generated list of AI presentation"
tenant: solo
visibility: fleet
seats: []
category: [migration, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_visual-generation-integration-reconciled_3150cc
    rel: cites
created: "2026-07-09T20:17:21"
updated: "2026-07-23T21:42:23"
---
<!-- GENERATED PROJECTION of art_20260709_visual-generation-repo-sweep-web-agent-v_78ec97 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Visual-generation repo sweep -- web agent verification report (verbatim)

# Visual-generation repo sweep -- web agent verification report (verbatim)

Context: Daniel supplied an LLM-generated list of AI presentation/chart/diagram repos plus
philholden/partialupdate (real-time UI updates) with the directive "integrate the best
aspects into our work". A fenced web agent verified every claim against the GitHub API +
READMEs on 2026-07-09. Companion report: deepseek integration seams (same date). Preserved
verbatim below; reconciliation in docs/visual-gen-integration-2026-07.md.

---

# GitHub Project Verification Report -- 2026-07-09

Method: every repo checked against the GitHub API (existence, stars, license, last push) + README fetched from the actual repo. Verdict up front: **all 10 paths exist -- no hallucinated repos.** Two are unusable anyway (no license / no code), and several claims needed correction.

## Per-repo findings

**1. philholden/partialupdate -- EXISTS (priority assessment)**
- (a) Actually: a multi-user AI chat that generates and edits its own UI (HTML/CSS/JS) on the fly, built on Chrome's new **Declarative Partial Updates** spec -- LLM streams `<template for="name">` fragments that patch DOM at `<?marker name="...">` insertion points; forms submit structured data back into LLM context.
- (b) MIT. (c) TypeScript on **Cloudflare Workers + Durable Objects + hibernatable WebSockets** (not a plain server); needs Cloudflare account + AI Gateway. (d) 18 stars, created 2026-06-26 (two weeks old), pushed 2026-06-27. A fresh demo, not infrastructure.
- (e) Steal: the **declarative patch protocol** -- server streams named HTML fragments; browser applies them at markers with zero client framework. Its spec.md documents a clean delimiter-based message format with server-side routing props (include/exclude client ids) -- directly maps to Bifrost fidelity-ladder routing.
- (f) Rewrite-idea-only. Hard dependency: the underlying spec is **Chrome 148+ behind the experimental-web-platform flag only** (confirmed via developer.chrome.com); polyfills exist (`template-for-polyfill`, `html-setters-polyfill`). For your Python+SSE console, the production-grade equivalent that works today in every browser is **datastar** or **htmx's SSE extension** (see shortlist).

**2. presenton/presenton -- EXISTS, claims check out**
- (a) Self-hosted AI presentation generator **and REST API** (Gamma alternative). (b) Apache-2.0 (matches Aurora's). (c) Next.js frontend + **FastAPI backend** (verified `servers/fastapi` + `servers/nextjs` in tree), single Docker image, also desktop apps; providers: Ollama, LM Studio, OpenAI, Gemini, Anthropic, Bedrock, any OpenAI-compatible. Exports **editable PPTX** + PDF. Has a **built-in MCP server**. (d) ~9.0k stars, pushed 2026-07-09 (today) -- actively maintained.
- (e) Steal: run as Docker sidecar and hit its **generation API / MCP** -- templates are plain HTML+Tailwind, so agents can author custom deck templates as code.
- (f) Drop-in service (docker compose). Heaviest footprint of the good options.

**3. allweonedev/presentation-ai -- EXISTS, claim overstated**
- (a) Open-source Gamma-alternative presentation generator with outline-first workflow, 38 themes, live slide build, PPTX export. "Fully local" is **not accurate**: requires PostgreSQL, Google OAuth (NextAuth), and optional cloud keys (Together, FAL, Tavily, UploadThing); local models possible via Ollama/LM Studio but the app itself is a SaaS-shaped Next.js+Prisma stack. (b) MIT. (c) Next.js/React/Postgres/Plate editor; self-host node server. (d) ~2.9k stars, pushed 2026-06-05, maintained.
- (e) Steal: the **outline-first workflow** (generate outline -> human edits -> then render slides) -- the right UX for chronicle->deck.
- (f) Heavy self-host; realistically idea-only for you.

**4. ysskrishna/ai-ppt-slide-generator -- EXISTS, claims accurate**
- (a) Backend-only FastAPI service that turns a topic (or user-supplied slide JSON) into PPTX via Gemini + python-pptx, with configurable layouts/fonts/colors. (b) MIT. (c) Python 3.12/FastAPI/Postgres/Docker; pure API, no UI. (d) 20 stars, pushed 2025-12-27; small portfolio project, low bus-factor.
- (e) Steal: the minimal **JSON-slide-spec -> python-pptx renderer** pattern (layout types: title/bullet + config object) -- maps 1:1 to a `deck_renderer.py` inside Aurora with zero Node dependency.
- (f) Library-pattern; re-implement in an afternoon rather than adopt its Postgres.

**5. cobacha/ppt-agent -- EXISTS, claims accurate but unproven**
- (a) Text/URL -> animated slides in ~30s; FastAPI + Next.js; Anthropic API; 18 themes; exports a **single self-contained HTML file** (all CSS/JS inline, offline, grid overview on 'G'), plus PDF; SQLite history, rate limiting, per-slide regeneration, design-check auto-retry. (b) MIT. (c) Docker compose self-host. (d) **1 star**, created 2026-05-25, pushed 2026-06-12 -- brand-new, zero community.
- (e) Steal: **single-file HTML deck export** + the quality-gate auto-retry loop ("slides that fail design checks get regenerated") -- that's your "trust the gates" philosophy applied to rendering.
- (f) Drop-in service technically, but 1-star maturity risk; safest as idea/template source.

**6. yujisatojr/chart-agent -- EXISTS, stale and unlicensed**
- (a) Chatbot that generates simple charts (React + Chart.js + FastAPI + GPT-4o). (b) **NO LICENSE** -- cannot copy code into an Apache-2.0 repo. (c) React client + FastAPI server, dev-mode only. (d) 13 stars, last push 2024-06-29 -- abandoned ~2 years.
- (e) Steal (idea-only): LLM emits a Chart.js config JSON, client renders it -- trivial to re-implement.
- (f) Idea-only (license blocks anything more).

**7. thongekchakrit/ChartAI -- EXISTS, dead and unlicensed**
- (a) GPT-3-era Streamlit app: upload CSV, chat, text-to-SQL, draggable Nivo charts. (b) **NO LICENSE.** (c) Streamlit single app. (d) 78 stars, last push 2023-06-16 -- dead 3 years.
- (e)/(f) Nothing worth taking that isn't done better elsewhere; idea-only. The sole repo under topic `generative-chart` is its modern successor: **OpenVizAI/OpenVizAI** (43 stars, pushed 2026-05-10, "AI picks the chart type and fields -- JavaScript does the rest").

**8. Cocoon-AI/architecture-diagram-generator -- EXISTS, claims accurate**
- (a) Not an app: a **packaged Claude skill** (zip + prompt/templates) that makes Claude emit dark-themed architecture diagrams as standalone HTML/SVG files with built-in Copy/PNG/PDF export buttons and semantic color coding per component type. (b) MIT. (c) HTML templates + skill definition; runs wherever Claude runs. (d) ~6.4k stars, created 2025-12-22, pushed 2026-05-13.
- (e) Steal: the **self-contained HTML/SVG diagram template** (embedded export buttons, slate-950 theme, arrows-behind-boxes layering) -- lift it as Aurora's visual-report house style, or just install the skill in Claude Code as-is.
- (f) Drop-in (it literally targets Claude; zero integration code).

**9. DayuanJiang/next-ai-draw-io -- EXISTS, claims accurate; the giant of the list**
- (a) Next.js app embedding draw.io: AI generates/modifies **draw.io XML** from natural language, streamed live onto the canvas (Vercel AI SDK + react-drawio); multi-provider; desktop app; Docker. (b) Apache-2.0. (c) Self-host node/Docker, or hosted demo; plus a published **MCP server**: `claude mcp add drawio -- npx @next-ai-drawio/mcp-server@latest` -- diagrams appear in the browser in real time. (d) ~33k stars, pushed 2026-07-09 (today) -- very actively maintained.
- (e) Steal: the **MCP server + draw.io-XML-as-artifact** design -- diagrams are durable, editable, versionable XML (Ledger-friendly), not opaque PNGs.
- (f) Drop-in (one MCP add for agent use; Docker for full app).

**10. graphic-design-ai/creatiposter -- EXISTS but is a PAPER STUB**
- (a) ByteDance's CreatiPoster (arXiv 2506.10890): multi-layer editable AI graphic composition. **No code, no model checkpoint, no license** -- the README's own to-do list still shows "publish codebase" unchecked; language=null; last push 2025-06-14. (d) 100 stars. (f) **Unusable** -- bookmark and revisit only if they ship. No verified open-source equivalent at its game; the practical route for editable visual compositions today is HTML/SVG generation (item 8's approach).

## Topic sweeps (verified via API)
- `topic:presentation-maker` -- junk drawer; top hit SlideAI (156 stars, dead since 2023). Nothing here beats your list.
- `topic:generative-chart` -- exactly one repo: OpenVizAI (above).
- No dominant "awesome presentation tools" list exists; search returns noise.

**Three standouts that beat the listed repos at their own game** (all verified today):
- **starfederation/datastar** -- 4.6k stars, MIT, pushed 2026-07-08. SSE-native hypermedia framework: any backend (your Python server) streams HTML-fragment patch events; a single small JS file applies them. Beats partialupdate at its own game, in all browsers, today.
- **yuzutech/kroki** -- 4.2k stars, MIT, pushed 2026-07-08. Self-hosted Docker service: one HTTP API turning Mermaid/PlantUML/Graphviz/D2/Excalidraw text into SVG/PNG. Beats every AI-diagram app at deterministic, server-side, token-free rendering. (mermaid itself: 89k stars, MIT, active -- one `<script>` tag renders diagrams client-side inside your console.)
- **slidevjs/slidev** -- 47.6k stars, MIT, pushed 2026-07-03. Markdown -> developer-grade slides/PDF/hosted deck. For chronicle->deck, an agent writing markdown + slidev rendering beats AI-layout tools on determinism and cost. (Lighter headless option: marp-team/marp-cli, 3.7k stars, MIT, pushed today -- md -> PPTX/PDF/HTML in one CLI call.)

## Ranked shortlist (value-to-effort for your three goals)

1. **datastar (or htmx+SSE extension)** -- goal (i). Keep your existing SSE channel; change payloads from "poll signal" to "HTML fragment + target selector"; DOM updates in place, no reloads, no polling, no build step, works in every browser. Library drop-in against the current Python console. Take partialupdate's routing idea (include/exclude client ids per fragment) for per-agent console views; skip its Chrome-flag dependency.
2. **next-ai-draw-io MCP server** -- goal (ii). One `claude mcp add` and agents produce live, editable architecture/flow diagrams; store the draw.io XML as atoms so diagrams are regenerable projections, not screenshots. 33k stars, Apache-2.0, pushed today -- the safest big bet on the list.
3. **kroki (+ mermaid in-console)** -- goal (ii) cheap tier. Docker sidecar next to Redis; `POST text -> SVG` lets any agent render diagrams deterministically with zero LLM tokens (token-frugality directive). Mermaid script-tag in the console renders those same text specs live inside SSE-patched panels.
4. **marp-cli or slidev** -- goal (iii) cheap tier. Chronicle/notes are already markdown-shaped; one CLI call yields a shareable HTML/PPTX/PDF deck, deterministic and reviewable in git. Steal Cocoon's self-contained-HTML-with-export-buttons template as the house style for one-page visual reports.
5. **presenton** -- goal (iii) full tier, when you want AI-designed editable PPTX for external optics: Apache-2.0 Docker sidecar with REST API + MCP, works against Ollama. Adopt only if the marp/slidev tier proves insufficient -- it is the heaviest item that still earns its place.

Licensing hazards to record: chart-agent and ChartAI have no license (ideas only, never copy code); creatiposter has no code at all.
