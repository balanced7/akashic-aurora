"""gen_physics_sheet -- regenerate docs/PHYSICS.md: the machinery's mechanical truths, derived.

The master-map charter's M2b static half (Daniel's ask 2026-07-19: "are we aware right now of
the mechanical constraints... for every piece of our machinery?" -- the honest answer was
"in code, discovered by collision"). This script ends discovered-by-collision for the STATIC
truths: every env flag and every numeric bound is greppable, so the sheet derives -- it can
never rot, only regenerate. Dynamic truths (throughput/latency envelopes) need MEASUREMENT
drills and are explicitly out of scope here (charter M2b, benchmark half).

Run:  py scripts/generators/gen_physics_sheet.py            # writes docs/PHYSICS.md
      py scripts/generators/gen_physics_sheet.py --check    # exit 1 if the file is stale (for CI/pre-ship)
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth
OUT = os.path.join(ROOT, "docs", "PHYSICS.md")

# Vendored / heavy / generated dirs -- never part of the machinery's own physics.
SKIP_DIRS = {
    # `scratch` is GITIGNORED by design (LIBRARY.md routes run output, logs and play
    # receipts there). Walking it made this sheet cite files that exist only on the author's
    # machine -- the committed PHYSICS.md referenced scratch/sol_runner_fragments.py, which
    # no other clone has, so CI regenerated a different sheet and called the committed one
    # stale FOREVER. A derived map must be a function of the TRACKED tree, or it cannot be
    # checked anywhere but the machine that wrote it. (lesson: repo_presentation_cleanup --
    # audit what a visitor sees, not what is local.)
    "scratch",
    ".git", ".claude", "__pycache__", ".venv", "venv", "node_modules", "backups", "assets",
    "model_cache", "ollama_data", "rocm-lib", ".pytest_cache", ".mypy_cache",
    "blobs", "dist", "build", "models", "dockerized-ai", "_archive", "ComfyUI-Zluda",
    # tests/ hold FIXTURE constants (a drill's NOW=, GATE=), not machinery physics -- scanning
    # them made the sheet churn on every new test. The sheet is the MACHINERY's constraints.
    "tests",
}

# A numeric module constant counts as a BOUND when its name says so.
_BOUND_WORDS = ("MAX", "MIN", "LIMIT", "TIMEOUT", "TTL", "CAP", "LEN", "BYTES",
                "CHARS", "_MS", "SEC", "FLOOR", "BUDGET", "INTERVAL", "WINDOW",
                "DEPTH", "RETR", "STALE", "THRESH")

_FLAG_RE = re.compile(r"""(?:os\.getenv|os\.environ\.get|_int_env|_bool_env)\(\s*["']([A-Z][A-Z0-9_]+)["']\s*(?:,\s*([^)\n]{0,60}))?""")
_BOUND_RE = re.compile(r"""^\s*(_?[A-Z][A-Z0-9_]*)\s*=\s*(\d[\d_]*)\s*(?:#\s*(.*))?$""")


def _py_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def scan(root_files=None):
    """One walk, two censuses: flags {NAME: [(site, default)]} and bounds
    [(name, value, site, note)]. Pure over file contents -- deterministic by sort."""
    flags, bounds = {}, []
    for path in (root_files or _py_files()):
        rel = _rel(path)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in _FLAG_RE.finditer(line):
                name, default = m.group(1), (m.group(2) or "").strip().rstrip(",")
                flags.setdefault(name, []).append((f"{rel}:{i}", default))
            m = _BOUND_RE.match(line)
            if m and any(w in m.group(1).upper() for w in _BOUND_WORDS):
                bounds.append((m.group(1), int(m.group(2).replace("_", "")),
                               f"{rel}:{i}", (m.group(3) or "").strip()))
    return flags, sorted(bounds, key=lambda b: (b[0], b[2]))


def _head_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:
        return "?"


def render(flags, bounds, sha):
    lines = [
        "# PHYSICS -- mechanical truths of the machinery (auto-generated)",
        "",
        "Status: current",
        "Class: reference",
        "",
        "> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_physics_sheet.py`.",
        f"> Derived at {sha}. A bound you discover by collision is not awareness -- this sheet",
        "> exists so every clip, cap, timeout and flag is READABLE before it is HIT.",
        "> Dynamic envelopes (throughput, latency, limits-under-load) are NOT here: they require",
        "> measurement, not grep -- see the master-map charter M2b (benchmark half).",
        "",
        f"## Configuration flags ({len(flags)} names)",
        "",
        "| Flag | Default (as written) | Read sites |",
        "|---|---|---|",
    ]
    for name in sorted(flags):
        sites = flags[name]
        default = next((d for _, d in sites if d), "")
        shown = ", ".join(s for s, _ in sites[:3]) + (f" +{len(sites) - 3}" if len(sites) > 3 else "")
        lines.append(f"| `{name}` | `{default}` | {shown} |")
    lines += [
        "",
        f"## Mechanical bounds ({len(bounds)} numeric constants)",
        "",
        "| Constant | Value | Site | Note |",
        "|---|---|---|---|",
    ]
    for name, val, site, note in bounds:
        lines.append(f"| `{name}` | {val:,} | {site} | {note[:90]} |")
    lines.append("")
    return "\n".join(lines)


def main():
    flags, bounds = scan()
    text = render(flags, bounds, _head_sha())
    if "--check" in sys.argv:
        try:
            old = open(OUT, encoding="utf-8").read()
        except OSError:
            print("PHYSICS.md missing -- regenerate"); return 1
        # compare bodies minus the derived-at line (sha churn is not staleness)
        strip = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("> Derived at "))
        if strip(old) != strip(text):
            print("PHYSICS.md STALE vs code -- regenerate (py scripts/generators/gen_physics_sheet.py)"); return 1
        print("PHYSICS.md current"); return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(flags)} flags, {len(bounds)} bounds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
