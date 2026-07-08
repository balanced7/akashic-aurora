"""
Boundary guardrails for the clean core/ layer.

Semantic Relationship: Guardrails enforce ArchitecturalBoundaries

WHY THIS EXISTS
---------------
The `core/` layer was rebuilt clean; this keeps it clean as the codebase grows.
Clarity and boundaries only compound if a machine holds the line -- otherwise
entropy creeps back (which is how the outer shell drifted from core/). Each rule
below encodes a boundary we deliberately drew.

Rules (scoped to core/):
1. redis-only-via-connector : only redis_connection.py may import redis directly;
   everyone else goes through connect_to_redis_with_fail_fast (no 48s hangs).
2. no-bare-except           : bare `except:` swallows errors silently -- narrow it.
3. no-syspath-insert        : library modules must not hack sys.path.
4. no-duplicate-class-names : one class name = one definition (ubiquitous language;
   catches accidental concept duplication).
5. no-duplicate-module-basename : one module basename across core/ (catches the
   import-shadowing hazard `from core import X` picks arbitrarily -- e.g. the
   session_state.py collision resolved 2026-07-07). Intentional per-package
   conventions (schema.py) are allowlisted.

Known pre-existing debt is listed in ALLOWLIST with a reason, so it is visible and
tracked rather than silently passing. New violations fail the check.

Run: py scripts/check_boundaries.py     (exit 0 = clean, 1 = new violation)
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))
PROTECTED = ["core"]  # dirs whose boundaries we enforce (add context/ etc. later)

# Pre-existing debt: (rule, relative_path) -> reason. Visible, tracked, not silent.
ALLOWLIST = {
    ("redis-only-via-connector", "core/foundation/fast_cache.py"):
        "pre-existing caching layer; migrate onto Store/connector (audit R3)",
    ("no-syspath-insert", "core/foundation/fast_cache.py"):
        "pre-existing; remove when fast_cache is refactored (audit R3)",
    ("no-bare-except", "core/foundation/fast_cache.py"):
        "11 pre-existing bare excepts; clean when fast_cache is refactored (audit R3)",
    ("no-duplicate-class-names", "SessionRecovery"):
        "pre-existing dup: session_recovery.py vs session_checkpoint.py:350 -- resolve carefully (audit)",
    ("no-duplicate-module-basename", "schema.py"):
        "intentional per-package convention: core/{codex,narrative,perspectives}/schema.py are always "
        "imported via the full package path (never `from core import schema`), so no shadowing hazard",
}

REDIS_CONNECTOR = "core/foundation/redis_connection.py"


def _py_files():
    for d in PROTECTED:
        for p in (ROOT / d).rglob("*.py"):
            if "__pycache__" not in p.parts:
                yield p


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def check() -> int:
    violations = []          # (rule, location, detail)
    allowed_hits = []        # (rule, location) that matched the allowlist
    class_defs = defaultdict(list)  # class name -> [files]
    module_basenames = defaultdict(set)  # basename -> {dirs} (import-shadowing hazard)

    bare_except = re.compile(r"^\s*except\s*:")
    import_redis = re.compile(r"^\s*import\s+redis(\s|$|\.)|^\s*from\s+redis\s+import")
    use_redis = re.compile(r"\bredis\.(Redis|StrictRedis|ConnectionPool)\(")
    syspath = re.compile(r"\bsys\.path\.insert\b")
    classdef = re.compile(r"^class\s+([A-Za-z_]\w*)")

    def record(rule, location, detail):
        if (rule, location) in ALLOWLIST:
            allowed_hits.append((rule, location))
        else:
            violations.append((rule, location, detail))

    for p in _py_files():
        rel = _rel(p)
        if p.name != "__init__.py":
            module_basenames[p.name].add(p.parent.as_posix())
        text = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if bare_except.search(line):
                record("no-bare-except", rel, f"{rel}:{i} bare except")
            if rel != REDIS_CONNECTOR and (import_redis.search(line) or use_redis.search(line)):
                record("redis-only-via-connector", rel, f"{rel}:{i} direct redis use")
            if syspath.search(line):
                record("no-syspath-insert", rel, f"{rel}:{i} sys.path.insert")
            m = classdef.match(line)
            if m:
                class_defs[m.group(1)].append(rel)

    for name, files in class_defs.items():
        if len(set(files)) > 1:
            record("no-duplicate-class-names", name,
                   f"class {name} defined in: {', '.join(sorted(set(files)))}")

    for base, dirs in module_basenames.items():
        if len(dirs) > 1:
            record("no-duplicate-module-basename", base,
                   f"module '{base}' in {len(dirs)} packages: {', '.join(sorted(dirs))}")

    # ---- report ----
    print("=" * 60)
    print("BOUNDARY CHECK (core/)")
    print("=" * 60)
    if allowed_hits:
        print(f"\nKnown debt (allowlisted, {len(allowed_hits)}):")
        for rule, loc in allowed_hits:
            print(f"  - [{rule}] {loc} -- {ALLOWLIST[(rule, loc)]}")
    if violations:
        print(f"\nVIOLATIONS ({len(violations)}):")
        for rule, _loc, detail in violations:
            print(f"  - [{rule}] {detail}")
        print("\nFAIL: new boundary violation(s). Fix, or add to ALLOWLIST with a reason.")
        return 1
    print("\nPASS: no new boundary violations.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
