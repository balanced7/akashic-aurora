#!/usr/bin/env python
"""drill-panel -- the ONE live drill for the phone control panel, on the PC alone.

    py scripts/phone/drill-panel.py            # the drill
    py scripts/phone/drill-panel.py --keep     # leave the drill's audit file in place to read

WHAT IT TOUCHES, and nothing else: a throwaway `http.server` on **port 8901** (the TEST band), driven
through the panel on **port 8900**. It never starts or stops a real house service, never opens the real
allowlist, never touches the Discord gateway, the runners, OpenGL's server, playlog or Rill's own
process, and never writes to the real audit log.

WHY A DRILL AT ALL, when there are 36 pins in tests/test_phone_panel.py. The pins run against fakes; they
prove the DECISIONS. This runs against the real world: a real socket, a real spawn, a real psutil read, a
real kill, a real confirm token over real HTTP, a real append-only audit line. The two failure classes a
fake cannot catch are exactly the ones this project would ship: a probe that reads the wrong thing, and a
stop whose target-matching is subtly wrong. Daniel's own phone drill comes later, with him, from the
phone; this is the PC half, runnable any time.

EXIT CODE 0 means every step PASSED. Any other exit prints which step failed and what it saw.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from arsenal.panel.actions import ActionRunner          # noqa: E402
from arsenal.panel.audit import AuditLog                # noqa: E402
from arsenal.panel.probe import Prober                  # noqa: E402
from arsenal.panel.server import Panel, PanelServer     # noqa: E402
from arsenal.panel.spec import load_document            # noqa: E402

PANEL_PORT = 8900          # TEST band [8900, 8999] -- never the prod port
PREVIEW_PORT = 8901        # the throwaway service
STEPS: list = []


def ok(step: str, detail: str = "") -> None:
    STEPS.append((True, step, detail))
    print(f"  PASS  {step}" + (f"  -- {detail}" if detail else ""))


def bad(step: str, detail: str = "") -> None:
    STEPS.append((False, step, detail))
    print(f"  FAIL  {step}" + (f"  -- {detail}" if detail else ""))


def port_free(port: int) -> bool:
    c = socket.socket()
    try:
        c.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE
                     if hasattr(socket, "SO_EXCLUSIVEADDRUSE") else socket.SO_REUSEADDR, 1)
        c.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        c.close()


def port_answers(port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def http(method: str, path: str, base: str, body=None, headers=None):
    """One request. The API always answers JSON; the PAGE does not, so a non-JSON body comes back as
    `{"text": ...}` rather than blowing up the caller (the first draft of this drill crashed on "/")."""
    hdrs = dict(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, _decode(res.read())
    except urllib.error.HTTPError as err:
        return err.code, _decode(err.read())


def _decode(raw: bytes):
    try:
        return json.loads(raw or b"{}")
    except ValueError:
        return {"text": (raw or b"").decode("utf-8", "replace")[:200]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="keep the drill's audit + spec files")
    args = ap.parse_args(argv)

    workdir = os.path.join(ROOT, "state", "phone-panel-drill")
    os.makedirs(workdir, exist_ok=True)
    audit_path = os.path.join(workdir, "drill-audit.jsonl")
    spec_path = os.path.join(workdir, "drill-allowlist.json")
    if os.path.exists(audit_path):
        os.remove(audit_path)                       # a drill starts from a clean receipt

    print("== phone control panel: live drill (PC only, TEST band) ==")
    print(f"   root   {ROOT}")
    print(f"   panel  http://127.0.0.1:{PANEL_PORT}   preview 127.0.0.1:{PREVIEW_PORT}")

    # ---- 0. the ground it stands on must be free ------------------------------------------------
    for port in (PANEL_PORT, PREVIEW_PORT):
        if not port_free(port):
            bad(f"port {port} is free", "something is already listening -- the drill refuses to "
                                        "guess what it is")
            return 2
    ok(f"ports {PANEL_PORT} and {PREVIEW_PORT} are free")

    # ---- 1. a throwaway allowlist (never the real one) -------------------------------------------
    doc = {
        "_what": "the drill's own allowlist: ONE throwaway http.server on a TEST port",
        "services": [{
            "id": "drill-preview",
            "label": "Drill preview",
            "group": "stage",
            "probe": {"kind": "port", "host": "127.0.0.1", "port": PREVIEW_PORT},
            "start": ["py", "-m", "http.server", str(PREVIEW_PORT), "--bind", "127.0.0.1"],
            "start_cwd": ROOT,
            "stop": {"type": "kill_argv", "match": ["http.server", str(PREVIEW_PORT)]},
        }, {
            "id": "drill-watched",
            "label": "Drill watched service",
            "group": "services",
            "status_only": True,
            "why_no_actions": "the drill's example of a watched-never-touched row",
            "probe": {"kind": "argv", "match": ["no-such-process-drill-marker"]},
        }],
    }
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    specs, meta = load_document(spec_path)
    ok("throwaway allowlist loaded and validated", f"{len(specs)} service(s)")

    prober = Prober()
    panel = Panel(specs, port=PANEL_PORT, prober=prober,
                  runner=ActionRunner(prober=prober),
                  audit=AuditLog(audit_path), audit_path=audit_path,
                  reach=None,                     # the link card is not what this drill measures
                  video_meta={"artemis": {"label": "Artemis", "deep_link": ""}})
    srv = PanelServer(panel, port=PANEL_PORT).start()
    base = f"http://127.0.0.1:{PANEL_PORT}"
    preview_proc = None
    try:
        ok("panel bound", base)

        # ---- 2. the page and the status document -------------------------------------------------
        code, doc_status = http("GET", "/api/status", base)
        if code == 200 and doc_status.get("version") == "1":
            ok("GET /api/status", f"{len(doc_status.get('services') or [])} service row(s)")
        else:
            bad("GET /api/status", f"HTTP {code}: {doc_status}")
            return 3
        rows = {r["id"]: r for r in doc_status["services"]}
        if rows["drill-preview"]["state"] == "DOWN" and rows["drill-preview"]["colour"] == "red":
            ok("the preview reads DOWN before the drill starts it")
        else:
            bad("the preview reads DOWN before the drill starts it", str(rows.get("drill-preview")))
        if [r["id"] for r in doc_status["status_only"]] == ["drill-watched"]:
            ok("the watched-only service is separate and has no verbs")
        else:
            bad("the watched-only service is separate", str(doc_status.get("status_only")))

        code, page = http("GET", "/", base)
        ok("GET / serves the page", f"HTTP {code}") if code == 200 else bad("GET /", f"HTTP {code}")

        # ---- 3. the gates, live --------------------------------------------------------------
        code, _ = http("GET", "/api/status", base, headers={"Host": "evil.example.com"})
        ok("a foreign Host is 421", f"HTTP {code}") if code == 421 else bad(
            "a foreign Host is 421", f"HTTP {code}")
        code, _ = http("POST", "/api/action", base, {"service": "drill-preview", "verb": "start"},
                       headers={"Origin": "https://evil.example.com"})
        ok("a foreign Origin is 403", f"HTTP {code}") if code == 403 else bad(
            "a foreign Origin is 403", f"HTTP {code}")
        code, _ = http("POST", "/api/action", base, {"service": "nope", "verb": "start"})
        ok("an unknown service is 404", f"HTTP {code}") if code == 404 else bad(
            "an unknown service is 404", f"HTTP {code}")
        code, _ = http("POST", "/api/action", base,
                       {"service": "drill-preview", "verb": "start", "args": ["--evil"]})
        ok("a body with an extra field is 400", f"HTTP {code}") if code == 400 else bad(
            "a body with an extra field is 400", f"HTTP {code}")
        code, _ = http("POST", "/api/action", base, {"service": "drill-preview", "verb": "stop"})
        ok("a stop without a confirm token is 403", f"HTTP {code}") if code == 403 else bad(
            "a stop without a confirm token is 403", f"HTTP {code}")

        # ---- 4. START, verified by the probe AND by an independent check ------------------------
        code, res = http("POST", "/api/action", base, {"service": "drill-preview", "verb": "start"})
        if code == 200 and res.get("ok") and res.get("state") == "UP":
            ok("POST start", f"verified UP in {res.get('elapsed_ms')} ms, pid {res.get('pids')}")
        else:
            bad("POST start", f"HTTP {code}: {res}")
        if port_answers(PREVIEW_PORT):
            ok("independent check: the real port answers", f"127.0.0.1:{PREVIEW_PORT}")
        else:
            bad("independent check: the real port answers", "the probe said UP but nothing answered")

        code, doc_status = http("GET", "/api/status", base)
        rows = {r["id"]: r for r in doc_status["services"]}
        ok("status now reads green for the preview") if rows["drill-preview"]["colour"] == "green" \
            else bad("status now reads green for the preview", str(rows["drill-preview"]))

        # ---- 5. STOP, two-step, and prove the port closed ---------------------------------------
        code, minted = http("POST", "/api/confirm", base, {"service": "drill-preview", "verb": "stop"})
        token = minted.get("token") if code == 200 else None
        ok("POST /api/confirm minted a token", f"ttl {minted.get('expires_in_s')}s") if token else \
            bad("POST /api/confirm", f"HTTP {code}: {minted}")
        if token:
            code, res = http("POST", "/api/action", base,
                             {"service": "drill-preview", "verb": "stop", "token": token})
            if code == 200 and res.get("ok") and res.get("state") == "DOWN":
                ok("POST stop with the token", str(res.get("detail"))[:120])
            else:
                bad("POST stop with the token", f"HTTP {code}: {res}")
            # single use: the replay must be refused
            code, res = http("POST", "/api/action", base,
                             {"service": "drill-preview", "verb": "stop", "token": token})
            ok("the token is single-use (replay refused)", f"HTTP {code}") if code == 403 else bad(
                "the token is single-use (replay refused)", f"HTTP {code}")
        if not port_answers(PREVIEW_PORT):
            ok("independent check: the real port is closed")
        else:
            bad("independent check: the real port is closed", "the probe said DOWN but it still answers")

        # ---- 6. the audit is a FILE, append-only ------------------------------------------------
        time.sleep(0.2)
        lines = [json.loads(ln) for ln in open(audit_path, encoding="utf-8").read().splitlines() if ln]
        decisions = [ln["decision"] for ln in lines]
        if "acted" in decisions and "refused" in decisions:
            ok("the audit recorded actions AND refusals", f"{len(lines)} line(s): {decisions}")
        else:
            bad("the audit recorded actions AND refusals", f"{decisions}")
        acted = [ln for ln in lines if ln["decision"] == "acted" and ln["verb"] == "start"]
        if acted and acted[0].get("ok") is True and acted[0].get("remote") == "127.0.0.1":
            ok("the start's audit line carries ok + remote", json.dumps(acted[0])[:140])
        else:
            bad("the start's audit line carries ok + remote", str(acted[:1]))
        if not any("args" in ln for ln in lines):
            ok("no audit line leaked the refused body's fields")
    finally:
        srv.stop()
        # ---- 7. leave no process behind ---------------------------------------------------------
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "cmdline"]):
                argv = [str(a) for a in (proc.info.get("cmdline") or [])]
                if "http.server" in argv and str(PREVIEW_PORT) in argv:
                    proc.terminate()
                    bad("cleanup: a drill server was still running and was terminated", f"pid {proc.pid}")
        except Exception as exc:
            bad("cleanup could not confirm the drill server is gone", str(exc))
        if not port_answers(PREVIEW_PORT, timeout=1.0):
            ok("cleanup: nothing is left listening on the drill port")
        if not args.keep:
            pass          # the spec + audit stay: they ARE the receipt

    failures = [s for s in STEPS if not s[0]]
    print("")
    print(f"== {len(STEPS) - len(failures)}/{len(STEPS)} steps passed ==")
    print(f"   audit: {audit_path}")
    print(f"   spec : {spec_path}")
    if failures:
        print("FAILED:")
        for _, step, detail in failures:
            print(f"  - {step}: {detail}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
