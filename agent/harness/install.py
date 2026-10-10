"""Hook installer: register Aurora's harness hooks at USER or PROJECT scope, and turn them off/on.

The door is `agent_cli.py hooks <status|install|uninstall|enable|disable>` (and the `setup`
onboarding, which calls into this module). What gets registered is data:
agent/harness/registry.py::HOOK_SPECS. Every hook runs from agent/harness/hooks/, the one hook tree.

Targets, per harness and scope:
  claude  user     ~/.claude/settings.json
          project  <project>/.claude/settings.local.json   (personal, gitignored -- the default)
                   <project>/.claude/settings.json         (with --shared: committed for everyone)
  codex   user     ~/.codex/hooks.json          project  <project>/.codex/hooks.json
  cursor  user     ~/.cursor/hooks.json         project  <project>/.cursor/hooks.json

Rules this module keeps:
  * OURS vs FOREIGN. An entry is ours iff its command runs a file under agent/harness/hooks/ or
    scripts/hooks/. Install, uninstall, enable and disable touch ours only; every other hook and
    every other settings key survives byte-for-byte in meaning (key order is preserved).
  * ONE SURFACE PER HOOK (test_k0_gauge_truth, failure-ledger C8-3). A Claude hook registered in
    two settings files double-fires and double-counts recall. Install SKIPS an (event, script)
    already registered in another Claude settings file in play, and says where it is.
  * DISABLE IS REVERSIBLE. Disable moves our entries out to a sidecar
    (<data_root>/state/harness/hooks-disabled.json); enable puts them back exactly, so a matcher
    someone hand-edited survives the round trip.
  * WRITES ARE ATOMIC, and the first change to a file leaves a `.bak` beside it.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.harness.registry import CURSOR_FAIL_CLOSED, HOOK_SPECS

HARNESS_NAMES = tuple(HOOK_SPECS)
SCOPES = ("user", "project")
_OURS = re.compile(r"(?:agent[\\/]+harness[\\/]+hooks|scripts[\\/]+hooks)[\\/]+([A-Za-z0-9_]+\.py)")
_STALE = re.compile(r"scripts[\\/]+hooks[\\/]+")


# ----------------------------------------------------------------------------- paths
def _repo() -> Path:
    from core.paths import repo_root

    return repo_root().resolve()


def _posix(p: Path | str) -> str:
    return str(p).replace("\\", "/")


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def target_file(harness: str, scope: str, project: str | os.PathLike | None = None, shared: bool = False) -> Path:
    """The config file a (harness, scope) install writes."""
    if harness not in HOOK_SPECS:
        raise ValueError(f"unknown harness {harness!r} (one of: {', '.join(HARNESS_NAMES)})")
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r} (user | project)")
    base = _home() if scope == "user" else Path(project or os.getcwd()).resolve()
    if harness == "claude":
        if scope == "user":
            return base / ".claude" / "settings.json"
        return base / ".claude" / ("settings.json" if shared else "settings.local.json")
    return base / f".{harness}" / "hooks.json"


def claude_files_in_play(project: str | os.PathLike | None = None) -> list[Path]:
    """Every Claude settings file whose hooks fire together for a session in `project`
    (default: this repo). Used for the one-surface rule."""
    proj = Path(project).resolve() if project else _repo()
    return [
        _home() / ".claude" / "settings.json",
        proj / ".claude" / "settings.json",
        proj / ".claude" / "settings.local.json",
    ]


# ----------------------------------------------------------------------------- commands
def _project_is_repo(scope: str, project) -> bool:
    return scope == "project" and Path(project or os.getcwd()).resolve() == _repo()


def hook_command(harness: str, script: str, scope: str, project=None, os_name: str | None = None) -> str:
    """The command line a harness runs for one hook script (script may carry trailing args)."""
    os_name = os_name or os.name
    name, _, extra = script.partition(" ")
    tail = f" {extra}" if extra else ""
    in_repo = _project_is_repo(scope, project)
    if harness == "claude":
        root = "$CLAUDE_PROJECT_DIR" if in_repo else _posix(_repo())
        path = f"{root}/agent/harness/hooks/{name}"
        if shutil.which("uv") or os_name == "nt":
            # uvw ships with uv on Windows and runs without a console window (--gui-script);
            # elsewhere it falls back to plain uv. --project finds the locked env from any cwd.
            return (
                f'AI_SETUP="{root}" $(command -v uvw || command -v uv) run --project "{root}" '
                f'-p 3.12 --gui-script "{path}"{tail}'
            )
        return f'AI_SETUP="{root}" python3 "{path}"{tail}'
    # codex / cursor run the command from the project root: keep committed files relative.
    if in_repo:
        return f"uv run agent/harness/hooks/{name}{tail}"
    root = _posix(_repo())
    return f'uv run --project "{root}" "{root}/agent/harness/hooks/{name}"{tail}'


# ----------------------------------------------------------------------------- json io
def read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    if not text.strip():
        return {}
    doc = json.loads(text)  # a broken file must stop us, never be overwritten
    if not isinstance(doc, dict):
        raise ValueError(f"{path} is not a JSON object")
    return doc


def write_config(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bak = path.with_name(path.name + ".bak")
    if path.exists() and not bak.exists():
        shutil.copy2(path, bak)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def sidecar_path() -> Path:
    from core.paths import data_root

    return Path(data_root()) / "state" / "harness" / "hooks-disabled.json"


def _sidecar_load() -> dict[str, list]:
    try:
        return read_config(sidecar_path())
    except Exception:
        return {}


def _sidecar_save(doc: dict[str, list]) -> None:
    p = sidecar_path()
    if doc:
        write_config(p, doc)
    elif p.exists():
        p.unlink()


# ----------------------------------------------------------------------------- entries
def script_of(command: str) -> str | None:
    """The hook script an entry runs, if it is one of ours."""
    m = _OURS.search(command or "")
    return m.group(1) if m else None


def _entries(doc: dict, harness: str):
    """Yield (event, matcher, entry) for every hook in a config document."""
    for event, groups in (doc.get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for g in groups:
            if not isinstance(g, dict):
                continue
            if harness == "cursor":
                yield event, g.get("matcher"), g
            else:
                for h in g.get("hooks") or []:
                    if isinstance(h, dict):
                        yield event, g.get("matcher"), h


def _strip_ours(doc: dict, harness: str) -> list[dict]:
    """Remove our entries in place; return them as sidecar records."""
    removed: list[dict] = []
    hooks = doc.get("hooks")
    if not isinstance(hooks, dict):
        return removed
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for g in groups:
            if not isinstance(g, dict):
                kept_groups.append(g)
                continue
            if harness == "cursor":
                if script_of(g.get("command", "")):
                    removed.append({"event": event, "entry": g})
                else:
                    kept_groups.append(g)
                continue
            keep = []
            for h in g.get("hooks") or []:
                if isinstance(h, dict) and script_of(h.get("command", "")):
                    removed.append({"event": event, "matcher": g.get("matcher"), "entry": h})
                else:
                    keep.append(h)
            if keep:
                kept_groups.append({**g, "hooks": keep})
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    if not hooks and "hooks" in doc:
        # Cursor's file is ours end to end; keep its version key but drop an empty hooks map.
        del doc["hooks"]
    return removed


def _add(doc: dict, harness: str, event: str, matcher: str | None, entry: dict) -> None:
    hooks = doc.setdefault("hooks", {})
    groups = hooks.setdefault(event, [])
    if harness == "cursor":
        groups.append(entry)
        return
    for g in groups:
        if isinstance(g, dict) and g.get("matcher") == matcher:
            g.setdefault("hooks", []).append(entry)
            return
    group: dict[str, Any] = {} if matcher is None else {"matcher": matcher}
    group["hooks"] = [entry]
    groups.append(group)


def _spec_entry(harness: str, script: str, matcher: str | None, scope: str, project) -> dict:
    cmd = hook_command(harness, script, scope, project)
    if harness == "cursor":
        e: dict[str, Any] = {"command": cmd}
        if matcher is not None:
            e["matcher"] = matcher
        if script.split(" ")[0] in CURSOR_FAIL_CLOSED:
            e["failClosed"] = True
        return e
    return {"type": "command", "command": cmd}


def _registered(path: Path, harness: str) -> set[tuple[str, str]]:
    try:
        doc = read_config(path)
    except Exception:
        return set()
    return {(ev, s) for ev, _, e in _entries(doc, harness) if (s := script_of(e.get("command", "")))}


# ----------------------------------------------------------------------------- actions
@dataclass
class Result:
    path: Path
    action: str
    changed: bool = False
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "path": str(self.path)}


def _label(rec_event: str, entry: dict) -> str:
    return f"{rec_event}:{script_of(entry.get('command', '')) or '?'}"


def install(harness, scope, project=None, shared=False, dry_run=False) -> Result:
    """(Re)write our hooks into one file. Idempotent; foreign hooks untouched."""
    path = target_file(harness, scope, project, shared)
    res = Result(path, "install")
    doc = read_config(path)
    before = json.dumps(doc, sort_keys=True)
    old = {_label(r["event"], r["entry"]): r["entry"].get("command") for r in _strip_ours(doc, harness)}
    elsewhere: dict[tuple[str, str], Path] = {}
    if harness == "claude":
        # A user-level hook fires in every project, so compare against this repo AND the cwd's
        # project; a project install compares against the user file and its own siblings.
        projects = [project] if scope == "project" else [None, os.getcwd()]
        for proj in projects:
            for other in claude_files_in_play(proj):
                if other.resolve() != path.resolve():
                    for key in _registered(other, harness):
                        elsewhere.setdefault(key, other)
    for event, matcher, script in HOOK_SPECS[harness]:
        name = script.split(" ")[0]
        where = elsewhere.get((event, name))
        if where is not None:
            res.skipped.append(f"{event}:{name} (already in {where})")
            continue
        entry = _spec_entry(harness, script, matcher, scope, project)
        _add(doc, harness, event, matcher, entry)
        label = f"{event}:{name}"
        if old.pop(label, None) != entry["command"]:
            res.added.append(label)  # new, or its command changed
    res.removed = sorted(old)  # ours before, not part of the spec any more (or now skipped)
    if harness == "cursor":
        doc.setdefault("version", 1)
    side = _sidecar_load()
    if str(path) in side:
        res.notes.append("dropped a stale disabled-hooks record for this file (install supersedes it)")
        if not dry_run:
            side.pop(str(path))
            _sidecar_save(side)
    res.changed = json.dumps(doc, sort_keys=True) != before
    if res.changed and not dry_run:
        write_config(path, doc)
    return res


def uninstall(harness, scope, project=None, shared=False, dry_run=False) -> Result:
    path = target_file(harness, scope, project, shared)
    res = Result(path, "uninstall")
    if not path.exists():
        res.notes.append("nothing to do: file does not exist")
        return res
    doc = read_config(path)
    res.removed = [_label(r["event"], r["entry"]) for r in _strip_ours(doc, harness)]
    res.changed = bool(res.removed)
    side = _sidecar_load()
    if str(path) in side and not dry_run:
        side.pop(str(path))
        _sidecar_save(side)
        res.notes.append("cleared its disabled-hooks record")
    if res.changed and not dry_run:
        write_config(path, doc)
    return res


def disable(harness, scope, project=None, shared=False, dry_run=False) -> Result:
    path = target_file(harness, scope, project, shared)
    res = Result(path, "disable")
    if not path.exists():
        res.notes.append("nothing to do: file does not exist")
        return res
    doc = read_config(path)
    removed = _strip_ours(doc, harness)
    if not removed:
        res.notes.append("nothing to disable: no Aurora hooks in this file")
        return res
    res.removed = [_label(r["event"], r["entry"]) for r in removed]
    res.changed = True
    if not dry_run:
        side = _sidecar_load()
        side[str(path)] = side.get(str(path), []) + [{**r, "harness": harness} for r in removed]
        _sidecar_save(side)
        write_config(path, doc)
    return res


def enable(harness, scope, project=None, shared=False, dry_run=False) -> Result:
    path = target_file(harness, scope, project, shared)
    res = Result(path, "enable")
    side = _sidecar_load()
    recs = side.get(str(path)) or []
    if not recs:
        res.notes.append(
            "nothing to enable: no disabled hooks recorded for this file "
            f"(to register fresh, run: agent_cli.py hooks install --harness {harness} --scope {scope})"
        )
        return res
    doc = read_config(path)
    have = {(ev, script_of(e.get("command", ""))) for ev, _, e in _entries(doc, harness)}
    for r in recs:
        key = (r["event"], script_of(r["entry"].get("command", "")))
        if key in have:
            res.skipped.append(f"{key[0]}:{key[1]} (already present)")
            continue
        _add(doc, harness, r["event"], r.get("matcher"), r["entry"])
        res.added.append(f"{key[0]}:{key[1]}")
    res.changed = bool(res.added)
    if not dry_run:
        side.pop(str(path), None)
        _sidecar_save(side)
        if res.changed:
            write_config(path, doc)
    return res


ACTIONS = {"install": install, "uninstall": uninstall, "enable": enable, "disable": disable}


# ----------------------------------------------------------------------------- status
def status(project=None) -> list[dict[str, Any]]:
    """One row per (harness, scope file): installed / disabled / stale / foreign counts."""
    side = _sidecar_load()
    rows = []
    proj = Path(project).resolve() if project else _repo()
    plan = [("claude", "user", False), ("claude", "project", True), ("claude", "project", False)]
    plan += [(h, s, False) for h in HARNESS_NAMES if h != "claude" for s in SCOPES]
    for harness, scope, shared in plan:
        path = target_file(harness, scope, proj, shared)
        row: dict[str, Any] = {
            "harness": harness,
            "scope": scope + (" (shared)" if shared else ""),
            "path": str(path),
            "exists": path.exists(),
            "installed": [],
            "stale": [],
            "foreign": 0,
            "disabled": len(side.get(str(path)) or []),
            "missing": [],
            "error": "",
        }
        try:
            doc = read_config(path)
        except Exception as e:  # report, never crash the status view
            row["error"] = f"{type(e).__name__}: {e}"
            rows.append(row)
            continue
        for ev, _, e in _entries(doc, harness):
            cmd = e.get("command", "")
            s = script_of(cmd)
            if not s:
                row["foreign"] += 1
            elif _STALE.search(cmd):
                row["stale"].append(f"{ev}:{s}")
            else:
                row["installed"].append(f"{ev}:{s}")
        rows.append(row)
    # `missing` is judged per harness across ALL its files: a Claude hook held by the user file
    # is not missing from the project just because the project file lacks it (one surface each).
    for harness in HARNESS_NAMES:
        mine = [r for r in rows if r["harness"] == harness]
        have = {x for r in mine for x in r["installed"] + r["stale"]}
        if have:
            want = {f"{ev}:{s.split(' ')[0]}" for ev, _, s in HOOK_SPECS[harness]}
            gap = sorted(want - have)
            holder = next(r for r in mine if r["installed"] or r["stale"])
            holder["missing"] = gap
    return rows


def status_lines(project=None, only_present: bool = True) -> list[str]:
    """Human status, each problem paired with the command that fixes it."""
    out = []
    for r in status(project):
        if only_present and not (r["exists"] and (r["installed"] or r["stale"] or r["disabled"] or r["error"])):
            continue
        scope_flag = "--scope " + r["scope"].split(" ")[0] + (" --shared" if "shared" in r["scope"] else "")
        head = f"{r['harness']:<7} {r['scope']:<16} {r['path']}"
        if r["error"]:
            out.append(
                f"{head}\n    UNREADABLE: {r['error']} -- fix the JSON by hand; the installer will not overwrite it"
            )
            continue
        state = f"{len(r['installed'])} installed"
        if r["disabled"]:
            state += f", {r['disabled']} disabled"
        if r["foreign"]:
            state += f", {r['foreign']} other hook(s) left alone"
        out.append(f"{head}\n    {state}")
        if r["stale"]:
            out.append(
                f"    {len(r['stale'])} via the old scripts/hooks/ shim path -- still works; to modernise: "
                f"agent_cli.py hooks install --harness {r['harness']} {scope_flag}"
            )
        if r["disabled"] and not r["installed"]:
            out.append(f"    turn back on: agent_cli.py hooks enable --harness {r['harness']} {scope_flag}")
        if r["missing"]:
            out.append(
                f"    not registered in any {r['harness']} file: {', '.join(r['missing'])} "
                f"(fix: agent_cli.py hooks install --harness {r['harness']}"
                + (" --scope user)" if r["harness"] == "claude" else f" {scope_flag})")
            )
    if not out:
        out.append("no Aurora hooks are registered anywhere. Run: agent_cli.py setup  (or: agent_cli.py hooks install)")
    return out
