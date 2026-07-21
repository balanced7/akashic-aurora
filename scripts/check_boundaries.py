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
6. singleton-honors-isolation  : a module-level singleton cache (`_INSTANCE(S)` or a
   private Optional-annotated None default) must honor _AISETUP_TEST_ISOLATED in the
   same file -- else the first door-touch under live env pins live-bound instances for
   every later isolated consumer (T069, reconciled spec:
   research/reviewed/t069-singleton-reconciliation-2026-07-15.md). Factories whose
   explicit-injection path IS the isolation are allowlisted (deepseek census, Part c).

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
    # fast_cache.py DELETED 2026-07-07 (arch-triage P2: dead, zero live consumers) -> its 3 debt
    # entries + the SessionRecovery dup (resolved: checkpoint's class renamed CheckpointRecovery) are gone.
    ("no-duplicate-module-basename", "schema.py"):
        "intentional per-package convention: core/{codex,narrative,perspectives}/schema.py are always "
        "imported via the full package path (never `from core import schema`), so no shadowing hazard",
    # T069 census (deepseek Part c): injection-path isolation -- get_x(store=...) IS the
    # isolated path; the canonical singleton is a lazy stateless wrapper. Tracked, not silent.
    ("singleton-honors-isolation", "core/comm/blobs.py"):
        "BlobStore binds the AI_SETUP dir (already temp under isolation); injection path exists",
    ("singleton-honors-isolation", "core/primitives/embedder.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/primitives/clusterer.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/primitives/consolidator.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/narrative/tag_audit.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/narrative/tag_governance.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/narrative/theme_assigner.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/narrative/theme_discovery.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    ("singleton-honors-isolation", "core/narrative/track_router.py"):
        "store= injection path is the isolation (deepseek T069 census)",
    # T099 V0 (2026-07-20) added core/toolbelt/registry.py; core/trust/registry.py predates
    # it. Both are ALWAYS imported by full package path (core.toolbelt.registry /
    # core.trust.registry), never `from core import registry` -- same no-shadowing-hazard
    # rationale as the schema.py allowlist above.
    ("no-duplicate-module-basename", "registry.py"):
        "two registries by deliberate design (toolbelt verb-registry vs trust ACL-registry); "
        "always imported by full package path, never `from core import registry`",
}

REDIS_CONNECTOR = "core/foundation/redis_connection.py"

# W38 rule-7: durable Store families -- legitimately Redis-only-plus-File, classified by
# the heal's File-family check at RUNTIME, never in EPHEMERAL_PREFIXES. A new durable
# family goes HERE (a conscious "this persists" decision), an ephemeral one in the roster.
DURABLE_FAMILIES = frozenset({
    "events", "learn", "narr", "mem", "codex", "resource", "atom", "chronicle",
    "coord", "reinforce", "skill", "settings",
})
# Families that appear in ns-key POSITION but are not live Redis families (probes/docs).
_FAMILY_ALLOWLIST = frozenset({"NAMESPACE"})
_NS_KEY_RE = re.compile(r"\{[\w.]*_?ns(?:\(\))?\}:([a-z_]+)")


def _ns_families(text: str) -> set:
    """Every `{ns}:<family>`, `{_ns()}:<family>`, `{self.ns}:<family>` family token in
    the text -- the families a module constructs Redis keys for (W38)."""
    return set(_NS_KEY_RE.findall(text or ""))


def _unregistered_families(text: str) -> set:
    """Families this text constructs that are NEITHER ephemeral-roster-matched NOR
    durable-allowlisted -- the register-at-ship-time gap. Fail-open on import error."""
    try:
        from core.comm.packet_spec import is_ephemeral_key
    except Exception:
        return set()
    out = set()
    for fam in _ns_families(text):
        if fam in DURABLE_FAMILIES or fam in _FAMILY_ALLOWLIST:
            continue
        if not is_ephemeral_key(f"bifrost:{fam}:probe"):
            out.add(fam)
    return out


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
    singleton_decl = re.compile(
        r"^_INSTANCES?\s*[:=]|^_[a-z_]+\s*:\s*Optional\[[A-Za-z_.\[\]]+\]\s*=\s*None")

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
        singleton_line = next((i for i, ln in enumerate(text.splitlines(), 1)
                               if singleton_decl.match(ln)), None)
        if singleton_line and "_AISETUP_TEST_ISOLATED" not in text:
            record("singleton-honors-isolation", rel,
                   f"{rel}:{singleton_line} module-level singleton cache without an "
                   f"_AISETUP_TEST_ISOLATED branch (T069)")
        # W38 rule-7 (register-at-ship-time): a core/comm module minting a new Redis key
        # family must classify it (ephemeral roster or DURABLE_FAMILIES) -- else it grows
        # a mailbox-style UNKNOWN heal wall. Scoped to the transport keyspace.
        if rel.startswith("core/comm/"):
            for fam in sorted(_unregistered_families(text)):
                record("redis-family-registered", f"{rel}:{fam}",
                       f"{rel} constructs `{{ns}}:{fam}:...` but '{fam}' is not in "
                       f"packet_spec.EPHEMERAL_PREFIXES nor DURABLE_FAMILIES -- register it "
                       f"(ephemeral-by-design -> roster; persisted -> durable allowlist)")
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
