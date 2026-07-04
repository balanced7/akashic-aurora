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
        if path == "/aurora-shader.js":
            return self._static("scripts/aurora-shader.js", "application/javascript")
        if path == "/bifrost_viz.js":
            return self._static("scripts/bifrost_viz.js", "application/javascript")
        if path == "/theme-void.js":
            return self._static("scripts/theme-void.js", "application/javascript")
        if path == "/presence-rail.js":
            return self._static("scripts/presence-rail.js", "application/javascript")
        if path == "/presence-cloud.js":
            return self._static("scripts/presence-cloud.js", "application/javascript")
        self.send_error(404)

    def _html(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, relpath, mime):
        """Serve a static file from the repo root. Caches nothing (dev cockpit)."""
        fpath = os.path.join(REPO, relpath.replace("/", os.sep))
        try:
            with open(fpath, "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (FileNotFoundError, PermissionError):
            self.send_error(404)

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
        # Known: ALL registered agents (always visible, even offline) + any agent currently online.
        # The roster shows every agent the user might want to message, not just ACL-registered ones.
        known = []
        try:
            known = sorted([g.agent_id for g in registry.grants()])
            # Always include agents that have ever appeared on the bus (even if not ACL'd)
            for a in agents:
                aid = a.get("agent")
                if aid and aid not in known:
                    known.append(aid)
            known.sort()
        except Exception:
            pass
        return {"paused": control.is_paused(), "pause": control.pause_status(),
                "agents": agents, "known": known, "activities": control.get_activities(),
                "signals": signals, "max_hops": control.MAX_HOPS,
                "halted": control.halted_agents(),
                "narration": control.get_narration_level()}   # claude reasoning visibility: off|key|full

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
        if path == "/negotiate":
            return self._negotiate(data)
        if path == "/narration":
            return self._narration(data)
        self.send_error(404)

    def _narration(self, data):
        """Set claude's reasoning-visibility level (off|key|full)."""
        level = str(data.get("level", "")).strip().lower()
        if level not in ("off", "key", "full"):
            return self._json({"ok": False, "error": "level must be off|key|full"}, 400)
        control.set_narration_level(level, by="user")
        return self._json({"ok": True, "level": level})

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

    def _negotiate(self, data):
        """Open a negotiation round after user input. Agents have 8s to declare their plan
        (what + scope + estimate). Returns the verdict: green/amber/red + conflict details."""
        context = (data.get("text") or "").strip()
        if not context:
            return self._json({"ok": False, "error": "empty context"}, 400)
        try:
            from bifrost.api import round_result
            result = round_result(triggered_by="user", context=context)
            return self._json({"ok": True, "verdict": result.get("verdict"),
                               "reason": result.get("reason"),
                               "proposals": result.get("proposals", []),
                               "conflicts": result.get("conflicts", []),
                               "round": result.get("round_id", "")})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)

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
    --text:#e7e9f0; --muted:#8b90a2; --faint:#727890;
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
  /* Aurora Glass canvas — the animated light bed behind everything.
     Replaces the body::before blur pseudo-element when WebGL2 is available;
     falls back to the CSS gradient when not. z-index:-2 so the body::after
     noise texture (z-index:-1) sits ON TOP of the aurora for grain. */
  #aurora-canvas{position:fixed; inset:0; z-index:-2; pointer-events:none}
  /* Viz canvas — slide-deck cards between aurora and cockpit. Hidden by default;
     shown when the viz engine is active (toggle via 'v' key or header button). */
  #viz-canvas{position:fixed; inset:0; z-index:-1; pointer-events:none; display:none}
  #viz-canvas.show{display:block}
  /* Viz control bar — overlays the top-right of the cockpit when viz is active */
  #viz-ctl{display:none; position:fixed; top:70px; right:20px; z-index:10; gap:6px}
  #viz-ctl.show{display:flex}
  #viz-ctl button{font:inherit; font-size:11px; font-weight:600; padding:5px 10px;
    border-radius:7px; cursor:pointer; border:1px solid var(--border);
    background:rgba(20,22,29,.85); color:var(--text); backdrop-filter:blur(8px);
    -webkit-backdrop-filter:blur(8px); transition:.15s}
  #viz-ctl button:hover{border-color:#39405a; background:rgba(23,26,34,.9)}
  #viz-ctl button.on{color:var(--accent); border-color:rgba(122,162,247,.35)}
  /* STATIC atmosphere: an animated blur(70px) repainted the whole viewport every frame -> typing/scroll jank.
     This is the CSS fallback; hidden when the WebGL canvas is active. */
  body::before{content:""; position:fixed; inset:-25%; z-index:-1; pointer-events:none; opacity:.6;
    background:conic-gradient(from 200deg at 42% 40%, var(--glow2),var(--glow3),var(--glow1),var(--glow4),var(--glow2));
    filter:blur(60px)}
  body::after{content:""; position:fixed; inset:0; z-index:-1; pointer-events:none; opacity:.3;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/></svg>")}
  .app{display:flex; flex-direction:column; height:100vh; max-width:1180px; margin:0 auto; position:relative; z-index:1}
  /* header */
  header{
    display:flex; align-items:center; gap:14px; padding:14px 20px;
    border-bottom:1px solid var(--glass-line); background:var(--glass);
    backdrop-filter:blur(26px) saturate(1.35); -webkit-backdrop-filter:blur(26px) saturate(1.35);
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
  .bubble{max-width:78%; background:var(--panel); border:1px solid var(--border); border-radius:5px 15px 15px 15px;
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
  /* === HUD glanceability strip (who's-doing-what, always visible) === */
  #hud{display:none; flex-direction:column; margin:0 16px; padding:6px 0; max-height:148px; overflow-y:auto;
    border-bottom:1px solid var(--glass-line);
    background:linear-gradient(to bottom,var(--glass),transparent 60%);
    backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
    transition:max-height .3s ease}
  #hud.show{display:flex}
  #hud.collapsed{max-height:38px}
  .hrow{display:flex; align-items:center; gap:9px; padding:5px 11px; min-height:30px; font-size:12.5px;
    animation:hudIn .26s cubic-bezier(.2,.9,.3,1.1); transition:background .18s,opacity .22s;
    border-radius:8px; cursor:pointer}
  .hrow:hover{background:var(--glass-hi)}
  .hrow.stale{opacity:.48}
  .hrow.expanded{background:var(--panel); border:1px solid var(--border); margin:1px 0}
  .hicon{flex:none; font-size:14px; width:20px; text-align:center}
  .hagent{font-weight:650; min-width:62px; white-space:nowrap}
  .hagent.claude{color:var(--claude)} .hagent.deepseek{color:var(--deepseek)}
  .hverb{color:var(--muted); min-width:52px; white-space:nowrap}
  .hdetail{flex:1; color:var(--faint); font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:11.5px;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0}
  .hrow:hover .hdetail{overflow:visible; white-space:normal; word-break:break-all}
  .helapsed{flex:none; color:var(--faint); font-size:11px; min-width:36px; text-align:right}
  /* new-activity glow pulse on the icon */
  .hrow.just-started .hicon{animation:hudPulse .55s ease-out}
  /* scan-line: a 1px sweep down the strip, the sci-fi HUD signature */
  #hud::after{content:""; position:absolute; left:0;right:0; height:1px; pointer-events:none;
    background:var(--hud-scanline, rgba(255,255,255,.025));
    animation:hudScan 3.8s linear infinite}
  @keyframes hudIn{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
  @keyframes hudPulse{0%{filter:drop-shadow(0 0 3px var(--aurora-neon, #48e6bf))}100%{filter:drop-shadow(0 0 0px transparent)}}
  @keyframes hudScan{from{top:0}to{top:100%}}
  #hud-toggle{align-self:flex-end; font-size:11px; color:var(--faint); cursor:pointer; padding:0 6px 2px;
    user-select:none; display:none}
  #hud-toggle.show{display:block}
  /* === slide deck cards (mini teaching slides when a HUD row is clicked) === */
  #deck{display:none; margin:0 16px 8px; position:relative; overflow:hidden}
  #deck.show{display:block}
  .deck-cards{display:flex; gap:0; width:100%; transition:transform .35s cubic-bezier(.2,.9,.3,1.05); will-change:transform}
  .slide-card{flex:none; width:100%; background:var(--panel); border:1px solid var(--border); border-radius:14px;
    padding:16px 18px; box-shadow:var(--shadow); position:relative;
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
  .slide-card .sc-head{display:flex; align-items:center; gap:10px; margin-bottom:8px}
  .slide-card .sc-icon{font-size:20px; width:28px; text-align:center}
  .slide-card .sc-title{font-weight:700; font-size:14px; color:var(--text)}
  .slide-card .sc-body{font-size:13px; color:var(--muted); line-height:1.5}
  .slide-card .sc-body code{font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:12px;
    background:var(--bg2); border:1px solid var(--border); border-radius:5px; padding:1px 6px; color:var(--text)}
  .slide-card .sc-result{font-size:13px; margin-top:8px; padding:8px 0 0; border-top:1px solid var(--border)}
  .slide-card .sc-result.good{color:var(--user)} .slide-card .sc-result.warn{color:var(--amber)} .slide-card .sc-result.bad{color:var(--danger)}
  .slide-dots{display:flex; justify-content:center; gap:8px; margin-top:10px}
  .slide-dot{width:7px; height:7px; border-radius:50%; background:var(--border); transition:all .3s}
  .slide-dot.active{background:var(--aurora-neon, #48e6bf); box-shadow:0 0 6px var(--aurora-neon, #48e6bf);
    transform:scale(1.3)}
  .deck-controls{display:flex; justify-content:center; align-items:center; gap:10px; margin-top:6px}
  .deck-ctrl{font-size:12px; color:var(--faint); cursor:pointer; user-select:none; padding:4px 10px;
    border-radius:8px; border:1px solid var(--border); background:var(--panel); transition:.15s}
  .deck-ctrl:hover{color:var(--text); border-color:var(--aurora-neon)}
  .deck-ctrl.paused{color:var(--amber); border-color:var(--amber)}
  /* card entry animation */
  @keyframes slideCardIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:none}}
  .slide-card{animation:slideCardIn .35s cubic-bezier(.2,.9,.3,1.05) both}
  .slide-card:nth-child(2){animation-delay:.05s}
  .slide-card:nth-child(3){animation-delay:.1s}
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
<canvas id="aurora-canvas"></canvas>
<canvas id="viz-canvas"></canvas>
<div class="app">
  <header>
    <div class="brand"><div class="logo"></div> Bifrost <small>live agent console</small></div>
    <div class="spacer"></div>
    <div class="pills" id="pills"></div>
    <div id="tiles"></div>
    <button class="ctl" id="reloadBtn" onclick="reloadUI()" title="reload the UI server (after an agent edits it)">↻</button>
    <button class="lctl" id="gearBtn" onclick="toggleSettings()" title="presentation settings">⚙</button>
    <button class="lctl" id="lnchrBtn" onclick="toggleLauncher()" title="launch &amp; manage agents">🚀 Agents</button>
    <button class="lctl" id="vizBtn" onclick="vizToggle()" title="toggle viz slide deck (v)">📊 Deck</button>
    <button class="ctl pause" id="pauseBtn" onclick="togglePause()">⏸ Pause</button>
  </header>
  <div class="banner" id="banner">⏸ Paused — the agents are frozen. Type below to interject, then Resume.</div>
  <div id="hud"><div id="hud-toggle" class="show" onclick="toggleHUD()" title="collapse HUD">⌃ collapse</div></div>
  <div id="deck"><div class="deck-cards" id="deckCards"></div><div class="slide-dots" id="deckDots"></div><div class="deck-controls"><span class="deck-ctrl" id="deckPrev" onclick="deckPrev()">◀ prev</span><span class="deck-ctrl" id="deckPause" onclick="deckTogglePause()">⏸ pause</span><span class="deck-ctrl" id="deckNext" onclick="deckNext()">next ▶</span></div></div>
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
    <div style="border-top:1px solid var(--border);margin:10px 0 6px;padding-top:10px">
      <span style="font-weight:650;font-size:13px">🌌 Aurora Glass</span>
      <span style="color:var(--faint);font-size:11.5px"> — progressive enhancement; toggle live</span>
    </div>
    <div id="setpAurora">
      <div class="setrow">
        <label>WebGL Aurora</label>
        <span class="setdesc">animated aurora background (needs WebGL2 + bench PASS)</span>
      </div>
      <div class="setrow" style="justify-content:flex-end">
        <button id="auroraToggle" class="lctl" onclick="toggleAuroraFlag()">Enable</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="auroraStatus">off — run bench-aurora.html first</span>
      </div>
      <div class="setrow">
        <label>HUD Strip</label>
        <span class="setdesc">who's-doing-what glanceability strip</span>
      </div>
      <div class="setrow" style="justify-content:flex-end">
        <button id="hudToggle" class="lctl" onclick="toggleHUDFlag()">Disable</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="hudStatus">on — pure DOM, no perf cost</span>
      </div>
      <div class="setrow">
        <label>Narration</label>
        <span class="setdesc">claude's reasoning visibility — off | key | full</span>
      </div>
      <div class="setrow" style="justify-content:flex-end;gap:6px">
        <button class="lctl narr-btn" data-lvl="off" onclick="setNarration('off')">off</button>
        <button class="lctl narr-btn active" data-lvl="key" onclick="setNarration('key')">key</button>
        <button class="lctl narr-btn" data-lvl="full" onclick="setNarration('full')">full</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="narrStatus">key — decision points only</span>
      </div>
      <div class="setrow" id="auroraSpeedRow" style="display:none">
        <label>Drift Speed</label>
        <input type="range" id="auroraSpeedSlider" min="0.25" max="2" step="0.05" value="1" style="flex:1;margin:0 8px"
          oninput="setAuroraSpeed(parseFloat(this.value))">
        <span class="setdesc" id="auroraSpeedLabel">1×</span>
      </div>
      <div class="setrow" id="auroraIntensityRow" style="display:none">
        <label>Intensity</label>
        <input type="range" id="auroraIntensitySlider" min="0.2" max="1" step="0.05" value="0.85" style="flex:1;margin:0 8px"
          oninput="setAuroraIntensity(parseFloat(this.value))">
        <span class="setdesc" id="auroraIntensityLabel">0.85</span>
      </div>
    </div>
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
<div id="viz-ctl">
  <button onclick="vizPrev()" title="previous card (←)">◀</button>
  <button id="vizGridBtn" onclick="vizGrid()" title="grid view (g)">⊞ grid</button>
  <button onclick="vizNext()" title="next card (→)">▶</button>
  <span style="font-size:10px;color:var(--faint);padding:5px 4px" id="vizLabel">—</span>
  <button id="vizDeckBtn" onclick="vizDeckMode()" title="full-view deck mode (d) — shrinks message log">⛶ deck</button>
  <button onclick="vizToggle()" title="hide viz (v)">✕</button>
</div>

<script src="/aurora-shader.js"></script>
<script src="/bifrost_viz.js"></script>
<script>
const log = document.getElementById('log');
const seen = new Set();
let paused = false, nearBottom = true, lastFrom = null;

log.addEventListener('scroll', ()=>{
  nearBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 120;
  if(log.scrollTop < 60) prependOlder();     // reached the top -> re-hydrate older history from the buffer
});

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

const allMsgs = [];                          // full-session data buffer (cheap); the DOM stays a window over it
const HISTORY_BATCH = 100;                    // messages re-hydrated per scroll-to-top

function renderMsg(m){                        // build a message's DOM node (no placement) -- reused for live + history
  const from = m.from || 'system';
  const kind = m.kind || 'chat';
  const isGuard = /loop-guard/i.test(m.content||'');
  if(kind==='trace'){
    const d=document.createElement('div'); d.className='traceline';
    d.innerHTML='<span class="trav '+cls(from)+'">'+esc(from)+'</span><span class="trat">'+esc(m.content||'')+'</span>';
    return d;
  }
  if(from==='system' || kind==='note'){
    const d=document.createElement('div'); d.className='sys'+(isGuard?' guard':'');
    d.innerHTML='<span>'+esc(m.content||'')+'</span>'; return d;
  }
  const me = from==='user'; const c = cls(from);
  const wrap=document.createElement('div'); wrap.className='msg'+(me?' me':'');
  const hop = (m.meta && m.meta.hops)? '<span class="hop">hop '+m.meta.hops+'</span>':'';
  const intent = (m.meta && m.meta.intent)? '<span class="ib ib-'+m.meta.intent+'" title="'+esc(m.meta.why||'')+'">'+m.meta.intent+'</span>':'';
  wrap.innerHTML =
    '<div class="av '+c+'">'+initials(from)+'</div>'+
    '<div class="bubble"><div class="row"><span class="who '+c+'">'+esc(from)+'</span>'+
    '<span class="time">'+now(m.ts)+'</span>'+intent+hop+'</div>'+
    '<div class="content">'+_msgRenderer(m)+'</div></div>';
  return wrap;
}

function addMsg(m){
  if(m.id && m.id!=='0'){ if(seen.has(m.id)) return; seen.add(m.id); }
  if((m.kind||'chat')==='_ready') return;
  // negotiation verdict: display prominently
  const kind = m.kind||'chat';
  if(kind === 'verdict' || (kind === 'halt' && (m.meta||{}).intent === 'verdict')){
    const v = (m.meta||{}).verdict || 'amber';
    const emoji = {green:'✅', amber:'⚠️', red:'🛑'};
    const d = document.createElement('div');
    d.className = 'sys guard';
    d.innerHTML = '<span>'+(emoji[v]||'')+' Round '+v+': '+esc(m.content||'')+'</span>';
    _msgPlacer(d, m); autoscroll(); return;
  }
  const idx = allMsgs.push(m) - 1;           // buffer it (data), then render at the live tail
  const node = renderMsg(m); if(!node) return;
  node.dataset.mi = idx;
  _msgPlacer(node, m); autoscroll();
}

function prependOlder(){                       // scroll-to-top: re-hydrate older messages from the buffer
  const first = log.firstElementChild; if(!first || first.dataset.mi===undefined) return;
  const oldest = parseInt(first.dataset.mi);
  if(oldest<=0) return;                        // already at the start of the session
  const start = Math.max(0, oldest-HISTORY_BATCH);
  const h0 = log.scrollHeight, frag=document.createDocumentFragment();
  for(let i=start;i<oldest;i++){ const n=renderMsg(allMsgs[i]); if(n){ n.dataset.mi=i; frag.appendChild(n); } }
  log.insertBefore(frag, log.firstElementChild);
  log.scrollTop += (log.scrollHeight - h0);    // anchor the reader's view (prepended content pushes down, view stays put)
}
const MAX_LOG_NODES = 250;                  // bounded render window (Doom 'culling'): cap DOM so a long/bursty log never grows into lag
function trimLog(){
  // absolute ceiling (rare): never grow truly without bound even during a scrolled-up flood
  while(log.childElementCount > 2000) log.removeChild(log.firstElementChild);
  // tail window: at the live tail keep it lean (250); scrollback stays for reading history + re-hydration
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

// === HUD glanceability strip (who's-doing-what, always visible) ===
var _lastHudSig = null, _hudCollapsed = false;
function elapsedHUD(ts){
  if(!ts) return '';
  try{ var s=Math.floor((Date.now()-new Date(ts).getTime())/1000); }
  catch(e){ return ''; }
  if(s<10) return 'just now'; if(s<60) return s+'s'; if(s<3600) return (s/60).toFixed(1)+'m'; return (s/3600).toFixed(1)+'h';
}
function hudPriority(st){   // active verbs first, then idle — so the HUD sorts "doing stuff" to the top
  var o={thinking:0,reading:0,writing:0,searching:0,running:0,recalling:0,inspecting:0,working:0,idle:1};
  return o[st]!==undefined ? o[st] : 2;
}
function renderHUD(acts){
  // Feature flag: hide entirely when disabled (default ON)
  if (localStorage.getItem(hudFlagKey()) === '0') {
    var s = document.getElementById('hud');
    if (s) s.classList.remove('show');
    return;
  }
  var strip=document.getElementById('hud'), toggle=document.getElementById('hud-toggle');
  if(!strip) return;
  acts=acts||{};
  // fingerprint: only rebuild DOM when activity state actually changed
  var sig=JSON.stringify(acts);
  if(sig===_lastHudSig) return;
  _lastHudSig=sig;
  var entries=Object.keys(acts).filter(function(a){return acts[a]&&acts[a].state;}).map(function(a){
    var st=acts[a].state||'working', dt=acts[a].detail||'', ts=acts[a].ts||'';
    return {agent:a, state:st, detail:dt, since:ts, elapsed:elapsedHUD(ts), stale:ts&&(Date.now()-new Date(ts).getTime())>300000};
  });
  entries.sort(function(x,y){ return hudPriority(x.state)-hudPriority(y.state) || x.agent.localeCompare(y.agent); });
  if(!entries.length){ strip.classList.remove('show'); toggle.classList.remove('show'); strip.innerHTML=''; return; }
  strip.classList.add('show'); toggle.classList.add('show');
  // diff against current DOM to minimize rebuilds — same pattern as the roster
  var curIds=new Set(entries.map(function(e){return e.agent;}));
  [].slice.call(strip.children).forEach(function(el){
    if(el.dataset.agent && !curIds.has(el.dataset.agent)){ el.style.opacity='0'; el.style.transform='translateX(-10px)'; setTimeout(function(){el.remove();},220); }
  });
  entries.forEach(function(e,i){
    var el=strip.querySelector('[data-agent="'+esc(e.agent)+'"]');
    if(!el){ el=document.createElement('div'); el.className='hrow'; el.dataset.agent=e.agent; el.title=e.agent+' — click to expand'; strip.appendChild(el); }
    el.className='hrow'+(e.stale?' stale':'');
    el.innerHTML='<span class="hicon">'+(ICON[e.state]||'⚡')+'</span>'+
      '<span class="hagent '+cls(e.agent)+'">'+esc(e.agent)+'</span>'+
      '<span class="hverb">'+(VERB[e.state]||e.state)+'</span>'+
      '<span class="hdetail">'+esc(e.detail)+'</span>'+
      '<span class="helapsed">'+e.elapsed+'</span>';
    // click: expand slide deck cards (mini teaching slides)
    el.onclick=function(ev){ ev.stopPropagation();
      var was=el.classList.contains('expanded');
      [].forEach.call(strip.querySelectorAll('.hrow.expanded'),function(r){r.classList.remove('expanded');});
      if(!was){ showDeck(e.agent); setTarget(e.agent); }
      else { hideDeck(); }
    };
  });
  // reorder children to match sorted entries
  entries.forEach(function(e,i){ var el=strip.querySelector('[data-agent="'+esc(e.agent)+'"]'); if(el) strip.appendChild(el); });
  toggle.textContent=_hudCollapsed?'⌄ expand':'⌃ collapse';
}
function toggleHUD(){ _hudCollapsed=!_hudCollapsed; document.getElementById('hud').classList.toggle('collapsed',_hudCollapsed);
  document.getElementById('hud-toggle').textContent=_hudCollapsed?'⌄ expand':'⌃ collapse'; }
// click-away closes expanded hud rows + deck
document.addEventListener('click',function(e){
  var deck=document.getElementById('deck');
  document.querySelectorAll('.hrow.expanded').forEach(function(r){r.classList.remove('expanded');});
  if(deck && deck.classList.contains('show') && !deck.contains(e.target) && !e.target.closest('.hrow')){
    hideDeck();
  }
});

// === slide deck cards (mini teaching slides — click a HUD row to expand) ===
var _traceBuffer = {};   // {agent: [{kind, text, ts}]} — last 20 traces per agent
var _deckAgent = null, _deckPage = 0, _deckPaused = false, _deckTimer = null;
function bufferTrace(from, kind, text){
  if(!from) return;
  var buf = _traceBuffer[from] = _traceBuffer[from] || [];
  buf.push({kind:kind, text:text, ts:new Date().toISOString()});
  if(buf.length > 20) buf.shift();   // keep last 20 traces
}
function buildDeckCards(agent){
  var buf = _traceBuffer[agent] || [];
  var act = null;   // current activity from the last /status poll
  try { act = JSON.parse(JSON.stringify((_lastHudSig ? JSON.parse(_lastHudSig) : {})[agent] || null)); } catch(e){}
  var cards = [];
  // Card 1: WHAT — current activity
  if(act && act.state){
    var st = act.state, dt = act.detail || '', ic = ICON[st] || '⚡', vb = VERB[st] || st;
    var elapsed = act.ts ? elapsedHUD(act.ts) : '';
    cards.push({
      icon: ic, title: vb.charAt(0).toUpperCase() + vb.slice(1),
      body: '<b>'+esc(agent)+'</b> is <b>'+esc(vb)+'</b>'+
        (dt?' <code>'+esc(dt)+'</code>':'')+
        (elapsed?'<br><span style="color:var(--faint);font-size:11px">'+elapsed+' elapsed</span>':''),
      result: null
    });
  }
  // Card 2: WHY — most recent thinking traces
  var thoughts = buf.filter(function(t){ return t.kind === 'thinking' || t.text.indexOf('💭')>=0; }).slice(-3);
  if(thoughts.length){
    var thoughtText = thoughts.map(function(t){ return t.text.replace(/^💭\s*/,''); }).join('<br><br>');
    cards.push({
      icon: '💭', title: 'Reasoning',
      body: '<span style="font-style:italic;color:var(--muted)">'+esc(thoughtText.slice(0,300))+'</span>',
      result: null
    });
  }
  // Card 3: RESULT — most recent tool traces
  var tools = buf.filter(function(t){ return t.kind === 'tool' || (t.text.indexOf('🔧')>=0 || t.text.indexOf('📖')>=0 || t.text.indexOf('✍️')>=0 || t.text.indexOf('⚙️')>=0); }).slice(-5);
  if(tools.length){
    var toolList = tools.map(function(t){ return '<span style="color:var(--faint);font-size:12px">'+esc(t.text.slice(0,120))+'</span>'; }).join('<br>');
    var resultClass = 'good';   // infer result: if last tool looks successful, mark good
    cards.push({
      icon: '✅', title: 'Recent Actions',
      body: toolList,
      result: {text: tools.length+' action'+(tools.length>1?'s':'')+' in the last few minutes', cls: resultClass}
    });
  }
  // Fallback: always at least one card
  if(!cards.length){
    cards.push({icon:'💤', title:'Idle', body:'<b>'+esc(agent)+'</b> is currently idle — no recent activity.', result:null});
  }
  return cards;
}
function showDeck(agent){
  _deckAgent = agent; _deckPage = 0; _deckPaused = false;
  renderDeck();
  document.getElementById('deck').classList.add('show');
  _startDeckTimer();
  // Highlight the HUD row
  document.querySelectorAll('.hrow.expanded').forEach(function(r){r.classList.remove('expanded');});
  var row = document.querySelector('.hrow[data-agent="'+esc(agent)+'"]');
  if(row) row.classList.add('expanded');
}
function hideDeck(){
  document.getElementById('deck').classList.remove('show');
  _deckAgent = null; _deckPage = 0;
  if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
}
function renderDeck(){
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  var container = document.getElementById('deckCards');
  var dots = document.getElementById('deckDots');
  if(!container) return;
  container.innerHTML = cards.map(function(c,i){
    var resultHtml = c.result ? '<div class="sc-result '+c.result.cls+'">'+c.result.text+'</div>' : '';
    return '<div class="slide-card"><div class="sc-head"><span class="sc-icon">'+c.icon+'</span><span class="sc-title">'+esc(c.title)+'</span></div><div class="sc-body">'+c.body+'</div>'+resultHtml+'</div>';
  }).join('');
  // dots
  dots.innerHTML = cards.map(function(_,i){
    return '<span class="slide-dot'+(i===_deckPage?' active':'')+'" onclick="deckGo('+i+')"></span>';
  }).join('');
  // position cards
  container.style.transform = 'translateX(-' + (_deckPage * 100) + '%)';
  // prev/next state
  var prevBtn = document.getElementById('deckPrev'), nextBtn = document.getElementById('deckNext');
  if(prevBtn) prevBtn.style.opacity = _deckPage === 0 ? '0.3' : '1';
  if(nextBtn) nextBtn.style.opacity = _deckPage >= cards.length-1 ? '0.3' : '1';
}
function deckGo(n){
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  if(n < 0 || n >= cards.length) return;
  _deckPage = n; renderDeck(); _startDeckTimer();
}
function deckNext(){ deckGo(_deckPage + 1); }
function deckPrev(){ deckGo(_deckPage - 1); }
function deckTogglePause(){
  _deckPaused = !_deckPaused;
  var btn = document.getElementById('deckPause');
  if(btn){ btn.textContent = _deckPaused ? '▶ play' : '⏸ pause'; btn.classList.toggle('paused', _deckPaused); }
  if(!_deckPaused) _startDeckTimer(); else if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
}
function _startDeckTimer(){
  if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
  if(_deckPaused) return;
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  if(_deckPage < cards.length-1){
    _deckTimer = setTimeout(function(){ deckNext(); }, 4500);
  }
}
// Intercept trace messages to build the buffer — called from addMsg
function _captureTrace(msg){
  var from = msg.from || '';
  if(!from || from==='system' || from==='user') return;
  bufferTrace(from, msg.kind||'trace', msg.content||'');
}
// Hook into addMsg to capture traces
var _origAddMsg = addMsg;
addMsg = function(m){
  if((m.kind||'chat')==='trace') _captureTrace(m);
  return _origAddMsg(m);
};

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
  // Smart negotiation: coordinate only when a collision is actually possible, speak only
  // when it finds one. A round fires only if >=2 agents are online (one agent can't collide),
  // and the verdict is surfaced only when it's amber/red (a real scope conflict). Green rounds
  // close silently -- coordination is a background safety net, not a per-message nag.
  // (inform/chat only; steer/interrupt/halt are already explicit, targeted acts.)
  if((fidelity === 'inform' || fidelity === 'chat') && _onlineAgents.length >= 2){
    fetch('/negotiate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})}).then(r => r.json()).then(v => {
      if(v && v.verdict && v.verdict !== 'green'){
        const emoji = {amber:'⚠️', red:'🛑'};
        toast((emoji[v.verdict]||'') + ' Round: ' + v.verdict + ' — ' + (v.reason||''));
      }
    }).catch(()=>{});
  }
}

// --- Slice 2: animated recipient selector (state = who you're messaging; last-messaged persists) ---
var _recips = ['all'];                          // ['all'] (broadcast) or a list of agent ids
var _onlineAgents = [];                         // bus agents currently online (excludes 'user'); gates the smart negotiation round
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
var _lastRosterSig = '';   // fingerprint cache: only rebuild DOM when agent state actually changed

function applyStatus(s){
  paused = !!s.paused;
  const b=document.getElementById('pauseBtn'), banner=document.getElementById('banner');
  b.textContent = paused ? '▶ Resume' : '⏸ Pause';
  b.classList.toggle('paused', paused);
  banner.classList.toggle('show', paused);
  // show WHO paused and WHY (the pause_status carries {by, reason, ts})
  var ps = s.pause || {};
  banner.innerHTML = paused
    ? '⏸ Paused' + (ps.by ? ' by <b>'+esc(ps.by)+'</b>' : '') + (ps.reason ? ' — '+esc(ps.reason) : '') + ' · the agents are frozen. Type below to interject, then Resume.'
    : '⏸ Paused — the agents are frozen. Type below to interject, then Resume.';
  // dynamic roster: UNION of ACL-registered + currently-online agents.
  const agents=(s.agents||[]).map(a=>a.agent).filter(Boolean);
  _onlineAgents = agents.slice();               // stash for send()'s smart-negotiation gate
  const known=s.known||[];
  const roster=[...new Set([...known, ...agents, 'user'])];
  const sig=s.signals||{};
  const onlineSet=new Set(agents);
  const isKnown=new Set(known);

  // Build fingerprint: roster order + each agent's online/steer/nudge state.
  // Only rebuild DOM when this actually changed (was doing innerHTML on every 1.2s poll).
  var newSig = roster.join(',') + '|' + roster.map(function(a){
    var g=sig[a]||{};
    return a+':'+(onlineSet.has(a)||a==='user'?'1':'0')+':'+(g.steer_pending||0)+':'+(g.nudged?'1':'0');
  }).join(';');

  if(newSig !== _lastRosterSig){
    _lastRosterSig = newSig;
    const pills=document.getElementById('pills');
    pills.innerHTML = roster.map(a=>{
      const g=sig[a]||{};
      const isOnline=onlineSet.has(a)||a==='user';
      const unknown=!isKnown.has(a) && a!=='user';
      const hd=(s.halted||{})[a];   // {by, reason, ts} when this agent is under a targeted halt
      const halt = hd?'<span title="'+esc(hd.reason||'no reason given')+(hd.ts?'  ('+esc(hd.ts)+')':'')+'" style="color:var(--danger);font-size:10.5px;font-weight:600;margin-left:5px">⏸ halted by '+esc(hd.by||'?')+'</span>':'';
      const marks=halt
                +(g.steer_pending?'<span class="sig steer" title="steer facts queued">↝'+g.steer_pending+'</span>':'')
                +(g.nudged?'<span class="sig nudge" title="interrupt pending">⚡</span>':'')
                +(unknown?' <span title="online but not ACL-registered — security onboarding cue" style="color:var(--amber);font-size:11px">⚠ unknown</span>':'');
      return '<div class="pill'+(isOnline?' on':' off')+'" onclick="setTarget(\''+esc(a)+'\')" title="click to message '+esc(a)+(unknown?' (unregistered)':'')+'"><span class="dot"></span>'+esc(a)+(isOnline?'':' 💤')+marks+'</div>';
    }).join('');
  }
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
  renderHUD(s.activities||{});
  syncAuroraState(paused, Object.keys(s.halted||{}).length);
  refreshNarrButtons(s.narration || 'key');
  // renderRecipient() removed from poll loop — the recipient chip only changes on explicit user action
  // (roster click / setTarget). Calling it every 1.2s was doing getBoundingClientRect() layout thrash.
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
    window._glassCardData=_glassCardData; window._lastActs=s.activities||{};   // cache for standalone tile variants
    if(_activeVariant.tile==='presence' && window.renderPresence) window.renderPresence(_glassCardData, window._lastActs);
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

// ---- Aurora Glass shader integration (progressive enhancement, feature-flagged) ----
var _auroraShader = null;
var _auroraEnabled = false;
function auroraFlagKey(){ return 'bifrost_aurora_shader'; }
function hudFlagKey(){ return 'bifrost_hud_strip'; }
function initAurora(){
  if (!window.AuroraGlass || !window.AuroraGlass.isSupported()) return false;
  if (_auroraShader) return true;   // already running
  try {
    var canvas = document.getElementById('aurora-canvas');
    if (!canvas) return false;
    _auroraShader = new window.AuroraGlass.AuroraShader(canvas);
    _auroraShader.start();
    // Kill the CSS fallback (body::before conic blur) — the shader is the light bed now
    var ss = document.createElement('style');
    ss.id = 'aurora-fallback-hide';
    ss.textContent = 'body::before{display:none}';
    document.head.appendChild(ss);
    _auroraEnabled = true;
    localStorage.setItem(auroraFlagKey(), '1');
    return true;
  } catch(e) { return false; }
}
function stopAurora(){
  if (!_auroraShader) return;
  _auroraShader.destroy();
  _auroraShader = null;
  _auroraEnabled = false;
  localStorage.setItem(auroraFlagKey(), '0');
  // Restore the CSS fallback
  var ss = document.getElementById('aurora-fallback-hide');
  if (ss) ss.remove();
}
function toggleAuroraFlag(){
  if (_auroraEnabled) stopAurora();
  else { if (!initAurora()) { toast('aurora shader unavailable — WebGL2 or benchmark required'); return; } }
  refreshAuroraButtons();
}
function refreshAuroraButtons(){
  var btn = document.getElementById('auroraToggle');
  var st = document.getElementById('auroraStatus');
  if (!btn) return;
  btn.textContent = _auroraEnabled ? 'Disable' : 'Enable';
  if (st) st.textContent = _auroraEnabled ? 'on — animated aurora active' : 'off — run bench-aurora.html first';
}
// Auto-start if previously enabled (user opted in and benchmark passed)
(function(){
  var stored = localStorage.getItem(auroraFlagKey());
  if (stored !== '0') { initAurora(); }   // default ON — the shock factor shouldn't be hidden; isSupported() + fps fallback guard it
  refreshAuroraButtons();
})();

// HUD strip feature flag (default ON — pure DOM, no perf risk)
function toggleHUDFlag(){
  var hud = document.getElementById('hud');
  var cur = localStorage.getItem(hudFlagKey()) !== '0';   // default '1' if unset
  var next = !cur;
  localStorage.setItem(hudFlagKey(), next ? '1' : '0');
  if (!next && hud) { hud.classList.remove('show'); }
  refreshHUDButtons();
  // Force a re-render on the next poll so the HUD reappears
  _lastHudSig = null;
}
function refreshHUDButtons(){
  var btn = document.getElementById('hudToggle');
  var st = document.getElementById('hudStatus');
  if (!btn) return;
  var on = localStorage.getItem(hudFlagKey()) !== '0';
  btn.textContent = on ? 'Disable' : 'Enable';
  if (st) st.textContent = on ? 'on — pure DOM, no perf cost' : 'off — hidden';
}
(function(){ refreshHUDButtons(); })();

// Shaderpark controls: aurora speed + intensity sliders (live-tune uniforms, localStorage persistence)
function auroraSpeedKey(){ return 'bifrost_aurora_speed'; }
function auroraIntensityKey(){ return 'bifrost_aurora_intensity'; }
function setAuroraSpeed(v){
  if (_auroraShader) _auroraShader.setSpeed(v);
  localStorage.setItem(auroraSpeedKey(), v);
  var lbl = document.getElementById('auroraSpeedLabel');
  if (lbl) lbl.textContent = v.toFixed(2) + '×';
}
function setAuroraIntensity(v){
  if (_auroraShader) _auroraShader.setIntensity(v);
  localStorage.setItem(auroraIntensityKey(), v);
  var lbl = document.getElementById('auroraIntensityLabel');
  if (lbl) lbl.textContent = v.toFixed(2);
}
function refreshAuroraParams(){
  var speedSlider = document.getElementById('auroraSpeedSlider');
  var intSlider = document.getElementById('auroraIntensitySlider');
  var speedRow = document.getElementById('auroraSpeedRow');
  var intRow = document.getElementById('auroraIntensityRow');
  if (!speedSlider || !intSlider) return;
  // Show sliders only when aurora is enabled
  var on = _auroraEnabled;
  if (speedRow) speedRow.style.display = on ? '' : 'none';
  if (intRow) intRow.style.display = on ? '' : 'none';
  if (!on) return;
  // Restore persisted values
  var sp = parseFloat(localStorage.getItem(auroraSpeedKey())) || 1;
  var it = parseFloat(localStorage.getItem(auroraIntensityKey())) || 0.85;
  speedSlider.value = sp; setAuroraSpeed(sp);
  intSlider.value = it; setAuroraIntensity(it);
}
// Wire into toggleAuroraFlag + initAurora so sliders appear/disappear
(function(){
  var _origToggle = toggleAuroraFlag;
  toggleAuroraFlag = function(){
    _origToggle();
    refreshAuroraParams();
  };
  var _origInit = initAurora;
  initAurora = function(){
    var ok = _origInit();
    if (ok) {
      // Apply persisted speed/intensity to the new shader
      var sp = parseFloat(localStorage.getItem(auroraSpeedKey())) || 1;
      var it = parseFloat(localStorage.getItem(auroraIntensityKey())) || 0.85;
      if (_auroraShader) { _auroraShader.setSpeed(sp); _auroraShader.setIntensity(it); }
    }
    refreshAuroraParams();
    return ok;
  };
  // Initial state
  refreshAuroraParams();
})();

// Wire setState into the status loop. Called at the end of applyStatus.
function syncAuroraState(paused, haltedCount) {
  if (!_auroraShader) return;
  if (haltedCount > 0) _auroraShader.setState(2);           // any agent halted -> desaturate
  else if (paused)     _auroraShader.setState(1);           // global pause -> amber tint
  else                 _auroraShader.setState(0);           // normal
}

// ---- Narration toggle (claude reasoning visibility: off|key|full) ----
var NARR_LABELS = {off:'off — silent', key:'key — decision points only', full:'full — stream all reasoning'};
async function setNarration(level){
  try {
    var r = await fetch('/narration', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({level:level})});
    var j = await r.json();
    if (j && j.ok) {
      refreshNarrButtons(level);
      toast('\u{1f4ad} narration: ' + level);
    }
  } catch(e) { toast('narration toggle failed — bus offline?'); }
}
function refreshNarrButtons(level){
  [].forEach.call(document.querySelectorAll('.narr-btn'), function(b){
    b.classList.toggle('active', b.dataset.lvl === level);
  });
  var st = document.getElementById('narrStatus');
  if (st) st.textContent = NARR_LABELS[level] || level;
}

// ---- Viz-canvas engine: slide-deck cards between aurora and cockpit ----
var _vizEngine = null, _vizVisible = false, _vizDeckMode = false;
function initViz(){
  if (!window.BifrostViz) return false;
  if (_vizEngine) return true;
  try {
    var canvas = document.getElementById('viz-canvas');
    if (!canvas) return false;
    _vizEngine = new window.BifrostViz.VizEngine(canvas);
    _vizEngine.onChange(function(info){
      updateVizLabel();
      if (info) {
        var lbl = document.getElementById('vizLabel');
        if (lbl) lbl.textContent = info.gridMode ? 'grid' : (info.idx + 1) + '/' + info.total + ' ' + (info.label || '');
        document.getElementById('vizGridBtn').classList.toggle('on', info.gridMode);
        document.getElementById('vizDeckBtn').classList.toggle('on', info.deckMode);
        document.getElementById('vizBtn').classList.toggle('active', _vizVisible);
      }
    });
    _vizEngine.start();
    return true;
  } catch(e) { return false; }
}
function vizToggle(){
  if (!_vizEngine && !initViz()) return;
  _vizVisible = !_vizVisible;
  document.getElementById('viz-canvas').classList.toggle('show', _vizVisible);
  document.getElementById('viz-ctl').classList.toggle('show', _vizVisible);
  document.getElementById('vizBtn').classList.toggle('active', _vizVisible);
  if (!_vizVisible) setVizDeckMode(false); // exit deck mode when hiding
  if (_vizVisible) updateVizLabel();
}
function vizNext(){ if(_vizEngine){ _vizEngine.nextCard(); } }
function vizPrev(){ if(_vizEngine){ _vizEngine.prevCard(); } }
function vizGrid(){ if(_vizEngine){ _vizEngine.showGrid(); } }
function vizDeckMode(){
  if (!_vizEngine) return;
  setVizDeckMode(!_vizDeckMode);
}
function setVizDeckMode(on){
  _vizDeckMode = !!on;
  if (_vizEngine) _vizEngine.setDeckMode(_vizDeckMode);
  document.getElementById('vizDeckBtn').classList.toggle('on', _vizDeckMode);
  // Deck mode: shrink log + activity, expand viz canvas to fill the cockpit area
  var log = document.getElementById('log');
  var act = document.getElementById('activity');
  var viz = document.getElementById('viz-canvas');
  if (_vizDeckMode) {
    if (log) log.style.maxHeight = '140px';
    if (act) act.style.display = 'none';
    if (viz) viz.style.inset = '56px 0 120px 0';  // under header, above composer
  } else {
    if (log) log.style.maxHeight = '';
    if (act) act.style.display = '';
    if (viz) viz.style.inset = '0';
  }
}
function updateVizLabel(){
  if (!_vizEngine) return;
  var info = _vizEngine.cardInfo();
  var lbl = document.getElementById('vizLabel');
  if (lbl && info) lbl.textContent = info.gridMode ? 'grid' : (info.idx + 1) + '/' + info.total + ' ' + (info.label || '');
  // Also update the header button
  var hbtn = document.getElementById('vizBtn');
  if (hbtn && info && _vizVisible) hbtn.textContent = '\u{1f4ca} ' + (info.label || 'Deck');
  else if (hbtn) hbtn.textContent = '\u{1f4ca} Deck';
}
// Feed traces + edges to viz engine — ALWAYS collect data, even when hidden
(function(){
  var _origAddMsg = addMsg;
  addMsg = function(m){
    _origAddMsg(m);
    if (_vizEngine) {
      if (m.kind === 'trace') _vizEngine.feedTrace(m);
      if (m.kind === 'chat' && m.from && m.to && m.to !== 'all' && m.to !== '*') {
        _vizEngine.feedEdge(m.from, m.to);
      }
    }
  };
  // Also feed edges from the send() function (user -> agent messages)
  var _origSend = send;
  send = function(){
    var text = (document.getElementById('input')||{}).value || '';
    var target = (document.getElementById('target')||{}).value || 'all';
    if (_vizEngine && text.trim() && target !== 'all') {
      _vizEngine.feedEdge('user', target);
    }
    return _origSend();
  };
})();
// Keyboard: v=toggle, arrows=navigate, g=grid, d=deck-mode, Escape=hide
document.addEventListener('keydown', function(e){
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if (e.key === 'v' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); vizToggle(); }
  if (e.key === 'Escape' && _vizVisible) { e.preventDefault(); vizToggle(); }
  if (_vizVisible && _vizEngine) {
    if (e.key === 'ArrowRight') { e.preventDefault(); vizNext(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); vizPrev(); }
    if (e.key === 'g' && !e.ctrlKey) { e.preventDefault(); vizGrid(); }
    if (e.key === 'd' && !e.ctrlKey) { e.preventDefault(); vizDeckMode(); }
  }
});
initViz();
</script>
<script src="/theme-void.js"></script>
<script src="/presence-rail.js"></script>
<script src="/presence-cloud.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
