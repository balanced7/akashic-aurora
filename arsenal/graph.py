"""arsenal.graph/v0: load, validate and write media graphs (contract §4.3).

JSON is the canonical form. parse_text() reads the one-line-per-statement text form and returns
that same JSON. Validation refuses at connect time and says why in words a person can act on.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from . import GRAPH_API
from .mediatypes import PRODUCER_TYPES, check_caps
from .registry import Registry, load_registry

MODES = ("live_audio", "live_silent", "offline", "edit")

_NAME = r"[A-Za-z_][A-Za-z0-9_-]*"
_NAME_RE = re.compile(rf"^{_NAME}$")


class GraphError(ValueError):
    def __init__(self, problems: List[str]):
        super().__init__("; ".join(problems) if problems else "invalid graph")
        self.problems = list(problems)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _split(endpoint) -> Tuple[str, str, Optional[str]]:
    """'node.port' or 'node.port.feature' -> (node, port, feature or None)."""
    parts = str(endpoint).split(".")
    if len(parts) not in (2, 3) or not all(_NAME_RE.match(p) for p in parts):
        raise GraphError([f"endpoint {endpoint!r} must look like node.port or node.port.feature"])
    return parts[0], parts[1], (parts[2] if len(parts) == 3 else None)


@dataclass
class Graph:
    api: str
    name: str
    mode: str
    assets: Dict[str, dict]
    nodes: Dict[str, dict]
    edges: List[Tuple[str, str]]
    bindings: List[dict]

    def to_json(self) -> dict:
        return {
            "api": self.api, "name": self.name, "mode": self.mode,
            "assets": copy.deepcopy(self.assets), "nodes": copy.deepcopy(self.nodes),
            "edges": [list(e) for e in self.edges], "bindings": copy.deepcopy(self.bindings),
        }

    def module_of(self, node: str) -> Optional[str]:
        return (self.nodes.get(node) or {}).get("use")

    def node_edges(self) -> List[Tuple[str, str]]:
        """Edges as (source node, destination node) pairs."""
        return [(src.split(".")[0], dst.split(".")[0]) for src, dst in self.edges]

    # ---------------------------------------------------------------- validation
    def validate(self, registry: Registry) -> List[str]:
        problems: List[str] = []
        if self.mode not in MODES:
            problems.append(f"mode {self.mode!r} is not one of {', '.join(MODES)}")

        known: Dict[str, str] = {}
        for name, node in self.nodes.items():
            use = (node or {}).get("use")
            if not use:
                problems.append(f"node {name!r} does not say which module it uses")
                continue
            try:
                registry.get(use)
            except KeyError:
                problems.append(f"node {name!r} uses unknown module {use!r}")
                continue
            known[name] = use

        feeds: Dict[str, List[str]] = {}
        for src, dst in self.edges:
            out_port = self._edge_port(src, "outputs", known, registry, problems, f"edge {src} -> {dst}")
            in_port = self._edge_port(dst, "inputs", known, registry, problems, f"edge {src} -> {dst}")
            if out_port is None or in_port is None:
                continue
            feeds.setdefault(dst, []).append(src)
            if out_port["type"] != in_port["type"]:
                problems.append(f"edge {src} -> {dst}: type mismatch: {src} gives {out_port['type']} "
                                f"but {dst} needs {in_port['type']}")
                continue
            for reason in check_caps(out_port.get("caps"), in_port.get("caps")):
                problems.append(f"edge {src} -> {dst}: caps {reason}")
        for dst, sources in feeds.items():
            if len(sources) > 1:
                problems.append(f"input {dst} is connected more than once (from {', '.join(sources)})")

        cycle = self._find_cycle()
        if cycle:
            problems.append(f"the graph has a cycle: {' -> '.join(cycle)}")

        for binding in self.bindings:
            self._check_binding(binding, known, registry, problems)
        return problems

    def require_valid(self, registry: Registry) -> "Graph":
        problems = self.validate(registry)
        if problems:
            raise GraphError(problems)
        return self

    def _edge_port(self, endpoint, side, known, registry, problems, label) -> Optional[dict]:
        try:
            node, port, feature = _split(endpoint)
        except GraphError as exc:
            problems.extend(f"{label}: {p}" for p in exc.problems)
            return None
        if feature:
            problems.append(f"{label}: {endpoint} names a feature; edges connect ports")
            return None
        if node not in self.nodes:
            problems.append(f"{label}: unknown node {node!r}")
            return None
        if node not in known:
            return None  # already reported as an unknown module
        found = registry.port(known[node], port, side)
        if found is not None:
            return found
        other = "inputs" if side == "outputs" else "outputs"
        if registry.port(known[node], port, other) is not None:
            wrong = "an input" if side == "outputs" else "an output"
            problems.append(f"{label}: wrong direction: {endpoint} is {wrong}; edges run from outputs to inputs")
        else:
            problems.append(f"{label}: {node!r} ({known[node]}) has no port {port!r}")
        return None

    def _check_binding(self, binding, known, registry, problems) -> None:
        src, dst = binding.get("from"), binding.get("to")
        label = f"binding {src} -> {dst}"
        smooth = binding.get("smooth")
        if smooth is not None and not (isinstance(smooth, dict) and set(smooth) == {"attack_ms", "release_ms"}
                                       and all(_is_int(v) and v >= 0 for v in smooth.values())):
            problems.append(f"{label}: smooth must be {{attack_ms, release_ms}} in whole milliseconds")
        if "precedence" in binding and not _is_int(binding["precedence"]):
            problems.append(f"{label}: precedence must be a whole number")
        if "learn" in binding and not isinstance(binding["learn"], bool):
            problems.append(f"{label}: learn must be true or false")
        try:
            s_node, s_port, feature = _split(src)
            t_node, t_param, extra = _split(dst)
        except GraphError as exc:
            problems.extend(f"{label}: {p}" for p in exc.problems)
            return
        if s_node not in self.nodes:
            problems.append(f"{label}: unknown node {s_node!r}")
        elif s_node in known:
            out_port = registry.port(known[s_node], s_port, "outputs")
            if out_port is None:
                problems.append(f"{label}: {s_node!r} has no output {s_port!r}")
            elif out_port["type"] not in PRODUCER_TYPES:
                problems.append(f"{label}: {src} is {out_port['type']}, not a control or analysis producer")
            elif feature and out_port["type"] != "analysis.features":
                problems.append(f"{label}: only analysis.features outputs take a feature suffix")
        if extra:
            problems.append(f"{label}: a binding target is node.param, not {dst!r}")
            return
        if t_node not in self.nodes:
            problems.append(f"{label}: unknown node {t_node!r}")
            return
        if t_node not in known:
            return
        param = registry.param(known[t_node], t_param)
        if param is None:
            problems.append(f"{label}: {t_param!r} is not a declared param of {t_node!r} ({known[t_node]})")
            return
        rng = binding.get("range")
        if rng is None:
            return
        lo_p, hi_p = param["range"]
        if not (isinstance(rng, (list, tuple)) and len(rng) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in rng)):
            problems.append(f"{label}: range must be [lo, hi]")
        elif rng[0] > rng[1]:
            problems.append(f"{label}: range {rng} runs backwards")
        elif rng[0] < lo_p or rng[1] > hi_p:
            problems.append(f"{label}: range {list(rng)} is outside {t_param}'s declared range {param['range']}")

    def _find_cycle(self) -> Optional[List[str]]:
        succ: Dict[str, List[str]] = {n: [] for n in self.nodes}
        for s, d in self.node_edges():
            if s in succ and d in succ:
                succ[s].append(d)
        state: Dict[str, int] = {}
        stack: List[str] = []

        def visit(n: str) -> Optional[List[str]]:
            state[n] = 1
            stack.append(n)
            for m in succ[n]:
                if state.get(m) == 1:
                    return stack[stack.index(m):] + [m]
                if m not in state:
                    found = visit(m)
                    if found:
                        return found
            stack.pop()
            state[n] = 2
            return None

        for n in succ:
            if n not in state:
                found = visit(n)
                if found:
                    return found
        return None


def load_graph(obj) -> Graph:
    if not isinstance(obj, dict):
        raise GraphError(["a graph must be a JSON object"])
    if obj.get("api") != GRAPH_API:
        raise GraphError([f"api must be {GRAPH_API!r}, got {obj.get('api')!r}"])
    problems: List[str] = []
    nodes = obj.get("nodes") or {}
    if not isinstance(nodes, dict):
        problems.append("nodes must map a name to {use, with}")
        nodes = {}
    for name in nodes:
        if not _NAME_RE.match(str(name)):
            problems.append(f"node name {name!r} must start with a letter and use letters, digits, _ or -")
    edges: List[Tuple[str, str]] = []
    for edge in obj.get("edges") or []:
        if isinstance(edge, (list, tuple)) and len(edge) == 2 and all(isinstance(x, str) for x in edge):
            edges.append((edge[0], edge[1]))
        elif isinstance(edge, dict) and isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str):
            edges.append((edge["from"], edge["to"]))
        else:
            problems.append(f"edge {edge!r} must be [from, to]")
    bindings = obj.get("bindings") or []
    if not isinstance(bindings, list) or not all(isinstance(b, dict) for b in bindings):
        problems.append("bindings must be a list of {from, to, ...}")
        bindings = []
    if problems:
        raise GraphError(problems)
    return Graph(api=obj["api"], name=str(obj.get("name") or ""), mode=str(obj.get("mode") or "live_audio"),
                 assets=copy.deepcopy(obj.get("assets") or {}), nodes=copy.deepcopy(nodes),
                 edges=edges, bindings=copy.deepcopy(bindings))


# -------------------------------------------------------------------- text form
_MODE_RE = re.compile(rf"^mode\s+({_NAME})$")
_NODE_RE = re.compile(rf"^node\s+({_NAME})\s*=\s*([A-Za-z0-9_.-]+)$")
_EDGE_RE = re.compile(rf"^({_NAME}\.{_NAME})\s*->\s*({_NAME}\.{_NAME})$")
_MAP_RE = re.compile(rf"^map\s+({_NAME}\.{_NAME}(?:\.{_NAME})?)\s*->\s*({_NAME}\.{_NAME})\s*(\{{.*\}})?$")
_NUM = r"-?\d+(?:\.\d+)?"


def _number(text: str):
    value = float(text)
    return int(value) if value.is_integer() and "." not in text else value


def _map_options(body: Optional[str], lineno: int) -> dict:
    if not body:
        return {}
    options = {}
    for item in filter(None, (p.strip() for p in body.strip()[1:-1].split(","))):
        if ":" not in item:
            raise GraphError([f"line {lineno}: map option {item!r} must be key: value"])
        key, value = (s.strip() for s in item.split(":", 1))
        if key == "range":
            m = re.fullmatch(rf"({_NUM})\s*\.\.\s*({_NUM})", value)
            if not m:
                raise GraphError([f"line {lineno}: range must look like lo..hi, got {value!r}"])
            options["range"] = [_number(m.group(1)), _number(m.group(2))]
        elif key == "smooth":
            # 20ms is symmetric; 12ms/180ms is attack/release. The JSON keeps whole milliseconds.
            m = re.fullmatch(r"(\d+)\s*ms(?:\s*/\s*(\d+)\s*ms)?", value)
            if not m:
                raise GraphError([f"line {lineno}: smooth must look like 20ms or 12ms/180ms, got {value!r}"])
            attack = int(m.group(1))
            options["smooth"] = {"attack_ms": attack, "release_ms": int(m.group(2)) if m.group(2) else attack}
        elif key == "precedence":
            if not re.fullmatch(r"-?\d+", value):
                raise GraphError([f"line {lineno}: precedence must be a whole number, got {value!r}"])
            options["precedence"] = int(value)
        elif key == "learn":
            if value not in ("true", "false"):
                raise GraphError([f"line {lineno}: learn must be true or false, got {value!r}"])
            options["learn"] = value == "true"
        else:
            raise GraphError([f"line {lineno}: unknown map option {key!r}"])
    return options


def parse_text(src: str, registry: Optional[Registry] = None) -> dict:
    """The text form -> canonical graph JSON. See FIRST-LIGHT-SPEC.md for the grammar."""
    registry = registry or load_registry()
    graph = {"api": GRAPH_API, "name": "", "mode": "live_audio", "assets": {}, "nodes": {},
             "edges": [], "bindings": []}
    for lineno, raw in enumerate(str(src).splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if m := _MODE_RE.match(line):
            graph["mode"] = m.group(1)
        elif m := _NODE_RE.match(line):
            graph["nodes"][m.group(1)] = {"use": m.group(2)}
        elif m := _MAP_RE.match(line):
            binding = {"from": m.group(1), "to": m.group(2), "precedence": 0}
            binding.update(_map_options(m.group(3), lineno))
            graph["bindings"].append(binding)
        elif m := _EDGE_RE.match(line):
            graph["edges"].append([m.group(1), m.group(2)])
        elif "|" in line:
            chain = [p.strip() for p in line.split("|")]
            for a, b in zip(chain, chain[1:]):
                graph["edges"].append(_chain_link(a, b, graph, registry, lineno))
        else:
            raise GraphError([f"line {lineno}: cannot read {raw.strip()!r}"])
    return graph


def _chain_link(a: str, b: str, graph: dict, registry: Registry, lineno: int) -> List[str]:
    for name in (a, b):
        if name not in graph["nodes"]:
            raise GraphError([f"line {lineno}: {name!r} is used in a chain before a node line declares it"])
    try:
        a_mod, b_mod = registry.get(graph["nodes"][a]["use"]), registry.get(graph["nodes"][b]["use"])
    except KeyError as exc:
        raise GraphError([f"line {lineno}: unknown module {exc.args[0]!r}"]) from None
    for out_port in a_mod.get("outputs", []):
        for in_port in b_mod.get("inputs", []):
            if in_port["type"] == out_port["type"]:
                return [f"{a}.{out_port['port']}", f"{b}.{in_port['port']}"]
    raise GraphError([f"line {lineno}: nothing {a!r} outputs matches an input of {b!r}"])
