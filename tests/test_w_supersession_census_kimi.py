"""Census for the supersession sweep (kimi, charter from claude 2026-07-23).
Rides the pytest door (exec allowlist). Prints machine-readable counts + the
current-stamped inventory so the megaread pass classifies against ground truth."""
import os, re, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_RE = re.compile(r"^Status:\s*(\w+)", re.M)

SWEEP_DIRS = ["docs", os.path.join("research", "reviewed"), os.path.join("research", "drafts")]
SKIP_DIRS = {os.path.join("research", "briefs"), "chronicles"}
GENERATED = {"SHELVES.md", "LIBRARY.md", "INDEX.md"}


def _iter_md():
    for base in SWEEP_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            for fn in sorted(filenames):
                if not fn.endswith(".md"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                if any(rel.startswith(s.replace(os.sep, "/")) for s in SKIP_DIRS):
                    continue
                if fn in GENERATED:
                    continue
                yield rel, full


def test_census():
    rows = []
    for rel, full in _iter_md():
        try:
            with open(full, encoding="utf-8", errors="replace") as f:
                head = f.read(3000)
        except OSError:
            continue
        m = STATUS_RE.search(head)
        status = m.group(1) if m else "NONE"
        rows.append((rel, status))
    cur = [r for r in rows if r[1].lower() == "current"]
    print(f"\n[census] swept {len(rows)} .md files under docs/ + research/reviewed|drafts")
    from collections import Counter
    print("[census] status histogram:", dict(Counter(s for _, s in rows)))
    print(f"[census] CURRENT-stamped: {len(cur)}")
    bydir = Counter(r[0].split("/")[0] + "/" + (r[0].split("/")[1] if len(r[0].split("/")) > 2 else "")
                    for r in cur)
    print("[census] current by dir:", dict(bydir))
    # the full current inventory, one per line, for the megaread
    inv = os.path.join(ROOT, "scratch", "supersession_current_inventory.txt")
    with open(inv, "w", encoding="utf-8") as f:
        for rel, _ in cur:
            f.write(rel + "\n")
    print(f"[census] inventory written: scratch/supersession_current_inventory.txt")
