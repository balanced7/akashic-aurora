"""Module manifests (arsenal.module/v0): what each module takes, gives and needs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import MODULE_PROTOCOL
from .mediatypes import MEMORY_DOMAINS, PORT_TYPES

DEFAULT_DIR = Path(__file__).resolve().parent / "modules"
ENGINES = ("arsenal", "browser", "ffmpeg", "gstreamer", "mpv", "external")


class ManifestError(ValueError):
    def __init__(self, problems: List[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def validate_manifest(m: dict, source: str = "manifest") -> List[str]:
    problems = []
    for key in ("id", "version", "protocol", "engine"):
        if not m.get(key):
            problems.append(f"{source}: missing {key}")
    if m.get("protocol") and m["protocol"] != MODULE_PROTOCOL:
        problems.append(f"{source}: protocol {m['protocol']!r} is not {MODULE_PROTOCOL!r}")
    if m.get("engine") and m["engine"] not in ENGINES:
        problems.append(f"{source}: unknown engine {m['engine']!r}")
    for side in ("inputs", "outputs"):
        seen = set()
        for port in m.get(side, []):
            name = port.get("port")
            if not name:
                problems.append(f"{source}: a port in {side} has no name")
                continue
            if name in seen:
                problems.append(f"{source}: duplicate {side} port {name!r}")
            seen.add(name)
            if port.get("type") not in PORT_TYPES:
                problems.append(f"{source}: port {name!r} has unknown type {port.get('type')!r}")
            memory = (port.get("caps") or {}).get("memory")
            if memory is not None and memory != "any" and memory not in MEMORY_DOMAINS:
                problems.append(f"{source}: port {name!r} has unknown memory domain {memory!r}")
    for param in m.get("params", []):
        rng = param.get("range")
        if not param.get("name") or not param.get("unit"):
            problems.append(f"{source}: a param needs a name and a unit")
        if not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(v, (int, float)) for v in rng)
                and rng[0] < rng[1]):
            problems.append(f"{source}: param {param.get('name')!r} needs range [lo, hi] with lo < hi")
    return problems


class Registry:
    def __init__(self, manifests: Dict[str, dict]):
        self._manifests = dict(manifests)

    def get(self, module_id: str) -> dict:
        return self._manifests[module_id]

    def ids(self) -> List[str]:
        return sorted(self._manifests)

    def port(self, module_id: str, name: str, side: str) -> Optional[dict]:
        """The port dict on 'inputs' or 'outputs', or None."""
        for port in self.get(module_id).get(side, []):
            if port.get("port") == name:
                return port
        return None

    def param(self, module_id: str, name: str) -> Optional[dict]:
        for param in self.get(module_id).get("params", []):
            if param.get("name") == name:
                return param
        return None


def load_registry(dirs: Optional[Iterable] = None) -> Registry:
    manifests: Dict[str, dict] = {}
    problems: List[str] = []
    for directory in [Path(d) for d in (dirs or [DEFAULT_DIR])]:
        for path in sorted(directory.glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            problems.extend(validate_manifest(manifest, path.name))
            module_id = manifest.get("id")
            if module_id in manifests:
                problems.append(f"{path.name}: duplicate module id {module_id!r}")
            manifests[module_id] = manifest
    if problems:
        raise ManifestError(problems)
    return Registry(manifests)
