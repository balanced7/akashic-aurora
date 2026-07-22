"""System census timing probes — v2, capture stdout."""
import os, sys, time, json, io, contextlib
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "temp", "census_timings.txt")
sys.path.insert(0, REPO)

lines = []
def m(label, fn):
    buf = io.StringIO()
    t0 = time.time()
    try:
        with contextlib.redirect_stdout(buf):
            r = fn()
        elapsed = (time.time() - t0) * 1000
        out = str(r)[:120].replace("\n", " ")
        lines.append(f"{label}: {elapsed:.1f}ms -> {out}")
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        lines.append(f"{label}: {elapsed:.1f}ms ERROR: {type(e).__name__}: {str(e)[:80]}")

# Foundation
def _fs():
    from core.foundation.store import FileStore
    return FileStore()
m("Store-File set", lambda: _fs().set("census_test", "1"))
m("Store-File get", lambda: _fs().get("census_test"))
m("Store-Hybrid online", lambda: __import__("core.foundation.store", fromlist=["create_store"]).create_store(prefer_redis=True).online)

# Bus
def _b():
    from core.comm.bus import Bus
    return Bus("census")
m("Bus.online", lambda: _b().online)
m("Bus.register", lambda: _b().register())
m("Bus.send", lambda: _b().send("census", "chat", "ping"))
m("Bus.inbox peek 5", lambda: len(_b().inbox(advance=False, limit=5)))

# Recall (json output to avoid render time)
import argparse as _ap
m("recall empty", lambda: __import__("agent_cli").cmd_recall(
    _ap.Namespace(query="", json=True, full=None, agent_id="census")))
m("recall_at cmd", lambda: __import__("agent_cli").cmd_recall_at(
    _ap.Namespace(command="py agent_cli.py boot", path=None, agent_id="census", limit=3)))

# Boot
m("boot task leer", lambda: len(__import__("agent_cli").cmd_boot(
    _ap.Namespace(agent_id="census", task="leer", json=True, sources_json=None)) or ""))

# Task ledger
m("task list", lambda: __import__("agent_cli").cmd_task(
    _ap.Namespace(rest=["list"])))
m("task next", lambda: __import__("agent_cli").cmd_task(
    _ap.Namespace(rest=["next"])))

# Notes
m("notes 5", lambda: __import__("agent_cli").cmd_notes(
    _ap.Namespace(days=0, limit=5, json=False)))

# Events
m("events 5", lambda: __import__("agent_cli").cmd_events(
    _ap.Namespace(search=None, agent=None, kind=None, limit=5)))

# Locks
m("locks", lambda: __import__("agent_cli").cmd_locks(
    _ap.Namespace(agent_id="census")))

# Status
m("status json", lambda: __import__("agent_cli").cmd_status(
    _ap.Namespace(json=True)))

# Stats
m("stats 1h", lambda: __import__("agent_cli").cmd_stats(
    _ap.Namespace(hours=1.0, days=None)))

# Story
m("story atlas", lambda: __import__("agent_cli").cmd_story(
    _ap.Namespace(track=None, chronicle=False)))

# Bifrost sync
m("bifrost_sync", lambda: __import__("agent_cli").cmd_bifrost_sync(
    _ap.Namespace(agent_id="census", limit=3, consume=False)))

# Promoted
m("promoted 5", lambda: __import__("agent_cli").cmd_promoted(
    _ap.Namespace(limit=5, since=None, until=None)))

# Handoff list
m("handoff list", lambda: __import__("agent_cli").cmd_handoff(
    _ap.Namespace(agent_id="census", to=None, task=None, note=None, blocker=None, list=True)))

# Knowledge map
m("knowledge_map bifrost", lambda: __import__("agent_cli").cmd_knowledge_map(
    _ap.Namespace(query="bifrost", per_layer=3)))

# Injections
m("injections 1h", lambda: __import__("agent_cli").cmd_injections(
    _ap.Namespace(hours=1.0)))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"WROTE {len(lines)} lines to {OUT}")


def test_census_timings():
    assert True

