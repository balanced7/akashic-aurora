"""context.scene.v1 -- one anchor, every plane, and silence that is typed.

SPEC: `research/in-flight/context-system-navi-m2.md` (Navi, E1), rows W0.5 and W0.6 of
      `fences/context-system/reconciliation.md`. PINS: `tests/test_context_scene_v1.py`.
ANCHORS: `core/coord/target.py` (W0.1). TOUCHES PLANE: `core/events/touch.py` (W0.2).

WHY, and it is the acceptance test for the whole wave, in Daniel's words:

    "when the design is finished I won't have to remind you whats related to what and the
     importance of it, you will be able to see it."

THE DESIGN PROBLEM IS NOT THE JOIN. Joining git to touches to lessons is ordinary work. The problem
is that a plane which knows nothing and a plane which CANNOT KNOW must not look the same, and today
across this house they do: both render as no results. Every surface that has lied to us this week
lied in exactly that way -- a doctor panel reporting truncations it could never see, a recall funnel
reporting a confident zero, a meter counting commands it could not read as having touched nothing.
So the state field is not metadata on the rows; it is the point, and the rows are what you get when
a plane earns `ok`.

  ok           asked, joined, has rows
  empty        asked, and there genuinely is nothing
  UNCHECKABLE  could not ask, and the reason rides along -- never a zero
  error        asked and it broke, with the exception in the fog line

A PLANE IS NEVER ABSENT. A plane missing from the output is indistinguishable from one that does not
exist, and the reader cannot tell which planes were consulted. Every plane this module knows about
appears in every scene, most of them saying honestly that they could not answer yet.

ROWS ARE ADDRESSES, NOT PROSE (Daniel's addendum, B6). Every row carries a ref the house's own doors
resolve. A plane that cannot mint a ref for a row puts that row in `fog`, never in `rows` -- a row
you cannot follow is a claim you cannot check.

TWO PLANES ARE LIVE: git and touches. The rest resolve UNCHECKABLE with their reason, which is the
honest shape of a half-built door rather than a stub that fakes completeness.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

SCHEMA = "context.scene.v1"
STATES = ("ok", "empty", "UNCHECKABLE", "error")

#: Every plane the context door knows about. Order is the reading order of the L0 card: what the
#: code did, who touched it, what we learned, what governs it, who holds it, who is on it.
PLANES = ("git", "touches", "lessons", "authorship", "locks", "focus")

#: Planes with no resolver yet say so, by name, with the slice that would fill them. A stub that
#: returned `empty` would be a lie with better manners.
_NOT_YET = {
    "lessons": "no resolver yet (Wave 1): lessons key on `files_affected`, and 39 of 1,526 carry "
               "one, so the plane would be near-empty for a reason that is about the corpus "
               "rather than about this anchor -- it needs W0.2's touches to key on instead",
    "authorship": "no resolver yet (Wave 1): the authorship ledger's rewrite-stable key is the "
                  "join, and wiring it is Heimdall's B5.3, filed to the parent fence",
    "locks": "no resolver yet (Wave 1): advisory locks key on their own lowercased path spelling, "
             "which is one of the four spellings W0.1 exists to unify; the lock plane joins once "
             "its keys route through context.target.v1",
    "focus": "no resolver yet (Wave 1): session focus matches by substring today "
             "(core/coord/session_focus.py), which the W0.1 spec explicitly keeps out of the "
             "typed plane because its false hits are the class it already owns",
}

MAX_ROWS = 12


def build(anchor: str, *, subject: str, roots: Any, level: int = 1,
          resolvers: Optional[Dict[str, Callable]] = None,
          exists: Optional[Callable[[str], bool]] = None,
          now_iso: Optional[str] = None) -> Dict[str, Any]:
    """Resolve one anchor into one scene. Raises only on a REFUSED anchor: a scene for a spelling
    we cannot parse would be a confident answer to a question nobody asked."""
    from core.coord import target as T

    ex = exists or _repo_exists
    tgt = T.parse(anchor, roots=roots, exists=ex)        # refuses loudly; that is deliberate

    use = dict(_default_resolvers()) if resolvers is None else dict(resolvers)
    planes: List[Dict[str, Any]] = []

    for name in PLANES:
        fn = use.get(name)
        if fn is None:
            planes.append(_plane(name, "UNCHECKABLE", "not joined yet",
                                 fog=_NOT_YET.get(name, "no resolver"),
                                 cost={"class": "o1", "note": "not called"}))
            continue
        try:
            p = fn(tgt, roots=roots, level=level)
        except Exception as e:                                            # noqa: BLE001
            # An exception is a FINDING about this plane, never a reason for the scene to be
            # smaller. The reader learns which plane broke and why.
            planes.append(_plane(name, "error", "resolver failed",
                                 fog=f"{type(e).__name__}: {e}",
                                 cost={"class": "o1", "note": "failed"}))
            continue
        planes.append(_validate(_demote_unaddressable(p, T, roots, ex), level))

    anchored = {"address": tgt.key, "kind": tgt.kind, "work": tgt.work,
                "display": anchor, "ref_kind": tgt.ref_kind,
                "line": tgt.line, "col": tgt.col}

    return {
        "schema": SCHEMA,
        "subject": str(subject or ""),
        "anchor": anchored,
        "level": int(level),
        "generated_at": now_iso or _now_iso(),
        "planes": planes,
        "span": _span(planes),
        "fog": _scene_fog(planes, tgt),
        "epistemic": _epistemic(planes),
        "drill": _drill(tgt, planes),
        # Always empty, and the field exists because `orient` established the refusal contract on
        # it: a context read performs no effects, and saying so is cheaper than being trusted.
        "effects": [],
    }


# --------------------------------------------------------------------------- validation
def _plane(name, state, summary, rows=None, cost=None, fog="", receipts=None):
    return {"plane": name, "state": state, "summary": summary, "rows": rows or [],
            "cost": cost or {"class": "o1", "note": ""}, "fog": fog, "receipts": receipts or []}


def _validate(p: Dict[str, Any], level: int) -> Dict[str, Any]:
    state = p.get("state")
    if state not in STATES:
        raise ValueError(f"plane {p.get('plane')!r}: state {state!r} is not one of {STATES}. "
                         f"An untyped state is how a plane's silence becomes a zero.")
    if state == "UNCHECKABLE" and not str(p.get("fog") or "").strip():
        raise ValueError(f"plane {p.get('plane')!r}: UNCHECKABLE without a reason. A plane may say "
                         f"it could not look; it may not say so without saying why, or the state "
                         f"decays back into the silent zero it exists to prevent.")
    rows = list(p.get("rows") or [])
    if rows and state == "empty":
        raise ValueError(f"plane {p.get('plane')!r}: state 'empty' with {len(rows)} rows")
    if level < 1:
        p["rows"] = []            # L0 is summaries only
    else:
        p["rows"] = rows[:MAX_ROWS]
    if level < 2:
        p["receipts"] = []        # receipts are the L2 contour
    return p


def _demote_unaddressable(p: Dict[str, Any], T, roots, ex) -> Dict[str, Any]:
    """A row the doors cannot follow is a claim nobody can check, so it moves to fog by name."""
    keep, dropped = [], []
    for row in list(p.get("rows") or []):
        ref = str((row or {}).get("ref") or "")
        try:
            if not ref:
                raise T.TargetError("no ref")
            T.parse(ref, roots=roots, exists=lambda _k: True)
            keep.append(row)
        except Exception:                                                 # noqa: BLE001
            dropped.append(str((row or {}).get("what") or ref or "?"))
    if dropped:
        note = "rows without a resolvable ref: " + "; ".join(dropped[:6])
        p["fog"] = (str(p.get("fog") or "") + " | " + note).strip(" |")
    p["rows"] = keep
    if not keep and p.get("state") == "ok":
        p["state"] = "empty"
    return p


# --------------------------------------------------------------------------- the live planes
def _git_plane(tgt, *, roots, level=1):
    path = tgt.path or tgt.key
    if tgt.kind not in ("file", "file_line", "dir"):
        return _plane("git", "UNCHECKABLE", "anchor is not a path",
                      fog="git answers for paths; this anchor is a " + tgt.kind,
                      cost={"class": "o1", "note": "not called"})
    root = str(roots.main)
    cmd = ["git", "log", "-n", str(MAX_ROWS), "--format=%H%x1f%aI%x1f%an%x1f%s", "--", path]
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=20).stdout
    rows = []
    for line in (out or "").splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            rows.append({"ref": "sha:" + parts[0], "at": parts[1], "who": parts[2],
                         "what": parts[3]})
    return _plane("git", "ok" if rows else "empty",
                  f"{len(rows)} commit(s) touching this path" if rows
                  else "no commit in this repository touches this path",
                  rows=rows, cost={"class": "ologn", "note": "one git log, capped"},
                  fog="this checkout's history only; a rewritten sha resolves through the sha verb",
                  receipts=[" ".join(cmd)])


def _touches_plane(tgt, *, roots, level=1):
    """The spine, keyed on the W0.1 target. This is the plane W0.2 built tonight."""
    import json
    from core.comm.bus import Bus
    c = Bus("claude")._client
    raw = c.xrevrange("events:raw", count=4000)
    rows = []
    for mid, f in raw:
        try:
            v = next(iter(f.values()))
            d = json.loads(v.decode() if isinstance(v, bytes) else str(v))
        except Exception:                                                 # noqa: BLE001
            continue
        if d.get("kind") != "touch":
            continue
        det = d.get("detail") or {}
        hit = any(str(t.get("key")) == tgt.key for t in (det.get("targets") or []))
        if not hit:
            continue
        sid = str(mid.decode() if isinstance(mid, bytes) else mid)
        rows.append({"ref": f"event:events:raw:{sid}", "at": d.get("at"),
                     "who": d.get("agent_id") or "?",
                     "what": f"{det.get('tool')} ({d.get('session_id') or 'no session'})"})
        if len(rows) >= MAX_ROWS:
            break
    return _plane("touches", "ok" if rows else "empty",
                  f"{len(rows)} touch(es) on this exact key" if rows
                  else "no touch on this key in the ring",
                  rows=rows, cost={"class": "on", "note": "scans the ring head; W0.1's byref index "
                                                          "makes this o1 once touches are indexed"},
                  fog="the firehose ring only, newest 4,000; touches older than the ring are gone",
                  receipts=["xrevrange events:raw + filter detail.targets[].key == " + tgt.key])


def _default_resolvers() -> Dict[str, Callable]:
    return {"git": _git_plane, "touches": _touches_plane}


# --------------------------------------------------------------------------- scene-level fields
def _span(planes):
    ats = [r.get("at") for p in planes for r in (p.get("rows") or []) if r.get("at")]
    ats = sorted(str(a) for a in ats)
    return {"first_at": ats[0] if ats else None, "last_at": ats[-1] if ats else None,
            "buckets": []}


def _scene_fog(planes, tgt):
    fog = []
    unchecked = [p["plane"] for p in planes if p["state"] == "UNCHECKABLE"]
    if unchecked:
        fog.append(f"{len(unchecked)} of {len(PLANES)} planes not joined yet: "
                   + ", ".join(unchecked))
    broke = [p["plane"] for p in planes if p["state"] == "error"]
    if broke:
        fog.append("planes that failed: " + ", ".join(broke))
    if tgt.kind == "question":
        fog.append("a question is not an address; no plane was consulted")
    return fog


def _epistemic(planes):
    """UNKNOWN is the truthful floor, per `orient`'s precedent: a scene is only as current as the
    planes that actually answered, and most of them have not been built yet."""
    ok = sum(1 for p in planes if p["state"] == "ok")
    return {"authority": "mechanical_source",
            "currency": "unknown" if ok < len(PLANES) else "current",
            "basis": f"{ok} of {len(PLANES)} planes joined"}


def _drill(tgt, planes):
    if tgt.kind == "question":
        return f'py agent_cli.py cast "{tgt.key[:60]}"   # a question routes to cast, not to an anchor'
    for p in planes:
        if p["state"] == "ok" and p.get("rows"):
            return f"py agent_cli.py events --get {p['rows'][0]['ref']}"
    return f"py agent_cli.py context {tgt.key} --level 2   # receipts for every plane"


def _now_iso() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _repo_exists(key: str) -> bool:
    try:
        from core import paths
        return os.path.exists(os.path.join(str(paths.repo_root()), key.replace("/", os.sep)))
    except Exception:                                                     # noqa: BLE001
        return False


# --------------------------------------------------------------------------- render
def render(sc: Dict[str, Any]) -> str:
    a = sc["anchor"]
    out = [f"context  {a['display']}", f"  anchor   {a['address']}   ({a['kind']})",
           f"  subject  {sc['subject']}   level {sc['level']}   {sc['generated_at'][:19]}", ""]
    mark = {"ok": "+", "empty": ".", "UNCHECKABLE": "?", "error": "!"}
    for p in sc["planes"]:
        out.append(f"  {mark.get(p['state'], '?')} {p['plane']:<11} {p['state']:<12} {p['summary']}")
        for r in (p.get("rows") or []):
            out.append(f"      {str(r.get('at'))[:19]}  {str(r.get('who'))[:14]:<14} "
                       f"{str(r.get('what'))[:58]}")
            out.append(f"        {r.get('ref')}")
        if p["state"] in ("UNCHECKABLE", "error") and p.get("fog"):
            out.append(f"      why: {p['fog']}")
        for rec in (p.get("receipts") or []):
            out.append(f"      $ {rec}")
    if sc.get("fog"):
        out += ["", "  FOG:"] + [f"    {f}" for f in sc["fog"]]
    out += ["", f"  epistemic  {sc['epistemic']['currency']} ({sc['epistemic']['basis']})",
            f"  drill      {sc['drill']}"]
    return "\n".join(out)
