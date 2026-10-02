"""touch.v1 -- what a seat actually touched, as one record the spine can join.

SPEC: W0.2 of `fences/context-system/reconciliation.md` section 4, as folded by
      `fences/one-spine/reconciliation.md`. PINS: `tests/test_touch_v1.py`.
BUILDS ON: `core/coord/target.py` (W0.1, `context.target.v1`).

WHY, as a number rather than a claim. Scanned `events:raw` the night this was written, 6,918
records: 89 carry a `session_id` and all 89 are a single kind. Every kind the hook emits -- `fail`,
`file_edit`, `command`, `flip`, `observation` -- carries none. So the house's own firehose cannot
answer "what was THIS seat, in THIS incarnation, doing at 03:12", which is the first question
anyone asks it. This module exists to make the answer a join instead of an archaeology.

IT ABSORBS GAP 3 of the record-is-total map, and that is a ruling, not an optimisation: a hook
firing IS the idle-to-active transition, so there is no separate `activity` kind. One fact on the
spine twice under two names would be a second writer for one transition, which is the rival
assembler both maps warn about.

TWO LAWS THIS MODULE IS BUILT AROUND, because it runs on the hot path of every seat:

  1. IT NEVER RAISES INTO THE HOOK. Every entry point returns None on any failure and increments a
     drop counter. A telemetry builder that can raise is a telemetry builder that can wedge the
     house. But a swallowed failure that is not COUNTED is just a lie with better manners, so the
     counter is not optional -- W0.4 reads it.
  2. NOTHING RAW IS STORED. Not the command text, not file contents, not a URL's query. The record
     carries what was touched and how, never what was said. `wire_journal`'s metadata-only doctrine
     and Daniel's D1 ("lets do the pointer") are the same rule, and this is the third door that
     obeys it.

NULL IS NOT EMPTY, and the schema keeps the distinction in both places (Navi, amendment B5):
`targets: None` means the command could not be seen into; `targets: []` means it was read and
touched nothing. Collapsing them is this house's "zero is not no" failure with a JSON accent.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

SCHEMA = "touch.v1"
KIND = "touch"

#: A cap, confessed rather than silent (`targets_total` + `targets_truncated` always ride along).
#: 32 is chosen as the smallest bound that covers ordinary work -- a glob-heavy command or a
#: multi-file edit rarely names more -- while keeping one record comfortably inside the event
#: store's per-record detail budget. The number is a measurement waiting to happen: W0.4 prices
#: real touches for 24 h, and if the truncated share is not near zero this is the knob to move.
MAX_TARGETS = 32

#: The tools the spec names, with the ACTION each one means. A file tool's action is known from the
#: tool itself; a shell tool's has to be extracted from the command, which is the hard case and
#: belongs to `context.target.v1`'s extraction contract rather than here.
_FILE_ACTIONS: Dict[str, str] = {
    "Read": "read", "NotebookRead": "read",
    "Edit": "write", "Write": "write", "NotebookEdit": "write",
}
_SHELL_TOOLS = {"Bash": "bash", "PowerShell": "powershell"}
_SEARCH_TOOLS = {"Grep", "Glob"}
_URL_TOOLS = {"WebFetch", "WebSearch"}

_drops = 0

#: The drop counter has to be DURABLE, and that is not a nicety -- it is the difference between a
#: counter and a decoration. This module's main caller is a PostToolUse hook, which is a fresh
#: short-lived process per tool call, so an in-process integer resets before anyone could read it
#: and would report zero forever while dropping every touch. Found by the wiring gate refusing
#: `drops()` as a public function nothing calls: asking who the reader was is what exposed that
#: there could not BE one.
#:
#: A file rather than Redis on purpose: drops happen exactly when something is wrong, and the store
#: being unreachable is one of the things that can be wrong. A counter that needs the thing it is
#: watching is a counter that goes quiet in the only situation it exists for.
def _drop_file() -> str:
    import tempfile
    return os.path.join(os.getenv("AKASHIC_TOUCH_DROPS_DIR") or tempfile.gettempdir(),
                        "akashic_touch_drops.txt")


def _bump_drop() -> None:
    global _drops
    _drops += 1
    try:
        p = _drop_file()
        n = 0
        try:
            with open(p, encoding="utf-8") as f:
                n = int((f.read() or "0").strip() or 0)
        except (OSError, ValueError):
            n = 0
        with open(p, "w", encoding="utf-8") as f:
            f.write(str(n + 1))
    except Exception:                                                     # noqa: BLE001
        pass          # the end of the line: if even this fails we are silent, and nothing is left


def drops() -> int:
    """How many touches have been dropped on this machine. Read by the doctor, so a swallowed
    failure is a line someone sees rather than a number nobody holds. Counts the durable file
    (the hook's drops, across its one-process-per-call lifetime) and this process's own."""
    try:
        with open(_drop_file(), encoding="utf-8") as f:
            return int((f.read() or "0").strip() or 0)
    except (OSError, ValueError):
        return _drops


@dataclass(frozen=True)
class Touch:
    kind: str
    summary: str
    session_id: str
    agent_id: str
    detail: Dict[str, Any]
    refs: List[str] = field(default_factory=list)


def _session_of(payload: Dict[str, Any]) -> tuple:
    """PAYLOAD FIRST, env only as a fallback, and the source is recorded either way.

    The environment is ambient: it inherits from parents and siblings, so resolving a seat from it
    first silently attributes one session's work to another. The payload's `session_id` is ground
    truth for who made this call. When neither exists the touch is still emitted -- an
    unattributable touch is a real fact about the house -- but it must not be indistinguishable
    from an attributed one, which is the same discipline T418-b landed for an unverified boot."""
    sid = str(payload.get("session_id") or "").strip()
    if sid:
        return sid, "payload"
    for var in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        v = str(os.getenv(var) or "").strip()
        if v:
            return v, "env"
    return "", "unknown"


def _agent_of() -> str:
    try:
        from core.comm import seat_identity as _si
        sid = os.getenv("CLAUDE_CODE_SESSION_ID") or ""
        return _si.resolve(sid) if hasattr(_si, "resolve") else (os.getenv("AKASHIC_AGENT_ID") or "")
    except Exception:                                                     # noqa: BLE001
        return str(os.getenv("AKASHIC_AGENT_ID") or "")


def _as_row(action: str, tgt, role: Optional[str] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {"action": action, "key": tgt.key, "kind": tgt.kind}
    if tgt.work:
        row["work"] = tgt.work
    if tgt.line is not None:
        row["line"] = tgt.line
    if role:
        row["role"] = role
    return row


def build(payload: Dict[str, Any], *, roots: Any, exists: Optional[Callable[[str], bool]] = None,
          exists_all: bool = False) -> Optional[Touch]:
    """One PostToolUse payload -> one touch record, or None (counted) if anything goes wrong.

    Pure: takes the payload, the roots and an existence callable. No disk, no Redis, no git."""
    try:
        from core.coord import target as T

        tool = str(payload.get("tool_name") or "")
        ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
        cwd = str(payload.get("cwd") or "") or None
        ex = (lambda _k: True) if exists_all else (exists or (lambda _k: False))

        rows: Optional[List[Dict[str, Any]]] = []
        incomplete = False
        total = 0

        if tool in _FILE_ACTIONS:
            action = _FILE_ACTIONS[tool]
            p = str(ti.get("file_path") or ti.get("notebook_path") or "").strip()
            if p:
                rows = [_as_row(action, T.parse(p, roots=roots, cwd=cwd, exists=ex))]
            total = len(rows or [])

        elif tool in _SHELL_TOOLS:
            ext = T.extract(str(ti.get("command") or ""), shell=_SHELL_TOOLS[tool],
                            cwd=cwd, roots=roots, exists=ex)
            incomplete = bool(ext.incomplete)
            if ext.targets is None:
                rows = None                      # could not see in; NOT the same as "nothing"
            else:
                total = len(ext.targets)
                rows = [_as_row(t.action, t.target, t.role) for t in ext.targets[:MAX_TARGETS]]

        elif tool in _SEARCH_TOOLS:
            p = str(ti.get("path") or ti.get("pattern") or "").strip()
            try:
                rows = [_as_row("search", T.parse(p, roots=roots, cwd=cwd, exists=ex))] if p else []
            except T.TargetError:
                rows = []                        # a bare regex is not a location, and that is fine
            total = len(rows)

        elif tool in _URL_TOOLS:
            u = str(ti.get("url") or "").strip()
            # The URL's PATH is the anchor; a query string can carry secrets and is dropped whole.
            u = u.split("?", 1)[0].split("#", 1)[0]
            rows = [_as_row("read", T.parse(u, roots=roots, exists=ex))] if u.startswith("http") else []
            total = len(rows)

        else:
            return None                          # an unlisted tool is not a touch

        detail: Dict[str, Any] = {
            "schema": SCHEMA,
            "harness": "claude-code",
            "tool": tool,
            "targets": rows,
            "targets_total": total,
            "targets_truncated": bool(rows is not None and total > len(rows)),
            "targets_incomplete": incomplete,
        }
        if cwd:
            try:
                detail["cwd"] = T.parse(cwd.rstrip("/\\") + "/", roots=roots, exists=ex).key
            except T.TargetError:
                detail["cwd_outside_known_roots"] = True

        sid, src = _session_of(payload)
        detail["session_source"] = src

        n = len(rows) if rows is not None else 0
        refs = [r["key"] for r in (rows or [])][:MAX_TARGETS]
        summary = f"{tool}: {n} target(s)" if rows is not None else f"{tool}: targets unknown"

        return Touch(kind=KIND, summary=summary, session_id=sid, agent_id=_agent_of(),
                     detail=detail, refs=refs)

    except Exception:                                                     # noqa: BLE001
        # The hot path of every seat runs through here. Never raise; always count.
        _bump_drop()
        return None


def emit(payload: Dict[str, Any], *, roots: Any = None,
         exists: Optional[Callable[[str], bool]] = None) -> bool:
    """Build a touch and put it on the spine. Returns whether a record landed. Never raises.

    The default roots are resolved HERE rather than by the hook, so the caller stays one line and
    the expensive lookup (`git worktree list`) is cached per process in one place."""
    try:
        t = build(payload, roots=roots if roots is not None else default_roots(),
                  exists=exists if exists is not None else _repo_exists)
        if t is None:
            return False
        from core.events.event_log import capture_event
        capture_event(t.kind, t.summary, agent_id=t.agent_id, session_id=t.session_id,
                      detail=t.detail, refs=t.refs)
        return True
    except Exception:                                                     # noqa: BLE001
        _bump_drop()
        return False


_ROOTS_CACHE: list = []


def default_roots():
    """`git worktree list` once per process, never once per touch. The spec prices it this way."""
    if _ROOTS_CACHE:
        return _ROOTS_CACHE[0]
    from core.coord import target as T
    from core import paths
    main = str(paths.repo_root())
    trees: List[str] = []
    try:
        import subprocess
        out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=main,
                             capture_output=True, text=True, timeout=10).stdout
        trees = [ln.split(" ", 1)[1].strip() for ln in out.splitlines()
                 if ln.startswith("worktree ")]
    except Exception:                                                     # noqa: BLE001
        trees = []                               # no worktrees known is a degraded read, not a crash
    r = T.Roots(main=main, worktrees=tuple(t for t in trees if t), resolve_sha=None)
    _ROOTS_CACHE.append(r)
    return r


def _repo_exists(key: str) -> bool:
    try:
        from core import paths
        return os.path.exists(os.path.join(str(paths.repo_root()), key.replace("/", os.sep)))
    except Exception:                                                     # noqa: BLE001
        return False
