"""gen_arch_index -- regenerate docs/MODULE_INDEX.md from every module's one-line docstring.

The companion to docs/ARCHITECTURE.md: that file is stable-altitude prose (hand-maintained,
rarely changes); THIS produces the churny per-module detail automatically, so it can never rot.
Every module's line-1 docstring IS its spec -- if a module has none, it shows as (no docstring),
which is itself a useful signal (a module that can't state its one job in a line is a smell).

Run:  py scripts/generators/gen_arch_index.py            # writes docs/MODULE_INDEX.md
      py scripts/generators/gen_arch_index.py --check    # exit 1 if the file is stale (for CI/pre-ship)
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth

# Derived docs are a claim about the REPOSITORY, so discovery reads tracked content, never
# the working tree. os.listdir here emitted rows for untracked modules and red-lined CI for
# 15+ runs (see scripts/generators/_tracked.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tracked import tracked_py, is_tracked_dir  # noqa: E402
OUT = os.path.join(ROOT, "docs", "MODULE_INDEX.md")

# Areas surveyed, in reading order. Kept in sync with the layers in ARCHITECTURE.md.
CORE_ORDER = [
    "foundation", "events", "signals", "comm", "coord",
    "learning", "recall", "primitives", "renew", "narrative",
    "trust", "fleet", "state", "codex", "perspectives",
]


def first_doc(path):
    try:
        d = ast.get_docstring(ast.parse(open(path, encoding="utf-8").read()))
        if d:
            return " ".join(d.strip().splitlines()[0].split())[:110]
    except Exception:
        pass
    return "(no docstring)"


def modules(rel):
    if not is_tracked_dir(rel):
        return []
    return tracked_py(rel)


def render():
    lines = [
        "# Module Index (auto-generated)",
        "",
        "> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_arch_index.py`.",
        "> The big picture lives in [ARCHITECTURE.md](ARCHITECTURE.md); this is the per-module detail,",
        "> each module's line-1 docstring = its single responsibility.",
        "",
    ]
    # core/ subpackages, known ones first (in layer order), then any newcomers (flagged)
    present = [d for d in os.listdir(os.path.join(ROOT, "core"))
               if os.path.isdir(os.path.join(ROOT, "core", d)) and not d.startswith("__")
               and is_tracked_dir(f"core/{d}")]
    ordered = [d for d in CORE_ORDER if d in present] + sorted(set(present) - set(CORE_ORDER))
    for sub in ordered:
        new = "  ⚠️ NOT in ARCHITECTURE.md layer order — add it there" if sub not in CORE_ORDER else ""
        mods = modules(f"core/{sub}")
        lines.append(f"## core/{sub}/  ({len(mods)} modules){new}")
        for m in mods:
            lines.append(f"- `{m}` — {first_doc(os.path.join(ROOT, 'core', sub, m))}")
        lines.append("")
    # top-level entry points
    lines.append("## entry points (repo root)")
    for f in tracked_py(""):
        lines.append(f"- `{f}` — {first_doc(os.path.join(ROOT, f))}")
    lines.append("")
    # scripts/
    lines.append("## scripts/")
    for m in modules("scripts"):
        lines.append(f"- `{m}` — {first_doc(os.path.join(ROOT, 'scripts', m))}")
    lines.append("")
    return "\n".join(lines)


def main():
    body = render()
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current.strip() != body.strip():
            print("STALE: docs/MODULE_INDEX.md is out of date -- run `py scripts/generators/gen_arch_index.py`")
            return 1
        print("PASS: docs/MODULE_INDEX.md is current.")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"wrote {OUT} ({body.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
