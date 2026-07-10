"""
Session State — snapshot the live Bifrost session so it can be resumed later.

When you're done for the night, save a snapshot of which agents were running, what they were
doing, and the current discussion context. Tomorrow, one command spins everything back up.

Snapshot is a JSON file in session_snapshots/ named by timestamp (e.g. 2026-07-04T0300.json).
The latest snapshot is also aliased as session_snapshots/latest.json for quick resume.

Integration:
  - bifrost_ui.py: GET /session/snapshot (save) + POST /session/resume (restore)
  - agent_cli.py: py agent_cli.py session --snapshot  /  py agent_cli.py session --resume
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent.parent.parent  # core/comm -> repo root
SNAPSHOT_DIR = HERE / "session_snapshots"
LATEST = SNAPSHOT_DIR / "latest.json"


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H%M")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def save(label: str = "") -> Dict[str, Any]:
    """Capture the current Bifrost session state. Returns the snapshot dict + path.

    Captures:
      - which agents are running (from the launcher registry)
      - which agents are online (from bus presence)
      - what each agent is doing (from control activity)
      - pause state
      - a timestamp and optional human label
    """
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    # ── Gather state ──────────────────────────────────────────────────
    agents: List[Dict[str, Any]] = []
    try:
        from core.comm.launcher import get_launcher
        agents = get_launcher().registry()
    except Exception:
        pass

    presence: List[Dict[str, Any]] = []
    try:
        from core.comm.bus import Bus
        presence = Bus("snapshot").presence()
    except Exception:
        pass

    activities: Dict[str, Any] = {}
    try:
        from core.comm import control
        activities = control.get_activities()
    except Exception:
        pass

    pause: Dict[str, Any] = {}
    try:
        from core.comm import control
        pause = control.pause_status()
    except Exception:
        pass

    # Mark which agents are running (have a live process)
    running_tags = [a["tag"] for a in agents if a.get("status") == "running"]
    online_ids = [p["agent"] for p in presence]

    snapshot = {
        "version": 1,
        "saved_at": _now(),
        "label": label or f"session-{_ts()}",
        "pause": pause,
        "running_agents": [
            {
                "tag": a["tag"],
                "agent_id": a["agent_id"],
                "pid": a.get("pid"),
                "description": a.get("description", ""),
                "activity": activities.get(a["agent_id"], {}),
            }
            for a in agents if a.get("status") == "running"
        ],
        "configured_agents": [
            {
                "tag": a["tag"],
                "agent_id": a["agent_id"],
                "status": a.get("status", "never_launched"),
                "description": a.get("description", ""),
            }
            for a in agents
        ],
        "online_agents": [
            {
                "agent": p["agent"],
                "last_seen": p.get("last_seen", ""),
                "activity": activities.get(p["agent"], {}),
            }
            for p in presence
        ],
        "context_note": "",
    }

    # ── Write snapshot ─────────────────────────────────────────────────
    fname = f"{_ts()}.json"
    path = SNAPSHOT_DIR / fname
    path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    # Alias as latest
    LATEST.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    return {"ok": True, "path": str(path), "latest": str(LATEST),
            "running": running_tags, "online": online_ids, "snapshot": snapshot}


def load(path: Optional[str] = None) -> Dict[str, Any]:
    """Load a saved snapshot. Defaults to latest.json."""
    target = Path(path) if path else LATEST
    if not target.exists():
        return {"ok": False, "error": f"no snapshot at {target}"}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return {"ok": True, "path": str(target), "snapshot": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def resume(path: Optional[str] = None, *, label: str = "") -> Dict[str, Any]:
    """Read a snapshot and relaunch the agents that were running.

    Spawns each running agent via the launcher. Returns which succeeded and which failed.
    A brief priming message can be broadcast to give agents context from the last session.
    """
    loaded = load(path)
    if not loaded["ok"]:
        return loaded

    snap = loaded["snapshot"]
    running = snap.get("running_agents", [])
    if not running:
        return {"ok": False, "error": "snapshot has no running agents to resume"}

    from core.comm.launcher import get_launcher
    launcher = get_launcher()

    results = []
    for agent in running:
        tag = agent["tag"]
        # Build a priming prompt from the snapshot context
        context = snap.get("context_note", "")
        prompt = ""
        if context:
            prompt = (
                f"[SESSION RESUME] You are being relaunched from a saved Bifrost session.\n"
                f"Label: {snap.get('label', 'unknown')}\n"
                f"Context: {context}\n"
                f"Your last known activity: {agent.get('activity', {}).get('state', 'unknown')}\n"
                f"Please check your inbox for any pending messages and continue where you left off."
            )
        elif label:
            prompt = f"[SESSION RESUME] Relaunched from session '{label}'. Check inbox and continue."

        result = launcher.launch(tag, prompt=prompt)
        results.append({
            "tag": tag,
            "agent_id": agent["agent_id"],
            "ok": result.get("ok", False),
            "pid": result.get("pid"),
            "error": result.get("error", ""),
        })

    all_ok = all(r["ok"] for r in results)

    # Clean up pause state so agents can work
    if snap.get("pause", {}).get("paused"):
        try:
            from core.comm import control
            control.resume()
        except Exception:
            pass

    return {
        "ok": all_ok,
        "resumed": len(results),
        "succeeded": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "results": results,
        "label": snap.get("label", ""),
    }


def list_snapshots() -> List[Dict[str, Any]]:
    """All saved snapshots, newest first."""
    if not SNAPSHOT_DIR.exists():
        return []
    out = []
    for f in sorted(SNAPSHOT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name == "latest.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append({
                "file": f.name,
                "saved_at": data.get("saved_at", ""),
                "label": data.get("label", ""),
                "running_agents": len(data.get("running_agents", [])),
                "online_agents": len(data.get("online_agents", [])),
            })
        except Exception:
            out.append({"file": f.name, "saved_at": "", "label": "(corrupt)", "running_agents": 0, "online_agents": 0})
    return out
