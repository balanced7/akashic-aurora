"""fence_phase -- the method board's state source (T079-E2).

Derives a fence arc's CURRENT phase from the files the fence itself produces in
research/reviewed/ (the fence workspace law: halves are <agent>-<slug>-*.md,
the reconciliation is <slug>-reconciliation-*.md or *-<slug>-reconciliation-*).
Ladder: idle -> blind (one half) -> reconciling (both halves) -> reconciled.
Pure mtime reader; never raises (F3) -- the board renders through anything.
"""
from __future__ import annotations

import os
from typing import Any, Dict


def _default_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "research", "reviewed")


def fence_phase(slug: str, reviewed_dir: str = "") -> Dict[str, Any]:
    d = reviewed_dir or _default_dir()
    slug_l = str(slug).lower()
    halves, recon = set(), []
    try:
        for name in os.listdir(d):
            n = name.lower()
            if slug_l not in n or not n.endswith(".md"):
                continue
            if "reconciliation" in n:
                recon.append(name)
            elif n.startswith("claude-"):
                halves.add("claude")
            elif n.startswith("deepseek-"):
                halves.add("deepseek")
    except Exception:
        return {"phase": "idle", "slug": slug, "files": []}
    if recon:
        return {"phase": "reconciled", "slug": slug, "agents": sorted(halves),
                "files": sorted(recon)}
    if len(halves) >= 2:
        return {"phase": "reconciling", "slug": slug, "agents": sorted(halves),
                "files": []}
    if halves:
        return {"phase": "blind", "slug": slug, "agents": sorted(halves), "files": []}
    return {"phase": "idle", "slug": slug, "files": []}
