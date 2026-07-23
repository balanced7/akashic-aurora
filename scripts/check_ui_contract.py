"""check_ui_contract.py — the design CONTRACT's enforcement teeth (organ 2's [M] half).

The three cheapest measurable clauses from design/CONTRACT.md v0, enforced
as source-level checks against scripts/bifrost_ui.py — no DOM parsing, no
browser, no Daniel-gate dependency. Same genus as check_boundaries.py and
mojibake_signatures.py: exit 0 = clean, exit 1 = contract violation found.

Run: py scripts/check_ui_contract.py          (default: bifrost_ui.py)
     py scripts/check_ui_contract.py --help

CHECKS (each maps to a design-contract [M] clause):
  M-L8  TOKEN LAW: no raw CSS hex color (#fff, #a1b2c3, etc.) at call sites —
        use the CSS variable name instead. A raw hex is a lint failure.
  M-L1  AXIS LAW: every gauge element must carry data-agent AND title attributes.
        Counts gauge-producing template lines vs attribute-bearing lines;
        mismatch = violation.
  M-L3  EARNED-ACCENT: alarm-color CSS classes (tripped, warn, high) must appear
        on the same line or the line immediately preceding a state-check predicate
        (runner===, workN>, legacyN>, pages>, allQuiet). Proximity-based heuristic;
        false positives are educational (flag a color assignment worth verifying).

STATUS: v0 — mechanical [M] clauses only. [T] clauses need sighted fence + Daniel
gate, not this script. Add clauses as the contract ratifies them.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "scripts" / "bifrost_ui.py"


# ---------------------------------------------------------------- M-L8: token law
def _check_raw_hex(lines: list[str]) -> list[str]:
    """No raw hex color in CSS — use CSS variable names.
    ALLOWS: --name:#hex (token definitions), var(--name, #fallback)
    FLAGS: standalone #hex at CSS property call sites and JS color literals."""
    problems: list[str] = []
    # Pattern: a #hex that is NOT part of a --custom-property definition
    # and NOT inside a var(...) fallback
    in_css = False
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Track CSS block boundaries
        if stripped.startswith("<style>") or stripped == "<style>":
            in_css = True
            continue
        if stripped.startswith("</style>") or stripped == "</style>":
            in_css = False
            continue

        # Remove var(...) contents to avoid flagging fallbacks
        cleaned = re.sub(r"var\([^)]*\)", "var(--replaced)", line)
        # Remove CSS custom property definitions: --name:#hex;
        cleaned = re.sub(r"--[\w-]+\s*:\s*#[0-9a-fA-F]+", "--name:var", cleaned)

        for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", cleaned):
            pos = m.start()
            # Skip if inside a JS comment
            before = line[:pos]
            if "//" in before.split("\n")[-1] if "\n" in before else "//" in before:
                continue
            # Skip if inside a CSS comment
            if "/*" in line[:pos] and "*/" in line[pos:]:
                continue
            problems.append(
                f"  L{i}: raw hex '{m.group()}' — use a CSS variable instead "
                f"({'CSS' if in_css else 'JS'} context, token law M-L8)")
    return problems


# ---------------------------------------------------------------- M-L1: axis law
def _check_gauge_axes(lines: list[str]) -> list[str]:
    """Every gauge element carries data-agent + title attributes."""
    problems: list[str] = []
    # Count gauge templates: lines with 'class="er-gauge"'
    gauge_lines: list[int] = []
    # Count which have both data-agent AND title
    has_agent: set[int] = set()
    has_title: set[int] = set()

    for i, line in enumerate(lines, 1):
        if 'class="er-gauge"' in line or "class='er-gauge'" in line:
            gauge_lines.append(i)
            if "data-agent=" in line:
                has_agent.add(i)
            if "title=" in line:
                has_title.add(i)

    for ln in gauge_lines:
        if ln not in has_agent:
            problems.append(
                f"  L{ln}: gauge element missing data-agent attribute "
                f"(axis law M-L1 — every gauge must label what it measures)")
        if ln not in has_title:
            problems.append(
                f"  L{ln}: gauge element missing title attribute "
                f"(axis law M-L1 — every gauge must carry a hover explanation)")

    return problems


# ---------------------------------------------------------------- M-L3: earned-accent
def _check_earned_accent(lines: list[str]) -> list[str]:
    """Alarm colors only on alarm states. Proximity heuristic.

    FENCE-CORRECTED (2026-07-23, claude fence RED #1/#2):
    - ALARM_CLASSES uses word-boundary regex so --warn-ink doesn't fire on "warn".
    - STATE_PREDICATES omits 'tripped' — relational checks (=== 'tripped') are
      distinct from class-assignment uses ('tripped') so a bare token can't self-
      satisfy. Custom-property names (--[\w-]+) are stripped before matching.
    """
    problems: list[str] = []
    _tok = re.compile(r"\b(tripped|warn|high)\b")
    # Relational / comparison patterns — the word IS being checked, not assigned
    _pred = re.compile(r"===\s*['\"]tripped|===\s*['\"]blocked|state\s*===\s*['\"]tripped",
                       re.IGNORECASE)
    _state = re.compile(r"\b(runner===|workN>|legacyN>|pages>|allQuiet|blocked|offline|"
                        r"!==\s*'active'|>\s*0|>\s*10|>\s*100)\b")

    for i, line in enumerate(lines, 1):
        # Strip CSS custom-property names before matching (--warn-ink -> removed)
        cleaned = re.sub(r"--[\w-]+", "--var", line)
        tokens = {m.group(1) for m in _tok.finditer(cleaned)}
        if not tokens:
            continue

        stripped = line.strip()
        # Allow: CSS class definitions like .tripped { ... }
        if any("." + t in stripped and "{" in stripped for t in tokens):
            continue
        # Allow: comments
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # Check this line AND the previous line for a state predicate
        prev = lines[i - 2] if i >= 2 else ""
        ctx = prev + " " + cleaned
        if _pred.search(ctx) or _state.search(ctx):
            continue

        problems.append(
            f"  L{i}: alarm-class token(#{'|'.join(tokens)}) without visible "
            f"state-check predicate on this or previous line — verify it is "
            f"alarm-gated (earned-accent law M-L3)")

    return problems


# ---------------------------------------------------------------- driver
def check_file(path: Path) -> int:
    if not path.exists():
        print(f"[ui-contract] SKIP: {path} not found")
        return 0

    lines = path.read_text(encoding="utf-8").split("\n")
    all_problems: list[str] = []

    for name, fn in [("token law M-L8", _check_raw_hex),
                     ("axis law M-L1", _check_gauge_axes),
                     ("earned-accent M-L3", _check_earned_accent)]:
        hits = fn(lines)
        if hits:
            all_problems.append(f"[ui-contract] {name}: {len(hits)} violation(s)")
            all_problems.extend(hits)

    if all_problems:
        print("\n".join(all_problems))
        return 1

    print(f"[ui-contract] CLEAN: {path.name} passes all [M] clause checks")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="UI design-contract [M] clause enforcement (organ 2's teeth)")
    ap.add_argument("file", nargs="?", default=str(DEFAULT),
                    help=f"UI file to check (default: {DEFAULT})")
    args = ap.parse_args(argv)
    return check_file(Path(args.file))


if __name__ == "__main__":
    sys.exit(main())
