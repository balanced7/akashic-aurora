"""mojibake_signatures.py — rule-8 pre-commit guard (D3, deepseek 2026-07-22).

The byte-level mojibake detector: scans tracked .md files for known corruption
signatures that indicate an encoding failure — replacement characters, mixed-encoding
artifacts, and truncated multibyte sequences. This is the pre-commit REFUSE door;
check_boundaries is the post-hoc backstop (rule 9+10+11).

Run as a pre-commit hook at mirror.py commit time, or standalone:
  py scripts/githooks/mojibake_signatures.py <file>.md ...    # check named files
  py scripts/githooks/mojibake_signatures.py --staged          # check all staged .md

Exit 0 = clean; exit 1 = mojibake found (commit REFUSED).

SIGNATURES (the known corruption trace classes):
  S1 REPLACEMENT-CHAR  U+FFFD in UTF-8 = b'\xef\xbf\xbd' — the universal "I couldn't
     decode this byte" marker. A valid .md file should never contain this; its presence
     means a round-trip through a broken codec.
  S2 LONE-SURROGATE   U+D800–U+DFFF — surrogates are a UTF-16 concept that MUST NOT
     appear in valid UTF-8. Their presence means raw UTF-16 leaked into the file.
  S3 SMART-QUOTE-MOJ  cp1252 curly quotes decoded as Latin-1 then encoded as UTF-8
     produces \u00e2\u0080\u009c/\u009d ("â\u0080\u009c") — the classic double-encode.
  S4 TRUNCATED-UTF8    A byte matching 0xE0–0xEF followed by <2 continuation bytes
     (0x80–0xBF) at end-of-line — a split multibyte character. Common from terminal
     cut/paste at a 80-char boundary.
  S5 NULL-BYTES        b'\x00' — should never appear in a text file. Indicates binary
     contamination.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# --- Pure byte signatures (are these bytes present in the raw file?) ---
# Each is (name, byte_pattern, human_description)
BYTE_SIGNATURES = [
    ("REPLACEMENT-CHAR", b"\xef\xbf\xbd",
     "U+FFFD replacement character — a codec round-trip corrupted this byte"),
    ("NULL-BYTES", b"\x00",
     "null byte — binary contamination, not valid text"),
]

# --- Regex patterns applied to the decoded UTF-8 text ---
TEXT_SIGNATURES = [
    ("LONE-SURROGATE", re.compile(r"[\ud800-\udfff]"),
     "lone surrogate (U+D800–U+DFFF) — raw UTF-16 leaked into the file"),
    ("SMART-QUOTE-MOJ", re.compile(r"\u00e2\u0080[\u009c\u009d]"),
     "cp1252 smart-quote double-encode (â\u0080\u009c/â\u0080\u009d) — 'smart quotes' corrupted by wrong codec"),
]


def _truncated_utf8_sig(data: bytes):
    """S4: multibyte leader at end-of-line with missing continuation bytes.
    Returns a list of (line_number, description)."""
    lines = data.split(b"\n")
    hits = []
    for i, line in enumerate(lines, 1):
        if not line:
            continue
        last = line[-1]
        if 0xC0 <= last <= 0xFD:
            hits.append((i, f"line {i}: truncated UTF-8 leader byte 0x{last:02x} at EOL"))
    return hits


def check_file(path: Path) -> list[str]:
    """Scan one .md file. Returns a list of problem descriptions (empty = clean)."""
    problems = []
    try:
        raw = path.read_bytes()
    except Exception as e:
        return [f"cannot read {path}: {e}"]

    # Byte-level signatures
    for name, pattern, desc in BYTE_SIGNATURES:
        if pattern in raw:
            idx = raw.index(pattern)
            start = max(0, idx - 20)
            end = min(len(raw), idx + len(pattern) + 20)
            context = raw[start:end].decode("utf-8", errors="replace")
            problems.append(f"S1/{name}: {desc} at byte {idx} "
                            f"(context: …{repr(context)}…)")

    # Truncated UTF-8 at EOL
    for lineno, desc in _truncated_utf8_sig(raw):
        problems.append(f"S4/TRUNCATED-UTF8: {desc}")

    # Text-level signatures (decode once)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        problems.append("S2/UTF8-INVALID: file is not valid UTF-8")
        return problems

    for name, pattern, desc in TEXT_SIGNATURES:
        for m in pattern.finditer(text):
            ctx = text[max(0, m.start() - 10):m.end() + 10]
            problems.append(f"S{3 if name == 'SMART-QUOTE-MOJ' else 2}/{name}: "
                            f"{desc} at char {m.start()} (context: …{ctx}…)")

    return problems


def staged_md_files() -> list[Path]:
    """List of staged .md files in the git repo (diff --cached --name-only)."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return []
        return [ROOT / f for f in r.stdout.strip().split("\n") if f.endswith(".md") and os.path.isfile(ROOT / f)]
    except Exception:
        return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Rule-8 mojibake pre-commit guard: REFUSE commits containing "
                    "known byte-level corruption signatures in .md files.")
    ap.add_argument("files", nargs="*", help=".md files to check")
    ap.add_argument("--staged", action="store_true",
                    help="check all staged .md files (git diff --cached)")
    args = ap.parse_args(argv)

    paths: list[Path] = [Path(f) for f in args.files]
    if args.staged:
        staged = staged_md_files()
        paths.extend(staged)
        if not staged:
            print("[mojibake] no staged .md files — nothing to check")
            return 0
    if not paths:
        print("[mojibake] no files specified — pass .md paths or --staged")
        return 0

    all_problems = 0
    for p in paths:
        if not p.suffix == ".md":
            continue
        if not p.exists():
            print(f"[mojibake] SKIP {p}: not found")
            continue
        hits = check_file(p)
        if hits:
            all_problems += len(hits)
            print(f"[mojibake] REFUSE {p}: {len(hits)} issue(s)")
            for h in hits:
                print(f"  • {h}")
    if all_problems:
        print(f"\n[mojibake] COMMIT REFUSED: {all_problems} mojibake issue(s). "
              f"Fix the source file (not the .md — fix what PRODUCED the bytes). "
              f"Re-save with correct UTF-8 encoding and re-stage.")
        return 1
    print(f"[mojibake] CLEAN: {len(paths)} file(s) scanned, zero mojibake")
    return 0


if __name__ == "__main__":
    sys.exit(main())
