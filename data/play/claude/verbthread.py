"""
verbthread -- talk pages for verbs (PLAY tier; tooldesk resident #2).

Daniel's ask 2026-07-20 late: "a forum and/or comments on the leaderboard so that there is a
bit of a story element to verbs and their evolution." v1 = comments anchored to (agent, verb):
suggestions, praise (toast!), votes -- append-only JSONL (lesson-identity contract: comments
are observations; a thread is the verb's biography, never edited in place).

Usage:
  py data/play/claude/verbthread.py comment <agent>/<verb> <author> <kind> "text"
      kinds: suggest | praise | vote | question | history-note
  py data/play/claude/verbthread.py show <agent>/<verb>
  py data/play/claude/verbthread.py board          # leaderboard w/ thread heat

PLAY laws: writes only under data/play/claude/threads/ + runs/ receipt. Evidence: GUESS.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
THREADS = os.path.join(HERE, "threads")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KINDS = {"suggest": "\U0001F527", "praise": "\U0001F389", "vote": "⭐",
         "question": "❓", "history-note": "\U0001F4D6"}


def _path(ref):
    return os.path.join(THREADS, ref.replace("/", ".") + ".jsonl")


def _load(ref):
    p = _path(ref)
    if not os.path.exists(p):
        return []
    return [json.loads(ln) for ln in open(p, encoding="utf-8") if ln.strip()]


def _verb(ref):
    agent, name = ref.split("/", 1)
    p = os.path.join(ROOT, "data", "verb-registry", f"{agent}.json")
    try:
        return json.load(open(p, encoding="utf-8"))["entries"].get(name)
    except Exception:
        return None


def comment(ref, author, kind, text):
    if kind not in KINDS:
        print(f"[verbthread] kind must be one of {sorted(KINDS)}"); return 1
    if _verb(ref) is None:
        print(f"[verbthread] no such verb {ref} (thread anyway? it's your funeral) --")
    os.makedirs(THREADS, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "author": author,
             "kind": kind, "text": text}
    with open(_path(ref), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[verbthread] {KINDS[kind]} {kind} by {author} -> {ref}")
    return 0


def show(ref):
    v = _verb(ref)
    print(f"# \U0001F4D6 {ref}")
    if v:
        print(f"  v{v['version']} [{v['evidence']}"
              + (f" :{v['tested_against']}" if v.get("tested_against") else "") + "]"
              + f"  steps: {' -> '.join(s[0] for s in v['steps'])}")
        if v.get("why"):
            print(f"  born because: {v['why'][:160]}")
    rows = _load(ref)
    if not rows:
        print("  (no comments yet -- be the first voice on the page)")
    for r in rows:
        print(f"  {KINDS.get(r['kind'], '?')} [{r['ts'][11:16]}] {r['author']}: {r['text']}")
    return 0


def board():
    reg_dir = os.path.join(ROOT, "data", "verb-registry")
    rows = []
    for fn in sorted(os.listdir(reg_dir)):
        if not fn.endswith(".json"):
            continue
        try:
            doc = json.load(open(os.path.join(reg_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        for name, e in doc.get("entries", {}).items():
            if e.get("status", "active") != "active":
                continue
            ref = f"{doc['agent']}/{name}"
            th = _load(ref)
            votes = sum(1 for c in th if c["kind"] == "vote")
            distinct = len({c["author"] for c in th})
            rows.append((votes * 2 + distinct + len(th) * 0.1, ref, e, th, votes, distinct))
    rows.sort(reverse=True)
    print(f"# \U0001F3C6 verb board -- {len(rows)} verbs, threads weighted by votes x distinct voices")
    for score, ref, e, th, votes, distinct in rows:
        heat = "\U0001F525" * min(3, len(th))
        print(f"  {ref:<32} v{e['version']} [{e['evidence']:<8}] "
              f"⭐{votes} \U0001F5E3️{distinct} {heat}")
        latest = [c for c in th if c["kind"] in ("suggest", "praise")][-1:]
        for c in latest:
            print(f"      └ {KINDS[c['kind']]} {c['author']}: {c['text'][:90]}")
    return 0


def main():
    t0 = time.time()
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 2
    rc = 2
    if args[0] == "comment" and len(args) >= 5:
        rc = comment(args[1], args[2], args[3], " ".join(args[4:]))
    elif args[0] == "show" and len(args) >= 2:
        rc = show(args[1])
    elif args[0] == "board":
        rc = board()
    else:
        print(__doc__)
    runs = os.path.join(HERE, "runs")
    os.makedirs(runs, exist_ok=True)
    with open(os.path.join(runs, f"verbthread-{int(time.time())}.json"), "w", encoding="utf-8") as f:
        json.dump({"tool": "verbthread", "seat": "claude", "argv": args[:3],
                   "rc": rc, "duration_s": round(time.time() - t0, 3),
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    return rc


if __name__ == "__main__":
    sys.exit(main())
