#!/usr/bin/env python3
"""check_verbatim_citation.py -- T031 hook 4: M6's forcing function at ship time.

M6's bar: zero decisions resting on evidence that lives only in a bus stream or a chat
scroll. The mechanical form: a ship message that CARRIES a gate decision (GATE
GREEN/RED, AFFIRM, verify record/verdict) must cite a research/reviewed/ path -- the
persisted verbatim record that decision rests on. There is NO hatch: the record must
exist anyway; citing it costs one path.

Usage (ship.py passes the message):  check_verbatim_citation.py <message>
       check_verbatim_citation.py --audit N     # M6 metric over the last N commits
Exit 0 = pass; exit 1 = the gate holds the ship.
"""
import argparse
import re
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # T104-M1 depth
GATE_RE = re.compile(
    r"\bGATE\s*:?\s*(GREEN|RED)\b|\bAFFIRM(?:ED)?\b|\bverify\s+(?:record|verdict)\b",
    re.IGNORECASE)
# Atom-era homes (P3 migration): verbatim records are report ATOMS -- cite the projection
# path (docs/library/report/...) or the atom id itself; the legacy research/reviewed/
# form stays accepted for pre-migration history (--audit walks old commits).
CITE_RE = re.compile(
    r"research/reviewed/[A-Za-z0-9_\-./]+\.md"
    r"|docs/library/report/[A-Za-z0-9_\-./]+\.md"
    r"|\bart_\d{8}_[a-z0-9\-]+_[0-9a-f]{6}\b")


def _check(message: str) -> int:
    if not GATE_RE.search(message):
        print("PASS: no gate-decision language -- M6 linter does not apply.")
        return 0
    if CITE_RE.search(message):
        print("PASS: gate decision cites its verbatim record.")
        return 0
    print("FAIL: this ship message carries a GATE decision with no verbatim record cited "
          "(method baseline M6 -- decisions never rest on bus-stream/chat-scroll evidence).")
    print("Fix: mint the peer verdict as a report atom (py agent_cli.py doc new --type report "
          "...) and cite its projection path (docs/library/report/...) or atom id in the message.")
    return 1


def _audit(n: int) -> int:
    log = subprocess.run(["git", "log", f"-n{n}", "--format=%x01%h%x09%s%n%b"],
                         capture_output=True, cwd=ROOT, encoding="utf-8",
                         errors="replace").stdout or ""
    total = missing = 0
    for block in log.split("\x01"):
        if not block.strip():
            continue
        total_gate = GATE_RE.search(block)
        if not total_gate:
            continue
        total += 1
        if not CITE_RE.search(block):
            missing += 1
            print(f"  MISSING {block.splitlines()[0][:90]}")
    ok = total - missing
    pct = (100.0 * ok / total) if total else 100.0
    print(f"M6 verbatim-citation compliance: {ok}/{total} gate-language commits cite a "
          f"record ({pct:.0f}%)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=int, default=0, metavar="N")
    ap.add_argument("message", nargs="?", default="")
    args = ap.parse_args()
    return _audit(args.audit) if args.audit else _check(args.message)


if __name__ == "__main__":
    sys.exit(main())
