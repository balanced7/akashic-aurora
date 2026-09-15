const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const embedded = window.parent !== window;
const pianoOrigin = "http://127.0.0.1:8793";
const pending = new Map();
let cards = [], responses = [], active = null, timer = null, currentFrame = null;
$("open-piano").hidden = embedded;
function notice(text, error=false) { $("notice").textContent=text; $("notice").classList.toggle("error",error); }
function pauseReplay() { currentFrame?.contentWindow?.postMessage({type:"arsenal.replay.pause"},location.origin); }
function playerUrl(clip, response=null) {
  const q = new URLSearchParams({embed:"1",label:response ? "Your answer" : clip.label});
  if(response) q.set("response",response.id);
  else for(const k of ["session","at","seconds"]) q.set(k,clip[k]);
  return `/web/replay.html?${q}`;
}
function showPlayer(card, clip, response) {
  pauseReplay();
  if(currentFrame) currentFrame.remove();
  const frame=document.createElement("iframe");frame.className="player-frame";frame.title=response?"Replay your answer":clip.label;
  frame.allow="autoplay";frame.src=playerUrl(clip,response);card.querySelector(".player-slot").append(frame);currentFrame=frame;
}
function renderAnswers(card) {
  const list=card.querySelector(".answer-list");list.replaceChildren();
  for(const r of responses.filter(r=>r.card_id===card.dataset.id)) {
    const row=document.createElement("div"),button=document.createElement("button");
    button.textContent=`▶ Your answer · ${((r.end_ms-r.start_ms)/1000).toFixed(1)}s`;
    button.addEventListener("click",()=>showPlayer(card,null,r));row.append(button);
    if(r.note){const p=document.createElement("p");p.textContent=r.note;row.append(p);}list.append(row);
  }
}
function render() {
  $("cards").replaceChildren();let group="";
  cards.forEach((c,index)=>{
    if(c.group!==group){const h=document.createElement("h2");h.className="group";h.textContent=c.group;$("cards").append(h);group=c.group;}
    const el=document.createElement("article");el.className="card";el.dataset.id=c.id;
    el.innerHTML=`<h2>${esc(c.title)}</h2><p class="observation">${esc(c.observation)}</p><div class="clips"></div>
      <div class="player-slot"></div><div class="question"><small>A QUESTION FOR YOU</small><p>${esc(c.question)}</p></div>
      <p class="prompt">${esc(c.prompt)}</p><button class="reply">Play an answer</button>
      <textarea class="answer-note" placeholder="Anything you want to tell me? (optional)" aria-label="A note with your musical answer" maxlength="1500" hidden></textarea>
      <div class="capture-status" role="status" aria-live="polite"></div><button class="cancel" hidden>Cancel answer</button><div class="answer-list"></div>`;
    for(const clip of c.clips){const b=document.createElement("button");b.className="clip";b.textContent=`▶ ${clip.label}`;b.addEventListener("click",()=>showPlayer(el,clip));el.querySelector(".clips").append(b);}
    el.querySelector(".reply").addEventListener("click",()=>active ? finish() : start(c,el));
    el.querySelector(".cancel").addEventListener("click",()=>resetCapture("Answer cancelled. Your normal practice log is unchanged."));
    $("cards").append(el);renderAnswers(el);
  });
  $("count").textContent=`${cards.length} cards · ${responses.length} saved answers`;
}
async function mark() {
  if(!embedded) throw new Error("Open these cards beside the piano to play an answer.");
  const id=crypto.randomUUID();
  return new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{pending.delete(id);reject(new Error("The piano did not answer. Refresh the piano page to load Conversation."));},12000);
    pending.set(id,{resolve,reject,timeout});
    parent.postMessage({type:"arsenal.conversation.mark",id},pianoOrigin);
  });
}
window.addEventListener("message",e=>{
  if(e.origin!==pianoOrigin||e.source!==parent||e.data?.type!=="arsenal.conversation.marked")return;
  const p=pending.get(e.data.id);if(!p)return;clearTimeout(p.timeout);pending.delete(e.data.id);
  e.data.error?p.reject(new Error(e.data.error)):p.resolve(e.data.mark);
});
function controls(armed) {
  $("refresh").disabled=armed;
  for(const c of document.querySelectorAll(".card")){
    c.querySelector(".reply").disabled=armed&&c!==active?.el;
    for(const b of c.querySelectorAll(".clips button,.answer-list button"))b.disabled=armed;
  }
}
async function start(card,el) {
  if(!embedded){notice("Open these cards beside the piano, then choose Play an answer.");$("open-piano").focus();return;}
  pauseReplay();el.querySelector(".reply").disabled=true;
  try {
    const anchor=await mark();
    active={card,el,anchor,id:crypto.randomUUID().replaceAll("-",""),started:performance.now(),body:null,saving:false};
    el.querySelector(".reply").textContent="Save my answer";el.querySelector(".reply").disabled=false;
    el.querySelector(".answer-note").hidden=false;el.querySelector(".cancel").hidden=false;controls(true);
    notice("");parent.postMessage({type:"arsenal.conversation.focus"},pianoOrigin);
    timer=setInterval(()=>{
      if(!active)return;const left=Math.max(0,60-Math.floor((performance.now()-active.started)/1000));
      el.querySelector(".capture-status").textContent=`Your turn. Play, then save · ${left}s left in this answer.`;
      if(left===0){clearInterval(timer);timer=null;void finish();}
    },250);
  }catch(error){notice(error.message,true);el.querySelector(".reply").disabled=false;}
}
function resetCapture(message="") {
  clearInterval(timer);timer=null;if(!active)return;
  const el=active.el;el.querySelector(".reply").textContent="Play another answer";el.querySelector(".reply").disabled=false;
  el.querySelector(".answer-note").hidden=true;el.querySelector(".answer-note").value="";el.querySelector(".cancel").hidden=true;
  el.querySelector(".capture-status").textContent=message;active=null;controls(false);
}
async function finish() {
  if(!active||active.saving)return;const a=active;a.saving=true;a.el.querySelector(".reply").disabled=true;
  clearInterval(timer);timer=null;
  try {
    if(!a.body){
      const end=await mark(),tb=end.timebase;
      if(!tb?.session)throw new Error("No notes have been logged yet. Play a phrase, then save again.");
      if(end.page_id!==a.anchor.page_id||(a.anchor.timebase?.session&&a.anchor.timebase.session!==tb.session))throw new Error("The piano take changed during this answer. Cancel and start a new answer.");
      if(end.buffered)throw new Error("Your notes are still uploading. Try Save again in a moment.");
      const from=Math.max(0,Math.round(a.anchor.perf_ms-tb.t0_perf_ms));
      const to=Math.min(Math.round(end.perf_ms-tb.t0_perf_ms),from+60000);
      a.body={id:a.id,card_id:a.card.id,session:tb.session,start_ms:from,end_ms:to,note:a.el.querySelector(".answer-note").value};
    }
    const response=await fetch("/api/conversation/responses",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(a.body),signal:AbortSignal.timeout(12000)});
    const data=await response.json();if(!response.ok){a.body=null;throw new Error(data.error||"Could not save that answer.");}
    responses.unshift(data);resetCapture(`Saved ${data.note_count} notes with this question.`);renderAnswers(a.el);
    $("count").textContent=`${cards.length} cards · ${responses.length} saved answers`;
  }catch(error){a.saving=false;a.el.querySelector(".reply").disabled=false;a.el.querySelector(".capture-status").textContent=error.message;}
}
async function load() {
  pauseReplay();currentFrame=null;
  try{const response=await fetch("/api/conversation",{cache:"no-store",signal:AbortSignal.timeout(10000)});const data=await response.json();
    if(!response.ok)throw new Error(data.error||"Could not load cards.");cards=data.cards;responses=data.responses;render();notice(cards.length?"":"No question cards have been added yet.");
  }catch(error){notice(error.message,true);}
}
$("refresh").addEventListener("click",load);
window.addEventListener("message",e=>{if(e.source===parent&&e.origin===pianoOrigin&&e.data?.type==="arsenal.conversation.pause")pauseReplay();});
load();
