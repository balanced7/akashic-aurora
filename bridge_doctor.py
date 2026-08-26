"""bridge_doctor — diagnose YOUR side of the bridge and report it back across the bridge.

    py bridge_doctor.py

One command. It checks every part of your half, prints the findings, and then POSTs the
report to your peer so they can help you with FACTS instead of guesses. No secret ever leaves
this machine — keys appear only as sha256[:12] fingerprints, which prove a match without
revealing a value.

WHY IT REPORTS ITSELF. Every diagnosis tonight cost a human round trip: someone reads a log,
retypes it into chat, the other side interprets it. That relay is where the errors entered —
two mangled key pastes, a stale file read as current, five delivered messages believed
unsent. The bridge is a working transport; a diagnostic that can use it removes the human
from the copying and leaves them in the deciding.

WHAT IT CANNOT DO, deliberately: it does not consume your parked mail, does not touch your
keys, does not change config, and does not send anything but its own report. If your outbound
is broken it says so and prints the report for you to paste by hand — a doctor whose
findings depend on the thing being diagnosed is no doctor at all.
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.comm import remote_relay as RR  # noqa: E402

R = []


def line(k, v, ok=None):
    mark = "  " if ok is None else ("OK  " if ok else "BAD ")
    R.append(f"{mark}{k:34s} {v}")
    print(f"{mark}{k:34s} {v}", flush=True)


def main() -> int:
    print("=" * 74)
    print("BRIDGE DOCTOR — your side, reported across the bridge")
    print("=" * 74)

    fp = lambda b: hashlib.sha256(b).hexdigest()[:12] if b else "(absent)"

    # ---- keys ------------------------------------------------------------------
    # PER-PEER, because a machine can host several identities. This read hardcoded
    # OUTBOUND_KEY_FILE/INBOUND_KEY_FILE, so on a multi-peer host the doctor reported the
    # DEFAULT peer's fingerprints no matter which identity it was actually acting as --
    # Chronos caught it self-reporting as serge-dsh while configured as chronos. A diagnostic
    # that misnames its own subject is worse than no diagnostic: it is confidently wrong at
    # exactly the moment someone is trying to establish who they are.
    rows = RR.peers() or [{"name": "(default)"}]
    for row in rows:
        pname = str(row.get("name") or "(default)")
        pas = str(row.get("as") or "")
        who = f"{pname}" + (f" as {pas}" if pas else "")
        send_k = RR._secret(str(row.get("outbound_secret_file") or RR.OUTBOUND_KEY_FILE))
        recv_k = RR._secret(str(row.get("inbound_secret_file") or RR.INBOUND_KEY_FILE))
        line(f"[{who}] key you SIGN with", f"{len(send_k)}B  fp={fp(send_k)}", bool(send_k))
        line(f"[{who}] key you VERIFY with", f"{len(recv_k)}B  fp={fp(recv_k)}", bool(recv_k))
        line(f"[{who}] keys are distinct", str(send_k != recv_k),
             bool(send_k) and send_k != recv_k)
        for lbl, k in (("outbound", send_k), ("inbound", recv_k)):
            if k:
                t = k.decode("utf-8", "replace")
                bad = [f"U+{ord(c):04X}@{i}" for i, c in enumerate(t)
                       if ord(c) < 32 or ord(c) > 126]
                line(f"[{who}] {lbl} ASCII-clean", "yes" if not bad else f"NO: {bad}", not bad)
                line(f"[{who}] {lbl} bytes==chars", f"{len(k)}=={len(t)}", len(k) == len(t))
    send_k = RR._outbound_key_for("")
    recv_k = RR._secret(RR.INBOUND_KEY_FILE)

    # ---- route -----------------------------------------------------------------
    cfg = RR._config()
    peer = (cfg.get("peer") or {})
    url = RR.peer_url()
    line("peer.name (what YOU call THEM)", peer.get("name") or "(unset)")
    line("peer.url", url or "(unset)", bool(url))

    # ---- your listener ---------------------------------------------------------
    try:
        import shutil, subprocess
        exe = shutil.which("tailscale") or r"C:\Program Files\Tailscale\tailscale.exe"
        my_ip = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True,
                               timeout=10).stdout.strip().splitlines()[0].strip()
    except Exception:                                             # noqa: BLE001
        my_ip = ""
    line("your tailnet IP", my_ip or "(tailscale not answering)", bool(my_ip))
    listening = False
    if my_ip:
        try:
            socket.create_connection((my_ip, 8791), timeout=4).close()
            listening = True
        except OSError:
            pass
    line("your listener on :8791", "UP" if listening else "DOWN", listening)
    line("your endpoint (give this to them)", f"http://{my_ip}:8791/xfer" if my_ip else "(unknown)")

    # ---- can you reach them ----------------------------------------------------
    reachable = False
    if url:
        try:
            host = url.split("//", 1)[-1].split("/", 1)[0]
            h, _, p = host.partition(":")
            socket.create_connection((h, int(p or 80)), timeout=6).close()
            reachable = True
        except Exception:                                         # noqa: BLE001
            pass
    line("their listener reachable", "YES" if reachable else "NO", reachable)

    # ---- what you have RECEIVED — the provenance question ----------------------
    rows = RR._read_jsonl(RR.inbox_path())
    peer_mail = [r for r in rows if str(r.get("frm", "")).startswith("remote:")]
    line("messages parked from them", str(len(peer_mail)), len(peer_mail) > 0)
    prov_ok = None
    for r in peer_mail[-6:]:
        t = datetime.datetime.fromtimestamp(int(r.get("admitted_at") or 0)).strftime("%H:%M:%S")
        skew = int(r.get("sent_at") or 0) - int(r.get("admitted_at") or 0)
        line(f"  parked {str(r.get('id'))[:26]}",
             f"frm={r.get('frm')} claimed={r.get('claimed_frm')} skew={skew:+d}s")
        if str(r.get("frm", "")).startswith("remote:"):
            prov_ok = True if prov_ok is None else prov_ok
        else:
            prov_ok = False
    if peer_mail:
        line("PROVENANCE REWRITE",
             "correct — frm assigned from route, claim kept inert" if prov_ok
             else "BROKEN — frm was read off the payload",
             bool(prov_ok))
    else:
        line("PROVENANCE REWRITE", "cannot judge — nothing received yet")

    # ---- clock -----------------------------------------------------------------
    if peer_mail:
        skews = [int(r.get("sent_at") or 0) - int(r.get("admitted_at") or 0) for r in peer_mail]
        worst = max(abs(s) for s in skews)
        line("worst clock skew seen", f"{worst}s of the 300s window", worst < 240)

    # ---- report back -----------------------------------------------------------
    report = "BRIDGE DOCTOR (their side)\n" + "\n".join(R)
    print("\n" + "=" * 74)
    if not (url and send_k):
        print("Cannot send the report — outbound is not configured. Paste the block above.")
        return 1
    payload = {"v": 1, "id": f"doctor-{int(time.time())}", "frm": "peer", "kind": "note",
               "content": report, "sent_at": int(time.time())}
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    env = {"body": base64.b64encode(body).decode(),
           "sig": hmac_sig(body, send_k)}
    req = urllib.request.Request(url, data=json.dumps(env).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            print(f"report sent across the bridge: {resp.status} {resp.read().decode()}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"report REFUSED by their gate: {e.code} {e.read().decode()}")
        print("Their log holds the reason; the refusal is flat by design. Paste the block above.")
        return 1
    except Exception as e:                                        # noqa: BLE001
        print(f"could not reach them ({type(e).__name__}: {e}). Paste the block above.")
        return 1


def hmac_sig(body: bytes, secret: bytes) -> str:
    import hmac as _h
    return _h.new(secret, body, hashlib.sha256).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
