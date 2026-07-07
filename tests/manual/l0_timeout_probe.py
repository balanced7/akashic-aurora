"""
Empirical test of the L0 assumption: does the OpenAI SDK `timeout=` actually
abort a STREAMING read that hangs (a) before any bytes and (b) mid-stream?

Reproduces the runner's exact pattern: OpenAI(base_url=...), chat.completions.create(stream=True),
`for chunk in stream`. Points base_url at a server that sends 200 + SSE headers then sleeps.
A worker thread runs the call with a hard outer cap; if the thread is still alive past the cap,
the SDK timeout did NOT work (real-world wedge unrecoverable in-process).
"""
import json, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from openai import OpenAI

MODE = {"v": "nodata"}  # "nodata" | "midstream"

def _chunk(text):
    return "data: " + json.dumps({
        "id": "x", "object": "chat.completion.chunk", "created": 0, "model": "m",
        "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]
    }) + "\n\n"

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        try: self.rfile.read(length)
        except Exception: pass
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        if MODE["v"] == "midstream":
            try:
                self.wfile.write(_chunk("hello").encode()); self.wfile.flush()
            except Exception: return
        time.sleep(600)  # STALL: server never finishes the response

srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
print(f"stall server on 127.0.0.1:{PORT}")

def run_case(name, mode, timeout, cap=15.0):
    MODE["v"] = mode
    box = {}
    def work():
        kw = dict(api_key="sk-test", base_url=f"http://127.0.0.1:{PORT}", max_retries=0)
        if timeout is not None:
            kw["timeout"] = timeout
        client = OpenAI(**kw)
        t0 = time.time()
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "hi"}],
                stream=True,
            )
            for _ in stream:
                pass
            box["r"] = "COMPLETED (no exception)"
        except Exception as e:
            box["r"] = f"{type(e).__name__}: {str(e)[:120]}"
        box["elapsed"] = time.time() - t0
    th = threading.Thread(target=work, daemon=True)
    t0 = time.time()
    th.start()
    th.join(cap)
    if th.is_alive():
        print(f"[{name}] mode={mode} timeout={timeout}: *** HUNG past {cap}s — timeout did NOT abort the read ***")
        return False
    print(f"[{name}] mode={mode} timeout={timeout}: aborted in {box.get('elapsed',0):.2f}s -> {box.get('r')}")
    return True

print("\n--- Q1: does timeout=3 abort a stall BEFORE any bytes? ---")
run_case("A", "nodata", 3.0)
print("\n--- Q2: does timeout=3 abort a stall MID-STREAM (the realistic wedge)? ---")
run_case("B", "midstream", 3.0)
print("\n--- Q3: control — NO timeout (current runner) on the same mid-stream stall ---")
run_case("C", "midstream", None, cap=12.0)
print("\ndone.")
