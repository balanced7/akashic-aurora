"""Session provenance -- which harness, model, effort and environment a session ran in.

Meta-harness task 01. A lesson used to carry only `agent_id`, and every Claude Code session
shares `claude`, so a lesson one model learned in one harness was served to every agent as
if it held for all of them. Nothing durable said otherwise: the model self-report in
`seat_model.py` is a Redis key with a 15-minute TTL, `AKASHIC_HARNESS` was never saved, and
effort lived only in a request parameter.

THE RECORD. One per session, written once and filled in as more becomes known:

    session_id, agent_id, harness, harness_version, model, effort,
    project_fingerprint, user_fingerprint, git_sha, branch, os, cwd, started_at

It lives in two places, so it survives a Redis restart: a Store hash `prov:session:<id>`
(no TTL) and one `provenance` event on the firehose. Lessons, flips, fails, repeats and
`session_signals` carry the pointer `prov:session:<id>`.

HONEST ABSENCE. A field the harness does not expose reads `unknown`. It is never guessed:
a guessed model would scope a lesson to the wrong model, which is worse than no scope.

Every function here is fail-soft. Provenance is telemetry; it must never break `learn`,
a hook or a runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[2]

UNKNOWN = "unknown"
KEY_PREFIX = "prov:session:"

#: Fields in the order `render` prints them.
FIELDS = (
    "session_id",
    "agent_id",
    "harness",
    "harness_version",
    "model",
    "effort",
    "project_fingerprint",
    "user_fingerprint",
    "git_sha",
    "branch",
    "os",
    "cwd",
    "started_at",
)

#: Fields that may start `unknown` and be learned later in the session (a SessionStart
#: payload may lack the model that the transcript names a turn later).
_FILLABLE = ("model", "effort", "harness_version", "agent_id")

#: Project-level harness config. Order is part of the fingerprint, so keep it stable.
_PROJECT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/settings.json",
    ".codex/config.toml",
    ".cursor/hooks.json",
)
_PROJECT_DIRS = (".claude/skills", ".claude/agents", ".agents/skills", ".cursor/rules")
_USER_FILES = (".claude/settings.json", ".claude/CLAUDE.md", ".claude/AGENTS.md", ".codex/config.toml")


def pointer(session_id: str) -> str:
    """The followable pointer other records carry."""
    return f"{KEY_PREFIX}{session_id}" if session_id else ""


def current_session_id(env: Mapping[str, str] | None = None) -> str:
    """This process's session id, from the first harness variable that names one.

    `AKASHIC_SESSION_ID` wins so a runner or a replay can set it on purpose. Empty when no
    harness says -- the caller then decides whether to mint one (`ensure(mint=True)`).
    """
    env = os.environ if env is None else env
    for name in (
        "AKASHIC_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        v = (env.get(name) or "").strip()
        if v:
            return v
    return ""


def _harness(env: Mapping[str, str]) -> tuple[str, str]:
    """(harness, version). An explicit `AKASHIC_HARNESS` always wins."""
    explicit = (env.get("AKASHIC_HARNESS") or "").strip()
    version = (env.get("AKASHIC_HARNESS_VERSION") or "").strip()
    if explicit:
        return explicit, version or UNKNOWN
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_SESSION_ID"):
        # AI_AGENT reads like `claude-code_2-1-292_agent`; it is the only version Claude Code
        # exports into tool processes.
        ai = env.get("AI_AGENT") or ""
        parts = ai.split("_")
        if len(parts) >= 2 and parts[0] == "claude-code":
            version = parts[1].replace("-", ".")
        return "claude-code", version or UNKNOWN
    if any(k.startswith("CODEX_") for k in env):
        return "codex-cli", version or UNKNOWN
    if env.get("CURSOR_TRACE_ID") or env.get("CURSOR_AGENT"):
        return "cursor", version or UNKNOWN
    return "shell", version or UNKNOWN


def detect_harness(env: Mapping[str, str] | None = None) -> str:
    """Just the harness name for this process (`shell` when none is recognised)."""
    return _harness(os.environ if env is None else env)[0]


def _model_from_transcript(path: str) -> str:
    """The model named on the newest assistant entry of a Claude Code transcript. Reads only
    the tail, so a long session costs one seek, not a full scan."""
    try:
        p = Path(path)
        size = p.stat().st_size
        with p.open("rb") as f:
            f.seek(max(0, size - 256_000))
            tail = f.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(tail):
            if '"model"' not in line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            msg = obj.get("message") if isinstance(obj, dict) else None
            model = msg.get("model") if isinstance(msg, dict) else None
            if model and model != "<synthetic>":
                return str(model)
    except Exception:  # noqa: BLE001  # fail-soft: no transcript means unknown, never an error
        pass
    return ""


def _claude_transcript(session_id: str, cwd: str) -> str:
    """Where Claude Code keeps this session's transcript (`~/.claude/projects/<slug>/<id>.jsonl`).

    The slug is the directory the session was LAUNCHED in, which a worktree or a `cd` makes
    differ from the cwd -- so try the cwd's slug first, then any project folder."""
    if not session_id:
        return ""
    projects = Path.home() / ".claude" / "projects"
    slug = "".join(c if c.isalnum() else "-" for c in cwd)
    p = projects / slug / f"{session_id}.jsonl"
    if p.exists():
        return str(p)
    try:
        hit = next(projects.glob(f"*/{session_id}.jsonl"), None)
    except OSError:
        hit = None
    return str(hit) if hit else ""


def _model(env: Mapping[str, str], payload: Mapping[str, Any], session_id: str, cwd: str) -> str:
    for v in (payload.get("model"), env.get("AKASHIC_MODEL"), env.get("ANTHROPIC_MODEL")):
        if isinstance(v, dict):  # some payloads nest it: {"model": {"id": ...}}
            v = v.get("id") or v.get("display_name")
        if v:
            return str(v)
    transcript = str(payload.get("transcript_path") or "") or _claude_transcript(session_id, cwd)
    return _model_from_transcript(transcript) if transcript else ""


def _effort(env: Mapping[str, str], payload: Mapping[str, Any]) -> str:
    for v in (payload.get("effort"), env.get("AKASHIC_EFFORT"), env.get("CLAUDE_EFFORT")):
        if v:
            return str(v)
    return ""


def _hash_paths(base: Path, files: tuple[str, ...], dirs: tuple[str, ...] = ()) -> str:
    """A short, stable hash over the named files' bytes and the names in the named dirs.
    Missing files hash as absent, so adding one changes the fingerprint."""
    h = hashlib.sha256()
    for rel in files:
        p = base / rel
        h.update(rel.encode())
        try:
            h.update(p.read_bytes())
        except OSError:
            h.update(b"\0absent")
    for rel in dirs:
        p = base / rel
        h.update(rel.encode())
        try:
            for name in sorted(os.listdir(p)):
                h.update(name.encode())
                sub = p / name / "SKILL.md"
                if sub.exists():
                    h.update(sub.read_bytes())
        except OSError:
            h.update(b"\0absent")
    return h.hexdigest()[:16]


def project_fingerprint(cwd: str | Path) -> str:
    """Hash of the project's harness config: instruction files, settings, skills, subagents."""
    return _hash_paths(Path(cwd), _PROJECT_FILES, _PROJECT_DIRS)


def user_fingerprint(home: str | Path | None = None) -> str:
    """Hash of the user-level config. Kept apart from the project hash, because the same
    project config under two different user configs is two different harnesses."""
    return _hash_paths(Path(home) if home else Path.home(), _USER_FILES)


def _git(cwd: str, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=3, check=False
        ).stdout.strip()
        return out or UNKNOWN
    except Exception:  # noqa: BLE001  # fail-soft: not a repo, or no git
        return UNKNOWN


def detect(
    payload: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    session_id: str = "",
    agent_id: str = "",
) -> dict[str, str]:
    """Build a provenance record for the current process. Reads only; writes nothing."""
    payload = payload or {}
    env = os.environ if env is None else env
    cwd = str(payload.get("cwd") or os.getcwd())
    sid = session_id or str(payload.get("session_id") or "") or current_session_id(env)
    harness, version = _harness(env)
    return {
        "session_id": sid,
        "agent_id": agent_id or (env.get("AKASHIC_AGENT_ID") or "").strip() or UNKNOWN,
        "harness": harness,
        "harness_version": version,
        "model": _model(env, payload, sid, cwd) or UNKNOWN,
        "effort": _effort(env, payload) or UNKNOWN,
        "project_fingerprint": project_fingerprint(cwd),
        "user_fingerprint": user_fingerprint(),
        "git_sha": _git(cwd, "rev-parse", "HEAD"),
        "branch": _git(cwd, "rev-parse", "--abbrev-ref", "HEAD"),
        "os": platform.system().lower() or UNKNOWN,
        "cwd": cwd,
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _store(store=None):
    if store is not None:
        return store
    from core.foundation.store import create_store

    return create_store()


def get(session_id: str, *, store=None) -> dict[str, str] | None:
    """The stored record for a session, or None."""
    if not session_id:
        return None
    try:
        rec = _store(store).hgetall(pointer(session_id))
        return dict(rec) if rec else None
    except Exception:  # noqa: BLE001  # fail-soft: a down store reads as no record
        return None


def ensure(
    payload: Mapping[str, Any] | None = None,
    env: Mapping[str, str] | None = None,
    *,
    session_id: str = "",
    agent_id: str = "",
    mint: bool = False,
    store=None,
) -> dict[str, str]:
    """Write this session's record if it is missing, and fill `unknown` fields that are now
    known. Returns the record (empty dict when there is no session and `mint` is False).

    Idempotent: the first write keeps `started_at`, and a known field is never overwritten
    by a later `unknown`. The firehose gets one `provenance` event per session, at first write.

    `mint=True` makes up a session id when no harness names one, and exports it as
    `AKASHIC_SESSION_ID` so every child process (and every later call here) shares it.
    """
    env = os.environ if env is None else env
    sid = session_id or str((payload or {}).get("session_id") or "") or current_session_id(env)
    if not sid:
        if not mint:
            return {}
        sid = f"local-{uuid.uuid4().hex[:12]}"
        if env is os.environ:
            os.environ["AKASHIC_SESSION_ID"] = sid
    try:
        st = _store(store)
        have = get(sid, store=st) or {}
        if have and not any(have.get(f, UNKNOWN) == UNKNOWN for f in _FILLABLE):
            return have
        fresh = detect(payload, env, session_id=sid, agent_id=agent_id)
        if not have:
            st.hset(pointer(sid), mapping=fresh)
            _announce(fresh)
            return fresh
        merged = dict(have)
        for f in _FILLABLE:
            if merged.get(f, UNKNOWN) == UNKNOWN and fresh.get(f, UNKNOWN) != UNKNOWN:
                merged[f] = fresh[f]
        if merged != have:
            st.hset(pointer(sid), mapping=merged)
        return merged
    except Exception:  # noqa: BLE001  # fail-soft: provenance must never break its caller
        return {}


def _announce(rec: Mapping[str, str]) -> None:
    from core.events.event_log import capture_event

    capture_event(
        "provenance",
        f"PROVENANCE: {rec.get('harness')} {rec.get('model')} effort={rec.get('effort')}",
        agent_id=rec.get("agent_id") or UNKNOWN,
        session_id=rec.get("session_id") or "",
        refs=[pointer(rec.get("session_id") or "")],
        detail=dict(rec),
    )


def stamp(detail: dict[str, Any] | None = None, *, session_id: str = "") -> dict[str, Any]:
    """Add `session_id` and `prov` to an event detail or record, in place, and return it.
    The pointer is added only when a session is known, so old readers see no new noise."""
    detail = detail if detail is not None else {}
    sid = session_id or current_session_id()
    if sid:
        detail.setdefault("session_id", sid)
        detail.setdefault("prov", pointer(sid))
    return detail


def render(rec: Mapping[str, str]) -> str:
    """Plain-text view, one field per line."""
    if not rec:
        return "no provenance record (no session id in this process; pass --session <id>)"
    width = max(len(f) for f in FIELDS)
    return "\n".join(f"{f.ljust(width)}  {rec.get(f, UNKNOWN)}" for f in FIELDS)
