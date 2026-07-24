"""Projection renderer (A1) -- one atom -> one read-only markdown file.

Spec: docs/library/design/20260701_artifact-substrate-the-reconciled-design_8ea728.md section 2 + docs/super-wiki-experience-
design-2026-07.md section 4. The render is DISPOSABLE and REGENERABLE; the atom is the
truth. YAML frontmatter carries the header fields (Obsidian Bases reads them natively)
plus akashic_id + akashic_sha -- the projection self-verifies against the atom body, so
drift is mechanically detectable (the audit library domain photographs this pair).

Incremental by construction: render_atom() writes exactly one file (deepseek's
walk-one-render-one; kills the door-expense collapse). gen_library folds this in for
the full-corpus walk + maps.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

DEFAULT_LIBRARY_DIR = os.path.join("docs", "library")

_DO_NOT_EDIT = (
    "<!-- GENERATED PROJECTION of {atom_id} -- DO NOT EDIT. The atom is the truth; "
    "regeneration overwrites this file. Edit through the doc verbs. -->"
)


def _yaml_escape(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "" or any(c in s for c in ":#[]{}&*!|>'\"%@`,\n") or s.strip() != s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'
    return s


def _iso(ts: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return "null"


def frontmatter(atom: Dict[str, Any]) -> str:
    h = atom["header"]
    lines = ["---"]
    lines.append(f"akashic_id: {_yaml_escape(atom['id'])}")
    lines.append(f"akashic_sha: {_yaml_escape(atom['body_sha'])}")
    # v1.1: schema_version renders (absent -> 1, the pre-version corpus); body_type is a
    # Bases-filterable facet (the reader's per-datatype render key). tenant only renders
    # on legacy atoms that still carry it (demoted from the stored shape 2026-07-24).
    lines.append(f"schema_version: {_yaml_escape(int(atom.get('schema_version', 1)))}")
    fields = ["status", "type", "arc", "date", "title", "gist", "visibility", "body_type"]
    if h.get("tenant") is not None:
        fields.insert(6, "tenant")
    for field in fields:
        if field == "arc" and h.get("arc") is None:
            continue  # deepseek fence: 'arc: null' renders as the STRING null in Bases -- omit
        if field == "body_type" and h.get("body_type") is None:
            lines.append("body_type: markdown")   # legacy default, explicit for Bases filters
            continue
        lines.append(f"{field}: {_yaml_escape(h.get(field))}")
    lines.append("seats: [" + ", ".join(_yaml_escape(s) for s in h.get("seats", [])) + "]")
    lines.append("category: [" + ", ".join(_yaml_escape(c) for c in h.get("category", [])) + "]")
    lines.append(f"origin: {_yaml_escape(atom.get('origin'))}")
    lines.append(f"settled: {_yaml_escape(atom.get('settled'))}")
    lines.append(f"supersedes: {_yaml_escape(atom.get('supersedes'))}")
    lines.append(f"superseded: {_yaml_escape(atom.get('superseded'))}")
    cites = atom.get("citations_out", [])
    if cites:
        lines.append("citations:")
        for c in cites:
            lines.append(f"  - target: {_yaml_escape(c.get('target'))}")
            lines.append(f"    rel: {_yaml_escape(c.get('rel'))}")
    else:
        lines.append("citations: []")
    lines.append(f"created: {_yaml_escape(_iso(atom.get('created_ts')))}")
    lines.append(f"updated: {_yaml_escape(_iso(atom.get('updated_ts')))}")
    lines.append("---")
    return "\n".join(lines)


def projection_relpath(atom: Dict[str, Any]) -> str:
    """docs/library/<type>/<id-minus-prefix>.md -- type + slug + hash only (one-facet law:
    the path never encodes arc/category/status; re-categorizing never moves a file)."""
    fname = atom["id"][len("art_"):] + ".md"
    return os.path.join(DEFAULT_LIBRARY_DIR, atom["header"]["type"], fname)


def render_atom(atom: Dict[str, Any], repo_root: str = "E:\\AI-Setup") -> str:
    """Write the atom's single projection file; returns the absolute path."""
    rel = projection_relpath(atom)
    path = os.path.join(repo_root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    h = atom["header"]
    banner = ""
    if h.get("status") == "superseded" and atom.get("superseded"):
        banner = f"\n> **SUPERSEDED** -- succeeded by `{atom['superseded']}`. This version is preserved as a receipt.\n"
    elif h.get("status") == "draft":
        banner = "\n> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.\n"
    elif atom.get("origin") == "conversation" and atom.get("settled") == "live":
        banner = "\n> **LIVE DISCUSSION** -- no ruling yet; authority derives from (type, origin, settled), never prose.\n"
    content = (
        frontmatter(atom) + "\n"
        + _DO_NOT_EDIT.format(atom_id=atom["id"]) + "\n"
        + banner + "\n"
        + f"# {h['title']}\n\n"
        + (atom.get("body") or "")
        + ("\n" if not (atom.get("body") or "").endswith("\n") else "")
    )
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return path
