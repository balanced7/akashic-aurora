"""gen_requirements -- render the pip requirement files from pyproject.toml + uv.lock.

requirements.txt was kept in step with pyproject.toml by hand, and pip still reads it: CI, the
Windows `py` setup (CONTRIBUTING, docs/DEPLOY.md), core/screenspace and
scripts/gemini_web_login.bat. Hand-kept twins drift, so both files are now GENERATED from the
lock: the exact versions `uv sync` installs, for every platform (environment markers included).

    requirements.txt              runtime dependencies + the dev group (pytest runs the suite)
    requirements/gemini-web.txt   the `browser` group (Gemini web door), installed on top

Run:  uv run poe lock                                     # uv lock, then rewrite both files
      uv run python scripts/generators/gen_requirements.py --check   # exit 1 if either is stale
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPORT = ["export", "--frozen", "--no-hashes", "--no-emit-project", "--no-annotate", "--no-header"]
FILES = {
    "requirements.txt": [],
    "requirements/gemini-web.txt": ["--only-group", "browser"],
}


def render(extra):
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("gen_requirements: uv is not on PATH (https://docs.astral.sh/uv/)")
    cmd = ["uv", *EXPORT, *extra]
    body = subprocess.run([uv, *cmd[1:]], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    header = (
        "# GENERATED — do not edit. Source: pyproject.toml + uv.lock.\n"
        "# Regenerate: uv run poe lock   (runs: %s)\n"
        "# pip consumers: pip install -r <this file>. uv users: uv sync.\n" % " ".join(cmd)
    )
    return header + body


def main(argv):
    check = "--check" in argv
    stale = []
    for rel, extra in FILES.items():
        path = os.path.join(ROOT, *rel.split("/"))
        want = render(extra)
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                have = fh.read()
        except FileNotFoundError:
            have = None
        if have == want:
            continue
        if check:
            stale.append(rel)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(want)
        print("wrote %s" % rel)
    if stale:
        print("STALE (hand-edited or not regenerated after uv lock): %s -- run: uv run poe lock" % ", ".join(stale))
        return 1
    if check:
        print("requirement files match uv.lock")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
