"""arsenal.panel.spec -- the ALLOWLIST, its validation, and the verb grammar.

This module is PURE: it reads one JSON file and returns frozen service specs. It starts nothing,
probes nothing and imports nothing from the rest of the house, so the whole grammar can be pinned
without touching a real daemon.

WHY AN ALLOWLIST OF FROZEN ARGV VECTORS, rather than a command string per service:

  * A request carries an `id` and a `verb`. It never carries a command, a flag, a path or an
    argument. There is no field in the request grammar that can hold one, so there is nothing to
    escape out of -- the injection surface is removed rather than filtered. Filters are the thing
    that gets it wrong once and is never noticed.
  * `subprocess` is called with the frozen LIST and `shell=False`. A vector that was a string would
    invite `shell=True` later, so a string is refused AT LOAD: `argv must be a list, not a string`.
  * The file is instance data (`local/phone-panel.json`), validated here. A typo therefore fails at
    start-up, loudly, naming the service -- rather than silently dropping a stop that then leaves a
    service Daniel cannot turn off from his phone.

FAIL LOUD ON LOAD, FAIL CLOSED ON USE. `load_specs` raises `SpecError` on any violation. A panel that
loaded a half-valid allowlist would be a panel that refused an action Daniel could see on screen,
which is worse than one that refused to start and said why.

LINES ARE NOT SPLIT. Every argv element is one argument exactly as it will arrive in the child. This
matters for the house's own services: `py -m arsenal serve --port 8796 --no-performance-log` is five
elements, not one string to be re-parsed by anything.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: The verbs a request may name. `restart` is spelled out rather than inferred so a client cannot
#: compose a sequence: the panel owns the order (stop, then start), the caller owns only the choice.
VERBS: Tuple[str, ...] = ("start", "stop", "restart")

#: Verbs that mean "this makes something stop, on a PC nobody is standing next to". These require a
#: confirm token (issued by a separate round-trip, see tokens.py) so a mis-tap on a phone screen is a
#: dialog rather than an outage.
CONFIRM_VERBS: Tuple[str, ...] = ("stop", "restart")

#: What a stop can be. Each is a DIFFERENT mechanism, named rather than inferred from a string:
#:   task_end     -- a scheduled task; `schtasks /End` lets the task end its own process tree
#:   task_run     -- the counterpart when a task's start IS its start (start-after-stop restart)
#:   service_stop -- a Windows service, through `net stop`/`sc stop`
#:   kill_argv    -- terminate the processes whose ARGV matches (never a substring of a joined cmdline)
#:   none         -- this service may be started here but must not be stopped here (the door says why)
STOP_KINDS: Tuple[str, ...] = ("task_end", "service_stop", "kill_argv", "none")

#: What a status probe can be:
#:   port    -- something answers a TCP connect on a loopback port
#:   argv    -- a process exists whose argv ELEMENTS match every string in `match`
#:   task    -- a scheduled task's state, read with `schtasks /query`
#:   service -- a Windows service's state
#:   absent  -- this thing is not expected on this PC at all (an honest "not installed")
PROBE_KINDS: Tuple[str, ...] = ("port", "argv", "task", "service", "absent")

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
_MAX_ARGV = 24
_MAX_ARG = 260
_MAX_LABEL = 60


class SpecError(ValueError):
    """The allowlist is malformed. Raised at load, naming the offending service."""


@dataclass(frozen=True)
class ServiceSpec:
    """One service the panel may act on, exactly as declared."""

    id: str
    label: str
    group: str
    probe: Dict[str, Any]
    start: Optional[Tuple[str, ...]] = None
    start_cwd: Optional[str] = None
    stop: Optional[Dict[str, Any]] = None
    log: Optional[str] = None
    status_only: bool = False
    why_no_actions: str = ""
    extra: Dict[str, Any] = field(default_factory=dict, compare=False)

    # ---------------------------------------------------------------- the verbs this service allows
    def allowed_verbs(self) -> Tuple[str, ...]:
        """Which of VERBS this service accepts -- derived from what it DECLARES, never guessed.

        A status-only service allows none: the house rule is that some things are watched and never
        touched from a phone (Rill's own DSH process, the Claude wake listener, the PhoneLink watcher
        whose restart would cut the phone off). Putting them on the screen is useful; putting a Stop
        button on them is not."""
        if self.status_only:
            return ()
        out: List[str] = []
        if self.start is not None:
            out.append("start")
            out.append("restart")           # restart = stop, then start; the panel owns the order
        if self.stop is not None and self.stop.get("type") != "none":
            out.append("stop")
            if self.start is not None and "restart" not in out:
                out.append("restart")
        return tuple(v for v in VERBS if v in out)

    def needs_confirm(self, verb: str) -> bool:
        return verb in CONFIRM_VERBS and verb in self.allowed_verbs()


# ------------------------------------------------------------------------------- validation
def _need(cond: bool, where: str, why: str) -> None:
    if not cond:
        raise SpecError(f"{where}: {why}")


def _string(value: Any, where: str, *, limit: int = _MAX_ARG, allow_empty: bool = False) -> str:
    _need(isinstance(value, str), where, f"must be a string, not {type(value).__name__}")
    if not allow_empty:
        _need(value.strip() != "", where, "must not be empty")
    _need("\x00" not in value, where, "must not contain a NUL byte")
    _need(len(value) <= limit, where, f"is longer than {limit} characters")
    return value


def _argv(value: Any, where: str) -> Tuple[str, ...]:
    """A frozen argv vector. A STRING IS REFUSED on purpose: a string is the shape that invites
    `shell=True` later, and it is also the shape that silently splits on a space inside a path."""
    _need(not isinstance(value, str), where,
          "argv must be a LIST of arguments, not a string (a string invites shell=True and "
          "splits on the spaces inside a path)")
    _need(isinstance(value, (list, tuple)), where, "argv must be a list of arguments")
    _need(len(value) > 0, where, "argv must not be empty")
    _need(len(value) <= _MAX_ARGV, where, f"argv has more than {_MAX_ARGV} elements")
    out = tuple(_string(a, f"{where}[{i}]") for i, a in enumerate(value))
    _need(bool(out[0].strip()), where, "argv[0] (the executable) must not be blank")
    return out


def _spec(raw: Dict[str, Any], index: int, root: str) -> ServiceSpec:
    where = f"services[{index}]"
    _need(isinstance(raw, dict), where, "must be an object")
    sid = _string(raw.get("id"), f"{where}.id", limit=40)
    _need(bool(_ID_RE.match(sid)), f"{where}.id",
          "must match ^[a-z0-9][a-z0-9._-]{0,39}$ (it is a URL field and a dict key; anything else "
          "invites a lookalike)")
    where = f"service {sid!r}"

    label = _string(raw.get("label", sid), f"{where}.label", limit=_MAX_LABEL)
    group = _string(raw.get("group", "services"), f"{where}.group", limit=40)

    probe = raw.get("probe")
    _need(isinstance(probe, dict), f"{where}.probe", "must be an object")
    kind = _string(probe.get("kind"), f"{where}.probe.kind", limit=20)
    _need(kind in PROBE_KINDS, f"{where}.probe.kind", f"must be one of {', '.join(PROBE_KINDS)}")
    probe = dict(probe)
    if kind == "port":
        port = probe.get("port")
        _need(isinstance(port, int) and not isinstance(port, bool), f"{where}.probe.port",
              "must be an integer")
        _need(1 <= port <= 65535, f"{where}.probe.port", "must be a real port")
        host = _string(probe.get("host", "127.0.0.1"), f"{where}.probe.host", limit=64)
        _need(host in ("127.0.0.1", "localhost", "::1"), f"{where}.probe.host",
              "the panel only probes loopback -- a probe that goes out to the LAN is a different "
              "question than 'is this service up on this PC'")
        probe["host"] = host
    elif kind == "argv":
        probe["match"] = list(_argv(probe.get("match"), f"{where}.probe.match"))
        _need(len(probe["match"]) > 0, f"{where}.probe.match", "needs at least one element")
    elif kind in ("task", "service"):
        probe["name"] = _string(probe.get("name"), f"{where}.probe.name", limit=120)
    elif kind == "absent":
        probe["why"] = _string(probe.get("why", "not installed on this PC"), f"{where}.probe.why",
                               limit=200)

    start = None
    start_cwd = None
    if raw.get("start") is not None:
        start = _argv(raw.get("start"), f"{where}.start")
        cwd = raw.get("start_cwd")
        if cwd is not None:
            start_cwd = _string(cwd, f"{where}.start_cwd", limit=260)
            _need(os.path.isabs(start_cwd), f"{where}.start_cwd",
                  "must be an absolute path -- a relative one resolves against wherever the panel "
                  "happened to be launched from, which is not a thing to leave to chance")
            _need(".." not in start_cwd.replace("\\", "/").split("/"), f"{where}.start_cwd",
                  "must not walk up with '..'")

    stop = None
    if raw.get("stop") is not None:
        raw_stop = raw.get("stop")
        _need(isinstance(raw_stop, dict), f"{where}.stop", "must be an object")
        stop = dict(raw_stop)
        stype = _string(stop.get("type"), f"{where}.stop.type", limit=20)
        _need(stype in STOP_KINDS, f"{where}.stop.type", f"must be one of {', '.join(STOP_KINDS)}")
        stop["type"] = stype
        if stype == "task_end":
            stop["name"] = _string(stop.get("name"), f"{where}.stop.name", limit=120)
        elif stype == "service_stop":
            stop["name"] = _string(stop.get("name"), f"{where}.stop.name", limit=120)
        elif stype == "kill_argv":
            stop["match"] = list(_argv(stop.get("match"), f"{where}.stop.match"))
            _need(len(stop["match"]) > 0, f"{where}.stop.match", "needs at least one element")
        elif stype == "none":
            stop["why"] = _string(stop.get("why", "stopping this from the phone is refused"),
                                  f"{where}.stop.why", limit=300)

    status_only = bool(raw.get("status_only"))
    why_no_actions = ""
    if status_only:
        why_no_actions = _string(raw.get("why_no_actions"),
                                 f"{where}.why_no_actions", limit=300)
        _need(start is None and (stop is None or stop.get("type") == "none"), where,
              "a status_only service must not declare a start or a real stop")

    log = None
    if raw.get("log") is not None:
        log = _string(raw.get("log"), f"{where}.log", limit=260)
        norm = log.replace("\\", "/")
        _need(".." not in norm.split("/"), f"{where}.log", "must not walk up with '..'")
        log = norm if os.path.isabs(norm) else os.path.join(root, norm)

    known = {"id", "label", "group", "probe", "start", "start_cwd", "stop", "log",
             "status_only", "why_no_actions"}
    return ServiceSpec(id=sid, label=label, group=group, probe=probe, start=start,
                       start_cwd=start_cwd, stop=stop, log=log, status_only=status_only,
                       why_no_actions=why_no_actions,
                       extra={k: v for k, v in raw.items() if k not in known})


def load_document(path: str, root: Optional[str] = None):
    """Read the allowlist AND its non-service sections. Returns (specs, meta).

    `meta` carries the things that are not services but are still instance facts:
      * `video`  -- the Artemis deep link and Apollo's web address (declared, never guessed: an app's
                    URL scheme is a fact about that app on that phone, and a guess ships a dead button);
      * `panel`  -- the agent id and session the link card reports, and an optional confirm TTL.
    A fork with no `video` section gets a video card that says so, which is the honest answer."""
    specs, meta = _load(path, root)
    return specs, meta


def load_specs(path: str, root: Optional[str] = None) -> Dict[str, ServiceSpec]:
    """The allowlist alone. Raises SpecError on ANY violation, naming the offender."""
    return _load(path, root)[0]


def _load(path: str, root: Optional[str]):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        raise SpecError(
            f"no allowlist at {path}. The panel refuses to start with an EMPTY allowlist: an empty "
            f"list and a list that failed to load look identical from the API, and one of them means "
            f"'nothing is controllable' while the other means 'someone is about to wonder why the "
            f"buttons do nothing'.")
    except ValueError as exc:
        raise SpecError(f"the allowlist at {path} is not valid JSON: {exc}")
    _need(isinstance(doc, dict), path, "the allowlist must be a JSON object")
    rows = doc.get("services")
    _need(isinstance(rows, list) and len(rows) > 0, f"{path}.services",
          "must be a non-empty list")
    base = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out: Dict[str, ServiceSpec] = {}
    for i, raw in enumerate(rows):
        spec = _spec(raw, i, base)
        _need(spec.id not in out, f"service {spec.id!r}",
              "is declared twice -- a duplicate id would make the second row unreachable and the "
              "first one ambiguous")
        out[spec.id] = spec
    meta = {k: v for k, v in doc.items() if k not in ("services",) and not k.startswith("_")}
    return out, meta


def as_dict(spec: ServiceSpec) -> Dict[str, Any]:
    """The spec as the API reports it: what a client may know, with no argv leaked.

    ARGV IS NOT IN THE RESPONSE, deliberately. The phone does not need to know how a service is
    started, and a response that carries the command is a response that can be read off a shoulder
    or out of a browser history. The ids and the verbs are the whole contract."""
    return {"id": spec.id, "label": spec.label, "group": spec.group,
            "actions": list(spec.allowed_verbs()),
            "confirm": [v for v in CONFIRM_VERBS if spec.needs_confirm(v)],
            "status_only": spec.status_only,
            "why_no_actions": spec.why_no_actions}
