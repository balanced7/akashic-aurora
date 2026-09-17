// Conversation is outside the recorded canvas. Only this piano's own clock/log can mark an answer.
const origin="http://127.0.0.1:8796";
const button=document.createElement("button");button.type="button";button.className="btn";button.id="btn-conversation";
button.textContent="Conversation";button.setAttribute("aria-expanded","false");
document.querySelector(".topbar-actions")?.append(button);
const dock=document.createElement("aside");dock.id="conversation-dock";dock.hidden=true;dock.setAttribute("aria-label","Piano conversation");
dock.style.cssText="position:fixed;right:12px;top:76px;bottom:12px;width:min(410px,calc(100vw - 24px));z-index:90;background:#111620;border:1px solid #52647a;border-radius:13px;box-shadow:0 20px 70px #0009;overflow:hidden";
const close=document.createElement("button");close.textContent="Close conversation";close.className="btn";
close.style.cssText="display:block;width:100%;height:36px;border-radius:0;background:#263548;color:#e6f3ec";
const frame=document.createElement("iframe");frame.title="Conversation cards";frame.allow="autoplay";
frame.style.cssText="width:100%;height:calc(100% - 36px);border:0;display:block";
dock.append(close,frame);document.body.append(dock);
function fitDock(){const bottom=document.querySelector(".topbar")?.getBoundingClientRect().bottom||0;dock.style.top=`${Math.max(12,Math.min(innerHeight-240,bottom+8))}px`;}
fitDock();window.addEventListener("resize",fitDock);
if(typeof ResizeObserver!=="undefined")new ResizeObserver(fitDock).observe(document.querySelector(".topbar"));
function show(on){if(on){window.__piano?.jam?.deck?.close();window.__piano?.studio?.close();}dock.hidden=!on;button.setAttribute("aria-expanded",String(on));if(on&&!frame.getAttribute("src"))frame.src=origin+"/web/conversation.html";
  if(!on)frame.contentWindow?.postMessage({type:"arsenal.conversation.pause"},origin);}
// The deck, the Studio and this dock use the same edge of the stage. Opening one gives it that space;
// closing the deck does not stop its musical transport.
function watchDrawer(sel){const drawer=document.querySelector(sel);if(!drawer)return false;
  new MutationObserver(()=>{if(drawer.dataset.open==='true'&&!dock.hidden)show(false);}).observe(drawer,{attributes:true,attributeFilter:['data-open']});return true;}
for(const sel of ['#deck','#studio'])if(!watchDrawer(sel)){const mounting=new MutationObserver(()=>{if(watchDrawer(sel))mounting.disconnect();});mounting.observe(document.body,{childList:true,subtree:true});}
button.addEventListener("click",()=>show(dock.hidden));close.addEventListener("click",()=>show(false));
window.addEventListener("message",async e=>{
  if(e.origin!==origin||e.source!==frame.contentWindow)return;
  if(e.data?.type==="arsenal.conversation.focus"){window.focus();document.activeElement?.blur();return;}
  if(e.data?.type!=="arsenal.conversation.mark")return;
  const reply={type:"arsenal.conversation.marked",id:e.data.id};
  try{if(!window.__piano?.conversation)throw new Error("The piano is still loading. Try again in a moment.");reply.mark=await window.__piano.conversation.mark();}
  catch(error){reply.error=error.message;}
  frame.contentWindow?.postMessage(reply,origin);
});
if(new URLSearchParams(location.search).get("conversation")==="1")show(true);
