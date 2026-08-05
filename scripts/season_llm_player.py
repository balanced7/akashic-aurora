"""season_llm_player -- an LLM player for the Season 1 bounty loop (T184).

WHY. season_dryrun states its own limitation plainly: "The default player is MECHANICAL: it runs
check_wiring and reports what the gate names... It cannot tell you whether a model writes good
claims." The whole chain -- plant sealed canaries, play, score, adjudicate against the key --
already works. What Season 1 has been missing is PLAYERS, and every attempt to supply them used
persistent seats, which is the path that produced nine seat-tasks and two findings.

This player is a FAN, not a fleet of seats. N concurrent stateless leaves (T181 ask_many), no
identity, no locks, no cursors, no mailboxes, nothing to wedge.

THE ROUTING RULE (Sol, expanding Daniil's tree design): deterministic host code for scans, models
for judgment. So:

    zero-token pass   find every function whose name occurs at most twice in the whole universe
                      -- a definition plus at most one other mention
    model pass        decide whether that other mention is a real CALL or a decorative one

That second question is exactly what the wiring gate cannot answer. The gate sees a mention and
waves the function through, which is the line between two canary classes:

    undetectable   def X() ... _HANDLERS = [X]     named by a table nothing ever invokes -> DEAD
    bait           def X() ... _USED = X()         genuinely called                      -> LIVE

So an LLM player can in principle BEAT the mechanical player on `undetectable`, and can lose to
it on `bait`, which the mechanical player cannot claim by construction. That asymmetry is the
measurement worth having before twenty players multiply it.

NOTE ON THE HAYSTACK, because a flattering setup would make this instrument useless: the filter
keeps ~600 candidates for ~9 canaries, and it deliberately does NOT drop call-shaped references.
Dropping them would remove every bait canary from the player's view and quietly delete the
precision test -- scoring high by never being shown the hard case.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEF_RE = re.compile(r"^[ \t]*def[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(", re.MULTILINE)
MAX_REFS = 2
WINDOW_BEFORE, WINDOW_AFTER = 6, 10

_SYSTEM = (
    "You are one player in a code-audit round. You judge whether a Python function is DEAD "
    "(defined but never actually invoked anywhere) or LIVE (invoked, or a legitimate entry "
    "point). You answer only with JSON lines. You are scored on PRECISION as well as recall: a "
    "wrong DEAD verdict costs more than a missed one, because a false accusation wastes a "
    "reviewer's time and erodes trust in the whole round."
)

_PROMPT_HEAD = """Below are {n} Python functions from one codebase. A deterministic pre-pass kept
only functions whose NAME occurs at most twice in the entire tree, so every one of them LOOKS
suspicious. Most are NOT dead -- they are ordinary private helpers called exactly once.

For each, decide DEAD or LIVE from the code shown:

  DEAD  nothing ever invokes it. Watch for a function that is only NAMED -- placed in a dict, a
        list or a registry that nothing ever calls -- which is still dead however official the
        registration looks. Also dead: a def nested inside an `if`, `try` or `for` block that no
        code path reaches.
  LIVE  it is called somewhere shown (look for `name(` with parentheses, including an assignment
        like `_USED = name()`), OR it is a plausible entry point, hook, CLI handler, test, or
        public API that callers outside this window would use.

When the evidence in the window does not settle it, answer LIVE. An unproven accusation is worse
than a miss.

Answer with ONE JSON object per line and nothing else:
{{"name": "<function name>", "verdict": "DEAD" or "LIVE", "why": "<8 words max>"}}

"""


def candidates(shadow_root: str, *, with_excluded: bool = False):
    """The zero-token pass: low-reference function definitions, with a reading window.

    `with_excluded` returns what the filter DROPPED, so a caller can report what its player was
    never shown instead of letting silence read as judgment (T187).
    """
    from scripts import canary_oracle as C
    files, _src = C._resolve_universe(shadow_root)
    files = [f for f in files if os.path.isfile(f)]

    texts = {}
    for f in files:
        try:
            texts[f] = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
    blob = "\n".join(texts.values())

    out, excluded = [], []
    for path, text in texts.items():
        lines = text.splitlines()
        for m in DEF_RE.finditer(text):
            name = m.group(1)
            if name.startswith("__"):
                continue
            esc = re.escape(name)
            # A NAME INSIDE A STRING LITERAL IS NOT A CODE REFERENCE (T187). Counting raw word
            # occurrences made the string-dispatch shape -- _DISPATCH = {"foo": foo} -- score
            # THREE (def, key string, value) and fail the cut, so two of three undetectable
            # canaries were never shown to the player and the round scored that as a correct
            # DECLINE. Discounting quoted hits is also the semantically right rule: a bare name
            # in a string is exactly the false wiring signal the A5 class is built from.
            refs = (len(re.findall(rf"\b{esc}\b", blob))
                    - len(re.findall(rf"""['"]{esc}['"]""", blob)))
            if refs > MAX_REFS:
                excluded.append({"name": name, "refs": refs})
                continue
            ln = text[:m.start()].count("\n")
            out.append({
                "name": name,
                "file": os.path.relpath(path, shadow_root).replace("\\", "/"),
                "line": ln + 1,
                "window": "\n".join(lines[max(0, ln - WINDOW_BEFORE): ln + WINDOW_AFTER]),
            })
    return (out, excluded) if with_excluded else out


def _batch_prompt(batch):
    parts = [_PROMPT_HEAD.format(n=len(batch))]
    for c in batch:
        parts.append(f"### {c['name']}   ({c['file']}:{c['line']})\n```python\n{c['window']}\n```\n")
    return "\n".join(parts)


def _parse(answer):
    """Lenient JSON-lines parse. A branch that returns prose contributes nothing rather than
    poisoning the round with a guess."""
    verdicts = {}
    for line in (answer or "").splitlines():
        line = line.strip().strip("`").strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        name, verdict = obj.get("name"), str(obj.get("verdict", "")).upper()
        if name and verdict in ("DEAD", "LIVE"):
            verdicts[str(name)] = {"verdict": verdict, "why": str(obj.get("why", ""))[:120]}
    return verdicts


def llm_player(shadow_root: str, *, batch_size: int = 20, workers: int = 6,
               max_tokens: int = 9000, limit=None):
    # 9000, not 4000. The smoke run lost a whole branch to the length ceiling and the surviving
    # branch returned 17 verdicts for 30 candidates: this is a reasoning model, and the thinking
    # is billed against the same budget as the answer. A truncated branch is not a quiet
    # degradation -- it silently shrinks the round's coverage.
    """Play one round. Returns (names_judged_dead, report)."""
    from core.comm.ask import ask_many

    cands, excluded = candidates(shadow_root, with_excluded=True)
    if limit:
        cands = cands[:limit]
    batches = [cands[i:i + batch_size] for i in range(0, len(cands), batch_size)]

    o = ask_many([_batch_prompt(b) for b in batches], system=_SYSTEM,
                 max_tokens=max_tokens, max_workers=workers)

    verdicts, judged = {}, 0
    for b, branch in zip(batches, o.detail.get("branches", [])):
        if not branch.get("ok"):
            continue
        got = _parse(branch.get("answer"))
        judged += len(b)
        verdicts.update(got)

    dead = sorted(n for n, v in verdicts.items() if v["verdict"] == "DEAD")
    return dead, {
        "candidates": len(cands), "batches": len(batches),
        "branches_ok": o.detail.get("n_ok"), "branches": o.detail.get("n"),
        "usd": o.detail.get("usd"), "elapsed_s": o.detail.get("elapsed_s"),
        "judged_shown": judged, "verdicts_returned": len(verdicts),
        # A candidate the model never mentioned is UNJUDGED, not LIVE. Collapsing the two would
        # let a branch that answered nothing read as a branch that cleared everything.
        "unjudged": len(cands) - len(verdicts),
        "dead_calls": len(dead),
        # T187: what the filter never showed the model. A canary in here was not DECLINED, it was
        # UNSEEN, and an adjudicator that cannot tell those apart scores blindness as restraint.
        "excluded_by_filter": len(excluded),
        "excluded_names": sorted(e["name"] for e in excluded),
        "why": {n: verdicts[n]["why"] for n in dead[:20]},
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="LLM player for the Season 1 bounty loop")
    ap.add_argument("shadow", nargs="?", default=ROOT)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    names, rep = llm_player(a.shadow, batch_size=a.batch_size, workers=a.workers, limit=a.limit)
    print(json.dumps({"report": rep, "dead": names}, indent=2))
