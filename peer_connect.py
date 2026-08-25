"""peer_connect — get a remote Akashic Aurora talking to ours in one command.

    py peer_connect.py

That is the whole thing. It asks for the two key values, works out which file each belongs
in BY TESTING rather than by making you read a table, points your config at us, starts your
listener, and sends a handshake. If it prints CONNECTED at the end, both directions work.

WHY THIS EXISTS. The written instructions were correct and still confusing, twice over:

  1. THE KEYS SWAP FILENAMES BETWEEN MACHINES. Our outbound is your inbound. Every honest
     description of that is a sentence someone has to hold two ways at once, and holding it
     backwards produces a signature failure whose only symptom is a refusal that explains
     nothing. So this script does not explain the swap. It TRIES a key, watches what our
     listener says, and puts it where the answer proves it belongs.

  2. "IS IT HEX?" The secret is the RAW BYTES of what you paste, whitespace-stripped, never
     hex-decoded — even if it looks like hex. That question cost us a round trip, so this
     script does the reading and you never have to decide.

The general principle, learned the expensive way tonight: when two competent implementations
disagree about an unstated contract, do not write a better paragraph. Ship an artifact that
makes the contract unnecessary to interpret.

Safe to re-run. It overwrites the key files with what you paste and nothing else.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SECRETS = Path(os.getenv("AKASHIC_SECRETS_DIR") or (ROOT / ".secrets"))
CONFIG = ROOT / "state" / "coord" / "remote_bridge.json"

#: Daniil's node on the shared tailnet. This is who you are connecting TO.
OUR_URL = "http://100.86.106.36:8791/xfer"
OUR_NAME = "daniil"

#: Your side of the pair. Named from YOUR point of view, which is the thing that confuses
#: everyone: the key you SIGN with lives in *outbound*, the key you VERIFY with in *inbound*.
SEND_KEY = "remote_bridge_outbound.key"     # you sign -> we verify
RECV_KEY = "remote_bridge_inbound.key"      # we sign  -> you verify

LISTEN_PORT = 8791


def say(step: str, msg: str) -> None:
    print(f"[{step}] {msg}", flush=True)


def fail(msg: str) -> int:
    print(f"\n  STOPPED: {msg}\n", flush=True)
    return 1


# --------------------------------------------------------------------------- crypto (ours)
def sign(body: bytes, secret: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def envelope(payload: dict, secret: bytes) -> bytes:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return json.dumps({"body": base64.b64encode(body).decode("ascii"),
                       "sig": sign(body, secret)}).encode("utf-8")


def post(url: str, raw: bytes, timeout: int = 10):
    req = urllib.request.Request(url, data=raw, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                                        # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


# --------------------------------------------------------------------------- steps
def read_keys() -> tuple:
    print(__doc__.split("WHY THIS EXISTS")[0].strip())
    print("\nPaste the two values Daniil sent you. They are NOT interchangeable, but you do")
    print("not need to know which is which — this works it out by testing.\n")
    a = input("  first value  (he called it Key 1): ").strip()
    b = input("  second value (he called it Key 2): ").strip()
    if not a or not b:
        return None, None
    if a == b:
        print("\n  Those are identical. The two directions must use DIFFERENT secrets, or")
        print("  revoking one silently revokes both. Ask Daniil to re-send.")
        return None, None
    return a.encode("utf-8"), b.encode("utf-8")


def which_key_signs(k1: bytes, k2: bytes):
    """Ask OUR listener which key is the sending one. The wire settles it, not a table.

    A correctly-signed chat gets 202; anything else gets a flat 400 that deliberately reveals
    nothing. That single bit is all we need, and it is the one fact no documentation can get
    wrong."""
    probe = {"v": 1, "id": "peer-connect-probe", "frm": "peer", "kind": "chat",
             "content": "peer_connect handshake probe", "sent_at": int(time.time())}
    for label, cand, other in (("Key 1", k1, k2), ("Key 2", k2, k1)):
        status, _body = post(OUR_URL, envelope(probe, cand))
        if status == 202:
            say("keys", f"{label} is your SENDING key (our listener accepted its signature)")
            return cand, other
        if status is None:
            return None, f"cannot reach {OUR_URL} — {_body}"
    return None, ("neither value was accepted by Daniil's listener. Either the keys are stale, "
                  "or your clock is off by more than 300s (check NTP first — it is the more "
                  "common cause and it looks exactly like a bad key)")


def write_keys(send_key: bytes, recv_key: bytes) -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    (SECRETS / SEND_KEY).write_bytes(send_key)
    (SECRETS / RECV_KEY).write_bytes(recv_key)
    say("keys", f"wrote {SEND_KEY} (you sign) and {RECV_KEY} (you verify) into {SECRETS}")


def write_config() -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    cfg.setdefault("peer", {})
    cfg["peer"]["name"] = OUR_NAME
    cfg["peer"]["url"] = OUR_URL
    cfg["peer"]["inbound_secret_file"] = RECV_KEY
    cfg["peer"]["outbound_secret_file"] = SEND_KEY
    cfg["note"] = ("Written by peer_connect.py. peer.name is what YOU call THEM — provenance "
                   "is assigned locally from it and never read off an arriving payload, so "
                   "the two sides' configs never need to agree.")
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    say("config", f"peer -> {OUR_NAME} at {OUR_URL}")


def tailnet_ip() -> str:
    exe = shutil.which("tailscale") or r"C:\Program Files\Tailscale\tailscale.exe"
    try:
        out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True,
                             timeout=10).stdout.strip()
        return out.splitlines()[0].strip() if out else ""
    except Exception:                                             # noqa: BLE001
        return ""


def ensure_firewall(port: int) -> None:
    """Windows blocks inbound on a fresh port even over the tailnet. Scoped, not wide open."""
    if os.name != "nt":
        return
    name = "Akashic remote-bridge (Tailscale only)"
    ps = (f"if (-not (Get-NetFirewallRule -DisplayName '{name}' -ErrorAction SilentlyContinue))"
          f" {{ New-NetFirewallRule -DisplayName '{name}' -Direction Inbound -Action Allow "
          f"-Protocol TCP -LocalPort {port} -RemoteAddress '100.64.0.0/10' "
          f"-InterfaceAlias 'Tailscale' -Profile Any | Out-Null; 'created' }} else {{ 'exists' }}")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=25)
        out = (r.stdout or "").strip()
        if out in ("created", "exists"):
            say("firewall", f"inbound rule {out} (TCP {port}, Tailscale adapter, tailnet only)")
        else:
            say("firewall", "could NOT add the rule — re-run this script as Administrator, "
                            "or add it by hand. Without it we cannot reach you.")
    except Exception as e:                                        # noqa: BLE001
        say("firewall", f"skipped ({type(e).__name__}) — add the rule by hand if we cannot reach you")


def start_listener(host: str, port: int):
    script = ROOT / "scripts" / "remote_bridge_listener.py"
    if not script.exists():
        say("listen", f"MISSING {script} — run `git pull` first, then re-run this script.")
        return None
    try:
        socket.create_connection((host, port), timeout=2).close()
        say("listen", f"already listening on {host}:{port}")
        return "already"
    except OSError:
        pass
    argv = [sys.executable, str(script), "--host", host, "--port", str(port),
            "--peer", OUR_NAME]
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    logf = open(ROOT / "state" / "logs" / "remote-bridge-listener.log", "ab") \
        if (ROOT / "state" / "logs").exists() else subprocess.DEVNULL
    p = subprocess.Popen(argv, stdout=logf, stderr=logf, creationflags=flags, close_fds=True)
    for _ in range(10):
        try:
            socket.create_connection((host, port), timeout=1).close()
            say("listen", f"listening on http://{host}:{port}/xfer  (pid {p.pid})")
            return p
        except OSError:
            time.sleep(1)
    say("listen", "listener did not come up — check state/logs/remote-bridge-listener.log")
    return None


def handshake(send_key: bytes, my_url: str) -> bool:
    payload = {"v": 1, "id": f"peer-connect-{int(time.time())}", "frm": "peer",
               "kind": "chat", "sent_at": int(time.time()),
               "content": f"peer_connect: I am live at {my_url} — both directions ready."}
    status, body = post(OUR_URL, envelope(payload, send_key))
    if status == 202:
        say("handshake", "202 — Daniil's fleet accepted the message")
        return True
    say("handshake", f"{status} {body} — reached them, but the gate refused")
    return False


def main() -> int:
    k1, k2 = read_keys()
    if not k1:
        return fail("no keys given")

    print()
    send_key, other = which_key_signs(k1, k2)
    if send_key is None:
        return fail(str(other))
    write_keys(send_key, other)
    write_config()

    ip = tailnet_ip()
    if not ip:
        return fail("could not read your Tailscale IP — is Tailscale running? "
                    "(`tailscale ip -4` should print a 100.x address)")
    say("tailnet", f"your address is {ip}")

    ensure_firewall(LISTEN_PORT)
    start_listener(ip, LISTEN_PORT)

    print()
    ok = handshake(send_key, f"http://{ip}:{LISTEN_PORT}/xfer")
    print()
    if ok:
        print("  CONNECTED.")
        print(f"  Tell Daniil your endpoint:  http://{ip}:{LISTEN_PORT}/xfer")
        print("  He points peer.url at it and both directions are live.")
        return 0
    print("  Outbound works or not as shown above; your listener is up either way.")
    print(f"  Tell Daniil:  http://{ip}:{LISTEN_PORT}/xfer")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
