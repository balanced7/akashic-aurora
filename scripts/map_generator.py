"""T381 M1 -- the living map's first render (c-map-design reconciled).

One substrate, two headsets: this is the HUMAN headset's front page -- the
deck as terrain, landmarks lit by activity, an event-badge whisper above and
a trail whisper below, the alarm banner owning the top when anything pages.
Lineage: the founding want (beautiful live dashboards, Apr 2026), "feel the
engine running" (29f15d47:1745), "assembled, not composed" as the named
failure (2026-07-05), and the trust-first law (e696354a:965) -- which is why
build_map REFUSES to render without its stamp: an unstamped map is not a
degraded map, it is a lie about now, so it is not a map at all.

Two halves, one seam (the T375 fold lesson applied to rendering):
  build_map(data) -> html     PURE -- deterministic, no I/O, pin-tested
  gather_map_data() -> data   the only I/O; READ verbs only. It must NEVER
                              call the Eye position family (go/back/inherit/
                              since) -- a render that moves a seat's cursor
                              poisons `since=` for that seat (half_a C3,
                              load-bearing).

Regenerate: py scripts/map_generator.py  ->  state/map/index.html
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)              # scripts/ runs standalone (house pattern)
OUT_PATH = os.path.join(ROOT, "state", "map", "index.html")

_REQUIRED_STAMP = ("generated_ts", "head_sha", "cursors")
_ACTIVE_STATUSES = ("claimed", "in_progress", "verifying")


class MapRefusal(Exception):
    """An unstamped render was requested. The map refuses to lie about now."""


# --------------------------------------------------------------------- pure
def build_map(data: Dict[str, Any]) -> str:
    for k in _REQUIRED_STAMP:
        if k not in data:
            raise MapRefusal(
                f"stamp ingredient {k!r} missing -- a map that cannot be dated "
                f"is a map that lies about now; refused, not degraded")
    e = _html.escape
    page_grades = int(data.get("page_grades") or 0)
    parts: List[str] = []
    parts.append(
        "<style>"
        "body{background:#0b0e14;color:#cdd6e4;font-family:Segoe UI,system-ui,"
        "sans-serif;margin:0;padding:0 0 2rem 0}"
        ".map-alarm{background:#8b1a1a;color:#fff;font-weight:600;padding:.8rem "
        "1.2rem;font-size:1.05rem}"
        ".kernel{display:flex;gap:1.2rem;align-items:baseline;padding:.7rem "
        "1.2rem;background:#11151f;border-bottom:1px solid #1d2433;flex-wrap:wrap}"
        ".kernel b{font-size:1.25rem;color:#7fd1b9}"
        ".kernel .overdue b{color:#e0a458}"
        ".badges{display:flex;gap:.9rem;padding:.45rem 1.2rem;font-size:.78rem;"
        "color:#8a93a6;border-bottom:1px solid #151a26;flex-wrap:wrap}"
        ".terrain{display:grid;grid-template-columns:repeat(auto-fill,minmax("
        "230px,1fr));gap:.8rem;padding:1.1rem 1.2rem}"
        ".lm{background:#131826;border:1px solid #1f2738;border-radius:9px;"
        "padding:.7rem .85rem}"
        ".lm .id{font-weight:700;color:#9ecbff}"
        ".lm .st{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;"
        "color:#7fd1b9;margin-left:.45rem}"
        ".lm.bet .id{color:#e6c07b}.lm.fence .id{color:#c39ac9}"
        ".lm .ti{font-size:.82rem;color:#aab3c5;margin-top:.3rem}"
        ".trail{padding:.55rem 1.2rem;color:#77809a;font-size:.8rem;"
        "border-top:1px solid #151a26}"
        ".stamp{margin:.9rem 1.2rem 0;padding:.6rem .85rem;background:#0e1119;"
        "border:1px dashed #2a3346;border-radius:8px;font-size:.72rem;"
        "color:#6b7488;font-family:Consolas,monospace}"
        "h1{font-size:1.0rem;margin:.9rem 1.2rem .1rem;color:#dfe6f2;"
        "font-weight:600}"
        "</style>")
    if page_grades > 0:
        parts.append(f'<div class="map-alarm">⚠ {page_grades} page-grade '
                     f'finding(s) -- the house is paging; everything below is '
                     f'secondary</div>')
    kernel = [f'<span>pages <b>{page_grades}</b></span>',
              f'<span>dashboard <b>{int(data.get("dashboard_count") or 0)}</b></span>']
    overdue = data.get("overdue") or []
    if overdue:
        names = ", ".join(e(str(o.get("id"))) for o in overdue)
        kernel.append(f'<span class="overdue">OVERDUE bets <b>{len(overdue)}</b> '
                      f'({names})</span>')
    else:
        kernel.append('<span class="overdue">OVERDUE bets <b>0</b></span>')
    parts.append(f'<div class="kernel">{"".join(kernel)}</div>')
    badges = data.get("badges") or []
    if badges:
        chips = "".join(
            f'<span>{e(str(b.get("family")))} · {int(b.get("count") or 0)}'
            f'</span>' for b in badges)
        parts.append(f'<div class="badges">{chips}</div>')
    parts.append("<h1>the deck</h1>")
    cards = []
    for lm in data.get("landmarks") or []:
        kind = e(str(lm.get("kind") or "task"))
        by = f' · {e(str(lm.get("by")))}' if lm.get("by") else ""
        cards.append(
            f'<div class="lm {kind}"><span class="id">{e(str(lm.get("id")))}'
            f'</span><span class="st">{e(str(lm.get("status")))}{by}</span>'
            f'<div class="ti">{e(str(lm.get("title") or ""))[:110]}</div></div>')
    parts.append(f'<div class="terrain">{"".join(cards)}</div>')
    tr = data.get("trails") or {}
    parts.append(f'<div class="trail">trails: {int(tr.get("routes") or 0)} '
                 f'authored route(s), {int(tr.get("last24h") or 0)} touched in '
                 f'the last 24h · sensed overlay arrives with T378</div>')
    cur = data["cursors"]
    cur_s = " · ".join(f"{e(str(k))}={e(str(v))}" for k, v in
                            sorted(cur.items()))
    parts.append(
        f'<div class="stamp">generated {e(str(data["generated_ts"]))} · '
        f'HEAD {e(str(data["head_sha"]))} · {cur_s} · a map without '
        f'this stamp is refused by its own generator</div>')
    return "".join(parts)


# ---------------------------------------------------------------------- i/o
def gather_map_data() -> Dict[str, Any]:
    """READ verbs only; never the Eye position family (half_a C3)."""
    data: Dict[str, Any] = {
        "generated_ts": datetime.now(timezone.utc).isoformat()}
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        data["head_sha"] = (r.stdout or "").strip() or "unknown"
    except Exception:
        data["head_sha"] = "unknown"

    ledger = json.load(open(os.path.join(ROOT, "state", "coord", "tasks.json"),
                            encoding="utf-8"))
    tasks = ledger.get("tasks") or []
    landmarks = [{"id": t.get("id"), "kind": "task", "status": t.get("status"),
                  "by": t.get("owner"), "title": t.get("title") or
                  (t.get("desc") or "")[:110]}
                 for t in tasks if t.get("status") in _ACTIVE_STATUSES]

    from core.coord.forecast_registry import ForecastRegistry
    reg = ForecastRegistry(path=os.path.join(ROOT, "state", "coord",
                                             "forecasts.jsonl"))
    state = reg.state()
    for fid in sorted(state):
        row = state[fid]
        landmarks.append({"id": fid, "kind": "bet",
                          "status": row.get("verdict") or "OPEN",
                          "by": row.get("registered_by"),
                          "title": (row.get("expectation") or {}).get(
                              "statement", "")[:110]})
    cal = reg.calibration()
    overdue = [{"id": r.get("id"), "registered_by": r.get("registered_by")}
               for r in cal.get("overdue") or []]

    fdir = os.path.join(ROOT, "fences")
    if os.path.isdir(fdir):
        for name in sorted(os.listdir(fdir)):
            fj = os.path.join(fdir, name, "fence.json")
            if os.path.exists(fj):
                try:
                    doc = json.load(open(fj, encoding="utf-8"))
                    seals = doc.get("seals") or {}
                    status = ("sealed" if "reconciliation" in seals
                              else f"{len(seals)}/4 sealed")
                except Exception:
                    status = "unreadable"
                landmarks.append({"id": name, "kind": "fence",
                                  "status": status, "title": "design fence"})

    page_grades, dashboard = 0, 0
    try:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "agent_cli.py"),
                            "doctor"], cwd=ROOT, capture_output=True,
                           text=True, timeout=90, encoding="utf-8",
                           errors="replace")
        m = re.search(r"doctor:\s*(\d+)\s*page-grade.*?(\d+)\s*dashboard",
                      r.stdout or "")
        if m:
            page_grades, dashboard = int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    data["page_grades"] = page_grades
    data["dashboard_count"] = dashboard

    badges: List[Dict[str, Any]] = []
    newest_event = ""
    try:
        from core.comm.bus import Bus
        c = Bus("map-generator", promote=False)._client
        for key in ("bifrost:inbox:claude", "bifrost:inbox:deepseek",
                    "bifrost:inbox:kimi", "events:raw"):
            try:
                n = c.xlen(key)
                last = c.xrevrange(key, count=1)
                sid = str(last[0][0]) if last else ""
                badges.append({"family": key, "count": int(n), "last_ts": sid})
                if key == "events:raw":
                    newest_event = sid
            except Exception:
                continue
    except Exception:
        pass
    data["badges"] = badges

    routes_n, last24 = 0, 0
    rp = os.path.join(ROOT, "state", "eye", "routes.jsonl")
    if os.path.exists(rp):
        try:
            now = datetime.now(timezone.utc).timestamp()
            for line in open(rp, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line:
                    continue
                routes_n += 1
                try:
                    ts = json.loads(line).get("ts")
                    if ts and (now - float(ts)) < 86400:
                        last24 += 1
                except Exception:
                    continue
        except Exception:
            pass
    data["trails"] = {"routes": routes_n, "last24h": last24}

    data["landmarks"] = landmarks
    data["overdue"] = overdue
    data["cursors"] = {"ledger_seq": ledger.get("seq"),
                       "forecasts": len(state),
                       "newest_event": newest_event or "none-read"}
    return data


def main() -> int:
    data = gather_map_data()
    html_out = build_map(data)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"[map] rendered {OUT_PATH} @ {data['head_sha']} "
          f"({len(data.get('landmarks') or [])} landmark(s), "
          f"page-grades {data.get('page_grades')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
