// UI only: reuse the host's controls and APIs so MIDI, saved looks, cues and capture keep one owner.
import { footerStatus } from './midi-hint-model.mjs';
import { handleHtml, loadOrder, makeReorderable, saveOrder } from './studio/reorder.js';
// The camera presets, in the order Daniel keeps them with their grips (studio/reorder.js). The top one is his default: the page
// opens with it and returns to it when he picks an instrument (gallery-camera.js itself starts at 'auto' and keeps nothing).
const CAMERAS=[['auto','Instrument portrait'],['performance','Performance · follow the keys'],['sculpture','Full sculpture'],['detail','Inside the mechanism'],['orbit','Free orbit']];
const CAMERA_ORDER='arsenal.piano.camera-order', INSTRUMENT_ORDER='arsenal.piano.instrument-order', CRYSTAL=['aether','solstice','nocturne'];
const cameraRow=([id,name])=>`<div class="camera-row" data-id="${id}" data-label="${name}">${handleHtml(name)}<label class="camera-choice"><input type="radio" name="studio-camera-mode" value="${id}"><span class="camera-name">${name}</span><span class="camera-default">Default</span></label></div>`;
const DETAILS = {
  aether: ['Crystal collection', 'Aether', 'Prism, platinum & suspended light.', '#a5e2e7', '01'],
  solstice: ['Crystal collection', 'Solstice', 'Opal, champagne brass & living light.', '#edc38f', '02'],
  nocturne: ['Crystal collection', 'Nocturne', 'Smoked crystal beneath an aurora.', '#bba7ed', '03'],
  'glass-piano': ['The instruments', 'Crystal grand', 'A transparent view of every moving part.', '#a5cfd7'],
  'concert-grand': ['The instruments', 'Concert grand', 'A familiar silhouette. An open stage.', '#bdad96'],
  page: ['The instruments', 'Page keys', 'Nothing between you and the notes.', '#acc3cc'],
  keylab88mk3: ['The instruments', 'KeyLab 88 mk3', 'Your controller, rendered in light.', '#c5c0b5'],
  upright: ['The instruments', 'Upright', 'An intimate, vertical instrument.', '#cba580'],
  'suitcase-ep': ['The instruments', 'Suitcase EP', 'Soft edges and electric character.', '#b3c7af'],
  'vintage-synth': ['The instruments', 'Vintage synth', 'Wood, metal and analogue lines.', '#d7ac83'],
  'light-kimi-aurora': ['Light sculptures', 'Aurora Harp', 'Light stretched into an instrument.', '#98d2bf'],
  'light-deepseek-orrery': ['Light sculptures', 'Orrery of Light', 'Notes in a miniature cosmos.', '#cbb9eb'],
  'light-vandor-ornithopter': ['Light sculptures', 'Ornithopter', 'A mechanical creature in flight.', '#d8b987'],
  'light-vandor-abyssal': ['Light sculptures', 'Abyssal', 'An instrument from the deep.', '#8fc9dc'],
};
const symbols = { instruments:'◈', scene:'✧', play:'♬', capture:'◉', practice:'⌘', companion:'◌' };
function silhouette(id) {
  const lid = id === 'solstice' ? '<path d="M58 34Q114 0 166 34M67 28Q116 7 164 23M83 17Q119 6 159 14"/>'
    : id === 'nocturne' ? '<path d="M67 47Q78 0 121 12Q165 11 177 30M78 44Q116 15 159 22"/>'
    : '<path d="M58 49L73 15Q125 9 172 28L122 65Z"/>';
  return `<svg viewBox="0 0 230 120" aria-hidden="true"><ellipse cx="117" cy="102" rx="79" ry="8" fill="currentColor" opacity=".06"/><g fill="none" stroke="currentColor" stroke-width=".9" stroke-linejoin="round">${lid}<path d="M45 57L101 37Q150 36 177 57L140 81L70 83Z"/><path d="M45 57L46 66L71 93L140 91L178 64L177 57M70 83L71 93M140 81L140 91M55 76L56 103M131 92L133 106M165 74L168 95"/><path d="M49 61L74 87L129 85L104 59Z" fill="currentColor" fill-opacity=".13"/>${Array.from({length:14},(_,i)=>`<path d="M${52+i*3.6} 62l23 23" opacity=".48"/>`).join('')}<path d="M80 50L142 64M86 47L147 61M92 44L154 57M99 41L160 53" opacity=".2"/></g></svg>`;
}

export function mountWorkbench(page) {
  const $ = id => document.getElementById(id), app=$('app'), stage=$('stage');
  const ids=['btn-midi','midi-select','btn-demo','btn-916','btn-169','color-select','scheme-select','instrument-select','audio-select','audio-meter','btn-rec','btn-full','nns-select','minor-select','key-select','boundary-select','lean-select','btn-log','log-status','btn-metro','btn-metro-tap','metro-bpm','metro-meter','metro-feel','metro-sound','metro-vol','btn-metro-sample','metro-file','metro-status','btn-cue-voice','cue-volume','btn-cue-lift','cue-midi-select','cue-view-select','cue-status','btn-atmosphere','btn-conversation'];
  const original=Object.fromEntries(ids.map(id=>[id,$(id)]));
  document.body.classList.add('piano-workbench');
  document.querySelector('.brand').innerHTML='<span class="workbench-mark">♮</span><span class="brand-mark">Piano<span class="brand-sub">THE LIGHT STUDIO</span></span>';
  const actions=document.querySelector('.topbar-actions');
  const session=document.createElement('span');session.className='session-light';session.textContent='LIVE STUDIO';
  const pause=document.createElement('button');pause.id='studio-pause';pause.className='btn';pause.textContent='Pause render';pause.setAttribute('aria-pressed','false');
  pause.addEventListener('click',()=>page.setRenderPaused(!page.rendering().paused));
  const focus=document.createElement('button');focus.className='btn focus-button';focus.textContent='Focus';focus.title='Hide the studio controls';focus.setAttribute('aria-pressed','false');
  actions.replaceChildren(session,original['btn-midi'],original['btn-demo'],original['btn-rec'],pause,focus,original['btn-full']);
  original['btn-full'].textContent='⤢';original['btn-full'].setAttribute('aria-label','Fullscreen');
  const workspace=document.createElement('div');workspace.className='studio-workspace';
  workspace.innerHTML=`<nav class="studio-rail" aria-label="Studio sections">${['instruments','scene','play','capture'].map(id=>`<button data-panel="${id}" aria-controls="studio-${id}" aria-expanded="false"><span>${symbols[id]}</span>${id[0].toUpperCase()+id.slice(1)}</button>`).join('')}<div class="rail-spacer"></div><button data-external="practice"><span>${symbols.practice}</span>Practice</button><button data-panel="companion" aria-controls="studio-companion" aria-expanded="false"><span>${symbols.companion}</span>Companion</button><a href="/web/piano-gyre.html" target="_blank" rel="noopener"><span>⌁</span>Studies</a></nav>
    <aside class="studio-inspector" aria-label="Studio inspector" hidden>
      <div class="inspector-heading"><span id="inspector-eyebrow">YOUR COLLECTION</span><button id="inspector-close" aria-label="Close studio panel">×</button></div>
      <section id="studio-instruments" aria-label="Instrument collection" hidden><h1>Find your<br><em>instrument.</em></h1><p class="inspector-intro">A different world for every piece.</p><div id="instrument-cards"></div><div id="instrument-menu"></div><div id="instrument-options"></div><button id="open-looks" class="studio-wide-button">Saved looks <span>↗</span></button></section>
      <section id="studio-scene" aria-label="Scene controls" hidden><h1>Set the<br><em>scene.</em></h1><p class="inspector-intro">Shape the space around your music.</p><div class="studio-field camera-field"><span id="camera-heading">Camera</span><div id="studio-camera-list" class="camera-list" role="radiogroup" aria-labelledby="camera-heading">${loadOrder(CAMERA_ORDER,CAMERAS.map(c=>c[0])).map(id=>cameraRow(CAMERAS.find(c=>c[0]===id))).join('')}</div><p class="camera-hint">The top camera is your default: the page opens with it and returns to it when you pick an instrument. Drag a grip to change the order.</p><select id="studio-camera" hidden tabindex="-1">${CAMERAS.map(([id,name])=>`<option value="${id}">${name}</option>`).join('')}</select></div><button id="studio-home" class="studio-wide-button">Reset view <span>↺</span></button><label class="studio-field" id="studio-canopy-field" hidden>Solstice overhead lights<select id="studio-canopy"><option value="ribbons">Layered LED ribbons</option><option value="fan">Radial fan</option><option value="halo">Halo bands</option><option value="sails">Opal sails</option></select></label><label class="studio-check"><input id="studio-motion" type="checkbox" checked> Ornamental motion</label><div class="control-section" id="scene-look-controls"><h2>Notes & colour</h2></div><div id="environment-mount"></div></section>
      <section id="studio-play" aria-label="Playing controls" hidden><h1>Make it<br><em>your own.</em></h1><p class="inspector-intro">Your keyboard, your harmony, your practice.</p><div class="control-section" id="input-controls"><h2>Your instrument</h2></div><div class="control-section" id="theory-controls"><h2>Harmony & notation</h2></div><div class="control-section" id="metro-controls"><h2>Metronome</h2><p>A click to play to. Its beats are recorded with your notes, which is what lets a score know where the beat really was instead of guessing it from the notes themselves.</p></div><div class="control-section" id="log-controls"><h2>Practice log</h2></div><details class="studio-shortcuts"><summary>Computer keyboard</summary><p>Z–/ and Q–P play notes.<br>Space holds sustain.<br>← → shift the octave.<br>H shows performance details.</p><p>Use Practice for exercises and Saved looks for your visual presets.</p></details><button id="open-practice" class="studio-wide-button">Open practice library <span>↗</span></button></section>
      <section id="studio-capture" aria-label="Capture controls" hidden><h1>Keep the<br><em>moment.</em></h1><p class="inspector-intro">The piano and its light, ready to share.</p><div class="control-section" id="frame-controls"><h2>Canvas framing</h2></div><div class="control-section" id="audio-controls"><h2>Recording sound</h2><p>Choose an audio input to include sound in the recording.</p></div><div class="control-section" id="render-controls"><h2>Rendering</h2><label class="studio-field">Detail<select id="studio-quality"><option value="studio">1080p</option><option value="ultra">1440p</option><option value="cinema">4K</option></select></label><label class="studio-field">Refresh rate<select id="studio-refresh"><option value="native">Monitor native</option><option value="60">60 fps</option></select></label><label class="studio-check" title="When the render is about twice the screen's pixels or more, it is filtered down in smooth steps instead of by the browser, so thin lines and edges stay clean"><input id="studio-smooth" type="checkbox" checked> Smooth preview</label><p>Smooths edges on screen when the render is much larger than its window. Only what you see changes, never the recording.</p><p>Recordings capture at up to 60 fps. Pause render gives the GPU a rest.</p><output id="studio-render-size"></output></div></section>
      <section id="studio-companion" aria-label="Companion controls" hidden><h1>Room for<br><em>another voice.</em></h1><p class="inspector-intro">Play, listen and explore together.</p><div class="control-section" id="companion-controls"><h2>Claude</h2></div></section>
    </aside>`;
  app.insertBefore(workspace,stage);workspace.append(stage);
  const inspector=workspace.querySelector('.studio-inspector');
  const move=(id,parent,field=true)=>{const node=original[id];if(node)$(parent).append(field?(node.closest('.field')||node):node);};
  move('instrument-select','instrument-menu');move('scheme-select','scene-look-controls');move('color-select','scene-look-controls');
  move('midi-select','input-controls');for(const id of ['nns-select','minor-select','key-select','boundary-select','lean-select'])move(id,'theory-controls');
  move('btn-log','log-controls',false);move('log-status','log-controls',false);
  for(const id of ['btn-metro','btn-metro-tap','metro-bpm','metro-meter','metro-feel','metro-sound','metro-vol','btn-metro-sample','metro-status'])move(id,'metro-controls');
  if(original['metro-file'])$('metro-controls').append(original['metro-file']);
  $('frame-controls').append(original['btn-916'].parentElement);
  move('audio-select','audio-controls');$('audio-controls').append(original['audio-meter'].parentElement);
  for(const id of ['btn-cue-voice','cue-volume','btn-cue-lift','cue-midi-select','cue-view-select','cue-status','btn-conversation'])move(id,'companion-controls');
  const atmosphere=$('atmosphere-panel');
  if(atmosphere){$('environment-mount').append(atmosphere);atmosphere.hidden=false;atmosphere.querySelector('.atmos-head button').hidden=true;}
  if(original['btn-atmosphere'])original['btn-atmosphere'].hidden=true;
  // Conversation loads independently; adopt its existing button if its module mounts later.
  const additions=new MutationObserver(()=>{const b=$('btn-conversation');if(b&&b.parentElement===actions)$('companion-controls').append(b);});
  additions.observe(actions,{childList:true});
  let openPanel=null, chooseToken=0;
  function open(id){
    openPanel=openPanel===id?null:id;inspector.hidden=!openPanel;workspace.dataset.panel=openPanel||'';
    for(const s of inspector.querySelectorAll('section'))s.hidden=s.id!==`studio-${openPanel}`;
    for(const b of workspace.querySelectorAll('[data-panel]'))b.setAttribute('aria-expanded',String(b.dataset.panel===openPanel));
    if(atmosphere)atmosphere.hidden=openPanel!=='scene';
    $('inspector-eyebrow').textContent={instruments:'YOUR COLLECTION',scene:'LIGHT & ATMOSPHERE',play:'THE PERFORMANCE',capture:'RECORDING STUDIO',companion:'PLAY TOGETHER'}[openPanel]||'';
    if(openPanel){page.studio?.close();page.jam?.deck?.close();}
  }
  workspace.querySelectorAll('[data-panel]').forEach(b=>b.addEventListener('click',()=>open(b.dataset.panel)));
  $('inspector-close').addEventListener('click',()=>{const previous=openPanel;open(null);workspace.querySelector(`[data-panel="${previous}"]`)?.focus();});
  inspector.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();$('inspector-close').click();}});
  function studio(tab){open(null);page.studio?.open(tab);}
  $('open-looks').addEventListener('click',()=>studio('looks'));
  $('open-practice').addEventListener('click',()=>studio('practice'));
  workspace.querySelector('[data-external="practice"]').addEventListener('click',()=>studio('practice'));
  focus.addEventListener('click',()=>{const on=document.body.classList.toggle('studio-focus');focus.setAttribute('aria-pressed',String(on));focus.textContent=on?'Show controls':'Focus';});
  const caption=document.createElement('div');caption.className='studio-scene-caption';caption.innerHTML='<span id="scene-collection">THE INSTRUMENTS</span><h2 id="scene-title">Piano</h2><p id="scene-description"></p>';stage.append(caption);
  const tip=document.createElement('div');tip.className='studio-stage-tip';tip.textContent='DRAG TO EXPLORE  ↗';stage.append(tip);
  const footer=document.createElement('footer');footer.className='studio-status';footer.innerHTML='<span><i></i><span id="studio-midi-status">Keyboard ready</span></span><span id="studio-harmony">A space for your music.</span><span id="studio-health"></span>';app.append(footer);
  const collection=$('instrument-cards');
  // Card art (assets/instrument-art, made by scripts/piano_card_art.py): a hidden-line wireframe of the live model, tinted by --card-accent
  // through a CSS mask, and a matted render from the same camera that fades in on hover, focus and the chosen card. Both load only as a
  // card nears view in the open panel; an instrument without a wireframe keeps the drawn silhouette(). The wireframe probe fetches in CORS
  // mode, as a CSS mask does, so the mask reuses its download instead of fetching the file again.
  const ART=new URL('../assets/instrument-art/',import.meta.url).href, artUrl=(id,kind)=>`${ART}${encodeURIComponent(id)}.${kind}.webp`;
  const look=b=>{if(b.dataset.look||!b.classList.contains('has-art'))return;b.dataset.look='1';const u=artUrl(b.dataset.instrument,'preview'),img=new Image();img.src=u;img.decode().then(()=>{b.style.setProperty('--look',`url("${u}")`);b.classList.add('look-ready');},()=>{});};
  const reveal=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){
    const b=e.target,box=b.querySelector('.instrument-art'),u=artUrl(b.dataset.instrument,'wire'),img=new Image();reveal.unobserve(b);img.crossOrigin='anonymous';img.src=u;
    img.decode().then(()=>{box.style.setProperty('--wire',`url("${u}")`);box.innerHTML='<span class="art-look"></span><span class="art-wire"></span>';b.classList.add('has-art');if(b.getAttribute('aria-pressed')==='true')look(b);},()=>{box.innerHTML=silhouette(b.dataset.instrument);});
  }},{root:inspector,rootMargin:'0px 0px 360px'});
  // Crystal studies are curated first; all existing instruments stay in the collection below. Each section keeps the order Daniel
  // drags its cards into (one list for all sections, arsenal.piano.instrument-order): a card never leaves its section, and an
  // instrument added later joins the end of its own. The grip sits beside the card, never in it, so it never chooses the instrument.
  const items=page.looks().instruments, sections=new Map();
  for(const item of [...items.filter(i=>CRYSTAL.includes(i.id)),...items.filter(i=>!CRYSTAL.includes(i.id))]){const d=DETAILS[item.id]||['The instruments',item.name,'','#b3cbd0'];if(!sections.has(d[0]))sections.set(d[0],new Map());sections.get(d[0]).set(item.id,[item,d]);}
  const keepInstruments=()=>saveOrder(INSTRUMENT_ORDER,[...collection.querySelectorAll('.instrument-row')].map(r=>r.dataset.id));
  for(const [name,cards] of sections){
    const box=document.createElement('div');box.className='instrument-section';const h=document.createElement('h2');h.textContent=name;box.append(h);collection.append(box);
    for(const id of loadOrder(INSTRUMENT_ORDER,[...cards.keys()])){
      const [item,d]=cards.get(id);
      const row=document.createElement('div');row.className='instrument-row';row.dataset.id=item.id;row.dataset.label=d[1];row.style.setProperty('--card-accent',d[3]);row.innerHTML=handleHtml(d[1]);
      const button=document.createElement('button');button.className=`instrument-card${d[4]?' featured':''}`;button.dataset.instrument=item.id;button.setAttribute('aria-pressed','false');
      button.innerHTML=`<span class="instrument-art" aria-hidden="true"></span><span class="instrument-copy"><span class="instrument-index">${d[4]||'◈'}</span><strong>${d[1]}</strong><small>${d[2]}</small></span><span class="instrument-picked">✓</span>`;
      button.setAttribute('aria-label',`Choose ${d[1]}`);
      row.addEventListener('pointerenter',()=>look(button));button.addEventListener('focus',()=>look(button));
      button.addEventListener('click',async()=>{
        const token=++chooseToken;button.classList.add('loading');
        try {const ok=await page.selectInstrument(item.id);if(ok){page.galleryCamera.setMode(topCamera());paintCamera();page.requestRender();if(innerWidth<1000)open(null);}}
        finally {button.classList.remove('loading');if(token===chooseToken)sync();}
      });row.append(button);box.append(row);reveal.observe(button);
    }
    makeReorderable(box,{item:'.instrument-row',onReorder:keepInstruments});
  }
  // The camera list: a radio per preset (Tab reaches the chosen one, the arrows choose another) and a grip to reorder; reordering
  // never changes the camera in use. #studio-camera stays as a hidden select kept in step both ways, for scripts that set it and
  // dispatch 'change'; REC disables the list as it did the select.
  const cameraList=$('studio-camera-list'), cameraSelect=$('studio-camera');
  const topCamera=()=>cameraList.querySelector('.camera-row')?.dataset.id||'auto';
  function paintCamera(rec){const mode=page.galleryCamera.mode;cameraSelect.value=mode;for(const r of cameraList.querySelectorAll('input'))r.checked=r.value===mode;if(rec===undefined)return;cameraSelect.disabled=rec;cameraList.setAttribute('aria-disabled',String(rec));for(const b of cameraList.querySelectorAll('input,button'))b.disabled=rec;}
  const setCamera=id=>{page.galleryCamera.setMode(id);paintCamera();};
  cameraList.addEventListener('click',e=>{if(e.detail&&e.target.closest('label'))setTimeout(()=>{const a=document.activeElement;if(a?.name==='studio-camera-mode')a.blur();});});  // a pointer pick leaves no focus behind (the label focuses its radio): letter keys stay the note keyboard
  cameraList.addEventListener('change',e=>{if(e.target.name==='studio-camera-mode')setCamera(e.target.value);});
  cameraSelect.addEventListener('change',()=>setCamera(cameraSelect.value));
  makeReorderable(cameraList,{item:'.camera-row',onReorder:ids=>saveOrder(CAMERA_ORDER,ids)});
  page.galleryCamera.setMode(topCamera());
  $('studio-home').addEventListener('click',()=>page.galleryCamera.home());
  $('studio-motion').addEventListener('change',e=>page.setOrnamentalMotion(e.target.checked));
  $('studio-canopy').addEventListener('change',e=>{page.instrument?.setCanopy?.(e.target.value);page.requestRender();});
  $('studio-quality').addEventListener('change',e=>{page.spectacle?.configure({quality:e.target.value});page.requestRender();sync();});
  $('studio-refresh').addEventListener('change',e=>page.setRefreshMode(e.target.value));
  $('studio-smooth').addEventListener('change',e=>{page.setSmoothPreview(e.target.checked);sync();});  // display only: allowed while REC runs
  inspector.addEventListener('change',()=>{if(page.rendering().paused)page.requestRender();});
  for(const b of workspace.querySelectorAll('button'))b.addEventListener('click',e=>{if(e.detail)b.blur();});
  // The mounted instrument's own choices (page.instrumentOptions(): its optionsSpec, e.g. the Crystal grand's glass), one select
  // each, rebuilt only when the instrument or its list of choices changes; page.setInstrumentOption remembers the pick.
  let optionsSig='';
  function syncInstrumentOptions(id,name,rec){
    const opts=page.instrumentOptions?.()||[], box=$('instrument-options');
    const sig=id+'|'+opts.map(o=>`${o.key}:${o.choices.map(c=>`${c.value}=${c.name}`).join(',')}`).join(';');
    if(sig!==optionsSig){
      optionsSig=sig;
      box.replaceChildren(...opts.map(o=>{
        const label=document.createElement('label');label.className='studio-field';label.title=o.title;label.append(o.label);
        const select=document.createElement('select');select.dataset.option=o.key;select.setAttribute('aria-label',`${o.label} of the ${name}`);
        for(const c of o.choices)select.append(new Option(c.name,c.value));
        select.addEventListener('change',()=>{if(!page.setInstrumentOption(o.key,select.value))optionsSig='';select.blur();sync();});
        label.append(select);return label;
      }));
    }
    for(const select of box.querySelectorAll('select')){
      const o=opts.find(x=>x.key===select.dataset.option);
      if(o&&document.activeElement!==select)select.value=o.value;
      select.disabled=rec!=='idle';
    }
  }
  let lastInstrument='';
  function sync(){
    const looks=page.looks(), id=looks.instrument||'page', d=DETAILS[id]||DETAILS.page, s=page.stats(), render=page.rendering();
    if(id!==lastInstrument){
      lastInstrument=id;document.documentElement.style.setProperty('--studio-accent',d[3]);
      $('scene-title').textContent=d[1];$('scene-collection').textContent=d[0].toUpperCase();$('scene-description').textContent=d[2];
      for(const b of collection.querySelectorAll('[data-instrument]')){const on=b.dataset.instrument===id;b.setAttribute('aria-pressed',String(on));if(on)look(b);}
    }
    syncInstrumentOptions(id,d[1],s.rec);
    $('studio-canopy-field').hidden=id!=='solstice';if(id==='solstice')$('studio-canopy').value=page.instrument?.canopy||'ribbons';
    paintCamera(s.rec!=='idle');
    $('studio-quality').value=page.spectacle?.settings.quality||'ultra';$('studio-refresh').value=render.refresh;
    $('studio-quality').disabled=s.rec!=='idle';$('studio-canopy').disabled=s.rec!=='idle';
    for(const b of collection.querySelectorAll('button'))b.disabled=s.rec!=='idle';
    pause.disabled=s.rec!=='idle';pause.textContent=render.paused?'Resume render':'Pause render';pause.setAttribute('aria-pressed',String(render.paused));
    const smooth=render.smoothPreview;if(smooth)$('studio-smooth').checked=smooth.on;
    $('studio-render-size').textContent=`${render.width} × ${render.height} pixels · 4× MSAA${smooth?.active?` · preview smoothed ${smooth.ratio}× down`:''}`;
    $('studio-health').textContent=`${render.width} × ${render.height} · ${render.paused?'PAUSED':`${s.fps} FPS`}`;
    $('studio-harmony').textContent=s.chord?`${s.chord}${s.pedal?' · sustain':''}`:s.demo?'Generative performance':'A space for your music.';
    const midi=original['midi-select'];$('studio-midi-status').textContent=midi.value?midi.selectedOptions[0]?.textContent:footerStatus({boundName:null,remembered:page.midiRemembered?.()??null,visible:[...midi.options].map(o=>o.textContent)});  // names a missing remembered keyboard instead of calling it ready
    stage.dataset.instrument=id;stage.dataset.camera=page.galleryCamera.active()?'sculpture':'performance';
    stage.dataset.sounding=s.sounding.length;stage.dataset.pedal=String(s.pedal);stage.dataset.paused=String(render.paused);
    tip.textContent=render.paused?'RENDER PAUSED':page.galleryCamera.active()?'DRAG TO EXPLORE  ↗':'PLAY THE KEYS  ↗';
  }
  const timer=setInterval(()=>{if(!document.hidden)sync();},500);
  addEventListener('pagehide',()=>{clearInterval(timer);additions.disconnect();reveal.disconnect();},{once:true});
  // No synthetic notes or audio are started by the interface.
  open(innerWidth>=1000?'instruments':null);sync();
  return {sync};
}
