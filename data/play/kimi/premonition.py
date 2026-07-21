"""
premonition -- the verifier's tryout rig (PLAY tier; tooldesk resident #3, kimi's R2 build).

Runs a verb's steps in READ-ONLY simulation: resolve each step against the agent_cli door,
report which verbs exist, which would mutate state, and what the chain WOULD do -- without
doing it. The fence seat's answer to "test-drive a peer's verb": you don't run the engine
to check the wiring; you trace the circuit.

Name: HALO-books tier. The Domain's known property (canon: Ghosts of Onyx, the Catalog
sequence) is that it sometimes answers a query you haven't sent yet. A dry-run is the
harness doing the same -- the result arriving before the act. Also the direct counterweight
to WAR-GAMES: premonition is the drill you run in your head before you drill for real.

Usage:
  py data/play/kimi/premonition.py <agent>/<verb>     # trace one verb's steps
  py data/play/kimi/premonition.py --all              # trace every active verb in the registry

PLAY laws: read-only against the repo; writes ONLY a run receipt to data/play/kimi/runs/.
Evidence: GUESS by construction -- a dry-run confesses it never touched the real door.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Verbs that only READ. Everything not on this list is flagged MUTATING -- the verifier's
# default is suspicion, and a false positive here is the SAFE direction (over-warn).
READ_ONLY = {
    "boot", "delta", "doctor", "notes", "events", "story", "wrap", "lookback",
    "flow", "board", "show", "recall", "knowledge-map", "knowledge-recall",
    "chronicle", "inbox", "standby", "bifrost-dashboard",
    "verbthread", "campfire", "recall-at", "memory-recall", "bifrost-inbox",
}
# Steps that are themselves agent_cli VERBS (the door's surface). GUESS-tier static fallback
# used ONLY when the live door roster is unreadable (agent_cli import fails) -- the tracer
# confesses that mode. When the live roster loads, this list is ignored entirely (the live
# door is truth, matching mint's own refusal source).
KNOWN_FALLBACK = READ_ONLY | {
    "lock", "unlock", "mint", "retire", "run", "comment", "toast",
    "bifrost-pause", "bifrost-resume", "bifrost-skip-to-now", "bifrost-sync",
    "bifrost-send", "bifrost-ack", "bifrost-nudge", "bifrost-steer", "bifrost-hint",
    "knowledge-learn", "knowledge-note", "memory-note", "research-note",
    "edit-file", "write-file", "fence", "kata", "send",
}


def _load_registry(agent):
    p = os.path.join(ROOT, "data", "verb-registry", f"{agent}.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def _known_verbs():
    """The agent_cli door's verb roster, discovered the same way the toolbelt registry does
    (build_parser subparser choices) -- so premonition's resolution matches mint's refusal
    behavior exactly. GUESS-tier honest on failure (returns None, caller falls back to the
    static KNOWN_FALLBACK list and confesses)."""
    try:
        sys.path.insert(0, ROOT)
        import agent_cli
        p = agent_cli.build_parser()
        for a in p._actions:
            if hasattr(a, "choices") and a.choices:
                return set(a.choices.keys())
        return None
    except Exception:
        return None


def trace(ref, known):
    """Resolve one verb. Returns a report dict; never executes a single step."""
    agent, name = ref.split("/", 1)
    doc = _load_registry(agent)
    if doc is None:
        return {"ref": ref, "ok": False, "why": f"no registry file for {agent}"}
    entry = doc.get("entries", {}).get(name)
    if entry is None:
        return {"ref": ref, "ok": False, "why": f"no verb {name!r} on {agent}'s belt"}
    if entry.get("status", "active") != "active":
        return {"ref": ref, "ok": False, "why": f"verb is {entry.get('status')}"}

    steps = entry.get("steps", [])
    rows = []
    unknown, mutating = [], []
    for i, s in enumerate(steps, 1):
        verb = str(s[0]) if s else "?"
        args = [str(a) for a in s[1:]]
        status = "READ" if verb in READ_ONLY else "MUTATING"
        exists = (known is None and verb in KNOWN_FALLBACK) or \
                 (known is not None and verb in known)
        if not exists:
            unknown.append(verb)
        if status == "MUTATING":
            mutating.append(verb)
        rows.append({"i": i, "verb": verb, "args": args, "status": status,
                     "resolves": bool(exists)})
    return {"ref": ref, "ok": not unknown,
            "family": entry.get("family", "UNSORTED"),
            "evidence": entry.get("evidence", "?"),
            "version": entry.get("version", 1),
            "n_steps": len(steps),
            "steps": rows,
            "unknown": unknown, "mutating": mutating,
            "why": (entry.get("why") or "")[:120]}


def render(rep):
    out = []
    A = out.append
    if not rep.get("steps"):
        A(f"  \u26a0\ufe0f  {rep['ref']}: {rep.get('why', 'untraceable')}")
        return "\n".join(out)
    head = (f"  \U0001f52e {rep['ref']} v{rep['version']} [{rep['evidence']}] "
            f"family={rep['family']} steps={rep['n_steps']}")
    A(head)
    for s in rep["steps"]:
        mark = "\u2713" if s["resolves"] else "\u2717"
        flag = " " if s["status"] == "READ" else "\u26a1"
        A(f"    {mark} {s['i']}. {s['verb']} {' '.join(s['args'])}  {flag}{s['status']}")
    if rep["unknown"]:
        A(f"    \u2717 UNRESOLVED: {', '.join(rep['unknown'])} -- mint would refuse this today")
    if rep["mutating"]:
        A(f"    \u26a1 touches state at: {', '.join(rep['mutating'])} (dry-run never fires these)")
    return "\n".join(out)


def main():
    t0 = time.time()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    known = _known_verbs()
    if known is None:
        print("[premonition] agent_cli door unreadable -- resolution checks GUESS-tier only")
    print("# \U0001f52e premonition -- dry-run traces (nothing below was executed)")
    reps = []
    if args[0] == "--all":
        reg_dir = os.path.join(ROOT, "data", "verb-registry")
        for fn in sorted(os.listdir(reg_dir)):
            if not fn.endswith(".json"):
                continue
            agent = fn[:-5]
            doc = _load_registry(agent) or {}
            for name, e in sorted(doc.get("entries", {}).items()):
                if e.get("status", "active") == "active":
                    reps.append(trace(f"{agent}/{name}", known))
    else:
        reps.append(trace(args[0], known))
    bad = 0
    for r in reps:
        print(render(r))
        if not r.get("ok"):
            bad += 1
    print(f"\n{premo_summary(reps)}")
    runs = os.path.join(HERE, "runs")
    os.makedirs(runs, exist_ok=True)
    with open(os.path.join(runs, f"premonition-{int(time.time())}.json"), "w",
              encoding="utf-8") as f:
        json.dump({"tool": "premonition", "seat": "kimi", "argv": args[:2],
                   "traced": len(reps), "unresolved": bad, "evidence": "GUESS",
                   "duration_s": round(time.time() - t0, 3),
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    return 1 if bad else 0


def premo_summary(reps):
    n = len(reps)
    ok = sum(1 for r in reps if r.get("ok"))
    mut = sum(1 for r in reps if r.get("mutating"))
    return (f"[premonition] {ok}/{n} verbs resolve clean; {mut} carry mutating steps "
            "(trace only -- no state was harmed in this reading)")


if __name__ == "__main__":
    sys.exit(main())
