"""The loud plan: what runs where, what gets copied, what it costs, and what it is licensed under.

Nothing here is measured. Latency is what modules declare, and the plan says so; receipts carry
measurements.
"""
from __future__ import annotations

import re
from typing import Dict, List

from .graph import Graph
from .mediatypes import MEDIA_PORT_TYPES
from .registry import Registry
from .timebase import MASTER_BY_MODE

#: GPL-family copyleft (GPL, AGPL). The leading word boundary keeps LGPL out, because LGPL used
#: dynamically stays in arsenal-core (contract F8).
_GPL_RE = re.compile(r"\bA?GPL(?:-|\b)")


def _is_gpl(licence: str) -> bool:
    return bool(_GPL_RE.search(licence or ""))


def make_plan(graph: Graph, registry: Registry) -> dict:
    graph.require_valid(registry)

    nodes: List[dict] = []
    for name, node in graph.nodes.items():
        manifest = registry.get(node["use"])
        nodes.append({"name": name, "module": manifest["id"], "engine": manifest["engine"],
                      "isolation": manifest.get("isolation", ""),
                      "licence": manifest.get("licence") or "NOASSERTION"})
    engine = {n["name"]: n["engine"] for n in nodes}

    edges: List[dict] = []
    warnings: List[str] = []
    for src, dst in graph.edges:
        s_node, s_port = src.split(".")[:2]
        d_node = dst.split(".")[0]
        port_type = registry.port(graph.nodes[s_node]["use"], s_port, "outputs")["type"]
        crosses = engine[s_node] != engine[d_node]
        is_copy = crosses and port_type in MEDIA_PORT_TYPES
        if is_copy:
            note = f"COPY: {port_type} leaves the {engine[s_node]} engine for {engine[d_node]}"
            warnings.append(f"copy on {src} -> {dst} ({engine[s_node]} -> {engine[d_node]})")
        elif crosses:
            note = f"reference handoff ({engine[s_node]} -> {engine[d_node]})"
        elif engine[s_node] == "browser" and port_type in MEDIA_PORT_TYPES:
            note = "same engine (inside the browser engine; copies there are not observable)"
        else:
            note = "same engine"
        edges.append({"from": src, "to": dst, "type": port_type, "copy": is_copy, "note": note})

    bindings = [{"from": b.get("from"), "to": b.get("to"), "range": b.get("range")} for b in graph.bindings]

    licences = sorted({n["licence"] for n in nodes})
    profile = "arsenal-gpl" if any(_is_gpl(lic) for lic in licences) else "arsenal-core"
    for n in nodes:
        if n["licence"] == "NOASSERTION":
            warnings.append(f"licence NOASSERTION for {n['name']} ({n['module']}, {n['engine']} engine): not asserted yet")
        elif "unverified" in n["licence"].lower():
            warnings.append(f"licence unverified for {n['name']} ({n['module']}): {n['licence']}")

    return {
        "api": "arsenal.plan/v0",
        "graph": graph.name,
        "mode": graph.mode,
        "master_clock": MASTER_BY_MODE.get(graph.mode),
        "nodes": nodes,
        "edges": edges,
        "bindings": bindings,
        "latency_ms": _longest_path_ms(graph, registry),
        "latency_basis": "declared, not measured",
        "licences": licences,
        "licence_profile": profile,
        "warnings": warnings,
    }


def _longest_path_ms(graph: Graph, registry: Registry) -> int:
    base: Dict[str, int] = {
        name: int((registry.get(node["use"]).get("latency_ms") or {}).get("base", 0))
        for name, node in graph.nodes.items()
    }
    preds: Dict[str, List[str]] = {n: [] for n in graph.nodes}
    for s, d in graph.node_edges():
        preds[d].append(s)
    memo: Dict[str, int] = {}

    def total(n: str) -> int:
        if n not in memo:
            memo[n] = base[n] + max((total(p) for p in preds[n]), default=0)
        return memo[n]

    return max((total(n) for n in graph.nodes), default=0)


def render_plan(plan: dict) -> str:
    lines = [f"PLAN {plan.get('graph') or '(unnamed)'}  ·  mode {plan['mode']}  ·  master clock: {plan.get('master_clock')}", "", "NODES"]
    width = max((len(n["name"]) for n in plan["nodes"]), default=4)
    for n in plan["nodes"]:
        lines.append(f"  {n['name']:<{width}}  {n['module']:<24} {n['engine']:<9} {n['isolation']:<12} {n['licence']}")
    lines += ["", "EDGES"]
    for e in plan["edges"]:
        flag = "!" if e["copy"] else " "
        lines.append(f" {flag} {e['from']} -> {e['to']}  [{e['type']}]  {e['note']}")
    if plan["bindings"]:
        lines += ["", "BINDINGS"]
        for b in plan["bindings"]:
            rng = b.get("range")
            suffix = f" {{range: {rng[0]}..{rng[1]}}}" if isinstance(rng, list) and len(rng) == 2 else ""
            lines.append(f"  map {b['from']} -> {b['to']}{suffix}")
    lines += ["", f"LATENCY  {plan['latency_ms']} ms along the longest path ({plan['latency_basis']})",
              f"LICENCES {plan['licence_profile']}: {', '.join(plan['licences'])}"]
    if plan["warnings"]:
        lines += ["", "WARNINGS"] + [f"  ! {w}" for w in plan["warnings"]]
    return "\n".join(lines)
