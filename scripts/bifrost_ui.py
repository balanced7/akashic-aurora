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
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from core.comm.bus import Bus
from core.comm import control
from core.comm import promoter
from core.comm.launcher import get_launcher
from core.trust import registry

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
        if path == "/launcher/status":
            return self._json(get_launcher().registry())
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
        # Per-agent awareness: pending nudge (hard) + queued steer (soft) + whether a runner holds the
        # singleton lock. Lets the roster show, at a glance, who's being signalled and who's actually live.
        signals = {}
        try:
            from core.comm import nudge, runner_lock
            for a in agents:
                aid = a.get("agent")
                if not aid:
                    continue
                signals[aid] = {"nudged": nudge.is_nudged(aid),
                                "steer_pending": nudge.steer_pending(aid),
                                "runner": bool(runner_lock.holder(aid))}
        except Exception:
            signals = {}
        # Known: ALL registered agents (always visible, even offline) for the wake-from-UI fix.
        known = []
        try:
            known = sorted([g.agent_id for g in registry.grants()])
            if "claude" not in known:
                known.append("claude")
                known.sort()
        except Exception:
            pass
        return {"paused": control.is_paused(), "pause": control.pause_status(),
                "agents": agents, "known": known, "activities": control.get_activities(),
                "signals": signals, "max_hops": control.MAX_HOPS}

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
            reason = data.get("reason", "console")
            control.pause(reason=reason, by="user")
            promoter.promote_control("pause", reason=reason, by="user")
            return self._json(self._status())
        if path == "/resume":
            control.resume()
            promoter.promote_control("resume", by="user")
            return self._json(self._status())
        if path == "/upload":
            return self._upload(data)
        if path == "/launcher/launch":
            tag = data.get("agent_id") or data.get("tag") or ""
            prompt = data.get("prompt") or ""
            result = get_launcher().launch(tag, prompt=prompt)
            return self._json(result)
        if path == "/launcher/kill":
            tag = data.get("agent_id") or data.get("tag") or ""
            result = get_launcher().kill(tag)
            return self._json(result)
        if path == "/reload":
            self._json({"ok": True, "reloading": True})
            threading.Thread(target=lambda: (time.sleep(0.3), _reexec()), daemon=True).start()
            return
        self.send_error(404)

    def _send(self, data):
        """Deliver an operator message at an EXPLICIT fidelity (chosen in the UI, not guessed from
        keywords -- that keyword-guessing false-tripped 'halt' on ordinary prose). Fidelities:
          chat/inform : plain delivery; the agent adopts it at its next turn. Never pauses.
          steer       : queue a fact the target folds into its CURRENT task (soft). Targeted only.
          interrupt   : hard barge-in -- set the target's nudge flag + kind=nudge. Targeted only.
        Global HALT is a separate, explicit control (the Pause button / /pause)."""
        text = (data.get("text") or "").strip()
        to = (data.get("to") or "all").strip().lower()       # default: reach every agent
        fidelity = (data.get("fidelity") or "chat").strip().lower()
        if not text:
            return self._json({"ok": False, "error": "empty"}, 400)
        broadcast = to in ("all", "both", "*", "")
        meta = {"hops": 0, "via": "console", "intent": fidelity}
        from core.comm import nudge

        # Targeted fidelity signals need one recipient; if broadcast, they degrade to plain delivery.
        if fidelity in ("interrupt", "steer") and not broadcast:
            if fidelity == "interrupt":
                nudge.nudge(to, by="user", reason=text[:80])
                mid = BUS.send(to, "nudge", text, meta=meta)
            else:
                nudge.steer_push(to, "user", text)
                mid = BUS.send(to, "steer", text, meta={**meta, "display_only": True})
            return self._json({"ok": bool(mid), "id": mid, "intent": fidelity, "to": to, "paused": False})

        kind = "inform" if fidelity == "inform" else "chat"
        mid = BUS.broadcast(kind, text, meta=meta) if broadcast else BUS.send(to, kind, text, meta=meta)
        return self._json({"ok": bool(mid), "id": mid, "intent": fidelity, "to": to, "paused": False})

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
        promoter.promote_drop(rel, len(blob), by="user")     # durable provenance: what the human shared
        return self._json({"ok": True, "path": rel, "bytes": len(blob)})


def _reexec():
    """Replace this process with a fresh one (same args/port) so edited source is served. SSE clients
    auto-reconnect; the browser just needs a refresh (the Reload button does it)."""
    try:
        sys.stdout.flush(); sys.stderr.flush()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _reload_watcher():
    """Self-reload: when this UI's own source changes on disk (an agent edited the console), re-exec so
    the new code is served -- no human in the restart loop. Debounced so we never reload mid-write."""
    try:
        last = os.path.getmtime(__file__)
    except Exception:
        return
    while True:
        time.sleep(2)
        try:
            m = os.path.getmtime(__file__)
        except Exception:
            continue
        if m != last:
            time.sleep(1.0)                 # debounce: let the writer finish flushing
            print("[bifrost-ui] source changed on disk -> reloading")
            _reexec()


def main():
    ap = argparse.ArgumentParser(description="Realtime Bifrost web console.")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--auto-reload", action="store_true",
                    help="re-exec the server when its source changes on disk (dev only; OFF by default so a "
                         "write-enabled agent editing the UI can't silently restart it under you). Use the "
                         "header ↻ Reload button for an explicit, safe reload instead.")
    args = ap.parse_args()
    if not BUS.online:
        print("bifrost_ui: WARNING -- bus offline (Redis unreachable). UI will serve but show no messages.")
    os.makedirs(DROPBOX, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    if args.auto_reload:                                             # opt-in: surprise-restart safe by default
        threading.Thread(target=_reload_watcher, daemon=True).start()
    url = f"http://{args.host}:{args.port}"
    print(f"[bifrost-ui] live at {url}   ({'auto-reload ON' if args.auto_reload else 'manual reload button'} - Ctrl-C to stop)")
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
    --fleet:#f472b6;
    --shadow:0 8px 30px rgba(0,0,0,.35);
    /* aurora glow tints (per-theme tunable) + glass */
    --glow1:rgba(240,145,92,.16); --glow2:rgba(122,162,247,.20); --glow3:rgba(72,230,191,.14); --glow4:rgba(157,124,247,.16);
    --glass:rgba(18,20,28,.55); --glass-line:rgba(255,255,255,.08); --glass-hi:rgba(255,255,255,.06);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; position:relative;
    background:
      radial-gradient(1100px 700px at 8% -8%, var(--glow1), transparent 60%),
      radial-gradient(1000px 720px at 92% 6%, var(--glow2), transparent 60%),
      radial-gradient(1200px 800px at 60% 108%, var(--glow3), transparent 62%),
      radial-gradient(900px 900px at 28% 92%, var(--glow4), transparent 60%),
      var(--bg);
    color:var(--text); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  /* STATIC atmosphere: an animated blur(70px) repainted the whole viewport every frame -> typing/scroll jank */
  body::before{content:""; position:fixed; inset:-25%; z-index:-1; pointer-events:none; opacity:.6;
    background:conic-gradient(from 200deg at 42% 40%, var(--glow2),var(--glow3),var(--glow1),var(--glow4),var(--glow2));
    filter:blur(60px)}
  body::after{content:""; position:fixed; inset:0; z-index:-1; pointer-events:none; opacity:.3;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/></svg>")}
  .app{display:flex; flex-direction:column; height:100vh; max-width:1020px; margin:0 auto; position:relative; z-index:1}
  /* header */
  header{
    display:flex; align-items:center; gap:14px; padding:14px 20px;
    border-bottom:1px solid var(--glass-line); background:var(--glass);
    backdrop-filter:blur(12px) saturate(1.2); -webkit-backdrop-filter:blur(12px) saturate(1.2);
    box-shadow:0 1px 0 var(--glass-hi) inset; position:sticky; top:0; z-index:5;
  }
  .brand{display:flex; align-items:center; gap:11px; font-weight:650; letter-spacing:.2px}
  .logo{width:26px;height:26px;border-radius:8px;
    background:conic-gradient(from 210deg,var(--accent),var(--accent2),#e0915c,var(--accent));
    box-shadow:0 0 18px rgba(122,162,247,.45)}
  .brand small{color:var(--muted); font-weight:450; margin-left:2px}
  .spacer{flex:1}
  .pills{display:flex; gap:7px; align-items:center}
  .pill{display:flex; align-items:center; gap:6px; padding:5px 10px; border:1px solid var(--border);
    border-radius:999px; background:var(--panel); font-size:12.5px; color:var(--muted); cursor:pointer}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--faint); box-shadow:0 0 0 0 rgba(0,0,0,0)}
  .pill.on .dot{background:var(--user); box-shadow:0 0 8px var(--user)}
  .pill.on{color:var(--text)}
  .pill.off{opacity:.55}
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
  .ib-interrupt{color:var(--danger); border-color:rgba(240,102,110,.5); background:rgba(240,102,110,.12)}
  .ib-inform{color:var(--user); border-color:rgba(95,211,155,.4); background:rgba(95,211,155,.1)}
  .ib-ask{color:var(--muted)}
  /* steer-pending / nudged markers on roster pills */
  .pill .sig{font-size:10px; font-weight:700; padding:0 5px; border-radius:6px; margin-left:3px}
  .pill .sig.steer{color:var(--deepseek); background:rgba(122,162,247,.16)}
  .pill .sig.nudge{color:var(--danger); background:rgba(240,102,110,.16)}
  .fidsel{align-self:center; background:var(--bg2); border:1px solid var(--border); color:var(--muted);
    border-radius:9px; padding:7px 8px; font:inherit; font-size:12.5px; outline:none; cursor:pointer}
  .fidsel:hover{border-color:#39405a}
  .fidsel.interrupt{color:var(--danger); border-color:rgba(240,102,110,.4)}
  .fidsel.steer{color:var(--deepseek); border-color:rgba(122,162,247,.4)}
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
  /* live trace: DeepSeek's tool calls + thinking, streamed as compact dim lines */
  .traceline{display:flex; gap:8px; align-items:baseline; margin:1px 0 1px 46px; font-size:12px;
    font-family:"SF Mono",SFMono-Regular,Consolas,monospace; animation:fade .18s ease}
  .traceline .trav{font-weight:600; opacity:.75; flex:none}
  .traceline .trav.deepseek{color:var(--deepseek)} .traceline .trav.claude{color:var(--claude)}
  .traceline .trav.system{color:var(--system)}
  .traceline .trat{color:var(--faint); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
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
  .composer{padding:12px 16px 18px; border-top:1px solid var(--glass-line); background:rgba(14,16,22,.9); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); position:relative}
  .cwrap{display:flex; gap:10px; align-items:flex-end; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:8px 8px 8px 14px; transition:.15s}
  .cwrap:focus-within{border-color:#3b425e; box-shadow:0 0 0 3px rgba(122,162,247,.12)}
  textarea{flex:1; background:none; border:none; outline:none; resize:none; color:var(--text);
    font:inherit; font-size:15px; max-height:160px; padding:6px 0}
  textarea::placeholder{color:var(--faint)}
  .target{align-self:center; background:var(--bg2); border:1px solid var(--border); color:var(--muted);
    border-radius:9px; padding:7px 8px; font:inherit; font-size:12.5px; outline:none; cursor:pointer}
  .target:hover{border-color:#39405a}
  .send{flex:none; width:38px;height:38px;border-radius:10px; border:none; cursor:pointer;
    background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; font-size:17px;
    display:grid;place-items:center; transition:.15s} .send:hover{filter:brightness(1.1)} .send:disabled{opacity:.4;cursor:default}
  .hint{color:var(--faint); font-size:11.5px; margin:7px 4px 0; display:flex; gap:5px; align-items:center}
  /* --- Slice 2: centered fidelity ladder + animated recipient selector --- */
  @property --spin{syntax:'<angle>'; inherits:false; initial-value:0deg}
  @keyframes ladderSweep{to{--spin:360deg}}
  @keyframes rpulse{0%{box-shadow:0 0 0 0 rgba(122,162,247,.4)}100%{box-shadow:0 0 0 10px rgba(122,162,247,0)}}
  .ladder{display:flex; justify-content:center; margin:0 0 10px}
  .ladder .seg{font:inherit; font-size:12.5px; color:var(--muted); background:var(--bg2); border:1px solid var(--border);
    border-right:none; padding:6px 16px; cursor:pointer; transition:.15s}
  .ladder .seg:first-child{border-radius:10px 0 0 10px}
  .ladder .seg:last-child{border-radius:0 10px 10px 0; border-right:1px solid var(--border)}
  .ladder .seg:hover{color:var(--text)}
  .ladder .seg.on{color:var(--text); background:var(--panel2); position:relative; z-index:1}
  .ladder .seg.on::after{content:""; position:absolute; inset:-1px; border-radius:inherit; padding:1px; pointer-events:none;
    background:conic-gradient(from var(--spin), var(--accent),var(--user),var(--claude),var(--accent2),var(--accent));
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0); -webkit-mask-composite:xor;
    mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0); mask-composite:exclude; animation:ladderSweep 4s linear infinite}
  @media (prefers-reduced-motion:reduce){.ladder .seg.on::after{animation:none}}
  .recipient{align-self:center; flex:none; display:flex; align-items:center; gap:9px; height:40px; padding:0 11px 0 7px;
    border:1px solid var(--border); border-radius:11px; background:var(--bg2); cursor:pointer; transition:border-color .15s,background .15s}
  .recipient:hover{border-color:var(--accent); background:rgba(122,162,247,.06)}
  .recipient.pulse{animation:rpulse .5s cubic-bezier(.2,.9,.3,1.2)}
  .rstack{display:flex; align-items:center; height:28px}
  .rstack .cav{width:28px;height:28px;border-radius:8px; margin-left:-11px; box-shadow:0 0 0 2px var(--panel);
    display:grid;place-items:center; font-size:11px;font-weight:700; color:#0a0b0f; will-change:transform,opacity}
  .rstack .cav:first-child{margin-left:0}
  .rlabel{display:flex; flex-direction:column; line-height:1.2; min-width:46px}
  .rlabel b{font-size:12px; color:var(--text); font-weight:600; white-space:nowrap}
  .rlabel .cue{font-size:9.5px; color:var(--faint); white-space:nowrap}
  .roster-pop{display:none; position:absolute; bottom:66px; left:16px; z-index:20; background:var(--panel);
    border:1px solid var(--border); border-radius:12px; padding:7px; box-shadow:var(--shadow); min-width:186px}
  .roster-pop.show{display:block; animation:drop .16s ease}
  .roster-pop .ri{display:flex; align-items:center; gap:9px; padding:7px 9px; border-radius:8px; cursor:pointer; font-size:13px; color:var(--text)}
  .roster-pop .ri:hover{background:var(--panel2)}
  .roster-pop .ri.sel{background:rgba(122,162,247,.12)}
  .roster-pop .ri .cav{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:10px;font-weight:700;color:#0a0b0f}
  .roster-pop .chk{margin-left:auto; color:var(--accent); font-size:13px; opacity:0}
  .roster-pop .ri.sel .chk{opacity:1}
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
  /* launcher panel */
  #lnchr{display:none; margin:0 16px 10px; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); animation:drop .25s ease}
  #lnchr.show{display:block}
  .lrow{display:flex; align-items:center; gap:10px; padding:8px 6px; border-bottom:1px solid rgba(255,255,255,.04)}
  .lrow:last-child{border-bottom:none}
  .ltag{font-weight:650; font-size:13px; color:var(--text); min-width:120px}
  .ldesc{flex:1; font-size:12.5px; color:var(--muted)}
  .lst{font-size:11.5px; font-weight:600; padding:2px 8px; border-radius:6px; white-space:nowrap}
  .lst.running{color:#5fd39b; background:rgba(95,211,155,.14)}
  .lst.exited{color:var(--muted); background:rgba(139,144,162,.1)}
  .lst.crashed,.lst.error{color:var(--danger); background:rgba(240,102,110,.12)}
  .lst.killed{color:var(--amber); background:rgba(240,178,70,.12)}
  .lst.token_exhausted{color:var(--amber); background:rgba(240,178,70,.14)}
  .lst.never_launched{color:var(--faint); background:rgba(90,95,112,.08)}
  .lact{display:flex; gap:6px}
  .lact button{font:inherit; font-size:11.5px; font-weight:600; padding:5px 11px; border-radius:7px;
    cursor:pointer; border:1px solid var(--border); background:var(--panel2); color:var(--text); transition:.15s}
  .lact button:hover{border-color:#39405a; background:#1c1f2a}
  .lact .lgo{background:linear-gradient(135deg,var(--accent),var(--accent2)); border-color:transparent; color:#fff}
  .lact .lgo:hover{filter:brightness(1.1)}
  .lact .lgo:disabled{opacity:.4; cursor:default; filter:none}
  .lact .lkill{border-color:rgba(240,102,110,.35); color:var(--danger)}
  .lact .lkill:hover{background:rgba(240,102,110,.12)}
  .lact .lkill:disabled{opacity:.3; cursor:default}
  .lreason{font-size:11px; color:var(--faint); margin-left:6px}
  button.lctl{
    font:inherit; font-size:12.5px; font-weight:600; color:var(--muted); cursor:pointer;
    border:1px solid var(--border); background:var(--panel); padding:6px 11px; border-radius:9px;
    transition:.15s; display:flex; align-items:center; gap:6px;
  }
  button.lctl:hover{border-color:#39405a; color:var(--text)}
  button.lctl.active{color:var(--accent); border-color:rgba(122,162,247,.35)}
  /* launch loading spinner */
  @keyframes lspin{to{transform:rotate(360deg)}}
  .lspinner{width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--accent);
    border-radius:50%;animation:lspin .7s linear infinite;display:none}
  .lspinner.show{display:inline-block}

  /* === V2 PRESENTATION REGISTRY === */
  /* settings panel */
  #setp{display:none; margin:0 16px 10px; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); animation:drop .25s ease}
  #setp.show{display:block}
  .setrow{display:flex; align-items:center; gap:12px; padding:9px 6px; border-bottom:1px solid rgba(255,255,255,.04)}
  .setrow:last-child{border-bottom:none}
  .setrow label{font-weight:600; font-size:13px; color:var(--text); min-width:70px}
  .setrow select{flex:1; background:var(--bg2); border:1px solid var(--border); color:var(--text);
    border-radius:8px; padding:7px 10px; font:inherit; font-size:13px; outline:none; cursor:pointer}
  .setrow select:hover{border-color:#39405a}
  .setrow .setdesc{font-size:11.5px; color:var(--faint); min-width:80px; text-align:right}
  /* glass-card tiles (strangler: lives alongside pills, shown when glass-card variant active) */
  #tiles{display:none; flex-wrap:wrap; gap:10px; padding:0}
  #tiles.show{display:flex}
  .gcard{position:relative; background:rgba(20,22,29,.7); backdrop-filter:blur(12px);
    border:1px solid var(--border); border-radius:14px; padding:10px 14px; min-width:125px;
    cursor:pointer; transition:.18s; display:flex; align-items:center; gap:10px; box-shadow:var(--shadow)}
  .gcard:hover{border-color:#39405a; background:rgba(23,26,34,.82)}
  .gcard.online{border-color:rgba(95,211,155,.22)}
  .gcard.online .gdot{background:var(--user); box-shadow:0 0 10px var(--user)}
  .gcard.nudged{border-color:rgba(240,102,110,.4); animation:gpulse 1.5s infinite}
  .gcard.steered{border-color:rgba(122,162,247,.32)}
  @keyframes gpulse{0%,100%{box-shadow:0 0 0 0 rgba(240,102,110,.3)}50%{box-shadow:0 0 14px 4px rgba(240,102,110,.18)}}
  .gdot{width:8px;height:8px;border-radius:50%;background:var(--faint); flex:none}
  .gname{font-weight:650; font-size:13px; color:var(--text)}
  .gbadge{font-size:9.5px; font-weight:700; padding:1px 6px; border-radius:5px; text-transform:uppercase; letter-spacing:.3px}
  .gbadge.admin{color:var(--accent); background:rgba(122,162,247,.15); border:1px solid rgba(122,162,247,.25)}
  .gcard .gactions{display:none; position:absolute; top:calc(100% + 2px); left:0; right:0; z-index:10;
    background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:8px;
    box-shadow:var(--shadow); flex-direction:column; gap:5px}
  .gcard.expanded .gactions{display:flex}
  .gactions button{font:inherit; font-size:11.5px; padding:5px 9px; border-radius:7px;
    cursor:pointer; border:1px solid var(--border); background:var(--panel); color:var(--text); transition:.15s; text-align:left}
  .gactions button:hover{border-color:#39405a}
  .gactions .gact-spawn{background:rgba(122,162,247,.15); border-color:rgba(122,162,247,.3); color:var(--accent)}
  .gactions .gact-kill{color:var(--danger); border-color:rgba(240,102,110,.25)}
  /* compact glass-card: icon-only */
  #tiles.compact .gcard{min-width:auto; padding:8px 10px}
  #tiles.compact .gcard .gname,#tiles.compact .gcard .gbadge,#tiles.compact .gcard .sig{display:none}
  #tiles.compact .gcard .gdot{width:10px;height:10px}

  /* === iso-cube tile === */
  .icube-row{display:flex; gap:20px; flex-wrap:wrap}
  .icube{position:relative; width:90px; height:90px; cursor:pointer; perspective:600px; flex:none}
  .icube-inner{position:relative; width:100%; height:100%; transform:rotateX(-25deg)rotateY(-35deg); transform-style:preserve-3d; transition:transform .35s ease}
  .icube:hover .icube-inner,.icube.sel .icube-inner{transform:rotateX(-25deg)rotateY(-35deg) translateZ(12px)}
  .icube-face{position:absolute; width:90px; height:90px; border:2px solid var(--border); border-radius:12px;
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; backface-visibility:hidden}
  .icube-top{transform:rotateX(90deg)translateZ(45px); background:rgba(20,22,29,.76)}
  .icube-front{transform:translateZ(45px); background:rgba(20,22,29,.82)}
  .icube-right{transform:rotateY(90deg)translateZ(45px); background:rgba(16,18,24,.78)}
  .icube .iavid{display:none}
  .icube .iav{width:28px;height:28px;border-radius:7px; display:grid;place-items:center;
    font-weight:700; font-size:11px; color:#0a0b0f}
  .iav.claude{background:linear-gradient(135deg,#e0915c,#d97b5a)}
  .iav.deepseek{background:linear-gradient(135deg,#7aa2f7,#9d7cf7)}
  .iav.user{background:linear-gradient(135deg,#5fd39b,#3fbf86)}
  .icube .iname{font-size:11px;font-weight:650;color:var(--text)}
  .icube.online .icube-front{border-color:rgba(95,211,155,.4); box-shadow:0 0 16px rgba(95,211,155,.18)}
  .icube.nudged .icube-front{border-color:rgba(240,102,110,.55); animation:gpulse 1.5s infinite}
  .icube .igact{display:none; position:absolute; top:calc(100% + 4px); left:-10px; z-index:10;
    background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:7px; box-shadow:var(--shadow);
    flex-direction:column; gap:4px; min-width:110px}
  .icube.expanded .igact{display:flex}
  .igact button{font:inherit; font-size:11px; padding:5px 8px; border-radius:7px; cursor:pointer;
    border:1px solid var(--border); background:var(--panel); color:var(--text); transition:.15s; text-align:left}
  .igact button:hover{border-color:#39405a}
  .igact .ig-spawn{background:rgba(122,162,247,.15); border-color:rgba(122,162,247,.3); color:var(--accent)}
  .igact .ig-kill{color:var(--danger); border-color:rgba(240,102,110,.25)}

  /* === RAZER SQUARE selector frame === */
  #ash{display:flex; align-items:center; gap:0; margin:0 16px 12px; position:relative}
  #ash-frame{flex:none; width:56px; height:56px; border-radius:16px;
    background:var(--panel); border:2.5px solid var(--border); cursor:pointer; transition:.25s ease;
    display:grid; place-items:center; position:relative; z-index:2; font-size:22px; color:var(--muted)}
  #ash-frame.open{border-radius:18px 18px 4px 18px}
  @keyframes chroma-breath{
    0%,100%{box-shadow:0 0 6px 0 rgba(122,162,247,.25),inset 0 0 6px 0 rgba(122,162,247,.08)}
    50%{box-shadow:0 0 18px 4px rgba(122,162,247,.45),inset 0 0 12px 2px rgba(122,162,247,.14)}
  }
  #ash-frame.chroma-claude{animation:chroma-breath-c 2.2s ease-in-out infinite; border-color:rgba(224,145,92,.5)}
  #ash-frame.chroma-deepseek{animation:chroma-breath-d 2.2s ease-in-out infinite; border-color:rgba(122,162,247,.5)}
  #ash-frame.chroma-user{animation:chroma-breath-u 2.2s ease-in-out infinite; border-color:rgba(95,211,155,.5)}
  @keyframes chroma-breath-c{0%,100%{box-shadow:0 0 6px 0 rgba(224,145,92,.2),inset 0 0 6px 0 rgba(224,145,92,.06)}50%{box-shadow:0 0 20px 5px rgba(224,145,92,.42),inset 0 0 14px 3px rgba(224,145,92,.12)}}
  @keyframes chroma-breath-d{0%,100%{box-shadow:0 0 6px 0 rgba(122,162,247,.25),inset 0 0 6px 0 rgba(122,162,247,.08)}50%{box-shadow:0 0 20px 5px rgba(122,162,247,.48),inset 0 0 14px 3px rgba(122,162,247,.14)}}
  @keyframes chroma-breath-u{0%,100%{box-shadow:0 0 6px 0 rgba(95,211,155,.2),inset 0 0 6px 0 rgba(95,211,155,.06)}50%{box-shadow:0 0 20px 5px rgba(95,211,155,.38),inset 0 0 14px 3px rgba(95,211,155,.11)}}
  #ash-content{display:none; align-items:center; gap:2px; overflow:hidden; animation:ashSlide .22s ease}
  #ash-content.show{display:flex}
  @keyframes ashSlide{from{opacity:0;max-width:0;transform:translateX(-12px)}to{opacity:1;max-width:600px;transform:none}}
  #ash-sep{width:1px;height:34px;background:var(--border); margin:0 8px; flex:none}

  /* === settings per-variant config === */
  .setcfg{margin-top:3px; display:flex; flex-wrap:wrap; gap:8px; padding-left:82px}
  .setcfg label{font-size:11.5px; color:var(--muted); display:flex; align-items:center; gap:5px; cursor:pointer}
  .setcfg input[type=checkbox]{accent-color:var(--accent); width:14px; height:14px; cursor:pointer}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><div class="logo"></div> Bifrost <small>live agent console</small></div>
    <div class="spacer"></div>
    <div class="pills" id="pills"></div>
    <div id="tiles"></div>
    <button class="ctl" id="reloadBtn" onclick="reloadUI()" title="reload the UI server (after an agent edits it)">↻</button>
    <button class="lctl" id="gearBtn" onclick="toggleSettings()" title="presentation settings">⚙</button>
    <button class="lctl" id="lnchrBtn" onclick="toggleLauncher()" title="launch &amp; manage agents">🚀 Agents</button>
    <button class="ctl pause" id="pauseBtn" onclick="togglePause()">⏸ Pause</button>
  </header>
  <div class="banner" id="banner">⏸ Paused — the agents are frozen. Type below to interject, then Resume.</div>
  <div id="ash">
    <div id="ash-frame" onclick="toggleAsh()" title="agent selector">⏣</div>
    <div id="ash-sep"></div>
    <div id="ash-content"></div>
  </div>
  <div id="lnchr">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span style="font-weight:650;font-size:13px">Agent Launcher</span>
      <span style="color:var(--faint);font-size:11.5px">— one-click start/stop, primed with context</span>
    </div>
    <div id="lnchrRows"></div>
  </div>
  <div id="setp">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span style="font-weight:650;font-size:13px">⚙ Presentation</span>
      <span style="color:var(--faint);font-size:11.5px">— pick variants per slot; swaps live</span>
    </div>
    <div id="setpRows"></div>
  </div>
  <div id="log"></div>
  <div class="activity" id="activity"></div>
  <div class="composer">
    <div class="ladder" id="ladder">
      <button type="button" class="seg" data-fid="inform" onclick="setFidelity('inform')">Inform</button>
      <button type="button" class="seg" data-fid="steer" onclick="setFidelity('steer')">Steer</button>
      <button type="button" class="seg" data-fid="interrupt" onclick="setFidelity('interrupt')">Interrupt</button>
    </div>
    <div class="cwrap">
      <div class="recipient" id="recipient" role="button" tabindex="0" title="who receives your message — click to choose" onclick="toggleRoster()">
        <div class="rstack" id="rstack"></div>
        <div class="rlabel" id="rlabel"></div>
      </div>
      <select id="target" style="display:none"></select>
      <select id="fidelity" style="display:none"><option value="inform">inform</option><option value="steer">steer</option><option value="interrupt">interrupt</option><option value="chat">chat</option></select>
      <textarea id="input" rows="1" placeholder="Message the agents… (Enter to send, Shift+Enter for newline)"></textarea>
      <button class="send" id="sendBtn" onclick="send()">➤</button>
    </div>
    <div class="roster-pop" id="rosterPop"></div>
    <div class="hint" id="fidhint">↳ Inform = adopt next turn · Steer = fold into current task (no stop) · Interrupt = drop &amp; switch · ⏸ Pause = freeze everyone</div>
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
  if(kind==='trace'){   // live tool-call / thinking line, streamed under the agent
    const d=document.createElement('div'); d.className='traceline';
    d.innerHTML='<span class="trav '+cls(from)+'">'+esc(from)+'</span><span class="trat">'+esc(m.content||'')+'</span>';
    _msgPlacer(d, m); autoscroll(); return;
  }
  if(from==='system' || kind==='note' || kind==='_ready'){
    if(kind==='_ready') return;
    const d=document.createElement('div'); d.className='sys'+(isGuard?' guard':'');
    d.innerHTML='<span>'+esc(m.content||'')+'</span>'; _msgPlacer(d, m); autoscroll(); return;
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
    '<div class="content">'+_msgRenderer(m)+'</div></div>';
  _msgPlacer(wrap, m); autoscroll();
}
const MAX_LOG_NODES = 250;                  // bounded render window (Doom 'culling'): cap DOM so a long/bursty log never grows into lag
function trimLog(){
  // hard ceiling: the DOM can NEVER grow without bound, even while the user is scrolled up
  while(log.childElementCount > MAX_LOG_NODES*2) log.removeChild(log.firstElementChild);
  // soft window: trim to MAX only at the live tail, so reading scrollback is never yanked
  if(nearBottom) while(log.childElementCount > MAX_LOG_NODES) log.removeChild(log.firstElementChild);
}
function autoscroll(){ trimLog(); if(nearBottom) log.scrollTop = log.scrollHeight; }
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
setFidelity('inform');                           // default fidelity + light the ladder (renderRecipient runs after _recips is defined, below)
document.addEventListener('click', function(e){  // click-away closes the roster popover
  var p=document.getElementById('rosterPop'), r=document.getElementById('recipient');
  if(p && p.classList.contains('show') && !p.contains(e.target) && r && !r.contains(e.target)) p.classList.remove('show');
});

// --- send ---
const input = document.getElementById('input');
input.addEventListener('input', ()=>{ input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,160)+'px'; });
input.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } });
const FIDLABEL = {chat:'💬 sent', inform:'🟢 informed', steer:'🔵 steered (folds into current task)', interrupt:'🔴 interrupted (drop & switch)'};
function fidChanged(){
  var f = document.getElementById('fidelity'); if(!f) return;
  [].forEach.call(document.querySelectorAll('#ladder .seg'), function(b){ b.classList.toggle('on', b.dataset.fid===f.value); });
}
function setFidelity(v){ var f=document.getElementById('fidelity'); if(f) f.value=v; fidChanged(); }
async function send(){
  const text = input.value.trim(); if(!text) return;
  const fidelity = (document.getElementById('fidelity')||{}).value || 'inform';
  var isAll = _recips.length===1 && _recips[0]==='all';
  var ids = _recipIds();
  if((fidelity==='steer'||fidelity==='interrupt') && (isAll || ids.length!==1)){
    toast('pick ONE agent for '+fidelity+' (it targets a single peer)'); return;
  }
  input.value=''; input.style.height='auto';
  var targets = isAll ? ['all'] : ids;
  try{
    var ok=true;
    for(const to of targets){
      const r = await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text, to, fidelity})});
      const j = await r.json(); if(!(j&&j.ok)) ok=false;
    }
    toast(ok ? (FIDLABEL[fidelity]||'sent')+' → '+(isAll?'all':ids.join(', ')) : 'send failed — bus offline?');
  }catch(e){ toast('send failed — bus offline?'); }
}

// --- Slice 2: animated recipient selector (state = who you're messaging; last-messaged persists) ---
var _recips = ['all'];                          // ['all'] (broadcast) or a list of agent ids
function _aiRoster(){                            // AI agents in the hidden target select (excludes 'all')
  var t=document.getElementById('target'); if(!t) return [];
  return [].map.call(t.options,function(o){return o.value;}).filter(function(v){return v!=='all';});
}
function avatarInfo(a){
  var m={claude:['#f0a56c','#e0724f','C'], deepseek:['#7aa2f7','#9d7cf7','D'], user:['#48e6bf','#2fbf8f','U']};
  if(m[a]) return {a:m[a][0], b:m[a][1], l:m[a][2]};
  var h=0; for(var i=0;i<a.length;i++){ h=(h*31+a.charCodeAt(i))%360; }   // dynamic agents -> stable hue
  return {a:'hsl('+h+' 68% 62%)', b:'hsl('+((h+38)%360)+' 62% 52%)', l:(a[0]||'?').toUpperCase()};
}
function _cav(a){
  var v=avatarInfo(a), el=document.createElement('div');
  el.className='cav'; el.dataset.id=a; el.textContent=v.l; el.title=a;
  el.style.background='linear-gradient(140deg,'+v.a+','+v.b+')'; return el;
}
// reusable FLIP group animator: reconcile container's children to `ids`, animating enter/exit/reorder
function animateGroup(container, ids, makeEl){
  if(!container) return;
  var reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;
  // reconcile FIRST, synchronously: drop any child not in `ids`. Correctness over a fade-out --
  // async removal races applyStatus's periodic re-render and leaves ghosts/duplicates.
  [].slice.call(container.children).forEach(function(el){ if(ids.indexOf(el.dataset.id)<0) el.remove(); });
  var live={}, old={};
  [].forEach.call(container.children,function(el){ live[el.dataset.id]=el; old[el.dataset.id]=el.getBoundingClientRect(); });
  // enters + reorder
  ids.forEach(function(id){
    var el=live[id];
    if(!el){ el=makeEl(id); container.appendChild(el);
      if(!reduce) el.animate([{opacity:0,transform:'scale(.4)'},{opacity:1,transform:'scale(1)'}],{duration:280,easing:'cubic-bezier(.2,.9,.3,1.35)'});
    } else { container.appendChild(el); }
  });
  // FLIP the survivors from their old x to the new x
  if(!reduce) ids.forEach(function(id){
    var el=live[id], o=old[id]; if(!el||!o) return;
    var dx=o.left-el.getBoundingClientRect().left;
    if(dx) el.animate([{transform:'translateX('+dx+'px)'},{transform:'translateX(0)'}],{duration:300,easing:'cubic-bezier(.2,.9,.3,1.2)'});
  });
}
function _recipIds(){ return (_recips.length===1 && _recips[0]==='all') ? _aiRoster() : _recips.slice(); }
function renderRecipient(){
  var stack=document.getElementById('rstack'), label=document.getElementById('rlabel'), box=document.getElementById('recipient');
  if(!stack) return;
  var isAll=_recips.length===1 && _recips[0]==='all';
  var ids=_recipIds(); if(!ids.length) ids=_aiRoster();
  animateGroup(stack, ids.slice(0,4), _cav);
  label.innerHTML = isAll ? '<b>Broadcast</b><span class="cue">'+ids.length+' agent'+(ids.length===1?'':'s')+'</span>'
                  : ids.length===1 ? '<b>'+esc(ids[0])+'</b><span class="cue">last messaged</span>'
                  : '<b>'+ids.length+' agents</b><span class="cue">multi-cast</span>';
  if(box){ box.classList.remove('pulse'); void box.offsetWidth; box.classList.add('pulse'); }
  var t=document.getElementById('target'); if(t){ t.value = isAll ? 'all' : (_recips.length===1 ? _recips[0] : 'all'); }
  renderRosterPop();
}
function setRecipients(list){ _recips = (list && list.length) ? list : ['all']; renderRecipient(); }
function toggleRecipient(a){
  if(a==='all'){ setRecipients(['all']); return; }
  var s=new Set(_recips.filter(function(x){return x!=='all';}));
  if(s.has(a)) s.delete(a); else s.add(a);
  setRecipients(Array.from(s));
}
function toggleRoster(){ var p=document.getElementById('rosterPop'); if(p){ renderRosterPop(); p.classList.toggle('show'); } }
function renderRosterPop(){
  var p=document.getElementById('rosterPop'); if(!p) return;
  var ids=_aiRoster(), isAll=_recips.length===1 && _recips[0]==='all';
  var rows='<div class="ri'+(isAll?' sel':'')+'" onclick="toggleRecipient(\'all\')"><div class="cav" style="background:linear-gradient(140deg,#7aa2f7,#48e6bf)">*</div>All agents<span class="chk">✓</span></div>';
  rows+=ids.map(function(a){ var v=avatarInfo(a), sel=!isAll && _recips.indexOf(a)>=0;
    return '<div class="ri'+(sel?' sel':'')+'" onclick="toggleRecipient(\''+esc(a)+'\')"><div class="cav" style="background:linear-gradient(140deg,'+v.a+','+v.b+')">'+v.l+'</div>'+esc(a)+'<span class="chk">✓</span></div>';
  }).join('');
  p.innerHTML=rows;
}
renderRecipient();                                // first paint (now that _recips + helpers are defined)

// --- pill click -> set composer target ---
function setTarget(aid){
  var tsel=document.getElementById('target');
  if(tsel && ![].some.call(tsel.options,function(o){return o.value===aid;})){
    var opt=document.createElement('option'); opt.value=aid; opt.textContent=aid; tsel.appendChild(opt);
  }
  setRecipients([aid]);                          // pill click -> single recipient (animated)
  if(typeof updateAshChroma==='function') updateAshChroma();
}

// --- reload (after an agent edits the UI source) ---
async function reloadUI(){
  try{ await fetch('/reload',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    toast('↻ reloading UI server…'); setTimeout(()=>location.reload(), 1600);
  }catch(e){ toast('reload failed'); }
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
  // dynamic roster: UNION of ACL-registered + currently-online agents.
  // An online-but-unknown agent gets a '⚠ unknown' marker (security onboarding cue).
  const agents=(s.agents||[]).map(a=>a.agent).filter(Boolean);
  const online=new Set(agents);
  const known=s.known||[];
  const roster=[...new Set([...known, ...agents, 'user'])];
  const isKnown=new Set(known);
  const sig=s.signals||{};
  const pills=document.getElementById('pills');
  pills.innerHTML = roster.map(a=>{
    const g=sig[a]||{};
    const isOnline=online.has(a)||a==='user';
    const unknown=!isKnown.has(a) && a!=='user';
    const marks=(g.steer_pending?'<span class="sig steer" title="steer facts queued">↝'+g.steer_pending+'</span>':'')
              +(g.nudged?'<span class="sig nudge" title="interrupt pending">⚡</span>':'')
              +(unknown?' <span title="online but not ACL-registered — security onboarding cue" style="color:var(--amber);font-size:11px">⚠ unknown</span>':'');
    return '<div class="pill'+(isOnline?' on':' off')+'" onclick="setTarget(\''+esc(a)+'\')" title="click to message '+esc(a)+(unknown?' (unregistered)':'')+'"><span class="dot"></span>'+esc(a)+(isOnline?'':' 💤')+marks+'</div>';
  }).join('');
  // keep the recipient dropdown in sync with union of ACL-registered + online agents
  const tsel=document.getElementById('target');
  if(tsel){
    const targets=roster.filter(a=>a!=='user');
    const sigStr='all|'+targets.join('|');
    if(tsel.dataset.sig!==sigStr){
      const cur=tsel.value||'all';
      tsel.innerHTML='<option value="all">All</option>'+targets.map(a=>{
        const label=esc(a)+(isKnown.has(a)?'':' ⚠');
        return '<option value="'+esc(a)+'">'+label+'</option>';
      }).join('');
      tsel.value=[...tsel.options].some(o=>o.value===cur)?cur:'all';
      tsel.dataset.sig=sigStr;
    }
  }
  renderActivity(s.activities||{});
  renderRecipient();                             // keep the animated recipient chip in sync with the roster
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

// --- launcher panel ---
let lnchrOpen=false, lnchrData=[];
function toggleLauncher(){
  lnchrOpen=!lnchrOpen;
  document.getElementById('lnchr').classList.toggle('show', lnchrOpen);
  document.getElementById('lnchrBtn').classList.toggle('active', lnchrOpen);
  if(lnchrOpen) refreshLauncher();
}
function exitClass(r){ return r||'never_launched'; }
function exitLabel(r){
  const map={clean:'clean exit',token_exhausted:'⚠ token exhausted',error:'✗ error',killed:'killed',
    auth_error:'🔑 auth error', never_launched:'not launched', running:'running', exited:'exited'};
  return map[r]||r||'unknown';
}
async function refreshLauncher(){
  try{
    const r=await (await fetch('/launcher/status')).json();
    lnchrData=r||[];
    const box=document.getElementById('lnchrRows');
    box.innerHTML=lnchrData.map(a=>{
      const cls=exitClass(a.status==='running'?'running':a.exit_reason);
      const lbl=exitLabel(a.status==='running'?'running':a.exit_reason);
      const reason=a.exit_reason&&a.status!=='running'?
        '<span class="lreason">'+lbl+(a.exit_code!=null?' (code '+a.exit_code+')':'')+'</span>':'';
      const running=a.status==='running';
      const pidInfo=running?' <span style="color:var(--faint);font-size:11px">pid '+a.pid+'</span>':'';
      return '<div class="lrow">'+
        '<span class="ltag">'+esc(a.tag)+pidInfo+'</span>'+
        '<span class="ldesc">'+esc(a.description||'')+'</span>'+
        '<span class="lst '+cls+'">'+lbl+'</span>'+reason+
        '<span class="lact">'+
          '<button class="lgo" onclick="launchAgent(\''+esc(a.tag)+'\')" '+(running||!a.enabled?'disabled':'')+'>'+
            (running?'running':'▶ Launch')+'</button>'+
          '<button class="lkill" onclick="killAgent(\''+esc(a.tag)+'\')" '+(!running?'disabled':'')+'>'+
            '✕ Kill</button>'+
        '</span></div>';
    }).join('')||'<div style="color:var(--faint);text-align:center;padding:12px">no agents registered — add entries to security/launcher.json</div>';
  }catch(e){}
}
async function launchAgent(tag){
  const row=lnchrData.find(a=>a.tag===tag);
  if(!row) return;
  toast('🚀 launching '+tag+'…');
  try{
    const r=await fetch('/launcher/launch',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag})});
    const j=await r.json();
    if(j&&j.ok) toast('✅ '+tag+' started (pid '+j.pid+')');
    else toast('❌ '+(j?j.error:'failed to launch '+tag));
    refreshLauncher();
  }catch(e){ toast('launch failed — server offline?'); }
}
async function killAgent(tag){
  toast('⏹ killing '+tag+'…');
  try{
    const r=await fetch('/launcher/kill',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag})});
    const j=await r.json();
    if(j&&j.ok) toast('⏹ '+tag+' terminated');
    else toast('❌ '+(j?j.error:'failed to kill '+tag));
    refreshLauncher();
  }catch(e){ toast('kill failed'); }
}
// poll launcher status when open
const LPOLL=setInterval(()=>{ if(lnchrOpen) refreshLauncher(); }, 5000);

// ==================================================================
//  V2 PRESENTATION REGISTRY  —  strangler alongside existing UI
//  Slots: theme | tile | message | viewmode
//  Each slot holds registered variants; getPref/setPref persist to
//  localStorage; mountAll() applies the active variant per slot.
//  Reference variants: aurora, glass-card, markdown, feed.
// ==================================================================
const SLOTS=['theme','tile','message','viewmode'];
const DEFAULTS={theme:'aurora',tile:'glass-card',message:'markdown',viewmode:'feed'};
const REGISTRY={theme:{},tile:{},message:{},viewmode:{}};
let _activeVariant={...DEFAULTS};
let _glassCardData={agents:[],known:[],signals:{}};

function getPref(slot){ try{ return localStorage.getItem('bifrost_pref_'+slot)||DEFAULTS[slot]; }catch(e){ return DEFAULTS[slot]; } }
function setPref(slot,id){
  try{ localStorage.setItem('bifrost_pref_'+slot,id); }catch(e){}
  mountSlot(slot,id);
}
function mountSlot(slot,id){
  if(!REGISTRY[slot]||!REGISTRY[slot][id]) return;
  if(_activeVariant[slot]===id) return;
  var oldId=_activeVariant[slot];
  if(oldId&&REGISTRY[slot][oldId]&&REGISTRY[slot][oldId].unmount) REGISTRY[slot][oldId].unmount();
  _activeVariant[slot]=id;
  if(REGISTRY[slot][id].mount) REGISTRY[slot][id].mount();
  refreshSettingsPanel();
}
function mountAll(){
  SLOTS.forEach(function(s){
    var id=getPref(s);
    _activeVariant[s]='';
    mountSlot(s,id);
  });
}
function registerVariant(slot,id,label,desc,mount,unmount,config,applyCfg){
  if(!REGISTRY[slot]) REGISTRY[slot]={};
  REGISTRY[slot][id]={label:label||id,desc:desc||'',mount:mount||noop,unmount:unmount||noop,
    config:config||null, applyConfig:applyCfg||null};
}
// variant config read/write (per-slot+id key)
function getVariantCfg(slot,id){
  try{ return JSON.parse(localStorage.getItem('bifrost_cfg_'+slot+'_'+id)||'{}'); }catch(e){ return {}; }
}
function setVariantCfg(slot,id,cfg){
  try{ localStorage.setItem('bifrost_cfg_'+slot+'_'+id, JSON.stringify(cfg)); }catch(e){}
  var v=REGISTRY[slot]&&REGISTRY[slot][id];
  if(v&&v.applyConfig) v.applyConfig(cfg);
  if(_activeVariant[slot]===id) refreshSettingsPanel();
}

// --- reference variants (one per slot, drop-in ready) ---

// theme variants — inject/remove a <style id="bifrost-theme-v2"> to swap :root
var THEME_CSS = {
  aurora:'',
  ember:' :root{--bg:#0d0a07;--bg2:#14100c;--panel:#1a1510;--panel2:#1f1913;--border:#2d2418;--text:#f0e6d3;--muted:#a08c70;--faint:#6a5a43;--claude:#e0915c;--deepseek:#f0b246;--user:#5fd39b;--system:#8a7c6e;--accent:#f0b246;--accent2:#e8783a;--amber:#f5c542;--danger:#f0666e;--shadow:0 8px 30px rgba(0,0,0,.45);}',
  abyss:' :root{--bg:#050a0f;--bg2:#080f17;--panel:#0c1520;--panel2:#101a28;--border:#1a2a3a;--text:#d0e0f0;--muted:#7088a8;--faint:#4a6078;--claude:#5fd0d9;--deepseek:#48c0ff;--user:#5fd39b;--system:#6088a0;--accent:#48c0ff;--accent2:#3090e0;--amber:#a0c040;--danger:#f0666e;--shadow:0 8px 30px rgba(0,0,0,.55);}',
  frost:' :root{--bg:#f2f4f8;--bg2:#e8ecf2;--panel:#ffffff;--panel2:#f5f7fa;--border:#d8dde5;--text:#1a1e2e;--muted:#6b7280;--faint:#9ca3af;--claude:#d97746;--deepseek:#4f7cf7;--user:#2ea87a;--system:#7c8ba0;--accent:#4f7cf7;--accent2:#7c4ff7;--amber:#d4a017;--danger:#e04040;--shadow:0 4px 16px rgba(0,0,0,.08);}'
};
function _mountTheme(id){
  var el=document.getElementById('bifrost-theme-v2');
  if(!el){ el=document.createElement('style'); el.id='bifrost-theme-v2'; document.head.appendChild(el); }
  el.textContent=THEME_CSS[id]||'';
}
function _unmountTheme(){ var el=document.getElementById('bifrost-theme-v2'); if(el) el.textContent=''; }

registerVariant('theme','aurora','Aurora','dark cosmic (default)');
registerVariant('theme','ember','Ember','warm amber coals',function(){_mountTheme('ember');},_unmountTheme);
registerVariant('theme','abyss','Abyss','deep ocean trench',function(){_mountTheme('abyss');},_unmountTheme);
registerVariant('theme','frost','Frost','arctic clean light',function(){_mountTheme('frost');},_unmountTheme);

// tile='glass-card' — frosted card with role badge, state-glow, expand-to-roster
// actions channel: {onSelect, onSetTarget, onSetFidelity, onSpawn, onKill}
// config: {compact:true} collapses cards to icon-only (space-saver)
registerVariant('tile','glass-card','Glass Card','frosted card + state glow + expand actions',
  function mountGlassCard(){
    document.getElementById('pills').style.display='none';
    var t=document.getElementById('tiles'); t.classList.add('show');
    var cfg=getVariantCfg('tile','glass-card');
    t.classList.toggle('compact',!!cfg.compact);
    renderGlassCards();
  },
  function unmountGlassCard(){
    document.getElementById('pills').style.display='';
    document.getElementById('tiles').classList.remove('show','compact');
  },
  [{key:'compact',type:'bool',default:false,label:'Compact (icon-only)'}],
  function(cfg){ document.getElementById('tiles').classList.toggle('compact',!!cfg.compact); }
);

// tile='iso-cube' — CSS 3D isometric cube, one per agent. Face colors from agent class.
// animateExpand(el, agents, actions) renders cubes into the selector frame content.
registerVariant('tile','iso-cube','Iso Cube','CSS 3D isometric cube per agent',
  function mountIsoCube(){
    document.getElementById('pills').style.display='none';
    var t=document.getElementById('tiles'); t.classList.add('show');
    renderIsoCubes();
  },
  function unmountIsoCube(){
    document.getElementById('pills').style.display='';
    document.getElementById('tiles').classList.remove('show');
  },
  [{key:'labelOnTop',type:'bool',default:true,label:'Labels on top face'}],
  function(cfg){ /* no live re-render needed for label toggle on existing cubes */ }
);

// message='markdown' — current fmt() (code + backtick); no-op. Variant overrides
// _msgRenderer(msg) → returns HTML string; called by addMsg instead of fmt()
var _msgRenderer = function(msg){ return fmt(msg.content); };
registerVariant('message','markdown','Markdown','code-block + backtick formatter',
  function(){ _msgRenderer = function(msg){ return fmt(msg.content); }; },
  function(){ _msgRenderer = function(msg){ return fmt(msg.content); }; }
);

// viewmode='feed' — appends to #log. Variant overrides _msgPlacer(el, msg)
// to control where a message DOM element lands (split-view, threaded, etc.)
var _msgPlacer = function(el, msg){ log.appendChild(el); };
registerVariant('viewmode','feed','Feed','single chronological log',
  function(){ _msgPlacer = function(el, msg){ log.appendChild(el); }; },
  function(){ _msgPlacer = function(el, msg){ log.appendChild(el); }; }
);

// ---- glass-card renderer ----
function renderGlassCards(){
  var box=document.getElementById('tiles');
  var d=_glassCardData;
  var agents=d.agents||[];
  var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  box.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user';
    var g=sig[aid]||{};
    var nudged=g.nudged, steered=g.steer_pending;
    var unknown=!isKnown.has(aid) && aid!=='user';
    var cl='gcard';
    if(isOnline) cl+=' online';
    if(nudged) cl+=' nudged';
    if(steered) cl+=' steered';
    var roleHtml=(aid==='deepseek'||aid==='claude')?'<span class="gbadge admin">admin</span>':'';
    if(unknown) roleHtml+=' <span class="gbadge" style="color:var(--amber);background:rgba(240,178,70,.12);border-color:rgba(240,178,70,.25)">⚠ unknown</span>';
    var statusMark=isOnline?'':' \u{1f4a4}';
    var steerMark=steered?'<span class="sig steer" title="steer pending">\u21dd'+steered+'</span>':'';
    var nudgeMark=nudged?'<span class="sig nudge" title="nudge pending">\u26a1</span>':'';
    return '<div class="'+cl+'" onclick="toggleGCard(event,\''+esc(aid)+'\')">'+
      '<div class="gdot"></div>'+
      '<div style="flex:1;min-width:0"><div class="gname">'+esc(aid)+statusMark+'</div>'+roleHtml+'</div>'+
      steerMark+nudgeMark+
      '<div class="gactions">'+
        '<button onclick="event.stopPropagation();setTarget(\''+esc(aid)+'\')">\u{1f3af} Select</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'chat\')">\u{1f4ac} Chat</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'steer\')">\u{1f535} Steer</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'interrupt\')">\u{1f534} Interrupt</button>'+
        '<button class="gact-spawn" onclick="event.stopPropagation();glassSpawn(\''+esc(aid)+'\')">\u25b6 Spawn</button>'+
        '<button class="gact-kill" onclick="event.stopPropagation();glassKill(\''+esc(aid)+'\')">\u2715 Kill</button>'+
      '</div></div>';
  }).join('');
}

// ---- iso-cube renderer ----
function renderIsoCubes(){
  var box=document.getElementById('tiles');
  var d=_glassCardData;
  var agents=d.agents||[]; var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  box.className='icube-row';
  box.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user';
    var g=sig[aid]||{}; var nudged=g.nudged, steered=g.steer_pending;
    var unknown=!isKnown.has(aid) && aid!=='user';
    var cl='icube'; if(isOnline) cl+=' online'; if(nudged) cl+=' nudged';
    var ca=cls(aid);
    return '<div class="'+cl+'" onclick="toggleICube(event,\''+esc(aid)+'\')">'+
      '<div class="icube-inner">'+
        '<div class="icube-face icube-top"><div class="iname">'+esc(aid)+'</div></div>'+
        '<div class="icube-face icube-front"><div class="iav '+ca+'">'+initials(aid)+'</div></div>'+
        '<div class="icube-face icube-right"></div>'+
      '</div>'+
      (unknown?'<span style="position:absolute;bottom:-2px;right:2px;font-size:9px;color:var(--amber)" title="online but not ACL-registered">⚠</span>':'')+
      (steered?'<span class="sig steer" style="position:absolute;top:-4px;right:-4px" title="steer pending">\u21dd</span>':'')+
      (nudged?'<span class="sig nudge" style="position:absolute;top:-4px;right:14px" title="interrupt pending">\u26a1</span>':'')+
      '<div class="igact">'+
        '<button onclick="event.stopPropagation();setTarget(\''+esc(aid)+'\')">\u{1f3af} Select</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'chat\')">\u{1f4ac} Chat</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'steer\')">\u{1f535} Steer</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'interrupt\')">\u{1f534} Interrupt</button>'+
        '<button class="ig-spawn" onclick="event.stopPropagation();glassSpawn(\''+esc(aid)+'\')">\u25b6 Spawn</button>'+
        '<button class="ig-kill" onclick="event.stopPropagation();glassKill(\''+esc(aid)+'\')">\u2715 Kill</button>'+
      '</div></div>';
  }).join('');
}
function toggleICube(e,aid){
  e.stopPropagation();
  var c=e.currentTarget; var was=c.classList.contains('expanded');
  document.querySelectorAll('.icube.expanded').forEach(function(el){el.classList.remove('expanded');});
  if(!was){ c.classList.add('expanded'); setTarget(aid); }
}
document.addEventListener('click',function(){ document.querySelectorAll('.icube.expanded').forEach(function(c){c.classList.remove('expanded');}); });

// ---- tile variant animateExpand (for selector frame) ----
function animateExpandTiles(el, agents, actions){
  var d=_glassCardData; var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  var vt=REGISTRY['tile']&&REGISTRY['tile'][_activeVariant.tile];
  if(vt&&vt.animateExpand){ vt.animateExpand(el, roster, online, sig, actions, isKnown); return; }
  el.innerHTML=roster.map(function(aid){
    var unk=!isKnown.has(aid)&&aid!=='user'?' ⚠':'';
    return '<button style="font:inherit;font-size:12px;padding:4px 10px;border-radius:6px;cursor:pointer;border:1px solid var(--border);background:var(--panel);color:var(--text);white-space:nowrap" onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+
      (online.has(aid)||aid==='user'?'\u25cf ':'\u25cb ')+esc(aid)+unk+'</button>';
  }).join('');
}
REGISTRY['tile']['glass-card'].animateExpand=function(el,roster,online,sig,actions,isKnown){
  el.innerHTML=roster.map(function(aid){
    var g=sig[aid]||{}; var isOnline=online.has(aid)||aid==='user';
    var nudged=g.nudged, steered=g.steer_pending;
    var unk=!isKnown.has(aid)&&aid!=='user'?' ⚠':'';
    var span='<span style="font-size:12px;font-weight:650;color:var(--text)">'+esc(aid)+unk+(isOnline?'':' \u{1f4a4}')+'</span>';
    if(steered) span+='<span class="sig steer" style="font-size:9px">\u21dd'+steered+'</span>';
    if(nudged) span+='<span class="sig nudge" style="font-size:9px">\u26a1</span>';
    return '<button style="font:inherit;font-size:12px;padding:5px 10px;border-radius:8px;cursor:pointer;border:1px solid '+(isOnline?'rgba(95,211,155,.3)':'var(--border)')+';background:var(--panel);color:var(--text);display:flex;align-items:center;gap:6px"'+
      ' onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+span+'</button>';
  }).join('');
};
REGISTRY['tile']['iso-cube'].animateExpand=function(el,roster,online,sig,actions,isKnown){
  el.style.cssText='display:flex;gap:10px;flex-wrap:wrap;padding:4px 0';
  el.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user'; var ca=cls(aid);
    var unk=!isKnown.has(aid)&&aid!=='user'?'<span style="position:absolute;bottom:0;right:2px;font-size:8px;color:var(--amber)">⚠</span>':'';
    return '<div style="width:46px;height:46px;perspective:300px;cursor:pointer;flex:none;position:relative" onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+
      '<div style="position:relative;width:100%;height:100%;transform:rotateX(-22deg)rotateY(-32deg);transform-style:preserve-3d">'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid '+(isOnline?'rgba(95,211,155,.35)':'var(--border)')+';border-radius:7px;background:rgba(20,22,29,.78);transform:translateZ(23px);display:grid;place-items:center">'+
          '<div class="iav '+ca+'" style="width:20px;height:20px;font-size:8px;border-radius:4px">'+initials(aid)+'</div></div>'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid var(--border);border-radius:7px;background:rgba(20,22,29,.7);transform:rotateX(90deg)translateZ(23px)"></div>'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid var(--border);border-radius:7px;background:rgba(16,18,24,.7);transform:rotateY(90deg)translateZ(23px)"></div>'+
      '</div>'+unk+'</div>';
  }).join('');
};

function toggleGCard(e,aid){
  e.stopPropagation();
  var card=e.currentTarget;
  var was=card.classList.contains('expanded');
  document.querySelectorAll('.gcard.expanded').forEach(function(c){c.classList.remove('expanded');});
  if(!was){ card.classList.add('expanded'); setTarget(aid); }
}
document.addEventListener('click',function(){ document.querySelectorAll('.gcard.expanded').forEach(function(c){c.classList.remove('expanded');}); });

// actions channel wiring
function setTargetFidelity(aid,fidelity){
  setTarget(aid);
  var fsel=document.getElementById('fidelity');
  if(fsel){ fsel.value=fidelity; fidChanged(); }
}
function glassSpawn(aid){
  var row=(lnchrData||[]).find(function(a){return a.agent_id===aid||a.tag===aid;});
  var tag=row?row.tag:aid;
  launchAgent(tag);
}
function glassKill(aid){
  var row=(lnchrData||[]).find(function(a){return a.agent_id===aid||a.tag===aid;});
  var tag=row?row.tag:aid;
  killAgent(tag);
}

// ---- wrap applyStatus to feed glass-card + iso-cube + selector frame data ----
(function(){
  var _orig=applyStatus;
  applyStatus=function(s){
    _orig(s);
    var agents=(s.agents||[]).map(function(a){return a.agent;}).filter(Boolean);
    var known=s.known||[];
    _glassCardData={
      agents:agents,
      known:known,
      roster:[...new Set([...known, ...agents, 'user'])],
      isKnown:new Set(known),
      signals:s.signals||{}
    };
    if(_activeVariant.tile==='glass-card') renderGlassCards();
    if(_activeVariant.tile==='iso-cube') renderIsoCubes();
    updateAshChroma();
  };
})();

// ---- selector frame (Razer square) ----
var _ashOpen=false, _ashTarget='';
function toggleAsh(){
  _ashOpen=!_ashOpen;
  var f=document.getElementById('ash-frame'); var c=document.getElementById('ash-content');
  var s=document.getElementById('ash-sep');
  f.classList.toggle('open',_ashOpen);
  c.classList.toggle('show',_ashOpen);
  s.style.display=_ashOpen?'block':'none';
  if(_ashOpen){
    var agents=_glassCardData.agents||[];
    animateExpandTiles(c, agents, {onSelect:setTargetAndCloseAsh});
  }
}
function setTargetAndCloseAsh(aid){
  _ashTarget=aid; setTarget(aid); updateAshChroma();
  _ashOpen=false;
  document.getElementById('ash-frame').classList.remove('open');
  document.getElementById('ash-content').classList.remove('show');
  document.getElementById('ash-sep').style.display='none';
}
function updateAshChroma(){
  var f=document.getElementById('ash-frame');
  var tsel=document.getElementById('target');
  var aid=(tsel&&tsel.value!=='all')?tsel.value:'';
  f.className=f.className.replace(/\s*chroma-\w+/g,'');
  if(aid==='claude') f.classList.add('chroma-claude');
  else if(aid==='deepseek') f.classList.add('chroma-deepseek');
  else if(aid) f.classList.add('chroma-user');
}

// ---- settings panel ----
var setpOpen=false;
function toggleSettings(){
  setpOpen=!setpOpen;
  document.getElementById('setp').classList.toggle('show',setpOpen);
  document.getElementById('gearBtn').classList.toggle('active',setpOpen);
  if(setpOpen) refreshSettingsPanel();
}
function refreshSettingsPanel(){
  var box=document.getElementById('setpRows');
  if(!box) return;
  box.innerHTML=SLOTS.map(function(slot){
    var variants=REGISTRY[slot]||{};
    var active=_activeVariant[slot]||DEFAULTS[slot];
    var opts=Object.keys(variants).map(function(id){
      return '<option value="'+esc(id)+'"'+(id===active?' selected':'')+'>'+esc(variants[id].label||id)+'</option>';
    }).join('');
    var desc=(variants[active]||{}).desc||'';
    var cfgHtml='';
    var v=variants[active];
    if(v&&v.config&&v.config.length){
      var curCfg=getVariantCfg(slot,active);
      cfgHtml='<div class="setcfg">'+v.config.map(function(c){
        if(c.type==='bool'){
          var checked=curCfg[c.key]!==undefined?curCfg[c.key]:c.default;
          return '<label><input type="checkbox" '+(checked?'checked':'')+
            ' onchange="var o=getVariantCfg(\''+esc(slot)+'\',\''+esc(active)+'\');o[\''+esc(c.key)+'\']=this.checked;setVariantCfg(\''+esc(slot)+'\',\''+esc(active)+'\',o)">'+
            esc(c.label||c.key)+'</label>';
        }
        return '';
      }).join('')+'</div>';
    }
    return '<div class="setrow"><label>'+esc(slot)+'</label>'+
      '<select onchange="setPref(\''+esc(slot)+'\',this.value)">'+opts+'</select>'+
      '<span class="setdesc">'+esc(desc)+'</span></div>'+cfgHtml;
  }).join('');
}

function noop(){}

// ---- init: apply stored preferences ----
mountAll();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
