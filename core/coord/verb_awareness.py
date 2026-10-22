"""verb_awareness -- do agents reach for the house's verbs without being reminded?

THE QUESTION THIS MEASURES. Daniil, 2026-10-22: "I don't want to have to remind you of all of
this functionality all the time." Every channel the house had for its verbs was PULL-shaped --
`discover`, deferred MCP tools behind tool search, skills -- and each one fails at the same
point: the agent has to suspect a verb exists before it can find it. The verb guide
(core/coord/verb_guide.py) pushes instead. This module is the meter that says whether the
push works, read off the Claude Code transcripts that already exist, so the baseline needs no
instrumentation that was not there before the change.

WHAT COUNTS, and why each number is the one that moves:
  reminders      user-typed messages that name a verb as a command (`aurora recall`,
                 `agent_cli.py doctor`, a backticked verb). The miss itself: the human had
                 to supply the verb. Should FALL.
  discover       how often an agent looked the verb table up. A lookup is the symptom of
                 not knowing; should FALL once the map is in context.
  verb calls     verbs agents actually ran (shell or MCP), and how many DISTINCT verbs. Use
                 concentrated on a dozen verbs means the other hundred are invisible; the
                 distinct count should RISE.
  nudges         verb suggestions the hooks injected, and how many of those verbs the agent
                 then ran in the same session (follow-through). Zero before the change.
  skills         invocations of the house's own skills (.agents/skills).

Read-only and transcript-local: it parses JSONL on this machine and writes nothing.
"""

from __future__ import annotations

import glob
import json
import os
import re
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

#: The marker every hook-injected verb suggestion carries (agent/harness/verbs.py renders it),
#: so a transcript can show what was suggested without a second record.
NUDGE_MARK = "[aurora verbs]"

_SYSTEM_PREFIXES = ("<system-reminder", "<command-", "<task-notification", "<local-command", "<agent-message")


def transcript_files(root: str | None = None, project_glob: str = "*akashic-labs-aurora*") -> list[str]:
    """Claude Code session transcripts for this repo and its worktrees (top-level sessions only;
    subagent sidechains live in subdirectories and are not the operator's sessions)."""
    base = root or os.path.join(os.getenv("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")
    return sorted(glob.glob(os.path.join(base, project_glob, "*.jsonl")))


def _verb_call_re(verbs: Iterable[str]) -> re.Pattern:
    alt = "|".join(sorted((re.escape(v) for v in verbs), key=len, reverse=True))
    return re.compile(rf"(?:agent_cli\.py|\baurora)\"?\s+({alt})(?![\w-])")


def _user_text(o: dict) -> str:
    """The words a human typed in this entry, or "" for tool results, hooks and harness text."""
    if o.get("type") != "user" or o.get("isMeta") or o.get("toolUseResult") is not None:
        return ""
    m = (o.get("message") or {}).get("content")
    if isinstance(m, list):
        m = " ".join(x.get("text", "") for x in m if isinstance(x, dict) and x.get("type") == "text")
    if not isinstance(m, str):
        return ""
    s = m.lstrip()
    return "" if s.startswith(_SYSTEM_PREFIXES) else m


def scan_session(path: str, verbs: list[str]) -> dict[str, Any]:
    """One transcript -> its counts. Unreadable lines are skipped, never fatal."""
    from core.coord.verb_guide import mentioned_verbs

    call_re = _verb_call_re(verbs)
    vset = set(verbs)
    rem: Counter = Counter()
    calls: Counter = Counter()
    nudged: set[str] = set()
    used_after_nudge: set[str] = set()
    skills: Counter = Counter()
    first = last = ""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return {"path": path, "unreadable": True}
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        ts = o.get("timestamp") or ""
        if ts:
            first = first or ts
            last = ts
        txt = _user_text(o)
        if txt:
            for v in mentioned_verbs(txt, vset):
                rem[v] += 1
            continue
        if o.get("type") == "attachment":
            a = o.get("attachment") or {}
            if a.get("type") == "hook_additional_context":
                body = "\n".join(a.get("content") or [])
                if NUDGE_MARK in body:
                    nudged.update(
                        v for v in re.findall(r"`[^`]*?(?:\baurora|agent_cli\.py) ([\w-]+)", body) if v in vset
                    )
            continue
        if o.get("type") != "assistant":
            continue
        for b in (o.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            hit: list[str] = []
            if name.startswith("mcp__akashic-aurora__"):
                v = name[len("mcp__akashic-aurora__") :].replace("_", "-")
                hit = [v] if v in vset else []
            elif name in ("Bash", "PowerShell"):
                hit = call_re.findall(str(inp.get("command", "")))
            elif name == "Skill":
                skills[str(inp.get("skill", ""))] += 1
            for v in hit:
                calls[v] += 1
                if v in nudged:
                    used_after_nudge.add(v)
    return {
        "path": path,
        "first": first,
        "last": last,
        "reminders": dict(rem),
        "calls": dict(calls),
        "nudged": sorted(nudged),
        "followed": sorted(used_after_nudge),
        "skills": dict(skills),
    }


def summarize(sessions: list[dict], house_skills: Iterable[str] = ()) -> dict[str, Any]:
    """Fold per-session scans into the report. Sessions with no activity still count in the
    denominator: a session that never needed a verb is part of the population."""
    ss = [s for s in sessions if not s.get("unreadable")]
    rem: Counter = Counter()
    calls: Counter = Counter()
    skills: Counter = Counter()
    nudged = followed = 0
    for s in ss:
        rem.update(s["reminders"])
        calls.update(s["calls"])
        skills.update(s["skills"])
        nudged += len(s["nudged"])
        followed += len(s["followed"])
    house = set(house_skills)
    n = len(ss) or 1
    dates = sorted(x for s in ss for x in (s["first"], s["last"]) if x)
    return {
        "sessions": len(ss),
        "from": dates[0][:10] if dates else "",
        "to": dates[-1][:10] if dates else "",
        "reminders": sum(rem.values()),
        "reminders_per_session": round(sum(rem.values()) / n, 2),
        "reminded_verbs": rem.most_common(15),
        "discover_calls": calls.get("discover", 0),
        "verb_calls": sum(calls.values()),
        "distinct_verbs_used": len(calls),
        "top_verbs": calls.most_common(15),
        "nudged": nudged,
        "nudges_followed": followed,
        "house_skill_invocations": sum(c for k, c in skills.items() if k in house),
        "skill_invocations": sum(skills.values()),
    }


def measure(verbs: list[str], *, root: str | None = None, since: str = "") -> dict[str, Any]:
    """The whole report over this machine's transcripts. `since` (ISO date) keeps sessions that
    were still active on or after that day -- the after-picture of a change."""
    sessions = [scan_session(p, verbs) for p in transcript_files(root)]
    if since:
        sessions = [s for s in sessions if (s.get("last") or "")[:10] >= since]
    # The code root this module ships in, not AURORA_REPO: the skills being measured are the ones
    # this checkout carries.
    skills_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".agents", "skills"
    )
    house = os.listdir(skills_dir) if os.path.isdir(skills_dir) else []
    return summarize(sessions, house)
