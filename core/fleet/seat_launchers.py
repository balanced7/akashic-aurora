"""seat_launchers -- `!spawn <name>` launches THAT seat, instead of a claude session about it.

THE DEFECT (2026-08-24). `!spawn` never resolved names. It took the operator's text as a
TASK STRING and handed it to a fresh claude seat. So when Daniil -- locked out, conductor
dead -- typed `!spawn rill` from his phone, the gateway spawned a claude session whose job
was the word "rill". It dutifully went and investigated Rill, wrote a report, and stopped.
Rill itself was never started, and stayed down for the rest of the day.

Every layer was working. The lever meant something other than what he meant.

WHAT A LAUNCHER ENTRY MUST CARRY, learned the hard way an hour before this file existed:

  THE SEAT'S OWN IDENTITY, EXPLICITLY. A DSH launched from inside another harness's
  session INHERITS that session's AKASHIC_AGENT_ID (docs/DSH_INTEGRATION.md), and the
  akashic plugin then pins itself observe-only by its own identity check
  (`plugins/dsh-akashic-recall/lib/index.js:135`) -- injecting nothing, mis-attributing
  nothing. That check is correct and it saved us; but it means a Rill launched carelessly
  comes up PRESENT AND DEAF. Alive on every dial, doing nothing. So every spec below sets
  its own AKASHIC_AGENT_ID rather than letting one be inherited.

RESOLUTION IS DELIBERATELY STRICT. Only a BARE seat name resolves. `!spawn rill` launches
Rill; `!spawn rill and check the ui` is a task for a claude seat, unchanged. A lever that
sometimes swallows your sentence because it began with a name would be a worse lever than
the one this replaces.
"""
from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

#: callsign / agent-id -> the seat it names. Both spellings resolve, because he says
#: "rill" and the ledger says "dsh_agent" and neither is wrong.
_ALIASES = {
    "rill": "rill", "dsh_agent": "rill", "dsh": "rill",
    "heimdall": "heimdall", "deepseek": "heimdall",
    "navi": "navi", "kimi": "navi",
}

#: One entry per launchable seat.
#:
#: `drilled` is NOT decoration. The house rule is that a recovery path without an executed
#: drill and a dated receipt is PRESUMED BROKEN, so the flag records which of these has
#: actually raised a dead seat and which has only been shown to be safe when the seat is
#: already up. It is read by the caller and shown to the operator; it must never be set
#: from the armchair.
_SEATS: Dict[str, Dict[str, Any]] = {
    "rill": {
        "seat": "dsh_agent",
        "callsign": "Rill",
        "kind": "dsh",
        "url": "http://127.0.0.1:3080",
        # EXECUTED 2026-08-24: killed pid 49696, confirmed no dsh/cordis process remained,
        # ran this lever, pid 52292 came up with observeOnly=false and dsh_agent returned
        # to bus presence at 22:32:19Z. (I wrote this field BEFORE running the drill, which
        # was the wrong order and exactly the sin of the day -- a receipt preceding its
        # evidence. It is rewritten here from what actually happened.)
        "drilled": "2026-08-24: killed cold, raised by this lever, dsh_agent back at 22:32:19Z",
    },
    "heimdall": {
        "seat": "deepseek",
        "callsign": "Heimdall",
        "kind": "daemon",
        "url": None,
        "drilled": "",   # safe-when-up only; raising it from the dead is NOT yet drilled
    },
    "navi": {
        "seat": "kimi",
        "callsign": "Navi",
        "kind": "runner",
        "url": None,
        "drilled": "",   # safe-when-up only; raising it from the dead is NOT yet drilled
    },
}


def resolve_seat(word: str) -> Optional[Dict[str, Any]]:
    """The seat a BARE name refers to, or None. Pure.

    None means "this is a task, not a seat" -- which is the historical behaviour and must
    stay reachable for every word that is not exactly a seat name."""
    key = str(word or "").strip().strip("`\"'").lower()
    if not key or len(key.split()) != 1:
        return None                     # a sentence is a task, never a launch
    slug = _ALIASES.get(key)
    if not slug:
        return None
    rec = dict(_SEATS[slug])
    rec["slug"] = slug
    return rec


def launch_argv(rec: Dict[str, Any], *, root: str,
                which=shutil.which,
                dsh_home: Optional[str] = None) -> Tuple[List[str], Dict[str, str], str]:
    """(argv, env-overlay, cwd) for a resolved seat. Raises if the launcher is unavailable,
    because a lever that pretends is the thing this whole day was about."""
    kind = rec.get("kind")
    seat = str(rec.get("seat"))
    # EVERY seat states its own identity. Never inherited -- see the module docstring.
    env: Dict[str, str] = {"AKASHIC_AGENT_ID": seat, "BIFROST_CONSUME_LANE": "work"}

    if kind == "dsh":
        home = dsh_home or os.environ.get("DSH_HOME") or os.path.join(
            os.path.expanduser("~"), ".dsh")
        exe = which("dsh")
        if not exe:
            raise RuntimeError(
                "dsh is not on PATH -- cannot launch Rill; install the DSH CLI "
                "(npm) or set DSH_HOME and put dsh on PATH")
        env["DSH_HOME"] = home
        return [exe, "web", "--no-open"], env, home

    if kind == "daemon":
        # The daemon owns its runner child and absorbs a duplicate via DaemonLock, so this
        # is safe to run when the seat is already up.
        return ([sys.executable, os.path.join(root, "scripts", "bifrost_daemon.py"),
                 "--agent", seat, "--spawn-runner"], env, root)

    if kind == "runner":
        # NOT the daemon. bifrost_daemon.py hardcodes bifrost_runner_deepseek.py for
        # --spawn-runner (lines 256/416), so `--agent kimi --spawn-runner` would hand Kimi
        # the wrong runner script -- the daemon_spawn_runner_hardcodes_deepseek_script
        # lesson. A non-deepseek seat launches with its OWN script.
        script = os.path.join(root, "scripts", f"bifrost_runner_{seat}.py")
        if not os.path.isfile(script):
            raise RuntimeError(f"no runner script for {seat!r} at {script}")
        return [sys.executable, script, "--agent", seat], env, root

    raise RuntimeError(f"unknown launcher kind {kind!r} for seat {seat!r}")


def launch_note(rec: Dict[str, Any]) -> str:
    """The line the operator gets. Names what is PROVEN and what is merely wired -- an
    undrilled lever must not read like a drilled one."""
    who = f"{rec.get('callsign')} ({rec.get('seat')})"
    where = f" — {rec['url']}" if rec.get("url") else ""
    if rec.get("drilled"):
        return f"launching {who}{where}; lever drilled {rec['drilled']}"
    return (f"launching {who}{where}; NOTE: this lever is wired but NOT yet drilled from "
            f"cold — it is safe to run when the seat is already up, and unproven at "
            f"raising a dead one")
