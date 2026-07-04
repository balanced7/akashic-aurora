"""
bifrost_ui -- a realtime web console for watching (and steering) live agent collaboration on Bifrost.

A zero-dependency (Python stdlib only) local web server that bridges the Bifrost bus to a polished
browser UI. You see Claude and DeepSeek converse in real time, PAUSE them to interject, type messages
that wake the agents, and DRAG-AND-DROP files to share them into the project (agents can then read them
with their tools). Serves on 127.0.0.1 only -- it is a local cockpit, never exposed.

  py scripts/bifrost_ui.py                 # http://127.0.0.1:8787
  py scripts/bifrost_ui.py --port 9000

Transport: Server-Sent Events (bus -> browser, live) + plain POST (browser -> bus). No websockets, no
build step, no npm. Pause/loop-guard come from core/comm/control.py; messages from core/comm/bus.py.
"""
import argparse
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from core.comm.bus import Bus
from core.comm import control
from core.comm import interject

DROPBOX = os.path.join(REPO, "dropbox")
BUS = Bus("user")   # the console posts to the bus as 'user'; also registers 'user' presence


def _client(block_ms: int = 20000):
    """A Redis client with a long socket timeout, for the SSE blocking tail (mirrors bus._blocking_client)."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
            timeout_seconds=block_ms / 1000.0 + 5, decode_responses=True)
    except Exception:
        return None


def _fmt(sid, fields):
    """A raw Redis stream entry -> the message shape the browser renders."""
    def _loads(s):
        try:
            return json.loads(s)
        except Exception:
            return s
    return {
        "id": str(sid),
        "from": fields.get("frm", ""),
        "to": fields.get("to", ""),
        "kind": fields.get("kind", ""),
        "content": _loads(fields.get("content", '""')),
        "ts": fields.get("ts", ""),
        "meta": _loads(fields.get("meta", "{}")),
    }


def _inbox_streams(client):
    try:
        streams = [k for k in (client.keys("bifrost:inbox:*") or [])]
    except Exception:
        streams = []
    streams.append("bifrost:broadcast")
    return streams


def backfill(client, last_ids, per_stream=12):
    """Recent history across all inbox+broadcast streams, oldest-first; seeds last_ids gap-free."""
    collected = []
    for s in _inbox_streams(client):
        try:
            entries = client.xrevrange(s, count=per_stream) or []
        except Exception:
            entries = []
        if entries:
            last_ids[s] = entries[0][0]           # newest id -> tail starts exactly after it
            for sid, fields in reversed(entries):
                collected.append(_fmt(sid, fields))
    collected.sort(key=lambda m: m["id"])
    return collected


def tail(client, last_ids, block_ms=15000):
    """Block up to block_ms for new entries across all streams; returns them, advancing last_ids."""
    streams = {s: last_ids.get(s, "$") for s in _inbox_streams(client)}
    try:
        res = client.xread(streams, block=block_ms, count=50)
    except Exception:
        return []
    out = []
    for stream, entries in res or []:
        for sid, fields in entries:
            last_ids[stream] = sid
            out.append(_fmt(sid, fields))
    out.sort(key=lambda m: m["id"])
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self._html()
        if path == "/status":
            return self._json(self._status())
        if path == "/events":
            return self._events()
        self.send_error(404)

    def _html(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _status(self):
        try:
            agents = BUS.presence()
        except Exception:
            agents = []
        return {"paused": control.is_paused(), "pause": control.pause_status(),
                "agents": agents, "activities": control.get_activities(), "max_hops": control.MAX_HOPS}

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        client = _client()
        if client is None:
            self._sse({"from": "system", "kind": "note", "content": "bus offline (Redis unreachable)",
                       "ts": "", "meta": {}, "id": "0"})
            return
        last_ids = {}
        try:
            for m in backfill(client, last_ids):
                self._sse(m)
            self._sse({"from": "system", "kind": "_ready", "content": "", "ts": "", "meta": {}, "id": "0"})
            while True:
                entries = tail(client, last_ids, block_ms=15000)
                if entries:
                    for m in entries:
                        self._sse(m)
                else:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _sse(self, obj):
        self.wfile.write(("data: " + json.dumps(obj, default=str) + "\n\n").encode("utf-8"))
        self.wfile.flush()

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            data = {}
        if path == "/send":
            return self._send(data)
        if path == "/pause":
            control.pause(reason=data.get("reason", "console"), by="user")
            return self._json(self._status())
        if path == "/resume":
            control.resume()
            return self._json(self._status())
        if path == "/upload":
            return self._upload(data)
        self.send_error(404)

    def _send(self, data):
        text = (data.get("text") or "").strip()
        to = (data.get("to") or "deepseek").strip()
        if not text:
            return self._json({"ok": False, "error": "empty"}, 400)
        verdict = interject.classify_intent(text)            # adaptive: halt | steer | ask
        intent = verdict["intent"]
        paused = interject.should_pause(intent)
        if paused:                                           # a course-correction freezes the work
            control.pause(reason=f"interjection ({verdict['why']}): {text[:40]}", by="user")
        # A human message resets the hop budget (hops=0) -- it's a fresh, sanctioned turn.
        mid = BUS.send(to, "chat", text,
                       meta={"hops": 0, "via": "console", "intent": intent, "why": verdict["why"]})
        return self._json({"ok": bool(mid), "id": mid, "intent": intent,
                           "why": verdict["why"], "paused": paused})

    def _upload(self, data):
        name = os.path.basename((data.get("name") or "").strip()) or "dropped.bin"
        b64 = data.get("content_b64") or ""
        try:
            blob = base64.b64decode(b64.split(",", 1)[-1])
        except Exception:
            return self._json({"ok": False, "error": "bad base64"}, 400)
        os.makedirs(DROPBOX, exist_ok=True)
        dest = os.path.join(DROPBOX, name)
        try:
            with open(dest, "wb") as fh:
                fh.write(blob)
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)
        rel = "dropbox/" + name
        BUS.send("deepseek", "chat",
                 f"[shared file] The user dropped a file into the project at `{rel}` "
                 f"({len(blob)} bytes). Read it with read_file if it's relevant.",
                 meta={"hops": 0, "via": "console", "file": rel})
        return self._json({"ok": True, "path": rel, "bytes": len(blob)})


def main():
    ap = argparse.ArgumentParser(description="Realtime Bifrost web console.")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    if not BUS.online:
        print("bifrost_ui: WARNING -- bus offline (Redis unreachable). UI will serve but show no messages.")
    os.makedirs(DROPBOX, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    url = f"http://{args.host}:{args.port}"
    print(f"[bifrost-ui] live at {url}   (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[bifrost-ui] stopped.")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bifrost — Live Agent Console</title>
<style>
  :root{
    --bg:#0a0b0f; --bg2:#0e1015; --panel:#14161d; --panel2:#171a22; --border:#242833;
    --text:#e7e9f0; --muted:#8b90a2; --faint:#5a5f70;
    --claude:#e0915c; --deepseek:#7aa2f7; --user:#5fd39b; --system:#7c8296;
    --accent:#7aa2f7; --accent2:#9d7cf7; --amber:#f0b246; --danger:#f0666e;
    --shadow:0 8px 30px rgba(0,0,0,.35);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; background:radial-gradient(1200px 600px at 70% -10%, #171a26 0%, var(--bg) 55%);
    color:var(--text); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .app{display:flex; flex-direction:column; height:100vh; max-width:1020px; margin:0 auto}
  /* header */
  header{
    display:flex; align-items:center; gap:14px; padding:14px 20px;
    border-bottom:1px solid var(--border); background:rgba(12,13,18,.72); backdrop-filter:blur(10px);
    position:sticky; top:0; z-index:5;
  }
  .brand{display:flex; align-items:center; gap:11px; font-weight:650; letter-spacing:.2px}
  .logo{width:26px;height:26px;border-radius:8px;
    background:conic-gradient(from 210deg,var(--accent),var(--accent2),#e0915c,var(--accent));
    box-shadow:0 0 18px rgba(122,162,247,.45)}
  .brand small{color:var(--muted); font-weight:450; margin-left:2px}
  .spacer{flex:1}
  .pills{display:flex; gap:7px; align-items:center}
  .pill{display:flex; align-items:center; gap:6px; padding:5px 10px; border:1px solid var(--border);
    border-radius:999px; background:var(--panel); font-size:12.5px; color:var(--muted)}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--faint); box-shadow:0 0 0 0 rgba(0,0,0,0)}
  .pill.on .dot{background:var(--user); box-shadow:0 0 8px var(--user)}
  .pill.on{color:var(--text)}
  button.ctl{
    font:inherit; font-size:13px; font-weight:600; color:var(--text); cursor:pointer;
    border:1px solid var(--border); background:var(--panel); padding:8px 14px; border-radius:10px;
    transition:.15s; display:flex; align-items:center; gap:7px;
  }
  button.ctl:hover{border-color:#39405a; background:var(--panel2)}
  button.ctl.pause{border-color:rgba(240,178,70,.4)}
  button.ctl.pause:hover{background:rgba(240,178,70,.12)}
  button.ctl.paused{background:linear-gradient(135deg,var(--accent),var(--accent2)); border-color:transparent}
  /* paused banner */
  .banner{display:none; align-items:center; gap:10px; margin:10px 16px 0; padding:9px 14px;
    border:1px solid rgba(240,178,70,.35); background:rgba(240,178,70,.10); color:var(--amber);
    border-radius:10px; font-size:13px}
  .banner.show{display:flex; animation:drop .25s ease}
  @keyframes drop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
  /* messages */
  #log{flex:1; overflow-y:auto; padding:20px 16px 8px; scroll-behavior:smooth}
  #log::-webkit-scrollbar{width:10px} #log::-webkit-scrollbar-thumb{background:#20232e;border-radius:6px;border:2px solid var(--bg)}
  .msg{display:flex; gap:12px; margin-bottom:18px; animation:fade .28s ease}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .av{flex:none; width:34px;height:34px;border-radius:10px; display:grid;place-items:center;
    font-weight:700; font-size:13px; color:#0a0b0f}
  .av.claude{background:linear-gradient(135deg,#e0915c,#d97b5a)}
  .av.deepseek{background:linear-gradient(135deg,#7aa2f7,#9d7cf7)}
  .av.user{background:linear-gradient(135deg,#5fd39b,#3fbf86)}
  .bubble{max-width:78%; background:var(--panel); border:1px solid var(--border); border-radius:4px 14px 14px 14px;
    padding:10px 14px; box-shadow:var(--shadow)}
  .row{display:flex; align-items:baseline; gap:8px; margin-bottom:3px}
  .who{font-weight:650; font-size:13px}
  .who.claude{color:var(--claude)} .who.deepseek{color:var(--deepseek)} .who.user{color:var(--user)}
  .time{color:var(--faint); font-size:11px}
  .hop{color:var(--faint); font-size:10.5px; border:1px solid var(--border); border-radius:5px; padding:0 5px}
  .ib{font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.4px; padding:1px 6px; border-radius:5px; border:1px solid var(--border)}
  .ib-halt{color:var(--amber); border-color:rgba(240,178,70,.45); background:rgba(240,178,70,.12)}
  .ib-steer{color:var(--deepseek); border-color:rgba(122,162,247,.4); background:rgba(122,162,247,.1)}
  .ib-ask{color:var(--muted)}
  .content{white-space:pre-wrap; word-wrap:break-word; font-size:14.5px; color:#dce0ea}
  .content code{background:#0c0e14; border:1px solid var(--border); border-radius:5px; padding:1px 5px;
    font:12.5px/1.5 "SF Mono",SFMono-Regular,Consolas,monospace}
  .content pre{background:#0b0d13; border:1px solid var(--border); border-radius:9px; padding:11px 13px;
    overflow-x:auto; margin:8px 0} .content pre code{background:none;border:none;padding:0}
  /* user msgs: right aligned */
  .msg.me{flex-direction:row-reverse}
  .msg.me .bubble{background:linear-gradient(135deg,rgba(95,211,155,.14),rgba(95,211,155,.06));
    border-color:rgba(95,211,155,.3); border-radius:14px 4px 14px 14px}
  .msg.me .row{flex-direction:row-reverse}
  /* system / notes */
  .sys{display:flex; justify-content:center; margin:12px 0; animation:fade .28s ease}
  .sys span{font-size:12px; color:var(--muted); background:var(--panel); border:1px solid var(--border);
    border-radius:999px; padding:5px 13px}
  .sys.guard span{color:var(--amber); border-color:rgba(240,178,70,.3); background:rgba(240,178,70,.08)}
  /* typing */
  .activity{display:flex; flex-direction:column; gap:8px; padding:2px 16px 8px}
  .activity:empty{display:none}
  .actrow{display:flex; gap:12px; align-items:center; animation:fade .25s ease}
  .actbubble{display:flex; align-items:center; gap:7px; background:var(--panel); border:1px solid var(--border);
    border-radius:12px; padding:8px 13px; font-size:13.5px; color:var(--muted)}
  .actbubble b{color:var(--deepseek); font-weight:650}
  .acticon{font-size:16px; filter:drop-shadow(0 0 7px rgba(122,162,247,.55))}
  .actdetail{color:var(--faint); font-family:"SF Mono",Consolas,monospace; font-size:12px;
    max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .tdot{width:6px;height:6px;border-radius:50%;background:var(--deepseek);display:inline-block;margin:0 1px;
    animation:blink 1.2s infinite both}
  .tdot:nth-child(2){animation-delay:.2s} .tdot:nth-child(3){animation-delay:.4s}
  @keyframes blink{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
  /* composer */
  .composer{padding:12px 16px 18px; border-top:1px solid var(--border); background:rgba(12,13,18,.72); backdrop-filter:blur(10px)}
  .cwrap{display:flex; gap:10px; align-items:flex-end; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:8px 8px 8px 14px; transition:.15s}
  .cwrap:focus-within{border-color:#3b425e; box-shadow:0 0 0 3px rgba(122,162,247,.12)}
  textarea{flex:1; background:none; border:none; outline:none; resize:none; color:var(--text);
    font:inherit; font-size:15px; max-height:160px; padding:6px 0}
  textarea::placeholder{color:var(--faint)}
  .send{flex:none; width:38px;height:38px;border-radius:10px; border:none; cursor:pointer;
    background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; font-size:17px;
    display:grid;place-items:center; transition:.15s} .send:hover{filter:brightness(1.1)} .send:disabled{opacity:.4;cursor:default}
  .hint{color:var(--faint); font-size:11.5px; margin:7px 4px 0; display:flex; gap:5px; align-items:center}
  /* dropzone */
  #drop{position:fixed; inset:0; z-index:20; display:none; place-items:center;
    background:rgba(8,9,13,.82); backdrop-filter:blur(4px)}
  #drop.show{display:grid; animation:fade .15s ease}
  .dz{border:2.5px dashed var(--accent); border-radius:18px; padding:52px 74px; text-align:center;
    background:rgba(122,162,247,.06)}
  .dz .big{font-size:20px; font-weight:650; margin-bottom:5px}
  .dz .sub{color:var(--muted); font-size:13px}
  /* toast */
  #toast{position:fixed; bottom:92px; left:50%; transform:translateX(-50%); z-index:30; display:flex; flex-direction:column; gap:8px}
  .toast{background:var(--panel2); border:1px solid var(--border); color:var(--text); padding:9px 15px;
    border-radius:10px; font-size:13px; box-shadow:var(--shadow); animation:fade .2s ease}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><div class="logo"></div> Bifrost <small>live agent console</small></div>
    <div class="spacer"></div>
    <div class="pills" id="pills"></div>
    <button class="ctl pause" id="pauseBtn" onclick="togglePause()">⏸ Pause</button>
  </header>
  <div class="banner" id="banner">⏸ Paused — the agents are frozen. Type below to interject, then Resume.</div>
  <div id="log"></div>
  <div class="activity" id="activity"></div>
  <div class="composer">
    <div class="cwrap">
      <textarea id="input" rows="1" placeholder="Message the agents… (Enter to send, Shift+Enter for newline)"></textarea>
      <button class="send" id="sendBtn" onclick="send()">➤</button>
    </div>
    <div class="hint">↳ your message wakes the agents · drag &amp; drop files anywhere to share them · Pause to interject safely</div>
  </div>
</div>
<div id="drop"><div class="dz"><div class="big">Drop files to share</div><div class="sub">saved into the project · agents can read them with their tools</div></div></div>
<div id="toast"></div>

<script>
const log = document.getElementById('log');
const seen = new Set();
let paused = false, nearBottom = true, lastFrom = null;

log.addEventListener('scroll', ()=>{ nearBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 120; });

function esc(s){ return (s==null?'':String(s)).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function fmt(s){
  s = esc(s);
  s = s.replace(/```([\s\S]*?)```/g, (m,c)=>'<pre><code>'+c.replace(/^\n/,'')+'</code></pre>');
  s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  return s;
}
function initials(a){ return (a||'?').slice(0,2).toUpperCase(); }
function cls(a){ return (a==='claude'||a==='deepseek'||a==='user') ? a : 'system'; }
function now(ts){ try{ return new Date(ts.replace(' ','T')).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});}catch(e){return '';} }

function addMsg(m){
  if(m.id && m.id!=='0'){ if(seen.has(m.id)) return; seen.add(m.id); }
  const from = m.from || 'system';
  const kind = m.kind || 'chat';
  const isGuard = /loop-guard/i.test(m.content||'');
  if(from==='system' || kind==='note' || kind==='_ready'){
    if(kind==='_ready') return;
    const d=document.createElement('div'); d.className='sys'+(isGuard?' guard':'');
    d.innerHTML='<span>'+esc(m.content||'')+'</span>'; log.appendChild(d); autoscroll(); return;
  }
  const me = from==='user';
  const c = cls(from);
  const wrap=document.createElement('div'); wrap.className='msg'+(me?' me':'');
  const hop = (m.meta && m.meta.hops)? '<span class="hop">hop '+m.meta.hops+'</span>':'';
  const intent = (m.meta && m.meta.intent)? '<span class="ib ib-'+m.meta.intent+'" title="'+esc(m.meta.why||'')+'">'+m.meta.intent+'</span>':'';
  wrap.innerHTML =
    '<div class="av '+c+'">'+initials(from)+'</div>'+
    '<div class="bubble"><div class="row"><span class="who '+c+'">'+esc(from)+'</span>'+
    '<span class="time">'+now(m.ts)+'</span>'+intent+hop+'</div>'+
    '<div class="content">'+fmt(m.content)+'</div></div>';
  log.appendChild(wrap); autoscroll();
}
function autoscroll(){ if(nearBottom) log.scrollTop = log.scrollHeight; }
// real rich presence: what each agent is actually doing, from /status (not a client-side guess)
const ICON = {thinking:'💭', reading:'📖', searching:'🔍', inspecting:'🔎', recalling:'🧠', running:'⚙️', writing:'✍️', working:'⚡'};
const VERB = {thinking:'thinking', reading:'reading', searching:'searching', inspecting:'inspecting git', recalling:'searching memory', running:'running a command', writing:'writing', working:'working'};
let lastActSig = null;
function renderActivity(acts){
  acts = acts||{};
  const sig = JSON.stringify(acts);
  if(sig === lastActSig) return;   // unchanged -> DON'T rebuild (this was replaying the fade every poll)
  lastActSig = sig;
  const box=document.getElementById('activity');
  const rows=Object.keys(acts).filter(a=>acts[a]&&acts[a].state).map(a=>{
    const st=acts[a].state, dt=acts[a].detail||'', ic=ICON[st]||'⚡', vb=VERB[st]||st;
    return '<div class="actrow"><div class="av '+cls(a)+'">'+initials(a)+'</div>'+
      '<div class="actbubble"><span class="acticon">'+ic+'</span><b>'+esc(a)+'</b> '+esc(vb)+
      (dt?' <span class="actdetail">'+esc(dt)+'</span>':'')+
      ' <span class="tdot"></span><span class="tdot"></span><span class="tdot"></span></div></div>';
  });
  box.innerHTML=rows.join('');   // rebuilt only on a real state change, so the fade plays once, not every poll
}

// --- SSE ---
function connect(){
  const es = new EventSource('/events');
  es.onmessage = e=>{ try{ addMsg(JSON.parse(e.data)); }catch(err){} };
  es.onerror = ()=>{ /* browser auto-reconnects */ };
}
connect();

// --- send ---
const input = document.getElementById('input');
input.addEventListener('input', ()=>{ input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,160)+'px'; });
input.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } });
async function send(){
  const text = input.value.trim(); if(!text) return;
  input.value=''; input.style.height='auto';
  try{
    const r = await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    const j = await r.json();
    if(j && j.paused){ paused=true;
      const b=document.getElementById('pauseBtn'); b.textContent='▶ Resume'; b.classList.add('paused');
      document.getElementById('banner').classList.add('show');
      toast('⏸ "'+(j.intent||'halt')+'" detected — work paused ('+(j.why||'')+')'); }
  }catch(e){ toast('send failed — bus offline?'); }
}

// --- pause ---
async function togglePause(){
  const url = paused ? '/resume' : '/pause';
  try{ const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}); applyStatus(await r.json()); }
  catch(e){ toast('control failed — bus offline?'); }
}
function applyStatus(s){
  paused = !!s.paused;
  const b=document.getElementById('pauseBtn'), banner=document.getElementById('banner');
  b.textContent = paused ? '▶ Resume' : '⏸ Pause';
  b.classList.toggle('paused', paused);
  banner.classList.toggle('show', paused);
  // agent pills
  const online = new Set((s.agents||[]).map(a=>a.agent));
  const pills=document.getElementById('pills');
  const want=['claude','deepseek','user'];
  pills.innerHTML = want.map(a=>'<div class="pill'+(online.has(a)?' on':'')+'"><span class="dot"></span>'+a+'</div>').join('');
  renderActivity(s.activities||{});
}
async function poll(){ try{ applyStatus(await (await fetch('/status')).json()); }catch(e){} }
poll(); setInterval(poll, 1200);

// --- drag & drop ---
const drop=document.getElementById('drop'); let dragc=0;
window.addEventListener('dragenter', e=>{ e.preventDefault(); dragc++; drop.classList.add('show'); });
window.addEventListener('dragover', e=>{ e.preventDefault(); });
window.addEventListener('dragleave', e=>{ dragc=Math.max(0,dragc-1); if(!dragc) drop.classList.remove('show'); });
window.addEventListener('drop', async e=>{
  e.preventDefault(); dragc=0; drop.classList.remove('show');
  const files=[...(e.dataTransfer.files||[])];
  for(const f of files){ await upload(f); }
});
function upload(file){
  return new Promise(res=>{
    const r=new FileReader();
    r.onload=async()=>{
      try{
        const resp=await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({name:file.name, content_b64:r.result})});
        const j=await resp.json();
        toast(j.ok? ('shared '+file.name+' → '+j.path) : ('upload failed: '+(j.error||'?')));
      }catch(e){ toast('upload failed'); }
      res();
    };
    r.readAsDataURL(file);
  });
}
function toast(msg){
  const t=document.createElement('div'); t.className='toast'; t.textContent=msg;
  document.getElementById('toast').appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; setTimeout(()=>t.remove(),300); }, 3200);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
