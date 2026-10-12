"""gen_cli_reference -- regenerate the docs site's full command reference from the CLI itself.

    uv run python scripts/generators/gen_cli_reference.py          # writes the page
    uv run python scripts/generators/gen_cli_reference.py --check  # exit 1 when the page is stale

Writes apps/docs/content/docs/reference/cli.mdx: every verb, what it does, its flags, and how
its output reads. Verbs, purposes and flags come from build_parser() (the same introspection as
docs/DOORS.md, via gen_doors.cli_verbs), so the page cannot drift from the code. A verb that has
been converted to the agent and human output modes shows its measured before/after results and
a sample of its agent output, read from research/axi-bench/<verb>.json, the report the AXI bench
writes (scripts/axi_bench/harness.py).

Everything generated sits in headings, tables and code blocks, which the docs checker reads as
reference rather than prose; only the short hand-written introduction below is prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "apps" / "docs" / "content" / "docs" / "reference" / "cli.mdx"
BENCH = ROOT / "research" / "axi-bench"
REPO = "https://github.com/balanced7/akashic-aurora/blob/master"
SAMPLE_LINES = 24

INTRO = """---
title: All commands
description: Every Aurora verb with its flags, generated from the CLI itself, and how each one prints for agents and for people.
---

This page lists every verb the `aurora` command offers. A script builds it from the CLI's own parser, so it always matches the code. For the verbs you will use most, start with [Commands](/docs/reference/commands).

Each verb prints for an agent or for a person. [Commands](/docs/reference/commands) explains how to choose with `--output agent` or `--output human`. A verb marked as converted has been measured before and after the change. The bench gives a reader model only the verb's output and checks its answers against known data.
"""


def _cell(text: str) -> str:
    """One table cell: a single line, with the characters MDX would read as markup escaped
    (`<` starts JSX, `{` starts an expression)."""
    parts = " ".join(str(text).split()).split("`")
    for i, part in enumerate(parts):
        part = part.replace("|", "\\|")
        if i % 2 == 0:  # outside a code span; inside one, MDX shows characters as written
            for raw, safe in (("<", "&lt;"), (">", "&gt;"), ("{", "\\{"), ("}", "\\}")):
                part = part.replace(raw, safe)
        parts[i] = part
    return "`".join(parts) or " "


def _bench(verb: str) -> dict | None:
    path = BENCH / f"{verb}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _status_rows(verb: str, rep: dict | None) -> list[str]:
    if not rep:
        return ["| Output | One format for every reader. Not converted to agent and human modes yet. |"]
    b, a = rep["before"], rep["after"]

    def pct(x, y):
        return f"{(y - x) / x:+.0%}" if x else "n/a"

    acc = f"{b['accuracy']:.0%} before, {a['accuracy']:.0%} after"
    tok = f"{b['output_tokens']:,} before, {a['output_tokens']:,} after ({pct(b['output_tokens'], a['output_tokens'])})"
    link = f"[bench report]({REPO}/research/axi-bench/{verb}.md)"
    return [
        "| Output | Agent mode (TOON) and human mode (colour). |",
        f"| Reader accuracy | {acc} |",
        f"| Output tokens | {tok} |",
        f"| AXI checks | {b['conformance_passed']} before, {a['conformance_passed']} after. {link} |",
    ]


def render(verbs: dict) -> str:
    converted = sum(1 for v in verbs if _bench(v))
    lines = [INTRO, f"{len(verbs)} verbs; {converted} converted to agent and human output.", ""]
    for verb, info in verbs.items():
        rep = _bench(verb)
        lines += [
            f"## `{verb}`",
            "",
            "| | |",
            "|---|---|",
            f"| Does | {_cell(info['help'])} |",
            *_status_rows(verb, rep),
            "",
        ]
        if info["args"]:
            lines += ["| Flag | Required | Values | What it does |", "|---|---|---|---|"]
            for flag, required, choices, text in info["args"]:
                lines.append(f"| `{_cell(flag)}` | {'yes' if required else ' '} | {_cell(choices)} | {_cell(text)} |")
            lines.append("")
        if rep:
            run = next(iter(rep["after"]["runs"].values()))
            sample = run["stdout"].rstrip().splitlines()
            if len(sample) > SAMPLE_LINES:
                sample = [*sample[:SAMPLE_LINES], f"... ({len(sample) - SAMPLE_LINES} more lines)"]
            lines += [
                f"Agent output of `aurora {' '.join(run['argv'])}` on the bench data:",
                "",
                "```text",
                *sample,
                "```",
                "",
            ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="regenerate the docs site's full command reference")
    ap.add_argument("--check", action="store_true", help="exit 1 if the page is stale")
    a = ap.parse_args(argv)
    from scripts.generators.gen_doors import cli_verbs

    text = render(cli_verbs())
    if a.check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != text:
            print(f"stale: {OUT.relative_to(ROOT)} -- run scripts/generators/gen_cli_reference.py")
            return 1
        print(f"fresh: {OUT.relative_to(ROOT)}")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
