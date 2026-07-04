// bifrost_viz.js — Viz-canvas engine + card template registry + viz modules.
//
// Renders on a z:-1 canvas between the aurora (z:-2) and cockpit (z:≥0). Consumes trace
// events from the bus SSE feed (kind=trace) to build live data structures, then feeds them
// into registered card modules (force-graph, bar-chart, code-tree, etc.). Cards are pluggable:
// each has {id, label, mount(canvasCtx, data, width, height), unmount()} and the engine
// cycles through them or shows a grid on demand.
//
// Shared seam with Claude's narration bridge: the WHY-card content comes from 💭 thinking
// traces (meta.trace==='think'). Cards that render "why" panels consume these directly.
//
// Interface:
//   window.BifrostViz = {VizEngine, CardRegistry, registerCard, ...}
//   const viz = new VizEngine(canvasEl); viz.start();
//   viz.feedTrace({from, content, meta});   // called from the UI's SSE handler
//   viz.nextCard() / viz.prevCard() / viz.showGrid()

(function (global) {
  'use strict';

  // ---------------------------------------------------------------------------
  // Card template registry — pluggable viz modules
  // ---------------------------------------------------------------------------
  const CARD_REGISTRY = {};

  function registerCard(card) {
    // card: {id:str, label:str, mount:(ctx,data,width,height)=>void, unmount:()=>void}
    CARD_REGISTRY[card.id] = card;
  }

  // ---------------------------------------------------------------------------
  // Data model — live structures fed by trace events
  // ---------------------------------------------------------------------------
  class TraceData {
    constructor() {
      this.agentActivity = {};     // {agent: {toolCalls:0, thinking:0, lastSeen:ts, filesSeen:{}}}
      this.edges = [];             // [{from, to, weight}] — message graph edges
      this.fileTouches = {};       // {filepath: count} — code-tree heatmap
      this.timeline = [];          // [{ts, from, kind, summary}] — recent trace history
      this.maxTimeline = 200;
    }

    ingest(msg) {
      // msg is the rendered bus message: {from, kind, content, meta}
      // We only ingest kind=trace messages
      if (!msg || msg.kind !== 'trace') return;
      const agent = msg.from || '?';
      const meta = msg.meta || {};
      const traceKind = meta.trace || 'tool';   // 'tool' | 'thinking'
      const content = msg.content || '';

      // Agent activity
      const aa = this.agentActivity[agent] || (this.agentActivity[agent] = {
        toolCalls: 0, thinking: 0, lastSeen: '',
        filesSeen: {}, edgesOut: 0, edgesIn: 0
      });
      aa.lastSeen = msg.ts || aa.lastSeen;
      if (traceKind === 'tool' || traceKind === 'tool_call') {
        aa.toolCalls++;
        // Extract file paths from tool content: "🔧 read_file(path='xxx')" or similar
        const fileMatch = content.match(/path\s*=\s*['"]([^'"]+)['"]/) ||
                          content.match(/['"]([^'"]+\.(?:py|js|md|html|json|css))['"]/);
        if (fileMatch) {
          const fp = fileMatch[1];
          aa.filesSeen[fp] = (aa.filesSeen[fp] || 0) + 1;
          this.fileTouches[fp] = (this.fileTouches[fp] || 0) + 1;
        }
      } else if (traceKind === 'thinking' || traceKind === 'think') {
        aa.thinking++;
      }

      // Timeline
      this.timeline.push({ ts: msg.ts, from: agent, kind: traceKind,
        summary: content.slice(0, 80).replace(/^[🔧💭]\s*/, '') });
      if (this.timeline.length > this.maxTimeline) this.timeline.shift();

      // Extract file paths from any content string for the code-tree
      const filePattern = /(?:path\s*=\s*|file\s+)(?:'|")([^'"]+\.\w{1,6})(?:'|")/gi;
      let fm;
      while ((fm = filePattern.exec(content)) !== null) {
        const fp = fm[1];
        this.fileTouches[fp] = (this.fileTouches[fp] || 0) + 1;
      }
    }

    ingestEdge(from, to) {
      // Called from the UI when a chat message is sent between agents
      if (!from || !to || from === to) return;
      const existing = this.edges.find(e =>
        (e.from === from && e.to === to) || (e.from === to && e.to === from));
      if (existing) { existing.weight++; }
      else { this.edges.push({from, to, weight: 1}); }
      // Update agent edge counts
      const aaFrom = this.agentActivity[from] || (this.agentActivity[from] = {
        toolCalls:0, thinking:0, lastSeen:'', filesSeen:{}, edgesOut:0, edgesIn:0});
      aaFrom.edgesOut++;
      const aaTo = this.agentActivity[to] || (this.agentActivity[to] = {
        toolCalls:0, thinking:0, lastSeen:'', filesSeen:{}, edgesOut:0, edgesIn:0});
      aaTo.edgesIn++;
    }

    reset() {
      this.agentActivity = {};
      this.edges = [];
      this.fileTouches = {};
      this.timeline = [];
    }
  }

  // ---------------------------------------------------------------------------
  // VizEngine — owns the canvas, render loop, and card cycling
  // ---------------------------------------------------------------------------
  class VizEngine {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.data = new TraceData();
      this.cards = Object.values(CARD_REGISTRY);
      this.cardIdx = 0;
      this.gridMode = false;
      this.deckMode = false;     // full-view slide deck (shrinks message log)
      this.animating = false;
      this._raf = null;
      this.width = 0;
      this.height = 0;
      this._onChange = null;     // optional callback (cardIdx, gridMode) -> fired on navigate
      this._resize();
      this._bind();
    }

    get currentCard() { return this.cards[this.cardIdx % this.cards.length] || null; }
    get cardCount() { return this.cards.length; }
    cardInfo() {
      const c = this.currentCard;
      return c ? {id: c.id, label: c.label, idx: this.cardIdx, total: this.cards.length,
                   gridMode: this.gridMode, deckMode: this.deckMode} : null;
    }

    onChange(fn) { this._onChange = fn; }   // cockpit can subscribe to navigation events

    _resize() {
      const dpr = Math.min(global.devicePixelRatio || 1, 2);
      this.width = Math.max(1, Math.floor(this.canvas.clientWidth * dpr));
      this.height = Math.max(1, Math.floor(this.canvas.clientHeight * dpr));
      this.canvas.width = this.width;
      this.canvas.height = this.height;
    }

    _bind() {
      this._onResize = () => this._resize();
      global.addEventListener('resize', this._onResize);
      this._onVis = () => { document.hidden ? this.stop() : this.start(); };
      document.addEventListener('visibilitychange', this._onVis);
    }

    feedTrace(msg) { this.data.ingest(msg); }
    feedEdge(from, to) { this.data.ingestEdge(from, to); }

    nextCard() {
      if (this.gridMode) return;
      this.cardIdx = (this.cardIdx + 1) % Math.max(1, this.cards.length);
      if (this._onChange) this._onChange(this.cardInfo());
    }

    prevCard() {
      if (this.gridMode) return;
      this.cardIdx = (this.cardIdx - 1 + Math.max(1, this.cards.length)) % Math.max(1, this.cards.length);
      if (this._onChange) this._onChange(this.cardInfo());
    }

    showGrid() { this.gridMode = !this.gridMode; if (this._onChange) this._onChange(this.cardInfo()); }
    setDeckMode(on) { this.deckMode = !!on; if (this._onChange) this._onChange(this.cardInfo()); }

    jumpTo(cardId) {
      const idx = this.cards.findIndex(c => c.id === cardId);
      if (idx >= 0) { this.cardIdx = idx; this.gridMode = false; if (this._onChange) this._onChange(this.cardInfo()); }
    }

    _tick() {
      if (!this.animating) return;
      this._raf = global.requestAnimationFrame(() => this._tick());
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);

      // Semi-transparent dark fill so cards read over the aurora
      ctx.fillStyle = 'rgba(6, 7, 13, 0.75)';
      ctx.fillRect(0, 0, this.width, this.height);

      if (this.cards.length === 0) {
        ctx.fillStyle = '#5a5f70';
        ctx.font = '14px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('no viz cards registered', this.width / 2, this.height / 2);
        return;
      }

      if (this.gridMode) {
        this._renderGrid(ctx);
      } else {
        const card = this.cards[this.cardIdx % this.cards.length];
        if (card && card.mount) {
          try { card.mount(ctx, this.data, this.width, this.height); }
          catch (e) { this._renderError(ctx, card.id, e); }
        }
        this._renderLabels(ctx, card);
      }
    }

    _renderGrid(ctx) {
      const n = this.cards.length;
      const cols = Math.ceil(Math.sqrt(n));
      const rows = Math.ceil(n / cols);
      const cw = Math.floor(this.width / cols);
      const ch = Math.floor(this.height / rows);
      this.cards.forEach((card, i) => {
        const col = i % cols, row = Math.floor(i / cols);
        const x = col * cw, y = row * ch;
        ctx.save();
        ctx.beginPath(); ctx.rect(x + 4, y + 4, cw - 8, ch - 8); ctx.clip();
        // Mini card label
        ctx.fillStyle = '#242833'; ctx.fillRect(x, y, cw, ch);
        ctx.fillStyle = '#8b90a2'; ctx.font = '13px monospace'; ctx.textAlign = 'center';
        ctx.fillText(card.label || card.id, x + cw / 2, y + 16);
        try { card.mount(ctx, this.data, cw - 8, ch - 20); }
        catch (e) { ctx.fillStyle = '#f0666e'; ctx.fillText('err', x + cw / 2, y + ch / 2); }
        ctx.restore();
      });
    }

    _renderLabels(ctx, card) {
      // Card title top-left
      ctx.fillStyle = '#e7e9f0'; ctx.font = 'bold 13px monospace'; ctx.textAlign = 'left';
      ctx.fillText(card ? (card.label || card.id) : '—', 14, 22);
      // Navigation hint bottom-right
      if (this.cards.length > 1) {
        ctx.fillStyle = '#5a5f70'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
        ctx.fillText(`card ${this.cardIdx + 1}/${this.cards.length}  ← →  g:grid`, this.width - 14, this.height - 10);
      }
    }

    _renderError(ctx, cardId, err) {
      ctx.fillStyle = '#f0666e'; ctx.font = '12px monospace'; ctx.textAlign = 'center';
      ctx.fillText(`card "${cardId}" error: ${err.message || err}`, this.width / 2, this.height / 2);
    }

    start() { if (!this.animating) { this.animating = true; this._tick(); } }
    stop() { this.animating = false; if (this._raf) { global.cancelAnimationFrame(this._raf); this._raf = null; } }
    destroy() { this.stop(); global.removeEventListener('resize', this._onResize); document.removeEventListener('visibilitychange', this._onVis); }
  }

  // ---------------------------------------------------------------------------
  // Built-in card: Agent Activity Bar Chart
  // ---------------------------------------------------------------------------
  registerCard({
    id: 'bar-chart',
    label: 'Agent Activity',
    mount(ctx, data, w, h) {
      const agents = Object.keys(data.agentActivity);
      if (agents.length === 0) {
        ctx.fillStyle = '#5a5f70'; ctx.font = '12px monospace'; ctx.textAlign = 'center';
        ctx.fillText('no agent activity yet', w / 2, h / 2);
        return;
      }
      const pad = { top: 50, bottom: 40, left: 80, right: 30 };
      const chartW = w - pad.left - pad.right;
      const chartH = h - pad.top - pad.bottom;
      const maxVal = Math.max(1, ...agents.map(a => {
        const aa = data.agentActivity[a];
        return (aa.toolCalls || 0) + (aa.thinking || 0);
      }));
      const barW = Math.max(18, Math.min(60, chartW / agents.length - 8));
      const gap = (chartW - barW * agents.length) / (agents.length + 1);

      // Axes
      ctx.strokeStyle = '#3b425e'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.left, pad.top); ctx.lineTo(pad.left, h - pad.bottom);
      ctx.lineTo(w - pad.right, h - pad.bottom); ctx.stroke();

      agents.forEach((a, i) => {
        const aa = data.agentActivity[a];
        const total = (aa.toolCalls || 0) + (aa.thinking || 0);
        const x = pad.left + gap + i * (barW + gap);
        const barH = (total / maxVal) * chartH;
        const y = h - pad.bottom - barH;

        // Stacked: tool calls (blue) + thinking (violet)
        if (aa.toolCalls > 0) {
          const th = (aa.toolCalls / maxVal) * chartH;
          ctx.fillStyle = 'rgba(122,162,247,0.7)';
          ctx.fillRect(x, h - pad.bottom - th, barW, th);
        }
        if (aa.thinking > 0) {
          const th = (aa.thinking / maxVal) * chartH;
          const baseY = h - pad.bottom - ((aa.toolCalls + aa.thinking) / maxVal) * chartH;
          ctx.fillStyle = 'rgba(157,124,247,0.6)';
          ctx.fillRect(x, baseY, barW, th);
        }

        // Label
        ctx.fillStyle = '#e7e9f0'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
        ctx.fillText(a.slice(0, 6), x + barW / 2, h - pad.bottom + 14);

        // Value
        ctx.fillStyle = '#8b90a2'; ctx.font = '9px monospace';
        ctx.fillText(total, x + barW / 2, y - 4);
      });

      // Legend
      ctx.fillStyle = 'rgba(122,162,247,0.85)'; ctx.fillRect(pad.left, 28, 10, 10);
      ctx.fillStyle = '#e7e9f0'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
      ctx.fillText('tool calls', pad.left + 14, 37);
      ctx.fillStyle = 'rgba(157,124,247,0.75)'; ctx.fillRect(pad.left + 90, 28, 10, 10);
      ctx.fillText('thinking', pad.left + 104, 37);
    }
  });

  // ---------------------------------------------------------------------------
  // Built-in card: File Touch Heatmap (horizontal bars)
  // ---------------------------------------------------------------------------
  registerCard({
    id: 'code-tree',
    label: 'File Touch Heatmap',
    mount(ctx, data, w, h) {
      const files = Object.entries(data.fileTouches)
        .sort((a, b) => b[1] - a[1]).slice(0, 15);
      if (files.length === 0) {
        ctx.fillStyle = '#5a5f70'; ctx.font = '12px monospace'; ctx.textAlign = 'center';
        ctx.fillText('no file touches yet', w / 2, h / 2);
        return;
      }
      const pad = { top: 40, bottom: 20, left: 14, right: 14 };
      const barH = Math.min(16, (h - pad.top - pad.bottom) / files.length - 4);
      const maxVal = files[0][1];

      files.forEach(([fp, count], i) => {
        const y = pad.top + i * (barH + 4);
        const barW = (count / maxVal) * (w - pad.left - pad.right - 180);
        // Heat color: cool (blue) → hot (magenta)
        const t = count / maxVal;
        const r = Math.floor(70 + t * 185), g = Math.floor(70 + (1 - t) * 80), b = Math.floor(150 + t * 100);
        ctx.fillStyle = `rgba(${r},${g},${b},0.7)`;
        ctx.fillRect(pad.left, y, barW, barH);
        ctx.fillStyle = '#e7e9f0'; ctx.font = '10px monospace'; ctx.textAlign = 'left';
        const label = fp.length > 40 ? '…' + fp.slice(-39) : fp;
        ctx.fillText(label, pad.left + 6, y + barH / 2 + 3.5);
        ctx.fillStyle = '#8b90a2'; ctx.font = '9px monospace'; ctx.textAlign = 'right';
        ctx.fillText(count + '', w - pad.right, y + barH / 2 + 3.5);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // Built-in card: Force-Directed Message Graph
  // ---------------------------------------------------------------------------
  registerCard({
    id: 'force-graph',
    label: 'Message Graph',
    mount(ctx, data, w, h) {
      const edges = data.edges;
      if (edges.length === 0) {
        ctx.fillStyle = '#5a5f70'; ctx.font = '12px monospace'; ctx.textAlign = 'center';
        ctx.fillText('no message edges yet', w / 2, h / 2);
        return;
      }
      // Simple force layout: agents as nodes, messages as edges
      const agents = [...new Set([...edges.map(e => e.from), ...edges.map(e => e.to)])];
      const cx = w / 2, cy = h / 2;
      const radius = Math.min(w, h) * 0.35;

      // Layout agents in a circle
      const positions = {};
      agents.forEach((a, i) => {
        const angle = (i / agents.length) * Math.PI * 2 - Math.PI / 2;
        positions[a] = {
          x: cx + Math.cos(angle) * radius,
          y: cy + Math.sin(angle) * radius
        };
      });

      // Draw edges
      const maxW = Math.max(1, ...edges.map(e => e.weight));
      edges.forEach(e => {
        const from = positions[e.from], to = positions[e.to];
        if (!from || !to) return;
        ctx.strokeStyle = `rgba(122,162,247,${0.15 + (e.weight / maxW) * 0.5})`;
        ctx.lineWidth = 0.5 + (e.weight / maxW) * 2.5;
        ctx.beginPath(); ctx.moveTo(from.x, from.y); ctx.lineTo(to.x, to.y); ctx.stroke();
      });

      // Draw nodes
      agents.forEach(a => {
        const p = positions[a];
        const aa = data.agentActivity[a] || {toolCalls: 0, thinking: 0};
        const size = 14 + Math.min(20, Math.sqrt(aa.toolCalls + aa.thinking) * 4);
        // Agent color
        const colorMap = { claude: '#e0915c', deepseek: '#7aa2f7', user: '#5fd39b' };
        const color = colorMap[a] || '#8b90a2';
        ctx.fillStyle = color; ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(p.x, p.y, size, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        // Label
        ctx.fillStyle = '#0a0b0f'; ctx.font = 'bold 10px monospace'; ctx.textAlign = 'center';
        ctx.fillText(a.slice(0, 2).toUpperCase(), p.x, p.y + 3.5);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // Built-in card: Timeline feed (scrollable trace history)
  // ---------------------------------------------------------------------------
  registerCard({
    id: 'timeline',
    label: 'Trace Timeline',
    mount(ctx, data, w, h) {
      const lines = data.timeline.slice(-30);
      if (lines.length === 0) {
        ctx.fillStyle = '#5a5f70'; ctx.font = '12px monospace'; ctx.textAlign = 'center';
        ctx.fillText('no trace events yet', w / 2, h / 2);
        return;
      }
      const pad = { top: 36, left: 14, right: 14 };
      const lineH = Math.min(15, (h - pad.top) / lines.length);
      lines.forEach((l, i) => {
        const y = pad.top + i * lineH;
        const colorMap = { claude: '#e0915c', deepseek: '#7aa2f7' };
        const color = colorMap[l.from] || '#8b90a2';
        const icon = l.kind === 'thinking' ? '💭' : '🔧';
        ctx.fillStyle = color; ctx.font = '9px monospace'; ctx.textAlign = 'left';
        ctx.fillText(`${icon} ${l.from.slice(0, 2)}`, pad.left, y + lineH - 2);
        ctx.fillStyle = '#8b90a2'; ctx.font = '9px monospace';
        ctx.fillText(l.summary.slice(0, 90), pad.left + 50, y + lineH - 2);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // Exports
  // ---------------------------------------------------------------------------
  const api = { VizEngine, registerCard, CARD_REGISTRY, TraceData };
  global.BifrostViz = api;
})(typeof window !== 'undefined' ? window : globalThis);
