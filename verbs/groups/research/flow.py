"""The flow waterfall: which ask produced which answer, on which lane, with what gap.

One logical message arriving twice renders as xN COPIES, never as N rows -- the distinction the
dual-write era made load-bearing, and the reason this is a trace and not a listing.
"""
from __future__ import annotations

import json

from verbs.registry import verb


@verb(local=False, door_notes="CLI only; core.comm.flow_trace.")
def cmd_flow(args):
    """R3 (T054): OTel-style waterfall of recent message flows across lanes. lookback
    answers WHY, knowledge-map answers WHAT'S NEAR -- this answers WHAT HAPPENED: which
    ask produced which answer, on which lane, with what gap, and whether one logical
    message arrived MORE than once (double-delivery renders as xN COPIES, never N rows)."""
    from core.comm.flow_trace import flow_trace
    unit = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    w = str(args.window or "6h").strip().lower()
    try:
        window_ms = int(float(w[:-1]) * unit[w[-1]]) if w and w[-1] in unit else int(w) * 60_000
    except Exception:
        print(f"ERROR: bad --window {args.window!r} (use e.g. 30m, 6h, 1d)"); return 1
    out = flow_trace(args.agent, window_ms=window_ms)
    if args.json:
        print(json.dumps(out, indent=2, default=str)); return 0
    if out.get("offline"):
        print("# flow: bus offline (Redis unreachable)"); return 1

    def _dups(node):
        return (1 if node["copies"] > 1 else 0) + sum(_dups(c) for c in node["children"])

    c = out["counts"]
    dup_nodes = sum(_dups(f["root"]) for f in out["flows"])
    who = f" touching {args.agent}" if args.agent else ""
    print(f"# FLOW TRACE -- last {w}{who}   ({c['flows']} flow(s) | {c['nodes']} msg(s) | "
          f"{c['copies']} observed | {dup_nodes} duplicated | window dropped {c['dropped_by_window']})")
    if not out["flows"]:
        print("  (no flows in the window -- widen --window or check the bus)")
        return 0

    def _fmt_ms(ms):
        if ms < 1000:
            return f"+{ms}ms"
        s = ms / 1000.0
        if s < 60:
            return f"+{s:.1f}s"
        m, sec = divmod(int(s), 60)
        if m < 60:
            return f"+{m}m{sec:02d}s"
        h, m2 = divmod(m, 60)
        return f"+{h}h{m2:02d}m"

    def _row(n, depth):
        pad = "  " * depth
        off = "0ms" if not n["offset_ms"] else _fmt_ms(n["offset_ms"])
        dup = f"  x{n['copies']} COPIES" if n["copies"] > 1 else ""
        miss = f"  (answers {n['answers_missing']} -- outside window)" if n.get("answers_missing") else ""
        kb = f"{n['len'] / 1024:.1f}KB" if n["len"] >= 1024 else f"{n['len']}B"
        print(f"  {pad}{off:>9}  [{','.join(n['lanes'])}] {n['frm']} -> {n['to']}  "
              f"{n['kind']}  {kb}{dup}{miss}")
        if n.get("snippet"):
            print(f"  {pad}           {n['snippet']!r}")
        for ch in n["children"]:
            _row(ch, depth + 1)

    for fl in out["flows"][:args.limit]:
        span = _fmt_ms(fl["span_ms"]).lstrip("+") if fl["span_ms"] else "single"
        print(f"\n[flow {fl['flow']}]  {fl['nodes']} msg, span {span}")
        _row(fl["root"], 0)
    hidden = len(out["flows"]) - min(len(out["flows"]), args.limit)
    if hidden:
        print(f"\n  (+{hidden} more flow(s) -- raise --limit)")
    return 0
