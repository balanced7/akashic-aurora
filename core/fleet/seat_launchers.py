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
    "sunshine": "sunshine", "sol": "sunshine",
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
    "sunshine": {
        "seat": "sol",
        "callsign": "Sunshine",
        # `runner`, not `daemon`: bifrost_daemon.py hardcodes bifrost_runner_deepseek.py for
        # --spawn-runner, so routing sol through the daemon hands him another seat's script.
        # He has his own -- scripts/bifrost_runner_sol.py, an OpenAI Responses API seat.
        "kind": "runner",
        "url": None,
        # ADDED 2026-08-28. He was the one seat with NO lever: revive.py cannot target him
        # (DAEMON_AGENTS is deepseek/kimi, --target is app/redis/daemon/gateway), so
        # `!spawn sunshine` fell through to the task path and would have launched a claude
        # session whose job was the word "sunshine" -- the 2026-08-24 defect this module
        # exists to kill, reproduced under a different name.
        #
        # EXECUTED 2026-08-28, COLD -- the strongest form, and the one neither heimdall nor
        # navi has. Pre-state verified first: no sol entry in the roster at all, no process,
        # last activity 19h prior. Ran this exact lever detached with the env overlay; pid
        # 7244 came up and sol reached bus presence as sol#7244-sol phase=running within the
        # 75s window. This field was written AFTER the run, not before -- the ordering the
        # rill entry above records getting wrong.
        "drilled": "2026-08-28: raised from COLD by this lever, sol#7244-sol on the bus",
        # FOUND 2026-08-31: the 08-28 drill proved the lever raises sol onto the bus, but never
        # checked WHAT came up. It came up TOOLLESS -- bifrost_runner_sol.py defaults to its
        # "one-shot bridge" replier (module line ~342) unless launched with --agentic, and even
        # --agentic alone gives read-only tools; --allow-exec is separate. This lever passed
        # neither, so every sol raised through it landed exactly in the
        # hand_spawned_runner_narrows_the_door_below_the_acl hole: security/acl.json grants sol
        # `exec` (2026-08-27, Daniil verbatim 'give the stable sol seat governed exec to play
        # with Aurora verbs'), but the DOOR his process launched behind carried none of it.
        # `write` is deliberately NOT in that grant, so it is deliberately not added here either
        # -- widening it needs its own authorization, not a side effect of this fix.
        "launch_flags": ["--agentic", "--allow-exec"],
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
        # hand_spawned_runner_narrows_the_door_below_the_acl: a capability in acl.json that
        # never reaches the launch line is not a capability -- the seat cannot tell the
        # difference between "policy" and "the lever forgot a flag". launch_flags is how a
        # registry entry states the posture its process must launch behind, opt-in per seat.
        return ([sys.executable, script, "--agent", seat] + list(rec.get("launch_flags") or []),
                env, root)

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


# ---------------------------------------------------------------- the claude seat
# `vandor` is not a daemon or a server -- it is a CLI seat, and it has TWO
# preconditions that today proved are independent: the Claude Code DESKTOP APP (the
# MSIX package that died at 12:01:59 and stayed dead until 14:45:52) and the `claude`
# CLI, which kept working the entire time the app was down. So the app is ensured
# DELIBERATELY, and never as a side effect of asking for a seat.
_SEATS["vandor"] = {
    "seat": "claude", "callsign": "Vandor", "kind": "claude_seat",
    "url": None,
    "drilled": "",     # the app-then-seat path is NOT yet drilled from cold
}
_ALIASES.update({"vandor": "vandor", "claude": "vandor"})

#: Flags a spawn target may carry. Parsed off before the bare-name check, so
#: `!spawn vandor --repair` still resolves to a seat rather than falling through to
#: the task path.
SPAWN_FLAGS = ("--repair", "--seat", "--status")


def parse_spawn_target(text: str) -> Tuple[Optional[Dict[str, Any]], set]:
    """(seat, flags) for an operator's `!spawn` argument. Pure.

    A seat resolves only when what REMAINS after removing known flags is a bare name,
    so a sentence is still a task and `--repair` does not turn one into a launch."""
    words = str(text or "").split()
    flags = {w.lower() for w in words if w.lower() in SPAWN_FLAGS}
    rest = " ".join(w for w in words if w.lower() not in SPAWN_FLAGS)
    return resolve_seat(rest), flags


def claude_permission_flags(mode: str = "default") -> List[str]:
    """The CLI permission flags a spawned claude seat launches with.

    THIS IS THE ONE THAT KEEPS BITING. A seat spawned read-only cannot arm its own wake
    watcher, cannot drain its mail, cannot commit, and cannot run a test -- so it looks
    alive on every dial and can do nothing, which is the failure this house has paid for
    repeatedly (unattended_spawn_cannot_use_write_or_exec_only_mcp_tools;
    spawn_grant_flags_must_ride_the_launch_line;
    hand_spawned_runner_narrows_the_door_below_the_acl). It is a decidable rule, so it
    lives in core WITH ITS PINS instead of inline in the gateway, and an unknown mode
    degrades to `arm` rather than silently to read-only."""
    m = str(mode or "default").strip().lower()
    if m == "dangerous":
        return ["--dangerously-skip-permissions"]
    return ["--permission-mode", "acceptEdits",
            "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep"]


def claude_seat_plan(*, app_healthy: bool, app_repairable: bool, app_detail: str,
                     live_seats: int, flags: set) -> Dict[str, Any]:
    """What `!spawn vandor` should DO, given the world. Pure.

    When the app is missing, this REPORTS AND OFFERS rather than acting. Package surgery
    triggered from a phone by a bare word is not a thing this house should do silently --
    and the whole point of the day was that a lever which acts without showing its reasons
    is indistinguishable from one that lies. So the ambiguous case hands him the choice.
    """
    seats = f"{live_seats} live claude seat(s)"
    if "--status" in flags:
        return {"action": "options", "message":
                f"Claude Code app: {'UP' if app_healthy else 'DOWN'} — {app_detail}\n"
                f"{seats}\n" + _choices(app_healthy, app_repairable)}
    if app_healthy or "--seat" in flags:
        return {"action": "spawn", "message":
                (f"app UP ({app_detail}); {seats} — spawning a fresh seat"
                 if app_healthy else
                 f"app DOWN ({app_detail}) — skipping it as asked; spawning a CLI seat, "
                 f"which works without it")}
    if "--repair" in flags:
        if not app_repairable:
            return {"action": "options", "message":
                    f"app DOWN and NOT repairable by this lever — {app_detail}\n"
                    + _choices(app_healthy, app_repairable)}
        return {"action": "repair_then_spawn", "message":
                f"app DOWN ({app_detail}) — verifying payload, then clearing only the "
                f"stale status bit, then proving by launch, then spawning a seat.\n"
                f"NOTE: the repair rung itself is drilled (executed falsifiers, real "
                f"package verifies 2348/2348 files, 11411/11411 blocks), but this "
                f"END-TO-END app-down → repair → seat chain is NOT — it cannot be "
                f"drilled from inside the app it repairs."}
    return {"action": "options", "message":
            f"Claude Code app NOT DETECTED — {app_detail}\n{seats}\n"
            + _choices(app_healthy, app_repairable)}


def _choices(app_healthy: bool, app_repairable: bool) -> str:
    lines = ["How to proceed:"]
    if not app_healthy and app_repairable:
        lines.append("  `!spawn vandor --repair`  verify payload → clear the stale MSIX "
                     "bit → launch → then a seat")
    elif not app_healthy:
        lines.append("  (no repair offered: this lever has no rung for that state)")
    lines.append("  `!spawn vandor --seat`    skip the app; spawn a CLI seat, which works "
                 "without it")
    lines.append("  `!revive --target app`    the app alone, no seat")
    return "\n".join(lines)
