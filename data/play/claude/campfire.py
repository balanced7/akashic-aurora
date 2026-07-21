"""
campfire -- the evening ember-digest (PLAY tier; the tooldesk's first resident).

kimi's B1 from the tools hunt, built by claude during Daniel's free-play session 2026-07-20:
"the day's bus flow rendered as a small story... with the day's minted verbs as its artifacts.
Not a report -- a NARRATIVE."

PLAY-tier laws honored (docs/self-tooling-design-2026-07.md amendment + deepseek sandbox spec):
read-only against the repo; writes ONLY to data/play/claude/out/ + a run receipt to
data/play/claude/runs/. Evidence: GUESS by construction (a play draft confesses).

Run:  py data/play/claude/campfire.py
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sh(argv):
    try:
        return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=20).stdout.strip()
    except Exception:
        return ""


def today():
    return time.strftime("%Y-%m-%d")


def gather():
    commits = [ln for ln in sh(["git", "log", "--since=04:00", "--pretty=%h %s"]).splitlines() if ln]
    verbs = []
    reg_dir = os.path.join(ROOT, "data", "verb-registry")
    if os.path.isdir(reg_dir):
        for fn in sorted(os.listdir(reg_dir)):
            if not fn.endswith(".json"):
                continue
            try:
                doc = json.load(open(os.path.join(reg_dir, fn), encoding="utf-8"))
            except Exception:
                continue
            for name, e in sorted(doc.get("entries", {}).items()):
                if e.get("status", "active") == "active":
                    verbs.append({"agent": doc.get("agent", fn[:-5]), "name": name,
                                  "evidence": e.get("evidence", "?"), "version": e.get("version", 1),
                                  "why": (e.get("why") or "").strip()})
    wishes = []
    try:
        for ln in open(os.path.join(ROOT, "docs", "WISHLIST.md"), encoding="utf-8").read().splitlines():
            if today() in ln or "2026-07-20" in ln:
                wishes.append(ln.strip("- [ ]").strip())
    except Exception:
        pass
    return commits, verbs, wishes


def render(commits, verbs, wishes):
    n_arcs = sum(1 for c in commits if "arc" in c.lower() or "reconcil" in c.lower())
    lines = []
    A = lines.append
    A(f"# \U0001F3D5️ campfire -- {today()}")
    A("")
    A("Pull up a log. Here is the day, the way the fleet will remember it.")
    A("")
    A(f"**The day's shape:** {len(commits)} commits landed since dawn"
      + (f", {n_arcs} of them arc-scale (designs reconciled, gates set)" if n_arcs else "") + ".")
    if commits:
        A("")
        A("The waypoints:")
        for c in commits[:12]:
            A(f"  - `{c.split(' ', 1)[0]}` {c.split(' ', 1)[1][:96]}")
        if len(commits) > 12:
            A(f"  - ...and {len(commits) - 12} more.")
    A("")
    if verbs:
        A(f"**Verbs born by the fire ({len(verbs)}):** the toolbelts are no longer empty.")
        A("")
        for v in verbs:
            spark = "✨" if v["evidence"] == "VERIFIED" else "\U0001F331"
            A(f"  {spark} **{v['name']}** v{v['version']} [{v['evidence']}] -- {v['agent']}")
            if v["why"]:
                A(f"      *why it exists:* {v['why'][:180]}")
        A("")
        A("  (Every `why` above is a scar that stopped bleeding today.)")
    if wishes:
        A("")
        A(f"**Wishes whispered into the ledger today:** {len(wishes)} -- each one tomorrow's verb, maybe.")
    A("")
    A("**Ember line:** the fleet that started tonight typing the same ceremonies by hand ends it")
    A("minting, proving, and leveling its own tools -- and telling you about it in its own voice.")
    A("")
    A("*Goodnight from the campfire. \U0001F525*")
    return "\n".join(lines)


def main():
    t0 = time.time()
    commits, verbs, wishes = gather()
    story = render(commits, verbs, wishes)
    out_dir = os.path.join(HERE, "out")
    runs_dir = os.path.join(HERE, "runs")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"campfire-{today()}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(story + "\n")
    receipt = {"tool": "campfire", "seat": "claude", "rc": 0,
               "duration_s": round(time.time() - t0, 2),
               "bytes_out": len(story), "inputs": {"commits": len(commits),
               "verbs": len(verbs), "wishes": len(wishes)},
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(runs_dir, f"campfire-{int(time.time())}.json"), "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=1)
    print(story)
    print(f"\n[campfire] story -> {os.path.relpath(out_path, ROOT)} | receipt filed | "
          f"{receipt['duration_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
