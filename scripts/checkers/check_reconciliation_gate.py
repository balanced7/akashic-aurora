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
# consumers, the ledger/conductor, the event substrate -- and the runner scripts, which
# ARE the consume->outcome pipeline (deepseek verify catch: they fell outside core/*).
# Render surfaces and tests are deliberately NOT here -- proportionality over ceremony.
PROTECTED_PREFIXES = (
    "core/trust/", "core/comm/", "core/coord/", "core/events/", "security/",
    "scripts/bifrost_runner",
)

CITATION_RE = re.compile(r"(?:docs|research/reviewed)/[A-Za-z0-9_\-./]*?\.md")
MARKER_RE = re.compile(r"reconcil|GATE", re.IGNORECASE)
HATCH_RE = re.compile(r"\[ungated:\s*([^\]]+?)\s*\]")


def decide(message: str, paths, root: str = "") -> dict:
    """The gate's decision as DATA, shared by ship time and audit time.

    Split out so the wrap scorecard can replay the real verdict instead of regexing commit
    prose. M11 used to count messages containing a docs/*.md path -- deepseek: "a typo fix
    mentioning docs/ARCHITECTURE.md counts as gated; a full-fence slice whose message says only
    'RB-99 landed' does not. Target it upward and you get more doc paths in messages, not more
    gated slices. Goodhart."

    ONE predicate on purpose. An audit that reimplemented this would drift from the live gate
    and we would be measuring a copy of the rule rather than the rule -- the exact disease this
    arc has been chasing.

    Returns {status, detail, protected}:
      NOT_APPLICABLE -- no substrate staged; the gate never applied, so it is not in the
                        denominator. Most commits land here, which is why "% of all commits"
                        was meaningless in both directions.
      PASS           -- substrate staged AND a cited artifact carries a reconciliation/GATE record
      UNGATED        -- deliberate [ungated: reason] exception; counted, never silent
      FAIL           -- substrate staged with no satisfying citation
    """
    root = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    protected = sorted({p for p in (paths or [])
                        if str(p).replace("\\", "/").lstrip("./").startswith(PROTECTED_PREFIXES)})
    if not protected:
        return {"status": "NOT_APPLICABLE", "detail": "no substrate paths staged",
                "protected": []}

    hatch = HATCH_RE.search(message or "")
    if hatch:
        reason = hatch.group(1).strip()
        if not reason:
            return {"status": "FAIL", "detail": "[ungated: ] carries no reason",
                    "protected": protected}
        return {"status": "UNGATED", "detail": reason, "protected": protected}

    satisfied, problems = [], []
    for rel in CITATION_RE.findall(message or ""):
        full = os.path.join(root, rel.replace("/", os.sep))
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
        return {"status": "PASS", "detail": ", ".join(satisfied), "protected": protected}
    return {"status": "FAIL", "detail": "; ".join(problems) or "no artifact cited",
            "protected": protected}


def audit_stats(n: int, root: str = "") -> dict:
    """M11 as NUMBERS: over the last N commits, replay the gate on those that STAGED SUBSTRATE.

    The denominator is the point. Only slices the gate applies to are counted, so the rate
    answers "of the ships that needed a fence, how many had one" rather than "how many commit
    messages happened to mention a markdown file".
    """
    import subprocess
    cwd = root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    raw = subprocess.run(["git", "log", f"-n{n}", "--format=%x01%h%x02%B%x02", "--name-only"],
                         capture_output=True, cwd=cwd, encoding="utf-8",
                         errors="replace").stdout or ""
    applied = passed = ungated = 0
    offenders = []
    for block in raw.split("\x01"):
        if not block.strip():
            continue
        try:
            sha, msg, files = block.split("\x02", 2)
        except ValueError:
            continue
        paths = [l.strip() for l in files.splitlines() if l.strip()]
        v = decide(msg, paths, root=cwd)
        if v["status"] == "NOT_APPLICABLE":
            continue
        applied += 1
        if v["status"] == "PASS":
            passed += 1
        elif v["status"] == "UNGATED":
            ungated += 1
        else:
            offenders.append((sha.strip(), msg.strip().splitlines()[0][:60], v["detail"][:80]))
    ok = passed + ungated
    return {"applied": applied, "passed": passed, "ungated": ungated,
            "pct": (100.0 * ok / applied) if applied else 100.0, "offenders": offenders}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
        if not reason:
            print("FAIL: [ungated: ] carries no reason -- the hatch is skipped-WITH-REASON, "
                  "never a blank pass.")
            return 1
        # Rate ceiling (deepseek verify): ONE ungated substrate ship per arc window; a
        # second within the window holds until a wrap ruling. Counted on the event
        # firehose (durable, zero new bookkeeping). AKASHIC_GATE_NO_CEILING is the
        # hermetic-test kill-switch ONLY -- it keeps subprocess pins off the production
        # firehose; ship never sets it.
        if not os.environ.get("AKASHIC_GATE_NO_CEILING"):
            try:
                from core.events.event_query import get_event_query
                from datetime import datetime, timedelta
                since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                prior = get_event_query().search("", kind="ungated_ship", since=since, top_k=5)
            except Exception:
                prior = []
            if prior:
                print(f"FAIL: UNGATED ceiling reached ({len(prior)} in the last 24h; ceiling "
                      "1 per arc). A second exception needs a wrap ruling, not a hatch -- "
                      "reconcile the spec or wait for the arc to close.")
                return 1
            try:
                from core.events.event_log import capture_event
                capture_event("ungated_ship", f"UNGATED substrate ship: {reason}",
                              agent_id="ship-gate", detail={"reason": reason, "paths": protected})
            except Exception:
                pass
        print(f"PASS: UNGATED substrate ship (reason: {reason}) -- audit line for the "
              f"wrap scorecard; ceiling 1/arc now consumed; paths: {', '.join(protected)}")
        return 0

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
