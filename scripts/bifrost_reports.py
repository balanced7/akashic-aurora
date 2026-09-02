"""Report shelf -- the Bifrost page and its JSON doors.

MOUNTING (per the bifrost_ui integration boundary: claude authors the standalone
module, deepseek wires it). Four lines inside `do_GET`, before the fallthrough:

    from scripts import bifrost_reports as _reports
    hit = _reports.handle(path, query)
    if hit is not None:
        return self._send(*hit)          # (status, content_type, body_bytes)

`handle` returns None for every path it does not own, so it can sit anywhere in the
chain without shadowing an existing route. It never writes -- the shelf is a viewer,
and a viewer that can publish is a leak waiting to happen.

Routes
    /reports                              the page
    /api/reports?q=&shelf=&category=&arc=&status=&limit=&offset=
    /api/report?id=<atom-or-priv-id>
    /api/reports/compare?left=<id>&right=<id>
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.library import reports as rs  # noqa: E402

Response = Tuple[int, str, bytes]

_FAMILY = None
_FAMILY_TRIED = False


def family():
    """Open the atom family lazily, once, and never let its absence break the page.

    The private shelf is plain files and always readable; if Redis is down the page
    must still serve those rather than 500. A degraded shelf beats a dead one.
    """
    global _FAMILY, _FAMILY_TRIED
    if _FAMILY_TRIED:
        return _FAMILY
    _FAMILY_TRIED = True
    try:
        from core.library.atoms import AtomFamily
        from core.foundation.store import create_store  # type: ignore
        _FAMILY = AtomFamily(create_store(), repo_root=str(ROOT))
    except Exception:
        _FAMILY = None
    return _FAMILY


def _json(payload: Dict[str, Any], status: int = 200) -> Response:
    return status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _one(query: Dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
    """Query values arrive as lists from parse_qs; take the first, keep the type honest."""
    val = query.get(key, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val


def handle(path: str, query: Optional[Dict[str, Any]] = None) -> Optional[Response]:
    query = query or {}
    if path == "/reports":
        return 200, "text/html; charset=utf-8", PAGE.encode("utf-8")

    if path == "/api/reports":
        status = _one(query, "status", "current")
        return _json(rs.list_reports(
            family(),
            shelf=_one(query, "shelf"),
            category=_one(query, "category"),
            arc=_one(query, "arc"),
            status=None if status in ("", "all", "any") else status,
            q=_one(query, "q"),
            limit=int(_one(query, "limit", "200") or 200),
            offset=int(_one(query, "offset", "0") or 0),
        ))

    if path == "/api/report":
        rid = _one(query, "id", "") or ""
        rep = rs.get_report(family(), rid)
        if not rep:
            return _json({"error": "not found", "id": rid}, 404)
        return _json(rep)

    if path == "/api/reports/compare":
        return _json(rs.compare(family(), _one(query, "left", "") or "",
                                _one(query, "right", "") or ""))
    return None


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>Report Shelf — Akashic Aurora</title>
<style>
  :root{
    --bg:#0a0c10; --panel:#12161d; --edge:#1e2530; --ink:#dfe6f0; --dim:#8b97a8;
    --accent:#5dd0c4; --accent2:#b98bff; --warn:#f0b866; --priv:#ff8fa3;
    --mono:ui-monospace,"Cascadia Code",Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:14px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
  header{display:flex;align-items:baseline;gap:14px;padding:14px 18px;
         border-bottom:1px solid var(--edge);position:sticky;top:0;background:var(--bg);z-index:5}
  h1{font-size:15px;margin:0;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
  .count{color:var(--dim);font:12px var(--mono)}
  .wrap{display:grid;grid-template-columns:250px minmax(0,1fr) minmax(0,1.05fr);
        gap:0;height:calc(100vh - 52px)}
  .rail,.list,.detail{overflow-y:auto;height:100%}
  .rail{border-right:1px solid var(--edge);padding:14px}
  .list{border-right:1px solid var(--edge);padding:10px}
  .detail{padding:16px 20px}
  input,select{width:100%;background:var(--panel);color:var(--ink);border:1px solid var(--edge);
               border-radius:7px;padding:7px 9px;font:13px var(--mono);margin-bottom:9px}
  input:focus,select:focus{outline:none;border-color:var(--accent)}
  .lbl{font:11px var(--mono);color:var(--dim);text-transform:uppercase;
       letter-spacing:.1em;margin:14px 0 6px}
  .chip{display:inline-block;font:11px var(--mono);padding:2px 7px;border-radius:99px;
        border:1px solid var(--edge);color:var(--dim);margin:0 4px 4px 0;cursor:pointer}
  .chip:hover{border-color:var(--accent);color:var(--accent)}
  .chip.on{background:var(--accent);color:#06231f;border-color:var(--accent)}
  .card{border:1px solid var(--edge);border-radius:9px;padding:10px 12px;margin-bottom:8px;
        cursor:pointer;background:var(--panel);transition:border-color .12s}
  .card:hover{border-color:var(--accent)}
  .card.sel{border-color:var(--accent2);box-shadow:0 0 0 1px var(--accent2) inset}
  .card h3{margin:0 0 4px;font-size:13.5px;font-weight:600;line-height:1.35}
  .meta{font:11px var(--mono);color:var(--dim);display:flex;gap:9px;flex-wrap:wrap;align-items:center}
  .badge{font:10px var(--mono);padding:1px 6px;border-radius:4px;border:1px solid var(--edge)}
  .badge.fleet{color:var(--accent);border-color:#1d4a45}
  .badge.private{color:var(--priv);border-color:#5a2733;background:#25121a}
  .gist{color:var(--dim);font-size:12.5px;margin-top:5px;
        display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .body{white-space:pre-wrap;font:12.5px/1.6 var(--mono);background:var(--panel);
        border:1px solid var(--edge);border-radius:9px;padding:14px;overflow-x:auto}
  .cmp{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}
  .cmp>div{border:1px solid var(--edge);border-radius:8px;padding:9px 11px;background:var(--panel)}
  .k{font:11px var(--mono);color:var(--dim)}
  .v{font:12px var(--mono);color:var(--ink)}
  .differ{color:var(--warn)}
  .empty{color:var(--dim);padding:26px;text-align:center;font:12px var(--mono)}
  button.act{background:var(--accent2);color:#150a26;border:0;border-radius:7px;
             padding:7px 12px;font:12px var(--mono);cursor:pointer;margin-right:7px}
  button.act[disabled]{opacity:.35;cursor:default}
  a{color:var(--accent)}
</style>

<header>
  <h1>Report Shelf</h1>
  <span class="count" id="count">loading…</span>
  <span style="flex:1"></span>
  <button class="act" id="cmpBtn" disabled>compare selected</button>
  <button class="act" id="clrBtn" style="background:#2a3240;color:var(--dim)">clear</button>
</header>

<div class="wrap">
  <div class="rail">
    <input id="q" placeholder="search title / gist / seat…" autocomplete="off">
    <select id="shelf">
      <option value="">both shelves</option>
      <option value="fleet">fleet only</option>
      <option value="private">private only</option>
    </select>
    <select id="status">
      <option value="current">current only</option>
      <option value="all">include superseded</option>
    </select>
    <div class="lbl">Category</div>
    <div id="cats"></div>
    <div class="lbl">Arc</div>
    <div id="arcs"></div>
  </div>
  <div class="list" id="list"><div class="empty">loading…</div></div>
  <div class="detail" id="detail"><div class="empty">select a report — pick two to compare</div></div>
</div>

<script>
const $ = s => document.querySelector(s);
let state = {q:"", shelf:"", status:"current", category:"", arc:"", sel:[]};

const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

async function load(){
  const p = new URLSearchParams();
  for (const k of ["q","shelf","status","category","arc"]) if (state[k]) p.set(k, state[k]);
  p.set("limit","400");
  const r = await fetch("/api/reports?"+p).then(r=>r.json()).catch(()=>null);
  if (!r){ $("#list").innerHTML = '<div class="empty">shelf unreachable</div>'; return; }
  $("#count").textContent = r.total + " reports" +
     (r.facets.shelf ? "  ·  " + Object.entries(r.facets.shelf).map(([k,v])=>k+" "+v).join("  ") : "");
  $("#list").innerHTML = r.reports.length ? r.reports.map(card).join("") :
     '<div class="empty">nothing matches</div>';
  chips("#cats", r.facets.category, "category");
  chips("#arcs", r.facets.arc, "arc");
  [...document.querySelectorAll(".card")].forEach(el =>
    el.onclick = () => pick(el.dataset.id));
}

function card(c){
  const sel = state.sel.includes(c.id) ? " sel" : "";
  return `<div class="card${sel}" data-id="${esc(c.id)}">
    <h3>${esc(c.title)}</h3>
    <div class="meta">
      <span class="badge ${c.shelf}">${esc(c.shelf)}</span>
      <span>${esc(c.date)}</span>
      ${c.arc?`<span>${esc(c.arc)}</span>`:""}
      <span>${(c.chars/1000).toFixed(1)}k</span>
      ${(c.category||[]).slice(0,3).map(x=>`<span>#${esc(x)}</span>`).join("")}
      ${(c.seats||[]).slice(0,3).map(x=>`<span>@${esc(x)}</span>`).join("")}
    </div>
    ${c.gist?`<div class="gist">${esc(c.gist)}</div>`:""}
  </div>`;
}

function chips(sel, obj, key){
  const el = $(sel); const cur = state[key];
  el.innerHTML = Object.entries(obj||{}).slice(0,22).map(([k,v]) =>
    `<span class="chip${cur===k?" on":""}" data-k="${esc(k)}">${esc(k)} ${v}</span>`).join("") || '<span class="k">—</span>';
  [...el.querySelectorAll(".chip")].forEach(c => c.onclick = () => {
    state[key] = (state[key]===c.dataset.k) ? "" : c.dataset.k; load();
  });
}

function pick(id){
  const i = state.sel.indexOf(id);
  if (i>=0) state.sel.splice(i,1); else state.sel.push(id);
  if (state.sel.length>2) state.sel.shift();
  $("#cmpBtn").disabled = state.sel.length !== 2;
  [...document.querySelectorAll(".card")].forEach(el =>
    el.classList.toggle("sel", state.sel.includes(el.dataset.id)));
  if (state.sel.length===1) show(state.sel[0]);
}

async function show(id){
  const r = await fetch("/api/report?id="+encodeURIComponent(id)).then(r=>r.json());
  if (r.error){ $("#detail").innerHTML = '<div class="empty">not found</div>'; return; }
  $("#detail").innerHTML = `
    <h2 style="margin:0 0 6px;font-size:16px">${esc(r.title)}</h2>
    <div class="meta" style="margin-bottom:12px">
      <span class="badge ${r.shelf}">${esc(r.shelf)}</span><span>${esc(r.date)}</span>
      ${r.arc?`<span>${esc(r.arc)}</span>`:""}<span>${esc(r.id)}</span>
      ${(r.category||[]).map(x=>`<span>#${esc(x)}</span>`).join("")}
    </div>
    <div class="body">${esc(r.body||"")}</div>`;
}

async function compare(){
  const [a,b] = state.sel;
  const r = await fetch(`/api/reports/compare?left=${encodeURIComponent(a)}&right=${encodeURIComponent(b)}`)
              .then(r=>r.json());
  if (r.error){ $("#detail").innerHTML = '<div class="empty">'+esc(r.error)+'</div>'; return; }
  const row = (k,v) => `<div><span class="k">${esc(k)}</span><br><span class="v">${esc(v)}</span></div>`;
  const differ = Object.entries(r.differ||{}).map(([k,v]) =>
    `<div class="cmp"><div><span class="k">${esc(k)} — left</span><br><span class="v differ">${esc(v.left)}</span></div>
     <div><span class="k">${esc(k)} — right</span><br><span class="v differ">${esc(v.right)}</span></div></div>`).join("");
  $("#detail").innerHTML = `
    <h2 style="margin:0 0 10px;font-size:16px">Comparison</h2>
    <div class="cmp">
      <div><span class="k">left</span><br><span class="v">${esc(r.left.title)}</span></div>
      <div><span class="k">right</span><br><span class="v">${esc(r.right.title)}</span></div>
    </div>
    <div class="lbl">Relation</div><div class="v">${esc(r.lineage)}</div>
    <div class="lbl">Agree on</div>
    <div class="cmp">${Object.entries(r.same||{}).map(([k,v])=>row(k,v)).join("") || '<div class="k">nothing</div>'}</div>
    <div class="lbl">Diverge on</div>
    ${differ || '<div class="k">nothing</div>'}
    <div class="lbl">Categories</div>
    <div class="cmp">
      ${row("shared", (r.category.shared||[]).join(", ") || "—")}
      ${row("overlap", r.category.overlap ?? "—")}
      ${row("left only", (r.category.left_only||[]).join(", ") || "—")}
      ${row("right only", (r.category.right_only||[]).join(", ") || "—")}
    </div>
    <div class="lbl">Seats</div>
    <div class="cmp">
      ${row("shared", (r.seats.shared||[]).join(", ") || "—")}
      ${row("left / right only",
        ((r.seats.left_only||[]).join(", ")||"—") + "  /  " + ((r.seats.right_only||[]).join(", ")||"—"))}
    </div>
    <div class="lbl">Size</div>
    <div class="cmp">${row("left chars", r.size.left_chars)}${row("right chars", r.size.right_chars)}</div>`;
}

$("#q").oninput = e => { state.q = e.target.value; clearTimeout(window._t);
                         window._t = setTimeout(load, 180); };
$("#shelf").onchange = e => { state.shelf = e.target.value; load(); };
$("#status").onchange = e => { state.status = e.target.value; load(); };
$("#cmpBtn").onclick = compare;
$("#clrBtn").onclick = () => { state = {q:"",shelf:"",status:"current",category:"",arc:"",sel:[]};
  $("#q").value=""; $("#shelf").value=""; $("#status").value="current";
  $("#cmpBtn").disabled = true;
  $("#detail").innerHTML = '<div class="empty">select a report — pick two to compare</div>'; load(); };
load();
</script>
"""
