"""redact.py -- remove third-party personal information from the tracked tree, repeatably.

    py scripts/ops/redact.py                 # DRY RUN: what would change, and where
    py scripts/ops/redact.py --apply         # do it
    py scripts/ops/redact.py --verify        # assert zero survivors

WHY THIS IS A TOOL AND NOT A ONE-OFF (2026-08-11): a redaction was ordered and executed
inline in a session. It ran against ONE file of six, and nobody could tell, because a
one-off leaves nothing to re-run and nothing to verify. It also matched case-sensitively,
so an all-caps rendering of the same surname survived inside the very file it cleaned --
and the inline script itself, quoted in the transcript, re-published the string it existed
to remove. All three failures are properties of it being a script instead of an organ.

THREE RULES, each answering one of those failures:

1. THE TARGETS LIVE OUTSIDE THE REPO. `.secrets/redaction-manifest.json` (gitignored) holds
   the strings; this file holds none. A manifest committed alongside the tool would
   re-publish exactly what it removes -- which is what happened last time.

2. MATCHING IS CASE-INSENSITIVE, ALWAYS. Non-negotiable, and the reason the last pass
   leaked.

3. A TARGET TOO COMMON TO BE A NAME IS REFUSED, NOT APPLIED. Every pattern is counted
   across the tree first, and one exceeding `max_hits_per_target` is reported and skipped.
   Auto-extracted identity tokens include things like three-letter acronyms; a repo-wide
   replace of one of those would corrupt the codebase far worse than the exposure it fixed.
   The ceiling is the difference between a redaction and an outage.

WHAT THIS DOES NOT DO, and it is the most important line here: **it does not unpublish
anything.** Rewriting the working tree leaves every prior commit intact, and on a public
remote those blobs stay fetchable forever. Only a history rewrite (`git filter-repo`)
actually removes them, and that invalidates every commit SHA recorded in lessons, notes and
docs. This tool is step one of two, and it must never be mistaken for both.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = _REPO_ROOT / ".secrets" / "redaction-manifest.json"

# Binary and vendored content: replacing bytes inside these corrupts them, and a name
# "found" in a PNG is image data, not a disclosure.
_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webm", ".mp4", ".pdf", ".zip", ".gz",
                  ".ico", ".woff", ".woff2", ".ttf", ".db", ".pyc", ".jsonl.gz"}
_SKIP_DIRS = ("refs/design-inspiration/", "docs/_archive/", "ComfyUI-Zluda/")


def load_manifest(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else MANIFEST
    if not p.exists():
        raise FileNotFoundError(
            f"no manifest at {p} -- it lives OUTSIDE the tracked tree on purpose, so the "
            f"tool can be reviewed without re-committing the strings it removes")
    man = json.loads(p.read_text(encoding="utf-8"))
    for t in man.get("targets", []):
        if not str(t.get("pattern", "")).strip():
            raise ValueError("a target has no pattern")
        if not str(t.get("why", "")).strip():
            raise ValueError(f"target {t['pattern'][:3]}… has no stated reason -- a "
                             f"redaction nobody can justify later is one nobody can audit")
    return man


def _tracked(root: Path) -> List[str]:
    out = subprocess.run(["git", "ls-files"], cwd=str(root),
                         capture_output=True, text=True).stdout
    files = []
    for rel in out.splitlines():
        rel = rel.strip()
        if not rel or Path(rel).suffix.lower() in _SKIP_SUFFIXES:
            continue
        if any(rel.replace("\\", "/").startswith(d) for d in _SKIP_DIRS):
            continue
        files.append(rel)
    return files


def shape(pattern: str) -> str:
    """A target named in output without being reproduced in it."""
    return f"{pattern[0]}{'*' * max(0, len(pattern) - 2)}{pattern[-1]}" \
        if len(pattern) > 2 else "**"


def scan(root: Optional[Path] = None, manifest: Optional[Dict[str, Any]] = None
         ) -> Dict[str, Any]:
    """Count every target across the tree. Nothing is written."""
    root = Path(root) if root else _REPO_ROOT
    man = manifest or load_manifest()
    ceiling = int(man.get("max_hits_per_target", 400))
    files = _tracked(root)

    per_target: List[Dict[str, Any]] = []
    for t in man["targets"]:
        rx = re.compile(re.escape(t["pattern"]), re.IGNORECASE)
        hits, where = 0, []
        for rel in files:
            try:
                body = (root / rel).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            n = len(rx.findall(body))
            if n:
                hits += n
                where.append((rel, n))
        per_target.append({
            "shape": shape(t["pattern"]), "why": t["why"], "hits": hits,
            "files": sorted(where, key=lambda x: -x[1]),
            # A pattern this common is a word, not a name. Refusing it is the difference
            # between a redaction and an outage.
            "refused": hits > ceiling,
        })
    return {"scanned": len(files), "ceiling": ceiling, "targets": per_target}


def apply(root: Optional[Path] = None, manifest: Optional[Dict[str, Any]] = None
          ) -> Dict[str, Any]:
    root = Path(root) if root else _REPO_ROOT
    man = manifest or load_manifest()
    pre = scan(root, man)
    ok_patterns = [t for t, s in zip(man["targets"], pre["targets"]) if not s["refused"]]
    files = _tracked(root)
    changed, replacements = 0, 0
    for rel in files:
        p = root / rel
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        new = body
        for t in ok_patterns:
            rx = re.compile(re.escape(t["pattern"]), re.IGNORECASE)
            new, n = rx.subn(t["replace"], new)
            replacements += n
        if new != body:
            p.write_text(new, encoding="utf-8")
            changed += 1
    return {"files_changed": changed, "replacements": replacements,
            "refused": [t["shape"] for t in pre["targets"] if t["refused"]],
            "applied_targets": len(ok_patterns)}


def render(rep: Dict[str, Any]) -> None:
    print(f"[redact] {rep['scanned']:,} tracked text file(s) | "
          f"refusal ceiling {rep['ceiling']} hits/target")
    for t in rep["targets"]:
        flag = "  REFUSED (too common to be a name)" if t["refused"] else ""
        print(f"   {t['shape']:22} {t['hits']:5} hit(s){flag}")
        if not t["refused"]:
            for rel, n in t["files"][:4]:
                print(f"        {n:4}  {rel}")
        print(f"        why: {t['why']}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--root", default="")
    a = ap.parse_args(argv)
    root = Path(a.root) if a.root else _REPO_ROOT

    if a.apply:
        rep = apply(root)
        print(f"[redact] APPLIED -- {rep['replacements']} replacement(s) across "
              f"{rep['files_changed']} file(s), {rep['applied_targets']} target(s)")
        if rep["refused"]:
            print(f"[redact] REFUSED (unchanged): {', '.join(rep['refused'])}")
        print("[redact] NOTE: the working tree is clean; HISTORY IS NOT. Prior commits")
        print("[redact] still carry these strings and stay fetchable on a public remote")
        print("[redact] until history is rewritten. This is step one of two.")
        return 0

    rep = scan(root)
    render(rep)
    if a.verify:
        live = [t for t in rep["targets"] if t["hits"] and not t["refused"]]
        if live:
            print(f"[redact] VERIFY FAILED -- {len(live)} target(s) still present")
            return 1
        print("[redact] VERIFY OK -- zero survivors among applied targets")
        return 0
    print("[redact] dry run -- nothing written. Use --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
