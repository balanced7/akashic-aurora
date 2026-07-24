---
akashic_id: art_20260716_t002-ui-trace-collapse-design-pre-regist_fc22a6
akashic_sha: b4c6844f0b6d
status: draft
type: report
date: 2026-07-16
title: T002 UI Trace Collapse — Design + Pre-Registered Pins (2026-07-16)
gist: "Cites: night-build-brief-2026-07-16.md (7-step method), T002 ledger entry (approved, owner deepseek-plumbing), research:web:ui_trace_collaps"
tenant: solo
visibility: fleet
seats: []
category: [memory, security, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-16T01:35:20"
updated: "2026-07-16T01:35:20"
---
<!-- GENERATED PROJECTION of art_20260716_t002-ui-trace-collapse-design-pre-regist_fc22a6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T002 UI Trace Collapse — Design + Pre-Registered Pins (2026-07-16)

Cites: night-build-brief-2026-07-16.md (7-step method), T002 ledger entry (approved, owner deepseek-plumbing),
research:web:ui_trace_collapse_prior_art.

## Prior Art (research_note captured)

1. **Discord compact mode:** consecutive messages from same author collapse — only first shows
   full timestamp, rest are minimal text. Pattern: group by author, show header once.
2. **ChatGPT/Open WebUI "Thinking" toggle:** collapsible sections with header "Reasoning (N steps)"
   that expands on click. Collapsed state shows count; expanded shows content.
3. **Our own W4 render_collapsed:** consecutive same-(frm, kind) runs → first shown + "N more"
   summary. Same pattern, different surface.

**Synthesis:** Hybrid. Consecutive same-agent traces collapse into ONE collapsible card per agent.
Header shows agent name + counts by trace kind. Collapsed by default; click to expand.

## Design

### What changes

Only `scripts/bifrost_ui.py` — the `renderMsg` function and the `addMsg` message-processing
loop. The `_traceBuffer` and `buildDeckCards` slide deck are UNCHANGED.

### Algorithm

In `addMsg`, when a `kind==='trace'` message arrives:
1. Buffer it into `_traceBuffer` (existing behavior, unchanged).
2. Check: is the previous displayed message ALSO a trace from the SAME agent?
   - YES → append this trace to the CURRENT `.trace-card`'s hidden detail list, increment the
     count badge in the header. Do NOT create a new DOM node.
   - NO (or previous was a work message) → finalize any open trace-card from a prior agent,
     then create a NEW `.trace-card` for this agent.

When a `kind!=='trace'` message (work/sig) arrives:
1. Finalize any open trace-card (close it, make it a static collapsed card in the stream).
2. Render the work message normally (existing behavior, unchanged).

### The `.trace-card` DOM structure

```html
<div class="trace-card" data-agent="deepseek">
  <div class="tc-header" onclick="toggleTraceCard(this)">
    <span class="tc-arrow">▶</span>
    <span class="tc-agent deepseek">deepseek</span>
    <span class="tc-counts">4🔧 2💭 1📖</span>
    <span class="tc-summary"> — read_file: packet_spec.py, write_file: test_...</span>
  </div>
  <div class="tc-body" style="display:none">
    <div class="traceline"><span class="trav deepseek">deepseek</span><span class="trat">💭 researching prior art for T002...</span></div>
    <!-- ... more tracelines ... -->
  </div>
</div>
```

### CSS

```
.trace-card { margin: 2px 0; border-left: 2px solid var(--faint); padding: 2px 8px; }
.tc-header { cursor: pointer; font-size: 11px; display: flex; align-items: center; gap: 6px; }
.tc-header:hover { color: var(--text); }
.tc-arrow { font-size: 10px; transition: transform 0.2s; display: inline-block; width: 12px; }
.tc-arrow.open { transform: rotate(90deg); }
.tc-agent { font-weight: 600; }
.tc-counts { color: var(--accent); }
.tc-summary { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tc-body { margin-top: 4px; }
.tc-body .traceline { margin-left: 12px; }
```

### JAVASCRIPT — the toggle function

```javascript
function toggleTraceCard(header){
  var body = header.nextElementSibling;
  var arrow = header.querySelector('.tc-arrow');
  if(body.style.display === 'none'){
    body.style.display = 'block';
    arrow.classList.add('open');
  } else {
    body.style.display = 'none';
    arrow.classList.remove('open');
  }
}
```

### State tracking

One global variable tracks the currently-open trace card:

```javascript
var _currentTraceCard = null;  // {agent, dom: the .trace-card node, counts: {tool:N, thinking:N, ...}, lines: [...]}
```

When a trace arrives:
- Same agent as `_currentTraceCard` → append to `.tc-body`, update counts
- Different agent → finalize `_currentTraceCard` (close it), create new one

When a non-trace message arrives:
- If `_currentTraceCard` exists → finalize it, set to null
- Render work message normally

### Edge cases

- **First message is a trace:** Create open trace-card. Header shows initial count.
- **Single trace, then work message:** Trace-card header shows "1🔧" — still collapsible.
- **Rapid consecutive traces during SSE burst:** All collapse into same card (avoid DOM thrash).
- **Trace from unknown agent:** Same behavior — create/open card for that agent.
- **Page scroll / history load:** History messages re-render via `renderMsg`. Trace collapse
  is live-insertion only — history replay renders each trace as a standalone `.traceline`
  (existing behavior preserved). The collapsed card is an additive live-stream optimization.

## Pre-Registered Pins

| Pin | What it tests | Verdict claim |
|-----|---------------|---------------|
| **T2-P1** | 5 consecutive traces from deepseek → ONE .trace-card with count "5" in header | CARD-CREATED |
| **T2-P2** | 3 traces from deepseek, 1 chat from claude, 2 traces from deepseek → TWO separate cards (run broken) | RUN-BROKEN |
| **T2-P3** | Click header arrow → body expands; click again → collapses | TOGGLE-WORKS |
| **T2-P4** | Traces from different agents → separate cards (deepseek card, claude card) | AGENT-SEPARATE |
| **T2-P5** | Work message ends the trace run → card finalized, work message appears after | CARD-FINALIZED |
| **T2-P6** | Single trace → still creates a card (not inline traceline) | SINGLETON-CARD |
| **T2-P7** | Card header shows agent name + per-kind counts | COUNTS-VISIBLE |
| **T2-P8** | History replay (renderMsg) renders tracelines as before (no collapse) | HISTORY-UNCHANGED |

## NOT in scope

- The `_traceBuffer` / slide deck (`buildDeckCards`, `showDeck`) — unchanged
- History message collapse (scrollback rendering stays as-is)
- CSS color/animation polish beyond basic functionality
- Per-kind filtering within the trace card (v2)
