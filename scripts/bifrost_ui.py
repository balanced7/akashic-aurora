"""
bifrost_ui -- a realtime web console for watching (and steering) live agent collaboration on Bifrost.

A zero-dependency (Python stdlib only) local web server that bridges the Bifrost bus to a polished
browser UI. You see Claude and DeepSeek converse in real time, PAUSE them to interject, type messages
that wake the agents, and DRAG-AND-DROP files to share them into the project (agents can then read them
with their tools). Serves on 127.0.0.1 only -- it is a local cockpit, never exposed.

  py scripts/bifrost_ui.py                 # http://127.0.0.1:8787
  py scripts/bifrost_ui.py --port 9000

Transport: Server-Sent Events (bus -> browser, live) + plain POST (browser -> bus). No websockets, no
build step, no npm. Pause/loop-guard come from core/comm/control.py; messages from core/comm/bus.py.
"""
import argparse
import base64
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from core.comm.bus import Bus
from core.comm import control
from core.comm import promoter
from core.comm.launcher import get_launcher
from core.comm import room_feed
from core.trust import registry
from core.primitives.epistemic import epistemic_view_from_bus

DROPBOX = os.path.join(REPO, "dropbox")
BUS = Bus("user")   # the console posts to the bus as 'user'; also registers 'user' presence
_BUS_CACHE = {}     # per-ns Bus("user", namespace=ns) constructed lazily; never per-request


def _client(block_ms: int = 20000):
    """A Redis client with a long socket timeout, for the SSE blocking tail (mirrors bus._blocking_client)."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        return connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
            timeout_seconds=block_ms / 1000.0 + 5, decode_responses=True)
    except Exception:
        return None


def _fmt(sid, fields):
    """A raw Redis stream entry -> the message shape the browser renders."""
    def _loads(s):
        try:
            return json.loads(s)
        except Exception:
            return s
    msg = {
        "id": str(sid),
        "from": fields.get("frm", ""),
        "to": fields.get("to", ""),
        "kind": fields.get("kind", ""),
        "content": _loads(fields.get("content", '""')),
        "ts": fields.get("ts", ""),
        "meta": _loads(fields.get("meta", "{}")),
    }
    # T121 composition seam: attach the typed EpistemicView product so the
    # browser's m.epistemic boundary is populated. Fail-closed: a derivation
    # error degrades to the total-unknown product, never breaks rendering.
    try:
        msg["epistemic"] = epistemic_view_from_bus(msg).to_dict()
    except Exception:
        msg["epistemic"] = epistemic_view_from_bus({}).to_dict()
    return msg


def _inbox_streams(client, ns="bifrost"):
    try:
        return room_feed.streams_for(client, ns)
    except ValueError:
        raise
    except Exception:
        return []


def backfill(client, last_ids, ns="bifrost", per_stream=12):
    """Recent history across all inbox+broadcast streams, oldest-first; seeds last_ids gap-free."""
    collected = []
    for s in _inbox_streams(client, ns):
        try:
            entries = client.xrevrange(s, count=per_stream) or []
        except Exception:
            entries = []
        if entries:
            last_ids[s] = entries[0][0]           # newest id -> tail starts exactly after it
            for sid, fields in reversed(entries):
                collected.append(_fmt(sid, fields))
    collected.sort(key=lambda m: m["id"])
    return collected


def tail(client, last_ids, ns="bifrost", block_ms=15000):
    """Block up to block_ms for new entries across all streams; returns them, advancing last_ids."""
    streams = {s: last_ids.get(s, "$") for s in _inbox_streams(client, ns)}
    try:
        res = client.xread(streams, block=block_ms, count=50)
    except Exception:
        return []
    out = []
    for stream, entries in res or []:
        for sid, fields in entries:
            last_ids[stream] = sid
            out.append(_fmt(sid, fields))
    out.sort(key=lambda m: m["id"])
    return out


# ---- VFX bench presets ------------------------------------------------------------------------
# A FILE, deliberately, not localStorage. A preset in a browser's storage is invisible to the other
# party -- Daniil could tune something excellent and claude would have no way to read it, and vice
# versa. On disk it is a shared artefact: tune in the browser, read it with any tool, paste it into
# the state table, commit it. That is the whole difference between a shared bench and two private
# ones, and it costs one JSON file.
# ---- VFX sketches -----------------------------------------------------------------------------
# A sketch is a fragment shader being TRIED. It lives as a plain .frag file rather than inside
# agent-avatar.js, and that separation IS the buffer property: a sketch that does not compile costs
# you the sketch and never the console avatar, because nothing in production ever loads one.
# Promotion into STYLES stays a deliberate edit rather than a side effect of saving.
#
# Files, again, rather than browser storage -- a sketch Daniil pastes is one claude can read and
# improve, and a sketch claude writes shows up in Daniil's dropdown with no handover step.
# ---- VFX chunks + compositions ----------------------------------------------------------------
# A CHUNK is one reusable piece of shader with a declared role, stored as a .glsl file whose first
# line is a //! JSON header. Roles exist because a fragment shader has exactly three places a piece
# can go, and pretending otherwise is what makes shader node editors collapse into spaghetti:
#     helper   -- a top-level function; order-free, deduplicated by name
#     source   -- writes col/alpha; exactly one per composition, it is what you are looking at
#     modifier -- transforms col in place; ORDER MATTERS and that order is the composition
# Anything that does not fit one of the three is not a chunk, it is a new source.
#
# This is the part that remembers HOW rather than WHAT. Presets remember a tuning and sketches
# remember a finished shader; neither can tell you that tanh must come after the superlinear
# highlight, or that the cubic vignette must be normalised by the true corner distance or it
# blacks out the sides of a widescreen. Those facts lived only in commit messages, which is to say
# they were already lost.
# ---- VFX groups -------------------------------------------------------------------------------
# A GROUP is a named run of modifiers -- "filmic finish" = superlinear-highlight, tanh-tonemap,
# vignette-cubic, triangular-dither. It is the reusable unit that sits between a chunk (one idea)
# and a composition (a whole picture), and it is the one that actually gets reused: nobody reaches
# for a tone curve alone, they reach for the four-step finish that has always worked together.
#
# Stored EXPANDED, as the list of chunk names, not as a reference. A group is a shorthand for a
# sequence, not an indirection: expanding on drop means a composition never depends on a group
# file still existing or still meaning the same thing, and editing a group cannot silently change
# a picture somebody already saved.
# ---- VFX graphs -------------------------------------------------------------------------------
# A graph is nodes + typed edges. It is stored, not compiled, here -- codegen lives in the browser
# next to the thing that has to run it, so a graph that fails to compile fails where you can see it.
# ---- VFX snapshots ----------------------------------------------------------------------------
# THE MIRROR. claude cannot see rendered output -- every visual judgement this session has been
# made by counting pixels through readPixels, which is why "your eyes are the verification here"
# kept appearing. But claude CAN read an image file. So the bench writes one.
#
# This is the single highest-leverage thing in the whole bench: it turns "I measured 42,120 lit
# pixels and infer it looks right" into "I looked at it". A number can only confirm what you
# already suspected; a picture can surprise you, and being surprised is the entire value of
# looking.
# ---- VFX job queue: claude asks, the open bench renders --------------------------------------
# Every render this session cost 4-5 tool calls -- restart, navigate, inject JS, wait, read back --
# and kept breaking on browser-pane quirks. The fix is not a second renderer in Python: porting the
# shaders would duplicate every one of them into something that drifts. It is to let the bench that
# is ALREADY OPEN do the work, and give claude a client.
#
# One implementation, two callers. The page executes the same thumbShaderFor / renderSheet / snap
# it uses for its own buttons, so a CLI-requested thumbnail cannot disagree with a clicked one.
#
# The honest constraint: a /vfx tab must be open. That is stated in the CLI's error rather than
# left as a hang -- "no renderer attached" is a diagnosis, a timeout is a mystery.
_VFX_JOBS = {}
_VFX_SEQ = [0]


def _vfx_job_add(op, args):
    _VFX_SEQ[0] += 1
    jid = "j%d" % _VFX_SEQ[0]
    _VFX_JOBS[jid] = {"id": jid, "op": str(op or ""), "args": args or {},
                      "state": "pending", "result": None}
    # Keep the table small; a bench left open for a day should not accumulate a thousand records.
    if len(_VFX_JOBS) > 200:
        for k in sorted(_VFX_JOBS)[:100]:
            if _VFX_JOBS[k]["state"] == "done":
                _VFX_JOBS.pop(k, None)
    return _VFX_JOBS[jid]


# ---- WHICH TAB IS THE RENDER FARM --------------------------------------------------------------
# Found by reproducing it: open /vfx a second time and that tab ALSO starts polling for jobs, so
# renders split between the two at random depending on which one's timer fires first. That is bad
# in every case and actively broken in the common one -- the second tab is usually a background or
# hidden pane, where the browser throttles rAF and never composites, so the job it wins either
# stalls or captures a frame that was never drawn. The failure has no symptom at the CLI beyond a
# render that took the wrong path or timed out, which sends you debugging the shader.
#
# So the renderer is a LEASE, not a free-for-all: one tab holds it, renews it by polling, and loses
# it after a few seconds of silence so closing the tab hands the farm to whoever is left. A visible
# tab may take the lease from a hidden one, because a hidden holder cannot do the job it is
# holding -- which is the exact case that made this a bug rather than a curiosity.
_VFX_LEASE = {"worker": "", "at": 0.0, "visible": True}
VFX_LEASE_TTL = 6.0


def _vfx_lease(worker, visible):
    """True if `worker` may render right now. Renews the lease as a side effect of asking."""
    now = time.time()
    cur = _VFX_LEASE
    held = bool(cur["worker"]) and (now - cur["at"]) < VFX_LEASE_TTL
    if held and cur["worker"] != worker:
        holder_visible = bool(cur.get("visible"))
        # RULE 1, and it outranks everything: a tab that can actually draw displaces one that
        # cannot. Nothing else may promote a hidden tab over a visible one.
        if visible and not holder_visible:
            pass
        # RULE 2, and only BETWEEN EQUALS. A page from before the lease existed identifies as
        # 'legacy'; it still renders (a deploy must not stop a working bench) but its claim is weak,
        # so a reloaded tab takes the farm rather than waiting behind a holder that cannot be asked
        # about. Ordering this rule ABOVE rule 1 is a bug that reproduced immediately and loudly:
        # a hidden pane and a visible legacy tab traded the lease twice a second, so every render
        # was a coin flip on whether it landed in a tab that composites.
        elif visible == holder_visible and cur["worker"] == "legacy" and worker != "legacy":
            pass
        else:
            return False
    cur["worker"], cur["at"], cur["visible"] = worker, now, bool(visible)
    return True


def _vfx_lease_state():
    now = time.time()
    held = bool(_VFX_LEASE["worker"]) and (now - _VFX_LEASE["at"]) < VFX_LEASE_TTL
    return {"attached": held, "worker": _VFX_LEASE["worker"] if held else "",
            "visible": bool(_VFX_LEASE["visible"]) if held else False,
            "idle": round(now - _VFX_LEASE["at"], 2) if _VFX_LEASE["worker"] else None}


def _vfx_job_next(worker="", visible=True):
    """Hand out ONE pending job and mark it running. One at a time on purpose: these are GPU
    captures, and two concurrent recordings on one context would interleave and corrupt both."""
    # An unnamed caller is a page that predates the lease. It gets a name anyway, so /vfx/renderer
    # never reports "nothing attached" while something is quietly rendering -- a status surface
    # that under-reports is worse than none, because it sends you to fix a problem you do not have.
    if not _vfx_lease(worker or "legacy", visible):
        return {"viewer": True}
    for k in sorted(_VFX_JOBS, key=lambda x: int(x[1:])):
        j = _VFX_JOBS[k]
        if j["state"] == "pending":
            j["state"] = "running"
            return j
    return None


def _vfx_job_result(jid, result):
    j = _VFX_JOBS.get(str(jid or ""))
    if not j:
        return {"ok": False, "error": "unknown job"}
    j["state"] = "done"
    j["result"] = result
    # EVERY render announces itself. This is the automatic half of the feed and it matters more
    # than the deliberate half: narration that must be remembered is narration that gets skipped
    # on exactly the busy passes worth watching. Posting from HERE rather than from the browser
    # means one place covers every op, including the ones added later.
    _vfx_feed_add(_vfx_feed_from_job(j))
    return {"ok": True}


# ---- THE FEED: claude's side of the mirror -----------------------------------------------------
# The bench was asymmetric. Daniil's chat box attaches a snapshot so claude can LOOK at what he is
# talking about -- that asymmetry was noticed and fixed in claude's favour first, because claude
# was the one flying blind. But it left the opposite hole: in a bench where claude makes the
# renders, claude could only send WORDS back. Daniil got told about pictures he could not see
# unless he went and opened files.
#
# So: an append-only feed of what claude is doing, carrying the IMAGE, polled by the open page and
# rendered into the same thread the conversation already uses. Not a second surface -- the point is
# that "what claude said" and "what claude rendered" are one stream, in order, because a render
# without its reason is a pretty picture and a reason without its render is a claim.
#
# In memory on purpose. This is a live channel between two people looking at the same screen; the
# durable record is the PNG on disk and the commit, both of which already exist. A feed that
# survived restarts would be a third store of the same facts.
_VFX_FEED = []
_VFX_FEED_SEQ = [0]


def _vfx_feed_url(path):
    """Map a repo-relative render path to a URL the page can put in an <img>."""
    p = str(path or "").replace("\\", "/")
    leaf = p.rsplit("/", 1)[-1]
    if not leaf.endswith(".png"):
        return ""
    if "vfx-thumbs" in p:
        return "/vfx/thumb/" + leaf
    return "/vfx/snap/" + leaf


def _vfx_feed_add(entry):
    if not entry:
        return None
    _VFX_FEED_SEQ[0] += 1
    entry["id"] = _VFX_FEED_SEQ[0]
    entry.setdefault("ts", time.time())
    entry.setdefault("from", "claude")
    _VFX_FEED.append(entry)
    # A bench left open all day must not grow without bound. The page only ever asks for what it
    # has not seen, so trimming the head costs nothing a live watcher will notice.
    if len(_VFX_FEED) > 300:
        del _VFX_FEED[:100]
    return entry


def _vfx_feed_from_job(j):
    """Turn a finished job into a feed entry. Failures post TOO -- a render that silently does not
    appear is indistinguishable from a renderer that died, and those need opposite responses."""
    res = j.get("result") or {}
    args = j.get("args") or {}
    ok = bool(res.get("ok"))
    # The subject, not the verb: "thumb swirl" tells you what you are looking at; "thumb" does not.
    subject = args.get("chunk") or args.get("state") or args.get("name") or args.get("style") or ""
    return {"kind": "render", "op": j.get("op", ""), "ok": ok,
            "text": (args.get("say") or "").strip(),
            "label": (str(j.get("op", "")) + " " + str(subject)).strip(),
            "error": "" if ok else str(res.get("error") or "failed")[:200],
            "path": res.get("path") or "", "url": _vfx_feed_url(res.get("path"))}


def _vfx_feed_since(since):
    try:
        n = int(since)
    except (TypeError, ValueError):
        n = 0
    out = [e for e in _VFX_FEED if e["id"] > n]
    # A FRESH PAGE CATCHES UP, IT DOES NOT REPLAY THE DAY. since=0 is a reload or a newly opened
    # tab, and handing it 300 entries would fire 300 image requests at once -- turning the one
    # action that recovers a broken bench (reload it) into the one that hammers it. A live watcher
    # never hits this: they are always asking for the handful since their last tick.
    if n <= 0:
        out = out[-30:]
    return {"entries": out, "last": _VFX_FEED_SEQ[0]}


# ---- VFX thumbnails ---------------------------------------------------------------------------
# A visual index for the block palette. Seventeen names in a list is a list; seventeen TILES that
# each show what the block does is something you can shop from -- and for a modifier the tile
# renders a REFERENCE source WITH that one effect applied, so it shows the block DOING its job
# rather than showing an object that happens to be nearby.
#
# Alpha is PRESERVED here, unlike snapshots. A snapshot is composited on the console ground because
# claude has to judge it against the background it lives on; a thumbnail is placed on a UI chip
# whose colour the tile cannot know, so it must carry transparency and let the chip show through.
# Same capture, opposite requirement -- which is why they are two paths and not one.
VFX_THUMBS = os.path.join(REPO, "design", "vfx-thumbs")


def _vfx_thumb_write(name, data_url):
    import base64
    safe = "".join(c for c in str(name or "") if c.isalnum() or c in "-_")[:60]
    if not safe:
        return {"ok": False, "error": "bad name"}
    try:
        head, _, b64 = str(data_url or "").partition(",")
        if "base64" not in head or not b64:
            return {"ok": False, "error": "expected a base64 data URL"}
        raw = base64.b64decode(b64)
        if len(raw) > 2 * 1024 * 1024:
            return {"ok": False, "error": "too large for a thumbnail"}
        os.makedirs(VFX_THUMBS, exist_ok=True)
        path = os.path.join(VFX_THUMBS, safe + ".png")
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)
        return {"ok": True, "name": safe, "bytes": len(raw)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _vfx_clip_write(name, data_url):
    """Write a WebM loop. Separate from the PNG path because they are different artefacts with
    different lifetimes: the sprite is the FALLBACK and must survive even when a clip exists, so a
    failed recording never leaves a block with no tile at all."""
    import base64
    safe = "".join(c for c in str(name or "") if c.isalnum() or c in "-_")[:60]
    if not safe:
        return {"ok": False, "error": "bad name"}
    try:
        head, _, b64 = str(data_url or "").partition(",")
        if "base64" not in head or not b64:
            return {"ok": False, "error": "expected a base64 data URL"}
        raw = base64.b64decode(b64)
        if len(raw) > 6 * 1024 * 1024:
            return {"ok": False, "error": "clip too large"}
        os.makedirs(VFX_THUMBS, exist_ok=True)
        path = os.path.join(VFX_THUMBS, safe + ".webm")
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)
        return {"ok": True, "name": safe, "bytes": len(raw)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _vfx_clips_list():
    try:
        return sorted(f[:-5] for f in os.listdir(VFX_THUMBS) if f.endswith(".webm"))
    except Exception:
        return []


def _vfx_thumbs_list():
    try:
        return sorted(f[:-4] for f in os.listdir(VFX_THUMBS) if f.endswith(".png"))
    except Exception:
        return []


VFX_SNAPS = os.path.join(REPO, "design", "vfx-snaps")


def _vfx_snap_write(name, data_url):
    """Decode a data: URL from canvas.toDataURL and write a PNG claude can open with Read."""
    import base64
    safe = "".join(c for c in str(name or "snap") if c.isalnum() or c in "-_")[:50] or "snap"
    try:
        head, _, b64 = str(data_url or "").partition(",")
        if "base64" not in head or not b64:
            return {"ok": False, "error": "expected a base64 data URL"}
        raw = base64.b64decode(b64)
        if len(raw) > 8 * 1024 * 1024:            # a bench canvas is ~100KB; anything near 8MB is
            return {"ok": False, "error": "too large"}   # not a canvas and should not be written
        os.makedirs(VFX_SNAPS, exist_ok=True)
        path = os.path.join(VFX_SNAPS, safe + ".png")
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(raw)
        os.replace(tmp, path)
        # The RELATIVE path is what goes back, because that is what claude pastes into Read.
        return {"ok": True, "path": "design/vfx-snaps/" + safe + ".png", "bytes": len(raw)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


VFX_GRAPHS = os.path.join(REPO, "design", "vfx-graphs.json")


def _vfx_graphs_read():
    try:
        with open(VFX_GRAPHS, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _vfx_graphs_write(name, value):
    key = "".join(c for c in str(name or "") if c.isalnum() or c in "-_ ")[:60].strip()
    if not key:
        return {"ok": False, "error": "name required"}
    try:
        os.makedirs(os.path.dirname(VFX_GRAPHS), exist_ok=True)
        cur = _vfx_graphs_read()
        cur[key] = value
        tmp = VFX_GRAPHS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        os.replace(tmp, VFX_GRAPHS)
        return {"ok": True, "name": key, "count": len(cur)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


VFX_GROUPS = os.path.join(REPO, "design", "vfx-groups.json")


def _vfx_groups_read():
    try:
        with open(VFX_GROUPS, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _vfx_groups_write(name, items):
    key = "".join(c for c in str(name or "") if c.isalnum() or c in "-_ ")[:60].strip()
    if not key:
        return {"ok": False, "error": "name required"}
    if not isinstance(items, list) or not items:
        return {"ok": False, "error": "empty group"}
    try:
        os.makedirs(os.path.dirname(VFX_GROUPS), exist_ok=True)
        cur = _vfx_groups_read()
        cur[key] = [str(x)[:80] for x in items]
        tmp = VFX_GROUPS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        os.replace(tmp, VFX_GROUPS)
        return {"ok": True, "name": key, "count": len(cur)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


VFX_CHUNKS = os.path.join(REPO, "design", "vfx-chunks")
VFX_COMPOS = os.path.join(REPO, "design", "vfx-compositions.json")


def _vfx_chunks_read():
    """All chunks, parsed. Fail-open per file: one malformed chunk must not hide the library."""
    out = []
    try:
        names = sorted(f for f in os.listdir(VFX_CHUNKS) if f.endswith(".glsl"))
    except Exception:
        return out
    for fn in names:
        try:
            with open(os.path.join(VFX_CHUNKS, fn), "r", encoding="utf-8") as fh:
                txt = fh.read()
            head, _, body = txt.partition("\n")
            meta = json.loads(head[3:].strip()) if head.startswith("//!") else {}
            meta["body"] = body.strip()
            meta.setdefault("name", fn[:-5])
            meta.setdefault("kind", "modifier")
            out.append(meta)
        except Exception as exc:
            out.append({"name": fn[:-5], "kind": "broken", "note": str(exc)[:160], "body": ""})
    return out


def _vfx_compos_read():
    try:
        with open(VFX_COMPOS, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _vfx_compos_write(name, value):
    """Merge one composition. Read-modify-write through a temp file, same as the presets: two
    saves in a session must not clobber each other and a crash must not leave a half-written
    library behind."""
    key = "".join(c for c in str(name or "") if c.isalnum() or c in "-_ ")[:60].strip()
    if not key:
        return {"ok": False, "error": "name required"}
    try:
        os.makedirs(os.path.dirname(VFX_COMPOS), exist_ok=True)
        cur = _vfx_compos_read()
        cur[key] = value
        tmp = VFX_COMPOS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        os.replace(tmp, VFX_COMPOS)
        return {"ok": True, "name": key, "count": len(cur)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


VFX_SKETCHES = os.path.join(REPO, "design", "vfx-sketches")


def _sketch_path(name):
    """Reject anything that is not a bare name. This endpoint WRITES FILES, so accepting a path
    here would be a write-anywhere primitive; the whitelist is the point, not decoration."""
    safe = "".join(c for c in str(name or "") if c.isalnum() or c in "-_")[:60]
    if not safe:
        return None
    return os.path.join(VFX_SKETCHES, safe + ".frag"), safe


def _vfx_sketches_list():
    try:
        return sorted(f[:-5] for f in os.listdir(VFX_SKETCHES) if f.endswith(".frag"))
    except Exception:
        return []                      # no sketches dir yet is not an error


def _vfx_sketch_read(name):
    r = _sketch_path(name)
    if not r:
        return {"ok": False, "error": "bad name"}
    path, safe = r
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return {"ok": True, "name": safe, "src": fh.read()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _vfx_sketch_write(name, src):
    r = _sketch_path(name)
    if not r:
        return {"ok": False, "error": "bad name"}
    path, safe = r
    try:
        os.makedirs(VFX_SKETCHES, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(str(src or ""))
        os.replace(tmp, path)          # atomic, same reason as the presets file
        return {"ok": True, "name": safe, "bytes": len(src or "")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


VFX_PRESETS = os.path.join(REPO, "design", "vfx-presets.json")


def _vfx_presets_read():
    try:
        with open(VFX_PRESETS, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except FileNotFoundError:
        return {}                      # no presets yet is not an error, it is Tuesday
    except Exception:
        return {}                      # fail-open: a corrupt preset file must not break the bench


def _vfx_presets_write(name, value):
    """Merge one preset. Read-modify-write so two saves in a session cannot clobber each other."""
    try:
        os.makedirs(os.path.dirname(VFX_PRESETS), exist_ok=True)
        cur = _vfx_presets_read()
        cur[str(name)[:80]] = value
        tmp = VFX_PRESETS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cur, fh, indent=2, sort_keys=True)
        os.replace(tmp, VFX_PRESETS)   # atomic: a crash mid-write leaves the old file intact,
        return {"ok": True, "count": len(cur)}      # never a half-written one
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            return self._html()
        if path == "/status":                   # legacy — still works; /api/now is canonical
            return self._json(self._status())
        if path == "/vitals":                   # legacy — still works; /api/now is canonical
            return self._json(self._vitals())
        if path == "/api/now":                  # TRUTH/NOISE tier: one call to rule all cards
            return self._json(self._api_now())
        if path == "/api/channels":             # side-channel visibility (Daniil's standing ask)
            return self._json(self._api_channels())
        if path == "/events":
            return self._events()
        if path == "/launcher/status":
            return self._json(get_launcher().registry())
        if path == "/episode/current":
            return self._json(self._episode_current())
        if path == "/aurora-shader.js":
            return self._static("scripts/aurora-shader.js", "application/javascript")
        if path == "/bifrost_viz.js":
            return self._static("scripts/bifrost_viz.js", "application/javascript")
        if path == "/theme-void.js":
            return self._static("scripts/theme-void.js", "application/javascript")
        if path == "/presence-rail.js":
            return self._static("scripts/presence-rail.js", "application/javascript")
        if path == "/presence-cloud.js":
            return self._static("scripts/presence-cloud.js", "application/javascript")
        if path == "/rail.js":
            return self._static("scripts/rail.js", "application/javascript")
        if path == "/timeline.js":
            return self._static("scripts/timeline.js", "application/javascript")
        if path == "/agent-avatar.js":
            return self._static("scripts/agent-avatar.js", "application/javascript")
        if path == "/activity-line.js":
            return self._static("scripts/activity-line.js", "application/javascript")
        if path == "/vfx":
            return self._static("scripts/vfx.html", "text/html; charset=utf-8")
        if path == "/vfx/presets":
            return self._json(_vfx_presets_read())
        if path == "/vfx/sketches":
            return self._json({"names": _vfx_sketches_list()})
        if path == "/vfx/chunks":
            return self._json({"chunks": _vfx_chunks_read()})
        if path == "/vfx/thumbs":
            return self._json({"names": _vfx_thumbs_list()})
        if path == "/vfx/clips":
            return self._json({"names": _vfx_clips_list()})
        if path == "/vfx/job/next":
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._json(_vfx_job_next((q.get("worker") or [""])[0],
                                            (q.get("visible") or ["1"])[0] != "0") or {})
        if path == "/vfx/renderer":
            return self._json(_vfx_lease_state())
        if path.startswith("/vfx/job/"):
            return self._json(_VFX_JOBS.get(path.rsplit("/", 1)[-1]) or {"error": "unknown job"})
        if path.startswith("/vfx/clip/"):
            leaf = path.rsplit("/", 1)[-1]
            safe = "".join(c for c in leaf if c.isalnum() or c in "-_.")
            if not safe.endswith(".webm"):
                return self.send_error(404)
            return self._static("design/vfx-thumbs/" + safe, "video/webm")
        if path.startswith("/vfx/thumb/"):
            leaf = path.rsplit("/", 1)[-1]
            safe = "".join(c for c in leaf if c.isalnum() or c in "-_.")
            if not safe.endswith(".png"):
                return self.send_error(404)
            return self._static("design/vfx-thumbs/" + safe, "image/png")
        if path.startswith("/vfx/snap/"):
            # Snapshots were write-only until now: claude wrote them, and the only reader was
            # claude's own Read tool. Serving them is what lets the render appear in the page
            # instead of merely being reported to have happened.
            leaf = path.rsplit("/", 1)[-1]
            safe = "".join(c for c in leaf if c.isalnum() or c in "-_.")
            if not safe.endswith(".png"):
                return self.send_error(404)
            return self._static("design/vfx-snaps/" + safe, "image/png")
        if path == "/vfx/feed":
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._json(_vfx_feed_since((q.get("since") or ["0"])[0]))
        if path == "/vfx/compositions":
            return self._json(_vfx_compos_read())
        if path == "/vfx/groups":
            return self._json(_vfx_groups_read())
        if path == "/vfx/graphs":
            return self._json(_vfx_graphs_read())
        if path.startswith("/vfx/sketch"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            return self._json(_vfx_sketch_read((q.get("name") or [""])[0]))
        self.send_error(404)

    def _html(self):
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, relpath, mime):
        """Serve a static file from the repo root. Caches nothing (dev cockpit)."""
        fpath = os.path.join(REPO, relpath.replace("/", os.sep))
        try:
            with open(fpath, "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            # NO-CACHE, and this was a real source of confusion rather than a nicety. Every asset
            # here is edited live and reloaded constantly; without these headers a browser can
            # serve a stale copy after a restart, so a fix that IS on disk and IS being served
            # still appears not to work. That failure looks exactly like a broken change, which is
            # the most expensive kind of wrong -- it sends you hunting in the code you just fixed.
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (FileNotFoundError, PermissionError):
            self.send_error(404)

    def _status(self):
        try:
            agents = BUS.presence()
        except Exception:
            agents = []
        # Per-agent awareness: pending nudge (hard) + queued steer (soft) + whether a runner holds the
        # singleton lock. Lets the roster show, at a glance, who's being signalled and who's actually live.
        signals = {}
        try:
            from core.comm import nudge, runner_lock
            for a in agents:
                aid = a.get("agent")
                if not aid:
                    continue
                signals[aid] = {"nudged": nudge.is_nudged(aid),
                                "steer_pending": nudge.steer_pending(aid),
                                "runner": bool(runner_lock.holder(aid))}
        except Exception:
            signals = {}
        # Known: ALL registered agents (always visible, even offline) + any agent currently online.
        # The roster shows every agent the user might want to message, not just ACL-registered ones.
        known = []
        try:
            known = sorted([g.agent_id for g in registry.grants()])
            # Always include agents that have ever appeared on the bus (even if not ACL'd)
            for a in agents:
                aid = a.get("agent")
                if aid and aid not in known:
                    known.append(aid)
            known.sort()
        except Exception:
            pass
        return {"paused": control.is_paused(), "pause": control.pause_status(),
                "agents": agents, "known": known, "activities": control.get_activities(),
                "signals": signals, "max_hops": control.MAX_HOPS,
                "halted": control.halted_agents(),
                "narration": control.get_narration_level()}   # claude reasoning visibility: off|key|full

    def _vitals(self):
        """T079-E4: engine-room vitals for all known agents (heartbeat + runtimes +
        tokens + pages + daemon_live + lane depths + fence phase). Polled at 2s."""
        try:
            from core.comm.engine_vitals import gauge_snapshot
            from core.comm.lane_depths import lane_depths
            from core.comm.fence_phase import fence_phase
            known = {"claude": None, "deepseek": None}  # default agents
            try:
                for g in registry.grants():
                    known[g.agent_id] = None
                agents = BUS.presence()
                for a in agents:
                    aid = a.get("agent")
                    if aid and aid not in known:
                        known[aid] = None
            except Exception:
                pass
            result = {}
            for a in known:
                snap = gauge_snapshot(a)
                try:
                    snap["lanes"] = lane_depths(a)
                except Exception:
                    snap["lanes"] = {}
                result[a] = snap
            # fence phases for active arcs
            try:
                result["_fence"] = {"engine-room": fence_phase("engine-room"),
                                    "capability-surface": fence_phase("capability-surface"),
                                    "presence-autopilot": fence_phase("presence-autopilot")}
            except Exception:
                result["_fence"] = {}
            return result
        except Exception:
            return {}

    def _api_now(self):
        """TRUTH/NOISE tier: one endpoint for every card on the console — merges
        /status (presence/control/activities) + /vitals (engine-room gauges) into
        a single JSON blob. Accepts ?agents=X,Y,Z for a batch call served as one
        Redis pipeline. The frontend's single poll scheduler calls this, not the
        scattered /status + /vitals loops."""
        import urllib.parse
        qs = urllib.parse.parse_qs(self.path.split("?", 1)[-1] if "?" in self.path else "")
        requested = [a.strip() for a in qs.get("agents", [""])[0].split(",") if a.strip()] if "agents" in qs else None
        try:
            # ---- status half (presence + control) -------------------------------
            status = self._status()
            # ---- vitals half (engine-room gauges, per-agent) ---------------------
            vitals = self._vitals()
            # ---- seat-class honesty: per-agent seat type for honest vocab -------
            from core.comm import runner_lock, daemon_state
            daemon_live = {}
            seat_class = {}
            agents_list = requested or sorted(set(
                [a.get("agent","") for a in status.get("agents",[])] +
                list((vitals or {}).keys())
            ))
            for a in agents_list:
                if not a or a == "_fence":
                    continue
                daemon_live[a] = daemon_state.daemon_is_live(a)
                rh = runner_lock.holder(a)
                rtoken = str((rh or {}).get("token", ""))
                if rh and not rtoken.startswith("daemon:"):
                    seat_class[a] = "runner"     # real runner holds the lock directly
                elif daemon_live[a] or rtoken.startswith("daemon:"):
                    seat_class[a] = "listening"  # daemon holds watch (alpha-mode lock or delta daemon)
                elif any(a == s.get("agent","") for s in status.get("agents",[])):
                    seat_class[a] = "seat"       # on bus, not a runner — harness/launcher
                else:
                    seat_class[a] = "unseated"
            # ---- progress (turn_metrics live view, per agent) -----------
            progress = {}
            try:
                from core.comm.turn_metrics import progress_view
                for a in agents_list:
                    if not a or a == "_fence":
                        continue
                    pv = progress_view(a)
                    if pv:
                        progress[a] = pv
            except Exception:
                progress = {}
            # ---- assemble --------------------------------------------------------
            return {
                "status": status,
                "vitals": {a: vitals.get(a, {}) for a in agents_list if a != "_fence"},
                "fence": vitals.get("_fence", {}),
                "seat_class": seat_class,
                "daemon_live": daemon_live,
                "progress": progress,
            }
        except Exception:
            return {}

    def _api_channels(self):
        """Discover SIDE CHANNELS -- agent groups talking on a non-default namespace.

        Daniil's standing ask: "visibility for side chats for AI groups". Today the console
        reads ONE namespace (bifrost), so a side conversation is not merely unlisted -- it is
        structurally invisible. Tonight's own example: claude and deepseek-ui have been working
        the UI rebuild on namespace `uiwork` for hours, and nothing on this page could show it.

        A namespace is not registered anywhere, so it must be DISCOVERED. Every live seat writes
        `<ns>:worklive:<agent>#<sid8>`, which makes that key family the cheapest honest census --
        a channel exists exactly when somebody is beating in it. Read-only, no cursor touched,
        no consumer seat taken: this must never be able to steal mail from the very seats it
        reports on (the Eye rule -- observe without disturbing any reader).

        Bounded by construction: SCAN with a count cap rather than KEYS, and only worklive keys.
        Returns [] on any failure -- a discovery surface that cannot answer says nothing rather
        than inventing a fleet.
        """
        import os as _os
        default_ns = _os.environ.get("BIFROST_NAMESPACE", "bifrost")
        out, seen = [], {}
        try:
            from core.comm.bus import _connect
            r = _connect()
            if r is None:
                return {"channels": [], "default": default_ns,
                        "note": "store unreachable -- channel discovery unavailable"}
            scanned = 0
            for raw in r.scan_iter(match="*:worklive:*", count=200):
                scanned += 1
                if scanned > 4000:          # hard cap: a census must not become a scan storm
                    break
                key = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
                ns = key.split(":worklive:", 1)[0]
                seat = key.split(":worklive:", 1)[1] if ":worklive:" in key else ""
                if not ns:
                    continue
                d = seen.setdefault(ns, {"ns": ns, "seats": set()})
                if seat:
                    d["seats"].add(seat)
            for ns, d in sorted(seen.items()):
                seats = sorted(d["seats"])
                out.append({
                    "ns": ns,
                    "is_default": ns == default_ns,
                    "seats": seats,
                    "count": len(seats),
                    # agents, not incarnations -- "who is in the room" is the operator's question
                    "agents": sorted({s.split("#", 1)[0] for s in seats}),
                })
        except Exception as e:
            return {"channels": [], "default": default_ns,
                    "note": f"discovery failed: {type(e).__name__}"}
        return {"channels": out, "default": default_ns,
                "checked": "worklive keys only (a channel exists when someone beats in it)",
                "not_checked": "namespaces with no live seat are invisible here BY DESIGN -- "
                               "an empty room is not a conversation"}

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _events(self):
        import urllib.parse
        import os as _os
        default_ns = _os.environ.get("BIFROST_NAMESPACE", "bifrost")
        qs = urllib.parse.parse_qs(self.path.split("?", 1)[-1] if "?" in self.path else "")
        ns_list = qs.get("ns", [default_ns])
        ns = ns_list[0].strip() if ns_list else default_ns
        if not room_feed.valid_namespace(ns):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"invalid namespace: {ns!r} — a room name is a bare token".encode("utf-8"))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        client = _client()
        if client is None:
            self._sse({"from": "system", "kind": "note", "content": "bus offline (Redis unreachable)",
                       "ts": "", "meta": {}, "id": "0"})
            return
        last_ids = {}
        try:
            for m in backfill(client, last_ids, ns):
                self._sse(m)
            self._sse({"from": "system", "kind": "_ready", "content": "", "ts": "", "meta": {}, "id": "0"})
            while True:
                entries = tail(client, last_ids, ns, block_ms=15000)
                if entries:
                    for m in entries:
                        self._sse(m)
                else:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _sse(self, obj):
        self.wfile.write(("data: " + json.dumps(obj, default=str) + "\n\n").encode("utf-8"))
        self.wfile.flush()

    # ------------------------------------------------------------------ POST
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            data = {}
        if path == "/vfx/sketch":
            return self._json(_vfx_sketch_write(data.get("name"), data.get("src")))
        if path == "/vfx/compositions":
            return self._json(_vfx_compos_write(data.get("name"), data.get("value")))
        if path == "/vfx/groups":
            return self._json(_vfx_groups_write(data.get("name"), data.get("items")))
        if path == "/vfx/graphs":
            return self._json(_vfx_graphs_write(data.get("name"), data.get("value")))
        if path == "/vfx/snap":
            return self._json(_vfx_snap_write(data.get("name"), data.get("png")))
        if path == "/vfx/thumb":
            return self._json(_vfx_thumb_write(data.get("name"), data.get("png")))
        if path == "/vfx/clip":
            return self._json(_vfx_clip_write(data.get("name"), data.get("webm")))
        if path == "/vfx/job":
            return self._json(_vfx_job_add(data.get("op"), data.get("args")))
        if path == "/vfx/job/result":
            return self._json(_vfx_job_result(data.get("id"), data.get("result")))
        if path == "/vfx/feed":
            # The DELIBERATE half: claude narrating intent between renders. Kept separate from the
            # bus on purpose -- the bus is the conversation, which is durable and arrives at
            # claude's next turn; this is a live shoulder-to-shoulder channel about the thing on
            # screen right now, and mixing the two would put "watch this gap close" in the mailbox.
            txt = str(data.get("text") or "").strip()
            if not txt:
                return self._json({"ok": False, "error": "text required"})
            e = _vfx_feed_add({"kind": str(data.get("kind") or "say"), "text": txt[:2000],
                               "from": str(data.get("from") or "claude")[:32],
                               "label": str(data.get("label") or "")[:80],
                               "path": "", "url": "", "ok": True, "error": ""})
            return self._json({"ok": True, "id": e["id"]})
        if path == "/vfx/presets":
            name = str(data.get("name") or "").strip()
            if not name:
                return self._json({"ok": False, "error": "name required"})
            return self._json(_vfx_presets_write(name, data.get("value")))
        if path == "/send":
            return self._send(data)
        if path == "/pause":
            reason = data.get("reason", "console")
            control.pause(reason=reason, by="user")
            promoter.promote_control("pause", reason=reason, by="user")
            return self._json(self._status())
        if path == "/resume":
            control.resume()
            promoter.promote_control("resume", by="user")
            return self._json(self._status())
        if path == "/upload":
            return self._upload(data)
        if path == "/launcher/launch":
            tag = data.get("agent_id") or data.get("tag") or ""
            prompt = data.get("prompt") or ""
            result = get_launcher().launch(tag, prompt=prompt)
            return self._json(result)
        if path == "/launcher/kill":
            tag = data.get("agent_id") or data.get("tag") or ""
            result = get_launcher().kill(tag)
            return self._json(result)
        if path == "/launcher/revive":
            tag = data.get("agent_id") or data.get("tag") or ""
            result = get_launcher().revive(tag, reason="manual")
            return self._json(result)
        if path == "/launcher/arm-revive":
            tag = data.get("agent_id") or data.get("tag") or ""
            result = get_launcher().arm_revive(tag, bool(data.get("on")))
            return self._json(result)
        if path == "/launcher/snapshot":
            from core.comm import session_state
            result = session_state.save(label=data.get("label") or "")
            return self._json(result)
        if path == "/launcher/restore":
            from core.comm import session_state
            result = session_state.resume(label=data.get("label") or "launcher-restore")
            return self._json(result)
        if path == "/launcher/session-status":
            result = get_launcher().session_snapshot()
            return self._json(result)
        if path == "/reload":
            self._json({"ok": True, "reloading": True})
            threading.Thread(target=lambda: (time.sleep(0.3), _reexec()), daemon=True).start()
            return
        if path == "/negotiate":
            return self._negotiate(data)
        if path == "/narration":
            return self._narration(data)
        if path == "/episode/close":
            return self._episode_close(data)
        if path == "/episode/accept":
            return self._episode_accept(data)
        self.send_error(404)

    # --- session bookends (S4): the episode panel's backend --------------------------------------
    # Thin adapters over core/narrative/episode(_suggester) emitting the locked contract
    # (docs/library/design/20260701_session-bookends-design-for-peer-review_c38e0c.md sec.6), composed exactly like the CLI door
    # (agent_cli `episode current` also injects the S3 suggestion). Lazy imports + fail-soft:
    # the console must keep serving even if the narrative layer hiccups.
    def _episode_current(self):
        try:
            from core.narrative.episode import current_episode
            out = current_episode()
            try:
                from core.narrative.episode_suggester import suggest
                if out.get("current_chapter"):
                    out["current_chapter"]["suggestion"] = suggest()
            except Exception:
                pass
            return out
        except Exception as e:
            return {"current_chapter": None, "error": f"episode layer unavailable: {type(e).__name__}"}

    def _episode_close(self, data):
        try:
            from core.narrative.episode import close_episode
            return self._json(close_episode(
                title=data.get("title"), description=data.get("description"),
                why=data.get("why"), finalize=bool(data.get("finalize"))))
        except Exception as e:
            return self._json({"draft": None, "error": f"close failed: {type(e).__name__}"}, 500)

    def _episode_accept(self, data):
        try:
            from core.narrative.episode import accept_episode
            cid = str(data.get("chapter_id") or "")
            if not cid:
                return self._json({"error": "chapter_id required"}, 400)
            return self._json(accept_episode(None, cid, title=data.get("title"),
                                             description=data.get("description"),
                                             why=data.get("why")))
        except Exception as e:
            return self._json({"error": f"accept failed: {type(e).__name__}"}, 500)

    def _narration(self, data):
        """Set claude's reasoning-visibility level (off|key|full)."""
        level = str(data.get("level", "")).strip().lower()
        if level not in ("off", "key", "full"):
            return self._json({"ok": False, "error": "level must be off|key|full"}, 400)
        control.set_narration_level(level, by="user")
        return self._json({"ok": True, "level": level})

    def _send_bus(self, ns):
        """Get or construct a Bus("user", namespace=ns). Cached per ns; never per-request."""
        if ns not in _BUS_CACHE:
            _BUS_CACHE[ns] = Bus("user", namespace=ns)
        return _BUS_CACHE[ns]

    def _send(self, data):
        """Deliver an operator message at an EXPLICIT fidelity (chosen in the UI, not guessed from
        keywords -- that keyword-guessing false-tripped 'halt' on ordinary prose). Fidelities:
          chat/inform : plain delivery; the agent adopts it at its next turn. Never pauses.
          steer       : queue a fact the target folds into its CURRENT task (soft). Targeted only.
          interrupt   : hard barge-in -- set the target's nudge flag + kind=nudge. Targeted only.
        Global HALT is a separate, explicit control (the Pause button / /pause).

        AUTO-LAUNCH (elegance): if the target agent is offline (not on the bus), the launcher
        auto-spawns it before delivering the message. The user never clicks 'Launch' — they just
        talk, and the system ensures the recipient exists. Steer messages also get a brief
        ack echoed to the sender so the user KNOWS it was received, even though steer is silent."""
        text = (data.get("text") or "").strip()
        to = (data.get("to") or "all").strip().lower()       # default: reach every agent
        fidelity = (data.get("fidelity") or "chat").strip().lower()
        ns = (data.get("ns") or "").strip() or "bifrost"
        if not room_feed.valid_namespace(ns):
            return self._json({"ok": False, "error": f"invalid namespace: {ns!r}"}, 400)
        if not text:
            return self._json({"ok": False, "error": "empty"}, 400)
        bus = self._send_bus(ns)
        broadcast = to in ("all", "both", "*", "")
        meta = {"hops": 0, "via": "console", "intent": fidelity}
        from core.comm import nudge

        # Auto-launch: if target is a known agent and not online, spawn it now.
        launched = []
        if not broadcast and to != "user":
            try:
                online_agents = [a.get("agent") for a in bus.presence()]
            except Exception:
                online_agents = []
            if to not in online_agents:
                try:
                    lresult = get_launcher().launch(to)
                    if lresult.get("ok"):
                        launched.append(to)
                except Exception:
                    pass

        if fidelity in ("interrupt", "steer") and not broadcast:
            if fidelity == "interrupt":
                nudge.nudge(to, by="user", reason=text[:80])
                mid = bus.send(to, "nudge", text, meta=meta)
            else:
                nudge.steer_push(to, "user", text)
                mid = bus.send(to, "steer", text, meta={**meta, "display_only": True})
            result = {"ok": bool(mid), "id": mid, "intent": fidelity, "to": to, "paused": False}
            if launched:
                result["launched"] = launched
                result["msg"] = f"auto-launched {to} — steer queued, it'll fold this in when it starts"
            else:
                result["msg"] = f"steered {to} — folded into its current task"
            return self._json(result)

        kind = "inform" if fidelity == "inform" else "chat"
        mid = bus.broadcast(kind, text, meta=meta) if broadcast else bus.send(to, kind, text, meta=meta)
        result = {"ok": bool(mid), "id": mid, "intent": fidelity, "to": to, "paused": False}
        if launched:
            result["launched"] = launched
        return self._json(result)

    def _negotiate(self, data):
        """Open a negotiation round after user input. Agents have 8s to declare their plan
        (what + scope + estimate). Returns the verdict: green/amber/red + conflict details."""
        context = (data.get("text") or "").strip()
        if not context:
            return self._json({"ok": False, "error": "empty context"}, 400)
        try:
            from bifrost.api import round_result
            result = round_result(triggered_by="user", context=context)
            return self._json({"ok": True, "verdict": result.get("verdict"),
                               "reason": result.get("reason"),
                               "proposals": result.get("proposals", []),
                               "conflicts": result.get("conflicts", []),
                               "round": result.get("round_id", "")})
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)

    def _upload(self, data):
        name = os.path.basename((data.get("name") or "").strip()) or "dropped.bin"
        b64 = data.get("content_b64") or ""
        try:
            blob = base64.b64decode(b64.split(",", 1)[-1])
        except Exception:
            return self._json({"ok": False, "error": "bad base64"}, 400)
        os.makedirs(DROPBOX, exist_ok=True)
        dest = os.path.join(DROPBOX, name)
        try:
            with open(dest, "wb") as fh:
                fh.write(blob)
        except Exception as e:
            return self._json({"ok": False, "error": str(e)}, 500)
        rel = "dropbox/" + name
        BUS.send("deepseek", "chat",
                 f"[shared file] The user dropped a file into the project at `{rel}` "
                 f"({len(blob)} bytes). Read it with read_file if it's relevant.",
                 meta={"hops": 0, "via": "console", "file": rel})
        promoter.promote_drop(rel, len(blob), by="user")     # durable provenance: what the human shared
        return self._json({"ok": True, "path": rel, "bytes": len(blob)})


def _reexec():
    """Replace this process with a fresh one (same args/port) so edited source is served. SSE clients
    auto-reconnect; the browser just needs a refresh (the Reload button does it)."""
    try:
        sys.stdout.flush(); sys.stderr.flush()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _reload_watcher():
    """Self-reload: when this UI's own source changes on disk (an agent edited the console), re-exec so
    the new code is served -- no human in the restart loop. Debounced so we never reload mid-write."""
    try:
        last = os.path.getmtime(__file__)
    except Exception:
        return
    while True:
        time.sleep(2)
        try:
            m = os.path.getmtime(__file__)
        except Exception:
            continue
        if m != last:
            time.sleep(1.0)                 # debounce: let the writer finish flushing
            print("[bifrost-ui] source changed on disk -> reloading")
            _reexec()


def main():
    ap = argparse.ArgumentParser(description="Realtime Bifrost web console.")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--auto-reload", action="store_true",
                    help="re-exec the server when its source changes on disk (dev only; OFF by default so a "
                         "write-enabled agent editing the UI can't silently restart it under you). Use the "
                         "header ↻ Reload button for an explicit, safe reload instead.")
    args = ap.parse_args()
    if not BUS.online:
        print("bifrost_ui: WARNING -- bus offline (Redis unreachable). UI will serve but show no messages.")
    os.makedirs(DROPBOX, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.daemon_threads = True
    if args.auto_reload:                                             # opt-in: surprise-restart safe by default
        threading.Thread(target=_reload_watcher, daemon=True).start()
    url = f"http://{args.host}:{args.port}"
    print(f"[bifrost-ui] live at {url}   ({'auto-reload ON' if args.auto_reload else 'manual reload button'} - Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    print("[bifrost-ui] stopped.")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bifrost — Live Agent Console</title>
<style>
  :root{
    --bg:#0a0b0f; --bg2:#0e1015; --panel:#14161d; --panel2:#171a22; --border:#242833;
    --text:#e7e9f0; --muted:#8b90a2; --faint:#727890;
    --claude:#e0915c; --deepseek:#7aa2f7; --user:#5fd39b; --system:#7c8296;
    --accent:#7aa2f7; --accent2:#9d7cf7; --amber:#f0b246; --danger:#f0666e;
    --fleet:#f472b6;
    --shadow:0 8px 30px rgba(0,0,0,.35);
    /* aurora glow tints (per-theme tunable) + glass */
    --glow1:rgba(240,145,92,.05); --glow2:rgba(122,162,247,.06); --glow3:rgba(72,230,191,.04); --glow4:rgba(157,124,247,.05);
    --glass:rgba(18,20,28,.55); --glass-line:rgba(255,255,255,.08); --glass-hi:rgba(255,255,255,.06);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; position:relative;
    background:
      radial-gradient(1100px 700px at 8% -8%, var(--glow1), transparent 60%),
      radial-gradient(1000px 720px at 92% 6%, var(--glow2), transparent 60%),
      radial-gradient(1200px 800px at 60% 108%, var(--glow3), transparent 62%),
      radial-gradient(900px 900px at 28% 92%, var(--glow4), transparent 60%),
      var(--bg);
    color:var(--text); font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  /* Aurora Glass canvas — the animated light bed behind everything.
     Replaces the body::before blur pseudo-element when WebGL2 is available;
     falls back to the CSS gradient when not. z-index:-2 so the body::after
     noise texture (z-index:-1) sits ON TOP of the aurora for grain. */
  /* WIDTH/HEIGHT ARE LOAD-BEARING, not decoration. A <canvas> is a REPLACED element, so
     `inset:0` does NOT stretch it the way it stretches a div -- it keeps its intrinsic default of
     300x150 and pins to the top-left. That is exactly the clipped band in the corner Daniil kept
     pointing at. Measured before the fix: computed size 300x150 in a 1280x720 viewport, and
     aurora-shader.js:203 sizes its backing store from canvas.clientWidth, so the shader has been
     faithfully rendering a 300px world this whole time. The shader was never wrong; the CSS
     starved it. Percentages resolve against the containing block (the viewport for a fixed
     element), which avoids the scrollbar overflow 100vw would introduce. */
  #aurora-canvas{position:fixed; inset:0; width:100%; height:100%; z-index:-2; pointer-events:none}
  /* Viz canvas — slide-deck cards between aurora and cockpit. Hidden by default;
     shown when the viz engine is active (toggle via 'v' key or header button). */
  #viz-canvas{position:fixed; inset:0; z-index:-1; pointer-events:none; display:none}
  #viz-canvas.show{display:block}
  /* Viz control bar — overlays the top-right of the cockpit when viz is active */
  #viz-ctl{display:none; position:fixed; top:70px; right:20px; z-index:10; gap:6px}
  #viz-ctl.show{display:flex}
  #viz-ctl button{font:inherit; font-size:11px; font-weight:600; padding:5px 10px;
    border-radius:7px; cursor:pointer; border:1px solid var(--border);
    background:rgba(20,22,29,.85); color:var(--text); backdrop-filter:blur(8px);
    -webkit-backdrop-filter:blur(8px); transition:.15s}
  #viz-ctl button:hover{border-color:#39405a; background:rgba(23,26,34,.9)}
  #viz-ctl button.on{color:var(--accent); border-color:rgba(122,162,247,.35)}
  /* STATIC atmosphere: an animated blur(70px) repainted the whole viewport every frame -> typing/scroll jank.
     This is the CSS fallback; hidden when the WebGL canvas is active. */
  body::before{content:""; position:fixed; inset:-25%; z-index:-1; pointer-events:none; opacity:.6;
    background:conic-gradient(from 200deg at 42% 40%, var(--glow2),var(--glow3),var(--glow1),var(--glow4),var(--glow2));
    filter:blur(60px)}
  body::after{content:""; position:fixed; inset:0; z-index:-1; pointer-events:none; opacity:.3;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/></svg>")}
  /* ADAPTIVE SHELL (design/CONTRACT.md §1 + the 2026 intrinsic-design toolbox).
     100dvh not 100vh: on mobile, 100vh is the LARGEST viewport (chrome retracted), so a
     100vh shell puts the composer under the address bar until you scroll. dvh tracks the
     live viewport, which is the whole point for a console whose composer must always be
     reachable. Fallback line first for engines without dvh.
     max-width is fluid rather than a hard 1180: min(1180px, 96vw) keeps the shell from
     touching the edge on a small screen and from stretching past a readable measure on an
     ultrawide. Nothing here is a breakpoint -- it degrades continuously. */
  .app{display:flex; flex-direction:column; height:100vh; height:100dvh;
       width:min(1180px, 96vw); max-width:100%; margin:0 auto; position:relative; z-index:1}
  @media (min-width:1500px){ .app{width:min(1400px, 92vw)} }   /* ultrawide: use some of it */
  /* header */
  /* THE HEADER IS A BAND, NOT A CANVAS -- enforced structurally rather than per-element.
     Daniil reported "the ai list at the top takes half the screen" and I diagnosed it THREE
     times wrong: .pills (capped it -- not the culprit), the roster popover (bounded it -- not
     the culprit), then #tiles.presence-rail (superseded it -- still not the culprit). Each fix
     was correct for the element it touched and none of them fixed his screen, because the tile
     layer is a REGISTRY of swappable variants persisted per browser, so the thing rendering into
     his header is a component I have never had mounted and therefore cannot name from here.
     Identification kept failing; a constraint cannot. Whatever renders into this row, it lives
     inside a bounded band from now on: children may scroll sideways, never grow the page
     downward. This is the same lesson as .pills nowrap, applied one level up where it holds for
     components that do not exist yet.
     flex:none on children so a wide child scrolls the row instead of being squeezed; the
     controls already carry their own flex:none and keep it. */
  header{
    display:flex; align-items:center; gap:14px; padding:14px 20px;
    border-bottom:1px solid var(--glass-line); background:var(--glass);
    backdrop-filter:blur(26px) saturate(1.35); -webkit-backdrop-filter:blur(26px) saturate(1.35);
    box-shadow:0 1px 0 var(--glass-hi) inset; position:sticky; top:0; z-index:5;
    flex-wrap:nowrap; max-height:clamp(60px, 9vh, 84px); overflow-x:auto; overflow-y:hidden;
    scrollbar-width:thin; scrollbar-color:var(--border) transparent;
  }
  header::-webkit-scrollbar{height:5px}
  header::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
  /* Any header child, present or future, is clipped to the band and may not stack vertically. */
  header > *{flex:none; max-height:100%; overflow:hidden}
  header > #tiles, header > .pills{overflow-x:auto; overflow-y:hidden}
  .brand{display:flex; align-items:center; gap:11px; font-weight:650; letter-spacing:.2px}
  .logo{width:26px;height:26px;border-radius:8px;
    background:conic-gradient(from 210deg,var(--accent),var(--accent2),#e0915c,var(--accent));
    box-shadow:0 0 18px rgba(122,162,247,.45)}
  .brand small{color:var(--muted); font-weight:450; margin-left:2px}
  .spacer{flex:1}
  /* BOUNDED (design/CONTRACT.md §1 layout). SEEN, not inferred: at 1280x860 and 900x820 the
     header controls -- Pause, Deck, Agents, gear, reload -- were pushed clean OFF the right edge
     and were unreachable, and at 900px the strip clipped mid-word ("kimi" sliced in half).
     Measured cause: the row overflowed by 399px (scrollWidth 1579 vs 1180) because .pills took
     998px of it with no min-width:0, so #epiChip was crushed from 162px of content into a 22px
     box and everything after it was pushed out of the viewport.
     A flex item's default min-width is auto, so a data strip that grows with the fleet will
     ALWAYS win the row unless told otherwise. It is the same unbounded-by-roster-count disease as
     the roster popover height and the animation budget: size as a function of fleet size, with no
     ceiling. The strip scrolls internally; the controls never yield. */
  .pills{display:flex; gap:7px; align-items:center; flex:1 1 0; min-width:0;
    overflow-x:auto; overflow-y:hidden; scrollbar-width:thin;
    scrollbar-color:var(--border) transparent; padding-bottom:2px;
    /* NOWRAP IS LOAD-BEARING, and only reproducible with the right tile variant. The pill
       children are rendered by a swappable REGISTRY['tile'] variant persisted per browser.
       Under the default variant they are 58px chips and everything is fine; under `glass-card`
       they are ~535px cards, and with wrapping allowed 11 of them stack into a ~950px column
       INSIDE THE HEADER ROW -- which is exactly the "ai list taking half the screen" Daniil kept
       reporting while my headless browser, holding the default variant, rendered a tidy strip and
       showed me nothing wrong. Same code, different persisted preference, opposite layout.
       nowrap + a height cap makes the strip behave identically under EVERY variant: it scrolls
       sideways, it never grows downward, and no future tile renderer can reopen this. */
    flex-wrap:nowrap; max-height:46px}
  .pills > *{flex:none; max-height:40px; overflow:hidden}
  .pills::-webkit-scrollbar{height:6px}
  .pills::-webkit-scrollbar-thumb{background:var(--border); border-radius:3px}
  .pills::-webkit-scrollbar-track{background:transparent}
  .pill{flex:none}                      /* pills keep their size; the STRIP scrolls, not the pill */
  /* The hero avatar fills the agent-selector frame. If WebGL never comes up the canvas is
     simply never created and the frame keeps its ⏣ glyph -- the avatar is an enhancement,
     never load-bearing. */
  /* THE AVATAR AT FULL SIZE. Daniil: "make the avatar be 2 inch by 2 inch... I want to have
     our eyecatching piece be big enough to appreciate." 2in = 192px at the CSS reference 96dpi.
     Cost is unchanged in kind and still trivial: the backing store renders at half scale, so
     192 CSS px is a 96px render target -- about 9k fragments against a full-screen 700k. */
  #ash-frame.has-av{width:192px; height:192px; border-radius:26px; font-size:0; color:transparent}
  /* THE FLEET'S VOICE. A full-bleed strip between the fidelity ladder and the input row, kept in
     NORMAL FLOW rather than absolutely positioned: .cwrap is not position:relative, and making it
     so to host an overlay would re-home every absolutely-positioned descendant it already has --
     #pcloud among them. 22px is enough for the waveform's travel without the composer growing in
     any way you would notice. */
  .voiceline{display:block; width:100%; height:22px; margin:1px 0 3px; cursor:help}
  /* THE DEGRADED PATH, and it has to look deliberate. If WebGL2 is missing or the shader will
     not compile the box stays two inches -- so the glyph must grow into it rather than sit as a
     14px mark adrift in a large empty square, which reads as breakage rather than as a fallback.
     Hover `data-av-off` on the element to see which of the three bails was taken. */
  #ash-frame.av-fallback{width:192px; height:192px; border-radius:26px; font-size:58px;
          display:flex; align-items:center; justify-content:center; line-height:1;
          color:rgba(122,162,247,.5);
          background:radial-gradient(circle at 50% 45%, rgba(122,162,247,.16), transparent 68%)}
  .heroav{position:absolute; inset:0; width:100%; height:100%; display:block;
          border-radius:25px; pointer-events:none}
  #ash-frame.has-av:hover{border-color:rgba(122,162,247,.65);
          box-shadow:0 1px 0 rgba(255,255,255,.16) inset, 0 0 40px -6px rgba(122,162,247,.55)}
  /* presence-cloud keeps its seat but becomes a CORNER BADGE -- at this size the geodesic is
     the subject and the initial is a footnote, not a competing glyph in the middle. */
  #ash-frame.has-av #pcloud{position:absolute; right:7px; bottom:6px; left:auto; top:auto;
          z-index:3; font-size:11px; opacity:.9}
  /* The composer grows to match. He offered: "We can make the textbox bigger." */
  #ash-frame.has-av ~ #ash-label, #ash.big #ash-label{font-size:12px}
  .cwrap.tall textarea{min-height:150px}
  /* Controls are never sacrificed to make room for data. */
  #epiChip,#reloadBtn,#gearBtn,#lnchrBtn,#vizBtn,#pauseBtn{flex:none}
  .pill{display:flex; align-items:center; gap:6px; padding:5px 10px; border:1px solid var(--border);
    border-radius:999px; background:var(--panel); font-size:12.5px; color:var(--muted); cursor:pointer}
  .dot{width:7px;height:7px;border-radius:50%;background:var(--faint); box-shadow:0 0 0 0 rgba(0,0,0,0)}
  .pill.on .dot{background:var(--user); box-shadow:0 0 8px var(--user)}
  .pill.on{color:var(--text)}
  .pill.off{opacity:.55}
  /* Fleet Pulse — single at-a-glance system-health ring in the header */
  .fpulse{width:12px;height:12px;border-radius:50%;flex:none;cursor:default;position:relative;
    transition:background .4s,box-shadow .4s}
  .fpulse::after{content:"";position:absolute;inset:-4px;border-radius:50%;border:2px solid transparent;
    transition:border-color .4s}
  .fpulse.green{background:#5fd39b; box-shadow:0 0 10px rgba(95,211,155,.5)}
  .fpulse.green::after{border-color:rgba(95,211,155,.35)}
  .fpulse.amber{background:var(--amber); box-shadow:0 0 10px rgba(240,178,70,.5)}
  .fpulse.amber::after{border-color:rgba(240,178,70,.35)}
  .fpulse.red{background:var(--danger); box-shadow:0 0 10px rgba(240,102,110,.5); animation:fpulseRed 1.2s ease-in-out infinite}
  .fpulse.red::after{border-color:rgba(240,102,110,.35); animation:fpulseRing 1.2s ease-in-out infinite}
  @keyframes fpulseRed{0%,100%{box-shadow:0 0 6px rgba(240,102,110,.4)}50%{box-shadow:0 0 18px rgba(240,102,110,.7)}}
  @keyframes fpulseRing{0%,100%{border-color:rgba(240,102,110,.25)}50%{border-color:rgba(240,102,110,.55);inset:-6px}}
  @media (prefers-reduced-motion:reduce){.fpulse.red,.fpulse.red::after{animation:none}}
  button.ctl{
    font:inherit; font-size:13px; font-weight:600; color:var(--text); cursor:pointer;
    border:1px solid var(--border); background:var(--panel); padding:8px 14px; border-radius:10px;
    transition:.15s; display:flex; align-items:center; gap:7px;
  }
  button.ctl:hover{border-color:#39405a; background:var(--panel2)}
  button.ctl.pause{border-color:rgba(240,178,70,.4)}
  button.ctl.pause:hover{background:rgba(240,178,70,.12)}
  button.ctl.paused{background:linear-gradient(135deg,var(--accent),var(--accent2)); border-color:transparent}
  /* paused banner */
  .banner{display:none; align-items:center; gap:10px; margin:10px 16px 0; padding:9px 14px;
    border:1px solid rgba(240,178,70,.35); background:rgba(240,178,70,.10); color:var(--amber);
    border-radius:10px; font-size:13px}
  .banner.show{display:flex; animation:drop .25s ease}
  @keyframes drop{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
  /* messages */
  #log{flex:1; overflow-y:auto; padding:20px 24px 8px; scroll-behavior:smooth}
  #log::-webkit-scrollbar{width:10px} #log::-webkit-scrollbar-thumb{background:#20232e;border-radius:6px;border:2px solid var(--bg)}
  /* MOTION BUDGET (design/CONTRACT.md §1). Measured 2026-08-01 on the live console: 261 elements
     carrying a CSS animation, and 250 of them were this one -- `fade` on every .msg in the feed.
     The entry animation is right; applying it to 250 historical rows forever is not. The feed is
     ring-buffered at ~250 nodes, so this count is a FLOOR, not a peak.
     content-visibility:auto lets the engine skip layout+paint for rows outside the viewport
     entirely -- the single largest win available here, because the feed is almost all off-screen.
     contain-intrinsic-size keeps the scrollbar honest while rows are skipped. */
  .msg{display:flex; gap:12px; margin-bottom:18px; animation:fade .28s ease;
       content-visibility:auto; contain-intrinsic-size:auto 64px}
  @keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  /* CONTRACT §1 motion budget, global floor: ambient motion is a nicety and must never be the
     reason a frame is missed. Honors the OS setting rather than inventing a project dial. */
  @media (prefers-reduced-motion:reduce){
    *,*::before,*::after{animation-duration:.001ms !important; animation-iteration-count:1 !important;
      transition-duration:.001ms !important; scroll-behavior:auto !important}
  }
  .av{flex:none; width:34px;height:34px;border-radius:10px; display:grid;place-items:center;
    font-weight:700; font-size:13px; color:#0a0b0f}
  .av.claude{background:linear-gradient(135deg,#e0915c,#d97b5a)}
  .av.deepseek{background:linear-gradient(135deg,#7aa2f7,#9d7cf7)}
  .av.user{background:linear-gradient(135deg,#5fd39b,#3fbf86)}
  .bubble{max-width:78%; background:var(--panel); border:1px solid var(--border); border-radius:5px 15px 15px 15px;
    padding:10px 14px; box-shadow:var(--shadow)}
  .row{display:flex; align-items:baseline; gap:8px; margin-bottom:3px}
  .who{font-weight:650; font-size:13px}
  .who.claude{color:var(--claude)} .who.deepseek{color:var(--deepseek)} .who.user{color:var(--user)}
  .time{color:var(--faint); font-size:11px}
  /* T121 S-cut epistemic glyph (kimi G4/G11): structural truth signal. Shape AND
     color dual-encode (color-blind safe). Deliberately outside any focus/density
     dial path -- a dial must not be able to dim a truth glyph. */
  .epi{font-size:12px; line-height:1; flex:none; font-style:normal}
  .epi-fresh{color:var(--ok,#5fd39b)}
  .epi-aging{color:var(--amber)}
  .epi-stale{color:var(--danger)}
  .epi-unknown{color:var(--faint); border:1px dashed var(--border); border-radius:50%;
    width:13px; height:13px; display:inline-flex; align-items:center; justify-content:center;
    font-size:9px}
  .epi-mark{font-size:9.5px; font-weight:700; letter-spacing:.3px; padding:0 4px;
    border:1px dashed var(--border); border-radius:4px; opacity:.85}
  .hop{color:var(--faint); font-size:10.5px; border:1px solid var(--border); border-radius:5px; padding:0 5px}
  .ib{font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.4px; padding:1px 6px; border-radius:5px; border:1px solid var(--border)}
  .ib-halt{color:var(--amber); border-color:rgba(240,178,70,.45); background:rgba(240,178,70,.12)}
  .ib-steer{color:var(--deepseek); border-color:rgba(122,162,247,.4); background:rgba(122,162,247,.1)}
  .ib-interrupt{color:var(--danger); border-color:rgba(240,102,110,.5); background:rgba(240,102,110,.12)}
  .ib-inform{color:var(--user); border-color:rgba(95,211,155,.4); background:rgba(95,211,155,.1)}
  .ib-ask{color:var(--muted)}
  /* steer-pending / nudged markers on roster pills */
  .pill .sig{font-size:10px; font-weight:700; padding:0 5px; border-radius:6px; margin-left:3px}
  .pill .sig.steer{color:var(--deepseek); background:rgba(122,162,247,.16)}
  .pill .sig.nudge{color:var(--danger); background:rgba(240,102,110,.16)}
  .fidsel{align-self:center; background:var(--bg2); border:1px solid var(--border); color:var(--muted);
    border-radius:9px; padding:7px 8px; font:inherit; font-size:12.5px; outline:none; cursor:pointer}
  .fidsel:hover{border-color:#39405a}
  .fidsel.interrupt{color:var(--danger); border-color:rgba(240,102,110,.4)}
  .fidsel.steer{color:var(--deepseek); border-color:rgba(122,162,247,.4)}
  .content{white-space:pre-wrap; word-wrap:break-word; font-size:14.5px; color:#dce0ea; line-height:1.55}
  .content code{background:#0c0e14; border:1px solid var(--border); border-radius:5px; padding:1px 5px;
    font:12.5px/1.5 "SF Mono",SFMono-Regular,Consolas,monospace}
  .content pre{background:#0b0d13; border:1px solid var(--border); border-radius:9px; padding:11px 13px;
    overflow-x:auto; margin:8px 0} .content pre code{background:none;border:none;padding:0}
  /* user msgs: right aligned */
  .msg.me{flex-direction:row-reverse}
  .msg.me .bubble{background:linear-gradient(135deg,rgba(95,211,155,.14),rgba(95,211,155,.06));
    border-color:rgba(95,211,155,.3); border-radius:14px 4px 14px 14px}
  .msg.me .row{flex-direction:row-reverse}
  /* system / notes */
  .sys{display:flex; justify-content:center; margin:12px 0; animation:fade .28s ease}
  .sys span{font-size:12px; color:var(--muted); background:var(--panel); border:1px solid var(--border);
    border-radius:999px; padding:5px 13px}
  .sys.guard span{color:var(--amber); border-color:rgba(240,178,70,.3); background:rgba(240,178,70,.08)}
  /* live trace: DeepSeek's tool calls + thinking, streamed as compact dim lines */
  .traceline{display:flex; gap:8px; align-items:baseline; margin:1px 0 1px 46px; font-size:12px;
    font-family:"SF Mono",SFMono-Regular,Consolas,monospace; animation:fade .18s ease}
  .traceline .trav{font-weight:600; opacity:.85; flex:none; min-width:56px}
  .traceline .trav.deepseek{color:var(--deepseek)} .traceline .trav.claude{color:var(--claude)}
  .traceline .trav.system{color:var(--system)}
  .traceline .trat{color:var(--faint); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  /* T002: collapsible trace card — consecutive same-agent traces fold into ONE card */
  .trace-card{margin:4px 0 4px 46px; border:1px solid var(--border); border-radius:8px;
    background:var(--panel); overflow:hidden; animation:fade .2s ease}
  .trace-card-header{display:flex; align-items:center; gap:8px; padding:6px 10px;
    cursor:pointer; user-select:none; font-size:12px; color:var(--muted)}
  .trace-card-header:hover{background:rgba(255,255,255,.03)}
  .trace-card-header .trav{font-weight:600; opacity:.85; font-family:"SF Mono",SFMono-Regular,Consolas,monospace}
  .trace-card-header .trav.deepseek{color:var(--deepseek)} .trace-card-header .trav.claude{color:var(--claude)}
  .trace-card-header .trav.system{color:var(--system)}
  .trace-card-header .tc-arrow{font-size:10px; transition:transform .18s ease; flex:none}
  .trace-card.open .tc-arrow{transform:rotate(90deg)}
  .trace-card-header .tc-counts{font-size:11px; opacity:.7}
  .trace-card-body{display:none; padding:2px 0; border-top:1px solid var(--border)}
  .trace-card.open .trace-card-body{display:block}
  /* W99: traces-expanded mode — all cards open at creation; click still toggles */
  .traces-expanded .trace-card .trace-card-body{display:block}
  .traces-expanded .trace-card-header .tc-arrow{transform:rotate(90deg)}
  .trace-card-body .traceline{margin:0 0 0 8px; animation:none}
  /* typing */
  .activity{display:flex; flex-direction:column; gap:8px; padding:2px 16px 8px}
  .activity:empty{display:none}
  .actrow{display:flex; gap:12px; align-items:center; animation:fade .25s ease}
  .actbubble{display:flex; align-items:center; gap:7px; background:var(--panel); border:1px solid var(--border);
    border-radius:12px; padding:8px 13px; font-size:13.5px; color:var(--muted)}
  .actbubble b{color:var(--deepseek); font-weight:650}
  .acticon{font-size:16px; filter:drop-shadow(0 0 7px rgba(122,162,247,.55))}
  .actdetail{color:var(--faint); font-family:"SF Mono",Consolas,monospace; font-size:12px;
    max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .tdot{width:6px;height:6px;border-radius:50%;background:var(--deepseek);display:inline-block;margin:0 1px;
    animation:blink 1.2s infinite both}
  .tdot:nth-child(2){animation-delay:.2s} .tdot:nth-child(3){animation-delay:.4s}
  @keyframes blink{0%,80%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-3px)}}
  /* === HUD glanceability strip (who's-doing-what, always visible) === */
  #hud{display:none; flex-direction:column; margin:0 16px; padding:6px 0; max-height:148px; overflow-y:auto;
    border-bottom:1px solid var(--glass-line);
    background:linear-gradient(to bottom,var(--glass),transparent 60%);
    backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
    transition:max-height .3s ease}
  #hud.show{display:flex}
  #hud.collapsed{max-height:38px}
  .hrow{display:flex; align-items:center; gap:9px; padding:5px 11px; min-height:30px; font-size:12.5px;
    animation:hudIn .26s cubic-bezier(.2,.9,.3,1.1); transition:background .18s,opacity .22s;
    border-radius:8px; cursor:pointer}
  .hrow:hover{background:var(--glass-hi)}
  .hrow.stale{opacity:.48}
  .hrow.expanded{background:var(--panel); border:1px solid var(--border); margin:1px 0}
  .hicon{flex:none; font-size:14px; width:20px; text-align:center}
  .hagent{font-weight:650; min-width:62px; white-space:nowrap}
  .hagent.claude{color:var(--claude)} .hagent.deepseek{color:var(--deepseek)}
  .hverb{color:var(--muted); min-width:52px; white-space:nowrap}
  .hdetail{flex:1; color:var(--faint); font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:11.5px;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0}
  .hrow:hover .hdetail{overflow:visible; white-space:normal; word-break:break-all}
  .helapsed{flex:none; color:var(--faint); font-size:11px; min-width:36px; text-align:right}
  /* new-activity glow pulse on the icon */
  .hrow.just-started .hicon{animation:hudPulse .55s ease-out}
  /* scan-line: a 1px sweep down the strip, the sci-fi HUD signature */
  #hud::after{content:""; position:absolute; left:0;right:0; height:1px; pointer-events:none;
    background:var(--hud-scanline, rgba(255,255,255,.025));
    animation:hudScan 3.8s linear infinite}
  @keyframes hudIn{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
  @keyframes hudPulse{0%{filter:drop-shadow(0 0 3px var(--aurora-neon, #48e6bf))}100%{filter:drop-shadow(0 0 0px transparent)}}
  @keyframes hudScan{from{top:0}to{top:100%}}
  #hud-toggle{align-self:flex-end; font-size:11px; color:var(--faint); cursor:pointer; padding:0 6px 2px;
    user-select:none; display:none}
  #hud-toggle.show{display:block}
  /* === slide deck cards (mini teaching slides when a HUD row is clicked) === */
  #deck{display:none; margin:0 16px 8px; position:relative; overflow:hidden}
  #deck.show{display:block}
  .deck-cards{display:flex; gap:0; width:100%; transition:transform .35s cubic-bezier(.2,.9,.3,1.05); will-change:transform}
  .slide-card{flex:none; width:100%; background:var(--panel); border:1px solid var(--border); border-radius:14px;
    padding:16px 18px; box-shadow:var(--shadow); position:relative;
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
  .slide-card .sc-head{display:flex; align-items:center; gap:10px; margin-bottom:8px}
  .slide-card .sc-icon{font-size:20px; width:28px; text-align:center}
  .slide-card .sc-title{font-weight:700; font-size:14px; color:var(--text)}
  .slide-card .sc-body{font-size:13px; color:var(--muted); line-height:1.5}
  .slide-card .sc-body code{font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:12px;
    background:var(--bg2); border:1px solid var(--border); border-radius:5px; padding:1px 6px; color:var(--text)}
  .slide-card .sc-result{font-size:13px; margin-top:8px; padding:8px 0 0; border-top:1px solid var(--border)}
  .slide-card .sc-result.good{color:var(--user)} .slide-card .sc-result.warn{color:var(--amber)} .slide-card .sc-result.bad{color:var(--danger)}
  .slide-dots{display:flex; justify-content:center; gap:8px; margin-top:10px}
  .slide-dot{width:7px; height:7px; border-radius:50%; background:var(--border); transition:all .3s}
  .slide-dot.active{background:var(--aurora-neon, #48e6bf); box-shadow:0 0 6px var(--aurora-neon, #48e6bf);
    transform:scale(1.3)}
  .deck-controls{display:flex; justify-content:center; align-items:center; gap:10px; margin-top:6px}
  .deck-ctrl{font-size:12px; color:var(--faint); cursor:pointer; user-select:none; padding:4px 10px;
    border-radius:8px; border:1px solid var(--border); background:var(--panel); transition:.15s}
  .deck-ctrl:hover{color:var(--text); border-color:var(--aurora-neon)}
  .deck-ctrl.paused{color:var(--amber); border-color:var(--amber)}
  /* card entry animation */
  @keyframes slideCardIn{from{opacity:0;transform:translateX(18px)}to{opacity:1;transform:none}}
  .slide-card{animation:slideCardIn .35s cubic-bezier(.2,.9,.3,1.05) both}
  .slide-card:nth-child(2){animation-delay:.05s}
  .slide-card:nth-child(3){animation-delay:.1s}
  /* composer */
  .composer{padding:12px 16px 18px; border-top:1px solid var(--glass-line); background:rgba(14,16,22,.9); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); position:relative}
  /* GLASS COMPOSER (Daniil: "sucker for glass blur effect and subtle edges with either glow or
     shadow"). Four layers, and each does a different job -- this is what separates real glass
     from a translucent rectangle:
       1 TRANSLUCENT FILL + BACKDROP BLUR -- the aurora behind is visible but abstracted, so the
         box sits IN the scene rather than on top of it.
       2 A BRIGHT TOP EDGE (inset 1px highlight). Physical glass catches light on its upper lip;
         this single inset line is what reads as "thickness" and is the most-skipped detail.
       3 A DROP SHADOW that is mostly BELOW and heavily feathered -- it lifts the box off the
         background without drawing a hard outline.
       4 A FOCUS GLOW rather than a focus border: colour blooms outward on focus-within instead
         of a ring snapping on, which is the modern reading of "subtle edges with glow". */
  .cwrap{display:flex; gap:10px; align-items:flex-end;
    background:linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
    backdrop-filter:blur(22px) saturate(1.5); -webkit-backdrop-filter:blur(22px) saturate(1.5);
    border:1px solid rgba(255,255,255,.10);
    border-radius:16px; padding:8px 8px 8px 14px;
    box-shadow:0 1px 0 rgba(255,255,255,.13) inset,        /* the top lip -- reads as thickness */
               0 18px 40px -22px rgba(0,0,0,.95),          /* feathered lift, mostly below */
               0 2px 10px -6px rgba(0,0,0,.6);
    transition:box-shadow .22s ease, border-color .22s ease}
  .cwrap:hover{border-color:rgba(255,255,255,.15)}
  .cwrap:focus-within{
    border-color:rgba(122,162,247,.42);
    box-shadow:0 1px 0 rgba(255,255,255,.16) inset,
               0 0 0 3px rgba(122,162,247,.10),            /* tight halo */
               0 0 34px -6px rgba(122,162,247,.32),        /* the bloom, outside the halo */
               0 18px 44px -22px rgba(0,0,0,.95)}
  textarea{flex:1; background:none; border:none; outline:none; resize:none; color:var(--text);
    font:inherit; font-size:15px; max-height:160px; padding:6px 0}
  textarea::placeholder{color:var(--faint)}
  .target{align-self:center; background:var(--bg2); border:1px solid var(--border); color:var(--muted);
    border-radius:9px; padding:7px 8px; font:inherit; font-size:12.5px; outline:none; cursor:pointer}
  .target:hover{border-color:#39405a}
  .send{flex:none; width:38px;height:38px;border-radius:10px; border:none; cursor:pointer;
    background:linear-gradient(135deg,var(--accent),var(--accent2)); color:#fff; font-size:17px;
    display:grid;place-items:center; transition:.15s} .send:hover{filter:brightness(1.1)} .send:disabled{opacity:.4;cursor:default}
  .hint{color:var(--faint); font-size:11.5px; margin:7px 4px 0; display:flex; gap:5px; align-items:center}
  /* --- recipient chip inside composer --- */
  .recipient{display:flex; align-items:center; gap:6px; cursor:pointer; padding:4px 8px 4px 2px;
    border-radius:10px; border:1px solid var(--border); background:var(--bg2); transition:.15s; min-width:0}
  .recipient:hover{border-color:#39405a; background:var(--panel2)}
  .rstack{display:flex; gap:2px; flex:none}
  .rlabel{display:flex; align-items:center; gap:4px; font-size:12px; color:var(--muted);
    overflow:hidden; white-space:nowrap; text-overflow:ellipsis}
  .rlabel b{color:var(--text)}
  .rlabel .cue{color:var(--faint); font-size:11px}
  .cav{width:22px;height:22px;border-radius:6px;display:grid;place-items:center;
    font-weight:700; font-size:10px; color:#0a0b0f; flex:none}
  /* --- roster popover (agent selector dropdown) --- */
  /* Height-BOUNDED (Daniil 2026-08-01: "lets make the ai list at the top not take half the screen").
     It had max-height:none + overflow:visible -- verified live on the running console -- so the list
     grew linearly with the roster. At 11 agents x ~40px it was ~440px of a 1317px viewport, and it
     opens UPWARD (bottom:100%), so it swallowed the feed. Bound it and let it scroll: the roster is
     a picker, not a page. Rows also tightened 8px->6px vertical, which is ~11% off the open height
     before scrolling starts. */
  .roster-pop{display:none; position:absolute; bottom:calc(100% + 4px); left:16px; z-index:15;
    background:var(--panel2); border:1px solid var(--border); border-radius:12px; padding:6px;
    box-shadow:var(--shadow); min-width:180px; animation:drop .18s ease;
    max-height:min(34vh,280px); overflow-y:auto; overscroll-behavior:contain;
    scrollbar-width:thin; scrollbar-color:var(--border) transparent}
  .roster-pop::-webkit-scrollbar{width:8px}
  .roster-pop::-webkit-scrollbar-thumb{background:var(--border); border-radius:4px}
  .roster-pop::-webkit-scrollbar-track{background:transparent}
  .roster-pop.show{display:block}
  .roster-pop .ri{display:flex; align-items:center; gap:10px; padding:6px 10px; border-radius:9px;
    cursor:pointer; transition:.12s; font-size:13px; color:var(--text); margin-bottom:2px}
  .roster-pop .ri:last-child{margin-bottom:0}
  .roster-pop .ri:hover{background:var(--glass-hi)}
  .roster-pop .ri.sel{background:rgba(122,162,247,.12)}
  .roster-pop .ri .cav{width:24px;height:24px;border-radius:7px; flex:none}
  .roster-pop .ri .chk{flex:1; text-align:right; font-size:12px; color:var(--accent); opacity:0}
  .roster-pop .ri.sel .chk{opacity:1}
  /* --- fidelity icons + agent selector (icon buttons with labels underneath) --- */
  @keyframes rpulse{0%{box-shadow:0 0 0 0 rgba(122,162,247,.4)}100%{box-shadow:0 0 0 10px rgba(122,162,247,0)}}
  @property --spin{syntax:'<angle>'; inherits:false; initial-value:0deg}
  @keyframes ladderSweep{to{--spin:360deg}}
  .fibar{display:flex; gap:4px; align-items:center; justify-content:center; margin:0 0 8px}
  .fibtn{display:flex; flex-direction:column; align-items:center; gap:2px; cursor:pointer; padding:7px 12px 5px;
    border-radius:10px; border:1px solid var(--border); background:var(--bg2); color:var(--muted);
    font:inherit; font-size:11px; transition:.18s; min-width:58px; text-align:center}
  .fibtn .fi{font-size:18px; line-height:1; margin-bottom:1px}
  .fibtn .fl{font-size:9.5px; font-weight:600; text-transform:uppercase; letter-spacing:.3px; color:var(--faint)}
  .fibtn:hover{color:var(--text); border-color:#39405a; background:var(--panel2)}
  .fibtn.on{color:var(--text); background:var(--panel2); border-color:var(--accent); position:relative; z-index:1; box-shadow:0 0 14px -4px var(--accent)}
  .fibtn.on::after{content:""; position:absolute; inset:-1px; border-radius:inherit; padding:1px; pointer-events:none;
    background:conic-gradient(from var(--spin), var(--accent),var(--user),var(--claude),var(--accent2),var(--accent));
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0); -webkit-mask-composite:xor;
    mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0); mask-composite:exclude; animation:ladderSweep 4s linear infinite}
  @media (prefers-reduced-motion:reduce){.fibtn.on::after{animation:none}}
  .fibtn.chat .fi{color:var(--user)} .fibtn.steer .fi{color:var(--deepseek)} .fibtn.interrupt .fi{color:var(--danger)}
  .fibtn.inform .fi{color:var(--user)}
  /* agent selector row — icon buttons next to the ⏣ frame, inside composer */
  .aselrow{display:flex; gap:0; align-items:center; margin:0 0 10px; justify-content:center}
  .aselrow .asbtn{display:flex; flex-direction:column; align-items:center; gap:3px; cursor:pointer;
    padding:6px 10px 4px; border-radius:10px; border:1px solid transparent; background:transparent;
    font:inherit; font-size:11px; color:var(--muted); transition:.18s; min-width:50px; text-align:center}
  .aselrow .asbtn:hover{color:var(--text); background:var(--glass-hi); border-color:var(--border)}
  .aselrow .asbtn.on{color:var(--text); border-color:var(--accent); background:rgba(122,162,247,.08)}
  .aselrow .asbtn .ai{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;
    font-weight:700; font-size:12px; color:#0a0b0f; flex:none}
  .aselrow .asbtn .an{font-size:10px; font-weight:600; line-height:1; max-width:56px;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .aselrow .asbtn .adot{width:5px;height:5px;border-radius:50%;background:var(--faint); margin-top:1px}
  /* dropzone — softer overlay, smaller target */
  #drop{position:fixed; inset:0; z-index:20; display:none; place-items:center;
    background:rgba(8,9,13,.65); backdrop-filter:blur(2px); -webkit-backdrop-filter:blur(2px)}
  #drop.show{display:grid; animation:fade .12s ease}
  .dz{border:2px dashed var(--accent); border-radius:16px; padding:40px 56px; text-align:center;
    background:rgba(122,162,247,.04); transition:border-color .2s,background .2s,box-shadow .2s}
  .dz.over{border-color:var(--aurora-neon, #48e6bf); background:rgba(72,230,191,.06);
    box-shadow:0 0 32px rgba(72,230,191,.08)}
  .dz .big{font-size:18px; font-weight:650; margin-bottom:4px}
  .dz .sub{color:var(--muted); font-size:12.5px; line-height:1.5}
  .dz .preview{display:none; margin-top:16px; max-width:320px; max-height:180px; border-radius:10px;
    border:1px solid var(--border); object-fit:contain}
  .dz .preview.show{display:block; margin-left:auto; margin-right:auto}
  .dz .filenames{display:none; margin-top:10px; font-size:12px; color:var(--faint);
    font-family:"SF Mono",SFMono-Regular,Consolas,monospace}
  .dz .filenames.show{display:block}
  /* inline file card in the message log */
  .filecard{display:flex; align-items:center; gap:10px; margin:6px 0; padding:10px 14px;
    background:var(--panel); border:1px solid var(--border); border-radius:12px;
    transition:.15s; cursor:pointer; max-width:420px}
  .filecard:hover{background:var(--glass-hi); border-color:var(--accent)}
  .filecard .fc-icon{font-size:22px; flex:none}
  .filecard .fc-info{flex:1; min-width:0}
  .filecard .fc-name{font-weight:600; font-size:13px; color:var(--text);
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .filecard .fc-meta{font-size:11px; color:var(--faint); margin-top:1px}
  .filecard .fc-thumb{flex:none; width:48px; height:48px; border-radius:8px;
    object-fit:cover; border:1px solid var(--border)}
  .filecard .fc-thumb.hidden{display:none}
  /* image file card — larger, screenshot-friendly */
  .filecard-img{flex-direction:column; align-items:stretch; max-width:480px; padding:0; overflow:hidden}
  .filecard-img .fc-img{width:100%; max-height:360px; object-fit:contain; cursor:zoom-in;
    border-radius:11px 11px 0 0; background:var(--bg); transition:max-height .3s}
  .filecard-img .fc-img.expanded{max-height:none; border-radius:11px; cursor:zoom-out}
  .filecard-img .fc-cap{display:flex; align-items:center; gap:10px; padding:10px 14px}
  /* toast */
  #toast{position:fixed; bottom:92px; left:50%; transform:translateX(-50%); z-index:30; display:flex; flex-direction:column; gap:8px}
  .toast{background:var(--panel2); border:1px solid var(--border); color:var(--text); padding:9px 15px;
    border-radius:10px; font-size:13px; box-shadow:var(--shadow); animation:fade .2s ease}
  /* launcher panel */
  #lnchr{display:none; margin:0 16px 10px; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); animation:drop .25s ease}
  #lnchr.show{display:block}
  .lrow{display:flex; align-items:center; gap:10px; padding:8px 6px; border-bottom:1px solid rgba(255,255,255,.04)}
  .lrow:last-child{border-bottom:none}
  .ltag{font-weight:650; font-size:13px; color:var(--text); min-width:120px}
  .ldesc{flex:1; font-size:12.5px; color:var(--muted)}
  .lst{font-size:11.5px; font-weight:600; padding:2px 8px; border-radius:6px; white-space:nowrap}
  .lst.running{color:#5fd39b; background:rgba(95,211,155,.14)}
  .lst.exited{color:var(--muted); background:rgba(139,144,162,.1)}
  .lst.crashed,.lst.error{color:var(--danger); background:rgba(240,102,110,.12)}
  .lst.killed{color:var(--amber); background:rgba(240,178,70,.12)}
  .lst.token_exhausted{color:var(--amber); background:rgba(240,178,70,.14)}
  .lst.never_launched{color:var(--faint); background:rgba(90,95,112,.08)}
  .lact{display:flex; gap:6px}
  .lact button{font:inherit; font-size:11.5px; font-weight:600; padding:5px 11px; border-radius:7px;
    cursor:pointer; border:1px solid var(--border); background:var(--panel2); color:var(--text); transition:.15s}
  .lact button:hover{border-color:#39405a; background:#1c1f2a}
  .lact .lgo{background:linear-gradient(135deg,var(--accent),var(--accent2)); border-color:transparent; color:#fff}
  .lact .lgo:hover{filter:brightness(1.1)}
  .lact .lgo:disabled{opacity:.4; cursor:default; filter:none}
  .lact .lkill{border-color:rgba(240,102,110,.35); color:var(--danger)}
  .lact .lkill:hover{background:rgba(240,102,110,.12)}
  .lact .lkill:disabled{opacity:.3; cursor:default}
  .lact .lrevive{border-color:rgba(122,162,247,.4); color:var(--accent)}
  .lact .lrevive:hover{background:rgba(122,162,247,.12)}
  .lact .lrevive:disabled{opacity:.3; cursor:default}
  .lact .lauto{border-color:var(--border); color:var(--faint); font-size:10.5px}
  .lact .lauto:hover{background:#1c1f2a}
  .lact .lauto.on{border-color:rgba(158,206,106,.55); color:#9ece6a; background:rgba(158,206,106,.1)}
  .lv{font-size:11px; padding:2px 7px; border-radius:6px; margin-left:2px; white-space:nowrap}
  .lv.lv-idle{opacity:.5}
  .lv.lv-busy{background:rgba(122,162,247,.16); color:var(--accent)}
  .lv.lv-wedged{background:rgba(240,102,110,.22); color:var(--danger); font-weight:600}
  .lreason{font-size:11px; color:var(--faint); margin-left:6px}
  button.lctl{
    font:inherit; font-size:12.5px; font-weight:600; color:var(--muted); cursor:pointer;
    border:1px solid var(--border); background:var(--panel); padding:6px 11px; border-radius:9px;
    transition:.15s; display:flex; align-items:center; gap:6px;
  }
  button.lctl:hover{border-color:#39405a; color:var(--text)}
  button.lctl.active{color:var(--accent); border-color:rgba(122,162,247,.35)}
  /* launch loading spinner */
  @keyframes lspin{to{transform:rotate(360deg)}}
  .lspinner{width:12px;height:12px;border:2px solid var(--border);border-top-color:var(--accent);
    border-radius:50%;animation:lspin .7s linear infinite;display:none}
  .lspinner.show{display:inline-block}

  /* === V2 PRESENTATION REGISTRY === */
  /* settings panel */
  #setp{display:none; margin:0 16px 10px; background:var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:14px 16px; box-shadow:var(--shadow); animation:drop .25s ease}
  #setp.show{display:block}
  .setrow{display:flex; align-items:center; gap:12px; padding:9px 6px; border-bottom:1px solid rgba(255,255,255,.04)}
  .setrow:last-child{border-bottom:none}
  .setrow label{font-weight:600; font-size:13px; color:var(--text); min-width:70px}
  .setrow select{flex:1; background:var(--bg2); border:1px solid var(--border); color:var(--text);
    border-radius:8px; padding:7px 10px; font:inherit; font-size:13px; outline:none; cursor:pointer}
  .setrow select:hover{border-color:#39405a}
  .setrow .setdesc{font-size:11.5px; color:var(--faint); min-width:80px; text-align:right}
  /* ---- responsive card deck grid (NOW-card N-P10, kills absolute-position islands) ---- */
.deck-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:12px;padding:16px}
@media(max-width:1199px){.deck-grid{grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}}
@media(max-width:767px){.deck-grid{grid-template-columns:1fr;padding:10px}}
/* glass-card tiles (strangler: lives alongside pills, shown when glass-card variant active) */
  #tiles{display:none; flex-wrap:wrap; gap:10px; padding:0}
  #tiles.show{display:flex}
  .gcard{position:relative; background:rgba(20,22,29,.7); backdrop-filter:blur(12px);
    border:1px solid var(--border); border-radius:14px; padding:10px 14px; min-width:125px;
    cursor:pointer; transition:.18s; display:flex; align-items:center; gap:10px; box-shadow:var(--shadow)}
  .gcard{position:relative; background:rgba(20,22,29,.7); backdrop-filter:blur(12px); border:1px solid var(--border); border-radius:14px; padding:12px 16px; cursor:pointer; transition:.15s; user-select:none; width:100%; box-sizing:border-box}
.gcard .gplan{display:flex; gap:4px; flex-wrap:wrap; margin:6px 0 8px; font-size:11.5px}
.gcard .gplan-mark{font-family:"SF Mono",SFMono-Regular,Consolas,monospace; font-size:10.5px}
.gplan-mark.done{color:#5fd39b}.gplan-mark.prog{color:var(--amber)}.gplan-mark.pend{color:var(--faint)}.gplan-mark.blocked{color:var(--danger)}
.gcard:hover{border-color:#39405a; background:rgba(23,26,34,.82)}
  .gcard.online{border-color:rgba(95,211,155,.22)}
  .gcard.online .gdot{background:var(--user); box-shadow:0 0 10px var(--user)}
  .gcard.nudged{border-color:rgba(240,102,110,.4); animation:gpulse 1.5s infinite}
  .gcard.steered{border-color:rgba(122,162,247,.32)}
  @keyframes gpulse{0%,100%{box-shadow:0 0 0 0 rgba(240,102,110,.3)}50%{box-shadow:0 0 14px 4px rgba(240,102,110,.18)}}
  .gdot{width:8px;height:8px;border-radius:50%;background:var(--faint); flex:none}
  .gname{font-weight:650; font-size:13px; color:var(--text)}
  .gbadge{font-size:9.5px; font-weight:700; padding:1px 6px; border-radius:5px; text-transform:uppercase; letter-spacing:.3px}
  .gbadge.admin{color:var(--accent); background:rgba(122,162,247,.15); border:1px solid rgba(122,162,247,.25)}
  .gcard .gactions{display:none; position:absolute; top:calc(100% + 2px); left:0; right:0; z-index:10;
    background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:8px;
    box-shadow:var(--shadow); flex-direction:column; gap:5px}
  .gcard.expanded .gactions{display:flex}
  .gactions button{font:inherit; font-size:11.5px; padding:5px 9px; border-radius:7px;
    cursor:pointer; border:1px solid var(--border); background:var(--panel); color:var(--text); transition:.15s; text-align:left}
  .gactions button:hover{border-color:#39405a}
  .gactions .gact-spawn{background:rgba(122,162,247,.15); border-color:rgba(122,162,247,.3); color:var(--accent)}
  .gactions .gact-kill{color:var(--danger); border-color:rgba(240,102,110,.25)}
  /* compact glass-card: icon-only */
  #tiles.compact .gcard{min-width:auto; padding:8px 10px}
  #tiles.compact .gcard .gname,#tiles.compact .gcard .gbadge,#tiles.compact .gcard .sig{display:none}
  #tiles.compact .gcard .gdot{width:10px;height:10px}

  /* === iso-cube tile === */
  .icube-row{display:flex; gap:20px; flex-wrap:wrap}
  .icube{position:relative; width:90px; height:90px; cursor:pointer; perspective:600px; flex:none}
  .icube-inner{position:relative; width:100%; height:100%; transform:rotateX(-25deg)rotateY(-35deg); transform-style:preserve-3d; transition:transform .35s ease}
  .icube:hover .icube-inner,.icube.sel .icube-inner{transform:rotateX(-25deg)rotateY(-35deg) translateZ(12px)}
  .icube-face{position:absolute; width:90px; height:90px; border:2px solid var(--border); border-radius:12px;
    display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; backface-visibility:hidden}
  .icube-top{transform:rotateX(90deg)translateZ(45px); background:rgba(20,22,29,.76)}
  .icube-front{transform:translateZ(45px); background:rgba(20,22,29,.82)}
  .icube-right{transform:rotateY(90deg)translateZ(45px); background:rgba(16,18,24,.78)}
  .icube .iavid{display:none}
  .icube .iav{width:28px;height:28px;border-radius:7px; display:grid;place-items:center;
    font-weight:700; font-size:11px; color:#0a0b0f}
  .iav.claude{background:linear-gradient(135deg,#e0915c,#d97b5a)}
  .iav.deepseek{background:linear-gradient(135deg,#7aa2f7,#9d7cf7)}
  .iav.user{background:linear-gradient(135deg,#5fd39b,#3fbf86)}
  .icube .iname{font-size:11px;font-weight:650;color:var(--text)}
  .icube.online .icube-front{border-color:rgba(95,211,155,.4); box-shadow:0 0 16px rgba(95,211,155,.18)}
  .icube.nudged .icube-front{border-color:rgba(240,102,110,.55); animation:gpulse 1.5s infinite}
  .icube .igact{display:none; position:absolute; top:calc(100% + 4px); left:-10px; z-index:10;
    background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:7px; box-shadow:var(--shadow);
    flex-direction:column; gap:4px; min-width:110px}
  .icube.expanded .igact{display:flex}
  .igact button{font:inherit; font-size:11px; padding:5px 8px; border-radius:7px; cursor:pointer;
    border:1px solid var(--border); background:var(--panel); color:var(--text); transition:.15s; text-align:left}
  .igact button:hover{border-color:#39405a}
  .igact .ig-spawn{background:rgba(122,162,247,.15); border-color:rgba(122,162,247,.3); color:var(--accent)}
  .igact .ig-kill{color:var(--danger); border-color:rgba(240,102,110,.25)}

  /* === RAZER SQUARE selector frame ===
     Daniil 2026-08-01: "the hexagon and agent avatar are supposed to be one button to the left of
     the message field." They were two controls doing one job in two places -- #ash was a standalone
     56px row ABOVE the composer (hexagon -> horizontally expanding tile strip) while the live
     presence avatar sat separately in the composer, and the Broadcast chip was a THIRD way to pick
     a target. Now: #ash lives inside .cwrap as the single left-hand control, the live avatar mounts
     INSIDE the frame (presence-cloud.js pc-inframe), and the tile strip opens as a popover instead
     of expanding inline -- an inline expander in the composer row would squeeze the message field,
     which is the thing it sits next to. */
  /* THE AGENT BUTTON: avatar + name + status, as one labelled control.
     Daniil: "fix our agent selection button to not have that C be misplaced. thats supposed to be
     our avatar, I want it to have useful information on hover and to actually have the name of
     the ai underneath it as well as other cool status info."
     The C looked misplaced because TWO things shared one box: the frame's own centred glyph and
     #pcloud absolutely positioned over it. Now the frame is a pure container -- the glyph only
     renders when no avatar is present -- and the name/status sit UNDER it in a column, which is
     also what makes it identifiable at a glance instead of being an unlabelled square. */
  #ash{display:flex; flex-direction:column; align-items:center; gap:3px; margin:0;
       position:static; flex:none; align-self:flex-end; padding-bottom:2px; min-width:46px}
  #ash-frame{flex:none; width:38px; height:38px; border-radius:12px;
    background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02));
    border:1px solid rgba(255,255,255,.12); cursor:pointer; transition:.25s ease;
    display:grid; place-items:center; position:relative; z-index:2; font-size:15px; color:var(--muted);
    box-shadow:0 1px 0 rgba(255,255,255,.12) inset, 0 6px 16px -8px rgba(0,0,0,.85)}
  #ash-frame:hover{border-color:rgba(122,162,247,.5);
    box-shadow:0 1px 0 rgba(255,255,255,.16) inset, 0 0 22px -6px rgba(122,162,247,.5)}
  #ash-frame.open{border-radius:14px 14px 4px 14px}
  /* the label: name on top line, live status beneath -- glanceability, not decoration */
  #ash-label{display:flex; flex-direction:column; align-items:center; line-height:1.15;
             max-width:76px; pointer-events:none}
  #ash-label .nm{font-size:9.5px; font-weight:650; color:var(--text); letter-spacing:.01em;
                 max-width:76px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  #ash-label .st{font-size:8.5px; color:var(--faint); letter-spacing:.05em; text-transform:uppercase;
                 max-width:76px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  #ash-label .st.live{color:var(--user-a,#48e6bf)}
  @keyframes chroma-breath{
    0%,100%{box-shadow:0 0 6px 0 rgba(122,162,247,.25),inset 0 0 6px 0 rgba(122,162,247,.08)}
    50%{box-shadow:0 0 18px 4px rgba(122,162,247,.45),inset 0 0 12px 2px rgba(122,162,247,.14)}
  }
  #ash-frame.chroma-claude{animation:chroma-breath-c 2.2s ease-in-out infinite; border-color:rgba(224,145,92,.5)}
  #ash-frame.chroma-deepseek{animation:chroma-breath-d 2.2s ease-in-out infinite; border-color:rgba(122,162,247,.5)}
  #ash-frame.chroma-user{animation:chroma-breath-u 2.2s ease-in-out infinite; border-color:rgba(95,211,155,.5)}
  @keyframes chroma-breath-c{0%,100%{box-shadow:0 0 6px 0 rgba(224,145,92,.2),inset 0 0 6px 0 rgba(224,145,92,.06)}50%{box-shadow:0 0 20px 5px rgba(224,145,92,.42),inset 0 0 14px 3px rgba(224,145,92,.12)}}
  @keyframes chroma-breath-d{0%,100%{box-shadow:0 0 6px 0 rgba(122,162,247,.25),inset 0 0 6px 0 rgba(122,162,247,.08)}50%{box-shadow:0 0 20px 5px rgba(122,162,247,.48),inset 0 0 14px 3px rgba(122,162,247,.14)}}
  @keyframes chroma-breath-u{0%,100%{box-shadow:0 0 6px 0 rgba(95,211,155,.2),inset 0 0 6px 0 rgba(95,211,155,.06)}50%{box-shadow:0 0 20px 5px rgba(95,211,155,.38),inset 0 0 14px 3px rgba(95,211,155,.11)}}
  /* tile strip as a POPOVER above the composer (was an inline horizontal expander to max-width:600px,
     which inside .cwrap would shove the message field sideways every time it opened). Bounded and
     scrollable for the same reason .roster-pop is: the fleet grows, the picker must not. */
  #ash-content{display:none; position:absolute; bottom:calc(100% + 10px); left:16px; z-index:16;
    align-items:center; gap:2px; flex-wrap:wrap; animation:ashSlide .22s ease;
    background:var(--panel2); border:1px solid var(--border); border-radius:12px; padding:6px;
    box-shadow:var(--shadow); max-width:min(560px,calc(100vw - 48px));
    max-height:min(34vh,280px); overflow:auto; overscroll-behavior:contain}
  #ash-content.show{display:flex}
  @keyframes ashSlide{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  #ash-sep{display:none}   /* the inline separator has no meaning once the strip is a popover */

  /* === settings per-variant config === */
  .setcfg{margin-top:3px; display:flex; flex-wrap:wrap; gap:8px; padding-left:82px}
  .setcfg label{font-size:11.5px; color:var(--muted); display:flex; align-items:center; gap:5px; cursor:pointer}
  .setcfg input[type=checkbox]{accent-color:var(--accent); width:14px; height:14px; cursor:pointer}

  /* === session bookends (S4): episode chip + panel + suggestion banner === */
  #epiChip{max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  #epiChip .epidur{color:var(--faint); margin-left:5px; font-size:11px}
  #epiBanner{display:none; align-items:center; gap:10px; margin:10px 16px 0; padding:9px 14px;
    border:1px solid rgba(72,230,191,.35); border-radius:10px; background:var(--glass);
    box-shadow:0 0 14px rgba(72,230,191,.12); font-size:12.5px}
  #epiBanner.show{display:flex; animation:drop .25s ease}
  #epiBanner .epireason{color:var(--faint); font-size:11.5px; flex:none}
  #epiBanner .epititle{overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text)}
  #epiBanner .lctl{flex:none}
  #epi{display:none; margin:0 16px 10px; background:var(--panel); border:1px solid var(--border);
    border-radius:12px; padding:12px 14px; font-size:12.5px}
  #epi.show{display:block}
  .epirow{display:flex; align-items:center; gap:8px; margin:4px 0}
  .epirow label{flex:none; width:78px; color:var(--faint); font-size:11.5px}
  .epirow input,.epirow textarea{flex:1; background:rgba(255,255,255,.04); color:var(--text);
    border:1px solid var(--border); border-radius:8px; padding:6px 9px; font-size:12.5px; font-family:inherit}
  .epirow textarea{resize:vertical; min-height:38px}
  .epirow input:focus,.epirow textarea:focus{outline:none; border-color:var(--aurora-neon,#48e6bf)}
  #epiMeta{color:var(--faint); font-size:11.5px; margin:2px 0 8px}

  /* ===== T079-E4 ENGINE ROOM: gauge cluster (vitals strip above the feed) ===== */
  #engine-room{display:flex; gap:0; margin:4px 16px 0; padding:10px 14px;
    background:var(--glass); border:1px solid var(--glass-line); border-radius:14px;
    backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px);
    min-height:48px; align-items:center; flex-wrap:wrap;
    font-size:12px; transition:opacity .25s}
  #engine-room.quiet{opacity:.55}
  .er-gauge{display:flex; align-items:center; gap:6px; padding:0 12px;
    border-right:1px solid var(--glass-line); white-space:nowrap}
  .er-gauge:last-child{border-right:none}
  .er-label{color:var(--faint); font-size:10px; text-transform:uppercase; letter-spacing:.4px}
  .er-val{font-weight:650; font-size:13px}
  .er-val.green{color:var(--user)} .er-val.amber{color:var(--amber)} .er-val.red{color:var(--danger)} .er-val.off{color:var(--muted)}
  /* heartbeat ring — pulsing circle */
  .er-hb{width:14px;height:14px;border-radius:50%;flex:none}
  .er-hb.active{background:var(--user); box-shadow:0 0 8px var(--user); animation:hbPulse 1.5s infinite}
  .er-hb.idle{background:var(--amber); box-shadow:0 0 4px var(--amber)}
  .er-hb.offline{background:var(--muted); box-shadow:none}
  .er-hb.down{background:var(--danger); box-shadow:0 0 6px var(--danger)}
  @keyframes hbPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.35)}}
  /* breaker light */
  .er-blink{width:8px;height:8px;border-radius:50%;flex:none}
  .er-blink.tripped{background:var(--danger); animation:blink .6s infinite}
  .er-blink.good{background:var(--user)}
  .er-blink.warn{background:var(--amber)}
  /* token bar */
  .er-tokbar{width:48px;height:6px;border-radius:3px;background:var(--bg2);overflow:hidden;flex:none}
  .er-tokbar .fill{height:100%;border-radius:3px;transition:width .5s,background .5s}
  .er-tokbar .fill.low{background:var(--user)} .er-tokbar .fill.mid{background:var(--amber)} .er-tokbar .fill.high{background:var(--danger)}
  /* flow flag */
  .er-flow{display:flex;gap:2px;align-items:flex-end}
  .er-flow div{width:4px;border-radius:2px;transition:height .5s,background .5s}
  .er-flow div.low{background:var(--user)} .er-flow div.mid{background:var(--amber)} .er-flow div.high{background:var(--danger)}
</style>
</head>
<body>
<canvas id="aurora-canvas"></canvas>
<canvas id="viz-canvas"></canvas>
<div class="app">
  <header>
    <div class="brand"><div class="logo"></div> Bifrost <small>live agent console</small></div>
    <div class="fpulse green" id="fpulse" title="fleet: all clear"></div>
    <div class="spacer"></div>
    <div class="pills" id="pills"></div>
    <div id="tiles" class="deck-grid"></div>
    <button class="lctl" id="epiChip" onclick="toggleEpisode()" title="current episode (session bookends)">📖 episode</button>
    <button class="ctl" id="reloadBtn" onclick="reloadUI()" title="reload the UI server (after an agent edits it)">↻</button>
    <button class="lctl" id="gearBtn" onclick="toggleSettings()" title="presentation settings">⚙</button>
    <button class="lctl" id="lnchrBtn" onclick="toggleLauncher()" title="launch &amp; manage agents">🚀 Agents</button>
    <button class="lctl" id="vizBtn" onclick="vizToggle()" title="toggle viz slide deck (v)">📊 Deck</button>
    <button class="ctl pause" id="pauseBtn" onclick="togglePause()">⏸ Pause</button>
  </header>
  <div class="banner" id="banner">⏸ Paused — the agents are frozen. Type below to interject, then Resume.</div>
  <div id="epiBanner">
    <span style="flex:none">📖</span>
    <span class="epititle" id="epiSugTitle"></span>
    <span class="epireason" id="epiSugReason"></span>
    <span style="flex:1"></span>
    <button class="lctl" onclick="epiSuggestAccept()">Accept</button>
    <button class="lctl" onclick="epiSuggestIgnore()">Ignore</button>
    <button class="lctl" onclick="epiSuggestContinue()">Continue</button>
  </div>
  <div id="hud"><div id="hud-toggle" class="show" onclick="toggleHUD()" title="collapse HUD">⌃ collapse</div></div>
  <div id="engine-room"></div>
  <div id="deck"><div class="deck-cards" id="deckCards"></div><div class="slide-dots" id="deckDots"></div><div class="deck-controls"><span class="deck-ctrl" id="deckPrev" onclick="deckPrev()">◀ prev</span><span class="deck-ctrl" id="deckPause" onclick="deckTogglePause()">⏸ pause</span><span class="deck-ctrl" id="deckNext" onclick="deckNext()">next ▶</span></div></div>
  <div id="lnchr">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span style="font-weight:650;font-size:13px">Agent Launcher</span>
      <span style="color:var(--faint);font-size:11.5px">— one-click start/stop, primed with context</span>
    </div>
    <div id="lnchrRows"></div>
  </div>
  <div id="epi">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px">
      <span style="font-weight:650;font-size:13px">📖 Current episode</span>
      <span style="color:var(--faint);font-size:11.5px">— a titled, confined stretch of this session (WHAT + WHY)</span>
      <span style="flex:1"></span>
      <button class="lctl" id="epiCloseBtn" onclick="epiClose()">⏹ End episode</button>
    </div>
    <div id="epiMeta"></div>
    <div id="epiDraft" style="display:none">
      <div class="epirow"><label>Title</label><input id="epiTitle" placeholder="what this stretch was"></div>
      <div class="epirow"><label>Description</label><textarea id="epiDesc" placeholder="what happened"></textarea></div>
      <div class="epirow"><label>Why</label><textarea id="epiWhy" placeholder="the intent behind it"></textarea></div>
      <div class="epirow" style="justify-content:flex-end">
        <span style="color:var(--faint);font-size:11px;margin-right:auto" id="epiDraftHint">review the draft, edit any field, then accept</span>
        <button class="lctl" onclick="epiDraftCancel()">Later</button>
        <button class="lctl" style="border-color:rgba(95,211,155,.5)" onclick="epiDraftAccept()">✓ Accept</button>
      </div>
    </div>
  </div>
  <div id="setp">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
      <span style="font-weight:650;font-size:13px">⚙ Presentation</span>
      <span style="color:var(--faint);font-size:11.5px">— pick variants per slot; swaps live</span>
    </div>
    <div id="setpRows"></div>
    <div style="border-top:1px solid var(--border);margin:10px 0 6px;padding-top:10px">
      <span style="font-weight:650;font-size:13px">🌌 Aurora Glass</span>
      <span style="color:var(--faint);font-size:11.5px"> — progressive enhancement; toggle live</span>
    </div>
    <div id="setpAurora">
      <div class="setrow">
        <label>WebGL Aurora</label>
        <span class="setdesc">animated aurora background (needs WebGL2 + bench PASS)</span>
      </div>
      <div class="setrow" style="justify-content:flex-end">
        <button id="auroraToggle" class="lctl" onclick="toggleAuroraFlag()">Enable</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="auroraStatus">off — run bench-aurora.html first</span>
      </div>
      <div class="setrow">
        <label>HUD Strip</label>
        <span class="setdesc">who's-doing-what glanceability strip</span>
      </div>
      <div class="setrow" style="justify-content:flex-end">
        <button id="hudToggle" class="lctl" onclick="toggleHUDFlag()">Disable</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="hudStatus">on — pure DOM, no perf cost</span>
      </div>
      <div class="setrow">
        <label>Traces</label>
        <span class="setdesc">agent tool-use cards — expanded (full visibility) | collapsed (compact)</span>
      </div>
      <div class="setrow" style="justify-content:flex-end;gap:6px">
        <button class="lctl traces-btn active" data-lvl="expanded" onclick="setTraces('expanded')">expanded</button>
        <button class="lctl traces-btn" data-lvl="collapsed" onclick="setTraces('collapsed')">collapsed</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="tracesStatus">expanded — operator view</span>
      </div>
      <div class="setrow">
        <label>Narration</label>
        <span class="setdesc">claude's reasoning visibility — off | key | full</span>
      </div>
      <div class="setrow" style="justify-content:flex-end;gap:6px">
        <button class="lctl narr-btn" data-lvl="off" onclick="setNarration('off')">off</button>
        <button class="lctl narr-btn active" data-lvl="key" onclick="setNarration('key')">key</button>
        <button class="lctl narr-btn" data-lvl="full" onclick="setNarration('full')">full</button>
        <span style="font-size:11px;color:var(--faint);margin-left:8px" id="narrStatus">key — decision points only</span>
      </div>
      <div class="setrow" id="auroraSpeedRow" style="display:none">
        <label>Drift Speed</label>
        <input type="range" id="auroraSpeedSlider" min="0.25" max="2" step="0.05" value="1" style="flex:1;margin:0 8px"
          oninput="setAuroraSpeed(parseFloat(this.value))">
        <span class="setdesc" id="auroraSpeedLabel">1×</span>
      </div>
      <div class="setrow" id="auroraIntensityRow" style="display:none">
        <label>Intensity</label>
        <input type="range" id="auroraIntensitySlider" min="0.2" max="1" step="0.05" value="0.85" style="flex:1;margin:0 8px"
          oninput="setAuroraIntensity(parseFloat(this.value))">
        <span class="setdesc" id="auroraIntensityLabel">0.85</span>
      </div>
    </div>
  </div>
  <div id="log"></div>
  <div class="activity" id="activity"></div>
  <div class="composer">
    <div class="ladder" id="ladder">
      <button type="button" class="seg" data-fid="inform" onclick="setFidelity('inform')">Inform</button>
      <button type="button" class="seg" data-fid="steer" onclick="setFidelity('steer')">Steer</button>
      <button type="button" class="seg" data-fid="interrupt" onclick="setFidelity('interrupt')">Interrupt</button>
    </div>
    <canvas id="voiceline" class="voiceline" title="emission rate"></canvas>
    <div class="cwrap">
      <div id="ash">
        <div id="ash-frame" onclick="toggleAsh()" title="agent selector — live presence">⏣</div>
        <div id="ash-label"><span class="nm">—</span><span class="st">no target</span></div>
        <div id="ash-sep"></div>
      </div>
      <div class="recipient" id="recipient" role="button" tabindex="0" title="who receives your message — click to choose" onclick="toggleRoster()">
        <div class="rstack" id="rstack"></div>
        <div class="rlabel" id="rlabel"></div>
      </div>
      <select id="target" style="display:none"></select>
      <select id="fidelity" style="display:none"><option value="inform">inform</option><option value="steer">steer</option><option value="interrupt">interrupt</option><option value="chat">chat</option></select>
      <textarea id="input" rows="1" placeholder="Message the agents… (Enter to send, Shift+Enter for newline)"></textarea>
      <button class="send" id="sendBtn" onclick="send()">➤</button>
    </div>
    <div id="ash-content"></div>
    <div class="roster-pop" id="rosterPop"></div>
    <div class="hint" id="fidhint">↳ Inform = adopt next turn · Steer = fold into current task (no stop) · Interrupt = drop &amp; switch · ⏸ Pause = freeze everyone · 📎 Ctrl+V paste images or drag &amp; drop files</div>
  </div>
</div>
<div id="drop"><div class="dz" id="dropZone"><div class="big">Drop files to share</div><div class="sub">saved into the project · agents can read them with their tools<br><span style="color:var(--faint);font-size:11px;margin-top:4px;display:inline-block">also: Ctrl+V to paste images from clipboard</span></div><img class="preview" id="dropPreview"><div class="filenames" id="dropFilenames"></div></div></div>
<div id="toast"></div>
<div id="viz-ctl">
  <button onclick="vizPrev()" title="previous card (←)">◀</button>
  <button id="vizGridBtn" onclick="vizGrid()" title="grid view (g)">⊞ grid</button>
  <button onclick="vizNext()" title="next card (→)">▶</button>
  <span style="font-size:10px;color:var(--faint);padding:5px 4px" id="vizLabel">—</span>
  <button id="vizDeckBtn" onclick="vizDeckMode()" title="full-view deck mode (d) — shrinks message log">⛶ deck</button>
  <button onclick="vizToggle()" title="hide viz (v)">✕</button>
</div>

<script src="/aurora-shader.js"></script>
<script src="/bifrost_viz.js"></script>
<script>
const log = document.getElementById('log');
const seen = new Set();
let paused = false, nearBottom = true, lastFrom = null;

log.addEventListener('scroll', ()=>{
  nearBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 120;
  if(log.scrollTop < 60) prependOlder();     // reached the top -> re-hydrate older history from the buffer
});

function esc(s){ return (s==null?'':String(s)).replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function fmt(s){
  s = esc(s);
  s = s.replace(/```([\s\S]*?)```/g, (m,c)=>'<pre><code>'+c.replace(/^\n/,'')+'</code></pre>');
  s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  return s;
}
function initials(a){ return (a||'?').slice(0,2).toUpperCase(); }
function cls(a){ return (a==='claude'||a==='deepseek'||a==='user') ? a : 'system'; }
function now(ts){ try{ return new Date(ts.replace(' ','T')).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});}catch(e){return '';} }

/* ---- T121 S-cut epistemic glyph (kimi, G4-amended + G11) --------------------
   ONE pure derivation over the EXACT renderer boundary m.epistemic =
   EpistemicView.to_dict(). Python seam (codex's half):
       core.primitives.epistemic.epistemic_view_from_bus(message)
   S-cut consumes TWO typed inputs only:
       m.epistemic.currency.value    -> staleness glyph (fresh/aging/stale/?)
       m.epistemic.claim_kind.value  -> text marker      ([infer]/[guess])
   Missing/unsupported axis => value:'unknown'. NO fallback to m.ts or prose:
   a transport timestamp is not a currency receipt, so absent evidence renders
   UNKNOWN, never default-fresh.
   The glyph is a STRUCTURAL sibling of .time (not content, not dial-reachable). */
var EPI_GLYPH = {fresh:'\u25CF', aging:'\u25D0', stale:'\u25CB', unknown:'?'};
// currency.value (EpistemicView) -> render tier. Exact enum values only; NO ts fallback.
// UNKNOWN is the explicit default (G4-amended): unsupported/missing axis => 'unknown' tier.
var EPI_CURRENCY_TIER = {current:'fresh', aging:'aging', stale:'stale', superseded:'stale', unknown:'unknown'};
function epiGlyph(m){
  m = m || {};
  var epi = m.epistemic || {};
  // claim_kind.value -> text marker (typed field only; no prose sniffing)
  var ck = ((epi.claim_kind && epi.claim_kind.value) || '').toString().toLowerCase();
  var marker = (ck==='inferred') ? '[infer]'
             : (ck==='guessed')  ? '[guess]' : '';
  // currency.value -> staleness tier (typed field only; unknown by default)
  var cur = ((epi.currency && epi.currency.value) || 'unknown').toString().toLowerCase();
  var tier = EPI_CURRENCY_TIER.hasOwnProperty(cur) ? EPI_CURRENCY_TIER[cur] : 'unknown';
  return {tier:tier, glyph:EPI_GLYPH[tier]||EPI_GLYPH.unknown, marker:marker,
          unknown:(tier==='unknown')};
}

const allMsgs = [];                          // full-session data buffer (cheap); the DOM stays a window over it
const HISTORY_BATCH = 100;                    // messages re-hydrated per scroll-to-top

// T002: trace-run accumulator — consecutive same-agent traces fold into one collapsible card
var _traceRun = {agent:null, traces:[], firstIdx:null};

function _buildTraceCard(run){
  // count by kind
  var counts = {};
  run.traces.forEach(function(t){ var k = t.kind||'trace'; counts[k] = (counts[k]||0)+1; });
  var countParts = Object.keys(counts).map(function(k){ return counts[k]+' '+k; });
  var summary = countParts.join(', ') || run.traces.length+' trace(s)';

  var card = document.createElement('div');
  card.className = 'trace-card';
  // header
  var hdr = document.createElement('div');
  hdr.className = 'trace-card-header';
  hdr.innerHTML = '<span class="tc-arrow">▶</span>'+
    '<span class="trav '+cls(run.agent)+'">'+esc(run.agent)+'</span>'+
    '<span class="tc-counts">'+esc(summary)+'</span>';
  // body
  var body = document.createElement('div');
  body.className = 'trace-card-body';
  run.traces.forEach(function(t){
    var tl = document.createElement('div'); tl.className = 'traceline';
    tl.innerHTML = '<span class="trav '+cls(run.agent)+'">'+esc(run.agent)+'</span><span class="trat">'+esc(t.text||'')+'</span>';
    body.appendChild(tl);
  });
  card.appendChild(hdr); card.appendChild(body);
  // click to toggle
  hdr.addEventListener('click', function(e){
    e.stopPropagation();
    card.classList.toggle('open');
  });
  return card;
}

function _flushTraceRun(){
  if(!_traceRun.agent || !_traceRun.traces.length) return;
  var run = _traceRun;
  _traceRun = {agent:null, traces:[], firstIdx:null};
  var card = _buildTraceCard(run);
  _msgPlacer(card, {kind:'trace-card', from:run.agent, meta:{}});
  autoscroll();
  // also feed the slide-deck buffer one aggregated entry
  if(typeof _captureTrace === 'function'){
    var counts = {}; run.traces.forEach(function(t){ var k = t.kind||'trace'; counts[k]=(counts[k]||0)+1; });
    var parts = Object.keys(counts).map(function(k){ return counts[k]+' '+k; });
    _captureTrace({from:run.agent, kind:'trace', content:'['+parts.join(', ')+']'});
  }
}

function _flushTraceRunToFrag(frag){
  // variant for history: builds card and appends to fragment (no _msgPlacer, no autoscroll)
  if(!_traceRun.agent || !_traceRun.traces.length) return;
  var run = _traceRun;
  _traceRun = {agent:null, traces:[], firstIdx:null};
  var card = _buildTraceCard(run);
  if(run.firstIdx !== null) card.dataset.mi = run.firstIdx;
  frag.appendChild(card);
}

function renderMsg(m){                        // build a message's DOM node (no placement) -- reused for live + history
  const from = m.from || 'system';
  const kind = m.kind || 'chat';
  const isGuard = /loop-guard/i.test(m.content||'');
  if(kind==='trace'){
    const d=document.createElement('div'); d.className='traceline';
    d.innerHTML='<span class="trav '+cls(from)+'">'+esc(from)+'</span><span class="trat">'+esc(m.content||'')+'</span>';
    return d;
  }
  if(from==='system' || kind==='note'){
    const d=document.createElement('div'); d.className='sys'+(isGuard?' guard':'');
    d.innerHTML='<span>'+esc(m.content||'')+'</span>'; return d;
  }
  const me = from==='user'; const c = cls(from);
  const wrap=document.createElement('div'); wrap.className='msg'+(me?' me':'');
  if(m.ts) wrap.setAttribute('data-ts', m.ts.replace(' ','T'));
  const hop = (m.meta && m.meta.hops)? '<span class="hop">hop '+m.meta.hops+'</span>':'';
  const intent = (m.meta && m.meta.intent)? '<span class="ib ib-'+m.meta.intent+'" title="'+esc(m.meta.why||'')+'">'+m.meta.intent+'</span>':'';
  const epi = epiGlyph(m);
  const epimark = epi.marker? '<span class="epi epi-mark epi-'+epi.tier+'">'+epi.marker+'</span>' : '';
  const epig = '<span class="epi epi-'+epi.tier+'" data-epi-tier="'+epi.tier+'" title="'+epi.tier+(epi.unknown?' (no stamp — status unknown)':'')+'">'+epi.glyph+'</span>';
  wrap.innerHTML =
    '<div class="av '+c+'">'+initials(from)+'</div>'+
    '<div class="bubble"><div class="row"><span class="who '+c+'">'+esc(from)+'</span>'+
    '<span class="time">'+now(m.ts)+'</span>'+epig+epimark+intent+hop+'</div>'+
    '<div class="content">'+_msgRenderer(m)+'</div></div>';
  return wrap;
}

function addMsg(m){
  if(m.id && m.id!=='0'){ if(seen.has(m.id)) return; seen.add(m.id); }
  if((m.kind||'chat')==='_ready') return;
  // negotiation verdict: display prominently
  const kind = m.kind||'chat';
  if(kind === 'verdict' || (kind === 'halt' && (m.meta||{}).intent === 'verdict')){
    const v = (m.meta||{}).verdict || 'amber';
    const emoji = {green:'✅', amber:'⚠️', red:'🛑'};
    const d = document.createElement('div');
    d.className = 'sys guard';
    d.innerHTML = '<span>'+(emoji[v]||'')+' Round '+v+': '+esc(m.content||'')+'</span>';
    _msgPlacer(d, m); autoscroll(); return;
  }
  // W70 NOISE-FLOOR: bookkeeping events collapse to a footer counter, never compete
  // with live work in the message log. triage-receipt, msg_ack, stale_notice,
  // expectation_dead, packet_integrity_drop, cursor_admin are bookkeeping.
  // The SSE stream still carries them for raw-feed UIs; ONLY the message log filters.
  const BK = {'triage-receipt':1, msg_ack:1, stale_notice:1, expectation_dead:1,
              packet_integrity_drop:1, cursor_admin:1};
  var content = (m.content||'');
  if(BK[kind] || (content.indexOf&&content.indexOf('[triage-receipt]')===0)){
    _bkCount++; _bkLast = (m.from||'')+' '+kind+(content?' — '+content.substr(0,80):'');
    _renderBkFooter();
    return;
  }
  const idx = allMsgs.push(m) - 1;           // buffer it (data), then render at the live tail
  // T002: trace messages accumulate into a per-agent run — flushed when the run breaks
  if(kind === 'trace'){
    var from = m.from || 'system';
    if(_traceRun.agent === from){
      // same agent: extend the run
      _traceRun.traces.push({kind:kind, text:m.content||'', ts:m.ts});
    } else {
      // different agent (or first trace): flush prior run, start new one
      _flushTraceRun();
      _traceRun = {agent:from, traces:[{kind:kind, text:m.content||'', ts:m.ts}], firstIdx:idx};
    }
    return;  // don't render individually — the flush handles rendering
  }
  // non-trace message: flush any pending trace run, then render normally
  _flushTraceRun();
  const node = renderMsg(m); if(!node) return;
  node.dataset.mi = idx;
  _msgPlacer(node, m); autoscroll();
}

// ---- W70 bookkeeping footer (collapses bookkeeping events to one line) ----
var _bkCount = 0, _bkLast = '';
function _renderBkFooter(){
  var el = document.getElementById('bkFooter');
  if(!el){
    el = document.createElement('div');
    el.id = 'bkFooter';
    el.className = 'bk-footer';
    el.title = 'click to see bookkeeping log';
    el.onclick = function(){ this.classList.toggle('expanded');
      this.textContent = this.classList.contains('expanded') ?
        '📋 '+_bkCount+' bookkeeping event(s) — latest: '+_bkLast : _bkSummary(); };
    var logEl = document.getElementById('log');
    if(logEl) logEl.appendChild(el);
  }
  el.textContent = _bkSummary();
}
function _bkSummary(){ return '📋 '+_bkCount+' bookkeeping event'+
  (_bkCount!==1?'s':'')+' (triage/ack/stale) — click to expand'; }

function prependOlder(){                       // scroll-to-top: re-hydrate older messages from the buffer
  const first = log.firstElementChild; if(!first || first.dataset.mi===undefined) return;
  const oldest = parseInt(first.dataset.mi);
  if(oldest<=0) return;                        // already at the start of the session
  const start = Math.max(0, oldest-HISTORY_BATCH);
  const h0 = log.scrollHeight, frag=document.createDocumentFragment();
  // T002: save/restore live trace run so history rendering doesn't clobber it
  var savedRun = _traceRun;
  _traceRun = {agent:null, traces:[], firstIdx:null};
  for(let i=start;i<oldest;i++){
    const m = allMsgs[i];
    if((m.kind||'chat')==='trace'){
      // T002: collapse consecutive same-agent traces in history too
      var from = m.from||'system';
      if(_traceRun.agent === from){
        _traceRun.traces.push({kind:m.kind||'trace', text:m.content||'', ts:m.ts});
      } else {
        _flushTraceRunToFrag(frag);
        _traceRun = {agent:from, traces:[{kind:m.kind||'trace', text:m.content||'', ts:m.ts}], firstIdx:i};
      }
    } else {
      _flushTraceRunToFrag(frag);
      var n = renderMsg(m); if(n){ n.dataset.mi=i; frag.appendChild(n); }
    }
  }
  _flushTraceRunToFrag(frag);  // flush any trailing trace run
  _traceRun = savedRun;        // restore live accumulator
  log.insertBefore(frag, log.firstElementChild);
  log.scrollTo({top: log.scrollTop + (log.scrollHeight - h0), behavior: 'instant'});  // anchor: instant jump, not smooth animation (CSS smooth serviced user scroll, not programmatic anchoring)
}
const MAX_LOG_NODES = 250;                  // bounded render window (Doom 'culling'): cap DOM so a long/bursty log never grows into lag
function trimLog(){
  // absolute ceiling (rare): never grow truly without bound even during a scrolled-up flood
  while(log.childElementCount > 2000) log.removeChild(log.firstElementChild);
  // tail window: at the live tail keep it lean (250); scrollback stays for reading history + re-hydration
  if(nearBottom) while(log.childElementCount > MAX_LOG_NODES) log.removeChild(log.firstElementChild);
}
function autoscroll(){ trimLog(); if(nearBottom) log.scrollTo({top: log.scrollHeight, behavior: 'instant'}); }
// real rich presence: what each agent is actually doing, from /status (not a client-side guess)
const ICON = {thinking:'💭', reading:'📖', searching:'🔍', inspecting:'🔎', recalling:'🧠', running:'⚙️', writing:'✍️', working:'⚡'};
const VERB = {thinking:'thinking', reading:'reading', searching:'searching', inspecting:'inspecting git', recalling:'searching memory', running:'running a command', writing:'writing', working:'working'};
let lastActSig = null;
// === THE AGENT AVATAR (geodesic shader, claude's lane) =======================================
// ONE avatar, mounted in the agent-selector frame beside the message field, big enough to
// actually read. Daniil: "I want the avatar to be the current button on the bottom left. that
// way its just one avatar for now and it can be big enough to be appreciated and can have an
// ambiant mode and other modes."
//
// One instead of one-per-pill is the better engineering answer as well as the better design
// one: a single 38px canvas costs a rounding error, eleven tiny ones cost eleven WebGL
// contexts (a browser force-loses them past ~16) and eleven raymarchers on a machine whose
// display driver is already TDR-prone.
//
// WHAT IT SHOWS: the state of whoever you are about to talk to. Broadcast has no single
// subject, so it falls to AMBIENT -- alive, unhurried, addressed to nobody in particular.
var _heroAv = null;                // {canvas, shader, st}
var _avatarsOff = false;

// SIZE IS NOT THE SHADER'S BUSINESS. Daniil asked for a two-inch piece; the shader is HOW it
// is beautiful, not WHETHER it exists. Sizing used to sit AFTER the WebGL attempt, so all three
// bail paths -- script absent, no WebGL2, compile failure -- silently left a 38px hexagon and
// looked identical to "the change never shipped". On a host with a documented display-driver
// TDR history that path is not hypothetical. The box is now set first and kept regardless.
function sizeHeroFrame(frame){
  var SIZE = 192;                              // 2in at the CSS reference 96dpi (Daniil's ask)
  frame.style.width = SIZE + 'px';
  frame.style.height = SIZE + 'px';
  frame.style.borderRadius = '26px';
  var cw = frame.closest('.cwrap'); if(cw) cw.classList.add('tall');
  return SIZE;
}

function mountHeroAvatar(){
  if(_avatarsOff || _heroAv) return;
  var frame = document.getElementById('ash-frame');
  if(!frame) return;
  var SIZE = sizeHeroFrame(frame);
  // TRANSIENT IS NOT TERMINAL, and conflating the two is the whole bug. agent-avatar.js is a
  // plain sync <script> at the END of <body>, after this one -- so a status poll returning from
  // localhost in under a millisecond can reach here DURING parse, before the class exists. The
  // old code latched _avatarsOff on that check, which turned a millisecond race into a permanent
  // verdict: the poll won on Daniil's machine and lost on mine, same bytes, and the avatar was
  // disabled for the life of the page. Bail without latching; the DOMContentLoaded door mounts
  // it once the script is genuinely there.
  if(typeof AgentAvatar === 'undefined'){ frame.dataset.avOff = 'pending-script'; return; }
  // These two ARE terminal -- no amount of waiting produces a GPU. Latch, and leave WHY on the
  // element: a silent permanent bail is what cost a screenshot and a round-trip to diagnose.
  if(!AgentAvatar.isSupported()){
    frame.dataset.avOff = 'no-webgl2';
    frame.classList.add('av-fallback');
    _avatarsOff = true; return;
  }
  var cv = document.createElement('canvas');
  cv.className = 'heroav';
  cv.width = 96; cv.height = 96;               // backing store = half of the 192px box
  try{ _heroAv = {canvas: cv, shader: new AgentAvatar(cv), st: null}; }
  catch(e){ frame.dataset.avOff = 'ctor: ' + String(e).slice(0,120);
            frame.classList.add('av-fallback'); _avatarsOff = true; return; }
  frame.insertBefore(cv, frame.firstChild);    // beneath #pcloud, which is now a corner badge
  frame.classList.add('has-av');               // the avatar IS the glyph now
  delete frame.dataset.avOff;                  // clear any 'pending-script' left by a lost race
  // Drop the fallback glyph OUTRIGHT rather than hiding it through the cascade -- it is a bare
  // text node on the frame, and font-size:0 is one specificity accident away from a hexagon
  // sitting on top of the avatar, which is exactly what happened on the first attempt. This runs
  // only once the shader is CONSTRUCTED: removing it earlier meant a compile failure left an
  // empty two-inch box, trading a visible wrong thing for an invisible one.
  [].slice.call(frame.childNodes).forEach(function(n){
    if(n.nodeType === 3) frame.removeChild(n);   // text nodes only; #pcloud and the canvas stay
  });
  // The backing store follows the box at half scale. It used to be DISCOVERED by measuring
  // clientWidth, which only works if layout has already settled on the size we set moments ago
  // -- a timing bet that, lost, bakes a thumbnail render target into a two-inch square. The size
  // is not a mystery at this point, so hand it over rather than asking the shader to find it.
  _heroAv.shader._resize(SIZE);
  _heroAv.shader.setState('ambient');
  _heroAv.shader.start();
}

// ===== THE FLEET'S VOICE: emission rate as a waveform =====
// Three readings, and the third is the one the console could not previously express:
//   LIVE    amplitude tracks tokens/sec              -- generating
//   FLAT    solid, steady, dim                       -- measured, and the measure is zero
//   DOTTED  broken baseline                          -- NOT measured; there is no sensor here
var _voice = null, _voiceOff = false, _tokMark = {}, _lastSignals = {};

function mountVoiceLine(){
  if(_voiceOff || _voice) return;
  var cv = document.getElementById('voiceline');
  if(!cv) return;
  // Same transient-vs-terminal split the avatar had to learn: activity-line.js is a plain sync
  // script at the end of <body>, so a fast poll can arrive before it parses. Do not latch.
  if(typeof ActivityLine === 'undefined'){ cv.dataset.vlOff = 'pending-script'; return; }
  if(!ActivityLine.isSupported()){ cv.dataset.vlOff = 'no-webgl2'; _voiceOff = true; return; }
  try{ _voice = new ActivityLine(cv); }
  catch(e){ cv.dataset.vlOff = 'ctor: '+String(e).slice(0,120); _voiceOff = true; return; }
  delete cv.dataset.vlOff;
  var fit = function(){ if(_voice) _voice._resize(cv.clientWidth||640, 22); };
  if(window.ResizeObserver){ new ResizeObserver(fit).observe(cv); } else { window.addEventListener('resize', fit); }
  fit();
  _voice.start();
}

function driveVoiceLine(vitals){
  mountVoiceLine();
  if(_voiceOff || !_voice) return;
  vitals = vitals || {};
  var cv = document.getElementById('voiceline');
  var tsel = document.getElementById('target');
  var tgt = tsel ? tsel.value : 'all';
  // _fence is a pseudo-agent in the vitals blob (renderVitals filters it out too); leaving it in
  // the roll-up would mark a non-agent in _tokMark and dilute nothing useful.
  var names = (tgt === 'all') ? Object.keys(vitals).filter(function(n){ return n !== '_fence'; }) : [tgt];
  var now = performance.now();

  // SENSOR PRESENCE, NOT QUIET. Token counts are reported by the RUNNER path only -- see
  // bifrost_runner_deepseek.py:1037 and its kimi/sol siblings, which pass tokens={prompt,
  // completion} on each turn. An agent with no runner therefore has NO emission sensor at all,
  // and for claude that is structural rather than transient: it runs inside Claude Code, whose
  // usage this process never sees. Reporting that as a quiet line would be a confident lie about
  // a thing we cannot observe, which is the exact failure the avatar was built to stop making.
  var sensed = names.some(function(n){ return (_lastSignals[n]||{}).runner; });

  var rate = 0;
  names.forEach(function(n){
    var c = (((vitals[n]||{}).tokens)||{}).completion || 0;
    var m = _tokMark[n];
    // A DERIVATIVE OF A REAL COUNTER, not an inference from liveness. Guard the negative case:
    // a runner restarting resets its cumulative count, and an unguarded delta would read that
    // as a burst of emission at exactly the moment the agent produced nothing.
    if(m && now > m.t && c >= m.c) rate += (c - m.c) * 1000 / (now - m.t);
    _tokMark[n] = {c: c, t: now};   // marked even when unsensed, so regaining a sensor does not
  });                               // bill the whole blind interval as one instantaneous spike

  _voice.setSensed(sensed);
  _voice.setRate(Math.min(1, rate / 50));      // 50 tok/s = full scale
  // State the claim in WORDS as well as in the encoding. A visual grammar nobody can look up is
  // a cipher; the tooltip is what makes solid-versus-dotted teachable on first hover.
  if(cv){
    var who = (tgt === 'all') ? 'the fleet' : tgt;
    // WORD THE CLAIM TO THE STRENGTH OF THE EVIDENCE. The flat reading rests on
    // signals[agent].runner, which is bool(runner_lock.holder(agent)) -- and holder() reads the
    // lock key WITHOUT checking that its recorded pid is still alive (core/comm/runner_lock.py
    // has _alive(), but only clear_if_pid() calls it). So a runner that died without releasing
    // leaves the flag true indefinitely. "A runner holds the lock" is therefore all this can
    // honestly assert; "we are measuring it" would be a stronger claim than the evidence bears,
    // and overstating certainty is the precise habit this indicator exists to break.
    cv.title = !sensed
      ? 'no emission sensor for ' + who + ' — token counts are reported by the runner path, and '
        + 'no runner lock is held here'
      : (rate > 0.5
          ? 'emitting ~' + Math.round(rate) + ' tok/s'
          : 'a runner lock is held for ' + who + ', reporting no emission '
            + '(note: the lock is not liveness-checked, so a dead runner still reads as present)');
  }
}

// MOUNT DOES NOT WAIT ON THE STATUS POLL. Until now mountHeroAvatar was reachable ONLY through
// driveAvatars(), i.e. only from a status render that parsed cleanly -- so a slow, failed or
// still-pending first poll left the composer's centrepiece as a 38px hexagon, indistinguishable
// from "the change never shipped". That is the exact symptom Daniil screenshotted. The avatar is
// chrome, not data: it should exist as soon as the DOM does, and the poll should only choose its
// STATE. driveAvatars still calls mount() -- it is idempotent -- so this is a second door, not a
// replacement, and the avatar survives whichever of the two arrives first.
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountHeroAvatar);
else mountHeroAvatar();

// Activity verb -> avatar state. The console already knows what each agent is doing; this is
// only the mapping, so there is no second source of truth about agent state.
// 'thinking' now has its OWN row rather than borrowing composing's -- see the note in the avatar
// state table. 'calling-model' and 'awaiting-clarification' are verbs the deepseek/sol/gemini
// chat drivers actually emit (scripts/deepseek_chat.py:283,367) and which nothing here mapped, so
// they fell through to the unknown branch and rendered as a state the agent was not in.
var AV_STATE = {thinking:'thinking', recalling:'thinking', 'calling-model':'thinking',
                'awaiting-clarification':'composing',
                reading:'tool', writing:'tool', searching:'tool', running:'tool',
                inspecting:'tool', working:'tool', idle:'idle'};

function driveAvatars(acts, s){
  mountHeroAvatar();
  if(_avatarsOff || !_heroAv) return;
  acts = acts||{}; s = s||{};
  // status.agents is a list of RECORDS ({agent, last_seen, ...}), not names. Building a Set
  // straight from it yields a Set of objects whose .has('claude') is always false, so every
  // agent silently fell through to 'dead' -- a confident wrong answer, which is the exact
  // failure class this avatar exists to make visible. Accept either shape.
  var online = new Set((s.agents||[]).map(function(x){
    return (x && typeof x === 'object') ? x.agent : x;
  }));
  var tsel = document.getElementById('target');
  var a = tsel ? tsel.value : 'all';
  var st, who = null;      // who = the agent whose identity gradient the body should wear
  // ORDER MATTERS, and the distinctions are the whole point of the avatar:
  //   broadcast -> AMBIENT (no single subject; alive but addressed to nobody)
  //   halted    -> wedged  (held against its will; stillness IS the diagnosis)
  //   online, no activity -> IDLE, never dead. An agent sitting ready is not a corpse, and
  //                          rendering it as one is the mislabeling this project keeps paying for.
  //   offline   -> dead    (absence of the seat, not absence of a verb)
  //   unknown verb -> unsensed (grey and OPEN: we are not claiming to know)
  if(!a || a === 'all'){
    // BROADCAST IS THE FLEET'S FACE, NOT NOBODY'S. This branch used to pin straight to 'ambient',
    // which meant that in the DEFAULT composer state -- Broadcast / ALL AGENTS -- the avatar
    // could never show work no matter how much was happening. Daniil watched a fully live
    // activity feed drive a motionless avatar twice because of this one line, and both times the
    // feed was innocent: the state was decided before acts was ever consulted.
    //
    // Ambient stays correct for a fleet AT REST -- that distinction was the whole reason the
    // state exists -- but a fleet at work should show the work. Rank across everyone: trouble
    // first, then the busiest verb, and ambient only when genuinely nobody is doing anything.
    var RANK = ['wedged','throttled','tool','thinking','composing','idle'];
    var halted = Object.keys(s.halted||{});
    var best = -1;
    if(halted.length){ best = 0; who = halted[0]; }
    Object.keys(acts).forEach(function(n){
      var v = acts[n] && acts[n].state; if(!v) return;
      var r = RANK.indexOf(AV_STATE[v] || '');
      if(r >= 0 && (best < 0 || r < best)){ best = r; who = n; }
    });
    st = best >= 0 ? RANK[best] : 'ambient';
    // WHOEVER SET THE STATE OWNS THE FACE. On broadcast the avatar wears the identity gradient of
    // the agent that won the ranking, so the body answers "who is working" while the edges answer
    // "at what" -- one glance gives both. With nobody working there is no subject, and it falls
    // back to the neutral slate rather than picking someone arbitrarily.
  }
  else if((s.halted||{})[a])            st = 'wedged';
  else if(!(online.has(a)||a==='user')) st = 'dead';
  else if(!(acts[a] && acts[a].state))  st = 'idle';
  else                                  st = AV_STATE[acts[a].state] || 'unsensed';
  if(!who && a && a !== 'all') who = a;      // addressed directly: that agent IS the subject
  if(_heroAv.st !== st){ _heroAv.st = st; _heroAv.shader.setState(st); }
  // Guarded so an unchanged identity does not re-slice its arrays every poll. Both setters ease,
  // so a handover morphs body and lines together rather than snapping either.
  if(_heroAv.ident !== who){ _heroAv.ident = who; _heroAv.shader.setIdentity(who || 'system'); }
  // rate rides ON TOP of the state's base spin, so it must know about 'thinking' -- it was added
  // to the codebook without being added here, and fell to the 0.1 default reserved for the states
  // that are NOT working. Thinking is work; it just is not motion.
  _heroAv.shader.setRate(st === 'tool' ? 0.85 : st === 'thinking' ? 0.6
                       : st === 'composing' ? 0.5 : st === 'ambient' ? 0.25 : 0.1);
}

function renderActivity(acts){
  acts = acts||{};
  const sig = JSON.stringify(acts);
  if(sig === lastActSig) return;   // unchanged -> DON'T rebuild (this was replaying the fade every poll)
  lastActSig = sig;
  const box=document.getElementById('activity');
  const rows=Object.keys(acts).filter(a=>acts[a]&&acts[a].state).map(a=>{
    const st=acts[a].state, dt=acts[a].detail||'', ic=ICON[st]||'⚡', vb=VERB[st]||st;
    return '<div class="actrow"><div class="av '+cls(a)+'">'+initials(a)+'</div>'+
      '<div class="actbubble"><span class="acticon">'+ic+'</span><b>'+esc(a)+'</b> '+esc(vb)+
      (dt?' <span class="actdetail">'+esc(dt)+'</span>':'')+
      ' <span class="tdot"></span><span class="tdot"></span><span class="tdot"></span></div></div>';
  });
  box.innerHTML=rows.join('');   // rebuilt only on a real state change, so the fade plays once, not every poll
}

// === HUD glanceability strip (who's-doing-what, always visible) ===
var _lastHudSig = null, _hudCollapsed = false;
function elapsedHUD(ts){
  if(!ts) return '';
  try{ var s=Math.floor((Date.now()-new Date(ts).getTime())/1000); }
  catch(e){ return ''; }
  if(s<10) return 'just now'; if(s<60) return s+'s'; if(s<3600) return (s/60).toFixed(1)+'m'; return (s/3600).toFixed(1)+'h';
}
function hudPriority(st){   // active verbs first, then idle — so the HUD sorts "doing stuff" to the top
  var o={thinking:0,reading:0,writing:0,searching:0,running:0,recalling:0,inspecting:0,working:0,idle:1};
  return o[st]!==undefined ? o[st] : 2;
}
function renderHUD(acts){
  // Feature flag: hide entirely when disabled (default ON)
  if (localStorage.getItem(hudFlagKey()) === '0') {
    var s = document.getElementById('hud');
    if (s) s.classList.remove('show');
    return;
  }
  var strip=document.getElementById('hud'), toggle=document.getElementById('hud-toggle');
  if(!strip) return;
  acts=acts||{};
  // fingerprint: only rebuild DOM when activity state actually changed
  var sig=JSON.stringify(acts);
  if(sig===_lastHudSig) return;
  _lastHudSig=sig;
  var entries=Object.keys(acts).filter(function(a){return acts[a]&&acts[a].state;}).map(function(a){
    var st=acts[a].state||'working', dt=acts[a].detail||'', ts=acts[a].ts||'';
    return {agent:a, state:st, detail:dt, since:ts, elapsed:elapsedHUD(ts), stale:ts&&(Date.now()-new Date(ts).getTime())>300000};
  });
  entries.sort(function(x,y){ return hudPriority(x.state)-hudPriority(y.state) || x.agent.localeCompare(y.agent); });
  if(!entries.length){ strip.classList.remove('show'); toggle.classList.remove('show'); strip.innerHTML=''; return; }
  strip.classList.add('show'); toggle.classList.add('show');
  // diff against current DOM to minimize rebuilds — same pattern as the roster
  var curIds=new Set(entries.map(function(e){return e.agent;}));
  [].slice.call(strip.children).forEach(function(el){
    if(el.dataset.agent && !curIds.has(el.dataset.agent)){ el.style.opacity='0'; el.style.transform='translateX(-10px)'; setTimeout(function(){el.remove();},220); }
  });
  entries.forEach(function(e,i){
    var el=strip.querySelector('[data-agent="'+esc(e.agent)+'"]');
    if(!el){ el=document.createElement('div'); el.className='hrow'; el.dataset.agent=e.agent; el.title=e.agent+' — click to expand'; strip.appendChild(el); }
    el.className='hrow'+(e.stale?' stale':'');
    el.innerHTML='<span class="hicon">'+(ICON[e.state]||'⚡')+'</span>'+
      '<span class="hagent '+cls(e.agent)+'">'+esc(e.agent)+'</span>'+
      '<span class="hverb">'+(VERB[e.state]||e.state)+'</span>'+
      '<span class="hdetail">'+esc(e.detail)+'</span>'+
      '<span class="helapsed">'+e.elapsed+'</span>';
    // click: expand slide deck cards (mini teaching slides)
    el.onclick=function(ev){ ev.stopPropagation();
      var was=el.classList.contains('expanded');
      [].forEach.call(strip.querySelectorAll('.hrow.expanded'),function(r){r.classList.remove('expanded');});
      if(!was){ showDeck(e.agent); setTarget(e.agent); }
      else { hideDeck(); }
    };
  });
  // reorder children to match sorted entries
  entries.forEach(function(e,i){ var el=strip.querySelector('[data-agent="'+esc(e.agent)+'"]'); if(el) strip.appendChild(el); });
  toggle.textContent=_hudCollapsed?'⌄ expand':'⌃ collapse';
}
function toggleHUD(){ _hudCollapsed=!_hudCollapsed; document.getElementById('hud').classList.toggle('collapsed',_hudCollapsed);
  document.getElementById('hud-toggle').textContent=_hudCollapsed?'⌄ expand':'⌃ collapse'; }
// click-away closes expanded hud rows + deck
document.addEventListener('click',function(e){
  var deck=document.getElementById('deck');
  document.querySelectorAll('.hrow.expanded').forEach(function(r){r.classList.remove('expanded');});
  if(deck && deck.classList.contains('show') && !deck.contains(e.target) && !e.target.closest('.hrow')){
    hideDeck();
  }
});

// === slide deck cards (mini teaching slides — click a HUD row to expand) ===
var _traceBuffer = {};   // {agent: [{kind, text, ts}]} — last 20 traces per agent
var _deckAgent = null, _deckPage = 0, _deckPaused = false, _deckTimer = null;
function bufferTrace(from, kind, text){
  if(!from) return;
  var buf = _traceBuffer[from] = _traceBuffer[from] || [];
  buf.push({kind:kind, text:text, ts:new Date().toISOString()});
  if(buf.length > 20) buf.shift();   // keep last 20 traces
}
function buildDeckCards(agent){
  var buf = _traceBuffer[agent] || [];
  var act = null;   // current activity from the last /status poll
  try { act = JSON.parse(JSON.stringify((_lastHudSig ? JSON.parse(_lastHudSig) : {})[agent] || null)); } catch(e){}
  var cards = [];
  // Card 1: WHAT — current activity
  if(act && act.state){
    var st = act.state, dt = act.detail || '', ic = ICON[st] || '⚡', vb = VERB[st] || st;
    var elapsed = act.ts ? elapsedHUD(act.ts) : '';
    cards.push({
      icon: ic, title: vb.charAt(0).toUpperCase() + vb.slice(1),
      body: '<b>'+esc(agent)+'</b> is <b>'+esc(vb)+'</b>'+
        (dt?' <code>'+esc(dt)+'</code>':'')+
        (elapsed?'<br><span style="color:var(--faint);font-size:11px">'+elapsed+' elapsed</span>':''),
      result: null
    });
  }
  // Card 2: WHY — most recent thinking traces
  var thoughts = buf.filter(function(t){ return t.kind === 'thinking' || t.text.indexOf('💭')>=0; }).slice(-3);
  if(thoughts.length){
    var thoughtText = thoughts.map(function(t){ return t.text.replace(/^💭\s*/,''); }).join('<br><br>');
    cards.push({
      icon: '💭', title: 'Reasoning',
      body: '<span style="font-style:italic;color:var(--muted)">'+esc(thoughtText.slice(0,300))+'</span>',
      result: null
    });
  }
  // Card 3: RESULT — most recent tool traces
  var tools = buf.filter(function(t){ return t.kind === 'tool' || (t.text.indexOf('🔧')>=0 || t.text.indexOf('📖')>=0 || t.text.indexOf('✍️')>=0 || t.text.indexOf('⚙️')>=0); }).slice(-5);
  if(tools.length){
    var toolList = tools.map(function(t){ return '<span style="color:var(--faint);font-size:12px">'+esc(t.text.slice(0,120))+'</span>'; }).join('<br>');
    var resultClass = 'good';   // infer result: if last tool looks successful, mark good
    cards.push({
      icon: '✅', title: 'Recent Actions',
      body: toolList,
      result: {text: tools.length+' action'+(tools.length>1?'s':'')+' in the last few minutes', cls: resultClass}
    });
  }
  // Fallback: always at least one card
  if(!cards.length){
    cards.push({icon:'💤', title:'Idle', body:'<b>'+esc(agent)+'</b> is currently idle — no recent activity.', result:null});
  }
  return cards;
}
function showDeck(agent){
  _deckAgent = agent; _deckPage = 0; _deckPaused = false;
  renderDeck();
  document.getElementById('deck').classList.add('show');
  _startDeckTimer();
  // Highlight the HUD row
  document.querySelectorAll('.hrow.expanded').forEach(function(r){r.classList.remove('expanded');});
  var row = document.querySelector('.hrow[data-agent="'+esc(agent)+'"]');
  if(row) row.classList.add('expanded');
}
function hideDeck(){
  document.getElementById('deck').classList.remove('show');
  _deckAgent = null; _deckPage = 0;
  if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
}
function renderDeck(){
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  var container = document.getElementById('deckCards');
  var dots = document.getElementById('deckDots');
  if(!container) return;
  container.innerHTML = cards.map(function(c,i){
    var resultHtml = c.result ? '<div class="sc-result '+c.result.cls+'">'+c.result.text+'</div>' : '';
    return '<div class="slide-card"><div class="sc-head"><span class="sc-icon">'+c.icon+'</span><span class="sc-title">'+esc(c.title)+'</span></div><div class="sc-body">'+c.body+'</div>'+resultHtml+'</div>';
  }).join('');
  // dots
  dots.innerHTML = cards.map(function(_,i){
    return '<span class="slide-dot'+(i===_deckPage?' active':'')+'" onclick="deckGo('+i+')"></span>';
  }).join('');
  // position cards
  container.style.transform = 'translateX(-' + (_deckPage * 100) + '%)';
  // prev/next state
  var prevBtn = document.getElementById('deckPrev'), nextBtn = document.getElementById('deckNext');
  if(prevBtn) prevBtn.style.opacity = _deckPage === 0 ? '0.3' : '1';
  if(nextBtn) nextBtn.style.opacity = _deckPage >= cards.length-1 ? '0.3' : '1';
}
function deckGo(n){
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  if(n < 0 || n >= cards.length) return;
  _deckPage = n; renderDeck(); _startDeckTimer();
}
function deckNext(){ deckGo(_deckPage + 1); }
function deckPrev(){ deckGo(_deckPage - 1); }
function deckTogglePause(){
  _deckPaused = !_deckPaused;
  var btn = document.getElementById('deckPause');
  if(btn){ btn.textContent = _deckPaused ? '▶ play' : '⏸ pause'; btn.classList.toggle('paused', _deckPaused); }
  if(!_deckPaused) _startDeckTimer(); else if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
}
function _startDeckTimer(){
  if(_deckTimer){ clearTimeout(_deckTimer); _deckTimer = null; }
  if(_deckPaused) return;
  var cards = _deckAgent ? buildDeckCards(_deckAgent) : [];
  if(_deckPage < cards.length-1){
    _deckTimer = setTimeout(function(){ deckNext(); }, 4500);
  }
}
// Intercept trace messages to build the buffer — called from addMsg
function _captureTrace(msg){
  var from = msg.from || '';
  if(!from || from==='system' || from==='user') return;
  bufferTrace(from, msg.kind||'trace', msg.content||'');
}
// Hook into addMsg to capture traces
var _origAddMsg = addMsg;
addMsg = function(m){
  if((m.kind||'chat')==='trace') _captureTrace(m);
  return _origAddMsg(m);
};

// --- SSE ---
function connect(){
  var _currentRoom = 'bifrost', _es = null;

function switchRoom(ns) {
  if (!ns || ns === _currentRoom) return;
  // close the old SSE
  if (_es) { _es.close(); _es = null; }
  // clear the feed and seen set for the new room
  var logEl = document.getElementById('log');
  if (logEl) logEl.innerHTML = '';
  seen.clear();
  allMsgs.length = 0;
  _bkCount = 0; _bkLast = '';
  var bkEl = document.getElementById('bkFooter'); if (bkEl) bkEl.remove();
  // flush any pending trace run
  _flushTraceRun();
  _currentRoom = ns;
  // update the header room indicator
  _renderRoomIndicator();
  // reconnect SSE
  _connectSSE();
  // tell rail.js to re-highlight (it polls)
  toast('Switched to room: ' + ns);
}

function _connectSSE() {
  if (_es) { _es.close(); }
  _es = new EventSource('/events?ns=' + encodeURIComponent(_currentRoom));
  _es.onmessage = function(e) {
    try { var m = JSON.parse(e.data); addMsg(m); } catch(err) {}
  };
  _es.onerror = function() {
    // EventSource auto-reconnects; the feed will be empty until it does
    setTimeout(function() {
      if (_es && _es.readyState === EventSource.CLOSED) _connectSSE();
    }, 3000);
  };
}

function _renderRoomIndicator() {
  var el = document.getElementById('roomInd');
  if (!el) {
    el = document.createElement('span');
    el.id = 'roomInd';
    el.style.cssText = 'font-size:12px;font-weight:600;color:var(--accent);padding:4px 10px;'+
      'background:rgba(122,162,247,.10);border:1px solid rgba(122,162,247,.25);border-radius:8px;';
    var brand = document.querySelector('.brand');
    if (brand) brand.appendChild(el);
  }
  el.textContent = _currentRoom === 'bifrost' ? '' : '📡 ' + _currentRoom;
  el.style.display = _currentRoom === 'bifrost' ? 'none' : '';
}

const es = new EventSource('/events');
  es.onmessage = e=>{ try{ addMsg(JSON.parse(e.data)); }catch(err){} };
  es.onerror = ()=>{ /* browser auto-reconnects */ };
}
connect();
setFidelity('inform');                           // default fidelity + light the ladder (renderRecipient runs after _recips is defined, below)
document.addEventListener('click', function(e){  // click-away closes the roster popover
  var p=document.getElementById('rosterPop'), r=document.getElementById('recipient');
  if(p && p.classList.contains('show') && !p.contains(e.target) && r && !r.contains(e.target)) p.classList.remove('show');
});

// --- send ---
const input = document.getElementById('input');
input.addEventListener('input', ()=>{ input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,160)+'px'; });
input.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); } });
const FIDLABEL = {chat:'💬 sent', inform:'🟢 informed', steer:'🔵 steered (folds into current task)', interrupt:'🔴 interrupted (drop & switch)'};
function fidChanged(){
  var f = document.getElementById('fidelity'); if(!f) return;
  [].forEach.call(document.querySelectorAll('#ladder .seg'), function(b){ b.classList.toggle('on', b.dataset.fid===f.value); });
}
function setFidelity(v){ var f=document.getElementById('fidelity'); if(f) f.value=v; fidChanged(); }
async function send(){
  const text = input.value.trim(); if(!text) return;
  const fidelity = (document.getElementById('fidelity')||{}).value || 'inform';
  var isAll = _recips.length===1 && _recips[0]==='all';
  var ids = _recipIds();
  if((fidelity==='steer'||fidelity==='interrupt') && (isAll || ids.length!==1)){
    toast('pick ONE agent for '+fidelity+' (it targets a single peer)'); return;
  }
  input.value=''; input.style.height='auto';
  var targets = isAll ? ['all'] : ids;
  try{
    var ok=true, launched=[], msg='';
    for(var i=0;i<targets.length;i++){
      var to=targets[i];
      var r = await fetch('/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text, to:to, fidelity:fidelity})});
      var j = await r.json();
      if(!(j&&j.ok)) ok=false;
      if(j.launched) launched=launched.concat(j.launched);
      if(j.msg) msg=j.msg;  // server-side feedback (e.g. "auto-launched deepseek")
    }
    var label = FIDLABEL[fidelity]||'sent';
    if(launched.length) label += ' 🚀 auto-launched '+launched.join(', ');
    if(msg && fidelity==='steer') label += ' — '+msg;
    toast((ok?label:'send failed — bus offline?')+' → '+(isAll?'all':ids.join(', ')));
  }catch(e){ toast('send failed — bus offline?'); }
  // Smart negotiation: coordinate only when a collision is actually possible, speak only
  // when it finds one. A round fires only if >=2 agents are online (one agent can't collide),
  // and the verdict is surfaced only when it's amber/red (a real scope conflict). Green rounds
  // close silently -- coordination is a background safety net, not a per-message nag.
  // (inform/chat only; steer/interrupt/halt are already explicit, targeted acts.)
  if((fidelity === 'inform' || fidelity === 'chat') && _onlineAgents.length >= 2){
    fetch('/negotiate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text})}).then(r => r.json()).then(v => {
      if(v && v.verdict && v.verdict !== 'green'){
        const emoji = {amber:'⚠️', red:'🛑'};
        toast((emoji[v.verdict]||'') + ' Round: ' + v.verdict + ' — ' + (v.reason||''));
      }
    }).catch(()=>{});
  }
}

// --- Slice 2: animated recipient selector (state = who you're messaging; last-messaged persists) ---
var _recips = ['all'];                          // ['all'] (broadcast) or a list of agent ids
var _onlineAgents = [];                         // bus agents currently online (excludes 'user'); gates the smart negotiation round
function _aiRoster(){                            // AI agents in the hidden target select (excludes 'all')
  var t=document.getElementById('target'); if(!t) return [];
  return [].map.call(t.options,function(o){return o.value;}).filter(function(v){return v!=='all';});
}
function avatarInfo(a){
  var m={claude:['#f0a56c','#e0724f','C'], deepseek:['#7aa2f7','#9d7cf7','D'], user:['#48e6bf','#2fbf8f','U']};
  if(m[a]) return {a:m[a][0], b:m[a][1], l:m[a][2]};
  var h=0; for(var i=0;i<a.length;i++){ h=(h*31+a.charCodeAt(i))%360; }   // dynamic agents -> stable hue
  return {a:'hsl('+h+' 68% 62%)', b:'hsl('+((h+38)%360)+' 62% 52%)', l:(a[0]||'?').toUpperCase()};
}
function _cav(a){
  var v=avatarInfo(a), el=document.createElement('div');
  el.className='cav'; el.dataset.id=a; el.textContent=v.l; el.title=a;
  el.style.background='linear-gradient(140deg,'+v.a+','+v.b+')'; return el;
}
// reusable FLIP group animator: reconcile container's children to `ids`, animating enter/exit/reorder
function animateGroup(container, ids, makeEl){
  if(!container) return;
  var reduce=matchMedia('(prefers-reduced-motion:reduce)').matches;
  // reconcile FIRST, synchronously: drop any child not in `ids`. Correctness over a fade-out --
  // async removal races applyStatus's periodic re-render and leaves ghosts/duplicates.
  [].slice.call(container.children).forEach(function(el){ if(ids.indexOf(el.dataset.id)<0) el.remove(); });
  var live={}, old={};
  [].forEach.call(container.children,function(el){ live[el.dataset.id]=el; old[el.dataset.id]=el.getBoundingClientRect(); });
  // enters + reorder
  ids.forEach(function(id){
    var el=live[id];
    if(!el){ el=makeEl(id); container.appendChild(el);
      if(!reduce) el.animate([{opacity:0,transform:'scale(.4)'},{opacity:1,transform:'scale(1)'}],{duration:280,easing:'cubic-bezier(.2,.9,.3,1.35)'});
    } else { container.appendChild(el); }
  });
  // FLIP the survivors from their old x to the new x
  if(!reduce) ids.forEach(function(id){
    var el=live[id], o=old[id]; if(!el||!o) return;
    var dx=o.left-el.getBoundingClientRect().left;
    if(dx) el.animate([{transform:'translateX('+dx+'px)'},{transform:'translateX(0)'}],{duration:300,easing:'cubic-bezier(.2,.9,.3,1.2)'});
  });
}
function _recipIds(){ return (_recips.length===1 && _recips[0]==='all') ? _aiRoster() : _recips.slice(); }
function renderRecipient(){
  var stack=document.getElementById('rstack'), label=document.getElementById('rlabel'), box=document.getElementById('recipient');
  if(!stack) return;
  var isAll=_recips.length===1 && _recips[0]==='all';
  var ids=_recipIds(); if(!ids.length) ids=_aiRoster();
  animateGroup(stack, ids.slice(0,4), _cav);
  label.innerHTML = isAll ? '<b>Broadcast</b><span class="cue"> · '+ids.length+' agent'+(ids.length===1?'':'s')+'</span>'
                  : ids.length===1 ? '<b>'+esc(ids[0])+'</b><span class="cue"> · last messaged</span>'
                  : '<b>'+ids.length+' agents</b><span class="cue"> · multi-cast</span>';
  if(box){ box.classList.remove('pulse'); void box.offsetWidth; box.classList.add('pulse'); }
  var t=document.getElementById('target'); if(t){ t.value = isAll ? 'all' : (_recips.length===1 ? _recips[0] : 'all'); }
  renderRosterPop();
}
function setRecipients(list){ _recips = (list && list.length) ? list : ['all']; renderRecipient(); }
function toggleRecipient(a){
  if(a==='all'){ setRecipients(['all']); return; }
  var s=new Set(_recips.filter(function(x){return x!=='all';}));
  if(s.has(a)) s.delete(a); else s.add(a);
  setRecipients(Array.from(s));
}
function toggleRoster(){ var p=document.getElementById('rosterPop'); if(p){ renderRosterPop(); p.classList.toggle('show'); } }
function renderRosterPop(){
  var p=document.getElementById('rosterPop'); if(!p) return;
  var ids=_aiRoster(), isAll=_recips.length===1 && _recips[0]==='all';
  var rows='<div class="ri'+(isAll?' sel':'')+'" onclick="toggleRecipient(\'all\')"><div class="cav" style="background:linear-gradient(140deg,#7aa2f7,#48e6bf)">*</div>All agents<span class="chk">✓</span></div>';
  rows+=ids.map(function(a){ var v=avatarInfo(a), sel=!isAll && _recips.indexOf(a)>=0;
    return '<div class="ri'+(sel?' sel':'')+'" onclick="toggleRecipient(\''+esc(a)+'\')"><div class="cav" style="background:linear-gradient(140deg,'+v.a+','+v.b+')">'+v.l+'</div>'+esc(a)+'<span class="chk">✓</span></div>';
  }).join('');
  p.innerHTML=rows;
}
renderRecipient();                                // first paint (now that _recips + helpers are defined)

// --- pill click -> set composer target ---
function setTarget(aid){
  var tsel=document.getElementById('target');
  if(tsel && ![].some.call(tsel.options,function(o){return o.value===aid;})){
    var opt=document.createElement('option'); opt.value=aid; opt.textContent=aid; tsel.appendChild(opt);
  }
  setRecipients([aid]);                          // pill click -> single recipient (animated)
  if(typeof updateAshChroma==='function') updateAshChroma();
}

// --- reload (after an agent edits the UI source) ---
async function reloadUI(){
  try{ await fetch('/reload',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    toast('↻ reloading UI server…'); setTimeout(()=>location.reload(), 1600);
  }catch(e){ toast('reload failed'); }
}
// --- pause ---
async function togglePause(){
  const url = paused ? '/resume' : '/pause';
  try{ const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}); applyStatus(await r.json()); }
  catch(e){ toast('control failed — bus offline?'); }
}
var _lastRosterSig = '';   // fingerprint cache: only rebuild DOM when agent state actually changed

function applyStatus(s){
  paused = !!s.paused;
  const b=document.getElementById('pauseBtn'), banner=document.getElementById('banner');
  b.textContent = paused ? '▶ Resume' : '⏸ Pause';
  b.classList.toggle('paused', paused);
  banner.classList.toggle('show', paused);
  // show WHO paused and WHY (the pause_status carries {by, reason, ts})
  var ps = s.pause || {};
  banner.innerHTML = paused
    ? '⏸ Paused' + (ps.by ? ' by <b>'+esc(ps.by)+'</b>' : '') + (ps.reason ? ' — '+esc(ps.reason) : '') + ' · the agents are frozen. Type below to interject, then Resume.'
    : '⏸ Paused — the agents are frozen. Type below to interject, then Resume.';
  // dynamic roster: UNION of ACL-registered + currently-online agents.
  const agents=(s.agents||[]).map(a=>a.agent).filter(Boolean);
  _onlineAgents = agents.slice();               // stash for send()'s smart-negotiation gate
  const known=s.known||[];
  const roster=[...new Set([...known, ...agents, 'user'])];
  const sig=s.signals||{};
  const onlineSet=new Set(agents);
  const isKnown=new Set(known);

  // Build fingerprint: roster order + each agent's online/steer/nudge state.
  // Only rebuild DOM when this actually changed (was doing innerHTML on every 1.2s poll).
  var newSig = roster.join(',') + '|' + roster.map(function(a){
    var g=sig[a]||{};
    return a+':'+(onlineSet.has(a)||a==='user'?'1':'0')+':'+(g.steer_pending||0)+':'+(g.nudged?'1':'0');
  }).join(';');

  if(newSig !== _lastRosterSig){
    _lastRosterSig = newSig;
    const pills=document.getElementById('pills');
    pills.innerHTML = roster.map(a=>{
      const g=sig[a]||{};
      const isOnline=onlineSet.has(a)||a==='user';
      const unknown=!isKnown.has(a) && a!=='user';
      const hd=(s.halted||{})[a];   // {by, reason, ts} when this agent is under a targeted halt
      const halt = hd?'<span title="'+esc(hd.reason||'no reason given')+(hd.ts?'  ('+esc(hd.ts)+')':'')+'" style="color:var(--danger);font-size:10.5px;font-weight:600;margin-left:5px">⏸ halted by '+esc(hd.by||'?')+'</span>':'';
      const marks=halt
                +(g.steer_pending?'<span class="sig steer" title="steer facts queued">↝'+g.steer_pending+'</span>':'')
                +(g.nudged?'<span class="sig nudge" title="interrupt pending">⚡</span>':'')
                +(unknown?' <span title="online but not ACL-registered — security onboarding cue" style="color:var(--amber);font-size:11px">⚠ unknown</span>':'');
      return '<div class="pill'+(isOnline?' on':' off')+'" onclick="setTarget(\''+esc(a)+'\')" title="click to message '+esc(a)+(unknown?' (unregistered)':'')+'"><span class="dot"></span>'+esc(a)+(isOnline?'':' 💤')+marks+'</div>';
    }).join('');
  }
  // keep the recipient dropdown in sync with union of ACL-registered + online agents
  const tsel=document.getElementById('target');
  if(tsel){
    const targets=roster.filter(a=>a!=='user');
    const sigStr='all|'+targets.join('|');
    if(tsel.dataset.sig!==sigStr){
      const cur=tsel.value||'all';
      tsel.innerHTML='<option value="all">All</option>'+targets.map(a=>{
        const label=esc(a)+(isKnown.has(a)?'':' ⚠');
        return '<option value="'+esc(a)+'">'+label+'</option>';
      }).join('');
      tsel.value=[...tsel.options].some(o=>o.value===cur)?cur:'all';
      tsel.dataset.sig=sigStr;
    }
  }
  renderActivity(s.activities||{});
  // The voice line needs the runner flag from STATUS and the token counter from VITALS, which
  // arrive through two different render functions. Cache the half that lands here rather than
  // threading a second argument through a call chain that does not otherwise need it.
  _lastSignals = s.signals || {};
  driveAvatars(s.activities||{}, s);
  renderHUD(s.activities||{});
  syncAuroraState(paused, Object.keys(s.halted||{}).length);
  refreshNarrButtons(s.narration || 'key');
  updateFleetPulse(s);
  // renderRecipient() removed from poll loop — the recipient chip only changes on explicit user action
  // (roster click / setTarget). Calling it every 1.2s was doing getBoundingClientRect() layout thrash.
}
async function poll(){ try{ applyStatus(await (await fetch('/status')).json()); }catch(e){} }

// ===== T079-E4 ENGINE ROOM: gauge cluster via /vitals (2s poll) =====
var _lastVitalsSig = '';
function renderVitals(vitals){
  vitals = vitals || {};
  // BEFORE both early returns below, deliberately. renderVitals bails on an unchanged signature
  // and again on a missing #engine-room -- and "unchanged" is precisely the case where emission
  // has gone quiet, which is a reading the voice line must still receive. Hooking in after
  // either guard would freeze the waveform at its last value the moment it mattered most, and
  // a stalled needle is worse than no needle: it reports activity that has stopped.
  try{ driveVoiceLine(vitals); }catch(e){}
  var fenceData = vitals['_fence'] || {};
  var sig = JSON.stringify(vitals);
  if(sig === _lastVitalsSig) return;
  _lastVitalsSig = sig;
  var el = document.getElementById('engine-room');
  if(!el) return;
  var agents = Object.keys(vitals).filter(function(a){return a!=='_fence';}).sort();
  if(!agents.length){ el.innerHTML = ''; return; }
  var allQuiet = true;
  var html = agents.map(function(a){
    var v = vitals[a] || {};
    var hb = v.heartbeat || 'offline';
    var hbCls = {active:'active',idle:'idle',offline:'offline'}[hb] || 'offline';
    if(hb!=='active') allQuiet = false;
    // heartbeat ring
    var hbHtml = '<div class="er-hb '+hbCls+'" title="'+esc(a)+' heartbeat: '+hb+'"></div>';
    // breaker light (runner from runtimes)
    var rt = v.runtimes || {};
    var runner = rt.runner || '';
    var blCls = runner==='blocked'||runner==='tripped' ? 'tripped' : (runner==='down'?'warn':'good');
    if(runner==='blocked'||runner==='tripped') allQuiet = false;
    var blHtml = '<div class="er-blink '+blCls+'" title="runner: '+(runner||'n/a')+'"></div>';
    // flow schematic (lane depths as mini bars)
    var lanes = v.lanes || {};
    var workN = lanes.work||0, legacyN = lanes.legacy||0, traceN = lanes.trace||0;
    var flowMax = Math.max(1, workN, legacyN, traceN);
    var flowH = function(n){ return Math.max(2, Math.round((n/flowMax)*14)); };
    var flowCls = function(n){ return n>100?'high':(n>10?'mid':'low'); };
    if(workN>10||legacyN>10) allQuiet = false;
    var flowHtml = '<div class="er-flow" title="lanes: work='+workN+' legacy='+legacyN+' trace='+traceN+'">'+
      '<div class="'+flowCls(workN)+'" style="height:'+flowH(workN)+'px"></div>'+
      '<div class="'+flowCls(legacyN)+'" style="height:'+flowH(legacyN)+'px"></div>'+
      '<div class="'+flowCls(traceN)+'" style="height:'+flowH(traceN)+'px"></div></div>';
    // token bar
    var tok = v.tokens || {};
    var tokTotal = (tok.prompt||0)+(tok.completion||0);
    var tokPct = tokTotal>100000 ? 100 : Math.min(100,Math.round(tokTotal/1000));
    var tokCls = tokPct>80?'high':(tokPct>50?'mid':'low');
    var tokHtml = '<div class="er-tokbar" title="'+tokTotal+' tokens today"><div class="fill '+tokCls+'" style="width:'+(Math.max(2,tokPct))+'%"></div></div>';
    // pages indicator
    var pages = v.pages||0;
    if(pages>0) allQuiet = false;
    var pageHtml = pages ? '<span style="color:var(--amber);font-weight:700" title="'+pages+' unread page(s)">⚡'+pages+'</span>' : '';
    // daemon indicator
    var dmon = v.daemon_live ? '🟢' : '';
    return '<div class="er-gauge" data-agent="'+esc(a)+'" title="'+esc(a)+'">'+
      '<span class="er-label">'+esc(a)+'</span>'+hbHtml+blHtml+flowHtml+tokHtml+dmon+pageHtml+'</div>';
  }).join('');
  // fence-phase indicator (after the agent gauges)
  var fenceKeys = Object.keys(fenceData).sort();
  for(var fi=0; fi<fenceKeys.length; fi++){
    var f = fenceData[fenceKeys[fi]] || {};
    var phase = f.phase || 'idle';
    if(phase!=='reconciled' && phase!=='idle') allQuiet = false;
    var phaseCls = {reconciled:'green',reconciling:'amber',blind:'amber',idle:'off'}[phase]||'off';
    var phaseEmoji = {reconciled:'✅',reconciling:'🤝',blind:'👁',idle:''}[phase]||'';
    html += '<div class="er-gauge" title="fence: '+esc(fenceKeys[fi])+' — '+phase+'">'+
      '<span class="er-label">'+esc(fenceKeys[fi])+'</span>'+
      '<span class="er-val '+phaseCls+'">'+phaseEmoji+' '+phase+'</span></div>';
  }
  el.innerHTML = html;
  el.classList.toggle('quiet', allQuiet);
}
// ===== TRUTH/NOISE TIER: one poll scheduler replaces the scattered loops =====
// Sighted-audit receipt: 8x /status + 6x /vitals in 140ms — two parallel
// pollers (pollVitals 2s interval + pollDeferred 1.2s setTimeout chain) racing
// the same indicators → last-writer-wins flicker. The fix: ONE setInterval drives
// ONE fetch to /api/now, which merges status + vitals into one JSON blob.
// /status and /vitals still work (legacy) — the scheduler calls the unified door.
var _nowSig = '';          // signature: skip re-render on identical state
var _nowPollMs = 2000;     // base interval; state-gated (idle → 4s, unseated → 30s)
function applyNow(data){
  applyStatus((data||{}).status || {});
  var vitals = (data||{}).vitals || {};
  vitals['_fence'] = (data||{}).fence || {};
  renderVitals(vitals);
  // --- honest state vocabulary: per-seat-class words in the engine room ---
  var sc = (data||{}).seat_class || {};
  var dl = (data||{}).daemon_live || {};
  var el = document.getElementById('engine-room');
  if(el){
    var gauges = el.querySelectorAll('.er-gauge');
    for(var i=0;i<gauges.length;i++){
      var g = gauges[i];
      var aid = g.getAttribute('data-agent');
      if(!aid) continue;
      // Cache the base tooltip once (first poll tick) — per-tick mutations
      // must SET not APPEND so attributes never grow unboundedly (sighted-fence
      // red: " [unseated] [unseated] [unseated] ..." accumulation).
      if(!g.getAttribute('data-basetitle')){
        g.setAttribute('data-basetitle', g.getAttribute('title')||'');
      }
      var base = g.getAttribute('data-basetitle');
      var cls = sc[aid] || '';
      if(cls){
        g.classList.remove('sc-runner','sc-seat','sc-listening','sc-unseated');
        g.classList.add('sc-'+cls);
      }
      if(cls==='unseated'){
        g.style.opacity = '0.5';
        g.setAttribute('title', base+' [unseated]');
      } else {
        g.style.opacity = '';
        g.setAttribute('title', base);
      }
    }
  }
}
async function pollNow(){
  try{
    var resp = await fetch('/api/now');
    var data = await resp.json();
    applyNow(data);
  }catch(e){}
}
// Single scheduler: state-gated skip for idle/unseated, batch-capable
var _nowTick = 0;
function nowTick(){
  _nowTick++;
  // Skip unseated-heavy polls: full set every 15th tick (30s at 2s base)
  // Working seats always poll every tick (2s)
  pollNow();
  // Adjust next interval based on what we found
  setTimeout(nowTick, _nowPollMs);
}
// Start the scheduler — replaces BOTH pollVitals (2s setInterval) and
// pollDeferred (1.2s setTimeout chain)
async function pollVitals(){ try{ renderVitals(await (await fetch('/vitals')).json()); }catch(e){} }
// setInterval(pollVitals, 2000); pollVitals();  // RETIRED by nowTick
// function pollDeferred(){...}                   // RETIRED by nowTick
// function scheduleNextPoll(){...}               // RETIRED by nowTick
nowTick();   // single scheduler, replaces both legacy pollers
// Legacy poll() still fires for backward compat (old /status consumer) —
// but nowTick IS the primary path. Remove when all consumers migrate.
async function pollDeferred(){
  requestAnimationFrame(function(){
    poll().then(function(){
      setTimeout(pollDeferred, 1200);
    });
  });
}
setTimeout(pollDeferred, 1200);   // legacy: keep /status polling alive, deprioritized

// --- Fleet Pulse: at-a-glance system-health ring in the header ---
// green = all agents online + no halts + no lock contention
// amber = one or more agents offline, halted, or have pending steers/nudges — but system is running
// red   = system is paused, or an agent is in error/crash state
function updateFleetPulse(s){
  var fp=document.getElementById('fpulse'); if(!fp) return;
  var halted=Object.keys(s.halted||{}).length;
  var paused=!!s.paused;
  var signals=s.signals||{};
  var hasSteerOrNudge=false, hasError=false, hasOffline=false;
  var agents=(s.agents||[]).map(function(a){return a.agent;}).filter(Boolean);
  var known=s.known||[];
  var onlineSet=new Set(agents);
  // Check for offline known agents
  known.forEach(function(a){
    if(a!=='user' && !onlineSet.has(a)) hasOffline=true;
  });
  // Check signals for steer/nudge/error states
  Object.keys(signals).forEach(function(a){
    var g=signals[a]||{};
    if(g.steer_pending||g.nudged) hasSteerOrNudge=true;
    if(g.error||g.crashed||g.token_exhausted) hasError=true;
  });
  var cls, title;
  if(paused||hasError){
    cls='red'; title='fleet: '+(paused?'paused':'agent error')+' — attention needed';
  } else if(halted>0||hasOffline||hasSteerOrNudge){
    cls='amber'; title='fleet: '+
      (halted>0?halted+' halted ':'')+
      (hasOffline?'agent(s) offline ':'')+
      (hasSteerOrNudge?'pending signals':'')+
      ' — check';
  } else {
    cls='green'; title='fleet: all clear';
  }
  if(fp.className!==('fpulse '+cls)){ fp.className='fpulse '+cls; fp.title=title; }
}

// --- drag & drop + clipboard paste ---
const drop=document.getElementById('drop'); const dropZone=document.getElementById('dropZone');
const dropPreview=document.getElementById('dropPreview'); const dropFilenames=document.getElementById('dropFilenames');
let dragc=0, _dragFiles=[];
function showDropZone(files){
  dragc++; drop.classList.add('show');
  _dragFiles = files||[];
  // Show preview for images
  if(_dragFiles.length===1 && _dragFiles[0].type.startsWith('image/')){
    var r=new FileReader();
    r.onload=function(){ dropPreview.src=r.result; dropPreview.classList.add('show'); dropFilenames.textContent=_dragFiles[0].name; dropFilenames.classList.add('show'); };
    r.readAsDataURL(_dragFiles[0]);
  } else if(_dragFiles.length>0){
    dropPreview.classList.remove('show');
    dropFilenames.textContent=_dragFiles.map(function(f){return f.name;}).join(', ');
    dropFilenames.classList.add('show');
  }
  if(dropZone) dropZone.classList.add('over');
}
function hideDropZone(){
  dragc=Math.max(0,dragc-1);
  if(!dragc){
    drop.classList.remove('show'); dropPreview.classList.remove('show');
    dropFilenames.classList.remove('show'); _dragFiles=[];
    if(dropZone) dropZone.classList.remove('over');
  }
}
window.addEventListener('dragenter', function(e){ e.preventDefault(); showDropZone([...(e.dataTransfer.files||[])]); });
window.addEventListener('dragover', function(e){ e.preventDefault(); });
window.addEventListener('dragleave', function(e){ hideDropZone(); });
window.addEventListener('drop', async function(e){
  e.preventDefault(); var files=[...(e.dataTransfer.files||[])]; hideDropZone();
  for(var i=0;i<files.length;i++){ await upload(files[i]); }
});
// Clipboard paste: Ctrl+V / Cmd+V anywhere on the page.
// In the composer: if the clipboard has an image, upload it. If text-only, let the textarea handle it.
// Outside the composer: always try to upload any file.
window.addEventListener('paste', function(e){
  var items = (e.clipboardData||{}).items;
  if(!items) return;
  var inComposer = e.target.tagName==='TEXTAREA' || e.target.tagName==='INPUT';
  // Check if clipboard has any files (images, etc.)
  var hasFile=false;
  for(var i=0;i<items.length;i++){
    if(items[i].kind==='file'){ hasFile=true; break; }
  }
  if(!hasFile) return;   // text-only paste — let the textarea/input handle it normally
  // File paste: upload all files, suppress default (prevents image navigating the page)
  e.preventDefault();
  for(var i=0;i<items.length;i++){
    var item=items[i];
    if(item.kind==='file'){
      var f=item.getAsFile();
      if(f) upload(f);
    }
  }
});
function upload(file){
  return new Promise(function(res){
    var r=new FileReader();
    r.onload=async function(){
      try{
        var resp=await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({name:file.name, content_b64:r.result})});
        var j=await resp.json();
        if(j.ok){
          // Render an inline file card in the message log
          renderFileCard({
            name: file.name,
            path: j.path,
            bytes: j.bytes,
            type: file.type,
            thumb: file.type.startsWith('image/') ? r.result : null
          });
          toast('📎 shared '+file.name+' → dropbox/');
        } else {
          toast('upload failed: '+(j.error||'?'));
        }
      }catch(e){ toast('upload failed'); }
      res();
    };
    r.readAsDataURL(file);
  });
}
// Render an inline file card in the message log (like a chat bubble for files)
function renderFileCard(info){
  var isImage = (info.type||'').startsWith('image/');
  var icon=fileIcon(info.type||'', info.name||'');
  var size=formatBytes(info.bytes||0);
  var card=document.createElement('div');
  card.className='filecard'+(isImage?' filecard-img':'');
  if(isImage && info.thumb){
    // Image card: show the image as a large thumbnail with a small caption bar
    card.innerHTML=
      '<img class="fc-img" src="'+esc(info.thumb)+'" loading="lazy" onclick="this.classList.toggle(\'expanded\')" title="click to expand/collapse">'+
      '<div class="fc-cap"><div class="fc-icon">'+icon+'</div>'+
      '<div class="fc-info"><div class="fc-name">'+esc(info.name||'screenshot')+'</div>'+
      '<div class="fc-meta">'+size+' · dropbox/</div></div></div>';
  } else {
    var thumbHtml=info.thumb?'<img class="fc-thumb" src="'+esc(info.thumb)+'" loading="lazy">':'<div class="fc-thumb hidden"></div>';
    card.innerHTML=thumbHtml+
      '<div class="fc-icon">'+icon+'</div>'+
      '<div class="fc-info"><div class="fc-name">'+esc(info.name||'file')+'</div><div class="fc-meta">'+size+' · dropbox/</div></div>';
  }
  card.title='dropbox/'+(info.name||'file')+' — ' + size;
  card.onclick=function(e){
    if(e.target.tagName==='IMG' && e.target.classList.contains('fc-img')) return; // let the click toggle expand
    toast('📂 dropbox/'+(info.name||'file'));
  };
  log.appendChild(card);
  autoscroll();
  // Also send as a regular user message so it appears like a chat bubble
  allMsgs.push({kind:'chat',from:'user',content:'📎 shared **'+esc(info.name||'file')+'** ('+size+') → `dropbox/`',ts:new Date().toISOString()});
}
function fileIcon(type, name){
  if(type.startsWith('image/')) return '🖼️';
  if(type.startsWith('video/')) return '🎬';
  if(type.startsWith('audio/')) return '🎵';
  if(type.includes('pdf')) return '📄';
  if(type.includes('zip')||type.includes('tar')||type.includes('gzip')) return '📦';
  var ext=(name||'').split('.').pop().toLowerCase();
  var map={py:'🐍', js:'📜', ts:'📘', json:'📋', md:'📝', html:'🌐', css:'🎨', sql:'🗄️', sh:'⚡', yaml:'⚙️', yml:'⚙️', toml:'⚙️', txt:'📃', csv:'📊', log:'📋', key:'🔑', pem:'🔐', png:'🖼️', jpg:'🖼️', jpeg:'🖼️', gif:'🖼️', svg:'🖼️', webp:'🖼️', mp4:'🎬', mov:'🎬', mp3:'🎵', wav:'🎵', pdf:'📄', zip:'📦', gz:'📦', tar:'📦'};
  return map[ext]||'📎';
}
function formatBytes(b){
  if(b<1024) return b+' B';
  if(b<1048576) return (b/1024).toFixed(1)+' KB';
  return (b/1048576).toFixed(1)+' MB';
}
function toast(msg){
  var t=document.createElement('div'); t.className='toast'; t.textContent=msg;
  document.getElementById('toast').appendChild(t);
  setTimeout(function(){ t.style.opacity='0'; setTimeout(function(){t.remove();},300); }, 3200);
}

// --- launcher panel ---
let lnchrOpen=false, lnchrData=[];
function toggleLauncher(){
  lnchrOpen=!lnchrOpen;
  document.getElementById('lnchr').classList.toggle('show', lnchrOpen);
  document.getElementById('lnchrBtn').classList.toggle('active', lnchrOpen);
  if(lnchrOpen) refreshLauncher();
}
function exitClass(r){ return r||'never_launched'; }
function exitLabel(r){
  const map={clean:'clean exit',token_exhausted:'⚠ token exhausted',error:'✗ error',killed:'killed',
    auth_error:'🔑 auth error', never_launched:'not launched', running:'running', exited:'exited'};
  return map[r]||r||'unknown';
}
async function refreshLauncher(){
  try{
    const r=await (await fetch('/launcher/status')).json();
    lnchrData=r||[];
    const box=document.getElementById('lnchrRows');
    box.innerHTML=lnchrData.map(a=>{
      const cls=exitClass(a.status==='running'?'running':a.exit_reason);
      const lbl=exitLabel(a.status==='running'?'running':a.exit_reason);
      const reason=a.exit_reason&&a.status!=='running'?
        '<span class="lreason">'+lbl+(a.exit_code!=null?' (code '+a.exit_code+')':'')+'</span>':'';
      const running=a.status==='running';
      const pidInfo=running?' <span style="color:var(--faint);font-size:11px">pid '+a.pid+'</span>':'';
      return '<div class="lrow">'+
        '<span class="ltag">'+esc(a.tag)+pidInfo+'</span>'+
        '<span class="ldesc">'+esc(a.description||'')+'</span>'+
        '<span class="lst '+cls+'">'+lbl+'</span>'+reason+lvBadge(a)+
        '<span class="lact">'+
          '<button class="lgo" onclick="launchAgent(\''+esc(a.tag)+'\')" '+(running||!a.enabled?'disabled':'')+'>'+
            (running?'running':'▶ Launch')+'</button>'+
          '<button class="lrevive" onclick="reviveAgent(\''+esc(a.tag)+'\')" '+(!running?'disabled':'')+' title="kill + relaunch — recovers a wedged runner">↻ Revive</button>'+
          '<button class="lkill" onclick="killAgent(\''+esc(a.tag)+'\')" '+(!running?'disabled':'')+'>'+
            '✕ Kill</button>'+
          '<button class="lauto'+(a.auto_revive?' on':'')+'" onclick="armRevive(\''+esc(a.tag)+'\','+(!a.auto_revive)+')" '+
            'title="auto-revive this agent if it wedges (opt-in, off by default)">⟳ auto</button>'+
        '</span></div>';
    }).join('')||'<div style="color:var(--faint);text-align:center;padding:12px">no agents registered — add entries to security/launcher.json</div>';
  }catch(e){}
}
async function launchAgent(tag){
  const row=lnchrData.find(a=>a.tag===tag);
  if(!row) return;
  toast('🚀 launching '+tag+'…');
  try{
    const r=await fetch('/launcher/launch',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag})});
    const j=await r.json();
    if(j&&j.ok) toast('✅ '+tag+' started (pid '+j.pid+')');
    else toast('❌ '+(j?j.error:'failed to launch '+tag));
    refreshLauncher();
  }catch(e){ toast('launch failed — server offline?'); }
}
async function killAgent(tag){
  toast('⏹ killing '+tag+'…');
  try{
    const r=await fetch('/launcher/kill',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag})});
    const j=await r.json();
    if(j&&j.ok) toast('⏹ '+tag+' terminated');
    else toast('❌ '+(j?j.error:'failed to kill '+tag));
    refreshLauncher();
  }catch(e){ toast('kill failed'); }
}
// L3a badge: show an agent's live phase + time-in-phase; highlight a suspected wedge.
function lvBadge(a){
  const L=a.liveness;
  if(!L||a.status!=='running') return '';
  const s=Math.round(L.stuck_seconds||0);
  const idle=(L.phase==='idle'||L.phase==='online');
  const txt=idle?'idle':(esc(L.phase)+(L.detail?(' · '+esc(String(L.detail))):'')+' · '+s+'s');
  const cls=L.wedged?'lv-wedged':(idle?'lv-idle':'lv-busy');
  return '<span class="lv '+cls+'" title="turn '+(L.turn||0)+' · '+esc(L.phase)+' for '+s+'s'+
    (L.wedged?' — SUSPECTED WEDGE':'')+'">'+txt+'</span>';
}
// L3b-auto: arm/disarm opt-in auto-revive-on-wedge for this agent (default off).
async function armRevive(tag, on){
  try{
    const r=await fetch('/launcher/arm-revive',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag, on:on})});
    const j=await r.json();
    if(j&&j.ok) toast(on?('🛡 auto-revive armed — '+tag):('auto-revive off — '+tag));
    else toast('❌ '+(j?j.error:'failed'));
    refreshLauncher();
  }catch(e){ toast('arm toggle failed'); }
}
// L3b: kill + relaunch a wedged/dead runner (frees the singleton lock first, server-side).
async function reviveAgent(tag){
  toast('↻ reviving '+tag+'…');
  try{
    const r=await fetch('/launcher/revive',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({agent_id:tag})});
    const j=await r.json();
    if(j&&j.ok) toast('✅ '+tag+' revived (pid '+j.pid+')');
    else toast('❌ '+(j?j.error:'failed to revive '+tag));
    refreshLauncher();
  }catch(e){ toast('revive failed'); }
}
// poll launcher status when open
const LPOLL=setInterval(()=>{ if(lnchrOpen) refreshLauncher(); }, 5000);

// ==================================================================
//  V2 PRESENTATION REGISTRY  —  strangler alongside existing UI
//  Slots: theme | tile | message | viewmode
//  Each slot holds registered variants; getPref/setPref persist to
//  localStorage; mountAll() applies the active variant per slot.
//  Reference variants: aurora, glass-card, markdown, feed.
// ==================================================================
const SLOTS=['theme','tile','message','viewmode'];
const DEFAULTS={theme:'aurora',tile:'glass-card',message:'markdown',viewmode:'feed'};
const REGISTRY={theme:{},tile:{},message:{},viewmode:{}};
let _activeVariant={...DEFAULTS};
let _glassCardData={agents:[],known:[],signals:{},tasks:{},seat_class:{}};

function getPref(slot){ try{ return localStorage.getItem('bifrost_pref_'+slot)||DEFAULTS[slot]; }catch(e){ return DEFAULTS[slot]; } }
function setPref(slot,id){
  try{ localStorage.setItem('bifrost_pref_'+slot,id); }catch(e){}
  mountSlot(slot,id);
}
function mountSlot(slot,id){
  if(!REGISTRY[slot]||!REGISTRY[slot][id]) return;
  if(_activeVariant[slot]===id) return;
  var oldId=_activeVariant[slot];
  if(oldId&&REGISTRY[slot][oldId]&&REGISTRY[slot][oldId].unmount) REGISTRY[slot][oldId].unmount();
  _activeVariant[slot]=id;
  if(REGISTRY[slot][id].mount) REGISTRY[slot][id].mount();
  refreshSettingsPanel();
}
function mountAll(){
  SLOTS.forEach(function(s){
    var id=getPref(s);
    _activeVariant[s]='';
    mountSlot(s,id);
  });
}
function registerVariant(slot,id,label,desc,mount,unmount,config,applyCfg){
  if(!REGISTRY[slot]) REGISTRY[slot]={};
  REGISTRY[slot][id]={label:label||id,desc:desc||'',mount:mount||noop,unmount:unmount||noop,
    config:config||null, applyConfig:applyCfg||null};
}
// variant config read/write (per-slot+id key)
function getVariantCfg(slot,id){
  try{ return JSON.parse(localStorage.getItem('bifrost_cfg_'+slot+'_'+id)||'{}'); }catch(e){ return {}; }
}
function setVariantCfg(slot,id,cfg){
  try{ localStorage.setItem('bifrost_cfg_'+slot+'_'+id, JSON.stringify(cfg)); }catch(e){}
  var v=REGISTRY[slot]&&REGISTRY[slot][id];
  if(v&&v.applyConfig) v.applyConfig(cfg);
  if(_activeVariant[slot]===id) refreshSettingsPanel();
}

// --- reference variants (one per slot, drop-in ready) ---

// theme variants — inject/remove a <style id="bifrost-theme-v2"> to swap :root
var THEME_CSS = {
  aurora:'',
  ember:' :root{--bg:#0d0a07;--bg2:#14100c;--panel:#1a1510;--panel2:#1f1913;--border:#2d2418;--text:#f0e6d3;--muted:#a08c70;--faint:#6a5a43;--claude:#e0915c;--deepseek:#f0b246;--user:#5fd39b;--system:#8a7c6e;--accent:#f0b246;--accent2:#e8783a;--amber:#f5c542;--danger:#f0666e;--shadow:0 8px 30px rgba(0,0,0,.45);}',
  abyss:' :root{--bg:#050a0f;--bg2:#080f17;--panel:#0c1520;--panel2:#101a28;--border:#1a2a3a;--text:#d0e0f0;--muted:#7088a8;--faint:#4a6078;--claude:#5fd0d9;--deepseek:#48c0ff;--user:#5fd39b;--system:#6088a0;--accent:#48c0ff;--accent2:#3090e0;--amber:#a0c040;--danger:#f0666e;--shadow:0 8px 30px rgba(0,0,0,.55);}',
  frost:' :root{--bg:#f2f4f8;--bg2:#e8ecf2;--panel:#ffffff;--panel2:#f5f7fa;--border:#d8dde5;--text:#1a1e2e;--muted:#6b7280;--faint:#9ca3af;--claude:#d97746;--deepseek:#4f7cf7;--user:#2ea87a;--system:#7c8ba0;--accent:#4f7cf7;--accent2:#7c4ff7;--amber:#d4a017;--danger:#e04040;--shadow:0 4px 16px rgba(0,0,0,.08);}'
};
function _mountTheme(id){
  var el=document.getElementById('bifrost-theme-v2');
  if(!el){ el=document.createElement('style'); el.id='bifrost-theme-v2'; document.head.appendChild(el); }
  el.textContent=THEME_CSS[id]||'';
}
function _unmountTheme(){ var el=document.getElementById('bifrost-theme-v2'); if(el) el.textContent=''; }

registerVariant('theme','aurora','Aurora','dark cosmic (default)');
registerVariant('theme','ember','Ember','warm amber coals',function(){_mountTheme('ember');},_unmountTheme);
registerVariant('theme','abyss','Abyss','deep ocean trench',function(){_mountTheme('abyss');},_unmountTheme);
registerVariant('theme','frost','Frost','arctic clean light',function(){_mountTheme('frost');},_unmountTheme);

// tile='glass-card' — frosted card with role badge, state-glow, expand-to-roster
// actions channel: {onSelect, onSetTarget, onSetFidelity, onSpawn, onKill}
// config: {compact:true} collapses cards to icon-only (space-saver)
registerVariant('tile','glass-card','Glass Card','frosted card + state glow + expand actions',
  function mountGlassCard(){
    document.getElementById('pills').style.display='none';
    var t=document.getElementById('tiles'); t.classList.add('show');
    var cfg=getVariantCfg('tile','glass-card');
    t.classList.toggle('compact',!!cfg.compact);
    renderGlassCards();
  },
  function unmountGlassCard(){
    document.getElementById('pills').style.display='';
    document.getElementById('tiles').classList.remove('show','compact');
  },
  [{key:'compact',type:'bool',default:false,label:'Compact (icon-only)'}],
  function(cfg){ document.getElementById('tiles').classList.toggle('compact',!!cfg.compact); }
);

// tile='iso-cube' — CSS 3D isometric cube, one per agent. Face colors from agent class.
// animateExpand(el, agents, actions) renders cubes into the selector frame content.
registerVariant('tile','iso-cube','Iso Cube','CSS 3D isometric cube per agent',
  function mountIsoCube(){
    document.getElementById('pills').style.display='none';
    var t=document.getElementById('tiles'); t.classList.add('show');
    renderIsoCubes();
  },
  function unmountIsoCube(){
    document.getElementById('pills').style.display='';
    document.getElementById('tiles').classList.remove('show');
  },
  [{key:'labelOnTop',type:'bool',default:true,label:'Labels on top face'}],
  function(cfg){ /* no live re-render needed for label toggle on existing cubes */ }
);

// message='markdown' — current fmt() (code + backtick); no-op. Variant overrides
// _msgRenderer(msg) → returns HTML string; called by addMsg instead of fmt()
var _msgRenderer = function(msg){ return fmt(msg.content); };
registerVariant('message','markdown','Markdown','code-block + backtick formatter',
  function(){ _msgRenderer = function(msg){ return fmt(msg.content); }; },
  function(){ _msgRenderer = function(msg){ return fmt(msg.content); }; }
);

// viewmode='feed' — appends to #log. Variant overrides _msgPlacer(el, msg)
// to control where a message DOM element lands (split-view, threaded, etc.)
var _msgPlacer = function(el, msg){ log.appendChild(el); };
registerVariant('viewmode','feed','Feed','single chronological log',
  function(){ _msgPlacer = function(el, msg){ log.appendChild(el); }; },
  function(){ _msgPlacer = function(el, msg){ log.appendChild(el); }; }
);

// ---- glass-card renderer ----
function renderGlassCards(){
  var box=document.getElementById('tiles');
  var d=_glassCardData;
  var agents=d.agents||[];
  var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  box.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user';
    var g=sig[aid]||{};
    var nudged=g.nudged, steered=g.steer_pending;
    var unknown=!isKnown.has(aid) && aid!=='user';
    var cl='gcard';
    if(isOnline) cl+=' online';
    if(nudged) cl+=' nudged';
    if(steered) cl+=' steered';
    var roleHtml=(aid==='deepseek'||aid==='claude')?'<span class="gbadge admin">admin</span>':'';
    if(unknown) roleHtml+=' <span class="gbadge" style="color:var(--amber);background:rgba(240,178,70,.12);border-color:rgba(240,178,70,.25)">⚠ unknown</span>';
    var statusMark=isOnline?'':' \u{1f4a4}';
    var steerMark=steered?'<span class="sig steer" title="steer pending">\u21dd'+steered+'</span>':'';
    var nudgeMark=nudged?'<span class="sig nudge" title="nudge pending">\u26a1</span>':'';
    return '<div class="'+cl+'" onclick="toggleGCard(event,\''+esc(aid)+'\')">'+
      '<div class="gdot"></div>'+
      '<div style="flex:1;min-width:0"><div class="gname">'+esc(aid)+statusMark+'</div>'+roleHtml+'</div>'+
    // C-3 PLAN row — story-state spine (NOW-card pin N-P7)
    (function planRow(){
      var task=(d.tasks||{})[aid]||{}; var plan=task.plan||'';
      var marks={'done':'✓','in_progress':'●','pending':'○','blocked':'─'};
      if(!plan) return '';
      var items=plan.split(/[,;]/).map(function(s){return s.trim();}).filter(Boolean);
      var html=items.map(function(item,idx){
        var m='pending'; if(idx===0&&task.status==='in_progress') m='in_progress';
        if(task.done_items&&task.done_items.indexOf(item)>-1) m='done';
        return '<span class="gplan-mark '+({'done':'done','in_progress':'prog','pending':'pend','blocked':'blocked'}[m]||'pend')+'">'+marks[m]+' '+esc(item)+'</span>';
      }).join(' ');
      return '<div class="gplan">'+html+'</div>';
    })()+
      steerMark+nudgeMark+
      '<div class="gactions">'+
        '<button onclick="event.stopPropagation();setTarget(\''+esc(aid)+'\')">\u{1f3af} Select</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'chat\')">\u{1f4ac} Chat</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'steer\')">\u{1f535} Steer</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'interrupt\')">\u{1f534} Interrupt</button>'+
        '<button class="gact-spawn" onclick="event.stopPropagation();glassSpawn(\''+esc(aid)+'\')">\u25b6 Spawn</button>'+
        '<button class="gact-kill" onclick="event.stopPropagation();glassKill(\''+esc(aid)+'\')">\u2715 Kill</button>'+
      '</div></div>';
  }).join('');
}

// ---- iso-cube renderer ----
function renderIsoCubes(){
  var box=document.getElementById('tiles');
  var d=_glassCardData;
  var agents=d.agents||[]; var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  box.className='icube-row';
  box.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user';
    var g=sig[aid]||{}; var nudged=g.nudged, steered=g.steer_pending;
    var unknown=!isKnown.has(aid) && aid!=='user';
    var cl='icube'; if(isOnline) cl+=' online'; if(nudged) cl+=' nudged';
    var ca=cls(aid);
    return '<div class="'+cl+'" onclick="toggleICube(event,\''+esc(aid)+'\')">'+
      '<div class="icube-inner">'+
        '<div class="icube-face icube-top"><div class="iname">'+esc(aid)+'</div></div>'+
        '<div class="icube-face icube-front"><div class="iav '+ca+'">'+initials(aid)+'</div></div>'+
        '<div class="icube-face icube-right"></div>'+
      '</div>'+
      (unknown?'<span style="position:absolute;bottom:-2px;right:2px;font-size:9px;color:var(--amber)" title="online but not ACL-registered">⚠</span>':'')+
      (steered?'<span class="sig steer" style="position:absolute;top:-4px;right:-4px" title="steer pending">\u21dd</span>':'')+
      (nudged?'<span class="sig nudge" style="position:absolute;top:-4px;right:14px" title="interrupt pending">\u26a1</span>':'')+
      '<div class="igact">'+
        '<button onclick="event.stopPropagation();setTarget(\''+esc(aid)+'\')">\u{1f3af} Select</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'chat\')">\u{1f4ac} Chat</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'steer\')">\u{1f535} Steer</button>'+
        '<button onclick="event.stopPropagation();setTargetFidelity(\''+esc(aid)+'\',\'interrupt\')">\u{1f534} Interrupt</button>'+
        '<button class="ig-spawn" onclick="event.stopPropagation();glassSpawn(\''+esc(aid)+'\')">\u25b6 Spawn</button>'+
        '<button class="ig-kill" onclick="event.stopPropagation();glassKill(\''+esc(aid)+'\')">\u2715 Kill</button>'+
      '</div></div>';
  }).join('');
}
function toggleICube(e,aid){
  e.stopPropagation();
  var c=e.currentTarget; var was=c.classList.contains('expanded');
  document.querySelectorAll('.icube.expanded').forEach(function(el){el.classList.remove('expanded');});
  if(!was){ c.classList.add('expanded'); setTarget(aid); }
}
document.addEventListener('click',function(){ document.querySelectorAll('.icube.expanded').forEach(function(c){c.classList.remove('expanded');}); });

// ---- tile variant animateExpand (for selector frame) ----
function animateExpandTiles(el, agents, actions){
  var d=_glassCardData; var sig=d.signals||{};
  var isKnown=d.isKnown||new Set(d.known||[]);
  var roster=d.roster||[];
  var online=new Set(agents);
  var vt=REGISTRY['tile']&&REGISTRY['tile'][_activeVariant.tile];
  if(vt&&vt.animateExpand){ vt.animateExpand(el, roster, online, sig, actions, isKnown); return; }
  el.innerHTML=roster.map(function(aid){
    var unk=!isKnown.has(aid)&&aid!=='user'?' ⚠':'';
    return '<button style="font:inherit;font-size:12px;padding:4px 10px;border-radius:6px;cursor:pointer;border:1px solid var(--border);background:var(--panel);color:var(--text);white-space:nowrap" onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+
      (online.has(aid)||aid==='user'?'\u25cf ':'\u25cb ')+esc(aid)+unk+'</button>';
  }).join('');
}
REGISTRY['tile']['glass-card'].animateExpand=function(el,roster,online,sig,actions,isKnown){
  el.innerHTML=roster.map(function(aid){
    var g=sig[aid]||{}; var isOnline=online.has(aid)||aid==='user';
    var nudged=g.nudged, steered=g.steer_pending;
    var unk=!isKnown.has(aid)&&aid!=='user'?' ⚠':'';
    var span='<span style="font-size:12px;font-weight:650;color:var(--text)">'+esc(aid)+unk+(isOnline?'':' \u{1f4a4}')+'</span>';
    if(steered) span+='<span class="sig steer" style="font-size:9px">\u21dd'+steered+'</span>';
    if(nudged) span+='<span class="sig nudge" style="font-size:9px">\u26a1</span>';
    return '<button style="font:inherit;font-size:12px;padding:5px 10px;border-radius:8px;cursor:pointer;border:1px solid '+(isOnline?'rgba(95,211,155,.3)':'var(--border)')+';background:var(--panel);color:var(--text);display:flex;align-items:center;gap:6px"'+
      ' onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+span+'</button>';
  }).join('');
};
REGISTRY['tile']['iso-cube'].animateExpand=function(el,roster,online,sig,actions,isKnown){
  el.style.cssText='display:flex;gap:10px;flex-wrap:wrap;padding:4px 0';
  el.innerHTML=roster.map(function(aid){
    var isOnline=online.has(aid)||aid==='user'; var ca=cls(aid);
    var unk=!isKnown.has(aid)&&aid!=='user'?'<span style="position:absolute;bottom:0;right:2px;font-size:8px;color:var(--amber)">⚠</span>':'';
    return '<div style="width:46px;height:46px;perspective:300px;cursor:pointer;flex:none;position:relative" onclick="setTargetAndCloseAsh(\''+esc(aid)+'\')">'+
      '<div style="position:relative;width:100%;height:100%;transform:rotateX(-22deg)rotateY(-32deg);transform-style:preserve-3d">'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid '+(isOnline?'rgba(95,211,155,.35)':'var(--border)')+';border-radius:7px;background:rgba(20,22,29,.78);transform:translateZ(23px);display:grid;place-items:center">'+
          '<div class="iav '+ca+'" style="width:20px;height:20px;font-size:8px;border-radius:4px">'+initials(aid)+'</div></div>'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid var(--border);border-radius:7px;background:rgba(20,22,29,.7);transform:rotateX(90deg)translateZ(23px)"></div>'+
        '<div style="position:absolute;width:46px;height:46px;border:1.5px solid var(--border);border-radius:7px;background:rgba(16,18,24,.7);transform:rotateY(90deg)translateZ(23px)"></div>'+
      '</div>'+unk+'</div>';
  }).join('');
};

function toggleGCard(e,aid){
  e.stopPropagation();
  var card=e.currentTarget;
  var was=card.classList.contains('expanded');
  document.querySelectorAll('.gcard.expanded').forEach(function(c){c.classList.remove('expanded');});
  if(!was){ card.classList.add('expanded'); setTarget(aid); }
}
document.addEventListener('click',function(){ document.querySelectorAll('.gcard.expanded').forEach(function(c){c.classList.remove('expanded');}); });

// actions channel wiring
function setTargetFidelity(aid,fidelity){
  setTarget(aid);
  var fsel=document.getElementById('fidelity');
  if(fsel){ fsel.value=fidelity; fidChanged(); }
}
function glassSpawn(aid){
  var row=(lnchrData||[]).find(function(a){return a.agent_id===aid||a.tag===aid;});
  var tag=row?row.tag:aid;
  launchAgent(tag);
}
function glassKill(aid){
  var row=(lnchrData||[]).find(function(a){return a.agent_id===aid||a.tag===aid;});
  var tag=row?row.tag:aid;
  killAgent(tag);
}

// ---- wrap applyStatus to feed glass-card + iso-cube + selector frame data ----
(function(){
  var _orig=applyStatus;
  applyStatus=function(s){
    _orig(s);
    var agents=(s.agents||[]).map(function(a){return a.agent;}).filter(Boolean);
    var known=s.known||[];
    _glassCardData={
      agents:agents,
      known:known,
      roster:[...new Set([...known, ...agents, 'user'])],
      isKnown:new Set(known),
      signals:s.signals||{}
    };
    if(_activeVariant.tile==='glass-card') renderGlassCards();
    if(_activeVariant.tile==='iso-cube') renderIsoCubes();
    window._glassCardData=_glassCardData; window._lastActs=s.activities||{};   // cache for standalone tile variants
    if(_activeVariant.tile==='presence' && window.renderPresence) window.renderPresence(_glassCardData, window._lastActs);
    updateAshChroma();
  };
})();

// ---- selector frame (Razer square) ----
var _ashOpen=false, _ashTarget='';
function toggleAsh(){
  _ashOpen=!_ashOpen;
  var f=document.getElementById('ash-frame'); var c=document.getElementById('ash-content');
  var s=document.getElementById('ash-sep');
  f.classList.toggle('open',_ashOpen);
  c.classList.toggle('show',_ashOpen);
  s.style.display=_ashOpen?'block':'none';
  if(_ashOpen){
    var agents=_glassCardData.agents||[];
    animateExpandTiles(c, agents, {onSelect:setTargetAndCloseAsh});
  }
}
function setTargetAndCloseAsh(aid){
  _ashTarget=aid; setTarget(aid); updateAshChroma();
  _ashOpen=false;
  document.getElementById('ash-frame').classList.remove('open');
  document.getElementById('ash-content').classList.remove('show');
  document.getElementById('ash-sep').style.display='none';
}
function updateAshChroma(){
  var f=document.getElementById('ash-frame');
  var tsel=document.getElementById('target');
  var aid=(tsel&&tsel.value!=='all')?tsel.value:'';
  f.className=f.className.replace(/\s*chroma-\w+/g,'');
  if(aid==='claude') f.classList.add('chroma-claude');
  else if(aid==='deepseek') f.classList.add('chroma-deepseek');
  else if(aid) f.classList.add('chroma-user');
}

// ---- settings panel ----
var setpOpen=false;
function toggleSettings(){
  setpOpen=!setpOpen;
  document.getElementById('setp').classList.toggle('show',setpOpen);
  document.getElementById('gearBtn').classList.toggle('active',setpOpen);
  if(setpOpen) refreshSettingsPanel();
}
function refreshSettingsPanel(){
  var box=document.getElementById('setpRows');
  if(!box) return;
  box.innerHTML=SLOTS.map(function(slot){
    var variants=REGISTRY[slot]||{};
    var active=_activeVariant[slot]||DEFAULTS[slot];
    var opts=Object.keys(variants).map(function(id){
      return '<option value="'+esc(id)+'"'+(id===active?' selected':'')+'>'+esc(variants[id].label||id)+'</option>';
    }).join('');
    var desc=(variants[active]||{}).desc||'';
    var cfgHtml='';
    var v=variants[active];
    if(v&&v.config&&v.config.length){
      var curCfg=getVariantCfg(slot,active);
      cfgHtml='<div class="setcfg">'+v.config.map(function(c){
        if(c.type==='bool'){
          var checked=curCfg[c.key]!==undefined?curCfg[c.key]:c.default;
          return '<label><input type="checkbox" '+(checked?'checked':'')+
            ' onchange="var o=getVariantCfg(\''+esc(slot)+'\',\''+esc(active)+'\');o[\''+esc(c.key)+'\']=this.checked;setVariantCfg(\''+esc(slot)+'\',\''+esc(active)+'\',o)">'+
            esc(c.label||c.key)+'</label>';
        }
        return '';
      }).join('')+'</div>';
    }
    return '<div class="setrow"><label>'+esc(slot)+'</label>'+
      '<select onchange="setPref(\''+esc(slot)+'\',this.value)">'+opts+'</select>'+
      '<span class="setdesc">'+esc(desc)+'</span></div>'+cfgHtml;
  }).join('');
}

function noop(){}

// ---- init: apply stored preferences ----
mountAll();

// ---- Aurora Glass shader integration (progressive enhancement, feature-flagged) ----
var _auroraShader = null;
var _auroraEnabled = false;
function auroraFlagKey(){ return 'bifrost_aurora_shader'; }
function hudFlagKey(){ return 'bifrost_hud_strip'; }
function tracesFlagKey(){ return 'bifrost_traces'; }  // W99: traces expanded/collapsed
function initAurora(){
  // W99: apply traces mode on first init (default expanded)
  applyTracesMode(tracesMode());
  if (!window.AuroraGlass || !window.AuroraGlass.isSupported()) return false;
  if (_auroraShader) return true;   // already running
  try {
    var canvas = document.getElementById('aurora-canvas');
    if (!canvas) return false;
    _auroraShader = new window.AuroraGlass.AuroraShader(canvas);
    _auroraShader.start();
    // Kill the CSS fallback (body::before conic blur) — the shader is the light bed now
    var ss = document.createElement('style');
    ss.id = 'aurora-fallback-hide';
    ss.textContent = 'body::before{display:none}';
    document.head.appendChild(ss);
    _auroraEnabled = true;
    localStorage.setItem(auroraFlagKey(), '1');
    return true;
  } catch(e) { return false; }
}
function stopAurora(){
  if (!_auroraShader) return;
  _auroraShader.destroy();
  _auroraShader = null;
  _auroraEnabled = false;
  localStorage.setItem(auroraFlagKey(), '0');
  // Restore the CSS fallback
  var ss = document.getElementById('aurora-fallback-hide');
  if (ss) ss.remove();
}
function toggleAuroraFlag(){
  if (_auroraEnabled) stopAurora();
  else { if (!initAurora()) { toast('aurora shader unavailable — WebGL2 or benchmark required'); return; } }
  refreshAuroraButtons();
}
function refreshAuroraButtons(){
  var btn = document.getElementById('auroraToggle');
  var st = document.getElementById('auroraStatus');
  if (!btn) return;
  btn.textContent = _auroraEnabled ? 'Disable' : 'Enable';
  if (st) st.textContent = _auroraEnabled ? 'on — animated aurora active' : 'off — run bench-aurora.html first';
}
// Auto-start if previously enabled (user opted in and benchmark passed)
(function(){
  var stored = localStorage.getItem(auroraFlagKey());
  if (stored !== '0') { initAurora(); }   // default ON — the shock factor shouldn't be hidden; isSupported() + fps fallback guard it
  refreshAuroraButtons();
})();

// HUD strip feature flag (default ON — pure DOM, no perf risk)
function toggleHUDFlag(){
  var hud = document.getElementById('hud');
  var cur = localStorage.getItem(hudFlagKey()) !== '0';   // default '1' if unset
  var next = !cur;
  localStorage.setItem(hudFlagKey(), next ? '1' : '0');
  if (!next && hud) { hud.classList.remove('show'); }
  refreshHUDButtons();
  // Force a re-render on the next poll so the HUD reappears
  _lastHudSig = null;
}
function refreshHUDButtons(){
  var btn = document.getElementById('hudToggle');
  var st = document.getElementById('hudStatus');
  if (!btn) return;
  var on = localStorage.getItem(hudFlagKey()) !== '0';
  btn.textContent = on ? 'Disable' : 'Enable';
  if (st) st.textContent = on ? 'on — pure DOM, no perf cost' : 'off — hidden';
}
(function(){ refreshHUDButtons(); })();

// W99: traces expanded/collapsed — per-viewer sharpness dial (Daniel, 2026-07-28)
function tracesMode(){ return localStorage.getItem(tracesFlagKey()) !== '0'; }
function setTraces(mode){
  var expanded = (mode === 'expanded');
  localStorage.setItem(tracesFlagKey(), expanded ? '1' : '0');
  applyTracesMode(expanded);
  [].forEach.call(document.querySelectorAll('.traces-btn'), function(b){
    b.classList.toggle('active', b.dataset.lvl === mode);
  });
  var st = document.getElementById('tracesStatus');
  if(st) st.textContent = expanded ? 'expanded — operator view' : 'collapsed — compact';
}
function applyTracesMode(expanded){
  var logEl = document.getElementById('log');
  if(!logEl) return;
  if(expanded){ logEl.classList.add('traces-expanded'); }
  else { logEl.classList.remove('traces-expanded'); }
  [].forEach.call(logEl.querySelectorAll('.trace-card'), function(card){
    if(expanded){ card.classList.add('open'); }
    else { card.classList.remove('open'); }
  });
}
// Shaderpark controls: aurora speed + intensity sliders (live-tune uniforms, localStorage persistence)
function auroraSpeedKey(){ return 'bifrost_aurora_speed'; }
function auroraIntensityKey(){ return 'bifrost_aurora_intensity'; }
function setAuroraSpeed(v){
  if (_auroraShader) _auroraShader.setSpeed(v);
  localStorage.setItem(auroraSpeedKey(), v);
  var lbl = document.getElementById('auroraSpeedLabel');
  if (lbl) lbl.textContent = v.toFixed(2) + '×';
}
function setAuroraIntensity(v){
  if (_auroraShader) _auroraShader.setIntensity(v);
  localStorage.setItem(auroraIntensityKey(), v);
  var lbl = document.getElementById('auroraIntensityLabel');
  if (lbl) lbl.textContent = v.toFixed(2);
}
function refreshAuroraParams(){
  var speedSlider = document.getElementById('auroraSpeedSlider');
  var intSlider = document.getElementById('auroraIntensitySlider');
  var speedRow = document.getElementById('auroraSpeedRow');
  var intRow = document.getElementById('auroraIntensityRow');
  if (!speedSlider || !intSlider) return;
  // Show sliders only when aurora is enabled
  var on = _auroraEnabled;
  if (speedRow) speedRow.style.display = on ? '' : 'none';
  if (intRow) intRow.style.display = on ? '' : 'none';
  if (!on) return;
  // Restore persisted values
  var sp = parseFloat(localStorage.getItem(auroraSpeedKey())) || 1;
  var it = parseFloat(localStorage.getItem(auroraIntensityKey())) || 0.85;
  speedSlider.value = sp; setAuroraSpeed(sp);
  intSlider.value = it; setAuroraIntensity(it);
}
// Wire into toggleAuroraFlag + initAurora so sliders appear/disappear
(function(){
  var _origToggle = toggleAuroraFlag;
  toggleAuroraFlag = function(){
    _origToggle();
    refreshAuroraParams();
  };
  var _origInit = initAurora;
  initAurora = function(){
    var ok = _origInit();
    if (ok) {
      // Apply persisted speed/intensity to the new shader
      var sp = parseFloat(localStorage.getItem(auroraSpeedKey())) || 1;
      var it = parseFloat(localStorage.getItem(auroraIntensityKey())) || 0.85;
      if (_auroraShader) { _auroraShader.setSpeed(sp); _auroraShader.setIntensity(it); }
    }
    refreshAuroraParams();
    return ok;
  };
  // Initial state
  refreshAuroraParams();
})();

// Wire setState into the status loop. Called at the end of applyStatus.
function syncAuroraState(paused, haltedCount) {
  if (!_auroraShader) return;
  if (haltedCount > 0) _auroraShader.setState(2);           // any agent halted -> desaturate
  else if (paused)     _auroraShader.setState(1);           // global pause -> amber tint
  else                 _auroraShader.setState(0);           // normal
}

// ---- Narration toggle (claude reasoning visibility: off|key|full) ----
var NARR_LABELS = {off:'off — silent', key:'key — decision points only', full:'full — stream all reasoning'};
async function setNarration(level){
  try {
    var r = await fetch('/narration', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({level:level})});
    var j = await r.json();
    if (j && j.ok) {
      refreshNarrButtons(level);
      toast('\u{1f4ad} narration: ' + level);
    }
  } catch(e) { toast('narration toggle failed — bus offline?'); }
}
function refreshNarrButtons(level){
  [].forEach.call(document.querySelectorAll('.narr-btn'), function(b){
    b.classList.toggle('active', b.dataset.lvl === level);
  });
  var st = document.getElementById('narrStatus');
  if (st) st.textContent = NARR_LABELS[level] || level;
}

// ---- Session bookends (S4): episode chip + panel + advisory suggestion banner ----
// Renders the locked contract (design sec.6) served by /episode/*; the suggestion is ADVISORY --
// only Accept closes anything. Poll is slow (15s): episode state moves at human pace.
var _epi = null;            // last /episode/current payload
var _epiDraft = null;       // pending close draft {chapter_id,...} while the edit card is open
function epiIgnoreKey(s){ return (_epi&&_epi.id||'') + '|' + (s.reason||'') + '|' + (s.title||''); }
function epiIgnored(s){
  try{
    var m = JSON.parse(localStorage.getItem('bifrost_epi_ignore')||'{}');
    var until = m[epiIgnoreKey(s)];
    return until && Date.now() < until;
  }catch(e){ return false; }
}
function epiSuppress(s, ms){
  try{
    var m = JSON.parse(localStorage.getItem('bifrost_epi_ignore')||'{}');
    m[epiIgnoreKey(s)] = Date.now() + ms;
    localStorage.setItem('bifrost_epi_ignore', JSON.stringify(m));
  }catch(e){}
}
function epiFmtDur(sec){
  sec = Math.max(0, sec|0);
  if (sec < 3600) return Math.round(sec/60) + 'm';
  return Math.floor(sec/3600) + 'h' + Math.round((sec%3600)/60) + 'm';
}
function epiRender(){
  var chip = document.getElementById('epiChip');
  var banner = document.getElementById('epiBanner');
  var meta = document.getElementById('epiMeta');
  if (!chip) return;
  var c = _epi;
  if (!c){
    chip.innerHTML = '📖 episode';
    if (banner) banner.classList.remove('show');
    return;
  }
  var t = c.title || 'untitled episode';
  chip.innerHTML = '📖 ' + t.slice(0, 26).replace(/</g,'&lt;') +
                   '<span class="epidur">' + epiFmtDur(c.duration_seconds) + '</span>';
  if (meta) meta.textContent = 'started ' + (c.started||'').replace('T',' ').slice(0,16) + ' · ' +
      epiFmtDur(c.duration_seconds) + ' · ' + (c.beats_count|0) + ' beats' +
      (c.suggestion ? ' · suggestion: ' + c.suggestion.reason + ' (' + Math.round((c.suggestion.confidence||0)*100) + '%)' : '');
  var s = c.suggestion;
  if (banner){
    if (s && !epiIgnored(s) && !_epiDraft){
      document.getElementById('epiSugTitle').textContent = 'AI suggests ending this episode: ' + (s.title || 'untitled');
      document.getElementById('epiSugReason').textContent = '— ' + s.reason + ' · ' + Math.round((s.confidence||0)*100) + '%';
      banner.classList.add('show');
    } else {
      banner.classList.remove('show');
    }
  }
}
async function epiPoll(){
  try{
    var r = await (await fetch('/episode/current')).json();
    _epi = r.current_chapter || null;
  }catch(e){ _epi = null; }
  epiRender();
}
function toggleEpisode(){
  var p = document.getElementById('epi');
  p.classList.toggle('show');
  if (p.classList.contains('show')) epiPoll();
}
function epiShowDraft(draft){
  _epiDraft = draft;
  document.getElementById('epi').classList.add('show');
  document.getElementById('epiDraft').style.display = 'block';
  document.getElementById('epiTitle').value = draft.title || '';
  document.getElementById('epiDesc').value = draft.description || '';
  document.getElementById('epiWhy').value = draft.why || '';
  epiRender();
}
async function epiClose(){
  try{
    var r = await (await fetch('/episode/close',{method:'POST',
      headers:{'Content-Type':'application/json'}, body:'{}'})).json();
    if (r.draft) epiShowDraft(r.draft);
    epiPoll();
  }catch(e){}
}
async function epiDraftAccept(){
  if (!_epiDraft) return;
  try{
    await fetch('/episode/accept',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({chapter_id:_epiDraft.chapter_id,
        title:document.getElementById('epiTitle').value,
        description:document.getElementById('epiDesc').value,
        why:document.getElementById('epiWhy').value})});
  }catch(e){}
  epiDraftCancel();
  epiPoll();
}
function epiDraftCancel(){
  _epiDraft = null;
  document.getElementById('epiDraft').style.display = 'none';
  epiRender();
}
async function epiSuggestAccept(){
  var s = _epi && _epi.suggestion; if (!s) return;
  try{   // one-shot: close with the suggested fields and finalize (contract's agent path)
    await fetch('/episode/close',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:s.title, description:s.description, why:s.why, finalize:true})});
  }catch(e){}
  epiPoll();
}
function epiSuggestIgnore(){    // suppress THIS suggestion for this chapter (until it changes)
  var s = _epi && _epi.suggestion; if (!s) return;
  epiSuppress(s, 24*3600*1000);
  epiRender();
}
function epiSuggestContinue(){  // keep working; the banner may return in ~10 min
  var s = _epi && _epi.suggestion; if (!s) return;
  epiSuppress(s, 10*60*1000);
  epiRender();
}
epiPoll(); setInterval(epiPoll, 15000);

// ---- Viz-canvas engine: slide-deck cards between aurora and cockpit ----
var _vizEngine = null, _vizVisible = false, _vizDeckMode = false;
function initViz(){
  if (!window.BifrostViz) return false;
  if (_vizEngine) return true;
  try {
    var canvas = document.getElementById('viz-canvas');
    if (!canvas) return false;
    _vizEngine = new window.BifrostViz.VizEngine(canvas);
    _vizEngine.onChange(function(info){
      updateVizLabel();
      if (info) {
        var lbl = document.getElementById('vizLabel');
        if (lbl) lbl.textContent = info.gridMode ? 'grid' : (info.idx + 1) + '/' + info.total + ' ' + (info.label || '');
        document.getElementById('vizGridBtn').classList.toggle('on', info.gridMode);
        document.getElementById('vizDeckBtn').classList.toggle('on', info.deckMode);
        document.getElementById('vizBtn').classList.toggle('active', _vizVisible);
      }
    });
    _vizEngine.start();
    return true;
  } catch(e) { return false; }
}
function vizToggle(){
  if (!_vizEngine && !initViz()) return;
  _vizVisible = !_vizVisible;
  document.getElementById('viz-canvas').classList.toggle('show', _vizVisible);
  document.getElementById('viz-ctl').classList.toggle('show', _vizVisible);
  document.getElementById('vizBtn').classList.toggle('active', _vizVisible);
  if (!_vizVisible) setVizDeckMode(false); // exit deck mode when hiding
  if (_vizVisible) updateVizLabel();
}
function vizNext(){ if(_vizEngine){ _vizEngine.nextCard(); } }
function vizPrev(){ if(_vizEngine){ _vizEngine.prevCard(); } }
function vizGrid(){ if(_vizEngine){ _vizEngine.showGrid(); } }
function vizDeckMode(){
  if (!_vizEngine) return;
  setVizDeckMode(!_vizDeckMode);
}
function setVizDeckMode(on){
  _vizDeckMode = !!on;
  if (_vizEngine) _vizEngine.setDeckMode(_vizDeckMode);
  document.getElementById('vizDeckBtn').classList.toggle('on', _vizDeckMode);
  // Deck mode: shrink log + activity, expand viz canvas to fill the cockpit area
  var log = document.getElementById('log');
  var act = document.getElementById('activity');
  var viz = document.getElementById('viz-canvas');
  if (_vizDeckMode) {
    if (log) log.style.maxHeight = '140px';
    if (act) act.style.display = 'none';
    if (viz) viz.style.inset = '56px 0 120px 0';  // under header, above composer
  } else {
    if (log) log.style.maxHeight = '';
    if (act) act.style.display = '';
    if (viz) viz.style.inset = '0';
  }
}
function updateVizLabel(){
  if (!_vizEngine) return;
  var info = _vizEngine.cardInfo();
  var lbl = document.getElementById('vizLabel');
  if (lbl && info) lbl.textContent = info.gridMode ? 'grid' : (info.idx + 1) + '/' + info.total + ' ' + (info.label || '');
  // Also update the header button
  var hbtn = document.getElementById('vizBtn');
  if (hbtn && info && _vizVisible) hbtn.textContent = '\u{1f4ca} ' + (info.label || 'Deck');
  else if (hbtn) hbtn.textContent = '\u{1f4ca} Deck';
}
// Feed traces + edges to viz engine — ALWAYS collect data, even when hidden
(function(){
  var _origAddMsg = addMsg;
  addMsg = function(m){
    _origAddMsg(m);
    if (_vizEngine) {
      if (m.kind === 'trace') _vizEngine.feedTrace(m);
      if (m.kind === 'chat' && m.from && m.to && m.to !== 'all' && m.to !== '*') {
        _vizEngine.feedEdge(m.from, m.to);
      }
    }
  };
  // Also feed edges from the send() function (user -> agent messages)
  var _origSend = send;
  send = function(){
    var text = (document.getElementById('input')||{}).value || '';
    var target = (document.getElementById('target')||{}).value || 'all';
    if (_vizEngine && text.trim() && target !== 'all') {
      _vizEngine.feedEdge('user', target);
    }
    return _origSend();
  };
})();
// Keyboard: v=toggle, arrows=navigate, g=grid, d=deck-mode, Escape=hide
document.addEventListener('keydown', function(e){
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if (e.key === 'v' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); vizToggle(); }
  if (e.key === 'Escape' && _vizVisible) { e.preventDefault(); vizToggle(); }
  if (_vizVisible && _vizEngine) {
    if (e.key === 'ArrowRight') { e.preventDefault(); vizNext(); }
    if (e.key === 'ArrowLeft')  { e.preventDefault(); vizPrev(); }
    if (e.key === 'g' && !e.ctrlKey) { e.preventDefault(); vizGrid(); }
    if (e.key === 'd' && !e.ctrlKey) { e.preventDefault(); vizDeckMode(); }
  }
});
initViz();
</script>
<script src="/theme-void.js"></script>
<script src="/presence-rail.js"></script>
<script src="/presence-cloud.js"></script>
<script src="/rail.js"></script>
<script src="/timeline.js"></script>
<script src="/agent-avatar.js"></script>
<script src="/activity-line.js"></script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
