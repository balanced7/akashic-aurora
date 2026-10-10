import itertools
import json
import socket

_ids = itertools.count(1)


def call(sock_path, method, **params):
    s = socket.socket(socket.AF_UNIX)
    s.connect(sock_path)
    s.sendall((json.dumps({"jsonrpc": "2.0", "id": next(_ids), "method": method, "params": params}) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(1 << 20)
        if not chunk:
            break
        buf += chunk
    s.close()
    r = json.loads(buf)
    if "error" in r:
        raise RuntimeError(f"{method}: {r['error']}")
    return r["result"]
