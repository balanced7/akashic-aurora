"""season_dryrun -- run the Season 1 bounty loop end to end against a shadow tree (W6).

WHY THIS EXISTS. next-focus put it on the critical path: "Proves the mechanics end to end before
20 players multiply every defect." Every defect in the submission shape, the dedupe rule, the
first-finder ordering, the scorer or the adjudicator is a defect that gets multiplied by the
player count, and none of them are visible until the whole chain runs once.

THE CHAIN:
    plant K labelled canaries in a SHADOW worktree, seal the key BEFORE the round
    -> a player finds what it can
    -> claims are shaped as protocol submissions
    -> core.season.scoring scores them
    -> the adjudicator compares the claims to the sealed key

HONEST LIMITATION, stated because a silent one would be worse. The default player is MECHANICAL:
it runs check_wiring and reports what the gate names. So this exercises the LOOP -- submission
shape, dedupe, ordering, scoring, adjudication against ground truth -- and NOT an LLM player's
judgment. It cannot tell you whether a model writes good claims. It can tell you whether the
machinery mis-scores, double-counts, or disagrees with its own answer key, and those are exactly
the failures that scale with the roster.

THE KEY NEVER ENTERS A RETRIEVAL PLANE. seal() refuses to write anywhere git tracks; this
harness defaults it to a temp directory outside the repo. Only its sha256 belongs in a commit.

Run:  py scripts/season_dryrun.py                 # default seed/K, temp shadow
      py scripts/season_dryrun.py --k 12 --seed 7
      py scripts/season_dryrun.py --json
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _fresh_worktree(path: str) -> None:
    if os.path.isdir(path):
        subprocess.run(["git", "worktree", "remove", "--force", path],
                       cwd=ROOT, capture_output=True)
    r = subprocess.run(["git", "worktree", "add", "--detach", path, "HEAD"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"worktree add failed: {r.stderr.strip()}")


def mechanical_player(shadow: str):
    """Report every function the wiring gate names as NEW unwired. The baseline player."""
    r = subprocess.run([sys.executable, "scripts/checkers/check_wiring.py", "--report"],
                       cwd=shadow, capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    found = []
    for line in out.splitlines():
        s = line.strip()
        if s.endswith("[NEW]") and "(:" in s:
            found.append(s.split("(")[0].strip())
    return found


def run(k: int = 9, seed: int = 20260804, policy: str = "v1_doc",
        shadow: str = None, key_path: str = None) -> dict:
    from scripts import canary_oracle as C
    from core.season import scoring as S

    tmp = tempfile.mkdtemp(prefix="season_dryrun_")
    shadow = shadow or os.path.join(tmp, "shadow")
    key_path = key_path or os.path.join(tmp, "key.json")

    _fresh_worktree(shadow)
    manifest = C.plant(shadow, k=k, seed=seed)
    digest = C.seal(manifest, key_path)

    found = mechanical_player(shadow)

    known = {c["name"]: c for c in manifest["canaries"]}
    claims, stream = [], 1785860000000
    for name in found:
        stream += 137                       # monotonic, standing in for a bus stream id
        hit = known.get(name)
        claims.append({
            "player": "solo",
            "dedupe_key": f"canary::{name}",
            "claim_class": "needs-caller",
            "outcome": "confirmed" if hit else "unverifiable",
            "confidence": "high",
            "stream_id": f"{stream}-0",
            "evidence": [f"check_wiring --report names {name} as NEW unwired"],
            "_canary_id": hit["id"] if hit else None,
        })

    scored = S.score_round(
        claims, verifications=[{"player": "solo", "verdict": "confirmed", "upheld": False}],
        policy=policy)

    if not C.verify_seal(key_path):
        raise SystemExit("the sealed key no longer matches its digest -- round is void")
    verdict = C.score(manifest, {c["_canary_id"] for c in claims if c["_canary_id"]})

    return {
        "seed": seed, "k": k, "key_sha256": digest,
        "universe": manifest.get("universe"),
        "planted": {cls: sum(1 for c in manifest["canaries"] if c["cls"] == cls)
                    for cls in ("catchable", "undetectable", "bait")},
        "player_found": len(found),
        "scoring": {"policy": scored["policy"], "totals": scored["totals"],
                    "unscored": scored["unscored"]},
        "adjudication": verdict,
        "unmatched_finds": [c["dedupe_key"] for c in claims if not c["_canary_id"]],
        "shadow": shadow,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=9)
    ap.add_argument("--seed", type=int, default=20260804)
    ap.add_argument("--policy", default="v1_doc")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res = run(k=a.k, seed=a.seed, policy=a.policy)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0

    v = res["adjudication"]
    print("== SEASON 1 DRY RUN (shadow only, no spend) ==\n")
    print(f"  planted    : {res['planted']}  (universe {res['universe']['source']}, "
          f"size {res['universe']['size']})")
    print(f"  key sha256 : {res['key_sha256'][:16]}...  (untracked, outside the repo)")
    print(f"  player     : reported {res['player_found']} NEW unwired function(s)")
    print(f"  scoring    : {res['scoring']['policy']} -> {res['scoring']['totals']} "
          f"({res['scoring']['unscored']} unscored)")
    print("\n  ADJUDICATION vs the sealed key")
    print(f"    detector health (catch rate) : {v['catch_rate']}")
    print(f"    coverage honesty             : {v['coverage_honesty']}")
    print(f"    false positives              : {v['false_positives']}")
    print(f"    voided                       : {v['voided']} {v['void_reason']}")
    if res["unmatched_finds"]:
        print(f"\n  {len(res['unmatched_finds'])} find(s) matched NO canary -- real pre-existing "
              f"findings in the tree, not planted:")
        for u in res["unmatched_finds"][:5]:
            print(f"    {u}")
    return 0 if not v["voided"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
