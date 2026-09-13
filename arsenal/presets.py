"""The preset bank: shader presets under arsenal/web/presets, each described by a one-line JSON header.

A preset opens with `#version 300 es` on line 1, because GLSL ES requires it there, and a
`//! {json}` header on line 2. PLAY-NIGHT-SPEC.md defines the format, the uniforms and the floors.
Problems are reported, never raised, so the page can list a broken preset instead of hiding it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

PRESET_DIR = Path(__file__).resolve().parent / "web" / "presets"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")

#: Uniforms v1 and their required types.
UNIFORMS = {
    "u_video": "sampler2D", "u_prev": "sampler2D", "u_audio": "sampler2D",
    "u_res": "vec2", "u_video_res": "vec2",
    "u_time": "float", "u_media_time": "float", "u_frame": "float", "u_has_video": "float",
    "u_pulse": "float", "u_beat": "float", "u_level": "float",
    "u_bass": "float", "u_mid": "float", "u_high": "float", "u_flux": "float",
    "u_hue": "float", "u_intensity": "float",
    **{f"u_k{i}": "float" for i in range(1, 9)},
}

_UNIFORM_DECL = re.compile(r"^\s*uniform\s+(?:(?:highp|mediump|lowp)\s+)?(\w+)\s+([^;]+);", re.MULTILINE)
_FOR_CONDITION = re.compile(r"\bfor\s*\([^;]*;([^;]*);")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


def parse_preset(path) -> dict:
    path = Path(path)
    problems: List[str] = []
    info = {"id": path.stem, "file": path.name, "url": f"/web/presets/{path.name}", "name": path.stem,
            "author": "", "tags": [], "params": [], "problems": problems}
    if not ID_RE.match(path.stem):
        problems.append(f"file name {path.stem!r} must use lowercase letters, digits and dashes (2 to 41 characters)")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        problems.append(f"cannot read the file: {exc}")
        return info

    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "#version 300 es":
        problems.append("line 1 must be exactly '#version 300 es'")
    if len(lines) < 2 or not lines[1].startswith("//!"):
        problems.append("line 2 must be the '//! {json}' header")
    else:
        try:
            header = json.loads(lines[1][3:])
        except ValueError as exc:
            problems.append(f"the line 2 header is not JSON: {exc}")
        else:
            if isinstance(header, dict):
                _check_header(header, path.stem, info, problems)
            else:
                problems.append("the line 2 header must be a JSON object")
    _check_source(_strip_comments(text), problems)
    return info


def _check_header(header: dict, stem: str, info: dict, problems: List[str]) -> None:
    if header.get("id") != stem:
        problems.append(f"header id {header.get('id')!r} must equal the file name {stem!r}")
    for key in ("name", "author"):
        value = header.get(key)
        if isinstance(value, str) and value.strip():
            info[key] = value.strip()
        else:
            problems.append(f"the header needs a non-empty {key}")
    tags = header.get("tags", [])
    if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
        info["tags"] = list(tags)
    else:
        problems.append("tags must be a list of strings")

    params = header.get("params", [])
    if not isinstance(params, list) or len(params) > 8:
        problems.append("params must be a list of at most 8 entries")
        return
    seen = set()
    for i, param in enumerate(params):
        if not isinstance(param, dict):
            problems.append(f"param {i} must be an object")
            continue
        k, name, default = param.get("k"), param.get("name"), param.get("default")
        if not (_is_int(k) and 1 <= k <= 8):
            problems.append(f"param {i}: k must be a whole number from 1 to 8")
            continue
        ok = True
        if k in seen:
            problems.append(f"param k{k} is declared twice")
            ok = False
        seen.add(k)
        if not (isinstance(name, str) and 1 <= len(name.strip()) <= 16):
            problems.append(f"param k{k}: name must be 1 to 16 characters")
            ok = False
        if isinstance(default, bool) or not isinstance(default, (int, float)) or not 0 <= default <= 1:
            problems.append(f"param k{k}: default must be a number from 0 to 1")
            ok = False
        if ok:
            info["params"].append({"k": k, "name": name.strip(), "default": default})


def _check_source(body: str, problems: List[str]) -> None:
    if re.search(r"\b(mediump|lowp)\b", body):
        problems.append("use highp only (no mediump or lowp)")
    if not re.search(r"^\s*precision\s+highp\s+float\s*;", body, re.MULTILINE):
        problems.append("declare 'precision highp float;'")
    if not re.search(r"\bin\s+vec2\s+v_uv\s*;", body):
        problems.append("declare 'in vec2 v_uv;'")
    if not re.search(r"\bout\s+vec4\s+outColor\s*;", body):
        problems.append("declare 'out vec4 outColor;'")
    for match in _UNIFORM_DECL.finditer(body):
        declared_type = match.group(1)
        for raw in match.group(2).split(","):
            name = raw.split("[")[0].strip()
            wanted = UNIFORMS.get(name)
            if wanted is None:
                problems.append(f"uniform {name} is not in the Play Night uniform list")
            elif wanted != declared_type:
                problems.append(f"uniform {name} must be {wanted}, not {declared_type}")
    for match in _FOR_CONDITION.finditer(body):
        if re.search(r"\bu_\w+", match.group(1)):
            problems.append(f"a loop bound uses a uniform ({match.group(1).strip()}); bounds must be constant")


def list_presets(directory=None) -> List[dict]:
    directory = Path(directory) if directory else PRESET_DIR
    if not directory.is_dir():
        return []
    presets = [parse_preset(path) for path in sorted(directory.glob("*.frag"))]
    return sorted(presets, key=lambda p: (p["name"].lower(), p["id"]))
