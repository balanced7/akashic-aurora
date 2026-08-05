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
        shadow: str = None, key_path: str = None, player=None,
        player_name: str = "mechanical", archive: bool = True,
        player_config: dict = None) -> dict:
    """T184: `player` is injectable so the loop can be driven by something other than a gate.

    The mechanical player cannot claim a `bait` canary by construction -- it only echoes what
    check_wiring names -- so it measures the MACHINERY and not a player's judgment. An LLM
    player can claim bait, which is the precision question a twenty-player round lives on.
    """
    from scripts import canary_oracle as C
    from core.season import scoring as S

    tmp = tempfile.mkdtemp(prefix="season_dryrun_")
    shadow = shadow or os.path.join(tmp, "shadow")
    key_path = key_path or os.path.join(tmp, "key.json")

    _fresh_worktree(shadow)
    manifest = C.plant(shadow, k=k, seed=seed)
    digest = C.seal(manifest, key_path)

    # A model player produces TWO load-bearing outputs: names to turn into claims, and the
    # coverage/reasoning report that explains how those names were produced.  T190 archived the
    # claims but the CLI used to attach the report only after run() returned -- after the archive
    # boundary had already passed.  Keep the products together at the player boundary so display
    # and durable replay cannot diverge (T191).  A list-only return remains the mechanical-player
    # contract; only the explicit (names, dict-report) shape is treated as the richer result.
    player_output = (player or mechanical_player)(shadow)
    player_report = None
    if (isinstance(player_output, tuple) and len(player_output) == 2
            and isinstance(player_output[1], dict)):
        found, player_report = player_output
    else:
        found = player_output

    known = {c["name"]: c for c in manifest["canaries"]}
    claims, stream = [], 1785860000000
    for name in found:
        stream += 137                       # monotonic, standing in for a bus stream id
        hit = known.get(name)
        claims.append({
            "player": player_name,
            "dedupe_key": f"canary::{name}",
            "claim_class": "needs-caller",
            "outcome": "confirmed" if hit else "unverifiable",
            "confidence": "high",
            "stream_id": f"{stream}-0",
            "evidence": [f"check_wiring --report names {name} as NEW unwired"],
            "_canary_id": hit["id"] if hit else None,
        })

    scored = S.score_round(
        claims, verifications=[{"player": player_name, "verdict": "confirmed", "upheld": False}],
        policy=policy)

    if not C.verify_seal(key_path):
        raise SystemExit("the sealed key no longer matches its digest -- round is void")
    verdict = C.score(manifest, {c["_canary_id"] for c in claims if c["_canary_id"]})

    # T190: the round's evidence outlives the round. Three earlier rounds costing $1.069
    # printed their claims and discarded them, so a scoreboard replacement had no old-score /
    # new-score comparison to be judged on. The record goes OUTSIDE git beside the key: claims
    # carry canary names, so committing one leaks name->class for this seed.
    round_path = None
    if archive:
        try:
            from scripts.round_archive import archive_round
            round_record = {
                "seed": seed, "k": k, "key_sha256": digest,
                "player_name": player_name, "player_config": player_config or {},
                "universe": manifest.get("universe"),
                "manifest": manifest,          # replay needs the key it was scored against
                "claims": claims,
                "scoring": {"policy": scored["policy"], "totals": scored["totals"],
                            "unscored": scored["unscored"]},
                "adjudication": verdict,
            }
            if player_report is not None:
                round_record["player_report"] = player_report
            round_path = archive_round(round_record)
        except Exception as e:
            # Loud, never silent: a round whose evidence was not stored must SAY so, or the
            # next replay quietly reads a shorter history than it thinks it has.
            print(f"[round-archive] FAILED to store this round: {type(e).__name__}: {e}",
                  file=sys.stderr)

    result = {
        "seed": seed, "k": k, "key_sha256": digest, "player_name": player_name,
        "round_path": round_path,
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
    if player_report is not None:
        result["player_report"] = player_report
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--k", type=int, default=9)
    ap.add_argument("--seed", type=int, default=20260804)
    ap.add_argument("--policy", default="v1_doc")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--player", default="mechanical", choices=("mechanical", "llm"),
                    help="T184: 'llm' fans N stateless leaves over the shadow tree instead of "
                         "echoing check_wiring. The mechanical player cannot claim a bait "
                         "canary by construction; an LLM player can, which is the point")
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    player = None
    if a.player == "llm":
        from scripts.season_llm_player import llm_player

        def player(shadow):                                     # noqa: F811
            return llm_player(shadow, batch_size=a.batch_size, workers=a.workers)

    res = run(k=a.k, seed=a.seed, policy=a.policy, player=player, player_name=a.player,
              player_config={"batch_size": a.batch_size, "workers": a.workers})
    if a.json:
        print(json.dumps(res, indent=2))
        return 0

    v = res["adjudication"]
    print("== SEASON 1 DRY RUN (shadow only, no spend) ==\n")
    print(f"  planted    : {res['planted']}  (universe {res['universe']['source']}, "
          f"size {res['universe']['size']})")
    print(f"  key sha256 : {res['key_sha256'][:16]}...  (untracked, outside the repo)")
    print(f"  player     : {res.get('player_name', 'mechanical')} -- reported "
          f"{res['player_found']} suspected dead function(s)")
    pr = res.get("player_report")
    if pr:
        print(f"               {pr['candidates']} candidates -> {pr['batches']} batches, "
              f"{pr['branches_ok']}/{pr['branches']} branches landed, "
              f"{pr['verdicts_returned']} verdicts, {pr['unjudged']} UNJUDGED")
        print(f"               ${pr['usd']} / {pr['elapsed_s']}s wall"
              if pr.get("usd") is not None else "               spend unpriced")
    print(f"  scoring    : {res['scoring']['policy']} -> {res['scoring']['totals']} "
          f"({res['scoring']['unscored']} unscored)")
    print("\n  ADJUDICATION vs the sealed key")
    print(f"    detector health (catch rate) : {v['catch_rate']}")
    print(f"    coverage honesty             : {v['coverage_honesty']}")
    print(f"    false positives              : {v['false_positives']}")
    print(f"    voided                       : {v['voided']} {v['void_reason']}")
    stored = res.get("round_path")
    print("\n  round archived: " + (stored if stored
                                    else "NOT STORED -- this round cannot be re-scored"))
    if res["unmatched_finds"]:
        print(f"\n  {len(res['unmatched_finds'])} find(s) matched NO canary -- real pre-existing "
              f"findings in the tree, not planted:")
        for u in res["unmatched_finds"][:5]:
            print(f"    {u}")
    return 0 if not v["voided"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
