"""arsenal.panel.__main__ -- start the phone control panel.

    py -m arsenal.panel                       # the panel on its registered port (config.PORT_PHONE_PANEL)
    py -m arsenal.panel --port 8900            # a TEST port, for the drill
    py -m arsenal.panel --self-check           # validate the allowlist and print it; bind nothing

WHAT IT REFUSES, and why each refusal is a feature rather than a limitation:

  * It will not bind anything but loopback. A `--host 0.0.0.0` is not a flag that exists; the reason is
    in `server.PanelServer.__init__` and it is that this API starts and stops processes.
  * It will not start with an empty or missing allowlist (`spec.SpecError`). An empty allowlist and a
    failed load look identical from the API, and one means "nothing is controllable" while the other
    means "someone is about to wonder why every button does nothing".
  * It will not start a second copy on the same port (`SO_EXCLUSIVEADDRUSE`): the failure is immediate
    and named, instead of two servers swapping the port between requests.

The first thing it prints is the URL the phone will use, which is NOT this PC's address: the phone
reaches this port at its OWN 127.0.0.1 through the PhoneLink watcher's `ssh -R`. Printing
`http://127.0.0.1:<port>` here would be printing the wrong machine's address, so the line names the
tunnel instead.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from arsenal.panel.server import API_VERSION, DEFAULT_PORT, Panel, PanelServer  # noqa: E402
from arsenal.panel.spec import SpecError, from_document, load_document  # noqa: E402
from arsenal.panel.status import ReachabilityCache  # noqa: E402


def _default_port() -> int:
    try:
        import config
        return int(getattr(config, "PORT_PHONE_PANEL", DEFAULT_PORT))
    except Exception:
        return DEFAULT_PORT


def _local_document(name: str):
    """`local/<name>.json` MERGED with this machine's private profile, through the ONE loader.

    The committed file is the allowlist's SHAPE plus the house services; the machine half -- where
    OpenRGB is installed, which seat the link card reports -- lives in the private profile
    (`akashic-local/profile/phone-panel.json`) and must never be committed to a public repo. So the
    panel asks `core.local`, exactly as every checker asks it, rather than parsing `local/` itself:
    a second parser here would silently drop the private half, and the panel would come up looking
    healthy while two of its rows carried defaults belonging to somebody else's machine.

    `core.local.load()` announces an absent profile in one loud line on stderr and then returns the
    public defaults, so a fork with no profile still runs -- it just says so.
    """
    try:
        from core import local as local_layer
    except ImportError as exc:                     # pragma: no cover - every checkout has core/
        raise SpecError(
            f"the panel reads its allowlist through core/local.py, which could not be imported "
            f"({exc}). Reading local/{name}.json with a private parser here would drop the private "
            f"profile silently, so this is a refusal rather than a fallback.")
    try:
        return local_layer.load(name), str(local_layer.local_path(name))
    except local_layer.LocalDataMissing as exc:
        raise SpecError(str(exc))


def _allowlist(args):
    """(specs, meta, source): an explicit `--spec` file, or the merged Local document."""
    if args.spec:
        return (*load_document(args.spec), args.spec)
    doc, path = _local_document("phone-panel")
    specs, meta = from_document(doc, path)
    return specs, meta, path


def build_panel(args) -> Panel:
    specs, meta, _source = _allowlist(args)
    panel_meta = meta.get("panel") or {}
    agent = (args.agent or os.environ.get("AKASHIC_AGENT_ID")
             or str(panel_meta.get("agent") or ""))
    session = args.session or os.environ.get("AKASHIC_SESSION_ID") or ""
    audit_path = args.audit or os.path.join(ROOT, "state", "phone-panel-audit.jsonl")
    ttl = float(args.confirm_ttl_s or panel_meta.get("confirm_ttl_s") or 60.0)
    reach = None
    if not args.no_reachability:
        reach = ReachabilityCache(agent, session)
    return Panel(specs, port=args.port, agent=agent, session=session, confirm_ttl_s=ttl,
                 audit_path=audit_path, reach=reach, video_meta=meta.get("video") or {})


def self_check(args) -> int:
    """Print what the panel WOULD control. Binds nothing, starts nothing, probes nothing."""
    try:
        specs, meta, spec_path = _allowlist(args)
    except SpecError as exc:
        print(f"REFUSED: {exc}")
        return 2
    print(f"allowlist: {spec_path}  ({len(specs)} service(s), api v{API_VERSION})")
    for spec in specs.values():
        verbs = ", ".join(spec.allowed_verbs()) or "(no actions)"
        start = " ".join(spec.start) if spec.start else "-"
        print(f"  {spec.id:<18} {spec.probe.get('kind'):<8} {verbs}")
        print(f"  {'':<18} start: {start}")
        if spec.stop:
            print(f"  {'':<18} stop:  {spec.stop.get('type')}"
                  + (f" {spec.stop.get('name') or ' '.join(spec.stop.get('match') or [])}"
                     if spec.stop.get("type") != "none" else ""))
    video = meta.get("video") or {}
    artemis = (video.get("artemis") or {})
    print(f"  artemis deep link: {artemis.get('deep_link') or '(not declared)'}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal.panel",
                                 description="the phone control panel (loopback only)")
    ap.add_argument("--port", type=int, default=_default_port(),
                    help=f"loopback port (default: config.PORT_PHONE_PANEL, {DEFAULT_PORT})")
    ap.add_argument("--spec", default=None, help="the allowlist JSON (default local/phone-panel.json)")
    ap.add_argument("--audit", default=None,
                    help="append-only audit JSONL (default state/phone-panel-audit.jsonl)")
    ap.add_argument("--agent", default="", help="seat id the link card reports (default: $AKASHIC_AGENT_ID)")
    ap.add_argument("--session", default="", help="session id the link card reports")
    ap.add_argument("--confirm-ttl-s", dest="confirm_ttl_s", type=float, default=0.0,
                    help="how long a confirm token lives (default 60)")
    ap.add_argument("--no-reachability", action="store_true", dest="no_reachability",
                    help="skip the phase-3 reachability verb (the link card then reads UNKNOWN)")
    ap.add_argument("--self-check", action="store_true", dest="self_check",
                    help="validate the allowlist and print it; bind nothing")
    args = ap.parse_args(argv)

    if args.self_check:
        return self_check(args)
    try:
        panel = build_panel(args)
    except SpecError as exc:
        print(f"REFUSED: {exc}")
        return 2
    try:
        srv = PanelServer(panel, port=args.port)
    except OSError as exc:
        print(f"REFUSED: port {args.port} could not be bound exclusively: {exc}")
        return 3
    except ValueError as exc:
        print(f"REFUSED: {exc}")
        return 2
    for spec in panel.specs.values():
        pass
    print(f"phone panel: http://127.0.0.1:{srv.port}  (api v{API_VERSION}, "
          f"{len(panel.specs)} service(s), audit {panel.audit_path})")
    print(f"  the phone reaches this at ITS OWN 127.0.0.1:{srv.port} through the PhoneLink watcher's "
          f"tunnel -- add -R {srv.port}:127.0.0.1:{srv.port} to `phonelink.ps1 watch`.")
    print(f"  this port is NOT published to the tailnet, by design.")
    srv.start()
    try:
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nstopping (nothing was started or stopped by stopping the panel)")
    finally:
        srv.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
