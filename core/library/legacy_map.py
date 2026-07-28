"""The legacy_path -> art_id map (T109): the migration's missing handle, finally wired.

Spec gap this closes: docs/library/design/20260723_kimi-half-the-artifact-substrate...§167
promised "records a legacy_path -> art_id map as a committed atom" -- it was specified,
never landed as a queryable door. f8510b6 ("Delete the 643!") deleted 621 docs/*.md
originals whose BASENAMES were the retrieval handle a cold agent searches by
("coordination-plan-synthesis", "comms-pillar-synthesis", ...). The content survived as
atom projections under docs/library/<type>/, but the slug survived in NO searchable
surface. Content reachable as bytes, unreachable as a handle = the confident-zero genus
(kimi, readme_directory_pointer_fails_open, T113 first-cut -- three instances, one shape).

The map is CONSTRUCTED, not hand-written, so it carries its own proof:
  * f8510b6's deletion is one git commit; each deleted docs/*.md's pre-deletion body is
    recoverable from git ancestry (the migration preserved it deliberately).
  * the migration lifted a PREFIX into the atom header and kept the remainder byte-exact
    as the atom body, so the atom body must be a SUFFIX of its recovered legacy document.
  * a deleted doc matches only when exactly one non-trivial atom body is its suffix.
Result: original_slug -> art_id, deterministic and self-verifying -- the very artifact the
design promised. Rebuild is idempotent; a slug that matches no atom is recorded UNMATCHED
(loud, never silently dropped) so the gap is visible rather than absorbed.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional

from core.library import atoms as _atoms

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATION_COMMIT = "f8510b6"          # "Delete the 643!" -- the sprawl retirement
MAP_PATH = os.path.join("store", "docs", "legacy_map.json")   # the committed map artifact
# Independent live census (codex, 2026-07-28): all 103 deleted docs matched exactly
# one atom, zero were ambiguous, and the shortest matching atom tail was 3,225
# characters -- more than 16x this conservative anti-trivial-match floor.
_MIN_SUFFIX_CHARS = 200


def _deleted_docs(commit: str = MIGRATION_COMMIT) -> List[str]:
    """Every docs/*.md path deleted by the migration commit (git ancestry is the truth)."""
    try:
        raw = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", "--diff-filter=D", commit],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30).stdout
    except Exception:
        return []
    return [ln.strip() for ln in raw.splitlines()
            if ln.strip().startswith("docs/") and ln.strip().endswith(".md")]


def _pre_delete_body(path: str, commit: str = MIGRATION_COMMIT) -> Optional[str]:
    """The deleted doc's body as of the commit's parent (its last live form)."""
    try:
        raw = subprocess.run(
            ["git", "show", f"{commit}^:{path}"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30)
        return raw.stdout if raw.returncode == 0 else None
    except Exception:
        return None


def _slug_of(path: str) -> str:
    """The retrieval handle: the deleted doc's basename minus .md."""
    return os.path.splitext(os.path.basename(path))[0]


def _match_atom(body: str, atoms_by_id: Dict[str, Any]) -> Optional[str]:
    """Return the one atom whose body is the legacy document's byte-exact suffix.

    The migration moved an unknown PREFIX into the atom header; reconstructing which
    header lines moved proved brittle (the second attempt over-stripped ``Class:`` lines
    the migration retained). The invariant has no header rules to guess: after trailing
    whitespace normalization, the preserved atom body must be the document's suffix.
    Zero or multiple candidates fail loud as UNMATCHED rather than committing a guessed
    art_id."""
    if not body:
        return None
    doc_body = body.rstrip()
    candidates: List[str] = []
    for aid, atom in atoms_by_id.items():
        atom_tail = str((atom or {}).get("body") or "").rstrip()
        if len(atom_tail) > _MIN_SUFFIX_CHARS and doc_body.endswith(atom_tail):
            candidates.append(aid)
    return candidates[0] if len(candidates) == 1 else None


def build_map(family: Optional[Any] = None) -> Dict[str, Any]:
    """original_slug -> {art_id, matched} for every doc deleted by the migration.

    Match is self-verifying: exactly one non-trivial atom body must be a byte-exact
    suffix of the recovered document (see _match_atom). Unmatched slugs are kept with
    art_id=None so the hole is a datum, not an absence."""
    if family is None:
        family = _atoms.AtomFamily(store=_default_store())
    atoms_by_id: Dict[str, Any] = {}
    for atom in family.find():
        atoms_by_id[atom["id"]] = atom
    out: Dict[str, Any] = {}
    for path in _deleted_docs():
        slug = _slug_of(path)
        body = _pre_delete_body(path)
        art = _match_atom(body, atoms_by_id) if body is not None else None
        out[slug] = {"art_id": art, "path": path, "matched": art is not None}
    return out


def write_map(path: str = MAP_PATH, family: Optional[Any] = None) -> Dict[str, Any]:
    """Build and persist the map (the committed artifact the design promised)."""
    import json
    m = build_map(family)
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1, sort_keys=True)
    return m


def load_map(path: str = MAP_PATH) -> Dict[str, Any]:
    """The persisted map; {} when absent (fail-soft -- a missing map means the corpus
    still answers by content, just not by original handle)."""
    import json
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    try:
        with open(full, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _default_store() -> Any:
    try:
        from core.foundation.store import create_store
        return create_store(prefer_redis=True)
    except Exception:
        return None


def main(argv: Optional[List[str]] = None) -> int:
    """py -m core.library.legacy_map [--write] -- build (and optionally persist) the map."""
    import argparse
    ap = argparse.ArgumentParser(description="build the legacy_path -> art_id map")
    ap.add_argument("--write", action="store_true", help="persist to store/docs/legacy_map.json")
    args = ap.parse_args(argv)
    fam = _atoms.AtomFamily(store=_default_store())
    if args.write:
        m = write_map(family=fam)
    else:
        m = build_map(family=fam)
    matched = sum(1 for r in m.values() if r.get("matched"))
    print(f"legacy_map: {matched}/{len(m)} deleted docs matched to one atom by suffix identity")
    for slug, rec in sorted(m.items()):
        if not rec.get("matched"):
            print(f"  UNMATCHED: {slug} ({rec.get('path')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
