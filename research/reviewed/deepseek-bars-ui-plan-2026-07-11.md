# DeepSeek bars-UI build plan (verbatim; QUEUED behind the design-language arc)

Provenance: bus msg 1783749254464-0, 2026-07-11 ~02:14 (his runner write-gated). Daniel opened the
UI design-language arc minutes later -- this plan executes in whatever language that arc lands.

Write access is disabled — the runner needs `--allow-write` to let me edit files. Here's my complete build plan for when writes are enabled. All edits target `scripts/bifrost_ui.py`:

---

## Progress Bars — UI Lane Build Plan

### Edit 1: Server-side — wire `progress_view()` into `/status`

Replace the `_status()` return statement with one that also collects progress data:

```python
        # Progress bars (turn_metrics data half; polled into /status — UI renders the cards).
        progress = {}
        try:
            from core.comm.turn_metrics import progress_view
            for a in agents:
                aid = a.get("agent")
                if not aid:
                    continue
                pv = progress_view(aid)
                if pv is not None:
                    progress[aid] = pv
        except Exception:
            pass
        return {"paused": control.is_paused(), "pause": control.pause_status(),
                "agents": agents, "known": known, "activities": control.get_activities(),
                "signals": signals, "max_hops": control.MAX_HOPS,
                "halted": control.halted_agents(),
                "narration": control.get_narration_level(),
                "progress": progress}
```

### Edit 2: CSS — 280px slide-in card styles

Insert before `/* === slide deck cards (mini teaching slides...`:

```css
  /* === progress bars (turn_metrics — polled, not pushed; 280px card slides in from right) === */
  #prog-strip{display:none; flex-direction:column; align-items:flex-end; margin:0 16px; padding:4px 0; gap:5px;
    border-bottom:1px solid var(--glass-line); background:linear-gradient(to bottom,var(--glass),transparent 50%);
    backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px)}
  #prog-strip.show{display:flex}
  .prog-card{display:flex; flex-direction:column; gap:4px; width:280px;
    background:var(--panel); border:1px solid var(--border); border-radius:11px;
    padding:8px 11px; font-size:12px; box-shadow:var(--shadow);
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
    animation:progSlideIn .3s cubic-bezier(.2,.9,.3,1.05) both;
    transition:border-color .35s,background .35s,opacity .4s,transform .4s}
  .prog-card.done{border-color:rgba(95,211,155,.5); background:rgba(95,211,155,.06);
    animation:progFlash .5s ease-out}
  .prog-card.removing{opacity:0; transform:translateX(18px)}
  @keyframes progSlideIn{from{opacity:0;transform:translateX(28px)}to{opacity:1;transform:none}}
  @keyframes progFlash{0%{box-shadow:0 0 0 rgba(95,211,155,0)}40%{box-shadow:0 0 22px rgba(95,211,155,.45)}100%{box-shadow:0 0 0 rgba(95,211,155,0)}}
  .prog-card .phead{display:flex; align-items:baseline; gap:7px}
  .prog-card .phead .pagent{font-weight:650; font-size:12px}
  .prog-card .phead .pagent.claude{color:var(--claude)} .prog-card .phead .pagent.deepseek{color:var(--deepseek)}
  .prog-card .phead .pelapsed{font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:11.5px; color:var(--faint); margin-left:auto; min-width:38px; text-align:right}
  .prog-card .phead .pelapsed.warn{color:var(--amber)} .prog-card .phead .pelapsed.bad{color:var(--danger)}
  .prog-bar-track{position:relative; height:6px; background:var(--bg2); border-radius:3px; overflow:hidden}
  .prog-bar-band{position:absolute; top:0; height:100%; background:rgba(122,162,247,.09); border-radius:3px; transition:width .7s ease}
  .prog-bar-fill{position:absolute; top:0; left:0; height:100%; background:linear-gradient(90deg,var(--accent),var(--accent2)); border-radius:3px; transition:width .7s ease}
  .prog-bar-fill.past-med{background:linear-gradient(90deg,var(--amber),#e0883a)}
  .prog-bar-fill.past-p90{background:linear-gradient(90deg,var(--danger),#e05058)}
  .prog-pct-track{position:relative; height:3px; background:var(--bg2); border-radius:2px; overflow:hidden}
  .prog-pct-fill{position:absolute; top:0; left:0; height:100%; background:var(--accent); border-radius:2px; transition:width .7s ease}
  .prog-pct-fill.done{background:var(--user); box-shadow:0 0 6px rgba(95,211,155,.35)}
  .prog-card .pfoot{display:flex; align-items:baseline; gap:8px; font-size:10.5px; color:var(--faint)}
  .prog-card .pfoot .peta{color:var(--muted)}
  .prog-card .pfoot .peta.low{font-style:italic}
  .prog-card .pfoot .ppct{color:var(--muted); margin-left:auto}
```

### Edit 3: HTML — progress strip container

After `<div id="hud"><div id="hud-toggle"...></div></div>`, add:

```html
  <div id="prog-strip"></div>
```

### Edit 4: JS — `renderProgress()` function

Insert between `toggleHUD()` and the `// click-away closes expanded hud rows + deck` comment:

```js
// === progress bars (turn_metrics — polled from /status; 280px card slides in from right) ===
var _progState = {};   // {agent: {doneTs: ms, removing: bool}} — tracks removal animation state
var _lastProgSig = null;
function renderProgress(prog){
  prog = prog || {};
  var strip = document.getElementById('prog-strip');
  if(!strip) return;
  var sig = JSON.stringify(prog);
  if(sig === _lastProgSig) return;
  _lastProgSig = sig;
  var now = Date.now();
  var agents = Object.keys(prog);
  // Detect newly-done agents (were in _progState, now gone from prog)
  Object.keys(_progState).forEach(function(a){
    if(!prog[a] && !_progState[a].doneTs){
      _progState[a].doneTs = now;   // start the 2s green-flash clock
    }
  });
  // Remove state for agents long-gone
  Object.keys(_progState).forEach(function(a){
    if(!prog[a] && _progState[a].doneTs && now - _progState[a].doneTs > 2200){
      delete _progState[a];
    }
  });
  // Build cards
  var activeAgents = new Set(agents);
  Object.keys(_progState).forEach(function(a){
    if(_progState[a].doneTs && now - _progState[a].doneTs < 2200) activeAgents.add(a);
  });
  if(!activeAgents.size){ strip.classList.remove('show'); strip.innerHTML=''; return; }
  strip.classList.add('show');
  // Reconcile DOM
  var existing = {};
  [].forEach.call(strip.children, function(el){ existing[el.dataset.agent] = el; });
  activeAgents.forEach(function(a){
    var el = existing[a];
    var p = prog[a];
    var done = !p;   // was in progress, now gone -> flash
    if(!el){
      el = document.createElement('div');
      el.className = 'prog-card';
      el.dataset.agent = a;
      strip.appendChild(el);
    }
    if(done && !el.classList.contains('done')){
      el.classList.add('done');
      el.classList.remove('removing');
      // Schedule removal
      setTimeout(function(){
        if(el && el.dataset.agent === a){
          el.classList.add('removing');
          setTimeout(function(){ if(el && el.parentNode) el.remove(); }, 450);
        }
      }, 2000);
    }
    if(p){
      el.classList.remove('done','removing');
      var eta = p.eta;
      var elapsed = p.elapsed_s || 0;
      var pct = p.pct_estimate;
      var median = eta ? eta.median_s : null;
      var p90 = eta ? eta.p90_s : null;
      var conf = eta ? eta.confidence : null;
      var bandPct = (p90 && p90 > 0) ? Math.min(100, (elapsed / p90) * 100) : 0;
      var fillPct = (p90 && p90 > 0) ? Math.min(100, (elapsed / p90) * 100) : 0;
      var pastMed = median && elapsed > median;
      var pastP90 = p90 && elapsed > p90;
      var remaining = median ? Math.max(0, Math.round(median - elapsed)) : null;
      var elapsedClass = pastP90 ? 'bad' : (pastMed ? 'warn' : '');
      var fillClass = pastP90 ? 'past-p90' : (pastMed ? 'past-med' : '');
      var pctStr = pct !== null && pct !== undefined ? pct + '%' : '--';
      var etaStr = remaining !== null ? '~' + remaining + 's' : (median ? median + 's median' : '…');
      el.innerHTML =
        '<div class="phead">'+
          '<span class="pagent ' + (a==='claude'?'claude':a==='deepseek'?'deepseek':'') + '">' + esc(a) + '</span>'+
          '<span class="pelapsed ' + elapsedClass + '">' + elapsed.toFixed(1) + 's</span>'+
        '</div>'+
        '<div class="prog-bar-track">'+
          '<div class="prog-bar-band" style="width:' + bandPct + '%"></div>'+
          '<div class="prog-bar-fill ' + fillClass + '" style="width:' + fillPct + '%"></div>'+
        '</div>'+
        '<div class="prog-pct-track">'+
          '<div class="prog-pct-fill" style="width:' + (pct||0) + '%"></div>'+
        '</div>'+
        '<div class="pfoot">'+
          '<span class="peta' + (conf==='low'?' low':'') + '">' + esc(etaStr) + (conf==='low'?' (low)':'') + '</span>'+
          '<span class="ppct">' + pctStr + '</span>'+
        '</div>';
    }
  });
  // Remove cards for agents no longer active
  [].forEach.call(strip.children, function(el){
    if(!activeAgents.has(el.dataset.agent)) el.remove();
  });
}
```

### Edit 5: JS — call `renderProgress` in `applyStatus`

After `renderHUD(s.activities||{});` add:

```js
  renderProgress(s.progress||{});
```

### Edit 6: JS — SSE `turn:done` handler (snap-to-100% push)

In the `addMsg` hook, extend to detect turn:done traces:

```js
var _origAddMsg = addMsg;
addMsg = function(m){
  if((m.kind||'chat')==='trace'){
    _captureTrace(m);
    // turn:done push — snap the progress bar to 100% green immediately
    var content = (m.content||'');
    if(content.indexOf('turn:done')>=0 && m.from){
      var agent = m.from;
      if(_progState[agent] !== undefined || document.querySelector('.prog-card[data-agent="'+esc(agent)+'"]')){
        _progState[agent] = _progState[agent] || {};
        _progState[agent].doneTs = Date.now();
        var card = document.querySelector('.prog-card[data-agent="'+esc(agent)+'"]');
        if(card){
          card.classList.add('done');
          var pctFill = card.querySelector('.prog-pct-fill');
          if(pctFill){ pctFill.style.width = '100%'; pctFill.classList.add('done'); }
          var ppct = card.querySelector('.ppct');
          if(ppct) ppct.textContent = '100%';
          setTimeout(function(){
            if(card && card.dataset.agent === agent){
              card.classList.add('removing');
              setTimeout(function(){ if(card && card.parentNode) card.remove(); }, 450);
            }
          }, 2000);
        }
      }
    }
  }
  return _origAddMsg(m);
};
```

---

## What each edit does

| Edit | What | Why |
|------|-------|-----|
| 1 | `/status` now includes `progress` dict keyed by agent | Poll-based data feed — the co-design's core choice |
| 2 | CSS for 280px glass card, animated bars, color tiers | The render spec: slide-in, amber-at-median, red-at-p90, green flash |
| 3 | `<div id="prog-strip">` container | DOM anchor for the cards |
| 4 | `renderProgress()` — fingerprint-diffs, builds/removes cards | Same pattern as `renderHUD` — only rebuild on real change |
| 5 | Call in `applyStatus` | Wired into the existing 1.2s poll loop |
| 6 | SSE `turn:done` handler — instant snap-to-green | The one push exception in the poll design |

**To proceed**: restart the runner with `--allow-write` and I'll apply all six edits, then `reload_ui` for you to refresh.