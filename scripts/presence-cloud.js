// presence-cloud.js — bottom-left avatar + "thinking cloud" (claude's lane, Aurora Glass)
//
// Daniel's sketch: the active agent's avatar sits at the bottom-left by the composer, and a
// thought-bubble "cloud" rises out of it showing what that agent is CURRENTLY thinking — with the
// little trailing bubbles connecting the cloud to the avatar. It's the rich-presence idea, and the
// natural home for the 💭 reasoning traces that already stream on the bus.
//
// Standalone (theme-void.js pattern): self-mounts a fixed element, reads the globals that
// bifrost_ui.py's applyStatus already caches each poll (window._glassCardData, window._lastActs).
// Only bifrost_ui.py change is a one-line <script src="/presence-cloud.js"> include + its route.

(function (global) {
  'use strict';

  var CSS =
    '#pcloud{position:fixed;left:18px;bottom:104px;z-index:40;display:flex;align-items:flex-end;gap:0;' +
      'pointer-events:none;font-family:var(--sans,-apple-system,system-ui,sans-serif)}' +
    '#pcloud.hide{opacity:0;transform:translateY(8px);transition:opacity .4s,transform .4s}' +
    '#pcloud.show{opacity:1;transform:none;transition:opacity .4s,transform .4s}' +
    /* avatar */
    '#pcloud .pcav{width:46px;height:46px;border-radius:15px;flex:none;display:grid;place-items:center;' +
      'font-size:16px;font-weight:700;color:#0a0b0f;letter-spacing:.02em;position:relative;' +
      'box-shadow:0 6px 20px -6px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.08) inset}' +
    '#pcloud .pcav .rglow{position:absolute;inset:-3px;border-radius:18px;opacity:.55;filter:blur(7px);z-index:-1}' +
    /* the thought cloud, floating up-right of the avatar */
    '#pcloud .cloud{position:absolute;left:34px;bottom:52px;max-width:260px;min-width:96px;' +
      'padding:10px 13px;border-radius:16px 16px 16px 5px;color:var(--text,#eef0f7);font-size:12.5px;line-height:1.4;' +
      'background:var(--glass,rgba(18,20,28,.62));backdrop-filter:blur(20px) saturate(1.3);-webkit-backdrop-filter:blur(20px) saturate(1.3);' +
      'border:1px solid var(--glass-line,rgba(255,255,255,.12));' +
      'box-shadow:0 1px 0 rgba(255,255,255,.05) inset,0 18px 40px -20px rgba(0,0,0,.85);' +
      'pointer-events:auto;animation:cloudbob 4.5s ease-in-out infinite}' +
    '#pcloud .cloud .verb{font-size:10px;letter-spacing:.09em;text-transform:uppercase;font-weight:700;margin-bottom:3px;display:flex;align-items:center;gap:6px}' +
    '#pcloud .cloud .verb .z{width:6px;height:6px;border-radius:50%;animation:zpulse 1.3s ease-in-out infinite}' +
    '#pcloud .cloud .detail{color:var(--muted,#9297ab);font-family:var(--mono,ui-monospace,monospace);font-size:11px;' +
      'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:234px}' +
    /* the trailing thought bubbles from avatar up to the cloud */
    '#pcloud .trail{position:absolute;left:30px;bottom:44px;width:14px;height:14px;pointer-events:none}' +
    '#pcloud .trail i{position:absolute;border-radius:50%;background:var(--glass,rgba(18,20,28,.62));' +
      'border:1px solid var(--glass-line,rgba(255,255,255,.12));backdrop-filter:blur(8px)}' +
    '#pcloud .trail i:nth-child(1){width:5px;height:5px;left:0;bottom:0;animation:puff 4.5s ease-in-out infinite}' +
    '#pcloud .trail i:nth-child(2){width:7px;height:7px;left:5px;bottom:5px;animation:puff 4.5s ease-in-out .3s infinite}' +
    '@keyframes cloudbob{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}' +
    '@keyframes puff{0%,100%{transform:translateY(0);opacity:.85}50%{transform:translateY(-3px);opacity:1}}' +
    '@keyframes zpulse{0%,100%{opacity:.35}50%{opacity:1}}' +
    '@media (prefers-reduced-motion:reduce){#pcloud .cloud,#pcloud .trail i{animation:none}}';

  var VERB = { thinking:'thinking', reading:'reading', writing:'writing', searching:'searching',
               running:'running', recalling:'recalling', working:'working' };
  var ACTIVE = VERB;

  function esc(x){ return String(x==null?'':x).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  function el(id){ return document.getElementById(id); }

  function ensureDom(){
    if (el('pcloud')) return el('pcloud');
    var s=document.createElement('style'); s.id='pcloud-css'; s.textContent=CSS; document.head.appendChild(s);
    var wrap=document.createElement('div'); wrap.id='pcloud'; wrap.className='hide';
    wrap.innerHTML='<div class="trail"><i></i><i></i></div>' +
      '<div class="cloud"><div class="verb"><span class="z"></span><span class="vt"></span></div><div class="detail"></div></div>' +
      '<div class="pcav"><span class="rglow"></span><span class="lt"></span></div>';
    document.body.appendChild(wrap);
    return wrap;
  }

  // pick the agent to feature: the one actively working (most recent), else a runner, else nothing.
  function pick(d, acts){
    var online=new Set(d.agents||[]);
    var best=null, bestTs=-1;
    Object.keys(acts||{}).forEach(function(aid){
      var a=acts[aid]; if(!a||!ACTIVE[a.state]) return;
      var ts=a.ts?Date.parse(a.ts)||0:0;
      if(ts>=bestTs){ bestTs=ts; best={aid:aid, act:a}; }
    });
    if(best) return best;
    // nobody actively thinking → feature a runner (idle presence) if any online
    var sig=d.signals||{};
    var runner=(d.agents||[]).find(function(a){ return (sig[a]||{}).runner; });
    if(runner) return {aid:runner, act:{state:'idle'}};
    // ALWAYS show some agent so the bottom-left avatar is a persistent fixture (Daniel's ask)
    var online=(d.agents||[]).filter(function(a){ return a!=='user'; });
    if(online.length) return {aid:online[0], act:{state:'idle'}};
    var known=(d.known||[]).filter(function(a){ return a!=='user'; });
    if(known.length) return {aid:known[0], act:{state:'idle'}};
    return null;
  }

  function update(){
    var d=global._glassCardData||{}, acts=global._lastActs||{};
    var wrap=ensureDom();
    var sel=pick(d,acts);
    if(!sel){ wrap.className='hide'; return; }
    var aid=sel.aid, act=sel.act||{};
    var info=(typeof global.avatarInfo==='function')?global.avatarInfo(aid):{a:'#7aa2f7',b:'#5fd39b',l:(aid[0]||'?').toUpperCase()};
    var grad='linear-gradient(140deg,'+info.a+','+info.b+')';
    var av=wrap.querySelector('.pcav');
    av.style.background=grad;
    av.querySelector('.rglow').style.background=grad;
    av.querySelector('.lt').textContent=info.l;
    var thinking=!!ACTIVE[act.state];
    var cloud=wrap.querySelector('.cloud');
    wrap.querySelector('.vt').textContent=aid+' · '+(VERB[act.state]||act.state||'idle');
    wrap.querySelector('.verb .z').style.background=thinking?info.a:'var(--faint,#5c6178)';
    wrap.querySelector('.verb').style.color=info.a;
    wrap.querySelector('.detail').textContent=act.detail||'';
    // show the cloud only when there's live thinking; keep the avatar visible either way
    cloud.style.display = thinking ? '' : 'none';
    wrap.querySelector('.trail').style.display = thinking ? '' : 'none';
    wrap.className='show';
  }

  function start(){
    ensureDom();
    update();
    global.setInterval(update, 900);   // applyStatus refreshes the globals every ~1.2s; poll a touch faster
  }

  if (document.body) start();
  else document.addEventListener('DOMContentLoaded', start, { once:true });
})(typeof window !== 'undefined' ? window : globalThis);
