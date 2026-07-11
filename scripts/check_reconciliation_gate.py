#!/usr/bin/env python3
"""check_reconciliation_gate.py -- T031 hook 1: the method baseline's lead forcing function.

M1's contract, enforced at ship time (deepseek's design: "without it, we're just two
agents chatting"): a slice that stages files under the TRUST/COORDINATION SUBSTRATE --
where wrongness is expensive by P0's revert-cost anchor -- must cite an existing
reconciliation artifact (a docs/ or research/reviewed/ .md that actually carries a
reconciliation/GATE record) in its ship message. The [ungated: <reason>] hatch allows a
deliberate exception LOUDLY (an UNGATED audit line the wrap scorecard reads) -- skipped-
with-reason, never silently.

Usage (ship.py passes these):  check_reconciliation_gate.py [--root R] <message> <path>...
Exit 0 = pass; exit 1 = the gate holds the ship.
"""
import argparse
import os
import re
import sys

# Where wrongness is expensive (P0 revert-cost anchor): identity/grants, the bus and its
# consumers, the ledger/conductor, the event substrate. Render surfaces and tests are
# deliberately NOT here -- the gate must stay proportionate or it becomes ceremony.
PROTECTED_PREFIXES = (
    "core/trust/", "core/comm/", "core/coord/", "core/events/", "security/",
)

CITATION_RE = re.compile(r"(?:docs|research/reviewed)/[A-Za-z0-9_\-./]*?\.md")
MARKER_RE = re.compile(r"reconcil|GATE", re.IGNORECASE)
HATCH_RE = re.compile(r"\[ungated:\s*([^\]]+?)\s*\]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("message")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()

    protected = sorted({p for p in args.paths
                        if p.replace("\\", "/").lstrip("./").startswith(PROTECTED_PREFIXES)})
    if not protected:
        print("PASS: no substrate paths staged -- ungated slice, gate does not apply.")
        return 0

    hatch = HATCH_RE.search(args.message)
    if hatch:
        reason = hatch.group(1).strip()
        if reason:
            print(f"PASS: UNGATED substrate ship (reason: {reason}) -- audit line for the "
                  f"wrap scorecard; paths: {', '.join(protected)}")
            return 0
        print("FAIL: [ungated: ] carries no reason -- the hatch is skipped-WITH-REASON, "
              "never a blank pass.")
        return 1

    cited = CITATION_RE.findall(args.message)
    satisfied, problems = [], []
    for rel in cited:
        full = os.path.join(args.root, rel.replace("/", os.sep))
        if not os.path.isfile(full):
            problems.append(f"cited {rel} does not exist")
            continue
        try:
            text = open(full, encoding="utf-8", errors="replace").read()
        except OSError as e:
            problems.append(f"cited {rel} unreadable ({e})")
            continue
        if MARKER_RE.search(text):
            satisfied.append(rel)
        else:
            problems.append(f"cited {rel} carries no reconciliation/GATE record")

    if satisfied:
        print(f"PASS: substrate ship cites reconciliation artifact(s): {', '.join(satisfied)}")
        return 0

    print("FAIL: this ship stages TRUST/COORDINATION SUBSTRATE paths with no reconciliation "
          "artifact cited (method baseline M1 -- the fence gates the commit):")
    for p in protected:
        print(f"  substrate: {p}")
    for p in problems:
        print(f"  problem:   {p}")
    if not cited:
        print("  problem:   no docs/ or research/reviewed/ .md cited in the ship message")
    print("Fix: cite the dated dual-half build spec (docs/... or research/reviewed/...) in "
          "the message, or -- deliberately and auditably -- add [ungated: <reason>].")
    return 1


if __name__ == "__main__":
    sys.exit(main())
